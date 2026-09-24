// 程序化检测动画 HTML 各场景在指定画布下是否溢出（替代肉眼看帧）
// 用法: node check_overflow.mjs <input.html>
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, resolve, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const __dir = dirname(fileURLToPath(import.meta.url));
const input = process.argv[2];
if (!input) { console.error("用法: node check_overflow.mjs <input.html>"); process.exit(1); }

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
const CHROME = findChromium();
const { chromium } = require(require.resolve("playwright-core", { paths: [join(__dir, "..", "..", "..", "binaries", "node", "workspace"), process.cwd()] }));

const htmlSrc = readFileSync(resolve(input), "utf8");
const mw = htmlSrc.match(/data-w="(\d+)"/);
const mh = htmlSrc.match(/data-h="(\d+)"/);
const VW = mw ? Number(mw[1]) : 1920;
const VH = mh ? Number(mh[1]) : 1080;

const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ["--force-device-scale-factor=1", "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--font-render-hinting=none"] });
const page = await browser.newPage({ viewport: { width: VW, height: VH }, deviceScaleFactor: 1 });
await page.goto(pathToFileURL(resolve(input)).href + "?capture=1", { waitUntil: "load" });
await page.waitForFunction("window.__KINETIC__ && window.__KINETIC__.starts.length>0", null, { timeout: 30000 });

const starts = await page.evaluate(() => window.__KINETIC__.starts);
const total = await page.evaluate(() => window.__KINETIC__.total);

console.log(`\n画布 ${VW}×${VH} | 场景 ${starts.length} | 总时长 ${total.toFixed(2)}s\n`);
let bad = 0;
for (let i = 0; i < starts.length; i++) {
  const mid = Math.min(total - 0.2, starts[i] + 0.6);
  await page.evaluate(t => window.__KINETIC__.seek(t), mid);
  await page.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
  const res = await page.evaluate(() => {
    const scene = [...document.querySelectorAll(".scene")].find(s => getComputedStyle(s).visibility === "visible");
    if (!scene) return { ok: false, reason: "无可见场景" };
    const inner = scene.querySelector(".scene-inner");
    const ib = inner.getBoundingClientRect();
    // 遍历所有后代，找最大/最小坐标
    let maxR = -1e9, maxB = -1e9, minL = 1e9, minT = 1e9;
    scene.querySelectorAll("*").forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      maxR = Math.max(maxR, r.right); maxB = Math.max(maxB, r.bottom);
      minL = Math.min(minL, r.left); minT = Math.min(minT, r.top);
    });
    return { ok: true, inner: { l: ib.left, t: ib.top, r: ib.right, b: ib.bottom }, maxR, maxB, minL, minT };
  });
  if (!res.ok) { console.log(`  场景 ${i}: ${res.reason}`); bad++; continue; }
  const overR = res.maxR - VW, overB = res.maxB - VH, overL = -res.minL, overT = -res.minT;
  const flags = [];
  if (overR > 1) flags.push(`右溢+${overR.toFixed(0)}`);
  if (overB > 1) flags.push(`下溢+${overB.toFixed(0)}`);
  if (overL > 1) flags.push(`左溢+${overL.toFixed(0)}`);
  if (overT > 1) flags.push(`上溢+${overT.toFixed(0)}`);
  const tag = flags.length ? "❌ " + flags.join(" ") : "✅";
  if (flags.length) bad++;
  console.log(`  场景 ${i} [${mid.toFixed(1)}s] ${tag}`);
}
console.log(bad ? `\n发现 ${bad} 个场景溢出` : "\n全部场景在画布内，无溢出 ✅");
await browser.close();
