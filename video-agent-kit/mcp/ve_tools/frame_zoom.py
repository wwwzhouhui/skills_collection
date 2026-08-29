"""Recall ORIGINAL-resolution frames, one image per frame, for reading detail.

Why this exists
---------------
`video_ingest` / `video_watch_segment` answer "what is happening here" and pay
for that answer with tiling: frames are packed into a 4-column contact sheet
capped at `sheet_width`, so every frame arrives about 392 px wide. That is the
right trade for judging motion, shot changes, or which panel's mouth is moving —
one image carries 24 moments.

It is the wrong trade for READING something in the frame. A broadcast lower-third,
a webcam name caption, a jersey number or a slide's body text survives 392 px only
marginally: measured on a 1280x720 source, a Chinese name plate lands around 10 px
tall, which is legible to a careful reader and a strong vision model but sits close
enough to the edge that a weaker one confabulates a plausible-looking name instead
of admitting it cannot read it. That failure is silent and expensive — a wrong name
propagates into every downstream speaker label.

So this tool does the opposite of tiling: a handful of exact timestamps in, one
full-resolution image each out, optionally cropped to the region that holds the
text (a name plate occupies maybe 6% of the frame; cropping to it spends the
model's attention where the answer is) and optionally upscaled so small glyphs
clear the tokenizer's patch grid.

Context is the budget people assume is scarce here; it mostly is not. A frontier
model handles hundreds of images per conversation, so the guidance is: when you
need to READ, pay for a few native-resolution crops rather than squint at a grid.

Nothing here calls a model API. It shells out to ffmpeg for exact-timestamp seeks
and returns image paths for the main model to inspect directly.
"""
from __future__ import annotations

import io
import subprocess
from .ffproc import run_proc
from pathlib import Path
from typing import Any

from .result import ToolResult
from .run_context import RunContext

# Region presets, as (left, top, right, bottom) fractions of the frame. These name
# the places broadcast and conference video actually put identifying text; a caller
# who knows better can pass explicit fractions instead.
REGION_PRESETS: dict[str, tuple[float, float, float, float]] = {
    "full": (0.0, 0.0, 1.0, 1.0),
    # Broadcast name plate / chyron: bottom-left corner, where CN/EN TV puts it.
    "name_plate": (0.0, 0.72, 0.55, 1.0),
    # The whole bottom band — lower-thirds, burned-in subtitles, tickers.
    "lower_third": (0.0, 0.66, 1.0, 1.0),
    "bottom_left": (0.0, 0.66, 0.5, 1.0),
    "bottom_right": (0.5, 0.66, 1.0, 1.0),
    # Webcam-grid captions and show bugs live in the corners.
    "top_left": (0.0, 0.0, 0.5, 0.34),
    "top_right": (0.5, 0.0, 1.0, 0.34),
    "center": (0.25, 0.25, 0.75, 0.75),
}

# A cap, not a target. The point of this tool is a few precise looks; someone asking
# for hundreds of native-resolution frames wants video_ingest instead.
MAX_FRAMES = 48
DEFAULT_MAX_FRAMES = 8
# Below this the JPEG artefacts start eating the glyphs we came here to read.
JPEG_QUALITY = 95


def _coerce_times(args: dict) -> list[float]:
    """Explicit timestamps, or a window sampled evenly."""
    raw = args.get("timestamps")
    if raw is not None:
        if not isinstance(raw, list) or not raw:
            raise ValueError("timestamps must be a non-empty array of seconds")
        times = []
        for value in raw:
            try:
                times.append(float(value))
            except (TypeError, ValueError):
                raise ValueError(f"timestamps entries must be numbers; got {value!r}")
        return times

    start, end = args.get("start_time"), args.get("end_time")
    if start is None or end is None:
        raise ValueError("pass either timestamps=[...] or start_time+end_time")
    try:
        start, end = float(start), float(end)
    except (TypeError, ValueError):
        raise ValueError("start_time and end_time must be numbers")
    if end < start:
        raise ValueError(f"end_time ({end}) is before start_time ({start})")
    count = int(args.get("count") or 3)
    if count < 1:
        raise ValueError("count must be >= 1")
    if count == 1:
        return [(start + end) / 2.0]
    step = (end - start) / (count - 1)
    return [start + step * i for i in range(count)]


def _resolve_region(args: dict) -> tuple[float, float, float, float] | None:
    region = args.get("region")
    if region in (None, "", "full"):
        return None
    if isinstance(region, str):
        key = region.strip().lower()
        if key not in REGION_PRESETS:
            raise ValueError(
                f"unknown region preset {region!r}; use one of {sorted(REGION_PRESETS)} "
                "or pass {left,top,right,bottom} fractions"
            )
        box = REGION_PRESETS[key]
        return None if box == REGION_PRESETS["full"] else box
    if isinstance(region, dict):
        try:
            box = (
                float(region["left"]), float(region["top"]),
                float(region["right"]), float(region["bottom"]),
            )
        except (KeyError, TypeError, ValueError):
            raise ValueError("region object needs numeric left, top, right, bottom fractions in [0,1]")
        left, top, right, bottom = box
        if not (0.0 <= left < right <= 1.0 and 0.0 <= top < bottom <= 1.0):
            raise ValueError(f"region fractions must satisfy 0<=left<right<=1 and 0<=top<bottom<=1; got {box}")
        return box
    raise ValueError("region must be a preset name or an object of fractions")


