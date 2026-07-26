#!/usr/bin/env python3
"""通过兼容 Grok2API 的接口，使用 grok-imagine-image 生成图片。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse


# Placeholder credentials. Replace before production use.
DEFAULT_API_BASE = "http://43.163.230.83:8000/v1"
DEFAULT_API_KEY = "g2a_REPLACE_ME"
DEFAULT_MODEL = "grok-imagine-image"
DEFAULT_TIMEOUT = 180
DEFAULT_SIZE = "1024x1024"


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def resolve_api_base(value: str | None) -> str:
    base = (value or os.environ.get("GROK_IMAGINE_API_BASE") or DEFAULT_API_BASE).rstrip("/")
    if not base.endswith("/v1"):
        # Accept either host root or full /v1 base.
        if base.endswith("/v1/"):
            base = base.rstrip("/")
        else:
            base = f"{base}/v1"
    return base


def resolve_api_key(value: str | None) -> str:
    key = value or os.environ.get("GROK_IMAGINE_API_KEY") or DEFAULT_API_KEY
    if not key or key == "g2a_REPLACE_ME":
        eprint(
            "错误：API Key 仍是占位符。"
            "请设置 GROK_IMAGINE_API_KEY，或传入 --api-key，"
            "或修改本脚本中的 DEFAULT_API_KEY。"
        )
        sys.exit(2)
    return key


def rewrite_media_url(url: str, api_base: str) -> str:
    """Rewrite loopback media URLs to the configured public API host."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        return url

    base = urlparse(api_base if "://" in api_base else f"http://{api_base}")
    # Keep path from media URL; swap scheme/netloc to public host.
    return urlunparse(
        (
            base.scheme or "http",
            base.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def http_json(
    method: str,
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, dict[str, str], Any]:
    data = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "grok-imagine-image-skill/1.0",
    }
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            headers_out = {k.lower(): v for k, v in resp.headers.items()}
            text = body.decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text) if text else {}
            except json.JSONDecodeError:
                parsed = {"raw": text}
            return resp.status, headers_out, parsed
    except urllib.error.HTTPError as err:
        body = err.read()
        text = body.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text) if text else {"error": {"message": text}}
        except json.JSONDecodeError:
            parsed = {"error": {"message": text or str(err)}}
        headers_out = {k.lower(): v for k, v in err.headers.items()} if err.headers else {}
        return err.code, headers_out, parsed
    except urllib.error.URLError as err:
        raise RuntimeError(f"调用 {url} 时网络错误: {err}") from err


def download_file(url: str, dest: Path, *, api_key: str, timeout: int) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "grok-imagine-image-skill/1.0",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        data = resp.read()

    # Ensure extension based on content type if missing.
    if dest.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }.get(content_type, ".jpg")
        dest = dest.with_suffix(ext)

    dest.write_bytes(data)
    return dest


def slugify(text: str, max_len: int = 48) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text, flags=re.IGNORECASE)
    text = re.sub(r"-+", "-", text).strip("-")
    if not text:
        text = "image"
    return text[:max_len].rstrip("-")


