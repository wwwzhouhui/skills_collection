// iph voice —— 配音档位自检。
// 三个引擎的「凭证 × 端点域 × 音色」任一不匹配，报错都很模糊，等出片时才炸很浪费时间。
// 这里先回显档位，再用一句短文本真合成一次 → build/_voice-check.wav，试听即知音色对不对。
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const paths = require('./paths.cjs');
const { cfg, ROOT } = paths;

try {
  process.loadEnvFile(path.join(ROOT, '.env'));
} catch {
  console.log('（没有 .env，只用环境变量）');
}

const ENGINE = process.env.TTS_ENGINE || cfg.tts.engine || 'volc';
process.env.TTS_ENGINE = ENGINE;
const SPEED = Number(cfg.tts.speed ?? 1);
const LOUDNESS = Number(cfg.tts.loudness ?? 1);
const SAMPLE = '海老豹讲知识，一二三四五六七八九十。';
const out = path.join(ROOT, 'build', '_voice-check.wav');

if (ENGINE === 'edge') {
  const e = cfg.tts.edge || {};
  console.log('engine   edge（本机 edge-tts，免费、不需要凭证）');
  console.log('音色     ' + (e.voice || 'zh-CN-YunxiNeural'));
  console.log('解释器   ' + (e.python || '(PATH 里的 python3 / python)'));
  console.log('语速     按 tts.speed=' + SPEED + ' 换算');
  console.log('直接跑 iph build <期> 就是自检。');
  process.exit(0);
}

if (ENGINE === 'mi') {
  const mi = cfg.tts.mi || {};
  if (mi.baseUrl) process.env.MI_TTS_BASE_URL = String(mi.baseUrl);
  if (mi.model) process.env.MI_TTS_MODEL = String(mi.model);
  if (mi.style) process.env.MI_TTS_STYLE = String(mi.style);
  process.env.MI_TTS_SPEED = String(SPEED);
  process.env.MI_TTS_LOUDNESS = String(LOUDNESS);
} else {
  if (cfg.tts.resourceId) process.env.VOLC_TTS_RESOURCE_ID = String(cfg.tts.resourceId);
  if (cfg.tts.endpoint) process.env.VOLC_TTS_ENDPOINT = String(cfg.tts.endpoint);
  process.env.VOLC_TTS_SPEED = String(Math.round((SPEED - 1) * 100));
  process.env.VOLC_TTS_LOUDNESS = String(Math.round((LOUDNESS - 1) * 100));
  if (cfg.tts.style) process.env.VOLC_TTS_STYLE = String(cfg.tts.style);
}

let vc;
try {
  if (ENGINE === 'mi') {
    const { resolveMiConfig } = await import('./tts/mi.mjs');
    const voice = (cfg.tts.mi || {}).voice || process.env.MI_TTS_VOICE || '';
    vc = resolveMiConfig(voice);
    console.log('engine   mi（小米 MiMo）');
    console.log('端点     ' + vc.baseUrl + '/chat/completions');
    console.log('模型     ' + vc.model);
    console.log('音色     ' + vc.speaker + ' @' + SPEED + 'x' + (vc.style ? '  风格「' + vc.style + '」' : ''));
    console.log('时间轴   小句级（小米不返回逐字时间戳）');
    console.log('变速     ' + (SPEED !== 1 ? '本地 ffmpeg atempo=' + SPEED + '（接口没有语速参数）' : '原速'));
  } else {
    const { resolveVolcConfig } = await import('./tts/tts.mjs');
    const voice = cfg.tts.voice || process.env.VOLC_TTS_VOICE;
    vc = resolveVolcConfig(voice);
    console.log('engine   volc（火山引擎）');
    console.log('端点     ' + vc.mode + ' 域 → ' + vc.url);
    console.log('资源     ' + vc.resourceId);
    console.log('音色     ' + vc.speaker + ' @' + SPEED + 'x');
    console.log('时间轴   逐字（字幕可做逐字跟读高亮）');
  }
} catch (e) {
  console.error('✗ ' + e.message);
  process.exit(1);
}

console.log('—— 试合成一句 ——');
process.env.FORCE_TTS = '1';
fs.mkdirSync(path.dirname(out), { recursive: true });
try {
  const { synthesize } = await import('./tts/tts.mjs');
  const r = await synthesize(SAMPLE, out, { voice: ENGINE === 'mi' ? (cfg.tts.mi || {}).voice : cfg.tts.voice });
  console.log('✓ ' + r.path);
  console.log('  时长 ' + r.duration.toFixed(2) + 's · 时间戳 ' + r.words.length + ' 条' + (r.align ? '（' + r.align + '）' : ''));
  console.log('  试听一下，音色不对就改 config.json 的 tts.' + (ENGINE === 'mi' ? 'mi.voice' : 'voice'));
} catch (e) {
  console.error('✗ ' + e.message);
  process.exit(1);
}
