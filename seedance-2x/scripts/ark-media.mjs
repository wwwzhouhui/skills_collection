#!/usr/bin/env node
/**
 * ark-media.mjs — 火山方舟 Seedance 2.x 视频 / Seedream 图片 命令行封装
 * 零依赖（Node 18+ 自带 fetch），不需要 npm install。
 *
 * 用法见 --help。
 */

import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const SKILL_ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_BASE = 'https://ark.cn-beijing.volces.com/api/v3';

let BASE = (process.env.ARK_BASE_URL || DEFAULT_BASE).replace(/\/$/, '');
let KEY = process.env.ARK_API_KEY;

/** 读技能根目录或当前目录的 .env，只补 ARK_*，不覆盖已存在的环境变量 */
async function loadEnv() {
  for (const file of [join(SKILL_ROOT, '.env'), join(process.cwd(), '.env')]) {
    let text;
    try {
      text = await readFile(file, 'utf8');
    } catch {
      continue;
    }
    for (const line of text.split(/\r?\n/)) {
      const kv = /^\s*(ARK_[A-Z_]+)\s*=\s*(.*)$/.exec(line);
      if (!kv) continue;
      const value = kv[2].trim().replace(/^["']|["']$/g, '');
      if (value && process.env[kv[1]] === undefined) process.env[kv[1]] = value;
    }
    break;
  }
  BASE = (process.env.ARK_BASE_URL || DEFAULT_BASE).replace(/\/$/, '');
  KEY = process.env.ARK_API_KEY;
}

const IMG_MIME = {
  '.png': 'png', '.jpg': 'jpeg', '.jpeg': 'jpeg', '.webp': 'webp',
  '.bmp': 'bmp', '.tif': 'tiff', '.tiff': 'tiff', '.gif': 'gif',
  '.heic': 'heic', '.heif': 'heif',
};

const REPEATABLE = new Set(['ref', 'ref-img', 'ref-video', 'ref-audio']);
const FLAGS = new Set(['dry-run', 'draft', 'watermark', 'no-watermark', 'no-audio', 'return-last-frame', 'help']);
const VALUED = new Set([
  'model', 'out', 'timeout', 'interval', 'prompt', 'size', 'n',
  'output-format', 'response-format', 'first', 'last', 'task-type',
  'res', 'ratio', 'dur', 'draft-from',
]);
const IMG_OPTS = new Set([
  'model', 'out', 'timeout', 'interval', 'dry-run', 'help',
  'prompt', 'ref', 'size', 'n', 'output-format', 'response-format', 'no-watermark',
]);
const VID_OPTS = new Set([
  'model', 'out', 'timeout', 'interval', 'dry-run', 'help',
  'prompt', 'first', 'last', 'ref-img', 'ref-video', 'ref-audio', 'task-type',
  'res', 'ratio', 'dur', 'no-audio', 'watermark', 'output-format',
  'draft', 'draft-from', 'return-last-frame',
]);
const TASK_OPTS = new Set(['out', 'timeout', 'interval', 'help']);
const MULTI_IMAGE = /doubao-seedream-(?:5-0-lite-|5-0-260128|4-5-|4-0-)/;

/** 参数与命令不匹配时直接拒绝：静默忽略等于让用户以为参数生效了还照常扣费 */
function checkOpts(cmd, opts) {
  const allowed = cmd === 'img' ? IMG_OPTS : cmd === 'vid' ? VID_OPTS : TASK_OPTS;
  const bad = Object.keys(opts).filter((k) => !allowed.has(k));
  if (bad.length) {
    fail(`${cmd} 不支持 ${bad.map((k) => `--${k}`).join('、')}\n  ${cmd} 可用参数见 --help`);
  }
}

const HELP = `ark-media.mjs — Seedance 2.5/2.0 视频 + Seedream 图片

用法:
  node ark-media.mjs img  --prompt "<描述>" [选项]
  node ark-media.mjs vid  --prompt "<描述>" [选项]
  node ark-media.mjs task <taskId> [--out <dir>]

公共选项:
  --model <id>        模型 ID（默认 img=doubao-seedream-5-5-261028, vid=doubao-seedance-2-5-260628）
  --out <dir>         产出目录（默认 ./ark-out）
  --dry-run           只打印请求体，不发请求、不花钱（无 key 也能跑）
  --timeout <秒>      轮询总超时（默认 1800）
  --interval <秒>     轮询间隔（默认 10）

图片 (img):
  --prompt <text>     必填
  --ref <路径|URL>    参考图，可重复；本地图片自动转 base64
  --size <档位|像素>  1K/1.5K/2K 或 2048x2048，默认 2K
  --n <数量>          多图（仅 5.0 lite / 4.5 / 4.0 支持）
  --output-format     jpeg / png
  --response-format   url（默认，24h 有效）/ b64_json
  --no-watermark      关掉"AI生成"水印（默认是开的）

视频 (vid):
  --prompt <text>     必填（--draft-from 时可省）
  --first <路径|URL>  首帧
  --last  <路径|URL>  尾帧（须同时给 --first）
  --ref-img <路径|URL>      参考图，可重复
  --ref-video <URL>         参考视频，可重复（仅 URL）
  --ref-audio <URL>         参考音频，可重复（仅 URL）
  --task-type <t>     auto / reference / edit / extend（仅 2.5）
  --res <r>           480p/720p/1080p/4k（默认 720p）
  --ratio <r>         16:9/4:3/1:1/3:4/9:16/21:9/adaptive（默认 adaptive）
  --dur <秒>          时长，-1 为自动；2.5 支持 4-30，2.0 支持 4-15
  --no-audio          不出音频（接口默认 generate_audio=true）
  --watermark         打"AI生成"水印（视频默认不打）
  --draft             出 480p 试片，返回 draft 任务 ID
  --draft-from <id>   用 draft 任务出正式片
  --return-last-frame 额外返回尾帧（可接下一个镜头首帧）
`;

function fail(msg) {
  console.error(`\x1b[31m错误: ${msg}\x1b[0m`);
  process.exit(2);
}

function note(msg) {
  console.error(`\x1b[33m注意: ${msg}\x1b[0m`);
}

function parseArgs(argv) {
  const opts = {};
  const pos = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) { pos.push(a); continue; }
    const key = a.slice(2);
    if (REPEATABLE.has(key)) {
      const v = argv[++i];
      if (v === undefined) fail(`--${key} 需要参数值`);
      (opts[key] = opts[key] || []).push(v);
    } else if (FLAGS.has(key)) {
      opts[key] = true;
    } else if (VALUED.has(key)) {
      const v = argv[++i];
      if (v === undefined) fail(`--${key} 需要参数值`);
      opts[key] = v;
    } else {
      fail(`未知参数 --${key}（--help 看可用参数）。拒绝静默忽略，避免参数没生效却照常扣费。`);
    }
  }
  return { opts, pos };
}

