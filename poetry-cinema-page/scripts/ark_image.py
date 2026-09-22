#!/usr/bin/env python3
"""Volcengine Ark (火山引擎方舟) image generation client for the poetry-cinema-page skill.

Supports text-to-image and image-to-image with doubao-seedream-5.0-pro / doubao-seedream-5.0-lite.

All tunables live in config/ark.config.json (single source of truth).
The API key resolves in this order: ARK_API_KEY env > config/ark.local.json > config api_key.

Examples
--------
    python scripts/ark_image.py probe
    python scripts/ark_image.py t2i --prompt "..." --out public/generated/x/hero.jpg
    python scripts/ark_image.py i2i --prompt "..." --ref hero --out public/generated/x/scene-1.jpg
    python scripts/ark_image.py batch --plan public/generated/x/plan.json

No third-party dependencies: standard library only.
"""

from __future__ import annotations

import argparse
import base64
import html
import http.client
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SKILL_DIR = SCRIPT_PATH.parent.parent
DEFAULT_CONFIG_PATH = SKILL_DIR / "config" / "ark.config.json"

IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".avif")
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
SIZE_RE = re.compile(r"^(\d{2,5})x(\d{2,5})$")


class ArkError(RuntimeError):
    """Any failure the caller can act on."""


# --------------------------------------------------------------------------- output

_JSON_MODE = False  # --json reserves stdout for the JSON stream; progress goes to stderr


def say(message: str = "", *, flush: bool = False) -> None:
    """Print a human-readable progress line, off stdout when --json is in use."""
    print(message, file=sys.stderr if _JSON_MODE else sys.stdout, flush=flush)


def emit_json(records: list[dict] | dict, args) -> None:
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2), flush=True)


# --------------------------------------------------------------------------- config


def load_config(explicit: str | None) -> tuple[dict, Path]:
    candidates: list[Path] = []
    if explicit:
        # An explicit --config must exist; silently falling back to the bundled config
        # would run against different models/endpoints than the caller asked for.
        candidates.append(Path(explicit).expanduser())
        if not candidates[0].is_file():
            raise ArkError(f"config file not found: {candidates[0]}")
    candidates.append(DEFAULT_CONFIG_PATH)
    candidates.append(Path.cwd() / "config" / "ark.config.json")
    candidates.append(Path.cwd() / "ark.config.json")

    for path in candidates:
        if path.is_file():
            try:
                config = json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError as exc:
                raise ArkError(f"config file is not valid JSON: {path} ({exc})") from exc
            if not isinstance(config, dict):
                # Valid JSON, wrong shape: `"models" not in config` would raise TypeError on
                # null / 42 / true and escape main() as a traceback.
                raise ArkError(
                    f"config file must contain a JSON object with 'models' and 'defaults', "
                    f"plus either 'image.providers' or a legacy 'api' block: {path}"
                )
            for section in ("models", "defaults"):
                if section not in config:
                    raise ArkError(f"config file is missing the '{section}' section: {path}")
            config["_image"] = normalize_image_config(config, path)
            return config, path.resolve()

    raise ArkError(
        "no config file found. Looked in: " + ", ".join(str(c) for c in candidates)
    )


def normalize_image_config(config: dict, path: Path | None = None) -> dict:
    """Canonical view of the image settings, whatever shape the config file uses.

    Two shapes are accepted:

    * the provider shape — ``image.providers.<name>`` plus ``image.provider`` as default;
    * the legacy single-provider shape — a top-level ``api`` block, optionally with a
      top-level ``limits`` block, treated as one provider named ``ark`` (or whatever
      ``api.kind`` says).

    Always returns ``{"provider": <default name>, "providers": {name: config}}`` so the
    rest of the program never has to care which shape was on disk.
    """
    where = f" ({path})" if path else ""
    image = config.get("image")
    if isinstance(image, dict) and isinstance(image.get("providers"), dict) and image["providers"]:
        providers = {
            name: dict(cfg)
            for name, cfg in image["providers"].items()
            if isinstance(cfg, dict)
        }
        if not providers:
            raise ArkError(f"'image.providers' contains no usable provider objects{where}")
        default = image.get("provider") or next(iter(providers))
        if default not in providers:
            raise ArkError(
                f"image.provider '{default}' is not one of the configured providers "
                f"({', '.join(sorted(providers))}){where}"
            )
        return {"provider": default, "providers": providers}

    api = config.get("api")
    if isinstance(api, dict) and api:
        provider = dict(api)
        provider.setdefault("kind", "ark")
        provider.setdefault("generations_path", api.get("images_path") or "/images/generations")
        provider.setdefault("reference_transport", "inline")
        if "limits" not in provider and isinstance(config.get("limits"), dict):
            provider["limits"] = config["limits"]
        name = str(provider.get("kind") or "ark")
        return {"provider": name, "providers": {name: provider}}

    raise ArkError(
        f"config file has neither an 'image.providers' block nor a legacy 'api' block{where}"
    )


def provider_config(config: dict, name: str | None) -> tuple[str, dict]:
    """Return (provider_name, provider_settings) for a name, or the configured default."""
    view = config.get("_image") or normalize_image_config(config)
    providers = view["providers"]
    chosen = name or view["provider"]
    if chosen not in providers:
        raise ArkError(
            f"unknown image provider '{chosen}'. Configured providers: "
            f"{', '.join(sorted(providers))}. Set image.provider in the config, or pass "
            f"--provider."
        )
    return chosen, providers[chosen]


def provider_key(config: dict, config_path: Path, provider_name: str, provider: dict) -> tuple[str, str]:
    """Return (key, human readable source) for one provider."""
    api = provider
    env_name = api.get("api_key_env") or "ARK_API_KEY"
    from_env = os.environ.get(env_name, "").strip()
    if from_env:
        return from_env, f"environment variable {env_name}"

    override = api.get("local_override")
    if override:
        for candidate in (
            SKILL_DIR / override,
            config_path.parent.parent / override,
            config_path.parent / Path(override).name,
        ):
            if candidate.is_file():
                try:
                    data = json.loads(candidate.read_text(encoding="utf-8-sig"))
                except json.JSONDecodeError:
                    continue
                value = str(data.get("api_key", "")).strip()
                if value:
                    return value, str(candidate)

    inline = str(api.get("api_key", "")).strip()
    if inline:
        return inline, f"api_key in {config_path.name}"

    hint = api.get("local_override") or f"config/{provider_name}.local.json"
    raise ArkError(
        f"no API key for provider '{provider_name}'. Set the {env_name} environment "
        f"variable, or put \"api_key\" into {SKILL_DIR / hint} (or next to the config file)."
    )



def resolve_api_key(config: dict, config_path: Path) -> tuple[str, str]:
    """Key for the DEFAULT image provider.

    Kept because narration.py imports it; new image code should call provider_key().
    """
    name, provider = provider_config(config, None)
    return provider_key(config, config_path, name, provider)


