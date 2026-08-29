from __future__ import annotations

import base64
import math
import time
import uuid
from pathlib import Path
from typing import Any

from .media import inspect_media
from .result import ToolResult
from .run_context import RunContext, clean_env
from .speech_service import (
    audio_url_allowed,
    call_remote_speech_tool,
    extract_audio_payload,
    genericize_data,
    genericize_result,
    genericize_text,
    remote_speech_configured,
)


CLOUD_TTS_CREATE_PATH = "/api/v3/tts/create"
CLOUD_TTS_DEFAULT_FORMAT = "mp3"
CLOUD_TTS_FORMATS = {"wav", "mp3", "ogg_opus"}
CLOUD_TTS_SUFFIX_FORMATS = {"wav": "wav", "mp3": "mp3", "ogg": "ogg_opus", "opus": "ogg_opus"}
CLOUD_TTS_FORMAT_SUFFIXES = {"wav": "wav", "mp3": "mp3", "ogg_opus": "ogg"}
CLOUD_TTS_TEXT_MAX_CHARS = 3000
CLOUD_TTS_SPEECH_RATE_MIN = -50
CLOUD_TTS_SPEECH_RATE_MAX = 100
CLOUD_TTS_PITCH_RATE_MIN = -12
CLOUD_TTS_PITCH_RATE_MAX = 12
CLOUD_TTS_LEVEL_MIN = -50
CLOUD_TTS_LEVEL_MAX = 100
CLOUD_TTS_SAMPLE_RATES = {8000, 16000, 24000, 32000, 44100, 48000}
TTS_DEFAULT_RETRIES = 3
TTS_MAX_RETRIES = 10
TTS_RETRY_BACKOFF_SECONDS = 3.0


class CloudTTSCapabilityError(ValueError):
    """Compatibility cloud TTS capability limit, not a caller parameter error."""


def tts_generate(args: dict, ctx: RunContext) -> ToolResult:
    """Compatibility wrapper. Paid TTS is exposed as speech_synthesize."""
    return speech_synthesize(args, ctx)


def speech_synthesize(args: dict, ctx: RunContext) -> ToolResult:
    if not str(args.get("text") or "").strip():
        return ToolResult(text="[ERROR] text is required")
    sample_mode = args.get("sample_mode", False)
    if not isinstance(sample_mode, bool):
        return ToolResult(text="[ERROR] sample_mode must be a boolean")
    speed = coerce_finite_number(args.get("speed")) if args.get("speed") is not None else None
    if args.get("speed") is not None and speed is None:
        return ToolResult(text="[ERROR] speed must be numeric")
    if speed is not None and speed <= 0:
        return ToolResult(text="[ERROR] speed must be a finite number > 0")
    if "allowed_providers" in args and args.get("allowed_providers") is not None:
        allowed = args["allowed_providers"]
    else:
        allowed = []
    if not isinstance(allowed, list):
        return ToolResult(text="[ERROR] allowed_providers must be an array of provider names")
    if any(not isinstance(provider, str) for provider in allowed):
        return ToolResult(text="[ERROR] allowed_providers must contain only provider names as strings")
    preferred = args.get("preferred_provider") or clean_env("VE_DEFAULT_TTS_PROVIDER") or "auto"
    try:
        candidates = provider_candidates(preferred, allowed)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}")
    retries = coerce_retry_count(args.get("retries", args.get("retry_count")))
    if isinstance(retries, ToolResult):
        return retries
    retry_backoff = (
        coerce_finite_number(args.get("retry_backoff_seconds"))
        if args.get("retry_backoff_seconds") is not None
        else TTS_RETRY_BACKOFF_SECONDS
    )
    if retry_backoff is None or retry_backoff < 0:
        return ToolResult(text="[ERROR] retry_backoff_seconds must be a finite number >= 0")
    reasons = []
    started = time.time()
    for provider in candidates:
        attempts = []
        result = ToolResult(text=f"[ERROR] unsupported provider: {provider}")
        for attempt in range(retries + 1):
            result = call_tts_provider(provider, args, ctx, sample_mode=sample_mode)
            if not result.text.startswith("[ERROR]"):
                result.data.setdefault("selected_provider", provider)
                result.data["alternatives_considered"] = candidates
                result.data["selection_reason"] = f"selected first available provider: {provider}"
                result.data["retry_attempts"] = attempt
                result.data["max_retries"] = retries
                result.data["elapsed_seconds"] = round(time.time() - started, 3)
                return result
            attempts.append({
                "attempt": attempt + 1,
                "error": result.text,
                "retryable": tts_error_retryable(result),
            })
            if result.data.get("param_error"):
                break
            if not tts_error_retryable(result) or attempt >= retries:
                break
            time.sleep(float(retry_backoff) * (2 ** attempt))
        if result.data.get("param_error"):
            # 调用方参数错误 (格式/后缀冲突等) 必须硬失败，不能被重试掩盖。
            result.data["attempts"] = attempts
            return result
        reasons.append({"provider": provider, "error": result.text, "attempts": attempts})
    return ToolResult(
        text="[ERROR] cloud_tts unavailable",
        data={"candidates": candidates, "failures": reasons},
    )


