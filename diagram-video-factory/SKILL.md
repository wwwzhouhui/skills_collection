---
name: diagram-video-factory
description: 扁平图解动画风"图随话动"讲解视频出片 skill（参考"程序员老王"式科技图解：米白底 + 橙红绿语义色 + 白卡片 + 元素随旁白逐个生长动画 + 章节制结构 + 参考文献收尾 + 烧录字幕（白字黑边）+ 品牌水印与片尾卡 + 三张封面 4:3 / 3:4 / 9:16 + 各平台发布文案），自带公共工序（事实核查与来源台账、发布前合规自查、成片验收、交付边界）。当用户说"做一期图解视频 / 图解动画讲解 / 科技科普图解 / 像程序员老王那样的视频 / diagram video"，或要在本仓库里新建一期、改场景、换贴纸或真实 Logo、重出片、改字幕、出封面、写发布文案时使用。全链路本地：Playwright + ffmpeg + 火山/小米/edge-tts 配音 + 本地 codex CLI 生图，不需要剪辑软件。
description_zh: 扁平图解动画风"图随话动"讲解视频出片 skill（元素随旁白逐个生长 + 语义色纪律 + 章节制 + 参考文献 + 烧录字幕 + 三画幅封面与各平台发布文案），自带公共工序（查证、合规、验收、交付边界）。当用户说"做一期图解视频 / 图解动画 / 科技科普图解 / 程序员老王风格"或要新建一期、改场景、重出片、改字幕、出封面、写发布文案时使用。全链路本地：Playwright + ffmpeg + 火山/小米/edge TTS + 本地 codex CLI 生图，不需要剪辑软件。
display_name: 图解动画视频工厂
category: video
version: 1.0.0
author: wwwzhouhui
---

# diagram-video-factory：图解动画讲解视频出片

把一个技术概念做成"程序员老王"式的图解动画讲解视频：**米白纯色背景上一块单画布，白卡片、语义色图形随旁白逐个生长出现，讲完一个概念，结尾列参考文献**。适合 3~12 分钟的概念讲解（"XX 是什么 / 为什么"），不适合 vlog、盘点、开箱。

工具就是本仓库（下文 `<仓库>`），CLI 是 `<仓库>/bin/dg`，参数全在 `<仓库>/config.json`。每期内容在 `config.json` 的 `dirs.projects`（默认 `<仓库>/episodes/<日期 标题>/`），中间产物与成片在 `dirs.build`（默认 `<仓库>/build/<日期 标题>/`）。

本文件只讲流程与规矩。细节按需翻 `references/`，全部在本仓库内，不依赖外部目录：

| 文件 | 讲什么 |
|---|---|
| `references/dsl.md` | 场景与封面 API（一行代码一个元素：卡片/气泡/流程链/卡片堆/数字列/向量/公式/参考文献） |
| `references/scene-patterns.md` | 招牌版式坐标套路（架构图/聊天 UI/对比卡片堆/向量空间/矩阵，可直接抄） |
| `references/publish.md` | 标题公式（「XX 是什么？」）、各平台规格与机制 |
| `references/voices-volc.md` | 火山 TTS：调用域、resourceId 配套、实测音色、报错速查 |
| `references/voices-mi.md` | 小米 MiMo TTS：端点与 assistant 角色规矩、无语速参数与时间戳怎么对齐 |
| `references/fact-check.md` | 事实核查与来源台账 |
| `references/compliance.md` | 发布前合规自查 |
| `references/delivery-qa.md` | 成片机器与目视验收、封面验收、交付边界 |
| `references/stickers.md` | 贴纸、真实 Logo、真人漫画像 |

## 硬规矩

