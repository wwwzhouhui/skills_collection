"""edge_tts provider: 免费的微软 Edge 在线语音合成。

替代 cloud_tts / zcode_official 通道: 不需要 API key、不需要 ZCode 宿主鉴权,
用微软 Edge 的免费 TTS 服务 (edge-tts 库) 直接合成 mp3。

参数映射 (与 speech_synthesize 标准参数对齐):
  - voice/speaker/speaker_id/voice_id -> edge-tts voice (默认 zh-CN-XiaoxiaoNeural)
  - speech_rate (-50..100) 或 speed  -> edge-tts rate ("+10%")
  - pitch_rate  (-12..12)            -> edge-tts pitch ("+3Hz")
  - loudness_rate (-50..100)         -> edge-tts volume ("-10%")
  - output_format / format           -> mp3 (原生) / wav / ogg_opus (ffmpeg 转码)
  - sample_rate                      -> 仅对非 mp3 生效 (ffmpeg 重采样)

限制:
  - 单次文本 <= 3000 字符 (与 cloud_tts 一致)
  - 需要网络可达微软 Edge TTS 服务; 偶发限流, 上层重试机制已覆盖
"""
from __future__ import annotations

import asyncio
import math
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from .media import inspect_media
from .result import ToolResult
from .run_context import RunContext, clean_env

EDGE_TTS_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
EDGE_TTS_TEXT_MAX_CHARS = 3000
EDGE_TTS_FORMATS = {"wav", "mp3", "ogg_opus"}
EDGE_TTS_SUFFIX_FORMATS = {"wav": "wav", "mp3": "mp3", "ogg": "ogg_opus", "opus": "ogg_opus"}
EDGE_TTS_FORMAT_SUFFIXES = {"wav": "wav", "mp3": "mp3", "ogg_opus": "ogg"}
EDGE_TTS_SAMPLE_RATES = {8000, 16000, 24000, 32000, 44100, 48000}
EDGE_TTS_CALL_TIMEOUT = 300.0

# 常见中文音色白名单提示 (仅用于报错信息, 不限制实际传入)
_ZH_VOICE_HINTS = [
    "zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunxiNeural",
    "zh-CN-YunjianNeural", "zh-CN-XiaoyouNeural", "zh-CN-YunyangNeural",
    "zh-TW-HsiaoChenNeural", "zh-TW-HsiaoYuNeural", "zh-HK-HiuMaanNeural",
    "zh-HK-HiuGaaiNeural", "zh-CN-liaoning-XiaobeiNeural", "zh-CN-shaanxi-XiaoniNeural",
]


class EdgeTTSCapabilityError(ValueError):
    """edge-tts 能力上限 (文本过长等), 非调用方参数错误。"""


def edge_tts_status() -> dict[str, Any]:
    """能力探测, 与 cloud_tts_status() 同构。"""
    reasons: list[str] = []
    try:
        import edge_tts  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"edge_tts package unavailable: {exc}")
    voice = clean_env("VE_EDGE_TTS_VOICE")
    if voice:
        reasons.append(f"bad voice name: {voice}")  # placeholder; 实际由调用时校验
        reasons.pop()  # voice 名不在此预检, 运行时报错更准
    return {
        "available": not reasons,
        "reasons": reasons,
        "provider": "edge_tts",
        "default_voice": EDGE_TTS_DEFAULT_VOICE,
    }


