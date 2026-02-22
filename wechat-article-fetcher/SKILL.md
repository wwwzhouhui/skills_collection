---
name: wechat-article-fetcher
description: "获取并解析微信公众号文章。从微信文章链接中提取标题、作者、公众号名称、正文内容、图片和元数据。当用户提供微信文章链接(mp.weixin.qq.com/s/...)并希望阅读、提取、下载或转换文章内容时使用。适用场景包括获取/下载微信文章、提取微信文章文字或元数据、将微信文章转换为Markdown、将微信文章连同图片保存到本地。关键词：微信公众号、文章获取、文章抓取、文章下载。"
---

# 微信公众号文章获取器

获取、解析并保存微信公众号文章，支持单篇和批量下载、元数据提取、图片下载和 Markdown 转换。

## 快速开始

获取单篇文章：

```bash
python scripts/fetch_wechat_article.py "https://mp.weixin.qq.com/s/xxxxx"
```

批量获取多篇文章（空格分隔）：

```bash
python scripts/fetch_wechat_article.py "url1" "url2" "url3" --output-dir ./output
```

批量获取多篇文章（逗号分隔）：

```bash
python scripts/fetch_wechat_article.py "url1,url2,url3" --output-dir ./output
```

仅输出元数据（不保存文件）：

```bash
python scripts/fetch_wechat_article.py "https://mp.weixin.qq.com/s/xxxxx" --json
```

## 依赖安装

```bash
pip install beautifulsoup4 html2text requests
```

## 功能说明

### 1. 获取文章并保存到本地

```bash
python scripts/fetch_wechat_article.py "<url>" --output-dir ./output
```

输出目录结构：
```
output/<公众号名称>/<日期>_<标题>/
├── index.html    # 格式化的独立HTML文件
├── article.md    # Markdown版本
├── meta.json     # 文章元数据
└── images/       # 下载的图片
```

### 2. 仅提取元数据

```bash
python scripts/fetch_wechat_article.py "<url>" --json
```

返回 JSON 包含：`title`（标题）、`author`（作者）、`account_nickname`（公众号名称）、`description`（摘要）、`create_time`（发布时间）、`content_text`（正文文本）、`content_markdown`（Markdown内容）、`cover_image`（封面图）、`source_url`（原文链接）。

### 3. 批量下载多篇文章

空格分隔多个链接：

```bash
python scripts/fetch_wechat_article.py "url1" "url2" "url3" --output-dir ./output
```

逗号分隔多个链接：

```bash
python scripts/fetch_wechat_article.py "url1,url2,url3" --output-dir ./output
```

自定义下载间隔（默认3秒，避免触发反爬）：

```bash
python scripts/fetch_wechat_article.py "url1" "url2" --interval 5
```

同一公众号的文章自动归类到同一目录下。

### 4. 不下载图片

```bash
python scripts/fetch_wechat_article.py "<url>" --no-images
```

### 4. 不下载图片

```bash
python scripts/fetch_wechat_article.py "<url>" --no-images
```

### 5. 作为 Python 库调用

```python
from scripts.fetch_wechat_article import fetch_article, batch_fetch

# 单篇获取并保存
result = fetch_article("https://mp.weixin.qq.com/s/xxxxx", output_dir="./output")
print(result['title'], result['path'])

# 单篇仅获取元数据
meta = fetch_article("https://mp.weixin.qq.com/s/xxxxx", json_only=True)
print(meta['title'])
print(meta['content_text'][:200])

# 批量获取
urls = ["https://mp.weixin.qq.com/s/aaa", "https://mp.weixin.qq.com/s/bbb"]
stats = batch_fetch(urls, output_dir="./output", interval=3.0)
print(f"成功{stats['success']}篇, 失败{stats['fail']}篇")
```

主要函数参数：
- `url`：文章链接（支持短链接和长链接）
- `output_dir`：保存目录（默认：`./wechat_articles`）
- `download_img`：是否下载图片（默认：`True`）
- `to_markdown`：是否转换为 Markdown（默认：`True`）
- `json_only`：仅返回元数据字典，不保存文件

`batch_fetch` 额外参数：
- `urls`：文章链接列表
- `interval`：每篇文章之间的下载间隔秒数（默认：`3.0`）

## 注意事项

- **优先使用短链接**（`/s/xxxxx`）—— 带 `__biz` 参数的长链接可能触发验证码。
- 批量下载时默认间隔3秒，可通过 `--interval` 调整，避免触发微信反爬机制。
- 自动使用微信移动端 User-Agent 绕过访问限制。
- 微信图片使用 `data-src` 属性（非 `src`），因为采用了懒加载。
- 下载图片需要设置 `Referer: https://mp.weixin.qq.com/` 请求头。
- HTML 结构详情参见 [references/wechat_html_structure.md](references/wechat_html_structure.md)。
