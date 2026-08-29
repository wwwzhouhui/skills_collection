"""cloud_asr: 直连 HTTP 语音识别的兼容 provider（legacy escape hatch）。

**这不是默认通道。** 默认走 ``zcode_speech``（宿主注入身份、无需任何 key）；配置了
``VE_SPEECH_MCP_URL`` 时走远端 Speech MCP。本模块只服务于既不在 ZCode 宿主里、也没有
远端 MCP 可用，却已自备一套直连 HTTP 识别服务的部署。

因此本模块**没有内置服务地址、也没有内置资源标识**：端点、资源 ID、鉴权全部由部署方
显式注入，缺一项即视为该通道不可用（见 ``cloud_asr_status``）。端点只从**进程环境**读
（``check_endpoint``），项目级 ``.env`` 不可信：若它能指定端点，仓库里的一个 .env 就能
把带着 API key 的请求导向攻击者主机。

协议形状（异步 submit/query，data 直传被拒时回退同步 flash 接口）沿用既有部署的约定：
音频以 base64 直传，因为本插件的输入是容器内本地文件，没有公网 URL。

配置（仅进程环境，见 .env.example）:
  VE_SPEECH_ASR_ENDPOINT        直连端点，必填；https（loopback 可 http）
  VE_SPEECH_ASR_RESOURCE_ID     异步接口资源标识，必填
  VE_SPEECH_ASR_FLASH_RESOURCE_ID  同步 flash 回退资源标识，可选
  VE_SPEECH_ASR_API_KEY         单 key 鉴权 (X-Api-Key)；与下面两项二选一
  VE_SPEECH_ASR_APP_KEY         APP ID  (X-Api-App-Key)
  VE_SPEECH_ASR_ACCESS_KEY      Access Token (X-Api-Access-Key)

输出统一为插件 transcript.json 口径: 毫秒时间戳归一到秒, utterances →
segments (speaker 从 additions 里尽力提取), words 展平。
"""
from __future__ import annotations

import base64
import json
import math
import shutil
from .ffproc import run_proc
import time
import uuid
from pathlib import Path
from typing import Any

from .result import ToolResult
from .run_context import clean_env, check_endpoint

SUBMIT_PATH = "/api/v3/auc/bigmodel/submit"
QUERY_PATH = "/api/v3/auc/bigmodel/query"
FLASH_PATH = "/api/v3/auc/bigmodel/recognize/flash"

STATUS_OK = "20000000"
STATUS_PROCESSING = {"20000001", "20000002"}       # 处理中 / 排队中
STATUS_SILENT = "20000003"                          # 静音音频 (无人声)
STATUS_INVALID = "45000001"                         # 参数无效 (data 直传被拒时触发回退)

# 提交的音频统一转成 16k 单声道 mp3 (接口支持 raw/wav/mp3/ogg; m4a 不在列)。
ASR_AUDIO_BITRATE = "64k"
ASR_SAMPLE_RATE = "16000"
# 只有 mp3 原样透传: wav 可能是 24bit/float (接口仅支持 16bit), ogg 可能是
# vorbis (接口只认 ogg opus), 透传会被拒 — 统一重编码更稳。
ASR_PASSTHROUGH_SUFFIXES = {".mp3"}
ASR_PASSTHROUGH_MAX_BYTES = 40 * 1024 * 1024
# 接口单文件上限按同步 flash 的 100MB / 异步的 512MB 取中; base64 后 ~4/3 倍,
# 超过就别硬塞了。
ASR_MAX_AUDIO_BYTES = 200 * 1024 * 1024

# 短语言码 → 接口 locale。zh/auto 不传 (默认支持中英与多方言, 且
# enable_speaker_info 要求 language 为空或 zh-CN)。带 "-" 的值原样透传。
ASR_LANGUAGE_MAP = {"en": "en-US", "ja": "ja-JP", "ko": "ko-KR", "yue": "yue-CN"}


