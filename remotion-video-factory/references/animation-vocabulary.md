# animation-vocabulary — 动画模式词汇表

8 种经过实战验证的模式。**一种手法全片只当一次主角**；同屏只讲一个动效；
关键信息落定后必须呼吸（hold ≥45f，重要字标 ≥30f）。

所有示例假设组件签名 `({D}: SceneProps)`，`useCurrentFrame()` 是场景内相对帧。

---

## 1. counter · 数字滚动

计数器从初值滚到目标，配缩放落定。开场钩子最常用。

```tsx
const count = Math.round(interpolate(frame, [0, 65], [0, 1000000], clamp));
const scale = interpolate(frame, [0, 55], [0.72, 1], {...clamp, easing: ease});
<div style={{fontFamily: MONO, fontSize: 190, transform: `scale(${scale})`}}>
  {count >= 999999 ? "1,000,000" : count.toLocaleString()}
</div>
```

要点：末段切换为格式化字符串避免中间态逗号闪烁；落定后 hold 到 fade。

## 2. stagger-grid · 交错网格（矩阵/热力图）

N×N 格子按 `(行+列)` 波前逐个点亮——注意力矩阵、表格、二维码类画面。

```tsx
const delay = 35 + (row + col) * 2;           // 对角波前
const p = interpolate(frame, [delay, delay + 20], [0, 1], clamp);
<div style={{
  borderRadius: 5,
  background: `rgba(139,124,255,${0.14 + p * 0.62})`,  // 透明度随进度加深
  transform: `scale(${0.4 + p * 0.6})`,
}} />
```

参数：`delay 步长` 控制波前斜率（大=平缓）；16×16 以上格子用 opacity 即可，别加 boxShadow（渲染慢且显脏）。

## 3. filter-transition · 稠密→稀疏过滤

先全量，再按"保留谓词"淡出无关项——Sparse Attention、特征筛选类画面。

```tsx
const t = interpolate(frame, [80, 160], [0, 1], {...clamp, easing: ease});
const keep = Math.abs(row - col) <= 1 || col === 0 || row === n - 1; // 保留谓词：按内容定
const alpha = keep ? 0.86 : 0.58 * (1 - t) + 0.03;                   // 无关项退到近黑
```

要点：保留项给一次高亮脉冲（`boxShadow` 在 t>0.6 后出现）；过滤瞬间配 whoosh+impact（见 sound-design）。

## 4. svg-lines · 连线拓扑生长

多对一汇聚、依赖图、请求流。SVG `<line>` 按帧改变 opacity/strokeDashoffset。

```tsx
<svg width={1920} height={1080} style={{position: "absolute", inset: 0}}>
  {nodes.map((_, i) => {
    const p = interpolate(frame, [40 + i * 8, 90 + i * 8], [0, 1], clamp);
    return <line key={i} x1={...} y1={...} x2={...} y2={...}
      stroke={color(i)} strokeWidth={4} opacity={p * 0.65} strokeDasharray="8 10" />;
  })}
</svg>
```

要点：连线画在内容层**之下**；末端节点在连线到齐后再入场；虚线 dasharray 给"数据流"感。

## 5. incremental-activation · 逐项激活（缓存/流水线）

序列中当前项高亮、历史项固定为完成态——KV Cache、逐步推理、队列消费。

```tsx
const active = Math.min(tokens.length - 1,
  Math.floor(interpolate(frame, [40, 420], [0, tokens.length - 1], clamp)));
// i < active: 完成态（暗青）; i === active: 高亮（warm + glow）; i > active: 未开始
```

要点：激活节奏与旁白语义对齐（说到第几个就亮到第几个，误差容忍一拍）；
历史区同步增长（缓存块逐个出现）讲"累积"效果最佳。

## 6. spring-cards · 弹簧卡片组

要点/总结/对比三卡片，spring 物理入场 + 交错。

```tsx
const p = spring({frame: frame - i * 18, fps: FPS,   // FPS 从 ../timeline 导入，勿写死 30
  config: {damping: 18, stiffness: 110, mass: 0.8}});
style={{transform: `translateY(${(1 - p) * 60}px)`, opacity: p}}
```

要点：交错 18f/张；3 张为宜；落地后不再动，靠 SFX 标记落点。

## 7. progress-fill · 进度/占比条

```tsx
<div style={{width: `${interpolate(frame, [45, 300], [8, 94], clamp)}%`,
  background: `linear-gradient(90deg,${C.cyan},${C.violet})`}} />
```

要点：填充时长 4–8s；数值标签跟随进度插值（counter 模式复用）。

## 8. typographic-hold · 大字定格

结论句/字标：入场（上移+缩放）→ **hold ≥30f** → fade。

```tsx
const scale = interpolate(frame, [0, 40], [0.9, 1], {...clamp, easing: ease});
```

要点：一屏一句；结论前留 10f 静默；结尾字标落定配 impact+sparkle（sound-design 结尾句式）。

---

## 组合律

- 开场：counter 或 typographic-hold（单一主角，动作 ≥3s）
- 讲解段：stagger-grid / filter-transition / svg-lines / incremental-activation 轮换，不连用两个同类
- 收尾：spring-cards（要点）→ typographic-hold（字标）
- 每场景 fade 出点用 `fade(frame, D)`，动画完成帧 < D - 60（留呼吸）
