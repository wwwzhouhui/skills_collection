#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信公众号文章聚合器 - 通过 mptext.top API 批量获取指定公众号的最新文章

用法：
    python fetch_articles.py --api-key <KEY> --fakeids "ID1,ID2" [--limit 2] [--output-dir ./output] [--format markdown]

依赖：
    pip install requests beautifulsoup4 html2text
"""

import sys
import os
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from html.parser import HTMLParser

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


# ============================================================
# 内置 HTML 正文提取器（无需 BeautifulSoup 也能工作）
# ============================================================

class ContentExtractor(HTMLParser):
    """从微信文章 HTML 中提取 #js_content 区域的纯文本"""

    def __init__(self):
        super().__init__()
        self.in_content = False
        self.depth = 0
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'noscript'}
        self.current_skip = 0
        self.block_tags = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                           'section', 'br', 'li', 'blockquote', 'pre', 'tr'}

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if attrs_dict.get('id') == 'js_content':
            self.in_content = True
            self.depth = 1
            return
        if self.in_content:
            self.depth += 1
        if tag in self.skip_tags:
            self.current_skip += 1
        if self.in_content and tag in self.block_tags:
            self.text_parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.current_skip = max(0, self.current_skip - 1)
        if self.in_content:
            self.depth -= 1
            if self.depth <= 0:
                self.in_content = False

    def handle_data(self, data):
        if self.in_content and self.current_skip == 0:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)

    def get_text(self):
        raw = '\n'.join(self.text_parts)
        # 合并连续空行
        return re.sub(r'\n{3,}', '\n\n', raw).strip()


# ============================================================
# API 调用
# ============================================================

API_BASE = "https://down.mptext.top"
ARTICLE_LIST_ENDPOINT = "/api/public/v1/article"
DOWNLOAD_ENDPOINT = "/api/public/v1/download"


def get_article_list(api_key: str, fakeid: str, limit: int = 2) -> list:
    """
    获取指定公众号的最新文章列表

    参数：
        api_key: mptext.top 的 API Key
        fakeid: 公众号的 fakeid (biz 编码)
        limit: 获取文章数量

    返回：
        文章信息列表 [{"title": ..., "url": ..., "create_time": ..., ...}, ...]
    """
    if not HAS_REQUESTS:
        print("错误: requests 未安装，请运行: pip install requests", file=sys.stderr)
        return []

    encoded_fakeid = quote(fakeid)
    url = f"{API_BASE}{ARTICLE_LIST_ENDPOINT}?fakeid={encoded_fakeid}&limit={limit}"
    headers = {"X-Auth-Key": api_key}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 401:
            print(f"错误: API Key 认证失败 (HTTP 401)", file=sys.stderr)
            return []
        if resp.status_code == 429:
            print(f"警告: 请求频率过高 (HTTP 429)，请稍后再试", file=sys.stderr)
            return []
        if resp.status_code != 200:
            print(f"错误: 获取文章列表失败 (HTTP {resp.status_code})", file=sys.stderr)
            return []

        data = resp.json()
        # API 返回格式适配：可能是 {"data": [...]} 或直接 [...]
        if isinstance(data, list):
            return data[:limit]
        if isinstance(data, dict):
            articles = data.get('data') or data.get('articles') or data.get('list') or []
            if isinstance(articles, list):
                return articles[:limit]
        return []

    except requests.exceptions.Timeout:
        print(f"错误: 请求超时", file=sys.stderr)
        return []
    except Exception as e:
        print(f"错误: 获取文章列表异常: {e}", file=sys.stderr)
        return []


