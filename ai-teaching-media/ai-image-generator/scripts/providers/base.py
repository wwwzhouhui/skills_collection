import json
import os
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

DEFAULT_HTTP_TIMEOUT = int(os.environ.get("IMAGE_HTTP_TIMEOUT", "180"))
DEFAULT_HTTP_RETRIES = int(os.environ.get("IMAGE_HTTP_RETRIES", "2"))


class BaseProvider(ABC):
    env_var: str = ""
    create_url: str = ""
    poll_url: str = ""
    POLL_INTERVAL = 5
    POLL_MAX_TIMES = 36
    # Providers can override for create/poll request timeout seconds
    HTTP_TIMEOUT = DEFAULT_HTTP_TIMEOUT
    HTTP_RETRIES = DEFAULT_HTTP_RETRIES

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        raise NotImplementedError

    @abstractmethod
    def parse_task_id(self, resp: dict) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def build_poll_url(self, task_id: str, mode: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_poll_status(self, resp: dict) -> tuple[str, dict]:
        """Return (status, body).  status is one of completed / polling / failed."""
        raise NotImplementedError

    @abstractmethod
    def extract_images(self, poll_body: dict) -> list[str]:
        raise NotImplementedError

    def describe_output_size(self, aspect_ratio: str, resolution: str) -> dict:
        """Optional provider-specific size metadata."""
        return {
            "requested_aspect_ratio": aspect_ratio,
            "requested_resolution": resolution,
            "actual_size": None,
            "resolution_honored": True,
            "notes": "",
        }

    def create_task(
        self, prompt: str, mode: str,
        images: Optional[list[str]] = None,
        aspect_ratio: str = "16:9", resolution: str = "2K",
    ) -> Optional[str]:
        create_url, payload = self.build_create_payload(prompt, mode, images, aspect_ratio, resolution)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = http_request(
            "POST", create_url, headers, json.dumps(payload).encode("utf-8"),
            timeout=self.HTTP_TIMEOUT, retries=self.HTTP_RETRIES,
        )
        if not (200 <= resp["status"] < 300):
            print(f"    ✗ 创建任务失败,HTTP {resp['status']}")
            print(f"      响应: {resp.get('body')}")
            return None
        return self.parse_task_id(resp)

    def poll_task(self, task_id: str, mode: str) -> Optional[dict]:
        url = self.build_poll_url(task_id, mode)
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for i in range(self.POLL_MAX_TIMES):
            time.sleep(self.POLL_INTERVAL)
            elapsed = (i + 1) * self.POLL_INTERVAL
            resp = http_request("GET", url, headers, timeout=self.HTTP_TIMEOUT, retries=self.HTTP_RETRIES)
            if resp["status"] != 200:
                print(f"    [第 {i+1} 次,已等 {elapsed}s] HTTP {resp['status']},继续等")
                continue

            status, poll_body = self.parse_poll_status(resp)

            if status == "completed":
                print(f"    ✓ 完成,耗时约 {elapsed}s")
                return {"images": self.extract_images(poll_body)}
            elif status == "failed":
                print(f"    ✗ 任务失败: {json.dumps(poll_body, ensure_ascii=False)}")
                return None
            else:
                print(f"    [第 {i+1} 次,已等 {elapsed}s] 状态: {status}")

        print(f"    ✗ 轮询超时({self.POLL_MAX_TIMES * self.POLL_INTERVAL}s)")
        return None


def http_request(
    method: str,
    url: str,
    headers: dict,
    data: Optional[bytes] = None,
    timeout: int = DEFAULT_HTTP_TIMEOUT,
    retries: int = DEFAULT_HTTP_RETRIES,
) -> dict:
    if "User-Agent" not in headers and "user-agent" not in headers:
        headers = {**headers, "User-Agent": DEFAULT_USER_AGENT}

    last_err = None
    attempts = max(1, retries + 1)
    for attempt in range(attempts):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return {"status": resp.status, "body": json.loads(body) if body else {}}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if e.fp else ""
            # retry only on transient gateway errors
            if e.code in (502, 503, 504) and attempt < attempts - 1:
                wait = 2 * (attempt + 1)
                print(f"    ⚠ HTTP {e.code}, {wait}s 后重试 ({attempt + 1}/{attempts})")
                time.sleep(wait)
                last_err = e
                continue
            return {"status": e.code, "body": err_body, "error": str(e)}
        except Exception as e:
            last_err = e
            if attempt < attempts - 1:
                wait = 2 * (attempt + 1)
                print(f"    ⚠ 请求失败 ({e}), {wait}s 后重试 ({attempt + 1}/{attempts})")
                time.sleep(wait)
                continue
            return {"status": 0, "body": "", "error": str(e)}
    return {"status": 0, "body": "", "error": str(last_err) if last_err else "unknown"}


def download_image(url: str, save_path: Path, timeout: int = DEFAULT_HTTP_TIMEOUT) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            save_path.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"    ✗ 下载失败: {e}")
        print(f"      可手动打开: {url}")
        return False
