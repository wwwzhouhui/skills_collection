#!/usr/bin/env node
// 文章封面生成脚本：选择模型 -> 创建任务 -> 轮询 -> 下载 -> 校验图片
// 用法:
//   node gen_cover.mjs --prompt-file p.txt --ratio 16:9 --out cover.png
//   node gen_cover.mjs --model MiniMax/MiniMax-H3-Image --prompt "..." --ratio 16:9 --out cover.png
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SKILL_DIR = path.dirname(path.dirname(SCRIPT_PATH));
const GPT_MODEL = "gpt-image-2.5";
const MINIMAX_MODEL = "MiniMax/MiniMax-H3-Image";
const ARG_NAMES = new Set(["prompt-file", "prompt", "ratio", "size", "out", "model"]);

const RATIO_SIZE = {
  "16:9": "1536x864",
  "9:16": "864x1536",
  "3:4": "864x1152",
  "4:3": "1152x864",
  "1:1": "1024x1024",
};

const PNG_SIGNATURE = Buffer.from("89504e470d0a1a0a", "hex");
const JPEG_SOF_MARKERS = new Set([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf]);

export class CoverError extends Error {
  constructor(message, exitCode, safeToRetry = false) {
    super(message);
    this.exitCode = exitCode;
    this.safeToRetry = safeToRetry;
  }
}

function hasOwn(source, key) {
  return Object.prototype.hasOwnProperty.call(source, key);
}

function cleanValue(value) {
  return typeof value === "string" ? value.trim() : "";
}

