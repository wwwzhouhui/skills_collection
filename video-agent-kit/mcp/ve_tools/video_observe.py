from __future__ import annotations

import hashlib
import io
import json
import math
import os
import shutil
import subprocess
from .ffproc import run_proc
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .fonts import find_cjk_font
from .result import ToolResult
from .run_context import RunContext
from .transcript import read_transcript_text, transcript_text_for_range

MAX_INLINE_IMAGES = 600
INLINE_TRANSCRIPT_CHAR_LIMIT = 40000
MAX_SEGMENTS = 8
MAX_SEGMENT_SECONDS = 60.0
MAX_TOTAL_SECONDS = 180.0
LEDGER_DUP_TOLERANCE_SECONDS = 0.2
TIME_RANGE_TOLERANCE_SECONDS = 0.05


@dataclass
class VideoSamplingDefaults:
    # These defaults intentionally follow the frame-selection behavior migrated
    # from base.py, but this module never calls a model API.
    video_frame_count: int | None = None
    video_fps: float = 2.0
    video_t_patch_size: int = 2
    video_sampling_mode: str = "prod"
    max_video_frames: int = 600
    video_frame_normalize_jpeg_quality: int = 90
    video_label_mode: str = "timestamp"
    sheet_cols: int = 4
    sheet_max_cells: int = 24
    sheet_width: int = 1568
    jpeg_quality: int = 85


@dataclass
class SampledFrame:
    label: str
    timestamp: float
    frame_index: int
    image: Any
    path: Path | None = None


def video_ingest(args: dict, ctx: RunContext) -> ToolResult:
    """Sample the full video and return timestamped image sheets to Claude Code."""
    if not args.get("video_path"):
        return ToolResult(text="[ERROR] video_path is required")
    video_path = ctx.resolve(args["video_path"])
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")

    transcript_result = resolve_transcript_args(args, ctx, video_path=video_path)
    if isinstance(transcript_result, ToolResult):
        return transcript_result
    transcript_path, transcript_text, transcript_fp = transcript_result

    output_json = ctx.resolve(args.get("output_json") or "out/video_ingest.json")
    frames_dir = ctx.resolve(
        args.get("save_frames_dir")
        or f".video_agent/video_frames/{video_frames_dir_id(video_path)}_full"
    )
    defaults = VideoSamplingDefaults()
    prompt = args.get("prompt") or default_full_prompt()
    result = build_video_observation(
        ctx=ctx,
        defaults=defaults,
        video_path=video_path,
        output_json=output_json,
        frames_dir=frames_dir,
        label="video_ingest",
        prompt=prompt,
        transcript_text=transcript_text,
        original_time_range=None,
    )
    if not result.text.startswith("[ERROR]"):
        ctx.remember_video(video_path, transcript_path, transcript_text,
                           visually_ingested=True, transcript_fingerprint=transcript_fp)
        if not transcript_text:
            result = append_transcribe_nudge(result, ctx)
    return result


def append_transcribe_nudge(result: ToolResult, ctx: RunContext | None = None) -> ToolResult:
    """Transcript-less ingest is usually a skipped step, not a real constraint:
    when cloud ASR is available, tell the agent the standard flow."""
    from .speech_service import cloud_asr_available

    try:
        provider_available = cloud_asr_available(ctx)
    except Exception:
        return result
    if not provider_available:
        return result
    result.text += (
        "\n\n[transcript] No transcript is attached to this observation, but an ASR provider is available "
        "(cloud_asr). Standard flow: call "
        "speech_transcribe(input_path=<this video>) to produce out/transcript.json, then re-run video_ingest with "
        "transcript_path so every visual decision is paired with matching speech text."
    )
    result.data["transcript_missing"] = True
    result.data["asr_available"] = True
    return result


