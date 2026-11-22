// 场景 DSL（图解动画版）：扁平矢量风格（参考"程序员老王"式科技图解视频）
// 与白板版的差别：线条干净（roughness:0、无手绘质感）、语义色纪律（橙=强调 / 红=负面 / 绿=正面）、
// 元素以"淡入+缩放生长"逐个出现（渲染器实现），本文件只负责产出元素与节拍。
// 元素仍是 Excalidraw 格式（可在 Obsidian 里微调），复合图形（流程链/聊天气泡/卡片堆/数字列）都由基础元素拼成。
// 项目里的 scenes.js 只需 require 这个文件，定义场景，最后 build(__dirname, scenes)。
const fs = require('fs');
const path = require('path');
const { projectPaths, cfg } = require('./paths.cjs');

let OUT = null;

// 图解风调色板：语义色纪律——橙=强调/主线，红=负面（拒绝/有害/风险），绿=正面（无害/通过/收益）。
// 一期从头到尾同一语义只用同一种颜色，观众扫一眼就知道好坏。
const C = {
  paper: '#E9E9E4',            // 全片背景（渲染器从 config render.paper 读，这里供封面/Obsidian 预览参考）
  ink: '#2B2B2B', gray: '#8A8A85', faint: '#C2C2BB', white: '#FFFFFF',
  orange: '#E8833A', red: '#D64541', green: '#5B8C5A', blue: '#4A7DB5', yellow: '#E0A93E',
  fOrange: '#F7E0C8', fRed: '#F3D4D1', fGreen: '#DFE9DE', fBlue: '#DCE6F0', fYellow: '#F6EBCB', fGray: '#ECECE8',
  grayFill: '#F0F0EC',         // AI 聊天气泡底
  brand: (cfg.brand && cfg.brand.accent) || '#E8833A', // 品牌色（config.json brand.accent），标题/点睛用它保持全系列一致
};

let idCounter = 0;
const nextId = () => 'el' + (++idCounter).toString(36).padStart(6, '0');

const isCJK = (ch) => /[　-鿿＀-￯]/.test(ch);
function measure(text, fs) {
  const lines = text.split('\n');
  let w = 0;
  for (const l of lines) {
    let lw = 0;
    for (const ch of l) lw += isCJK(ch) ? fs : fs * 0.55;
    w = Math.max(w, lw);
  }
  return { width: Math.round(w), height: Math.round(fs * 1.25 * lines.length) };
}
// 按宽度折行（气泡/长文案用）：中文逐字、英文按词
function wrap(text, fs, maxW) {
  const out = [];
  for (const para of text.split('\n')) {
    let line = '';
    for (const word of para.split(/(\s+)/)) {
      const t = line + word;
      if (measure(t, fs).width <= maxW || !line) line = t;
      else { out.push(line.trimEnd()); line = word.trimStart(); }
      // 单个超长词（无空格长串）按字符硬切
      while (measure(line, fs).width > maxW && line.length > 1) {
        let cut = line.length - 1;
        while (cut > 1 && measure(line.slice(0, cut), fs).width > maxW) cut--;
        out.push(line.slice(0, cut)); line = line.slice(cut);
      }
    }
    out.push(line);
  }
  return out.join('\n');
}

function base(type, x, y, w, h, o = {}) {
  return {
    id: nextId(), type, x, y, width: w, height: h, angle: 0,
    strokeColor: o.stroke || C.ink, backgroundColor: o.fill || 'transparent',
    fillStyle: 'solid', strokeWidth: o.strokeWidth || 2,
    strokeStyle: o.strokeStyle || 'solid', roughness: 0, opacity: o.opacity ?? 100,
    roundness: o.round === false ? null : { type: 3 },   // 图解风默认圆角矩形
    radius: o.radius,                                     // 渲染器用：圆角像素（不进 Excalidraw 标准属性也不碍事）
    anim: o.anim,                                         // 入场动画覆盖：fade / rise / pop / wipe（缺省按元素类型）
    groupIds: [], frameId: null,
    seed: 4242, version: 1, versionNonce: 4242, isDeleted: false,
    boundElements: null, updated: Date.now(), link: null, locked: false,
  };
}

