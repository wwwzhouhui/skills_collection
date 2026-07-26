# 教学视频编写规范 (HyperFrames)

> 写 `index.html` 时的硬规则。模板 `assets/video-template/index.html` 已内置引擎
> (转场/字幕/时间轴), 你只写场景内容和入场编排。违反本文规则的组合 lint 能过但渲染必坏。

## 管线顺序 (不能乱)

```
storyboard.json ──→ minimax_tts.py (minimax|edge|say) ──→ scaffold_video.py ──→ 填场景内容 ──→ build_video.sh
                    (先出音频)          (生成骨架,             (AI 只写 SVG      (lint + validate
                                        时间轴/配色已填好)       + 卡片 + 编排)     + render + 蒙太奇)
```

**先 TTS 再脚手架**: 场景时长由音频实际长度决定。`scaffold_video.py` 会把 durations.json
的时间轴、audio 标签、SEGMENTS、主题配色全部填好 — **不要手抄数字, 不要手搭骨架**。
示意图零件从 `references/svg-parts.md` 拷, 别从零画。

**重跑 TTS 后 (换音色/改旁白) 不要手抄新数字** — 用 `python3 scripts/sync_timeline.py <project_dir>`
一键同步时间轴, 然后重新渲染。

## 场景内容要求

每个子概念场景 (s2-s6) 必须有, 缺一即空壳:

1. **section-chip** — 左上角编号 + 小节名
2. **示意图** — `diagram-zone` 里的 SVG, 是场景的主角。振动画振动、波形画波形,
   对比类概念画上下两条对比 (高频 vs 低频)。SVG 元素给 id, 用 GSAP 画入场
3. **info-card** — 右侧要点卡片, 2-4 行 + 可选公式行 (公式用 Unicode: · × ÷ ₁ ₂ ⁸)
4. **callout 标注** — 至少一条"指哪讲哪": SVG 里画线+圆点, 文字用 `.callout-label`
5. **ghost 编号** — 底纹编号, **与 chip 同号** (场景 2-7 = 01..06); 标题页不放

标题段 (s1): 主题图标 SVG + 大标题 + 子概念胶囊排 + 副标题。
总结段 (s7): 大数字/公式 + 小结卡片 + summary-bar 徽章排。

**画面 ≠ 字幕**: 卡片写要点短语, 字幕显示旁白原文, 两者不重复。

## SVG 示意图画法

- viewBox 随手定 (如 `0 0 800 620`), CSS 已设 `overflow: visible`
- 线条粗细 4-8px (视频里 1-2px 线不可见), 颜色用 `var(--primary)` 等配色变量
- 描边入场: CSS 设 `stroke-dasharray: <len>; stroke-dashoffset: <len>`,
  GSAP 用 `tl.fromTo(el, { strokeDashoffset: len }, { strokeDashoffset: 0, ... })`
- 波形直接用 `<path d="M0,100 Q50,40 100,100 T200,100 …">` 或 polyline 采样正弦
- 文字标签 `font-size` ≥ 24, 填 `var(--ink)`

## GSAP 硬规则 (渲染器是非线性 seek 的, 这些坑 lint 查不出)

1. **一律 `tl.fromTo()`**, 不用 `tl.from()` — from 的 immediateRender 在 seek 时会闪现/失踪
2. **退场动画禁用** (除最后一段) — 转场就是退场, 转场开始时场景内容必须完整可见
3. **同一元素不叠两个 transform tween** — 入场 y + 环境 scale 要分别挂在父子两层
4. **环境动效必须挂 `tl`**, 裸 `gsap.to()` 在渲染时不动
5. **禁 `repeat: -1`** — 按段时长算有限次: `repeat: Math.ceil(dur / cycle) - 1`
6. **禁 `Math.random()` / `Date.now()` / async 构建时间轴**
7. 淡出后的元素要 `tl.set(el, { visibility: "hidden" }, t)` 硬杀, 防止被后续 tween 复活
   (模板引擎对场景和字幕已做, 场景内自己加的淡出要自己杀)

## 视觉体系 v2 (模板已内置, 写场景时遵守)

- **60-30-10 配色**: 主色只给示意图主体/公式/大数字/编号; 标签、kicker、结构线一律
  `var(--neutral)` / `var(--line)` 冷中性。见 color-palettes.md 的 CSS 映射
- **字体分工**: 大标题/大数字/公式 = `"Songti SC", serif` (宋体, 已在 .t-hero/.formula 设好);
  正文/标签 = 黑体。不要给正文上宋体
- **卡片**: card-title 是 kicker (小字 + 0.35em 字距 + 规则线), 不是大色块; 标题信息由
  section-chip 承担, 卡片标题写短词
- **质感层**: 场景 ::before 双网格+双射光、::after 纸张颗粒、.ghost 宋体底纹编号,
  模板自带, 别删

## 持续动效 (让"物理"动起来, 比入场动画更重要)