def _grab_frame(video_path: Path, timestamp: float):
    """One exact frame, decoded at full source resolution."""
    from PIL import Image

    cmd = [
        "ffmpeg", "-v", "error", "-ss", f"{max(0.0, timestamp):.6f}", "-i", str(video_path),
        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1",
    ]
    proc = run_proc(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if not proc.stdout:
        raise ValueError(f"ffmpeg returned no frame at {timestamp:.2f}s from {video_path}")
    with Image.open(io.BytesIO(proc.stdout)) as image:
        return image.convert("RGB")


def video_read_frames(args: dict, ctx: RunContext) -> ToolResult:
    """Return original-resolution frames, one image per timestamp, for reading detail."""
    from PIL import Image

    video_arg = args.get("video_path")
    if not video_arg:
        return ToolResult(text="[ERROR] video_path is required")
    video_path = ctx.resolve(video_arg)
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")

    try:
        times = _coerce_times(args)
        region = _resolve_region(args)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}")

    max_frames = int(args.get("max_frames") or DEFAULT_MAX_FRAMES)
    max_frames = max(1, min(max_frames, MAX_FRAMES))
    dropped = max(0, len(times) - max_frames)
    times = sorted(times)[:max_frames]

    # A crop of a name plate can be only ~100 px wide; small glyphs survive the
    # model's patch grid better with an integer upscale. Default 1 (untouched):
    # upscaling adds no information and costs tokens, so it is opt-in.
    try:
        upscale = float(args.get("upscale") or 1.0)
    except (TypeError, ValueError):
        return ToolResult(text="[ERROR] upscale must be a number")
    if not (1.0 <= upscale <= 4.0):
        return ToolResult(text="[ERROR] upscale must be between 1 and 4")

    max_width = args.get("max_width")
    if max_width is not None:
        try:
            max_width = int(max_width)
        except (TypeError, ValueError):
            return ToolResult(text="[ERROR] max_width must be an integer")
        if max_width < 64:
            return ToolResult(text="[ERROR] max_width must be >= 64 (this tool exists to preserve detail)")

    out_dir = ctx.resolve(args.get("output_dir") or f".video_agent/frame_zoom/{video_path.stem}")
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[dict[str, Any]] = []
    failures: list[str] = []
    for timestamp in times:
        try:
            frame = _grab_frame(video_path, timestamp)
        except Exception as exc:  # ffmpeg seek past EOF, unreadable file, ...
            failures.append(f"{timestamp:.2f}s: {exc}")
            continue
        source_size = frame.size
        if region:
            w, h = frame.size
            left, top, right, bottom = region
            box = (int(left * w), int(top * h), max(int(left * w) + 1, int(right * w)),
                   max(int(top * h) + 1, int(bottom * h)))
            frame = frame.crop(box)
        if upscale > 1.0:
            frame = frame.resize(
                (int(frame.width * upscale), int(frame.height * upscale)), Image.LANCZOS
            )
        if max_width and frame.width > max_width:
            ratio = max_width / frame.width
            frame = frame.resize((max_width, max(1, int(frame.height * ratio))), Image.LANCZOS)

        name = f"t{timestamp:09.3f}".replace(".", "_")
        if region:
            name += "_crop"
        path = out_dir / f"{name}.jpg"
        frame.save(path, quality=JPEG_QUALITY, subsampling=0)
        written.append({
            "timestamp": round(timestamp, 3),
            "path": str(path),
            "size": list(frame.size),
            "source_frame_size": list(source_size),
        })

    if not written:
        detail = "; ".join(failures) or "no frames produced"
        return ToolResult(text=f"[ERROR] could not read any frame: {detail}")

    region_note = (
        f"cropped to {args.get('region')!r} " if region else "full frame "
    )
    lines = "\n".join(
        f"- {item['timestamp']:.2f}s  {item['size'][0]}x{item['size'][1]}px  {ctx.virtualize(Path(item['path']))}"
        for item in written
    )
    warn = ""
    if failures:
        warn += f"\n[warn] {len(failures)} timestamp(s) failed: {'; '.join(failures[:3])}"
    if dropped:
        warn += f"\n[warn] {dropped} timestamp(s) beyond max_frames={max_frames} were not read."

    source_w = written[0]["source_frame_size"][0]
    delivered_w = written[0]["size"][0]
    return ToolResult(
        text=(
            f"Read {len(written)} frame(s) at original resolution ({region_note}"
            f"source frame {source_w}px wide, delivered {delivered_w}px). "
            "Each frame is a separate image below — no contact-sheet tiling, so small text "
            "keeps the pixels it had in the source.\n"
            f"{lines}{warn}\n\n"
            "Use this to READ (name plates, lower-thirds, slides, jersey numbers, UI text). "
            "For judging motion, cuts, or who is speaking across a span, video_watch_segment's "
            "sheets are cheaper and better suited.\n"
            "If a name is still not legible here, say so and fall back to a neutral label — "
            "an honest 'speaker A' beats a guessed name."
        ),
        data={
            "tool": "video_read_frames",
            "video_path": str(video_path),
            "region": args.get("region") or "full",
            "frames": written,
            "failed": failures,
        },
        artifacts=[str(out_dir)],
        image_paths=[item["path"] for item in written],
    )