class Scene {
  constructor(name, narration) {
    this.name = name;
    this.segments = narration.split('|').map((s) => s.trim()).filter(Boolean);
    this.elements = [];
    this.files = {};
    this.assetsDir = null;
    this.beatOf = []; // element index -> beat index
    this.beat = -1;
    this._gid = 0;    // 逻辑单元计数：渲染器按 gid 分组，同组元素同起同落（复合图形=一个整体入场）
    this._unit = null;
  }
  nextBeat() { this.beat++; this._unit = null; return this; }
  // 把若干元素标成一个"逻辑单元"（同拍内一起入场）。嵌套调用（flowChain 里调 flowBox）沿用外层单元。
  unit(fn) { const saved = this._unit; if (saved == null) this._unit = 'u' + (this._gid++); try { return fn(); } finally { this._unit = saved; } }
  push(el) {
    if (this.beat < 0) throw new Error('call nextBeat() first');
    if (this._unit != null) el.gid = this._unit; else el.gid = 'u' + (this._gid++);
    this.elements.push(el); this.beatOf.push(this.beat); return el;
  }
  rect(x, y, w, h, o = {}) { return this.push(base('rectangle', x, y, w, h, o)); }
  ellipse(x, y, w, h, o = {}) { return this.push(base('ellipse', x, y, w, h, o)); }
  diamond(x, y, w, h, o = {}) { return this.push(base('diamond', x, y, w, h, o)); }
  text(x, y, str, o = {}) {
    const fs = o.size || 36;
    const m = measure(str, fs);
    let tx = x;
    if (o.align === 'center') tx = x - m.width / 2;
    if (o.align === 'right') tx = x - m.width;
    const el = base('text', tx, y, m.width, m.height, { stroke: o.color || C.ink, round: false, ...o });
    Object.assign(el, {
      text: str, originalText: str, fontSize: fs, fontFamily: o.font || 5,
      textAlign: o.align || 'left', verticalAlign: 'top', containerId: null, autoResize: true, lineHeight: 1.25,
      italic: !!o.italic, weight: o.weight == null ? 700 : o.weight,
    });
    return this.push(el);
  }
  line(points, o = {}) {
    const xs = points.map((p) => p[0]), ys = points.map((p) => p[1]);
    const x = Math.min(...xs), y = Math.min(...ys);
    const el = base(o.arrow ? 'arrow' : 'line', x, y, Math.max(...xs) - x, Math.max(...ys) - y, o);
    if (o.round) el.roundness = { type: 2 };
    Object.assign(el, {
      points: points.map((p) => [p[0] - x, p[1] - y]), lastCommittedPoint: null,
      startBinding: null, endBinding: null, startArrowhead: o.startHead || null,
      endArrowhead: o.arrow ? 'arrow' : null, elbowed: false,
    });
    return this.push(el);
  }
  arrow(points, o = {}) { return this.line(points, { ...o, arrow: true }); }
  // 贴纸图片：name 对应 <project>/assets/<name>.png（gen-image.mjs 产物）。给 w 或 h 之一按原图比例算另一个。
  image(x, y, name, o = {}) {
    const file = path.join(projectPaths(module.exports.projectDir).assets, `${name}.png`);
    if (!fs.existsSync(file)) throw new Error(`缺少贴纸 assets/${name}.png，先跑 dg image`);
    return this.imageFile(x, y, file, o);
  }
  // 贴纸原图尺寸（排版前算宽高比用）
  imageSize(name) {
    const buf = fs.readFileSync(path.join(projectPaths(module.exports.projectDir).assets, `${name}.png`));
    return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  }
  // 任意 png 文件（品牌 logo 等）；name 用文件名
  imageFile(x, y, file, o = {}) {
    const name = path.basename(file, '.png');
    const buf = fs.readFileSync(file);
    const iw = buf.readUInt32BE(16), ih = buf.readUInt32BE(20);
    let w = o.w, h = o.h;
    if (w && !h) h = Math.round(w * ih / iw);
    if (h && !w) w = Math.round(h * iw / ih);
    if (!w) { w = iw; h = ih; }
    if (o.align === 'center') x = x - w / 2;
    const fileId = 'img_' + name.replace(/[^a-z0-9]/gi, '_');
    const el = base('image', x, y, w, h, {});
    Object.assign(el, { fileId, status: 'saved', scale: [1, 1], crop: null });
    this.files[fileId] = { mimeType: 'image/png', id: fileId, dataURL: 'data:image/png;base64,' + buf.toString('base64'), created: Date.now(), name: `${name}.png` };
    return this.push(el);
  }

  // ---- 图解复合图形（全部由基础元素拼成，Obsidian 里仍可拆开微调）----

  // 白圆角卡片：图解风的基本容器
  card(x, y, w, h, o = {}) {
    return this.rect(x, y, w, h, {
      fill: o.fill || C.white, stroke: o.stroke || C.faint, strokeWidth: o.sw || 2,
      radius: o.radius == null ? 24 : o.radius, ...o,
    });
  }
  // 强调框：橙色圆角描边，"讲到哪、亮到哪"——框在要强调的元素外面
  frameBox(x, y, w, h, o = {}) {
    return this.rect(x - 8, y - 8, w + 16, h + 16, { stroke: o.color || C.orange, strokeWidth: o.sw || 5, fill: 'transparent', radius: (o.radius == null ? 24 : o.radius) + 8, anim: o.anim });
  }
  // 平头马克笔高亮：无描边浅橙圆角实底，放在文字前面 push 就垫在字下
  highlight(x, y, w, h, o = {}) {
    return this.rect(x, y, w, h, { fill: o.color || C.fOrange, stroke: o.color || C.fOrange, radius: 10, opacity: o.opacity ?? 100 });
  }
  // 章节大标题：左上角，品牌色
  heading(t, o = {}) {
    return this.text(o.x || 110, o.y || 64, t, { size: o.size || 68, color: o.color || C.brand });
  }
  // 圆角小徽章（chip）+ 居中文字，如「有害组」「假设」「第1层」
  chip(x, y, w, h, label, o = {}) {
    return this.unit(() => {
      this.rect(x, y, w, h, { fill: o.fill || C.fOrange, stroke: o.stroke || o.fill || C.orange, strokeWidth: o.sw || 2, radius: o.radius == null ? h / 2 : o.radius });
      const size = o.size || Math.min(38, h * 0.52);
      this.text(x + w / 2, y + h / 2 - size * 0.62, label, { size, align: 'center', color: o.color || C.ink, weight: o.weight });
      return { x, y, w, h };
    });
  }