def download_article_html(api_key: str, article_url: str) -> str:
    """
    通过 mptext.top API 下载文章 HTML 内容

    参数：
        api_key: mptext.top 的 API Key
        article_url: 微信文章 URL

    返回：
        文章 HTML 内容，失败返回空字符串
    """
    if not HAS_REQUESTS:
        return ""

    encoded_url = quote(article_url, safe='')
    url = f"{API_BASE}{DOWNLOAD_ENDPOINT}?url={encoded_url}&type=html"
    headers = {"X-Auth-Key": api_key}

    try:
        resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code == 401:
            print(f"错误: API Key 认证失败", file=sys.stderr)
            return ""
        if resp.status_code == 429:
            print(f"警告: 请求频率限制，等待 5 秒后重试...", file=sys.stderr)
            time.sleep(5)
            resp = requests.get(url, headers=headers, timeout=60)
        if resp.status_code != 200:
            print(f"错误: 下载文章失败 (HTTP {resp.status_code})", file=sys.stderr)
            return ""
        return resp.text

    except requests.exceptions.Timeout:
        print(f"错误: 下载文章超时", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"错误: 下载文章异常: {e}", file=sys.stderr)
        return ""


# ============================================================
# 内容解析与转换
# ============================================================

def extract_text_from_html(html_content: str) -> str:
    """从 HTML 中提取 #js_content 区域的纯文本（内置解析器）"""
    extractor = ContentExtractor()
    extractor.feed(html_content)
    return extractor.get_text()


def extract_markdown_from_html(html_content: str, title: str = "",
                                account: str = "", date_str: str = "") -> str:
    """从 HTML 中提取内容并转换为 Markdown"""
    # 优先使用 BeautifulSoup + html2text
    if HAS_BS4 and HAS_HTML2TEXT:
        soup = BeautifulSoup(html_content, 'html.parser')
        content_div = soup.find('div', id='js_content') or soup.find('div', class_='rich_media_content')
        if content_div:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0
            md_body = h.handle(str(content_div))

            header = f"# {title}\n\n" if title else ""
            meta_parts = []
            if account:
                meta_parts.append(f"> 公众号: {account}")
            if date_str:
                meta_parts.append(f"> 日期: {date_str}")
            meta = "\n".join(meta_parts) + "\n\n---\n\n" if meta_parts else ""

            return header + meta + md_body

    # 降级：使用内置解析器提取纯文本
    text = extract_text_from_html(html_content)
    if title:
        text = f"# {title}\n\n{text}"
    return text


# ============================================================
# 文件输出
# ============================================================

def safe_filename(name: str, max_length: int = 80) -> str:
    """生成安全的文件/目录名"""
    safe = re.sub(r'[\\/:*?"<>|\r\n\t]', '', name)
    safe = re.sub(r'\s+', '_', safe).strip('_.')
    return (safe[:max_length] if len(safe) > max_length else safe) or 'untitled'


def save_article(content: str, title: str, account_name: str,
                 output_dir: str, fmt: str = "markdown") -> str:
    """
    保存文章内容到文件

    返回：保存的文件路径
    """
    account_dir = Path(output_dir) / safe_filename(account_name)
    account_dir.mkdir(parents=True, exist_ok=True)

    safe_title = safe_filename(title)
    if fmt == "markdown":
        filepath = account_dir / f"{safe_title}.md"
    elif fmt == "html":
        filepath = account_dir / f"{safe_title}.html"
    else:
        filepath = account_dir / f"{safe_title}.txt"

    filepath.write_text(content, encoding='utf-8')
    return str(filepath)


# ============================================================
# 主流程
# ============================================================

