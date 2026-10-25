#!/usr/bin/env node
// 文章封面生成脚本：创建文生图任务 -> 轮询 -> 下载 -> 校验尺寸
// 配置：技能根目录 .env（API_KEY 必填，API_BASE/MODEL 可选），首次使用先创建该文件
// 用法:
//   node gen_cover.mjs --prompt-file p.txt --ratio 16:9 --out cover.png
//   node gen_cover.mjs --prompt "..." --size 1536x864 --out cover.png
// 兜底(无Node时手动curl):
//   curl https://image.mlgb7.com/v1/images/generations -H "Content-Type: application/json" \
//     -H "Authorization: Bearer $KEY" \
//     -d '{"model":"gpt-image-2.5","prompt":"...","n":1,"async":true,"response_format":"url","size":"1536x864"}'
//   curl "https://image.mlgb7.com/api/image-tasks?ids=<task_id>" -H "Authorization: Bearer $KEY"
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SKILL_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

function loadEnv() {
  const envPath = path.join(SKILL_DIR, ".env");
  if (!fs.existsSync(envPath)) {
    console.error(`缺少配置文件: ${envPath}`);
    console.error("请创建该文件（UTF-8）并写入以下内容，API_KEY 必填：");
    console.error("API_BASE=https://image.mlgb7.com");
    console.error("API_KEY=<你的中转站 apikey>");
    console.error("MODEL=gpt-image-2.5");
    process.exit(1);
  }
  const env = {};
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m) env[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  if (!env.API_KEY) {
    console.error(`配置不完整: ${envPath} 中缺少 API_KEY（格式见文件内注释）`);
    process.exit(1);
  }
  return env;
}
const ENV = loadEnv();
const API_BASE = (ENV.API_BASE || "https://image.mlgb7.com").replace(/\/+$/, "");
const KEY = ENV.API_KEY;
const MODEL = ENV.MODEL || "gpt-image-2.5";

const RATIO_SIZE = {
  "16:9": "1536x864",
  "9:16": "864x1536",
  "3:4": "864x1152",
  "4:3": "1152x864",
  "1:1": "1024x1024",
};

// ---- 解析参数 ----
const args = process.argv.slice(2);
function arg(name) {
  const i = args.indexOf("--" + name);
  return i >= 0 ? args[i + 1] : undefined;
}
const promptFile = arg("prompt-file");
let prompt = arg("prompt");
if (promptFile) prompt = fs.readFileSync(promptFile, "utf8").trim();
if (!prompt) { console.error("需要 --prompt-file 或 --prompt"); process.exit(1); }
const ratio = (arg("ratio") || "4:3").toLowerCase().replace("x", ":");
const size = arg("size") || RATIO_SIZE[ratio];
if (!size) { console.error(`不支持的比例: ${ratio}，可选: ${Object.keys(RATIO_SIZE).join(" ")}`); process.exit(1); }
let out = arg("out") || `封面_${ratio.replace(":", "x")}_${Date.now()}.png`;
out = out.replace(/\\/g, "/");

const headers = { "Content-Type": "application/json", Authorization: `Bearer ${KEY}` };

// ---- 1. 创建任务 ----
let createJson = null;
for (let attempt = 0; attempt < 2 && !createJson; attempt++) {
  try {
    const res = await fetch(`${API_BASE}/v1/images/generations`, {
      method: "POST", headers,
      body: JSON.stringify({ model: MODEL, prompt, n: 1, async: true, response_format: "url", size }),
    });
    const text = await res.text();
    if (!res.ok) { console.error(`创建任务失败 HTTP ${res.status}: ${text}`); process.exit(2); }
    createJson = JSON.parse(text);
  } catch (e) {
    if (attempt === 1) { console.error(`创建任务网络错误: ${e.message}`); process.exit(2); }
    await new Promise(r => setTimeout(r, 3000));
  }
}
const taskId = createJson.task_id || createJson.id;
if (!taskId) { console.error(`响应中无任务ID: ${JSON.stringify(createJson)}`); process.exit(2); }
console.error(`任务已创建: ${taskId} (size=${size})`);

// ---- 2. 轮询 ----
let result = null, failure = null;
for (let i = 0; i < 60; i++) {
  await new Promise(r => setTimeout(r, i === 0 ? 3000 : 5000));
  let pollJson;
  try {
    const res = await fetch(`${API_BASE}/api/image-tasks?ids=${taskId}`, { headers: { Authorization: `Bearer ${KEY}` } });
    pollJson = await res.json();
  } catch (e) {
    console.error(`轮询#${i} 网络错误: ${e.message}`);
    continue;
  }
  const it = pollJson?.items?.[0];
  if (!it) { console.error(`轮询#${i} 无任务数据: ${JSON.stringify(pollJson).slice(0, 300)}`); failure = "任务不存在或已被清理"; break; }
  console.error(`轮询#${i} status=${it.status} stage=${it.stage_label || ""}`);
  if (it.status === "failed" || it.status === "cancelled") { failure = `任务失败: ${it.error_code || ""} ${it.public_error || ""}`; break; }
  if (it.terminal && it.status === "success" && it.results?.length) { result = it.results[0]; break; }
}
if (!result) {
  console.error(failure || `超时: 5分钟内未完成，task_id=${taskId}，可稍后手动查询 ${API_BASE}/api/image-tasks?ids=${taskId}`);
  process.exit(3);
}
const url = result.url;
if (!url && !result.b64_json) { console.error(`结果中无图片: ${JSON.stringify(result).slice(0, 300)}`); process.exit(3); }

// ---- 3. 保存图片 ----
let buf;
if (url) {
  try {
    const dl = await fetch(url);
    if (!dl.ok) { console.error(`下载失败 HTTP ${dl.status}`); process.exit(4); }
    buf = Buffer.from(await dl.arrayBuffer());
  } catch (e) { console.error(`下载网络错误: ${e.message}`); process.exit(4); }
} else {
  buf = Buffer.from(result.b64_json, "base64");
}
fs.mkdirSync(out.slice(0, out.lastIndexOf("/")), { recursive: true });
fs.writeFileSync(out, buf);

// ---- 4. 校验并输出 ----
let w = result.width, h = result.height, fmt = "unknown";
if (buf.length > 24 && buf.readUInt32BE(12) === 0x49484452) { w = buf.readUInt32BE(16); h = buf.readUInt32BE(20); fmt = "png"; }
else if (buf[0] === 0xff && buf[1] === 0xd8) fmt = "jpeg";
else if (buf.slice(0, 4).toString() === "RIFF" && buf.slice(8, 12).toString() === "WEBP") fmt = "webp";
console.log(JSON.stringify({ ok: true, path: out, format: fmt, width: w, height: h, ratio, task_id: taskId }));
