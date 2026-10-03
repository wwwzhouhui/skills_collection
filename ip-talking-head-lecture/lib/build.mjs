// 构建管线：读 script.json → 逐场景合成配音 → 按画幅生成 timeline.json（+ 写进 Remotion 工程）
//           → 字幕（中/英 × SRT/VTT）+ 旁白稿 + 发布文案。
//
//   node lib/build.mjs <期> [--ratio=16:9] [--force-tts]
//
// timeline.json 是"整个视频的唯一真相"：每个场景的开始秒、时长、配音文件、字幕条，全由**TTS 实际音频时长**反推，
// 所以改一句旁白重新 build 就整体重排，不需要手调任何帧数。
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { buildCues, toSrt, toVtt, flattenCues } from './cues.mjs';
import { renderPublish } from './publish.mjs';

const require = createRequire(import.meta.url);
const paths = require('./paths.cjs');
const { cfg, ROOT, projectPaths, resolveProject } = paths;

// ── 参数 ─────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const flags = {};
const positional = [];
for (const a of argv) {
  const m = /^--([^=]+)(?:=(.*))?$/.exec(a);
  if (m) flags[m[1]] = m[2] ?? true;
  else positional.push(a);
}
const P = projectPaths(resolveProject(positional[0]));
const forceTts = Boolean(flags['force-tts']);
if (forceTts) process.env.FORCE_TTS = '1';

// ── .env（TTS 凭证） ─────────────────────────────────────────────────
try {
  process.loadEnvFile(path.join(ROOT, '.env'));
} catch {
  /* 没有 .env 就只用环境变量 */
}

// ── TTS 档位（照 config.json 落到各引擎自己的环境变量上） ──────────────
const ENGINE = process.env.TTS_ENGINE || cfg.tts.engine || 'volc';
process.env.TTS_ENGINE = ENGINE;
const SPEED = Number(cfg.tts.speed ?? 1);
const LOUDNESS = Number(cfg.tts.loudness ?? 1);

if (ENGINE === 'mi') {
  const mi = cfg.tts.mi || {};
  if (mi.baseUrl) process.env.MI_TTS_BASE_URL = String(mi.baseUrl);
  if (mi.model) process.env.MI_TTS_MODEL = String(mi.model);
  if (mi.style) process.env.MI_TTS_STYLE = String(mi.style);
  process.env.MI_TTS_SPEED = String(SPEED);
  process.env.MI_TTS_LOUDNESS = String(LOUDNESS);
} else if (ENGINE === 'volc') {
  if (cfg.tts.resourceId) process.env.VOLC_TTS_RESOURCE_ID = String(cfg.tts.resourceId);
  if (cfg.tts.endpoint) process.env.VOLC_TTS_ENDPOINT = String(cfg.tts.endpoint);
  process.env.VOLC_TTS_SPEED = String(Math.max(-50, Math.min(100, Math.round((SPEED - 1) * 100))));
  process.env.VOLC_TTS_LOUDNESS = String(Math.max(-50, Math.min(100, Math.round((LOUDNESS - 1) * 100))));
  if (cfg.tts.style) process.env.VOLC_TTS_STYLE = String(cfg.tts.style);
}

// ── 读脚本 ───────────────────────────────────────────────────────────
if (!fs.existsSync(P.script)) throw new Error(`缺 ${P.script}`);
const script = JSON.parse(fs.readFileSync(P.script, 'utf8'));
const scenes = script.scenes || [];
if (!scenes.length) throw new Error('script.json 里 scenes 是空的');

const video = { ...cfg.video, ...(script.video || {}) };
const pace = { ...cfg.pacing, ...(script.pacing || {}) };
const cueOpts = { ...cfg.cues, ...(script.cues || {}) };
// 品牌层提前合并（config.brand ← script.brand 覆盖），片尾卡与 logo 处理都要用
const brand = { ...cfg.brand, ...(script.brand || {}) };

