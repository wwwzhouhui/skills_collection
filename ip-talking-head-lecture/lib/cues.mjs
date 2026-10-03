// 字幕条切分 —— volc / mi 两条通道的「原文 ↔ 时间戳」对齐规则不同，分开处理：
//   volc：返回**逐字**时间戳 → 按标点 + 目标字数重新切行，每行时间由首末字决定（最准）
//   mi  ：只返回**小句级**时间戳（按 ，。？！；： 切）→ 直接拿小句当字幕条，只做相邻合并
// （mi 若强行按字数细切，会掉进"一行跨两个小句"的坑，时间只能瞎猜，不如老实按小句走）

const CLAUSE_SPLIT = /(?<=[，。？！；：])/;
const VISIBLE = /[\p{L}\p{N}]/u;

const norm = (s) => [...s].filter((c) => VISIBLE.test(c)).join('');

/** 按标点切成小句（标点留在句尾） */
export function clauses(text) {
  return text
    .replace(/\s+/g, ' ')
    .split(CLAUSE_SPLIT)
    .map((s) => s.trim())
    .filter((s) => norm(s).length > 0);
}

/** 把旁白按标点 + 目标字数切成字幕行（用于有逐字时间戳的通道） */
export function splitCaptionLines(text, { maxChars = 20, minChars = 6 } = {}) {
  const cs = clauses(text);
  const lines = [];
  let buf = '';
  const flush = () => {
    if (buf.trim()) lines.push(buf.trim());
    buf = '';
  };
  for (const c of cs) {
    const n = norm(c).length;
    const bufN = norm(buf).length;
    // 单句就超长：先把它塞进去再由后面统一硬切
    if (!buf) {
      buf = c;
    } else if (bufN + n <= maxChars) {
      buf += c;
    } else {
      flush();
      buf = c;
    }
    if (norm(buf).length >= maxChars) flush();
  }
  flush();

  // 过短的与相邻合并（"好的。"这类短句单独一条会闪）
  const merged = [];
  for (const l of lines) {
    const prev = merged[merged.length - 1];
    if (prev && norm(prev).length + norm(l).length <= maxChars && norm(prev).length < minChars) {
      merged[merged.length - 1] = prev + l;
    } else {
      merged.push(l);
    }
  }
  // 仍然超长的：按字数硬切（尽量切在标点上）
  const out = [];
  for (const l of merged) {
    if (norm(l).length <= maxChars * 1.5) {
      out.push(l);
      continue;
    }
    let rest = l;
    while (norm(rest).length > maxChars) {
      const chars = [...rest];
      let cut = maxChars;
      for (let i = Math.min(maxChars, chars.length - 1); i > maxChars * 0.5; i--) {
        if (/[，。？！；：、]/.test(chars[i - 1])) {
          cut = i;
          break;
        }
      }
      out.push(chars.slice(0, cut).join(''));
      rest = chars.slice(cut).join('');
    }
    if (norm(rest).length) out.push(rest);
  }
  return out;
}

/**
 * 把 words 展开成"逐字时间"并对齐到 text 上。
 * words 可能是逐字（volc）也可能是小句级（mi），这里统一展开后再逐字匹配，
 * 匹配不上就向前找几个候选、再不行就顺延，保证**任何情况都不会崩**。
 */
function alignChars(text, words) {
  const flat = [];
  for (const w of words || []) {
    const cs = [...String(w.w ?? '')];
    if (!cs.length) continue;
    const span = (w.e - w.s) / cs.length;
    cs.forEach((ch, i) => flat.push({ ch, s: w.s + span * i, e: w.s + span * (i + 1) }));
  }
  const chars = [...text];
  const res = new Array(chars.length).fill(null);
  let k = 0;
  for (let i = 0; i < chars.length; i++) {
    const c = chars[i];
    if (!VISIBLE.test(c)) continue;
    let found = -1;
    for (let j = k; j < Math.min(flat.length, k + 4); j++) {
      if (flat[j].ch === c) {
        found = j;
        break;
      }
    }
    if (found < 0 && k < flat.length) found = k;
    if (found < 0) break;
    res[i] = { s: flat[found].s, e: flat[found].e };
    k = found + 1;
  }
  let last = null;
  for (let i = 0; i < chars.length; i++) {
    if (res[i]) last = res[i];
    else if (last) res[i] = { s: last.e, e: last.e };
  }
  return res;
}

/** words 是逐字还是小句级？看平均词长 */
export function wordGranularity(words) {
  if (!words || !words.length) return 'none';
  const avg = words.reduce((a, w) => a + [...String(w.w ?? '')].length, 0) / words.length;
  return avg <= 1.6 ? 'char' : 'clause';
}

/**
 * 生成字幕条 cues。返回 [{text, start, end}]，时间都是**场景内相对秒**。
 */
