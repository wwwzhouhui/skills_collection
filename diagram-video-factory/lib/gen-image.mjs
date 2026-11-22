// 用本地 codex CLI 的 imagegen 出"白板贴纸"：白底 + 粗黑马克笔描边 + Excalidraw 配色，然后抠掉白底、裁到内容边界。
// 一次最多 4 张走 2x2 四宫格（一次生成额度、画风一致），再切格。
// 用法：node lib/gen-image.mjs <projectDir> name1="英文描述" [name2="..." ...] [--single] [--ref=path.png] [--rekey 只重抠不重生成]
//   产物 <期目录>/assets/<name>.png（透明底）；原图留在 build/<期>/raw/
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { chromium } from "playwright";
import chromiumPath from "./chromium.cjs";
import paths from "./paths.cjs";

// codex CLI 的定位：Windows 上 npm 全局只提供 codex.cmd / codex.ps1 包装，Node 的 spawn 既不能直接跑 .cmd
// （会被 EINVAL/ENOENT 拦掉），所以直接找到包内真正的入口 codex.js，用当前 node 执行，跨平台一致。
function resolveCodex() {
  if (process.env.CODEX_BIN) return process.env.CODEX_BIN;
  const dirs = (process.env.PATH || "").split(path.delimiter).filter(Boolean);
  const rels = [
    "node_modules/@openai/codex/bin/codex.js",
    "../node_modules/@openai/codex/bin/codex.js",
    "node_modules/@openai/codex/bin/codex",
  ];
  for (const d of dirs) for (const rel of rels) {
    const p = path.resolve(d, rel);
    if (fs.existsSync(p)) return p;
  }
  return "codex";
}
const CODEX_BIN = resolveCodex();
const CODEX_MODEL = process.env.CODEX_IMAGE_MODEL || "gpt-5.5";
const GEN_DIR = path.join(os.homedir(), ".codex", "generated_images");
const TIMEOUT_MS = Number(process.env.CODEX_IMAGE_TIMEOUT_MS || 360000);

const STYLE =
  "Whiteboard sticker illustration in Excalidraw hand-drawn style: thick, slightly wobbly black marker outlines, " +
  "flat pastel fills using ONLY these colours: pale yellow #ffec99, pale blue #a5d8ff, pale green #b2f2bb, pale red #ffc9c9, light grey #e9ecef, plus black lines. " +
  "Simple chibi proportions, clean and readable at small size, isolated subject centred on a PURE FLAT WHITE background #FFFFFF with nothing else. " +
  "No shadow, no ground line, no texture, no gradient, no text, no letters, no numerals, no logos, no watermark, no border, no photorealism, no 3D, no thin pen lines, no cross-hatching.";

export function stickerPrompt(desc) { return `${desc}. ${STYLE}`; }
// 真人漫画像：--ref=真人照片 --likeness，desc 只写姿势/表情/服装
export function caricaturePrompt(desc) {
  return `A friendly editorial caricature sticker of the real person shown in the attached reference photo. ` +
    `Keep a clearly recognisable likeness: face shape, hairstyle, hair colour, glasses or no glasses, skin tone, and their typical outfit. ` +
    `Chibi-ish proportions with a slightly large head, upper body to waist, ${desc}. ` +
    `Whiteboard sticker in Excalidraw hand-drawn style: thick slightly wobbly black marker outlines, flat pastel fills, clean and readable at small size, ` +
    `single isolated figure centred on a PURE FLAT WHITE background #FFFFFF. No shadow, no ground, no text, no letters, no logos, no border, no photorealism, no 3D.`;
}

function run(bin, args, timeout = TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    // bin 指向 .js 入口时用当前 node 跑（Windows 上 codex 只有 .cmd 包装，spawn 直接跑会失败）
    const useNode = bin.endsWith(".js") || bin.endsWith(".mjs");
    const cmd = useNode ? process.execPath : bin;
    const argv = useNode ? [bin, ...args] : args;
    const child = spawn(cmd, argv, { stdio: ["ignore", "pipe", "pipe"] });
    let out = "", err = "";
    const timer = setTimeout(() => child.kill("SIGKILL"), timeout);
    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));
    child.on("error", (e) => { clearTimeout(timer); reject(e); });
    child.on("close", (code) => { clearTimeout(timer); code === 0 ? resolve({ out, err }) : reject(Object.assign(new Error(`codex exit ${code}`), { out, err })); });
  });
}
function newestSince(startMs) {
  let best = null;
  for (const d of (fs.existsSync(GEN_DIR) ? fs.readdirSync(GEN_DIR) : [])) {
    const sub = path.join(GEN_DIR, d);
    let files = []; try { files = fs.readdirSync(sub); } catch { continue; }
    for (const f of files) {
      if (!f.endsWith(".png")) continue;
      const fp = path.join(sub, f); const st = fs.statSync(fp);
      if (st.mtimeMs >= startMs && (!best || st.mtimeMs > best.mtimeMs)) best = { fp, mtimeMs: st.mtimeMs };
    }
  }
  return best?.fp || null;
}

