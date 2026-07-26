#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 audio/durations.json 的时间轴同步进 index.html。

重跑 TTS 后 (换音色/改旁白) 音频时长会变, 用本脚本一键同步, 不要手抄数字:
    python3 sync_timeline.py <project_dir>

要求 index.html 遵循 assets/video-template 的约定:
    - 根 div 有 data-duration
    - 音频标签形如 <audio id="aN" src="audio/seg-0N.mp3" data-start=".." data-duration="..">
    - SEGMENTS 数组条目形如 { sel: "#sN", start: .., duration: .., ... }
    - 场景注释形如 <!-- ... 场景 N: xxx (a.aa - b.bb) ... --> (可选)

同步后需要重新渲染: bash build_video.sh <project_dir>
"""

import json
import re
import sys
from pathlib import Path


def main():
    project = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    html_path = project / "index.html"
    dur_path = project / "audio" / "durations.json"
    for p in (html_path, dur_path):
        if not p.exists():
            print(f"❌ 找不到 {p}", file=sys.stderr)
            sys.exit(1)

    d = json.loads(dur_path.read_text(encoding="utf-8"))
    segs = d["segments"]
    html = html_path.read_text(encoding="utf-8")
    changes = []

    def sub(pattern, repl, text, label, count=0):
        new, n = re.subn(pattern, repl, text, count=count)
        changes.append(f"   {label}: {n} 处")
        return new

    # 1. 根 data-duration (只改带 data-composition-id 块里的第一个)
    html = sub(r'(data-composition-id="[^"]+"[^>]*?data-duration=")[\d.]+(")',
               rf'\g<1>{d["total"]}\g<2>', html, "根 data-duration", count=1)
    if f'data-duration="{d["total"]}"' not in html:
        # 根 div 跨多行时 data-duration 在单独一行
        html = sub(r'(data-start="0" data-duration=")[\d.]+(")',
                   rf'\g<1>{d["total"]}\g<2>', html, "根 data-duration(跨行)", count=1)

    # 2. 音频标签
    for s in segs:
        html = sub(
            rf'(<audio id="a{s["id"]}"[^>]*?data-start=")[\d.]+("\s+data-duration=")[\d.]+(")',
            rf'\g<1>{s["audio_start"]}\g<2>{s["audio_duration"]}\g<3>',
            html, f'audio a{s["id"]}')

    # 3. SEGMENTS 数组
    for s in segs:
        html = sub(
            rf'(sel: "#s{s["id"]}", start: )[\d.]+(,\s*duration: )[\d.]+(,)',
            rf'\g<1>{s["start"]}\g<2>{s["duration"]}\g<3>',
            html, f'SEGMENTS #s{s["id"]}')

    # 4. 场景注释里的时间区间 (可选, 匹配不到就跳过)
    bounds = [s["start"] for s in segs] + [d["total"]]
    for s in segs:
        html, n = re.subn(
            rf'(场景 {s["id"]}: [^(]*\()[\d.]+ - [\d.]+(\))',
            rf'\g<1>{s["start"]:.2f} - {bounds[s["id"]]:.2f}\g<2>', html)

    html_path.write_text(html, encoding="utf-8")
    print(f"==> 同步 {dur_path} → {html_path} (total {d['total']}s)")
    print("\n".join(changes))
    missing = [c for c in changes if ": 0 处" in c]
    if missing:
        print("⚠ 以下项没匹配到, 请检查 index.html 是否遵循模板约定:")
        print("\n".join(missing))
        sys.exit(2)
    print("✅ 完成。重新渲染: bash scripts/build_video.sh <project_dir>")


if __name__ == "__main__":
    main()
