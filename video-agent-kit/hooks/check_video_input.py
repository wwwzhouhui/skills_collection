#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from hook_common import project_dir, read_stdin_json

VIDEO_PATH_RE = re.compile(
    # Explicit right boundary instead of \b: CJK characters count as \w, so \b
    # would fail to match "input.mp4剪成..." in Chinese prompts.
    r"[^\s'\"()\[\]<>,;:!?，、。；：！？]+\.(?:mp4|mov|webm|mkv|avi)(?![0-9A-Za-z_])",
    re.IGNORECASE,
)
MAX_VIDEOS = 3


def duration_seconds(path: Path) -> float:
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        cap.release()
        return frames / fps if fps > 0 else 0.0
    except Exception:
        return 0.0


def grid_start_ms(path: Path) -> int:
    match = re.search(r"_grid_(\d+)ms_", path.name)
    return int(match.group(1)) if match else 1 << 62


def existing_sheets(project: Path, video: Path) -> tuple[list[Path], bool]:
    """返回 (sheets, attributed)。attributed=False 表示 sheets 来自不按视频
    区分的共享目录 (project/ingest), 可能属于另一个源视频, 提示措辞须保留
    核对余地 — 否则会诱导 agent 拿视频 A 的 sheet 当视频 B 的观察。"""
    import hashlib

    digest = hashlib.sha256(str(video.resolve()).encode("utf-8")).hexdigest()[:8]
    scoped = [
        # 与 video_observe.video_frames_dir_id 一致的新默认命名 (stem+路径哈希)
        project / ".video_agent" / "video_frames" / f"{video.stem}_{digest}_full" / "sheets",
        # 旧默认命名 (仅 stem), 兼容既有项目
        project / ".video_agent" / "video_frames" / f"{video.stem}_full" / "sheets",
        project / ".video_agent" / "video_frames" / video.stem / "sheets",
    ]
    for directory in scoped:
        if not directory.is_dir():
            continue
        sheets = sorted(directory.glob("video_grid_*.jpg"), key=grid_start_ms)
        if sheets:
            return sheets, True
    shared = project / "ingest"
    if shared.is_dir():
        sheets = sorted(shared.glob("video_grid_*.jpg"), key=grid_start_ms)
        if sheets:
            return sheets, False
    return [], True


def resolve_candidate(raw: str, project: Path) -> Path | None:
    """Resolve a regex match to an existing file. Chinese prompts often glue
    text to the path ("请把input.mp4剪成...") and filenames may legitimately
    contain CJK characters, so when the full match does not exist, retry
    progressively shorter left-trimmed suffixes until one names a real file.

    左裁剪只允许发生在首个路径分隔符之前 (含该分隔符): 越过 '/'
    会把 URL/外机路径 (http://cdn/x/input.mp4、C:\\v\\input.mp4) 裁成裸文件名,
    误绑到项目里无关的同名本地文件。is_file 也要进 try: 超长 token 的
    ENAMETOOLONG 不属于 is_file 自吞的错误类, 会把 hook 整个炸掉。"""
    sep_positions = [i for i in (raw.find("/"), raw.find("\\")) if i != -1]
    max_start = min(sep_positions) if sep_positions else len(raw) - 1
    for start in range(max_start + 1):
        candidate = raw[start:]
        path = Path(candidate)
        if not path.is_absolute():
            path = project / candidate
        try:
            path = path.resolve()
            if path.is_file():
                return path
        except (OSError, ValueError):
            # OSError: ENAMETOOLONG 等; ValueError: 含 \x00 的 candidate
            continue
    return None


def main() -> None:
    data = read_stdin_json()
    prompt = data.get("prompt") or ""
    project = project_dir()
    seen: set[Path] = set()
    lines: list[str] = []

    for match in VIDEO_PATH_RE.finditer(prompt):
        path = resolve_candidate(match.group(0), project)
        if path is None or path in seen:
            continue
        seen.add(path)
        if len(seen) > MAX_VIDEOS:
            break

        sheets, attributed = existing_sheets(project, path)
        if sheets and attributed:
            listed = "\n".join(f"  - {sheet}" for sheet in sheets)
            lines.append(
                f"[video-agent-kit] Local video {path} already has timestamped contact sheet(s). "
                "If this task requires visual inspection, read these sheets before planning; use "
                f"video_watch_segment for local high-FPS rewatch:\n{listed}"
            )
        elif sheets:
            listed = "\n".join(f"  - {sheet}" for sheet in sheets)
            lines.append(
                f"[video-agent-kit] Found contact sheet(s) in the shared ingest/ directory, but they are "
                f"NOT attributable to {path} (the directory is not per-video and may hold sheets from a "
                "different source). Verify they match this video before reusing; when in doubt, run "
                f"video_ingest on {path} instead:\n{listed}"
            )
        else:
            duration = duration_seconds(path)
            duration_text = f" (~{duration:.0f}s)" if duration > 0 else ""
            lines.append(
                f"[video-agent-kit] Detected local video input {path}{duration_text}. "
                "If this task requires transcription, audio/speech understanding, or viewing the video, "
                "follow the standard flow: call speech_transcribe(input_path) first (provider=auto uses the "
                "configured cloud ASR service) to produce out/transcript.json, then "
                "video_ingest(video_path, transcript_path) so every contact sheet is paired with matching "
                "speech text; use video_watch_segment only for specific uncertain moments afterwards."
            )

    if not lines:
        sys.exit(0)
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines),
        }
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
