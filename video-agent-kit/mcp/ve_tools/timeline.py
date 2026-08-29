from __future__ import annotations

import copy
import hashlib
import json
import math
import shutil
import subprocess
from .ffproc import run_proc
import time
from pathlib import Path
from typing import Any

from .result import ToolResult
from .run_context import RunContext


VIDEO_TRACK_TYPES = {
    "v",
    "v1",
    "video",
    "video_1",
    "main",
    "primary",
    "footage",
    "source",
    "main_video",
    "primary_video",
    "source_video",
    "主视频",
    "主视频轨",
    "主轨",
    "视频",
    "视频轨",
    "画面",
}
AUDIO_TRACK_TYPES = {
    "a",
    "a1",
    "audio",
    "music",
    "bgm",
    "voiceover",
    "narration",
    "dialogue",
    "sound",
    "sfx",
    "音频",
    "音乐",
    "旁白",
    "对白",
    "音效",
}
TEXT_TRACK_TYPES = {
    "subtitle",
    "subtitles",
    "caption",
    "captions",
    "text",
    "title",
    "lower_third",
    "chapter_card",
    "callout",
    "字幕",
    "标题",
    "下三分之一",
    "章节卡",
    "标注",
}
OVERLAY_TRACK_TYPES = {
    "overlay",
    "image",
    "graphic",
    "sticker",
    "logo",
    "watermark",
    "b_roll",
    "broll",
    "叠加",
    "贴纸",
    "水印",
    "图形",
}
KNOWN_TRACK_TYPES = VIDEO_TRACK_TYPES | AUDIO_TRACK_TYPES | TEXT_TRACK_TYPES | OVERLAY_TRACK_TYPES
PATCH_OPERATION_KEYS = {
    "add_assets",
    "update_assets",
    "remove_asset_indices",
    "add_tracks",
    "insert_tracks",
    "replace_tracks",
    "remove_track_indices",
    "remove_clip_indices",
    "add_clips",
    "replace_clips",
    "insert_clips",
    "update_clips",
    "move_clips",
    "set_timeline_fields",
    "set_track_fields",
}
STRUCTURAL_TRACK_PATCH_KEYS = {
    "add_tracks",
    "insert_tracks",
    "replace_tracks",
    "remove_track_indices",
}
CLIP_PATCH_KEYS = {
    "remove_clip_indices",
    "add_clips",
    "replace_clips",
    "insert_clips",
    "update_clips",
    "move_clips",
}
PROTECTED_TIMELINE_PATCH_FIELDS = {"clips", "tracks"}


