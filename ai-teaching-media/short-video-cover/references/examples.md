# 已验证的短视频封面提示词案例

这里是已经跑通过的案例,供参考"怎么把不同类型的视频文案提炼成 3:4 封面提示词"。

---

## 案例 1:Claude Desktop 接 API 后联网避坑(已发)

**视频核心**:上一集教 Claude Desktop 接国产模型很火,但很多人留言说接好后不能联网。这条视频教大家在开发者模式里打开 Allowed Egress Hosts 即可。

**素材提炼**:

| 项目 | 内容 |
|---|---|
| 顶部主标题 | "Claude 不能上网了?" |
| 辅助小标题 | "Claude Desktop · 避坑指南" |
| 底部副标题 | "10 秒解决" |
| Element 1(问题) | Claude Desktop 截图 + 红色"❌ 无法访问外部网络"横幅 |
| Element 2(解决) | Claude Desktop 联网搜索成功 + 绿色 ✅ |
| 表情 | 自信微笑,看镜头 |
| 手势 | 右手食指指向报错截图 |

**关键决策点**:
- 原始口播提到"接了 API 不能访问外网"——这是行话,主标题改为"Claude 不能上网了?"
- 底部用"10 秒解决"而不是"一键搞定"——具体数字比抽象承诺更有说服力
- UI 元素用了双截图(报错+成功),讲清楚视频要解决什么问题

**完整提示词** 见本文件末尾「完整示例 1」区块。

---

## 案例 2(示意):n8n 微信群消息抓取自动化

**视频核心**:用 n8n 自动抓取微信群消息生成日报。

**素材提炼**:

| 项目 | 内容 |
|---|---|
| 顶部主标题 | "微信群聊看不完?" |
| 辅助小标题 | "n8n · 自动化教程" |
| 底部副标题 | "自动出日报" |
| Element 1(问题) | 截图:微信群消息 999+ 未读,密密麻麻 |
| Element 2(解决) | 截图:整齐的日报文档,带分类和高亮 |
| 表情 | 自信微笑,看镜头 |
| 手势 | 右手食指指向 999+ 未读截图 |

**关键决策点**:
- 不写"用 n8n 抓取微信群消息"——这是行话,改成"微信群聊看不完?"让所有人都懂
- 底部"自动出日报"比"一键生成"更具体

---

## 案例 3(示意):Cursor 报错快速定位

**视频核心**:Cursor 写代码报错时的快速 debug 技巧。

**素材提炼**:

| 项目 | 内容 |
|---|---|
| 顶部主标题 | "代码报错找不到?" |
| 辅助小标题 | "Cursor · 提效技巧" |
| 底部副标题 | "30 秒定位" |
| Element 1(问题) | 满屏红色错误堆栈,看不出问题在哪 |
| Element 2(解决) | Cursor 高亮出问题代码行,旁边有 AI 建议 |
| 表情 | 自信微笑,看镜头 |
| 手势 | 右手食指指向报错堆栈 |

---

## 完整示例 1(Claude 联网避坑封面 · 可直接跑)

下面这段是把案例 1 的素材填进模板后的完整提示词,可以直接传给 `ai-teaching-media/ai-image-generator/scripts/generate.py`。

