#!/usr/bin/env python3
"""
通用图像生成器
调用 MuleRun / APImart / Atlas Cloud / Agnes API,支持 generation(纯文本生图)和 edit(带参考图修图)两种模式。
单张用 CLI 参数,批量用 manifest JSON。

用法:
    # 单张生图
    python generate.py --mode generation --prompt "..." --name-tag diagram-001 --output-dir ./out

    # 单张修图
    python generate.py --mode edit --prompt "..." --images "https://..." --name-tag cover --output-dir ./out

    # 从文件读 prompt
    python generate.py --mode generation --prompt-file ./prompt.txt --output-dir ./out

    # 批量(串行)
    python generate.py --manifest ./batch.json --output-dir ./out

    # 批量(并行)
    python generate.py --manifest ./batch.json --output-dir ./out --parallel

环境变量:
    MULERUN_API_KEY    --provider mulerun 时必填
    APIMART_API_KEY    --provider apimart 时必填
    ATLASCLOUD_API_KEY --provider atlascloud 时必填
    AGNES_API_KEY      --provider agnes 时必填
    VOLCENGINE_API_KEY --provider volcengine 时必填 (火山引擎 Ark Seedream)
    VOLCENGINE_API_BASE_URL 可选,默认 https://ark.cn-beijing.volces.com/api/plan/v3
    VOLCENGINE_IMAGE_MODEL 可选,默认 doubao-seedream-5.0-lite
    AGNES_API_BASE_URL 可选,默认 https://apihub.agnes-ai.com/v1
    AGNES_IMAGE_MODEL  可选,默认 agnes-image-2.1-flash

示例 (Agnes):
    export AGNES_API_KEY=sk-xxx
    python generate.py --provider agnes --mode generation --prompt "..." --output-dir ./out
    python generate.py --provider agnes --mode edit --prompt "..." --image ./ref.png --output-dir ./out

Manifest JSON 格式:
    {
      "mode": "generation",
      "aspect_ratio": "16:9",
      "resolution": "2K",
      "items": [
        {"id": "img-001", "prompt": "..."},
        {"id": "img-002", "prompt": "...", "images": ["https://..."]}
      ]
    }

产出:
    单张: {name-tag}-{timestamp}.png / .txt / .json
    批量: {id}.png / {id}.txt / {id}.json + _run_metadata.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

from providers import get_provider, get_provider_class, list_providers
from providers.base import BaseProvider, download_image

import re
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
VALID_MODES = {"generation", "edit", "mixed"}


def sanitize_item_id(item_id: str):
    if not item_id or not isinstance(item_id, str):
        return None
    candidate = item_id.strip()
    if not SAFE_ID_RE.fullmatch(candidate):
        return None
    if ".." in candidate or "/" in candidate or "\\" in candidate:
        return None
    return candidate


def parse_images_args(args):
    images = []
    if getattr(args, "image", None):
        images.extend([x.strip() for x in args.image if x and x.strip()])
    if getattr(args, "images", None):
        for chunk in str(args.images).split(","):
            chunk = chunk.strip()
            if chunk:
                images.append(chunk)
    return images or None


def save_image_ref(image_ref: str, save_path: Path) -> bool:
    """Save http(s) image URL or data:image/...;base64,... payload to disk."""
    if image_ref.startswith("data:image"):
        try:
            import base64
            header, b64 = image_ref.split(",", 1)
            save_path.write_bytes(base64.b64decode(b64))
            return True
        except Exception as e:
            print(f"    ✗ 保存 base64 图片失败: {e}")
            return False
    return download_image(image_ref, save_path)


# ============================================================
# 默认配置
# ============================================================

DEFAULT_ASPECT_RATIO = "16:9"
DEFAULT_RESOLUTION = "2K"
DEFAULT_PROVIDER = "mulerun"

# ============================================================


def validate_item(item: dict, manifest_mode: str = "generation", seen_ids: Optional[set] = None) -> Optional[str]:
    if not isinstance(item, dict):
        return "item 必须是对象"
    if seen_ids is None:
        seen_ids = set()
    safe_id = sanitize_item_id(item.get("id") if isinstance(item.get("id"), str) else None)
    if not safe_id:
        return f"非法 id: {item.get('id')!r} (仅允许字母数字._- , 禁止路径)"
    if safe_id in seen_ids:
        return f"重复 id: {safe_id}"
    item["id"] = safe_id
    seen_ids.add(safe_id)
    if not isinstance(item.get("prompt"), str) or not item.get("prompt").strip():
        return "缺少字段: prompt"
    item_mode = resolve_item_mode(item, manifest_mode)
    if item_mode not in ("generation", "edit"):
        return f"非法 mode: {item_mode}"
    images = item.get("images")
    if item_mode == "edit":
        if not isinstance(images, list) or not any(isinstance(x, str) and x.strip() for x in images):
            return "edit 模式必须提供非空 images 数组"
    if images is not None and not isinstance(images, list):
        return "images 必须是数组"
    return None


def resolve_item_mode(item: dict, manifest_mode: str) -> str:
    """Resolve the effective mode for an item.

    When manifest_mode is "mixed" (used by cartoon-infographic style),
    each item may specify its own mode via the "mode" field.
    Otherwise, all items use the manifest's top-level mode.
    """
    if manifest_mode == "mixed":
        return item.get("mode", "generation")
    return manifest_mode


def load_blocklist(blocklist_path: Optional[str]) -> Optional[list[str]]:
    if not blocklist_path:
        return None
    p = Path(blocklist_path)
    if not p.exists():
        print(f"✗ blocklist 文件不存在: {p}")
        sys.exit(1)
    terms = [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not terms:
        return None
    print(f"✓ 加载 blocklist: {p} ({len(terms)} 个词)")
    return terms


def check_blocklist(prompt: str, terms: Optional[list[str]], context: str = "") -> None:
    if not terms:
        return
    hits = [t for t in terms if t in prompt]
    if not hits:
        return
    label = f" [{context}]" if context else ""
    print(f"✗ 提示词{label}命中 blocklist 禁用词,已停止生成")
    print(f"  命中的词: {', '.join(hits)}")
    sys.exit(1)


def process_single_item(
    item: dict, output_dir: Path, provider: BaseProvider, mode: str,
    aspect_ratio: str, resolution: str, index: int, total: int,
) -> dict:
    item_id = item["id"]
    images = item.get("images")

    print(f"\n[{index}/{total}] {item_id} mode={mode}")
    if mode == "edit" and (not images or not any(isinstance(x, str) and x.strip() for x in images)):
        print("    ✗ edit 模式缺少参考图 images")
        return {"id": item_id, "status": "failed", "stage": "validate"}

    task_id = provider.create_task(item["prompt"], mode, images, aspect_ratio, resolution)
    if not task_id:
        return {"id": item_id, "status": "failed", "stage": "create"}
    print(f"    ✓ task_id: {task_id}")

    print(f"    → 轮询中")
    result = provider.poll_task(task_id, mode)
    if not result:
        return {"id": item_id, "status": "failed", "stage": "poll", "task_id": task_id}

    result_images = result.get("images", [])
    if not result_images:
        return {"id": item_id, "status": "failed", "stage": "no_image", "task_id": task_id}

    prompt_path = output_dir / f"{item_id}.txt"
    prompt_path.write_text(item["prompt"], encoding="utf-8")

    image_paths = []
    for idx, image_url in enumerate(result_images):
        suffix = f"-{idx}" if len(result_images) > 1 else ""
        image_path = output_dir / f"{item_id}{suffix}.png"
        print(f"    → 下载图片({idx+1}/{len(result_images)}) → {image_path.name}")
        if not save_image_ref(image_url, image_path):
            return {"id": item_id, "status": "failed", "stage": "download", "task_id": task_id}
        image_paths.append(str(image_path))
        print(f"    ✓ {image_path.stat().st_size // 1024} KB")

    meta_path = output_dir / f"{item_id}.json"
    size_meta = result.get("size_meta") if isinstance(result, dict) else None
    if not size_meta and hasattr(provider, "describe_output_size"):
        size_meta = provider.describe_output_size(aspect_ratio, resolution)
    meta_path.write_text(
        json.dumps({
            "id": item_id,
            "mode": mode,
            "task_id": task_id,
            "images": image_paths,
            "requested": {"aspect_ratio": aspect_ratio, "resolution": resolution},
            "size": size_meta or {
                "requested_aspect_ratio": aspect_ratio,
                "requested_resolution": resolution,
                "actual_size": None,
                "resolution_honored": True,
                "notes": "",
            },
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "id": item_id, "status": "completed",
        "image_urls": result_images, "local_images": image_paths,
        "task_id": task_id,
    }


def _download_item(iid: str, item: dict, poll_result: Optional[dict],
                   output_dir: Path, task_id: str) -> dict:
    if not poll_result:
        return {"id": iid, "status": "failed", "stage": "poll", "task_id": task_id}

    images = poll_result.get("images", [])
    if not images:
        return {"id": iid, "status": "failed", "stage": "no_image", "task_id": task_id}

    prompt_path = output_dir / f"{iid}.txt"
    prompt_path.write_text(item["prompt"], encoding="utf-8")

    image_paths = []
    for idx, image_url in enumerate(images):
        suffix = f"-{idx}" if len(images) > 1 else ""
        image_path = output_dir / f"{iid}{suffix}.png"
        if not save_image_ref(image_url, image_path):
            return {"id": iid, "status": "failed", "stage": "download", "task_id": task_id}
        image_paths.append(str(image_path))

    return {"id": iid, "status": "completed", "image_urls": images, "local_images": image_paths, "task_id": task_id}


def run_parallel(items: list, output_dir: Path, provider, manifest_mode: str,
                  aspect_ratio: str, resolution: str) -> list:
    if not items:
        print("⚠ 没有可执行 item, 跳过并行执行")
        return []

    # End-to-end per item (create -> poll/download) to avoid temporary URL expiry
    # and to make --parallel actually concurrent for sync providers like Agnes.
    results = []
    max_workers = min(4, len(items))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for idx, item in enumerate(items, 1):
            item_mode = resolve_item_mode(item, manifest_mode)
            fut = executor.submit(
                process_single_item, item, output_dir, provider, item_mode,
                aspect_ratio, resolution, idx, len(items),
            )
            futures[fut] = item.get("id", f"item-{idx}")
        for fut in as_completed(futures):
            item_id = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                print(f"    ✗ {item_id} 并行执行异常: {e}")
                results.append({"id": item_id, "status": "failed", "stage": "exception", "error": str(e)})
    order = {item["id"]: i for i, item in enumerate(items)}
    results.sort(key=lambda r: order.get(r.get("id"), 10**9))
    return results


def run_single(mode: str, prompt: str, images: Optional[list[str]], name_tag: str,
               output_dir: Path, provider, aspect_ratio: str, resolution: str) -> None:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_stem = f"{name_tag}-{timestamp}"

    print(f"→ 创建{mode}任务")

    task_id = provider.create_task(prompt, mode, images, aspect_ratio, resolution)
    if not task_id:
        print("✗ 创建任务失败")
        sys.exit(1)
    print(f"✓ task_id: {task_id}")

    print(f"→ 轮询中(最多等 {provider.POLL_MAX_TIMES * provider.POLL_INTERVAL}s)")
    result = provider.poll_task(task_id, mode)
    if not result:
        print("✗ 任务失败或超时")
        sys.exit(1)

    result_images = result.get("images", [])
    if not result_images:
        print("✗ API 成功但无图片")
        sys.exit(1)

    prompt_path = output_dir / f"{file_stem}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")

    image_paths = []
    for idx, image_url in enumerate(result_images):
        suffix = f"-{idx}" if len(result_images) > 1 else ""
        image_path = output_dir / f"{file_stem}{suffix}.png"
        print(f"→ 下载图片({idx+1}/{len(result_images)}) → {image_path.name}")
        if not save_image_ref(image_url, image_path):
            sys.exit(1)
        image_paths.append(image_path)
        print(f"✓ {image_path.stat().st_size // 1024} KB")

    meta_path = output_dir / f"{file_stem}.json"
    size_meta = result.get("size_meta") if isinstance(result, dict) else None
    if not size_meta and hasattr(provider, "describe_output_size"):
        size_meta = provider.describe_output_size(aspect_ratio, resolution)
    meta_path.write_text(
        json.dumps({
            "task_id": task_id,
            "mode": mode,
            "provider": getattr(provider, "model", None) and provider.__class__.__name__ or provider.__class__.__name__,
            "image_urls": result_images,
            "local_images": [str(p) for p in image_paths],
            "requested": {"aspect_ratio": aspect_ratio, "resolution": resolution},
            "size": size_meta or {
                "requested_aspect_ratio": aspect_ratio,
                "requested_resolution": resolution,
                "actual_size": None,
                "resolution_honored": True,
                "notes": "",
            },
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 60)
    print(f"✓ 生成完毕,共 {len(result_images)} 张图片")
    for p in image_paths:
        print(f"  📁 {p}")
    print(f"  📝 {prompt_path}")
    print("=" * 60)
    print(f"  不满意可改 .txt 提示词后重跑:")
    print(f"  python {Path(__file__).name} --mode {mode} --prompt-file {prompt_path} --name-tag {name_tag}-v2")


def main():
    # 确保 providers 包可被导入 (脚本直接运行时的路径问题)
    sys.path.insert(0, str(Path(__file__).parent))

    parser = argparse.ArgumentParser(description="通用图像生成器 (MuleRun / APImart / Atlas Cloud / Agnes / Volcengine)")

    parser.add_argument("--provider", choices=list_providers(), default=None,
                        help="API 提供商; 不传则自动检测, 多 key 时必须显式指定")
    parser.add_argument("--mode", choices=["generation", "edit"], help="生成模式: generation(纯文本生图) 或 edit(带参考图)")
    prompt_src = parser.add_mutually_exclusive_group()
    prompt_src.add_argument("--prompt", type=str, help="提示词文本")
    prompt_src.add_argument("--prompt-file", type=str, help="提示词文件路径")
    prompt_src.add_argument("--manifest", type=str, help="批量 manifest JSON 路径")
    parser.add_argument("--image", action="append", dest="image", help="参考图(可重复). 支持 URL/本地路径/data URI/base64")
    parser.add_argument("--images", type=str, help="兼容旧参数: 逗号分隔 URL(不要传 data URI)")
    parser.add_argument("--name-tag", type=str, default="image", help="单张模式文件命名前缀(默认 image)")
    parser.add_argument("--output-dir", type=str, default="./output", help="输出目录(默认 ./output)")
    parser.add_argument("--aspect-ratio", type=str, default=DEFAULT_ASPECT_RATIO, help=f"纵横比(默认 {DEFAULT_ASPECT_RATIO})")
    parser.add_argument("--resolution", type=str, default=DEFAULT_RESOLUTION, help=f"分辨率(默认 {DEFAULT_RESOLUTION})")
    parser.add_argument("--parallel", action="store_true", help="批量模式启用并行执行")
    parser.add_argument("--blocklist", type=str, help="禁用词表文件路径(每行一个词,命中即停止)")
    args = parser.parse_args()

    # Provider 决策: 仅当未显式传 --provider 时自动检测; 多 key 强制显式指定
    has_map = {
        "mulerun": bool(os.environ.get("MULERUN_API_KEY")),
        "apimart": bool(os.environ.get("APIMART_API_KEY")),
        "atlascloud": bool(os.environ.get("ATLASCLOUD_API_KEY")),
        "agnes": bool(os.environ.get("AGNES_API_KEY")),
        "volcengine": bool(os.environ.get("VOLCENGINE_API_KEY") or os.environ.get("ARK_API_KEY")),
    }
    present = [k for k, v in has_map.items() if v]
    if args.provider:
        provider_name = args.provider
    elif len(present) == 1:
        provider_name = present[0]
        print(f"  自动检测: 仅发现 {provider_name.upper()}_API_KEY, 使用 {provider_name}")
    elif len(present) == 0:
        print("✗ 未发现任何 provider API Key")
        print("  请设置 MULERUN_API_KEY / APIMART_API_KEY / ATLASCLOUD_API_KEY / AGNES_API_KEY 之一")
        sys.exit(1)
    else:
        print(f"✗ 检测到多个 provider key: {', '.join(present)}")
        print("  请显式指定 --provider, 避免静默选错模型")
        sys.exit(1)

    provider_cls = get_provider_class(provider_name)

    # 加载 blocklist
    blocklist = load_blocklist(args.blocklist)

    # 鉴权
    env_var = provider_cls.env_var
    api_key = os.environ.get(env_var)
    # Volcengine Ark keys may also be provided as ARK_API_KEY
    if not api_key and provider_name == "volcengine":
        api_key = os.environ.get("ARK_API_KEY")
        if api_key:
            env_var = "ARK_API_KEY"
    if not api_key:
        print(f"✗ 未找到环境变量 {provider_cls.env_var}")
        print(f"  请先设置: export {provider_cls.env_var}=sk-xxx")
        sys.exit(1)

    try:
        provider = get_provider(provider_name, api_key)
    except ValueError as e:
        print(f"✗ provider 配置无效: {e}")
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 批量模式
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.exists():
            print(f"✗ manifest 不存在: {manifest_path}")
            sys.exit(1)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"✗ manifest JSON 解析失败: {e}")
            sys.exit(1)

        manifest_mode = manifest.get("mode", "generation")
        if manifest_mode not in VALID_MODES:
            print(f"✗ manifest.mode 非法: {manifest_mode} (允许 generation/edit/mixed)")
            sys.exit(1)
        aspect_ratio = manifest.get("aspect_ratio", args.aspect_ratio)
        resolution = manifest.get("resolution", args.resolution)
        items = manifest.get("items", [])

        if not isinstance(items, list) or not items:
            print("✗ manifest.items 必须是非空数组")
            sys.exit(1)

        total = len(items)
        print("=" * 60)
        if provider_name == "agnes":
            print(f"⚠ Agnes 忽略 resolution={resolution}; 按 aspect_ratio 映射固定 size")
        print(f"批量{manifest_mode}模式 · {total} 项 · {'并行' if args.parallel else '串行'} · provider={provider_name}")
        print(f"  参数: aspect_ratio={aspect_ratio}, resolution={resolution}")
        print(f"  输出: {output_dir}")
        print("=" * 60)

        if args.parallel:
            filtered = []
            results = []
            seen_ids: set[str] = set()
            for idx, item in enumerate(items, 1):
                err = validate_item(item, manifest_mode=manifest_mode, seen_ids=seen_ids)
                if err:
                    print(f"\n[{idx}/{total}] ✗ 跳过: {err}")
                    results.append({"id": item.get("id", "?"), "status": "failed", "stage": "validate"})
                    continue
                try:
                    check_blocklist(item["prompt"], blocklist, context=item.get("id", f"item-{idx}"))
                except SystemExit:
                    results.append({"id": item.get("id", "?"), "status": "failed", "stage": "blocklist"})
                    continue
                filtered.append(item)
            if not filtered and results:
                print("⚠ 全部 item 校验失败, 跳过并行执行")
            results += run_parallel(filtered, output_dir, provider, manifest_mode, aspect_ratio, resolution)
        else:
            results = []
            seen_ids = set()
            for idx, item in enumerate(items, 1):
                err = validate_item(item, manifest_mode=manifest_mode, seen_ids=seen_ids)
                if err:
                    print(f"\n[{idx}/{total}] ✗ 跳过: {err}")
                    results.append({"id": item.get("id", "?"), "status": "failed", "stage": "validate"})
                    continue
                check_blocklist(item["prompt"], blocklist, context=item.get("id", f"item-{idx}"))
                item_mode = resolve_item_mode(item, manifest_mode)
                results.append(process_single_item(item, output_dir, provider, item_mode, aspect_ratio, resolution, idx, total))

        # 写运行元数据
        meta_path = output_dir / "_run_metadata.json"
        meta_path.write_text(
            json.dumps({
                "timestamp": datetime.now().strftime("%Y%m%d-%H%M%S"),
                "provider": provider_name,
                "mode": manifest_mode,
                "total": total,
                "results": results,
                "params": {
                    "aspect_ratio": aspect_ratio,
                    "requested_resolution": resolution,
                    "provider_notes": (
                        "Agnes ignores resolution; actual size comes from aspect_ratio tokens"
                        if provider_name == "agnes" else None
                    ),
                },
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        success_count = sum(1 for r in results if r["status"] == "completed")
        print()
        print("=" * 60)
        print(f"{'✓' if success_count == total else '⚠'} 完成 {success_count}/{total}")
        print(f"  📁 {output_dir}")
        print(f"  📋 {meta_path}")
        print("=" * 60)
        if success_count < total:
            sys.exit(1)
        return

    # 单张模式
    if not args.mode:
        print("✗ 单张模式必须指定 --mode generation 或 --mode edit")
        sys.exit(1)

    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        p = Path(args.prompt_file)
        if not p.exists():
            print(f"✗ 文件不存在: {p}")
            sys.exit(1)
        prompt = p.read_text(encoding="utf-8")
    else:
        print("✗ 必须指定 --prompt、--prompt-file 或 --manifest")
        sys.exit(1)

    images = parse_images_args(args)
    if args.mode == "edit" and not images:
        print("✗ edit 模式必须通过 --image/--images 提供参考图")
        sys.exit(1)
    if args.images and "data:image" in args.images:
        print("✗ data URI 请用可重复 --image, 不要用逗号分隔 --images")
        sys.exit(1)

    if provider_name == "agnes":
        print(f"⚠ Agnes 忽略 resolution={args.resolution}; 按 aspect_ratio 映射固定 size")
    check_blocklist(prompt, blocklist)
    run_single(args.mode, prompt, images, args.name_tag, output_dir, provider, args.aspect_ratio, args.resolution)


if __name__ == "__main__":
    main()
