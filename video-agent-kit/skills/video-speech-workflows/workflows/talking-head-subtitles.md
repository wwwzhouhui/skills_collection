---
name: talking-head-subtitles
description: Add accurate, readable, correctly placed subtitles to a talking-head / voice-over (口播) video. Use for captioning a single-speaker piece to camera, adding burned-in captions to a short-form vertical video, subtitling a monologue or narration clip, or fixing subtitles that are mistimed, mis-segmented, unreadable, or covering the frame. Covers ASR, transcript correction, cue segmentation, styling, burn-in, and evidence-based verification.
---

# Talking-Head Subtitles

Subtitle a single-speaker video so the captions are **accurate, readable, and out of the way**. The job is finished when you have looked at the rendered frames and can point to the evidence for each of those three claims — not when the encoder exits zero.

## What Makes This Hard

The pipeline is short, so it is tempting to treat it as mechanical: transcribe, split, burn. Three things go wrong when you do.

- **ASR is confidently wrong about the words that matter most.** Names, products, jargon and acronyms are exactly what a 口播 video is about, and exactly what ASR mangles. A subtitle repeats the error in 60-point type.
- **Timing is inherited, not given.** `transcribe` returns segment-level timestamps — one segment can be a ten-second run of speech. Cue times inside a segment are derived, and derived timing drifts.
- **The frame already has content.** The default caption position is a guess. Under it may be the speaker's chin, a lower-third, a logo, or the platform's own UI. You cannot know without looking.

Every rule below exists to force one of those three into the open.

## Hard Rules

1. **Look at the frame before you decide where text goes.** Run `subtitle_scout` (or `video_ingest` for a dense full-video pass) and read the sheets. Never accept the preset's margins — or its default outline over a bright band — without having seen what occupies that band of the frame.
2. **Read the transcript against the video before segmenting.** Fix what ASR got wrong, and record every fix with its justification in `out/transcript_edits.md`. If nothing needed fixing, say so explicitly — an empty file is not a verdict.
3. **Never invent transcript content.** A correction must be supported by the audio, by on-screen text, or by unambiguous context. If a word is genuinely unintelligible, leave the ASR output and log it as a known risk.
4. **Read the cue table `subtitle_build` returns before you render.** It is the cheapest possible review of segmentation quality, and it is text.
5. **Read every evidence frame `subtitle_qc` returns.** Not the first few. Each one is the only proof that its cue actually looks right.
6. **Timing claims need a window, not a frame.** A still cannot show whether a cue changes in the speaker's pause. Use `video_watch_segment` on the rendered video for those.
7. **Verification is append-only.** Every checkpoint's verdict goes into `out/subtitle_verify.md` as a new line. Never rewrite an old line; the last line for a checkpoint is its current state.
8. **Do not wait for confirmation.** If the task is underspecified, choose conservatively, and record the assumption in `out/report.md`.

## File Contract

Everything under `out/` relative to the project directory. Conversation text is not progress.

| File | What | When |
|---|---|---|
| `out/media.json` | Source probe from `inspect_media`. | First. |
| `out/transcript.json` | ASR transcript with per-segment times. | Before anything visual. |
| `out/transcript_edits.md` | Every correction made to the ASR text, with its justification — or an explicit "no corrections needed". | Before `subtitle_build`. |
| `out/subtitle_scout.json` | Task-shaped placement scout: caption-band strip, shot count, measured band luminance, contrast recommendation. **This satisfies the visual-inspection requirement on its own.** | Before choosing style/placement. |
| `out/video_ingest.json` | Full-video 2fps contact-sheet sweep. Optional — only when a dense pass is genuinely needed (moving speaker, content between cuts); skip it on short/static clips, it is expensive. | Only if needed. |
| `out/subtitle_plan.md` | Style choice with reasons drawn from the frame, the safe area, and the checkpoint list. | Before `subtitle_build`. |
| `out/subtitles.json` | Cue package (plus sidecar `.ass` / `.srt`). | Before render. |
| `out/subtitled.mp4` | Burned-in output. | Before verification. |
| `out/subtitle_qc_report.json` | Deterministic QC over the current cues and output. | After render. |
| `out/subtitle_verify.md` | Append-only checkpoint verdict log. | Throughout verification. |
| `out/report.md` | Closeout: assumptions, outputs, parked items, residual risk. | Last. |

