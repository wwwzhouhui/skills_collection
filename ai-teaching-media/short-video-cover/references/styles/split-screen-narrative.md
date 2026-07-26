# 双屏对比叙事风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

人物居中，双手/手势连接"问题"和"解决"两个截图，像在说"左边这个坑，右边这样填"。

### 视觉特征

- 构图：上下或左右两块对比区域，中间用箭头/曲线连接
- 问题侧：红色/暗色/报错截图，带 ❌ 或警告感
- 解决侧：绿色/亮色/成功截图，带 ✅ 或清爽感
- 人物：居中或偏下，手势指向问题侧或连接两侧
- 标题：横跨画面上方，大字压在两屏之上

### 固定

- 双屏对比关系必须明确：一亮一暗、一错一对
- 人物：参考图 1 五官，半身
- 水印：@wwwzhouhui

### 变量

- 分屏方向（上下 / 左右）
- 问题/解决截图内容
- 标题位置（上方 / 中间分隔带）
- 背景色调（通常偏深，衬托对比）

### 提示词模板

```
A vertical video thumbnail in 3:4 ratio (1080×1440), Chinese short-video cover in "before vs after" split-screen style, optimized for WeChat Channels / Douyin / Xiaohongshu.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 20%: massive Chinese headline spanning full width
- Middle 60%: split-screen comparison (problem vs solution) + subject connecting them
- Bottom 20%: small subtitle/tags + watermark

SPLIT-SCREEN COMPARISON (the core visual story):

⭐ LEFT / TOP — PROBLEM STATE (make this visually dominant):
{{问题截图描述}}
- Darker / redder tint, error state
- Large red ❌ or warning icon overlay
- Subtle red glow around the edge
- Clearly readable Chinese error text if applicable

⭐ RIGHT / BOTTOM — SOLUTION STATE (brighter, cleaner):
{{解决截图描述}}
- Lighter / greener tint, success state
- Large green ✅ overlay
- Curved arrow connecting from problem to solution, showing transformation

SUBJECT (center or lower-center):
- A 30-something Asian male tech blogger
- Wearing a dark-colored casual t-shirt
- Glasses: optional; only if the host reference wears glasses, keep matching style
- FACIAL EXPRESSION: {{人物表情，默认 confident mentor smile, looking at camera}}
- GESTURE: {{人物手势}} — 手势可依据本风格构图需求自然调整；参考图仅用于保持面部五官一致，不要复制参考图的身体姿势、手势或肩膀角度。
- Half-body shot
- Body position: centered between the two screens, one hand pointing to the problem side, the other gesturing toward the solution side
- Relatively small compared to the split-screen elements

TYPOGRAPHY:

⭐ TOP HEADLINE:
- Text: "{{顶部主标题}}"
- Color: {{标题颜色}}
- HEAVY WHITE STROKE OUTLINE
- Font: extra bold condensed sans-serif
- Massive size, full width

⭐ BOTTOM SUBTITLE:
- Text: "{{底部副标题}}"
- Color: {{副标题颜色}}
- Heavy white stroke outline
- Center aligned
- Reserve a clear zone for this subtitle — it must NOT overlap the solution screenshot's key content

BACKGROUND:
- {{背景描述，默认 dark gradient or dark tech base, keeping focus on the two comparison screens}}

WATERMARK (bottom-right):
- "@wwwzhouhui" in small white text with thin stroke

STYLE NOTES:
- The split-screen contrast is the hero — problem vs solution must be instantly readable
- Subject acts as the bridge/commentator, not the main focal point
- Curved arrow or visual connector between the two states is essential
- Optimized for mobile thumbnail: even at small size, viewer should understand "this video fixes X"

ASPECT RATIO: 3:4 vertical
```
