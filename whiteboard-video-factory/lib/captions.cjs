// 字幕：文本用原文（scenes.js 里的旁白），时间借 TTS 词时间
// （火山/edge 返回逐字原生时间戳；小米没有，是静音检测估出来的句子级时间，见 lib/tts/mi.mjs）。
// 对齐方式：按标点把原文和 TTS 词序列各切成小句，数量一致就一一配对（时间准、文本原样）；
// 不一致则退回按规范化字数累计映射。之后把太短的小句合并、太长的拆开，得到 6~20 字的 cue。
// 每个 cue 再带一组高亮单元 units（{text,start,end}）：语音念到哪个 unit，渲染器就在哪一段上套色块，
// 做出"跟读高亮"的效果（渲染见 render.html 的 updateCaption）。unit 优先用 TTS 词时间，对不上就按字数等比切。
// 供渲染器烧录；并导出期目录 字幕.srt（发平台用）。
// ⚠️SRT 是纯文本格式、装不下高亮：逐段高亮只存在于烧录进画面的那一版。
const fs = require('fs');
const path = require('path');
const { cfg, projectPaths, resolveProject } = require('./paths.cjs');

const CAP = cfg.captions;
const LEAD = cfg.render.leadSeconds, HOLD = cfg.render.holdSeconds;
// ⚠️PUNCT 必须与 lib/tts/mi.mjs 的 clausesOf **逐字一致**：小米通道是"一个小句一条词"，
// 两边切的份数必须相等才能走"数量一致"的精确配对；集合不一致就直接退化成等比估算（字幕时间会飘）。
// 不含顿号：顿号处 TTS 停顿弱且不稳（实测 28 处里 10 处没有停顿），当边界会造出没有锚点的小句，
// 字幕起点只能按字数猜——实测偏早 1.16s。详见 lib/tts/mi.mjs 的 ALIGN_VERSION 注释。
const PUNCT = /[，。？！；：]/;
const HARD = /[。？！；]$/;
const TRIM_END = /[，。；：、]+$/;
const norm = (s) => [...s].filter((c) => /[\p{L}\p{N}]/u.test(c)).join('');
const nlen = (s) => norm(s).length;

// 原文按标点切小句（标点留在句尾）。集合与 PUNCT 一致。
function splitText(text) {
  return text.replace(/\s+/g, ' ').split(/(?<=[，。？！；：])/).map((s) => s.trim()).filter((s) => nlen(s) > 0);
}
// TTS 词按标点切小句
function splitWords(words) {
  const out = []; let buf = [];
  for (const w of words) { buf.push(w); if (PUNCT.test(w.w.slice(-1))) { out.push(buf); buf = []; } }
  if (buf.length) out.push(buf);
  return out.filter((g) => g.some((w) => nlen(w.w) > 0));
}

// ===== 高亮单元（unit）=====
// unit = { text, start, end }，text 是 cue 显示文本里的一段（拼起来必须正好等于 cue.text），
// 时间用 TTS 词时间（还没加 LEAD）。
//
// 粒度参数（config captions.highlight 可覆盖）。unit 太碎，色块每秒跳五次很晃；
// minUnitChars 是"至少几个字"（不足就并给下一段），maxUnitChars 是硬上限（超了按比例再切，见 splitUnit）。
// ⚠️别再按"时长太短就并"来调粒度：实测会把 TTS 的原生词边界冲掉，把 [小米][MiMo] 并成 [米 Mi][Mo 的]，
//   英文单词被拦腰截断。字数是可控的，时长不是——按字数就够。
const DEF_HL = { minUnitChars: 2, maxUnitChars: 4 };
const HL_PARAM = { ...DEF_HL, ...(CAP.highlight || {}) };

// 按字符下标区间 [from,to) 切 unit 列表；边界落在 unit 内部时，按字数比例切它的时间。
function sliceUnits(units, from, to) {
  const out = []; let pos = 0;
  for (const u of units) {
    const chars = [...u.text], n = chars.length, a = pos;
    pos = a + n;
    if (pos <= from || a >= to) continue;
    const i = Math.max(0, from - a), j = Math.min(n, to - a);
    const cut = (k) => u.start + ((u.end - u.start) * k) / n;
    const text = chars.slice(i, j).join('');
    if (text) out.push({ text, start: cut(i), end: cut(j) });
  }
  return out;
}

