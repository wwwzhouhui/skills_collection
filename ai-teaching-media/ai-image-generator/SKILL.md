---
name: ai-image-generator
description: |
  通用图像生成执行层,支持 MuleRun Nano Banana 2、APImart GPT Image 2、Atlas Cloud GPT Image 2 和 Agnes Image 2.1 Flash 四种生图 API。通过 --provider 切换。支持 generation(纯文本生图)和 edit(带参考图修图)两种模式,单张和批量执行。这是被其他 skill 调用的基础设施 skill,不直接面向终端用户。当其他 skill(如 ai-image-generator、tech-article-diagram)需要调 API 生图时,调用本 skill 的 scripts/generate.py。不要用于:提示词撰写、风格注入、业务校验——这些由调用方 skill 负责。
---

# 通用图像生成器

支持四种生图 API 的执行层,通过 `--provider` 参数切换。调用方 skill 负责 prompt 撰写、样式注入、业务校验;本 skill 只管"接收 prompt → 调 API → 返回结果"。

## 什么时候触发这个 skill

本 skill 是被其他 skill 调用的基础设施,不直接由用户触发。当 Claude 正在执行某个生图相关的 skill(如 `ai-image-generator`、`tech-article-diagram`)时,通过 bash 调用本 skill 的脚本。

## 生图 API 切换

通过 `--provider` 参数或环境变量自动检测选择生图平台:

```bash
# 方式 1: 自动检测 —— 只设一个环境变量就行
export APIMART_API_KEY=sk-xxx
python scripts/generate.py \
  --mode generation --prompt "..." --output-dir ./out
# 自动检测到 APIMART_API_KEY，使用 apimart

# 方式 2: 显式指定 —— 两个都设了时用这个覆盖
python scripts/generate.py \
  --provider apimart --mode generation --prompt "..." --output-dir ./out
```

| Provider | `--provider` | 环境变量 | 模型 |
|---|---|---|---|
| MuleRun | `mulerun` | `MULERUN_API_KEY` | Nano Banana 2 |
| APImart | `apimart` | `APIMART_API_KEY` | GPT Image 2 |
| Atlas Cloud | `atlascloud` | `ATLASCLOUD_API_KEY` | GPT Image 2 |
| Agnes | `agnes` | `AGNES_API_KEY` | Agnes Image 2.1 Flash（`agnes-image-2.1-flash`） |

**自动检测逻辑**（不传 `--provider` 时）:
1. 仅发现一个 API Key → 自动使用对应 provider
2. 多个 API Key 同时存在 → **直接报错，要求显式指定 `--provider`**
3. 没有 API Key → 报错并提示设置


## 两种模式

### generation — 纯文本生图

从纯文字 prompt 生成图片,不依赖参考图。适合:概念图、流程图、信息图等。

```bash
# 单张
python scripts/generate.py \
  --mode generation \
  --prompt "A notebook-style diagram showing..." \
  --name-tag diagram-001 \
  --output-dir ./out

# 单张(从文件读 prompt)
python scripts/generate.py \
  --mode generation \
  --prompt-file ./prompt.txt \
  --name-tag diagram-001 \
  --output-dir ./out
```

### edit — 带参考图修图

在参考图基础上生成新图,适合需要人物一致性的场景。

```bash
# 单张
python scripts/generate.py \
  --mode edit \
  --prompt "A portrait of..." \
  --images "../short-video-cover/references/host_ref_face.png" \
  --name-tag ai-image-generator \
  --output-dir ./out
```

## 批量模式

通过 manifest JSON 批量提交,支持串行和并行。

```bash
# 串行
python scripts/generate.py \
  --manifest ./batch.json \
  --output-dir ./out

# 并行
python scripts/generate.py \
  --manifest ./batch.json \
  --output-dir ./out \
  --parallel
```

### Manifest JSON 格式

```json
{
  "mode": "mixed",
  "aspect_ratio": "16:9",
  "resolution": "2K",
  "items": [
    {
      "id": "diagram-001",
      "prompt": "完整提示词(调用方已注入风格前缀)"
    },
    {
      "id": "cover-001",
      "mode": "edit",
      "prompt": "完整提示词",
      "images": ["https://example.com/ref.png"]
    }
  ]
}
```

- `mode`: `generation`、`edit` 或 `mixed`(默认 `generation`; `mixed` 时每个 item 用自己的 `mode`)
- `aspect_ratio` / `resolution`: 全局默认,可省略
- `items[].id`: 必填,用于输出文件命名
- `items[].prompt`: 必填,完整提示词(调用方已完成所有拼接)
- `items[].images`: 可选,edit 模式需要传参考图 URL

## CLI 参数

| 参数 | 单张 | 批量 | 必填 | 说明 |
|---|---|---|---|---|
| `--provider` | Y | Y | 否* | `mulerun` / `apimart` / `atlascloud` / `agnes`；*未传时仅单 key 自动检测，多 key 必须显式指定 |
| `--mode` | Y | N(在 manifest) | 单张必填 | `generation` 或 `edit` |
| `--prompt` | Y(或 --prompt-file) | N | 否 | 内联提示词 |
| `--prompt-file` | Y(或 --prompt) | N | 否 | 提示词文件路径 |
| `--manifest` | N | Y | 否 | manifest JSON 路径 |
| `--image` | Y(edit 模式) | N | 可重复 | 参考图 URL/本地路径/data URI/base64 |
| `--images` | Y | N | 兼容旧参数 | 逗号分隔 URL（不要传 data URI） |
| `--name-tag` | Y | N | 否 | 输出文件名前缀(默认 `image`) |
| `--output-dir` | Y | Y | 否 | 输出目录(默认 `./output`) |
| `--aspect-ratio` | Y | Y(可被 manifest 覆盖) | 否 | 默认 `16:9` |
| `--resolution` | Y | Y(可被 manifest 覆盖) | 否 | 默认 `2K` |
| `--parallel` | N | Y | 否 | 启用并行执行 |
| `--blocklist` | Y | Y | 否 | 禁用词表文件路径(每行一个词,命中即停止) |

