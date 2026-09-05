#!/usr/bin/env python3
"""口播稿 -> TTS 配音 + 逐句时间轴。

用法:
  python tts.py --script script.txt --out build [--voice zh-CN-XiaoxiaoNeural] [--rate +0%] [--pitch +0Hz]

输出 (写入 --out 目录):
  voice.mp3      配音音频
  timeline.json  逐句时间轴: sentences[{i,text,start,end,words:[{w,t,d}]}], 时间单位毫秒
  subtitles.srt  逐句 SRT 字幕 (供平台上传, 渲染时画面内字幕由 HTML 引擎负责)

原理: edge-tts 在流式合成时回调 WordBoundary(每个词的 offset/duration),
按句子归一化字数把它们聚合回句子, 得到逐句精确起止时间。
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

SENT_END = set("。！？；!?;\n")
SOFT = set("，、,：:—…·")

# 常用中文音色 (更多: edge-tts --list-voices)
VOICES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",  # 女声, 自然通用(默认)
    "xiaoyi": "zh-CN-XiaoyiNeural",      # 女声, 活泼
    "yunxi": "zh-CN-YunxiNeural",        # 男声, 阳光年轻
    "yunjian": "zh-CN-YunjianNeural",    # 男声, 沉稳浑厚
    "yunyang": "zh-CN-YunyangNeural",    # 男声, 新闻播报
}


def split_sentences(text: str, max_len: int = 60) -> list[str]:
    """按句末标点/换行分句; 超长句在最近的逗号处强制切分。"""
    sents, buf = [], ""
    for ch in text.replace("\r\n", "\n"):
        buf += ch
        if ch in SENT_END:
            if buf.strip():
                sents.append(buf.strip())
            buf = ""
    if buf.strip():
        sents.append(buf.strip())

    out = []
    for s in sents:
        while len(s) > max_len:
            cut = max((i for i, c in enumerate(s[:max_len]) if c in SOFT), default=-1)
            if cut < 10:
                break
            out.append(s[: cut + 1].strip())
            s = s[cut + 1 :].strip()
        if s:
            out.append(s)
    return out


def norm(s: str) -> str:
    """去掉空白和标点, 只留文字/数字, 用于把词边界聚合回句子。"""
    return re.sub(r"[\W_]+", "", s, flags=re.UNICODE)


def ffprobe_ms(path: Path) -> int:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True,
        )
        return int(float(r.stdout.strip()) * 1000)
    except Exception:
        return 0


def fmt_srt(ms: int) -> str:
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


async def synth(text: str, voice: str, rate: str, pitch: str, volume: str):
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume,
                                boundary="WordBoundary")
    audio = bytearray()
    words = []  # {w,t,d} 毫秒
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            words.append({
                "w": chunk["text"],
                "t": chunk["offset"] / 1e4,      # 100ns -> ms
                "d": chunk["duration"] / 1e4,
            })
    return bytes(audio), words


def build_timeline(sents: list[str], words: list[dict], audio_ms: int = 0) -> list[dict]:
    if not words:
        # 回退: 拿不到词边界时按归一化字数占比均分音频时长
        weights = [len(norm(s)) or 1 for s in sents]
        total, t, result = sum(weights), 0, []
        dur = audio_ms or total * 250
        for i, s in enumerate(sents):
            span = int(dur * weights[i] / total)
            result.append({"i": i, "text": s, "start": t, "end": t + span,
                           "words": [], "hold_end": t + span})
            t += span
        if result:
            result[-1]["hold_end"] = max(result[-1]["hold_end"], dur)
        return result
    """把词边界按归一化字数聚合回句子。"""
    result, wi = [], 0
    for i, sent in enumerate(sents):
        need = len(norm(sent))
        consumed, start, end = 0, None, None
        used = []
        while wi < len(words) and consumed < need:
            w = words[wi]
            if start is None:
                start = w["t"]
            end = w["t"] + w["d"]
            consumed += len(norm(w["w"]))
            used.append(w)
            wi += 1
        if start is None:  # 该句没有任何词边界(罕见): 挂到前一句结尾
            prev_end = result[-1]["end"] if result else 0
            start = end = prev_end
        result.append({
            "i": i, "text": sent,
            "start": round(start), "end": round(max(end, start + 300)),
            "words": used,
        })
    # hold_end: 场景停留到下一句开始(短停顿)或句尾+缓冲(长停顿), 供场景切分用
    audio_end = result[-1]["end"] if result else 0
    for j, s in enumerate(result):
        nxt = result[j + 1]["start"] if j + 1 < len(result) else None
        gap = (nxt - s["end"]) if nxt else None
        if nxt is None:
            s["hold_end"] = max(s["end"] + 500, audio_end)
        elif gap < 1200:
            s["hold_end"] = nxt
        else:
            s["hold_end"] = s["end"] + min(800, int(gap * 0.6))
    return result


def main():
    ap = argparse.ArgumentParser(description="口播稿 TTS + 逐句时间轴")
    ap.add_argument("--script", required=True, help="口播稿 txt 文件(纯文本)")
    ap.add_argument("--out", default="build", help="输出目录")
    ap.add_argument("--voice", default=VOICES["xiaoxiao"],
                    help=f"edge-tts 音色名或简称: {', '.join(VOICES)}")
    ap.add_argument("--rate", default="+0%", help="语速, 如 +10% / -5%")
    ap.add_argument("--pitch", default="+0Hz", help="音调, 如 +20Hz")
    ap.add_argument("--volume", default="+0%", help="音量")
    args = ap.parse_args()

    voice = VOICES.get(args.voice.lower(), args.voice)
    text = Path(args.script).read_text(encoding="utf-8").strip()
    if not text:
        sys.exit("script 为空")
    sents = split_sentences(text)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[tts] voice={voice} sentences={len(sents)} chars={len(text)}")
    audio, words = asyncio.run(synth(text, voice, args.rate, args.pitch, args.volume))
    if not audio:
        sys.exit("edge-tts 未返回音频(检查网络/代理)")

    mp3 = out / "voice.mp3"
    mp3.write_bytes(audio)
    last_ms = int(words[-1]["t"] + words[-1]["d"]) if words else 0
    audio_ms = ffprobe_ms(mp3) or last_ms

    sentences = build_timeline(sents, words, audio_ms)
    if audio_ms and sentences:
        sentences[-1]["hold_end"] = max(sentences[-1]["hold_end"], audio_ms)

    timeline = {
        "meta": {"voice": voice, "rate": args.rate, "pitch": args.pitch,
                 "audio": mp3.name, "audio_ms": audio_ms, "unit": "ms"},
        "sentences": sentences,
    }
    (out / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")

    srt = "".join(
        f"{k+1}\n{fmt_srt(s['start'])} --> {fmt_srt(s['end'])}\n{s['text']}\n\n"
        for k, s in enumerate(sentences))
    (out / "subtitles.srt").write_text(srt, encoding="utf-8")

    # 供 composition.html 直接 <script src> 引用的字幕数据
    (out / "subtitles.js").write_text(
        "window.SUBTITLES = " + json.dumps(sentences, ensure_ascii=False) + ";",
        encoding="utf-8")

    total = sentences[-1]["end"] if sentences else 0
    print(f"[tts] voice.mp3 {len(audio)/1024:.0f}KB  audio={audio_ms/1000:.1f}s  speech={total/1000:.1f}s")
    for s in sentences:
        print(f"  #{s['i']:>2} {s['start']:>6}-{s['end']:>6}ms  {s['text'][:40]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
