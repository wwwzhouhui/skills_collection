# 风格: 卡通信息图风 (cartoon-infographic)

**适用场景**: 技术博客、产品文档、知识管理、教程配图。传达"干净、好懂、专业但不冷"的感觉。根据场景需要，可选加入 host 卡通形象辅助叙事。

## 风格基因(每个提示词开头必须包含)

```
Style: Warm hand-drawn sketchnote infographic with soft organic lines and rounded container shapes, like a skilled illustrator's whiteboard notebook.
Background: warm cream / light beige (#F5F0E8 to #FAF6EE range), solid flat fill, no grid lines, no visible paper texture or grain pattern. Not pure white — the warmth of the background gives a natural notebook feel.
Lines: black ink hand-drawn outlines with visible stroke weight variation (thicker on containers, thinner on connectors and arrows), slightly wobbly and organic, never perfectly straight. Rounded corners on all containers look hand-sketched, not geometrically precise. Lines should be slightly blobby at corners, tapering at ends, like a felt-tip pen — not a uniform-width digital stroke.
Fills: containers and boxes have soft pastel interior fills with slightly irregular edges as if colored with a wide marker. Fills are flat, no gradients. Not every container needs a fill — use fills to create visual grouping and hierarchy.
Color palette: functional muted tones — soft sage green, dusty blue, warm peach-orange, soft lavender purple, muted coral. Each color serves a purpose (green=positive/growth, blue=process/data, orange=attention/contrast, purple=structure). Low saturation, not pastel-faded but not bright either. Think "soft marker on warm paper".Large parent containers use very light tinted backgrounds (almost white with a hint of color), while smaller inner containers use slightly deeper fills — this creates clear nesting hierarchy.
Typography: mix of clean sans-serif for main labels AND hand-lettered style for annotations and small notes near arrows. Large bold headline, concise labels, optional English in parentheses for key terms. Small callout text should feel like someone jotted it on the diagram after drawing. Annotations near arrows and at margins must use a looser, more casual hand-lettered font, clearly different from the main label font — creating a "drawn first, annotated later" layered feel.
Layout: generous whitespace, clear visual hierarchy, flat 2D feel, balanced negative space.
Icons: hand-drawn doodle-style mini illustrations (brain, gear, lock, book, lightbulb, etc.) with color fills, sketched quality matching the container line style. NOT clean vector line icons — they should look hand-drawn.Arrows and connectors are thin hand-drawn lines with small arrowheads, never thick block arrows or PowerPoint-style shape arrows.
Overall: educational, approachable, warm, personal — like a talented colleague drew this on a whiteboard to explain something to you. Publication-ready but not cold.
Do not use photographs, 3D rendering, glossy effects, heavy shadows, dark backgrounds, neon colors, bright saturated colors, dense BI dashboard visuals, perfect geometric shapes, or clean vector icons.
```

## 补充说明

- **底色**: 暖奶油色 (#F5F0E8 ~ #FAF6EE)，不是纯白——给画面温暖的笔记本底调，但不要做成明黄色
- **线条**: 黑色手绘墨水线条，有**粗细变化**（容器外框粗、连接线和箭头细），有机略不完美，手绘圆角不是几何精确的圆角
- **填色**: 容器内部有柔和的色块填充，边缘略不规则（像马克笔涂的），不是所有容器都填色——用填色做视觉分组和层级区分
- **配色**:
  - 功能性多色：灰绿(正向/增长)、灰蓝(流程/数据)、暖桃橙(注意/对比)、灰紫(结构)、灰珊瑚(强调)
  - 低饱和但要看得清——像柔和马克笔画在暖底纸上的效果
  - **嵌套层级**：大容器底色极淡（几乎是白色带一丝色调），小容器用稍深的填色，形成清晰的父子层级
  - 不要高饱和儿童色，不要霓虹色，不要亮色块
- **文字**:
  - 主标题和标签用干净无衬线体
  - 箭头旁边的小注释、补充说明用**手写风格**文字，像画完图后随手标注上去的
- **图标**: 手绘涂鸦风小插画（大脑、齿轮、锁、书本等），**带填色**，不是线性矢量图标，和容器线条风格一致
- **布局**:
  - 充足留白，视觉层级清晰
  - 圆角手绘容器，内部 padding 充足
  - 箭头和连接线用**细手绘线条+小箭头头**，不要粗块状箭头、不要 PPT 风格的形状箭头
  - 整体像干净的教育信息图，不是 PPT，不是 BI 看板
- **角色(可选)**:
  - 某些场景需要小人辅助叙事时，加入 host 卡通形象
  - 角色承担辅助叙事：在角落、流程节点旁、对话气泡里做反应
  - 不需要小人的场景(纯架构图、纯数据图)不强制加入
  - 由 manifest item 的 `needs_character` 字段控制
- **禁忌**:
  - 不要纯白背景
  - 不要网格纸背景
  - 不要真实照片感
  - 不要高饱和配色
  - 不要深色背景
  - 不要密集文字堆砌
  - 不要干净的矢量线性图标
  - 不要几何精确的圆角和直线
  - 不要粗块状箭头或 PPT 风格的形状箭头
  - 不要父子容器用相同浓度的填色（大容器要比小容器淡很多）
- **图标一致性**: 同一张图内所有图标保持相同的抽象层级——要么全用简笔涂鸦，要么全用具象插画，不要混搭

## 版式倾向

### 对比类图

- 左右分栏圆角面板，中间用箭头或分隔线
- 顶部大标题，每栏内部简洁
- 适合"A vs B"、"前后对比"、"新旧差异"

### 流程类图

- 3-5 个圆角步骤容器，用手绘箭头连接
- 每个步骤留足空白，不要塞次级说明
- 底部可加一句话总结

### 架构类图

- 分层或分组模块，层级清晰
- 模块间用线条或箭头表示关系
- 保持极简，不要过度装饰

### 抽象概念类图

- 中心辐射式布局，核心概念居中
- 周围 3-5 个卡片式子概念
- 用颜色区分不同概念类别

## 三条自检

1. **是否足够干净**: 留白充足，信息密度适中，不是每个角落都塞满东西。
2. **配色是否有功能**: 每种颜色都有用途，不是装饰性的彩虹配色。
3. **线条是否有手绘感**: 粗细有变化，圆角不规则，图标是涂鸦风不是矢量图标。
4. **角色是否必要**: 如果加了卡通人物，它是否真的帮助理解？如果去掉它图是否同样清晰？