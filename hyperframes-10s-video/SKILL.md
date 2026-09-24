---
name: hyperframes-10s-video
display_name: "HyperFrames 动画视频（时长/配色/音频 全参数化）"
display_name_en: "HyperFrames Kinetic Video (duration / skin / audio configurable)"
description_zh: |
  基于 HyperFrames 风格（声明式分镜 → HTML+GSAP → 无头 Chromium 逐帧渲染 → ffmpeg H.264）的一键动画视频技能。把「一段内容」变成横屏（1920×1080、30fps、H.264）动画视频，并自动输出同名 .srt 字幕。**时长可参数化**：默认 10 秒，用 `--total=<秒>` 或在 scenes.json 顶层写 `"duration": 15` 即可输出任意时长（各幕 dur 按比例精确归一），长片建议写 5–11 幕；且时长不再写死。**配色 10 套可选**（tech/wuding/aurora/sunset/ocean/forest/midnight/gold/candy/paper），经 `skin` 字段或 `--skin=` 指定，附可视化配色画廊。音频**可选**：默认无声（无音轨）；当用户要求「带语音/配音/有声」或 scenes.json 置 `"audio":true` 时自动跑 TTS（edge-tts）混音进 MP4。当用户说「生成 N 秒视频」「做一段口播动画」「视频+字幕」「用 HyperFrames 风格出个短视频」「带配音的口播」「换个配色/风格」「视频再长一点/短一点」时触发。
description_en: |
  HyperFrames-style (declarative scenes → HTML+GSAP → headless Chromium frame capture → ffmpeg H.264) one-shot kinetic video skill. Turns content into a landscape (1920×1080, 30fps, H.264) animation video plus a matching .srt subtitle. **Duration is parameterized**: 10s by default, but `--total=<seconds>` or a top-level `"duration": 15` in scenes.json yields any length (scene durations are proportionally normalized to hit the target exactly); use 5–11 scenes for long pieces. Ships 10 selectable color skins (tech/wuding/aurora/sunset/ocean/forest/midnight/gold/candy/paper) via the `skin` field or `--skin=`, with a visual skin gallery. Audio is OPTIONAL: silent (no track) by default; when the user asks for "voiceover / with audio / 带配音" or sets "audio":true, it runs TTS (edge-tts) and muxes the voice in. Trigger on "make an N-second video", "kinetic video + subtitles", "HyperFrames clip", "voiced narration", "switch the color theme", "make it longer/shorter".
version: 2.0.0
agent_created: true
license: MIT
category: design
platforms:
- WorkBuddy
---

# HyperFrames · 动画视频 + 字幕（时长 / 配色 / 音频 全参数化）

> **定位**：HyperFrames 风格的声明式动画视频流水线。思路——把「分镜结构 + 每幕动作」写进 `scenes.json`，由 GSAP 按时间轴执行，无头 Chromium 逐帧截图，ffmpeg 收成 H.264 MP4；再由 `make_srt.mjs` 按同一分镜自动生成同名 SRT 字幕。
> **时长可参数化**：默认 **10 秒**，但**不写死**——`--total=<秒>` 或 `scenes.json` 顶层 `"duration": N` 可产任意时长（比例归一，精确到 0.01s）。
> **音频可开关**：默认**无声**（纯画面 + 字幕）；开启后跑 `tts_scenes.py`（edge-tts）生成整轨配音并混音进 MP4，字幕改用语音时间轴对齐。是否发声由调用时决定，**不写死**。
> **配色可选**：内置 **10 套皮肤**，用 `scenes.json` 的 `"skin"` 字段或构建时 `--skin=` 选择；同一分镜换肤即换风格，见下「配色皮肤」。

## ⏱️ 时长参数（默认 10s，可任意）

| 想要 | 怎么给 | 行为 |
|---|---|---|
| **默认 10 秒** | 什么都不写 | 各幕 `dur` 之和即总时长 |
| **指定总时长** | `build_html.mjs scenes.json out.html --total=20` | 各幕 `dur` 按比例缩放，总和**精确等于** 20.00s |
| **写进配置** | `scenes.json` 顶层 `"duration": 15` | 同上（CLI `--total` 优先于该字段） |
| **分幕自定** | 直接写每幕 `dur`（和即总时长） | 与目标差 ≤0.05s 时不缩放；否则归一 |

