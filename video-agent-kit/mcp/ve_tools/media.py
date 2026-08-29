from __future__ import annotations

import hashlib
import base64
import json
import math
import shutil
import subprocess
from .ffproc import run_proc
import time
from pathlib import Path
from typing import Any

from .result import ToolResult
from .run_context import RunContext, clean_env
from .cloud_asr import prepare_asr_audio, cloud_asr_status, cloud_asr_transcribe_payload
from .zcode_speech import (
    max_chunk_seconds as zcode_speech_max_chunk_seconds,
    zcode_speech_status,
    zcode_speech_transcribe_payload,
)
from .speech_service import (
    call_remote_speech_tool,
    extract_transcript_payload,
    genericize_data,
    genericize_result,
    genericize_text,
    remote_asr_transfer_mode,
    remote_speech_configured,
)
from .transcript import read_transcript_text

ASR_AUDIO_BITRATE = "64k"
ASR_SAMPLE_RATE = "16000"
ASR_POLL_INTERVAL_SECONDS = 2.5
ASR_TIMEOUT_SECONDS = 3600.0
# Direct-HTTP backend single-submit limit observed in production: longer media is more
# likely to time out or be rejected. Split long inputs into overlapping chunks
# and merge timestamped segments back onto the source timeline.
ASR_CHUNK_SECONDS = 1700.0
ASR_CHUNK_THRESHOLD_SECONDS = 1800.0
ASR_CHUNK_OVERLAP_SECONDS = 2.0
ASR_DEFAULT_RETRIES = 3
ASR_MAX_RETRIES = 10
ASR_RETRY_BACKOFF_SECONDS = 30.0
REMOTE_ASR_UPLOAD_MAX_BYTES = 180 * 1024 * 1024


def run_json(cmd: list[str], timeout: int = 60) -> dict:
    proc = run_proc(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"command failed: {cmd}")
    return json.loads(proc.stdout)


def coerce_asr_retry_count(value: object) -> int | ToolResult:
    if value is None:
        return ASR_DEFAULT_RETRIES
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
    if parsed < 0 or parsed > ASR_MAX_RETRIES:
        return ToolResult(text=f"[ERROR] retries must be in [0, {ASR_MAX_RETRIES}]")
    return parsed


