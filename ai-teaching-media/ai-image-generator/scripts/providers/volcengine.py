"""Volcengine Ark Seedream image provider (sync OpenAI-compatible generations)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Optional

from .base import BaseProvider, http_request


# Seedream 5.0 requires total pixels >= 3_686_400.
ASPECT_RATIO_TO_SIZE = {
    "1:1": "1920x1920",
    "16:9": "2560x1440",
    "9:16": "1440x2560",
    "4:3": "2304x1728",
    "3:4": "1728x2304",
    "3:2": "2400x1600",
    "2:3": "1600x2400",
}

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/plan/v3"
DEFAULT_MODEL = "doubao-seedream-5.0-lite"


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    value = int(str(raw).strip())
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


class VolcengineProvider(BaseProvider):
    """Doubao Seedream via Volcengine Ark images generations API.

    API is synchronous: POST /images/generations returns image URL immediately.
    """

    env_var = "VOLCENGINE_API_KEY"
    create_url = f"{DEFAULT_BASE_URL}/images/generations"
    poll_url = f"{DEFAULT_BASE_URL}/images/generations"
    POLL_INTERVAL = 0
    POLL_MAX_TIMES = 1
    HTTP_TIMEOUT = 180
    HTTP_RETRIES = 2

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = os.environ.get("VOLCENGINE_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.model = os.environ.get("VOLCENGINE_IMAGE_MODEL", DEFAULT_MODEL)
        self.http_timeout = _env_int("VOLCENGINE_HTTP_TIMEOUT", _env_int("IMAGE_HTTP_TIMEOUT", 180, 5), 5)
        self.http_retries = _env_int("VOLCENGINE_HTTP_RETRIES", _env_int("IMAGE_HTTP_RETRIES", 2, 0), 0)
        self.watermark = str(os.environ.get("VOLCENGINE_WATERMARK", "false")).strip().lower() in ("1", "true", "yes", "on")
        self._result_cache: dict[str, dict] = {}

    def _size_from_aspect_ratio(self, aspect_ratio: str, resolution: str) -> str:
        key = (aspect_ratio or "16:9").strip()
        if key not in ASPECT_RATIO_TO_SIZE:
            allowed = ", ".join(ASPECT_RATIO_TO_SIZE)
            raise ValueError(f"Volcengine 不支持 aspect_ratio={key!r} (允许: {allowed})")
        return ASPECT_RATIO_TO_SIZE[key]

    def describe_output_size(self, aspect_ratio: str, resolution: str) -> dict:
        actual = self._size_from_aspect_ratio(aspect_ratio, resolution)
        return {
            "requested_aspect_ratio": aspect_ratio,
            "requested_resolution": resolution,
            "actual_size": actual,
            "resolution_honored": False,
            "notes": "Seedream uses fixed large sizes to satisfy min pixel constraint; --resolution is mapped via aspect_ratio",
        }

    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        if mode == "edit":
            # Seedream lite text-to-image endpoint; edit not supported here.
            raise ValueError("Volcengine Seedream 当前仅支持 generation 模式，不支持 edit")
        size = self._size_from_aspect_ratio(aspect_ratio, resolution)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "response_format": "url",
            "n": 1,
            "watermark": self.watermark,
        }
        return f"{self.base_url}/images/generations", payload

    def parse_task_id(self, resp: dict) -> Optional[str]:
        body = resp.get("body") if isinstance(resp, dict) else None
        if isinstance(body, dict):
            return body.get("id") or body.get("task_id")
        return None

    def build_poll_url(self, task_id: str, mode: str) -> str:
        return f"{self.base_url}/images/generations/{task_id}"

    def parse_poll_status(self, resp: dict) -> tuple[str, dict]:
        body = resp.get("body", {}) if isinstance(resp, dict) else {}
        if not isinstance(body, dict):
            return "failed", {"error": body}
        if body.get("error"):
            return "failed", body
        return "completed", body

    def extract_images(self, poll_body: dict) -> list[str]:
        urls: list[str] = []
        data = poll_body.get("data")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                if isinstance(url, str) and url:
                    urls.append(url)
                    continue
                b64 = item.get("b64_json")
                if isinstance(b64, str) and b64:
                    urls.append(f"data:image/png;base64,{b64}")
        if not urls:
            url = poll_body.get("url") or poll_body.get("image")
            if isinstance(url, str) and url:
                urls.append(url)
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
            print(f"    ✗ Volcengine 参数错误: {e}")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        size_meta = self.describe_output_size(aspect_ratio, resolution)
        print(
            f"    → Volcengine 同步生图 model={self.model} size={payload.get('size')} "
            f"(requested_resolution={resolution}, resolution_honored=false)"
        )
        resp = http_request(
            "POST", create_url, headers, json.dumps(payload).encode("utf-8"),
            timeout=self.http_timeout, retries=self.http_retries,
        )
        if not (200 <= resp.get("status", 0) < 300):
            print(f"    ✗ 创建任务失败,HTTP {resp.get('status')}")
            print(f"      响应: {resp.get('body')}")
            return None

        body = resp.get("body")
        if not isinstance(body, dict):
            print(f"    ✗ Volcengine 返回非 JSON 对象: {body}")
            return None

        image_urls = self.extract_images(body)
        if not image_urls:
            print(f"    ✗ Volcengine 未返回图片: {json.dumps(body, ensure_ascii=False)[:300]}")
            return None

        task_id = str(uuid.uuid4())
        self._result_cache[task_id] = {
            "images": image_urls,
            "raw": body,
            "size_meta": size_meta,
        }
        print(f"    ✓ Volcengine 同步完成, task_id={task_id[:8]}..., images={len(image_urls)}")
        return task_id

    def poll_task(self, task_id: str, mode: str) -> Optional[dict]:
        cached = self._result_cache.pop(task_id, None)
        if not cached:
            print(f"    ✗ 找不到 Volcengine 本地任务缓存: {task_id}")
            return None
        return {
            "images": cached.get("images", []),
            "size_meta": cached.get("size_meta"),
        }
