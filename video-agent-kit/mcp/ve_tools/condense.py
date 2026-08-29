"""Condense a rambling talk into a tight cut: index, plan, render, verify.

The four tools here mirror the subtitle family (`build`/`render`/`qc`) because
the discipline is the same: the deterministic work is done by the tool, the
editorial work is left to the model, and nothing is believed until it has been
measured on the rendered file.

Division of labour:

- `condense_index` measures the recording — sentence-sized units, disfluency
  spans, pauses, repetition, and how short the piece could get without dropping
  any content at all. That last number matters: it is the difference between
  "this target needs tighter pauses" and "this target needs half the sentences
  gone", and a model that does not know it will either over-cut or fail silently.
- `condense_plan` turns a keep-list into cut points. Choosing *what* to keep is
  editorial; choosing *where the blade lands* is not, and this is where a cut
  sounds natural or does not: boundaries move outward into real silence, a
  little breath is kept on each side, and every join is checked for the ways a
  removal breaks the sentence that follows it.
- `condense_render` builds the file, with the two treatments that make a jump
  cut read as intentional rather than broken.
- `condense_qc` measures the result and hands back frame and waveform evidence
  at each join, because "ffmpeg exited zero" says nothing about whether the cut
  sounds like a person talking.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from .ffproc import run_proc, require_ffmpeg
import time
from pathlib import Path
from typing import Any

from . import condense_lang as lang
from .result import ToolResult
from .run_context import RunContext
from .subtitle import (
    detect_pauses,
    load_timed_segments,
    measure_loudness,
    resolve_silence_db,
)
from .timeline import file_sha256, media_duration_seconds

DEFAULT_UNIT_PAUSE = 0.55
DEFAULT_MAX_UNIT_SECONDS = 14.0
DEFAULT_MIN_SILENCE = 0.10
DEFAULT_MAX_GAP = 0.45
DEFAULT_LEAD_IN = 0.10
DEFAULT_LEAD_OUT = 0.22
DEFAULT_MIN_CLIP = 0.60
DEFAULT_SNAP_WINDOW = 0.30
DEFAULT_TABLE_ROWS = 140

_MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?[\d.]+)\s*dB")


# --- shared helpers -------------------------------------------------------

def _number(value: object, default: float) -> float:
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def _positive(value: object, default: float) -> float:
    parsed = _number(value, default)
    return parsed if parsed > 0 else default


def _bool(value: object, default: bool) -> bool | None:
    """Booleans must be real booleans; a string "false" is a caller bug."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return None


def _fmt(seconds: float) -> str:
    if not math.isfinite(seconds):
        return "?"
    minutes, rest = divmod(max(0.0, seconds), 60.0)
    return f"{int(minutes)}:{rest:04.1f}"


def _pause_at(pauses: list[tuple[float, float]], boundary: float, window: float) -> tuple[float, float] | None:
    best: tuple[float, tuple[float, float]] | None = None
    for start, end in pauses:
        if start <= boundary <= end:
            distance = 0.0
        else:
            distance = min(abs(boundary - start), abs(boundary - end))
        if distance > window:
            continue
        if best is None or distance < best[0]:
            best = (distance, (start, end))
    return best[1] if best else None


def _silence_total(pauses: list[tuple[float, float]]) -> float:
    return sum(max(0.0, end - start) for start, end in pauses)


