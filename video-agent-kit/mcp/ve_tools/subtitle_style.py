"""Subtitle style presets, font resolution, text measurement and ASS emission.

Everything here is deterministic and font-aware: cue widths are measured in real
pixels with the same font file libass will use at render time, so the segmenter
and the QC check agree with what actually lands on the frame. Falling back to
character counting is only a last resort when Pillow cannot open the font.
"""
from __future__ import annotations

import functools
import math
import re
import shutil
import subprocess
from .ffproc import run_proc
import unicodedata
from pathlib import Path
from typing import Any

from .fonts import covers_cjk, family_of_file, find_cjk_font, override_dirs

# Preset defaults are expressed as ratios of the video height/width so one
# preset works for 1080x1920 shorts and 1920x1080 landscape alike.
PRESETS: dict[str, dict[str, Any]] = {
    # Vertical short-form look: one big bold line hugging the lower third,
    # punctuation stripped, sized so a phrase is readable on a phone.
    "shortform_zh": {
        "font_family": "Noto Sans SC",
        "font_weight": "bold",
        "font_size_ratio": 0.0330,
        "bold": True,
        "primary_colour": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "back_colour": "&H80000000",
        "border_style": 1,
        "outline_ratio": 0.0028,
        "shadow_ratio": 0.0012,
        "alignment": 2,
        "margin_h_ratio": 0.060,
        "margin_v_ratio": 0.150,
        "max_lines": 1,
        "max_cps": 9.0,
        "target_fill": 0.86,
        "min_duration": 0.70,
        "max_duration": 5.0,
        "min_gap": 0.06,
        "strip_end_punctuation": True,
        "keep_inner_punctuation": False,
        "shrink_floor": 0.90,
        "max_chars_per_line": 18,
    },
    # Conventional two-line broadcast/OTT subtitle: smaller, centred low,
    # punctuation preserved, stricter reading-speed budget.
    "broadcast": {
        "font_family": "Noto Sans SC",
        "font_weight": "medium",
        "font_size_ratio": 0.0260,
        "bold": False,
        "primary_colour": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "back_colour": "&H80000000",
        "border_style": 1,
        "outline_ratio": 0.0020,
        "shadow_ratio": 0.0010,
        "alignment": 2,
        "margin_h_ratio": 0.070,
        "margin_v_ratio": 0.055,
        "max_lines": 2,
        "max_cps": 9.0,
        "target_fill": 0.90,
        "min_duration": 0.85,
        "max_duration": 6.0,
        "min_gap": 0.08,
        "strip_end_punctuation": False,
        "keep_inner_punctuation": True,
        "shrink_floor": 1.0,
        "max_chars_per_line": 20,
    },
    # Latin-script two-line subtitle. The differences from `broadcast` are not
    # cosmetic: English reads far faster per character than Chinese (~14
    # non-space chars/s vs ~9) and a line is capped by *character count* long
    # before it is capped by pixel width — a 1920 px frame would otherwise fit
    # over a hundred characters on one unreadable line.
    "broadcast_en": {
        "font_family": "Noto Sans SC",
        "font_weight": "medium",
        "font_size_ratio": 0.0380,
        "bold": False,
        "primary_colour": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "back_colour": "&H80000000",
        "border_style": 1,
        "outline_ratio": 0.0022,
        "shadow_ratio": 0.0010,
        "alignment": 2,
        "margin_h_ratio": 0.100,
        "margin_v_ratio": 0.070,
        "max_lines": 2,
        "max_cps": 14.0,
        "target_fill": 0.88,
        "min_duration": 0.85,
        "max_duration": 6.0,
        "min_gap": 0.08,
        "strip_end_punctuation": False,
        "keep_inner_punctuation": True,
        "shrink_floor": 1.0,
        "max_chars_per_line": 42,
    },
}
DEFAULT_PRESET = "shortform_zh"

# Style keys a caller may override individually on top of a preset.
OVERRIDABLE = set(PRESETS[DEFAULT_PRESET]) | {
    "font_file",
    "font_size",
    "outline",
    "shadow",
    "margin_l",
    "margin_r",
    "margin_v",
    "readability",
    # --- advanced features (all off by default, backward compatible) ---
    "karaoke",              # bool: sweep each cue's text word-by-word as it is spoken
    "karaoke_sung_colour",  # ASS &HAABBGGRR of already-spoken text
    "karaoke_unsung_colour",# ASS colour of not-yet-spoken text
    "speaker_labels",       # bool: prefix each cue with its speaker's name/label
    "speaker_colours",      # dict speaker-key -> ASS colour, or "auto"
    "bilingual_scale",      # float: translation line size relative to the caption
    "bilingual_colour",     # ASS colour of the translation line
    "annotation_scale",     # float: note size relative to the caption
    "annotation_colour",    # ASS colour of the explanatory note text
}

# A colourblind-safe, high-contrast palette assigned to speakers in first-seen
# order when speaker_colours="auto". Values are ASS &HBBGGRR (no alpha = opaque).
SPEAKER_PALETTE = [
    "&H00FFFFFF",  # white
    "&H0066D9FF",  # amber
    "&H0080FF80",  # green
    "&H00FF9E6E",  # sky blue
    "&H00C0A0FF",  # pink
    "&H00E0E000",  # cyan
]

