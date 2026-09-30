---
name: whiteboard-video-factory
description: 手绘白板风"边画边讲"讲解视频出片 skill（Excalidraw 逐笔动画 + 火山/小米/edge-tts 配音 + 烧录字幕并逐段跟读高亮 + 品牌水印与片尾卡 + 三张封面 4:3 / 3:4 / 9:16 + 各平台发布文案：视频号 / 小红书 / 抖音 / B 站 / 公众号），自带公共工序（事实核查与来源台账、发布前合规自查、成片机器与目视验收、交付边界）。当用户说"做一期白板视频 / 边画边讲 / 手绘讲解视频 / 用 excalidraw 做视频 / whiteboard video"，或要在本仓库里新建一期、改场景、换贴纸或真实 Logo、重出片、改字幕（含字幕高亮 / 跟读高亮 / 卡拉OK式高亮）、出封面、写发布文案（含抖音）时使用。全链路本地：Playwright + ffmpeg + 火山/小米 TTS + 本地 codex CLI 生图，不需要剪辑软件。
description_zh: 手绘白板风"边画边讲"讲解视频出片 skill（Excalidraw 逐笔动画 + 火山/小米/edge-tts 配音 + 烧录字幕并逐段跟读高亮 + 品牌水印与片尾卡 + 三张封面 4:3 / 3:4 / 9:16 + 各平台发布文案），自带公共工序（查证、合规、验收、交付边界）。当用户说"做一期白板视频 / 边画边讲 / 手绘讲解视频 / 用 excalidraw 做视频 / whiteboard video"，或要在本仓库里新建一期、改场景、换贴纸或真实 Logo、重出片、改字幕（含字幕高亮 / 跟读高亮）、出封面、写发布文案时使用。全链路本地：Playwright + ffmpeg + 火山/小米 TTS + 本地 codex CLI 生图，不需要剪辑软件。
display_name: 白板讲解视频工厂
category: video
version: 1.0.0
author: hailaobao666
---

# whiteboard-video-factory：白板讲解视频出片

工具就是本仓库（下文 `<仓库>`），CLI 是 `<仓库>/bin/wb`，参数全在 `<仓库>/config.json`。每期内容在 `config.json` 的 `dirs.projects`（默认 `<仓库>/episodes/<日期 标题>/`），中间产物与成片在 `dirs.build`（默认 `<仓库>/build/<日期 标题>/`）。

本文件只讲流程与规矩。细节按需翻 `references/`，全部在本仓库内，不依赖外部目录：

| 文件 | 讲什么 |
|---|---|
| `references/dsl.md` | 场景与封面 API（一行代码一个元素） |
| `references/scene-patterns.md` | 版式坐标套路（可直接抄） |
| `references/stickers.md` | 贴纸、真实 Logo、真人漫画像 |
| `references/publish.md` | 标题公式、各平台规格与机制、抖音怎么写 |
| `references/voices-volc.md` | 火山 TTS：两个调用域、resourceId 与音色的配套关系、实测可用音色、报错速查 |
| `references/voices-mi.md` | 小米 MiMo TTS：端点与 assistant 角色规矩、无语速参数、无时间戳怎么对齐、九个实测音色、三条通道怎么选 |
| `references/fact-check.md` | 事实核查与来源台账 |
| `references/compliance.md` | 发布前合规自查 |
| `references/delivery-qa.md` | 成片机器与目视验收、封面验收、交付边界 |

## 硬规矩

