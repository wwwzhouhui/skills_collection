# 分镜脚本 schema（scenes.json）

顶层字段：

```json
{
  "skin": "tech",                 // 配色皮肤，10 选 1（见下表）｜默认 tech
  "badge": "海老豹666",      // 右上常驻角标
  "foot":  "底部常驻小字",          // 可写数据来源/口径声明
  "orient": "landscape",          // landscape=1920×1080（默认）| portrait=1080×1920
  "duration": 10,                 // 目标总时长（秒）。可省略=各幕 dur 之和；也可用 CLI --total=20 覆盖
  "fps": 30,                      // 帧率，默认 30（也可 build --fps=60）
  "scenes": [ ... ]
}
```

> `duration` 与命令行 `--total=<秒>` 等价，**CLI 优先**。给定目标后各幕 `dur` 按比例缩放、末幕吸收舍入漂移，总和精确等于目标（`|差| ≤ 0.05s` 时不缩放）；单幕下限 `0.6s`。
> 缩放后的真实时长写入 `<slug>.effective.json`（build 自动产出），字幕生成必须用它。

每幕通用字段：`type` + `dur`（秒，必填）；另有可选 `srt`（该幕字幕覆盖文本，`\n` 分行）——
字幕默认由 `make_srt.mjs` 自动抽取画面文字，需要精确控制时在该幕写：

```json
{"type":"quote","dur":5,"text":"你只管想清楚讲什么，画面交给代码。","by":"海老豹666",
 "srt":"你只管想清楚讲什么\n画面交给代码。"}
```

### 配色皮肤（`skin`，10 套可选）

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

> 可视化预览见 `references/skin-gallery.html`（同一分镜的 10 套配色实拍帧）。
> 也可在生成的可播放 HTML 底部控制条用下拉框实时切换；未知皮肤名自动回退 `tech`。

每幕通用字段：`type` + `dur`（秒，必填）。

## 1. title / end（片头 / 片尾）
```json
{"type":"title","dur":4.5,
 "eyebrow":"KINETIC VIDEO",
 "brand":"海老豹666",
 "title":"一篇笔记，一条动画视频",
 "sub":"分镜 · 排版 · 动效 · 成片，一条指令跑完"}
```
`end` 额外支持：`tags":["调研笔记","口播稿","产品页"]","cta":"一句话开工"`。
动效：品牌字 elastic 弹入 → 标题逐字上滑（stagger 0.045）→ 副标淡入 → dashed ring 慢速旋转 → 片尾 CTA 弹入。

## 2. points（要点卡，2–4 张最佳）
```json
{"type":"points","dur":7,"head":"这套流水线能干什么",
 "items":[{"icon":"light","t":"知识讲解","d":"讲到一个观点，画面立刻把它讲清楚"}]}
```
icon 可选：`light / layers / bolt / chart / box / pen / gear / heart / check / play`
动效：卡片 elastic 弹入（stagger 0.14）+ 图标 SVG 描边生长。竖屏下卡片自动纵向堆叠。

## 3. bigword（大字强调）
```json
{"type":"bigword","dur":4,"eyebrow":"核心不是提示词","word":"分镜","note":"先拆幕，再定每幕的动作"}
```
动效：大字 elastic 放大 + 轻微回旋。

## 4. typewriter（打字机）
```json
{"type":"typewriter","dur":6.5,"head":"底层在做什么",
 "text":"把每一幕写进工程配置，GSAP 按时执行，浏览器一帧一帧画出来。",
 "note":"不是一句提示词，是写死的动作表"}
```
动效：文字逐字打出 + 光标闪烁 + 面板横向展开。

## 5. flow（流程 / 步骤，2–4 步）
```json
{"type":"flow","dur":6.5,"head":"三步落地",
 "steps":[{"t":"文稿","d":"一篇笔记或口播稿"},{"t":"分镜","d":"拆成 5–8 幕"},{"t":"成片","d":"1920×1080 · 30fps"}]}
```
动效：节点 back 弹入（stagger 0.22）+ 箭头描边生长。竖屏下箭头自动旋转 90°。

