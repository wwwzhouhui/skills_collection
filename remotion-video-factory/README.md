# remotion-video-factory · 视觉优先的程序化视频工厂

> **一句话**：给一个主题，产出一条**图解动画 + AI 配音**的 MP4——技术结构图
> （矩阵/连线/图表/流程）全部由 Remotion + React 代码绘制，配音由 edge-tts 生成
> 并自动测长，时间线脚本重建，三层音频混音，双版本交付。

## 它能做什么

- ✅ **精确的图形动画**：注意力矩阵逐格点亮、拓扑连线生长、逐项激活、数字滚动、
  弹簧卡片——代码绘制，文字零乱码、结构可参数化、改数据自动重排
- ✅ **AI 配音自动对齐**：edge-tts 分段生成 + ffprobe 实测时长，
  `build-timeline.mjs` 按实测重建时间线（场景 = max(视觉最短, 配音+40f)），
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
# 0. 环境自检（Node / ffmpeg / ffprobe / Python / edge-tts）
node scripts/check-env.mjs

# 1. 拷贝模板工程并装依赖（PowerShell: Copy-Item -Recurse）
cp -r assets/template-project my-video && cd my-video && npm install

# 2. 写 VOICEOVER_ZH.md（一段=一场景；Markdown 标题/引用会被 tts.py 自动剥离）和 DESIGN.md 分镜表

# 3. 生成配音（需网络访问 Microsoft TTS；Windows 命令是 python，无 python3）
python3 scripts/tts.py --script VOICEOVER_ZH.md --out . --voice yunyang

# 4. 写 build/scenes.json（分镜 id + visualMin），生成时间线
node scripts/build-timeline.mjs

# 5. 在 src/Video.tsx 实现场景（动画模式见 references/animation-vocabulary.md）

# 6. 渲染双版本（props-nobgm.json 模板已预置）
npx remotion render src/index.ts Video out/final.mp4 --concurrency=4
npx remotion render src/index.ts Video out/final-nobgm.mp4 --props=props-nobgm.json
```

## 目录结构

```
remotion-video-factory/
├── SKILL.md                        # 技能入口：触发条件 + 八步工作流 + 硬规则
├── README.md                       # 本文档
├── scripts/
│   ├── check-env.mjs               # 环境一键自检（跨平台）
│   ├── selftest.mjs                # 回归自测：解析/校验/时间线/字幕（无需网络）
│   ├── tts.py                      # 旁白稿 → 分段配音 + durations.json（实测时长）
│   └── build-timeline.mjs          # durations + scenes.json → timeline.ts + types.ts + SRT
├── assets/
│   └── template-project/           # 可直接拷贝的 Remotion 工程骨架
│       ├── src/lib/                # theme（tokens）/ primitives（组件）/ audio（音频骨架）
│       ├── src/Video.tsx           # 3 场景示例（counter/matrix/cards）+ 组装模式
│       ├── props-nobgm.json        # 预置的无 BGM 渲染参数（Windows 免 echo 坑）
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

一键检查以上全部：`node scripts/check-env.mjs`（Windows / macOS / Linux 通用，
自动探测 `python` / `python3` / `py`）。

## 项目统计

**概要结论**：技能体积紧凑（≈285 KB、文本文件 28 个、代码 ≈1,063 行），覆盖
「旁白稿 → 配音测长 → 时间线重建 → 场景实现 → 声音设计 → 双版本渲染」全链路，
不依赖任何外部 API Key（配音走免费 edge-tts），模板工程自带占位音频、开箱即渲。

### 代码规模

| 统计项 | 数值 |
|---|---|
| 技能包体积 | ≈285 KB（含模板工程占位音频） |
| 文本文件 | 28 个：代码 15 · 配置 4（json）· 文档 9（md） |
| 代码行数 | ≈1,063 行（ts/tsx ≈403 · mjs 518 · py 142） |
| 脚本工具 | 5 个：check-env / selftest / tts.py / build-timeline / render |
| 模板场景示例 | 3 个（counter 数字滚动 / matrix 交错网格 / cards 弹簧卡片） |

### 能力参数

| 参数 | 规格 |
|---|---|
| 输出画幅 | 1920×1080 · 30fps（FPS 统一引用 timeline.ts，`--fps` 可全局改） |
| 音画对齐 | 一段旁白 = 一场景；时长 = max(visualMin, 配音 + 40f) |
| 动画模式 | 8 种：counter / stagger-grid / filter-transition / svg-lines / incremental-activation / spring-cards / progress-fill / typographic-hold |
| 音频层 | 3 层：VO(1.0) + BGM(≈0.34，可开关) + SFX 钉帧表（相对帧表达式） |
| 交付物 | 带 BGM + 无 BGM 双版本 · 逐句 SRT 字幕 · QA 静帧 |
| 实战案例 | 《1M 上下文的秘密》125s · VO + BGM + 28 SFX 点 · 双版本 |

### 版本与支持

| 依赖 | 要求 |
|---|---|
| Node.js | ≥ 18（实测 24 可用） |
| Python | 3.10+（配音链路，需联网访问 Microsoft TTS） |
| ffmpeg / ffprobe | 必需（编码 / 测长 / 抽查） |
| Remotion | 随模板工程锁定（个人与 ≤3 人团队免费） |
| 平台 | Windows / macOS / Linux（自动探测 `python` / `python3` / `py`） |

## 许可与署名

- 成片归使用者所有，可直接商用
- [Remotion](https://github.com/remotion-dev/remotion) 本体：个人与 ≤3 人团队免费，
  更大团队需商业许可（渲染引擎许可，与本 skill 无关但需自知）
- edge-tts 为微软免费神经网络语音（服务端可能限流，脚本已内置重试与超时保护）
- 音效/BGM 素材授权自行把关：只放确认过授权的免费商用素材

## 更新说明

一句话摘要：截至 **2026-09-07**，最新 **v1.1.0** 完成审查修复（旁白稿 Markdown 结构行
剥离、时间线/字幕/短场景淡入淡出健壮性加固）并新增一键环境自检；
**v1.0** 为技能首版，沉淀自实战成片《1M 上下文的秘密》。

**版本记录：**

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
