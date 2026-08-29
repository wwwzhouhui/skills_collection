"""zcode_speech: 走 ZCode 官方 Server MCP 的 ASR / TTS provider。

端点：``POST {ZCODE_BASE_URL}/api/v1/mcp/server/video_edit``（Streamable HTTP MCP，
stateless），工具 ``speech_transcribe`` / ``speech_synthesize``。鉴权不由本插件持有：
身份头随每次 ``tools/call`` 的 ``_meta`` 由 ZCode 宿主下发，见 ve_tools/official_auth.py。

与直连 HTTP 的兼容通道（cloud_asr / tts.py 的 cloud_tts）相比，这里没有任何 API key：用户只要
登录 ZCode 且持有 Coding Plan 即可用，配额与计费由服务端统一管。

四个实现上必须记住的服务端事实（都核过源码，改动前先复核）：

1. **请求体上限 45 MiB，卡点在入口 nginx。** 上限由入口 nginx 的 ``client_max_body_size`` 决定，
   应用层 go-sdk 侧配的是 50 MiB。这个值运维改过两次：最初是 nginx 默认的 1m（实测
   1,048,576 B 通过、1,048,577 B 起返回 nginx 的 413 HTML）→ 5 MiB → 现在 45 MiB。长音频仍要
   在本地分片逐片上传（见 media.py 的 chunked_payload 与本文件的 max_chunk_seconds），服务端
   自带的 ``chunk_seconds`` 一律传 0。网关上限再变时设 ``ZCODE_SPEECH_MAX_REQUEST_BYTES``，
   分片长度会自动跟着变，不需要改代码。
   **注意到 45 MiB 这一档，卡点已经不是体积而是时间**：45 MiB 的预算够装约 4400 秒音频，
   而一次请求的超时预算是 ASR_TIMEOUT_SECONDS（3600s），转写 70 分钟音频必然先超时；
   因此分片秒数另有上限 MAX_CHUNK_SECONDS_CEILING，见 max_chunk_seconds；
2. **所有入参都是 required。** 服务端刻意去掉了请求结构体上的全部 ``omitempty``
   （zcode-server commit b1c7283），推导出的 JSON Schema 里每个字段都进 ``required``。
   所以下面两个 payload 构造函数把每个字段都显式填齐，含零值——少一个就是 schema 校验失败；
3. **HTTP 细节。** 只收 POST；``Content-Type: application/json``；``Accept`` 必须同时含
   ``application/json`` 与 ``text/event-stream``（缺一 400）；响应是 SSE 帧（服务端没开
   ``JSONResponse``），要解 ``data:`` 行。stateless 下 go-sdk 会合成 initialize/initialized，
   因此裸发 ``tools/call`` 即可，不需要握手，也不要发 ``Mcp-Session-Id``；
4. **URL 不能带尾斜杠**（``…/video_edit/`` 会 307）。
"""
from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .official_auth import OfficialAuth
from .run_context import clean_env
from .result import ToolResult
from .cloud_asr import language_sanity_warning, prepare_asr_audio

MCP_PATH = "/api/v1/mcp/server/video_edit"
TOOL_TRANSCRIBE = "speech_transcribe"
TOOL_SYNTHESIZE = "speech_synthesize"
PROVIDER = "zcode_speech"

