# SVG 符号库 (视频管线)

> 教学示意图的可复用零件。全部按 `diagram-zone` 的约定写: viewBox `0 0 900 700`
> (对比双栏用 `0 0 940 700`), 颜色一律用配色变量, 线宽 ≥4。
> 直接拷进 `<svg>` 里再挪坐标; 元素记得给 id 供 GSAP 入场。
> 来源: examples/sound-video (声学/波形已渲染验证); 电学/图线零件出自欧姆定律测试片, 同样渲染验证过。

## 通用约定

- 主体图形 `stroke="var(--primary)"`, 对比/弱化项 `var(--neutral)` 或 `var(--accent)`
- 电流/能量/高亮一律 `var(--accent)`
- callout: SVG 里画 `<circle r="8">` + `<line stroke-width="4">`, 文字用 HTML `.callout-label` 绝对定位
- 描边入场用 `drawIn()`; **虚线元素不能 drawIn** (会变实线), 用 opacity 淡入

## 电学 (已验证)

```html
<!-- 电池 (国标: 长线=正极, 短线=负极), 嵌在导线缺口处 -->
<line x1="420" y1="452" x2="420" y2="508" stroke="var(--primary)" stroke-width="7"/>
<line x1="480" y1="466" x2="480" y2="494" stroke="var(--primary)" stroke-width="7"/>

<!-- 电阻 (国标矩形, 嵌在导线上, fill 白色盖住底下的线) -->
<rect x="340" y="180" width="120" height="40" fill="#fff"
      stroke="var(--primary)" stroke-width="7"/>

<!-- 电流表 / 电压表 (圆圈 + 字母; 电压表配黄色并联支路) -->
<circle cx="280" cy="220" r="42" fill="#fff" stroke="var(--primary)" stroke-width="6"/>
<text x="262" y="238" font-size="46" font-weight="800" fill="var(--primary)">A</text>

<!-- 灯泡 (圆 + 交叉线 + 可选光芒) -->
<circle cx="300" cy="105" r="27" fill="color-mix(in srgb, var(--highlight) 55%, transparent)"
        stroke="var(--primary)" stroke-width="6"/>
<path d="M 281 86 L 319 124 M 319 86 L 281 124" stroke="var(--primary)" stroke-width="5"/>

<!-- 开关 (断开状态: 支点 + 斜杆) -->
<circle cx="500" cy="480" r="7" fill="var(--primary)"/>
<line x1="500" y1="480" x2="560" y2="440" stroke="var(--primary)" stroke-width="7" stroke-linecap="round"/>
<circle cx="580" cy="480" r="7" fill="var(--primary)"/>

<!-- 电流方向箭头 (黄色三角, 贴在导线上; 循环点亮 = 电流在流) -->
<polygon class="amp" points="230,190 256,200 230,210" fill="var(--accent)"/>
<!-- GSAP: fromTo(amp, {opacity:0}, {opacity:1, yoyo:true, repeat:2n-1}) 逐个错开 0.35s -->

<!-- 矩形回路骨架 (电池缺口在底边, 元件缺口在顶边) -->
<path d="M 150 480 V 200 H 340 M 460 200 H 730 V 480 H 480 M 420 480 H 150"
      stroke="var(--primary)" stroke-width="7" fill="none" stroke-linecap="round"/>
```

## 坐标图线 (已验证)

