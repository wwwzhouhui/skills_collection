---
name: remotion-video-factory
description: 视觉优先的程序化视频生产流水线：Remotion + React 代码渲染精确图形动画（注意力矩阵/连线拓扑/数据图表/数字滚动/流程图解），edge-tts 中文配音自动测长并重建时间线，三层音频（配音/BGM/SFX 钉帧表），确定性渲染，双版本成片交付。Use whenever the user wants to 用代码或 AI 制作技术讲解/科普动画视频、把概念、数据、架构、算法做成动画演示, mentions Remotion、程序化视频、动画图解、技术科普视频、animated explainer、code-rendered video, or asks for a video whose core is 图表/矩阵/连线/数据可视化/公式动画 — even if they just say "帮我做个视频" and the content is technical, data-driven, or diagram-heavy.
---

# Remotion 视频工厂（视觉优先）

把一个主题变成一条**图解动画 + AI 配音**的 MP4：技术结构图（矩阵/连线/流程/图表）
全部由代码绘制——精确、可参数化、改数据自动重排；配音由 edge-tts 生成并**自动测长**，
时间线由脚本重建，保证旁白永不被画面切走。

```
主题简报 ──▶ DESIGN.md（分镜表） + VOICEOVER_ZH.md（一段=一场景）
                          │
                          ▼ scripts/tts.py（edge-tts，逐段生成+ffprobe测长）
              public/vo/sceneN.mp3 + build/durations.json
                          │
                          ▼ scripts/build-timeline.mjs（时长=max(视觉最短, 配音+40f)）
              src/timeline.ts + src/types.ts + build/subtitles.srt
                          │
                          ▼ 场景组件（React，按 references/animation-vocabulary.md）
                          ▼ remotion still 逐镜头 QA ──▶ remotion render
              final.mp4（带BGM） + final-nobgm.mp4 + SRT + QA 静帧
```

## 何时用 / 不用本 skill

| 内容特征 | 用哪个 |
|---|---|
| 图解、数据、结构是主角（矩阵/连线/图表/公式/流程） | **本 skill** |
| 精确的技术动画（Token、注意力、架构、算法可视化） | **本 skill** |
| 口播稿为主、要 12 套风格快速切换、卡拉OK逐词字幕 | voice-to-video |
| 复刻真实产品页面（截图 + 2.5D 运镜） | video-shotcraft |
| 真人出镜 / 实拍素材剪辑 | 都不适合 |

## 核心理念（四条铁律）

1. **视觉从代码生长**：结构图/数据图由 React + SVG 代码绘制，不让 AI 视频模型画公式和连线（文字必乱码、关系必漂移）。素材只在"真实性值钱"的地方使用（产品截图、Logo、真实数据）。
2. **句级音画对齐**：一段旁白 = 一个场景。场景时长 = `max(visualMin, 配音帧数 + 40f 尾巴)`，由 `build-timeline.mjs` 自动计算——改稿/换语速只需重跑两个脚本，时间线自动重排。
3. **三层音频**：VO（1.0）+ BGM（~0.34，首尾淡入淡出，`bgm` inputProp 控制可出无 BGM 版）+ SFX 钉帧表（`from` 一律写 `SHOTS.x.from + offset` 相对表达式，时间线平移自动跟随）。
4. **确定性渲染**：禁 `Date.now()` / `Math.random()` / 无参 `new Date()`；一切伪随机用固定种子。同样输入永远渲出同样的帧。

## 环境自检（首次使用）

```bash
node <skill>/scripts/check-env.mjs   # 一键自检：Node / ffmpeg / ffprobe / Python / edge-tts
```

手动检查（Windows 用户注意：命令是 `python` 不是 `python3`，PowerShell 没有 `head`）：

```bash
node --version          # ≥18（实测 24 可用）
ffmpeg -version         # PowerShell 下不要接 | head -1
python -c "import edge_tts" || python -m pip install edge-tts   # Unix 用 python3 / pip3
```

网络需能访问 Microsoft TTS 服务（配音步骤）。渲染无需网络。

## 工作目录约定

```
<video_dir>/                  # 每条视频一个独立 Remotion 工程（从 assets/template-project 拷贝）
├── DESIGN.md                 # 简报 + 分镜表（含每镜 visualMin）
├── VOICEOVER_ZH.md           # 旁白稿：一段 = 一个场景，段落间空行分隔
├── build/
│   ├── durations.json        # tts.py 产出：逐段配音实测时长
│   ├── scenes.json           # 手写：[{id, visualMin, tail?, vo?}]，与分镜一一对应（进 git）
│   └── subtitles.srt         # build-timeline.mjs 产出：逐句外挂字幕
├── public/
│   ├── vo/sceneN.mp3         # tts.py 产出的分段配音
│   ├── sfx/*.mp3             # 音效素材（免费商用库拷入，见 references/sound-design.md）
│   └── bgm/bgm.mp3           # 背景音乐（可选）
├── src/
│   ├── timeline.ts           # build-timeline.mjs 生成（含 FPS），勿手改
│   ├── types.ts              # build-timeline.mjs 生成（SceneId 联合类型），勿手改
│   ├── Video.tsx             # 场景组件 + SFX 钉帧表 + 组装
│   └── lib/                  # theme / primitives / audio 三件套（模板自带）
└── out/                      # 渲染产物 + qa/ 静帧
```