def call_tts_provider(provider: str, args: dict, ctx: RunContext, *, sample_mode: bool) -> ToolResult:
    if provider == "edge_tts":
        from .edge_tts_provider import edge_tts_tts
        return edge_tts_tts(args, ctx, sample_mode=sample_mode)
    if provider == "cloud_tts":
        if remote_speech_configured():
            return remote_speech_synthesize(args, ctx, sample_mode=sample_mode)
        from .zcode_speech import zcode_speech_status

        if zcode_speech_status(ctx)["available"]:
            return zcode_official_speech_synthesize(args, ctx, sample_mode=sample_mode)
        return genericize_result(cloud_tts_tts(args, ctx, sample_mode=sample_mode))
    return ToolResult(text=f"[ERROR] unsupported provider: {provider}", data={"param_error": True})


def coerce_retry_count(value: object) -> int | ToolResult:
    if value is None:
        return TTS_DEFAULT_RETRIES
    if isinstance(value, bool):
        return ToolResult(text="[ERROR] retries must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return ToolResult(text="[ERROR] retries must be an integer")
    try:
        raw = float(value)
    except (TypeError, ValueError):
        raw = float(parsed)
    if not math.isfinite(raw) or raw != parsed:
        return ToolResult(text="[ERROR] retries must be an integer")
    if parsed < 0 or parsed > TTS_MAX_RETRIES:
        return ToolResult(text=f"[ERROR] retries must be in [0, {TTS_MAX_RETRIES}]")
    return parsed


def tts_error_retryable(result: ToolResult) -> bool:
    if result.data.get("param_error"):
        return False
    if result.data.get("retryable") is True:
        return True
    if result.data.get("retryable") is False:
        return False
    text = result.text.lower()
    non_retryable = [
        "not set",
        "not available",
        "package unavailable",
        "command not found",
        "unsupported",
        "only outputs",
        "suffix",
        "text_prompt exceeds",
        "must be",
        "conflict",
    ]
    if any(marker in text for marker in non_retryable):
        return False
    return message_retryable(text)


def http_retryable(status_code: int, body: str = "") -> bool:
    if status_code in {408, 409, 425, 429} or 500 <= status_code <= 599:
        return True
    return message_retryable(body)


def message_retryable(message: object) -> bool:
    text = str(message or "").lower()
    retry_markers = [
        "429",
        "too many",
        "rate limit",
        "ratelimit",
        "concurrency",
        "concurrent",
        "busy",
        "throttl",
        "temporar",
        "timeout",
        "timed out",
        "try again",
        "server error",
        "service unavailable",
        "gateway",
        "connection",
        "reset",
    ]
    return any(marker in text for marker in retry_markers)


def provider_candidates(preferred: str, allowed: list[str]) -> list[str]:
    aliases = {
        "auto": "auto",
        "cloud": "cloud_tts",
        "cloud_tts": "cloud_tts",
        "remote": "cloud_tts",
        "speech": "cloud_tts",
        "edge": "edge_tts",
        "edge_tts": "edge_tts",
    }
    # WorkBuddy 迁移后无 ZCode 鉴权, edge_tts (免费免key) 优先, cloud_tts 兜底
    base = ["edge_tts", "cloud_tts"]
    allowed_set: set[str] | None = None
    if allowed:
        raw_allowed = {str(p).strip().lower() for p in allowed}
        unknown = sorted(raw_allowed - set(aliases))
        allowed_set = {aliases[p] for p in raw_allowed if p in aliases}
        if unknown:
            raise ValueError(f"unknown TTS backend(s) in allowed_providers: {', '.join(unknown)}")
        base = [p for p in base if p in allowed_set]
    preferred = str(preferred or "auto").strip().lower()
    if preferred not in aliases:
        raise ValueError(f"unknown preferred_provider: {preferred}")
    preferred_norm = aliases[preferred]
    if preferred_norm != "auto" and allowed_set is not None and preferred_norm not in allowed_set:
        raise ValueError(
            f"preferred_provider {preferred} is not in allowed_providers; "
            "align the two settings instead of relying on a silent substitution"
        )
    if preferred_norm and preferred_norm != "auto" and preferred_norm in base:
        return [preferred_norm] + [p for p in base if p != preferred_norm]
    return base


def coerce_finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def output_path_for(args: dict, ctx: RunContext, provider: str, ext: str) -> Path:
    if args.get("output_path"):
        return ctx.resolve(args["output_path"])
    return ctx.output_dir / f"tts_{provider}_{time.time_ns()}.{ext}"


def remote_speech_synthesize(args: dict, ctx: RunContext, *, sample_mode: bool) -> ToolResult:
    try:
        audio_format = cloud_tts_output_format(args)
        output_path = cloud_tts_output_path_for(args, ctx, audio_format)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}", data={"provider": "cloud_tts", "param_error": True})
    remote_args = {
        key: value
        for key, value in args.items()
        if key not in {"output_path", "allowed_providers", "preferred_provider"}
    }
    remote_args["output_format"] = audio_format
    remote_args["sample_mode"] = sample_mode
    result = call_remote_speech_tool("synthesize", remote_args, timeout=300.0)
    if result.text.startswith("[ERROR]"):
        return result
    payload = extract_audio_payload(result.data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    saved = save_cloud_tts_result(payload, output_path)
    if isinstance(saved, ToolResult):
        return saved
    extra = {
        "remote_mcp": True,
        "output_format": audio_format,
        **{
            k: v
            for k, v in result.data.items()
            if k not in {
                "audio",
                "audio_base64",
                "audio_payload",
                "audio_url",
                "content",
                "data",
                "payload",
                "result",
                "url",
            }
        },
    }
    return finish_tts(ctx, output_path, "cloud_tts", genericize_data(extra))


def cloud_tts_output_path_for(args: dict, ctx: RunContext, audio_format: str) -> Path:
    output_path = output_path_for(args, ctx, "cloud_tts", CLOUD_TTS_FORMAT_SUFFIXES[audio_format])
    if not args.get("output_path"):
        return output_path
    suffix = output_path.suffix.lower().lstrip(".")
    suffix_format = CLOUD_TTS_SUFFIX_FORMATS.get(suffix)
    if suffix and suffix_format is None:
        allowed = ", ".join(f".{ext}" for ext in sorted(CLOUD_TTS_SUFFIX_FORMATS))
        raise ValueError(f"cloud_tts output_path suffix must be one of: {allowed}")
    if suffix_format is not None and suffix_format != audio_format:
        raise ValueError(
            f"cloud_tts output_path suffix .{suffix} conflicts with output_format={audio_format}"
        )
    return output_path


def zcode_official_speech_synthesize(
    args: dict, ctx: RunContext, *, sample_mode: bool
) -> ToolResult:
    """Use host-injected ZCode identity behind the generic cloud_tts surface."""
    from . import zcode_speech as zs

    try:
        audio_format = cloud_tts_output_format(args)
        text = sample_text(args) if sample_mode else str(args["text"]).strip()
        if len(text) > CLOUD_TTS_TEXT_MAX_CHARS:
            raise CloudTTSCapabilityError(
                f"cloud_tts text exceeds {CLOUD_TTS_TEXT_MAX_CHARS} characters"
            )
        speech_rate = cloud_tts_speech_rate(args)
        sample_rate = cloud_tts_sample_rate(args)
        pitch_rate = cloud_tts_int_range(
            args.get("pitch_rate"), "pitch_rate",
            CLOUD_TTS_PITCH_RATE_MIN, CLOUD_TTS_PITCH_RATE_MAX, 0,
        )
        loudness_rate = cloud_tts_int_range(
            args.get("loudness_rate"), "loudness_rate",
            CLOUD_TTS_LEVEL_MIN, CLOUD_TTS_LEVEL_MAX, 0,
        )
        output_path = cloud_tts_output_path_for(args, ctx, audio_format)
    except CloudTTSCapabilityError as exc:
        return ToolResult(text=f"[ERROR] {exc}", data={"provider": "cloud_tts"})
    except ValueError as exc:
        return ToolResult(
            text=f"[ERROR] {exc}", data={"provider": "cloud_tts", "param_error": True}
        )

    voice = next(
        (
            value
            for value in (
                args.get("speaker"), args.get("speaker_id"),
                args.get("voice_id"), args.get("voice"),
            )
            if value is not None and not isinstance(value, bool) and str(value).strip()
        ),
        None,
    )
    arguments = zs.synthesize_arguments(
        text=text,
        output_format=audio_format,
        voice=str(voice) if voice is not None else "",
        speed=0,
        speech_rate=speech_rate,
        pitch_rate=pitch_rate,
        loudness_rate=loudness_rate,
        sample_rate=sample_rate,
        model=str(args.get("model") or ""),
        style_instructions=str(args.get("style_instructions") or "").strip(),
        sample_mode=sample_mode,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data, call_meta = zs.call_speech_tool(zs.TOOL_SYNTHESIZE, arguments, ctx=ctx)
    except zs.ZCodeSpeechError as exc:
        return ToolResult(
            text=f"[ERROR] cloud_tts failed: {genericize_text(exc)}",
            data={
                "provider": "cloud_tts",
                "channel": "zcode_official",
                "retryable": bool(exc.detail.get("recoverable", True)),
                **genericize_data({k: v for k, v in exc.detail.items() if k != "recoverable"}),
            },
        )
    saved = zs.write_synthesized_audio(data, output_path)
    if isinstance(saved, ToolResult):
        return genericize_result(saved)
    return finish_tts(
        ctx,
        output_path,
        "cloud_tts",
        genericize_data({
            "channel": "zcode_official",
            "output_format": audio_format,
            "sample_rate": sample_rate,
            "speech_rate": speech_rate,
            "pitch_rate": pitch_rate,
            "loudness_rate": loudness_rate,
            "voice": str(voice) if voice is not None else None,
            **call_meta,
            "usage": data.get("usage"),
        }),
    )


def cloud_tts_config() -> dict[str, Any]:
    """Config for the direct-HTTP synthesis compatibility backend.

    Like cloud_asr, this backend ships no endpoint and no model default: it is a
    legacy escape hatch for deployments that bring their own speech service, and
    the kit does not name or presume a vendor. Under ZCode nothing here is needed
    — the official channel authenticates through host-injected identity.
    """
    api_key = clean_env(
        "VE_SPEECH_TTS_API_KEY",
        "VE_CLOUD_TTS_API_KEY",
        "VE_SPEECH_ASR_API_KEY",
        "VE_CLOUD_ASR_API_KEY",
    )
    from .run_context import check_endpoint
    endpoint, endpoint_error = check_endpoint(
        "VE_SPEECH_TTS_ENDPOINT", "VE_CLOUD_TTS_ENDPOINT",
    )
    return {
        "api_key": api_key,
        "endpoint": endpoint,
        "endpoint_error": endpoint_error,
        "model": clean_env("VE_SPEECH_TTS_MODEL", "VE_CLOUD_TTS_MODEL"),
        "speaker": clean_env("VE_SPEECH_TTS_VOICE", "VE_CLOUD_TTS_VOICE"),
    }


def cloud_tts_status() -> dict[str, Any]:
    cfg = cloud_tts_config()
    reasons: list[str] = []
    if cfg.get("endpoint_error"):
        reasons.append(cfg["endpoint_error"])
    if not cfg["model"]:
        reasons.append("VE_SPEECH_TTS_MODEL is not set")
    if not cfg["api_key"]:
        reasons.append("credentials not set (need VE_SPEECH_TTS_API_KEY)")
    try:
        import requests  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"requests package unavailable: {exc}")
    return {
        "available": not reasons,
        "reasons": reasons,
        "auth_mode": "api_key",
        "model": cfg["model"],
        "speaker_configured": bool(cfg["speaker"]),
    }


def cloud_tts_headers(cfg: dict[str, Any], request_id: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Api-Request-Id": request_id,
        "X-Api-Key": cfg["api_key"],
    }
    return headers


def cloud_tts_tts(args: dict, ctx: RunContext, *, sample_mode: bool) -> ToolResult:
    status = cloud_tts_status()
    if not status["available"]:
        return ToolResult(
            text="[ERROR] cloud_tts is not available: " + "; ".join(status["reasons"]),
            data={"provider": "cloud_tts", "status": status},
        )
    try:
        import requests
    except Exception as exc:
        return ToolResult(text=f"[ERROR] requests package unavailable: {exc}")

    cfg = cloud_tts_config()
    try:
        audio_format = cloud_tts_output_format(args)
        payload, payload_meta = cloud_tts_payload(args, cfg, audio_format, sample_mode=sample_mode)
    except CloudTTSCapabilityError as exc:
        # 能力上限 (文本长度等): 不标 param_error, 让链上其他 provider 接手
        return ToolResult(text=f"[ERROR] {exc}", data={"provider": "cloud_tts"})
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}", data={"provider": "cloud_tts", "param_error": True})

    try:
        output_path = cloud_tts_output_path_for(args, ctx, audio_format)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}", data={"provider": "cloud_tts", "param_error": True})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    request_id = str(uuid.uuid4())
    try:
        resp = requests.post(
            cfg["endpoint"] + CLOUD_TTS_CREATE_PATH,
            headers=cloud_tts_headers(cfg, request_id),
            json=payload,
            timeout=300,
        )
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            text=f"[ERROR] cloud_tts failed: {exc}",
            data={"provider": "cloud_tts", "request_id": request_id, "retryable": True, **payload_meta},
        )

    logid = str(resp.headers.get("X-Tt-Logid") or "")
    if resp.status_code >= 400:
        return ToolResult(
            text=f"[ERROR] cloud_tts failed: {resp.status_code} {genericize_text(resp.text[:500])}",
            data={
                "provider": "cloud_tts",
                "request_id": request_id,
                "logid": logid,
                "retryable": http_retryable(resp.status_code, resp.text),
                **payload_meta,
            },
        )
    try:
        result = resp.json() or {}
    except ValueError as exc:
        return ToolResult(
            text=f"[ERROR] cloud_tts returned non-JSON body: {exc}",
            data={"provider": "cloud_tts", "request_id": request_id, "logid": logid, "retryable": True, **payload_meta},
        )
    code = result.get("code")
    if code not in (None, 0):
        return ToolResult(
            text=f"[ERROR] cloud_tts failed: {code} {genericize_text(result.get('message') or '')}".rstrip(),
            data={
                "provider": "cloud_tts",
                "request_id": request_id,
                "logid": logid,
                "code": code,
                "message": genericize_text(result.get("message") or ""),
                "retryable": message_retryable(f"{code} {result.get('message') or ''}"),
                **payload_meta,
            },
        )

    saved = save_cloud_tts_result(result, output_path)
    if isinstance(saved, ToolResult):
        saved.data.update({"request_id": request_id, "logid": logid, **payload_meta})
        return saved

    extra = {
        "model": payload_meta["model"],
        "request_id": request_id,
        "logid": logid,
        "service_duration_seconds": result.get("duration"),
        "service_original_duration_seconds": result.get("original_duration"),
        **payload_meta,
    }
    if isinstance(result.get("subtitle"), dict):
        extra["subtitle"] = result["subtitle"]
    return finish_tts(ctx, output_path, "cloud_tts", extra)


