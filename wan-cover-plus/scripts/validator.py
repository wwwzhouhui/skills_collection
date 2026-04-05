from pathlib import Path
from urllib.parse import urlparse

from schema import SkillInput


SUPPORTED_TASK_TYPES = {"image", "text_to_video", "image_to_video", "reference_to_video"}
SUPPORTED_SCENES = {"wechat_cover", "xiaohongshu_cover", "relayout_poster"}
SUPPORTED_STYLES = {"tech_media", "warm_lifestyle", "premium_brand", "cute_note"}
SUPPORTED_VIDEO_RESOLUTIONS = {"720P", "1080P"}
SUPPORTED_VIDEO_ASPECT_RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4"}
SUPPORTED_SHOT_TYPES = {"single", "multi"}
SUPPORTED_SUBTITLE_MODES = {"burned", "sidecar", "both"}
VIDEO_TASK_TYPES = {"text_to_video", "image_to_video", "reference_to_video"}


def _is_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _validate_reference_paths(paths: list[str], label: str):
    for path in paths:
        if _is_url(path):
            continue
        if not Path(path).exists():
            raise ValueError(f"{label} does not exist: {path}")


def validate_input(data: dict) -> SkillInput:
    task_type = data.get("task_type", "image")
    if task_type not in SUPPORTED_TASK_TYPES:
        raise ValueError(f"unsupported task_type: {task_type}")

    style = data.get("style")
    if task_type == "image":
        if not data.get("title"):
            raise ValueError("title is required")
        if data.get("scene") not in SUPPORTED_SCENES:
            raise ValueError(f"unsupported scene: {data.get('scene')}")
        if style not in SUPPORTED_STYLES:
            raise ValueError(f"unsupported style: {style}")
    else:
        if not data.get("title") and not data.get("prompt"):
            raise ValueError("title or prompt is required for video tasks")
        if style and style not in SUPPORTED_STYLES:
            raise ValueError(f"unsupported style: {style}")

    reference_images = data.get("reference_images") or []
    reference_videos = data.get("reference_videos") or []

    if task_type == "image_to_video":
        if not reference_images:
            raise ValueError("reference_images is required for image_to_video")
    if task_type == "reference_to_video":
        if not reference_images and not reference_videos:
            raise ValueError("reference_images or reference_videos is required for reference_to_video")

    if reference_images:
        _validate_reference_paths(reference_images, "reference image")
    if reference_videos:
        _validate_reference_paths(reference_videos, "reference video")

    resolution = data.get("resolution")
    if resolution and resolution not in SUPPORTED_VIDEO_RESOLUTIONS:
        raise ValueError(f"unsupported resolution: {resolution}")

    aspect_ratio = data.get("aspect_ratio")
    if aspect_ratio and aspect_ratio not in SUPPORTED_VIDEO_ASPECT_RATIOS:
        raise ValueError(f"unsupported aspect_ratio: {aspect_ratio}")

    shot_type = data.get("shot_type")
    if shot_type and shot_type not in SUPPORTED_SHOT_TYPES:
        raise ValueError(f"unsupported shot_type: {shot_type}")

    duration_seconds = data.get("duration_seconds")
    if duration_seconds is not None and not (2 <= int(duration_seconds) <= 15):
        raise ValueError("duration_seconds must be between 2 and 15")

    subtitle_mode = data.get("subtitle_mode")
    if subtitle_mode and subtitle_mode not in SUPPORTED_SUBTITLE_MODES:
        raise ValueError(f"unsupported subtitle_mode: {subtitle_mode}")

    has_tts_related = any(
        data.get(key) is not None
        for key in [
            "enable_narration",
            "enable_subtitles",
            "narration_text",
            "subtitle_text",
            "subtitle_mode",
            "tts_voice",
            "tts_rate",
            "tts_volume",
        ]
    )
    if has_tts_related and task_type not in VIDEO_TASK_TYPES:
        raise ValueError("narration and subtitle options are only supported for video tasks")

    if data.get("enable_narration") and task_type not in VIDEO_TASK_TYPES:
        raise ValueError("enable_narration is only supported for video tasks")

    if data.get("enable_subtitles") and task_type not in VIDEO_TASK_TYPES:
        raise ValueError("enable_subtitles is only supported for video tasks")

    return SkillInput(**data)
