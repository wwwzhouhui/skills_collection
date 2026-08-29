#!/usr/bin/env python3
"""lol-recap 确定性工具组: 英雄联盟职业比赛 -> 叙事解说集锦(全程生成解说)。

照 soccer.py 结构改。分工红线: 工具不调用大模型的"叙事脑"——比赛理解/大纲/解说词/冷读由主 Agent 完成;
本模块只做确定性媒体操作(接入/排片/TTS/渲染混音/QC)。LOL 相对足球的简化:
  - 广播画面自带记分板/击杀提示 HUD,无需自绘比分角标、无防剧透跳分;
  - 纯生成解说: 原声全程压低当氛围,不做原声呼吸段;
  - 事件来源 = Agent 读解说轴(ASR)抽事件 + 可选 events_path(我们 VLM 检测的精确 in/out)做精定位。

四个工具:
  lol_ingest   source=lol -> out/match.json(队伍/各局视频/时长); action=axis: 解说ASR -> C 编号解说轴
  lol_arrange  match+shots+outline(Agent写)[+可选vlm events] -> reel.json + writing_brief.txt
  lol_tts      writer_script(Agent写) -> 逐句TTS(三档情绪:语速/响度, 音调恒零) + 句级缓存
  lol_render   reel+script_tts -> 硬切拼接 + 解说主轨 + 原声ducking + 标题/结尾卡 + QC门(yuv420p/faststart)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from .ffproc import run_proc, escape_text
from pathlib import Path

from .fonts import ass_font_name, find_cjk_font
from .result import ToolResult
from .run_context import RunContext, clean_env

# ---------------- 剪辑常量 ----------------
KIND_WINDOWS = {          # 每类事件默认 (前摇, 事件后) 秒; 事件后放长, 让画面把事情演完再切
    "fight":   (6.0, 9.0),   # 团战
    "kill":    (3.5, 5.0),   # 单个击杀/一血
    "objective": (8.0, 9.0), # 大龙/小龙/峡谷先锋
    "tower":   (5.0, 8.0),   # 推塔/破高地/拆水晶
    "ending":  (8.0, 11.0),  # 终结比赛
}
SNAP_IN_BACK, SNAP_IN_FWD = 5.0, 3.0
SNAP_OUT_BACK, SNAP_OUT_FWD = 3.0, 7.0
FLASH_PRE, FLASH_POST = 2.5, 1.5      # 冷开场名场面快闪(标题叠在第一个快闪上)
GAP_BREATH = 0.0                       # 不要中间黑屏
FREEZE = 3.0
CALL_SLOT = 3.5                        # 名场面呐喊句槽位
TITLE_SEC = 0.0                        # 标题不再单独黑卡,叠在开场画面上
NARR_TAIL = 1.2                        # 每段解说讲完后画面再留 ~1.2s 才切

# ---- mode="script"(解说稿驱动摘片): 画面是台词的函数, 讲到哪摘到哪 ----
JUMP_GAP = 6.0                         # 句子 t 超出当前画面游标该秒数 -> 另起切片(跳切蒙太奇)
CLIP_PRE = 1.0                         # 切片在首句所指时刻前留的起势画面
HARD_LEAD = 0.25                       # 硬事件句(呐喊)比事件帧早这么多起口
ACTION_SLACK = 6.0                     # 硬事件切片为让动作演完最多多留的秒数
QC_MAX_GAP = 9.0                       # QC 门: 全片最大无解说空窗(秒), 超过判 FAIL

# 三档情绪: 音调恒 0,只用语速+响度拉开
TIERS_RATE = {0: 10, 1: 20, 2: 30}
TIERS_LUFS = {0: -18.0, 1: -16.5, 2: -14.5}
CHARS_PER_SEC = {0: 4.6, 1: 4.9, 2: 5.2}
DEFAULT_TTS_PROVIDER = "edge_tts"
DEFAULT_LOL_TTS_VOICE = "zh-CN-YunjianNeural"

BED_VOL = 0.10                         # 原声全程压低(纯生成解说,原声只当氛围)
SUB_FONTNAME = "Noto Sans CJK SC"
CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _font() -> str:
    for f in CJK_FONT_CANDIDATES:
        if Path(f).exists():
            return f
    # 非 Linux (以及没装 Noto CJK 的 Linux): 用系统自带的 CJK 字体, 不要直接炸。
    found = find_cjk_font("bold")
    if found:
        return found
    raise RuntimeError("LoL/Basketball rendering needs a CJK font: install "
                       "Noto Sans CJK (Linux/mac) or point VE_FONT_DIRS at a "
                       "font directory — run /env-check for the exact command")


def _dur_of(p) -> float:
    out = run_proc(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def _ffmpeg(args):
    return run_proc(["ffmpeg", "-nostdin", "-y", "-v", "error"] + args,
                          capture_output=True, text=True)


# ================================================================ lol_ingest
def _commentary_axis(transcripts, out_dir):
    lines, index, n = [], [], 0
    for gi, tr in transcripts:
        for s in tr.get("segments", []):
            txt = (s.get("text") or "").strip()
            if not txt:
                continue
            cid = f"C{n:04d}"
            mm, ss = divmod(int(s["start"]), 60)
            lines.append(f"{cid} [G{gi} {mm:02d}:{ss:02d}] {txt}")
            index.append({"id": cid, "game": gi, "start": round(float(s["start"]), 2),
                          "end": round(float(s.get("end", s["start"])), 2), "text": txt})
            n += 1
    (out_dir / "commentary_axis.txt").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "commentary_index.json").write_text(json.dumps(index, ensure_ascii=False),
                                                    encoding="utf-8")
    return n, sum(len(i["text"]) for i in index)


def lol_ingest(args: dict, ctx: RunContext) -> ToolResult:
    action = args.get("action", "match")
    out_dir = Path(args.get("out_dir", "out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if action == "axis":
        paths = args.get("transcript_paths") or []
        if not paths:
            return ToolResult(text="[ERROR] transcript_paths required for action=axis")
        trs = []
        for i, p in enumerate(paths, 1):
            if not Path(p).exists():
                return ToolResult(text=f"[ERROR] transcript not found: {p}")
            trs.append((i, json.load(open(p))))
        n, chars = _commentary_axis(trs, out_dir)
        return ToolResult(text=f"commentary axis: {n} lines, {chars} chars -> {out_dir}/commentary_axis.txt",
                          data={"lines": n, "chars": chars,
                                "axis_path": str(out_dir / "commentary_axis.txt"),
                                "index_path": str(out_dir / "commentary_index.json")},
                          artifacts=[str(out_dir / "commentary_axis.txt")])

    if args.get("source", "lol") != "lol":
        return ToolResult(text="[ERROR] unknown source (supported: lol)")
    games_in = args.get("games")   # [{"name":"第一局","video":..., "video_lowres":...}]
    if not games_in:
        return ToolResult(text="[ERROR] games required: [{name,video,video_lowres?}]")
    games = {}
    for i, g in enumerate(games_in, 1):
        v = g["video"]
        if not Path(v).exists():
            return ToolResult(text=f"[ERROR] game video missing: {v}")
        games[str(i)] = {"name": g.get("name", f"G{i}"), "video": v,
                         "video_lowres": g.get("video_lowres", v),
                         "duration": round(_dur_of(v), 2)}
    match = {"source": "lol", "game": args.get("game", ""),
             "home": args.get("home", ""), "away": args.get("away", ""),
             "event_title": args.get("event_title", ""), "games": games}
    mp = out_dir / "match.json"
    mp.write_text(json.dumps(match, ensure_ascii=False, indent=1), encoding="utf-8")
    return ToolResult(text=f"{match['home']} vs {match['away']} | {len(games)} game(s) -> {mp}",
                      data={"match_path": str(mp), "n_games": len(games)},
                      artifacts=[str(mp)])


# ================================================================ lol_arrange
def _cuts_from_shots(sj):
    shots = sj.get("shots") or []
    cuts = [round(float(s["start"]), 3) for s in shots[1:]]
    if shots:
        cuts.append(round(float(shots[-1]["end"]), 3))
    return cuts


def _snap(t, cuts, back, fwd, prefer):
    cand = [c for c in cuts if t - back <= c <= t + fwd]
    if not cand:
        return t
    fore = [c for c in cand if (c - t) * prefer >= 0]
    return (min(fore, key=lambda c: abs(c - t)) if fore else min(cand, key=lambda c: abs(c - t)))


def _pin_vlm(t, game_idx, events, win=12.0, chain_gap=6.0):
    """v2 精定位: 把 ASR 时间 t 吸附到窗口内最近的 VLM 事件;并把间隔<=chain_gap 的
    相邻事件链成一个完整过程(团战->接推进),窗口下限=真实事件区间。"""
    evs = sorted([e for e in events if str(e.get("game", 1)) == str(game_idx)],
                 key=lambda e: e["src_start"])
    bi = None; bc = None
    for i, e in enumerate(evs):
        c = (e["src_start"] + e["src_end"]) / 2
        if abs(c - t) <= win and (bi is None or abs(c - t) < abs(bc - t)):
            bi, bc = i, c
    if bi is None:
        return None
    s, en = evs[bi]["src_start"], evs[bi]["src_end"]
    j = bi
    while j + 1 < len(evs) and evs[j + 1]["src_start"] - en <= chain_gap:
        j += 1; en = max(en, evs[j]["src_end"])
    j = bi
    while j - 1 >= 0 and s - evs[j - 1]["src_end"] <= chain_gap:
        j -= 1; s = min(s, evs[j]["src_start"])
    return (s, en, bc)  # (in, out, center)


def _validate_outline(outline):
    issues = []
    if not outline.get("teams_cn", {}).get("home"):
        issues.append("teams_cn.home/away required")
    beats = outline.get("beats") or []
    if not beats:
        issues.append("beats empty")
    kinds = {"open", "fight", "kill", "objective", "tower", "ending"}
    prev_t = -1.0
    for b in beats:
        k = b.get("kind")
        if k not in kinds:
            issues.append(f"beat {b.get('idx')}: kind must be {sorted(kinds)}"); continue
        if k == "open":
            continue
        if not isinstance(b.get("t"), (int, float)):
            issues.append(f"beat {b.get('idx')}: t(游戏秒) required"); continue
        if b["t"] < prev_t - 1:
            issues.append(f"beat {b.get('idx')}: 时间倒序")
        prev_t = b["t"]
    return issues


def _sim_need_out(sents, event_t, in_t, hl):
    """模拟 _place 的摆放逻辑, 返回该拍台词讲完时的源时间秒(含留白); 无台词返回 None。
    句子时长优先用 TTS 实测 dur(script_tts.json), 否则按字数估。"""
    if not sents:
        return None
    prev_end = None; mx = None
    for s in sents:
        dur = float(s.get("dur") or (len(s["text"]) / 4.8 + 0.4))
        a = s.get("anchor", "flow"); off = float(s.get("offset", 0.0))
        if a == "event":
            planned = event_t + off
        elif a == "bridge":
            planned = in_t - 1.2
        elif a == "post":
            planned = event_t + (CALL_SLOT if hl else 0.0) + off
        else:
            planned = (prev_end + 0.15) if prev_end is not None else in_t - 1.0
        st = planned if prev_end is None else max(planned, prev_end + 0.12)
        prev_end = st + dur
        mx = prev_end if mx is None else max(mx, prev_end)
    return mx + NARR_TAIL


# ---------------- mode="script": 解说稿驱动摘片 ----------------
# 范式与 window 模式相反: 先有从头到尾的解读稿(每句标注它讲的源画面秒 t),
# 画面按稿摘 —— 每组台词摘一段刚好讲完的画面, 硬事件句由 VLM 钉到动作帧。
# 没有词的画面不会被摘进来, 空窗在结构上不存在(只剩呐喊后的呼吸口)。

def _sent_dur(s):
    return float(s.get("dur") or (len(s["text"]) / 4.8 + 0.4))


def _group_moments(sents):
    """按 t 跳变把一拍的句子分成若干"时刻组", 每组对应一个源画面切片。
    无 t 的句子跟随前句(画面连续讲下去)。"""
    groups, cur, cursor = [], [], None    # cursor: 当前组讲完时画面播到的源秒
    for s in sents:
        st = s.get("t")
        if cur and st is not None and cursor is not None and float(st) - cursor > JUMP_GAP:
            groups.append(cur); cur = []; cursor = None
        cur.append(s)
        if st is not None:
            cursor = float(st) + _sent_dur(s) + 0.15
        elif cursor is not None:
            cursor += _sent_dur(s) + 0.15
    if cur:
        groups.append(cur)
    return groups


def _clip_layout(group, clip_in, hl, hard_te=None):
    """摆一组句子: 前向链 + t 软约束; 硬句钉死在 hard_te(事件帧), 前面的铺垫句
    向前回填(解说比画面早起口是自然的), 后面的句子从硬句(含呐喊呼吸口)重新前推。
    假定每组至多一个硬句(写作纪律)。返回 (每句片内偏移, 末句讲完偏移)。"""
    hi = next((i for i, s in enumerate(group) if s.get("hard")), None)
    locs, prev_end = [], None
    for s in group:
        want = 0.2 if prev_end is None else prev_end + 0.15
        st = s.get("t")
        if st is not None and not s.get("hard"):
            want = max(want, float(st) - clip_in - 0.8)
        locs.append(want)
        prev_end = want + _sent_dur(s)
        if s.get("hard") and hl:
            prev_end += CALL_SLOT
    if hi is not None and hard_te is not None:
        locs[hi] = hard_te - clip_in - HARD_LEAD
        for j in range(hi - 1, -1, -1):                      # 铺垫回填
            locs[j] = min(locs[j], locs[j + 1] - _sent_dur(group[j]) - 0.15)
        prev_end = locs[hi] + _sent_dur(group[hi]) + (CALL_SLOT if hl else 0.0)
        for j in range(hi + 1, len(group)):                  # 硬句后重新前推
            want = prev_end + 0.15
            stj = group[j].get("t")
            if stj is not None:
                want = max(want, float(stj) - clip_in - 0.8)
            locs[j] = want
            prev_end = locs[j] + _sent_dur(group[j])
    last_end = max(loc + _sent_dur(s) for loc, s in zip(locs, group))
    if hi is not None and hl:
        last_end = max(last_end, locs[hi] + _sent_dur(group[hi]) + CALL_SLOT)
    return locs, last_end


def _solve_clip(group, hl, pin, gdur):
    """解切片入点: 硬事件句起口落在事件帧前 HARD_LEAD; 铺垫被回填出片头时
    把画面入点提前(铺垫词盖在事件前的真实画面上)。"""
    hi = next((i for i, s in enumerate(group) if s.get("hard")), None)
    te = None
    if hi is not None:
        te = pin[2] if pin else (float(group[hi]["t"]) if group[hi].get("t") is not None else None)
    clip_in = float(group[0]["t"]) - CLIP_PRE
    locs, last_end = _clip_layout(group, clip_in, hl, te)
    if locs[0] < 0.2:
        clip_in = max(0.0, clip_in - (0.2 - locs[0]))
        locs, last_end = _clip_layout(group, clip_in, hl, te)
    out = clip_in + last_end + NARR_TAIL
    if pin:
        out = max(out, min(pin[1] + 0.8, out + ACTION_SLACK))   # 动作演完再切
    return round(clip_in, 3), round(min(out, gdur), 3), locs


def _arrange_script_mode(out_dir, args, match, outline, sents_by_beat, vlm_events):
    beats = outline["beats"]
    co = outline.get("cold_open") or {}
    flashes = [{"game": str(fl.get("game", 1)), "in": round(fl["t"] - FLASH_PRE, 3),
                "out": round(fl["t"] + FLASH_POST, 3)} for fl in co.get("flashes", [])]
    open_dur = sum(f["out"] - f["in"] for f in flashes) + TITLE_SEC

    clips, issues = [], []
    for b in beats:
        if b["kind"] == "open":
            continue
        sents = sents_by_beat.get(b["idx"]) or []
        if not sents:
            issues.append(f"beat{b['idx']} 无台词 — script 模式画面=台词的函数, 无词不摘片")
            continue
        if sents[0].get("t") is None:
            issues.append(f"beat{b['idx']} 首句缺 t(它讲的是比赛第几秒)")
            continue
        g = str(b.get("game", 1)); gdur = match["games"][g]["duration"]
        hl = bool(b.get("highlight"))
        for group in _group_moments(sents):
            if group[0].get("t") is None and clips:   # 跳切组首句无 t: 并回上一片
                clips[-1]["_sents"] += group
                cin, cout, locs = _solve_clip(clips[-1]["_sents"], clips[-1]["highlight"],
                                              clips[-1].get("_pin"), gdur)
                clips[-1].update({"in": cin, "out": cout, "_locs": locs})
                continue
            hs = next((s for s in group if s.get("hard") and s.get("t") is not None), None)
            pin = _pin_vlm(float(hs["t"]), g, vlm_events) if hs is not None else None
            cin, cout, locs = _solve_clip(group, hl, pin, gdur)
            clips.append({"beat": b["idx"], "kind": "seg", "tag": b["kind"], "game": g,
                          "event_t": round(pin[2] if pin else float(group[0]["t"]), 2),
                          "in": cin, "out": cout, "highlight": hl,
                          "_locs": locs, "_sents": group, "_pin": pin})
    if not clips:
        return ToolResult(text="outline_invalid: " + "; ".join(issues[:5]),
                          data={"status": "outline_invalid", "issues": issues})

    # 源时间单调: 相邻切片重叠 -> 先收上一片的动作余量, 不够再顺移本片(并报告)
    for a, c in zip(clips, clips[1:]):
        if c["game"] != a["game"] or c["in"] >= a["out"] + 0.1:
            continue
        a_min = a["in"] + a["_locs"][-1] + _sent_dur(a["_sents"][-1]) + 0.3
        a["out"] = round(max(a_min, c["in"] - 0.1), 3)
        if c["in"] < a["out"] + 0.1:
            issues.append(f"beat{a['beat']}->beat{c['beat']} 画面重叠 {a['out']-c['in']:.1f}s, "
                          f"beat{c['beat']} 顺移(硬钉可能漂移)")
            shift = a["out"] + 0.1 - c["in"]
            c["in"] = round(c["in"] + shift, 3); c["out"] = round(c["out"] + shift, 3)
    ending = [c for c in clips if c["tag"] == "ending"]
    if ending:
        ending[-1]["kind"] = "end"

    cur = open_dur
    plan = []
    ob = next((x for x in beats if x["kind"] == "open"), None)
    if ob is not None:                       # 开场句骑在快闪蒙太奇上, 从 0.4s 链排
        prev = 0.4
        for s in sents_by_beat.get(ob["idx"], []):
            plan.append({"beat": ob["idx"], "text": s["text"], "start": round(prev, 2),
                         "dur": round(_sent_dur(s), 2)})
            prev += _sent_dur(s) + 0.15
        if prev > open_dur + 1.5:
            issues.append(f"开场白 {prev:.1f}s 超出冷开场 {open_dur:.1f}s, 加快闪或删句")
    for c in clips:
        c["reel_in"] = round(cur, 2)
        c["reel_event"] = round(cur + c["event_t"] - c["in"], 2)
        for s, loc in zip(c["_sents"], c["_locs"]):
            plan.append({"beat": c["beat"], "text": s["text"], "start": round(cur + loc, 2),
                         "dur": round(_sent_dur(s), 2)})
        cur += c["out"] - c["in"]
        if c["kind"] == "end":
            cur += FREEZE
    total = round(cur, 2)
    for c in clips:
        c.pop("_sents", None); c.pop("_locs", None); c.pop("_pin", None)

    # 覆盖审计: 无解说空窗一目了然, 这是"讲清楚比赛"的机器化验收
    gaps, cursor = [], 0.0
    for p in sorted(plan, key=lambda x: x["start"]):
        if p["start"] - cursor > 2.0:
            gaps.append((round(cursor, 1), round(p["start"] - cursor, 1)))
        cursor = max(cursor, p["start"] + p["dur"])
    body_end = total - (FREEZE if ending else 0.0)
    if body_end - cursor > 2.0:
        gaps.append((round(cursor, 1), round(body_end - cursor, 1)))
    max_gap = max((g[1] for g in gaps), default=0.0)
    speech = sum(p["dur"] for p in plan)

    reel = {"mode": "script", "match_path": str(args["match_path"]), "open_dur": round(open_dur, 2),
            "title_sec": TITLE_SEC, "flashes": flashes, "segs": clips, "total": total,
            "freeze": FREEZE, "gap_breath": 0.0, "plan": plan}
    (out_dir / "reel.json").write_text(json.dumps(reel, ensure_ascii=False, indent=1), encoding="utf-8")
    rpt = [f"script 模式: {len(clips)} 切片, 成片预计 {total:.0f}s, 语音 {speech:.0f}s "
           f"(覆盖 {speech/max(total,1)*100:.0f}%), 最大空窗 {max_gap:.1f}s (QC 门 {QC_MAX_GAP}s)"]
    rpt += [f"  空窗 {g[1]}s @ 成片{g[0]}s" for g in gaps if g[1] > 4.0]
    rpt += [f"  [!] {i}" for i in issues]
    (out_dir / "coverage_report.txt").write_text("\n".join(rpt), encoding="utf-8")
    return ToolResult(text=rpt[0] + ("; issues: " + "; ".join(issues[:3]) if issues else ""),
                      data={"status": "ok" if max_gap <= QC_MAX_GAP and not issues else "check",
                            "total_sec": total, "n_clips": len(clips), "speech_sec": round(speech, 1),
                            "max_gap": max_gap, "gaps": gaps, "issues": issues,
                            "reel_path": str(out_dir / "reel.json")},
                      artifacts=[str(out_dir / "reel.json"), str(out_dir / "coverage_report.txt")])


def lol_arrange(args: dict, ctx: RunContext) -> ToolResult:
    out_dir = Path(args.get("out_dir", "out"))
    try:
        match = json.load(open(args["match_path"]))
        outline = json.load(open(args["outline_path"]))
        shots = {str(h): json.load(open(p)) for h, p in (args.get("shots_paths") or {}).items()}
    except KeyError as e:
        return ToolResult(text=f"[ERROR] missing arg: {e}")
    except (OSError, json.JSONDecodeError) as e:
        return ToolResult(text=f"[ERROR] cannot read input: {e}")
    vlm_events = []
    if args.get("events_path") and Path(args["events_path"]).exists():
        vlm_events = json.load(open(args["events_path"]))
    # 可选: 读台词, 逐句模拟真实摆放(锚点+时长), 算出每拍"话讲完"需要画面到哪一秒 —
    # 讲清楚比赛优先, 画面窗口伸缩配合台词。script_path 可以是 writer_script.json
    # 或 script_tts.json(后者带每句真实语音时长, 最准, 推荐先 lol_tts 再 arrange)。
    sents_by_beat = {}
    if args.get("script_path") and Path(args["script_path"]).exists():
        scr = json.load(open(args["script_path"]))
        if "sentences" in scr:                     # script_tts.json (扁平, 带 dur)
            for s in scr["sentences"]:
                sents_by_beat.setdefault(s["beat"], []).append(s)
        else:                                       # writer_script.json (估时)
            for b in scr.get("beats", []):
                sents_by_beat[b["idx"]] = b.get("sentences", [])

    issues = _validate_outline(outline)
    if issues:
        return ToolResult(text="outline_invalid: " + "; ".join(issues[:5]),
                          data={"status": "outline_invalid", "issues": issues})

    if args.get("mode", "window") == "script":     # 解说稿驱动摘片(新范式)
        if not sents_by_beat:
            return ToolResult(text="[ERROR] mode=script 需要 script_path(推荐 script_tts.json, 带真实时长)")
        return _arrange_script_mode(out_dir, args, match, outline, sents_by_beat, vlm_events)

    cuts = {h: _cuts_from_shots(sj) for h, sj in shots.items()}
    beats = outline["beats"]
    co = outline.get("cold_open") or {}
    flashes = []
    for fl in co.get("flashes", []):     # [{game,t}] 名场面快闪
        g = str(fl.get("game", 1))
        flashes.append({"game": g, "in": round(fl["t"] - FLASH_PRE, 3),
                        "out": round(fl["t"] + FLASH_POST, 3)})
    open_dur = sum(f["out"] - f["in"] for f in flashes) + (GAP_BREATH if flashes else 0.0) + TITLE_SEC

    segs = []
    for b in beats:
        k = b["kind"]
        if k == "open":
            continue
        g = str(b.get("game", 1))
        pre_w, post_w = KIND_WINDOWS.get(k, (5.0, 5.0))
        pre_w = float(b.get("pre", pre_w)); post_w = float(b.get("post", post_w))
        t = float(b["t"])
        pin = _pin_vlm(t, g, vlm_events)     # v2: VLM 精定位
        if pin:
            s, t1 = pin[0] - pre_w * 0.5, pin[1] + post_w * 0.5
            t_event = pin[2]
        else:
            s, t1, t_event = t - pre_w, t + post_w, t
        c = cuts.get(g, [])
        gdur = match["games"][g]["duration"]
        s2 = max(0.0, _snap(s, c, SNAP_IN_BACK, SNAP_IN_FWD, -1))
        e2 = min(gdur, _snap(t1, c, SNAP_OUT_BACK, SNAP_OUT_FWD, +1))
        if e2 <= s2 + 1:
            e2 = min(gdur, s2 + max(4.0, pre_w + post_w))
        segs.append({"beat": b["idx"], "kind": "end" if k == "ending" else "seg",
                     "tag": k, "game": g, "event_t": t_event, "in": round(s2, 3),
                     "out": round(e2, 3), "highlight": bool(b.get("highlight"))})

    for a, b2 in zip(segs, segs[1:]):     # 同局重叠 -> 让 Agent 改大纲
        if a["game"] == b2["game"] and b2["in"] < a["out"] + 0.5:
            return ToolResult(text=f"outline_invalid: beat {a['beat']}/{b2['beat']} 画面窗口重叠,请合并或调 pre",
                              data={"status": "outline_invalid",
                                    "issues": [f"beats {a['beat']}/{b2['beat']} overlap"]})

    # 台词优先: 逐拍模拟摆放, 窗口不够讲完的向后延真实画面(不撞下一拍, 不超本局时长)
    extended = []
    for i, g in enumerate(segs):
        want = _sim_need_out(sents_by_beat.get(g["beat"]), g["event_t"], g["in"], g["highlight"])
        if not want or want <= g["out"] + 0.1:
            continue
        cap = match["games"][g["game"]]["duration"]
        if i + 1 < len(segs) and segs[i+1]["game"] == g["game"]:
            cap = min(cap, segs[i+1]["in"] - 0.5)
        new_out = min(want, cap)
        if new_out > g["out"] + 0.1:
            extended.append(f"beat{g['beat']} +{new_out - g['out']:.1f}s")
            g["out"] = round(new_out, 3)

    cur = open_dur
    for g in segs:
        g["reel_in"] = round(cur, 2)
        g["reel_event"] = round(cur + g["event_t"] - g["in"], 2)
        cur += g["out"] - g["in"]
        if g["kind"] == "end":
            cur += FREEZE
    total = round(cur, 2)

    cps = CHARS_PER_SEC
    brief_beats, brief_txt = [], []
    ob = next((b for b in beats if b["kind"] == "open"), None)
    if ob is not None:
        sec = open_dur - 0.5
        brief_beats.append({"idx": ob["idx"], "kind": "open", "sec": round(sec, 1),
                            "budget_chars": int(sec * cps[1])})
        brief_txt.append(f"拍{ob['idx']} [开场白] 骑在标题卡+{len(flashes)}个快闪上,可用 {sec:.1f}s ≈ {int(sec*cps[1])} 字")
    for i, g in enumerate(segs):
        b = next(x for x in beats if x["idx"] == g["beat"])
        region_end = segs[i+1]["reel_in"] if i+1 < len(segs) else total - 0.9
        buildup = g["reel_event"] - g["reel_in"] - 0.3
        post_start = g["reel_event"] + (CALL_SLOT if g["highlight"] else 0.0)
        post = max(0.0, region_end - 0.3 - post_start)
        bb = {"idx": g["beat"], "kind": g["tag"], "reel_in": g["reel_in"], "reel_event": g["reel_event"],
              "buildup_sec": round(buildup, 1), "buildup_chars": int(buildup*cps[0]),
              "post_sec": round(post, 1), "post_chars": int(post*cps[0]), "highlight": g["highlight"]}
        brief_beats.append(bb)
        hl = " [highlight:呐喊句钉事件秒]" if g["highlight"] else ""
        brief_txt.append(f"拍{g['beat']} [{g['tag']} {b.get('summary','')}]{hl}\n"
                         f"  铺垫 {bb['buildup_sec']}s≈{bb['buildup_chars']}字 | 事件后 {bb['post_sec']}s≈{bb['post_chars']}字\n"
                         f"  桥接句可骑跨段首(提前~1.2s起句)")

    reel = {"match_path": str(args["match_path"]), "open_dur": round(open_dur, 2),
            "title_sec": TITLE_SEC, "flashes": flashes, "segs": segs, "total": total,
            "freeze": FREEZE, "gap_breath": GAP_BREATH if flashes else 0.0}
    (out_dir / "reel.json").write_text(json.dumps(reel, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "writing_brief.txt").write_text(
        f"成片预计 {total:.0f}s(开场 {open_dur:.1f}s)。每拍字数是硬预算,可少10%不许超。\n"
        f"呐喊句(tier2)钉事件秒;桥接句骑跨段首;整篇顺读像一个人从头讲到尾。\n\n" + "\n".join(brief_txt),
        encoding="utf-8")
    (out_dir / "brief.json").write_text(json.dumps({"beats": brief_beats, "total": total},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    return ToolResult(text=(f"reel: {len(flashes)} flashes + {len(segs)} segs, 预计 {total:.0f}s "
                            f"(VLM精定位:{len(vlm_events)}事件"
                            + (f"; 台词伸窗:{', '.join(extended)}" if extended else "") + ")"),
                      data={"status": "ok", "total_sec": total, "n_segs": len(segs),
                            "reel_path": str(out_dir / "reel.json"),
                            "brief_path": str(out_dir / "writing_brief.txt")},
                      artifacts=[str(out_dir / "reel.json"), str(out_dir / "writing_brief.txt")])


# ================================================================ lol_tts (照 soccer_tts)
def _sent_fp(provider, voice, rate, text):
    return hashlib.sha1(f"{provider}\x00{voice}\x00{rate}\x00{text}".encode()).hexdigest()[:16]


def _synth_cloud(text, voice, tier, dst, ctx):
    from .tts import tts_generate
    import time
    for k in range(4):
        r = tts_generate({"text": text, "preferred_provider": "edge_tts", "speaker": voice,
                          "speech_rate": TIERS_RATE[tier], "pitch_rate": 0, "output_path": str(dst)}, ctx)
        if not r.text.startswith("[ERROR]"):
            return None
        time.sleep(8*(2**k))
    return f"edge_tts synth failed: {r.text[:120]}"


def lol_tts(args: dict, ctx: RunContext) -> ToolResult:
    out_dir = Path(args.get("out_dir", "out"))
    try:
        script = json.load(open(args["script_path"]))
    except KeyError:
        return ToolResult(text="[ERROR] script_path required")
    except (OSError, json.JSONDecodeError) as e:
        return ToolResult(text=f"[ERROR] cannot read script: {e}")
    provider = str(args.get("provider") or clean_env("VE_LOL_TTS_PROVIDER") or DEFAULT_TTS_PROVIDER).strip().lower()
    if provider in ("auto", "cloud", "cloud_tts", "edge", "edge_tts"):
        provider = DEFAULT_TTS_PROVIDER
    if provider != DEFAULT_TTS_PROVIDER:
        return ToolResult(text=f"[ERROR] unsupported provider: {provider}; expected {DEFAULT_TTS_PROVIDER}")
    voice = str(args.get("voice") or clean_env("VE_LOL_TTS_VOICE") or DEFAULT_LOL_TTS_VOICE)
    cache = out_dir / "tts_cache"; cache.mkdir(parents=True, exist_ok=True)
    sents, failed = [], []
    for b in script.get("beats", []):
        for s in b.get("sentences", []):
            tier = int(s.get("tier", 0)); text = s["text"].strip()
            rate_key = str(TIERS_RATE[tier])
            fp = _sent_fp(provider, voice, rate_key, text)
            raw = cache / f"{fp}.mp3"
            if not raw.exists() or raw.stat().st_size < 1000:
                err = _synth_cloud(text, voice, tier, raw, ctx)
                if err:
                    failed.append({"beat": b["idx"], "text": text[:30], "err": err}); continue
            norm = cache / f"{fp}_n.wav"
            if not norm.exists():
                r = _ffmpeg(["-i", str(raw), "-af", f"loudnorm=I={TIERS_LUFS[tier]}:TP=-2:LRA=7",
                             "-ar", "48000", "-ac", "2", str(norm)])
                if r.returncode:
                    failed.append({"beat": b["idx"], "text": text[:30], "err": r.stderr[-120:]}); continue
            sents.append({**s, "beat": b["idx"], "tier": tier, "audio": str(norm),
                          "dur": round(_dur_of(norm), 2)})
    if failed:
        return ToolResult(text=f"[ERROR] {len(failed)} sentences failed TTS",
                          data={"status": "tts_failed", "failed": failed})
    sp = out_dir / "script_tts.json"
    sp.write_text(json.dumps({"provider": provider, "voice": voice, "sentences": sents},
                             ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(s["dur"] for s in sents)
    return ToolResult(text=f"TTS {len(sents)} sentences, speech {total:.0f}s -> {sp}",
                      data={"status": "ok", "n_sentences": len(sents), "speech_sec": round(total, 1),
                            "script_tts_path": str(sp)}, artifacts=[str(sp)])


# ================================================================ lol_render
def _place(sentences, reel):
    segs = reel["segs"]; by = {g["beat"]: g for g in segs}
    bounds = [g["reel_in"] for g in segs[1:]] + [reel["total"] - 0.9]
    placed, issues = [], []
    for s in sentences:
        g = by.get(s["beat"]); anchor = s.get("anchor", "flow"); off = float(s.get("offset", 0.0))
        if g is None:
            s["_p"] = max(0.4, off)
        elif anchor == "event":
            s["_p"] = g["reel_event"] + off
        elif anchor == "bridge":
            s["_p"] = g["reel_in"] - min(1.2, s["dur"]*0.4)
        elif anchor == "post":
            s["_p"] = g["reel_event"] + (CALL_SLOT if g.get("highlight") else 0.0) + off
        else:
            s["_p"] = placed[-1]["start"] + placed[-1]["dur"] + 0.15 if placed else 0.4
        prev_end = placed[-1]["start"] + placed[-1]["dur"] if placed else 0.0
        st = max(s["_p"], prev_end + 0.12)
        limit = (reel["total"] - 0.9 if anchor == "bridge"
                 else next((b for b in bounds if b > s["_p"]+0.01), reel["total"]-0.9) - 0.3)
        over = st + s["dur"] - limit
        if over > 0.05:
            issues.append(f"beat{s['beat']} 越界{over:.2f}s: {s['text'][:18]}")
        if s.get("hard") and st - s["_p"] > 0.6:
            issues.append(f"beat{s['beat']} 硬锚句被挤晚: {s['text'][:18]}")
        placed.append({**s, "start": round(st, 2)})
    for s in placed:
        s.pop("_p", None)
    return placed, issues


def _place_plan(sentences, reel):
    """script 模式: 逐句按 arrange 解好的摆放计划落位(计划与稿子同序)。"""
    plan = reel.get("plan") or []
    if len(plan) != len(sentences):
        return [], [f"plan/script 句数不一致: {len(plan)} vs {len(sentences)} — 稿子改了请重跑 lol_arrange"]
    placed, issues = [], []
    prev_end = 0.0
    for s, p in zip(sentences, plan):
        if s["text"].strip() != p["text"].strip():
            return [], [f"句序与计划不一致(自 \"{s['text'][:14]}\") — 稿子改了请重跑 lol_arrange"]
        st = max(p["start"], prev_end + 0.12)
        if s.get("hard") and st - p["start"] > 0.6:
            issues.append(f"beat{p['beat']} 硬钉句被挤晚 {st-p['start']:.2f}s: {s['text'][:16]}")
        if st + s["dur"] > reel["total"] - 0.4:
            issues.append(f"beat{p['beat']} 越界: {s['text'][:16]}")
        placed.append({**s, "beat": p["beat"], "start": round(st, 2)})
        prev_end = st + s["dur"]
    return placed, issues


def _card(text_lines, dur, out, work, tag):
    font = _font()
    dt = []
    for txt, fs, yf in text_lines:
        t = escape_text(txt)
        dt.append(f"drawtext=fontfile={font}:text='{t}':x=(w-text_w)/2:y=h*{yf}-text_h/2:"
                  f"fontsize={fs}:fontcolor=white")
    vf = ",".join(dt) + f",fade=t=in:st=0:d=0.4,fade=t=out:st={max(0,dur-0.5):.2f}:d=0.5"
    p = work / f"{tag}.mp4"
    _ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=25:d={dur}",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-t", f"{dur}",
             "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", str(p)])
    return p


def _render_segments(reel, match, outline, work):
    files = []
    tcn = outline.get("teams_cn", {})
    font = _font()
    for i, f in enumerate(reel["flashes"]):
        src = match["games"][f["game"]]["video"]
        dst = work / f"flash_{i}.mp4"; dur = f["out"] - f["in"]
        vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=25"
        if i == 0:                # 标题叠在第一个快闪画面上(不再要黑色标题卡)
            l1 = escape_text(f"{tcn.get('home','')}  vs  {tcn.get('away','')}")
            l2 = escape_text(outline.get("open_title", ""))
            vf += (f",drawbox=x=0:y=0:w=iw:h=ih:color=black@0.32:t=fill"
                   f",drawtext=fontfile={font}:text='{l1}':x=(w-text_w)/2:y=h*0.40-text_h/2:"
                   f"fontsize=80:fontcolor=white:borderw=3:bordercolor=black"
                   f",drawtext=fontfile={font}:text='{l2}':x=(w-text_w)/2:y=h*0.58-text_h/2:"
                   f"fontsize=34:fontcolor=white:borderw=2:bordercolor=black"
                   f",fade=t=in:st=0:d=0.4")
        af = f"afade=t=in:st=0:d=0.04,afade=t=out:st={dur-0.04:.2f}:d=0.04"
        r = _ffmpeg(["-ss", f"{f['in']:.3f}", "-to", f"{f['out']:.3f}", "-i", src, "-vf", vf, "-af", af,
                     "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-ar", "48000", "-ac", "2", str(dst)])
        if r.returncode:
            return files, f"flash {i}: {r.stderr[-200:]}"
        files.append(dst)
    if reel["flashes"] and GAP_BREATH > 0:
        gap = work / "gap.mp4"
        _ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s=1280x720:r=25:d={GAP_BREATH}",
                 "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                 "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                 "-c:a", "aac", "-ar", "48000", "-ac", "2", str(gap)])
        files.append(gap)
    for i, g in enumerate(reel["segs"]):
        src = match["games"][g["game"]]["video"]
        dst = work / f"seg_{i:02d}.mp4"; dur = g["out"] - g["in"]
        vf = "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=25"
        af = f"afade=t=in:st=0:d=0.08,afade=t=out:st={dur-0.08:.2f}:d=0.08"
        if g["kind"] == "end":
            ec = outline.get("end_card") or {}; fz = reel.get("freeze", FREEZE); font = _font()
            vf += f",tpad=stop_mode=clone:stop_duration={fz}"
            if ec.get("line1"):
                ec1 = escape_text(ec["line1"])
                vf += (f",drawtext=fontfile={font}:text='{ec1}':x=(w-text_w)/2:y=300:fontsize=60:"
                       f"fontcolor=white:enable=gte(t\\,{dur+0.3:.2f})")
            if ec.get("line2"):
                ec2 = escape_text(ec["line2"])
                vf += (f",drawtext=fontfile={font}:text='{ec2}':x=(w-text_w)/2:y=400:fontsize=34:"
                       f"fontcolor=0xdddddd:enable=gte(t\\,{dur+0.5:.2f})")
            vf += f",fade=t=out:st={dur+fz-0.9:.2f}:d=0.9"
            af = f"apad=pad_dur={fz},afade=t=in:st=0:d=0.08,afade=t=out:st={dur+fz-1.2:.2f}:d=1.2"
        r = _ffmpeg(["-ss", f"{g['in']:.3f}", "-to", f"{g['out']:.3f}", "-i", src, "-vf", vf, "-af", af,
                     "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-ar", "48000", "-ac", "2", str(dst)])
        if r.returncode:
            return files, f"seg {i}: {r.stderr[-300:]}"
        files.append(dst)
    return files, None


def _srt_ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int((s-int(s))*1000):03d}"


def _build_srt(placed, path):
    """把每句解说按 (start, start+dur) 写成 SRT,供烧字幕。"""
    lines = []
    for i, s in enumerate(sorted(placed, key=lambda z: z["start"]), 1):
        st = s["start"]; en = st + s.get("dur", 2.0)
        lines.append(f"{i}\n{_srt_ts(st)} --> {_srt_ts(en)}\n{s['text'].strip()}\n")
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return path


def _mix(base, placed, out_path, work, subs=None):
    """动态 ducking: 解说时原声压到 BED_VOL, 无解说空窗 0.4s 内平滑抬到 GAP_VOL;
    短于 MIN_GAP 的空窗不抬(避免原解说半字冒头)。解说句 adelay 叠加。可选烧字幕。"""
    GAP_VOL, RAMP, MIN_GAP = 0.85, 0.4, 1.2
    # 解说区间 -> 合并小间隙(小空窗保持压低)
    iv = sorted((s["start"] - 0.15, s["start"] + s.get("dur", 2.0) + 0.15) for s in placed)
    duck = []
    for a, b in iv:
        if duck and a - duck[-1][1] < MIN_GAP:
            duck[-1][1] = max(duck[-1][1], b)
        else:
            duck.append([max(0.0, a), b])
    # 到最近解说区间的距离: 区间内=0 -> BED_VOL; 区间外按距离 0.4s 线性抬到 GAP_VOL
    dists = [f"max(max({a:.2f}-t\\,t-{b:.2f})\\,0)" for a, b in duck]
    expr = dists[0]
    for d in dists[1:]:
        expr = f"min({expr}\\,{d})"
    vol = f"volume='{BED_VOL}+{GAP_VOL - BED_VOL}*min(1\\,({expr})/{RAMP})':eval=frame"

    parts = []
    if subs:
        # libass 只认 family 名 (不吃文件路径), 所以这里要的是本机真装了的那个
        # family: Linux 上通常还是 Noto CJK, Win/mac 上是系统自带的雅黑/苹方。
        style = (f"FontName={ass_font_name() or SUB_FONTNAME},FontSize=18,PrimaryColour=&H00FFFFFF,"
                 f"OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,"
                 f"Alignment=2,MarginV=38")
        parts.append(f"[0:v]subtitles=filename='{os.path.abspath(subs)}':"
                     f"force_style='{style}'[v]")
        vmap = "[v]"
    else:
        vmap = "0:v"
    parts.append(f"[0:a]{vol}[bg]"); amixin = "[bg]"
    for k, s in enumerate(placed):
        ms = int(round(s["start"]*1000))
        parts.append(f"[{k+1}:a]adelay={ms}|{ms}[n{k}]"); amixin += f"[n{k}]"
    parts.append(f"{amixin}amix=inputs={len(placed)+1}:duration=first:normalize=0,"
                 f"acompressor=threshold=0.15:ratio=2:attack=200:release=800:makeup=1.5,"
                 f"alimiter=limit=0.95[out]")
    fscript = work / "mix.txt"; fscript.write_text(";".join(parts), encoding="utf-8")
    cmd = ["-i", str(base)]
    for s in placed:
        cmd += ["-i", s["audio"]]
    cmd += ["-filter_complex_script", str(fscript), "-map", vmap, "-map", "[out]",
            "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-level", "4.0", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(out_path)]
    r = _ffmpeg(cmd)
    return r.stderr[-400:] if r.returncode else None


def _qc(final, reel, placed=None):
    qc = {"pass": True, "checks": {}}
    d = _dur_of(final)
    qc["checks"]["duration"] = {"pass": abs(d - reel["total"]) < 3.0, "final": round(d, 2), "reel": reel["total"]}
    r = run_proc(["ffmpeg", "-nostdin", "-i", str(final), "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]+\}", r.stderr[-2000:], re.S)
    lufs = float(json.loads(m.group())["input_i"]) if m else None
    qc["checks"]["loudness"] = {"pass": lufs is not None and -20 <= lufs <= -12, "input_i": lufs}
    r = run_proc(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=pix_fmt", "-of", "csv=p=0", str(final)], capture_output=True, text=True)
    qc["checks"]["pix_fmt"] = {"pass": r.stdout.strip() == "yuv420p", "pix_fmt": r.stdout.strip()}
    if placed:   # 空窗门: 讲清楚比赛的机器化验收 —— 全片不允许长时间没人讲
        cursor, worst = 0.0, (0.0, 0.0)
        for p in sorted(placed, key=lambda x: x["start"]):
            g = p["start"] - cursor
            if g > worst[1]:
                worst = (cursor, g)
            cursor = max(cursor, p["start"] + p.get("dur", 2.0))
        tail = reel["total"] - reel.get("freeze", 0.0) - cursor
        if tail > worst[1]:
            worst = (cursor, tail)
        qc["checks"]["narr_gap"] = {"pass": worst[1] <= QC_MAX_GAP,
                                    "max_gap": round(worst[1], 1), "at": round(worst[0], 1)}
    qc["pass"] = all(c["pass"] for c in qc["checks"].values())
    return qc


def lol_render(args: dict, ctx: RunContext) -> ToolResult:
    out_dir = Path(args.get("out_dir", "out"))
    try:
        reel = json.load(open(args["reel_path"]))
        stts = json.load(open(args["script_tts_path"]))
        match = json.load(open(reel["match_path"]))
        outline = json.load(open(args["outline_path"]))
    except KeyError as e:
        return ToolResult(text=f"[ERROR] missing arg: {e}")
    except (OSError, json.JSONDecodeError) as e:
        return ToolResult(text=f"[ERROR] cannot read input: {e}")
    out_path = Path(args.get("output_path") or out_dir / "final.mp4")
    work = out_dir / "render_work"; work.mkdir(parents=True, exist_ok=True)

    placed, issues = (_place_plan(stts["sentences"], reel) if reel.get("mode") == "script"
                      else _place(stts["sentences"], reel))
    (out_dir / "placement.json").write_text(json.dumps(placed, ensure_ascii=False, indent=1), encoding="utf-8")
    if issues:
        tag = "placement_invalid" if reel.get("mode") == "script" else "over_budget"
        hint = ("稿子与 reel 计划不同步/硬钉漂移: 改稿后请按 tts -> arrange(mode=script) -> render 顺序重跑"
                if reel.get("mode") == "script" else "压缩对应拍文案后重跑 lol_tts + lol_render")
        return ToolResult(text=f"{tag}: " + "; ".join(issues[:4]),
                          data={"status": tag, "issues": issues, "hint": hint})
    files, err = _render_segments(reel, match, outline, work)
    if err:
        return ToolResult(text=f"[ERROR] render failed: {err}")
    lst = work / "concat.txt"; lst.write_text("".join(f"file '{os.path.abspath(f)}'\n" for f in files), encoding="utf-8")
    base = work / "base.mp4"
    r = _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(base)])
    if r.returncode:
        return ToolResult(text=f"[ERROR] concat failed: {r.stderr[-200:]}")
    subs = _build_srt(placed, work / "subs.srt")   # 解说字幕(中文黑体烧录)
    err = _mix(base, placed, out_path, work, subs=subs)
    if err:
        return ToolResult(text=f"[ERROR] mix failed: {err}")
    qc = _qc(out_path, reel, placed)
    (out_dir / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=1), encoding="utf-8")
    d = _dur_of(out_path)
    status = "ok" if qc["pass"] else "qc_failed"
    return ToolResult(text=f"final: {out_path} {d:.1f}s QC {'pass' if qc['pass'] else 'FAIL '+str([k for k,v in qc['checks'].items() if not v['pass']])}",
                      data={"status": status, "output_path": str(out_path), "duration": round(d, 2), "qc": qc},
                      artifacts=[str(out_path)], video_paths=[str(out_path)])
