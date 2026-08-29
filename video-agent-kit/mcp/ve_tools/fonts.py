"""Cross-platform CJK font discovery — one list, one override, one place.

Every renderer in the kit needs a *concrete font file* (ffmpeg `drawtext
fontfile=`, PIL `ImageFont.truetype`, libass metrics in `subtitle_style`) or a
*family name* (`subtitles=...:force_style=FontName=`). Until 0.4.1 each call
site carried its own hardcoded `/usr/share/fonts/opentype/noto/...` list plus
`fc-match`/`fc-list`, which resolves on the Linux batch boxes and nowhere else:
macOS only has fontconfig if the user installed it by hand, and **Windows has
none at all**, so `subtitle_build` raised `no font file found for family ...`
before drawing a single frame — on a machine with 微软雅黑 sitting right there.

Search order is deliberate, and step 2 is why it is safe to adopt everywhere:

1. ``VE_FONT_DIRS`` / ``VIDEO_EDIT_FONT_DIRS`` — explicit override, wins over
   everything (already the convention in `render.py` / `video_observe.py`).
2. the Linux dirs the kit has always searched, in their original order —
   an already-provisioned batch box resolves to the same file as before, so
   subtitle line-breaking (which is measured against the real font) does not
   shift under existing traces.
3. the current platform's system font dirs — mac/Windows ship CJK fonts, they
   were simply never looked at.

Nothing here imports a third-party package at module level: `env_doctor.py`
imports this module directly to probe the font situation, and that has to work
on a machine where pip installs have not happened yet.
"""
from __future__ import annotations

import functools
import os
import shutil
import subprocess
import sys
from pathlib import Path

OS = ("macos" if sys.platform == "darwin"
      else "windows" if os.name == "nt" else "linux")

# Dirs the kit has always searched (subtitle_style._FONT_DIRS through 0.4.0).
# Kept first on every platform: they do not exist off Linux, so listing them
# costs one stat and preserves Linux resolution order exactly.
_LEGACY_DIRS = ["/root/.fonts", "/usr/share/fonts"]

_PLATFORM_DIRS = {
    "linux": ["/usr/local/share/fonts", "~/.fonts", "~/.local/share/fonts"],
    "macos": ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
              "/Library/Fonts", "~/Library/Fonts"],
    "windows": [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Fonts"),
                # Per-user installs (Windows 10+ "Install for me only")
                os.path.join(os.environ.get("LOCALAPPDATA", ""),
                             "Microsoft", "Windows", "Fonts")],
}

# Filenames to prefer per weight, best first. The NotoSans* entries are what the
# Linux images ship (and what subtitle_style's presets are tuned against); the
# rest are the stock CJK faces on macOS / Windows, which is the whole point.
_WEIGHT_FILES = {
    "black": ["NotoSansSC-900.ttf", "NotoSansCJK-Black.ttc", "NotoSansCJKsc-Black.otf"],
    "bold": ["NotoSansSC-700.ttf", "NotoSansCJK-Bold.ttc", "NotoSansCJKsc-Bold.otf",
             "SourceHanSansSC-Bold.otf", "msyhbd.ttc", "simhei.ttf",
             "PingFang.ttc", "Hiragino Sans GB.ttc"],
    "medium": ["NotoSansSC-500.ttf", "NotoSansCJK-Medium.ttc", "NotoSansCJKsc-Medium.otf"],
    "regular": ["NotoSansSC-400.ttf", "PingFang.ttf",
                "NotoSansCJK-Regular.ttc", "NotoSansCJKsc-Regular.otf",
                "NotoSansSC-Regular.otf", "SourceHanSansSC-Regular.otf",
                "PingFang.ttc", "Hiragino Sans GB.ttc", "STHeiti Light.ttc",
                "msyh.ttc", "simhei.ttf", "simsun.ttc", "Deng.ttf",
                "wqy-zenhei.ttc", "wqy-microhei.ttc", "DroidSansFallbackFull.ttf"],
}

# Last resort: any font file whose name looks like a CJK face. Matched against
# the lowercased stem so "NotoSansCJKsc-Regular" and "msyhl" both land.
_CJK_NAME_HINTS = ("notosanscjk", "notoserifcjk", "notosanssc", "notosanstc",
                   "sourcehansans", "sourcehanserif", "pingfang", "hiragino sans gb",
                   "stheiti", "songti", "heiti", "yuppy", "msyh", "msjh", "yahei",
                   "simhei", "simsun", "simkai", "deng", "fangsong", "kaiti",
                   "wqy-", "uming", "ukai", "droidsansfallback", "arialunicode",
                   "unifont")

