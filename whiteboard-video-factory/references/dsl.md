# 场景 DSL 速查（`lib/scene-dsl.js`）

```js
const { Scene, C, CX, build } = require('<仓库路径>/lib/scene-dsl')   // wb new 会自动填好.use(__dirname);
const scenes = [];
{
  const s = new Scene('01-intro', `第一段旁白。| 第二段旁白。| 第三段。`);  // `|` 分 beat
  s.nextBeat();          // 之后添加的元素属于第 1 段
  s.text(CX, 60, '标题', { size: 90, align: 'center' });
  s.nextBeat();
  // ...
  scenes.push(s);
}
build(__dirname, scenes);   // 写 scenes/*.excalidraw.md + script.json + 旁白稿.md
```

- beat 数必须等于旁白段数，否则 `save()` 抛错。
- 元素按添加顺序逐笔画。每个元素有自然时长：文字按字数（每个汉字 0.06~0.2s，随字号；拉丁字母减半）、线框按描边长度（1000 px/s）+ 填充（≤1.2s）、贴纸按宽度（≥0.8s）；单元素 ≥0.35s，两笔之间抬笔 0.12s，笔尖在间隙里从上一笔末端移到下一笔起点。一个 beat 画不完最多溢出到下一段前 35%，仍不够才整体压缩——所以别往一段里塞太多元素。参数在 config.json `render.pen`。

## 基本元素

| 调用 | 说明 |
|---|---|
| `s.text(x, y, str, {size, color, align:'left'|'center'|'right', font})` | 多行用 `\n`；align center 时 x 是中心 |
| `s.rect(x, y, w, h, {round, fill, fillStyle:'hachure'|'solid', stroke, strokeWidth, strokeStyle:'dashed', roughness})` | |
| `s.ellipse(x, y, w, h, opts)` | x,y 是外接框左上 |
| `s.diamond(x, y, w, h, opts)` | |
| `s.line([[x,y],...], {round, stroke, strokeWidth, strokeStyle, fill})` | 带 fill 变闭合多边形；round 走曲线 |
| `s.arrow([[x,y],[x2,y2]], {stroke, strokeWidth, startHead:'arrow'})` | 末端箭头；startHead 双向 |
| `s.image(x, y, 'name', {w|h, align:'center'})` | 贴纸 `assets/<name>.png`；给 w 或 h 之一按比例算另一个 |

## 封面

```js
const cover = (s, ratio) => s.coverLayout({
  ratio,                                  // build 会按 config.json cover.ratios 各调一次：'4:3'(1440×1080) / '3:4'(1080×1440)，也认 '16:9' '1:1'
  title: '杜兰特随手一投\n赚得比打球多',   // ≤2 行、每行 ≤8 字；字号按最长行自动定（4:3 ≤162，3:4 ≤170）
  sub: '25 万 → 6000 万，Hugging Face 这笔账',   // 可省
  sticker: 'basketball-player',           // 4:3 在右下、尽量大且只避开会撞到的标题行；3:4 在标题下方居中
  accent: 1,                              // 高亮第几行（0 起，默认最后一行）；color 高亮字色默认 C.brand，highlight 马克笔色默认 C.fYellow
  tag: '白板 3 分钟讲清楚',                // 左上/顶部标签，默认 config cover.seriesTag，'' 不要
});
build(__dirname, scenes, { cover });      // 写 scenes/00-cover-4x3.excalidraw.md 等 + cover.json；wb cover 渲染成 <期>/封面-4x3.png
```
4:3 是标题通栏 + 贴纸右下；3:4 是标题居中 + 贴纸下方（宽图如 `logos-vs` 自动按宽度缩、在空位里垂直居中）；16:9 才是左右分栏。公司题材 `sticker` 传 `logos-vs` 或 `logo-x`（`wb logo` 产物）。封面自带手绘粗边框（config `cover.frame`）、马克笔高亮、左下/底部品牌标。想加元素就在 cover 函数里 `if (ratio === '3:4') ... else ...` 继续 `s.text / s.image`。
单独可用：`s.highlight(x, y, w, h, {color, opacity})` 马克笔色块（先 push 再写字就垫在字下）、`s.brandMark(x, y, size)` 星号+手写名+绿线。

## 复合图形

`s.robot(x, y, scale, {headOnly, fill, color})` · `s.laptop(x, y, scale, {screen})` · `s.cloud(cx, cy, w, {fill})` · `s.person(x, y, scale)` · `s.checkbox(x, y, label, {size, fill})` · `s.moon(cx, cy, r)` · `s.squiggle(x1, x2, y, {color})`

需要新图形：优先出贴纸；确要画，写成期内的辅助函数（如薄肌期的 dumbbell/clock/wave），稳定后再搬进 scene-dsl.js。

## 颜色

线色 `C.ink/gray/red/green/blue/orange/purple`；填充 `C.fRed/fGreen/fBlue/fYellow/fPurple/fGray`；`fillStyle:'solid'` 实心、默认 `hachure` 斜线。
`C.brand` = config.json `brand.accent`（默认绿 #2f9e44）：大标题、圈注、结论箭头优先用它，蓝/紫/橙做对比色。

## 品牌层（config.json `brand`，不用每期写）

- **水印**：右上角 `brand.name` 手写字 + 品牌绿下划线 + 小星号（呼应头像），透明度 0.72；第一场景开头 1.2s 逐笔画入，之后每帧静态。位置 `watermark.position`（top-right / top-left / bottom-right / bottom-left），右上角 320×130 区域场景别放元素。
- **片尾品牌卡**：`wb build` / 整片 `wb render` 自动追加 `99-brand`（5.5s，静音，BGM 继续并淡出）：名字或 `brand.logo`（透明底 png）+ 划线 + `brand.slogan` + 黄色 CTA 胶囊 `endCard.cta`。`wb stills` 会出 `99-brand-beat1.png` 预览；单场景 `wb render <期> 03-xxx` 不带片尾。
- **铅笔**：`brand.pen.color` 笔身颜色。
- 片尾卡的样式在 `scene-dsl.js` `brandEndCard()`，想加二维码/头像就给 `brand.logo` 或改那个函数。

## 尺寸经验

- 标题 90（顶部 y=60）；大字 140~150；正文 40~44；注释 32~36（灰）；卡片标题 48~56。
- 1920 宽下，44 号中文一行别超 30 字；左对齐文本估算宽 = 汉字数×size + 英文×0.55×size。
- 贴纸人形 h 360~380；三栏卡片 540×720，间距 60，顶 230。
- 字幕安全线 y=960；分割虚线到 940 为止。

## 目录约定（config.json `dirs`）

期目录 `<dirs.projects>/<日期 标题>/`（默认 `episodes/`）：`scenes.js`（手写）· `README.md`（手写：来源）· `发布.md`（手写：文案）· `scenes/` · `assets/` · `旁白稿.md` · `字幕.srt` · `封面-4x3.png` · `封面-3x4.png`
后台 `<dirs.build>/<日期 标题>/`（默认 `build/`）：`outputs/final.mp4`（成片）· `work/audio/`（wav + json 含 wordList）· `work/frames/`（`wb stills` 静帧，build 后自动清）· `work/out/`（分段与 master.mp4）· `work/raw/`（生图原稿、Logo 原 SVG）
