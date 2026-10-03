// 异步进程执行器。
//
// ⚠️ 为什么必须异步：本机（Windows + 当前 Node 22）的**同步**进程调用
//    （execFileSync / execSync / spawnSync）一律抛 `EBUSY`，连 `cmd /c echo` 都起不来；
//    而异步 spawn 完全正常（能拿到真实 stdout/退出码）。已排除 NODE_OPTIONS、sandbox、
//    ELECTRON_RUN_AS_NODE 等原因（Python 的 subprocess 也正常）。2026-10-02 实测。
//    → TTS 库里所有外部命令（ffmpeg / ffprobe）一律走这里，别再引入 execFileSync。
import { spawn } from "node:child_process";

// 跑一条命令，返回 { code, stdout, stderr }。stdio="inherit" 时不捕获（直接继承父进程的终端）。
export function run(cmd, args, { stdio = "inherit", cwd, env } = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio, cwd, env });
    let out = "";
    let err = "";
    if (p.stdout) p.stdout.on("data", (d) => (out += d.toString()));
    if (p.stderr) p.stderr.on("data", (d) => (err += d.toString()));
    p.on("error", reject);
    p.on("close", (code) => resolve({ code, stdout: out, stderr: err }));
  });
}

// 跑一条命令并要求成功，返回 stdout。失败抛出带 stderr 的错误。
export async function capture(cmd, args, { cwd, env } = {}) {
  const { code, stdout, stderr } = await run(cmd, args, { stdio: "pipe", cwd, env });
  if (code !== 0) throw new Error(`${cmd} 退出码 ${code}: ${stderr.trim().split("\n").slice(-3).join(" | ")}`);
  return stdout;
}