_FONT_SUFFIXES = {".ttf", ".ttc", ".otf", ".otc"}

# stem prefix -> the family name libass / DirectWrite / fontconfig answers to.
# Used for `force_style=FontName=`, where a file path is not accepted.
_FAMILY_BY_STEM = (
    ("notosanscjk", "Noto Sans CJK SC"),
    ("notosanssc", "Noto Sans SC"),
    ("notosanstc", "Noto Sans TC"),
    ("sourcehansans", "Source Han Sans SC"),
    ("pingfang", "PingFang SC"),
    ("hiragino sans gb", "Hiragino Sans GB"),
    ("stheiti", "Heiti SC"),
    ("songti", "Songti SC"),
    ("msyhbd", "Microsoft YaHei"),
    ("msyh", "Microsoft YaHei"),
    ("msjh", "Microsoft JhengHei"),
    ("simhei", "SimHei"),
    ("simsun", "SimSun"),
    ("deng", "DengXian"),
    ("wqy-zenhei", "WenQuanYi Zen Hei"),
    ("wqy-microhei", "WenQuanYi Micro Hei"),
    ("uming", "AR PL UMing CN"),
    ("ukai", "AR PL UKai CN"),
    ("droidsansfallback", "Droid Sans Fallback"),
)

# Family to ask libass for when no concrete file was found: the stock CJK face
# of the platform, which its font backend (fontconfig / DirectWrite / CoreText)
# resolves without any of our dirs being involved.
_DEFAULT_FAMILY = {"linux": "Noto Sans CJK SC",
                   "macos": "PingFang SC",
                   "windows": "Microsoft YaHei"}


def override_dirs() -> list[Path]:
    """Dirs from VE_FONT_DIRS / VIDEO_EDIT_FONT_DIRS (os.pathsep-separated)."""
    raw = (os.environ.get("VE_FONT_DIRS")
           or os.environ.get("VIDEO_EDIT_FONT_DIRS") or "")
    return [Path(p.strip()).expanduser() for p in raw.split(os.pathsep) if p.strip()]


def font_dirs() -> list[Path]:
    """Every directory worth searching, highest priority first.

    Not cached: VE_FONT_DIRS is read per call so a tool can point at a font
    directory it just materialised (and so the doctor's advice takes effect
    without restarting the MCP server).
    """
    dirs = [*override_dirs(),
            *(Path(p) for p in _LEGACY_DIRS),
            *(Path(p).expanduser() for p in _PLATFORM_DIRS[OS] if p)]
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        key = str(d)
        if key in seen:
            continue
        seen.add(key)
        out.append(d)
    return out


def _find_named(name: str, dirs: list[Path]) -> str | None:
    """Locate one filename: direct child first, then a recursive walk.

    The recursive pass exists because distro packages bury the file
    (`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`) while the batch
    images drop it flat into `/root/.fonts`.
    """
    for directory in dirs:
        candidate = directory / name
        if candidate.is_file():
            return str(candidate)
    for directory in dirs:
        try:
            if not directory.is_dir():
                continue
            for hit in directory.rglob(name):
                if hit.is_file():
                    return str(hit)
        except OSError:          # unreadable mount / permission — not our problem
            continue
    return None


def _scan_by_hint(dirs: list[Path], prefer_bold: bool) -> str | None:
    for directory in dirs:
        try:
            if not directory.is_dir():
                continue
            files = [p for p in sorted(directory.rglob("*"))
                     if p.is_file() and p.suffix.lower() in _FONT_SUFFIXES
                     and any(h in p.stem.lower() for h in _CJK_NAME_HINTS)]
        except OSError:
            continue
        if not files:
            continue
        if prefer_bold:
            bold = [p for p in files if "bold" in p.stem.lower() or "bd" in p.stem.lower()]
            if bold:
                return str(bold[0])
        return str(files[0])
    return None


@functools.lru_cache(maxsize=8)
def _find_cjk_font(weight: str, dirs_key: tuple[str, ...]) -> str | None:
    dirs = [Path(d) for d in dirs_key]
    names = _WEIGHT_FILES.get(weight) or _WEIGHT_FILES["regular"]
    # Fall through to regular: a machine with only one CJK face should still
    # render bold text (libass synthesises the weight) rather than fail.
    for name in [*names, *(n for n in _WEIGHT_FILES["regular"] if n not in names)]:
        hit = _find_named(name, dirs)
        if hit:
            return hit
    hit = _scan_by_hint(dirs, prefer_bold=weight in ("bold", "black"))
    if hit:
        return hit
    # Last resort: whatever fontconfig says covers Chinese, wherever it lives.
    # Catches faces our name hints have never heard of (and fonts installed
    # outside every directory above) — but only if the cmap agrees, since
    # `:lang=zh` is fontconfig's claim, not a guarantee.
    for path in _fc_list_zh_files():
        if covers_cjk(path) is not False:
            return path
    return None


