import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import zlib from "node:zlib";

import { CoverError, ensureOutputDirectory, generateCover } from "./gen_cover.mjs";

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const CRC_TABLE = Array.from({ length: 256 }, (_, value) => {
  let crc = value;
  for (let bit = 0; bit < 8; bit++) crc = (crc & 1) ? 0xedb88320 ^ (crc >>> 1) : crc >>> 1;
  return crc >>> 0;
});

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const typeBuffer = Buffer.from(type, "ascii");
  const chunk = Buffer.alloc(data.length + 12);
  chunk.writeUInt32BE(data.length, 0);
  typeBuffer.copy(chunk, 4);
  data.copy(chunk, 8);
  chunk.writeUInt32BE(crc32(Buffer.concat([typeBuffer, data])), data.length + 8);
  return chunk;
}

function pngBuffer(width = 2, height = 1) {
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header[8] = 8;
  header[9] = 6;
  const row = Buffer.alloc(1 + width * 4);
  const pixels = Buffer.concat(Array.from({ length: height }, () => row));
  return Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"),
    pngChunk("IHDR", header),
    pngChunk("IDAT", zlib.deflateSync(pixels)),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

function tempOutput(t, name = "cover.png") {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "article-cover-test-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  return path.join(directory, name);
}

test("GPT 默认模型保持原协议并输出兼容 JSON", async t => {
  const output = tempOutput(t);
  const image = pngBuffer(1536, 864);
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (calls.length === 1) return jsonResponse({ task_id: "gpt-task-1" }, 202);
    return jsonResponse({
      items: [{
        status: "success",
        terminal: true,
        results: [{ b64_json: image.toString("base64") }],
      }],
    });
  };

  const result = await generateCover({
    argv: ["--prompt", " 测试封面 ", "--ratio", "16:9", "--out", output],
    env: { ARTICLE_COVER_API_KEY: "gpt-test-key" },
    fileEnv: {},
    fetchImpl,
    sleep: async () => {},
    log: () => {},
  });

  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "https://image.mlgb7.com/v1/images/generations");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    model: "gpt-image-2.5",
    prompt: "测试封面",
    n: 1,
    async: true,
    response_format: "url",
    size: "1536x864",
  });
  assert.equal(calls[1].url, "https://image.mlgb7.com/api/image-tasks?ids=gpt-task-1");
  assert.deepEqual(result, {
    ok: true,
    path: output.replace(/\\/g, "/"),
    format: "png",
    width: 1536,
    height: 864,
    ratio: "16:9",
    task_id: "gpt-task-1",
    provider: "gpt-gateway",
    model: "gpt-image-2.5",
  });
  assert.deepEqual(fs.readFileSync(output), image);
});

test("旧版自定义 MODEL 仍走 GPT 兼容网关", async t => {
  const output = tempOutput(t);
  const image = pngBuffer();
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    return calls.length === 1
      ? jsonResponse({ id: "custom-model-task" })
      : jsonResponse({ items: [{ status: "success", terminal: true, results: [{ b64_json: image.toString("base64") }] }] });
  };

  const result = await generateCover({
    argv: ["--prompt", "自定义模型", "--out", output],
    env: {},
    fileEnv: { MODEL: "custom-gpt-image", API_KEY: "legacy-key", API_BASE: "https://gateway.example.test" },
    fetchImpl,
    sleep: async () => {},
    log: () => {},
  });

  assert.equal(result.model, "custom-gpt-image");
  assert.equal(result.provider, "gpt-gateway");
  assert.equal(calls[0].url, "https://gateway.example.test/v1/images/generations");
  assert.equal(JSON.parse(calls[0].options.body).model, "custom-gpt-image");
});

test("通用进程 MODEL 不会覆盖技能默认模型", async t => {
  const output = tempOutput(t);
  const image = pngBuffer();
  let submittedModel;
  let calls = 0;
  const fetchImpl = async (_url, options = {}) => {
    calls++;
    if (calls === 1) {
      submittedModel = JSON.parse(options.body).model;
      return jsonResponse({ task_id: "generic-env-model" });
    }
    return jsonResponse({ items: [{ status: "success", terminal: true, results: [{ b64_json: image.toString("base64") }] }] });
  };

  await generateCover({
    argv: ["--prompt", "环境隔离", "--out", output],
    env: { MODEL: "unrelated-model", ARTICLE_COVER_API_KEY: "gpt-test-key" },
    fileEnv: {},
    fetchImpl,
    sleep: async () => {},
    log: () => {},
  });
  assert.equal(submittedModel, "gpt-image-2.5");
});

