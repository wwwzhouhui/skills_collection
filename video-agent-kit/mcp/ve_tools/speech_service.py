from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .result import ToolResult
from .run_context import clean_env


REMOTE_SPEECH_URL_ENV = "VE_SPEECH_MCP_URL"
REMOTE_SPEECH_TOKEN_ENV = "VE_SPEECH_MCP_TOKEN"
REMOTE_ASR_TRANSFER_ENV = "VE_SPEECH_MCP_ASR_TRANSFER"
TRANSCRIBE_TOOL_ENV = "VE_SPEECH_TRANSCRIBE_TOOL"
SYNTHESIZE_TOOL_ENV = "VE_SPEECH_SYNTHESIZE_TOOL"

DEFAULT_TRANSCRIBE_TOOL = "speech_transcribe"
DEFAULT_SYNTHESIZE_TOOL = "speech_synthesize"

# The kit's own code carries no vendor names. These patterns exist for text the
# kit does NOT author: error bodies, status messages and resource identifiers
# echoed back by a remote speech MCP or a direct-HTTP compatibility service. That
# text reaches the user through tool results, so it is scrubbed on the way out —
# which is why the vendor strings below are deliberate, not leftovers.
_VENDOR_PATTERNS = [
    (re.compile(r"seed[_ -]?asr", re.IGNORECASE), "cloud_asr"),
    (re.compile(r"seed[_ -]?audio", re.IGNORECASE), "cloud_tts"),
    (re.compile(r"volc(?:engine)?", re.IGNORECASE), "cloud speech service"),
    (re.compile(r"火山引擎|火山|豆包"), "cloud speech service"),
    (re.compile(r"bytedance", re.IGNORECASE), "cloud speech service"),
    (re.compile(r"openspeech\.bytedance\.com", re.IGNORECASE), "cloud speech endpoint"),
    (re.compile(r"volc\.[A-Za-z0-9_.-]+"), "cloud_resource"),
]


