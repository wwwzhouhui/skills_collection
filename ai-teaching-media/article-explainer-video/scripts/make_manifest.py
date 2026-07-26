#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 storyboard.json 提取每章插图提示词, 生成 ai-image-generator 的 manifest (diagrams.json)

用法:
    python3 make_manifest.py <project_dir>

输出 <project_dir>/diagrams.json (不含风格前缀), 之后走 tech-article-diagram 的注入 + ai-image-generator 生成:

    python3 <tech-article-diagram>/scripts/inject_style.py --style cozy-handdrawn --manifest diagrams.json
    python3 <ai-image-generator>/scripts/generate.py --manifest diagrams-styled.json --output-dir images/ --parallel

插图纵横比固定 4:3 (右栏插图区约 950x620, 模板 object-fit: contain 自适应)。
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("用法: python3 make_manifest.py <project_dir>")
        sys.exit(1)
    project = Path(sys.argv[1])
    sb_path = project / "storyboard.json"
    if not sb_path.exists():
        print(f"❌ 找不到 {sb_path}")
        sys.exit(1)

    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    items = []
    skipped = 0
    for ch in sb.get("chapters", []):
        if ch.get("layout", "illustration") != "illustration":
            skipped += 1
            continue  # grid / statement / terminal 章节不需要插图
        illu = ch.get("illustration") or {}
        brief = (illu.get("brief") or "").strip()
        if not brief:
            print(f"❌ 章节 {ch.get('id')} 缺少 illustration.brief")
            sys.exit(1)
        items.append({
            "id": illu.get("id") or f"ch-{ch['id']:02d}",
            "prompt": brief,
        })

    manifest = {
        "mode": "generation",
        "aspect_ratio": "4:3",
        "resolution": "2K",
        "items": items,
    }
    out_path = project / "diagrams.json"
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {len(items)} 张插图提示词 → {out_path}"
          + (f" (跳过 {skipped} 个 grid/statement 章节)" if skipped else ""))
    print("   下一步: inject_style.py --style cozy-handdrawn --manifest diagrams.json")


if __name__ == "__main__":
    main()
