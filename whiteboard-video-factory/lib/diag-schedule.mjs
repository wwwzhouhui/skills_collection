// 诊断：把 render.html 的排期结果 dump 出来，和旁白 beat 时间对比，量化「画面落后声音」多少秒。
// 用法：node lib/diag-schedule.mjs <projectDir>
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
const require = createRequire(import.meta.url);
const paths = require('./paths.cjs');
const { cfg, projectPaths } = paths;
const { chromium } = require('playwright');
const P = projectPaths(process.argv[2]);
const BRAND = cfg.brand || {};
const LEAD = cfg.render.leadSeconds;

const exe = require('./chromium.cjs').resolveChromium();

function loadDrawing(name) {
  const md = path.join(P.scenes, `${name}.excalidraw.md`);
  const txt = fs.readFileSync(md, 'utf8');
  let doc;
  const m = txt.match(/```json\s*([\s\S]*?)```/);
  const c = txt.match(/```compressed-json\s*([\s\S]*?)```/);
  if (m) doc = JSON.parse(m[1]);
  else { const { decompressFromBase64 } = require('lz-string'); doc = JSON.parse(decompressFromBase64(c[1].replace(/\s+/g, ''))); }
  doc.files = doc.files || {};
  const emb = txt.match(/## Embedded Files\n([\s\S]*?)\n\n/);
  if (emb) for (const line of emb[1].split('\n')) {
    const mm = line.match(/^(\S+):\s*\[\[([^\]|]+)/); if (!mm) continue;
    const fname = path.basename(mm[2]);
    const cand = [path.join(P.scenes, fname), path.join(P.assets, fname)].find((f) => fs.existsSync(f));
    if (cand) doc.files[mm[1]] = { id: mm[1], mimeType: 'image/png', dataURL: 'data:image/png;base64,' + fs.readFileSync(cand).toString('base64') };
  }
  return doc;
}

const browser = await chromium.launch(exe ? { executablePath: exe } : {});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(pathToFileURL(path.join(paths.ROOT, 'lib', 'render.html')).href);
await page.evaluate(() => document.fonts.ready);
// 想对比"改之前"的节奏，用 PEN_OVERRIDE 传一组旧值，例如：
//   PEN_OVERRIDE='{"speed":1000,"overflow":0.35,"minSeconds":0.35,"gapSeconds":0.12,"charSeconds":[0.06,0.2],"fillMaxSeconds":1.2,"fillSpeed":9000}' node lib/diag-schedule.mjs <期目录>
const PEN = { ...(cfg.render.pen || {}), color: BRAND.pen && BRAND.pen.color };
if (process.env.PEN_OVERRIDE) Object.assign(PEN, JSON.parse(process.env.PEN_OVERRIDE));
await page.evaluate((o) => window.setPen(o), PEN);

const script = JSON.parse(fs.readFileSync(P.script));
const report = [];
for (const sc of script) {
  const info = JSON.parse(fs.readFileSync(path.join(P.audio, `${sc.name}.json`)));
  const doc = loadDrawing(sc.name);
  const st = info.segmentStarts, d = info.duration;
  const beats = st.map((t, i) => [t + LEAD, (i + 1 < st.length ? st[i + 1] : d) + LEAD]);
  const total = d + LEAD + cfg.render.holdSeconds;
  await page.evaluate(({ elements, beatOf, beats, files, total }) => {
    window.__els = elements; window.__beatOf = beatOf;
    return window.loadScene(elements, beatOf, beats, files, total);
  }, { elements: doc.elements, beatOf: sc.beatOf, beats, files: doc.files || {}, total });
  const items = await page.evaluate(() => {
    const idx = new Map(window.__els.map((e, i) => [e, i]));
    return items.map((i) => ({
      beat: window.__beatOf[idx.get(i.el)], start: i.start, end: i.end, dur: i.dur, kind: i.kind,
      txt: String((i.el && (i.el.text != null ? i.el.text : i.el.type)) || '').slice(0, 18),
    }));
  });
  report.push({ name: sc.name, duration: d, total, beats, items });
}
await browser.close();

for (const r of report) {
  console.log(`\n## ${r.name}  旁白 ${r.duration.toFixed(1)}s / 场景 ${r.total.toFixed(1)}s`);
  const byBeat = new Map();
  for (const it of r.items) { if (!byBeat.has(it.beat)) byBeat.set(it.beat, []); byBeat.get(it.beat).push(it); }
  for (let b = 0; b < r.beats.length; b++) {
    const list = byBeat.get(b) || [];
    const [t0, t1] = r.beats[b];
    if (!list.length) { console.log(`  beat${b + 1} 旁白 ${t0.toFixed(1)}~${t1.toFixed(1)}  （无元素）`); continue; }
    const s = Math.min(...list.map((i) => i.start)), e = Math.max(...list.map((i) => i.end));
    const sc = list.map((i) => (i.end - i.start) / Math.max(1e-6, i.dur));
    const minSc = Math.min(...sc), avgSc = sc.reduce((a, b) => a + b, 0) / sc.length;
    console.log(`  beat${b + 1} 旁白 ${t0.toFixed(1)}~${t1.toFixed(1)} (${(t1 - t0).toFixed(1)}s, ${list.length}元素)  画 ${s.toFixed(1)}~${e.toFixed(1)}  起笔+${(s - t0).toFixed(2)}s  收笔${(e - t1) >= 0 ? '+' : ''}${(e - t1).toFixed(2)}s  压缩×${minSc.toFixed(2)}~${avgSc.toFixed(2)}`);
  }
}
