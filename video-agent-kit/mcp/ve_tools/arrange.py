"""arrange_footage:电影解说"先排片、后成稿"的确定性排片器(A-lite 内核)。

纪律:大纲决定讲什么,画面决定能讲多久,文案把两者缝起来;
禁止"每句拿着秒数去素材库凑碎片"。工具不调用任何大模型——
大纲和旁白由跑技能的 Agent 写,这里只做三步确定性变换:

- action=dialogue:transcript → 带 D 编号的全片台词轴(Agent 读它写大纲)。
  D 编号以本步产出的 dialogue_index.json 为唯一权威,杜绝编号漂移。
- action=arrange:台词索引+镜头库+大纲+目标分钟数 → 排片卷 reel.json。
  每个剧情要点锚在它引用台词的时刻,从该镜头起整镜头顺延取"连续原片块"
  (块内节奏=原片剪辑师的节奏);全局光标只进不退,新接缝只出现在
  要点/拍边界。附带写作简报(每拍/每要点的真实画面秒数与字数硬预算)。
- action=anchor:排片卷+Agent 写的旁白 → 句级锚定的解说稿+事件图
  (下游 bind_narration 的输入契约)。超预算的拍结构化报错退回重写。
"""
from __future__ import annotations

import bisect
import json
import re
from pathlib import Path

from .result import ToolResult
from .run_context import RunContext

SCHEMA_VERSION = "1.0-alite"
CHARS_PER_SEC = 3.4        # 中文口播语速
NARRATION_RATIO = 0.88     # 旁白占画面时长比,余量留呼吸
SEC_PER_POINT_LO = 4.5     # 每要点画面预算下限(预算归一化夹取区间)
SEC_PER_POINT_HI = 8.0
MIN_BEAT_SEC = 10.0        # 一拍画面下限,不足向后续播补足
MAX_BEAT_SEC = 30.0        # 一拍画面上限,防单拍吃掉太多片长
OVERRUN_TOL = 1.03         # 总卷超目标片长 3% 才回吐
OVER_CHAR_TOL = 1.15       # 单拍旁白超预算 15% 才判超(与写稿"可少不许超"配合)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def arrange_footage(args: dict, ctx: RunContext) -> ToolResult:
    action = args.get("action")
    if action == "dialogue":
        return _action_dialogue(args, ctx)
    try:
        if action == "arrange":
            return _action_arrange(args, ctx)
        if action == "anchor":
            return _action_anchor(args, ctx)
    except ValueError as exc:
        # 输入数据脏(如 outline 引用不存在的台词编号): 结构化返回, 不裸抛
        return ToolResult(text=f"[ERROR] {exc}", data={"error": "invalid_input"})
    return ToolResult(
        text="[ERROR] action must be one of: dialogue, arrange, anchor",
        data={"error": "bad_action", "got": action})


# ---------------------------------------------------------------- dialogue --
def _action_dialogue(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("transcript_path"):
        return ToolResult(text="[ERROR] transcript_path is required")
    tp = ctx.resolve(args["transcript_path"])
    if not tp.is_file():
        return ToolResult(text=f"[ERROR] transcript not found: {tp}")
    try:
        rows = _load_json(tp)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] invalid transcript JSON: {exc}")
    if isinstance(rows, dict):
        rows = rows.get("segments", [])
    rows = [r for r in rows
            if isinstance(r, dict) and str(r.get("text", "")).strip()
            and isinstance(r.get("start"), (int, float))]
    if not rows:
        return ToolResult(
            text="[ERROR] transcript has no usable speech segments — "
            "dialogue-driven recap needs spoken lines; fall back to a "
            "vision-based flow for this film",
            data={"error": "empty_transcript"})
    rows.sort(key=lambda r: float(r["start"]))

    index = [{"id": f"D{i + 1:04d}", "start": float(r["start"]),
              "end": float(r.get("end", r["start"])),
              "speaker": str(r.get("speaker", "?")),
              "text": str(r["text"]).strip()}
             for i, r in enumerate(rows)]
    axis = "\n".join(f"{r['id']}[{r['start']:.0f}s] {r['speaker']}: {r['text']}"
                     for r in index)

    out_txt = ctx.resolve(args.get("output_txt") or "out/dialogue_axis.txt")
    out_json = ctx.resolve(args.get("output_json") or "out/dialogue_index.json")
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(axis + "\n", encoding="utf-8")
    _save_json(index, out_json)
    n_chars = sum(len(r["text"]) for r in index)
    return ToolResult(
        text=(f"Dialogue axis ready: {len(index)} lines / {n_chars} chars, "
              f"{index[0]['start']:.0f}s → {index[-1]['start']:.0f}s. "
              f"Read {ctx.virtualize(out_txt)} like a screenplay to write the "
              "outline; cite line ids (D0001) as evidence for every point."),
        data={"n_lines": len(index), "n_chars": n_chars,
              "first_line_sec": index[0]["start"],
              "last_line_sec": index[-1]["start"]},
        artifacts=[str(out_txt), str(out_json)])


