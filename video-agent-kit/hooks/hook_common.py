from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def project_dir() -> Path:
    value = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("VE_PROJECT_DIR")
    return Path(value).resolve() if value else Path.cwd().resolve()


def plugin_root() -> Path:
    value = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("VE_PLUGIN_ROOT")
    return Path(value).resolve() if value else Path(__file__).resolve().parents[1]


def read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read()
        value = json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}
    # CC 总是发 object; 防御性归一, 非 dict 输入不该让 hook 以 AttributeError 崩掉
    return value if isinstance(value, dict) else {}


def state_dir() -> Path:
    value = os.environ.get("CLAUDE_PLUGIN_DATA")
    root = Path(value) if value else project_dir() / ".video_agent" / "hook_state"
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_scope(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z_.-]", "_", value.strip())
    return cleaned[:80] or "default"


def _strike_counter(rule: str, scope: str | None) -> Path:
    name = f"strike_{rule}" + (f"_{sanitize_scope(scope)}" if scope else "")
    return state_dir() / f"{name}.count"


def strike(rule: str, limit: int = 3, scope: str | None = None) -> tuple[int, bool]:
    """Count one violation. Counters are scoped (typically per session) so
    stale counts from earlier sessions cannot leak into a new one."""
    counter = _strike_counter(rule, scope)
    try:
        count = int(counter.read_text(encoding="utf-8").strip())
    except Exception:
        count = 0
    count += 1
    released = count >= limit
    if released:
        counter.write_text("0", encoding="utf-8")
        with (state_dir() / "violations.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"rule": rule, "scope": scope, "strikes": count}, ensure_ascii=False) + "\n")
    else:
        counter.write_text(str(count), encoding="utf-8")
    return count, released


def clear_strike(rule: str, scope: str | None = None) -> None:
    counter = _strike_counter(rule, scope)
    if counter.exists():
        counter.write_text("0", encoding="utf-8")


def block_stop(reason: str) -> None:
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    sys.exit(0)


def allow() -> None:
    sys.exit(0)
