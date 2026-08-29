"""镜头切分: PySceneDetect 跑全片, 把切点写成 shots.json 时间轴缓存。

从 movie_cut/pipeline/step_vis_segment.py 移植。输出 JSON 契约与 movie_cut
的 timeline.json 逐字段一致 (video/duration/video_signature/segment_version/
threshold/min_len/frame_skip/fps/n_shots/shots[]), 下游工具靠这个契约互通,
不要增删改字段名。
"""
from __future__ import annotations

import json
import shutil
import subprocess
from .ffproc import run_proc
import time
from pathlib import Path

from .result import ToolResult
from .run_context import RunContext

# 与 movie_cut 保持同一版本串: 两边产物可互相复用缓存, 改合并算法时必须换版本号
SEGMENT_VERSION = "cover-all-v2"

PROBE_TIMEOUT_SECONDS = 60


def detect_shots(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("input_path"):
        return ToolResult(text="[ERROR] input_path is required")
    input_path = ctx.resolve(args["input_path"])
    if not input_path.is_file():
        return ToolResult(text=f"[ERROR] File not found: {input_path}")
    if not shutil.which("ffprobe"):
        return ToolResult(text="[ERROR] ffprobe not found on PATH")

    output_path = ctx.resolve(args.get("output_json") or "out/shots.json")
    threshold = _number_arg(args, "threshold", 27.0)
    if isinstance(threshold, ToolResult):
        return threshold
    min_len = _number_arg(args, "min_len", 0.8)
    if isinstance(min_len, ToolResult):
        return min_len
    frame_skip = _int_arg(args, "frame_skip", 0)
    if isinstance(frame_skip, ToolResult):
        return frame_skip
    force = args.get("force", False)
    if not isinstance(force, bool):
        return ToolResult(text="[ERROR] force must be a boolean", data={"force": force})
    if threshold <= 0:
        return ToolResult(text="[ERROR] threshold must be positive", data={"threshold": threshold})
    if min_len < 0:
        return ToolResult(text="[ERROR] min_len must be >= 0", data={"min_len": min_len})
    if frame_skip < 0:
        return ToolResult(text="[ERROR] frame_skip must be >= 0", data={"frame_skip": frame_skip})

    # 缓存复用: 输出已存在且 视频指纹+全部切分参数 都对上才复用。指纹是
    # path|size|mtime, 视频被覆盖/替换后 mtime 变化即失效。缓存文件本身
    # 读不出来 (损坏/半截) 不算错, 走重切分覆盖它。
    signature = file_signature(input_path)
    if output_path.exists() and not force:
        try:
            tl = load_json(output_path)
        except Exception:
            tl = None
        if (isinstance(tl, dict)
                and tl.get("video") == str(input_path)
                and tl.get("video_signature") == signature
                and tl.get("segment_version") == SEGMENT_VERSION
                and _same_number(tl.get("threshold", threshold), threshold)
                and _same_number(tl.get("min_len", min_len), min_len)
                and _same_int(tl.get("frame_skip", frame_skip), frame_skip)):
            return ToolResult(
                text=f"Reused cached shots: {ctx.virtualize(output_path)} ({tl.get('n_shots', 0)} shots)",
                data=_summary(tl, output_path, reused=True, elapsed=0.0),
                artifacts=[str(output_path)],
            )

    try:
        from scenedetect import ContentDetector
    except ImportError:
        return ToolResult(
            text=("[ERROR] scenedetect is not installed. Install with --no-deps "
                  "(it pulls GUI opencv otherwise and breaks cv2): "
                  "pip install --no-deps \"scenedetect>=0.6\", or run /env-check"),
            data={"missing_dependency": "scenedetect"},
        )

    try:
        meta = probe(input_path)
    except Exception as exc:
        return ToolResult(text=f"[ERROR] ffprobe failed: {exc}", data={"input_path": str(input_path)})

    started = time.time()
    det = ContentDetector(threshold=threshold)
    try:
        if frame_skip > 0:
            # 隔帧检测: 解码量减少, 提速全片切分; 代价是切点精度下降(可能漏快切),
            # 默认关闭。SceneManager 默认 auto_downscale=True, 检测本身已在缩小帧上做。
            from scenedetect import SceneManager, open_video
            v = open_video(str(input_path))
            sm = SceneManager()
            sm.add_detector(det)
            sm.detect_scenes(v, frame_skip=frame_skip, show_progress=False)
            scenes = sm.get_scene_list()
        else:
            from scenedetect import detect
            scenes = detect(str(input_path), det, show_progress=False)
    except Exception as exc:
        return ToolResult(
            text=f"[ERROR] scene detection failed: {exc}",
            data={"input_path": str(input_path), "threshold": threshold, "frame_skip": frame_skip},
        )

    # SceneDetect 的 scene_list 覆盖整片。短镜头不能直接 continue，否则时间轴会
    # 出现洞（旧样片累计漏掉约70秒）；把它并入相邻镜头，同时保持全片连续覆盖。
    merged: list[list[float]] = []
    pending_first: list[float] | None = None
    for s, e in scenes:
        st, en = round(s.get_seconds(), 3), round(e.get_seconds(), 3)
        if en - st < min_len:
            if merged:
                merged[-1][1] = en
            elif pending_first is None:
                pending_first = [st, en]
            else:
                pending_first[1] = en
            continue
        if pending_first is not None:
            st = pending_first[0]
            pending_first = None
        merged.append([st, en])
    if pending_first is not None:
        merged.append(pending_first)

    shots = [{"shot_id": f"shot_{i:04d}", "start": st, "end": en,
              "dur": round(en - st, 3)} for i, (st, en) in enumerate(merged)]

    tl = {"video": str(input_path), "duration": meta["duration"],
          "video_signature": signature,
          "segment_version": SEGMENT_VERSION, "threshold": threshold,
          "min_len": min_len, "frame_skip": frame_skip,
          "fps": meta["fps"], "n_shots": len(shots), "shots": shots}
    try:
        save_json(tl, output_path)
    except OSError as exc:
        return ToolResult(text=f"[ERROR] failed to write {output_path}: {exc}")

    elapsed = round(time.time() - started, 3)
    return ToolResult(
        text=f"Detected {len(shots)} shots in {meta['duration']:.1f}s video -> {ctx.virtualize(output_path)} ({elapsed}s)",
        data=_summary(tl, output_path, reused=False, elapsed=elapsed),
        artifacts=[str(output_path)],
    )


def _summary(tl: dict, output_path: Path, *, reused: bool, elapsed: float) -> dict:
    # data 只放摘要不放整张 shots 表: 全片级时间轴动辄上千镜头, 塞进 MCP
    # 响应会撑爆上下文; 下游按契约读 output_json 文件。
    shots = tl.get("shots") or []
    return {
        "output_json": str(output_path),
        "reused": reused,
        "video": tl.get("video"),
        "duration": tl.get("duration"),
        "fps": tl.get("fps"),
        "segment_version": tl.get("segment_version"),
        "threshold": tl.get("threshold"),
        "min_len": tl.get("min_len"),
        "frame_skip": tl.get("frame_skip"),
        "n_shots": tl.get("n_shots"),
        "coverage_start": shots[0]["start"] if shots else None,
        "coverage_end": shots[-1]["end"] if shots else None,
        "elapsed_seconds": elapsed,
    }


def _same_number(cached, requested: float) -> bool:
    # 缓存里的参数可能是 int/float/字符串混着来 (手编 JSON), 转不成数字按不匹配处理
    try:
        return float(cached) == float(requested)
    except (TypeError, ValueError):
        return False


def _same_int(cached, requested: int) -> bool:
    try:
        return int(cached) == int(requested)
    except (TypeError, ValueError):
        return False


def _number_arg(args: dict, name: str, default: float) -> float | ToolResult:
    value = args.get(name, default)
    # bool 是 int 子类, true 会被 float() 悄悄转成 1.0 — 显式拒绝
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ToolResult(text=f"[ERROR] {name} must be a number", data={name: value})
    return float(value)


def _int_arg(args: dict, name: str, default: int) -> int | ToolResult:
    value = args.get(name, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return ToolResult(text=f"[ERROR] {name} must be an integer", data={name: value})
    return value


# ---------------------------------------------------------------------------
# 以下辅助函数抄自 movie_cut pipeline/common.py 与 event_common.py
# (kit 不依赖 movie_cut 包, 语义保持一致)
# ---------------------------------------------------------------------------

def probe(path: str | Path) -> dict:
    """返回视频的 duration/width/height/fps 等元信息。"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_name",
        "-of", "json", str(path),
    ]
    # ffprobe 不认 -nostdin (那是 ffmpeg 的选项), 用 DEVNULL 达到同样效果:
    # MCP 走 stdio, 子进程绝不能碰继承的 stdin
    proc = run_proc(cmd, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=PROBE_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"ffprobe failed for {path}")
    info = json.loads(proc.stdout)
    stream = info.get("streams", [{}])[0]
    num, den = (stream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) else 30.0
    return {
        "duration": float(info.get("format", {}).get("duration", 0.0)),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": round(fps, 3),
        "codec": stream.get("codec_name"),
    }


def file_signature(path: str | Path | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {"path": str(p), "missing": True}
    st = p.stat()
    return {"path": str(p.resolve()), "size": st.st_size,
            "mtime_ns": st.st_mtime_ns}


def load_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
