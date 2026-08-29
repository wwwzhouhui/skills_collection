"""Language-side machinery for condensing spontaneous speech.

Condensing a rambling talk into a tight one is two problems wearing one coat.
The *editorial* problem — which sentences carry the piece — belongs to the model.
The *mechanical* problem is everything below, and none of it is a judgement call:

- **Where do the sentences actually start and end?** ASR hands back segments, not
  sentences: one segment can be a fourteen-second run-on, and its punctuation is
  a guess. Spontaneous speech marks its own boundaries with *pauses*, so units
  are split on the union of terminal punctuation and real silence, and a
  character-to-time map (built from word timestamps when the provider gives
  them) turns a text offset back into a cut time.
- **Which spans are disfluency rather than content?** Fillers and stutters are
  the free compression in any unscripted recording, but "这个" is a filler in
  one clause and a demonstrative in the next, so the lexicon is split into a
  tier that is almost always disfluency and a tier that needs the model to look.
- **What breaks when a sentence is removed?** A cut is not local. Dropping a
  question orphans its answer; dropping an antecedent leaves "它" pointing at
  nothing; dropping "首先" leaves "其次" hanging. These are detectable from the
  text alone, and they are exactly the failures that make a condensed cut sound
  wrong even when every individual cut point is clean.

Everything here is text and timing analysis. No frames, no model calls.
"""
from __future__ import annotations

import difflib
import math
import re
import unicodedata
from typing import Any, Iterable

# --- character classes ----------------------------------------------------

_TERMINAL_PUNCT = "。．！？!?…"
_CLAUSE_PUNCT = "，,、；;：:"
_ALL_PUNCT = _TERMINAL_PUNCT + _CLAUSE_PUNCT + "\"'“”‘’()（）《》[]【】—-~"