const wantRatios = String(flags.ratio || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
const ratios = wantRatios.length ? wantRatios : video.ratios || ['16:9'];

// ── 输出目录 ─────────────────────────────────────────────────────────
fs.mkdirSync(P.audio, { recursive: true });
// ⚠️不要递归删 public/audio、public/avatar：本机的 safe-delete 会拦下批量删除并直接报错退出
//    （SAFE_DELETE_BULK_GUARD_ERROR）。素材按固定文件名覆盖写入即可 —— 上一个期留下的同名文件
//    会被覆盖，多余的文件不会被 timeline 引用，无害。
fs.mkdirSync(path.join(P.publicDir, 'avatar'), { recursive: true });
fs.mkdirSync(path.join(P.publicDir, 'audio'), { recursive: true });
fs.mkdirSync(P.outputs, { recursive: true });

// ── 数字人素材 → public/avatar（形象预设 + 期目录可覆盖） ────────────────
// 形象优先级：--preset=human > script.avatar.preset > config.avatar.preset
const baseAvatar = cfg.avatar || {};
const presetName = String(flags.preset || (script.avatar || {}).preset || baseAvatar.preset || '').trim();
const presets = baseAvatar.presets || {};
const preset = presetName ? presets[presetName] : null;
if (presetName && !preset) {
  const avail = Object.keys(presets).filter((k) => !k.startsWith('_'));
  throw new Error(`config.avatar.presets 里没有形象「${presetName}」（可用：${avail.join(' / ') || '(空)'}）`);
}
// preset 的 focus / scale 覆盖全局，script.avatar 再覆盖 preset
const avatarSpec = { ...baseAvatar, ...(preset || {}), ...(script.avatar || {}) };

// 同一帧允许的备用主名（新旧目录结构都认）
const STEMS = {
  image: ['image', 'avatar'],
  mouthMid: ['mouth-mid', 'mouthmid', 'avatar-mid'],
  mouthOpen: ['mouth-open', 'mouthopen', 'avatar-open'],
};

/** 在目录里按主名 + 任意扩展名找一个文件（找不到返回 ''） */
function findByStem(dir, stems) {
  if (!dir || !fs.existsSync(dir)) return '';
  const files = fs.readdirSync(dir).filter((f) => !f.startsWith('.'));
  for (const stem of stems) {
    const hit = files.find((f) => path.basename(f, path.extname(f)).toLowerCase() === stem);
    if (hit) return path.join(dir, hit);
  }
  return '';
}

const presetDir = preset && preset.dir ? paths.expand(preset.dir) : '';

const resolveAsset = (rel) => {
  const local = path.join(P.project, path.basename(rel));
  if (fs.existsSync(local)) return local;
  const local2 = path.join(P.assets, path.basename(rel));
  if (fs.existsSync(local2)) return local2;
  return paths.expand(rel);
};

const avatarFiles = {};
const avatarSource = {};
for (const key of ['image', 'mouthMid', 'mouthOpen']) {
  // 1) 期目录覆盖（本期专属形象：<期>/assets/ 或 <期>/ 根下的同名文件）
  let src = findByStem(P.assets, STEMS[key]) || findByStem(P.project, STEMS[key]);
  let from = src ? '期目录' : '';
  // 2) 形象预设目录
  if (!src && presetDir) {
    src = findByStem(presetDir, STEMS[key]);
    from = src ? '预设目录' : '';
  }
  // 3) 兜底：老式的显式路径（config.avatar.image 等）
  if (!src && avatarSpec[key]) {
    const cand = resolveAsset(avatarSpec[key]);
    if (fs.existsSync(cand)) {
      src = cand;
      from = '兜底路径';
    }
  }
  if (!src) {
    if (key === 'image') {
      throw new Error(
        `找不到数字人形象图。形象「${presetName || '(未设置 preset)'}」应放在 ${presetDir || 'config.avatar.image'} 下，` +
          `文件名形如 image.png / avatar.png`,
      );
    }
    continue; // 口型帧可选
  }
  const ext = path.extname(src);
  fs.copyFileSync(src, path.join(P.publicDir, 'avatar', `${key}${ext}`));
  avatarFiles[key] = `avatar/${key}${ext}`;
  avatarSource[key] = { from, path: src };
}
console.log(
  `[avatar] 形象 ${presetName || '(无 preset，走兜底路径)'}` +
    (preset ? ` · ${preset.label || ''}` : '') +
    (avatarSource.image ? ` · ${avatarSource.image.from}` : '') +
    ` · 口型帧 ${['mouthMid', 'mouthOpen'].filter((k) => avatarFiles[k]).length}/2`,
);
{
  // 旧预设留下的不同扩展名文件会残留在 public/avatar（safe-delete 不许清目录），
  // 但 timeline 只引用上面写定的确切路径，残留无害。
  const stale = fs
    .readdirSync(path.join(P.publicDir, 'avatar'))
    .filter((f) => !Object.values(avatarFiles).some((v) => path.basename(v) === f));
  if (stale.length) console.log(`[avatar] 残留未引用文件（无害）：${stale.join(', ')}`);
}

// ── 片尾品牌卡（参考 whiteboard-video-factory 的 brand.endCard） ──────────
// build 时自动在末尾追加一个无配音的 outro 场景；script.json 里已手写 outro 则不重复追加。
// 标识图优先级：<期>/assets/<logo 文件名> > brand.logo 配置路径；找不到就退化为手写名文字。
const endCard = brand.endCard || {};
const lastScene = scenes[scenes.length - 1];
if (endCard.enabled !== false && String(brand.name || '').trim() && (!lastScene || lastScene.kind !== 'outro')) {
  let logoOut = '';
  if (brand.logo) {
    const logoCand = [
      path.join(P.assets, path.basename(brand.logo)),
      path.join(P.project, path.basename(brand.logo)),
      paths.expand(brand.logo),
    ].find((f) => f && fs.existsSync(f));
    if (logoCand) {
      const ext = path.extname(logoCand);
      fs.mkdirSync(path.join(P.publicDir, 'brand'), { recursive: true });
      fs.copyFileSync(logoCand, path.join(P.publicDir, 'brand', `logo${ext}`));
      logoOut = `brand/logo${ext}`;
      console.log(`[endCard] 标识图 ← ${logoCand}`);
    } else {
      console.warn(`[endCard] brand.logo 不存在：${brand.logo} —— 片尾卡退化为手写名文字`);
    }
  }
  scenes.push({
    kind: 'outro',
    id: 'scene-outro',
    narration: '',
    duration: Number(endCard.seconds) || 4.2,
    data: { name: brand.name, slogan: brand.slogan || '', cta: endCard.cta || '', logo: logoOut },
  });
  console.log(`[endCard] 追加片尾品牌卡 ${Number(endCard.seconds) || 4.2}s · CTA「${endCard.cta || '(无)'}」`);
}

// ── 配音合成 ─────────────────────────────────────────────────────────
const { synthesize, resolveVolcConfig } = await import('./tts/tts.mjs');

if (ENGINE === 'mi') {
  const { resolveMiConfig, miAlignLabel } = await import('./tts/mi.mjs');
  const vc = resolveMiConfig((cfg.tts.mi || {}).voice || '');
  console.log(`[voice] 小米 MiMo · ${vc.model} · ${vc.speaker} @${SPEED}x · 字幕按小句对齐`);
} else if (ENGINE === 'volc') {
  const vc = resolveVolcConfig(cfg.tts.voice || '');
  console.log(`[voice] 火山 ${vc.mode} 域 · ${vc.resourceId} · ${vc.speaker} @${SPEED}x · 字幕逐字对齐`);
} else {
  console.log(`[voice] edge-tts（免费备胎）`);
}

// 重试只对偶发故障有意义；凭证/音色类错误重试纯属浪费
const HARD_FAIL = /code 4\d{7}|Invalid X-Api-Key|not granted|mismatched with speaker|Unknown voice|Param Incorrect|缺少火山凭证|缺少小米凭证|小米 TTS HTTP 4(0[0134])|API key/;

// 时间戳字段归一化：火山与小米都返回 {word, startTime, endTime}，
// 本项目内部统一用 {w, s, e}（短、便于塞进 timeline.json）。
function normWords(words) {
  return (words || [])
    .map((x) => ({
      w: String(x.word ?? x.w ?? ''),
      s: Number(x.startTime ?? x.s ?? NaN),
      e: Number(x.endTime ?? x.e ?? NaN),
    }))
    .filter((x) => x.w && Number.isFinite(x.s) && Number.isFinite(x.e) && x.e >= x.s);
}

// 每个引擎有**自己**的音色字段（火山 tts.voice / 小米 tts.mi.voice / edge tts.edge.voice），
// 互相顶替会报 Unknown voice —— 这是最常见的配置坑。
const VOICE =
  ENGINE === 'mi'
    ? (cfg.tts.mi || {}).voice || process.env.MI_TTS_VOICE
    : ENGINE === 'edge'
      ? (cfg.tts.edge || {}).voice || process.env.EDGE_TTS_VOICE
      : cfg.tts.voice || process.env.VOLC_TTS_VOICE;

const narration = [];
for (let i = 0; i < scenes.length; i++) {
  const sc = scenes[i];
  const id = sc.id || `scene-${i + 1}`;
  sc.id = id;
  const text = String(sc.narration || '').trim();
  const wav = path.join(P.audio, `${id}.wav`);
  const pubWav = path.join(P.publicDir, 'audio', `${id}.wav`);

  if (!text) {
    // 无旁白场景（片尾卡）：不合成音频
    narration.push({ id, text: '', duration: 0, words: [], noAudio: true });
    console.log(`[voice] ${id} 无旁白，跳过`);
    continue;
  }

  let r;
  let tries = 0;
  for (;;) {
    try {
      r = await synthesize(text, wav, { voice: VOICE });
      break;
    } catch (e) {
      if (HARD_FAIL.test(e.message) || ++tries >= 4) throw e;
      console.log(`[voice] ${id} 第 ${tries} 次失败，重试：${e.message.split('\n')[0]}`);
      await new Promise((s) => setTimeout(s, 800 * tries));
    }
  }
  fs.mkdirSync(path.dirname(pubWav), { recursive: true });
  fs.copyFileSync(r.path, pubWav);
  console.log(
    `[voice] ${id} ✓ ${r.duration.toFixed(2)}s · ${normWords(r.words).length} 条时间戳（${r.align || 'native'}）`,
  );
  narration.push({ id, text, duration: r.duration, words: normWords(r.words) });
}

// ── 组装 timeline（每个画幅一份） ──────────────────────────────────────
const written = [];
for (const ratio of ratios) {
  const lay = (cfg.layout || {})[ratio];
  if (!lay) throw new Error(`config.layout 里没有画幅 ${ratio}（可用：${Object.keys(cfg.layout || {}).filter((k) => !k.startsWith('_')).join(' / ')}）`);

  const avatar = {
    image: avatarFiles.image,
    mouthMid: avatarFiles.mouthMid,
    mouthOpen: avatarFiles.mouthOpen,
    preset: presetName || '',
    size: lay.avatar.size,
    x: lay.avatar.x,
    y: lay.avatar.y,
    ringColor: (script.brand || {}).accent || cfg.brand.accent,
    focus: avatarSpec.focus || '50% 24%',
    scale: Number.isFinite(Number(avatarSpec.scale)) ? Number(avatarSpec.scale) : 1.04,
    showRing: avatarSpec.showRing !== false,
  };

  let cursor = 0;
  const outScenes = [];
  for (let i = 0; i < scenes.length; i++) {
    const sc = scenes[i];
    const nr = narration[i];
    const lead = sc.leadPadding ?? pace.leadPadding;
    const tail = sc.tailPadding ?? pace.tailPadding;
    const audioDur = nr.duration || Number(sc.duration || 0) || pace.minSceneSeconds;
    const raw = nr.noAudio ? Number(sc.duration || 3.5) : lead + audioDur + tail;
    const duration = Math.max(Number(sc.minSeconds || pace.minSceneSeconds), raw);
    const start = i === 0 ? 0 : Math.max(0, cursor - pace.sceneGap);

    const cues = nr.noAudio ? [] : buildCues(nr.text, nr.words, cueOpts);
    outScenes.push({
      id: sc.id,
      kind: sc.kind,
      start: +start.toFixed(3),
      duration: +duration.toFixed(3),
      audio: nr.noAudio ? '' : `audio/${sc.id}.wav`,
      audioOffset: nr.noAudio ? 0 : +lead.toFixed(3),
      kicker: sc.kicker || '',
      heading: sc.heading || '',
      sub: sc.sub || '',
      data: sc.data || {},
      cues,
      words: (nr.words || []).map((w) => ({ w: w.w, s: +w.s.toFixed(3), e: +w.e.toFixed(3) })),    });
    cursor = start + duration;
  }

  const timeline = {
    title: script.title || P.name,
    width: lay.width,
    height: lay.height,
    fps: video.fps,
    total: +cursor.toFixed(3),
    tone: script.tone || 'light',
    brand,
    avatar,
    subtitle: lay.subtitle || {},
    scenes: outScenes,
  };

  const outFile = path.join(P.work, `timeline-${ratio.replace(':', 'x')}.json`);
  fs.writeFileSync(outFile, JSON.stringify(timeline, null, 2), 'utf8');
  // Remotion 工程读的那一份（每次渲染前覆盖）
  fs.writeFileSync(
    path.join(ROOT, 'remotion', 'src', 'generated', 'timeline.json'),
    JSON.stringify(timeline, null, 2),
    'utf8',
  );
  written.push({ ratio, timeline, outFile });
  console.log(
    `[timeline] ${ratio} ${lay.width}x${lay.height} · ${outScenes.length} 场景 · ${timeline.total.toFixed(1)}s`,
  );
}

// ── 字幕（中/英 × SRT/VTT） + 旁白稿 + 发布文案 ─────────────────────────
const primary = written[0].timeline;
const srtCount = flattenCues(primary.scenes).length;

// 英文字幕逐条复用中文的时间轴（条数必须一致，否则宁可不生成，避免时间轴错位）
const enCues = script.publish && script.publish.en ? script.publish.en.cues : null;
let hasEnCues = false;
if (Array.isArray(enCues) && enCues.length) {
  if (enCues.length === srtCount) {
    hasEnCues = true;
  } else {
    console.warn(
      `[warn] publish.en.cues 有 ${enCues.length} 条，但中文字幕是 ${srtCount} 条 —— 跳过英文字幕。` +
        `\n       改成逐条对应（条数一致）才会生成，避免时间轴错位。`,
    );
  }
}

fs.writeFileSync(P.srt, toSrt(primary.scenes), 'utf8');
fs.writeFileSync(P.vtt, toVtt(primary.scenes), 'utf8');
if (hasEnCues) {
  fs.writeFileSync(P.srtEn, toSrt(primary.scenes, enCues), 'utf8');
  fs.writeFileSync(P.vttEn, toVtt(primary.scenes, enCues), 'utf8');
}

const noteLines = [
  `# ${primary.title}`,
  '',
  `- 时长：${primary.total.toFixed(1)} 秒 ｜ 场景：${primary.scenes.length} 个 ｜ 画幅：${ratios.join(' / ')}`,
  `- 配音：${ENGINE}（${ENGINE === 'mi' ? (cfg.tts.mi || {}).voice : cfg.tts.voice}）@${SPEED}x`,
  '',
  '| # | 版式 | 起 | 时长 | 旁白 |',
  '| --- | --- | --- | --- | --- |',
  ...primary.scenes.map(
    (s, i) =>
      `| ${i + 1} | ${s.kind} | ${s.start.toFixed(1)}s | ${s.duration.toFixed(1)}s | ${String(
        narration[i].text || '（无）',
      ).replace(/\|/g, '/')} |`,
  ),
  '',
];
fs.writeFileSync(P.note, noteLines.join('\n'), 'utf8');

// 发布文案：只有 script.json 写了 publish 段才生成（没写就不硬凑一份空壳）
if (script.publish) {
  const voice = ENGINE === 'mi' ? (cfg.tts.mi || {}).voice : cfg.tts.voice;
  const engineLabel = ENGINE === 'mi' ? '小米 MiMo' : ENGINE === 'volc' ? '火山引擎' : 'edge-tts';
  const avatarLabel =
    ((cfg.avatar.presets || {})[presetName] || {}).label || presetName || '默认形象';
  fs.writeFileSync(
    P.publish,
    renderPublish({
      title: primary.title,
      total: primary.total,
      scenes: primary.scenes,
      pub: script.publish,
      ratios,
      engine: engineLabel,
      voice,
      speed: SPEED,
      avatarLabel,
      hasEnCues,
      srtCount,
    }),
    'utf8',
  );
}

console.log(`[done] 时间轴 → ${written.map((w) => path.basename(w.outFile)).join(' ')}`);
console.log(`[done] 字幕 → ${path.basename(P.srt)} · ${path.basename(P.vtt)}${hasEnCues ? ` · ${path.basename(P.srtEn)} · ${path.basename(P.vttEn)}` : ''}`);
console.log(`[done] 旁白稿 → ${P.note}`);
if (script.publish) console.log(`[done] 发布文案 → ${P.publish}`);
console.log(`[next] node lib/render.mjs "${P.name}" --ratio=${ratios.join(',')}`);
