// 混 BGM（闪避配方）：BGM 裁剪循环，说话时 ×speak、间隙 ×gap，缓坡过渡，尾部淡出。
// 输入 work/out/master.mp4 → 输出 outputs/final.mp4（后台目录）。没有配乐文件时直接出无配乐成片
// 用法：node lib/mix-bgm.mjs <projectDir> [gain]      BGM=/path/x.mp3 可临时换曲
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";

import paths from "./paths.cjs";
const { projectPaths } = paths;
const cfg = paths.cfg.bgm;
const P = projectPaths(process.argv[2] || ".");
const IN = path.join(P.out, "master.mp4");
const OUT = P.final; // 成片落在后台 outputs/，旁白稿里放文件链接
fs.mkdirSync(path.dirname(OUT), { recursive: true });
const GAIN = Number(process.argv[3] || cfg.gain);
const { speak: SPEAK, gap: GAP, rampSeconds: RAMP, tailFadeSeconds: TAIL } = cfg;
const SR = 48000;

// 配乐来源两选一：**单曲**（bgm.file；临时换曲 `BGM=路径`）或**播放列表**（bgm.playlist；临时换用 BGM_PLAYLIST='[{...}]'）。
// 为什么要有 playlist：一首 2~3 分钟的曲子配 20 分钟的片子要循环十几次，一听就出戏。
// 列表里几首按顺序拼成一整段，再整体循环——段落变长、重复感立刻降下来。
// 条目形如 { "file": "assets/bgm-1.mp3", "trim": [0, 90], "gain": 0.9 }；file 相对仓库根，支持 ~，trim 省略即整首。
const probeDuration = (f) => Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).toString().trim());
function normTrack(raw) {
  const it = typeof raw === "string" ? { file: raw } : raw && typeof raw === "object" ? raw : {};
  if (!it.file) return null;
  return { file: paths.expand(it.file), trim: Array.isArray(it.trim) && it.trim.length === 2 ? it.trim : null, gain: Number(it.gain || 1) };
}
function wantedList() {
  const raw = process.env.BGM_PLAYLIST != null ? process.env.BGM_PLAYLIST : cfg.playlist;
  if (raw == null || raw === "") return [];
  let arr = raw;
  if (typeof arr === "string") { try { arr = JSON.parse(arr); } catch { arr = [arr]; } }
  return (Array.isArray(arr) ? arr : [arr]).map(normTrack).filter(Boolean);
}
const wanted = wantedList();
const tracks = [];
for (const t of wanted) { if (fs.existsSync(t.file)) tracks.push(t); else console.warn(`  ⚠ 配乐不存在，跳过：${t.file}`); }
if (!tracks.length) {
  if (wanted.length) console.warn("  ⚠ bgm.playlist 里的配乐都找不到，回退到 bgm.file");
  const single = paths.expand(process.env.BGM || cfg.file || "assets/bgm.mp3");
  // ⚠️ cfg.trim 默认是空数组 []，而空数组是**真值** —— 直接当 trim 用会得到 atrim=undefined:NaN。
  //    只有长度恰好是 2 的数组才算有效裁剪区间。
  const trim = Array.isArray(cfg.trim) && cfg.trim.length === 2 ? cfg.trim : null;
  if (fs.existsSync(single)) tracks.push({ file: single, trim, gain: 1 });
  else {
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", IN, "-c", "copy", "-movflags", "+faststart", OUT]);
    console.log(`没找到配乐，已出无配乐成片：${OUT}（放一首无版权音乐到 assets/bgm.mp3，或改 config.json 的 bgm.file / bgm.playlist 再跑 wb mix）`);
    process.exit(0);
  }
}
// 裁段区间与"拼接后总长"：单首就是它自己的 trim，多首是各段之和（aloop 要用这个长度做循环单元）
for (const t of tracks) {
  const len = probeDuration(t.file);
  if (!Number.isFinite(len) || len <= 0) { console.error(`读不出配乐时长（ffprobe 返回 ${len}）：${t.file}`); process.exit(1); }
  const from = t.trim ? t.trim[0] : 0;
  const to = t.trim ? Math.min(t.trim[1], len) : len;
  if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) { console.error(`配乐裁剪区间无效：${t.file} trim=${JSON.stringify(t.trim)}（时长 ${len.toFixed(2)}s）`); process.exit(1); }
  t.from = from; t.to = to;
}
const loopLen = tracks.reduce((s, t) => s + (t.to - t.from), 0);
if (loopLen <= 0) { console.error("配乐裁剪后长度为 0，检查 bgm.trim / playlist 的 trim"); process.exit(1); }