def is_cjk(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


def is_content_char(ch: str) -> bool:
    """A character that carries sound, so it can be aligned to a timestamp."""
    if ch.isspace():
        return False
    category = unicodedata.category(ch)
    return not category.startswith("P") and not category.startswith("S")


def display_weight(ch: str) -> float:
    """Rough syllable weight, used only when no word timings exist.

    Mirrors the subtitle layer's `display_units`: a CJK character is about one
    syllable, a Latin letter a fraction of one. Interpolating on raw character
    count instead makes an embedded English phrase eat a disproportionate slice
    of the timeline, which then places cut points inside words.
    """
    if is_cjk(ch):
        return 1.0
    if ch.isspace():
        return 0.15
    if ch in _ALL_PUNCT:
        return 0.35
    return 0.38


def guess_language(text: str) -> str:
    sample = text[:4000]
    if not sample:
        return "und"
    cjk = sum(1 for ch in sample if is_cjk(ch))
    return "zh" if cjk >= max(4, len(sample) * 0.15) else "en"


# --- disfluency lexicons --------------------------------------------------
#
# Two tiers, because the cost of being wrong is asymmetric. `HARD` spans are
# excised automatically when the caller asks for filler removal: they are
# hesitation sounds with no reading under which they carry meaning. `SOFT` spans
# are only ever *reported*: "这个" before a noun is a demonstrative, "其实"
# can be the hinge of an argument, and silently deleting either changes what the
# speaker said. The model decides on those by reading the unit.

FILLERS_HARD_ZH = ["嗯嗯", "嗯", "呃", "额", "唔", "呣", "哎", "诶", "欸", "啊啊"]
FILLERS_HARD_EN = ["um", "umm", "uh", "uhh", "erm", "er", "hmm", "mmm", "ah"]
FILLERS_SOFT_ZH = [
    "就是说", "也就是说", "怎么说呢", "怎么讲", "你知道吧", "你知道",
    "对不对", "对吧", "是吧", "是不是", "然后呢", "反正", "其实",
    "那个", "这个", "就是", "什么的", "之类的",
]
FILLERS_SOFT_EN = [
    "you know", "i mean", "sort of", "kind of", "you see", "right",
    "basically", "actually", "literally", "like", "well", "so yeah", "anyway",
]

# Openers that point backwards. A unit starting with one of these was a reply to
# whatever came before it; promote it to the start of a clip and it sounds like
# an answer to a question the viewer never heard.
CONNECTIVE_OPENERS_ZH = [
    "所以", "因此", "但是", "但", "可是", "不过", "然而", "而且", "并且", "另外",
    "然后", "接着", "因为", "由于", "其实", "也就是说", "就是说", "比如说", "比如",
    "举个例子", "总之", "总的来说", "反过来", "换句话说", "于是", "结果", "那么", "那",
    "对", "是的", "没错", "当然",
]
CONNECTIVE_OPENERS_EN = [
    "so", "but", "and", "because", "however", "therefore", "also", "then",
    "besides", "anyway", "actually", "for example", "in other words", "well",
    "yes", "yeah", "right", "exactly", "of course", "which",
]

# Words whose referent lives in an earlier sentence. If that sentence was cut,
# the reference dangles.
ANAPHORA_ZH = [
    "这个", "这些", "这种", "这样", "这件", "这点", "那个", "那些", "那种", "那样",
    "它", "它们", "他", "他们", "她", "她们", "此", "该", "上面", "前面", "刚才",
    "刚刚", "之前说", "我说的", "提到的", "同样", "也是", "一样",
]
ANAPHORA_EN = [
    "this", "that", "these", "those", "it", "they", "them", "he", "she",
    "such", "the same", "as i said", "as mentioned", "earlier", "just now",
    "the latter", "the former",
]

ENUM_FIRST_ZH = ["第一", "首先", "一是", "一方面", "开始", "最开始"]
ENUM_LATER_ZH = ["第二", "第三", "第四", "其次", "然后是", "二是", "三是", "另一方面", "最后", "再一个", "再者"]
ENUM_FIRST_EN = ["first", "firstly", "to begin", "one thing", "for one"]
ENUM_LATER_EN = ["second", "secondly", "third", "thirdly", "next", "finally", "lastly", "another"]

QUESTION_MARKERS_ZH = ["吗", "呢", "什么", "怎么", "为什么", "哪", "多少", "是不是", "有没有", "能不能"]
QUESTION_MARKERS_EN = ["what", "why", "how", "when", "where", "who", "which", "do you", "did you", "can you", "would you"]

# Phrases that point at something on screen. These are the trace a visual moment
# leaves in the transcript, and they are the reason this pipeline does not need a
# dense visual pass: instead of sampling the whole video looking for content the
# text might have missed, the text says where to look. Dropping a unit that says
# "watch this" silently discards whatever was being shown; keeping it without
# checking the frame risks keeping a reference to something now off screen.
#
# Curated as multi-word phrases on purpose. A bare 这里 / "this" is among the
# commonest words in speech and would flag most of the recording.
VISUAL_REFERENCE_ZH = [
    "看这里", "看这个", "看一下这", "你看这", "大家看", "看我", "像这样", "这样子",
    "这个动作", "这个姿势", "这个位置", "这个手势", "屏幕上", "画面上", "图上",
    "如图", "我给你看", "我给大家看", "我演示", "演示一下", "我比划", "上面这个",
    "右边这", "左边这", "这边这个", "注意看", "可以看到",
]
VISUAL_REFERENCE_EN = [
    "as you can see", "you can see", "you'll see", "look at this", "look at that",
    "look here", "right here", "over here", "like this", "like so",
    "on the screen", "in this picture", "in this diagram", "watch this",
    "i'll show you", "let me show", "i'm going to show", "showing you",
    "this position", "this movement", "this exercise", "notice how", "see how",
    "point to", "pointing at", "up here", "down here",
]


def _lex(language: str, zh: list[str], en: list[str]) -> list[str]:
    return zh if language == "zh" else en


# --- character/time alignment --------------------------------------------

def align_char_times(
    text: str,
    words: list[dict[str, Any]] | None,
    seg_start: float,
    seg_end: float,
) -> tuple[list[tuple[float, float]], str]:
    """Per-character (start, end) for `text`, and how it was derived.

    Cut times are the whole point of this module, and a cut is only as good as
    the mapping from "this character" to "this second". With word timestamps the
    mapping is measured; without them it is interpolated, and the caller has to
    know which it got — an interpolated boundary can sit mid-syllable, so it
    needs a pause-snap and a listening check that a measured one does not.
    """
    chars = list(text)
    if not chars:
        return [], "empty"
    if words:
        aligned = _align_from_words(chars, words, seg_start, seg_end)
        if aligned is not None:
            return aligned, "word_timestamps"
    return _interpolate(chars, seg_start, seg_end), "interpolated"


def _word_char_stream(words: list[dict[str, Any]]) -> list[tuple[str, float, float]]:
    """Flatten words into per-character timed slots."""
    stream: list[tuple[str, float, float]] = []
    for word in words:
        text = str(word.get("text") or "")
        start = float(word.get("start"))
        end = float(word.get("end"))
        body = [ch for ch in text if is_content_char(ch)]
        if not body:
            continue
        span = max(0.0, end - start)
        step = span / len(body) if body else 0.0
        for idx, ch in enumerate(body):
            stream.append((ch, start + step * idx, start + step * (idx + 1)))
    return stream


def _align_from_words(
    chars: list[str],
    words: list[dict[str, Any]],
    seg_start: float,
    seg_end: float,
) -> list[tuple[float, float]] | None:
    stream = _word_char_stream(words)
    if not stream:
        return None
    text_idx = [i for i, ch in enumerate(chars) if is_content_char(ch)]
    if not text_idx:
        return None
    # The ASR text and the word list are the same utterance but not always the
    # same string: text may be normalized (spacing inserted around Latin runs,
    # full-width digits folded, punctuation added). Diffing the two content-only
    # character sequences absorbs those edits instead of letting one inserted
    # space shift every subsequent timestamp.
    text_seq = [chars[i].lower() for i in text_idx]
    word_seq = [ch.lower() for ch, _, _ in stream]
    if abs(len(text_seq) - len(word_seq)) > max(8, 0.35 * max(len(text_seq), len(word_seq))):
        # Too far apart to be the same utterance; trust interpolation instead of
        # a bogus alignment that would silently misplace every cut.
        return None
    matcher = difflib.SequenceMatcher(a=text_seq, b=word_seq, autojunk=False)
    times: list[tuple[float, float] | None] = [None] * len(chars)
    matched = 0
    for a_start, b_start, size in matcher.get_matching_blocks():
        for k in range(size):
            _, start, end = stream[b_start + k]
            times[text_idx[a_start + k]] = (start, end)
            matched += 1
    if matched < 0.5 * len(text_seq):
        return None
    return _fill_gaps(times, chars, seg_start, seg_end)


def _fill_gaps(
    times: list[tuple[float, float] | None],
    chars: list[str],
    seg_start: float,
    seg_end: float,
) -> list[tuple[float, float]]:
    """Give unaligned characters (punctuation, unmatched runs) a sane time.

    Unaligned characters get a zero-width slot at the boundary between their
    aligned neighbours, interpolated across the run. Zero width matters: a comma
    must not claim any audio, or a cut placed "after the comma" would land a few
    tens of milliseconds into the next word.
    """
    n = len(times)
    known = [i for i, t in enumerate(times) if t is not None]
    if not known:
        return _interpolate(chars, seg_start, seg_end)
    out: list[tuple[float, float]] = []
    for idx in range(n):
        current = times[idx]
        if current is not None:
            out.append(current)
            continue
        prev = next((times[j] for j in range(idx - 1, -1, -1) if times[j] is not None), None)
        nxt = next((times[j] for j in range(idx + 1, n) if times[j] is not None), None)
        if prev is not None and nxt is not None:
            point = min(prev[1], nxt[0])
        elif prev is not None:
            point = prev[1]
        elif nxt is not None:
            point = nxt[0]
        else:
            point = seg_start
        out.append((point, point))
    return out


def _interpolate(chars: list[str], seg_start: float, seg_end: float) -> list[tuple[float, float]]:
    weights = [display_weight(ch) for ch in chars]
    total = sum(weights) or 1.0
    span = max(0.0, seg_end - seg_start)
    out: list[tuple[float, float]] = []
    cursor = 0.0
    for weight in weights:
        start = seg_start + span * (cursor / total)
        cursor += weight
        end = seg_start + span * (cursor / total)
        out.append((start, end))
    return out


# --- unit segmentation ----------------------------------------------------

def split_units(
    segments: list[dict[str, Any]],
    *,
    unit_pause: float = 0.55,
    max_unit_seconds: float = 14.0,
    min_unit_seconds: float = 0.35,
) -> list[dict[str, Any]]:
    """Turn ASR segments into sentence-sized, individually selectable units.

    A unit is the grain at which the model keeps or drops content, so the grain
    has to match how speech is actually organized. Two signals define a
    boundary and neither is sufficient alone:

    - **terminal punctuation**, which is what the ASR thinks a sentence is;
    - **a real pause**, which is what the speaker thinks a sentence is.

    Punctuation alone leaves twelve-second run-ons in providers that punctuate
    sparsely. Pauses alone shred a fast speaker into fragments. Taking the union,
    then force-splitting anything still longer than `max_unit_seconds` at its
    widest internal gap, keeps units selectable without inventing boundaries
    where the speaker did not leave one.
    """
    units: list[dict[str, Any]] = []
    for seg_index, seg in enumerate(segments):
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg["start"])
        end = float(seg["end"])
        if not (math.isfinite(start) and math.isfinite(end)) or end <= start:
            continue
        words = seg.get("words") if isinstance(seg.get("words"), list) else None
        char_times, timing_source = align_char_times(text, words, start, end)
        if not char_times:
            continue
        cuts = _unit_cut_offsets(text, char_times, unit_pause)
        pieces = _slice_text(text, char_times, cuts)
        pieces = _force_split_long(pieces, max_unit_seconds)
        pieces = _merge_tiny(pieces, min_unit_seconds)
        for piece in pieces:
            units.append({
                "text": piece["text"],
                "start": piece["start"],
                "end": piece["end"],
                "speaker": seg.get("speaker"),
                "segment_index": seg_index,
                "timing_source": timing_source,
                "char_times": piece["char_times"],
                "words": _words_within(words, piece["start"], piece["end"]) if words else [],
            })
    units.sort(key=lambda u: (u["start"], u["end"]))
    for idx, unit in enumerate(units):
        unit["id"] = f"u{idx + 1:03d}"
        unit["index"] = idx
    return units


