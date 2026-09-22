# Narration reference

How the poetry-cinema-page skill produces the poem's narration track. The implementation is `scripts/narration.py`; the settings live under `narration` in `config/ark.config.json` — the same single config file the image pipeline uses.

A narration track is **generated**, not supplied. The user may still bring their own audio, in which case wire that file into the page and skip this pipeline; otherwise generate one with either engine below.

**Verified scope (author's machine, 2026-09).** Both engines, every command in this document, the narration-script rules, the timing sidecar, the SRT, and the failures listed under Troubleshooting were exercised end to end. Verified counts: 8 edge-tts voices and 15 doubao voices, all synthesizing with `resource_id=seed-tts-2.0`. Measured builds from one `《将进酒》` script: doubao `jiang-jin-jiu-doubao.mp3` at 78.07 s / 915 KB, edge-tts `jiang-jin-jiu-edge.mp3` at 68.74 s / 806 KB, both mp3, 24000 Hz, mono, 96 kbps. Sampled `audition` output: one mp3 per voice, 50–88 KB across the 15 doubao voices and 27–33 KB across the 8 edge-tts voices.

**Not verified: how any voice sounds.** The `gloss` strings in the config are glosses of the romanised voice ids — not official descriptions — and nobody has listened to them. Never describe a voice's tone, warmth, or quality from its id. Run `audition` and let the user listen.

## Engines

| Engine key | What it is | API key | Native output | Cost |
| --- | --- | --- | --- | --- |
| `edge-tts` | Microsoft edge-tts, synthesized locally | none | mp3 | free |
| `doubao-seed-tts` | Volcengine Doubao `seed-tts-2.0`, over the Ark plan gateway | yes — the same Ark key the image pipeline resolves (`ARK_API_KEY` or `config/ark.local.json`) | wav | metered on the Ark plan |

Trade-off: `edge-tts` is the zero-setup default — no key at all, only the `edge-tts` pip package. `doubao-seed-tts` introduces no second credential (it reuses the Ark key the images already need) and streams wav, which the script transcodes to mp3 whenever the requested extension says mp3, so everything downstream is identical.

How to switch:

- persistently: `narration.engine` in `config/ark.config.json` — `"engine": "edge-tts"` or `"engine": "doubao-seed-tts"`;
- per run: `--engine edge-tts|doubao-seed-tts` on any subcommand.

## Commands

```bash
python scripts/narration.py voices   [--engine edge-tts|doubao-seed-tts]
python scripts/narration.py probe    [--dry-run]
python scripts/narration.py audition [--engine X] [--voices a,b,c] [--out-dir DIR]
python scripts/narration.py say      --text "..." --out FILE [--engine X] [--voice ID]
python scripts/narration.py build    --text-file FILE --out FILE [--srt FILE] [--engine X] [--voice ID]
                                     [--format mp3|m4a|aac|wav] [--sample-rate N] [--gap SEC] [--paragraph-gap SEC]
```

The config resolves next to the script (`config/ark.config.json`), so the working directory only affects relative `--out` / `--text-file` / `--out-dir` paths.

Common flags, accepted by every subcommand:

| Flag | Value | Effect |
| --- | --- | --- |
| `--config PATH` | config file path | use a config other than `config/ark.config.json`. |
| `--engine NAME` | `edge-tts` or `doubao-seed-tts` | override `narration.engine` for this run. |
| `--voice ID` | voice id | override the configured voice; use an id from `narration.voice_catalog` for that engine. |
| `--text "..."` | text to speak | `probe` defaults to `测试`, `audition` to `君不见，黄河之水天上来，奔流到海不复回。`; `say` requires it. |
| `--name NAME` | label | label used in progress lines. |
| `--json` | — | `say` only: also print the result as a JSON document. |

### `voices`

Prints the catalog from the config for both engines (or just `--engine`), marks the currently configured voice with `*`, reports the engine's `needs_api_key`, and ends with the switch hint. No network access, no cost.

### `probe`

Reports the config path, the active engine, the output `dir`/`format`/`bitrate`, `ffmpeg` on PATH, and whether `edge-tts` is importable. Then, unless `--dry-run` is given, it speaks one short phrase on **every configured engine** (`--engine` limits it to one) and prints per-engine OK / FAIL with the voice, size, and elapsed time.

`probe` is not free: it really synthesizes, so it sends a few characters to whichever engines are configured. `--dry-run` prints the same report and synthesizes nothing. `--live` is accepted and changes nothing — `probe` already speaks. Exit code 1 means at least one engine failed, and each failure prints its own reason.

### `audition`

Speaks one sentence with many voices and writes an `index.html` page to A/B by ear. See [Choosing a voice](#choosing-a-voice).

### `say`

One clip. `--out` is required, and the extension is honoured: when the engine's native container differs from the extension you asked for (doubao streams wav), the clip is transcoded with ffmpeg, so the extension always matches the bytes. Useful for spot checks; pages use `build`.

### `build`

The full track from a script file. `--text-file` and `--out` are required.

| Flag | Meaning |
| --- | --- |
| `--text-file FILE` | the narration script (format below). |
| `--out FILE` | output track. Its extension must match `--format` / `narration.audio.format` — `build` does not sniff the extension. |
| `--srt FILE` | also write SRT subtitles from the same timings. |
| `--format mp3\|m4a\|aac\|wav` | override `narration.audio.format`. |
| `--sample-rate N` | override the output sample rate (default `narration.audio.sample_rate`, 24000). |
| `--gap SEC` | pause between lines inside a paragraph (default `narration.audio.line_gap_seconds`, 0.75). |
| `--paragraph-gap SEC` | pause before the first line of a new paragraph (default `narration.audio.paragraph_gap_seconds`, 1.6). |

`build` needs ffmpeg (concatenation, silence generation, conversion) and ffprobe (segment durations); a missing binary is a clear error, not a silent fallback. Each segment is synthesized on its own, converted to canonical PCM at the configured rate and channel count, joined with the configured silences, optionally loudness-normalised, and encoded once into the final track.

## Narration script format

`--text-file` is a line-oriented script:

- a line starting with `#` is a comment and is skipped;
- a blank line starts a new paragraph — the next line gets the longer `paragraph_gap_seconds` pause;
- every other line is one spoken segment, synthesized on its own and joined in order, with `line_gap_seconds` between lines of the same paragraph.

This maps onto a poem directly: one verse line per line. The file is read as UTF-8 (a BOM is tolerated). A file with no speakable line is an error, and `build` refuses to produce an empty track.

Worked example — the `《将进酒》` script the measured builds above used (4 paragraphs, 13 spoken segments):

```text
# 《将进酒》朗诵稿
# 规则：# 开头是注释；空行分段（段间停顿更长）；其余每行单独朗读。
# 三段对应全诗的情绪弧：下坠 → 上扬 → 升华。

《将进酒》，李白。

君不见，黄河之水天上来，奔流到海不复回。
君不见，高堂明镜悲白发，朝如青丝暮成雪。

人生得意须尽欢，莫使金樽空对月。
天生我材必有用，千金散尽还复来。
烹羊宰牛且为乐，会须一饮三百杯。
岑夫子，丹丘生，将进酒，杯莫停。
与君歌一曲，请君为我倾耳听。
钟鼓馔玉不足贵，但愿长醉不复醒。

古来圣贤皆寂寞，惟有饮者留其名。
陈王昔时宴平乐，斗酒十千恣欢谑。
主人何为言少钱，径须沽取对君酌。
五花马，千金裘，呼儿将出换美酒，与尔同销万古愁。
```

Keep the poem verbatim, punctuation included — the engine uses the punctuation for phrasing, and this text is also what the SRT will carry. Keep the title line (`open_with_title` / `title_template` in the config) so the track announces the poem before it starts reading.

Then:

```bash
python scripts/narration.py build \
  --text-file narration.txt \
  --out public/audio/jiang-jin-jiu-doubao.mp3 \
  --srt public/audio/jiang-jin-jiu-doubao.srt
```

## What `build` writes

### The track

`--out`, in `narration.audio.format` unless `--format` overrides it. The two measured builds of the example script:

| Build | File | Duration | Size | Format |
| --- | --- | --- | --- | --- |
| doubao-seed-tts · `zh_male_qingcang_uranus_bigtts` | `jiang-jin-jiu-doubao.mp3` | 78.07 s | 915 KB (937,197 bytes) | mp3 · 24000 Hz · mono · 96 kbps |
| edge-tts · `zh-CN-YunxiNeural` | `jiang-jin-jiu-edge.mp3` | 68.74 s | 806 KB | mp3 · 24000 Hz · mono · 96 kbps |

Same script, two engines: the same text lands at different lengths because the voices read at different speeds. Take durations from the sidecar, never from an assumption.

### The timing sidecar

`<out>.json` (here `jiang-jin-jiu-doubao.mp3.json`), written on every `build`:

```json
{
  "generated_at": "2026-09-21T14:29:38+00:00",
  "config": "/abs/path/config/ark.config.json",
  "engine": "doubao-seed-tts",
  "voice": "zh_male_qingcang_uranus_bigtts",
  "audio": "jiang-jin-jiu-doubao.mp3",
  "duration_seconds": 78.072,
  "bytes": 937197,
  "format": "mp3",
  "gaps": { "line": 0.75, "paragraph": 1.6 },
  "paragraphs": 4,
  "lines": [
    {
      "index": 1,
      "paragraph": 1,
      "text": "《将进酒》，李白。",
      "start": 0.0,
      "end": 3.192,
      "duration": 3.192,
      "engine": "doubao-seed-tts",
      "voice": "zh_male_qingcang_uranus_bigtts"
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `generated_at` | UTC timestamp, seconds precision. |
| `config` | the config file that was used. |
| `engine` / `voice` | what actually spoke (the `--voice` override if one was passed). |
| `audio` | output file name, sitting next to the sidecar. |
| `duration_seconds`, `bytes`, `format` | the finished track. |
| `gaps` | the line and paragraph pauses that were used. |
| `paragraphs` | paragraph count of the script. |
| `lines[]` | one entry per spoken segment, in spoken order: `index` (1-based across the whole script), `paragraph` (1-based), `text`, `start` / `end` / `duration` in seconds with the pauses included, and the `engine` / `voice` of that segment. |

`start` / `end` are absolute positions on the final track, so they can drive captions, line highlighting, or scroll sync without probing the audio. Sanity check: `duration` per line should be seconds (roughly 2–8 s per verse line), and `end` must increase monotonically.

### The SRT

With `--srt FILE`, `build` rewrites the same timings as subtitles:

```
1
00:00:00,000 --> 00:00:03,192
《将进酒》，李白。
```

One block per spoken line with `HH:MM:SS,mmm` timestamps. It cannot drift from the sidecar — both are derived from the one timeline — so it is safe to use for captions or as the sync source itself.

## Choosing a voice

Nobody can pick a voice from an id, and the catalog `gloss` is only a translation of the id. `audition` exists so the decision is made by ear:

```bash
python scripts/narration.py audition --text "君不见，黄河之水天上来，奔流到海不复回"
```

- default text: `君不见，黄河之水天上来，奔流到海不复回。`
- default voices: the whole `voice_catalog` for the active engine (8 for edge-tts, 15 for doubao); restrict with `--voices a,b,c`;
- default output directory: `public/audio/audition/`; override with `--out-dir`;
- sample format: `narration.audio.format` (mp3 by default).

It writes one clip per voice plus an `index.html` beside them. The page lists one `<figure>` per voice: the caption is the voice id with its duration and size, and under it a native `<audio controls preload="none">` player — play them back to back, or hand the page to the user. Failures are printed in the terminal and tallied at the end (`成功 N，失败 M`), so a partially filled page is visible there instead of being mistaken for a quiet voice.

When a voice wins, set `narration.engines.<engine>.voice` to its id (or pass `--voice <id>` per command). Re-audition after changing `rate` / `pitch` (edge-tts) or `speed` / `emotion` (doubao), because those change the result.

## Configuration walkthrough

Every key below lives under `narration` in `config/ark.config.json`. (A config with no `narration` section makes the CLI fail with a message pointing at this file.)

### `narration.engine`

The active engine key: `edge-tts` or `doubao-seed-tts`. The name must exist in `narration.engines`; an unknown name is rejected with the list of configured engines. `--engine` overrides it per run.

### `narration.engines.edge-tts`

| Key | Default | Meaning |
| --- | --- | --- |
| `label` | `edge-tts（免费 · 本地 · 无需密钥）` | shown by `voices` and `probe`. |
| `needs_api_key` | `false` | no key is resolved for this engine. |
| `voice` | `zh-CN-YunxiNeural` | default voice; override with `--voice`. |
| `rate` | `"+0%"` | speaking-rate delta, e.g. `-20%` for a slower read. |
| `volume` | `"+0%"` | volume delta, e.g. `-10%`. |
| `pitch` | `"+0Hz"` | pitch delta, e.g. `-8Hz` for a lower read. |

### `narration.engines.doubao-seed-tts`

| Key | Default | Meaning |
| --- | --- | --- |
| `label` | `豆包 seed-tts-2.0（火山方舟 · 中文更好）` | shown by `voices` and `probe`. |
| `needs_api_key` | `true` | key resolved for the DEFAULT image provider, i.e. `ARK_API_KEY` → `config/ark.local.json` → that provider's `api_key` field. |
| `voice` | `zh_male_qingcang_uranus_bigtts` | default voice; must belong to `resource_id` (see below). |
| `speed` | `0` | integer percent delta, clamped to −50..100; `-20` reads 20% slower. |
| `emotion` | `""` | empty = the engine's natural delivery; any other value is forwarded as the emotion parameter and is voice-dependent. |
| `resource_id` | `seed-tts-2.0` | sent as `X-Api-Resource-Id`; fixes which voice ids are legal. |
| `url` | `https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional` | the Ark plan TTS gateway (unidirectional streaming). |
| `sample_rate` | `24000` | request rate; the streamed wav comes back at this rate. |

The default image provider's `timeout_seconds`, `max_retries` and `retry_backoff_seconds` govern this HTTP call. With the shipped config the default provider is `ark`, so those are `image.providers.ark.*`; if you switch `image.provider`, the narration TTS call follows the same retry settings while still using the Ark key it needs.

### `narration.audio`

| Key | Default | Meaning |
| --- | --- | --- |
| `dir` | `public/audio` | default output directory (`audition` appends `/audition`). |
| `format` | `mp3` | output container: `mp3`, `m4a`, `aac`, or `wav`. |
| `bitrate` | `96k` | encoder bitrate for the lossy formats. |
| `channels` | `1` | channel count of the canonical PCM and of the output. |
| `sample_rate` | `24000` | output sample rate. |
| `line_gap_seconds` | `0.75` | silence between lines inside a paragraph. |
| `paragraph_gap_seconds` | `1.6` | silence before a new paragraph's first line. |
| `normalize_loudness` | `true` | loudness-normalise the joined track. |
| `target_loudness_lufs` | `-16` | its target (applied as `loudnorm=I=-16:TP=-1.5:LRA=11`). |

### `narration.script`

The composition contract for the narration script you hand to `build`:

| Key | Default | Meaning |
| --- | --- | --- |
| `open_with_title` | `true` | open the track by announcing the poem. |
| `title_template` | `《{title}》{author}` | the announcement line, e.g. `《将进酒》，李白。`. |
| `include_original` | `true` | narrate the poem itself. |
| `include_literal` | `false` | also narrate the line-by-line plain meaning. Turn this on when the narration should carry the interpretation — an explainer or classroom video, where the voice is the teaching. |
| `include_analysis` | `false` | also narrate the closing interpretation (genre, imagery, technique, emotional arc). |

How these switches are read depends on the source file. With a structured `.json` source (`{"title", "author", "lines": [{"original", "literal", "analysis"}]}`) `build` honours them directly: the selected layers of each verse line become consecutive segments inside one paragraph, so the recitation pauses before the meaning and resumes after it. With a plain `.txt` source `build` speaks the file verbatim, line by line, and these switches are only the authoring contract — the script you write is what gets spoken. `--include original,literal,analysis` overrides the config for one run, which is the quickest way to produce a poem-plus-interpretation track.

### `narration.voice_catalog`

The selectable voices per engine, each `{ "id": ..., "gloss": ... }`. `voices` prints it and marks the configured voice with `*`, and `audition` defaults to it, so the catalog is exactly the set of voices a user can choose from. `gloss` is an id gloss (see the top of this page), not a description of the audio.

### `narration.known_rejected`

Voice ids that were tried and rejected, with the reason — currently the doubao ids that do not belong to `seed-tts-2.0`. Kept so nobody burns a run re-trying them.

## Voice catalogs

Every id below is enabled by the shipped config and was verified to synthesize at least one clip on the author's machine. The gloss column reads the id; it is not an audition.

### edge-tts — 8 Mandarin voices

| Voice id | id gloss |
| --- | --- |
| `zh-CN-YunxiNeural` | 云希 · Yunxi — default |
| `zh-CN-YunyangNeural` | 云扬 · Yunyang |
| `zh-CN-YunjianNeural` | 云健 · Yunjian |
| `zh-CN-YunxiaNeural` | 云夏 · Yunxia |
| `zh-CN-XiaoxiaoNeural` | 晓晓 · Xiaoxiao |
| `zh-CN-XiaoyiNeural` | 晓伊 · Xiaoyi |
| `zh-CN-liaoning-XiaobeiNeural` | 小北 · Xiaobei — Liaoning (Northeastern) Mandarin |
| `zh-CN-shaanxi-XiaoniNeural` | 小妮 · Xiaoni — Shaanxi Mandarin |

The config's own `gloss` strings add the voice-type and dialect hints you see in the `voices` output; they are still id glosses, and none of them is a listening result.

### doubao-seed-tts — 15 voices, all with `resource_id=seed-tts-2.0`

| Voice id | id gloss |
| --- | --- |
| `zh_male_qingcang_uranus_bigtts` | qingcang — default |
| `zh_male_shenyeboke_uranus_bigtts` | 深夜播客 · “late-night podcast” |
| `zh_male_ruyaqingnian_uranus_bigtts` | 儒雅青年 · “refined young man” |
| `zh_male_wennuanahu_uranus_bigtts` | 温暖阿虎 · “warm A-hu” |
| `zh_male_liufei_uranus_bigtts` | liufei |
| `zh_male_yuanboxiaoshu_uranus_bigtts` | 渊博小叔 · “erudite young uncle” |
| `zh_male_shaonianzixin_uranus_bigtts` | 少年自信 · “confident youth” |
| `zh_male_yangguangqingnian_uranus_bigtts` | 阳光青年 · “sunny youth” |
| `zh_female_vv_uranus_bigtts` | vv |
| `zh_female_xiaohe_uranus_bigtts` | xiaohe |
| `zh_female_qingxinnvsheng_uranus_bigtts` | 清新女生 · “fresh girl” |
| `zh_female_gaolengyujie_uranus_bigtts` | 高冷御姐 · “aloof big sister” |
| `zh_female_linjianvhai_uranus_bigtts` | 邻家女孩 · “girl next door” |
| `zh_female_roumeinvyou_uranus_bigtts` | 柔美女友 · “gentle girlfriend” |
| `zh_female_meilinvyou_uranus_bigtts` | 魅力女友 · “charismatic girlfriend” |

Beware of selecting a doubao voice that is not in this table: a listed id is only known to be legal for `resource_id=seed-tts-2.0` if it came from the catalog.

## Voice id vs `resource_id`

The doubao engine sends `X-Api-Resource-Id: seed-tts-2.0` (from `narration.engines.doubao-seed-tts.resource_id`). A voice id that belongs to a different resource is refused by the service with:

```
code 55000000: resource ID is mismatched with speaker related resource
```

The script turns that into a readable error: the stream contains no audio, and the message names the cause and points at the catalog — "this voice does not belong to resource id 'seed-tts-2.0'. Use a voice from the doubao-seed-tts catalog in config/ark.config.json, or run `narration.py voices`." Only use ids listed in `narration.voice_catalog`.

Confirmed mismatches include every id ending in `_moon_bigtts` and these `_uranus_bigtts` ids:

- `zh_male_jingqiangkanye_uranus_bigtts`
- `zh_female_wanwanxiaohe_uranus_bigtts`
- `zh_male_beijingxiaoye_uranus_bigtts`

The three `_uranus_bigtts` ids above are recorded under `narration.known_rejected`; any of them, and any `_moon_bigtts` id, would need its own `resource_id`, which this skill does not enable. Before adding a new doubao id to the catalog, synthesize one clip with it (`say --engine doubao-seed-tts --voice <id> --text "测试"`); a `55000000` failure means it belongs to a different resource id and stays out.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ffmpeg not found on PATH. It is required for audio concatenation and format conversion...` | ffmpeg missing or not on PATH | Install ffmpeg. `build` always needs it; `say` and `audition` need it whenever a transcode happens. |
| `ffprobe not found on PATH; needed to measure segment durations.` | ffprobe missing | It ships with ffmpeg; install a full ffmpeg build, not a stripped one. |
| `the edge-tts package is not installed. Install it with pip install edge-tts` | the pip package is missing | `pip install edge-tts` — it needs no key. |
| `engine 'doubao-seed-tts' requires an Ark API key...` | no key found | Set `ARK_API_KEY` or create `config/ark.local.json`, or switch `narration.engine` to `edge-tts`. |
| `... the TTS stream contained no audio ... 55000000 ...` | the voice does not match `resource_id` | Use a voice from `narration.voice_catalog`, or run `voices`. |
| `TTS authentication failed (HTTP 401/403)` | bad key, or `seed-tts-2.0` is not enabled for it | Re-check the key resolution order and run `probe`. |
| `the config file has no 'narration' section; add one...` | the config predates narration | Add the `narration` block, or point `--config` at the shipped file. |
| `the narration text file has no speakable lines: <file>` | the script is only comments and blank lines | Write at least one spoken line. |
| Output exists but is silent | see the checklist below | |

Silence checklist:

- Empty or missing output is always an error, never a silent success: a script with no speakable lines and `say` without `--text` both fail loudly, and a provider that sends no audio raises instead of writing an empty file.
- If the file exists but plays nothing, check the sidecar first: a plausible `duration_seconds` with monotonically increasing line timings means the audio is fine and the problem is on the page (player volume, the `audioSrc` URL, browser autoplay policy — see [page-pattern.md](page-pattern.md)).
- If every voice is silent in `audition`, the problem is engine-level (package, key, or voice), not a single bad voice — start with `probe --dry-run` and then `probe`.
- After any ambiguous run, trust the exit code and the printed per-engine FAIL lines over the presence of a file.
