#!/usr/bin/env python3
"""Extract the latest built-in ImageGen PNG results from a Codex rollout JSONL."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--count", required=True, type=int)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--names", required=True, help="Comma-separated output basenames")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = [item.strip() for item in args.names.split(",") if item.strip()]
    if args.count <= 0 or len(names) != args.count:
        raise SystemExit("--count must be positive and equal the number of --names")

    results: list[str] = []
    with args.session.expanduser().open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload", {})
            if payload.get("type") != "image_generation_call":
                continue
            result = payload.get("result")
            if isinstance(result, str) and result:
                results.append(result)

    selected = results[-args.count :]
    if len(selected) != args.count:
        raise SystemExit(f"found only {len(selected)} usable image results")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, encoded in zip(names, selected, strict=True):
        output = args.out_dir / f"{name}.png"
        output.write_bytes(base64.b64decode(encoded))
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
