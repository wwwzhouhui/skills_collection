"""Subtitle authoring for talking-head (口播) video: cue segmentation, burn-in
rendering, and subtitle-specific QC with visual evidence.

The interesting part is `subtitle_build`. ASR gives us segment-level timing —
one segment can be a fifteen-second run of speech — but a subtitle cue is a
couple of seconds of readable text. Turning one into the other well needs three
things the naive "split by character count" approach does not do:

1.  Break where the sentence breaks. Cut points are scored by the punctuation
    at the break, so a cue ends at a full stop rather than mid-phrase.
2.  Break where the speaker breathes. Boundary times are snapped onto real
    silences detected in the audio, so a cue change lands in a pause instead of
    clipping a syllable.
3.  Optimise globally, not greedily. A dynamic program over all candidate break
    points minimises a joint cost (reading speed, line fill, break quality), so
    one awkward early cut cannot cascade through the rest of the segment.

Widths are measured in real pixels with the same font file libass renders with,
so "does this line fit" is answered the same way at build time and at QC time.
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

from . import subtitle_style as sty
from .result import ToolResult
from .run_context import RunContext
from .timeline import file_sha256, media_duration_seconds
from .transcript import coerce_float, collect_segments, first_present, load_transcript_data

# Silence quieter than this for at least MIN_SILENCE seconds counts as a pause
# a cue boundary may be snapped onto.
DEFAULT_SILENCE_DB = -32.0
DEFAULT_MIN_SILENCE = 0.10
DEFAULT_SNAP_WINDOW = 0.35
# Keep a cue on screen across gaps shorter than this instead of flickering off.
GAP_HOLD_SECONDS = 0.50
LEAD_IN = 0.05
TAIL_HOLD = 0.15
INF = float("inf")


_MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?[\d.]+)\s*dB")
_MAX_VOLUME = re.compile(r"max_volume:\s*(-?[\d.]+)\s*dB")
# Offset below the file's RMS level used by silence_db="auto". Calibrated on
# only two clips so far (a narration-over-music mix and a dry voice recording),
# so treat it as a starting point to verify, not a settled constant.
AUTO_SILENCE_OFFSET_DB = 8.0


def measure_loudness(video_path: Path) -> dict[str, float | None]:
    """RMS and peak level of the audio, via ffmpeg volumedetect.

    Reported alongside the cues because a fixed dBFS silence threshold is not
    portable: a narration-over-music mix and a dry voice recording can sit 20 dB
    apart, which changes detected pause density by more than 10x at the same
    threshold. The caller needs to see the level to judge the threshold.
    """
    cmd = ["ffmpeg", "-v", "info", "-i", str(video_path), "-vn", "-af", "volumedetect", "-f", "null", "-"]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=900)
    except Exception:
        return {"mean_volume_db": None, "max_volume_db": None}
    log = (proc.stderr or "") + (proc.stdout or "")
    mean = _MEAN_VOLUME.search(log)
    peak = _MAX_VOLUME.search(log)
    return {
        "mean_volume_db": float(mean.group(1)) if mean else None,
        "max_volume_db": float(peak.group(1)) if peak else None,
    }


def resolve_silence_db(value: object, loudness: dict[str, float | None]) -> tuple[float, str]:
    """Return the threshold to use and how it was chosen."""
    if isinstance(value, str) and value.strip().lower() == "auto":
        mean = loudness.get("mean_volume_db")
        if mean is None:
            return DEFAULT_SILENCE_DB, "fixed default (loudness measurement failed)"
        return round(mean - AUTO_SILENCE_OFFSET_DB, 1), f"auto: mean_volume {mean:.1f} dB - {AUTO_SILENCE_OFFSET_DB:.0f}"
    if value is None:
        return DEFAULT_SILENCE_DB, "fixed default"
    return coerce_number(value, DEFAULT_SILENCE_DB), "caller-specified"


# --- build ----------------------------------------------------------------

def subtitle_build(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not args.get("transcript_path"):
        return ToolResult(text="[ERROR] transcript_path is required")
    if not args.get("video_path"):
        return ToolResult(text="[ERROR] video_path is required (cue timing is snapped to pauses in its audio)")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")

    transcript_path = ctx.resolve(args["transcript_path"])
    if not transcript_path.is_file():
        return ToolResult(text=f"[ERROR] transcript not found: {transcript_path}")
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

    # speaker_names is a data map (ASR speaker label -> display name the model
    # has worked out), not a visual style, so it rides alongside the style dict
    # rather than through the preset merge.
    speaker_names = args.get("speaker_names")
    if speaker_names is not None:
        if not isinstance(speaker_names, dict):
            return ToolResult(text="[ERROR] speaker_names must be an object mapping speaker label to display name")
        style["speaker_names"] = {str(k): str(v) for k, v in speaker_names.items()}

    try:
        segments = load_timed_segments(transcript_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read transcript: {exc}")
    if not segments:
        return ToolResult(
            text="[ERROR] transcript has no timed segments; subtitle timing needs start/end per segment",
            data={"transcript_path": str(transcript_path)},
        )

    snap_window = coerce_positive(args.get("snap_window_seconds"), DEFAULT_SNAP_WINDOW)
    missing_glyphs = sty.uncovered_characters("".join(s["text"] for s in segments), style)
    if missing_glyphs:
        return ToolResult(
            text=(
                f"[ERROR] the resolved font {style['font_file']} has no glyph for "
                f"{''.join(missing_glyphs)} and would render blanks or tofu boxes. "
                "Install a font covering this script, or pass style.font_file explicitly."
            ),
            data={"font_file": style["font_file"], "missing_glyphs": missing_glyphs},
        )
    loudness = measure_loudness(video_path)
    silence_db, silence_db_origin = resolve_silence_db(args.get("silence_db"), loudness)
    min_silence = coerce_positive(args.get("min_silence_seconds"), DEFAULT_MIN_SILENCE)
    pauses = detect_pauses(video_path, silence_db=silence_db, min_silence=min_silence)

    cues: list[dict[str, Any]] = []
    for seg_index, segment in enumerate(segments):
        cues.extend(segment_to_cues(segment, seg_index, style, pauses, snap_window))
    cues = finalize_cues(cues, style, video_duration=duration, pauses=pauses)
    if not cues:
        return ToolResult(
            text="[ERROR] no subtitle cues were produced; the transcript segments carried no displayable text",
            data={"segment_count": len(segments)},
        )

    ass_text = sty.build_ass(cues, style, title=video_path.stem)
    srt_text = sty.build_srt(cues)
    output_json = ctx.resolve(args.get("output_json") or "out/subtitles.json")
    output_ass = ctx.resolve(args.get("output_ass") or output_json.with_suffix(".ass"))
    output_srt = ctx.resolve(args.get("output_srt") or output_json.with_suffix(".srt"))
    for path in (output_json, output_ass, output_srt):
        path.parent.mkdir(parents=True, exist_ok=True)
    output_ass.write_text(ass_text, encoding="utf-8")
    output_srt.write_text(srt_text, encoding="utf-8")

    stats = cue_stats(cues, segments, style, duration)
    package = {
        "version": "1.0",
        "source_video": str(video_path),
        "source_video_sha256": file_sha256(video_path),
        "transcript_path": str(transcript_path),
        "language": args.get("language") or detect_language(segments),
        "video": {"width": width, "height": height, "duration": duration},
        "style": style,
        "pause_count": len(pauses),
        "pause_density_per_second": round(len(pauses) / duration, 3) if duration else 0.0,
        "audio_loudness": loudness,
        "silence_db": silence_db,
        "silence_db_origin": silence_db_origin,
        "min_silence_seconds": min_silence,
        "snap_window_seconds": snap_window,
        "cues": cues,
        "stats": stats,
        "ass_path": str(output_ass),
        "srt_path": str(output_srt),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")

    hints = build_hints(stats, style, package)
    return ToolResult(
        text=(
            f"Built {len(cues)} subtitle cues from {len(segments)} transcript segments "
            f"({stats['snapped_boundaries']}/{stats['internal_boundaries']} boundaries snapped to a real pause). "
            f"Read the cue table below and check the wording and break points before rendering: "
            f"{ctx.virtualize(output_json)}\n\n" + cue_table(cues)
            + (("\n\n" + hints) if hints else "")
        ),
        data={k: v for k, v in package.items() if k != "cues"},
        artifacts=[str(output_json), str(output_ass), str(output_srt)],
    )


def build_hints(stats: dict[str, Any], style: dict[str, Any], package: dict[str, Any]) -> str:
    """Surface the two failure modes a caller cannot see from the cue table
    alone, with the concrete knob to turn."""
    hints: list[str] = []
    internal = int(stats.get("internal_boundaries") or 0)
    snapped = int(stats.get("snapped_boundaries") or 0)
    if internal >= 4 and snapped / internal < 0.5:
        mean = (package.get("audio_loudness") or {}).get("mean_volume_db")
        level = f"audio RMS {mean:.1f} dB, " if isinstance(mean, (int, float)) else ""
        origin = str(package.get("silence_db_origin") or "")
        if origin.startswith("auto"):
            # Already level-relative, so the remaining knob is the duration floor.
            advice = (
                "The threshold is already derived from the measured level, so the next knob is "
                f"min_silence_seconds (currently {package.get('min_silence_seconds')}) — lowering it to 0.06 "
                "admits shorter breaths. Some narration genuinely runs without pauses at cue-length intervals, "
                "in which case no threshold helps and the interpolated timing is what you ship."
            )
        else:
            advice = (
                'Re-run with silence_db="auto" to derive the threshold from the measured level instead of a '
                "fixed dBFS value, or pass an explicit number, and compare the ratio."
            )
        hints.append(
            f"[timing] Only {snapped} of {internal} invented cue boundaries landed on a detected pause "
            f"({package.get('pause_count')} found, {package.get('pause_density_per_second')}/s at "
            f"silence_db={package.get('silence_db')} [{origin}], {level}"
            f"min_silence_seconds={package.get('min_silence_seconds')}). The unsnapped boundaries are timed by "
            "interpolating speech rate and may drift against the audio. A low density usually means the "
            "threshold sits below this mix's noise floor — a music bed or room tone does that. "
            + advice
            + " Whatever you ship, verify unsnapped boundaries with video_watch_segment."
        )
    max_cps = float(stats.get("max_cps") or 0)
    budget = float(style.get("max_cps") or 0)
    if budget and max_cps > budget:
        hints.append(
            f"[reading speed] Peak {max_cps:.1f} chars/s against a {budget:.1f} budget. If most cues are over, "
            "the speaker is simply fast and no segmentation fixes it — the honest options are accepting it or "
            "condensing the wording. If only a few are over, they are candidates for a longer on-screen time."
        )
    return "\n".join(hints)


def segment_to_cues(
    segment: dict[str, Any],
    seg_index: int,
    style: dict[str, Any],
    pauses: list[tuple[float, float]],
    snap_window: float,
) -> list[dict[str, Any]]:
    text = sty.normalize_asr_text(segment["text"])
    if not text:
        return []
    atoms = tokenize_atoms(text, style)
    if not atoms:
        return []

    seg_start = float(segment["start"])
    seg_end = float(segment["end"])
    if not (math.isfinite(seg_start) and math.isfinite(seg_end)) or seg_end <= seg_start:
        return []

    # Map atom boundaries onto time by cumulative speech weight, not raw
    # character count, so a run of Latin letters does not hog the clock. The
    # raw form is used here because punctuation buys real pause time even when
    # the style does not print it.
    units = [sty.display_units(a["raw"]) for a in atoms]
    total_units = sum(units) or 1.0
    prefix = [0.0]
    for value in units:
        prefix.append(prefix[-1] + value)
    span = seg_end - seg_start

    def time_at(atom_index: int) -> float:
        return seg_start + span * (prefix[atom_index] / total_units)

    breaks = plan_breaks(atoms, prefix, total_units, span, style)
    cues: list[dict[str, Any]] = []
    for order, (i, j) in enumerate(breaks):
        cue_text = atoms_display(atoms, i, j)
        if not cue_text:
            continue
        cues.append({
            "start": time_at(i),
            "end": time_at(j),
            "text": cue_text,
            "lines": sty.wrap_lines(cue_text, style),
            "source_segment": seg_index,
            "speaker": segment.get("speaker"),
            "_words": segment.get("words"),
            "break_strength": atoms[j - 1]["break_after"],
            "is_segment_start": order == 0,
            "is_segment_end": j == len(atoms),
            "snapped_start": False,
            "snapped_end": False,
        })
    if not cues:
        return []

    # The first/last cue own the segment's own boundaries exactly; only the
    # cuts we invented inside the segment get snapped to audio pauses.
    cues[0]["start"] = max(0.0, seg_start - LEAD_IN)
    # Hold the last cue slightly past the speech, but never past the style's
    # own maximum on-screen time.
    hold_room = max(0.0, float(style["max_duration"]) - (seg_end - cues[-1]["start"]))
    cues[-1]["end"] = seg_end + min(TAIL_HOLD, hold_room)
    for idx in range(len(cues) - 1):
        boundary = 0.5 * (cues[idx]["end"] + cues[idx + 1]["start"])
        snapped = snap_to_pause(boundary, pauses, snap_window)
        if snapped is None:
            continue
        pause_start, pause_end = snapped
        # Land the cue change inside the real pause (that is what keeps it off a
        # syllable) but choose *where* in the pause by reading speed, not by
        # always parking it at the pause's far edge. Parking the incoming cue at
        # pause_end starves it whenever the pause sits late in its neighbour's
        # proportional slot: the seaice narration spiked one cue to 18.9 cps
        # purely this way, when the same split reads at 15.1 cps unsnapped.
        # The split that gives both neighbours equal reading speed is the
        # char-weighted division of their shared span; clamp that fair point into
        # the pause so sync is preserved but no cue is starved further than the
        # pause geometry forces.
        a = cues[idx]["start"]
        b = cues[idx + 1]["end"]
        prev_chars = max(1, sty.visible_char_count(cues[idx]["text"]))
        next_chars = max(1, sty.visible_char_count(cues[idx + 1]["text"]))
        fair = (prev_chars * b + next_chars * a) / (prev_chars + next_chars)
        swap = min(max(fair, pause_start), pause_end)
        swap = max(a + 0.20, min(swap, b - 0.20))
        half_gap = 0.5 * float(style["min_gap"])
        cues[idx]["end"] = max(a + 0.15, swap - half_gap)
        cues[idx + 1]["start"] = min(b - 0.15, max(cues[idx]["end"], swap + half_gap))
        cues[idx]["snapped_end"] = True
        cues[idx + 1]["snapped_start"] = True
    return cues


def plan_breaks(
    atoms: list[dict[str, Any]],
    prefix: list[float],
    total_units: float,
    span: float,
    style: dict[str, Any],
) -> list[tuple[int, int]]:
    """Choose cue boundaries with a dynamic program over every candidate break.

    cost[j] is the cheapest way to cover atoms[0:j]; each transition i -> j is
    one cue. Because a cue can only get so wide and so long, the inner loop
    stops as soon as extending leftward is physically impossible, which keeps
    this linear in practice.
    """
    n = len(atoms)
    max_lines = int(style["max_lines"])
    usable = float(style["usable_width_px"])
    # A cue may render slightly condensed rather than being split, so the hard
    # width ceiling sits above the nominal usable width. Without this, a phrase
    # that overshoots the margin by a few pixels gets torn in half.
    shrink_floor = float(style.get("shrink_floor") or 1.0)
    line_ceiling = usable / max(0.5, min(1.0, shrink_floor))
    capacity = line_ceiling * max_lines
    max_duration = float(style["max_duration"])
    min_duration = float(style["min_duration"])
    max_cps = float(style["max_cps"])
    target_fill = float(style["target_fill"])

    cost = [INF] * (n + 1)
    back = [0] * (n + 1)
    cost[0] = 0.0
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            if cost[i] == INF and i != 0:
                continue
            text = atoms_display(atoms, i, j)
            if not text:
                continue
            single_width = sty.text_width_px(text, style)
            if single_width > capacity and j - i > 1:
                # Any further-left i is wider still.
                break
            duration = span * (prefix[j] - prefix[i]) / total_units
            if duration > max_duration and j - i > 1:
                break
            if cost[i] == INF:
                continue

            lines = sty.wrap_lines(text, style)
            if len(lines) > max_lines:
                continue
            widest = max(sty.text_width_px(line, style) for line in lines)
            if widest > line_ceiling and j - i > 1:
                continue
            max_chars = int(style.get("max_chars_per_line") or 0)
            if max_chars and any(not sty.fits_chars(line, max_chars) for line in lines) and j - i > 1:
                continue

            candidate = cost[i] + cue_cost(
                text=text,
                lines=lines,
                widest=widest,
                usable=usable,
                duration=duration,
                break_after=atoms[j - 1]["break_after"],
                trailing_taboo=bool(atoms[j - 1].get("trailing_taboo")),
                leading_taboo=bool(atoms[i].get("leading_taboo")) and i > 0,
                is_last=(j == n),
                min_duration=min_duration,
                max_cps=max_cps,
                target_fill=target_fill,
            )
            if candidate < cost[j]:
                cost[j] = candidate
                back[j] = i
    if cost[n] == INF:
        # Nothing satisfied the hard constraints (e.g. a single unbreakable
        # token wider than the frame). Fall back to one cue for the segment so
        # the caller still sees the text and QC can flag the overflow.
        return [(0, n)]
    spans: list[tuple[int, int]] = []
    j = n
    while j > 0:
        i = back[j]
        spans.append((i, j))
        j = i
    spans.reverse()
    return spans


def cue_cost(
    *,
    text: str,
    lines: list[str],
    widest: float,
    usable: float,
    duration: float,
    break_after: int,
    trailing_taboo: bool,
    leading_taboo: bool,
    is_last: bool,
    min_duration: float,
    max_cps: float,
    target_fill: float,
) -> float:
    """Lower is better. Every term is a readability rule, not an aesthetic."""
    total = 0.0

    # Reading speed: above the budget the viewer cannot finish the line.
    cps = sty.estimate_cps(text, duration)
    if cps > max_cps:
        total += 9.0 * (cps - max_cps) ** 2

    # Too brief to read at all, even if the reading speed looks fine.
    if duration < min_duration:
        total += 40.0 * (min_duration - duration)

    # Prefer cues that use most of the line rather than a dribble of words,
    # except for the trailing cue, which is allowed to be short.
    if not is_last:
        fill = widest / usable if usable > 0 else 1.0
        total += 20.0 * (target_fill - fill) ** 2

    # Condensing a cue to keep a phrase whole is allowed but not free.
    overshoot = max(0.0, (widest / usable) - 1.0) if usable > 0 else 0.0
    total += 20.0 * overshoot

    # Break quality: ending on a full stop is free, ending merely because the
    # line ran out of room is expensive. This has to outweigh the fill term,
    # or the segmenter will pack lines to the margin and break mid-sentence.
    # The final cue of a segment ends where the speech ends, so it pays nothing.
    if not is_last:
        total += {3: 0.0, 2: 1.0}.get(break_after, 8.0)

    # Never leave a conjunction, particle or adverb dangling at the end of a
    # cue: the viewer reads "心思和" and then has to wait for the word it was
    # pointing at. Costly enough to lose to almost any alternative.
    if trailing_taboo and not is_last:
        total += 14.0

    # The mirror case: a cue that opens with a bare conjunction or particle has
    # been cut out of the phrase it belongs to. Breaking 心思和精力 after 心思
    # passes the trailing check and still strands 和 at the head of the next cue.
    if leading_taboo:
        total += 11.0

    # A two- or three-word cue flashes past; discourage unless punctuation
    # genuinely ends the thought there.
    chars = sty.visible_char_count(text)
    if chars < 5 and not is_last:
        total += 2.0 * (5 - chars)

    # Two lines are fine but one is cleaner when both would read the same.
    total += 1.0 * (len(lines) - 1)

    # A multi-line cue whose own internal wrap has to cut through a phrase is
    # usually a sign the cue is too long: two shorter cues would each wrap
    # cleanly. Charge for it so the segmenter prefers splitting instead.
    for line in lines[:-1]:
        stripped = line.rstrip()
        if stripped and stripped[-1] not in sty.STRONG_PUNCT + sty.WEAK_PUNCT:
            total += 4.0
    return total


def atoms_display(atoms: list[dict[str, Any]], i: int, j: int) -> str:
    """The on-screen text for a run of atoms, with the surrounding whitespace
    that punctuation stripping may have left behind removed."""
    return "".join(a["display"] for a in atoms[i:j]).strip()


def tokenize_atoms(text: str, style: dict[str, Any]) -> list[dict[str, Any]]:
    """Split text into indivisible units, each tagged with how good a cue break
    immediately after it would be (3 strong punctuation, 2 weak, 1 word
    boundary).

    Two things make this the crux of the whole segmenter.

    Chinese has no spaces, so without word segmentation every character looks
    like a legal break and the segmenter happily cuts 柠檬茶 into 柠 / 檬茶.
    Atoms are therefore words, not characters.

    And break strength is read off the *original* punctuation even when the
    style does not display it. Short-form captions drop commas, but the comma
    is still the best available evidence for where a phrase ends, so each atom
    keeps a raw form for scoring and a display form for drawing.
    """
    tokens = sty.cut_words_tagged(text)
    atoms: list[dict[str, Any]] = []
    for token, pos in tokens:
        if not token:
            continue
        if token.isspace():
            if atoms:
                atoms[-1]["display"] += " "
                atoms[-1]["raw"] += " "
                atoms[-1]["break_after"] = max(atoms[-1]["break_after"], 1)
            continue
        strength = _punctuation_strength(token)
        if strength is not None and atoms:
            # Punctuation is not a cue of its own; it trails the word it
            # follows and upgrades the break strength at that position. It also
            # clears any taboo: "心思和，" does end a phrase.
            atoms[-1]["raw"] += token
            atoms[-1]["display"] += sty.to_display_text(token, style)
            atoms[-1]["break_after"] = max(atoms[-1]["break_after"], strength)
            if strength >= 2:
                atoms[-1]["trailing_taboo"] = False
            continue
        atoms.append({
            "raw": token,
            "display": sty.to_display_text(token, style),
            "text": token,
            "pos": pos,
            "break_after": 1,
            "trailing_taboo": sty.is_trailing_taboo(token, pos),
            "leading_taboo": sty.is_leading_taboo(token, pos),
        })
    if atoms:
        atoms[-1]["break_after"] = 3
        atoms[-1]["trailing_taboo"] = False
    return [a for a in atoms if a["display"].strip() or a["raw"].strip()]


def _punctuation_strength(token: str) -> int | None:
    """Break strength a trailing punctuation token grants, or None if the token
    is not punctuation."""
    if not token or any(ch not in sty.ALL_PUNCT for ch in token):
        return None
    if any(ch in sty.STRONG_PUNCT for ch in token):
        return 3
    if any(ch in sty.WEAK_PUNCT + sty.CLOSING_PUNCT for ch in token):
        return 2
    return 0


def finalize_cues(
    cues: list[dict[str, Any]],
    style: dict[str, Any],
    *,
    video_duration: float,
    pauses: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    """Global pass: order, de-overlap, hold across short gaps, clamp to the
    video, and re-derive the reported metrics from the final times."""
    cues = [c for c in cues if c["text"].strip()]
    cues.sort(key=lambda c: (c["start"], c["end"]))
    min_gap = float(style["min_gap"])
    max_duration = float(style["max_duration"])

    for idx, cue in enumerate(cues):
        cue["start"] = max(0.0, min(cue["start"], video_duration))
        cue["end"] = max(cue["start"] + 0.05, min(cue["end"], video_duration))
        if idx == 0:
            continue
        prev = cues[idx - 1]
        if cue["start"] < prev["end"] + min_gap:
            # Overlap or too tight: give the boundary to the later cue and pull
            # the earlier one back, never past its own start.
            boundary = max(prev["start"] + 0.20, min(cue["start"], prev["end"]))
            prev["end"] = max(prev["start"] + 0.20, boundary - min_gap)
            cue["start"] = max(cue["start"], prev["end"] + min_gap)

    for idx in range(len(cues) - 1):
        gap = cues[idx + 1]["start"] - cues[idx]["end"]
        # A sub-half-second hole reads as a flicker; hold the cue through it.
        if 0 < gap < GAP_HOLD_SECONDS:
            extended = cues[idx + 1]["start"] - min_gap
            if extended - cues[idx]["start"] <= max_duration:
                cues[idx]["end"] = extended

    out: list[dict[str, Any]] = []
    usable = float(style.get("usable_width_px") or 0)
    for idx, cue in enumerate(cues, start=1):
        if cue["end"] - cue["start"] <= 0:
            continue
        cue["index"] = idx
        cue["start"] = round(cue["start"], 3)
        cue["end"] = round(cue["end"], 3)
        cue["duration"] = round(cue["end"] - cue["start"], 3)
        cue["lines"] = sty.wrap_lines(cue["text"], style)
        cue["chars"] = sty.visible_char_count(cue["text"])
        cue["cps"] = round(sty.estimate_cps(cue["text"], cue["duration"]), 2)
        widest = max(sty.text_width_px(l, style) for l in cue["lines"])
        # Condense rather than overflow when a whole phrase is a few pixels too
        # wide; QC measures against this same factor.
        cue["font_scale"] = round(min(1.0, usable / widest), 3) if usable and widest > usable else 1.0
        cue["widest_line_px"] = round(widest * cue["font_scale"], 1)
        out.append(cue)
    apply_speaker_styling(out, style)
    if style.get("karaoke"):
        for cue in out:
            cue["karaoke"] = karaoke_units(cue, style, pauses)
    # Drop the internal word-timing payload; it has done its job and would only
    # bloat subtitles.json.
    for cue in out:
        cue.pop("_words", None)
    return out


def apply_speaker_styling(cues: list[dict[str, Any]], style: dict[str, Any]) -> None:
    """When speaker labels are on, give each cue a name tag and a stable colour.

    The display name comes from `speaker_names` (a map the model fills in once it
    has worked out who is who), falling back to the raw ASR speaker label. Colour
    assignment is first-seen order from a fixed palette, so the same speaker keeps
    the same colour across the whole video. If a cue already carries an explicit
    `speaker_prefix`/`speaker_colour` (e.g. hand-edited), it is left untouched.
    """
    if not style.get("speaker_labels"):
        return
    names = style.get("speaker_names") if isinstance(style.get("speaker_names"), dict) else {}
    colours = style.get("speaker_colours")
    auto = colours in (None, "auto") or not isinstance(colours, dict)
    colour_map: dict[str, str] = {} if auto else dict(colours)
    order: list[str] = []
    # Only tag speakers when there is genuinely more than one; a single-speaker
    # video does not need "Name:" on every line.
    distinct = {str(c.get("speaker")) for c in cues if c.get("speaker") not in (None, "")}
    if len(distinct) < 2:
        return
    for cue in cues:
        spk = cue.get("speaker")
        if spk in (None, ""):
            continue
        key = str(spk)
        if key not in order:
            order.append(key)
        if auto and key not in colour_map:
            colour_map[key] = sty.SPEAKER_PALETTE[(len(colour_map)) % len(sty.SPEAKER_PALETTE)]
        cue.setdefault("speaker_name", names.get(key, key))
        cue.setdefault("speaker_prefix", f"{cue['speaker_name']}:")
        cue.setdefault("speaker_colour", colour_map.get(key))


def _voiced_window(
    start: float, end: float, pauses: list[tuple[float, float]] | None
) -> tuple[float, float]:
    """Trim the silence that pads a cue's [start, end] down to the interval that
    actually carries voice.

    Cue boundaries are deliberately parked *inside* pauses (a change lands in a
    breath, not on a syllable) and the first/last cue carry an extra lead-in and
    tail-hold. An even karaoke sweep spread over the whole padded span therefore
    runs slower than the real speech and the highlight trails the voice — worst
    by the end of the cue. Clamping the sweep to [voiced_start, voiced_end] makes
    the estimate track the actual speaking rate without needing word timestamps.
    """
    v_start, v_end = start, end
    for ps, pe in (pauses or []):
        if ps <= v_start < pe:      # a pause straddles the cue's start → speech begins at its end
            v_start = min(pe, end)
        if ps < v_end <= pe:        # a pause straddles the cue's end → speech ended at its start
            v_end = max(ps, start)
    if v_end - v_start < 0.05:      # degenerate (near-silent cue): keep the full span
        return start, end
    return v_start, v_end


def karaoke_units(
    cue: dict[str, Any],
    style: dict[str, Any],
    pauses: list[tuple[float, float]] | None = None,
) -> list[dict[str, Any]]:
    """Split a cue into word-by-word karaoke timing units.

    When the transcript carries real word-level timestamps, the
    highlight follows the actual voice: each word holds until the moment it is
    finished being spoken. Otherwise the cue's own duration is distributed across
    its words by the same speech-weight measure the segmenter uses
    (`display_units`). To keep that estimate honest the sweep is confined to the
    cue's voiced window (`_voiced_window` strips the leading/trailing silence the
    boundary-snapping parked inside the cue); a leading empty unit holds the
    highlight at rest until speech begins, and the trailing silence needs no unit
    because the finished sweep simply stays fully lit until the cue leaves screen.
    Each line break becomes a newline unit so the sweep respects wrapping.
    """
    words = cue.get("_words")
    if isinstance(words, list) and words:
        real = _karaoke_from_words(cue, words)
        if real:
            return real
    start = float(cue["start"])
    end = float(cue["end"])
    v_start, v_end = _voiced_window(start, end, pauses)
    lead_cs = int(round((v_start - start) * 100))
    duration_cs = max(1, int(round((v_end - v_start) * 100)))
    lines = cue.get("lines") or [cue.get("text", "")]
    tokens: list[str] = []
    for li, line in enumerate(lines):
        if li > 0:
            tokens.append("\n")
        tokens.extend(_karaoke_tokens(str(line)))
    weights = [sty.display_units(t) if t != "\n" else 0.0 for t in tokens]
    total = sum(weights) or 1.0
    units: list[dict[str, Any]] = []
    if lead_cs >= 5:  # hold the sweep at rest through a real pre-speech pause
        units.append({"text": "", "cs": lead_cs})
    spent = 0
    weighted = [(t, w) for t, w in zip(tokens, weights)]
    n_timed = sum(1 for _, w in weighted if w > 0)
    seen = 0
    for t, w in weighted:
        if t == "\n":
            units.append({"text": "\n", "cs": 0})
            continue
        seen += 1
        if seen == n_timed:
            cs = max(1, duration_cs - spent)  # last unit soaks up rounding
        else:
            cs = max(1, int(round(duration_cs * w / total)))
        spent += cs
        units.append({"text": t, "cs": cs})
    return units


def _karaoke_from_words(cue: dict[str, Any], words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Karaoke units from real word timestamps that fall inside the cue window.

    Each word's fill spans exactly its spoken interval `[start, end]`, and the
    silence between words is a *hold*: the completed highlight waits on the gap
    rather than the next word beginning to fill before it is spoken. This is the
    honest reading of the audio — the older convention (fold the gap into the
    following word's fill) made the sweep anticipate every pause, e.g. "largest"
    lit up ~0.2 s early on propy_titan cue #5. The hold is expressed as an ASS
    karaoke unit on the inter-word space (`{\\kf<gap>} `), or an empty lead-in
    unit (`{\\kf<gap>}`) where there is no space to carry it (before the first
    word, and between CJK glyphs). Words are matched to the cue by time overlap.

    The sweep must also respect the cue's line wrapping, so the units are folded
    onto `cue["lines"]` by `_fold_karaoke_lines`.
    """
    cs = float(cue["start"])
    ce = float(cue["end"])
    inside = [w for w in words if float(w["end"]) > cs + 0.01 and float(w["start"]) < ce - 0.01]
    if not inside:
        return []
    units: list[dict[str, Any]] = []
    cursor = cs
    for k, w in enumerate(inside):
        wstart = max(cs, float(w["start"]))
        wend = min(ce, float(w["end"]))
        if wend <= wstart:
            wend = min(ce, wstart + 0.01)
        gap_cs = int(round((wstart - cursor) * 100))  # silence to hold before this word
        word_cs = max(1, int(round((wend - wstart) * 100)))
        text = str(w["text"]).lstrip(" ")
        # Non-CJK words after the first are separated by a real space, which is
        # the natural carrier for the gap hold; CJK glyphs and the first word are
        # not, so the hold rides an empty lead-in unit instead.
        space_carrier = k > 0 and not sty.is_wide(text[:1] or " ")
        if space_carrier:
            units.append({"text": " ", "cs": max(1, gap_cs)})
        elif gap_cs >= 1:
            units.append({"text": "", "cs": gap_cs})
        units.append({"text": text, "cs": word_cs})
        cursor = wend
    return _fold_karaoke_lines(units, cue.get("lines") or [])