// 一个 unit 超过 maxChars 字就再切几段（时间按字数比例分）。
// 断点不能随便落在均分位置上：实测会出现 [小米 M]·[iMo] 这种把 MiMo 拦腰截断的色块，很难看。
// 规则：① 绝不切开英文单词/数字；② 尽量不挨着空格（否则色块边缘会多包一个空格）；
//       ③ 每段非空白字尽量凑 3 个；④ 再不行才比谁离均分点近。段内空白不影响计数，渲染时色块会按去空白后的范围量。
function splitUnit(u, p) {
  const chars = [...u.text], n = chars.length;
  if (n <= p.maxUnitChars) return [u];
  const isWord = (c) => /[A-Za-z0-9]/.test(c);
  const cuts = [];
  for (let k = 1, pos = 0; n - pos > p.maxUnitChars; k++) {
    const target = Math.round((n * k) / Math.ceil(n / p.maxUnitChars));
    // cap=true 时还要求这一段不超过 maxChars；不够挑就放宽（宁可长一点，也别把英文单词切开）
    const pick = (cap) => {
      let i0 = -1, key0 = null;
      for (let i = pos + 1; i < n; i++) {
        const ns = chars.slice(pos, i).filter((c) => !/\s/.test(c)).length;
        if (ns < p.minUnitChars) continue;
        if (cap && ns > p.maxUnitChars) break;
        if (chars.slice(i).every((c) => /\s/.test(c))) continue;      // 后面只剩空白，没意义
        const a = chars[i - 1], b = chars[i];
        const key = [isWord(a) && isWord(b) ? 2 : (a === ' ' || b === ' ' ? 1 : 0), Math.abs(ns - 3), Math.abs(i - target)];
        const better = !key0 || key[0] < key0[0]
          || (key[0] === key0[0] && (key[1] < key0[1] || (key[1] === key0[1] && key[2] < key0[2])));
        if (better) { i0 = i; key0 = key; }
      }
      return { i: i0, score: key0 ? key0[0] : 9 };
    };
    let r = pick(true);
    if (r.i <= pos || r.score === 2) r = pick(false);
    if (r.i <= pos || r.score === 2) break;                           // 只剩"切开单词"的断点：整段留着
    cuts.push(r.i); pos = r.i;
  }
  cuts.push(n);
  const out = [];
  let prev = 0;
  for (const c of cuts) {
    const text = chars.slice(prev, c).join('');
    if (text) out.push({ text, start: u.start + ((u.end - u.start) * prev) / n, end: u.start + ((u.end - u.start) * c) / n });
    prev = c;
  }
  return out;
}

// 兜底：没有可用的词时间（或与原文对不上）时，按字数比例把整个 cue 均分
function proportionalUnits(text, start, end) {
  const chars = [...text], n = chars.length;
  if (!n) return [];
  return chars.map((ch, i) => ({ text: ch, start: start + ((end - start) * i) / n, end: start + ((end - start) * (i + 1)) / n }));
}

// 空格不算字数：TTS 词表常带前导/尾随空格（"米 "、" 的"），按含空格的长度算会把 1 个字的段当成 2 个字的段
const nsc = (s) => [...s].filter((c) => !/\s/.test(c)).length;
const isW = (c) => /[A-Za-z0-9]/.test(c);

// 调粒度：先切长的，再按"目标 3 个字"把碎段贪心分组。三条粘的规则（按优先级）：
//   ① 上一段结尾和这一段开头都是字母/数字 → 同一个词被 TTS 切开了（实测火山某次把 MiMo 切成 Mi + Mo），
//      必须粘回去，且不受 maxUnitChars 约束，否则会在字母中间断一刀（[米 MiM]·[o 的配音]）。
//   ② 上一段不够 minUnitChars 字（"小"）→ 补上，凑够下限。
//   ③ 上一段还没到目标长度、且塞得下 → 塞进去。
// 目标取 min/max 的中点（默认 2/4 → 3 个字）。为什么要目标值而不只是"补下限"：火山的词表是**逐字**的
// （"字""幕""也""能"…），只补下限会切出 [用的是小]·[米]·[MiMo]·[的配音] 这种参差的框；
// 按目标 3 字分组得到 [用的是]·[小米]·[MiMo]·[的配音]，跟人念的节奏一致。
function normalizeUnits(units, p) {
  const TARGET = Math.round((p.minUnitChars + p.maxUnitChars) / 2);
  const out = [];
  for (const u of units) for (const s of splitUnit(u, p)) {
    const last = out[out.length - 1];
    const nLast = last ? nsc(last.text) : 0;
    const head = [...s.text][0] || '', tail = [...(last ? last.text : '')].pop() || '';
    const ww = isW(tail) && isW(head);
    const fill = nLast < p.minUnitChars;
    const grow = nLast < TARGET && nLast + nsc(s.text) <= p.maxUnitChars;
    if (last && (ww || fill || grow)) { last.text += s.text; last.end = s.end; }
    else out.push({ ...s });
  }
  // 末尾若剩个过短的碎片（词表尾随的空格、句尾标点很常见），并回上一段，别单独高亮一个空格或一个逗号
  const last = out[out.length - 1];
  if (out.length > 1 && last && nsc(last.text) < p.minUnitChars
    && nsc(out[out.length - 2].text) + nsc(last.text) <= p.maxUnitChars) {
    out[out.length - 2].text += last.text; out[out.length - 2].end = last.end; out.pop();
  }
  return out;
}

