#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章获取器 - 下载并解析微信公众号文章

支持链接格式：
- 短链接: https://mp.weixin.qq.com/s/xxxxxxxxxxxxx
- 长链接: https://mp.weixin.qq.com/s?__biz=xxx&mid=xxx&idx=xxx&sn=xxx

用法：
    python fetch_wechat_article.py <url> [--output-dir <目录>] [--no-images] [--no-markdown] [--json]

输出：
    默认保存到 ./wechat_articles/<公众号>/<日期>_<标题>/
    - index.html   : 格式化的文章HTML
    - article.md   : Markdown版本（需要html2text）
    - meta.json    : 文章元数据
    - images/      : 下载的图片（可选）

    使用 --json 参数时，将元数据JSON输出到标准输出，不保存文件。

依赖：
    pip install beautifulsoup4 html2text requests
"""

import sys
import os
import re
import json
import hashlib
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from urllib.parse import urlparse, parse_qs

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False


MOBILE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 '
                  'MicroMessenger/8.0.42(0x18002a2a) NetType/WIFI Language/zh_CN',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://mp.weixin.qq.com/',
}


def is_short_link(url: str) -> bool:
    """判断是否为微信短链接格式"""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.path.startswith('/s/') and len(parsed.path) > 4:
        return True
    if '__biz' in url:
        return False
    return False


def fetch_html(url: str, cookie: str = None) -> Optional[str]:
    """获取文章HTML内容"""
    if not HAS_REQUESTS:
        print("错误: requests 未安装，请运行: pip install requests", file=sys.stderr)
        return None

    headers = dict(MOBILE_HEADERS)
    if cookie:
        headers['Cookie'] = cookie

    try:
        resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        if resp.status_code != 200:
            print(f"错误: HTTP {resp.status_code}", file=sys.stderr)
            return None

        final_url = resp.url
        html_content = resp.text

        # 检测验证码
        if 'wappoc_appmsgcaptcha' in str(final_url) or 'captcha' in str(final_url):
            if not is_short_link(url):
                print("错误: 触发了验证码，请使用短链接格式", file=sys.stderr)
            else:
                print("错误: 检测到验证码页面", file=sys.stderr)
            return None

        if any(kw in html_content for kw in ('访问验证', '安全验证', '环境异常')):
            print("警告: 检测到访问验证页面，内容可能不完整", file=sys.stderr)

        return html_content
    except Exception as e:
        print(f"错误: 获取文章失败: {e}", file=sys.stderr)
        return None


def parse_meta(html_content: str) -> Dict:
    """从HTML中提取文章元数据"""
    if not HAS_BS4:
        return {}

    soup = BeautifulSoup(html_content, 'html.parser')
    meta = {}

    # OG meta 标签
    for prop, key in [
        ('og:title', 'title'),
        ('og:article:author', 'author'),
        ('og:description', 'description'),
        ('og:url', 'url'),
        ('og:image', 'cover_image'),
    ]:
        tag = soup.find('meta', property=prop)
        if tag and tag.get('content'):
            meta[key] = tag['content']

    # 微信专属 meta 标签
    tag = soup.find('meta', property='weixin:account')
    if tag and tag.get('content'):
        meta['account_id'] = tag['content']

    # 从 script 标签中提取
    for script in soup.find_all('script'):
        text = script.string
        if not text:
            continue

        patterns = {
            'title': r'msg_title\s*[:=]\s*["\']([^"\']+)["\']',
            'author': r'msg_author\s*[:=]\s*["\']([^"\']+)["\']',
            'create_time': r'create_time\s*[:=]\s*["\']?(\d+)',
            'account_nickname': r'nickname\s*[:=]\s*["\']([^"\']+)["\']',
            'biz': r'__biz\s*[:=]\s*["\']([^"\']+)["\']',
            'mid': r'mid\s*[:=]\s*["\']?(\d+)',
            'idx': r'idx\s*[:=]\s*["\']?(\d+)',
            'sn': r'sn\s*[:=]\s*["\']([^"\']+)["\']',
        }

        for key, pattern in patterns.items():
            if key not in meta:
                m = re.search(pattern, text)
                if m:
                    val = m.group(1)
                    meta[key] = int(val) if key in ('create_time', 'mid', 'idx') else val

    return meta


def extract_content(html_content: str) -> Optional[object]:
    """提取文章正文内容区域（BeautifulSoup对象）"""
    if not HAS_BS4:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')


def download_images(content_div, images_dir: Path, referer: str) -> int:
    """下载文章中的图片并替换为本地路径，返回下载数量"""
    if not HAS_REQUESTS:
        return 0

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': referer,
    }

    count = 0
    for idx, img in enumerate(content_div.find_all('img')):
        img_url = img.get('data-src') or img.get('src')
        if not img_url or img_url.startswith('data:'):
            continue
        if img_url.startswith('//'):
            img_url = 'https:' + img_url

        # 判断图片扩展名
        ext = '.jpg'
        for e in ('.png', '.gif', '.webp', '.jpeg', '.jpg'):
            if e in img_url.split('?')[0].lower():
                ext = e
                break
        for fmt, e in [('png', '.png'), ('gif', '.gif'), ('jpeg', '.jpg'), ('jpg', '.jpg')]:
            if f'wx_fmt={fmt}' in img_url:
                ext = e
                break

        local_name = f"{idx + 1}{ext}"
        local_path = images_dir / local_name

        try:
            resp = requests.get(img_url, headers=headers, timeout=30)
            if resp.status_code == 200:
                local_path.write_bytes(resp.content)
                img['src'] = f"images/{local_name}"
                if img.get('data-src'):
                    del img['data-src']
                count += 1
        except Exception:
            pass

    return count


def build_html(title: str, content: str, account: str, date_str: str, author: str = '') -> str:
    """构建独立的HTML文档"""
    author_line = f'<span>作者: {author}</span><span> | </span>' if author else ''
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ max-width: 800px; margin: 0 auto; padding: 20px;
               font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
               line-height: 1.8; color: #333; }}
        .article-header {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; }}
        .article-title {{ font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .article-meta {{ color: #999; font-size: 14px; }}
        .article-content img {{ max-width: 100%; height: auto; }}
    </style>
</head>
<body>
    <div class="article-header">
        <h1 class="article-title">{title}</h1>
        <div class="article-meta">
            <span>公众号: {account}</span><span> | </span>
            {author_line}
            <span>日期: {date_str}</span>
        </div>
    </div>
    <div class="article-content">{content}</div>
</body>
</html>"""