def mask(key: str) -> str:
    if len(key) <= 12:
        return "*" * len(key)
    return f"{key[:8]}...{key[-4:]}"


# --------------------------------------------------------------------------- parameters


def resolve_size(value: str | None, config: dict, limits: dict | None = None) -> str:
    """Validate a size against one provider's limits.

    Ark enforces an area band (lite refuses anything under 3,686,400 px), while the
    OpenAI-compatible gateway takes arbitrary sizes and also the literal "auto".
    """
    presets = config.get("size_presets", {})
    raw = value or config["defaults"]["size"]

    if raw in presets:
        raw = presets[raw]

    if raw == "auto":
        if limits is not None and not limits.get("allow_auto"):
            raise ArkError(
                "size 'auto' is only supported by the OpenAI-compatible provider; "
                "pass an explicit WIDTHxHEIGHT for this one."
            )
        return raw

    if not SIZE_RE.match(raw):
        raise ArkError(
            f"size '{raw}' is not valid. Use an explicit WIDTHxHEIGHT such as 2560x1440, "
            f"or one of the presets: {', '.join(sorted(presets)) or '(none)'}. "
            "Do not use shorthand like '2K' — it does not guarantee a 16:9 frame."
        )

    limits = limits or {}
    width, height = (int(part) for part in raw.split("x"))
    area = width * height
    shortest = min(width, height)
    longest = max(width, height)

    # Area band: Ark's rule.
    minimum = int(limits.get("min_area_px", 0))
    maximum = int(limits.get("max_area_px", 0))
    if minimum and area < minimum:
        raise ArkError(
            f"size {raw} is {area} px; this provider requires at least {minimum} px "
            f"(doubao-seedream-5.0-lite enforces this). Use 2560x1440 for 16:9 pages."
        )
    if maximum and area > maximum:
        raise ArkError(f"size {raw} is {area} px; this provider allows at most {maximum} px.")

    # Edge band: the gateway's rule, and a guard against nonsense sizes anywhere.
    min_edge = int(limits.get("min_edge_px", 0))
    max_edge = int(limits.get("max_edge_px", 0))
    if min_edge and shortest < min_edge:
        raise ArkError(
            f"size {raw} has a {shortest} px edge; this provider requires at least "
            f"{min_edge} px on the short edge."
        )
    if max_edge and longest > max_edge:
        raise ArkError(
            f"size {raw} has a {longest} px edge; this provider allows at most "
            f"{max_edge} px on the long edge."
        )

    return raw


def resolve_model_entry(config: dict, tier: str) -> tuple[str, str]:
    """Return (model_id, provider_name) for a tier name in config['models'].

    A tier may be written either as an object {"provider": ..., "id": ...} or, for
    backward compatibility, as a bare model id string (which uses the default provider).
    """
    models = config["models"]
    entry = models[tier]
    default_provider = (config.get("_image") or normalize_image_config(config))["provider"]
    if isinstance(entry, dict):
        model_id = str(entry.get("id") or "").strip()
        if not model_id:
            raise ArkError(f"model tier '{tier}' has no 'id'.")
        return model_id, str(entry.get("provider") or default_provider)
    if isinstance(entry, str):
        return entry, default_provider
    raise ArkError(
        f"model tier '{tier}' must be a model id string or an object with 'id' and "
        f"optional 'provider'."
    )


def pick_model(config: dict, role: str, tier: str | None, model: str | None,
               provider: str | None = None) -> tuple[str, str, str]:
    """Return (model_id, tier_label, provider_name)."""
    if model:
        # An explicit model id may be a configured tier name; otherwise the caller's
        # --provider (or the default) decides which endpoint to talk to.
        if model in config.get("models", {}):
            model_id, provider_name = resolve_model_entry(config, model)
            return model_id, model, provider_name
        fallback = provider or (config.get("_image") or normalize_image_config(config))["provider"]
        return model, "explicit", fallback
    chosen = tier or config.get("routing", {}).get(role) or config["defaults"]["tier"]
    models = config["models"]
    if chosen not in models:
        raise ArkError(f"unknown tier '{chosen}'. Configured tiers: {', '.join(sorted(models))}")
    model_id, provider_name = resolve_model_entry(config, chosen)
    if provider:
        provider_name = provider
    return model_id, chosen, provider_name


def file_to_data_uri(path: Path) -> str:
    suffix = path.suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".avif": "image/avif",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def resolve_reference(
    ref: str, out_dir: Path | None, allow_missing: bool = False
) -> tuple[str, str]:
    """Return (payload_value, description). Accepts URL, data URI, path, or sibling name."""
    lowered = ref.lower()
    if lowered.startswith(("http://", "https://")):
        return ref, f"url:{ref}"
    if lowered.startswith("data:"):
        return ref, "data-uri:inline"

    candidate = Path(ref).expanduser()
    if candidate.is_file():
        return file_to_data_uri(candidate), f"file:{candidate}"
    if candidate.suffix and out_dir and (out_dir / candidate.name).is_file():
        full = out_dir / candidate.name
        return file_to_data_uri(full), f"file:{full}"

    if out_dir:
        for suffix in IMAGE_SUFFIXES:
            full = out_dir / f"{ref}{suffix}"
            if full.is_file():
                return file_to_data_uri(full), f"file:{full}"

    if allow_missing:
        # A dry run previews the whole plan, so a reference to a sibling that this same
        # run will create is expected to be missing.
        return f"<pending:{ref}>", f"pending:{ref}"
    raise ArkError(
        f"reference image '{ref}' not found. Pass a file path, a public URL, or the "
        f"name of an image already generated in {out_dir}."
    )


def normalize_out_path(path: Path, image_format: str) -> tuple[Path, str | None]:
    """Make the written extension match the format the API actually returned."""
    image_format = (image_format or "jpeg").lower().lstrip(".")
    if image_format in {"jpeg", "jpg"}:
        accepted, preferred = {".jpg", ".jpeg"}, ".jpg"
    else:
        accepted, preferred = {f".{image_format}"}, f".{image_format}"

    suffix = path.suffix.lower()
    if suffix in accepted:
        return path, None
    fixed = path.with_suffix(preferred)
    if suffix == "":
        return fixed, None
    return fixed, (
        f"the API returns {image_format}, so '{path.name}' was written as "
        f"'{fixed.name}' to avoid a mislabelled file"
    )


def normalize_references(entry: dict, label: str) -> list[str]:
    """A plan 'ref' may be one string; expand it so it is not iterated per character."""
    value = entry.get("ref", entry.get("references", []))
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        for position, item in enumerate(value):
            if not isinstance(item, str):
                # str(item) would turn [null] into a search for a file named "None".
                kind = "null" if item is None else type(item).__name__
                raise ArkError(
                    f"[{label}] 'ref[{position}]' must be a string, got {kind}. "
                    "Omit a missing reference instead of passing null."
                )
        return list(value)
    raise ArkError(
        f"[{label}] 'ref' must be a string or a list of strings, not {type(value).__name__}"
    )


