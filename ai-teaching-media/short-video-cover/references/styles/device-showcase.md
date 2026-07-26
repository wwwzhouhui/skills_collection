# 手持设备展示风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

## 一句话定位

人物手持手机/平板/设备，把产品 UI 直接怼到观众眼前的封面。适合展示网页、App、UI 设计、作品集、高级感数字产品。

## 视觉特征

- 背景：深空宇宙/星云感，黑蓝渐变 + 蓝色发光漩涡/粒子，宏大且有科技感
- 标题：顶部 2-3 行超大字体，金属铬蓝/冰蓝渐变，厚白描边，3D 立体字
- 人物：位于画面中上部，双手持设备伸向镜头，设备屏幕是视觉焦点
- 设备屏幕：展示真实产品界面（网页、App、UI、代码编辑器、Agent 面板等）
- 漂浮元素：半透明科技图标（六边形、代码括号、设置齿轮、AI 图标等）环绕在人物周围
- 色调：深蓝、冰蓝、银白、少量青紫，整体高级、冷静、未来感
- 整体：产品展示感强，像高端数码产品发布会海报

## 固定

- 比例：3:4 竖版（1080×1440）
- 标题必须在顶部，使用金属/铬感蓝色渐变 + 白色粗描边
- 必须有人物手持设备伸向镜头的动作
- 设备屏幕必须清晰可读，是画面核心视觉锚点
- 背景必须是深空/星云/科技感暗色，不能是纯色或明亮背景
- 水印：右下角 "@wwwzhouhui"
- 禁用：暖色调背景、卡通化、人物过小、设备屏幕被手遮挡、无漂浮科技图标

## 变量

- 标题文案与产品关键词
- 设备类型（手机 / 平板 / 笔记本屏幕 / 悬浮界面）
- 设备屏幕展示的具体 UI 内容
- 漂浮科技图标的种类和位置
- 星云/漩涡的具体形态与亮度
- 人物表情与衣着（默认深色上衣，突出设备）

## 提示词模板

```text
A vertical video thumbnail in 3:4 ratio (1080×1440), premium device-showcase Chinese short-video cover style — cosmic tech aesthetic, optimized for WeChat Channels / Douyin / Xiaohongshu.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 25%: massive bold Chinese headline with chrome/ice-blue gradient and heavy white stroke
- Middle 55%: subject holding a tablet/phone/device toward the camera, screen clearly visible
- Bottom 20%: subtle floating tech icons + watermark
- Background: deep space/cosmic nebula with blue glowing swirls and particles

COLOR PALETTE & BACKGROUND:
- Deep black/navy background (#020617 → #0F172A)
- Cosmic blue nebula swirls and glowing particles (#3B82F6, #06B6D4, #6366F1)
- Subtle starfield or dust particles
- Title: chrome/ice-blue gradient (#60A5FA → #3B82F6 → #A855F7) with thick white stroke
- Device frame: dark metallic or sleek black, thin bezel
- Screen UI: realistic app/website interface, light or dark theme depending on content
- Accent glows: cyan, blue, soft purple
- Overall feel: premium, futuristic, product-launch keynote aesthetic

MAIN HEADLINE (DOMINANT — top 20-25%):
- 2-3 lines of massive bold Chinese text, center-aligned
- Chrome/ice-blue gradient fill with thick white stroke outline
- Slight 3D bevel or metallic sheen
- Font: extra bold condensed sans-serif
- Must be readable at small thumbnail size

  Line 1: "{{主标题第1行}}"
  Line 2: "{{主标题第2行（可选）}}"

- LAYERING: the headline sits BEHIND the subject in z-order — where they overlap, the subject's head/hair occludes the text edge; text must never cover the hair or face

SUBJECT (center, upper-middle):
- A tech content host with a clear face, optional glasses, half-body framing
- FACIAL EXPRESSION: {{人物表情，默认 confident and focused with a subtle warm smile, looking at camera, calm expert vibe — NEVER cold, stern or displeased}}
- GESTURE: {{人物手势}} — 双手持设备伸向镜头，把屏幕展示给观众；手势可依据本风格构图需求自然调整；参考图仅用于保持面部五官一致，不要复制参考图的身体姿势、手势或肩膀角度
- Clothing: dark casual top (black or dark navy) so the device and title stand out
- Upper body visible, positioned behind the device
- Lighting: dramatic with blue rim light from the cosmic background, face softly lit

DEVICE & SCREEN (center, dominant focal point):
- A modern tablet or large smartphone held with both hands, slightly tilted toward the viewer
- Device frame: thin, dark, premium
- Screen content: {{设备屏幕内容描述}}
  - For a website: show the actual landing page UI, headline, buttons, hero image
  - For an App: show the main interface or key feature screen
  - For a UI kit/component: show the component in context
- Screen must be the brightest/clearest area after the title
- Reflections and subtle glow around the device to integrate with cosmic background

FLOATING TECH ICONS (around the subject and device):
- Semi-transparent glowing hexagons, code brackets `</>`, settings gears, AI brain icons, database symbols
- Color: cyan/blue/white glow
- Size: small to medium, decorative, should not compete with device screen
- Distribution: 3-5 icons around the subject, some near top corners, some near device edges

STYLE NOTES:
- The device screen is the hero after the headline — it must be readable and central
- The subject's role is to "present" the device, not to be the main focus
- Background should feel vast and premium, like a product launch event
- Keep the color palette cool (blues, cyans, purples) — avoid warm or playful colors
- Photo-realistic subject + polished UI screen + cosmic background = intentional high-end mix
- Optimized for mobile thumbnail: title and device screen must pop at small size
- The overall impression at thumbnail size: "this person is showing me a polished digital product"
- Best suited for: website showcases, app launches, UI/UX tutorials, portfolio pieces, premium tool demos

WATERMARK:
- "@wwwzhouhui" in small white text at bottom-right corner

ASPECT RATIO: 3:4 vertical
```
