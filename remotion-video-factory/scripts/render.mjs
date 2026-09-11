#!/usr/bin/env node
/**
 * render.mjs - render visual frames once, then derive the BGM edition with FFmpeg.
 * Run from a Remotion project root:
 *   node <skill>/scripts/render.mjs --mode both --concurrency 8
 */
import {existsSync} from "node:fs";
import {spawn} from "node:child_process";
import os from "node:os";

const args = process.argv.slice(2);
const get = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const mode = get("mode", "both");
const concurrency = get("concurrency", String(Math.max(2, Math.min(8, os.cpus().length - 2))));
const composition = get("composition", "Video");
const outDir = get("out", "out");
const bgm = get("bgm", "public/bgm/bgm.mp3");
const bgmLevel = Number(get("bgm-level", "0.34"));
const force = args.includes("--force");
const base = `${outDir}/final-nobgm.mp4`;
const final = `${outDir}/final.mp4`;

if (!['final', 'nobgm', 'both'].includes(mode)) {
  console.error('mode must be final, nobgm, or both');
  process.exit(2);
}
if (!existsSync('src/index.ts') || !existsSync('props-nobgm.json')) {
  console.error('Run from the Remotion project root (src/index.ts and props-nobgm.json required).');
  process.exit(2);
}
if ((mode === 'final' || mode === 'both') && !existsSync(bgm)) {
  console.error(`BGM not found: ${bgm}`);
  process.exit(2);
}

const run = (command, commandArgs) => new Promise((resolve, reject) => {
  const child = spawn(command, commandArgs, {stdio: 'inherit', shell: false});
  child.on('error', reject);
  child.on('exit', (code) => code === 0 ? resolve() : reject(new Error(`${command} failed (${code})`)));
});

// The base includes VO + SFX. It is the only pass that runs Chromium for every frame.
if (!existsSync(base) || force) {
  // Node ≥18.20/20.12 起直接 spawn 'npx.cmd'（shell:false）会 EINVAL，须走 cmd /c
  const isWin = process.platform === 'win32';
  const cliArgs = [
    'remotion', 'render', 'src/index.ts', composition, base,
    `--props=props-nobgm.json`, `--concurrency=${concurrency}`,
  ];
  console.log(`render visual master ${base} (concurrency=${concurrency})`);
  await run(isWin ? 'cmd.exe' : 'npx', isWin ? ['/c', 'npx', ...cliArgs] : cliArgs);
} else {
  console.log(`reuse visual master ${base} (use --force after visual/VO/SFX changes)`);
}

// Do not render identical video frames a second time. Copy H.264 and mix BGM with FFmpeg.
if (mode === 'final' || mode === 'both') {
  if (!existsSync(final) || force) {
    console.log(`mix BGM -> ${final} (video stream copy; no second Chromium render)`);
    const filter = `[1:a]volume=${bgmLevel},afade=t=in:st=0:d=1,afade=t=out:st=0:d=3:curve=tri:enable='gte(t,duration-3)'[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[a]`;
    // afade's dynamic enable is not supported consistently; determine duration first.
    const probe = process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe';
    let probeOut = '';
    await new Promise((resolve, reject) => {
      const child = spawn(probe, ['-v','error','-show_entries','format=duration','-of','csv=p=0',base], {shell:false});
      child.stdout.on('data', (x) => { probeOut += x; });
      child.on('error', reject);
      child.on('exit', (code) => code === 0 ? resolve() : reject(new Error(`ffprobe failed (${code})`)));
    });
    const duration = Number(probeOut.trim());
    const fadeOut = Math.max(0, duration - 3);
    const stableFilter = `[1:a]volume=${bgmLevel},afade=t=in:st=0:d=1,afade=t=out:st=${fadeOut.toFixed(3)}:d=3[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.95[a]`;
    const ffmpeg = process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg';
    await run(ffmpeg, [
      '-y', '-v', 'warning', '-i', base, '-stream_loop', '-1', '-i', bgm,
      '-filter_complex', stableFilter, '-map', '0:v:0', '-map', '[a]',
      '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', duration.toFixed(3), final,
    ]);
  } else {
    console.log(`reuse ${final} (use --force to rebuild)`);
  }
}
console.log('render complete');