def _fold_karaoke_lines(units: list[dict[str, Any]], lines: list[Any]) -> list[dict[str, Any]]:
    """Insert newline karaoke units so a word-timed sweep breaks where the cue's
    wrapped `lines` break.

    The mapping is by visible-character count (spaces and punctuation excluded),
    which is robust to the spacing/punctuation differences between raw ASR word
    tokens and the wrapped caption text: after the running word-character count
    passes each line's length, a hard break is emitted before the next word. If
    the words do not reconstruct the lines exactly (an edited transcript), the
    count simply yields fewer breaks rather than a wrong one — never an overflow
    worse than the unbroken fallback."""
    if len(lines) <= 1:
        return units
    bounds: list[int] = []
    run = 0
    for line in lines[:-1]:
        run += sty.visible_char_count(str(line))
        bounds.append(run)
    out: list[dict[str, Any]] = []
    acc = 0
    bi = 0
    for unit in units:
        if bi < len(bounds) and acc >= bounds[bi]:
            out.append({"text": "\n", "cs": 0})
            bi += 1
            # A word that starts a new line must not carry the inter-word space
            # the previous line's flow gave it, or line 2 renders indented.
            txt = str(unit.get("text") or "")
            if txt.startswith(" "):
                unit = {**unit, "text": txt[1:]}
        out.append(unit)
        acc += sty.visible_char_count(str(unit.get("text") or ""))
    while bi < len(bounds):
        # Any line boundaries the word run never reached (rare count drift) still
        # get a break, appended in order so no two lines merge.
        out.append({"text": "\n", "cs": 0})
        bi += 1
    return out


