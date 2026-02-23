---
name: wechat-article-aggregator
description: "微信公众号文章聚合器。通过 mptext.top API 批量获取指定公众号博主的最新文章列表，下载文章内容并解析为 Markdown/HTML/纯文本格式。支持按公众号名称或 fakeid 获取，预置 8 个热门 AI 技术公众号。适用场景：获取指定公众号最新文章、批量抓取多个博主内容、公众号文章聚合阅读、技术资讯采集。关键词：公众号文章获取、微信文章抓取、公众号聚合、文章采集、mptext API。"
version: 1.0.0
---

# 微信公众号文章聚合器

通过 mptext.top API 批量获取指定公众号博主的最新文章，下载并解析为 Markdown/HTML/纯文本格式输出。

## 快速开始

获取单个公众号最新 2 篇文章：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ=="
```

获取多个公众号文章（逗号分隔 fakeid）：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ==,MjM5NDI4MTY3NA==" --limit 3
```

按公众号名称获取：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "赛博禅心,饼干哥哥AGI"
```

获取所有预置公众号的文章：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids all --limit 2
```

## 依赖安装

```bash
pip install requests beautifulsoup4 html2text
```

> **最低依赖**: 仅 `requests` 为必须依赖。`beautifulsoup4` 和 `html2text` 用于增强 Markdown 转换效果，未安装时会使用内置 HTML 解析器。

## 用户参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--api-key` / `-k` | string | **是** | - | mptext.top 的 API Key |
| `--fakeids` / `-f` | string | **是** | - | 公众号 fakeid 列表（逗号分隔）、公众号名称、或 `all` |
| `--limit` / `-l` | int | 否 | 2 | 每个公众号获取的文章数量 |
| `--output-dir` / `-o` | string | 否 | `./output` | 输出目录 |
| `--format` / `-F` | string | 否 | `markdown` | 输出格式：`markdown` / `html` / `text` / `json` |
| `--accounts-file` / `-a` | string | 否 | 自动查找 | 自定义公众号账号列表 JSON 文件路径 |
| `--interval` / `-i` | float | 否 | 1.0 | 请求间隔秒数 |
| `--list-accounts` | flag | 否 | - | 列出所有预置公众号信息 |

### API Key 获取方式

API Key 来源于 mptext.top 平台，用于认证文章获取请求。在请求头中以 `X-Auth-Key` 传递。

### fakeid 说明

`fakeid` 是微信公众号的唯一标识（Base64 编码的 biz 参数），可通过以下方式获取：

1. 在微信公众号平台后台查看
2. 从公众号文章 URL 中的 `__biz` 参数提取
3. 使用本 skill 预置的账号列表

## 功能说明

### 1. 获取文章列表

调用 mptext.top API 获取指定公众号的最新文章列表：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ==" --limit 5
```

### 2. 下载并解析文章内容

获取文章 HTML 后自动提取 `#js_content` 正文区域，转换为 Markdown 格式：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "赛博禅心" --format markdown
```

### 3. 批量获取多个公众号

同时获取多个公众号的最新文章：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "赛博禅心,饼干哥哥AGI,老金开源" --limit 3
```

### 4. 获取所有预置公众号

使用 `all` 关键字获取所有预置公众号的文章：

```bash
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids all
```

### 5. 查看预置公众号列表

```bash
python scripts/fetch_articles.py --api-key dummy --fakeids dummy --list-accounts
```

### 6. 作为 Python 库调用

```python
import sys
sys.path.insert(0, 'scripts')
from fetch_articles import get_article_list, download_article_html, extract_markdown_from_html, load_accounts, resolve_fakeids, fetch_all

api_key = "YOUR_API_KEY"

# 获取单个公众号文章列表
articles = get_article_list(api_key, "MzkzNDQxOTU2MQ==", limit=2)
for art in articles:
    print(art['title'], art['url'])

# 下载并解析文章内容
html = download_article_html(api_key, articles[0]['url'])
markdown = extract_markdown_from_html(html, title=articles[0]['title'])
print(markdown[:500])

# 批量获取多个公众号
accounts = load_accounts()
fakeids = resolve_fakeids("赛博禅心,饼干哥哥AGI", accounts)
summary = fetch_all(api_key, fakeids, limit=2, output_dir="./output")
print(f"成功: {summary['success']}, 失败: {summary['fail']}")
```

## 输出结构

```
output/
├── 赛博禅心/
│   ├── 文章标题1.md
│   └── 文章标题2.md
├── 饼干哥哥AGI/
│   ├── 文章标题1.md
│   └── 文章标题2.md
├── 老金开源/
│   └── ...
└── summary.json          # 所有文章的元数据汇总
```

