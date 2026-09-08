#!/usr/bin/env node
/** selftest.mjs — tts.py 解析与 build-timeline.mjs 的回归测试（无需网络，不调用 TTS）
 *
 * 用法: node <skill>/scripts/selftest.mjs
 * 覆盖: ① Markdown 剥离（模板格式旁白稿解析） ② 时间线生成（FPS/时长公式/vo:false）
 *       ③ 非法输入校验（重复 id / 非法 visualMin / 零时长 / 段数不匹配）
 *       ④ types.ts 随场景自动更新 ⑤ SRT 逐句切分与区间 ⑥ 短场景警告不致命
 */
import {mkdirSync, writeFileSync, rmSync, readFileSync} from "node:fs";
import {spawnSync} from "node:child_process";
import {join, dirname} from "node:path";
import {tmpdir} from "node:os";
import {fileURLToPath} from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const BT = join(here, "build-timeline.mjs");

let passed = 0;
const failures = [];
const t = (name, ok, detail = "") => {
  if (ok) {
    passed++;
    console.log(`  ✓ ${name}`);
  } else {
    failures.push(name);
    console.log(`  ✗ ${name}${detail ? ` — ${detail}` : ""}`);
  }
};

const mkproj = (name, {durations, scenes, withSrc = true}) => {
  const dir = join(tmpdir(), `rvf-selftest-${name}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`);
  mkdirSync(join(dir, "build"), {recursive: true});
  if (withSrc) mkdirSync(join(dir, "src"), {recursive: true});
  writeFileSync(join(dir, "build", "durations.json"), JSON.stringify(durations));
  writeFileSync(join(dir, "build", "scenes.json"), JSON.stringify(scenes));
  return dir;
};
const runBT = (cwd) => spawnSync(process.execPath, [BT], {cwd, encoding: "utf8"});

const DUR = {
  voice: "zh-CN-YunyangNeural", rate: "+0%", fps: 30,
  scenes: [
    {i: 1, text: "第一句。第二句，还是第二句的一部分；第三句！", file: "vo/scene1.mp3", durationSec: 6.0, frames: 180},
    {i: 2, text: "矩阵场景旁白。", file: "vo/scene2.mp3", durationSec: 4.0, frames: 120},
  ],
};

console.log("== build-timeline.mjs ==");

// 1) 正常路径：FPS / 时长公式 / vo:false / types / SRT 逐句
{
  const dir = mkproj("ok", {
    durations: DUR,
    scenes: [
      {id: "hook", visualMin: 300},
      {id: "matrix", visualMin: 420, tail: 60},
      {id: "logo", visualMin: 90, vo: false},
    ],
  });
  const r = runBT(dir);
  t("正常生成退出码 0", r.status === 0, r.stderr.trim());
  const ts = readFileSync(join(dir, "src", "timeline.ts"), "utf8");
  t("导出 FPS=30", /export const FPS = 30;/.test(ts));
  t("时长 = max(visualMin, vo+tail)", /hook: \{from: 0, duration: 300\}/.test(ts) && /matrix: \{from: 300, duration: 420\}/.test(ts), ts);
  t("vo:false 不消耗配音段（logo from=720, VO_MAP 只含 hook/matrix）",
    /logo: \{from: 720, duration: 90\}/.test(ts) && /VO_MAP[\s\S]*hook: 1,[\s\S]*matrix: 2,/.test(ts)
    && !/logo: \d/.test(ts.split("VO_MAP").pop()));
  t("TOTAL_FRAMES = 810", /export const TOTAL_FRAMES = 810;/.test(ts));
  t("types.ts 生成 SceneId 联合类型", readFileSync(join(dir, "src", "types.ts"), "utf8").includes('"hook" | "matrix" | "logo"'));
  const srt = readFileSync(join(dir, "build", "subtitles.srt"), "utf8");
  t("SRT 逐句切分（3+1 句 → 4 条）", (srt.match(/ --> /g) || []).length === 4, `got ${(srt.match(/ --> /g) || []).length}`);
  t("SRT 首条从场景起点开始", srt.startsWith("1\n00:00:00,000 --> "));
  t("SRT 末句止于配音终点（不含 tail）", srt.includes("00:00:06,000\n第三句！"));
  t("SRT 第二场景区间 [10s,14s]", srt.includes("00:00:10,000 --> 00:00:14,000"));
  t("纯视觉镜头无字幕", !srt.includes("logo"));
  rmSync(dir, {recursive: true, force: true});
}

// 2) 重复 id
{
  const dir = mkproj("dup", {durations: DUR, scenes: [{id: "a", visualMin: 100}, {id: "a", visualMin: 100}]});
  const r = runBT(dir);
  t("重复 id 报错退出", r.status === 1 && r.stderr.includes("重复"), r.stderr.trim());
  rmSync(dir, {recursive: true, force: true});
}

// 3) 缺 visualMin
{
  const dir = mkproj("nomin", {durations: DUR, scenes: [{id: "a"}]});
  const r = runBT(dir);
  t("缺 visualMin 报错退出", r.status === 1 && r.stderr.includes("visualMin"), r.stderr.trim());
  rmSync(dir, {recursive: true, force: true});
}

