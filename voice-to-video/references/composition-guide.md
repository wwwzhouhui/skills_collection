# 合成指南 — composition.html 编写规范

合成页 = `kit.css`（设计系统）+ `engine.js`（确定性引擎）+ 你的场景 HTML + 时间轴数据。
本文件是给 agent 看的编写规范：怎么分场景、怎么用动画属性、怎么对齐 timeline.json。

## 1. 文件准备

从技能 `assets/` 拷贝三件到项目目录：`kit.css`、`engine.js`、`template.html`（改名 `composition.html`）。
**不要**改 engine.js；设计系统可在 kit.css 基础上覆盖或整体替换（保留 `#hf-subtitle`、`#hf-progress*`、`#stage`、`.scene` 的样式约定）。

## 2. 时间轴对齐（最重要）

`tts.py` 产出的 `build/timeline.json`：

```json
{
  "meta": {"audio_ms": 43500, ...},
  "sentences": [
    {"i": 0, "text": "第一句口播。", "start": 180, "end": 2400, "hold_end": 2600,
     "words": [{"w": "第一句", "t": 180, "d": 420}, ...]},
    ...
  ]
}
```

对齐规则（**画面、语音、文字稿逐句对应**的来源）：

- **一句口播 = 一个 `.scene`**（很短的连续两句可合一个场景）。
- `data-start` = 该句 `start`；`data-end` = 该句 `hold_end`（句间停顿时画面不空窗）。
- 最后一个场景可只写 `data-start`，引擎自动停到片尾。
- 场景里出现的数字/关键词必须来自该句文字稿，**禁止**画与当前句子无关的内容。
- 场景内的强调元素用 `data-delay` 错峰出现：句子念到该词的时间点 ≈ 该词 `words[].t`，把 delay 设成 `词.t - 场景.start`。

## 3. 场景骨架

```html
<section class="scene" data-start="180" data-end="2600">
  <!-- 内容 -->
</section>
```

- `.scene` 绝对定位铺满舞台；布局直接写内联 flex/grid 或加专属 class 到 `<style>`。
- 页眉页脚放在 `.scene` 外（`.hf-header` / `.hf-footer`），全程可见。
- 引擎容器三件套必须保留：`#hf-subtitle`、`#hf-progress`、`#hf-playhint`。

## 4. 动画属性（data-anim）

引擎用 JS 逐帧计算样式（不用 CSS transition/animation，保证可 seek、可复现）。

| 属性 | 说明 |
|---|---|
| `data-anim` | 类型：`fade` `up` `down` `left` `right` `pop` `wipe-l` `wipe-r` `count` `type` |
| `data-delay` | 距场景开始的毫秒数（默认 0） |
| `data-dur` | 动画时长毫秒（默认 500） |
| `data-ease` | `out`(默认) `in` `inout` `back` `spring` `linear` |
| `data-out` | 出场类型（同上，可选），在场景结束前 350ms 自动退场 |
| `data-out-dur` | 出场时长（默认 350） |
| `data-count` | `count` 类型的目标数字（数字滚动，配 `data-suffix`） |
| — | `type` = 打字机，作用于纯文本元素 |

示例：句子念到 "37 秒"（word.t=8600，场景 start=7900）时数字滚动：

```html
<div class="big-num" data-anim="count" data-count="37" data-suffix="s"
     data-delay="700" data-dur="900">0</div>
```

示例：要点列表逐条随语速进入（每条约 2.5s 的句子）：

```html
<li data-anim="left" data-delay="200">…</li>
<li data-anim="left" data-delay="900">…</li>
<li data-anim="left" data-delay="1600">…</li>
```

## 5. 自定义逐帧动画

需要精细控制时（如图表生长、进度环）：

```js
HF.on(function (t) {
  var p = HF.easeOut(clamp((t - 9000) / 1200, 0, 1));  // 也可自己写缓动
  document.getElementById("bar").style.width = (p * 62) + "%";
});
```

规则：只允许在 `HF.on` 回调里改样式；**禁止** `setTimeout`/`requestAnimationFrame`/`Date.now()`/`Math.random()`（破坏确定性与 seek）。

## 6. 场景类型速查（kit.css 现成组件）

| 场景 | 用法 |
|---|---|
| 封面 | `.kicker` + `.title-xl`，居中 flex |
| 要点 | `.title-lg` + `ul.bullets`（3-4 条，每条 ≤18 字） |
| 命令/终端 | `.term`（`.bar` 三个圆点 + `.body` 逐行 `$` 命令） |
| 大数字 | `.big-num`（count 动画）+ 右侧说明 |
| 引用 | `.quote` |
| 步骤流程 | `.steps` > `.step`（`.n` 序号角标） |
| 卡片组 | `.card`（`.coral/.mint/.sky` 变体），grid 2-3 列 |
| 结尾 | 居中大字 + 一句行动号召 |

设计规范：一屏一个重点；标题 ≤ 12 字/行；正文 ≥ 30px；强调用 `.hl/.hl-coral/.hl-mint`；等宽内容（命令、数字、代码）用 `.mono`。颜色只用 `:root` 里的变量。

## 7. 初始化块

字幕数据二选一（推荐 A，免手工粘贴不出错）：

A. 引用 tts.py 产出的 `build/subtitles.js`（内容即 `window.SUBTITLES = [...sentences]`）：

```html
<script src="build/subtitles.js"></script>
<script src="engine.js"></script>
<script>
HF.init({ audio: "build/voice.mp3", durationMs: 0, subtitle: true, karaoke: true });
</script>
```

B. 手工粘贴：`const SUBTITLES = /* timeline.json 的 sentences 原样粘贴 */;` 后再 init。

`SUBTITLES` 必须与口播稿逐字一致（它就是打在画面底部的字幕）。句子很长时字幕条会自动换行，无需处理。

## 8. 自检清单（渲染前过一遍）

- [ ] 每个 `data-start` 来自 timeline.json 且单调递增；场景数 = 句子数（或按规则合并）
- [ ] 所有 `data-anim` 元素在场景 `display:none` 时不会闪现（引擎已处理，勿手动加 CSS animation）
- [ ] 没有引入网络资源（字体走本机、图片用本地文件或纯 CSS）
- [ ] `SUBTITLES` 与口播稿一致；`hold_end` 用作 `data-end`
- [ ] 浏览器打开能播：点空格播放，字幕逐句变、词高亮跟上语速、场景切换发生在换句处
