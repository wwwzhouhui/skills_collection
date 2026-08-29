---
name: video-recap-workflows
description: Consolidated narrated recap workflows for movie commentary, football/soccer match recaps, League of Legends esports recaps, and basketball/NBA/CBA full-game recaps. Use when video-edit-agent routes a full film, match, game replay, or broadcast into mode=movie-recap, mode=soccer-recap, mode=lol-recap, or mode=basketball-recap for Chinese narrated highlight/recap editing with deterministic recap MCP tools.
---

# Video Recap Workflows

This skill contains specialized single-title recap workflows that sit beside `video-edit-assembly` and `video-speech-workflows`.

## Route Modes

Choose exactly one mode from the caller's args, then read and follow the matching workflow document:

| Mode | Workflow |
|---|---|
| `movie-recap` | [workflows/movie-recap.md](workflows/movie-recap.md) |
| `soccer-recap` | [workflows/soccer-recap.md](workflows/soccer-recap.md) |
| `lol-recap` | [workflows/lol-recap.md](workflows/lol-recap.md) |
| `basketball-recap` | [workflows/basketball-recap.md](workflows/basketball-recap.md) |

If the args do not name a mode, infer the narrowest matching one:

- Use `movie-recap` for "movie recap", "film commentary", "几分钟看完一部电影", or other one-film Chinese narrated recap tasks with substantial dialogue.
- Use `soccer-recap` for full football/soccer match recaps, 足球比赛解说集锦, or story-driven match highlight reels.
- Use `lol-recap` for full League of Legends pro-game or BO-series recaps with original caster commentary.
- Use `basketball-recap` for full basketball broadcast recaps, including NBA/CBA-style Chinese narrated highlight stories.

## Boundaries

- Multi-material user source packs stay in `video-edit-assembly` unless the task is specifically one full title/match/game recap handled by a workflow above.
- Short official highlight compilations are not valid inputs for the sports recap workflows unless the user only wants ordinary trimming or subtitling; use the common `video-edit-agent` workflow for those.
- The selected workflow's own file contract is authoritative. These workflows usually produce `out/final.mp4` and workflow-specific QC artifacts rather than the generic `out/preview.mp4` timeline contract.
- The recap tools do not perform narrative reasoning. The main agent must read transcripts/axes, write outlines, scripts, style cards, and spot-review notes; deterministic tools only inspect, arrange, synthesize, bind, render, and validate media.

## Shared Tool Families

- Movie recap: `detect_shots`, `arrange_footage`, `synthesize_narration`, `bind_narration`, `render_narrated`.
- Soccer recap: `soccer_ingest`, `detect_shots`, `soccer_arrange`, `soccer_tts`, `soccer_render`.
- LoL and basketball recap: `lol_ingest`, `detect_shots`, `lol_tts`, `lol_arrange`, `lol_render`.
- All workflows may still use common tools such as `inspect_media`, `transcribe`, `video_ingest`, `video_watch_segment`, and `qc_preview` when the workflow requires evidence or closeout checks.

## References

- Movie style corpus: [references/jieshuo_corpus.jsonl](references/jieshuo_corpus.jsonl). Search or filter it by `movie_types` and `like`; do not load the full corpus unless needed.
- Soccer style card: [references/soccer-style-card.md](references/soccer-style-card.md).
- LoL/esports style card: [references/lol-style-card.md](references/lol-style-card.md). Basketball may use this as pacing reference while keeping basketball terminology and score logic grounded in the broadcast.
