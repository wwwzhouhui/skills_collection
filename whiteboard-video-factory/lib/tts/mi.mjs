// 小米 MiMo 语音合成（mimo-v2.5-tts）适配层 —— 第三条配音通道（火山 / edge / 小米）。
//
// 端点形态（2026-09-29 全部实测，非照文档猜）：
//   POST {baseUrl}/chat/completions      baseUrl 默认 https://token-plan-cn.xiaomimimo.com/v1
//   Authorization: Bearer <MI_TTS_API_KEY>   （token-plan 的 tp- 开头 Key）
//   { model:"mimo-v2.5-tts",
//     messages:[ 可选 {role:"user", content:"风格指令"}, **必须** {role:"assistant", content:"要朗读的正文"} ],
//     audio:{ voice, format } }
//   → choices[0].message.audio.data = base64 音频
//
// ⚠️ 三条与火山截然不同的规矩，踩过才知道：
//   1) messages **必须含 assistant 角色**，正文放 assistant 的 content 里；只给 user 会报
//      `messages must contain an assistant role for TTS model`。user 消息只当风格指令用。
//   2) **没有语速参数**。顶层 speed、audio.speed、audio.speech_rate 全部被忽略
//      （实测 speed=0.5 与不传返回**字节完全相同**）。要按 config 的 tts.speed 变速，
//      只能自己 ffmpeg atempo 后处理 —— 本文件就是这么做的。
//   3) **不返回逐字时间戳**，audio.transcript 恒为 null，也**没有**流式时间戳事件。
//      所以句子级时间用「标点小句 + 静音检测吸附」还原（见 estimateWords）。
//   另：/audio/speech 与 /tts 都是 404（openresty 的 HTML 404），ASR 模型 mimo-v2.5-asr 也只回文本。
//   voice 只有这九个：mimo_default / 冰糖 / 茉莉 / 苏打 / 白桦 / Mia / Chloe / Milo / Dean
//   format 支持 wav / mp3 / pcm / pcm16（我们固定 wav：24kHz 单声道 16bit，省一次转码）。
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const DEFAULT_BASE = "https://token-plan-cn.xiaomimimo.com/v1";
const DEFAULT_MODEL = "mimo-v2.5-tts";
const DEFAULT_VOICE = "冰糖";
export const MI_VOICES = ["mimo_default", "冰糖", "茉莉", "苏打", "白桦", "Mia", "Chloe", "Milo", "Dean"];

// 时间轴算法的版本号，**改了 estimateWords / detectSilences / clausesOf 就要 +1**。
// 火山的时间戳是引擎给的、跟着音频走；小米这版是**我们算出来的**，所以它必须进缓存键——
// 否则算法改进了、缓存却还命中旧结果，字幕会一直用老的对齐，白白浪费时间还查不出原因。
// v2：停顿区间双端点（前句止于停顿起点、后句起于停顿终点）+ 单调 DP 配对（修掉整链错位一格）。
// v3：顿号不再当小句边界（2026-09-29 实测）。顿号是并列顿开、TTS 在它上面的停顿**弱且不稳**：
//     本期 28 处顿号边界里 10 处在音频里根本没有停顿（≥0.10s 的静音），DP 找不到锚点只能按字数插值，
//     实测把「做 PPT 都行」这类顿号小句的起点推早了 1.16s；而 ，。？！；： 的平均停顿 0.27~0.36s，锚点可靠。
//     去掉顿号后这些并列项并进相邻小句，两端都落在真实停顿上，字幕/高亮时间随之变准（代价：小句变长，
//     句内高亮单元仍是按字数等比切，粒度略粗，但字幕**换行时机**才是一个人最先察觉的）。
export const ALIGN_VERSION = 3;

// 凭证 / 端点 / 音色（config tts.mi.* 与 .env MI_TTS_* 已由 tts-volc.mjs 灌进环境变量）。导出给回显用。
export function resolveMiConfig(voice) {
  const apiKey = process.env.MI_TTS_API_KEY || "";
  if (!apiKey) throw new Error("缺少小米凭证：在 .env 配 MI_TTS_API_KEY（token-plan 的 tp- 开头 Key）");
  const baseUrl = (process.env.MI_TTS_BASE_URL || DEFAULT_BASE).replace(/\/+$/, "");
  const model = process.env.MI_TTS_MODEL || DEFAULT_MODEL;
  // voice 优先用显式传入的（driver 已按引擎挑好），其次环境变量，最后默认。
  const speaker = voice || process.env.MI_TTS_VOICE || DEFAULT_VOICE;
  const style = process.env.MI_TTS_STYLE || "";
  return { apiKey, baseUrl, model, speaker, style };
}

