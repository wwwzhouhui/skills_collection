from __future__ import annotations

import base64
import binascii
import json
import os
import re
import uuid
from pathlib import Path
from typing import Optional

from .base import BaseProvider, http_request


ASPECT_RATIO_TO_SIZE = {
    "1:1": "1024x1024",
    "4:3": "1024x768",
    "3:4": "768x1024",
    "16:9": "1024x576",
    "9:16": "576x1024",
    "3:2": "1024x768",
    "2:3": "768x1024",
}

DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_MODEL = "agnes-image-2.1-flash"
DEFAULT_MAX_REFERENCE_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_LOCAL_SUFFIX = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
ALLOWED_DATA_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}
DATA_URI_RE = re.compile(
    r"^data:(image/(?:png|jpeg|webp|gif));base64,(.+)$",
    re.IGNORECASE | re.DOTALL,
)


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except ValueError as e:
        raise ValueError(f"{name} 必须是整数, 收到 {raw!r}") from e
    if value < minimum:
        qualifier = "非负整数" if minimum == 0 else f"大于等于 {minimum} 的整数"
        raise ValueError(f"{name} 必须是{qualifier}, 收到 {value}")
    return value


def _detect_image_mime(data: bytes) -> Optional[str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


class AgnesProvider(BaseProvider):
    """Agnes Image 2.1 Flash provider.

    Agnes image API is synchronous (POST /v1/images/generations returns the image
    immediately). We still implement the shared create/poll interface so the rest
    of generate.py can stay provider-agnostic.

    HTTP body contract (verified against Agnes-AI-Platform raw httpx client):
    - top-level: model, prompt, size
    - nested extra_body: response_format and optional image/mask
    - response_format at top-level returns 400
    """

    env_var = "AGNES_API_KEY"
    create_url = f"{DEFAULT_BASE_URL}/images/generations"
    poll_url = f"{DEFAULT_BASE_URL}/images/generations"
    POLL_INTERVAL = 0
    POLL_MAX_TIMES = 1
    HTTP_TIMEOUT = 300
    HTTP_RETRIES = 2

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = os.environ.get("AGNES_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.model = os.environ.get("AGNES_IMAGE_MODEL", DEFAULT_MODEL)
        self.http_timeout = _env_int("AGNES_HTTP_TIMEOUT", 300)
        self.http_retries = _env_int("AGNES_HTTP_RETRIES", 2, minimum=0)
        if os.environ.get("AGNES_MAX_REFERENCE_IMAGE_BYTES") is not None:
            self.max_reference_image_bytes = _env_int(
                "AGNES_MAX_REFERENCE_IMAGE_BYTES", DEFAULT_MAX_REFERENCE_IMAGE_BYTES
            )
        else:
            # Keep the earlier name working for existing deployments.
            self.max_reference_image_bytes = _env_int(
                "AGNES_MAX_LOCAL_IMAGE_BYTES", DEFAULT_MAX_REFERENCE_IMAGE_BYTES
            )
        self._result_cache: dict[str, dict] = {}

    def _size_from_aspect_ratio(self, aspect_ratio: str, resolution: str) -> str:
        if aspect_ratio is None:
            key = "1:1"
        elif isinstance(aspect_ratio, str):
            key = aspect_ratio.strip()
        else:
            raise ValueError(f"aspect_ratio 必须是字符串, 收到 {type(aspect_ratio).__name__}")
        if key not in ASPECT_RATIO_TO_SIZE:
            allowed = ", ".join(ASPECT_RATIO_TO_SIZE)
            raise ValueError(f"Agnes 不支持 aspect_ratio={key!r} (允许: {allowed})")
        return ASPECT_RATIO_TO_SIZE[key]

    def describe_output_size(self, aspect_ratio: str, resolution: str) -> dict:
        actual = self._size_from_aspect_ratio(aspect_ratio, resolution)
        return {
            "requested_aspect_ratio": aspect_ratio,
            "requested_resolution": resolution,
            "actual_size": actual,
            "resolution_honored": False,
            "notes": "Agnes Image 2.1 Flash uses fixed size tokens; --resolution is ignored",
        }

    def _normalize_ref_image(self, image: str) -> str:
        if not isinstance(image, str):
            raise ValueError(f"参考图必须是字符串, 收到 {type(image).__name__}")
        raw = image.strip()
        if not raw:
            raise ValueError("参考图为空")

        if raw.lower().startswith(("http://", "https://")):
            return raw

        if raw.lower().startswith("data:"):
            match = DATA_URI_RE.fullmatch(raw)
            if not match:
                raise ValueError("data URI 必须是受支持的 image MIME 且使用 ;base64 编码")
            claimed_mime = match.group(1).lower()
            decoded = self._decode_base64(match.group(2), "data URI")
            return self._encode_validated_image(decoded, claimed_mime)

        try:
            path = Path(raw)
            is_local_file = path.exists() and path.is_file()
        except OSError:
            is_local_file = False
        if is_local_file:
            suffix = path.suffix.lower()
            if suffix not in ALLOWED_LOCAL_SUFFIX:
                raise ValueError(f"不支持的本地图片后缀: {suffix or '(none)'}")
            try:
                if path.stat().st_size > self.max_reference_image_bytes:
                    raise ValueError(
                        f"本地参考图过大, 上限 {self.max_reference_image_bytes} bytes"
                    )
                data = path.read_bytes()
            except ValueError:
                raise
            except OSError as e:
                raise ValueError(f"无法读取本地参考图: {path}") from e
            expected_mime = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".gif": "image/gif",
            }[suffix]
            return self._encode_validated_image(data, expected_mime)

        # pure base64 only if it decodes cleanly and is reasonably long
        try:
            decoded = self._decode_base64(raw, "base64")
            return self._encode_validated_image(decoded)
        except Exception as e:
            raise ValueError(
                f"参考图既不是 URL / data URI / 可读本地文件, 也不是合法 base64: {raw[:80]}"
            ) from e

    def _decode_base64(self, encoded: str, label: str) -> bytes:
        max_encoded_length = ((self.max_reference_image_bytes + 2) // 3) * 4
        if len(encoded) > max_encoded_length:
            raise ValueError(
                f"{label} 参考图编码过大, 解码后上限 {self.max_reference_image_bytes} bytes"
            )
        try:
            return base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as e:
            raise ValueError(f"{label} 包含无效 base64") from e

    def _encode_validated_image(self, data: bytes, claimed_mime: Optional[str] = None) -> str:
        if not data:
            raise ValueError("参考图内容为空")
        if len(data) > self.max_reference_image_bytes:
            raise ValueError(
                f"参考图过大({len(data)} bytes), 上限 {self.max_reference_image_bytes} bytes"
            )
        detected_mime = _detect_image_mime(data)
        if detected_mime not in ALLOWED_DATA_MIME:
            raise ValueError("参考图内容不是受支持的 PNG/JPEG/WebP/GIF")
        if claimed_mime and claimed_mime.lower() != detected_mime:
            raise ValueError(
                f"参考图 MIME 与内容不一致: 声明 {claimed_mime}, 实际 {detected_mime}"
            )
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{detected_mime};base64,{b64}"

    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        mode = (mode or "generation").strip().lower()
        if mode not in ("generation", "edit"):
            raise ValueError(f"Agnes 不支持 mode={mode!r} (仅 generation/edit)")
        size = self._size_from_aspect_ratio(aspect_ratio, resolution)
        body: dict = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
        }

        if mode == "edit":
            if not images:
                raise ValueError("Agnes edit 模式必须提供参考图 images")
            refs: list[str] = []
            for img in images:
                if not isinstance(img, str):
                    raise ValueError(f"参考图必须是字符串, 收到 {type(img).__name__}")
                refs.append(self._normalize_ref_image(img))
            # Nested extra_body is intentional for Agnes raw HTTP (not SDK client expand).
            body["extra_body"] = {
                "image": refs,
                "response_format": "url",
            }
        else:
            body["extra_body"] = {
                "response_format": "url",
            }

        return f"{self.base_url}/images/generations", body

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
            print(f"    ✗ Agnes 参数错误: {e}")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        size_meta = self.describe_output_size(aspect_ratio, resolution)
        print(
            f"    → Agnes 同步生图 model={self.model} size={payload.get('size')} "
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
            print(f"    ✗ Agnes 返回非 JSON 对象: {body}")
            return None

        image_urls = self.extract_images(body)
        if not image_urls:
            print(f"    ✗ Agnes 未返回图片: {json.dumps(body, ensure_ascii=False)[:300]}")
            return None

        task_id = str(uuid.uuid4())
        self._result_cache[task_id] = {
            "images": image_urls,
            "raw": body,
            "size_meta": size_meta,
        }
        print(f"    ✓ Agnes 同步完成, task_id={task_id[:8]}..., images={len(image_urls)}")
        return task_id

    def poll_task(self, task_id: str, mode: str) -> Optional[dict]:
        cached = self._result_cache.pop(task_id, None)
        if not cached:
            print(f"    ✗ 找不到 Agnes 本地任务缓存: {task_id}")
            return None
        return {
            "images": cached.get("images", []),
            "size_meta": cached.get("size_meta"),
        }