- **波形**: `data-wave` 加 `"flow":true`, svg 加 `style="overflow:hidden"` 和
  `data-layout-allow-overflow` (flow 多生成一个波长, inspect 会报 overflow, 属预期),
  draw 完成后调 `flowWave(sel, t, sceneEnd)` — 波形按统一波速滚动, 频率高的自然更密
- **扩散**: 同心圆/波弧用"发射循环": `fromTo(scale 小→大, opacity 有→无, repeat N)`,
  逐环错开 0.5s, 比 yoyo 呼吸更像真实传播 (markup 里 opacity 先置 0)
- repeat 次数一律按剩余场景时长算: `Math.ceil((sceneEnd - t0) / cycle)`

## 动效编排 (每场景)

- 第一个入场 offset `t + 0.2` 起 (转场占掉 0-0.6s), 不要 t+0
- 每场景 ≥3 种 ease、≥2 个入场方向; 全用 `y:30, opacity:0` = 没编排
- 节奏: 示意图先画 (0.2-1.2s) → callout 弹出 → 卡片滑入 (旁白讲到要点时) → 停住呼吸
- 每场景一个环境动效 (波纹呼吸/图标浮动/箭头脉动), 场景间要换花样
- 入场用 `.out` 系 ease; 时长快 0.3 / 中 0.5 / 慢 0.8, 一个场景里要有对比

## 尺寸 (视频不是网页, 小了看不见)

| 元素 | 最小值 | 模板类 |
|---|---|---|
| 大标题 | 130px+ | `.t-hero` |
| 场景标题 | 48px+ | `.t-title` |
| 卡片正文 | 30px | `.info-card p` |
| 字幕 | 34px | `.subtitle` |
| 标注 | 26px | `.callout-label` |
| SVG 线条 | 4px | — |
| 装饰透明度 | ≥10% | `.ghost` |

## 中文字体

`font-family: "Heiti SC", "PingFang SC", "Noto Sans CJK SC", sans-serif` (模板已设)。
渲染走本机 headless Chrome, 用系统字体; Linux 上确认装了 Noto Sans CJK, 否则中文变豆腐块。

**系统字体必须有显式 `@font-face { src: local("...") }` 声明** (模板已带), 否则 lint 报
`font_family_without_font_face` error。

## 实测过的 lint 坑

| 现象 | 修法 |
|---|---|
| `font_family_without_font_face` error | 系统字体加 `@font-face { src: local("字体名") }` |
| `duplicate_audio_track` warning 刷屏 | 每个 `<audio>` 写 `data-duration` (= durations.json 的 audio_duration) |
| `overlapping_gsap_tweens` on scale | 入场 tween 和环境动效叠了同一元素的 transform — 环境动效挂子元素 (内层 span / SVG 子节点) 或改成 opacity 脉动 |
| `composition_file_too_large` warning | 单文件 7 场景约 450 行, 这条可接受, 不拆 |
| inspect 报 "Two text blocks overlap" | **不要凭经验放过**。实测: 将军饮马 s2 的点标签 "B" 和中文注 "帐篷" 都放在点右上, 完全叠住, inspect 报了 warning 却被当成"标签贴点属正常"放过, 直到成片才被人眼发现。规则: 点的字母标注和中文说明必须错开方位 (如字母右上、中文右下), 逐条核对 overlap warning |
| inspect 报 chip/summary-bar 出画 (info) | push-up 转场移动整场造成, 预期行为, 可忽略 |
| 虚线画完变实线 | `drawIn()` 会把 `stroke-dasharray` 覆盖成整段长度 — 虚线元素 (参考线/辅助线) 用 opacity 淡入, 不用 drawIn |
| validate 报 `.num` 对比度 1.06:1 | 已知误报: 元素自带背景色 (chip 编号圆) 时审计采样不到它, 白字对深色圆实际 >10:1, 忽略。`#chapter` 等无自带底色的元素报警是真问题, 必须调色 |
| `²` 上标渲染为空白 | **Songti SC 缺 ²(U+00B2) 字形**。`.diagram-zone` 里的 SVG 文字被 CSS `font-family: inherit` 覆盖成黑体所以没事; 用宋体的地方 (`.formula`/`.t-hero`/zone 外的 SVG) 会空档。规则: HTML 公式写 `a<sup>2</sup>` (模板有 `sup` 样式), 宋体 SVG 文字用 `<tspan font-size="小" dy="-N">2</tspan>` |

## 检查清单

```bash
npx hyperframes lint            # 结构错误 (必须 0 error)
npx hyperframes inspect         # 文字溢出/出画 (逐条修)
npx hyperframes preview         # 人眼过一遍: 转场处内容是否完整、字幕是否跟上旁白
bash scripts/build_video.sh .   # lint + render + 蒙太奇
```

渲染后必看蒙太奇 `preview/montage.png`: 7 格里有没有空场景、文字重叠、配色跑偏。