def convert_to_markdown(title: str, content_html: str, account: str,
                        date_str: str, author: str = '') -> str:
    """将HTML文章内容转换为Markdown"""
    if not HAS_HTML2TEXT:
        return ''

    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0

    md_body = h.handle(content_html)

    meta_lines = [f"> 公众号: {account}"]
    if author:
        meta_lines.append(f"> 作者: {author}")
    meta_lines.append(f"> 日期: {date_str}")

    return f"# {title}\n\n" + "\n".join(meta_lines) + "\n\n---\n\n" + md_body


def safe_filename(name: str, max_length: int = 50) -> str:
    """生成安全的文件名"""
    safe = re.sub(r'[\\/:*?"<>|]', '', name)
    safe = re.sub(r'\s+', '_', safe)
    return (safe[:max_length] if len(safe) > max_length else safe) or 'untitled'


def fetch_article(url: str, output_dir: str = None, download_img: bool = True,
                  to_markdown: bool = True, cookie: str = None,
                  json_only: bool = False) -> Optional[Dict]:
    """
    主入口函数：获取并处理微信公众号文章

    参数：
        url: 微信文章链接（支持短链接和长链接）
        output_dir: 输出目录（默认: ./wechat_articles）
        download_img: 是否下载图片
        to_markdown: 是否转换为Markdown
        cookie: 可选的微信Cookie
        json_only: 为True时仅返回元数据字典，不保存文件

    返回：
        包含文章元数据和状态的字典，失败时返回None
    """
    # 检查依赖
    missing = []
    if not HAS_REQUESTS:
        missing.append('requests')
    if not HAS_BS4:
        missing.append('beautifulsoup4')
    if to_markdown and not HAS_HTML2TEXT:
        missing.append('html2text')
    if missing:
        print(f"缺少依赖: {', '.join(missing)}", file=sys.stderr)
        print(f"请安装: pip install {' '.join(missing)}", file=sys.stderr)
        if not HAS_REQUESTS or not HAS_BS4:
            return None

    # 获取HTML
    html_content = fetch_html(url, cookie)
    if not html_content:
        return None

    # 解析元数据
    meta = parse_meta(html_content)
    meta['source_url'] = url
    meta['fetch_time'] = datetime.now().isoformat()

    title = meta.get('title', '未命名')
    author = meta.get('author', '')
    account = meta.get('account_nickname', '未知公众号')
    create_time = meta.get('create_time')
    date_str = datetime.fromtimestamp(create_time).strftime('%Y%m%d') if create_time else 'unknown'

    if json_only:
        # 提取纯文本内容
        content_div = extract_content(html_content)
        if content_div:
            meta['content_text'] = content_div.get_text(separator='\n', strip=True)
            if HAS_HTML2TEXT:
                meta['content_markdown'] = convert_to_markdown(
                    title, str(content_div), account, date_str, author
                )
        meta['status'] = 'success'
        return meta

    # 保存到文件
    if output_dir is None:
        output_dir = './wechat_articles'

    base_dir = Path(output_dir)
    article_dir = base_dir / safe_filename(account) / f"{date_str}_{safe_filename(title)}"
    article_dir.mkdir(parents=True, exist_ok=True)

    # 提取正文
    content_div = extract_content(html_content)
    if not content_div:
        # 保存原始HTML作为备份
        (article_dir / 'index.html').write_text(html_content, encoding='utf-8')
        meta['status'] = 'partial'
        meta['reason'] = '未找到正文区域'
        meta['path'] = str(article_dir)
        return meta

    # 下载图片
    if download_img:
        images_dir = article_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        img_count = download_images(content_div, images_dir, url)
        meta['images_downloaded'] = img_count

    # 保存HTML
    html_out = build_html(title, str(content_div), account, date_str, author)
    (article_dir / 'index.html').write_text(html_out, encoding='utf-8')

    # 保存Markdown
    if to_markdown and HAS_HTML2TEXT:
        md_content = convert_to_markdown(title, str(content_div), account, date_str, author)
        (article_dir / 'article.md').write_text(md_content, encoding='utf-8')

    # 保存元数据
    (article_dir / 'meta.json').write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    meta['status'] = 'success'
    meta['path'] = str(article_dir)
    return meta


