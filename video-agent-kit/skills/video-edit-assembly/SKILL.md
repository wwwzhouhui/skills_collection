---
name: video-edit-assembly
description: Specialized workflow for multi-material video assembly. Use after video-edit-agent classifies a task as combining, selecting, ordering, de-duplicating, or shaping multiple user-provided videos/audio/images into one coherent finished video, montage, recap, social-media cut, or story.
---

# Video Edit Assembly

Use this skill for multi-material assembly tasks: the user provides a batch of materials and asks for a coherent finished video. The goal is not to use every file; the goal is to choose the right materials, order them intentionally, preserve important speech, avoid repetition and off-topic shots, and deliver a rendered preview that passes the common video-edit contract.

Follow the `video-edit-agent` common file contract and completion bar. This skill adds the assembly-specific decision process.

## Assembly Principles

1. **Classify before cutting.** Multi-material editing starts with an inventory and grouping pass, not with a timeline.
2. **Use source evidence.** Selection decisions must be based on `inspect_media`, transcript when speech matters, and visual contact sheets. Do not infer content from filenames alone.
3. **Not all materials should be used.** Drop duplicates, low-quality clips, off-topic material, broken speech fragments, and shots that weaken the requested story.
4. **Preserve key speech.** If a used source contains speech, avoid cutting important sentences mid-thought. If preserving a sentence would hurt the edit, either keep the complete sentence or drop that spoken segment entirely and explain the tradeoff.
5. **Respect task constraints.** Duration, aspect ratio/platform, tone, pacing, special effects, subtitles, music, and speech protection should be parsed before planning. Record hard constraints and soft preferences in `out/media.json` or `out/report.md`.
6. **Prefer coherent structure over file order.** Build an editorial arc from content: hook, setup, development, contrast/turn, climax, resolution, outro, or another structure fitting the task.
7. **Use conservative assumptions.** In automated data runs, do not ask for confirmation unless the task is impossible. Explain assumptions in `out/report.md`.

## Assembly Workflow

Run these phases in order.

### Phase 1: Discover And Parse Constraints

Read `materials_manifest.json` when present; otherwise scan the current working directory, excluding generated/runtime directories. Build a material inventory with:

- file path and type: video, audio, image, other;
- duration, resolution, fps, audio presence, obvious technical risk;
- user-mentioned files/folders if any;
- inferred task type, target duration, target platform/aspect ratio, tone, pacing, effects/subtitle/music expectations;
- hard constraints vs soft preferences.

Write or later update `out/media.json` with the inventory. For multiple sources, write per-source probes to `out/media/<source>.json`.

### Phase 2: Inspect Sources

For every video/audio source that may participate, call `inspect_media`.

For sources with audio when speech may affect editing, call `transcribe` into `out/transcripts/<source>.json`. Run ASR for all audio-bearing sources when the user says not to cut speech, asks for dialogue-aware editing, or the content type likely includes speech. Silent or no-speech transcripts are valid and should be recorded.

For each source video that may be used or needs a keep/drop decision, call `video_ingest` with a distinct output path:

```text
out/ingest/<source_stem>.json
```

Read the returned contact-sheet images. If a source is clearly unusable after metadata alone (corrupt, wrong file type, zero duration), record that reason without visual planning. Otherwise do not reject video content without visual evidence.

Use `analyze_media` only as a deterministic hint for scene boundaries, black ranges, silence ranges, or candidate segments. It does not replace visual inspection.

### Phase 3: Group, Score, And Select

Before timeline writing, create a source selection summary in `out/media.json` or a separate review artifact referenced by `out/report.md`. Include:

- `material_groups`: duplicates, same scene/take, same topic, off-topic, low-quality, spoken/interview, B-roll, title cards, stills/images, audio-only;
- `selection_summary`: selected, rejected, maybe/backup;
- keep/drop reasons grounded in visual/audio evidence;
- speech constraints: which spoken ranges must be preserved or avoided;
- candidate ranges with source timestamps and editorial purpose;
- quality risks: shaky footage, black frames, low resolution, wrong aspect ratio, source jump cuts, loud audio, silence.