# ----------------------------------------------------------------- arrange --
def _check_outline(outline: dict, n_dlg: int, minutes: float) -> dict | None:
    """大纲结构校验;返回 None=通过,否则结构化错误(Agent 拿去重写)。"""
    beats = outline.get("beats")
    if not isinstance(beats, list) or not beats:
        return {"error": "outline_invalid", "why": "beats missing/empty"}
    expect = max(24, int(minutes * 3))
    if len(beats) < expect * 0.5:
        return {"error": "outline_invalid",
                "why": f"only {len(beats)} beats, expected ≈{expect} "
                       "(about 3 beats per output minute)"}
    n_pts = bad = 0
    issues = []
    for bi, b in enumerate(beats, 1):
        for p in b.get("points", []) if isinstance(b, dict) else []:
            n_pts += 1
            ids = [x for x in p.get("dlg", [])
                   if re.fullmatch(r"D\d{4}", str(x)) and 0 < int(str(x)[1:]) <= n_dlg]
            if not ids:
                bad += 1
                if len(issues) < 10:
                    issues.append(f"beat{bi}: point '{str(p.get('text'))[:30]}' "
                                  f"has no valid dlg ids {p.get('dlg')}")
            p["dlg"] = ids
    if n_pts == 0 or bad > n_pts * 0.1:
        return {"error": "outline_invalid",
                "why": f"{bad}/{n_pts} points cite no valid dialogue id",
                "issues": issues}
    return None


def _take_block(shots: list[dict], shot_starts: list[float], state: dict,
                t_anchor: float, need: float, hard_end: float) -> list[dict]:
    """从锚点所在镜头起整镜头顺延取满 need 秒;全局光标只进不退。"""
    a = max(t_anchor - 1.0, state["cursor"])
    if a >= hard_end:
        return []
    i = max(0, bisect.bisect_right(shot_starts, a) - 1)
    spans, got = [], 0.0
    first = True
    while i < len(shots) and got < need:
        s = shots[i]
        if float(s["start"]) >= hard_end:
            break               # 拍边界是硬边界: 不吞下一拍的镜头(shots 有序,后面更远)
        # 末片同样被拍边界截断 — 长镜头曾在这里整个越界,把全局光标推进下一拍
        # 领地,造成后续拍锚点全在光标之前(锚漂移/整拍 dropped)
        lo, hi = max(a, float(s["start"])), min(float(s["end"]), hard_end)
        if first:
            # 入块处是跳切点,第一片必须≥1.5s(短了就是"短闪"):
            # 不够先把入点向镜头头部提前(锚点时刻仍在片内),
            # 镜头剩余本身太短则整个顺延到下一镜头。
            lo = max(state["cursor"], float(s["start"]), min(lo, hi - 1.5))
            if hi - lo < 1.3:
                i += 1
                continue
            first = False
        if hi > lo + 0.2:
            spans.append({"shot_id": s["shot_id"], "start": round(lo, 3),
                          "end": round(hi, 3), "sec": round(hi - lo, 2)})
            got += hi - lo
        i += 1
    if spans:
        state["cursor"] = spans[-1]["end"]
    return spans


def _trim_overrun(reels: dict, plan: list[dict], target: float) -> float:
    """总卷超目标片长 3% 时,从最长拍的尾巴回吐(整 span 或截尾,保≥1.5s片):
    只动拍尾不动拍中,不产生新接缝;拍长不跌破 MIN_BEAT_SEC。"""
    total = sum(r["reel_sec"] for r in reels.values())
    trimmed, frozen = 0.0, set()
    while total > target * OVERRUN_TOL:
        cand = [p for p in plan if p["seg_id"] not in frozen
                and reels[p["seg_id"]]["reel_sec"] > MIN_BEAT_SEC + 0.5]
        if not cand:
            break
        p = max(cand, key=lambda x: reels[x["seg_id"]]["reel_sec"])
        r = reels[p["seg_id"]]
        need = total - target
        room = r["reel_sec"] - MIN_BEAT_SEC
        sp = r["spans"][-1]
        if len(r["spans"]) > 1 and sp["sec"] <= min(need, room) + 0.2:
            cut = sp["sec"]
            r["spans"].pop()
        else:
            cut = min(need, room, sp["sec"] - 1.5)
            if cut <= 0.2:
                frozen.add(p["seg_id"])
                continue
            sp["end"] = round(sp["end"] - cut, 3)
            sp["sec"] = round(sp["sec"] - cut, 2)
        r["reel_sec"] = round(r["reel_sec"] - cut, 2)
        total -= cut
        trimmed += cut
    return trimmed


