// 旁白生成驱动器 —— 按 config.json tts.engine 选通道（volc 火山 / mi 小米 MiMo / say 占位），
// 逐场景合成 <project>/audio/<scene>.wav + <scene>.json（duration / segmentStarts / wordList，
// 渲染器按段起点对齐画图节奏、captions.cjs 按 wordList 排字幕）。
// 用法：node lib/tts-volc.mjs <projectDir> [scene...]   FORCE_TTS=1 强制重配
import fs from "node:fs";
import path from "node:path";

import paths from "./paths.cjs";
const { cfg, projectPaths } = paths;
const P = projectPaths(process.argv[2] || ".");
const only = process.argv.slice(3);

try { process.loadEnvFile(path.join(paths.ROOT, ".env")); } catch { /* 没有 .env 就只用环境变量 */ }

const ENGINE = process.env.TTS_ENGINE || cfg.tts.engine || "volc";
process.env.TTS_ENGINE = ENGINE;

// 语速/音量：config 里填的是**倍率**（1=原速，1.2 推荐），两个引擎的落点不同：
//   火山：映射到 speech_rate / loudness_rate（[-50,100] 的增量，原生合成，不改时长结构）
//   小米：API 根本没有语速参数 → 只能自己 ffmpeg atempo / volume 后处理（见 lib/tts/mi.mjs）
const SPEED = Number(cfg.tts.speed || 1);
const LOUDNESS = Number(cfg.tts.loudness || 1);

let VC;   // 回显用的档位信息
let ALIGN; // 时间轴来源的兜底标签（小米=估算，其余=引擎原生）
if (ENGINE === "mi") {
  const mi = cfg.tts.mi || {};
  if (mi.baseUrl) process.env.MI_TTS_BASE_URL = String(mi.baseUrl);
  if (mi.model) process.env.MI_TTS_MODEL = String(mi.model);
  if (mi.style) process.env.MI_TTS_STYLE = String(mi.style);
  process.env.MI_TTS_SPEED = String(SPEED);
  process.env.MI_TTS_LOUDNESS = String(LOUDNESS);
} else {
  if (cfg.tts.resourceId) process.env.VOLC_TTS_RESOURCE_ID = cfg.tts.resourceId;
  // 调用域：config tts.endpoint = "plan" | "standard" | 完整 URL；留空则由 tts.mjs 按 Key 前缀判定（ark- → plan）。
  // ⚠️火山两个域互不相通，打错域报 45000010 Invalid X-Api-Key（不是额度问题）。2026-09-29 实测。
  if (cfg.tts.endpoint) process.env.VOLC_TTS_ENDPOINT = String(cfg.tts.endpoint);
  process.env.VOLC_TTS_SPEED = String(Math.max(-50, Math.min(100, Math.round((SPEED - 1) * 100))));
  process.env.VOLC_TTS_LOUDNESS = String(Math.max(-50, Math.min(100, Math.round((LOUDNESS - 1) * 100))));
  if (cfg.tts.style) process.env.VOLC_TTS_STYLE = String(cfg.tts.style);
}
process.env.FORCE_TTS = process.env.FORCE_TTS || "0";

const { synthesize, resolveVolcConfig } = await import("./tts/tts.mjs");

// 每个引擎有自己的音色字段（火山 cfg.tts.voice / 小米 cfg.tts.mi.voice / edge cfg.tts.edge.voice），
// 别互相顶替——shots 里的旧值（Tingting、*_bigtts）到小米那边是无效音色。
let VOICE;
if (ENGINE === "mi") {
  const { resolveMiConfig, miAlignLabel } = await import("./tts/mi.mjs");
  VOICE = (cfg.tts.mi || {}).voice || process.env.MI_TTS_VOICE;
  if (!VOICE) throw new Error("没有音色：在 config.json tts.mi.voice 或 .env MI_TTS_VOICE 填小米音色（可用：mimo_default/冰糖/茉莉/苏打/白桦/Mia/Chloe/Milo/Dean）");
  VC = { ...resolveMiConfig(VOICE), mode: "mi" };
  ALIGN = miAlignLabel(SPEED);
  console.log(`[tts] 小米 MiMo · ${VC.model} · ${VC.speaker} @${SPEED}x${VC.style ? ` · 风格「${VC.style}」` : ""}`);
  console.log(`[tts] 端点 ${VC.baseUrl}/chat/completions  ·  ${SPEED !== 1 ? "语速由本地 atempo 后处理" : "原速"}  ·  时间轴=静音检测估算`);
} else {
  VOICE = cfg.tts.voice || process.env.VOLC_TTS_VOICE;
  if (!VOICE) throw new Error("没有音色：在 .env 填 VOLC_TTS_VOICE，或在 config.json tts.voice 填音色 ID");
  // 先解析一次档位：凭证缺失/音色没配在这里就报，别等进了场景循环才炸。
  VC = resolveVolcConfig(VOICE);
  console.log(`[tts] 火山 ${VC.mode} 域 · ${VC.resourceId} · ${VC.speaker} @${SPEED}x`);
  console.log(`[tts] 端点 ${VC.url}`);
}

