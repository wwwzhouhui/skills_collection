#!/usr/bin/env node
/**
 * build-timeline.mjs — durations.json + scenes.json → src/timeline.ts + src/types.ts + build/subtitles.srt
 *
 * 用法（在视频工程根目录执行）:
 *   node <skill>/scripts/build-timeline.mjs
 *
 * 输入 build/scenes.json（手写，与 DESIGN.md 分镜表一一对应）:
 *   [
 *     {"id": "hook",   "visualMin": 300},             // visualMin = 纯视觉最短帧数（必填，≥0）
 *     {"id": "matrix", "visualMin": 420, "tail": 60}, // tail = 配音结束后额外停留（默认 40，≥0）
 *     {"id": "logo",   "visualMin": 90, "vo": false}  // vo:false = 纯视觉镜头，不占配音段
 *   ]
 *
 * 场景时长 = max(visualMin, 配音帧数 + tail)；VO 段按 scenes.json 顺序逐段消耗 durations.json。
 * 校验: id 唯一且合法、visualMin/tail 数值合法、时长 > 0；<37f 仅警告（fade() 已自适应短场景）。
 */
import {readFileSync, writeFileSync, existsSync, mkdirSync} from "node:fs";

const die = (msg) => { console.error("✗ " + msg); process.exit(1); };
const warn = (msg) => console.error("⚠ " + msg);
if (!existsSync("build/durations.json")) die("缺 build/durations.json —— 先跑 tts.py");
if (!existsSync("build/scenes.json")) die(`缺 build/scenes.json —— 按 DESIGN.md 分镜表誊写，例如:
[
  {"id": "hook", "visualMin": 300},
  {"id": "matrix", "visualMin": 420},
  {"id": "cards", "visualMin": 240}
]`);

const durations = JSON.parse(readFileSync("build/durations.json", "utf8"));
const spec = JSON.parse(readFileSync("build/scenes.json", "utf8"));
const fps = durations.fps ?? 30;
const DEFAULT_TAIL = 40;
const FADE_SAFE = 37; // fade() 需要的最小时长；更短的场景会自动缩短淡入淡出

// ---------- scenes.json 校验 ----------
const idOk = (id) => /^[A-Za-z][A-Za-z0-9_]*$/.test(id);
const numOk = (v) => typeof v === "number" && Number.isFinite(v);
const seen = new Set();
for (const s of spec) {
  if (!idOk(s.id)) die(`场景 id "${s.id}" 不是合法标识符（字母开头，仅字母数字下划线）`);
  if (seen.has(s.id)) die(`场景 id "${s.id}" 重复 —— SHOTS 是键值表，重复 id 会静默覆盖导致时间线错乱`);
  seen.add(s.id);
  if (!("visualMin" in s)) die(`场景 "${s.id}" 缺 visualMin（纯视觉最短帧数，可写 0 表示完全由配音决定）`);
  if (!numOk(s.visualMin) || s.visualMin < 0) die(`场景 "${s.id}" 的 visualMin 必须是 ≥0 的数字`);
  if (s.tail !== undefined && (!numOk(s.tail) || s.tail < 0)) die(`场景 "${s.id}" 的 tail 必须是 ≥0 的数字`);
}

const voScenes = durations.scenes;
let voCursor = 0;
let from = 0;
const shots = [];
const voMap = {}; // id -> 配音段号（1 起）；无配音则不设

for (const s of spec) {
  const hasVo = s.vo !== false;
  let voFrames = 0;
  if (hasVo) {
    if (voCursor >= voScenes.length)
      die(`场景 "${s.id}" 需要配音但 durations.json 只有 ${voScenes.length} 段（检查两文件段数/顺序）`);
    voFrames = voScenes[voCursor].frames;
    voMap[s.id] = voScenes[voCursor].i;
    voCursor++;
  }
  const tail = hasVo ? (s.tail ?? DEFAULT_TAIL) : 0;
  const duration = Math.max(s.visualMin, voFrames + tail);
  if (duration < 1) die(`场景 "${s.id}" 时长为 ${duration}f —— Remotion Sequence 要求 > 0（纯视觉镜头请给 visualMin ≥ 1）`);
  if (duration < FADE_SAFE) warn(`场景 "${s.id}" 仅 ${duration}f（<${FADE_SAFE}），fade() 将自动缩短淡入淡出`);
  shots.push({id: s.id, from, duration, vo: hasVo ? voMap[s.id] : null, voFrames: hasVo ? voFrames : null});
  from += duration;
}
if (voCursor < voScenes.length)
  die(`scenes.json 只消耗了 ${voCursor}/${voScenes.length} 段配音 —— 补齐场景或去掉多余段落`);

