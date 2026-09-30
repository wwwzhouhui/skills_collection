// 渲染：把每个场景按帧截图喂给 ffmpeg，和旁白合成，最后串成 out/master.mp4（无 BGM）。
// 用法：node lib/render.js <projectDir>            渲染全部
//       node lib/render.js <projectDir> --stills   只导出每个 beat 结束时的静帧到 frames/（检查排版）
//       node lib/render.js <projectDir> 03-xxx     只渲染指定场景
//       node lib/render.js <projectDir> --clean    出片后清中间产物：frames/ 静帧、out/ 里已不在场景表的旧分段
// 并行：seek(t) 每帧整屏重画、只由 t 决定，所以开 render.workers 路（各一个 Chromium）交错出帧（第 k 路出 k, k+N, k+2N…），
// 主进程按帧号顺序喂 ffmpeg；截图参数不变，workers=1 与 workers=4 出的帧逐字节一致。
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const { cfg, projectPaths } = require('./paths.cjs');
const { cuesForScene, writeSrt } = require('./captions.cjs');
const { brandEndCard } = require('./scene-dsl');
const LIB = __dirname;
const args = process.argv.slice(2);
const P = projectPaths(args[0] || '.');
const stills = args.includes('--stills');
const coverMode = args.includes('--cover');
const cleanMode = args.includes('--clean');
const only = args.slice(1).filter((a) => !a.startsWith('--'));
const FPS = cfg.render.fps, HOLD = cfg.render.holdSeconds, LEAD = cfg.render.leadSeconds;
const WORKERS = Math.max(1, Number(cfg.render.workers) || 1);
const BRAND = cfg.brand || {};
// 字幕高亮配色：config 里 captions.highlight.color 留空就用品牌色，改一处全片生效
const CAP_STYLE = (() => {
  const h = cfg.captions.highlight;
  return { ...cfg.captions, highlight: h && h.enabled !== false ? { ...h, color: h.color || BRAND.accent || '#2f9e44' } : null };
})();
// 跨平台家目录：os.homedir() 优先。Windows 上 process.env.HOME 常是 Git Bash 的 MSYS 路径（/c/Users/x），
// Node 会当成当前盘符下的 \c\Users\x → 一律以 os.homedir() 为准（与 paths.cjs / scene-dsl.js 一致）。
const expand = (p) => { const e = p.replace(/^~/, require('os').homedir() || process.env.HOME || ''); return path.isAbsolute(e) ? e : path.join(__dirname, '..', e); };

// 传给页面的品牌数据：logo 读成 dataURL（可选）
function brandPayload() {
  const b = { name: BRAND.name || '', accent: BRAND.accent, ink: BRAND.ink, watermark: BRAND.watermark || { enabled: false }, logo: '' };
  if (BRAND.logo) {
    const f = expand(BRAND.logo);
    if (!fs.existsSync(f)) throw new Error(`brand.logo 不存在：${f}`);
    const buf = fs.readFileSync(f);
    b.logo = 'data:image/png;base64,' + buf.toString('base64');
    b.logoAspect = buf.readUInt32BE(16) / buf.readUInt32BE(20);
  }
  return b;
}

// 优先读 Obsidian 插件格式 .excalidraw.md（从 ```json 块或压缩块里取 JSON），否则读裸 .excalidraw
function loadDrawing(name) {
  const md = path.join(P.scenes, `${name}.excalidraw.md`);
  if (fs.existsSync(md)) {
    const txt = fs.readFileSync(md, 'utf8');
    let doc;
    const m = txt.match(/```json\s*([\s\S]*?)```/);
    const c = txt.match(/```compressed-json\s*([\s\S]*?)```/);
    if (m) doc = JSON.parse(m[1]);
    else if (c) { const { decompressFromBase64 } = require('lz-string'); doc = JSON.parse(decompressFromBase64(c[1].replace(/\s+/g, ''))); }
    else throw new Error(`${name}.excalidraw.md 里没找到 Drawing JSON`);
    // Embedded Files: "<fileId>: [[xxx.png]]" → 从 scenes/ 或 assets/ 读 png
    doc.files = doc.files || {};
    const emb = txt.match(/## Embedded Files\n([\s\S]*?)\n\n/);
    if (emb) for (const line of emb[1].split('\n')) {
      const mm = line.match(/^(\S+):\s*\[\[([^\]|]+)/); if (!mm) continue;
      const fname = path.basename(mm[2]);
      const cand = [path.join(P.scenes, fname), path.join(P.assets, fname)].find((f) => fs.existsSync(f));
      if (!cand) throw new Error(`找不到嵌入图片 ${fname}`);
      doc.files[mm[1]] = { id: mm[1], mimeType: 'image/png', dataURL: 'data:image/png;base64,' + fs.readFileSync(cand).toString('base64') };
    }
    return doc;
  }
  throw new Error(`缺少 scenes/${name}.excalidraw.md，先跑 wb scenes`);
}

// 旁白时间信息：有音频就用真实时长；没有（还没跑 tts）就按 286 字/分估算，只供 --stills 检查排版
function infoFor(sc) {
  const f = path.join(P.audio, `${sc.name}.json`);
  if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f));
  if (!stills) throw new Error(`缺少 audio/${sc.name}.json，先跑 wb tts`);
  const cps = (286 / 60) * Number(cfg.tts.speed || 1), starts = []; let t = 0;
  for (const seg of sc.segments) { starts.push(t); t += [...seg].filter((c) => /[\p{L}\p{N}]/u.test(c)).length / cps + 0.4; }
  return { duration: t, segmentStarts: starts, estimated: true };
}

