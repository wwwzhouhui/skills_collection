from __future__ import annotations

import asyncio
import base64
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ve_tools.official_auth import OfficialAuth, read_official_auth
from ve_tools.result import ToolResult
from ve_tools.run_context import RunContext, clean_env

log = logging.getLogger(__name__)
_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}

# Hard cap on a single inlined image's on-disk size. A base64 copy costs ~4/3
# this in one JSON-RPC line, and original-resolution frames (frame_zoom) can be
# tens of MB each — inlining them floods the model context. Oversized images
# are still part of the observation; they are listed for Read instead.
MAX_INLINE_IMAGE_BYTES = 3 * 1024 * 1024


def _image_content(path: str) -> types.ImageContent | None:
    p = Path(path)
    try:
        if p.stat().st_size > MAX_INLINE_IMAGE_BYTES:
            log.warning("Skipping inline of oversized image %s (%d bytes)", path, p.stat().st_size)
            return None
        data = base64.b64encode(p.read_bytes()).decode("ascii")
    except OSError as exc:
        log.warning("Failed to inline image %s: %s", path, exc)
        return None
    return types.ImageContent(type="image", data=data, mimeType=_MIME.get(p.suffix.lower(), "image/jpeg"))


def result_to_content(result: ToolResult | str) -> list[types.TextContent | types.ImageContent]:
    if isinstance(result, str):
        result = ToolResult(text=result)
    payload = result.text
    if result.data:
        import json
        payload += "\n\n```json\n" + json.dumps(result.data, ensure_ascii=False, indent=2) + "\n```"
    if result.artifacts:
        payload += "\n\nArtifacts:\n" + "\n".join(f"- {p}" for p in result.artifacts)
    if result.video_paths:
        payload += (
            "\n\nVideo outputs:\n"
            + "\n".join(f"- {p}" for p in result.video_paths)
            + "\nUse these paths for preview review, QC, or final handoff."
        )
    try:
        max_inline = int(clean_env("VE_MAX_INLINE_IMAGES") or "16")
    except ValueError:
        max_inline = 16
    max_inline = max(0, max_inline)  # 0 disables inlining entirely
    images = list(result.image_paths)
    # Split out oversized images up front so the count-slice applies only to
    # images that can actually be inlined; oversized ones join the overflow list.
    inlinable: list[str] = []
    oversized: list[str] = []
    for p in images:
        try:
            if Path(p).stat().st_size <= MAX_INLINE_IMAGE_BYTES:
                inlinable.append(p)
            else:
                oversized.append(p)
        except OSError:
            oversized.append(p)
    if max_inline and len(inlinable) > max_inline:
        overflow = inlinable[max_inline:]
        inlinable = inlinable[:max_inline]
    else:
        overflow = []
    overflow.extend(oversized)
    if overflow or not max_inline:
        skipped_note = (
            " (oversized frames are listed rather than inlined to bound context)"
            if oversized else ""
        )
        listed = images if not max_inline else overflow
        payload += (
            f"\n\n[note] This tool produced {len(images)} image(s){skipped_note}. "
            + ("Inlining is disabled (VE_MAX_INLINE_IMAGES=0); all of them "
               if not max_inline else
               f"{max_inline} are inlined below; the remaining {len(overflow)} ")
            + "are equally part of this observation and must be read before making visual decisions. "
            "Use Read on these paths, preferably in one parallel batch:\n"
            + "\n".join(f"- {p}" for p in listed)
        )
    out: list[types.TextContent | types.ImageContent] = [types.TextContent(type="text", text=payload)]
    failed_inline: list[str] = []
    for image_path in inlinable:
        content = _image_content(image_path)
        if content is not None:
            out.append(content)
        else:
            failed_inline.append(image_path)
    if failed_inline:
        # 内联失败必须在返回文本里留痕: 只警告 stderr 的话, 主模型看到
        # "inlined below" 却少了图, 无从察觉观察证据缺失
        out.append(types.TextContent(
            type="text",
            text=(
                f"[note] {len(failed_inline)} image(s) failed to inline but are still part of this "
                "observation — Read these paths before making visual decisions:\n"
                + "\n".join(f"- {p}" for p in failed_inline)
            ),
        ))
    return out


def serve(server_name: str, schemas: dict[str, dict], impls: dict[str, Callable], ctx: RunContext) -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format=f"[{server_name}] %(levelname)s %(message)s")
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"{server_name}-tools")

    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(name=name, description=schema["description"], inputSchema=schema["inputSchema"])
            for name, schema in schemas.items()
        ]

    async def call_tool(name: str, arguments: dict, official_auth: OfficialAuth | None = None):
        fn = impls.get(name)
        if fn is None:
            return [types.TextContent(type="text", text=f"[ERROR] Unknown tool: {name}")]
        if arguments is None:
            tool_args = {}
        elif isinstance(arguments, dict):
            tool_args = arguments
        else:
            return [types.TextContent(type="text", text="[ERROR] tool arguments must be a JSON object")]

        def _run():
            # 在 worker 线程里赋值而不是提交前：事件循环可能在上一次工具体还在跑时就受理下一次
            # tools/call，提交前赋值会覆盖在飞调用的身份。executor 是单 worker，因此工具体之间
            # 严格串行，这里的赋值与其后的整个工具体属同一次调用。
            ctx.official_auth = official_auth
            try:
                return result_to_content(fn(tool_args, ctx))
            except Exception as exc:
                tb = traceback.format_exc(limit=6)
                return [types.TextContent(type="text", text=f"[ERROR] tool {name} failed: {exc}\n{tb}")]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, _run)

    # mcp>=1.22 switched lowlevel Server registration from decorator methods to
    # constructor callbacks. Keep the older decorator path for pinned installs.
    server = Server(server_name)
    if hasattr(server, "list_tools") and hasattr(server, "call_tool"):
        # 身份头必须在事件循环线程里读：request_context 是 contextvar，
        # 不跨 run_in_executor 的线程边界（见 ve_tools/official_auth.py）。
        async def call_tool_entry(name: str, arguments: dict):
            return await call_tool(name, arguments, read_official_auth(server=server))

        server.list_tools()(list_tools)
        server.call_tool()(call_tool_entry)
    else:
        async def on_list_tools(_request_context, _params):
            return types.ListToolsResult(tools=await list_tools())

        async def on_call_tool(request_context, params):
            name = params.get("name") if isinstance(params, dict) else getattr(params, "name", None)
            arguments = (
                params.get("arguments") if isinstance(params, dict)
                else getattr(params, "arguments", None)
            )
            official_auth = read_official_auth(request_context=request_context, params=params)
            return types.CallToolResult(content=await call_tool(name, arguments, official_auth))

        server = Server(
            server_name,
            on_list_tools=on_list_tools,
            on_call_tool=on_call_tool,
        )

    async def _main() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    try:
        asyncio.run(_main())
    finally:
        executor.shutdown(wait=False)
