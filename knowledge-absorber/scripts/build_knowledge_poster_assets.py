#!/usr/bin/env python3
"""Build knowledge poster prompt for Wan 2.7 from knowledge card markdown."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

STYLE_MAP = {
    "1": {
        "name": "坐标蓝图",
        "emoji": "🧪",
        "scene": "技术参数、专业评测",
        "aesthetic": "Laboratory manual + Blueprint coordinate system",
        "mood": "Precision, Technical, Data-driven",
        "palette": "灰白网格底(#F2F2F2)、柔和青绿(#B8D8BE)、荧光粉(#E91E63)、柠檬黄(#FFF200)、碳棕线条(#2D2926)",
        "layout_extras": [
            "坐标标签装饰每个模块（R-20, G-02, SEC-08）",
            "技术标尺标记（0.5mm, 1.8mm, 45°）",
        ],
        "elements": "数据卡片、截面图、数学符号(Σ, Δ)、十字准星、X/Y 坐标轴箭头",
        "typography": "标题粗犷中文、正文技术无衬线、数字大号高亮",
        "avoid": "涂鸦、柔和色系、通用图标",
    },
    "2": {
        "name": "复古波普",
        "emoji": "📐",
        "scene": "干货清单、对比表格",
        "aesthetic": "1970s Retro Pop Art + Swiss Grid System",
        "mood": "Orderly, Bold, Graphic",
        "palette": "复古奶油底(#F5F0E6)、三文鱼粉、天蓝、芥末黄、薄荷绿、纯黑粗轮廓",
        "layout_extras": [
            "严格瑞士网格：方形/矩形单元格",
            "粗黑线分隔模块",
        ],
        "elements": "古灵精怪几何图标、复古漫画表情、棋盘格/斜线纹理",
        "typography": "标题复古粗体、正文清晰无衬线中文、装饰性英文标签",
        "avoid": "3D 效果、渐变、细线条、浮动布局",
    },
    "3": {
        "name": "文件夹",
        "emoji": "📁",
        "scene": "系统指南、分类清单",
        "aesthetic": "Neo-skeuomorphism + File folder organization",
        "mood": "Clean, Professional, Organized",
        "palette": "奶油米色底(#F5F5DC)、克莱因蓝主色、活力橙点缀、柔灰+深黑文字",
        "layout_extras": [
            "竖版剪贴板构图",
            "层叠文件夹 + 索引标签",
        ],
        "elements": "3D 金属夹子、层叠文件夹标签、索引导航标签、3D 鼠标光标、微妙阴影增加层次",
        "typography": "标题大号粗体无衬线、正文整洁列表、标签紧凑大写",
        "avoid": "扁平无层次、花哨装饰",
    },
    "4": {
        "name": "热敏纸",
        "emoji": "🧾",
        "scene": "步骤清单、时间线",
        "aesthetic": "Modern ticket/receipt + Perforated edges",
        "mood": "Sequential, Functional, Tactile",
        "palette": "亮青(#00AEEF)或芥末黄(#FFD100)边框、米白纸张底(#F9F9F9)、深炭文字",
        "layout_extras": [
            "竖版收据流式布局",
            "穿孔边缘细节 + 3D 出票机头部",
        ],
        "elements": "3D/黏土风图标、手绘复选框 ✓、荧光笔圈关键词、像素字体页眉",
        "typography": "头部复古数码/像素字体、标题粗体现代无衬线、正文轻量无衬线",
        "avoid": "无边框、过于正式",
    },
    "5": {
        "name": "复古手帐",
        "emoji": "📓",
        "scene": "案例研究、调查分析",
        "aesthetic": "Mixed-media archival + Evidence board",
        "mood": "Investigative, Layered, Analog",
        "palette": "奶油色、牛皮纸棕、米白底、深黑+海军蓝字体、亮绿+红色点缀、柔黄胶带",
        "layout_extras": [
            "拼贴构图，元素可重叠",
            "图钉固定效果、边注批注",
        ],
        "elements": "撕纸边缘、半调网点、回形针/图钉/胶带、宝丽来相框、手绘箭头和虚线",
        "typography": "标题粗体无衬线、数据打字机等宽、笔记手写风格",
        "avoid": "过于整齐、数字感太强",
    },
    "6": {
        "name": "陶土手绘",
        "emoji": "✏️",
        "scene": "轻松干货、亲和科普",
        "aesthetic": "Organic hand-drawn + Imperfect lines",
        "mood": "Friendly, Approachable, Playful",
        "palette": "陶土橙/铁锈色为主、炭黑(#2D2926)对比、米白/奶油底、浅蓝+柔粉圆点",
        "layout_extras": [
            "手绘模块分隔线",
            "不规则有机形状色块",
        ],
        "elements": "几何形状(圆/三角/星)、波浪装饰线、简笔手势图标、圆点纹理、有意不完美的线条",
        "typography": "标题友好圆润无衬线、正文清晰可读、强调部分手写感",
        "avoid": "直线条、渐变、3D、冷色调",
    },
    "7": {
        "name": "酸性复古",
        "emoji": "💾",
        "scene": "数码评测、极客内容",
        "aesthetic": "Y2K Tech-Nostalgia + Acid Graphics",
        "mood": "Edgy, Digital, Cyber",
        "palette": "深炭底(#1A1A1A)带颗粒、赛博黄/电光橙/霓虹绿、银色/铬金属、彩虹渐变",
        "layout_extras": [
            "非对称模块化网格",
            "重叠层次 + 贴纸风标签",
        ],
        "elements": "复古科技(老Mac、CD-ROM、软盘)、像素图标、全息渐变、贴纸边框、重颗粒纹理",
        "typography": "标题粗重无衬线、数据等宽/终端字体、标签贴纸风格",
        "avoid": "柔和色调、极简风、传统排版",
    },
    "8": {
        "name": "剧场票据",
        "emoji": "🎫",
        "scene": "故事演进、系列指南",
        "aesthetic": "Vintage tickets + Film noir collage",
        "mood": "Dramatic, Sequential, Cinematic",
        "palette": "深海军蓝或深炭底(带颗粒)、青色/金丝雀黄/珊瑚粉/薄荷绿票据、银色金属夹",
        "layout_extras": [
            "重叠票据堆叠效果",
            "锯齿票根边缘 + 胶片边框",
        ],
        "elements": "复古剧场门票、金属回形针、胶片齿孔、剧本/演员表页面、颗粒胶片纹理",
        "typography": "标题粗衬线体、正文等宽打字机体、标签全大写块状",
        "avoid": "明亮背景、卡通风格",
    },
    "9": {
        "name": "矢量插图",
        "emoji": "🖼️",
        "scene": "PPT 封面、场景插画",
        "aesthetic": "Flat monoline vector + Geometric simplification",
        "mood": "Clean, Friendly, Educational",
        "palette": "奶油/米白纸张纹理底、珊瑚红/薄荷绿/芥末黄/焦橙/岩石蓝",
        "layout_extras": [
            "全景水平带(顶部 1/3)",
            "2.5D 层叠透视，所有层清晰度一致",
        ],
        "elements": "统一黑色单线描边、圆润线端、封闭轮廓、几何简化(棒棒糖树/矩形建筑/药丸云)",
        "typography": "标题超大粗体复古衬线、副标题彩色色块全大写无衬线、正文清爽现代无衬线",
        "avoid": "复杂渐变、写实风格、尖锐棱角",
    },
    "10": {
        "name": "孟菲斯网格",
        "emoji": "🎨",
        "scene": "高密度信息、艺术指南",
        "aesthetic": "Modern Memphis + Swiss Design Grid foundation",
        "mood": "Experimental, Dynamic, Arts-forward",
        "palette": "浅灰网格底(#E5E5E5)、黑色对比块、洋红(#E91E8C)标题、深森绿/青(#00695C)副标题、亮青(#4DD0E1)几何块、紫罗兰(#7E57C2)圆形、赭黄(#FFCA28)双圆、暖棕(#8D6E63)日期标签",
        "layout_extras": [
            "可见网格系统作为结构骨架",
            "模块化布局，独立色块编码，错位对齐",
        ],
        "elements": "抽象形状(圆/花生双圆/锯齿线)、交叉阴影线簇、错位文字块、网格叠加、几何装饰(点/线/弧)",
        "typography": "标题清爽现代无衬线(Helvetica Neue 风格)、正文大小/颜色层级、黑色块上白色文字",
        "avoid": "渐变、3D 效果、通用圆润图标、纯白背景、柔和色调",
    },
    "11": {
        "name": "水墨国学",
        "emoji": "☯️",
        "scene": "国学经典、人文哲学",
        "aesthetic": "Chinese ink wash + Traditional scroll painting",
        "mood": "Zen, Contemplative, Scholarly",
        "palette": "宣纸米白底(#FDF8F0)、水墨黑(#1A1A1A)、朱砂红(#B91C1C)印章点缀、黛青(#2C3E50)标题、淡墨灰(#6B7280)正文",
        "layout_extras": [
            "竖版卷轴构图",
            "留白意境，呼吸感强",
        ],
        "elements": "水墨晕染背景、朱红印章装饰、毛笔笔触、山水意境、古典纹样(云纹/水纹)、折扇/书卷元素",
        "typography": "标题书法风格或宋体、正文宋体/思源宋体、引用楷体",
        "avoid": "现代几何图形、饱和色彩、西文字体为主、过于拥挤",
    },
}

DEFAULT_STYLE = "10"
DEFAULT_AUDIENCE = "零基础学习者"
DEFAULT_RATIO = "3:4"
DEFAULT_SIZE = "2K"


def read_markdown(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def extract_title(content: str) -> str:
    """Extract title from markdown (first # heading)."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "知识卡片"


def extract_core_concepts(content: str, limit: int = 5) -> list[str]:
    """Extract core concepts from markdown."""
    concepts = []

    # Look for ## headings as concepts
    for match in re.finditer(r"^##\s+(.+)$", content, re.MULTILINE):
        concept = match.group(1).strip()
        if concept and len(concept) < 50:
            concepts.append(concept)
            if len(concepts) >= limit:
                break

    return concepts[:limit]


def extract_key_points(content: str, limit: int = 6) -> list[str]:
    """Extract key points from markdown (bullet points)."""
    points = []

    # Look for bullet points
    for match in re.finditer(r"^\s*[-*]\s+(.+)$", content, re.MULTILINE):
        point = match.group(1).strip()
        # Clean up markdown formatting
        point = re.sub(r"\*\*([^*]+)\*\*", r"\1", point)
        point = re.sub(r"`([^`]+)`", r"\1", point)
        if point and len(point) < 100:
            points.append(point)
            if len(points) >= limit:
                break

    return points[:limit]


def extract_summary(content: str) -> str:
    """Extract or generate a one-sentence summary."""
    # Try to find a summary section
    summary_match = re.search(r"(?:摘要|总结|Summary)[：:]\s*(.+?)(?:\n|$)", content, re.IGNORECASE)
    if summary_match:
        return summary_match.group(1).strip()[:80]

    # Use first paragraph after title
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            # Get next non-empty paragraph
            for j in range(i + 1, min(i + 10, len(lines))):
                para = lines[j].strip()
                if para and not para.startswith("#"):
                    return para[:80]

    return "掌握核心知识，提升学习效率"


def detect_guoxue_keywords(content: str) -> bool:
    """Detect if content is about Chinese classical studies."""
    keywords = [
        "国学", "古文", "论语", "庄子", "道德经", "史记", "诗经", "易经",
        "孟子", "荀子", "春秋", "左传", "礼记", "周易", "尚书", "大学",
        "中庸", "佛", "儒", "道", "哲学", "人文", "儒家", "道家", "佛家",
        "法家", "墨家", "兵家", "禅宗", "理学", "心学", "玄学",
        "孔子", "老子", "孟子", "庄子", "荀子", "墨子", "韩非子",
        "朱熹", "王阳明", "程颐", "程颢", "古诗", "词", "赋", "骈文",
        "散文", "文言文", "经史子集", "四书五经", "诸子百家", "传统文化",
    ]
    content_lower = content.lower()
    return any(kw.lower() in content_lower for kw in keywords)


def build_prompt(
    content: str,
    title: str,
    audience: str,
    style_key: str,
    size: str,
    ratio: str,
) -> str:
    """Build Wan 2.7 prompt from knowledge card content."""
    style = STYLE_MAP.get(style_key, STYLE_MAP[DEFAULT_STYLE])

    core_concepts = extract_core_concepts(content)
    key_points = extract_key_points(content)
    summary = extract_summary(content)

    concepts_text = " | ".join(core_concepts) if core_concepts else "核心概念"
    points_text = "\n".join(f"- {p}" for p in key_points) if key_points else "- 掌握要点"

    layout_extras = "\n".join(f"- {line}" for line in style["layout_extras"])

    return f"""请生成一张中文优先的知识学习信息图海报，面向 {audience}。

=== 视觉目标 ===
- 风格：{style['name']}（{style['aesthetic']}）
- 氛围：{style['mood']}
- 配色：{style['palette']}
- 视觉元素：{style['elements']}
- 排版：{style['typography']}
{layout_extras}
- 整体要求：信息精炼、可读性优先、结构清楚，不要做成高密度塞满版面的海报

=== 版式要求 ===
- 画幅比例：{ratio}
- 分辨率目标：{size}
- 使用 4 个主模块：标题区、核心概念区、知识要点区、底部总结区
- 中文为主，英文仅保留必要术语
- 标题简洁有力，要点精炼可读

=== 禁止事项 ===
- 不要高密度排版塞满版面
- 不要大段长文字
- 不要空泛文案或营销口号
- 不要过多装饰图形影响阅读
- 不要：{style['avoid']}

=== 画面文案 ===
主标题：{title}
副标题：知识卡片 | 可读性优先
模块1【核心概念】：{concepts_text}
模块2【知识要点】：
{points_text}
模块3【一句话总结】：{summary}

=== 细节要求 ===
- 标题醒目但不夸张
- 要点层级明确，便于阅读
- 用色块或图标区分不同模块
- 留白呼吸感，不要拥挤
""".strip() + "\n"


def save_text(path: str, content: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build knowledge poster prompt for Wan 2.7")
    parser.add_argument("--input", required=True, help="Input knowledge card markdown path")
    parser.add_argument("--prompt-output", default="output/wan_prompt.txt", help="Output Wan prompt path")
    parser.add_argument("--audience", default=DEFAULT_AUDIENCE, help="Target audience")
    parser.add_argument("--style", default="", help="Style key (1-11), auto-detected if not specified")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Requested generation size")
    parser.add_argument("--ratio", default=DEFAULT_RATIO, help="Poster aspect ratio")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    content = read_markdown(args.input)
    title = extract_title(content)

    # Auto-detect style for guoxue content
    style_key = args.style
    if not style_key:
        if detect_guoxue_keywords(content):
            style_key = "11"  # Water ink style
            print(f"检测到国学内容，自动切换为水墨国学风格 (11)")
        else:
            style_key = DEFAULT_STYLE

    prompt = build_prompt(
        content=content,
        title=title,
        audience=args.audience,
        style_key=style_key,
        size=args.size,
        ratio=args.ratio,
    )

    save_text(args.prompt_output, prompt)
    print(f"已保存 Wan Prompt: {args.prompt_output}")
    print(f"标题: {title}")
    print(f"风格: {STYLE_MAP[style_key]['name']}")
    print(f"受众: {args.audience}")
    print(f"Prompt 长度: {len(prompt)} 字符")


if __name__ == "__main__":
    main()