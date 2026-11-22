---
name: html-video
description: 用本机已安装的 html-video 项目把 HTML/CSS/数据渲染成真实 MP4（Hyperframes + Remotion 双引擎，23 个模板），并驱动它自带的本地 studio 网页端；也用于生成中文口播/科普/技术讲解视频（按解说句级节拍逐句揭示画面，画面每 3–5 秒有一次可见变化、与配音严格对齐）。当用户说「用 html-video 出片 / 做成一个口播视频 / 讲解视频 / 科普视频 / 打开 html-video studio / 用它的模板渲染视频 / HTML 转 MP4 / 这个视频用 html-video 生成 / html-video 渲染报错或画面不对（字体跳闪、时长不对、多帧混流、画面静止干等解说）」时使用。注意：不要把这个 skill 与「用代码手写 HTML 视频」的其他 skill 混用——本 skill 走的是本机 html-video CLI/studio。
---

# html-video（本机已安装）

- **仓库（= project root）**：`D:\临时\2026\9月\2026年9月19日\html-video`
- 上游：`https://github.com/nexu-io/html-video`（Apache-2.0，nexu-io / Open Design 团队）
- 定位：HTML→Video 元层。agent 选模板 + 写内容 → 无头 Chromium 录制动画 HTML → ffmpeg 编码成 MP4。全部本机完成，无按次渲染费用。

> **要做中文口播讲解片（画面每 3–5 秒有一次变化、画面与配音对齐）？**
> 直接照抄现成的提示词模板：`D:\临时\2026\9月\2026年9月19日\hermes-agent-html-video\PROMPT-TEMPLATE.md`
> 同级目录就是那条片的完整成品 + 全部构建脚本（可直接复用，别从零写）。做法与坑见本文档后面几节。

## 环境（已就绪，勿重复安装）

| 依赖 | 状态 |
|---|---|
| Node 22.14 / pnpm 9.15（corepack 按仓库 `packageManager` 锁定） | ✅ |
| ffmpeg 6.1.1（PATH 上 `D:\develop\ffmpeg\bin` 等） | ✅ |
| Chromium：Playwright `chromium-1243`（`%LOCALAPPDATA%\ms-playwright`） | ✅ |
| 可用 agent 后端：Claude Code / Codex / Gemini / Grok（studio 里可切换） | ✅ |
| MiniMax 音轨（BGM/旁白） | 可选，未配置则 studio 其余功能照常 |

## 命令速查

`html-video` 已通过 `pnpm link --global` 注册到 `%LOCALAPPDATA%\pnpm`（在 PATH 上），任意目录可用。**在仓库外调用时用 `--cwd` 指向仓库**，否则发现不到 23 个模板、`.html-video/` 状态目录也会建在别处：

```powershell
$HV = "D:\临时\2026\9月\2026年9月19日\html-video"

# 起 studio（默认 http://127.0.0.1:3071，仅监听 127.0.0.1；不会自动开浏览器）
html-video studio --cwd $HV --port 3071

# 体检：node / ffmpeg / chromium / 两个 adapter / 模板数（overall=ok 才算正常）
html-video doctor --cwd $HV

# 找模板：按意图打分返回（模板元数据在 templates/<id>/template.html-video.yaml）
html-video search-templates --intent "github stars race" --top 3 --cwd $HV
html-video inspect-template frame-glitch-title --cwd $HV    # 看 inputs schema / 时长 / license

# 脚本化出片（不带 agent 的最短路径）
$p = html-video project-create --name demo --intent "..." --aspect "16:9" --cwd $HV   # 输出 project_id
html-video project-set-template $id --template frame-glitch-title --cwd $HV
html-video project-set-var      $id --key title --value "HTML VIDEO ONLINE" --cwd $HV
html-video project-render       $id --output out.mp4 --cwd $HV
```

其他子命令：`list-engines` / `project-list` / `project-show` / `project-add-asset` / `project-remove-asset` / `project-set-vars`（从 JSON 文件批量设变量）/ `project-preview`（先出 HTML 预览再渲染）/ `project-delete`。

## 引擎与已知坑（改渲染前必读）

- **hyperframes**（默认，已接好）：CSS/GSAP 动画 HTML，逐帧录屏。字体跳闪（FOUT）只在导出 MP4 出现，studio 的 iframe 实时预览看不出来 → 验证载体只能是导出的 MP4，量早期帧。
- **remotion**（原生模板，如 `frame-data-rollup`）：模板自带 `source/entry.ts`，webpack 能 resolve 到 workspace 根的 react/remotion。
- **多帧混流 concat 不能用 concat demuxer + 重编码**：两引擎 timebase/PTS 不兼容会错误累加时间戳（8s 变 35s）。必须用 **concat filter**（每段独立 `-i` + `filter_complex concat=n=N:v=1`）。判混流输出要 `ffprobe` 量时长 + `ffmpeg -f null -` 全解码。
- 每帧时长硬约束走 `RenderConfig.durationMode='explicit'`；单帧快速预览仍是 `auto`（会自动 extend 覆盖用户设定）。
- 长任务（渲染/批量）在 Windows 上没有 `timeout` 命令，用工具自带超时。

