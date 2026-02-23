#!/usr/bin/env python3
"""
Gemai API Image Generator - 基于 OpenAI 格式的文生图工具
API 提供商: Gemai 公益站 (https://api.gemai.cc)
模型: gemini-3-pro-image-preview
"""

import requests
import json
import base64
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
import argparse


class GemaiImageGenerator:
    """Gemai API 文生图生成器（OpenAI 标准格式）"""

    def __init__(self, api_key: str, base_url: str = "https://api.gemai.cc"):
        """
        初始化生成器

        Args:
            api_key: API 密钥
            base_url: API 基础地址
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = "gemini-3-pro-image-preview"
        self.endpoint = f"{self.base_url}/v1/chat/completions"

    def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        output_path: Optional[str] = None,
        num_images: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成图片（支持批量生成）

        Args:
            prompt: 图片描述文本（正向提示词）
            negative_prompt: 负向提示词（不想要的内容）
            output_path: 输出文件路径（可选）
            num_images: 生成图片数量（1-4，默认1）
            **kwargs: 其他参数
                - temperature: 创造性程度 0.0-1.0（默认0.7）
                - max_tokens: 最大令牌数（默认4096）
                - aspect_ratio: 宽高比，如 "16:9", "1:1", "9:16", "4:3", "3:4"
                - style: 图片风格，如 "realistic", "anime", "oil-painting", "watercolor", "sketch"

        Returns:
            包含生成结果的字典
        """
        # 限制生成数量
        num_images = max(1, min(num_images, 4))

        # 构建完整的提示词
        full_prompt = prompt

        # 添加风格参数到提示词
        if "style" in kwargs and kwargs["style"]:
            style_map = {
                "realistic": "photorealistic style",
                "anime": "anime style",
                "oil-painting": "oil painting style",
                "watercolor": "watercolor painting style",
                "sketch": "sketch drawing style"
            }
            style_text = style_map.get(kwargs["style"], kwargs["style"])
            full_prompt = f"{prompt}, {style_text}"

        # 添加宽高比参数到提示词
        if "aspect_ratio" in kwargs and kwargs["aspect_ratio"]:
            full_prompt = f"{full_prompt}, aspect ratio {kwargs['aspect_ratio']}"

        # 添加负向提示词
        if negative_prompt:
            full_prompt = f"{full_prompt}\n\nNegative prompt: {negative_prompt}"

        # 构建 OpenAI 标准格式的请求体
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        # 添加 n 参数（生成多张图片）
        if num_images > 1:
            payload["n"] = num_images
            print(f"🔢 请求生成 {num_images} 张图片")

        # 请求头（OpenAI 标准格式）
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            print(f"🚀 正在调用 Gemai API: {self.endpoint}")
            print(f"🤖 使用模型: {self.model}")
            print(f"📝 提示词: {prompt}")
            if negative_prompt:
                print(f"🚫 负向提示词: {negative_prompt}")
            if "style" in kwargs and kwargs["style"]:
                print(f"🎨 风格: {kwargs['style']}")
            if "aspect_ratio" in kwargs and kwargs["aspect_ratio"]:
                print(f"📐 宽高比: {kwargs['aspect_ratio']}")

            # 发送请求
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=120  # 图片生成可能需要较长时间
            )

            # 检查响应
            print(f"📡 响应状态码: {response.status_code}")
            response.raise_for_status()

            result = response.json()

            # 调试：打印响应结构
            print(f"🔍 响应顶级字段: {list(result.keys())}")

            # 解析响应并保存图片
            if output_path:
                self._save_images(result, output_path, prompt)

            print("✅ 图片生成成功！")
            return result

        except requests.exceptions.RequestException as e:
            print(f"❌ API 请求失败: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"错误详情: {e.response.text}")
            raise

    def _save_images(self, result: Dict[str, Any], output_path: str, prompt: str):
        """
        保存生成的图片（支持多图）

        Args:
            result: API 响应结果
            output_path: 输出路径
            prompt: 原始提示词（用于文件命名）
        """
        try:
            images = []

            print(f"🔍 解析 API 响应...")

            # OpenAI 标准格式: choices -> message -> content
            if "choices" in result:
                print(f"📌 检测到 OpenAI 标准格式，共 {len(result['choices'])} 个选择")

                for choice_idx, choice in enumerate(result["choices"]):
                    print(f"\n处理第 {choice_idx + 1} 个选择...")

                    message = choice.get("message", {})
                    content = message.get("content", "")

                    # 检查 content 类型
                    if isinstance(content, str):
                        print(f"   → content 是字符串，长度: {len(content)}")

                        # 方式1: 尝试从 Markdown 格式提取图片
                        # 格式: ![image](data:image/png;base64,BASE64_DATA)
                        markdown_pattern = r'!\[.*?\]\(data:image/([^;]+);base64,([^)]+)\)'
                        matches = re.findall(markdown_pattern, content)

                        if matches:
                            print(f"   → 找到 {len(matches)} 个 Markdown 格式的图片")
                            for idx, (image_format, base64_data) in enumerate(matches):
                                print(f"   → 图片 {idx + 1}: {image_format} 格式")
                                images.append({
                                    'format': image_format,
                                    'data': base64_data.strip(),
                                    'source': f'choice_{choice_idx + 1}_markdown_{idx + 1}'
                                })
                        else:
                            # 方式2: 尝试直接匹配 data URL
                            data_url_pattern = r'data:image/([^;]+);base64,([A-Za-z0-9+/=\n\r]+)'
                            matches = re.findall(data_url_pattern, content, re.DOTALL)

                            if matches:
                                print(f"   → 找到 {len(matches)} 个 data URL 格式的图片")
                                for idx, (image_format, base64_data) in enumerate(matches):
                                    # 清理 base64 数据中的换行符
                                    clean_data = base64_data.replace('\n', '').replace('\r', '').strip()
                                    print(f"   → 图片 {idx + 1}: {image_format} 格式")
                                    images.append({
                                        'format': image_format,
                                        'data': clean_data,
                                        'source': f'choice_{choice_idx + 1}_dataurl_{idx + 1}'
                                    })
                            else:
                                # 方式3: 尝试 JSON 解析（有些 API 返回 JSON 字符串）
                                try:
                                    content_json = json.loads(content)
                                    if isinstance(content_json, dict):
                                        if "image" in content_json:
                                            images.append({
                                                'format': 'png',
                                                'data': content_json["image"],
                                                'source': f'choice_{choice_idx + 1}_json_image'
                                            })
                                            print(f"   → 找到 JSON 格式的图片（image 字段）")
                                        elif "data" in content_json:
                                            images.append({
                                                'format': 'png',
                                                'data': content_json["data"],
                                                'source': f'choice_{choice_idx + 1}_json_data'
                                            })
                                            print(f"   → 找到 JSON 格式的图片（data 字段）")
                                    elif isinstance(content_json, list):
                                        # 处理 JSON 数组
                                        for idx, item in enumerate(content_json):
                                            if isinstance(item, dict):
                                                if "image" in item:
                                                    images.append({
                                                        'format': 'png',
                                                        'data': item["image"],
                                                        'source': f'choice_{choice_idx + 1}_json_array_{idx + 1}'
                                                    })
                                                elif "data" in item:
                                                    images.append({
                                                        'format': 'png',
                                                        'data': item["data"],
                                                        'source': f'choice_{choice_idx + 1}_json_array_{idx + 1}'
                                                    })
                                        print(f"   → 找到 JSON 数组格式，共 {len(content_json)} 个图片")
                                except json.JSONDecodeError:
                                    print(f"   → content 不是 JSON 格式")
                                    # 保存原始内容供调试
                                    print(f"   → content 预览: {content[:200]}...")

                    # 如果 content 是列表或字典（某些 API 可能这样返回）
                    elif isinstance(content, (list, dict)):
                        print(f"   → content 是 {type(content).__name__} 类型")
                        # 尝试提取图片数据
                        if isinstance(content, dict):
                            if "image" in content:
                                images.append({
                                    'format': 'png',
                                    'data': content["image"],
                                    'source': f'choice_{choice_idx + 1}_dict_image'
                                })
                            elif "data" in content:
                                images.append({
                                    'format': 'png',
                                    'data': content["data"],
                                    'source': f'choice_{choice_idx + 1}_dict_data'
                                })
                        elif isinstance(content, list):
                            # 处理列表格式
                            for idx, item in enumerate(content):
                                if isinstance(item, dict):
                                    if "image" in item:
                                        images.append({
                                            'format': 'png',
                                            'data': item["image"],
                                            'source': f'choice_{choice_idx + 1}_list_{idx + 1}'
                                        })
                                    elif "data" in item:
                                        images.append({
                                            'format': 'png',
                                            'data': item["data"],
                                            'source': f'choice_{choice_idx + 1}_list_{idx + 1}'
                                        })

            # 如果没有找到图片，保存原始响应供调试
            if not images:
                print("⚠️  未找到图片数据，保存原始响应供调试...")
                output_file = Path(output_path).with_suffix('.json')
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"📄 原始响应已保存至: {output_file}")
                print(f"💡 提示: 请检查 {output_file} 文件以确定正确的响应格式")
                return

            print(f"\n✓ 找到 {len(images)} 个图片数据")

            # 保存图片
            saved_count = 0
            for idx, image_info in enumerate(images):
                print(f"\n处理第 {idx + 1}/{len(images)} 个图片...")
                print(f"   来源: {image_info.get('source', 'unknown')}")

                image_data = image_info['data']
                image_format = image_info.get('format', 'png')

                try:
                    # 解码 base64
                    image_bytes = base64.b64decode(image_data)
                    print(f"   → 解码后大小: {len(image_bytes)} 字节 ({len(image_bytes)/1024:.2f} KB)")

                    # 生成文件名
                    base_path = Path(output_path)
                    if len(images) > 1:
                        # 多图时添加序号
                        filename = f"{base_path.stem}_{idx + 1}.{image_format}"
                    else:
                        # 单图时使用原始文件名或添加扩展名
                        if base_path.suffix:
                            filename = str(base_path)
                        else:
                            filename = f"{base_path.stem}.{image_format}"

                    # 保存文件
                    with open(filename, 'wb') as f:
                        f.write(image_bytes)

                    print(f"   ✅ 图片已保存: {filename}")
                    saved_count += 1

                except Exception as e:
                    print(f"   ❌ 保存图片失败: {e}")
                    # 保存原始数据供调试
                    debug_file = f"{Path(output_path).stem}_debug_{idx + 1}.txt"
                    with open(debug_file, 'w') as f:
                        f.write(image_data[:1000])  # 只保存前1000字符
                    print(f"   → 前 1000 字符已保存至: {debug_file}")

            print(f"\n📊 成功保存 {saved_count}/{len(images)} 张图片")

        except Exception as e:
            print(f"⚠️  保存图片时出错: {e}")
            print("尝试保存原始响应...")
            output_file = Path(output_path).with_suffix('.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"📄 原始响应已保存至: {output_file}")


def main():
    """命令行主函数"""
    parser = argparse.ArgumentParser(
        description="Gemai API 文生图工具（OpenAI 标准格式）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基础使用
  python gemai_image_generator.py --prompt "一只可爱的猫咪"

  # 指定输出文件
  python gemai_image_generator.py --prompt "夕阳下的城市" -o sunset.png

  # 使用负向提示词
  python gemai_image_generator.py --prompt "森林" --negative "dark, scary"

  # 生成多张图片
  python gemai_image_generator.py --prompt "太空站" --num-images 3 -o space.png

  # 调整创造力参数
  python gemai_image_generator.py --prompt "武士" --temperature 0.9

  # 指定风格和宽高比
  python gemai_image_generator.py --prompt "武士" --style anime --aspect-ratio 16:9

  # 完整示例
  python gemai_image_generator.py --prompt "美丽的樱花" --negative "blurry" --num-images 2 --temperature 0.8 --style watercolor --aspect-ratio 16:9 -o sakura.png
        """
    )

    parser.add_argument(
        "--api-key",
        default=None,
        help="API 密钥（也可通过环境变量 GEMAI_API_KEY 设置）"
    )

    parser.add_argument(
        "--prompt",
        "-p",
        required=True,
        help="图片描述文本（正向提示词）"
    )

    parser.add_argument(
        "--negative",
        "-n",
        help="负向提示词（不想要的内容）"
    )

    parser.add_argument(
        "--output",
        "-o",
        default="output.png",
        help="输出文件路径（默认: output.png）"
    )

    parser.add_argument(
        "--num-images",
        type=int,
        default=1,
        help="生成图片数量 1-4（默认: 1）"
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="创造性程度 0.0-1.0（默认: 0.7）"
    )

    parser.add_argument(
        "--aspect-ratio",
        choices=["1:1", "16:9", "9:16", "4:3", "3:4"],
        help="宽高比"
    )

    parser.add_argument(
        "--style",
        choices=["realistic", "anime", "oil-painting", "watercolor", "sketch"],
        help="图片风格"
    )

    parser.add_argument(
        "--base-url",
        default="https://api.gemai.cc",
        help="API 基础地址（默认: https://api.gemai.cc）"
    )

    args = parser.parse_args()

    # 解析 API Key: 命令行参数 > 环境变量
    api_key = args.api_key or os.environ.get("GEMAI_API_KEY")
    if not api_key:
        parser.error("请通过 --api-key 参数或环境变量 GEMAI_API_KEY 提供 API 密钥")

    # 创建生成器
    generator = GemaiImageGenerator(api_key=api_key, base_url=args.base_url)

    # 准备参数
    kwargs = {
        "temperature": args.temperature
    }

    if args.aspect_ratio:
        kwargs["aspect_ratio"] = args.aspect_ratio
    if args.style:
        kwargs["style"] = args.style

    # 生成图片
    try:
        result = generator.generate_image(
            prompt=args.prompt,
            negative_prompt=args.negative,
            output_path=args.output,
            num_images=args.num_images,
            **kwargs
        )

        print("\n" + "="*50)
        print("📊 生成统计:")
        print(f"   模型: {generator.model}")
        print(f"   提示词: {args.prompt}")
        if args.negative:
            print(f"   负向提示词: {args.negative}")
        if args.num_images > 1:
            print(f"   生成数量: {args.num_images}")
        if args.style:
            print(f"   风格: {args.style}")
        if args.aspect_ratio:
            print(f"   宽高比: {args.aspect_ratio}")
        print(f"   输出文件: {args.output}")
        print("="*50)

        return 0

    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())