# `readability` is a one-word macro for the contrast treatment behind the text.
# It exists because a good box needs four coordinated ASS fields (border style,
# a semi-transparent outline colour, box padding scaled to the font, and the
# drop shadow turned off); a caller who sets only border_style=3 gets a heavy,
# cramped, fully-opaque slab. Naming the treatment lets subtitle_scout recommend
# it as one value and keeps the four fields consistent. Any field the caller
# also sets explicitly still wins over the macro.
READABILITY_MODES = ("outline", "heavy_outline", "box", "opaque_box")

# Weight name -> the font files we ship/expect, best match first.
_FONT_FILE_HINTS = {
    "black": ["NotoSansSC-900.ttf"],
    "bold": ["NotoSansSC-700.ttf"],
    "medium": ["NotoSansSC-500.ttf"],
    "regular": ["NotoSansSC-400.ttf", "PingFang.ttf"],
}
# Dirs the shipped weights live in on the Linux images. Everything else
# (VE_FONT_DIRS, the platform's own font dirs) is handled by `fonts.py` —
# see resolve_font_file for why the order below is kept as-is.
_FONT_DIRS = [Path("/root/.fonts"), Path("/usr/share/fonts")]


STRONG_PUNCT = "。！？!?…."
WEAK_PUNCT = "，、；：,;:—～~"
CLOSING_PUNCT = "”’）】》」』)]}"
ALL_PUNCT = STRONG_PUNCT + WEAK_PUNCT + CLOSING_PUNCT + "“‘（【《「『([{\"'"


def resolve_style(
    preset_name: str | None,
    overrides: dict[str, Any] | None,
    *,
    video_width: int,
    video_height: int,
) -> dict[str, Any]:
    """Merge preset + overrides and turn every ratio into an absolute pixel
    value against the real video size."""
    name = (preset_name or DEFAULT_PRESET).strip()
    if name not in PRESETS:
        raise ValueError(f"unknown subtitle preset: {name!r} (known: {sorted(PRESETS)})")
    style: dict[str, Any] = {"preset": name, **PRESETS[name]}
    explicit: set[str] = set()
    for key, value in (overrides or {}).items():
        if key not in OVERRIDABLE:
            raise ValueError(f"unknown style override: {key!r}")
        if value is not None:
            style[key] = value
            explicit.add(key)

    readability = style.get("readability")
    if readability is not None and str(readability) not in READABILITY_MODES:
        raise ValueError(
            f"unknown readability mode: {readability!r} (known: {list(READABILITY_MODES)})"
        )

    # Ratios resolve against height so the look is resolution-independent;
    # explicit absolute overrides always win.
    style.setdefault("font_size", max(12, round(video_height * float(style["font_size_ratio"]))))
    style.setdefault("outline", round(video_height * float(style["outline_ratio"]), 2))
    style.setdefault("shadow", round(video_height * float(style["shadow_ratio"]), 2))
    margin_h = round(video_width * float(style["margin_h_ratio"]))
    style.setdefault("margin_l", margin_h)
    style.setdefault("margin_r", margin_h)
    style.setdefault("margin_v", round(video_height * float(style["margin_v_ratio"])))

    # The readability macro runs after font_size exists (box padding scales to it)
    # but only fills fields the caller did not set by hand.
    _apply_readability(style, explicit)

    style["font_size"] = int(style["font_size"])
    style["outline"] = float(style["outline"])
    style["shadow"] = float(style["shadow"])
    for key in ("margin_l", "margin_r", "margin_v"):
        style[key] = int(style[key])
    style["max_lines"] = int(style["max_lines"])
    style["max_chars_per_line"] = int(style.get("max_chars_per_line") or 0)

    font_file = style.get("font_file") or resolve_font_file(style["font_family"], style.get("font_weight"))
    if not font_file:
        raise ValueError(
            f"no font file found for family {style['font_family']!r}; "
            "install a CJK font or pass style.font_file explicitly"
        )
    style["font_file"] = str(font_file)
    style["font_family_resolved"] = font_family_of(Path(font_file)) or style["font_family"]
    style["video_width"] = int(video_width)
    style["video_height"] = int(video_height)
    # Horizontal room a line may occupy before it collides with the margins.
    style["usable_width_px"] = max(1, int(video_width) - style["margin_l"] - style["margin_r"])
    return style