## 本机对上游做的四处修补（未提交，`git diff` 可查；截至 c414ecc 共 +223/−28 行，3 个文件）

1. `packages/cli/package.json` → build 脚本里 POSIX `chmod +x dist/bin.js` 换成跨平台的 `node -e "fs.chmodSync(...)"`。**不改这个 `pnpm -r build` 在 Windows 上必然失败**（tsc 已成功、仅最后一步报错）。
2. `packages/cli/src/commands/doctor.ts` → 探测改用 Windows `where`（原为 Unix `which`）、补 Windows Chrome/Edge 路径、并识别 Playwright 自带的 Chromium。改前 doctor 在 Windows 上会误报 ffmpeg missing + chromium warning。
3. `packages/adapter-hyperframes/src/render.ts`（最大的一处，口播片管线的前提）→ 给录制开头的 `-ss` 裁剪加**两个环境变量开关**，默认行为与上游完全一致：
   - `HV_LEADIN_TRIM=0`：跳过 leadIn 墙钟裁剪。冻结式单文件 CSS 模板里 webm 第一帧就是解冻时刻，**没有死区可裁**；而 `leadInMs` 把 `newPage()` 耗时也算进去（实测 Windows+360 环境可达 ~10.7s），这一刀会连真实动画一起裁掉。渲染口播片**必带**。
   - `HV_TRIM_WHITE_HEAD=1`：改用帧级「白屏头裁剪」`detectWhiteHead()`——解码 webm 头 0.8s 为 64×36 灰帧，仅当开头连续纯白（均值≥250）且紧邻下一帧为暗（<60）才按帧裁，浅色底模板判据不成立不会被误伤。解决 playwright 录制器在导航提交前就出 about:blank 白帧、多镜头 concat 每次切换白闪的问题（chromium 的 `--default-background-color` 在 chrome-headless-shell 下与 `--remote-debugging-pipe` 互斥，启动参数这条路走不通，只能录后裁）。
4. `packages/adapter-hyperframes/src/render.ts` → `HV_REUSE_BROWSER=1` 把 chromium 提为**模块级单例**跨 `render()` 复用（context 仍每帧新建，recordVideo 的 sink 挂 context 不可共享），多帧导出省掉每帧一次浏览器启动（实测每帧 ≈10.9s）；配套导出 `closeSharedBrowser()` 供一次性脚本渲完释放（不关则 playwright 连接钉住 node 进程不退出）。默认不设变量时行为与上游逐字节一致。细节与实测见「渲染提速」节。

## 多帧口播片的最短路径（本项目实践验证过）

html-video 的多帧管线可以喂**任意自定义动画 HTML**，不必用内置模板 —— 做讲解/口播片走这条：

```js
const { bootstrap } = await import(
  pathToFileURL(join(HV, 'packages/cli/dist/context.js')).href
);                       // 直接复用 CLI 的 wiring，省掉自己拼 ProjectOrchestrator 依赖
const ctx = await bootstrap({ cwd: HV });

const project = await ctx.orchestrator.create({
  name, intent, preferences: { resolution: { width: 1920, height: 1080 }, fps: 30 },
});
await ctx.orchestrator.writeContentGraph(project.id, {
  schemaVersion: 1, intent: 'explainer', synopsis,
  nodes: scenes.map((s) => ({ id: s.id, kind: 'text', label: s.title,
                              frameIntent: 'narrated-explainer-frame',
                              durationSec: s.audioSec + 0.6, text: s.narration })),
  edges: scenes.slice(1).map((s, i) => ({ from: scenes[i].id, to: s.id, kind: 'sequence' })),
});
for (const s of scenes) {
  await ctx.orchestrator.writeFrameHtml(project.id, s.id, htmlOf(s));  // 任意 HTML
}
await ctx.orchestrator.exportMp4({ projectId: project.id, outputPath });
```

关键事实（源码级确认）：

- 帧 HTML 落在 `<root>/.html-video/projects/<id>/frames/NN-<nodeId>.html`，渲染时 `sourcePath` 就是它
  —— **完全可以不走模板**，自己写 HTML 即可。
- 多帧导出固定用 `durationMode: 'explicit'` 调引擎，所以 content-graph 里写的 `durationSec` 是**硬时长**
  （不足补尾帧、超出裁掉）。单帧快速预览仍是 `auto`，会被动画长度 extend。
