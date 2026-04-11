#!/usr/bin/env python3
"""Run Wan 2.7 generation with a prepared prompt file for knowledge posters."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = SKILL_ROOT / "outputs"

# Try to find Wan skill directory
WAN_SKILL_DIR = Path(os.environ.get("WAN_SKILL_DIR", ""))
if not WAN_SKILL_DIR.exists():
    # Try common locations
    candidate_paths = [
        SKILL_ROOT.parent / "Wan-skills-main" / "skills" / "wan2.7-image-skill",
        SKILL_ROOT.parent.parent / "Wan-skills-main" / "skills" / "wan2.7-image-skill",
        Path.home() / ".claude" / "skills" / "Wan-skills-main" / "skills" / "wan2.7-image-skill",
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            WAN_SKILL_DIR = candidate
            break

WAN_SCRIPTS_DIR = WAN_SKILL_DIR / "scripts" if WAN_SKILL_DIR.exists() else None
WAN_SCRIPT = WAN_SCRIPTS_DIR / "image-generation-editing.py" if WAN_SCRIPTS_DIR else None
CHECK_SCRIPT = WAN_SCRIPTS_DIR / "check_wan_task_status.py" if WAN_SCRIPTS_DIR else None
PARSE_RESOLUTION_SCRIPT = WAN_SCRIPTS_DIR / "parse_resolution.py" if WAN_SCRIPTS_DIR else None

DEFAULT_PROMPT_PATH = OUTPUT_DIR / "wan_prompt.txt"
RESULT_FILE = "wan_result.json"

URL_PATTERN = re.compile(r"result No\.\s*\d+:\s+(https?://\S+)")
TASK_ID_PATTERN = re.compile(r"(?:Dashscope\s+)?TASK_ID:\s+(\S+)", re.IGNORECASE)


def ensure_script(path: Path | None, label: str) -> None:
    if path is None or not path.is_file():
        raise FileNotFoundError(
            f"缺少{label}脚本: {path}\n"
            f"请确保 Wan-skills-main 已安装，或设置 WAN_SKILL_DIR 环境变量"
        )


def read_prompt(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt 文件不存在: {path}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"Prompt 文件为空: {path}")
    return content.strip()


def resolve_size(size: str, ratio: str | None, parse_script: Path | None) -> str:
    normalized_size = size.strip()
    if not ratio:
        return normalized_size
    if "*" in normalized_size or "x" in normalized_size.lower():
        return normalized_size

    if parse_script and parse_script.is_file():
        command = [sys.executable, str(parse_script), f"{normalized_size} {ratio}"]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

    # Fallback: manual resolution mapping
    size_map = {
        "1K": {"3:4": "1024*1365", "4:3": "1365*1024", "1:1": "1024*1024", "16:9": "1820*1024"},
        "2K": {"3:4": "1774*2364", "4:3": "2364*1774", "1:1": "2048*2048", "16:9": "2730*1536"},
        "4K": {"3:4": "2688*3584", "4:3": "3584*2688", "1:1": "4096*4096", "16:9": "3840*2160"},
    }
    if normalized_size in size_map and ratio in size_map[normalized_size]:
        return size_map[normalized_size][ratio]

    return normalized_size


def ensure_env() -> None:
    if not os.getenv("DASHSCOPE_API_KEY"):
        raise EnvironmentError(
            "缺少 DASHSCOPE_API_KEY 环境变量。\n"
            "请设置: export DASHSCOPE_API_KEY='your-api-key'"
        )


def build_command(prompt: str, size: str, sequential: bool, number: int, wan_script: Path) -> list[str]:
    command = [
        sys.executable,
        str(wan_script),
        "--user_requirement",
        prompt,
        "--n",
        str(number),
        "--size",
        size,
    ]
    if sequential:
        command.append("--enable_sequential")
    return command


def run_subprocess(command: list[str], action: str) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    stdout = result.stdout or ""
    if stdout:
        print(stdout, end="" if stdout.endswith("\n") else "\n")
    if result.returncode != 0:
        detail = (result.stderr or stdout).strip() or f"{action}失败"
        print(detail, file=sys.stderr)
    return result.returncode, stdout


def parse_generation_output(stdout: str) -> dict:
    urls = URL_PATTERN.findall(stdout)
    task_id_match = TASK_ID_PATTERN.search(stdout)
    task_id = task_id_match.group(1) if task_id_match else ""
    if urls:
        status = "SUCCEEDED"
    elif task_id:
        status = "PENDING"
    else:
        status = "UNKNOWN"
    return {
        "task_id": task_id,
        "image_urls": urls,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }


def save_result(result_data: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = OUTPUT_DIR / RESULT_FILE
    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(result_data, handle, ensure_ascii=False, indent=2)
    print(f"已保存结果: {result_path}")
    return result_path


def run_generation(
    prompt_path: Path,
    size: str,
    ratio: str | None,
    sequential: bool,
    number: int,
) -> int:
    ensure_env()

    if WAN_SCRIPT is None:
        raise FileNotFoundError("Wan 脚本目录未找到，请设置 WAN_SKILL_DIR 环境变量")

    ensure_script(WAN_SCRIPT, "Wan 生成")
    prompt = read_prompt(prompt_path)
    resolved_size = resolve_size(size, ratio, PARSE_RESOLUTION_SCRIPT)
    command = build_command(prompt, resolved_size, sequential, number, WAN_SCRIPT)

    print(f"开始调用 Wan 2.7 生图:")
    print(f"  - prompt: {prompt_path}")
    print(f"  - size: {resolved_size}")
    print(f"  - n: {number}")

    code, stdout = run_subprocess(command, "Wan 生图")
    result_data = parse_generation_output(stdout)
    result_data["prompt_path"] = str(prompt_path)
    result_data["size"] = resolved_size
    result_data["number"] = number
    save_result(result_data)
    return code


def check_task(task_id: str) -> int:
    ensure_env()

    if CHECK_SCRIPT is None:
        raise FileNotFoundError("Wan 任务查询脚本未找到")

    ensure_script(CHECK_SCRIPT, "Wan 任务查询")
    command = [sys.executable, str(CHECK_SCRIPT), "--task_id", task_id]
    print(f"开始查询 Wan 任务: task_id={task_id}")
    code, stdout = run_subprocess(command, "Wan 任务查询")
    result_data = parse_generation_output(stdout)
    result_data["task_id"] = task_id
    save_result(result_data)
    return code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Wan 2.7 generation for knowledge posters")
    parser.add_argument("--prompt", default=str(DEFAULT_PROMPT_PATH), help="Prompt file path")
    parser.add_argument("--size", default="2K", help="Requested size, e.g. 2K or 1774*2364")
    parser.add_argument("--ratio", default="3:4", help="Aspect ratio used when size is K-based")
    parser.add_argument("--sequential", action="store_true", help="Enable sequential multi-image generation")
    parser.add_argument("--n", type=int, default=1, help="Number of images to request")
    parser.add_argument("--task-id", default="", help="Existing task id to query instead of generating")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        if args.task_id:
            code = check_task(args.task_id)
        else:
            code = run_generation(
                prompt_path=Path(args.prompt),
                size=args.size,
                ratio=args.ratio,
                sequential=args.sequential,
                number=args.n,
            )
    except (EnvironmentError, FileNotFoundError, ValueError) as exc:
        print(f"执行失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    raise SystemExit(code)


if __name__ == "__main__":
    main()