- 归一算法：`scale = 目标 / Σdur`，逐幕 `dur × scale` 保留 2 位小数，末幕吸收舍入漂移，保证总和精确等于目标；单幕下限 `0.6s`（装不下会告警并按最小值铺满）。
- 帧数 = `总时长 × fps`（默认 30fps，可 `--fps=60`）。
- **长片建议**：不要靠拉伸 3 幕凑时长（内容会长久静止），而是**增加幕数**——30s→5–6 幕、45s→7–8 幕、60s→9–11 幕（见 `references/scenes_schema.md` 末尾「时长建议」表）。
- `build_html.mjs` 会顺带写出 `<slug>.effective.json`（生效分镜，含缩放后的真实 dur/start），字幕与画面同源，务必用它喂给 `make_srt.mjs`。

## 🎨 配色皮肤（10 套可选）

| 皮肤名 | 风格 | 主色 c1 / c2 / c3 |
|---|---|---|
| `tech` | 深墨科技（默认） | 薄荷 `#2FE3C7` · 天蓝 `#38BDF8` · 珊瑚 `#F7A66A` |
| `wuding` | 五鼎雅致 | 松绿 `#56A989` · 暖橙 `#F2A979` · 米金 `#E8D9A0` |
| `aurora` | 极光紫青 | 紫罗兰 `#8B7CFF` · 青绿 `#35E0D0` · 粉 `#FF8FD0` |
| `sunset` | 日落橙粉 | 橘橙 `#FF8A5B` · 玫红 `#FF5C8A` · 暖金 `#FFD166` |
| `ocean` | 深海蓝绿 | 青绿 `#38D6C4` · 宝蓝 `#2E8BFF` · 浅青 `#7FE3FF` |
| `forest` | 森野绿 | 嫩绿 `#7BD389` · 翡翠 `#35C0A0` · 黄绿 `#D9E8A0` |
| `midnight` | 午夜蓝紫 | 靛蓝 `#6C8CFF` · 紫 `#9B6CFF` · 天青 `#4FD1FF` |
| `gold` | 黑金商务 | 香槟金 `#E9C46A` · 琥珀 `#F4A261` · 米驼 `#D9B08C` |
| `candy` | 糖果马卡龙 | 桃粉 `#FF7EB6` · 天蓝 `#7ED8FF` · 奶黄 `#FFE08A` |
| `paper` | 素白浅色（浅底深字） | 品牌蓝 `#2569AB` · 青绿 `#12A48E` · 橘 `#E67E22` |

**怎么选**（任选其一，互不冲突）：
1. `scenes.json` 顶层写 `"skin":"aurora"`；
2. 构建时传参：`node build_html.mjs scenes.json out.html --skin=aurora`（CLI 优先，未知皮肤自动回退 `tech` 并告警）；
3. 生成后打开 `<slug>.html`，用底部控制条最右侧的**配色下拉框**实时预览切换（仅预览，不影响渲染；渲染走 `capture=1` 不显示控制条）。

> 可视化挑色：`references/skin-gallery.html`（同一 RSI 分镜的 10 套配色实拍帧，双击即看）。
> 浅色皮肤 `paper` 适合白底/打印/文档场景，其余为深色主题；皮肤只改 CSS 变量，不影响分镜与动效。

## 🔀 音频开关（调用时决定）

| 想要 | 怎么触发 | 行为 |
|---|---|---|
| **无声**（默认） | 只说「生成 10 秒视频 + 字幕」，或 scenes.json 无 `"audio"` / `"audio":false` | 不调 TTS、成片无音轨、SRT 按分镜 dur 切分 |
| **有声 / 配音** | 说「带语音」「配音」「有声版」，或 scenes.json 置 `"audio":true` | 写 `script.json`（每幕一句口播）→ 跑 TTS → 混音进 MP4 → SRT 按语音时间轴对齐 |

> 有声模式下，用 `tts_scenes.py --keep-dur` 把每幕配音补到该幕在 `scenes.json` 写明的 `dur`，从而**保持总时长 ≈ 原目标（如 10.0s）**；仅当某幕语音本身比 `dur` 还长时才放宽该幕（总时长略超，会在日志告警）。

## 🚀 一句话 SOP（接到指令即跑）