```html
<!-- 坐标轴 + 箭头 + 原点 O -->
<line x1="140" y1="580" x2="820" y2="580" stroke="var(--ink)" stroke-width="5"/>
<line x1="140" y1="580" x2="140" y2="120" stroke="var(--ink)" stroke-width="5"/>
<polygon points="820,580 798,571 798,589" fill="var(--ink)"/>
<polygon points="140,120 131,142 149,142" fill="var(--ink)"/>
<text x="835" y="592" class="wave-label" fill="var(--ink)">U</text>
<text x="120" y="100" class="wave-label" fill="var(--ink)">I</text>
<text x="118" y="612" class="wave-label" fill="var(--neutral)">O</text>

<!-- 正比直线 (过原点) + 虚线参考点 (虚线组淡入, 不 drawIn) -->
<line x1="140" y1="580" x2="760" y2="190" stroke="var(--primary)" stroke-width="7"/>
<g stroke="var(--accent)" stroke-width="4" stroke-dasharray="10 10" fill="none">
  <path d="M 420 580 V 404 H 140"/>
</g>
<circle cx="420" cy="404" r="11" fill="var(--accent)"/>

<!-- 反比曲线 (双曲线一支, 用平滑贝塞尔近似) -->
<path d="M 200 180 C 260 400, 400 480, 780 520"
      stroke="var(--primary)" stroke-width="7" fill="none"/>
```

## 波形 (已验证, 引擎生成)

```html
<!-- 正弦波: 引擎按 data-wave 生成 polyline, 不手写点
     flow:true = 相位流动 (svg 要 overflow:hidden + data-layout-allow-overflow)
     harmonics = 叠加谐波 (音色/复杂波) -->
<polyline data-layout-allow-overflow
  data-wave='{"x0":70,"y0":230,"len":790,"amp":62,"cycles":4,"flow":true}'
  fill="none" stroke="var(--primary)" stroke-width="6" stroke-linecap="round"/>
<!-- 场景函数里: drawIn(sel, t+0.5, 1.0); flowWave(sel, t+1.7, sceneEnd); -->

<!-- 振幅双向箭头 -->
<g stroke="var(--ink)" stroke-width="5" fill="var(--ink)" stroke-linecap="round">
  <line x1="895" y1="455" x2="895" y2="635"/>
  <polygon points="895,450 886,468 904,468"/>
  <polygon points="895,640 886,622 904,622"/>
</g>
```

## 声学 (已验证)

```html
<!-- 音叉 (U 形双臂 + 底桥 + 手柄 + 底座) -->
<g stroke="var(--ink)" stroke-width="12" fill="none" stroke-linecap="round">
  <line x1="260" y1="120" x2="260" y2="360"/>
  <line x1="340" y1="120" x2="340" y2="360"/>
  <path d="M 260 360 A 40 40 0 0 0 340 360"/>
  <line x1="300" y1="398" x2="300" y2="520"/>
</g>
<rect x="240" y="520" width="120" height="28" rx="8" fill="var(--line)" opacity="0.65"/>

<!-- 声波弧 (多层半圆, 透明度递减; opacity 属性写在元素上, drawIn 画入) -->
<path d="M 480 190 A 62 62 0 0 1 480 314" stroke="var(--accent)" stroke-width="6"
      fill="none" opacity="0.9" stroke-linecap="round"/>

<!-- 鼓 + 同心圆声波 (圆 opacity 初始 0, 发射循环: scale 0.3→1.12 + opacity→0, repeat) -->
<circle class="ring" cx="330" cy="330" r="110" stroke="var(--accent)" stroke-width="6"
        fill="none" opacity="0"/>
<g><rect x="240" y="330" width="180" height="115" rx="14" fill="#C0392B" opacity="0.85"/>
   <ellipse cx="330" cy="330" rx="90" ry="26" fill="var(--soft)" stroke="var(--ink)" stroke-width="5"/></g>
```

## 力学 (新增, 用前先 lint + 目检)

