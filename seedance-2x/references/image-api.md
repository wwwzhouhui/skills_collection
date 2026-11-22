# 图片生成接口（Seedream）

## 调用链路

```
POST /api/v3/images/generations   同步返回图片结果（stream=true 时可流式）
```

Base URL：`https://ark.cn-beijing.volces.com/api/v3`
鉴权：`Authorization: Bearer $ARK_API_KEY`

与视频接口不同，图片接口是**同步**的：一次请求直接拿结果，没有任务 ID 和轮询。

## 请求体字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `model` | string | ✓ | 模型 ID 或推理接入点 ID |
| `prompt` | string | ✓ | 画面描述；做分层时写分层意图与 `<bbox>` 坐标 |
| `image` | string \| string[] | | 参考图。单图生图给字符串，多参考图给数组；URL 或 `data:image/<fmt>;base64,...` |
| `size` | string | | 档位名（`1K` / `1.5K` / `2K`）、像素（`2048x2048`）或 `auto`；默认 2K（5.5/5.0pro/5.0flash）或 2048x2048（旧档） |
| `sequential_image_generation` | string | | `auto` / `disabled`（默认）。仅 5.0 lite / 4.5 / 4.0 |
| `response_format` | string | | `url`（默认，24h 有效）/ `b64_json` |
| `watermark` | bool | | **默认 `true`**，会打"AI生成"水印 |
| `output_format` | string | | `jpeg` / `png`；5.5 支持原生 RGBA |
| `stream` | bool | | 默认 `false`，仅 5.0 lite / 4.5 / 4.0 |
| `tools` | object[] | | 联网搜索等，5.0 lite 有 `tool_usage.web_search` 回显 |
| `optimize_prompt_options` | object | | 提示词优化开关 |
| `background` | string | | 背景/透明控制（5.5） |
| `layer_decomposition` | bool | | 抠图层分离，5.5 / 5.0 pro / 5.0 flash 支持 |
| `layer_decomposition_options` | object | | 分层选项 |
| `safety_identifier` | string | | 终端用户标识 |

## 三种用法

> 图片接口**没有 `ratio` 参数**，画面比例完全由 `size` 的宽高比决定。要竖版就写 `1152x2048` 这类像素值，不要指望像视频那样传比例字段。

### 1. 文生图

```json
{
  "model": "doubao-seedream-5-5-261028",
  "prompt": "雨夜霓虹街头的赛博朋克女黑客，中景，浅景深，冷蓝与紫红打光，电影质感",
  "size": "2K",
  "response_format": "url",
  "watermark": false
}
```

### 2. 单图生图（改风格 / 改场景 / 保持人物）

```json
{
  "model": "doubao-seedream-5-5-261028",
  "prompt": "保持人物五官与发型不变，换成海边黄昏场景，暖色逆光",
  "image": "https://.../hero.png",
  "size": "2K",
  "watermark": false
}
```

本地图片可直接内联（脚本会自动转）：

```
data:image/png;base64,iVBORw0KGgo...
```

格式名用小写，且要与实际图片格式一致。

### 3. 多参考图生图（人物 + 服装 + 场景分别给图）

```json
{
  "model": "doubao-seedream-5-5-261028",
  "prompt": "用@图1的人物穿上@图2的服装，站在@图3的场景中，全身像，自然光",
  "image": ["https://.../hero.png", "https://.../outfit.png", "https://.../scene.png"],
  "size": "2K",
  "watermark": false
}
```

## 返回结构

```json
{
  "model": "doubao-seedream-5-5-261028",
  "created": 1784696685,
  "data": [
    {"url": "https://...", "size": "2048x2048", "output_format": "jpeg"}
  ],
  "usage": {
    "input_images": 1,
    "generated_images": 1,
    "output_tokens": 23107,
    "total_tokens": 23107
  }
}
```

- `data[]` 每项有 `url`（`response_format=url` 时）或 `b64_json`（`response_format=b64_json` 时），另有 `size`、`output_format`；做分层时还有 `z_index`（0 为底图）、`name`、`description`、`bounding_box`。
- 完全没出图时，顶层返回 `error`。
- 计费看 `usage.output_tokens`，算法是 `sum(宽 × 高) / 256`——**尺寸是成本的直接乘数**，同样内容用 2K 和 4K 差 4 倍。

## 拿它当视频首帧的注意点

1. **比例必须提前定**。图生视频时成片比例跟随首帧，所以出图就用最终比例（竖版短视频出 `1024x1536` 这一类，别出完再裁）。
2. **构图留给运动空间**。首帧把主体堆满画面，后续推拉摇移没有余量；中景、留白比大特写更好用。
3. **不要在图里烧文字**，除非确实要固定文案（图里的字再动起来容易糊）。
4. 出图后先看图、再花视频的钱。一套 3 镜头片子，图错一张就废一条视频。
