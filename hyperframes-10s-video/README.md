# HyperFrames 动画视频 Skill

> 把**一段文字**变成**一支动画视频 + 一份同名字幕**。
> 声明式分镜（`scenes.json`）→ HTML + GSAP → 无头 Chromium 逐帧截图 → ffmpeg 收成 H.264 MP4，字幕由同一份分镜自动生成，永不错位。

**三个可调维度**：⏱️ 时长（任意秒） · 🎨 配色（10 套皮肤） · 🔊 声音（无声 / AI 配音）

默认输出：**10 秒 · 1920×1080 · 30fps · H.264 · 无声 · 带 SRT 字幕**。

---

## 目录

- [30 秒上手](#30-秒上手)
- [用法一：在对话里调用（推荐）](#用法一在对话里调用推荐)
- [用法二：命令行直接跑](#用法二命令行直接跑)
- [参数速查](#参数速查)
- [scenes.json 怎么写](#scenesjson-怎么写)
- [三种常用配方](#三种常用配方)
- [脚本清单](#脚本清单)
- [输出文件说明](#输出文件说明)
- [常见坑 / FAQ](#常见坑--faq)
- [环境依赖](#环境依赖)

---

## 30 秒上手

在任意对话里写：

```
@skill:hyperframes-10s-video 生成一段 10 秒视频

内容：AI自我进化RSI，分为三个核心方向！改代码、论文等产出物，是产物进化；
优化提示词、工具、记忆等智能脚手架，是框架进化；
自主训练迭代模型参数，是模型进化。三者共同构成AI自主进化体系！
```

技能会自动：拆成 3 幕分镜 → 构建动画页 → 抽帧核验 → 逐帧渲染 → 编码 MP4 → 生成同名 SRT → 交付。

**要改需求？直接在话里说就行**，不用记参数：

| 你说 | 得到 |
|---|---|
| 「生成 **20 秒**视频」 | 20.00s 成片（幕数不够会自动加幕） |
| 「用 **candy**（糖果）风格」 | 换配色，分镜不动 |
| 「**带语音**的口播视频」 | AI 配音 + 混音，字幕按语音时间轴对齐 |
| 「竖屏版」 | 1080×1920 |

---

## 用法一：在对话里调用（推荐）

```
@skill:hyperframes-10s-video <你想生成的描述>
```

技能内置了标准提示词模板，也可以整段粘贴（见 `references/prompt-template.md`）：

```
@skill:hyperframes-10s-video

## 【输入内容】
<粘贴你的一段内容>

## 【时长】
10 秒

## 【配色】
自动 / tech / candy / paper …

## 【音频】
无声 / 带语音

## 【固定输出要求】
1. 横屏 1920×1080、30fps、H.264 MP4，时长见上；
2. 同时输出同名 .srt 字幕；
3. 生成后记录起止时间到 gen-log.txt。
```

---

## 用法二：命令行直接跑

技能目录里有一套独立可跑的脚本，不依赖对话：

```bash
SK="C:/Users/wwwzh/.workbuddy/skills/hyperframes-10s-video"
NODE="C:/Users/wwwzh/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"
FFMPEG="D:/Program Files/ffmpeg-6.1.1-full_build/bin/ffmpeg.exe"
CHROME="C:/Users/wwwzh/AppData/Local/ms-playwright/chromium-1243/chrome-win64/chrome.exe"

# 1) 构建动画 HTML（指定 20 秒 + candy 配色）
"$NODE" "$SK/scripts/build_html.mjs" scenes.json out.html --total=20 --skin=candy

# 2) 抽帧核验（每幕看一眼，无溢出再全量）
"$NODE" "$SK/scripts/render.mjs" out.html _preview --only=60,240,500 --chrome="$CHROME"

# 3) 全量渲染（总时长 × fps 帧）
"$NODE" "$SK/scripts/render.mjs" out.html _frames --chrome="$CHROME"

# 4) 编码成 MP4
"$NODE" "$SK/scripts/encode.mjs" _frames out-1920x1080-30fps.mp4 --ffmpeg="$FFMPEG"

# 5) 生成字幕（用 build 产出的 .effective.json，保证与画面同源）
"$NODE" "$SK/scripts/make_srt.mjs" scenes.json out-1920x1080-30fps.srt --eff=out.effective.json
```

> 想出声？中间插一步 TTS，见 [配方二](#配方二20-秒--带-ai-配音)。

---

## 参数速查

### 时长（默认 10s）

| 想要 | 怎么给 |
|---|---|
| 默认 10 秒 | 什么都不写 |
| 指定总时长 | `build_html.mjs scenes.json out.html --total=20` |
| 写进配置 | `scenes.json` 顶层 `"duration": 15`（CLI `--total` 优先） |
| 分幕自定 | 直接写每幕 `dur`，和即总时长 |

- 归一算法：各幕 `dur × (目标 / Σdur)`，保留 2 位小数，末幕吸收舍入漂移 → **总和精确等于目标**。
- 单幕下限 `0.6s`；帧数 = `总时长 × fps`。
- **长片靠「加幕」不靠「拉长单幕」**：30s→5–6 幕、45s→7–8 幕、60s→9–11 幕。

### 配色（10 套）

| 皮肤 | 风格 | 皮肤 | 风格 |
|---|---|---|---|
| `tech` | 深墨科技（默认） | `forest` | 森野绿 |
| `wuding` | 五鼎雅致 | `midnight` | 午夜蓝紫 |
| `aurora` | 极光紫青 | `gold` | 黑金商务 |
| `sunset` | 日落橙粉 | `candy` | 糖果马卡龙 |
| `ocean` | 深海蓝绿 | `paper` | 素白浅色（浅底深字） |

三种选法（任选）：`scenes.json` 写 `"skin":"aurora"` ／ 构建传 `--skin=aurora`（未知值回退 `tech` 并告警）／ 打开 HTML 用底部下拉框**实时预览**切换（仅预览，不影响渲染）。
挑色看画廊：`references/skin-gallery.html`（同一分镜 10 套配色实拍帧并排）。

### 音频

| 模式 | 触发 | 结果 |
|---|---|---|
| **无声**（默认） | 不提 / `"audio":false` | 无音轨，SRT 按分镜切 |
| **有声** | 说「带语音/配音」，或 `"audio":true` | AI 配音 + AAC 混音，SRT 按语音时间轴对齐 |

### 其他

| 参数 | 说明 | 默认 |
|---|---|---|
| `--orient=portrait` | 竖屏 1080×1920 | `landscape` 1920×1080 |
| `--fps=60` | 帧率（只改帧数不改时长） | `30` |
| `--badge=xxx` | 右上角标 | `海老豹666` |
| `--foot=yyy` | 底部声明小字（数据来源等） | 空 |
| `--crf=18` | 编码质量（越小越清晰） | `20` |
| `--quality=80` | 截图 JPEG 质量（提速） | `92` |

---

## scenes.json 怎么写

最小示例（3 幕 / 10 秒 / 无声）：

```json
{
  "skin": "candy",
  "badge": "AI进化 · RSI",
  "foot": "AI自我进化 RSI｜产物 · 框架 · 模型 三位一体",
  "orient": "landscape",
  "duration": 10,
  "scenes": [
    { "type": "title", "dur": 2.5,
      "eyebrow": "AI SELF-EVOLUTION",
      "brand": "AI自我进化 · RSI",
      "title": "自主进化三引擎",
      "sub": "产物 · 框架 · 模型，一起转" },

    { "type": "bigword", "dur": 5,
      "eyebrow": "CORE",
      "word": "自我进化",
      "note": "三个方向，一起转" },

    { "type": "end", "dur": 2.5,
      "brand": "三位一体",
      "title": "AI自主进化体系",
      "sub": "产物 + 框架 + 模型，闭环驱动",
      "cta": "关注 AI进化 · RSI" }
  ]
}
```

**常用场景类型**（完整定义见 `references/scenes_schema.md`）：

| type | 用途 | 主要字段 |
|---|---|---|
| `title` | 片头 | `eyebrow` / `brand` / `title` / `sub` |
| `end` | 收尾 | `brand` / `title` / `sub` / `cta` |
| `bigword` | 超大金句 | `eyebrow` / `word` / `note` |
| `quote` | 引用 | `text` / `by` |
| `flow` | 步骤流程 | `head` + `items[]` |
| `points` | 并列要点 | `head` + `items[]`（**横屏 3 张卡会折行，三卡请用 `free`**） |
| `bars` | 数据条形 | `head` + `items[]`（数值须真实，否则在 `foot` 声明估算） |
| `typewriter` | 打字机 | `head` / `text` / `note` |
| `free` | 自由 HTML | `html`（写任意标签，配模板的 `.card` / `.ic` / `.ct` / `.cd` 类） |

> 三卡布局必须写成 `<div style="display:flex;gap:30px"><div class="card" style="flex:1">…</div>×3</div>`，`flex:1` 才能保证横屏单行不换行。

**每幕可选 `srt` 字段**：想精确控制该幕字幕就写 `"srt": "第一行\n第二行"`，优先于自动抽取。

---

## 三种常用配方

### 配方一：10 秒 · 无声 · 带字幕（最快）

```bash
NODE="C:/Users/wwwzh/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"
SK="C:/Users/wwwzh/.workbuddy/skills/hyperframes-10s-video"

"$NODE" "$SK/scripts/build_html.mjs"  scenes.json  out.html
"$NODE" "$SK/scripts/render.mjs"      out.html  _frames --chrome="$CHROME"
"$NODE" "$SK/scripts/encode.mjs"      _frames   out-1920x1080-30fps.mp4 --ffmpeg="$FFMPEG"
"$NODE" "$SK/scripts/make_srt.mjs"    scenes.json  out-1920x1080-30fps.srt --eff=out.effective.json
```

### 配方二：20 秒 · 带 AI 配音

```bash
PY="C:/Users/wwwzh/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
SK="C:/Users/wwwzh/.workbuddy/skills/hyperframes-10s-video"
```

**① 写 `script.json`**（每幕一句口播，条数 = 幕数；口播稿按 **约 4 字/秒** 估算）：

```json
{
  "voice": "zh-CN-YunyangNeural",
  "rate": "+15%",
  "lines": [
    "AI 自我进化，正在发生。",
    "产物、框架、模型，三条路径协同进化。",
    "三位一体，构成自主进化体系。"
  ]
}
```

**② 跑 TTS**（`--keep-dur` 让配音贴合每幕原定时长）：

```bash
"$PY" "$SK/scripts/tts_scenes.py" script.json scenes.json . \
  --ffmpeg="$FFMPEG" --keep-dur --rate=+15%
# 产出：voice.mp3 + scenes_vo.json + timing.json
```

**③ 用 `scenes_vo.json` 继续**（后续步骤同配方一），**④ 混音**：

```bash
"$FFMPEG" -y -i out-1920x1080-30fps.mp4 -i voice.mp3 \
  -c:v copy -c:a aac -b:a 192k -shortest out-1920x1080-30fps-a.mp4
```

**⑤ 字幕按语音对齐**：

```bash
"$NODE" "$SK/scripts/make_srt.mjs" scenes.json out-1920x1080-30fps-a.srt --timing=timing.json
```

> ⚠️ 改了文案 / `voice` / `rate` 后**必须先删缓存**再重跑，否则 TTS 不生效：
> `rm -rf _seg voice.mp3 scenes_vo.json timing.json`

### 配方三：同一分镜换 10 种配色，挑一套

```bash
for s in tech wuding aurora sunset ocean forest midnight gold candy paper; do
  "$NODE" "$SK/scripts/build_html.mjs" scenes.json "_gallery/$s.html" --skin=$s
  "$NODE" "$SK/scripts/render.mjs"     "_gallery/$s.html" "_gallery/$s" --only=48,156 --chrome="$CHROME"
done

# 拼成一张自包含画廊
"$NODE" "$SK/scripts/build_skin_gallery.mjs" _gallery skin-gallery.html --frames=48,156 --labels=片头,主体
```

---

## 脚本清单

| 脚本 | 用法 | 作用 |
|---|---|---|
| `build_html.mjs` | `build_html.mjs <scenes.json> <out.html> [--total=15] [--fps=30] [--skin=aurora] [--orient=portrait] [--badge=x] [--foot=y]` | 生成自包含动画 HTML，并写出 `<out>.effective.json`（生效分镜） |
| `render.mjs` | `render.mjs <in.html> <framesDir> [--fps=30] [--scale=1] [--quality=92] [--start=N] [--end=N] [--only=1,2,3] [--chrome=路径]` | 无头 Chromium 逐帧截图（`--only` 抽帧核验，`--start/--end` 分段跑长片） |
| `check_overflow.mjs` | `check_overflow.mjs <in.html>` | 程序化检测文字溢出 / 报错 |
| `encode.mjs` | `encode.mjs <framesDir> <out.mp4> [--fps=30] [--crf=20] [--preset=medium] [--ffmpeg=路径]` | 帧序列 → H.264 MP4 |
| `make_srt.mjs` | `make_srt.mjs <scenes.json> <out.srt> [--eff=<.effective.json>] [--timing=timing.json] [--total=N]` | 自动生成 SRT 字幕（不用手写） |
| `tts_scenes.py` | `tts_scenes.py <script.json> <scenes.json> <outDir> [--voice=] [--rate=] [--keep-dur] [--ffmpeg=]` | edge-tts 配音：`voice.mp3` + `scenes_vo.json` + `timing.json` |
| `build_skin_gallery.mjs` | `build_skin_gallery.mjs <帧根目录> <out.html> [--frames=48,156] [--labels=片头,主体]` | 把各配色帧拼成自包含画廊 |

**SRT 时间轴优先级**：`--timing`（有声，跟语音）> `--eff`（无声，跟画面）> 按 `dur` 累加。
**字幕文字来源**：某幕的 `"srt"` 字段 ＞ 按 type 自动抽取画面文字。`end` 幕的 `cta` 默认不入字幕，需要就用 `srt` 显式加。

---

## 输出文件说明

| 文件 | 说明 | 交付后可否删 |
|---|---|---|
| `<slug>-1920x1080-30fps.mp4` | 成片（无声版） | 保留 |
| `<slug>-1920x1080-30fps-a.mp4` | 有声版（含 AAC 音轨） | 保留 |
| `<slug>.srt` | 字幕，与 MP4 同名可自动加载 | 保留 |
| `<slug>.html` | 交互预览页（可实时换肤、空格播放/暂停、←→ 切幕） | 保留 |
| `<slug>.effective.json` | 生效分镜（含缩放后真实 dur/start），字幕之源 | 保留 |
| `gen-log.txt` | 生成起止时间与各阶段耗时 | 保留 |
| `scenes.json` / `script.json` | 分镜源 / 口播稿 | 保留 |
| `_frames/` `_preview/` `_seg/` | 临时帧与 TTS 分段缓存（约 20MB/秒视频） | **可删** |

---

## 常见坑 / FAQ

**Q：渲染出来的颜色不是我选的？**
以 `--skin=` 或 `scenes.json` 的 `"skin"` 为准；HTML 里第一个 `data-skin="tech"` 是 CSS 默认选择器，不是实际值。校验看构建日志的「配色 skin=xxx」那行。

**Q：字幕和画面对不上？**
一定是用错时间轴了。必须把 `build_html.mjs` 产出的 `<slug>.effective.json` 用 `--eff=` 喂给 `make_srt.mjs`——时长归一后每幕 `dur` 变了，按原始 `dur` 累加必然错位。

**Q：改了配音文案，声音没变？**
`_seg/` 有分段缓存，先 `rm -rf _seg voice.mp3 scenes_vo.json timing.json` 再重跑。

**Q：配音比画面长很多 / 成片被拉长？**
口播稿太长。按 **约 4 字/秒** 压缩（10s ≈ 35 字内），并用 `--keep-dur`。若某幕语音本身超过该幕 `dur`，该幕会被放宽，日志会告警。

**Q：60 秒视频渲染很久？**
耗时线性增长（10s ≈ 2 分钟，60s ≈ 12 分钟）。用 `render.mjs --start=0 --end=899` 之类分段跑，避免后台进程被 kill。

**Q：画面文字溢出？**
调小时长（尤其压到 <8s）后必须重新抽帧核验；或跑 `check_overflow.mjs`。三卡布局请用 `free` 幕而非 `points`，否则横屏会折成 2+1。

**Q：中文字体？**
Windows 无 PingFang SC，模板已回退 Microsoft YaHei，无需处理。

---

## 环境依赖

本机（Windows）已就绪，路径如下：

| 依赖 | 路径 |
|---|---|
| Node | `C:\Users\wwwzh\.workbuddy\binaries\node\versions\22.22.2-3\node.exe` |
| Python（TTS 用，已装 `edge_tts`） | `C:\Users\wwwzh\.workbuddy\binaries\python\envs\default\Scripts\python.exe` |
| Chromium | `render.mjs` / `check_overflow.mjs` 自动探测 `%LOCALAPPDATA%\ms-playwright\chromium-*`（取最高版本），也可 `--chrome=` 指定或用 Edge |
| ffmpeg（H.264） | `D:\Program Files\ffmpeg-6.1.1-full_build\bin\ffmpeg.exe` |

> ⚠️ Playwright 自带的 `ffmpeg-win64.exe` 是精简版（只有 VP8/webm），**不能**输出 H.264 MP4，别用错。

**目录结构**：

```
hyperframes-10s-video/
├── SKILL.md                 # 技能主文档（完整 SOP 与铁律）
├── README.md                # 本文件（使用说明）
├── assets/
│   ├── template.html        # 动画模板（分镜渲染 + 10 套皮肤 + 控制条）
│   └── gsap.min.js          # GSAP（离线自包含）
├── scripts/                 # 全部可执行脚本
│   ├── build_html.mjs
│   ├── render.mjs
│   ├── check_overflow.mjs
│   ├── encode.mjs
│   ├── make_srt.mjs
│   ├── tts_scenes.py
│   └── build_skin_gallery.mjs
└── references/
    ├── scenes_schema.md     # 分镜字段完整定义
    ├── prompt-template.md   # 对话用标准提示词模板
    ├── skin-gallery.html    # 10 套配色可视化画廊
    └── example-rsi/         # RSI 完整范例（scenes.json + SRT）
```
