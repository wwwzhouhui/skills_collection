#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
MCP_ROOT = PLUGIN_ROOT / "mcp"
sys.path.insert(0, str(MCP_ROOT))

from ve_tools import (  # noqa: E402
    arrange,
    basic_ops,
    condense,
    diarize,
    frame_zoom,
    lol,
    media,
    narrate_tts,
    narration_bind,
    qc,
    render,
    render_narrated,
    shots,
    soccer,
    subtitle,
    subtitle_scout,
    timeline,
    tts,
    video_observe,
)
from ve_tools.run_context import RunContext  # noqa: E402


TOOLS = {
    "inspect_media": media.inspect_media,
    "analyze_media": media.analyze_media,
    "speech_transcribe": media.speech_transcribe,
    "transcribe": media.transcribe,
    "video_ingest": video_observe.video_ingest,
    "video_watch_segment": video_observe.video_watch_segment,
    "video_basic_operation": basic_ops.video_basic_operation,
    "speech_synthesize": tts.speech_synthesize,
    "tts_generate": tts.tts_generate,
    "subtitle_scout": subtitle_scout.subtitle_scout,
    "subtitle_build": subtitle.subtitle_build,
    "subtitle_render": subtitle.subtitle_render,
    "subtitle_qc": subtitle.subtitle_qc,
    "condense_index": condense.condense_index,
    "condense_plan": condense.condense_plan,
    "condense_render": condense.condense_render,
    "condense_qc": condense.condense_qc,
    "diarize_audit": diarize.diarize_audit,
    "diarize_relabel": diarize.diarize_relabel,
    "video_read_frames": frame_zoom.video_read_frames,
    "validate_timeline": timeline.validate_timeline,
    "render_preview": render.render_preview,
    "qc_preview": qc.qc_preview,
    "timeline_diff": timeline.timeline_diff,
    "detect_shots": shots.detect_shots,
    "arrange_footage": arrange.arrange_footage,
    "synthesize_narration": narrate_tts.synthesize_narration,
    "bind_narration": narration_bind.bind_narration,
    "render_narrated": render_narrated.render_narrated,
    "soccer_ingest": soccer.soccer_ingest,
    "soccer_arrange": soccer.soccer_arrange,
    "soccer_tts": soccer.soccer_tts,
    "soccer_render": soccer.soccer_render,
    "lol_ingest": lol.lol_ingest,
    "lol_arrange": lol.lol_arrange,
    "lol_tts": lol.lol_tts,
    "lol_render": lol.lol_render,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run video-agent-kit tools without starting the MCP server.")
    parser.add_argument("tool", choices=sorted(TOOLS))
    parser.add_argument("--args-json", help="JSON object passed directly to the tool.")
    parser.add_argument("--args-file", help="Path to a JSON file containing tool arguments.")
    parser.add_argument("--project-dir", help="Project directory used for relative paths and outputs.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the structured result.")
    known, unknown = parser.parse_known_args()

    if known.project_dir:
        import os

        resolved = str(Path(known.project_dir).resolve())
        # run_context.project_dir() 的优先级是 CLAUDE_PROJECT_DIR > VE_PROJECT_DIR;
        # 在 Claude Code 会话里前者总是被导出, 只写后者会让 --project-dir 被静默忽略
        os.environ["CLAUDE_PROJECT_DIR"] = resolved
        os.environ["VE_PROJECT_DIR"] = resolved

    args = load_args(known.args_json, known.args_file)
    args.update(parse_unknown_flags(unknown))
    result = TOOLS[known.tool](args, RunContext())
    payload = {
        "text": result.text,
        "data": result.data,
        "artifacts": result.artifacts,
        "image_paths": result.image_paths,
        "video_paths": result.video_paths,
    }
    if known.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def load_args(args_json: str | None, args_file: str | None) -> dict:
    if args_json and args_file:
        raise SystemExit("Use --args-json or --args-file, not both.")
    if args_file:
        try:
            value = json.loads(Path(args_file).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--args-file must contain valid JSON: {exc}") from None
        return require_json_object(value, "--args-file")
    if args_json:
        try:
            value = json.loads(args_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--args-json must be valid JSON: {exc}") from None
        return require_json_object(value, "--args-json")
    return {}


def require_json_object(value: object, source: str) -> dict:
    if not isinstance(value, dict):
        raise SystemExit(f"{source} must contain a JSON object.")
    return value


# Flags whose values are always strings (paths, free text); never type-coerced
# so inputs like --video-path 002 keep their literal spelling.
STRING_FLAG_SUFFIXES = ("path", "dir", "file", "json", "text", "prompt")

CANONICAL_INT_RE = re.compile(r"-?(?:0|[1-9]\d*)")
CANONICAL_FLOAT_RE = re.compile(r"-?(?:0|[1-9]\d*)\.\d+")


def parse_unknown_flags(items: list[str]) -> dict:
    parsed: dict[str, object] = {}
    idx = 0
    while idx < len(items):
        key = items[idx]
        if not key.startswith("--"):
            raise SystemExit(f"Unexpected argument: {key}")
        body = key[2:]
        if "=" in body:
            # --flag=value 形式: 不拆开会被解析成布尔键 "flag=value", 参数静默丢失
            name, raw = body.split("=", 1)
            name = name.replace("-", "_")
            parsed[name] = raw if name.endswith(STRING_FLAG_SUFFIXES) else coerce_value(raw)
            idx += 1
            continue
        name = body.replace("-", "_")
        if idx + 1 >= len(items) or items[idx + 1].startswith("--"):
            parsed[name] = True
            idx += 1
            continue
        raw = items[idx + 1]
        parsed[name] = raw if name.endswith(STRING_FLAG_SUFFIXES) else coerce_value(raw)
        idx += 2
    return parsed


def coerce_value(value: str) -> object:
    if value in {"true", "false"}:
        return value == "true"
    stripped = value.strip()
    if stripped.startswith(("{", "[")) or stripped == "null":
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    # Only coerce canonical numeric spellings so values like "002" survive as
    # strings instead of collapsing to 2.
    if CANONICAL_INT_RE.fullmatch(value):
        return int(value)
    if CANONICAL_FLOAT_RE.fullmatch(value):
        return float(value)
    return value


if __name__ == "__main__":
    main()