## Workflow

### Phase 1: Intake

`inspect_media(input_path)` — record duration, resolution, orientation, frame rate, audio streams.

`speech_transcribe(input_path)` — this is a standard step. `provider=auto` uses cloud ASR. Continue without a transcript **only** if cloud ASR is unavailable; then record the limitation and stop, because there is nothing to subtitle.

Then sanity-check the transcript before trusting it:

- Do the segment times span the speech, or does the tail cut off?
- Is `n_speakers` 1 as expected? More than one on a solo piece means diarization split one voice, which is harmless here but tells you the audio is noisy.
- Does the text read as fluent speech, or are there hallucinated loops and repeated phrases?

### Phase 2: See The Frame

`subtitle_scout(video_path, preset=...)` is the task-shaped way to see the frame, and for most clips it is all you need: it samples one frame per shot, returns a downscaled overview strip (for composition and faces) plus a native-width strip of just the caption band (for what the text will sit on), and — because contrast is the one legibility failure a thumbnail hides — it *measures* the band luminance numerically and hands back a concrete contrast recommendation. Read both strips; do not decide placement from the numbers alone. The scout satisfies the visual-inspection contract on its own.

Add a full `video_ingest(video_path, transcript_path="out/transcript.json")` **only when you actually need a dense, evenly-spaced pass** — e.g. the speaker moves across many framings, or you must inspect content between shot cuts. It samples the whole video at 2 fps, which on a long clip is a large number of frames (expensive, and it has timed runs out), so do not run it reflexively on top of the scout for a short or static piece. When you do run it, read every sheet.

You are looking for the things that decide placement and style — this is not a formality:

- **Where is the speaker's face and chin?** Captions must not cover the mouth.
- **What already occupies the lower third?** Existing burned-in captions, a lower-third name plate, a logo, a progress bar, a watermark.
- **Is the framing stable?** If the speaker moves or the shot cuts between framings, the safe band is the intersection across the whole video, not one frame. `subtitle_scout` reports the shot-cut count so you know how many distinct framings to reconcile.
- **What is the background luminance behind the caption band, and does it change across shots?** This is the contrast question, and it is the one the scout answers with a number and a recommendation.
- **Vertical or landscape?** Vertical short-form needs a much higher bottom margin, because the platform draws its own UI over the bottom ~12–15% of the frame.

**Acting on the contrast recommendation.** The scout classifies the band as low / medium / high contrast risk and, when there is a risk, returns a drop-in `style` override:

- **high** — some frame is bright behind the text, or the band swings bright-to-dark across shots. White-on-outline text washes out on the bright frames, and a fixed outline that reads on the dark ones is not the same guarantee on the bright ones. The recommended fix is `readability: box` — a semi-transparent band hugging the text that holds the same contrast on every frame regardless of what is under it. Confirm it on the brightest band-strip row before committing, and keep it only if the footage needs it — a box on uniformly dark footage is heavier than it has to be.
- **medium** — mid-to-bright band; `readability: heavy_outline` usually suffices. If any band-strip row still looks marginal, step up to `readability: box`.
- **low** — consistently dark; the preset outline reads cleanly and no override is needed.

`readability` is a single style knob (`box`, `opaque_box`, `heavy_outline`, or the default `outline`) that expands to the four coordinated ASS fields a good box needs — pass just `{"readability": "box"}` rather than hand-setting `border_style`, `outline_colour`, padding and shadow, which is easy to get subtly wrong. Any field you also set by hand still wins, so `{"readability": "box", "outline": 14}` gives a box with 14px padding.

The recommendation is evidence, not a verdict: it is the placement of a measurement next to the frame it came from. Pass the override verbatim, escalate `box`→`opaque_box` on extreme brightness, or reject it after looking — but if you reject a high-risk recommendation, say why in the plan, because a still will later be asked to prove the text is legible.

