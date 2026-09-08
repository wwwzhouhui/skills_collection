#!/usr/bin/env python3
"""tts.py — 旁白稿 → 分段配音 + 实测时长表

用法（在视频工程根目录执行）:
    python3 <skill>/scripts/tts.py --script VOICEOVER_ZH.md --out . --voice yunyang

段落规则: 段落间空行分隔（一行 --- 也算分隔）; 一段 = 一个场景 = 一个 mp3。
         Markdown 结构行（# 标题、> 引用、``` 代码块围栏）自动剥离，只有正文进入配音。
产物:
    public/vo/scene{N}.mp3      分段配音（N 从 1 起，与段落顺序一致）
    build/durations.json        {voice, fps, scenes:[{i,text,file,durationSec,frames}]}
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

VOICE_ALIASES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",  # 女·通用
    "xiaoyi": "zh-CN-XiaoyiNeural",      # 女·活泼
    "yunxi": "zh-CN-YunxiNeural",        # 男·阳光
    "yunjian": "zh-CN-YunjianNeural",    # 男·沉稳
    "yunyang": "zh-CN-YunyangNeural",    # 男·播报（技术讲解默认）
}


def parse_segments(text: str) -> list[str]:
    """空行分段；Markdown 结构行（# 标题 / > 引用 / ``` 代码块）替换为空行，只合成正文。

    结构行替换为空行而非直接删除，因此 "正文A / ## 标题 / 正文B"（标题前后无空行）
    也能被正确切成两段。
    """
    lines: list[str] = []
    in_code = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            lines.append("")
            continue
        if in_code or (s and (s.startswith("#") or s.startswith(">"))):
            lines.append("")  # 结构行 → 视为段落分隔
            continue
        lines.append(line)
    parts = re.split(r"\n\s*---+\s*\n|\n\s*\n", "\n".join(lines).strip())
    segs = []
    for p in parts:
        p = " ".join(p.split())  # 压空白但保留中英文间距
        if p:
            segs.append(p)
    return segs


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


async def synth_segment(text: str, voice: str, rate: str, dest: Path) -> None:
    import edge_tts
    last_err = None
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate)
            await asyncio.wait_for(comm.save(str(dest)), timeout=90)  # 防网络挂起
            if dest.stat().st_size > 0:
                return
            raise RuntimeError("empty output")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < 2:
                await asyncio.sleep(2.0 * (attempt + 1))
    raise RuntimeError(
        f"edge-tts 连续失败: {last_err}\n"
        "  排查: 1) 网络能否访问 Microsoft TTS 服务; 2) 升级客户端 "
        "pip install -U edge-tts（微软服务端变更常导致旧版失效）; 3) 稍后重试避开限流"
    )


async def main() -> None:
    ap = argparse.ArgumentParser(description="旁白稿 → 分段配音 + durations.json")
    ap.add_argument("--script", required=True, help="旁白稿路径（段落间空行分隔）")
    ap.add_argument("--out", default=".", help="视频工程根目录（默认当前目录）")
    ap.add_argument("--voice", default="yunyang",
                    help="xiaoxiao|xiaoyi|yunxi|yunjian|yunyang 或完整 edge-tts 音色名")
    ap.add_argument("--rate", default="+0%", help="语速，如 +10%% / -5%%")
    ap.add_argument("--fps", type=int, default=30, help="帧率（用于换算帧数，默认 30）")
    args = ap.parse_args()

    if not re.fullmatch(r"[+-]\d+%", args.rate):
        sys.exit("✗ --rate 格式应为 +10% / -5%（必须带正负号）")

    script_path = Path(args.script)
    if not script_path.exists():
        sys.exit(f"✗ 找不到旁白稿: {script_path}")

    segments = parse_segments(script_path.read_text(encoding="utf-8"))
    if not segments:
        sys.exit("✗ 旁白稿为空")
    for i, s in enumerate(segments, 1):
        if len(s) > 160:
            print(f"  ⚠ 第 {i} 段偏长（{len(s)} 字），单场景建议 ≤120 字，否则画面停留过久")

    voice = VOICE_ALIASES.get(args.voice, args.voice)
    root = Path(args.out)
    vo_dir = root / "public" / "vo"
    build_dir = root / "build"
    vo_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    scenes = []
    for i, text in enumerate(segments, 1):
        dest = vo_dir / f"scene{i}.mp3"
        print(f"  合成 scene{i} … {text[:26]}")
        await synth_segment(text, voice, args.rate, dest)
        dur = ffprobe_duration(dest)
        frames = int(round(dur * args.fps))
        scenes.append({
            "i": i, "text": text, "file": f"vo/scene{i}.mp3",
            "durationSec": round(dur, 3), "frames": frames,
        })
        print(f"    ✓ {dur:.2f}s = {frames}f")

    data = {"voice": voice, "rate": args.rate, "fps": args.fps, "scenes": scenes}
    (build_dir / "durations.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(s["frames"] for s in scenes)
    print(f"\n✓ {len(scenes)} 段配音 → public/vo/ ；时长表 → build/durations.json")
    print(f"  旁白总长 ≈ {total / args.fps:.1f}s（不含场景尾巴与纯视觉镜头）")
    print(f"  下一步: 写 build/scenes.json 后运行 build-timeline.mjs")


if __name__ == "__main__":
    asyncio.run(main())
