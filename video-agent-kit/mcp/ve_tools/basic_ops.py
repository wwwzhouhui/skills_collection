from __future__ import annotations

import json
import math
import shutil
import subprocess
from .ffproc import run_proc
import time
from pathlib import Path
from typing import Any

from .render import cut_clip, ffconcat_escape, probe_video_size, source_has_audio, source_has_video
from .result import ToolResult
from .run_context import RunContext, reject_input_output_collision
from .timeline import file_sha256, media_duration_seconds


VIDEO_OPERATIONS = {
    "trim",
    "splice",
    "speed",
    "crop",
    "scale",
    "rotate",
    "flip",
    "freeze_frame",
}
SPEED_MIN = 0.1
SPEED_MAX = 8.0


def video_basic_operation(args: dict, ctx: RunContext) -> ToolResult:
    operation = str(args.get("operation") or "").strip().lower()
    if operation not in VIDEO_OPERATIONS:
        return ToolResult(
            text=f"[ERROR] operation must be one of: {', '.join(sorted(VIDEO_OPERATIONS))}",
            data={"supported_operations": sorted(VIDEO_OPERATIONS)},
        )
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    started = time.time()
    try:
        if operation == "trim":
            output_path, artifacts = op_trim(args, ctx)
        elif operation == "splice":
            output_path, artifacts = op_splice(args, ctx)
        elif operation == "speed":
            output_path, artifacts = op_speed(args, ctx)
        elif operation == "crop":
            output_path, artifacts = op_filter(args, ctx, build_crop_filter(args))
        elif operation == "scale":
            output_path, artifacts = op_filter(args, ctx, build_scale_filter(args))
        elif operation == "rotate":
            output_path, artifacts = op_filter(args, ctx, build_rotate_filter(args))
        elif operation == "flip":
            output_path, artifacts = op_filter(args, ctx, build_flip_filter(args))
        else:
            output_path, artifacts = op_freeze_frame(args, ctx)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}")
    except RuntimeError as exc:
        return ToolResult(text=f"[ERROR] {exc}")

    # 输出必须有视频流兜底: 边界 start (源时长 ±0.05 容差内) 等形态下 ffmpeg
    # 可能 exit 0 却产出 0 流空 mp4 — 不能报 completed
    if not output_path.is_file() or not source_has_video(output_path):
        return ToolResult(
            text=(
                f"[ERROR] {operation} produced no video stream (empty output) — "
                "the requested range/time likely falls outside the usable source"
            ),
            data={"operation": operation, "output_path": str(output_path)},
        )

    report = {
        "operation": operation,
        "output_path": str(output_path),
        "output_sha256": file_sha256(output_path) if output_path.is_file() else None,
        "elapsed_seconds": round(time.time() - started, 3),
        "implementation": "ffmpeg deterministic media operation inspired by OpenChatCut timeline item transforms",
    }
    report_path = output_path.with_suffix(".basic_operation.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    all_artifacts = artifacts + [str(output_path), str(report_path)]
    return ToolResult(
        text=f"Video basic operation completed: {ctx.virtualize(output_path)}",
        data=report,
        artifacts=all_artifacts,
        video_paths=[str(output_path)],
    )


def op_trim(args: dict, ctx: RunContext) -> tuple[Path, list[str]]:
    input_path = require_input_file(args, ctx)
    start = number_arg(args, "start_time", default=0.0, minimum=0.0)
    duration = duration_from_args(args, start)
    ensure_range_within_source(input_path, start, duration)
    output_path = output_for(args, ctx, input_path, "trim")
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.6f}",
        "-t", f"{duration:.6f}",
        "-i", str(input_path),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-vf", "setsar=1,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-avoid_negative_ts", "make_zero",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(cmd, "trim failed")
    return output_path, []