function loadEnvFile() {
  const envPath = path.join(SKILL_DIR, ".env");
  if (!fs.existsSync(envPath)) return {};

  const env = {};
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (match) env[match[1]] = match[2].replace(/^["']|["']$/g, "");
  }
  return env;
}

export function parseArgs(args) {
  const options = {};
  for (let index = 0; index < args.length; index += 2) {
    const token = args[index];
    if (!token?.startsWith("--") || !ARG_NAMES.has(token.slice(2))) {
      throw new CoverError(`不支持的参数: ${token || "(空)"}`, 1);
    }
    const name = token.slice(2);
    if (hasOwn(options, name)) throw new CoverError(`参数重复: --${name}`, 1);

    const value = args[index + 1];
    if (value === undefined || value.startsWith("--") || !value.trim()) {
      throw new CoverError(`参数缺少值: --${name}`, 1);
    }
    options[name] = value;
  }
  return options;
}

function readPrompt(options) {
  if (hasOwn(options, "prompt-file") && hasOwn(options, "prompt")) {
    throw new CoverError("--prompt-file 与 --prompt 只能使用一个", 1);
  }

  if (hasOwn(options, "prompt-file")) {
    try {
      const prompt = fs.readFileSync(options["prompt-file"], "utf8").trim();
      if (!prompt) throw new CoverError("提示词文件为空", 1);
      return prompt;
    } catch (error) {
      if (error instanceof CoverError) throw error;
      throw new CoverError(`读取提示词文件失败: ${error.message}`, 1);
    }
  }

  const prompt = cleanValue(options.prompt);
  if (!prompt) throw new CoverError("需要 --prompt-file 或 --prompt", 1);
  return prompt;
}

function selectModel(options, runtimeEnv, fileEnv) {
  return cleanValue(options.model)
    || cleanValue(runtimeEnv.ARTICLE_COVER_MODEL)
    || cleanValue(fileEnv.ARTICLE_COVER_MODEL)
    || cleanValue(fileEnv.MODEL)
    || GPT_MODEL;
}

function configGroup(source, keyName, baseName, defaultBase) {
  const used = hasOwn(source, keyName) || hasOwn(source, baseName);
  if (!used) return null;

  const apiKey = cleanValue(source[keyName]);
  if (!apiKey) {
    throw new CoverError(`配置了 ${baseName} 时必须在同一配置来源设置 ${keyName}，不允许与其他来源的密钥混用`, 1);
  }
  return {
    apiKey,
    baseUrl: (cleanValue(source[baseName]) || defaultBase).replace(/\/+$/, ""),
  };
}

function resolveProviderConfig(runtimeEnv, fileEnv, spec) {
  const sources = [
    [runtimeEnv, spec.namespacedKey, spec.namespacedBase],
    [runtimeEnv, spec.legacyKey, spec.legacyBase],
    [fileEnv, spec.namespacedKey, spec.namespacedBase],
    [fileEnv, spec.legacyKey, spec.legacyBase],
  ];
  for (const [source, keyName, baseName] of sources) {
    const config = configGroup(source, keyName, baseName, spec.defaultBase);
    if (config) return config;
  }
  throw new CoverError(`缺少 ${spec.label} 配置: 请在技能目录 .env 或当前进程环境变量中设置 ${spec.namespacedKey}（兼容 ${spec.legacyKey}）`, 1);
}

function selectProvider(model, runtimeEnv, fileEnv) {
  if (model === MINIMAX_MODEL) {
    return {
      name: "modelscope",
      ...resolveProviderConfig(runtimeEnv, fileEnv, {
        label: "ModelScope",
        namespacedKey: "ARTICLE_COVER_MODELSCOPE_API_KEY",
        namespacedBase: "ARTICLE_COVER_MODELSCOPE_API_BASE",
        legacyKey: "MODELSCOPE_API_KEY",
        legacyBase: "MODELSCOPE_API_BASE",
        defaultBase: "https://api-inference.modelscope.cn",
      }),
    };
  }

  return {
    name: "gpt-gateway",
    ...resolveProviderConfig(runtimeEnv, fileEnv, {
      label: "GPT",
      namespacedKey: "ARTICLE_COVER_API_KEY",
      namespacedBase: "ARTICLE_COVER_API_BASE",
      legacyKey: "API_KEY",
      legacyBase: "API_BASE",
      defaultBase: "https://image.mlgb7.com",
    }),
  };
}

async function requestJson(fetchImpl, url, options, label, exitCode, safeToRetry = false) {
  let response;
  let text;
  try {
    response = await fetchImpl(url, options);
    text = await response.text();
  } catch (error) {
    throw new CoverError(`${label}网络错误: ${error.message}`, exitCode, safeToRetry);
  }

  if (!response.ok) throw new CoverError(`${label}失败 HTTP ${response.status}: ${text}`, exitCode);
  try {
    return JSON.parse(text);
  } catch {
    throw new CoverError(`${label}返回的不是有效 JSON: ${text.slice(0, 300)}`, exitCode);
  }
}

async function createGptTask({ fetchImpl, provider, model, prompt, size }) {
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${provider.apiKey}` };
  const data = await requestJson(fetchImpl, `${provider.baseUrl}/v1/images/generations`, {
    method: "POST",
    headers,
    body: JSON.stringify({ model, prompt, n: 1, async: true, response_format: "url", size }),
  }, "创建任务", 2);
  const taskId = data.task_id || data.id;
  if (!taskId) throw new CoverError(`响应中无任务ID: ${JSON.stringify(data).slice(0, 300)}`, 2);
  return taskId;
}

async function pollGptTask({ fetchImpl, sleep, log, provider, taskId, maxPolls }) {
  const headers = { Authorization: `Bearer ${provider.apiKey}` };
  for (let index = 0; index < maxPolls; index++) {
    await sleep(index === 0 ? 3000 : 5000);
    let data;
    try {
      data = await requestJson(
        fetchImpl,
        `${provider.baseUrl}/api/image-tasks?ids=${encodeURIComponent(taskId)}`,
        { headers },
        `轮询#${index}`,
        3,
        true,
      );
    } catch (error) {
      if (error.safeToRetry) {
        log(error.message);
        continue;
      }
      throw error;
    }

    const item = data?.items?.[0];
    if (!item) throw new CoverError(`轮询#${index} 无任务数据: ${JSON.stringify(data).slice(0, 300)}`, 3);
    log(`轮询#${index} status=${item.status} stage=${item.stage_label || ""}`);
    if (item.status === "failed" || item.status === "cancelled") {
      throw new CoverError(`任务失败: ${item.error_code || ""} ${item.public_error || ""}`.trim(), 3);
    }
    if (item.terminal && item.status === "success" && item.results?.length) return item.results[0];
  }
  throw new CoverError(`超时: 5分钟内未完成，task_id=${taskId}，可稍后手动查询 ${provider.baseUrl}/api/image-tasks?ids=${taskId}`, 3);
}

async function createModelScopeTask({ fetchImpl, provider, model, prompt, ratio }) {
  const headers = {
    Authorization: `Bearer ${provider.apiKey}`,
    "Content-Type": "application/json",
    "X-ModelScope-Async-Mode": "true",
  };
  const data = await requestJson(fetchImpl, `${provider.baseUrl}/v1/images/generations`, {
    method: "POST",
    headers,
    body: JSON.stringify({ model, prompt: `${prompt}\n请按 ${ratio} 画面比例构图。` }),
  }, "创建任务", 2);
  if (!data.task_id) throw new CoverError(`响应中无任务ID: ${JSON.stringify(data).slice(0, 300)}`, 2);
  return data.task_id;
}