def cloud_asr_config() -> dict[str, Any]:
    api_key = clean_env("VE_SPEECH_ASR_API_KEY", "VE_CLOUD_ASR_API_KEY")
    app_key = clean_env("VE_SPEECH_ASR_APP_KEY", "VE_CLOUD_ASR_APP_KEY")
    access_key = clean_env("VE_SPEECH_ASR_ACCESS_KEY", "VE_CLOUD_ASR_ACCESS_KEY")
    endpoint, endpoint_error = check_endpoint(
        "VE_SPEECH_ASR_ENDPOINT", "VE_CLOUD_ASR_ENDPOINT",
    )
    return {
        "api_key": api_key,
        "app_key": app_key,
        "access_key": access_key,
        "endpoint": endpoint,
        "endpoint_error": endpoint_error,
        "resource_id": clean_env("VE_SPEECH_ASR_RESOURCE_ID", "VE_CLOUD_ASR_RESOURCE_ID"),
        "flash_resource_id": clean_env(
            "VE_SPEECH_ASR_FLASH_RESOURCE_ID", "VE_CLOUD_ASR_FLASH_RESOURCE_ID",
        ),
    }


def cloud_asr_status() -> dict[str, Any]:
    """Availability probe for the direct-HTTP compatibility backend, shaped like
    {available, reasons, ...} so provider selection can treat every channel alike.

    Not being configured is the normal case, not a defect: under ZCode the
    official channel needs no local configuration at all.
    """
    cfg = cloud_asr_config()
    reasons: list[str] = []
    if cfg.get("endpoint_error"):
        reasons.append(cfg["endpoint_error"])
    if not cfg["resource_id"]:
        reasons.append("VE_SPEECH_ASR_RESOURCE_ID is not set")
    if not (cfg["api_key"] or (cfg["app_key"] and cfg["access_key"])):
        reasons.append(
            "credentials not set (need VE_SPEECH_ASR_API_KEY, or "
            "VE_SPEECH_ASR_APP_KEY + VE_SPEECH_ASR_ACCESS_KEY)"
        )
    try:
        import requests  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"requests package unavailable: {exc}")
    return {
        "available": not reasons,
        "reasons": reasons,
        "auth_mode": "api_key" if cfg["api_key"] else "app_key+access_key",
        "resource_id": cfg["resource_id"],
        "endpoint": cfg["endpoint"],
    }


def _headers(cfg: dict[str, Any], request_id: str, resource_id: str, *, submit: bool) -> dict[str, str]:
    headers: dict[str, str] = {
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "Content-Type": "application/json",
    }
    if cfg["api_key"]:
        headers["X-Api-Key"] = cfg["api_key"]          # 单 key 鉴权
    else:
        headers["X-Api-App-Key"] = cfg["app_key"]      # APP ID + Access Token 鉴权
        headers["X-Api-Access-Key"] = cfg["access_key"]
    if submit:
        headers["X-Api-Sequence"] = "-1"
    return headers


def _api_status(resp) -> tuple[str, str, str]:
    """(status_code, message, logid) from the speech service response headers."""
    return (
        str(resp.headers.get("X-Api-Status-Code") or ""),
        str(resp.headers.get("X-Api-Message") or ""),
        str(resp.headers.get("X-Tt-Logid") or ""),
    )


def _language_field(language: str) -> str | None:
    lang = (language or "").strip()
    if not lang or lang.lower() in {"zh", "auto"}:
        return None
    if "-" in lang:
        return lang
    return ASR_LANGUAGE_MAP.get(lang.lower(), lang)


def _request_body(audio_b64: str, audio_format: str, language: str) -> dict[str, Any]:
    audio: dict[str, Any] = {"data": audio_b64, "format": audio_format}
    lang = _language_field(language)
    if lang:
        audio["language"] = lang
    return {
        "user": {"uid": "video-agent-kit"},
        "audio": audio,
        "request": {
            "model_name": "bigmodel",
            "enable_itn": True,
            "enable_punc": True,
            "show_utterances": True,
            # 说话人聚类分离 (10 人以内效果较好); 要求 language 为空或 zh-CN
            "enable_speaker_info": lang is None or lang == "zh-CN",
        },
    }


def speaker_info_enabled(language: str) -> bool:
    """Whether this language argument leaves speaker clustering enabled."""
    lang = _language_field(language)
    return lang is None or lang == "zh-CN"


_CJK_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF))


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _CJK_RANGES)


def _cjk_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha() or _is_cjk(ch)]
    if not letters:
        return 0.0
    return sum(1 for ch in letters if _is_cjk(ch)) / len(letters)