def cloud_tts_output_format(args: dict) -> str:
    fmt = str(args.get("format") or "").strip().lower()
    out_fmt = str(args.get("output_format") or "").strip().lower()
    if fmt and out_fmt and fmt != out_fmt:
        # 两个别名字段冲突不能静默取其一
        raise ValueError(f"output_format={out_fmt} conflicts with format={fmt}; provide only one")
    requested = out_fmt or fmt
    if not requested and args.get("output_path"):
        suffix = Path(str(args["output_path"])).suffix.lower().lstrip(".")
        requested = CLOUD_TTS_SUFFIX_FORMATS.get(suffix, suffix)
    audio_format = requested or CLOUD_TTS_DEFAULT_FORMAT
    if audio_format not in CLOUD_TTS_FORMATS:
        raise ValueError(
            f"unsupported cloud_tts output format: {audio_format}; "
            "expected wav, mp3, or ogg_opus"
        )
    return audio_format


def cloud_tts_output_path_for(args: dict, ctx: RunContext, audio_format: str) -> Path:
    output_path = output_path_for(args, ctx, "cloud_tts", CLOUD_TTS_FORMAT_SUFFIXES[audio_format])
    if not args.get("output_path"):
        return output_path
    suffix = output_path.suffix.lower().lstrip(".")
    suffix_format = CLOUD_TTS_SUFFIX_FORMATS.get(suffix)
    if suffix and suffix_format is None:
        allowed = ", ".join(f".{ext}" for ext in sorted(CLOUD_TTS_SUFFIX_FORMATS))
        raise ValueError(f"cloud_tts output_path suffix must be one of: {allowed}")
    if suffix_format is not None and suffix_format != audio_format:
        raise ValueError(
            f"cloud_tts output_path suffix .{suffix} conflicts with output_format={audio_format}"
        )
    return output_path