1. **全链路本地。** 旁白走语音合成，`config.json` 的 `tts.engine` 三选一：**`volc`**（火山引擎，`seed-tts-2.0`，凭证在 `<仓库>/.env`，音色可以是官方音色或你自己的声音复刻；**返回逐字时间戳，字幕最准，默认用它**）/ **`mi`**（小米 MiMo `mimo-v2.5-tts`，凭证 `MI_TTS_API_KEY`，音色固定九个；**接口没有语速参数、也不返回时间戳**，语速靠本地 `atempo`、时间轴靠静音检测估算，见 `references/voices-mi.md`）/ **`edge`**（本机 edge-tts，免费、无凭证，`tts.edge.python` 指向装好 `edge_tts` 的解释器）；语速默认 1.2 倍。贴纸走本地 `codex` CLI 生图（codex 分派到无生图能力的模型时，改用内置 ImageGen 工具出四宫格再 `--rekey` 切图）；真实 Logo 走 Wikimedia Commons 官方 SVG（`wb logo`）；配乐放 `assets/bgm.mp3`，没有就出无配乐成片。改配置不改代码。**动了 TTS 配置先跑 `wb voice`**：它回显引擎/端点/模型/音色并真合成一句，比出片到一半才报错省事。三个引擎各有自己的音色字段（火山 `tts.voice` / 小米 `tts.mi.voice` / edge `tts.edge.voice`），别互相顶替。
2. **一处为主。** 期目录就是工程目录，`scenes.js` 是唯一手写源（旁白、场景、封面都在里面）；`scenes/`、`旁白稿.md`、`字幕.srt`、`封面-*.png` 是生成物，不手改、不外拷。`README.md`（资料来源）和 `发布.md`（文案）是人写的。视频不放进期目录：成片在 `<dirs.build>/<期>/outputs/final.mp4`，中间产物在同目录 `work/`，`旁白稿.md` 里自动带成片链接。
3. **先旁白后画面。** 旁白按 `|` 切 beat，每 beat 3~4 句配一组元素。**时长是变量，不是固定 3 分钟**：动手前先跟用户确认目标时长，再按「1 分钟 ≈ 8 个 beat ≈ 200 字（1.2 倍语速）≈ 1.5~2 个场景」折算。短片 2~3 分钟（6~8 个场景）、中片 5~10 分钟（15~25 个场景）、长片 15~40 分钟（40~90 个场景）都行——每个场景都保持「3~4 beat / 80~120 字 / 一屏 10~20 个元素」的舒适区，**靠加场景变长，别把一个场景写得又长又满**。长片另外要分幕与呼吸点，见「做长片」。
4. **画布 1920×1080。y≥960 是字幕区，右上 320×130 是水印区**，元素不进去；`wb scenes` 的 ⚠ 必须清零。
5. **公司、产品、模型用真实 Logo；人物、器械、物件用贴纸；文字、箭头、框用 Excalidraw。** 讲到具体公司时主角用官方 Logo（`wb logo`），不用生图拟人机器人代指，观众认不出是谁。讲到具体公众人物时用真人照片参考的漫画像（`wb image ... --ref=照片 --likeness`，见 `references/stickers.md`），不用通用小人代指。Excalidraw 画人很丑，人和物件一律出贴纸。
6. **事实先查再写。** 数字、日期、价格要有来源，写进期目录 `README.md`；估算值在旁白和文案里都标"据报道/估算"。查证动作见 `references/fact-check.md`。
7. **品牌层自动带，不用每期写。** 右上角手写水印（第一场景逐笔画入）、片尾品牌卡（5.5 秒，静音）、封面上的品牌标都由工具生成，名字、品牌色、slogan 在 `config.json` 的 `brand`；标题和点睛色优先用 `C.brand`。
8. **交付四件套：成片 + 三张封面（4:3 横版 / 3:4 竖版 / 9:16 抖音竖屏）+ `发布.md`**，主用标题、视频号简介和抖音描述直接贴在回复里。

## 命令

```bash
W=<仓库>/bin/wb
$W new "<标题>"                          # 建期目录：scenes.js 模板 + 发布.md 模板
$W logo "<标题>" logo-x="Commons 文件名.svg" ... [--vs=x,y]   # 真实 Logo → assets/<name>.png；--vs 拼 "A VS B" 封面图；--search="词" 先看候选
$W image "<标题>" name="英文描述" ...     # 贴纸，一次 ≤4 张（四宫格同风格）→ assets/<name>.png
$W stills "<标题>"                       # 每 beat 静帧 → <后台>/<期>/work/frames/，逐张看
$W cover "<标题>"                        # 封面-4x3.png / 封面-3x4.png / 封面-9x16.png → 期目录（画幅见 config cover.ratios）
$W captions "<标题>"                     # 核对字幕：每条的时间、文本，以及高亮分段（[a·b·c] 里 · 的位置就是色块跳的节拍）
$W voice                                 # 配音自检：回显 engine / 端点 / 模型 / 音色，并真合成一句 → build/_voice-check.wav
$W build "<标题>"                        # scenes → tts → render → mix → cover → clean，出 outputs/final.mp4 / 字幕.srt / 旁白稿.md
```

分步：`scenes` / `tts` / `voice` / `captions` / `render [scene|99-brand]` / `mix [gain]` / `clean` / `open` / `list`。`wb build` 出片后自动 `clean`：删 `work/frames` 静帧和 `work/out` 里已不在场景表的旧分段，各场景分段与 master 保留（单场景重渲、重混配乐要用）。期参数用标题子串（`wb build 薄肌`）。`wb render <期> 03-xxx` 只重渲一段并自动重拼 master，接 `wb mix` 即新成片；TTS 有缓存，只有改过的旁白会重配。

## 一期的流程

### 1. 立题与查证
- 明确选题、观众、口吻（默认冷静科普口吻，账号口吻写进 `references/publish.md`）。
- 搜 2~3 轮；**官方页优先且读到全文**，二手站数字只做线索。
- 数字、日期、来源列进 `README.md`「资料来源」，口径（"240 倍 = 6000 万 / 25 万"）单列一节。完整动作见 `references/fact-check.md`。

