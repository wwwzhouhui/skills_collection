#!/usr/bin/env python3
"""Standalone Wan 2.7 image generation script."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"


def read_prompt(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt 文件不存在: {path}")
    content = path.read_text(encoding="utf-8")
    return content.strip()


def resolve_size(size: str, ratio: str) -> str:
    """Resolve K-based size to actual pixels."""
    size_map = {
        "1K": {"3:4": "1024*1365", "4:3": "1365*1024", "1:1": "1024*1024", "16:9": "1820*1024"},
        "2K": {"3:4": "1774*2364", "4:3": "2364*1774", "1:1": "2048*2048", "16:9": "2730*1536"},
        "4K": {"3:4": "2688*3584", "4:3": "3584*2688", "1:1": "4096*4096", "16:9": "3840*2160"},
    }
    normalized = size.upper().strip()
    if normalized in size_map and ratio in size_map[normalized]:
        return size_map[normalized][ratio]
    if "*" in size or "x" in size.lower():
        return size.replace("x", "*").replace("X", "*")
    return size


def call_api(api_key: str, prompt: str, size: str, n: int) -> dict:
    """Call DashScope Wan 2.7 API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    payload = {
        "model": "wanx2.1-t2i-turbo",
        "input": {
            "prompt": prompt,
        },
        "parameters": {
            "size": size,
            "n": n,
            "prompt_extend": True,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"API 错误 {e.code}: {error_body}")


def poll_task(api_key: str, task_id: str, max_wait: int = 300) -> dict:
    """Poll for task completion."""
    url = f"{API_URL}/{task_id}"
    headers = {"Authorization": f"Bearer {api_key}"}

    start = time.time()
    status = "PENDING"
    while time.time() - start < max_wait:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                status = result.get("output", {}).get("task_status", "PENDING")
                if status in ("SUCCEEDED", "FAILED", "UNKNOWN"):
                    return result
        except urllib.error.HTTPError as e:
            print(f"查询错误: {e.code}", file=sys.stderr)

        print(f"任务状态: {status}, 等待中...")
        time.sleep(5)

    raise TimeoutError(f"任务超时 ({max_wait}秒)")


def main():
    parser = argparse.ArgumentParser(description="Wan 2.7 独立生图脚本")
    parser.add_argument("--prompt", required=True, help="Prompt 文件路径")
    parser.add_argument("--size", default="2K", help="尺寸 (1K/2K/4K 或 W*H)")
    parser.add_argument("--ratio", default="3:4", help="比例 (3:4/4:3/1:1/16:9)")
    parser.add_argument("--n", type=int, default=1, help="生成数量")
    args = parser.parse_args()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("错误: 缺少 DASHSCOPE_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    prompt_path = Path(args.prompt)
    prompt = read_prompt(prompt_path)
    size = resolve_size(args.size, args.ratio)

    print(f"开始调用 Wan 2.7:")
    print(f"  - prompt: {prompt_path}")
    print(f"  - size: {size}")
    print(f"  - n: {args.n}")

    # Submit task
    result = call_api(api_key, prompt, size, args.n)
    task_id = result.get("output", {}).get("task_id")

    if not task_id:
        print(f"错误: 未获取到 task_id: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"任务已提交: TASK_ID: {task_id}")

    # Poll for result
    final_result = poll_task(api_key, task_id)
    output = final_result.get("output", {})
    status = output.get("task_status", "UNKNOWN")

    print(f"\n任务状态: {status}")

    if status == "SUCCEEDED":
        results = output.get("results", [])
        for i, r in enumerate(results, 1):
            url = r.get("url", "")
            print(f"result No.{i}: {url}")

        # Save result
        output_dir = Path(__file__).parent.parent / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        result_file = output_dir / "wan_result.json"

        result_data = {
            "task_id": task_id,
            "status": status,
            "image_urls": [r.get("url") for r in results],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "prompt_path": str(prompt_path),
            "size": size,
        }

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        print(f"\n已保存结果: {result_file}")
    else:
        print(f"生成失败: {output.get('message', '未知错误')}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()