"""解说批量 TTS: 排片写稿 script.json → 逐段合成音频 + 句级时长切分。

移植自 movie_cut pipeline/step_bc_tts.py 的 synth_all():
  - 段级输出契约不变: audio_path/audio_dur/speech_dur/delivery_pause_sec/
    sentences/tts_mode/_tts_fp/_tts_complete — 下游 bind 的语义切片靠 sentences。
  - semantic_out 契约不变: {schema_version, n_units, units[]}。
  - 段级缓存指纹绑定 文本+句映射+停顿+provider+voice+rate, 改稿/换音色不复用旧音频。
  - 只走 kit 自己的标准 speech_synthesize/tts_generate 入口。
"""
from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
from .ffproc import run_proc
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .result import ToolResult
from .run_context import RunContext, clean_env

TTS_SCHEMA_VERSION = "3.1-sentence-trim"

DEFAULT_PROVIDER = "edge_tts"
DEFAULT_NARRATION_VOICE = "zh-CN-YunxiNeural"
DEFAULT_RATE = "+0%"

# 云端 TTS 调用走保守低并发，避免并发/限流错误。
CLOUD_TTS_WORKERS = 2

_RATE_RE = re.compile(r"^[+-]\d+%$")


# ---------------------------------------------------------------------------
# 基础工具 (从 movie_cut common.py 抄入, 禁止 import movie_cut)
# ---------------------------------------------------------------------------

def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    """跑一条命令, 失败把 stderr 抛出来 (ffmpeg 出错信息都在 stderr)。"""
    proc = run_proc(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed (exit {proc.returncode}): {shlex.join(cmd)}\n{proc.stderr[-2000:]}"
        )
    return proc


def _media_duration(path: str | Path) -> float:
    """取音频流时长; 流里没存 duration 时回退 format。"""
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a:0",
           "-show_entries", "stream=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    proc = run_proc(cmd, capture_output=True, text=True, timeout=60)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        cmd2 = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
        return float(_run(cmd2).stdout.strip() or 0.0)


def _valid_audio(path: str | Path, minimum: float = 0.1) -> bool:
    try:
        return bool(path) and Path(path).exists() and _media_duration(path) > minimum
    except Exception:
        return False


