// TTS 配音层 —— 按 config.json tts.engine 分派：
//   volc(默认) 火山引擎(豆包)语音合成大模型，音色见 .env VOLC_TTS_VOICE / config tts.voice。**下面这一整段都是火山实现**。
//   mi         小米 MiMo（mimo-v2.5-tts），实现在 ./mi.mjs —— 端点/参数规矩与火山完全不同，别混用。
//   say        占位通道（仅验版式用，见下）。
// 每段旁白产出一个 wav, 返回真实时长。时长很关键: 它决定每个分镜在时间轴上的长度(音画同步)。
// 失败就抛错、不回退到别的引擎(保证音色一致); 火山 403 就去续授权/额度, 别拿其它声音顶替。
// 按正文、引擎、端点、音色、参数与 WAV 内容指纹自动复用；FORCE_TTS=1 强制重配。
import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { digest, ttsIdentity, readAudioCache, writeAudioCache } from "./content-cache.mjs";

// 火山有两个**互不相通**的调用域；同一个 Key 打错域会直接 401/403，不是"额度不够"：
//   standard   https://openspeech.bytedance.com/api/v3/tts/unidirectional        控制台直购 / 常规额度
//   plan       https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional   方舟「套餐(plan)」域
// 2026-09-29 实测：控制台发的 ark- 开头 Key 打 standard 报 `45000010 Invalid X-Api-Key`，打 plan 才 HTTP 200 出音频。
// ⚠️ark.cn-beijing.volces.com/api/plan/v3 是方舟**另一套(非 TTS)**入口，TTS 不走它，别拿它当 baseURL 拼路径。
// HTTP 单向接口: 一次性输入文本, 一个请求拿到完整音频(fetch 自动收齐分块, 我们无需流式)。
// 文档: https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3
const VOLC_ENDPOINTS = {
  standard: "https://openspeech.bytedance.com/api/v3/tts/unidirectional",
  plan: "https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional",
};

// 端点选择：VOLC_TTS_ENDPOINT(完整 URL 或 plan/standard) > 按 Key 前缀判定 > standard。
// ark- 是方舟套餐域签发的 Key，只有 plan 路径认它；其余(控制台旧版 AppId/AccessKey 或直购 Key)走 standard。
function resolveEndpoint(apiKey) {
  const raw = String(process.env.VOLC_TTS_ENDPOINT || "").trim();
  if (raw) {
    const named = VOLC_ENDPOINTS[raw.toLowerCase()];
    if (named) return { url: named, mode: raw.toLowerCase() };
    return { url: raw, mode: raw.includes("/plan/") ? "plan" : "custom" };
  }
  const mode = /^ark-/i.test(apiKey || "") ? "plan" : "standard";
  return { url: VOLC_ENDPOINTS[mode], mode };
}

export function getDuration(file) {
  const out = execFileSync("ffprobe", [
    "-v", "quiet", "-show_entries", "format=duration",
    "-of", "csv=p=0", file,
  ]).toString().trim();
  return parseFloat(out) || 0;
}

// mp3 → 44100/立体声 wav(对齐管线其余环节)
function toWav(src, outWav) {
  execFileSync("ffmpeg", ["-y", "-i", src, "-ar", "44100", "-ac", "2", outWav], { stdio: "ignore" });
}

// 从环境变量拼鉴权头与音色(新版控制台 API Key / 旧版 AppId+Token 二选一)。导出给 tts-volc.mjs 回显档位。
export function resolveVolcConfig(voice) {
  // 默认 2.0 资源：官方 2.0 音色(*_uranus_bigtts)配 seed-tts-2.0；1.0 音色配 seed-tts-1.0；声音复刻配 volc.megatts.default。
  const resourceId = process.env.VOLC_TTS_RESOURCE_ID || "seed-tts-2.0";
  const headers = {
    "Content-Type": "application/json",
    "X-Api-Resource-Id": resourceId,
    "X-Api-Connect-Id": randomUUID(),
  };
  let apiKey = "";
  if (process.env.VOLC_TTS_API_KEY) {
    apiKey = process.env.VOLC_TTS_API_KEY;
    headers["X-Api-Key"] = apiKey;
  } else if (process.env.VOLC_TTS_APP_ID && process.env.VOLC_TTS_ACCESS_TOKEN) {
    headers["X-Api-App-Id"] = process.env.VOLC_TTS_APP_ID;
    headers["X-Api-Access-Key"] = process.env.VOLC_TTS_ACCESS_TOKEN;
  } else {
    throw new Error("缺少火山凭证: 在 .env 配 VOLC_TTS_API_KEY(新版控制台) 或 VOLC_TTS_APP_ID+VOLC_TTS_ACCESS_TOKEN(旧版)");
  }
  // shotlist 的 voice 是 macOS 旧值(如 Tingting, 无下划线), 不是火山音色; 仅当像火山音色才采用。
  const speaker = voice && voice.includes("_")
    ? voice
    : (process.env.VOLC_TTS_VOICE || "zh_male_liufei_uranus_bigtts");
  const { url, mode } = resolveEndpoint(apiKey);
  return { headers, speaker, resourceId, url, mode, arkKey: /^ark-/i.test(apiKey) };
}

