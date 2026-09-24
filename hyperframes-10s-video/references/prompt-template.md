# 动画视频 + 字幕 · 标准提示词模板（时长 · 配色 · 音频 均可选）

> 用法：新建对话 → 第一行写 `@skill:hyperframes-10s-video` → 下面整段粘贴本模板 → 替换「【输入内容】」那段，并按需勾选【时长】【配色】【音频】→ 发送。
> 输出：1 个横屏 MP4 + 1 个同名 .srt。**时长任意（默认 10s）；配色 10 选 1；音频默认无声，勾选「带语音」即自动跑 TTS 配音并混音。**

---

@skill:hyperframes-10s-video

## 【输入内容】

<在这里粘贴你的一段内容（一句话主张 / 一段短文 / 几个并列要点皆可）>

## 【时长开关】（默认 10 秒，可写任意秒数）

成片总时长：**10 秒**（← 改成你想要的秒数，如 `20 秒`、`45 秒`、`1 分钟`）

- 实现方式：`build_html.mjs ... --total=<秒>`，或在 `scenes.json` 顶层写 `"duration": <秒>`；两种等价，CLI 优先。
- 各幕 `dur` 会按比例归一到该目标（末幕吸收舍入漂移，总时长精确到 0.01s）；单幕下限 0.6s。
- **长片要加幕，不要只拉长单幕**：默认 3 幕=10s；20–30s→4–6 幕；45s→7–8 幕；60s→9–11 幕。拉长会让画面长久静止。
- 不写本项 = 按各幕 `dur` 之和出片。

## 【配色开关】（10 选 1，默认 tech）

配色皮肤：`tech`（深墨科技·默认）/ `wuding`（五鼎雅致）/ `aurora`（极光紫青）/ `sunset`（日落橙粉）/ `ocean`（深海蓝绿）/ `forest`（森野绿）/ `midnight`（午夜蓝紫）/ `gold`（黑金商务）/ `candy`（糖果马卡龙）/ `paper`（素白浅色·浅底深字）。

- 指定方式：填到 `scenes.json` 的 `"skin"`，**或**构建时传 `--skin=<名字>`。
- 未指定则默认 `tech`；也可按内容气质推荐：商务→`gold`、科技→`tech`/`aurora`、清新/文档→`paper`/`forest`、活力→`sunset`/`candy`。
- 配色预览：`references/skin-gallery.html`（10 套同分镜实拍帧）；生成后也可在 HTML 预览页底部下拉框实时切换。

## 【音频开关】（二选一，默认无声）

- **无声（默认）**：不写 `script.json`、不调 TTS，成片无音轨。
- **带语音 / 配音 / 有声版**：写 `script.json`（每幕一句口播 `lines`，条数=幕数），跑 `tts_scenes.py --keep-dur` 生成 `voice.mp3`，再用 ffmpeg 把音轨混进 MP4，交付 `<slug>-1920x1080-30fps-a.mp4`。
  - 口播稿按 **约 4 字/秒** 估：10s ≈ 35 字、45s ≈ 180 字、60s ≈ 240 字。

## 【固定输出要求】

1. 基于上方内容，生成一段 **横屏动画视频，总时长 = 上面设定的秒数**：
   - 分辨率 **1920×1080**、**30fps**、**H.264**、封装 MP4；
   - **无声模式**：无 TTS 配音、无音轨（纯画面）；**有声模式**：带 AAC 音轨（配音来自 TTS）。例外：配音时长无法压缩到目标时会略超，需在交付说明里讲明。
2. 同时输出 **同名 .srt 字幕文件**：用 `make_srt.mjs` 生成，字幕文字与画面显示完全一致，时间轴与画面（无声）或语音（有声）严格对齐。
3. 文件命名：`<主题英文slug>-1920x1080-30fps.mp4` 与 `<主题英文slug>-1920x1080-30fps.srt`（slug 由主题词拼音/英文缩写生成，如 `rsi`）。
4. 工作目录：当前会话目录下的 `<slug>-kinetic-video/` 子目录，中间文件（`_frames` / `_preview` / `<slug>.html`）放其中。

## 【分镜结构】