- 想让画面跟着配音走：先把每场 TTS 出音频、`ffprobe` 量实测时长，再 `durationSec = 音频 + 固定尾巴`；
  合音频时用**同一个尾巴常量**，音视频时间轴才同源。改口播稿后必须重跑 TTS 并重渲（时长会变）。

### 口播片必须「按解说分拍揭示」，不能把动画全堆在开头

这是最容易犯、也最致命的错：把入场动画都放在开头 0–3s，而帧长 28–50s（由配音时长决定），
结果每帧 84–90% 的时间画面完全静止，观感就是「幻灯片放完动画后干等解说」。
实测本项目第一版：最大静止 35.0s、停滞占比 84%。改成按解说句级节拍铺开后：最大间隔 2.5–4.5s。

做法：帧源文件只标节拍，延迟在组装时从**配音的句级时间轴**反算。

```html
<div class="kicker r" data-beat="1">…</div>       <!-- 第 1 句解说的起始时刻 -->
<g class="nd rf" data-at="10.0">…</g>             <!-- 长句内部再分拍时用显式秒数 -->
<g class="nd core keep-rise" data-beat="2">…</g>  <!-- 入场 + 抵达后持续轻微呼吸 -->
```

```js
// build 阶段：从 audio/<场>.srt 读每句起始秒 → 生成 animation-delay
const PHASE_ADVANCE_SEC = 0.49;   // 见下，补偿适配器的相位提前
const delay = (target) => `${Math.max(0, target + PHASE_ADVANCE_SEC).toFixed(2)}s`;
// 注意选择器必须和 HTML 里字面一致：data-at="3.0" ≠ [data-at="3"]
```

三个要点：

- **元素靠 `animation-fill-mode: both` 实现「到拍才可见」**：每个元素都必须带一个入场类
  （`.r/.rf/.draw/.hairline/.keep-*`），否则它会从第 0 秒就显示出来。
- **入场延迟必须 `!important`**：帧内局部 `<style>` 里的 `.draw{animation:draw … both}` 这类**简写**
  会重置 `animation-delay`，且它在 body 里、文档顺序更靠后，不加 `!important` 会被它吃掉。
- **相位提前常数要实测，别猜**：适配器按 leadIn 用 `-ss` 裁掉录制开头，声明的 delay D 实际在成片
  D−0.49s 处出现。所以 `delay = 目标时刻 + 0.49`。这个常数会随机器/浏览器启动耗时略变，
  成片后必须复核（本项目复核结果：误差中位数 +0.20s，95% 落在 ±0.6s 内）。

### 两个专门给口播片用的质检工具

1. **画面停滞量化**：抽 2fps → 相邻帧逐像素差 → 二值化（滤 h264 噪声）→ 取「变化面积占比」，
   找最长停滞区间。用法 `node measure-motion.mjs [视频] [--pix=14] [--area=0.0015]`。
   **它必须做阈值敏感性分析**：本项目同一段成片，`pix=14` 时最大停滞 13s，`pix=6` 时只有 3.5s——
   低对比揭示（半透明横带、小芯片）在严阈值下会被误判成停滞。报告结论时两个读数都要给。
2. **节拍对齐复核**（两个工具，**适用边界不同，别混用**）：
   - `probe-phase.mjs` —— **权威**。手工挑「整块出现」的大幅元素（面板/横条/大标题），
     对**整场**扫描找出现时刻，反推相位提前量。9 个探针即可给出可信中位数。
   - `verify-beat-sync.mjs` —— **仅供交叉参考**。自动遍历所有节拍元素。实测在「密集分拍揭示」
     的构图里会把误差**系统性拉负约 1.4s**（元素包围盒里含背景与邻居内容的亮度，稀释了信号），
     所以它的中位数不能直接用来调常数。它的三种测量陷阱都写在文件头注释里：
     ① 观察窗太窄 → 提前出现的元素被截断，误差被压向窗口起点（踩过：误报 −0.92s 并据此改坏了常数）；
     ② 观察窗从帧开头扫 → 远处内容污染（踩过：误报 −5.62s）；
     ③ 不筛元素面积 → 小元素噪声主导（踩过：−1.80s）。

### 相位提前量是**渲染期的随机量**，不要指望用常数消掉

适配器按 `leadIn` 用 `-ss` 裁掉录制开头，而 `leadIn` = 「从 newContext() 到解冻」的耗时，
**随浏览器启动速度与机器负载浮动**。同一套帧连渲两轮，实测相位提前量分别是 **0.31s 和 0.75s**
（另一条 16:9 的片是 0.49s）。含义：

