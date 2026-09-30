// 把本地 SVG 渲成透明底 PNG —— 给「Commons 上没有、只能从官网/press kit 拿」的 Logo 用。
// Commons 有的走 lib/fetch-logo.mjs（wb logo），那一步会连带记录来源；这个工具只负责渲染。
// 用法: node lib/svg2png.mjs <输入.svg> <输出.png> [宽|高，默认按长边 1600/800]
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";
import chromiumPath from "./chromium.cjs";

const [inSvg, outPng, sizeArg] = process.argv.slice(2);
if (!inSvg || !outPng) {
  console.error("用法: node lib/svg2png.mjs <输入.svg> <输出.png> [宽|高]");
  process.exit(1);
}

const svg = fs.readFileSync(inSvg, "utf8").replace(/<\?xml[^>]*\?>/, "");
const vb = svg.match(/viewBox="([^"]+)"/);
let asp = 1;
if (vb) { const [, , w, h] = vb[1].trim().split(/[\s,]+/).map(Number); if (w && h) asp = w / h; }

const size = sizeArg ? Number(sizeArg) : null;
const box = size
  ? `width:${size}px`
  : asp > 1.6 ? "width:1600px" : `width:${Math.round(800 * asp)}px;height:800px`;

const exe = chromiumPath.resolveChromium();
const browser = await chromium.launch(exe ? { executablePath: exe } : {});
const page = await browser.newPage();
await page.setContent(`<html><body style="margin:0;background:transparent"><div id=w style="display:inline-block;padding:4px"><div style="${box}">${svg}</div></div><style>svg{width:100%;height:auto;display:block}</style></body></html>`);
fs.mkdirSync(path.dirname(path.resolve(outPng)), { recursive: true });
await (await page.$("#w")).screenshot({ path: outPng, omitBackground: true });
await browser.close();
console.log(`  ${path.basename(outPng)} ← ${path.basename(inSvg)}  (viewBox 比例 ${asp.toFixed(2)})`);