def edge_tts_tts(args: dict, ctx: RunContext, *, sample_mode: bool) -> ToolResult:
    """speech_synthesize 的 edge_tts provider 实现。"""
    try:
        import edge_tts  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            text=f"[ERROR] edge_tts package unavailable: {exc}",
            data={"provider": "edge_tts", "retryable": False},
        )
    try:
        text = _edge_tts_text(args, sample_mode=sample_mode)
        audio_format = _edge_tts_output_format(args)
        voice = _edge_tts_voice(args)
        rate = _edge_tts_rate(args)
        pitch = _edge_tts_pitch(args)
        volume = _edge_tts_volume(args)
        sample_rate = _edge_tts_sample_rate(args)
        output_path = _edge_tts_output_path(args, ctx, audio_format)
    except EdgeTTSCapabilityError as exc:
        return ToolResult(text=f"[ERROR] {exc}", data={"provider": "edge_tts"})
    except ValueError as exc:
        return ToolResult(
            text=f"[ERROR] {exc}", data={"provider": "edge_tts", "param_error": True}
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    native_path = output_path
    transcode_format = None
    if audio_format != "mp3":
        # edge-tts 原生只出 mp3; 其他格式先存临时 mp3, 再 ffmpeg 转码
        native_path = output_path.with_suffix(".mp3")
        transcode_format = audio_format

    started = time.time()
    err = _run_edge_tts_sync(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
        output_path=native_path,
    )
    if err is not None:
        return ToolResult(
            text=f"[ERROR] edge_tts failed: {err}",
            data={"provider": "edge_tts", "voice": voice, "retryable": _retryable_error(err)},
        )

    if transcode_format is not None:
        res = _transcode(native_path, output_path, audio_format, sample_rate)
        if isinstance(res, str):
            return ToolResult(
                text=f"[ERROR] edge_tts transcode failed: {res}",
                data={"provider": "edge_tts", "retryable": False},
            )
        try:
            native_path.unlink(missing_ok=True)
        except OSError:
            pass

    probe = inspect_media({
        "input_path": str(output_path),
        "output_json": str(ctx.output_dir / f"{output_path.stem}_media.json"),
    }, ctx)
    if probe.text.startswith("[ERROR]"):
        return ToolResult(
            text=f"[ERROR] edge_tts generated, but media probe failed: {probe.text}",
            data={"provider": "edge_tts", "output_path": str(output_path),
                  "probe_error": probe.text},
            artifacts=[str(output_path)],
        )
    duration = probe.data.get("duration_seconds")
    if not isinstance(duration, (int, float)) or not math.isfinite(float(duration)) or float(duration) <= 0:
        return ToolResult(
            text=f"[ERROR] edge_tts generated, but ffprobe did not return a valid audio duration",
            data={"provider": "edge_tts", "output_path": str(output_path),
                  "audio_duration_seconds": duration, "media": probe.data},
            artifacts=[str(output_path)],
        )
    extra = {
        "voice": voice,
        "output_format": audio_format,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "sample_rate": sample_rate,
        "channel": "edge_tts",
        "elapsed_seconds": round(time.time() - started, 3),
    }
    data = {
        "provider": "edge_tts",
        "output_path": str(output_path),
        "audio_duration_seconds": float(duration),
        "format": output_path.suffix.lstrip("."),
        **extra,
    }
    return ToolResult(
        text=f"TTS generated with edge_tts: {ctx.virtualize(output_path)}",
        data=data,
        artifacts=[str(output_path)],
    )


# ---------------------------------------------------------------------------
# 参数解析
# ---------------------------------------------------------------------------

def _edge_tts_text(args: dict, *, sample_mode: bool) -> str:
    text = str(args.get("text") or "").strip()
    if not text:
        raise ValueError("text is required")
    if sample_mode:
        text = text[: min(len(text), 260)]
    if len(text) > EDGE_TTS_TEXT_MAX_CHARS:
        raise EdgeTTSCapabilityError(
            f"edge_tts text exceeds {EDGE_TTS_TEXT_MAX_CHARS} characters"
        )
    instructions = str(args.get("style_instructions") or "").strip()
    if instructions:
        return f"{instructions}\n{text}"
    return text


def _edge_tts_output_format(args: dict) -> str:
    fmt = str(args.get("format") or "").strip().lower()
    out_fmt = str(args.get("output_format") or "").strip().lower()
    if fmt and out_fmt and fmt != out_fmt:
        raise ValueError(f"output_format={out_fmt} conflicts with format={fmt}; provide only one")
    requested = out_fmt or fmt
    if not requested and args.get("output_path"):
        suffix = Path(str(args["output_path"])).suffix.lower().lstrip(".")
        requested = EDGE_TTS_SUFFIX_FORMATS.get(suffix, suffix)
    audio_format = requested or "mp3"
    if audio_format not in EDGE_TTS_FORMATS:
        raise ValueError(
            f"unsupported edge_tts output format: {audio_format}; "
            "expected wav, mp3, or ogg_opus"
        )
    return audio_format


def _edge_tts_output_path(args: dict, ctx: RunContext, audio_format: str) -> Path:
    if args.get("output_path"):
        output_path = ctx.resolve(args["output_path"])
        suffix = output_path.suffix.lower().lstrip(".")
        suffix_format = EDGE_TTS_SUFFIX_FORMATS.get(suffix)
        if suffix and suffix_format is None:
            allowed = ", ".join(f".{ext}" for ext in sorted(EDGE_TTS_SUFFIX_FORMATS))
            raise ValueError(f"edge_tts output_path suffix must be one of: {allowed}")
        if suffix_format is not None and suffix_format != audio_format:
            raise ValueError(
                f"edge_tts output_path suffix .{suffix} conflicts with output_format={audio_format}"
            )
        return output_path
    return ctx.output_dir / f"tts_edge_tts_{time.time_ns()}.{EDGE_TTS_FORMAT_SUFFIXES[audio_format]}"


def _edge_tts_voice(args: dict) -> str:
    voice = next(
        (
            v
            for v in (
                args.get("speaker"), args.get("speaker_id"),
                args.get("voice_id"), args.get("voice"),
            )
            if v is not None and not isinstance(v, bool) and str(v).strip()
        ),
        None,
    )
    if voice is not None:
        return str(voice)
    return clean_env("VE_EDGE_TTS_VOICE") or EDGE_TTS_DEFAULT_VOICE


def _edge_tts_rate(args: dict) -> str:
    if args.get("speech_rate") is not None:
        rate_int = _int_range(args.get("speech_rate"), "speech_rate", -50, 100, 0)
    elif args.get("speed") is not None:
        speed = _finite(args.get("speed"), "speed")
        if speed <= 0:
            raise ValueError("speed must be a finite number > 0")
        rate_int = min(max(round((speed - 1.0) * 100), -50), 100)
    else:
        rate_int = 0
    return f"{rate_int:+d}%"


def _edge_tts_pitch(args: dict) -> str:
    pitch = _int_range(args.get("pitch_rate"), "pitch_rate", -12, 12, 0)
    return f"{pitch:+d}Hz"


def _edge_tts_volume(args: dict) -> str:
    volume = _int_range(args.get("loudness_rate"), "loudness_rate", -50, 100, 0)
    return f"{volume:+d}%"


def _edge_tts_sample_rate(args: dict) -> int:
    if args.get("sample_rate") is None:
        return 24000  # edge-tts 原生输出
    value = _finite(args.get("sample_rate"), "sample_rate")
    if int(value) != value:
        raise ValueError("sample_rate must be an integer")
    sample_rate = int(value)
    if sample_rate not in EDGE_TTS_SAMPLE_RATES:
        allowed = ", ".join(str(v) for v in sorted(EDGE_TTS_SAMPLE_RATES))
        raise ValueError(f"sample_rate must be one of: {allowed}")
    return sample_rate


def _int_range(value: object, name: str, min_value: int, max_value: int, default: int) -> int:
    if value is None:
        return default
    parsed = _finite(value, name)
    if int(parsed) != parsed:
        raise ValueError(f"{name} must be an integer")
    intval = int(parsed)
    if intval < min_value or intval > max_value:
        raise ValueError(f"{name} must be in [{min_value}, {max_value}]")
    return intval


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be finite")
    return parsed


# ---------------------------------------------------------------------------
# edge-tts 调用 (同步包装: MCP server 是同步 call_tool)
# ---------------------------------------------------------------------------

def _run_edge_tts_sync(
    *,
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
    output_path: Path,
) -> str | None:
    """在独立线程 + 事件循环里跑 edge-tts (异步库), 返回 None 或错误消息。"""
    box: dict[str, Any] = {}

    def worker() -> None:
        try:
            import edge_tts
        except Exception as exc:  # noqa: BLE001
            box["error"] = f"edge_tts package unavailable: {exc}"
            return
        try:
            communicate = edge_tts.Communicate(
                text, voice, rate=rate, volume=volume, pitch=pitch
            )
            asyncio.run(communicate.save(str(output_path)))
            box["ok"] = True
        except Exception as exc:  # noqa: BLE001
            box["error"] = f"{type(exc).__name__}: {exc}"

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=EDGE_TTS_CALL_TIMEOUT)
    if thread.is_alive():
        return f"timed out after {EDGE_TTS_CALL_TIMEOUT:.0f}s"
    if box.get("ok"):
        return None
    return str(box.get("error") or "unknown error")