export function getDuration(file) {
  const out = execFileSync("ffprobe", ["-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", file]).toString().trim();
  return parseFloat(out) || 0;
}

// ===== 时间轴还原：标点小句 + 静音吸附 =====
// ⚠️这里的标点集合必须与 lib/captions.cjs 的 PUNCT **逐字一致**（那边用它切原文、切 TTS 词序列后一一配对；
// 我们这里每个小句恰好产出一条 word，两边小句数天然相等 → 配对走"数量一致"分支，时间最准）。
// 改动任一处务必同步另一处，并把上面的 ALIGN_VERSION +1。
// 不含顿号：理由见 ALIGN_VERSION 的注释（顿号处停顿弱且不稳，当边界会引入无锚点小句）。
const norm = (s) => [...s].filter((c) => /[\p{L}\p{N}]/u.test(c)).join("");
function clausesOf(text) {
  return text.replace(/\s+/g, " ").split(/(?<=[，。？！；：])/).map((s) => s.trim()).filter((s) => norm(s).length > 0);
}

// ffmpeg silencedetect 把结果打在 stderr 上。⚠️别用 execFileSync：它退出码 0 时**拿不到 stderr**，
// 会把"有静音"误报成"0 段静音"（我第一版探针就栽在这，白折腾一轮）。
// 阈值 -35dB/0.10s 是**实测选出来的**：拿 5 段真实旁白比"各句语速(字/秒)的变异系数"，越小说明切得越准——
//   -35dB/0.10 → 0.144（最好）  -38/0.08 → 0.152  -40/0.10 → 0.152  -45/0.06 → 0.197  -50/0.03 → 0.344
// 反直觉但已复现：把阈值调灵敏**更差**。多检出的停顿会被下面的 DP 认领，反而把切分带偏；
// 漏检的短停顿只会优雅退化回字数比例，伤害更小。**别凭直觉"调灵敏点试试"。**
function detectSilences(file) {
  const r = spawnSync(
    "ffmpeg",
    ["-nostdin", "-hide_banner", "-i", file, "-af", "silencedetect=noise=-35dB:d=0.10", "-f", "null", "-"],
    { encoding: "utf8" },
  );
  const err = r.stderr || "";
  const out = [];
  let cur = null;
  for (const line of err.split("\n")) {
    const st = /silence_start:\s*([-\d.]+)/.exec(line);
    const en = /silence_end:\s*([-\d.]+)\s*\|\s*silence_duration:\s*([-\d.]+)/.exec(line);
    if (st) cur = parseFloat(st[1]);
    if (en) { out.push({ start: cur, end: parseFloat(en[1]), dur: parseFloat(en[2]) }); cur = null; }
  }
  if (cur !== null) out.push({ start: cur, end: null, dur: null }); // 尾部静音到文件结束：只报了 start
  return out;
}

// 有效发声窗口：TTS 常在首尾留静音，扣掉它再分配时间，首句才不会"提前 0.3s 就在画"。
function speechWindow(duration, sil) {
  let t0 = 0, t1 = duration;
  const lead = sil.find((s) => s.start !== null && s.start <= 0.08);
  if (lead?.end != null && lead.end < duration * 0.5) t0 = lead.end;
  const tail = [...sil].reverse().find((s) => s.end == null || s.end >= duration - 0.08);
  if (tail?.start != null && tail.start > duration * 0.5) t1 = tail.start;
  return t1 - t0 > duration * 0.3 ? [t0, t1] : [0, duration];
}