def coerce_nonnegative_number(value: object, field: str, default: float) -> float | ToolResult:
    if value is None:
        return default
    if isinstance(value, bool):
        return ToolResult(text=f"[ERROR] {field} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return ToolResult(text=f"[ERROR] {field} must be numeric")
    if not math.isfinite(parsed) or parsed < 0:
        return ToolResult(text=f"[ERROR] {field} must be a finite number >= 0")
    return parsed


def run_asr_with_retries(call: Any, *, retries: int, retry_backoff_seconds: float) -> tuple[Any, int]:
    result: Any = ToolResult(text="[ERROR] ASR failed")
    attempts: list[dict[str, Any]] = []
    for attempt in range(retries + 1):
        result = call()
        if not isinstance(result, ToolResult):
            return result, attempt
        retryable = asr_error_retryable(result)
        attempts.append({
            "attempt": attempt + 1,
            "error": result.text,
            "retryable": retryable,
        })
        if not retryable or attempt >= retries:
            break
        if retry_backoff_seconds > 0:
            time.sleep(float(retry_backoff_seconds) * (2 ** attempt))
    if isinstance(result, ToolResult):
        result.data = {
            **(result.data or {}),
            "attempts": attempts,
            "retry_attempts": max(0, len(attempts) - 1),
            "max_retries": retries,
        }
    return result, max(0, len(attempts) - 1)


def asr_error_retryable(result: ToolResult) -> bool:
    data = result.data or {}
    if data.get("param_error"):
        return False
    if data.get("recoverable") is False:
        return False
    status_code = str(data.get("status_code") or "")
    if status_code.startswith("55"):
        return True
    text = result.text.lower()
    http_status = http_status_from_text(text)
    if http_status is not None:
        return http_status in {408, 409, 425, 429} or 500 <= http_status <= 599
    non_retryable = [
        "input_path is required",
        "file not found",
        "no asr provider available",
        "not set",
        "not available",
        "ffmpeg not found",
        "audio too large",
        "split the source media",
        "must be",
        "unsupported",
        "package unavailable",
    ]
    if any(marker in text for marker in non_retryable):
        return False
    if data.get("retryable") is True:
        return True
    return message_retryable(text)


def http_status_from_text(text: str) -> int | None:
    marker = "http "
    idx = text.find(marker)
    if idx < 0:
        return None
    raw = text[idx + len(marker):].split(None, 1)[0].strip(":,.;")
    try:
        return int(raw)
    except ValueError:
        return None


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


def inspect_media(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("input_path"):
        return ToolResult(text="[ERROR] input_path is required")
    input_path = ctx.resolve(args["input_path"])
    if not input_path.is_file():
        return ToolResult(text=f"[ERROR] File not found: {input_path}")
    if not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffprobe not found on PATH")

    started = time.time()
    try:
        data = run_json([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(input_path)
        ])
    except Exception as exc:
        return ToolResult(text=f"[ERROR] ffprobe failed: {exc}")
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    duration_seconds = safe_float(fmt.get("duration"))
    if duration_seconds is None:
        stream_durations = [safe_float(s.get("duration")) for s in streams if isinstance(s, dict)]
        stream_durations = [value for value in stream_durations if value is not None]
        duration_seconds = max(stream_durations) if stream_durations else None
    out = {
        "input_path": str(input_path),
        "duration_seconds": duration_seconds,
        "size_bytes": safe_int(fmt.get("size")) or 0,
        "format_name": fmt.get("format_name"),
        "bit_rate": safe_int(fmt.get("bit_rate")),
        "streams": streams,
        "video_streams": [s for s in streams if s.get("codec_type") == "video"],
        "audio_streams": [s for s in streams if s.get("codec_type") == "audio"],
        "elapsed_seconds": round(time.time() - started, 3),
    }
    out["summary"] = media_summary(out)
    out["technical_risks"] = media_technical_risks(out)
    output_json = args.get("output_json")
    artifacts = []
    if output_json:
        p = ctx.resolve(output_json)
    else:
        p = ctx.output_dir / "media.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts.append(str(p))
    return ToolResult(
        text=f"Inspected media: {ctx.virtualize(input_path)}",
        data=out,
        artifacts=artifacts,
    )


def analyze_media(args: dict, ctx: RunContext) -> ToolResult:
    """Lightweight deterministic source analysis for planning, not a semantic judge."""
    if not args.get("input_path"):
        return ToolResult(text="[ERROR] input_path is required")
    input_path = ctx.resolve(args["input_path"])
    if not input_path.is_file():
        return ToolResult(text=f"[ERROR] File not found: {input_path}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    scene_threshold = coerce_threshold(args.get("scene_threshold"), default=0.30)
    if isinstance(scene_threshold, ToolResult):
        return scene_threshold
    started = time.time()
    probe_sidecar = ctx.work_dir / "analysis" / f"{input_path.stem}_media.json"
    probe = inspect_media({"input_path": str(input_path), "output_json": str(probe_sidecar)}, ctx)
    if probe.text.startswith("[ERROR]"):
        return ToolResult(text=f"[ERROR] inspect failed during analyze_media: {probe.text}", data=probe.data)
    duration = safe_float((probe.data.get("summary") or {}).get("duration_seconds"))
    scenes, scene_log = scan_scene_changes(input_path, scene_threshold)
    black_ranges, black_log = scan_ranges(input_path, "blackdetect=d=0.2:pix_th=0.10", "black")
    silence_ranges, silence_log = scan_ranges(input_path, "silencedetect=n=-35dB:d=0.5", "silence")
    candidate_segments = segments_from_boundaries(duration, scenes)
    report = {
        "input_path": str(input_path),
        "duration_seconds": duration,
        "scene_threshold": scene_threshold,
        "scene_change_times": scenes,
        "candidate_segments": candidate_segments,
        "black_ranges": black_ranges,
        "silence_ranges": silence_ranges,
        "notes": [
            "candidate_segments are deterministic scene-boundary hints, not final editorial choices",
            "use video_ingest/video_watch_segment to visually verify any candidate before timeline decisions",
        ],
        "logs": {
            "scene_tail": scene_log[-2000:],
            "black_tail": black_log[-2000:],
            "silence_tail": silence_log[-2000:],
        },
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json = ctx.resolve(args.get("output_json") or "out/media_analysis.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # The full report (scene_change_times / candidate_segments / black & silence
    # ranges) is written to disk above. Inlining it into data too would dump
    # hundreds of KB / six figures of tokens for a long film into one tool
    # result. Return only a bounded summary here; Read the artifact for detail.
    summary = {
        "input_path": report["input_path"],
        "duration_seconds": duration,
        "scene_threshold": scene_threshold,
        "scene_change_count": len(scenes),
        "candidate_segment_count": len(candidate_segments),
        "black_range_count": len(black_ranges),
        "silence_range_count": len(silence_ranges),
        "notes": report["notes"],
        "elapsed_seconds": report["elapsed_seconds"],
    }
    return ToolResult(
        text=(
            f"Media analysis written: {ctx.virtualize(output_json)} "
            f"({len(scenes)} scene changes, {len(candidate_segments)} candidate segments). "
            f"Read {ctx.virtualize(output_json)} for the full boundary list before timeline decisions."
        ),
        data=summary,
        artifacts=[str(output_json)],
    )


def safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    if not math.isfinite(parsed):
        return None
    return round(parsed, 6)


def safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def coerce_threshold(value: object, *, default: float) -> float | ToolResult:
    if value is None:
        return default
    if isinstance(value, bool):
        return ToolResult(text="[ERROR] scene_threshold must be numeric")
    try:
        parsed = float(value)
    except Exception:
        return ToolResult(text="[ERROR] scene_threshold must be numeric")
    if not math.isfinite(parsed) or parsed <= 0 or parsed >= 1:
        return ToolResult(text="[ERROR] scene_threshold must be in (0, 1)")
    return parsed


def scan_scene_changes(path: Path, threshold: float) -> tuple[list[float], str]:
    expr = f"select='gt(scene,{threshold:.6f})',showinfo"
    cmd = ["ffmpeg", "-v", "info", "-i", str(path), "-vf", expr, "-f", "null", "-"]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=900)
    except Exception as exc:
        return [], str(exc)
    output = (proc.stderr or "") + (proc.stdout or "")
    times = []
    for line in output.splitlines():
        marker = "pts_time:"
        if marker not in line:
            continue
        tail = line.split(marker, 1)[1].split()[0]
        value = safe_float(tail)
        if value is not None:
            times.append(value)
    return sorted(set(round(t, 3) for t in times if t >= 0)), output


def scan_ranges(path: Path, filter_expr: str, kind: str) -> tuple[list[dict], str]:
    filter_arg = "-af" if kind == "silence" else "-vf"
    cmd = ["ffmpeg", "-v", "info", "-i", str(path), filter_arg, filter_expr, "-f", "null", "-"]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=900)
    except Exception as exc:
        return [], str(exc)
    output = (proc.stderr or "") + (proc.stdout or "")
    starts: list[float] = []
    ranges = []
    start_marker = f"{kind}_start:"
    end_marker = f"{kind}_end:"
    duration_marker = f"{kind}_duration:"
    for line in output.splitlines():
        if start_marker in line:
            value = safe_float(line.split(start_marker, 1)[1].split()[0])
            if value is not None:
                starts.append(value)
        if end_marker in line:
            end = safe_float(line.split(end_marker, 1)[1].split()[0])
            duration = safe_float(line.split(duration_marker, 1)[1].split()[0]) if duration_marker in line else None
            start = starts.pop(0) if starts else ((end - duration) if end is not None and duration is not None else None)
            if start is not None and end is not None:
                ranges.append({"start": round(start, 3), "end": round(end, 3), "duration": round(end - start, 3)})
    return ranges, output


def segments_from_boundaries(duration: float | None, boundaries: list[float]) -> list[dict]:
    if duration is None or duration <= 0:
        return []
    points = [0.0] + [t for t in boundaries if 0.1 < t < duration - 0.1] + [duration]
    points = sorted(set(round(t, 3) for t in points))
    segments = []
    for idx, (start, end) in enumerate(zip(points, points[1:])):
        if end - start < 0.3:
            continue
        segments.append({
            "index": idx,
            "start": start,
            "end": end,
            "duration": round(end - start, 3),
            "source": "scene_boundary",
        })
    return segments


def media_summary(probe: dict) -> dict:
    video = first_stream(probe.get("video_streams"))
    audio = first_stream(probe.get("audio_streams"))
    return {
        "duration_seconds": probe.get("duration_seconds"),
        "has_video": bool(video),
        "has_audio": bool(audio),
        "width": safe_int(video.get("width")) if video else None,
        "height": safe_int(video.get("height")) if video else None,
        "fps": stream_fps(video) if video else None,
        "video_codec": video.get("codec_name") if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_channels": safe_int(audio.get("channels")) if audio else None,
        "audio_sample_rate": safe_int(audio.get("sample_rate")) if audio else None,
        "pix_fmt": video.get("pix_fmt") if video else None,
        "color_space": video.get("color_space") if video else None,
        "color_transfer": video.get("color_transfer") if video else None,
        "rotation": stream_rotation(video) if video else None,
    }


def media_technical_risks(probe: dict) -> list[dict]:
    risks = []
    summary = probe.get("summary") or {}
    if not summary.get("has_video") and not summary.get("has_audio"):
        risks.append({"severity": "error", "message": "no video or audio stream detected"})
    elif not summary.get("has_video"):
        risks.append({"severity": "warning", "message": "media has no video stream"})
    if summary.get("has_video") and not summary.get("has_audio"):
        risks.append({"severity": "warning", "message": "video has no audio stream"})
    width = summary.get("width") or 0
    height = summary.get("height") or 0
    if width and height and (width % 2 or height % 2):
        risks.append({"severity": "warning", "message": "odd video dimensions may require padding before H.264 render"})
    if width and height and width * height >= 3840 * 2160:
        risks.append({"severity": "info", "message": "4K-or-larger source may be expensive to sample/render"})
    video = first_stream(probe.get("video_streams"))
    if video:
        avg = stream_fps(video, "avg_frame_rate")
        nominal = stream_fps(video, "r_frame_rate")
        if avg and nominal and abs(avg - nominal) > 0.5:
            risks.append({
                "severity": "warning",
                "message": "possible variable-frame-rate source",
                "evidence": f"avg_frame_rate={avg:.3f}, r_frame_rate={nominal:.3f}",
            })
        if stream_rotation(video):
            risks.append({"severity": "info", "message": f"rotation metadata present: {stream_rotation(video)}"})
        transfer = str(video.get("color_transfer") or "").lower()
        if transfer in {"smpte2084", "arib-std-b67"}:
            risks.append({"severity": "warning", "message": f"HDR transfer detected ({transfer}); SDR preview may need tonemapping"})
    return risks


def first_stream(streams: object) -> dict:
    if isinstance(streams, list) and streams and isinstance(streams[0], dict):
        return streams[0]
    return {}


def stream_fps(stream: dict, key: str | None = None) -> float | None:
    keys = [key] if key else ["avg_frame_rate", "r_frame_rate"]
    for item in keys:
        value = stream.get(item)
        if not value or value == "0/0":
            continue
        try:
            if "/" in str(value):
                num, den = str(value).split("/", 1)
                den_f = float(den)
                if den_f == 0:
                    continue
                fps = float(num) / den_f
            else:
                fps = float(value)
        except Exception:
            continue
        if math.isfinite(fps) and fps > 0:
            return round(fps, 6)
    return None


def stream_rotation(stream: dict) -> str | None:
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    if tags.get("rotate"):
        return str(tags["rotate"])
    side_data = stream.get("side_data_list")
    if isinstance(side_data, list):
        for item in side_data:
            if isinstance(item, dict) and item.get("rotation") not in (None, 0, "0"):
                return str(item["rotation"])
    return None


ASR_PROVIDERS = {"auto", "cloud", "cloud_asr", "remote", "speech"}
LOCAL_ASR_ALIASES = {"auto", "cloud", "cloud_asr", "remote", "speech"}


def transcribe(args: dict, ctx: RunContext) -> ToolResult:
    """Compatibility wrapper. Paid ASR is exposed as speech_transcribe."""
    return speech_transcribe(args, ctx)


def speech_transcribe(args: dict, ctx: RunContext) -> ToolResult:
    remote = remote_speech_transcribe(args, ctx)
    if remote is not None:
        return remote
    return local_speech_transcribe(args, ctx)


def remote_speech_transcribe(args: dict, ctx: RunContext) -> ToolResult | None:
    if not remote_speech_configured():
        return None
    if not args.get("input_path"):
        return ToolResult(text="[ERROR] input_path is required")
    input_path = ctx.resolve(args["input_path"])
    if not input_path.is_file():
        return ToolResult(text=f"[ERROR] File not found: {input_path}")
    output_path = ctx.resolve(args.get("output_json") or "out/transcript.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    remote_args = {
        key: value
        for key, value in args.items()
        if key not in {"output_json", "work_dir"}
    }
    transfer_mode = remote_asr_transfer_mode()
    if transfer_mode == "base64":
        prepared = prepare_remote_asr_upload(input_path, args, ctx)
        if isinstance(prepared, ToolResult):
            return prepared
        upload_path, input_format = prepared
        remote_args.pop("input_path", None)
        remote_args["audio_base64"] = base64.b64encode(upload_path.read_bytes()).decode("ascii")
        remote_args["input_format"] = input_format
        remote_args["source_name"] = input_path.name
    else:
        remote_args["input_path"] = str(input_path)
    result = call_remote_speech_tool(
        "transcribe",
        remote_args,
        timeout=float(args.get("timeout_seconds") or ASR_TIMEOUT_SECONDS),
    )
    if result.text.startswith("[ERROR]"):
        return result
    payload = extract_transcript_payload(result.data)
    if payload is None:
        return ToolResult(
            text="[ERROR] remote speech transcription returned no transcript payload",
            data=result.data,
        )
    payload = sanitize_transcript_payload(payload)
    payload["source_media"] = str(input_path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    transcript_text = read_transcript_text(output_path)
    transcript_fingerprint = ctx.file_fingerprint(output_path)
    ctx.remember_transcript_for_video(
        input_path, output_path, transcript_text,
        transcript_fingerprint=transcript_fingerprint,
    )
    if (
        ctx.active_video_path is not None
        and ctx.active_video_key is not None
        and ctx.active_video_key == ctx.video_memory_key(input_path)
    ):
        ctx.active_transcript_path = output_path
        ctx.active_transcript_text = transcript_text
        ctx.active_transcript_fingerprint = transcript_fingerprint
    data = {
        "provider": "cloud_asr",
        "tool": "speech_transcribe",
        "output_json": str(output_path),
        "source_media": str(input_path),
        "language": payload.get("language") or args.get("language") or "zh",
        "word_count": len(payload.get("words", [])),
        "segment_count": len(payload.get("segments", [])),
        "remote_mcp": True,
        "remote_transfer": transfer_mode,
        **({
            "silent_audio": True,
        } if payload.get("silent_audio") else {}),
    }
    return ToolResult(
        text=f"cloud_asr transcript written: {ctx.virtualize(output_path)}",
        data=data,
        artifacts=[str(output_path)],
    )


def prepare_remote_asr_upload(input_path: Path, args: dict, ctx: RunContext) -> tuple[Path, str] | ToolResult:
    if args.get("work_dir"):
        work_dir = ctx.resolve(args["work_dir"])
    else:
        path_digest = hashlib.sha256(str(input_path.resolve()).encode("utf-8")).hexdigest()[:8]
        work_dir = ctx.resolve(f".video_agent/speech_mcp_upload/{input_path.stem}_{path_digest}")
    work_dir.mkdir(parents=True, exist_ok=True)
    prepared = prepare_asr_audio(input_path, work_dir)
    if isinstance(prepared, ToolResult):
        return genericize_result(prepared)
    upload_path, input_format, _source_kind = prepared
    try:
        upload_bytes = upload_path.stat().st_size
    except OSError as exc:
        return ToolResult(text=f"[ERROR] failed to stat remote ASR upload audio: {exc}", data={"retryable": True})
    try:
        max_bytes = int(clean_env("VE_SPEECH_MCP_MAX_UPLOAD_BYTES") or str(REMOTE_ASR_UPLOAD_MAX_BYTES))
    except ValueError:
        max_bytes = REMOTE_ASR_UPLOAD_MAX_BYTES
    if upload_bytes > max_bytes:
        return ToolResult(
            text=(
                f"[ERROR] remote ASR upload audio too large ({upload_bytes / 2**20:.0f} MiB > "
                f"{max_bytes / 2**20:.0f} MiB); use shared-storage path mode or split the source"
            ),
            data={"recoverable": False, "retryable": False},
        )
    return upload_path, input_format


def local_speech_transcribe(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("input_path"):
        return ToolResult(text="[ERROR] input_path is required")
    input_path = ctx.resolve(args["input_path"])
    if not input_path.is_file():
        return ToolResult(text=f"[ERROR] File not found: {input_path}")
    output_path = ctx.resolve(args.get("output_json") or "out/transcript.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    language = str(args.get("language") or "zh").strip() or "zh"
    timeout_seconds = coerce_positive_number(args.get("timeout_seconds"), "timeout_seconds", ASR_TIMEOUT_SECONDS)
    if isinstance(timeout_seconds, ToolResult):
        return timeout_seconds
    poll_interval_seconds = coerce_positive_number(
        args.get("poll_interval_seconds"),
        "poll_interval_seconds",
        ASR_POLL_INTERVAL_SECONDS,
    )
    if isinstance(poll_interval_seconds, ToolResult):
        return poll_interval_seconds
    retries = coerce_asr_retry_count(args.get("retries", args.get("retry_count")))
    if isinstance(retries, ToolResult):
        return retries
    retry_backoff_seconds = coerce_nonnegative_number(
        args.get("retry_backoff_seconds"),
        "retry_backoff_seconds",
        ASR_RETRY_BACKOFF_SECONDS,
    )
    if isinstance(retry_backoff_seconds, ToolResult):
        return retry_backoff_seconds

    provider_arg = str(args.get("provider") or clean_env("VE_ASR_PROVIDER") or "auto").strip().lower()
    if provider_arg not in ASR_PROVIDERS:
        return ToolResult(
            text="[ERROR] provider must be auto or cloud",
            data={"supported_providers": ["auto", "cloud"]},
        )
    zcode_status = zcode_speech_status(ctx)
    compat_status = cloud_asr_status() if provider_arg in LOCAL_ASR_ALIASES else None
    if provider_arg in LOCAL_ASR_ALIASES:
        if zcode_status["available"]:
            backend = "zcode_official"
        elif compat_status["available"]:
            backend = "local_compat"
        else:
            return ToolResult(
                text=(
                    "[ERROR] cloud_asr is not available: "
                    + genericize_text(
                        "official channel: " + "; ".join(zcode_status["reasons"])
                        + ". local compatibility channel: " + "; ".join(compat_status["reasons"])
                    )
                ),
                data={
                    "recoverable": True,
                    "official_channel": genericize_data(zcode_status),
                    "cloud_asr": genericize_data(compat_status),
                },
            )
        provider = "cloud_asr"
    else:
        provider = provider_arg

    started = time.time()
    # 默认 work_dir 加路径哈希: 只按 stem 键控时, 不同目录的同名源视频会共用
    # .video_agent/asr/{stem}/, 提取音频/中间产物被后一次调用 -y 覆盖, 前一次
    # 返回的 artifacts 静默变成另一个视频的音频 (与帧目录同 stem 互删同类洞)
    if args.get("work_dir"):
        work_dir = ctx.resolve(args["work_dir"])
    else:
        path_digest = hashlib.sha256(str(input_path.resolve()).encode("utf-8")).hexdigest()[:8]
        work_dir = ctx.resolve(f".video_agent/asr/{input_path.stem}_{path_digest}")
    work_dir.mkdir(parents=True, exist_ok=True)

    def transcribe_one(
        audio_path: Path, out_dir: Path, *, started_at: float
    ) -> tuple[dict[str, Any], Path] | ToolResult:
        if backend == "zcode_official":
            return zcode_speech_transcribe_payload(
                audio_path,
                out_dir,
                ctx=ctx,
                language=language,
                timeout_seconds=float(timeout_seconds),
                started=started_at,
            )
        return cloud_asr_transcribe_payload(
            audio_path,
            out_dir,
            language=language,
            timeout_seconds=float(timeout_seconds),
            poll_interval_seconds=float(poll_interval_seconds),
            started=started_at,
        )

    if provider == "cloud_asr":
        default_chunk_seconds = (
            zcode_speech_max_chunk_seconds() if backend == "zcode_official" else ASR_CHUNK_SECONDS
        )
        chunk_threshold_seconds = (
            default_chunk_seconds if backend == "zcode_official" else ASR_CHUNK_THRESHOLD_SECONDS
        )
        chunk_seconds = coerce_positive_number(
            args.get("chunk_seconds"), "chunk_seconds", default_chunk_seconds
        )
        if isinstance(chunk_seconds, ToolResult):
            return chunk_seconds
        duration = media_duration_seconds(input_path)
        if duration and duration > max(float(chunk_seconds), chunk_threshold_seconds):
            asr_result = cloud_asr_chunked_payload(
                input_path,
                work_dir,
                backend=backend,
                transcribe_one=transcribe_one,
                language=language,
                started=started,
                duration=duration,
                chunk_seconds=float(chunk_seconds),
                retries=retries,
                retry_backoff_seconds=float(retry_backoff_seconds),
            )
        else:
            asr_result, retry_attempts = run_asr_with_retries(
                lambda: transcribe_one(input_path, work_dir, started_at=started),
                retries=retries,
                retry_backoff_seconds=float(retry_backoff_seconds),
            )
        if isinstance(asr_result, ToolResult):
            return genericize_result(asr_result)
        transcript_payload, asr_source = asr_result
        if not transcript_payload.get("chunks"):
            transcript_payload["retry_attempts"] = retry_attempts
            transcript_payload["max_retries"] = retries
        transcript_payload = sanitize_transcript_payload(transcript_payload)

    output_path.write_text(json.dumps(transcript_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    transcript_text = read_transcript_text(output_path)
    transcript_fingerprint = ctx.file_fingerprint(output_path)
    ctx.remember_transcript_for_video(input_path, output_path, transcript_text,
                                      transcript_fingerprint=transcript_fingerprint)
    if (
        ctx.active_video_path is not None
        and ctx.active_video_key is not None
        and ctx.active_video_key == ctx.video_memory_key(input_path)
    ):
        ctx.active_transcript_path = output_path
        ctx.active_transcript_text = transcript_text
        ctx.active_transcript_fingerprint = transcript_fingerprint
    data = {
        "provider": provider,
        "requested_provider": provider_arg if provider_arg != "cloud_asr" else "cloud",
        "tool": "speech_transcribe",
        "channel": "zcode_official" if backend == "zcode_official" else "local_compat",
        "output_json": str(output_path),
        "source_media": str(input_path),
        "asr_audio": str(asr_source),
        "language": transcript_payload.get("language") or language,
        "word_count": len(transcript_payload.get("words", [])),
        "segment_count": len(transcript_payload.get("segments", [])),
        "retry_attempts": transcript_payload.get("retry_attempts", 0),
        "max_retries": retries,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    if provider == "cloud_asr":
        data["n_speakers"] = len({
            seg.get("speaker") for seg in transcript_payload.get("segments", [])
            if seg.get("speaker")
        }) or None
        if transcript_payload.get("silent_audio"):
            data["silent_audio"] = True
        if transcript_payload.get("chunks"):
            data["chunks"] = transcript_payload["chunks"]
            data["chunk_seconds"] = transcript_payload.get("chunk_seconds")
    return ToolResult(
        text=f"{provider} transcript written: {ctx.virtualize(output_path)}",
        data=data,
        artifacts=[str(output_path), str(asr_source)],
    )


def sanitize_transcript_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(genericize_data(payload))
    out["provider"] = "cloud_asr"
    # Transcripts cached by an older plugin version carry a vendor-prefixed
    # request-id key. Fold any such key into the neutral name so re-read payloads
    # stay branding-free too, rather than leaking through this function untouched.
    for legacy_key in [k for k in out if k != "request_id" and k.endswith("_request_id")]:
        out.setdefault("request_id", out[legacy_key])
        out.pop(legacy_key, None)
    for key in ("resource_id", "interface", "fallback_from", "fallback_reason"):
        out.pop(key, None)
    if isinstance(out.get("note"), str):
        out["note"] = genericize_text(out["note"])
    if isinstance(out.get("warnings"), list):
        out["warnings"] = [genericize_text(item) for item in out["warnings"]]
    return out


def media_duration_seconds(path: Path) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    try:
        data = run_json([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(path)
        ], timeout=120)
    except Exception:
        return None
    duration = safe_float(data.get("format", {}).get("duration"))
    if duration is None:
        streams = [
            safe_float(s.get("duration"))
            for s in data.get("streams", [])
            if isinstance(s, dict)
        ]
        streams = [value for value in streams if value is not None]
        duration = max(streams) if streams else None
    return duration


def cloud_asr_chunked_payload(
    input_path: Path,
    work_dir: Path,
    *,
    backend: str,
    transcribe_one: Any,
    language: str,
    started: float,
    duration: float,
    chunk_seconds: float,
    retries: int,
    retry_backoff_seconds: float,
) -> tuple[dict[str, Any], Path] | ToolResult:
    """Transcribe long media through either cloud channel in resumable chunks."""
    if not shutil.which("ffmpeg"):
        return ToolResult(text="[ERROR] ffmpeg not found on PATH; required for chunked ASR")
    full_audio = work_dir / f"{input_path.stem}.asr.mp3"
    if not full_audio.is_file() or full_audio.stat().st_size == 0:
        proc = run_proc([
            "ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(input_path),
            "-vn", "-ac", "1", "-ar", ASR_SAMPLE_RATE, "-b:a", ASR_AUDIO_BITRATE,
            str(full_audio),
        ], capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0 or not full_audio.is_file() or full_audio.stat().st_size == 0:
            return ToolResult(
                text="[ERROR] failed to extract audio for chunked ASR",
                data={"detail": (proc.stderr or proc.stdout or "").strip()[-800:]},
            )

    n_chunks = max(1, math.ceil(duration / chunk_seconds))
    span = duration / n_chunks
    segments: list[dict[str, Any]] = []
    interface = None
    resource_id = None
    silent_audio = True
    retry_attempts = 0

    for idx in range(n_chunks):
        offset = span * idx
        chunk_dir = work_dir / f"chunk_{idx:02d}"
        chunk_dir.mkdir(parents=True, exist_ok=True)
        cache = chunk_dir / "transcript_chunk.json"
        payload: dict[str, Any] | None = None

        if cache.is_file():
            try:
                payload = json.loads(cache.read_text(encoding="utf-8"))
            except Exception:
                payload = None
            if payload is not None and (
                str(payload.get("language") or "") != str(language or "")
                or (
                    "chunk_offset" in payload
                    and abs(float(payload["chunk_offset"]) - offset) > 0.5
                )
                or (
                    "chunk_span" in payload
                    and abs(float(payload["chunk_span"]) - span) > 0.5
                )
            ):
                payload = None

        if payload is None:
            chunk_audio = chunk_dir / "audio.mp3"
            proc = run_proc([
                "ffmpeg", "-nostdin", "-y", "-v", "error",
                "-ss", f"{offset:.3f}",
                "-t", f"{span + ASR_CHUNK_OVERLAP_SECONDS:.3f}",
                "-i", str(full_audio),
                "-c", "copy",
                str(chunk_audio),
            ], capture_output=True, text=True, timeout=600)
            if proc.returncode != 0 or not chunk_audio.is_file() or chunk_audio.stat().st_size == 0:
                return ToolResult(
                    text=f"[ERROR] failed to cut ASR chunk {idx + 1}/{n_chunks}",
                    data={"detail": (proc.stderr or proc.stdout or "").strip()[-800:]},
                )

            last_err: ToolResult | None = None
            result, chunk_retry_attempts = run_asr_with_retries(
                lambda: transcribe_one(chunk_audio, chunk_dir, started_at=time.time()),
                retries=retries,
                retry_backoff_seconds=retry_backoff_seconds,
            )
            retry_attempts += chunk_retry_attempts
            if isinstance(result, ToolResult):
                last_err = result
            else:
                payload = result[0]
                payload["language"] = str(language or "")
                payload["chunk_offset"] = round(offset, 3)
                payload["chunk_span"] = round(span, 3)
                cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            if payload is None and last_err is None:
                last_err = ToolResult(text=f"[ERROR] {backend} chunk failed")

            if payload is None:
                err = last_err or ToolResult(text=f"[ERROR] {backend} chunk failed")
                err.data = {
                    **(err.data or {}),
                    "chunk": idx + 1,
                    "n_chunks": n_chunks,
                    "hint": "chunk results are cached; rerun transcribe to resume",
                }
                err.text = f"[ERROR] chunk {idx + 1}/{n_chunks}: " + err.text.removeprefix("[ERROR] ")
                return err

        interface = interface or payload.get("interface")
        resource_id = resource_id or payload.get("resource_id")
        silent_audio = silent_audio and bool(payload.get("silent_audio"))
        for seg in payload.get("segments", []):
            text = str(seg.get("text", "")).strip()
            start = safe_float(seg.get("start"))
            if not text or start is None:
                continue
            if idx > 0 and start < ASR_CHUNK_OVERLAP_SECONDS:
                continue
            segments.append({
                "speaker": f"p{idx}_{seg.get('speaker') or 's?'}",
                "text": text,
                "start": round(start + offset, 2),
                "end": round((safe_float(seg.get("end")) or start) + offset, 2),
            })

    segments.sort(key=lambda item: item["start"])
    return {
        "provider": "cloud_asr",
        "language": language,
        "source_media": str(input_path),
        "asr_audio": str(full_audio),
        "resource_id": resource_id,
        "interface": interface,
        "chunks": n_chunks,
        "chunk_seconds": chunk_seconds,
        "speaker_note": (
            "speaker labels are per-chunk clusters (p{chunk}_{speaker}); "
            "the same person may carry different labels across chunks"
        ),
        "text": " ".join(s["text"] for s in segments),
        "words": [],
        "segments": segments,
        "silent_audio": silent_audio or not segments,
        "retry_attempts": retry_attempts,
        "max_retries": retries,
        "elapsed_seconds": round(time.time() - started, 3),
        "time_unit": "seconds",
    }, full_audio


def coerce_positive_number(value: object, field: str, default: float) -> float | ToolResult:
    if value is None:
        return default
    if isinstance(value, bool):
        return ToolResult(text=f"[ERROR] {field} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return ToolResult(text=f"[ERROR] {field} must be numeric")
    if not math.isfinite(parsed) or parsed <= 0:
        return ToolResult(text=f"[ERROR] {field} must be a finite number > 0")
    return parsed