def video_watch_segment(args: dict, ctx: RunContext) -> ToolResult:
    """Sample a local segment at higher FPS and return timestamped image sheets."""
    if args.get("video_path"):
        video_path = ctx.resolve(args["video_path"])
        if not video_path.is_file():
            return ToolResult(text=f"[ERROR] video not found: {video_path}")
        visually_ingested = ctx.video_was_visually_ingested(video_path)
        transcript_result = resolve_transcript_args(args, ctx, video_path=video_path)
        if isinstance(transcript_result, ToolResult):
            return transcript_result
        transcript_path, transcript_text, transcript_fp = transcript_result
        src = video_path
        src_visually_ingested = visually_ingested
    else:
        if ctx.active_video_path is None:
            return ToolResult(text="[ERROR] No active video. Call video_ingest first, or pass video_path.")
        if ctx.active_video_changed():
            return ToolResult(
                text="[ERROR] active video file changed since it was last observed. "
                "Pass video_path explicitly for the current file, or run video_ingest again before implicit video_watch_segment."
            )
        src = ctx.active_video_path
        src_visually_ingested = ctx.active_video_visually_ingested
        transcript_path = ctx.active_transcript_path
        transcript_text = guarded_transcript_text(
            ctx.active_transcript_path, ctx.active_transcript_text,
            ctx.active_transcript_fingerprint,
        )
        transcript_fp = ctx.active_transcript_fingerprint
        if args.get("transcript_path") or args.get("transcript_text"):
            transcript_result = resolve_transcript_args(args, ctx, video_path=ctx.active_video_path)
            if isinstance(transcript_result, ToolResult):
                return transcript_result
            transcript_path, transcript_text, transcript_fp = transcript_result

    fps = coerce_finite_number(args.get("fps"))
    if fps is None:
        return ToolResult(text="[ERROR] fps is required and must be numeric")
    if fps <= 0:
        return ToolResult(text="[ERROR] fps must be a finite number > 0")
    force = args.get("force", False)
    if not isinstance(force, bool):
        return ToolResult(text="[ERROR] force must be a boolean")
    try:
        segments = parse_watch_segments(args)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}")

    ledger_dir = ctx.work_dir / "video_watch_ledger" / video_ledger_id(src)
    kept, ledger_notes = filter_covered_segments(segments, ledger_dir, fps=fps, force=force)
    if not kept:
        return ToolResult(
            text="[window ledger] all requested segments duplicate prior watch windows at the same fps; "
            "no new visual observation was produced. Pass force=true to rewatch anyway.\n"
            + "\n".join(ledger_notes),
            data={
                "tool": "video_watch_segment",
                "status": "skipped_duplicate",
                "segments": [{"start_time": start, "end_time": end} for start, end in segments],
                "ledger_notes": ledger_notes,
                "ledger_path": str(ledger_dir / "covered.json"),
            },
        )

    base_output = ctx.resolve(
        args.get("output_json") or f"out/{video_frames_dir_id(src)}_watch.json"
    )
    base_frames_dir = ctx.resolve(
        args.get("save_frames_dir")
        or f".video_agent/video_frames/{video_frames_dir_id(src)}_watch"
    )
    # 显式传了路径的单窗口调用保持原路径 (调用方要在那个确切位置拿结果);
    # 默认路径必须带窗口后缀 —— 共享 {stem}_watch 目录时, 每次 watch 的
    # reset_frames_dir 会把上一次 watch 的 contact sheet 全部删掉 (超过内联
    # 上限、等着被 Read 的溢出 sheet 直接消失, 缓存复用也被打穿)。
    explicit_output = bool(args.get("output_json"))
    explicit_frames = bool(args.get("save_frames_dir"))
    defaults = VideoSamplingDefaults(video_fps=fps)
    prompt = args.get("prompt") or default_detail_prompt()
    # transcript 文件可能已被后续 transcribe(另一视频) 同名覆盖 (默认都写
    # out/transcript.json): 指纹不符时禁止重读盘做窗口过滤 — 否则窗口会附上
    # 另一个视频的语音 — 改走会话记忆全文快照的回退并注明原因。
    transcript_stale = (
        transcript_path is not None
        and transcript_fp is not None
        and RunContext.file_fingerprint(transcript_path) != transcript_fp
    )
    range_transcript_path = None if transcript_stale else transcript_path
    results: list[ToolResult] = []
    for idx, (start_time, end_time) in enumerate(kept):
        segment_transcript_text = transcript_text_for_range(range_transcript_path, start_time, end_time)
        if not segment_transcript_text and transcript_text:
            reason = (
                "the transcript file was overwritten after it was remembered for this video "
                "(fingerprint mismatch), so exact range filtering would read the wrong transcript"
                if transcript_stale else
                "no timestamped transcript path was available for exact range filtering"
            )
            segment_transcript_text = (
                f"Full transcript fallback: {reason}.\n"
                f"{transcript_text}"
            )
        suffix = f"seg{idx:02d}_{start_time:.3f}_{end_time:.3f}_fps{fps:g}"
        multi = len(kept) > 1
        output_json = with_suffix_before_ext(base_output, suffix) if (multi or not explicit_output) else base_output
        frames_dir = base_frames_dir / suffix if (multi or not explicit_frames) else base_frames_dir
        results.append(build_video_observation(
            ctx=ctx,
            defaults=defaults,
            video_path=src,
            output_json=output_json,
            frames_dir=frames_dir,
            label="video_watch_segment",
            prompt=prompt,
            transcript_text=segment_transcript_text,
            original_time_range=(start_time, end_time),
            extra_data={"source_video": str(src), "start_time": start_time, "end_time": end_time, "fps": fps},
        ))

    if any(result.text.startswith("[ERROR]") for result in results):
        return merge_watch_results(results, ledger_notes, kept, update_ledger=False, ledger_dir=ledger_dir)
    ctx.remember_video(src, transcript_path, transcript_text,
                       visually_ingested=src_visually_ingested,
                       transcript_fingerprint=transcript_fp)
    update_segment_ledger(ledger_dir, kept, fps=fps)
    return merge_watch_results(results, ledger_notes, kept, update_ledger=True, ledger_dir=ledger_dir)


def resolve_transcript_args(
    args: dict,
    ctx: RunContext,
    *,
    video_path: Path | None = None,
) -> tuple[Path | None, str, str | None] | ToolResult:
    """返回 (transcript_path, 全文, 文件指纹)。指纹是该 path 与全文快照对应
    时刻的 path|size|mtime — 供 watch 在重读盘做窗口过滤前校验文件没被
    后续 transcribe(另一视频) 同名覆盖。"""
    transcript_path = ctx.resolve(args["transcript_path"]) if args.get("transcript_path") else None
    if transcript_path is not None and not transcript_path.is_file():
        return ToolResult(text=f"[ERROR] transcript not found: {transcript_path}")
    if transcript_path is None and not args.get("transcript_text") and video_path is not None:
        active = ctx.active_video_path.resolve() if ctx.active_video_path is not None else None
        if (
            active == video_path.resolve()
            and not ctx.active_video_changed()
            and (ctx.active_transcript_path is not None or ctx.active_transcript_text)
        ):
            transcript_text = guarded_transcript_text(
                ctx.active_transcript_path, ctx.active_transcript_text,
                ctx.active_transcript_fingerprint,
            )
            return ctx.active_transcript_path, transcript_text, ctx.active_transcript_fingerprint
        remembered = ctx.transcript_for_video(video_path)
        if remembered is not None:
            remembered_path, remembered_text, remembered_fp = remembered
            transcript_text = guarded_transcript_text(remembered_path, remembered_text, remembered_fp)
            return remembered_path, transcript_text, remembered_fp
    transcript_text = read_transcript_text(transcript_path, args.get("transcript_text"))
    return transcript_path, transcript_text, ctx.file_fingerprint(transcript_path)


