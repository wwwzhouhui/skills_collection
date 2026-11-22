# 场景 DSL API（图解动画版）

`scenes.js` 的写法：`require` 本 DSL → `new Scene(name, '旁白|按|竖线|分拍')` → `s.nextBeat()` 后逐个加元素 → `build(__dirname, scenes, { cover })`。元素归属当前 beat，渲染时该拍旁白一响，这组元素错峰"生长"入场（淡入 + 从 94% 放大 + 上移 14px；线条/箭头用擦出）。元素一直留在画布上，到场景结束。

## 调色板 C（语义色纪律）

```js
C.ink     '#2B2B2B'   墨字        C.gray  '#8A8A85'  次要文字
C.faint   '#C2C2BB'   弱描边      C.white '#FFFFFF'  卡片底
C.orange  '#E8833A'   强调/主线   C.fOrange '#F7E0C8'
C.red     '#D64541'   负面语义    C.fRed  '#F3D4D1'
C.green   '#5B8C5A'   正面语义    C.fGreen '#DFE9DE'
C.blue    '#4A7DB5'   中性知识    C.fBlue '#DCE6F0'
C.yellow  '#E0A93E'   警示/数字   C.fYellow '#F6EBCB'
C.paper   '#E9E9E4'   全片背景    C.brand = config brand.accent（默认橙）
C.grayFill '#F0F0EC'  AI 聊天气泡底
```
纪律：**橙=强调、红=负面、绿=正面、蓝=中性**，一期一义，全片不换。浅底色 `f*` 用于卡片填充，饱和色用于描边/文字。

## 基础元素

```js
s.rect(x, y, w, h, { fill, stroke, strokeWidth, radius, opacity, strokeStyle: 'solid'|'dashed'|'dotted' })
s.ellipse(x, y, w, h, { ... })          // x,y 是外接框左上角
s.diamond(x, y, w, h, { ... })
s.text(x, y, '文字', { size: 36, color, align: 'left'|'center'|'right', italic, weight })  // weight 默认 700
s.line([[x,y],[x,y],...], { stroke, strokeWidth, round, strokeStyle })
s.arrow([[x,y],[x,y]], { ... })          // 带实心三角箭头
s.image(x, y, '贴纸名', { w | h, align: 'center' })   // assets/<名>.png；dg image 产物
s.imageFile(x, y, '路径.png', { w | h, align: 'center' })  // 品牌 logo 等
s.imageSize('贴纸名')                    // 排版前算宽高比：{ w, h }
```
所有元素的入厂动画默认按类型选：形状/文字/贴纸 `rise`（淡入+缩放+上移），线条/箭头 `wipe`（沿笔画擦出）。单个元素可覆盖：`{ anim: 'fade' | 'rise' | 'pop' | 'wipe' }`。

## 复合原语（本风格的招牌，全部由基础元素拼成，Obsidian 里可拆开微调）

```js
s.card(x, y, w, h, { fill: C.white, stroke: C.faint, radius: 24, sw: 2 })   // 白圆角卡片，基本容器
s.frameBox(x, y, w, h, { color: C.orange, sw: 5 })   // 强调框：框在元素外 8px，"讲到哪、亮到哪"
s.highlight(x, y, w, h, { color: C.fOrange })        // 平头马克笔：无描边浅橙圆角垫底，push 在文字前面
s.heading('标题', { x: 110, y: 64, size: 68, color: C.brand })  // 章节大标题
s.chip(x, y, w, h, '标签', { fill, stroke, color, size, radius })   // 圆角徽章：「有害组」「假设」「第1层」
```

### 聊天 UI（引子/实例演示）
```js
const p = s.chatPanel(x, y, w, h, { title: 'AI助手' })   // 白卡片 + AI 徽章 + 顶栏 + 分隔线；返回内容区 {x,y,w,h}
s.bubble(p.x, p.y, w, '文字', { role: 'ai' | 'user' | 'refuse', size })  // 气泡：ai=浅灰墨字 / user=深绿白字 / refuse=红底白字
                                                          // 高度自动；返回 {x,y,w,h}
```

