#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_common import serve
from ve_tools import (
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
from ve_tools.run_context import RunContext
from ve_tools.schemas import TOOL_SCHEMAS


def main() -> None:
    ctx = RunContext(session_kind="mcp")
    impls = {
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
    serve("video-agent-kit", TOOL_SCHEMAS, impls, ctx)


if __name__ == "__main__":
    main()
