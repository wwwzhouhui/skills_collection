# 风格: 专业扁平信息图 (infographic)

**适用场景**: 商业演示、对比分析、架构概览、品牌内容。传达"专业、系统、有深度"的感觉。

## 风格基因(每个提示词开头必须包含)

```
Style: Professional clean flat vector-style digital infographic.
Background: very light warm off-white cream color (#FFF8F0).
Minimalist, symmetrical, and structured layout.

Color palette:
- Primary accent (headers/titles): dark maroon (#6B2C2C)
- Left side theme: blue and indigo tones (#3B5998, #5B7FC9)
- Right side theme: orange and terracotta tones (#D2691E, #E07B3C)
- Supporting elements: light grey (#E8E8E8) for cards/panels
- Text: dark charcoal (#333333) for body

Typography:
- Professional sans-serif font
- Clear text hierarchy (bold titles -> medium headers -> small body)
- All major text in Chinese; minimize English to established technical terms only (e.g. API, Agent)
- Avoid mixing Chinese and English in the same label — this causes garbled Chinese rendering

Visual elements:
- Clean rounded-corner panels with light fills for sub-sections
- Minimalist lines for clear flow paths
- Geometric icons (no hand-drawn feel)
- No gradient fills, no shadows, no 3D rendering
- Ample white space, balanced composition
```

## 版式规范

### 对比类图 (A vs B)

```
Header: Bold two-line central title in dark maroon.
  Line 1: "{{主标题}}"
  Line 2: "{{副标题/核心洞察}}"

Main body: Precise side-by-side vertical split.
  Left section ({{A 名}}): blue/indigo tones
  Right section ({{B 名}}): orange/terracotta tones

Bottom cards:
  Two light grey rounded-corner panels side-by-side.
  Each card: icon + Chinese/English text summary
```

### 流程/循环类图

```
Header: Bold central title in dark maroon.

Main flow: Clean directional layout with rounded geometric nodes.
  Use blue arrows for sequential/process flow
  Use orange arrows for feedback/iteration loops

Center elements: Geometric icons (circles, rectangles with rounded corners)
Background: Cream with subtle grid lines (optional)
```

### 架构/分层类图

```
Header: Bold title in dark maroon.

Layered structure: Clear horizontal bands.
  Each layer: rounded-corner rectangle with light fill
  Layer labels: centered, bold Chinese text
  Connecting arrows: blue for top-down flow

Bottom summary: Single line in grey, centered
```

## 禁忌

- No hand-drawn elements
- No photographs
- No 3D rendering
- No heavy shadows or gradients
- Avoid clutter — every element must have purpose