function need(opts, name) {
  const v = opts[name];
  if (v === undefined || v === '') fail(`缺少 --${name}`);
  return v;
}

/** 本地图片转 data URL；URL / asset:// / data: 原样返回 */
async function toImageRef(value, dry) {
  if (/^(https?:\/\/|asset:\/\/|data:)/i.test(value)) return value;
  const ext = extname(value).toLowerCase();
  const mime = IMG_MIME[ext];
  if (!mime) fail(`不支持的图片格式: ${value}（支持 ${Object.keys(IMG_MIME).join(' ')}）`);
  if (dry) return `data:image/${mime};base64,<<本地文件 ${value}>>`;
  let buf;
  try {
    buf = await readFile(value);
  } catch {
    fail(`读不到文件: ${value}`);
  }
  if (buf.length > 30 * 1024 * 1024) fail(`图片超过 30MB: ${value}`);
  return `data:image/${mime};base64,${buf.toString('base64')}`;
}

function requireUrl(value, kind) {
  if (!/^https?:\/\//i.test(value)) {
    fail(`${kind} 只接受公网 URL，收到本地路径: ${value}\n  本脚本不做文件上传。请先把素材放到可访问的地址，或改用图片形式。`);
  }
  return value;
}

/** 按模型 ID 推断能力边界 */
function caps(model) {
  if (/seedance-2-5-flash/.test(model)) return { fam: '2.5f', res: ['480p', '720p'], dur: [4, 30], mov: false, draft: false };
  if (/seedance-2-5/.test(model)) return { fam: '2.5', res: ['480p', '720p', '1080p', '4k'], dur: [4, 30], mov: true, draft: true };
  if (/seedance-2-0-(fast|mini)/.test(model)) return { fam: '2.0f', res: ['480p', '720p'], dur: [4, 15], mov: false, draft: false };
  if (/seedance-2-0/.test(model)) return { fam: '2.0', res: ['480p', '720p', '1080p', '4k'], dur: [4, 15], mov: false, draft: false };
  if (/seedance-1-0/.test(model)) return { fam: '1.0', res: ['480p', '720p', '1080p'], dur: [2, 12], mov: false, draft: false };
  return { fam: '?', res: ['480p', '720p', '1080p', '4k'], dur: [4, 30], mov: true, draft: false };
}

