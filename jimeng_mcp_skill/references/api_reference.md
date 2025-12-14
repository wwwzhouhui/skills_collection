# 即梦 MCP 服务器 API 参考

jimeng-mcp-server 工具的完整 API 文档。

## 概述

jimeng-mcp-server 提供四个主要工具用于 AI 驱动的视觉内容生成：

1. **text_to_image** - 从文本描述生成图像
2. **image_composition** - 合并和混合多张图片
3. **text_to_video** - 从文本提示创建视频
4. **image_to_video** - 为静态图像添加动画

所有工具返回包含生成内容 URL 的 JSON 响应。

---

## 工具：text_to_image

使用即梦 4.5 引擎从文本描述生成高质量图像。

### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|-----------|------|----------|---------|-------------|
| `prompt` | string | 是 | - | 期望图像的文本描述 |
| `model` | string | 否 | "jimeng-4.5" | 使用的模型版本 |
| `ratio` | string | 否 | "1:1" | 图像宽高比 |
| `resolution` | string | 否 | "2k" | 分辨率预设 |
| `negativePrompt` | string | 否 | "" | 要在生成图像中避免的元素 |

### 支持的宽高比（ratio）

| ratio 值 | 说明 | 适用场景 |
|----------|------|----------|
| "1:1" | 正方形 | 头像、图标、社交媒体帖子 |
| "4:3" | 标准横向 | 通用图片、博客配图 |
| "3:4" | 标准竖向 | 人像照片、手机壁纸 |
| "16:9" | 宽屏横向 | 视频封面、Banner |
| "9:16" | 宽屏竖向 | 手机竖屏、短视频封面 |
| "3:2" | 经典横向 | 摄影作品 |
| "2:3" | 经典竖向 | 海报、杂志封面 |

### 支持的分辨率（resolution）

| resolution 值 | 说明 | 推荐场景 |
|---------------|------|----------|
| "1k" | 标准分辨率 | 快速预览、网页小图 |
| "2k" | 高清分辨率（推荐） | 通用使用、社交媒体 |
| "4k" | 超高清分辨率 | 印刷品、高质量展示 |

### 示例请求

```json
{
  "model": "jimeng-4.5",
  "prompt": "一个宁静的日式花园，有樱花、锦鲤池塘和传统石灯笼，黄昏时分",
  "ratio": "16:9",
  "resolution": "2k",
  "negativePrompt": "人物, 现代建筑"
}
```

### 示例响应

```json
{
  "created": 1765202702,
  "data": [
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    },
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    },
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    },
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    }
  ]
}
```

### 错误响应

```json
{
  "success": false,
  "error": "API key not configured",
  "code": "AUTH_ERROR"
}
```

**常见错误代码：**
- `AUTH_ERROR`：API 密钥无效或缺失
- `INVALID_PARAMS`：参数值无效
- `QUOTA_EXCEEDED`：已达每日积分限制
- `GENERATION_FAILED`：图像生成失败
- `SERVER_ERROR`：后端服务器错误

---

## 工具：image_composition

通过智能融合合并和混合多张图片。

### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|-----------|------|----------|---------|-------------|
| `prompt` | string | 是 | - | 如何合成图片的描述 |
| `images` | array[string] | 是 | - | 要合成的 2-5 个图片 URL 数组 |
| `model` | string | 否 | "jimeng-4.5" | 使用的模型版本 |
| `ratio` | string | 否 | "1:1" | 输出图像宽高比 |
| `resolution` | string | 否 | "2k" | 分辨率预设 |

### 支持的宽高比（ratio）

| ratio 值 | 说明 |
|----------|------|
| "1:1" | 正方形输出 |
| "4:3" | 标准横向 |
| "3:4" | 标准竖向 |
| "16:9" | 宽屏横向 |
| "9:16" | 宽屏竖向 |

### 支持的分辨率（resolution）

| resolution 值 | 说明 |
|---------------|------|
| "1k" | 标准分辨率 |
| "2k" | 高清分辨率（推荐） |
| "4k" | 超高清分辨率 |

### 图片 URL 要求

- 必须是公开可访问的 HTTP/HTTPS URL
- 支持的格式：JPG、PNG、WebP
- 最大文件大小：每张图片 10MB
- 相似分辨率的图片效果最好

### 示例请求

```json
{
  "model": "jimeng-4.5",
  "prompt": "将图片1中的人像主体无缝融合到图片2的山景中，保持自然光照",
  "images": [
    "https://example.com/portrait.jpg",
    "https://example.com/mountain.jpg"
  ],
  "ratio": "4:3",
  "resolution": "2k"
}
```

