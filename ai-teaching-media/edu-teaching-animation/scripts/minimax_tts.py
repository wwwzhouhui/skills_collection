#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""教学视频配音管线: storyboard.json → 分段 TTS 音频 + durations.json

用法:
    python3 minimax_tts.py <storyboard.json> [--outdir audio] [--provider minimax|edge|say|seed]
                           [--voice <voice_id>] [--speed 1.0] [--model speech-02-hd]
                           [--skip-existing]

Provider 优先级 (未显式指定时):
    1. storyboard.voice.provider
    2. 有 MINIMAX_API_KEY → minimax
    3. 否则 → edge (免费, 需外网; 依赖 pip install edge-tts)

Provider:
    minimax  付费高质量, 模型 speech-02-hd, 需要 MINIMAX_API_KEY
             可选: MINIMAX_GROUP_ID / MINIMAX_API_HOST / MINIMAX_TTS_MODEL
    edge     免费 Edge TTS (Microsoft 在线服务), 无需 API Key, 需外网
             默认音色 zh-CN-XiaoxiaoNeural
             仅默认音色可被 EDGE_TTS_VOICE 覆盖; CLI/storyboard 显式 voice 优先
    seed     火山引擎/豆包 Seed TTS 2.0 (HTTP unidirectional)
             需要 SEED_TTS_API_KEY 或 VOLCENGINE_API_KEY/ARK_API_KEY
             默认音色 zh_female_vv_uranus_bigtts, resource_id=seed-tts-2.0
    say      macOS 内置 TTS, 仅预览管线

--skip-existing: 已存在且参数指纹(provider/voice/speed/text/model)匹配的 mp3 可复用

输出 (写入 --outdir):
    seg-01.mp3 ...           每段旁白音频
    durations.json           每段音频时长 + 场景时间轴
    tts-cache.json           skip-existing 指纹缓存
