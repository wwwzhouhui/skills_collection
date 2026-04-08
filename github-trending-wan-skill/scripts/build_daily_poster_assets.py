#!/usr/bin/env python3
"""Build low-density Chinese brief and Wan prompt from GitHub trending Top 5 data."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import datetime
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
        "elements": "古灵精怪几何图标、复古漫画表情(😊✓ 😐 ☹️✗)、棋盘格/斜线纹理",
        "typography": "标题复古粗体、正文清晰无衬线中文、装饰性英文标签 WARNING/INFO",
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
}
DEFAULT_STYLE = "10"
DEFAULT_AUDIENCE = "开发者 / 技术团队"
DEFAULT_RATIO = "3:4"
DEFAULT_SIZE = "2K"
TREND_KEYWORD_GROUPS = {
    "AI / Agent": ["agent", "ai", "llm", "model", "rag", "智能体", "大模型", "推理", "生成式"],
    "开发工具": ["developer", "tool", "cli", "sdk", "framework", "editor", "开发工具", "编码", "工作流"],
    "基础设施": ["kubernetes", "docker", "infra", "cloud", "deploy", "server", "容器", "部署", "网关", "集群"],
    "数据 / 数据库": ["data", "database", "sql", "analytics", "vector", "pipeline", "数据库", "数据", "向量", "分析"],
    "前端 / Web": ["frontend", "ui", "component", "browser", "web", "javascript", "typescript", "前端", "浏览器", "组件"],
}


def read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)



def ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)



def short_text(text: str, limit: int = 120) -> str:
    if not text:
        return "暂无信息"
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1].rstrip()}…"



def join_list(values: list[str], fallback: str = "暂无信息", limit: int = 4) -> str:
    cleaned = [" ".join(str(value).split()) for value in values if str(value).strip()]
    if not cleaned:
        return fallback
    return "、".join(cleaned[:limit])



def clean_stack_items(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        normalized = " ".join(str(value).split())
        if not normalized or len(normalized) > 60:
            continue
        if normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned[:5]



def collect_trend_labels(items: list[dict[str, Any]]) -> list[str]:
    scores: Counter[str] = Counter()
    for item in items:
        haystack = " ".join(
            [
                item.get("description", ""),
                item.get("summary_intro", ""),
                " ".join(item.get("topics") or []),
                " ".join(item.get("tech_stack") or []),
            ]
        ).lower()
        for label, keywords in TREND_KEYWORD_GROUPS.items():
            if any(keyword.lower() in haystack for keyword in keywords):
                scores[label] += 1
    if not scores:
        return ["开发工具", "开源基础设施", "AI / Agent"]
    return [label for label, _ in scores.most_common(3)]



def build_overview(items: list[dict[str, Any]], generated_date: str, audience: str) -> str:
    languages = Counter(item.get("language") or "Unknown" for item in items).most_common(3)
    language_text = "、".join(f"{language}×{count}" for language, count in languages) or "Unknown"
    trend_text = "、".join(collect_trend_labels(items))
    return (
        f"日期：{generated_date}；榜单范围：GitHub Trending Top {len(items)}；"
        f"主要语言：{language_text}；热点方向：{trend_text}；目标读者：{audience}"
    )



def build_project_card(item: dict[str, Any]) -> str:
    description = short_text(item.get("description", ""), 72)
    problem = short_text(item.get("summary_intro") or item.get("description", ""), 88)
    stack = join_list(clean_stack_items(item.get("tech_stack") or []), fallback=item.get("language") or "暂无信息")
    stars = item.get("stargazers_count") or 0
    return "\n".join(
        [
            f"{item.get('rank')}. {item.get('name')}",
            f"项目是什么：{description}",
            f"解决什么问题：{problem}",
            f"技术栈：{stack}",
            f"Star 数量：{stars}",
        ]
    )



def build_project_cards(items: list[dict[str, Any]]) -> list[str]:
    return [build_project_card(item) for item in items[:5]]



def build_hotspots(items: list[dict[str, Any]]) -> list[str]:
    labels = collect_trend_labels(items)
    bullets: list[str] = []
    for label in labels:
        matched = []
        for item in items:
            haystack = " ".join(
                [
                    item.get("description", ""),
                    item.get("summary_intro", ""),
                    " ".join(item.get("topics") or []),
                    " ".join(item.get("tech_stack") or []),
                ]
            ).lower()
            if any(keyword.lower() in haystack for keyword in TREND_KEYWORD_GROUPS[label]):
                matched.append(item)
        if not matched:
            matched = items[:2]
        bullets.append(f"{label}：代表项目 {join_list([item['name'] for item in matched], limit=2)}")
    return bullets[:3]



def build_takeaway(items: list[dict[str, Any]]) -> str:
    trend_text = "、".join(collect_trend_labels(items))
    languages = Counter(item.get("language") or "Unknown" for item in items).most_common(2)
    language_text = "、".join(language for language, _ in languages) or "多语言"
    return f"今天榜单重点集中在 {trend_text}，主流语言偏向 {language_text}，适合优先关注能直接提升开发效率或 AI 应用落地的项目。"



def build_prompt_cards(items: list[dict[str, Any]]) -> str:
    lines = []
    for item in items[:5]:
        lines.append(
            "｜".join(
                [
                    f"Top {item.get('rank')}",
                    str(item.get("name") or "Unknown"),
                    f"是什么：{short_text(item.get('description', ''), 42)}",
                    f"解决：{short_text(item.get('summary_intro') or item.get('description', ''), 54)}",
                    f"技术栈：{join_list(clean_stack_items(item.get('tech_stack') or []), fallback=item.get('language') or '暂无信息', limit=3)}",
                    f"⭐ {item.get('stargazers_count') or 0}",
                ]
            )
        )
    return "\n".join(lines)



def build_markdown(data: dict[str, Any], audience: str, style_key: str, size: str) -> str:
    items = data.get("items") or []
    generated_date = data.get("generated_date") or datetime.now().strftime("%Y-%m-%d")
    style = STYLE_MAP.get(style_key, STYLE_MAP[DEFAULT_STYLE])
    overview = build_overview(items, generated_date, audience)
    hotspots = build_hotspots(items)
    takeaway = build_takeaway(items)
    translation_model = data.get("translation_model") or "未记录"

    sections: list[str] = [
        "# GitHub 今日热门开源 Top 5 简报\n",
        "## 步骤1：启动确认\n",
        f"- 日期：{generated_date}",
        f"- 目标读者：{audience}",
        f"- 海报风格：{style['emoji']} {style['name']}（{style['scene']}）",
        f"- 输出分辨率：{size}",
        f"- 中文翻译模型：{translation_model}",
        "- 当前模式：先生成内容与 Prompt，待确认后再生图\n",
        "## 步骤2：内容整理\n",
        "### 模块1【榜单概览】",
        f"- {overview}\n",
        "### 模块2【Top 5 项目卡片】",
    ]

    for card in build_project_cards(items):
        sections.append(card)
        sections.append("")

    sections.extend(
        [
            "### 模块3【热点方向】",
            *(f"- {line}" for line in hotspots),
            "",
            "### 模块4【一句话结论】",
            f"- {takeaway}\n",
            "## 步骤3：确认后生图\n",
            "- 检查 `wan_prompt.txt` 是否保持中文优先、信息适中、版面不拥挤",
            '- 用户回复"确认生图"后，调用 Wan 2.7 生成单张 3:4 信息图海报',
            "- 若返回 task_id，则继续查询任务状态直到出图\n",
        ]
    )
    return "\n".join(sections).strip() + "\n"



def build_prompt(data: dict[str, Any], audience: str, style_key: str, size: str, ratio: str) -> str:
    items = data.get("items") or []
    generated_date = data.get("generated_date") or datetime.now().strftime("%Y-%m-%d")
    style = STYLE_MAP.get(style_key, STYLE_MAP[DEFAULT_STYLE])
    overview = build_overview(items, generated_date, audience)
    hotspots = " | ".join(build_hotspots(items))
    cards = build_prompt_cards(items)
    takeaway = build_takeaway(items)

    layout_extras = "\n".join(f"- {line}" for line in style["layout_extras"])

    return f"""请生成一张中文优先的 GitHub 今日热门开源信息图海报，面向 {audience}。