// 火山流式响应是一串 JSON(每个含 base64 音频片段)。无论 NDJSON 还是 SSE(event:/data:)分隔,
// 都用花括号配平扫出每个顶层 JSON 对象, 避免依赖具体换行/前缀格式。
function extractJsonObjects(text) {
  const objs = [];
  let depth = 0, start = -1, inStr = false, esc = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') inStr = false;
    } else if (c === '"') inStr = true;
    else if (c === "{") { if (depth++ === 0) start = i; }
    else if (c === "}") { if (--depth === 0 && start >= 0) { objs.push(text.slice(start, i + 1)); start = -1; } }
  }
  return objs;
}

// 递归收集逐字时间戳: 火山把它放在 sentence.words, 与音频分片穿插在同一串 JSON 里。
// ⚠️别再丢掉它(2026-08-21 之前 collectAudio 只捞音频, 字幕只能按字数线性估时间 → 断句飘)。
function collectWords(node, out) {
  if (!node || typeof node !== "object") return;
  if (Array.isArray(node.words) && node.words.length) out.push(...node.words);
  for (const v of Object.values(node)) if (v && typeof v === "object") collectWords(v, out);
}

// 递归收集音频: 取任意层级下 key 为 data/audio 的 base64 字符串(火山可能把音频包在 header/payload 内)。
function collectAudio(node, out) {
  if (!node || typeof node !== "object") return;
  for (const [k, v] of Object.entries(node)) {
    if ((k === "data" || k === "audio") && typeof v === "string" && v) out.push(Buffer.from(v, "base64"));
    else if (v && typeof v === "object") collectAudio(v, out);
  }
}

// ⚠️火山把业务错误也塞在 HTTP 200 的 body 里(只有鉴权失败才 401/403)，所以"没拿到音频"时
//   必须回读 code/message 才能说清原因——否则只剩一句"未返回音频"，403/额度/音色不匹配全长得一样。
//   这里把常见错因翻译成可执行的下一步。
function explainFailure(raw, status, { mode, resourceId, speaker, arkKey }) {
  let code = 0, message = "";
  for (const objStr of extractJsonObjects(raw)) {
    let o;
    try { o = JSON.parse(objStr); } catch { continue; }
    const c = o.code ?? o.header?.code;
    if (c && c !== 0 && c !== 20000000) { code = c; message = o.message || o.header?.message || ""; break; }
  }
  const hints = [];
  if (code === 45000010 || /Invalid X-Api-Key/i.test(message)) {
    if (mode === "plan")
      hints.push("域没选错、Key 也是 ark- 套餐 Key，那就是 Key 本身无效或已过期：核对 .env 的 VOLC_TTS_API_KEY 是否完整，或改用旧版 VOLC_TTS_APP_ID + VOLC_TTS_ACCESS_TOKEN");
    else if (arkKey)
      hints.push(`这个 Key 不被 ${mode} 域接受：ark- 开头的套餐 Key 只能走 plan，把 config.json 的 tts.endpoint 设成 "plan"`);
    else
      hints.push(`这个 Key 不被 ${mode} 域接受：确认 Key 是 ${mode} 域签发的（旧版控制台用 VOLC_TTS_APP_ID + VOLC_TTS_ACCESS_TOKEN 两个字段），或改 config.json 的 tts.endpoint`);
  }
  if (code === 45000030 || /not granted/i.test(message))
    hints.push(`${resourceId} 未授权：去火山控制台开通对应服务，或改 tts.resourceId（官方 2.0 音色用 seed-tts-2.0、1.0 用 seed-tts-1.0、声音复刻用 volc.megatts.default）`);
  if (/mismatched with speaker/i.test(message))
    hints.push(`音色 "${speaker}" 不属于 ${resourceId}：seed-tts-2.0 只认 *_uranus_bigtts 家族，且该音色要被这个 Key 授权（可用音色见 references/voices-volc.md）`);
  if (code === 40402003 || /exceed max limit/i.test(message))
    hints.push("提交文本超长：把这一段旁白拆成两段再合成");
  if (/concurrency/i.test(message))
    hints.push("并发超限：先停掉正在跑的其它合成任务再重试");
  const head = status && status !== 200 ? `火山 TTS HTTP ${status}` : `火山 TTS(${mode}) 未返回音频`;
  return [
    head + (code ? `：code ${code} ${message}` : message ? `：${message}` : ""),
    raw.trim() ? `  原始响应[:300]=${raw.slice(0, 300)}` : "  原始响应为空（网络被拦？代理/防火墙？）",
    ...hints.map((h) => "  ↳ " + h),
  ].join("\n");
}