function beatsFor(info) {
  const st = info.segmentStarts, d = info.duration;
  return st.map((t, i) => [t + LEAD, (i + 1 < st.length ? st[i + 1] : d) + LEAD]);
}

function run(cmd, argv) {
  return new Promise((res, rej) => {
    const c = spawn(cmd, argv, { stdio: 'inherit' });
    c.on('close', (code) => (code === 0 ? res() : rej(new Error(`${cmd} exit ${code}`))));
  });
}

const CHROMIUM = require('./chromium.cjs').resolveChromium(cfg.render.chromium ? expand(cfg.render.chromium) : null);
if (CHROMIUM) console.log(`（Chromium: ${CHROMIUM}）`);

// 一个 worker = 一个 Chromium + 一个页面。同一个浏览器里多开页面，截图会卡在浏览器主进程（实测 4 页也只有约 113 帧/秒），
// 各开各的浏览器才真正并行（4 路约 180 帧/秒）
async function openPage() {
  const browser = await chromium.launch(CHROMIUM ? { executablePath: CHROMIUM } : {});
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(require('url').pathToFileURL(path.join(LIB, 'render.html')).href);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.evaluate((o) => window.setPen(o), { ...(cfg.render.pen || {}), color: BRAND.pen && BRAND.pen.color });
  return { browser, page };
}

async function shot(page, t) {
  await page.evaluate((t) => window.seek(t), t);
  for (let tries = 0; ; ) {
    try { return await page.screenshot({ type: 'jpeg', quality: 92, timeout: 20000 }); }
    catch (e) { if (++tries >= 3) throw e; console.warn(`\n  截图重试 ${tries}: ${e.message.split('\n')[0]}`); }
  }
}

// 各页交错出帧，按帧号顺序写进 ffmpeg；返回 ffmpeg 收尾的 promise（不必等它编完就能开始下一个场景）
async function encodeFrames(pages, frames, ff, label) {
  const ready = new Map(); let next = 0, wake = null, err = null; const t0 = Date.now();
  const closed = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg ${label} exit ${c}`)))));
  closed.catch(() => {});   // 由调用方 await；这里只防"还没 await 就先失败"被当成未处理
  const workers = Promise.all(pages.map(async (page, k) => {
    for (let i = k; i < frames && !err; i += pages.length) {
      while (i - next > pages.length * 3 && !err) await new Promise((r) => setTimeout(r, 5));   // 别让某页跑太远，控内存
      ready.set(i, await shot(page, i / FPS)); if (wake) wake();
    }
  })).catch((e) => { err = e; if (wake) wake(); });
  while (next < frames) {
    if (err) { ff.kill(); throw err; }
    if (!ready.has(next)) { await new Promise((r) => (wake = r)); wake = null; continue; }
    const buf = ready.get(next); ready.delete(next);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (next % 150 === 0) process.stdout.write(`\r${label}: ${next}/${frames} frames  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    next++;
  }
  await workers;
  ff.stdin.end();
  return { seconds: (Date.now() - t0) / 1000, closed };
}

