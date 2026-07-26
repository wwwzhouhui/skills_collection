#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 storyboard.json + audio/durations.json 生成 index.html 骨架。

用法:
    python3 scaffold_video.py <project_dir> [--force]

前置: 项目目录里已有 storyboard.json, 且已跑过 minimax_tts.py (有 audio/durations.json)。

生成的骨架已填好 (不需要再手抄任何数字):
    - 配色 (按 storyboard.palette 从 9 套主题里选, CSS 其余部分取自 assets/video-template)
    - 章节角标 / 根 data-duration / 7 个 audio 标签 / SEGMENTS 数组 / 字幕 / 转场引擎
    - 7 个场景外壳: chip + ghost + storyboard.visual 描述 (HTML 注释)
    - scene1 / scene7 的标准入场编排 (结构固定); scene2-6 留桩

AI 只需要做两件事:
    1. 填 s2-s6 的 diagram-zone (SVG, 见 references/svg-parts.md) 和 info-card 内容
    2. 写 scene2()-scene6() 的入场编排 (规则见 references/video-authoring.md)
"""

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_ROOT / "assets" / "video-template" / "index.html"

# 9 套主题配色 (v2: 中性色色温与主色相反)。sound/electricity 已渲染验证。
PALETTES = {
    "sound": {
        "primary": "#E8631C", "accent": "#F4A24C", "highlight": "#FFD166",
        "ink": "#22303C", "neutral": "#5E7183", "soft": "#FFFDF6",
        "line": "#9DAEBB", "bg": "#FFF6E5", "series": "#5E7183",
    },
    "light": {
        "primary": "#E89B00", "accent": "#5B9BD5", "highlight": "#FFE680",
        "ink": "#21313F", "neutral": "#5A7284", "soft": "#FFFDF6",
        "line": "#9FB4C2", "bg": "#FFFCF0", "series": "#5A7284",
    },
    "mechanics": {
        "primary": "#D63B26", "accent": "#F08A24", "highlight": "#FFD166",
        "ink": "#26303A", "neutral": "#64748B", "soft": "#FFFDF8",
        "line": "#A3AEBB", "bg": "#FBF5EB", "series": "#64748B",
    },
    "electricity": {
        "primary": "#0D3B66", "accent": "#F4A300", "highlight": "#FFD166",
        "ink": "#26221C", "neutral": "#8A7D6B", "soft": "#FDFDFB",
        "line": "#BCB2A2", "bg": "#FAFCFF", "series": "#8A7D6B",
    },
    "heat": {
        "primary": "#E25822", "accent": "#88B8D8", "highlight": "#FFD166",
        "ink": "#223240", "neutral": "#5E7488", "soft": "#FFFDF8",
        "line": "#9DB0BE", "bg": "#FFF8F0", "series": "#5E7488",
    },
    "biology": {
        "primary": "#2F9E77", "accent": "#E9B44C", "highlight": "#FFE08A",
        "ink": "#232A22", "neutral": "#857A6A", "soft": "#FCFDF9",
        "line": "#B5AB9B", "bg": "#FAFCF5", "series": "#857A6A",
    },
    "chemistry": {
        "primary": "#0B6F75", "accent": "#B84A32", "highlight": "#F2C14E",
        "ink": "#243036", "neutral": "#756C62", "soft": "#FBFDFC",
        "line": "#B7ADA2", "bg": "#F4FAF8", "series": "#756C62",
    },
    "history": {
        "primary": "#7A2E3A", "accent": "#9A641F", "highlight": "#E8D4A2",
        "ink": "#2F3038", "neutral": "#667085", "soft": "#FFFDF8",
        "line": "#AEB7C2", "bg": "#F8F3EA", "series": "#667085",
    },
    # math 走莫兰迪低饱和变体 (米白暖底 + 雾紫 + 灰灰蓝中性 + 焦糖点缀), 已渲染验证。
    # 低饱和只给数学/人文向主题; 物理类 (sound/electricity/...) 保持高饱和强调, 波形/电流需要能量感。
    "math": {
        "primary": "#7A6296", "accent": "#B98A5C", "highlight": "#D8D1E6",
        "ink": "#433D50", "neutral": "#6B7889", "soft": "#FCFAF6",
        "line": "#B9C2CE", "bg": "#F7F3ED", "series": "#6B7889",
    },
}


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def extract(src, start, end):
    """取 src 中 start 与 end 之间的文本 (含 start, 不含 end)。"""
    i = src.index(start)
    return src[i:src.index(end, i)]


# 输出模式变量声明 (放 <html> 上): video=带配音字幕完整版 / silent=无声循环紧凑版
COMPOSITION_VARS = ('''data-composition-variables='['''
                    '''{"id":"mode","type":"enum","label":"输出模式","default":"video","options":['''
                    '''{"value":"video","label":"视频(带配音字幕)"},'''
                    '''{"value":"silent","label":"无声MP4(循环)"}]}]' ''')


def build_root_css(palette):
    lines = "\n".join(f"      --{k}:   {v};" for k, v in palette.items())
    return ":root {\n" + lines + "\n    }"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", help="项目目录 (含 storyboard.json + audio/durations.json)")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 index.html")
    args = ap.parse_args()

    proj = Path(args.project)
    sb_path = proj / "storyboard.json"
    dur_path = proj / "audio" / "durations.json"
    out_path = proj / "index.html"
    for p in (sb_path, dur_path, TEMPLATE):
        if not p.exists():
            die(f"找不到 {p}" + ("" if p != dur_path else " — 先跑 minimax_tts.py"))
    if out_path.exists() and not args.force:
        die(f"{out_path} 已存在, 覆盖用 --force (会丢掉已写的场景内容!)")

    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    dur = json.loads(dur_path.read_text(encoding="utf-8"))
    segs_sb = {s["id"]: s for s in sb["segments"]}
    segs = dur["segments"]
    if len(segs) != 7:
        die(f"期望 7 段, durations.json 里有 {len(segs)} 段")

    palette_name = sb.get("palette", "sound")
    if palette_name not in PALETTES:
        die(f"未知 palette '{palette_name}', 可选: {', '.join(PALETTES)}")
    palette = PALETTES[palette_name]

    tpl = TEMPLATE.read_text(encoding="utf-8")

    # ---- CSS: 取模板整个 <style> 块, 换掉 :root 配色 ----
    style = extract(tpl, "<style>", "</style>") + "</style>"
    style = re.sub(r":root \{.*?\}", build_root_css(palette), style, count=1, flags=re.S)

    # ---- JS: 从模板切 helper 块和通用引擎块 (单一来源, 避免脚手架与模板漂移) ----
    helpers = extract(tpl, "    /* ==== 波形生成",
                      "    /* ================================================================").rstrip()
    engine = extract(tpl, "    /* ================================================================\n       以下为通用引擎",
                     '    window.__timelines["main"] = tl;').rstrip()

    topic = sb.get("topic", "主题")
    chapter = sb.get("chapter", "学科·章节")
    pills = "".join(f'<span class="pill">{segs_sb[i]["title"]}</span>'
                    for i in range(2, 7) if i in segs_sb)

    # ---- 场景外壳 ----
    def bounds(i):
        end = segs[i + 1]["start"] if i + 1 < len(segs) else dur["total"]
        return f"{segs[i]['start']:.2f} - {end:.2f}"

    scenes = []
    for i, seg in enumerate(segs, start=1):
        sbseg = segs_sb.get(seg["id"], {})
        visual = sbseg.get("visual", "")
        title = seg.get("title", f"场景{i}")
        head = (f'    <!-- ============ 场景 {i}: {title} ({bounds(i - 1)}) ============\n'
                f'         visual: {visual} -->\n')
        if i == 1:
            body = f'''    <div id="s1" class="scene">
      <div class="scene-content" style="flex-direction: column; justify-content: center; gap: 40px;">
        <div id="s1-icon" style="height: 190px;">
          <svg viewBox="0 0 420 210" style="height: 190px; overflow: visible;">
            <!-- TODO: 主题图标 (见 references/svg-parts.md) -->
          </svg>
        </div>
        <div id="s1-title" class="t-hero">{topic}</div>
        <div id="s1-subs" style="display: flex; gap: 22px;">{pills}</div>
        <div id="s1-tagline" class="t-label">—— TODO: 副标题 ——</div>
      </div>
    </div>'''
        elif i == 7:
            body = f'''    <div id="s7" class="scene">
      <div class="ghost" data-layout-ignore>06</div>
      <div class="section-chip"><span class="num">{i - 1}</span><span class="label">{title}</span></div>
      <div class="scene-content" style="flex-direction: column; justify-content: center; gap: 30px;">
        <div id="s7-number" class="t-hero" style="font-size: 150px;"><span id="s7-number-inner" style="display: inline-block;">TODO 大数字/公式</span></div>
        <div id="s7-note" class="t-label" style="font-size: 30px;">TODO 注释</div>
        <div class="info-card" id="s7-card" style="width: 1060px; flex: none;">
          <div class="card-title">本章小结</div>
          <div class="card-body">
            <p>TODO 要点一</p>
            <p>TODO 要点二</p>
            <p>TODO 要点三</p>
          </div>
        </div>
        <div class="summary-bar" id="s7-bar">
          <div class="badge"><div class="icon">?</div><div class="name">TODO</div></div>
          <div class="badge"><div class="icon">?</div><div class="name">TODO</div></div>
          <div class="badge"><div class="icon">?</div><div class="name">TODO</div></div>
          <div class="badge"><div class="icon">?</div><div class="name">TODO</div></div>
        </div>
      </div>
    </div>'''
        else:
            body = f'''    <div id="s{i}" class="scene">
      <div class="ghost" data-layout-ignore>{i - 1:02d}</div>
      <div class="section-chip"><span class="num">{i - 1}</span><span class="label">{title}</span></div>
      <div class="scene-content">
        <div class="diagram-zone" id="s{i}-diagram">
          <svg viewBox="0 0 900 700">
            <!-- TODO: 按上方 visual 描述画示意图 (零件见 references/svg-parts.md),
                 至少 1 条 callout; 对比双栏改 viewBox="0 0 940 700" -->
          </svg>
        </div>
        <div class="card-zone">
          <div class="info-card" id="s{i}-card">
            <div class="card-title">{title}</div>
            <div class="card-body">
              <p>TODO 要点一</p>
              <p>TODO 要点二</p>
            </div>
          </div>
        </div>
      </div>
    </div>'''
        scenes.append(head + body)

    # ---- 音频标签 ----
    audio = "\n".join(
        f'    <audio id="a{s["id"]}" src="{s["file"]}" data-start="{s["audio_start"]}" '
        f'data-duration="{s["audio_duration"]}" data-track-index="2"></audio>'
        for s in segs)

    # ---- SEGMENTS 数组 ----
    seg_lines = []
    for i, s in enumerate(segs, start=1):
        trans = segs_sb.get(s["id"], {}).get("transition", "blur-crossfade")
        seg_lines.append(
            f'      {{ sel: "#s{i}", start: {s["start"]}, duration: {s["duration"]}, '
            f'transition: "{trans}",\n        subtitle: {json.dumps(s["subtitle"], ensure_ascii=False)} }},')
    segments_js = (
        '// 输出模式: video(带配音字幕) / silent(无声循环紧凑)\n'
        '    const MODE = (window.__hyperframes && window.__hyperframes.getVariables\n'
        '      ? window.__hyperframes.getVariables().mode : null) || "video";\n'
        '    const SILENT_SEG = 4.6;   // 无声模式每段时长 (无旁白, 只需看清画面+动效)\n\n'
        '    const SEGMENTS_VIDEO = [\n' + "\n".join(seg_lines) + "\n    ];\n\n"
        '    // 无声模式: 每段等长紧凑重排; 视频模式沿用音频驱动时间轴\n'
        '    let _acc = 0;\n'
        '    const SEGMENTS = MODE === "silent"\n'
        '      ? SEGMENTS_VIDEO.map((s) => { const o = { ...s, start: _acc, duration: SILENT_SEG }; _acc += SILENT_SEG; return o; })\n'
        '      : SEGMENTS_VIDEO;'
    )

    # ---- 场景编排桩 (s1/s7 标准编排预填, s2-6 留桩) ----
    builders = ['''    function scene1(t) {
      tl.fromTo("#s1-title", { y: 70, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.8, ease: "power3.out" }, t + 0.2);
      tl.fromTo("#s1-icon", { scale: 0.6, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.7, ease: "back.out(1.5)" }, t + 0.7);
      tl.fromTo("#s1-subs .pill", { y: 34, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.45, ease: "power2.out", stagger: 0.09 }, t + 1.2);
      tl.fromTo("#s1-tagline", { opacity: 0 },
        { opacity: 1, duration: 0.6, ease: "sine.out" }, t + 1.9);
    }''']
    for i in range(2, 7):
        builders.append(f'''    function scene{i}(t) {{
      // TODO: 编排 (fromTo, ≥3 种 ease, ≥2 个方向; 示意图先画→callout→卡片; 持续动效挂 tl)
      // 参考: drawIn("#s{i}-diagram path", t + 0.3, 0.8);
      tl.fromTo("#s{i}-card", {{ x: 90, opacity: 0 }},
        {{ x: 0, opacity: 1, duration: 0.7, ease: "power3.out" }}, t + 3.0);
    }}''')
    builders.append('''    function scene7(t) {
      tl.fromTo("#s7-number", { scale: 0.4, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.8, ease: "back.out(1.6)" }, t + 0.3);
      tl.fromTo("#s7-note", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "sine.out" }, t + 1.0);
      tl.fromTo("#s7-card", { y: 90, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.7, ease: "power3.out" }, t + 1.6);
      tl.fromTo("#s7-bar .badge", { y: 44, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.5, ease: "power2.out", stagger: 0.12 }, t + 2.4);
      tl.to("#s7-number-inner", { scale: 1.03, transformOrigin: "50% 50%", yoyo: true, repeat: 7, duration: 0.8, ease: "sine.inOut" }, t + 1.4);
      // 收尾淡出 (仅视频模式; 无声循环不淡出, 保证首尾衔接)
      if (MODE !== "silent") {
        const end = t + SEGMENTS[6].duration;
        tl.to("#s7 .scene-content, #s7 .section-chip, #chapter", { opacity: 0, duration: 0.6, ease: "power1.in" }, end - 0.7);
      }
    }''')
    builders_js = "\n".join(builders)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN" {COMPOSITION_VARS}>
<!--
  {topic} · 教学视频 (由 scaffold_video.py 生成, 模板: assets/video-template/index.html)
  时间轴已按 audio/durations.json 填好 — 只需填 TODO 的场景内容和 scene2()-scene6() 编排
  规则: references/video-authoring.md | SVG 零件: references/svg-parts.md
  渲染: bash scripts/build_video.sh <project_dir>
-->
<head>
  <meta charset="UTF-8" />
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  {style}
</head>
<body>
  <div id="root" data-composition-id="main" data-width="1920" data-height="1080"
       data-start="0" data-duration="{dur["total"]}">

{chr(10).join(scenes)}

    <!-- ============ 常驻层 ============ -->
    <div id="chapter">{chapter}</div>
    <div id="subtitle-layer"></div>

    <!-- ============ 旁白音频 ============ -->
{audio}
  </div>

  <script>
    window.__timelines = window.__timelines || {{}};
    const tl = gsap.timeline({{ paused: true }});

    /* ==== 时间轴 (由 scaffold 从 durations.json 生成) ==== */
    {segments_js}

{helpers}

    /* ==== 每场景入场编排 ==== */
{builders_js}
    const SCENE_BUILDERS = [scene1, scene2, scene3, scene4, scene5, scene6, scene7];

{engine}
    window.__timelines["main"] = tl;
  </script>
</body>
</html>
'''
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 骨架 → {out_path}  (palette={palette_name}, total={dur['total']}s)")
    print("   下一步: 填 7 处 TODO (场景内容) + scene2()-scene6() 编排, 然后 lint / build_video.sh")


if __name__ == "__main__":
    main()