// 4) 非法 visualMin
{
  const dir = mkproj("negmin", {durations: DUR, scenes: [{id: "a", visualMin: -5}]});
  const r = runBT(dir);
  t("负数 visualMin 报错退出", r.status === 1 && r.stderr.includes("visualMin"), r.stderr.trim());
  rmSync(dir, {recursive: true, force: true});
}

// 5) 零时长
{
  const dir = mkproj("zerodur", {durations: DUR, scenes: [{id: "logo", visualMin: 0, vo: false}]});
  const r = runBT(dir);
  t("零时长场景报错退出", r.status === 1 && r.stderr.includes("时长"), r.stderr.trim());
  rmSync(dir, {recursive: true, force: true});
}

// 6) 配音段数不匹配
{
  const dir = mkproj("mismatch", {durations: DUR, scenes: [{id: "a", visualMin: 100}]});
  const r = runBT(dir);
  t("scenes 少于配音段时报错退出", r.status === 1 && r.stderr.includes("只消耗"), r.stderr.trim());
  rmSync(dir, {recursive: true, force: true});
}

// 7) types.ts 随场景更新（第二次跑新增场景）
{
  const dir = mkproj("retype", {durations: DUR, scenes: [{id: "a", visualMin: 100}, {id: "b", visualMin: 100}]});
  runBT(dir);
  const DUR3 = {...DUR, scenes: [...DUR.scenes, {i: 3, text: "第三段。", file: "vo/scene3.mp3", durationSec: 2, frames: 60}]};
  writeFileSync(join(dir, "build", "durations.json"), JSON.stringify(DUR3));
  writeFileSync(join(dir, "build", "scenes.json"), JSON.stringify([
    {id: "a", visualMin: 100}, {id: "b", visualMin: 100}, {id: "c", visualMin: 100},
  ]));
  const r = runBT(dir);
  const types = readFileSync(join(dir, "src", "types.ts"), "utf8");
  t("types.ts 随场景重跑自动更新（新增 c）", r.status === 0 && types.includes('"c"'), types.trim());
  rmSync(dir, {recursive: true, force: true});
}

// 8) 短场景仅警告不失败（scenes 必须消耗完全部配音段，否则触发段数校验）
{
  const dir = mkproj("short", {
    durations: DUR,
    scenes: [
      {id: "hook", visualMin: 300},   // 消耗 vo1
      {id: "m", visualMin: 100},      // 消耗 vo2
      {id: "s", visualMin: 20, vo: false},  // 纯视觉短镜头 → 仅警告
    ],
  });
  const r = runBT(dir);
  t("短场景（<37f）警告但不失败", r.status === 0 && r.stderr.includes("⚠"), `${r.status} ${r.stderr.trim()}`);
  rmSync(dir, {recursive: true, force: true});
}

// 9) src 目录不存在也能生成
{
  const dir = mkproj("nosrc", {durations: DUR, scenes: [{id: "a", visualMin: 100}, {id: "b", visualMin: 100}], withSrc: false});
  const r = runBT(dir);
  t("src 目录缺失时自动创建", r.status === 0 && readFileSync(join(dir, "src", "timeline.ts"), "utf8").includes("SHOTS"), r.stderr.trim());
  rmSync(dir, {recursive: true, force: true});
}

console.log("\n== tts.py parse_segments（Markdown 剥离）==");
{
  const py = ["python", "python3", "py"].find(
    (x) => spawnSync(x, ["--version"], {encoding: "utf8", windowsHide: true}).status === 0
  );
  if (!py) {
    console.log("  ⚠ 未找到 python，跳过（不算失败）");
  } else {
    const testFile = join(tmpdir(), `rvf-parse-test-${Date.now()}.py`);
    writeFileSync(testFile, [
      "import sys",
      `sys.path.insert(0, ${JSON.stringify(here)})`,
      "from tts import parse_segments",
      "",
      "tpl = '''# 旁白稿（VOICEOVER_ZH）",
      "",
      "> 段落间空行分隔；一段 = 一个场景。",
      "> 中文语速约 4.2 字/秒。",
      "",
      "## 1 · hook",
      "",
      "（第一段旁白文字）",
      "",
      "## 2 · matrix",
      "",
      "（第二段旁白文字）",
      "'''",
      "a = parse_segments(tpl)",
      "assert a == ['（第一段旁白文字）', '（第二段旁白文字）'], a",
      "",
      "b = parse_segments('段A\\n## 标题\\n段B')",
      "assert b == ['段A', '段B'], b",
      "",
      "c = parse_segments('第一段。\\n\\n第二段。')",
      "assert c == ['第一段。', '第二段。'], c",
      "",
      "d = parse_segments('前言\\n\\n```\\ncode line\\n```\\n\\n后记')",
      "assert d == ['前言', '后记'], d",
      "",
      "print('OK')",
    ].join("\n"));
    const r = spawnSync(py, [testFile], {encoding: "utf8", windowsHide: true});
    t("模板格式/紧贴标题/纯文本/代码块 四用例", r.status === 0 && r.stdout.includes("OK"),
      (r.stderr || r.stdout || "").trim().slice(0, 300));
    rmSync(testFile, {force: true});
  }
}

console.log(`\n结果: ${passed} 通过, ${failures.length} 失败`);
if (failures.length) {
  failures.forEach((f) => console.log(`  ✗ ${f}`));
  process.exit(1);
}
