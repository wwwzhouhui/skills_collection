"""Shared subprocess runner for the MCP tools.

Why this exists
---------------
The MCP server speaks JSON-RPC over its stdin/stdout. Every child process
*inherits* that stdin pipe unless we detach it. ffmpeg in particular reads one
byte from stdin on startup (for interactive "overwrite [y/N]" prompting); under
the MCP stdio transport that byte is stolen from the JSON-RPC input stream,
silently corrupting the next pipelined message (a parallel tool call, a
``notifications/cancelled``, or a ping). The client then blocks until
``timeoutMs`` (15 min) elapses with nothing in the transcript explaining it.

The fix is universal and does not depend on how ``cmd`` is shaped:

* force ``stdin=DEVNULL`` on every command (the real defense), and
* inject ``-nostdin`` for ffmpeg as belt-and-braces (also stops prompts).

We also enforce a default timeout so no call can wedge the single-worker server
forever (``server_common`` runs tools on ``ThreadPoolExecutor(max_workers=1)``).
"""
from __future__ import annotations

import re as _re
import shutil
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 3600


def run_proc(cmd: list[str], *args, timeout: float | None = None, **kwargs):
    """Drop-in replacement for :func:`subprocess.run` that is safe inside an
    MCP stdio server.

    Differences from ``subprocess.run``:
      * ``stdin`` defaults to :data:`subprocess.DEVNULL` (overridable).
      * ``-nostdin`` is injected right after the ffmpeg binary when absent.
      * ``timeout`` defaults to :data:`DEFAULT_TIMEOUT` when not supplied.

    Everything else (``capture_output``, ``text``, ``check``, ``stdout`` ...)
    is passed through unchanged.
    """
    kwargs.setdefault("stdin", subprocess.DEVNULL)
    if cmd and Path(cmd[0]).name == "ffmpeg" and "-nostdin" not in cmd:
        cmd = [cmd[0], "-nostdin", *cmd[1:]]
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    return subprocess.run(cmd, *args, timeout=timeout, **kwargs)


# ---------------------------------------------------------------------------
# ffmpeg filtergraph escaping
#
# ffmpeg runs its own mini-parser over -vf/-filter_complex strings. Quoting
# discipline decides whether an agent-authored string can break out of its
# option and inject new filters (movie=/amovie= → arbitrary local file read /
# SSRF). Three contexts, three escapers:
# ---------------------------------------------------------------------------

def escape_text(value) -> str:
    """Escape arbitrary text for an ffmpeg ``drawtext=text='...'`` value.

    The result must be placed between single quotes in the filtergraph. Inside
    that quoted region commas/colons are literal, so we only need to neutralise
    the two chars that can terminate or alter the quote: backslash and the
    single quote itself. Order matters — backslash first, then the standard
    close-quote/escaped-quote/reopen trick (``'\\'''``)."""
    s = "" if value is None else str(value)
    return s.replace("\\", "\\\\").replace("'", "'\\''")


# Chars that are structurally meaningful in an *unquoted* filter option value:
# they terminate an option (`,`) or a filter (`;`), open/close a labelled pad
# (`[` `]`), separate option from value (`:`), or start/end quoting (`'`) /
# escaping (`\`). All must be backslash-escaped.
_UNQUOTED_SPECIAL = ("\\", ":", "'", ",", ";", "[", "]")


def escape_option(value) -> str:
    """Escape an unquoted ffmpeg filter option value (fontfile path,
    fontcolor, boxcolor, ...). Backslash is escaped first so the escaping we
    then insert for the other specials is not itself re-doubled."""
    s = "" if value is None else str(value)
    for ch in _UNQUOTED_SPECIAL:
        s = s.replace(ch, "\\" + ch)
    return s


# drawtext/overlay ``x=`` / ``y=`` hold arithmetic over w/h/text_w/text_h, not
# new options. Accept the expression chars only; anything that could break out
# of the option (``: ; ' " \ [ ] =``) forces the safe default instead.
_EXPR_OK = _re.compile(r"^[A-Za-z0-9_+\-*/().<> ,]*$")


def safe_expr(value, default: str) -> str:
    """Return ``value`` only if it is a benign drawtext/overlay geometry
    expression; otherwise return ``default``."""
    s = "" if value is None else str(value).strip()
    if s and _EXPR_OK.match(s):
        return s
    return default


# ---------------------------------------------------------------------------
# Fail-fast capability check
#
# conda / static / minimal ffmpeg builds frequently drop libx264, libmp3lame
# or libass. The encode or filter only fails at the *last* step, after minutes
# of rendering — "前面全白跑". Probe the build up front so we return a clear
# [ERROR] before the long job, not a stderr tail at the end.
# ---------------------------------------------------------------------------
_FEATURE_CACHE: dict[str, str] = {}


def _ffmpeg_feature_text(kind: str) -> str:
    """Cached ``ffmpeg -<kind>`` listing (kind in {"encoders", "filters"}).
    Empty string when ffmpeg is absent or the listing can't be obtained."""
    exe = shutil.which("ffmpeg")
    if not exe:
        return ""
    if kind not in _FEATURE_CACHE:
        try:
            proc = subprocess.run(
                [exe, "-hide_banner", f"-{kind}"],
                capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL,
            )
            _FEATURE_CACHE[kind] = (proc.stdout or "") + (proc.stderr or "")
        except Exception:  # noqa: BLE001
            _FEATURE_CACHE[kind] = ""
    return _FEATURE_CACHE[kind]


def require_ffmpeg(*, encoders: tuple[str, ...] = (), filters: tuple[str, ...] = ()) -> str | None:
    """Return an error string if ffmpeg is missing or lacks any requested
    encoder/filter; ``None`` when OK. Call at the top of a long render so a
    feature-missing build fails in milliseconds, not after a full encode."""
    if not shutil.which("ffmpeg"):
        return "[ERROR] ffmpeg not found on PATH"
    enc_text = _ffmpeg_feature_text("encoders")
    fil_text = _ffmpeg_feature_text("filters")
    miss_enc = [e for e in encoders if enc_text and e not in enc_text]
    miss_fil = [f for f in filters if fil_text and f" {f} " not in fil_text]
    if not (miss_enc or miss_fil):
        return None
    parts = []
    if miss_enc:
        parts.append("encoders missing: " + ", ".join(miss_enc))
    if miss_fil:
        parts.append("filters missing: " + ", ".join(miss_fil))
    return (
        "[ERROR] this ffmpeg build lacks required features (" + "; ".join(parts)
        + "). It was compiled without them; install a full build (conda-forge ffmpeg, "
        "or your platform's full package). Run /env-check for a fix command."
    )