  // 聊天 UI：白色圆角面板 + 顶栏（AI 徽章 + 标题）+ 分隔线；返回内容区 {x,y,w,h}
  chatPanel(x, y, w, h, o = {}) {
    return this.unit(() => {
      this.card(x, y, w, h, { radius: 28, stroke: C.faint });
      const bar = o.titleSize || 40;
      this.chip(x + 28, y + 24, 62, 52, 'AI', { fill: C.orange, color: C.white, size: 30, weight: 800, radius: 26 });
      this.text(x + 108, y + 30, o.title || 'AI助手', { size: bar });
      this.line([[x + 2, y + 100], [x + w - 2, y + 100]], { stroke: C.faint, strokeWidth: 2 });
      return { x: x + 28, y: y + 124, w: w - 56, h: h - 152 };
    });
  }
  // 聊天气泡。role：ai=浅灰墨字 / user=深绿白字 / refuse=红底白字。x 为左缘，自动算高度；返回 {x,y,w,h}
  bubble(x, y, w, text, o = {}) {
    return this.unit(() => {
      const size = o.size || 38;
      const lines = wrap(text, size, w - 56).split('\n');
      const h = Math.max(72, lines.length * size * 1.35 + 34);
      const roles = {
        ai: { fill: C.grayFill, stroke: C.faint, color: C.ink },
        user: { fill: '#4A6B52', stroke: '#4A6B52', color: '#FFFFFF' },
        refuse: { fill: C.red, stroke: C.red, color: '#FFFFFF' },
      };
      const r = roles[o.role || 'ai'];
      this.rect(x, y, w, h, { fill: r.fill, stroke: r.stroke, radius: 20 });
      this.text(x + 28, y + h / 2 - (lines.length * size * 1.35) / 2 + size * 0.12, lines.join('\n'), { size, color: r.color, lineHeight: 1.35 });
      return { x, y, w, h };
    });
  }