- 把 `PHASE_ADVANCE_SEC` 调到某一次实测值，下一轮渲染可能又偏。
- 务实做法：取多轮实测的**中位数**做常数（本项目取 0.40s），让误差期望接近 0；
  每轮成片后用 `probe-phase.mjs` 复核，只有偏差明显（>0.6s）才值得重渲。
- 观感上「视觉略早于解说」（−0.3 ~ −0.7s）比「画面滞后于解说」自然 —— 前者是视觉先导，后者像掉帧。
- 这一项**不影响**「每 3–5 秒有变化」的节奏目标（那是节拍密度的事），只影响画面与解说的贴合度。

### 竖屏（9:16）比横屏多做的四件事

1. **字幕几何必须重新实测**。libass 按**视频高度**缩放字号：16:9 用的 `FontSize=13` 放到 1080×1920
   会变成约 87px 高。用 `verify-subtitle.mjs --font=N --margin=M` 逐档实测（它会烧一条真实字幕再扫像素，
   报「单行字高 / 最大行宽 / 行数 / 是否侵入安全带」）。本项目竖屏定为 `FontSize=9` / `MarginV=32`：
   字高 44px（画面高 2.29%）、最长行宽 921px、全部单行、距底 214px。
2. **字幕要先拆短行**。TTS 原始 cue 中位数 37 字、最长 90 字，竖屏会折成 3–4 行、把字号压小。
   在合字幕那一步按标点拆成 ≤22 字的小段（时长按字数比例分配），全部变单行后才有空间放大字号。
3. **底部安全带放大**：横屏 158px → 竖屏 300px（画面高 15.6%），因为字幕更大、还要避开平台底部 UI。
4. **版式全面转纵向**：内容宽只有 896px，流程/对比/表格都要改成自上而下堆叠。

### 口播片多皮肤（--theme=）：一套帧源、八种配色出片

「为什么我生成的视频都是固定的」的正解：管线刻意绕开 html-video 的 23 个内置模板、
用一份自维护的 `_system.css` 视觉基座，所以默认全片一个皮肤。要换风格不必重写帧源，
把基座做成 token 层即可（qwen38-omni-video 项目已落地，可直接抄）：

- **三层架构**：① `_system.css` = 基础 token（--bg/--fg/--neutral/四语义色/--*-lite/字体/底纹参数）
  + 派生 token + 全部规则；② `skins/<名>.css` = `:root` 覆盖 + 可选规则覆盖，
  组装时注入在基座之后、节拍延迟之前（同特异性后来者胜，零 !important）；
  ③ `skins/skins.json` 登记皮肤名/深浅模式/`<html>` 内联底色（首绘即皮肤底色，防白屏首帧）。
  `build-frames.mjs --theme=<名>` 选择；布局常量（pad/字幕安全带）**不开放给皮肤**——皮肤只改颜色不改版式。
- **color-mix 是像素级安全阀**：透明度层级一律 `color-mix(in srgb, 色 p%, transparent)` 从基础 token 派生。
  srgb 下与 transparent 混色只改 alpha、RGB 通道精确不变，所以默认皮肤与硬编码 rgba 版
  **渲染结果一致**（实测判据：逐帧截图 diff>2 的像素 = 0，最大 ±1/255 为 8bit 取整；md5 会因取整不同，别拿 md5 当判据）。
- **`--neutral` 一个 token 扛下浅皮**：面板/网格/描线/.bx 填充全走「中性叠色层」，
  深色皮肤 = 白、浅色皮肤翻成黑，整套半透明层级自动变「浅底压深」，
  抵达可见性档位（≥11% 中性 / ≥20% 语义填充）不用逐条规则重调。
  `--*-lite`（大数字/高亮字用）在浅皮上要取**更深**的同色系，名字里的 lite 是「强调变体」不是「更亮」。
- **SVG presentation attribute 不认 var()/color-mix**：`fill="rgba(...)"` 这类属性必须改成
  CSS 类（基座里预置 `.mk-core/.mk-ctx/.mk-mute/.mk-ghost…` 共享类，写在 `<style>` 规则里的值可用 var()）。
  这是帧源 token 化时唯一的结构性改动点。
- **换肤后必做质检**：`measure-motion.mjs` 重跑抵达可见性（浅色皮肤尤其，语义色在浅底上的亮度差与深底不等价）；
  版式审计（audit-frames）不用重跑（盒模型不变）。字幕层/品牌层若不走 token 要明确标注「保持默认皮肤观感」。
- 皮肤预览不用渲视频：`build-skin-gallery.mjs` 每皮肤重组装帧 + playwright 截 2–3 个代表场终态
  （选帧要覆盖四语义色），拼一个本地 `皮肤画廊.html` 给用户挑，挑完再走全量渲染。

### 两个「看起来像缺陷、其实是测量伪影」的坑