### 2. 写旁白（scenes.js）
- 口语短句，每句一个信息点。数字用中文读法利于 TTS（"三百美元"）；字幕用原文，所以阿拉伯数字也行，但 `@`、`iOS` 这类 TTS 会念歪的词要斟酌。
- 结构：开场定义/反差 → 分解（三要素/两列对比/时间线）→ 怎么算/怎么做 → 数字与门槛 → 冷水/边界 → 一句话总结 + 评论区问题。
- 每个 beat 都要有能画出来的东西，抽象句并入相邻 beat。按原速写即可，成片语速 1.2 倍。

### 3. 出 Logo 与贴纸
- **先列本期出现的公司/产品/模型 → `wb logo`。** `wb logo --search="<公司> logo"` 看 Commons 候选，挑官方现行版（带年份的取最新），一期一条命令取齐：标志（`logo-<名>`，方形，放主视觉）+ 字标（`logo-<名>-word`，横长，当标签/表头）；两家对比再加 `--vs=a,b` 出 `logos-vs.png` 当封面主图。来源自动记在 `assets/logos.json`，抄进 README「画面素材」。Commons 没有的，去官网 press kit / brand 页找 SVG，确认授权再下载。
- 再列本期物件（人物、器械、设备、道具），`wb image` 一次 ≤4 张，英文描述写姿势/服装/颜色（Excalidraw 五色：pale yellow/blue/green/red/grey）。
- 逐张看 `assets/<name>.png`：杂点、邻格残片、主体断块 → `--single` 单张重出；只是抠图问题 → `--rekey`。封面主角贴纸也在这一步出（公司题材封面用 Logo，不另出）。

### 4. 画场景
- 抄 `references/scene-patterns.md` 的版式坐标再微调；贴纸 `s.image(x, y, 'name', { h: 370, align: 'center' })`，人形 360~380 高；Logo 同样用 `s.image`：主视觉标志 h 260~300，卡片/柱子里 h 100~130，字标当标签用 `w`。
- 一屏 10~20 个元素；一个 beat 塞不下就删元素，别指望笔画得完（排期最多溢出到下一段前 35%，再多就整体压缩）。
- `wb stills` 后**逐张看静帧**：重叠、越界、文字超宽、太挤。改到满意。

### 5. 封面
- `scenes.js` 末尾 `cover` 函数：`s.coverLayout({ ratio, title, sub, sticker })`，`build(__dirname, scenes, { cover })`；`wb cover` 按 config `cover.ratios` 出 4:3 / 3:4 / 9:16（9:16 给抖音，标题与贴纸压在中央安全区，因为抖音封面上下会被裁到约 1080×1464）。
- 标题 ≤2 行、每行 ≤8 字：第一行说对象，第二行说钩子（自动品牌色 + 马克笔高亮）；副标放数字；贴纸用主角（公司题材传 `sticker: 'logos-vs'` 或单个 `logo-x`，宽图在竖版会自动按宽度缩）。
- 看三张 png：文字没撞贴纸、高亮压在钩子行、品牌标在角上。细则见 `references/delivery-qa.md` 的「封面验收」。

### 6. 出片与验收
- `wb build`。抽 2~3 帧看（`ffmpeg -ss <t> -i final.mp4 -frames:v 1 x.png`）：字幕在底、**跟读高亮压在正念到的那几个字上**（色块紧贴字、不吞标点、不切断 `MiMo` 这类英文词）、水印在右上、贴纸擦出正常；片尾看一眼 `99-brand`。抽帧时**先看原图再下结论**：把几十帧缩成一张长图看，容易把墨色字误判成"没高亮"。
- `wb captions <期>`：不打图就能核对每条字幕的时间、文本，以及高亮分段（`[a·b·c]` 里 `·` 的位置就是色块跳的节拍；每段大致 0.2~0.6 秒算正常）。
- 看 `字幕.srt` 前几条：原文拼写、数字未拆。**SRT 里没有高亮**（纯文本格式装不下），高亮只烧进画面。
- 机器检查与交付边界按 `references/delivery-qa.md`。
- `README.md` 写好，时长以 `ffprobe` 为准。

### 7. 发布文案与标题
- 按 `references/publish.md`：5 个标题候选（数字反差 / 事件主语 / 结论前置 / 生活单位换算 / 提问）选 1 主用；视频号简介、抖音描述（前 55 字钩子 + 话题 3~5 个排最后 + AIGC 标注）、小红书标题+正文+标签、B 站标题、公众号摘要、评论区置顶。
- 数字与 `README.md` 一致；合规自查勾完（`references/compliance.md`）。
- 填 `发布.md`，交付四件套。

## 做长片（>5 分钟）

**代码层面没有时长上限。** 渲染是按场景分段出 mp4、再用 `ffmpeg concat` 拼成 master（`lib/render.js`），场景数不受限；TTS 也是逐场景合成与缓存（`lib/tts-volc.mjs`）。所以「能拍多长」只取决于内容规划，不取决于工具。实测（2026-09-30，plan 域流式端点）：单次提交 2200 字 / 6600 字节（≈6.5 分钟音频）也正常返回，所以即使某一场写得很长也不会卡在接口上。

