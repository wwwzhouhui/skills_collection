// 把 assets/template.html + scenes.json + gsap.min.js 打包成一个自包含 HTML（可离线播放 / 供渲染器逐帧截图）
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const SKILL = resolve(__dir, "..");

const [, , ...rest] = process.argv;
// 解析位置参数 + --flag=value（如 --skin=aurora --badge=xxx --foot=yyy --orient=portrait）
const flags = {};
const positional = [];
for (const a of rest) {
  if (a.startsWith("--")) { const i = a.indexOf("="); flags[i < 0 ? a.slice(2) : a.slice(2, i)] = i < 0 ? true : a.slice(i + 1); }
  else positional.push(a);
}
const [scenesPath, outPath] = positional;
if (!scenesPath || !outPath) {
  console.error("用法: node build_html.mjs <scenes.json> <out.html> [--total=15] [--fps=30] [--skin=aurora] [--orient=portrait] [--badge=xxx] [--foot=yyy]");
  console.error("  --total=<秒>  目标总时长（也可在 scenes.json 顶层写 \"duration\": 15）；缺省=各幕 dur 之和");
  process.exit(1);
}

// 可选配色皮肤（须与 assets/template.html 的 html[data-skin="..."] 一一对应）
const SKINS = ["tech","wuding","aurora","sunset","ocean","forest","midnight","gold","candy","paper"];

const tpl = readFileSync(join(SKILL, "assets", "template.html"), "utf8");
const gsap = readFileSync(join(SKILL, "assets", "gsap.min.js"), "utf8");
const data = JSON.parse(readFileSync(resolve(scenesPath), "utf8"));

const scenes = data.scenes;

// ─────────────────────────────────────────────────────────────
// 时长控制：--total=<秒>（CLI 优先）或 scenes.json 顶层 "duration"
//   不指定 → 用各幕 dur 之和（原样）
//   指定且与当前总和不符 → 按比例缩放各幕 dur，精确归一到目标时长
//   指定且已相等（±0.05s）→ 不缩放
// ─────────────────────────────────────────────────────────────
const FPSOUT = Number(flags.fps || data.fps || 30);
const MIN_DUR = 0.6; // 单幕最短 0.6s，避免缩放到不可见
const rawTarget = flags.total !== undefined ? flags.total : (data.duration !== undefined ? data.duration : null);
let sumDur = scenes.reduce((s, x) => s + (Number(x.dur) || 5), 0);

if (rawTarget !== null) {
  const target = Number(rawTarget);
  if (!Number.isFinite(target) || target <= 0) {
    console.warn(`[build] ⚠️ 无效时长参数 "${rawTarget}"，已忽略（用各幕 dur 之和 ${sumDur.toFixed(2)}s）`);
  } else if (scenes.length * MIN_DUR > target) {
    console.warn(`[build] ⚠️ 目标 ${target}s 装不下 ${scenes.length} 幕（每幕至少 ${MIN_DUR}s），已按最小值铺满 ${(scenes.length * MIN_DUR).toFixed(2)}s`);
    scenes.forEach(sc => { sc.dur = MIN_DUR; });
    sumDur = scenes.reduce((s, x) => s + x.dur, 0);
  } else if (Math.abs(sumDur - target) <= 0.05) {
    console.log(`[build] 时长 ${sumDur.toFixed(2)}s 已等于目标 ${target}s，无需缩放`);
  } else {
    const scale = target / sumDur;
    let acc = 0;
    scenes.forEach((sc, i) => {
      const d = i === scenes.length - 1
        ? Number((target - acc).toFixed(2))
        : Number(((Number(sc.dur) || 5) * scale).toFixed(2));
      sc.dur = Math.max(MIN_DUR, d);
      acc += sc.dur;
    });
    // 修正四舍五入漂移，保证总和精确等于目标
    const drift = Number((target - acc).toFixed(2));
    if (drift !== 0) scenes[scenes.length - 1].dur = Number((scenes[scenes.length - 1].dur + drift).toFixed(2));
    console.log(`[build] 时长归一：${sumDur.toFixed(2)}s → ${target}s（比例 ${scale.toFixed(3)}，逐幕 ${scenes.map(s => s.dur).join(" / ")}）`);
    sumDur = scenes.reduce((s, x) => s + x.dur, 0);
  }
}

let skin = flags.skin || data.skin || "tech";
if (!SKINS.includes(skin)) { console.warn(`[build] ⚠️ 未知皮肤 "${skin}"，回退 tech。可选：${SKINS.join(", ")}`); skin = "tech"; }
const meta = {
  badge: flags.badge || data.badge || "海老豹666",
  foot: flags.foot !== undefined ? flags.foot : (data.foot || ""),
  skin,
  orient: flags.orient || data.orient || "landscape"
};

const orient = meta.orient === "portrait" ? "portrait" : "landscape";
const W = orient === "portrait" ? 1080 : 1920;
const H = orient === "portrait" ? 1920 : 1080;

let html = tpl
  .replace("/*__SCENES__*/[]", JSON.stringify(scenes))
  .replace(/\/\*__META__\*\/\{[^}]*\}/, JSON.stringify(meta))
  .replace('data-orient="landscape"', `data-orient="${orient}"`)
  .replace('data-w="1920" data-h="1080"', `data-w="${W}" data-h="${H}"`)
  .replace('<script src="gsap.min.js"></script>', `<script>${gsap}</script>`);

if (!html.includes('"orient"')) { console.error("[build] ⚠️ META 替换失败，模板占位符不匹配"); process.exit(1); }

mkdirSync(dirname(resolve(outPath)), { recursive: true });
writeFileSync(resolve(outPath), html, "utf8");

// 写出「生效分镜」sidecar：含缩放后的真实 dur，供 make_srt.mjs / 复核使用，保证字幕与画面同源
const effPath = resolve(outPath).replace(/\.html?$/i, "") + ".effective.json";
const effScenes = scenes.map((sc, i) => ({
  i,
  type: sc.type,
  dur: sc.dur,
  start: Number(scenes.slice(0, i).reduce((s, x) => s + x.dur, 0).toFixed(3)),
  srt: sc.srt !== undefined ? sc.srt : null
}));
writeFileSync(effPath, JSON.stringify({
  total: sumDur, fps: FPSOUT, frames: Math.round(sumDur * FPSOUT),
  orient, skin: meta.skin, scenes: effScenes
}, null, 2), "utf8");

console.log(`[build] ${resolve(outPath)}`);
console.log(`[build] 场景 ${scenes.length} 幕 / 总时长 ${sumDur.toFixed(2)}s / ${FPSOUT}fps = ${Math.round(sumDur * FPSOUT)} 帧`);
console.log(`[build] 配色 skin=${meta.skin} / 画幅 orient=${orient}`);
console.log(`[build] 生效分镜 → ${effPath}（供字幕/复核）`);