  // 流程盒子：白圆角盒 + 内部图标 + 盒上方斜体标签（Embedding/注意力/MLP…）
  // icon：cube=Embedding 立方体 / gear=注意力齿轮 / grid=MLP 网格 / dot=token 圆点 / blank=空
  flowBox(x, y, w, h, label, o = {}) {
    return this.unit(() => {
      const icon = o.icon || 'blank', col = o.color || C.orange;
      if (label) this.text(x + w / 2, y - (o.labelSize || 40) - 14, label, { size: o.labelSize || 40, align: 'center', italic: true, color: o.labelColor || C.ink });
      this.rect(x, y, w, h, { fill: C.white, stroke: C.ink, strokeWidth: 3, radius: 18 });
      const cx = x + w / 2, cy = y + h / 2, s = Math.min(w, h) * 0.30;
      if (icon === 'cube') {
        this.line([[cx, cy - s], [cx + s, cy - s * 0.4], [cx + s, cy + s * 0.5], [cx, cy + s * 0.95], [cx - s, cy + s * 0.5], [cx - s, cy - s * 0.4], [cx, cy - s]], { stroke: col, strokeWidth: 3, fill: C.fOrange });
        this.line([[cx - s, cy - s * 0.4], [cx, cy + s * 0.1], [cx + s, cy - s * 0.4]], { stroke: col, strokeWidth: 3 });
        this.line([[cx, cy + s * 0.1], [cx, cy + s * 0.95]], { stroke: col, strokeWidth: 3 });
      } else if (icon === 'gear') {
        this.ellipse(cx - s * 0.75, cy - s * 0.75, s * 1.5, s * 1.5, { stroke: col, strokeWidth: 3, fill: C.fOrange });
        this.ellipse(cx - s * 0.28, cy - s * 0.28, s * 0.56, s * 0.56, { stroke: col, strokeWidth: 3, fill: C.white });
        for (let k = 0; k < 8; k++) {
          const a = (k / 8) * Math.PI * 2;
          this.line([[cx + Math.cos(a) * s * 0.75, cy + Math.sin(a) * s * 0.75], [cx + Math.cos(a) * s * 1.05, cy + Math.sin(a) * s * 1.05]], { stroke: col, strokeWidth: 5 });
        }
      } else if (icon === 'grid') {
        const g = s * 2 / 3;
        for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++)
          this.rect(cx - s + i * g + 2, cy - s + j * g + 2, g - 4, g - 4, { stroke: col, strokeWidth: 2, fill: (i + j) % 2 ? C.fOrange : C.white, radius: 4 });
      } else if (icon === 'dot') {
        this.ellipse(cx - s * 0.45, cy - s * 0.45, s * 0.9, s * 0.9, { stroke: C.ink, strokeWidth: 3, fill: C.white });
      }
      return { x, y, w, h };
    });
  }
  // 招牌架构图：token → [Embedding→注意力→MLP→…→注意力→MLP] → 输出，橙色残差流底线 + ⊕ 逐层相加。
  // steps: ['Embedding','注意力','MLP','注意力','MLP']（缺省按图标自动配）或 [{label,icon}]
  // 返回 { boxes: [{x,y,w,h,label}], residualY }，方便之后 frameBox 高亮某一层
  flowChain(x, y, o = {}) {
    return this.unit(() => {
      const defs = o.steps || ['Embedding', '注意力', 'MLP', '注意力', 'MLP'];
      const icons = { Embedding: 'cube', 注意力: 'gear', MLP: 'grid', 输出: 'blank' };
      const bw = o.boxW || 118, bh = o.boxH || 104, gap = o.gap || 62, dotR = 15;
      const n = defs.length;
      const tokenW = o.tokenW || 84;
      const cy = y + bh / 2, ry = y + bh + (o.residualDrop || 62);
      // token 输入盒
      if (o.token !== false) {
        this.unit(() => {
          this.flowBox(x, cy - tokenW / 2, tokenW, tokenW, null, { icon: 'dot' });
          this.text(x + tokenW / 2, cy + tokenW / 2 + 12, o.tokenLabel || 'token', { size: 30, align: 'center', italic: true, color: C.gray });
        });
        this.unit(() => this.arrow([[x + tokenW + 6, cy], [x + tokenW + 32, cy]], { stroke: C.ink, strokeWidth: 3 }));
      }
      const x0 = x + (o.token === false ? 0 : tokenW + 34);
      const boxes = [];
      let bx = x0;
      defs.forEach((d, i) => {
        const label = typeof d === 'string' ? d : d.label;
        const icon = typeof d === 'string' ? (icons[label] || 'blank') : (d.icon || icons[label] || 'blank');
        // 中段省略号：第 4 个盒子前画「···」
        if (o.ellipsis !== false && i === Math.ceil(n / 2) && n >= 5) {
          this.unit(() => this.text(bx + gap / 2, cy - 16, '···', { size: 44, align: 'center', color: C.ink, weight: 800 }));
          bx += gap; // 省略号占一个 gap 的位置，盒子从 gap 之后开始
        }
        const b = this.flowBox(bx, y, bw, bh, label, { icon, labelSize: o.labelSize || 38 });
        boxes.push({ ...b, label });
        bx += bw;
        if (i < n - 1) {
          const ax = bx;
          this.unit(() => this.arrow([[ax + 8, cy], [ax + gap - 8, cy]], { stroke: C.ink, strokeWidth: 3 }));
          bx += gap;
        }
      });
      // 输出盒
      if (o.out !== false) {
        this.unit(() => {
          this.arrow([[bx + 8, cy], [bx + 34, cy]], { stroke: C.ink, strokeWidth: 3 });
          this.flowBox(bx + 36, cy - tokenW / 2, tokenW, tokenW, null, { icon: 'blank' });
          this.text(bx + 36 + tokenW / 2, cy + tokenW / 2 + 12, o.outLabel || '输出', { size: 30, align: 'center', italic: true, color: C.gray });
        });
      }
      // 橙色残差流：从第一个盒子底部出来，横向贯穿，⊕ 相加进每一层
      if (o.residual !== false) {
        const lastBox = boxes[boxes.length - 1];
        this.unit(() => {
          this.line([[x0 + bw / 2, y + bh], [x0 + bw / 2, ry]], { stroke: C.orange, strokeWidth: 8 });
          this.line([[x0 + bw / 2, ry], [lastBox.x + bw / 2, ry]], { stroke: C.orange, strokeWidth: 8 });
          this.line([[lastBox.x + bw / 2, ry], [lastBox.x + bw / 2, y + bh]], { stroke: C.orange, strokeWidth: 8 });
        });
        boxes.forEach((b, i) => {
          if (i === 0 || i === boxes.length - 1) return;
          const cx = b.x + bw / 2;
          this.unit(() => {
            this.ellipse(cx - dotR, ry - dotR, dotR * 2, dotR * 2, { stroke: C.orange, strokeWidth: 4, fill: C.paper });
            this.line([[cx - 7, ry], [cx + 7, ry]], { stroke: C.orange, strokeWidth: 4 });
            this.line([[cx, ry - 7], [cx, ry + 7]], { stroke: C.orange, strokeWidth: 4 });
            this.arrow([[cx, ry - dotR - 2], [cx, y + bh + 6]], { stroke: C.orange, strokeWidth: 4 });
          });
        });
      }
      return { boxes, residualY: ry, width: bx + 36 + tokenW - x };
    });
  }

  // 卡片堆：数据集（有害组 x128 / 无害组 x128）。x,y 是最上面那张的左上角；下面的卡片向右下偏移
  stack(x, y, w, h, n, o = {}) {
    return this.unit(() => {
      const dx = o.dx == null ? 7 : o.dx, dy = o.dy == null ? 7 : o.dy;
      this.unit(() => {
        for (let i = n - 1; i >= 1; i--) this.rect(x + i * dx, y + i * dy, w, h, { fill: C.white, stroke: o.stroke || C.faint, strokeWidth: 2, radius: 14 });
      });
      this.rect(x, y, w, h, { fill: o.fill || C.white, stroke: o.stroke || C.ink, strokeWidth: 3, radius: 14 });
      if (o.label) this.text(x, y + h + (n - 1) * dy + 14, o.label, { size: o.labelSize || 34, color: o.labelColor || o.stroke || C.ink });
      return { x, y, w: w + (n - 1) * dx, h: h + (n - 1) * dy };
    });
  }
  // 数字列：模型内部向量可视化。values 逐个上色（负=红底、正=白底），高亮下标套橙框；右侧大括号+说明
  numColumn(x, y, values, o = {}) {
    return this.unit(() => {
      const cw = o.cellW || 108, ch = o.cellH || 46, size = o.size || 30;
      values.forEach((v, i) => {
        this.unit(() => {
          const neg = v < 0, yy = y + i * (ch + 6);
          this.rect(x, yy, cw, ch, { fill: neg ? C.fRed : C.white, stroke: neg ? C.red : C.faint, strokeWidth: 2, radius: 8 });
          this.text(x + cw / 2, yy + ch / 2 - size * 0.62, String(v), { size, align: 'center', color: neg ? C.red : C.ink, italic: true });
        });
      });
      const h = values.length * (ch + 6) - 6;
      const bx = x + cw + 18;
      // 右大括号（三段折线近似）
      this.line([[bx, y + 4], [bx + 14, y + 14], [bx + 14, y + h / 2 - 10], [bx + 26, y + h / 2]], { stroke: C.gray, strokeWidth: 3 });
      this.line([[bx + 26, y + h / 2], [bx + 14, y + h / 2 + 10], [bx + 14, y + h - 14], [bx, y + h - 4]], { stroke: C.gray, strokeWidth: 3 });
      if (o.label) this.text(bx + 44, y + h / 2 - (o.labelSize || 44) * 0.62, o.label, { size: o.labelSize || 44, color: o.labelColor || C.ink });
      return { x, y, w: cw + 70 + measure(o.label || '', o.labelSize || 44).width, h };
    });
  }
  // 向量箭头（带长度感）：向量空间里的"方向"。label 放箭头末端旁
  vec(x1, y1, x2, y2, o = {}) {
    return this.unit(() => {
      const el = this.arrow([[x1, y1], [x2, y2]], { stroke: o.color || C.orange, strokeWidth: o.width || 7 });
      if (o.label) this.text(x2 + (x2 >= x1 ? 14 : -14), y2 - 16, o.label, { size: o.labelSize || 34, align: x2 >= x1 ? 'left' : 'right', color: o.color || C.orange, italic: !!o.italic, weight: o.weight });
      return el;
    });
  }
  // 公式：斜体居中文本
  formula(x, y, text, o = {}) {
    return this.text(x, y, text, { size: o.size || 48, align: o.align || 'center', color: o.color || C.ink, italic: true });
  }
  // 参考文献：[{title, sub}]；橙色序号 + 墨色粗体标题 + 灰色斜体出处。返回总高度
  refList(x, y, refs, o = {}) {
    return this.unit(() => {
      const ts = o.titleSize || 40, ss = o.subSize || 30, gap = o.gap || 26;
      let cy = y;
      refs.forEach((r, i) => {
        this.unit(() => {
          const num = `[${i + 1}]`;
          const nw = measure(num, ts).width;
          this.text(x, cy, num, { size: ts, color: C.orange, italic: true });
          this.text(x + nw + 22, cy, r.title, { size: ts, color: C.ink });
          if (r.sub) this.text(x + nw + 22, cy + ts * 1.28, r.sub, { size: ss, color: C.gray, italic: true });
        });
        cy += ts * 1.28 + (r.sub ? ss * 1.4 : 0) + gap;
      });
      return cy - y;
    });
  }

  // 渲染器直接用的文档（不落盘）：片尾品牌卡等虚拟场景用
  toRenderDoc() {
    if (this.beat + 1 !== this.segments.length) throw new Error(`${this.name}: ${this.beat + 1} beats but ${this.segments.length} narration segments`);
    return { elements: this.elements, files: this.files, beatOf: this.beatOf, segments: this.segments };
  }

  // 品牌标：粗体名 + 品牌色圆角下划线（水印/片尾/封面共用母题）。x 为左边，size 字号；返回宽度
  brandMark(x, y, size = 56, o = {}) {
    return this.unit(() => {
      const b = cfg.brand || {}; const name = o.name || b.name || 'Your Brand'; const accent = o.accent || b.accent || C.brand;
      const w = measure(name, size).width;
      this.text(x, y, name, { size, color: o.color || b.ink || C.ink, weight: 800 });
      const uy = y + size * 1.22;
      this.rect(x, uy, w * 0.62, Math.max(6, size * 0.12), { stroke: accent, fill: accent, radius: 4 });
      this.rect(x + w * 0.68, uy + size * 0.04, w * 0.32, Math.max(4, size * 0.07), { stroke: accent, fill: accent, radius: 3, opacity: 70 });
      return w;
    });
  }
  // 封面版式。opts: { ratio:'4:3'|'3:4'|'9:16', title:'两行\n用换行', accent: 高亮第几行(0 起，默认最后一行),
  //   sticker:'贴纸名', tag:'左上标签', sub:'副标', color: 高亮字色 }
  coverLayout(o = {}) {
    const ratio = o.ratio || '4:3';
    const [cw, ch] = coverSize(ratio);
    const portrait = ch > cw;
    const cv = cfg.cover || {};
    const lines = String(o.title || '').split('\n').map((l) => l.trim()).filter(Boolean);
    const accentIdx = o.accent == null ? lines.length - 1 : o.accent;
    const accentColor = o.color || C.brand, hl = o.highlight || C.fOrange;
    const maxLen = Math.max(...lines.map((l) => [...l].reduce((n, ch) => n + (isCJK(ch) ? 1 : 0.55), 0)));
    const tag = o.tag === undefined ? cv.seriesTag : o.tag;
    if (ch / cw > 1.6) {
      // 9:16 长竖版（抖音/快手）：标签 → 标题块 → 贴纸撑中下 → 品牌标贴安全区底
      let y = 270;
      if (tag) { const tw = measure(tag, 44).width + 80; this.chip(cw / 2 - tw / 2, y, tw, 84, tag, { fill: C.fOrange, color: C.orange, size: 44, radius: 42 }); y += 160; }
      const size = Math.min(190, Math.floor((cw - 120) / Math.max(4, maxLen)));
      const lh = size * 1.28;
      y = Math.max(y, 430);
      lines.forEach((l, i) => {
        const w = measure(l, size).width;
        if (i === accentIdx) { this.highlight(cw / 2 - w / 2 - 20, y + i * lh + size * 0.46, w + 40, size * 0.6, { color: hl }); this.rect(cw / 2 - w / 2 - 20, y + i * lh + size * 1.12, w + 40, 12, { stroke: accentColor, fill: accentColor, radius: 6 }); }
        this.text(cw / 2, y + i * lh, l, { size, align: 'center', color: i === accentIdx ? accentColor : C.ink });
      });
      y += lines.length * lh + 34;
      if (o.sub) { this.text(cw / 2, y, o.sub, { size: 48, align: 'center', color: C.gray }); y += 110; }
      const brandY = ch - 240;
      if (o.sticker) {
        const d = this.imageSize(o.sticker), maxW = cw - 160;
        const room = brandY - 50 - y;
        const hCap = Math.min(820, room), h = Math.min(hCap, Math.round(maxW * d.h / d.w));
        this.image(cw / 2, y + 20 + (hCap - h) / 2, o.sticker, { h, align: 'center' });
      }
      const bw = measure(cfg.brand.name || 'Your Brand', 60).width;
      this.brandMark(cw / 2 - bw / 2, brandY, 60);
    } else if (portrait) {
      // 3:4 竖版：标签 → 标题居中 → 贴纸 → 品牌标
      let y = 110;
      if (tag) { const tw = measure(tag, 40).width + 70; this.chip(cw / 2 - tw / 2, y, tw, 74, tag, { fill: C.fOrange, color: C.orange, size: 40, radius: 37 }); y += 130; }
      const size = Math.min(165, Math.floor((cw - 120) / Math.max(4, maxLen)));
      const lh = size * 1.22;
      lines.forEach((l, i) => {
        const w = measure(l, size).width;
        if (i === accentIdx) { this.highlight(cw / 2 - w / 2 - 20, y + i * lh + size * 0.46, w + 40, size * 0.6, { color: hl }); this.rect(cw / 2 - w / 2 - 20, y + i * lh + size * 1.1, w + 40, 11, { stroke: accentColor, fill: accentColor, radius: 5 }); }
        this.text(cw / 2, y + i * lh, l, { size, align: 'center', color: i === accentIdx ? accentColor : C.ink });
      });
      y += lines.length * lh + 20;
      if (o.sub) { this.text(cw / 2, y, o.sub, { size: 44, align: 'center', color: C.gray }); y += 90; }
      const brandY = ch - 150;
      if (o.sticker) {
        const d = this.imageSize(o.sticker), maxW = cw - 180;
        const room = brandY - 40 - y;
        const hCap = Math.min(640, room), h = Math.min(hCap, Math.round(maxW * d.h / d.w));
        this.image(cw / 2, y + 10 + (hCap - h) / 2, o.sticker, { h, align: 'center' });
      }
      const bw = measure(cfg.brand.name || 'Your Brand', 52).width;
      this.brandMark(cw / 2 - bw / 2, brandY, 52);
    } else if (cw / ch < 1.6) {
      // 4:3 偏方横版：标题通栏大字 → 副标 → 贴纸右下 → 品牌标左下
      let y = 96;
      if (tag) { const tw = measure(tag, 40).width + 70; this.chip(110, y, tw, 74, tag, { fill: C.fOrange, color: C.orange, size: 40, radius: 37 }); y += 130; }
      const size = Math.min(Math.round(ch * 0.15), Math.floor((cw - 220) / Math.max(4, maxLen)));
      const lh = size * 1.2;
      const rows = [];
      lines.forEach((l, i) => {
        const w = measure(l, size).width;
        if (i === accentIdx) { this.highlight(110 - 20, y + i * lh + size * 0.46, w + 40, size * 0.6, { color: hl }); this.rect(110 - 20, y + i * lh + size * 1.08, w + 40, 11, { stroke: accentColor, fill: accentColor, radius: 5 }); }
        this.text(110, y + i * lh, l, { size, color: i === accentIdx ? accentColor : C.ink });
        rows.push({ right: 110 + w + 36, bottom: y + i * lh + size * 1.05 });
      });
      y += lines.length * lh + 10;
      if (o.sub) { const w = measure(o.sub, 44).width; this.text(114, y, o.sub, { size: 44, color: C.gray }); rows.push({ right: 114 + w, bottom: y + 50 }); y += 80; }
      if (o.sticker) {
        const asp = (() => { const d = this.imageSize(o.sticker); return d.w / d.h; })();
        const bottom = ch - 70, right = cw - 100;
        let h = Math.round(ch * 0.55);
        for (; h > ch * 0.25; h -= 10) {
          const top = bottom - h, left = right - h * asp;
          if (!rows.some((r) => r.right > left && r.bottom > top)) break;
        }
        this.image(right - (h * asp) / 2, bottom - h, o.sticker, { h, align: 'center' });
      }
      this.brandMark(120, ch - 150, 56);
    } else {
      // 16:9 宽横版：左侧标题，右侧贴纸列（宽 36%），左下品牌标
      const stickerCol = o.sticker ? Math.round(cw * 0.36) : 0;
      const leftW = cw - stickerCol - 220;
      let y = 96;
      if (tag) { const tw = measure(tag, 40).width + 70; this.chip(110, y, tw, 74, tag, { fill: C.fOrange, color: C.orange, size: 40, radius: 37 }); y += 120; }
      const size = Math.min(Math.round(ch * 0.185), Math.floor(leftW / Math.max(4, maxLen)));
      const lh = size * 1.2;
      const blockH = lines.length * lh + (o.sub ? 90 : 0);
      y = Math.max(y, (ch - 160 - y - blockH) / 2 + y - 20);
      lines.forEach((l, i) => {
        const w = measure(l, size).width;
        if (i === accentIdx) { this.highlight(110 - 20, y + i * lh + size * 0.46, w + 40, size * 0.6, { color: hl }); this.rect(110 - 20, y + i * lh + size * 1.08, w + 40, 11, { stroke: accentColor, fill: accentColor, radius: 5 }); }
        this.text(110, y + i * lh, l, { size, color: i === accentIdx ? accentColor : C.ink });
      });
      if (o.sub) this.text(114, y + lines.length * lh + 10, o.sub, { size: 48, color: C.gray });
      if (o.sticker) this.image(cw - stickerCol / 2 - 30, 150, o.sticker, { h: Math.min(Math.round(ch * 0.72), ch - 300), align: 'center' });
      this.brandMark(120, ch - 150, 56);
    }
    return this;
  }

  save(outDir) {
    OUT = outDir; fs.mkdirSync(OUT, { recursive: true });
    const safe = (cfg.captions && cfg.captions.safeTop) || 960;
    const label = (el) => `${el.type}${el.text ? `「${el.text}」` : ''}`;
    if (!this.isCover) for (const el of this.elements) if (el.y + el.height > safe) console.warn(`  ⚠ ${this.name}: ${label(el)} 底边 ${Math.round(el.y + el.height)} 超过字幕安全线 ${safe}`);
    // 品牌水印占位（config.json brand.watermark）：角上 300×130 别放元素
    const wm = cfg.brand && cfg.brand.watermark;
    if (!this.isCover && wm && wm.enabled !== false && cfg.brand.name) {
      const pos = wm.position || 'top-right', zw = 320, zh = 130;
      const zx = pos.endsWith('left') ? 0 : W - zw, zy = pos.startsWith('bottom') ? safe - zh : 0;
      for (const el of this.elements) if (el.x < zx + zw && el.x + el.width > zx && el.y < zy + zh && el.y + el.height > zy) console.warn(`  ⚠ ${this.name}: ${label(el)} 压到${pos}水印区（x ${zx}~${zx + zw}, y ${zy}~${zy + zh}）`);
    }
    if (this.beat + 1 !== this.segments.length) {
      throw new Error(`${this.name}: ${this.beat + 1} beats but ${this.segments.length} narration segments`);
    }
    const doc = {
      type: 'excalidraw', version: 2, source: 'diagram-video-factory', elements: this.elements,
      appState: { viewBackgroundColor: (cfg.render && cfg.render.paper) || C.paper, gridSize: null }, files: this.files,
    };
    // 只出 Obsidian 插件格式：图片不内嵌 base64，走 Embedded Files 引用同目录 png
    const embedded = Object.values(this.files).map((f) => `${f.id}: [[${f.name}]]`).join('\n');
    const mdDoc = { ...doc, files: {} };
    const textEls = this.elements.filter((e) => e.type === 'text').map((e) => `${e.text} ^${e.id}`).join('\n\n');
    const md = `---\n\nexcalidraw-plugin: parsed\ntags: [excalidraw]\n\n---\n==⚠  Switch to EXCALIDRAW VIEW in the MORE OPTIONS menu of this document. ⚠== You can decompress Drawing data with the command palette: 'Decompress current Excalidraw file'. For more info check in plugin settings under 'Saving'\n\n\n# Excalidraw Data\n\n## Text Elements\n${textEls}\n\n${embedded ? `## Embedded Files\n${embedded}\n\n` : ''}%%\n## Drawing\n\`\`\`json\n${JSON.stringify(mdDoc)}\n\`\`\`\n%%`;
    fs.writeFileSync(path.join(OUT, `${this.name}.excalidraw.md`), md);
    return { name: this.name, segments: this.segments, beatOf: this.beatOf };
  }
}

