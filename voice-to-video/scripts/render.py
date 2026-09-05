#!/usr/bin/env python3
"""确定性渲染: HTML 合成 -> 逐帧截图 -> ffmpeg 合成 MP4(含配音)。

用法:
  python render.py --html composition.html --audio build/voice.mp3 --out final.mp4
      [--fps 30] [--width 1920] [--height 1080] [--quality 85] [--crf 18]
      [--fast] [--frames-dir frames] [--keep-frames] [--from-frame N]

原理: Playwright 无头 Chromium 加载合成页, 对每一帧调用 window.HF.seek(t)
把整个 DOM 设到该时刻的状态(纯函数、与墙钟无关), 截图后按序交给 ffmpeg 编码,
最后混入配音音轨。同样的 HTML + timeline 永远渲出同样的每一帧。

安全说明: 所有 subprocess 调用均为参数列表形式且 shell=False,
路径作为独立参数传递, 不经过 shell, 不存在命令注入面。
"""

import argparse
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path


def ffprobe_ms(path: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True, shell=False)
    return int(float(r.stdout.strip()) * 1000)


def encode_video(frames_pattern: str, audio: Path, out: Path, fps: int,
                 preset: str, crf: int) -> None:
    """把帧序列与配音合成为 MP4。参数列表 + shell=False, 无 shell 解释。"""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-stats",
        "-framerate", str(fps), "-start_number", "0",
        "-i", frames_pattern,
        "-i", str(audio),
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ], check=True, shell=False)


def main():
    ap = argparse.ArgumentParser(description="HTML 合成确定性渲染为 MP4")
    ap.add_argument("--html", required=True, help="合成页 composition.html")
    ap.add_argument("--audio", required=True, help="配音音频(voice.mp3)")
    ap.add_argument("--out", default="final.mp4", help="输出 mp4 路径")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--quality", type=int, default=85, help="JPEG 质量 1-100")
    ap.add_argument("--crf", type=int, default=18, help="x264 CRF, 越小越清晰")
    ap.add_argument("--fast", action="store_true", help="草稿模式: crf 23 + veryfast")
    ap.add_argument("--style-kit", default=None,
                    help="渲染时注入的 kit CSS 路径(覆盖合成页 <link> 的样式, 免复制切换风格)")
    ap.add_argument("--watermark", default=None,
                    help="右下角作者水印文字(如 laohaibao2025), 渲染时注入, 无需改合成页")
    ap.add_argument("--wait-videos", action="store_true",
                    help="每帧等待合成页内嵌 <video> seek 完成(画面含视频素材时必开, 略慢)")
    ap.add_argument("--frames-dir", default=None)
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--from-frame", type=int, default=0, help="跳过此帧之前(断点续渲)")
    args = ap.parse_args()

    html = Path(args.html).resolve()
    audio = Path(args.audio).resolve()
    out = Path(args.out).resolve()
    if not html.is_file():
        sys.exit(f"--html 不存在: {html}")
    if not audio.is_file():
        sys.exit(f"--audio 不存在: {audio}")
    out.parent.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(args.frames_dir).resolve() if args.frames_dir \
        else out.parent / f"frames_{out.stem}"

    audio_ms = ffprobe_ms(audio)
    total = math.ceil(audio_ms * args.fps / 1000)
    print(f"[render] {args.width}x{args.height}@{args.fps}fps  audio={audio_ms/1000:.2f}s  frames={total}")
    frames_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            sys.exit(f"Chromium 启动失败: {e}\n请先执行: python -m playwright install chromium")
        page = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=1,
        ).new_page()

        page.goto(html.as_uri(), wait_until="load")
        page.evaluate("() => document.fonts.ready")
        page.wait_for_function("() => window.HF && window.HF.ready === true")
        page.evaluate(f"() => HF.setDuration({int(audio_ms)})")
        if args.style_kit:
            kit_path = Path(args.style_kit)
            if not kit_path.is_file():
                sys.exit(f"--style-kit 不存在: {kit_path}")
            page.add_style_tag(path=str(kit_path))  # 注入风格 kit, 级联覆盖合成页 <link>
            page.wait_for_timeout(200)
        # 渲染模式: 隐藏预览播放提示(字幕条/进度条属于成片设计, 保留)
        page.evaluate(
            "() => { const h = document.getElementById('hf-playhint');"
            " if (h) h.style.display = 'none'; }")
        if args.watermark:
            # 直接 DOM 注入而非 HF.setWatermark: 对加载旧版 engine.js 的存量合成页同样生效
            page.evaluate(
                "(t) => { let el = document.getElementById('hf-watermark');"
                " if (!el) { el = document.createElement('div'); el.id = 'hf-watermark';"
                " el.style.cssText = 'position:absolute;z-index:50;right:26px;bottom:14px;' +"
                " 'font:600 17px/1 var(--mono, ui-monospace, Consolas, monospace);' +"
                " 'letter-spacing:1.5px;color:rgba(128,132,150,.62);' +"
                " 'text-shadow:0 1px 2px rgba(0,0,0,.10);pointer-events:none;user-select:none;';"
                " (document.getElementById('stage') || document.body).appendChild(el); }"
                " el.textContent = t; }",
                args.watermark)

        # 预热: 字体/着色器首次渲染较慢, 先空跑一帧
        page.evaluate("() => HF.seek(0)")
        page.screenshot(type="jpeg", quality=args.quality)

        for i in range(total):
            fpath = frames_dir / f"f_{i:06d}.jpg"
            if fpath.exists():  # 断点续渲: 已存在的帧跳过
                continue
            t_ms = i * 1000.0 / args.fps
            page.evaluate("t => HF.seek(t)", t_ms)
            if args.wait_videos:
                page.evaluate("() => (window.HF && HF.waitVideos) ? HF.waitVideos() : null")
            page.screenshot(path=str(fpath), type="jpeg", quality=args.quality)
            if i % 60 == 0:
                done, el = i + 1, time.time() - t0
                eta = el / done * (total - done)
                print(f"[render] frame {i+1}/{total}  {el:.0f}s elapsed  ~{eta:.0f}s left", flush=True)

        browser.close()

    print(f"[render] frames done in {time.time()-t0:.0f}s, encoding with ffmpeg ...")
    preset = "veryfast" if args.fast else "medium"
    crf = 23 if args.fast else args.crf
    encode_video(str(frames_dir / "f_%06d.jpg"), audio, out, args.fps, preset, crf)

    if not args.keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)
    dur = ffprobe_ms(out)
    print(f"[render] OK -> {out}  ({out.stat().st_size/1e6:.1f}MB, {dur/1000:.2f}s)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