def _unit_cut_offsets(text: str, char_times: list[tuple[float, float]], unit_pause: float) -> list[int]:
    """Character offsets (exclusive end of a unit) where a unit may break."""
    offsets: set[int] = set()
    n = len(text)
    for idx, ch in enumerate(text):
        if ch in _TERMINAL_PUNCT:
            # Break *after* the punctuation and any closing quotes.
            end = idx + 1
            while end < n and text[end] in "\"'”’)）】》":
                end += 1
            if 0 < end < n:
                offsets.add(end)
        # A gap in the audio wider than `unit_pause` is a sentence boundary the
        # speaker actually produced, whatever the punctuation says.
        if idx + 1 < n:
            gap = char_times[idx + 1][0] - char_times[idx][1]
            if gap >= unit_pause:
                offsets.add(idx + 1)
    return sorted(offsets)


def _slice_text(text: str, char_times: list[tuple[float, float]], cuts: list[int]) -> list[dict[str, Any]]:
    bounds = [0, *cuts, len(text)]
    pieces: list[dict[str, Any]] = []
    for lo, hi in zip(bounds, bounds[1:]):
        chunk = text[lo:hi]
        if not chunk.strip():
            continue
        times = char_times[lo:hi]
        voiced = [t for ch, t in zip(chunk, times) if is_content_char(ch)]
        if not voiced:
            continue
        pieces.append({
            "text": chunk.strip(),
            "start": min(t[0] for t in voiced),
            "end": max(t[1] for t in voiced),
            "char_times": _trimmed_char_times(chunk, times),
        })
    return pieces


