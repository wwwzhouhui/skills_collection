"""Speaker-attribution repair for transcripts whose diarization collapsed.

Cloud ASR transcribes the WORDS accurately but, on remote-mixed or
noisy multi-speaker audio, its built-in diarization can collapse two or more
distinct speakers onto one label — verified on a 3-way podcast where an
interviewer's questions and the guest's answers were all tagged speaker "1".
The words are right; only the "who said it" is wrong.

The fix does NOT touch the text. It has two deterministic pieces plus a visual
judgement the driving model performs — and the tools deliberately do NOT try to
decide who is right, because that is a judgement the model makes better than a
regex could:

1. `diarize_audit` reads the transcript and returns an EVIDENCE BRIEF, not a
   verdict: the per-label time SHARE; the turn-boundary WINDOWS (the acoustic
   gaps between utterances) worth a look; soft content HINTS that a label may
   merge two people (a question and its first-person answer under one label, a
   call-and-response, one label holding a lopsided share of what reads as a
   dialogue); and — new — the speaker-identifying NAME CUES already sitting in
   the text (a self-introduction "我是X", a hand-off "有请X", a vocative "X，你…").
   It never certifies the labels; even a clean-looking brief leaves the call to
   the model, and the watch windows are offered regardless of the soft verdict.
   The point is to aim the expensive visual pass at a few timestamps and hand
   over every cue the text already carries — not to pre-empt the decision.
2. The model uses `video_watch_segment` on those windows to SEE who is speaking
   (whose mouth moves / which panel is active) and cross-checks each name cue
   against the picture — the only source that can settle it when the audio itself
   cannot, and the only one that can tie a name to a face.
3. `diarize_relabel` writes the model's corrected time-range → speaker mapping
   back onto the transcript's segments and words, leaving every character of the
   text untouched.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import condense_lang as lang
from .result import ToolResult
from .run_context import RunContext
from .timeline import file_sha256
from .transcript import collect_segments, coerce_float, first_present, load_transcript_data

# First-person / second-person / naming cues, used only to decide whether an
# adjacent pair of same-labelled utterances *reads* like two people.
_FIRST_PERSON_ZH = ("我", "我们", "咱", "俺")
_FIRST_PERSON_EN = ("i ", "i'", "we ", "we'", "my ", "our ", "i,", "me ")
_SECOND_PERSON_ZH = ("你", "您", "你们")
_SECOND_PERSON_EN = ("you ", "you'", "your ")


def _norm(text: str) -> str:
    return "".join(ch for ch in text if not ch.isspace())


def _starts_first_person(text: str, language: str) -> bool:
    head = text.strip()[:8]
    if language == "zh":
        return any(p in head for p in _FIRST_PERSON_ZH)
    low = (" " + text.strip().lower())[:14]
    return any(p in low for p in _FIRST_PERSON_EN)


def _addresses_other(text: str, language: str) -> bool:
    if language == "zh":
        return any(p in text for p in _SECOND_PERSON_ZH)
    low = " " + text.lower()
    return any(p in low for p in _SECOND_PERSON_EN)


# --- Name cues carried by the transcript text itself -------------------------
# The words ASR returns often name the speakers: someone introduces themselves
# ("我是小龙" → this segment's speaker is 小龙) or is handed the floor ("有请小明"
# → 小明 is another participant, usually the next to talk). The audit surfaces
# these as CANDIDATES with timestamps so the model has them in hand — it still
# verifies each against the picture before trusting it, because a name spoken
# aloud can belong to someone not on camera. Skill guidance, previously the only
# place this signal lived, is now backed by the tool actually extracting it.
_SELF_INTRO_ZH = ("大家好我是", "大家好我叫", "我叫", "我是", "我就是", "我这边是")
_SELF_INTRO_EN = ("i'm ", "i am ", "my name is ", "this is ", "here's ")
# Hand-off / introduction. "欢迎" is deliberately excluded — "欢迎收看/欢迎来到"
# would mint junk names, and these cues are only worth surfacing when clean.
_HANDOFF_ZH = ("掌声有请", "接下来有请", "有请我们的", "让我们欢迎", "掌声欢迎", "请出", "有请")
_HANDOFF_EN = ("welcome ", "let's welcome ", "please welcome ", "over to ", "let's hear from ")
# A Chinese name token is short and contains NONE of these — pronouns, particles,
# numbers, the common conjunctions/adverbs/verbs/roles that a bare copula ("我是
# 最低的") or a conjunction ("因为…") would otherwise be mis-grabbed as a name.
# Precision over recall on purpose: a junk candidate misleads the visual pass, so
# it is better to surface no name than a wrong one — the model still reads the
# window and can catch a name the filter was too strict to keep.
_PARTICLES = set("的了着过吗呢啊吧嘛呀哟喔噢嗯哈呵")
_NOT_IN_NAME = set(
    "你您我他她它们咱"
    "一二三四五六七八九十零百千两几"
    "因为所以但如果然其实可能就是现这那不没有很太最挺更真还也都又再"
    "已经会要想说来去给把被对和跟或虽反正而且当确主感觉得知什么怎"
    "样时候位种些是有在做看到请问谢欢迎"
    "老师同学朋友先生女士大家各位嘉宾主持高低"
) | _PARTICLES


def _looks_like_name_zh(tok: str) -> bool:
    return 2 <= len(tok) <= 3 and all(c not in _NOT_IN_NAME for c in tok)


def _grab_name_zh(tail: str) -> str:
    """A short name-like token from the text right after a trigger, or ''."""
    for pre in ("我们的", "咱们的", "我们", "咱们"):  # "有请我们的李娜" → drop the possessive
        if tail.startswith(pre):
            tail = tail[len(pre):]
            break
    run: list[str] = []
    for ch in tail:
        if "一" <= ch <= "鿿":
            run.append(ch)
            if len(run) >= 4:
                break
        else:
            break
    for n in (3, 2):  # prefer a 3-char full name, fall back to a 2-char one
        cand = "".join(run[:n])
        if _looks_like_name_zh(cand):
            return cand
    return ""


def _grab_name_en(tail: str) -> str:
    m = re.match(r"\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", tail)
    return m.group(1) if m else ""


def _find_cue(text: str, triggers: tuple[str, ...], language: str) -> str:
    hay = text if language == "zh" else text.lower()
    for trig in triggers:
        idx = hay.find(trig)
        if idx >= 0:
            tail = text[idx + len(trig):]
            return _grab_name_zh(tail) if language == "zh" else _grab_name_en(tail)
    return ""


def _extract_name_cues(units: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    cues: list[dict[str, Any]] = []
    self_trigs = _SELF_INTRO_ZH if language == "zh" else _SELF_INTRO_EN
    hand_trigs = _HANDOFF_ZH if language == "zh" else _HANDOFF_EN
    for u in units:
        t = u["text"]
        spk = u["speaker"]
        # Self-introduction → the name belongs to THIS segment's speaker.
        name = _find_cue(t, self_trigs, language)
        if name:
            cues.append({"at": round(u["start"], 2), "kind": "self_intro",
                         "speaker_label": spk, "name_guess": name, "quote": t[:40],
                         "verify_window": {"start": round(u["start"], 2),
                                           "end": round(min(u["end"], u["start"] + 3.0), 2)}})
        # Hand-off / introduction → a participant, usually the NEXT speaker. Verify
        # by looking at who speaks just AFTER the hand-off, not at the announcer.
        name = _find_cue(t, hand_trigs, language)
        if name:
            cues.append({"at": round(u["end"], 2), "kind": "handoff",
                         "speaker_label": spk, "name_guess": name, "quote": t[:40],
                         "verify_window": {"start": round(u["end"], 2),
                                           "end": round(u["end"] + 3.0, 2)}})
    return cues


def _load_units(transcript_path: Path) -> tuple[list[dict[str, Any]], str]:
    data = load_transcript_data(transcript_path)
    raw = collect_segments(data)
    units: list[dict[str, Any]] = []
    for seg in raw:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        start = coerce_float(first_present(seg, ["start", "start_time", "begin"]))
        end = coerce_float(first_present(seg, ["end", "end_time", "finish"]))
        if start is None or end is None or end < start:
            continue
        units.append({"start": start, "end": end, "text": text, "speaker": str(seg.get("speaker")) if seg.get("speaker") is not None else None})
    units.sort(key=lambda u: u["start"])
    lang_code = data.get("language") if isinstance(data, dict) else None
    language = "zh" if str(lang_code or "").startswith("zh") else lang.guess_language(" ".join(u["text"] for u in units[:40]))
    return units, language


def _implausible_same_speaker(prev: dict[str, Any], nxt: dict[str, Any], language: str) -> str | None:
    """Why this adjacent same-label pair reads like two different people, or None."""
    if prev["speaker"] != nxt["speaker"] or prev["speaker"] is None:
        return None
    pt, nt = prev["text"], nxt["text"]
    prev_q = lang._is_question(pt, language)
    nxt_q = lang._is_question(nt, language)
    # Question → first-person answer: the classic interviewer/interviewee merge.
    if prev_q and not nxt_q and _starts_first_person(nt, language):
        return f"上一句是提问、下一句是第一人称回答，却同属 {prev['speaker']}"
    # Third/second-person address that is a question → first-person reply.
    if prev_q and _addresses_other(pt, language) and _starts_first_person(nt, language):
        return f"上一句在问“对方”、下一句以第一人称答，却同属 {prev['speaker']}"
    # Call-and-response: two short utterances, one a greeting/imperative, the
    # next a thanks/acknowledgement — almost never the same mouth.
    pn, nn = _norm(pt), _norm(nt)
    if len(pn) <= 8 and len(nn) <= 8:
        greet = ("加油", "欢迎", "来", "请", "谢谢", "谢", "对", "好", "哦", "嗯", "耶")
        if any(g in pn for g in ("加油", "欢迎", "请", "来吧")) and any(g in nn for g in ("谢谢", "谢", "好的", "好", "对")):
            return f"一喊一应（“{pt}”→“{nt}”）却同属 {prev['speaker']}"
    return None


def _merge_windows(flags: list[dict[str, Any]], pad: float, gap: float) -> list[dict[str, Any]]:
    """Collapse nearby flag boundaries into padded watch windows."""
    if not flags:
        return []
    flags = sorted(flags, key=lambda f: f["at"])
    windows: list[dict[str, Any]] = []
    for f in flags:
        lo, hi = max(0.0, f["at"] - pad), f["at"] + pad
        if windows and lo <= windows[-1]["end"] + gap:
            windows[-1]["end"] = max(windows[-1]["end"], hi)
            windows[-1]["reasons"].append(f["reason"])
        else:
            windows.append({"start": round(lo, 2), "end": round(hi, 2), "reasons": [f["reason"]]})
    for w in windows:
        w["end"] = round(w["end"], 2)
    return windows


def _combine_windows(a: list[dict[str, Any]], b: list[dict[str, Any]], hard_cap: int) -> list[dict[str, Any]]:
    """Merge two window lists (content-flag + turn-candidate), collapsing overlaps
    and keeping at most hard_cap of them, earliest first."""
    merged: list[dict[str, Any]] = []
    for w in sorted(a + b, key=lambda x: x["start"]):
        if merged and w["start"] <= merged[-1]["end"] + 1.0:
            merged[-1]["end"] = round(max(merged[-1]["end"], w["end"]), 2)
            merged[-1]["reasons"] = list(dict.fromkeys(merged[-1].get("reasons", []) + w.get("reasons", [])))
        else:
            merged.append({"start": w["start"], "end": w["end"], "reasons": list(w.get("reasons", []))})
    return merged[:hard_cap]


def _turn_candidate_windows(units: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    """Windows around the real gaps between utterances — candidate turn changes.

    When diarization is degenerate the whole transcript has to be re-attributed
    by eye, so instead of the sparse content-flag windows, hand back the natural
    boundaries: each inter-utterance gap is a place a turn could change, worth a
    look. Widest gaps first (most likely a real handoff), capped so a long
    recording stays reviewable.
    """
    gaps: list[tuple[float, float, float]] = []  # (gap, boundary_time, ...)
    for prev, nxt in zip(units, units[1:]):
        g = nxt["start"] - prev["end"]
        gaps.append((g, (prev["end"] + nxt["start"]) / 2.0, prev["end"]))
    gaps.sort(reverse=True)
    picked = sorted(b for _, b, _ in gaps[:cap])
    windows: list[dict[str, Any]] = []
    for b in picked:
        lo, hi = max(0.0, b - 1.5), b + 1.5
        if windows and lo <= windows[-1]["end"] + 1.0:
            windows[-1]["end"] = round(max(windows[-1]["end"], hi), 2)
        else:
            windows.append({"start": round(lo, 2), "end": round(hi, 2), "reasons": ["turn candidate (标签退化，全片需重新归属)"]})
    return windows


def diarize_audit(args: dict, ctx: RunContext) -> ToolResult:
    transcript_path = ctx.resolve(args.get("transcript_path") or "out/transcript.json")
    if not transcript_path.is_file():
        return ToolResult(text=f"[ERROR] transcript not found: {transcript_path}")
    try:
        units, language = _load_units(transcript_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read transcript: {exc}")
    if not units:
        return ToolResult(text="[ERROR] transcript has no usable timestamped segments")

    speakers = [u["speaker"] for u in units if u["speaker"] is not None]
    labelled = bool(speakers)
    share: dict[str, float] = {}
    total = 0.0
    for u in units:
        dur = u["end"] - u["start"]
        total += dur
        if u["speaker"] is not None:
            share[u["speaker"]] = share.get(u["speaker"], 0.0) + dur
    share_pct = {k: round(v / total, 3) for k, v in share.items()} if total else {}
    top_share = max(share_pct.values()) if share_pct else 1.0

    # Roster: for each EXISTING label, a couple of representative windows (its
    # longest, clearest segments) where the model can go SEE who that label is.
    # This is what lets re-attribution stay CONSISTENT — before minting a new
    # identity for a person in a suspicious window, the model can check the
    # roster and reuse the label of someone already on it. (When the labels have
    # collapsed onto one, the roster is thin and the model builds its own cast as
    # it watches — the skill covers that; the tool still hands over what it has.)
    by_label: dict[str, list[dict[str, Any]]] = {}
    for u in units:
        if u["speaker"] is not None:
            by_label.setdefault(u["speaker"], []).append(u)
    roster: list[dict[str, Any]] = []
    for label, us in by_label.items():
        longest = sorted(us, key=lambda x: x["end"] - x["start"], reverse=True)[:2]
        samples = [
            {"start": round(seg["start"], 2),
             "end": round(min(seg["end"], seg["start"] + 4.0), 2),
             "quote": seg["text"][:24]}
            for seg in sorted(longest, key=lambda x: x["start"])
        ]
        roster.append({"label": label, "share": share_pct.get(label, 0.0), "sample_windows": samples})
    roster.sort(key=lambda r: r["share"], reverse=True)

    flags: list[dict[str, Any]] = []
    for prev, nxt in zip(units, units[1:]):
        reason = _implausible_same_speaker(prev, nxt, language)
        if reason:
            flags.append({
                "at": round((prev["end"] + nxt["start"]) / 2.0, 2),
                "reason": reason,
                "left": prev["text"][-24:],
                "right": nxt["text"][:24],
            })

    # Speaker-identifying cues sitting in the text itself. Candidates for the
    # model to verify against the picture — never a decision on their own.
    name_cues = _extract_name_cues(units, language)

    # Soft signals — evidence, not a verdict. The model decides whether to look.
    has_q = any(lang._is_question(u["text"], language) for u in units)
    has_fp = any(_starts_first_person(u["text"], language) for u in units)
    lopsided = labelled and top_share >= 0.85
    looks_like_dialogue = has_q and has_fp and len(units) >= 6
    likely_collapsed = labelled and looks_like_dialogue and (lopsided or len(share_pct) <= 1)
    signals = {
        "top_share": round(top_share, 3),
        "lopsided": lopsided,
        "looks_like_dialogue": looks_like_dialogue,
        "contradiction_hits": len(flags),
        "name_cue_count": len(name_cues),
    }

    # Windows to look at: content-contradiction spots always, plus turn-candidate
    # windows (the acoustic gaps where a turn could change) so the model can look
    # REGARDLESS of the soft verdict — generously when a collapse looks likely, a
    # few spot-checks otherwise. A clean-looking brief is never a certificate.
    flag_windows = _merge_windows(flags, pad=float(args.get("window_pad") or 1.5), gap=float(args.get("window_gap") or 2.0))
    hard_cap = int(args.get("max_windows") or 40)
    turn_cap = hard_cap if likely_collapsed else 6
    turn_windows = _turn_candidate_windows(units, cap=turn_cap) if labelled else []
    windows = _combine_windows(flag_windows, turn_windows, hard_cap=hard_cap)

    if not labelled:
        verdict = "no_speaker_labels"
        note = "转录没有说话人标签，无可审计。"
    elif likely_collapsed:
        verdict = "likely_collapsed"
        note = (
            f"一个标签（{max(share_pct, key=share_pct.get)}）占了 {top_share:.0%} 的时长，"
            "但内容里既有提问又有第一人称回答——像是把一段对话并到了一个人身上。"
            "标签很可能不可信，建议按下面的窗口看画面重新归属。"
        )
    elif flags:
        verdict = "worth_checking"
        note = f"有 {len(flags)} 处相邻同标签读起来像两个人（见 suspect_flags），其余大体一致。"
    else:
        verdict = "no_obvious_conflict"
        note = (
            "文本层面未见标签与内容明显冲突——但这只是从文字做的推断，不是免检。"
            "谁在说话最终以画面为准；若这段的去留取舍依赖说话人身份，仍应抽查窗口。"
        )

    report = {
        "transcript_path": str(transcript_path),
        "transcript_sha256": file_sha256(transcript_path),
        "language": language,
        "segment_count": len(units),
        "speaker_share": share_pct,
        "speaker_count": len(share_pct),
        "roster": roster,
        "verdict": verdict,
        "note": note,
        "signals": signals,
        "name_cues": name_cues,
        "suspect_flags": flags,
        "watch_windows": windows,
    }
    output_json = ctx.resolve(args.get("output_json") or "out/diarize_audit.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    win_txt = "\n".join(
        f"  {w['start']:.1f}-{w['end']:.1f}s  {w['reasons'][0]}"
        for w in windows[:20]
    ) or "  （无）"
    roster_txt = "\n".join(
        "  标签 {}（占 {:.0%}）：去 {} 看这是谁".format(
            r["label"], r["share"],
            "、".join(f"{w['start']:.1f}-{w['end']:.1f}s" for w in r["sample_windows"]) or "（无干净样本）",
        )
        for r in roster[:8]
    ) or "  （无既有标签）"
    cue_txt = "\n".join(
        "  {:.1f}s [{}] 名字候选「{}」← “{}”；到 {:.1f}-{:.1f}s 看那时谁在说来核对".format(
            c["at"], c["kind"], c["name_guess"], c["quote"],
            c["verify_window"]["start"], c["verify_window"]["end"],
        )
        for c in name_cues[:12]
    ) or "  （文本里没有自我介绍/点名之类的姓名线索）"
    return ToolResult(
        text=(
            f"Diarization 证据简报（不是裁决，判断权在你）：{verdict} — {note}\n"
            f"说话人时长占比：{share_pct}\n\n"
            f"【人物表】既有标签各去哪看清是谁（先建这张表，再谈归属）：\n{roster_txt}\n\n"
            f"【姓名线索】文本里的候选，去各自的核对窗确认（念到的名字未必是画面里正在说话的人）：\n{cue_txt}\n\n"
            f"【待看窗口】值得确认“谁在说”的地方（在这些地方看即可，不必全片）：\n{win_txt}\n\n"
            "下一步：①先对【人物表】每个标签的样本窗各看一次，记下每个人的画框位置/长相/角标名，建成一张"
            "『这段视频里有谁』的对照表；②再看【待看窗口】，判断每个窗里说话的人是不是对照表里已有的某位——"
            "是就复用那个标签/名字（别给同一个人起两个名），只有对不上任何人才新建；③名字候选只有在其核对窗里"
            "对上了正在说话的人才用，对不上宁可用 A/B/C。把每段 {start,end,speaker} 收集好调 diarize_relabel "
            "写回。全程不改文字——文字是准的。\n\n"
            "怎么看：video_watch_segment(video_path=..., fps=4, segments=[...])，多个窗合成一次调用，"
            "不需要先 video_ingest，只按窗口计费。**fps 至少 4**——2 fps 下说话的嘴和打哈欠的嘴长得一样。"
            "判据不是「嘴张开了」（听的人也会笑、会喘气、会点头应一声「嗯」），而是"
            "**整个窗里几乎每一帧口型都在变**，而且**变化的时长要对得上本窗的文字**"
            "（中文约每秒 4–6 字；若某人只在开头一秒动嘴而这句有 5 秒，那就不是他）。"
            "若整窗没有任何人在动嘴，别硬选：说话人可能不在画面里，或这里是配音的插播画面。"
            "窗口尽量卡在**换人处**——一张嘴停、另一张嘴起，一次看出两个结论。"
            "画面若有平台的「当前说话人」高亮框，它比口型更硬。要读角标/名牌上的字请改用 "
            "video_read_frames(region=\"name_plate\", upscale=2)，contact sheet 的分辨率会让你把名字猜错。"
            "看完仍分不清就保留中性标签并在 brief 里写明——错误归属会悄悄污染下游每一处 speaker_change 检查。"
        ),
        data=report,
        artifacts=[str(output_json)],
    )


def _word_text(word: dict) -> str:
    return str(first_present(word, ["text", "word"]) or "")


def _slice_text_by_words(text: str, words: list[dict]) -> list[str] | None:
    """Cut `text` into one piece per word, keeping punctuation with its word.

    The ASR's word list carries no punctuation ("机会要放，大胆的投。" arrives as
    机/会/要/放/大/胆/的/投), so a split segment's text cannot simply be the words
    joined back together — that silently drops every comma and full stop. Instead
    walk the original text, find each word in order, and let piece *i* run from
    word *i*'s position up to word *i+1*'s. Punctuation therefore rides along with
    the word it follows, and concatenating all pieces reproduces `text` exactly.

    Returns None when the words cannot be aligned to the text (a provider that
    normalises differently), which tells the caller not to split that segment.
    """
    pieces: list[str] = []
    starts: list[int] = []
    pos = 0
    for word in words:
        token = _word_text(word)
        if not token:
            return None
        idx = text.find(token, pos)
        if idx < 0:
            return None
        starts.append(idx)
        pos = idx + len(token)
    if not starts:
        return None
    for i, start in enumerate(starts):
        # Piece 0 also absorbs anything before the first word (a leading quote).
        left = 0 if i == 0 else start
        right = starts[i + 1] if i + 1 < len(starts) else len(text)
        pieces.append(text[left:right])
    return pieces


def _split_segment_by_speaker(seg: dict, words: list[dict]) -> list[dict] | None:
    """Split one segment into runs of consecutive same-speaker words.

    This is the fix for the case that motivated it: cloud ASR routinely bundles a
    speaker change inside one segment — a player's answer running straight into
    the narrator's score recap — and a segment can only carry one speaker label.
    Labelling by the segment's midpoint then hands the whole span to whoever holds
    the middle, so the minority speaker's sentences are silently attributed to the
    wrong person even when the caller's time ranges were exactly right. Splitting
    at the word-level speaker boundary keeps the model's correct judgement instead
    of averaging it away, and as a side effect the new boundaries land on speaker
    changes rather than mid-sentence.

    Returns None when there is nothing to split or the split cannot be done safely.
    """
    labels = [w.get("speaker") for w in words]
    if len(set(map(str, labels))) <= 1:
        return None

    runs: list[tuple[int, int]] = []
    run_start = 0
    for i in range(1, len(words)):
        if str(labels[i]) != str(labels[i - 1]):
            runs.append((run_start, i))
            run_start = i
    runs.append((run_start, len(words)))
    if len(runs) < 2:
        return None

    text = str(seg.get("text") or "")
    pieces = _slice_text_by_words(text, words) if text else None
    if text and pieces is None:
        return None  # cannot preserve the text safely; leave the segment alone

    out: list[dict] = []
    for lo, hi in runs:
        chunk = words[lo:hi]
        start = coerce_float(first_present(chunk[0], ["start", "start_time", "begin"]))
        end = coerce_float(first_present(chunk[-1], ["end", "end_time", "finish"]))
        if start is None or end is None:
            return None
        piece = dict(seg)
        piece["start"] = start
        piece["end"] = end
        piece["speaker"] = chunk[0].get("speaker")
        # Each new segment keeps its own word slice. Dropping `words` here would
        # make condense_index report "no word-level timestamps" for the WHOLE
        # transcript and fall back to interpolated timing everywhere.
        piece["words"] = chunk
        if pieces is not None:
            piece["text"] = "".join(pieces[lo:hi]).strip()
        out.append(piece)
    return out


def diarize_relabel(args: dict, ctx: RunContext) -> ToolResult:
    """Apply a corrected time-range → speaker mapping onto the transcript.

    Rewrites the `speaker` field on every segment and word whose midpoint falls in
    an assignment range, and — when word timings are present — splits any segment
    whose words end up under more than one speaker, so an ASR-bundled speaker
    change no longer collapses onto whoever holds the segment's midpoint. The text
    is never edited: a split segment's text is cut at the word boundary,
    punctuation included, and the pieces still concatenate to the original.
    Assignments that name a real person are honoured verbatim (so labels can
    become "主持人"/"喵喵子" instead of "1"/"2")."""
    transcript_path = ctx.resolve(args.get("transcript_path") or "out/transcript.json")
    if not transcript_path.is_file():
        return ToolResult(text=f"[ERROR] transcript not found: {transcript_path}")
    assignments = args.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        return ToolResult(text="[ERROR] assignments must be a non-empty array of {start, end, speaker} objects")
    ranges: list[tuple[float, float, str]] = []
    for a in assignments:
        if not isinstance(a, dict):
            return ToolResult(text="[ERROR] each assignment must be an object {start, end, speaker}")
        s = coerce_float(a.get("start"))
        e = coerce_float(a.get("end"))
        spk = a.get("speaker")
        if s is None or e is None or e <= s or spk in (None, ""):
            return ToolResult(text=f"[ERROR] invalid assignment (need start<end and non-empty speaker): {a}")
        ranges.append((s, e, str(spk)))
    ranges.sort()

    def assign(mid: float, fallback: Any) -> Any:
        best = None
        for s, e, spk in ranges:
            if s <= mid <= e:
                return spk  # explicit range wins
            d = min(abs(mid - s), abs(mid - e))
            if best is None or d < best[0]:
                best = (d, spk)
        # Only snap to the nearest range if it is genuinely close; else keep old.
        if best is not None and best[0] <= float(args.get("snap_seconds") or 0.4):
            return best[1]
        return fallback

    try:
        data = json.loads(transcript_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] could not read transcript JSON: {exc}")

    changed = 0
    total = 0
    split_count = 0
    split_notes: list[str] = []

    def relabel_list(items: list) -> list:
        """Relabel every item, splitting any whose words span two speakers.

        Returns the new list (same objects where nothing split), so the caller can
        swap it in — a segment that splits becomes two entries.
        """
        nonlocal changed, total, split_count
        out: list = []
        for it in items:
            if not isinstance(it, dict):
                out.append(it)
                continue
            s = coerce_float(first_present(it, ["start", "start_time", "begin"]))
            e = coerce_float(first_present(it, ["end", "end_time", "finish"]))
            if s is None or e is None:
                out.append(it)
                continue
            total += 1
            original_speaker = it.get("speaker")

            words = it.get("words")
            if isinstance(words, list) and words:
                for w in words:
                    if isinstance(w, dict):
                        ws = coerce_float(first_present(w, ["start", "start_time", "begin"]))
                        we = coerce_float(first_present(w, ["end", "end_time", "finish"]))
                        if ws is not None and we is not None:
                            w["speaker"] = assign((ws + we) / 2.0, w.get("speaker"))
                usable = [w for w in words if isinstance(w, dict) and _word_text(w)]
                if len(usable) == len(words):
                    parts = _split_segment_by_speaker(it, words)
                    if parts:
                        split_count += 1
                        if len(split_notes) < 6:
                            split_notes.append(
                                f"{s:.1f}-{e:.1f}s → " + " | ".join(
                                    f"{p['speaker']} {p['start']:.1f}-{p['end']:.1f}s" for p in parts
                                )
                            )
                        for p in parts:
                            if p.get("speaker") != original_speaker:
                                changed += 1
                        out.extend(parts)
                        continue

            new = assign((s + e) / 2.0, original_speaker)
            if new != original_speaker:
                it["speaker"] = new
                changed += 1
            out.append(it)
        return out

    if isinstance(data, dict):
        for key in ("segments", "utterances", "results"):
            if isinstance(data.get(key), list):
                data[key] = relabel_list(data[key])
                break
        if isinstance(data.get("words"), list):
            for w in data["words"]:
                if isinstance(w, dict):
                    ws = coerce_float(first_present(w, ["start", "start_time", "begin"]))
                    we = coerce_float(first_present(w, ["end", "end_time", "finish"]))
                    if ws is not None and we is not None:
                        w["speaker"] = assign((ws + we) / 2.0, w.get("speaker"))
        data["speaker_relabeled"] = True
        data["n_speakers"] = len({str(r[2]) for r in ranges})
    elif isinstance(data, list):
        data = relabel_list(data)

    output_path = ctx.resolve(args.get("output_path") or str(transcript_path))
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    speakers = sorted({r[2] for r in ranges})
    split_txt = ""
    if split_count:
        split_txt = (
            f"\nSplit {split_count} segment(s) that the ASR had bundled across a speaker change, "
            "at the word-level boundary (text and word timings preserved):\n  "
            + "\n  ".join(split_notes)
            + ("\n  ..." if split_count > len(split_notes) else "")
        )
    return ToolResult(
        text=(
            f"Relabeled {changed}/{total} segment(s) across {len(ranges)} assignment range(s). "
            f"New speaker set: {speakers}. Text left untouched. Wrote {ctx.virtualize(output_path)}."
            f"{split_txt}\n"
            "Re-run diarize_audit to confirm the picture is now consistent."
        ),
        data={
            "changed": changed, "total": total, "speakers": speakers,
            "segments_split": split_count, "output_path": str(output_path),
        },
        artifacts=[str(output_path)],
    )