def cloud_tts_payload(
    args: dict,
    cfg: dict[str, Any],
    audio_format: str,
    *,
    sample_mode: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    text_prompt = cloud_tts_text_prompt(args, sample_mode=sample_mode)
    if len(text_prompt) > CLOUD_TTS_TEXT_MAX_CHARS:
        raise CloudTTSCapabilityError(
            f"cloud_tts text_prompt exceeds {CLOUD_TTS_TEXT_MAX_CHARS} characters"
        )

    audio_config: dict[str, Any] = {
        "format": audio_format,
        "sample_rate": cloud_tts_sample_rate(args),
        "pitch_rate": cloud_tts_int_range(
            args.get("pitch_rate"),
            "pitch_rate",
            CLOUD_TTS_PITCH_RATE_MIN,
            CLOUD_TTS_PITCH_RATE_MAX,
            0,
        ),
        "speech_rate": cloud_tts_speech_rate(args),
        "loudness_rate": cloud_tts_int_range(
            args.get("loudness_rate"),
            "loudness_rate",
            CLOUD_TTS_LEVEL_MIN,
            CLOUD_TTS_LEVEL_MAX,
            0,
        ),
    }
    if "enable_subtitle" in args and args.get("enable_subtitle") is not None:
        if not isinstance(args["enable_subtitle"], bool):
            raise ValueError("enable_subtitle must be a boolean")
        audio_config["enable_subtitle"] = args["enable_subtitle"]

    payload: dict[str, Any] = {
        "model": str(args.get("model") or cfg["model"]),
        "text_prompt": text_prompt,
        "audio_config": audio_config,
        "watermark": {},
    }
    # 逐个取第一个可用值而非 or 链: 数字音色 ID 0 是合法值, or 链会把它当
    # falsy 吞掉静默回退 env 配置; 布尔值 (CLI 裸 flag 解析产物) 不是音色。
    speaker = next(
        (
            v
            for v in (
                args.get("speaker"),
                args.get("speaker_id"),
                args.get("voice_id"),
                args.get("voice"),
                cfg.get("speaker"),
            )
            if v is not None and not isinstance(v, bool) and str(v).strip() != ""
        ),
        None,
    )
    if speaker is not None:
        payload["references"] = [{"speaker": str(speaker)}]
    meta = {
        "model": payload["model"],
        "output_format": audio_format,
        "sample_rate": audio_config["sample_rate"],
        "speech_rate": audio_config["speech_rate"],
        "pitch_rate": audio_config["pitch_rate"],
        "loudness_rate": audio_config["loudness_rate"],
        "speaker": str(speaker) if speaker is not None else None,
    }
    requested_speed = args.get("speed")
    if requested_speed is not None:
        meta["requested_speed"] = float(requested_speed)
        meta["applied_speed"] = round(1.0 + (audio_config["speech_rate"] / 100.0), 3)
        # 只有换算值真被截断才算 clamp: speed=0.5 恰好等于下界 -50, 按
        # "值 ∈ {MIN, MAX}" 判定会误报
        if args.get("speech_rate") is None:
            raw_rate = round((float(requested_speed) - 1.0) * 100)
            if raw_rate != audio_config["speech_rate"]:
                meta["speed_note"] = (
                    f"speed clamped to cloud_tts speech_rate range "
                    f"[{CLOUD_TTS_SPEECH_RATE_MIN}, {CLOUD_TTS_SPEECH_RATE_MAX}]"
                )
    return payload, meta


def cloud_tts_text_prompt(args: dict, *, sample_mode: bool) -> str:
    text = sample_text(args) if sample_mode else str(args["text"]).strip()
    instructions = str(args.get("style_instructions") or "").strip()
    if instructions:
        return f"{instructions}\n{text}"
    return text


def cloud_tts_sample_rate(args: dict) -> int:
    if args.get("sample_rate") is None:
        return 48000
    value = coerce_finite_number(args.get("sample_rate"))
    if value is None or int(value) != value:
        raise ValueError("sample_rate must be an integer")
    sample_rate = int(value)
    if sample_rate not in CLOUD_TTS_SAMPLE_RATES:
        allowed = ", ".join(str(v) for v in sorted(CLOUD_TTS_SAMPLE_RATES))
        raise ValueError(f"sample_rate must be one of: {allowed}")
    return sample_rate


def cloud_tts_speech_rate(args: dict) -> int:
    if args.get("speech_rate") is not None:
        return cloud_tts_int_range(
            args.get("speech_rate"),
            "speech_rate",
            CLOUD_TTS_SPEECH_RATE_MIN,
            CLOUD_TTS_SPEECH_RATE_MAX,
            0,
        )
    if args.get("speed") is None:
        return 0
    speed = float(args["speed"])
    return min(max(round((speed - 1.0) * 100), CLOUD_TTS_SPEECH_RATE_MIN), CLOUD_TTS_SPEECH_RATE_MAX)


def cloud_tts_int_range(value: object, name: str, min_value: int, max_value: int, default: int) -> int:
    if value is None:
        return default
    parsed = coerce_finite_number(value)
    if parsed is None or int(parsed) != parsed:
        raise ValueError(f"{name} must be an integer")
    intval = int(parsed)
    if intval < min_value or intval > max_value:
        raise ValueError(f"{name} must be in [{min_value}, {max_value}]")
    return intval


def save_cloud_tts_result(result: dict[str, Any], output_path: Path) -> Path | ToolResult:
    audio_base64 = (
        result.get("audio_base64")
        or result.get("audio")
        or result.get("data")
        or result.get("content")
    )
    if isinstance(audio_base64, str) and audio_base64.strip():
        try:
            output_path.write_bytes(base64.b64decode(audio_base64))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                text=f"[ERROR] cloud_tts returned invalid base64 audio: {exc}",
                data={"provider": "cloud_tts", "output_path": str(output_path), "retryable": True},
            )
        return output_path

    audio_url = result.get("url") or result.get("audio_url")
    if isinstance(audio_url, str) and audio_url.strip():
        if not audio_url_allowed(audio_url):
            return ToolResult(
                text="[ERROR] cloud_tts returned an audio URL outside the configured remote MCP host",
                data={
                    "provider": "cloud_tts",
                    "output_path": str(output_path),
                    "retryable": False,
                },
            )
        try:
            import requests

            resp = requests.get(audio_url, timeout=300, allow_redirects=False)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                text=f"[ERROR] cloud_tts audio URL download failed: {exc}",
                data={"provider": "cloud_tts", "output_path": str(output_path), "retryable": True},
            )
        if resp.status_code >= 400:
            return ToolResult(
                text=f"[ERROR] cloud_tts audio URL download failed: {resp.status_code} {resp.text[:500]}",
                data={
                    "provider": "cloud_tts",
                    "output_path": str(output_path),
                    "retryable": http_retryable(resp.status_code, resp.text),
                },
            )
        output_path.write_bytes(resp.content)
        return output_path

    return ToolResult(
        text="[ERROR] cloud_tts response contained neither audio base64 nor url",
        data={
            "provider": "cloud_tts",
            "output_path": str(output_path),
            "response_keys": sorted(result.keys()),
            "retryable": True,
        },
    )


