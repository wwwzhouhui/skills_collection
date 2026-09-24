// 从分镜自动生成 .srt 字幕（严格等于画面显示文字）
// 用法:
//   node make_srt.mjs <scenes.json> <out.srt> [--eff=<slug>.effective.json] [--timing=timing.json] [--total=15]
//
// 时间轴取值优先级：
//   1) --timing=timing.json   （有声版：按语音逐幕对齐，start/dur 来自 TTS）
//   2) --eff=<...>.effective.json（build_html.mjs 自动产出的“生效分镜”，含缩放后的真实 dur/start）
//   3) scenes.json 自身的 dur 累加（可再传 --total=N 做与 build 一致的比例归一）
//
// 文案取值：每幕若有 "srt" 字段则原样使用（字符串用 \n 分行，或数组）；否则按 type 自动抽取画面文字。
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, resolve } from "node:path";

const argv = process.argv.slice(2);
const positional = argv.filter(a => !a.startsWith("--"));
const opt = Object.fromEntries(argv.filter(a => a.startsWith("--")).map(a => {
  const [k, v] = a.replace(/^--/, "").split("=");
  return [k, v === undefined ? true : v];
}));

const [srcPath, outPath] = positional;
if (!srcPath || !outPath) {
  console.error("用法: node make_srt.mjs <scenes.json> <out.srt> [--eff=<slug>.effective.json] [--timing=timing.json] [--total=15]");
  process.exit(1);
}

const data = JSON.parse(readFileSync(resolve(srcPath), "utf8"));
const scenes = data.scenes || [];

// ── 时间轴 ────────────────────────────────────────────────
let timing = null;
if (opt.timing) {
  const t = JSON.parse(readFileSync(resolve(opt.timing), "utf8"));
  timing = t.timing || null;
  if (!timing) console.warn(`[srt] ⚠️ ${opt.timing} 里没有 timing 数组，改用分镜 dur`);
}

let eff = null;
if (opt.eff && existsSync(resolve(opt.eff))) {
  eff = JSON.parse(readFileSync(resolve(opt.eff), "utf8"));
  if (eff.scenes && eff.scenes.length !== scenes.length) {
    console.warn(`[srt] ⚠️ 生效分镜 ${eff.scenes.length} 幕 ≠ 分镜源 ${scenes.length} 幕，已忽略 --eff`);
    eff = null;
  }
}

// 兜底：按 dur 累加（与 build_html.mjs 相同的比例归一算法）
let durs = scenes.map(s => Number(s.dur) || 5);
const rawTarget = opt.total !== undefined ? Number(opt.total) : (data.duration !== undefined ? Number(data.duration) : null);
const MIN_DUR = 0.6;
if (rawTarget !== null && Number.isFinite(rawTarget) && rawTarget > 0) {
  const sum = durs.reduce((a, b) => a + b, 0);
  if (Math.abs(sum - rawTarget) > 0.05) {
    const scale = rawTarget / sum;
    let acc = 0;
    durs = durs.map((d, i) => {
      const nd = i === durs.length - 1 ? Number((rawTarget - acc).toFixed(2)) : Number((d * scale).toFixed(2));
      const v = Math.max(MIN_DUR, nd); acc += v; return v;
    });
    const drift = Number((rawTarget - acc).toFixed(2));
    if (drift !== 0) durs[durs.length - 1] = Number((durs[durs.length - 1] + drift).toFixed(2));
    console.log(`[srt] 时长归一：${sum.toFixed(2)}s → ${rawTarget}s`);
  }
}

// ── 每幕文案 ──────────────────────────────────────────────
function stripTags(s) {
  return String(s)
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/(div|p|h[1-6]|li|tr|section)>/gi, "\n")
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/gi, " ").replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<").replace(/&gt;/gi, ">").replace(/&quot;/gi, '"')
    .split("\n").map(x => x.replace(/[ \t\u3000]+/g, " ").trim()).filter(Boolean);
}