1. **全链路本地。** 旁白走语音合成，`config.json` 的 `tts.engine` 三选一：**`volc`**（火山引擎，返回逐字时间戳，字幕最准，推荐）/ **`mi`**（小米 MiMo，接口无语速参数、无逐字时间戳，靠本地 atempo + 静音检测估算）/ **`edge`**（本机 edge-tts，免费无凭证）。凭证在 `<仓库>/.env`。**动了 TTS 配置先跑 `dg voice`**。贴纸走本地 `codex` CLI 生图；真实 Logo 走 Wikimedia Commons 官方 SVG（`dg logo`）；配乐放 `assets/bgm.mp3`，没有就出无配乐成片。改配置不改代码。
2. **一处为主。** 期目录就是工程目录，`scenes.js` 是唯一手写源（旁白、场景、封面都在里面）；`scenes/`、`旁白稿.md`、`字幕.srt`、`封面-*.png` 是生成物，不手改、不外拷。`README.md`（资料来源）和 `发布.md`（文案）是人写的。成片在 `<dirs.build>/<期>/outputs/final.mp4`，不放进期目录。
3. **先旁白后画面。** 旁白按 `|` 切 beat，每 beat 3~4 句配一组元素。**时长是变量**：动手前先跟用户确认目标时长，再按「1 分钟 ≈ 8 个 beat ≈ 210 字（1.15 倍语速）≈ 1.5~2 个场景」折算。短片 2~3 分钟（6~8 个场景）、中片 5~12 分钟（15~30 个场景）、长片更长——每个场景保持「3~4 beat / 80~120 字 / 一屏 10~20 个元素」的舒适区，**靠加场景变长，别把一个场景写得又长又满**。长片分幕见「做长片」。
4. **画布 1920×1080，米白底（`#E9E9E4`）。y≥960 是字幕区，右上 320×130 是水印区**，元素不进去；`dg scenes` 的 ⚠ 必须清零。
5. **语义色纪律（这是这类视频风格统一的根本）：橙 = 强调/主线（当前讲到哪、残差流、品牌点睛），红 = 负面（拒绝/有害/风险/差向量），绿 = 正面（无害/通过/收益），蓝 = 中性知识，深灰墨字 = 文字。一期从头到尾同一语义只用同一种颜色，观众扫一眼就知道好坏。** 不要发明第四种语义色。
6. **每 beat 必须有画面动作。** 旁白念到哪句，画面上就要有元素出现/高亮/移动——没有画面动作的抽象句并入相邻 beat。动作=新元素入场（渲染器自动做），或既有元素变色/加框（`frameBox` "讲到哪、亮到哪"）。
7. **公司、产品、模型用真实 Logo；人物、吉祥物、物件用贴纸；文字、箭头、框、图表用 DSL 原语。** 讲到具体公司用官方 Logo（`dg logo`）；吉祥物角色（如柴犬程序员）用 `dg image` 出贴纸，只在引子和结尾出场，中段是图形的主场。Excalidraw 画人很丑，人和物件一律出贴纸。
8. **事实先查再写。** 数字、日期、参数（维度数/层数/条数）要有来源，写进期目录 `README.md`；结尾场景必须放 `refList` 参考文献（论文 arXiv 号、开源仓库），这是这个体裁的信任来源。查证动作见 `references/fact-check.md`。
9. **品牌层自动带，不用每期写。** 右上角水印（第一场景淡入）、片尾品牌卡（5.5 秒，静音）、封面品牌标由工具生成，名字、品牌色、slogan 在 `config.json` 的 `brand`（首次使用改成自己的频道名）。
10. **交付四件套：成片 + 三张封面（4:3 横版 / 3:4 竖版 / 9:16 抖音竖屏）+ `发布.md`**，主用标题、视频号简介和抖音描述直接贴在回复里。

## 命令

