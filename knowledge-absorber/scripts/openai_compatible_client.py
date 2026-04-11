from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


class OpenAICompatibleError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def normalize_connection(connection: Dict[str, Any]) -> Dict[str, str]:
    normalized = {
        "base_url": str(connection.get("baseUrl") or connection.get("base_url") or "").strip(),
        "model": str(connection.get("model") or "").strip(),
        "api_key": str(connection.get("apiKey") or connection.get("api_key") or "").strip(),
    }
    if not normalized["base_url"]:
        raise OpenAICompatibleError("请填写 Base URL。", 400)
    if not normalized["model"]:
        raise OpenAICompatibleError("请填写模型名称。", 400)
    if not normalized["api_key"]:
        raise OpenAICompatibleError("请填写 API Key。", 400)
    return normalized


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def looks_like_direct_endpoint(base_url: str) -> bool:
    normalized = normalize_base_url(base_url).lower()
    return normalized.endswith("/chat/completions") or normalized.endswith("/responses")


def build_endpoint_candidates(base_url: str) -> List[Tuple[str, str]]:
    normalized = normalize_base_url(base_url)
    candidates: List[Tuple[str, str]] = []

    def add_candidate(url: str, mode: str) -> None:
        item = (url, mode)
        if item not in candidates:
            candidates.append(item)

    if looks_like_direct_endpoint(normalized):
        add_candidate(normalized, "responses" if normalized.lower().endswith("/responses") else "chat")
        return candidates

    direct_candidates = [
        (f"{normalized}/chat/completions", "chat"),
        (f"{normalized}/responses", "responses"),
    ]
    versioned_candidates = [
        (f"{normalized}/v1/chat/completions", "chat"),
        (f"{normalized}/v1/responses", "responses"),
    ]

    has_version_segment = bool(re.search(r"/v\d+(/|$)", normalized, re.IGNORECASE))
    ordered = direct_candidates if has_version_segment else [*versioned_candidates, *direct_candidates]
    for url, mode in ordered:
        add_candidate(url, mode)
    add_candidate(normalized, "chat")
    return candidates


def build_request_body(mode: str, connection: Dict[str, str], messages: List[Dict[str, str]], options: Dict[str, Any]) -> Dict[str, Any]:
    if mode == "responses":
        return {
            "model": connection["model"],
            "input": [
                {
                    "role": message["role"],
                    "content": [{"type": "input_text", "text": message["content"]}],
                }
                for message in messages
            ],
            "temperature": options.get("temperature", 0.2),
            "max_output_tokens": options.get("maxTokens", 2000),
        }
    return {
        "model": connection["model"],
        "messages": messages,
        "temperature": options.get("temperature", 0.2),
        "max_tokens": options.get("maxTokens", 2000),
    }


def resolve_timeout_seconds(options: Dict[str, Any]) -> float:
    raw_timeout = options.get("timeoutSeconds", 60)
    try:
        timeout_value = float(raw_timeout)
    except (TypeError, ValueError):
        timeout_value = 60.0
    return min(max(timeout_value, 5.0), 300.0)


def extract_assistant_text(payload: Dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"].strip()
    output = payload.get("output")
    if isinstance(output, list):
        collected: List[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for segment in item.get("content", []):
                if not isinstance(segment, dict):
                    continue
                text = segment.get("text")
                if isinstance(text, str) and text.strip():
                    collected.append(text.strip())
        if collected:
            return "\n".join(collected).strip()
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = (message or {}).get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
                    parts.append(item["text"].strip())
            if parts:
                return "\n".join(parts).strip()
    return ""


def forward_request(connection: Dict[str, str], messages: List[Dict[str, str]], options: Dict[str, Any]) -> Dict[str, Any]:
    timeout_seconds = resolve_timeout_seconds(options)
    allow_empty_content = bool(options.get("allowEmptyContent"))
    attempted: List[str] = []
    last_error = ""
    for endpoint, mode in build_endpoint_candidates(connection["base_url"]):
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {connection['api_key']}",
                },
                json=build_request_body(mode, connection, messages, options),
                timeout=timeout_seconds,
            )
        except requests.ReadTimeout:
            raise OpenAICompatibleError(
                f"请求超时：模型接口在 {int(timeout_seconds)} 秒内没有返回结果。请检查模型负载，或把当前任务拆小后重试。",
                504,
            )
        except requests.RequestException as exc:
            raise OpenAICompatibleError(f"请求发送失败：{exc}", 502) from exc

        attempted.append(f"{endpoint} -> {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenAICompatibleError(f"接口返回了非 JSON 响应（HTTP {response.status_code}）。", 502) from exc

        if response.ok:
            content = extract_assistant_text(payload)
            if not content:
                if allow_empty_content:
                    return {
                        "content": "",
                        "endpoint": endpoint,
                        "mode": mode,
                        "empty_content": True,
                    }
                raise OpenAICompatibleError("模型接口已响应，但没有返回可读内容。", 502)
            return {"content": content, "endpoint": endpoint, "mode": mode, "empty_content": False}

        api_message = (payload.get("error") or {}).get("message") or payload.get("message") or f"HTTP {response.status_code}"
        last_error = str(api_message)
        if response.status_code in {401, 403}:
            raise OpenAICompatibleError(f"认证失败：{api_message}", response.status_code)
        if response.status_code in {404, 405}:
            continue
        raise OpenAICompatibleError(f"接口请求失败：{api_message}", response.status_code)

    raise OpenAICompatibleError(
        f"接口地址可能不兼容：所有候选端点都未找到。已尝试 {'；'.join(attempted)}。{(' 最后错误：' + last_error) if last_error else ''}",
        404,
    )


def chat_text(connection: Dict[str, str], system_prompt: str, user_prompt: str, temperature: float = 0.2, max_tokens: int = 2000, timeout_seconds: float = 120) -> str:
    result = forward_request(
        connection=normalize_connection(connection),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={
            "temperature": temperature,
            "maxTokens": max_tokens,
            "timeoutSeconds": timeout_seconds,
        },
    )
    return result["content"]


def load_profile_connection(profile_path: Path) -> Optional[Dict[str, str]]:
    if not profile_path.exists():
        return None
    payload = json.loads(profile_path.read_text(encoding="utf-8-sig"))
    profile = payload.get("default_profile")
    if not isinstance(profile, dict):
        raise OpenAICompatibleError("profile file must contain a default_profile object", 400)
    return normalize_connection(profile)


def load_env_connection() -> Optional[Dict[str, str]]:
    base_url = os.getenv("KA_BASE_URL", "").strip()
    model = os.getenv("KA_MODEL", "").strip()
    api_key = os.getenv("KA_API_KEY", "").strip()
    if not any([base_url, model, api_key]):
        return None
    return normalize_connection({"base_url": base_url, "model": model, "api_key": api_key})


def resolve_generation_connection(profile_path: Path) -> Optional[Dict[str, str]]:
    profile_connection = load_profile_connection(profile_path)
    if profile_connection:
        return profile_connection
    return load_env_connection()