def guarded_transcript_text(path: Path | None, snapshot_text: str, fingerprint: str | None) -> str:
    """会话记忆的 transcript 读取: 快照非空直接用; 快照为空需要重读盘时先校验
    文件指纹 — 文件可能已被后续 transcribe(另一视频) 同名覆盖 (默认都写
    out/transcript.json), 无守卫的重读会把别的视频的语音当成本视频的
    (空快照旁路形态, 第四轮实测复现)。指纹缺失 (旧会话) 保持旧行为读盘。"""
    if snapshot_text:
        return read_transcript_text(None, snapshot_text)
    if path is None:
        return ""
    if fingerprint is not None and RunContext.file_fingerprint(path) != fingerprint:
        return ""
    return read_transcript_text(path)


def parse_watch_segments(args: dict) -> list[tuple[float, float]]:
    raw_segments = args.get("segments")
    if raw_segments is not None:
        if not isinstance(raw_segments, list) or not raw_segments:
            raise ValueError("segments must be a non-empty list of {start, end} objects")
        if len(raw_segments) > MAX_SEGMENTS:
            raise ValueError(f"segments can include at most {MAX_SEGMENTS} windows")
        segments = []
        for idx, item in enumerate(raw_segments):
            if not isinstance(item, dict) or "start" not in item or "end" not in item:
                raise ValueError(f"segments[{idx}] must contain start and end")
            segments.append((coerce_segment_time(item["start"], f"segments[{idx}].start"),
                             coerce_segment_time(item["end"], f"segments[{idx}].end")))
    else:
        if "start_time" not in args or "end_time" not in args:
            raise ValueError("provide start_time/end_time or segments")
        segments = [(
            coerce_segment_time(args["start_time"], "start_time"),
            coerce_segment_time(args["end_time"], "end_time"),
        )]

    total = 0.0
    parsed = []
    for idx, (start, end) in enumerate(segments):
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError(f"segment {idx} start/end must be finite numbers")
        if start < 0 or end < 0:
            raise ValueError(f"segment {idx} start/end must be >= 0")
        if end <= start:
            raise ValueError(f"segment {idx} end_time must be greater than start_time")
        duration = end - start
        if duration > MAX_SEGMENT_SECONDS:
            raise ValueError(f"segment {idx} is {duration:.1f}s, above {MAX_SEGMENT_SECONDS:.0f}s")
        total += duration
        parsed.append((start, end))
    if total > MAX_TOTAL_SECONDS:
        raise ValueError(f"total watch duration is {total:.1f}s, above {MAX_TOTAL_SECONDS:.0f}s")
    return parsed


def coerce_segment_time(value: object, field: str) -> float:
    parsed = coerce_finite_number(value)
    if parsed is None:
        raise ValueError(f"{field} must be numeric") from None
    return parsed


def coerce_finite_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


LEDGER_FPS_TOLERANCE = 1e-6


def filter_covered_segments(
    segments: list[tuple[float, float]],
    ledger_dir: Path,
    *,
    fps: float,
    force: bool = False,
) -> tuple[list[tuple[float, float]], list[str]]:
    ledger = read_segment_ledger(ledger_dir)
    kept: list[tuple[float, float]] = []
    notes: list[str] = []
    for start, end in segments:
        # A window only counts as a duplicate when times AND fps match a prior
        # watch; rewatching the same window at a different fps is a new
        # observation. Legacy ledger entries without fps never dedup.
        duplicate = None
        if not force:
            duplicate = next((
                item for item in ledger
                if abs(item[0] - start) <= LEDGER_DUP_TOLERANCE_SECONDS
                and abs(item[1] - end) <= LEDGER_DUP_TOLERANCE_SECONDS
                and item[2] is not None
                and abs(item[2] - fps) <= LEDGER_FPS_TOLERANCE
            ), None)
        if duplicate is not None:
            notes.append(
                f"- {start:g}-{end:g}s duplicates prior watch window {duplicate[0]:g}-{duplicate[1]:g}s "
                f"at fps={duplicate[2]:g}; skipped. Use a different fps, a tighter window, or force=true to rewatch."
            )
            continue
        overlaps = [item for item in ledger if min(end, item[1]) - max(start, item[0]) > 0.05]
        if overlaps:
            covered = "; ".join(f"{item[0]:g}-{item[1]:g}s" for item in overlaps[:4])
            notes.append(
                f"- {start:g}-{end:g}s overlaps prior watch window(s) ({covered}); "
                "kept because a tighter or shifted micro-window can reveal different details."
            )
        kept.append((start, end))
    return kept, notes


