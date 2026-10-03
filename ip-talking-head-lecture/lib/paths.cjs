// 目录约定 + 配置加载。
//   期目录：内容放 <projects>/<期>/（script.json、旁白稿.md、封面、README）—— 人看人改
//   后台目录：<build>/<期>/work/{audio,public,out} 中间产物，<build>/<期>/outputs/ 成片
const fs = require('fs');
const os = require('os');
const path = require('path');

// ⚠️Windows 上 process.env.HOME 常是 Git Bash 的 MSYS 路径（/c/Users/x），Node 会当成
//   「当前盘符下的 \c\Users\x」→ 一律以 os.homedir() 为准。
const HOME = os.homedir() || process.env.HOME || '';
const ROOT = path.join(__dirname, '..');

const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'config.json'), 'utf8'));

const expand = (p) => {
  const e = String(p).replace(/^~/, HOME);
  return path.isAbsolute(e) ? e : path.join(ROOT, e);
};

const PROJECTS_DIR = expand(cfg.dirs.projects);
const BUILD_DIR = expand(cfg.dirs.build);

function projectPaths(projectDir) {
  const project = path.resolve(projectDir);
  const name = path.basename(project);
  const studio = path.join(BUILD_DIR, name);
  const work = path.join(studio, 'work');
  return {
    name,
    project,
    studio,
    work,
    outputs: path.join(studio, 'outputs'),
    script: path.join(project, 'script.json'),
    note: path.join(project, '旁白稿.md'),
    assets: path.join(project, 'assets'),      // 本期专属素材（可选）
    audio: path.join(work, 'audio'),
    // Remotion 的 staticFile 根目录。放在工程内（而不是本期 work/）省掉 --public-dir 参数，
    // 代价是每期构建前要清一次 audio/avatar 子目录（见 build.mjs）。
    publicDir: path.join(ROOT, 'remotion', 'public'),
    timeline: path.join(work, 'timeline.json'),
    out: path.join(work, 'out'),
    srt: path.join(project, '字幕.srt'),
    vtt: path.join(project, '字幕.vtt'),
    srtEn: path.join(project, '字幕.en.srt'),
    vttEn: path.join(project, '字幕.en.vtt'),
    publish: path.join(project, '发布文案.md'),
    final: (ratio) => path.join(studio, 'outputs', `final-${String(ratio).replace(':', 'x')}.mp4`),
  };
}

// 参数可以是绝对路径、期目录名，或标题的任意子串（大小写不敏感，多个匹配取最新）
function resolveProject(arg) {
  if (!arg) throw new Error('缺少期参数');
  if (fs.existsSync(arg) && fs.statSync(arg).isDirectory()) return path.resolve(arg);
  const direct = path.join(PROJECTS_DIR, arg);
  if (fs.existsSync(direct)) return direct;
  if (!fs.existsSync(PROJECTS_DIR)) throw new Error(`期目录还不存在：${PROJECTS_DIR}`);
  const list = fs
    .readdirSync(PROJECTS_DIR)
    .filter((d) => fs.statSync(path.join(PROJECTS_DIR, d)).isDirectory() && !d.startsWith('.'));
  const hit = list.filter((d) => d.toLowerCase().includes(arg.toLowerCase())).sort();
  if (!hit.length) throw new Error(`找不到「${arg}」，现有：${list.join(' | ') || '(空)'}`);
  return path.join(PROJECTS_DIR, hit[hit.length - 1]);
}

function listProjects() {
  if (!fs.existsSync(PROJECTS_DIR)) return [];
  return fs
    .readdirSync(PROJECTS_DIR)
    .filter((d) => fs.existsSync(path.join(PROJECTS_DIR, d, 'script.json')))
    .sort();
}

module.exports = { ROOT, cfg, HOME, PROJECTS_DIR, BUILD_DIR, projectPaths, resolveProject, listProjects, expand };