## 输出结构

单张:
```
{output-dir}/
├── {name-tag}-{timestamp}.png   # 生成图片
├── {name-tag}-{timestamp}.txt   # 使用的 prompt
└── {name-tag}-{timestamp}.json  # 元数据
```

批量:
```
{output-dir}/
├── {id}.png            # 每项图片
├── {id}.txt            # 每项 prompt
├── {id}.json           # 每项元数据
└── _run_metadata.json  # 整体运行信息
```

## 环境变量

根据 `--provider` 设置对应的 API Key:

- `MULERUN_API_KEY`: `--provider mulerun` 时必填,MuleRun API 的 Bearer token
- `APIMART_API_KEY`: `--provider apimart` 时必填,APImart API 的 Bearer token
- `ATLASCLOUD_API_KEY`: `--provider atlascloud` 时必填,Atlas Cloud API 的 Bearer token
- `AGNES_API_KEY`: `--provider agnes` 时必填,Agnes AI API 的 Bearer token
- `AGNES_API_BASE_URL`: 可选,默认 `https://apihub.agnes-ai.com/v1`
- `AGNES_IMAGE_MODEL`: 可选,默认 `agnes-image-2.1-flash`

- `AGNES_HTTP_TIMEOUT`: 可选，Agnes 请求超时秒数，默认 `300`
- `AGNES_HTTP_RETRIES`: 可选，Agnes 重试次数，默认 `2`，可设为 `0`
- `AGNES_MAX_REFERENCE_IMAGE_BYTES`: 可选，本地/data URI/base64 参考图上限，默认 `8388608`
  （兼容旧名称 `AGNES_MAX_LOCAL_IMAGE_BYTES`）

## 调用方 skill 集成指南

### 新 skill 如何使用

1. 在你的 SKILL.md 中定义 prompt 生成工作流
2. 生成 prompt 后,通过 bash 调用本 skill:

```bash
# 单张（未传 provider 时，仅一个 API Key 才会自动选择）
python /path/to/ai-image-generator/scripts/generate.py \
  --mode generation \
  --prompt-file ./my-prompt.txt \
  --name-tag my-image \
  --output-dir ./my-output

# 单张（指定 apimart）
python /path/to/ai-image-generator/scripts/generate.py \
  --provider apimart \
  --mode generation \
  --prompt-file ./my-prompt.txt \
  --name-tag my-image \
  --output-dir ./my-output

# 单张（指定 atlascloud）
python /path/to/ai-image-generator/scripts/generate.py \
  --provider atlascloud \
  --mode generation \
  --prompt-file ./my-prompt.txt \
  --name-tag my-image \
  --output-dir ./my-output

# 批量:先写 manifest JSON,再调用
python /path/to/ai-image-generator/scripts/generate.py \
  --manifest ./my-manifest.json \
  --output-dir ./my-output \
  --parallel
```

3. 脚本退出码:0 成功,1 失败
4. 读取输出目录中的 .txt 文件可获取保存的 prompt,方便重跑

### 调用方负责的事情

- 提示词撰写和拼接(包括风格前缀注入)
- 业务校验(如禁用特定词汇)
- 参考图 URL 管理
- 后处理(如生成 manifest.md 插图位置清单)

## 故障排除

| 问题 | 原因 | 对策 |
|---|---|---|
| API KEY 未找到 | 环境变量未设置 | mulerun/apimart/atlascloud/agnes 对应 `export XXX_API_KEY=sk-xxx`；多 key 时加 `--provider` |
| HTTP 403 | Cloudflare WAF 拦截 | 脚本已内置浏览器 UA,检查网络 |
| 轮询超时 | API 服务繁忙 | 等待后重试,或检查 API 状态 |
| edit 模式未传 --images | 缺少参考图 | edit 模式必须通过 --image/--images 传参考图 |


## Agnes Image 2.1 Flash 说明

- 模型 ID：`agnes-image-2.1-flash`
- 默认 Base URL：`https://apihub.agnes-ai.com/v1`
- 接口：同步 `POST /images/generations`（无需任务轮询）
- 支持：
  - `generation` 文生图
  - `edit` 图生图（参考图 URL / 本地路径 / base64）
- 比例到 size 映射：

| aspect_ratio | Agnes size |
|---|---|
| `1:1` | `1024x1024` |
| `4:3` / `3:2` | `1024x768` |
| `3:4` / `2:3` | `768x1024` |
| `16:9` | `1024x576` |
| `9:16` | `576x1024` |

注意：Agnes 侧使用固定 size token，`--resolution` 参数会被忽略（仅为兼容其它 provider 的统一 CLI）；不支持的 `aspect_ratio` 会直接报错，不会静默退化成方图。


## 变更记录

### v1.1.0
- 新增 Agnes Image 2.1 Flash provider
- 修复 provider 自动选择：多 key 必须显式指定
- edit 模式强制校验参考图，禁止静默退化成文生图
- 批量 ID 安全校验、空并行保护
- CLI 支持重复 `--image`，避免 data URI 被逗号拆坏
- 元数据区分 requested_resolution 与 actual_size（Agnes 会记录忽略 2K 等 resolution）
- HTTP 超时默认 300s，支持重试；参考图输入增加格式和大小校验
