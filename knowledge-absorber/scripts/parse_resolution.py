#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025-2026 The Alibaba Wan Team Authors. All rights reserved.

"""
Resolution Parser for Wan 2.7 Image Generation

Parses the user-provided resolution description and converts it into the size parameter required by the API

Usage Examples:
    python parse_resolution.py "2K 3:4"
    python parse_resolution.py "1K 16:9"
    python parse_resolution.py "2048*2048"
    python parse_resolution.py "1K"

Output:
    1536*2048
    1696*960
    2048*2048
    1024*1024

K + aspect ratio format syntax:
`{K value} {width}:{height}`
| input | output | description |
|------|------|------|
| `1K 1:1` | 1024*1024 | 1K square |
| `1K 3:4` | 896*1194 | Portrait orientation |
| `1K 4:3` | 1194*896 | Landscape orientation |
| `1K 16:9` | 1364*768 | Widescreen |
| `1K 9:16` | 768*1364 | Mobile portrait |
| `2K 3:4` | 1774*2364 | 2K portrait |
| `2K 16:9` | 2730*1536 | 2K widescreen |
| `2K 1:1` | 2048*2048 | 2K square |
"""

import re
import sys
import argparse


def parse_resolution(input_str):
    """
    Parse resolution input string
    
    Args:
        input_str: User input supports the following formats:
            - "2K 3:4", "1K 16:9" (K + aspect ratio)
            - "2K", "1K" (Only K value, default 1:1)
            - "1280*1280", "2048*2048" (Directly specify resolution size, using * as the separator)
            - "1280x1280" (Directly specify resolution size, using x as the separator)
    
    Returns:
        str: Formatted resolution size string, e.g., "1536*2048"
    
    Raises:
        ValueError: Invalid input format or out of range
    """
    
    input_str = input_str.strip().lower()
    
    # Mode 1: Directly specify resolution size (e.g., "1280*1280" or "1280x1280")
    direct_pattern = r'^(\d+)[*x](\d+)$'
    match = re.match(direct_pattern, input_str)
    if match:
        width = int(match.group(1))
        height = int(match.group(2))
        
        if not (768*768 <= width * height <= 2048*2048):
            raise ValueError(f"Total pixel count must be within the range [768*768, 2048*2048], i.e., [{768*768}, {2048*2048}]. Current: {width}*{height}: {width*height}")
        
        aspect_ratio = width / height
        if not (1/8 <= aspect_ratio <= 8):
            raise ValueError(f"Aspect ratio must be within the range [1:8, 8:1]. Current: {aspect_ratio:.2f}")
        
        return f"{width}*{height}"
    
    # Mode 2: K + aspect ratio (e.g., "2K 3:4", "1K 16:9")
    k_ratio_pattern = r'^([124])k\s*(\d+):(\d+)$'
    match = re.match(k_ratio_pattern, input_str)
    if match:
        k_value = int(match.group(1))
        ratio_w = int(match.group(2))
        ratio_h = int(match.group(3))
        
        
        total_pixels = min(max((k_value * 1024) ** 2, 1024*1024), 2048*2048)
        base_unit = (total_pixels / (ratio_w * ratio_h)) ** 0.5
        width = int(round(base_unit * ratio_w))
        height = int(round(base_unit * ratio_h))

        # Ensure it is even (required by some models)
        width = width if width % 2 == 0 else width - 1
        height = height if height % 2 == 0 else height - 1

        if not (768*768 <= width * height <= 2048*2048):
            raise ValueError(f"Total pixel count must be within the range [768*768, 2048*2048], i.e., [{768*768}, {2048*2048}]. Calculated resolution is out of range: {width}*{height}: {width*height}")
        
        aspect_ratio = width / height
        if not (1/8 <= aspect_ratio <= 8):
            raise ValueError(f"Aspect ratio must be within the range [1:8, 8:1]. Current: {aspect_ratio:.2f}")
        
        return f"{width}*{height}"
    
    # Mode 3: K value only (e.g., "1K", "2K"), defaulting to a 1:1 aspect ratio
    k_only_pattern = r'^([12])k$'
    match = re.match(k_only_pattern, input_str)
    if match:
        k_value = int(match.group(1))
        size = k_value * 1024
        return f"{size}*{size}"


    raise ValueError(
        f"Unsupported input format: '{input_str}'\n"
        f"Supported input formats: \n"
        f"  - K + aspect ratio: '2K 3:4', '1K 16:9', '2K 1:1'\n"
        f"  - K value only: '1K', '2K' (defaulting to a 1:1 aspect ratio)\n"
        f"  - Directly specify resolution size: '1280*1280', '2048*2048'"
    )


def main():
    parser = argparse.ArgumentParser(
        description='Parses resolution strings, supporting K value format or specific pixel formats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Example:
  python parse_resolution.py '2K 3:4'       # output: 1536*2048
  python parse_resolution.py '1K 16:9'      # output: 1696*960  
  python parse_resolution.py '2048*2048'    # output: 2048*2048
  python parse_resolution.py '1K'           # output: 1024*1024
        '''.strip()
    )
    
    parser.add_argument(
        'input',
        help='Resolution input string, format like: "2K 3:4", "2048*2048", "1K"'
    )
    
    args = parser.parse_args()
    input_str = args.input
    
    try:
        result = parse_resolution(input_str)
        print(result)
    except ValueError as e:
        print(f"Failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
