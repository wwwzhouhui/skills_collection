// 把帧序列编码成 MP4（H.264，微信/视频号可直接用）
// 用法: node encode.mjs <framesDir> <out.mp4> [--fps=30] [--crf=20] [--preset=medium]
import { existsSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";

const __dir = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const positional = argv.filter(a => !a.startsWith("--"));
const opt = Object.fromEntries(argv.filter(a => a.startsWith("--")).map(a => {
  const [k, v] = a.replace(/^--/, "").split("=");
  return [k, v === undefined ? true : v];
}));

const framesDir = positional[0], out = positional[1];
if (!framesDir || !out) { console.error("用法: node encode.mjs <framesDir> <out.mp4>"); process.exit(1); }

const FPS = Number(opt.fps || 30);
const CRF = Number(opt.crf || 20);
const PRESET = opt.preset || "medium";

// ffmpeg 定位：本机常用路径 > Tools 备份 > @ffmpeg-installer
const candidates = [
  "D:/Program Files/ffmpeg-6.1.1-full_build/bin/ffmpeg.exe",
  "D:/obsidian 笔记(海老豹666)/09-0全域创业素材/Tools/ffmpeg/ffmpeg.exe",
  join(__dir, "..", "..", "..", "binaries", "node", "workspace", "node_modules", "@ffmpeg-installer", "win32-x64", "ffmpeg.exe")
];
const ffmpeg = opt.ffmpeg || candidates.find(p => existsSync(p));
if (!ffmpeg) { console.error("[encode] 找不到 ffmpeg，用 --ffmpeg=<path> 指定"); process.exit(1); }

console.log(`[encode] ffmpeg: ${ffmpeg}`);
execFileSync(ffmpeg, [
  "-y", "-hide_banner", "-loglevel", "error",
  "-framerate", String(FPS),
  "-i", join(resolve(framesDir), "f%05d.jpg"),
  "-c:v", "libx264", "-pix_fmt", "yuv420p",
  "-crf", String(CRF), "-preset", PRESET,
  "-movflags", "+faststart",
  resolve(out)
], { stdio: "inherit" });

const size = statSync(resolve(out)).size;
console.log(`[encode] 完成 → ${resolve(out)} (${(size / 1024 / 1024).toFixed(1)} MB)`);