def resolve_local_file(ref: str, out_dir: Path | None) -> tuple[Path | None, str]:
    """Return the on-disk file a reference names, or (None, description) for remote ones.

    The multipart upload path needs real bytes, so a reference that is a URL has to be
    fetched first; a reference that is already local is used as-is.
    """
    lowered = ref.lower()
    if lowered.startswith(("http://", "https://")):
        return None, f"url:{ref}"
    if lowered.startswith("data:"):
        return None, "data-uri:inline"

    candidate = Path(ref).expanduser()
    if candidate.is_file():
        return candidate, f"file:{candidate}"
    if candidate.suffix and out_dir and (out_dir / candidate.name).is_file():
        full = out_dir / candidate.name
        return full, f"file:{full}"
    if out_dir:
        for suffix in IMAGE_SUFFIXES:
            full = out_dir / f"{ref}{suffix}"
            if full.is_file():
                return full, f"file:{full}"
    return None, f"missing:{ref}"


def fetch_to_temp(url: str, workdir: Path, position: int) -> tuple[Path, str]:
    """Download a remote reference so it can be uploaded as a file."""
    suffix = Path(urllib.parse.urlsplit(url).path).suffix.lower()
    if suffix not in IMAGE_SUFFIXES:
        suffix = ".jpg"
    target = workdir / f"ref-fetched-{position + 1}{suffix}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT},
                                         method="GET")
        with urllib.request.urlopen(request, timeout=180) as response:
            blob = response.read()
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
        raise ArkError(f"could not fetch the reference image {url}: {exc}") from exc
    if not blob:
        raise ArkError(f"the reference image {url} returned an empty body")
    target.write_bytes(blob)
    return target, f"file:{target}"


def format_from_url(url: str) -> str:
    """Image format implied by a result URL, so extensions never mislabel the bytes."""
    path = urllib.parse.urlsplit(url).path
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix in {"jpg", "jpeg", "png", "webp", "avif", "bmp"}:
        return "jpeg" if suffix == "jpg" else suffix
    return ""


# --------------------------------------------------------------------------- transport


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def provider_kind(provider: dict) -> str:
    return str(provider.get("kind") or "ark")


def provider_headers(provider: dict, key: str, content_type: str | None = "application/json") -> dict:
    """Request headers for one provider.

    The OpenAI-compatible gateway sits behind Cloudflare, which answers the default
    urllib User-Agent with ``error code: 1010`` before the request ever reaches the API,
    so a browser-like UA is not optional there.
    """
    headers: dict[str, str] = {}
    if content_type:
        headers["Content-Type"] = content_type
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if provider_kind(provider) == "openai-images":
        headers["User-Agent"] = provider.get("user_agent") or DEFAULT_USER_AGENT
        headers["Accept"] = "application/json, text/plain, */*"
        headers["Accept-Language"] = "zh-CN,zh;q=0.9,en;q=0.8"
        base = str(provider.get("base_url") or "").strip()
        if base:
            parts = urllib.parse.urlsplit(base)
            if parts.scheme and parts.netloc:
                origin = f"{parts.scheme}://{parts.netloc}"
                headers["Origin"] = origin
                headers["Referer"] = origin + "/"
    return headers


def _retry_settings(provider: dict, config: dict) -> tuple[float, int, float]:
    legacy = config.get("api") if isinstance(config.get("api"), dict) else {}
    timeout = float(provider.get("timeout_seconds") or legacy.get("timeout_seconds") or 300)
    retries = int(provider.get("max_retries", legacy.get("max_retries", 2)))
    backoff = float(provider.get("retry_backoff_seconds",
                                 legacy.get("retry_backoff_seconds", 6)))
    return timeout, retries, backoff


def _perform(url: str, data: bytes, provider: dict, key: str, config: dict, label: str,
             content_type: str | None) -> dict:
    """POST raw bytes and return the parsed JSON response, retrying transient faults."""
    timeout, retries, backoff = _retry_settings(provider, config)
    last_error = ""
    for attempt in range(retries + 1):
        response_body = b""
        try:
            # The Request constructor parses the URL and raises ValueError for a
            # scheme-less base_url, so it belongs inside this try as well.
            request = urllib.request.Request(
                url,
                data=data,
                headers=provider_headers(provider, key, content_type),
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_body = response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")
            except (http.client.HTTPException, OSError) as exc2:
                # A truncated error body is an HTTPException too: it must not escape
                # as a traceback either.
                detail = f"<unreadable error body: {type(exc2).__name__}: {exc2}>"
            last_error = f"HTTP {exc.code} — {detail}"
            if exc.code in RETRYABLE_STATUS and attempt < retries:
                wait = backoff * (attempt + 1)
                say(f"  {label}: HTTP {exc.code}, retrying in {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            raise ArkError(describe_http_error(exc.code, detail, provider)) from exc
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            # IncompleteRead / BadStatusLine are HTTPExceptions, not OSErrors: without
            # this clause a truncated response escapes as a traceback.
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                wait = backoff * (attempt + 1)
                say(f"  {label}: {last_error}, retrying in {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            raise ArkError(
                f"network failure calling {url}: {last_error}. Transient TLS/connection "
                f"drops are common on this route; raise max_retries for the provider if "
                f"it keeps happening."
            ) from exc
        except ValueError as exc:
            # urlopen raises ValueError ("unknown url type") for a URL it cannot parse,
            # e.g. a scheme-less base_url — that is a config error, not a bad body.
            raise ArkError(
                f"cannot call {url}: {exc} — check 'base_url' and 'generations_path' for "
                f"this provider; base_url must be absolute, for example "
                f"'https://ark.cn-beijing.volces.com/api/plan/v3'"
            ) from exc

        try:
            return json.loads(response_body.decode("utf-8"))
        except ValueError as exc:
            # A 200 whose body is not UTF-8 JSON: decode and parse errors are ValueErrors.
            snippet = response_body[:200].decode("utf-8", "replace")
            raise ArkError(
                f"the API returned a non-JSON response body: {exc}. "
                f"First 200 bytes: {snippet!r}"
            ) from exc

    raise ArkError(f"request failed after {retries + 1} attempts: {last_error}")


def post_json(url: str, key: str, payload: dict, config: dict, label: str,
              provider: dict | None = None) -> dict:
    if provider is None:
        provider = provider_config(config, None)[1]
    return _perform(url, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    provider, key, config, label, "application/json")


def post_multipart(url: str, key: str, fields: list[tuple[str, str]],
                   files: list[tuple[str, str, str, bytes]], config: dict, label: str,
                   provider: dict | None = None) -> dict:
    """POST a multipart/form-data body.

    This is the only transport the OpenAI-compatible gateway accepts for reference
    images: ``/v1/images/edits`` takes the picture as an uploaded file. Passing an
    ``image`` field to ``/v1/images/generations`` instead is silently ignored, which
    would quietly turn an image-to-image request into a fresh text-to-image one.
    """
    if provider is None:
        provider = provider_config(config, None)[1]
    boundary = "----poetrypage" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for name, value in fields:
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n"
            f"{value}\r\n".encode("utf-8")
        )
    for field, filename, mime, blob in files:
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
            f"filename=\"{filename}\"\r\nContent-Type: {mime}\r\n\r\n".encode("utf-8")
        )
        chunks.append(blob)
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return _perform(url, b"".join(chunks), provider, key, config, label,
                    f"multipart/form-data; boundary={boundary}")


