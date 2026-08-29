---
name: video-speech-workflows
description: Consolidated single-source voiced-video workflows for speech condensing, talking-head subtitles, and end-to-end caption/edit orchestration. Use when video-edit-agent routes a single voiced video to mode=speech-condense, mode=talking-head-subtitles, or mode=video-pipeline.
---

# Video Speech Workflows

This skill contains the specialized single-source speech/video workflows that sit beside `video-edit-assembly`.

## Route Modes

Choose exactly one mode from the caller's args, then read and follow the matching workflow document:

| Mode | Workflow |
|---|---|
| `speech-condense` | [workflows/speech-condense.md](workflows/speech-condense.md) |
| `talking-head-subtitles` | [workflows/talking-head-subtitles.md](workflows/talking-head-subtitles.md) |
| `video-pipeline` | [workflows/video-pipeline.md](workflows/video-pipeline.md) |

If the args do not name a mode, infer the narrowest matching one:

- Use `speech-condense` for one long unscripted recording that must be shortened, tightened, or cut to a target length.
- Use `talking-head-subtitles` for straight captioning, subtitle repair, speaker-labelled captions, karaoke highlighting, bilingual lines, or subtitle placement/legibility work on one rendered video.
- Use `video-pipeline` when a single voiced video needs an end-to-end stage plan that may combine condensing/editing with captions, speaker differentiation, karaoke, translation, or terminology notes.

## Boundaries

- Multi-material source packs stay in `video-edit-assembly` or the common `video-edit-agent` workflow first. Subtitle the rendered output afterward so cue times match the final video.
- The selected workflow's file contract and verification rules are authoritative for its own outputs.
- `video_watch_segment(video_path=...)` can directly inspect tight windows without a prior full `video_ingest`; reserve full ingest for workflows that genuinely need dense whole-video contact sheets.
