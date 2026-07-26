---
name: grok-imagine-image
description: |
  使用 grok-imagine-image 模型，通过兼容 Grok2API / OpenAI 风格的接口（`/v1/images/generations`）生成图片。当用户要求用 Grok Imagine / grok-imagine-image 生成、绘制、创作图片时使用；或其他工作流需要本地脚本调用该生图模型时使用。当用户明确指定 Grok Imagine，或提供该 Grok2API 地址时，优先使用本技能，而不是通用生图工具。
---

# Grok Imagine 生图

通过 `POST /v1/images/generations` 调用 `grok-imagine-image` 生成图片。

## 快速开始

在任意工作区执行：

```bash
python "$CODEX_HOME/skills/grok-imagine-image/scripts/generate.py" \
  --prompt "a cozy reading nook with soft daylight" \
  --output-dir ./outputs \
  --name-tag reading-nook \
  --json
```

Windows 绝对路径示例：

```bash
python "C:\Users\Administrator\.codex\skills\grok-imagine-image\scripts\generate.py" \
  --prompt "a simple red apple on a white background" \
  --output-dir "./outputs" \
  --json
```

## 默认配置

| 项目 | 默认值 |
|---|---|
| API 地址 | `http://43.163.230.83:8000/v1` |
| 模型 | `grok-imagine-image` |
| 尺寸 | `1024x1024` |
| 超时 | `180` 秒 |
| API Key | 写在 `scripts/generate.py` 中的占位符（`DEFAULT_API_KEY`） |

可用环境变量或参数覆盖：

- `GROK_IMAGINE_API_KEY` / `--api-key`
- `GROK_IMAGINE_API_BASE` / `--api-base`
- `GROK_IMAGINE_MODEL` / `--model`

## 工作流程

1. 确认用户需要使用 Grok Imagine 生图。
2. 写清楚提示词（该接口通常英文 prompt 效果更稳）。
3. 选择当前工作区下的输出目录（面向用户的图片优先放 `outputs/`）。
4. 运行 `scripts/generate.py`。
5. 回报本地保存路径和可访问的图片 URL。
6. 若下载成功，把本地图片路径展示给用户。

## 重要接口行为

- **只使用** `/v1/images/generations`。不要用 `/v1/chat/completions` 调 `grok-imagine-image`。
- 成功响应大致如下：

```json
{
  "created": 1785029720,
  "data": [
    {
      "mime_type": "image/jpeg",
      "revised_prompt": "",
      "url": "http://127.0.0.1:8000/v1/media/images/img_xxx"
    }
  ]
}
```

- 返回的媒体 URL 可能指向 `127.0.0.1`。脚本会在下载前改写为配置的公网主机地址。
- 生图可能需要几十秒；超时时间请保持较高（默认 180 秒）。

## 脚本参数

```bash
python scripts/generate.py \
  --prompt "..." \
  --prompt-file ./prompt.txt \
  --output-dir ./outputs \
  --name-tag my-image \
  --n 1 \
  --size 1024x1024 \
  --model grok-imagine-image \
  --api-base http://43.163.230.83:8000/v1 \
  --api-key g2a_xxx \
  --timeout 180 \
  --json
```

常用参数：

- `--json`：输出机器可读 JSON，方便 Agent 解析
- `--no-download`：只打印 API URL，不下载文件
- `--response-format url|b64_json`：可选 OpenAI 风格字段（若网关支持）

## 密钥配置

首次正式使用前，请替换：

`scripts/generate.py` 中的 `DEFAULT_API_KEY = "g2a_REPLACE_ME"`

或设置：

```bash
# PowerShell
$env:GROK_IMAGINE_API_KEY = "g2a_xxx"
$env:GROK_IMAGINE_API_BASE = "http://43.163.230.83:8000/v1"
```

不要在用户可见回复中完整打印 API Key。

## 失败处理

- `invalid_request` / 缺少 model 或 prompt：检查请求体，确保 `--prompt` 非空。
- `401/403`：密钥缺失、仍是占位符，或未授权。
- 超时：用相同 prompt 重试一次；生图本身可能较慢。
- 生成成功但下载失败：回报改写后的公网 URL，并保留生成结果。
- 若走 Chat Completions 失败：改回 `images/generations`。

## Agent 检查清单

- 优先使用本技能自带脚本，不要手写临时 curl/Python。
- 用户可见图片优先保存到工作区 `outputs/`。
- 成功后简要汇报：使用的 prompt、本地路径、公网 URL。
- 若用户提供了新的 base URL 或 key，优先用参数/环境变量传入，不要去改无关文件。