### 示例响应

```json
{
  "created": 1765173538,
  "data": [
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    },
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    },
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    },
    {
      "url": "https://p3-dreamina-sign.byteimg.com/..."
    }
  ]
}
```

### 错误响应

```json
{
  "success": false,
  "error": "Invalid image URL: https://example.com/invalid.jpg",
  "code": "INVALID_IMAGE_URL"
}
```

**常见错误代码：**
- `INVALID_IMAGE_URL`：一个或多个图片 URL 不可访问
- `UNSUPPORTED_FORMAT`：不支持的图片格式
- `IMAGE_TOO_LARGE`：图片超过大小限制
- `TOO_FEW_IMAGES`：提供的图片少于 2 张
- `TOO_MANY_IMAGES`：提供的图片超过 5 张

---

## 工具：text_to_video

从文本描述创建短视频。

### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|-----------|------|----------|---------|-------------|
| `prompt` | string | 是 | - | 视频场景的文本描述 |
| `model` | string | 否 | "jimeng-video-3.0" | 使用的视频模型版本 |
| `ratio` | string | 否 | "16:9" | 视频宽高比 |
| `resolution` | string | 否 | "720p" | 预设分辨率 |

### 支持的宽高比（ratio）

| ratio 值 | 说明 | 适用场景 |
|----------|------|----------|
| "16:9" | 宽屏横向（推荐） | 视频平台、YouTube |
| "9:16" | 宽屏竖向 | 短视频、抖音 |
| "4:3" | 标准横向 | 通用视频 |
| "3:4" | 标准竖向 | 社交媒体 |
| "1:1" | 正方形 | Instagram |

### 分辨率预设（resolution）

| resolution 值 | 说明 | 使用场景 |
|---------------|------|----------|
| "480p" | 标准清晰度 | 快速预览、测试 |
| "720p" | 高清（推荐） | 平衡质量/速度 |
| "1080p" | 全高清 | 高质量、生成较慢 |

### 视频特性

- **时长**：通常 3-5 秒（由 API 固定）
- **格式**：MP4
- **帧率**：24-30 fps
- **生成时间**：30-60 秒
- **文件大小**：通常 1-5 MB

### 示例请求

```json
{
  "model": "jimeng-video-3.0",
  "prompt": "一只金毛寻回犬幼犬在阳光明媚的公园里玩红色球，慢动作，电影感",
  "ratio": "16:9",
  "resolution": "720p"
}
```

### 示例响应

```json
{
  "success": true,
  "video_url": "https://p3-dreamina-sign.byteimg.com/...mp4",
  "metadata": {
    "width": 1280,
    "height": 720,
    "duration": 4.5,
    "fps": 30,
    "format": "mp4",
    "generation_time": 45.2
  }
}
```

### 错误响应

```json
{
  "success": false,
  "error": "Video generation timeout after 90 seconds",
  "code": "GENERATION_TIMEOUT"
}
```

**常见错误代码：**
- `GENERATION_TIMEOUT`：视频生成时间过长
- `INVALID_RESOLUTION`：不支持的分辨率预设
- `QUOTA_EXCEEDED`：已达每日视频积分限制
- `GENERATION_FAILED`：视频生成失败

---

## 工具：image_to_video

为静态图像添加运动和动画效果。

### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|-----------|------|----------|---------|-------------|
| `prompt` | string | 是 | - | 期望动画效果的描述 |
| `file_paths` | array[string] | 是 | - | 要添加动画的图片 URL 数组（1-3 张图片） |
| `model` | string | 否 | "jimeng-video-3.0" | 使用的视频模型版本 |
| `ratio` | string | 否 | "16:9" | 视频宽高比 |
| `resolution` | string | 否 | "720p" | 预设分辨率 |

### 支持的宽高比（ratio）

| ratio 值 | 说明 |
|----------|------|
| "16:9" | 宽屏横向（推荐） |
| "9:16" | 宽屏竖向 |
| "4:3" | 标准横向 |
| "3:4" | 标准竖向 |
| "1:1" | 正方形 |

### 分辨率预设（resolution）

| resolution 值 | 说明 |
|---------------|------|
| "480p" | 标准清晰度 |
| "720p" | 高清（推荐） |
| "1080p" | 全高清 |

### 动画类型

**镜头运动：**
- 平移（水平/垂直移动）
- 缩放（放大/缩小）
- 推拉（前进/后退移动）
- 环绕（围绕主体的圆周运动）

**主体动画：**
- 人物动作（行走、手势）
- 物体运动（摇摆、旋转）
- 自然效果（头发/衣服在风中飘动）

