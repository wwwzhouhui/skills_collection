// 诊断：字幕（字幕.srt / cuesForScene）与真实语音的对齐度。
// 用 ffmpeg silencedetect 取每段旁白的"有声区间"，再逐条字幕算覆盖率与边界偏移。
// 用法：node lib/diag-captions.mjs <projectDir>
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { cfg, projectPaths } = require('./paths.cjs');
const { cuesForScene } = require('./captions.cjs');

const P = projectPaths(process.argv[2]);
const script = JSON.parse(fs.readFileSync(P.script));

// ffmpeg silencedetect → 有声区间 [start,end]
function speechRanges(wav) {
  // ⚠️silencedetect 的输出走 stderr，只读 stdout 会拿到空串（会误判成"整段都在说话"）
  const r0 = spawnSync('ffmpeg', ['-hide_banner', '-i', wav, '-af', 'silencedetect=noise=-35dB:d=0.10', '-f', 'null', '-'], { encoding: 'utf8' });
  const out = (r0.stderr || '') + (r0.stdout || '');
  const ev = [];
  for (const line of out.split('\n')) {
    let m = line.match(/silence_start:\s*(-?[\d.]+)/); if (m) ev.push({ t: +m[1], k: 's' });
    m = line.match(/silence_end:\s*([\d.]+)/); if (m) ev.push({ t: +m[1], k: 'e' });
  }
  const dur = +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', wav], { encoding: 'utf8' }).trim();
  const r = []; let cur = 0;
  for (const e of ev) { if (e.k === 's') { if (e.t > cur) r.push([cur, e.t]); cur = e.t; } else cur = e.t; }
  if (cur < dur) r.push([cur, dur]);
  return { ranges: r, dur };
}
const overlap = (a, b, rs) => rs.reduce((s, [x, y]) => s + Math.max(0, Math.min(b, y) - Math.max(a, x)), 0);
// 最近的语音起点（用于看"字幕是不是比声音早/晚出现"）
const nearestOnset = (t, rs) => rs.map(([x]) => x).reduce((best, x) => (Math.abs(x - t) < Math.abs(best - t) ? x : best), rs.length ? rs[0][0] : t);

const LEAD = cfg.render.leadSeconds;
let all = [], offs = [];
console.log('场景            条数  覆盖率   起笔偏移(中位/最大)  边界落在静音里的条数');
for (const sc of script) {
  const info = JSON.parse(fs.readFileSync(path.join(P.audio, `${sc.name}.json`)));
  const { ranges } = speechRanges(path.join(P.audio, `${sc.name}.wav`));
  const cues = cuesForScene(info);
  let cov = 0, tot = 0, bad = 0; const off = [];
  for (const c of cues) {
    const a = c.start - LEAD, b = c.end - LEAD;          // cues 含 LEAD，音频没有
    tot += b - a; cov += overlap(a, b, ranges);
    const o = c.start - LEAD - nearestOnset(a, ranges);  // 字幕起点相对最近语音起点
    off.push(o); offs.push(o);
    if (Math.abs(o) > 0.35) console.log(`    ⚠ ${o >= 0 ? '+' : ''}${o.toFixed(2)}s  ${c.start.toFixed(2)}-${c.end.toFixed(2)}  ${c.text}`);
    // 边界是否落在静音里：字幕区间内"非重叠"时长占比 > 40% 视为错位
    if ((b - a - overlap(a, b, ranges)) / (b - a) > 0.4) bad++;
  }
  const med = off.slice().sort((x, y) => x - y)[Math.floor(off.length / 2)] || 0;
  const mx = off.reduce((m, x) => Math.max(m, Math.abs(x)), 0);
  all.push(cues.length);
  console.log(`${sc.name.padEnd(14)} ${String(cues.length).padStart(4)}  ${(100 * cov / tot).toFixed(1)}%   ${med >= 0 ? '+' : ''}${med.toFixed(2)}s / ${mx.toFixed(2)}s       ${bad}`);
}
const allMed = offs.slice().sort((a, b) => a - b)[Math.floor(offs.length / 2)];
console.log(`\n全片 ${all.reduce((a, b) => a + b, 0)} 条字幕；起点偏移中位数 ${allMed >= 0 ? '+' : ''}${allMed.toFixed(2)}s`);
