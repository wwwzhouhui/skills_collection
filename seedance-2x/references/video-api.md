# 视频生成接口（Seedance 2.x）

## 调用链路

```
POST /api/v3/contents/generations/tasks   创建任务，同步返回 task id
GET  /api/v3/contents/generations/tasks/{id}   轮询，直到 succeeded/failed
GET  content.video_url                    下载，24 小时内有效
```

Base URL：`https://ark.cn-beijing.volces.com/api/v3`
鉴权：`Authorization: Bearer $ARK_API_KEY`，`Content-Type: application/json`

创建任务是**异步**的，不会当场返回视频。SDK 与官方示例的轮询节奏是每 10 秒一次。

## 请求体字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `model` | string | ✓ | 模型 ID 或推理接入点 ID |
| `content` | object[] | ✓ | 多模态内容数组，见下 |
| `resolution` | string | | `480p` / `720p` / `1080p` / `4k`，默认 `720p` |
| `ratio` | string | | `16:9` `4:3` `1:1` `3:4` `9:16` `21:9` `adaptive`，2.x 默认 `adaptive` |
| `duration` | int | | 秒。2.5: 4–30 或 `-1`；2.0: 4–15 或 `-1` |
| `generate_audio` | bool | | 2.x 默认 `true`。输出恒为立体声 |
| `watermark` | bool | | 默认 `false`；`true` 打"AI生成"水印 |
| `output_format` | string | | `mp4`（默认）/ `mov`，mov 仅 2.5 |
| `omni_reference_task_type` | string | | `auto`(默认) / `reference` / `edit` / `extend`，仅 2.5 |
| `draft` | bool | | `true` 出 480p 试片，仅 2.5；其他分辨率会报错 |
| `return_last_frame` | bool | | `true` 时查询结果多给 `content.last_frame_url` |
| `tools` | object[] | | `[{"type":"web_search"}]`，2.x 支持，用量见 `usage.tool_usage.web_search` |
| `callback_url` | string | | 生产环境用回调替代轮询 |
| `execution_expires_after` | int | | 任务执行超时（秒） |
| `safety_identifier` | string | | 终端用户标识，便于追溯 |
| `priority` | int | | 任务优先级，取值以控制台为准 |

不在上表的参数（如 1.0 的 `seed`、`frames`、`camera_fixed`）对 2.x 无效或会报错。

## content 数组元素

| 类型 | 结构 | 可选 role |
|---|---|---|
| 文本 | `{"type":"text","text":"提示词"}` | — |
| 图片 | `{"type":"image_url","image_url":{"url":"..."},"role":"..."}` | `first_frame` / `last_frame` / `reference_image` |
| 视频 | `{"type":"video_url","video_url":{"url":"..."},"role":"reference_video"}` | `reference_video` |
| 音频 | `{"type":"audio_url","audio_url":{"url":"..."},"role":"reference_audio"}` | `reference_audio` |
| 草稿 | `{"type":"draft_task","draft_task":{"id":"cgt-..."}}` | — |

图片 URL 支持三种写法：公网 https 链接、Base64 `data:image/png;base64,...`、素材库 `asset://<ASSET_ID>`。视频与音频按文档只接受链接形式。

## 五种模式的完整请求

### 1. 文生视频

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [{"type": "text", "text": "雨夜霓虹街头，女黑客转身走进巷子，冷蓝与紫红打光，浅景深"}],
  "resolution": "720p",
  "ratio": "16:9",
  "duration": 5,
  "generate_audio": true,
  "watermark": false
}
```

### 2. 首帧生视频

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "镜头缓慢推近，人物抬头看向窗外，雨滴沿玻璃滑落"},
    {"type": "image_url", "image_url": {"url": "https://.../first.png"}, "role": "first_frame"}
  ],
  "resolution": "1080p",
  "ratio": "adaptive",
  "duration": 5
}
```

`ratio` 必须是 `adaptive`，成片比例跟随首帧。