const total = from;

// ---------- src/timeline.ts（含 FPS：Composition / spring 一律引用它，勿写死 30） ----------
const shotLines = shots.map((s) => `  ${s.id}: {from: ${s.from}, duration: ${s.duration}},`).join("\n");
const voLines = Object.entries(voMap).map(([k, v]) => `  ${k}: ${v},`).join("\n");
const orderLines = shots.map((s) => `  "${s.id}",`).join("\n");

const ts = `// 由 build-timeline.mjs 生成，勿手改；改稿/改配音后重跑脚本。
// 场景时长 = max(visualMin, 配音帧数 + tail)，改任何输入都会自动重排。
import type {SceneId} from "./types";

export const FPS = ${fps};

export const SHOTS: Record<SceneId, {from: number; duration: number}> = {
${shotLines}
};

// SCENE_ORDER: 场景顺序（组装与 VO 挂载都按它遍历）
export const SCENE_ORDER: SceneId[] = [
${orderLines}
] as const;

// VO_MAP: 有配音的场景 → 配音段号（public/vo/scene{N}.mp3）
export const VO_MAP: Partial<Record<SceneId, number>> = {
${voLines}
};

export const TOTAL_FRAMES = ${total};
`;

// ---------- src/types.ts（每次重写，随场景清单自动更新） ----------
mkdirSync("src", {recursive: true});
writeFileSync("src/types.ts", `// 由 build-timeline.mjs 生成（每次重跑自动更新），勿手改。
export type SceneId = ${shots.map((s) => `"${s.id}"`).join(" | ")};
`);
writeFileSync("src/timeline.ts", ts);

// ---------- build/subtitles.srt（逐句切分：按句长在配音区间内加权估算） ----------
const fmt = (sec) => {
  const ms = Math.round(sec * 1000);
  const h = String(Math.floor(ms / 3600000)).padStart(2, "0");
  const m = String(Math.floor(ms / 60000) % 60).padStart(2, "0");
  const s = String(Math.floor(ms / 1000) % 60).padStart(2, "0");
  const mmm = String(ms % 1000).padStart(3, "0");
  return `${h}:${m}:${s},${mmm}`;
};
const splitSentences = (text) => {
  const parts = text.split(/(?<=[。！？!?；;…])/).map((x) => x.trim()).filter(Boolean);
  return parts.length ? parts : [text];
};
let srt = "";
let n = 0;
for (const shot of shots) {
  if (!shot.vo) continue;
  const sentences = splitSentences(voScenes[shot.vo - 1].text);
  const totalChars = sentences.reduce((a, x) => a + x.length, 0);
  const startMs = (shot.from / fps) * 1000;
  const voMs = (shot.voFrames / fps) * 1000; // 字幕只覆盖配音区间，不含场景尾巴
  let cur = startMs;
  sentences.forEach((sent, idx) => {
    const isLast = idx === sentences.length - 1;
    const end = isLast ? startMs + voMs : cur + (voMs * sent.length) / totalChars;
    n++;
    srt += `${n}\n${fmt(cur / 1000)} --> ${fmt(end / 1000)}\n${sent}\n\n`;
    cur = end;
  });
}
writeFileSync("build/subtitles.srt", srt);

// ---------- 摘要 ----------
console.log("场景  from    时长    配音");
for (const s of shots) {
  console.log(
    String(s.id).padEnd(10) +
    String(s.from).padStart(6) + "f " +
    (s.duration / fps).toFixed(1).padStart(5) + "s  " +
    (s.vo ? `vo${s.vo}` : "—")
  );
}
console.log(`\n✓ 总时长 ${total}f = ${(total / fps).toFixed(1)}s @${fps}fps`);
console.log("✓ src/timeline.ts + src/types.ts 已生成（每次重跑自动覆盖）");
console.log(`✓ build/subtitles.srt 已生成（${n} 条，逐句加权估算；精确逐词对齐请走 voice-to-video 路线）`);
console.log("  下一步: 在 Video.tsx 中实现各场景组件，逐镜头 remotion still 自检");