**默认 3 幕**（总 10s；片头 2.5s + 主体 5s + 收尾 2.5s）。**时长≠10s 时按比例缩放这三段的相对节奏，或增加幕数。**

- **第 1 幕 · 片头（title）**
  - `brand` = 核心主题词（大渐变艺术字，≤12 字）；
  - `title` = 一句话主张 / 主标题（≤14 字）；
  - `sub` = 副文案（≤20 字）；
  - `eyebrow` = 英文小标（如 `AI SELF-EVOLUTION`）。
- **第 2 幕起 · 主体**：按内容形态选 type
  - 含 **2–3 个并列要点** → `free` 幕写三张等宽卡片（`<div style="display:flex;gap:30px"><div class="card" style="flex:1">…</div>×3</div>`），每卡 `ct`（小标题）+ `cd`（一行说明）；**必须 flex:1 保证横屏单行不换行**（不要用 `points` 幕，3 张卡在横屏会折成 2+1）。
  - **单一金句 / 核心词** → `bigword` 或 `quote`。
  - **步骤流程** → `flow`（2–4 步）。
  - **数据对比** → `bars`（数值须真实或标注估算，并写进 `foot`）。
  - **长内容** → 拆成 4–11 幕，每幕一个语义段，别硬塞进 3 幕。
- **末幕 · 收尾（end）**
  - `brand` = 总结短语；`title` = 体系/结论名（≤14 字）；`sub` = 闭环主张（≤20 字）；可选 `cta`。

> 内容没有现成 3 要点时：自己归纳 2–3 个并列维度（是什么 / 为什么 / 怎么做），不要硬凑。

## 【执行步骤（调用技能脚本，按顺序）】

1. 写 `scenes.json`：顶层含 `"skin":"<配色>"`、`"duration":<目标秒数>`、`"badge"`、`"foot"`、`"orient":"landscape"`；`scenes` 数组按上面结构（默认 3 幕）。需要精确字幕的幕可加 `"srt":"第一行\n第二行"`。
2. **IF 带语音**：写 `script.json`（`{"voice":"zh-CN-YunyangNeural","rate":"+0%","lines":[...]}`），跑
   `tts_scenes.py script.json scenes.json <输出目录> --ffmpeg="<本机 ffmpeg>" --keep-dur`
   得到 `voice.mp3` + `scenes_vo.json` + `timing.json`；**后续用 `scenes_vo.json` 作分镜源**（它已含每幕音频对齐时长）。
   （无声模式跳过此步，直接用 `scenes.json`。）
3. `build_html.mjs <分镜源.json> <slug>.html --total=<秒> [--skin=<配色>]` → 生成自包含 HTML，并产出 `<slug>.effective.json`。
4. 抽帧核验：`render.mjs <slug>.html _preview --only=<每幕1帧,末幕靠后1帧> --chrome="<本机 chromium>"`，Read 检查无文字溢出、无页面报错。
5. `render.mjs <slug>.html _frames --chrome="<本机 chromium>"` 全量渲染（`总时长×30` 帧）；长片放后台，必要时 `--start/--end` 分段。
6. `encode.mjs _frames <slug>-1920x1080-30fps.mp4 --ffmpeg="<本机 H.264 ffmpeg>"` 编码成片（无声）。
7. **IF 带语音**：`ffmpeg -y -i <slug>-1920x1080-30fps.mp4 -i voice.mp3 -c:v copy -c:a aac -b:a 192k -shortest <slug>-1920x1080-30fps-a.mp4` 混音，交付用 `-a.mp4`。
8. **生成 .srt**：`make_srt.mjs <分镜源.json> <slug>.srt`
   - 无声加 `--eff=<slug>.effective.json`（与缩放后的画面严格一致）；
   - 有声加 `--timing=timing.json`（与语音逐幕同步）。
9. 用 ffmpeg 读 `Duration` 复核 = 目标秒数（误差 ≤0.02s）、1920×1080、30fps；无声仅 video 流，有声含 AAC audio 流；并确认 `make_srt.mjs` 的「末条结束」等于总时长。

## 【字幕规范】

