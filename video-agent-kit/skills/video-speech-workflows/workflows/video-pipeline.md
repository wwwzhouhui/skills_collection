---
name: video-pipeline
description: Orchestrate the video-agent-kit capabilities from one user prompt. Use when a user supplies a voiced video and asks for an end-to-end result that may combine editing or condensing with captions, multi-speaker differentiation, karaoke word highlighting, bilingual translation, or concise terminology explanations. Also use for underspecified requests such as “process this video” or “add suitable subtitles”, where the driving model must select compatible stages and rich-subtitle features from the material instead of requiring the user to name every tool.
---

# Video Pipeline

Turn one video plus one natural-language request into a small, auditable pipeline. Reuse the existing skills and MCP tools; do not duplicate or modify their implementations.

## Canonical procedures

Load only the procedures selected by the route:

- For caption construction, placement, rendering, and verification, read and follow [talking-head-subtitles](talking-head-subtitles.md).
- For speech condensing, read and follow [speech-condense](speech-condense.md), then caption its output if requested.
- For other timeline edits, read and follow [video-edit-agent](../../video-edit-agent/SKILL.md), then caption the rendered output if requested.

The selected canonical skill's hard rules and file contract remain authoritative. This skill only decides composition and the hand-off between stages.

## Plan from the prompt

The first task artifact must be `out/pipeline_plan.md`. Write a provisional plan from the prompt **before calling `transcribe`, `subtitle_scout`, `video_ingest`, or any render tool**. Do not wait for ASR or visual evidence to create it; mark evidence-dependent choices as `auto -> pending`, then update the same plan after intake. `inspect_media` may run first only when the file cannot otherwise be identified.

Include:

- source video and the user's request;
- final deliverable;
- ordered stages;
- one row for `edit`, `condense`, `captions`, `speaker_labels`, `karaoke`, `translation`, and `term_notes`, each marked `on`, `off`, or `auto -> on/off` with a short reason;
- intended working video and transcript at the caption stage;
- any assumption or downgrade.

Make conservative decisions without waiting for confirmation. Do not enable every effect just because it exists.

### Guard against existing dialogue subtitles

The normal burn-in route expects a subtitle-free source. After the provisional plan exists, inspect the media streams and representative frames before building captions:

- Treat an embedded subtitle stream or recurring dialogue text in the caption band as existing subtitles. Logos, watermarks, scoreboards, and occasional name lower-thirds are graphics, not dialogue subtitles, but placement must avoid them.
- Do not burn a second dialogue layer over existing soft or hard subtitles by default. In an interactive task, request the subtitle-free source. In an unattended task, produce recoverable sidecar subtitles and explain why burn-in was withheld.
- Only replace or cover existing dialogue subtitles when the user explicitly asks for replacement. Route that as an edit with its own visual verification; never present it as the standard caption-only path.
- Record the source-subtitle check and its evidence in `out/pipeline_plan.md` and `out/report.md`.

Use these routing rules:

1. Turn on an edit or condense stage only when the prompt asks for a content or timeline change. Run it before captions.
2. Turn captions on when the prompt asks for subtitles, translation, speaker differentiation, karaoke, or terminology notes. For an otherwise underspecified voiced, uncaptioned video request, default to readable captions.
3. Treat multi-speaker differentiation as a correctness feature, not decoration. Turn it on whenever the material actually contains multiple speakers, even if the prompt merely says “add subtitles”.
4. Turn translation on when the prompt requests a target language or clearly identifies an audience whose language differs from the source. Do not invent a target language.
5. Turn karaoke on for an explicit request, or for a clearly punchy short-form/lyric treatment where word highlighting supports the requested style. Leave it off for dense interviews, formal material, or multi-layer subtitles unless explicitly requested.
6. Turn term notes on when requested, or when a small number of unexplained specialist terms would otherwise block the intended audience. Notes must add comprehension, not decoration.

If the prompt explicitly chooses a feature, honour it unless the required evidence or timing data is unavailable. Record the downgrade instead of silently substituting a weak approximation.

