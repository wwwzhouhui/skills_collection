#!/usr/bin/env python3
"""
风格注入脚本
读取 references/styles/{style}.md 中的风格前缀,注入到 prompt 文件或 manifest JSON 中。

用法:
    # 单文件注入
    python inject_style.py --style notebook --prompt-file diagram-01.txt
    # 输出: diagram-01-styled.txt

    # manifest 批量注入
    python inject_style.py --style notebook --manifest diagrams.json
    # 输出: diagrams-styled.json

    # 自定义输出路径
    python inject_style.py --style notebook --prompt-file diagram-01.txt --output diagram-01-final.txt
"""

import argparse
import json
import re
import sys
from pathlib import Path

STYLE_CHOICES = ("notebook", "infographic", "executive-tech", "cozy-handdrawn", "tech-doodle", "cartoon-infographic", "whiteboard-sketch")

# cozy-handdrawn 始终走 edit 模式; cartoon-infographic 按 item 的 needs_character 动态切换
CARTOON_REFERENCE_IMAGE = "https://r2.cloudnative101.net/assets/katong.png"
EDIT_MODE_STYLES = {"cozy-handdrawn"}
CONDITIONAL_EDIT_STYLES = {"cartoon-infographic"}


def extract_style_prefix(style_raw: str) -> str:
    """提取风格文件中的第一个代码块,作为注入到 prompt 的风格前缀。"""
    code_blocks = re.findall(r"```[\s\S]*?```", style_raw)
    if code_blocks:
        return re.sub(r"```[^\n]*\n?|```$", "", code_blocks[0]).strip()
    return style_raw.strip()


def strip_known_style_prefix(prompt: str, known_prefixes: list[str]) -> str:
    """移除已知风格前缀,避免重复注入。"""
    normalized = prompt.strip()
    for prefix in known_prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix):].lstrip()
    return normalized


def compose_prompt(prompt_body: str, style_prefix: str) -> str:
    """把风格前缀和内容 prompt 合成为最终请求。"""
    return f"{style_prefix}\n\n{prompt_body.strip()}"


def load_all_style_prefixes(styles_dir: Path) -> list[str]:
    """加载所有已知风格的前缀,用于去重。"""
    prefixes = []
    for style_name in STYLE_CHOICES:
        path = styles_dir / f"{style_name}.md"
        if path.exists():
            prefixes.append(extract_style_prefix(path.read_text(encoding="utf-8")))
    return prefixes


def main():
    parser = argparse.ArgumentParser(description="风格注入脚本")
    parser.add_argument("--style", required=True, choices=list(STYLE_CHOICES),
                        help="风格: notebook / infographic / executive-tech / cozy-handdrawn / tech-doodle / cartoon-infographic / whiteboard-sketch")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt-file", type=str, help="单张图的 prompt 文件路径")
    src.add_argument("--manifest", type=str, help="manifest JSON 路径")
    parser.add_argument("--output", type=str, help="输出文件路径(默认自动生成)")
    args = parser.parse_args()

    # 定位 references/styles/ 目录
    script_dir = Path(__file__).parent.resolve()
    styles_dir = script_dir.parent / "references" / "styles"
    style_path = styles_dir / f"{args.style}.md"

    if not style_path.exists():
        print(f"✗ 风格文件不存在: {style_path}")
        sys.exit(1)

    # 加载风格前缀
    style_prefix = extract_style_prefix(style_path.read_text(encoding="utf-8"))
    known_prefixes = load_all_style_prefixes(styles_dir)
    print(f"✓ 加载风格: {args.style} ({len(style_prefix)} 字符)")

    # 单文件模式
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        if not prompt_path.exists():
            print(f"✗ 文件不存在: {prompt_path}")
            sys.exit(1)

        raw_prompt = prompt_path.read_text(encoding="utf-8")
        clean_body = strip_known_style_prefix(raw_prompt, known_prefixes)
        styled_prompt = compose_prompt(clean_body, style_prefix)

        output_path = Path(args.output) if args.output else prompt_path.with_name(
            f"{prompt_path.stem}-styled{prompt_path.suffix}"
        )
        output_path.write_text(styled_prompt, encoding="utf-8")
        print(f"✓ 已注入 → {output_path}")
        return

    # manifest 批量模式
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"✗ manifest 不存在: {manifest_path}")
        sys.exit(1)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"✗ manifest JSON 解析失败: {e}")
        sys.exit(1)

    items = manifest.get("items", [])
    if not items:
        print("✗ manifest.items 为空")
        sys.exit(1)

    use_edit = args.style in EDIT_MODE_STYLES
    is_conditional = args.style in CONDITIONAL_EDIT_STYLES
    for item in items:
        if "prompt" not in item:
            print(f"  ⚠ 跳过(无 prompt): {item.get('id', '?')}")
            continue
        clean_body = strip_known_style_prefix(item["prompt"], known_prefixes)
        item["prompt"] = compose_prompt(clean_body, style_prefix)
        if use_edit:
            item["images"] = [CARTOON_REFERENCE_IMAGE]
        elif is_conditional and item.get("needs_character"):
            item["images"] = [CARTOON_REFERENCE_IMAGE]
            item["mode"] = "edit"

    if use_edit:
        manifest["mode"] = "edit"
        print(f"✓ {args.style} 模式: 已切换为 edit + 参考图")
    elif is_conditional:
        # 混合模式: needs_character 的 item 走 edit, 其他走 generation
        manifest["mode"] = "mixed"
        edit_count = sum(1 for it in items if it.get("mode") == "edit")
        print(f"✓ {args.style} 模式: 混合模式({edit_count} 张含卡通人物走 edit, 其余走 generation)")

    output_path = Path(args.output) if args.output else manifest_path.with_name(
        f"{manifest_path.stem}-styled{manifest_path.suffix}"
    )
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✓ 已注入 {len(items)} 项 → {output_path}")


if __name__ == "__main__":
    main()
