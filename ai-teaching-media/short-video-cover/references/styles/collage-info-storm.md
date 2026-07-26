# 拼贴信息飓风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

多张 UI 碎片/截图分层叠加，制造纵深和信息密度，适合讲工作流、多工具组合、复杂流程。

### 视觉特征

- 构图：前中后三层，元素之间有明确遮挡关系
- 前景：最大的素材图或标题文字
- 中景：人物或次要素材
- 后景：模糊的背景素材
- 字体：压在层次之间，白色或描边效果
- 整体：信息密度高但层级清晰

### 固定

- 至少有一张额外素材（UI 截图/流程图）
- 人物：参考图 1 五官，半身
- 水印：@wwwzhouhui

### 变量

- 各层元素内容
- 叠加方式
- 透明度/模糊度
- 背景色调

### 提示词模板

```
A vertical video thumbnail in 3:4 ratio (1080×1440), Chinese short-video cover in layered UI collage style, optimized for WeChat Channels / Douyin / Xiaohongshu.

OVERALL COMPOSITION (3:4 VERTICAL):
- Foreground: large headline text + main UI fragment
- Mid-ground: subject half-body + secondary UI fragments
- Background: blurred/dimmed additional UI layers
- Strong sense of depth through overlap, blur, and drop shadows

LAYERED UI COLLAGE:

⭐ FOREGROUND:
{{前景元素描述}}
- Largest UI fragment or screenshot
- Slightly tilted, with drop shadow
- Partially behind the headline text

⭐ MID-GROUND:
- Subject: A 30-something Asian male tech blogger, wearing dark casual t-shirt, optional glasses matching host reference
- FACIAL EXPRESSION: {{人物表情，默认 confident smile, looking at camera}}
- GESTURE: {{人物手势}} — 手势可依据本风格构图需求自然调整；参考图仅用于保持面部五官一致，不要复制参考图的身体姿势、手势或肩膀角度。
- Half-body shot, positioned among the UI layers
- Secondary UI fragments FLOAT around the subject with depth and shadows — the subject does NOT physically hold or grab any UI panel

⭐ BACKGROUND:
{{后景元素描述}}
- Multiple smaller UI fragments, workflow diagrams, chat bubbles
- Blurred or low-opacity, creating depth
- Arranged asymmetrically, avoiding a repeated-template feel

TYPOGRAPHY:

⭐ MAIN HEADLINE:
- Text: "{{主标题}}"
- Color: white with thick outline or {{其他高对比色}}
- Font: extra bold condensed sans-serif
- Massive size, layered between foreground and mid-ground elements
- Partially occluded by UI fragments for depth

ACCENT TEXT:
- "{{辅助小标题}}" in smaller font

BACKGROUND:
- {{深色沉稳色调，默认 dark charcoal / deep blue-black, letting the layers pop}}

WATERMARK (bottom-right):
- "@wwwzhouhui" in small white text with thin stroke

STYLE NOTES:
- Layers must have clear depth: foreground sharp, background blurred/dimmed
- Headline remains readable despite the collage
- Each collage element should relate to the video topic
- Avoid chaos — high density but clear hierarchy
- Optimized for mobile thumbnail: headline readable at small size

ASPECT RATIO: 3:4 vertical
```
