# Agent 号召风

> 本风格模板须与 `references/brand_baseline.md` 中的品牌基线一起使用。

暗色科技底 + 蓝紫渐变图标 + 亮黄行动号召色 + 对话气泡框，专为 AI 工具推荐、Agent 概念、开发者效率类内容设计，视觉上传达"立刻行动、拥抱未来"的紧迫感。

### 视觉特征

- 背景：深色科技底（深蓝黑 / 墨黑 / 暗蓝），叠加代码编辑器界面、流程图节点（如 Function / Bash / Agent）、数据流箭头等开发者元素，做半透明纹理层
- 标题：2-3 行巨型中文，占画面 40-50%，白色粗体为主 + 亮黄 #FFD93D 强调关键数字或短语
- 对话气泡：左下方亮黄色对话气泡框，内含副标题文案 + 播放按钮图标，暗示视频内容
- 右上角图标区：有产品 logo 时放真实 logo；无 logo 时留白或用 subtle 蓝紫装饰，不硬塞通用 AI 云图标
- 人物：右下方，占画面 20-25%，手指向左下角气泡框，引导视觉动线
- 整体色调偏蓝紫，区别于默认的青蓝科技风，更有 AI 神秘感

### 固定

- 人物：参考图 1 五官，只要半身，深色衬衫或 T 恤
- 对话气泡框：亮黄色，位于左下角，必须包含播放按钮图标
- 右上角图标区：优先放提供的真实产品 logo；未提供时留白，禁止 invented logo
- 标题：白字 + 亮黄强调色双色系
- 水印：@wwwzhouhui
- 元素不超出安全区

### 变量

- 背景叠加的开发者元素具体内容（代码片段 / 流程图 / Agent 工作流 / 终端截图）
- 标题文字内容
- 对话气泡内副标题文案
- 蓝紫渐变的具体色调倾向（偏蓝 / 偏紫 / 均衡）
- 右上角是否放置真实产品 logo（不确定时留白）

### 提示词模板

