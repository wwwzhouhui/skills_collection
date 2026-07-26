#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 index.html: storyboard.json + audio/timeline.json + images/ → 可渲染的 HyperFrames 组合

用法:
    python3 scaffold.py <project_dir> [--template <path>]

前置:
    <project_dir>/storyboard.json          分镜
    <project_dir>/audio/timeline.json      tts_pipeline.py 的产物
    <project_dir>/images/ch-NN.png         每章插图 (ai-image-generator 产物)

产出:
    <project_dir>/index.html               完整可渲染 (bash scripts/build.sh <project_dir>)

模板是全数据驱动的, 本脚本只做三处替换:
    /*__DATA_JSON__*/null   → 合并后的章节数据
    __TOTAL__               → 总时长
    <!--__AUDIO_TAGS__-->   → 每句一个 <audio> 标签
"""

import argparse
import json
import sys
from pathlib import Path


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--template", default=None)
    args = ap.parse_args()

    project = Path(args.project_dir)
    template_path = Path(args.template) if args.template else (
        Path(__file__).resolve().parent.parent / "assets" / "template" / "index.html")

    sb_path = project / "storyboard.json"
    tl_path = project / "audio" / "timeline.json"
    for p in (sb_path, tl_path, template_path):
        if not p.exists():
            die(f"找不到 {p}")

    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    timeline = json.loads(tl_path.read_text(encoding="utf-8"))
    tl_by_id = {c["id"]: c for c in timeline["chapters"]}

    chapters = []
    audio_tags = []
    warnings = []
    for ch in sb["chapters"]:
        cid = ch["id"]
        tc = tl_by_id.get(cid)
        if not tc:
            die(f"timeline.json 里没有章节 {cid} — 改过分镜后要重跑 tts_pipeline.py")
        if len(tc["sentences"]) != len(ch.get("narration", [])):
            die(f"章节 {cid} 句数不一致 (storyboard {len(ch.get('narration', []))} vs "
                f"timeline {len(tc['sentences'])}) — 重跑 tts_pipeline.py")

        layout = ch.get("layout", "illustration")
        image_rel = None
        if layout == "illustration":
            illu_id = (ch.get("illustration") or {}).get("id") or f"ch-{cid:02d}"
            image_rel = f"images/{illu_id}.png"
            if not (project / image_rel).exists():
                warnings.append(f"缺插图 {image_rel} (先跑 make_manifest → inject_style → generate)")
        elif layout == "grid" and not ch.get("panels"):
            die(f"章节 {cid} layout=grid 但缺 panels 数组")
        elif layout == "terminal" and not (ch.get("terminal") or {}).get("lines"):
            die(f"章节 {cid} layout=terminal 但缺 terminal.lines 数组")

        headline = ch["headline"]
        if isinstance(headline, str):
            headline = [headline]

        chapters.append({
            "id": cid,
            "layout": layout,
            "kicker": ch.get("kicker", ""),
            "headline": headline,
            "subhead": ch.get("subhead", ""),
            "card": ch.get("card"),
            "panels": ch.get("panels", []),
            "terminal": ch.get("terminal"),
            "tags": ch.get("tags", []),
            "image": image_rel,
            "start": tc["start"],
            "duration": tc["duration"],
            "sentences": [
                {"text": s["text"], "start": s["start"], "duration": s["duration"]}
                for s in tc["sentences"]
            ],
        })

        for si, s in enumerate(tc["sentences"], 1):
            audio_tags.append(
                f'<audio id="a-ch{cid:02d}-s{si:02d}" src="{s["file"]}" data-start="{s["start"]}" '
                f'data-duration="{s["duration"]}" data-track-index="2"></audio>')

    data = {"title": sb.get("title", ""), "theme": sb.get("theme", "warm"), "chapters": chapters}

    html = template_path.read_text(encoding="utf-8")
    for token in ("/*__DATA_JSON__*/null", "__TOTAL__", "<!--__AUDIO_TAGS__-->"):
        if token not in html:
            die(f"模板缺少占位符 {token}")
    html = html.replace("/*__DATA_JSON__*/null", json.dumps(data, ensure_ascii=False))
    html = html.replace("__TOTAL__", str(timeline["total"]))
    html = html.replace("<!--__AUDIO_TAGS__-->", "\n    ".join(audio_tags))

    out_path = project / "index.html"
    out_path.write_text(html, encoding="utf-8")

    n_sent = sum(len(c["sentences"]) for c in chapters)
    print(f"✅ index.html 已生成: {len(chapters)} 章 / {n_sent} 句 / 总时长 {timeline['total']}s")
    for w in warnings:
        print(f"   ⚠ {w}")
    if warnings:
        print("   插图补齐后无需重跑 scaffold (路径是固定的)")
    print(f"   下一步: bash scripts/build.sh {project}")


if __name__ == "__main__":
    main()