// 1. 旁白轨 → 单声道 f32
const narr = path.join(P.audio, "_narration.f32");
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", IN, "-vn", "-ac", "1", "-ar", String(SR), "-f", "f32le", narr]);
const buf = fs.readFileSync(narr);
const pcm = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
const n = pcm.length, dur = n / SR;

// 2. 10ms 窗 RMS → 说话掩码（-38dBFS 以上算说话，两侧各扩 120ms 补气口）
const win = SR / 100, frames = Math.ceil(n / win);
const speaking = new Uint8Array(frames);
for (let f = 0; f < frames; f++) {
  let s = 0, c = 0;
  for (let i = f * win; i < Math.min(n, (f + 1) * win); i++) { s += pcm[i] * pcm[i]; c++; }
  speaking[f] = c && 10 * Math.log10(s / c + 1e-12) > -38 ? 1 : 0;
}
const dil = new Uint8Array(frames), pad = 12;
for (let f = 0; f < frames; f++) if (speaking[f]) for (let k = Math.max(0, f - pad); k <= Math.min(frames - 1, f + pad); k++) dil[k] = 1;

// 3. 目标电平 → 缓坡（移动平均）→ 头尾淡入淡出 → 立体声 f32 包络
const target = new Float32Array(frames);
for (let f = 0; f < frames; f++) target[f] = (dil[f] ? SPEAK : GAP) * GAIN;
const rampF = Math.round(RAMP * 100), env = new Float32Array(frames);
for (let f = 0; f < frames; f++) {
  let s = 0, c = 0;
  for (let k = Math.max(0, f - rampF); k <= Math.min(frames - 1, f + rampF); k++) { s += target[k]; c++; }
  env[f] = s / c;
}
const out = new Float32Array(n * 2);
for (let i = 0; i < n; i++) {
  const t = i / SR;
  let v = env[Math.min(frames - 1, Math.floor(i / win))];
  if (t > dur - TAIL) v *= Math.max(0, (dur - t) / TAIL);
  if (t < 1.5) v *= t / 1.5;
  out[i * 2] = v; out[i * 2 + 1] = v;
}
const envPath = path.join(P.audio, "_bgm-env.f32");
fs.writeFileSync(envPath, Buffer.from(out.buffer));
const spk = dil.reduce((a, b) => a + b, 0) / frames;
const bgmLabel = tracks.length === 1
  ? `${path.basename(tracks[0].file)}${tracks[0].trim ? `[${tracks[0].from}~${tracks[0].to}]` : ""}`
  : `${tracks.length} 首拼接（${tracks.map((t) => path.basename(t.file)).join(" + ")}）→ 单段 ${loopLen.toFixed(1)}s`;
console.log(`旁白 ${dur.toFixed(1)}s，说话占比 ${(spk * 100).toFixed(0)}%，BGM ${bgmLabel} 电平：说话 ${(SPEAK * GAIN).toFixed(3)} / 间隙 ${(GAP * GAIN).toFixed(3)}`);

// 4. BGM 各段裁剪 →（多首才拼接）→ 整体循环 × 包络，再与旁白叠加。
//    单首走原来的单链（回归安全）；多首先用 concat 拼成 [cat] 再当循环单元。
const chains = tracks.map((t, k) =>
  `[${k + 1}:a]aformat=sample_fmts=fltp:sample_rates=${SR}:channel_layouts=stereo,atrim=${t.from}:${t.to},asetpts=N/SR/TB${t.gain !== 1 ? `,volume=${t.gain}` : ""}[t${k}]`);
const loop = `aloop=loop=-1:size=${loopLen * SR},atrim=0:${dur.toFixed(3)},asetpts=N/SR/TB[bgm]`;
const bgmChain = tracks.length > 1
  ? `${tracks.map((_, k) => `[t${k}]`).join("")}concat=n=${tracks.length}:v=0:a=1[cat];[cat]${loop}`
  : `[t0]${loop}`;
execFileSync("ffmpeg", ["-y", "-loglevel", "error",
  "-i", IN,
  ...tracks.flatMap((t) => ["-i", t.file]),
  "-f", "f32le", "-ar", String(SR), "-ac", "2", "-i", envPath,
  "-filter_complex",
  chains.join(";") + ";" + bgmChain + ";" +
  `[bgm][${tracks.length + 1}:a]amultiply[duck];` +
  `[0:a]aformat=sample_fmts=fltp:sample_rates=${SR}:channel_layouts=stereo[v];` +
  `[v][duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]`,
  "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT]);
fs.rmSync(narr, { force: true }); fs.rmSync(envPath, { force: true });
console.log("final:", OUT);
