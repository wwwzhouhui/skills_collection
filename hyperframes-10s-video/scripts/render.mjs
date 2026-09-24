// 用无头 Chromium 把自包含动画 HTML 逐帧截图成序列（确定性渲染：按时间轴 seek，不依赖真实播放速度）
// 用法: node render.mjs <input.html> <framesDir> [--fps=30] [--scale=1] [--quality=92] [--every=1] [--only=1,2,3]
import { readFileSync, mkdirSync, existsSync, writeFileSync } from "node:fs";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const __dir = dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const positional = argv.filter(a => !a.startsWith("--"));
const opt = Object.fromEntries(argv.filter(a => a.startsWith("--")).map(a => {
  const [k, v] = a.replace(/^--/, "").split("=");
  return [k, v === undefined ? true : v];
}));

const input = positional[0], framesDir = positional[1];
if (!input || !framesDir) { console.error("用法: node render.mjs <input.html> <framesDir> [--fps=30]"); process.exit(1); }

const FPS = Number(opt.fps || 30);
const SCALE = Number(opt.scale || 1);
const QUALITY = Number(opt.quality || 92);
const EVERY = Number(opt.every || 1);
const ONLY = opt.only ? String(opt.only).split(",").map(Number) : null;
const START = Number(opt.start || 0);
const END = opt.end !== undefined ? Number(opt.end) : null;

// 定位 chromium：优先当前用户 Playwright 缓存（自动取最高版本），其次本机 Edge/Chrome
function findChromium() {
  const { existsSync: ex, readdirSync } = require("node:fs");
  const { homedir } = require("node:os");
  const { join: pj } = require("node:path");
  const cands = [
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ];
  try {
    const pwDir = pj(homedir(), "AppData", "Local", "ms-playwright");
    const vers = readdirSync(pwDir)
      .filter(d => /^chromium-\d+$/.test(d))
      .sort((a, b) => Number(b.split("-")[1]) - Number(a.split("-")[1]));
    for (const v of vers) cands.unshift(pj(pwDir, v, "chrome-win64", "chrome.exe"));
  } catch {}
  return cands.find(p => ex(p));
}

const CHROME = opt.chrome || findChromium();
if (!CHROME) { console.error("[render] 找不到 Chromium，用 --chrome=<path> 指定"); process.exit(1); }

const { chromium } = require(require.resolve("playwright-core", { paths: [join(__dir, "..", "..", "..", "binaries", "node", "workspace"), process.cwd()] }));

const framesDirAbs = resolve(framesDir);
mkdirSync(framesDirAbs, { recursive: true });

const browser = await chromium.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--force-device-scale-factor=1", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--font-render-hinting=none"]
});
// 画布尺寸由 HTML 的 data-w/data-h 决定（横屏 1920×1080 / 竖屏 1080×1920）
const htmlSrc = readFileSync(resolve(input), "utf8");
const mw = htmlSrc.match(/data-w="(\d+)"/);
const mh = htmlSrc.match(/data-h="(\d+)"/);
const VW = Number(opt.w || (mw ? mw[1] : 1920));
const VH = Number(opt.h || (mh ? mh[1] : 1080));

const page = await browser.newPage({ viewport: { width: VW, height: VH }, deviceScaleFactor: SCALE });

const errors = [];
page.on("pageerror", e => errors.push(String(e)));
page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });

await page.goto(pathToFileURL(resolve(input)).href + "?capture=1", { waitUntil: "load" });
await page.waitForFunction("window.__KINETIC__ && window.__KINETIC__.total > 0", null, { timeout: 30000 });

const info = await page.evaluate(() => ({ total: window.__KINETIC__.total }));
const totalFrames = Math.round(info.total * FPS);
const endFrame = END === null ? totalFrames : Math.min(END, totalFrames);
const list = ONLY ? ONLY : Array.from({ length: totalFrames }, (_, i) => i)
  .filter(i => i % EVERY === 0 && i >= START && i < endFrame);

console.log(`[render] chromium: ${CHROME}`);
console.log(`[render] 画布 ${VW}×${VH}`);
console.log(`[render] 总时长 ${info.total.toFixed(2)}s | ${totalFrames} 帧 | 本次输出 ${list.length} 帧`);

const t0 = Date.now();
for (let n = 0; n < list.length; n++) {
  const f = list[n];
  const t = f / FPS;
  await page.evaluate(tt => window.__KINETIC__.seek(tt), t);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const name = `f${String(f).padStart(5, "0")}.jpg`;
  await page.screenshot({ path: join(framesDirAbs, name), type: "jpeg", quality: QUALITY });
  if (n % 30 === 0 || n === list.length - 1) {
    const el = (Date.now() - t0) / 1000;
    const eta = (el / (n + 1)) * (list.length - n - 1);
    process.stdout.write(`\r[render] ${n + 1}/${list.length}  (${el.toFixed(0)}s, 预计剩 ${eta.toFixed(0)}s)   `);
  }
}
process.stdout.write("\n");

writeFileSync(join(framesDirAbs, "_meta.json"), JSON.stringify({ fps: FPS, totalFrames, rendered: list.length, total: info.total }, null, 2));

if (errors.length) {
  console.warn(`[render] 页面报错 ${errors.length} 条：`);
  errors.slice(0, 8).forEach(e => console.warn("   - " + e.slice(0, 200)));
} else {
  console.log("[render] 无页面错误 ✅");
}
await browser.close();
console.log(`[render] 完成 → ${framesDirAbs}`);
