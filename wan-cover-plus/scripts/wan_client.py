from pathlib import Path
import base64
import time
from urllib.parse import urlparse

import yaml
import requests


DEFAULT_SIZE_BY_SCENE = {
    "wechat_cover": "1792x1024",
    "xiaohongshu_cover": "1024x1792",
    "relayout_poster": "1024x1792",
}

VIDEO_SIZE_BY_ASPECT_RATIO = {
    ("720P", "16:9"): "1280*720",
    ("720P", "9:16"): "720*1280",
    ("720P", "1:1"): "960*960",
    ("720P", "4:3"): "1088*832",
    ("720P", "3:4"): "832*1088",
    ("1080P", "16:9"): "1920*1080",
    ("1080P", "9:16"): "1080*1920",
    ("1080P", "1:1"): "1440*1440",
    ("1080P", "4:3"): "1632*1248",
    ("1080P", "3:4"): "1248*1632",
}


def load_config(base_dir: Path):
    path = base_dir / "config.yaml"
    if not path.exists():
        path = base_dir / "config.example.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _download_binary(url: str) -> bytes:
    resp = requests.get(url, timeout=300)
    resp.raise_for_status()
    return resp.content


def _is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _encode_local_file(path: str) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower().lstrip(".") or "octet-stream"
    raw = file_path.read_bytes()
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:application/{suffix};base64,{encoded}"


def _normalize_media_input(value: str) -> str:
    if _is_url(value):
        return value
    return _encode_local_file(value)


def _is_wan27_model(model: str) -> bool:
    """Return True if the model uses the Wan 2.7 media protocol (input.media)."""
    return model.startswith("wan2.7-") and model not in ("wan2.7-image", "wan2.7-t2v")


def _media_item(url_or_path: str, media_type: str = "image") -> dict:
    """Build a single media item for Wan 2.7 input.media array."""
    return {"type": media_type, "url": _normalize_media_input(url_or_path)}


def _media_items_from_paths(paths: list, default_type: str = "image") -> list:
    """Build media items list from a list of file paths or URLs."""
    items = []
    for p in (paths or []):
        suffix = Path(p).suffix.lower() if not _is_url(p) else ""
        if suffix in (".mp4", ".avi", ".mov", ".webm"):
            media_type = "video"
        elif default_type == "video":
            media_type = "video"
        else:
            media_type = "image"
        items.append(_media_item(p, media_type))
    return items


def _prepare_output(output_path: str, prompt: str):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    prompt_file = output.with_suffix(".prompt.txt")
    prompt_file.write_text(prompt, encoding="utf-8")
    return output, prompt_file


def _wan_cfg(config: dict) -> dict:
    wan_cfg = config.get("wan", {})
    if not wan_cfg.get("api_key"):
        raise ValueError("wan.api_key is required in config.yaml")
    return wan_cfg


def _default_model_for_task(task_type: str, wan_cfg: dict) -> str:
    mapping = {
        "image": wan_cfg.get("image_model") or wan_cfg.get("model") or "wan2.7-image",
        "text_to_video": wan_cfg.get("text_to_video_model") or "wan2.7-t2v",
        "image_to_video": wan_cfg.get("image_to_video_model") or "wan2.7-i2v",
        "reference_to_video": wan_cfg.get("reference_to_video_model") or "wan2.7-r2v",
    }
    return mapping[task_type]


def _create_video_task(payload: dict, wan_cfg: dict) -> dict:
    resp = requests.post(
        f"{wan_cfg.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')}/services/aigc/video-generation/video-synthesis",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {wan_cfg['api_key']}",
            "X-DashScope-Async": "enable",
        },
        json=payload,
        timeout=300,
    )
    data = resp.json()
    if resp.status_code != 200:
        raise ValueError(f"Wan video API error ({resp.status_code}): {data.get('message', str(data))}")

    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise ValueError(f"Wan video API did not return task_id: {data}")
    return data


