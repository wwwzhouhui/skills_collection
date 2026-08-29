from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def read_transcript_text(path: str | Path | None = None, inline_text: str | None = None) -> str:
    if inline_text:
        return inline_text.strip()
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    if p.suffix.lower() not in {".json", ".jsonl"}:
        return p.read_text(encoding="utf-8", errors="ignore").strip()
    try:
        data = load_transcript_data(p)
    except Exception:
        return p.read_text(encoding="utf-8", errors="ignore").strip()
    return transcript_data_to_text(data)


def load_transcript_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in text.splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
    return json.loads(text)


def transcript_data_to_text(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        parts = []
        for item in data:
            if isinstance(item, dict):
                parts.append(format_segment(item))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p)
    if not isinstance(data, dict):
        return str(data)
    for key in ("segments", "utterances", "results", "words"):
        value = data.get(key)
        if isinstance(value, list):
            return transcript_data_to_text(value)
    if data.get("text"):
        return str(data["text"])
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_segment(seg: dict[str, Any]) -> str:
    text = str(seg.get("text") or seg.get("word") or seg.get("content") or "").strip()
    start = first_present(seg, ["start", "start_time", "start_seconds", "begin"])
    end = first_present(seg, ["end", "end_time", "end_seconds", "finish"])
    speaker = seg.get("speaker") or seg.get("speaker_id")
    prefix = ""
    if start is not None or end is not None:
        prefix += f"[{fmt_time(start)}-{fmt_time(end)}]"
    if speaker:
        prefix += f"[{speaker}]"
    if prefix:
        return f"{prefix} {text}".strip()
    return text


def first_present(seg: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in seg and seg[key] is not None:
            return seg[key]
    return None


def fmt_time(value: Any) -> str:
    if value is None:
        return "?"
    try:
        parsed = float(value)
    except Exception:
        return str(value)
    return f"{parsed:.2f}s" if math.isfinite(parsed) else "?"


def transcript_text_for_range(path: str | Path | None, start_time: float, end_time: float) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.is_file():
        return ""
    if p.suffix.lower() not in {".json", ".jsonl"}:
        return p.read_text(encoding="utf-8", errors="ignore").strip()
    try:
        data = load_transcript_data(p)
    except Exception:
        return p.read_text(encoding="utf-8", errors="ignore").strip()

    segments = collect_segments(data)
    if not segments:
        return transcript_data_to_text(data)
    selected = []
    any_timestamped = False
    for seg in segments:
        raw_start = first_present(seg, ["start", "start_time", "start_seconds", "begin"])
        raw_end = first_present(seg, ["end", "end_time", "end_seconds", "finish"])
        start = coerce_float(raw_start)
        end = coerce_float(raw_end)
        if (raw_start is not None and start is None) or (raw_end is not None and end is None):
            continue
        if start is None and end is None:
            continue
        any_timestamped = True
        if end is None:
            end = start
        if start is None:
            start = end
        if segment_overlaps_range(start, end, start_time, end_time):
            selected.append(format_segment(seg))
    joined = "\n".join(s for s in selected if s)
    if joined:
        return joined
    if not any_timestamped:
        # 分段全部没有可用时间戳: 这是"无法做 range 过滤", 不是"窗口内无语音"。
        # 返回空串让调用方走全量转录回退 — 返回静音标记会把整份转录静默丢弃
        # 并对每个窗口错误断言无语音。
        return ""
    # Timestamped transcript with no speech in this window. Must NOT be the
    # empty string: callers treat "" as "range filtering unavailable" and fall
    # back to inlining the FULL transcript labeled as matching this window —
    # a false pairing that corrupts cut decisions on silent segments.
    return "(no transcript segments within this time window)"


def segment_overlaps_range(seg_start: float, seg_end: float, range_start: float, range_end: float) -> bool:
    if seg_end > seg_start:
        return max(seg_start, range_start) < min(seg_end, range_end)
    return range_start <= seg_start < range_end


def collect_segments(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("segments", "utterances", "results", "words"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed if math.isfinite(parsed) else None