// 对一段文本生成配音, 返回 { path, duration, words }。**只用当前引擎, 失败就抛错(不回退别的引擎)**。
// REUSE_AUDIO 不再跳过内容校验；缓存命中同时恢复本次音频对应的 words。
export async function synthesize(text, outWav, { voice } = {}) {
  fs.mkdirSync(path.dirname(outWav), { recursive: true });
  const key = digest(ttsIdentity(text, voice));
  // 无元数据的旧 WAV 是未验证缓存，不猜测其来源。强制重配用 FORCE_TTS=1。
  const cached = process.env.FORCE_TTS !== '1' && readAudioCache(outWav, key);
  if (cached) return cached;
  const remember = audio => { writeAudioCache(outWav, key, audio); return audio; };
  // ⚠️ 占位通道(2026-09-05 火山全账号 403 时加): TTS_ENGINE=say 用 macOS say 出临时配音, 只为验版式/时间轴,
  //   正式出片必须删掉 wav 换回火山重配。不带逐字时间戳(words=[])。
  if (process.env.TTS_ENGINE === "say") {
    const { execFileSync } = await import("node:child_process");
    const aiff = outWav.replace(/\.wav$/, ".aiff");
    execFileSync("say", ["-v", process.env.SAY_VOICE || "Tingting", "-r", process.env.SAY_RATE || "200", "-o", aiff, text]);
    execFileSync("ffmpeg", ["-nostdin", "-y", "-v", "error", "-i", aiff, "-ar", "24000", "-ac", "1", outWav]);
    fs.rmSync(aiff, { force: true });
    return remember({ path: outWav, duration: getDuration(outWav), words: [] });
  }
  // 小米 MiMo：走 chat/completions，**没有**逐字时间戳，句子级时间由 mi.mjs 用静音检测估算。
  if (process.env.TTS_ENGINE === "mi") {
    const { synthesizeMi } = await import("./mi.mjs");
    return remember(await synthesizeMi(text, outWav, { voice }));
  }
  const cfg = resolveVolcConfig(voice);
  const { headers, speaker } = cfg;

  // 逐字时间戳(sentence.words[{word,startTime,endTime,confidence}]), 两个开关都放 audio_params 里:
  //   enable_timestamp → 仅 TTS 1.0 音色生效(字为 tn 后文本);
  //   enable_subtitle  → TTS 2.0 / ICL 2.0 音色生效(字为原文, 以 TTSSubtitle 事件穿插返回, 可能晚于音频帧)。
  // ⚠️2026-09-14 实测: seed-tts-2.0 + *_uranus_bigtts 只开 enable_timestamp 返回 words=[]; 加 enable_subtitle 后每字一条, 1.2 倍速也准。
  // ⚠️2026-09-29 plan 域复测: timestamp=0/subtitle=1 → 17 words; subtitle=0 → words=0。**要字幕就必须开 enable_subtitle**。
  //   官方文档 https://docs.volcengine.com/docs/DoubaoVoice/HTTPChunkedSSEUnidirectionalStreaming-V3。有了它字幕对齐不再需要 whisper ASR。
  const audioParams = { format: "mp3", sample_rate: 24000, bit_rate: 128000, enable_timestamp: true, enable_subtitle: true };
  const speed = Number(process.env.VOLC_TTS_SPEED || 0); // [-50,100], 0=原速
  if (speed) audioParams.speech_rate = speed;
  const loudness = Number(process.env.VOLC_TTS_LOUDNESS || 0); // [-50,100], 0=原音量
  if (loudness) audioParams.loudness_rate = loudness;

  // 2.0 音色的自然语言风格控制(VOLC_TTS_STYLE / config tts.style, 如"低沉沙哑的深夜电台女主播"):
  // additions 必须是 JSON 序列化字符串, context_texts 只取第一条, 不计字符费。仅 *_uranus_bigtts 家族响应。
  const reqParams = { text, speaker, audio_params: audioParams };
  const style = process.env.VOLC_TTS_STYLE || "";
  if (style) reqParams.additions = JSON.stringify({ context_texts: [style] });

  const resp = await fetch(cfg.url, {
    method: "POST",
    headers,
    body: JSON.stringify({
      user: { uid: "whiteboard-video" },
      req_params: reqParams,
    }),
  });
  const raw = await resp.text();

  const chunks = [];
  const words = [];
  for (const objStr of extractJsonObjects(raw)) {
    let o;
    try { o = JSON.parse(objStr); } catch { continue; }
    collectAudio(o, chunks);
    collectWords(o, words);
  }
  if (!chunks.length) throw new Error(explainFailure(raw, resp.ok ? 200 : resp.status, cfg));

  const mp3 = outWav.replace(/\.wav$/, ".mp3");
  fs.writeFileSync(mp3, Buffer.concat(chunks));
  toWav(mp3, outWav);
  fs.rmSync(mp3, { force: true });
  // words: [{word,startTime,endTime,confidence}] — 逐字对齐, 给字幕分段/卡拉OK高亮用。
  // ⚠️时间戳只描述「这一遍合成的音频」: 火山非确定性(同句两次时长实测差 0.07-0.24s),
  //   拿它去套另一条已存在的 wav 会飘, 必须与音频同一次产出。
  return remember({ path: outWav, duration: getDuration(outWav), words });
}