def _karaoke_tokens(line: str) -> list[str]:
    """Highlight units within a line: whole words for space-delimited scripts,
    single glyphs for CJK, so the sweep moves the way each script reads."""
    tokens: list[str] = []
    buf = ""
    for ch in line:
        if sty.is_wide(ch):
            if buf:
                tokens.append(buf); buf = ""
            tokens.append(ch)
        elif ch.isspace():
            buf += ch
            tokens.append(buf); buf = ""
        else:
            buf += ch
    if buf:
        tokens.append(buf)
    return tokens


# --- pause detection ------------------------------------------------------

_SILENCE_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_pauses(video_path: Path, *, silence_db: float, min_silence: float) -> list[tuple[float, float]]:
    """Silence intervals in the source audio, used as legal cue-boundary slots."""
    cmd = [
        "ffmpeg", "-v", "info", "-i", str(video_path),
        # -vn: this is an audio-only scan, so do not spend time decoding video.
        "-vn",
        "-af", f"silencedetect=n={silence_db}dB:d={min_silence}",
        "-f", "null", "-",
    ]
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=900)
    except Exception:
        return []
    log = (proc.stderr or "") + (proc.stdout or "")
    starts = [float(m) for m in _SILENCE_START.findall(log)]
    ends = [float(m) for m in _SILENCE_END.findall(log)]
    pauses: list[tuple[float, float]] = []
    for idx, start in enumerate(starts):
        end = ends[idx] if idx < len(ends) else None
        if end is None or not math.isfinite(end) or end <= start:
            continue
        pauses.append((start, end))
    return pauses


