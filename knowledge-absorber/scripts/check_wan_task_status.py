#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025-2026 The Alibaba Wan Team Authors. All rights reserved.

"""
check_wan_task_status -  Query the status and final result of a DashScope API asynchronous task using the task_id.
"""

import os
import sys
import argparse
import requests


def _check_wan_task_status(task_id: str, headers: dict[str, str]) -> str:
    """Check task status until completion"""

    dashscope_base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/api/v1/")
    check_url = f"{dashscope_base_url}tasks/{task_id}"
    
    check_response = requests.get(check_url, headers=headers)
    if check_response.status_code != 200:
        try:
            error_data = check_response.json()
            error_message = error_data.get(
                "error", f"HTTP {check_response.status_code}")
        except Exception:
            error_message = f"HTTP {check_response.status_code}"
        raise Exception(
            f"poll Dashscope failed: {error_message}")
    
    check_res = check_response.json()
    status = check_res.get("output", {}).get("task_status")
    if status == "SUCCEEDED":
        output = check_res.get("output", {}).get("choices", [])[0].get("message", None).get("content", None)
        if output and isinstance(output, list):
            return {"status": status, "content": output}
        else:
            raise Exception(
                "No image URL found in successful response")
    elif status == "RUNNING":
        return {"status": status, "content": []}
    elif status == "FAILED":
        failed_code = check_res.get("output", {}).get("code", "")
        failed_message = check_res.get("output", {}).get("message", "")
        detail_error = f"Task failed with code: {failed_code}  message: {failed_message}"
        raise Exception(
            f"Dashscope image generation failed: {detail_error}")
    raise Exception(f"Task polling failed with final status: {status}")


def main():
    parser = argparse.ArgumentParser(description="Query the status and final result of a DashScope API asynchronous task using the task_id")
    parser.add_argument("--task_id", type=str, required=True, help="The task_id used for querying")
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
    
    check_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
    }

    try:
        check_rst = _check_wan_task_status(task_id = args.task_id, headers = check_headers)
        status = check_rst["status"]
        content = check_rst["content"]
        
        if status == "SUCCEEDED":
            for rst_idx, rst_item in enumerate(content):
                rst_type = rst_item.get('type', '')
                if rst_type == 'image':
                    print(f'result No. {rst_idx+1}', rst_item['image'])
            print("\n🎉 Generation successful!")
        elif status == "RUNNING":
            print(f"\nStill running! This is an asynchronous generation task. You can later query its status using task_id: {args.task_id}.")
        
            
    except KeyboardInterrupt:
        print("\n\n⚠️  User interrupted the operation")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Program execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