// 产出 wordList：一个小句一条 {word, startTime, endTime}。
// 先验=按规范化字数比例分配；再把每个小句边界**吸附到真正的停顿区间**（容差随小句长度放宽）。
// 停顿区间用两个端点而不是一个中点，因为两条子句的边界时间需求不同：
//   前一句在**停顿开始**处结束（不把字幕拖进静音）、后一句在**停顿结束**处开始（字幕正好压在起音上）。
// 实测：比例先验已能到 ±0.3s；吸附后 27 个边界平均误差 0.046s。
export function estimateWords(text, duration, sil) {
  const cls = clausesOf(text);
  if (!cls.length) return [];
  const n = cls.length;
  const lens = cls.map((c) => norm(c).length);
  const total = lens.reduce((a, b) => a + b, 0) || 1;
  const [t0, t1] = speechWindow(duration, sil);
  const span = t1 - t0;

  // 先验：按规范化字数比例
  const priors = [];
  let acc = 0;
  for (let i = 0; i < n - 1; i++) { acc += lens[i]; priors.push(t0 + (acc / total) * span); }
  // 每个小句的保底时长——吸附后不能出现 0.05s 的"句子"
  const minDur = lens.map((L) => Math.min(0.22, (L / total) * span * 0.45));
  // 停顿区间（首尾静音不入候选：它们是留白，不是句间停顿）
  const waits = sil.map((s) => (s.start != null ? [s.start, s.end != null ? s.end : t1] : null))
    .filter((w) => w && w[1] > t0 + 0.05 && w[0] < t1 - 0.05)
    .map(([a, b]) => [Math.max(a, t0), Math.min(b, t1)]);
  const distTo = (p, [a, b]) => (p < a ? a - p : p > b ? p - b : 0);
  const tol = priors.map((_, i) => Math.min(1.2, Math.max(0.25, (((lens[i] + lens[i + 1]) / 2 / total) * span) * 0.9)));

  // 单调最优配对（DP）：边界与停顿都按时间有序，一个边界最多认领一段停顿、一段停顿最多给一个边界。
  // ⚠️别改用"按距离贪心"：先验自带 ±0.3s 噪声，某个先验可能正好落进停顿里而抢先认领，
  //   把相邻边界挤到下一段停顿上，**整条链错位一格**——实测出现过"9 个字的句子只分到 0.28s"。
  //   单调约束能从结构上杜绝这种错位。未认领边界的代价记为它的容差 tol，
  //   于是配对条件自然等价于"距离 ≤ 容差"，只是在冲突时取全局最优而非局部最优。
  const m = waits.length;
  const INF = 1e9;
  const dp = Array.from({ length: priors.length + 1 }, () => new Array(m + 1).fill(0));
  const pick = Array.from({ length: priors.length + 1 }, () => new Array(m + 1).fill(""));
  for (let i = 1; i <= priors.length; i++) { dp[i][0] = dp[i - 1][0] + tol[i - 1]; pick[i][0] = "skip"; }
  for (let i = 1; i <= priors.length; i++) {
    for (let j = 1; j <= m; j++) {
      const d = distTo(priors[i - 1], waits[j - 1]);
      let best = dp[i - 1][j] + tol[i - 1], how = "skip";                                   // 这个边界不认领
      if (d <= tol[i - 1] && dp[i - 1][j - 1] + d < best) { best = dp[i - 1][j - 1] + d; how = "match"; }
      if (dp[i][j - 1] < best) { best = dp[i][j - 1]; how = "unused"; }                      // 这段停顿空着
      dp[i][j] = best; pick[i][j] = how;
    }
  }
  const rawA = [...priors], rawB = [...priors];   // 未认领时退化成同一个点（= 字数比例先验）
  for (let i = priors.length, j = m; i > 0 && j > 0;) {
    const how = pick[i][j];
    if (how === "match") { [rawA[i - 1], rawB[i - 1]] = waits[j - 1]; i--; j--; }
    else if (how === "skip") i--;
    else j--;
  }

  // 单调 + 保底时长：clause i 的时长 = rawA[i] - rawB[i-1]，必须 ≥ minDur[i]
  const A = [], B = [];
  let prevEnd = t0;
  for (let i = 0; i < n - 1; i++) {
    const a = Math.max(rawA[i], prevEnd + minDur[i]);
    const need = minDur.slice(i + 1).reduce((x, y) => x + y, 0);   // 给后面所有小句留住保底时长
    const b = Math.min(Math.max(rawB[i], a), Math.max(a, t1 - need));
    A.push(a); B.push(b);
    prevEnd = b;
  }
  const words = [];
  for (let i = 0; i < n; i++) {
    const start = i === 0 ? t0 : B[i - 1];
    const end = i === n - 1 ? t1 : A[i];
    words.push({ word: cls[i], startTime: +start.toFixed(3), endTime: +end.toFixed(3) });
  }
  return words;
}

