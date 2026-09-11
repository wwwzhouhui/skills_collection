#!/usr/bin/env python3
"""tts.py — 旁白稿 → 分段配音 + 实测时长表（双引擎：edge-tts / 自定义克隆音色）

用法（在视频工程根目录执行）:

    # 引擎 A：edge-tts（默认，微软神经音色，快）
    python <skill>/scripts/tts.py --script VOICEOVER_ZH.md --out . --voice yunyang

    # 引擎 B：自定义克隆服务（OmniVoice，音色更真实的人声）
    #   首次：上传参考音频（5–15s，干净人声）建立克隆音色，voice_id 自动存 build/clone-voice-id.txt
    python <skill>/scripts/tts.py --engine clone --script VOICEOVER_ZH.md --out . --ref-audio ref.wav --ref-text "参考音频的逐字文稿"
    #   之后：直接复用 voice_id（换音色才需要再传 --ref-audio）
    python <skill>/scripts/tts.py --engine clone --script VOICEOVER_ZH.md --out .
    #   提速：--num-steps 16（默认 32 质量）；换种子：--seed N（默认 42，固定种子保证确定性）
    #   并发：--clone-concurrency N（默认 1 串行；当前服务端为单 worker 排队，调大无益，
    #         服务端扩容后才建议 2–4）

段落规则: 段落间空行分隔（一行 --- 也算分隔）; 一段 = 一个场景 = 一个 mp3。
         Markdown 结构行（# 标题、> 引用、``` 代码块围栏）自动剥离，只有正文进入配音。
产物:
    public/vo/scene{N}.mp3      分段配音（N 从 1 起，与段落顺序一致；clone 引擎产出先为 WAV 再转 MP3）
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import hashlib
import threading
from pathlib import Path

# 线程安全的日志（并发合成时段落完成顺序不定，打印不能串行错乱）
_PRINT_LOCK = threading.Lock()


def log(msg: str) -> None:
    with _PRINT_LOCK:
        print(msg)

VOICE_ALIASES = {
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",  # 女·通用
    "xiaoyi": "zh-CN-XiaoyiNeural",      # 女·活泼
    "yunxi": "zh-CN-YunxiNeural",        # 男·阳光
    "yunjian": "zh-CN-YunjianNeural",    # 男·沉稳
    "yunyang": "zh-CN-YunyangNeural",    # 男·播报（技术讲解默认）
}

# 克隆服务默认地址（OmniVoice）；可用 --base-url 覆盖
CLONE_BASE_URL = "https://omnivoice.duckcloud.fun"
CLONE_DEFAULT_SEED = 42  # 固定种子：同稿重跑得到同样音频（确定性铁律）


def parse_segments(text: str) -> list[str]:
    """空行分段；Markdown 结构行（# 标题 / > 引用 / ``` 代码块）替换为空行，只合成正文。
    结构行替换为空行而非直接删除，因此 "正文A / ## 标题 / 正文B"（标题前后无空行）
    也能被正确切成两段。
    """
    text = text.lstrip(chr(65279))  # 剥离 UTF-8 BOM（PowerShell Set-Content 常写入）
    lines: list[str] = []
    in_code = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            lines.append("")
            continue
        if in_code or (s and (s.startswith("#") or s.startswith(">"))):
            lines.append("")  # 结构行 → 视为段落分隔
            continue
        lines.append(line)
    parts = re.split(r"\n\s*---+\s*\n|\n\s*\n", "\n".join(lines).strip())
    segs = []
    for p in parts:
        p = " ".join(p.split())  # 压空白但保留中英文间距
        if p:
            segs.append(p)
    return segs


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


# ---------------- 引擎 A：edge-tts ----------------

async def synth_segment_edge(text: str, voice: str, rate: str, dest: Path) -> None:
    import edge_tts
    last_err = None
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate)
            await asyncio.wait_for(comm.save(str(dest)), timeout=90)  # 防网络挂起
            if dest.stat().st_size > 0:
                return
            raise RuntimeError("empty output")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < 2:
                await asyncio.sleep(2.0 * (attempt + 1))
    raise RuntimeError(
        f"edge-tts 连续失败: {last_err}\n"
        "  排查: 1) 网络能否访问 Microsoft TTS 服务; 2) 升级客户端 "
        "pip install -U edge-tts（微软服务端变更常导致旧版失效）; 3) 稍后重试避开限流"
    )


# ---------------- 引擎 B：自定义克隆服务（OmniVoice） ----------------

def _clone_error_message(response) -> str:
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text.strip()
    if isinstance(detail, list):
        detail = "; ".join(str(item) for item in detail)
    return f"HTTP {response.status_code}: {detail or response.reason}"


def clone_upload_voice(session, base_url: str, ref_audio: Path, ref_text: str, timeout: float) -> str:
    """上传参考音频建立克隆音色，返回 voice_id。"""
    with ref_audio.open("rb") as audio_handle:
        response = session.post(
            f"{base_url.rstrip('/')}/v1/voices",
            files={"file": (ref_audio.name, audio_handle)},
            data={"reference_text": ref_text},
            timeout=timeout,
        )
    if not response.ok:
        raise RuntimeError(f"参考音频上传失败: {_clone_error_message(response)}")
    voice_id = response.json().get("id")
    if not voice_id:
        raise RuntimeError(f"服务未返回 voice_id: {response.text}")
    return voice_id


def clone_resolve_voice(args, session) -> str:
    """解析克隆音色：--ref-audio 上传 > voice-id 文件复用 > --voice / 默认 default。"""
    if args.ref_audio is not None:
        if not args.ref_audio.is_file():
            sys.exit(f"✗ 找不到参考音频: {args.ref_audio}")
        if not (args.ref_text or "").strip():
            sys.exit("✗ --ref-audio 必须配 --ref-text（参考音频的逐字文稿）")
        voice_id = clone_upload_voice(
            session, args.base_url, args.ref_audio, args.ref_text.strip(), args.timeout)
        args.voice_id_file.parent.mkdir(parents=True, exist_ok=True)
        args.voice_id_file.write_text(voice_id + "\n", encoding="utf-8")
        print(f"  克隆音色已建立并保存: voice_id={voice_id} → {args.voice_id_file}")
        return voice_id
    if args.voice_id_file.exists():
        voice_id = args.voice_id_file.read_text(encoding="utf-8").strip()
        if voice_id:
            print(f"  复用克隆音色 voice_id={voice_id}（{args.voice_id_file}；换音色请重传 --ref-audio）")
            return voice_id
    return args.voice if args.voice not in VOICE_ALIASES else "default"


def synth_segment_clone(text: str, voice_id: str, num_steps: int, seed: int,
                        dest: Path, base_url: str, timeout: float,
                        tag: str = "") -> None:
    """调克隆服务生成 WAV，再转 MP3（流水线统一 MP3，§5/§8 完全不变）。

    线程安全：可在 ThreadPoolExecutor 中并发调用（每段独立文件，互不干扰）。
    """
    import requests
    prefix = f"  [{tag}] " if tag else "    "
    payload = {"model": "omnivoice", "input": text, "voice": voice_id, "num_steps": num_steps}
    if seed is not None:
        payload["seed"] = seed
    last_err = None
    for attempt in range(3):
        try:
            response = requests.post(
                f"{base_url.rstrip('/')}/v1/audio/speech", json=payload, timeout=timeout)
            if response.ok and response.content:
                tmp_wav = dest.with_suffix(".wav")
                tmp_wav.write_bytes(response.content)
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-v", "error", "-i", str(tmp_wav),
                         "-codec:a", "libmp3lame", "-qscale:a", "2", str(dest)],
                        check=True)
                finally:
                    tmp_wav.unlink(missing_ok=True)
                if dest.stat().st_size > 0:
                    gen_s = response.headers.get("X-Generation-Seconds", "?")
                    log(f"{prefix}（服务生成 {gen_s}s）")
                    return
            raise RuntimeError(_clone_error_message(response))
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < 2:
                import time
                time.sleep(3.0 * (attempt + 1))
    raise RuntimeError(
        f"克隆服务连续失败: {last_err}\n"
        f"  排查: 1) 服务地址可达（{base_url}）; 2) voice_id 是否有效（重传 --ref-audio 重建）; "
        "3) 网络/超时（--timeout 可调大）; 4) 依赖 requests（pip install requests）"
    )


# ---------------- 主流程 ----------------

async def main() -> None:
    ap = argparse.ArgumentParser(description="旁白稿 → 分段配音 + durations.json（edge-tts / 克隆双引擎）")
    ap.add_argument("--script", required=True, help="旁白稿路径（段落间空行分隔）")
    ap.add_argument("--out", default=".", help="视频工程根目录（默认当前目录）")
    ap.add_argument("--engine", choices=["edge", "clone"], default="edge",
                    help="edge = edge-tts 神经音色（默认，快）; clone = 自定义克隆服务（更真实的人声）")
    ap.add_argument("--voice", default="yunyang",
                    help="edge 引擎: xiaoxiao|xiaoyi|yunxi|yunjian|yunyang 或完整音色名; "
                         "clone 引擎: 已有 voice_id 或 default")
    ap.add_argument("--rate", default="+0%", help="edge 引擎语速，如 +10%% / -5%%（clone 引擎不支持，忽略）")
    ap.add_argument("--fps", type=int, default=30, help="帧率（用于换算帧数，默认 30）")
    ap.add_argument("--force", action="store_true", help="忽略缓存，重新合成全部段落")
    ap.add_argument("--cache", action="store_true", default=True, help="复用文本/音色未变化的已有 MP3（默认开启）")
    # ---- clone 引擎专用 ----
    ap.add_argument("--base-url", default=CLONE_BASE_URL, help=f"克隆服务地址（默认 {CLONE_BASE_URL}）")
    ap.add_argument("--ref-audio", type=Path, help="参考音频（5–15s 干净人声），首次建立克隆音色用")
    ap.add_argument("--ref-text", help="参考音频的逐字文稿（与 --ref-audio 配套必填）")
    ap.add_argument("--num-steps", type=int, default=32, help="生成步数: 32 质量（默认）/ 16 提速")
    ap.add_argument("--seed", type=int, default=CLONE_DEFAULT_SEED,
                    help=f"随机种子（默认 {CLONE_DEFAULT_SEED}，固定种子保证同稿重跑结果一致）")
    ap.add_argument("--voice-id-file", type=Path, default=None,
                    help="voice_id 保存/复用文件（默认 <out>/build/clone-voice-id.txt）")
    ap.add_argument("--timeout", type=float, default=300, help="克隆服务 HTTP 超时秒数（默认 300）")
    ap.add_argument("--clone-concurrency", type=int, default=1,
                    help="clone 引擎并发请求数（默认 1；实测当前服务为单 worker 排队，"
                         "并发不提速反略慢。仅当服务端扩容支持并发时调大，上限 8）")
    args = ap.parse_args()

    if args.engine == "edge" and not re.fullmatch(r"[+-]\d+%", args.rate):
        sys.exit("✗ --rate 格式应为 +10% / -5%（必须带正负号）")
    if args.engine == "clone":
        if args.rate != "+0%":
            print("  ⚠ 克隆引擎暂不支持语速参数，--rate 已忽略（改稿调整句长即可）")
        try:
            import requests  # noqa: F401
        except ImportError:
            sys.exit("✗ 克隆引擎需要 requests：python -m pip install requests")

    script_path = Path(args.script)
    if not script_path.exists():
        sys.exit(f"✗ 找不到旁白稿: {script_path}")

    segments = parse_segments(script_path.read_text(encoding="utf-8"))
    if not segments:
        sys.exit("✗ 旁白稿为空")
    for i, s in enumerate(segments, 1):
        if len(s) > 160:
            print(f"  ⚠ 第 {i} 段偏长（{len(s)} 字），单场景建议 ≤120 字，否则画面停留过久")

    root = Path(args.out)
    vo_dir = root / "public" / "vo"
    build_dir = root / "build"
    vo_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    # 音色解析（clone：可能先上传参考音频换取 voice_id）
    clone_session = None
    voice = args.voice
    if args.engine == "edge":
        voice = VOICE_ALIASES.get(args.voice, args.voice)
        if args.voice_id_file is None:
            args.voice_id_file = build_dir / "clone-voice-id.txt"
    else:
        import requests
        if args.voice_id_file is None:
            args.voice_id_file = build_dir / "clone-voice-id.txt"
        clone_session = requests.Session()
        voice = clone_resolve_voice(args, clone_session)

    # 缓存键：引擎 + 音色 + 引擎参数 + 文本
    if args.engine == "edge":
        engine_key = f"edge|{voice}|{args.rate}"
    else:
        engine_key = f"clone|{voice}|steps{args.num_steps}|seed{args.seed}"

    if args.engine == "clone":
        if not (1 <= args.clone_concurrency <= 8):
            sys.exit("✗ --clone-concurrency 应在 1–8 之间（服务并发能力有限，不建议更大）")
        print(f"  克隆引擎就绪: {args.base_url} · num_steps={args.num_steps} · seed={args.seed}"
              f" · {len(segments)} 段 · 并发 {args.clone_concurrency} 路"
              f"（每段数秒～数十秒，多段并发总耗时 ≈ 最慢几段之和）")

    # ---- 阶段 1：缓存检查（串行、瞬时），缺的段落进待合成队列 ----
    pending: list[tuple[int, str, Path, str]] = []  # (i, text, dest, cache_key)
    for i, text in enumerate(segments, 1):
        dest = vo_dir / f"scene{i}.mp3"
        cache_key = hashlib.sha256(f"{engine_key}|{text}".encode("utf-8")).hexdigest()
        stamp = dest.with_suffix(".sha256")
        if args.cache and not args.force and dest.exists() and stamp.exists() and stamp.read_text(encoding="ascii").strip() == cache_key:
            log(f"  复用 scene{i} … {text[:26]}")
        else:
            pending.append((i, text, dest, cache_key))

    # ---- 阶段 2：合成（edge 串行；clone 多段并发，线程安全） ----
    if args.engine == "edge":
        for i, text, dest, cache_key in pending:
            log(f"  合成 scene{i} … {text[:26]}")
            await synth_segment_edge(text, voice, args.rate, dest)
            dest.with_suffix(".sha256").write_text(cache_key, encoding="ascii")
    elif pending:
        from concurrent.futures import ThreadPoolExecutor

        def _clone_job(item: tuple[int, str, Path, str]) -> None:
            i, text, dest, cache_key = item
            log(f"  ▶ scene{i} 请求中 … {text[:26]}")
            synth_segment_clone(text, voice, args.num_steps, args.seed,
                                dest, args.base_url, args.timeout, tag=f"scene{i}")
            dest.with_suffix(".sha256").write_text(cache_key, encoding="ascii")
            log(f"  ✔ scene{i} 完成")

        workers = max(1, min(args.clone_concurrency, len(pending)))
        if workers == 1:
            for item in pending:
                _clone_job(item)
        else:
            log(f"  并发合成 {len(pending)} 段（{workers} 路并发）…")
            with ThreadPoolExecutor(max_workers=workers) as pool:
                # map 的惰性迭代会在取结果时抛出首个异常（含重试耗尽），整趟失败并保留清晰报错
                list(pool.map(_clone_job, pending))

    # ---- 阶段 3：统一测长（串行、有序输出，产物顺序与段落一致） ----
    scenes = []
    for i, text in enumerate(segments, 1):
        dest = vo_dir / f"scene{i}.mp3"
        dur = ffprobe_duration(dest)
        frames = int(round(dur * args.fps))
        scenes.append({
            "i": i, "text": text, "file": f"vo/scene{i}.mp3",
            "durationSec": round(dur, 3), "frames": frames,
        })
        log(f"  ✓ scene{i}: {dur:.2f}s = {frames}f")

    data = {"engine": args.engine, "voice": voice, "fps": args.fps, "scenes": scenes}
    if args.engine == "edge":
        data["rate"] = args.rate
    else:
        data["numSteps"] = args.num_steps
        data["seed"] = args.seed
    (build_dir / "durations.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(s["frames"] for s in scenes)
    print(f"\n✓ {len(scenes)} 段配音 → public/vo/ ；时长表 → build/durations.json（引擎: {args.engine}）")
    print(f"  旁白总长 ≈ {total / args.fps:.1f}s（不含场景尾巴与纯视觉镜头）")
    print(f"  下一步: 写 build/scenes.json 后运行 build-timeline.mjs")


if __name__ == "__main__":
    asyncio.run(main())