def describe_http_error(status: int, detail: str, provider: dict | None = None) -> str:
    provider = provider or {}
    label = str(provider.get("label") or provider.get("kind") or "image")
    env_name = str(provider.get("api_key_env") or "API key")

    code = ""
    message = detail
    try:
        parsed = json.loads(detail)
        error = parsed.get("error", parsed)
        code = str(error.get("code", ""))
        message = str(error.get("message", detail))
    except json.JSONDecodeError:
        pass

    hint = ""
    if status in (401, 403) or code in {"AuthenticationError", "Unauthorized", "invalid_api_key"}:
        hint = f" — the API key was rejected; check {env_name} or the provider's local key file"
    elif code == "UnsupportedModel":
        hint = (
            " — this model is not enabled for the endpoint in use; check the models "
            "section of config/ark.config.json"
        )
    elif code == "InvalidParameter" and "size" in message.lower():
        hint = (
            " — fix the size: for Ark it must be an explicit WIDTHxHEIGHT inside the "
            "configured area band (2560x1440 works for both seedream 5.0 models); the "
            "OpenAI-compatible gateway also accepts 'auto'"
        )
    elif status == 429 or code == "RateLimitExceeded":
        hint = " — rate limited; wait and retry, or lower the request rate"
    elif status in (502, 503, 504, 520, 522, 524):
        hint = (
            " — the gateway or its upstream was overloaded. This route drops connections "
            "under load; raise the provider's max_retries / retry_backoff_seconds and retry"
        )

    return f"{label} error HTTP {status} [{code or 'unknown'}]: {message}{hint}"


def download(url: str, destination: Path, config: dict, provider: dict | None = None) -> int:
    provider = provider or provider_config(config, None)[1]
    timeout, retries, backoff = _retry_settings(provider, config)
    blob = b""
    for attempt in range(retries + 1):
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(
                url, headers=provider_headers(provider, "", content_type=None), method="GET")
            with urllib.request.urlopen(request, timeout=timeout) as response:
                blob = response.read()
            break
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            # IncompleteRead (a truncated download) is an HTTPException, not an OSError.
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
                continue
            raise ArkError(
                f"failed to download the generated image to {destination}: "
                f"{type(exc).__name__}: {exc} (the image URL may have expired, or the "
                f"connection dropped)"
            ) from exc

    if not blob:
        # A 200 with an empty body is not an image; writing it would record a
        # 0-byte file as a success.
        raise ArkError(
            f"the image download for {destination} returned an empty body; nothing was "
            f"written (the image URL may have expired)"
        )
    destination.write_bytes(blob)
    return len(blob)


def build_payload(config: dict, provider: dict, model: str, prompt: str, size: str,
                  refs: list[str]) -> dict:
    """Request body for a text-to-image call, shaped for the provider's API."""
    defaults = config["defaults"]
    limits = provider.get("limits") or {}
    kind = provider_kind(provider)

    if kind == "openai-images":
        # response_format=b64_json is refused by this gateway; url is the only mode.
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": provider.get("response_format") or "url",
        }
        if provider.get("quality"):
            payload["quality"] = provider["quality"]
    else:
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "response_format": defaults.get("response_format", "url"),
            "watermark": bool(defaults.get("watermark", False)),
        }

    limit = int(limits.get("max_reference_images", 10))
    if refs:
        if len(refs) > limit:
            raise ArkError(
                f"{len(refs)} reference images given; this provider allows at most {limit}."
            )
        if kind != "openai-images":
            # Ark takes inline references (URLs or data URIs) in the same JSON body.
            payload["image"] = refs
    return payload


def prepare_reference(path: Path, provider: dict, workdir: Path) -> tuple[Path, str | None]:
    """Shrink a reference image before an upload.

    The gateway closed the connection on a 366 KB upload but accepted the same picture
    at 22 KB, so references are resized down to ``reference_max_edge`` first.
    """
    max_edge = int(provider.get("reference_max_edge") or 0)
    if max_edge <= 0:
        return path, None
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError:
        return path, None
    try:
        with Image.open(path) as image:
            width, height = image.size
            longest = max(width, height)
            if longest <= max_edge:
                return path, None
            scale = max_edge / float(longest)
            resized = image.convert("RGB").resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.LANCZOS,
            )
            target = workdir / (path.stem + f"-ref{max_edge}.jpg")
            resized.save(target, "JPEG", quality=88, optimize=True)
        return target, (
            f"reference resized from {width}x{height} to fit {max_edge}px "
            f"({path.stat().st_size // 1024} KB -> {target.stat().st_size // 1024} KB)"
        )
    except Exception:  # noqa: BLE001 - a resize failure must not block generation
        return path, None


def mime_for(path: Path) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".bmp": "image/bmp", ".avif": "image/avif",
    }.get(path.suffix.lower(), "application/octet-stream")


# --------------------------------------------------------------------------- generation