For duplicate or near-duplicate material, keep the best version based on stability, completeness, composition, audio, and usefulness. Do not include multiple near-identical clips just to reach target duration unless the user explicitly asks for repetition.

For off-topic material, drop it even if it helps duration. If the requested duration cannot be reached without weak material, prefer a shorter strong cut and explain the limitation.

### Phase 4: Decide Format And Structure

Choose sequence/canvas early:

- If the user asks for vertical/social/mobile/reels/tiktok/shorts, prefer a 9:16 canvas unless the material would be harmed and explain the tradeoff.
- If the user asks for horizontal, documentary, presentation, archival, or source fidelity, keep a landscape canvas when appropriate.
- If the user only says "social media" and materials are mixed, choose the aspect ratio that best preserves subjects and record the assumption.

Define an editorial structure before writing clips. Common assembly structures:

- hook -> context -> development -> climax -> resolution;
- before -> process -> result;
- wide -> medium -> close detail -> payoff;
- problem -> evidence -> answer;
- calm opener -> activity -> peak -> closing card;
- chronological sequence when chronology matters.

Record the chosen structure in `project`, `markers[]`, clip `beat`, and `out/report.md`.

### Phase 5: Build Project Timeline

Write `out/timeline.json` as a project-style timeline with:

- `project`: task, assumptions, selected strategy, rejected-material policy;
- `sequence` or `output_canvas`: width, height, fps, duration target, aspect-ratio/platform notes;
- `assets[]`: all source and derived assets, including rejected assets with roles/reasons when useful;
- `tracks[]`: at least one typed `video` or `main` track. Add `audio`, `music`, `voiceover`, `subtitle`, `overlay`, or `chapter_card` tracks only when required by the task or clearly justified.

Each video clip needs `source`, `start`, `end` or `duration`, optional `timeline_start`, and a `reason` explaining its editorial role. Use `beat` for the structural role. Use `volume`, `speed`, `opacity`, `transition_in`, and `transition_out` only when meaningful.

Do not silently claim unsupported advanced NLE features were rendered. If an idea is only metadata, make that clear in `out/report.md`.

### Phase 6: Validate, Render, QC, And Self-Review

Run:

1. `validate_timeline(timeline_path="out/timeline.json", output_json="out/timeline_validation.json")`
2. `render_preview(timeline_path="out/timeline.json", output_path="out/preview.mp4")`
3. `qc_preview(video_path="out/preview.mp4", timeline_path="out/timeline.json", output_json="out/preview_qc_report.json")`

Then visually self-review `out/preview.mp4` using `video_ingest` with `output_json="out/preview_ingest.json"` when needed. Check:

- the final video follows the requested structure and tone;
- selected materials match the user's subject;
- repeated or off-topic shots were not accidentally included;
- important speech is not cut mid-sentence;
- transitions and cut boundaries are clean;
- aspect ratio/crop keeps important subjects visible;
- audio continuity and loudness are acceptable;
- QC warnings are fixed or explicitly justified.

If repair is needed, use `timeline_diff`, then rerun validation, render, and QC.

### Phase 7: Report

Write `out/report.md` with:

- user task and assumptions;
- final output path, duration, resolution, fps, and audio state;
- selected structure and timeline summary;
- selected and rejected material decisions;
- speech preservation decisions;
- QC status and any warnings/errors;
- repair loop summary if any;
- unresolved risks or limitations.

## Assembly-Specific Completion Bar

In addition to the global completion bar, the assembly task is complete only when:

- every relevant video source has either a source observation package or a recorded reason why visual inspection was unnecessary/impossible;
- `out/media.json` summarizes source groups and keep/drop decisions;
- the timeline uses project-style `assets[]` and `tracks[]`;
- selected clips have editorial `reason` and, when useful, `beat`;
- rejected/unused important materials are explained in `out/report.md` or `out/media.json`;
- the final report states whether the result met duration/aspect/tone/speech constraints or explains any deliberate deviation.