// 出片后清中间产物：stills 静帧（成片出来就过期了）、out/ 里场景改名/删掉后留下的旧分段、concat 清单。
// 留着 out/ 各场景分段与 master.mp4：单场景重渲要靠它们重拼，wb mix 调 BGM 要读 master
function cleanWork(script) {
  const keep = new Set(script.map((sc) => `${sc.name}.mp4`).concat(['99-brand.mp4', 'master.mp4']));
  const gone = [];
  if (fs.existsSync(P.frames)) { gone.push(`frames/ ${fs.readdirSync(P.frames).length} 张静帧`); fs.rmSync(P.frames, { recursive: true, force: true }); }
  if (fs.existsSync(P.out)) for (const f of fs.readdirSync(P.out)) {
    if (keep.has(f)) continue;
    fs.rmSync(path.join(P.out, f), { recursive: true, force: true }); gone.push(`out/${f}`);
  }
  console.log(gone.length ? `清理中间产物：${gone.join('、')}` : '没有要清的中间产物');
}

async function main() {
  const script = JSON.parse(fs.readFileSync(P.script));
  if (cleanMode) return cleanWork(script);
  fs.mkdirSync(P.out, { recursive: true });
  if (stills) fs.mkdirSync(P.frames, { recursive: true });
  // 静帧与封面只截几张，一页够了；出片开 WORKERS 路并行
  const workers = await Promise.all(Array.from({ length: stills || coverMode ? 1 : WORKERS }, openPage));
  const pages = workers.map((w) => w.page), page = pages[0];
  const closeAll = () => Promise.all(workers.map((w) => w.browser.close()));

  // 封面：scenes/cover.json 列出的每个画幅，全部画完的静帧 → <期>/封面-<ratio>.png
  if (coverMode) {
    const cj = path.join(P.scenes, 'cover.json');
    if (!fs.existsSync(cj)) throw new Error('scenes.js 里没定义封面：build(__dirname, scenes, { cover: (s, ratio) => s.coverLayout({...}) })');
    for (const c of JSON.parse(fs.readFileSync(cj))) {
      const doc = loadDrawing(c.name);
      await page.setViewportSize({ width: c.width, height: c.height });
      await page.evaluate(({ w, h }) => window.setCanvas(w, h), { w: c.width, h: c.height });
      await page.evaluate(({ elements, beatOf, files }) => window.loadScene(elements, beatOf, [[0, 5]], files, 6), { elements: doc.elements, beatOf: c.beatOf, files: doc.files || {} });
      await page.evaluate(() => { window.setBrand(null); window.setCaptions([]); window.seek(100); });
      const out = path.join(P.project, `封面-${c.ratio.replace(':', 'x')}.png`);
      await page.screenshot({ path: out });
      console.log(`封面 ${c.ratio} ${c.width}×${c.height} → ${path.basename(out)}`);
    }
    await closeAll();
    return;
  }
  const brand = brandPayload();
  const wmDraw = (BRAND.watermark && BRAND.watermark.enabled !== false && BRAND.watermark.drawInSeconds) || 0;

  // 待渲染队列：正片场景 + （整片渲染时）片尾品牌卡
  const queue = script.filter((sc) => !only.length || only.includes(sc.name)).map((sc) => ({ sc, isCard: false }));
  const wantCard = BRAND.endCard && BRAND.endCard.enabled && BRAND.name;
  if (wantCard && (!only.length || only.includes('99-brand'))) {
    // 片尾卡：总长 seconds，其中最后 holdSeconds 静止展示（画完再停一会儿）
    const secs = BRAND.endCard.seconds || 5.5, hold = BRAND.endCard.holdSeconds == null ? 1.5 : BRAND.endCard.holdSeconds;
    const doc = brandEndCard(BRAND).toRenderDoc();
    queue.push({ sc: { name: '99-brand', beatOf: doc.beatOf, segments: doc.segments }, isCard: true, doc, info: { duration: Math.max(1, secs - LEAD - HOLD - hold), segmentStarts: [0], total: secs, drawEnd: secs - hold } });
  }

  const encodes = [];
  const tAll = Date.now();
  for (const { sc, isCard, doc: cardDoc, info: cardInfo } of queue) {
    const info = isCard ? cardInfo : infoFor(sc);
    const doc = isCard ? cardDoc : loadDrawing(sc.name);
    const beats = beatsFor(info);
    const total = info.total || info.duration + LEAD + HOLD;
    // 水印：全片第一个场景逐笔画入，其余场景静态；品牌卡上不叠水印
    const isFirst = script.length && sc.name === script[0].name;
    const cues = cfg.captions.enabled && info.wordList ? cuesForScene(info) : [];
    // 每个页面各自装同一个场景（排期是纯计算，各页结果相同），等贴纸解码完再开拍
    const [n] = await Promise.all(pages.map(async (pg) => {
      const n = await pg.evaluate(({ elements, beatOf, beats, files, total }) => window.loadScene(elements, beatOf, beats, files, total), { elements: doc.elements, beatOf: sc.beatOf, beats, files: doc.files || {}, total: info.drawEnd || total });
      await pg.evaluate(({ brand, win }) => window.setBrand(brand, win), { brand: isCard ? null : brand, win: isFirst && wmDraw ? [0.1, 0.1 + wmDraw] : null });
      await pg.evaluate(({ cues, style }) => window.setCaptions(cues, style), { cues, style: CAP_STYLE });
      await pg.evaluate(() => window.imagesReady());
      return n;
    }));

    if (stills) {
      for (let i = 0; i < beats.length; i++) {
        // 最后一个 beat 允许画到 HOLD 里，静帧取场景末尾
        await page.evaluate((t) => window.seek(t), i + 1 === beats.length ? total - 0.05 : beats[i][1] - 0.02);
        await page.screenshot({ path: path.join(P.frames, `${sc.name}-beat${i + 1}.png`) });
      }
      if (!isCard) {
        await page.evaluate((t) => window.seek(t), beats[0][0] + (beats[0][1] - beats[0][0]) * 0.4);
        await page.screenshot({ path: path.join(P.frames, `${sc.name}-mid.png`) });
      }
      console.log(`${sc.name}: ${n} items, ${beats.length} stills`);
      continue;
    }

    const audio = isCard ? null : ['wav', 'mp3'].map((e) => path.join(P.audio, `${sc.name}.${e}`)).find((f) => fs.existsSync(f));
    if (!isCard && !audio) throw new Error(`缺少旁白音频 audio/${sc.name}.wav，先跑 wb tts`);
    const outMp4 = path.join(P.out, `${sc.name}.mp4`);
    const audioIn = isCard ? ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo'] : ['-i', audio];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
      ...audioIn,
      '-filter_complex', `[1:a]adelay=${Math.round(LEAD * 1000)}|${Math.round(LEAD * 1000)},apad,aformat=sample_rates=48000:channel_layouts=stereo[a]`,
      '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS),
      '-c:a', 'aac', '-b:a', '192k', '-shortest', outMp4], { stdio: ['pipe', 'inherit', 'inherit'] });
    const frames = Math.ceil(total * FPS);
    const r = await encodeFrames(pages, frames, ff, sc.name);
    console.log(`\r${sc.name}: done ${frames} frames in ${r.seconds.toFixed(0)}s  (${total.toFixed(1)}s)`);
    encodes.push(r.closed);
  }
  await closeAll();
  await Promise.all(encodes);
  if (!stills) console.log(`出帧 ${((Date.now() - tAll) / 1000).toFixed(0)}s，${pages.length} 路并行`);

  // 拼 master：按 script 顺序（+ 片尾卡）取 out/ 里的分段；只渲染了部分场景时，只要其余分段还在就照样重拼，wb mix 即可出新成片
  if (!stills) {
    const names = script.map((sc) => sc.name).concat(wantCard ? ['99-brand'] : []);
    const all = names.map((n) => path.join(P.out, `${n}.mp4`));
    const missing = all.filter((f) => !fs.existsSync(f)).map((f) => path.basename(f));
    if (missing.length) { console.log(`缺少分段 ${missing.join(', ')}，没拼 master；跑一次完整 wb render`); return; }
    const list = path.join(P.out, 'list.txt');
    // Windows 的 ffmpeg concat 清单要正斜杠，反斜杠会被当转义字符吃掉。
    fs.writeFileSync(list, all.map((p) => `file '${p.replace(/\\/g, '/').replace(/'/g, "'\\''")}'`).join('\n'));
    await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', path.join(P.out, 'master.mp4')]);
    console.log(`master: ${path.relative(process.cwd(), path.join(P.out, 'master.mp4'))}（无 BGM，下一步 wb mix）`);
    if (cfg.captions.enabled) { const r = writeSrt(P.project); console.log(`字幕 ${r.count} 条 → ${path.basename(r.file)}`); }
  }
}
main().catch((e) => { console.error(e); process.exit(1); });