def _all_words(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for unit in units:
        for word in unit.get("words") or []:
            words.append(word)
    words.sort(key=lambda w: w["start"])
    return words


def _spans_seconds(spans: list[dict[str, Any]]) -> float:
    return sum(max(0.0, float(s["end"]) - float(s["start"])) for s in spans)


def _preview(text: str, width: int = 46) -> str:
    body = " ".join(text.split())
    if len(body) <= width:
        return body
    return body[: width - 1] + "…"


# --- coarse visual survey -------------------------------------------------

# Frame budget is driven by the number of distinct framings, floored low and
# capped high — the opposite of a fixed "8 frames" that is too few to see a
# many-shot video and pure waste on a static talking head (8 near-identical
# thumbnails). A locked-off single shot is knowable from a couple of frames; a
# 49-cut recording needs one per shot. Tiles are large enough that burned-in
# captions in the lower third are actually legible.
MIN_SURVEY_FRAMES = 3
MAX_SURVEY_FRAMES = 32
SURVEY_TILE_WIDTH = 360
DEFAULT_SCENE_THRESHOLD = 0.30


def visual_survey(
    video_path: Path,
    duration: float,
    work_dir: Path,
    *,
    frames: int | None = None,
    scene_threshold: float = DEFAULT_SCENE_THRESHOLD,
) -> dict[str, Any]:
    """A deliberately cheap look at the picture, sized to the content.

    Condensing is decided from the text. What the picture has to answer is much
    narrower than for subtitling, and none of it needs temporal density:

    - **how many shots are there, and how much does the footage move?** That
      decides the join treatment (near-static footage makes every cut a visible
      jump (keep longer runs); footage that already cuts hides your cuts among
      its own).
    - **is there burned-in text or a graphic?** It changes at cuts too, and a
      caption jumping mid-word is as obvious as the picture jumping.

    The budget scales with **the number of distinct framings, not the duration**.
    That distinction is the whole point: cost must not grow with length (a 2 fps
    sweep of a long recording costs orders of magnitude more and answers a
    question nobody asked here), but a recording with fifty shot cuts genuinely
    has more framings to reconcile than a locked-off talking head, and eight
    frames would show one in six of them. So the count is derived from the
    detected cut count and hard-capped: a static single shot needs ~6, a
    heavily-cut recording gets up to `MAX_SURVEY_FRAMES`, and a forty-minute
    single-shot podcast still costs the same as a three-minute one.

    Anything the text implies is worth seeing (a demo, a gesture, an on-screen
    diagram) leaves a trace in the transcript, and those traces are reported
    separately as timestamps to look at directly.
    """
    from PIL import Image, ImageDraw

    cuts = _detect_shot_cuts(video_path, scene_threshold)
    if frames is None:
        # One frame per distinct shot (plus the floor), so a static clip gets a
        # handful and a heavily-cut one gets one per framing up to the cap.
        auto = MIN_SURVEY_FRAMES + len(cuts)
        budget = max(MIN_SURVEY_FRAMES, min(auto, MAX_SURVEY_FRAMES))
        budget_basis = f"auto from {len(cuts)} shot cut(s)"
    else:
        budget = max(2, min(int(frames), MAX_SURVEY_FRAMES))
        budget_basis = "caller-specified"
    timestamps = _survey_timestamps(cuts, duration, budget)

    work_dir.mkdir(parents=True, exist_ok=True)
    for stale in work_dir.glob("survey_*.jpg"):
        stale.unlink()

    tiles: list[tuple[float, Any]] = []
    for idx, moment in enumerate(timestamps):
        path = work_dir / f"survey_{idx:02d}.jpg"
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{moment:.3f}", "-i", str(video_path),
            "-frames:v", "1", "-vf", f"scale={SURVEY_TILE_WIDTH}:-2", "-q:v", "4", str(path),
        ]
        try:
            run_proc(cmd, capture_output=True, text=True, timeout=120)
        except Exception:
            continue
        if path.is_file():
            try:
                tiles.append((moment, Image.open(path).convert("RGB")))
            except Exception:
                continue
    if not tiles:
        return {"performed": False, "reason": "could not sample any frame from the video"}

    stability = _motion_baseline(video_path, [t for t, _ in tiles], work_dir, _probe_fps(video_path))
    columns = min(4, len(tiles))
    rows = (len(tiles) + columns - 1) // columns
    tile_h = max(img.height for _, img in tiles) + 18
    sheet = Image.new("RGB", (columns * SURVEY_TILE_WIDTH, rows * tile_h), (12, 12, 12))
    draw = ImageDraw.Draw(sheet)
    font = _qc_font(13)
    for pos, (moment, img) in enumerate(tiles):
        x = (pos % columns) * SURVEY_TILE_WIDTH
        y = (pos // columns) * tile_h
        draw.text((x + 4, y + 2), f"{_fmt(moment)} ({moment:.1f}s)", fill=(255, 230, 110), font=font)
        sheet.paste(img, (x, y + 18))
    sheet_path = work_dir / "visual_survey.jpg"
    sheet.save(sheet_path, quality=84)

    return {
        "performed": True,
        "image": str(sheet_path),
        "frame_count": len(tiles),
        "frame_budget": budget,
        "frame_budget_basis": budget_basis,
        "sampled_timestamps": [round(t, 2) for t, _ in tiles],
        "shot_cut_count": len(cuts),
        "shot_cuts": [round(c, 2) for c in cuts[:40]],
        "scene_threshold": scene_threshold,
        "frames_per_minute": round(len(tiles) / max(1e-6, duration / 60.0), 2),
        **stability,
    }


def _detect_shot_cuts(video_path: Path, threshold: float) -> list[float]:
    from .subtitle_scout import detect_shot_cuts

    return detect_shot_cuts(video_path, threshold)


def _survey_timestamps(cuts: list[float], duration: float, frames: int) -> list[float]:
    """Spread the fixed budget over the recording, favouring new shots.

    Sampling one frame per cut is what a subtitle scout does, and it does not
    scale: a forty-minute podcast can have hundreds of cuts. Here the budget is
    fixed, so cuts are *thinned* into it rather than driving it, and the rest of
    the budget spreads evenly so a long stretch without cuts is still seen.
    """
    picks = [min(duration * 0.02, 2.0)]
    if cuts:
        keep = max(1, frames // 2)
        stride = max(1, len(cuts) // keep)
        picks += [min(c + 0.25, duration - 0.05) for c in cuts[::stride][:keep]]
    remaining = max(0, frames - len(picks))
    if remaining:
        step = duration / (remaining + 1)
        picks += [step * (i + 1) for i in range(remaining)]
    picks = sorted({round(max(0.0, min(p, max(0.0, duration - 0.05))), 2) for p in picks})
    if len(picks) <= frames:
        return picks
    stride = len(picks) / frames
    return [picks[min(len(picks) - 1, int(i * stride))] for i in range(frames)]


def _motion_baseline(video_path: Path, timestamps: list[float], work_dir: Path, fps: float) -> dict[str, Any]:
    """How much this footage moves between *adjacent* frames.

    An earlier version inferred "is the framing stable" by diffing the survey
    thumbnails against each other. That was unsound: the samples are tens of
    seconds apart, so on a locked-off three-person webcam grid the people have
    moved a lot and the metric reported `variable_framing` for footage that never
    changes framing at all.

    The question that actually matters is what a cut will look like, and a cut is
    judged against the shot's *own* frame-to-frame motion — the same baseline QC
    uses on the rendered file. So measure that directly: at each sample point,
    two frames one and a half frames apart. Low motion means every cut will read
    as a jump (keep longer runs); busy footage hides cuts among its own
    change. This is the pre-render estimate of the number QC measures after.
    """
    from PIL import Image

    step = 1.5 / max(1.0, fps)
    diffs: list[float] = []
    for idx, moment in enumerate(timestamps[:8]):
        pair = []
        for slot, offset in enumerate((0.0, step)):
            path = work_dir / f"motion_{idx:02d}_{slot}.jpg"
            cmd = [
                "ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, moment + offset):.4f}",
                "-i", str(video_path), "-frames:v", "1", "-vf", "scale=96:-2", "-q:v", "4", str(path),
            ]
            try:
                run_proc(cmd, capture_output=True, text=True, timeout=60)
            except Exception:
                break
            if not path.is_file():
                break
            try:
                pair.append(Image.open(path).convert("L"))
            except Exception:
                break
        if len(pair) == 2 and pair[0].size == pair[1].size:
            data_a, data_b = list(pair[0].getdata()), list(pair[1].getdata())
            diffs.append(sum(abs(x - y) for x, y in zip(data_a, data_b)) / max(1, len(data_a)))
    for stale in work_dir.glob("motion_*.jpg"):
        stale.unlink()
    if not diffs:
        return {"motion_baseline": None, "motion": "unknown", "note": "could not measure frame-to-frame motion"}

    median = sorted(diffs)[len(diffs) // 2]
    if median < 2.0:
        motion, note = "locked_off", (
            "Frame-to-frame motion is very low: this is a near-static shot. Every cut you make will be a visible "
            "jump against that stillness, so plan on keeping long consecutive runs. "
            "QC measures each cut against this same baseline and will tell you which ones actually jump."
        )
    elif median < 6.0:
        motion, note = "moderate_motion", (
            "Moderate frame-to-frame motion. Cuts will be noticeable but not glaring; decide per cut from the QC "
            "jump ratio and its frame row."
        )
    else:
        motion, note = "busy", (
            "The footage moves a lot frame to frame, so your cuts will hide among that motion. Straight cuts are "
            "usually fine here."
        )
    return {"motion_baseline": round(median, 2), "motion": motion, "note": note}


# --- condense_index -------------------------------------------------------

def condense_index(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not args.get("video_path"):
        return ToolResult(text="[ERROR] video_path is required")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    video_path = ctx.resolve(args["video_path"])
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")
    transcript_path = ctx.resolve(args.get("transcript_path") or "out/transcript.json")
    if not transcript_path.is_file():
        return ToolResult(
            text=f"[ERROR] transcript not found: {transcript_path}. Run transcribe first — "
            "condensing needs timestamped text, and cloud_asr may provide word-level times "
            "that let cut points land between words instead of inside one."
        )

    duration = media_duration_seconds(video_path)
    if duration is None:
        return ToolResult(text=f"[ERROR] could not probe a valid duration for {video_path}")
    try:
        segments = load_timed_segments(transcript_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read transcript: {exc}")
    if not segments:
        return ToolResult(
            text="[ERROR] transcript has no timestamped segments; condensing decisions are made on text with "
            "times, so there is nothing to index. Check that transcribe produced segments[] with start/end."
        )

    unit_pause = _positive(args.get("unit_pause_seconds"), DEFAULT_UNIT_PAUSE)
    max_unit = _positive(args.get("max_unit_seconds"), DEFAULT_MAX_UNIT_SECONDS)
    min_silence = _positive(args.get("min_silence_seconds"), DEFAULT_MIN_SILENCE)
    max_gap = _positive(args.get("max_gap"), DEFAULT_MAX_GAP)

    loudness = measure_loudness(video_path)
    silence_db, silence_reason = resolve_silence_db(args.get("silence_db"), loudness)
    pauses = detect_pauses(video_path, silence_db=silence_db, min_silence=min_silence)

    units = lang.split_units(segments, unit_pause=unit_pause, max_unit_seconds=max_unit)
    if not units:
        return ToolResult(text="[ERROR] transcript produced no usable units after segmentation")
    language = str(args.get("language") or "").strip() or lang.guess_language("".join(u["text"] for u in units[:40]))
    duplicates = lang.find_near_duplicates(units)

    records: list[dict[str, Any]] = []
    for idx, unit in enumerate(units):
        prev_end = units[idx - 1]["end"] if idx else 0.0
        next_start = units[idx + 1]["start"] if idx + 1 < len(units) else duration
        disfluency = lang.find_disfluencies(unit, language)
        features = lang.unit_features(unit, language)
        removable = _spans_seconds(disfluency["hard"]) + _spans_seconds(disfluency["stutter"])
        span = max(1e-6, unit["end"] - unit["start"])
        record = {
            "id": unit["id"],
            "index": idx,
            "start": round(unit["start"], 3),
            "end": round(unit["end"], 3),
            "duration": round(span, 3),
            "speaker": unit.get("speaker"),
            "text": unit["text"],
            "chars": features["chars"],
            "cps": round(features["chars"] / span, 2),
            "lead_gap": round(max(0.0, unit["start"] - prev_end), 3),
            "trail_gap": round(max(0.0, next_start - unit["end"]), 3),
            "timing_source": unit["timing_source"],
            "has_terminal_punct": features["has_terminal_punct"],
            "opens_with_connective": features["opens_with_connective"],
            "anaphora": features["anaphora"],
            "enum_first": features["enum_first"],
            "enum_later": features["enum_later"],
            "is_question": features["is_question"],
            "visual_reference": features["visual_reference"],
            "disfluency": {
                "hard": disfluency["hard"],
                "soft": disfluency["soft"],
                "stutter": disfluency["stutter"],
            },
            "removable_disfluency_seconds": round(removable, 3),
            "soft_filler_seconds": round(_spans_seconds(disfluency["soft"]), 3),
            "pause_before": _pause_at(pauses, unit["start"], DEFAULT_SNAP_WINDOW) is not None,
            "pause_after": _pause_at(pauses, unit["end"], DEFAULT_SNAP_WINDOW) is not None,
            "word_count": len(unit.get("words") or []),
            # The words themselves, not just their count. Two downstream checks
            # are dead without them and fail silently: mid_word_cut (the only
            # blocking error on cut placement) and the word timings carried into
            # the remapped transcript so a later subtitle pass needs no re-ASR.
            # They live only in the file, never in a tool return.
            "words": unit.get("words") or [],
        }
        dup = duplicates.get(unit["id"])
        if dup:
            record["near_duplicate_of"] = dup["duplicate_of"]
            record["similarity"] = dup["similarity"]
        records.append(record)

    totals, budget = _index_totals(records, duration, pauses, max_gap)
    silence_seconds = _silence_total(pauses)
    pause_check = _pause_sanity(pauses, silence_seconds, duration, totals["speech_seconds"], silence_db)
    survey_on = _bool(args.get("visual_survey"), True)
    if survey_on is None:
        return ToolResult(text="[ERROR] visual_survey must be a boolean")
    if survey_on:
        survey = visual_survey(
            video_path, duration,
            ctx.resolve(args.get("frames_dir") or f".video_agent/condense_survey/{video_path.stem}"),
            frames=int(args["survey_frames"]) if args.get("survey_frames") is not None else None,
            scene_threshold=_positive(args.get("scene_threshold"), DEFAULT_SCENE_THRESHOLD),
        )
    else:
        survey = {"performed": False, "reason": "visual_survey=false"}
    timing_sources = {r["timing_source"] for r in records}
    timing = timing_sources.pop() if len(timing_sources) == 1 else "mixed"

    report = {
        "video_path": str(video_path),
        "video_sha256": file_sha256(video_path),
        "transcript_path": str(transcript_path),
        "transcript_sha256": file_sha256(transcript_path),
        "language": language,
        "timing_source": timing,
        "source_duration": round(duration, 3),
        "audio": {
            "mean_volume_db": loudness.get("mean_volume_db"),
            "max_volume_db": loudness.get("max_volume_db"),
            "silence_db": silence_db,
            "silence_db_reason": silence_reason,
            "min_silence_seconds": min_silence,
            "pause_count": len(pauses),
            "silence_seconds": round(silence_seconds, 3),
            "pause_detection": pause_check,
        },
        "segmentation": {
            "unit_pause_seconds": unit_pause,
            "max_unit_seconds": max_unit,
            "asr_segment_count": len(segments),
            "unit_count": len(records),
        },
        "totals": totals,
        "budget": budget,
        "visual_survey": survey,
        "visual_check_timestamps": _visual_check_list(records),
        "topic_runs": lang.find_topic_runs(units, language),
        "trim_candidates": _trim_candidates(records),
        "units": records,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json = ctx.resolve(args.get("output_json") or "out/speech_index.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    table_rows = int(_positive(args.get("max_table_rows"), DEFAULT_TABLE_ROWS))
    table_md = ctx.resolve(args.get("output_table") or "out/speech_index.md")
    table_md.write_text(_unit_table_markdown(report), encoding="utf-8")

    return ToolResult(
        text=_index_text(report, table_rows, ctx.virtualize(table_md)),
        data={k: v for k, v in report.items() if k != "units"},
        artifacts=[str(output_json), str(table_md)],
        image_paths=[survey["image"]] if survey.get("image") else [],
    )


def _index_totals(
    records: list[dict[str, Any]],
    duration: float,
    pauses: list[tuple[float, float]],
    max_gap: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    speech = sum(r["duration"] for r in records)
    gaps = [r["lead_gap"] for r in records[1:]]
    long_gap_excess = sum(max(0.0, g - max_gap) for g in gaps)
    head_tail = max(0.0, duration - speech - sum(gaps))
    disfluency = sum(r["removable_disfluency_seconds"] for r in records)
    soft = sum(r["soft_filler_seconds"] for r in records)
    dup_seconds = sum(r["duration"] for r in records if r.get("near_duplicate_of"))
    speakers = sorted({str(r["speaker"]) for r in records if r.get("speaker")})

    totals = {
        "source_duration": round(duration, 3),
        "speech_seconds": round(speech, 3),
        "gap_seconds": round(max(0.0, duration - speech), 3),
        "inter_unit_gap_seconds": round(sum(gaps), 3),
        "head_tail_seconds": round(head_tail, 3),
        "long_gap_excess_seconds": round(long_gap_excess, 3),
        "removable_disfluency_seconds": round(disfluency, 3),
        "soft_filler_seconds": round(soft, 3),
        "near_duplicate_seconds": round(dup_seconds, 3),
        "unit_count": len(records),
        "speakers": speakers,
        "speaker_count": len(speakers),
        "question_count": sum(1 for r in records if r["is_question"]),
        "units_without_terminal_punct": sum(1 for r in records if not r["has_terminal_punct"]),
    }

    # The lossless floor: keep every sentence, but tighten every pause to
    # `max_gap` and excise hesitation sounds and stutters. Anything shorter than
    # this requires dropping content, and anything longer is reachable without an
    # editorial decision at all. A target below the floor is the single most
    # useful thing to know before choosing what to keep.
    floor = max(0.0, speech - disfluency + min(sum(gaps), max_gap * max(0, len(records) - 1)))
    # Targets are NOT clamped to the floor. Clamping would report "0:20.5" as the
    # aggressive target on a dense recording and imply the piece cannot go
    # shorter, which is false — it can, by dropping sentences. Instead each target
    # says whether it needs content removed, which is the actual decision.
    targets = {}
    for name, ratio in (("light", 0.80), ("medium", 0.60), ("aggressive", 0.40)):
        seconds = duration * ratio
        targets[name] = {
            "seconds": round(seconds, 1),
            "ratio": ratio,
            "needs_content_dropped": seconds < floor - 0.5,
            "content_seconds_to_drop": round(max(0.0, floor - seconds), 1),
        }
    budget = {
        "lossless_floor_seconds": round(floor, 3),
        "lossless_floor_ratio": round(floor / duration, 3) if duration else None,
        "free_savings_seconds": round(max(0.0, duration - floor), 3),
        "suggested_targets": targets,
        "note": (
            f"Tightening pauses to {max_gap:.2f}s and removing hesitation sounds alone gets this from "
            f"{_fmt(duration)} to about {_fmt(floor)} ({floor / duration:.0%} of source) without dropping a single "
            f"sentence. Every second below {_fmt(floor)} has to come out of content."
        ),
    }
    return totals, budget


def _pause_sanity(
    pauses: list[tuple[float, float]],
    silence_seconds: float,
    duration: float,
    speech_seconds: float,
    silence_db: float,
) -> dict[str, Any]:
    """Is the silence threshold actually finding the speaker's breaths?

    Every cut point in this pipeline is snapped to a detected silence, so a
    mis-set threshold does not fail loudly — it quietly produces cuts placed by
    arithmetic instead of by ear. The check is a cross-reference the tool already
    has both halves of: the transcript says how much of the recording is speech,
    and `silencedetect` says how much is quiet. When those two disagree badly,
    the threshold is wrong, and it is worth saying so before any cut is planned.
    """
    non_speech = max(0.0, duration - speech_seconds)
    ratio = silence_seconds / duration if duration else 0.0
    if duration <= 0:
        return {"verdict": "unknown", "note": "could not evaluate pause detection"}
    if silence_seconds > non_speech * 1.8 + 1.0:
        return {
            "verdict": "threshold_too_high",
            "detected_silence_ratio": round(ratio, 3),
            "note": (
                f"{silence_seconds:.1f}s was detected as silence but the transcript only leaves {non_speech:.1f}s "
                f"outside speech, so the {silence_db:.0f} dB threshold is counting quiet speech as silence. Cut "
                'points would snap into the middle of words. Re-run with silence_db="auto" (or a lower number) '
                "before planning."
            ),
        }
    if pauses and silence_seconds < non_speech * 0.25 and non_speech > 1.5:
        return {
            "verdict": "threshold_too_low",
            "detected_silence_ratio": round(ratio, 3),
            "note": (
                f"only {silence_seconds:.1f}s of silence was detected across {non_speech:.1f}s of non-speech time, "
                f"so the {silence_db:.0f} dB threshold is missing the speaker's breaths (room tone or a music bed "
                "sits above it). Most boundaries will fail to snap and their times will be derived. Try "
                'silence_db="auto" or a higher number.'
            ),
        }
    if not pauses:
        return {
            "verdict": "no_pauses_found",
            "detected_silence_ratio": 0.0,
            "note": (
                f"no silence at all was detected at {silence_db:.0f} dB. Every cut boundary will be placed by "
                'arithmetic rather than in a real breath. Try silence_db="auto", and expect to verify each join '
                "by listening."
            ),
        }
    return {
        "verdict": "plausible",
        "detected_silence_ratio": round(ratio, 3),
        "note": (
            f"{len(pauses)} pause(s) totalling {silence_seconds:.1f}s, consistent with the {non_speech:.1f}s the "
            "transcript leaves outside speech. Boundaries should find real breaths to snap to."
        ),
    }


def _trim_candidates(records: list[dict[str, Any]], limit: int = 14) -> list[dict[str, Any]]:
    """Units whose removal is cheapest in meaning per second gained.

    Deliberately not a keep-list: it is the reading order for the editorial pass.
    A speaker's loops and stalls are the parts a linear read is worst at noticing
    and the parts a viewer misses least, so surfacing them by measured duration
    saves the model from rediscovering them one sentence at a time.
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    for record in records:
        reasons: list[str] = []
        weight = 0.0
        if record.get("near_duplicate_of"):
            reasons.append(f"restates {record['near_duplicate_of']} (similarity {record.get('similarity')})")
            weight += 3.0
        filler_ratio = (record["removable_disfluency_seconds"] + record["soft_filler_seconds"]) / max(1e-6, record["duration"])
        if filler_ratio >= 0.25:
            reasons.append(f"{filler_ratio * 100:.0f}% of it is filler/hesitation")
            weight += 2.0 * filler_ratio
        if record["chars"] <= 6 and record["duration"] >= 0.8:
            reasons.append("almost no content for its length")
            weight += 1.2
        if record["cps"] and record["cps"] < 2.5 and record["duration"] >= 2.0:
            reasons.append(f"very slow ({record['cps']:.1f} chars/s) — dead air inside the sentence")
            weight += 1.0
        if not reasons:
            continue
        scored.append((weight * record["duration"], {
            "id": record["id"],
            "seconds": record["duration"],
            "text": _preview(record["text"], 60),
            "reasons": reasons,
        }))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def _visual_check_list(records: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    """Timestamps the transcript itself says are worth looking at.

    This is the cheap alternative to a dense visual sweep, and the reason the
    sweep is not needed. A unit that says "watch this" or "看这里" is telling you
    that its meaning lives in the picture, not the words — so those are the only
    places a targeted look pays for itself. Batch them into ONE low-fps
    video_watch_segment call rather than sampling the whole recording.
    """
    picked = [
        {
            "unit": r["id"],
            "start": r["start"],
            "end": r["end"],
            "phrases": r["visual_reference"],
            "text": _preview(r["text"], 60),
        }
        for r in records if r.get("visual_reference")
    ]
    return picked[:limit]


def _unit_flags(record: dict[str, Any]) -> str:
    flags = []
    if record.get("near_duplicate_of"):
        flags.append("D")
    if record["disfluency"]["hard"] or record["disfluency"]["stutter"]:
        flags.append("F")
    if record["disfluency"]["soft"]:
        flags.append("s")
    if record["is_question"]:
        flags.append("Q")
    if record["opens_with_connective"]:
        flags.append("C")
    if record["anaphora"]:
        flags.append("A")
    if record["enum_first"]:
        flags.append("1")
    if record["enum_later"]:
        flags.append("2")
    if not record["has_terminal_punct"]:
        flags.append("!")
    if record.get("visual_reference"):
        flags.append("V")
    if record["duration"] < DEFAULT_MIN_CLIP:
        flags.append("x")
    if record["timing_source"] != "word_timestamps":
        flags.append("~")
    return "".join(flags) or "-"


_FLAG_LEGEND = (
    "flags: D=near-verbatim restatement of an earlier unit  F=hesitation/stutter inside  "
    "s=soft filler (your call)  Q=question  C=opens with a backward-pointing connective  "
    "A=contains a reference to something earlier  1/2=enumeration opener/continuation  "
    "!=no sentence-final punctuation (probably a run-on; cutting at its end lands mid-thought)  "
    "V=points at something on screen (\"like this\", \"看这里\"), so the words alone do not carry it: dropping the "
    "unit discards whatever was shown, and keeping it needs the frame checked  "
    f"x=shorter than min_clip ({DEFAULT_MIN_CLIP:.2f}s), so keeping it alone would be dropped — an "
    "interjection or crowd noise, not a decision worth spending  "
    "~=timing interpolated, not measured"
)


def _unit_row(record: dict[str, Any]) -> str:
    return (
        f"{record['id']}  {record['start']:>8.2f}  {record['duration']:>5.2f}  "
        f"{record['lead_gap']:>4.2f}  {str(record.get('speaker') or '-'):<4}  "
        f"{_unit_flags(record):<7}  {record['text']}"
    )


def _unit_table_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Speech index — {Path(report['video_path']).name}",
        "",
        f"- source duration: {_fmt(report['source_duration'])} ({report['source_duration']:.1f}s)",
        f"- units: {report['segmentation']['unit_count']} (from {report['segmentation']['asr_segment_count']} ASR segments)",
        f"- language: {report['language']}  timing: {report['timing_source']}",
        f"- lossless floor: {_fmt(report['budget']['lossless_floor_seconds'])} "
        f"({report['budget']['lossless_floor_ratio']:.0%} of source)",
        "",
        _FLAG_LEGEND,
        "",
        "```",
        "id      start      dur   gap  spk   flags    text",
    ]
    lines += [_unit_row(r) for r in report["units"]]
    lines += ["```", ""]
    return "\n".join(lines)


def _index_text(report: dict[str, Any], table_rows: int, table_path: str) -> str:
    totals = report["totals"]
    budget = report["budget"]
    units = report["units"]
    shown = units[:table_rows]
    table = "\n".join(_unit_row(r) for r in shown)
    truncated = (
        f"\n… {len(units) - len(shown)} more unit(s) not shown. Read {table_path} for the full table "
        "before deciding what to keep — a keep-list built from a truncated view drops the tail of the video."
        if len(shown) < len(units) else ""
    )
    dup_note = (
        f"{totals['near_duplicate_seconds']:.1f}s sits in units that restate an earlier one"
        if totals["near_duplicate_seconds"] > 0.5 else "no near-duplicate units detected"
    )
    timing_note = (
        "Word-level timestamps are present, so cut points can land between words."
        if report["timing_source"] == "word_timestamps" else
        "No word-level timestamps (this transcript is segment-timed only), so every cut time inside a unit is "
        "INTERPOLATED. Boundaries will be snapped to detected silences, but filler excision is unsafe and each "
        "cut needs a listening check. Re-run speech_transcribe(provider=\"cloud_asr\") if you need word timing."
    )
    candidates = report["trim_candidates"]
    cand_text = "\n".join(
        f"  {c['id']}  {c['seconds']:>5.2f}s  {'; '.join(c['reasons'])}\n         “{c['text']}”"
        for c in candidates[:8]
    ) or "  (none — this recording has little mechanical fat; savings have to come from editorial choices)"
    targets = budget["suggested_targets"]
    target_text = "  ".join(
        f"{name} {_fmt(spec['seconds'])}"
        + (f" (needs {spec['content_seconds_to_drop']:.0f}s of content dropped)" if spec["needs_content_dropped"] else " (pauses alone get you there)")
        for name, spec in targets.items()
    )
    pause_check = report["audio"]["pause_detection"]
    pause_line = (
        f"Pause detection: {pause_check['verdict']} — {pause_check['note']}"
    )
    survey = report.get("visual_survey") or {}
    if survey.get("performed"):
        visual_line = (
            f"PICTURE (coarse survey — {survey['frame_count']} thumbnail(s) for the whole recording, "
            f"{survey['frames_per_minute']:.2f} frames/min; budget {survey['frame_budget']} "
            f"({survey['frame_budget_basis']}) — it scales with the number of distinct framings, NOT with "
            f"duration):\n"
            f"  {survey['shot_cut_count']} shot cut(s) detected. Frame-to-frame motion: {survey['motion']} "
            f"(median adjacent-frame difference {survey['motion_baseline']}).\n"
            f"  {survey['note']}\n"
            "  The thumbnail sheet follows as an image. It is here to settle two things and no more: how many "
            "framings you have to reconcile (which decides the join treatment) and whether the source carries "
            "burned-in captions, a lower third, or a logo — anything like that jumps mid-sentence at every cut you "
            "make, and it is a defect a viewer notices even when the picture itself matches. Read the sheet for that; "
            "it is not measured. Do NOT run a dense video_ingest on top of this "
            "— it costs orders of magnitude more and answers a question this pipeline does not ask."
        )
    else:
        visual_line = (
            f"PICTURE: no visual survey ({survey.get('reason') or 'not run'}). You have no basis for the join "
            "treatment or for spotting burned-in captions; re-run with visual_survey=true."
        )
    checks = report.get("visual_check_timestamps") or []
    if checks:
        check_lines = "\n".join(
            f"  {c['unit']}  {c['start']:>7.2f}-{c['end']:<7.2f}  [{', '.join(c['phrases'][:2])}]  “{c['text']}”"
            for c in checks
        )
        visual_line += (
            f"\n\nWHERE THE TEXT SAYS TO LOOK ({len(checks)} unit(s) flagged V) — these point at something on "
            "screen, so the words alone do not carry them: dropping such a unit discards whatever was being shown, "
            "and keeping it means the frame has to still make sense after the cut. Batch these into ONE low-fps "
            f"video_watch_segment call; do not sweep the whole video.\n{check_lines}"
        )
    runs = report.get("topic_runs") or []
    runs_text = "\n".join(
        f"  “{r['keyword']}” — {r['hit_count']} unit(s) across {r['span'][0]}–{r['span'][1]}, "
        f"{r['span_seconds']:.1f}s total"
        for r in runs[:6]
    ) or "  (none — no term dominates a stretch of this recording)"

    return (
        f"Indexed {totals['unit_count']} speech unit(s) across {_fmt(report['source_duration'])} "
        f"({report['source_duration']:.1f}s), language {report['language']}, "
        f"{totals['speaker_count']} speaker(s).\n"
        f"Time accounting: {totals['speech_seconds']:.1f}s speech, {totals['gap_seconds']:.1f}s non-speech "
        f"({totals['inter_unit_gap_seconds']:.1f}s between units, {totals['head_tail_seconds']:.1f}s head/tail). "
        f"{totals['removable_disfluency_seconds']:.1f}s of hesitation sounds and stutters, "
        f"{totals['soft_filler_seconds']:.1f}s of soft fillers (context-dependent — your call), and {dup_note}.\n"
        f"Audio: mean {report['audio']['mean_volume_db']} dB, silence threshold {report['audio']['silence_db']} dB "
        f"({report['audio']['silence_db_reason']}), {report['audio']['pause_count']} pause(s) detected.\n"
        f"{pause_line}\n"
        f"{timing_note}\n\n"
        f"{visual_line}\n\n"
        f"BUDGET. {budget['note']}\n"
        f"Suggested targets: {target_text}\n\n"
        f"CHEAPEST CUTS FIRST (mechanical fat, not an editorial verdict):\n{cand_text}\n\n"
        f"TOPIC RUNS — stretches where one term keeps coming back. Near-verbatim repetition is caught by the D flag; "
        f"this catches the commoner case, where the speaker paraphrases the same point across several sentences. It "
        f"is a question, not a verdict: check whether the run needs all of its length.\n{runs_text}\n\n"
        f"{_FLAG_LEGEND}\n"
        f"Full table also written to {table_path}.\n"
        "```\n"
        "id      start      dur   gap  spk   flags    text\n"
        f"{table}\n"
        "```"
        f"{truncated}\n\n"
        "Next: write out/condense_brief.md (target, what counts as essential for THIS piece, checkpoints), then "
        "call condense_plan with the keep-list. Keep runs of consecutive units together where you can — "
        "consecutive units produce no cut at all, which is the most natural join there is."
    )


# --- keep-list parsing ----------------------------------------------------

_ID_RANGE = re.compile(r"^\s*(u\d+)\s*(?:-|–|—|\.\.|to)\s*(u\d+)\s*$", re.IGNORECASE)
_ID_ONE = re.compile(r"^\s*(u\d+)\s*$", re.IGNORECASE)


def _parse_keep(keep: object, by_id: dict[str, dict[str, Any]], units: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Resolve a keep-list into ordered source intervals.

    Accepts what a model naturally writes: `"u003"`, `"u003-u009"` for a run, or
    an explicit `{"start": …, "end": …}` when the boundary is not a unit edge.
    Ranges matter more than convenience — a run of consecutive units becomes one
    uncut clip, so making runs easy to express makes the natural edit the easy
    one to ask for.
    """
    if not isinstance(keep, list) or not keep:
        return [], ["keep must be a non-empty array of unit ids ('u007'), id ranges ('u007-u012'), or {start, end} objects"]
    intervals: list[dict[str, Any]] = []
    errors: list[str] = []
    for entry in keep:
        if isinstance(entry, str):
            match = _ID_RANGE.match(entry)
            if match:
                lo, hi = match.group(1).lower(), match.group(2).lower()
                if lo not in by_id or hi not in by_id:
                    errors.append(f"unknown unit id in range '{entry}'")
                    continue
                lo_i, hi_i = by_id[lo]["index"], by_id[hi]["index"]
                if hi_i < lo_i:
                    errors.append(f"range '{entry}' runs backwards")
                    continue
                intervals.append({"unit_indices": list(range(lo_i, hi_i + 1)), "source": entry})
                continue
            match = _ID_ONE.match(entry)
            if match:
                uid = match.group(1).lower()
                if uid not in by_id:
                    errors.append(f"unknown unit id '{entry}'")
                    continue
                intervals.append({"unit_indices": [by_id[uid]["index"]], "source": entry})
                continue
            errors.append(f"could not parse keep entry '{entry}'")
            continue
        if isinstance(entry, dict):
            if entry.get("unit"):
                uid = str(entry["unit"]).lower()
                if uid not in by_id:
                    errors.append(f"unknown unit id '{entry['unit']}'")
                    continue
                intervals.append({"unit_indices": [by_id[uid]["index"]], "source": uid})
                continue
            start = _number(entry.get("start"), float("nan"))
            end = _number(entry.get("end"), float("nan"))
            if not (math.isfinite(start) and math.isfinite(end)) or end <= start:
                errors.append(f"raw keep entry needs finite start < end: {entry}")
                continue
            covered = [u["index"] for u in units if u["end"] > start and u["start"] < end]
            intervals.append({"unit_indices": covered, "raw": (start, end), "source": f"{start:.2f}-{end:.2f}s"})
            continue
        errors.append(f"keep entries must be strings or objects, got {type(entry).__name__}")
    return intervals, errors


def _resolve_spans(
    intervals: list[dict[str, Any]],
    units: list[dict[str, Any]],
    drop_ids: set[str],
) -> list[dict[str, Any]]:
    """Collapse the keep-list into source-contiguous spans of kept units."""
    kept: set[int] = set()
    raw_ranges: list[tuple[float, float]] = []
    for interval in intervals:
        if interval.get("raw"):
            raw_ranges.append(interval["raw"])
        for index in interval["unit_indices"]:
            kept.add(index)
    kept = {i for i in kept if units[i]["id"] not in drop_ids}

    spans: list[dict[str, Any]] = []
    for index in sorted(kept):
        if spans and index == spans[-1]["unit_indices"][-1] + 1:
            spans[-1]["unit_indices"].append(index)
            continue
        spans.append({"unit_indices": [index]})
    for span in spans:
        first = units[span["unit_indices"][0]]
        last = units[span["unit_indices"][-1]]
        span["start"] = first["start"]
        span["end"] = last["end"]
        # An explicit {start,end} entry may narrow a unit's own boundaries; honour
        # the tighter of the two so a hand-picked in/out point is not widened
        # back out to the whole sentence.
        for lo, hi in raw_ranges:
            if lo <= span["start"] and hi >= span["end"]:
                continue
            if hi > span["start"] and lo < span["end"]:
                span["start"] = max(span["start"], min(lo, span["start"])) if lo <= span["start"] else max(span["start"], lo)
                span["end"] = min(span["end"], hi) if hi < span["end"] else span["end"]
    return [s for s in spans if s["end"] > s["start"]]


# --- condense_plan --------------------------------------------------------

def condense_plan(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    index_path = ctx.resolve(args.get("index_path") or "out/speech_index.json")
    if not index_path.is_file():
        return ToolResult(text=f"[ERROR] speech index not found: {index_path}. Run condense_index first.")
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read speech index: {exc}")
    units = index.get("units")
    if not isinstance(units, list) or not units:
        return ToolResult(text="[ERROR] speech index has no units[]")

    video_path = ctx.resolve(args.get("video_path") or index.get("video_path") or "")
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")
    if file_sha256(video_path) != index.get("video_sha256"):
        return ToolResult(
            text="[ERROR] the video no longer matches the speech index (different file content). "
            "Re-run condense_index on the current video — every unit time in the index would otherwise be wrong."
        )
    source_duration = _number(index.get("source_duration"), 0.0) or media_duration_seconds(video_path) or 0.0

    by_id = {u["id"].lower(): u for u in units}
    drop_ids = {str(d).lower() for d in (args.get("drop") or []) if isinstance(d, str)}
    unknown_drops = sorted(drop_ids - set(by_id))
    if unknown_drops:
        return ToolResult(text=f"[ERROR] unknown unit id(s) in drop: {', '.join(unknown_drops)}")
    intervals, keep_errors = _parse_keep(args.get("keep"), by_id, units)
    if keep_errors:
        return ToolResult(text="[ERROR] " + "; ".join(keep_errors))

    tighten = _bool(args.get("tighten_pauses"), True)
    if tighten is None:
        return ToolResult(text="[ERROR] tighten_pauses must be a boolean")
    max_gap = _positive(args.get("max_gap"), DEFAULT_MAX_GAP)
    lead_in = max(0.0, _number(args.get("lead_in"), DEFAULT_LEAD_IN))
    lead_out = max(0.0, _number(args.get("lead_out"), DEFAULT_LEAD_OUT))
    min_clip = _positive(args.get("min_clip"), DEFAULT_MIN_CLIP)
    snap_window = _positive(args.get("snap_window"), DEFAULT_SNAP_WINDOW)
    fillers_mode, filler_error = _resolve_filler_mode(args.get("drop_fillers"), index)
    if filler_error:
        return ToolResult(text=f"[ERROR] {filler_error}")

    min_silence = _positive(args.get("min_silence_seconds"), _number(index.get("audio", {}).get("min_silence_seconds"), DEFAULT_MIN_SILENCE))
    silence_db_arg = args.get("silence_db")
    if silence_db_arg is None:
        silence_db = _number(index.get("audio", {}).get("silence_db"), -32.0)
        silence_reason = "inherited from speech index"
    else:
        silence_db, silence_reason = resolve_silence_db(silence_db_arg, measure_loudness(video_path))
    pauses = detect_pauses(video_path, silence_db=silence_db, min_silence=min_silence)

    spans = _resolve_spans(intervals, units, drop_ids)
    if not spans:
        return ToolResult(text="[ERROR] the keep-list resolved to no usable spans (empty after drop, or zero-length)")

    raw_clips, removed = _split_spans(spans, units, tighten=bool(tighten), max_gap=max_gap, fillers_mode=fillers_mode)
    words = _all_words(units)
    clips, edge_notes = _apply_edges(
        raw_clips, pauses, words,
        lead_in=lead_in, lead_out=lead_out, snap_window=snap_window,
        duration=source_duration,
    )
    del edge_notes  # recomputed after merge-and-prune, where the clip list is final
    clips, short_dropped = _merge_and_prune(clips, min_clip=min_clip)
    if not clips:
        return ToolResult(
            text=f"[ERROR] every candidate clip was shorter than min_clip={min_clip:.2f}s. "
            "Keep longer runs of units, or lower min_clip if you really want micro-cuts."
        )
    edge_notes = _recount_edges(clips)

    joins = _build_joins(clips, units, words, pauses, snap_window=snap_window, index=index)
    output_duration = sum(c["duration"] for c in clips)
    target = _target_verdict(args, source_duration, output_duration, index)

    plan = {
        "status": "ok",
        "video_path": str(video_path),
        "video_sha256": index.get("video_sha256"),
        "index_path": str(index_path),
        "index_sha256": file_sha256(index_path),
        "language": index.get("language"),
        "timing_source": index.get("timing_source"),
        "source_duration": round(source_duration, 3),
        "output_duration": round(output_duration, 3),
        "compression_ratio": round(output_duration / source_duration, 4) if source_duration else None,
        "target": target,
        "options": {
            "tighten_pauses": bool(tighten),
            "max_gap": max_gap,
            "lead_in": lead_in,
            "lead_out": lead_out,
            "min_clip": min_clip,
            "snap_window": snap_window,
            "drop_fillers": fillers_mode,
            "silence_db": silence_db,
            "silence_db_reason": silence_reason,
            "min_silence_seconds": min_silence,
        },
        "clips": clips,
        "joins": joins,
        "removed": removed | {
            "short_clips_dropped": short_dropped,
            "kept_unit_count": sum(len(c["unit_ids"]) for c in clips),
            "dropped_unit_count": len(units) - len({uid for c in clips for uid in c["unit_ids"]}),
        },
        "edge_notes": edge_notes,
        "flag_counts": _flag_counts(joins),
        "next_moves": _next_moves(clips, units, index, target),
        "elapsed_seconds": round(time.time() - started, 3),
    }

    output_json = ctx.resolve(args.get("output_json") or "out/condense_plan.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    timeline_path = ctx.resolve(args.get("timeline_json") or "out/condense_timeline.json")
    timeline_path.write_text(json.dumps(_as_timeline(plan, video_path, ctx), ensure_ascii=False, indent=2), encoding="utf-8")

    script_path = ctx.resolve(args.get("script_md") or "out/condense_script.md")
    script_path.write_text(_script_markdown(plan, units), encoding="utf-8")

    transcript_path = ctx.resolve(args.get("output_transcript") or "out/condensed_transcript.json")
    transcript_path.write_text(json.dumps(_remapped_transcript(plan, units, index), ensure_ascii=False, indent=2), encoding="utf-8")

    redline_path = ctx.resolve(args.get("redline_json") or "out/condense_redline.json")
    redline_path.write_text(json.dumps(build_redline(plan, units), ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        text=_plan_text(plan, ctx.virtualize(script_path), ctx.virtualize(output_json)),
        data={k: v for k, v in plan.items() if k not in {"clips", "joins"}} | {
            "clip_count": len(clips),
            "join_count": len(joins),
        },
        artifacts=[str(output_json), str(timeline_path), str(script_path), str(transcript_path), str(redline_path)],
    )


def build_redline(plan: dict[str, Any], units: list[dict[str, Any]]) -> dict[str, Any]:
    """The whole source transcript, in order, marked kept vs dropped, with the
    silence tightened at each in-run join called out inline.

    This is the validation view: read the entire talk top to bottom and see
    exactly what survived and what did not, so nobody has to scrub the video.
    Every second of the source is accounted for — dropped speech, tightened
    pauses, and the head/tail trim — so the numbers reconcile against
    source-minus-output instead of looking like less was cut than really was.
    Structured (not HTML) so the viewer can render it inline in one page.
    """
    kept_ids = {uid for c in plan["clips"] for uid in c["unit_ids"]}
    # A tightened pause lives between the outgoing and incoming unit of a
    # `pause`-kind join; index the removed seconds by the unit it follows.
    tighten_after: dict[str, float] = {}
    for join in plan.get("joins", []):
        if join.get("kind") == "pause" and join.get("outgoing_unit"):
            tighten_after[join["outgoing_unit"]] = tighten_after.get(join["outgoing_unit"], 0.0) + float(join.get("removed_seconds") or 0.0)

    entries: list[dict[str, Any]] = []
    for unit in units:
        entries.append({
            "type": "unit",
            "id": unit["id"],
            "start": round(unit["start"], 2),
            "end": round(unit["end"], 2),
            "speaker": unit.get("speaker"),
            "text": unit["text"],
            "status": "kept" if unit["id"] in kept_ids else "dropped",
        })
        if unit["id"] in tighten_after and tighten_after[unit["id"]] >= 0.15:
            entries.append({"type": "tighten", "seconds": round(tighten_after[unit["id"]], 2)})

    dropped = [u for u in units if u["id"] not in kept_ids]
    src = float(plan.get("source_duration") or 0.0)
    out = float(plan.get("output_duration") or 0.0)
    dropped_speech = sum(u["end"] - u["start"] for u in dropped)
    tighten_total = sum(tighten_after.values())
    return {
        "source_duration": round(src, 2),
        "output_duration": round(out, 2),
        "removed_total": round(src - out, 2),
        "unit_count": len(units),
        "kept_units": len(kept_ids),
        "dropped_units": len(dropped),
        "dropped_speech_seconds": round(dropped_speech, 2),
        "dropped_chars": sum(u["chars"] for u in dropped),
        "kept_chars": sum(u["chars"] for u in units if u["id"] in kept_ids),
        "tightened_pause_seconds": round(tighten_total, 2),
        "head_tail_and_margin_seconds": round(max(0.0, (src - out) - dropped_speech - tighten_total), 2),
        "entries": entries,
    }


def _resolve_filler_mode(value: object, index: dict[str, Any]) -> tuple[str, str | None]:
    """Filler excision is only safe on measured word times.

    An interpolated span boundary can be tens of milliseconds off, and excising
    on an off-by-50ms boundary clips the consonant of the neighbouring word — an
    artefact far more noticeable than the filler it removed. So the unsafe
    combination is refused rather than warned about.
    """
    if value is None or value is False:
        return "off", None
    mode = "hard" if value is True else str(value).strip().lower()
    if mode in {"off", "none", "false"}:
        return "off", None
    if mode not in {"hard", "aggressive"}:
        return "off", f"drop_fillers must be false, 'hard', or 'aggressive' (got {value!r})"
    if index.get("timing_source") != "word_timestamps":
        return "off", (
            "drop_fillers needs word-level timestamps, but this transcript is segment-timed "
            f"(timing_source={index.get('timing_source')!r}). Interpolated filler boundaries clip the "
            "neighbouring word's consonant, which is more audible than the filler. Re-run "
            'speech_transcribe(provider="cloud_asr") for word times, or leave drop_fillers off and drop whole units instead.'
        )
    return mode, None


def _split_spans(
    spans: list[dict[str, Any]],
    units: list[dict[str, Any]],
    *,
    tighten: bool,
    max_gap: float,
    fillers_mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Break each kept span wherever time is being removed from *inside* it.

    Two kinds of internal removal: a pause longer than `max_gap` (dead air the
    viewer does not need) and a filler span. Both turn one span into several
    clips. Everything else stays whole — a run of consecutive units is emitted as
    a single clip precisely because an uncut clip cannot have a bad join.
    """
    excisions: list[dict[str, Any]] = []
    for span in spans:
        for index in span["unit_indices"]:
            unit = units[index]
            if fillers_mode == "off":
                continue
            spans_to_cut = list(unit["disfluency"]["hard"]) + list(unit["disfluency"]["stutter"])
            if fillers_mode == "aggressive":
                spans_to_cut += [s for s in unit["disfluency"]["soft"] if s.get("standalone_hint")]
            for cut in spans_to_cut:
                start = _number(cut.get("start"), float("nan"))
                end = _number(cut.get("end"), float("nan"))
                if not (math.isfinite(start) and math.isfinite(end)) or end - start < 0.06:
                    # Sub-60ms excisions are below the length at which removing
                    # audio is audible as anything but a click.
                    continue
                excisions.append({
                    "start": start, "end": end, "unit": unit["id"],
                    "phrase": cut.get("phrase"), "kind": "filler",
                })

    clips: list[dict[str, Any]] = []
    pause_removed = 0.0
    for span in spans:
        cuts: list[tuple[float, float, str]] = []
        if tighten:
            indices = span["unit_indices"]
            for prev, nxt in zip(indices, indices[1:]):
                gap_start = units[prev]["end"]
                gap_end = units[nxt]["start"]
                gap = gap_end - gap_start
                if gap <= max_gap:
                    continue
                # Keep half of `max_gap` on each side so the join still carries a
                # breath rather than butting two words together.
                keep = max_gap / 2.0
                cuts.append((gap_start + keep, gap_end - keep, "pause"))
                pause_removed += gap - max_gap
        for excision in excisions:
            if excision["start"] >= span["start"] and excision["end"] <= span["end"]:
                cuts.append((excision["start"], excision["end"], "filler"))
        cuts.sort()
        cursor = span["start"]
        for cut_start, cut_end, kind in cuts:
            if cut_start <= cursor:
                cursor = max(cursor, cut_end)
                continue
            clips.append({
                "start": cursor, "end": cut_start,
                "unit_ids": _units_in(units, span["unit_indices"], cursor, cut_start),
                "out_reason": kind,
            })
            cursor = cut_end
        if cursor < span["end"]:
            clips.append({
                "start": cursor, "end": span["end"],
                "unit_ids": _units_in(units, span["unit_indices"], cursor, span["end"]),
                "out_reason": "span_end",
            })
    clips = [c for c in clips if c["end"] > c["start"]]
    removed = {
        "pause_seconds": round(pause_removed, 3),
        "filler_count": sum(1 for e in excisions if e["kind"] == "filler"),
        "filler_seconds": round(sum(e["end"] - e["start"] for e in excisions), 3),
        "filler_phrases": [e["phrase"] for e in excisions][:40],
    }
    return clips, removed


def _units_in(units: list[dict[str, Any]], indices: list[int], start: float, end: float) -> list[str]:
    return [units[i]["id"] for i in indices if units[i]["end"] > start + 0.01 and units[i]["start"] < end - 0.01]


def _word_gap_limits(words: list[dict[str, Any]], moment: float) -> tuple[float, float]:
    """The nearest word edges bracketing `moment`.

    Returned as (latest word end at or before, earliest word start at or after),
    i.e. the silent corridor a boundary may move inside without entering a word.
    """
    lower = 0.0
    upper = float("inf")
    for word in words:
        if word["end"] <= moment + 1e-6:
            lower = max(lower, word["end"])
        if word["start"] >= moment - 1e-6:
            upper = min(upper, word["start"])
    return lower, upper


def _apply_edges(
    clips: list[dict[str, Any]],
    pauses: list[tuple[float, float]],
    words: list[dict[str, Any]],
    *,
    lead_in: float,
    lead_out: float,
    snap_window: float,
    duration: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Move each clip boundary outward into real silence, keeping a little breath.

    This is the difference between a cut that sounds edited and one that sounds
    broken. A boundary placed exactly at the first phoneme clips the attack; a
    boundary placed anywhere in the middle of speech is obviously spliced. So each
    edge looks for a detected silence it can expand into and takes at most
    `lead_in`/`lead_out` of it — capped, because expanding all the way into a
    three-second pause just puts the dead air back.

    `lead_out` is larger than `lead_in` by default: the tail of a sentence plus a
    beat of silence is what makes a cut read as "the thought finished", while a
    long run-up before the next sentence just feels slow.
    """
    out: list[dict[str, Any]] = []
    snapped_in = snapped_out = 0
    for clip in clips:
        raw_start, raw_end = clip["start"], clip["end"]
        pause_in = _pause_at(pauses, raw_start, snap_window)
        if pause_in is not None and pause_in[0] < raw_start:
            new_start = max(pause_in[0], raw_start - lead_in)
            snapped_in += 1
            in_kind = "snapped_to_silence"
        else:
            new_start = max(0.0, raw_start - lead_in * 0.5)
            in_kind = "no_silence_nearby"
        pause_out = _pause_at(pauses, raw_end, snap_window)
        if pause_out is not None and pause_out[1] > raw_end:
            new_end = min(pause_out[1], raw_end + lead_out)
            snapped_out += 1
            out_kind = "snapped_to_silence"
        else:
            new_end = raw_end + lead_out * 0.5
            out_kind = "no_silence_nearby"
        new_start = max(0.0, min(new_start, duration))
        new_end = max(new_start + 0.02, min(new_end, duration))
        # Never let the outward expansion enter a word. Snapping aims the boundary
        # at silence, but when no silence was found nearby the fallback still moved
        # it by half a lead — and half a lead is easily longer than the gap before
        # the next syllable, which puts the cut inside it. Clamping to the
        # bracketing word edges makes "cuts land between words" a property of the
        # plan rather than something QC merely complains about afterwards.
        if words:
            in_lower, _ = _word_gap_limits(words, raw_start)
            if new_start < in_lower:
                new_start = min(raw_start, in_lower)
                in_kind = "clamped_to_word_edge"
            _, out_upper = _word_gap_limits(words, raw_end)
            if math.isfinite(out_upper) and new_end > out_upper:
                new_end = max(raw_end, out_upper)
                out_kind = "clamped_to_word_edge"
            new_end = max(new_start + 0.02, new_end)
        out.append({
            **clip,
            "start": round(new_start, 3),
            "end": round(new_end, 3),
            "duration": round(new_end - new_start, 3),
            "speech_start": round(raw_start, 3),
            "speech_end": round(raw_end, 3),
            "in_edge": in_kind,
            "out_edge": out_kind,
        })
    notes = {
        "clips": len(out),
        "in_edges_snapped_to_silence": snapped_in,
        "out_edges_snapped_to_silence": snapped_out,
        "snap_ratio": round((snapped_in + snapped_out) / max(1, 2 * len(out)), 3),
    }
    return out, notes


def _recount_edges(clips: list[dict[str, Any]]) -> dict[str, Any]:
    """Edge statistics for the clips that actually survived.

    Counted after merge-and-prune, not before: merging removes a join entirely
    and pruning removes a clip, so the pre-merge counts can report more snapped
    edges than there are clips, which reads as a broken number and makes the
    snap ratio — the one figure that says how trustworthy the boundary times are
    — useless.
    """
    snapped_in = sum(1 for c in clips if c.get("in_edge") == "snapped_to_silence")
    snapped_out = sum(1 for c in clips if c.get("out_edge") == "snapped_to_silence")
    clamped = sum(1 for c in clips for key in ("in_edge", "out_edge") if c.get(key) == "clamped_to_word_edge")
    return {
        "clips": len(clips),
        "in_edges_snapped_to_silence": snapped_in,
        "out_edges_snapped_to_silence": snapped_out,
        "edges_clamped_to_word_edge": clamped,
        "snap_ratio": round((snapped_in + snapped_out) / max(1, 2 * len(clips)), 3),
    }


def _merge_and_prune(clips: list[dict[str, Any]], *, min_clip: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Merge edges that grew into each other; drop clips too short to read.

    Edge expansion can make two clips overlap or abut. Merging them is strictly
    better than keeping the join: it removes a cut entirely.
    """
    clips = sorted(clips, key=lambda c: c["start"])
    merged: list[dict[str, Any]] = []
    for clip in clips:
        if merged and clip["start"] <= merged[-1]["end"] + 0.02:
            prev = merged[-1]
            prev["end"] = max(prev["end"], clip["end"])
            prev["duration"] = round(prev["end"] - prev["start"], 3)
            prev["speech_end"] = max(prev.get("speech_end", prev["end"]), clip.get("speech_end", clip["end"]))
            prev["unit_ids"] = list(dict.fromkeys(prev["unit_ids"] + clip["unit_ids"]))
            prev["out_edge"] = clip["out_edge"]
            prev["out_reason"] = clip.get("out_reason")
            prev["merged_from"] = prev.get("merged_from", 1) + 1
            continue
        merged.append(dict(clip))
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for clip in merged:
        if clip["duration"] < min_clip:
            dropped.append({"start": clip["start"], "end": clip["end"], "duration": clip["duration"], "unit_ids": clip["unit_ids"]})
            continue
        kept.append(clip)
    for idx, clip in enumerate(kept):
        clip["index"] = idx
    return kept, dropped


# --- joins and continuity -------------------------------------------------

def _build_joins(
    clips: list[dict[str, Any]],
    units: list[dict[str, Any]],
    words: list[dict[str, Any]],
    pauses: list[tuple[float, float]],
    *,
    snap_window: float,
    index: dict[str, Any],
) -> list[dict[str, Any]]:
    """One record per cut, with everything that could be wrong about it.

    A join has two independent failure modes and they need different evidence.
    *Mechanically* it can clip a syllable or splice mid-speech — checkable from
    word times and detected silence. *Semantically* it can strand the sentence
    that follows: an answer without its question, a "但是" contradicting nothing,
    a pronoun whose referent was deleted. Those are the failures that survive a
    clean-sounding cut, so they are computed here rather than left to be noticed.
    """
    by_id = {u["id"]: u for u in units}
    language = index.get("language") or "zh"
    joins: list[dict[str, Any]] = []
    output_cursor = clips[0]["duration"] if clips else 0.0
    for left, right in zip(clips, clips[1:]):
        dropped_ids = [
            u["id"] for u in units
            if u["start"] >= left["end"] - 0.05 and u["end"] <= right["start"] + 0.05
            and u["id"] not in left["unit_ids"] and u["id"] not in right["unit_ids"]
        ]
        last_unit = by_id.get(left["unit_ids"][-1]) if left["unit_ids"] else None
        next_unit = by_id.get(right["unit_ids"][0]) if right["unit_ids"] else None
        # What kind of cut this is decides which checks even apply. A filler
        # excision is *deliberately* placed in speech, so testing it for "is
        # there silence here" is guaranteed to fail and would bury the content
        # cuts, where the same question is the one that matters.
        kind = {"filler": "filler", "pause": "pause"}.get(left.get("out_reason") or "", "content")
        if kind == "content" and not dropped_ids and right["start"] - left["end"] < 0.05:
            kind = "pause"
        flags = _continuity_flags(
            last_unit, next_unit, dropped_ids, by_id, units, language,
            left=left, right=right, words=words, pauses=pauses, snap_window=snap_window,
            kind=kind,
        )
        joins.append({
            "index": len(joins),
            "kind": kind,
            "output_time": round(output_cursor, 3),
            "source_out": left["end"],
            "source_in": right["start"],
            "removed_seconds": round(max(0.0, right["start"] - left["end"]), 3),
            "outgoing_unit": last_unit["id"] if last_unit else None,
            "incoming_unit": next_unit["id"] if next_unit else None,
            "outgoing_tail": _preview((last_unit or {}).get("text", "")[-24:], 26),
            "incoming_head": _preview((next_unit or {}).get("text", "")[:24], 26),
            "dropped_units": dropped_ids,
            "flags": flags,
        })
        output_cursor += right["duration"]
    return joins


def _continuity_flags(
    last_unit: dict[str, Any] | None,
    next_unit: dict[str, Any] | None,
    dropped_ids: list[str],
    by_id: dict[str, dict[str, Any]],
    units: list[dict[str, Any]],
    language: str,
    *,
    left: dict[str, Any],
    right: dict[str, Any],
    words: list[dict[str, Any]],
    pauses: list[tuple[float, float]],
    snap_window: float,
    kind: str = "content",
) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []

    def add(code: str, severity: str, message: str, hint: str) -> None:
        flags.append({"code": code, "severity": severity, "message": message, "hint": hint})

    # --- mechanical -------------------------------------------------------
    for edge, time_value, label in (("out", left["end"], "outgoing"), ("in", right["start"], "incoming")):
        word = _word_containing(words, time_value)
        if word is not None:
            add(
                "mid_word_cut", "error",
                f"the {label} boundary at {time_value:.3f}s falls inside the word “{word['text']}” "
                f"({word['start']:.3f}-{word['end']:.3f}s)",
                "Move the boundary to a unit edge, or widen snap_window so it can reach the nearest silence. "
                "A cut inside a syllable is audible on any playback.",
            )
    if kind == "content" and (left.get("out_edge") == "no_silence_nearby" or right.get("in_edge") == "no_silence_nearby"):
        add(
            "no_silence_at_cut", "warning",
            "no detected silence within snap_window of this cut, so the boundary time is derived rather than "
            "placed in a real breath",
            "Listen to this join specifically (condense_qc samples it), or raise snap_window / lower silence_db "
            "so pause detection finds the breath.",
        )
    if kind == "filler":
        # The excision is bounded by word timings, so the risk is not silence but
        # margin: if the removed span starts within a few milliseconds of the
        # previous word's end, the cut shaves that word's release.
        margin_out = min((left["end"] - w["end"] for w in words if w["end"] <= left["end"] + 1e-6), default=None)
        margin_in = min((w["start"] - right["start"] for w in words if w["start"] >= right["start"] - 1e-6), default=None)
        tight = [m for m in (margin_out, margin_in) if m is not None and m < 0.02]
        if tight:
            add(
                "tight_filler_excision", "warning",
                f"this filler excision sits within {min(tight) * 1000:.0f} ms of the neighbouring word, so it may "
                "shave that word's attack or release",
                "Leave this filler in (drop_fillers=false, or drop the whole unit instead). A clipped consonant is "
                "more audible than the filler it removed.",
            )

    # --- semantic ---------------------------------------------------------
    # Only content cuts can break meaning: a filler excision or a tightened pause
    # removes no words, so the sentence after it is the same sentence.
    if kind != "content":
        return flags
    if last_unit is not None and not last_unit.get("has_terminal_punct") and dropped_ids:
        add(
            "mid_thought_out", "warning",
            f"{last_unit['id']} has no sentence-final punctuation, so the cut probably lands mid-thought",
            "Extend the clip to include the rest of the sentence, or move the out-point to the previous unit "
            "that does end a sentence.",
        )
    if next_unit is not None and next_unit.get("opens_with_connective") and dropped_ids:
        add(
            "orphan_connective_in", "warning",
            f"{next_unit['id']} opens with “{next_unit['opens_with_connective']}”, which points back at material "
            "that is no longer there",
            "Either keep the unit it refers to, or start the clip after the connective by giving an explicit "
            "{start,end} keep entry that begins past it.",
        )
    if next_unit is not None and dropped_ids:
        # Only a reference at the HEAD of the unit points at the previous
        # sentence. 这个/那个/it/they are among the commonest words in speech, and
        # one buried mid-sentence almost always has a local antecedent inside the
        # same unit — flagging those fires on nearly every join and buries the
        # ones that matter.
        head = next_unit["text"][:14]
        head_refs = [a for a in (next_unit.get("anaphora") or []) if a in head]
        if head_refs:
            add(
                "broken_reference_in", "warning",
                f"{next_unit['id']} opens by referring back ({', '.join(head_refs[:3])}) while "
                f"{len(dropped_ids)} unit(s) before it were dropped — the referent may be gone",
                "Check what the reference points at. Keep the antecedent unit, or accept it if the referent is "
                "still on screen or obvious from context.",
            )
    if dropped_ids and next_unit is not None:
        # Only the LAST dropped unit can be the question this material answers,
        # and only if it is a substantial utterance. Firing on any question
        # anywhere in the gap flags self-directed stalls ("怎么说呢？") and
        # crowd heckles as orphaned questions.
        trailing = by_id.get(dropped_ids[-1])
        if (
            trailing is not None
            and trailing.get("is_question")
            and trailing.get("duration", 0.0) >= 0.6
            and trailing.get("chars", 0) >= 5
        ):
            add(
                "answer_without_question", "warning",
                f"the last dropped unit before this cut ({trailing['id']}, “{_preview(trailing['text'], 30)}”) is a "
                "question, so the material after the cut may now answer nothing",
                "Keep the question, or start the kept clip at a unit that restates what is being answered.",
            )
    if next_unit is not None and next_unit.get("enum_later") and not next_unit.get("enum_first"):
        # "第一天封神，第二天骨折" carries both halves of its own enumeration; it
        # needs no earlier opener.
        earlier_kept = _kept_before(units, next_unit, left, right)
        if not any(u.get("enum_first") for u in earlier_kept):
            add(
                "enumeration_gap", "warning",
                f"{next_unit['id']} continues an enumeration ({', '.join(next_unit['enum_later'][:2])}) but no "
                "kept unit before it opens one",
                "Keep the unit that introduces the list, or accept that the numbering will read oddly.",
            )
    if last_unit is not None and next_unit is not None:
        left_speaker = last_unit.get("speaker")
        right_speaker = next_unit.get("speaker")
        if left_speaker and right_speaker and left_speaker != right_speaker:
            add(
                "speaker_change", "info",
                f"this join switches speaker {left_speaker} → {right_speaker}",
                "Normal in an interview, but check the exchange still makes sense as a question/answer pair "
                "and that the cut is not mid-overlap.",
            )
    return flags


def _word_containing(words: list[dict[str, Any]], moment: float, margin: float = 0.02) -> dict[str, Any] | None:
    for word in words:
        if word["start"] + margin < moment < word["end"] - margin:
            return word
    return None


def _kept_before(
    units: list[dict[str, Any]],
    next_unit: dict[str, Any],
    left: dict[str, Any],
    right: dict[str, Any],
) -> list[dict[str, Any]]:
    limit = next_unit.get("index", 0)
    return [u for u in units if u.get("index", 0) < limit and u["end"] <= left["end"] + 0.05]


def _flag_counts(joins: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    severities = {"error": 0, "warning": 0, "info": 0}
    kinds: dict[str, int] = {}
    for join in joins:
        kinds[join.get("kind", "content")] = kinds.get(join.get("kind", "content"), 0) + 1
        for flag in join["flags"]:
            counts[flag["code"]] = counts.get(flag["code"], 0) + 1
            severities[flag["severity"]] = severities.get(flag["severity"], 0) + 1
    return {
        "by_code": counts,
        "by_severity": severities,
        "by_kind": kinds,
        "clean_joins": sum(1 for j in joins if not j["flags"]),
    }


# --- target and advice ----------------------------------------------------

def _target_verdict(args: dict, source: float, output: float, index: dict[str, Any]) -> dict[str, Any]:
    requested_seconds = args.get("target_duration")
    requested_ratio = args.get("target_ratio")
    target: float | None = None
    basis = "model's own judgement (no target given)"
    if requested_seconds is not None:
        target = _positive(requested_seconds, 0.0) or None
        basis = "caller-specified duration"
    elif requested_ratio is not None:
        ratio = _positive(requested_ratio, 0.0)
        if 0 < ratio <= 1.0:
            target = source * ratio
            basis = f"caller-specified ratio {ratio:.2f} of source"
        elif 1 < ratio <= 100:
            target = source * ratio / 100.0
            basis = f"caller-specified ratio {ratio:.0f}% of source"
    floor = _number((index.get("budget") or {}).get("lossless_floor_seconds"), 0.0)
    verdict: dict[str, Any] = {
        "basis": basis,
        "target_seconds": round(target, 2) if target else None,
        "achieved_seconds": round(output, 2),
        "achieved_ratio": round(output / source, 4) if source else None,
    }
    if target is None:
        verdict["verdict"] = "no_target"
        verdict["note"] = (
            f"No target was given, so {_fmt(output)} is your call. Say in the brief why this length is right for "
            "the material rather than leaving it implicit."
        )
        return verdict
    delta = output - target
    verdict["delta_seconds"] = round(delta, 2)
    tolerance = max(2.0, target * 0.08)
    if abs(delta) <= tolerance:
        verdict["verdict"] = "on_target"
        verdict["note"] = f"Within {tolerance:.1f}s of the {_fmt(target)} target."
    elif delta > 0:
        verdict["verdict"] = "too_long"
        verdict["note"] = f"{delta:.1f}s over the {_fmt(target)} target — drop more units, or accept and say why."
    else:
        verdict["verdict"] = "too_short"
        verdict["note"] = (
            f"{abs(delta):.1f}s under the {_fmt(target)} target. Under-cutting is a real failure too: it usually "
            "means whole sections went missing. Add back the units that carry the most content."
        )
    if target < floor - 0.5:
        verdict["below_lossless_floor"] = True
        verdict["note"] += (
            f" Note the target is below the lossless floor of {_fmt(floor)}, so it cannot be met by tightening "
            "pauses alone — it requires dropping content."
        )
    return verdict


def _next_moves(
    clips: list[dict[str, Any]],
    units: list[dict[str, Any]],
    index: dict[str, Any],
    target: dict[str, Any],
) -> dict[str, Any]:
    """Concrete candidates for the next iteration, in both directions."""
    kept_ids = {uid for c in clips for uid in c["unit_ids"]}
    by_id = {u["id"]: u for u in units}
    to_shorten = [
        {"id": c["id"], "seconds": c["seconds"], "reasons": c["reasons"]}
        for c in (index.get("trim_candidates") or []) if c["id"] in kept_ids
    ][:8]
    dropped = [u for u in units if u["id"] not in kept_ids]
    # Ranked by content density: characters per second, so what comes back is
    # substance rather than the next-longest pause.
    dropped.sort(key=lambda u: (u["chars"] / max(0.2, u["duration"])), reverse=True)
    to_lengthen = [
        {"id": u["id"], "seconds": u["duration"], "chars": u["chars"], "text": _preview(u["text"], 56)}
        for u in dropped[:8]
    ]
    return {
        "verdict": target.get("verdict"),
        "kept_units_worth_re_examining": to_shorten,
        "dropped_units_with_the_most_content": to_lengthen,
        "note": (
            "If the cut is too long, the entries above are the kept units with the least content per second. "
            "If it is too short, the dropped units with the most content per second are the cheapest to restore. "
            "Neither list is a verdict — read the text."
        ),
    }


# --- plan outputs ---------------------------------------------------------

def _as_timeline(plan: dict[str, Any], video_path: Path, ctx: RunContext) -> dict[str, Any]:
    """The plan as a standard timeline, so `validate_timeline` can check it.

    Written to `condense_timeline.json` rather than `timeline.json` on purpose:
    the editing contract keys on the latter, and a condense run should not be
    asked for a `preview.mp4` it never produces. The validation is still worth
    having — it independently confirms every clip sits inside the source and has
    a positive duration.
    """
    return {
        "version": "1.0",
        "task": (
            f"Condensed cut: {plan['source_duration']:.1f}s -> {plan['output_duration']:.1f}s "
            f"({(plan.get('compression_ratio') or 0) * 100:.0f}% of source) across {len(plan['clips'])} clip(s)."
        ),
        "clips": [
            {
                "source": ctx.virtualize(video_path),
                "start": clip["start"],
                "end": clip["end"],
                "reason": (
                    f"keep {', '.join(clip['unit_ids']) or 'raw range'}"
                    + (f"; in-edge {clip['in_edge']}, out-edge {clip['out_edge']}")
                ),
            }
            for clip in plan["clips"]
        ],
    }


def _script_markdown(plan: dict[str, Any], units: list[dict[str, Any]]) -> str:
    """The condensed talk as continuous prose, with every join marked.

    This is the artifact that catches the failure the numbers cannot: a cut where
    each boundary is clean and the result still does not make sense. Reading the
    kept text straight through, in order, with the removals annotated, is the
    cheapest possible coherence check and it is text, not frames.
    """
    by_id = {u["id"]: u for u in units}
    lines = [
        "# Condensed script (read this straight through for coherence)",
        "",
        f"- source {_fmt(plan['source_duration'])} → output {_fmt(plan['output_duration'])} "
        f"({(plan.get('compression_ratio') or 0) * 100:.0f}% of source)",
        f"- {len(plan['clips'])} clip(s), {len(plan['joins'])} join(s), "
        f"{plan['flag_counts']['clean_joins']} join(s) with no flags",
        f"- target: {plan['target'].get('verdict')} — {plan['target'].get('note')}",
        "",
        "If this reads as a person talking, the edit works. If a sentence answers nothing, contradicts nothing, "
        "or points at something that is gone, fix the keep-list — not the render.",
        "",
    ]
    output_cursor = 0.0
    for clip in plan["clips"]:
        lines.append(
            f"## Clip {clip['index'] + 1} — source {clip['start']:.2f}–{clip['end']:.2f}s "
            f"→ output {output_cursor:.2f}–{output_cursor + clip['duration']:.2f}s ({clip['duration']:.2f}s)"
        )
        lines.append("")
        for uid in clip["unit_ids"]:
            unit = by_id.get(uid)
            if unit:
                lines.append(f"{unit['text']}")
        if not clip["unit_ids"]:
            lines.append("_(raw time range with no whole unit inside)_")
        lines.append("")
        output_cursor += clip["duration"]
        join = next((j for j in plan["joins"] if j["index"] == clip["index"]), None)
        if join is None:
            continue
        dropped = join["dropped_units"]
        head = (
            f"**— cut {join['index'] + 1} @ output {join['output_time']:.2f}s: "
            f"removed {join['removed_seconds']:.2f}s"
            + (f", units {dropped[0]}–{dropped[-1]} ({len(dropped)})" if dropped else "")
            + " —**"
        )
        lines.append(head)
        for flag in join["flags"]:
            mark = {"error": "🛑", "warning": "⚠️", "info": "ℹ️"}.get(flag["severity"], "·")
            lines.append(f"  - {mark} `{flag['code']}` {flag['message']}")
        if dropped:
            removed_text = " ".join((by_id.get(d) or {}).get("text", "") for d in dropped)
            lines.append(f"  - removed text: {_preview(removed_text, 220)}")
        lines.append("")
    return "\n".join(lines)


def _remapped_transcript(plan: dict[str, Any], units: list[dict[str, Any]], index: dict[str, Any]) -> dict[str, Any]:
    """A transcript in *output* time, so a later subtitle pass needs no re-ASR.

    Subtitling the condensed cut with the source transcript would put every cue
    at the wrong time. Re-transcribing works but throws away the word-level times
    the original provider gave. Remapping keeps them: each kept interval is
    shifted by its clip's offset and clipped to the clip's bounds.
    """
    segments: list[dict[str, Any]] = []
    offset_cursor = 0.0
    for clip in plan["clips"]:
        offset = offset_cursor - clip["start"]
        for unit in units:
            lo = max(unit["start"], clip["start"])
            hi = min(unit["end"], clip["end"])
            if hi - lo < 0.05:
                continue
            words = [
                {"text": w["text"], "start": round(w["start"] + offset, 3), "end": round(w["end"] + offset, 3)}
                for w in (unit.get("words") or [])
                if w["end"] > clip["start"] and w["start"] < clip["end"]
            ]
            segments.append({
                "speaker": unit.get("speaker"),
                "text": unit["text"],
                "start": round(lo + offset, 3),
                "end": round(hi + offset, 3),
                "source_unit": unit["id"],
                "source_start": round(unit["start"], 3),
                "partial": (unit["start"] < clip["start"] - 0.05) or (unit["end"] > clip["end"] + 0.05),
                "words": words,
            })
        offset_cursor += clip["duration"]
    segments.sort(key=lambda s: s["start"])
    return {
        "provider": f"remapped_from:{index.get('transcript_path')}",
        "language": index.get("language"),
        "time_unit": "seconds",
        "note": (
            "Transcript remapped into the condensed output's timeline by condense_plan. Valid only for the exact "
            "render this plan produced; re-run condense_plan if the keep-list changes. Segment texts are the "
            "source units, so a unit split by a cut appears twice with partial=true — check those before "
            "subtitling on top of it."
        ),
        "source_transcript": index.get("transcript_path"),
        "n_segments": len(segments),
        "segments": segments,
    }


def _plan_text(plan: dict[str, Any], script_path: str, plan_path: str) -> str:
    clips = plan["clips"]
    joins = plan["joins"]
    counts = plan["flag_counts"]
    rows = [
        f"{c['index'] + 1:>3}  {c['start']:>8.2f} {c['end']:>8.2f}  {c['duration']:>6.2f}  "
        f"{(c['unit_ids'][0] + '–' + c['unit_ids'][-1]) if len(c['unit_ids']) > 1 else (c['unit_ids'][0] if c['unit_ids'] else 'raw'):<12}  "
        f"{c['in_edge'][:4]}/{c['out_edge'][:4]}"
        for c in clips[:60]
    ]
    clip_table = "\n".join(rows)
    if len(clips) > 60:
        clip_table += f"\n… {len(clips) - 60} more clip(s); read {plan_path}."

    flagged = [j for j in joins if j["flags"]]
    join_lines: list[str] = []
    for join in flagged[:20]:
        codes = ", ".join(f"{f['code']}({f['severity'][0]})" for f in join["flags"])
        join_lines.append(
            f"  cut {join['index'] + 1} @ out {join['output_time']:.2f}s "
            f"(src {join['source_out']:.2f}→{join['source_in']:.2f}, −{join['removed_seconds']:.1f}s): {codes}\n"
            f"      …{join['outgoing_tail']} ┃ {join['incoming_head']}…"
        )
        for flag in join["flags"]:
            join_lines.append(f"      {flag['severity']}: {flag['message']}\n        → {flag['hint']}")
    join_text = "\n".join(join_lines) or "  (no flagged joins)"
    if len(flagged) > 20:
        join_text += f"\n  … {len(flagged) - 20} more flagged join(s); read {plan_path}."

    errors = counts["by_severity"].get("error", 0)
    # Without word timings the mid-word check cannot run at all. Saying "0 errors"
    # in that case is the same silent-pass failure that hid nine real mid-word cuts
    # once already, so the absence of the check has to be as visible as its result.
    no_word_note = (
        ""
        if plan.get("timing_source") == "word_timestamps" else
        "\nNOTE: this transcript has no word-level timestamps, so the mid-word-cut check COULD NOT RUN. "
        "A clean error count here does not mean the boundaries avoid syllables — it means nothing was measured. "
        "Every cut needs a listening check, or re-run speech_transcribe(provider=\"cloud_asr\") for word timing and re-plan."
    )
    header = (
        f"[ERROR-LEVEL FLAGS: {errors}] " if errors else ""
    )
    kinds = counts.get("by_kind") or {}
    kind_text = ", ".join(
        f"{kinds.get(k, 0)} {label}"
        for k, label in (("content", "content cut(s)"), ("filler", "filler excision(s)"), ("pause", "pause tighten(s)"))
        if kinds.get(k)
    ) or "none"
    removed = plan["removed"]
    return (
        f"{header}Plan: {len(clips)} clip(s), {len(joins)} cut(s) — {kind_text}. "
        f"{_fmt(plan['source_duration'])} → {_fmt(plan['output_duration'])} "
        f"({(plan.get('compression_ratio') or 0) * 100:.0f}% of source).\n"
        f"Target: {plan['target']['verdict']} — {plan['target']['note']}\n"
        f"Removed: {removed['dropped_unit_count']} unit(s), {removed['pause_seconds']:.1f}s of over-long pauses, "
        f"{removed['filler_count']} filler span(s) ({removed['filler_seconds']:.1f}s)"
        + (f", {len(removed['short_clips_dropped'])} clip(s) below min_clip" if removed["short_clips_dropped"] else "")
        + ".\n"
        f"Boundary quality: {plan['edge_notes']['in_edges_snapped_to_silence']}/{len(clips)} in-edges and "
        f"{plan['edge_notes']['out_edges_snapped_to_silence']}/{len(clips)} out-edges landed in a detected silence "
        f"(snap ratio {plan['edge_notes']['snap_ratio']:.2f}). A low ratio means boundary times are derived, "
        f"not placed in a real breath — those joins need a listening check. Filler excisions are expected NOT to "
        f"snap; they are cut in speech by design.\n"
        f"Join flags: {counts['by_severity'].get('error', 0)} error, {counts['by_severity'].get('warning', 0)} warning, "
        f"{counts['by_severity'].get('info', 0)} info; {counts['clean_joins']}/{len(joins)} joins clean.{no_word_note}\n\n"
        f"CLIPS (source in/out, duration, units, edge treatment):\n"
        "```\n"
        "  #     start      end     dur  units         in/out\n"
        f"{clip_table}\n"
        "```\n\n"
        f"FLAGGED JOINS:\n{join_text}\n\n"
        f"Now read {script_path} straight through. It is the condensed talk as continuous prose with every removal "
        "annotated, and it is the only cheap way to catch a cut where each boundary is clean but the result no "
        "longer makes sense. Errors above are blocking: a cut inside a word will be audible. Fix the keep-list and "
        "re-plan, then condense_render, then condense_qc."
    )


# --- condense_render ------------------------------------------------------

DEFAULT_DISSOLVE = 0.16
MAX_DISSOLVE_CLIPS = 40


def condense_render(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    # Fail fast: condense dissolves clips with xfade; a build without it dies
    # deep into a long render.
    cap_err = require_ffmpeg(encoders=("libx264", "aac"), filters=("xfade",))
    if cap_err:
        return ToolResult(text=cap_err)
    plan_path = ctx.resolve(args.get("plan_path") or "out/condense_plan.json")
    if not plan_path.is_file():
        return ToolResult(text=f"[ERROR] plan not found: {plan_path}. Run condense_plan first.")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read plan: {exc}")
    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        return ToolResult(text="[ERROR] plan has no clips[]")

    video_path = ctx.resolve(args.get("video_path") or plan.get("video_path") or "")
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")
    if plan.get("video_sha256") and file_sha256(video_path) != plan["video_sha256"]:
        return ToolResult(
            text="[ERROR] the video no longer matches the one the plan was built on. Every clip time would be "
            "wrong. Re-run condense_index and condense_plan against the current file."
        )

    join_mode = str(args.get("join") or "hard").strip().lower()
    if join_mode not in {"hard", "dissolve"}:
        return ToolResult(text="[ERROR] join must be 'hard' or 'dissolve'")
    dissolve = _positive(args.get("dissolve_seconds"), DEFAULT_DISSOLVE)
    crf = int(_positive(args.get("crf"), 18))

    shortest = min(c["duration"] for c in clips)
    if join_mode == "dissolve":
        if len(clips) > MAX_DISSOLVE_CLIPS:
            return ToolResult(
                text=f"[ERROR] dissolve joins are built as one {len(clips)}-input xfade chain, which is beyond the "
                f"{MAX_DISSOLVE_CLIPS}-clip limit this tool will attempt. Use join='hard' for a cut with this many "
                "clips."
            )
        if shortest <= dissolve * 2:
            return ToolResult(
                text=f"[ERROR] shortest clip is {shortest:.2f}s but dissolve_seconds is {dissolve:.2f}s; a "
                "cross-dissolve needs clips at least twice its length. Lower dissolve_seconds, raise min_clip in "
                "condense_plan, or use join='hard'."
            )

    try:
        target_width, target_height = _resolve_canvas(args, video_path)
    except RuntimeError as exc:
        return ToolResult(text=f"[ERROR] {exc}")
    fps = _probe_fps(video_path)

    output_path = ctx.resolve(args.get("output_path") or "out/condensed.mp4")
    work_dir = ctx.resolve(args.get("work_dir") or f".video_agent/condense/{plan_path.stem}")
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    for stale in work_dir.glob("seg_*.mp4"):
        stale.unlink()

    segments: list[dict[str, Any]] = []
    for idx, clip in enumerate(clips):
        seg_path = work_dir / f"seg_{idx:04d}.mp4"
        error = _cut_segment(
            video_path, clip, seg_path,
            width=target_width, height=target_height, fps=fps, crf=crf,
        )
        if error:
            return ToolResult(
                text=f"[ERROR] ffmpeg failed cutting clip {idx + 1} ({clip['start']:.2f}-{clip['end']:.2f}s): {error}",
                data={"clip_index": idx, "clip": clip},
            )
        segments.append({
            "index": idx,
            "path": str(seg_path),
            "source_start": clip["start"],
            "source_end": clip["end"],
            "duration": clip["duration"],
        })

    if join_mode == "hard":
        error = _concat_hard(segments, output_path, crf=crf)
        expected = sum(s["duration"] for s in segments)
        join_times = _cumulative_joins(segments, overlap=0.0)
    else:
        error = _concat_dissolve(segments, output_path, dissolve=dissolve, crf=crf, fps=fps)
        expected = sum(s["duration"] for s in segments) - dissolve * (len(segments) - 1)
        join_times = _cumulative_joins(segments, overlap=dissolve)
    if error:
        return ToolResult(text=f"[ERROR] ffmpeg failed joining segments: {error}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        return ToolResult(text="[ERROR] render produced no output file")

    measured = media_duration_seconds(output_path)
    report = {
        "plan_path": str(plan_path),
        "plan_sha256": file_sha256(plan_path),
        "video_path": str(video_path),
        "output_path": str(output_path),
        "output_sha256": file_sha256(output_path),
        "join": join_mode,
        "dissolve_seconds": dissolve if join_mode == "dissolve" else 0.0,
        "output_width": target_width,
        "output_height": target_height,
        "fps": fps,
        "crf": crf,
        "clip_count": len(segments),
        "expected_duration": round(expected, 3),
        "measured_duration": round(measured, 3) if measured else None,
        "output_join_times": [round(t, 3) for t in join_times],
        "segments": segments,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    report_path = output_path.with_suffix(".render_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        text=(
            f"Rendered {ctx.virtualize(output_path)}: {len(segments)} clip(s), {join_mode} joins, "
            f"{target_width}x{target_height} @ {fps:g} fps.\n"
            f"Expected duration {expected:.2f}s, measured "
            f"{f'{measured:.2f}s' if measured else 'unknown'}.\n"
            "Joins are straight cuts, so each one is a visible jump if the speaker's pose differs across it. "
            "condense_qc samples frames either side of every join; read them to judge whether that is acceptable "
            "for this material, or keep longer consecutive runs (fewer cuts) if not.\n"
            "A successful encode proves the filter graph ran. It proves nothing about whether the cut sounds like a "
            f"person talking — run condense_qc(plan_path, video_path=\"{ctx.virtualize(output_path)}\") next and read "
            "the join evidence."
        ),
        data=report,
        artifacts=[str(output_path), str(report_path)],
        video_paths=[str(output_path)],
    )


def _resolve_canvas(args: dict, video_path: Path) -> tuple[int, int]:
    width_arg = args.get("output_width")
    height_arg = args.get("output_height")
    if width_arg is None and height_arg is None:
        from .render import probe_video_size

        return probe_video_size(video_path)
    if width_arg is None or height_arg is None:
        raise RuntimeError("output_width and output_height must be provided together")
    if isinstance(width_arg, bool) or isinstance(height_arg, bool):
        raise RuntimeError("output_width/output_height must be integers, not booleans")
    try:
        width, height = int(width_arg), int(height_arg)
    except Exception as exc:
        raise RuntimeError("output_width/output_height must be integers") from exc
    if width <= 0 or height <= 0:
        raise RuntimeError("output_width/output_height must be positive")
    return width - width % 2, height - height % 2


def _probe_fps(video_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(video_path),
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=30)
        num, _, den = (proc.stdout or "").strip().partition("/")
        value = float(num) / float(den or 1)
    except Exception:
        return 30.0
    return value if 1.0 <= value <= 240.0 else 30.0


def _cut_segment(
    video_path: Path,
    clip: dict[str, Any],
    output_path: Path,
    *,
    width: int,
    height: int,
    fps: float,
    crf: int,
) -> str | None:
    """One normalized segment, re-encoded so the joiner can rely on it.

    Every segment is forced to the same size, sar, pixel format and frame rate:
    the concat demuxer tolerates nothing else, and xfade misbehaves without it.
    The 8 ms audio declick at each end is not cosmetic — a raw splice at a
    non-zero sample value is an audible click even when the cut sits in silence.
    """
    duration = float(clip["end"]) - float(clip["start"])
    if duration <= 0:
        return f"invalid clip duration {duration}"
    from .render import source_has_audio

    has_audio = source_has_audio(video_path)
    filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=decrease",
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "setsar=1",
    ]
    filters.append("format=yuv420p")
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{float(clip['start']):.6f}", "-t", f"{duration:.6f}", "-i", str(video_path),
    ]
    if has_audio:
        cmd += ["-map", "0:v:0", "-map", "0:a:0"]
    else:
        cmd += [
            "-f", "lavfi", "-t", f"{duration:.6f}",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map", "0:v:0", "-map", "1:a:0",
        ]
    cmd += ["-vf", ",".join(filters), "-r", f"{fps:.6f}"]
    if has_audio:
        # 8 ms declick, not a 30 ms fade to silence. Measured: the old 30 ms fade
        # carved ~22 ms of extra room tone off each boundary for no benefit, so a
        # shorter declick is a strictly-better default that keeps pauses at their
        # natural floor. NB it does NOT fix an intrinsically-quiet join: where the
        # source itself decays to near-silence right at the cut (speaker ran two
        # sentences together and the breath fell in the removed span), the beat
        # before the incoming word stays quiet no matter the fade — that
        # abruptness is a property of the edit point, surfaced by QC's in_speech /
        # no_silence signals, not something a boundary fade can smooth.
        fade = 0.008
        cmd += ["-af", f"afade=t=in:st=0:d={fade},afade=t=out:st={max(0.0, duration - fade):.6f}:d={fade}"]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-shortest", "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=1800)
    except Exception as exc:
        return str(exc)
    return None if proc.returncode == 0 else (proc.stderr or "").strip()[-1200:]


def _concat_hard(segments: list[dict[str, Any]], output_path: Path, *, crf: int) -> str | None:
    concat_file = Path(segments[0]["path"]).parent / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{Path(s['path']).as_posix()}'\n" for s in segments),
        encoding="utf-8",
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "aac", "-movflags", "+faststart",
        str(output_path),
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=7200)
    except Exception as exc:
        return str(exc)
    return None if proc.returncode == 0 else (proc.stderr or "").strip()[-1500:]


def _concat_dissolve(
    segments: list[dict[str, Any]],
    output_path: Path,
    *,
    dissolve: float,
    crf: int,
    fps: float,
) -> str | None:
    """Chain xfade/acrossfade so each join is a short cross-dissolve.

    The offset arithmetic is the whole trick: each xfade consumes `dissolve`
    seconds of overlap, so the accumulated timeline shortens by that much at
    every join and the next offset must be computed from the *shortened*
    accumulator, not from the raw source durations.
    """
    cmd: list[str] = ["ffmpeg", "-y", "-v", "error"]
    for seg in segments:
        cmd += ["-i", seg["path"]]
    steps: list[str] = []
    v_label, a_label = "0:v", "0:a"
    accumulated = segments[0]["duration"]
    for idx in range(1, len(segments)):
        offset = accumulated - dissolve
        v_out, a_out = f"v{idx}", f"a{idx}"
        steps.append(
            f"[{v_label}][{idx}:v]xfade=transition=fade:duration={dissolve:.4f}:offset={offset:.4f}[{v_out}]"
        )
        steps.append(f"[{a_label}][{idx}:a]acrossfade=d={dissolve:.4f}:c1=tri:c2=tri[{a_out}]")
        v_label, a_label = v_out, a_out
        accumulated += segments[idx]["duration"] - dissolve
    cmd += [
        "-filter_complex", ";".join(steps),
        "-map", f"[{v_label}]", "-map", f"[{a_label}]",
        "-r", f"{fps:.6f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
        "-c:a", "aac", "-movflags", "+faststart",
        str(output_path),
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=7200)
    except Exception as exc:
        return str(exc)
    return None if proc.returncode == 0 else (proc.stderr or "").strip()[-1500:]


def _cumulative_joins(segments: list[dict[str, Any]], *, overlap: float) -> list[float]:
    times: list[float] = []
    cursor = 0.0
    for idx, seg in enumerate(segments):
        cursor += seg["duration"]
        if idx < len(segments) - 1:
            cursor -= overlap
            # For a dissolve the join is the midpoint of the overlap, which is
            # where the two shots are equally visible.
            times.append(cursor + overlap / 2.0 if overlap else cursor)
    return times


# --- condense_qc ----------------------------------------------------------

DEFAULT_EVIDENCE_JOINS = 8
# Bounds runtime on a pathological plan (each join costs two short ffmpeg reads
# for audio and four more for the jump ratio). Raised from 60 after a real
# 37-minute run produced 66 cuts and silently measured only the first 60 — a cap
# that hides what it dropped reads as "everything checked out".
MAX_MEASURED_JOINS = 120
CHOPPY_CUTS_PER_MINUTE = 20.0


def condense_qc(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")
    plan_path = ctx.resolve(args.get("plan_path") or "out/condense_plan.json")
    if not plan_path.is_file():
        return ToolResult(text=f"[ERROR] plan not found: {plan_path}")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read plan: {exc}")
    video_path = ctx.resolve(args.get("video_path") or "out/condensed.mp4")
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] condensed output not found: {video_path}. Run condense_render first.")

    render_report_path = ctx.resolve(args.get("render_report_path") or str(video_path.with_suffix(".render_report.json")))
    render_report = {}
    if render_report_path.is_file():
        try:
            render_report = json.loads(render_report_path.read_text(encoding="utf-8"))
        except Exception:
            render_report = {}

    issues: list[dict[str, Any]] = []

    def add(severity: str, message: str, **extra: Any) -> None:
        issues.append({"severity": severity, "message": message, **extra})

    if video_path.stat().st_size == 0:
        add("error", "output file is empty")
    if render_report and render_report.get("plan_sha256") not in (None, file_sha256(plan_path)):
        add(
            "error",
            "the render report was produced from a different plan than the one given here; re-render, or pass the "
            "render_report_path that matches this plan. QC against a mismatched pair proves nothing.",
        )

    expected = _number(render_report.get("expected_duration"), _number(plan.get("output_duration"), 0.0))
    measured = media_duration_seconds(video_path)
    if measured is None:
        add("error", "could not probe a valid duration for the condensed output")
    else:
        tolerance = max(0.35, expected * 0.02)
        if expected > 0 and abs(measured - expected) > tolerance:
            add(
                "error",
                f"output duration {measured:.2f}s differs from the planned {expected:.2f}s by "
                f"{abs(measured - expected):.2f}s (tolerance {tolerance:.2f}s). Something was dropped or repeated "
                "during the join — do not ship this until the two agree.",
                measured_duration=round(measured, 3), expected_duration=round(expected, 3),
            )

    from .render import source_has_audio

    has_audio = source_has_audio(video_path)
    if not has_audio:
        add("error", "the condensed output has no audio stream; a condensed talk without speech is not a deliverable")

    clips = plan.get("clips") or []
    plan_joins = plan.get("joins") or []
    join_times = [float(t) for t in (render_report.get("output_join_times") or [])]
    if not join_times:
        cursor = 0.0
        for clip in clips[:-1]:
            cursor += clip["duration"]
            join_times.append(cursor)

    # Correct for encoder-priming drift. Each concatenated segment carries a
    # small constant of AAC encoder-delay padding (~1024 samples = 21.3 ms at
    # 48 kHz), so the real output is a touch longer than planned and every join
    # sits progressively LATER than its planned time — on a 74-clip render the
    # last join drifts ~1.5 s. QC samples audio and frames at these times, so
    # uncorrected, the evidence for late joins lands mid-speech and a clean
    # word-boundary cut reads as `in_speech`. The drift is linear in the join
    # index (join i has i segments of padding before it), so distribute the
    # measured overshoot across the joins by index. Found by a model that had to
    # re-measure all 37 content cuts by hand to see the real 5 in_speech behind a
    # spurious 41.
    join_drift_per_index = 0.0
    if measured is not None and expected and join_times and abs(measured - expected) > 0.05:
        # measured - expected is the total padding across all n_clips segments;
        # join i (0-based) has (i+1) segments of padding accumulated before it.
        join_drift_per_index = (measured - expected) / max(1, len(clips))
        join_times = [t + join_drift_per_index * (i + 1) for i, t in enumerate(join_times)]

    min_clip = _number((plan.get("options") or {}).get("min_clip"), DEFAULT_MIN_CLIP)
    join_kinds = {j["index"]: j.get("kind", "content") for j in plan_joins}
    for clip in clips:
        if clip["duration"] < min_clip - 0.01:
            add(
                "error",
                f"clip {clip['index'] + 1} is {clip['duration']:.2f}s, below the plan's own min_clip "
                f"{min_clip:.2f}s — the plan and the render disagree",
                clip_index=clip["index"],
            )
    for clip in clips:
        if clip["duration"] < 0.9:
            add(
                "warning",
                f"clip {clip['index'] + 1} is only {clip['duration']:.2f}s; clips this short read as a stutter in "
                "the edit rather than as a sentence",
                clip_index=clip["index"],
            )
    if measured and measured > 0:
        cuts_per_minute = len(join_times) / (measured / 60.0)
        # Pace is about *perceptual* cuts. A tightened pause removes dead air
        # between two adjacent sentences of the same continuous take: nothing is
        # dropped, the picture barely changes (these measure ~1.0x on the jump
        # ratio), and a viewer does not register it as a cut. Counting them made
        # the headline pace 3x the felt pace on a real 37-minute run — 5.4/min
        # reported against 1.6/min of actual content cuts — which is both a
        # misleading number and a warning that would fire on a well-paced edit.
        perceptual = sum(1 for idx in range(len(join_times)) if join_kinds.get(idx, "content") != "pause")
        content_cuts_per_minute = perceptual / (measured / 60.0)
        if content_cuts_per_minute > CHOPPY_CUTS_PER_MINUTE:
            add(
                "warning",
                f"{content_cuts_per_minute:.1f} content cuts per minute of output ({perceptual} content cuts and "
                f"filler excisions in {measured:.1f}s; {len(join_times) - perceptual} tightened pauses are not "
                "counted, being imperceptible). Above roughly 20 the result reads as choppy regardless of how clean "
                "each individual cut is; consider keeping longer runs of consecutive units.",
                content_cuts_per_minute=round(content_cuts_per_minute, 2),
            )
    else:
        cuts_per_minute = None
        content_cuts_per_minute = None

    # Carry forward the plan's own blocking flags: a mid-word cut is still a
    # mid-word cut after rendering, and QC is where it must not be waved through.
    for join in plan_joins:
        for flag in join["flags"]:
            if flag["severity"] == "error":
                add(
                    "error",
                    f"cut {join['index'] + 1} (output {join['output_time']:.2f}s): {flag['message']}",
                    join_index=join["index"], code=flag["code"],
                )
    warning_codes: dict[str, int] = {}
    for join in plan_joins:
        for flag in join["flags"]:
            if flag["severity"] == "warning":
                warning_codes[flag["code"]] = warning_codes.get(flag["code"], 0) + 1
    for code, count in sorted(warning_codes.items(), key=lambda kv: -kv[1]):
        add(
            "warning",
            f"{count} join(s) carry the continuity flag `{code}` from the plan; each needs a verdict in "
            "out/condense_verify.md — accepted after listening, or fixed in the keep-list",
            code=code, count=count,
        )

    work_dir = ctx.resolve(args.get("frames_dir") or f".video_agent/condense_qc/{video_path.stem}")
    work_dir.mkdir(parents=True, exist_ok=True)
    for stale in list(work_dir.glob("*.jpg")) + list(work_dir.glob("*.png")):
        stale.unlink()

    audio_wav = work_dir / "audio.wav"
    audio_ok = has_audio and _extract_audio(video_path, audio_wav) is None
    reference_db = measure_loudness(video_path).get("mean_volume_db") if audio_ok else None
    # How wide a region the render attenuates at each join. A cross-dissolve is
    # an order of magnitude wider than the per-segment fade, and measuring inside
    # it reports the crossfade's own ramp as a natural breath.
    join_ramp = max(0.03, _number(render_report.get("dissolve_seconds"), 0.0))
    measured_cap = min(len(join_times), MAX_MEASURED_JOINS)
    if len(join_times) > MAX_MEASURED_JOINS:
        # A cap must never pass for a clean bill of health.
        add(
            "warning",
            f"this cut has {len(join_times)} joins but only the first {MAX_MEASURED_JOINS} were measured for audio "
            f"and picture change; joins {MAX_MEASURED_JOINS + 1}-{len(join_times)} were NOT checked. Treat them as "
            "unverified: either check them with video_watch_segment, or consolidate the keep-list into fewer, longer "
            "runs — a cut with this many joins is hard to verify and hard to watch.",
            unmeasured_joins=len(join_times) - MAX_MEASURED_JOINS,
        )
    join_measurements: list[dict[str, Any]] = []
    if audio_ok:
        for idx, moment in enumerate(join_times[:MAX_MEASURED_JOINS]):
            measurement = _measure_join(audio_wav, moment, reference_db, ramp=join_ramp)
            measurement["index"] = idx
            measurement["output_time"] = round(moment, 3)
            measurement["kind"] = join_kinds.get(idx, "content")
            join_measurements.append(measurement)
            # A filler excision is cut in speech by design, so "in_speech" is the
            # expected reading there and warning about it would be noise.
            if measurement["verdict"] == "in_speech" and measurement["kind"] == "content":
                add(
                    "warning",
                    f"cut {idx + 1} at output {moment:.2f}s has full speech energy on both sides "
                    f"(before {measurement['before_db']} dB, after {measurement['after_db']} dB, file mean "
                    f"{measurement['reference_db']} dB) — there is no breath at this join. It may be a clean "
                    "word-to-word splice or a clipped syllable; only listening tells you which.",
                    join_index=idx,
                )

    render_fps = _number(render_report.get("fps"), 0.0) or _probe_fps(video_path)
    visual_jumps = measure_visual_jumps(video_path, join_times, work_dir, render_fps, limit=measured_cap) if join_times else []
    for jump in visual_jumps:
        if jump["verdict"] == "severe":
            add(
                "warning",
                f"cut {jump['index'] + 1} at output {jump['output_time']:.2f}s changes the picture "
                f"{jump['ratio']:.1f}x more than the shot's own frame-to-frame motion — a jump this large reads as "
                "a glitch rather than an edit. Look at its frame row; keep the run intact (fewer cuts) if it matters.",
                join_index=jump["index"], ratio=jump["ratio"],
            )
        elif jump["verdict"] == "scene_change":
            add(
                "warning",
                f"cut {jump['index'] + 1} at output {jump['output_time']:.2f}s changes the picture "
                f"{jump['ratio']:.1f}x more than the shot's own motion — the two sides are effectively different "
                "shots, not two takes of one. That is fine when it is deliberate (the speaker moved, the scene "
                "changed, and the viewer reads it as a new shot), and a continuity break when it is not. Look at "
                "the frame row and say which in out/condense_verify.md; do not treat it as a jump cut to smooth over.",
                join_index=jump["index"], ratio=jump["ratio"],
            )

    evidence_count = int(_positive(args.get("max_evidence_joins"), DEFAULT_EVIDENCE_JOINS))
    sampled = _pick_evidence_joins(plan_joins, join_times, join_measurements, visual_jumps, evidence_count)
    images: list[str] = []
    frame_sheet = wave_sheet = None
    if sampled:
        try:
            frame_sheet = _build_join_frame_sheet(
                video_path, sampled, plan_joins, work_dir,
                _number(render_report.get("fps"), 0.0) or _probe_fps(video_path),
            )
            if frame_sheet:
                images.append(str(frame_sheet))
        except Exception as exc:
            add("warning", f"could not build join frame evidence: {exc}")
        if audio_ok:
            try:
                wave_sheet = _build_waveform_sheet(audio_wav, sampled, work_dir)
                if wave_sheet:
                    images.append(str(wave_sheet))
            except Exception as exc:
                add("warning", f"could not build join waveform evidence: {exc}")

    error_count = sum(1 for i in issues if i["severity"] == "error")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")
    report = {
        "status": "pass" if error_count == 0 else "fail",
        "error_count": error_count,
        "warning_count": warning_count,
        "plan_path": str(plan_path),
        "plan_sha256": file_sha256(plan_path),
        "video_path": str(video_path),
        "video_sha256": file_sha256(video_path),
        "render_report_path": str(render_report_path) if render_report else None,
        "join_mode": render_report.get("join"),
        "source_duration": plan.get("source_duration"),
        "expected_duration": round(expected, 3) if expected else None,
        "measured_duration": round(measured, 3) if measured else None,
        "compression_ratio": round(measured / plan["source_duration"], 4) if measured and plan.get("source_duration") else None,
        "clip_count": len(clips),
        "cut_count": len(join_times),
        "join_drift_per_index_s": round(join_drift_per_index, 5),
        "cuts_per_minute": round(cuts_per_minute, 2) if cuts_per_minute else None,
        "content_cuts_per_minute": round(content_cuts_per_minute, 2) if content_cuts_per_minute else None,
        "has_audio_stream": has_audio,
        "join_measurements": join_measurements,
        "measured_join_count": len(join_measurements),
        "unmeasured_join_count": max(0, len(join_times) - measured_cap),
        "visual_jumps": visual_jumps,
        "evidence_joins": [s["index"] for s in sampled],
        "images": {
            "join_frames": str(frame_sheet) if frame_sheet else None,
            "join_waveforms": str(wave_sheet) if wave_sheet else None,
        },
        "issues": issues,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json = ctx.resolve(args.get("output_json") or "out/condense_qc_report.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return ToolResult(
        text=_qc_text(report, sampled, ctx.virtualize(output_json)),
        data={k: v for k, v in report.items() if k not in {"join_measurements", "visual_jumps"}},
        artifacts=[str(output_json)],
        image_paths=images,
    )


def _extract_audio(video_path: Path, wav_path: Path) -> str | None:
    """One 16 kHz mono WAV up front, so per-join windows are cheap and exact.

    Seeking into the mp4 for every window would either be slow (accurate seek
    re-decodes from the last keyframe) or imprecise (fast seek lands on a
    keyframe), and a join measurement that is 200 ms off measures the wrong thing.
    """
    cmd = [
        "ffmpeg", "-y", "-v", "error", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav_path),
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=1800)
    except Exception as exc:
        return str(exc)
    return None if proc.returncode == 0 and wav_path.is_file() else (proc.stderr or "").strip()[-500:]


def _window_db(wav_path: Path, start: float, duration: float) -> float | None:
    cmd = [
        "ffmpeg", "-v", "info", "-ss", f"{max(0.0, start):.4f}", "-t", f"{duration:.4f}",
        "-i", str(wav_path), "-af", "volumedetect", "-f", "null", "-",
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=120)
    except Exception:
        return None
    match = _MEAN_VOLUME.search((proc.stderr or "") + (proc.stdout or ""))
    return float(match.group(1)) if match else None


def _measure_join(wav_path: Path, moment: float, reference_db: float | None, ramp: float = 0.03) -> dict[str, Any]:
    """Is the audio quiet immediately either side of the cut?

    An earlier version compared a window straddling the join against its
    neighbours looking for a "trough". That was wrong: the render's 30 ms fades
    are far too short to move a 100 ms mean, so the straddling window sometimes
    measured *louder* than both neighbours and the verdict was noise.

    What actually distinguishes a natural join is simpler and local: a cut placed
    in a breath has near-silence in the ~80 ms on each side of it, and a cut
    placed mid-phrase has full speech energy on both. So both windows are
    measured against the file's own overall level — which makes the test portable
    across recordings instead of depending on an absolute dBFS threshold.

    `ramp` is the region the render itself attenuates, and the windows must start
    outside it or the render manufactures the very quiet this looks for. A 30 ms
    fade needs almost no clearance; a 180 ms **cross-dissolve** needs six times as
    much, and measured with the fade-sized clearance the same material flipped
    from several `in_speech` verdicts to all `in_pause` purely because the
    crossfade ramped both sides down. Same class of error as the trough bug, one
    order of magnitude wider.
    """
    clearance = max(0.035, ramp / 2.0 + 0.02)
    pre = _window_db(wav_path, moment - clearance - 0.08, 0.08)
    post = _window_db(wav_path, moment + clearance, 0.08)
    verdict = "unknown"
    quiet_margin = 10.0
    if pre is not None and post is not None and reference_db is not None:
        threshold = reference_db - quiet_margin
        quiet_sides = (1 if pre <= threshold else 0) + (1 if post <= threshold else 0)
        verdict = {2: "in_pause", 1: "one_side_quiet", 0: "in_speech"}[quiet_sides]
    return {
        "before_db": round(pre, 1) if pre is not None else None,
        "after_db": round(post, 1) if post is not None else None,
        "reference_db": round(reference_db, 1) if reference_db is not None else None,
        "quiet_threshold_db": round(reference_db - quiet_margin, 1) if reference_db is not None else None,
        "window_clearance_s": round(clearance, 3),
        "verdict": verdict,
    }


def _pick_evidence_joins(
    plan_joins: list[dict[str, Any]],
    join_times: list[float],
    measurements: list[dict[str, Any]],
    visual_jumps: list[dict[str, Any]],
    count: int,
) -> list[dict[str, Any]]:
    """Spend the frame budget on the joins most likely to be wrong.

    Sampling evenly would give every join equal weight, but they are not equally
    suspect: a cut the plan flagged, or one the audio says has no dip, is where
    the defect lives. Suspect joins first, then an even spread of the rest so a
    clean-looking stretch is still represented.
    """
    if not join_times:
        return []
    suspicion: dict[int, float] = {}
    for join in plan_joins:
        score = sum({"error": 5.0, "warning": 2.0, "info": 0.3}.get(f["severity"], 0.0) for f in join["flags"])
        if score:
            suspicion[join["index"]] = suspicion.get(join["index"], 0.0) + score
    for measurement in measurements:
        if measurement["verdict"] == "in_speech" and measurement.get("kind", "content") == "content":
            suspicion[measurement["index"]] = suspicion.get(measurement["index"], 0.0) + 3.0
    for jump in visual_jumps:
        bonus = {"scene_change": 5.0, "severe": 4.0, "visible": 1.5}.get(jump["verdict"], 0.0)
        if bonus:
            suspicion[jump["index"]] = suspicion.get(jump["index"], 0.0) + bonus
    ordered = sorted(suspicion.items(), key=lambda kv: -kv[1])
    picked: list[int] = [idx for idx, _ in ordered[:count] if idx < len(join_times)]
    if len(picked) < count:
        remaining = [i for i in range(len(join_times)) if i not in picked]
        need = count - len(picked)
        if remaining:
            stride = max(1, len(remaining) // need)
            picked += remaining[::stride][:need]
    picked = sorted(set(picked))[:count]
    out = []
    for idx in picked:
        record = {"index": idx, "output_time": join_times[idx]}
        plan_join = next((j for j in plan_joins if j["index"] == idx), None)
        if plan_join:
            record["outgoing_tail"] = plan_join.get("outgoing_tail")
            record["incoming_head"] = plan_join.get("incoming_head")
            record["codes"] = [f["code"] for f in plan_join["flags"]]
        measurement = next((m for m in measurements if m["index"] == idx), None)
        if measurement:
            record["audio"] = measurement
        jump = next((j for j in visual_jumps if j["index"] == idx), None)
        if jump:
            record["visual"] = jump
        out.append(record)
    return out


def _frame_offsets(fps: float) -> tuple[float, ...]:
    """Sample offsets around a cut, in units of real frames.

    A fixed ±0.03 s looked reasonable and was useless: one frame at 30 fps is
    0.0333 s, so the two frames straddling the cut could resolve to the *same*
    decoded frame and the row proved nothing. Offsets have to be expressed in
    frames — 1.5 frames guarantees the tight pair lands on opposite sides of the
    boundary, and 5 frames gives the wider context that shows whether the pose
    moved rather than just whether the picture changed.
    """
    step = 1.0 / max(1.0, fps)
    return (-5.0 * step, -1.5 * step, 1.5 * step, 5.0 * step)


def _build_join_frame_sheet(
    video_path: Path,
    sampled: list[dict[str, Any]],
    plan_joins: list[dict[str, Any]],
    work_dir: Path,
    fps: float,
) -> Path | None:
    """One labelled row per join: two frames before the cut, two after.

    A jump cut is the failure a still cannot express on its own — you have to see
    the pose on both sides of the same instant. Two frames each side, tight around
    the cut, is the minimum that shows both "did the framing jump" and "did the
    speaker's mouth or hands teleport".
    """
    from PIL import Image, ImageDraw

    offsets = _frame_offsets(fps)
    rows: list[tuple[dict[str, Any], list[Path]]] = []
    for record in sampled:
        frames: list[Path] = []
        for slot, offset in enumerate(offsets):
            moment = max(0.0, record["output_time"] + offset)
            frame_path = work_dir / f"join{record['index']:03d}_{slot}.jpg"
            cmd = [
                "ffmpeg", "-y", "-v", "error", "-ss", f"{moment:.4f}", "-i", str(video_path),
                "-frames:v", "1", "-q:v", "3", str(frame_path),
            ]
            try:
                run_proc(cmd, capture_output=True, text=True, timeout=120)
            except Exception:
                continue
            if frame_path.is_file():
                frames.append(frame_path)
        if frames:
            rows.append((record, frames))
    if not rows:
        return None

    tile_width = 300
    label_height = 34
    tiles: list[tuple[dict[str, Any], list[Any]]] = []
    for record, frames in rows:
        images = []
        for path in frames:
            img = Image.open(path).convert("RGB")
            scale = tile_width / img.width
            images.append(img.resize((tile_width, max(1, int(img.height * scale))), Image.LANCZOS))
        tiles.append((record, images))
    row_height = max(max(i.height for i in imgs) for _, imgs in tiles) + label_height
    columns = max(len(imgs) for _, imgs in tiles)
    sheet = Image.new("RGB", (tile_width * columns, row_height * len(tiles)), (12, 12, 12))
    draw = ImageDraw.Draw(sheet)
    font = _qc_font(15)
    small = _qc_font(13)
    for row_idx, (record, images) in enumerate(tiles):
        top = row_idx * row_height
        codes = ", ".join(record.get("codes") or []) or "no flags"
        audio = record.get("audio") or {}
        visual = record.get("visual") or {}
        draw.text(
            (6, top + 3),
            f"cut {record['index'] + 1} @ {record['output_time']:.2f}s   {codes}"
            + (f"   audio {audio.get('verdict')}" if audio else "")
            + (f"   jump {visual.get('verdict')} ({visual.get('ratio')}x)" if visual else ""),
            fill=(255, 230, 110), font=font,
        )
        draw.text(
            (6, top + 19),
            f"…{record.get('outgoing_tail') or ''}  ┃  {record.get('incoming_head') or ''}…",
            fill=(180, 220, 255), font=small,
        )
        for col, img in enumerate(images):
            x = col * tile_width
            sheet.paste(img, (x, top + label_height))
            offset = offsets[col]
            side = "BEFORE" if offset < 0 else "AFTER"
            caption = f"{side} {offset * 1000:+.0f}ms ({offset * fps:+.1f}f)"
            # Bright footage swallows a bare label, and an unreadable label makes
            # the frame unusable as evidence — the reader cannot tell which side
            # of the cut they are looking at.
            box = draw.textbbox((x + 5, top + label_height + 3), caption, font=small)
            draw.rectangle([box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2], fill=(0, 0, 0))
            draw.text((x + 5, top + label_height + 3), caption, fill=(255, 150, 150), font=small)
            if col == len(images) // 2:
                draw.line([x, top + label_height, x, top + row_height], fill=(255, 60, 60), width=3)
        draw.line([0, top + row_height - 1, sheet.width, top + row_height - 1], fill=(70, 70, 70))
    sheet_path = work_dir / "join_frames.jpg"
    sheet.save(sheet_path, quality=86)
    return sheet_path


def _build_waveform_sheet(wav_path: Path, sampled: list[dict[str, Any]], work_dir: Path) -> Path | None:
    """A one-second waveform around each sampled cut, with the cut marked.

    The frames show whether the picture jumps; this shows whether the *sound*
    does. A cut in a breath has a visible trough at the marker; a cut through a
    word has continuous energy across it, which is legible at a glance in a way
    three dB numbers are not.
    """
    from PIL import Image, ImageDraw

    width, height = 720, 90
    strips: list[tuple[dict[str, Any], Any]] = []
    for record in sampled:
        start = max(0.0, record["output_time"] - 0.5)
        png = work_dir / f"wave{record['index']:03d}.png"
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", "1.0", "-i", str(wav_path),
            # cbrt, not lin: speech recorded at a conservative level draws as a
            # flat line on a linear amplitude scale, which hides the very trough
            # this image exists to show.
            "-filter_complex", f"showwavespic=s={width}x{height}:colors=0x8fd6ff:scale=cbrt",
            "-frames:v", "1", str(png),
        ]
        try:
            run_proc(cmd, capture_output=True, text=True, timeout=120)
        except Exception:
            continue
        if png.is_file():
            strips.append((record, Image.open(png).convert("RGB")))
    if not strips:
        return None
    label_height = 20
    sheet = Image.new("RGB", (width, (height + label_height) * len(strips)), (10, 10, 10))
    draw = ImageDraw.Draw(sheet)
    font = _qc_font(13)
    for idx, (record, img) in enumerate(strips):
        top = idx * (height + label_height)
        audio = record.get("audio") or {}
        draw.text(
            (6, top + 3),
            f"cut {record['index'] + 1} @ {record['output_time']:.2f}s   "
            f"before {audio.get('before_db')} dB / after {audio.get('after_db')} dB "
            f"(file mean {audio.get('reference_db')} dB, quiet below {audio.get('quiet_threshold_db')} dB)"
            f"   → {audio.get('verdict')}",
            fill=(255, 230, 110), font=font,
        )
        sheet.paste(img, (0, top + label_height))
        # The cut is at the centre of the one-second window.
        marker_x = width // 2
        draw.line([marker_x, top + label_height, marker_x, top + label_height + height], fill=(255, 70, 70), width=2)
        draw.line([0, top + label_height + height - 1, width, top + label_height + height - 1], fill=(60, 60, 60))
    sheet_path = work_dir / "join_waveforms.png"
    sheet.save(sheet_path)
    return sheet_path


def _qc_font(size: int):
    from PIL import ImageFont

    from . import subtitle_style as sty

    candidate = sty.resolve_font_file("Noto Sans SC", "regular")
    if candidate:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()


JUMP_VISIBLE_RATIO = 3.0
JUMP_SEVERE_RATIO = 6.0
# Above this the two sides are not the same shot in any useful sense — the
# speaker has moved to a different position or the scene has changed. Measured at
# 26x on a real cut where a seated talk became a floor demonstration. Worth its
# own band because the verdict differs in kind: a `severe` jump is a bad cut to
# fix, a `scene_change` is either deliberate (and reads fine, because the viewer
# reads it as a new shot rather than a glitch) or a continuity break that needs
# the frames looked at, not a threshold tuned.
JUMP_SCENE_CHANGE_RATIO = 15.0


def measure_visual_jumps(
    video_path: Path,
    join_times: list[float],
    work_dir: Path,
    fps: float,
    limit: int = MAX_MEASURED_JOINS,
) -> list[dict[str, Any]]:
    """How big is the picture change at each cut, relative to normal motion?

    "Is this jump cut visible" is the most subjective checkpoint in the pipeline,
    and it does not have to be. The absolute pixel difference across a cut means
    nothing on its own — a busy shot differs a lot frame to frame anyway — but the
    *ratio* of the across-cut difference to the ordinary frame-to-frame difference
    a few frames earlier is scale-free and matches what a viewer notices: a cut
    that changes the picture no more than the speaker's own movement does is
    invisible, and one that changes it many times more reads as a glitch.

    This also means the visual checkpoint has a number behind it even when the
    frames themselves cannot be read, which matters because the material this
    pipeline exists for is video of people talking.
    """
    from PIL import Image

    step = 1.0 / max(1.0, fps)
    results: list[dict[str, Any]] = []

    def grab(moment: float, tag: str) -> Any:
        path = work_dir / f"jump_{tag}.jpg"
        cmd = [
            "ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, moment):.4f}", "-i", str(video_path),
            "-frames:v", "1", "-vf", "scale=192:-2", "-q:v", "4", str(path),
        ]
        try:
            run_proc(cmd, capture_output=True, text=True, timeout=60)
        except Exception:
            return None
        if not path.is_file():
            return None
        try:
            return Image.open(path).convert("L")
        except Exception:
            return None

    def diff(a: Any, b: Any) -> float | None:
        if a is None or b is None or a.size != b.size:
            return None
        pa, pb = a.getdata(), b.getdata()
        total = sum(abs(x - y) for x, y in zip(pa, pb))
        return total / max(1, len(a.getdata()))

    for idx, moment in enumerate(join_times[:limit]):
        before = grab(moment - 1.5 * step, f"{idx:03d}_b")
        after = grab(moment + 1.5 * step, f"{idx:03d}_a")
        # Baseline: ordinary motion inside the outgoing shot, a few frames back.
        base_a = grab(moment - 5.5 * step, f"{idx:03d}_r0")
        base_b = grab(moment - 4.0 * step, f"{idx:03d}_r1")
        across = diff(before, after)
        baseline = diff(base_a, base_b)
        record: dict[str, Any] = {
            "index": idx,
            "output_time": round(moment, 3),
            "across_cut_diff": round(across, 2) if across is not None else None,
            "baseline_motion_diff": round(baseline, 2) if baseline is not None else None,
        }
        if across is None or baseline is None:
            record["ratio"] = None
            record["verdict"] = "unknown"
        else:
            # Floor the baseline: on a locked-off shot with a still speaker the
            # ordinary difference is near zero, and dividing by it would report an
            # enormous ratio for a cut nobody would notice.
            ratio = across / max(baseline, 1.5)
            record["ratio"] = round(ratio, 2)
            if ratio >= JUMP_SCENE_CHANGE_RATIO:
                record["verdict"] = "scene_change"
            elif ratio >= JUMP_SEVERE_RATIO:
                record["verdict"] = "severe"
            elif ratio >= JUMP_VISIBLE_RATIO:
                record["verdict"] = "visible"
            else:
                record["verdict"] = "subtle"
        results.append(record)
    for stale in work_dir.glob("jump_*.jpg"):
        stale.unlink()
    return results


def _qc_text(report: dict[str, Any], sampled: list[dict[str, Any]], report_path: str) -> str:
    errors = [i for i in report["issues"] if i["severity"] == "error"]
    warnings = [i for i in report["issues"] if i["severity"] == "warning"]
    verdicts: dict[str, int] = {}
    for measurement in report["join_measurements"]:
        verdicts[measurement["verdict"]] = verdicts.get(measurement["verdict"], 0) + 1
    audio_summary = ", ".join(f"{k}: {v}" for k, v in sorted(verdicts.items())) or "not measured"
    jump_verdicts: dict[str, int] = {}
    for jump in report.get("visual_jumps") or []:
        jump_verdicts[jump["verdict"]] = jump_verdicts.get(jump["verdict"], 0) + 1
    jump_summary = ", ".join(f"{k}: {v}" for k, v in sorted(jump_verdicts.items())) or "not measured"
    lines = [
        f"QC {report['status'].upper()}: {report['error_count']} error(s), {report['warning_count']} warning(s). "
        f"{report_path}",
        f"Output {report['measured_duration']}s vs planned {report['expected_duration']}s; "
        f"{report['clip_count']} clip(s), {report['cut_count']} cut(s)"
        + (f", {report['content_cuts_per_minute']} content cuts/min "
           f"({report['cuts_per_minute']} incl. imperceptible pause tightens)"
           if report.get("content_cuts_per_minute") is not None else "")
        + (f", {(report['compression_ratio'] or 0) * 100:.0f}% of source" if report.get("compression_ratio") else "")
        + f", join mode {report.get('join_mode')}.",
        f"Audio at cuts: {audio_summary}. Measured as the level in the 80 ms immediately either side of the cut, "
        "against the file's own mean. `in_pause` = quiet both sides, the cut sits in a breath. `one_side_quiet` = "
        "fine. `in_speech` = full speech energy both sides, so there is no breath there: on a content cut that is "
        "either a clean word-to-word splice or a clipped syllable and only listening separates them; on a filler "
        "excision it is expected by design.",
        (
            f"NOTE: {report['unmeasured_join_count']} of {report['cut_count']} joins were beyond the measurement cap "
            f"and were NOT checked for audio or picture change — treat them as unverified.\n"
            if report.get("unmeasured_join_count") else ""
        )
        + f"Picture change at cuts: {jump_summary}. Measured as the across-cut frame difference divided by the "
        f"shot's own frame-to-frame motion just before it — scale-free, so it means the same thing on a static "
        f"shot and a busy one. `subtle` (<{JUMP_VISIBLE_RATIO:g}x) is invisible to a viewer, `visible` is a "
        f"noticeable jump cut, `severe` (>={JUMP_SEVERE_RATIO:g}x) reads as a glitch. This is a measurement, not a "
        "verdict: read the frame row to decide whether the jump is acceptable for this material.",
    ]
    if errors:
        lines.append("\nERRORS (blocking):")
        lines += [f"  - {i['message']}" for i in errors[:20]]
    if warnings:
        lines.append("\nWARNINGS (accept consciously or fix — either way they need a verdict):")
        lines += [f"  - {i['message']}" for i in warnings[:20]]
    if sampled:
        lines.append(
            f"\nEvidence for cut(s) {', '.join(str(s['index'] + 1) for s in sampled)} follows as two images. "
            "The first is four frames per cut — two before, two after, with the cut marked in red: read each row and "
            "judge whether the picture jumps in a way a viewer would notice (pose, hands, gaze, framing). The second "
            "is a one-second waveform per cut with the cut marked: a cut in a breath shows the waveform collapsing "
            "toward the marker, a cut through a word shows energy running straight across it."
        )
        lines.append(
            "Frames and a waveform cannot settle whether the *edit* makes sense — that is what out/condense_script.md "
            "is for, and what a high-fps video_watch_segment over a cut is for. Record one verdict per checkpoint in "
            "out/condense_verify.md."
        )
    else:
        lines.append("\nNo cuts to sample (single-clip output), so there are no join artefacts to inspect.")
    return "\n".join(lines)


