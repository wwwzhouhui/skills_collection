#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2025-2026 The Alibaba Wan Team Authors. All rights reserved.

"""
File Upload to OSS - File Upload Utility

Upload local files or base64-encoded image data to the temporary OSS storage and obtain an oss:// URL.

Use Cases:
- Uploading reference images for image-to-image generation, image editing, or image series generation
- Any scenario requiring local files or base64-encoded data as model input

Usage:
    # Method 1: Upload from a file path
    python file_to_oss.py --file /path/to/image.jpg --model wan2.7-image
    
    # Method 2: Upload from base64 data
    python file_to_oss.py --base64 "<base64_data>" --model wan2.7-image

Example Output:
    oss://dashscope-instant/xxx/2024-07-18/xxx/cat.png

Environment Variable:
    DASHSCOPE_API_KEY: Required - your Alibaba Cloud DashScope API Key
"""

import os
import sys
import base64
import requests
from pathlib import Path
import argparse


def upload_file_to_oss(api_key: str, model_name: str, file_path: str = None, 
                       base64_data: str = None, filename: str = None) -> str:
    """
    Upload a file to temporary OSS storage
    
    Args:
        api_key: Alibaba Cloud DashScope API Key
        model_name: Model name (e.g., wan2.7-image)
        file_path: Local file path (mutually exclusive with base64_data)
        base64_data: Base64-encoded image data (mutually exclusive with file_path)
        filename: Filename to use when uploading via base64_data (default: image.png)
        
    Returns:
        A temporary URL in oss:// format
        
    Raises:
        ValueError: If neither file_path nor base64_data is provided
        FileNotFoundError: If the specified file does not exist
        Exception: If the upload fails
    """
    
    if not file_path and not base64_data:
        raise ValueError("Either file_path or base64_data must be provided")
    if file_path and base64_data:
        raise ValueError("Only one of file_path or base64_data may be provided")
    

    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(file_path, 'rb') as f:
            file_content = f.read()
        file_name = Path(file_path).name
    else:
        try:
            if ',' in base64_data:
                base64_data = base64_data.split(',', 1)[1]
            file_content = base64.b64decode(base64_data)
        except Exception as e:
            raise Exception(f"Base64 decoding failed: {e}")
        file_name = filename or "image.png"


    upload_url = "https://dashscope.aliyuncs.com/api/v1/uploads"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "action": "getPolicy",
        "model": model_name
    }
    
    try:
        response = requests.get(upload_url, headers=headers, params=params)
        if response.status_code != 200:
            raise ValueError(f"Failed to get upload policy: {response.text}")
        
        policy_data = response.json()['data']
    except Exception as e:
        raise Exception(f"Failed to obtain upload credentials: {e}")
    
    
    key = f"{policy_data['upload_dir']}/{file_name}"
    
    files = {
        'OSSAccessKeyId': (None, policy_data['oss_access_key_id']),
        'Signature': (None, policy_data['signature']),
        'policy': (None, policy_data['policy']),
        'x-oss-object-acl': (None, policy_data['x_oss_object_acl']),
        'x-oss-forbid-overwrite': (None, policy_data['x_oss_forbid_overwrite']),
        'key': (None, key),
        'success_action_status': (None, '200'),
        'file': (file_name, file_content)
    }
    
    try:
        response = requests.post(policy_data['upload_host'], files=files)
        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.text}")
    except Exception as e:
        raise Exception(f"File upload failed: {e}")
    
    return f"oss://{key}"


def main():
    parser = argparse.ArgumentParser(
        description='OSS File Upload Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  # Method 1: Upload from a file path
  python file_to_oss.py --file /path/to/image.jpg --model wan2.7-image
  
  # Method 2: Upload from base64 data
  python file_to_oss.py --base64 "<base64_data>" --model wan2.7-image
        """
    )
    
    parser.add_argument('--file', '-f', help='Local file path (mutually exclusive with base64_data)')
    parser.add_argument('--base64', '-b', help='Base64-encoded image data (mutually exclusive with file_path)')
    parser.add_argument('--model', '-m', required=True, help='Model name (e.g., wan2.7-image)')
    parser.add_argument('--filename', help='Filename to use when uploading via base64_data (default: image.png)')
    
    args = parser.parse_args()


    if not args.file and not args.base64:
        print("❌ Error: Please provide one of --file, --base64")
        print("   Use --help to view help information.")
        sys.exit(1)
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ Error: DASHSCOPE_API_KEY is not set")
        print("Please set the environment variable: ")
        print("If using bash")
        print("echo 'export DASHSCOPE_API_KEY=\"your-api-key-here\"' >> ~/.bashrc && source ~/.bashrc")
        print("If using zsh")
        print("echo 'export DASHSCOPE_API_KEY=\"your-api-key-here\"' >> ~/.zshrc && source ~/.zshrc")
        sys.exit(1)
    
    try:
        if args.base64:
            oss_url = upload_file_to_oss(api_key, args.model, base64_data=args.base64, 
                                        filename=args.filename)
        else:
            oss_url = upload_file_to_oss(api_key, args.model, file_path=args.file)
        
        print(oss_url)
    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
