#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插图去底: 把生成插图的纯色背景变成透明, 视频换背景也能直接兼容

原理: 从图片四边采样背景色, 泛洪填充(BFS)只抠掉**与边缘连通**的背景色区域。
气泡内部/卡片内部的白色不与边缘连通, 不会被误伤。比抠图模型(u2net)更可控,
不会把插图里的散落元素当背景抠掉。

用法:
    python3 strip_background.py <images_dir> [--tolerance 22] [--feather]
    python3 strip_background.py ch-01.png [--tolerance 22]

    images_dir: 处理目录下所有 *.png (跳过已透明的)。原图备份到 <dir>/raw/。
    --tolerance: 与背景色的每通道容差 (默认 22; 背景有噪点/纹理时调大)
    --feather:   对 alpha 边缘做 1px 柔化 (默认开)

依赖: Pillow (pip install pillow)
"""

import argparse
import sys
from collections import deque
from pathlib import Path

try:
    from PIL import Image, ImageFilter
except ImportError:
    print("❌ 需要 Pillow: pip install pillow", file=sys.stderr)
    sys.exit(1)


def sample_bg_color(px, w, h):
    """采样四边中点 + 四角共 8 个点的中位色作为背景色"""
    pts = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
           (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]
    samples = [px[x, y][:3] for x, y in pts]
    med = tuple(sorted(c[i] for c in samples)[len(samples) // 2] for i in range(3))
    return med


def strip_one(path: Path, tolerance: int, feather: bool) -> bool:
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    px = img.load()

    # 已经有透明像素的跳过 (避免重复处理)
    if any(px[x, y][3] < 250 for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]):
        print(f"   ⤷ {path.name} 边缘已透明, 跳过")
        return False

    bg = sample_bg_color(px, w, h)

    def is_bg(x, y):
        r, g, b, a = px[x, y]
        return (abs(r - bg[0]) <= tolerance and abs(g - bg[1]) <= tolerance
                and abs(b - bg[2]) <= tolerance)

    # BFS 泛洪: 从四边所有背景色像素起步
    mask = bytearray(w * h)   # 1 = 透明化
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_bg(x, y) and not mask[y * w + x]:
                mask[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_bg(x, y) and not mask[y * w + x]:
                mask[y * w + x] = 1
                q.append((x, y))

    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not mask[ny * w + nx] and is_bg(nx, ny):
                mask[ny * w + nx] = 1
                q.append((nx, ny))

    alpha = Image.frombytes("L", (w, h), bytes(255 - m * 255 for m in mask))
    if feather:
        alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))
    img.putalpha(alpha)
    img.save(path)

    removed = sum(mask) * 100 // (w * h)
    print(f"   ✓ {path.name} 抠掉 {removed}% 背景 (bg≈#{bg[0]:02X}{bg[1]:02X}{bg[2]:02X})")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="图片目录或单个 png")
    ap.add_argument("--tolerance", type=int, default=22)
    ap.add_argument("--no-feather", action="store_true")
    args = ap.parse_args()

    target = Path(args.target)
    if target.is_file():
        files = [target]
        backup_dir = target.parent / "raw"
    elif target.is_dir():
        files = sorted(p for p in target.glob("*.png"))
        backup_dir = target / "raw"
    else:
        print(f"❌ 找不到 {target}", file=sys.stderr)
        sys.exit(1)

    if not files:
        print("❌ 没有 png 文件", file=sys.stderr)
        sys.exit(1)

    backup_dir.mkdir(exist_ok=True)
    n = 0
    for f in files:
        bak = backup_dir / f.name
        if not bak.exists():
            bak.write_bytes(f.read_bytes())
        if strip_one(f, args.tolerance, not args.no_feather):
            n += 1
    print(f"✅ 处理 {n}/{len(files)} 张 (原图备份在 {backup_dir}/)")


if __name__ == "__main__":
    main()
