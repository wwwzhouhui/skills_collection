from __future__ import annotations

import re


TOOL_SCHEMAS: dict[str, dict] = {
    "inspect_media": {
        "description": "Inspect a video or audio file with ffprobe and return structured media metadata plus a concise summary and technical risk list. Duration prefers format duration, falls back to stream duration, and ignores NaN/Infinity values. The summary includes duration, dimensions, fps, codecs, audio layout, pixel/color metadata, and rotation when available; risks flag no-audio/no-video, odd dimensions, possible VFR, HDR transfer metadata, and large-source cost.",
        "inputSchema": {
            "type": "object",
            "required": ["input_path"],
            "properties": {
                "input_path": {"type": "string"},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "analyze_media": {
        "description": "Run lightweight deterministic planning analysis on a source video/audio file using FFmpeg/ffprobe. It detects scene-change timestamps, derives scene-boundary candidate segments, scans black ranges and silence ranges, and writes a JSON report. These are planning hints only; verify candidate segments with video_ingest/video_watch_segment before final timeline decisions.",
        "inputSchema": {
            "type": "object",
            "required": ["input_path"],
            "properties": {
                "input_path": {"type": "string"},
                "output_json": {"type": "string"},
                "scene_threshold": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "exclusiveMaximum": 1,
                    "default": 0.3
                }
            },
            "additionalProperties": False
        }
    },
    "transcribe": {
        "description": "Compatibility alias for speech_transcribe. Create transcript.json for a video/audio file through the configured cloud ASR capability. Transient network/concurrency/rate-limit/server errors retry by default (retries=3 extra attempts, retry_backoff_seconds=30), but deterministic configuration/input failures do not retry. Long media over about 30 minutes is automatically split into overlapping chunks of at most chunk_seconds (default 1700s), transcribed with per-chunk caching, then merged back onto the source timeline. Millisecond timestamps are normalized to seconds. A silent-audio result (no speech) is a valid empty transcript, flagged silent_audio=true. In one MCP session, transcribing an input media file remembers that transcript for the same media fingerprint without marking any video as visually ingested; it updates the active transcript only when the input media fingerprint matches the current active video. Downstream transcript readers support plain text, JSON, and standard JSONL, and range filtering ignores NaN/Infinity timestamps.",
        "inputSchema": {
            "type": "object",
            "required": ["input_path"],
            "properties": {
                "input_path": {"type": "string"},
                "output_json": {"type": "string"},
                "provider": {
                    "type": "string",
                    "enum": ["auto", "cloud", "cloud_asr"],
                    "default": "auto",
                    "description": "ASR provider. Use auto unless a workflow explicitly requires cloud_asr."
                },
                "language": {"type": "string", "default": "zh"},
                "chunk_seconds": {
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "description": "Maximum seconds per chunk for long media before merge (default 1700)."
                },
                "timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
                "poll_interval_seconds": {"type": "number", "exclusiveMinimum": 0},
                "retries": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Extra retry attempts for transient ASR failures such as concurrency/rate-limit/network/server errors."
                },
                "retry_count": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Alias for retries."
                },
                "retry_backoff_seconds": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Initial exponential backoff before ASR retries (default 30)."
                },
                "work_dir": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "video_ingest": {
        "description": "Sample the complete video into timestamped contact-sheet images and return them as MCP image content for the Claude Code main model to inspect directly. Standard flow: run transcribe first and pass its output as transcript_path, so every contact sheet is paired with matching speech text; omit transcript arguments only when transcribe reported that cloud ASR is unavailable (a transcript-less ingest while ASR is available gets a reminder in the result). Call this once before planning any video edit, and call it again if the video file at that path is overwritten or replaced. Explicit transcript_path must exist. In an MCP session, re-ingesting a video without transcript arguments reuses the transcript previously remembered for that same video fingerprint when available. Full-ingest session state is recorded only after the observation package is successfully produced; failed sampling does not count as full-video visual evidence. The tool is idempotent for the same video/prompt/transcript/settings, preserves every sampled visual observation without blank/near-duplicate folding, and always includes the matching transcript when provided. If the result lists non-inlined image paths, read them before making visual decisions. This tool does not call any model API.",
        "inputSchema": {
            "type": "object",
            "required": ["video_path"],
            "properties": {
                "video_path": {"type": "string"},
                "transcript_path": {"type": "string"},
                "transcript_text": {"type": "string"},
                "prompt": {"type": "string"},
                "output_json": {"type": "string"},
                "save_frames_dir": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "video_watch_segment": {
        "description": "Sample one or more local video segments at higher FPS and return timestamped contact-sheet images for the Claude Code main model to inspect directly. Provide either start_time+end_time for one window, or segments=[{start,end}, ...] for a batch, plus fps (required); passing neither is a tool error, and when segments is provided it takes precedence over start_time/end_time. Pass video_path to watch any existing video directly; a prior full video_ingest is not required for explicit video_path calls. If video_path is omitted, the tool uses the current active video from the session; if that active file has been overwritten or replaced since it was last observed, implicit segment watch returns an error. Explicit transcript_path must exist. Passing a video_path without transcript arguments reuses the transcript previously remembered for that same video fingerprint when available instead of clearing it. Start/end values must be numeric. Windows that clearly exceed source duration return an error instead of being silently shortened. The tool tracks already-watched windows per (start, end, fps): only a same-times same-fps request is skipped with status=skipped_duplicate and no new sheets, so rewatching the same window at a different fps is a new observation; pass force=true to bypass the duplicate skip entirely. Overlapping windows produce warnings but are kept. Matching transcript is attached automatically. Active-video session state is updated only after new contact sheets are successfully produced; failed or skipped-duplicate watches do not count as new visual evidence, and partial failures are flagged with a leading [ERROR] summary. If the result lists non-inlined image paths, read them before making visual decisions. This tool does not call any model API.",
        "inputSchema": {
            "type": "object",
            "required": ["fps"],
            "properties": {
                "start_time": {"type": "number", "minimum": 0},
                "end_time": {"type": "number", "minimum": 0},
                "video_path": {"type": "string"},
                "transcript_path": {"type": "string"},
                "transcript_text": {"type": "string"},
                "segments": {
                    "type": "array",
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "required": ["start", "end"],
                        "properties": {
                            "start": {"type": "number", "minimum": 0},
                            "end": {"type": "number", "minimum": 0}
                        },
                        "additionalProperties": False
                    }
                },
                "fps": {"type": "number", "minimum": 0.1},
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Bypass the watched-window duplicate skip and rewatch the requested windows."
                },
                "prompt": {"type": "string"},
                "output_json": {"type": "string"},
                "save_frames_dir": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "video_basic_operation": {
        "description": "Run one deterministic FFmpeg-backed basic video operation inspired by OpenChatCut timeline item transforms. Supported operations are trim, splice, speed, crop, scale, rotate, flip, and freeze_frame. Use this for source preparation or one-off media transforms; use render_preview for timeline-based preview rendering.",
        "inputSchema": {
            "type": "object",
            "required": ["operation"],
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["trim", "splice", "speed", "crop", "scale", "rotate", "flip", "freeze_frame"]
                },
                "input_path": {"type": "string"},
                "output_path": {"type": "string"},
                "work_dir": {"type": "string"},
                "start_time": {"type": "number", "minimum": 0},
                "end_time": {"type": "number", "minimum": 0},
                "duration": {"type": "number", "exclusiveMinimum": 0},
                "speed": {"type": "number", "minimum": 0.1, "maximum": 8.0},
                "reverse": {"type": "boolean", "default": False},
                "x": {"type": "number", "minimum": 0},
                "y": {"type": "number", "minimum": 0},
                "width": {"type": "integer", "minimum": 2},
                "height": {"type": "integer", "minimum": 2},
                "output_width": {"type": "integer", "minimum": 2},
                "output_height": {"type": "integer", "minimum": 2},
                "mode": {"type": "string", "enum": ["fit", "fill", "stretch"], "default": "fit"},
                "degrees": {"type": "number"},
                "direction": {"type": "string", "enum": ["horizontal", "vertical", "both"], "default": "horizontal"},
                "at_time": {"type": "number", "minimum": 0},
                "clips": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "input_path": {"type": "string"},
                            "src": {"type": "string"},
                            "start": {"type": "number", "minimum": 0},
                            "end": {"type": "number", "minimum": 0},
                            "duration": {"type": "number", "exclusiveMinimum": 0},
                            "reason": {"type": "string"}
                        },
                        "additionalProperties": False
                    }
                }
            },
            "additionalProperties": False
        }
    },
    "tts_generate": {
        "description": "Compatibility alias for speech_synthesize. Generate narration or dubbing audio through the configured cloud TTS capability. preferred_provider=auto uses the default cloud TTS provider, and when allowed_providers is also given the preferred provider must be included in it (a conflict is a configuration error, not a silent substitution). allowed_providers, when provided, acts as a hard allowlist; wrong types or unknown provider names return a structured error. Retries transient network/concurrency/rate-limit errors by default (retries=3 extra attempts) but does not retry deterministic parameter/configuration failures. sample_mode must be boolean when provided. speed maps to speech_rate and the tool can also accept explicit speech_rate/pitch_rate/loudness_rate/sample_rate/output_format; this wrapper exposes ffprobe-friendly wav/mp3/ogg_opus output and rejects suffix/format mismatches. Generated audio must have a valid positive ffprobe duration or the tool returns an error.",
        "inputSchema": {
            "type": "object",
            "required": ["text"],
            "properties": {
                "text": {"type": "string"},
                "language": {"type": "string", "default": ""},
                # speaker/voice 允许整数: 数字音色 ID (含 0) 是合法值, 实现侧
                # 的 next() 链已按非 None 处理 — 只放行 string 会把 0 拦在门外
                "voice": {"type": ["string", "integer"]},
                "speaker": {"type": ["string", "integer"]},
                "speaker_id": {"type": ["string", "integer"]},
                "voice_id": {"type": ["string", "integer"]},
                "model": {"type": "string"},
                "style_instructions": {"type": "string"},
                "speed": {"type": "number", "exclusiveMinimum": 0},
                "speech_rate": {"type": "integer", "minimum": -50, "maximum": 100},
                "pitch_rate": {"type": "integer", "minimum": -12, "maximum": 12},
                "loudness_rate": {"type": "integer", "minimum": -50, "maximum": 100},
                "sample_rate": {"type": "integer", "enum": [8000, 16000, 24000, 32000, 44100, 48000]},
                "output_format": {"type": "string", "enum": ["wav", "mp3", "ogg_opus"]},
                "format": {"type": "string", "enum": ["wav", "mp3", "ogg_opus"]},
                "enable_subtitle": {"type": "boolean"},
                "preferred_provider": {"type": "string", "enum": ["auto", "cloud", "cloud_tts", "edge", "edge_tts"], "default": "auto"},
                "allowed_providers": {"type": "array", "items": {"type": "string", "enum": ["cloud", "cloud_tts", "edge", "edge_tts"]}},
                "retries": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "default": 3,
                    "description": "Extra retry attempts for transient TTS failures such as concurrency/rate-limit/network/server errors."
                },
                "retry_count": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 10,
                    "description": "Alias for retries."
                },
                "retry_backoff_seconds": {
                    "type": "number",
                    "minimum": 0,
                    "default": 3,
                    "description": "Initial exponential backoff before retries."
                },
                "sample_mode": {"type": "boolean", "default": False},
                "output_path": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "subtitle_scout": {
        "description": "Cheap subtitle-placement scout for a local video. Samples representative frames, returns an overview strip plus a native-width caption-band strip, measures band luminance, reports shot cuts, and suggests concrete style overrides for contrast/font-size before building subtitles. This tool does not call any model API.",
        "inputSchema": {
            "type": "object",
            "required": ["video_path"],
            "properties": {
                "video_path": {"type": "string"},
                "preset": {
                    "type": "string",
                    "enum": ["shortform_zh", "broadcast", "broadcast_en"],
                    "default": "shortform_zh"
                },
                "style": {"type": "object"},
                "max_frames": {"type": "integer", "minimum": 2},
                "scene_threshold": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
                "frames_dir": {"type": "string"},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "subtitle_build": {
        "description": "Build a subtitle package from timed transcript segments and a source video. Produces subtitles.json plus ASS/SRT sidecars, using punctuation-aware and word-boundary-aware cue segmentation, font-aware width measurement, and silence-snapped cue boundaries. Read the returned cue table before rendering.",
        "inputSchema": {
            "type": "object",
            "required": ["transcript_path", "video_path"],
            "properties": {
                "transcript_path": {"type": "string"},
                "video_path": {"type": "string"},
                "preset": {
                    "type": "string",
                    "enum": ["shortform_zh", "broadcast", "broadcast_en"],
                    "default": "shortform_zh"
                },
                "style": {"type": "object"},
                "speaker_names": {"type": "object"},
                "language": {"type": "string"},
                "silence_db": {"type": ["number", "string"], "description": "Silence threshold in dB, or 'auto'."},
                "min_silence_seconds": {"type": "number", "exclusiveMinimum": 0},
                "snap_window_seconds": {"type": "number", "exclusiveMinimum": 0},
                "output_json": {"type": "string"},
                "output_ass": {"type": "string"},
                "output_srt": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "subtitle_render": {
        "description": "Render subtitles from subtitles.json onto a local video. Burn-in mode re-emits ASS from cues[] every time so hand edits to subtitles.json take effect; soft mode muxes a mov_text subtitle track.",
        "inputSchema": {
            "type": "object",
            "required": ["video_path", "subtitles_path"],
            "properties": {
                "video_path": {"type": "string"},
                "subtitles_path": {"type": "string"},
                "output_path": {"type": "string"},
                "mode": {"type": "string", "enum": ["burn", "soft", "both"], "default": "burn"},
                "ass_path": {"type": "string"},
                "srt_path": {"type": "string"},
                "crf": {"type": "integer", "minimum": 0, "maximum": 51}
            },
            "additionalProperties": False
        }
    },
    "subtitle_qc": {
        "description": "Validate a subtitle package and optionally sample evidence frames from the rendered video. Checks cue timing, visibility, overlap, line overflow using real font metrics, reading-speed warnings, and transcript coverage. Evidence frames must be inspected by the agent.",
        "inputSchema": {
            "type": "object",
            "required": ["subtitles_path"],
            "properties": {
                "subtitles_path": {"type": "string"},
                "video_path": {"type": "string"},
                "output_json": {"type": "string"},
                "frames_dir": {"type": "string"},
                "max_evidence_frames": {"type": "integer", "minimum": 1}
            },
            "additionalProperties": False
        }
    },
    "condense_index": {
        "description": "Index a long spoken video for condensing. Splits timed transcript into sentence-like units using punctuation and detected pauses, finds disfluency/repetition/topic hints, computes a lossless compression floor, runs a coarse visual survey, and writes speech_index.json plus a full markdown unit table.",
        "inputSchema": {
            "type": "object",
            "required": ["video_path"],
            "properties": {
                "video_path": {"type": "string"},
                "transcript_path": {"type": "string", "default": "out/transcript.json"},
                "language": {"type": "string"},
                "unit_pause_seconds": {"type": "number", "exclusiveMinimum": 0},
                "max_unit_seconds": {"type": "number", "exclusiveMinimum": 0},
                "min_silence_seconds": {"type": "number", "exclusiveMinimum": 0},
                "silence_db": {"type": ["number", "string"], "description": "Silence threshold in dB, or 'auto'."},
                "max_gap": {"type": "number", "minimum": 0},
                "visual_survey": {"type": "boolean", "default": True},
                "survey_frames": {"type": "integer", "minimum": 1},
                "scene_threshold": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
                "frames_dir": {"type": "string"},
                "max_table_rows": {"type": "integer", "minimum": 1},
                "output_json": {"type": "string"},
                "output_table": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "condense_plan": {
        "description": "Turn a speech index keep/drop list into cut clips and joins. Snaps clip edges to detected pauses, tightens long pauses inside kept runs, flags continuity and word-boundary risks, and writes condense_plan.json, condense_timeline.json, condense_script.md, condensed_transcript.json, and condense_redline.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index_path": {"type": "string", "default": "out/speech_index.json"},
                "video_path": {"type": "string"},
                "keep": {
                    "type": "array",
                    "items": {"type": ["string", "object"]},
                    "description": "Unit ids/ranges such as 'u012-u031', or explicit {start,end} ranges."
                },
                "drop": {"type": "array", "items": {"type": "string"}},
                "tighten_pauses": {"type": "boolean", "default": True},
                "drop_fillers": {"type": ["boolean", "string"], "description": "false/off, 'hard', or 'aggressive'."},
                "max_gap": {"type": "number", "minimum": 0},
                "lead_in": {"type": "number", "minimum": 0},
                "lead_out": {"type": "number", "minimum": 0},
                "min_clip": {"type": "number", "exclusiveMinimum": 0},
                "snap_window": {"type": "number", "exclusiveMinimum": 0},
                "min_silence_seconds": {"type": "number", "exclusiveMinimum": 0},
                "silence_db": {"type": ["number", "string"], "description": "Silence threshold in dB, or 'auto'."},
                "target_duration": {"type": "number", "exclusiveMinimum": 0},
                "target_ratio": {"type": "number", "exclusiveMinimum": 0},
                "output_json": {"type": "string"},
                "timeline_json": {"type": "string"},
                "script_md": {"type": "string"},
                "output_transcript": {"type": "string"},
                "redline_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "condense_render": {
        "description": "Render a condensed spoken video from condense_plan.json. Cuts each planned clip through FFmpeg, normalizes all segments to one canvas/fps/pixel format, joins with hard cuts or short dissolves, and writes a render report with output join times.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_path": {"type": "string", "default": "out/condense_plan.json"},
                "video_path": {"type": "string"},
                "output_path": {"type": "string"},
                "work_dir": {"type": "string"},
                "join": {"type": "string", "enum": ["hard", "dissolve"], "default": "hard"},
                "dissolve_seconds": {"type": "number", "exclusiveMinimum": 0},
                "crf": {"type": "integer", "minimum": 0, "maximum": 51},
                "output_width": {"type": "integer", "minimum": 2},
                "output_height": {"type": "integer", "minimum": 2}
            },
            "additionalProperties": False
        }
    },
    "condense_qc": {
        "description": "Quality-check a condensed video against its condense plan. Verifies duration/hash binding/audio presence, measures join audio energy and visual jump severity, returns join frame/waveform evidence sheets, and writes condense_qc_report.json.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_path": {"type": "string", "default": "out/condense_plan.json"},
                "video_path": {"type": "string", "default": "out/condensed.mp4"},
                "render_report_path": {"type": "string"},
                "frames_dir": {"type": "string"},
                "max_evidence_joins": {"type": "integer", "minimum": 1},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "diarize_audit": {
        "description": "Audit speaker labels in an existing transcript without changing text. Returns speaker share, roster sample windows, name cues from transcript text, suspect turn windows, and a soft verdict to guide visual speaker-attribution repair.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "transcript_path": {"type": "string", "default": "out/transcript.json"},
                "window_pad": {"type": "number", "minimum": 0},
                "window_gap": {"type": "number", "minimum": 0},
                "max_windows": {"type": "integer", "minimum": 1},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "diarize_relabel": {
        "description": "Apply corrected time-range to speaker assignments to a transcript, rewriting only speaker labels on segments/words and splitting segments at word-level speaker boundaries when safe. It never edits transcript text.",
        "inputSchema": {
            "type": "object",
            "required": ["assignments"],
            "properties": {
                "transcript_path": {"type": "string", "default": "out/transcript.json"},
                "assignments": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["start", "end", "speaker"],
                        "properties": {
                            "start": {"type": "number", "minimum": 0},
                            "end": {"type": "number", "minimum": 0},
                            "speaker": {"type": "string"}
                        },
                        "additionalProperties": False
                    }
                },
                "snap_seconds": {"type": "number", "minimum": 0},
                "output_path": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "video_read_frames": {
        "description": "Read a few original-resolution frames, optionally cropped/upscaled, for inspecting small on-screen text such as name plates, lower-thirds, UI labels, or slide text. Use video_watch_segment for motion; use this when the task is reading detail.",
        "inputSchema": {
            "type": "object",
            "required": ["video_path"],
            "properties": {
                "video_path": {"type": "string"},
                "timestamps": {"type": "array", "items": {"type": "number", "minimum": 0}},
                "start_time": {"type": "number", "minimum": 0},
                "end_time": {"type": "number", "minimum": 0},
                "count": {"type": "integer", "minimum": 1},
                "region": {
                    "type": ["string", "object"],
                    "description": "Preset name such as full/name_plate/lower_third/bottom_left/bottom_right/top_left/top_right/center, or {left,top,right,bottom} fractions."
                },
                "upscale": {"type": "number", "minimum": 1, "maximum": 4},
                "max_width": {"type": "integer", "minimum": 64},
                "max_frames": {"type": "integer", "minimum": 1, "maximum": 48},
                "output_dir": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "validate_timeline": {
        "description": "Validate EDL/timeline project JSON before rendering. Requires ffprobe for source-duration bounds; source duration is read from format duration with stream duration fallback and cached per source file. Pipeline timelines must be JSON objects with non-empty project, assets[], sequence{} or output_canvas{}, tracks[], and at least one video/main track; legacy top-level clips[] is retained only for debug compatibility and does not satisfy the project contract. It validates project/sequence/output_canvas/assets/markers/transitions metadata when provided; tracks and clips must be objects. Checks required clip source/start/end-or-duration/reason fields, rejects boolean/NaN/Infinity time values, checks end-duration consistency, source existence, source-duration bounds, optional timeline placement/effects/transition metadata, and writes a report with the current timeline hash. In tracks[] timelines, clips on non-video tracks (subtitle/overlay/callout plans) may provide non-empty text instead of a media source; video/main track clips always require a source.",
        "inputSchema": {
            "type": "object",
            "required": ["timeline_path"],
            "properties": {
                "timeline_path": {"type": "string"},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "render_preview": {
        "description": "Render a preview video from timeline JSON using FFmpeg/ffprobe. Project-style tracks[] timelines are rendered as a basic editing project: video/main clips are placed on a black sequence canvas by timeline_start with boundary padding, original video audio plus audio/music/voiceover tracks are internally pre-baked into full-length positioned wav beds before mixing, subtitle/text tracks are composited with drawtext, and image/overlay tracks are composited with overlay enable windows. The renderer writes preview.render_report.json, preview.render_plan.json, and preview.edit_decisions.json for traceability. It supports simple fade transition_in/transition_out, clip speed, volume, opacity, output_canvas/sequence canvas and fps. Pipeline timelines must satisfy the project contract; top-level clips[] are legacy/debug compatibility only. Unsupported unknown track types are recorded in the render plan rather than silently rendered.",
        "inputSchema": {
            "type": "object",
            "required": ["timeline_path"],
            "properties": {
                "timeline_path": {"type": "string"},
                "output_path": {"type": "string"},
                "work_dir": {"type": "string"},
                "output_width": {"type": "integer", "minimum": 2},
                "output_height": {"type": "integer", "minimum": 2}
            },
            "additionalProperties": False
        }
    },
    "qc_preview": {
        "description": "Run deterministic QC on a preview/final video: ffprobe metadata, black frame scan, short edit-boundary black-frame scan, silence scan, freeze-frame scan, volume peak/mean scan, audio stream coverage, timeline/render hash binding, and expected duration/resolution/fps checks against the timeline. Media probe failures and scan failures are blocking; black/silence/freeze/clipping/very-low-volume findings become warning issues unless they indicate a scan failure; audio ending before the video is an error. The silence/volume scans only run when an audio stream exists; a video without any audio stream is reported as a warning. Pass timeline_path so the QC report can prove which timeline produced the preview and compare output media against timeline sequence expectations.",
        "inputSchema": {
            "type": "object",
            "required": ["video_path"],
            "properties": {
                "video_path": {"type": "string"},
                "timeline_path": {"type": "string"},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    },
    "timeline_diff": {
        "description": "Create an auditable timeline diff from repair instructions and optionally apply it to a timeline. patch must be a JSON object when provided, and apply must be a boolean. Supported patch operations: set_timeline_fields (project metadata except clips/tracks), set_track_fields, add_assets, update_assets, remove_asset_indices, add_tracks, insert_tracks, replace_tracks, remove_track_indices, update_clips (shallow field merge; null deletes a field), replace_clips, remove_clip_indices, move_clips, insert_clips, and add_clips. replace/update/remove/move indices refer to the pre-patch flat clip order; asset and track indices refer to their own arrays. Structural track operations (add/insert/replace/remove tracks) cannot be mixed with clip operations in the same patch; split them into separate timeline_diff calls. replace/update are applied first, then remove in reverse order, then at most one move_clips entry, then insert/add new clips. move_clips cannot be combined with remove_clip_indices, cannot contain multiple moves in one patch, and cannot address clips inserted by the same patch. Duplicate remove/replace/update indices, remove-and-replace/update conflicts, out-of-range indices, non-object clips/fields, an empty apply patch, or mixing structural track operations with clip operations are validation errors. When apply=true, patch operations and the patched timeline are validated first; invalid patches write the diff report but do not modify the original timeline. In tracks[] timelines, add_clips prefers the first video/main track, while insert/move may specify track_index.",
        "inputSchema": {
            "type": "object",
            "required": ["timeline_path", "instructions"],
            "properties": {
                "timeline_path": {"type": "string"},
                "instructions": {"type": "string"},
                "patch": {"type": "object"},
                "apply": {"type": "boolean", "default": False},
                "output_json": {"type": "string"}
            },
            "additionalProperties": False
        }
    }
}


RECAP_TOOL_SCHEMAS: dict[str, dict] = {'detect_shots': {'description': 'Detect shot boundaries across the whole video with PySceneDetect ContentDetector and '
                                 'cache them as a shots.json timeline (segment_version cover-all-v2). Shots cover the '
                                 'full video contiguously with no gaps: sub-min_len shots are merged into the previous '
                                 'shot (or accumulated into the first real shot when they open the video), so adjacent '
                                 'shots always satisfy end == next start. Output JSON fields '
                                 '(video/duration/video_signature/segment_version/threshold/min_len/frame_skip/fps/n_shots/shots[{shot_id,start,end,dur}]) '
                                 'are the shared contract consumed by downstream shot-driven tools (arrange_footage, '
                                 'bind_narration, render_narrated). If output_json already exists and its video '
                                 'signature (path|size|mtime) plus all detection parameters match, the cache is reused '
                                 'and the result reports reused=true; pass force=true to redetect. frame_skip>0 speeds '
                                 'up detection by skipping frames at the cost of cut precision. This tool does not '
                                 'call any model API; requires ffprobe and the scenedetect package.',
                  'inputSchema': {'type': 'object',
                                  'required': ['input_path'],
                                  'properties': {'input_path': {'type': 'string'},
                                                 'output_json': {'type': 'string', 'default': 'out/shots.json'},
                                                 'threshold': {'type': 'number',
                                                               'exclusiveMinimum': 0,
                                                               'default': 27.0,
                                                               'description': 'ContentDetector cut sensitivity; lower '
                                                                              'detects more cuts.'},
                                                 'min_len': {'type': 'number',
                                                             'minimum': 0,
                                                             'default': 0.8,
                                                             'description': 'Shots shorter than this are merged into '
                                                                            'neighbors instead of dropped, keeping '
                                                                            'coverage gap-free.'},
                                                 'frame_skip': {'type': 'integer', 'minimum': 0, 'default': 0},
                                                 'force': {'type': 'boolean',
                                                           'default': False,
                                                           'description': 'Ignore an existing matching cache and '
                                                                          'redetect.'}},
                                  'additionalProperties': False}},
 'arrange_footage': {'description': 'Deterministic footage arranger for dialogue-driven movie recaps '
                                    '(arrange-footage-first, write-narration-second). Three actions, no model API '
                                    'calls anywhere. action=dialogue converts a speaker-labelled transcript into a '
                                    'numbered dialogue axis (D0001[84s] speaker: line) plus dialogue_index.json — the '
                                    'single authority for D-ids the agent must cite when writing the outline. '
                                    'action=arrange turns dialogue_index + shots timeline + an agent-written outline '
                                    '(beats -> 2-4 points, each citing D-ids) + target minutes into a per-beat footage '
                                    'reel: each point is anchored at its cited dialogue moment and takes a continuous '
                                    'whole-shot block from there (a global monotonic cursor never rewinds; new seams '
                                    'only appear at point/beat boundaries; the first piece of every block must be '
                                    '>=1.5s to avoid short flashes), per-point seconds are normalized from the target '
                                    'length, and when the total reel overruns target/narration_ratio by >3% whole '
                                    "spans are trimmed back from the longest beats' tails; outputs reel.json, "
                                    'plan.json and a writing brief with hard char budgets per beat AND per point. An '
                                    'invalid outline returns a structured outline_invalid error for the agent to '
                                    'rewrite. action=anchor merges the agent-written narration (beats -> sentences '
                                    'tagged with their point number) with the reel: sentences are mechanically '
                                    "re-split on punctuation, bound to their OWN point's footage block (shots assigned "
                                    'by midpoint to exactly one sentence, so anchor sets are disjoint), and emitted as '
                                    'narration_script.json + graph.json for TTS and bind_narration; beats whose '
                                    'narration exceeds the char cap by >15% return a structured over_budget error '
                                    'listing them so the agent shortens the text (narration always yields to footage).',
                     'inputSchema': {'type': 'object',
                                     'required': ['action'],
                                     'properties': {'action': {'type': 'string',
                                                               'enum': ['dialogue', 'arrange', 'anchor']},
                                                    'transcript_path': {'type': 'string',
                                                                        'description': 'dialogue: speaker-labelled '
                                                                                       'transcript JSON (transcribe '
                                                                                       'output or segments array).'},
                                                    'output_txt': {'type': 'string',
                                                                   'description': 'dialogue: dialogue axis path. '
                                                                                  'Default: out/dialogue_axis.txt'},
                                                    'output_json': {'type': 'string',
                                                                    'description': 'dialogue: dialogue index path. '
                                                                                   'Default: out/dialogue_index.json'},
                                                    'dialogue_index_path': {'type': 'string',
                                                                            'description': 'arrange: '
                                                                                           'dialogue_index.json from '
                                                                                           'action=dialogue.'},
                                                    'shots_path': {'type': 'string',
                                                                   'description': 'arrange: shots timeline from '
                                                                                  'detect_shots.'},
                                                    'outline_path': {'type': 'string',
                                                                     'description': 'arrange: agent-written outline '
                                                                                    'JSON (characters + '
                                                                                    'beats/points/dlg).'},
                                                    'minutes': {'type': 'number',
                                                                'exclusiveMinimum': 0,
                                                                'description': 'arrange: target output minutes.'},
                                                    'sec_per_point': {'type': 'number',
                                                                      'exclusiveMinimum': 0,
                                                                      'description': 'arrange: override the normalized '
                                                                                     'per-point footage seconds '
                                                                                     '(regression/replay use).'},
                                                    'chars_per_sec': {'type': 'number',
                                                                      'minimum': 2,
                                                                      'maximum': 7,
                                                                      'description': 'arrange: narration speaking rate '
                                                                                     'used for the word-count budget '
                                                                                     '(default 3.4; measure the active '
                                                                                     'cloud TTS voice before large runs). Carried '
                                                                                     'into reel.json and reused by '
                                                                                     'action=anchor.'},
                                                    'trim': {'type': 'boolean',
                                                             'default': True,
                                                             'description': 'arrange: trim reel overrun back to target '
                                                                            '(disable only for replay).'},
                                                    'reel_json': {'type': 'string',
                                                                  'description': 'arrange: reel output. Default: '
                                                                                 'out/reel.json'},
                                                    'plan_json': {'type': 'string',
                                                                  'description': 'arrange: plan output. Default: '
                                                                                 'out/plan.json'},
                                                    'brief_txt': {'type': 'string',
                                                                  'description': 'arrange: writing brief output. '
                                                                                 'Default: out/writing_brief.txt'},
                                                    'reel_path': {'type': 'string',
                                                                  'description': 'anchor: reel.json from '
                                                                                 'action=arrange.'},
                                                    'plan_path': {'type': 'string',
                                                                  'description': 'anchor: plan.json from '
                                                                                 'action=arrange.'},
                                                    'script_path': {'type': 'string',
                                                                    'description': 'anchor: agent-written narration '
                                                                                   'JSON '
                                                                                   '{beats:[{idx,sentences:[{text,point}]}]}.'},
                                                    'title': {'type': 'string',
                                                              'description': 'anchor: film title recorded in the '
                                                                             'graph.'},
                                                    'output_script': {'type': 'string',
                                                                      'description': 'anchor: narration script output. '
                                                                                     'Default: '
                                                                                     'out/narration_script.json'},
                                                    'output_graph': {'type': 'string',
                                                                     'description': 'anchor: event graph output. '
                                                                                    'Default: out/graph.json'}},
                                     'additionalProperties': False}},
 'synthesize_narration': {'description': 'Batch-synthesize commentary narration audio from a narration script.json '
                                         '(array of segments with seg_id/text/semantic_units, produced by '
                                         'arrange_footage action=anchor). For each segment it synthesizes one audio '
                                         'file (paragraph mode by default; by_sentence=true synthesizes per sentence '
                                         'and concatenates), then writes script_tts.json with segment-level '
                                         'audio_path/audio_dur/speech_dur/delivery_pause_sec plus a per-sentence '
                                         'sentences[] timeline (start/end offsets estimated from speech weight) that '
                                         'downstream shot binding relies on. Optional semantic_out writes a flat '
                                         'semantic timeline with per-sentence global offsets. Uses the standard cloud '
                                         "TTS capability through this kit's tts_generate. Segment results are cached by a fingerprint of spoken text + "
                                         'semantic-unit mapping + pause + provider + voice + rate, so unchanged '
                                         'segments are never re-synthesized while any script or voice change forces '
                                         'regeneration. With require_complete=true (default) any failed segment '
                                         'returns an error listing missing seg_ids and output_json is not written '
                                         '(per-file audio cache is kept for reruns); with false a partial output_json '
                                         'is written and flagged.',
                          'inputSchema': {'type': 'object',
                                          'required': ['script_path'],
                                          'properties': {'script_path': {'type': 'string'},
                                                         'output_json': {'type': 'string',
                                                                         'default': 'out/script_tts.json'},
                                                         'audio_dir': {'type': 'string',
                                                                       'default': '.video_agent/narration_tts'},
                                                         'provider': {'type': 'string',
                                                                      'enum': ['auto',
                                                                               'cloud',
                                                                               'cloud_tts'],
                                                                      'description': 'Cloud TTS provider. Defaults to the configured cloud TTS backend.'},
                                                         'voice': {'type': 'string',
                                                                   'description': 'Voice name or speaker id. Defaults to the configured narration voice.'},
                                                         'rate': {'type': 'string',
                                                                  'description': 'Rate like +6% or -10%; mapped to cloud TTS speed. Defaults to the configured narration rate.'},
                                                         'by_sentence': {'type': 'boolean',
                                                                         'default': False,
                                                                         'description': 'Synthesize per sentence and '
                                                                                        'concatenate; gives real '
                                                                                        'per-sentence timings and '
                                                                                        'starves LLM-TTS of rewrite '
                                                                                        'room. Recommended for '
                                                                                        'LLM-based cloud voices.'},
                                                         'flatten_quotes': {'type': 'boolean',
                                                                            'default': False,
                                                                            'description': 'De-dramatize spoken text '
                                                                                           'before synthesis: '
                                                                                           'full-width colons become '
                                                                                           'commas and quote marks are '
                                                                                           'removed (punctuation only, '
                                                                                           'words untouched; subtitles '
                                                                                           'keep the original text). '
                                                                                           'Prevents LLM-TTS from '
                                                                                           "treating 'X said:' as a "
                                                                                           'script speaker tag — '
                                                                                           'measured failure mode: '
                                                                                           'dropped attribution '
                                                                                           'clauses, voice-acted '
                                                                                           'quotes, invented '
                                                                                           'dialogue.'},
                                                         'verify': {'type': 'string',
                                                                    'enum': ['asr'],
                                                                    'description': 'Post-synthesis fidelity check: '
                                                                                   'each segment audio is transcribed '
                                                                                   'back through cloud ASR and every sentence '
                                                                                   'is checked by 4-gram content hit '
                                                                                   'plus duration-vs-chars '
                                                                                   'plausibility (ASR alone '
                                                                                   'under-transcribes, duration is the '
                                                                                   'independent second signal). '
                                                                                   'hit<0.35 or duration outlier = '
                                                                                   'bad; 0.35-0.7 = grey. Bad AND grey '
                                                                                   'sentences are re-synthesized '
                                                                                   '(per-sentence cache file deleted) '
                                                                                   'for up to verify_retries rounds; '
                                                                                   'only a still-grey final round is '
                                                                                   'accepted as warn — grey no longer '
                                                                                   'slips through unhealed. Short '
                                                                                   'sentences (<6 chars) need dual '
                                                                                   'evidence (zero hit + duration '
                                                                                   'outlier). If ASR itself is '
                                                                                   'unavailable, status is capped at '
                                                                                   'warn with reason=asr_unavailable '
                                                                                   '(never a fake pass). Speaker count '
                                                                                   '>1 in narration is reported as a '
                                                                                   'warning (voice-acted quotes). '
                                                                                   'pass/warn are terminal; reruns '
                                                                                   're-verify only missing/failed '
                                                                                   'segments.'},
                                                         'verify_retries': {'type': 'integer',
                                                                            'minimum': 0,
                                                                            'maximum': 3,
                                                                            'default': 2,
                                                                            'description': 'Max heal rounds per '
                                                                                           'segment when verify finds '
                                                                                           'bad sentences.'},
                                                         'semantic_out': {'type': 'string'},
                                                         'require_complete': {'type': 'boolean', 'default': True}},
                                          'additionalProperties': False}},
 'bind_narration': {'description': 'Deterministically bind TTS narration sentences to footage windows with the tape-DP '
                                   'kernel in reel mode. Consumes script_tts.json (segments with audio durations + '
                                   'sentence timeline), the event graph, the shots timeline and the per-beat reel from '
                                   'arrange_footage; each beat binds only within its own reel tape, so the arranged '
                                   'footage order is preserved and new seams stay at point/beat boundaries. Emits a '
                                   'render-ready EDL plus a hard-QC report enforcing zero shot reuse, monotonic source '
                                   'time, no short flashes (with a seamless-continuation exemption), and '
                                   'frame-continuous breathing tails <=3s. Optional inserts_path enables '
                                   'original-audio reserve/replay windows that auto-degrade when they would starve '
                                   'narration footage. avoid_shot_ids penalizes given shots in the DP (use after a '
                                   'spot review found sentence/visual contradictions, then rebind). Pure '
                                   'deterministic, no model API calls. On footage shortage or QC failure it returns an '
                                   '[ERROR] with structured details (which beat, required vs available seconds) '
                                   "instead of raising — shorten that beat's narration, re-TTS, and rebind.",
                    'inputSchema': {'type': 'object',
                                    'required': ['script_path', 'graph_path', 'timeline_path', 'reel_path'],
                                    'properties': {'script_path': {'type': 'string',
                                                                   'description': 'script_tts.json from '
                                                                                  'synthesize_narration.'},
                                                   'graph_path': {'type': 'string',
                                                                  'description': 'Event graph JSON from '
                                                                                 'arrange_footage action=anchor.'},
                                                   'timeline_path': {'type': 'string',
                                                                     'description': 'Shots timeline JSON from '
                                                                                    'detect_shots.'},
                                                   'reel_path': {'type': 'string',
                                                                 'description': 'Reel JSON from arrange_footage '
                                                                                'action=arrange; each segment binds '
                                                                                'only within its own reel.'},
                                                   'output_edl': {'type': 'string',
                                                                  'description': 'Output EDL path. Default: '
                                                                                 'out/edl.json'},
                                                   'qc_json': {'type': 'string',
                                                               'description': 'Output QC report path. Default: '
                                                                              'out/edl_qc.json'},
                                                   'inserts_path': {'type': 'string',
                                                                    'description': 'Optional original-audio inserts '
                                                                                   'JSON; reserved mode auto-degrades '
                                                                                   'to replay when it would starve '
                                                                                   'narration footage.'},
                                                   'avoid_shot_ids': {'type': 'array',
                                                                      'items': {'type': 'string'},
                                                                      'description': 'Shot ids to avoid when rebinding '
                                                                                     'after a review found '
                                                                                     'sentence/visual contradictions.'},
                                                   'tail_mode': {'type': 'string',
                                                                 'enum': ['highlight', 'all', 'none'],
                                                                 'default': 'highlight',
                                                                 'description': 'Breathing-tail policy. "highlight" '
                                                                                '(default): only beats marked '
                                                                                'highlight=true in the writer script '
                                                                                'get a <=3s tail — gaps are '
                                                                                'punctuation, not spaces; a gap after '
                                                                                'every beat reads as slack pacing. '
                                                                                '"all": legacy every-beat tails. '
                                                                                '"none": no tails.'}},
                                    'additionalProperties': False}},
 'render_narrated': {'description': 'Render the final narrated video from an EDL: cuts source windows per segment '
                                    '(with per-segment caching, so interrupted renders resume), concatenates picture '
                                    'and narration on a frame-accurate shared timebase, burns sentence-level subtitles '
                                    'rebuilt on the output timeline, and mixes scene-grouped background music. '
                                    'Narration audio paths come from script_tts.json. Subtitles auto-disable with a '
                                    'warning when no CJK font is installed; BGM is skipped with a warning when '
                                    'bgm_dir/VE_BGM_DIR is unset, missing, or holds no usable audio (files with '
                                    'embedded cover art streams are filtered out — they hang concat). Hard gates: '
                                    'rejects EDLs with duplicate/overlapping/regressing shot windows and refuses to '
                                    'mux drifted A/V tracks. Breathing-tail segments extend picture past narration '
                                    'with original audio. This tool does not call any model API; requires '
                                    'ffmpeg/ffprobe.',
                     'inputSchema': {'type': 'object',
                                     'required': ['edl_path', 'video_path', 'timeline_path', 'script_path'],
                                     'properties': {'edl_path': {'type': 'string',
                                                                 'description': 'EDL JSON from bind_narration (list of '
                                                                                'segments, or {segments:[...]}).'},
                                                    'video_path': {'type': 'string',
                                                                   'description': 'Source movie file.'},
                                                    'timeline_path': {'type': 'string',
                                                                      'description': 'Shots timeline JSON, used for '
                                                                                     'shot lookup and the QC gate.'},
                                                    'script_path': {'type': 'string',
                                                                    'description': 'script_tts.json with per-segment '
                                                                                   'sentence timings for subtitles.'},
                                                    'output_path': {'type': 'string',
                                                                    'description': 'Output file. Default: '
                                                                                   'out/final.mp4'},
                                                    'subtitle': {'type': 'boolean',
                                                                 'default': True,
                                                                 'description': 'Burn subtitles (auto-disabled if no '
                                                                                'CJK font).'},
                                                    'bgm': {'type': 'boolean', 'default': True},
                                                    'bgm_dir': {'type': 'string',
                                                                'description': 'BGM library dir with <emotion>/*.mp3 '
                                                                               'subdirs. Default: VE_BGM_DIR env.'},
                                                    'bgm_volume': {'type': 'number',
                                                                   'exclusiveMinimum': 0,
                                                                   'default': 0.06},
                                                    'bed_volume': {'type': 'number',
                                                                   'minimum': 0,
                                                                   'maximum': 1,
                                                                   'description': 'Volume of the original-film audio '
                                                                                  'bed mixed under narration. Default '
                                                                                  '0.13 (RENDER_BED_VOLUME env). Set 0 '
                                                                                  'for foreign-language films: footage '
                                                                                  'is anchored at dialogue moments, so '
                                                                                  'the bed is mostly foreign speech '
                                                                                  'and reads as characters talking '
                                                                                  'over the narrator.'},
                                                    'tail_volume': {'type': 'number',
                                                                    'minimum': 0,
                                                                    'maximum': 1,
                                                                    'description': 'Original-film audio volume inside '
                                                                                   'breathing tails (narration '
                                                                                   'stopped). Default 0.85 '
                                                                                   '(RENDER_TAIL_VOLUME env). While '
                                                                                   'the narrator speaks the bed stays '
                                                                                   'at bed_volume (default 0.13 — '
                                                                                   'LOWERED, not muted; pass '
                                                                                   'bed_volume=0 for true silence '
                                                                                   'under narration, mandatory for '
                                                                                   'foreign films); in the gap the '
                                                                                   'original audio ramps up to '
                                                                                   'tail_volume over 0.3s. Set 0 for '
                                                                                   'silent tails (legacy).'},
                                                    'sub_pos': {'type': 'string',
                                                                'enum': ['top', 'middle', 'lower', 'bottom'],
                                                                'default': 'lower'},
                                                    'breath_every': {'type': 'integer',
                                                                     'minimum': 0,
                                                                     'default': 0,
                                                                     'description': 'LEGACY: insert an original-audio '
                                                                                    'breathing segment every N '
                                                                                    'segments (0=off). Superseded by '
                                                                                    "bind_narration's "
                                                                                    'tail_mode=highlight breathing '
                                                                                    'tails — do not enable both or the '
                                                                                    'pacing gets double-punctuated.'},
                                                    'work_dir': {'type': 'string',
                                                                 'description': 'Cache/work dir. Default: '
                                                                                '.video_agent/render_narrated'}},
                                     'additionalProperties': False}},
 'soccer_ingest': {'description': 'soccer-recap step 1: adapt football match half videos into the standard '
                                  'out/match.json contract (teams, half video paths+durations, empty event axis). action=axis '
                                  'instead merges half transcripts into a C-numbered English commentary axis '
                                  '(out/commentary_axis.txt + commentary_index.json) — the football equivalent of '
                                  "movie-recap's dialogue axis; the agent reads it to understand the match story. "
                                  'Deterministic, no model calls. Goal/chance events are written later as inline '
                                  'event objects in the agent-authored outline.',
                   'inputSchema': {'type': 'object',
                                   'properties': {'action': {'type': 'string',
                                                             'enum': ['match', 'axis'],
                                                             'default': 'match'},
                                                  'source': {'type': 'string',
                                                             'enum': ['video'],
                                                             'default': 'video'},
                                                  'game': {'type': 'string',
                                                           'description': 'Relative match dir under video_root '
                                                                          '(action=match).'},
                                                  'video_root': {'type': 'string'},
                                                  'transcript_paths': {'type': 'array',
                                                                       'items': {'type': 'string'},
                                                                       'description': 'action=axis: transcript.json of '
                                                                                      'half 1 and half 2, in order.'},
                                                  'out_dir': {'type': 'string', 'default': 'out'}},
                                   'additionalProperties': False}},
 'soccer_arrange': {'description': 'soccer-recap step 4: deterministic footage arrangement. Consumes out/match.json, '
                                   'full-half shots.json (from detect_shots on the lowres half videos) and the '
                                   'agent-written out/outline.json (narrative beats carrying inline event objects; kinds '
                                   'open/goal/chance/ending; per-goal replays 0-2 variation; highlight flags; ending '
                                   'beat carries agent-located whistle_t/in_t/out_t). Produces out/reel.json '
                                   '(cold-open flash montage + one segment per beat with shot-boundary snapped cuts, '
                                   'replay incorporation, reel_in/reel_event timeline, single breathing black gap) and '
                                   'out/writing_brief.txt (per-beat REAL narration seconds and HARD char budgets, call '
                                   'slots and highlight holds already deducted). Returns outline_invalid with issues '
                                   'when the outline has invalid events, is out of order, or windows overlap — fix the '
                                   'outline and rerun (<=2 attempts).',
                    'inputSchema': {'type': 'object',
                                    'required': ['match_path', 'outline_path', 'shots_paths'],
                                    'properties': {'match_path': {'type': 'string'},
                                                   'outline_path': {'type': 'string'},
                                                   'shots_paths': {'type': 'object',
                                                                   'description': '{"1": shots_h1.json, "2": '
                                                                                  'shots_h2.json}',
                                                                   'additionalProperties': {'type': 'string'}},
                                                   'chars_per_sec': {'type': 'object',
                                                                     'description': 'Per-tier chars/sec override, e.g. '
                                                                                    '{"0":4.9}.',
                                                                     'additionalProperties': {'type': 'number'}},
                                                   'out_dir': {'type': 'string', 'default': 'out'}},
                                    'additionalProperties': False}},
 'soccer_tts': {'description': 'soccer-recap step 7: per-sentence TTS of the agent-written out/writer_script.json with '
                               'the 3-tier emotion system (tier 0/1/2 -> cloud TTS speech_rate 12/20/28, '
                               'loudnorm -17.5/-16.5/-14.5 LUFS). Pitch is ALWAYS 0 — pitch shifts read as a '
                               'different person (verified by speaker clustering). Sentence-level cache keyed by '
                               'provider+voice+rate+text: rewriting one sentence only resynthesizes that sentence. '
                               'Provider/voice from args or configured soccer narration defaults. Produces '
                               'out/script_tts.json with real per-sentence durations.',
                'inputSchema': {'type': 'object',
                                'required': ['script_path'],
                                'properties': {'script_path': {'type': 'string'},
                                               'provider': {'type': 'string', 'enum': ['auto', 'cloud', 'cloud_tts']},
                                               'voice': {'type': 'string'},
                                               'out_dir': {'type': 'string', 'default': 'out'}},
                                'additionalProperties': False}},
 'soccer_render': {'description': 'soccer-recap step 8: placement + render + mix + hard QC gates, all deterministic. '
                                  'Places sentences (anchor=event pins goal calls to the event second, bridge starts '
                                  '~1.5s before the segment cut for a J-cut straddle, post respects highlight '
                                  'crowd-roar holds, flow chains after the previous sentence); fails fast with '
                                  "over_budget BEFORE rendering when text overruns its region (compress that beat's "
                                  'copy, rerun soccer_tts+soccer_render — cache makes it cheap). Renders segments '
                                  'joined by duration-preserving 0.3s dissolves (extra 0.15s footage is taken on each '
                                  'side and consumed by the crossfade, so the reel timeline and every narration anchor '
                                  'stay exact; the open montage keeps hard cuts), a spoiler-free Chinese scoreboard '
                                  '(score switches only at the goal instant), a title card over the designed post-open '
                                  'black beat (no naked black frame; text from outline.gap_card {line1,line2} or '
                                  'teams_cn/open_title fallback), freeze-frame end card, and burned-in bottom-center '
                                  'subtitles from the placed sentences (disable with subtitles=false). Mixes narration '
                                  'over a smooth-ramp ducked bed (pass base_transcript_path of the base reel to also '
                                  'duck original English commentary). QC gates written to out/qc.json: blackdetect '
                                  '(only the designed gap region tolerated), hard-anchor deviation <=1s, integrated '
                                  'loudness in [-19.5,-12.5] LUFS, duration match; returns qc_failed with details when '
                                  'any gate fails.',
                   'inputSchema': {'type': 'object',
                                   'required': ['reel_path', 'script_tts_path', 'outline_path'],
                                   'properties': {'reel_path': {'type': 'string'},
                                                  'script_tts_path': {'type': 'string'},
                                                  'outline_path': {'type': 'string'},
                                                  'base_transcript_path': {'type': 'string',
                                                                           'description': 'transcript.json of the base '
                                                                                          'reel; its speech intervals '
                                                                                          'are added to the ducking '
                                                                                          'union.'},
                                                  'subtitles': {'type': 'boolean',
                                                                'default': True,
                                                                'description': 'Burn bottom-center narration subtitles '
                                                                               '(per placed sentence).'},
                                                  'output_path': {'type': 'string'},
                                                  'out_dir': {'type': 'string', 'default': 'out'}},
                                   'additionalProperties': False}},
 'lol_ingest': {'description': 'lol-recap step 1: adapt a League of Legends match into out/match.json (teams, per-game '
                               'video paths+durations). action=axis instead merges per-game caster ASR transcripts '
                               'into a C-numbered Chinese commentary axis (out/commentary_axis.txt + '
                               'commentary_index.json) — the agent reads it like a screenplay to understand the game '
                               'story (players/objectives/turning points). Deterministic, no model calls.',
                'inputSchema': {'type': 'object',
                                'properties': {'action': {'type': 'string',
                                                          'enum': ['match', 'axis'],
                                                          'default': 'match'},
                                               'source': {'type': 'string', 'enum': ['lol'], 'default': 'lol'},
                                               'game': {'type': 'string'},
                                               'home': {'type': 'string'},
                                               'away': {'type': 'string'},
                                               'event_title': {'type': 'string'},
                                               'games': {'type': 'array',
                                                         'items': {'type': 'object'},
                                                         'description': '[{name,video,video_lowres?}] per-game full '
                                                                        'replay videos (第N局).'},
                                               'transcript_paths': {'type': 'array',
                                                                    'items': {'type': 'string'},
                                                                    'description': 'action=axis: per-game caster ASR '
                                                                                   'transcript.json in order.'},
                                               'out_dir': {'type': 'string', 'default': 'out'}},
                                'additionalProperties': False}},
 'lol_arrange': {'description': 'lol-recap step: deterministic footage arrangement. Consumes out/match.json, per-game '
                                'shots.json, and the agent-written out/outline.json (beats with kind '
                                'open/fight/kill/objective/tower/ending, game index, game-second t from the commentary '
                                'axis, cold_open flashes, highlight flags). Optional events_path = precomputed VLM '
                                'highlight spans (our detector) used to PIN each ASR beat to the precise '
                                'kill/teamfight frame (ASR+VLM). Produces out/reel.json (title card + flash montage + '
                                'one segment per beat, shot-boundary-snapped) and out/writing_brief.txt (per-beat REAL '
                                'seconds + HARD char budgets). Returns outline_invalid on out-of-order/overlapping '
                                'beats.',
                 'inputSchema': {'type': 'object',
                                 'required': ['match_path', 'outline_path', 'shots_paths'],
                                 'properties': {'match_path': {'type': 'string'},
                                                'outline_path': {'type': 'string'},
                                                'shots_paths': {'type': 'object',
                                                                'additionalProperties': {'type': 'string'},
                                                                'description': '{"1": shots_g1.json, ...}'},
                                                'events_path': {'type': 'string',
                                                                'description': 'optional VLM highlight spans json for '
                                                                               'precise event pinning (ASR+VLM).'},
                                                'script_path': {'type': 'string',
                                                                'description': 'optional writer_script.json: windows '
                                                                               'auto-extend (real footage, capped at '
                                                                               "next beat) so every beat's narration "
                                                                               'fits — story first, footage '
                                                                               'accommodates.'},
                                                'mode': {'type': 'string',
                                                         'enum': ['window', 'script'],
                                                         'default': 'window',
                                                         'description': 'script = narration-driven clipping '
                                                                        '(recommended): every sentence carries t (the '
                                                                        'game-second it narrates, from the commentary '
                                                                        'axis); footage clips are cut to fit the '
                                                                        'narration, hard sentences VLM-pinned to the '
                                                                        'action frame. Requires script_path '
                                                                        '(script_tts.json recommended). Produces '
                                                                        'reel.json with a per-sentence placement plan '
                                                                        '+ coverage_report.txt; long narration gaps '
                                                                        'become structurally impossible.'},
                                                'out_dir': {'type': 'string', 'default': 'out'}},
                                 'additionalProperties': False}},
 'lol_tts': {'description': 'lol-recap step: per-sentence TTS of the agent-written out/writer_script.json with 3-tier '
                            'emotion (rate/loudness, pitch always +0Hz). Sentence-level cache. Provider/voice from '
                            'args or configured recap narration defaults. Produces out/script_tts.json with real per-sentence '
                            'durations.',
             'inputSchema': {'type': 'object',
                             'required': ['script_path'],
                             'properties': {'script_path': {'type': 'string'},
                                            'provider': {'type': 'string', 'enum': ['auto', 'cloud', 'cloud_tts']},
                                            'voice': {'type': 'string'},
                                            'out_dir': {'type': 'string', 'default': 'out'}},
                             'additionalProperties': False}},
 'lol_render': {'description': 'lol-recap step: placement + hard-cut render + mix + QC. Fully generated Chinese '
                               'narration is the MAIN track; original broadcast audio (teamfight SFX + crowd) is '
                               'ducked low throughout as ambience (no original-caster breathing tails). Title card + '
                               'freeze-frame end card; the broadcast HUD (killfeed/scoreboard) is kept as-is so no '
                               'score overlay is drawn. over_budget fails fast before render. Output is '
                               'yuv420p/High/faststart (QuickTime-compatible). QC in out/qc.json: duration, loudness, '
                               'pix_fmt.',
                'inputSchema': {'type': 'object',
                                'required': ['reel_path', 'script_tts_path', 'outline_path'],
                                'properties': {'reel_path': {'type': 'string'},
                                               'script_tts_path': {'type': 'string'},
                                               'outline_path': {'type': 'string'},
                                               'output_path': {'type': 'string'},
                                               'out_dir': {'type': 'string', 'default': 'out'}},
                                'additionalProperties': False}}}

TOOL_SCHEMAS.update(RECAP_TOOL_SCHEMAS)


SPEECH_TRANSCRIBE_SCHEMA = {
    "description": (
        "Create a timestamped transcript for a video/audio file through the standard speech_transcribe "
        "tool. provider=auto uses the configured cloud ASR capability: an explicit remote HTTP MCP "
        "first, the host-authenticated ZCode official channel next, then the local compatibility "
        "backend. Transient "
        "network/concurrency/rate-limit/server errors retry by default; deterministic input and "
        "configuration failures do not. Long media may be split into cached overlapping chunks and "
        "merged back onto the source timeline. Silent audio returns a valid empty transcript flagged "
        "silent_audio=true."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["input_path"],
        "properties": {
            "input_path": {"type": "string"},
            "output_json": {"type": "string"},
            "provider": {
                "type": "string",
                "enum": ["auto", "cloud", "cloud_asr"],
                "default": "auto",
                "description": "ASR provider. Use auto unless a workflow explicitly requires cloud_asr.",
            },
            "language": {"type": "string", "default": "zh"},
            "chunk_seconds": {
                "type": "number",
                "exclusiveMinimum": 0,
                "description": "Maximum seconds per chunk for long media before merge.",
            },
            "timeout_seconds": {"type": "number", "exclusiveMinimum": 0},
            "poll_interval_seconds": {"type": "number", "exclusiveMinimum": 0},
            "retries": {
                "type": "integer",
                "minimum": 0,
                "maximum": 10,
                "description": "Extra retry attempts for transient ASR failures.",
            },
            "retry_count": {"type": "integer", "minimum": 0, "maximum": 10},
            "retry_backoff_seconds": {
                "type": "number",
                "minimum": 0,
                "description": "Initial exponential backoff before ASR retries.",
            },
            "work_dir": {"type": "string"},
        },
        "additionalProperties": False,
    },
}

SPEECH_SYNTHESIZE_SCHEMA = {
    "description": (
        "Generate narration or dubbing audio through the standard speech_synthesize tool. "
        "preferred_provider=auto uses the configured cloud TTS capability: an explicit remote HTTP MCP "
        "first, the host-authenticated ZCode official channel next, then the local compatibility "
        "backend. allowed_providers "
        "is a hard allowlist. Transient network/concurrency/rate-limit failures retry by default; "
        "deterministic parameter and configuration failures do not. The tool writes wav/mp3/ogg_opus "
        "audio and verifies that ffprobe reports a valid positive duration."
    ),
    "inputSchema": {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "language": {"type": "string", "default": ""},
            "voice": {"type": ["string", "integer"]},
            "speaker": {"type": ["string", "integer"]},
            "speaker_id": {"type": ["string", "integer"]},
            "voice_id": {"type": ["string", "integer"]},
            "model": {"type": "string"},
            "style_instructions": {"type": "string"},
            "speed": {"type": "number", "exclusiveMinimum": 0},
            "speech_rate": {"type": "integer", "minimum": -50, "maximum": 100},
            "pitch_rate": {"type": "integer", "minimum": -12, "maximum": 12},
            "loudness_rate": {"type": "integer", "minimum": -50, "maximum": 100},
            "sample_rate": {"type": "integer", "enum": [8000, 16000, 24000, 32000, 44100, 48000]},
            "output_format": {"type": "string", "enum": ["wav", "mp3", "ogg_opus"]},
            "format": {"type": "string", "enum": ["wav", "mp3", "ogg_opus"]},
            "enable_subtitle": {"type": "boolean"},
            "preferred_provider": {
                "type": "string",
                "enum": ["auto", "cloud", "cloud_tts", "edge", "edge_tts"],
                "default": "auto",
            },
            "allowed_providers": {
                "type": "array",
                "items": {"type": "string", "enum": ["cloud", "cloud_tts", "edge", "edge_tts"]},
            },
            "retries": {"type": "integer", "minimum": 0, "maximum": 10, "default": 3},
            "retry_count": {"type": "integer", "minimum": 0, "maximum": 10},
            "retry_backoff_seconds": {"type": "number", "minimum": 0, "default": 3},
            "sample_mode": {"type": "boolean", "default": False},
            "output_path": {"type": "string"},
        },
        "additionalProperties": False,
    },
}


def _scrub_public_schema_text(value):
    """Last line of defence over the published tool schemas.

    The schema literals above are already vendor-neutral; this pass exists so a
    future edit cannot reintroduce a vendor name into a tool description that
    every client displays. Same intent as speech_service._VENDOR_PATTERNS — the
    vendor strings here are the things being removed, not things being shipped.
    """
    if isinstance(value, dict):
        return {key: _scrub_public_schema_text(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub_public_schema_text(item) for item in value]
    if not isinstance(value, str):
        return value
    replacements = [
        (r"seed[_ -]?asr", "cloud_asr"),
        (r"seed[_ -]?audio", "cloud_tts"),
        (r"Seed ASR", "cloud ASR"),
        (r"Seed Audio", "cloud TTS"),
        (r"Volcengine|volcengine|火山引擎|火山|豆包|ByteDance|bytedance", "cloud speech service"),
        (r"VE_SEED_[A-Z0-9_]+", "compatible legacy speech credential"),
        (r"volc\.[A-Za-z0-9_.-]+", "cloud_resource"),
        (r"openspeech\.bytedance\.com", "cloud speech endpoint"),
    ]
    out = value
    for pattern, replacement in replacements:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    return out


TOOL_SCHEMAS = _scrub_public_schema_text(TOOL_SCHEMAS)
TOOL_SCHEMAS["speech_transcribe"] = SPEECH_TRANSCRIBE_SCHEMA
TOOL_SCHEMAS["transcribe"] = {
    **SPEECH_TRANSCRIBE_SCHEMA,
    "description": "Compatibility alias for speech_transcribe. Prefer speech_transcribe for new integrations.",
}
TOOL_SCHEMAS["speech_synthesize"] = SPEECH_SYNTHESIZE_SCHEMA
TOOL_SCHEMAS["tts_generate"] = {
    **SPEECH_SYNTHESIZE_SCHEMA,
    "description": "Compatibility alias for speech_synthesize. Prefer speech_synthesize for new integrations.",
}
for _name in ("synthesize_narration", "soccer_tts", "lol_tts"):
    _schema = TOOL_SCHEMAS.get(_name)
    if isinstance(_schema, dict):
        _props = ((_schema.get("inputSchema") or {}).get("properties") or {})
        if isinstance(_props.get("provider"), dict):
            _props["provider"]["enum"] = ["auto", "cloud", "cloud_tts", "edge", "edge_tts"]