def _action_arrange(args: dict, ctx: RunContext) -> ToolResult:
    for k in ("dialogue_index_path", "shots_path", "outline_path", "minutes"):
        if not args.get(k):
            return ToolResult(text=f"[ERROR] {k} is required")
    try:
        minutes = float(args["minutes"])
        if not minutes > 0:
            raise ValueError
    except (TypeError, ValueError):
        return ToolResult(text="[ERROR] minutes must be a positive number")
    try:
        dlg = _load_json(ctx.resolve(args["dialogue_index_path"]))
        timeline = _load_json(ctx.resolve(args["shots_path"]))
        outline = _load_json(ctx.resolve(args["outline_path"]))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] failed to load inputs: {exc}")
    shots = sorted(timeline.get("shots", []), key=lambda s: float(s["start"]))
    if not shots:
        return ToolResult(text="[ERROR] shots_path has no shots — run detect_shots first")
    bad = _check_outline(outline, len(dlg), minutes)
    if bad:
        return ToolResult(
            text="[ERROR] outline_invalid: " + bad.get("why", "") +
            " — rewrite the outline (cite real D-ids from the dialogue axis) "
            "and call arrange again",
            data=bad)

    shot_starts = [float(s["start"]) for s in shots]
    film_end = float(shots[-1]["end"])
    by_id = {r["id"]: r for r in dlg}

    def dlg_t(x: str) -> float:
        row = by_id.get(str(x))
        if row is None:
            # 索引被手改出编号空洞时不裸 KeyError; outline 校验容忍 ≤10% 坏引用,
            # 漏网的在这里以可定位的 ValueError 收口(外层按结构化错误返回)
            raise ValueError(f"outline 引用的台词编号不存在: {x}")
        return float(row["start"])

    # 拍的时间锚:每拍 t0 = 其要点台词的最早时刻;强制时间单调
    beats = []
    for b in outline["beats"]:
        pts = [p for p in b.get("points", []) if p.get("dlg")]
        if not pts:
            continue
        for p in pts:
            p["t"] = min(dlg_t(x) for x in p["dlg"])
        pts.sort(key=lambda p: p["t"])
        beats.append({"summary": str(b.get("summary", "")), "points": pts,
                      "t0": pts[0]["t"]})
    beats.sort(key=lambda b: b["t0"])
    for cur, nxt in zip(beats, beats[1:]):
        cur["t1"] = nxt["t0"]
    if beats:
        last = beats[-1]
        last["t1"] = min(film_end, max(dlg_t(x) for p in last["points"]
                                       for x in p["dlg"]) + 40.0)

    # 预算归一化:每要点画面秒数由目标片长反推,不再用固定值
    # (固定 6.5s/点在要点多的大纲上会把总卷推超目标 8%+)。
    # 卷是素材带,旁白只占卷的 NARRATION_RATIO——目标卷长要除回去,
    # 否则成片会比 minutes 短 12%。
    target_reel = minutes * 60.0 / NARRATION_RATIO
    n_points = sum(len(b["points"]) for b in beats)
    try:
        sec_per_point = float(args.get("sec_per_point") or 0) or None
    except (TypeError, ValueError):
        return ToolResult(text="[ERROR] sec_per_point must be a number")
    if sec_per_point is None:
        sec_per_point = min(SEC_PER_POINT_HI,
                            max(SEC_PER_POINT_LO, target_reel / max(n_points, 1)))

    state = {"cursor": 0.0}
    reels: dict[str, dict] = {}
    plan: list[dict] = []
    dropped: list[str] = []
    for bi, b in enumerate(beats, 1):
        seg_id = f"s{bi:03d}"
        spans: list[dict] = []
        pt_secs: list[float] = []
        for pi, p in enumerate(b["points"], 1):
            got = sum(x["sec"] for x in spans)
            if got >= MAX_BEAT_SEC:
                pt_secs.append(0.0)
                continue
            blk = _take_block(shots, shot_starts, state, p["t"],
                              min(sec_per_point, MAX_BEAT_SEC - got), b["t1"])
            for sp in blk:
                sp["point"] = pi          # 块归属要点:句子只配自己要点的画面
            spans += blk
            pt_secs.append(sum(x["sec"] for x in blk))
        # 不足下限 → 块尾向后续播补足(不跳取),记到最后一个有画面的要点
        if spans and sum(x["sec"] for x in spans) < MIN_BEAT_SEC:
            blk = _take_block(shots, shot_starts, state, state["cursor"],
                              MIN_BEAT_SEC - sum(x["sec"] for x in spans),
                              b["t1"] + 20.0)
            last_pt = spans[-1]["point"]
            for sp in blk:
                sp["point"] = last_pt
            spans += blk
            pt_secs[last_pt - 1] += sum(x["sec"] for x in blk)
        if not spans:
            dropped.append(f"beat{bi}: {b['summary'][:24]}")
            continue
        reel_sec = round(sum(x["sec"] for x in spans), 2)
        reels[seg_id] = {"seg_id": seg_id, "idx": bi, "spans": spans,
                         "reel_sec": reel_sec, "char_cap": 0}
        plan.append({"idx": bi, "seg_id": seg_id, "summary": b["summary"],
                     "points": [dict(text=p["text"]) for p in b["points"]],
                     "sec": reel_sec})

    if not plan:
        return ToolResult(text="[ERROR] arrange produced no beats — outline "
                          "anchors may all point before the global cursor",
                          data={"error": "empty_plan", "dropped": dropped})

    trimmed = 0.0
    if args.get("trim", True):
        trimmed = _trim_overrun(reels, plan, target_reel)

    # 语速可按音色校准:字数预算 = 画面秒 × 旁白占比 × 语速。
    # 默认 3.4 字/秒偏保守; 云端音色需按实测校准, 不校准会把稿写薄。
    try:
        cps = float(args.get("chars_per_sec") or CHARS_PER_SEC)
        if not 2.0 <= cps <= 7.0:
            raise ValueError
    except (TypeError, ValueError):
        return ToolResult(text="[ERROR] chars_per_sec must be a number in [2, 7]")

    # 回吐后统一从 spans 反推:要点秒数/字数预算/视觉短语接缝
    n_seams = 0
    for p in plan:
        r = reels[p["seg_id"]]
        spans = r["spans"]
        r["reel_sec"] = round(sum(x["sec"] for x in spans), 2)
        r["char_cap"] = int(r["reel_sec"] * NARRATION_RATIO * cps)
        pt_sec: dict[int, float] = {}
        for sp in spans:
            pt_sec[int(sp["point"])] = pt_sec.get(int(sp["point"]), 0.0) + sp["sec"]
        for j, pt in enumerate(p["points"], 1):
            sec = round(pt_sec.get(j, 0.0), 1)
            pt["sec"] = sec
            pt["chars"] = int(sec * NARRATION_RATIO * cps)
        phrases = []
        for sp in spans:
            if phrases and sp["start"] - phrases[-1][-1]["end"] <= 0.1:
                phrases[-1].append(sp)
            else:
                phrases.append([sp])
        p["sec"] = r["reel_sec"]
        p["chars"] = r["char_cap"]
        p["n_phrases"] = len(phrases)
        n_seams += len(phrases) - 1

    total_sec = round(sum(r["reel_sec"] for r in reels.values()), 1)
    est_film = round(total_sec * NARRATION_RATIO, 1)
    names = "、".join(str(c.get("name", "")) for c in
                     outline.get("characters", []))[:200]
    brief = (f"角色表:{names}\n目标时长:约{minutes:.0f}分钟"
             f"(画面已剪好共{total_sec:.0f}秒)\n\n" + "\n".join(
                 f"拍{p['idx']}(画面{p['sec']:.0f}秒,总预算{p['chars']}字): "
                 f"{p['summary']}\n" +
                 "\n".join(f"  要点{j + 1}" +
                           (f"(画面{pt['sec']:.0f}秒,≤{pt['chars']}字)"
                            if pt["sec"] > 0.5 else "(无画面)") +
                           f": {pt['text']}"
                           for j, pt in enumerate(p["points"]))
                 for p in plan))

    reel_out = ctx.resolve(args.get("reel_json") or "out/reel.json")
    plan_out = ctx.resolve(args.get("plan_json") or "out/plan.json")
    brief_out = ctx.resolve(args.get("brief_txt") or "out/writing_brief.txt")
    _save_json({"schema_version": SCHEMA_VERSION, "beats": reels,
                "narration_ratio": NARRATION_RATIO,
                "chars_per_sec": round(cps, 2),
                "target_reel_sec": round(target_reel, 1),
                "sec_per_point": round(sec_per_point, 2)}, reel_out)
    _save_json(plan, plan_out)
    brief_out.parent.mkdir(parents=True, exist_ok=True)
    brief_out.write_text(brief + "\n", encoding="utf-8")
    return ToolResult(
        text=(f"Arranged {len(plan)} beats · reel {total_sec:.0f}s "
              f"(target reel {target_reel:.0f}s, trimmed {trimmed:.0f}s) · "
              f"estimated film ≈{est_film:.0f}s vs asked {minutes * 60:.0f}s · "
              f"{n_seams} intra-beat seams "
              f"({n_seams / max(len(plan), 1):.1f}/beat) · "
              f"{sec_per_point:.1f}s per point. Write narration per "
              f"{ctx.virtualize(brief_out)}: hard char budgets per beat AND "
              "per point, footage decides how long you may talk."),
        data={"n_beats": len(plan), "reel_sec": total_sec,
              "target_reel_sec": round(target_reel, 1),
              "est_film_sec": est_film,
              "trimmed_sec": round(trimmed, 1),
              "seams_per_beat": round(n_seams / max(len(plan), 1), 2),
              "sec_per_point": round(sec_per_point, 2),
              "dropped_beats": dropped},
        artifacts=[str(reel_out), str(plan_out), str(brief_out)])