```
A vertical video thumbnail in 3:4 ratio (1080×1440), dark agent-tech aesthetic Chinese short-video cover style — action-oriented developer tool recommendation aesthetic optimized for WeChat Channels / Douyin / Xiaohongshu thumbnails.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 15%: subtle header area with small hook text or icon
- Middle 55%: massive bold Chinese headline as the dominant visual element + background developer texture
- Bottom 30%: yellow speech bubble (bottom-left) + subject portrait (bottom-right) + watermark
- IMPORTANT: keep critical visual elements within the central 1:1 area

COLOR PALETTE & BACKGROUND:
- Dark agent-tech aesthetic, deep and slightly mysterious
- Background base: black / deep navy / dark blue-black with localized blue-purple glow accents
- Background texture layer: semi-transparent code editor interface, flowchart nodes (labeled "Function", "Bash", "Agent"), data flow arrows, terminal snippets — all subtly faded into the dark background
- Primary accent: blue-purple gradient (#6C63FF → #A855F7) for icons, glows, and decorative elements
- Secondary accent: bright yellow (#FFD93D) for emphasis text and speech bubble
- White (#FFFFFF) for main headline text, extra bold
- Overall feel: dark, futuristic, action-oriented, AI-native — slightly different from pure cyan tech, leaning more blue-purple/mysterious

HEADER AREA (top 10-15%, subtle):
- Small hook text or category label
- Text: "{{顶部钩子条文案}}" in small white or light blue text
- Minimal, should not compete with the main headline

MAIN HEADLINE (DOMINANT — occupies 40-50% of vertical space):
- This is the PRIMARY visual element, massive and commanding
- Layout: 2-3 lines of massive bold Chinese text, left-aligned or center-left

  Line 1: "{{主标题第1行}}"
  - Color: pure white (#FFFFFF), extra bold, largest size
  - Font: extra bold condensed sans-serif

  Line 2: "{{主标题第2行，含关键数字或短语}}"
  - Color: bright yellow (#FFD93D) for the key emphasis word/number, rest in white
  - The yellow portion should be noticeably larger or bolder to draw the eye
  - Example emphasis: only the user-specified key number or keyword (such as "Agent", "150" or the most important action verb) should be highlighted in yellow; do NOT invent numbers or words that are not in the headline

  Line 3: "{{主标题第3行，可选}}"
  - Color: white or light blue-purple (#B8B8FF)
  - Slightly smaller, closing statement

- Each character should feel massive, almost filling the width
- Subtle blue-purple glow/shadow behind text for depth

TOP-RIGHT LOGO / ICON AREA (top-right area):
- If a product logo is provided (e.g. OiiOii logo): place the provided logo here, cleanly integrated against the dark background
- If no logo is provided or the logo is uncertain: leave this area empty or use only a subtle blue-purple decorative glow/dot. Do NOT invent a fake brand logo or generic "AI cloud" icon
- Size: medium, clearly visible but not competing with headline
- Subtle glow effect allowed, but only if no real logo is used

YELLOW SPEECH BUBBLE (bottom-left, prominent):
- A bright yellow (#FFD93D) rounded speech bubble shape
- Contains subtitle text: "{{气泡框副标题文案}}"
- Bold dark text inside the bubble for contrast against yellow
- A play button icon (▶) inside or beside the bubble, suggesting video content
- The bubble should feel energetic and action-oriented
- Position: bottom-left quadrant, angled slightly upward

SUBJECT (bottom-right area, 20-25% of canvas height):
- A 30-something Asian male tech blogger
- Wearing a dark-colored casual shirt (black or deep charcoal)
- Glasses: optional; only if the host reference wears glasses, keep matching style
- FACIAL EXPRESSION: {{人物表情，默认 confident and persuasive — slight smile, eyes looking toward the speech bubble or camera}}
- GESTURE: {{人物手势，默认 one hand pointing diagonally down-left toward the yellow speech bubble, guiding the viewer's eye}} — 手势可依据本风格构图需求自然调整；参考图仅用于保持面部五官一致，不要复制参考图的身体姿势、手势或肩膀角度
- Half-body shot, positioned in bottom-right
- Relatively SMALL compared to the headline text
- Lighting: cool blue-purple rim light from the side, matching the accent palette

BACKGROUND DEVELOPER TEXTURE (behind everything, semi-transparent):
{{背景开发者元素描述}}
- Faded code editor interface with syntax-highlighted lines (blue/green/purple tones)
- Flowchart or pipeline nodes with labels like "Function", "Bash", "Agent"
- Data flow arrows connecting nodes
- Terminal or command-line snippets
- All elements at 15-25% opacity, serving as texture not focal points
- Should suggest "developer tools / automation / AI agent" without being readable

WATERMARK (bottom-right corner, near subject):
- "@wwwzhouhui" in small white text with thin stroke

STYLE NOTES:
- Dark blue-purple agent-tech aesthetic, distinct from the default cyan-blue tech style
- The HEADLINE is the hero — text should occupy 3-4x more visual space than the subject
- Visual flow: headline → cloud icon → speech bubble → subject (Z-pattern reading)
- {{风格主题补充}}
- Yellow speech bubble is the signature element for this style; the top-right area holds the product logo when available, otherwise stays clean
- The speech bubble with play button creates urgency and "watch now" energy
- Photo-realistic portrait for the subject, stylized/tech aesthetic for everything else
- Background developer texture must vary by topic — recompose for each cover
- Optimized for mobile thumbnail: headline must be readable at small size, yellow bubble pops at any scale
- The overall impression at thumbnail size should communicate: "{{缩略图一句话印象}}"
- Best suited for: AI tool recommendations, developer productivity tools, Agent-era concepts, "must-have tool" urgency content

ASPECT RATIO: 3:4 vertical
```