def _load_json(path: str | Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(obj, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 文本/时间轴辅助 (契约与 movie_cut step_bc_tts 一致)
# ---------------------------------------------------------------------------

def _spoken_text(seg: dict) -> str:
    """TTS 只读口播字段; 兼容未经过 spoken_text 层的旧脚本。"""
    direct = str(seg.get("spoken_text", "")).strip()
    if direct:
        return direct
    units = seg.get("semantic_units", [])
    joined = "".join(
        str(x.get("spoken_text", x.get("text", ""))).strip()
        for x in units if isinstance(x, dict))
    return joined or str(seg.get("text", "")).strip()


def _pause_ms(seg: dict) -> int:
    """没有显式停顿字段时保持 0; 有则夹到 [0, 650]。"""
    if "delivery_pause_ms" not in seg:
        return 0
    try:
        value = int(seg.get("delivery_pause_ms", 0))
    except (TypeError, ValueError):
        value = 0
    return max(0, min(650, value))


def _split_sentences(text: str) -> list[str]:
    """按标点拆句; 过滤纯标点句 (TTS 对纯标点报错)。"""
    parts = re.split(r"(?<=[。！？；])", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) > 20:
            out.extend([x.strip() for x in re.split(r"(?<=[，、])", p) if x.strip()])
        else:
            out.append(p)
    return [s for s in out if re.sub(r"[\W_]+", "", s, flags=re.UNICODE)]


def _timing_units(seg: dict) -> list[dict]:
    """取字幕/口播双文本及原有 claim 映射, 供整段音频估算句级落点。"""
    rows = []
    for idx, unit in enumerate(seg.get("semantic_units", []), 1):
        if not isinstance(unit, dict):
            continue
        subtitle = str(unit.get("subtitle_text", unit.get("text", ""))).strip()
        spoken = str(unit.get("spoken_text", unit.get("text", ""))).strip()
        if not spoken:
            continue
        rows.append({
            "semantic_unit_id": unit.get(
                "semantic_unit_id", f"{seg.get('seg_id', 'seg')}_u{idx:02d}"),
            "text": subtitle or spoken,
            "subtitle_text": subtitle or spoken,
            "spoken_text": spoken,
            "event_ids": list(unit.get("event_ids", seg.get("event_ids", []))),
            "claim_ids": list(unit.get("claim_ids", [])),
            "anchor_shot_ids": list(unit.get("anchor_shot_ids", [])),
        })
    if rows:
        return rows

    subtitle_parts = _split_sentences(str(seg.get("subtitle_text", seg.get("text", ""))))
    spoken_parts = _split_sentences(_spoken_text(seg))
    if len(subtitle_parts) != len(spoken_parts):
        subtitle_parts = [str(seg.get("subtitle_text", seg.get("text", ""))).strip()]
        spoken_parts = [_spoken_text(seg)]
    return [{
        "semantic_unit_id": f"{seg.get('seg_id', 'seg')}_u{i + 1:02d}",
        "text": subtitle or spoken,
        "subtitle_text": subtitle or spoken,
        "spoken_text": spoken,
        "event_ids": list(seg.get("event_ids", [])),
        "claim_ids": list(seg.get("evidence_claim_ids", [])),
        "anchor_shot_ids": [],
    } for i, (subtitle, spoken) in enumerate(zip(subtitle_parts, spoken_parts)) if spoken]


def _speech_weight(text: str) -> float:
    """把整段真实时长按发音量和标点停连分配给语义句。"""
    content = len(re.findall(r"[\w㐀-鿿]", str(text), flags=re.UNICODE))
    commas = len(re.findall(r"[，、,:：]", str(text)))
    stops = len(re.findall(r"[。！？!?；;]", str(text)))
    return max(1.0, content + commas * 0.55 + stops * 0.9)


def _estimate_timeline(seg: dict, speech_dur: float) -> list[dict]:
    """整段合成没有强制对齐信息, 按口播字符与停连估算句界; 尾部呼吸不算字幕。"""
    units = _timing_units(seg)
    if not units or speech_dur <= 0:
        return []
    weights = [_speech_weight(x["spoken_text"]) for x in units]
    total = sum(weights) or 1.0
    timeline, cursor = [], 0.0
    for idx, (unit, weight) in enumerate(zip(units, weights), 1):
        end = speech_dur if idx == len(units) else cursor + speech_dur * weight / total
        timeline.append({**unit, "start": round(cursor, 3), "end": round(end, 3)})
        cursor = end
    return timeline


_QUOTE_CHARS = "“”‘’\"'「」『』"


def _flatten_spoken(text: str) -> str:
    """口播去戏剧化: LLM-TTS 会把 "某某说:" 当剧本说话人标签吞掉, 把引语拿去角色演绎
    (实测: 吞句 / 变声 / 自编对白)。冒号压成逗号、引号删除后此类失误显著减少。
    只动标点不动字, 字幕仍走 subtitle_text/text 原文, 不会音字不符。"""
    t = re.sub(r"[::]", ",", str(text))
    t = re.sub(f"[{_QUOTE_CHARS}]", "", t)
    return re.sub(r"[,,]{2,}", ",", t)


def _norm_cjk(text: str) -> str:
    return re.sub(r"[^一-鿿A-Za-z0-9]", "", str(text))


def _gram_hit_ratio(target: str, heard: str, n: int = 4) -> float:
    """target 的 n 字滑窗在 heard 中的命中率; 短句退化为整串包含。
    实测分界: TTS 改写/吞句 <0.35, ASR 同音误听仍 >0.6。"""
    t, h = _norm_cjk(target), _norm_cjk(heard)
    if not t:
        return 1.0
    if len(t) <= n:
        return 1.0 if t in h else 0.0
    hits = sum(1 for i in range(len(t) - n + 1) if t[i:i + n] in h)
    return hits / (len(t) - n + 1)


_VERIFY_RATE = 4.4  # 语速合理性估算用 (字/秒, 云端音色经验值); 只定区间不做硬契约


def _duration_suspect(chars: int, dur: float) -> str | None:
    """句音频时长与字数的合理区间; ASR 自己会漏听, 时长是独立的第二证据。"""
    if chars <= 0 or dur <= 0:
        return None
    expect = chars / _VERIFY_RATE
    if dur < expect * 0.55:
        return (f"audio {dur:.1f}s too short for {chars} chars "
                f"(expect ~{expect:.1f}s): content likely dropped")
    if dur > expect * 1.8 + 1.2:
        return (f"audio {dur:.1f}s too long for {chars} chars "
                f"(expect ~{expect:.1f}s): dramatized pauses or extra content")
    return None


def _sent_fp(provider: str, voice: str, rate: str, sent: str) -> str:
    """句级文件缓存指纹: 只认 provider+voice+rate+句文本。
    注意: 重试同一句必须先删文件, 否则永远复用第一次的坏音频。"""
    return hashlib.sha256(
        f"{provider}\x00{voice}\x00{rate}\x00{sent}".encode("utf-8")
    ).hexdigest()[:10]


def _tts_fingerprint(seg: dict, provider: str, by_sentence: bool,
                     voice: str, rate: str) -> str:
    """缓存指纹: 口播文本+句子映射+停顿+provider+voice+rate。
    改稿/换音色/换语速任一变化都不会复用旧音频 (voice/rate 显式入参, 不靠全局)。"""
    knobs = (TTS_SCHEMA_VERSION, provider, _spoken_text(seg),
             "sentence" if by_sentence else "paragraph", str(_pause_ms(seg)),
             voice, rate,
             json.dumps(seg.get("semantic_units", []), ensure_ascii=False,
                        sort_keys=True))
    return hashlib.sha256("\x00".join(knobs).encode("utf-8")).hexdigest()[:16]


def _pad_audio(raw_audio: str, out_audio: str, pause_ms: int) -> str:
    """段尾加入明确呼吸, 统一转 24kHz 单声道 wav, 避免 MP3 拼接尾差。"""
    if pause_ms <= 0:
        return raw_audio
    speech_dur = _media_duration(raw_audio)
    total = speech_dur + pause_ms / 1000.0
    _run(["ffmpeg", "-y", "-i", raw_audio,
          "-af", f"apad=pad_dur={pause_ms / 1000.0:.3f}",
          "-t", f"{total:.3f}", "-ar", "24000", "-ac", "1",
          "-c:a", "pcm_s16le", out_audio])
    return out_audio


_TRIM_EDGE_SEC = 0.25   # 句音频头尾保留的静音上限
_TRIM_DB = 45           # 静音判定阈值(-dB)


def _trim_part(part: str) -> str:
    """句音频边缘静音裁剪 (by_sentence 模式)。TTS 原生的头尾静音逐句累积会把段
    音频吹胀 ~10%, 短句尤甚 (实测 4 字句 1.9s, 排片 span 只有 1.5s 时 DP 无解)。
    头尾各保留 ≤0.25s; 裁剪参数编进文件名(调参即换缓存), 并带 mtime 校验
    (句重合成后自动重裁)。"""
    src = Path(part)
    out = src.with_name(
        f"{src.stem}_trim{int(_TRIM_EDGE_SEC * 1000)}n{_TRIM_DB}.wav")
    if out.exists() and out.stat().st_mtime >= src.stat().st_mtime and _valid_audio(out):
        return str(out)
    th = f"-{_TRIM_DB}dB"
    _run(["ffmpeg", "-nostdin", "-y", "-i", str(src), "-af",
          f"silenceremove=start_periods=1:start_threshold={th}:start_silence={_TRIM_EDGE_SEC},"
          f"areverse,"
          f"silenceremove=start_periods=1:start_threshold={th}:start_silence={_TRIM_EDGE_SEC},"
          f"areverse",
          str(out)])
    if not _valid_audio(out):  # 全静音等极端输入: 裁剪产物无效则只转码不裁 (保持 wav 统一)
        out.unlink(missing_ok=True)
        _run(["ffmpeg", "-nostdin", "-y", "-i", str(src), str(out)])
        if not _valid_audio(out):
            out.unlink(missing_ok=True)
            return str(src)
    return str(out)


def _concat_audio(parts: list[str], out: str) -> None:
    """拼接句音频成段音频 (by_sentence 模式)。"""
    if len(parts) == 1:
        # 统一转码 (拼接输入可能是裁剪后的 wav, 容器随 out 后缀走, -c copy 会容器错配)
        codec1 = ["-c:a", "pcm_s16le"] if Path(out).suffix.lower() == ".wav" else \
                 ["-c:a", "libmp3lame", "-b:a", "192k"]
        _run(["ffmpeg", "-y", "-i", parts[0], *codec1, out])
        return
    lst = out + ".txt"
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    codec = ["-c:a", "pcm_s16le"] if Path(out).suffix.lower() == ".wav" else \
            ["-c:a", "libmp3lame", "-b:a", "192k"]
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, *codec, out])


