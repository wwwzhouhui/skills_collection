---
name: env-setup
description: Checking and provisioning the machine's environment for the video-agent-kit plugin — probing for ffmpeg/ffprobe that actually carry the encoders and filters we render with (libx264/aac/libmp3lame, libass, libfreetype), python packages (mcp, cv2, numpy, PIL, jieba, fontTools, scenedetect) in the interpreter Claude Code really uses, a CJK font whose cmap truly covers Chinese, and which speech channel is in play (under ZCode the official channel needs no local key) — then installing what is missing (China mirrors by default) or telling the user exactly what to install. Works on macOS, Windows and Linux. Use BEFORE the first edit run on a new machine, when the session-start hook reports 缺失依赖, or whenever a tool fails in an environment-shaped way — ModuleNotFoundError, `ffmpeg not found`, `Unknown encoder 'libx264'`, `No such filter: 'subtitles'`, `no font file found for family`, 字幕烧成豆腐块/方块, speech_transcribe 超时或 401. Also use when asked to 检查环境 / 装依赖 / 配国内源 / setup / doctor.
---

# Env Setup

Claude Code is a generic harness — it ships **no** ffmpeg, no CJK font, no python
media stack. Everything this kit needs is per-machine, and provisioning it is
this skill's job. A run started on a half-provisioned machine does not fail
cleanly: it burns the whole observe→timeline phase and then dies at
`render_preview`, or worse, *succeeds* while burning subtitles as tofu boxes
(□□□) because `fc-match` handed us a font with no Chinese glyphs and ffmpeg
exited 0.

**One entry point** — everything else here is judgement about its output:

```bash
python3 <plugin_root>/skills/env-setup/scripts/env_doctor.py          # probe + what's needed
python3 <plugin_root>/skills/env-setup/scripts/env_doctor.py --fix    # + install the auto-safe items
```

(Windows: `python` instead of `python3` if that's what's on PATH.) Plugin root is
announced at session start and written to `.video_agent/plugin_root`. Always call
it by absolute path — cwd is the project directory, not the skill directory. A
full probe is a few seconds; give Bash ≥ 120s anyway, because a blocked network
spends its timeouts before answering.

## What must be present, and what dies without it

The script decides *state* and prints the exact requirement + an example command
for **the current OS**. This table is only for judging *impact*:

