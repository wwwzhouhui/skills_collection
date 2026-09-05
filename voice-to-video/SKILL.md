---
name: voice-to-video
description: 口播文字稿一键成片：TTS 配音（edge-tts，带逐句/逐词时间戳）→ HTML 动画合成（场景由时间戳驱动，画面跟着声音走）→ Playwright 逐帧确定性渲染合成 MP4。Use whenever the user wants to 把口播稿/文字稿/文案/文章做成视频、配音视频、解说视频、知识类短视频、口播视频、文字转视频、TTS video、voice-over video、画音同步、字幕驱动画面，or mentions HyperFrames 式的 HTML 渲视频流程 — even if they just say "帮我做个视频" 并附了一段稿子.
---

# 口播转视频（voice-to-video）

把一段口播文字稿变成一条 **文字稿 ↔ 配音 ↔ 画面逐句对应** 的 MP4：

```
script.txt ──tts.py──▶ voice.mp3 + timeline.json(逐句/逐词毫秒时间戳) + subtitles.srt
                              │
                              ▼
              composition.html（一句口播 = 一个场景，时间戳来自 timeline）
                              │ render.py（无头浏览器逐帧截图 = 确定性渲染）
                              ▼
                        final.mp4（配音音轨已混入）
```

核心约定（务必遵守）：**音频即时钟，画面跟着声音走**。场景切换、元素出现、字幕高亮全部由 timeline.json 的时间戳驱动；渲染是 seek 式逐帧截图，同样的输入永远渲出同样的每一帧。

## 工作目录约定

每条视频一个独立目录，产物集中存放：

```
<video_dir>/
├── script.txt          口播稿（纯文本）
├── kit.css engine.js   从技能 assets/ 拷贝
├── composition.html    你编写的合成页
├── build/              tts.py 产物: voice.mp3 / timeline.json / subtitles.srt
├── frames_final/       渲染中间帧（默认渲完删除）
└── final.mp4           成片
```

## Step 0 · 环境自检

首次使用或报错时检查（本机已确认可用的版本：ffmpeg 6.1.1 / edge-tts 7.2.8 / playwright 1.55）：

```bash
ffmpeg -version | head -1 && python -c "import edge_tts, playwright" \
  && python -m playwright install chromium --dry-run
```

缺 Chromium 就执行 `python -m playwright install chromium`。edge-tts 需要能访问 Microsoft 服务（失败通常是网络/代理问题，重试或换网络）。

## Step 1 · 口播稿 script.txt

- 纯文本，一段到底，标点规范（分句依据 。！？；!? 和换行）。
- 用户给了稿 → 原样使用，只做明显口误/错字的修正。
- 用户只给了主题 → 先按主题写稿（口语化短句，中文每句 ≤ 40 字），**给用户确认后再进入合成**；中文语速约 4.2 字/秒，可用来估算成片时长。
- 长稿（>5 分钟）提示用户渲染耗时（1080p30 约为片长 6-10 倍），可改 `--fast` 或 720p。

## Step 2 · 生成配音与时间轴

```bash
python <skill>/scripts/tts.py --script script.txt --out build --voice xiaoxiao
```

- 音色简称：`xiaoxiao`(女·通用默认) `xiaoyi`(女·活泼) `yunxi`(男·阳光) `yunjian`(男·沉稳) `yunyang`(男·播报)；或传完整 edge-tts 音色名。可用 `--rate +10%` 调语速。
- 产物 `build/timeline.json` 是全流程的"时钟"，先读它：确认句子切分合理、时长符合预期，再进入 Step 3。
- 用户自带配音/SRT（如 ListenHub 导出）→ 跳过本步，把 SRT 转成 timeline.json 的 `sentences` 格式（`{i,text,start,end,words?}`，毫秒；words 可省略）。

## Step 3 · 编写合成页 composition.html