test("MiniMax 走 ModelScope 异步提交、轮询和首张图片下载", async t => {
  const output = tempOutput(t, "nested/cover.png");
  const image = pngBuffer(760, 1280);
  const calls = [];
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (calls.length === 1) return jsonResponse({ task_id: "ms-task-1" }, 202);
    if (calls.length === 2) return jsonResponse({ task_status: "RUNNING" });
    if (calls.length === 3) return jsonResponse({
      task_status: "SUCCEED",
      output_images: ["https://images.example.test/first.png", "https://images.example.test/second.png"],
    });
    return new Response(image, { status: 200, headers: { "Content-Type": "image/png" } });
  };

  const result = await generateCover({
    argv: [
      "--model", "MiniMax/MiniMax-H3-Image",
      "--prompt", "A golden cat",
      "--ratio", "16:9",
      "--out", output,
    ],
    env: { ARTICLE_COVER_MODELSCOPE_API_KEY: "modelscope-test-key" },
    fileEnv: {},
    fetchImpl,
    sleep: async () => {},
    log: () => {},
  });

  assert.equal(calls.length, 4);
  assert.equal(calls[0].url, "https://api-inference.modelscope.cn/v1/images/generations");
  assert.equal(calls[0].options.method, "POST");
  assert.equal(calls[0].options.headers["Content-Type"], "application/json");
  assert.equal(calls[0].options.headers["X-ModelScope-Async-Mode"], "true");
  assert.equal(calls[0].options.headers.Authorization, "Bearer modelscope-test-key");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    model: "MiniMax/MiniMax-H3-Image",
    prompt: "A golden cat\n请按 16:9 画面比例构图。",
  });
  assert.equal("size" in JSON.parse(calls[0].options.body), false);
  assert.equal(calls[1].url, "https://api-inference.modelscope.cn/v1/tasks/ms-task-1");
  assert.equal(calls[1].options.headers["Content-Type"], "application/json");
  assert.equal(calls[1].options.headers.Authorization, "Bearer modelscope-test-key");
  assert.equal(calls[1].options.headers["X-ModelScope-Task-Type"], "image_generation");
  assert.equal(calls[2].url, calls[1].url);
  assert.equal(calls[3].url, "https://images.example.test/first.png");
  assert.equal(result.provider, "modelscope");
  assert.equal(result.model, "MiniMax/MiniMax-H3-Image");
  assert.equal(result.width, 760);
  assert.equal(result.height, 1280);
  assert.deepEqual(fs.readFileSync(output), image);
});

test("只要求当前所选模型对应的密钥", async t => {
  const gptOutput = tempOutput(t, "gpt.png");
  const minimaxOutput = tempOutput(t, "minimax.png");
  const image = pngBuffer();

  const gptFetch = async (_url, options = {}) => options.method === "POST"
    ? jsonResponse({ task_id: "gpt-key-test" })
    : jsonResponse({ items: [{ status: "success", terminal: true, results: [{ b64_json: image.toString("base64") }] }] });
  await generateCover({
    argv: ["--prompt", "GPT", "--out", gptOutput],
    env: { ARTICLE_COVER_API_KEY: "gpt-only" },
    fileEnv: {},
    fetchImpl: gptFetch,
    sleep: async () => {},
    log: () => {},
  });

  let call = 0;
  const minimaxFetch = async () => {
    call++;
    if (call === 1) return jsonResponse({ task_id: "ms-key-test" });
    if (call === 2) return jsonResponse({ task_status: "SUCCEED", output_images: ["https://images.example.test/key.png"] });
    return new Response(image, { status: 200 });
  };
  await generateCover({
    argv: ["--model", "MiniMax/MiniMax-H3-Image", "--prompt", "MiniMax", "--out", minimaxOutput],
    env: { ARTICLE_COVER_MODELSCOPE_API_KEY: "modelscope-only" },
    fileEnv: {},
    fetchImpl: minimaxFetch,
    sleep: async () => {},
    log: () => {},
  });
});

test("ModelScope FAILED 返回任务错误并立即停止", async t => {
  const output = tempOutput(t);
  let calls = 0;
  const fetchImpl = async () => {
    calls++;
    return calls === 1
      ? jsonResponse({ task_id: "ms-failed" })
      : jsonResponse({ task_status: "FAILED", message: "generation rejected" });
  };

  await assert.rejects(
    generateCover({
      argv: ["--model", "MiniMax/MiniMax-H3-Image", "--prompt", "测试", "--out", output],
      env: { ARTICLE_COVER_MODELSCOPE_API_KEY: "modelscope-test-key" },
      fileEnv: {},
      fetchImpl,
      sleep: async () => {},
      log: () => {},
    }),
    error => error instanceof CoverError && error.exitCode === 3 && /generation rejected/.test(error.message),
  );
  assert.equal(calls, 2);
  assert.equal(fs.existsSync(output), false);
});

test("创建任务网络结果不明确时不会自动重复提交且不可安全重试", async () => {
  let createCalls = 0;
  const fetchImpl = async () => {
    createCalls++;
    throw new Error("connection reset after send");
  };

  await assert.rejects(
    generateCover({
      argv: ["--model", "MiniMax/MiniMax-H3-Image", "--prompt", "测试"],
      env: { ARTICLE_COVER_MODELSCOPE_API_KEY: "modelscope-test-key" },
      fileEnv: {},
      fetchImpl,
      sleep: async () => {},
      log: () => {},
    }),
    error => error instanceof CoverError && error.exitCode === 2 && error.safeToRetry === false,
  );
  assert.equal(createCalls, 1);
});