def save_cloud_tts_result(result: dict[str, Any], output_path: Path) -> Path | ToolResult:
    audio_base64 = result.get("audio") or result.get("data")
    if isinstance(audio_base64, str) and audio_base64.strip():
        try:
            output_path.write_bytes(base64.b64decode(audio_base64))
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                text=f"[ERROR] cloud_tts returned invalid base64 audio: {exc}",
                data={"provider": "cloud_tts", "output_path": str(output_path)},
            )
        return output_path

    audio_url = result.get("url")
    if isinstance(audio_url, str) and audio_url.strip():
        from .run_context import is_allowed_host
        if not is_allowed_host(audio_url, cloud_tts_config().get("endpoint")):
            return ToolResult(
                text=(
                    "[ERROR] cloud_tts returned an audio URL outside the configured "
                    "speech endpoint origin; refusing to fetch"
                ),
                data={"provider": "cloud_tts", "output_path": str(output_path),
                      "retryable": False},
            )
        try:
            import requests

            resp = requests.get(audio_url, timeout=300, allow_redirects=False)
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                text=f"[ERROR] cloud_tts audio URL download failed: {exc}",
                data={"provider": "cloud_tts", "output_path": str(output_path), "retryable": True},
            )
        if resp.status_code >= 400:
            return ToolResult(
                text=f"[ERROR] cloud_tts audio URL download failed: {resp.status_code} {genericize_text(resp.text[:500])}",
                data={
                    "provider": "cloud_tts",
                    "output_path": str(output_path),
                    "retryable": http_retryable(resp.status_code, resp.text),
                },
            )
        output_path.write_bytes(resp.content)
        return output_path

    return ToolResult(
        text="[ERROR] cloud_tts response contained neither audio/data base64 nor url",
        data={"provider": "cloud_tts", "output_path": str(output_path), "response_keys": sorted(result.keys()), "retryable": True},
    )


