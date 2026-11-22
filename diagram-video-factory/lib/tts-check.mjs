// wb voice —— 配音档位自检。
// 三个引擎的"凭证 × 端点 × 音色"任一不匹配，报错都很模糊，出片时才炸很浪费时间。
// 这里先回显档位，再用一句短文本真跑一次合成 → build/_voice-check.wav，试听即知音色对不对。
//   火山：凭证 × 调用域(standard/plan) × 音色，打错域报 45000010 Invalid X-Api-Key
//   小米：凭证 × baseUrl × model × 音色(只有九个可选)，音色写错报 Unknown voice
import fs from "node:fs";
import path from "node:path";

import paths from "./paths.cjs";
const { cfg } = paths;
try { process.loadEnvFile(path.join(paths.ROOT, ".env")); } catch { /* 没有 .env 就只用环境变量 */ }

const ENGINE = process.env.TTS_ENGINE || cfg.tts.engine || "volc";
process.env.TTS_ENGINE = ENGINE;
const SPEED = Number(cfg.tts.speed || 1);
const LOUDNESS = Number(cfg.tts.loudness || 1);
const out = path.join(paths.BUILD_DIR, "_voice-check.wav");
const SAMPLE = "白板讲解视频配音自检，一二三四五六七八九十。";

if (ENGINE === "edge") {
  const e = cfg.tts.edge || {};
  console.log(`engine   edge（本机 edge-tts，免费、不需要凭证）`);
  console.log(`音色     ${e.voice || "zh-CN-YunxiNeural"}`);
  console.log(`解释器   ${e.python || "(PATH 里的 python3 / python)"}`);
  console.log(`语速     ${e.rate || `按 tts.speed=${SPEED} 换算`}`);
  console.log("跑一句 `wb tts <期>` 就是自检。");
  console.log('要换回火山：config.json 的 tts.engine 改 "volc"；换小米：改 "mi"。');
  process.exit(0);
}

if (ENGINE === "mi") {
  const mi = cfg.tts.mi || {};
  if (mi.baseUrl) process.env.MI_TTS_BASE_URL = String(mi.baseUrl);
  if (mi.model) process.env.MI_TTS_MODEL = String(mi.model);
  if (mi.style) process.env.MI_TTS_STYLE = String(mi.style);
  process.env.MI_TTS_SPEED = String(SPEED);
  process.env.MI_TTS_LOUDNESS = String(LOUDNESS);

  const { synthesize } = await import("./tts/tts.mjs");
  const { resolveMiConfig } = await import("./tts/mi.mjs");
  const VOICE = mi.voice || process.env.MI_TTS_VOICE || "";
  let vc;
  try {
    vc = resolveMiConfig(VOICE);
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  console.log(`engine   mi（小米 MiMo）`);
  console.log(`端点     ${vc.baseUrl}/chat/completions`);
  console.log(`模型     ${vc.model}`);
  console.log(`音色     ${vc.speaker} @${SPEED}x${vc.style ? `  风格「${vc.style}」` : ""}`);
  console.log(`时间轴   静音检测估算（小米接口不返回逐字时间戳，与火山不同）`);
  console.log(`变速     ${SPEED !== 1 ? `本地 ffmpeg atempo=${SPEED}（接口无语速参数）` : "原速"}`);
  console.log("—— 试合成一句 ——");
  process.env.FORCE_TTS = "1";   // 自检必须真打一次接口，别吃缓存
  fs.mkdirSync(path.dirname(out), { recursive: true });
  try {
    const r = await synthesize(SAMPLE, out, { voice: VOICE });
    console.log(`✓ ${r.path}`);
    console.log(`  时长 ${r.duration.toFixed(2)}s · 句子时间 ${r.words.length} 条（${r.align}）`);
    for (const w of r.words) console.log(`    ${w.startTime.toFixed(2)}-${w.endTime.toFixed(2)}  ${w.word}`);
    console.log("  试听确认音色；满意就 wb build <期>，换声线改 config.json tts.mi.voice 后重跑本命令。");
  } catch (e) {
    console.error(`✗ ${e.message}`);
    process.exit(1);
  }
  process.exit(0);
}

if (cfg.tts.resourceId) process.env.VOLC_TTS_RESOURCE_ID = cfg.tts.resourceId;
if (cfg.tts.endpoint) process.env.VOLC_TTS_ENDPOINT = String(cfg.tts.endpoint);
process.env.VOLC_TTS_SPEED = String(Math.max(-50, Math.min(100, Math.round((SPEED - 1) * 100))));
if (cfg.tts.style) process.env.VOLC_TTS_STYLE = String(cfg.tts.style);
process.env.FORCE_TTS = "1";   // 自检必须真打一次接口，别吃缓存

const { synthesize, resolveVolcConfig } = await import("./tts/tts.mjs");
const VOICE = cfg.tts.voice || process.env.VOLC_TTS_VOICE || "";
let vc;
try {
  vc = resolveVolcConfig(VOICE);
} catch (e) {
  console.error(`✗ ${e.message}`);
  process.exit(1);
}
console.log(`engine   volc（火山引擎 / 豆包语音合成）`);
console.log(`端点     ${vc.mode} 域  ${vc.url}`);
console.log(`资源     ${vc.resourceId}`);
console.log(`音色     ${vc.speaker} @${SPEED}x${process.env.VOLC_TTS_STYLE ? `  风格「${process.env.VOLC_TTS_STYLE}」` : ""}`);
console.log("—— 试合成一句 ——");

fs.mkdirSync(path.dirname(out), { recursive: true });
try {
  const r = await synthesize(SAMPLE, out, { voice: VOICE });
  console.log(`✓ ${r.path}`);
  console.log(`  时长 ${r.duration.toFixed(2)}s · 逐字时间戳 ${r.words.length} 条`);
  if (!r.words.length) console.log("  ⚠ 没有逐字时间戳：2.0 音色要 enable_subtitle:true（本仓库已开），否则字幕会退化成按字数估时间");
  console.log("  试听确认音色；满意就 wb build <期>，换声线改 config.json tts.voice 后重跑本命令。");
} catch (e) {
  console.error(`✗ ${e.message}`);
  process.exit(1);
}