| Requirement | Dead without it |
|---|---|
| Python ≥ 3.10, and `mcp` (1.x), `requests`, `opencv-python-headless`, `numpy`, `pillow`, `jieba`, `fonttools`, `scenedetect` in **that same interpreter** | `mcp` → every tool (server won't start); requests → `transcribe` + all TTS; cv2/numpy/PIL → `video_ingest`, contact sheets, `qc_preview` scans, i.e. all visual evidence; jieba → `subtitle_build` line breaking; fontTools → the pre-render tofu check; scenedetect → recap shot boundaries |
| `ffmpeg` + `ffprobe` on PATH, **with libx264 / aac / libmp3lame** | ingestion and probing (Phase 1 can't start); missing encoder = the render dies at the last step, after everything upstream was paid for |
| that ffmpeg **built with libass + libfreetype** (`subtitles`/`ass`/`drawtext` filters) | subtitle burn-in, title cards, score bugs — the recap deliverable |
| a **CJK font whose cmap really covers Chinese** | Chinese subtitles/titles. This one fails *silently* — see the tofu warning above |
| cloud ASR credentials or Speech MCP access | `speech_transcribe`; without it there is no transcript, so every speech-driven decision is guesswork. **Under ZCode this is never a gap** — see below |
| cloud TTS credentials or Speech MCP access | narration/dubbing (`speech_synthesize`, `tts_generate`, `*_tts`). Edit-only and subtitle-only tasks survive without it |

### Speech needs no local key under ZCode

Transcription and synthesis default to the **official channel**, which authenticates
with identity the ZCode host injects into each `tools/call`. There is nothing to
configure, nothing to install, and no key to obtain. Two consequences:

- **Never tell the user to set an ASR/TTS key to get transcription working**, and
  never treat a "credentials not set" line as a blocker. The doctor reports these
  two rows as `官方通道` whenever `ZCODE_BASE_URL` is present, and both rows are
  soft (`只降级不致命`) in every case.
- The doctor runs as its **own process**, so it cannot see the per-call identity
  headers — only whether the official channel exists at all. A *specific* call
  failing on identity (not logged in, no Coding Plan) surfaces from the tool
  itself, with a message saying which of the two it is. That is the signal to act
  on; the doctor's row is not.

Only non-ZCode hosts need configuration, in this order of preference: remote
Speech MCP (`VE_SPEECH_MCP_URL` / `VE_SPEECH_MCP_TOKEN`), or — as a legacy escape
hatch for deployments bringing their own speech service — a direct HTTP backend,
which needs its endpoint and resource/model identifiers in the **process
environment** (a project `.env` is untrusted for those; it could otherwise
redirect an authenticated call) plus a key. `/env-check` prints the exact set.

Version floors are the only hard numbers; how the tool gets installed is the
user's choice — package manager, installer, conda, whatever the machine already
uses.

## Mirrors — use them by default, not as a fallback

Most users of this plugin are in mainland China, where the official PyPI CDN and
GitHub-hosted Homebrew bottles are routinely slow enough to time out. A timeout
there doesn't look like a network problem — it looks like "the install ran for
ten minutes and then failed", which gets misdiagnosed as a broken package every
time. **So a mirror is the first choice, not the recovery step.** The doctor
already puts the mirror into the command it prints (and uses); when you install
by hand, use these:

| What | First choice | Alternative |
|---|---|---|
| pip | 清华 `https://pypi.tuna.tsinghua.edu.cn/simple` — `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>` | 阿里云 `https://mirrors.aliyun.com/pypi/simple/` |
| ffmpeg | **macOS**: `export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles` then `brew install ffmpeg`. **Any platform / no root**: `conda install -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge ffmpeg` — cleanest path, no system package manager touched. | apt sources → Tsinghua/USTC (system-wide change); Windows `winget`/gyan.dev has no mirror concept (use conda) |
| CJK font | Linux `apt-get install fonts-noto-cjk` (apt mirror helps). mac/Windows already ship 苹方/微软雅黑 — install nothing. | Download NotoSansSC from `github.com/notofonts/noto-cjk` into any directory and point `VE_FONT_DIRS` at it (works without root) |
| direct speech endpoint (only if you configured one) | **no mirror exists** — it is the service itself. Unreachable = network policy; that's a proxy question, not a mirror one | — |

Notes that matter in practice:

- Making it permanent is the user's call, not yours by default:
  `pip config set global.index-url <url>` writes their **global** config and
  affects every other project on the machine. The doctor prints it; only run it
  if the user agrees — a one-off `-i <url>` needs no such permission.
- **Mirrors lag.** If a package version genuinely isn't on the mirror, the fix is
  to drop `-i` for that one install and go to the official source — not to
  conclude the environment is broken.
- Outside mainland China these mirrors are pointless (and slower).
  `VE_PIP_INDEX=<url>` overrides the pip index the doctor uses; set it to the
  official URL to opt out entirely.
- A mirror fixes slowness, **a proxy fixes blockage** — different problems. Try
  the mirror first; only if the mirror itself is unreachable is it a
  proxy/firewall question.

## Workflow

`doctor → read the requirements → --fix the auto items → tell the user what's left → re-run doctor → report`

1. **Run the doctor first, always.** Never install from this file's tables or
   from memory — on a provisioned machine the correct action is *nothing*, and a
   speculative install can downgrade a working package (or, with opencv, break
   the one that worked).
2. **`--fix` covers only the user-space, idempotent subset**: pip installs into
   the running interpreter. It deliberately does **not** install ffmpeg, fonts,
   or uninstall anything — those are system-level or destructive, the right
   method differs per machine (and per permission level), and guessing wrong is
   worse than reporting. For those, **give the user the requirement and the
   suggested command, and let them run it.**
3. **Fix in the printed order.** An item whose prerequisite failed prints
   `[未探测]` instead of a guessed verdict — don't run a fix for an unprobed
   item; fix its prerequisite and re-run.
4. **`·` means "not applicable on this OS", not "broken"**, and
   `只降级不致命` means exactly that: the two speech-channel rows and disk headroom
   don't block a task. Everything else is a hard gap.
5. **After a PATH-changing install, the new tool is invisible to the current
   shell** (most visibly on Windows). If the doctor still can't see ffmpeg the
   user just installed, that's the reason — have them restart the terminal (or
   Claude Code) rather than reinstalling.
6. **Re-run the doctor at the end** — not the fix commands' exit codes.
   `pip install` can succeed while the import still fails (a wheel mismatched to
   the platform). The run writes `.video_agent/env_report.json` as the receipt,
   so **don't re-probe every turn**; re-probe after installing something or
   after a tool fails.
7. **Report in capability terms, then stop if something's dead.** "ffmpeg has no
   libass → subtitle burn-in unavailable; the recap can't ship. Install a full
   build and re-run `/env-check`." Do not enter a phase whose tools are dead and
   improvise around it.

## Rules

- **Install only what the doctor flagged.** Extra packages are how a working
  environment drifts into an unreproducible one.
- **Never substitute for a missing dependency.** No cv2 does not mean "extract
  frames with ffmpeg and eyeball the filenames"; no transcript does not mean
  "infer the dialogue from the visuals"; no CJK font does not mean "render the
  subtitles in English". A dead capability is a report line, not a workaround.
- **`scenedetect` must be installed with `--no-deps`.** It declares
  `opencv-python` (the GUI build), which overwrites the same `cv2` package
  directory as `opencv-python-headless` and leaves both half-broken. The doctor
  prints the two-step command; don't "simplify" it.
- **Never auto-uninstall opencv.** If GUI+headless are both installed the doctor
  reports it and prints the fix, because the GUI build may belong to another
  project on that machine. That's the user's call.
- **A font that resolves is not a font that works.** `fc-match` never fails: ask
  it for an uninstalled Chinese family and it returns DejaVu Sans, which has no
  CJK glyphs, and libass then renders blanks while ffmpeg exits 0. The doctor
  reads the cmap for exactly this reason — if it says the resolved font has no
  Chinese coverage, treat it as missing even though a path was printed.
- **Adding a dependency to this plugin means adding a `Check` to
  `env_doctor.py` in the same change** (and to `requirements.txt`). The
  `SessionStart` hook imports `cheap_missing()` from it, so the cheap checks are
  the single source of truth for the startup warning — a dependency that isn't a
  `Check` is one nobody hears about until it crashes.

## Fonts: the one platform difference worth knowing

Font lookup is centralised in `mcp/ve_tools/fonts.py`, searched in this order:

1. `VE_FONT_DIRS` (os.pathsep-separated) — explicit override, always wins
2. the Linux dirs the kit has always used (`/root/.fonts`, `/usr/share/fonts`)
3. the platform's own font dirs — `/System/Library/Fonts`, `~/Library/Fonts`
   (macOS), `%SystemRoot%\Fonts`, `%LOCALAPPDATA%\Microsoft\Windows\Fonts`
   (Windows)
4. `fc-list :lang=zh` when fontconfig exists, cmap-verified

So **macOS and Windows normally need no font install at all** (苹方 / 微软雅黑
are found in step 3, and libass resolves them through CoreText/DirectWrite).
Linux images without `fonts-noto-cjk` are the case that actually needs work.
When a user has fonts somewhere unusual, `VE_FONT_DIRS` is the answer — not a
code change, and not `sudo cp` into `/usr/share/fonts`.

## Anti-patterns

- Prescribing one platform's install method (`apt-get …`) to a user on another OS
  — the doctor already picked the right example for their machine; if they'd
  rather use their own method, that's fine, the requirement is what matters.
- Reading this skill's tables and installing from them without running the doctor.
- Treating a `[未探测]` line as a missing dependency, or a `·` (n/a) line as a defect.
- Auto-installing system-level software (ffmpeg, fonts) or uninstalling packages
  on the user's machine without being asked.
- Retrying a stalled `pip install` unchanged on a machine that needs a mirror
  (or a proxy) — the second attempt fails the same way, ten minutes later.
- Declaring the environment fixed off exit codes without a re-probe.
- Re-running the full doctor every turn "to be safe" — `.video_agent/env_report.json`
  holds the last verdict.
- Proceeding into a render or a recap with ffmpeg missing libass, letting it
  surface as a mysterious tool error twenty rounds later.
- **Asking the user for an ASR/TTS key.** Under ZCode there is no key to give;
  the doctor's speech rows say `官方通道` and a failing call reports whether it is
  a login or a plan problem. Chasing a key wastes the user's turn and fixes nothing.
- Blaming the plugin for `speech_transcribe` timeouts before checking which
  channel it used — an unreachable *configured direct endpoint* is a network
  policy problem no amount of retrying fixes, and it is not even consulted when
  the official channel or a remote Speech MCP is in play.