# 请求体预算。**卡点是入口 nginx，不是 go-sdk。**
#
# go-sdk 侧服务端配的是 50 MiB，真正的瓶颈是前面那层 nginx 的 client_max_body_size。
# 它最初是 nginx 默认的 1m（实测：1,048,576 B 通过，1,048,577 B 起返回
# nginx 的 413 HTML），运维两次调高：1m → 5 MiB → 45 MiB，故默认值跟到 45 MiB。
# 留 5 MiB 不贴满 50 MiB：超出应用层上限时 go-sdk 的 413 与 nginx 的 413 表现不同，没必要
# 把这条边界踩在两个组件的交界上。
#
# 网关上限再变时不需要改插件：设 ZCODE_SPEECH_MAX_REQUEST_BYTES 即可，分片长度会跟着自动
# 变化（见 max_chunk_seconds）。
DEFAULT_MAX_REQUEST_BODY_BYTES = 45 * 1024 * 1024
# 留给 JSON-RPC 包封与另外 7 个必填字段的余量。它们只有几百字节，8 KiB 是宽松取值。
REQUEST_BODY_OVERHEAD_BYTES = 8 * 1024
# prepare_asr_audio 统一抽成 16 kHz 单声道 mp3 @64 kbps = 8000 B/s，是唯一的换算依据。
UPLOAD_AUDIO_BYTES_PER_SECOND = 8000
# 分片留 5% 余量：ffmpeg 的实际码率会略高于标称，且切片会带上 ASR_CHUNK_OVERLAP_SECONDS。
CHUNK_SAFETY_FACTOR = 0.95
CHUNK_OVERLAP_ALLOWANCE_SECONDS = 2.0
# 分片秒数的上限，与体积预算无关。
#
# 体积预算涨到 45 MiB 后，按 8 KB/s 反推出的分片是约 4200 秒（70 分钟），而单次请求的超时预算
# 是 media.py 的 ASR_TIMEOUT_SECONDS（3600s）——转写 70 分钟音频不可能在 1 小时内返回，
# 每一片都会超时，且超时后整片重来，浪费的是几十分钟而不是几十秒。
#
# 取 1700s 与兼容通道 (cloud_asr) 的 ASR_CHUNK_SECONDS 一致：那是这条流水线上已经跑熟的分片长度，
# 单片转写耗时远小于超时预算，重试成本也可接受。用户显式传 chunk_seconds 仍可越过这个默认值
# （体积守卫按 max_audio_bytes 另算），因此这里只约束默认值，不封顶能力。
MAX_CHUNK_SECONDS_CEILING = 1700.0


def max_request_body_bytes() -> int:
    """请求体上限。ZCODE_SPEECH_MAX_REQUEST_BYTES 可覆盖（运维调高 nginx 后用它跟上）。"""
    raw = clean_env("ZCODE_SPEECH_MAX_REQUEST_BYTES")
    if raw:
        try:
            parsed = int(str(raw).strip())
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
    return DEFAULT_MAX_REQUEST_BODY_BYTES


def max_audio_bytes() -> int:
    """单次请求可上传的原始音频字节数（base64 膨胀 4/3 反推）。"""
    return max(1, ((max_request_body_bytes() - REQUEST_BODY_OVERHEAD_BYTES) * 3) // 4)


def max_chunk_seconds() -> float:
    """由上述预算推导出的分片秒数，供 media.transcribe 当默认值。

    不写死一个数字：预算变了分片必须跟着变，否则两处一旦漂移就是一次线上 413——正是
    这条代码路径已经踩过的坑（按 4 MiB 算出 300s，而当时真实上限只有 1 MiB）。

    但也不能一路跟着体积涨：预算大到一定程度后卡点变成超时预算而非体积，故再夹一道
    MAX_CHUNK_SECONDS_CEILING（见该常量的说明）。
    """
    seconds = max_audio_bytes() / UPLOAD_AUDIO_BYTES_PER_SECOND
    derived = float(int((seconds - CHUNK_OVERLAP_ALLOWANCE_SECONDS) * CHUNK_SAFETY_FACTOR))
    return min(MAX_CHUNK_SECONDS_CEILING, max(10.0, derived))

DEFAULT_TIMEOUT_SECONDS = 600.0

_ACCEPT = "application/json, text/event-stream"


def zcode_api_origin() -> tuple[str | None, str | None]:
    """(origin, error)。

    **只读进程环境**，不走 clean_env 的 .env 回退。理由与 cloud_asr 的 endpoint 信任模型同源：
    项目本地 .env 是不可信输入，若允许它提供 origin，一个仓库里的 .env 就能把 ZCode 的 JWT
    与 Coding Plan key 导向攻击者的主机。ZCODE_BASE_URL 由宿主在 spawn 时注入（它是宿主已解析
    完成的权威值），拿不到就是拿不到，不猜。
    """
    raw = (os.environ.get("ZCODE_BASE_URL") or "").strip().rstrip("/")
    if not raw:
        return None, (
            "ZCODE_BASE_URL is not set in the process environment; the ZCode host injects it, "
            "so this usually means the plugin is not running under ZCode"
        )
    try:
        parts = urlsplit(raw)
    except Exception as exc:  # noqa: BLE001
        return None, f"ZCODE_BASE_URL is unparseable: {raw!r} ({exc})"
    scheme = (parts.scheme or "").lower()
    host = (parts.hostname or "").lower()
    if parts.username or parts.password:
        return None, "ZCODE_BASE_URL must not embed credentials"
    is_loopback = host in ("127.0.0.1", "::1", "localhost")
    if scheme == "https" or (scheme == "http" and is_loopback):
        return f"{parts.scheme}://{parts.netloc}", None
    return None, (
        f"ZCODE_BASE_URL must be https (or http on loopback for local development), got {raw!r}"
    )


def official_auth_of(ctx: Any) -> OfficialAuth | None:
    return getattr(ctx, "official_auth", None)


def zcode_speech_status(ctx: Any) -> dict[str, Any]:
    """{available, reasons, ...}，与 cloud_asr_status() / cloud_tts_status() 同构，
    供 provider 选择与能力探测复用。三种不可用要能被分辨，否则用户不知道该去登录还是去升级套餐。"""
    reasons: list[str] = []
    origin, origin_error = zcode_api_origin()
    if origin_error:
        reasons.append(origin_error)
    auth = official_auth_of(ctx)
    if auth is None:
        reasons.append(
            "the MCP host did not send ZCode identity headers with this tool call "
            "(expected when running outside ZCode, e.g. under Claude Code or a direct CLI call)"
        )
    elif not auth.ok:
        reasons.append(f"ZCode identity unavailable: {auth.describe_failure()}")
    try:
        import requests  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"requests package unavailable: {exc}")
    return {
        "available": not reasons,
        "reasons": reasons,
        "auth_mode": "zcode_official_meta",
        "endpoint": f"{origin}{MCP_PATH}" if origin else None,
    }