def _apply_readability(style: dict[str, Any], explicit: set[str]) -> None:
    """Expand the `readability` macro into the concrete ASS contrast fields.

    Only fills a field the caller did not set by hand (tracked in `explicit`), so
    `{"readability":"box","outline":12}` yields a box with 12px padding, and a
    plain `border_style` override is never silently overwritten. `outline` here is
    box padding (BorderStyle 3 draws the fill in OutlineColour, `Outline` px of
    padding around the glyphs); the shadow is dropped so no BackColour slab trails
    the box.
    """
    mode = str(style.get("readability") or "outline")
    if mode == "outline":
        return
    font_size = float(style["font_size"])

    def put(key: str, value: Any) -> None:
        if key not in explicit:
            style[key] = value

    if mode in ("box", "opaque_box"):
        # Draw a clean vector rectangle behind the text (see _band_dialogue),
        # NOT BorderStyle 3: libass's BorderStyle-3 box hugs each glyph outline,
        # so the band's edges come out ragged/uneven (a notch at the right end,
        # wavy top where ascenders vary), which reads as "the black box looks
        # broken". A pixel-sized drawn rectangle is perfectly even every time.
        # The text keeps a thin outline (BorderStyle 1) so it stays crisp on the
        # band, and the drop shadow is dropped so nothing trails the box.
        put("border_style", 1)
        put("outline", max(1.5, round(font_size * 0.05, 2)))
        put("shadow", 0.0)
        # Band fill: semi-transparent black for `box` (footage reads through),
        # solid black for `opaque_box`. Consumed by _band_dialogue in build_ass.
        style["readability_band"] = "&H000000&"  # BGR black
        style["readability_band_alpha"] = "&H00&" if mode == "opaque_box" else "&H40&"
        put("outline_colour", "&H00000000")
    elif mode == "heavy_outline":
        # Keep the clean outline look but thicken the rim and add a shadow floor
        # so a white glyph never floats free on a mid-bright band.
        put("outline", round(float(style["outline"]) * 1.6, 2))
        put("shadow", round(max(float(style["shadow"]), font_size * 0.03), 2))


def resolve_font_file(family: str, weight: str | None = None) -> str | None:
    """Locate a concrete font file: shipped weight hints first (so we pick the
    intended weight rather than whatever fontconfig aliases to), then fc-match,
    then the platform's own CJK faces.

    The last step is what makes this work off Linux: macOS only has fontconfig
    if the user installed it, Windows never does, and both ship a perfectly good
    CJK font that the first two steps cannot see. Order is deliberate — an
    already-provisioned Linux box still resolves through the hints/fc-match it
    always did, so measured line breaks do not shift under existing traces.
    """
    for name in _FONT_FILE_HINTS.get((weight or "regular").lower(), []):
        for directory in [*override_dirs(), *_FONT_DIRS]:
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)
    if shutil.which("fc-match"):
        query = f"{family}:weight={weight}" if weight else family
        try:
            proc = run_proc(
                ["fc-match", "-f", "%{file}", query], capture_output=True, text=True, timeout=15
            )
            path = proc.stdout.strip()
        except Exception:
            path = ""
        # fc-match never fails: ask for an uninstalled Chinese family and it
        # hands back DejaVu Sans, which has no CJK glyphs at all. Every preset
        # here is a Chinese subtitle preset, so a zero-CJK answer is not an
        # answer — take a real CJK face over it when the machine has one.
        # (`uncovered_characters` would still catch this later, but only as a
        # hard failure at build time, which is not a better outcome.)
        if path and Path(path).is_file():
            if covers_cjk(path) is not False:
                return path
            fallback = find_cjk_font(weight or "regular")
            return fallback or path
    return find_cjk_font(weight or "regular")


def font_family_of(font_file: Path) -> str | None:
    """Family name libass should be asked for, for this file.

    Goes into the ASS `Style:` line verbatim, so it has to be *one* family:
    `fc-scan` applies the format once per face, and a `.ttc` collection has
    several (PingFang.ttc, uming.ttc, msyh.ttc are all collections), which
    without a separator comes back as "AR PL UMing CNAR PL UMing HK…" —
    a name that resolves to nothing and silently renders in libass's default
    font. Hence the `\\n` and taking the first line.

    Falls back to the filename→family map when there is no fontconfig at all
    (Windows, bare macOS); returning None there would leave the caller asking
    libass for the preset's `Noto Sans SC`, which is not installed on those
    machines either.
    """
    if shutil.which("fc-scan"):
        try:
            proc = run_proc(
                ["fc-scan", "-f", "%{family[0]}\\n", str(font_file)],
                capture_output=True, text=True, timeout=15,
            )
            first = next((ln.strip() for ln in proc.stdout.splitlines() if ln.strip()), "")
        except Exception:
            first = ""
        if first:
            return first
    return family_of_file(font_file)


@functools.lru_cache(maxsize=16)
def _pil_font(font_file: str, size: int):
    try:
        from PIL import ImageFont

        return ImageFont.truetype(font_file, size)
    except Exception:
        return None


def text_width_px(text: str, style: dict[str, Any]) -> float:
    """Rendered width of one line in pixels, including the outline that libass
    draws outside the glyph box on both sides."""
    if not text:
        return 0.0
    font = _pil_font(str(style["font_file"]), int(style["font_size"]))
    if font is not None:
        try:
            glyph_width = float(font.getlength(text))
        except Exception:
            glyph_width = _fallback_width(text, style)
    else:
        glyph_width = _fallback_width(text, style)
    return glyph_width + 2.0 * float(style.get("outline") or 0.0)


