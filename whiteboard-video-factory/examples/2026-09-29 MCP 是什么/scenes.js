const { Scene, C, CX, build } = require(require('path').join(__dirname, '../../lib/scene-dsl')).use(__dirname);
const scenes = [];

function heading(s, t, color = C.brand) { s.text(120, 60, t, { size: 80, color }); }

// 圆角卡片 + 居中文字
function card(s, x, y, w, h, t, color = C.ink, fill = C.fYellow, size = 48) {
  s.rect(x, y, w, h, { round: true, fill, fillStyle: 'solid' });
  s.text(x + w / 2, y + h / 2 - size * 0.62, t, { size, align: 'center', color });
}

// 小方块（AI 应用 / 数据源 / 能力方）
function chip(s, x, y, w, h, t, { stroke = C.ink, fill = C.fBlue, style = 'solid', size = 40, color = C.ink } = {}) {
  s.rect(x, y, w, h, { round: true, fill, fillStyle: style, stroke, strokeWidth: 3 });
  s.text(x + w / 2, y + h / 2 - size * 0.62, t, { size, align: 'center', color });
}

// 汇聚图标：左三根进 → 中间标准柱 → 右三根出（M×N 变 M+N）
function fanIcon(s, cx, cy, w, h) {
  const left = cx - w / 2, right = cx + w / 2;
  const ys = [cy - h * 0.40, cy, cy + h * 0.40];
  const lx = left + w * 0.32, rx = right - w * 0.32;
  ys.forEach((y) => s.line([[left, y], [lx, cy]], { stroke: C.blue, strokeWidth: 5 }));
  ys.forEach((y) => s.line([[rx, cy], [right, y]], { stroke: C.orange, strokeWidth: 5 }));
  s.rect(lx, cy - h * 0.17, rx - lx, h * 0.34, { round: true, fill: C.fGreen, fillStyle: 'solid', stroke: C.brand, strokeWidth: 5 });
  const size = Math.round(h * 0.2);
  s.text((lx + rx) / 2, cy - size * 0.62, 'MCP', { size, align: 'center', color: C.brand });
}

// ---------- 01 开场：工具越来越多，连线越接越乱 ----------
{
  const s = new Scene('01-hook', `你日常用的 AI 工具，正在变得越来越多。|它们都想连上你的文件、日历、数据库。|可在以前，每连一个新东西，都得单独打通一次。`);
  s.nextBeat();
  heading(s, 'AI 工具，越接越多');
  chip(s, 220, 300, 380, 130, 'AI 助手', { stroke: C.blue, fill: C.fBlue, size: 46 });
  chip(s, 220, 480, 380, 130, '编程助手', { stroke: C.blue, fill: C.fBlue, size: 46 });
  chip(s, 220, 660, 380, 130, '办公助手', { stroke: C.blue, fill: C.fBlue, size: 46 });
  s.nextBeat();
  chip(s, 1320, 300, 380, 130, '文件', { stroke: C.orange, fill: C.fYellow, size: 46 });
  chip(s, 1320, 480, 380, 130, '日历', { stroke: C.orange, fill: C.fYellow, size: 46 });
  chip(s, 1320, 660, 380, 130, '数据库', { stroke: C.orange, fill: C.fYellow, size: 46 });
  s.nextBeat();
  s.line([[600, 365], [1320, 725]], { stroke: C.red, strokeWidth: 3 });
  s.line([[600, 725], [1320, 365]], { stroke: C.red, strokeWidth: 3 });
  s.line([[600, 545], [1320, 545]], { stroke: C.red, strokeWidth: 3 });
  s.line([[600, 365], [1320, 545]], { stroke: C.red, strokeWidth: 3 });
  s.line([[600, 545], [1320, 365]], { stroke: C.red, strokeWidth: 3 });
  s.line([[600, 725], [1320, 545]], { stroke: C.red, strokeWidth: 3 });
  s.text(CX, 850, '每连一个新东西，都要单独打通一次', { size: 46, align: 'center', color: C.red });
  scenes.push(s);
}