0. **判定音频模式**：用户要「带语音/配音」或 scenes 含 `"audio":true` → `AUDIO=on`；否则 `AUDIO=off`。
0.2 **判定时长**：用户说了秒数（「20 秒」「半分钟」「1 分钟」）→ `TOTAL=<秒>`；没说 → 默认 10。长片（>20s）建议同步把幕数加到 5–11 幕，别只拉伸 3 幕。
0.5 **判定配色**：用户指定了风格/皮肤名 → 用该 skin；未指定则默认 `tech`（也可按内容气质推荐：商务→`gold`、科技/未来→`tech`/`aurora`、清新/文档→`paper`/`forest`、活力→`sunset`/`candy`）。写进 `scenes.json` 的 `"skin"`，或构建时 `--skin=` 覆盖。
1. **拆幕写 `scenes.json`**：把内容映射到 N 幕（默认 3 幕，见下「内容→分镜」）。各幕 `dur` 可先按内容节奏写相对值，总时长交给 `--total` 归一即可（**不再硬锁 10 秒**）。有声模式用 `--keep-dur` 尽量贴合 `TOTAL`。
2. **IF `AUDIO=on`**：写 `script.json`（`voice`/`rate` + 每幕一句口播 `lines`，条数 = 幕数），跑 TTS 得到 `voice.mp3` + `scenes_vo.json` + `timing.json`，后续用 `scenes_vo.json` 作为分镜源：
   ```powershell
   python C:\Users\wwwzh\.workbuddy\binaries\python\envs\default\Scripts\python.exe `
     C:\Users\wwwzh\.workbuddy\skills\hyperframes-10s-video\scripts\tts_scenes.py `
     script.json scenes.json <输出目录> --ffmpeg="D:\Program Files\ffmpeg-6.1.1-full_build\bin\ffmpeg.exe" --keep-dur
   ```
   （可选 `--voice=zh-CN-YunyangNeural --rate=+0%`；`script.json` 里的同名字段优先级相同，CLI 覆盖。）
3. **构建 HTML**（无声用 `scenes.json`，有声用 `scenes_vo.json`；**可传 `--skin=<皮肤>` 与 `--total=<秒>`**）：
   ```powershell
   node C:\Users\wwwzh\.workbuddy\binaries\node\versions\22.22.2-3\node.exe `
     C:\Users\wwwzh\.workbuddy\skills\hyperframes-10s-video\scripts\build_html.mjs `
     <分镜源.json> <输出目录>\<slug>.html [--skin=aurora] [--total=20]
   ```
   日志会打印「时长归一：10.00s → 20s（逐幕 …）」并产出 `<slug>.effective.json`（**字幕必须用这份**）。
4. **抽帧验证**（必做其一）：`render.mjs <slug>.html _preview --only=36,135,255 --chrome="<chromium>"` 或 `check_overflow.mjs <slug>.html`。核验各幕无溢出、无报错（幕数多时按 `总帧数/N` 取样，每幕至少 1 帧；末幕补验 `总帧数-10` 附近，避免抽到淡出帧）。
5. **全量渲染**（`总时长×fps` 帧，放后台；>30s 建议按 `--start/--end` 分段）：`render.mjs <slug>.html _frames --chrome="<chromium>"`。
6. **编码 MP4**（无声成片）：
   ```powershell
   node ...\scripts\encode.mjs _frames <slug>-1920x1080-30fps.mp4 --ffmpeg="D:\Program Files\ffmpeg-6.1.1-full_build\bin\ffmpeg.exe"
   ```