**Acting on the font-size recommendation.** The scout also returns `font_recommendation`: it compares the preset's resolved font size against a viewing-context target band (phone-first vertical short-form reads best around 4.5–5.8% of frame height; a landscape 16:9 caption around 3.6–4.8%) and, when the preset default falls outside that band, hands back a concrete `{"font_size": N}` override. Do not just inherit the preset size — a preset default is a starting point, and the vertical one in particular renders small on a phone. Two-step it: (1) if the scout says `too_small`/`too_large`, apply the suggested `font_size` (or your own judgement of it); (2) **confirm against the cue table `subtitle_build` returns** — if lines are short with lots of empty width you can push larger, but if many cues start condensing (`font_scale < 1`) or hit the per-line character cap, the font is too big and wrapping will suffer, so ease back. Size and wrapping are one decision: the right size is the largest that still lets the segmenter wrap cleanly without condensing most cues.

If the lower third is unusable, decide where the captions go instead (higher margin, top alignment) and say why in the plan.

### Phase 3: Correct The Transcript

Read the transcript text against what you saw and heard. Fix, and log each fix in `out/transcript_edits.md` with the reason:

- proper nouns, brand names, people's names;
- technical terms and acronyms — check capitalisation (`AGI`, not `agi`);
- homophone errors, which are the dominant Chinese ASR failure and the easiest to spot from context;
- mixed-script spacing, and sentence-final punctuation ASR dropped, since punctuation drives segmentation;
- hallucinated repeats.

Edit `out/transcript.json` in place, keeping the timing fields untouched. **Do not** edit timings here; that is what pause snapping is for.

### Phase 4: Plan

Write `out/subtitle_plan.md`. It records the decisions and, crucially, the list of claims you will later have to prove. The choices below are yours to make from the evidence — this is guidance on what to weigh, not a lookup table.

1. **Style choice, justified from the frame.** The presets are starting points, not categories to sort the video into. What actually decides the look:

   - **Orientation and platform.** Vertical short-form wants a high bottom margin (the platform paints UI over the bottom ~12–15%) and reads well as one large line; landscape has room for two smaller lines.
   - **Register.** A punchy monologue suits a bold single line with punctuation dropped; a formal or information-dense piece suits conventional two-line captions with punctuation kept.
   - **Script and pace.** Latin text reads far faster per character than CJK and is capped by character count long before pixel width, so it needs a different reading-speed budget and line length — that is why `broadcast_en` exists apart from `broadcast`.

   `shortform_zh`, `broadcast`, and `broadcast_en` are the built-in points in that space. Pick the closest and tune it with overrides rather than forcing the video to fit a preset. Name the frame evidence that led you there; if you overrode a preset default, say what in the frame required it.

2. **Safe area.** The vertical band captions may occupy, and what is above and below it.

3. **Style overrides and why**, each tied to something you saw — a raised `margin_v` to clear a logo, `readability: box` for a bright or variable band (the scout will have flagged this), `max_lines: 2` for dense speech, a lower `max_cps` if the speaker is fast.

4. **The checkpoint list — what you will verify, and how.** List the claims that, if false, would make you reject the deliverable: at minimum, that every cue's wording is right, that the captions are placed and legible without covering anything that matters, and that they track the speech without flicker or clipped boundaries. Cover the whole video, not a sample — a wrong word or an overflow on one unchecked cue is still a defect you shipped.

   For each claim, note how you will settle it, because that dictates the tool. The operative question is whether a single still can prove it:

   - if yes, it is **frame-provable** (tag it **F**) — text correctness, overflow, legibility, occlusion, line count — and a QC evidence frame settles it;
   - if it depends on motion or timing — speech sync, whether a boundary lands in a pause, flicker between cues, a cue flashing past unreadably — a still cannot prove it and you need a window (tag it **T**, verified with `video_watch_segment`).

   When unsure, treat it as needing a window; a frame that happens to look right can hide a timing fault. Tag each checkpoint F or T so Phase 7 knows which tool to reach for.

### Phase 5: Build Cues

`subtitle_build(transcript_path, video_path, preset, style)`.

