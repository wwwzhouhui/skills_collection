from typing import Optional

from .base import BaseProvider


class MuleRunProvider(BaseProvider):
    env_var = "MULERUN_API_KEY"
    create_url = "https://api.mulerun.com/vendors/google/v1/nano-banana-2"
    poll_url = "https://api.mulerun.com/vendors/google/v1/nano-banana-2"

    def build_create_payload(
        self, prompt: str, mode: str, images: Optional[list[str]],
        aspect_ratio: str, resolution: str,
    ) -> tuple[str, dict]:
        path = "edit" if mode == "edit" else "generation"
        create_url = f"{self.create_url}/{path}"
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
        }
        if mode == "edit" and images:
            payload["images"] = images
        return create_url, payload

    def parse_task_id(self, resp: dict) -> Optional[str]:
        return resp["body"]["task_info"]["id"]

    def build_poll_url(self, task_id: str, mode: str) -> str:
        path = "edit" if mode == "edit" else "generation"
        return f"{self.poll_url}/{path}/{task_id}"

    def parse_poll_status(self, resp: dict) -> tuple[str, dict]:
        task_info = resp["body"].get("task_info", {})
        status = task_info.get("status", "unknown")
        if status in ("completed", "succeeded"):
            return "completed", resp["body"]
        if status in ("failed", "error"):
            return "failed", resp["body"]
        return "polling", resp["body"]

    def extract_images(self, poll_body: dict) -> list[str]:
        return poll_body.get("images", [])