```bash
D=<仓库>/bin/dg
$D new "<标题>"                          # 建期目录：scenes.js 模板 + 发布.md 模板
$D logo "<标题>" logo-x="Commons 文件名.svg" ... [--vs=x,y]   # 真实 Logo → assets/<name>.png；--search="词" 先看候选
$D image "<标题>" name="英文描述" ...     # 贴纸，一次 ≤4 张（四宫格同风格）→ assets/<name>.png
$D stills "<标题>"                       # 每 beat 静帧 → <后台>/<期>/work/frames/，逐张看
$D cover "<标题>"                        # 封面-4x3.png / 封面-3x4.png / 封面-9x16.png → 期目录
$D captions "<标题>"                     # 核对字幕：每条的时间、文本，以及高亮分段
$D voice                                 # 配音自检：回显 engine/端点/音色，并真合成一句
$D build "<标题>"                        # scenes → tts → render → mix → cover → clean，出 outputs/final.mp4 / 字幕.srt / 旁白稿.md
```

分步：`scenes` / `tts` / `voice` / `captions` / `render [scene]` / `mix [gain]` / `clean` / `open` / `list`。期参数用标题子串（`dg build 图解`）。`dg render <期> 03-xxx` 只重渲一段并自动重拼 master，接 `dg mix` 即新成片；TTS 有缓存，只有改过的旁白会重配。

## 一期的流程

### 1. 立题与查证
- 明确选题、观众、口吻。图解体裁的选题公式：**一个概念 + 一个为什么**（"abliteration 是什么"、"残差流为什么重要"）。
- 精读 1 篇核心论文/官方文档（记 arXiv 号），扫 1~2 个开源实现；数字、日期、参数来源列进 `README.md`「资料来源」。完整动作见 `references/fact-check.md`。

### 2. 章节大纲（图解体裁的骨架，照抄）
```
引子(30~60s)     生活场景/聊天 UI 切入 → 词源或一句话定义 → "接下来 10 分钟讲透它"
铺垫(1~2min)     看懂主线所需的最小前置（架构图/名词），只讲后面要用的
核心直觉(1~2min) 把概念翻译成一个比喻/一张图（"概念=方向"），这是全片记忆点
方法①②(2~3min)  步骤拆解，每步一张图：数据从哪来 → 怎么算 → 怎么挑
落地(1min)       公式/代码一屏 + 实际效果
结尾(1min)       一句升华 + 边界与责任 + refList 参考文献
```
- 每章一个"章节心象"：这章看懂后观众脑子里留下的那张图。先定心象再写旁白。
- 每个 beat 都要有能画出来的东西；讲不了的细节删掉，别塞注脚。

### 3. 写旁白（scenes.js）
- 口语短句，第一人称，有梗但不抖机灵；每句一个信息点。数字用中文读法利于 TTS（"四千零九十六个数字"），字幕用原文。
- 抽象句必须配比喻："embedding 是一长串数字" → "也就是一个固定长度的向量"。
- 按原速写即可，成片语速 1.15 倍。

### 4. 出 Logo 与贴纸
- 先列本期出现的公司/产品/模型 → `dg logo`；再列物件/吉祥物 → `dg image`（一次 ≤4 张，英文描述写姿势/颜色/风格）。逐张看 `assets/<name>.png`：杂点、断块 → `--single` 重出，抠图问题 → `--rekey`。
- 封面主角：公司题材用 Logo，概念题材用核心图形（封面可以不用贴纸，靠大字 + 橙色下划线）。

### 5. 画场景
- 抄 `references/scene-patterns.md` 的版式坐标再微调；一屏 10~20 个元素；一个 beat 塞不下就删元素。
- **讲到哪、亮到哪**：在讲到某元素的 beat 里给它叠 `frameBox`/`highlight`，比让眼睛自己找强。
- `dg stills` 后**逐张看静帧**：重叠、越界、文字超宽、太挤。改到满意。

### 6. 封面
- `scenes.js` 末尾 `cover` 函数：`s.coverLayout({ ratio, title, sub, sticker, tag })`；`dg cover` 出三画幅。
- 标题 ≤2 行、每行 ≤8 字：第一行说对象，第二行说钩子（橙色 + 橙色下划线）；副标放三个关键词；`tag` 默认「图解讲清楚」。
- 看三张 png：文字没撞贴纸、下划线压在钩子行、品牌标在角上。细则见 `references/delivery-qa.md`。