function freeToLines(html) {
  const raw = String(html || "");
  const head = raw.match(/<h[1-6][^>]*class="h"[^>]*>([\s\S]*?)<\/h[1-6]>/i);
  const cts = [...raw.matchAll(/class="ct"[^>]*>([\s\S]*?)<\/div>/gi)].map(m => stripTags(m[1]).join(" "));
  const cds = [...raw.matchAll(/class="cd"[^>]*>([\s\S]*?)<\/div>/gi)].map(m => stripTags(m[1]));
  if (cts.length) {
    const out = [];
    if (head) out.push(stripTags(head[1]).join(" "));
    cts.forEach((ct, i) => {
      const d = (cds[i] || [])[0] || "";
      out.push(d ? `${ct}：${d}` : ct);
    });
    return out.filter(Boolean);
  }
  return stripTags(raw);
}

function linesFromScene(sc) {
  // 1) 显式覆盖：字符串（\n 分行）或数组
  if (sc.srt !== undefined && sc.srt !== null) {
    const v = sc.srt;
    if (Array.isArray(v)) return v.map(String).map(s => s.trim()).filter(Boolean);
    return String(v).split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  }
  const out = [];
  const p = s => { if (s !== undefined && s !== null && String(s).trim()) out.push(String(s).trim()); };
  switch (sc.type) {
    case "title":      p(sc.brand); p(sc.title); p(sc.sub); break;
    case "end":        p(sc.brand); p(sc.title); p(sc.sub); break; // cta 是按钮文案，默认不入字幕；需要时用 "srt" 覆盖
    case "bigword":    p(sc.eyebrow); p(sc.word); p(sc.note); break;
    case "typewriter": p(sc.head); p(sc.text); p(sc.note); break;
    case "quote":      p(sc.text); p(sc.by); break;
    case "flow":
      p(sc.head);
      (sc.steps || []).forEach((s, i) => p(`${i + 1}. ${s.t}${s.d ? "：" + s.d : ""}`));
      break;
    case "points":
      p(sc.head);
      (sc.items || []).forEach(it => p(`${it.t}${it.d ? "：" + it.d : ""}`));
      break;
    case "bars":
      p(sc.head);
      (sc.items || []).forEach(it => p(`${it.label} ${it.v}${it.suffix || ""}`));
      break;
    case "free":
      return freeToLines(sc.html || "");
    default:
      p(sc.head); p(sc.title); p(sc.text); p(sc.brand); p(sc.sub);
  }
  return out;
}

// ── 组装 ──────────────────────────────────────────────────
function fmt(t) {
  const ms = Math.max(0, Math.round(t * 1000));
  const h = Math.floor(ms / 3600000), m = Math.floor(ms % 3600000 / 60000), s = Math.floor(ms % 60000 / 1000), z = ms % 1000;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")},${String(z).padStart(3, "0")}`;
}

const cues = [];
let cursor = 0;
for (let i = 0; i < scenes.length; i++) {
  let start, dur;
  if (timing && timing[i]) { start = Number(timing[i].start) || 0; dur = Number(timing[i].dur) || 0; }
  else if (eff && eff.scenes[i]) { start = Number(eff.scenes[i].start) || 0; dur = Number(eff.scenes[i].dur) || 0; }
  else { start = cursor; dur = durs[i]; }
  cursor = start + dur;

  const lines = linesFromScene(scenes[i]);
  if (!lines.length) { console.warn(`[srt] ⚠️ 第 ${i + 1} 幕（${scenes[i].type}）无可用文字，已跳过`); continue; }
  cues.push({ start, end: start + dur, lines });
}

// 末条时间码吸附到总时长，避免浮点尾巴
if (cues.length) {
  let total = timing ? Math.max(...timing.map(t => (Number(t.start) || 0) + (Number(t.dur) || 0)))
    : eff ? Number(eff.total)
    : durs.reduce((a, b) => a + b, 0);
  total = Number(total.toFixed(3));
  cues[cues.length - 1].end = Math.max(cues[cues.length - 1].start + 0.2, total);
}

const srt = cues.map((c, i) => `${i + 1}\n${fmt(c.start)} --> ${fmt(c.end)}\n${c.lines.join("\n")}\n`).join("\n");
mkdirSync(dirname(resolve(outPath)), { recursive: true });
writeFileSync(resolve(outPath), srt, "utf8");

console.log(`[srt] 来源 ${resolve(srcPath)}${timing ? " + timing" : eff ? " + effective" : ""}`);
console.log(`[srt] ${cues.length} 条字幕 / 末条结束 ${fmt(cues.length ? cues[cues.length - 1].end : 0)}`);
console.log(`[srt] → ${resolve(outPath)}`);
