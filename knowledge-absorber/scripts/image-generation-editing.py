#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025-2026 The Alibaba Wan Team Authors. All rights reserved.

"""
image-generation-editing - Use the DashScope API for image generation, image editing, and image series generation.
"""

import os
import sys
import argparse
import requests
import time


def _poll_wan_task_status(task_id: str, headers: dict[str, str]) -> str:
    """Poll task status until completion"""

    dashscope_base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1/")
    check_url = f"{dashscope_base_url}tasks/{task_id}"
    
    status = "PENDING"
    check_count = 0
    while status not in ("SUCCEEDED", "FAILED", "CANCELLED"):
        if check_count >= 15:
            return {"status": status, "content": []}
        print(
            f"Polling Dashscope generation {task_id}, current status: {status} ...")
        time.sleep(3)  # Wait 3 seconds between polls
        poll_response = requests.get(check_url, headers=headers)
        if poll_response.status_code != 200:
            try:
                error_data = poll_response.json()
                error_message = error_data.get(
                    "error", f"HTTP {poll_response.status_code}")
            except Exception:
                error_message = f"HTTP {poll_response.status_code}"
            raise Exception(
                f"poll Dashscope failed: {error_message}")
        
        poll_res = poll_response.json()
        status = poll_res.get("output", {}).get("task_status")
        if status == "SUCCEEDED":
            output = poll_res.get("output", {}).get("choices", [])[0].get("message", None).get("content", None)
            if output and isinstance(output, list):
                return {"status": status, "content": output}
            else:
                raise Exception(
                    "No image URL found in successful response")
        elif status == "FAILED":
            failed_code = poll_res.get("output", {}).get("code", "")
            failed_message = poll_res.get("output", {}).get("message", "")
            detail_error = f"Task failed with code: {failed_code}  message: {failed_message}"
            raise Exception(
                f"Dashscope image generation failed: {detail_error}")
        check_count += 1
    raise Exception(f"Task polling failed with final status: {status}")
    

def generate(user_requirement: str, input_images: list[str] = [], n: int = 1, size: str = '1K', enable_sequential: bool = False):
    """
    Use the DashScope API for image generation, image editing, and image series generation

    Args:
        user_requirement: User's requirements for image generation, image editing, and image series generation
        input_images: Input reference image
        n: Number of images to generate
        size: Resolution of the generated image
        enable_sequential: Whether to enable image series generation
        
    Returns:
        dict: A result dictionary containing fields such as "success" and "content"
    """

    try:
        api_key = os.environ.get("DASHSCOPE_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "API key not provided. Set DASHSCOPE_API_KEY environment variable"
            }

        dashscope_base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1/")
        api_url = f"{dashscope_base_url}services/aigc/image-generation/generation"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-DashScope-Async": "enable",
            "X-DashScope-OssResourceResolve": "enable"
        }
        payload = {
            "model": "wan2.7-image",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": f"{user_requirement}"}
                        ]
                    }
                ]
            },
            "parameters": {
                "size": f"{size}",
                "n": n,
                "watermark": False,
                "enable_sequential": enable_sequential
            }
        }
        if input_images:
            for img_url in input_images:
                payload['input']['messages'][0]['content'].append({"image": f"{img_url}"})
        response = requests.post(api_url, headers=headers, json=payload)

        # post request
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get(
                    "error", f"HTTP {response.status_code}")
            except Exception:
                error_message = f"HTTP {response.status_code}"
            raise Exception(
                f"Dashscope task creation failed: {error_message}")
        result = response.json()
        task_id = result.get("output", {}).get("task_id", None)
        print('Dashscope TASK_ID: ', task_id)

        # check results
        check_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        poll_rst = _poll_wan_task_status(task_id, check_headers)
        status = poll_rst['status']
        content = poll_rst['content']
        if status == 'SUCCEEDED':
            for rst_idx, rst_item in enumerate(content):
                rst_type = rst_item.get('type', '')
                if rst_type == 'image':
                    print(f'result No. {rst_idx+1}: ', rst_item['image'])

            return {
                "success": True,
                "content": content,
                "error": ""
            }
        elif status == 'RUNNING':
            return {
                "success": False,
                "content": content,
                "task_id": task_id,
                "error": "still running"
            }

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return {
            "success": False,
            "error": f"Generation failed: {e}"
        }


def main():
    parser = argparse.ArgumentParser(description="Use the DashScope API for image generation, image editing, and image series generation")

    parser.add_argument("--user_requirement", type=str, required=True, help="User's requirements for image generation, image editing, and image series generation")

    parser.add_argument("--input_images", nargs='*', default=[], help="Input reference image")
    parser.add_argument("--n", type=int, default=1, help="Number of images to generate")
    parser.add_argument("--size", type=str, default='1K', help="Resolution of the generated image")
    parser.add_argument("--enable_sequential", action="store_true", help="Whether to enable image series generation")
    
    args = parser.parse_args()
    

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ Error: DASHSCOPE_API_KEY is not set")
        print("Please set the environment variable: ")
        print("If using bash")
        print("echo 'export DASHSCOPE_API_KEY=\"your-api-key-here\"' >> ~/.bashrc && source ~/.bashrc")
        print("If using zsh")
        print("echo 'export DASHSCOPE_API_KEY=\"your-api-key-here\"' >> ~/.zshrc && source ~/.zshrc")
        sys.exit(1)
    
    dashscope_base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1/")
    api_url = f"{dashscope_base_url}services/aigc/image-generation/generation"

    try:
        result = generate(
            user_requirement=args.user_requirement,
            input_images=args.input_images,
            n=args.n,
            size=args.size,
            enable_sequential=args.enable_sequential
        )
        
        if result["success"]:
            print("\n🎉 Generation successful!")
        else:
            if result['error'] == 'still running':
                print(f"\nStill running! This is an asynchronous generation task. You can later query its status using task_id: {result['task_id']}")
            else:
                print(f"\n❌ Generation failed: {result['error']}")
                sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  User interrupted the operation")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Program execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