const norm = (s) => [...s].filter((c) => /[\p{L}\p{N}]/u.test(c)).join("");
const scenes = JSON.parse(fs.readFileSync(P.script));
fs.mkdirSync(P.audio, { recursive: true });

// 重试只对"偶发"故障有意义(半段音频、网络抖动)。凭证/授权/音色这类错误重试 4 次只是浪费时间，
// 而且会把真正的报错刷掉——命中就直接抛给用户。429 是限流，值得重试，故意不收进来。
const HARD_FAIL = /code 4\d{7}|Invalid X-Api-Key|not granted|mismatched with speaker|exceed max limit|缺少火山凭证|缺少小米凭证|小米 TTS HTTP 4(0[0134])|Unknown voice|Param Incorrect|没有音色/;
for (const sc of scenes) {
  if (only.length && !only.includes(sc.name)) continue;
  const full = sc.segments.join("");
  const wav = path.join(P.audio, `${sc.name}.wav`);
  const need = norm(full).length;
  let r, tries = 0;
  while (true) {
    try {
      r = await synthesize(full, wav, { voice: VOICE });
      const got = r.words.reduce((n, w) => n + norm(w.word).length, 0);
      if (got >= need * 0.85) break;
      // 半段音频：按字数校验，不够就强制重配
      console.log(`  truncated ${sc.name}: ${got}/${need} chars, retry`);
      process.env.FORCE_TTS = "1";
    } catch (e) {
      const msg = String(e.message || e);
      if (HARD_FAIL.test(msg)) throw new Error(`${sc.name} 配音失败：\n  ${msg.split("\n").join("\n  ")}`);
      console.log("  retry", sc.name, msg.split("\n")[0].slice(0, 120));
    }
    if (++tries >= 4) throw new Error("TTS failed: " + sc.name);
  }
  process.env.FORCE_TTS = "0";
  // 逐字时间 → 每个旁白段的起始秒
  let acc = 0; const posTime = [];
  for (const w of r.words) { posTime.push([acc, w.startTime]); acc += norm(w.word).length; }
  const starts = []; let p = 0;
  for (const seg of sc.segments) { starts.push(p); p += norm(seg).length; }
  const segStarts = starts.map((sp) => { let best = 0; for (const [cp, t] of posTime) { if (cp <= sp) best = t; else break; } return best; });
  segStarts[0] = 0;
  fs.writeFileSync(path.join(P.audio, `${sc.name}.json`), JSON.stringify({ name: sc.name, duration: r.duration, segmentStarts: segStarts, segments: sc.segments, voice: VOICE, words: r.words.length, normChars: p,
  // align: 时间轴来源。火山是引擎返回的逐字时间戳(native)；小米没有，是静音检测估算(silence-estimate)。
  // ⚠️不能只写 `r.align || "native"`：缓存命中时 align 是历史字段，早期写下的缓存里没有它，
  //   那样小米的每一幕都会被标成 native、日志也会印成"逐字"，和 references/voices-mi.md 说的正好相反。
  //   所以按引擎推一个兜底值（小米的时间轴只可能是估算，因为接口压根不给时间戳）。
  align: ALIGN || "native", engine: ENGINE,
  wordList: r.words.map((w) => ({ w: w.word, s: +w.startTime.toFixed(3), e: +w.endTime.toFixed(3) })) }, null, 1));
  // 逐字条目数 ≠ 正文字数：一个条目可能是多字（如 "MCP，" → 3 字），所以 逐字<正文 是正常的。
  // 小米的条目是**一个小句一条**，说"逐字"会误导（它的 20 条其实覆盖 74 个字）。
  const unit = (r.align || ALIGN) === "native" ? "逐字" : "句子";
  console.log(`${sc.name}: ${r.duration.toFixed(1)}s @${SPEED}x  starts=${segStarts.map((t) => t.toFixed(1)).join(",")}  ${unit}=${r.words.length}条/${p}字`);
}
