#!/usr/bin/env python3
"""
腾讯云 COS 图片上传工具

功能：
- 上传图片到腾讯云 COS
- 自动生成符合小灰灰公众号规范的文件名（image-YYYYMMDD-HHMMSS）
- 返回完整的 COS URL

依赖：
pip install cos-python-sdk-v5 python-dotenv

使用方法：
python upload_to_cos.py <image_path> [--name custom-name]

配置：
在项目根目录创建 .env 文件，包含以下配置：
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
COS_BUCKET=your-bucket
COS_REGION=your-region
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import argparse

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 从脚本所在目录向上查找 .env 文件
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_path = project_root / '.env'

    # 如果项目根目录没有 .env，尝试当前工作目录
    if not env_path.exists():
        env_path = Path.cwd() / '.env'

    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    print("⚠️  警告: python-dotenv 未安装，将只使用环境变量")
    print("   安装: pip install python-dotenv")

# 从环境变量读取 COS 配置
COS_SECRET_ID = os.environ.get('COS_SECRET_ID')
COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY')
COS_BUCKET = os.environ.get('COS_BUCKET')
COS_REGION = os.environ.get('COS_REGION')

# 验证必需的配置
def validate_config():
    """验证 COS 配置是否完整"""
    missing = []
    if not COS_SECRET_ID:
        missing.append('COS_SECRET_ID')
    if not COS_SECRET_KEY:
        missing.append('COS_SECRET_KEY')
    if not COS_BUCKET:
        missing.append('COS_BUCKET')
    if not COS_REGION:
        missing.append('COS_REGION')

    if missing:
        print("❌ 错误: 缺少必需的 COS 配置", file=sys.stderr)
        print(f"\n缺少的配置项: {', '.join(missing)}", file=sys.stderr)
        print("\n请在项目根目录创建 .env 文件，包含以下配置:", file=sys.stderr)
        print("COS_SECRET_ID=your-secret-id", file=sys.stderr)
        print("COS_SECRET_KEY=your-secret-key", file=sys.stderr)
        print("COS_BUCKET=your-bucket", file=sys.stderr)
        print("COS_REGION=your-region", file=sys.stderr)
        print("\n或者设置对应的环境变量。", file=sys.stderr)
        sys.exit(1)

def init_cos_client():
    """初始化 COS 客户端"""
    config = CosConfig(
        Region=COS_REGION,
        SecretId=COS_SECRET_ID,
        SecretKey=COS_SECRET_KEY
    )
    client = CosS3Client(config)
    return client

def generate_filename(original_path=None, custom_name=None):
    """
    生成符合规范的文件名
    格式：image-YYYYMMDD-HHMMSS.extension
    """
    if custom_name:
        # 如果提供了自定义名称，使用它
        if '.' in custom_name:
            return custom_name
        else:
            # 如果没有扩展名，从原始文件获取
            ext = os.path.splitext(original_path)[1] if original_path else '.png'
            return f"{custom_name}{ext}"

    # 生成基于时间戳的文件名
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    ext = os.path.splitext(original_path)[1] if original_path else '.png'
    return f"image-{timestamp}{ext}"

def upload_image(image_path, custom_name=None):
    """
    上传图片到 COS

    Args:
        image_path: 本地图片路径
        custom_name: 自定义文件名（可选）

    Returns:
        str: 完整的 COS URL
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    # 初始化客户端
    client = init_cos_client()

    # 生成文件名
    filename = generate_filename(image_path, custom_name)

    # 上传文件
    try:
        with open(image_path, 'rb') as fp:
            response = client.put_object(
                Bucket=COS_BUCKET,
                Body=fp,
                Key=filename,
                EnableMD5=False
            )

        # 构建完整 URL
        url = f"https://{COS_BUCKET}.cos.{COS_REGION}.myqcloud.com/{filename}"
        return url

    except Exception as e:
        raise Exception(f"上传失败: {str(e)}")

def main():
    # 首先验证配置
    validate_config()

    parser = argparse.ArgumentParser(description='上传图片到腾讯云 COS')
    parser.add_argument('image_path', help='本地图片路径')
    parser.add_argument('--name', help='自定义文件名（可选）', default=None)
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式，只输出 URL')

    args = parser.parse_args()

    try:
        url = upload_image(args.image_path, args.name)

        if args.quiet:
            print(url)
        else:
            print(f"✅ 上传成功!")
            print(f"📁 文件: {os.path.basename(args.image_path)}")
            print(f"🔗 URL: {url}")
            print(f"\nMarkdown 格式:")
            print(f"![image]({url})")

        return 0

    except Exception as e:
        if not args.quiet:
            print(f"❌ 错误: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