=== 视觉目标 ===
- 风格：{style['name']}（{style['aesthetic']}）
- 氛围：{style['mood']}
- 配色：{style['palette']}
- 视觉元素：{style['elements']}
- 排版：{style['typography']}
{layout_extras}
- 整体要求：信息适中、可读性优先、结构清楚，不要做成高密度塞满版面的海报

=== 版式要求 ===
- 画幅比例：{ratio}
- 分辨率目标：{size}
- 使用 4 个主模块：标题区、榜单概览、Top 5 项目卡片区、底部总结区
- 每个项目卡片只保留 5 个信息点：项目名、项目是什么、解决什么问题、技术栈、Star 数量
- 中文为主，英文仅保留 repo 名、编程语言名、框架名、协议名、产品名等必要术语

=== 禁止事项 ===
- 不要 7 模块高密度排版
- 不要大段英文说明
- 不要空泛文案或营销口号
- 不要过多装饰图形影响阅读
- 不要把表格、标签、数字堆满整页
- 不要：{style['avoid']}

=== 画面文案 ===
主标题：GitHub 今日热门开源 Top 5
副标题：{generated_date}｜中文摘要｜可读性优先
模块1【榜单概览】：{overview}
模块2【Top 5 项目卡片】：
{cards}
模块3【热点方向】：{hotspots}
模块4【一句话结论】：{takeaway}

=== 细节要求 ===
- Top 5 卡片按排名自上而下或左右排布，层级明确
- Star 数字要清晰可见，但不是最大视觉主体
- 用少量标签或色块区分语言 / 技术方向即可
- 允许使用简洁图标、分隔线、数据卡片，但不要抢文字信息
""".strip() + "\n"



def save_text(path: str, content: str) -> None:
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build low-density Chinese markdown brief and Wan prompt assets")
    parser.add_argument("--input", default="output/daily_top5_zh.json", help="Input JSON path")
    parser.add_argument("--brief-output", default="output/daily_brief.md", help="Output markdown brief path")
    parser.add_argument("--prompt-output", default="output/wan_prompt.txt", help="Output Wan prompt path")
    parser.add_argument("--audience", default=DEFAULT_AUDIENCE, help="Target audience")
    parser.add_argument("--style", default=DEFAULT_STYLE, help="Style key, e.g. 1 or 10")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Requested generation size, e.g. 2K")
    parser.add_argument("--ratio", default=DEFAULT_RATIO, help="Poster aspect ratio")
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    data = read_json(args.input)
    markdown = build_markdown(data, args.audience, args.style, args.size)
    prompt = build_prompt(data, args.audience, args.style, args.size, args.ratio)
    save_text(args.brief_output, markdown)
    save_text(args.prompt_output, prompt)
    print(f"已保存: {args.brief_output}")
    print(f"已保存: {args.prompt_output}")


if __name__ == "__main__":
    main()