def op_splice(args: dict, ctx: RunContext) -> tuple[Path, list[str]]:
    clips_arg = args.get("clips")
    if not isinstance(clips_arg, list) or not clips_arg:
        raise ValueError("splice requires non-empty clips[]")
    if args.get("output_path"):
        output_path = ctx.resolve(str(args["output_path"]))
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = ctx.resolve("out/splice.mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = ctx.resolve(args.get("work_dir") or f".video_agent/basic_ops/{output_path.stem}")
    work_dir.mkdir(parents=True, exist_ok=True)
    clips = [normalize_splice_clip(item, idx, ctx) for idx, item in enumerate(clips_arg)]
    for clip in clips:
        reject_input_output_collision(clip.get("source"), output_path)
    target_width, target_height = resolve_canvas(args, clips[0]["source"])
    segment_paths: list[Path] = []
    for idx, clip in enumerate(clips):
        segment_path = work_dir / f"seg_{idx:04d}.mp4"
        cut_clip(clip, segment_path, target_width=target_width, target_height=target_height)
        segment_paths.append(segment_path)
    concat_file = work_dir / "concat.txt"
    concat_file.write_text("".join(f"file '{ffconcat_escape(path)}'\n" for path in segment_paths), encoding="utf-8")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(cmd, "splice concat failed")
    return output_path, [str(concat_file), *[str(path) for path in segment_paths]]


def op_speed(args: dict, ctx: RunContext) -> tuple[Path, list[str]]:
    input_path = require_input_file(args, ctx)
    speed = number_arg(args, "speed", default=None, minimum=SPEED_MIN, maximum=SPEED_MAX)
    start = number_arg(args, "start_time", default=0.0, minimum=0.0)
    duration = duration_from_args(args, start, required=False)
    if duration is not None:
        ensure_range_within_source(input_path, start, duration)
    else:
        # 只给 start_time 不给时长: start 仍须落在源内, 否则 ffmpeg 会输出
        # 0 流的空 mp4 且 exit 0, 工具报成功
        ensure_range_within_source(input_path, start, 0.001)
    reverse = bool_arg(args.get("reverse"), "reverse", default=False)
    output_path = output_for(args, ctx, input_path, "speed")
    cmd = ["ffmpeg", "-y"]
    if start > 0:
        cmd += ["-ss", f"{start:.6f}"]
    if duration is not None:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += ["-i", str(input_path)]
    vf_parts = []
    if reverse:
        vf_parts.append("reverse")
    vf_parts += [f"setpts=PTS/{speed:.8f}", "setsar=1", "format=yuv420p"]
    cmd += ["-map", "0:v:0", "-vf", ",".join(vf_parts)]
    if source_has_audio(input_path):
        af_parts = []
        if reverse:
            af_parts.append("areverse")
        af_parts.extend(atempo_chain(speed))
        cmd += ["-map", "0:a:0", "-af", ",".join(af_parts)]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(cmd, "speed operation failed")
    return output_path, []


def op_filter(args: dict, ctx: RunContext, vf: str) -> tuple[Path, list[str]]:
    input_path = require_input_file(args, ctx)
    operation = str(args["operation"]).strip().lower()
    output_path = output_for(args, ctx, input_path, operation)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(cmd, f"{operation} operation failed")
    return output_path, []


def op_freeze_frame(args: dict, ctx: RunContext) -> tuple[Path, list[str]]:
    input_path = require_input_file(args, ctx)
    at_time = number_arg(args, "at_time", default=None, minimum=0.0)
    duration = number_arg(args, "duration", default=None, minimum=0.001)
    ensure_range_within_source(input_path, at_time, 0.001)
    output_path = output_for(args, ctx, input_path, "freeze_frame")
    work_dir = ctx.resolve(args.get("work_dir") or f".video_agent/basic_ops/{output_path.stem}")
    work_dir.mkdir(parents=True, exist_ok=True)
    frame_path = work_dir / "freeze_frame.jpg"
    extract_cmd = [
        "ffmpeg", "-y",
        "-ss", f"{at_time:.6f}",
        "-i", str(input_path),
        "-frames:v", "1",
        str(frame_path),
    ]
    run_ffmpeg(extract_cmd, "freeze frame extraction failed")
    if not frame_path.is_file() or frame_path.stat().st_size == 0:
        # at_time 落在源时长容差区内但已过最后一帧时, ffmpeg 可能 0 帧成功退出;
        # 不在这里拦住的话, 下游 render 会报无关的 "No such file" 误导归因
        raise RuntimeError(
            f"freeze frame extraction produced no frame at {at_time:.3f}s "
            "(at_time is likely past the last frame of the source)"
        )
    width, height = resolve_canvas(args, input_path)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1,format=yuv420p"
    )
    render_cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", f"{duration:.6f}", "-i", str(frame_path),
        "-f", "lavfi", "-t", f"{duration:.6f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    run_ffmpeg(render_cmd, "freeze frame render failed")
    return output_path, [str(frame_path)]


