"""旁白（本机备胎）：edge-tts（微软在线 TTS）。用法: python lib/tts-edge.py <projectDir> [scene...]

输出 <后台>/<期>/work/audio/<scene>.mp3 与 .json（duration / segmentStarts / wordList）。
wordList 来自 edge-tts 的 WordBoundary 事件，字段与火山通道一致（{w,s,e}），所以烧录字幕与 字幕.srt 都能用。
正式出片仍推荐火山 lib/tts-volc.mjs（音色/克隆音）；此路径不需要任何付费凭证。

配置（config.json）:
  tts.engine          = "edge" 时 bin/wb 才会走这里
  tts.speed           = 语速倍率（1.2 → edge rate +20%）
  tts.edge.voice      = 音色，如 zh-CN-YunxiNeural / zh-CN-XiaoxiaoNeural / zh-CN-YunjianNeural
  tts.edge.python     = 跑本脚本的解释器（需已装 edge-tts）
  tts.edge.rate/volume/pitch  可选，直接写 edge 的原生格式（+20% / +0% / +0Hz）
环境变量 VOICE / RATE / FORCE_TTS=1（强制重配）可临时覆盖。
"""
import asyncio
import hashlib
import json
import os
import subprocess
import sys

import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CFG = json.load(open(os.path.join(REPO, "config.json"), encoding="utf-8"))


def expand(p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.join(REPO, p)


PROJECTS = expand(CFG["dirs"]["projects"])
BUILD = expand(CFG["dirs"]["build"])
TTSCFG = CFG.get("tts", {}) or {}
EDGE = TTSCFG.get("edge", {}) or {}

VOICE = os.environ.get("VOICE") or EDGE.get("voice") or "zh-CN-YunxiNeural"
SPEED = float(TTSCFG.get("speed", 1.0) or 1.0)
_default_rate = "%+d%%" % round((SPEED - 1) * 100)
RATE = os.environ.get("RATE") or EDGE.get("rate") or _default_rate
VOLUME = EDGE.get("volume", "+0%")
PITCH = EDGE.get("pitch", "+0Hz")


def resolve_project(arg):
    if os.path.isdir(arg):
        return os.path.abspath(arg)
    direct = os.path.join(PROJECTS, arg)
    if os.path.isdir(direct):
        return direct
    dirs = sorted(d for d in os.listdir(PROJECTS) if os.path.isdir(os.path.join(PROJECTS, d)))
    hit = [d for d in dirs if arg.lower() in d.lower()]
    if not hit:
        raise SystemExit("找不到项目「%s」，现有：%s" % (arg, " | ".join(dirs)))
    return os.path.join(PROJECTS, hit[-1])


PROJECT = resolve_project(sys.argv[1] if len(sys.argv) > 1 else ".")
NAME = os.path.basename(PROJECT)
AUDIO = os.path.join(BUILD, NAME, "work", "audio")
SCRIPT = os.path.join(PROJECT, "scenes", "script.json")


def norm(s):
    return "".join(ch for ch in s if ch.isalnum())


def probe_duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]
    ).decode().strip()
    return float(out)


async def one(scene):
    name, segs = scene["name"], scene["segments"]
    full = "".join(segs)
    mp3 = os.path.join(AUDIO, name + ".mp3")
    js = os.path.join(AUDIO, name + ".json")
    key = hashlib.sha1(("|".join([full, VOICE, RATE, VOLUME, PITCH])).encode("utf-8")).hexdigest()

    if os.environ.get("FORCE_TTS") != "1" and os.path.exists(mp3) and os.path.exists(js):
        try:
            old = json.load(open(js, encoding="utf-8"))
            if old.get("cacheKey") == key and old.get("wordList"):
                print("%s: 命中缓存 %.1fs" % (name, old["duration"]))
                return
        except Exception:
            pass

    comm = edge_tts.Communicate(full, VOICE, rate=RATE, volume=VOLUME, pitch=PITCH,
                                boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                e = s + chunk.get("duration", 0) / 1e7
                words.append({"w": chunk["text"], "s": round(s, 3), "e": round(e, 3)})

    if not words:
        print("  ⚠ %s 没拿到 WordBoundary，字幕会退化成按字数估算" % name)

    # 逐字时间 → 每个旁白段的起始秒（与 tts-volc.mjs 同一套算法，保证两条通道对齐一致）
    pos_time = []
    acc = 0
    for w in words:
        pos_time.append((acc, w["s"]))
        acc += len(norm(w["w"]))
    total_norm = len(norm(full))
    starts, p = [], 0
    for sg in segs:
        starts.append(p)
        p += len(norm(sg))
    seg_times = []
    for sp in starts:
        best = 0.0
        for cp, t in pos_time:
            if cp <= sp:
                best = t
            else:
                break
        seg_times.append(best)
    seg_times[0] = 0.0

    dur = probe_duration(mp3)
    info = {
        "name": name, "duration": dur, "segmentStarts": seg_times, "segments": segs,
        "wordList": words, "voice": VOICE, "engine": "edge",
        "words": len(words), "normChars": total_norm, "cacheKey": key,
    }
    with open(js, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    print("%s: %.1fs @%s  starts=%s  words=%d/%d" % (
        name, dur, RATE, ",".join("%.1f" % t for t in seg_times), len(words), total_norm))


async def main():
    os.makedirs(AUDIO, exist_ok=True)
    scenes = json.load(open(SCRIPT, encoding="utf-8"))
    only = sys.argv[2:]
    for sc in scenes:
        if only and sc["name"] not in only:
            continue
        await one(sc)


print("edge-tts: voice=%s rate=%s → %s" % (VOICE, RATE, AUDIO))
asyncio.run(main())
