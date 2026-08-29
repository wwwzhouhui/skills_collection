#!/usr/bin/env python3
"""soccer-recap 确定性工具组: 足球比赛 -> 叙事解说集锦
分工红线: 工具不调用任何大模型。比赛理解/大纲/旁白/冷读全部由主 Agent 完成,
本模块只做确定性媒体操作(数据源适配/排片/TTS/渲染混音/QC门)。

四个工具:
  soccer_ingest   足球视频适配: source=video -> out/match.json (标准比赛合同);
                  action=axis: 上下半场 transcript -> 带 C 编号的英文解说轴
  soccer_arrange  match+shots+outline(Agent写) -> reel.json + writing_brief.txt
  soccer_tts      writer_script(Agent写) -> 逐句TTS(三档情绪:语速/响度, 音调恒零) + 句级缓存
  soccer_render   reel+script_tts -> 摆放混音渲染成片 + QC硬门(黑场唯一/硬锚零偏/响度)

剪辑语法(v0.5-v0.7 实测定型, v0.8 补三项):
  - 蒙太奇内部硬切; 段间 0.3s 溶解(时长守恒: 两侧各多取 0.15s 喂 xfade, 时间轴不变);
    冷开场后 0.7s 黑场压标题卡(不留裸黑屏); 0s 淡入/片尾淡出
  - 全片解说字幕烧录(ASS 底部居中, 按摆放时刻逐句)
  - 切点吸附镜头边界; 进球回放收编(12s后>=5s中长镜头); 回放数按大纲变奏
  - 防剧透比分角标: 进球瞬间才跳分; 末帧定格+总比分字幕
  - 解说: 硬锚句钉事件秒; 桥接句骑跨切点(J-cut); highlight 拍呐喊后留白透欢呼
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from .ffproc import run_proc, escape_text
from pathlib import Path
from urllib.parse import quote

from .fonts import find_cjk_font
from .result import ToolResult
from .run_context import RunContext, clean_env

# ---------------- 剪辑常量 (v0.7 定型) ----------------
GOAL_PRE_DEFAULT, GOAL_POST = 14, 18
CHANCE_PRE, CHANCE_POST = 9, 6
SNAP_IN_BACK, SNAP_IN_FWD = 6.0, 3.0
SNAP_OUT_BACK, SNAP_OUT_FWD = 3.0, 8.0
REPLAY_SCAN_FROM, REPLAY_SHOT_MIN, REPLAY_CAP = 12, 5.0, 50
FLASH_PRE, FLASH_POST = 2.0, 0.8
GAP_BREATH = 0.7          # 冷开场后黑场"屏息" —— 全片唯一允许的黑场(压标题卡, 不裸黑)
XFADE = 0.30              # 段间溶解时长; 两侧各多取 XFADE/2 素材, 叠化吃掉延长量 => 时间轴不变
XPAD = XFADE / 2
FREEZE = 3.2              # 末帧定格
CALL_SLOT = 4.5           # 进球呐喊句预留槽位(s)
HIGHLIGHT_HOLD = 2.5      # highlight 拍呐喊后欢呼留白(s)
# 三档情绪: 音调恒 0(音调抬升会被听成换人), 只用语速+响度拉开
TIERS_RATE = {0: 12, 1: 20, 2: 28}          # edge_tts speech_rate
TIERS_LUFS = {0: -17.5, 1: -16.5, 2: -14.5}
CHARS_PER_SEC = {0: 4.9, 1: 5.1, 2: 5.3}
DEFAULT_TTS_PROVIDER = "edge_tts"
DEFAULT_SOCCER_TTS_VOICE = "zh-CN-YunjianNeural"

CJK_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]


def _font() -> str:
    for f in CJK_FONT_CANDIDATES:
        if Path(f).exists():
            return f
    # 非 Linux (以及没装 Noto CJK 的 Linux): 退到系统自带 CJK 字体; 一个都没有时
    # 仍返回首个候选, 让 ffmpeg 报"字体文件不存在"而不是静默画出豆腐块。
    return find_cjk_font("bold") or CJK_FONT_CANDIDATES[0]


def _dur_of(p: Path | str) -> float:
    out = run_proc(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip()
    return float(out)


def _ffmpeg(args: list[str]) -> subprocess.CompletedProcess:
    return run_proc(["ffmpeg", "-nostdin", "-y", "-v", "error"] + args,
                          capture_output=True, text=True)


# ================================================================
# soccer_ingest
# ================================================================

def _commentary_axis(transcripts: list[tuple[int, dict]], out_dir: Path) -> tuple[int, int]:
    lines, index = [], []
    n = 0
    for half, tr in transcripts:
        for s in tr.get("segments", []):
            txt = (s.get("text") or "").strip()
            if not txt:
                continue
            cid = f"C{n:04d}"
            mm, ss = divmod(int(s["start"]), 60)
            lines.append(f"{cid} [H{half} {mm:02d}:{ss:02d}] {txt}")
            index.append({"id": cid, "half": half, "start": round(float(s["start"]), 2),
                          "end": round(float(s.get("end", s["start"])), 2), "text": txt})
            n += 1
    (out_dir / "commentary_axis.txt").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "commentary_index.json").write_text(
        json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return n, sum(len(i["text"]) for i in index)


def soccer_ingest(args: dict, ctx: RunContext) -> ToolResult:
    action = args.get("action", "match")
    out_dir = Path(args.get("out_dir", "out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    if action == "axis":
        paths = args.get("transcript_paths") or []
        if not paths:
            return ToolResult(text="[ERROR] transcript_paths is required for action=axis")
        trs = []
        for i, p in enumerate(paths, 1):
            if not Path(p).exists():
                return ToolResult(text=f"[ERROR] transcript not found: {p}")
            trs.append((i, json.load(open(p))))
        n, chars = _commentary_axis(trs, out_dir)
        return ToolResult(
            text=f"commentary axis: {n} lines, {chars} chars -> {out_dir}/commentary_axis.txt",
            data={"lines": n, "chars": chars,
                  "axis_path": str(out_dir / "commentary_axis.txt"),
                  "index_path": str(out_dir / "commentary_index.json")},
            artifacts=[str(out_dir / "commentary_axis.txt")])

    source = str(args.get("source") or "video").strip().lower()
    if source != "video":
        return ToolResult(text=f"[ERROR] unknown source: {source} (supported: video)")
    # 只接入半场视频。事件由 Agent 通读解说轴+抽帧理解比赛后,
    # 以内联 event{half,t,minute,score_after} 写进 outline。
    game = args.get("game", "")
    halves_in = {str(k): v for k, v in (args.get("halves") or {}).items()}
    if not halves_in and game:
        video_root = Path(args.get("video_root") or "")
        vdir = video_root / Path(*[quote(p) for p in Path(game).parts])
        halves_in = {str(h): str(vdir / f"{h}_720p.mkv") for h in (1, 2)}
    halves = {}
    for h in ("1", "2"):
        p = Path(halves_in.get(h, ""))
        if not p.exists():
            return ToolResult(text=f"[ERROR] half {h} video missing: {p} (传 halves 或 game+video_root)")
        halves[h] = {"video": str(p), "video_lowres": str(p),
                     "duration": round(_dur_of(p), 2)}
    match = {"source": "video", "game": game,
             "home": args.get("home", ""), "away": args.get("away", ""),
             "date": args.get("date", ""), "final_score": args.get("final_score", ""),
             "halves": halves, "events": []}
    mp = out_dir / "match.json"
    mp.write_text(json.dumps(match, ensure_ascii=False, indent=1), encoding="utf-8")
    return ToolResult(
        text=(f"video match -> {mp}\n"
              f"H1 {halves['1']['duration']:.0f}s / H2 {halves['2']['duration']:.0f}s。"
              f"事件由解说轴和抽帧确认后以内联 event{{half,t,minute,score_after}} 写进 outline。"),
        data={"match_path": str(mp), "n_events": 0,
              "halves": {h: halves[h]["duration"] for h in halves}},
        artifacts=[str(mp)])


# ================================================================
# soccer_arrange
# ================================================================

def _cuts_from_shots(shots_json: dict) -> list[float]:
    shots = shots_json.get("shots") or []
    cuts = [round(float(s["start"]), 3) for s in shots[1:]]
    if shots:
        cuts.append(round(float(shots[-1]["end"]), 3))
    return cuts


def _snap(t: float, cuts: list[float], back: float, fwd: float, prefer: int) -> float:
    cand = [c for c in cuts if t - back <= c <= t + fwd]
    if not cand:
        return t
    fore = [c for c in cand if (c - t) * prefer >= 0]
    return (min(fore, key=lambda c: abs(c - t)) if fore else min(cand, key=lambda c: abs(c - t)))


def _replay_end(cuts: list[float], t_event: float, max_shots: int) -> float | None:
    ends = []
    for a, b in zip(cuts, cuts[1:]):
        if a < t_event + REPLAY_SCAN_FROM:
            continue
        if a > t_event + REPLAY_CAP:
            break
        if b - a >= REPLAY_SHOT_MIN and b <= t_event + REPLAY_CAP:
            ends.append(b)
            if len(ends) >= max_shots:
                break
    return ends[-1] if ends else None


def _resolve_beat_event(b: dict) -> tuple[dict | None, str | None]:
    """拍事件解析: 常规流程用内联 event{half,t,minute[,score_after,team]}。"""
    ev = b.get("event")
    if not isinstance(ev, dict):
        return None, "需要内联 event{half,t,minute[,score_after]}"
    if ev.get("half") not in (1, 2):
        return None, "event.half must be 1 or 2"
    if not isinstance(ev.get("t"), (int, float)) or ev["t"] <= 0:
        return None, "event.t (半场视频秒, 抽帧确认过的) required"
    if not isinstance(ev.get("minute"), int):
        return None, "event.minute (比赛分钟, 下半场加 45) required"
    is_goal = b.get("kind") == "goal"
    if is_goal and not re.fullmatch(r"\d+-\d+", str(ev.get("score_after", ""))):
        return None, "goal 拍需要 event.score_after 如 '1-2' (进球后 主-客)"
    return {"id": f"B{b.get('idx')}", "type": "goal" if is_goal else "chance",
            "half": int(ev["half"]), "t": float(ev["t"]), "minute": int(ev["minute"]),
            "team": ev.get("team", ""), "score_after": str(ev.get("score_after", ""))}, None


def _validate_outline(outline: dict) -> tuple[list[str], dict]:
    issues: list[str] = []
    resolved: dict = {}
    if not outline.get("teams_cn", {}).get("home") or not outline.get("teams_cn", {}).get("away"):
        issues.append("teams_cn.home/away required (比分角标用中文队名)")
    beats = outline.get("beats") or []
    if not beats:
        issues.append("beats is empty")
    prev_key = (-1, -1.0)
    kinds = {"open", "goal", "chance", "ending"}
    for b in beats:
        k = b.get("kind")
        if k not in kinds:
            issues.append(f"beat {b.get('idx')}: kind must be one of {sorted(kinds)}")
            continue
        if k in ("goal", "chance"):
            e, err = _resolve_beat_event(b)
            if err:
                issues.append(f"beat {b.get('idx')}: {err}")
                continue
            resolved[b["idx"]] = e
            key = (e["half"], e["t"])
            if key < prev_key:
                issues.append(f"beat {b.get('idx')}: 时间倒序 (拍必须按比赛时间顺序)")
            prev_key = key
            reps = b.get("replays", 1)
            if k == "goal" and reps not in (0, 1, 2):
                issues.append(f"beat {b.get('idx')}: replays must be 0/1/2")
        if k == "ending":
            for f in ("in_t", "out_t", "whistle_t"):
                if not isinstance(b.get(f), (int, float)):
                    issues.append(f"ending beat: {f} required (从解说轴/画面定位终场哨)")
    co = outline.get("cold_open") or {}
    for fl in co.get("flashes", []):     # 内联快闪时刻
        if not isinstance(fl, dict) or fl.get("half") not in (1, 2) \
                or not isinstance(fl.get("t"), (int, float)):
            issues.append("cold_open.flashes 每项需要 {half:1|2, t:秒}")
    return issues, resolved


def soccer_arrange(args: dict, ctx: RunContext) -> ToolResult:
    out_dir = Path(args.get("out_dir", "out"))
    try:
        match = json.load(open(args["match_path"]))
        outline = json.load(open(args["outline_path"]))
        shots = {int(h): json.load(open(p))
                 for h, p in (args.get("shots_paths") or {}).items()}
    except KeyError as e:
        return ToolResult(text=f"[ERROR] missing arg: {e}")
    except (OSError, json.JSONDecodeError) as e:
        return ToolResult(text=f"[ERROR] cannot read input: {e}")
    if set(shots) != {1, 2}:
        return ToolResult(text="[ERROR] shots_paths must map halves '1' and '2' to shots.json paths")

    issues, resolved = _validate_outline(outline)
    if issues:
        return ToolResult(text="outline_invalid: " + "; ".join(issues[:5]),
                          data={"status": "outline_invalid", "issues": issues})

    cuts = {h: _cuts_from_shots(sj) for h, sj in shots.items()}
    beats = outline["beats"]

    # ---- 冷开场快闪 ----
    co = outline.get("cold_open") or {}
    pre = float(co.get("pre", FLASH_PRE))
    post = float(co.get("post", FLASH_POST))
    flashes = []
    for fl in co.get("flashes", []):     # 内联快闪时刻
        flashes.append({"half": int(fl["half"]),
                        "in": round(float(fl["t"]) - pre, 3),
                        "out": round(float(fl["t"]) + post, 3)})
    open_dur = sum(f["out"] - f["in"] for f in flashes) + (GAP_BREATH if flashes else 0.0)

    # ---- 正片段落(每拍一段) ----
    segs = []
    score_now = "0-0"
    for b in beats:
        k = b["kind"]
        if k == "open":
            continue
        if k == "ending":
            s2 = _snap(float(b["in_t"]), cuts[2], 6, 3, prefer=-1)
            segs.append({"beat": b["idx"], "kind": "end", "half": 2, "tag": "FT",
                         "event_t": float(b["whistle_t"]), "in": round(s2, 3),
                         "out": round(float(b["out_t"]), 3), "score": score_now,
                         "score_pre": score_now, "minute": 90, "highlight": bool(b.get("highlight"))})
            continue
        e = resolved[b["idx"]]
        is_goal = k == "goal"
        if is_goal:
            pre_w = float(b.get("pre", GOAL_PRE_DEFAULT))
            post_w, max_rep = GOAL_POST, int(b.get("replays", 1))
        else:
            pre_w, post_w, max_rep = float(b.get("pre", CHANCE_PRE)), CHANCE_POST, 0
        s = max(0.0, e["t"] - pre_w)
        t1 = e["t"] + post_w
        c = cuts[e["half"]]
        s2 = _snap(s, c, SNAP_IN_BACK, SNAP_IN_FWD, prefer=-1)
        e2 = _snap(t1, c, SNAP_OUT_BACK, SNAP_OUT_FWD, prefer=+1)
        if is_goal:
            r = _replay_end(c, e["t"], max_rep) if max_rep else None
            if r and r > e2:
                e2 = r
        score_pre = score_now
        if is_goal:
            score_now = e["score_after"]
        segs.append({"beat": b["idx"], "kind": "seg", "half": e["half"],
                     "tag": "GOAL" if is_goal else "CHANCE", "event_ref": e["id"],
                     "event_t": e["t"], "in": round(s2, 3), "out": round(e2, 3),
                     "score": score_now, "score_pre": score_pre, "minute": e["minute"],
                     "team": e.get("team", ""), "highlight": bool(b.get("highlight"))})
    # 同半场重叠合并 -> 直接报错让 Agent 改大纲(拍粒度合并会破坏拍-段一一对应)
    for a, b2 in zip(segs, segs[1:]):
        if a["half"] == b2["half"] and b2["in"] < a["out"] + 0.5 and a["kind"] == b2["kind"] == "seg":
            return ToolResult(
                text=f"outline_invalid: beat {a['beat']} 与 beat {b2['beat']} 画面窗口重叠, 请合并为一拍或调整 pre",
                data={"status": "outline_invalid",
                      "issues": [f"beats {a['beat']}/{b2['beat']} overlap: "
                                 f"[{a['in']},{a['out']}] vs [{b2['in']},{b2['out']}]"]})

    # ---- 卷轴时间 + 写作简报 ----
    cur = open_dur
    for g in segs:
        g["reel_in"] = round(cur, 2)
        g["reel_event"] = round(cur + g["event_t"] - g["in"], 2)
        cur += g["out"] - g["in"]
        if g["kind"] == "end":
            cur += FREEZE
    total = round(cur, 2)

    cps = {int(k): float(v) for k, v in (args.get("chars_per_sec") or {}).items()} or CHARS_PER_SEC
    brief_beats, brief_txt = [], []
    open_beat = next((b for b in beats if b["kind"] == "open"), None)
    if open_beat is not None and flashes:
        sec = open_dur - 0.5
        brief_beats.append({"idx": open_beat["idx"], "kind": "open", "sec": round(sec, 1),
                            "budget_chars": int(sec * cps[1])})
        brief_txt.append(f"拍{open_beat['idx']} [开场白] 骑在 {len(flashes)} 个快闪+黑场上, "
                         f"可用 {sec:.1f}s ≈ {int(sec * cps[1])} 字 (建议 tier1)")
    for g in segs:
        b = next(x for x in beats if x["idx"] == g["beat"])
        region_end = total if g["kind"] == "end" else None
        nxt = segs[segs.index(g) + 1]["reel_in"] if segs.index(g) + 1 < len(segs) else total - 0.9
        region_end = nxt
        buildup = g["reel_event"] - g["reel_in"] - 0.4
        post_start = g["reel_event"] + (CALL_SLOT if g["tag"] == "GOAL" else 0.0)
        if g["highlight"]:
            post_start += HIGHLIGHT_HOLD
        post = max(0.0, region_end - 0.3 - post_start)
        bb = {"idx": g["beat"], "kind": g["tag"], "reel_in": g["reel_in"],
              "reel_event": g["reel_event"], "region_end": round(region_end, 2),
              "buildup_sec": round(buildup, 1), "buildup_chars": int(buildup * cps[0]),
              "post_sec": round(post, 1), "post_chars": int(post * cps[0]),
              "highlight": g["highlight"]}
        brief_beats.append(bb)
        hl = " [highlight:呐喊后留白透欢呼]" if g["highlight"] else ""
        call = f" 呐喊槽 {CALL_SLOT}s 已扣" if g["tag"] == "GOAL" else ""
        brief_txt.append(
            f"拍{g['beat']} [{g['tag']} {g['minute']}' {b.get('summary','')}]{hl}\n"
            f"  铺垫 {bb['buildup_sec']}s ≈ {bb['buildup_chars']} 字 | "
            f"事件后 {bb['post_sec']}s ≈ {bb['post_chars']} 字{call}\n"
            f"  桥接句可骑跨段首(提前 ~1.5s 起句, J-cut 缝时间跳跃)")

    reel = {"match_path": str(args["match_path"]), "open_dur": round(open_dur, 2),
            "flashes": flashes, "segs": segs, "total": total,
            "freeze": FREEZE, "gap_breath": GAP_BREATH if flashes else 0.0}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "reel.json").write_text(json.dumps(reel, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    (out_dir / "writing_brief.txt").write_text(
        f"成片预计 {total:.0f}s (冷开场 {open_dur:.1f}s)。每拍字数是硬预算, 可少 10% 不许超。\n"
        f"呐喊句(tier2)必须钉在事件秒; 桥接句骑跨段首; highlight 拍呐喊后闭嘴 {HIGHLIGHT_HOLD}s。\n\n"
        + "\n".join(brief_txt), encoding="utf-8")
    (out_dir / "brief.json").write_text(json.dumps({"beats": brief_beats, "total": total},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    return ToolResult(
        text=(f"reel: {len(flashes)} flashes + {len(segs)} segs, 预计 {total:.0f}s "
              f"-> {out_dir}/reel.json + writing_brief.txt"),
        data={"status": "ok", "total_sec": total, "n_segs": len(segs),
              "reel_path": str(out_dir / "reel.json"),
              "brief_path": str(out_dir / "writing_brief.txt")},
        artifacts=[str(out_dir / "reel.json"), str(out_dir / "writing_brief.txt")])


# ================================================================
# soccer_tts
# ================================================================

def _sent_fp(provider: str, voice: str, rate: str, text: str) -> str:
    return hashlib.sha1(f"{provider}\x00{voice}\x00{rate}\x00{text}".encode()).hexdigest()[:16]


def _synth_cloud(text: str, voice: str, tier: int, dst: Path, ctx: RunContext) -> str | None:
    from .tts import tts_generate
    import time
    for k in range(4):
        r = tts_generate({"text": text, "preferred_provider": "edge_tts", "speaker": voice,
                          "speech_rate": TIERS_RATE[tier], "pitch_rate": 0,
                          "output_path": str(dst)}, ctx)
        if not r.text.startswith("[ERROR]"):
            return None
        time.sleep(8 * (2 ** k))
    return f"edge_tts synth failed: {r.text[:120]}"


def soccer_tts(args: dict, ctx: RunContext) -> ToolResult:
    out_dir = Path(args.get("out_dir", "out"))
    try:
        script = json.load(open(args["script_path"]))
    except KeyError:
        return ToolResult(text="[ERROR] script_path is required")
    except (OSError, json.JSONDecodeError) as e:
        return ToolResult(text=f"[ERROR] cannot read script: {e}")
    provider = str(args.get("provider") or clean_env("VE_SOCCER_TTS_PROVIDER") or DEFAULT_TTS_PROVIDER).strip().lower()
    if provider in ("auto", "cloud", "cloud_tts", "edge", "edge_tts"):
        provider = DEFAULT_TTS_PROVIDER
    if provider != DEFAULT_TTS_PROVIDER:
        return ToolResult(text=f"[ERROR] unsupported provider: {provider}; expected {DEFAULT_TTS_PROVIDER}")
    voice = str(args.get("voice") or clean_env("VE_SOCCER_TTS_VOICE") or DEFAULT_SOCCER_TTS_VOICE)
    cache = out_dir / "tts_cache"
    cache.mkdir(parents=True, exist_ok=True)

    sents, failed = [], []
    for b in script.get("beats", []):
        for s in b.get("sentences", []):
            tier = int(s.get("tier", 0))
            text = s["text"].strip()
            rate_key = str(TIERS_RATE[tier])
            fp = _sent_fp(provider, voice, rate_key, text)
            raw = cache / f"{fp}.mp3"
            if not raw.exists() or raw.stat().st_size < 1000:
                err = _synth_cloud(text, voice, tier, raw, ctx)
                if err:
                    failed.append({"beat": b["idx"], "text": text[:30], "err": err})
                    continue
            norm = cache / f"{fp}_n.wav"
            if not norm.exists():
                r = _ffmpeg(["-i", str(raw), "-af",
                             f"loudnorm=I={TIERS_LUFS[tier]}:TP=-2:LRA=7",
                             "-ar", "48000", "-ac", "2", str(norm)])
                if r.returncode:
                    failed.append({"beat": b["idx"], "text": text[:30], "err": r.stderr[-120:]})
                    continue
            sents.append({**s, "beat": b["idx"], "tier": tier,
                          "audio": str(norm), "dur": round(_dur_of(norm), 2)})
    if failed:
        return ToolResult(text=f"[ERROR] {len(failed)} sentences failed TTS",
                          data={"status": "tts_failed", "failed": failed})
    sp = out_dir / "script_tts.json"
    sp.write_text(json.dumps({"provider": provider, "voice": voice, "sentences": sents},
                             ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(s["dur"] for s in sents)
    return ToolResult(
        text=f"TTS {len(sents)} sentences, speech {total:.0f}s -> {sp}",
        data={"status": "ok", "n_sentences": len(sents), "speech_sec": round(total, 1),
              "script_tts_path": str(sp)},
        artifacts=[str(sp)])


# ================================================================
# soccer_render
# ================================================================

def _place(sentences: list[dict], reel: dict) -> tuple[list[dict], list[str]]:
    """摆放: 硬锚钉事件秒, 桥接句骑跨段首, 其余顺流; 返回 (placed, issues)"""
    segs = reel["segs"]
    by_beat = {g["beat"]: g for g in segs}
    bounds = [g["reel_in"] for g in segs[1:]] + [reel["total"] - 0.9]
    placed, issues = [], []
    for s in sentences:
        g = by_beat.get(s["beat"])
        anchor = s.get("anchor", "flow")
        off = float(s.get("offset", 0.0))
        if g is None:                      # open 拍: 相对卷首
            s["_planned"] = max(0.4, off)
        elif anchor == "event":
            s["_planned"] = g["reel_event"] + off
        elif anchor == "bridge":           # 骑跨: 段首前 ~1.5s 起句
            s["_planned"] = g["reel_in"] - min(1.5, s["dur"] * 0.4)
        elif anchor == "post":
            base = g["reel_event"] + off
            if g.get("highlight") and s.get("tier") != 2:
                base = max(base, g["reel_event"] + CALL_SLOT + HIGHLIGHT_HOLD)
            s["_planned"] = base
        else:                              # flow: 跟在前句后
            s["_planned"] = placed[-1]["start"] + placed[-1]["dur"] + 0.15 if placed else 0.4
        prev_end = placed[-1]["start"] + placed[-1]["dur"] if placed else 0.0
        st = max(s["_planned"], prev_end + 0.15)
        limit = next((b for b in bounds if b > s["_planned"] + 0.01), reel["total"] - 0.9) - 0.3
        if anchor == "bridge":             # 骑跨句允许越过本段边界(它就是要跨)
            limit = reel["total"] - 0.9
        over = st + s["dur"] - limit
        late = st - s["_planned"]
        if over > 0.05:
            issues.append(f"beat{s['beat']} 越界{over:.2f}s: {s['text'][:18]}")
        if s.get("hard") and late > 0.6:
            issues.append(f"beat{s['beat']} 硬锚句被挤晚{late:.2f}s: {s['text'][:18]}")
        placed.append({**s, "start": round(st, 2)})
    for s in placed:
        s.pop("_planned", None)
    return placed, issues


def _render_segments(reel: dict, match: dict, outline: dict, work: Path) -> tuple[list[dict], str | None]:
    """渲染各拼装件. 返回 pieces=[{path, D:时间轴时长, head/tail:溶解延长量}].
    段间溶解是时长守恒的: 边界两侧各多取 XPAD 秒素材, xfade 叠化正好吃掉延长量,
    因此 reel 时间轴(以及所有解说锚点)一毫米都不动."""
    font = _font()
    tcn = outline["teams_cn"]
    home = escape_text(tcn.get("home", ""))
    away = escape_text(tcn.get("away", ""))
    pieces: list[dict] = []
    flash_files = []
    for i, f in enumerate(reel["flashes"]):
        src = match["halves"][str(f["half"])]["video"]
        dst = work / f"flash_{i}.mp4"
        dur = f["out"] - f["in"]
        tail = XPAD if i == len(reel["flashes"]) - 1 else 0.0   # 末闪多取素材, 溶入标题卡
        vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
              "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=25")
        if i == 0 and outline.get("open_title"):
            ot = escape_text(outline["open_title"])
            vf += (f",drawtext=fontfile={font}:text='{ot}':"
                   f"x=(w-text_w)/2:y=60:fontsize=34:fontcolor=white:box=1:"
                   f"boxcolor=black@0.5:boxborderw=10,fade=t=in:st=0:d=0.3")
        af = f"afade=t=in:st=0:d=0.04,afade=t=out:st={dur-0.04:.2f}:d=0.04,volume=0.85"
        r = _ffmpeg(["-ss", f"{f['in']:.3f}", "-to", f"{f['out']+tail:.3f}", "-i", src,
                     "-vf", vf, "-af", af, "-c:v", "libx264", "-crf", "20",
                     "-preset", "medium", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-ar", "48000", "-ac", "2", str(dst)])
        if r.returncode:
            return pieces, f"flash {i}: {r.stderr[-200:]}"
        flash_files.append(dst)
    if flash_files:
        # 快闪蒙太奇内部保持硬切: 先硬拼成 open.mp4 再进溶解链
        lst = work / "open_concat.txt"
        lst.write_text("".join(f"file '{f.resolve()}'\n" for f in flash_files), encoding="utf-8")
        open_mp4 = work / "open.mp4"
        r = _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(open_mp4)])
        if r.returncode:
            return pieces, f"open concat: {r.stderr[-200:]}"
        pieces.append({"path": open_mp4, "D": sum(f["out"] - f["in"] for f in reel["flashes"]),
                       "head": 0.0, "tail": XPAD})
        # 屏息黑场压标题卡 —— 不给观众裸黑屏
        gap = work / "gap.mp4"
        gc = outline.get("gap_card") or {}
        l1 = escape_text(gc.get("line1") or f"{tcn['home']}  vs  {tcn['away']}")
        l2 = escape_text(gc.get("line2") or outline.get("open_title", ""))
        gvf = (f"drawtext=fontfile={font}:text='{l1}':x=(w-text_w)/2:y=296:"
               f"fontsize=58:fontcolor=white")
        if l2:
            gvf += (f",drawtext=fontfile={font}:text='{l2}':x=(w-text_w)/2:y=402:"
                    f"fontsize=30:fontcolor=0xcccccc")
        r = _ffmpeg(["-f", "lavfi", "-i",
                     f"color=c=black:s=1280x720:r=25:d={GAP_BREATH+2*XPAD:.2f}",
                     "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                     "-vf", gvf, "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-ar", "48000", "-ac", "2", str(gap)])
        if r.returncode:
            return pieces, f"gap card: {r.stderr[-200:]}"
        pieces.append({"path": gap, "D": GAP_BREATH, "head": XPAD, "tail": XPAD})
    for i, g in enumerate(reel["segs"]):
        src = match["halves"][str(g["half"])]["video"]
        dst = work / f"seg_{i:02d}.mp4"
        head = XPAD if pieces else 0.0
        tail = 0.0 if g["kind"] == "end" else XPAD
        ss = max(0.0, g["in"] - head)
        head = g["in"] - ss
        dur = g["out"] + tail - ss           # 素材件全长(含溶解延长量)
        vf = ("scale=1280:720:force_original_aspect_ratio=decrease,"
              "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=25,")
        sb_box = "fontsize=26:fontcolor=white:box=1:boxcolor=black@0.45:boxborderw=10"
        if g["kind"] == "end":
            vf += (f"drawtext=fontfile={font}:text='{home} {g['score']} {away}   "
                   f"全场结束':x=36:y=32:{sb_box}")
        elif g["tag"] == "GOAL" and g["score_pre"] != g["score"]:
            t_rel = g["event_t"] - ss + 0.8     # 进球瞬间才跳分, 不剧透(随 head 平移)
            mn = escape_text(g.get("minute", ""))
            for txt, en in ((f"{home} {g['score_pre']} {away}   {mn}'",
                             f"enable=lt(t\\,{t_rel:.2f})"),
                            (f"{home} {g['score']} {away}   {mn}'",
                             f"enable=gte(t\\,{t_rel:.2f})")):
                vf += f"drawtext=fontfile={font}:text='{txt}':x=36:y=32:{sb_box}:{en},"
            vf = vf.rstrip(",")
        else:
            mn = escape_text(g.get("minute", ""))
            vf += (f"drawtext=fontfile={font}:text='{home} {g['score']} {away}   "
                   f"{mn}'':x=36:y=32:{sb_box}")
        af = None                            # 段间淡入淡出交给拼装图的溶解, 不在件内做
        if g["kind"] == "end":
            ec = outline.get("end_card") or {}
            fz = reel.get("freeze", FREEZE)
            vf += f",tpad=stop_mode=clone:stop_duration={fz}"
            if ec.get("line1"):
                ec1 = escape_text(ec["line1"])
                vf += (f",drawtext=fontfile={font}:text='{ec1}':x=(w-text_w)/2:y=280:"
                       f"fontsize=64:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18:"
                       f"enable=gte(t\\,{dur+0.3:.2f})")
            if ec.get("line2"):
                ec2 = escape_text(ec["line2"])
                vf += (f",drawtext=fontfile={font}:text='{ec2}':x=(w-text_w)/2:y=390:"
                       f"fontsize=36:fontcolor=0xdddddd:box=1:boxcolor=black@0.55:boxborderw=12:"
                       f"enable=gte(t\\,{dur+0.6:.2f})")
            vf += f",fade=t=out:st={dur+fz-0.9:.2f}:d=0.9"
            af = f"apad=pad_dur={fz},afade=t=out:st={dur+fz-1.5:.2f}:d=1.5"
        cmd = ["-ss", f"{ss:.3f}", "-to", f"{g['out']+tail:.3f}", "-i", src, "-vf", vf]
        if af:
            cmd += ["-af", af]
        cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-ar", "48000", "-ac", "2", str(dst)]
        r = _ffmpeg(cmd)
        if r.returncode:
            return pieces, f"seg {i}: {r.stderr[-300:]}"
        D = (g["out"] - g["in"]) + (reel.get("freeze", FREEZE) if g["kind"] == "end" else 0.0)
        pieces.append({"path": dst, "D": D, "head": head, "tail": tail})
    return pieces, None


def _write_ass(placed: list[dict], path: Path) -> None:
    """解说字幕轨: 底部居中白字黑边, 按摆放时刻逐句显示, 不与下一句重叠"""
    def ts(t: float) -> str:
        t = max(0.0, t)
        return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1280", "PlayResY: 720",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: N,Noto Sans CJK SC,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H7F000000,"
        "1,0,0,0,100,100,0,0,1,2,0.8,2,60,60,34,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for i, s in enumerate(placed):
        st = s["start"]
        en = st + s["dur"] + 0.3
        if i + 1 < len(placed):
            en = min(en, placed[i + 1]["start"] - 0.05)
        en = max(en, st + 0.5)
        txt = s["text"].replace("\n", " ").replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},N,,0,0,0,,{txt}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assemble(pieces: list[dict], base: Path, ass_path: Path | None, work: Path) -> str | None:
    """溶解拼装: 视频链式 xfade(offset 按时间轴推算, 延长量正好被叠化吃掉);
    音频不用 acrossfade(逐段拼会累积时长漂移), 而是各件按时间轴 adelay 精确摆放 +
    边界 XFADE 淡入淡出, amix 叠加 == 交叉淡化且采样级对齐. 字幕(如有)在此一次性烧录."""
    n = len(pieces)
    parts = [f"[{k}:v]settb=AVTB,fps=25[v{k}]" for k in range(n)]
    cur, acc = "v0", pieces[0]["D"]
    for k in range(1, n):
        xf = pieces[k - 1]["tail"] + pieces[k]["head"]
        parts.append(f"[{cur}][v{k}]xfade=transition=fade:duration={xf:.2f}:"
                     f"offset={acc - pieces[k]['head']:.3f}[vx{k}]")
        cur = f"vx{k}"
        acc += pieces[k]["D"]
    if ass_path:
        parts.append(f"[{cur}]ass='{ass_path}'[vout]")
        cur = "vout"
    t_axis, ains = 0.0, ""
    for k, p in enumerate(pieces):
        ext = p["D"] + p["head"] + p["tail"]
        chain = []
        if p["head"] > 0:
            chain.append(f"afade=t=in:st=0:d={XFADE:.2f}")
        if p["tail"] > 0:
            chain.append(f"afade=t=out:st={ext - XFADE:.2f}:d={XFADE:.2f}")
        ms = int(round((t_axis - p["head"]) * 1000))
        if ms > 0:
            chain.append(f"adelay={ms}|{ms}")
        parts.append(f"[{k}:a]{','.join(chain) if chain else 'anull'}[a{k}]")
        ains += f"[a{k}]"
        t_axis += p["D"]
    parts.append(f"{ains}amix=inputs={n}:duration=longest:normalize=0[aout]")
    fscript = work / "assemble_filter.txt"
    fscript.write_text(";".join(parts), encoding="utf-8")
    cmd = []
    for p in pieces:
        cmd += ["-i", str(p["path"])]
    cmd += ["-filter_complex_script", str(fscript), "-map", f"[{cur}]", "-map", "[aout]",
            "-c:v", "libx264", "-crf", "19", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", str(base)]
    r = _ffmpeg(cmd)
    return r.stderr[-300:] if r.returncode else None


def _mix(base: Path, placed: list[dict], duck_iv: list[list[float]], out_path: Path,
         work: Path) -> str | None:
    dists = [f"max(max({a:.2f}-t\\,t-{b:.2f})\\,0)" for a, b in duck_iv]
    expr = dists[0]
    for d in dists[1:]:
        expr = f"min({expr}\\,{d})"
    vol = f"volume='0.3+0.7*min(1\\,({expr})/0.4)':eval=frame"
    parts, amixin = [f"[0:a]{vol}[bg]"], "[bg]"
    for k, s in enumerate(placed):
        ms = int(round(s["start"] * 1000))
        parts.append(f"[{k+1}:a]adelay={ms}|{ms}[n{k}]")
        amixin += f"[n{k}]"
    parts.append(f"{amixin}amix=inputs={len(placed)+1}:duration=first:normalize=0,"
                 f"acompressor=threshold=0.12:ratio=2:attack=200:release=900:makeup=2[out]")
    fscript = work / "mix_filter.txt"
    fscript.write_text(";".join(parts), encoding="utf-8")
    cmd = ["-i", str(base)]
    for s in placed:
        cmd += ["-i", s["audio"]]
    cmd += ["-filter_complex_script", str(fscript), "-map", "0:v", "-map", "[out]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out_path)]
    r = _ffmpeg(cmd)
    return r.stderr[-300:] if r.returncode else None


def _qc_gates(final: Path, reel: dict, placed: list[dict]) -> dict:
    qc = {"pass": True, "checks": {}}
    # 1. 黑场唯一性: 只允许冷开场后的 GAP_BREATH 一处
    r = run_proc(["ffmpeg", "-nostdin", "-i", str(final), "-vf",
                        "blackdetect=d=0.2:pix_th=0.10", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)
    gap_start = reel["open_dur"] - reel.get("gap_breath", 0.0)
    unexpected = [(a, b) for a, b in blacks
                  if not (abs(float(a) - gap_start) < 1.0)
                  and float(a) < reel["total"] - 3.0]
    qc["checks"]["blackdetect"] = {"pass": not unexpected, "found": blacks,
                                   "unexpected": unexpected}
    # 2. 硬锚零偏: 摆放层已校验, 复核落盘值
    hard_bad = [{"text": s["text"][:16], "start": s["start"]}
                for s in placed if s.get("hard") and s.get("anchor") == "event"
                and abs(s["start"] - next((g["reel_event"] + float(s.get("offset", 0))
                                           for g in reel["segs"] if g["beat"] == s["beat"]), 0)) > 1.0]
    qc["checks"]["hard_anchor"] = {"pass": not hard_bad, "bad": hard_bad}
    # 3. 响度
    r = run_proc(["ffmpeg", "-nostdin", "-i", str(final), "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]+\}", r.stderr[-2000:], re.S)
    lufs = float(json.loads(m.group())["input_i"]) if m else None
    qc["checks"]["loudness"] = {"pass": lufs is not None and -19.5 <= lufs <= -12.5,
                                "input_i": lufs}
    # 4. 时长
    d = _dur_of(final)
    qc["checks"]["duration"] = {"pass": abs(d - reel["total"]) < 2.0,
                                "final": round(d, 2), "reel": reel["total"]}
    qc["pass"] = all(c["pass"] for c in qc["checks"].values())
    return qc


def soccer_render(args: dict, ctx: RunContext) -> ToolResult:
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
    work = out_dir / "render_work"
    work.mkdir(parents=True, exist_ok=True)

    # ---- 摆放(先于渲染: over_budget 时不浪费渲染) ----
    placed, issues = _place(stts["sentences"], reel)
    (out_dir / "placement.json").write_text(json.dumps(placed, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    if issues:
        return ToolResult(text="over_budget: " + "; ".join(issues[:4]),
                          data={"status": "over_budget", "issues": issues,
                                "hint": "压缩对应拍的文案(删修饰不删事实)后重跑 soccer_tts + soccer_render"})

    # ---- 渲染底版: 各件 -> 溶解拼装(+字幕烧录) ----
    pieces, err = _render_segments(reel, match, outline, work)
    if err:
        return ToolResult(text=f"[ERROR] render failed: {err}")
    ass_path = None
    if args.get("subtitles", True):
        ass_path = (work / "subs.ass").resolve()
        _write_ass(placed, ass_path)
    base = work / "base.mp4"
    err = _assemble(pieces, base, ass_path, work)
    if err:
        return ToolResult(text=f"[ERROR] assemble failed: {err}")

    # ---- 压音区间: 底版转录区间(可选) ∪ 中文句区间 ----
    iv = [(s["start"], s["start"] + s["dur"]) for s in placed]
    tr_path = args.get("base_transcript_path")
    if tr_path and Path(tr_path).exists():
        tr = json.load(open(tr_path))
        iv += [(t["start"], t["end"]) for t in tr.get("segments", [])]
    iv = sorted((max(0.0, a - 0.2), b + 0.2) for a, b in iv)
    duck = []
    for a, b in iv:
        if duck and a - duck[-1][1] < 0.7:
            duck[-1][1] = max(duck[-1][1], b)
        else:
            duck.append([a, b])
    err = _mix(base, placed, duck, out_path, work)
    if err:
        return ToolResult(text=f"[ERROR] mix failed: {err}")

    # ---- QC 硬门 ----
    qc = _qc_gates(out_path, reel, placed)
    (out_dir / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    if not qc["pass"]:
        bad = [k for k, v in qc["checks"].items() if not v["pass"]]
        return ToolResult(text=f"qc_failed: {bad} (成片已出但未达标, 详见 qc.json)",
                          data={"status": "qc_failed", "qc": qc,
                                "output_path": str(out_path)})
    d = _dur_of(out_path)
    return ToolResult(
        text=(f"final: {out_path}  {d:.1f}s  "
              f"LUFS {qc['checks']['loudness']['input_i']}  QC all pass"),
        data={"status": "ok", "output_path": str(out_path), "duration": round(d, 2),
              "qc": qc, "n_duck_intervals": len(duck)},
        artifacts=[str(out_path)], video_paths=[str(out_path)])