### summary.json 格式

```json
{
  "fetch_time": "2026-02-23T17:30:00",
  "total_accounts": 3,
  "total_articles": 6,
  "success": 5,
  "fail": 1,
  "accounts": [
    {
      "fakeid": "MzkzNDQxOTU2MQ==",
      "name": "赛博禅心",
      "articles": [
        {
          "title": "文章标题",
          "url": "https://mp.weixin.qq.com/s/...",
          "create_time": "1708689600",
          "saved_path": "output/赛博禅心/文章标题.md",
          "status": "success"
        }
      ]
    }
  ]
}
```

## API 接口说明

### 文章列表接口

```
GET https://down.mptext.top/api/public/v1/article?fakeid={URL_ENCODED_FAKEID}&limit={N}
```

| 参数 | 说明 |
|------|------|
| `fakeid` | 公众号的 fakeid，需 URL 编码（`==` → `%3D%3D`） |
| `limit` | 返回文章数量 |

**请求头：**
```
X-Auth-Key: {YOUR_API_KEY}
```

**响应示例：**
```json
[
  {
    "title": "文章标题",
    "url": "https://mp.weixin.qq.com/s/xxxxx",
    "create_time": 1708689600
  }
]
```

### 文章下载接口

```
GET https://down.mptext.top/api/public/v1/download?url={URL_ENCODED_ARTICLE_URL}&type=html
```

| 参数 | 说明 |
|------|------|
| `url` | 微信文章 URL，需 URL 编码 |
| `type` | 固定为 `html`（API 返回 HTML 格式） |

**请求头：**
```
X-Auth-Key: {YOUR_API_KEY}
```

**响应：** 完整的微信文章 HTML 页面。

### HTML 正文解析规则

从下载的 HTML 中提取正文内容：

1. 定位 `id="js_content"` 的 div 元素
2. 移除 `script`、`style`、`noscript` 标签内容
3. 提取文本内容，保留段落换行
4. 使用 `html2text` 转换为 Markdown（如已安装）

## 预置公众号列表

| 序号 | 公众号名称 | 分类 | FakeID |
|------|-----------|------|--------|
| 1 | 饼干哥哥AGI | AI编程 | `MjM5NDI4MTY3NA==` |
| 2 | 赛博禅心 | AI前沿 | `MzkzNDQxOTU2MQ==` |
| 3 | 可怜的小互 | AI技术 | `MzkzMTcyMTgxNg==` |
| 4 | 宝玉的工程技术分享 | 技术翻译 | `Mzk1NzgxMjQ0OA==` |
| 5 | 苍何 | AI实战 | `Mzg3MTk3NzYzNw==` |
| 6 | 老金开源 | Claude Code | `MzI0NzU2MDgyNA==` |
| 7 | 玩转AI工具 | AI工具 | `MzU4NTE1Mjg4MA==` |
| 8 | 袋鼠帝AI客栈 | AI实战 | `MzkwMzE4NjU5NA==` |

可通过 `--accounts-file` 参数指定自定义的公众号列表 JSON 文件来扩展。

## 注意事项

- **API Key 安全**: 请勿将 API Key 硬编码到代码中，建议通过环境变量或命令行参数传入。
- **请求频率**: 默认间隔 1 秒，如遇 429 错误请增大 `--interval` 值。
- **HTML 解析**: 下载接口返回完整 HTML 页面，脚本自动从 `#js_content` 区域提取正文。
- **依赖降级**: 未安装 `beautifulsoup4` 和 `html2text` 时，使用内置 HTMLParser 提取纯文本。
- **文件命名**: 输出文件以文章标题命名，自动去除特殊字符，长度截断为 80 字符。

## 触发关键词

- "获取公众号文章"
- "抓取微信文章"
- "公众号文章聚合"
- "批量获取公众号"
- "下载公众号文章"
- "微信文章采集"
- "获取最新公众号文章"

## 更新日志

### v1.0.0 (2026-02-23)
- 初始版本
- 支持通过 mptext.top API 获取公众号文章列表
- 支持下载文章 HTML 并解析为 Markdown/HTML/Text/JSON
- 内置 HTMLParser 提取 `#js_content` 正文（零依赖降级方案）
- 预置 8 个热门 AI 技术公众号 fakeid
- 支持按公众号名称或 fakeid 获取
- 支持 `all` 关键字获取所有预置公众号
- 自动生成 summary.json 汇总元数据