async function pollModelScopeTask({ fetchImpl, sleep, log, provider, taskId, maxPolls }) {
  const headers = {
    Authorization: `Bearer ${provider.apiKey}`,
    "Content-Type": "application/json",
    "X-ModelScope-Task-Type": "image_generation",
  };
  for (let index = 0; index < maxPolls; index++) {
    await sleep(index === 0 ? 3000 : 5000);
    let data;
    try {
      data = await requestJson(
        fetchImpl,
        `${provider.baseUrl}/v1/tasks/${encodeURIComponent(taskId)}`,
        { headers },
        `轮询#${index}`,
        3,
        true,
      );
    } catch (error) {
      if (error.safeToRetry) {
        log(error.message);
        continue;
      }
      throw error;
    }

    log(`轮询#${index} status=${data.task_status || "unknown"}`);
    if (data.task_status === "FAILED") {
      throw new CoverError(`任务失败: ${data.message || data.error || "ModelScope 返回 FAILED"}`, 3);
    }
    if (data.task_status === "SUCCEED") {
      const url = data.output_images?.[0];
      if (!url) throw new CoverError(`任务成功但无图片地址: ${JSON.stringify(data).slice(0, 300)}`, 3);
      return { url };
    }
  }
  throw new CoverError(`超时: 5分钟内未完成，task_id=${taskId}，可稍后手动查询 ${provider.baseUrl}/v1/tasks/${taskId}`, 3);
}

async function downloadImage(fetchImpl, result) {
  if (result.url) {
    try {
      const response = await fetchImpl(result.url);
      if (!response.ok) throw new CoverError(`下载失败 HTTP ${response.status}`, 4);
      return Buffer.from(await response.arrayBuffer());
    } catch (error) {
      if (error instanceof CoverError) throw error;
      throw new CoverError(`下载网络错误: ${error.message}`, 4);
    }
  }
  if (result.b64_json) return Buffer.from(result.b64_json, "base64");
  throw new CoverError(`结果中无图片: ${JSON.stringify(result).slice(0, 300)}`, 3);
}

function inspectPng(buffer) {
  if (buffer.length < 45 || !buffer.subarray(0, 8).equals(PNG_SIGNATURE)) return null;

  let offset = 8;
  let width = null;
  let height = null;
  let sawIdat = false;
  let sawIend = false;
  let chunkIndex = 0;
  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.subarray(offset + 4, offset + 8).toString("ascii");
    const dataStart = offset + 8;
    const next = dataStart + length + 4;
    if (next > buffer.length) return null;

    if (chunkIndex === 0) {
      if (type !== "IHDR" || length !== 13) return null;
      width = buffer.readUInt32BE(dataStart);
      height = buffer.readUInt32BE(dataStart + 4);
      if (!width || !height) return null;
    } else if (type === "IDAT") {
      sawIdat = true;
    } else if (type === "IEND") {
      if (length !== 0) return null;
      sawIend = true;
      break;
    }

    offset = next;
    chunkIndex++;
  }
  return sawIdat && sawIend ? { format: "png", width, height } : null;
}

function inspectJpeg(buffer) {
  if (buffer.length < 10 || buffer[0] !== 0xff || buffer[1] !== 0xd8) return null;
  if (buffer[buffer.length - 2] !== 0xff || buffer[buffer.length - 1] !== 0xd9) return null;

  let offset = 2;
  while (offset + 4 <= buffer.length) {
    while (offset < buffer.length && buffer[offset] === 0xff) offset++;
    const marker = buffer[offset++];
    if (marker === 0xd9 || marker === 0xda) break;
    if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
    if (offset + 2 > buffer.length) return null;

    const length = buffer.readUInt16BE(offset);
    if (length < 2 || offset + length > buffer.length) return null;
    if (JPEG_SOF_MARKERS.has(marker)) {
      if (length < 7) return null;
      const height = buffer.readUInt16BE(offset + 3);
      const width = buffer.readUInt16BE(offset + 5);
      return width && height ? { format: "jpeg", width, height } : null;
    }
    offset += length;
  }
  return null;
}

function readUInt24LE(buffer, offset) {
  return buffer[offset] | (buffer[offset + 1] << 8) | (buffer[offset + 2] << 16);
}

