from typing import Optional

from .base import BaseProvider


SIZE_MAP = {
    "16:9": "2560x1440",
    "9:16": "1440x2560",
    "1:1": "1024x1024",
}


class AtlasCloudProvider(BaseProvider):
    env_var = "ATLASCLOUD_API_KEY"
    create_url = "https://api.atlascloud.ai/api/v1/model/generateImage"
    poll_url = "https://api.atlascloud.ai/api/v1/model/prediction"

    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        size = SIZE_MAP.get(aspect_ratio, "2560x1440")
        model = "openai/gpt-image-2/edit" if mode == "edit" else "openai/gpt-image-2/text-to-image"
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "quality": "high",
        }
        if mode == "edit" and images:
            payload["images"] = images
        return self.create_url, payload

    def parse_task_id(self, resp: dict) -> Optional[str]:
        data = resp["body"].get("data", {})
        return data.get("id")

    def build_poll_url(self, task_id: str, mode: str) -> str:
        return f"{self.poll_url}/{task_id}"

    def parse_poll_status(self, resp: dict) -> tuple[str, dict]:
        data = resp["body"].get("data", {})
        status = data.get("status", "unknown")
        if status in ("completed", "succeeded"):
            return "completed", data
        if status in ("failed", "error"):
            return "failed", data
        return "polling", data

    def extract_images(self, poll_body: dict) -> list[str]:
        outputs = poll_body.get("outputs", [])
        return [u for u in outputs if isinstance(u, str) and u.startswith("http")]