// CLI 自测凭证: node lib/tts/tts.mjs "要合成的文本" [输出.wav]   （wb voice 也走这里）
// (单跑时 tts-volc.mjs 不会执行, 这里自己加载根目录 .env; config 里的 endpoint/voice 不会生效, 只认环境变量)
// TTS_ENGINE=mi 时直接转给小米通道的自测（它有自己的端点/音色回显）。
// ⚠️守卫要把 argv[1] 转 file URL 再比：直接拼 `file://${argv[1]}` 在传相对路径时恒为假、脚本静默不跑。
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { process.loadEnvFile(path.resolve(import.meta.dirname, "../../.env")); } catch { /* 无 .env 忽略 */ }
  const text = process.argv[2] || "你好，我是语音合成服务。这是一段测试旁白。";
  const out = path.resolve(process.argv[3] || "tts-test.wav");
  if (process.env.TTS_ENGINE === "mi") {
    const { synthesizeMi, resolveMiConfig } = await import("./mi.mjs");
    try {
      const c = resolveMiConfig(process.env.MI_TTS_VOICE || "");
      console.log(`[tts] 小米 ${c.baseUrl}/chat/completions`);
      console.log(`[tts] 模型 ${c.model} · 音色 ${c.speaker}`);
      const r = await synthesizeMi(text, out, {});
      console.log(`[tts] ✓ ${r.path}  时长 ${r.duration.toFixed(2)}s  句子时间 ${r.words.length} 条（${r.align}）`);
    } catch (e) {
      console.error(`[tts] ✗ ${e.message}`);
      process.exitCode = 1;
    }
  } else {
    try {
      const cfg = resolveVolcConfig("");
      console.log(`[tts] 端点 ${cfg.mode} → ${cfg.url}`);
      console.log(`[tts] 资源 ${cfg.resourceId} · 音色 ${cfg.speaker}`);
      const r = await synthesize(text, out, {});
      console.log(`[tts] ✓ ${r.path}  时长 ${r.duration.toFixed(2)}s  逐字 ${r.words.length} 条`);
    } catch (e) {
      console.error(`[tts] ✗ ${e.message}`);
      process.exitCode = 1;
    }
  }
}