- 一律用 `make_srt.mjs` 生成，不手写。
- 字幕文字严格等于画面显示文字（无声）或口播文字（有声），不另造。
- 每幕 1 个 cue；副标题/卡片说明多行直接换行写在同一 cue 内。
- 时间码与画面/语音严格对齐；`end` 幕的 `cta` 默认不入字幕，要用就在该幕加 `"srt"`。

## 【收尾】

- 清理 `_frames` / `_preview` / `_seg` / `voice.mp3` / `timing.json` / `scenes_vo.json` 等临时文件，保留 `<slug>.html`（交互预览版）+ MP4（有声版 `-a.mp4`）+ SRT + `<slug>.effective.json`。
- 用 present_files 同时交付 MP4（+ 有声版）与 SRT。

---

## ▶ 已验证的填写范例（AI自我进化 RSI · 10s · tech · 无声）

【输入内容】
> AI自我进化RSI，分为三个核心方向！改代码、论文等产出物，是产物进化；优化提示词、工具、记忆等智能脚手架，是框架进化；自主训练迭代模型参数，是模型进化，三者共同构成AI自主进化体系！

【时长开关】10 秒 ｜【配色开关】tech ｜【音频开关】无声

落地产物（实测）：
- `rsi-1920x1080-30fps.mp4`（10.00s，1920×1080，30fps，H.264，无音轨）
- `rsi-1920x1080-30fps.srt`（3 cue：片头 / 三卡 / 收尾，与画面一致）

`scenes.json` 关键结构（`duration` 已写、每幕带 `srt` 覆盖以保证字幕精确）：
```json
{"skin":"tech","badge":"AI进化 · RSI","orient":"landscape","duration":10,
 "scenes":[
   {"type":"title","dur":2.5,"eyebrow":"AI SELF-EVOLUTION","brand":"AI自我进化 · RSI","title":"自主进化三引擎","sub":"产物 · 框架 · 模型，一起转",
    "srt":"AI自我进化 · RSI\n自主进化三引擎\n产物 · 框架 · 模型，一起转"},
   {"type":"free","dur":5,
    "srt":"三个核心方向，一起转\n产物进化：改代码、写论文\n框架进化：优化提示词、工具、记忆\n模型进化：自主训练迭代模型参数",
    "html":"<h2 class=\"h\">三个核心方向，一起转</h2><div style=\"display:flex;gap:30px;margin-top:22px\"><div class=\"card\" style=\"flex:1\"><div class=\"ct\">产物进化</div><div class=\"cd\">改代码、写论文<br>产出物越做越强</div></div><div class=\"card\" style=\"flex:1\"><div class=\"ct\">框架进化</div><div class=\"cd\">优化提示词、工具、记忆<br>智能脚手架持续升级</div></div><div class=\"card\" style=\"flex:1\"><div class=\"ct\">模型进化</div><div class=\"cd\">自主训练迭代<br>模型参数自我完善</div></div></div>"},
   {"type":"end","dur":2.5,"eyebrow":"AI SELF-EVOLUTION","brand":"三位一体","title":"AI自主进化体系","sub":"产物 + 框架 + 模型，闭环驱动","cta":"关注 AI进化 · RSI",
    "srt":"三位一体 · AI自主进化体系\n产物 + 框架 + 模型，闭环驱动"}
 ]}
```

**改成 20 秒**只需两步：① `scenes.json` 里把 `"duration"` 改 20（或构建时加 `--total=20`）；② `make_srt.mjs` 带上 `--eff=<slug>.effective.json`。分镜不动，时间码自动重算。

SRT（10s 版，由 `make_srt.mjs` 产出，与本文件同源）：
```
1
00:00:00,000 --> 00:00:02,500
AI自我进化 · RSI
自主进化三引擎
产物 · 框架 · 模型，一起转

2
00:00:02,500 --> 00:00:07,500
三个核心方向，一起转
产物进化：改代码、写论文
框架进化：优化提示词、工具、记忆
模型进化：自主训练迭代模型参数

3
00:00:07,500 --> 00:00:10,000
三位一体 · AI自主进化体系
产物 + 框架 + 模型，闭环驱动
```
