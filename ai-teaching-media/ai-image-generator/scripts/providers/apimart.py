from typing import Optional

from .base import BaseProvider


class ApimartProvider(BaseProvider):
    env_var = "APIMART_API_KEY"
    create_url = "https://api.apimart.ai/v1/images/generations"
    poll_url = "https://api.apimart.ai/v1/tasks"

    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        payload = {
            "model": "gpt-image-2-official",
            "prompt": prompt,
            "size": aspect_ratio,
            "resolution": resolution.lower(),
            "quality": "high",
            "n": 1,
        }
        if images:
            payload["image_urls"] = images
        return self.create_url, payload

    def parse_task_id(self, resp: dict) -> Optional[str]:
        data = resp["body"].get("data")
        if isinstance(data, list) and data:
            return data[0].get("task_id")
        return None

    def build_poll_url(self, task_id: str, mode: str) -> str:
        return f"{self.poll_url}/{task_id}?language=zh"

    def parse_poll_status(self, resp: dict) -> tuple[str, dict]:
        data = resp["body"].get("data", {})
        status = data.get("status", "unknown")
        if status == "completed":
            return "completed", data
        if status in ("failed", "cancelled"):
            return "failed", data
        return "polling", data

    def extract_images(self, poll_body: dict) -> list[str]:
        result = poll_body.get("result", {})
        image_items = result.get("images", [])
        urls = []
        for item in image_items:
            item_urls = item.get("url", [])
            urls.extend(item_urls)
        return urls
