#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
video.py —— 沉浸式诗词页面 Skill 的「口播视频」流水线。

职责：把第 4 步生成好的场景图、第 5 步生成好的朗诵音轨（及其逐行时间轴 sidecar）、
第 6 步页面里的诗文本色板与设计 tokens，钉成一条帧级时间轴，交给 Remotion 渲染成片。

设计上遵循 video-shotcraft 的三条硬原则：
  1. 画面用真实素材——这里的"真实"就是图像管线的产出，视频层不手搓任何 UI。
  2. 视觉语言从页面自身长出来——色板/字体直接取 poetry-page 的 CSS tokens。
  3. 先有人声，后有镜头——权威时间轴是 narration.py 的 sidecar，画面只是被钉上去。

子命令：
  probe    检查渲染链路（node / remotion / ffmpeg / 浏览器可执行文件 / node_modules）
  init     从 assets/video-template 建立 Remotion 工作区
  build    读 video-plan.json + sidecar，生成帧级时间轴与素材
  render   渲染成片
  still    渲染单个或多个静帧用于验收
  frames   从成片抽关键帧
  run      init → build → render → frames 一次跑完

配置集中在 config/ark.config.json 的 video 块。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------- 基础路径

SKILL_DIR = Path(__file__).resolve().parent.parent
ROOT_CONFIG = SKILL_DIR / "config" / "ark.config.json"
TEMPLATE_DIR = SKILL_DIR / "assets" / "video-template"

COMPOSITION_ID = "PoemVoiceover"

IS_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------- 输出辅助

def _log(msg: str) -> None:
    print(msg, flush=True)


def _warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr, flush=True)