def generate_images(
    *,
    prompt: str,
    api_base: str,
    api_key: str,
    model: str,
    n: int,
    size: str,
    timeout: int,
    response_format: str | None,
) -> dict[str, Any]:
    url = f"{api_base}/images/generations"
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
    }
    if response_format:
        payload["response_format"] = response_format

    status, _headers, body = http_json(
        "POST",
        url,
        api_key=api_key,
        payload=payload,
        timeout=timeout,
    )
    if status >= 400:
        message = body
        if isinstance(body, dict):
            err = body.get("error") or body
            if isinstance(err, dict):
                message = err.get("message") or err
        raise RuntimeError(f"图片生成失败（{status}）: {message}")
    if not isinstance(body, dict) or "data" not in body:
        raise RuntimeError(f"响应结构异常: {body}")
    return body


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="使用 grok-imagine-image 生成图片（兼容 Grok2API）。"
    )
    parser.add_argument("--prompt", help="图片提示词")
    parser.add_argument("--prompt-file", help="从文本文件读取提示词")
    parser.add_argument(
        "--output-dir",
        default="./outputs",
        help="图片保存目录（默认: ./outputs）",
    )
    parser.add_argument(
        "--name-tag",
        default=None,
        help="文件名前缀（默认根据提示词生成）",
    )
    parser.add_argument("--n", type=int, default=1, help="生成数量（默认: 1）")
    parser.add_argument(
        "--size",
        default=DEFAULT_SIZE,
        help=f"图片尺寸（默认: {DEFAULT_SIZE}）",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("GROK_IMAGINE_MODEL", DEFAULT_MODEL),
        help=f"模型 ID（默认: {DEFAULT_MODEL}）",
    )
    parser.add_argument(
        "--api-base",
        default=None,
        help=f"API 基础地址（默认: {DEFAULT_API_BASE} 或 GROK_IMAGINE_API_BASE）",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API Key（默认: GROK_IMAGINE_API_KEY 或脚本内占位符）",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"HTTP 超时秒数（默认: {DEFAULT_TIMEOUT}）",
    )
    parser.add_argument(
        "--response-format",
        choices=["url", "b64_json"],
        default=None,
        help="可选的 OpenAI 风格 response_format",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="只打印 API 结果，不下载图片",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="向标准输出打印机器可读 JSON 摘要",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
    elif args.prompt:
        prompt = args.prompt.strip()
    else:
        eprint("错误：请提供 --prompt 或 --prompt-file")
        return 2

    if not prompt:
        eprint("错误：提示词为空")
        return 2

    api_base = resolve_api_base(args.api_base)
    api_key = resolve_api_key(args.api_key)
    output_dir = Path(args.output_dir)
    name_tag = args.name_tag or slugify(prompt)

    eprint(f"API 地址 : {api_base}")
    eprint(f"模型     : {args.model}")
    eprint(f"提示词   : {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    eprint(f"输出目录 : {output_dir}")

    started = time.time()
    result = generate_images(
        prompt=prompt,
        api_base=api_base,
        api_key=api_key,
        model=args.model,
        n=max(1, args.n),
        size=args.size,
        timeout=args.timeout,
        response_format=args.response_format,
    )
    elapsed = time.time() - started

    items = result.get("data") or []
    saved: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        raw_url = item.get("url") or ""
        public_url = rewrite_media_url(str(raw_url), api_base) if raw_url else ""
        mime = item.get("mime_type") or "image/jpeg"
        record: dict[str, Any] = {
            "index": idx,
            "mime_type": mime,
            "url": public_url or raw_url,
            "raw_url": raw_url,
            "revised_prompt": item.get("revised_prompt") or "",
        }

        if not args.no_download and public_url:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{name_tag}-{stamp}-{idx + 1}"
            dest = output_dir / filename
            try:
                path = download_file(
                    public_url,
                    dest,
                    api_key=api_key,
                    timeout=args.timeout,
                )
                record["path"] = str(path.resolve())
                record["bytes"] = path.stat().st_size
                eprint(f"已保存[{idx + 1}]: {path} ({record['bytes']} 字节)")
            except Exception as err:  # noqa: BLE001 - surface download issues clearly
                record["download_error"] = str(err)
                eprint(f"警告：第 {idx + 1} 张图下载失败: {err}")
        saved.append(record)

    summary = {
        "ok": True,
        "model": args.model,
        "api_base": api_base,
        "prompt": prompt,
        "created": result.get("created"),
        "elapsed_sec": round(elapsed, 2),
        "count": len(saved),
        "images": saved,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("生成成功。")
        for item in saved:
            print(f"- url: {item.get('url')}")
            if item.get("path"):
                print(f"  path: {item['path']}")
            if item.get("download_error"):
                print(f"  download_error: {item['download_error']}")
        print(f"耗时: {summary['elapsed_sec']}s")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        eprint("已中断。")
        raise SystemExit(130)
    except Exception as err:  # noqa: BLE001
        eprint(f"错误: {err}")
        raise SystemExit(1)
