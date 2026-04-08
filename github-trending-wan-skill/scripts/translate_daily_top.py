#!/usr/bin/env python3
"""Translate trending summary fields into Simplified Chinese via DashScope compatible chat API."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_INPUT = "output/daily_top10.json"
DEFAULT_OUTPUT = "output/daily_top5_zh.json"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_CANDIDATES = [
    "kimi-k2.5",
    "qwen3.5-flash-2026-02-23",
    "qwen3.5-397b-a17b",
    "MiniMax-M2.5",
    "qwen3.5-35b-a3b",
    "qwen3.5-plus",
    "qwen3.5-plus-2026-02-15",
    "glm-5",
    "qwen3-max-2026-01-23",
    "qwen3.5-27b",
    "tongyi-xiaomi-analysis-flash",
    "qwen3.6-plus-2026-04-02",
]
ENGLISH_RE = re.compile(r"[A-Za-z]")
CODE_BLOCK_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str, data: dict[str, Any]) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def ensure_env() -> str:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError("缺少 DASHSCOPE_API_KEY，无法执行中文翻译。")
    return api_key


def normalize_base_url(base_url: str | None) -> str:
    candidate = (base_url or os.getenv("DASHSCOPE_COMPATIBLE_BASE_URL") or "").strip()
    if not candidate:
        candidate = os.getenv("DASHSCOPE_BASE_URL", "").strip()
    if not candidate:
        return DEFAULT_BASE_URL

    candidate = candidate.rstrip("/")
    if candidate.endswith("/compatible-mode/v1"):
        return candidate
    if candidate.endswith("/api/v1"):
        return f"{candidate[:-7]}/compatible-mode/v1"
    if candidate.endswith("/v1"):
        return candidate
    return f"{candidate}/compatible-mode/v1"


def contains_english(value: str) -> bool:
    return bool(value and ENGLISH_RE.search(value))


def should_translate_list(values: list[str]) -> bool:
    return any(contains_english(value) for value in values)


def extract_response_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("翻译接口未返回 choices")
    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
        content = "".join(chunks)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("翻译接口返回空内容")
    return content.strip()


def parse_json_text(text: str) -> dict[str, Any]:
    cleaned = CODE_BLOCK_RE.sub("", text).strip()
    return json.loads(cleaned)


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def translate_item(item: dict[str, Any], api_key: str, base_url: str, model: str) -> tuple[dict[str, Any], int]:
    fields = {
        "description": item.get("description", ""),
        "summary_intro": item.get("summary_intro", ""),
        "tech_stack": item.get("tech_stack") or [],
        "target_users": item.get("target_users", ""),
    }
    if not (
        contains_english(fields["description"])
        or contains_english(fields["summary_intro"])
        or contains_english(fields["target_users"])
        or should_translate_list(fields["tech_stack"])
    ):
        return item, 0

    endpoint = f"{base_url}/chat/completions"
    system_prompt = (
        "你是技术内容翻译助手。请把输入字段翻译成简体中文，要求忠实、简洁、不扩写。"
        "保留仓库名、编程语言名、框架名、产品名、协议名和常见技术术语；"
        "如果技术栈条目本身就是专有名词，可直接保留；返回 JSON，不要加解释。"
    )
    user_prompt = json.dumps(
        {
            "task": "translate_fields_to_zh_cn",
            "schema": {
                "description": "string",
                "summary_intro": "string",
                "tech_stack": ["string"],
                "target_users": "string",
            },
            "input": fields,
        },
        ensure_ascii=False,
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    response = post_json(endpoint, headers, payload)
    translated = parse_json_text(extract_response_text(response))
    result = dict(item)
    result["description"] = translated.get("description", fields["description"]).strip() or fields["description"]
    result["summary_intro"] = translated.get("summary_intro", fields["summary_intro"]).strip() or fields["summary_intro"]
    tech_stack = translated.get("tech_stack", fields["tech_stack"])
    if isinstance(tech_stack, list):
        result["tech_stack"] = [str(value).strip() for value in tech_stack if str(value).strip()]
    result["target_users"] = translated.get("target_users", fields["target_users"]).strip() or fields["target_users"]
    changed_count = sum(
        1
        for key in ("description", "summary_intro", "target_users")
        if result.get(key) != item.get(key)
    )
    if result.get("tech_stack") != item.get("tech_stack"):
        changed_count += 1
    return result, changed_count


def translate_payload(data: dict[str, Any], api_key: str, base_url: str, model: str) -> tuple[dict[str, Any], int]:
    translated = deepcopy(data)
    items = translated.get("items") or []
    total_changes = 0
    translated_items: list[dict[str, Any]] = []
    for item in items:
        translated_item, changed_count = translate_item(item, api_key, base_url, model)
        translated_items.append(translated_item)
        total_changes += changed_count
    translated["items"] = translated_items
    translated["translation_model"] = model
    translated["translated_at"] = datetime.now(timezone.utc).isoformat()
    translated["translation_target_language"] = "zh-CN"
    translated["translation_changed_fields"] = total_changes
    return translated, total_changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Translate daily trending summary fields into Simplified Chinese")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input JSON path")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON path")
    parser.add_argument("--model", default="", help="Optional explicit model; default picks one random candidate")
    parser.add_argument("--base-url", default="", help="Optional compatible-mode base URL")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = ensure_env()
    model = args.model.strip() or random.choice(MODEL_CANDIDATES)
    base_url = normalize_base_url(args.base_url)
    try:
        data = read_json(args.input)
        translated, changed_count = translate_payload(data, api_key, base_url, model)
        save_json(args.output, translated)
    except (FileNotFoundError, json.JSONDecodeError, HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"翻译失败: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"已保存: {args.output}")
    print(f"翻译模型: {model}")
    print(f"字段变更数: {changed_count}")


if __name__ == "__main__":
    main()