def _die(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[valid-type]
    print(f"[error] {msg}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- 配置

DEFAULTS = {
    "engine": "remotion",
    "template_dir": str(TEMPLATE_DIR),
    "workspace": "video",
    "fps": 30,
    "width": 1920,
    "height": 1080,
    "crossfade_frames": 14,
    "grain_opacity": 0.07,
    "tail_seconds": 3.0,
    "lead_seconds": 0.0,
    # 动效三旋钮：运镜倍率、手持微抖幅度（像素）、原文层是否逐字点亮。
    "motion_gain": 1.0,
    "handheld_px": 3.4,
    "caption_reveal": True,
    "default_transition": "crossfade",
    "node_modules": None,
    "browser_executable": None,
    "concurrency": None,
}


def load_video_config(config_path: Path | None = None) -> dict:
    """读取 config/ark.config.json 的 video 块，缺字段用 DEFAULTS 兜。"""
    cfg = dict(DEFAULTS)
    path = config_path or ROOT_CONFIG
    if path.exists():
        data = _load_json(path)
        block = data.get("video") or {}
        for key, value in block.items():
            if value is not None:
                cfg[key] = value
    return cfg


# ---------------------------------------------------------------- probe

def _which(name: str) -> str | None:
    return shutil.which(name)


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def cmd_probe(args: argparse.Namespace) -> int:
    cfg = load_video_config(args.config)
    ok = True

    node = _which("node")
    npm = _which("npm")
    ff = _which("ffmpeg")
    fp = _which("ffprobe")

    _log("渲染链路检查")
    _log("-" * 62)
    for label, found in (("node", node), ("npm", npm), ("ffmpeg", ff), ("ffprobe", fp)):
        if found:
            _log(f"  OK    {label:<10} {found}")
        else:
            _log(f"  MISS  {label:<10} 未找到")
            ok = found is not None or ok
            if found is None and label in ("node", "ffmpeg", "ffprobe"):
                ok = False

    if node:
        r = _run([node, "-v"])
        _log(f"        node 版本  {r.stdout.strip()}")

    # Remotion 模板
    template = Path(cfg["template_dir"])
    if not template.is_absolute():
        template = SKILL_DIR / template
    if template.exists():
        _log(f"  OK    template   {template}")
    else:
        _log(f"  MISS  template   {template}")
        ok = False

    # node_modules：工作区自己有，或能从别处复用
    ws = Path(args.workspace) if args.workspace else None
    sources = [p for p in [ws / "node_modules" / "remotion" if ws else None,
                           Path(cfg["node_modules"]) / "remotion" if cfg.get("node_modules") else None] if p]
    found_nm = next((p for p in sources if p.exists()), None)
    if found_nm:
        _log(f"  OK    remotion   {found_nm.parent.parent}")
    else:
        _log("  MISS  remotion   工作区没有依赖，init 时用 --node-modules 指定一个现成安装，或跑 npm install")

    # 浏览器
    browser = resolve_browser(cfg)
    explicit = cfg.get("browser_executable")
    if browser:
        _log(f"  OK    browser    {browser}"
             + ("" if explicit else "（自动探测）"))
        if not explicit:
            _log("        note: 把这条路径写进 config/ark.config.json 的 video.browser_executable 可省掉每次探测。")
    else:
        _log("  MISS  browser    未找到 Chrome/Edge。Remotion 需要浏览器二进制；"
             "离线环境下请装 Chrome 并把路径写进 video.browser_executable")
        ok = False

    _log("-" * 62)
    _log("结论：" + ("可以渲染。" if ok else "链路不完整，按上面的 MISS 项补齐后再跑 render。"))
    return 0 if ok else 1


# ---------------------------------------------------------------- init

def _remotion_bin(workspace: Path) -> list[str] | None:
    """优先用工作区自己的 CLI，避免 npx 每次联网探查。"""
    bdir = workspace / "node_modules" / ".bin"
    for name in (["remotion.cmd", "remotion"] if IS_WINDOWS else ["remotion"]):
        p = bdir / name
        if p.exists():
            return [str(p)]
    return None


def cmd_init(args: argparse.Namespace) -> int:
    cfg = load_video_config(args.config)
    template = Path(cfg["template_dir"])
    if not template.is_absolute():
        template = SKILL_DIR / template
    if not template.exists():
        _die(f"找不到模板目录：{template}")

    ws = Path(args.workspace).resolve()

    # 整棵 src/ 复制，而不是维护一份文件清单——清单漏一个新文件（比如新加的
    # lib/fx.tsx），工作区就会用一个半旧的模板渲染，报错还很难看懂。
    for rel in ("remotion.config.ts", "tsconfig.json", "package.json"):
        shutil.copy2(template / rel, ws / rel)

    src_root = template / "src"
    for src in sorted(src_root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(template)
        dst = ws / rel
        # timeline.generated.ts 只在缺失时补占位。否则 init 会把上一次 build 的
        # 成果打回占位时间轴，之后必须记得再 build 一次，是个很容易踩的坑。
        if rel.as_posix() == "src/timeline.generated.ts" and dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    (ws / "public").mkdir(parents=True, exist_ok=True)
    (ws / "out").mkdir(parents=True, exist_ok=True)
    _log(f"工作区已就绪：{ws}")

    if (ws / "node_modules" / "remotion").exists():
        _log("依赖：已存在，跳过。")
        return 0

    source = args.node_modules or cfg.get("node_modules")
    if source:
        source = Path(source)
        if source.exists():
            _log(f"依赖：复制 {source} → {ws / 'node_modules'}（本机复用，不联网）")
            shutil.copytree(source, ws / "node_modules", dirs_exist_ok=True)
            _log("依赖：完成。")
            return 0
        _warn(f"指定的 node_modules 不存在：{source}")

    _log("依赖：未指定来源，尝试 npm install（需要网络）…")
    r = _run(["npm", "install", "--no-audit", "--no-fund"], cwd=ws)
    if r.returncode != 0:
        _warn(r.stdout[-1500:])
        _warn(r.stderr[-1500:])
        _die("npm install 失败。离线环境请指定 --node-modules <已装好的 node_modules 路径>")
    _log("依赖：完成。")
    return 0


# ---------------------------------------------------------------- 时间轴构建

def _group_runs_by_paragraph(lines: list[dict]) -> list[list[int]]:
    """按 sidecar 的 paragraph 字段切成连续段，返回每段的 line index 列表（1-based）。"""
    runs: list[list[int]] = []
    current_para = None
    for ln in lines:
        p = ln.get("paragraph", 1)
        if current_para is None or p != current_para:
            runs.append([ln["index"]])
            current_para = p
        else:
            runs[-1].append(ln["index"])
    return runs


def _distribute(indices: list[int], buckets: int) -> list[list[int]]:
    """把 n 行尽量均匀地分到 buckets 个镜头里（允许空桶时由调用方过滤）。"""
    n = len(indices)
    buckets = max(1, buckets)
    base = n // buckets
    extra = n % buckets
    out: list[list[int]] = []
    cursor = 0
    for i in range(buckets):
        take = base + (1 if i < extra else 0)
        out.append(indices[cursor:cursor + take])
        cursor += take
    return out


def resolve_shot_lines(plan_shots: list[dict], lines: list[dict]) -> list[list[int]]:
    """
    决定每个镜头覆盖哪些 sidecar 行。

    优先级：plan 里显式写了 lines → 直接用；否则自动分：
      - 段落切分的行数刚好等于镜头数（with-meaning 这类「原文+释义」稿就是这种情况）→ 1:1 映射；
      - 否则按行数均匀分配。朗诵版只有 4 个段落但有 8 张图，走的就是均匀分配。
    """
    explicit = [s.get("lines") for s in plan_shots]
    if any(explicit):
        if not all(explicit):
            missing = [i for i, e in enumerate(explicit) if not e]
            _die(f"video-plan 里 lines 字段要么全部省略，要么全部填写；缺少的镜头序号：{missing}")
        return [[int(i) for i in grp] for grp in explicit]  # type: ignore[arg-type]

    all_indices = [ln["index"] for ln in lines]
    runs = _group_runs_by_paragraph(lines)
    if len(runs) == len(plan_shots):
        return runs
    return _distribute(all_indices, len(plan_shots))


def classify_role(text: str, line_index: int, original_lines: list[str], title_shot_index: int | None,
                  shot_index: int) -> str:
    """
    字幕角色决定排版层级：
      - 标题镜头里的行 → title（会被 TitleCard 替掉）
      - 原文行        → verse（大号衬线）
      - 其余          → prose（解释层，小一号）

    判定依据是「这句话是否出现在原诗里」，不猜站位：讲解稿原文与释义交替出现，
    朗诵稿却通篇都是原文，两种稿子的角色分布完全不同。
    """
    if shot_index == title_shot_index:
        return "title"
    norm = "".join(text.split())
    if not original_lines:
        return "verse"
    for src in original_lines:
        if norm == "".join(src.split()):
            return "verse"
    return "prose"


def build_timeline(plan: dict, plan_dir: Path, cfg: dict, ws_override: Path | None = None):
    """把 video-plan.json + sidecar 编译成帧级时间轴。"""
    fps = int(plan.get("fps", cfg["fps"]))
    width = int(plan.get("width", cfg["width"]))
    height = int(plan.get("height", cfg["height"]))
    crossfade = int(plan.get("crossfade_frames", cfg["crossfade_frames"]))
    tail = float(plan.get("tail_seconds", cfg["tail_seconds"]))
    lead = float(plan.get("lead_seconds", cfg["lead_seconds"]))

    timing_path = plan_dir / plan["timing"]
    if not timing_path.exists():
        _die(f"找不到配音时间轴 sidecar：{timing_path}")
    sidecar = _load_json(timing_path)
    lines = sidecar["lines"]
    audio_seconds = float(sidecar["duration_seconds"])

    plan_shots = plan["shots"]
    if not plan_shots:
        _die("video-plan.json 的 shots 为空。")

    groups = resolve_shot_lines(plan_shots, lines)
    total_seconds = audio_seconds + tail
    total_frames = int(round(total_seconds * fps))

    # ---- 镜头边界：相邻两句之间的静默中点，保证画面连续不黑屏
    boundaries: list[tuple[float, float]] = []
    for k, group in enumerate(groups):
        first = next(ln for ln in lines if ln["index"] == group[0])
        last = next(ln for ln in lines if ln["index"] == group[-1])
        if k == 0:
            start_sec = max(0.0, first["start"] - lead)
        else:
            prev_group = groups[k - 1]
            prev_last = next(ln for ln in lines if ln["index"] == prev_group[-1])
            start_sec = (prev_last["end"] + first["start"]) / 2.0
        if k == len(groups) - 1:
            end_sec = total_seconds
        else:
            next_group = groups[k + 1]
            next_first = next(ln for ln in lines if ln["index"] == next_group[0])
            end_sec = (last["end"] + next_first["start"]) / 2.0
        boundaries.append((max(0.0, start_sec), end_sec))

    _log(f"镜头 {len(groups)} 个｜人声 {len(lines)} 句｜音轨 {audio_seconds:.2f}s｜成片 {total_seconds:.2f}s / {total_frames} 帧")

    # ---- 素材落到工作区 public/
    ws = Path(plan.get("workspace") or plan_dir / cfg["workspace"])
    if not ws.is_absolute():
        ws = (plan_dir / ws).resolve()
    images_dir = plan_dir / plan["images_dir"]

    scenes_dir = ws / "public" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    audio_src = plan_dir / plan["audio"]
    if not audio_src.exists():
        _die(f"找不到配音文件：{audio_src}")
    audio_dir = ws / "public" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_dst_name = audio_src.name
    shutil.copy2(audio_src, audio_dir / audio_dst_name)

    title_shot_index = None
    for i, s in enumerate(plan_shots):
        if s.get("role") == "title":
            title_shot_index = i
            break

    original_lines = plan.get("original_lines") or []
    roles_by_line = {}
    for k, group in enumerate(groups):
        for idx in group:
            ln = next(x for x in lines if x["index"] == idx)
            roles_by_line[idx] = classify_role(ln["text"], idx, original_lines, title_shot_index, k)

    shots: list[dict] = []
    for k, (s, group) in enumerate(zip(plan_shots, groups)):
        start_sec, end_sec = boundaries[k]
        start_f = 0 if k == 0 else math.floor(start_sec * fps)
        end_f = total_frames if k == len(groups) - 1 else math.floor(end_sec * fps)
        if k > 0 and shots:
            start_f = max(start_f, shots[-1]["from"] + 1)
        duration = max(1, end_f - start_f)

        name = s["image"]
        src_file = images_dir / name
        if not src_file.exists():
            _die(f"找不到场景图：{src_file}")
        dst = scenes_dir / name
        if not dst.exists() or dst.stat().st_mtime < src_file.stat().st_mtime:
            shutil.copy2(src_file, dst)

        shots.append({
            "index": k,
            "from": start_f,
            "durationInFrames": duration,
            "src": f"scenes/{name}",
            "move": s.get("move", "auto"),
            "role": s.get("role", "beat"),
            "seed": int(s.get("seed", k * 977 + 31)),
            # 转场与气层都允许逐镜指定；不写就 crossfade / auto（由镜头序号派生）。
            "transition": s.get("transition", plan.get("default_transition", "crossfade")),
            "fx": s.get("fx", "auto"),
        })
        _log(f"  镜头 {k}  {start_f:>5}→{end_f:<5} ({duration:>4}帧) {name:<14} "
             f"{s.get('move','auto'):<11} {str(s.get('transition','crossfade')):<12} "
             f"{str(s.get('fx','auto')):<7} 行 {group}")

    captions: list[dict] = []
    line_to_shot = {}
    for k, group in enumerate(groups):
        for idx in group:
            line_to_shot[idx] = k
    for ln in lines:
        start_f = max(0, math.floor(ln["start"] * fps))
        end_f = min(total_frames, math.ceil(ln["end"] * fps))
        if end_f <= start_f:
            end_f = start_f + 1
        captions.append({
            "text": ln["text"],
            "start": start_f,
            "end": end_f,
            "role": roles_by_line.get(ln["index"], "verse"),
            "shot": line_to_shot.get(ln["index"], 0),
        })

    verse_n = sum(1 for c in captions if c["role"] == "verse")
    prose_n = sum(1 for c in captions if c["role"] == "prose")
    _log(f"字幕 {len(captions)} 条：原文 {verse_n} / 释义 {prose_n} / 标题 {len(captions) - verse_n - prose_n}")

    palette = plan.get("palette") or {
        "ink": "#0d0f10", "moon": "#e6e2d6", "gold": "#d9a84e",
        "amber": "#a8641f", "ochre": "#b8763a",
    }

    timeline = {
        "slug": plan.get("slug", plan_dir.name),
        "fps": fps,
        "width": width,
        "height": height,
        "durationInFrames": total_frames,
        "audio": f"audio/{audio_dst_name}",
        "audioVolume": plan.get("audio_volume", 1),
        "bgm": plan.get("bgm"),
        "bgmVolume": plan.get("bgm_volume", 0.3),
        "title": plan.get("title", ""),
        "author": plan.get("author", ""),
        "era": plan.get("era", ""),
        "genre": plan.get("genre", ""),
        "closing": plan.get("closing", ""),
        "palette": palette,
        "font": plan.get("font"),
        "crossfadeFrames": crossfade,
        "grainOpacity": plan.get("grain_opacity", cfg["grain_opacity"]),
        "motionGain": float(plan.get("motion_gain", cfg["motion_gain"])),
        "handheldPx": float(plan.get("handheld_px", cfg["handheld_px"])),
        "captionReveal": bool(plan.get("caption_reveal", cfg["caption_reveal"])),
        "shots": shots,
        "captions": captions,
    }
    if not timeline["font"]:
        timeline.pop("font")

    return timeline, ws


def _write_timeline_module(timeline: dict, ws: Path) -> Path:
    """把时间轴写成一个 TS 模块。

    写 TS 而不是 JSON，是不想在 tsconfig 里再开一个开关；所有字符串都走
    json.dumps，转义规则和 JSON 一致，中文与反引号都不会破壳。
    """
    body = json.dumps(timeline, ensure_ascii=False, indent=2)
    content = (
        "/* eslint-disable */\n"
        "// 自动生成文件 —— 请勿手工编辑。\n"
        f"// 由 scripts/video.py build 生成（slug: {timeline.get('slug', '')}）。\n\n"
        "export type ShotRole = 'title' | 'beat' | 'outro';\n"
        "export type CaptionRole = 'verse' | 'prose' | 'title';\n\n"
        "export interface Shot {\n"
        "  index: number;\n"
        "  from: number;\n"
        "  durationInFrames: number;\n"
        "  src: string;\n"
        "  move: string;\n"
        "  role: ShotRole;\n"
        "  seed: number;\n"
        "}\n\n"
        "export interface Caption {\n"
        "  text: string;\n"
        "  start: number;\n"
        "  end: number;\n"
        "  role: CaptionRole;\n"
        "  shot: number;\n"
        "}\n\n"
        f"export const timeline = {body} as unknown as {{\n"
        "  slug: string; fps: number; width: number; height: number; durationInFrames: number;\n"
        "  audio: string | null; audioVolume: number; bgm: string | null; bgmVolume: number;\n"
        "  title: string; author: string; era: string; genre: string; closing: string;\n"
        "  palette: Record<string, string>; font?: { serif: string; sans: string };\n"
        "  crossfadeFrames: number; grainOpacity: number;\n"
        "  shots: Shot[]; captions: Caption[];\n"
        "};\n"
    )
    out = ws / "src" / "timeline.generated.ts"
    out.write_text(content, encoding="utf-8")
    return out


def cmd_build(args: argparse.Namespace) -> int:
    cfg = load_video_config(args.config)
    plan_path = Path(args.plan).resolve()
    if not plan_path.exists():
        _die(f"找不到 video-plan.json：{plan_path}")
    plan_dir = plan_path.parent
    plan = _load_json(plan_path)

    ws = Path(args.workspace).resolve() if args.workspace else None
    timeline, ws = build_timeline(plan, plan_dir, cfg, ws)

    out = _write_timeline_module(timeline, ws)
    _log(f"时间轴已写入：{out}")

    # 按 variant 归档一份，永远不被下一次 build 覆盖。否则同一个工作区
    # 先后渲两个变体时，timeline.json 被改写，旧片子的时间基准就丢了，
    # 终检会拿错的时间轴去核对抽帧。
    slug = timeline["slug"]
    json_out = ws / f"timeline-{slug}.json"
    previous = None
    cur = ws / "timeline.json"
    if cur.exists():
        try:
            previous = _load_json(cur).get("slug")
        except Exception:
            previous = None
    json_out.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    cur.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    _log(f"时间轴（本 variant 归档）已写入：{json_out}")
    if previous and previous != slug:
        _warn(f"timeline.json 已从「{previous}」切到「{slug}」。"
              f"之前那个变体的时间基准在 {ws / ('timeline-' + previous + '.json')}，"
              "对它做 QA 时用 --timeline 显式指定。")

    if args.emit_plan_summary:
        _log_plan_summary(timeline)
    return 0


def _log_plan_summary(t: dict) -> None:
    _log("")
    _log("分镜概览（秒 → 帧）")
    _log("-" * 92)
    _log(f"{'#':>2}  {'入场':>7} {'时长':>6}  {'画面':<14} {'运镜':<11} {'转场':<12} {'气层':<7} 说明")
    for s in t["shots"]:
        seg = [c["text"] for c in t["captions"] if c["shot"] == s["index"]]
        head = seg[0][:30] if seg else ""
        fx = s.get("fx", "auto")
        fx_label = fx if isinstance(fx, str) else "custom"
        _log(f"{s['index']:>2}  {s['from']:>7} {s['durationInFrames']:>6}  "
             f"{s['src'].split('/')[-1]:<14} {s['move']:<11} "
             f"{str(s.get('transition', 'crossfade')):<12} {fx_label:<7} {head}")
    _log("-" * 92)


# ---------------------------------------------------------------- 渲染

BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def resolve_browser(cfg: dict) -> str | None:
    """优先用配置里指定的浏览器；没指定就按常见安装位置自动探测。"""
    explicit = cfg.get("browser_executable")
    if explicit:
        return explicit if Path(explicit).exists() else None
    return next((c for c in BROWSER_CANDIDATES if Path(c).exists()), None)


def _render_cmd(ws: Path, cfg: dict, extra: list[str]) -> list[str]:
    b = _remotion_bin(ws)
    if b is None:
        if not _which("npx"):
            _die("工作区缺少 @remotion/cli，也没有 npx。先跑 init。")
        b = ["npx", "remotion"]
    cmd = b + extra

    browser = resolve_browser(cfg)
    if browser:
        cmd.append(f"--browser-executable={browser}")
    conc = cfg.get("concurrency")
    if conc:
        cmd.append(f"--concurrency={conc}")
    return cmd


def _load_timeline(ws: Path, explicit: str | None) -> dict:
    """QA 命令的时间轴解析：显式 --timeline 优先，否则用当前 timeline.json。

    工作区里每个 variant 另有一份永不覆盖的 timeline-<slug>.json 归档；
    回头复核旧片子时必须用 --timeline 指到那份归档。
    """
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = ws / p
        if not p.exists():
            _die(f"找不到时间轴：{p}")
        return _load_json(p)
    cur = ws / "timeline.json"
    if not cur.exists():
        _die(f"工作区还没有时间轴，先跑 build：{cur}")
    return _load_json(cur)


def _video_duration(path: Path) -> float:
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "csv=p=0", str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def cmd_render(args: argparse.Namespace) -> int:
    cfg = load_video_config(args.config)
    ws = Path(args.workspace).resolve()
    timeline = _load_timeline(ws, getattr(args, "timeline", None))
    out_name = args.out or f"{timeline['slug']}.mp4"
    out_path = Path(out_name)
    if not out_path.is_absolute():
        out_path = ws / "out" / out_name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    extra = ["render", "src/index.ts", COMPOSITION_ID, str(out_path)]
    if args.frames:
        extra.append(f"--frames={args.frames}")

    cmd = _render_cmd(ws, cfg, extra)
    _log("渲染：" + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    r = subprocess.run(cmd, cwd=str(ws))
    if r.returncode != 0:
        _die(f"渲染失败（exit {r.returncode}）")
    _log(f"成片：{out_path}")
    return 0


def cmd_still(args: argparse.Namespace) -> int:
    cfg = load_video_config(args.config)
    ws = Path(args.workspace).resolve()
    timeline = _load_timeline(ws, getattr(args, "timeline", None))

    outdir = ws / "out" / "qa"
    outdir.mkdir(parents=True, exist_ok=True)

    if args.frames:
        frames = [int(x) for x in args.frames.split(",") if x.strip()]
    else:
        # 默认每个镜头的入场中与中段各一帧——这是最容易暴露构图问题的两个时刻
        frames = []
        for s in timeline["shots"]:
            frames.append(s["from"] + 6)
            frames.append(s["from"] + s["durationInFrames"] // 2)

    for f in frames:
        label = f"f{f:04d}"
        out = outdir / f"{timeline['slug']}-{label}.png"
        cmd = _render_cmd(ws, cfg, ["still", "src/index.ts", COMPOSITION_ID, str(out), f"--frame={f}"])
        r = subprocess.run(cmd, cwd=str(ws))
        if r.returncode != 0:
            _warn(f"第 {f} 帧渲染失败")
        else:
            _log(f"  {out}")
    return 0


def cmd_frames(args: argparse.Namespace) -> int:
    ws = Path(args.workspace).resolve()
    src = Path(args.input)
    if not src.is_absolute():
        # `--input out/x.mp4`（相对工作区）与 `--input x.mp4`（相对 out/）都接受
        cand = ws / src
        src = cand if cand.exists() else ws / "out" / src
    if not src.exists():
        _die(f"找不到成片：{src}")

    timeline = _load_timeline(ws, getattr(args, "timeline", None))
    slug = timeline["slug"]
    fps = float(timeline["fps"])
    video_seconds = _video_duration(src)

    outdir = ws / "out" / "qa_extracts"
    outdir.mkdir(parents=True, exist_ok=True)

    if args.at:
        times = [float(x) for x in args.at.split(",") if x.strip()]
    else:
        times = []
        for s in timeline["shots"]:
            times.append((s["from"] + 4) / fps)
            times.append((s["from"] + s["durationInFrames"] / 2) / fps)
            times.append((s["from"] + s["durationInFrames"] - 3) / fps)

    skipped = 0
    written = 0
    for tt in times:
        if video_seconds and tt > video_seconds:
            # 时间轴超出成片时长：多半是 timeline.json 属于另一个变体
            skipped += 1
            continue
        out = outdir / f"{slug}-{written + 1:02d}_t{tt:06.2f}s.png"
        cmd = ["ffmpeg", "-y", "-ss", f"{tt:.3f}", "-i", str(src), "-frames:v", "1", str(out)]
        r = _run(cmd)
        if r.returncode != 0:
            _warn(f"{tt}s 抽帧失败")
        else:
            written += 1
            _log(f"  {out}")

    if skipped:
        _warn(f"有 {skipped} 个采样点超出成片时长（{video_seconds:.1f}s）被跳过——"
              "确认 timeline.json 与成片是不是同一个变体；"
              "旧变体的时间轴在 timeline-<slug>.json，用 --timeline 指定。")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """init → build → still → render → frames，一条命令跑完。

    中间产物全部留档：out/qa/ 是静帧，out/qa_extracts/ 是从成片抽回来的帧。
    两者互相对照，能发现「预览里没出现、渲染后才暴露」的问题。
    """
    _log("== init ==")
    if cmd_init(args) != 0:
        return 1

    _log("== build ==")
    if cmd_build(args) != 0:
        return 1

    _log("== still（每镜头入场与中段）==")
    args.frames = getattr(args, "frames", None)
    args.timeline = getattr(args, "timeline", None)
    cmd_still(args)

    _log("== render ==")
    args.out = args.out or None
    if cmd_render(args) != 0:
        return 1

    _log("== frames（从成片回抽）==")
    ws = Path(args.workspace).resolve()
    timeline = _load_timeline(ws, None)
    args.input = str(ws / "out" / f"{timeline['slug']}.mp4")
    args.at = getattr(args, "at", None)
    return cmd_frames(args)


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="video.py",
        description="沉浸式诗词页面的口播视频流水线（图片 + 朗诵 + 字幕 → Remotion 成片）",
    )
    ap.add_argument("--config", help="config/ark.config.json 路径")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_probe = sub.add_parser("probe", help="检查渲染链路")
    p_probe.add_argument("--workspace", help="待检查的工作区（用于确认依赖是否就绪）")
    p_probe.set_defaults(func=cmd_probe)

    p_init = sub.add_parser("init", help="建立 Remotion 工作区")
    p_init.add_argument("--workspace", required=True)
    p_init.add_argument("--node-modules", help="复用一个已安装好的 node_modules（离线环境推荐）")
    p_init.set_defaults(func=cmd_init)

    p_build = sub.add_parser("build", help="生成帧级时间轴")
    p_build.add_argument("--plan", required=True, help="video-plan.json 路径")
    p_build.add_argument("--workspace", help="覆盖默认工作区路径")
    p_build.add_argument("--emit-plan-summary", action="store_true", help="打印分镜概览")
    p_build.set_defaults(func=cmd_build)

    p_render = sub.add_parser("render", help="渲染成片")
    p_render.add_argument("--workspace", required=True)
    p_render.add_argument("--out", help="输出文件名或绝对路径")
    p_render.add_argument("--frames", help="只渲某段，格式 0-299")
    p_render.add_argument("--timeline", help="指定 timeline-<slug>.json（复核旧变体时用）")
    p_render.set_defaults(func=cmd_render)

    p_still = sub.add_parser("still", help="渲染静帧用于验收")
    p_still.add_argument("--workspace", required=True)
    p_still.add_argument("--frames", help="逗号分隔的帧号；缺省取每镜头入场与中段")
    p_still.set_defaults(func=cmd_still)

    p_fr = sub.add_parser("frames", help="从成片抽关键帧")
    p_fr.add_argument("--workspace", required=True)
    p_fr.add_argument("--input", required=True)
    p_fr.add_argument("--at", help="逗号分隔的秒数；缺省按镜头自动取")
    p_fr.add_argument("--timeline", help="指定 timeline-<slug>.json")
    p_fr.set_defaults(func=cmd_frames)

    p_run = sub.add_parser("run", help="init → build → still → render → frames 一次跑完")
    p_run.add_argument("--plan", required=True)
    p_run.add_argument("--workspace", required=True)
    p_run.add_argument("--node-modules", help="复用已安装好的 node_modules")
    p_run.add_argument("--render-range", dest="render_range", help="只渲某段，格式 0-299")
    p_run.add_argument("--out", help="输出文件名或绝对路径")
    p_run.add_argument("--emit-plan-summary", action="store_true")
    p_run.set_defaults(func=cmd_run, frames=None, at=None, render_range=None)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
