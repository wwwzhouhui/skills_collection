# 卡片展示人设风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

## 一句话定位

人物居中、内容卡片在前、标题居上的"达人展示"风格。适合工具/产品/技巧/案例合集类口播,营造"我把好东西摊给你看"的亲和信任感。

## 视觉特征

- 背景：黑到暖橙的径向渐变（中心偏下亮橙，四周压暗），营造舞台聚光灯感
- 标题：顶部 2-3 行巨型中文标题，亮黄色 + 黑色粗描边，动感倾斜，视觉锤极强
- 人物：位于画面中下部，半身或大半身，表情自信、热情、有说服力
- 内容卡片：2-4 张圆角卡片/截图/产品图，位于人物胸前或下方，被人物手势自然引导
- 手势：**不固定**，根据口播文案和展示内容自由设计（托举、指向、摊开、比数字等）
- 色调：暖橙 + 亮黄 + 深黑，整体活力、年轻、小红书爆款感
- 装饰： subtle 光晕、速度线、小星星/闪光点缀，增强动感

## 固定

- 比例：3:4 竖版（1080×1440）
- 标题必须在顶部，且是画面最大视觉元素
- 标题颜色：亮黄色为主，黑色粗描边
- 内容卡片必须有统一圆角和阴影，排列整齐但不死板
- 水印：右下角 "@wwwzhouhui"
- 禁用：冷色调背景、科技感网格、故障风、双手抱胸/插兜等封闭姿态

## 变量

- 标题文案与强调词
- 内容卡片数量与内容（2-4 张，根据口播决定）
- 人物手势与表情（根据口播情绪自由调整）
- 是否戴帽子/穿什么颜色上衣（默认不戴帽，保持 host 辨识度；用户要求时再戴）
- 背景橙色的浓淡方向

## 提示词模板

```text
A vertical video thumbnail in 3:4 ratio (1080×1440), warm creator-style Chinese short-video cover — "card showcase host" aesthetic optimized for WeChat Channels / Douyin / Xiaohongshu thumbnails.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 25%: massive bold Chinese headline, yellow with black outline, tilted slightly for dynamism
- Middle 45%: the host  centered, upper body visible, interacting with content cards
- Bottom 30%: 2-4 rounded content cards arranged in a row or staggered stack, supported or pointed by the host's hands
- Background: dark black-to-warm-orange radial gradient, brightest near the host, darker at edges

COLOR PALETTE & BACKGROUND:
- Deep black at the edges, transitioning to warm orange/amber (#F59E0B → #EA580C) in the center
- Soft orange glow behind the host's head and shoulders
- Title: bright yellow (#FFD93D) with thick black/dark outline
- Cards: light cream or white backgrounds with rounded corners, subtle drop shadows
- Accent colors inside cards should come from the actual UI/product screenshots, but keep harmonious
- Overall feel: warm, energetic, approachable, creator-recommendation vibe

MAIN HEADLINE (DOMINANT — top 20-25%):
- 2-3 lines of massive bold Chinese text, left-aligned or center-aligned
- Color: bright yellow (#FFD93D) with thick black outline/drop shadow
- Font: extra bold, slightly condensed, with a subtle forward tilt or speed-line accent
- Must be readable at small thumbnail size

  Line 1: "{{主标题第1行}}"
  Line 2: "{{主标题第2行，含关键数字/词，可标黄强调}}"
  Line 3: "{{主标题第3行（可选）}}"

- LAYERING: the headline sits BEHIND the host in z-order — where they overlap, the host's head/hair occludes the bottom edge of the text (classic text-behind-subject thumbnail effect); the text must NEVER cover the host's hair or face

HOST / SUBJECT (center, 40-45% vertical space):
- A tech content host with a clear face
- FACIAL EXPRESSION: {{人物表情，默认 confident and enthusiastic, looking directly at camera, like a friend recommending something great}}
- GESTURE: {{人物手势}} — 手势必须根据本次口播内容和展示卡片自然设计，不要 1:1 复制参考图姿势；参考图仅用于保持面部五官一致
- Clothing: dark casual shirt by default; cap only if user explicitly requests it
- Upper body visible, positioned so the face is clearly visible above the cards
- Lighting: warm rim light from behind, matching the orange background glow

CONTENT CARDS (bottom 25-30%, 2-4 cards):
- Rounded-corner cards with soft shadows, arranged in a row or gentle arc
- Each card shows a key visual from the topic:
  - For tools: UI screenshot / workflow preview
  - For products: product render / before-after / feature highlight
  - For collections: representative thumbnail for each item
- Card style should feel like physical prints the host is presenting
- Cards must not cover the host's face or main title
- Optional small labels or captions under each card in simple Chinese

STYLE NOTES:
- The headline is the hero — must dominate the top of the frame
- The host's gesture should actively present or interact with the cards, not just stand there
- Gestures can include: holding cards up, pointing at a card, spreading hands to present options, making an "OK" or counting gesture, etc. Choose based on the script.
- Background should stay simple: gradient + glow only, no busy textures
- Cards should look like real objects with depth, not flat pasted screenshots
- The overall impression at thumbnail size: "this creator is showing me 2-4 specific things I should check out"
- Best suited for: tool roundups, product comparisons, tutorial collections, "X things you should know" content

WATERMARK:
- "@wwwzhouhui" in small white text at bottom-right corner

ASPECT RATIO: 3:4 vertical
```