def load_accounts(accounts_file: str = None) -> list:
    """加载预置公众号账号列表"""
    if accounts_file and Path(accounts_file).exists():
        with open(accounts_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    # 默认查找同级 references/accounts.json
    script_dir = Path(__file__).parent.parent
    default_path = script_dir / 'references' / 'accounts.json'
    if default_path.exists():
        with open(default_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return []


def resolve_fakeids(fakeids_input: str, accounts: list) -> list:
    """
    解析 fakeid 输入，支持：
    - 直接传 fakeid: "MzkzNDQxOTU2MQ=="
    - 传公众号名称: "赛博禅心"
    - 传 "all" 使用所有预置账号
    - 逗号分隔多个
    """
    if fakeids_input.strip().lower() == 'all':
        return [(a['fakeid'], a['name']) for a in accounts]

    result = []
    for item in fakeids_input.split(','):
        item = item.strip()
        if not item:
            continue

        # 检查是否是名称
        matched = False
        for acc in accounts:
            if acc['name'] == item:
                result.append((acc['fakeid'], acc['name']))
                matched = True
                break
        if not matched:
            # 当作 fakeid 使用
            # 尝试从预置列表找名称
            name = item
            for acc in accounts:
                if acc['fakeid'] == item:
                    name = acc['name']
                    break
            result.append((item, name))

    return result


def fetch_all(api_key: str, fakeids: list, limit: int = 2,
              output_dir: str = "./output", fmt: str = "markdown",
              interval: float = 1.0) -> dict:
    """
    批量获取多个公众号的最新文章

    参数：
        api_key: mptext.top API Key
        fakeids: [(fakeid, name), ...] 列表
        limit: 每个公众号获取的文章数
        output_dir: 输出目录
        fmt: 输出格式 (markdown/html/text/json)
        interval: 请求间隔（秒）

    返回：
        汇总结果字典
    """
    summary = {
        "fetch_time": datetime.now().isoformat(),
        "total_accounts": len(fakeids),
        "total_articles": 0,
        "success": 0,
        "fail": 0,
        "accounts": []
    }

    for idx, (fakeid, account_name) in enumerate(fakeids):
        print(f"\n[{idx+1}/{len(fakeids)}] 正在获取: {account_name} ({fakeid})")

        account_result = {
            "fakeid": fakeid,
            "name": account_name,
            "articles": []
        }

        # 获取文章列表
        articles = get_article_list(api_key, fakeid, limit)
        if not articles:
            print(f"  未获取到文章")
            summary['accounts'].append(account_result)
            if idx < len(fakeids) - 1:
                time.sleep(interval)
            continue

        print(f"  获取到 {len(articles)} 篇文章")

        for art_idx, article in enumerate(articles):
            title = article.get('title', '未知标题')
            article_url = article.get('url') or article.get('link', '')
            create_time = article.get('create_time', '')

            print(f"  [{art_idx+1}/{len(articles)}] {title}")

            if not article_url:
                print(f"    跳过: 无文章链接")
                account_result['articles'].append({
                    "title": title,
                    "status": "skip",
                    "reason": "no_url"
                })
                summary['fail'] += 1
                continue

            # 下载文章 HTML
            html_content = download_article_html(api_key, article_url)
            if not html_content:
                print(f"    下载失败")
                account_result['articles'].append({
                    "title": title,
                    "url": article_url,
                    "status": "fail",
                    "reason": "download_failed"
                })
                summary['fail'] += 1
                time.sleep(interval)
                continue

            # 解析内容
            date_str = ""
            if create_time:
                try:
                    if isinstance(create_time, (int, float)):
                        date_str = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d')
                    else:
                        date_str = str(create_time)[:10]
                except Exception:
                    date_str = str(create_time)

            if fmt == "html":
                content = html_content
            elif fmt == "json":
                text = extract_text_from_html(html_content)
                article_data = {
                    "title": title,
                    "url": article_url,
                    "account": account_name,
                    "create_time": str(create_time),
                    "content": text
                }
                content = json.dumps(article_data, ensure_ascii=False, indent=2)
            else:
                # markdown 或 text
                content = extract_markdown_from_html(
                    html_content, title=title,
                    account=account_name, date_str=date_str
                )

            # 保存文件
            saved_path = save_article(
                content=content,
                title=title,
                account_name=account_name,
                output_dir=output_dir,
                fmt=fmt
            )
            print(f"    保存至: {saved_path}")

            account_result['articles'].append({
                "title": title,
                "url": article_url,
                "create_time": str(create_time),
                "saved_path": saved_path,
                "status": "success"
            })
            summary['success'] += 1
            summary['total_articles'] += 1

            # 请求间隔
            time.sleep(interval)

        summary['accounts'].append(account_result)

    # 保存汇总信息
    summary_path = Path(output_dir) / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"\n汇总信息已保存至: {summary_path}")

    return summary


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='微信公众号文章聚合器 - 批量获取指定公众号的最新文章',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 获取单个公众号最新2篇文章
  python fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ=="

  # 获取多个公众号，每个3篇
  python fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ==,MjM5NDI4MTY3NA==" --limit 3

  # 按公众号名称获取（需要 accounts.json）
  python fetch_articles.py --api-key YOUR_KEY --fakeids "赛博禅心,饼干哥哥AGI"

  # 获取所有预置公众号的文章
  python fetch_articles.py --api-key YOUR_KEY --fakeids all

  # 输出为 HTML 格式
  python fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ==" --format html

  # 自定义输出目录
  python fetch_articles.py --api-key YOUR_KEY --fakeids all --output-dir ./my_articles
        """
    )

    parser.add_argument('--api-key', '-k', required=True,
                        help='mptext.top 的 API Key（必填）')
    parser.add_argument('--fakeids', '-f', required=True,
                        help='公众号 fakeid 列表（逗号分隔），或公众号名称，或 "all" 获取所有预置账号')
    parser.add_argument('--limit', '-l', type=int, default=2,
                        help='每个公众号获取的文章数量（默认: 2）')
    parser.add_argument('--output-dir', '-o', default='./output',
                        help='输出目录（默认: ./output）')
    parser.add_argument('--format', '-F', choices=['markdown', 'html', 'text', 'json'],
                        default='markdown',
                        help='输出格式（默认: markdown）')
    parser.add_argument('--accounts-file', '-a', default=None,
                        help='自定义公众号账号列表 JSON 文件路径')
    parser.add_argument('--interval', '-i', type=float, default=1.0,
                        help='请求间隔秒数（默认: 1.0）')
    parser.add_argument('--list-accounts', action='store_true',
                        help='列出所有预置公众号账号')

    args = parser.parse_args()

    # 列出预置账号
    if args.list_accounts:
        accounts = load_accounts(args.accounts_file)
        if not accounts:
            print("未找到预置公众号账号列表")
            sys.exit(1)
        print(f"{'序号':<4} {'公众号名称':<20} {'分类':<10} {'FakeID'}")
        print("-" * 70)
        for i, acc in enumerate(accounts, 1):
            print(f"{i:<4} {acc['name']:<20} {acc.get('category', '-'):<10} {acc['fakeid']}")
        sys.exit(0)

    # 检查依赖
    if not HAS_REQUESTS:
        print("错误: requests 未安装，请运行: pip install requests", file=sys.stderr)
        sys.exit(1)

    # 加载账号列表
    accounts = load_accounts(args.accounts_file)

    # 解析 fakeid
    fakeids = resolve_fakeids(args.fakeids, accounts)
    if not fakeids:
        print("错误: 未指定有效的公众号", file=sys.stderr)
        sys.exit(1)

    print(f"准备获取 {len(fakeids)} 个公众号的最新文章（每个 {args.limit} 篇）")
    print(f"输出目录: {args.output_dir}")
    print(f"输出格式: {args.format}")
    print("=" * 60)

    # 执行获取
    summary = fetch_all(
        api_key=args.api_key,
        fakeids=fakeids,
        limit=args.limit,
        output_dir=args.output_dir,
        fmt=args.format,
        interval=args.interval
    )

    # 输出统计
    print("\n" + "=" * 60)
    print(f"获取完成!")
    print(f"  公众号数: {summary['total_accounts']}")
    print(f"  文章总数: {summary['total_articles']}")
    print(f"  成功: {summary['success']}")
    print(f"  失败: {summary['fail']}")


if __name__ == '__main__':
    main()