class ZCodeSpeechError(RuntimeError):
    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def call_speech_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    ctx: Any,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """调用官方 MCP 的一个工具，返回 (structured_result, meta)。失败抛 ZCodeSpeechError。"""
    import requests

    origin, origin_error = zcode_api_origin()
    if origin_error or not origin:
        raise ZCodeSpeechError(origin_error or "ZCODE_BASE_URL is unavailable", {"recoverable": False})
    auth = official_auth_of(ctx)
    if auth is None or not auth.ok:
        detail = auth.describe_failure() if auth is not None else "no identity headers in tool call _meta"
        raise ZCodeSpeechError(f"ZCode identity unavailable: {detail}", {"recoverable": False})

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    body_budget = max_request_body_bytes()
    if len(body) > body_budget:
        raise ZCodeSpeechError(
            f"request body is {len(body):,d} B, over the {body_budget:,d} B limit; "
            "split the input further (or raise ZCODE_SPEECH_MAX_REQUEST_BYTES if the gateway "
            "limit was raised)",
            {"recoverable": False, "request_body_bytes": len(body), "body_budget_bytes": body_budget},
        )

    headers = {
        **(auth.headers or {}),
        "Accept": _ACCEPT,
        "Content-Type": "application/json",
    }
    url = f"{origin}{MCP_PATH}"
    meta: dict[str, Any] = {"endpoint": url, "mcp_tool": name}
    try:
        # allow_redirects=False：3xx 不跟随，避免身份头被跨 origin 重定向带走。
        # 正式端点是 canonical URL，出现 3xx 说明 URL 拼错了（如带了尾斜杠）。
        response = requests.post(
            url, headers=headers, data=body, timeout=timeout_seconds, allow_redirects=False
        )
    except Exception as exc:  # noqa: BLE001
        raise ZCodeSpeechError(f"request failed: {exc}", {"recoverable": True, **meta}) from exc

    # 服务端自行生成 request id 并放在响应头里（它不采纳入站值），是与服务端日志对账的唯一键。
    server_request_id = response.headers.get("x-request-id") or ""
    if server_request_id:
        meta["server_request_id"] = server_request_id

    if response.status_code in (401, 403):
        # 身份问题重取同一份凭证不会变好，且本进程在单次工具调用内换不到新头
        # （见 official_auth.py 的约束 2）。标为不可重试，让 agent 重试整个工具调用。
        kind = "official_auth_rejected" if response.status_code == 401 else "official_auth_forbidden"
        raise ZCodeSpeechError(
            f"ZCode rejected the official MCP call ({response.status_code} {kind})",
            {"recoverable": False, "http_status": response.status_code, **meta},
        )
    if 300 <= response.status_code < 400:
        raise ZCodeSpeechError(
            f"official MCP endpoint returned a redirect ({response.status_code}); "
            "the endpoint must be a canonical URL without a trailing slash",
            {"recoverable": False, "http_status": response.status_code, **meta},
        )
    if response.status_code == 413:
        # 带上服务端原话与本次体积：413 可能来自入口 nginx（client_max_body_size，当前 45m，
        # 响应是 HTML）也可能来自 go-sdk（MaxRequestBodyBytes，响应是
        # "request body exceeds N bytes"）。两者的处置不同，报错里必须能分辨。
        raise ZCodeSpeechError(
            f"official MCP rejected the request body as too large "
            f"(sent {len(body):,d} B, budget {body_budget:,d} B): {_decode_body(response)[:300]!r}",
            {
                "recoverable": False,
                "http_status": 413,
                "request_body_bytes": len(body),
                "body_budget_bytes": body_budget,
                **meta,
            },
        )
    if response.status_code >= 400:
        raise ZCodeSpeechError(
            f"official MCP request failed: {response.status_code} {_decode_body(response)[:500]}",
            {"recoverable": response.status_code >= 500, "http_status": response.status_code, **meta},
        )

    envelope = _parse_rpc_response(_decode_body(response), response.headers.get("content-type", ""))
    if envelope is None:
        raise ZCodeSpeechError("official MCP response had no JSON-RPC frame", {"recoverable": True, **meta})
    error = envelope.get("error")
    if isinstance(error, dict):
        raise ZCodeSpeechError(
            f"official MCP rpc error {error.get('code')}: {error.get('message')}",
            {"recoverable": False, **meta},
        )
    result = envelope.get("result")
    if not isinstance(result, dict):
        raise ZCodeSpeechError("official MCP response had no result", {"recoverable": True, **meta})
    if result.get("isError"):
        raise ZCodeSpeechError(
            f"{name} failed: {_result_text(result)[:500]}",
            {"recoverable": True, **meta},
        )
    data = _result_data(result)
    if data is None:
        raise ZCodeSpeechError(
            f"{name} returned no structured content", {"recoverable": True, **meta}
        )
    return data, meta


