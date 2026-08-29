from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    text: str
    data: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)
    video_paths: list[str] = field(default_factory=list)