- **切点 PSNR 检查要避开帧边界**。用 `-ss 切点±0.12s` 抽帧做 PSNR 时，抽帧可能落在同一帧内（累积时长偏差
  + 关键帧对齐），得到 41 dB 的「几乎相同」——误判成「切换不明显」。**取 ±0.5s 或 ±1.5s 处复核**
  （本项目 9/9 切点都是 16–19 dB，切换明确）。
- **帧首尾亮度对照**能快速判断「有没有散场感」：抽每帧 `开场+0.5s` 与 `结尾−0.2s` 的平均亮度，
  正常应是「开场暗、结尾亮」（逐步建满）。本项目 16→27，符合预期。


### 一个会让所有「冻结到终态」的 QA 失效的坑

审计/测量脚本习惯用 `*{animation-delay:0s!important;animation-duration:0s!important}` 把动画推到终态。
**一旦节拍延迟是 `[data-beat="N"]{animation-delay:…!important}`（特异性 0-1-0 > `*` 的 0-0-0），
冻结就失效**：延迟没被清零、时长被清零 → 量到的是「入场前那一帧」（元素还透明、还偏移 28px），
于是版式审计形同虚设（本项目踩过：`.hairline` 量到宽度 0）。
正解是绕开 CSS 特异性，用 Web Animations API：
```js
await page.evaluate(() => {
  for (const a of document.getAnimations()) {
    try { a.finish(); } catch { a.cancel(); }   // infinite 的 finish() 会抛，退回 cancel
  }
});
```

### 三个必踩的坑

1. **描线动画必须写 `<path pathLength="1">`**（XML 属性，不是 CSS）。只写
   `.ln{stroke-dasharray:1;stroke-dashoffset:1}` 而不给 `pathLength`，那条线会渲染成 **1px 点线**，
   而不是「整条线按比例描出」。实测 A/B：同一个 80px 线段，缺属性时像素墨量只有正确写法的 **50.0%**
   （精确 2.00×）——是明显的视觉缺陷。做帧时对每条 `ln`/`draw` 路径都加上。
2. **帧里不要引任何外部资源**（Google Fonts / CDN / 图片 / JS）。适配器在录制前要等
   `link[rel=stylesheet]` 与 `document.fonts` 就绪（单帧最长等 8s）；字体 CDN 在部分网络下不可达，
   会既拖慢渲染又触发字体跳闪（FOUT）。只用系统字体栈 + 纯 CSS 动画最稳。

3. **适配器会按 leadIn 用 `-ss` 裁掉录制开头**（`adapter-hyperframes/src/render.ts`：
   `seekSec = leadInMs > 200 ? (leadInMs - 120)/1000 : 0`，`leadInMs` 从 `newContext()` **之前**开始计）。
   上游没有任何配置能关掉它（**本机补丁加了开关**：`HV_LEADIN_TRIM=0` 跳过、`HV_TRIM_WHITE_HEAD=1` 改帧级白头条裁剪，见上文「四处修补」第 3 条），且**失败是静默的**——它有两种表现，都实测过：
   - **严重（短帧）**：机器忙、浏览器启动慢时 `context.newPage()` 实测可到 ~12s，`-ss 12.5` 打在一条
     只有 `duration+0.3s` 的 webm 上会**什么都不剩**。`ffmpeg` 仍然 **exit 0**，于是每帧 mp4 都是
     **262 字节空文件**，`render()` 照常返回成功，直到 concat 才报
     `Output file does not contain any stream`。**排查信号：逐帧 mp4 < 10KB。**
   - **轻微（长帧）**：帧长 ≫ leadIn 时能出片，但录制开头被切掉一段。实测（20s 匀速扫过全幅的测试帧、
     走完整 `exportMp4`）：动画**完整保留**（无冻结、无漂移、尾部正常），但存在**恒定 ~0.45s 相位提前**
     —— 每帧开场时入场动画已经跑了约 0.45s。所以**不要把关键信息只放在前 0.5s 的动画里**，
     也不要把入场延迟设得太小。
   - 规避：渲染时带 `HV_LEADIN_TRIM=0`（本机补丁，见「四处修补」第 3 条，本项目所有出片命令默认带上）；或帧长留足余量（本项目 27–50s，无恙）；
     **渲完必须逐帧查 mp4 体积 + ffprobe 时长**，别信 `render()` 的返回值。

### 渲染提速：确定性逐帧引擎（hyperframes CLI）与本机实测边界