7. **IF `AUDIO=on`**：把配音混进成片（音轨用 AAC）：
   ```powershell
   & "D:\Program Files\ffmpeg-6.1.1-full_build\bin\ffmpeg.exe" -y -i <slug>-1920x1080-30fps.mp4 -i voice.mp3 `
     -c:v copy -c:a aac -b:a 192k -shortest <slug>-1920x1080-30fps-a.mp4
   ```
   交付用 `<slug>-1920x1080-30fps-a.mp4`，无声版一并保留亦可。
8. **写 SRT（用脚本，不手写）**——自动按分镜/语音时间轴切分，文字 = 画面实际显示（或口播）文字：
   ```powershell
   node C:\Users\wwwzh\.workbuddy\binaries\node\versions\22.22.2-3\node.exe `
     C:\Users\wwwzh\.workbuddy\skills\hyperframes-10s-video\scripts\make_srt.mjs `
     <分镜源.json> <输出目录>\<slug>.srt [--eff=<输出目录>\<slug>.effective.json] [--timing=<输出目录>\timing.json]
   ```
   - 无声：传 `--eff=`（build 产出的生效分镜）→ 时间码与缩放后的画面严格一致。
   - 有声：传 `--timing=timing.json` → 与语音逐幕同步。
   - 想精确控制某幕字幕 → 在该幕加 `"srt": "第一行\n第二行"`（字段里写死，优先于自动抽取）；`end` 幕的 `cta` 默认不入字幕，需要时也用 `srt` 加上。
9. **复核 + 记录时间**：ffmpeg 读 `Duration`，须 = `TOTAL`（无声误差 ≤0.02s）且无声仅 video 流 / 有声含 audio 流（AAC），分辨率与 fps 与 `--orient`/`--fps` 一致；`make_srt.mjs` 打印的「末条结束」须等于总时长；把生成起止时间写入 `<输出目录>\gen-log.txt`。
10. **交付**：`present_files` 交 MP4（+ 有声版 `-a.mp4`）+ SRT（HTML 预览版可一并给出）。

**node 路径固定用**：`C:\Users\wwwzh\.workbuddy\binaries\node\versions\22.22.2-3\node.exe`
**python（TTS 用）**：`C:\Users\wwwzh\.workbuddy\binaries\python\envs\default\Scripts\python.exe`（已装 `edge_tts`）
**chromium**：render/check_overflow 自动探测当前用户 `AppData\Local\ms-playwright\chromium-*`（取最高版本），也可 `--chrome=` 指定或用 Edge。
**ffmpeg（H.264）**：`D:\Program Files\ffmpeg-6.1.1-full_build\bin\ffmpeg.exe`。⚠️ Playwright 自带 `ffmpeg-win64.exe` 只有 webm，**不能**出 H.264 MP4。

## 默认结构：3 幕（2.5 / 5 / 2.5）= 10 秒

> 这是**默认节奏**（不传 `--total` 时）；时长可任意，见上「时长参数」。

| 幕 | type | dur | 内容 |
|---|---|---|---|
| 1 片头 | `title` | 2.5s | `brand`=核心主题词（≤12字）/`title`=一句主张（≤14字）/`sub`=副文案（≤20字）/`eyebrow`=英文小标 |
| 2 主体 | `free`(三卡) 或 `bigword`/`quote`/`flow` | 5s | 2–3 个并列要点 → 用 `free` 写三张等宽卡片（见下）；单一金句 → `bigword`/`quote`；步骤 → `flow` |
| 3 收尾 | `end` | 2.5s | `brand`=总结短语/`title`=体系名（≤14字）/`sub`=闭环主张（≤20字）/可选 `cta` |

**做长片怎么加幕**（推荐按内容节奏写绝对秒数，总和即目标；或先写相对值再 `--total` 归一）：

| 成片目标 | 建议幕数 | 单幕时长 |
|---|---|---|
| 10s 快闪（默认） | 3 | 2.5 / 5 / 2.5 |
| 20–30s 讲解 | 4–6 | 4–6s |
| 45s 标准讲解 | 7–8 | 4.5–7s |
| 60s 深度 | 9–11 | 5–6s |
| 60–80s 配音版 | 8–9 | 以 audio 时长 + 1s 留白为锚 |

> 三卡必须用 `<div style="display:flex;gap:30px"><div class="card" style="flex:1">…</div>×3</div>`，**flex:1 保证横屏单行不换行**（不要用 `points` 幕，3 张卡在横屏会折成 2+1）。
> 内容没有现成 3 要点时：自己归纳 2–3 个并列维度（是什么/为什么/怎么做，或 产物/框架/模型 这类三元结构），不要硬凑。

## 内容 → 分镜映射规则

- 输入是一段短文/主张 → 抽核心主题词作 `brand`，主张作 `title`，起承句作 `sub`，结尾收束作 `end`。
- 输入含并列要点 → 主体用三卡，`ct`（小标题）+ `cd`（一行说明）。
- 长输入 → 先切成 4–11 个语义段落，每段一幕（`flow` 讲步骤、`points` 讲并列、`quote`/`bigword` 讲金句、`bars` 讲数据），别把长内容硬塞进 3 幕。
- **有声模式写 `script.json`**：每幕一句 `lines`（可等于该幕画面文字，也可改写成更口语的口播稿），条数必须与幕数一致，否则 TTS 按较小值对齐并告警。
- 完整字段与示例 → `references/scenes_schema.md`；标准提示词模板 → `references/prompt-template.md`；RSI 范例 → `references/example-rsi/`；配色画廊 → `references/skin-gallery.html`。

## SRT 规范

- **一律用 `scripts/make_srt.mjs` 生成，不手写**（长片手写必错）。
- 字幕文字严格等于画面显示文字（无声）或口播文字（有声），不另造。
- 每幕 1 个 cue；副标题/卡片说明多行直接换行写在同一 cue 内。
- 时间码 `HH:MM:SS,mmm`，与画面/语音严格对齐：
  - 无声 → `--eff=<slug>.effective.json`（build 产出的生效分镜，含缩放后的真实 dur/start）
  - 有声 → `--timing=timing.json`（与语音逐幕同步）
  - 兜底 → 按 scenes 的 `dur` 累加（可带 `--total` 复现同样的归一）
- 想精确改写某幕字幕 → 该幕加 `"srt": "第一行\n第二行"`（优先于自动抽取）；`end` 幕的 `cta` 默认不入字幕，要用 `srt` 显式加。
- 自动抽取规则：`title`→brand/title/sub｜`end`→brand/title/sub｜`bigword`→eyebrow/word/note｜`typewriter`→head/text/note｜`quote`→text/by｜`flow`/`points`→head + 逐项「标题：说明」｜`bars`→head + 「标签 值后缀」｜`free`→优先取 `.h` 标题 + 各 `.ct：.cd` 首行，否则去标签取全文。

## 铁律

1. **逐帧确定性渲染**：渲染走 `window.__KINETIC__.seek(t)`（GSAP timeline pause+seek），不依赖真实播放速度——机器再慢也不掉帧。
2. **先抽帧后全量**：全量渲染前必看 `_preview` 静帧或跑 `check_overflow`。
3. **时长参数化、不写死**：默认 10.0s；`--total=<秒>` 或顶层 `"duration"` 可产任意时长（比例归一，精确到 0.01s）。长片靠**加幕**而非拉长单幕。
4. **音频可选、不写死**：默认无声、无音轨；仅当明确要求配音或 `"audio":true` 才调 `tts_scenes.py` 并混音。有声版交付 `<slug>-1920x1080-30fps-a.mp4`。
5. **SRT 必出且用脚本生成**：`make_srt.mjs` 产出同名 `.srt`，无声用 `--eff`、有声用 `--timing`；末条结束时间码须等于成片总时长。
6. **不造伪数据**：`bars` 数值必须真实或明确标注估算，非实测写进 `foot` 声明。
7. **记录生成时间**：每次生成把起止时间戳写入 `gen-log.txt`（含各阶段耗时）。
8. **配色可选、不写死**：默认 `tech`；用户指定皮肤名或内容气质匹配时换 skin，换肤不改分镜与时长。

## 常见坑

- **时长归一后要重新核验抽帧**：各幕 `dur` 变了，文字溢出风险随之变化（尤其压缩到 <8s 时）。
- **`--eff` 必须用同一份**：字幕若不用 `build_html.mjs` 产出的 `<slug>.effective.json`，而是自己按原 `dur` 累加，会出现字幕与画面错位（缩放后 dur 不同）。
- **长片渲染耗时线性增长**：10s ≈ 2 分钟，60s ≈ 12 分钟；>30s 建议用 `render.mjs --start/--end` 分段跑，避免后台被 kill。
- **字体**：Windows 无 PingFang SC，模板已回退 Microsoft YaHei。
- **配色皮肤**：皮肤只改 CSS 变量，不动分镜/动效；`paper` 为浅底深字，若在自定义场景 HTML 里硬编码了浅色文字需改用 `var(--fg)`/`var(--muted)`。**新增皮肤**三步：① `assets/template.html` 加一段 `html[data-skin="名字"]{ --bg/--bg2/--c1/--c2/--c3/--fg/--muted/--line/--panel }`；② 同步 `scripts/build_html.mjs` 与 `scripts/build_skin_gallery.mjs` 里的 `SKINS` 数组；③ 用 `build_skin_gallery.mjs` 重生成画廊。
- **jpg 序列编码**：帧文件名固定 `f%05d.jpg`，ffmpeg 用 `-framerate <fps> -i f%05d.jpg`（fps 与渲染一致，默认 30）。
- **TTS 缓存**：`tts_scenes.py` 有 `_seg/` 分段缓存，改文案/voice/rate 后须先 `rm -rf _seg voice.mp3 scenes_vo.json timing.json` 再重跑，否则不生效。
- **混音音画对齐**：有声模式务必用 `--keep-dur`，否则各幕时长被语音长度重算，可能偏离目标；口播稿按 **约 4 字/秒** 估算，10s ≈ 35 字内、60s ≈ 240 字左右。
- **临时帧目录**（`_frames`/`_preview`/`_seg`，约 20MB/秒视频）交付后可删，保留 `HTML+MP4(+`-a`)+SRT+effective.json` 即可复改。