def snap_to_pause(
    boundary: float,
    pauses: list[tuple[float, float]],
    window: float,
) -> tuple[float, float] | None:
    """The pause whose body is closest to `boundary`, if one is near enough."""
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


# --- transcript loading ---------------------------------------------------

def load_timed_segments(path: Path) -> list[dict[str, Any]]:
    data = load_transcript_data(path)
    segments: list[dict[str, Any]] = []
    for raw in collect_segments(data):
        text = str(raw.get("text") or raw.get("word") or raw.get("content") or "").strip()
        if not text:
            continue
        start = coerce_float(first_present(raw, ["start", "start_time", "start_seconds", "begin"]))
        end = coerce_float(first_present(raw, ["end", "end_time", "end_seconds", "finish"]))
        if start is None or end is None or end <= start:
            continue
        seg = {"start": start, "end": end, "text": text, "speaker": raw.get("speaker")}
        # Carry word-level timing when the provider gives it:
        # it lets karaoke follow the real voice instead of an even estimate.
        words = raw.get("words")
        if isinstance(words, list) and words:
            clean = []
            for w in words:
                if not isinstance(w, dict):
                    continue
                wt = str(w.get("text") or w.get("word") or "").strip()
                ws = coerce_float(first_present(w, ["start", "start_time", "begin"]))
                we = coerce_float(first_present(w, ["end", "end_time", "finish"]))
                if wt and ws is not None and we is not None and we >= ws:
                    clean.append({"text": wt, "start": ws, "end": we})
            if clean:
                seg["words"] = clean
        segments.append(seg)
    segments.sort(key=lambda s: s["start"])
    return segments


