# remotion-video-factory · 视觉优先的程序化视频工厂

> **一句话**：给一个主题，产出一条**图解动画 + AI 配音**的 MP4——技术结构图
> （矩阵/连线/图表/流程）全部由 Remotion + React 代码绘制，配音由 TTS 生成
> （默认 edge-tts；`--engine clone` 可用自定义克隆音色，真人声更真实）
> 并自动测长，时间线脚本重建，三层音频混音，双版本交付。

## 它能做什么

- ✅ **精确的图形动画**：注意力矩阵逐格点亮、拓扑连线生长、逐项激活、数字滚动、
  弹簧卡片——代码绘制，文字零乱码、结构可参数化、改数据自动重排
- ✅ **AI 配音自动对齐**：edge-tts 分段生成 + ffprobe 实测时长（或 `--engine clone`
  克隆音色引擎），`build-timeline.mjs` 按实测重建时间线（场景 = max(视觉最短, 配音+40f)），
  旁白永不被画面切走
- ✅ **三层音频**：配音 + BGM（淡入出，可开关）+ SFX 钉帧表（相对帧表达式，
  时间线平移自动跟随）
- ✅ **确定性渲染**：同样输入永远渲出同样的帧；工程 git 可管
- ✅ **双版本交付**：带 BGM 版 + 无 BGM 版（后期自配乐）+ 逐句 SRT 字幕
- ✅ **改稿成本极低**：改旁白 → 重跑两个脚本；改画面 → 改组件；互不影响

## 与其他视频方案的边界

| 内容特征 | 用哪个 |
|---|---|
| 图解/数据/结构是主角（矩阵、连线、图表、公式、流程） | **本 skill** |
| 口播稿为主、要 12 套风格快速切换、卡拉OK逐词字幕 | voice-to-video |
| 复刻真实产品页面（截图 + 2.5D 运镜） | video-shotcraft |
| 真人出镜 / 实拍剪辑 | 都不适合 |

> 当前模板按 **1920×1080 横屏**设计（Composition 尺寸与场景坐标均为横屏）。
> 竖屏 9:16 需改 Composition 的 width/height 并自行重排布局，本 skill 未提供竖屏预设。

## 快速开始

```bash
# 0. 环境自检（Node / ffmpeg / ffprobe / Python / edge-tts / requests）
node scripts/check-env.mjs

# 1. 拷贝模板工程并装依赖（PowerShell: Copy-Item -Recurse）
cp -r assets/template-project my-video && cd my-video && npm install

# 2. 写 VOICEOVER_ZH.md（一段=一场景；Markdown 标题/引用会被 tts.py 自动剥离）和 DESIGN.md 分镜表

# 3. 生成配音（需网络访问 Microsoft TTS；Windows 命令是 python，无 python3）
python3 scripts/tts.py --script VOICEOVER_ZH.md --out . --voice yunyang
# 3'. 可选：克隆音色（更真实的人声；首次传参考音频建立音色，之后自动复用 voice_id）
python scripts/tts.py --engine clone --script VOICEOVER_ZH.md --out . --ref-audio ref.wav --ref-text "参考音频逐字文稿"

# 4. 写 build/scenes.json（分镜 id + visualMin），生成时间线
node scripts/build-timeline.mjs

# 5. 在 src/Video.tsx 实现场景（动画模式见 references/animation-vocabulary.md）

# 6. 渲染双版本（顺序执行，避免两个 Chromium/FFmpeg 任务互相争用资源）
node scripts/render.mjs --mode both --concurrency 8
# 只重渲一个版本：node scripts/render.mjs --mode final --concurrency 8 --force
# 带 BGM 必须显式传 props-bgm.json；无 BGM 使用 props-nobgm.json
```

## 目录结构

```
remotion-video-factory/
├── SKILL.md                        # 技能入口：触发条件 + 八步工作流 + 硬规则
├── README.md                       # 本文档
├── scripts/
│   ├── check-env.mjs               # 环境一键自检（跨平台）
│   ├── selftest.mjs                # 回归自测：解析/校验/时间线/字幕（无需网络）
│   ├── tts.py                      # 旁白 → 分段配音 + durations.json（edge-tts / 克隆音色双引擎，带增量缓存）
│   ├── build-timeline.mjs          # durations + scenes.json → timeline.ts + types.ts + SRT
│   └── render.mjs                  # 单次 Chromium 渲染 + FFmpeg 派生双版本
├── assets/
│   └── template-project/           # 可直接拷贝的 Remotion 工程骨架
│       ├── src/lib/                # theme（tokens）/ primitives（组件）/ audio（音频骨架）
│       ├── src/Video.tsx           # 3 场景示例（counter/matrix/cards）+ 组装模式
│       ├── props-bgm.json          # 带 BGM 渲染参数
│       ├── props-nobgm.json        # 无 BGM 渲染参数
│       └── public/                 # vo/sfx/bgm 目录（自带静音占位，开箱可渲）
├── references/
│   ├── workflow.md                 # 八步流程细节与坑
│   ├── animation-vocabulary.md     # 8 种动画模式 + 代码
│   └── sound-design.md             # 三层音频 + 钉帧规则 + 混音验收
└── examples/
    └── case-study-long-context.md  # 实战案例：《1M 上下文的秘密》全程复盘
```