const W = 1920, H = 1080, CX = W / 2, CY = H / 2;

// 把所有场景写到 <期目录>/scenes/，生成 script.json 和 旁白稿.md
function build(projectDir, sceneList, extra = {}) {
  const P = projectPaths(projectDir);
  const meta = sceneList.map((s) => s.save(P.scenes));
  fs.writeFileSync(P.script, JSON.stringify(meta, null, 1));
  // 封面：extra.cover = (s, ratio) => { s.coverLayout({...ratio, ...}) }，每个画幅一张，存 scenes/00-cover-<ratio>.excalidraw.md + cover.json
  const covers = [];
  if (extra.cover) {
    for (const ratio of (cfg.cover && cfg.cover.ratios) || ['4:3', '3:4']) {
      const tag = ratio.replace(':', 'x');
      const s = new Scene(`00-cover-${tag}`, '封面'); s.isCover = true; s.nextBeat();
      extra.cover(s, ratio);
      const [w, h] = coverSize(ratio);
      const m = s.save(P.scenes); covers.push({ ...m, ratio, width: w, height: h });
      for (const f of Object.values(s.files)) fs.copyFileSync(path.join(P.assets, f.name), path.join(P.scenes, f.name));
    }
    fs.writeFileSync(path.join(P.scenes, 'cover.json'), JSON.stringify(covers, null, 1));
  } else if (fs.existsSync(path.join(P.scenes, 'cover.json'))) fs.rmSync(path.join(P.scenes, 'cover.json'));
  // 贴纸 png 复制到 scenes/ 旁边，供 .excalidraw.md 的 Embedded Files 引用
  for (const s of sceneList) for (const f of Object.values(s.files)) fs.copyFileSync(path.join(P.assets, f.name), path.join(P.scenes, f.name));
  writeNote(P, meta);
  console.log(meta.map((s) => `${s.name}: ${s.segments.length} beats, ${s.beatOf.length} elements`).concat(covers.map((c) => `${c.name}: 封面 ${c.width}×${c.height}, ${c.beatOf.length} elements`)).join('\n'));
  return meta;
}