// 一个标点小句对应的词 → unit，时间用词的原生时间，**文本取自小句原文**（所以拼起来必然等于原文）。
//
// 为什么不能直接用 w.w 当文本：TTS 词表会吞掉或挪动空格（火山把 "用的是小米 MiMo 的配音" 返回成
// "用的是/小/米/Mi/Mo/..." 这类不带空格的碎片），拿 w.w 拼回去 ≠ 原文，校验就判"对不上"、整条退化成
// 等比估算，英文字母还会被字数上限切成 [米 MiM]·[o 的配音]。按**非空白字符**对齐就没这个问题：
// 只在两边的"实字"序列上走，词与词之间的空白跟着前一段，文本始终是原文切片。
// 对不上（词表被改过、含原文没有的字符）就返回 null，交给上层退化成等比估算。
function wordsToUnits(text, group) {
  const chars = [...text];
  const solid = chars.map((c) => (/\s/.test(c) ? '' : c));
  const out = [];
  let pos = 0;
  for (const w of group) {
    const need = [...String(w.w)].filter((c) => !/\s/.test(c));
    if (!need.length) continue;
    let end = -1;
    for (let i = pos; i < chars.length && need.length; i++) {
      if (!solid[i]) continue;
      if (solid[i] !== need[0]) return null;      // 内容对不上，别硬来
      need.shift(); end = i;
    }
    if (end < 0 || need.length) return null;
    out.push({ text: chars.slice(pos, end + 1).join(''), start: w.s, end: w.e });
    pos = end + 1;
  }
  if (!out.length) return null;
  if (pos < chars.length) out[out.length - 1].text += chars.slice(pos).join('');   // 尾巴上的标点/空白归最后一段
  return out;
}

