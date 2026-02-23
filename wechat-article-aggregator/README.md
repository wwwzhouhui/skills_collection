# WeChat Article Aggregator

> 微信公众号文章聚合器 - 通过 mptext.top API 批量获取指定公众号博主的最新文章，下载并解析为 Markdown/HTML/纯文本格式

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Version](https://img.shields.io/badge/version-1.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

## 项目介绍

WeChat Article Aggregator 是一个微信公众号文章批量采集工具，基于 [mptext.top](https://down.mptext.top) API 实现。只需提供公众号的 fakeid 或名称，即可自动获取最新文章列表、下载文章内容并解析为 Markdown 格式保存到本地。

预置了 8 个热门 AI 技术公众号，支持一键获取所有公众号的最新文章，同时也可作为 Claude Code Skill 在 AI 编程助手中直接调用。

### 核心特性

- **批量获取** - 一次获取多个公众号的最新文章，按公众号分目录存储
- **智能解析** - 自动提取微信文章 `#js_content` 正文区域，去除广告和冗余内容
- **多格式输出** - 支持 Markdown、HTML、纯文本、JSON 四种输出格式
- **名称识别** - 支持直接传入公众号名称（如 `赛博禅心`），自动匹配 fakeid
- **预置账号** - 内置 8 个热门 AI/技术公众号，`--fakeids all` 一键获取
- **零依赖降级** - 仅 `requests` 为必须依赖，无 BeautifulSoup 时自动使用内置解析器
- **元数据汇总** - 自动生成 `summary.json` 记录所有文章的标题、链接、保存路径等信息

---

## 快速开始

### 1. 安装依赖

```bash
pip install requests beautifulsoup4 html2text
```

> `beautifulsoup4` 和 `html2text` 为可选依赖，用于增强 Markdown 转换效果。未安装时自动使用内置 HTML 解析器。

### 2. 获取 API Key

访问 [mptext.top](https://down.mptext.top) 平台注册并获取 API Key。

### 3. 运行

```bash
# 获取单个公众号最新 2 篇文章
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ=="

# 按公众号名称获取
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "赛博禅心,饼干哥哥AGI"

# 获取所有预置公众号的文章
python scripts/fetch_articles.py --api-key YOUR_KEY --fakeids all --limit 2
```

---

## 使用说明

### 命令行参数

| 参数 | 简写 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|------|--------|------|
| `--api-key` | `-k` | string | 是 | - | mptext.top 的 API Key |
| `--fakeids` | `-f` | string | 是 | - | 公众号 fakeid（逗号分隔）、名称、或 `all` |
| `--limit` | `-l` | int | 否 | 2 | 每个公众号获取的文章数量 |
| `--output-dir` | `-o` | string | 否 | `./output` | 输出目录 |
| `--format` | `-F` | string | 否 | `markdown` | 输出格式：markdown/html/text/json |
| `--accounts-file` | `-a` | string | 否 | 自动查找 | 自定义公众号账号列表 JSON 文件 |
| `--interval` | `-i` | float | 否 | 1.0 | 请求间隔秒数 |
| `--list-accounts` | - | flag | 否 | - | 列出所有预置公众号信息 |

### 使用示例

**获取单个公众号最新文章：**

```bash
python scripts/fetch_articles.py -k YOUR_KEY -f "MzkzNDQxOTU2MQ==" -l 3
```

**按名称获取多个公众号：**

```bash
python scripts/fetch_articles.py -k YOUR_KEY -f "赛博禅心,老金开源,苍何" -l 2
```

**获取所有预置公众号，输出为 HTML：**

```bash
python scripts/fetch_articles.py -k YOUR_KEY -f all -F html -o ./my_articles
```

**查看预置公众号列表：**

```bash
python scripts/fetch_articles.py -k dummy -f dummy --list-accounts
```

输出：

```
序号   公众号名称                分类         FakeID
----------------------------------------------------------------------
1    饼干哥哥AGI              AI编程       MjM5NDI4MTY3NA==
2    赛博禅心                 AI前沿       MzkzNDQxOTU2MQ==
3    可怜的小互                AI技术       MzkzMTcyMTgxNg==
4    宝玉的工程技术分享            技术翻译       Mzk1NzgxMjQ0OA==
5    苍何                   AI实战       Mzg3MTk3NzYzNw==
6    老金开源                 Claude Code MzI0NzU2MDgyNA==
7    玩转AI工具               AI工具       MzU4NTE1Mjg4MA==
8    袋鼠帝AI客栈              AI实战       MzkwMzE4NjU5NA==
```

### 作为 Python 库调用

```python
import sys
sys.path.insert(0, 'scripts')
from fetch_articles import (
    get_article_list,
    download_article_html,
    extract_markdown_from_html,
    load_accounts,
    resolve_fakeids,
    fetch_all
)

api_key = "YOUR_API_KEY"

# 获取单个公众号文章列表
articles = get_article_list(api_key, "MzkzNDQxOTU2MQ==", limit=2)
for art in articles:
    print(art['title'], art['url'])

# 下载并解析单篇文章为 Markdown
html = download_article_html(api_key, articles[0]['url'])
markdown = extract_markdown_from_html(html, title=articles[0]['title'])
print(markdown[:500])

# 批量获取多个公众号
accounts = load_accounts()
fakeids = resolve_fakeids("赛博禅心,饼干哥哥AGI", accounts)
summary = fetch_all(api_key, fakeids, limit=2, output_dir="./output")
print(f"成功: {summary['success']}, 失败: {summary['fail']}")
```

---

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
└── summary.json              # 所有文章的元数据汇总
```

### summary.json 示例

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
          "title": "GLM-5 技术报告全解读",
          "url": "https://mp.weixin.qq.com/s/...",
          "create_time": "1708689600",
          "saved_path": "output/赛博禅心/GLM-5_技术报告全解读.md",
          "status": "success"
        }
      ]
    }
  ]
}
```

---

## 预置公众号

| 公众号名称 | 分类 | 简介 | FakeID |
|-----------|------|------|--------|
| 饼干哥哥AGI | AI编程 | AI编程实战与AGI前沿探索 | `MjM5NDI4MTY3NA==` |
| 赛博禅心 | AI前沿 | AI前沿技术深度解读 | `MzkzNDQxOTU2MQ==` |
| 可怜的小互 | AI技术 | AI技术科普与实战分享 | `MzkzMTcyMTgxNg==` |
| 宝玉的工程技术分享 | 技术翻译 | 海外AI技术文章翻译与工程实践 | `Mzk1NzgxMjQ0OA==` |
| 苍何 | AI实战 | AI工具实战教程与效率提升 | `Mzg3MTk3NzYzNw==` |
| 老金开源 | Claude Code | Claude Code深度使用与开源项目 | `MzI0NzU2MDgyNA==` |
| 玩转AI工具 | AI工具 | AI工具评测与使用技巧 | `MzU4NTE1Mjg4MA==` |
| 袋鼠帝AI客栈 | AI实战 | AI应用实战与案例分享 | `MzkwMzE4NjU5NA==` |

### 添加自定义公众号

创建自定义 JSON 文件（如 `my_accounts.json`）：

```json
[
  {
    "fakeid": "YOUR_FAKEID_HERE",
    "name": "公众号名称",
    "category": "分类",
    "description": "简介"
  }
]
```

通过 `--accounts-file` 参数加载：

```bash
python scripts/fetch_articles.py -k YOUR_KEY -f all -a my_accounts.json
```

### fakeid 获取方式

`fakeid` 是微信公众号的唯一标识（Base64 编码的 biz 参数），获取方式：

1. 从公众号文章 URL 的 `__biz` 参数中提取
2. 在微信公众号平台后台查看
3. 使用本工具预置的账号列表

---

## 技术架构

### 工作流程

```
输入公众号 fakeid/名称
        ↓
调用 mptext.top 文章列表 API
        ↓
获取文章标题、链接、发布时间
        ↓
调用 mptext.top 下载 API 获取 HTML
        ↓
解析 #js_content 正文区域
        ↓
转换为 Markdown / HTML / Text / JSON
        ↓
按公众号分目录保存 + 生成 summary.json
```

### API 接口

**文章列表：**

```
GET https://down.mptext.top/api/public/v1/article?fakeid={URL_ENCODED_FAKEID}&limit={N}
Header: X-Auth-Key: {API_KEY}
```

**文章下载：**

```
GET https://down.mptext.top/api/public/v1/download?url={URL_ENCODED_URL}&type=html
Header: X-Auth-Key: {API_KEY}
```

### HTML 解析策略

| 优先级 | 方案 | 依赖 | 说明 |
|--------|------|------|------|
| 1 | BeautifulSoup + html2text | `beautifulsoup4`, `html2text` | 完整 Markdown 转换，保留图片链接和格式 |
| 2 | 内置 ContentExtractor | 无（标准库） | 基于 `html.parser`，提取纯文本，自动降级 |

---

## 项目结构

```
wechat-article-aggregator/
├── README.md                     # 项目文档
├── SKILL.md                      # Claude Code Skill 定义文件
├── scripts/
│   └── fetch_articles.py         # 核心抓取脚本 (CLI + Python 库)
└── references/
    └── accounts.json             # 预置公众号账号列表
```

---

## Claude Code Skill 用法

本项目同时是一个 Claude Code Skill，安装后可在 Claude Code 中通过自然语言触发：

**安装：**

```bash
cp -rf wechat-article-aggregator /root/.claude/skills/
```

**触发关键词：**

- "获取公众号文章"
- "抓取微信文章"
- "公众号文章聚合"
- "批量获取公众号"
- "下载公众号文章"

**对话示例：**

```
> 获取赛博禅心和老金开源最新2篇公众号文章
> 批量获取所有预置公众号的最新文章
> 抓取饼干哥哥AGI最新3篇文章并保存为Markdown
```

---

## 注意事项

- **API Key 安全** - 请勿将 API Key 硬编码到代码或提交到版本库，建议通过命令行参数或环境变量传入
- **请求频率** - 默认间隔 1 秒，遇到 HTTP 429 错误时请增大 `--interval` 值
- **HTML 解析** - 下载接口返回完整 HTML 页面，脚本自动从 `#js_content` 区域提取正文
- **文件命名** - 输出文件以文章标题命名，自动去除特殊字符，长度截断为 80 字符
- **编码** - 所有输出文件使用 UTF-8 编码

---

## 更新日志

### v1.0.0 (2026-02-23)

- 初始版本发布
- 支持通过 mptext.top API 获取公众号文章列表和内容
- 支持 Markdown / HTML / Text / JSON 四种输出格式
- 内置 HTMLParser 实现零依赖降级方案
- 预置 8 个热门 AI 技术公众号
- 支持按公众号名称或 fakeid 获取
- 支持 `all` 关键字一键获取所有预置公众号
- 自动生成 summary.json 汇总元数据

---

## 作者

- **GitHub**: [wwwzhouhui](https://github.com/wwwzhouhui)
- **微信**: laohaibao2025
