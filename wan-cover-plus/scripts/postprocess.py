import json
import re
import subprocess
from pathlib import Path

import edge_tts


def should_postprocess_video(skill_input) -> bool:
    return bool(getattr(skill_input, "enable_narration", False) or getattr(skill_input, "enable_subtitles", False))


def build_auto_narration_text(skill_input) -> str:
    parts = []
    if getattr(skill_input, "title", None):
        parts.append(skill_input.title.strip())
    if getattr(skill_input, "subtitle", None):
        parts.append(skill_input.subtitle.strip())

    highlights = [item.strip() for item in (getattr(skill_input, "highlights", None) or []) if item and item.strip()]
    if highlights:
        parts.append("，".join(highlights[:3]))

    text = "。".join(part for part in parts if part)
    if text and not text.endswith(("。", "！", "？", ".", "!", "?")):
        text += "。"
    return text


def _postprocess_cfg(config: dict) -> dict:
    return config.get("postprocess", {})


def _run_command(command: list[str]):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(stderr or f"Command failed: {' '.join(command)}")
    return result


def probe_media_duration(media_path: str, config: dict) -> float:
    ffprobe_bin = _postprocess_cfg(config).get("ffprobe_bin", "ffprobe")
    result = _run_command(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            media_path,
        ]
    )
    return float((result.stdout or "0").strip() or 0)


def _split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[。！？.!?；;])\s*", normalized) if chunk.strip()]
    return chunks or [normalized]


def _format_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def build_srt_segments(text: str, duration_seconds: float) -> list[tuple[float, float, str]]:
    chunks = _split_sentences(text)
    if not chunks:
        return []

    total_weight = sum(max(len(chunk), 1) for chunk in chunks)
    cursor = 0.0
    segments = []
    for index, chunk in enumerate(chunks):
        weight = max(len(chunk), 1)
        if index == len(chunks) - 1:
            end = max(duration_seconds, cursor)
        else:
            end = cursor + (duration_seconds * weight / total_weight)
        segments.append((cursor, end, chunk))
        cursor = end
    return segments


def write_srt_file(srt_path: Path, segments: list[tuple[float, float, str]]) -> Path:
    lines = []
    for idx, (start, end, text) in enumerate(segments, start=1):
        lines.extend([
            str(idx),
            f"{_format_srt_time(start)} --> {_format_srt_time(end)}",
            text,
            "",
        ])
    srt_path.write_text("\n".join(lines), encoding="utf-8")
    return srt_path


async def _synthesize_tts_async(text: str, output_path: Path, voice: str, rate: str, volume: str):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await communicate.save(str(output_path))


def generate_tts_audio(text: str, output_path: Path, config: dict, skill_input) -> Path:
    cfg = _postprocess_cfg(config)
    voice = getattr(skill_input, "tts_voice", None) or cfg.get("tts_voice", "zh-CN-XiaoxiaoNeural")
    rate = getattr(skill_input, "tts_rate", None) or cfg.get("tts_rate", "+0%")
    volume = getattr(skill_input, "tts_volume", None) or cfg.get("tts_volume", "+0%")
    import asyncio

    asyncio.run(_synthesize_tts_async(text, output_path, voice=voice, rate=rate, volume=volume))
    return output_path


