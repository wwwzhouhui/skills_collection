import fs from 'node:fs';
import path from 'node:path';
import { createHash, randomUUID } from 'node:crypto';
// 小米通道的句子时间轴是本地估算的（引擎不给时间戳），算法版本必须进缓存键，见 mi.mjs 的 ALIGN_VERSION。
import { ALIGN_VERSION } from './mi.mjs';

export const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
export function fileDigest(file) {
  const hash = createHash('sha256');
  const fd = fs.openSync(file, 'r');
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try { let n; while ((n = fs.readSync(fd, buffer, 0, buffer.length, null))) hash.update(buffer.subarray(0, n)); }
  finally { fs.closeSync(fd); }
  return hash.digest('hex');
}
export function assetFingerprint(value) {
  const url = String(value);
  if (/^https?:\/\//.test(url)) return { url, remote: true }; // 远程源需先落本地才能核实内容
  const file = path.resolve(url.replace(/^file:\/\//, ''));
  try { return { file, sha256: fileDigest(file) }; } catch { return { file, missing: true }; }
}
export function footageFingerprint(shotList) {
  const urls = [...new Set((shotList.scenes || []).flatMap(s => {
    const v = s.visual?.footage_url;
    return Array.isArray(v) ? v : v ? [v] : [];
  }))];
  return urls.map(assetFingerprint);
}
export function atomicJSON(file, data) {
  const tmp = `${file}.${randomUUID()}.tmp`;
  try { fs.writeFileSync(tmp, JSON.stringify(data)); fs.renameSync(tmp, file); }
  finally { fs.rmSync(tmp, { force: true }); }
}
export function readAudioCache(file, key) {
  try {
    const entry = JSON.parse(fs.readFileSync(`${file}.cache.json`, 'utf8'));
    if (entry.version !== 1 || entry.key !== key || entry.sha256 !== fileDigest(file)
      || !Number.isFinite(entry.duration) || !(entry.duration > 0) || !Array.isArray(entry.words)) return null;
    // align 也要带出来。它是**诊断标签**（native=引擎逐字时间戳 / silence-estimate=本地估算），
    // 漏传的后果不是音频错，而是缓存命中时驱动器和文档看到的时间轴来源会突然变成 "native"，
    // 冷跑与热跑说法不一致——极难排查的"假信息"。（老缓存没有这个字段，驱动器有兜底推导。）
    return { path: file, duration: entry.duration, words: entry.words, ...(entry.align ? { align: entry.align } : {}) };
  } catch { return null; }
}
export function writeAudioCache(file, key, audio) {
  if (!Number.isFinite(audio.duration) || audio.duration <= 0) throw new Error("不能缓存无效音频时长");
  atomicJSON(`${file}.cache.json`, { version: 1, key, sha256: fileDigest(file), duration: audio.duration, words: audio.words || [], align: audio.align || null });
}
export function ttsIdentity(text, voice, env = process.env) {
  if (env.TTS_ENGINE === 'say') return { version: 1, text, engine: 'say', voice: env.SAY_VOICE || 'Tingting', rate: env.SAY_RATE || '200', wav: '24000-mono' };
  // 小米 MiMo：端点/模型/音色/风格/变速/音量 全进键。变速是本地 atempo 后处理，改倍率必须重配。
  // alignVers 也要进键——时间轴是本地估算的，算法换了就必须重算（见 mi.mjs 的 ALIGN_VERSION）。
  if (env.TTS_ENGINE === 'mi') return { version: 1, text, engine: 'mi',
    baseUrl: env.MI_TTS_BASE_URL || 'https://token-plan-cn.xiaomimimo.com/v1',
    model: env.MI_TTS_MODEL || 'mimo-v2.5-tts',
    speaker: voice || env.MI_TTS_VOICE || '冰糖',
    style: env.MI_TTS_STYLE || '', speed: Number(env.MI_TTS_SPEED || 1), loudness: Number(env.MI_TTS_LOUDNESS || 1),
    format: 'wav', wav: '44100-stereo', alignVers: ALIGN_VERSION };
  // 端点(standard/plan)也要进键：同一句话在两个域上是不同音频，换域必须重配，不能命中旧缓存。
  const endpoint = env.VOLC_TTS_ENDPOINT || (/^ark-/i.test(env.VOLC_TTS_API_KEY || '') ? 'plan' : 'standard');
  return { version: 1, text, engine: 'volc', endpoint, resource: env.VOLC_TTS_RESOURCE_ID || 'seed-tts-2.0',
    speaker: voice?.includes('_') ? voice : env.VOLC_TTS_VOICE || 'zh_male_liufei_uranus_bigtts',
    speed: Number(env.VOLC_TTS_SPEED || 0), loudness: Number(env.VOLC_TTS_LOUDNESS || 0), style: env.VOLC_TTS_STYLE || '',
    format: 'mp3', sampleRate: 24000, bitRate: 128000, timestamp: true, subtitle: true, wav: '44100-stereo' };
}

// 总管线与逐镜缓存都看内容；产物缺失/被替换不能被 manifest 的旧状态掩盖。
export function stageMediaFingerprint(stage, paths, shotList, videoIndex) {
  const beds = (videoIndex.items || []).filter(i => i.video).map(i => assetFingerprint(path.join(paths.dir, i.video)));
  if (stage === 'video') return { sources: footageFingerprint(shotList), beds };
  return { beds, audio: (shotList.scenes || []).flatMap(s => [
    assetFingerprint(path.join(paths.audio, `${s.id}.wav`)),
    assetFingerprint(path.join(paths.audio, `${s.id}.wav.cache.json`)),
  ]) };
}