# ---------------------------------------------------------------------------
# 合成后端: 委托 kit 标准 TTS 工具
# ---------------------------------------------------------------------------

def _make_cloud_tts_fn(voice: str, speed: float | None, ctx: RunContext):
    """委托 kit 自己的 tts_generate 逐段合成。
    voice/speed 透传给标准 TTS 工具，保留段级缓存与验音逻辑。"""
    from .tts import tts_generate
    ext = ".mp3"

    def fn(text: str, out_base: str, retries: int = 2) -> str:
        out = out_base + ext
        d_args: dict = {
            "text": text,
            "preferred_provider": DEFAULT_PROVIDER,
            "allowed_providers": [DEFAULT_PROVIDER],
            "output_path": out,
            "speaker": voice,
        }
        if speed is not None:
            d_args["speed"] = speed
        last: Exception | None = None
        for i in range(retries):
            result = tts_generate(dict(d_args), ctx)
            if not result.text.startswith("[ERROR]") and _valid_audio(out, 0.05):
                return out
            last = RuntimeError(result.text)
            time.sleep(3 * (i + 1))
        raise last  # type: ignore[misc]

    return fn


def _parse_rate_speed(rate: str) -> float | None:
    """百分比语速 "+6%" → cloud_tts speed 1.06; "+0%" 视为不指定。"""
    m = _RATE_RE.match(rate.strip())
    if not m:
        return None
    pct = int(rate.strip().rstrip("%"))
    if pct == 0:
        return None
    return round(1.0 + pct / 100.0, 3)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def synthesize_narration(args: dict, ctx: RunContext) -> ToolResult:
    if not args.get("script_path"):
        return ToolResult(text="[ERROR] script_path is required")
    script_path = ctx.resolve(args["script_path"])
    if not script_path.is_file():
        return ToolResult(text=f"[ERROR] script not found: {script_path}")
    try:
        segs = _load_json(script_path)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(text=f"[ERROR] invalid script JSON: {exc}")
    if not isinstance(segs, list) or not segs:
        return ToolResult(text="[ERROR] script must be a non-empty JSON array of segments")
    for idx, seg in enumerate(segs):
        if not isinstance(seg, dict) or not str(seg.get("seg_id", "")).strip():
            return ToolResult(
                text=f"[ERROR] segment #{idx} is missing seg_id",
                data={"segment_index": idx},
            )

    # 只支持标准 TTS: 参数 > .env(VE_NARRATION_TTS_*) > 内置音色。
    # 用户级音色偏好放 .env, 每次调用可显式覆盖。
    provider = str(args.get("provider")
                   or clean_env("VE_NARRATION_TTS_PROVIDER")
                   or DEFAULT_PROVIDER).strip().lower()
    if provider in ("auto", "cloud", "cloud_tts", "edge", "edge_tts"):
        provider = DEFAULT_PROVIDER
    if provider != DEFAULT_PROVIDER:
        return ToolResult(
            text=f"[ERROR] unsupported provider: {provider}; "
                 f"expected {DEFAULT_PROVIDER}",
        )
    by_sentence = args.get("by_sentence", False)
    if not isinstance(by_sentence, bool):
        return ToolResult(text="[ERROR] by_sentence must be a boolean")
    flatten_quotes = args.get("flatten_quotes", False)
    if not isinstance(flatten_quotes, bool):
        return ToolResult(text="[ERROR] flatten_quotes must be a boolean")
    verify_mode = str(args.get("verify") or "").strip().lower()
    if verify_mode not in ("", "asr"):
        return ToolResult(text='[ERROR] verify must be "asr" or omitted')
    try:
        verify_retries = int(args.get("verify_retries", 2))
    except (TypeError, ValueError):
        return ToolResult(text="[ERROR] verify_retries must be an integer")
    verify_retries = max(0, min(3, verify_retries))
    if flatten_quotes:
        # 口播去戏剧化写回 spoken_text (指纹随之变化, 不会误用未压平的旧音频);
        # subtitle_text/text 原文不动
        for s in segs:
            s["spoken_text"] = _flatten_spoken(_spoken_text(s))
            for u in s.get("semantic_units", []):
                if isinstance(u, dict):
                    u["spoken_text"] = _flatten_spoken(
                        str(u.get("spoken_text", u.get("text", ""))))
    require_complete = args.get("require_complete", True)
    if not isinstance(require_complete, bool):
        return ToolResult(text="[ERROR] require_complete must be a boolean")

    explicit_voice = args.get("voice")
    if explicit_voice is not None and not str(explicit_voice).strip():
        explicit_voice = None
    if explicit_voice is None:
        explicit_voice = clean_env("VE_NARRATION_TTS_VOICE")
    rate = str(args.get("rate") or clean_env("VE_NARRATION_TTS_RATE")
               or DEFAULT_RATE).strip()
    if not _RATE_RE.match(rate):
        return ToolResult(text='[ERROR] rate must look like "+0%", "+6%" or "-10%"')
    voice = str(explicit_voice or DEFAULT_NARRATION_VOICE).strip()
    speed = _parse_rate_speed(rate)
    fn = _make_cloud_tts_fn(voice, speed, ctx)
    workers = CLOUD_TTS_WORKERS
    ext = ".mp3"

    out_path = ctx.resolve(args.get("output_json") or "out/script_tts.json")
    tts_dir = ctx.resolve(args.get("audio_dir") or ".video_agent/narration_tts")
    tts_dir.mkdir(parents=True, exist_ok=True)
    semantic_out = ctx.resolve(args["semantic_out"]) if args.get("semantic_out") else None

    started = time.time()

    # 断点续跑: 只有 文案+provider+voice+rate 指纹完全一致才继承段级结果;
    # 仅按 seg_id 复用会在改稿/换音色后继续播放旧音频 (严重内容错配)。
    cached_done: dict[str, dict] = {}
    if out_path.exists():
        try:
            for d in _load_json(out_path):
                ap = d.get("audio_path")
                if (d.get("sentences") and d.get("_tts_complete", False)
                        and ap and Path(ap).exists()):
                    cached_done[d["seg_id"]] = d
        except Exception:
            pass
    done: dict[str, dict] = {}
    for s in segs:
        d = cached_done.get(s["seg_id"])
        if d and d.get("_tts_fp") == _tts_fingerprint(s, provider, by_sentence, voice, rate):
            done[s["seg_id"]] = d
            for key in ("audio_path", "audio_dur", "speech_dur", "sentences",
                        "delivery_pause_sec", "tts_mode", "_tts_fp", "_tts_complete",
                        "verify"):
                if key in d:
                    s[key] = d[key]
    pending = [s for s in segs if s["seg_id"] not in done]

    failures: list[dict] = []

    if by_sentence and pending:
        # 句级并行: 跨全部待办段, 每句独立任务; 顺序拼接与句级时间轴在合成后按序重建
        seg_units = {s["seg_id"]: _timing_units(s) for s in pending}
        seg_sents = {seg_id: [u["spoken_text"] for u in units]
                     for seg_id, units in seg_units.items()}
        jobs = [(s["seg_id"], j, sent)
                for s in pending for j, sent in enumerate(seg_sents[s["seg_id"]])]

        def _work(job):
            seg_id, j, sent = job
            # 句级文件缓存指纹同样绑 provider+voice+rate
            base = str((tts_dir / f"{seg_id}_{j}_{_sent_fp(provider, voice, rate, sent)}").resolve())
            cached = base + ext
            if Path(cached).exists():
                if _valid_audio(cached):
                    return seg_id, j, cached, None      # 断点续跑: 复用已生成句
                Path(cached).unlink(missing_ok=True)    # 坏/空文件删掉重合成
            try:
                return seg_id, j, fn(sent, base), None
            except Exception as exc:  # noqa: BLE001
                return seg_id, j, None, f"{type(exc).__name__}: {str(exc)[:120]}"

        paths: dict[tuple[str, int], str | None] = {}
        sent_errors: dict[str, list[str]] = {}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            for seg_id, j, ap, err in ex.map(_work, jobs):
                paths[(seg_id, j)] = ap
                if err:
                    sent_errors.setdefault(seg_id, []).append(err)

        for s in pending:
            sents = seg_sents[s["seg_id"]]
            parts, timeline, t = [], [], 0.0
            for j, sent in enumerate(sents):
                ap = paths.get((s["seg_id"], j))
                if not ap:
                    continue
                ap = _trim_part(ap)
                d = round(_media_duration(ap), 3)
                unit = seg_units[s["seg_id"]][j]
                timeline.append({
                    "text": unit.get("subtitle_text", unit.get("text", sent)),
                    "subtitle_text": unit.get("subtitle_text", unit.get("text", sent)),
                    "spoken_text": sent, "start": round(t, 3),
                    "end": round(t + d, 3),
                    "semantic_unit_id": unit.get(
                        "semantic_unit_id", f"{s['seg_id']}_u{j + 1:02d}"),
                    "event_ids": list(unit.get("event_ids", s.get("event_ids", []))),
                    "claim_ids": list(unit.get("claim_ids", [])),
                    "anchor_shot_ids": list(unit.get("anchor_shot_ids", []))})
                t += d
                parts.append(ap)
            if not parts:
                failures.append({"seg_id": s["seg_id"], "reason": "no valid sentence audio",
                                 "errors": sent_errors.get(s["seg_id"], [])})
                continue
            try:
                fp = _tts_fingerprint(s, provider, by_sentence, voice, rate)
                raw_audio = str((tts_dir / f"{s['seg_id']}_sentence_{fp}{ext}").resolve())
                _concat_audio(parts, raw_audio)
                speech_dur = round(_media_duration(raw_audio), 3)
                pause = _pause_ms(s)
                final_audio = str((tts_dir /
                                   f"{s['seg_id']}_sentence_{fp}_p{pause}.wav").resolve())
                audio = _pad_audio(raw_audio, final_audio, pause)
                s["audio_path"] = audio
                s["speech_dur"] = speech_dur
                s["audio_dur"] = round(_media_duration(audio), 3)
                s["delivery_pause_sec"] = round(max(0.0, s["audio_dur"] - speech_dur), 3)
                s["tts_mode"] = "sentence"
                s["sentences"] = timeline
                s["_tts_fp"] = fp
                s["_tts_complete"] = len(parts) == len(sents)
                if not s["_tts_complete"]:
                    failures.append({
                        "seg_id": s["seg_id"],
                        "reason": f"only {len(parts)}/{len(sents)} sentences synthesized",
                        "errors": sent_errors.get(s["seg_id"], []),
                    })
            except Exception as exc:  # noqa: BLE001
                failures.append({"seg_id": s["seg_id"],
                                 "reason": f"concat/pad failed: {str(exc)[:160]}"})
    elif pending:
        # 默认整段合成: 一段只起一次调, 句内停连由 TTS 连续建模;
        # 句级时间轴按发音量估算切分
        def _work_paragraph(s: dict):
            fp = _tts_fingerprint(s, provider, by_sentence, voice, rate)
            text = _spoken_text(s)
            base = str((tts_dir / f"{s['seg_id']}_paragraph_{fp}").resolve())
            raw_audio = base + ext
            # 段级文件缓存: 指纹一致且音频有效则不重合成
            if not _valid_audio(raw_audio):
                Path(raw_audio).unlink(missing_ok=True)
                raw_audio = fn(text, base)
            speech_dur = round(_media_duration(raw_audio), 3)
            pause = _pause_ms(s)
            final_audio = str((tts_dir /
                               f"{s['seg_id']}_paragraph_{fp}_p{pause}.wav").resolve())
            if pause:
                if not _valid_audio(final_audio, max(0.1, speech_dur - 0.05)):
                    Path(final_audio).unlink(missing_ok=True)
                    _pad_audio(raw_audio, final_audio, pause)
                audio = final_audio
            else:
                audio = raw_audio
            audio_dur = round(_media_duration(audio), 3)
            return s["seg_id"], {
                "audio_path": audio, "audio_dur": audio_dur,
                "speech_dur": speech_dur,
                "delivery_pause_sec": round(max(0.0, audio_dur - speech_dur), 3),
                "sentences": _estimate_timeline(s, speech_dur),
                "tts_mode": "paragraph", "_tts_fp": fp, "_tts_complete": True,
            }

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_work_paragraph, s): s for s in pending}
            for future, source in list(futures.items()):
                try:
                    _, result = future.result()
                    source.update(result)
                except Exception as exc:  # noqa: BLE001
                    failures.append({"seg_id": source["seg_id"],
                                     "reason": f"{type(exc).__name__}: {str(exc)[:160]}"})

    # 忠实度回验: LLM-TTS 会改写/吞句/演绎 (实测), 回听是唯一能兜住的闸门。
    # pass/warn 均为终态不重验 (warn=末轮仍灰、已接受); 治愈会改写音频与句时间轴。
    if verify_mode == "asr":
        targets = [
            s for s in segs
            if s.get("_tts_complete") and _valid_audio(s.get("audio_path", ""))
            and (s.get("verify") or {}).get("status") not in ("pass", "warn")
        ]
        if targets:
            # 治愈阶段会并发调 TTS 委托, 不得突破付费后端的保守并发上限
            with ThreadPoolExecutor(max_workers=max(1, min(3, workers))) as ex:
                reports = list(ex.map(
                    lambda s: _verify_seg(s, ctx, tts_dir, ext, fn,
                                          provider, voice, rate, verify_retries),
                    targets))
            for s, rep in zip(targets, reports):
                s["verify"] = rep

    missing = [s.get("seg_id", "") for s in segs
               if not s.get("_tts_complete") or not _valid_audio(s.get("audio_path", ""))]

    # require_complete: 有失败段不写半成品 output_json (段级音频文件缓存仍在,
    # 重跑只补失败段); 非严格模式写出并在 data 里标 partial
    if missing and require_complete:
        return ToolResult(
            text=f"[ERROR] TTS incomplete for {len(missing)} of {len(segs)} segments; "
                 "output_json not written (audio file cache is kept, rerun to fill gaps)",
            data={
                "provider": provider, "voice": voice, "rate": rate,
                "mode": "sentence" if by_sentence else "paragraph",
                "segments_total": len(segs),
                "segments_cached": len(done),
                "missing_seg_ids": missing,
                "failures": failures,
                "audio_dir": str(tts_dir),
                "elapsed_seconds": round(time.time() - started, 3),
            },
        )

    _save_json(segs, out_path)
    if semantic_out is not None:
        _save_semantic_timeline(segs, semantic_out)

    total = sum(float(s.get("audio_dur", 0) or 0) for s in segs)
    data = {
        "provider": provider, "voice": voice, "rate": rate,
        "mode": "sentence" if by_sentence else "paragraph",
        "flatten_quotes": flatten_quotes,
        "segments_total": len(segs),
        "segments_cached": len(done),
        "segments_synthesized": len(pending) - len(
            {f["seg_id"] for f in failures} & {s["seg_id"] for s in pending}),
        "total_audio_seconds": round(total, 3),
        "output_json": str(out_path),
        "audio_dir": str(tts_dir),
        "semantic_out": str(semantic_out) if semantic_out is not None else None,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    verify_note = ""
    if verify_mode == "asr":
        v_fail = [s["seg_id"] for s in segs
                  if (s.get("verify") or {}).get("status") == "fail"]
        v_warn = [s["seg_id"] for s in segs
                  if (s.get("verify") or {}).get("status") == "warn"]
        data["verify"] = {"mode": "asr", "failed_seg_ids": v_fail,
                          "warn_seg_ids": v_warn}
        verify_note = (f" | verify: {len(v_fail)} fail / {len(v_warn)} warn"
                       if (v_fail or v_warn) else " | verify: all pass")
    artifacts = [str(out_path)] + ([str(semantic_out)] if semantic_out is not None else [])
    if missing:
        data["partial"] = True
        data["missing_seg_ids"] = missing
        data["failures"] = failures
        return ToolResult(
            text=f"[ERROR] narration TTS partial: {len(segs) - len(missing)}/{len(segs)} "
                 f"segments ready ({total:.1f}s) -> {ctx.virtualize(out_path)}; "
                 "output_json written with incomplete segments flagged",
            data=data, artifacts=artifacts,
        )
    return ToolResult(
        text=f"Narration TTS complete: {len(segs)} segments, {total:.1f}s total "
             f"-> {ctx.virtualize(out_path)}{verify_note}",
        data=data, artifacts=artifacts,
    )


def _verify_heard(audio_path: str, ctx: RunContext, tag: str) -> tuple[str | None, int]:
    """段音频 ASR 回听: 返回 (听写全文, 说话人数)。ASR 挂了返回 (None, 0),
    调用方退化为只用时长指标且 status 封顶 warn——不许假 pass。"""
    from .media import speech_transcribe
    vdir = ctx.resolve(".video_agent/narration_tts/_verify")
    work = vdir / tag                    # 每段固定目录, 重试轮覆写不留垃圾
    work.mkdir(parents=True, exist_ok=True)
    output_json = work / "transcript.json"
    try:
        got = speech_transcribe({
            "input_path": str(audio_path),
            "output_json": str(output_json),
            "work_dir": str(work),
            "language": "zh",
            "timeout_seconds": 300.0,
            "poll_interval_seconds": 3.0,
        }, ctx)
    except Exception:
        return None, 0
    if got.text.startswith("[ERROR]"):
        return None, 0
    try:
        payload = json.loads(output_json.read_text(encoding="utf-8"))
    except Exception:
        return None, 0
    rows = payload.get("segments") or payload.get("utterances") or []
    utts = [u for u in rows if isinstance(u, dict)]
    heard = "".join(str(u.get("text", "")) for u in utts)
    speakers = {str(u.get("speaker", "")).strip()
                for u in utts if str(u.get("speaker", "")).strip()}
    return heard, len(speakers)


def _rebuild_sentence_seg(s: dict, tts_dir: Path, ext: str,
                          provider: str, voice: str, rate: str) -> None:
    """按稳定命名公式重收集句音频, 重拼段音频并刷新句级时间轴。"""
    parts, t = [], 0.0
    for j, sent in enumerate(s["sentences"]):
        spoken = str(sent.get("spoken_text", ""))
        raw = tts_dir / f"{s['seg_id']}_{j}_{_sent_fp(provider, voice, rate, spoken)}{ext}"
        ap = _trim_part(str(raw))
        d = round(_media_duration(ap), 3)
        sent["start"], sent["end"] = round(t, 3), round(t + d, 3)
        t += d
        parts.append(str(ap))
    fp = s["_tts_fp"]
    raw_audio = str((tts_dir / f"{s['seg_id']}_sentence_{fp}{ext}").resolve())
    Path(raw_audio).unlink(missing_ok=True)
    _concat_audio(parts, raw_audio)
    speech_dur = round(_media_duration(raw_audio), 3)
    pause = _pause_ms(s)
    final_audio = str((tts_dir / f"{s['seg_id']}_sentence_{fp}_p{pause}.wav").resolve())
    Path(final_audio).unlink(missing_ok=True)
    audio = _pad_audio(raw_audio, final_audio, pause)
    s["audio_path"] = audio
    s["speech_dur"] = speech_dur
    s["audio_dur"] = round(_media_duration(audio), 3)
    s["delivery_pause_sec"] = round(max(0.0, s["audio_dur"] - speech_dur), 3)


def _verify_seg(s: dict, ctx: RunContext, tts_dir: Path, ext: str, fn,
                provider: str, voice: str, rate: str, retries: int) -> dict:
    """忠实度回验: ASR 内容命中 + 句时长合理性双指标。

    判定(实测校准): 长句(≥6字)命中<0.35 或时长越界 = 坏句; 0.35~0.7 = 灰句。
    坏句和灰句在非末轮都删句级缓存重合成(灰区曾漏过半句改写, 不再直接放行),
    末轮仍灰才以 warn 接受。短句(<6字)ASR 误伤率高, 要求 hit==0 且时长越界
    双证据才判坏。词全对(hit≥0.7)只是读得慢的句子豁免 "too long"(重合成
    大概率同样慢, 纯烧配额)。ASR 整体不可用时只剩时长指标, status 封顶 warn
    并置 reason=asr_unavailable——不许假 pass。说话人 >1 只记警告。"""
    seg_id = s["seg_id"]
    sentence_mode = s.get("tts_mode") == "sentence"
    rep: dict = {"status": "pass", "rounds": 0}
    for rnd in range(retries + 1):
        heard, n_spk = _verify_heard(s["audio_path"], ctx, seg_id)
        units = (s.get("sentences", []) if sentence_mode
                 else [{"spoken_text": _spoken_text(s), "start": 0.0,
                        "end": float(s.get("speech_dur", 0) or 0)}])
        bad, grey = [], []
        for j, sent in enumerate(units):
            spoken = str(sent.get("spoken_text", ""))
            chars = len(_norm_cjk(spoken))
            dur = float(sent.get("end", 0)) - float(sent.get("start", 0))
            issue = _duration_suspect(chars, dur)
            hit = _gram_hit_ratio(spoken, heard) if heard is not None else None
            if issue and "too long" in issue and hit is not None and hit >= 0.7:
                issue = None            # 词对速慢: 豁免, 见 docstring
            row = {"index": j, "text": spoken, "dur": round(dur, 2),
                   "hit": None if hit is None else round(hit, 2),
                   "duration_issue": issue}
            if chars >= 6:
                if issue or (hit is not None and hit < 0.35):
                    bad.append(row)
                elif hit is not None and hit < 0.7:
                    grey.append(row)
            else:
                if issue and hit == 0.0:
                    bad.append(row)     # 短句双证据
                elif hit == 0.0 and issue is None:
                    grey.append(row)
        rep.update({
            "rounds": rnd, "speakers": n_spk,
            "asr_available": heard is not None,
            "heard": (heard or "")[:400],
            "failed_sentences": bad, "warn_sentences": grey,
        })
        if heard is None:
            rep["reason"] = "asr_unavailable"
        heal = bad + (grey if rnd < retries else [])
        if not heal:
            rep["status"] = ("warn" if (grey or n_spk > 1 or heard is None)
                             else "pass")
            return rep
        if rnd == retries:
            rep["status"] = "fail" if bad else "warn"
            return rep
        # 治愈: 坏句/灰句删句级缓存后重合成, 再重拼段音频
        if sentence_mode:
            for item in heal:
                j = item["index"]
                spoken = str(s["sentences"][j].get("spoken_text", ""))
                base = str((tts_dir /
                            f"{seg_id}_{j}_{_sent_fp(provider, voice, rate, spoken)}").resolve())
                Path(base + ext).unlink(missing_ok=True)
                try:
                    fn(spoken, base)
                except Exception as exc:  # noqa: BLE001
                    item["retry_error"] = f"{type(exc).__name__}: {str(exc)[:120]}"
            try:
                _rebuild_sentence_seg(s, tts_dir, ext, provider, voice, rate)
            except Exception as exc:  # noqa: BLE001
                rep["status"] = "fail"
                rep["rebuild_error"] = str(exc)[:160]
                return rep
        else:
            # 整段模式: 删段音频整段重合成 (无句级粒度)
            fp = s["_tts_fp"]
            base = str((tts_dir / f"{seg_id}_paragraph_{fp}").resolve())
            Path(base + ext).unlink(missing_ok=True)
            pause = _pause_ms(s)
            Path(f"{base}_p{pause}.wav").unlink(missing_ok=True)
            try:
                raw_audio = fn(_spoken_text(s), base)
                speech_dur = round(_media_duration(raw_audio), 3)
                audio = (_pad_audio(raw_audio, f"{base}_p{pause}.wav", pause)
                         if pause else raw_audio)
                s["audio_path"] = audio
                s["speech_dur"] = speech_dur
                s["audio_dur"] = round(_media_duration(audio), 3)
                s["delivery_pause_sec"] = round(max(0.0, s["audio_dur"] - speech_dur), 3)
                s["sentences"] = _estimate_timeline(s, speech_dur)
            except Exception as exc:  # noqa: BLE001
                rep["status"] = "fail"
                rep["rebuild_error"] = str(exc)[:160]
                return rep
    return rep


def _save_semantic_timeline(segs: list[dict], out: Path) -> None:
    """语义时间轴: 每句的段内相对/全局绝对时间, 契约与 movie_cut semantic.json 一致。"""
    rows, global_start = [], 0.0
    for seg in segs:
        dur = float(seg.get("audio_dur", 0) or 0)
        for sent in seg.get("sentences", []):
            rows.append({
                "seg_id": seg.get("seg_id", ""),
                "semantic_unit_id": sent.get("semantic_unit_id", ""),
                "text": sent.get("subtitle_text", sent.get("text", "")),
                "subtitle_text": sent.get("subtitle_text", sent.get("text", "")),
                "spoken_text": sent.get("spoken_text", sent.get("text", "")),
                "relative_start": sent.get("start", 0),
                "relative_end": sent.get("end", 0),
                "global_start": round(global_start + float(sent.get("start", 0)), 3),
                "global_end": round(global_start + float(sent.get("end", 0)), 3),
                "event_ids": sent.get("event_ids", seg.get("event_ids", [])),
                "claim_ids": sent.get("claim_ids", []),
                "anchor_shot_ids": sent.get("anchor_shot_ids", []),
            })
        global_start += dur
    _save_json({"schema_version": "2.0", "n_units": len(rows), "units": rows}, out)