// 旁白稿.md：每期自动生成，含旁白分段、场景链接、时长（配音后才有）、成片
function writeNote(P, meta) {
  const L = [`# ${P.name} · 旁白稿`, '', `> 自动生成（\`dg scenes\` / \`dg build\` 会覆盖），别手改；改旁白去 \`scenes.js\`。`, ''];
  if (fs.existsSync(P.final)) L.push(`成片：[final.mp4](file://${encodeURI(P.final)})（在后台目录，视频不放进期目录）`, '');
  let total = 0;
  for (const s of meta) {
    const a = path.join(P.audio, `${s.name}.json`);
    let dur = '';
    if (fs.existsSync(a)) { const d = JSON.parse(fs.readFileSync(a)).duration; total += d; dur = `（${d.toFixed(0)}s）`; }
    L.push(`## ${s.name}${dur}  [[${s.name}.excalidraw]]`, '');
    s.segments.forEach((seg, i) => L.push(`${i + 1}. ${seg}`));
    L.push('');
  }
  if (total) L.splice(4, 0, `全片旁白约 ${Math.floor(total / 60)}:${String(Math.round(total % 60)).padStart(2, '0')}`, '');
  fs.writeFileSync(P.note, L.join('\n'));
}

// 封面画幅
const COVER_SIZES = { '4:3': [1440, 1080], '3:4': [1080, 1440], '9:16': [1080, 1920], '16:9': [1920, 1080], '1:1': [1080, 1080] };
const coverSize = (ratio) => COVER_SIZES[ratio] || COVER_SIZES['4:3'];