def _poll_video_task(task_id: str, wan_cfg: dict, timeout_seconds: int = 900, interval_seconds: int = 15) -> dict:
    url = f"{wan_cfg.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')}/tasks/{task_id}"
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {wan_cfg['api_key']}"},
            timeout=120,
        )
        data = resp.json()
        if resp.status_code != 200:
            raise ValueError(f"Wan task polling error ({resp.status_code}): {data.get('message', str(data))}")

        output = data.get("output", {})
        status = output.get("task_status")
        if status == "SUCCEEDED":
            return data
        if status == "FAILED":
            raise ValueError(f"Wan video task failed: {output.get('code') or ''} {output.get('message') or data}")
        if status == "UNKNOWN":
            raise ValueError(f"Wan video task expired or became unknown: {task_id}")
        time.sleep(interval_seconds)

    raise TimeoutError(f"Timed out waiting for Wan video task: {task_id}")


def _video_parameters(skill_input, use_reference_size: bool = False) -> dict:
    resolution = skill_input.resolution or "720P"
    duration = skill_input.duration_seconds or 5
    shot_type = skill_input.shot_type or "single"
    audio = True if skill_input.audio is None else bool(skill_input.audio)

    params = {
        "duration": duration,
        "shot_type": shot_type,
        "audio": audio,
        "watermark": False,
    }

    if use_reference_size:
        aspect_ratio = skill_input.aspect_ratio or "16:9"
        params["size"] = VIDEO_SIZE_BY_ASPECT_RATIO[(resolution, aspect_ratio)]
    else:
        params["resolution"] = resolution
        params["prompt_extend"] = True

    return params


def call_wan_image_api(prompt: str, output_path: str, config: dict, scene: str = "wechat_cover", model: str | None = None):
    wan_cfg = _wan_cfg(config)
    model = model or _default_model_for_task("image", wan_cfg)

    size = DEFAULT_SIZE_BY_SCENE.get(scene, "1792x1024").replace("x", "*")
    output, prompt_file = _prepare_output(output_path, prompt)

    resp = requests.post(
        f"{wan_cfg.get('base_url', 'https://dashscope.aliyuncs.com/api/v1')}/services/aigc/multimodal-generation/generation",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {wan_cfg['api_key']}",
        },
        json={
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {
                "prompt_extend": False,
                "size": size,
                "watermark": False,
            },
        },
        timeout=300,
    )

    data = resp.json()
    if resp.status_code != 200:
        raise ValueError(f"Wan API error ({resp.status_code}): {data.get('message', str(data))}")

    out = data.get("output", {})
    image_value = out.get("result_image")
    if not image_value:
        choices = out.get("choices", [])
        if choices:
            for item in choices[0].get("message", {}).get("content", []):
                if "image" in item:
                    image_value = item["image"]
                    break

    if not image_value:
        raise ValueError(f"No image returned: {data}")

    if isinstance(image_value, str) and image_value.startswith("http"):
        image_bytes = _download_binary(image_value)
    else:
        image_bytes = base64.b64decode(image_value)

    output.write_bytes(image_bytes)
    return {
        "output_file": str(output),
        "prompt_file": str(prompt_file),
        "note": "Generated via real Wan2.7-image API",
        "model_used": model,
        "media_type": "image",
    }


def call_wan_text_to_video_api(prompt: str, output_path: str, config: dict, skill_input):
    wan_cfg = _wan_cfg(config)
    model = skill_input.model or _default_model_for_task("text_to_video", wan_cfg)
    output, prompt_file = _prepare_output(output_path, prompt)

    payload = {
        "model": model,
        "input": {
            "prompt": prompt,
            "negative_prompt": skill_input.negative_prompt or "",
        },
        "parameters": _video_parameters(skill_input),
    }

    created = _create_video_task(payload, wan_cfg)
    task_id = created["output"]["task_id"]
    final_data = _poll_video_task(task_id, wan_cfg)
    video_url = final_data.get("output", {}).get("video_url")
    if not video_url:
        raise ValueError(f"Wan text-to-video task returned no video_url: {final_data}")

    output.write_bytes(_download_binary(video_url))
    return {
        "output_file": str(output),
        "prompt_file": str(prompt_file),
        "note": "Generated via Wan text-to-video API",
        "task_id": task_id,
        "video_url": video_url,
        "model_used": model,
        "media_type": "video",
    }