export function buildCues(text, words, opts = {}) {
  const { maxChars = 20, minChars = 6 } = opts;
  const gran = wordGranularity(words);

  if (gran === 'none') {
    return [{ text, start: 0, end: 0 }];
  }

  if (gran === 'clause') {
    // 小句级：以 words 为准，相邻合并到目标字数
    const out = [];
    for (const w of words) {
      const t = String(w.w ?? '').trim();
      if (!t) continue;
      const prev = out[out.length - 1];
      if (prev && norm(prev.text).length + norm(t).length <= maxChars && norm(prev.text).length < minChars) {
        prev.text += t;
        prev.end = w.e;
      } else {
        out.push({ text: t, start: w.s, end: w.e });
      }
    }
    if (!out.length) return [{ text, start: 0, end: 0 }];
    return out;
  }

  // 逐字级：按目标字数切行，再用首末字的时间定界
  const lines = splitCaptionLines(text, { maxChars, minChars });
  const times = alignChars(text, words);
  const cues = [];
  let cursor = 0;
  for (const line of lines) {
    // 在原文里找到这一行（允许中间的空白差异）
    let startIdx = -1;
    let endIdx = -1;
    let li = 0;
    for (let i = cursor; i < text.length && li < line.length; i++) {
      if (!VISIBLE.test(line[li]) && line[li] !== text[i]) {
        li++;
        continue;
      }
      if (line[li] === text[i]) {
        if (li === 0) startIdx = i;
        li++;
        endIdx = i;
      } else if (VISIBLE.test(line[li])) {
        // 对不上（旁白与字幕行不同源）：跳过这个字继续找
        li++;
        i--;
      }
    }
    if (startIdx < 0) {
      startIdx = cursor;
      endIdx = Math.min(text.length - 1, cursor + line.length - 1);
    }
    const slice = times.slice(startIdx, endIdx + 1).filter(Boolean);
    const s = slice.length ? slice[0].s : cues.length ? cues[cues.length - 1].end : 0;
    const e = slice.length ? slice[slice.length - 1].e : s + 1.2;
    cues.push({ text: line, start: +s.toFixed(3), end: +Math.max(e, s + 0.2).toFixed(3) });
    cursor = endIdx + 1;
  }
  if (!cues.length) return [{ text, start: 0, end: words[words.length - 1].e }];
  return cues;
}

/** 把场景数组摊平成「整片时间」的字幕条目（时间 = 场景起点 + 场景内相对时间） */
export function flattenCues(scenes) {
  const out = [];
  for (const sc of scenes) {
    for (const c of sc.cues || []) {
      out.push({ start: sc.start + c.start, end: sc.start + c.end, text: c.text });
    }
  }
  return out;
}

const pad = (n, w = 2) => String(n).padStart(w, '0');

function fmtTime(sec, sep) {
  const t = Math.max(0, sec);
  const h = Math.floor(t / 3600);
  const m = Math.floor((t % 3600) / 60);
  const s = Math.floor(t % 60);
  const ms = Math.round((t - Math.floor(t)) * 1000);
  // 四舍五入到 1000ms 时进位（否则会写出 00:00:03,1000 这种非法时间码）
  const carry = ms >= 1000 ? 1 : 0;
  return `${pad(h)}:${pad(m)}:${pad(s + carry)}${sep}${pad(carry ? 0 : ms, 3)}`;
}

/**
 * 生成 SRT 文本。
 *   scenes 来自 timeline（cue 的时间是场景内相对秒）
 *   texts  可选：按**整片顺序**逐条替换字幕文本 —— 中英双语字幕就靠它复用同一条时间轴。
 *          条数不必相等；多出来的条目忽略，缺的位置沿用原文。
 */
export function toSrt(scenes, texts) {
  const items = flattenCues(scenes);
  return items
    .map((it, i) => {
      const text = texts && texts[i] !== undefined ? texts[i] : it.text;
      return `${i + 1}\n${fmtTime(it.start, ',')} --> ${fmtTime(it.end, ',')}\n${text}\n`;
    })
    .join('\n');
}

/**
 * 生成 WebVTT 文本。YouTube 上传字幕更推荐 VTT：
 * 结构与 SRT 相同，但①首行必须是 WEBVTT ②时间码的小数点用 `.` 而不是 `,` ③序号可省略。
 */
export function toVtt(scenes, texts) {
  const items = flattenCues(scenes);
  const body = items
    .map((it, i) => {
      const text = texts && texts[i] !== undefined ? texts[i] : it.text;
      return `${i + 1}\n${fmtTime(it.start, '.')} --> ${fmtTime(it.end, '.')}\n${text}\n`;
    })
    .join('\n');
  return `WEBVTT\n\n${body}`;
}