问「有没有比 Chrome 实时录屏更快的替代」——**有，而且本机已装着**：
`packages/adapter-hyperframes/node_modules/hyperframes`（v0.4.45，上游 HeyGen 正主引擎）。
它不走 `recordVideo` 实时录屏，而是 **CDP `HeadlessExperimental.beginFrame` + `--deterministic-mode` +
chrome-headless-shell**：虚拟时钟逐帧推进（每帧恰好 1000/fps ms），N 个 worker 并行（每个 ≈256MB Chrome），
`-q draft/standard/high` 三档、`--gpu` 硬件编码、可出透明 webm/mov。同输入必同像素（顺带根治实时录屏的帧抖动与相位漂移）。
用法：项目目录放 `index.html`（body 标 `data-composition-id/data-width/data-height/data-start/data-duration`），
`node .../hyperframes/dist/cli.js render <dir> -o out.mp4 -w 4 -q draft`。
纯 CSS 动画帧**无需注册 window.__timelines 也能正确跑节拍**（实测 t=20s 抽帧与实时版相位一致），
只有 lint 提示；`var(--sans)` 等 CSS 变量字体会触发「无确定性字体映射」警告（我们零 webfont，无害，忽略）。

**但本机（Windows + 安全软件）实测它反而更慢**：46.9s 的 s2 帧，
实时录屏 ≈ 58s（47s 录制 + ~11s 启动）；CLI `-w 4` 3m04s、`-w 8`（自动降到 6）2m24s，
≈ 10 帧/s 总吞吐且加 worker 扩展性差 —— 瓶颈是**本机 Chrome 单帧光栅化 + PNG 编码成本**
（安全软件拖慢进程与文件 IO，与此前实测 newPage()≈10.7s 同源），不是引擎选型。
判断：**干净/服务器级机器上确定性并行会反超实时录屏**（Remotion 云渲染同理），本机则相反。

本机真正有效的提速手段（按性价比）：
1. ✅ **已实施：跨帧复用同一 browser（第 4 处本机补丁 `HV_REUSE_BROWSER=1`）**——
   `adapter-hyperframes/src/render.ts` 把 chromium 提为模块级单例（context 仍每帧新建：
   recordVideo 的 video sink 挂在 context 上不可共享）；并发第二份 render 自动各开专用浏览器；
   崩溃由 `isConnected()` 检出重启；**finally 里复用模式必须清残留 context**（中途 abort 会留下
   仍在录像的脏 context）。一次性脚本渲完要 `await closeSharedBrowser()`（同文件导出），
   否则 playwright 连接钉住事件循环、进程不退出（实测踩过：bench 打完日志仍 hang 到超时）。
   实测（3s 帧 ×6 连续 render，HV_LEADIN_TRIM=0）：不复用 137.9s（均 23s/帧）→ 复用 78.6s
   （均 13.1s/帧），**每帧省 ≈10.9s**（launch+close 税），输出时长逐帧 3.000s 无差。
   7 帧主片导出 ≈ 省 65s，字幕层同理。
2. **把渲染目录加入安全软件白名单**（Chrome/ffmpeg 子进程与临时目录），10.7s 启动大概率能砍到 ~2s。
3. 迭代期用 24fps + `ONLY=sN` 单场快验（已有），终版才 30fps 全量。
4. ✅ **已实施：长层分段并行录制（`build-avatar-layer.mjs --segments=K`）**——
   300s 实时录制的墙钟成本 = 视频长度，**降 fps 省不了时间**（曾以为能，实测路径不存在），
   正确做法是把长动画切成 K 段并行录：每段 HTML 给**所有**动画的 delay 平移 `-T0`
   （`dt(d)=d-T0` 一个 helper 搞定，含口型/门控/无限循环的 bob/pulse/bar——
   **漏一条无 delay 的动画，该元素相位就断在接缝**，r1 光环踩过），负延迟纯声明式、
   不碰适配器冻结/解冻时序，零竞态。等价性验证：分段页跑 1.5s 后的 computed 状态 vs 整层页
   WAAPI 钉到同一**effect 时刻**（注意 `currentTime`/`localTime` 都**不**扣 delay，
   真实关键帧位置 = `localTime − delay`；且状态和时间戳必须**同一个 evaluate** 里读，
   跨 evaluate 的十几 ms 漂移足以让秒级周期动画的 opacity 明显不同——两次误判踩过）。
   K 个 node 子进程各渲各段（录制几乎不吃 CPU，并行安全）→ concat：四段同 encoder，
   demuxer+`-c copy` 即可（时长不符自动退回 concat filter 重编码）。
   实测 K=4：**300s+启动 → 墙钟 183.7s**，拼接后 299.867s，与旧的连续版在三个接缝两侧
   |diff|>32 占比全 0.000%（PSNR 21–38dB 是独立重编码噪声，非差异，别拿它当判据）。
5. 换机器/上云时用 hyperframes CLI 确定性模式（`--docker` 出生产级可复现片），本机维持实时路径。
   实时路径本身也可分段并行（同 4 的负延迟手法按帧切），主片/字幕层若再压时间走这条。

### 帧的自动化 QA（人眼看不了像素时用）