def _trimmed_char_times(chunk: str, times: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Keep char_times aligned with the stripped text stored on the unit."""
    lead = len(chunk) - len(chunk.lstrip())
    trail = len(chunk) - len(chunk.rstrip())
    return times[lead: len(times) - trail if trail else len(times)]


def _force_split_long(pieces: list[dict[str, Any]], max_unit_seconds: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    queue = list(pieces)
    guard = 0
    while queue:
        guard += 1
        if guard > 4000:
            out.extend(queue)
            break
        piece = queue.pop(0)
        if piece["end"] - piece["start"] <= max_unit_seconds:
            out.append(piece)
            continue
        split_at = _widest_internal_gap(piece)
        if split_at is None:
            out.append(piece)
            continue
        left, right = _split_piece(piece, split_at)
        if left is None or right is None:
            out.append(piece)
            continue
        queue.insert(0, right)
        queue.insert(0, left)
    return out


def _widest_internal_gap(piece: dict[str, Any]) -> int | None:
    text = piece["text"]
    times = piece["char_times"]
    best: tuple[float, int] | None = None
    # Avoid splitting off a sliver: stay inside the middle 80% of the unit.
    lo = max(1, int(len(text) * 0.10))
    hi = min(len(text) - 1, int(len(text) * 0.90))
    for idx in range(lo, hi):
        if idx >= len(times):
            break
        gap = times[idx][0] - times[idx - 1][1]
        # Prefer clause punctuation when the gaps are comparable.
        bonus = 0.12 if idx >= 1 and text[idx - 1] in _CLAUSE_PUNCT else 0.0
        score = gap + bonus
        if best is None or score > best[0]:
            best = (score, idx)
    if best is None:
        return None
    return best[1]


def _split_piece(piece: dict[str, Any], offset: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    text = piece["text"]
    times = piece["char_times"]
    halves = []
    for chunk, chunk_times in ((text[:offset], times[:offset]), (text[offset:], times[offset:])):
        if not chunk.strip() or not chunk_times:
            halves.append(None)
            continue
        voiced = [t for ch, t in zip(chunk, chunk_times) if is_content_char(ch)]
        if not voiced:
            halves.append(None)
            continue
        halves.append({
            "text": chunk.strip(),
            "start": min(t[0] for t in voiced),
            "end": max(t[1] for t in voiced),
            "char_times": _trimmed_char_times(chunk, chunk_times),
        })
    return halves[0], halves[1]


def _merge_tiny(pieces: list[dict[str, Any]], min_unit_seconds: float) -> list[dict[str, Any]]:
    """Fold sub-`min_unit_seconds` fragments into a neighbour.

    A 0.2 s unit is not a decision the model should be asked to make; it is an
    interjection ("对") or an alignment artifact. Left standalone it also becomes
    a candidate clip too short to render cleanly.
    """
    if len(pieces) <= 1:
        return pieces
    out: list[dict[str, Any]] = []
    for piece in pieces:
        if piece["end"] - piece["start"] >= min_unit_seconds or not out:
            out.append(piece)
            continue
        prev = out[-1]
        prev["text"] = f"{prev['text']}{piece['text']}" if _needs_no_space(prev["text"]) else f"{prev['text']} {piece['text']}"
        prev["end"] = max(prev["end"], piece["end"])
        prev["char_times"] = prev["char_times"] + piece["char_times"]
    # A leading fragment has no previous unit to fold into; fold it forward.
    if len(out) > 1 and out[0]["end"] - out[0]["start"] < min_unit_seconds:
        head, second = out[0], out[1]
        second["text"] = f"{head['text']}{second['text']}" if _needs_no_space(head["text"]) else f"{head['text']} {second['text']}"
        second["start"] = min(head["start"], second["start"])
        second["char_times"] = head["char_times"] + second["char_times"]
        out = out[1:]
    return out


def _needs_no_space(text: str) -> bool:
    return bool(text) and is_cjk(text[-1])


def _words_within(words: list[dict[str, Any]] | None, start: float, end: float) -> list[dict[str, Any]]:
    if not words:
        return []
    picked = []
    for word in words:
        try:
            ws = float(word.get("start"))
            we = float(word.get("end"))
        except (TypeError, ValueError):
            continue
        if we <= start or ws >= end:
            continue
        picked.append({"text": str(word.get("text") or ""), "start": ws, "end": we})
    return picked


# --- disfluency spans -----------------------------------------------------

def find_disfluencies(unit: dict[str, Any], language: str) -> dict[str, list[dict[str, Any]]]:
    """Timed spans for hesitation sounds, hedges and stutters inside a unit.

    Returned as three separate lists rather than one, because they carry
    different licence to delete: `hard` is safe to excise mechanically, `stutter`
    likewise, `soft` is reported for the model to rule on.
    """
    text = unit["text"]
    times = unit["char_times"]
    hard = _match_spans(text, times, _lex(language, FILLERS_HARD_ZH, FILLERS_HARD_EN), language, standalone=False)
    soft = _match_spans(text, times, _lex(language, FILLERS_SOFT_ZH, FILLERS_SOFT_EN), language, standalone=True)
    stutter = _find_stutters(text, times, language)
    return {"hard": hard, "soft": soft, "stutter": stutter}


def _match_spans(
    text: str,
    times: list[tuple[float, float]],
    lexicon: Iterable[str],
    language: str,
    *,
    standalone: bool,
) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    lowered = text.lower()
    for phrase in sorted(lexicon, key=len, reverse=True):
        needle = phrase.lower()
        start = 0
        while True:
            idx = lowered.find(needle, start)
            if idx < 0:
                break
            start = idx + 1
            end = idx + len(needle)
            if language != "zh" and not _word_bounded(lowered, idx, end):
                continue
            if _overlaps_existing(spans, idx, end):
                continue
            if idx >= len(times) or end - 1 >= len(times):
                continue
            spans.append({
                "phrase": text[idx:end],
                "char_start": idx,
                "char_end": end,
                "start": times[idx][0],
                "end": times[end - 1][1],
                "standalone_hint": _standalone_hint(text, idx, end),
            })
    spans.sort(key=lambda s: s["char_start"])
    return spans


def _word_bounded(text: str, start: int, end: int) -> bool:
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    return not before.isalnum() and not after.isalnum()


def _overlaps_existing(spans: list[dict[str, Any]], start: int, end: int) -> bool:
    return any(not (end <= s["char_start"] or start >= s["char_end"]) for s in spans)


def _standalone_hint(text: str, start: int, end: int) -> bool:
    """True when the phrase is bracketed by punctuation or the unit edge.

    This is the difference between "那个，我觉得" (a stall) and "那个产品"
    (a demonstrative). It is a hint and nothing more — reported so the model can
    weigh it, never used to delete a soft filler on its own.
    """
    before = text[start - 1] if start > 0 else ""
    after = text[end] if end < len(text) else ""
    edge = (not before) or before in _ALL_PUNCT or before.isspace()
    tail = (not after) or after in _ALL_PUNCT or after.isspace()
    return edge and tail


_STUTTER_ZH = re.compile(r"([一-鿿]{1,3})(?:\1){1,}")
_STUTTER_EN = re.compile(r"\b(\w{1,12})(?:[\s,]+\1\b){1,}", re.IGNORECASE)


def _find_stutters(text: str, times: list[tuple[float, float]], language: str) -> list[dict[str, Any]]:
    """Immediate repetitions: "我我我", "就是就是", "the the".

    Unlike a soft filler this has no second reading — a speaker restarting a word
    is not saying it twice on purpose. The span kept is everything after the
    first occurrence, so the excision leaves one clean copy.
    """
    pattern = _STUTTER_ZH if language == "zh" else _STUTTER_EN
    spans: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        token = match.group(1)
        if not token.strip():
            continue
        keep_end = match.start() + len(token)
        drop_start, drop_end = keep_end, match.end()
        if drop_end <= drop_start or drop_end - 1 >= len(times) or drop_start >= len(times):
            continue
        spans.append({
            "phrase": text[match.start():match.end()],
            "char_start": drop_start,
            "char_end": drop_end,
            "start": times[drop_start][0],
            "end": times[drop_end - 1][1],
            "repeats": (drop_end - drop_start) // max(1, len(token)) + 1,
        })
    return spans


# --- unit-level text features --------------------------------------------

def unit_features(unit: dict[str, Any], language: str) -> dict[str, Any]:
    text = unit["text"]
    stripped = "".join(ch for ch in text if is_content_char(ch))
    return {
        "chars": len(stripped),
        "has_terminal_punct": bool(text.rstrip() and text.rstrip()[-1] in _TERMINAL_PUNCT),
        "opens_with_connective": _opening_match(text, _lex(language, CONNECTIVE_OPENERS_ZH, CONNECTIVE_OPENERS_EN), language),
        "anaphora": _contains_any(text, _lex(language, ANAPHORA_ZH, ANAPHORA_EN), language),
        "enum_first": _contains_any(text, _lex(language, ENUM_FIRST_ZH, ENUM_FIRST_EN), language),
        "enum_later": _contains_any(text, _lex(language, ENUM_LATER_ZH, ENUM_LATER_EN), language),
        "is_question": _is_question(text, language),
        "visual_reference": _contains_any(text, _lex(language, VISUAL_REFERENCE_ZH, VISUAL_REFERENCE_EN), language),
    }


def _opening_match(text: str, lexicon: Iterable[str], language: str) -> str | None:
    head = text.lstrip()
    lowered = head.lower()
    for phrase in sorted(lexicon, key=len, reverse=True):
        needle = phrase.lower()
        if not lowered.startswith(needle):
            continue
        if language != "zh":
            rest = lowered[len(needle):]
            if rest and rest[0].isalnum():
                continue
        return head[:len(needle)]
    return None


def _contains_any(text: str, lexicon: Iterable[str], language: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for phrase in lexicon:
        needle = phrase.lower()
        idx = lowered.find(needle)
        if idx < 0:
            continue
        if language != "zh" and not _word_bounded(lowered, idx, idx + len(needle)):
            continue
        found.append(phrase)
    return found


def _is_question(text: str, language: str) -> bool:
    """Is this unit actually a question?

    Deliberately strict. The loose version — "contains 什么/怎么/how/why" — fires
    on "不用抱什么太大的期望" and "我不知道为什么", which are statements, and a
    question flag that is wrong half the time is worse than no flag: it makes
    the `answer_without_question` continuity check cry wolf at every join.
    """
    body = text.rstrip().rstrip("\"'”’)）】》")
    if body.endswith(("？", "?")):
        return True
    if language == "zh":
        # A sentence-final interrogative particle is the reliable marker when the
        # ASR dropped the question mark. 么 is excluded deliberately: it matches
        # the tail of 什么/怎么/那么, so "会发生什么。" would read as a question.
        stripped = body.rstrip("。，、；：!！… ")
        if stripped.endswith(("吗", "呢")):
            return True
        # A wh-word only counts in a short utterance that opens with it — that is
        # the shape of a real question, not of a clause containing 什么.
        head = stripped[:8]
        for marker in ("为什么", "怎么", "哪", "多少"):
            if marker in head and len(stripped) <= 24:
                return True
        # A-not-A questions (是不是 / 有没有 / 能不能) need a guard: the same
        # substrings appear inside reduplications like 没有没有 and 不是不是, which
        # are stutters, not questions.
        for marker in ("是不是", "有没有", "能不能"):
            idx = head.find(marker)
            if idx < 0 or len(stripped) > 24:
                continue
            if idx == 0 or head[idx - 1] not in "没不":
                return True
        return False
    lowered = body.lower()
    if len(lowered) <= 120:
        for opener in ("what", "why", "how", "when", "where", "who", "which", "do you", "did you",
                       "can you", "could you", "would you", "are you", "is it", "does it"):
            if lowered.startswith(opener):
                return True
    return False


def normalize_for_similarity(text: str) -> str:
    return "".join(ch.lower() for ch in text if is_content_char(ch))


def find_near_duplicates(
    units: list[dict[str, Any]],
    *,
    window: int = 40,
    threshold: float = 0.74,
    min_chars: int = 8,
) -> dict[str, dict[str, Any]]:
    """Units that restate an earlier one.

    Unscripted speakers loop: they make a point, digress, and make it again in
    slightly different words. That is the largest single block of removable
    duration in most recordings and the hardest to see by reading linearly, so
    it is worth computing. Comparison is limited to a sliding window of earlier
    units — a callback forty sentences later is usually deliberate structure,
    not a loop, and the quadratic cost is not worth paying to catch it.
    """
    keys = [normalize_for_similarity(u["text"]) for u in units]
    result: dict[str, dict[str, Any]] = {}
    for idx, key in enumerate(keys):
        if len(key) < min_chars:
            continue
        best: tuple[float, int] | None = None
        for prev in range(max(0, idx - window), idx):
            other = keys[prev]
            if len(other) < min_chars:
                continue
            # Cheap length gate before the expensive ratio.
            if min(len(key), len(other)) / max(len(key), len(other)) < 0.55:
                continue
            ratio = difflib.SequenceMatcher(a=key, b=other, autojunk=False).ratio()
            if ratio >= threshold and (best is None or ratio > best[0]):
                best = (ratio, prev)
        if best is not None:
            result[units[idx]["id"]] = {
                "duplicate_of": units[best[1]]["id"],
                "similarity": round(best[0], 3),
            }
    return result


# --- topic runs -----------------------------------------------------------

_STOP_ZH = frozenset([
    "我们", "你们", "他们", "这个", "那个", "什么", "怎么", "可以", "然后", "就是", "因为", "所以",
    "但是", "还是", "自己", "现在", "已经", "一个", "一些", "一样", "这样", "那样", "觉得", "知道",
    "真的", "其实", "可能", "需要", "东西", "时候", "问题", "大家", "没有", "不是", "这些", "那些",
    "感觉", "很多", "有些", "非常", "特别", "比较", "应该", "为什么", "或者", "如果", "只有", "还有",
])
_STOP_EN = frozenset([
    "the", "and", "that", "this", "with", "have", "just", "like", "know", "really", "think",
    "going", "would", "could", "there", "their", "them", "they", "what", "when", "where",
    "because", "about", "which", "these", "those", "your", "you're", "it's", "don't", "very",
    "some", "thing", "things", "kind", "sort", "want", "make", "from", "into", "more", "then",
    "actually", "basically", "literally", "something", "anything", "everything", "little",
])

# Function words already have their own flags; letting them through as "topics"
# would rank a stretch by how often the speaker said 反正, which is a disfluency
# signal, not a subject.
_TOPIC_EXCLUDE_ZH = frozenset(
    FILLERS_HARD_ZH + FILLERS_SOFT_ZH + CONNECTIVE_OPENERS_ZH + ANAPHORA_ZH + ENUM_FIRST_ZH + ENUM_LATER_ZH
)
_TOPIC_EXCLUDE_EN = frozenset(
    w.lower() for w in (FILLERS_HARD_EN + FILLERS_SOFT_EN + CONNECTIVE_OPENERS_EN + ANAPHORA_EN)
)


def _content_tokens(text: str, language: str) -> set[str]:
    if language == "zh":
        try:
            import jieba  # noqa: PLC0415

            tokens = [t.strip() for t in jieba.cut(text) if len(t.strip()) >= 2]
        except Exception:
            # Bigrams are a usable stand-in: a repeated topic word shows up as a
            # repeated bigram even without a segmenter.
            body = [ch for ch in text if is_cjk(ch)]
            tokens = ["".join(body[i:i + 2]) for i in range(len(body) - 1)]
        return {
            t for t in tokens
            if t not in _STOP_ZH and t not in _TOPIC_EXCLUDE_ZH and all(is_cjk(ch) for ch in t)
        }
    words = re.findall(r"[a-z']{4,}", text.lower())
    return {w for w in words if w not in _STOP_EN and w not in _TOPIC_EXCLUDE_EN}


def find_topic_runs(
    units: list[dict[str, Any]],
    language: str,
    *,
    window: int = 14,
    min_units: int = 3,
    min_seconds: float = 6.0,
    min_concentration: float = 0.6,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Stretches where the speaker keeps circling the same term.

    Verbatim-similarity detection only catches a sentence restated almost word
    for word. What unscripted speakers actually do is paraphrase: six sentences
    in a row about the same thing, no two alike, collectively saying what one
    would have. That is the largest block of removable time in a rambling
    recording and it is invisible both to a similarity ratio and to a linear read.

    Shared content words find it, but raw frequency does not: over a
    thirty-seven-minute recording, courtesy and framing words (谢谢, 关注,
    "thanks", "question") recur throughout and would fill the whole list. What
    separates a topic from a tic is **concentration** — a topic word has most of
    its occurrences inside one stretch, a generic word is spread across the
    recording. So a candidate must hold at least `min_concentration` of its total
    occurrences within the window, which is why a stopword list alone was never
    going to scale.

    This does not claim the run is redundant — a speaker may well need six
    sentences — it says "here is 20 s spent on one term, check whether it needs
    all of it", which is a question worth putting in front of the model rather
    than a verdict.
    """
    token_sets = [_content_tokens(u["text"], language) for u in units]
    global_counts: dict[str, int] = {}
    for tokens in token_sets:
        for token in tokens:
            global_counts[token] = global_counts.get(token, 0) + 1
    seen_tokens: set[str] = set()
    runs: list[dict[str, Any]] = []
    for start in range(len(units)):
        for token in sorted(token_sets[start] - seen_tokens):
            members = [
                idx for idx in range(start, min(len(units), start + window))
                if token in token_sets[idx]
            ]
            if len(members) < min_units:
                continue
            concentration = len(members) / max(1, global_counts.get(token, len(members)))
            if concentration < min_concentration:
                # Spread across the recording, so it is vocabulary, not a topic.
                seen_tokens.add(token)
                continue
            span_units = units[members[0]: members[-1] + 1]
            seconds = sum(u["end"] - u["start"] for u in span_units)
            if seconds < min_seconds:
                continue
            seen_tokens.add(token)
            runs.append({
                "keyword": token,
                "unit_ids": [units[i]["id"] for i in members],
                "span": [span_units[0]["id"], span_units[-1]["id"]],
                "hit_count": len(members),
                "total_occurrences": global_counts.get(token, len(members)),
                "concentration": round(concentration, 2),
                "span_seconds": round(seconds, 2),
            })
    runs.sort(key=lambda r: -r["span_seconds"])
    return runs[:limit]
