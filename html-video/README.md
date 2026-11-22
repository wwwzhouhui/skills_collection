# html-video · HTML→Video 元层 + 中文口播片流水线

把 **HTML/CSS 动画渲染成真实 MP4** 的本机工具链：上游 [nexu-io/html-video](https://github.com/nexu-io/html-video)（Apache-2.0，Hyperframes + Remotion 双引擎、23 个模板、自带 studio 网页端）负责「渲染引擎」，本 skill 沉淀的是**让它在 Windows 上跑通、并稳定产出中文口播/科普讲解片**的全部增量。全部本机完成，无按次渲染费用，不开剪辑软件。

一条文章的链接 → 一条 5 分钟、音画严格对齐、含逐词卡拉OK字幕与品牌包装的成片，就是这么来的。

```
文章/主题 ──► 口播稿+分场 ──► TTS 配音+词级时间戳 ──► ffprobe 实测时长
                                                          │  帧长 = 音频 + 0.6s 尾巴
自写动画 HTML（data-beat 节拍）──► html-video 多帧项目 ──► 逐帧渲染 ──► concat 主片
                                                          │
              字幕层（纯黑底逐词高亮，colorkey 叠加）──────┤
              品牌层（角标 PNG / 深色片尾卡 / 口型数字人）─┴─► 成片 MP4 + 无字幕版 + 音轨
```

## 它能做什么

- **用上游本体**：`html-video studio` 网页端、`search-templates` 模板检索、`project-render` 脚本化出片（23 模板开箱即用，未改动）。
- **口播片最短路径**（不走模板）：`bootstrap()` 复用 CLI wiring → `writeFrameHtml()` 喂**任意自定义动画 HTML** → `durationSec` 硬时长 → `exportMp4()`。
- **节拍驱动揭示**：画面跟着解说句级时间轴逐拍展开（每 3–5 秒有一次可见变化），杜绝「幻灯片放完动画干等解说」；入场延迟从配音 SRT 反算，相位提前量实测校准。
- **逐词卡拉OK字幕**：字幕层独立渲染纯黑底，`colorkey` 抠底叠加——有字幕/无字幕两版同源，字幕像素可独立验收。
- **品牌三件套**（全部图层叠加，主片零重渲）：右上角作者角标（inline-flex 紧贴真角落）、深色片尾卡（concat filter + anullsrc）、右下 IP 数字人（**真实响度包络驱动口型**：20Hz RMS → p15/p90 归一 → 快攻慢释，`@property inherits:true` 烘 6000 停关键帧；单 IP 配置可选）。
- **质检闭环**（5 个工具，机器判据可进门禁）：画面停滞量化（measure-motion，双阈值并报）、节拍对齐复核（probe-phase 权威 / verify-beat-sync 交叉）、口型-配音同步（check-mouth-sync）、字幕几何实测（verify-subtitle）、版式/描线/依赖扫描。

## 对上游的四处未提交补丁

| 文件 | 为什么 |
|---|---|
| `packages/cli/package.json` | POSIX `chmod +x` → 跨平台写法；**不改则 Windows 上 `pnpm -r build` 必失败** |
| `packages/cli/src/commands/doctor.ts` | Windows 体检：`where` 探测、Chrome/Edge 路径、识别 Playwright 自带 Chromium |
| `packages/adapter-hyperframes/src/render.ts` | 录制开头裁剪加开关：`HV_LEADIN_TRIM=0` 防动画被静默裁光（实测 newPage 可达 ~10.7s）、`HV_TRIM_WHITE_HEAD=1` 帧级白屏头检测消镜头切换白闪。**默认全关，行为与上游一致** |
| `packages/adapter-hyperframes/src/render.ts`（同文件第 4 处） | `HV_REUSE_BROWSER=1`：chromium 提为模块级单例跨帧复用（context 仍每帧新建），多帧导出每帧省 ≈11s 启动税；配套 `closeSharedBrowser()` 释放。默认关，行为与上游一致 |

补丁全部留在工作区（`git diff` 即完整补丁），`git pull` 升级后按 `SKILL.md`「四处修补」一节重做即可。

## 快速开始（出片命令）

```powershell
$HV = "D:\临时\2026\9月\2026年9月19日\html-video"   # 仓库 = project root
html-video doctor --cwd $HV                          # 体检 overall=ok 才算就绪
html-video studio --cwd $HV --port 3071              # 自带网页端
```

口播片走 `SKILL.md`「多帧口播片的最短路径」一节的 JS 范式（帧 HTML 直接喂），渲染命令固定带：

```powershell
$env:HV_LEADIN_TRIM=0; $env:HV_TRIM_WHITE_HEAD=1
```

## 完整知识在哪

`SKILL.md`（约 335 行）：环境表 / 命令速查 / 引擎与已知坑 / 四处修补 / 口播片最短路径 / 节拍揭示与相位提前 / 5 个质检工具与适用边界 / 竖屏（9:16）四件事 / 多皮肤（--theme=）/ 品牌三件套 / 12+ 条实测坑（`pathLength="1"`、零外链、leadIn 静默失败、`@property inherits`、测量伪影……）。

多皮肤参考包 `multi-skin-kit/`：八套皮肤（`skins/`，从上游 23 模板风格提炼，含规则覆盖层示例）+ token 迁移脚本 + 皮肤画廊脚本 + 接入四步说明。核心不变量：默认皮肤与 token 化重构前像素级一致（color-mix 只改 alpha），皮肤只改颜色不改版式与字幕安全带。

实践成品与可复跑脚本：`qwen38-omni-video` 项目（7 场 / 306.58s 成片，README 附全部验收读数）。

## 环境依赖

Node 22（corepack 锁 pnpm）、ffmpeg 6.x（PATH）、Playwright Chromium（`%LOCALAPPDATA%\ms-playwright`）、TTS 通道（小米 MiMo / 火山 / edge-tts，见相关项目脚本）。

## 作者与来源

- 上游引擎：[nexu-io/html-video](https://github.com/nexu-io/html-video)（Apache-2.0）
- 本机补丁 + 口播片方法论：wwwzhouhui，2026 年 9–10 月，经 4 条成片、5 遍全量重渲实测沉淀
