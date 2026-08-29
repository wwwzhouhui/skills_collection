"""ZCode 官方 Server MCP 身份头的接收侧。

宿主（ZCode CLI 的 MCP adapter）在**每次** `tools/call` 的 `params._meta` 上带一个
`com.zcode/official-mcp-auth` 键，内容是本次调用可用的身份头，或一个失败原因。
协议见 z-code 仓库的 `docs/coding-plan/zcode-official-server-mcp-stdio-meta-phase-2-spec.md`。

为什么身份头走 `_meta` 而不是 env：env 在本进程生命周期内是死值，而这个 MCP server 活整个
会话，ZCode 的 JWT 一轮换就必然 401 且无法自救。`_meta` 是逐调用现取的，天然新鲜。

两个使用约束：

1. `mcp` 的 `request_context` 是 contextvar，**不会**跨 `loop.run_in_executor` 的线程边界传播。
   因此必须在事件循环线程里把它读出来（见 server_common.serve），worker 线程里读不到；
2. 单次工具调用内部长跑时（如 2 小时视频转写会在一次调用里连续发几十个 HTTP 请求），中途
   凭证轮换后本进程拿不到新头。约定是 401 **不重试**，如实报 official_auth_rejected，
   由 agent 重试整个工具调用来换取新头。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# 跨语言协议常量，必须与 z-code 的 OFFICIAL_MCP_AUTH_META_KEY 逐字符一致。
OFFICIAL_AUTH_META_KEY = "com.zcode/official-mcp-auth"

# 宿主下发的失败原因（枚举，不是自由文本）。这里只做人类可读化，不据此改变控制流——
# 控制流只看"有没有 headers"。
REASON_HINTS = {
    "official_auth_unavailable": (
        "ZCode is not signed in, or no provider connection is selected "
        "(a standalone CLI without a host auth port also reports this)"
    ),
    "official_auth_plan_required": (
        "the official speech MCP is a Coding Plan entitlement, and the currently selected "
        "ZCode connection has no Coding Plan key (Start Plan and API-key mode are not eligible)"
    ),
    "official_mcp_origin_untrusted": (
        "the host rejected its own resolved ZCode API origin; this is a client configuration "
        "problem (non-https or overridden endpoint), not a credential problem"
    ),
}


@dataclass(frozen=True)
class OfficialAuth:
    """一次工具调用可用的官方身份。`headers` 与 `reason` 恰有一个非空。"""

    headers: dict[str, str] | None = None
    reason: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.headers)

    def describe_failure(self) -> str:
        if self.ok:
            return ""
        reason = self.reason or "official_auth_unavailable"
        hint = REASON_HINTS.get(reason)
        return f"{reason} ({hint})" if hint else reason


def extract_official_auth(meta: Any) -> OfficialAuth | None:
    """从一个 `_meta` 对象里取出身份载荷。返回 None = 宿主没下发该键（非 ZCode 宿主）。"""
    payload = _meta_get(meta, OFFICIAL_AUTH_META_KEY)
    if not isinstance(payload, dict):
        return None
    if payload.get("ok") is True:
        headers = payload.get("headers")
        if not isinstance(headers, dict) or not headers:
            # 声明成功却没有头：当作协议异常处理，不静默当成"没配"
            return OfficialAuth(reason="official_auth_unavailable")
        clean = {
            str(name): str(value)
            for name, value in headers.items()
            if isinstance(name, str) and value is not None and str(value).strip() != ""
        }
        return OfficialAuth(headers=clean) if clean else OfficialAuth(
            reason="official_auth_unavailable"
        )
    reason = payload.get("reason")
    return OfficialAuth(reason=str(reason) if isinstance(reason, str) else "official_auth_unavailable")


def read_official_auth(
    *,
    server: Any = None,
    request_context: Any = None,
    params: Any = None,
) -> OfficialAuth | None:
    """在事件循环线程里读取本次请求的身份载荷。

    三个来源按可得性依次尝试，覆盖 mcp 1.x 两套 dispatch API：
    显式 params（>=1.22 的 on_call_tool）、显式 request_context、以及 contextvar
    （<1.22 的装饰器路径只能走这条）。
    """
    for meta in (
        _params_meta(params),
        getattr(request_context, "meta", None),
        _server_context_meta(server),
    ):
        if meta is None:
            continue
        found = extract_official_auth(meta)
        if found is not None:
            return found
    return None


def _params_meta(params: Any) -> Any:
    if params is None:
        return None
    if isinstance(params, dict):
        return params.get("_meta") or params.get("meta")
    return getattr(params, "meta", None)


def _server_context_meta(server: Any) -> Any:
    if server is None:
        return None
    try:
        # 未在请求上下文中调用时 mcp 会抛 LookupError
        return getattr(server.request_context, "meta", None)
    except Exception:  # noqa: BLE001 — 取不到上下文不是错误，只是没有身份
        return None


def _meta_get(meta: Any, key: str) -> Any:
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta.get(key)
    # pydantic 的 RequestParams.Meta 用 extra="allow"，自定义键落在 model_extra 里；
    # 键名带点和斜杠，不能用属性访问。
    extra = getattr(meta, "model_extra", None)
    if isinstance(extra, dict) and key in extra:
        return extra[key]
    try:
        dumped = meta.model_dump(by_alias=True)
    except Exception:  # noqa: BLE001
        return None
    return dumped.get(key) if isinstance(dumped, dict) else None