| 目标时长 | 场景数 | 总字数 | 分幕 |
|---|---|---|---|
| 2~3 分钟 | 6~8 | 500~700 | 不用分幕 |
| 5~10 分钟 | 15~25 | 1200~2400 | 2~3 幕 |
| 15~25 分钟 | 40~60 | 3500~6000 | 3~5 幕 |
| 30~40 分钟 | 75~90 | 7000~9000 | 5~8 幕 |

长片比短片多做的四件事：

1. **分幕。** 每幕开头加一张「章节卡」场景（普通 `new Scene('02-act2', ...)` 就行：画幕标题 + 一句导览），观众才知道自己在哪；发布文案的时间戳也按幕切。片尾卡由工具自动追加，章节卡要手写。
2. **每 2~3 分钟一个呼吸点。** 白板讲解连续 20 分钟会累：呼吸点可以是一句小结、一个踩坑现场、一张对比表。别一路平铺。
3. **配乐改用播放列表。** 一首 2~3 分钟的曲子配 20 分钟的片子要循环十几次，一听就出戏——`config.json` 的 `bgm.playlist` 填几首（`[{ "file": "assets/bgm-1.mp3" }, { "file": "assets/bgm-2.mp3", "trim": [0, 90] }]`），它们会按顺序拼成一整段再整体循环，重复感立刻降下来；playlist 为空时仍走 `bgm.file` 单曲循环。
4. **封面标签别提时长。** `cover.seriesTag` 默认「白板讲清楚」；要强调时长就在 `scenes.js` 的 cover 里按本期实际时长传 `tag`，别在 config 里写死「3 分钟」。

耗时与体积（本机 4 路并行实测 + 外推；1080p30）：

| 时长 | 出帧 | `wb build` 全程 | 成片 + 中间产物 |
|---|---|---|---|
| 2.7 分钟（《DeepSeek Harness 桌面端》实测 8 场景） | ~1.8 分钟 | ~3 分钟 | 12 MB + 24 MB |
| 10 分钟 | ~7 分钟 | ~10 分钟 | ~46 MB + ~90 MB |
| 30 分钟 | ~21 分钟 | ~30 分钟 | ~140 MB + ~270 MB |

> 出帧速度按本机实测 ≈44 帧/秒（4 路并行）折算；体积按实测 ≈4.5 MB/分钟。白板片画面白、运动少，比实拍素材小得多。机器吃紧就把 `render.workers` 降到 2。

**长片一定要用断点续跑**：TTS 与渲染都按场景缓存，改一句旁白或一个场景不必整片重跑——

```bash
wb tts   <期> <场景名>     # 只重配改过的那一幕（缓存命中时几乎瞬时）
wb render <期> <场景名>    # 只重渲这一段，并自动重拼 master
wb mix   <期>              # 出片
```

⚠️ `wb build` 会**整期重渲**（即使 TTS 全命中缓存），长片别拿它做小改动。另外 `wb captions <期>` 在长片上尤其有用：不打图就能逐条核对 90 条字幕的时间与高亮分段。

## 修改类请求怎么接