```
A vertical video thumbnail in 3:4 ratio (1080×1440), BRIGHT and high-contrast Chinese short-video cover style — energetic tech blogger aesthetic optimized for WeChat Channels / Douyin / Xiaohongshu thumbnails.

OVERALL COMPOSITION (3:4 VERTICAL):
- Top 25% (top safe zone): massive bold Chinese headline with strong white stroke outline
- Middle 50% (1:1 safe zone): real-photo-style half-body portrait of subject + floating UI elements
- Bottom 25% (bottom safe zone): bold subtitle line with stroke outline + small watermark
- IMPORTANT: keep critical visual elements within the central 1:1 area, as edges may be cropped on different display surfaces

SUBJECT (CENTERED LOWER-MIDDLE):
- A 30-something Asian male tech blogger
- Wearing an OVERSIZED, RELAXED-FIT, heavyweight waffle-knit short-sleeve polo shirt in Midnight Green color (#004953)

  CRITICAL FIT DETAILS:
  - EXTREMELY relaxed, oversized silhouette — drapes loosely
  - DROPPED SHOULDERS with sagging fabric folds
  - WIDE LOOSE SHORT SLEEVES extending to just above the elbow
  - DEEP V OPENING with both buttons completely undone
  - Visible diagonal draping wrinkles
  - Heavyweight waffle-knit fabric with HIGHLY VISIBLE grid texture
  - Color: rich muted dark green, similar to iPhone 11 Pro Midnight Green
  - Style: Japanese-inspired oversized casual polo, NOT fitted

- Glasses: thin black wire-frame
- FACIAL EXPRESSION: confident and approachable — slight smile, eyes looking directly at camera, looks like a knowledgeable mentor about to share a tip. NOT shocked, NOT wide-eyed, NOT exaggerated, NOT theatrical.
- Half-body shot, head positioned around 1/3 from top of central safe zone
- Body slightly turned, right hand raised pointing toward UI element
- Lighting: bright soft warm light from front, clean studio illumination revealing waffle fabric texture

FLOATING UI ELEMENTS (around the subject):

⭐ ELEMENT 1 (MOST PROMINENT — make this VISUALLY DOMINANT in the middle area):
A LARGE realistic Claude Desktop screenshot with a prominent FAILURE state:
- Claude logo visible at top
- Chat input showing user query: "帮我搜一下今天的AI新闻"
- Claude's response showing a BIG RED ERROR BANNER with bold Chinese text:
  "❌ 无法访问外部网络 / 网络连接失败"
- The error banner should be OVERSIZED and clearly readable
- A large red ❌ X-mark overlay on top-right corner of screenshot
- Subtle red glow around the screenshot edge to emphasize the "problem" state
- This is the MAIN visual storytelling element — make it big and obvious

⭐ ELEMENT 2 (smaller, supporting):
A smaller secondary screenshot showing the SOLUTION state:
- Claude Desktop with successful web search results
- Green checkmark ✅ overlay
- Positioned slightly behind/below Element 1, partially overlapping
- Curved white arrow connecting from the failure state to the success state, suggesting transformation

The two elements together tell a visual story: "❌ 报错 → ✅ 解决"

The subject's pointing hand should gesture toward Element 1 (the error), as if saying "看到这个问题没?"

BACKGROUND:
- Clean modern home office, bright warm tone
- Soft warm bokeh, slightly blurred
- Subtle desk elements visible but out-of-focus (monitor edge, plant, warm lamp glow)
- Overall tone: warm cream / light beige gradient — bright and inviting, NOT dark
- Feels like a YouTuber thumbnail

TYPOGRAPHY:

⭐ TOP HEADLINE (most important — must be readable to non-technical viewers):
- Text: "Claude 不能上网了?"
- Color: bright yellow #FFD93D
- HEAVY WHITE STROKE OUTLINE (8-10px stroke for vertical format)
- Font: extra bold condensed sans-serif (思源黑体 Heavy / 阿里巴巴普惠体 Bold)
- Massive size, occupying most of the top zone width
- Slight drop shadow for depth
- Position: top 20% of canvas, with 150px margin from very top

ACCENT TEXT (small, just below top headline):
- "Claude Desktop · 避坑指南" in white with thin stroke, semi-transparent
- Smaller font, supporting role only

⭐ BOTTOM SUBTITLE (also critical):
- Text: "10秒解决 ✅"
- Color: bright green #7FFF00
- Same heavy white stroke outline
- Same font, slightly smaller than top headline
- Center aligned
- Position: bottom 20% of canvas, with 200px margin from very bottom

WATERMARK (bottom-right, within safe zone):
- "@wwwzhouhui" in small white text with thin stroke

STYLE NOTES:
- Photo-realistic portrait, sharp and well-lit
- Bright, clean, inviting background — opposite of dark tech aesthetic
- Color palette: warm bright background, subject colors anchored by host reference, yellow + green typography with thick white strokes, RED accent for error state
- Strong visual hierarchy:
  1. TOP: catchy plain-language headline (anyone can understand)
  2. MIDDLE: visual problem demonstration (red error screenshot DOMINATES)
  3. BOTTOM: solution promise
- Confident, approachable expression — NEVER shocked or theatrical
- Optimized for mobile thumbnail at small size — even non-technical viewers should immediately understand the visual story
- Vertical composition flow: HEADLINE → ERROR SCREENSHOT (visual hook) → SUBJECT → SOLUTION SUBTITLE

ASPECT RATIO: 3:4 vertical
```
