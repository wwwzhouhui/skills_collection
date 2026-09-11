---
name: remotion-video-factory
description: 视觉从代码生长的技术讲解视频工厂：给一个主题，产出一条"图解动画 + AI 配音"的 MP4——结构图/矩阵/连线拓扑/图表/数字滚动全部用 Remotion + React/SVG 代码精确绘制（不用 AI 视频模型，杜绝公式乱码与连线漂移，可参数化、改数据自动重排），旁白由 TTS 逐段生成 + ffprobe 实测时长（默认 edge-tts 神经音色；`--engine clone` 支持自定义克隆音色服务，上传参考音频即可用真人音色配音，人声更真实），build-timeline.mjs 按实测时长自动重建时间线（场景 = max(视觉最短, 配音+40帧尾巴），画面永远跟着配音走、绝不被切断），三层音频混音（配音 + 可开关 BGM + 音效钉帧表），确定性渲染（禁随机数/当前时间），双版本交付（带 BGM + 无 BGM 供后期自配乐 + 逐句 SRT）。Use whenever the user wants 技术讲解视频、图解动画视频、科普/架构动画 + AI 配音、克隆声音/克隆音色做视频配音、矩阵/连线/图表动画视频、"给我一个主题做个会动的技术动画"、Remotion 视频、或强调"画面要精确/可改/文字不能乱码"的程序化视频 — 视觉主体是代码绘制的矢量图解（非实拍、非数字人、非产品界面复刻）时选本 skill。
---

# remotion-video-factory · 图解动画 + AI 配音 技术讲解视频工厂

给一个主题，产出 MP4：**画面 100% 由 Remotion + React/SVG 代码绘制**（精确、可参数化、改数据自动重排），**配音由 TTS 生成并按实测时长驱动时间线**（旁白永不被画面切走；默认 edge-tts 神经音色，`--engine clone` 可切换自定义克隆音色，人声更真实），三层音频混音，确定性渲染，双版本交付。

## 与其他视频 skill 的边界

| 内容特征 | 用哪个 |
|---|---|
| 图解/数据/结构是主角（矩阵、连线、图表、公式、流程） | **本 skill** |
| 口播稿为主、要 12 套风格快切、卡拉 OK 逐词字幕 | voice-to-video |
| 行业大会演讲视频（HTML PPT + 数字人 + 口型） | talk-video-studio |
| 复刻真实产品页面（截图 + 2.5D 运镜）/ 真人出镜 | 本 skill 不适合 |

> 模板按 **1920×1080 横屏**设计；竖屏需改 Composition 尺寸并自行重排布局。

## 铁律（每次都要遵守）

1. **视觉从代码生长**：一切图形用 React/SVG 组件绘制，参数来自数据；**禁止**截图当动画、禁止 AI 视频模型生成画面（公式必乱码、连线必漂移）。
2. **一段旁白 = 一个场景**；场景时长 = `max(visualMin, 配音实测帧数 + tail(默认40f))`，由 `build-timeline.mjs` 自动重建时间线——**改稿/换语速不手调任何一镜**，画面出点（`fade(frame, D)`）自动跟随。
3. **确定性渲染**：禁 `Date.now()` / `Math.random()` / 网络/环境变量依赖；伪随机一律 `mulberry32(seed)`。同样输入必须渲出同样的帧——这是可回归、可迭代的前提。
4. **三层音频独立可验证**：VO（主）+ BGM（`bgm` inputProp 开关，产出无 BGM 版供后期自配乐）+ SFX 钉帧表（`from: SHOTS.x.from + offset` 相对帧表达式，时间线平移自动跟随）。
5. **每镜头完成即 QA 静帧**（`npx remotion still --frame=...`），不攒到最后；全片渲完再抽帧回看关键镜头 + ffprobe/volumedetect 验收音轨。
6. **`src/timeline.ts` 与 `src/types.ts` 由脚本生成，勿手改**；手改数据只碰 `VOICEOVER_ZH.md`、`build/scenes.json`、`DESIGN.md` 三处。

## 八步流水线

```
0 环境自检     node scripts/check-env.mjs        （Node/ffmpeg/ffprobe/Python/edge-tts）
1 简报         写 DESIGN.md 头部：主题/观众/时长/风格/渠道
2 旁白+分镜    VOICEOVER_ZH.md（一段=一场景，单段≤120字）
               + DESIGN.md 分镜表（id/画面/动画模式/visualMin/SFX 计划）
3 搭工程       Copy-Item -Recurse assets\template-project → my-video
               npm install && npx tsc --noEmit     （模板自带静音占位，开箱可渲）
4 配音         python scripts\tts.py --script VOICEOVER_ZH.md --out . --voice yunyang
               → public/vo/sceneN.mp3 + build/durations.json（ffprobe 实测）
               要真实人声：加 --engine clone --ref-audio 参考音频 --ref-text 逐字稿
               （voice_id 自动存档复用；详见 workflow.md §4）
5 时间线       手写 build/scenes.json（id + visualMin）
               node scripts/build-timeline.mjs → timeline.ts + types.ts + SRT
6 场景实现     src/Video.tsx 每场景一个组件；逐镜头仍帧 QA
7 声音设计     SFX 钉帧表 + BGM；规则见 references/sound-design.md
8 渲染交付     node scripts/render.mjs --mode both --concurrency 8
               → final.mp4 + final-nobgm.mp4 + subtitles.srt + out/qa 静帧
```

每步的操作细节、产出与已知坑：**先读 `references/workflow.md`** 再动手。

## 文件地图

```
SKILL.md                        本入口
references/workflow.md          八步流程细节与坑（执行前必读）
references/animation-vocabulary.md   8 种动画模式 + 代码（矩阵点亮/连线生长/数字滚动/弹簧卡片…）
references/sound-design.md      三层音频 + 钉帧规则 + 混音验收
scripts/check-env.mjs           环境一键自检（跨平台）
scripts/tts.py                  旁白 → 分段配音 + durations.json（edge-tts / --engine clone 克隆音色双引擎；增量缓存/限流重试）
scripts/build-timeline.mjs      durations + scenes.json → timeline.ts + types.ts + SRT
scripts/render.mjs              单次渲染 + FFmpeg 派生双版本
scripts/selftest.mjs            回归自测（解析/校验/时间线/字幕，无需网络）
assets/template-project/        可直接拷贝的 Remotion 工程骨架（lib/theme/primitives/audio）
examples/case-study-long-context.md   实战复盘：《1M 上下文的秘密》125s 成片
```

## 改稿成本对照（向用户报告时按此说明）

- 改旁白 → 重跑 §4（tts.py）+ §5（build-timeline.mjs）+ 重渲；场景时长自动重建
- 改画面 → 改 Video.tsx 组件 + 逐镜 QA + 重渲
- 换 BGM → 换 `public/bgm/bgm.mp3` + 重渲（画面不必重渲，见 render.mjs `--force` 语义）

## 交付物（每次必须齐）

`final.mp4`（带 BGM）+ `final-nobgm.mp4`（后期自配乐用）+ `build/subtitles.srt`（逐句字幕）+ `out/qa/` 静帧；并向用户报告：成片路径、时长、两版差异、改稿/改画面各自重跑哪步。
