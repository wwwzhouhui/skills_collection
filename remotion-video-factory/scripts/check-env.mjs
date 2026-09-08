#!/usr/bin/env node
/** check-env.mjs — remotion-video-factory 环境一键自检（跨平台：Windows / macOS / Linux）
 *
 * 用法: node <skill>/scripts/check-env.mjs
 * 检查: Node ≥18、ffmpeg、ffprobe、Python 3.10+、edge-tts（配音步骤还需网络）
 */
import {spawnSync} from "node:child_process";

const c = (code, s) => (process.stdout.isTTY ? `\x1b[${code}m${s}\x1b[0m` : s);
const ok = (s) => c(32, `✓ ${s}`);
const bad = (s) => c(31, `✗ ${s}`);
const warn = (s) => c(33, `⚠ ${s}`);

const run = (cmd, args = []) => {
  try {
    const r = spawnSync(cmd, args, {encoding: "utf8", timeout: 20000, windowsHide: true});
    if (r.error || r.status !== 0) return null;
    return r.stdout || "";
  } catch {
    return null;
  }
};

let failed = 0;

// Node ≥ 18
const nodeMajor = parseInt(process.versions.node.split(".")[0], 10);
if (nodeMajor >= 18) console.log(ok(`Node ${process.versions.node}（≥18）`));
else {
  console.log(bad(`Node ${process.versions.node} —— 需要 ≥18，请升级`));
  failed++;
}

// ffmpeg / ffprobe
const ffOut = run("ffmpeg", ["-version"]);
if (ffOut) {
  const v = (ffOut.split("\n")[0] || "").match(/version\s+(\S+)/);
  console.log(ok(`ffmpeg ${v ? v[1] : "已安装"}`));
} else {
  console.log(bad("ffmpeg 未安装或不在 PATH —— 渲染与音画抽查必需"));
  failed++;
}
if (run("ffprobe", ["-version"])) console.log(ok("ffprobe 已安装"));
else {
  console.log(bad("ffprobe 未安装或不在 PATH —— tts.py 测长必需"));
  failed++;
}

// Python（Windows 常为 python/py，Unix 常为 python3）
const pyCmd = ["python", "python3", "py"].find((x) => run(x, ["--version"]));
if (!pyCmd) {
  console.log(bad("Python 未找到 —— 配音步骤必需（3.10+）"));
  failed++;
} else {
  const v = run(pyCmd, ["--version"]).trim();
  const m = v.match(/(\d+)\.(\d+)/);
  const [maj, min] = m ? [parseInt(m[1], 10), parseInt(m[2], 10)] : [0, 0];
  console.log(ok(`${v}（命令: ${pyCmd}${maj === 3 && min < 10 ? " —— 建议 3.10+" : ""}）`));
  if (run(pyCmd, ["-c", "import edge_tts"])) console.log(ok("edge-tts 已安装"));
  else console.log(warn(`edge-tts 未安装 —— ${pyCmd} -m pip install edge-tts 后重跑本检查`));
}

console.log(
  failed
    ? `\n${failed} 项未通过 —— 修复后再开始八步工作流。`
    : "\n环境就绪 —— 可开始八步工作流（配音步骤需网络，渲染无需网络）。"
);
process.exit(failed ? 1 : 0);