### 7. 出片与验收
- `dg build`。抽 2~3 帧看（`ffmpeg -ss <t> -i final.mp4 -frames:v 1 x.png`）：字幕白字黑边在底、水印在右上、语义色没串、贴纸擦出正常；片尾看一眼 `99-brand`。
- `dg captions <期>`：逐条核对字幕时间与文本（`[a·b·c]` 是高亮分段，默认关着，仅供开启后核对）。
- 看 `字幕.srt` 前几条：原文拼写、数字未拆。
- 机器检查与交付边界按 `references/delivery-qa.md`。`README.md` 写好，时长以 `ffprobe` 为准。

### 8. 发布文案与标题
- 按 `references/publish.md`：标题公式「XX是什么？」/「为什么XX」，5 个候选选 1 主用；视频号简介、抖音描述（前 55 字钩子 + 话题 3~5 个排最后 + AIGC 标注）、小红书、B 站、公众号摘要、评论区置顶。
- 数字与 `README.md` 一致；合规自查勾完（`references/compliance.md`）。填 `发布.md`，交付四件套。

## 做长片（>5 分钟）

**代码层面没有时长上限**：渲染按场景分段出视频再 concat 拼 master（`lib/render.js`），TTS 逐场景合成与缓存，场景数不受限。「能拍多长」只取决于内容规划。

| 目标时长 | 场景数 | 总字数 | 分幕 |
|---|---|---|---|
| 2~3 分钟 | 6~8 | 500~700 | 不用分幕 |
| 5~10 分钟 | 15~25 | 1300~2600 | 2~3 幕 |
| 15~25 分钟 | 40~60 | 3500~6000 | 3~5 幕 |

长片比短片多做的四件事：
1. **分幕。** 每幕开头加一张「章节卡」场景（幕标题 + 一句导览；参考目标频道 7 章结构：引子/铺垫/直觉/方法①/方法②/落地/结尾）。发布文案的时间戳按幕切。
2. **每 2~3 分钟一个呼吸点。** 一句小结、一个真实例子、一张对比表。别一路平铺。
3. **配乐改用播放列表。** `config.json` 的 `bgm.playlist` 填几首，按顺序拼成一整段再整体循环。
4. **封面标签别提时长。** `cover.seriesTag` 默认「图解讲清楚」。

**长片一定要用断点续跑**：TTS 与渲染都按场景缓存——
```bash
dg tts <期> <场景名>      # 只重配改过的那一幕
dg render <期> <场景名>   # 只重渲这一段，并自动重拼 master
dg mix <期>               # 出片
```
⚠️ `dg build` 会整期重渲，长片别拿它做小改动。

## 修改类请求怎么接