def language_sanity_warning(language: str, text: str, has_speaker_labels: bool) -> str | None:
    """Warn when the language hint likely disabled speaker labels for Chinese speech."""
    lang = (language or "").strip().lower()
    enabled = speaker_info_enabled(language)
    ratio = _cjk_ratio(text)
    if ratio >= 0.3 and lang not in ("", "zh", "auto", "zh-cn"):
        note = (
            f"language={language!r} was passed but {ratio:.0%} of the returned text is Chinese. "
            "Speaker diarization only runs when language is empty, 'zh' or 'auto' "
            f"(speaker diarization was {'enabled' if enabled else 'disabled'} for this call), and a wrong "
            "language can also degrade segmentation and punctuation."
        )
        if not has_speaker_labels:
            note += (
                " This transcript has no speaker labels. If the piece has more than one speaker, rerun "
                "speech_transcribe with language='zh' or omit the language before downstream speaker decisions."
            )
        return note
    if not has_speaker_labels and not enabled:
        return (
            f"language={language!r} disabled speaker diarization, so this transcript has no speaker labels. "
            "Rerun with language='zh' or omit the language if speaker identity matters."
        )
    return None


def prepare_asr_audio(
    input_path: Path,
    work_dir: Path,
    *,
    allow_passthrough: bool = True,
) -> tuple[Path, str, str] | ToolResult:
    """(audio_path, format, source_kind)。非受支持格式/大文件统一抽成 16k 单声道 mp3。

    ``allow_passthrough=False`` 强制重编码。zcode_speech 需要它：原样透传一个高码率 mp3
    体积不可预测，容易撞上官方 MCP 的请求体上限，而重编码后的 16k/64kbps 是可预测的 8 KB/s。
    """
    suffix = input_path.suffix.lower()
    if (
        allow_passthrough
        and suffix in ASR_PASSTHROUGH_SUFFIXES
        and input_path.stat().st_size <= ASR_PASSTHROUGH_MAX_BYTES
    ):
        return input_path, suffix.lstrip("."), "original_audio"
    if not shutil.which("ffmpeg"):
        return ToolResult(text="[ERROR] ffmpeg not found on PATH; required to extract ASR audio")
    output = work_dir / f"{input_path.stem}.asr.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", ASR_SAMPLE_RATE,
        "-b:a", ASR_AUDIO_BITRATE,
        str(output),
    ]
    proc = run_proc(cmd, capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
        detail = (proc.stderr or proc.stdout or "").strip()[-1200:]
        return ToolResult(
            text="[ERROR] failed to extract ASR audio",
            data={"cmd": cmd, "detail": detail},
        )
    return output, "mp3", "extracted_audio"


def cloud_asr_transcribe_payload(
    input_path: Path,
    work_dir: Path,
    *,
    language: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
    started: float,
) -> tuple[dict[str, Any], Path] | ToolResult:
    status = cloud_asr_status()
    if not status["available"]:
        return ToolResult(
            text="[ERROR] cloud_asr is not available: " + "; ".join(status["reasons"]),
            data={"recoverable": True, "provider": "cloud_asr", "status": status},
        )
    prepared = prepare_asr_audio(input_path, work_dir)
    if isinstance(prepared, ToolResult):
        return prepared
    asr_source, audio_format, source_kind = prepared
    audio_bytes = asr_source.stat().st_size
    if audio_bytes > ASR_MAX_AUDIO_BYTES:
        return ToolResult(
            text=(
                f"[ERROR] cloud_asr audio too large ({audio_bytes / 2**20:.0f} MiB > "
                f"{ASR_MAX_AUDIO_BYTES / 2**20:.0f} MiB); split the source media first"
            ),
            data={"provider": "cloud_asr", "recoverable": False, "asr_audio": str(asr_source)},
        )

    cfg = cloud_asr_config()
    if cfg.get("endpoint_error"):
        return ToolResult(
            text=f"[ERROR] cloud_asr transcription blocked: {cfg['endpoint_error']}",
            data={"provider": "cloud_asr", "recoverable": False},
        )
    audio_b64 = base64.b64encode(asr_source.read_bytes()).decode("ascii")
    body = _request_body(audio_b64, audio_format, language)
    try:
        result, meta = _run_recognition(
            cfg, body,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
    except CloudASRError as exc:
        return ToolResult(
            text=f"[ERROR] cloud_asr transcription failed: {exc}",
            data={"provider": "cloud_asr", "recoverable": True, **exc.detail},
        )
    except Exception as exc:  # noqa: BLE001 — 网络层等意外错误统一可重试
        return ToolResult(
            text=f"[ERROR] cloud_asr transcription failed: {exc}",
            data={"provider": "cloud_asr", "recoverable": True},
        )
    payload = asr_result_to_transcript_json(
        result,
        source_media=input_path,
        asr_audio=asr_source,
        language=language,
        source_kind=source_kind,
        elapsed_seconds=round(time.time() - started, 3),
        meta=meta,
    )
    return payload, asr_source


class CloudASRError(RuntimeError):
    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.detail = detail or {}


def _run_recognition(
    cfg: dict[str, Any],
    body: dict[str, Any],
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """异步 submit/query, data 直传被拒时回退同步 flash。返回 (result_body, meta)。"""
    import requests

    request_id = str(uuid.uuid4())
    meta: dict[str, Any] = {
        "request_id": request_id,
        "resource_id": cfg["resource_id"],
        "interface": "submit_query",
    }
    resp = requests.post(
        cfg["endpoint"] + SUBMIT_PATH,
        headers=_headers(cfg, request_id, cfg["resource_id"], submit=True),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        # submit (含 base64 整包上传) 也受调用方 timeout_seconds 约束, 600s 只是上限
        timeout=min(600.0, max(30.0, timeout_seconds)),
    )
    code, message, logid = _api_status(resp)
    meta["submit_logid"] = logid
    if code == STATUS_INVALID:
        # 异步接口可能只收 audio.url: 回退到明确支持 base64 的同步 flash 接口。
        # 注意这会退到 flash 资源对应的模型, 结果里标注。
        if not cfg.get("flash_resource_id"):
            raise CloudASRError(
                f"submit rejected inline audio: {code} {message} (logid {logid}); "
                "set VE_SPEECH_ASR_FLASH_RESOURCE_ID to enable the synchronous fallback",
                {"status_code": code, "logid": logid},
            )
        return _run_flash(cfg, body, meta_note={
            "fallback_from": cfg["resource_id"],
            "fallback_reason": f"submit rejected base64 data: {code} {message} (logid {logid})",
        }, timeout_seconds=timeout_seconds)
    if code != STATUS_OK:
        raise CloudASRError(
            f"submit failed: {code} {message} (logid {logid})",
            {"status_code": code, "logid": logid},
        )

    deadline = time.time() + timeout_seconds
    query_headers = _headers(cfg, request_id, cfg["resource_id"], submit=False)
    while True:
        resp = requests.post(
            cfg["endpoint"] + QUERY_PATH, headers=query_headers, data=b"{}", timeout=120,
        )
        code, message, logid = _api_status(resp)
        if code == STATUS_OK:
            meta["query_logid"] = logid
            try:
                return resp.json() or {}, meta
            except ValueError as exc:
                raise CloudASRError(f"query returned non-JSON body: {exc}", {"logid": logid}) from exc
        if code == STATUS_SILENT:
            meta["query_logid"] = logid
            meta["silent_audio"] = True
            return {}, meta
        if code not in STATUS_PROCESSING:
            # 服务端把 55xxxxxx 归为"服务端错误, 可稍后重试" (如 55000031 服务器
            # 繁忙); 5xx 无状态头时 code 为空串。任务已 submit 成功, 轮询中一次
            # 瞬时错误不该废弃整个任务 — deadline 内继续重试, 持续失败由超时
            # 分支收尾 (超时消息带最后一次 code)。
            transient = (not code) or str(code).startswith("55")
            if not transient:
                raise CloudASRError(
                    f"query failed: {code} {message} (logid {logid})",
                    {"status_code": code, "logid": logid},
                )
            errors = meta.setdefault("transient_query_errors", [])
            errors.append(f"{code} {message} (logid {logid})")
            del errors[:-5]
        if time.time() >= deadline:
            raise CloudASRError(
                f"transcription timed out after {timeout_seconds:g}s (last status {code})",
                {"status_code": code, "logid": logid},
            )
        time.sleep(poll_interval_seconds)


def _run_flash(
    cfg: dict[str, Any],
    body: dict[str, Any],
    *,
    meta_note: dict[str, Any],
    timeout_seconds: float = 1800.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    import requests

    request_id = str(uuid.uuid4())
    meta: dict[str, Any] = {
        "request_id": request_id,
        "resource_id": cfg["flash_resource_id"],
        "interface": "flash",
        **meta_note,
    }
    resp = requests.post(
        cfg["endpoint"] + FLASH_PATH,
        headers=_headers(cfg, request_id, cfg["flash_resource_id"], submit=True),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        # flash 同步接口 (上传+识别一次完成) 同样受调用方 timeout_seconds 约束
        timeout=min(1800.0, max(30.0, timeout_seconds)),
    )
    code, message, logid = _api_status(resp)
    meta["flash_logid"] = logid
    if code == STATUS_SILENT:
        meta["silent_audio"] = True
        return {}, meta
    if code != STATUS_OK:
        # 回退语境必须带出来: 触发回退的原始 submit 拒绝才是根因, 只报 flash 侧
        # 错误 (如资源未开通) 会误导排障方向
        raise CloudASRError(
            f"flash recognize failed: {code} {message} (logid {logid})",
            {"status_code": code, "logid": logid, **meta_note},
        )
    try:
        return resp.json() or {}, meta
    except ValueError as exc:
        raise CloudASRError(f"flash returned non-JSON body: {exc}", {"logid": logid}) from exc


def _ms_to_seconds(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(parsed) or parsed < 0:
        return 0.0
    return round(parsed / 1000.0, 3)


def _utterance_speaker(item: dict[str, Any]) -> str:
    """说话人字段在文档里没定死: 逐个候选位置尽力取 (additions.speaker 为主)。"""
    additions = item.get("additions") if isinstance(item.get("additions"), dict) else {}
    for value in (
        item.get("speaker"),
        additions.get("speaker"),
        additions.get("speaker_id"),
        additions.get("channel_id"),
        item.get("channel_id"),
    ):
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _normalize_word(item: dict[str, Any], speaker: str) -> dict[str, Any]:
    return {
        "text": str(item.get("text") or "").strip(),
        "start": _ms_to_seconds(item.get("start_time")),
        "end": _ms_to_seconds(item.get("end_time")),
        "speaker": speaker or None,
    }


def asr_result_to_transcript_json(
    payload: dict[str, Any],
    *,
    source_media: Path,
    asr_audio: Path,
    language: str,
    source_kind: str,
    elapsed_seconds: float,
    meta: dict[str, Any],
) -> dict[str, Any]:
    result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    utterances_raw = result.get("utterances") if isinstance(result.get("utterances"), list) else []
    segments: list[dict[str, Any]] = []
    words: list[dict[str, Any]] = []
    for item in utterances_raw:
        if not isinstance(item, dict):
            continue
        speaker = _utterance_speaker(item)
        seg_words = [
            _normalize_word(word, speaker)
            for word in (item.get("words") or [])
            if isinstance(word, dict)
        ]
        seg_words = [word for word in seg_words if word["text"]]
        segment = {
            "speaker": speaker,
            "text": str(item.get("text") or "").strip(),
            "start": _ms_to_seconds(item.get("start_time")),
            "end": _ms_to_seconds(item.get("end_time")),
            "words": seg_words,
        }
        if segment["text"] or seg_words:
            segments.append(segment)
            words.extend(seg_words)
    text = str(result.get("text") or "").strip()
    if not text and segments:
        text = "\n".join(seg["text"] for seg in segments if seg["text"]).strip()
    audio_info = payload.get("audio_info") if isinstance(payload.get("audio_info"), dict) else {}
    out: dict[str, Any] = {
        "provider": "cloud_asr",
        "request_id": meta.get("request_id"),
        "resource_id": meta.get("resource_id"),
        "interface": meta.get("interface"),
        "language": language,
        "speaker_labels": any(seg.get("speaker") for seg in segments),
        "source_media": str(source_media),
        "asr_audio": str(asr_audio),
        "source_kind": source_kind,
        "text": text,
        "words": words,
        "segments": segments,
        "elapsed_seconds": elapsed_seconds,
        "time_unit": "seconds",
    }
    if audio_info.get("duration") is not None:
        out["audio_duration_seconds"] = _ms_to_seconds(audio_info.get("duration"))
    if meta.get("silent_audio"):
        out["silent_audio"] = True
        out["note"] = "cloud_asr reported silent audio (no speech detected); empty transcript is valid"
    warning = language_sanity_warning(language, text, bool(out["speaker_labels"]))
    if warning:
        out["warnings"] = [warning]
        out["note"] = (out.get("note") + " " if out.get("note") else "") + warning
    if meta.get("fallback_from"):
        out["fallback_from"] = meta["fallback_from"]
        out["fallback_reason"] = meta["fallback_reason"]
    return out
