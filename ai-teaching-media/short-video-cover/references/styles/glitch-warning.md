# 故障警示风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

暗色底 + glitch/故障效果 + 红色/橙色警示元素，专门给 Bug 排查、安全提醒、避坑内容用。

### 视觉特征

- 背景：深色，带 glitch 扫描线、色差、噪点等数字故障效果
- 主视觉：红色报错截图 / 警告图标 / 错误代码片段
- 人物：表情可稍严肃或专注，不像其他风格那么轻松
- 标题：白字重描边或红色，突出"警告感"
- 点缀：小 ⚠️ / ❌ / 红色边框

### 固定

- 必须包含至少一个明确的"问题/错误"视觉元素
- 人物：参考图 1 五官，半身
- 水印：@wwwzhouhui

### 变量

- 故障效果强度（轻微 / 中等 / 强烈）
- 警示颜色（红 / 橙 / 玫红）
- 报错元素类型（截图 / 代码 / 图标）
- 标题颜色

### 提示词模板

```
A vertical video thumbnail in 3:4 ratio (1080×1440), Chinese short-video cover in dark glitch / warning aesthetic style, optimized for WeChat Channels / Douyin / Xiaohongshu.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 20%: bold warning-style headline
- Middle 60%: large error/warning UI element + glitch effects
- Bottom 20%: subject portrait + watermark

COLOR PALETTE & BACKGROUND:
- Dark base: black / charcoal / deep red-black
- Glitch effects: RGB chromatic aberration, scan lines, subtle noise, horizontal tearing
- Warning accents: red #FF3B30, orange #FF9500, magenta #FF2D55
- Cyan/blue glitch accents allowed for digital feel
- Overall feel: urgent, digital, slightly unsettling but not horror

WARNING/ERROR ELEMENT (dominant):
{{报错/警示元素描述}}
- Large realistic error screenshot or warning graphic
- Red error banner, ❌ marks, or ⚠️ warning icons
- Glitch distortion around the edges
- Chinese error message clearly readable

GLITCH EFFECTS:
- Subtle RGB split / chromatic aberration on text and UI edges
- Horizontal scan lines across dark areas
- Occasional pixel tearing or duplicate ghosting
- Keep it stylized, not unreadable

SUBJECT (bottom area, relatively small):
- A 30-something Asian male tech blogger
- Wearing a dark-colored casual t-shirt
- Glasses: optional; only if the host reference wears glasses, keep matching style
- FACIAL EXPRESSION: {{人物表情，默认 serious-but-helpful focused expression with a hint of approachable confidence, looking at camera — "I found the bug" energy, NOT shocked, NOT sulky or annoyed}}
- GESTURE: {{人物手势}} — 手势可依据本风格构图需求自然调整；参考图仅用于保持面部五官一致，不要复制参考图的身体姿势、手势或肩膀角度。
- Half-body shot, positioned in bottom-center or slightly to the side
- One hand may point toward the error element
- Cool rim light with subtle red/cyan glitch tint

TYPOGRAPHY:

⭐ TOP HEADLINE:
- Text: "{{主标题}}"
- Color: white with thick outline, or bright red #FF3B30
- HEAVY WHITE STROKE OUTLINE
- Font: extra bold condensed sans-serif
- Massive size, full width
- Subtle glitch effect on the text edges allowed

ACCENT TEXT:
- "{{辅助小标题}}" in smaller font, supporting role

⭐ BOTTOM SUBTITLE:
- Text: "{{底部副标题}}"
- Color: bright green or white
- Center aligned

WATERMARK (bottom-right):
- "@wwwzhouhui" in small white text with thin stroke

STYLE NOTES:
- The warning/error element is the hook
- Glitch effects should add urgency, not destroy readability
- Subject expression: focused and helpful, not panicked
- Convey "this problem looks scary but I have the fix"
- Optimized for mobile thumbnail: error text readable at small size

ASPECT RATIO: 3:4 vertical
```