| 用户说 | 做法 |
|---|---|
| 改某句旁白 / 加一段 | 改 `scenes.js` → `wb build`（只重配改过的场景） |
| 用了假机器人 / 要真 Logo | `wb logo` 取官方 SVG → scenes.js 把 `s.image` 名字换成 `logo-*` → `wb stills` → `wb render && wb mix && wb cover` |
| 换贴纸 / 人物太丑 | `wb image` 重出 → `wb stills` → `wb render && wb mix`（封面用到的话再 `wb cover`） |
| 画得太快/太慢、文字蹦出来 | config `render.pen`：`speed` 描边 px/s、`charSeconds` 每字秒数区间、`minSeconds` 单元素下限、`gapSeconds` 抬笔间隙 → `wb render && wb mix` |
| **画面跟不上旁白**（声音在讲、画还没画完，越到后面越明显） | 先量：`node lib/diag-schedule.mjs <期目录绝对路径>` 逐拍打印「起笔偏移」，> 0.35s 就是落后，且会**累积到后面每一拍**。修法（只动 config）：`render.pen.overflow` 设 `0`（禁掉"一拍画不完就溢到下一拍"）、`speed` 提到 1400~1600、`charSeconds` 上限压到 ~0.14、`fillMaxSeconds` ~0.8、`gapSeconds` ~0.09；再跑一次 diag 复核到 ≤0.1s，最后 `wb render && wb mix`。元素 >20 个的拍会被压缩得明显变快，想更从容就删几个元素（比让整片晚 2~3 秒划算） |
| **字幕与语音对不齐**（小米通道） | `node lib/diag-captions.mjs <期目录绝对路径>` 看「锚定率」与起点偏移。锚定率不是 100% 就是有字幕时间在靠字数插值，来源几乎总是**长小句被 `captions.maxChars` 硬拆**：把 `maxChars` 放大到装得下最长小句（本期 25 字 → 26），或给那句旁白补个逗号让它自然分成两个小句（补标点不改语义，但要重跑 `wb tts`）。细则见 `references/voices-mi.md` |
| 渲染太慢 / 机器吃紧 | config `render.workers`（默认 4 路，每路一个 Chromium；1 = 串行），出帧与路数无关、逐帧一致 |
| 语速快/慢 | config `tts.speed`（默认 1.2）→ `wb build`，全部场景自动重配、字幕同步。⚠️火山是原生变速，**小米是本地 `atempo` 后处理**（接口无语速参数） |
| 换配音引擎（火山 / 小米 / edge） | config `tts.engine` 改 `"volc"` / `"mi"` / `"edge"` → **必须重跑 `wb tts`**：三家音频、语速、停顿都不一样，字幕是跟着音频走的，缓存也按引擎分开。换完跑 `wb voice` 试听 |
| 要更长 / 更短的片子 | 不改代码、不改配置，只改 `scenes.js` 的场景数（按「1 分钟 ≈ 1.5~2 个场景 ≈ 200 字」折算，见「做长片」）→ `wb build`。⚠️这是**重写内容**的活，不是调参：加长就补场景（每场景仍是 3~4 beat），别把现有场景往里灌更多旁白。>5 分钟记得分幕 + 加呼吸点 + 换 `bgm.playlist` |
| 配乐大/小 | config `bgm.gain` → `wb mix`；临时试听 `wb mix <期> 0.4` |
| 字幕字号/位置 | config `captions.fontSize / baselineY` → `wb render && wb mix` |
| 字幕跟读高亮（开关 / 颜色 / 粒度 / 半透明） | config `captions.highlight` → `wb render && wb mix`。`enabled` 关掉就是原来的静态字幕；`color` **留空用品牌色**；`opacity` + `keepHalo:true` 出半透明马克笔效果；`minUnitChars/maxUnitChars` 调粒度（默认 2/4，目标 3 个字）。改完先 `wb captions <期>` 看分段：`[用的是·小米 ·MiMo ·的配音]` 里的 `·` 就是色块依次跳的位置｜字幕文本与 `字幕.srt` 都不受影响 |
| 水印位置/关掉/换 logo | config `brand.watermark.position/enabled`、`brand.logo`（透明底 png）→ `wb render && wb mix` |
| 片尾卡 slogan / CTA / 时长 / 不要 | config `brand.slogan`、`brand.endCard.*` → `wb render <期> 99-brand && wb mix` |
| 封面文案 / 贴纸 / 画幅 | `scenes.js` 末尾 cover 函数 → `wb cover`；画幅 config `cover.ratios`（含抖音用的 9:16），标签 `cover.seriesTag`（`tag: ''` 去掉） |
| 标题 / 发布文案 / 换平台 | 改 `发布.md`，不用重出片 |
| 在 Obsidian 里改了图 | `wb render && wb mix` 直接读 `.excalidraw.md`；增删元素会改逐笔顺序，结构性改动回 `scenes.js` |
| 换声线 / 换曲 | 先 `wb voice` 确认档位，再改各自引擎的音色字段：火山 `tts.voice`（2.0 音色配 `resourceId: seed-tts-2.0`，声音复刻配 `volc.megatts.default`）/ 小米 `tts.mi.voice`（只有九个，见 `references/voices-mi.md`）/ edge `tts.edge.voice`；或 `.env` 的 `VOLC_TTS_VOICE`、`MI_TTS_VOICE` / 配乐改 `bgm.playlist`（多首按序拼接，长片用）或 `assets/bgm.mp3`（单曲循环，换曲先 volumedetect 量电平再定 gain）；临时换曲 `BGM=路径`、临时换列表 `BGM_PLAYLIST='[{...}]'` |
| 配乐固定几首轮播 | config `bgm.playlist` 填 `[{ "file": "...", "trim": [起, 止] }]`；`trim` 省略即整首，`gain` 可逐首配平响度 → `wb mix`。列表非空时 `bgm.file` / `bgm.trim` 被忽略 |
| TTS 报 `Invalid X-Api-Key` / `not granted` | 先怀疑**调用域**不是额度：`ark-` 开头 Key 只走 `plan`，改 config `tts.endpoint`，见 `references/voices-volc.md` 的报错速查 |
| 小米报 `Unknown voice` / `assistant role` / 404 | 三类坑：音色不在九个之内、正文没放在 `assistant` 角色、路径不是 `{baseUrl}/chat/completions`，见 `references/voices-mi.md` 的报错速查 |
| 换账号品牌 | config `brand.name/accent/slogan`，其余不动 |

## 跨平台说明（Windows / macOS / Linux）

平台差异全部收在工具层，写新脚本时照抄下面几条：