def detect_language(segments: list[dict[str, Any]]) -> str:
    sample = "".join(s["text"] for s in segments[:20])
    cjk = sum(1 for ch in sample if "一" <= ch <= "鿿")
    return "zh" if cjk >= max(4, len(sample) * 0.2) else "und"


# --- render ---------------------------------------------------------------

def subtitle_render(args: dict, ctx: RunContext) -> ToolResult:
    started = time.time()
    if not args.get("video_path"):
        return ToolResult(text="[ERROR] video_path is required")
    if not args.get("subtitles_path"):
        return ToolResult(text="[ERROR] subtitles_path is required (out/subtitles.json from subtitle_build)")
    if not shutil.which("ffmpeg"):
        return ToolResult(text="[ERROR] ffmpeg not found on PATH")
    # Fail fast: subtitle burn-in needs libass (subtitles/ass filter); minimal
    # builds drop it and only fail after reading the whole video.
    cap_err = require_ffmpeg(encoders=("libx264", "aac"), filters=("subtitles",))
    if cap_err:
        return ToolResult(text=cap_err)
    video_path = ctx.resolve(args["video_path"])
    if not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")
    subtitles_path = ctx.resolve(args["subtitles_path"])
    if not subtitles_path.is_file():
        return ToolResult(text=f"[ERROR] subtitles not found: {subtitles_path}")

    mode = str(args.get("mode") or "burn").strip().lower()
    if mode not in {"burn", "soft", "both"}:
        return ToolResult(text="[ERROR] mode must be one of: burn, soft, both")

    try:
        package = json.loads(subtitles_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] invalid subtitles JSON: {exc}")
    cues = package.get("cues")
    style = package.get("style")
    if not isinstance(cues, list) or not cues:
        return ToolResult(text="[ERROR] subtitles JSON has no cues[]")
    if not isinstance(style, dict):
        return ToolResult(text="[ERROR] subtitles JSON has no style object")

    # Re-emit the ASS from the cue list so an edited subtitles.json always wins
    # over a stale sidecar .ass file.
    ass_path = ctx.resolve(args.get("ass_path") or subtitles_path.with_suffix(".ass"))
    ass_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path.write_text(sty.build_ass(cues, style, title=video_path.stem), encoding="utf-8")

    output_path = ctx.resolve(args.get("output_path") or "out/subtitled.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    crf = int(args.get("crf") or 18)
    fonts_dir = str(Path(style["font_file"]).parent)

    outputs: dict[str, str] = {}
    if mode in {"burn", "both"}:
        vf = (
            f"ass=filename={sty.ffmpeg_filter_escape(str(ass_path))}"
            f":fontsdir={sty.ffmpeg_filter_escape(fonts_dir)}"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart",
            str(output_path),
        ]
        proc = run_ffmpeg(cmd)
        if proc is not None:
            return ToolResult(text=f"[ERROR] subtitle burn-in failed: {proc}", data={"cmd": cmd})
        outputs["burned"] = str(output_path)

    if mode in {"soft", "both"}:
        srt_path = ctx.resolve(args.get("srt_path") or subtitles_path.with_suffix(".srt"))
        srt_path.write_text(sty.build_srt(cues), encoding="utf-8")
        soft_path = output_path.with_name(output_path.stem + "_softsubs" + output_path.suffix)
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path), "-i", str(srt_path),
            "-map", "0", "-map", "1",
            "-c", "copy", "-c:s", "mov_text",
            "-metadata:s:s:0", f"language={package.get('language') or 'und'}",
            str(soft_path),
        ]
        proc = run_ffmpeg(cmd)
        if proc is not None:
            return ToolResult(text=f"[ERROR] soft subtitle mux failed: {proc}", data={"cmd": cmd})
        outputs["soft"] = str(soft_path)

    report = {
        "mode": mode,
        "source_video": str(video_path),
        "subtitles_path": str(subtitles_path),
        "subtitles_sha256": file_sha256(subtitles_path),
        "ass_path": str(ass_path),
        "cue_count": len(cues),
        "style": {k: style[k] for k in ("preset", "font_family_resolved", "font_size", "max_lines", "margin_v") if k in style},
        "outputs": outputs,
        "output_sha256": {name: file_sha256(Path(p)) for name, p in outputs.items()},
        "elapsed_seconds": round(time.time() - started, 3),
    }
    report_path = Path(str(output_path)).with_suffix(".subtitle_render_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return ToolResult(
        text=(
            f"Subtitles rendered ({mode}): " + ", ".join(f"{k}={ctx.virtualize(v)}" for k, v in outputs.items())
            + ". Run subtitle_qc on the burned output and read the evidence frames before accepting it."
        ),
        data=report,
        artifacts=[str(report_path), *outputs.values()],
        video_paths=list(outputs.values()),
    )