- 版式：真实浏览器里量盒模型 —— 画布溢出 / 元素越界 / 压字幕安全带 / 顶层叠压 / 文字被裁。
  给帧留一条**底部字幕安全带**（本项目留 158px），烧字幕时才不会压内容。
- 描线：逐条取路径 bbox 截图、量「墨量像素 / (路径长×线宽)」，比值 ≈1 以上为实线、≈0.5 是点线。
- 同步：对每个场次切换点，量切点前后两帧的 PSNR；若切点位置正确，差异会非常大（本项目 17–20 dB）。
- 烧字幕是否成功：成片与无字幕版在**字幕带区域**做 PSNR，明显低于整帧 PSNR 即说明字幕已画上。
  注意 ffmpeg 的 `psnr` / `metadata=print` 统计走 **stderr**，用 `execFileSync(...).toString()` 读不到，
  要用 `spawnSync(..., { encoding: 'utf8' }).stderr`。
### 品牌三件套（右上角标 / 片尾卡 / 右下角 IP 数字人）——全部走图层叠加，主片零重渲

口播片要加固定品牌元素时，**不要动帧 HTML**（主片一次渲染 25+ 分钟），全部作为独立层在
`build-final` 合成期叠上去。三件套与配置源（本项目 `brand.json` 一份配置管全部）：

| 元素 | 生成方式 | 叠加方式 |
|---|---|---|
| 右上角作者角标 | playwright 截**透明 PNG**（`omitBackground:true`，按实测文本宽 clip） | `overlay=W-w-<margin>:<y>`（PNG 单帧输入，overlay 默认 eof_action=repeat 自动持续） |
| 片尾品牌卡（静默 ~7s） | html-video **单帧项目**（durationSec 硬时长），动画全部 CSS 节拍 | 主段 `trim=0:MAIN` 后与片尾段 **concat filter** 拼接（配 `anullsrc` 等长静音，`aformat=48000:stereo` 对齐主音轨） |
| 右下 IP 数字人（`layer.active` 从多预设里选一个渲染） | 纯黑底层 HTML，口型/说话门控**烘焙成关键帧**后整层实时录制 | 与字幕层同款 `colorkey=0x000000:0.010:0.020` + overlay |

数字人口型的 CSS 化（三帧交叉淡入淡出骨架移植自 ip-talking-head-lecture 的 Remotion `TalkingAvatar`）：

- **口型信号要用真实响度包络，不要用伪随机音节**（用户验收判据："嘴巴要和语音联动"）。
  build 阶段 `ffmpeg -i narration.wav -ac 1 -ar 8000 -f s16le -` 拿裸 PCM → 50ms 窗 RMS
  → 只在"说话窗"里取 p15 当噪声底、p90 当响度顶做归一 → `pow(…,0.75)` 抬中低响度 →
  快攻慢释 `m=max(raw, prev*0.72)`（升跟窗、降 ≈80ms 收口）。伪随机音节函数（参考 skill 原版）
  声音停了嘴还在动，观感就是"各说各的"。
- 包络按 20Hz 采样烘焙成 `@keyframes` 驱动注册自定义属性 `@property --m { syntax:'<number>' }`
  （注册后才能数值插值），300s 片 ≈6000 停/条；说话门控 `--spk` 用稀疏关键帧
  （从 `words.json` 词级时间戳合并区间，pad −0.12/+0.06s），句子间隙自动收口型+光环+声波条。
- 图层里透明度用 `opacity:calc(max(0,min(...var(--m)...)))` 表达三帧权重；光环/声波条 `opacity:var(--spk)`
  只在说话时出现。
- 素材：每形象 3 帧（闭口/微张/张口）webp（1024px PNG → `ffmpeg scale=360:360 -c:v libwebp -quality 82`，单张 10–15KB），base64 内联进 HTML。
- 联动验收工具 `check-mouth-sync.mjs`：解析烘好的 `--m` 序列挑响窗/轻窗/间隙三组时刻，
  对渲染出的层视频量**嘴部裁块 YAVG**（嘴越张、口腔暗部越大、YAVG 越低），判
  响窗显著更暗 + 轻窗≈闭口 + corr(env,−YAVG)≥0.5。嘴部坐标先目测一次写进 `brand.json → layer.mouthBox`。

**必踩的新坑**：

1. **IP 头像是一个新的遮挡区，必须逐场对终态静帧避让**。字幕安全带只预留了底部 230px，
   但帧内容普遍画到 y≈785（全宽装饰条、右对齐文字）。约束位是**各场最底文字的下沿**（本片实测
   s2 条内文字 y≈745），圆顶 = `cy − D/2 − 光环inset − bob幅度` 必须在它之下；实在放不下就
   缩小圆径（本片 200→110 才找到无文字冲突的角位）。边框/光环/声波条/投影要按 `D/200` 等比缩放，
   否则小尺寸头重脚轻。