## Build the stage graph

Use this order:

```text
prompt plan
  -> optional edit/condense
  -> select final caption input and its transcript
  -> audit speakers when needed
  -> scout placement and correct transcript
  -> build caption cues with build-time features
  -> add cue-level translation/notes
  -> render
  -> deterministic QC + visual/timing verification
  -> report
```

Avoid redundant ASR:

- Caption-only: use the source video and `out/transcript.json`.
- Condense then caption: use `out/condensed.mp4` and `out/condensed_transcript.json`; do not transcribe the condensed video again.
- Other timeline edit then caption: use a transcript remapped by that workflow when one exists. Otherwise transcribe the edited output, because source timestamps no longer match.

Never build captions on the source and then edit the video underneath them.

## Audit and identify speakers

After transcription, inspect actual `speaker` fields and the dialogue. Do not trust `n_speakers` alone.

When there are multiple speakers, when labels appear collapsed, or when the prompt expects a conversation:

1. Run `diarize_audit(transcript_path=...)`.
2. Batch its relevant `watch_windows` through `video_watch_segment(video_path=...)` and decide who is speaking from mouth movement, framing, and turn-taking.
3. Use `video_read_frames` on the original-resolution name-plate or lower-third region when a displayed name must be read. A contact sheet is not reliable evidence for tiny text.
4. Verify self-introductions and hand-offs against the person actually speaking. Never turn a merely mentioned name into a speaker identity.
5. If labels are wrong or collapsed, call `diarize_relabel` with time-range assignments, then audit again.

Use one stable identity for the same person across the full video. Prefer a verified real name; otherwise use stable neutral labels such as `主持人`, `嘉宾`, `说话人 A`, and `说话人 B`. An honest neutral label is better than a guessed name.

Build with:

```json
{
  "style": {
    "speaker_labels": true,
    "speaker_colours": "auto"
  },
  "speaker_names": {
    "<ASR label>": "<verified display name>"
  }
}
```

The built-in colour-blind-safe palette assigns a stable colour by first appearance. Do not hand-edit colours per cue. If the video has only one real speaker, leave labels off.

## Compose rich subtitle features

### Karaoke

Pass `style.karaoke=true` to `subtitle_build`; it cannot be added faithfully after building. Prefer `speech_transcribe(provider="cloud_asr")` and confirm that words have real `start`/`end` times. If only segment timing is available, disable karaoke unless the user explicitly accepts estimated timing, and record the limitation.

### Translation

After `subtitle_build`, add `translation_lines` to each dialogue cue in `out/subtitles.json`. Translate cue by cue, preserving meaning, speaker intent, names, numbers, and terminology. Keep each translation attached to the same time window as its source cue. Do not add translations to annotation cues.

### Terminology explanations

Add a separate cue with `role="annotation"` and its own short time window near the term's first relevant occurrence. Keep the explanation brief, audience-appropriate, and factually supported. Prefer one useful note over repeated definitions; avoid stacking simultaneous notes.

### Combination rules

- Speaker labels and translation compose normally.
- Term notes stay at the top and dialogue stays in the caption band.
- Karaoke can compose technically with other features, but multi-speaker + bilingual + karaoke is visually dense. Use all three together only when the prompt explicitly calls for that treatment and the evidence frames remain readable.
- Every optional layer must survive the same safe-area and contrast decision made from `subtitle_scout`.

## Verify the composed result

Follow the canonical caption QC and repair loop. In addition, explicitly verify:

- each speaker keeps the same name and colour across turns;
- speaker changes occur at the right boundary;
- every translation matches its source cue and remains within the safe width;
- notes do not collide with faces, titles, or other notes;
- karaoke highlighting tracks spoken words in high-fps windows.

Add these as F/T checkpoints in `out/subtitle_plan.md` and append their evidence to `out/subtitle_verify.md`. Run `subtitle_qc` on the burned result and treat its errors as blockers.

Finish `out/report.md` with the selected route, enabled and disabled features, speaker naming basis, translation target, notes added, downgrades, QC status, and final artifact paths.