// 调 codex 出一张图到 outPng（1024x1024，或四宫格）
export async function codexGenerate(prompt, outPng, { grid = false, refImages = [], refRole = 'style', cwd = process.cwd() } = {}) {
  const abs = path.resolve(outPng);
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.rmSync(abs, { force: true });   // 旧原图不删，codex 没落盘时会被当成新图返回
  const instruction =
    `Use your built-in image generation tool (imagegen) to create ONE image and save it to the EXACT absolute path:\n${abs}\n` +
    `Do NOT write code or call any external API — use your native image generation tool only.\n` +
    `Size: 1024x1024 square.\n` +
    (grid
      ? `The image is a clean 2x2 grid of FOUR separate stickers, each quadrant fully independent, each centred in its quadrant with generous white margin, NO grid lines or dividers, pure white background everywhere.\n${prompt}\n`
      : `Image description: ${prompt}\n`) +
    (refImages.length ? (refRole === 'likeness'
      ? `Reference photo(s) attached: use them ONLY for the person's likeness (face, hair, glasses, outfit); do NOT copy the photo style — draw in the sticker style described above.\n`
      : `Reference image(s) attached: match their drawing style (line weight, palette, proportions) exactly.\n`) : "") +
    `After saving, confirm the saved path.`;
  const startMs = Date.now() - 1000;
  const args = ["exec", "--skip-git-repo-check", "--ignore-user-config", "-s", "workspace-write", "-c", "approval_policy=never",
    "-c", `model=${CODEX_MODEL}`, "-c", "model_reasoning_effort=low", "-C", cwd, ...refImages.flatMap((p) => ["-i", path.resolve(p)]), "--", instruction];
  let runErr = null;
  try { await run(CODEX_BIN, args); } catch (e) { runErr = e; }
  if (fs.existsSync(abs) && fs.statSync(abs).size > 0) return abs;
  const fb = newestSince(startMs);
  if (fb) { fs.copyFileSync(fb, abs); return abs; }
  throw new Error("codex imagegen 未产出图片" + (runErr ? `: ${runErr.message} ${String(runErr.err).slice(0, 300)}` : ""));
}