// 片尾品牌卡：粗体名字 + 品牌色下划线 + slogan + CTA 徽章，一个 beat，逐个浮现。由 render.js 在成片末尾追加。
function brandEndCard(brand) {
  const s = new Scene('99-brand', '品牌卡');
  s.nextBeat();
  const accent = brand.accent || C.brand, ink = brand.ink || C.ink;
  let nameW, top = 300, bottom;
  const logo = brand.logo && expandHome(brand.logo);
  if (logo && fs.existsSync(logo)) {
    const el = s.imageFile(CX, 230, logo, { h: 280, align: 'center' });
    nameW = el.width; top = el.y; bottom = el.y + el.height;
  } else {
    const size = 150;
    const t = s.text(CX, top, brand.name, { size, align: 'center', color: ink, weight: 800 });
    nameW = t.width; bottom = t.y + size * 1.1;
  }
  s.rect(CX - nameW / 2 - 10, bottom + 22, nameW + 20, 14, { stroke: accent, fill: accent, radius: 7 });
  if (brand.slogan) s.text(CX, bottom + 90, brand.slogan, { size: 44, align: 'center', color: C.gray, weight: 600 });
  if (brand.endCard && brand.endCard.cta) {
    const y = bottom + 220;
    s.chip(CX - 300, y, 600, 96, brand.endCard.cta, { fill: C.fOrange, stroke: accent, color: ink, size: 38, radius: 48 });
  }
  return s;
}
// os.homedir() 优先：Windows 上 process.env.HOME 可能是 /c/Users/x（MSYS 写法），Node 解析会错。
const expandHome = (p) => { const e = p.replace(/^~/, require('os').homedir() || process.env.HOME || ''); return path.isAbsolute(e) ? e : path.join(__dirname, '..', e); };

module.exports = { Scene, C, W, H, CX, CY, build, writeNote, brandEndCard, wrap, projectDir: null };
// 项目 scenes.js 里 require 后先调用 use(__dirname)，image() 才知道贴纸在哪
module.exports.use = (dir) => { module.exports.projectDir = dir; return module.exports; };