# ------------------------------------------------------------------ anchor --
def _split_sents(rows: list[dict]) -> list[dict]:
    """写手常把整拍塞进一个 sentence 对象——机械按标点重分句,保住句级锚定粒度。"""
    out = []
    for s in rows:
        for part in re.split(r"(?<=[。！？!?；;])", str(s.get("text", ""))):
            part = part.strip()
            if part:
                out.append({"text": part, "point": s.get("point", 1)})
    return out


def _action_anchor(args: dict, ctx: RunContext) -> ToolResult:
    for k in ("reel_path", "plan_path", "script_path"):
        if not args.get(k):
            return ToolResult(text=f"[ERROR] {k} is required")
    try:
        reel = _load_json(ctx.resolve(args["reel_path"]))
        plan = _load_json(ctx.resolve(args["plan_path"]))
        sdata = _load_json(ctx.resolve(args["script_path"]))
    except Exception as exc:
        return ToolResult(text=f"[ERROR] failed to load inputs: {exc}")
    reels = reel.get("beats", {})
    cps = float(reel.get("chars_per_sec") or CHARS_PER_SEC)
    def _idx(v) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            return -1

    # idx 统一 int 归一: 写手把 idx 写成字符串时, 句子失配会报 script_invalid
    # 兜底, 但 highlight 侧失配曾是静默全丢(留白归零无告警)
    by_idx = {_idx(b.get("idx")): b.get("sentences", [])
              for b in sdata.get("beats", []) if isinstance(b, dict)}
    hl_idx = {_idx(b.get("idx")) for b in sdata.get("beats", [])
              if isinstance(b, dict) and bool(b.get("highlight"))}

    missing = [p["idx"] for p in plan
               if p["idx"] not in by_idx or not by_idx[p["idx"]]]
    if len(missing) > len(plan) * 0.1:
        return ToolResult(
            text=f"[ERROR] script_invalid: beats {missing[:10]} have no "
            "sentences — cover every beat in the brief, then call anchor again",
            data={"error": "script_invalid", "missing_beats": missing})

    over = []
    for p in plan:
        n = sum(len(str(s.get("text", ""))) for s in by_idx.get(p["idx"]) or [])
        if n > p["chars"] * OVER_CHAR_TOL:
            over.append({"idx": p["idx"], "chars": n, "cap": p["chars"],
                         "summary": p["summary"][:30]})
    if over:
        return ToolResult(
            text=(f"[ERROR] over_budget: {len(over)} beats exceed their char "
                  "cap by >15% — narration must yield to footage; shorten "
                  "these beats (cut adjectives, keep facts) and call anchor "
                  "again: " +
                  ",".join(f"beat{o['idx']}({o['chars']}/{o['cap']})"
                           for o in over[:8])),
            data={"error": "over_budget", "beats": over})

    script: list[dict] = []
    events: list[dict] = []
    n_sent = 0
    for p in plan:
        seg_id = p["seg_id"]
        sents = _split_sents(by_idx.get(p["idx"]) or [])
        if not sents or seg_id not in reels:
            continue
        spans = reels[seg_id]["spans"]
        text = "".join(s["text"] for s in sents)
        # 句→要点→该要点的画面块直接绑定(不按全拍字数比例摊,治句画漂移):
        # 讲要点k的句子只在要点k的块里配画面;同要点多句在块内按字数细分。
        pt_spans: dict[int, list[dict]] = {}
        for sp in spans:
            pt_spans.setdefault(int(sp.get("point", 1)), []).append(sp)
        pts_avail = sorted(pt_spans)

        def spans_for(pi: int) -> list[dict]:
            if pi in pt_spans:
                return pt_spans[pi]
            prev = [k for k in pts_avail if k < pi]   # 无画面要点→就近归前
            return pt_spans[prev[-1] if prev else pts_avail[0]]

        grouped: list[tuple[int, list[dict]]] = []
        for s in sents:
            pi = int(s.get("point") or 1)
            if grouped and grouped[-1][0] == pi:
                grouped[-1][1].append(s)
            else:
                grouped.append((pi, [s]))
        units, si = [], 0
        for pi, group in grouped:
            g_spans = spans_for(pi)
            g_sec = sum(sp["sec"] for sp in g_spans)
            g_chars = max(sum(len(x["text"]) for x in group), 1)
            pos = 0.0
            for s in group:
                si += 1
                sec = len(s["text"]) / g_chars * g_sec
                w0, w1 = pos, min(pos + sec, g_sec)
                pos = w1
                # 镜头按中点归属唯一一句:锚集互不相交,DP 分组不糊
                acc, ids = 0.0, []
                for sp in g_spans:
                    mid = acc + sp["sec"] / 2
                    if w0 <= mid < w1:
                        ids.append(sp["shot_id"])
                    acc += sp["sec"]
                if not ids:             # 短句窗口没罩住镜头中点→取窗口所在镜头
                    acc = 0.0
                    for sp in g_spans:
                        if acc + sp["sec"] > (w0 + w1) / 2:
                            ids = [sp["shot_id"]]
                            break
                        acc += sp["sec"]
                units.append({"semantic_unit_id": f"{seg_id}_u{si:02d}",
                              "text": s["text"], "anchor_shot_ids": ids[:4],
                              "claim_ids": [],
                              "event_ids": [f"alb_{p['idx']:03d}"]})
                n_sent += 1
        events.append({"event_id": f"alb_{p['idx']:03d}",
                       "start": spans[0]["start"], "end": spans[-1]["end"],
                       "summary": p["summary"][:80], "importance": 0.6,
                       "narrative_role": "development", "character_ids": [],
                       "shot_ids": [x["shot_id"] for x in spans],
                       "candidate_shot_ids": [x["shot_id"] for x in spans],
                       "claims": [], "cue_ids": []})
        script.append({"seg_id": seg_id, "idx": p["idx"],
                       "source_seg_ids": [seg_id],
                       "story_scene_id": f"scene_{p['idx']:03d}",
                       "event_ids": [f"alb_{p['idx']:03d}"], "text": text,
                       "emotion": "neutral", "narrative": "development",
                       "highlight": p["idx"] in hl_idx, "use_original_audio": False,
                       "duration_is_soft": True,
                       "target_sec": round(len(text) / cps, 1),
                       "semantic_units": units})

    out_script = ctx.resolve(args.get("output_script") or "out/narration_script.json")
    out_graph = ctx.resolve(args.get("output_graph") or "out/graph.json")
    _save_json(script, out_script)
    _save_json({"title": str(args.get("title", "")),
                "schema_version": SCHEMA_VERSION, "events": events}, out_graph)
    total_chars = sum(len(s["text"]) for s in script)
    total_reel = round(sum(reels[s["seg_id"]]["reel_sec"] for s in script), 1)
    return ToolResult(
        text=(f"Anchored {len(script)} beats / {n_sent} sentences / "
              f"{total_chars} chars over a {total_reel:.0f}s reel "
              f"(narration ≈{total_chars / cps:.0f}s). Next: TTS, "
              "then bind_narration with this script + graph + reel."),
        data={"n_beats": len(script), "n_sentences": n_sent,
              "n_chars": total_chars, "reel_sec": total_reel,
              "est_narration_sec": round(total_chars / cps, 1)},
        artifacts=[str(out_script), str(out_graph)])
