// Remotion 渲染器。
//   node lib/render.mjs <期> [--ratio=16:9,9:16] [--scene=N] [--still=秒]
//
// 每个画幅渲染前，把该画幅的 timeline.json 覆盖写进工程（Root.tsx 读它当默认 props），
// 于是同一个 React 工程能出多种画幅，且脚本/配音改了不用动任何组件代码。
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { run } from './tts/run.mjs';

const require = createRequire(import.meta.url);
const paths = require('./paths.cjs');
const { cfg, ROOT, projectPaths, resolveProject } = paths;

const argv = process.argv.slice(2);
const flags = {};
const positional = [];
for (const a of argv) {
  const m = /^--([^=]+)(?:=(.*))?$/.exec(a);
  if (m) flags[m[1]] = m[2] ?? true;
  else positional.push(a);
}
const P = projectPaths(resolveProject(positional[0]));

const REMOTION = path.join(ROOT, 'remotion');
const CLI = path.join(REMOTION, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');
const GEN = path.join(REMOTION, 'src', 'generated', 'timeline.json');
const ENTRY = 'src/index.ts';
const COMP = 'IpLecture';

if (!fs.existsSync(CLI)) {
  throw new Error(`Remotion 还没装：${CLI}\n  在 ${REMOTION} 里跑 npm install（或从别的 Remotion 工程拷一份 node_modules）`);
}

const video = { ...cfg.video };

// ── 找可用的 Chromium ────────────────────────────────────────────────
// Remotion 首次渲染会自动下载 chrome-headless-shell；若下载被网络拦，
// 就用本机 Playwright 已装好的那份（同源、版本兼容）。
function findBrowser() {
  const bases = [
    path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright'),
    path.join(os.homedir(), 'Library', 'Caches', 'ms-playwright'),
    path.join(os.homedir(), '.cache', 'ms-playwright'),
  ];
  const hits = [];
  for (const base of bases) {
    if (!fs.existsSync(base)) continue;
    for (const d of fs.readdirSync(base)) {
      if (!d.startsWith('chromium')) continue;
      for (const rel of [
        ['chrome-headless-shell-win64', 'chrome-headless-shell.exe'],
        ['chrome-headless-shell-linux64', 'chrome-headless-shell'],
        ['chrome-headless-shell-mac-arm64', 'chrome-headless-shell'],
        ['chrome-headless-shell-mac-x64', 'chrome-headless-shell'],
        ['chrome-win', 'chrome.exe'],
        ['chrome-linux', 'chrome'],
      ]) {
        const p = path.join(base, d, ...rel);
        if (fs.existsSync(p)) hits.push(p);
      }
    }
  }
  return hits.sort().pop() || '';
}
const BROWSER = process.env.REMOTION_BROWSER || findBrowser();

// ── 画幅清单 ─────────────────────────────────────────────────────────
const ratios = String(flags.ratio || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
const list = ratios.length
  ? ratios
  : (cfg.video.ratios || ['16:9']).filter((r) => fs.existsSync(path.join(P.work, `timeline-${r.replace(':', 'x')}.json`)));

if (!list.length) throw new Error('没有可渲染的时间轴，先跑：node lib/build.mjs <期>');

const isStill = flags.still !== undefined;
const onlyScene = flags.scene !== undefined ? Number(flags.scene) : null;

async function renderOne(ratio, { still, scene }) {
  const tlFile = path.join(P.work, `timeline-${ratio.replace(':', 'x')}.json`);
  if (!fs.existsSync(tlFile)) throw new Error(`缺时间轴 ${tlFile}（先 build）`);
  const tl = JSON.parse(fs.readFileSync(tlFile, 'utf8'));
  fs.writeFileSync(GEN, JSON.stringify(tl, null, 2), 'utf8');

  const common = [
    CLI,
    still ? 'still' : 'render',
    ENTRY,
    COMP,
  ];

  if (still) {
    // 支持一次出多张：--still=1.5,12,25,40（逗号分隔秒数）
    const secs = String(still)
      .split(',')
      .map((s) => Number(s.trim()))
      .filter((n) => Number.isFinite(n));
    const outs = [];
    for (const sec of secs.length ? secs : [1]) {
      const frame = Math.max(0, Math.round(sec * tl.fps));
      const out = path.join(P.out, `still-${ratio.replace(':', 'x')}-${frame}.png`);
      fs.mkdirSync(P.out, { recursive: true });
      const args = [...common, out, `--frame=${frame}`, '--log=warn', '--overwrite'];
      if (BROWSER) args.push(`--browser-executable=${BROWSER}`);
      console.log(`\n[render] 静帧 ${ratio} @${sec}s (frame ${frame})`);
      const r = await run(process.execPath, args, { cwd: REMOTION, stdio: 'inherit' });
      if (r.code !== 0) throw new Error(`静帧失败（退出码 ${r.code}）`);
      console.log(`[render] ✓ ${out}`);
      outs.push(out);
    }
    return outs;
  }

  const out = path.join(P.studio, 'outputs', `final-${ratio.replace(':', 'x')}.mp4`);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const args = [
    ...common,
    out,
    `--concurrency=${video.concurrency || 4}`,
    `--crf=${video.crf ?? 18}`,
    '--codec=h264',
    '--audio-codec=aac',
    '--log=info',
    '--overwrite',
  ];
  if (scene !== null && Number.isFinite(scene)) args.push(`--frames=${sceneRange(tl, scene)}`);
  if (BROWSER) args.push(`--browser-executable=${BROWSER}`);

  console.log(`\n[render] ${ratio} → ${out}`);
  console.log(`[render] ${path.basename(CLI)} · concurrency=${video.concurrency} · crf=${video.crf}`);
  const t0 = Date.now();
  const r = await run(process.execPath, args, { cwd: REMOTION, stdio: 'inherit' });
  if (r.code !== 0) {
    throw new Error(
      `渲染失败（退出码 ${r.code}）。常见原因：\n` +
        `  · Chromium 拉不起来 → 手动指定：REMOTION_BROWSER=<chrome路径>\n` +
        `  · 缺字体 → 装一套中文字体（HarmonyOS Sans SC / MiSans / 思源黑体）\n` +
        `  · 内存不够 → 把 config.video.concurrency 降到 2`,
    );
  }
  const secs = ((Date.now() - t0) / 1000).toFixed(0);
  const size = (fs.statSync(out).size / 1024 / 1024).toFixed(1);
  console.log(`[render] ✓ ${out}  ${size}MB  ${secs}s`);
  return out;
}

/** 只渲染某一个场景（快速看版式）：算出该场景的帧区间 */
function sceneRange(tl, n) {
  const sc = tl.scenes[n];
  if (!sc) throw new Error(`没有第 ${n} 个场景（共 ${tl.scenes.length} 个，下标从 0 起）`);
  const from = Math.round(sc.start * tl.fps);
  const to = Math.round((sc.start + sc.duration) * tl.fps) - 1;
  return `${from}-${to}`;
}

const outs = [];
for (const ratio of list) {
  outs.push(await renderOne(ratio, { still: flags.still !== undefined ? flags.still || 1 : null, scene: onlyScene }));
}
console.log(`\n[done] ${outs.length} 个产物：`);
for (const o of outs) console.log(`  ${o}`);
