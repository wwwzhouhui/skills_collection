// 《__TITLE__》— 手绘白板讲解视频场景定义
// 流程：改这里 → wb stills "__TITLE__" 看 frames/ 排版 → wb build "__TITLE__" 出片（out/final.mp4）
//
// 规则：
//  - 旁白用 `|` 切成若干段（beat），每段前调用 s.nextBeat()，之后添加的元素会在这段旁白播放时画出来
//  - 画布 1920×1080，CX 是水平中心；元素按添加顺序逐笔绘制；底部 y≥960 留给字幕，别放元素
//  - 可用: s.text / s.rect / s.ellipse / s.diamond / s.line / s.arrow，以及复合图形
//    s.robot / s.laptop / s.cloud / s.person / s.checkbox / s.moon / s.squiggle
//  - 人物/器械等复杂图形用贴纸: 先 wb image "<标题>" name="英文描述"，再 s.image(x, y, 'name', { h: 370, align: 'center' })
//  - 颜色 C.ink/gray/red/green/blue/orange/purple，填充 C.fRed/fGreen/fBlue/fYellow/fPurple/fGray；C.brand 是品牌色（config.json brand.accent），大标题/点睛优先用它
//  - 右上角 320×130 是品牌水印区（config.json brand.watermark），别放元素；片尾品牌卡由 wb build 自动追加，不用写
//  - 封面在文件末尾 cover 函数里定义（s.coverLayout），也可以在里面再加 s.text/s.image 自由发挥（ratio 判断坐标）
//  - 一段旁白 3~4 句、一屏元素 10~20 个最舒服；**时长按场景数定**，约「1 分钟 ≈ 1.5~2 个场景 ≈ 200 字」（短片 6~8 场景 ≈ 2~3 分钟；长片 40+ 场景，打分幕与呼吸点，见 SKILL.md「做长片」）
const { Scene, C, CX, build } = require('__WB_ROOT__/lib/scene-dsl').use(__dirname);
const scenes = [];

// ---------- 场景 1：开场 ----------
{
  const s = new Scene('01-intro', `第一段旁白，画标题。| 第二段旁白，画一个对比。| 第三段旁白，抛出问题。`);
  s.nextBeat();
  s.robot(520, 330, 1.1);
  s.text(800, 330, '标题', { size: 150, color: C.brand });
  s.text(815, 510, '副标题 · 日期', { size: 40, color: C.gray });
  s.nextBeat();
  s.ellipse(240, 700, 420, 150, { fill: C.fGray, fillStyle: 'solid' });
  s.text(450, 745, '旧东西', { size: 42, align: 'center' });
  s.text(720, 700, '≠', { size: 120, color: C.red });
  s.nextBeat();
  s.text(880, 720, '到底是什么？', { size: 84 });
  s.squiggle(880, 1390, 830);
  scenes.push(s);
}

// ---------- 场景 2：主体 ----------
{
  const s = new Scene('02-body', `标题一句。| 左边讲 A。| 右边讲 B。`);
  s.nextBeat();
  s.text(CX, 60, '两个东西', { size: 90, align: 'center' });
  s.line([[CX, 200], [CX, 940]], { strokeStyle: 'dashed', stroke: C.gray });
  s.nextBeat();
  s.text(480, 200, 'A', { size: 80, color: C.blue, align: 'center' });
  s.text(280, 640, '· 要点 1\n· 要点 2\n· 要点 3', { size: 40 });
  s.nextBeat();
  s.text(1440, 200, 'B', { size: 80, color: C.purple, align: 'center' });
  s.laptop(1180, 420, 1.1);
  s.text(1100, 700, '结论', { size: 56, color: C.purple });
  scenes.push(s);
}

// ---------- 场景 3：总结 ----------
{
  const s = new Scene('03-outro', `一句话总结。| 抛个问题，引导评论。`);
  s.nextBeat();
  s.text(CX, 250, 'A  →  会说', { size: 72, align: 'center', color: C.blue });
  s.text(CX, 370, 'B  →  会做', { size: 72, align: 'center', color: C.purple });
  s.nextBeat();
  s.text(CX, 820, '你会先把哪个活儿交给它？', { size: 56, align: 'center' });
  s.ellipse(1500, 780, 240, 110, { fill: C.fYellow, fillStyle: 'solid' });
  s.text(1620, 812, '评论区聊聊', { size: 36, align: 'center' });
  scenes.push(s);
}

// ---------- 封面（wb cover 出 封面-4x3.png / 封面-3x4.png / 封面-9x16.png，画幅见 config cover.ratios；wb build 也会出） ----------
// title 两行以内、每行 ≤8 字，默认最后一行是钩子（品牌绿 + 马克笔高亮）；sticker 用本期主角贴纸；sub 可省
const cover = (s, ratio) => s.coverLayout({
  ratio,
  title: '第一行说对象\n第二行说钩子',
  sub: '一句补充（可省）',
  // sticker: 'figure-name',
});
build(__dirname, scenes, { cover });
