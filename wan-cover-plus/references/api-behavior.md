# API 与输出行为

这个文件不是 API 教程，而是用于排查**为什么没出图、为什么没出视频、为什么输出不对、为什么不该伪造成功**。

## 什么时候必须读取这个文件

只在以下情况读取：
- 运行脚本时报配置错误
- 你需要确认 `config.yaml` 应该长什么样
- 你需要判断输出目录、prompt sidecar、返回 JSON 是否正常
- 你需要解释为什么 API 调用失败
- 你需要排查视频任务为什么一直轮询、为什么没有 `video_url`

如果只是正常跑标准示例，不要先读这个文件。

---

## 配置键

```yaml
wan:
  api_key: "your_wan_api_key"
  base_url: "https://dashscope.aliyuncs.com/api/v1"
  image_model: "wan2.7-image"
  text_to_video_model: "wan2.7-t2v"
  image_to_video_model: "wan2.7-i2v"
  reference_to_video_model: "wan2.7-r2v"

defaults:
  task_type: "image"
  scene: "wechat_cover"
  style: "tech_media"
  variants: 1
  output_dir: "output"
  video_duration_seconds: 5
  video_resolution: "720P"
  video_aspect_ratio: "16:9"
  video_shot_type: "single"
  video_audio: true

postprocess:
  ffmpeg_bin: "ffmpeg"
  ffprobe_bin: "ffprobe"
  tts_voice: "zh-CN-XiaoxiaoNeural"
  tts_rate: "+0%"
  tts_volume: "+0%"
  subtitle_mode: "burned"
```

---

## 配置判断规则

### `wan.api_key`

这是硬前提。

如果缺失：
- 不要运行后再假装能生成
- 直接告诉用户必须补这个字段

### `wan.base_url`

当前默认对接：

```text
https://dashscope.aliyuncs.com/api/v1
```

如果用户没有特别要求，不要主动改这个值。

### `wan.image_model`

图片任务默认模型：

```text
wan2.7-image
```

### `wan.text_to_video_model`

文生视频默认模型位。

支持常见写法：
- `wan2.6-t2v`
- `wan2.7-t2v`

如果用户在输入 JSON 中显式给了 `model`，则优先使用输入值。

### `wan.image_to_video_model`

静态图转视频默认模型位。

常见可用值：

```text
wan2.7-i2v
wan2.6-i2v-flash
```

### `wan.reference_to_video_model`

参考图 / 参考视频转视频默认模型位。

常见可用值：

```text
wan2.7-r2v
wan2.6-r2v-flash
```

### `defaults.output_dir`

决定图片、视频和 `.prompt.txt` 的默认落盘目录。

如果用户没有指定输出位置，不要手动发明新的目录规则。

---

## 图片任务请求行为

图片任务会向以下地址发起 POST：

```text
{base_url}/services/aigc/multimodal-generation/generation
```

当前关键请求参数包括：
- `prompt_extend: false`
- `watermark: false`
- 按 scene 映射的 `size`

### 图片 scene 与尺寸映射

- `wechat_cover` → `1792x1024`
- `xiaohongshu_cover` → `1024x1792`
- `relayout_poster` → `1024x1792`

如果用户只是换标题，不要顺手改尺寸映射。

---

## 视频任务请求行为

视频任务会向以下地址发起 POST：

```text
{base_url}/services/aigc/video-generation/video-synthesis
```

视频 HTTP 调用是**异步任务模式**。

创建任务时必须带：
- `Authorization: Bearer <API_KEY>`
- `Content-Type: application/json`
- `X-DashScope-Async: enable`

查询任务状态：

```text
GET {base_url}/tasks/{task_id}
```

### i2v 任务（兼容 Wan 2.6 / 2.7）

适合：
- 单张静态图转视频

关键输入：
- Wan 2.6：`img_url`
- Wan 2.7：`media`
- `prompt`（可选但建议有）
- `negative_prompt`（2.6 可选）

#### Wan 2.7 media 结构

```json
"media": [
  { "type": "first_frame", "url": "https://..." }
]
```

常用参数：
- `resolution`: `720P | 1080P`
- `duration`: `2-15`
- `shot_type`: `single | multi`
- `audio`: `true | false`
- `watermark`: `false`

### r2v 任务（兼容 Wan 2.6 / 2.7）

适合：
- 参考图 / 参考视频转视频

关键输入：
- `prompt`
- Wan 2.6：`reference_urls`
- Wan 2.7：`media`

#### Wan 2.7 media 结构

```json
"media": [
  { "type": "reference_image", "url": "https://..." },
  { "type": "reference_video", "url": "https://..." }
]
```

`reference_urls` 可以混合图片和视频，但不要超过 API 支持上限。

常用参数：
- `size`: 由 `resolution + aspect_ratio` 映射出的分辨率
- `duration`: `2-10`
- `shot_type`: `single | multi`
- `audio`: `true | false`
- `watermark`: `false`

---

## 响应行为

### 图片任务

技能支持 2 种图片返回形式：
- 图片 URL
- base64 图片内容

成功时会写出：
- 最终图片文件到 `output/`
- 同名 `.prompt.txt` 文件
- JSON 结果

### 视频任务

视频任务先返回：
- `task_id`
- `task_status: PENDING`

然后需要轮询，直到：
- `SUCCEEDED`
- `FAILED`
- `UNKNOWN`
- 超时

成功时会写出：
- 最终 `.mp4` 文件到 `output/`
- 同名 `.prompt.txt` 文件
- JSON 结果

如果拿不到 `video_url`，不算真正成功。

---

## 如何判断是否真的成功

以下条件都满足，才算真正成功：

1. API 返回成功
2. 图片任务拿到了可解码或可下载的图片内容，或视频任务拿到了 `video_url`
3. 输出文件实际写入成功
4. `.prompt.txt` 文件实际生成
5. JSON 结果中的 `output_files` 指向真实存在的文件

缺任意一项，都不应被表述为“已经成功生成”。

---

## 常见失败

- 缺少 `config.yaml`
- 缺少 `wan.api_key`
- API 返回非 200
- 返回中没有图片 payload
- 视频任务提交成功但最终没有 `video_url`
- 视频轮询超时
- `task_status = FAILED`
- `task_status = UNKNOWN`
- scene/style/task_type 输入非法
- 输出路径写入失败
- 本地参考图或参考视频路径不存在
- URL 无法访问

---

## 排查顺序

### 图片任务
1. 先看 `config.yaml` 是否存在
2. 再看 `wan.api_key` 是否存在
3. 再看 scene/style 是否有效
4. 再看 API 返回是否有图片字段
5. 最后看输出文件是否真的落盘

### 视频任务
1. 先看 `config.yaml` 是否存在
2. 再看 `wan.api_key` 是否存在
3. 再看 task_type / 模型配置是否正确
4. 再看参考图 / 参考视频路径或 URL 是否有效
5. 再看创建任务时是否拿到了 `task_id`
6. 再看轮询是否到了 `SUCCEEDED`
7. 最后确认是否真的拿到了 `video_url` 并落盘成 `.mp4`

---

## NEVER

- **NEVER** 在配置缺失时继续假设脚本可以正常出图或出视频
- **NEVER** 在 API 返回非 200 时把它包装成“只是效果不理想”
- **NEVER** 在没有图片 payload 或没有 `video_url` 时谎称生成成功
- **NEVER** 只看控制台 JSON，不检查输出文件是否真的存在
- **NEVER** 擅自更改模型、base_url 或尺寸映射来碰运气
- **NEVER** 在视频任务轮询失败后还对用户说“已经生成好了”