def sample_text(args: dict) -> str:
    text = str(args["text"]).strip()
    return text[: min(len(text), 260)]


def finish_tts(ctx: RunContext, output_path: Path, provider: str, extra: dict) -> ToolResult:
    probe = inspect_media({
        "input_path": str(output_path),
        "output_json": str(ctx.output_dir / f"{output_path.stem}_media.json"),
    }, ctx)
    if probe.text.startswith("[ERROR]"):
        return ToolResult(
            text=f"[ERROR] TTS generated with {provider}, but media probe failed: {probe.text}",
            data={"provider": provider, "output_path": str(output_path), "probe_error": probe.text, **extra},
            artifacts=[str(output_path)],
        )
    duration = probe.data.get("duration_seconds")
    if not isinstance(duration, (int, float)) or not math.isfinite(float(duration)) or float(duration) <= 0:
        return ToolResult(
            text=f"[ERROR] TTS generated with {provider}, but ffprobe did not return a valid audio duration",
            data={
                "provider": provider,
                "output_path": str(output_path),
                "audio_duration_seconds": duration,
                "media": probe.data,
                **extra,
            },
            artifacts=[str(output_path)],
        )
    data = {
        "provider": provider,
        "output_path": str(output_path),
        "audio_duration_seconds": float(duration),
        "format": output_path.suffix.lstrip("."),
        **extra,
    }
    return ToolResult(
        text=f"TTS generated with {provider}: {ctx.virtualize(output_path)}",
        data=data,
        artifacts=[str(output_path)],
    )