def batch_fetch(urls: list, output_dir: str = None, download_img: bool = True,
                to_markdown: bool = True, cookie: str = None,
                interval: float = 3.0) -> Dict:
    """
    批量获取多篇微信公众号文章

    参数：
        urls: 微信文章链接列表
        output_dir: 输出目录（默认: ./wechat_articles）
        download_img: 是否下载图片
        to_markdown: 是否转换为Markdown
        cookie: 可选的微信Cookie
        interval: 每篇文章之间的下载间隔秒数（默认3秒，避免触发反爬）

    返回：
        包含批量下载统计的字典
    """
    stats = {'total': len(urls), 'success': 0, 'fail': 0, 'results': []}

    for idx, url in enumerate(urls, 1):
        url = url.strip()
        if not url:
            continue

        print(f"\n[{idx}/{len(urls)}] 正在获取: {url[:60]}...")

        result = fetch_article(
            url=url,
            output_dir=output_dir,
            download_img=download_img,
            to_markdown=to_markdown,
            cookie=cookie,
        )

        if result and result.get('status') == 'success':
            stats['success'] += 1
            print(f"  标题: {result.get('title', '无')}")
            print(f"  公众号: {result.get('account_nickname', '无')}")
            print(f"  保存至: {result.get('path', '无')}")
        else:
            stats['fail'] += 1
            reason = result.get('reason', '获取失败') if result else '获取失败'
            print(f"  失败: {reason}")

        stats['results'].append(result or {'source_url': url, 'status': 'fail'})

        # 下载间隔，避免触发反爬
        if idx < len(urls):
            time.sleep(interval)

    return stats


def main():
    parser = argparse.ArgumentParser(description='微信公众号文章获取器')
    parser.add_argument('urls', nargs='+', help='微信文章链接（支持多个，空格分隔）')
    parser.add_argument('--output-dir', '-o', default='./wechat_articles',
                        help='输出目录（默认: ./wechat_articles）')
    parser.add_argument('--no-images', action='store_true', help='不下载图片')
    parser.add_argument('--no-markdown', action='store_true', help='不转换Markdown')
    parser.add_argument('--cookie', default=None, help='微信Cookie（用于认证）')
    parser.add_argument('--json', action='store_true',
                        help='将元数据JSON输出到标准输出，不保存文件')
    parser.add_argument('--interval', type=float, default=3.0,
                        help='批量下载时每篇文章的间隔秒数（默认: 3）')
    args = parser.parse_args()

    # 展开逗号分隔的URL（兼容 "url1,url2" 和 "url1 url2" 两种写法）
    urls = []
    for u in args.urls:
        urls.extend(part.strip() for part in u.split(',') if part.strip())

    if len(urls) == 1:
        # 单篇文章
        result = fetch_article(
            url=urls[0],
            output_dir=args.output_dir,
            download_img=not args.no_images,
            to_markdown=not args.no_markdown,
            cookie=args.cookie,
            json_only=args.json,
        )

        if result:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"标题: {result.get('title', '无')}")
                print(f"作者: {result.get('author', '无')}")
                print(f"公众号: {result.get('account_nickname', '无')}")
                print(f"状态: {result.get('status', '无')}")
                if result.get('path'):
                    print(f"保存至: {result['path']}")
        else:
            print("获取文章失败", file=sys.stderr)
            sys.exit(1)
    else:
        # 批量下载
        print(f"共 {len(urls)} 篇文章，开始批量下载...")
        stats = batch_fetch(
            urls=urls,
            output_dir=args.output_dir,
            download_img=not args.no_images,
            to_markdown=not args.no_markdown,
            cookie=args.cookie,
            interval=args.interval,
        )

        print(f"\n{'='*50}")
        print(f"批量下载完成: 共{stats['total']}篇, "
              f"成功{stats['success']}篇, 失败{stats['fail']}篇")

        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