def find_cjk_font(weight: str = "regular") -> str | None:
    """A concrete CJK-capable font file, or None if the machine has none.

    Never guesses a path that does not exist: callers that need a hard failure
    (lol/soccer rendering) can raise on None, and the doctor reports it as a
    missing requirement with a per-platform install command.
    """
    return _find_cjk_font((weight or "regular").lower(),
                          tuple(str(d) for d in font_dirs()))


@functools.lru_cache(maxsize=1)
def _fc_list_zh_families() -> frozenset[str]:
    """Families fontconfig knows that cover Chinese. Empty off Linux."""
    if not shutil.which("fc-list"):
        return frozenset()
    try:
        proc = subprocess.run(["fc-list", ":lang=zh", "family"],
                              capture_output=True, text=True, timeout=30)
    except Exception:
        return frozenset()
    families: set[str] = set()
    for line in proc.stdout.splitlines():
        for fam in line.split(","):
            fam = fam.strip()
            if fam:
                families.add(fam)
    return frozenset(families)


@functools.lru_cache(maxsize=1)
def _fc_list_zh_files() -> tuple[str, ...]:
    """Font *files* fontconfig reports as covering Chinese, existing ones only."""
    if not shutil.which("fc-list"):
        return ()
    try:
        proc = subprocess.run(["fc-list", ":lang=zh", "file"],
                              capture_output=True, text=True, timeout=30)
    except Exception:
        return ()
    files: list[str] = []
    for line in proc.stdout.splitlines():
        path = line.strip().rstrip(":").strip()
        if path and path not in files and Path(path).is_file():
            files.append(path)
    return tuple(files)


def family_of_file(font_file: str | Path) -> str | None:
    """Family name for a font file, by filename — no fontconfig needed."""
    stem = Path(font_file).stem.lower()
    for prefix, family in _FAMILY_BY_STEM:
        if stem.startswith(prefix) or prefix in stem:
            return family
    return None


def ass_font_name() -> str | None:
    """Family name to put in `force_style=FontName=`, or None if the machine has
    no CJK font at all (caller should then skip burn-in rather than render tofu).

    fontconfig first (its answer is what libass will actually resolve on Linux),
    then the family of whatever concrete file we found, then the platform's
    stock face — on Windows/macOS libass goes through DirectWrite/CoreText, so a
    family name works there even though `fc-list` does not exist.
    """
    families = _fc_list_zh_families()
    for preferred in ("Noto Sans CJK SC", "Noto Sans CJK TC", "Noto Sans SC",
                      "Source Han Sans SC", "WenQuanYi Zen Hei"):
        if preferred in families:
            return preferred
    if families:
        return sorted(families)[0]
    found = find_cjk_font("regular")
    if found:
        return family_of_file(found) or _DEFAULT_FAMILY[OS]
    return None


def covers_cjk(font_file: str | Path) -> bool | None:
    """Does this font actually have CJK glyphs? None = cannot tell.

    `fc-match` never fails — ask it for an uninstalled Chinese family and it
    returns DejaVu Sans, which renders tofu while the encode *succeeds*. Reading
    the cmap is the only honest check. fontTools is imported lazily so this
    module stays usable before dependencies are installed.
    """
    try:
        from fontTools.ttLib import TTFont

        with TTFont(str(font_file), fontNumber=0, lazy=True) as font:
            cmap = font.getBestCmap()
    except Exception:
        return None
    # 你好 + 一 (CJK Unified Ideographs) — a face without these cannot render
    # Chinese subtitles no matter what fontconfig claims.
    return all(ord(ch) in cmap for ch in "你好一")


def diagnose() -> dict:
    """Everything the env doctor needs in one call (no printing, no fixing)."""
    dirs = font_dirs()
    regular = find_cjk_font("regular")
    bold = find_cjk_font("bold")
    return {"platform": OS,
            "override_dirs": [str(d) for d in override_dirs()],
            "searched_dirs": [str(d) for d in dirs],
            "existing_dirs": [str(d) for d in dirs if d.is_dir()],
            "regular": regular,
            "bold": bold,
            "covers_cjk": covers_cjk(regular) if regular else None,
            "ass_font_name": ass_font_name(),
            "fontconfig": bool(shutil.which("fc-match")),
            "default_family": _DEFAULT_FAMILY[OS]}