The tool handles what can be decided by rule — word-boundary breaks via jieba, punctuation-aware break scoring, a taboo on stranding conjunctions and particles, reading-speed and line-fill trade-offs solved as a dynamic program, and boundary times snapped onto silences detected in the audio.

What it cannot decide is whether the wording and the break points are *right for this script*. So **read the returned cue table** and check:

- Does any cue split a phrase that should stay together — a name, a number and its unit, a fixed expression?
- Does any cue end on a word that leaves the viewer hanging?
- Does the reported `snapped_boundaries / internal_boundaries` ratio look low? A low ratio means the audio had no pause near the cuts, so timing there is derived and deserves a T checkpoint.
- Is any cue condensed (`font_scale < 1`)? That is fine in small doses; a lot of them means the font is too large for this script.

To change wording or a break, edit `out/subtitles.json` directly and re-render — `subtitle_render` always regenerates the ASS from `cues[]`, so hand edits take effect. Keep cue times monotonic and non-overlapping.

### Phase 5b (optional): Richer subtitle looks

Plain captions are the default and are right for most clips. Four richer treatments are available when the material calls for them — decide from the content, not by habit, and only reach for one when it earns its place. Each is driven either by a `style` flag at build time or by fields you add to the cues in `out/subtitles.json` before rendering.

- **Multi-speaker labelling.** When the transcript has more than one speaker (cloud ASR clusters them and gives each a label), build with `style.speaker_labels=true` so each cue is prefixed with the speaker and tinted a stable colour. Give real names when you can get them: speakers often introduce themselves ("I'm Connor Nixon…") or are named on screen — read that and pass `speaker_names={"<asr-label>": "<real name>"}` rather than settling for a generic tag. Fall back to the raw label only when no name is recoverable.
- **Karaoke word-highlight.** For a lyric/music-video feel where each word lights up as it is spoken, build with `style.karaoke=true`. Sync quality lives or dies on **word-level timestamps**, so this treatment requires a transcript whose `segments[].words[]` carry real per-word `start`/`end`; the highlight then lands exactly on each word's spoken interval, unaffected by background music. Without word timings the sweep falls back to an even, character-weighted estimate confined to each cue's voiced window; it reads acceptably on short, clean cues but **visibly lags the voice whenever a background-music bed is present** (energy-based silence detection cannot find the true speech edges under the music, so the sweep is spread over too long a span). Use karaoke for punchy short-form, not dense narration where it distracts.
- **Bilingual subtitles.** To show a translation under the original, add a `translation_lines` list (the translated lines) to each caption cue and re-render; it renders as a smaller, dimmer block locked to the same time window, so the two languages stay aligned with each other and with the audio. You produce the translation — keep each translated cue's meaning matched to the original cue it sits under, so the two lines correspond line-for-line rather than drifting. Any translation line wider than the usable width is wrapped for you at word boundaries (measured at the smaller translation font, capped at the caption's line budget), so a long translation reflows instead of overflowing — you still read the frame to confirm the reflow reads well.
- **Explanatory notes.** When a term, acronym, piece of jargon or slang would leave a viewer lost, you may add a separate note cue: an extra cue with `role="annotation"` and its own time window, which renders at the top of the frame so it does not fight the dialogue. Use them sparingly, only where genuinely needed, and keep them short. This is a judgement call — add one when the content is opaque without it, not as decoration.

These compose (a bilingual multi-speaker track is fine). Whatever you enable, it still has to pass the same verification: read the frames, confirm nothing overflows or collides, and that the timing tracks the speech.

### Phase 6: Render

`subtitle_render(video_path, subtitles_path, output_path="out/subtitled.mp4", mode="burn")`.

Use `mode="both"` when the deliverable should also carry a toggleable subtitle track. A successful render proves the filter graph ran; it proves nothing about the result.

### Phase 7: Verify

`subtitle_qc(video_path="out/subtitled.mp4", subtitles_path="out/subtitles.json")`.

Treat errors as blockers and warnings as review items you must consciously accept or fix. Overflow, overlap and coverage loss are always errors; a coverage error means segmentation silently dropped speech and must never be waved through.

Then do the two kinds of verification the checkpoints demand.

