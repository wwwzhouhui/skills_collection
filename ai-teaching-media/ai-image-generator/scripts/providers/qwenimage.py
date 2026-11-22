"""Alibaba Cloud Model Studio Qwen-Image provider (sync multimodal generation)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Optional

from .base import BaseProvider, http_request


ASPECT_RATIO_TO_SIZE = {
    "1:1": "2048*2048",
    "16:9": "2688*1536",
    "9:16": "1536*2688",
    "4:3": "2368*1728",
    "3:4": "1728*2368",
    "3:2": "2304*1536",
    "2:3": "1536*2304",
}

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_MODEL = "qwen-image-2.0-pro-2026-06-22"


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    value = int(str(raw).strip())
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _normalize_base_url(raw: str) -> str:
    base = (raw or DEFAULT_BASE_URL).rstrip("/")
    if base.endswith("/compatible-mode/v1"):
        return base[: -len("/compatible-mode/v1")] + "/api/v1"
    if base.endswith("/api/v1"):
        return base
    if "/api/v1/services/" in base:
        return base.split("/api/v1/services/", 1)[0] + "/api/v1"
    return base + "/api/v1"


class QwenImageProvider(BaseProvider):
    """Qwen-Image synchronous text-to-image provider.

    The API returns image URLs immediately, so generate.py stores the result in
    a local cache and exposes it through the common create/poll shape.
    """

    env_var = "QWEN_IMAGE_API_KEY"
    POLL_INTERVAL = 0
    POLL_MAX_TIMES = 1
    HTTP_TIMEOUT = 240
    HTTP_RETRIES = 1

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = _normalize_base_url(os.environ.get("QWEN_IMAGE_BASE_URL") or os.environ.get("QWEN_IMAGE_API_URL") or DEFAULT_BASE_URL)
        self.model = os.environ.get("QWEN_IMAGE_MODEL", DEFAULT_MODEL)
        self.http_timeout = _env_int("QWEN_IMAGE_HTTP_TIMEOUT", _env_int("IMAGE_HTTP_TIMEOUT", 240, 5), 5)
        self.http_retries = _env_int("QWEN_IMAGE_HTTP_RETRIES", _env_int("IMAGE_HTTP_RETRIES", 1, 0), 0)
        self.watermark = str(os.environ.get("QWEN_IMAGE_WATERMARK", "false")).strip().lower() in ("1", "true", "yes", "on")
        self.prompt_extend = str(os.environ.get("QWEN_IMAGE_PROMPT_EXTEND", "false")).strip().lower() in ("1", "true", "yes", "on")
        self._result_cache: dict[str, dict] = {}

    def _size_from_aspect_ratio(self, aspect_ratio: str, resolution: str) -> str:
        key = (aspect_ratio or "16:9").strip()
        if key not in ASPECT_RATIO_TO_SIZE:
            allowed = ", ".join(ASPECT_RATIO_TO_SIZE)
            raise ValueError(f"Qwen-Image does not support aspect_ratio={key!r} (allowed: {allowed})")
        return ASPECT_RATIO_TO_SIZE[key]

    def describe_output_size(self, aspect_ratio: str, resolution: str) -> dict:
        actual = self._size_from_aspect_ratio(aspect_ratio, resolution)
        return {
            "requested_aspect_ratio": aspect_ratio,
            "requested_resolution": resolution,
            "actual_size": actual,
            "resolution_honored": False,
            "notes": "Qwen-Image uses size values mapped from aspect_ratio; --resolution is ignored",
        }

    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        if mode == "edit":
            raise ValueError("Qwen-Image provider currently supports generation only")
        size = self._size_from_aspect_ratio(aspect_ratio, resolution)
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {
                "size": size,
                "n": 1,
                "prompt_extend": self.prompt_extend,
                "watermark": self.watermark,
            },
        }
        return f"{self.base_url}/services/aigc/multimodal-generation/generation", payload

    def parse_task_id(self, resp: dict) -> Optional[str]:
        body = resp.get("body") if isinstance(resp, dict) else None
        if isinstance(body, dict):
            return body.get("request_id") or body.get("id")
        return None

    def build_poll_url(self, task_id: str, mode: str) -> str:
        return f"{self.base_url}/services/aigc/multimodal-generation/generation/{task_id}"

    def parse_poll_status(self, resp: dict) -> tuple[str, dict]:
        body = resp.get("body", {}) if isinstance(resp, dict) else {}
        if not isinstance(body, dict):
            return "failed", {"error": body}
        if body.get("code") or body.get("message"):
            return "failed", body
        return "completed", body

    def extract_images(self, poll_body: dict) -> list[str]:
        urls: list[str] = []
        choices = poll_body.get("output", {}).get("choices", [])
        if isinstance(choices, list):
            for choice in choices:
                content = choice.get("message", {}).get("content", []) if isinstance(choice, dict) else []
                if not isinstance(content, list):
                    continue
                for item in content:
                    image = item.get("image") if isinstance(item, dict) else None
                    if isinstance(image, str) and image:
                        urls.append(image)
        return urls

    def create_task(
        self, prompt: str, mode: str,
        images: Optional[list[str]] = None,
        aspect_ratio: str = "16:9", resolution: str = "2K",
    ) -> Optional[str]:
        try:
            create_url, payload = self.build_create_payload(
                prompt, mode, images, aspect_ratio, resolution
            )
        except ValueError as e:
            print(f"    x Qwen-Image parameter error: {e}")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        size_meta = self.describe_output_size(aspect_ratio, resolution)
        print(
            f"    -> Qwen-Image sync generation model={self.model} size={payload['parameters'].get('size')} "
            f"(requested_resolution={resolution}, resolution_honored=false)"
        )
        resp = http_request(
            "POST", create_url, headers, json.dumps(payload).encode("utf-8"),
            timeout=self.http_timeout, retries=self.http_retries,
        )
        if not (200 <= resp.get("status", 0) < 300):
            print(f"    x Create task failed, HTTP {resp.get('status')}")
            print(f"      Response: {resp.get('body')}")
            return None

        body = resp.get("body")
        if not isinstance(body, dict):
            print(f"    x Qwen-Image returned non-JSON object: {body}")
            return None

        image_urls = self.extract_images(body)
        if not image_urls:
            print(f"    x Qwen-Image returned no image: {json.dumps(body, ensure_ascii=False)[:300]}")
            return None

        task_id = str(body.get("request_id") or uuid.uuid4())
        self._result_cache[task_id] = {
            "images": image_urls,
            "raw": body,
            "size_meta": size_meta,
        }
        print(f"    ok Qwen-Image sync completed, task_id={task_id[:8]}..., images={len(image_urls)}")
        return task_id

    def poll_task(self, task_id: str, mode: str) -> Optional[dict]:
        cached = self._result_cache.pop(task_id, None)
        if not cached:
            print(f"    x Missing local Qwen-Image task cache: {task_id}")
            return None
        return {
            "images": cached.get("images", []),
            "size_meta": cached.get("size_meta"),
        }