async function buildImageBody(opts, dry) {
  const model = opts.model || 'doubao-seedream-5-5-261028';
  const body = { model, prompt: need(opts, 'prompt') };

  const refs = opts.ref || [];
  if (refs.length === 1) body.image = await toImageRef(refs[0], dry);
  if (refs.length > 1) body.image = await Promise.all(refs.map((r) => toImageRef(r, dry)));

  body.size = opts.size || '2K';
  body.response_format = opts['response-format'] || 'url';
  body.watermark = !opts['no-watermark'];
  if (opts['output-format']) body.output_format = opts['output-format'];

  const n = Number(opts.n || 1);
  if (n > 1) {
    if (!MULTI_IMAGE.test(model)) {
      fail(`${model} 一次只出一张图。要一次多图只能用 5.0 lite / 4.5 / 4.0（均已标即将下线），建议改为多次调用。`);
    }
    body.sequential_image_generation = 'auto';
  }
  return { body, model };
}

async function buildVideoBody(opts, dry) {
  const model = opts.model || 'doubao-seedance-2-5-260628';
  const c = caps(model);
  const content = [];

  if (opts['draft-from']) {
    content.push({ type: 'draft_task', draft_task: { id: opts['draft-from'] } });
    if (opts.prompt) content.push({ type: 'text', text: opts.prompt });
  } else {
    content.push({ type: 'text', text: need(opts, 'prompt') });
  }

  const first = opts.first ? await toImageRef(opts.first, dry) : null;
  const last = opts.last ? await toImageRef(opts.last, dry) : null;
  const refImgs = await Promise.all((opts['ref-img'] || []).map((r) => toImageRef(r, dry)));
  const refVids = (opts['ref-video'] || []).map((v) => requireUrl(v, '参考视频'));
  const refAuds = (opts['ref-audio'] || []).map((a) => requireUrl(a, '参考音频'));

  if (last && !first) fail('给了 --last 就必须同时给 --first');
  if ((first || last) && refImgs.length) {
    fail('首帧/首尾帧与参考图是互斥模式，不能同时给 --first/--last 和 --ref-img');
  }
  if ((first || last) && (refVids.length || refAuds.length)) {
    fail('首帧/首尾帧模式不能混入参考视频或参考音频');
  }
  if (c.fam.startsWith('2.0') && refAuds.length && !refImgs.length && !refVids.length) {
    fail('Seedance 2.0 系列不支持只给音频参考，必须同时给参考图或参考视频');
  }

  if (first) content.push({ type: 'image_url', image_url: { url: first }, role: 'first_frame' });
  if (last) content.push({ type: 'image_url', image_url: { url: last }, role: 'last_frame' });
  for (const u of refImgs) content.push({ type: 'image_url', image_url: { url: u }, role: 'reference_image' });
  for (const u of refVids) content.push({ type: 'video_url', video_url: { url: u }, role: 'reference_video' });
  for (const u of refAuds) content.push({ type: 'audio_url', audio_url: { url: u }, role: 'reference_audio' });

  const body = { model, content };

  // 分辨率
  let res = (opts.res || (opts.draft ? '480p' : '720p')).toLowerCase();
  if (opts.draft) {
    if (!c.draft) fail(`${model} 不支持 draft 试片（仅 Seedance 2.5 支持，flash 不支持）`);
    if (res !== '480p') fail(`draft 试片只能 480p，收到 ${res}`);
  }
  if (!c.res.includes(res)) fail(`${model} 不支持 ${res}，可选: ${c.res.join(' / ')}`);
  body.resolution = res;

  // 比例
  let ratio = (opts.ratio || 'adaptive').toLowerCase();
  const frameMode = Boolean(first || last);
  const taskType = opts['task-type'];
  if (frameMode && ratio !== 'adaptive') {
    note(`首帧/首尾帧模式要求 ratio=adaptive，已从 ${ratio} 自动改为 adaptive`);
    ratio = 'adaptive';
  }
  if (taskType === 'edit' && ratio !== 'adaptive') {
    note(`edit 模式要求 ratio=adaptive，已从 ${ratio} 自动改为 adaptive`);
    ratio = 'adaptive';
  }
  if (taskType === 'extend' && ratio !== 'adaptive') {
    note(`extend 模式要求 ratio=adaptive，已从 ${ratio} 自动改为 adaptive`);
    ratio = 'adaptive';
  }
  body.ratio = ratio;

  // 时长
  if (!opts['draft-from']) {
    let dur = opts.dur === undefined ? -1 : Number(opts.dur);
    if (!Number.isFinite(dur)) fail(`--dur 需要数字，收到 ${opts.dur}`);
    if (taskType === 'edit' && dur !== -1) {
      note('edit 模式要求 duration=-1，已自动改为 -1');
      dur = -1;
    }
    if (dur !== -1 && (dur < c.dur[0] || dur > c.dur[1])) {
      fail(`${model} 的时长范围是 ${c.dur[0]}-${c.dur[1]} 秒或 -1，收到 ${dur}`);
    }
    body.duration = dur;
  }

  // 任务类型（仅 2.5）
  if (taskType) {
    if (c.fam !== '2.5') fail(`omni_reference_task_type 只有 Seedance 2.5 支持，${model} 不支持`);
    if (!['auto', 'reference', 'edit', 'extend'].includes(taskType)) {
      fail(`--task-type 只能是 auto / reference / edit / extend`);
    }
    if ((taskType === 'edit' || taskType === 'extend') && !refVids.length) {
      fail(`${taskType} 模式必须至少给一个 --ref-video`);
    }
    body.omni_reference_task_type = taskType;
  }

  if (opts['output-format']) {
    if (!c.mov) fail(`output_format=mov 只有 Seedance 2.5 支持`);
    body.output_format = opts['output-format'];
  }

  body.generate_audio = !opts['no-audio'];
  if (opts.watermark) body.watermark = true;
  if (opts.draft) body.draft = true;
  if (opts['return-last-frame']) body.return_last_frame = true;

  return { body, model };
}