def _fallback_width(text: str, style: dict[str, Any]) -> float:
    """Font-free estimate: full-width glyphs occupy one em, the rest ~half."""
    size = float(style["font_size"])
    return sum(size if is_wide(ch) else size * 0.52 for ch in text)


def is_wide(ch: str) -> bool:
    return unicodedata.east_asian_width(ch) in ("W", "F")


def display_units(text: str) -> float:
    """Speech-time weight of a string. CJK glyphs are roughly one syllable each;
    Latin letters are much faster per character; punctuation carries no speech
    but does buy a small pause."""
    total = 0.0
    for ch in text:
        if ch in ALL_PUNCT:
            total += 0.35
        elif is_wide(ch):
            total += 1.0
        elif ch.isspace():
            total += 0.15
        else:
            total += 0.38
    return total


def visible_char_count(text: str) -> int:
    return sum(1 for ch in text if not ch.isspace() and ch not in ALL_PUNCT)


# --- ASS emission ---------------------------------------------------------

def ass_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    centis = int(round(seconds * 100))
    hours, rest = divmod(centis, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, cs = divmod(rest, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    """Escape dialogue text: braces start override blocks, backslashes start
    escape codes, and a leading space would be swallowed."""
    text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    text = text.replace("\r", "").replace("\n", "\\N")
    if text.startswith(" "):
        text = "\\h" + text[1:]
    return text


def build_ass(cues: list[dict[str, Any]], style: dict[str, Any], *, title: str = "video-agent-kit") -> str:
    """Emit an ASS file for the cue list.

    A cue is a dict with `lines` (list of strings) plus `start`/`end`. Beyond
    that, four optional groups of fields unlock the advanced looks, and every
    one of them is ignored when absent, so a plain caption cue renders exactly
    as before:

    - `role: "annotation"` renders under a separate top-of-frame Note style
      instead of the bottom caption style — used for glossary / context notes.
    - `speaker_prefix` / `speaker_colour` prepend a name tag and tint the cue,
      for multi-speaker dialogue.
    - `translation_lines` render a second, smaller block under the caption, for
      bilingual subtitles that stay locked to the same time window. Each line is
      wrapped to the usable width at word boundaries (measured at the smaller
      translation font, capped at the caption's max_lines) by
      `translation_display_lines`, so a long translation reflows instead of
      overflowing the frame.
    - `karaoke` (a list of {text, cs}) sweeps the cue word-by-word as it is
      spoken, using the Karaoke style's two colours.
    """
    bold = -1 if style.get("bold") else 0
    karaoke_on = bool(style.get("karaoke"))
    sung = style.get("karaoke_sung_colour") or style.get("primary_colour") or "&H00FFFFFF"
    unsung = style.get("karaoke_unsung_colour") or "&H00B0B0B0"

    # Caption style is the baseline. When karaoke is on, PrimaryColour is the
    # "sung" colour and SecondaryColour the "unsung" one, which is what the ASS
    # \kf sweep interpolates between; otherwise both equal the fill colour.
    primary = sung if karaoke_on else style["primary_colour"]
    secondary = unsung if karaoke_on else style["primary_colour"]

    # A top-anchored Note style for annotations: smaller, tinted, its own box so
    # it never blends into the dialogue at the bottom.
    note_size = max(10, round(int(style["font_size"]) * float(style.get("annotation_scale") or 0.62)))
    note_colour = style.get("annotation_colour") or "&H0066D9FF"  # amber
    note_margin_v = max(int(style["video_height"] * 0.045), 20)

    header = f"""[Script Info]
Title: {title}
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {style['video_width']}
PlayResY: {style['video_height']}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['font_family_resolved']},{style['font_size']},{primary},{secondary},{style['outline_colour']},{style['back_colour']},{bold},0,0,0,100,100,0,0,{style['border_style']},{style['outline']},{style['shadow']},{style['alignment']},{style['margin_l']},{style['margin_r']},{style['margin_v']},1
Style: Note,{style['font_family_resolved']},{note_size},{note_colour},{note_colour},&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,{max(3, round(note_size*0.18))},0,8,{style['margin_l']},{style['margin_r']},{note_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for cue in cues:
        band = _band_dialogue(cue, style) if style.get("readability_band") and str(cue.get("role") or "") != "annotation" else None
        if band:
            lines.append(band)
        lines.append(_dialogue_line(cue, style, karaoke_on))
    return "\n".join(lines) + "\n"


def _band_dialogue(cue: dict[str, Any], style: dict[str, Any]) -> str | None:
    """A Layer-0 filled rectangle behind one caption cue.

    Sized to the widest rendered line (caption + speaker tag, plus any
    translation block at its smaller size) with padding, and positioned to sit
    exactly under the text that alignment 2 (bottom-centre) will place at
    MarginV. Drawn with ASS vector graphics so the edges are always a clean
    rectangle — unlike BorderStyle 3, which hugs the glyphs and looks ragged.
    """
    caption_lines = _as_lines(cue)
    if not any(str(l).strip() for l in caption_lines):
        return None
    fs = int(style["font_size"])
    scale = float(cue.get("font_scale") or 1.0)

    # Widest caption line in pixels (speaker tag rides the first line).
    widths = []
    for i, line in enumerate(caption_lines):
        measure = str(line)
        if i == 0 and cue.get("speaker_prefix"):
            measure = f"{cue['speaker_prefix']} {measure}"
        widths.append(text_width_px(measure, style) * scale)
    n_lines = len(caption_lines)
    line_h = fs * 1.25

    # Translation block, if any, is rendered smaller directly under the caption.
    trans = cue.get("translation_lines")
    if trans:
        tscale = float(style.get("bilingual_scale") or 0.78)
        tsize = max(8, round(fs * tscale))
        tstyle = {**style, "font_size": tsize}
        for line in trans:
            widths.append(text_width_px(str(line), tstyle))
        n_lines += len(trans)
        block_h = line_h * len(caption_lines) + tsize * 1.25 * len(trans)
    else:
        block_h = line_h * n_lines

    pad_x = max(10.0, fs * 0.45)
    pad_y = max(6.0, fs * 0.28)
    box_w = max(widths) + 2 * pad_x

    # Co-anchor the band with the text instead of computing an absolute \pos:
    # both this Dialogue and the caption use the Default style's alignment 2
    # (bottom-centre) and MarginV, so their bottom-centre anchor points are
    # identical. Drawing upward from that shared anchor guarantees the box lands
    # exactly behind the text regardless of libass's exact line-height maths.
    # In ASS drawing space +y is downward, so the box floor sits pad_y *below*
    # the anchor and its ceiling block_h+pad_y *above* it.
    #
    # x MUST start at 0, never at -box_w/2. libass sizes a drawing's layout box
    # from the path bounding box, but then puts the path *origin* at that box's
    # left edge — so every negative x escapes to the left and the whole band
    # shifts by |min_x|. With the symmetric form the band ended up half a box
    # left of the text ("a black slab hanging off the left"), its right edge
    # cutting through the middle of the caption. Measured on a grey plate at
    # 854x480, box_w=320: symmetric -> x 107..426 (centre 266.5); this form ->
    # x 267..586 (centre 426.5, frame centre 427). y is unaffected either way.
    floor = pad_y
    ceil = -(block_h + pad_y)
    draw = f"m 0 {floor:.0f} l {box_w:.0f} {floor:.0f} {box_w:.0f} {ceil:.0f} 0 {ceil:.0f}"
    band = style["readability_band"]
    alpha = style.get("readability_band_alpha") or "&H40&"
    override = "{\\an2\\bord0\\shad0\\1c%s\\1a%s\\p1}" % (band, alpha)
    return f"Dialogue: 0,{ass_timestamp(cue['start'])},{ass_timestamp(cue['end'])},Default,,0,0,0,,{override}{draw}{{\\p0}}"


def _dialogue_line(cue: dict[str, Any], style: dict[str, Any], karaoke_on: bool) -> str:
    start, end = ass_timestamp(cue["start"]), ass_timestamp(cue["end"])
    if str(cue.get("role") or "") == "annotation":
        body = ass_escape("\n".join(_as_lines(cue)))
        return f"Dialogue: 0,{start},{end},Note,,0,0,0,,{body}"

    caption_lines = _as_lines(cue)
    # Karaoke sweep replaces the plain caption text when timing units are present.
    if karaoke_on and cue.get("karaoke"):
        text = _karaoke_text(cue["karaoke"])
    else:
        text = ass_escape("\n".join(caption_lines))

    prefix = ""
    # Per-cue horizontal condense so a whole phrase fits without being split.
    scale = float(cue.get("font_scale") or 1.0)
    if scale < 0.999:
        prefix += "{\\fscx%d}" % round(scale * 100)
    # Speaker tint applies to the whole cue (prefix + words).
    colour = cue.get("speaker_colour")
    if colour:
        prefix += "{\\c%s}" % colour
    # Speaker name tag, rendered bold ahead of the words.
    tag = str(cue.get("speaker_prefix") or "").strip()
    if tag:
        text = "{\\b1}" + ass_escape(tag + " ") + "{\\b0}" + text

    # Bilingual second block: smaller, dimmer, on the same time window so it is
    # always in sync with the caption above it.
    trans = cue.get("translation_lines")
    if trans:
        _, tsize = translation_render_style(style)
        tcolour = style.get("bilingual_colour") or "&H00D8D8D8"
        # Reflow the translation to the usable width at the smaller font before
        # emitting, so a line the model left too long wraps at a word boundary
        # instead of overflowing the frame (see translation_display_lines).
        disp = translation_display_lines(cue, style)
        # Escape each line, then join with the literal \N override. (Escaping a
        # string that already contains \N would double the backslash and print a
        # stray "\" on screen.)
        block = "\\N".join(ass_escape(str(l)) for l in disp)
        text = text + "\\N" + "{\\fs%d\\c%s}" % (tsize, tcolour) + block

    return f"Dialogue: 0,{start},{end},Default,,0,0,0,,{prefix}{text}"


def _as_lines(cue: dict[str, Any]) -> list[str]:
    lines = cue.get("lines")
    if isinstance(lines, list) and lines:
        return [str(l) for l in lines]
    return [str(cue.get("text") or "")]


def _karaoke_text(units: list[dict[str, Any]]) -> str:
    """Build the `{\\kf<cs>}word` run for a karaoke sweep. Each unit is
    {"text":..,"cs":centiseconds}; a newline unit becomes a hard line break."""
    out = []
    for u in units:
        piece = str(u.get("text") or "")
        if piece == "\n":
            out.append("\\N")
            continue
        cs = max(1, int(round(float(u.get("cs") or 0))))
        out.append("{\\kf%d}%s" % (cs, ass_escape(piece)))
    return "".join(out)


def srt_timestamp(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    millis = int(round(seconds * 1000))
    hours, rest = divmod(millis, 3600000)
    minutes, rest = divmod(rest, 60000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_srt(cues: list[dict[str, Any]]) -> str:
    """Plain SRT: no colour/karaoke (SRT cannot express them), but the speaker
    tag and the translation line are kept as plain text so the sidecar is still
    a faithful readable transcript."""
    blocks = []
    idx = 0
    for cue in cues:
        if str(cue.get("role") or "") == "annotation":
            continue  # notes are an on-screen overlay, not part of the dialogue track
        idx += 1
        body_lines = _as_lines(cue)
        tag = str(cue.get("speaker_prefix") or "").strip()
        if tag and body_lines:
            body_lines = [f"{tag} {body_lines[0]}"] + body_lines[1:]
        if cue.get("translation_lines"):
            body_lines = body_lines + [str(l) for l in cue["translation_lines"]]
        body = "\n".join(body_lines)
        blocks.append(f"{idx}\n{srt_timestamp(cue['start'])} --> {srt_timestamp(cue['end'])}\n{body}\n")
    return "\n".join(blocks)


def ffmpeg_filter_escape(path: str) -> str:
    """Escape a path for use as an ffmpeg filter argument value."""
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


@functools.lru_cache(maxsize=8)
def _font_charset(font_file: str) -> frozenset[int] | None:
    """Codepoints the font actually has glyphs for, read from its cmap. None
    when the font cannot be parsed, in which case coverage is simply unknown."""
    try:
        from fontTools.ttLib import TTFont

        with TTFont(font_file, fontNumber=0, lazy=True) as font:
            return frozenset(font.getBestCmap())
    except Exception:
        return None


def uncovered_characters(text: str, style: dict[str, Any], limit: int = 12) -> list[str]:
    """Characters the resolved font has no glyph for.

    This check exists because `fc-match` never fails: ask it for a Chinese
    family that is not installed and it cheerfully returns DejaVu Sans, which
    has no CJK glyphs at all. libass then renders blanks or tofu boxes and the
    burn-in *succeeds* — a silent, total failure. Reading the font's cmap
    catches it before we encode anything.
    """
    charset = _font_charset(str(style["font_file"]))
    if charset is None:
        return []
    missing: list[str] = []
    seen: set[str] = set()
    for ch in text:
        if ch in seen or ch.isspace():
            continue
        seen.add(ch)
        if ord(ch) not in charset:
            missing.append(ch)
        if len(missing) >= limit:
            break
    return missing


def normalize_asr_text(text: str) -> str:
    """Whitespace normalisation only. Punctuation is deliberately kept:
    it is the strongest signal we have about where a cue may end, and it must
    survive until after segmentation. Use `to_display_text` for what the viewer
    actually sees.

    Note this does *not* run NFKC. NFKC folds the full-width CJK marks ，。！？
    onto their ASCII counterparts, which is simply wrong typography in a Chinese
    subtitle — the half-width comma sits on the baseline with no ideographic
    spacing around it.
    """
    text = str(text or "").replace("　", " ").replace("﻿", "").strip()
    # ASR often emits a space between CJK glyphs; it reads as a typo on screen.
    text = re.sub(r"(?<=[㐀-鿿])\s+(?=[㐀-鿿])", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def to_display_text(text: str, style: dict[str, Any]) -> str:
    """Turn a piece of transcript into what is drawn on the frame."""
    if not style.get("keep_inner_punctuation"):
        # Short-form captions drop commas; a thin gap reads better than the mark.
        text = re.sub(f"[{re.escape(WEAK_PUNCT)}]", " ", text)
        text = re.sub(r"\s{2,}", " ", text)
    if style.get("strip_end_punctuation"):
        text = re.sub(f"[{re.escape(STRONG_PUNCT)}]", " ", text)
        text = re.sub(r"\s{2,}", " ", text)
    return text


# Part-of-speech prefixes a cue or line must not end on. A conjunction,
# preposition, particle, adverb, numeral or classifier binds forward to the word
# it governs, so breaking after one strands it: "心思和 / 精力" and "相对 / 低一
# 级别" are both wrong even though jieba considers them word boundaries.
TRAILING_TABOO_POS = ("c", "p", "u", "d", "m", "q")
# Determiners share the "r" (pronoun) tag with perfectly breakable pronouns.
TRAILING_TABOO_WORDS = frozenset({"这", "那", "这个", "那个", "每", "某", "各", "本", "上述", "以下"})

# jieba tags every Latin token "eng", so the Chinese part-of-speech taboo is
# blind to English function words and would happily end a line on "the" or
# "of". These lists restore the same rule for Latin script: a word that governs
# what follows it must not be the last thing on the line.
TRAILING_TABOO_EN = frozenset("""
a an the this that these those my your his her its our their
of in on at to for with from by as into onto than about across through
during before after between among against toward towards over under within
and or but nor so yet plus versus
is are was were be been being am
has have had do does did
will would can could may might must shall should
no not very more most less least such another each every either neither
""".split())

# Words that must not *open* a cue: a leading conjunction has been cut out of
# the phrase it joins, and a leading possessive/infinitive marker is orphaned.
LEADING_TABOO_EN = frozenset("""
and or but nor so yet plus of to
""".split())


def _is_latin_word(word: str, pos: str) -> bool:
    if str(pos or "").startswith("eng"):
        return True
    stripped = word.strip().strip(ALL_PUNCT)
    return bool(stripped) and all(ch.isascii() and (ch.isalpha() or ch in "'-") for ch in stripped)


def is_trailing_taboo(word: str, pos: str) -> bool:
    """True when a break immediately after this word would strand it."""
    bare = word.strip().strip(ALL_PUNCT)
    if not bare:
        return False
    if _is_latin_word(word, pos):
        return bare.lower() in TRAILING_TABOO_EN
    if bare in TRAILING_TABOO_WORDS:
        return True
    return str(pos or "").startswith(TRAILING_TABOO_POS)


# Part-of-speech prefixes a cue must not *begin* on. This is the mirror of the
# trailing taboo and catches a different defect: breaking 心思和精力 after 心思
# satisfies the trailing rule (心思 is a noun) but opens the next cue with a bare
# 和, splitting a coordinate structure across the cut. Particles are included
# because a cue can never legitimately open with 的 or 了.
LEADING_TABOO_POS = ("c", "u")


def is_leading_taboo(word: str, pos: str) -> bool:
    """True when starting a cue with this word would orphan it from the phrase
    it belongs to."""
    bare = word.strip().strip(ALL_PUNCT)
    if not bare:
        return False
    if _is_latin_word(word, pos):
        return bare.lower() in LEADING_TABOO_EN
    return str(pos or "").startswith(LEADING_TABOO_POS)


def cut_words_tagged(text: str) -> list[tuple[str, str]]:
    """Word tokens with part-of-speech tags. Falls back to untagged
    per-character tokens when jieba is unavailable — worse breaks, but still
    functional."""
    try:
        import logging

        import jieba
        import jieba.posseg as pseg

        jieba.setLogLevel(logging.ERROR)
        tokens = [(w, f) for w, f in pseg.cut(text) if w]
    except Exception:
        tokens = [(t, "") for t in _fallback_cut(text)]
    return _glue_hyphens(tokens)


def _glue_hyphens(tokens: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Rejoin `real` `-` `time` into a single token.

    jieba splits on the ASCII hyphen, and the hyphen is not sentence
    punctuation, so without this a cue break can land inside a hyphenated
    compound: "uses real" / "-time satellite data".
    """
    out: list[tuple[str, str]] = []
    idx = 0
    while idx < len(tokens):
        word, pos = tokens[idx]
        if (
            word == "-"
            and out
            and idx + 1 < len(tokens)
            and _is_latin_word(out[-1][0], out[-1][1])
            and _is_latin_word(tokens[idx + 1][0], tokens[idx + 1][1])
        ):
            prev_word, prev_pos = out[-1]
            out[-1] = (prev_word + "-" + tokens[idx + 1][0], prev_pos or "eng")
            idx += 2
            continue
        out.append((word, pos))
        idx += 1
    return out


def cut_words(text: str) -> list[str]:
    return [w for w, _ in cut_words_tagged(text)]


def _fallback_cut(text: str) -> list[str]:
    tokens: list[str] = []
    buffer = ""
    for ch in text:
        if is_wide(ch) or ch in ALL_PUNCT or ch.isspace():
            if buffer:
                tokens.append(buffer)
                buffer = ""
            tokens.append(ch)
        else:
            buffer += ch
    if buffer:
        tokens.append(buffer)
    return tokens


def translation_render_style(style: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The style used to lay out the bilingual translation block: the caption
    style scaled down to the translation font size. Width measurement and line
    wrapping for the translation must use this, not the caption size. Returns
    (translation_style, translation_font_size)."""
    tscale = float(style.get("bilingual_scale") or 0.78)
    tsize = max(8, round(int(style["font_size"]) * tscale))
    tstyle = {**style, "font_size": tsize}
    # The character-count cap is calibrated to the caption size; the smaller
    # translation glyphs fit proportionally more per line, so relax it in step
    # with the font, letting the pixel-width budget be the real constraint.
    max_chars = int(style.get("max_chars_per_line") or 0)
    if max_chars and tscale > 0:
        tstyle["max_chars_per_line"] = max(1, round(max_chars / tscale))
    return tstyle, tsize


def _join_translation_lines(lines: list[str]) -> str:
    """Reflow the model's translation lines back into a single string so it can
    be re-wrapped to the budget. Join with a space only where a space belongs
    (Latin word boundary); adjacent CJK glyphs are concatenated directly so no
    stray space appears mid-sentence."""
    out = ""
    for line in lines:
        line = str(line).strip()
        if not line:
            continue
        if not out:
            out = line
            continue
        sep = "" if (is_wide(out[-1]) or is_wide(line[0])) else " "
        out += sep + line
    return out


def translation_display_lines(cue: dict[str, Any], style: dict[str, Any]) -> list[str]:
    """The translation lines as they should actually render: the model's
    `translation_lines`, but with any line wider than the usable width wrapped
    at word boundaries (measured at the smaller translation font). Lines that
    already fit are left exactly as given. If wrapping overflows the caption's
    max_lines budget, the whole translation is reflowed into balanced lines
    within that budget."""
    trans = cue.get("translation_lines")
    if not trans:
        return []
    tstyle, _ = translation_render_style(style)
    usable = float(tstyle.get("usable_width_px") or 0)
    max_lines = int(tstyle.get("max_lines") or 1)
    raw = [str(l) for l in trans]
    wrapped: list[str] = []
    for line in raw:
        if usable and text_width_px(line, tstyle) > usable + 1.0:
            wrapped.extend(wrap_lines(line, tstyle))
        else:
            wrapped.append(line)
    if max_lines and len(wrapped) > max_lines:
        wrapped = wrap_lines(_join_translation_lines(raw), tstyle)
    return wrapped


def wrap_lines(text: str, style: dict[str, Any]) -> list[str]:
    """Break a cue into at most max_lines visually balanced lines."""
    max_lines = int(style["max_lines"])
    usable = float(style["usable_width_px"])
    max_chars = int(style.get("max_chars_per_line") or 0)
    if max_lines <= 1 or (text_width_px(text, style) <= usable and fits_chars(text, max_chars)):
        return [text]
    breaks = _break_candidates(text)
    best: tuple[float, list[str]] | None = None
    # A wrap that lands on punctuation is worth this much line-width of
    # imbalance; without it the wrapper chases symmetry straight through the
    # middle of a phrase.
    punct_bonus = usable * 0.35
    for pos in breaks:
        head, tail = text[:pos].strip(), text[pos:].strip()
        if not head or not tail:
            continue
        head_w, tail_w = text_width_px(head, style), text_width_px(tail, style)
        overflow = max(0.0, head_w - usable) + max(0.0, tail_w - usable)
        # A line that is short enough in pixels can still be too long to read.
        if max_chars:
            per_char = usable / max_chars
            overflow += per_char * (
                max(0, line_char_count(head) - max_chars) + max(0, line_char_count(tail) - max_chars)
            )
        # Prefer two lines of similar length once both fit.
        cost = overflow * 100.0 + abs(head_w - tail_w)
        if head[-1] not in STRONG_PUNCT + WEAK_PUNCT:
            cost += punct_bonus
        if best is None or cost < best[0]:
            best = (cost, [head, tail])
    if best is None:
        return [text]
    if max_lines == 2:
        return best[1]
    # More than two lines: recurse on the longer half.
    head, tail = best[1]
    sub_style = {**style, "max_lines": max_lines - 1}
    return [head, *wrap_lines(tail, sub_style)]


def _break_candidates(text: str) -> list[int]:
    """Indices where a line break is typographically acceptable.

    Word boundaries only — the same reason cue segmentation needs jieba applies
    to line wrapping: breaking 评论区 into 评论 / 区 across two lines is just as
    wrong as breaking it across two cues. Positions that would strand a
    conjunction or particle at the end of a line are dropped outright, unless
    that would leave nowhere to break at all.
    """
    positions: list[int] = []
    fallback: list[int] = []
    cursor = 0
    for word, pos in cut_words_tagged(text):
        cursor += len(word)
        if cursor >= len(text):
            break
        # Never start a line with punctuation: a break belongs after the mark,
        # not before it.
        if text[cursor].isspace() or text[cursor] in ALL_PUNCT:
            continue
        # Never break inside a contraction or hyphenated word: "NASA's" and
        # "real-time" must not split at the apostrophe/hyphen (jieba tokenizes
        # them into pieces, which would otherwise look like a legal boundary).
        if cursor >= 1 and text[cursor - 1] in "'’-" and text[cursor].isalnum():
            continue
        fallback.append(cursor)
        if is_trailing_taboo(word, pos):
            continue
        positions.append(cursor)
    return positions or fallback


def line_char_count(text: str) -> int:
    """Characters a reader has to take in on one line. Spaces are excluded so
    the same limit is meaningful for Chinese (no spaces) and English."""
    return sum(1 for ch in text if not ch.isspace())


def fits_chars(text: str, max_chars: int) -> bool:
    return not max_chars or line_char_count(text) <= max_chars


def estimate_cps(text: str, duration: float) -> float:
    if duration <= 0:
        return math.inf
    return visible_char_count(text) / duration