// 在无头浏览器里：切格（可选）→ 从四边泛洪抠掉白底 → 裁到内容边界 → 输出透明 PNG
export async function keyoutAndSplit(rawPng, outputs, { grid = false, pad = 24 } = {}) {
  const exe = chromiumPath.resolveChromium();
  const browser = await chromium.launch(exe ? { executablePath: exe } : {});
  const page = await browser.newPage();
  const dataUrl = "data:image/png;base64," + fs.readFileSync(rawPng).toString("base64");
  const results = await page.evaluate(async ({ dataUrl, n, grid, pad }) => {
    const img = new Image(); img.src = dataUrl; await img.decode();
    const W = img.naturalWidth, H = img.naturalHeight;
    const cells = grid ? [[0, 0], [W / 2, 0], [0, H / 2], [W / 2, H / 2]].slice(0, n) : [[0, 0]];
    const cw = grid ? W / 2 : W, ch = grid ? H / 2 : H;
    const out = [];
    for (const [sx, sy] of cells) {
      const c = document.createElement("canvas"); c.width = cw; c.height = ch;
      const ctx = c.getContext("2d"); ctx.drawImage(img, sx, sy, cw, ch, 0, 0, cw, ch);
      const id = ctx.getImageData(0, 0, cw, ch), d = id.data;
      const isWhite = (i) => { if (d[i + 3] < 20) return true; const r = d[i], g = d[i + 1], b = d[i + 2]; return Math.min(r, g, b) > 232 && Math.max(r, g, b) - Math.min(r, g, b) < 14; };
      // 泛洪：从四边出发，只去掉与边界连通的白
      const seen = new Uint8Array(cw * ch); const stack = [];
      const push = (x, y) => { const k = y * cw + x; if (x < 0 || y < 0 || x >= cw || y >= ch || seen[k]) return; seen[k] = 1; if (isWhite(k * 4)) stack.push(k); else seen[k] = 2; };
      for (let x = 0; x < cw; x++) { push(x, 0); push(x, ch - 1); }
      for (let y = 0; y < ch; y++) { push(0, y); push(cw - 1, y); }
      while (stack.length) { const k = stack.pop(); const x = k % cw, y = (k / cw) | 0; d[k * 4 + 3] = 0; push(x + 1, y); push(x - 1, y); push(x, y + 1); push(x, y - 1); }
      // 边缘羽化：紧贴透明区的像素按白度降 alpha
      for (let y = 1; y < ch - 1; y++) for (let x = 1; x < cw - 1; x++) {
        const k = y * cw + x; if (d[k * 4 + 3] === 0) continue;
        const nb = [k - 1, k + 1, k - cw, k + cw].some((j) => d[j * 4 + 3] === 0);
        if (nb) { const m = Math.min(d[k * 4], d[k * 4 + 1], d[k * 4 + 2]); d[k * 4 + 3] = Math.round(255 * Math.min(1, (255 - m) / 60)); }
      }
      // 连通块：去掉杂点与邻格残片（只留最大块 + 面积 ≥ 3% 的块）
      const comp = new Int32Array(cw * ch).fill(-1); const areas = [];
      for (let k0 = 0; k0 < cw * ch; k0++) {
        if (d[k0 * 4 + 3] <= 8 || comp[k0] >= 0) continue;
        const id = areas.length; let area = 0; const st = [k0]; comp[k0] = id;
        while (st.length) { const k = st.pop(); area++; const x = k % cw, y = (k / cw) | 0;
          for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]]) { const nx = x + dx, ny = y + dy; if (nx < 0 || ny < 0 || nx >= cw || ny >= ch) continue; const nk = ny * cw + nx; if (comp[nk] < 0 && d[nk * 4 + 3] > 8) { comp[nk] = id; st.push(nk); } } }
        areas.push(area);
      }
      const maxA = Math.max(0, ...areas);
      for (let k = 0; k < cw * ch; k++) if (comp[k] >= 0 && areas[comp[k]] < maxA * 0.03) d[k * 4 + 3] = 0;
      // 裁到内容
      let x0 = cw, y0 = ch, x1 = 0, y1 = 0;
      for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) if (d[(y * cw + x) * 4 + 3] > 8) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
      if (x1 <= x0) { out.push(null); continue; }
      ctx.putImageData(id, 0, 0);
      x0 = Math.max(0, x0 - pad); y0 = Math.max(0, y0 - pad); x1 = Math.min(cw - 1, x1 + pad); y1 = Math.min(ch - 1, y1 + pad);
      const o = document.createElement("canvas"); o.width = x1 - x0 + 1; o.height = y1 - y0 + 1;
      o.getContext("2d").drawImage(c, x0, y0, o.width, o.height, 0, 0, o.width, o.height);
      out.push({ dataUrl: o.toDataURL("image/png"), w: o.width, h: o.height });
    }
    return out;
  }, { dataUrl, n: outputs.length, grid, pad });
  await browser.close();
  results.forEach((r, i) => {
    if (!r) { console.log("  空白格:", outputs[i]); return; }
    fs.writeFileSync(outputs[i], Buffer.from(r.dataUrl.split(",")[1], "base64"));
    console.log(`  ${path.basename(outputs[i])}  ${r.w}x${r.h}`);
  });
}

// CLI
if (process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]))) {
  const args = process.argv.slice(2);
  const P = paths.projectPaths(args[0]);
  const project = P.project;
  const single = args.includes("--single");
  const rekey = args.includes("--rekey");
  const likeness = args.includes("--likeness");
  const ref = args.filter((a) => a.startsWith("--ref=")).map((a) => a.slice(6));
  const items = args.slice(1).filter((a) => !a.startsWith("--")).map((a) => { const i = a.indexOf("="); return { name: a.slice(0, i), desc: a.slice(i + 1) }; });
  if (!items.length || items.length > 4) { console.error("每次 1~4 个 name=描述"); process.exit(1); }
  const assets = P.assets, raw = P.raw;
  fs.mkdirSync(raw, { recursive: true }); fs.mkdirSync(assets, { recursive: true });
  if (likeness && (items.length !== 1 || !ref.length)) { console.error("--likeness 一次 1 张，且要 --ref=真人照片"); process.exit(1); }
  const grid = items.length > 1 && !single;
  const quad = ["top-left", "top-right", "bottom-left", "bottom-right"];
  const prompt = grid
    ? items.map((it, k) => `${quad[k]} quadrant: ${it.desc}`).join("\n") + `\n${STYLE}`
    : likeness ? caricaturePrompt(items[0].desc) : stickerPrompt(items[0].desc);
  const rawPng = path.join(raw, (grid ? items.map((i) => i.name).join("+") : items[0].name) + ".png");
  if (rekey) console.log(`复用原图 ${path.relative(project, rawPng)}`);
  else { console.log(`codex 出图 → ${path.relative(project, rawPng)}`); await codexGenerate(prompt, rawPng, { grid, refImages: ref, refRole: likeness ? 'likeness' : 'style', cwd: project }); }
  console.log("抠白底 + 裁边:");
  await keyoutAndSplit(rawPng, items.map((i) => path.join(assets, i.name + ".png")), { grid });
}
