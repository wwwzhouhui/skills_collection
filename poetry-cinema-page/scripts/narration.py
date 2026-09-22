#!/usr/bin/env python3
"""Narration (TTS) generator for the poetry-cinema-page skill.

Two engines, selectable per run or via config/ark.config.json:

  edge-tts         free, local, no API key; returns mp3
  doubao-seed-tts  Volcengine Doubao seed-tts-2.0 over the Ark plan gateway;
                   reuses the same Ark key as the image pipeline; returns streaming WAV

Commands
--------
    python scripts/narration.py voices [--engine edge-tts]
    python scripts/narration.py probe [--live]
    python scripts/narration.py audition --text "君不见黄河之水天上来"
    python scripts/narration.py say   --text "..." --out public/audio/x.mp3
    python scripts/narration.py build --text-file poem.txt --out public/audio/x.mp3 --srt x.srt

`build` treats the text file as a narration script: `#` lines are comments, a blank
line starts a new paragraph (longer pause), every other line is one spoken segment.
It concatenates all segments with pauses, normalises loudness, and writes a sidecar
JSON (and optional SRT) with per-line timings.

Standard library only; ffmpeg is required for concatenation and format conversion.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent
SKILL_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))
from ark_image import ArkError, load_config, mask, resolve_api_key  # noqa: E402

EDGE_ENGINE = "edge-tts"
DOUBAO_ENGINE = "doubao-seed-tts"
VOLC_STREAM_END = 20000000
RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504}


# --------------------------------------------------------------------------- helpers


def need_ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise ArkError(
            "ffmpeg not found on PATH. It is required for audio concatenation and format "
            "conversion. Install ffmpeg, or use `say` for a single un-joined clip."
        )
    return exe


def ffprobe_duration(path: Path) -> float:
    exe = shutil.which("ffprobe")
    if not exe:
        raise ArkError("ffprobe not found on PATH; needed to measure segment durations.")
    result = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, timeout=120,
    )
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise ArkError(f"ffprobe could not read a duration for {path}: {result.stderr[:200]}") from exc


def run_ffmpeg(args: list[str], label: str) -> None:
    exe = need_ffmpeg()
    result = subprocess.run([exe, "-hide_banner", "-loglevel", "error", *args],
                            capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        raise ArkError(f"ffmpeg failed ({label}): {result.stderr.strip()[:400]}")


def narration_config(config: dict) -> dict:
    block = config.get("narration")
    if not isinstance(block, dict):
        raise ArkError(
            "the config file has no 'narration' section; add one (see "
            "references/narration.md) or pass an updated config/ark.config.json."
        )
    return block


def resolve_engine(config: dict, requested: str | None) -> tuple[str, dict]:
    block = narration_config(config)
    engines = block.get("engines") or {}
    name = requested or block.get("engine") or EDGE_ENGINE
    if name not in engines:
        raise ArkError(
            f"unknown narration engine '{name}'. Configured: {', '.join(sorted(engines))}"
        )
    settings = dict(engines[name])
    if settings.get("_notes"):
        settings.pop("_notes", None)
    return name, settings


def catalog_for(config: dict, engine: str) -> list[dict]:
    catalog = narration_config(config).get("voice_catalog") or {}
    entries = catalog.get(engine) or []
    return [e for e in entries if isinstance(e, dict) and e.get("id")]


def output_settings(config: dict) -> dict:
    return narration_config(config).get("audio") or {}


def default_out(config: dict, poem_slug: str) -> Path:
    block = narration_config(config)
    out = output_settings(config)
    directory = Path(out.get("dir") or "public/audio")
    fmt = out.get("format") or "mp3"
    return directory / f"{poem_slug}.{fmt}"


# --------------------------------------------------------------------------- edge-tts


def synth_edge(config: dict, settings: dict, text: str, out_path: Path, voice: str | None) -> dict:
    try:
        import asyncio

        import edge_tts
    except ImportError as exc:
        raise ArkError(
            "the edge-tts package is not installed. Install it with "
            "`pip install edge-tts` (it needs no API key)."
        ) from exc

    chosen = voice or settings.get("voice")
    if not chosen:
        raise ArkError("no voice configured for edge-tts.")

    rate = settings.get("rate") or "+0%"
    volume = settings.get("volume") or "+0%"
    pitch = settings.get("pitch") or "+0Hz"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        async def go() -> None:
            communicate = edge_tts.Communicate(text, chosen, rate=rate, volume=volume, pitch=pitch)
            await communicate.save(str(out_path))

        asyncio.run(go())
    except Exception as exc:  # noqa: BLE001
        raise ArkError(f"edge-tts synthesis failed for voice '{chosen}': {exc}") from exc

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise ArkError(f"edge-tts produced no audio for voice '{chosen}'.")

    return {
        "engine": EDGE_ENGINE,
        "voice": chosen,
        "rate": rate,
        "volume": volume,
        "pitch": pitch,
        "format": "mp3",
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }


# --------------------------------------------------------------------------- doubao seed-tts


def _fix_streaming_wav_header(data: bytes) -> bytes:
    """The streaming encoder emits placeholder RIFF/data sizes; rewrite them."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        return data
    out = bytearray(data)
    pos = 12
    offset = None
    while pos + 8 <= len(out):
        chunk_id = bytes(out[pos:pos + 4])
        chunk_size = struct.unpack("<I", out[pos + 4:pos + 8])[0]
        if chunk_id == b"data":
            offset = pos + 8
            break
        pos += 8 + chunk_size
    if offset is None:
        return data
    struct.pack_into("<I", out, 4, len(out) - 8)
    struct.pack_into("<I", out, offset - 4, len(out) - offset)
    return bytes(out)