def mux_audio_into_video(video_path: Path, audio_path: Path, output_path: Path, config: dict) -> Path:
    ffmpeg_bin = _postprocess_cfg(config).get("ffmpeg_bin", "ffmpeg")
    _run_command(
        [
            ffmpeg_bin,
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    )
    return output_path


def burn_subtitles_into_video(video_path: Path, subtitle_path: Path, output_path: Path, config: dict) -> Path:
    ffmpeg_bin = _postprocess_cfg(config).get("ffmpeg_bin", "ffmpeg")
    escaped_subtitle_path = str(subtitle_path).replace(":", "\\:")
    subtitle_filter = f"subtitles={escaped_subtitle_path}"
    _run_command(
        [
            ffmpeg_bin,
            "-y",
            "-i",
            str(video_path),
            "-vf",
            subtitle_filter,
            "-c:a",
            "copy",
            str(output_path),
        ]
    )
    return output_path


def run_video_postprocess(api_result: dict, skill_input, config: dict) -> dict:
    original_video = Path(api_result["output_file"])
    narration_enabled = bool(getattr(skill_input, "enable_narration", False))
    subtitles_enabled = bool(getattr(skill_input, "enable_subtitles", False))
    subtitle_mode = getattr(skill_input, "subtitle_mode", None) or _postprocess_cfg(config).get("subtitle_mode", "burned")

    if not narration_enabled and not subtitles_enabled:
        return api_result

    narration_text = (getattr(skill_input, "narration_text", None) or "").strip() or build_auto_narration_text(skill_input)
    subtitle_text = (getattr(skill_input, "subtitle_text", None) or "").strip() or narration_text

    derived = {
        "postprocessed": False,
        "narration_enabled": narration_enabled,
        "subtitles_enabled": subtitles_enabled,
        "subtitle_mode": subtitle_mode,
        "narration_text_used": narration_text or None,
        "subtitle_file": None,
        "narration_audio": None,
        "narrated_video": None,
        "final_video": None,
        "postprocess_error": None,
    }

    working_video = original_video

    try:
        if narration_enabled and narration_text:
            audio_path = original_video.with_suffix(".narration.mp3")
            generate_tts_audio(narration_text, audio_path, config, skill_input)
            narrated_video = original_video.with_suffix(".narrated.mp4")
            mux_audio_into_video(working_video, audio_path, narrated_video, config)
            derived["narration_audio"] = str(audio_path)
            derived["narrated_video"] = str(narrated_video)
            working_video = narrated_video

        if subtitles_enabled and subtitle_text:
            duration = probe_media_duration(str(working_video), config)
            segments = build_srt_segments(subtitle_text, duration)
            srt_path = original_video.with_suffix(".srt")
            write_srt_file(srt_path, segments)
            derived["subtitle_file"] = str(srt_path)

            if subtitle_mode in {"burned", "both"}:
                final_video = original_video.with_suffix(".final.mp4")
                burn_subtitles_into_video(working_video, srt_path, final_video, config)
                derived["final_video"] = str(final_video)
                working_video = final_video

        if subtitle_mode == "sidecar":
            derived["final_video"] = str(working_video)
        elif not derived["final_video"]:
            derived["final_video"] = str(working_video)

        derived["postprocessed"] = True
    except Exception as exc:
        derived["postprocess_error"] = str(exc)

    merged = dict(api_result)
    merged["postprocess"] = derived
    merged["output_file"] = derived.get("final_video") or api_result["output_file"]
    return merged


def format_result(task_type, scene, prompt, api_result, skill_input=None):
    reference_assets = {
        "reference_images": getattr(skill_input, "reference_images", []) if skill_input else [],
        "reference_videos": getattr(skill_input, "reference_videos", []) if skill_input else [],
    }

    output_files = [api_result["output_file"]]
    postprocess = api_result.get("postprocess") or {}
    for key in ["narration_audio", "subtitle_file", "narrated_video", "final_video"]:
        value = postprocess.get(key)
        if value and value not in output_files:
            output_files.append(value)

    return {
        "success": True,
        "task_type": task_type,
        "media_type": api_result.get("media_type", "image"),
        "scene": scene,
        "model_used": api_result.get("model_used"),
        "prompt_used": prompt,
        "reference_assets": reference_assets,
        "output_files": output_files,
        "meta": {
            "prompt_file": api_result.get("prompt_file"),
            "note": api_result.get("note"),
            "task_id": api_result.get("task_id"),
            "video_url": api_result.get("video_url"),
            "duration_seconds": getattr(skill_input, "duration_seconds", None) if skill_input else None,
            "resolution": getattr(skill_input, "resolution", None) if skill_input else None,
            "aspect_ratio": getattr(skill_input, "aspect_ratio", None) if skill_input else None,
            "postprocessed": postprocess.get("postprocessed", False),
            "narration_enabled": postprocess.get("narration_enabled", False),
            "subtitles_enabled": postprocess.get("subtitles_enabled", False),
            "subtitle_mode": postprocess.get("subtitle_mode"),
            "narration_text_used": postprocess.get("narration_text_used"),
            "subtitle_file": postprocess.get("subtitle_file"),
            "narration_audio": postprocess.get("narration_audio"),
            "narrated_video": postprocess.get("narrated_video"),
            "final_video": postprocess.get("final_video"),
            "postprocess_error": postprocess.get("postprocess_error"),
        },
    }