def generate_one(
    config: dict,
    config_path: Path,
    key: str | None = None,
    *,
    prompt: str,
    out_path: Path,
    role: str,
    tier: str | None,
    model: str | None,
    size: str | None,
    references: list[str],
    out_dir: Path | None,
    label: str,
    dry_run: bool,
    provider: str | None = None,
) -> dict:
    model_id, tier_label, provider_name = pick_model(config, role, tier, model, provider)
    _, provider_cfg = provider_config(config, provider_name)
    resolved_size = resolve_size(size, config, provider_cfg.get("limits") or {})
    if not dry_run and not key:
        # Resolve the key for THIS provider: two providers in one run must not have to
        # share one credential, and a missing key must surface before any upload work.
        key = provider_key(config, config_path, provider_name, provider_cfg)[0]
    kind = provider_kind(provider_cfg)
    base = str(provider_cfg.get("base_url") or "").rstrip("/")
    generations_url = base + str(provider_cfg.get("generations_path") or "/images/generations")
    edits_url = base + str(provider_cfg.get("edits_path") or "/images/edits")

    ref_payloads: list[str] = []
    ref_labels: list[str] = []
    for ref in references:
        payload_value, description = resolve_reference(ref, out_dir, allow_missing=dry_run)
        ref_payloads.append(payload_value)
        ref_labels.append(description)

    use_edits = bool(ref_payloads) and kind == "openai-images"
    url = edits_url if use_edits else generations_url
    mode = "image-to-image" if ref_payloads else "text-to-image"
    if ref_payloads and kind == "openai-images":
        mode = "image-to-image (multipart upload)"

    payload = build_payload(config, provider_cfg, model_id, prompt, resolved_size, ref_payloads)

    record: dict = {
        "name": label,
        "role": role,
        "tier": tier_label,
        "provider": provider_name,
        "model": model_id,
        "mode": mode,
        "size": resolved_size,
        "prompt": prompt,
        "references": ref_labels,
        "requested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    if dry_run:
        preview = dict(payload)
        if use_edits:
            preview = {"model": model_id, "prompt": prompt, "size": resolved_size,
                       "n": 1, "response_format": "url"}
            preview["_multipart_file"] = list(ref_labels)
        elif "image" in preview:
            preview["image"] = list(ref_labels)
        record["dry_run"] = True
        record["payload"] = preview
        record["endpoint"] = url
        say(f"[dry-run] {label}: {mode} via {provider_name}/{model_id} at {resolved_size}")
        say(json.dumps(preview, ensure_ascii=False, indent=2))
        return record

    say(f"[{label}] {mode} · {provider_name}/{model_id} · {resolved_size}", flush=True)
    started = time.monotonic()

    if use_edits:
        fields = [("model", model_id), ("prompt", prompt), ("n", "1"),
                  ("size", resolved_size),
                  ("response_format", str(provider_cfg.get("response_format") or "url"))]
        # Stage the uploads in a temp dir: the resized reference and any fetched remote
        # reference are working files, and the delivery folder must hold only the
        # generated images plus the manifest and contact sheet.
        with tempfile.TemporaryDirectory(prefix="poetry-refs-") as staging:
            workdir = Path(staging)
            files: list[tuple[str, str, str, bytes]] = []
            for position, ref in enumerate(references):
                source, _ = resolve_reference(ref, out_dir)
                local, _description = resolve_local_file(ref, out_dir)
                if local is None:
                    # Remote references cannot be uploaded as-is; fetch them once.
                    local, _description = fetch_to_temp(source, workdir, position)
                prepared, notice = prepare_reference(local, provider_cfg, workdir)
                if notice:
                    say(f"  note: {notice}")
                files.append(("image", prepared.name, mime_for(prepared),
                              prepared.read_bytes()))
            response = post_multipart(edits_url, key, fields, files, config, label,
                                      provider_cfg)
    else:
        response = post_json(url, key or "", payload, config, label, provider_cfg)

    elapsed = round(time.monotonic() - started, 1)

    items = response.get("data") or []
    if not items or not items[0].get("url"):
        raise ArkError(f"[{label}] the API returned no image: {json.dumps(response)[:400]}")

    item = items[0]
    image_format = str(
        item.get("output_format")
        or format_from_url(str(item.get("url") or ""))
        or config["defaults"].get("image_format", "jpeg")
    )
    final_path, notice = normalize_out_path(out_path, image_format)
    if notice:
        say(f"  note: {notice}")
    bytes_written = download(item["url"], final_path, config, provider_cfg)

    record.update(
        {
            "output": str(final_path),
            "bytes": bytes_written,
            "api_size": item.get("size"),
            "elapsed_seconds": elapsed,
            "usage": response.get("usage", {}),
        }
    )
    if item.get("revised_prompt"):
        record["revised_prompt"] = item["revised_prompt"]
    if config.get("output", {}).get("keep_api_urls", True):
        record["api_url"] = item["url"]

    say(f"  saved {final_path} ({bytes_written / 1024:.0f} KB in {elapsed}s)", flush=True)
    return record


# --------------------------------------------------------------------------- manifest


def manifest_path(out_dir: Path, config: dict) -> Path:
    name = config.get("output", {}).get("manifest_name", "prompts.json")
    return out_dir / name


def load_manifest_records(out_dir: Path, config: dict) -> list[dict]:
    """Entries already recorded in the manifest; [] when it is missing or malformed."""
    path = manifest_path(out_dir, config)
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        # UnicodeDecodeError is a ValueError, not an OSError: a manifest hand-edited in a
        # legacy codepage (GBK on Chinese Windows) must degrade to [] like any other
        # malformed manifest, not abort the run after the images were paid for.
        return []
    if not isinstance(data, dict):  # valid JSON but not an object: never crash the merge
        return []
    images = data.get("images")
    if not isinstance(images, list):
        return []
    # write_contact_sheet indexes record["name"] / record["output"] and html-escapes them,
    # so an entry missing either one is unusable and must never reach the sheet writer.
    return [
        entry
        for entry in images
        if isinstance(entry, dict)
        and isinstance(entry.get("name"), str)
        and entry["name"]
        and isinstance(entry.get("output"), str)
        and entry["output"]
    ]


def resolve_recorded_path(recorded: str, out_dir: Path) -> Path:
    """Resolve a manifest-recorded output path against out_dir, then against the CWD.

    Run 1 may have recorded a relative path (public/generated/poem/hero.png) from a
    different working directory; testing it against the CWD alone finds nothing and
    re-generates an image that already exists — a second billed call.
    """
    path = Path(recorded)
    if not path.is_absolute():
        candidate = out_dir / path
        if candidate.is_file():
            return candidate
    return path


def skipped_record(
    entry: dict,
    name: str,
    output: Path,
    config: dict,
    *,
    role: str | None = None,
    tier: str | None = None,
    model: str | None = None,
    previous: dict | None = None,
) -> dict:
    """A record for an image this run reused instead of regenerating.

    Without one an all-skip run leaves `records` empty and writes neither the manifest
    nor the contact sheet. Nothing here is requested, downloaded or billed.
    """
    previous = previous or {}
    role = role or previous.get("role") or config["defaults"].get("role", "beat")
    tier = (
        tier
        or previous.get("tier")
        or config.get("routing", {}).get(role)
        or config["defaults"].get("tier", "")
    )
    model = model or previous.get("model") or config.get("models", {}).get(tier, "")
    refs = entry.get("ref", entry.get("references"))
    has_refs = bool(refs) if isinstance(refs, (str, list)) else False

    return {
        "name": name,
        "role": role,
        "tier": tier,
        "model": str(model),
        "mode": previous.get("mode") or ("image-to-image" if has_refs else "text-to-image"),
        "size": str(entry.get("size") or previous.get("size") or config["defaults"]["size"]),
        "prompt": str(entry.get("prompt", "")),
        "output": str(output),
        "skipped": True,
        "skipped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def write_manifest(out_dir: Path, config: dict, records: list[dict]) -> Path:
    path = manifest_path(out_dir, config)

    merged = {
        entry.get("name"): entry
        for entry in load_manifest_records(out_dir, config)
        if entry.get("name")
    }
    for record in records:
        if record.get("dry_run"):
            continue
        existing = merged.get(record["name"])
        if record.get("skipped") and existing:
            # A skip reuses the image the manifest already describes: keep the richer
            # record (bytes, api_size, usage) rather than replacing it with the stub.
            continue
        merged[record["name"]] = record

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": str(config.get("_config_path", "")),
        "models": config.get("models", {}),
        "images": list(merged.values()),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_contact_sheet(out_dir: Path, config: dict, records: list[dict]) -> Path | None:
    name = config.get("output", {}).get("contact_sheet_name", "contact-sheet.html")
    columns = int(config.get("output", {}).get("contact_sheet_columns", 3))
    path = out_dir / name

    entries = [r for r in records if r.get("output")]
    if not entries and path.is_file():
        return path
    if not entries:
        return None

    cards = []
    for record in entries:
        image = Path(record["output"])
        try:
            relative = image.relative_to(out_dir).as_posix()
        except ValueError:
            relative = os.path.relpath(image, out_dir).replace("\\", "/")
        cards.append(
            f"""    <figure>
      <img src="{html.escape(relative)}" alt="{html.escape(record['name'])}" loading="lazy" />
      <figcaption>
        <strong>{html.escape(record['name'])}</strong>
        <span>{html.escape(record.get('mode', ''))} · {html.escape(record.get('model', ''))} · {html.escape(str(record.get('size', '')))}</span>
        <em>{html.escape(record.get('prompt', ''))}</em>
      </figcaption>
    </figure>"""
        )

    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>联系表 · contact sheet</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; padding: 32px; background: #101416; color: #f2eadf;
         font-family: "Noto Serif SC", "Songti SC", serif; }}
  h1 {{ font-size: 22px; font-weight: 500; margin: 0 0 6px; }}
  p.meta {{ color: rgba(242,234,223,.6); margin: 0 0 28px; font-size: 13px; }}
  .grid {{ display: grid; gap: 20px; grid-template-columns: repeat({columns}, minmax(0, 1fr)); }}
  figure {{ margin: 0; border: 1px solid rgba(255,255,255,.14); background: rgba(10,15,18,.7); }}
  img {{ display: block; width: 100%; height: auto; }}
  figcaption {{ padding: 10px 12px 14px; font-size: 12px; line-height: 1.6; }}
  figcaption strong {{ display: block; font-size: 14px; color: #d5b98d; }}
  figcaption span {{ display: block; color: rgba(242,234,223,.55); }}
  figcaption em {{ display: block; margin-top: 6px; color: rgba(242,234,223,.75); font-style: normal; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  @media (max-width: 560px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>联系表 · contact sheet</h1>
<p class="meta">{len(entries)} 张图 · 生成于 {html.escape(datetime.now(timezone.utc).isoformat(timespec='seconds'))} · 逐张检查人物一致性、时代错误、意外文字与风格漂移</p>
<div class="grid">
{chr(10).join(cards)}
</div>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- commands


def command_probe(args, config: dict, config_path: Path) -> int:
    view = config.get("_image") or normalize_image_config(config)
    providers = view["providers"]

    # --json reserves stdout for exactly one report object, so every human-readable line
    # below goes through say() (which prints to stderr in JSON mode).
    report: dict = {
        "command": "probe",
        "config": str(config_path),
        "default_provider": view["provider"],
        "providers": {},
        "models": config["models"],
        "routing": config.get("routing", {}),
        "default_size": config["defaults"]["size"],
        "size_presets": config.get("size_presets", {}),
        "dry_run": bool(args.dry_run),
        "live": bool(args.live),
        "probed_models": [],
    }

    def done(code: int) -> int:
        """Emit the single JSON report object, then return the exit code."""
        report["ok"] = code == 0
        emit_json(report, args)
        return code

    def target_tiers() -> list[str]:
        if args.tier:
            return [args.tier]
        return sorted(config["models"])

    tiers = target_tiers()
    for tier in tiers:
        if tier not in config["models"]:
            say(f"unknown tier '{tier}'; configured tiers: {', '.join(sorted(config['models']))}")
            return done(1)

    # Resolve each provider's key once, and only when it is actually needed.
    keys: dict[str, str] = {}
    sources: dict[str, str] = {}
    for tier in tiers:
        _, provider_name = resolve_model_entry(config, tier)
        if provider_name in keys:
            continue
        provider = providers.get(provider_name)
        if provider is None:
            report["providers"][provider_name] = {"ok": False, "error": "not configured"}
            continue
        base = str(provider.get("base_url") or "").rstrip("/")
        entry = {
            "label": provider.get("label"),
            "kind": provider_kind(provider),
            "endpoint": base + str(provider.get("generations_path") or "/images/generations"),
            "limits": provider.get("limits") or {},
        }
        if args.dry_run:
            entry.update({"api_key": None, "api_key_source": None, "ok": True,
                          "api_key_note": "dry run — not resolved"})
        else:
            try:
                key, source = provider_key(config, config_path, provider_name, provider)
                keys[provider_name] = key
                sources[provider_name] = source
                entry.update({"api_key": mask(key), "api_key_source": source, "ok": True})
            except ArkError as exc:
                entry.update({"api_key": None, "api_key_source": None, "ok": False,
                              "error": str(exc)})
        report["providers"][provider_name] = entry

    say(f"config        : {config_path}")
    say(f"default prov. : {view['provider']}")
    for name, entry in report["providers"].items():
        say(f"  provider {name:12s} [{entry.get('kind')}] {entry.get('endpoint')}")
        if entry.get("api_key"):
            say(f"      key       : {entry['api_key']}  (from {entry.get('api_key_source')})")
        elif entry.get("ok"):
            say("      key       : (dry run — not resolved)")
        else:
            say(f"      key       : MISSING — {entry.get('error')}")
    say("models        : " + json.dumps(config["models"], ensure_ascii=False))
    say(f"routing       : {json.dumps(config.get('routing', {}), ensure_ascii=False)}")
    say(f"default size  : {config['defaults']['size']}")
    visible_presets = {k: v for k, v in (config.get("size_presets") or {}).items()
                       if not k.startswith("_")}
    say(f"size presets  : {json.dumps(visible_presets, ensure_ascii=False)}")

    if args.live:
        if args.dry_run:
            return done(0)
        probe_dir = Path(args.out_dir or ".") / "_probe"
        for tier in tiers:
            model_id, provider_name = resolve_model_entry(config, tier)
            key = keys.get(provider_name)
            if not key:
                report["probed_models"].append(
                    {"tier": tier, "provider": provider_name, "model": model_id, "ok": False,
                     "error": "no API key for this provider"})
                continue
            try:
                record = generate_one(
                    config, config_path, key,
                    prompt="一张极简测试图：灰色渐变背景中央一个白色圆形，无文字",
                    out_path=probe_dir / f"probe-{tier}.jpg",
                    role="draft", tier=tier, model=None, size=args.size,
                    references=[], out_dir=probe_dir, label=f"probe-{tier}",
                    dry_run=False,
                )
                report["probed_models"].append(
                    {"tier": tier, "provider": provider_name, "model": record.get("model"),
                     "ok": True, "bytes": record.get("bytes")})
                say(f"  [{tier:10s}] live OK  {record.get('model')}  "
                    f"{record.get('bytes', 0) // 1024} KB")
            except ArkError as exc:
                report["probed_models"].append(
                    {"tier": tier, "provider": provider_name, "model": model_id, "ok": False,
                     "error": str(exc)})
                say(f"  [{tier:10s}] live FAILED — {str(exc)[:150]}")
        failures = [m for m in report["probed_models"] if not m["ok"]]
        return done(1 if failures else 0)

    if args.dry_run:
        say(
            "\n[dry-run] connectivity probe skipped — no API key was resolved and no "
            "request was sent. Re-run without --dry-run to check the endpoints."
        )
        return done(0)

    # Free connectivity check: a request that MUST be rejected by body validation. A
    # structured 4xx proves the endpoint is reachable and the key was accepted, without
    # generating (and paying for) an image — safe to run before every poem.
    #
    # The canary differs per provider. Ark validates `size` strictly, so 1x1 works and
    # also proves the model id (Ark resolves the model before validating the body).
    # The OpenAI-compatible gateway validates the body FIRST and happily accepts
    # nonsense sizes (1x1 and even "abc" return 200), so an out-of-range `n` is the only
    # reliable canary there — and by the same token a free probe cannot vouch for the
    # model id on that provider. Only --live can.
    say(f"\nconnectivity probe (free, no image generated), {len(tiers)} model(s)")
    failures = 0
    for tier in tiers:
        model_id, provider_name = resolve_model_entry(config, tier)
        provider = providers.get(provider_name) or {}
        key = keys.get(provider_name, "")
        base = str(provider.get("base_url") or "").rstrip("/")
        url = base + str(provider.get("generations_path") or "/images/generations")
        if not key:
            say(f"  [{tier:10s}] {model_id:26s} SKIPPED — no API key for {provider_name}")
            report["probed_models"].append(
                {"tier": tier, "provider": provider_name, "model": model_id, "ok": False,
                 "error": "no API key"})
            failures += 1
            continue

        if provider_kind(provider) == "openai-images":
            payload = {"model": model_id, "prompt": "connectivity probe", "n": 0}
            canary = "n"
            verifies_model = False
        else:
            payload = {
                "model": model_id,
                "prompt": "connectivity probe — this request must be rejected by size validation",
                "size": "1x1",
                "response_format": "url",
            }
            canary = "size"
            verifies_model = True
        try:
            post_json(url, key, payload, config, "probe", provider)
            say(f"  [{tier:10s}] {model_id:26s} UNEXPECTED — the API accepted an invalid "
                f"'{canary}'")
            report["probed_models"].append(
                {"tier": tier, "provider": provider_name, "model": model_id, "ok": False})
            failures += 1
        except ArkError as exc:
            message = str(exc)
            mentions = canary in message.lower()
            # Both providers answer body-validation failures with a structured 4xx whose
            # message names the offending field; a key problem would be 401/403 instead.
            rejected = any(token in message for token in (
                "InvalidParameter", "HTTP 400", "HTTP 422",
                "invalid_request_error", "bad_request",
            ))
            if mentions and rejected:
                if verifies_model:
                    verdict = "OK — endpoint reachable, key accepted, model id valid"
                else:
                    verdict = ("OK — endpoint reachable, key accepted "
                               "(model id NOT verified; use --live for that)")
                say(f"  [{tier:10s}] {model_id:26s} {verdict}")
                report["probed_models"].append(
                    {"tier": tier, "provider": provider_name, "model": model_id, "ok": True,
                     "model_verified": verifies_model})
            else:
                detail = message.split(" — ")[0].strip()[:170]
                say(f"  [{tier:10s}] {model_id:26s} FAILED — {detail}")
                report["probed_models"].append(
                    {"tier": tier, "provider": provider_name, "model": model_id, "ok": False,
                     "error": detail})
                failures += 1

    if failures:
        say(
            f"\n{failures} of {len(tiers)} models failed. Fix the key, the base_url, or the "
            f"models section of {config_path.name} before generating anything."
        )
        return done(1)
    say("\nEndpoints and keys are good. Run with --live to also prove every model id by "
        "generating one image each.")
    return done(0)


def command_t2i(args, config: dict, config_path: Path) -> int:
    key = None
    out = Path(args.out).expanduser()
    count = max(1, int(args.n))
    base_label = args.name or out.stem
    records = []
    failures: list[str] = []
    for index in range(count):
        target = out if count == 1 else out.with_name(f"{out.stem}-{index + 1}{out.suffix}")
        label = base_label if count == 1 else f"{base_label}-{index + 1}"
        try:
            records.append(
                generate_one(
                    config,
                    config_path,
                    key,
                    prompt=args.prompt,
                    out_path=target,
                    role=args.role,
                    tier=args.tier,
                    model=args.model,
                    size=args.size,
                    references=[],
                    out_dir=args.out_dir and Path(args.out_dir),
                    label=label,
                    dry_run=args.dry_run,
                    provider=args.provider,
                )
            )
        except ArkError as exc:
            # One failed iteration must not discard the images already generated (and
            # billed): report it, keep going, and let the successes reach finish().
            failures.append(label)
            print(f"[{label}] FAILED — {exc}", file=sys.stderr)
    return finish(records, args, failures)


def command_i2i(args, config: dict, config_path: Path) -> int:
    if not args.ref:
        raise ArkError("i2i requires at least one --ref (file path, URL, or sibling image name).")
    key = None
    out = Path(args.out).expanduser()
    count = max(1, int(args.n))
    base_label = args.name or out.stem
    records = []
    failures: list[str] = []
    for index in range(count):
        target = out if count == 1 else out.with_name(f"{out.stem}-{index + 1}{out.suffix}")
        label = base_label if count == 1 else f"{base_label}-{index + 1}"
        try:
            records.append(
                generate_one(
                    config,
                    config_path,
                    key,
                    prompt=args.prompt,
                    out_path=target,
                    role=args.role,
                    tier=args.tier,
                    model=args.model,
                    size=args.size,
                    references=args.ref,
                    out_dir=args.out_dir and Path(args.out_dir),
                    label=label,
                    dry_run=args.dry_run,
                    provider=args.provider,
                )
            )
        except ArkError as exc:
            # Same contract as t2i: one bad iteration must not lose the records of the
            # iterations that already succeeded.
            failures.append(label)
            print(f"[{label}] FAILED — {exc}", file=sys.stderr)
    return finish(records, args, failures)


def command_batch(args, config: dict, config_path: Path) -> int:
    plan_path = Path(args.plan).expanduser()
    if not plan_path.is_file():
        raise ArkError(f"plan file not found: {plan_path}")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ArkError(f"plan file is not valid JSON: {plan_path} ({exc})") from exc
    except OSError as exc:
        raise ArkError(f"plan file could not be read: {plan_path} ({exc})") from exc
    if not isinstance(plan, dict):
        raise ArkError(f"plan file must contain a JSON object: {plan_path}")

    out_dir = Path(args.out_dir or plan.get("out_dir") or plan_path.parent).expanduser()
    entries = plan.get("images") or []
    if not entries:
        raise ArkError(f"plan file has no images: {plan_path}")

    key = None
    if not args.dry_run:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArkError(f"cannot use out_dir {out_dir}: {exc}") from exc

    say(f"plan    : {plan_path}")
    say(f"out_dir : {out_dir}")
    say(f"images  : {len(entries)}\n")

    records: list[dict] = []
    failures: list[str] = []
    recorded = {entry["name"]: entry for entry in load_manifest_records(out_dir, config)}

    for index, entry in enumerate(entries):
        label = f"entry {index}"
        try:
            name = str(entry["name"])
            label = name
            target = out_dir / f"{name}.jpg"
            if not args.force:
                previous = recorded.get(name)
                previous_path = (
                    resolve_recorded_path(str(previous["output"]), out_dir) if previous else None
                )
                if previous_path is not None and previous_path.is_file():
                    # normalize_out_path may have written a different extension than .jpg
                    # (e.g. the API returned png), so trust the manifest's recorded path —
                    # resolved against out_dir, not against whatever CWD wrote it.
                    say(
                        f"[{name}] already generated at {previous_path} — skipped "
                        "(use --force to regenerate)"
                    )
                    records.append(
                        skipped_record(
                            entry,
                            name,
                            previous_path,
                            config,
                            role=entry.get("role", args.role),
                            tier=entry.get("tier", args.tier),
                            model=entry.get("model", args.model),
                            previous=previous,
                        )
                    )
                    continue
                if target.is_file():
                    say(f"[{name}] already exists — skipped (use --force to regenerate)")
                    records.append(
                        skipped_record(
                            entry,
                            name,
                            target,
                            config,
                            role=entry.get("role", args.role),
                            tier=entry.get("tier", args.tier),
                            model=entry.get("model", args.model),
                        )
                    )
                    continue
            records.append(
                generate_one(
                    config,
                    config_path,
                    key,
                    prompt=entry["prompt"],
                    out_path=target,
                    role=entry.get("role", args.role),
                    tier=entry.get("tier", args.tier),
                    model=entry.get("model", args.model),
                    size=entry.get("size", args.size),
                    references=normalize_references(entry, label),
                    out_dir=out_dir,
                    label=name,
                    dry_run=args.dry_run,
                    provider=entry.get("provider", args.provider),
                )
            )
        except (ArkError, KeyError, TypeError) as exc:
            # Keep going: a six-image run should not lose the five that succeeded.
            failures.append(label)
            if isinstance(exc, KeyError):
                detail = f"the plan entry is missing the required '{exc.args[0]}' field"
            elif isinstance(exc, TypeError) and not isinstance(entry, dict):
                detail = f"the plan entry must be an object, got {type(entry).__name__}"
            else:
                detail = str(exc)
            print(f"[{label}] FAILED — {detail}", file=sys.stderr)

    if args.dry_run:
        finish(records, args)
        if failures:
            print("failed: " + ", ".join(failures), file=sys.stderr)
            return 1
        return 0

    emit_json(records, args)

    if not args.no_manifest:
        if records:
            manifest = write_manifest(out_dir, config, records)
            say(f"\nmanifest: {manifest}")
        # The sheet covers every image in out_dir, not only this run's records, so it is
        # refreshed even when this run generated nothing new.
        merged = load_manifest_records(out_dir, config) or records
        if merged:
            sheet = write_contact_sheet(out_dir, config, merged)
            if sheet:
                say(f"contact : {sheet}  ← inspect every image together before wiring them into the page")

    generated = sum(1 for record in records if not record.get("skipped"))
    say(
        f"\ndone: {generated} generated, {len(records) - generated} skipped, "
        f"{len(failures)} failed"
    )
    if failures:
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def finish(records: list[dict], args, failures: list[str] | None = None) -> int:
    failures = list(failures or [])
    emit_json(records, args)
    if args.dry_run:
        if failures:
            print("failed: " + ", ".join(failures), file=sys.stderr)
            return 1
        return 0
    out_dir = Path(records[0]["output"]).parent if records else None
    if out_dir and not args.no_manifest:
        config = args._config
        manifest = write_manifest(out_dir, config, records)
        say(f"manifest: {manifest}")
        # The sheet covers every image in out_dir, not only this run's records.
        sheet = write_contact_sheet(out_dir, config, load_manifest_records(out_dir, config) or records)
        if sheet:
            say(f"contact : {sheet}")
    if failures:
        # The successful iterations are already recorded on disk; the exit code still has
        # to tell the caller that the run as a whole did not succeed.
        print("failed: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


# --------------------------------------------------------------------------- cli


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="path to ark.config.json (defaults to the skill config)")
    parser.add_argument("--tier", help="model tier override, e.g. pro or lite; validated against the config")
    parser.add_argument("--model", help="explicit model id, or a configured tier name")
    parser.add_argument("--provider", help="force an image provider by name (see image.providers)")
    parser.add_argument("--size", help="WIDTHxHEIGHT or a preset name from the config")
    parser.add_argument("--role", default=None, choices=["hero", "beat", "draft", "repair"])
    parser.add_argument("--out-dir", help="directory used to resolve sibling reference names")
    parser.add_argument("--name", help="label used in the manifest")
    parser.add_argument("--json", action="store_true", help="print machine-readable records")
    parser.add_argument("--dry-run", action="store_true", help="print the request without calling")
    parser.add_argument("--no-manifest", action="store_true", help="do not write prompts.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ark_image.py",
        description="Volcengine Ark image generation for the poetry-cinema-page skill.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe", help="check config, credentials and connectivity")
    add_common(probe)
    probe.add_argument("--live", action="store_true", help="also generate one real image")

    t2i = subparsers.add_parser("t2i", help="text to image")
    add_common(t2i)
    t2i.add_argument("--prompt", required=True)
    t2i.add_argument("--out", required=True, help="output image path")
    t2i.add_argument("--n", type=int, default=1, help="repeat the call N times")

    i2i = subparsers.add_parser("i2i", help="image to image")
    add_common(i2i)
    i2i.add_argument("--prompt", required=True)
    i2i.add_argument("--out", required=True, help="output image path")
    i2i.add_argument("--ref", action="append", default=[], help="reference image; repeatable")
    i2i.add_argument("--n", type=int, default=1, help="repeat the call N times")

    batch = subparsers.add_parser("batch", help="generate a whole poem image set from a plan")
    add_common(batch)
    batch.add_argument("--plan", required=True, help="plan JSON with out_dir and images[]")
    batch.add_argument("--force", action="store_true", help="regenerate images that already exist")

    return parser


def main(argv: list[str] | None = None) -> int:
    global _JSON_MODE
    args = build_parser().parse_args(argv)
    _JSON_MODE = bool(getattr(args, "json", False))
    try:
        config, config_path = load_config(args.config)
        config["_config_path"] = str(config_path)
        if getattr(args, "role", None) is None:
            args.role = config["defaults"].get("role", "beat")
        args._config = config
        handler = {
            "probe": command_probe,
            "t2i": command_t2i,
            "i2i": command_i2i,
            "batch": command_batch,
        }[args.command]
        return handler(args, config, config_path)
    except ArkError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
