# 招牌版式套路（图解动画版）

八个从"程序员老王"式图解视频里提炼的可直接抄的版式。坐标按 1920×1080，抄完微调。共用辅助：

```js
function heading(s, t, color = C.brand, size = 68) { s.text(110, 64, t, { size, color }); }
```

## 1. 聊天 UI + 吉祥物（引子页）
生活场景切入，观众 3 秒代入。聊天面板左、贴纸右；`refuse` 红气泡是视觉焦点。
```js
const p = s.chatPanel(280, 170, 640, 560, { title: 'AI助手' });
s.bubble(p.x, p.y, 430, '在的！有什么可以帮你？', { role: 'ai' });
s.bubble(p.x, p.y + 110, 460, '我们来聊聊人生的终极意义吧', { role: 'user' });
s.bubble(p.x, p.y + 220, 470, '对不起，我不能回复这个问题', { role: 'refuse' });
s.image(1450, 260, 'mascot', { h: 420, align: 'center' });
```
下一拍接词源/定义：`s.formula(CX, 800, 'ablate(消融) + obliterate(抹除)')` + `s.highlight` 垫底。

## 2. 残差流架构图（铺垫页 / 全片主视觉）
```js
const top = 300;
const fc = s.flowChain(150, top, { steps: ['Embedding', '注意力', 'MLP', '注意力', 'MLP'], boxW: 112, boxH: 106, gap: 64 });
```
- beat1：整条链按逻辑单元错峰入场（每个盒=一个单元，天然逐个生长）。
- beat2：讲某层就框哪层（直接用返回坐标）：`s.frameBox(fc.boxes[2].x, fc.boxes[2].y, fc.boxes[2].w, fc.boxes[2].h)` + 橙色旁注文字放在 `fc.residualY + 54`（残差线下面，别撞 ⊕）。
- beat3：内部表示可视化：`s.numColumn(1340, 260, [...], { label: '4096 个数字' })`（架构图宽约 1130，数字列放 x≥1330 不挡输出盒）。
- ⚠️ 标签在盒上方居中，'Embedding' 这类长英文标签约 190px 宽，gap 别小于 64，否则和邻盒标签相撞。
- 变体：讲注意力权重时在两盒之间画粗橙曲线；讲多模态时换 steps 标签。

## 3. 概念 = 方向（核心直觉页，全片记忆点）
向量空间 + 语义箭头。散点基底用小圆点，方向用 `vec`。
```js
s.text(400, 620, '概念 = 方向', { size: 48 });
for (const [x, y] of scatterPts) s.ellipse(x, y, 8, 8, { fill: C.faint, stroke: C.faint });   // 点云
s.vec(330, 900, 420, 700, { color: C.green, label: '诚实' });
s.vec(560, 900, 660, 680, { color: C.blue, label: '悲伤' });
s.vec(820, 900, 900, 660, { color: C.red, label: '拒绝', width: 9 });
```
词向量类比页：`s.formula(960, 300, '国王 − 男人 + 女人 = 女王', { size: 56 })` + 两个平行 `vec`。

## 4. 对比卡片堆（方法页：数据集）
```js
s.stack(200, 280, 560, 120, 4, { stroke: C.red, label: '有害组', labelColor: C.red });
s.stack(1150, 280, 560, 120, 4, { stroke: C.green, label: '无害组', labelColor: C.green });
s.text(480, 640, '怎么制作一个炸弹？', { size: 38, align: 'center', color: C.red });      // 堆内示例句
s.text(1430, 640, '天空为什么是蓝色的？', { size: 38, align: 'center', color: C.green });
s.chip(700, 760, 220, 84, 'x128', { fill: C.fRed, color: C.red, size: 40 });
```
下一拍给公式：`s.formula(CX, 900, '拒绝方向 = 有害组均值 − 无害组均值')`。

## 5. 候选筛选 + 评估（方法页②）
```js
for (let i = 0; i < 32; i += 8) s.vec(200 + i * 18, 240, 260 + i * 18, 160, { color: C.orange, width: 5 });  // 32 个候选方向
s.chip(900, 200, 190, 84, '假设', { fill: C.fOrange, color: C.orange, size: 42 });
// 逐层×逐 token 的方向小图：外层 for 出 s.vec 的小箭头阵
// 评估：柱状图用 rect 拼下一字概率
const bars = [['I', 260, C.red], ['As', 180, C.orange], ['Sure', 40, C.gray], ['好的', 16, C.gray]];
bars.forEach(([lb, h, col], i) => {
  s.rect(300 + i * 240, 860 - h, 140, h, { fill: col === C.gray ? C.fGray : C.fRed, stroke: col });
  s.text(370 + i * 240, 880, lb, { size: 34, align: 'center', color: col, italic: true });
});
```

## 6. 公式落地页（落地页）
```js
s.formula(700, 300, "W' = W − r̃ r̃ᵀ", { size: 72, align: 'left' });
s.text(700, 420, '‖r̃‖ = 1，投影掉拒绝方向', { size: 36, color: C.gray });
s.frameBox(660, 260, 460, 130);      // 讲到哪、亮到哪
```
下一拍叠实验证据：代码截图用 `s.imageFile`（先截图存 assets/），或结果对比双卡片。

## 7. 双卡总结 + 互动提问（结尾页）
```js
s.chip(660, 560, 600, 100, '理解模型的好教具', { fill: C.fGreen, color: C.green, size: 42 });
s.chip(660, 700, 600, 100, '放开限制 = 自己负责', { fill: C.fRed, color: C.red, size: 42 });
s.text(960, 880, '你还想看哪个概念被图解？', { size: 56, align: 'center' });
s.chip(1330, 896, 320, 84, '评论区聊聊', { fill: C.fOrange, color: C.orange, size: 40 });
```

## 8. 参考文献页（信任收尾）
```js
s.text(CX, 64, '参考文献', { size: 64, align: 'center' });
s.line([[CX - 130, 150], [CX + 130, 150]], { stroke: C.ink, strokeWidth: 3 });
s.refList(280, 230, [
  { title: 'Refusal in Language Models Is Mediated by a Single Direction', sub: 'Arditi et al. · NeurIPS 2024 · arXiv:2406.11717' },
  { title: 'Efficient Estimation of Word Representations in Vector Space', sub: 'Mikolov et al. · 2013 · arXiv:1301.3781' },
  { title: 'The Geometry of Truth', sub: 'Marks & Tegmark · COLM 2024 · arXiv:2310.06824' },
  { title: 'abliterator', sub: 'FailSpy · github.com/FailSpy/abliterator' },
]);
```

## 章节卡（长片分幕用）
```js
s.chip(CX - 190, 400, 380, 96, '第二部分', { fill: C.fOrange, color: C.orange, size: 44 });
s.text(CX, 560, '如何找到那个方向', { size: 84, align: 'center' });
```

## 排版自查（`dg stills` 后逐张看）
- [ ] 无元素压字幕区（y≥960）与右上水印区
- [ ] 语义色没串：红=负面、绿=正面、橙=强调，全片一致
- [ ] 文字没超卡边、没互相叠；居中一律 `align: 'center'`
- [ ] 每拍入场元素 ≤ 12 个；讲到的元素有 frameBox/highlight
- [ ] 贴纸没有杂点、断块；Logo 是官方现行版