def read_segment_ledger(ledger_dir: Path) -> list[tuple[float, float, float | None]]:
    ledger_path = ledger_dir / "covered.json"
    try:
        value = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else []
    except Exception:
        return []
    if not isinstance(value, list):
        return []
    cleaned: list[tuple[float, float, float | None]] = []
    for item in value:
        try:
            if not isinstance(item, (list, tuple)) or len(item) not in (2, 3):
                continue
            start = float(item[0])
            end = float(item[1])
            fps = float(item[2]) if len(item) == 3 and item[2] is not None else None
        except Exception:
            continue
        if not (math.isfinite(start) and math.isfinite(end) and start >= 0 and end > start):
            continue
        if fps is not None and (not math.isfinite(fps) or fps <= 0):
            fps = None
        cleaned.append((start, end, fps))
    return cleaned


def update_segment_ledger(ledger_dir: Path, segments: list[tuple[float, float]], *, fps: float) -> None:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / "covered.json"
    ledger = read_segment_ledger(ledger_dir)
    known = {(start, end, entry_fps) for start, end, entry_fps in ledger}
    for start, end in segments:
        if (start, end, fps) not in known:
            ledger.append((start, end, fps))
            known.add((start, end, fps))
    ledger_path.write_text(
        json.dumps([list(entry) for entry in ledger], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def video_ledger_id(video_path: Path) -> str:
    stat = video_path.stat()
    key = f"{video_path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"{video_path.stem}_{digest}"


def video_frames_dir_id(video_path: Path) -> str:
    """默认帧目录标识: stem + 路径哈希。只按 stem 命名时, 不同目录下的同名
    视频 (素材库常见) 会共用 {stem}_full/{stem}_watch, 后一次 ingest/watch 的
    reset_frames_dir 会把前一视频的 contact sheet 全部删掉 — 超过内联上限、
    等着被 Read 的溢出 sheet 直接消失。"""
    digest = hashlib.sha256(str(video_path.resolve()).encode("utf-8")).hexdigest()[:8]
    return f"{video_path.stem}_{digest}"


def merge_watch_results(
    results: list[ToolResult],
    ledger_notes: list[str],
    segments: list[tuple[float, float]],
    *,
    update_ledger: bool,
    ledger_dir: Path,
) -> ToolResult:
    failed = sum(1 for result in results if result.text.startswith("[ERROR]"))
    text = "\n\n".join(result.text for result in results)
    if failed:
        text = (
            f"[ERROR] {failed}/{len(results)} watch segment(s) failed; no ledger/session state was updated. "
            "Per-segment output follows.\n\n" + text
        )
    if ledger_notes:
        text += "\n\n[window ledger]\n" + "\n".join(ledger_notes)
    if update_ledger:
        text += f"\n\n[window ledger] recorded {len(segments)} watched segment(s) in {ledger_dir / 'covered.json'}."
    image_paths = [path for result in results for path in result.image_paths]
    artifacts = [path for result in results for path in result.artifacts]
    data = {
        "tool": "video_watch_segment",
        "segments": [{"start_time": start, "end_time": end} for start, end in segments],
        "failed_segment_count": failed,
        "results": [result.data for result in results],
        "ledger_notes": ledger_notes,
    }
    return ToolResult(text=text, data=data, artifacts=artifacts, image_paths=image_paths)


def build_video_observation(
    *,
    ctx: RunContext,
    defaults: VideoSamplingDefaults,
    video_path: Path,
    output_json: Path,
    frames_dir: Path,
    label: str,
    prompt: str,
    transcript_text: str,
    original_time_range: tuple[float, float] | None,
    extra_data: dict | None = None,
) -> ToolResult:
    validate_defaults(defaults)
    started = time.perf_counter()
    output_json.parent.mkdir(parents=True, exist_ok=True)
    signature = observation_signature(video_path, defaults, prompt, transcript_text,
                                      original_time_range, extra_data, frames_dir)
    reused = False
    cached = read_cached_observation(output_json, signature)
    if cached is not None:
        sheets = [Path(path) for path in cached.get("sheet_paths", [])]
        frames = []
        media = cached.get("media", {})
        sampled_frame_count = int(media.get("sampled_frames") or len(cached.get("frame_paths", [])) or 0)
        reused = True
    else:
        reset_error = reset_frames_dir(frames_dir, ctx)
        if reset_error:
            return ToolResult(text=f"[ERROR] {label}: {reset_error}")

        try:
            frames, media = sample_video_frames(video_path, defaults, frames_dir / "frames", source_time_range=original_time_range)
            sheets = build_contact_sheets(frames, frames_dir / "sheets", defaults)
            sampled_frame_count = len(frames)
        except Exception as exc:
            return ToolResult(text=f"[ERROR] {label} frame sampling failed: {exc}")

        payload = {
            "tool": label,
            "video_path": str(video_path),
            "original_time_range": original_time_range,
            "used_time_range": media.get("source_time_range"),
            "prompt_for_main_agent": prompt,
            "transcript_text": transcript_text,
            "media": media,
            "frame_paths": [str(frame.path) for frame in frames if frame.path],
            "sheet_paths": [str(path) for path in sheets],
            "cache_signature": signature,
            "notes": [
                "No model API was called by this tool.",
                "The Claude Code main model must inspect the returned timestamped images directly.",
                "Every visual observation must be evaluated together with the matching transcript text.",
            ],
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            **(extra_data or {}),
        }
        output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    transcript_block = transcript_for_inline(transcript_text)
    sheet_lines = "\n".join(f"- {ctx.virtualize(path)}" for path in sheets)
    frame_note = (
        "Frame timestamps are source-video timestamps within original_time_range."
        if original_time_range else
        "Frame timestamps are source-video timestamps."
    )
    text = (
        f"{label} completed: sampled {sampled_frame_count} frame(s) and built {len(sheets)} timestamped "
        f"contact sheet(s). The sheets are inlined below for the Claude Code main model to inspect; "
        "this tool did not call any model API.\n\n"
        f"Observation JSON: {ctx.virtualize(output_json)}\n"
        f"Sheets:\n{sheet_lines}\n\n"
        f"{frame_note}\n"
        "Read sheet cells left-to-right and top-to-bottom. Adjacent timestamp jumps mean the sampler "
        "did not include intermediate frames; call video_watch_segment with a tighter time range and "
        "higher fps when motion or a cut point is unclear.\n\n"
        f"Task prompt for the main model:\n{prompt}\n\n"
        "Matching transcript for these images:\n"
        "<transcript>\n"
        f"{transcript_block}\n"
        "</transcript>"
    )
    if reused:
        text += "\n\n[note] Reused previously generated contact sheet(s) for the same video, time range, prompt, transcript, and sampling settings."
    return ToolResult(
        text=text,
        data={
            "tool": label,
            "output_json": str(output_json),
            "video_path": str(video_path),
            "used_time_range": media.get("source_time_range"),
            "image_count": len(sheets),
            "sampled_frames": sampled_frame_count,
            "media": media,
            "reused": reused,
            **(extra_data or {}),
        },
        artifacts=[str(output_json), str(frames_dir)],
        image_paths=[str(path) for path in sheets],
    )


def reset_frames_dir(frames_dir: Path, ctx: RunContext) -> str | None:
    """Prepare a clean frames_dir. Stale frames are only deleted when the
    directory lives strictly inside the plugin work dir; arbitrary
    user-supplied directories are never removed."""
    resolved = frames_dir.resolve()
    work_dir = ctx.work_dir.resolve()
    if resolved != work_dir and resolved.is_relative_to(work_dir):
        if resolved.exists():
            shutil.rmtree(resolved)
        resolved.mkdir(parents=True, exist_ok=True)
        return None
    if resolved.exists() and any(resolved.iterdir()):
        return (
            f"save_frames_dir {resolved} already exists, is not empty, and is outside the plugin work dir "
            f"({work_dir}); refusing to delete it. Pass an empty/new directory, or a directory under "
            f"{work_dir} to allow automatic cleanup."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return None


def transcript_for_inline(transcript_text: str) -> str:
    if not transcript_text:
        return "(No transcript available.)"
    if len(transcript_text) <= INLINE_TRANSCRIPT_CHAR_LIMIT:
        return transcript_text
    return (
        transcript_text[:INLINE_TRANSCRIPT_CHAR_LIMIT]
        + f"\n\n[TRUNCATED in tool text at {INLINE_TRANSCRIPT_CHAR_LIMIT} chars; full transcript is saved in observation JSON.]"
    )


def validate_defaults(defaults: VideoSamplingDefaults) -> None:
    if not math.isfinite(defaults.video_fps) or defaults.video_fps <= 0:
        raise ValueError("video_fps must be a finite number > 0")
    if defaults.video_t_patch_size <= 0:
        raise ValueError("video_t_patch_size must be > 0")
    if defaults.max_video_frames > MAX_INLINE_IMAGES:
        raise ValueError(f"max_video_frames must be <= {MAX_INLINE_IMAGES}")
    if defaults.sheet_cols <= 0 or defaults.sheet_max_cells <= 0:
        raise ValueError("sheet layout settings must be > 0")
    if defaults.sheet_width <= 0:
        raise ValueError("sheet_width must be > 0")
    if not (1 <= defaults.jpeg_quality <= 100):
        raise ValueError("jpeg_quality must be in [1, 100]")


def observation_signature(
    video_path: Path,
    defaults: VideoSamplingDefaults,
    prompt: str,
    transcript_text: str,
    original_time_range: tuple[float, float] | None,
    extra_data: dict | None,
    frames_dir: Path,
) -> dict[str, Any]:
    stat = video_path.stat()
    transcript_hash = hashlib.sha256(transcript_text.encode("utf-8")).hexdigest()
    return {
        "video_path": str(video_path.resolve()),
        "video_size": stat.st_size,
        "video_mtime_ns": stat.st_mtime_ns,
        "sampling": defaults.__dict__,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "original_time_range": list(original_time_range) if original_time_range else None,
        "transcript_sha256": transcript_hash,
        # 缓存命中必须绑定帧目录: 否则换 save_frames_dir 复用旧缓存时, 新目录
        # 不会被创建、artifacts 却声称 frames 在新目录; 反向组合还会让 reset
        # 删掉另一个缓存 JSON 引用的 sheets
        "frames_dir": str(frames_dir.resolve()),
        "extra": extra_data or {},
    }


def read_cached_observation(output_json: Path, signature: dict[str, Any]) -> dict | None:
    if not output_json.is_file():
        return None
    try:
        payload = json.loads(output_json.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("cache_signature") != signature:
        return None
    sheets = [Path(path) for path in payload.get("sheet_paths", [])]
    if not sheets or not all(path.is_file() for path in sheets):
        return None
    return payload


def video_metadata(video_path: Path) -> dict[str, Any]:
    vali_meta = vali_video_metadata(video_path)
    if vali_meta is not None:
        return vali_meta
    try:
        import cv2

        capture = cv2.VideoCapture(str(video_path))
        if capture.isOpened():
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            duration = frame_count / fps if fps > 0 and frame_count > 0 else None
            capture.release()
            if frame_count > 0 and fps > 0:
                return {
                    "frame_count": frame_count,
                    "fps": fps,
                    "width": width,
                    "height": height,
                    "duration": duration,
                    "reader": "opencv",
                }
        capture.release()
    except Exception:
        pass
    return ffprobe_metadata(video_path)


def vali_video_metadata(video_path: Path) -> dict[str, Any] | None:
    try:
        import python_vali as vali

        reader = vali.PyDecoder(str(video_path), opts={}, gpu_id=-1)
        frame_count = int(reader.NumFrames or 0)
        fps = float(reader.Framerate or 0.0)
        width = int(reader.Width or 0)
        height = int(reader.Height or 0)
        if frame_count > 0 and fps > 0:
            return {
                "frame_count": frame_count,
                "fps": fps,
                "width": width,
                "height": height,
                "duration": frame_count / fps,
                "reader": "python_vali",
            }
    except Exception:
        return None
    return None


def parse_rate(rate: str | None) -> float:
    if not rate or rate == "0/0":
        return 0.0
    if "/" in rate:
        num, den = rate.split("/", 1)
        den_f = float(den)
        return float(num) / den_f if den_f else 0.0
    return float(rate)


def ffprobe_metadata(video_path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames,r_frame_rate,duration:format=duration",
        "-of", "json", str(video_path),
    ]
    proc = run_proc(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    payload = json.loads(proc.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError(f"Could not read video metadata: {video_path}")
    stream = streams[0]
    fps = parse_rate(stream.get("r_frame_rate"))
    duration = ffprobe_duration(stream.get("duration"))
    if duration is None:
        fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
        duration = ffprobe_duration(fmt.get("duration")) if isinstance(fmt, dict) else None
    frame_count_raw = stream.get("nb_frames")
    frame_count = int(frame_count_raw) if frame_count_raw and frame_count_raw.isdigit() else int((duration or 0.0) * fps)
    if frame_count <= 0 or fps <= 0 or duration is None:
        raise ValueError(f"Invalid video metadata from ffprobe: {video_path}")
    return {
        "frame_count": frame_count,
        "fps": fps,
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration": duration,
        "reader": "ffmpeg",
    }


def ffprobe_duration(value: object) -> float | None:
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(duration) or duration <= 0:
        return None
    return duration


def align_frame_count_to_t_patch(num_frames: int, max_frame_count: int, t_patch: int) -> int:
    max_frame_count = int(max_frame_count)
    num_frames = min(max(int(num_frames), 1), max_frame_count)
    if t_patch > 1 and num_frames % t_patch != 0:
        max_aligned_frames = (max_frame_count // t_patch) * t_patch
        if max_aligned_frames <= 0:
            raise ValueError(f"max_video_frames={max_frame_count} must be at least video_t_patch_size={t_patch}")
        num_frames = ((num_frames + t_patch - 1) // t_patch) * t_patch
        num_frames = min(num_frames, max_aligned_frames)
    return num_frames


def resolve_sample_count(meta: dict[str, Any], defaults: VideoSamplingDefaults) -> int:
    if defaults.video_frame_count is not None:
        requested = defaults.video_frame_count
    else:
        duration = meta.get("duration") or (meta["frame_count"] / meta["fps"] if meta.get("fps") else 0)
        if defaults.video_sampling_mode == "prod":
            requested = int(float(duration) * defaults.video_fps)
        else:
            requested = math.ceil(float(duration) * defaults.video_fps)
    if defaults.video_sampling_mode == "prod":
        return align_frame_count_to_t_patch(requested, defaults.max_video_frames, defaults.video_t_patch_size)
    requested = max(1, requested)
    return min(requested, defaults.max_video_frames, meta["frame_count"])


def prod_dynamic_fps_indices(
    total_frames: int,
    fps: float,
    num_frames: int,
    target_fps: float,
    t_patch_size: int,
) -> tuple[list[int], list[float]]:
    import numpy as np

    if total_frames <= 0:
        raise ValueError("Video has no readable frames.")
    if fps <= 0:
        raise ValueError(f"Video FPS must be positive, got {fps}.")
    if target_fps <= 0:
        raise ValueError(f"video_fps must be positive, got {target_fps}.")
    if num_frames == -1:
        return [0], [0.0]

    duration_per_frame = 1 / fps
    timestamps = [i * duration_per_frame for i in range(total_frames)]
    duration = timestamps[-1]
    if total_frames < num_frames:
        frame_indices = [math.floor(i * total_frames / num_frames) for i in range(num_frames)]
    else:
        frame_indices = []
        current_second = 0
        threshold_idx = 1
        inv_fps = 1 / target_fps
        for frame_index in range(total_frames):
            if timestamps[frame_index] >= current_second:
                current_second = threshold_idx * inv_fps
                frame_indices.append(frame_index)
                threshold_idx += 1
                if current_second > duration - inv_fps:
                    break
    if len(frame_indices) < 3:
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int).tolist()
    if len(frame_indices) < num_frames:
        frame_indices = np.linspace(frame_indices[0], frame_indices[-1], num_frames, dtype=int).tolist()
    elif len(frame_indices) > num_frames:
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int).tolist()
    while len(frame_indices) % t_patch_size != 0:
        frame_indices.append(frame_indices[-1])
    return frame_indices, timestamps


def uniform_indices(total: int, count: int) -> list[int]:
    if total <= 0:
        raise ValueError("Video has no readable frames.")
    count = min(max(1, count), total)
    if count == 1:
        return [0]
    return sorted({round(i * (total - 1) / (count - 1)) for i in range(count)})


def sample_video_frames(
    video_path: Path,
    defaults: VideoSamplingDefaults,
    save_dir: Path | None = None,
    source_time_range: tuple[float, float] | None = None,
) -> tuple[list[SampledFrame], dict]:
    from PIL import Image
    import cv2

    meta = video_metadata(video_path)
    if source_time_range is None:
        range_start = 0.0
        range_end = float(meta.get("duration") or (meta["frame_count"] / meta["fps"]))
        used_time_range = None
        range_frame_offset = 0
        range_frame_count = meta["frame_count"]
        sample_meta = meta
    else:
        range_start, range_end = source_time_range
        if range_start < 0 or range_end < 0:
            raise ValueError("source_time_range start/end must be >= 0")
        if range_end <= range_start:
            raise ValueError("source_time_range end must be greater than start")
        duration = float(meta.get("duration") or (meta["frame_count"] / meta["fps"]))
        if range_start >= duration:
            raise ValueError(f"source_time_range start {range_start:.3f}s is beyond video duration {duration:.3f}s")
        if range_end > duration + TIME_RANGE_TOLERANCE_SECONDS:
            raise ValueError(f"source_time_range end {range_end:.3f}s exceeds video duration {duration:.3f}s")
        range_end = min(range_end, duration)
        used_time_range = (range_start, range_end)
        range_frame_offset = max(0, int(math.ceil(range_start * meta["fps"] - 1e-9)))
        range_last_frame = min(meta["frame_count"] - 1, int(math.floor(range_end * meta["fps"] + 1e-9)))
        if range_frame_offset > range_last_frame:
            midpoint_frame = int(round(((range_start + range_end) / 2) * meta["fps"]))
            midpoint_frame = min(meta["frame_count"] - 1, max(0, midpoint_frame))
            range_frame_offset = midpoint_frame
            range_last_frame = midpoint_frame
        range_frame_count = max(1, range_last_frame - range_frame_offset + 1)
        sample_meta = {**meta, "frame_count": range_frame_count, "duration": range_end - range_start}

    sample_count = resolve_sample_count(sample_meta, defaults)
    if defaults.video_sampling_mode == "prod":
        indices, _ = prod_dynamic_fps_indices(
            range_frame_count, meta["fps"], sample_count, defaults.video_fps, defaults.video_t_patch_size
        )
    else:
        indices = uniform_indices(range_frame_count, sample_count)

    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        capture = None
    frames: list[SampledFrame] = []
    for out_idx, local_frame_idx in enumerate(indices):
        frame_idx = range_frame_offset + local_frame_idx
        timestamp = frame_idx / meta["fps"]
        if capture is not None:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = capture.read()
            if not ok:
                continue
            # POS_MSEC must be read AFTER read(): before it, the FFmpeg backend
            # still reports the PTS of the frame decoded during the seek
            # (frame_idx - 1), which labeled every contact sheet one frame
            # early. After read() it is the PTS of the frame just returned.
            pos_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
            if pos_ms and pos_ms > 0:
                # Decoder-reported PTS is more accurate than frame_idx/fps for
                # variable-frame-rate sources.
                timestamp = pos_ms / 1000.0
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
        else:
            image = read_frame_with_ffmpeg(video_path, timestamp)
        image = normalize_video_frame(image, defaults.video_frame_normalize_jpeg_quality)
        path = None
        if save_dir is not None:
            path = save_dir / f"{video_path.stem}_{out_idx:03d}_frame{frame_idx}.jpg"
            image.save(path, quality=90)
        frames.append(SampledFrame(label="", timestamp=float(timestamp), frame_index=int(frame_idx), image=image, path=path))
    if capture is not None:
        capture.release()
    if not frames:
        raise ValueError(f"No frames could be sampled from video: {video_path}")
    # Label with the actual sampled count so skipped/unreadable frames cannot
    # desynchronize the "Frame i/N" numbering.
    for seq, frame in enumerate(frames, start=1):
        if defaults.video_label_mode == "none":
            frame.label = ""
        elif defaults.video_label_mode == "frame":
            frame.label = f"Frame {seq:03d}/{len(frames):03d}"
        else:
            frame.label = f"Frame {seq:03d}/{len(frames):03d}; timestamp={frame.timestamp:.6f}s"
    formatted_indices = [
        f"{round(frame.timestamp, 1)} seconds"
        for frame in frames[::defaults.video_t_patch_size if defaults.video_sampling_mode == "prod" else 1]
    ]
    return frames, {
        **meta,
        "sample_fps": defaults.video_fps,
        "sampled_frames": len(frames),
        "sampling_mode": defaults.video_sampling_mode,
        "duration_for_sampling": sample_meta.get("duration"),
        "source_time_range": used_time_range,
        "t_patch_size": defaults.video_t_patch_size,
        "raw_frame_indices": [frame.frame_index for frame in frames],
        "raw_frame_timestamps_sec": [round(frame.timestamp, 6) for frame in frames],
        "prod_frame_indices": formatted_indices,
    }


def read_frame_with_ffmpeg(video_path: Path, timestamp: float):
    from PIL import Image

    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{timestamp:.6f}", "-i", str(video_path),
        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ]
    proc = run_proc(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not proc.stdout:
        raise ValueError(f"ffmpeg did not return a frame at {timestamp:.2f}s from {video_path}")
    with Image.open(io.BytesIO(proc.stdout)) as image:
        return image.convert("RGB")


def normalize_video_frame(image, quality: int):
    from PIL import Image

    if quality <= 0:
        return image
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    with Image.open(buffer) as normalized:
        return normalized.convert("RGB")


def build_contact_sheets(frames: list[SampledFrame], out_dir: Path, defaults: VideoSamplingDefaults) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont

    out_dir.mkdir(parents=True, exist_ok=True)
    cols = defaults.sheet_cols
    max_cells = defaults.sheet_max_cells
    cell_w = max(1, defaults.sheet_width // cols)
    label_font_size = max(20, min(34, cell_w // 12))
    font = None
    font_paths = []
    font_dirs = (
        os.environ.get("VE_FONT_DIRS")
        or os.environ.get("VIDEO_EDIT_FONT_DIRS")
        or ""
    )
    for raw_dir in [p for p in font_dirs.split(os.pathsep) if p.strip()]:
        font_dir = Path(raw_dir)
        if font_dir.is_dir():
            files = [
                p for p in sorted(font_dir.iterdir())
                if p.is_file() and p.suffix.lower() in {".ttf", ".ttc", ".otf"}
            ]
            bold = [p for p in files if "bold" in p.name.lower()]
            font_paths.extend(str(p) for p in [*bold, *files])
    font_paths.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ])
    # 上面全是 Linux 路径; mac/Windows 的系统字体在别处 (见 fonts.py)。找不到就
    # 走下面的 PIL 默认位图字体 —— 时间戳标签只有数字, 不至于因此失效。
    platform_font = find_cjk_font("bold")
    if platform_font:
        font_paths.append(platform_font)
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, label_font_size)
            break
        except OSError:
            continue
    if font is None:
        try:
            font = ImageFont.load_default(size=label_font_size)
        except TypeError:
            font = ImageFont.load_default()
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    probe_bbox = probe.textbbox((0, 0), "00.00s", font=font)
    label_h = max(30, probe_bbox[3] - probe_bbox[1] + 14)
    paths: list[Path] = []

    for chunk_idx, chunk_start in enumerate(range(0, len(frames), max_cells)):
        chunk = frames[chunk_start:chunk_start + max_cells]
        cells = []
        for frame in chunk:
            image = frame.image.convert("RGB")
            w, h = image.size
            # cell 高度加上界: 极端纵横比 (h/w 很大) 会把整张 sheet 推过 JPEG
            # 65500px 尺寸上限, 保存直接抛错、整次观察失败
            image_h = max(1, min(int(h * cell_w / max(1, w)), max(1, cell_w * 4 - label_h)))
            resized = image.resize((cell_w, image_h), Image.Resampling.LANCZOS)
            cell = Image.new("RGB", (cell_w, label_h + image_h), (0, 0, 0))
            draw = ImageDraw.Draw(cell)
            label = f"{frame.timestamp:.2f}s"
            bbox = draw.textbbox((0, 0), label, font=font)
            text_h = bbox[3] - bbox[1]
            text_y = max(0, (label_h - text_h) // 2 - bbox[1])
            draw.rectangle((0, 0, cell_w, label_h), fill=(12, 15, 20))
            draw.text((12, text_y), label, fill=(255, 255, 255), font=font)
            draw.line((0, label_h - 1, cell_w, label_h - 1), fill=(56, 64, 75))
            cell.paste(resized, (0, label_h))
            cells.append(cell)

        cell_h = max(cell.height for cell in cells)
        padded = []
        for cell in cells:
            if cell.height == cell_h:
                padded.append(cell)
                continue
            canvas = Image.new("RGB", (cell_w, cell_h), (0, 0, 0))
            canvas.paste(cell, (0, 0))
            padded.append(canvas)
        while len(padded) % cols:
            padded.append(Image.new("RGB", (cell_w, cell_h), (0, 0, 0)))

        rows = []
        for row_start in range(0, len(padded), cols):
            row = Image.new("RGB", (cell_w * cols, cell_h), (0, 0, 0))
            for i, cell in enumerate(padded[row_start:row_start + cols]):
                row.paste(cell, (i * cell_w, 0))
            rows.append(row)
        sheet = Image.new("RGB", (cell_w * cols, cell_h * len(rows)), (0, 0, 0))
        for i, row in enumerate(rows):
            sheet.paste(row, (0, i * cell_h))

        start_ms = int(round(chunk[0].timestamp * 1000))
        end_ms = int(round(chunk[-1].timestamp * 1000))
        # 文件名带 chunk 序号: 亚帧窗口 + 高 fps 下多个 chunk 的首末时间戳可以
        # 完全相同, 只按时间戳命名会后写覆盖前写, sheet_paths 里出现重复路径
        path = out_dir / f"video_grid_{start_ms}ms_{end_ms}ms_p{chunk_idx:02d}.jpg"
        sheet.save(path, quality=defaults.jpeg_quality)
        paths.append(path)
    return paths


def with_suffix_before_ext(path: Path, suffix: str) -> Path:
    return path.with_name(f"{path.stem}_{suffix}{path.suffix or '.json'}")


def default_full_prompt() -> str:
    return (
        "Inspect the complete video directly from the timestamped sheets. Identify people, scenes, "
        "actions, narrative/content structure, visual quality, candidate usable ranges, and ranges "
        "that need local high-FPS rewatch before editing."
    )


def default_detail_prompt() -> str:
    return (
        "Inspect this local segment directly from the timestamped sheets. Judge cut usability, "
        "motion continuity, facial/action details, occlusion, subtitle/overlay conflicts, and whether "
        "the segment should be used or avoided."
    )