def _decode_volc_stream(raw: str, label: str) -> tuple[bytes, list, list]:
    """Split the unidirectional stream into JSON objects and join the audio chunks."""
    decoder = json.JSONDecoder()
    index = 0
    audio = bytearray()
    codes: list = []
    errors: list[str] = []
    length = len(raw)
    while index < length:
        while index < length and raw[index] in " \r\n\t":
            index += 1
        if index >= length:
            break
        try:
            obj, index = decoder.raw_decode(raw, index)
        except ValueError:
            break
        if not isinstance(obj, dict):
            continue
        code = obj.get("code")
        codes.append(code)
        chunk = obj.get("data")
        if chunk:
            try:
                audio += base64.b64decode(chunk)
            except (ValueError, TypeError) as exc:
                raise ArkError(f"[{label}] the TTS stream returned an invalid base64 chunk.") from exc
        elif code not in (0, VOLC_STREAM_END, None):
            errors.append(f"code {code}: {str(obj.get('message') or '')[:200]}")
    if not codes:
        raise ArkError(f"[{label}] unparsable TTS response: {raw[:200]!r}")
    return bytes(audio), codes, errors


def synth_doubao(config: dict, settings: dict, text: str, out_path: Path,
                 voice: str | None, label: str, api_key: str) -> dict:
    url = settings.get("url") or "https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional"
    resource_id = settings.get("resource_id") or "seed-tts-2.0"
    chosen = voice or settings.get("voice")
    if not chosen:
        raise ArkError("no voice configured for doubao-seed-tts.")
    if not api_key:
        raise ArkError(
            "doubao-seed-tts needs the Ark API key. Set ARK_API_KEY or put it in "
            "config/ark.local.json, or switch narration.engine to edge-tts (free, no key)."
        )

    sample_rate = int(settings.get("sample_rate") or 24000)
    audio_params: dict = {"format": "wav", "sample_rate": sample_rate}
    speed = settings.get("speed")
    if speed not in (None, ""):
        audio_params["speech_rate"] = max(-50, min(100, int(speed)))
    emotion = str(settings.get("emotion") or "").strip()
    if emotion:
        audio_params["emotion"] = emotion

    body = {
        "user": {"uid": "poetry-cinema-page"},
        "req_params": {"text": text, "speaker": chosen, "audio_params": audio_params},
    }
    request_id = str(uuid.uuid4())
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "X-Api-Key": api_key,
            "X-Api-Resource-Id": resource_id,
            "X-Api-Request-Id": request_id,
            "X-Api-Connect-Id": request_id,
            "X-Api-Sequence": "-1",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    timeout = float(config["api"].get("timeout_seconds", 300))
    retries = int(config["api"].get("max_retries", 2))
    backoff = float(config["api"].get("retry_backoff_seconds", 6))

    raw = ""
    started = time.monotonic()
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in RETRYABLE and attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            if exc.code in (401, 403):
                raise ArkError(
                    f"[{label}] TTS authentication failed (HTTP {exc.code}). Check that the Ark key "
                    f"is valid and that ARK resource '{resource_id}' is enabled for it. {detail}"
                ) from exc
            raise ArkError(f"[{label}] TTS request failed (HTTP {exc.code}): {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise ArkError(f"[{label}] TTS connection failed: {exc}") from exc

    audio, codes, errors = _decode_volc_stream(raw, label)
    if not audio:
        hint = ""
        if any("mismatched" in e for e in errors):
            hint = (
                " — this voice does not belong to resource id "
                f"'{resource_id}'. Use a voice from the doubao-seed-tts catalog in "
                "config/ark.config.json, or run `narration.py voices`."
            )
        raise ArkError(f"[{label}] the TTS stream contained no audio. {'; '.join(errors) or codes[:4]}{hint}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_fix_streaming_wav_header(audio))

    return {
        "engine": DOUBAO_ENGINE,
        "voice": chosen,
        "resource_id": resource_id,
        "sample_rate": sample_rate,
        "speech_rate": audio_params.get("speech_rate"),
        "emotion": emotion or None,
        "format": "wav",
        "bytes": len(audio),
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }


# --------------------------------------------------------------------------- formats

# What each engine actually returns, so a file's extension never lies about its bytes.
NATIVE_FORMAT = {EDGE_ENGINE: "mp3", DOUBAO_ENGINE: "wav"}


def native_extension(engine: str) -> str:
    return NATIVE_FORMAT.get(engine, "wav")


def convert_audio(src: Path, fmt: str, settings: dict) -> Path:
    """Transcode src to fmt when the engine's native container differs.

    Doubao streams WAV while edge-tts returns MP3, so writing either payload under the
    other's extension would mislabel the file. The extension always matches the bytes.
    """
    fmt = (fmt or "").lower().lstrip(".")
    if not fmt or src.suffix.lower().lstrip(".") == fmt:
        return src
    need_ffmpeg()
    target = src.with_suffix("." + fmt)
    rate = int(settings.get("sample_rate") or 24000)
    channels = int(settings.get("channels") or 1)
    bitrate = settings.get("bitrate") or "96k"
    codec = {
        "mp3": ["-c:a", "libmp3lame", "-b:a", bitrate],
        "m4a": ["-c:a", "aac", "-b:a", bitrate],
        "aac": ["-c:a", "aac", "-b:a", bitrate],
        "wav": ["-c:a", "pcm_s16le"],
    }.get(fmt, ["-b:a", bitrate])
    run_ffmpeg(["-y", "-i", str(src), "-ar", str(rate), "-ac", str(channels),
                *codec, str(target)], f"convert {src.name} to {fmt}")
    src.unlink(missing_ok=True)
    return target

# --------------------------------------------------------------------------- dispatch


def synthesize(config: dict, engine: str, settings: dict, text: str, out_path: Path,
               voice: str | None, label: str, api_key: str) -> dict:
    if engine == EDGE_ENGINE:
        return synth_edge(config, settings, text, out_path, voice)
    if engine == DOUBAO_ENGINE:
        return synth_doubao(config, settings, text, out_path, voice, label, api_key)
    raise ArkError(f"engine '{engine}' has no implementation.")


def read_api_key(config: dict, config_path: Path, engine: str, settings: dict) -> str:
    """Only resolve a key when the engine needs one."""
    if not settings.get("needs_api_key"):
        return ""
    try:
        return resolve_api_key(config, config_path)[0]
    except ArkError:
        raise ArkError(
            f"engine '{engine}' requires an Ark API key. Set ARK_API_KEY or create "
            "config/ark.local.json, or switch the engine to edge-tts (free, no key)."
        ) from None


# --------------------------------------------------------------------------- commands


def command_voices(args, config: dict, config_path: Path) -> int:
    block = narration_config(config)
    active = block.get("engine")
    engines = block.get("engines") or {}
    wanted = [args.engine] if args.engine else list(engines)

    for name in wanted:
        if name not in engines:
            print(f"unknown engine '{name}'", file=sys.stderr)
            return 2
        settings = engines[name] or {}
        current = settings.get("voice")
        print(f"\n=== {name} — {settings.get('label', '')}")
        print(f"    config engine : {active == name and 'ACTIVE' or 'inactive'}")
        print(f"    needs API key : {settings.get('needs_api_key')}")
        entries = catalog_for(config, name)
        if not entries:
            print("    (no catalog entries in the config)")
        for entry in entries:
            mark = "*" if entry["id"] == current else " "
            print(f"    {mark} {entry['id']:46s} {entry.get('gloss', '')}")
    print("\n  * = 当前配置的音色。gloss 由音色 ID 直译而来，最终请用 audition 试听决定。")
    print("  切换音色：改 config/ark.config.json 的 narration.engines.<engine>.voice，")
    print("  或运行时加 --voice <id>。\n")
    return 0


def command_probe(args, config: dict, config_path: Path) -> int:
    block = narration_config(config)
    engines = block.get("engines") or {}
    out = output_settings(config)

    print("config        :", config_path)
    print("active engine :", block.get("engine"))
    print("output dir    :", out.get("dir"), f"({out.get('format')}, {out.get('bitrate')})")
    print("ffmpeg        :", shutil.which("ffmpeg") or "MISSING (needed by build)")
    try:
        import edge_tts
        print("edge-tts      :", f"installed (v{getattr(edge_tts, '__version__', '?')})")
    except ImportError:
        print("edge-tts      : NOT INSTALLED (pip install edge-tts)")
    print()

    if args.dry_run:
        for name, settings in engines.items():
            print(f"  [{name:16s}] {settings.get('voice')}  (dry run, nothing synthesized)")
        return 0

    picks = [(args.engine, args.voice)] if args.engine else list(engines.items())
    failures = 0
    probe_text = args.text or "测试"
    tmp_dir = Path(tempfile.mkdtemp(prefix="narration-probe-"))
    try:
        for name, settings in picks:
            if not isinstance(settings, dict):
                continue
            voice = args.voice if args.engine and args.engine == name else None
            target = tmp_dir / f"{name}.{native_extension(name)}"
            try:
                key = read_api_key(config, config_path, name, settings)
                info = synthesize(config, name, settings, probe_text, target, voice, "probe", key)
                size = target.stat().st_size if target.is_file() else 0
                print(f"  [{name:16s}] OK   {info['voice']:44s} {size // 1024} KB  "
                      f"{info['elapsed_seconds']}s")
            except ArkError as exc:
                failures += 1
                print(f"  [{name:16s}] FAIL {exc}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if failures:
        print(f"\n{failures} engine(s) failed. edge-tts needs no key; doubao needs the Ark key.")
        return 1
    print("\nAll probed engines synthesized audio successfully.")
    if args.live:
        print("(--live is implied here: probe already speaks a short phrase.)")
    return 0


def command_audition(args, config: dict, config_path: Path) -> int:
    block = narration_config(config)
    engines = block.get("engines") or {}
    out = output_settings(config)
    engine = args.engine or block.get("engine")
    if engine not in engines:
        print(f"unknown engine '{engine}'", file=sys.stderr)
        return 2
    settings = dict(engines[engine] or {})

    if args.voices:
        voices = [v.strip() for v in args.voices.split(",") if v.strip()]
    else:
        voices = [e["id"] for e in catalog_for(config, engine)]

    directory = Path(args.out_dir) if args.out_dir else Path(out.get("dir") or "public/audio") / "audition"
    directory.mkdir(parents=True, exist_ok=True)
    target_format = (getattr(args, "format", None) or out.get("format") or "mp3").lower().lstrip(".")

    print(f"engine : {engine}")
    print(f"text   : {args.text}")
    print(f"voices : {len(voices)}")
    print(f"out    : {directory}\n")

    key = read_api_key(config, config_path, engine, settings)
    rows = []
    failures = 0
    for voice in voices:
        safe = voice.replace("/", "_")
        native_path = directory / f"{safe}.{native_extension(engine)}"
        try:
            info = synthesize(config, engine, settings, args.text, native_path, voice, "audition", key)
            final = convert_audio(native_path, target_format, {**out, **settings})
            size = final.stat().st_size
            seconds = ffprobe_duration(final)
            print(f"  OK   {voice:46s} {size // 1024:>5} KB  {seconds:.2f}s")
            rows.append({"voice": voice, "file": final.name, "bytes": size,
                         "seconds": round(seconds, 2), "info": info})
        except ArkError as exc:
            failures += 1
            print(f"  FAIL {voice:46s} {exc}")

    if rows:
        index = directory / "index.html"
        cards = "\n".join(
            f"""  <figure>
    <figcaption>{html.escape(r['voice'])}<span>{r['seconds']}s · {r['bytes'] // 1024} KB</span></figcaption>
    <audio controls preload="none" src="{html.escape(r['file'])}"></audio>
  </figure>""" for r in rows
        )
        index.write_text(
            f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8" /><title>音色试听 · {html.escape(engine)}</title>
<style>
  body {{ margin:0; padding:28px; background:#101416; color:#f2eadf;
         font-family:"Noto Serif SC","Songti SC",serif; }}
  h1 {{ font-size:18px; font-weight:500; margin:0 0 4px; }}
  p {{ color:rgba(242,234,223,.6); font-size:13px; margin:0 0 22px; }}
  figure {{ margin:0 0 14px; padding:12px 14px; border:1px solid rgba(255,255,255,.14); }}
  figcaption {{ display:flex; justify-content:space-between; font-size:13px; margin-bottom:8px; color:#d5b98d; }}
  figcaption span {{ color:rgba(242,234,223,.5); }}
  audio {{ width:100%; }}
  @media (min-width:900px) {{ .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }} }}
</style></head><body>
<h1>音色试听 · {html.escape(engine)}</h1>
<p>同一句「{html.escape(args.text)}」，{len(rows)} 个音色。选定后把 ID 填进 config/ark.config.json 的 narration.engines.{html.escape(engine)}.voice。</p>
<div class="grid">
{cards}
</div>
</body></html>
""",
            encoding="utf-8",
        )
        print(f"\n试听页: {index}")

    print(f"\n成功 {len(rows)}，失败 {failures}")
    return 1 if failures and not rows else 0


def _paragraphs(text_file: Path) -> list[list[str]]:
    """Split a narration script into paragraphs of lines."""
    if not text_file.is_file():
        raise ArkError(f"narration text file not found: {text_file}")
    raw = text_file.read_text(encoding="utf-8-sig")
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not stripped:
            if current:
                paragraphs.append(current)
                current = []
            continue
        current.append(stripped)
    if current:
        paragraphs.append(current)
    if not paragraphs:
        raise ArkError(f"the narration text file has no speakable lines: {text_file}")
    return paragraphs

def _structured_segments(source: Path, script_cfg: dict) -> list[list[str]]:
    """Compose narration paragraphs from a structured poem JSON.

    This is where narration.script.include_* actually takes effect: the title line is
    optional, and each verse line can carry its literal meaning and/or its close reading
    as extra spoken segments. Use it to narrate the interpretation, not just the poem.
    """
    if not source.is_file():
        raise ArkError(f"narration JSON not found: {source}")
    try:
        data = json.loads(source.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ArkError(f"narration JSON is not valid: {source} ({exc})") from exc
    if not isinstance(data, dict):
        raise ArkError(f"narration JSON must be an object: {source}")

    entries = data.get("lines")
    if not isinstance(entries, list) or not entries:
        raise ArkError(f"narration JSON needs a non-empty 'lines' array: {source}")

    want_original = bool(script_cfg.get("include_original", True))
    want_literal = bool(script_cfg.get("include_literal", False))
    want_analysis = bool(script_cfg.get("include_analysis", False))
    if not (want_original or want_literal or want_analysis):
        raise ArkError(
            "narration.script has include_original, include_literal and include_analysis all "
            "disabled, so there is nothing to speak. Enable at least one."
        )

    paragraphs: list[list[str]] = []
    title = str(data.get("title") or "").strip()
    if script_cfg.get("open_with_title", True) and title:
        template = str(script_cfg.get("title_template") or "《{title}》{author}")
        announcement = template.format(title=title, author=str(data.get("author") or "").strip())
        paragraphs.append([announcement.strip().strip("，,")])

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        group: list[str] = []
        if want_original and entry.get("original"):
            group.append(str(entry["original"]).strip())
        if want_literal and entry.get("literal"):
            group.append(str(entry["literal"]).strip())
        if want_analysis and entry.get("analysis"):
            group.append(str(entry["analysis"]).strip())
        group = [item for item in group if item]
        if group:
            paragraphs.append(group)

    if not paragraphs:
        raise ArkError(f"narration JSON produced no speakable segments: {source}")
    return paragraphs



def _to_canonical(ffmpeg_input: Path, target: Path, rate: int, channels: int) -> None:
    run_ffmpeg(["-y", "-i", str(ffmpeg_input), "-ar", str(rate), "-ac", str(channels),
                "-c:a", "pcm_s16le", str(target)], f"normalise {ffmpeg_input.name}")


def _silence(seconds: float, target: Path, rate: int, channels: int) -> None:
    run_ffmpeg(["-y", "-f", "lavfi", "-i", f"anullsrc=r={rate}:cl={'mono' if channels == 1 else 'stereo'}",
                "-t", f"{seconds:.3f}", "-c:a", "pcm_s16le", str(target)], "make silence")


def _srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def command_say(args, config: dict, config_path: Path) -> int:
    engine, settings = resolve_engine(config, args.engine)
    out = output_settings(config)
    requested = Path(args.out).expanduser()
    want_format = requested.suffix.lower().lstrip(".") or native_extension(engine)
    native_path = requested
    if requested.suffix.lower().lstrip(".") != native_extension(engine):
        native_path = requested.with_suffix("." + native_extension(engine))
    key = read_api_key(config, config_path, engine, settings)
    info = synthesize(config, engine, settings, args.text, native_path, args.voice,
                      args.name or requested.stem, key)
    final_path = convert_audio(native_path, want_format, {**out, **settings})
    info["output"] = str(final_path)
    info["format"] = want_format
    print(f"[{engine}] {info['voice']} -> {final_path} "
          f"({final_path.stat().st_size // 1024} KB, {info['elapsed_seconds']}s)")
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def command_build(args, config: dict, config_path: Path) -> int:
    engine, settings = resolve_engine(config, args.engine)
    out = output_settings(config)
    if args.format:
        out = dict(out, format=args.format)

    source = Path(args.text_file).expanduser()
    script_cfg = narration_config(config).get("script") or {}
    if args.include:
        wanted = {part.strip().lower() for part in args.include.split(",") if part.strip()}
        unknown = wanted - {"original", "literal", "analysis"}
        if unknown:
            raise ArkError(
                f"unknown --include layer(s): {', '.join(sorted(unknown))}. "
                "Use any of: original, literal, analysis."
            )
        script_cfg = {
            **script_cfg,
            "include_original": "original" in wanted,
            "include_literal": "literal" in wanted,
            "include_analysis": "analysis" in wanted,
        }
    if source.suffix.lower() == ".json":
        paragraphs = _structured_segments(source, script_cfg)
    else:
        paragraphs = _paragraphs(source)
    rate = int(args.sample_rate or out.get("sample_rate") or 24000)
    channels = int(out.get("channels") or 1)
    line_gap = args.gap if args.gap is not None else float(out.get("line_gap_seconds") or 0.75)
    para_gap = args.paragraph_gap if args.paragraph_gap is not None else float(
        out.get("paragraph_gap_seconds") or 1.6)
    fmt = (out.get("format") or "mp3").lower()
    bitrate = out.get("bitrate") or "128k"

    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    need_ffmpeg()

    line_count = sum(len(p) for p in paragraphs)
    print(f"engine     : {engine} ({settings.get('voice') or args.voice})")
    print(f"script     : {args.text_file}")
    print(f"paragraphs : {len(paragraphs)}   lines: {line_count}")
    print(f"gaps       : line {line_gap}s · paragraph {para_gap}s")
    print(f"output     : {out_path}\n")

    key = read_api_key(config, config_path, engine, settings)

    workdir = Path(tempfile.mkdtemp(prefix="narration-build-"))
    timeline: list[dict] = []
    try:
        pieces: list[Path] = []
        cursor = 0.0
        index = 0

        for p_idx, paragraph in enumerate(paragraphs):
            for l_idx, line in enumerate(paragraph):
                index += 1
                raw = workdir / f"{index:03d}-raw.{'mp3' if engine == EDGE_ENGINE else 'wav'}"
                canonical = workdir / f"{index:03d}.wav"

                info = synthesize(config, engine, settings, line, raw, args.voice,
                                  f"line{index}", key)
                _to_canonical(raw, canonical, rate, channels)
                seconds = ffprobe_duration(canonical)

                if cursor > 0:
                    gap_seconds = para_gap if l_idx == 0 else line_gap
                    gap_file = workdir / f"{index:03d}-gap.wav"
                    _silence(gap_seconds, gap_file, rate, channels)
                    pieces.append(gap_file)
                    cursor += gap_seconds

                pieces.append(canonical)
                timeline.append({
                    "index": index,
                    "paragraph": p_idx + 1,
                    "text": line,
                    "start": round(cursor, 3),
                    "end": round(cursor + seconds, 3),
                    "duration": round(seconds, 3),
                    "engine": info["engine"],
                    "voice": info["voice"],
                })
                cursor += seconds
                print(f"  [{index:3d}/{line_count}] {seconds:5.2f}s  {line[:34]}")

        if not pieces:
            raise ArkError("nothing was synthesized; the script produced no segments.")

        list_file = workdir / "concat.txt"
        list_file.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in pieces), encoding="utf-8")

        filters = []
        if out.get("normalize_loudness"):
            lufs = out.get("target_loudness_lufs", -16)
            filters.append(f"loudnorm=I={lufs}:TP=-1.5:LRA=11")
        extra: list[str] = []
        if fmt == "mp3":
            extra = ["-c:a", "libmp3lame", "-b:a", bitrate]
        elif fmt in ("m4a", "aac"):
            extra = ["-c:a", "aac", "-b:a", bitrate]
        elif fmt == "wav":
            extra = ["-c:a", "pcm_s16le"]
        else:
            extra = ["-b:a", bitrate]

        cmd = ["-y", "-f", "concat", "-safe", "0", "-i", str(list_file)]
        if filters:
            cmd += ["-af", ",".join(filters)]
        cmd += ["-ar", str(rate), *extra, str(out_path)]
        run_ffmpeg(cmd, "concat + encode")

        total = ffprobe_duration(out_path)
        sidecar = out_path.with_suffix(out_path.suffix + ".json")
        sidecar.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "config": str(config_path),
            "engine": engine,
            "voice": args.voice or settings.get("voice"),
            "audio": out_path.name,
            "duration_seconds": round(total, 3),
            "bytes": out_path.stat().st_size,
            "format": fmt,
            "gaps": {"line": line_gap, "paragraph": para_gap},
            "paragraphs": len(paragraphs),
            "lines": timeline,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\naudio   : {out_path}  ({out_path.stat().st_size // 1024} KB, {total:.2f}s)")
        print(f"timings : {sidecar}")

        if args.srt:
            srt_path = Path(args.srt).expanduser()
            srt_path.parent.mkdir(parents=True, exist_ok=True)
            blocks = []
            for item, entry in enumerate(timeline, start=1):
                blocks.append(
                    f"{item}\n{_srt_timestamp(entry['start'])} --> {_srt_timestamp(entry['end'])}\n"
                    f"{entry['text']}\n"
                )
            srt_path.write_text("\n".join(blocks), encoding="utf-8")
            print(f"subtitles: {srt_path}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


# --------------------------------------------------------------------------- cli


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="path to ark.config.json")
    parser.add_argument("--engine", choices=[EDGE_ENGINE, DOUBAO_ENGINE],
                        help="narration engine; defaults to narration.engine in the config")
    parser.add_argument("--voice", help="voice id, overriding the configured one")
    parser.add_argument("--text", help="text to speak")
    parser.add_argument("--name", help="label used in logs")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narration.py",
        description="Narration/TTS for the poetry-cinema-page skill (edge-tts or Doubao seed-tts).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    voices = sub.add_parser("voices", help="list the configured voice catalog")
    add_common(voices)

    probe = sub.add_parser("probe", help="check engines and credentials, then speak a short phrase")
    add_common(probe)
    probe.add_argument("--dry-run", action="store_true", help="report config only, synthesize nothing")
    probe.add_argument("--live", action="store_true", help="accepted for symmetry; probe already speaks")

    audition = sub.add_parser("audition", help="speak one sentence with many voices for A/B listening")
    add_common(audition)
    audition.add_argument("--voices", help="comma-separated voice ids; defaults to the whole catalog")
    audition.add_argument("--out-dir", help="where the samples and index.html go")

    say = sub.add_parser("say", help="synthesize one clip")
    add_common(say)
    say.add_argument("--out", required=True)

    build = sub.add_parser("build", help="build a full narration track from a script file")
    add_common(build)
    build.add_argument("--text-file", required=True,
                       help="narration script (.txt: '#' comments, blank line = paragraph "
                            "break) or a structured poem .json honouring narration.script")
    build.add_argument("--out", required=True)
    build.add_argument("--srt", help="also write an SRT subtitle file")
    build.add_argument("--include", help="which text layers to narrate from a .json source: "
                                         "a comma list of original, literal, analysis "
                                         "(overrides narration.script)")
    build.add_argument("--format", choices=["mp3", "m4a", "aac", "wav"], help="override output format")
    build.add_argument("--sample-rate", type=int)
    build.add_argument("--gap", type=float, help="pause between lines, seconds")
    build.add_argument("--paragraph-gap", type=float, help="pause between paragraphs, seconds")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config, config_path = load_config(args.config)
        config["_config_path"] = str(config_path)
        if not getattr(args, "text", None) and args.command in ("probe", "audition"):
            args.text = "君不见，黄河之水天上来，奔流到海不复回。" if args.command == "audition" else "测试"
        if args.command == "say" and not args.text:
            raise ArkError("`say` requires --text.")
        handler = {
            "voices": command_voices,
            "probe": command_probe,
            "audition": command_audition,
            "say": command_say,
            "build": command_build,
        }[args.command]
        return handler(args, config, config_path)
    except ArkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