## 6. bars（数据条）
```json
{"type":"bars","dur":6,"head":"值不值得做",
 "items":[{"label":"重复利用率","v":90,"suffix":"%"},{"label":"单条耗时下降","v":75,"suffix":"%"}]}
```
动效：进度条生长（power3.out）+ 数字同步计数。
**铁律**：v 必须是真实或明确标注的估算值；非实测数据必须在 `foot` 里声明口径。

## 7. quote（金句）
```json
{"type":"quote","dur":5,"text":"你只管想清楚讲什么，画面交给代码。","by":"海老豹666"}
```
动效：引号弹入 + 正文逐字上滑 + 署名滑入。

## 8. free（自定义 HTML 幕）
```json
{"type":"free","dur":5,"html":"<div style='font-size:80px'>任意排版</div>"}
```

## 9. TTS 配音输入（script.json）

与 `scenes.json` 一一对应，每幕一句口播：

```json
{
  "voice": "zh-CN-YunyangNeural",
  "rate": "+0%",
  "lines": [
    "海老豹666新先说。退休之后，把日子过成诗。100种雅致玩法，说到底只讲了三个字。",
    "公园里常见的退休状态有两种。",
    "刷手机，一坐一下午，眼神是空的。",
    "真正的敌人不是没钱，而是被需要感。",
    "雅致不是花钱，是花心思。",
    "三个转变，把时间还给自己。",
    "退休后的自由，不是想做什么就做什么，而是想不做什么就不做什么。",
    "退休前，时间是别人的；退休后，时间主权回到自己手里。",
    "把时间还给自己。退休不是落幕，是人生真正自由的开始。"
  ]
}
```

运行 `tts_scenes.py script.json scenes.json <输出目录>` 后得到：
- `voice.mp3`：整轨配音
- `timing.json`：每幕音频时长
- `scenes_vo.json`：每幕 `dur = audio + 1s` 留白，可直接用于渲染

## 脚本参数速查

### build_html.mjs（构建自包含 HTML）
```powershell
build_html.mjs <scenes.json> <out.html> [--total=20] [--fps=30] [--skin=aurora] [--orient=portrait] [--badge=xxx] [--foot=yyy]
```
- `--total=<秒>`：目标总时长，各幕 `dur` 按比例归一到该值（等价于顶层 `duration`，CLI 优先）
- 产出 `<out>.effective.json`：生效分镜（含缩放后的真实 `dur`/`start`），**字幕必须用它**

### render.mjs（逐帧截图）
```powershell
render.mjs <html> <framesDir> [--fps=30] [--scale=1] [--quality=92] [--only=1,2,3] [--start=N] [--end=N]
```
- `--start`/`--end`：按帧号范围分段并行，避免长后台被 kill
- `--only`：只渲染指定帧号（抽帧核验用）
- `--quality`：JPEG 质量，80 可提速约 15–20%，画质损失不明显

### encode.mjs（编码成片）
```powershell
encode.mjs <framesDir> <out.mp4> [--fps=30] [--crf=20] [--preset=medium]
```

### make_srt.mjs（自动字幕）
```powershell
make_srt.mjs <scenes.json> <out.srt> [--eff=<slug>.effective.json] [--timing=timing.json] [--total=N]
```
- 时间轴优先级：`--timing`（有声，按语音）> `--eff`（无声，按生效分镜）> 按 `dur` 累加
- 文案：每幕 `"srt"` 字段优先，否则按 type 自动抽取画面文字

## 时长建议
| 成片目标 | 幕数 | 单幕时长 |
|---|---|---|
| 10s 快闪（默认） | 3 | 2.5 / 5 / 2.5 |
| 20–30s 讲解 | 4–6 | 4–6s |
| 45s 标准讲解 | 7–8 | 4.5–7s |
| 60s 深度 | 9–11 | 5–6s |
| 60–80s 配音版 | 8–9 | 以 audio 时长 + 1s 留白为锚 |

> 长片靠**加幕**而非拉长单幕（拉长会让画面长久静止）。先写内容的自然节奏，再用 `--total` 精确卡时长即可。
> 口播配套：约 4 字/秒，10s ≈ 35 字、45s ≈ 180 字、60s ≈ 240 字。
> 渲染耗时约线性：10s ≈ 2 分钟、60s ≈ 12 分钟（本机实测，30fps/1080p）。