def _retryable_error(message: str) -> bool:
    text = str(message or "").lower()
    markers = [
        "429", "too many", "rate limit", "ratelimit", "concurrency",
        "busy", "throttl", "temporar", "timeout", "timed out",
        "try again", "server error", "service unavailable", "gateway",
        "connection", "reset", "websocket",
    ]
    return any(m in text for m in markers)


def _transcode(src: Path, dst: Path, audio_format: str, sample_rate: int) -> str | None:
    """ffmpeg 把 edge-tts 的 mp3 转成 wav / ogg_opus (可选重采样)。"""
    args = ["ffmpeg", "-y", "-i", str(src)]
    if audio_format == "wav":
        args += ["-ar", str(sample_rate), "-ac", "1", "-c:a", "pcm_s16le", str(dst)]
    else:  # ogg_opus
        args += ["-ar", str(sample_rate), "-ac", "1", "-c:a", "libopus", "-b:a", "96k", str(dst)]
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=EDGE_TTS_CALL_TIMEOUT
        )
    except FileNotFoundError:
        return "ffmpeg not found on PATH"
    except subprocess.TimeoutExpired:
        return "ffmpeg transcoding timed out"
    if proc.returncode != 0:
        return (proc.stderr or proc.stdout or "").strip()[:500]
    if not dst.is_file() or dst.stat().st_size == 0:
        return "transcoded output is empty"
    return None
