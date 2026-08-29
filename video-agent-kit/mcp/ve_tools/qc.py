from __future__ import annotations

import json
import shutil
import subprocess
from .ffproc import run_proc
import time
from pathlib import Path

from .media import inspect_media
from .render import source_has_audio, source_has_video
from .result import ToolResult
from .run_context import RunContext
from .timeline import file_sha256, load_timeline, normalize_track_type, timeline_clips, VIDEO_TRACK_TYPES


def qc_preview(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("video_path"):
        return ToolResult(text="[ERROR] video_path is required")
    video_path = ctx.resolve(args["video_path"])
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")
    timeline_path: Path | None = None
    if args.get("timeline_path"):
        # 前置校验: 黑帧/静音扫描是分钟级操作, timeline 缺失时不能等扫完才报错
        timeline_path = ctx.resolve(args["timeline_path"])
        if not timeline_path.is_file():
            return ToolResult(text=f"[ERROR] timeline not found: {timeline_path}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    started = time.time()
    media_result = inspect_media({
        "input_path": str(video_path),
        "output_json": str(ctx.output_dir / f"{video_path.stem}_media.json"),
    }, ctx)
    if media_result.text.startswith("[ERROR]"):
        return ToolResult(text=f"[ERROR] media probe failed during QC: {media_result.text}", data=media_result.data)
    issues = []
    if video_path.stat().st_size == 0:
        issues.append({"severity": "error", "message": "output file is empty"})
    # 视频流缺失是 error (音频缺失只是 warning): 对无视频流的文件, blackdetect
    # 的 -vf 被 ffmpeg 静默忽略且 exit 0 — 亚帧 clip 渲出的纯音频 preview 曾
    # 借此全链路过关
    has_video = source_has_video(video_path)
    if not has_video:
        issues.append({
            "severity": "error",
            "message": "no video stream detected; the QC target is not a playable video (black frame scan is meaningless)",
        })
    black, black_error = run_filter_scan(video_path, "blackdetect=d=0.2:pix_th=0.10", filter_kind="video")
    short_black, short_black_error = run_filter_scan(video_path, "blackdetect=d=0.025:pix_th=0.10", filter_kind="video")
    freeze, freeze_error = run_filter_scan(video_path, "freezedetect=n=-60dB:d=1.0", filter_kind="video")
    # Probe audio existence explicitly: some ffmpeg builds silently ignore -af
    # on audio-less inputs, which would make a fully silent (no-audio-track)
    # output pass the silence scan without any finding.
    has_audio = source_has_audio(video_path)
    if has_audio:
        silence, silence_error = run_filter_scan(video_path, "silencedetect=n=-35dB:d=0.5", filter_kind="audio")
        volume, volume_error = run_filter_scan(video_path, "volumedetect", filter_kind="audio")
    else:
        silence, silence_error = "", ""
        volume, volume_error = "", ""
        issues.append({
            "severity": "warning",
            "message": "no audio stream detected; the output is fully silent and the silence scan was skipped",
        })
    if black_error:
        issues.append({"severity": "error", "message": "black frame scan failed", "evidence": black_error})
    if short_black_error:
        issues.append({"severity": "error", "message": "short black-frame scan failed", "evidence": short_black_error})
    if silence_error:
        issues.append({"severity": "error", "message": "silence scan failed", "evidence": silence_error})
    if freeze_error:
        issues.append({"severity": "error", "message": "freeze frame scan failed", "evidence": freeze_error})
    if volume_error:
        issues.append({"severity": "error", "message": "volume scan failed", "evidence": volume_error})
    if "black_start" in black:
        issues.append({"severity": "warning", "message": "black frames detected", "evidence": black[-2000:]})
    if "silence_start" in silence:
        issues.append({"severity": "warning", "message": "silence detected", "evidence": silence[-2000:]})
    if "freeze_start" in freeze:
        issues.append({"severity": "warning", "message": "freeze frames detected", "evidence": freeze[-2000:]})
    volume_stats = parse_volumedetect(volume)
    audio_duration = audio_duration_from_media(media_result.data)
    video_duration = safe_float(media_result.data.get("duration_seconds"))
    if has_audio and audio_duration is not None and video_duration is not None:
        if audio_duration + 0.25 < video_duration:
            issues.append({
                "severity": "error",
                "message": "audio stream ends before the video; render audio coverage is incomplete",
                "evidence": f"audio_duration={audio_duration:.3f}s video_duration={video_duration:.3f}s",
            })
    if volume_stats.get("max_volume_db") is not None and volume_stats["max_volume_db"] >= -0.1:
        issues.append({
            "severity": "warning",
            "message": "audio peak is near clipping",
            "evidence": f"max_volume={volume_stats['max_volume_db']} dB",
        })
    if volume_stats.get("mean_volume_db") is not None and volume_stats["mean_volume_db"] <= -35.0:
        issues.append({
            "severity": "warning",
            "message": "audio mean volume is very low",
            "evidence": f"mean_volume={volume_stats['mean_volume_db']} dB",
        })
    video_sha = file_sha256(video_path)
    timeline_sha: str | None = None
    timeline_expectations = {}
    if timeline_path is not None:
        timeline_sha = file_sha256(timeline_path)
        issues.extend(render_binding_issues(video_path, video_sha, timeline_sha))
        timeline_expectations = expected_from_timeline(timeline_path)
        issues.extend(timeline_expectation_issues(media_result.data, timeline_expectations))
        issues.extend(edit_boundary_black_issues(timeline_path, short_black))
    status = "pass" if not any(i["severity"] == "error" for i in issues) else "fail"
    report = {
        "status": status,
        "video_path": str(video_path),
        "video_sha256": video_sha,
        "has_video_stream": has_video,
        "has_audio_stream": has_audio,
        "media": media_result.data,
        "issues": issues,
        "timeline_expectations": timeline_expectations,
        "volume_stats": volume_stats,
        "audio_duration_seconds": audio_duration,
        "blackdetect_log_tail": black[-2000:],
        "short_blackdetect_log_tail": short_black[-2000:],
        "silencedetect_log_tail": silence[-2000:],
        "freezedetect_log_tail": freeze[-2000:],
        "elapsed_seconds": round(time.time() - started, 3),
    }
    if timeline_path is not None:
        report["timeline_path"] = str(timeline_path)
        report["timeline_sha256"] = timeline_sha
    output_json = ctx.resolve(args.get("output_json") or f"out/{video_path.stem}_qc_report.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return ToolResult(
        text=f"QC {status}: {ctx.virtualize(output_json)}",
        data=report,
        artifacts=[str(output_json)],
    )


def render_binding_issues(video_path: Path, video_sha: str, timeline_sha: str) -> list[dict]:
    """preview 与 timeline 的渲染绑定校验。

    QC 报告里的 timeline_sha256 只是 QC 时刻 timeline 的哈希 — 渲染后改
    timeline 不重渲染, validation/QC/Stop hook 的哈希检查全部照过, 陈旧
    preview 会混过收尾契约。render_preview 落的 render_report 记录了渲染
    时刻的 timeline_sha256/output_sha256。带 timeline_path 的 QC 是 pipeline
    收尾门禁, 必须证明 preview 来自 render_preview 和当前 timeline；report
    缺失、损坏或描述的不是当前文件都应拦截。"""
    report_path = video_path.with_suffix(".render_report.json")
    try:
        render_report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [{
            "severity": "error",
            "message": "render report is missing or unreadable; run render_preview before qc_preview",
            "evidence": f"{report_path.name}: {exc}",
        }]
    if not isinstance(render_report, dict):
        return [{
            "severity": "error",
            "message": "render report is malformed; rerun render_preview",
            "evidence": f"{report_path.name} root is not an object",
        }]
    if render_report.get("output_sha256") != video_sha:
        return [{
            "severity": "error",
            "message": "render report does not describe the current preview; rerun render_preview before QC",
            "evidence": (
                f"{report_path.name}: output_sha256 {render_report.get('output_sha256')} "
                f"!= current preview sha256 {video_sha}"
            ),
        }]
    rendered_timeline_sha = render_report.get("timeline_sha256")
    if not rendered_timeline_sha:
        return [{
            "severity": "error",
            "message": "render report does not record timeline_sha256; rerun render_preview",
            "evidence": report_path.name,
        }]
    if rendered_timeline_sha != timeline_sha:
        return [{
            "severity": "error",
            "message": (
                "preview was rendered from a different timeline than timeline_path; "
                "re-run render_preview on the current timeline before QC"
            ),
            "evidence": (
                f"{report_path.name}: rendered timeline_sha256 {rendered_timeline_sha} "
                f"!= current timeline sha256 {timeline_sha}"
            ),
        }]
    return []


def run_filter_scan(video_path: Path, filter_expr: str, filter_kind: str) -> tuple[str, str]:
    filter_arg = "-af" if filter_kind == "audio" else "-vf"
    cmd = ["ffmpeg", "-v", "info", "-i", str(video_path), filter_arg, filter_expr, "-f", "null", "-"]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=600)
    except Exception as exc:
        return "", str(exc)
    output = (proc.stderr or "") + (proc.stdout or "")
    if proc.returncode != 0:
        return output, output[-2000:] or f"ffmpeg {filter_kind} scan failed"
    return output, ""


def parse_volumedetect(output: str) -> dict:
    stats = {}
    for line in output.splitlines():
        if "mean_volume:" in line:
            stats["mean_volume_db"] = parse_db_value(line)
        elif "max_volume:" in line:
            stats["max_volume_db"] = parse_db_value(line)
    return stats


def audio_duration_from_media(media: dict) -> float | None:
    durations = []
    for stream in media.get("audio_streams") or []:
        if not isinstance(stream, dict):
            continue
        value = safe_float(stream.get("duration"))
        if value is not None:
            durations.append(value)
    return max(durations) if durations else None


def parse_filter_ranges(output: str, kind: str) -> list[dict]:
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
        if end_marker not in line:
            continue
        end = safe_float(line.split(end_marker, 1)[1].split()[0])
        duration = safe_float(line.split(duration_marker, 1)[1].split()[0]) if duration_marker in line else None
        start = starts.pop(0) if starts else ((end - duration) if end is not None and duration is not None else None)
        if start is not None and end is not None and end >= start:
            ranges.append({"start": round(start, 3), "end": round(end, 3), "duration": round(end - start, 3)})
    return ranges


def edit_boundary_black_issues(timeline_path: Path, black_log: str) -> list[dict]:
    ranges = parse_filter_ranges(black_log, "black")
    if not ranges:
        return []
    cuts = timeline_video_cut_times(timeline_path)
    if not cuts:
        return []
    hits = []
    for cut in cuts:
        for item in ranges:
            if abs(item["start"] - cut) <= 0.08 or item["start"] <= cut <= item["end"] + 0.08:
                hits.append({"cut_time": round(cut, 3), "black_range": item})
                break
    if not hits:
        return []
    return [{
        "severity": "warning",
        "message": "short black frame detected near edit boundary",
        "evidence": hits[:20],
    }]


def timeline_video_cut_times(timeline_path: Path) -> list[float]:
    try:
        data = load_timeline(timeline_path)
    except Exception:
        return []
    duration = timeline_duration(data) or 0.0
    cuts: set[float] = set()
    if not isinstance(data, dict):
        return []
    tracks = data.get("tracks")
    if isinstance(tracks, list):
        for track in tracks:
            if not isinstance(track, dict) or not isinstance(track.get("clips"), list):
                continue
            track_type = normalize_track_type(track.get("type") or track.get("track_type") or track.get("name") or "")
            if track_type not in VIDEO_TRACK_TYPES:
                continue
            cursor = 0.0
            for clip in track["clips"]:
                if not isinstance(clip, dict):
                    continue
                render_duration = clip_render_duration_for_qc(clip)
                if render_duration is None:
                    continue
                start = safe_float(clip.get("timeline_start", clip.get("position")))
                if start is None:
                    start = cursor
                end = start + render_duration
                cursor = max(cursor, end)
                for value in (start, end):
                    if 0.15 < value < duration - 0.15:
                        cuts.add(round(value, 3))
    else:
        cursor = 0.0
        for clip in timeline_clips(data):
            render_duration = clip_render_duration_for_qc(clip)
            if render_duration is None:
                continue
            cursor += render_duration
            if 0.15 < cursor < duration - 0.15:
                cuts.add(round(cursor, 3))
    return sorted(cuts)


def clip_render_duration_for_qc(clip: dict) -> float | None:
    start = safe_float(clip.get("start", clip.get("start_time", clip.get("in", 0)))) or 0.0
    end = safe_float(clip.get("end", clip.get("end_time", clip.get("out"))))
    duration = safe_float(clip.get("duration"))
    if end is not None:
        duration = end - start
    if duration is None or duration <= 0:
        return None
    speed = safe_float(clip.get("speed")) or 1.0
    if speed <= 0:
        return None
    return duration / speed


def parse_db_value(line: str) -> float | None:
    try:
        tail = line.split(":", 1)[1].strip()
        return float(tail.split()[0])
    except Exception:
        return None


def expected_from_timeline(timeline_path: Path) -> dict:
    try:
        data = load_timeline(timeline_path)
    except Exception as exc:
        return {"error": f"could not read timeline: {exc}"}
    if not isinstance(data, dict):
        return {"error": "timeline root is not an object"}
    width = height = fps = None
    for candidate in (
        data.get("output_canvas"),
        (data.get("sequence") or {}).get("canvas") if isinstance(data.get("sequence"), dict) else None,
        (data.get("sequence") or {}).get("output_canvas") if isinstance(data.get("sequence"), dict) else None,
        data.get("sequence"),
    ):
        if not isinstance(candidate, dict):
            continue
        width = width or safe_int(candidate.get("width"))
        height = height or safe_int(candidate.get("height"))
        fps = fps or safe_float(candidate.get("fps"))
    duration = None
    if isinstance(data.get("sequence"), dict):
        duration = safe_float(data["sequence"].get("duration"))
    if duration is None:
        duration = timeline_duration(data)
    return {
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "fps": fps,
    }


def timeline_duration(data: dict) -> float | None:
    max_end = 0.0
    if isinstance(data.get("tracks"), list):
        for track in data["tracks"]:
            if not isinstance(track, dict) or not isinstance(track.get("clips"), list):
                continue
            track_type = normalize_track_type(track.get("type") or track.get("track_type") or track.get("name") or "")
            cursor = 0.0
            for clip in track["clips"]:
                if not isinstance(clip, dict):
                    continue
                start = safe_float(clip.get("start", clip.get("start_time", clip.get("in", 0)))) or 0.0
                end = safe_float(clip.get("end", clip.get("end_time", clip.get("out"))))
                duration = safe_float(clip.get("duration"))
                if end is not None:
                    source_duration = max(0.0, end - start)
                elif duration is not None:
                    source_duration = duration
                else:
                    continue
                speed = safe_float(clip.get("speed")) or 1.0
                render_duration = source_duration / speed if speed > 0 else source_duration
                timeline_start = safe_float(clip.get("timeline_start", clip.get("position")))
                if timeline_start is None:
                    timeline_start = cursor
                timeline_end = timeline_start + render_duration
                cursor = max(cursor, timeline_end)
                if track_type in VIDEO_TRACK_TYPES or track_type:
                    max_end = max(max_end, timeline_end)
    else:
        cursor = 0.0
        for clip in timeline_clips(data):
            start = safe_float(clip.get("start", clip.get("start_time", clip.get("in", 0)))) or 0.0
            end = safe_float(clip.get("end", clip.get("end_time", clip.get("out"))))
            duration = safe_float(clip.get("duration"))
            source_duration = (end - start) if end is not None else duration
            if source_duration is None:
                continue
            cursor += max(0.0, source_duration)
        max_end = cursor
    return round(max_end, 6) if max_end > 0 else None


def timeline_expectation_issues(media: dict, expected: dict) -> list[dict]:
    issues = []
    if not expected or expected.get("error"):
        return issues
    actual_duration = safe_float(media.get("duration_seconds"))
    expected_duration = safe_float(expected.get("duration_seconds"))
    if actual_duration is not None and expected_duration is not None:
        tolerance = max(0.35, expected_duration * 0.03)
        if abs(actual_duration - expected_duration) > tolerance:
            issues.append({
                "severity": "error",
                "message": "preview duration does not match timeline duration",
                "evidence": f"actual={actual_duration:.3f}s expected={expected_duration:.3f}s tolerance={tolerance:.3f}s",
            })
    stream = first_video_stream(media)
    if stream:
        actual_width = safe_int(stream.get("width"))
        actual_height = safe_int(stream.get("height"))
        if expected.get("width") and expected.get("height"):
            if actual_width != int(expected["width"]) or actual_height != int(expected["height"]):
                issues.append({
                    "severity": "error",
                    "message": "preview resolution does not match timeline canvas",
                    "evidence": f"actual={actual_width}x{actual_height} expected={expected['width']}x{expected['height']}",
                })
        expected_fps = safe_float(expected.get("fps"))
        actual_fps = stream_fps(stream)
        if expected_fps is not None and actual_fps is not None and abs(actual_fps - expected_fps) > 0.5:
            issues.append({
                "severity": "warning",
                "message": "preview fps differs from timeline fps",
                "evidence": f"actual={actual_fps:.3f} expected={expected_fps:.3f}",
            })
    return issues


def first_video_stream(media: dict) -> dict:
    streams = media.get("video_streams") or []
    return streams[0] if streams and isinstance(streams[0], dict) else {}


def stream_fps(stream: dict) -> float | None:
    for key in ("avg_frame_rate", "r_frame_rate"):
        value = stream.get(key)
        if not value or value == "0/0":
            continue
        try:
            if "/" in str(value):
                num, den = str(value).split("/", 1)
                den_f = float(den)
                if den_f == 0:
                    continue
                return float(num) / den_f
            return float(value)
        except Exception:
            continue
    return None


def safe_float(value) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if parsed == parsed and parsed not in (float("inf"), float("-inf")) else None


def safe_int(value) -> int | None:
    try:
        return int(value)
    except Exception:
        return None
