from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SkillInput:
    title: Optional[str] = None
    scene: Optional[str] = None
    style: Optional[str] = None
    subtitle: Optional[str] = None
    highlights: List[str] = field(default_factory=list)
    brand_colors: List[str] = field(default_factory=list)
    reference_images: List[str] = field(default_factory=list)
    reference_videos: List[str] = field(default_factory=list)
    need_variants: int = 1
    need_text_layout: bool = True
    edit_instruction: Optional[str] = None
    task_type: str = "image"
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    duration_seconds: Optional[int] = None
    resolution: Optional[str] = None
    aspect_ratio: Optional[str] = None
    model: Optional[str] = None
    camera_instruction: Optional[str] = None
    motion_instruction: Optional[str] = None
    shot_type: Optional[str] = None
    audio: Optional[bool] = None
    enable_narration: Optional[bool] = None
    enable_subtitles: Optional[bool] = None
    narration_text: Optional[str] = None
    subtitle_text: Optional[str] = None
    subtitle_mode: Optional[str] = None
    tts_voice: Optional[str] = None
    tts_rate: Optional[str] = None
    tts_volume: Optional[str] = None
