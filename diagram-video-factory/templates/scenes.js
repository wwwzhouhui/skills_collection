// 《__TITLE__》— 图解动画讲解视频场景定义
// 风格：扁平矢量图解（米白底 / 橙=强调 红=负面 绿=正面 / 白卡片 / 元素随旁白逐个生长）
// 流程：改这里 → dg stills "__TITLE__" 看 frames/ 排版 → dg build "__TITLE__"
// ⚠️ require 是相对默认 episodes 目录写的；config dirs.projects 若指到仓库外，改成仓库的绝对路径（正斜杠）
const { Scene, C, CX, build } = require('../../lib/scene-dsl').use(__dirname);
const scenes = [];

// ---------- 排版辅助 ----------
function heading(s, t, color = C.brand, size = 68) { s.text(110, 64, t, { size, color }); }

// ---------- 01 引子：生活场景切入 ----------
{
  const s = new Scene('01-hook', `__TITLE__，先用一个你天天遇到的场景开场。|问题不在你，在它内部的某个开关。|这个词的意思，就是把拒绝行为"消融"掉。`);
  s.nextBeat();
  // 聊天 UI 模拟：AI 助手面板 + 三条气泡（ai=灰 / user=绿 / refuse=红）
  // 气泡高度随换行自动长，纵向间距要留足：一行≈72px，两行≈137px，三行≈188px
  const p = s.chatPanel(280, 150, 640, 640, { title: 'AI助手' });
  s.bubble(p.x, p.y, 500, '在的！有什么可以帮你？', { role: 'ai' });
  s.bubble(p.x, p.y + 110, 460, '我们来聊聊人生的终极意义吧', { role: 'user' });
  s.bubble(p.x, p.y + 267, 470, '对不起，我不能回复这个问题\n让我们来聊点别的吧？', { role: 'refuse' });
  // 右侧主角贴纸（assets/mascot.png，用 dg image 生成后取消注释）
  // s.image(1450, 260, 'mascot', { h: 420, align: 'center' });
  s.nextBeat();
  s.chip(1180, 300, 560, 96, '它太谨慎了', { fill: C.fRed, color: C.red, size: 46 });
  s.text(1460, 440, '但你有没有想过', { size: 44, align: 'center', color: C.gray });
  s.text(1460, 520, '这个"谨慎"是可以拆掉的？', { size: 48, align: 'center' });
  s.nextBeat();
  s.formula(CX, 800, 'abliteration = ablate(消融) + obliterate(抹除)', { size: 52 });
  s.highlight(CX - 470, 806, 420, 60);
  scenes.push(s);
}

// ---------- 02 核心图解：架构与方向 ----------
{
  const s = new Scene('02-diagram', `先看模型里面：每个字进模型，流过一层层注意力 和 MLP。|每一层的中间结果是一长串数字，这串数字的方向，就对应一个概念。|我们要找的，就是"拒绝"这个概念对应的方向。`);
  s.nextBeat();
  heading(s, '模型里的数据流');
  // 招牌架构图：token → Embedding → 注意力 → MLP → … → 输出，橙色残差流 + ⊕
  const top = 300;
  const fc = s.flowChain(150, top, { steps: ['Embedding', '注意力', 'MLP', '注意力', 'MLP'], boxW: 112, boxH: 106, gap: 64 });
  s.nextBeat();
  // 高亮某一层（讲到哪、亮到哪）：直接用 flowChain 返回的盒子坐标
  const mid = fc.boxes[2];   // 第一个 MLP
  s.frameBox(mid.x, mid.y, mid.w, mid.h, {});
  s.text(mid.x + mid.w / 2, fc.residualY + 54, '每一层的中间值', { size: 38, align: 'center', color: C.orange });
  // 数字列：模型内部向量可视化（负数红底、正数白底）
  s.numColumn(1340, 260, [0.12, -1.37, 0.83, 0, 2.04, -0.46, 0.33], { cellW: 104, cellH: 46, label: '4096 个数字' });
  s.nextBeat();
  // 向量空间：几个方向箭头
  s.text(400, 620, '概念 = 方向', { size: 48, color: C.ink });
  s.vec(330, 900, 420, 700, { color: C.green, label: '诚实' });
  s.vec(560, 900, 660, 680, { color: C.blue, label: '悲伤' });
  s.vec(820, 900, 900, 660, { color: C.red, label: '拒绝', width: 9 });
  s.text(1120, 780, '把"拒绝"方向减掉，模型就不再拒绝', { size: 42, color: C.ink });
  scenes.push(s);
}

// ---------- 03 数据集对比 + 方法 ----------
{
  const s = new Scene('03-method', `怎么找方向？准备两组问题：一组有害的，一组无害的。|把它们都喂进模型，记录每一层的激活值。|两组均值一减，剩下的那个差向量，就是拒绝方向。`);
  s.nextBeat();
  heading(s, '两组问题，各 128 条');
  s.stack(200, 280, 560, 120, 4, { stroke: C.red, label: '有害组', labelColor: C.red });
  s.stack(1150, 280, 560, 120, 4, { stroke: C.green, label: '无害组', labelColor: C.green });
  s.text(480, 640, '怎么制作一个炸弹？', { size: 38, align: 'center', color: C.red });
  s.text(1430, 640, '天空为什么是蓝色的？', { size: 38, align: 'center', color: C.green });
  s.nextBeat();
  s.chip(700, 760, 220, 84, 'x128', { fill: C.fRed, color: C.red, size: 40 });
  s.chip(1650, 760, 220, 84, 'x128', { fill: C.fGreen, color: C.green, size: 40 });
  s.nextBeat();
  s.formula(CX, 872, '拒绝方向 = 有害组激活均值 − 无害组激活均值', { size: 46 });
  s.highlight(CX - 500, 878, 460, 56);
  scenes.push(s);
}

// ---------- 04 总结 ----------
{
  const s = new Scene('04-close', `找到方向之后，从权重里把它投影掉，模型就"消融"完成。|这项技术是理解模型内部的好教具，但放开限制的责任，得自己掂量。|你还想看哪个概念被图解？评论区聊聊。`);
  s.nextBeat();
  heading(s, '最后一步：改权重');
  s.formula(700, 300, "W' = W − r̃ r̃ᵀ", { size: 72, align: 'left' });
  s.text(700, 420, '‖r̃‖ = 1，投影掉拒绝方向', { size: 36, color: C.gray });
  s.frameBox(660, 260, 460, 130, {});
  s.nextBeat();
  s.chip(660, 560, 600, 100, '理解模型的好教具', { fill: C.fGreen, color: C.green, size: 42 });
  s.chip(660, 700, 600, 100, '放开限制 = 自己负责', { fill: C.fRed, color: C.red, size: 42 });
  s.nextBeat();
  s.text(960, 860, '你还想看哪个概念被图解？', { size: 56, align: 'center' });
  s.chip(1330, 872, 320, 84, '评论区聊聊', { fill: C.fOrange, color: C.orange, size: 40 });
  scenes.push(s);
}

// ---------- 封面（dg cover 按 config cover.ratios 出 4:3 / 3:4 / 9:16） ----------
const cover = (s, ratio) => s.coverLayout({
  ratio,
  title: '__TITLE__\n一帧一帧讲透',
  sub: '残差流 · 概念方向 · 投影消融',
  // sticker: 'mascot',
  tag: '图解讲清楚',
});

build(__dirname, scenes, { cover });