// ---------- 02 痛点：M × N ----------
{
  const s = new Scene('02-mn', `十个 AI 工具，十个数据源，最老实的办法，是写一百套对接。|这就是所谓的 M 乘 N 问题。底下数据一变，上面的工具全都得跟着改。`);
  s.nextBeat();
  heading(s, '最笨的办法：一套一套接');
  card(s, 150, 300, 400, 200, '10 个 AI 工具', C.blue, C.fBlue, 44);
  s.text(600, 355, '×', { size: 80, align: 'center', color: C.gray });
  card(s, 650, 300, 400, 200, '10 个数据源', C.orange, C.fYellow, 44);
  s.text(1100, 355, '=', { size: 80, align: 'center', color: C.gray });
  card(s, 1150, 300, 560, 200, '100 套对接', C.red, C.fRed, 56);
  s.nextBeat();
  s.text(CX, 560, 'M × N', { size: 170, align: 'center', color: C.red });
  s.text(CX, 800, '加一个数据源，M 个工具全都要改', { size: 52, align: 'center' });
  s.squiggle(560, 1360, 900, { color: C.red });
  scenes.push(s);
}

// ---------- 03 解法：一个标准 ----------
{
  const s = new Scene('03-standard', `MCP 换了个思路：工具不用跟每个数据源单独对接，大家都去对接同一个标准就行。|写一次，所有支持 MCP 的 AI 都能用，不用为每家单独再写一遍。|官方自己的比喻是，MCP 就是 AI 应用的 USB-C 口。M 乘 N，也变成了 M 加 N。`);
  s.nextBeat();
  heading(s, '一个标准，替掉一堆线');
  chip(s, 180, 250, 340, 100, 'AI 助手', { stroke: C.blue, fill: C.fBlue, size: 42 });
  chip(s, 180, 380, 340, 100, '编程助手', { stroke: C.blue, fill: C.fBlue, size: 42 });
  chip(s, 180, 510, 340, 100, '办公助手', { stroke: C.blue, fill: C.fBlue, size: 42 });
  s.rect(830, 260, 260, 380, { round: true, fill: C.fGreen, fillStyle: 'solid', stroke: C.brand, strokeWidth: 5 });
  s.text(960, 400, 'MCP', { size: 72, align: 'center', color: C.brand });
  s.line([[520, 300], [830, 320]], { stroke: C.blue, strokeWidth: 4 });
  s.line([[520, 430], [830, 450]], { stroke: C.blue, strokeWidth: 4 });
  s.line([[520, 560], [830, 580]], { stroke: C.blue, strokeWidth: 4 });
  s.nextBeat();
  chip(s, 1400, 250, 340, 100, '文件', { stroke: C.orange, fill: C.fYellow, size: 42 });
  chip(s, 1400, 380, 340, 100, '日历', { stroke: C.orange, fill: C.fYellow, size: 42 });
  chip(s, 1400, 510, 340, 100, '数据库', { stroke: C.orange, fill: C.fYellow, size: 42 });
  s.line([[1090, 320], [1400, 300]], { stroke: C.orange, strokeWidth: 4 });
  s.line([[1090, 450], [1400, 430]], { stroke: C.orange, strokeWidth: 4 });
  s.line([[1090, 580], [1400, 560]], { stroke: C.orange, strokeWidth: 4 });
  s.nextBeat();
  s.text(760, 690, 'M × N', { size: 76, align: 'center', color: C.gray });
  s.arrow([[900, 728], [1020, 728]], { stroke: C.gray, strokeWidth: 6 });
  s.text(1180, 690, 'M + N', { size: 76, align: 'center', color: C.brand });
  s.text(CX, 850, '官方比喻：MCP 就是 AI 应用的 USB-C 口', { size: 44, align: 'center', color: C.gray });
  scenes.push(s);
}