function inspectWebp(buffer) {
  if (buffer.length < 25 || buffer.subarray(0, 4).toString() !== "RIFF" || buffer.subarray(8, 12).toString() !== "WEBP") return null;
  const declaredLength = buffer.readUInt32LE(4) + 8;
  const chunkLength = buffer.readUInt32LE(16);
  if (declaredLength > buffer.length || 20 + chunkLength > declaredLength) return null;

  const chunkType = buffer.subarray(12, 16).toString();
  if (chunkType === "VP8X" && chunkLength >= 10 && buffer.length >= 30) {
    return { format: "webp", width: readUInt24LE(buffer, 24) + 1, height: readUInt24LE(buffer, 27) + 1 };
  }
  if (chunkType === "VP8L" && chunkLength >= 5 && buffer.length >= 25 && buffer[20] === 0x2f) {
    const bits = buffer.readUInt32LE(21);
    return { format: "webp", width: (bits & 0x3fff) + 1, height: ((bits >>> 14) & 0x3fff) + 1 };
  }
  if (chunkType === "VP8 " && chunkLength >= 10 && buffer.length >= 30
      && buffer[23] === 0x9d && buffer[24] === 0x01 && buffer[25] === 0x2a) {
    return { format: "webp", width: buffer.readUInt16LE(26) & 0x3fff, height: buffer.readUInt16LE(28) & 0x3fff };
  }
  return null;
}

export function inspectImage(buffer, fallback = {}) {
  const detected = inspectPng(buffer) || inspectJpeg(buffer) || inspectWebp(buffer);
  if (!detected) return { format: "unknown", width: null, height: null };
  return {
    format: detected.format,
    width: detected.width ?? fallback.width ?? null,
    height: detected.height ?? fallback.height ?? null,
  };
}

export function ensureOutputDirectory(outputPath) {
  const directory = path.dirname(outputPath);
  if (directory !== ".") fs.mkdirSync(directory, { recursive: true });
}

export async function generateCover({
  argv = process.argv.slice(2),
  env = process.env,
  fileEnv,
  fetchImpl = globalThis.fetch,
  sleep = ms => new Promise(resolve => setTimeout(resolve, ms)),
  log = message => console.error(message),
  maxPolls = 60,
} = {}) {
  const options = parseArgs(argv);
  const localEnv = fileEnv ?? loadEnvFile();
  const prompt = readPrompt(options);
  const ratio = (cleanValue(options.ratio) || "4:3").toLowerCase().replace("x", ":");
  const customSize = cleanValue(options.size).toLowerCase();
  if (customSize && !/^[1-9]\d*x[1-9]\d*$/.test(customSize)) {
    throw new CoverError(`无效的尺寸: ${options.size}，格式应为 WIDTHxHEIGHT`, 1);
  }
  const size = customSize || RATIO_SIZE[ratio];
  if (!size) {
    throw new CoverError(`不支持的比例: ${ratio}，可选: ${Object.keys(RATIO_SIZE).join(" ")}`, 1);
  }

  const model = selectModel(options, env, localEnv);
  if (model === MINIMAX_MODEL && hasOwn(options, "size")) {
    throw new CoverError("MiniMax-H3-Image 的 ModelScope 接口未确认支持 --size，请改用 --ratio", 1);
  }
  const provider = selectProvider(model, env, localEnv);
  let outputPath = cleanValue(options.out) || `封面_${ratio.replace(":", "x")}_${Date.now()}.png`;
  outputPath = outputPath.replace(/\\/g, "/");

  let taskId;
  let result;
  if (provider.name === "modelscope") {
    taskId = await createModelScopeTask({ fetchImpl, provider, model, prompt, ratio });
    log(`任务已创建: ${taskId} (model=${model}, ratio=${ratio})`);
    result = await pollModelScopeTask({ fetchImpl, sleep, log, provider, taskId, maxPolls });
  } else {
    taskId = await createGptTask({ fetchImpl, provider, model, prompt, size });
    log(`任务已创建: ${taskId} (model=${model}, size=${size})`);
    result = await pollGptTask({ fetchImpl, sleep, log, provider, taskId, maxPolls });
  }

  const buffer = await downloadImage(fetchImpl, result);
  const image = inspectImage(buffer, result);
  if (image.format === "unknown") throw new CoverError("下载结果不是有效的 PNG、JPEG 或 WebP 图片，已拒绝写入文件", 4);

  ensureOutputDirectory(outputPath);
  fs.writeFileSync(outputPath, buffer);
  return {
    ok: true,
    path: outputPath,
    format: image.format,
    width: image.width,
    height: image.height,
    ratio,
    task_id: taskId,
    provider: provider.name,
    model,
  };
}

async function main() {
  try {
    console.log(JSON.stringify(await generateCover()));
  } catch (error) {
    console.error(error instanceof CoverError ? error.message : `未预期错误: ${error.message}`);
    process.exitCode = error instanceof CoverError ? error.exitCode : 1;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(SCRIPT_PATH)) await main();