**F checkpoints** — read every evidence frame. For each, compare the label (cue index and expected text) against the pixels: is that exactly the text, fully inside the frame, readable against that background, clear of the mouth and of any graphic? Raise `max_evidence_frames` when there are more cues than frames sampled, so every cue gets seen.

**T checkpoints** — `video_watch_segment(video_path="out/subtitled.mp4", ...)` at high fps over tight windows. Batch windows into one call with `segments=[...]`. Windows worth spending:

- the first cue's appearance and the last cue's disappearance;
- two or three cue boundaries, preferring ones `subtitle_build` reported as *not* snapped to a pause;
- any cue whose QC warning was about duration or reading speed;
- any boundary where you suspect the caption changes while a word is still being spoken.

Note that ingesting `out/subtitled.mp4` makes it the active video; pass the original path explicitly if you need to go back to the source.

Append one line per checkpoint to `out/subtitle_verify.md`: the checkpoint id, its F/T tag, the evidence you used (frame or window), and the verdict — pass, fail, or parked.

### Phase 8: Repair Loop

For each failure, fix at the level that caused it:

| Symptom | Fix at |
|---|---|
| Wrong words on screen | the transcript, then rebuild |
| Bad break point or phrasing | `out/subtitles.json` cue text, or a `style` change, then rebuild/re-render |
| Caption covers a face or graphic | `style.margin_v` / `alignment`, then rebuild |
| Illegible against background | `style.readability` (`box` / `opaque_box` / `heavy_outline`), then re-render |
| Line overflows | `style.font_size` down or `max_lines` up, then rebuild |
| Cue changes mid-word | `snap_window_seconds` up, or `silence_db` / `min_silence_seconds` retuned for this audio, then rebuild |
| Reading speed too high | `max_cps` down so the segmenter prefers shorter cues, then rebuild |

Re-run QC and re-verify the affected checkpoints after every change. Append the new verdicts; do not edit the old lines.

**Stop-loss.** Three repair rounds on one checkpoint without resolution, and you may park it: append a `parked` verdict stating what you tried and what remains wrong. Parking is for genuine dead ends — a checkpoint you never actually verified may never be parked.

### Phase 9: Report

Write `out/report.md`: the task, the style chosen and why, transcript corrections made, QC status, every parked checkpoint with its reason, and residual risks.

## Tool Policy

- `inspect_media` — required for the source.
- `transcribe` — required. Segment-level timestamps only; do not expect word timing.
- `subtitle_scout` — the task-shaped way to settle placement and contrast before styling: caption-band strip, shot count, measured band luminance, and a drop-in contrast override. Its band strip and recommendation are a required read.
- `video_ingest` — the dense full-video pass for a moving speaker or many framings.
- `video_watch_segment` — the only way to settle a T checkpoint. Batch windows into one call.
- `subtitle_build` — produces the cues; its returned table is a required read.
- `subtitle_render` — burn-in and/or soft mux; regenerates the ASS from the JSON every time.
- `subtitle_qc` — required before accepting; its evidence frames are a required read.
- `render_preview` / `validate_timeline` / `timeline_diff` — only when the task also involves *cutting* the video. Straight captioning of one continuous clip needs no timeline. If you do cut first, subtitle the rendered cut, not the source, or every cue time will be wrong.
- `speech_synthesize` / `tts_generate` — not part of this task.

## Completion Bar

Done only when all of these hold:

- `out/media.json`, `out/transcript.json`, `out/transcript_edits.md`, `out/subtitle_scout.json` (or `out/video_ingest.json`), `out/subtitle_plan.md`, `out/subtitles.json`, `out/subtitled.mp4`, `out/subtitle_qc_report.json`, `out/subtitle_verify.md` and `out/report.md` all exist;
- `out/subtitle_qc_report.json` covers the current `out/subtitles.json` and `out/subtitled.mp4`, and has no unresolved errors;
- every checkpoint in `out/subtitle_plan.md` has a final verdict in `out/subtitle_verify.md`, and every parked one names what was tried;
- every evidence frame produced by the final QC run has been read;
- `out/report.md` is non-empty and records assumptions, outputs, parked items and residual risks.