### 招牌架构图（残差流）
```js
const r = s.flowChain(x, y, {
  steps: ['Embedding', '注意力', 'MLP', '注意力', 'MLP'],  // 或 [{label, icon}]
  boxW: 118, boxH: 104, gap: 62,            // 图标自动配：Embedding=cube 注意力=gear MLP=grid
  token: true, out: true, residual: true,   // 输入 token 盒 / 输出盒 / 橙色残差流 + ⊕ 相加
  ellipsis: true,                           // 中段「···」省略号
})
r.boxes   // [{x,y,w,h,label}] —— 之后对某一层 s.frameBox(b.x, b.y, b.w, b.h) 高亮
```
单盒子也可单独用：`s.flowBox(x, y, w, h, '标签', { icon: 'cube'|'gear'|'grid'|'dot'|'blank' })`（标签在盒上方，斜体）。

### 数据集卡片堆（有害组 x128 / 无害组 x128）
```js
s.stack(x, y, w, h, n, { stroke: C.red, label: '有害组', labelColor: C.red })
// n 张卡片向右下偏移(7,7)堆叠；label 在堆下方
```

### 数字列（模型内部向量可视化）
```js
s.numColumn(x, y, [0.12, -1.37, 0.83, 2.04, -0.46, 0.33], { cellW: 108, cellH: 46, label: '4096 个数字', labelSize: 44 })
// 负数=红底红字，其余=白底墨字；右侧自动画大括号 + 说明
```

### 向量与公式（核心直觉页）
```js
s.vec(x1, y1, x2, y2, { color: C.red, width: 9, label: '拒绝', labelSize: 34 })   // 粗箭头 + 末端标签
s.formula(x, y, "W' = W − r̃ r̃ᵀ", { size: 48, align: 'center' })                  // 斜体公式
```

### 参考文献收尾（这个体裁的信任来源，结尾场景必放）
```js
s.heading('参考文献', { align 位置自定 })   // 或 s.text(CX, 64, '参考文献', { size: 64, align: 'center' })
const h = s.refList(x, y, [
  { title: 'Refusal in Language Models Is Mediated by a Single Direction', sub: 'Arditi et al. · NeurIPS 2024 · arXiv:2406.11717' },
  { title: 'abliterator', sub: 'FailSpy · github.com/FailSpy/abliterator' },
], { titleSize: 40, subSize: 30, gap: 26 })
// 橙色 [n] 序号 + 墨色粗体标题 + 灰色斜体出处；返回总高度
```

## 封面

```js
const cover = (s, ratio) => s.coverLayout({
  ratio,                                    // '4:3' | '3:4' | '9:16'（config cover.ratios 逐个调用）
  title: '两行标题\n第二行是钩子',           // 行分隔；accent 指定高亮行（默认最后一行）
  sub: '关键词 · 关键词 · 关键词',
  sticker: 'mascot',                        // 可选；16:9 放右列，4:3 放右下，竖版放标题下
  tag: '图解讲清楚',                         // 左上角系列标签（config cover.seriesTag 默认）
});
build(__dirname, scenes, { cover });
```
版式：米白底、无外框，大号粗体标题（高亮行 = 橙字 + 浅橙马克笔垫底 + 橙色粗下划线），品牌标在左下/底中。9:16 版式把标题与贴纸压在中央安全区（抖音封面上下会被裁）。

## 排版红线

- 画布 1920×1080；**y ≥ 960 字幕区、右上 (1600,0)~(1920,130) 水印区**，元素别进去（`dg scenes` 会打 ⚠，必须清零）。
- 一屏 10~20 个元素；一个 beat 塞不下就删元素或拆拍。
- 文本宽度是估算值，`align: 'center'` 才准；左对齐长文本别超 1920。
- 每拍 3~4 句、80~120 字；15+ 元素的拍会顶满溢出（stagger 被压缩），删元素比调参划算。