```html
<!-- 杠杆: 支点三角 + 横梁 + 重物 + 力箭头 -->
<polygon points="450,430 410,500 490,500" fill="color-mix(in srgb, var(--primary) 25%, #fff)"
         stroke="var(--primary)" stroke-width="5"/>
<line x1="150" y1="440" x2="750" y2="415" stroke="var(--ink)" stroke-width="9" stroke-linecap="round"/>
<rect x="170" y="360" width="70" height="70" fill="color-mix(in srgb, var(--accent) 70%, #fff)"
      stroke="var(--ink)" stroke-width="5"/>
<g stroke="var(--accent)" stroke-width="7" fill="var(--accent)" stroke-linecap="round">
  <line x1="700" y1="410" x2="700" y2="300"/>
  <polygon points="700,290 686,316 714,316"/>
</g>

<!-- 物块 + 支持面 + 摩擦/拉力箭头 -->
<line x1="100" y1="500" x2="800" y2="500" stroke="var(--ink)" stroke-width="6"/>
<rect x="330" y="400" width="140" height="100" fill="#fff" stroke="var(--primary)" stroke-width="6"/>
<g stroke="var(--accent)" stroke-width="7" fill="var(--accent)" stroke-linecap="round">
  <line x1="470" y1="450" x2="590" y2="450"/>
  <polygon points="600,450 574,436 574,464"/>
</g>

<!-- 定滑轮 -->
<line x1="450" y1="120" x2="450" y2="170" stroke="var(--ink)" stroke-width="6"/>
<circle cx="450" cy="220" r="52" fill="#fff" stroke="var(--primary)" stroke-width="7"/>
<circle cx="450" cy="220" r="8" fill="var(--primary)"/>
```

## 光学 (新增, 用前先 lint + 目检)

```html
<!-- 三棱镜 + 入射光 + 色散 (彩虹色保持真实色, 不用配色变量) -->
<polygon points="450,180 330,430 570,430" fill="color-mix(in srgb, var(--primary) 8%, #fff)"
         stroke="var(--primary)" stroke-width="6"/>
<line x1="150" y1="330" x2="395" y2="320" stroke="var(--ink)" stroke-width="5"/>
<g stroke-width="5">
  <line x1="510" y1="320" x2="790" y2="260" stroke="#E63946"/>
  <line x1="510" y1="325" x2="790" y2="310" stroke="#F4A300"/>
  <line x1="510" y1="330" x2="790" y2="360" stroke="#06A77D"/>
  <line x1="510" y1="335" x2="790" y2="410" stroke="#118AB2"/>
</g>

<!-- 平面镜反射: 镜面 + 法线(虚线,淡入) + 入射/反射光 -->
<line x1="250" y1="500" x2="650" y2="500" stroke="var(--ink)" stroke-width="8"/>
<line x1="450" y1="500" x2="450" y2="180" stroke="var(--neutral)" stroke-width="4"
      stroke-dasharray="12 10"/>
<g stroke="var(--primary)" stroke-width="6" fill="var(--primary)" stroke-linecap="round">
  <line x1="220" y1="240" x2="450" y2="500"/>
  <line x1="450" y1="500" x2="680" y2="240"/>
  <polygon points="668,226 690,232 676,252"/>
</g>

<!-- 凸透镜 (双弧) + 主光轴 -->
<path d="M 450 180 C 490 300, 490 400, 450 520 C 410 400, 410 300, 450 180 Z"
      fill="color-mix(in srgb, var(--primary) 10%, #fff)" stroke="var(--primary)" stroke-width="6"/>
<line x1="120" y1="350" x2="780" y2="350" stroke="var(--neutral)" stroke-width="4"
      stroke-dasharray="14 12"/>
```

## 生物/化学 · 流程链 (通用)

```html
<!-- 节点徽章 + 箭头链 (光合作用/水循环类; HTML 版可直接用 .badge) -->
<circle cx="180" cy="330" r="58" fill="color-mix(in srgb, var(--primary) 10%, #fff)"
        stroke="var(--primary)" stroke-width="5"/>
<text x="152" y="345" font-size="40" fill="var(--primary)">☀</text>
<text x="145" y="430" class="wave-label" fill="var(--ink)">阳光</text>
<g stroke="var(--accent)" stroke-width="6" fill="var(--accent)" stroke-linecap="round">
  <line x1="250" y1="330" x2="330" y2="330"/>
  <polygon points="342,330 318,318 318,342"/>
</g>
```