async function ark(path, init = {}) {
  if (!KEY) {
    fail('没有找到 ARK_API_KEY。\n  三种方式任选其一：\n  1) 在技能根目录建 .env 写 ARK_API_KEY=xxx（模板见 .env.example）\n  2) export ARK_API_KEY=xxx   (Git Bash)\n  3) $env:ARK_API_KEY="xxx"   (PowerShell)');
  }
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json', ...(init.headers || {}) },
  });
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : {};
  } catch {
    json = { raw: text };
  }
  if (!res.ok) {
    const code = json?.error?.code || json?.code || res.status;
    const msg = json?.error?.message || json?.message || text.slice(0, 500);
    const err = new Error(`${code}: ${msg}`);
    err.code = code;
    err.payload = json;
    throw err;
  }
  return json;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function download(url, dir, name) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`下载失败 ${res.status}: ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await mkdir(dir, { recursive: true });
  const file = join(dir, name);
  await writeFile(file, buf);
  return { file, bytes: buf.length };
}

function stamp() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

async function pollTask(id, { interval, timeout }) {
  const started = Date.now();
  let last = null;
  let transient = 0;
  for (;;) {
    if (Date.now() - started > timeout * 1000) {
      throw new Error(`轮询超时（${timeout}s）。任务 ID ${id} 仍有效，可用 task 命令续查。`);
    }
    let info;
    try {
      info = await ark(`/contents/generations/tasks/${id}`);
      transient = 0;
    } catch (e) {
      if (++transient > 3) throw e;
      await sleep(interval * 1000);
      continue;
    }
    if (info.status !== last) {
      const secs = Math.round((Date.now() - started) / 1000);
      console.error(`[${secs}s] ${id} → ${info.status}`);
      last = info.status;
    }
    if (info.status === 'succeeded') return info;
    if (['failed', 'cancelled', 'expired'].includes(info.status)) {
      const e = info.error || {};
      throw new Error(`任务 ${info.status}: ${e.code || ''} ${e.message || ''}`.trim());
    }
    await sleep(interval * 1000);
  }
}

async function runImage(opts) {
  const { body } = await buildImageBody(opts, Boolean(opts['dry-run']));
  if (opts['dry-run']) return console.log(JSON.stringify(body, null, 2));

  const res = await ark('/images/generations', { method: 'POST', body: JSON.stringify(body) });
  const items = res.data || [];
  if (!items.length) {
    throw new Error(`没有返回图片: ${res.error ? `${res.error.code} ${res.error.message}` : JSON.stringify(res).slice(0, 400)}`);
  }
  const out = opts.out || './ark-out';
  const ext = (body.output_format === 'jpeg' || body.output_format === undefined) ? 'jpeg' : 'png';
  const ts = stamp();
  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    if (it.url) {
      const { file, bytes } = await download(it.url, out, `img-${ts}-${i}.${ext}`);
      console.log(`已保存 ${file}  (${(bytes / 1024).toFixed(0)} KB, ${it.size || '?'})`);
    } else if (it.b64_json) {
      await mkdir(out, { recursive: true });
      const file = join(out, `img-${ts}-${i}.${ext}`);
      await writeFile(file, Buffer.from(it.b64_json, 'base64'));
      console.log(`已保存 ${file}  (b64)`);
    }
  }
  console.log(`用量: 输入图 ${res.usage?.input_images ?? 0} · 出图 ${res.usage?.generated_images ?? items.length} · tokens ${res.usage?.total_tokens ?? '?'}`);
}

async function runVideo(opts) {
  const { body, model } = await buildVideoBody(opts, Boolean(opts['dry-run']));
  if (opts['dry-run']) return console.log(JSON.stringify(body, null, 2));

  const created = await ark('/contents/generations/tasks', { method: 'POST', body: JSON.stringify(body) });
  const id = created.id;
  if (!id) throw new Error(`创建任务失败，返回: ${JSON.stringify(created).slice(0, 400)}`);
  console.log(`已创建任务 ${id}（${model}）`);

  if (body.draft) {
    console.log(`这是 draft 试片任务。出片后用: node ark-media.mjs vid --draft-from ${id} --res 1080p --out <dir>`);
  }

  const info = await pollTask(id, {
    interval: Number(opts.interval || 10),
    timeout: Number(opts.timeout || 1800),
  });

  const out = opts.out || './ark-out';
  const ext = body.output_format === 'mov' ? 'mov' : 'mp4';
  if (info.content?.video_url) {
    const { file, bytes } = await download(info.content.video_url, out, `vid-${id}.${ext}`);
    console.log(`已保存 ${file}  (${(bytes / 1024 / 1024).toFixed(1)} MB)`);
  } else {
    console.log(`任务成功但没有 video_url，原始返回: ${JSON.stringify(info).slice(0, 600)}`);
  }
  if (info.content?.last_frame_url) {
    const { file } = await download(info.content.last_frame_url, out, `lastframe-${id}.jpeg`);
    console.log(`尾帧 ${file}`);
  }
  console.log(`用量: ${info.usage?.total_tokens ?? '?'} tokens · ${info.resolution || ''} ${info.ratio || ''} ${info.duration || ''}s ${info.framespersecond || ''}fps`);
}

async function runTask(opts, pos) {
  const id = pos[0];
  if (!id) fail('用法: node ark-media.mjs task <taskId>');
  const info = await pollTask(id, {
    interval: Number(opts.interval || 10),
    timeout: Number(opts.timeout || 1800),
  });
  const out = opts.out || './ark-out';
  if (info.content?.video_url) {
    const { file, bytes } = await download(info.content.video_url, out, `vid-${id}.mp4`);
    console.log(`已保存 ${file}  (${(bytes / 1024 / 1024).toFixed(1)} MB)`);
  } else {
    console.log(JSON.stringify(info, null, 2));
  }
}

async function main() {
  const argv = process.argv.slice(2);
  const { opts, pos } = parseArgs(argv);
  if (opts.help || !pos.length) return console.log(HELP);

  const cmd = pos.shift();
  await loadEnv();
  try {
    if (cmd === 'img' || cmd === 'vid' || cmd === 'task') checkOpts(cmd, opts);
    if (cmd === 'img') return await runImage(opts);
    if (cmd === 'vid') return await runVideo(opts);
    if (cmd === 'task') return await runTask(opts, pos);
    fail(`未知命令: ${cmd}\n\n${HELP}`);
  } catch (e) {
    console.error(`\x1b[31m失败: ${e.message}\x1b[0m`);
    if (e.payload) console.error(JSON.stringify(e.payload, null, 2).slice(0, 2000));
    process.exit(1);
  }
}

main();