## 八步工作流

| 步 | 做什么 | 产出 / 命令 | 细节 |
|---|---|---|---|
| 1 | 明确简报：主题、观众、时长、风格、品牌 | DESIGN.md 头部 | workflow.md §1 |
| 2 | 写旁白稿（一段=一场景）+ 分镜表（含 visualMin） | VOICEOVER_ZH.md + DESIGN.md 表格 | workflow.md §2 |
| 3 | 拷贝模板工程并装依赖 | `cp -r <skill>/assets/template-project ./ && npm install` | workflow.md §3 |
| 4 | 生成配音并测长 | `python3 <skill>/scripts/tts.py --script VOICEOVER_ZH.md --out . --voice yunyang` | workflow.md §4 |
| 5 | 写 build/scenes.json，生成时间线 | `node <skill>/scripts/build-timeline.mjs` | workflow.md §5 |
| 6 | 逐镜头实现场景组件，每镜头渲 2 张静帧自检 | `npx remotion still src/index.ts Video out/qa/x.png --frame=N` | animation-vocabulary.md |
| 7 | 声音设计：SFX 钉帧表 + BGM | Video.tsx 的 SFX 数组 | sound-design.md |
| 8 | 渲染双版本 + 音画抽查 + 交付 | 见下 | workflow.md §8 |

**渲染命令（第 8 步）：**

```bash
# 推荐：顺序渲染并复用已有成片，避免两个完整渲染任务互相争用 CPU/内存
node <skill>/scripts/render.mjs --mode both --concurrency 8
# 强制重渲：追加 --force；只渲染一个版本：--mode final 或 --mode nobgm
# 手动命令时，带 BGM 必须使用 props-bgm.json；无 BGM 使用 props-nobgm.json
# 音画抽查（成片音量应 mean ≈ -20dB、max ≤ -2dB 无削波）
ffmpeg -i out/final.mp4 -map 0:a -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

## 文件导航（何时读哪个）

| 时机 | 读 |
|---|---|
| 开始一条新视频 | 本文件 + `references/workflow.md`（全流程细节与坑） |
| 写场景组件 / 设计动画 | `references/animation-vocabulary.md`（8 种动画模式 + 代码） |
| 铺音频 / 选音效 / 混音 | `references/sound-design.md`（三层结构 + 钉帧规则 + 音量判例） |
| 搭工程 | 拷贝 `assets/template-project/`（含 theme/primitives/audio 三件套与示例场景） |
| 想看真实成片长什么样 | `examples/case-study-long-context.md`（2 分钟技术讲解片全程复盘） |
| 改了脚本想回归验证 | `node <skill>/scripts/selftest.mjs`（无需网络，覆盖解析/校验/时间线/字幕全部关键行为） |

## 硬规则（前人踩过的坑）

- **Root.tsx 必须渲染 `<MyComposition />`**（Composition 注册器），不是场景组件本身——否则报 "No video config found"。
- 场景组件的 fade 出点一律用 `D` prop（`fade(frame, D)`），不写死数字；时间线重建后自动正确。
- **长音效（>1.5s）必须给 `durationInFrames`**（SFX 表的 `d` 字段），否则声音拖到后续镜头。
- **fps 唯一来源是 timeline.ts 的 `FPS`**：Composition 的 `fps={FPS}`、spring 的 `fps: FPS` 都引用它；
  tts.py 的 `--fps` 改帧率后整条链自动一致，任何地方写死 30 都会失同步。
- VOICEOVER_ZH.md 里的 Markdown 标题（#）、引用（>）、代码块由 tts.py 自动剥离，
  只有正文段落进入配音——可放心用 `## 1 · hook` 组织稿子。
- `build/scenes.json` 与 DESIGN.md 分镜表是同一信息的两份拷贝，改分镜时两处同步（id / visualMin / tail / vo）。
- Windows：`--props` 一律走文件（shell 剥内联 JSON 引号），勿用 `echo >` 生成 props 文件
  （PowerShell 重定向写 UTF-16）——模板已预置 props-nobgm.json；命令用 `python`（无 `python3`），
  PowerShell 无 `head`/`cp`（拷贝用 `Copy-Item -Recurse`）。
- 音效目录只放确认过版权的免费商用素材；成片商用前自查。
- Remotion 对 >3 人公司需商业许可（个人与小团队免费）；edge-tts 免费但服务端可能限流（429 → 等几秒重试，脚本已内置 3 次重试）。
