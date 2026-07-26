---
name: edu-teaching-animation
description: 把单个学科概念(中文/英文都行,如"声现象""杠杆原理""光合作用")自动做成动态教学内容。两种产出都由 HyperFrames 渲染、共用同一个 index.html(mode 变量切换):① 配音教学视频 — 分镜 + Minimax / Edge TTS 中文配音 + 字幕 + 完整 MP4(1080p, ~90s, 发视频号/给孩子看);② 无声循环动图 — 同一内容的紧凑无声版 MP4(1080p, ~32s, 循环, 公众号正文内嵌自动播放)。共用一份 7 段分镜和同一套主题配色(声/光/力/电/热/生物/化学/历史/数学各有色系),视频和动图风格完全统一。当用户提"教学视频""配音视频""教学动图""无声动图""循环视频""公众号内嵌动图""concept → animation"或给一个学科概念要做成动态内容时,使用本 skill。
---

# Teaching Animation (配音教学视频 + 无声循环动图)

## 概述

输入一个概念 (例 "声现象") → 两种动态产出,**都是 HyperFrames 渲染的 MP4,共用同一个 index.html**:

| 产出 | 规格 | 用途 |
|---|---|---|
| **配音视频** | 1080p、~90s、中文旁白 + 字幕 | 完整讲解,发视频号 / 给孩子看 |
| **无声动图** | 1080p、~32s、无声、循环 | 公众号正文内嵌自动播放 |

关键: 两种产出**共用同一个 `index.html`**,靠 HyperFrames 变量 `mode`(video/silent)切换——
搭一次内容,两种都能出。silent 模式紧凑时间轴、无字幕、不淡出(循环无缝),质感和动效
与视频版完全一致。

共用: **7 段结构** (1 标题 + 5 子概念 + 1 总结)、**同一套主题配色**
(`references/color-palettes.md`)、**同一份分镜脚本** (`references/storyboard-guide.md`)。

## 触发路由

| 用户说 | 做什么 |
|---|---|
| "教学视频" / "配音" / "讲解版" | 搭 index.html → `build_video.sh` |
| "教学动图" / "无声" / "循环" / "公众号内嵌" | 搭 index.html → `build_silent.sh` |
| "视频和动图都要" | 搭一次 index.html,两个脚本都跑 |

不确定时, **先问清楚概念 + 适用学段 (默认初二物理)**, 其他别问。

## 统一流程 (两种产出共用前 4 步)

```bash
# 第 0 步: 写分镜 (见 references/storyboard-guide.md)
#   把概念拆成 7 段, 写 storyboard.json: 每段 title / narration (旁白 30-50 字, 口语化,
#   不读公式) / visual (画面描述) / transition。配色按主题族选 (color-palettes.md)。
#   拆解质量决定一切 — 对照教材知识点, 参考 examples/sound-video/storyboard.json。

# 1. TTS 配音
# 默认: storyboard.voice.provider → 有 MINIMAX_API_KEY 用 minimax, 否则 edge
# edge 免费但需外网; 批量失败可用 --skip-existing 续跑, 或 --provider minimax 备用
# pip install -r ../requirements-tts.txt   # edge-tts
# export MINIMAX_API_KEY=...              # 仅 minimax 需要
# export EDGE_TTS_VOICE=zh-CN-YunxiNeural  # 仅覆盖 edge 默认音色
python3 scripts/minimax_tts.py storyboard.json --outdir audio/ --provider edge
# 或: python3 scripts/minimax_tts.py storyboard.json --outdir audio/ --provider minimax
#   → audio/seg-0N.mp3 + audio/durations.json (时间轴来源, 无声版也需要它做骨架)

# 2. 生成骨架 (时间轴/配色/audio/SEGMENTS/silent机制 全部自动填好, 不要手搭)
python3 scripts/scaffold_video.py <project_dir>

# 3. 填场景内容: s2-s6 的 SVG 示意图 (零件拷 references/svg-parts.md) + 卡片文案
#    + scene2()-scene6() 入场编排。规则见 references/video-authoring.md

# 4. 出片 (二选一或都要):
bash scripts/build_video.sh  <project_dir>   # → 配音视频  renders/<name>.mp4
bash scripts/build_silent.sh <project_dir>   # → 无声动图  renders/<name>-silent.mp4
```

`build_video.sh`: lint + WCAG 对比度审计 + render(video 模式) + 场景中点蒙太奇。
`build_silent.sh`: 临时改 data-duration + render(silent 模式,紧凑 32s 无声) + 蒙太奇。
两个脚本读同一个 index.html,只是渲染的 `mode` 变量不同。

**换音色/改旁白后重跑 TTS,用 `python3 scripts/sync_timeline.py <project_dir>` 同步
时间轴 (不要手抄数字),再重新渲染。**

场景内容标准: section-chip + SVG 示意图 (≥3 图形元素) + info-card + callout。
视频尺寸规范、SVG 画法、动效编排、silent 机制、实测 lint 坑都在 `references/video-authoring.md`。

环境: Node.js ≥22 + ffmpeg (`npx hyperframes doctor` 自检)。
配音可选: Minimax (`MINIMAX_API_KEY`) 或免费 Edge TTS (`pip install edge-tts`, 需外网, 可能限流)。

