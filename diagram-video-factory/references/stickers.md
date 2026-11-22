# 贴纸（codex imagegen）

`bin/wb image "<期>" name="英文描述" [name2=...]`，≤4 张走 2×2 四宫格（一次额度、同风格）；`--single` 单张；`--rekey` 只重抠；`--ref=path.png` 带参考图对齐风格。

风格提示词固定在 `lib/gen-image.mjs` 顶部 `STYLE`：Excalidraw 手绘、粗黑马克笔描边、五色平涂（#ffec99 / #a5d8ff / #b2f2bb / #ffc9c9 / #e9ecef）、Q 版、纯白底、无文字无阴影。描述里只写**主体**：

- 人物：体型 + 姿势 + 服装颜色（用五色之一）+ 表情。例：`A lean athletic standing chibi person with a slim V-shaped torso, subtle six-pack lines, relaxed confident pose, wearing a pale green tank top`
- 物件：视角 + 主色。例：`A simple side-view bicycle with two round wheels, pale blue frame`
- 别写场景、背景、文字、数字。

后处理（自动）：泛洪抠白底 → 边缘羽化 → 连通块过滤（去杂点、去邻格残片，<3% 最大块面积的都删）→ 裁到内容 + 24px 边距 → 透明 PNG 到 `assets/<name>.png`，同时拷到 `scenes/` 供 `.excalidraw.md` 的 `## Embedded Files` 引用。

检查：Read `assets/<name>.png`。常见问题：
- 主体天然分块（分离的手、飘散的物件）被连通块过滤删掉 → `--single` 重出并让主体连在一起，或描述里加 "all parts connected"。
- 风格漂成写实/细线 → 提示词里强调 thick wobbly marker outline，或 `--ref` 带上一张满意的贴纸。
- 四宫格里某格空白 → 该 name 报"空白格"，单独 `--single` 补。

放置：`s.image(x, y, 'name', { h: 370, align: 'center' })`；动画为左→右擦出，铅笔跟随。

# 真实 Logo（公司 / 产品 / 模型题材默认）

讲到具体公司、产品、模型时，主角用官方 Logo，**不用贴纸拟人代指**（AI 画的拟人机器人再可爱，观众也认不出说的是哪家）。贴纸只留给人物、器械、道具这类没有官方形象的东西。

```bash
W=bin/wb   # 在仓库根目录执行
$W logo --search="Anthropic logo"                         # 列 Commons 候选（标 "非 svg" 的别用）
$W logo "<期>" logo-claude="Claude AI symbol.svg" logo-anthropic="Anthropic logo.svg" \
              logo-openai="OpenAI logo 2025 (symbol).svg" logo-openai-word="OpenAI logo 2025 (wordmark).svg" \
              --vs=claude,openai                          # 另出 assets/logos-vs.png（A VS B，封面主图）
```

- 参数值写**精确文件名**最稳；写搜索词就取第一个 `.svg` 结果，结果要 Read 核对是不是现行版。
- 命名：`logo-<名>` 方形标志（渲染 800 高），`logo-<名>-word` 横长字标（渲染 1600 宽）；`--vs=a,b` 按 `a.png` 或 `logo-a.png` 找。
- 产物透明 PNG 在 `assets/`，原 SVG 在后台 `work/raw/`，来源（Commons 页面、原文件 URL、日期）自动追加到 `assets/logos.json`，写 README「画面素材」时照抄。
- 选版本：带年份取最新（OpenAI 用 2025 花形新标，不用 2017~22 旧版）；公司标和产品标分开（Anthropic 字标 ≠ Claude 星芒），画面讲模型就用产品标，表头/署名用公司字标。
- Commons 没有：去官网 press kit / brand 页找 SVG，下载前确认授权；实在没有矢量图就用 Excalidraw 手写公司名，不要拿 codex 生成仿冒 Logo。
- 放置尺寸：主视觉标志 h 260~300；卡片、柱状图里 h 100~130；字标当标签 Anthropic w 300~360 / OpenAI h 50~56。
- 用途是新闻评论中指代公司，只用原样 Logo，不改色、不变形、不拼进别家品牌里。

# 真人漫画像（讲到具体人物时默认）

讲到具体公众人物（阿莫代伊、奥特曼、黄仁勋……）时，用**以真人照片为参考的漫画像**，不用通用西装小人代指（通用小人认不出是谁）。

```bash
# 1) 参考照：维基百科页面主图（API 取 original），缩到 ≤900 宽，放临时目录，不进期目录
curl -s "https://en.wikipedia.org/w/api.php?action=query&titles=Jensen_Huang&prop=pageimages&piprop=original&format=json"
# 2) 一人一条，desc 只写姿势/表情/服装；命名 p-<人>
$W image "<期>" p-huang="arms crossed, confident grin, wearing his signature black leather jacket" --ref=/path/huang.jpg --likeness
```

- `--likeness`：参考图只取长相（脸型、发型、眼镜、肤色、标志性穿着），画风仍是白板贴纸；不加这个开关，参考图会被当"照搬画风"用，出来是写实照。
- **不要并发跑 `wb image`**：codex 没按指定路径落盘时会兜底抓"最近生成的图"，并发会把别人的图抄过来（实测三张同时出，三张全成了同一个人）。一张一张串行跑，出完 Read 核对是不是本人。
- 姿势对应立场：赞同 = thumbs up，反对 = arms crossed，发起人 = 抬手示意停；人物 h 260~330，下面配公司字标 + 名字。
- 用途是新闻评论里指代公众人物：只画公开形象，不丑化、不加侮辱性元素，不拿来画与事实无关的剧情。
- 维基媒体偶尔回 429，取 logo / 照片之间间隔几秒。