def run_ffmpeg(cmd: list[str]) -> str | None:
    """Run ffmpeg; return None on success or the stderr tail on failure."""
    try:
        proc = run_proc(cmd, capture_output=True, text=True, timeout=7200)
    except Exception as exc:
        return str(exc)
    if proc.returncode != 0:
        return (proc.stderr or "").strip()[-2000:] or "ffmpeg failed"
    return None


# --- QC -------------------------------------------------------------------

def subtitle_qc(args: dict, ctx: RunContext) -> ToolResult:
    """Deterministic subtitle checks plus frame evidence from the burned video.

    The checks catch what a machine can prove (overlap, overflow, reading speed,
    dropped text). The evidence frames exist because the rest — is the wording
    right, does the box cover the speaker's mouth, is it legible against this
    background — can only be settled by looking, and the agent has to look.
    """
    started = time.time()
    if not args.get("subtitles_path"):
        return ToolResult(text="[ERROR] subtitles_path is required")
    subtitles_path = ctx.resolve(args["subtitles_path"])
    if not subtitles_path.is_file():
        return ToolResult(text=f"[ERROR] subtitles not found: {subtitles_path}")
    try:
        package = json.loads(subtitles_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] invalid subtitles JSON: {exc}")
    cues = package.get("cues") or []
    style = package.get("style") or {}
    if not isinstance(cues, list) or not cues:
        return ToolResult(text="[ERROR] subtitles JSON has no cues[]")

    video_path = ctx.resolve(args["video_path"]) if args.get("video_path") else None
    if video_path is not None and not video_path.is_file():
        return ToolResult(text=f"[ERROR] video not found: {video_path}")
    video_duration = media_duration_seconds(video_path) if video_path else package.get("video", {}).get("duration")

    issues = check_cues(cues, style, video_duration)
    coverage = check_coverage(package, ctx)
    if coverage is not None:
        issues.extend(coverage["issues"])

    image_paths: list[str] = []
    frames_meta: list[dict[str, Any]] = []
    if video_path is not None:
        frames_dir = ctx.resolve(args.get("frames_dir") or f".video_agent/subtitle_qc/{video_path.stem}")
        max_frames = int(args.get("max_evidence_frames") or 12)
        image_paths, frames_meta, frame_error = sample_cue_frames(
            video_path, cues, frames_dir, max_frames=max_frames
        )
        if frame_error:
            issues.append({"severity": "error", "message": "cue evidence sampling failed", "evidence": frame_error})

    errors = [i for i in issues if i["severity"] == "error"]
    status = "fail" if errors else "pass"
    report = {
        "status": status,
        "subtitles_path": str(subtitles_path),
        "subtitles_sha256": file_sha256(subtitles_path),
        "video_path": str(video_path) if video_path else None,
        "video_sha256": file_sha256(video_path) if video_path else None,
        "cue_count": len(cues),
        "video_duration": video_duration,
        "coverage": {k: v for k, v in (coverage or {}).items() if k != "issues"},
        "issues": issues,
        "error_count": len(errors),
        "warning_count": len(issues) - len(errors),
        "evidence_frames": frames_meta,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_json = ctx.resolve(args.get("output_json") or "out/subtitle_qc_report.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = f"Subtitle QC {status}: {len(errors)} error(s), {len(issues) - len(errors)} warning(s)."
    if image_paths:
        summary += (
            f" {len(frames_meta)} of {len(cues)} cue(s) were sampled at their midpoint and tiled into "
            f"{len(image_paths)} labelled contact sheet(s). These are the only proof that the subtitle "
            "actually looks right on screen: read every sheet and, for each labelled cell, confirm the "
            "on-screen text matches the cue text in the label, is fully inside the frame, is legible "
            "against the background, and does not cover the speaker's face or any on-screen graphic."
        )
        if len(frames_meta) < len(cues):
            summary += (
                f" {len(cues) - len(frames_meta)} cue(s) were not sampled; raise max_evidence_frames "
                "to see all of them."
            )
    return ToolResult(
        text=summary + f"\nReport: {ctx.virtualize(output_json)}",
        data=report,
        artifacts=[str(output_json)],
        image_paths=image_paths,
    )


def check_cues(cues: list[dict[str, Any]], style: dict[str, Any], video_duration: float | None) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    usable = float(style.get("usable_width_px") or 0)
    max_lines = int(style.get("max_lines") or 2)
    max_cps = float(style.get("max_cps") or 9.0)
    min_duration = float(style.get("min_duration") or 0.7)
    max_duration = float(style.get("max_duration") or 6.0)
    min_gap = float(style.get("min_gap") or 0.0)

    previous: dict[str, Any] | None = None
    for cue in cues:
        idx = cue.get("index")
        start, end = coerce_float(cue.get("start")), coerce_float(cue.get("end"))
        # Annotations live on a separate top-of-frame track: they legitimately
        # overlap the dialogue below and are not bound by the caption line/width
        # budget, so they get a lighter check (valid, in-bounds times) only.
        if str(cue.get("role") or "") == "annotation":
            if start is None or end is None or end <= start:
                issues.append({"severity": "error", "cue": idx, "message": "annotation has invalid start/end"})
            elif video_duration is not None and end > float(video_duration) + 0.05:
                issues.append({"severity": "warning", "cue": idx, "message": "annotation ends after the video"})
            continue
        lines = cue.get("lines") or []
        if start is None or end is None:
            issues.append({"severity": "error", "cue": idx, "message": "cue start/end must be finite numbers"})
            continue
        if end <= start:
            issues.append({"severity": "error", "cue": idx, "message": f"cue end {end} is not after start {start}"})
        if start < 0:
            issues.append({"severity": "error", "cue": idx, "message": "cue starts before the video"})
        if video_duration is not None and end > float(video_duration) + 0.05:
            issues.append({
                "severity": "error", "cue": idx,
                "message": f"cue end {end:.3f}s exceeds video duration {float(video_duration):.3f}s",
            })
        if not any(str(line).strip() for line in lines):
            issues.append({"severity": "error", "cue": idx, "message": "cue has no visible text"})
        if len(lines) > max_lines:
            issues.append({
                "severity": "error", "cue": idx,
                "message": f"cue wraps to {len(lines)} lines but the style allows {max_lines}",
            })
        for li, line in enumerate(lines):
            measure = str(line)
            # The speaker tag is rendered ahead of the first line, so it counts
            # toward that line's width.
            if li == 0 and cue.get("speaker_prefix"):
                measure = f"{cue['speaker_prefix']} {measure}"
            width = sty.text_width_px(measure, style) * float(cue.get("font_scale") or 1.0)
            if usable and width > usable + 1.0:
                issues.append({
                    "severity": "error", "cue": idx,
                    "message": f"line overflows the safe width by {width - usable:.0f}px "
                               f"({width:.0f}px rendered vs {usable:.0f}px usable)",
                    "evidence": measure,
                })
        # Bilingual translation lines render smaller and are auto-wrapped to the
        # usable width at build/render time; QC measures those wrapped lines, so
        # it only flags a residual overflow (a single token wider than the frame).
        trans = cue.get("translation_lines")
        if trans and usable:
            tstyle, _ = sty.translation_render_style(style)
            disp = sty.translation_display_lines(cue, style)
            if len(disp) > max_lines:
                issues.append({
                    "severity": "error", "cue": idx,
                    "message": f"translation wraps to {len(disp)} lines but the style allows {max_lines}",
                })
            for line in disp:
                w = sty.text_width_px(str(line), tstyle)
                if w > usable + 1.0:
                    issues.append({
                        "severity": "error", "cue": idx,
                        "message": f"translation line overflows the safe width by {w - usable:.0f}px",
                        "evidence": str(line),
                    })
        duration = end - start
        cps = sty.estimate_cps(cue.get("text") or "".join(lines), duration)
        if cps > max_cps + 0.5:
            issues.append({
                "severity": "warning", "cue": idx,
                "message": f"reading speed {cps:.1f} chars/s exceeds the {max_cps:.1f} budget",
            })
        if duration < min_duration - 0.01:
            issues.append({
                "severity": "warning", "cue": idx,
                "message": f"cue is on screen for {duration:.2f}s, under the {min_duration:.2f}s minimum",
            })
        if duration > max_duration + 0.01:
            issues.append({
                "severity": "warning", "cue": idx,
                "message": f"cue is on screen for {duration:.2f}s, over the {max_duration:.2f}s maximum",
            })
        if previous is not None:
            prev_end = coerce_float(previous.get("end"))
            if prev_end is not None and start < prev_end:
                issues.append({
                    "severity": "error", "cue": idx,
                    "message": f"overlaps the previous cue (starts {start:.3f}s, previous ends {prev_end:.3f}s)",
                })
            elif prev_end is not None and start - prev_end < min_gap - 0.001:
                issues.append({
                    "severity": "warning", "cue": idx,
                    "message": f"gap to the previous cue is {start - prev_end:.3f}s, under the {min_gap:.3f}s minimum",
                })
        previous = cue
    return issues


def check_coverage(package: dict[str, Any], ctx: RunContext) -> dict[str, Any] | None:
    """Compare the characters on screen with the characters ASR produced, so a
    segmentation bug that silently drops speech gets caught."""
    transcript_path = package.get("transcript_path")
    if not transcript_path:
        return None
    path = ctx.resolve(str(transcript_path))
    if not path.is_file():
        return {"issues": [{"severity": "warning", "message": f"transcript missing, coverage not checked: {path}"}]}
    try:
        segments = load_timed_segments(path)
    except Exception as exc:
        return {"issues": [{"severity": "warning", "message": f"coverage check failed: {exc}"}]}
    transcript_chars = sum(sty.visible_char_count(s["text"]) for s in segments)
    cue_chars = sum(sty.visible_char_count(c.get("text") or "") for c in package.get("cues") or [])
    ratio = (cue_chars / transcript_chars) if transcript_chars else 1.0
    issues: list[dict[str, Any]] = []
    if transcript_chars and ratio < 0.98:
        issues.append({
            "severity": "error",
            "message": f"subtitles carry {cue_chars} of {transcript_chars} transcript characters "
                       f"({ratio:.1%}); speech was dropped during segmentation",
        })
    elif transcript_chars and ratio > 1.02:
        issues.append({
            "severity": "warning",
            "message": f"subtitles carry more characters ({cue_chars}) than the transcript ({transcript_chars}); "
                       "text may be duplicated across cues",
        })
    return {
        "transcript_chars": transcript_chars,
        "cue_chars": cue_chars,
        "ratio": round(ratio, 4),
        "issues": issues,
    }


def sample_cue_frames(
    video_path: Path,
    cues: list[dict[str, Any]],
    frames_dir: Path,
    *,
    max_frames: int,
) -> tuple[list[str], list[dict[str, Any]], str]:
    """Grab one frame at the midpoint of evenly spread cues and tile them."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    for stale in frames_dir.glob("cue_*.jpg"):
        stale.unlink()
    for stale in frames_dir.glob("sheet_*.jpg"):
        stale.unlink()

    picks = evenly_spaced(cues, max_frames)
    saved: list[tuple[dict[str, Any], Path]] = []
    for cue in picks:
        start, end = coerce_float(cue.get("start")), coerce_float(cue.get("end"))
        if start is None or end is None or end <= start:
            continue
        midpoint = start + (end - start) * 0.5
        frame_path = frames_dir / f"cue_{int(cue.get('index') or 0):04d}.jpg"
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-ss", f"{midpoint:.3f}", "-i", str(video_path),
            "-frames:v", "1", "-q:v", "3", str(frame_path),
        ]
        error = run_ffmpeg(cmd)
        if error or not frame_path.is_file():
            return [], [], error or f"no frame produced at {midpoint:.3f}s"
        saved.append((cue, frame_path))
    if not saved:
        return [], [], "no cue produced a sampleable timestamp"

    sheets = build_cue_sheets(saved, frames_dir)
    meta = [
        {
            "cue": cue.get("index"),
            "timestamp": round(float(cue["start"]) + (float(cue["end"]) - float(cue["start"])) * 0.5, 3),
            "expected_text": cue.get("text"),
            "frame": str(path),
        }
        for cue, path in saved
    ]
    return [str(p) for p in sheets], meta, ""


def evenly_spaced(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if count <= 0 or not items:
        return []
    if len(items) <= count:
        return list(items)
    step = len(items) / count
    return [items[min(len(items) - 1, int(i * step))] for i in range(count)]


def build_cue_sheets(saved: list[tuple[dict[str, Any], Path]], out_dir: Path) -> list[Path]:
    """Tile cue frames into labelled contact sheets, one row per few cues.

    The label carries the cue index and the text we *expect* to see, so reading
    the sheet is a direct comparison rather than a memory exercise.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return [path for _, path in saved]

    cols = 3
    cell_w = 460
    label_h = 46
    sheet_max_cells = 9
    font = _label_font(18)
    sheets: list[Path] = []
    for sheet_index in range(0, len(saved), sheet_max_cells):
        chunk = saved[sheet_index:sheet_index + sheet_max_cells]
        thumbs = []
        for cue, path in chunk:
            try:
                img = Image.open(path).convert("RGB")
            except Exception:
                continue
            ratio = cell_w / img.width
            img = img.resize((cell_w, max(1, int(img.height * ratio))), Image.LANCZOS)
            thumbs.append((cue, img))
        if not thumbs:
            continue
        cell_h = max(img.height for _, img in thumbs) + label_h
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (18, 18, 18))
        draw = ImageDraw.Draw(sheet)
        for pos, (cue, img) in enumerate(thumbs):
            col, row = pos % cols, pos // cols
            x, y = col * cell_w, row * cell_h
            sheet.paste(img, (x, y + label_h))
            midpoint = float(cue["start"]) + (float(cue["end"]) - float(cue["start"])) * 0.5
            label = f"#{cue.get('index')} @{midpoint:.2f}s  {cue.get('text') or ''}"
            draw.text((x + 8, y + 8), label[:64], fill=(255, 235, 120), font=font)
        sheet_path = out_dir / f"sheet_{sheet_index // sheet_max_cells:02d}.jpg"
        sheet.save(sheet_path, quality=88)
        sheets.append(sheet_path)
    return sheets


def _label_font(size: int):
    from PIL import ImageFont

    candidate = sty.resolve_font_file("Noto Sans SC", "regular")
    if candidate:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()


# --- shared helpers -------------------------------------------------------

def probe_video_size(source: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(source),
    ]
    proc = run_proc(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ffprobe failed for {source}")
    try:
        stream = (json.loads(proc.stdout).get("streams") or [])[0]
        width, height = int(stream["width"]), int(stream["height"])
    except Exception as exc:
        raise RuntimeError(f"invalid ffprobe size metadata for {source}") from exc
    if width <= 0 or height <= 0:
        raise RuntimeError(f"invalid video size for {source}: {width}x{height}")
    return width, height


def coerce_number(value: object, default: float) -> float:
    if isinstance(value, bool) or value is None:
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def coerce_positive(value: object, default: float) -> float:
    parsed = coerce_number(value, default)
    return parsed if parsed > 0 else default


def cue_stats(
    cues: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    style: dict[str, Any],
    duration: float,
) -> dict[str, Any]:
    cps_values = [c["cps"] for c in cues if math.isfinite(c["cps"])]
    durations = [c["duration"] for c in cues]
    internal = sum(1 for c in cues if not c.get("is_segment_start"))
    snapped = sum(1 for c in cues if c.get("snapped_start"))
    on_screen = sum(durations)
    return {
        "cue_count": len(cues),
        "segment_count": len(segments),
        "internal_boundaries": internal,
        "snapped_boundaries": snapped,
        "max_cps": round(max(cps_values), 2) if cps_values else 0.0,
        "mean_cps": round(sum(cps_values) / len(cps_values), 2) if cps_values else 0.0,
        "min_duration": round(min(durations), 2) if durations else 0.0,
        "max_duration": round(max(durations), 2) if durations else 0.0,
        "mean_duration": round(sum(durations) / len(durations), 2) if durations else 0.0,
        "screen_coverage": round(on_screen / duration, 3) if duration else 0.0,
        "multi_line_cues": sum(1 for c in cues if len(c["lines"]) > 1),
        "widest_line_px": round(max((c["widest_line_px"] for c in cues), default=0.0), 1),
        "usable_width_px": style["usable_width_px"],
    }


def cue_table(cues: list[dict[str, Any]], limit: int = 80) -> str:
    rows = ["idx  start     end       dur   cps   text"]
    for cue in cues[:limit]:
        text = " / ".join(cue["lines"])
        rows.append(
            f"{cue['index']:>3}  {cue['start']:>7.2f}  {cue['end']:>7.2f}  "
            f"{cue['duration']:>4.2f}  {cue['cps']:>4.1f}  {text}"
        )
    if len(cues) > limit:
        rows.append(f"... {len(cues) - limit} more cues in the JSON package")
    return "\n".join(rows)
