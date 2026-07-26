# 深色科技标题风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

**默认安全牌**。黑底暗科技感背景，青蓝 + 亮黄 + 白字描边，标题是绝对主角，人物在底部做"导师"点缀。

### 视觉特征

- 背景：深色科技风（黑 / 炭灰 / 深蓝黑），可带暗网格、暗 UI 画布、暗工作台，**每篇重新构图**
- 标题：2-3 行巨型中文，占画面 40-50%，青蓝 #00D4FF + 白字青描边 + 亮黄 #FFD93D
- 人物：底部居中，占画面 20-25%，自信微笑，食指轻抬指向重点
- UI 元素：暗色工作流截图 + Agent 对话碎片 + 小结果缩略图，做"证据层"
- 标签：底部 2-3 个深底青边小标签

### 固定

- 人物：参考图 1 五官，只要半身，深色 T 恤
- 标题：三段式颜色（青 / 白描青 / 黄）
- 水印：@wwwzhouhui
- 元素不超出安全区

### 变量

- 背景具体暗色主题（暗网格 / 暗画布 / 暗工作台 / 暗渐变）
- 标题文字内容
- UI 碎片具体内容
- 底部标签文案

### 提示词模板

```
A vertical video thumbnail in 3:4 ratio (1080×1440), dark tech aesthetic Chinese short-video cover style — energetic tech blogger aesthetic optimized for WeChat Channels / Douyin / Xiaohongshu thumbnails.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 15%: hook strip bar with small text
- Middle 60%: massive bold Chinese headline as the dominant visual element + floating UI screenshots
- Bottom 20%: subject half-body portrait (relatively small) + supporting text/tags
- IMPORTANT: keep critical visual elements within the central 1:1 area

COLOR PALETTE & BACKGROUND:
- Dark tech aesthetic, but NOT a fixed repeated background template
- Background can vary by topic: dark studio, dark UI canvas, dark workspace, dark gradient, dark blurred setup, or dark scene collage
- Preferred base: black / charcoal / deep blue-black with localized cyan glow accents
- May include subtle grid, vignette, blur, soft light bloom, or layered dark interface texture
- Primary accent: cyan-blue (#00D4FF) for borders, highlights, and key text
- Secondary accent: bright yellow (#FFD93D) for hook strip and emphasis text
- White (#FFFFFF) for main headline text with thick stroke outlines
- Overall feel: dark, techy, high-contrast — but the background should be recomposed for each topic, not copied 1:1 every time

TOP HOOK STRIP (narrow banner, top 10%):
- A thin horizontal bar spanning full width
- Background: semi-transparent dark with cyan-blue border/glow
- Text inside: "{{顶部钩子条文案}}" in small bright yellow text
- Positioned at very top with slight padding

MAIN HEADLINE (DOMINANT — occupies 40-50% of vertical space):
- This is the PRIMARY visual element, much larger than the subject
- Layout: 2-3 lines of massive bold Chinese text, center-aligned

  Line 1: "{{主标题第1行}}"
  - Color: bright cyan-blue (#00D4FF)
  - Extra bold, largest size

  Line 2: "{{主标题第2行}}"
  - Color: pure white with thick cyan stroke outline
  - Slightly smaller than Line 1

  Line 3: "{{主标题第3行，可选}}"
  - Color: bright yellow (#FFD93D)
  - Bold, with emphasis glow effect

- Font: extra bold condensed sans-serif
- Each character should feel massive, almost filling the width
- Subtle cyan glow/shadow behind text for depth

FLOATING UI ELEMENTS (around the headline, mid-layer):

⭐ ELEMENT 1 (left side, partially behind text):
{{左侧主 UI 元素描述}}
- Dark-themed screenshot fragment with cyan-blue border glow
- Visible nodes connected by lines, suggesting an AI workflow pipeline
- Should serve as background texture rather than the focal point
- Can be resized, tilted, cropped, blurred, or partially hidden behind text

⭐ ELEMENT 2 (right side, smaller):
{{右侧次 UI 元素描述}}
- Small dark UI fragment with subtle accent dots
- Partially cropped, enough to suggest AI dialogue or automation
- Position and shape can vary by composition

⭐ ELEMENT 3 (scattered around headline):
{{围绕标题散落的结果图描述}}
- Small output thumbnails arranged asymmetrically around the main text
- Decorative role only — shows result quality, should not compete with the headline

SUBJECT (bottom area, relatively small — 25% of canvas height):
- A 30-something Asian male tech blogger
- Wearing a dark-colored casual t-shirt (black or deep navy)
- Glasses: optional; only if the host reference wears glasses, keep matching style
- FACIAL EXPRESSION: {{人物表情，默认 confident, slight knowing smile, looking at camera}}
- GESTURE: {{人物手势}} — 手势可依据本风格构图需求自然调整；参考图仅用于保持面部五官一致，不要复制参考图的身体姿势、手势或肩膀角度。
- Half-body shot, positioned in bottom-center
- Relatively SMALL compared to the headline text
- One hand slightly raised with index finger pointing up
- Lighting: cool-toned rim light from sides, matching the cyan-blue accent color

BOTTOM TAGS/LABELS (below or beside the subject):
- 2-3 small tag boxes arranged horizontally
- Each tag has a dark background with cyan border
- Tag contents:
  - "{{标签1}}"
  - "{{标签2}}"
  - "{{标签3}}"
- Small font, supporting role

WATERMARK (bottom-right corner):
- "@wwwzhouhui" in small white text with thin stroke

STYLE NOTES:
- Dark tech aesthetic matching 技术博主's established cover style
- The HEADLINE is the hero, not the person — text should occupy 3-4x more visual space than the subject
- High information density but clear visual hierarchy: hook strip → headline → UI elements → subject → tags
- {{风格主题补充}}
- Cyan-blue + yellow on dark background is the signature color combination
- Photo-realistic portrait for the subject, stylized/dark-UI aesthetic for everything else
- Background must feel newly composed for this topic, not reused from another finished cover
- Optimized for mobile thumbnail: headline must be readable even at small size
- The overall impression at thumbnail size should communicate: "{{缩略图一句话印象}}"

ASPECT RATIO: 3:4 vertical
```
