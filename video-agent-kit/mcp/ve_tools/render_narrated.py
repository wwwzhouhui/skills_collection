"""render_narrated: EDL → 带解说配音 + 字幕 + BGM 的最终成片。

从 movie_cut 移植三个模块并合为一个 MCP 工具(逻辑逐行保真, JSON/文件契约不变):
  - step_e_render.render   成片渲染(seg级切片缓存断点续跑/呼吸尾tail_sec/
                            音画漂移硬校验/响度QC/原声让位)
  - step_subtitle.build_srt 句级字幕 + 均衡换行
  - step_bgm.build_from_edl BGM 按故事场景分组垫乐(原声段静音让位)

与源版的差异(见文件尾注释"移植取舍"):
  - HDR tonemap 前缀改为运行时 ffprobe 探测(源版读 probe.json)
  - BGM 素材运行时从 bgm_dir(VE_BGM_DIR) 读, 并过滤带视频流(内嵌封面
    attached_pic)的文件 —— 该类 mp3 会让拼接挂起
  - 无 CJK 字体时字幕自动降级为不烧录(warning, 不失败)
  - 不移植: LLM 相关 / intro+outro 片头尾卡 / keep_original_audio 全程 ducking
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .fonts import ass_font_name
from .result import ToolResult
from .run_context import RunContext, clean_env

# ---------------------------------------------------------------------------
# 统一输出规格(保证切片可无缝拼接) + 渲染调优旋钮(环境变量可覆盖, 与源版一致)
# ---------------------------------------------------------------------------
W, H, FPS, PIXFMT = 1920, 1080, 24, "yuv420p"

PRESET = os.environ.get("RENDER_PRESET", "veryfast")
ENC_THREADS = os.environ.get("RENDER_ENC_THREADS", "8")
CUT_WORKERS = int(os.environ.get("RENDER_CUT_WORKERS", "24"))
# 快速 seek: -ss 放 -i 前跳到最近关键帧, 再用输出端 -ss 补精度(大 GOP 源留 12s 缓冲)
PRESEEK = 12.0
# 成片整体变速(默认原速)
SPEEDUP = float(os.environ.get("RENDER_SPEEDUP", "1.0"))
# 解说底下铺原片原声的音量(环境声透出来); 0=关闭
BED_VOL = float(os.environ.get("RENDER_BED_VOLUME", "0.13"))
# 呼吸留白段的原片原声音量:解说停、原声起(互斥而非叠加)。0=留白静音(旧行为)
TAIL_VOL = float(os.environ.get("RENDER_TAIL_VOLUME", "0.85"))
# 解说增益 + alimiter 兜底防削波
NARR_GAIN = float(os.environ.get("RENDER_NARR_GAIN", "1.8"))

# V3 EDL 渲染前硬门禁的最小窗口时长(源: step_event_bind.MIN_WINDOW_SEC)
MIN_WINDOW_SEC = 1.25

# ffmpeg 长任务超时(秒)
FF_TIMEOUT = 3600

# 渲染过程日志(代替源版 print; 单进程内一次只跑一个工具调用)
_LOG: list[str] = []


def _log(msg: str) -> None:
    _LOG.append(msg)


# ---------------------------------------------------------------------------
# 公共小工具(从 movie_cut/pipeline/common.py 抄入)
# ---------------------------------------------------------------------------

def load_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run(cmd: list[str], check: bool = True,
        timeout: float = FF_TIMEOUT) -> subprocess.CompletedProcess:
    """跑一条命令; ffmpeg 强制 -nostdin, 失败把 stderr 抛出来。"""
    if cmd and Path(cmd[0]).name == "ffmpeg" and "-nostdin" not in cmd:
        cmd = [cmd[0], "-nostdin", *cmd[1:]]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL)
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"命令失败 (exit {proc.returncode}):\n  {shlex.join(cmd)}\n"
            f"--- stderr ---\n{proc.stderr[-3000:]}"
        )
    return proc


def media_duration(path: str | Path, stream: str = "v") -> float:
    """单独取某条流的时长(v=视频, a=音频), 用于缓存校验与成片自检。"""
    cmd = ["ffprobe", "-v", "error", "-select_streams", f"{stream}:0",
           "-show_entries", "stream=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    out = run(cmd, check=False, timeout=60).stdout.strip()
    try:
        return float(out)
    except ValueError:
        # 有些容器流里没存 duration, 回退到 format
        cmd2 = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        return float(run(cmd2, timeout=60).stdout.strip() or 0.0)


_HDR_VF_CACHE: dict[str, str] = {}


def hdr_vf(video: str) -> str:
    """HDR 片源的 tonemap 前缀滤镜, SDR 返回空串。
    源版读 step_probe 的 probe.json; 这里改为直接 ffprobe color_transfer,
    滤镜链与源版完全一致(否则 HDR 直出 x264+yuv420p 整体发灰)。"""
    key = str(Path(video).resolve())
    if key not in _HDR_VF_CACHE:
        vf = ""
        r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=color_transfer", "-of", "csv=p=0",
                 str(video)], check=False, timeout=60)
        if r.returncode == 0 and r.stdout.strip() in {"smpte2084", "arib-std-b67"}:
            vf = ("zscale=transfer=linear:npl=100,tonemap=hable:desat=0,"
                  "zscale=primaries=bt709:transfer=bt709:matrix=bt709:range=tv,"
                  "format=yuv420p,")
        _HDR_VF_CACHE[key] = vf
    return _HDR_VF_CACHE[key]


# ---------------------------------------------------------------------------
# 字幕(从 step_subtitle.py 抄入)
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> list[str]:
    """按中文标点拆短句, 保留语义完整。过长的逗号句也拆。"""
    parts = re.split(r"(?<=[。！？；])", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > 20:
            sub = re.split(r"(?<=[，、])", p)
            out.extend([x.strip() for x in sub if x.strip()])
        else:
            out.append(p)
    return out


def balanced_wrap(text: str, width: int = 20) -> str:
    """长句均衡换行: 行数按总长均分(不是塞满第一行剩个孤字尾行),
    断点优先落在标点后。烧录时整块显示, 观感齐整。"""
    text = text.strip()
    if len(text) <= width:
        return text
    n = math.ceil(len(text) / width)
    per = math.ceil(len(text) / n)
    lines, rest = [], text
    while len(rest) > per + 2:
        cut = per
        for i in range(max(1, per - 4), min(len(rest) - 1, per + 4)):
            if rest[i - 1] in "，、。！？；：":
                cut = i
        lines.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        lines.append(rest)
    return "\n".join(lines)


def fmt_ts(sec: float) -> str:
    """秒 → SRT 时间戳 HH:MM:SS,mmm"""
    total_ms = max(0, int(round(sec * 1000)))
    total_s, ms = divmod(total_ms, 1000)
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(script_path: str, out_path: str, edl_path: str | None = None) -> int:
    """句级字幕: 段起点按 EDL 最终画面时长(整帧取整)累加, 消除长片累计漂移。
    返回字幕条数。"""
    segs = load_json(script_path)
    edl_durations = {}
    if edl_path:
        edl = load_json(edl_path)
        rows = edl.get("segments", []) if isinstance(edl, dict) else edl
        edl_durations = {
            str(row.get("seg_id")): float(row.get("video_dur", 0) or 0)
            for row in rows
            if row.get("seg_id") and float(row.get("video_dur", 0) or 0) > 0
        }
    cues = []
    seg_start = 0.0
    for s in segs:
        dur = s.get("audio_dur")
        if not dur or dur <= 0:
            # 该段 TTS 失败/无音频 —— 已被 EDL/渲染丢弃, 字幕同样跳过
            continue
        # 优先用 TTS 逐句合成产出的真实句级时间轴(精确对齐, 零漂移)
        if s.get("sentences"):
            for sent in s["sentences"]:
                cues.append((seg_start + sent["start"], seg_start + sent["end"],
                             sent.get("subtitle_text", sent.get("text", ""))))
        else:
            # 回退: 按字数比例均分(有漂移)
            sents = split_sentences(s.get("subtitle_text", s["text"]))
            total_chars = sum(len(x) for x in sents) or 1
            t = seg_start
            for sent in sents:
                d = dur * len(sent) / total_chars
                cues.append((t, t + d, sent))
                t += d
        # 以最终 EDL 时长推进, 微小余量留在本段末尾, 不传递成全片累计漂移
        seg_start += edl_durations.get(str(s.get("seg_id")), dur)

    lines = []
    for i, (st, en, text) in enumerate(cues, 1):
        lines.append(f"{i}\n{fmt_ts(st)} --> {fmt_ts(en)}\n{balanced_wrap(text)}\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    _log(f"[字幕] {len(cues)} 条字幕 → {out_path}")
    return len(cues)


def _detect_cjk_font() -> str | None:
    """fc-list 探测可用中文字体; 没有则返回 None(字幕降级为不烧录)。

    Windows 没有 fontconfig、mac 也常没装, 那边 fc-list 一律探测不到 —— 但系统
    自带雅黑/苹方, libass 走 DirectWrite/CoreText 能直接按 family 名解析。所以
    只在 fc-list 压根拿不到任何中文 family 时改问 fonts.ass_font_name();
    fc-list 有结果但没有 Noto CJK 的情况仍照旧返回 None —— 那是 Linux 上"字体
    装得不对"的既有判定, 不在这次跨平台适配的范围里动。
    """
    try:
        r = subprocess.run(["fc-list", ":lang=zh", "family"],
                           capture_output=True, text=True, timeout=30)
    except Exception:
        return ass_font_name()
    families: set[str] = set()
    for line in r.stdout.splitlines():
        for fam in line.split(","):
            fam = fam.strip()
            if fam:
                families.add(fam)
    if not families:
        return ass_font_name()
    for pref in ("Noto Sans CJK SC", "Noto Sans CJK TC"):
        if pref in families:
            return pref
    return None


# ---------------------------------------------------------------------------
# BGM(从 step_bgm.py 抄入; 素材库目录由调用方传入, 不再指向 movie_cut/assets)
# ---------------------------------------------------------------------------

EMOTIONS = {"sad", "tense", "warm", "epic", "happy", "neutral"}

_EMOTION_ALIASES = {
    "悲伤": "sad", "伤感": "sad", "痛心": "sad", "心疼": "sad",
    "沉重": "sad", "绝望": "sad", "无奈": "sad", "怅然": "sad",
    "隐忍": "sad", "残酷": "sad",
    "紧张": "tense", "悬疑": "tense", "诡异": "tense", "惊悚": "tense",
    "压抑": "tense", "恐惧": "tense", "压迫": "tense", "不安": "tense",
    "警觉": "tense", "惊惧": "tense", "无助": "tense", "恐怖": "tense",
    "焦灼": "tense", "失控": "tense", "狂躁": "tense", "阴冷": "tense",
    "戒备": "tense", "紧迫": "tense", "窒息": "tense", "惊恐": "tense",
    "冷酷": "tense",
    "温暖": "warm", "温情": "warm", "感动": "warm", "克制": "warm",
    "开心": "happy", "快乐": "happy", "轻松": "happy", "期待": "happy",
    "激烈": "epic", "史诗": "epic", "推进": "epic", "关键": "epic",
    "释放": "epic", "坚决": "epic", "振奋": "epic",
    "平静": "neutral", "中性": "neutral", "警醒": "neutral",
}


def normalize_emotion(value: Any) -> str:
    """把模型常见的中英文自由输出收敛到六个稳定枚举。"""
    s = str(value or "neutral").strip().lower()
    if s in EMOTIONS:
        return s
    if s in _EMOTION_ALIASES:
        return _EMOTION_ALIASES[s]
    for key, val in _EMOTION_ALIASES.items():
        if key in s:
            return val
    for val in EMOTIONS:
        if val in s:
            return val
    return "neutral"


EMOTION_CHORD = {
    "warm":   [261.63, 329.63, 392.00],   # C4 E4 G4 大三
    "happy":  [261.63, 329.63, 392.00],
    "sad":    [220.00, 261.63, 329.63],   # A3 C4 E4 小三
    "tragic": [220.00, 261.63, 329.63],
    "tense":  [246.94, 293.66, 349.23],   # B3 D4 F4 减
    "epic":   [130.81, 164.81, 196.00],   # C3 E3 G3 低厚
    "neutral": [261.63, 329.63, 392.00],
}

_BGM_HAS_VIDEO_CACHE: dict[str, bool] = {}


def _bgm_has_video(path: str) -> bool:
    """音乐文件是否带视频流(内嵌封面 attached_pic)——这种 mp3 会让拼接挂起,
    选文件时过滤掉。探测失败按'有视频'处理(宁可不选, 不冒挂起风险)。"""
    if path not in _BGM_HAS_VIDEO_CACHE:
        try:
            r = run(["ffprobe", "-v", "error", "-select_streams", "v",
                     "-show_entries", "stream=index", "-of", "csv=p=0", path],
                    check=False, timeout=60)
            _BGM_HAS_VIDEO_CACHE[path] = (r.returncode != 0) or bool(r.stdout.strip())
        except Exception:
            _BGM_HAS_VIDEO_CACHE[path] = True
    return _BGM_HAS_VIDEO_CACHE[path]


def lib_pick(bgm_dir: str, emotion: str, key: str = "",
             avoid: str | None = None) -> str | None:
    """从音乐库 bgm_dir/<emotion>/*.mp3|m4a 按情绪挑一首。
    确定性选曲(按 key 哈希): 同一部片重跑选同一首; avoid=上一组用过的曲子,
    同情绪连续场景尽量换曲。找不到该情绪则尝试 neutral, 再无则 None。"""
    for emo in (emotion, "neutral"):
        d = Path(bgm_dir) / emo
        if d.is_dir():
            files = sorted([str(p) for p in d.glob("*.mp3")] +
                           [str(p) for p in d.glob("*.m4a")])
            files = [f for f in files if not _bgm_has_video(f)]
            if files:
                idx = int(hashlib.sha256(f"{emo}|{key}".encode()).hexdigest(), 16) % len(files)
                pick = files[idx]
                if avoid and pick == avoid and len(files) > 1:
                    pick = files[(idx + 1) % len(files)]
                return pick
    return None


def synth_segment(freqs: list[float], dur: float, out: str, fade: float = 1.5) -> None:
    """合成一段和弦氛围乐: 多正弦叠加 + 混响 + 低通柔化 + 首尾淡入淡出。"""
    inputs = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={dur:.2f}"]
    n = len(freqs)
    mix = "".join(f"[{i}]" for i in range(n))
    fc = (f"{mix}amix=inputs={n},volume=2.0,"
          f"aecho=0.8:0.7:60:0.4,lowpass=f=1800,"
          f"afade=t=in:d={fade},afade=t=out:st={max(0, dur - fade):.2f}:d={fade}[a]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[a]",
         "-c:a", "libmp3lame", "-b:a", "128k", out])


def fit_clip(src: str, dur: float, out: str, fade: float = 1.0) -> None:
    """把一段音乐裁切或循环到 dur 秒, 并加首尾淡入淡出。"""
    src_dur = media_duration(src, "a")
    loops = max(0, int(dur // max(src_dur, 0.1)))   # 需要额外循环几遍
    af = f"afade=t=in:d={fade},afade=t=out:st={max(0, dur - fade):.2f}:d={fade}"
    run(["ffmpeg", "-y", "-stream_loop", str(loops), "-i", src,
         "-t", f"{dur:.6f}", "-af", af,
         "-c:a", "libmp3lame", "-b:a", "128k", out])


def make_segment(bgm_dir: str, emotion: str, dur: float, out: str,
                 user_bgm: str | None, key: str = "",
                 avoid: str | None = None) -> tuple[str, str | None]:
    """单段 BGM, 三档优先级: 库 > 用户自备 > 合成。返回(来源标记, 曲目路径或None)。"""
    lib = lib_pick(bgm_dir, emotion, key=key, avoid=avoid)
    if lib:
        fit_clip(lib, dur, out)
        return f"库:{Path(lib).name}", lib
    if user_bgm:
        fit_clip(user_bgm, dur, out)
        return "用户自备", user_bgm
    synth_segment(EMOTION_CHORD.get(emotion, EMOTION_CHORD["neutral"]), dur, out)
    return "合成", None


def _silence(dur: float, out: str) -> None:
    """原声穿插段的 BGM 占位: 纯静音(电影自己说话的时刻, 配乐必须让位)。"""
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{dur:.6f}", "-c:a", "libmp3lame", "-b:a", "128k", out])


def _scene_groups(edl: list) -> list[dict]:
    """按故事场景合并连续 EDL 段; 原声穿插段单独成组(静音)。
    一场戏一首曲、场景边界才换曲, 配乐才跟着剧情走。"""
    groups: list[dict] = []
    for e in edl:
        dur = float(e.get("video_dur") or
                    (e.get("audio_dur", 0) + e.get("tail_sec", 0.0)))
        emo = normalize_emotion(e.get("emotion", "neutral"))
        oa = bool(e.get("original_audio"))
        key = f"oa:{e['seg_id']}" if oa else (e.get("story_scene_id") or e["seg_id"])
        if groups and not oa and not groups[-1]["oa"] and groups[-1]["key"] == key:
            groups[-1]["dur"] += dur
            groups[-1]["emotions"][emo] = groups[-1]["emotions"].get(emo, 0.0) + dur
        else:
            groups.append({"key": key, "oa": oa, "dur": dur, "emotions": {emo: dur}})
    return groups


def build_from_edl(edl_path: str, out: str, work: str, bgm_dir: str,
                   user_bgm: str | None = None) -> None:
    """按故事场景分组选 BGM(场景内一首到底, 时长加权主情绪), 再交叉淡化拼接。
    原声穿插段静音让位。"""
    edl = load_json(edl_path)
    Path(work).mkdir(parents=True, exist_ok=True)
    groups = _scene_groups(edl)
    parts, timeline_durations = [], []
    xfade = 1.0
    prev_track: str | None = None
    for gi, g in enumerate(groups):
        dur = g["dur"]
        p = f"{work}/bgm_g{gi:03d}.mp3"
        # acrossfade 会吃掉每个边界 xfade 秒; 除最后一组外预补同样时长,
        # 保证最终 BGM 总长仍等于 EDL, 而不是几十组后提前结束。
        render_dur = dur + (xfade if gi < len(groups) - 1 else 0.0)
        if g["oa"]:
            _silence(render_dur, p)
            emo, src = "原声让位", "静音"
        else:
            emo = max(g["emotions"], key=g["emotions"].get)
            src, track = make_segment(bgm_dir, emo, render_dur, p, user_bgm,
                                      key=g["key"], avoid=prev_track)
            prev_track = track or prev_track
        parts.append(p)
        timeline_durations.append(float(dur))
        _log(f"  {g['key']} [{emo}] {dur:.0f}s ← {src}")
    # 拼接(交叉淡化避免和弦突变)
    inputs = []
    for p in parts:
        inputs += ["-i", p]
    total_dur = sum(timeline_durations)
    if len(parts) == 1:
        run(["ffmpeg", "-y", "-i", parts[0],
             "-af", f"apad,atrim=duration={total_dur:.6f}",
             "-c:a", "libmp3lame", "-b:a", "128k", out])
    else:
        fc, prev = [], "[0:a]"
        for i in range(1, len(parts)):
            lbl = f"[a{i}]" if i < len(parts) - 1 else "[aout]"
            fc.append(f"{prev}[{i}:a]acrossfade=d={xfade}:c1=tri:c2=tri{lbl}")
            prev = lbl
        fc.append(f"{prev}apad,atrim=duration={total_dur:.6f}[afinal]")
        run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc),
             "-map", "[afinal]", "-c:a", "libmp3lame", "-b:a", "128k", out])
    _log(f"[BGM] 按场景分组拼接 {len(parts)} 组 → {out}")


def _bgm_dir_usable(bgm_dir: Path) -> bool:
    """库目录下(含情绪子目录)是否有任何不带视频流的可用音频。"""
    if not bgm_dir.is_dir():
        return False
    for pat in ("*.mp3", "*.m4a", "*/*.mp3", "*/*.m4a"):
        for p in sorted(bgm_dir.glob(pat)):
            if not _bgm_has_video(str(p)):
                return True
    return False


# ---------------------------------------------------------------------------
# 渲染前硬门禁(从 step_event_bind.audit_edl 抄入, V3 EDL 专用)
# ---------------------------------------------------------------------------

def audit_edl(edl: list[dict], fps: float = FPS,
              min_window_sec: float = MIN_WINDOW_SEC) -> dict:
    """渲染前硬门禁: 任何重复、重叠、倒退或无意碎片都不放行。"""
    seen_shots, intervals = set(), []
    duplicate_shots, overlaps, regressions, short_windows, reused = [], [], [], [], []
    previous_end = -1
    previous_sid = ""
    for entry in edl:
        is_oa = bool(entry.get("original_audio"))
        for window in entry.get("windows", []):
            if window.get("replay"):
                # 原声回放窗口: 有意重放关键台词时刻, 在旁白画面账本之外,
                # 不参与重复/倒带/重叠判定, 也不推进时间基。
                continue
            sid = window.get("shot_id", "")
            start = int(window.get("start_frame", round(float(window["start"]) * fps)))
            end = int(window.get("end_frame", round(float(window["end"]) * fps)))
            row = {"seg_id": entry.get("seg_id"), "shot_id": sid,
                   "start_frame": start, "end_frame": end}
            contiguous = sid == previous_sid and start == previous_end
            # 帧连续但换镜头 = 原片自己的剪辑点(续播路径), 不是跳切。
            # 镜头边界取整会留 1~2 帧缝(≈83ms, 不可感), 视为连续。
            seamless = 0 <= start - previous_end <= 2
            # 原声窗口是原片连续区间按镜头边界的记账拆分: 豁免重复与短闪判定,
            # 帧重叠与时间倒退仍严格检查。
            if sid in seen_shots and not contiguous and not is_oa:
                duplicate_shots.append(row)
            if start < previous_end:
                overlaps.append(row)
                regressions.append(row)
            if window.get("reused"):
                reused.append(row)
            if (end - start) / fps + 1e-6 < min_window_sec and \
                    float(entry.get("audio_dur", 0)) >= min_window_sec and \
                    not seamless and not is_oa:  # 帧连续窗口(顺延/续播)短不算闪
                short_windows.append(row)
            seen_shots.add(sid)
            intervals.append((start, end, sid))
            previous_end = max(previous_end, end)
            previous_sid = sid
    report = {
        "status": "passed" if not any((duplicate_shots, overlaps, regressions,
                                       short_windows, reused)) else "failed",
        "n_segments": len(edl), "n_windows": len(intervals),
        "duplicate_shots": duplicate_shots,
        "overlapping_source_frames": overlaps,
        "source_time_regressions": regressions,
        "too_short_windows": short_windows,
        "explicit_reuse": reused,
        "fps": fps,
    }
    return report


# ---------------------------------------------------------------------------
# 渲染内核(从 step_e_render.py 抄入; print → _log, hdr_vf 按片源探测)
# ---------------------------------------------------------------------------

def _content_fp(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True,
                                     default=str).encode("utf-8")).hexdigest()[:16]


def _file_sig(path: str) -> tuple:
    p = Path(path)
    if not p.exists():
        return (str(p), 0, 0)
    s = p.stat()
    return (str(p.resolve()), s.st_size, s.st_mtime_ns)


def _cache_ok(path: str, fp: str, duration: float, stream: str,
              tolerance: float) -> bool:
    p = Path(path)
    side = Path(path + ".fp")
    if not p.exists() or not side.exists() or side.read_text().strip() != fp:
        return False
    try:
        return abs(media_duration(path, stream) - duration) < tolerance
    except Exception:
        return False


def _cache_mark(path: str, fp: str) -> None:
    Path(path + ".fp").write_text(fp, encoding="utf-8")


def _mix_bed(video: str, windows: list[tuple[float, float]], dur: float,
             narr: str, out: str, narr_end: float | None = None,
             tail_vol: float | None = None,
             bed_vol: float | None = None,
             narr_gain: float | None = None) -> None:
    """解说 + 与每个画面窗口真正对应的原片原声(逐窗口抽原声后 concat,
    声音和蒙太奇窗口保持一致)。

    音量全部显式传参(不读模块全局): 调用方用哪组值算缓存指纹, 就必须用同
    一组值混音, 否则并发改全局时会产出"错误音量+正确指纹"的毒缓存。
    narr_end/tail_vol 给呼吸留白做分时包络:解说在讲时原声压到 bed_vol,
    解说结束(narr_end 起 0.3s 渐入)原声升到 tail_vol —— 解说与原声互斥。"""
    bv = BED_VOL if bed_vol is None else bed_vol
    ng = NARR_GAIN if narr_gain is None else narr_gain
    inputs, filters, labels = [], [], []
    for i, (start, wdur) in enumerate(windows):
        ss = max(0.0, start - PRESEEK)
        off = start - ss
        inputs += ["-ss", f"{ss:.3f}", "-i", video]
        filters.append(f"[{i}:a]atrim=start={off:.3f}:duration={wdur:.3f},"
                       f"asetpts=PTS-STARTPTS[b{i}]")
        labels.append(f"[b{i}]")
    narr_idx = len(windows)
    inputs += ["-i", narr]
    if narr_end is not None and tail_vol is not None and tail_vol > 0 \
            and narr_end < dur - 0.05:
        ne, ramp = narr_end, 0.3
        vol_expr = (f"if(lt(t\\,{ne:.3f})\\,{bv:.4f}\\,"
                    f"if(lt(t\\,{ne + ramp:.3f})\\,"
                    f"{bv:.4f}+({tail_vol:.4f}-{bv:.4f})*(t-{ne:.3f})/{ramp}\\,"
                    f"{tail_vol:.4f}))")
        bed_vol_filter = f"volume='{vol_expr}':eval=frame"
    else:
        bed_vol_filter = f"volume={bv:.4f}"
    filters.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1,"
                   f"apad,atrim=duration={dur:.6f},{bed_vol_filter}[bed]")
    # MP3 的容器时长和实际可解码采样常差 20~50ms, 在本段内补齐,
    # 误差不累积到长片末尾, 余量只保留轻微环境声。
    filters.append(f"[{narr_idx}:a]volume={ng:.4f},apad,"
                   f"atrim=duration={dur:.6f}[nr]")
    filters.append("[nr][bed]amix=inputs=2:duration=longest:dropout_transition=0:"
                   f"normalize=0,atrim=duration={dur:.6f},alimiter=limit=0.95[a]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[a]", "-t", f"{dur:.3f}", "-ar", "44100", "-ac", "2", out])


def _loudness(path: str):
    """volumedetect 量成片响度(mean/max dB), 质检用。"""
    r = run(["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
            check=False)
    m = re.search(r"mean_volume: ([-\d.]+) dB", r.stderr)
    x = re.search(r"max_volume: ([-\d.]+) dB", r.stderr)
    return (float(m.group(1)) if m else None, float(x.group(1)) if x else None)


def _global_speedup(path: str, factor: float) -> None:
    """对最终成片做一次整体变速重编(字幕已烧进画面, 会一起同步加速)。"""
    if abs(factor - 1.0) < 1e-3:
        return
    tmp = str(Path(path).with_suffix(".spd.mp4"))
    run(["ffmpeg", "-y", "-i", path,
         "-filter_complex", f"[0:v]setpts=PTS/{factor},fps={FPS}[v];[0:a]atempo={factor}[a]",
         "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", PRESET, "-crf", "20", "-pix_fmt", PIXFMT,
         "-threads", ENC_THREADS, "-c:a", "aac", "-b:a", "192k", tmp])
    Path(tmp).replace(path)


def shot_index(shots_path: str) -> dict:
    data = load_json(shots_path)
    rows = data.get("shots", []) if isinstance(data, dict) else data
    return {s["shot_id"]: s for s in rows}


def cut_clip(video: str, start: float, dur: float, speed: float, out: str) -> None:
    """从原片切一段, 统一规格 + 按 speed 变速(视频 setpts, 丢原声)。
    快速 seek: -ss 放 -i 前跳到最近关键帧, 再用输出端 -ss 补 PRESEEK 秒到精确帧。"""
    ss = max(0.0, start - PRESEEK)
    off = start - ss
    vf = (hdr_vf(video) + f"setpts={speed}*PTS,scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}")
    run(["ffmpeg", "-y", "-ss", f"{ss:.3f}", "-i", video, "-ss", f"{off:.3f}",
         "-t", f"{dur:.3f}",
         "-vf", vf, "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", "21",
         "-pix_fmt", PIXFMT, "-r", str(FPS), "-threads", ENC_THREADS, out])


def _seg_vdur(e: dict) -> float:
    """段画面时长: 卷引擎带呼吸留白时 video_dur > audio_dur,
    画面按 video_dur 切, 解说音频 apad 补静音——旁白念完画面继续演。"""
    return float(e.get("video_dur") or e.get("audio_dur", 0) or 0)


def _parse_windows(e: dict, shots: dict):
    """从 edl 解析画面窗口 [(start, dur), ...]。
    - windows 数组(V3): 直接取。
    - 'start-end' 时间段字符串: 直接取。
    - 纯 shot_id(标注源 legacy): 去 shots 表查起止。"""
    if e.get("windows"):
        return [(float(w["start"]), float(w["end"]) - float(w["start"]))
                for w in e["windows"] if float(w["end"]) > float(w["start"])]
    wins = []
    for sid in e["shot_ids"]:
        if "-" in sid and sid.replace("-", "").replace(".", "").isdigit():
            st, en = (float(x) for x in sid.split("-"))
        else:
            sh = shots.get(sid, {"start": 0, "end": e["audio_dur"]})
            st, en = sh["start"], sh["end"]
        wins.append((st, en - st))
    return wins


def _cut_seg_video(video: str, windows: list, audio_dur: float,
                   base: str, seg_v: str) -> None:
    """产出一段解说对应的画面 seg_v, 精确 = audio_dur(带尾窗时=video_dur)。
    - 单窗口: 从窗口起点切, 窗口远长于解说时从中前部取(跳开头转场)。
    - 多窗口: 逐窗口切好 → concat → 裁到 audio_dur。"""
    if len(windows) <= 1:
        wst, wdur = windows[0]
        need = audio_dur + 1.0
        if wdur > need + 2:
            cs, cdur = wst + (wdur - need) * 0.4, need
        else:
            cs, cdur = wst, wdur
        raw = base + "_raw.mp4"
        cut_clip(video, cs, cdur, 1.0, raw)
        _trim_to(raw, audio_dur, seg_v)
        return
    parts = []
    for j, (wst, wdur) in enumerate(windows):
        praw = f"{base}_w{j}_raw.mp4"
        pv = f"{base}_w{j}.mp4"
        cut_clip(video, wst, wdur, 1.0, praw)
        _trim_to(praw, wdur, pv)               # 每窗口精确到自己的 slice 时长
        parts.append(pv)
    merged = f"{base}_merged.mp4"
    _concat(parts, merged)
    _trim_to(merged, audio_dur, seg_v)         # 拼接后精确裁到目标时长(音画对齐前提)


def _precut_all(edl: list, shots: dict, video: str, clips_dir: str,
                breath_every: int, breath_sec: float) -> None:
    """并行预切所有段画面(+原声段+呼吸段)。各段独立, 线程池吃满多核。
    已切好且时长对的段跳过(断点续跑)。切完后主循环只做记账。"""
    jobs = []
    for idx, e in enumerate(edl):
        if e.get("original_audio"):
            wins = _parse_windows(e, shots)
            bv = f"{clips_dir}/oa_{e['seg_id']}.mp4"
            oa_fp = _content_fp("oa-v1", _file_sig(video), wins, W, H, FPS, PIXFMT)
            if not _cache_ok(bv, oa_fp, e["audio_dur"], "v", 0.15):
                jobs.append(("oa", video, wins[0][0], e["audio_dur"], bv,
                             f"{clips_dir}/oa_{e['seg_id']}.wav", oa_fp))
            continue
        wins = _parse_windows(e, shots)
        vdur = _seg_vdur(e)
        seg_v = f"{clips_dir}/seg_{e['seg_id']}.mp4"
        seg_fp = _content_fp("seg-v3-tail", _file_sig(video), wins, vdur,
                             W, H, FPS, PIXFMT)
        if not _cache_ok(seg_v, seg_fp, vdur, "v", 0.15):
            jobs.append(("seg", video, wins, vdur,
                         f"{clips_dir}/seg_{e['seg_id']}", seg_v, seg_fp))
        if (breath_every > 0 and (idx + 1) % breath_every == 0
                and idx < len(edl) - 1):
            bv = f"{clips_dir}/breath_{e['seg_id']}.mp4"
            ba = f"{clips_dir}/breath_{e['seg_id']}.wav"
            b_st = wins[0][0] + e["audio_dur"]
            b_fp = _content_fp("breath-v1", _file_sig(video), b_st, breath_sec)
            if not _cache_ok(bv, b_fp, breath_sec, "v", 0.3):
                jobs.append(("breath", video, b_st, breath_sec, bv, ba, b_fp))
    if not jobs:
        _log("[E] 预切: 所有段已就绪(断点续跑), 跳过")
        return

    def _do(j):
        if j[0] == "seg":
            _, v, wins, adur, base, seg_v, seg_fp = j
            _cut_seg_video(v, wins, adur, base, seg_v)
            _cache_mark(seg_v, seg_fp)
        elif j[0] == "oa":
            _, v, ost, odur, bv, ba, oa_fp = j
            _cut_with_audio(v, ost, odur, bv, ba)
            _cache_mark(bv, oa_fp)
        else:
            _, v, bst, bsec, bv, ba, b_fp = j
            _cut_with_audio(v, bst, bsec, bv, ba)
            _cache_mark(bv, b_fp)

    _log(f"[E] 并行切片: {len(jobs)} 段待切, {CUT_WORKERS} 并发, preset={PRESET}")
    with ThreadPoolExecutor(max_workers=CUT_WORKERS) as ex:
        list(ex.map(_do, jobs))
    _log(f"[E] 并行切片完成 ({len(jobs)} 段)")


def _rebuild_subtitle(script_path: str, seg_offsets: dict, out: str,
                      extra_cues: list | None = None) -> None:
    """按每段在成片的真实起点(seg_id→offset)重建解说字幕;
    原声穿插段的台词字幕(extra_cues, 绝对时间)一并合入。"""
    segs = load_json(script_path)
    cues = []
    for s in segs:
        base = seg_offsets.get(s.get("seg_id"))
        if base is None:
            continue
        for sent in s.get("sentences", []):
            cues.append((base + sent["start"], base + sent["end"],
                         sent.get("subtitle_text", sent.get("text", ""))))
    cues.extend(tuple(x) for x in (extra_cues or []))
    cues.sort(key=lambda x: x[0])
    lines = []
    for i, (st, en, text) in enumerate(cues, 1):
        lines.append(f"{i}\n{fmt_ts(st)} --> {fmt_ts(en)}\n{balanced_wrap(text)}\n")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _trim_to(src: str, dur: float, out: str) -> None:
    """把视频精确对齐到 dur 秒: 长了裁短, 短了定格最后一帧补足。
    必须严格=dur, 否则视频轨与音频轨累积错位导致全片音画不同步。"""
    src_dur = media_duration(src, "v")
    if src_dur >= dur:
        run(["ffmpeg", "-y", "-i", src, "-t", f"{dur:.3f}",
             "-c:v", "libx264", "-preset", PRESET, "-crf", "21",
             "-pix_fmt", PIXFMT, "-r", str(FPS), "-threads", ENC_THREADS, "-an", out])
    else:
        # 源不够长(绑定原片区间短于解说): 用 tpad 定格最后一帧补到 dur
        run(["ffmpeg", "-y", "-i", src,
             "-vf", f"tpad=stop_mode=clone:stop_duration={dur - src_dur + 0.1:.3f}",
             "-t", f"{dur:.3f}",
             "-c:v", "libx264", "-preset", PRESET, "-crf", "21",
             "-pix_fmt", PIXFMT, "-r", str(FPS), "-threads", ENC_THREADS, "-an", out])


def _cut_with_audio(video: str, start: float, dur: float, out_v: str, out_a: str,
                    gain: float = 2.5) -> None:
    """切原片一段(原声段/呼吸段), 统一画面规格 + 提取原声。
    原声用 loudnorm 响度归一化到与解说相近(约-17dB), 避免各段音量时大时小。"""
    vf = (hdr_vf(video) + f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}")
    ss = max(0.0, start - PRESEEK)
    off = start - ss
    run(["ffmpeg", "-y", "-ss", f"{ss:.3f}", "-i", video, "-ss", f"{off:.3f}",
         "-t", f"{dur:.3f}",
         "-vf", vf, "-an", "-c:v", "libx264", "-preset", PRESET, "-crf", "21",
         "-pix_fmt", PIXFMT, "-r", str(FPS), "-threads", ENC_THREADS, out_v])
    # 原声: loudnorm 归一到与解说一致的响度(I=-17), 再限幅防爆音
    run(["ffmpeg", "-y", "-ss", f"{ss:.3f}", "-i", video, "-ss", f"{off:.3f}",
         "-t", f"{dur:.3f}",
         "-vn", "-af", "loudnorm=I=-17:TP=-1.5:LRA=11,alimiter=limit=0.95",
         "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", out_a])


def _concat(parts: list[str], out: str) -> None:
    """concat demuxer 拼接同规格片段。"""
    if len(parts) == 1:
        run(["ffmpeg", "-y", "-i", parts[0], "-c", "copy", out])
        return
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{Path(p).resolve()}'\n")
    # 切片已统一规格, 这里可安全 -c copy; 若仍报错回退重编
    r = run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-c", "copy", out], check=False)
    if r.returncode != 0:
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-c:v", "libx264", "-crf", "21", "-pix_fmt", PIXFMT, "-r", str(FPS), out])


def _concat_audio_plain(parts: list[str], out: str,
                        durations: list[float] | None = None) -> None:
    """纯拼接音频段, 不做交叉淡化。
    durations 给定时, 每段在自身边界内补齐/裁短到对应视频段的整帧时长,
    误差不跨段累计; 同时统一采样率, 避免参数差异导致拼接问题。"""
    norm = []
    for i, p in enumerate(parts):
        np_ = f"{out}.n{i}.wav"
        cmd = ["ffmpeg", "-y", "-i", p]
        if durations is not None:
            cmd += ["-af", f"apad,atrim=duration={durations[i]:.6f}"]
        cmd += ["-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", np_]
        run(cmd)
        norm.append(np_)
    lst = out + ".txt"
    with open(lst, "w") as f:
        for p in norm:
            f.write(f"file '{Path(p).resolve()}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])


def _mux(video: str, narration: str, out: str, subtitle: str | None = None,
         bgm: str | None = None, bgm_volume: float = 0.18,
         sub_pos: str = "top", font_name: str = "Noto Sans CJK SC") -> None:
    """合成画面+解说(+可选BGM +可选字幕烧录)。
    音频混音链: 解说为主, BGM 压低垫底。字幕存在则烧录(重编码), 否则 -c copy。"""
    inputs = ["-i", video, "-i", narration]          # 0:v画面  1:a解说
    amix_srcs = ["[1:a]"]                            # 参与混音的音轨标签
    fc = []
    idx = 2

    if bgm:
        inputs += ["-i", bgm]                        # idx: BGM
        fc.append(f"[{idx}:a]volume={bgm_volume}[bgm]")
        amix_srcs.append("[bgm]")
        idx += 1

    # 混音: 解说优先(duration=first 跟随解说长度)
    if len(amix_srcs) > 1:
        fc.append(f"{''.join(amix_srcs)}amix=inputs={len(amix_srcs)}:"
                  f"duration=first:dropout_transition=0:normalize=0[aout]")
        amap = "[aout]"
    else:
        amap = "1:a"

    # 视频: 有字幕则烧录(重编码), 否则 copy
    if subtitle:
        sub = str(Path(subtitle).resolve())
        # Alignment: 2=底部居中, 8=顶部, 5=正中。sub_pos: top/middle/lower/bottom
        # lower=中下方(底部对齐但上抬, 落在画面下1/3处)
        align = 8 if sub_pos == "top" else (5 if sub_pos == "middle" else 2)
        margin_v = 60 if sub_pos == "lower" else 45
        style = (f"FontName={font_name},FontSize=20,"
                 f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                 f"BackColour=&H99000000,Bold=1,BorderStyle=1,Outline=2,"
                 f"Shadow=1,Alignment={align},MarginV={margin_v}")
        # 转义路径里的冒号(ffmpeg filter 语法要求)
        sub_esc = sub.replace(":", "\\:")
        fc.append(f"[0:v]subtitles='{sub_esc}':force_style='{style}'[vout]")
        vmap = "[vout]"
        vcodec = ["-c:v", "libx264", "-preset", PRESET, "-crf", "21",
                  "-pix_fmt", PIXFMT, "-threads", ENC_THREADS]
    else:
        vmap = "0:v"
        vcodec = ["-c:v", "copy"]

    cmd = ["ffmpeg", "-y", *inputs]
    if fc:
        cmd += ["-filter_complex", ";".join(fc)]
    cmd += ["-map", vmap, "-map", amap, *vcodec,
            "-c:a", "aac", "-b:a", "192k", "-ac", "2",  # 强制双声道(mono复制到双声道)
            "-movflags", "+faststart", "-shortest", out]
    run(cmd)


def _render(edl_path: str, video: str, shots_path: str, out: str,
            clips_dir: str, subtitle: str | None = None, bgm: str | None = None,
            bgm_volume: float = 0.18, sub_pos: str = "top",
            script_path: str | None = None,
            breath_every: int = 0, breath_sec: float = 6.0) -> dict:
    """渲染主流程(源 step_e_render.render 的 v11 用法路径), 返回质检报告。"""
    edl = load_json(edl_path)
    # V3 EDL 必须再次通过无重复硬门禁: 即使有人手工改过 EDL,
    # 渲染层也不能把重叠/倒带镜头写进成片。
    if edl and any(str(x.get("schema_version", "")).startswith("3") for x in edl):
        timeline_meta = load_json(shots_path) if shots_path and Path(shots_path).exists() else {}
        qc = audit_edl(edl, fps=float(timeline_meta.get("fps", FPS) or FPS),
                       min_window_sec=MIN_WINDOW_SEC)
        if qc["status"] != "passed":
            raise RuntimeError(
                "拒绝渲染未通过无重复质检的EDL: "
                f"重复{len(qc['duplicate_shots'])}/"
                f"重叠{len(qc['overlapping_source_frames'])}/"
                f"倒退{len(qc['source_time_regressions'])}/"
                f"短闪{len(qc['too_short_windows'])}")
    shots = shot_index(shots_path) if shots_path and Path(shots_path).exists() else {}
    Path(clips_dir).mkdir(parents=True, exist_ok=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    # --- 0. 并行预切所有段(多核加速); 主循环命中断点续跑分支只做记账 ---
    _precut_all(edl, shots, video, clips_dir, breath_every, breath_sec)

    # --- 1. 逐段切画面 + 构造每段音频 ---
    seg_videos, seg_audios, seg_durations = [], [], []
    seg_offsets: dict[str, float] = {}   # 解说段 seg_id → 成片起始时间(字幕重定位用)
    oa_cues = []                         # 原声段台词字幕(绝对时间)
    cum = 0.0
    for idx, e in enumerate(edl):
        wins = _parse_windows(e, shots)
        first_st = wins[0][0]             # 首窗口起点(垫底原声/呼吸段接续用)

        # --- 原声穿插段: 电影自己说话(原片画面+loudnorm原声, 无解说无BGM) ---
        if e.get("original_audio"):
            bv = f"{clips_dir}/oa_{e['seg_id']}.mp4"
            ba = f"{clips_dir}/oa_{e['seg_id']}.wav"
            oa_fp = _content_fp("oa-v1", _file_sig(video), wins, W, H, FPS, PIXFMT)
            if not _cache_ok(bv, oa_fp, e["audio_dur"], "v", 0.15):
                _cut_with_audio(video, first_st, e["audio_dur"], bv, ba)
                _cache_mark(bv, oa_fp)
            odur = media_duration(bv, "v")
            seg_videos.append(bv)
            seg_audios.append(ba)
            seg_durations.append(odur)
            for line in e.get("subtitle_lines", []):
                oa_cues.append((cum + float(line["start"]),
                                cum + min(float(line["end"]), odur),
                                str(line.get("text", ""))))
            cum += odur
            _log(f"  [oa] {e['seg_id']}: 原声{odur:.1f}s @原片{first_st:.0f}s")
            continue

        seg_v = f"{clips_dir}/seg_{e['seg_id']}.mp4"
        vdur = _seg_vdur(e)
        seg_fp = _content_fp("seg-v3-tail", _file_sig(video), wins, vdur,
                             W, H, FPS, PIXFMT)
        # 断点续跑: seg_v 已存在且指纹/时长对(渲染常被环境杀, 复用不重切)
        if not _cache_ok(seg_v, seg_fp, vdur, "v", 0.15):
            _cut_seg_video(video, wins, vdur,
                           f"{clips_dir}/seg_{e['seg_id']}", seg_v)
            _cache_mark(seg_v, seg_fp)
        # 视频只能落在整帧边界, 真实段长可能比 MP3 标称时长多几十毫秒。
        # 后续音频、字幕都以这个最终画面段长为唯一时间基。
        seg_dur = media_duration(seg_v, "v")

        # 该段音频: 解说为主 + 原片原声垫底;有呼吸留白时,留白部分原声升到
        # tail_vol(解说停、原声起)——bed=0 也要为留白建原声轨。
        # 音量在此一次快照: 指纹与混音必须用同一组值(防并发改全局的毒缓存)
        bed_v, tail_v, narr_g = BED_VOL, TAIL_VOL, NARR_GAIN
        tail = float(e.get("tail_sec", 0) or 0)
        need_tail_audio = tail > 0.05 and tail_v > 0
        if bed_v > 0 or need_tail_audio:
            narr_end = seg_dur - tail if need_tail_audio else None
            seg_a = f"{clips_dir}/sega_{e['seg_id']}.wav"
            audio_fp = _content_fp("bed-v4-tail-envelope", _file_sig(video), wins,
                                   _file_sig(e["audio_path"]), seg_dur,
                                   bed_v, narr_g, tail_v,
                                   narr_end if narr_end is not None else -1)
            if not _cache_ok(seg_a, audio_fp, seg_dur, "a", 0.02):
                _mix_bed(video, wins, seg_dur, e["audio_path"], seg_a,
                         narr_end=narr_end,
                         tail_vol=tail_v if need_tail_audio else None,
                         bed_vol=bed_v, narr_gain=narr_g)
                _cache_mark(seg_a, audio_fp)
            seg_audios.append(seg_a)
        else:
            seg_audios.append(e["audio_path"])
        seg_videos.append(seg_v)
        seg_durations.append(seg_dur)
        seg_offsets[e["seg_id"]] = cum
        cum += seg_dur
        _log(f"  {e['seg_id']}: {e['audio_dur']:.0f}s · {len(wins)}镜"
             f"{f' · 留白{tail:.1f}s' if tail > 0.05 else ''}")

        # --- 每隔 breath_every 段, 插一个纯原片原声"呼吸段"(无解说无字幕) ---
        #   原片从"该镜头解说所覆盖画面之后"接着放(不重复刚讲过的那几秒)。
        if (breath_every > 0 and (idx + 1) % breath_every == 0
                and idx < len(edl) - 1):
            bv = f"{clips_dir}/breath_{e['seg_id']}.mp4"
            ba = f"{clips_dir}/breath_{e['seg_id']}.wav"
            breath_st = first_st + e["audio_dur"]   # 接在解说覆盖画面之后
            # 呼吸段同样要内容指纹: verify 治愈/改稿会改 audio_dur, 起点随之
            # 移动, 只查文件存在会静默复用过期位置的画面
            b_fp = _content_fp("breath-v1", _file_sig(video), breath_st, breath_sec)
            if not _cache_ok(bv, b_fp, breath_sec, "v", 0.3):
                _cut_with_audio(video, breath_st, breath_sec, bv, ba)
                _cache_mark(bv, b_fp)
            bdur = media_duration(bv, "v")
            seg_videos.append(bv)
            seg_audios.append(ba)
            seg_durations.append(bdur)
            cum += bdur
            _log(f"    ↳ 呼吸段 {bdur:.1f}s 纯原声@{breath_st:.0f}s")

    # --- 2. 拼接所有段的画面 ---
    full_v = f"{clips_dir}/_full_video.mp4"
    _concat(seg_videos, full_v)

    # --- 3. 拼接音频(纯拼接, 每段音频补齐/裁短到视频段整帧时长) ---
    full_narr = f"{clips_dir}/_full_narration.wav"
    _concat_audio_plain(seg_audios, full_narr, seg_durations)

    # 最终 mux 的 -shortest 会掩盖上游累计漂移, 必须在 mux 之前硬检查。
    full_v_dur = media_duration(full_v, "v")
    full_a_dur = media_duration(full_narr, "a")
    if abs(full_v_dur - full_a_dur) > (1.0 / FPS + 0.01):
        raise RuntimeError(
            f"拒绝合成累计漂移的音画轨: 视频{full_v_dur:.3f}s / "
            f"音频{full_a_dur:.3f}s")
    _log(f"[E] 分段时间基对齐 (视频{full_v_dur:.3f}s / 音频{full_a_dur:.3f}s)")

    # 始终按真实视频段起点重建字幕: 即使没有呼吸段, 逐段整帧取整也会产生
    # 几十毫秒差值; 不在段内归零, 长片后半段就会逐渐漂移。
    sub_use = subtitle
    if script_path and Path(script_path).exists() and subtitle:
        sub_use = f"{clips_dir}/_subtitle_aligned.srt"
        _rebuild_subtitle(script_path, seg_offsets, sub_use, extra_cues=oa_cues)
        _log(f"  字幕已按最终画面时间轴重建 → {sub_use}")

    # --- 4. 混音并合成(字幕烧录 + BGM) ---
    font_name = _detect_cjk_font() or "Noto Sans CJK SC"
    _mux(full_v, full_narr, out, sub_use, bgm, bgm_volume, sub_pos, font_name)

    # --- 4.6 成片整体微加速(默认 1.0 原速, 环境变量 RENDER_SPEEDUP 可开) ---
    if abs(SPEEDUP - 1.0) > 1e-3:
        _global_speedup(out, SPEEDUP)
        _log(f"  成片整体 {SPEEDUP}x 加速")

    # --- 5. 自检 ---
    vd = media_duration(out, "v")
    ad = media_duration(out, "a")
    _log(f"[E] 成片 {out}  视频{vd:.1f}s 音频{ad:.1f}s"
         f"{' +字幕' if subtitle else ''}{' +BGM' if bgm else ''}")
    av_drift = abs(vd - ad)
    if av_drift > 0.5:
        _log(f"[E] 警告: 音视频时长差 {av_drift:.2f}s > 0.5s, 建议检查")
    else:
        _log(f"[E] 音视频对齐 (差 {av_drift:.2f}s)")
    mean_db, max_db = _loudness(out)
    loudness_flag = "ok"
    if mean_db is not None:
        loudness_flag = ("mean-too-low" if mean_db < -28 else
                         ("clip-risk" if (max_db or 0) > -0.5 else "ok"))
        _log(f"[E] 响度[{loudness_flag}] mean {mean_db:.1f}dB / max {max_db:.1f}dB")
    return {
        "n_segments": len(edl),
        "video_duration_sec": round(vd, 3),
        "audio_duration_sec": round(ad, 3),
        "av_drift_sec": round(av_drift, 3),
        "loudness_mean_db": mean_db,
        "loudness_max_db": max_db,
        "loudness_flag": loudness_flag,
        "subtitle_burned": bool(sub_use),
        "aligned_subtitle_path": sub_use if (sub_use and sub_use != subtitle) else None,
    }


# ---------------------------------------------------------------------------
# 工具入口
# ---------------------------------------------------------------------------

def render_narrated(args: dict, ctx: RunContext) -> ToolResult:
    """EDL → 带解说配音+字幕+BGM 的最终成片(内部先 build_srt / build_from_edl)。"""
    global _LOG, BED_VOL
    _LOG = []
    # 垫底原声音量可按片调:中文片默认 0.13(氛围感);外语片建议 0——
    # 排片锚在台词时刻,垫底几乎全是外语人声,留白段只剩它会像"人物自己在说话"。
    # 模块全局在 MCP server 里安全:工具都跑在单线程 executor 上,不会并发互踩。
    if args.get("bed_volume") is not None:
        try:
            bed = float(args["bed_volume"])
            if not 0 <= bed <= 1:
                raise ValueError
        except (TypeError, ValueError):
            return ToolResult(text="[ERROR] bed_volume must be a number in [0, 1]")
        BED_VOL = bed
    else:
        BED_VOL = float(os.environ.get("RENDER_BED_VOLUME", "0.13"))
    global TAIL_VOL
    if args.get("tail_volume") is not None:
        try:
            tv = float(args["tail_volume"])
            if not 0 <= tv <= 1:
                raise ValueError
        except (TypeError, ValueError):
            return ToolResult(text="[ERROR] tail_volume must be a number in [0, 1]")
        TAIL_VOL = tv
    else:
        TAIL_VOL = float(os.environ.get("RENDER_TAIL_VOLUME", "0.85"))
    for key in ("edl_path", "video_path", "timeline_path", "script_path"):
        if not args.get(key):
            return ToolResult(text=f"[ERROR] {key} is required")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffmpeg/ffprobe not found on PATH")

    edl_path = ctx.resolve(args["edl_path"])
    video_path = ctx.resolve(args["video_path"])
    timeline_path = ctx.resolve(args["timeline_path"])
    script_path = ctx.resolve(args["script_path"])
    for name, p in (("edl", edl_path), ("video", video_path),
                    ("timeline", timeline_path), ("script", script_path)):
        if not p.is_file():
            return ToolResult(text=f"[ERROR] {name} file not found: {p}")

    try:
        edl = load_json(edl_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] invalid EDL JSON: {exc}")
    rows = edl.get("segments") if isinstance(edl, dict) else edl
    if not isinstance(rows, list) or not rows:
        return ToolResult(text="[ERROR] EDL has no segments")
    # 渲染内核按 list 契约读 EDL; dict 包裹的 segments 落一份展开版
    work_dir = ctx.resolve(args.get("work_dir") or ".video_agent/render_narrated")
    work_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(edl, dict):
        flat = work_dir / "edl_segments.json"
        flat.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        edl_path = flat

    # 每段解说音频必须可读(TTS 产物路径写在 EDL 里)
    missing_audio = [e.get("seg_id") for e in rows
                     if not e.get("original_audio")
                     and not Path(str(e.get("audio_path") or "")).is_file()]
    if missing_audio:
        return ToolResult(
            text=f"[ERROR] narration audio missing for {len(missing_audio)} segment(s): "
                 f"{missing_audio[:5]}",
            data={"missing_audio_seg_ids": missing_audio})

    output_path = ctx.resolve(args.get("output_path") or "out/final.mp4")
    bgm_volume = float(args.get("bgm_volume", 0.06))
    sub_pos = str(args.get("sub_pos") or "lower")
    if sub_pos not in {"top", "middle", "lower", "bottom"}:
        return ToolResult(text="[ERROR] sub_pos must be one of top/middle/lower/bottom")
    breath_every = int(args.get("breath_every", 0) or 0)
    warnings: list[str] = []

    # --- 字幕: 先探测 CJK 字体, 没有则降级为不烧录(不失败) ---
    srt_path: str | None = None
    subtitle_font: str | None = None
    if bool(args.get("subtitle", True)):
        subtitle_font = _detect_cjk_font()
        if subtitle_font is None:
            warnings.append("no CJK font found via fc-list; subtitle burning "
                            "disabled (install a CJK font, e.g. Noto Sans CJK SC)")
        else:
            srt_path = str(work_dir / "subtitle.srt")
            try:
                build_srt(str(script_path), srt_path, str(edl_path))
            except Exception as exc:
                return ToolResult(text=f"[ERROR] build_srt failed: {exc}",
                                  data={"log": _LOG[-20:]})

    # --- BGM: 素材运行时从 bgm_dir(默认 VE_BGM_DIR)读; 没配/目录空则跳过 ---
    bgm_path: str | None = None
    if bool(args.get("bgm", True)):
        bgm_dir_raw = args.get("bgm_dir") or clean_env("VE_BGM_DIR")
        if not bgm_dir_raw:
            warnings.append("bgm_dir not set and VE_BGM_DIR not configured; BGM skipped")
        else:
            bgm_dir = ctx.resolve(bgm_dir_raw)
            if not _bgm_dir_usable(bgm_dir):
                warnings.append(f"bgm_dir has no usable audio (dir missing/empty or "
                                f"all files carry embedded cover art): {bgm_dir}; BGM skipped")
            else:
                bgm_path = str(work_dir / "bgm.mp3")
                try:
                    build_from_edl(str(edl_path), bgm_path,
                                   str(work_dir / "bgm"), str(bgm_dir))
                except Exception as exc:
                    # BGM 失败不拖垮渲染: 降级为无 BGM 成片
                    warnings.append(f"BGM build failed, rendering without BGM: {exc}")
                    bgm_path = None

    # --- 渲染 ---
    started = time.time()
    try:
        report = _render(str(edl_path), str(video_path), str(timeline_path),
                         str(output_path), clips_dir=str(work_dir / "clips"),
                         subtitle=srt_path, bgm=bgm_path, bgm_volume=bgm_volume,
                         sub_pos=sub_pos, script_path=str(script_path),
                         breath_every=breath_every)
    except subprocess.TimeoutExpired as exc:
        return ToolResult(text=f"[ERROR] ffmpeg timed out after {exc.timeout}s",
                          data={"warnings": warnings, "log": _LOG[-40:]})
    except (RuntimeError, KeyError, ValueError, OSError) as exc:
        return ToolResult(text=f"[ERROR] render failed: {exc}",
                          data={"warnings": warnings, "log": _LOG[-40:]})

    if report["av_drift_sec"] > 0.5:
        warnings.append(f"final A/V duration differs by {report['av_drift_sec']:.2f}s (>0.5s)")
    if report["loudness_flag"] == "mean-too-low":
        warnings.append(f"loudness low: mean {report['loudness_mean_db']:.1f} dB < -28 dB")
    elif report["loudness_flag"] == "clip-risk":
        warnings.append(f"clipping risk: max {report['loudness_max_db']:.1f} dB > -0.5 dB")

    report.update({
        "output_path": str(output_path),
        "work_dir": str(work_dir),
        "subtitle_path": srt_path,
        "subtitle_font": subtitle_font,
        "bgm_path": bgm_path,
        "bgm_volume": bgm_volume if bgm_path else None,
        "warnings": warnings,
        "elapsed_seconds": round(time.time() - started, 3),
        "log": _LOG[-60:],
    })
    parts = [f"Final video rendered: {ctx.virtualize(output_path)} "
             f"({report['video_duration_sec']:.1f}s, {report['n_segments']} segments"
             f"{', subtitles burned' if report['subtitle_burned'] else ''}"
             f"{', BGM mixed' if bgm_path else ''})"]
    if warnings:
        parts.append("[WARNING] " + "; ".join(warnings))
    artifacts = [str(output_path)] + ([srt_path] if srt_path else [])
    return ToolResult(text="\n".join(parts), data=report,
                      artifacts=artifacts, video_paths=[str(output_path)])