| 用户说 | 做法 |
|---|---|
| 改某句旁白 / 加一段 | 改 `scenes.js` → `dg build`（只重配改过的场景） |
| 用了假机器人 / 要真 Logo | `dg logo` 取官方 SVG → scenes.js 换 `s.image` 名字 → `dg stills` → `dg render && dg mix && dg cover` |
| 换贴纸 / 吉祥物太丑 | `dg image` 重出 → `dg stills` → `dg render && dg mix`（封面用到的话再 `dg cover`） |
| 元素出得太快/太慢 | config `render.motion`：`animSeconds`（入场时长）、`stagger`（同拍错峰）、`leadIn` → `dg render && dg mix` |
| 某拍元素太多、入场太赶 | 删元素（推荐）或 `render.motion.stagger` 调小、`overflow` 调大 → `dg render && dg mix` |
| 字幕与语音对不齐（小米通道） | `node lib/diag-captions.mjs <期目录绝对路径>` 看锚定率；把 `captions.maxChars` 放大到装得下最长小句，或给长句补逗号 → 重跑 `dg tts` |
| 渲染太慢 / 机器吃紧 | config `render.workers`（默认 4 路，每路一个 Chromium；1 = 串行），出帧与路数无关 |
| 语速快/慢 | config `tts.speed`（默认 1.15）→ `dg build`。⚠️火山是原生变速，小米是本地 `atempo` 后处理 |
| 换配音引擎 | config `tts.engine` 改 `"volc"` / `"mi"` / `"edge"` → **必须重跑 `dg tts`**（三家音频、时间戳都不同）→ `dg voice` 试听 |
| 要更长 / 更短的片子 | 只改 `scenes.js` 的场景数（按「1 分钟 ≈ 1.5~2 个场景 ≈ 210 字」折算）→ `dg build`。⚠️这是重写内容的活。>5 分钟记得分幕 + 呼吸点 + `bgm.playlist` |
| 配乐大/小 | config `bgm.gain` → `dg mix`；临时试听 `dg mix <期> 0.4` |
| 字幕字号/位置 | config `captions.fontSize / baselineY` → `dg render && dg mix` |
| 字幕跟读高亮（默认关） | config `captions.highlight.enabled: true` → `dg render && dg mix`；颜色留空用品牌色 |
| 水印位置/关掉/换 logo | config `brand.watermark.position/enabled`、`brand.logo` → `dg render && dg mix` |
| 片尾卡 slogan / CTA / 不要 | config `brand.slogan`、`brand.endCard.*` → `dg render <期> 99-brand && dg mix` |
| 换背景色 | config `render.paper`（默认 `#E9E9E4` 米白）→ `dg render && dg mix`；DSL 里 `C.paper` 同步 |
| 换品牌色 | config `brand.accent`（影响标题/下划线/高亮默认色）→ `dg render && dg mix && dg cover` |
| 封面文案 / 贴纸 / 画幅 | `scenes.js` 末尾 cover 函数 → `dg cover`；画幅 config `cover.ratios` |
| 标题 / 发布文案 / 换平台 | 改 `发布.md`，不用重出片 |
| 在 Obsidian 里改了图 | `dg render && dg mix` 直接读 `.excalidraw.md`；结构性改动回 `scenes.js` |
| 换声线 / 换曲 | 先 `dg voice` 确认档位，再改各引擎音色字段（火山 `tts.voice` / 小米 `tts.mi.voice` / edge `tts.edge.voice`）或 `bgm.playlist` |
| 换账号品牌 | config `brand.name/accent/slogan`，其余不动 |

## 跨平台说明（Windows / macOS / Linux）

- **路径展开**：`lib/paths.cjs`、`lib/scene-dsl.js`、`lib/render.js` 里的 `~` 统一走 `require('os').homedir()`。**别用 `process.env.HOME`**——Git Bash 下它是 MSYS 写法 `/c/Users/x`，Windows 版 Node 会解析成 `C:\c\Users\x` 而 ENOENT。
- **`file://` URL**：Chromium 载入 `render.html` 和本地图片一律用 `require('url').pathToFileURL(p).href`。
- **Chromium**：`lib/chromium.cjs` 的 `resolveChromium()` 在 ms-playwright 里自动取本地最高版本。
- **`npm install` 可能以 exit 1 收尾但依赖已装好**（postinstall 拉 Chromium 失败时）；`node_modules/` 已随仓库带全（playwright / lz-string），浏览器走 `resolveChromium()`，别反复重装。
- **codex 在 Windows 上只有 `codex.cmd`**，`lib/gen-image.mjs` 的 `resolveCodex()` 会自动处理。
- **Node 联网**：Commons API 需要代理时走 `lib/proxy.mjs`（读 `HTTPS_PROXY`/`HTTP_PROXY`，写进 `.env` 也行）。
- **`bin/dg`**：Git Bash 下运行；路径含中文或空格记得加引号。
- **期目录移出仓库时**：`config.json` 的 `dirs.projects` / `dirs.build` 支持绝对路径；⚠️期目录里 `scenes.js` 第 6 行的 `require('../../lib/scene-dsl')` 是相对默认 episodes 目录写的，换了位置要改写成仓库绝对路径（正斜杠）。成片实际所在的后台目录要和 `dirs.build` 一致，否则诊断脚本量到的是上一次构建。