- **路径展开**：`lib/paths.cjs`、`lib/scene-dsl.js`、`lib/render.js` 里的 `~` 统一走 `require('os').homedir()`。**别用 `process.env.HOME`**——Git Bash 下它是 MSYS 写法 `/c/Users/x`，Windows 版 Node 会解析成 `C:\c\Users\x` 而 ENOENT。
- **`file://` URL**：Chromium 载入 `render.html` 和本地图片一律用 `require('url').pathToFileURL(p).href`，不要手拼 `file://` + `path.join`（Windows 反斜杠会被当转义）。
- **ffmpeg concat 清单**：写进 `list.txt` 的路径要 `p.replace(/\\/g, '/')`。
- **Chromium**：`lib/chromium.cjs` 的 `resolveChromium()` 在 ms-playwright 里自动取本地最高版本，绕开"Playwright 要的版本本机没有、`npx playwright install` 也装不上"的死路。
- **`npm install` 可能以 exit 1 收尾，但依赖其实装好了**：`postinstall` 跑 `playwright install chromium`，网络下不来 Chromium 时报 `Download failure, code=1`；此时 `node_modules/` 里 playwright / roughjs / lz-string 都已就位，成片照跑。**别为了这个 exit 1 反复重装**；嫌吵就用 `npm install --ignore-scripts`，浏览器反正走 `resolveChromium()`。
- **codex 在 Windows 上只有 `codex.cmd`**，`spawn('codex')` 会 ENOENT；`lib/gen-image.mjs` 的 `resolveCodex()` 会去找 `node_modules/@openai/codex/bin/codex.js` 并用 `process.execPath` 跑。
- **Node 联网**：Commons API 在部分网络下必须经代理，`lib/proxy.mjs` 的 `installProxyFetch()` 给 Node 的 fetch 装一层 HTTPS CONNECT 隧道（读 `HTTPS_PROXY` / `HTTP_PROXY` 环境变量，写进 `.env` 也行；没有配就是空操作）。`lib/fetch-logo.mjs`、`lib/gen-image.mjs` 入口调用它。
- **本地 SVG 转 PNG**：非 Commons 来源的 Logo（如官网 SVG）用 `lib/svg2png.mjs` 过 Playwright 转透明 PNG。
- **`bin/wb`**：`ROOT` 传给 Node 前先 `cygpath -m` 转成 `C:/...`（Git Bash 的 `/c/...` Node 读不了；没有 `cygpath` 就原样传）；`open` 在 Windows 用 `explorer.exe`，Linux 用 `xdg-open`。
- **期目录移出仓库时**：`config.json` 的 `dirs.projects` / `dirs.build` 支持绝对路径（如 `D:/临时/2026/9月/2026年9月29日`），临时改动完记得改回 `./episodes` / `./build`，别把本机绝对路径提交进仓库。另外 `wb new` 生成的 `scenes.js` 会把 `__WB_ROOT__` 替换成仓库绝对路径，但**手拷来的 `scenes.js` 第 4 行的 `require('../../lib/scene-dsl')` 是相对期目录写的，换位置后会 ENOENT**——要么重写成仓库绝对路径（正斜杠），要么用 `wb new` 重建。
- Windows 上用 Git Bash 跑命令；路径含中文或空格记得加引号。

## 已知坑