// ---------- 04 三个角色：Host / Client / Server ----------
{
  const s = new Scene('04-roles', `MCP 里有三个角色。第一个是 Host，就是你正在用的那个 AI 应用，比如 ChatGPT、Claude、VS Code。|第二个是 Server，能力提供方。它可以是电脑上的一个本地程序，也可以是远端的服务。|第三个是 Client，藏在中间。Host 给每个 Server 各配一个 Client，一对一连着，权限才能分开管。`);
  s.nextBeat();
  heading(s, '三个角色，各管一段');
  s.text(420, 190, '① Host', { size: 52, align: 'center', color: C.blue });
  s.rect(110, 260, 620, 520, { round: true, fill: C.fBlue, fillStyle: 'hachure', stroke: C.blue, strokeWidth: 4, roughness: 1.2 });
  s.text(420, 292, '你在用的 AI 应用', { size: 40, align: 'center' });
  s.text(420, 354, 'ChatGPT / Claude / VS Code', { size: 32, align: 'center', color: C.gray });
  s.nextBeat();
  s.text(1590, 190, '② Server', { size: 52, align: 'center', color: C.orange });
  chip(s, 1400, 380, 380, 110, '本地程序', { stroke: C.orange, fill: C.fYellow, size: 42 });
  chip(s, 1400, 540, 380, 110, '公司内部服务', { stroke: C.orange, fill: C.fYellow, size: 42 });
  chip(s, 1400, 700, 380, 110, '第三方服务', { stroke: C.orange, fill: C.fYellow, size: 42 });
  s.nextBeat();
  s.text(420, 420, '③ Client（每个 Server 一个）', { size: 32, align: 'center', color: C.purple });
  chip(s, 170, 470, 500, 80, 'Client', { stroke: C.purple, fill: '#ffffff', size: 38 });
  chip(s, 170, 570, 500, 80, 'Client', { stroke: C.purple, fill: '#ffffff', size: 38 });
  chip(s, 170, 670, 500, 80, 'Client', { stroke: C.purple, fill: '#ffffff', size: 38 });
  s.line([[670, 510], [1400, 435]], { stroke: C.purple, strokeWidth: 3 });
  s.line([[670, 610], [1400, 595]], { stroke: C.purple, strokeWidth: 3 });
  s.line([[670, 710], [1400, 755]], { stroke: C.purple, strokeWidth: 3 });
  s.text(CX, 870, '一个 Server 配一个 Client，权限才能分开管', { size: 44, align: 'center', color: C.purple });
  scenes.push(s);
}

// ---------- 05 三类能力：Tools / Resources / Prompts ----------
{
  const s = new Scene('05-primitives', `Server 能提供三类东西。第一类，Tools，工具：模型自己决定要不要调用，而且会真的动手，写文件、发消息、查数据库。|第二类，Resources，资源：只读。读一份文档、拉一张表，不改你的数据。|第三类，Prompts，是给人挑的模板，比如「帮我审一遍这段代码」，不是模型自己选。|分清这三类，你就知道 MCP 到底能干什么。其中只有会动手的那一类，才需要你点头。`);
  const colW = 540, top = 230, hgt = 560;
  s.nextBeat();
  heading(s, 'Server 能提供三类东西');
  s.rect(90, top, colW, hgt, { round: true, fill: C.fYellow, fillStyle: 'hachure', stroke: C.orange, strokeWidth: 3, roughness: 1.2 });
  s.text(360, 252, '① Tools 工具', { size: 50, align: 'center', color: C.orange });
  s.text(360, 410, '模型自己决定调用', { size: 44, align: 'center' });
  s.text(360, 530, '会真的动手', { size: 46, align: 'center', color: C.red });
  s.text(360, 670, '写文件 · 发消息 · 查数据库', { size: 32, align: 'center', color: C.gray });
  s.nextBeat();
  s.rect(690, top, colW, hgt, { round: true, fill: C.fBlue, fillStyle: 'hachure', stroke: C.blue, strokeWidth: 3, roughness: 1.2 });
  s.text(960, 252, '② Resources 资源', { size: 50, align: 'center', color: C.blue });
  s.text(960, 410, '只读，不改东西', { size: 44, align: 'center' });
  s.text(960, 530, '读文档 · 拉一张表', { size: 46, align: 'center', color: C.blue });
  s.text(960, 670, '不写、不改、不删', { size: 32, align: 'center', color: C.gray });
  s.nextBeat();
  s.rect(1290, top, colW, hgt, { round: true, fill: C.fPurple, fillStyle: 'hachure', stroke: C.purple, strokeWidth: 3, roughness: 1.2 });
  s.text(1560, 252, '③ Prompts 模板', { size: 50, align: 'center', color: C.purple });
  s.text(1560, 410, '给人挑的模板', { size: 44, align: 'center' });
  s.text(1560, 530, '「帮我审这段代码」', { size: 40, align: 'center', color: C.purple });
  s.text(1560, 670, '模型不自己选，你点了才用', { size: 32, align: 'center', color: C.gray });
  s.nextBeat();
  s.text(360, 812, '会动手 → 要你点头', { size: 38, align: 'center', color: C.red });
  s.text(CX, 895, '分清这三类，你就知道 MCP 能干什么', { size: 44, align: 'center', color: C.ink });
  scenes.push(s);
}