def require_input_file(args: dict, ctx: RunContext) -> Path:
    if not args.get("input_path"):
        raise ValueError("input_path is required")
    input_path = ctx.resolve(str(args["input_path"]))
    if not input_path.is_file():
        raise ValueError(f"File not found: {input_path}")
    return input_path


def output_for(args: dict, ctx: RunContext, input_path: Path, operation: str) -> Path:
    if args.get("output_path"):
        output_path = ctx.resolve(str(args["output_path"]))
    else:
        stem = input_path.stem if input_path.stem else "output"
        output_path = ctx.resolve(f"out/{stem}_{operation}.mp4")
    reject_input_output_collision(input_path, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path


def number_arg(
    args: dict,
    field: str,
    *,
    default: float | None,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = args.get(field, default)
    if value is None:
        raise ValueError(f"{field} is required")
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{field} must be >= {minimum:g}")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{field} must be <= {maximum:g}")
    return parsed


def int_arg(args: dict, field: str, *, minimum: int = 1) -> int:
    value = args.get(field)
    if value is None:
        raise ValueError(f"{field} is required")
    if isinstance(value, bool):
        raise ValueError(f"{field} must be an integer")
    if isinstance(value, float) and not value.is_integer():
        # int() 截断 + 取偶会让 3.9 静默变成 2 (CLI/直调路径可传 float);
        # 非整数值直接报错而不是双重漂移
        raise ValueError(f"{field} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if parsed < minimum:
        raise ValueError(f"{field} must be >= {minimum}")
    return parsed if parsed % 2 == 0 else parsed - 1 if parsed > 2 else 2


def bool_arg(value: object, field: str, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} must be boolean")


def duration_from_args(args: dict, start: float, *, required: bool = True) -> float | None:
    if args.get("end_time") is not None:
        end = number_arg(args, "end_time", default=None, minimum=0.0)
        if end <= start:
            raise ValueError("end_time must be greater than start_time")
        if args.get("duration") is not None:
            duration = number_arg(args, "duration", default=None, minimum=0.001)
            if abs(duration - (end - start)) > 0.05:
                raise ValueError("duration must match end_time - start_time when both are provided")
        return end - start
    if args.get("duration") is not None:
        return number_arg(args, "duration", default=None, minimum=0.001)
    if required:
        raise ValueError("end_time or duration is required")
    return None


def ensure_range_within_source(input_path: Path, start: float, duration: float) -> None:
    source_duration = media_duration_seconds(input_path)
    if source_duration is not None and start + duration > source_duration + 0.05:
        raise ValueError(f"requested range exceeds source duration {source_duration:.3f}s")


def normalize_splice_clip(item: object, idx: int, ctx: RunContext) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"clips[{idx}] must be an object")
    source = item.get("source") or item.get("input_path") or item.get("src")
    if not source:
        raise ValueError(f"clips[{idx}] missing source/input_path/src")
    source_path = ctx.resolve(str(source))
    if not source_path.is_file():
        raise ValueError(f"clips[{idx}] source not found: {source}")
    start = number_arg(item, "start", default=0.0, minimum=0.0)
    if item.get("end") is not None:
        end = number_arg(item, "end", default=None, minimum=0.0)
        if end <= start:
            raise ValueError(f"clips[{idx}] end must be greater than start")
    elif item.get("duration") is not None:
        end = start + number_arg(item, "duration", default=None, minimum=0.001)
    else:
        raise ValueError(f"clips[{idx}] requires end or duration")
    ensure_range_within_source(source_path, start, end - start)
    return {
        "source": str(source_path),
        "start": start,
        "end": end,
        "duration": end - start,
        "reason": str(item.get("reason") or f"splice clip {idx}"),
    }


def resolve_canvas(args: dict, first_source: Path | str) -> tuple[int, int]:
    if args.get("output_width") is None and args.get("output_height") is None:
        return probe_video_size(Path(first_source))
    if args.get("output_width") is None or args.get("output_height") is None:
        raise ValueError("output_width and output_height must be provided together")
    return int_arg(args, "output_width", minimum=2), int_arg(args, "output_height", minimum=2)


def build_crop_filter(args: dict) -> str:
    width = int_arg(args, "width", minimum=2)
    height = int_arg(args, "height", minimum=2)
    x = number_arg(args, "x", default=0.0, minimum=0.0)
    y = number_arg(args, "y", default=0.0, minimum=0.0)
    return f"crop={width}:{height}:{x:.6f}:{y:.6f},setsar=1,format=yuv420p"


def build_scale_filter(args: dict) -> str:
    width = int_arg(args, "output_width", minimum=2)
    height = int_arg(args, "output_height", minimum=2)
    mode = str(args.get("mode") or "fit").strip().lower()
    if mode == "fit":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1,format=yuv420p"
        )
    if mode == "fill":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,format=yuv420p"
        )
    if mode == "stretch":
        return f"scale={width}:{height},setsar=1,format=yuv420p"
    raise ValueError("mode must be fit, fill, or stretch")