// 一个场景的 cue 列表（时间为场景内秒，已含 LEAD）
function cuesForScene(info) {
  const words = info.wordList || [];
  if (!words.length) return [];
  const text = (info.segments || []).join('');
  const tc = splitText(text), wc = splitWords(words);
  let clauses;
  if (tc.length === wc.length) {
    clauses = tc.map((t, i) => ({ text: t, start: wc[i][0].s, end: wc[i][wc[i].length - 1].e, units: wordsToUnits(t, wc[i]) }));
  } else {
    // 退回：规范化字数累计映射（词序列按标点切出来的小句数和原文对不上，比如小米只给句子级时间）。
    // 这一路拿不到可靠的词级归属，units 先留空，最后按 cue 文本等比切。
    const pos = []; let acc = 0;
    for (const w of words) { pos.push({ p0: acc, p1: acc + nlen(w.w), s: w.s, e: w.e }); acc += nlen(w.w); }
    const timeAt = (p, useEnd) => { let best = useEnd ? words[words.length - 1].e : words[0].s; for (const x of pos) { if (useEnd ? x.p1 <= p : x.p0 <= p) best = useEnd ? x.e : x.s; else break; } return best; };
    let p = 0; clauses = [];
    for (const t of tc) { const n = nlen(t); clauses.push({ text: t, start: timeAt(p, false), end: timeAt(p + n, true), units: null }); p += n; }
  }
  // 合并短句（软标点后且合并不超长）
  const merged = [];
  for (const c of clauses) {
    const last = merged[merged.length - 1];
    const join = () => { last.text += c.text; last.end = c.end; last.units = last.units && c.units ? last.units.concat(c.units) : null; };
    if (last && !HARD.test(last.text) && nlen(last.text) < CAP.minChars && nlen(last.text) + nlen(c.text) <= CAP.maxChars) join();
    else if (last && !HARD.test(last.text) && nlen(c.text) < 3 && nlen(last.text) + nlen(c.text) <= CAP.maxChars) join();
    else merged.push({ text: c.text, start: c.start, end: c.end, units: c.units ? c.units.map((u) => ({ ...u })) : null });
  }
  // 拆长句：只在汉字之间（或空格处）断，取离等分点最近的位置；时间按字数比例分
  const isCJK = (ch) => /[\u4e00-\u9fff]/.test(ch);
  const cues = [];
  const splitLong = (c) => {
    const n = nlen(c.text);
    if (n <= CAP.maxChars) { cues.push(c); return; }
    const chars = [...c.text];
    // 累计规范化字数 → 字符索引
    const cum = []; let k = 0; for (const ch of chars) { cum.push(k); k += nlen(ch); }
    const ideal = n / Math.ceil(n / CAP.maxChars);
    let best = -1, bestD = Infinity;
    for (let i = 1; i < chars.length; i++) {
      const ok = chars[i] === ' ' || (isCJK(chars[i - 1]) && isCJK(chars[i]));
      if (!ok) continue;
      const d = Math.abs(cum[i] - ideal);
      if (d < bestD) { bestD = d; best = i; }
    }
    if (best < 0) { cues.push(c); return; }
    const rawA = chars.slice(0, best).join(''), rawB = chars.slice(best).join('');
    const a = rawA.trim(), b = rawB.trim();
    const na = nlen(a), t = c.start + (c.end - c.start) * (na / n);
    const head = (s) => s.length - s.replace(/^\s+/, '').length;   // 被 trim 掉的前导空白数
    cues.push({ text: a, start: c.start, end: t, units: c.units ? sliceUnits(c.units, head(rawA), best) : null });
    splitLong({ text: b, start: t, end: c.end, units: c.units ? sliceUnits(c.units, best + head(rawB), chars.length) : null });
  };
  for (const c of merged) splitLong(c);
  // 显示文本去句尾标点；算好 units；加 LEAD
  for (let i = 0; i < cues.length; i++) {
    const raw = cues[i].text, shown = raw.replace(TRIM_END, '');
    if (cues[i].units) {
      const cut = raw.length - shown.length;                       // 被剪掉的尾标点字符数
      const us = cut > 0 ? sliceUnits(cues[i].units, 0, raw.length - cut) : cues[i].units;
      // 校验：unit 文本拼起来必须正好是显示文本。对不上就退回按字数等比——宁可粗一点，不能错位。
      cues[i].units = us.map((u) => u.text).join('') === shown ? us : null;
    }
    cues[i].text = shown;
    if (!cues[i].units || !cues[i].units.length) cues[i].units = proportionalUnits(shown, cues[i].start, cues[i].end);
    cues[i].units = normalizeUnits(cues[i].units, HL_PARAM);
    for (const u of cues[i].units) { u.start += LEAD; u.end += LEAD; }
    cues[i].start += LEAD; cues[i].end += LEAD;
  }
  for (let i = 0; i < cues.length; i++) {
    const prev = cues[i - 1], next = cues[i + 1];
    cues[i].start = Math.max(prev ? prev.end : 0, cues[i].start - CAP.leadSeconds);
    cues[i].end = Math.min(cues[i].end + CAP.tailSeconds, next ? next.start - 0.02 : info.duration + LEAD + HOLD);
    if (next && cues[i].end < cues[i].start + 0.3) cues[i].end = Math.min(cues[i].start + 0.3, next.start);
  }
  return cues.filter((c) => c.text);
}

function sceneInfos(P) {
  const script = JSON.parse(fs.readFileSync(P.script));
  return script.map((sc) => JSON.parse(fs.readFileSync(path.join(P.audio, `${sc.name}.json`))));
}

// 全片 SRT（按场景累计偏移）
function writeSrt(projectDir) {
  const P = projectPaths(projectDir);
  const infos = sceneInfos(P);
  let offset = 0, n = 0; const lines = [];
  const ts = (t) => { const ms = Math.round(t * 1000); const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, s = Math.floor(ms / 1000) % 60; return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms % 1000).padStart(3, '0')}`; };
  for (const info of infos) {
    for (const c of cuesForScene(info)) lines.push(`${++n}\n${ts(offset + c.start)} --> ${ts(offset + c.end)}\n${c.text}\n`);
    offset += info.duration + LEAD + HOLD;
  }
  const out = path.join(P.project, '字幕.srt');
  fs.writeFileSync(out, lines.join('\n'));
  return { file: out, count: n };
}

module.exports = { cuesForScene, writeSrt };

if (require.main === module) {
  const P = projectPaths(resolveProject(process.argv[2] || '.'));
  if (process.argv.includes('--dump')) {
    // [a·b·c] = 这条会依次高亮的三段（点号就是色块跳动的位置），不用看图也能核粒度
    for (const info of sceneInfos(P)) {
      console.log(`## ${info.name}`);
      for (const c of cuesForScene(info)) {
        const hl = c.units && c.units.length ? `  [${c.units.map((u) => u.text).join('·')}]` : '';
        console.log(`  ${c.start.toFixed(2)}-${c.end.toFixed(2)}  ${c.text}${hl}`);
      }
    }
  } else { const r = writeSrt(P.project); console.log(`字幕 ${r.count} 条 → ${r.file}`); }
}
