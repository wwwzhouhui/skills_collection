# voice-to-video · 口播文字稿一键成片技能包

> **一句话**：给它一段口播文字稿，它生成配音（带逐句/逐词时间戳），再生成与语音逐句对齐的 HTML 动画页面，最后用无头浏览器逐帧确定性渲染，合成一条 **文字稿 ↔ 配音 ↔ 画面严格对应** 的 MP4 视频。
>
> 灵感与流程同 HeyGen 开源的 HyperFrames（"HTML 就是一种视频格式"）：**音频即时钟，画面跟着声音走。**

---

## 目录

- [它能做什么](#它能做什么)
- [工作原理](#工作原理)
- [目录结构](#目录结构)
- [环境依赖](#环境依赖)
- [使用方法](#使用方法)
- [13 套画面风格](#13-套画面风格)
- [脚本参考手册](#脚本参考手册)
- [timeline.json 格式](#timelinejson-格式)
- [常见问题](#常见问题)
- [版本记录](#版本记录)

---

## 它能做什么

输入一段口播稿（或只给一个主题），输出一条可直接发布的视频：

- ✅ **配音自动生成**：edge-tts（免费、微软音色），返回每个词的精确时间戳
- ✅ **画音严格同步**：一句口播 = 一个动画场景，字幕逐词卡拉OK高亮，声音念到哪画面切到哪
- ✅ **确定性渲染**：同样的输入永远渲出同样的每一帧，视频可以像代码一样 git 管理、看 diff、复现
- ✅ **13 套画面风格**：每种风格有独立的版式 DNA（布局骨架/编排/动效签名），不是简单换配色
- ✅ **修改成本极低**：改稿子→重跑 TTS；改画面→改 HTML；换风格→一条渲染参数，互不影响
- ✅ **外挂字幕**：自动产出 `subtitles.srt` 供视频平台上传

适合：知识类短视频、工具介绍、教程解说、课程内容、口播笔记等一切"有人旁白"的视频。

## 工作原理

```
script.txt（口播稿）
   │
   ▼  scripts/tts.py（edge-tts, WordBoundary 词级时间戳）
build/voice.mp3 + build/timeline.json + build/subtitles.srt + build/subtitles.js
   │
   ▼  按 references/ 两份指南编写 composition.html
   │    （一句口播 = 一个 .scene，时间戳驱动一切入场/切换/高亮）
   ▼  scripts/render.py（Playwright 无头 Chromium 逐帧 seek + 截图）
frames/f_000001.jpg ...
   │
   ▼  ffmpeg 编码 + 混入配音音轨
final.mp4
```

三个关键设计：

1. **一切画面状态是时间 t 的纯函数**。引擎只有一个入口 `HF.seek(t)`，相同 t 永远得到相同画面——所以"渲染"就是让 t 走过整个时间轴并逐帧截图。禁用 CSS animation、setTimeout、随机数，保证确定性。
2. **音频即时钟**。场景的 `data-start/data-end`、元素出现的 `data-delay`、卡拉OK高亮，全部来自 tts.py 产出的词级时间戳，而不是人肉估的秒数。
3. **风格与内容解耦**。动画引擎和场景时间轴是骨架，13 套 kit（配色/字体/组件皮肤）+ 版式 DNA（布局骨架）是皮肤和肌肉，互相独立、随意替换。

## 目录结构

```
voice-to-video/
├── SKILL.md                        # 技能入口：ZCode 加载的主工作流（六步流程）
├── README.md                       # 本文档
├── scripts/
│   ├── tts.py                      # 口播稿 → 配音 + 逐句/逐词时间轴 + SRT + subtitles.js
│   └── render.py                   # 合成页 → 逐帧截图 → ffmpeg 合成 MP4
├── assets/
│   ├── engine.js                   # 确定性动画引擎（HF.seek / HF.play / 声明式动画）
│   ├── kit.css                     # 默认风格：BlockFrame 积木风
│   ├── template.html               # 合成页模板（含各类场景示例）
│   └── kits/                       # 12 套扩展风格（见下表）
│       ├── dark-hud.css  editorial.css  terminal.css  whiteboard.css
│       ├── swiss.css     ink.css       glass.css      clay.css
│       └── blueprint.css pixel.css
└── references/
    ├── composition-guide.md        # 合成页编写规范（对齐规则/动画属性/场景类型/自检清单）
    └── styles.md                   # 风格目录 + 版式 DNA + 自动匹配规则
```

## 环境依赖

| 依赖 | 用途 | 安装/检查 |
|---|---|---|
| Python 3.10+ | 运行脚本 | 已随 ZCode 环境 |
| edge-tts | TTS 配音（需能访问微软服务） | `pip install edge-tts` |
| playwright + Chromium | 无头浏览器逐帧截图 | `pip install playwright && python -m playwright install chromium` |
| ffmpeg（含 ffprobe） | 编码合成、探测时长 | 官网下载加入 PATH |

一条自检命令：

```bash
ffmpeg -version | head -1 && python -c "import edge_tts, playwright" && echo OK
```

## 使用方法

### 在 ZCode 里（推荐）

直接用自然语言触发技能，不必记任何命令：

```
把这段稿子做成视频：（粘贴口播稿）
用终端极客风做一条介绍 XX 的口播视频
这条视频换个水墨风重渲一版
```

技能会自动走六步流程：**环境自检 → 整理口播稿 → TTS → 编写合成页 → 预览 → 渲染验收**。细节规则见 `SKILL.md`。

### 手动跑管线

```bash
# 1. 生成配音与时间轴（voice 可换 xiaoyi/yunxi/yunjian/yunyang 或完整音色名）
python scripts/tts.py --script script.txt --out build --voice xiaoxiao --rate +0%

# 2. 编写 composition.html（拷贝 assets/engine.js + 某个 kit，按 references/ 指南写场景）

# 3. 浏览器预览（空格播放，字幕卡拉OK，检查同步）
python -m http.server 8765   # 打开 http://localhost:8765/composition.html

# 4. 渲染成片
python scripts/render.py --html composition.html --audio build/voice.mp3 --out final.mp4

# 4b. 用其他风格重渲同一内容（无需改合成页）
python scripts/render.py --html composition.html --audio build/voice.mp3 \
    --style-kit assets/kits/ink.css --out final_ink.mp4
```

## 13 套画面风格

| Kit | 风格 | 一句话特征 | 适用题材 |
|---|---|---|---|
| `kit.css`（默认） | BlockFrame 积木风 | 奶油底、糖果色块、黑描边硬阴影 | 通用科技/工具类 |
| `kits/dark-hud.css` | 暗夜科技 HUD | 深蓝黑底、霓虹青紫、发光网格扫描线 | AI、编程、数码 |
| `kits/editorial.css` | 编辑杂志风 | 杂志跨页、衬线大标题、拉引与索引表 | 深度解读、财经、历史 |
| `kits/terminal.css` | 终端极客风 | 全片一场终端会话、打字机命令+日志 | 编程教程、CLI 工具 |
| `kits/whiteboard.css` | 手绘白板风 | 便利贴、手绘圈、逐条打勾的清单 | 教学、概念科普 |
| `kits/swiss.css` | 极简瑞士风 | 12 列模数网格、巨大数字、齐边排版 | 商业、观点、方法论 |
| `kits/ink.css` | 国潮水墨风 | 竖排对联、印章、月洞窗、宣纸界格 | 国学、历史、文化 |
| `kits/glass.css` | 玻璃拟态/液态玻璃 | 极光色场、磨砂玻璃面板、通透圆角 | 产品介绍、效率工具、设计 |
| `kits/clay.css` | 黏土拟态软胶风 | 粉彩蓬松、软胶质感、胶囊与圆徽章 | 轻松科普、生活、亲子 |
| `kits/blueprint.css` | 蓝图工程风 | 工程蓝制图网格、虚线框、FIG 图号与 ⌀ 编号 | 原理讲解、架构解析 |
| `kits/pixel.css` | 像素复古游戏风 | 8-bit 色板、游戏对话框、任务清单与血条 | 游戏、怀旧科技 |

每种风格不只是配色——`references/styles.md` 的**版式 DNA** 一节规定了各自的布局骨架、编排方式、装饰元素和动效签名（例如：terminal 必须是"命令+输出"结构、swiss 禁用卡片贴网格、ink 用竖排和印章）。生成合成页时必须按 DNA 重组版面。

## 脚本参考手册

### tts.py

```
python scripts/tts.py --script script.txt --out build
     [--voice xiaoxiao|xiaoyi|yunxi|yunjian|yunyang|完整音色名]
     [--rate +10%] [--pitch +0Hz] [--volume +0%]
```

| 产物 | 说明 |
|---|---|
| `voice.mp3` | 配音音频 |
| `timeline.json` | 逐句时间轴（含逐词 `words`），全流程的"时钟"，schema 见下节 |
| `subtitles.srt` | 逐句字幕，供视频平台上传 |
| `subtitles.js` | `window.SUBTITLES = [...]`，合成页直接 `<script src>` 引入 |

分句规则：按 `。！？；!?;` 和换行分句，超过 60 字在最近的逗号处强制切分。

### render.py

```
python scripts/render.py --html composition.html --audio build/voice.mp3 --out final.mp4
     [--fps 30] [--width 1920] [--height 1080] [--quality 85] [--crf 18]
     [--fast]                       # 草稿模式：crf 23 + veryfast
     [--style-kit assets/kits/xxx.css]  # 渲染时注入风格，覆盖合成页 <link>
     [--frames-dir DIR] [--keep-frames] # 保留中间帧（默认渲完删除）
```

- **断点续渲**：中断后原命令重跑，自动跳过已存在的帧
- **渲染耗时**：约为片长 2 倍（1080p30，实测 178s 片 ≈ 6.2 分钟）；3 路并发互不拖慢
- **输出**：H.264 + AAC，`-movflags +faststart`，可直接上传平台

## timeline.json 格式

```jsonc
{
  "meta": { "voice": "...", "audio": "voice.mp3", "audio_ms": 178296, "unit": "ms" },
  "sentences": [
    {
      "i": 0,
      "text": "这句口播的原文。",       // 与口播稿逐字一致，也是画面底部字幕
      "start": 100,                    // 本句开始（毫秒）
      "end": 4300,                     // 语音结束
      "hold_end": 4875,                // 场景建议停留到的时刻（已含句间停顿策略）
      "words": [ { "w": "这句", "t": 100.0, "d": 350.0 } ]  // 词级时间，驱动卡拉OK与元素出场
    }
  ]
}
```

合成页对齐规则（详见 `references/composition-guide.md`）：

- 一句口播 = 一个 `.scene`，`data-start` = 句子 `start`，`data-end` = 句子 `hold_end`
- 元素 `data-delay ≈ 词的 t − 场景 start`，让关键词在"被念到"的那一刻出现
- 字幕/卡拉OK由引擎按 `SUBTITLES` 自动驱动，无需手写

自带 TTS？只要能产出"音频 + 逐句 SRT"，把 SRT 转成上面的 `sentences` 格式即可接入（`words` 可省略，卡拉OK退化为逐句高亮）。

## 常见问题

| 问题 | 处理 |
|---|---|
| edge-tts 报 429 / 超时 | 等几秒重试或换网络；或用自带 TTS+SRT 走 timeline 接入 |
| Chromium 启动失败 | `python -m playwright install chromium` |
| 画面里中文显示异常 | kit 的字体栈已含微软雅黑/楷体等系统字体兜底；勿删除 font-family 兜底链 |
| 渲染结果与预览不一致 | 检查是否用了 CSS animation/`Math.random`/`setTimeout`——动画一律走 `data-anim` 或 `HF.on` |
| 音画差半拍 | render.py 以 ffprobe 探测的音频时长为准；确认 composition 没写死 durationMs |
| 长视频渲染太久 | 草稿用 `--fast`/低分辨率；或 `--fps 24`；渲染支持断点续渲 |
| 只想换风格 | 不用改合成页：`--style-kit` 注入即可 |

## 版本记录

- **2026-09-05 v1.0**：技能创建。TTS 词级时间轴、确定性引擎、BlockFrame 风格、端到端验证。
- **2026-09-05 v1.1**：`tts.py` 显式 `boundary="WordBoundary"`（修复 7.2.8 默认只发句边界）；新增 `subtitles.js` 产出；卡拉OK标点回填；`render.py` 支持断点续渲与 `--style-kit` 风格注入。
- **2026-09-05 v1.2**：风格扩展至 13 套；`references/styles.md` 新增**版式 DNA** 体系（按风格重组页面结构，而非仅换 CSS）；实测 5 种版式 DNA 各出一条成片（杂志跨页/终端会话/白板便利贴/瑞士网格/水墨竖排）。

---

*本技能由 ZCode 的 skill-creator 流程创建并迭代；用法问题先看 `SKILL.md`（工作流）与 `references/composition-guide.md`（合成规范）。*