test("轮询响应体读取错误会查询同一任务而不创建新任务", async t => {
  const output = tempOutput(t);
  const image = pngBuffer();
  let createCalls = 0;
  let pollCalls = 0;
  const fetchImpl = async (url, options = {}) => {
    if (options.method === "POST") {
      createCalls++;
      return jsonResponse({ task_id: "poll-body-error" });
    }
    if (String(url).includes("/v1/tasks/")) {
      pollCalls++;
      if (pollCalls === 1) return { ok: true, status: 200, text: async () => { throw new Error("body interrupted"); } };
      return jsonResponse({ task_status: "SUCCEED", output_images: ["https://images.example.test/recovered.png"] });
    }
    return new Response(image, { status: 200 });
  };

  await generateCover({
    argv: ["--model", "MiniMax/MiniMax-H3-Image", "--prompt", "测试", "--out", output],
    env: { ARTICLE_COVER_MODELSCOPE_API_KEY: "modelscope-test-key" },
    fileEnv: {},
    fetchImpl,
    sleep: async () => {},
    log: () => {},
  });
  assert.equal(createCalls, 1);
  assert.equal(pollCalls, 2);
});

test("未知、重复或缺值参数不会发起网络请求", async () => {
  const cases = [
    ["--promtp", "测试"],
    ["--prompt", "测试", "--prompt", "重复"],
    ["--prompt", "--out", "cover.png"],
    ["--model"],
    ["--prompt", "   "],
    ["--prompt", "测试", "--ratio", "2:1"],
    ["--prompt", "测试", "--size", "wide"],
  ];

  for (const argv of cases) {
    let calls = 0;
    await assert.rejects(
      generateCover({
        argv,
        env: { ARTICLE_COVER_API_KEY: "gpt-test-key" },
        fileEnv: {},
        fetchImpl: async () => { calls++; return jsonResponse({}); },
      }),
      error => error instanceof CoverError && error.exitCode === 1,
    );
    assert.equal(calls, 0);
  }
});

test("端点覆盖与密钥必须来自同一配置来源", async () => {
  let calls = 0;
  await assert.rejects(
    generateCover({
      argv: ["--prompt", "测试"],
      env: { ARTICLE_COVER_API_BASE: "https://unexpected.example.test" },
      fileEnv: { ARTICLE_COVER_API_KEY: "local-secret" },
      fetchImpl: async () => { calls++; return jsonResponse({}); },
    }),
    error => error instanceof CoverError && error.exitCode === 1 && /同一配置来源/.test(error.message),
  );
  assert.equal(calls, 0);
});

test("HTTP 200 错误页不会写成图片", async t => {
  const output = tempOutput(t);
  let call = 0;
  const fetchImpl = async () => {
    call++;
    if (call === 1) return jsonResponse({ task_id: "html-download" });
    if (call === 2) return jsonResponse({ task_status: "SUCCEED", output_images: ["https://images.example.test/error"] });
    return new Response("<html>upstream error</html>", { status: 200, headers: { "Content-Type": "text/html" } });
  };

  await assert.rejects(
    generateCover({
      argv: ["--model", "MiniMax/MiniMax-H3-Image", "--prompt", "测试", "--out", output],
      env: { ARTICLE_COVER_MODELSCOPE_API_KEY: "modelscope-test-key" },
      fileEnv: {},
      fetchImpl,
      sleep: async () => {},
      log: () => {},
    }),
    error => error instanceof CoverError && error.exitCode === 4 && /不是有效/.test(error.message),
  );
  assert.equal(fs.existsSync(output), false);
});

test("纯文件名输出不会创建错误目录", async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "article-cover-cwd-test-"));
  const previousCwd = process.cwd();
  process.chdir(directory);
  t.after(() => {
    process.chdir(previousCwd);
    fs.rmSync(directory, { recursive: true, force: true });
  });

  const image = pngBuffer();
  let call = 0;
  const fetchImpl = async () => {
    call++;
    return call === 1
      ? jsonResponse({ task_id: "filename-test" })
      : jsonResponse({ items: [{ status: "success", terminal: true, results: [{ b64_json: image.toString("base64") }] }] });
  };

  const result = await generateCover({
    argv: ["--prompt", "测试", "--out", "cover.png"],
    env: { ARTICLE_COVER_API_KEY: "gpt-test-key" },
    fileEnv: {},
    fetchImpl,
    sleep: async () => {},
    log: () => {},
  });

  ensureOutputDirectory("cover.png");
  assert.equal(result.path, "cover.png");
  assert.equal(fs.existsSync(path.join(directory, "cover.png")), true);
  assert.equal(fs.existsSync(path.join(directory, "cover.pn")), false);
});