def _decode_body(response: Any) -> str:
    """按 UTF-8 解响应体，不用 requests 的 ``response.text``。

    Bugfix: ``response.text`` 在没有 charset 参数时按 RFC 2616 给 ``text/*`` 猜
    ISO-8859-1，而官方 MCP 的响应正是 ``Content-Type: text/event-stream``（无 charset）。
    走 ``.text`` 会把每一段中文听写结果变成乱码（“你好”→“ä½ å¥½”），且不会报错。
    JSON-RPC 载荷按规范就是 UTF-8，这里直接按 UTF-8 解。
    """
    body = getattr(response, "content", b"") or b""
    return body.decode("utf-8", errors="replace")


def _parse_rpc_response(text: str, content_type: str) -> dict[str, Any] | None:

    """SSE 帧或裸 JSON 都能解。服务端默认走 SSE（没开 JSONResponse），但别把它写死——
    一旦服务端打开 JSONResponse，写死 SSE 的客户端会整体失败。"""
    if "text/event-stream" not in (content_type or "").lower():
        try:
            parsed = json.loads(text)
        except ValueError:
            return None
        return parsed if isinstance(parsed, dict) else None

    frames: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if line.startswith("data:"):
            current.append(line[5:].lstrip())
            continue
        if line == "" and current:
            frames.append("\n".join(current))
            current = []
    if current:
        frames.append("\n".join(current))
    for frame in reversed(frames):
        try:
            parsed = json.loads(frame)
        except ValueError:
            continue
        if isinstance(parsed, dict) and ("result" in parsed or "error" in parsed):
            return parsed
    return None