// ===== 失败诊断 =====
// 小米的报错都挺具体（放在 error.param 里，还会直接列出可选值），但会被非 200 状态码掩盖成
// 一句 HTTP 4xx；这里翻译成"改哪一项"。
export function explainMiFailure(status, raw) {
  let code = "", message = "", param = "";
  try {
    const o = JSON.parse(raw);
    code = o?.error?.code ?? status;
    message = o?.error?.message ?? "";
    param = o?.error?.param ?? "";
  } catch { /* 非 JSON（例如 openresty 的 HTML 404） */ }
  const text = `${message} ${param}`;
  const hints = [];
  if (/Unknown voice/i.test(text)) {
    hints.push(`音色的可用值只有这九个：${MI_VOICES.join(" / ")}（写错一个字符就会报这个）`);
  }
  if (/assistant role/i.test(text)) {
    hints.push("内部结构错误：messages 必须含 assistant 角色且正文放它的 content 里（本仓库已按此发送，出现即说明请求被改写）");
  }
  if (/user message content must not be empty/i.test(text)) {
    hints.push("模型选成了 voicedesign：voice design 模型必须给 user 消息写音色描述，普通合成请用 mimo-v2.5-tts");
  }
  if (/audio must not be empty for voice clone/i.test(text)) {
    hints.push("模型选成了 voiceclone：声音复刻模型要额外传参考音频，普通合成请用 mimo-v2.5-tts");
  }
  if (/only mp3\/flac\/m4a\/wav\/ogg/i.test(text)) {
    hints.push("传的是 ASR 模型（mimo-v2.5-asr）：它只做识别，不做合成");
  }
  if (/Unsupported audio format/i.test(text)) {
    hints.push("format 只能是 wav / mp3 / pcm / pcm16（opus、aac 不支持）");
  }
  if (status === 401 || status === 403 || /api.?key|unauthorized|invalid.*token/i.test(text)) {
    hints.push("凭证问题：核对 .env 的 MI_TTS_API_KEY（token-plan 的 tp- 开头 Key），以及它是否还有余量");
  }
  if (status === 404) {
    hints.push(`baseUrl 或路径不对：小米只有 {baseUrl}/chat/completions 这一个入口（/audio/speech、/tts 都是 404）。当前 baseUrl=${process.env.MI_TTS_BASE_URL || DEFAULT_BASE}`);
  }
  if (status === 429 || /rate.?limit|too many/i.test(text)) {
    hints.push("触发限流：等几秒重试，或减小并发（本仓库是逐段串行合成）");
  }
  return [
    `小米 TTS HTTP ${status}${code && code !== String(status) ? `（code ${code}）` : ""}${message ? `：${message}` : ""}`,
    param && param !== message ? `  详情=${param}` : "",
    raw.trim() ? `  原始响应[:300]=${raw.slice(0, 300)}` : "  原始响应为空（网络被拦？代理/防火墙？）",
    ...hints.map((h) => "  ↳ " + h),
  ].filter(Boolean).join("\n");
}

// atempo 单次只认 0.5~2.0，超出就串联多个（如 3 倍 → atempo=2,atempo=1.5）。
function atempoChain(rate) {
  const parts = [];
  let r = rate;
  while (r > 2) { parts.push(2); r /= 2; }
  while (r < 0.5) { parts.push(0.5); r /= 0.5; }
  parts.push(r);
  return parts.map((v) => `atempo=${v.toFixed(6)}`).join(",");
}