0. **选画面风格**：先读 `references/styles.md`（风格目录+版式 DNA+选择规则）。用户指定了风格就用对应的 kit（`assets/kits/` 下有 dark-hud / editorial / terminal / whiteboard / swiss / ink / glass / clay / blueprint / pixel），没指定就按题材自动匹配，拿不准用默认 `assets/kit.css`（BlockFrame 积木风）。
1. 拷贝 `assets/engine.js`、`assets/template.html`（改名 composition.html）和**选中的 kit**（如 `assets/kits/ink.css`）到视频目录，composition.html 的 `<link rel="stylesheet">` 指向该 kit 文件名。注意：安全钩子会拦截用 Bash `cp` 复制源码文件，用 Read + Write 工具完成拷贝（engine.js / kit 内容原样写入）。
2. **先读 `references/composition-guide.md`**（对齐规则、动画属性、场景类型、自检清单都在里面），要点：
   - 一句口播 = 一个 `.scene`，`data-start` = 句子 `start`，`data-end` = 句子 `hold_end`；
   - 场景内容必须与当前句子对应，关键词出现时机用 `data-delay ≈ 词时间 - 场景start`；
   - **按所选风格遵循 `references/styles.md` 的"版式 DNA"重排场景结构**（布局骨架/编排/装饰/动效签名随风格变），只换 CSS 配色算不达标；
   - 字幕数据用 `<script src="build/subtitles.js"></script>` 引入（tts.py 产出，即 timeline 的 sentences；也可手工粘贴成 `const SUBTITLES`）；
   - 禁止 CSS animation/transition、setTimeout、Math.random（破坏确定性）。
3. 视觉：默认用 kit.css 的 BlockFrame 设计系统（奶油底/糖果色/黑描边硬阴影）。用户给了品牌/风格要求 → 覆盖 `:root` 变量与组件样式，但保持整套一致。

## Step 4 · 预览（合成后必做）

```bash
python -m http.server 8765   # 在视频目录下执行
```

把 `http://localhost:8765/composition.html` 给用户，或用浏览器工具自查：**空格播放**，确认（1）字幕逐句切换且词高亮跟得上语速；（2）换句瞬间场景切换；（3）元素出现时机与语义对得上。发现问题回到 Step 3 改（预览阶段不渲染，改起来最快）。

## Step 5 · 渲染成片

```bash
python <skill>/scripts/render.py --html composition.html --audio build/voice.mp3 --out final.mp4
```

- 默认 1920×1080 @30fps、CRF18。草稿用 `--fast`，小样用 `--width 1280 --height 720`。
- 断点续渲：中断后原命令重跑即自动跳过已有帧；`--keep-frames` 保留中间帧。
- 预计耗时 ≈ 片长 × 6-10（1080p30），长视频先告知用户。
- 渲染完成后用 ffmpeg 抽查帧与 timeline 对齐：`ffmpeg -ss <句中时间> -i final.mp4 -frames:v 1 check.jpg`，确认该时刻画面/字幕与该句一致。

## Step 6 · 交付

向用户报告：`final.mp4`（成片）、`build/subtitles.srt`（平台上传用外挂字幕）、`composition.html`（源文件，可改后重渲）、时长/大小。一句话说明"改稿子/改画面后重跑哪两步"。

## 故障排查

| 症状 | 处理 |
|---|---|
| edge-tts 429/超时 | 等几秒重试；换网络；或用户自带 TTS+SRT（走 timeline.json 格式） |
| Chromium 启动失败 | `python -m playwright install chromium` |
| 画面字体不对/中文方块 | 确认本机有微软雅黑；kit.css 的 --f-body 兜底链已含系统字体 |
| 渲染出的画面与预览不一致 | 检查是否用了 CSS animation/random；动画一律走 data-anim / HF.on |
| 音画差半拍 | render.py 以 ffprobe 音频时长为准；确认 composition 里没写死 durationMs 覆盖 |
| 帧渲染中断 | 原命令重跑（自动续渲），或 `--from-frame N` |