- Logo：很多官网有验证页拦截，Logo 一律走 Commons API（`wb logo`），别去官网抓图。OpenAI 2025 字标最后的 "I" 就是一根竖条，不是被裁掉；Claude 星芒 SVG 边缘略锯齿，放大到 300 高以内看不出来。
- 火山 TTS 偶尔只返回半段：`tts-volc.mjs` 按逐字数校验自动重试；全量重配 `FORCE_TTS=1`。缓存键含文本+音色+语速+音量+风格+**调用域**，改任一项都会自动重配。
- **火山 TTS 的两个调用域互不相通**（2026-09-29 实测）：控制台发的 `ark-` 开头 API Key 只能走 `plan` 域（`/api/v3/plan/tts/unidirectional`），直购/旧版凭证走 `standard` 域（`/api/v3/tts/unidirectional`）。**打错域报 `45000010 Invalid X-Api-Key`，看着像 Key 错或没额度，其实只是域不对**——先查 `tts.endpoint` 再怀疑凭证。`ark.cn-beijing.volces.com/api/plan/v3` 是方舟另一套（非 TTS）入口，别当 baseURL 拼。音色与 `resourceId` 也必须配套（2.0 音色↔`seed-tts-2.0`），配错报 `55000000 mismatched with speaker`。`lib/tts/tts.mjs` 的 `explainFailure()` 会把这些错翻成可执行的下一步；`wb voice` 可提前自检。
- **画面落后旁白是这套排期的头号同步问题**（2026-09-29 实测，小米通道）：`schedule()`（`lib/render.html`）给每拍的绘制上限是 `limit = 本拍结束 + overflow × 下一拍时长`，而**下一拍的起笔又取 `max(本拍起点, 上一笔结束)`**——所以某一拍画不完就会把后面每一拍一起推后，**误差是累积的**。实测默认参数（`speed:1000 / overflow:0.35`）下最差一拍落后 3.62 秒（旁白已经在讲第三拍，画面还在画第二拍）。修法是**只动 `config.json` 的 `render.pen`**：`overflow: 0` + `speed: 1450` + `charSeconds:[0.05,0.14]` + `fillMaxSeconds: 0.8` + `gapSeconds: 0.09`，实测把最大起笔偏移压到 **+0.07s**。**改完必须量，不能凭感觉**：`node lib/diag-schedule.mjs <期目录绝对路径>` 逐拍打印「起笔偏移／收笔偏移／压缩倍率」，目标每拍起笔偏移 ≤0.35s（`diag-schedule.mjs` 支持 `PEN_OVERRIDE='{...}'` 环境变量传入旧参数做 A/B，不用改 config）。
- **小米 MiMo TTS（`tts.engine: "mi"`）与火山处处不同**（2026-09-29 实测）：① 走 `POST {baseUrl}/chat/completions`，**正文必须放在 `assistant` 角色消息里**（只给 user 报 `messages must contain an assistant role`）；`/audio/speech`、`/tts` 全是 404。② **接口没有语速参数**——顶层 `speed`/`audio.speed`/`audio.speech_rate` 全被忽略（`audio.speed=0.5` 与不传返回**字节完全相同**），`tts.speed` 由本地 `atempo` 后处理实现。③ **不返回逐字时间戳**（`audio.transcript` 恒 null，AI 语音识别模型也只回文本），句子时间靠「标点小句 + `silencedetect` 停顿 + 单调 DP 吸附」估算，实测边界误差约 0.05s、各句语速一致性 CV 0.144；`work/audio/<scene>.json` 的 `align` 字段会标 `silence-estimate`（火山是 `native`）。**小句边界不含顿号**（`ALIGN_VERSION = 3`）：顿号处停顿弱且不稳，实测 28 处里 10 处根本没停顿、DP 只能按字数插值（把小句起点推早 1.16s）；改这个集合要**同时改 `lib/tts/mi.mjs` 的 `clausesOf` 与 `lib/captions.cjs` 的 `PUNCT`/`splitText`**（两边必须逐字一致，否则配对份数不等会整片退化成等比）并 `ALIGN_VERSION +1`。④ 音色固定九个（`mimo_default` / `冰糖` / `茉莉` / `苏打` / `白桦` / `Mia` / `Chloe` / `Milo` / `Dean`），写错报 `Unknown voice` 并在报错里列出全部可选值。⑤ 静音阈值 `-35dB/0.10s` 是**扫出来的最优**，别凭直觉调灵敏（越灵敏语速一致性越差，已复现）。细节见 `references/voices-mi.md`。
- **改旁白后先 `wb scenes` 再 `wb tts`**：`scenes.js` 是手写源，TTS 读的是 `scenes/script.json`（由 `wb scenes` 生成）。只改 `scenes.js` 就直接跑 `wb tts`，**读到的还是旧 script.json**，会误以为"改了没生效"（2026-09-29 踩过）。`wb build` 一条龙里有 `scenes` 那一步，所以走 build 不受影响。
- **验收字幕/画面同步用两个诊断脚本**（都在 `lib/`，不改产物、可反复跑）：
  - `node lib/diag-captions.mjs <期目录绝对路径>`：字幕条数、有声覆盖率、起点偏移中位数、**锚定率**（起点是否正好落在语音小句边界上，100% 为佳）。
  - `node lib/diag-schedule.mjs <期目录绝对路径>`：每拍的旁白窗口 vs 实际绘制窗口、起笔/收笔偏移、压缩倍率。
  两个脚本都**直接吃期目录的绝对路径**（不走 `dirs.projects`），但后台目录仍按 `config.json` 的 `dirs.build` 解析——**跨目录出片时别忘了 `dirs.build` 要和成片实际所在的后台目录一致**，否则量到的是上一次构建的音频（我第一轮诊断就栽在这，白改一轮参数）。