def genericize_text(value: object) -> str:
    text = str(value or "")
    for pattern, replacement in _VENDOR_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def genericize_data(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            safe_key = genericize_text(key)
            if safe_key in {"resource_id", "flash_resource_id", "endpoint"}:
                continue
            out[safe_key] = genericize_data(item)
        return out
    if isinstance(value, list):
        return [genericize_data(item) for item in value]
    if isinstance(value, str):
        return genericize_text(value)
    return value


def genericize_result(result: ToolResult) -> ToolResult:
    return ToolResult(
        text=genericize_text(result.text),
        data=genericize_data(result.data),
        artifacts=result.artifacts,
        image_paths=result.image_paths,
        video_paths=result.video_paths,
    )


def remote_speech_configured() -> bool:
    return bool(clean_env(REMOTE_SPEECH_URL_ENV))


def remote_tool_name(kind: str) -> str:
    if kind == "transcribe":
        return clean_env(TRANSCRIBE_TOOL_ENV) or DEFAULT_TRANSCRIBE_TOOL
    if kind == "synthesize":
        return clean_env(SYNTHESIZE_TOOL_ENV) or DEFAULT_SYNTHESIZE_TOOL
    return kind


def remote_asr_transfer_mode() -> str:
    """How the kit sends ASR media to the remote speech MCP server.

    path:   send input_path; works for co-located/shared-storage deployments.
    base64: upload a compact extracted audio file in JSON-RPC arguments.
    auto:   path for localhost URLs, base64 otherwise.
    """
    configured = str(clean_env(REMOTE_ASR_TRANSFER_ENV) or "auto").strip().lower()
    if configured in {"path", "base64"}:
        return configured
    if configured not in {"", "auto"}:
        return "auto"
    url = clean_env(REMOTE_SPEECH_URL_ENV) or ""
    try:
        host = (urlsplit(url).hostname or "").lower()
    except Exception:
        host = ""
    if host in {"", "localhost", "127.0.0.1", "::1"}:
        return "path"
    return "base64"


def remote_speech_url_is_loopback(url: str | None = None) -> bool:
    raw = url or clean_env(REMOTE_SPEECH_URL_ENV) or ""
    try:
        host = (urlsplit(raw).hostname or "").lower()
    except Exception:
        return False
    return host in {"localhost", "127.0.0.1", "::1"}


def cloud_asr_available(ctx: Any | None = None) -> bool:
    """Is *some* transcription channel reachable?

    Order matters, and so does the ``ctx`` -less case: hooks (closeout contract)
    call this from a separate process with no tool-call context, so they cannot
    see the per-call ZCode identity headers. Presence of ``ZCODE_BASE_URL`` is
    the best signal available there, and it is the right one to trust — under
    ZCode the official channel needs no local credentials, so answering "no"
    just because no API key is configured would wrongly excuse the run from
    producing a transcript.
    """
    if remote_speech_configured():
        return True
    if ctx is not None:
        try:
            from .zcode_speech import zcode_speech_status

            if zcode_speech_status(ctx).get("available"):
                return True
        except Exception:
            pass
    elif (os.environ.get("ZCODE_BASE_URL") or "").strip():
        return True
    try:
        from .cloud_asr import cloud_asr_status

        return bool(cloud_asr_status().get("available"))
    except Exception:
        return False


def call_remote_speech_tool(kind: str, arguments: dict[str, Any], *, timeout: float = 600.0) -> ToolResult:
    """Call a remote HTTP MCP speech tool using a JSON-RPC tools/call request.

    The remote server is expected to expose one paid speech capability per MCP
    tool. The response can be either a ToolResult-shaped JSON object, a normal
    MCP CallToolResult, or a direct structured JSON payload.
    """
    url = clean_env(REMOTE_SPEECH_URL_ENV)
    if not url:
        return ToolResult(text=f"[ERROR] remote speech MCP URL is not configured ({REMOTE_SPEECH_URL_ENV})")
    tool_name = remote_tool_name(kind)
    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    token = clean_env(REMOTE_SPEECH_TOKEN_ENV)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        import requests

        if remote_speech_url_is_loopback(url):
            session = requests.Session()
            session.trust_env = False
            response = session.post(url, headers=headers, json=body, timeout=timeout)
        else:
            response = requests.post(url, headers=headers, json=body, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(text=f"[ERROR] remote speech MCP call failed: {exc}", data={"retryable": True})
    if response.status_code >= 400:
        retryable = response.status_code in {408, 409, 425, 429} or 500 <= response.status_code <= 599
        return ToolResult(
            text=f"[ERROR] remote speech MCP call failed: HTTP {response.status_code} {response.text[:500]}",
            data={"status_code": response.status_code, "retryable": retryable},
        )
    try:
        payload = _decode_remote_payload(response.text, response.headers.get("content-type", ""))
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] remote speech MCP returned invalid JSON: {exc}", data={"retryable": True})
    if isinstance(payload, dict) and payload.get("error"):
        err = payload["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        code = err.get("code") if isinstance(err, dict) else None
        retryable = code not in {-32700, -32600, -32601, -32602}
        return ToolResult(
            text=f"[ERROR] remote speech MCP tool failed: {message}",
            data={"retryable": retryable, **({"code": code} if code is not None else {})},
        )
    result = payload.get("result") if isinstance(payload, dict) and "result" in payload else payload
    return tool_result_from_remote_payload(result)


def _decode_remote_payload(text: str, content_type: str) -> Any:
    if "text/event-stream" not in content_type.lower():
        return json.loads(text)
    data_lines = []
    for line in text.splitlines():
        if line.startswith("data:"):
            data = line.split(":", 1)[1].strip()
            if data and data != "[DONE]":
                data_lines.append(data)
    if not data_lines:
        raise ValueError("SSE response had no data lines")
    return json.loads(data_lines[-1])


def tool_result_from_remote_payload(payload: Any) -> ToolResult:
    if isinstance(payload, ToolResult):
        return payload
    if isinstance(payload, dict):
        if "text" in payload or "data" in payload or "artifacts" in payload:
            return ToolResult(
                text=str(payload.get("text") or "remote speech tool completed"),
                data=payload.get("data") if isinstance(payload.get("data"), dict) else {},
                artifacts=[str(p) for p in payload.get("artifacts", []) if p],
                image_paths=[str(p) for p in payload.get("image_paths", []) if p],
                video_paths=[str(p) for p in payload.get("video_paths", []) if p],
            )
        content = payload.get("content")
        if isinstance(content, list):
            texts = [
                str(item.get("text") or "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            data = payload.get("structuredContent") or payload.get("structured_content") or {}
            return ToolResult(
                text="\n".join(t for t in texts if t) or "remote speech tool completed",
                data=data if isinstance(data, dict) else {},
            )
        return ToolResult(text="remote speech tool completed", data=payload)
    return ToolResult(text=str(payload or "remote speech tool completed"))


def audio_url_allowed(url: str) -> bool:
    """Remote speech audio URLs may be fetched only from the configured remote
    server origin. Base64 audio is preferred because it is fully self-contained."""
    remote = clean_env(REMOTE_SPEECH_URL_ENV)
    if not remote:
        return False
    try:
        candidate = urlsplit(url)
        configured = urlsplit(remote)
        return (
            (candidate.scheme or "").lower() == (configured.scheme or "").lower()
            and (candidate.hostname or "").lower() == (configured.hostname or "").lower()
            and effective_port(candidate) == effective_port(configured)
        )
    except Exception:
        return False


def effective_port(parts) -> int | None:
    if parts.port is not None:
        return parts.port
    scheme = (parts.scheme or "").lower()
    if scheme == "http":
        return 80
    if scheme == "https":
        return 443
    return None


def extract_transcript_payload(data: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("transcript", "transcript_payload", "payload", "result"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    if isinstance(data.get("segments"), list) or isinstance(data.get("words"), list) or data.get("text"):
        return data
    return None


def extract_audio_payload(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("audio", "audio_payload", "payload", "result"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return data


def scrub_secret_path(path: str | Path) -> str:
    return str(path)