## 已知坑

- **ffmpeg 参数是字面量**：`render.js` 里视频帧走 stdin、旁白音频走 fd3 管道、成片走 stdout 落盘，文件路径不进命令行（防注入，也顺带避免了路径转义问题）。代价：`render.fps`（=30）与 `render.leadSeconds`（=0.3）被固化进参数，改了 config 会启动报错提醒同步改代码。分段与 master 是 matroska 流存成 `.mkv`，`mix-bgm` 读 `master.mkv` 重封装出 `final.mp4`。
- **Logo**：很多官网有验证页拦截，Logo 一律走 Commons API（`dg logo`），别去官网抓图。
- **火山 TTS 的两个调用域互不相通**：`ark-` 开头 Key 只走 `plan` 域；打错域报 `45000010 Invalid X-Api-Key`，看着像 Key 错其实是域不对——先查 `tts.endpoint`。音色与 `resourceId` 必须配套。`dg voice` 可提前自检。
- **小米 MiMo TTS**：正文必须放 `assistant` 角色消息；接口无语速参数（本地 atempo 实现）；无逐字时间戳（静音检测估算，`work/audio/<scene>.json` 的 `align` 标 `silence-estimate`）；音色固定九个；顿号不作为小句边界（`lib/tts/mi.mjs` 与 `lib/captions.cjs` 的标点集合必须逐字一致）。细节见 `references/voices-mi.md`。
- **改旁白后先 `dg scenes` 再 `dg tts`**：TTS 读的是 `scenes/script.json`（由 `dg scenes` 生成）。`dg build` 一条龙里有 scenes 步，不受影响。
- **字幕逐字时间戳靠火山的 `enable_subtitle`**：关掉会退化成按字数估时间，别关。字幕文本用原文（TTS 词表会吞空格/改写 `@` 这类词）。
- **字幕高亮**（默认关，开启后）：量字符区间用 `tspan.getExtentOfChar`（码点数下标），别用 `Range.getBoundingClientRect()`（只量得出第一个字）；火山的 `wordList` 会吞空格，按非空白字符对齐。
- **验收字幕/画面同步用两个诊断脚本**（`lib/`，只读可反复跑）：`node lib/diag-captions.mjs <期目录绝对路径>`（字幕锚定率）、`node lib/diag-schedule.mjs <期目录绝对路径>`（逐拍入场偏移；图解版排期不跨拍累积，看"起入 +x"≤0.15s 即健康）。
- **画面跟不上旁白**在图解版基本不可能：每拍按"逻辑单元"（DSL 复合图形=一个整体）错峰入场，放不下先压错峰、再压入场时长，误差不跨拍累积。核对用 `node lib/diag-schedule.mjs <期目录绝对路径>`（"起入 +x"≤0.15s 即健康）。一拍塞下一整条 flowChain（上百个基础元素）也只要 1 秒左右；要避免的是一拍塞 15+ 个**互不相关**的独立元素（视觉上一闪而过）——删元素比调参数划算。
- **并行出帧靠两点，别动**：`render.html` 的 `seek()` 每帧把底色矩形原地重插（强制整屏重画，保证多页并行与单页逐帧一致）；每路单开一个 Chromium。改渲染器后用 `render.workers=1` 和 `4` 各出一遍，`ffmpeg -f framemd5` 对比必须 0 帧不同。
- **不要并发跑 `dg image`**：codex 没按指定路径落盘时会兜底抓"最近生成的图"，并发会互相抓错。
- **`dg build` 的清理步可能被安全钩子拦**（批量删除文件需要确认）：不影响交付，手动清一次或用 `dg clean`。
- **字体**：渲染用系统粗黑体（MiSans / HarmonyOS Sans SC / Microsoft YaHei / PingFang SC 栈，字幕与标签 `font-weight 700`，英文/数字可 `italic: true` 出斜体）。要换字体改 `render.html` 的 font-family。