### 3. 首尾帧生视频

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "人物从门口走到窗边，光线由暖转冷"},
    {"type": "image_url", "image_url": {"url": "https://.../a.png"}, "role": "first_frame"},
    {"type": "image_url", "image_url": {"url": "https://.../b.png"}, "role": "last_frame"}
  ],
  "ratio": "adaptive",
  "duration": 6
}
```

### 4. 全模态参考生视频（2.5）

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "参考@图像1的人物形象与@图像2的服装，参考@视频1的运镜与节奏，背景音乐参考@音频1"},
    {"type": "image_url", "image_url": {"url": "https://.../hero.png"}, "role": "reference_image"},
    {"type": "image_url", "image_url": {"url": "https://.../outfit.png"}, "role": "reference_image"},
    {"type": "video_url", "video_url": {"url": "https://.../ref.mp4"}, "role": "reference_video"},
    {"type": "audio_url", "audio_url": {"url": "https://.../bgm.mp3"}, "role": "reference_audio"}
  ],
  "resolution": "1080p",
  "ratio": "9:16",
  "duration": 10,
  "omni_reference_task_type": "reference"
}
```

### 5. 视频编辑 / 视频延长

编辑（改内容）：

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "编辑视频：把天空改成黄昏色调，其余保持不变"},
    {"type": "video_url", "video_url": {"url": "https://.../in.mp4"}, "role": "reference_video"}
  ],
  "ratio": "adaptive",
  "duration": -1,
  "omni_reference_task_type": "edit",
  "output_format": "mov"
}
```

延长（接时长）：

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [
    {"type": "text", "text": "向后延长5秒，人物继续走向镜头，光线渐暗"},
    {"type": "video_url", "video_url": {"url": "https://.../in.mp4"}, "role": "reference_video"}
  ],
  "ratio": "adaptive",
  "duration": 5,
  "omni_reference_task_type": "extend"
}
```

**编辑模式硬约束**：必须带至少一个 `reference_video`；源片 4–30s；`ratio` 必须 `adaptive`；`duration` 必须 `-1`；成片比例与时长跟随源片（误差 ≤0.4s）。
**延长模式硬约束**：必须带 `reference_video`；`ratio` 必须 `adaptive`；`duration` 填**新增**的秒数（延长 5 秒就填 5），留 `-1` 则模型自定。

### 6. 草稿试片 → 正式片（2.5 专属）

第一步出 480p 试片：

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [{"type": "text", "text": "..."}],
  "draft": true,
  "resolution": "480p"
}
```

第二步用返回的 draft 任务 ID 出正式片：

```json
{
  "model": "doubao-seedance-2-5-260628",
  "content": [{"type": "draft_task", "draft_task": {"id": "cgt-20260414114820-xxxxx"}}],
  "resolution": "1080p"
}
```

`draft: true` 时其他分辨率会报错。2.5 flash 不支持 draft。

## 查询任务返回

```json
{
  "id": "cgt-2026****-****",
  "model": "doubao-seedance-2-0-260128",
  "status": "succeeded",
  "content": {
    "video_url": "https://ark-content-generation-cn-beijing.tos-cn-beijing.volces.com/xxx",
    "last_frame_url": null
  },
  "usage": {"completion_tokens": 108900, "total_tokens": 108900},
  "created_at": 1779348818,
  "updated_at": 1779348874,
  "seed": 78674,
  "resolution": "720p",
  "ratio": "16:9",
  "duration": 5,
  "framespersecond": 24,
  "generate_audio": true,
  "draft": false,
  "error": null
}
```

- `status` 取值：`queued` / `running` / `cancelled` / `succeeded` / `failed` / `expired`。
- `usage.total_tokens` 等于 `completion_tokens`，输入不计 token。计费看这个数。
- `error` 为 `null` 表示成功；失败时含 `code`、`message`。
- `content.last_frame_url` 只在创建时开了 `return_last_frame: true` 才有，是 JPEG、尺寸同视频、无水印。

## 时效与配额

| 对象 | 有效期 |
|---|---|
| 视频下载 URL | 24 小时；Seedance 2.5 单个 URL 下载次数上限 100 |
| 普通任务 ID | 7 天 |
| draft 任务 ID | 2026-10-28 10:00 (UTC+8) 起创建为 14 天，此前 7 天 |

## 常见错误码

| 错误码 | 含义 | 处理 |
|---|---|---|
| `InvalidParameter.TaskTypeMismatch` | 提示词意图与 `omni_reference_task_type` 不符 | 让提示词关键词与 task_type 对齐 |
| `InvalidParameter.TaskTypeConstraint` | 参数组合不满足该任务类型约束 | 按上文硬约束修正 |
| `InvalidParameter` | 分辨率/时长/比例超出该模型范围 | 查 `references/models.md` |
| 鉴权类错误 | key 缺失或无效 | 检查 `ARK_API_KEY` |
| 模型未开通 | 该模型未在控制台开通 | 控制台开通 |
| 内容安全拦截 | 素材或提示词触线 | 换素材；真人脸部素材会被拦 |
