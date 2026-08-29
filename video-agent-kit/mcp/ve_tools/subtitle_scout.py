"""Cheap, task-shaped visual scouting for subtitle placement.

`video_ingest` samples the whole video at 2 fps with no tunable knobs: an 88 s
clip becomes eight contact sheets, roughly 20k image tokens. For *subtitling*
almost all of that is waste. Deciding where captions go needs four answers, and
none of them require dense temporal coverage:

- what already occupies the band the captions will sit in;
- whether the shot changes, because the safe band is the intersection across
  shots, not one frame's worth;
- where faces are, so text does not cover a mouth;
- how bright the background behind the band is, which decides outline weight
  and whether an opaque box is needed.

So this samples one frame per detected shot (evenly spread when there are no
cuts) and returns two small images instead: a downscaled overview strip for
composition and faces, and a native-width strip of just the caption band. That
is roughly a tenth of the tokens and a better match to the question being asked.
The band luminance is also measured numerically, so contrast is not left to
eyeballing a thumbnail.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from .ffproc import run_proc
import time
from pathlib import Path
from typing import Any

from . import subtitle_style as sty
from .result import ToolResult
from .run_context import RunContext
from .subtitle import probe_video_size, run_ffmpeg
from .timeline import file_sha256, media_duration_seconds

DEFAULT_MAX_FRAMES = 12
DEFAULT_SCENE_THRESHOLD = 0.30
OVERVIEW_TILE_WIDTH = 320
BAND_STRIP_WIDTH = 960
_SHOWINFO_TIME = re.compile(r"pts_time:([\d.]+)")


def subtitle_scout(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not args.get("video_path"):
        return ToolResult(text="[ERROR] video_path is required")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    video_path = ctx.resolve(args["video_path"])
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")

    overrides = args.get("style")
    if overrides is not None and not isinstance(overrides, dict):
        return ToolResult(text="[ERROR] style must be an object of style overrides")

    try:
        width, height = probe_video_size(video_path)
    except RuntimeError as exc:
        return ToolResult(text=f"[ERROR] could not probe video size: {exc}")
    duration = media_duration_seconds(video_path)
    if duration is None:
        return ToolResult(text=f"[ERROR] could not probe a valid duration for {video_path}")
    try:
        style = sty.resolve_style(args.get("preset"), overrides, video_width=width, video_height=height)
    except ValueError as exc:
        return ToolResult(text=f"[ERROR] {exc}")

    max_frames = max(2, int(args.get("max_frames") or DEFAULT_MAX_FRAMES))
    threshold = float(args.get("scene_threshold") or DEFAULT_SCENE_THRESHOLD)
    cuts = detect_shot_cuts(video_path, threshold)
    timestamps = pick_timestamps(cuts, duration, max_frames)

    band = caption_band(style)
    work_dir = ctx.resolve(args.get("frames_dir") or f".video_agent/subtitle_scout/{video_path.stem}")
    work_dir.mkdir(parents=True, exist_ok=True)
    for stale in work_dir.glob("*.jpg"):
        stale.unlink()

    frames: list[tuple[float, Path]] = []
    for idx, ts in enumerate(timestamps):
        frame_path = work_dir / f"f{idx:03d}.jpg"
        error = run_ffmpeg([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{ts:.3f}", "-i", str(video_path),
            "-frames:v", "1", "-q:v", "3", str(frame_path),
        ])
        if error or not frame_path.is_file():
            continue
        frames.append((ts, frame_path))
    if not frames:
        return ToolResult(text="[ERROR] could not sample any frame from the video")

    try:
        overview, band_strip, samples = build_scout_images(frames, band, work_dir, style)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not build scout images: {exc}")

    report = {
        "video_path": str(video_path),
        "video_sha256": file_sha256(video_path),
        "video": {"width": width, "height": height, "duration": duration},
        "preset": style["preset"],
        "caption_band": band,
        "shot_cut_count": len(cuts),
        "shot_cuts": [round(c, 3) for c in cuts[:60]],
        "scene_threshold": threshold,
        "sampled_timestamps": [round(t, 3) for t, _ in frames],
        "samples": samples,
        "band_luminance": summarize_luminance(samples),
        "contrast_recommendation": recommend_contrast(samples, style),
        "font_recommendation": recommend_font_size(style),
        "images": {"overview": str(overview), "caption_band": str(band_strip)},
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json = ctx.resolve(args.get("output_json") or "out/subtitle_scout.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    lum = report["band_luminance"]
    rec = report["contrast_recommendation"]
    cut_note = (
        f"{len(cuts)} shot cut(s) detected, so the usable caption band is the intersection across shots — "
        "check every sampled frame, not just the first."
        if cuts else
        "No shot cuts detected; the framing is stable, so one frame's safe band should hold throughout."
    )
    if rec["level"] == "low":
        contrast_note = f"Contrast: low risk — {rec['reason']}. {rec['note']}"
    else:
        contrast_note = (
            f"Contrast: {rec['level'].upper()} risk — {rec['reason']}.\n"
            f"Suggested style override (pass verbatim to subtitle_build --style, or adjust after looking at "
            f"the band strip): {json.dumps(rec['style'], ensure_ascii=False)}\n"
            f"{rec['note']}"
        )
    return ToolResult(
        text=(
            f"Scouted {len(frames)} frame(s) for subtitle placement using preset '{style['preset']}'.\n"
            f"Caption band for this style: y {band['top']}-{band['bottom']} of {height} "
            f"(x {band['left']}-{band['right']}), i.e. the bottom {band['from_bottom_pct']:.1f}%-"
            f"{band['to_bottom_pct']:.1f}% of the frame.\n"
            f"{cut_note}\n"
            f"Band luminance across samples: mean {lum['mean']:.0f}, min {lum['min']:.0f}, max {lum['max']:.0f} "
            f"(0-255). {lum['verdict']}\n"
            f"{contrast_note}\n"
            f"Font size: {report['font_recommendation']['level']} — {report['font_recommendation']['note']}\n\n"
            "Two images follow. The first is a downscaled overview: use it for composition, faces, and how the "
            "shot changes. The second shows only the caption band at readable width, one row per sample with its "
            "timestamp: use it to see exactly what the text will sit on top of. Decide the style and margins from "
            "these, then record the decision and the safe area in out/subtitle_plan.md."
        ),
        data=report,
        artifacts=[str(output_json)],
        image_paths=[str(overview), str(band_strip)],
    )


def recommend_font_size(style: dict[str, Any]) -> dict[str, Any]:
    """A font-size sanity check the model can act on, mirroring the contrast one.

    Font size is the placement decision the model most often gets wrong by
    inheriting a preset default without asking whether it fits *this* frame:
    the vertical short-form preset in particular renders small on a phone. This
    turns the two things that actually decide a good size — the viewing context
    (a phone at arm's length wants bigger text than a desktop 16:9) and the
    resolution — into a concrete target band and a drop-in override, without
    fitting to any one video. It is advice backed by geometry, not a mandate:
    the real confirmation is the cue table `subtitle_build` returns (how many
    cues condense, how full the lines are) and the rendered frame.
    """
    height = int(style["video_height"])
    width = int(style["video_width"])
    cur_px = int(style["font_size"])
    cur_ratio = cur_px / height if height else 0.0
    vertical = height > width

    # Target bands are viewing-context norms, not per-video tuning: phone-first
    # vertical short-form reads best around 4.5-5.5% of frame height; a landscape
    # 16:9 broadcast caption sits around 3.6-4.6%. Both are resolution-independent
    # because they are ratios of height.
    if vertical:
        lo, hi, ideal = 0.045, 0.058, 0.050
        context = "vertical short-form (phone viewing wants large, bold text)"
    else:
        lo, hi, ideal = 0.036, 0.048, 0.042
        context = "landscape 16:9 (comfortable reading distance)"

    target_px = round(height * ideal)
    if cur_ratio < lo - 0.002:
        level = "too_small"
        note = (
            f"Current font_size {cur_px}px is {cur_ratio*100:.1f}% of frame height; "
            f"for {context} aim for {lo*100:.1f}-{hi*100:.1f}%. Consider style "
            f"font_size={target_px} (≈{ideal*100:.1f}%). Then read subtitle_build's cue "
            "table: if lines are short with lots of empty width, you can go larger; if many "
            "cues start condensing (font_scale<1) or hit the line char cap, ease back."
        )
        rec = {"font_size": target_px}
    elif cur_ratio > hi + 0.004:
        level = "too_large"
        note = (
            f"Current font_size {cur_px}px is {cur_ratio*100:.1f}% of frame height, above the "
            f"{lo*100:.1f}-{hi*100:.1f}% band for {context}; it may overflow or crowd. Consider "
            f"font_size={target_px}, and check the cue table for condensed/over-wrapped cues."
        )
        rec = {"font_size": target_px}
    else:
        level = "ok"
        note = (
            f"Current font_size {cur_px}px ({cur_ratio*100:.1f}% of height) is within the "
            f"{lo*100:.1f}-{hi*100:.1f}% band for {context}. Confirm on the frame and via the cue table."
        )
        rec = {}
    return {
        "level": level,
        "orientation": "vertical" if vertical else "landscape",
        "current_font_size": cur_px,
        "current_ratio_pct": round(cur_ratio * 100, 2),
        "target_band_pct": [round(lo * 100, 1), round(hi * 100, 1)],
        "style": rec,
        "note": note,
    }


def caption_band(style: dict[str, Any]) -> dict[str, Any]:
    """Pixel rectangle the resolved style's text will occupy."""
    height = int(style["video_height"])
    width = int(style["video_width"])
    margin_v = int(style["margin_v"])
    font_size = int(style["font_size"])
    lines = int(style["max_lines"])
    # libass measures MarginV from the bottom edge to the bottom of the text.
    bottom = max(0, height - margin_v)
    top = max(0, bottom - int(font_size * 1.25 * lines))
    return {
        "top": top,
        "bottom": bottom,
        "left": int(style["margin_l"]),
        "right": width - int(style["margin_r"]),
        "from_bottom_pct": 100.0 * (height - bottom) / height,
        "to_bottom_pct": 100.0 * (height - top) / height,
    }


def detect_shot_cuts(video_path: Path, threshold: float) -> list[float]:
    """Shot boundary timestamps via ffmpeg scene detection."""
    cmd = [
        "ffmpeg", "-v", "info", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-an", "-f", "null", "-",
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=1800)
    except Exception:
        return []
    log = (proc.stderr or "") + (proc.stdout or "")
    return sorted({round(float(t), 3) for t in _SHOWINFO_TIME.findall(log)})


def pick_timestamps(cuts: list[float], duration: float, max_frames: int) -> list[float]:
    """One sample just after each cut, plus evenly spread fills.

    Sampling *after* a cut is deliberate: the frame that matters for placement is
    the new shot's composition, not the last frame of the old one.
    """
    picks: list[float] = [min(duration * 0.02, 1.0)]
    picks += [min(c + 0.20, duration - 0.05) for c in cuts]
    if len(picks) < max_frames:
        need = max_frames - len(picks)
        step = duration / (need + 1)
        picks += [step * (i + 1) for i in range(need)]
    picks = sorted({round(max(0.0, min(p, duration - 0.05)), 3) for p in picks})
    if len(picks) <= max_frames:
        return picks
    # Thin evenly rather than truncating, so late shots are still represented.
    stride = len(picks) / max_frames
    return [picks[min(len(picks) - 1, int(i * stride))] for i in range(max_frames)]


def build_scout_images(
    frames: list[tuple[float, Path]],
    band: dict[str, Any],
    out_dir: Path,
    style: dict[str, Any],
) -> tuple[Path, Path, list[dict[str, Any]]]:
    from PIL import Image, ImageDraw, ImageFont

    font = _font(16)
    samples: list[dict[str, Any]] = []

    thumbs = []
    bands = []
    for ts, path in frames:
        img = Image.open(path).convert("RGB")
        scale = OVERVIEW_TILE_WIDTH / img.width
        thumbs.append((ts, img.resize((OVERVIEW_TILE_WIDTH, max(1, int(img.height * scale))), Image.LANCZOS)))

        crop = img.crop((band["left"], band["top"], band["right"], band["bottom"]))
        grey = crop.convert("L")
        pixels = list(grey.getdata())
        mean = sum(pixels) / len(pixels) if pixels else 0.0
        peak = max(pixels) if pixels else 0
        samples.append({
            "timestamp": round(ts, 3),
            "band_mean_luminance": round(mean, 1),
            "band_max_luminance": peak,
        })
        bscale = BAND_STRIP_WIDTH / crop.width if crop.width else 1.0
        bands.append((ts, crop.resize((BAND_STRIP_WIDTH, max(1, int(crop.height * bscale))), Image.LANCZOS)))

    cols = min(4, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    tile_h = max(t.height for _, t in thumbs) + 20
    overview = Image.new("RGB", (cols * OVERVIEW_TILE_WIDTH, rows * tile_h), (12, 12, 12))
    draw = ImageDraw.Draw(overview)
    for pos, (ts, thumb) in enumerate(thumbs):
        x = (pos % cols) * OVERVIEW_TILE_WIDTH
        y = (pos // cols) * tile_h
        draw.text((x + 4, y + 3), f"{ts:.2f}s", fill=(255, 230, 110), font=font)
        overview.paste(thumb, (x, y + 20))
        # Mark where the caption band falls, so the overview answers the
        # placement question directly instead of requiring mental arithmetic.
        s = thumb.width / (band["right"] - band["left"]) if band["right"] > band["left"] else 1.0
        full_scale = thumb.height / style["video_height"]
        draw.rectangle(
            [x + int(band["left"] * thumb.width / style["video_width"]),
             y + 20 + int(band["top"] * full_scale),
             x + int(band["right"] * thumb.width / style["video_width"]),
             y + 20 + int(band["bottom"] * full_scale)],
            outline=(255, 90, 90), width=1,
        )
    overview_path = out_dir / "overview.jpg"
    overview.save(overview_path, quality=85)

    label_h = 22
    strip_h = sum(b.height + label_h for _, b in bands)
    strip = Image.new("RGB", (BAND_STRIP_WIDTH, strip_h), (12, 12, 12))
    sdraw = ImageDraw.Draw(strip)
    y = 0
    for ts, crop in bands:
        sdraw.text((6, y + 3), f"{ts:.2f}s  caption band", fill=(255, 230, 110), font=font)
        y += label_h
        strip.paste(crop, (0, y))
        y += crop.height
        sdraw.line([0, y - 1, BAND_STRIP_WIDTH, y - 1], fill=(70, 70, 70))
    strip_path = out_dir / "caption_band.jpg"
    strip.save(strip_path, quality=88)
    return overview_path, strip_path, samples


def summarize_luminance(samples: list[dict[str, Any]]) -> dict[str, Any]:
    values = [s["band_mean_luminance"] for s in samples] or [0.0]
    mean = sum(values) / len(values)
    lo, hi = min(values), max(values)
    if hi > 170:
        verdict = ("Some samples are bright behind the text; white fill needs a heavy outline, or use "
                   "border_style 3 for an opaque box.")
    elif hi - lo > 70:
        verdict = ("Background brightness varies a lot across the video, so a setting that reads well on one "
                   "shot may fail on another; check the brightest sample.")
    elif mean < 90:
        verdict = "Consistently dark behind the text; white fill with the default outline should read cleanly."
    else:
        verdict = "Mid-tone background; verify the outline holds on the brightest sample."
    return {"mean": round(mean, 1), "min": round(lo, 1), "max": round(hi, 1), "verdict": verdict}


def recommend_contrast(samples: list[dict[str, Any]], style: dict[str, Any]) -> dict[str, Any]:
    """Turn measured band luminance into a concrete, ready-to-apply style hint.

    The luminance verdict tells the caller *what* the problem is; this tells it
    *what to pass to subtitle_build* to fix it. Contrast against a bright band is
    the one legibility failure a still cannot lie about and the outline alone
    cannot always solve — a plain white-on-white line survives only on a hairline
    of black. So when any sampled frame is bright behind the text, or the band
    swings between bright and dark across shots, recommend a text-hugging box
    (BorderStyle 3): it guarantees the same contrast on every frame regardless of
    what is under it, which a fixed outline cannot.

    The returned `style` is a drop-in override object; the caller may pass it
    verbatim, adjust it, or reject it after looking at the band strip. It is a
    recommendation backed by a measurement, not a mandate.
    """
    means = [float(s.get("band_mean_luminance") or 0.0) for s in samples] or [0.0]
    maxes = [float(s.get("band_max_luminance") or 0.0) for s in samples] or [0.0]
    mean = sum(means) / len(means)
    hi_mean = max(means)
    lo_mean = min(means)
    spread = hi_mean - lo_mean
    # Peak local brightness matters as much as the band average: a small bright
    # patch (sun glint, a caption-band highlight) under a few glyphs is enough to
    # dissolve them even when the band average reads mid-tone.
    hi_peak = max(maxes)

    # `readability` is a one-word macro (resolved in subtitle_style): "box" seats
    # the text in a semi-transparent black band scaled to the font, "heavy_outline"
    # just thickens the rim. Recommending the macro keeps the four underlying ASS
    # fields consistent — a caller who copies raw values can fumble the alpha or
    # padding; the macro cannot.
    box_style = {"readability": "box"}
    heavy_outline = {"readability": "heavy_outline"}

    bright = hi_mean >= 165 or hi_peak >= 235
    swings = spread >= 60 and hi_mean >= 130
    mid = mean >= 115 or hi_mean >= 140

    if bright or swings:
        reason = (
            f"a sampled band reaches mean luminance {hi_mean:.0f} / peak {hi_peak:.0f} of 255"
            if bright else
            f"the band swings {lo_mean:.0f}->{hi_mean:.0f} across shots, so no single outline reads on every frame"
        )
        return {
            "level": "high",
            "reason": reason,
            "treatment": "box",
            "style": box_style,
            "note": (
                "White-on-outline text will wash out here. The `box` treatment (readability:box, a "
                "semi-transparent band) guarantees contrast on every frame. Confirm on the brightest "
                "band-strip row, then keep it only if the footage genuinely needs it — a box on consistently "
                "dark footage is heavier than it has to be. Step up to readability:opaque_box if a shot is so "
                "bright the semi-transparent band still washes out."
            ),
        }
    if mid:
        return {
            "level": "medium",
            "reason": f"the band runs mid-to-bright (mean {mean:.0f}, brightest {hi_mean:.0f})",
            "treatment": "heavy_outline",
            "style": heavy_outline,
            "note": (
                "Probably readable with a heavier outline; if any band-strip row still looks marginal, step up "
                "to the box treatment (readability:box)."
            ),
        }
    return {
        "level": "low",
        "reason": f"the band is consistently dark (mean {mean:.0f}, brightest {hi_mean:.0f})",
        "treatment": "none",
        "style": {},
        "note": "White fill with the preset outline should read cleanly; no contrast override needed.",
    }


def _font(size: int):
    from PIL import ImageFont

    candidate = sty.resolve_font_file("Noto Sans SC", "regular")
    if candidate:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()