## silent(无声)模式怎么工作

`index.html` 的 `<html>` 声明 `mode` 变量。渲染时 `--variables '{"mode":"silent"}'` 切到无声版:
- **时间轴**: 每段等长紧凑 (`SILENT_SEG`=4.6s, 共 ~32s), 不依赖音频长度
- **无字幕**: `MODE !== "silent"` 才生成字幕
- **不淡出**: 最后一段不淡出到底, 循环首尾无缝
- **质感动效全保留**: 渐变/颗粒/波形流动都在 (MP4 有帧间压缩, 不像 GIF 怕连续色调和运动)

> 为什么不出 GIF? GIF 无帧间压缩, 完整 7 段想要 720p 高清必然 >2MB (实测), 只能降到
> 480p 且小字发糊。公众号早已支持内嵌 MP4 自动播放, 无声 MP4 = 1080p 完整 + 8~10MB,
> 比任何 GIF 都清晰。所以动图产出用无声 MP4, 不用 GIF。

## 输出文件规范

```
<topic>/
├── storyboard.json           # 分镜 (第 0 步)
├── audio/
│   ├── seg-01..07.mp3         # TTS 分段配音
│   └── durations.json         # 时间轴来源
├── index.html                # HyperFrames 组合 (video/silent 双模式)
├── renders/
│   ├── <topic>.mp4            # 配音视频 (~90s)
│   └── <topic>-silent.mp4     # 无声循环动图 (~32s)
└── preview/
    ├── montage.png            # 配音视频蒙太奇
    └── montage-silent.png     # 无声动图蒙太奇
```

## 资源

- `assets/video-template/index.html` — HyperFrames 模板 (组件 + video/silent 双模式 + 转场/字幕/波形引擎)
- `examples/sound-video/` — 声现象完整示例 (storyboard → 音频 → index.html → 配音视频 + 无声动图)
- `scripts/minimax_tts.py` — Minimax / Edge / say 分段配音 + 时间轴 + 指纹缓存
- `scripts/scaffold_video.py` — 骨架生成 (第 2 步, 含 silent 机制)
- `scripts/sync_timeline.py` — 重配音后同步时间轴
- `scripts/build_video.sh` — 配音视频渲染 (lint + validate + render + 蒙太奇)
- `scripts/build_silent.sh` — 无声循环动图渲染 (silent 模式)
- `references/storyboard-guide.md` — 分镜拆解 + 旁白规范 (第 0 步必读)
- `references/video-authoring.md` — 场景编写硬规则 + silent 机制 + 实测坑 (必读)
- `references/svg-parts.md` — SVG 符号库 (电学/波形/图线/力学/光学, 画示意图先来这拷)
- `references/color-palettes.md` — 9 套主题调色板 (60-30-10 + 莫兰迪, 含 CSS 变量)


## TTS Provider（配音引擎）

教学视频配音支持三种引擎。未显式指定时优先级：

1. `storyboard.voice.provider`
2. 已设置 `MINIMAX_API_KEY` → `minimax`
3. 否则 → `edge`

| Provider | 费用 | 依赖 | 说明 |
|---|---|---|---|
| `minimax` | 付费 | `MINIMAX_API_KEY` | 高质量，模型 `speech-02-hd` |
| `edge` | 免费 | `pip install edge-tts` + **外网** | Microsoft 在线 TTS；可能限流/地区限制 |
| `say` | 免费 | macOS 内置 | 仅本地预览 |

```bash
# 免费 edge-tts（无 Minimax key 时的默认路径，需外网）
python3 scripts/minimax_tts.py storyboard.json --provider edge
# 覆盖默认 edge 音色（仅当未在 CLI/storyboard 指定 voice 时生效）
export EDGE_TTS_VOICE=zh-CN-YunxiNeural

# Minimax 高质量
export MINIMAX_API_KEY=...
python3 scripts/minimax_tts.py storyboard.json --provider minimax --voice female-chengshu

# 改旁白后指纹不匹配会自动重生成；也可用 --skip-existing 续跑
python3 scripts/minimax_tts.py storyboard.json --outdir audio/ --provider edge --skip-existing
```

storyboard.json：
```json
{
  "voice": {
    "provider": "edge",
    "voice_id": "zh-CN-XiaoxiaoNeural",
    "speed": 1.0
  }
}
```

音色优先级：`--voice` > `storyboard.voice.edge_voice_id`/`minimax_voice_id` > 兼容 `voice_id` >（edge 时）`EDGE_TTS_VOICE` > 内置默认。
CLI 显式 `--provider edge` 时，不会把 Minimax 克隆音色（如 `host-voice-default`）直接传给 Edge；请配置 `edge_voice_id` 或 `EDGE_TTS_VOICE`。

Edge 常用中文音色：`zh-CN-XiaoxiaoNeural` / `zh-CN-XiaoyiNeural` / `zh-CN-YunxiNeural` / `zh-CN-YunyangNeural`。

语速范围：`0.5 ~ 2.0`。单次 Edge 请求默认超时 60s（`EDGE_TTS_TIMEOUT` 可改）。
