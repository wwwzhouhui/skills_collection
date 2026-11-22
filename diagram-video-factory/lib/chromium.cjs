// 本机 Chromium 定位（跨平台）。
// 本机装的 ms-playwright 版本常与当前 playwright 包要求的版本不一致（会报 "Executable doesn't exist at ...chromium-XXXX"）。
// 这里按优先级找可用的 chromium 可执行文件，找不到就返回 null（交由 playwright 自己解析）。
//   1) config.render.chromium（显式指定）
//   2) 环境变量 WB_CHROMIUM
//   3) 用户 ms-playwright 缓存里版本号最高的 chromium-*
const fs = require('fs');
const os = require('os');
const path = require('path');

function resolveChromium(explicit) {
  if (explicit && fs.existsSync(explicit)) return explicit;
  if (process.env.WB_CHROMIUM && fs.existsSync(process.env.WB_CHROMIUM)) return process.env.WB_CHROMIUM;
  const home = os.homedir();
  const roots = [
    process.env.LOCALAPPDATA,
    path.join(home, 'AppData', 'Local'),
    path.join(home, 'Library', 'Caches'),
    path.join(home, '.cache'),
  ].filter(Boolean);
  const rels = [
    'chrome-win64/chrome.exe', 'chrome-win/chrome.exe',
    'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
    'chrome-linux/chrome',
  ];
  const found = [];
  for (const r of roots) {
    const base = path.join(r, 'ms-playwright');
    if (!fs.existsSync(base)) continue;
    for (const d of fs.readdirSync(base)) {
      const m = d.match(/^chromium-(\d+)$/);
      if (!m) continue;
      for (const rel of rels) {
        const exe = path.join(base, d, rel);
        if (fs.existsSync(exe)) found.push({ rev: Number(m[1]), exe });
      }
    }
  }
  if (!found.length) return null;
  found.sort((a, b) => b.rev - a.rev);
  return found[0].exe;
}

module.exports = { resolveChromium };