"""

from __future__ import annotations

import argparse
import asyncio
import binascii
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HEAD_PAD = 0.6
TAIL_PAD = 0.9
DEFAULT_MIN_DURATION = 5.0
DEFAULT_VOICE = "female-chengshu"
DEFAULT_EDGE_VOICE = "zh-CN-XiaoxiaoNeural"
MIN_SPEED = 0.5
MAX_SPEED = 2.0
DEFAULT_EDGE_TIMEOUT = 60.0
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

EDGE_VOICE_ALIASES = {
    "female-chengshu": "zh-CN-XiaoxiaoNeural",
    "female-yujie": "zh-CN-XiaoyiNeural",
    "presenter_female": "zh-CN-XiaoxiaoNeural",
    "male-qn-jingying": "zh-CN-YunxiNeural",
    "male-qn-daxuesheng": "zh-CN-YunyangNeural",
    "presenter_male": "zh-CN-YunxiNeural",
}


def log(msg):
    print(msg, flush=True)


def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def clamp_speed(speed):
    try:
        s = float(speed)
    except (TypeError, ValueError):
        die(f"无效语速: {speed!r} (需要有限数字)")
    if not math.isfinite(s):
        die(f"无效语速: {speed!r} (不能是 NaN/Inf)")
    if s < MIN_SPEED or s > MAX_SPEED:
        die(f"语速超范围: {s} (允许 {MIN_SPEED} ~ {MAX_SPEED})")
    return s




def resolve_edge_timeout():
    raw = os.environ.get("EDGE_TTS_TIMEOUT", str(DEFAULT_EDGE_TIMEOUT))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        die(f"EDGE_TTS_TIMEOUT 无效: {raw!r} (需要正数秒)")
    if not math.isfinite(value) or value <= 0:
        die(f"EDGE_TTS_TIMEOUT 无效: {raw!r} (需要正数秒)")
    return value


def looks_like_minimax_voice(voice_id: str) -> bool:
    if not voice_id:
        return False
    v = str(voice_id).strip()
    if v in EDGE_VOICE_ALIASES:
        return True
    return v.startswith(("male-", "female-", "presenter", "moss_")) or (
        "-" in v and not v.startswith("zh-") and "Neural" not in v and not v.startswith(("en-", "ja-", "ko-"))
    )


def looks_like_edge_voice(voice_id: str) -> bool:
    if not voice_id:
        return False
    v = str(voice_id).strip()
    if v in EDGE_VOICE_ALIASES.values():
        return True
    # Edge neural voice pattern: lang-region-NameNeural
    return bool(re.match(r"^[A-Za-z]{2,3}-[A-Za-z]{2,}-.+Neural$", v))


def resolve_provider(cli_provider, voice_cfg):
    provider = cli_provider or voice_cfg.get("provider")
    if provider:
        return str(provider).strip().lower()
    return "minimax" if os.environ.get("MINIMAX_API_KEY") else "edge"


def resolve_voice_settings(provider, cli_voice, voice_cfg, cli_provider=None):
    """区分: CLI 显式 > provider 专属配置 > 兼容 storyboard.voice_id > 默认。

    当最终 provider 为 edge，而 storyboard.voice_id 是 Minimax 克隆音色等不兼容值时，
    优先使用 voice.edge_voice_id / EDGE_TTS_VOICE / 默认 edge 音色，避免把克隆 id 发给 Edge。
    """
    if cli_voice is not None and str(cli_voice).strip() != "":
        return str(cli_voice).strip(), "cli"

    edge_cfg = voice_cfg.get("edge_voice_id") or voice_cfg.get("edge_voice")
    minimax_cfg = voice_cfg.get("minimax_voice_id") or voice_cfg.get("minimax_voice")
    generic = voice_cfg.get("voice_id")
    generic = str(generic).strip() if generic is not None and str(generic).strip() != "" else None
    edge_cfg = str(edge_cfg).strip() if edge_cfg is not None and str(edge_cfg).strip() != "" else None
    minimax_cfg = str(minimax_cfg).strip() if minimax_cfg is not None and str(minimax_cfg).strip() != "" else None

    if provider == "edge":
        if edge_cfg:
            return edge_cfg, "storyboard.edge_voice_id"
        if generic and (looks_like_edge_voice(generic) or generic in EDGE_VOICE_ALIASES):
            return generic, "storyboard"
        # 不兼容的 Minimax/克隆音色不要传给 Edge
        if generic and not looks_like_edge_voice(generic) and generic not in EDGE_VOICE_ALIASES:
            env_voice = os.environ.get("EDGE_TTS_VOICE", "").strip()
            if env_voice:
                return env_voice, "env"
            return DEFAULT_EDGE_VOICE, "default"
        env_voice = os.environ.get("EDGE_TTS_VOICE", "").strip()
        if env_voice:
            return env_voice, "env"
        return DEFAULT_EDGE_VOICE, "default"

    if provider == "minimax":
        if minimax_cfg:
            return minimax_cfg, "storyboard.minimax_voice_id"
        if generic:
            return generic, "storyboard"
        return DEFAULT_VOICE, "default"

    if provider == "seed":
        seed_cfg = voice_cfg.get("seed_voice_id") or voice_cfg.get("seed_voice")
        seed_cfg = str(seed_cfg).strip() if seed_cfg is not None and str(seed_cfg).strip() != "" else None
        if seed_cfg:
            return seed_cfg, "storyboard.seed_voice_id"
        if generic and looks_like_seed_voice(generic):
            return generic, "storyboard.voice_id"
        if generic and (looks_like_edge_voice(generic) or generic in EDGE_VOICE_ALIASES or looks_like_minimax_voice(generic)):
            return resolve_seed_voice(generic), "mapped.voice_id"
        env_voice = os.environ.get("SEED_TTS_VOICE", "").strip() or os.environ.get("DEFAULT_SEED_VOICE", "").strip()
        if env_voice:
            return env_voice, "env"
        if generic:
            return generic, "storyboard.voice_id"
        return DEFAULT_SEED_VOICE, "default"

    if provider == "say":
        if generic and not looks_like_minimax_voice(generic) and not looks_like_edge_voice(generic):
            return generic, "storyboard"
        return "Tingting", "default"

    if generic:
        return generic, "storyboard"
    return DEFAULT_VOICE, "default"

def resolve_edge_voice(voice_id, allow_env_fallback=False):
    if voice_id is None or str(voice_id).strip() == "":
        if allow_env_fallback:
            env_voice = os.environ.get("EDGE_TTS_VOICE", "").strip()
            if env_voice:
                return env_voice
        return DEFAULT_EDGE_VOICE
    voice_id = str(voice_id).strip()
    if voice_id in EDGE_VOICE_ALIASES:
        return EDGE_VOICE_ALIASES[voice_id]
    if voice_id.startswith(("male-", "female-", "presenter", "moss_")):
        return EDGE_VOICE_ALIASES.get(voice_id, DEFAULT_EDGE_VOICE)
    return voice_id


def speed_to_edge_rate(speed):
    s = clamp_speed(speed)
    pct = int(round((s - 1.0) * 100))
    return f"{pct:+d}%"


def atomic_write_bytes(path: Path, data: bytes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def audio_temp_path(path: Path, suffix: str | None = None) -> Path:
    """Return a unique sibling temp path whose final suffix stays codec-readable."""
    path = Path(path)
    final_suffix = path.suffix if suffix is None else suffix
    return path.parent / f".{path.stem}.tmp.{os.getpid()}.{time.time_ns()}{final_suffix}"


def write_validated_audio(path: Path, data: bytes):
    """Validate new audio before atomically replacing an existing output."""
    path = Path(path)
    tmp = audio_temp_path(path)
    try:
        tmp.write_bytes(data)
        probe_duration(tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def fingerprint_payload(provider, voice, speed, text, model):
    raw = json.dumps(
        {
            "provider": provider,
            "voice": voice,
            "speed": round(float(speed), 4),
            "text": text,
            "model": model if provider in ("minimax", "seed") else "",
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_cache(path: Path):
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(path: Path, cache: dict):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(cache, ensure_ascii=False, indent=2).encode("utf-8")
    atomic_write_bytes(path, payload)


def is_valid_audio(path: Path):
    if not path.exists() or path.stat().st_size < 64:
        return False
    try:
        probe_duration(path)
        return True
    except Exception:
        return False


def can_skip_existing(path: Path, cache: dict, key: str, fingerprint: str):
    if not is_valid_audio(path):
        return False
    entry = cache.get(key)
    if not isinstance(entry, dict):
        return False
    return entry.get("fingerprint") == fingerprint


def sanitize_segment_id(raw_id, used_ids: set):
    if isinstance(raw_id, bool) or not isinstance(raw_id, (int, str)):
        die(f"segment.id 类型无效: {raw_id!r}")
    if isinstance(raw_id, int):
        if raw_id < 0:
            die(f"segment.id 非法: {raw_id!r}")
        sid = str(raw_id)
    else:
        sid = str(raw_id).strip()
        if not sid or not SAFE_ID_RE.match(sid):
            die(f"segment.id 非法: {raw_id!r} (仅允许字母数字._-)")
        if sid.isdigit():
            # 统一 "01" / "1"，避免映射到同一文件名
            sid = str(int(sid))
    collision_key = sid.casefold()
    if collision_key in used_ids:
        die(f"segment.id 重复: {sid}")
    used_ids.add(collision_key)
    return sid


def validate_segments(segments):
    if not isinstance(segments, list) or not segments:
        die("storyboard.json 缺少非空 segments 数组")
    used_ids = set()
    cleaned = []
    for idx, seg in enumerate(segments, 1):
        if not isinstance(seg, dict):
            die(f"segments[{idx}] 必须是对象")
        if "id" not in seg:
            die(f"segments[{idx}] 缺少 id")
        sid = sanitize_segment_id(seg["id"], used_ids)
        narration = seg.get("narration")
        if not isinstance(narration, str):
            die(f"segment {sid} 的 narration 必须是字符串, 实际={type(narration).__name__}")
        text = narration.strip()
        if not text:
            die(f"segment {sid} 的 narration 为空")
        cleaned.append({**seg, "id": sid, "narration": text})
    return cleaned



DEFAULT_SEED_VOICE = "zh_female_vv_uranus_bigtts"
DEFAULT_SEED_RESOURCE = "seed-tts-2.0"
DEFAULT_SEED_URL = "https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional"
DEFAULT_SEED_TIMEOUT = 120.0

SEED_VOICE_ALIASES = {
    "female-chengshu": "zh_female_vv_uranus_bigtts",
    "female-yujie": "zh_female_gaolengyujie_uranus_bigtts",
    "presenter_female": "zh_female_vv_uranus_bigtts",
    "male-qn-jingying": "zh_male_dayi_uranus_bigtts",
    "male-qn-daxuesheng": "zh_male_yangguangqingnian_uranus_bigtts",
    "presenter_male": "zh_male_dayi_uranus_bigtts",
    "zh-CN-XiaoxiaoNeural": "zh_female_vv_uranus_bigtts",
    "zh-CN-XiaoyiNeural": "zh_female_cancan_uranus_bigtts",
    "zh-CN-YunxiNeural": "zh_male_dayi_uranus_bigtts",
    "zh-CN-YunyangNeural": "zh_male_yangguangqingnian_uranus_bigtts",
}


def looks_like_seed_voice(voice_id: str) -> bool:
    if not voice_id:
        return False
    v = str(voice_id).strip()
    if v in SEED_VOICE_ALIASES or v in SEED_VOICE_ALIASES.values():
        return True
    return v.startswith(("zh_female_", "zh_male_", "en_female_", "en_male_", "ICL_"))


def resolve_seed_voice(voice_id, allow_env_fallback=False):
    if voice_id is None or str(voice_id).strip() == "":
        if allow_env_fallback:
            env_voice = os.environ.get("SEED_TTS_VOICE", "").strip() or os.environ.get("DEFAULT_SEED_VOICE", "").strip()
            if env_voice:
                return env_voice
        return DEFAULT_SEED_VOICE
    voice_id = str(voice_id).strip()
    if voice_id in SEED_VOICE_ALIASES:
        return SEED_VOICE_ALIASES[voice_id]
    if looks_like_edge_voice(voice_id) or looks_like_minimax_voice(voice_id):
        return SEED_VOICE_ALIASES.get(voice_id, DEFAULT_SEED_VOICE)
    return voice_id


def speed_to_seed_speech_rate(speed) -> int:
    """Map platform speed 0.5~2.0 -> Seed speech_rate roughly -50~100."""
    s = clamp_speed(speed)
    rate = int(round((s - 1.0) * 100))
    return max(-50, min(100, rate))


def resolve_seed_api_key():
    for name in ("SEED_TTS_API_KEY", "VOLCENGINE_API_KEY", "ARK_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val, name
    return "", ""


def tts_seed(text, out_path, voice_id, speed, model):
    """Volcengine / 豆包 Seed TTS 2.0 via HTTP unidirectional stream (NDJSON base64)."""
    import base64
    import uuid

    api_key, key_source = resolve_seed_api_key()
    if not api_key:
        die(
            "SEED_TTS_API_KEY / VOLCENGINE_API_KEY / ARK_API_KEY 未设置。"
            "导出后重试, 或改用 --provider edge。"
        )

    url = os.environ.get("SEED_TTS_URL", DEFAULT_SEED_URL).strip() or DEFAULT_SEED_URL
    resource_id = (
        (model if model and str(model).strip() and str(model).strip() != "speech-02-hd" else None)
        or os.environ.get("SEED_TTS_RESOURCE_ID", "").strip()
        or DEFAULT_SEED_RESOURCE
    )
    speaker = resolve_seed_voice(voice_id, allow_env_fallback=True)
    speech_rate = speed_to_seed_speech_rate(speed)
    sample_rate = int(os.environ.get("SEED_TTS_SAMPLE_RATE", "24000") or 24000)
    timeout = float(os.environ.get("SEED_TTS_HTTP_TIMEOUT", str(DEFAULT_SEED_TIMEOUT)) or DEFAULT_SEED_TIMEOUT)
    retries = int(os.environ.get("SEED_TTS_HTTP_RETRIES", "2") or 2)
    retries = max(0, retries)

    payload = {
        "user": {"uid": os.environ.get("SEED_TTS_UID", "ai-teaching-video-platform")},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "audio_params": {
                "format": "mp3",
                "sample_rate": sample_rate,
                "speech_rate": speech_rate,
            },
        },
    }

    last_err = None
    for attempt in range(retries + 1):
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            chunks = []
            finished = False
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise RuntimeError(f"Seed TTS 返回非 JSON: {e}: {line[:120]}") from e
                code = obj.get("code")
                if code == 20000000:
                    finished = True
                    continue
                if code not in (0, None):
                    msg = obj.get("message") or obj.get("msg") or str(obj)
                    raise RuntimeError(f"Seed TTS error code={code}: {msg}")
                data = obj.get("data")
                if data:
                    chunks.append(base64.b64decode(data))
            if not chunks:
                raise RuntimeError("Seed TTS 响应无音频 data")
            audio = b"".join(chunks)
            if not audio.startswith((b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")) and audio[:2] != b"\xff\xfa":
                # still accept if length ok; probe_duration will validate
                pass
            write_validated_audio(out_path, audio)
            return
        except (urllib.error.URLError, RuntimeError, ValueError, binascii.Error, TimeoutError) as e:
            last_err = e
            wait = 2 * (attempt + 1)
            log(f"   ⚠ Seed TTS 第 {attempt + 1} 次失败 ({e}), {wait}s 后重试... key={key_source} resource={resource_id}")
            time.sleep(wait)
    die(f"Seed TTS 连续失败: {last_err}")


def tts_minimax(text, out_path, voice_id, speed, model):
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        die("MINIMAX_API_KEY 未设置。导出后重试, 或改用 --provider edge / --provider say。")

    host = os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com").rstrip("/")
    url = f"{host}/v1/t2a_v2"
    group_id = os.environ.get("MINIMAX_GROUP_ID")
    if group_id:
        url += f"?GroupId={group_id}"

    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "language_boost": "Chinese",
        "output_format": "hex",
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            status = body.get("base_resp", {}).get("status_code")
            if status != 0:
                msg = body.get("base_resp", {}).get("status_msg", "unknown")
                if status in (1004, 2013):
                    die(f"Minimax 返回错误 status_code={status}: {msg}")
                raise RuntimeError(f"status_code={status}: {msg}")
            audio_hex = body.get("data", {}).get("audio")
            if not audio_hex:
                raise RuntimeError("响应缺少 data.audio")
            write_validated_audio(out_path, binascii.unhexlify(audio_hex))
            return
        except (urllib.error.URLError, RuntimeError, ValueError, binascii.Error) as e:
            last_err = e
            wait = 2 * (attempt + 1)
            log(f"   ⚠ 第 {attempt + 1} 次调用失败 ({e}), {wait}s 后重试...")
            time.sleep(wait)
    die(f"Minimax TTS 连续失败: {last_err}")


def tts_edge(text, out_path, voice_id, speed, model, timeout=None):
    try:
        import edge_tts
    except ImportError:
        die("未安装 edge-tts。请先执行: pip install edge-tts")

    voice = resolve_edge_voice(voice_id, allow_env_fallback=False)
    rate = speed_to_edge_rate(speed)
    timeout = resolve_edge_timeout() if timeout is None else float(timeout)
    out_path = Path(out_path)

    last_err = None
    for attempt in range(3):
        tmp_path = audio_temp_path(out_path)

        async def _run():
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate)
            await asyncio.wait_for(communicate.save(str(tmp_path)), timeout=timeout)

        try:
            asyncio.run(_run())
            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise RuntimeError("edge-tts 未生成有效音频文件")
            # 先校验临时文件，再原子替换，避免留下损坏正式文件
            probe_duration(tmp_path)
            os.replace(tmp_path, out_path)
            return
        except Exception as e:
            last_err = e
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            wait = 2 * (attempt + 1)
            log(f"   ⚠ Edge TTS 第 {attempt + 1} 次失败 ({e}), {wait}s 后重试...")
            time.sleep(wait)
    die(f"Edge TTS 连续失败: {last_err}")


def tts_say(text, out_path, voice_id, speed, model):
    voice = (
        voice_id
        if voice_id and not str(voice_id).startswith(("male-", "female-", "presenter", "moss_"))
        else "Tingting"
    )
    out_path = Path(out_path)
    aiff = audio_temp_path(out_path, ".aiff")
    tmp_path = audio_temp_path(out_path)
    rate = int(180 * clamp_speed(speed))
    try:
        subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", str(aiff), text], check=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff),
                "-ar", "32000", "-b:a", "128k", str(tmp_path),
            ],
            check=True,
        )
        probe_duration(tmp_path)
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
    finally:
        if aiff.exists():
            try:
                aiff.unlink()
            except OSError:
                pass


PROVIDERS = {"minimax": tts_minimax, "edge": tts_edge, "seed": tts_seed, "say": tts_say}


def probe_duration(path):
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    duration = float(out.stdout.strip())
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError(f"音频时长无效: {duration!r} ({path})")
    return duration


def format_seg_filename(sid: str) -> str:
    if sid.isdigit():
        return f"seg-{int(sid):02d}.mp3"
    return f"seg-{sid}.mp3"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("storyboard", help="storyboard.json 路径")
    ap.add_argument("--outdir", default="audio", help="音频输出目录 (默认 audio/)")
    ap.add_argument(
        "--provider",
        choices=list(PROVIDERS),
        default=None,
        help="TTS 引擎 (默认: storyboard.voice.provider → 有 MINIMAX_API_KEY 用 minimax, 否则 edge)",
    )
    ap.add_argument("--voice", default=None, help="音色 id (默认: storyboard.voice.voice_id / provider 默认音色)")
    ap.add_argument("--speed", type=float, default=None, help=f"语速 (默认 1.0, 范围 {MIN_SPEED}-{MAX_SPEED})")
    ap.add_argument(
        "--model",
        default=None,
        help="Minimax 模型 (默认 MINIMAX_TTS_MODEL 或 speech-02-hd; edge/say 忽略)",
    )
    ap.add_argument(
        "--skip-existing",
        action="store_true",
        help="已存在且指纹匹配的 mp3 不重新生成",
    )
    args = ap.parse_args()

    sb_path = Path(args.storyboard)
    if not sb_path.exists():
        die(f"找不到 {sb_path}")
    try:
        sb = json.loads(sb_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        die(f"storyboard.json 不是合法 JSON: {e}")
    if not isinstance(sb, dict):
        die("storyboard.json 根节点必须是对象")

    segments = validate_segments(sb.get("segments"))
    voice_cfg = sb.get("voice")
    if voice_cfg is None:
        voice_cfg = {}
    elif not isinstance(voice_cfg, dict):
        die("storyboard.voice 必须是对象")

    provider = resolve_provider(args.provider, voice_cfg)
    if provider not in PROVIDERS:
        die(f"不支持的 provider: {provider}")
    voice_id, voice_source = resolve_voice_settings(provider, args.voice, voice_cfg, cli_provider=args.provider)
    speed = clamp_speed(args.speed if args.speed is not None else voice_cfg.get("speed", 1.0))
    if provider == "seed":
        model = args.model or os.environ.get("SEED_TTS_RESOURCE_ID", DEFAULT_SEED_RESOURCE)
    else:
        model = args.model or os.environ.get("MINIMAX_TTS_MODEL", "speech-02-hd")
    tts = PROVIDERS[provider]
    edge_timeout = resolve_edge_timeout() if provider == "edge" else None

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cache_path = outdir / "tts-cache.json"
    cache = load_cache(cache_path)

    if provider == "edge":
        display_voice = resolve_edge_voice(voice_id)
    elif provider == "seed":
        display_voice = resolve_seed_voice(voice_id, allow_env_fallback=True)
    else:
        display_voice = voice_id
    if provider == "edge":
        log(
            f"==> TTS: provider=edge voice={display_voice} (source={voice_source}) "
            f"speed={speed} rate={speed_to_edge_rate(speed)} timeout={edge_timeout}s"
        )
    else:
        log(
            f"==> TTS: provider={provider} voice={display_voice} (source={voice_source}) speed={speed}"
            + (f" model={model}" if provider == "minimax" else (f" resource={os.environ.get('SEED_TTS_RESOURCE_ID', DEFAULT_SEED_RESOURCE)}" if provider == "seed" else ""))
        )

    cursor = 0.0
    results = []
    for i, seg in enumerate(segments, 1):
        sid = seg["id"]
        narration = seg["narration"]
        out_path = outdir / format_seg_filename(sid)
        cache_key = out_path.name
        fp = fingerprint_payload(provider, display_voice, speed, narration, model)
        log(f"   [{i}/{len(segments)}] id={sid} {seg.get('title', '')} ({len(narration)} 字)")

        if args.skip_existing and can_skip_existing(out_path, cache, cache_key, fp):
            log(f"      复用已有音频 ({out_path.name})")
        else:
            if provider == "edge":
                tts_edge(narration, out_path, display_voice, speed, model, timeout=edge_timeout)
            else:
                tts(narration, out_path, voice_id, speed, model)
            if not is_valid_audio(out_path):
                die(f"生成音频无效: {out_path}")
            cache[cache_key] = {
                "fingerprint": fp,
                "provider": provider,
                "voice": display_voice,
                "speed": speed,
                "text": narration,
                "model": model if provider in ("minimax", "seed") else "",
            }
            save_cache(cache_path, cache)

        audio_dur = round(probe_duration(out_path), 2)
        min_dur = float(seg.get("min_duration", DEFAULT_MIN_DURATION))
        scene_dur = round(max(HEAD_PAD + audio_dur + TAIL_PAD, min_dur), 2)
        results.append({
            "id": int(sid) if sid.isdigit() else sid,
            "title": seg.get("title", ""),
            "file": f"{outdir.name}/{out_path.name}",
            "audio_duration": audio_dur,
            "start": round(cursor, 2),
            "audio_start": round(cursor + HEAD_PAD, 2),
            "duration": scene_dur,
            "subtitle": narration,
        })
        cursor += scene_dur

    save_cache(cache_path, cache)
    manifest = {
        "topic": sb.get("topic", ""),
        "provider": provider,
        "voice_id": display_voice,
        "speed": speed,
        "head_pad": HEAD_PAD,
        "tail_pad": TAIL_PAD,
        "total": round(cursor, 2),
        "segments": results,
    }
    manifest_path = outdir / "durations.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"✅ {len(results)} 段音频 → {outdir}/  总时长 {manifest['total']}s")
    log(f"✅ 时间轴 → {manifest_path}  (把 segments 的 start/duration/audio_start 抄进 index.html)")


if __name__ == "__main__":
    main()