// base64 → 落盘 → 转 44100/立体声 wav（对齐管线其余环节）+ 变速/音量后处理
function toWav(srcBuf, outWav, { speed, loudness }) {
  const magic = srcBuf.subarray(0, 4).toString("latin1");
  const isWav = magic === "RIFF";
  const isMp3 = magic.startsWith("ID3") || (srcBuf[0] === 0xff && (srcBuf[1] & 0xe0) === 0xe0);
  const tmp = outWav.replace(/\.wav$/, isWav ? ".mi.wav" : isMp3 ? ".mi.mp3" : ".mi.pcm");
  fs.writeFileSync(tmp, srcBuf);
  const filters = [];
  if (loudness && loudness !== 1) filters.push(`volume=${loudness}`);
  if (speed && speed !== 1) filters.push(atempoChain(speed));
  const args = ["-nostdin", "-y", "-v", "error"];
  // 裸 PCM 没有头，必须显式告诉 ffmpeg 格式（我们请求的是 wav，落到这里说明响应异常）
  if (!isWav && !isMp3) args.push("-f", "s16le", "-ar", "24000", "-ac", "1");
  args.push("-i", tmp);
  if (filters.length) args.push("-af", filters.join(","));
  args.push("-ar", "44100", "-ac", "2", outWav);
  execFileSync("ffmpeg", args, { stdio: "ignore" });
  fs.rmSync(tmp, { force: true });
}

// 时间轴来源的标签。驱动器和本文件都要用它，导出来共用一份，别各写各的字符串。
export const miAlignLabel = (speed) => (Number(speed) !== 1 ? `silence-estimate@${Number(speed)}x` : "silence-estimate");

// 对一段文本合成配音，返回 { path, duration, words, align }。
// words 是**估算**的句子级时间（小米不给逐字时间戳），align 标出来供上层/文档区分。
export async function synthesizeMi(text, outWav, { voice } = {}) {
  fs.mkdirSync(path.dirname(outWav), { recursive: true });
  const { apiKey, baseUrl, model, speaker, style } = resolveMiConfig(voice);

  const messages = [];
  if (style) messages.push({ role: "user", content: style });
  messages.push({ role: "assistant", content: text });

  const resp = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify({ model, messages, audio: { voice: speaker, format: "wav" } }),
    signal: AbortSignal.timeout(180000),
  });
  const raw = await resp.text();
  if (!resp.ok) throw new Error(explainMiFailure(resp.status, raw));

  let b64 = "";
  try {
    const o = JSON.parse(raw);
    b64 = o?.choices?.[0]?.message?.audio?.data || "";
    if (!b64) throw new Error(explainMiFailure(resp.status, raw));
  } catch (e) {
    if (e.message.includes("小米 TTS")) throw e;
    throw new Error(`小米 TTS 响应解析失败：${raw.slice(0, 300)}`);
  }

  const speed = Number(process.env.MI_TTS_SPEED || 1) || 1;
  const loudness = Number(process.env.MI_TTS_LOUDNESS || 1) || 1;
  toWav(Buffer.from(b64, "base64"), outWav, { speed, loudness });

  // 时间轴必须基于**后处理之后**的音频来量（atempo 改过时长），否则字幕会整体偏。
  const duration = getDuration(outWav);
  const words = estimateWords(text, duration, detectSilences(outWav));
  const align = miAlignLabel(speed);
  return { path: outWav, duration, words, align };
}

export default { synthesizeMi, resolveMiConfig, estimateWords, explainMiFailure, MI_VOICES };

// CLI 自测：node lib/tts/mi.mjs "要合成的文本" [输出.wav]
// ⚠️守卫必须把 argv[1] 转成 file URL 再比：直接拼 `file://${argv[1]}` 在传相对路径时恒为假，
//    脚本会"静默什么都不做"（原 tts.mjs 也踩了同一坑）。
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  try { process.loadEnvFile(path.resolve(import.meta.dirname, "../../.env")); } catch { /* 无 .env 忽略 */ }
  const text = process.argv[2] || "你好，我是小米 MiMo 语音合成。这是第一句，这是第二句。";
  const out = path.resolve(process.argv[3] || "mi-test.wav");
  try {
    const c = resolveMiConfig("");
    console.log(`[mi] 端点 ${c.baseUrl}/chat/completions`);
    console.log(`[mi] 模型 ${c.model} · 音色 ${c.speaker}${c.style ? ` · 风格「${c.style}」` : ""}`);
    const r = await synthesizeMi(text, out, {});
    console.log(`[mi] ✓ ${r.path}`);
    console.log(`[mi]   时长 ${r.duration.toFixed(2)}s · 句子时间 ${r.words.length} 条（${r.align}）`);
    for (const w of r.words) console.log(`[mi]     ${w.startTime.toFixed(2)}-${w.endTime.toFixed(2)}  ${w.word}`);
  } catch (e) {
    console.error(`[mi] ✗ ${e.message}`);
    process.exitCode = 1;
  }
}