## 环境依赖

| 依赖 | 用途 | 检查 |
|---|---|---|
| Node ≥18 | Remotion 渲染 | `node --version` |
| ffmpeg + ffprobe | 编码 / 测长 / 抽查 | `ffmpeg -version` |
| Python 3.10+ & edge-tts | 配音（需网络） | `python3 -c "import edge_tts"` |
| Python requests（可选） | 克隆音色引擎 `--engine clone` | `python3 -c "import requests"` |

一键检查以上全部：`node scripts/check-env.mjs`（Windows / macOS / Linux 通用，
自动探测 `python` / `python3` / `py`）。

## 许可与署名

- 成片归使用者所有，可直接商用
- [Remotion](https://github.com/remotion-dev/remotion) 本体：个人与 ≤3 人团队免费，
  更大团队需商业许可（渲染引擎许可，与本 skill 无关但需自知）
- edge-tts 为微软免费神经网络语音（服务端可能限流，脚本已内置重试与超时保护）；
  `--engine clone` 走自定义克隆服务（默认 https://omnivoice.duckcloud.fun，`--base-url` 可换），
  固定 seed 保证同稿重跑结果一致
- 音效/BGM 素材授权自行把关：只放确认过授权的免费商用素材

## 版本记录

- **2026-09-10 v1.2.1**：Windows 渲染兼容修复 + 克隆并发实测校准。
  ① render.mjs 修复 Node ≥18.20/20.12 下直接 spawn `npx.cmd`（shell:false）
  报 EINVAL 的问题，改为 `cmd /c npx` 调用；② 模板 remotion.config.ts 增加
  浏览器回退：本地无 Remotion Headless Shell 缓存时（首次渲染联网下载慢/被墙）
  自动改用系统 Chrome/Edge，避免渲染无限挂起；③ tts.py 新增
  `--clone-concurrency N` 并发请求克隆服务（1–8，默认 1 串行）——严格对照实测
  当前服务为单 worker 排队，并发 3 路反而慢约 26%，故默认串行，服务端扩容后
  可调大；主流程重构为「缓存检查（串行）→ 合成（可并发）→ 统一测长（有序）」，
  线程安全日志；④ 首个克隆音色实战成片验证（《光合作用》124s 科普片，
  5 段克隆配音 + 程序化 BGM/SFX + loudnorm 响度归一化流程）。
- **2026-09-08 v1.2.0**：新增克隆音色引擎。tts.py 支持 `--engine clone`
  （自定义 OmniVoice 克隆服务，默认 https://omnivoice.duckcloud.fun）：
  `--ref-audio`/`--ref-text` 上传参考音频建立音色，voice_id 自动存
  build/clone-voice-id.txt 复用；服务返回 WAV 自动转 MP3，下游
  build-timeline/render 零改动；固定 seed（默认 42）保证确定性；
  `--num-steps 16` 可提速；check-env.mjs 增加 requests 检查；修复 BOM 残留。
- **2026-09-07 v1.1.0**：审查修复。① tts.py 剥离 Markdown 结构行（模板的
  `## 标题`/`> 引用` 不再被读进配音）+ 合成超时保护 + rate 格式校验；
  ② build-timeline.mjs 校验重复 id / 非法 visualMin / 零时长，types.ts 每次自动
  重生成，timeline.ts 导出 FPS（Composition 与 spring 统一引用），SRT 改逐句切分；
  ③ fade() 对 <37f 短场景自动缩短淡入淡出；④ 模板预置 props-nobgm.json，
  .gitignore 不再误吞手写的 scenes.json；⑤ 新增 check-env.mjs 一键环境自检；
  ⑥ 文档补 Windows 命令等价与横屏声明。
- **2026-09-07 v1.0**：技能创建。从实战项目《1M 上下文的秘密》
  （125s 技术讲解片，VO+BGM+28 SFX 点，双版本交付）沉淀；
  模板工程零配置可渲（静音占位音频）；tts.py / build-timeline.mjs 端到端验证。