def call_wan_i2v_api(prompt: str, output_path: str, config: dict, skill_input):
    wan_cfg = _wan_cfg(config)
    model = skill_input.model or _default_model_for_task("image_to_video", wan_cfg)
    output, prompt_file = _prepare_output(output_path, prompt)

    normalized_media = _normalize_media_input(skill_input.reference_images[0])

    if _is_wan27_model(model):
        # Wan 2.7 protocol: input.media array with typed items
        input_block = {
            "prompt": prompt,
            "media": [{"type": "first_frame", "url": normalized_media}],
        }
        params = _video_parameters(skill_input)
    else:
        # Wan 2.6 protocol: input.img_url
        input_block = {
            "prompt": prompt,
            "negative_prompt": skill_input.negative_prompt or "",
            "img_url": normalized_media,
        }
        params = _video_parameters(skill_input)

    payload = {
        "model": model,
        "input": input_block,
        "parameters": params,
    }

    created = _create_video_task(payload, wan_cfg)
    task_id = created["output"]["task_id"]
    final_data = _poll_video_task(task_id, wan_cfg)
    video_url = final_data.get("output", {}).get("video_url")
    if not video_url:
        raise ValueError(f"Wan image-to-video task returned no video_url: {final_data}")

    output.write_bytes(_download_binary(video_url))
    return {
        "output_file": str(output),
        "prompt_file": str(prompt_file),
        "note": f"Generated via {model}",
        "task_id": task_id,
        "video_url": video_url,
        "model_used": model,
        "media_type": "video",
    }


def call_wan_r2v_api(prompt: str, output_path: str, config: dict, skill_input):
    wan_cfg = _wan_cfg(config)
    model = skill_input.model or _default_model_for_task("reference_to_video", wan_cfg)
    output, prompt_file = _prepare_output(output_path, prompt)

    if _is_wan27_model(model):
        # Wan 2.7 protocol: input.media array with typed reference items
        media_items = []
        for p in (skill_input.reference_images or []):
            media_items.append({"type": "reference_image", "url": _normalize_media_input(p)})
        for p in (skill_input.reference_videos or []):
            media_items.append({"type": "reference_video", "url": _normalize_media_input(p)})
        input_block = {
            "prompt": prompt,
            "media": media_items,
        }
        params = _video_parameters(skill_input, use_reference_size=True)
    else:
        # Wan 2.6 protocol: input.reference_urls
        reference_urls = [_normalize_media_input(path) for path in (skill_input.reference_images or [])]
        reference_urls.extend(_normalize_media_input(path) for path in (skill_input.reference_videos or []))
        input_block = {
            "prompt": prompt,
            "negative_prompt": skill_input.negative_prompt or "",
            "reference_urls": reference_urls,
        }
        params = _video_parameters(skill_input, use_reference_size=True)

    payload = {
        "model": model,
        "input": input_block,
        "parameters": params,
    }

    created = _create_video_task(payload, wan_cfg)
    task_id = created["output"]["task_id"]
    final_data = _poll_video_task(task_id, wan_cfg)
    video_url = final_data.get("output", {}).get("video_url")
    if not video_url:
        raise ValueError(f"Wan reference-to-video task returned no video_url: {final_data}")

    output.write_bytes(_download_binary(video_url))
    return {
        "output_file": str(output),
        "prompt_file": str(prompt_file),
        "note": f"Generated via {model}",
        "task_id": task_id,
        "video_url": video_url,
        "model_used": model,
        "media_type": "video",
    }