def _result_data(result: dict[str, Any]) -> dict[str, Any] | None:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    # 回退：typed tool 同时把 JSON 写进 content 文本
    text = _result_text(result)
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _result_text(result: dict[str, Any]) -> str:
    blocks = result.get("content")
    if not isinstance(blocks, list):
        return ""
    parts = [
        str(block.get("text") or "")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(part for part in parts if part).strip()


# ── speech_transcribe ────────────────────────────────────────────────────────


def transcribe_arguments(audio_b64: str, audio_format: str, language: str) -> dict[str, Any]:
    """服务端 SpeechTranscribeRequest 的 8 个字段全部显式填齐（全为 required，见模块 docstring）。

    chunk_seconds / retries / retry_backoff_seconds 传 0：分片与重试都留在本地
    （请求体上限决定了服务端分片用不上，重试要复用插件既有的 run_asr_with_retries）。
    """
    return {
        "audio_base64": audio_b64,
        "input_format": audio_format,
        "input_path": "",
        "language": language or "",
        "timeout_seconds": 0,
        "chunk_seconds": 0,
        "retries": 0,
        "retry_backoff_seconds": 0,
    }


def zcode_speech_transcribe_payload(
    input_path: Path,
    work_dir: Path,
    *,
    ctx: Any,
    language: str,
    timeout_seconds: float,
    started: float,
) -> tuple[dict[str, Any], Path] | ToolResult:
    """签名与产物形状都与 cloud_asr_transcribe_payload 对齐，下游 transcript 消费方不用改。"""
    status = zcode_speech_status(ctx)
    if not status["available"]:
        return ToolResult(
            text="[ERROR] zcode_speech is not available: " + "; ".join(status["reasons"]),
            data={"recoverable": False, "provider": PROVIDER, "status": status},
        )
    prepared = prepare_asr_audio(input_path, work_dir)
    if isinstance(prepared, ToolResult):
        return prepared
    asr_source, audio_format, source_kind = prepared
    if asr_source.stat().st_size > max_audio_bytes() and source_kind == "original_audio":
        # 透传的原始 mp3 可能是高码率的：重编码成 16k/64kbps 再试一次
        prepared = prepare_asr_audio(input_path, work_dir, allow_passthrough=False)
        if isinstance(prepared, ToolResult):
            return prepared
        asr_source, audio_format, source_kind = prepared
    audio_bytes = asr_source.stat().st_size
    budget = max_audio_bytes()
    if audio_bytes > budget:
        return ToolResult(
            text=(
                f"[ERROR] zcode_speech audio too large ({audio_bytes:,d} B > {budget:,d} B); "
                f"lower chunk_seconds to at most {max_chunk_seconds():.0f}s so each request stays "
                f"under the {max_request_body_bytes():,d} B gateway body limit"
            ),
            data={
                "provider": PROVIDER,
                "recoverable": False,
                "asr_audio": str(asr_source),
                "audio_bytes": audio_bytes,
                "audio_budget_bytes": budget,
            },
        )

    audio_b64 = base64.b64encode(asr_source.read_bytes()).decode("ascii")
    arguments = transcribe_arguments(audio_b64, audio_format, language)
    try:
        data, meta = call_speech_tool(
            TOOL_TRANSCRIBE,
            arguments,
            ctx=ctx,
            timeout_seconds=max(60.0, float(timeout_seconds)),
        )
    except ZCodeSpeechError as exc:
        return ToolResult(
            text=f"[ERROR] zcode_speech transcription failed: {exc}",
            data={
                "provider": PROVIDER,
                "recoverable": bool(exc.detail.get("recoverable", True)),
                **exc.detail,
            },
        )
    payload = transcript_from_response(
        data,
        source_media=input_path,
        asr_audio=asr_source,
        language=language,
        source_kind=source_kind,
        elapsed_seconds=round(time.time() - started, 3),
        meta=meta,
    )
    return payload, asr_source


def transcript_from_response(
    data: dict[str, Any],
    *,
    source_media: Path,
    asr_audio: Path,
    language: str,
    source_kind: str,
    elapsed_seconds: float,
    meta: dict[str, Any],
) -> dict[str, Any]:
    """服务端 SpeechTranscribeResponse → 插件 transcript.json 口径。

    时间戳两侧都已是秒，不用换算。唯一需要注意的类型差异：服务端 ``transcript.speaker_labels``
    是字符串数组，插件口径是 bool——直接透传会让下游 ``any(...)`` 之类的判断行为改变。
    """
    transcript = data.get("transcript") if isinstance(data.get("transcript"), dict) else {}
    segments = [
        segment
        for segment in (_segment(item) for item in _as_list(transcript.get("segments")))
        if segment is not None
    ]
    words = [word for word in (_word(item, "") for item in _as_list(transcript.get("words"))) if word]
    if not words:
        words = [word for segment in segments for word in segment.get("words", [])]
    text = str(transcript.get("text") or "").strip()
    if not text and segments:
        text = "\n".join(segment["text"] for segment in segments if segment["text"]).strip()
    has_speakers = any(segment.get("speaker") for segment in segments)

    out: dict[str, Any] = {
        "provider": PROVIDER,
        "language": str(transcript.get("language") or data.get("language") or language),
        "speaker_labels": has_speakers,
        "source_media": str(source_media),
        "asr_audio": str(asr_audio),
        "source_kind": source_kind,
        "text": text,
        "words": words,
        "segments": segments,
        "elapsed_seconds": elapsed_seconds,
        "time_unit": "seconds",
        "endpoint": meta.get("endpoint"),
    }
    if meta.get("server_request_id"):
        out["zcode_request_id"] = meta["server_request_id"]
    duration = _number(transcript.get("audio_duration_seconds"))
    if duration is not None:
        out["audio_duration_seconds"] = duration
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
    if usage:
        out["usage"] = usage
    if data.get("silent_audio"):
        out["silent_audio"] = True
        out["note"] = "zcode_speech reported silent audio (no speech detected); empty transcript is valid"
    warning = language_sanity_warning(language, text, has_speakers)
    if warning:
        out["warnings"] = [warning]
        out["note"] = (out.get("note") + " " if out.get("note") else "") + warning
    return out


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round(parsed, 3)


def _word(item: Any, fallback_speaker: str) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    return {
        "text": text,
        "start": _number(item.get("start")) or 0.0,
        "end": _number(item.get("end")) or 0.0,
        "speaker": str(item.get("speaker") or fallback_speaker) or None,
    }


def _segment(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    speaker = str(item.get("speaker") or "").strip()
    text = str(item.get("text") or "").strip()
    words = [word for word in (_word(w, speaker) for w in _as_list(item.get("words"))) if word]
    if not text and not words:
        return None
    return {
        "speaker": speaker,
        "text": text,
        "start": _number(item.get("start")) or 0.0,
        "end": _number(item.get("end")) or 0.0,
        "words": words,
    }


# ── speech_synthesize ────────────────────────────────────────────────────────


def synthesize_arguments(
    *,
    text: str,
    output_format: str,
    voice: str,
    speed: float,
    speech_rate: int,
    pitch_rate: int,
    loudness_rate: int,
    sample_rate: int,
    model: str,
    style_instructions: str,
    sample_mode: bool,
) -> dict[str, Any]:
    """服务端 SpeechSynthesizeRequest 的 11 个字段全部显式填齐（全为 required）。"""
    return {
        "text": text,
        "output_format": output_format,
        "voice": voice,
        "speed": speed,
        "speech_rate": speech_rate,
        "pitch_rate": pitch_rate,
        "loudness_rate": loudness_rate,
        "sample_rate": sample_rate,
        "model": model,
        "style_instructions": style_instructions,
        "sample_mode": sample_mode,
    }


def write_synthesized_audio(data: dict[str, Any], output_path: Path) -> Path | ToolResult:
    audio_b64 = data.get("audio_base64")
    if not isinstance(audio_b64, str) or not audio_b64.strip():
        return ToolResult(
            text="[ERROR] zcode_speech TTS response contained no audio_base64",
            data={
                "provider": PROVIDER,
                "output_path": str(output_path),
                "response_keys": sorted(data.keys()),
                "retryable": True,
            },
        )
    try:
        output_path.write_bytes(base64.b64decode(audio_b64))
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            text=f"[ERROR] zcode_speech TTS returned invalid base64 audio: {exc}",
            data={"provider": PROVIDER, "output_path": str(output_path), "retryable": False},
        )
    return output_path
