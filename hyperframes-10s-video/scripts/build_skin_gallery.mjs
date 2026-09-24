// 把各配色渲染帧拼成一张「配色预览画廊」自包含 HTML（图片 base64 内嵌，可离线查看）
// 用法: node build_skin_gallery.mjs <帧根目录> <输出.html> [--frames=48,156] [--scene=landscape]
//   帧根目录下按皮肤名分子目录，如 <root>/aurora/f00048.jpg、<root>/aurora/f00156.jpg
import { readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { mkdirSync } from "node:fs";

const args = process.argv.slice(2);
const flags = {};
const pos = [];
for (const a of args) {
  if (a.startsWith("--")) { const i = a.indexOf("="); flags[i < 0 ? a.slice(2) : a.slice(2, i)] = i < 0 ? true : a.slice(i + 1); }
  else pos.push(a);
}
const [root, outPath] = pos;
if (!root || !outPath) { console.error("用法: node build_skin_gallery.mjs <帧根目录> <输出.html> [--frames=48,156]"); process.exit(1); }
const FRAMES = String(flags.frames || "48,156").split(",").map(s => `f${String(s.trim()).padStart(5, "0")}.jpg`);
const FRAME_LABELS = String(flags.labels || "片头,主体").split(",");

// 与 assets/template.html 的皮肤一一对应
const SKINS = [
  { k: "tech",     label: "深墨科技",   desc: "薄荷 · 天蓝 · 珊瑚（默认）", bg: "#06121F", c1: "#2FE3C7", c2: "#38BDF8", c3: "#F7A66A" },
  { k: "wuding",   label: "五鼎雅致",   desc: "松绿 · 暖橙 · 米金",         bg: "#0E1A16", c1: "#56A989", c2: "#F2A979", c3: "#E8D9A0" },
  { k: "aurora",   label: "极光紫青",   desc: "紫罗兰 · 青绿 · 粉",         bg: "#0B0A1F", c1: "#8B7CFF", c2: "#35E0D0", c3: "#FF8FD0" },
  { k: "sunset",   label: "日落橙粉",   desc: "橘橙 · 玫红 · 暖金",         bg: "#1A0E12", c1: "#FF8A5B", c2: "#FF5C8A", c3: "#FFD166" },
  { k: "ocean",    label: "深海蓝绿",   desc: "青绿 · 宝蓝 · 浅青",         bg: "#04121C", c1: "#38D6C4", c2: "#2E8BFF", c3: "#7FE3FF" },
  { k: "forest",   label: "森野绿",     desc: "嫩绿 · 翡翠 · 黄绿",         bg: "#0A140C", c1: "#7BD389", c2: "#35C0A0", c3: "#D9E8A0" },
  { k: "midnight", label: "午夜蓝紫",   desc: "靛蓝 · 紫 · 天青",           bg: "#070B18", c1: "#6C8CFF", c2: "#9B6CFF", c3: "#4FD1FF" },
  { k: "gold",     label: "黑金商务",   desc: "香槟金 · 琥珀 · 米驼",       bg: "#0B0B0D", c1: "#E9C46A", c2: "#F4A261", c3: "#D9B08C" },
  { k: "candy",    label: "糖果马卡龙", desc: "桃粉 · 天蓝 · 奶黄",         bg: "#1B1026", c1: "#FF7EB6", c2: "#7ED8FF", c3: "#FFE08A" },
  { k: "paper",    label: "素白浅色",   desc: "品牌蓝 · 青绿 · 橘（浅底深字）", bg: "#F5F7FB", c1: "#2569AB", c2: "#12A48E", c3: "#E67E22" }
];

const b64 = p => existsSync(p) ? readFileSync(p).toString("base64") : null;

const cards = SKINS.map(s => {
  const dir = join(resolve(root), s.k);
  const imgs = FRAMES.map((f, i) => {
    const data = existsSync(dir) ? b64(join(dir, f)) : null;
    if (!data) return `<div class="ph">未渲染</div>`;
    return `<figure><img src="data:image/jpeg;base64,${data}" alt="${s.k} ${f}"><figcaption>${FRAME_LABELS[i] || f}</figcaption></figure>`;
  }).join("");
  const sw = [s.c1, s.c2, s.c3, s.bg].map(c => `<span class="dot" style="background:${c}"></span>`).join("");
  return `<section class="card">
    <div class="shots">${imgs}</div>
    <div class="info">
      <div class="row"><code>${s.k}</code><span class="lab">${s.label}</span></div>
      <div class="desc">${s.desc}</div>
      <div class="pal">${sw}<span class="hex">${s.c1} · ${s.c2} · ${s.c3}</span></div>
    </div>
  </section>`;
}).join("\n");

const html = `<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>配色皮肤预览 · HyperFrames</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0e14;color:#e8eef6;font-family:"Microsoft YaHei","PingFang SC",-apple-system,sans-serif;padding:40px 32px 80px}
h1{font-size:30px;font-weight:800;letter-spacing:-.01em}
.sub{color:#8da0b6;font-size:15px;margin-top:10px;line-height:1.7}
.sub code{background:rgba(255,255,255,.08);padding:2px 8px;border-radius:6px;color:#7fe3c8}
.wrap{display:grid;grid-template-columns:repeat(auto-fill,minmax(560px,1fr));gap:26px;margin-top:32px}
.card{background:#111823;border:1px solid rgba(255,255,255,.08);border-radius:18px;overflow:hidden;display:flex;flex-direction:column}
.shots{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:rgba(255,255,255,.06)}
.shots figure{position:relative;background:#000}
.shots img{width:100%;display:block}
.shots figcaption{position:absolute;left:8px;bottom:8px;font-size:12px;background:rgba(0,0,0,.6);padding:2px 8px;border-radius:6px;color:#cfe0f0}
.ph{aspect-ratio:16/9;display:flex;align-items:center;justify-content:center;color:#5a6b80;font-size:13px;background:#0d131c}
.info{padding:16px 18px 18px}
.row{display:flex;align-items:center;gap:12px}
.row code{font-size:15px;font-weight:700;color:#7fe3c8;background:rgba(127,227,200,.10);padding:3px 10px;border-radius:8px}
.lab{font-size:16px;font-weight:700}
.desc{color:#93a6bb;font-size:13.5px;margin-top:9px}
.pal{display:flex;align-items:center;gap:8px;margin-top:12px}
.dot{width:20px;height:20px;border-radius:6px;border:1px solid rgba(255,255,255,.18)}
.hex{color:#6d7f95;font-size:12px;margin-left:6px;font-variant-numeric:tabular-nums}
.foot{margin-top:34px;color:#6d7f95;font-size:13.5px;line-height:1.9}
</style></head>
<body>
<h1>🎨 HyperFrames · 10 秒视频配色皮肤预览</h1>
<div class="sub">
共 <b>10 套</b>配色，同一分镜、仅换皮肤。<br>
选用方式：① <code>scenes.json</code> 里写 <code>"skin":"aurora"</code>；② 或构建时传 <code>--skin=aurora</code>；③ 也可在预览页 <code>rsi.html</code> 底部控制条的下拉框实时切换。
</div>
<div class="wrap">
${cards}
</div>
<div class="foot">
皮肤名：${SKINS.map(s => s.k).join(" / ")}<br>
浅色皮肤 <code>paper</code> 采用浅底深字，适合白底/打印/文档场景；其余为深色主题。
</div>
</body></html>`;

mkdirSync(dirname(resolve(outPath)), { recursive: true });
writeFileSync(resolve(outPath), html, "utf8");
console.log(`[gallery] ${resolve(outPath)}`);
console.log(`[gallery] 皮肤 ${SKINS.length} 套 / 每套 ${FRAMES.length} 帧`);