**环境效果：**
- 天气（雨、雪、风）
- 光照变化（白天到夜晚）
- 粒子效果（闪光、烟雾）

### 示例请求

```json
{
  "model": "jimeng-video-3.0",
  "prompt": "添加轻柔的镜头缩放和细微的人像主体运动，电影感",
  "file_paths": ["https://example.com/portrait.jpg"],
  "ratio": "16:9",
  "resolution": "720p"
}
```

### 示例响应

```json
{
  "success": true,
  "video_url": "https://p3-dreamina-sign.byteimg.com/...mp4",
  "metadata": {
    "source_image": "portrait.jpg",
    "width": 1280,
    "height": 720,
    "duration": 3.8,
    "generation_time": 38.6
  }
}
```

### 错误响应

```json
{
  "success": false,
  "error": "Image URL not accessible: https://example.com/missing.jpg",
  "code": "IMAGE_NOT_ACCESSIBLE"
}
```

**常见错误代码：**
- `IMAGE_NOT_ACCESSIBLE`：源图片 URL 无效或不可访问
- `UNSUPPORTED_IMAGE_FORMAT`：不支持该图片格式的动画
- `GENERATION_FAILED`：动画生成失败

---

## 速率限制和配额

### 免费层限制

- **每日积分**：每天 66 积分（官方即梦 API）
- **图像生成**：每张图片约 1 积分
- **视频生成**：每个视频约 3-5 积分
- **速率限制**：每分钟约 10 个请求

### 积分消耗

| 操作 | 典型成本 |
|-----------|-------------|
| 文本生成图像 (1024x1024) | 1 积分 |
| 图像合成 (2 张图片) | 1-2 积分 |
| 文本生成视频 (720p, 5秒) | 3-5 积分 |
| 图像生成视频 (720p, 3秒) | 2-4 积分 |

**注意**：更高的分辨率和更长的视频消耗更多积分。

### 配额管理

通过即梦网站仪表板监控使用情况。积分在 UTC 午夜每天重置。

---

## 响应时间指南

| 操作 | 典型时间 | 最长时间 |
|-----------|-------------|--------------|
| 文本生成图像 | 10-20 秒 | 30 秒 |
| 图像合成 | 15-30 秒 | 45 秒 |
| 文本生成视频 | 30-60 秒 | 90 秒 |
| 图像生成视频 | 20-50 秒 | 75 秒 |

**影响速度的因素：**
- 分辨率（越高越慢）
- 提示词的复杂度
- 服务器负载
- 网络延迟

---

## 错误处理最佳实践

### 重试策略

```python
max_retries = 3
retry_delay = 5  # 秒

for attempt in range(max_retries):
    try:
        result = generate_image(prompt)
        break
    except TimeoutError:
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
            continue
        else:
            raise
```

### 错误恢复

1. **连接错误** → 验证服务器状态，重试
2. **身份验证错误** → 检查 API 密钥，如需要则刷新
3. **配额错误** → 等待每日重置，使用替代服务
4. **生成错误** → 简化提示词，尝试不同参数
5. **超时错误** → 降低分辨率，增加超时限制

---

## 高级功能

### 批量处理

虽然不直接支持，但可以按顺序处理多个请求：

```python
prompts = ["提示词1", "提示词2", "提示词3"]
results = []

for prompt in prompts:
    result = text_to_image(prompt)
    results.append(result)
    time.sleep(2)  # 速率限制
```

### 缓存结果

考虑缓存生成的内容 URL 以避免重新生成相同的请求：

```python
cache = {}

def generate_with_cache(prompt):
    if prompt in cache:
        return cache[prompt]

    result = text_to_image(prompt)
    cache[prompt] = result
    return result
```

### 并行请求

**不推荐**：jimeng-mcp-server 按顺序处理请求。并行请求可能会使后端过载或达到速率限制。

---

## API 版本控制

当前 API 版本：**v1**

重大变更将导致新版本号。查看项目发布页面了解更新：
https://github.com/wwwzhouhui/jimeng-mcp-server/releases

---

## 其他资源

- **GitHub 仓库**：https://github.com/wwwzhouhui/jimeng-mcp-server
- **后端 API**：https://github.com/wwwzhouhui/jimeng-free-api-all
- **即梦官网**：https://jimeng.jianying.com/
- **问题跟踪**：https://github.com/wwwzhouhui/jimeng-mcp-server/issues

---

**最后更新**：2025-12-14
**API 版本**：2.0（支持 ratio/resolution 新参数）