def build_rotate_filter(args: dict) -> str:
    degrees = number_arg(args, "degrees", default=None)
    normalized = degrees % 360
    if abs(normalized - 90) < 0.0001:
        return "transpose=1,setsar=1,format=yuv420p"
    if abs(normalized - 180) < 0.0001:
        return "hflip,vflip,setsar=1,format=yuv420p"
    if abs(normalized - 270) < 0.0001:
        return "transpose=2,setsar=1,format=yuv420p"
    radians = normalized * math.pi / 180.0
    # rotw()/roth() 的实参是旋转角 (弧度), 不是输入宽高 —— 传 iw/ih 会按
    # "旋转 iw 弧度" 算画布, 非 90 度倍数的角度全部裁角或过量留边。
    # 任意角的画布常为奇数, libx264+yuv420p 要求偶数, pad 补齐 1px。
    angle = f"{radians:.10f}"
    return (
        f"rotate={angle}:ow=rotw({angle}):oh=roth({angle}):c=black,"
        "pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:black,setsar=1,format=yuv420p"
    )


def build_flip_filter(args: dict) -> str:
    direction = str(args.get("direction") or "horizontal").strip().lower()
    if direction in {"horizontal", "h", "x"}:
        return "hflip,setsar=1,format=yuv420p"
    if direction in {"vertical", "v", "y"}:
        return "vflip,setsar=1,format=yuv420p"
    if direction == "both":
        return "hflip,vflip,setsar=1,format=yuv420p"
    raise ValueError("direction must be horizontal, vertical, or both")


def atempo_chain(speed: float) -> list[str]:
    parts: list[float] = []
    remaining = speed
    while remaining > 2.0:
        parts.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        parts.append(0.5)
        remaining /= 0.5
    parts.append(remaining)
    return [f"atempo={part:.8f}" for part in parts]


def run_ffmpeg(cmd: list[str], message: str) -> None:
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=3600)
    except Exception as exc:
        raise RuntimeError(f"{message}: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"{message}: {detail}")