2. **两版独立重编码之间不能用 PSNR>45dB 判图层独立性**：文字/面板边缘的编码噪声就能把干净
   区域拉到 ~34dB（实测；旧版 47dB 是因为无字幕版走了 `-c:v copy`）。改用「|diff|>32 像素占比」
   （`blend=difference,lut=y='if(gt(val\,32)\,255\,0)',signalstats` 取 YAVG/2.55%）：
   噪声只吃边缘零点（本片均值 0.00005%、峰值 0.0195%），污染会成片出现。
3. 片尾卡 CTA 若要「弹入 + 呼吸」两段动画，必须写在**同一条 `animation` 简写**里逗号并列
   （`.cta{animation:bounce .8s … 2.9s both, breathe 2.4s … infinite}`）；另起 `.cta.keep{…}`
   规则会整条覆盖简写，弹入直接消失。
4. 角标/数字人/字幕的叠加顺序 = 语义层级：数字人 → 字幕 → 角标（角标最顶，字幕盖数字人
   下缘无妨——面板不透明且只在底部出现）。
5. 品牌层质检并入合成分脚本：角标区/数字人区对**裸主片**做带内 PSNR（<40dB=叠上了），
   片尾段对 `outro.mp4` 比（>30dB=concat 没吃帧），全部用 `-t MAIN` 限长防止跨进片尾段。
6. **角标 PNG 的测量容器必须 `display:inline-flex`**：块级 flex 会占满 body 宽（本项目 640px），
   `getBoundingClientRect().width` 量到的是容器宽不是文字宽 → 截出的"透明 PNG"右侧带一大条
   空白，`overlay=W-w-<margin>` 时文字落在右上角**偏左一百多像素**（用户实测报缺陷）。
   改 inline-flex 后 PNG 从 640px 收缩到 264px 紧贴文字；clip 宽度再加 ~16px 给 text-shadow 余量，
   别把辉光裁出硬边。
7. **片尾卡配色必须跟主片同一套 token**（`_system.css` 的 --bg/--fg/--acc/--ctx/--core）：
   独立设计的浅色卡接在深色正片后面，用户第一反应就是"风格和视频不一致"。底用主片同款
   径向深底+网格点阵纹，主文字 #E9EDF5，划线用绿→蓝渐变，CTA 用主片强调色琥珀 #F5A524
   深底反白字。改卡不碰帧，重渲单帧项目 + 重合成即可。
8. **双 IP 并排是小尺寸才塞得下的妥协**：圆径 110 才能两个并排避开各场最底文字；用户想要
   参考片那种**大头像**（~150-300px）就只能留一个位（右下贴边），用 `brand.layer.active`
   在多个 preset 间选一个渲染，positions 各预设共享同一坐标。放大后重新逐场核避让：
   圆顶 cy−D/2 对 s2/s4 条文字下沿 745，圆底进字幕带无妨（字幕后叠在上层）。
9. **`@property --m` 必须 `inherits: true`，否则口型永远纹丝不动**：动画打在头像容器 `.a0` 上，
   真正读 `var(--m)` 算 opacity 的是它的**子元素**（三帧嘴部）；注册属性 `inherits:false` 时
   子元素永远拿 initial-value 0 → closed 帧恒 opacity:1，渲出来"像模像样"但嘴从不张合。
   小尺寸（110px）时目视几乎看不出来，本项目双 IP 版带着这个 bug 交付过一轮。
   **渲前必做 30 秒探针**：playwright 打开层 HTML，`getAnimations()` 逐条 `currentTime=1000*t`
   挑 3~4 个时刻（响窗/轻窗/间隙），读 `.open/.mid/.closed` 的 computed opacity 是否符合包络预期，
   再花 5 分钟整层录制。渲后还要用 `check-mouth-sync.mjs` 对嘴部裁块（先目测定坐标写进
   `brand.json → layer.mouthBox`）量 YAVG：嘴越张口腔暗部越大、YAVG 越低，判响窗显著更暗 +
   轻窗≈闭口 + corr(env,−YAVG)≥0.5。裁块要**紧贴嘴**（~48×28px）：框大了白毛均值稀释，
   口型全片的 YAVG 差不到 1，测了等于没测。

## 维护

```powershell
cd "D:\临时\2026\9月\2026年9月19日\html-video"
git pull; pnpm install; pnpm -r build      # 更新后重跑；本地四处修补可能产生冲突，冲突时按上面四条重做
html-video doctor --cwd .                  # 复检
```

移除：`pnpm rm -g @html-video/cli`（撤掉全局命令）、`Remove-Item -Recurse -Force <仓库>`（删仓库）。