- **字幕的逐字时间戳靠 `enable_subtitle: true`**（火山 2.0/ICL 2.0 音色生效；1.0 音色靠 `enable_timestamp`）。**plan 域复测：关掉 `enable_subtitle` 直接 `words=0`**，字幕会退化成按字数估时间——别为了"省点数据"关它。（小米通道无此开关，它本来就没有时间戳。）
- 字幕文本必须用原文，TTS 词会把 `@grok` 写成 `atgrok`；字幕时间来自 TTS 逐字时间戳，改旁白必须重跑 tts。
- **字幕跟读高亮**（`config captions.highlight`，默认开）改 `render.html` 时注意三件事（2026-09-29 实测）：
  ① **别用 `Range.getBoundingClientRect()` 量 SVG 文本的局部字符区间**——Chromium 只量得出第一个字（"MiMo" 量成 "M"），色块比文字窄一半，高亮段剩下的字被涂成纸色、看起来像**丢了字**。用 `tspan.getExtentOfChar(i)`（返回用户坐标，本页 1:1 就是画布坐标），下标用**码点数** `[...str]`，别用 UTF-16 下标。
  ② **火山的 `wordList` 会吞掉空格**（`用的是小米 MiMo 的配音` 返回成 `...小米MiMo的配音`），拿 `w.word` 拼回去 ≠ 原文；若按逐字节校验就会判"对不上"、整条退化成等比估算，英文字母还会被字数上限切成 `[米 MiM]·[o 的配音]`。`captions.cjs` 的 `wordsToUnits()` 按**非空白字符**对齐、文本取原文切片，就是为了这个。
  ③ **粒度只按字数调，别按"时长太短就并"**——按时长会把原生词边界冲掉（`[小米][MiMo]` 并成 `[米 Mi][Mo 的]`）。火山的词表是**逐字**切的（"字""幕""也""能"…），靠"目标 3 个字"的贪心分组才得到 `[用的是]·[小米]·[MiMo]·[的配音]`。
- SVG dash 在每个子路径 `M` 处重起，rough.js 又双描边：整条 path 一起 dashoffset 会"所有边同时长、每边描两遍"。渲染器已按子路径拆节点、双描边拆 A/B 层，别回退。
- rough.js `toPaths` 不带 dasharray，虚线在 `render.html` 手动设。
- 文本宽度是估算值，居中用 `align:'center'` 才准；左对齐长文本别超 1920。
- Playwright 截图偶发 30s 超时，渲染器带 3 次重试；再挂重跑 `wb render`。
- 不要并发跑 `wb image`：codex 没按指定路径落盘时会兜底抓"最近生成的图"，并发会互相抓错。
- 并行出帧靠两点，别动：`render.html` 的 `seek()` 每帧把底色矩形原地重插，强制整屏重画（否则 Chromium 只重画变化区域，帧会跟出帧顺序有关）；每路单开一个 Chromium。改渲染器后用 `render.workers=1` 和 `4` 各出一遍，`ffmpeg -f framemd5` 对比必须 0 帧不同。
- 用 `require()` 跑 `templates/scenes.js` 会在 templates/ 下生成产物，别这么测；冒烟测试用 `wb new`。
- **渲染耗时看机器**：参考值 2.5 分钟片 4 路并发出帧约 35 秒；本机实测 2 分钟片全量出帧约 82 秒、`wb build` 全程约 2.5 分钟（**即使 TTS 全命中缓存也会整期重渲再 clean**）。改一个场景想省时间用 `wb render <期> <场景>` + `wb mix`。后台长任务不要用 `&`，用运行环境自带的后台运行。
- **3 分钟不是上限，是旧规范**（2026-09-30 核实并改掉）：`lib/render.js` 按场景分段出 mp4 再用 `ffmpeg concat` 拼 master、`lib/tts-volc.mjs` 逐场景合成+缓存，两者都不受场景数约束；「6~8 个场景 / 2~2.5 分钟」原本只是内容建议。实测火山 plan 域**流式**端点单次吃下 2200 字 / 6600 字节（≈6.5 分钟音频）无报错——所以长片不用改代码，加场景即可。真正的代价是**出帧时间（≈44 帧/秒）与磁盘（≈4.5 MB/分钟）**，以及 `wb build` 整期重渲 —— 长片一律用 `wb tts/render <期> <场景>` 断点续跑。⚠️**别在封面标签里写死时长**：默认 `cover.seriesTag` 原来就是「白板 3 分钟讲清楚」，做长片会自相矛盾，已改成「白板讲清楚」；另外 `bgm` 单曲循环配 20 分钟片子会一听就出戏，长片把 `bgm.playlist` 填上（多首按序拼接后整体循环）。
- **`wb build` 的清理步可能被安全钩子拦**：成片已落盘、字幕封面都出完之后，如果清理 `work/frames` 时一次删超过数十个文件，某些 Agent 沙箱会抛 `SAFE_DELETE_BULK_CONFIRM_REQUIRED`。不影响交付，手动清一次或用 `wb clean` 即可。
- **edge-tts 引擎**（`tts.engine: "edge"`）：`lib/tts-edge.py` 读 `work/audio/` 落 `<scene>.mp3` + `<scene>.json`，json 里用 WordBoundary 事件拼出 `wordList`（和火山的逐字时间戳同格式），字幕链路不用改。缓存键含文本+音色+语速，**对不上会自动重配**（强制重配 `FORCE_TTS=1`）。解释器由 `config.json` 的 `tts.edge.python` 指定（指向装好 `edge_tts` 的那个），留空则用 PATH 里的 `python3` / `python`。edge 读不出中文多音字，数字/英文模型名建议在旁白里写成中文读法。