// ---------- 06 时间线 ----------
{
  const s = new Scene('06-timeline', `MCP 是 2024 年 11 月 25 日，被 Anthropic 开源的。到现在还不满两年。|2025 年 12 月 9 日，Anthropic 把 MCP 捐给了 Linux 基金会下面的 Agentic AI Foundation。|那时候，公开的 MCP 服务器已经超过一万个，Python 和 TypeScript 的 SDK 每月下载九千七百万次。|现在 ChatGPT、Claude、Gemini、Copilot、VS Code，都已经支持它。`);
  s.nextBeat();
  heading(s, '不到两年，成了行业默认');
  s.line([[180, 430], [1740, 430]], { stroke: C.gray, strokeWidth: 4 });
  s.ellipse(304, 414, 32, 32, { fill: C.brand, fillStyle: 'solid', stroke: C.brand, strokeWidth: 3 });
  s.text(320, 298, '2024.11.25', { size: 42, align: 'center' });
  s.text(320, 468, 'Anthropic 开源 MCP', { size: 36, align: 'center', color: C.gray });
  s.nextBeat();
  s.ellipse(944, 414, 32, 32, { fill: C.orange, fillStyle: 'solid', stroke: C.orange, strokeWidth: 3 });
  s.text(960, 298, '2025.12.09', { size: 42, align: 'center' });
  s.text(960, 468, '捐给 Linux 基金会', { size: 36, align: 'center', color: C.gray });
  s.nextBeat();
  card(s, 300, 580, 580, 200, '10,000+', C.brand, C.fGreen, 68);
  s.text(590, 726, '公开的 MCP 服务器', { size: 32, align: 'center', color: C.gray });
  card(s, 1040, 580, 580, 200, '9700 万', C.blue, C.fBlue, 68);
  s.text(1330, 726, 'SDK 每月下载次数', { size: 32, align: 'center', color: C.gray });
  s.nextBeat();
  s.ellipse(1568, 414, 32, 32, { fill: C.blue, fillStyle: 'solid', stroke: C.blue, strokeWidth: 3 });
  s.text(1584, 298, '现在', { size: 42, align: 'center' });
  s.text(1584, 468, '主流产品都支持', { size: 36, align: 'center', color: C.gray });
  s.text(CX, 856, 'ChatGPT · Claude · Gemini · Copilot · VS Code', { size: 46, align: 'center' });
  scenes.push(s);
}

// ---------- 07 总结 ----------
{
  const s = new Scene('07-close', `所以 MCP 不是什么新功能，它就是把 M 乘 N 变成 M 加 N 的那根线。|对普通用户，记住一句就够了：以后看一个 AI 工具强不强，看它能接多少 MCP。|你的 AI 工具，现在接上几个了？`);
  s.nextBeat();
  heading(s, '一句话记住 MCP');
  card(s, 180, 230, 440, 170, 'M × N', C.red, C.fRed, 58);
  s.arrow([[660, 315], [790, 315]], { stroke: C.gray, strokeWidth: 8 });
  card(s, 820, 230, 440, 170, 'M + N', C.brand, C.fGreen, 58);
  s.text(CX, 460, '写一次，到处能用', { size: 52, align: 'center' });
  s.nextBeat();
  s.text(CX, 600, '看一个 AI 工具强不强，', { size: 60, align: 'center' });
  s.text(CX, 695, '看它能接多少 MCP。', { size: 64, align: 'center', color: C.brand });
  s.nextBeat();
  card(s, 300, 825, 1000, 120, '你的 AI 工具，现在接上几个了？', C.ink, C.fYellow, 46);
  s.ellipse(1400, 833, 300, 104, { stroke: C.orange, fill: C.fYellow, fillStyle: 'solid' });
  s.text(1550, 856, '评论区聊聊', { size: 38, align: 'center', color: C.orange });
  scenes.push(s);
}

// ---------- 封面（wb cover 按 config cover.ratios 出 4:3 / 3:4 / 9:16） ----------
const cover = (s, ratio) => {
  s.coverLayout({
    ratio,
    title: 'MCP 是什么\nAI 的 USB-C 口',
    sub: '1 万+ 服务器 · 9700 万次月下载',
    tag: '白板 3 分钟讲清楚',
  });
  if (ratio === '4:3') fanIcon(s, 1040, 880, 620, 340);
  else if (ratio === '3:4') fanIcon(s, 540, 950, 640, 400);
  else if (ratio === '9:16') fanIcon(s, 540, 1250, 640, 400);
  else fanIcon(s, 1400, 560, 520, 320);
};
build(__dirname, scenes, { cover });