def load_timeline(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def timeline_clips(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("clips"), list):
        return [clip for clip in data["clips"] if isinstance(clip, dict)]
    tracks = data.get("tracks")
    if isinstance(tracks, list):
        clips: list[dict[str, Any]] = []
        for track in tracks:
            if isinstance(track, dict) and isinstance(track.get("clips"), list):
                track_type = track.get("type") or track.get("track_type") or track.get("name")
                for clip in track["clips"]:
                    if isinstance(clip, dict):
                        item = dict(clip)
                        if "track_type" in item and "clip_track_type" not in item:
                            item["clip_track_type"] = item["track_type"]
                        item["track_type"] = track_type
                        clips.append(item)
        return clips
    return []


def validate_timeline(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not args.get("timeline_path"):
        return ToolResult(text="[ERROR] timeline_path is required")
    timeline_path = ctx.resolve(args["timeline_path"])
    if not timeline_path.is_file():
        return ToolResult(text=f"[ERROR] timeline not found: {timeline_path}")
    if not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffprobe not found on PATH")
    try:
        data = load_timeline(timeline_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] invalid JSON: {exc}")

    clips, issues = validate_timeline_data(data, ctx)
    status = "pass" if not any(i["severity"] == "error" for i in issues) else "fail"
    project_contract = timeline_project_contract(data)
    report = {
        "status": status,
        "timeline_path": str(timeline_path),
        "timeline_sha256": file_sha256(timeline_path),
        "clip_count": len(clips),
        "project_contract": project_contract,
        "issues": issues,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json = ctx.resolve(args.get("output_json") or f"out/{timeline_path.stem}_validation.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return ToolResult(
        text=f"Timeline validation {status}: {ctx.virtualize(output_json)}",
        data=report,
        artifacts=[str(output_json)],
    )


def validate_timeline_data(data: dict[str, Any], ctx: RunContext) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if not shutil.which("ffprobe"):
        issues.append({"severity": "error", "message": "ffprobe not found on PATH"})
    if not isinstance(data, dict):
        return [], issues + [{"severity": "error", "message": "timeline JSON root must be an object"}]
    if isinstance(data.get("clips"), list) and isinstance(data.get("tracks"), list):
        issues.append({"severity": "error", "message": "timeline must use either top-level clips[] or tracks[], not both"})
    check_project_shape(data, issues)
    check_project_contract(data, issues)
    check_container_shape(data, issues)
    check_asset_references_and_track_layout(data, issues)
    tracks_mode = not isinstance(data.get("clips"), list) and isinstance(data.get("tracks"), list)
    clips = timeline_clips(data)
    if not clips:
        issues.append({"severity": "error", "message": "timeline must contain clips[] or tracks[].clips[]"})
    duration_cache: dict[str, float | None] = {}
    for idx, clip in enumerate(clips):
        check_clip(idx, clip, ctx, issues, tracks_mode=tracks_mode, duration_cache=duration_cache)
    return clips, issues


def check_asset_references_and_track_layout(data: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    assets = data.get("assets")
    asset_ids = {
        str(asset.get("id"))
        for asset in assets
        if isinstance(asset, dict) and str(asset.get("id") or "").strip()
    } if isinstance(assets, list) else set()
    content_end = 0.0
    tracks = data.get("tracks")
    if not isinstance(tracks, list):
        return
    for track_idx, track in enumerate(tracks):
        if not isinstance(track, dict) or not isinstance(track.get("clips"), list):
            continue
        track_type = normalize_track_type(track.get("type") or track.get("track_type") or track.get("name") or "")
        cursor = 0.0
        occupied: list[tuple[float, float, int]] = []
        for clip_idx, clip in enumerate(track["clips"]):
            if not isinstance(clip, dict):
                continue
            asset_id = clip.get("asset_id")
            if asset_id is not None and str(asset_id) not in asset_ids:
                issues.append({
                    "severity": "error",
                    "track": track_idx,
                    "clip": clip_idx,
                    "message": f"clip asset_id references unknown asset: {asset_id}",
                })
            render_duration = clip_render_duration(clip)
            timeline_start = coerce_timeline_number(clip.get("timeline_start", clip.get("position")))
            if timeline_start is None:
                timeline_start = cursor
            if render_duration is None:
                continue
            timeline_end = timeline_start + render_duration
            cursor = max(cursor, timeline_end)
            content_end = max(content_end, timeline_end)
            for prev_start, prev_end, prev_idx in occupied:
                if timeline_start < prev_end - 0.01 and timeline_end > prev_start + 0.01:
                    severity = "warning" if track_type in VIDEO_TRACK_TYPES else "error"
                    issues.append({
                        "severity": severity,
                        "track": track_idx,
                        "clip": clip_idx,
                        "message": (
                            f"clip timeline range overlaps clip {prev_idx} on the same track "
                            f"({timeline_start:.3f}-{timeline_end:.3f}s vs {prev_start:.3f}-{prev_end:.3f}s)"
                        ),
                    })
            occupied.append((timeline_start, timeline_end, clip_idx))
            for key in ("transition_in", "transition_out"):
                value = clip.get(key)
                if isinstance(value, dict):
                    transition_duration = coerce_timeline_number(value.get("duration"))
                    if transition_duration is not None and transition_duration > render_duration:
                        issues.append({
                            "severity": "error",
                            "track": track_idx,
                            "clip": clip_idx,
                            "message": f"{key}.duration exceeds clip render duration",
                        })
    sequence = data.get("sequence")
    if isinstance(sequence, dict):
        declared_duration = coerce_timeline_number(sequence.get("duration"))
        if declared_duration is not None and content_end > declared_duration + 0.05:
            issues.append({
                "severity": "error",
                "message": (
                    f"sequence.duration {declared_duration:.3f}s is shorter than timeline content "
                    f"ending at {content_end:.3f}s"
                ),
            })


def clip_render_duration(clip: dict[str, Any]) -> float | None:
    start = coerce_timeline_number(clip.get("start", clip.get("start_time", clip.get("in", 0))))
    end = coerce_timeline_number(clip.get("end", clip.get("end_time", clip.get("out"))))
    duration = coerce_timeline_number(clip.get("duration"))
    if end is not None and start is not None:
        duration = end - start
    elif duration is None:
        timeline_start = coerce_timeline_number(clip.get("timeline_start", clip.get("position")))
        timeline_end = coerce_timeline_number(clip.get("timeline_end"))
        if timeline_start is not None and timeline_end is not None:
            duration = timeline_end - timeline_start
    if duration is None or not math.isfinite(duration) or duration <= 0:
        return None
    speed = coerce_timeline_number(clip.get("speed")) or 1.0
    if speed <= 0 or not math.isfinite(speed):
        return None
    return duration / speed


def timeline_project_contract(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"ok": False, "missing": ["root_object"]}
    missing: list[str] = []
    project = data.get("project")
    if not isinstance(project, dict) or not project:
        missing.append("project")
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        missing.append("assets")
    elif not any(
        isinstance(asset, dict)
        and any(str(asset.get(k) or "").strip() for k in ("path", "source", "input_path", "src"))
        for asset in assets
    ):
        missing.append("asset_path")
    if not isinstance(data.get("sequence"), dict) and not isinstance(data.get("output_canvas"), dict):
        missing.append("sequence_or_output_canvas")
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        missing.append("tracks")
    elif not any(isinstance(track, dict) and is_video_track(track) for track in tracks):
        missing.append("video_track")
    return {
        "ok": not missing,
        "missing": missing,
        "requires": ["project", "assets", "sequence_or_output_canvas", "tracks", "video_track"],
    }


def check_project_shape(data: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for key in ("project", "sequence", "output_canvas", "metadata"):
        if key in data and not isinstance(data.get(key), dict):
            issues.append({"severity": "error", "message": f"{key} must be an object when provided"})
    for key in ("assets", "markers", "transitions"):
        if key in data and not isinstance(data.get(key), list):
            issues.append({"severity": "error", "message": f"{key} must be an array when provided"})
    check_canvas_like(data.get("output_canvas"), "output_canvas", issues)
    sequence = data.get("sequence")
    if isinstance(sequence, dict):
        check_canvas_like(sequence.get("canvas") or sequence.get("output_canvas"), "sequence.canvas", issues)
        check_positive_number(sequence.get("fps"), "sequence.fps", issues)
        check_positive_number(sequence.get("duration"), "sequence.duration", issues)
        check_non_negative_number(sequence.get("start_time"), "sequence.start_time", issues)
        check_non_negative_number(sequence.get("timebase"), "sequence.timebase", issues)
    check_asset_entries(data.get("assets"), issues)
    check_marker_entries(data.get("markers"), issues)
    check_transition_entries(data.get("transitions"), issues)


def check_project_contract(data: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    project = data.get("project")
    if not isinstance(project, dict) or not project:
        issues.append({
            "severity": "error",
            "message": "project timeline contract requires a non-empty project object",
        })
    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        issues.append({
            "severity": "error",
            "message": "project timeline contract requires non-empty assets[]",
        })
    elif not any(
        isinstance(asset, dict)
        and any(str(asset.get(k) or "").strip() for k in ("path", "source", "input_path", "src"))
        for asset in assets
    ):
        issues.append({
            "severity": "error",
            "message": "project timeline contract requires at least one asset with path/source/input_path/src",
        })
    if not isinstance(data.get("sequence"), dict) and not isinstance(data.get("output_canvas"), dict):
        issues.append({
            "severity": "error",
            "message": "project timeline contract requires sequence{} or output_canvas{}",
        })
    tracks = data.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        issues.append({
            "severity": "error",
            "message": "project timeline contract requires tracks[]; legacy top-level clips[] is no longer sufficient for pipeline runs",
        })
    elif not any(isinstance(track, dict) and is_video_track(track) for track in tracks):
        issues.append({
            "severity": "error",
            "message": "project timeline contract requires at least one video/main track",
        })


def check_canvas_like(value: object, label: str, issues: list[dict[str, Any]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        issues.append({"severity": "error", "message": f"{label} must be an object"})
        return
    width = value.get("width")
    height = value.get("height")
    if width is not None:
        check_positive_integer(width, f"{label}.width", issues)
    if height is not None:
        check_positive_integer(height, f"{label}.height", issues)
    check_positive_number(value.get("fps"), f"{label}.fps", issues)


def check_asset_entries(value: object, issues: list[dict[str, Any]]) -> None:
    if value is None or not isinstance(value, list):
        return
    seen_ids: set[str] = set()
    for idx, asset in enumerate(value):
        if not isinstance(asset, dict):
            issues.append({"severity": "error", "asset": idx, "message": "asset must be an object"})
            continue
        asset_id = asset.get("id")
        if asset_id is not None:
            if not str(asset_id).strip():
                issues.append({"severity": "error", "asset": idx, "message": "asset.id must be non-empty"})
            elif str(asset_id) in seen_ids:
                issues.append({"severity": "error", "asset": idx, "message": f"duplicate asset.id: {asset_id}"})
            seen_ids.add(str(asset_id))
        if not any(str(asset.get(k) or "").strip() for k in ("path", "source", "input_path", "src")):
            issues.append({"severity": "warning", "asset": idx, "message": "asset has no path/source/input_path/src"})
        check_positive_number(asset.get("duration"), f"assets[{idx}].duration", issues)
        check_positive_integer(asset.get("width"), f"assets[{idx}].width", issues)
        check_positive_integer(asset.get("height"), f"assets[{idx}].height", issues)
        check_positive_number(asset.get("fps"), f"assets[{idx}].fps", issues)


def check_marker_entries(value: object, issues: list[dict[str, Any]]) -> None:
    if value is None or not isinstance(value, list):
        return
    for idx, marker in enumerate(value):
        if not isinstance(marker, dict):
            issues.append({"severity": "error", "marker": idx, "message": "marker must be an object"})
            continue
        time_value = marker.get("time", marker.get("start"))
        if time_value is None:
            issues.append({"severity": "error", "marker": idx, "message": "marker needs time/start"})
        else:
            check_non_negative_number(time_value, f"markers[{idx}].time", issues)
        check_positive_number(marker.get("duration"), f"markers[{idx}].duration", issues)


def check_transition_entries(value: object, issues: list[dict[str, Any]]) -> None:
    if value is None or not isinstance(value, list):
        return
    for idx, transition in enumerate(value):
        if not isinstance(transition, dict):
            issues.append({"severity": "error", "transition": idx, "message": "transition must be an object"})
            continue
        if not str(transition.get("type") or transition.get("name") or "").strip():
            issues.append({"severity": "error", "transition": idx, "message": "transition needs type/name"})
        check_positive_number(transition.get("duration"), f"transitions[{idx}].duration", issues)
        at_clip = transition.get("at_clip")
        if at_clip is not None and not is_patch_index(at_clip):
            issues.append({"severity": "error", "transition": idx, "message": "transition.at_clip must be an integer"})


def check_container_shape(data: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if "clips" in data and not isinstance(data.get("clips"), list):
        issues.append({"severity": "error", "message": "clips must be an array"})
    if "tracks" in data and not isinstance(data.get("tracks"), list):
        issues.append({"severity": "error", "message": "tracks must be an array"})
    if isinstance(data.get("clips"), list):
        for idx, clip in enumerate(data["clips"]):
            if not isinstance(clip, dict):
                issues.append({"severity": "error", "clip": idx, "message": "clip must be an object"})
    if isinstance(data.get("tracks"), list):
        for track_idx, track in enumerate(data["tracks"]):
            if not isinstance(track, dict):
                issues.append({"severity": "error", "track": track_idx, "message": "track must be an object"})
                continue
            check_track_shape(track_idx, track, issues)
            clips = track.get("clips")
            if not isinstance(clips, list):
                issues.append({"severity": "error", "track": track_idx, "message": "track.clips must be an array"})
                continue
            for clip_idx, clip in enumerate(clips):
                if not isinstance(clip, dict):
                    issues.append({
                        "severity": "error",
                        "track": track_idx,
                        "clip": clip_idx,
                        "message": "clip must be an object",
                    })


def check_track_shape(track_idx: int, track: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    track_type_raw = track.get("type") or track.get("track_type") or track.get("name") or ""
    track_type = normalize_track_type(track_type_raw)
    if track_type and track_type not in KNOWN_TRACK_TYPES:
        issues.append({
            "severity": "warning",
            "track": track_idx,
            "message": f"unknown track type/name: {track_type_raw}",
        })
    for key in ("enabled", "muted", "locked", "visible", "solo"):
        if key in track and not isinstance(track.get(key), bool):
            issues.append({"severity": "error", "track": track_idx, "message": f"track.{key} must be boolean"})
    if "order" in track and not is_patch_index(track.get("order")):
        issues.append({"severity": "error", "track": track_idx, "message": "track.order must be an integer"})
    check_effects(track.get("effects"), f"tracks[{track_idx}].effects", issues)


def check_clip(
    idx: int,
    clip: dict[str, Any],
    ctx: RunContext,
    issues: list[dict[str, Any]],
    *,
    tracks_mode: bool = False,
    duration_cache: dict[str, float | None] | None = None,
) -> None:
    if duration_cache is None:
        duration_cache = {}
    # In tracks[] timelines, only subtitle/text/callout clips may be pure text.
    # Video, audio, and image/overlay clips need a source the renderer can read;
    # otherwise validation passes but render_preview later feeds an empty path to
    # ffmpeg.
    clip_track_type = normalize_track_type(clip.get("track_type") or "")
    is_video_clip = not tracks_mode or clip_track_type in VIDEO_TRACK_TYPES
    allows_text_only = tracks_mode and clip_track_type in TEXT_TRACK_TYPES
    source = clip.get("source") or clip.get("input_path") or clip.get("src")
    text_content = str(clip.get("text") or "").strip()
    source_path: Path | None = None
    if source:
        source_path = ctx.resolve(str(source))
        if not source_path.is_file():
            issues.append({"severity": "error", "clip": idx, "message": f"source not found: {source}"})
    elif is_video_clip or not allows_text_only:
        issues.append({"severity": "error", "clip": idx, "message": "missing source/input_path/src"})
    elif not text_content:
        issues.append({
            "severity": "error",
            "clip": idx,
            "message": "text/subtitle track clip needs source (media) or non-empty text",
        })
    if not str(clip.get("reason") or "").strip():
        issues.append({"severity": "error", "clip": idx, "message": "missing reason"})
    check_clip_project_fields(idx, clip, issues)
    text_only_clip = allows_text_only and source_path is None
    start = clip.get("start", clip.get("start_time", clip.get("in")))
    end = clip.get("end", clip.get("end_time", clip.get("out")))
    duration = clip.get("duration")
    start_f = coerce_timeline_number(start)
    if start_f is None and text_only_clip:
        start_f = 0.0
    if start_f is None:
        issues.append({"severity": "error", "clip": idx, "message": "start/start_time/in must be numeric"})
    end_f = coerce_timeline_number(end) if end is not None else None
    if end is not None and end_f is None:
        issues.append({"severity": "error", "clip": idx, "message": "end/end_time/out must be numeric"})
    duration_f = coerce_timeline_number(duration) if duration is not None else None
    if duration_f is None and end is None and text_only_clip:
        timeline_start = coerce_timeline_number(clip.get("timeline_start", clip.get("position")))
        timeline_end = coerce_timeline_number(clip.get("timeline_end"))
        if timeline_start is not None and timeline_end is not None:
            duration_f = timeline_end - timeline_start
    if duration is not None and duration_f is None:
        issues.append({"severity": "error", "clip": idx, "message": "duration must be numeric"})
    if start_f is not None and start_f < 0:
        issues.append({"severity": "error", "clip": idx, "message": "start must be >= 0"})
    if start_f is not None and not math.isfinite(start_f):
        issues.append({"severity": "error", "clip": idx, "message": "start must be finite"})
    if end_f is not None and not math.isfinite(end_f):
        issues.append({"severity": "error", "clip": idx, "message": "end must be finite"})
    if duration_f is not None and not math.isfinite(duration_f):
        issues.append({"severity": "error", "clip": idx, "message": "duration must be finite"})
    if end_f is not None and start_f is not None and end_f <= start_f:
        issues.append({"severity": "error", "clip": idx, "message": "end must be greater than start"})
    if end_f is None and duration_f is None:
        issues.append({"severity": "error", "clip": idx, "message": "clip needs end or duration"})
    if end_f is not None and duration_f is not None and start_f is not None:
        implied_duration = end_f - start_f
        if math.isfinite(implied_duration) and abs(implied_duration - duration_f) > 0.05:
            issues.append({
                "severity": "error",
                "clip": idx,
                "message": f"duration {duration_f:.3f}s does not match end-start {implied_duration:.3f}s",
            })
    resolved_end = end_f
    if resolved_end is None and start_f is not None and duration_f is not None:
        resolved_end = start_f + duration_f
    if duration_f is not None and duration_f <= 0:
        issues.append({"severity": "error", "clip": idx, "message": "duration must be greater than 0"})
    if source_path is not None and source_path.is_file() and resolved_end is not None:
        source_duration = cached_media_duration(source_path, duration_cache)
        if source_duration is not None and resolved_end > source_duration + 0.05:
            issues.append({
                "severity": "error",
                "clip": idx,
                "message": f"clip end {resolved_end:.3f}s exceeds source duration {source_duration:.3f}s",
            })


def check_clip_project_fields(idx: int, clip: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    check_non_negative_number(clip.get("timeline_start", clip.get("position")), f"clips[{idx}].timeline_start", issues)
    check_non_negative_number(clip.get("timeline_end"), f"clips[{idx}].timeline_end", issues)
    timeline_start = coerce_timeline_number(clip.get("timeline_start", clip.get("position")))
    timeline_end = coerce_timeline_number(clip.get("timeline_end")) if clip.get("timeline_end") is not None else None
    if timeline_start is not None and timeline_end is not None and timeline_end <= timeline_start:
        issues.append({"severity": "error", "clip": idx, "message": "timeline_end must be greater than timeline_start"})
    check_positive_number(clip.get("speed"), f"clips[{idx}].speed", issues)
    check_non_negative_number(clip.get("volume"), f"clips[{idx}].volume", issues)
    opacity = clip.get("opacity")
    if opacity is not None:
        parsed = coerce_timeline_number(opacity)
        if parsed is None or not math.isfinite(parsed) or parsed < 0 or parsed > 1:
            issues.append({"severity": "error", "clip": idx, "message": "opacity must be a finite number in [0, 1]"})
    for key in ("enabled", "muted", "locked", "visible"):
        if key in clip and not isinstance(clip.get(key), bool):
            issues.append({"severity": "error", "clip": idx, "message": f"{key} must be boolean"})
    for key in ("transition_in", "transition_out"):
        value = clip.get(key)
        if value is not None:
            check_transition_object(value, f"clips[{idx}].{key}", issues)
    check_effects(clip.get("effects"), f"clips[{idx}].effects", issues)


def check_transition_object(value: object, label: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(value, dict):
        issues.append({"severity": "error", "message": f"{label} must be an object"})
        return
    if not str(value.get("type") or value.get("name") or "").strip():
        issues.append({"severity": "error", "message": f"{label} needs type/name"})
    check_positive_number(value.get("duration"), f"{label}.duration", issues)


def check_effects(value: object, label: str, issues: list[dict[str, Any]]) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        issues.append({"severity": "error", "message": f"{label} must be an array"})
        return
    for idx, effect in enumerate(value):
        if not isinstance(effect, dict):
            issues.append({"severity": "error", "message": f"{label}[{idx}] must be an object"})
            continue
        if not str(effect.get("type") or effect.get("name") or "").strip():
            issues.append({"severity": "error", "message": f"{label}[{idx}] needs type/name"})
        if "enabled" in effect and not isinstance(effect.get("enabled"), bool):
            issues.append({"severity": "error", "message": f"{label}[{idx}].enabled must be boolean"})


def check_positive_integer(value: object, label: str, issues: list[dict[str, Any]]) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        issues.append({"severity": "error", "message": f"{label} must be a positive integer"})


def check_positive_number(value: object, label: str, issues: list[dict[str, Any]]) -> None:
    if value is None:
        return
    parsed = coerce_timeline_number(value)
    if parsed is None or not math.isfinite(parsed) or parsed <= 0:
        issues.append({"severity": "error", "message": f"{label} must be a finite positive number"})


def check_non_negative_number(value: object, label: str, issues: list[dict[str, Any]]) -> None:
    if value is None:
        return
    parsed = coerce_timeline_number(value)
    if parsed is None or not math.isfinite(parsed) or parsed < 0:
        issues.append({"severity": "error", "message": f"{label} must be a finite number >= 0"})


def cached_media_duration(path: Path, cache: dict[str, float | None]) -> float | None:
    key = str(path)
    if key not in cache:
        cache[key] = media_duration_seconds(path)
    return cache[key]


def media_duration_seconds(path: Path) -> float | None:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=duration",
        "-of", "json",
        str(path),
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except Exception:
        return None
    fmt = data.get("format") if isinstance(data, dict) else {}
    value = safe_duration(fmt.get("duration")) if isinstance(fmt, dict) else None
    if value is not None:
        return value
    streams = data.get("streams") if isinstance(data, dict) else []
    if not isinstance(streams, list):
        return None
    values = [
        duration
        for stream in streams
        if isinstance(stream, dict)
        for duration in [safe_duration(stream.get("duration"))]
        if duration is not None
    ]
    return max(values) if values else None


def safe_duration(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(duration) or duration <= 0:
        return None
    return duration


def coerce_timeline_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed


def normalize_clip(clip: dict[str, Any], ctx: RunContext) -> dict[str, Any]:
    source = clip.get("source") or clip.get("input_path") or clip.get("src")
    start = float(clip.get("start", clip.get("start_time", clip.get("in", 0))))
    if clip.get("end", clip.get("end_time", clip.get("out"))) is not None:
        end = float(clip.get("end", clip.get("end_time", clip.get("out"))))
    else:
        end = start + float(clip["duration"])
    return {
        **clip,
        "source": str(ctx.resolve(str(source))),
        "start": start,
        "end": end,
        "duration": end - start,
    }


def timeline_diff(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("timeline_path"):
        return ToolResult(text="[ERROR] timeline_path is required")
    if not args.get("instructions"):
        return ToolResult(text="[ERROR] instructions is required")
    timeline_path = ctx.resolve(args["timeline_path"])
    if not timeline_path.is_file():
        return ToolResult(text=f"[ERROR] timeline not found: {timeline_path}")
    try:
        before = load_timeline(timeline_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] invalid JSON: {exc}")
    if not isinstance(before, dict):
        return ToolResult(text="[ERROR] timeline JSON root must be an object")
    after = copy.deepcopy(before)
    apply_flag = coerce_apply_flag(args.get("apply"))
    if apply_flag is None:
        return ToolResult(text="[ERROR] apply must be a boolean")
    patch = args.get("patch", {})
    if patch is None:
        patch = {}
    if not isinstance(patch, dict):
        return ToolResult(text="[ERROR] patch must be an object")
    patch_issues = validate_timeline_patch(before, patch, apply_requested=apply_flag)
    if not any(i["severity"] == "error" for i in patch_issues):
        apply_patch_to_timeline(after, patch)
    after_clips, after_issues = validate_timeline_data(after, ctx)
    after_issues = patch_issues + after_issues

    diff = {
        "timeline_path": str(timeline_path),
        "instructions": args["instructions"],
        "patch": patch,
        "requested_apply": apply_flag,
        "applied": False,
        "before_clip_count": len(timeline_clips(before)),
        "after_clip_count": len(after_clips),
        "after_validation_status": "pass" if not any(i["severity"] == "error" for i in after_issues) else "fail",
        "after_validation_issues": after_issues,
    }
    output_json = ctx.resolve(args.get("output_json") or f"out/{timeline_path.stem}_timeline_diff.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")

    artifacts = [str(output_json)]
    if apply_flag and diff["after_validation_status"] != "pass":
        return ToolResult(
            text=f"[ERROR] timeline_diff patch is invalid; original timeline was not modified. Diff written: {ctx.virtualize(output_json)}",
            data=diff,
            artifacts=artifacts,
        )
    if apply_flag:
        timeline_path.write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")
        diff["applied"] = True
        output_json.write_text(json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(str(timeline_path))
    return ToolResult(
        text=f"Timeline diff written: {ctx.virtualize(output_json)}",
        data=diff,
        artifacts=artifacts,
    )


def apply_patch_to_timeline(data: dict[str, Any], patch: dict[str, Any]) -> None:
    set_timeline_fields(data, patch.get("set_timeline_fields"))
    set_track_fields(data, patch.get("set_track_fields"))
    apply_asset_patch(data, patch)
    apply_track_patch(data, patch)
    refs = timeline_clip_refs(data)
    update_clips = patch.get("update_clips", [])
    if not isinstance(update_clips, list):
        update_clips = []
    for item in update_clips:
        if not isinstance(item, dict) or not is_patch_index(item.get("index")):
            continue
        idx = item["index"]
        if 0 <= idx < len(refs) and isinstance(item.get("fields"), dict):
            container, local_idx = refs[idx]
            merge_fields(container[local_idx], item["fields"])
    replace_clips = patch.get("replace_clips", [])
    if not isinstance(replace_clips, list):
        replace_clips = []
    for item in replace_clips:
        if not isinstance(item, dict) or not is_patch_index(item.get("index")):
            continue
        idx = item["index"]
        if 0 <= idx < len(refs) and isinstance(item.get("clip"), dict):
            container, local_idx = refs[idx]
            container[local_idx] = item["clip"]
    remove_indices = patch.get("remove_clip_indices", [])
    if not isinstance(remove_indices, list):
        remove_indices = []
    unique_removals = sorted({idx for idx in remove_indices if is_patch_index(idx)}, reverse=True)
    for idx in unique_removals:
        if 0 <= idx < len(refs):
            container, local_idx = refs[idx]
            container.pop(local_idx)
    move_clips = patch.get("move_clips", [])
    if isinstance(move_clips, list):
        for item in move_clips:
            if not isinstance(item, dict):
                continue
            move_clip(data, item)
    insert_clips = patch.get("insert_clips", [])
    if isinstance(insert_clips, list):
        for item in insert_clips:
            insert_clip(data, item)
    add_clips = patch.get("add_clips", [])
    if not isinstance(add_clips, list):
        add_clips = []
    for item in add_clips:
        if isinstance(item, dict):
            default_clip_container(data).append(item)


def apply_asset_patch(data: dict[str, Any], patch: dict[str, Any]) -> None:
    assets = data.get("assets")
    if not isinstance(assets, list):
        assets = []
        data["assets"] = assets
    update_assets = patch.get("update_assets", [])
    if isinstance(update_assets, list):
        for item in update_assets:
            if not isinstance(item, dict) or not is_patch_index(item.get("index")):
                continue
            idx = item["index"]
            if 0 <= idx < len(assets) and isinstance(assets[idx], dict) and isinstance(item.get("fields"), dict):
                merge_fields(assets[idx], item["fields"])
    remove_asset_indices = patch.get("remove_asset_indices", [])
    if isinstance(remove_asset_indices, list):
        for idx in sorted({i for i in remove_asset_indices if is_patch_index(i)}, reverse=True):
            if 0 <= idx < len(assets):
                assets.pop(idx)
    add_assets = patch.get("add_assets", [])
    if isinstance(add_assets, list):
        for item in add_assets:
            if isinstance(item, dict):
                assets.append(item)


def apply_track_patch(data: dict[str, Any], patch: dict[str, Any]) -> None:
    tracks = data.get("tracks")
    if not isinstance(tracks, list):
        tracks = []
        data["tracks"] = tracks
    replace_tracks = patch.get("replace_tracks", [])
    if isinstance(replace_tracks, list):
        for item in replace_tracks:
            if not isinstance(item, dict) or not is_patch_index(item.get("index")):
                continue
            idx = item["index"]
            if 0 <= idx < len(tracks) and isinstance(item.get("track"), dict):
                tracks[idx] = item["track"]
    remove_track_indices = patch.get("remove_track_indices", [])
    if isinstance(remove_track_indices, list):
        for idx in sorted({i for i in remove_track_indices if is_patch_index(i)}, reverse=True):
            if 0 <= idx < len(tracks):
                tracks.pop(idx)
    insert_tracks = patch.get("insert_tracks", [])
    if isinstance(insert_tracks, list):
        for item in insert_tracks:
            if not isinstance(item, dict) or not is_patch_index(item.get("index")) or not isinstance(item.get("track"), dict):
                continue
            tracks.insert(max(0, min(item["index"], len(tracks))), item["track"])
    add_tracks = patch.get("add_tracks", [])
    if isinstance(add_tracks, list):
        for item in add_tracks:
            if isinstance(item, dict):
                tracks.append(item)


def set_timeline_fields(data: dict[str, Any], fields: object) -> None:
    if not isinstance(fields, dict):
        return
    for key, value in fields.items():
        if key in PROTECTED_TIMELINE_PATCH_FIELDS:
            continue
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value


def set_track_fields(data: dict[str, Any], items: object) -> None:
    if not isinstance(items, list) or not isinstance(data.get("tracks"), list):
        return
    tracks = data["tracks"]
    for item in items:
        if not isinstance(item, dict) or not is_patch_index(item.get("index")):
            continue
        idx = item["index"]
        if not (0 <= idx < len(tracks)) or not isinstance(tracks[idx], dict):
            continue
        fields = item.get("fields")
        if isinstance(fields, dict):
            merge_fields(tracks[idx], fields)


def merge_fields(target: dict[str, Any], fields: dict[str, Any]) -> None:
    for key, value in fields.items():
        if value is None:
            target.pop(key, None)
        else:
            target[key] = value


def move_clip(data: dict[str, Any], item: dict[str, Any]) -> None:
    from_idx = item.get("from")
    to_idx = item.get("to")
    if not is_patch_index(from_idx) or not is_patch_index(to_idx):
        return
    refs = timeline_clip_refs(data)
    if not (0 <= from_idx < len(refs)):
        return
    target_container = clip_target_container(data, item)
    if target_container is None:
        return
    source_container, local_idx = refs[from_idx]
    clip = source_container.pop(local_idx)
    if target_container is source_container and to_idx > local_idx:
        to_idx -= 1
    to_idx = max(0, min(to_idx, len(target_container)))
    target_container.insert(to_idx, clip)


def insert_clip(data: dict[str, Any], item: object) -> None:
    if not isinstance(item, dict) or not isinstance(item.get("clip"), dict):
        return
    index = item.get("index")
    if not is_patch_index(index):
        return
    container = clip_target_container(data, item)
    if container is None:
        return
    container.insert(max(0, min(index, len(container))), item["clip"])


def clip_target_container(data: dict[str, Any], item: dict[str, Any]) -> list | None:
    tracks = data.get("tracks")
    track_index = item.get("track_index")
    if isinstance(tracks, list) and is_patch_index(track_index):
        if 0 <= track_index < len(tracks) and isinstance(tracks[track_index], dict):
            return track_clips_list(tracks[track_index])
        return None
    return default_clip_container(data)


def coerce_apply_flag(value: object) -> bool | None:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return None


def validate_timeline_patch(
    data: dict[str, Any],
    patch: dict[str, Any],
    *,
    apply_requested: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    refs = timeline_clip_refs(data)
    # 只看 key 是否存在会放过 {"add_clips": []} 这类零操作 patch: 它会把
    # timeline 原样重写一遍 (JSON 重排 => sha 变化, 既有 validation/QC 报告的
    # hash 关联全部失效) 且报告 applied=true。apply=true 必须带至少一个非空操作。
    if apply_requested and not patch_has_non_empty_operation(patch):
        issues.append({
            "severity": "error",
            "message": "apply=true requires at least one non-empty timeline patch operation",
        })
    for key in patch:
        if key not in PATCH_OPERATION_KEYS:
            issues.append({"severity": "warning", "message": f"unknown patch key ignored: {key}"})
    structural_track_ops = [key for key in STRUCTURAL_TRACK_PATCH_KEYS if operation_is_non_empty(patch.get(key))]
    clip_ops = [key for key in CLIP_PATCH_KEYS if operation_is_non_empty(patch.get(key))]
    if structural_track_ops and clip_ops:
        issues.append({
            "severity": "error",
            "message": (
                "structural track operations and clip operations must be split into separate timeline_diff calls; "
                f"track ops={structural_track_ops}, clip ops={clip_ops}"
            ),
        })

    validate_asset_patch(data, patch, issues)
    validate_track_patch(data, patch, issues)

    remove_indices = patch.get("remove_clip_indices", [])
    valid_remove_indices: set[int] = set()
    if "remove_clip_indices" in patch:
        if not isinstance(remove_indices, list):
            issues.append({"severity": "error", "message": "remove_clip_indices must be an array of clip indices"})
        else:
            seen_remove: set[int] = set()
            for pos, idx in enumerate(remove_indices):
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"remove_clip_indices[{pos}] must be an integer"})
                elif idx < 0 or idx >= len(refs):
                    issues.append({"severity": "error", "message": f"remove_clip_indices[{pos}] out of range: {idx}"})
                elif idx in seen_remove:
                    issues.append({"severity": "error", "message": f"remove_clip_indices[{pos}] duplicates index {idx}"})
                else:
                    seen_remove.add(idx)
                    valid_remove_indices.add(idx)

    add_clips = patch.get("add_clips", [])
    if "add_clips" in patch:
        if not isinstance(add_clips, list):
            issues.append({"severity": "error", "message": "add_clips must be an array of clip objects"})
        else:
            for pos, item in enumerate(add_clips):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"add_clips[{pos}] must be an object"})

    insert_clips = patch.get("insert_clips", [])
    if "insert_clips" in patch:
        if not isinstance(insert_clips, list):
            issues.append({"severity": "error", "message": "insert_clips must be an array of {index, clip, track_index?} objects"})
        else:
            for pos, item in enumerate(insert_clips):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"insert_clips[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"insert_clips[{pos}].index must be an integer"})
                elif idx < 0:
                    issues.append({"severity": "error", "message": f"insert_clips[{pos}].index must be >= 0"})
                if not isinstance(item.get("clip"), dict):
                    issues.append({"severity": "error", "message": f"insert_clips[{pos}].clip must be an object"})
                validate_track_index(data, item, f"insert_clips[{pos}]", issues)

    replace_clips = patch.get("replace_clips", [])
    if "replace_clips" in patch:
        if not isinstance(replace_clips, list):
            issues.append({"severity": "error", "message": "replace_clips must be an array of {index, clip} objects"})
        else:
            seen_replace: set[int] = set()
            for pos, item in enumerate(replace_clips):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"replace_clips[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"replace_clips[{pos}].index must be an integer"})
                elif idx < 0 or idx >= len(refs):
                    issues.append({"severity": "error", "message": f"replace_clips[{pos}].index out of range: {idx}"})
                elif idx in seen_replace:
                    issues.append({"severity": "error", "message": f"replace_clips[{pos}].index duplicates index {idx}"})
                elif idx in valid_remove_indices:
                    issues.append({
                        "severity": "error",
                        "message": f"replace_clips[{pos}].index {idx} is also listed in remove_clip_indices; "
                        "an index cannot be replaced and removed in the same patch",
                    })
                else:
                    seen_replace.add(idx)
                if not isinstance(item.get("clip"), dict):
                    issues.append({"severity": "error", "message": f"replace_clips[{pos}].clip must be an object"})

    update_clips = patch.get("update_clips", [])
    if "update_clips" in patch:
        if not isinstance(update_clips, list):
            issues.append({"severity": "error", "message": "update_clips must be an array of {index, fields} objects"})
        else:
            seen_update: set[int] = set()
            for pos, item in enumerate(update_clips):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"update_clips[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"update_clips[{pos}].index must be an integer"})
                elif idx < 0 or idx >= len(refs):
                    issues.append({"severity": "error", "message": f"update_clips[{pos}].index out of range: {idx}"})
                elif idx in seen_update:
                    issues.append({"severity": "error", "message": f"update_clips[{pos}].index duplicates index {idx}"})
                elif idx in valid_remove_indices:
                    issues.append({
                        "severity": "error",
                        "message": f"update_clips[{pos}].index {idx} is also listed in remove_clip_indices; "
                        "an index cannot be updated and removed in the same patch",
                    })
                else:
                    seen_update.add(idx)
                fields = item.get("fields")
                if not isinstance(fields, dict) or not fields:
                    issues.append({"severity": "error", "message": f"update_clips[{pos}].fields must be a non-empty object"})

    move_clips = patch.get("move_clips", [])
    if "move_clips" in patch:
        if not isinstance(move_clips, list):
            issues.append({"severity": "error", "message": "move_clips must be an array of {from, to, track_index?} objects"})
        else:
            if len(move_clips) > 1:
                issues.append({
                    "severity": "error",
                    "message": "move_clips supports one move per timeline_diff call; split multiple reorders into separate calls",
                })
            if valid_remove_indices and move_clips:
                issues.append({
                    "severity": "error",
                    "message": "move_clips cannot be combined with remove_clip_indices; split reorder and deletion into separate timeline_diff calls",
                })
            for pos, item in enumerate(move_clips):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"move_clips[{pos}] must be an object"})
                    continue
                from_idx = item.get("from")
                to_idx = item.get("to")
                if not is_patch_index(from_idx):
                    issues.append({"severity": "error", "message": f"move_clips[{pos}].from must be an integer"})
                elif from_idx < 0 or from_idx >= len(refs):
                    issues.append({"severity": "error", "message": f"move_clips[{pos}].from out of range: {from_idx}"})
                if not is_patch_index(to_idx):
                    issues.append({"severity": "error", "message": f"move_clips[{pos}].to must be an integer"})
                elif to_idx < 0 or to_idx > len(refs):
                    issues.append({"severity": "error", "message": f"move_clips[{pos}].to out of range: {to_idx}"})
                validate_track_index(data, item, f"move_clips[{pos}]", issues)

    set_timeline_fields = patch.get("set_timeline_fields")
    if "set_timeline_fields" in patch:
        if not isinstance(set_timeline_fields, dict) or not set_timeline_fields:
            issues.append({"severity": "error", "message": "set_timeline_fields must be a non-empty object"})
        else:
            for key in set_timeline_fields:
                if key in PROTECTED_TIMELINE_PATCH_FIELDS:
                    issues.append({
                        "severity": "error",
                        "message": f"set_timeline_fields cannot modify {key}; use clip/track patch operations",
                    })

    set_track_fields = patch.get("set_track_fields")
    if "set_track_fields" in patch:
        tracks = data.get("tracks")
        if not isinstance(set_track_fields, list):
            issues.append({"severity": "error", "message": "set_track_fields must be an array of {index, fields} objects"})
        elif not isinstance(tracks, list):
            issues.append({"severity": "error", "message": "set_track_fields requires a tracks[] timeline"})
        else:
            seen_tracks: set[int] = set()
            for pos, item in enumerate(set_track_fields):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"set_track_fields[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"set_track_fields[{pos}].index must be an integer"})
                elif idx < 0 or idx >= len(tracks):
                    issues.append({"severity": "error", "message": f"set_track_fields[{pos}].index out of range: {idx}"})
                elif idx in seen_tracks:
                    issues.append({"severity": "error", "message": f"set_track_fields[{pos}].index duplicates index {idx}"})
                else:
                    seen_tracks.add(idx)
                fields = item.get("fields")
                if not isinstance(fields, dict) or not fields:
                    issues.append({"severity": "error", "message": f"set_track_fields[{pos}].fields must be a non-empty object"})
    return issues


def validate_asset_patch(data: dict[str, Any], patch: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    assets = data.get("assets")
    asset_count = len(assets) if isinstance(assets, list) else 0
    add_assets = patch.get("add_assets", [])
    if "add_assets" in patch:
        if not isinstance(add_assets, list):
            issues.append({"severity": "error", "message": "add_assets must be an array of asset objects"})
        else:
            for pos, item in enumerate(add_assets):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"add_assets[{pos}] must be an object"})
    update_assets = patch.get("update_assets", [])
    if "update_assets" in patch:
        if not isinstance(update_assets, list):
            issues.append({"severity": "error", "message": "update_assets must be an array of {index, fields} objects"})
        else:
            seen: set[int] = set()
            for pos, item in enumerate(update_assets):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"update_assets[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"update_assets[{pos}].index must be an integer"})
                elif idx < 0 or idx >= asset_count:
                    issues.append({"severity": "error", "message": f"update_assets[{pos}].index out of range: {idx}"})
                elif idx in seen:
                    issues.append({"severity": "error", "message": f"update_assets[{pos}].index duplicates index {idx}"})
                if is_patch_index(idx):
                    seen.add(idx)
                if not isinstance(item.get("fields"), dict) or not item.get("fields"):
                    issues.append({"severity": "error", "message": f"update_assets[{pos}].fields must be a non-empty object"})
    remove_asset_indices = patch.get("remove_asset_indices", [])
    if "remove_asset_indices" in patch:
        if not isinstance(remove_asset_indices, list):
            issues.append({"severity": "error", "message": "remove_asset_indices must be an array of asset indices"})
        else:
            seen: set[int] = set()
            for pos, idx in enumerate(remove_asset_indices):
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"remove_asset_indices[{pos}] must be an integer"})
                elif idx < 0 or idx >= asset_count:
                    issues.append({"severity": "error", "message": f"remove_asset_indices[{pos}] out of range: {idx}"})
                elif idx in seen:
                    issues.append({"severity": "error", "message": f"remove_asset_indices[{pos}] duplicates index {idx}"})
                if is_patch_index(idx):
                    seen.add(idx)


def validate_track_patch(data: dict[str, Any], patch: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    tracks = data.get("tracks")
    track_count = len(tracks) if isinstance(tracks, list) else 0
    if any(key in patch for key in ("add_tracks", "insert_tracks", "replace_tracks", "remove_track_indices")) and isinstance(data.get("clips"), list):
        issues.append({
            "severity": "error",
            "message": "track patch operations require a tracks[] timeline, not legacy top-level clips[]",
        })
    add_tracks = patch.get("add_tracks", [])
    if "add_tracks" in patch:
        if not isinstance(add_tracks, list):
            issues.append({"severity": "error", "message": "add_tracks must be an array of track objects"})
        else:
            for pos, item in enumerate(add_tracks):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"add_tracks[{pos}] must be an object"})
    insert_tracks = patch.get("insert_tracks", [])
    if "insert_tracks" in patch:
        if not isinstance(insert_tracks, list):
            issues.append({"severity": "error", "message": "insert_tracks must be an array of {index, track} objects"})
        else:
            for pos, item in enumerate(insert_tracks):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"insert_tracks[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"insert_tracks[{pos}].index must be an integer"})
                elif idx < 0 or idx > track_count:
                    issues.append({"severity": "error", "message": f"insert_tracks[{pos}].index out of range: {idx}"})
                if not isinstance(item.get("track"), dict):
                    issues.append({"severity": "error", "message": f"insert_tracks[{pos}].track must be an object"})
    replace_tracks = patch.get("replace_tracks", [])
    if "replace_tracks" in patch:
        if not isinstance(replace_tracks, list):
            issues.append({"severity": "error", "message": "replace_tracks must be an array of {index, track} objects"})
        else:
            seen: set[int] = set()
            for pos, item in enumerate(replace_tracks):
                if not isinstance(item, dict):
                    issues.append({"severity": "error", "message": f"replace_tracks[{pos}] must be an object"})
                    continue
                idx = item.get("index")
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"replace_tracks[{pos}].index must be an integer"})
                elif idx < 0 or idx >= track_count:
                    issues.append({"severity": "error", "message": f"replace_tracks[{pos}].index out of range: {idx}"})
                elif idx in seen:
                    issues.append({"severity": "error", "message": f"replace_tracks[{pos}].index duplicates index {idx}"})
                if is_patch_index(idx):
                    seen.add(idx)
                if not isinstance(item.get("track"), dict):
                    issues.append({"severity": "error", "message": f"replace_tracks[{pos}].track must be an object"})
    remove_track_indices = patch.get("remove_track_indices", [])
    if "remove_track_indices" in patch:
        if not isinstance(remove_track_indices, list):
            issues.append({"severity": "error", "message": "remove_track_indices must be an array of track indices"})
        else:
            seen: set[int] = set()
            for pos, idx in enumerate(remove_track_indices):
                if not is_patch_index(idx):
                    issues.append({"severity": "error", "message": f"remove_track_indices[{pos}] must be an integer"})
                elif idx < 0 or idx >= track_count:
                    issues.append({"severity": "error", "message": f"remove_track_indices[{pos}] out of range: {idx}"})
                elif idx in seen:
                    issues.append({"severity": "error", "message": f"remove_track_indices[{pos}] duplicates index {idx}"})
                if is_patch_index(idx):
                    seen.add(idx)


def patch_has_non_empty_operation(patch: dict[str, Any]) -> bool:
    for key in PATCH_OPERATION_KEYS:
        if operation_is_non_empty(patch.get(key)):
            return True
    return False


def operation_is_non_empty(value: object) -> bool:
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return bool(value)
    return False


def validate_track_index(data: dict[str, Any], item: dict[str, Any], label: str, issues: list[dict[str, Any]]) -> None:
    track_index = item.get("track_index")
    if track_index is None:
        return
    tracks = data.get("tracks")
    if not is_patch_index(track_index):
        issues.append({"severity": "error", "message": f"{label}.track_index must be an integer"})
    elif not isinstance(tracks, list):
        issues.append({"severity": "error", "message": f"{label}.track_index requires a tracks[] timeline"})
    elif track_index < 0 or track_index >= len(tracks):
        issues.append({"severity": "error", "message": f"{label}.track_index out of range: {track_index}"})


def is_patch_index(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def timeline_clip_refs(data: dict[str, Any]) -> list[tuple[list[dict[str, Any]], int]]:
    if isinstance(data.get("clips"), list):
        return [(data["clips"], idx) for idx, clip in enumerate(data["clips"]) if isinstance(clip, dict)]
    refs: list[tuple[list[dict[str, Any]], int]] = []
    tracks = data.get("tracks")
    if isinstance(tracks, list):
        for track in tracks:
            if isinstance(track, dict) and isinstance(track.get("clips"), list):
                for idx, clip in enumerate(track["clips"]):
                    if isinstance(clip, dict):
                        refs.append((track["clips"], idx))
    return refs


def default_clip_container(data: dict[str, Any]) -> list:
    if isinstance(data.get("clips"), list):
        return data["clips"]
    tracks = data.get("tracks")
    if isinstance(tracks, list):
        # tracks 模式下绝不落到顶层 clips[]: 那会造出 clips+tracks 双容器,
        # after 校验报 "not both" 且错误归因完全误导 (真实原因是轨内 clips 非法
        # 或没有可用轨)。轨内 clips 非法时就地归一为数组; 一个可用轨都没有时
        # 新建 video 轨承接 add_clips。
        for track in tracks:
            if isinstance(track, dict) and is_video_track(track):
                return track_clips_list(track)
        for track in tracks:
            if isinstance(track, dict):
                return track_clips_list(track)
        new_track: dict[str, Any] = {"type": "video", "clips": []}
        tracks.append(new_track)
        return new_track["clips"]
    return data.setdefault("clips", [])


def track_clips_list(track: dict[str, Any]) -> list:
    clips = track.get("clips")
    if not isinstance(clips, list):
        clips = []
        track["clips"] = clips
    return clips


def is_video_track(track: dict[str, Any]) -> bool:
    return normalize_track_type(track.get("type") or track.get("track_type") or track.get("name") or "") in VIDEO_TRACK_TYPES


def normalize_track_type(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
