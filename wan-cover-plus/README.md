# WanCover+

WanCover+ 是一个基于 Wan 系列模型的 Claude Code Skill，用来把标题、副标题、卖点、品牌色、结构化 JSON、参考图或参考视频，转成可直接交付的**图片或视频**。

它现在支持：
- **图片生成**：公众号封面图、小红书封面图、种草图、海报重排版
- **视频生成**：文生视频、静态图转丝滑动态视频、参考图 / 参考视频转视频
- **视频后处理**：为视频自动补 Edge TTS 配音、SRT 字幕，并支持直接烧录字幕

## 1. 先看哪个文件

推荐阅读顺序：

1. **`SKILL.md`**：Claude 的决策入口，说明什么时候该触发、怎么选 scene、怎么选 `task_type`
2. **`README.md`**：人类使用说明
3. **`references/README.md`**：reference 索引，告诉你该读哪份补充文档
4. **`references/input-schema.md`**：字段怎么构造、哪些字段不能乱猜
5. **`references/scenes.md`**：图片任务的 scene 冲突判断
6. **`references/api-behavior.md`**：配置、API、输出和排错规则

---

## 2. 目录结构

```text
wan-cover-plus/
├── SKILL.md
├── README.md
├── config.example.yaml
├── requirements.txt
├── assets/
├── examples/
├── references/
│   ├── README.md
│   ├── input-schema.md
│   ├── scenes.md
│   └── api-behavior.md
└── scripts/
```

目录说明：
- **`SKILL.md`**：给 Claude 的主入口，只保留决策层信息
- **`README.md`**：给人类的安装和运行说明
- **`examples/`**：正式 demo 输入
- **`references/`**：按需加载的补充判断文档
- **`scripts/`**：实际运行逻辑

---

## 3. 安装依赖

在技能目录下执行：

```bash
pip install -r requirements.txt
```

如果你要启用视频配音和字幕，还需要系统安装：

- `ffmpeg`
- `ffprobe`

---

## 4. 准备配置

先复制示例配置：

```bash
cp config.example.yaml config.yaml
```

然后填写 `config.yaml`，至少要补：

- `wan.api_key`
- `wan.base_url`
- 相关模型配置

推荐配置：

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

说明：
- 默认以 Wan 2.7 为主
- 视频任务兼容 Wan 2.6 / 2.7
- 如果输入 JSON 里显式给了 `model`，优先使用输入值

---

## 5. 标准执行命令

```bash
python3 scripts/generate.py --input <json-file>
```

### 图片 demo

```bash
python3 scripts/generate.py --input examples/demo_wechat_cover.json
python3 scripts/generate.py --input examples/demo_xiaohongshu_cover.json
python3 scripts/generate.py --input examples/demo_relayout_poster.json
```

### 视频 demo

```bash
python3 scripts/generate.py --input examples/demo_text_to_video.json
python3 scripts/generate.py --input examples/demo_image_to_video.json
python3 scripts/generate.py --input examples/demo_reference_to_video.json
```

---

## 6. 输入格式

### 图片任务最小输入

```json
{
  "title": "string",
  "scene": "wechat_cover | xiaohongshu_cover | relayout_poster",
  "style": "tech_media | warm_lifestyle | premium_brand | cute_note"
}
```

### 文生视频最小输入

```json
{
  "task_type": "text_to_video",
  "title": "string"
}
```

或：

```json
{
  "task_type": "text_to_video",
  "prompt": "string"
}
```

### 静态图转视频最小输入

```json
{
  "task_type": "image_to_video",
  "title": "string",
  "reference_images": ["/absolute/path/or/url"]
}
```

### 参考图 / 参考视频转视频最小输入

```json
{
  "task_type": "reference_to_video",
  "title": "string",
  "reference_images": ["/absolute/path/or/url"],
  "reference_videos": ["/absolute/path/or/url"]
}
```

更细的字段判断见 `references/input-schema.md`。

---

## 7. Wan 2.6 / 2.7 视频协议差异

### `wan2.7-i2v`
- Wan 2.6：`input.img_url`
- Wan 2.7：`input.media`
- Wan 2.7 图片媒体类型：`first_frame`

```json
"media": [
  { "type": "first_frame", "url": "https://..." }
]
```

### `wan2.7-r2v`
- Wan 2.6：`input.reference_urls`
- Wan 2.7：`input.media`
- Wan 2.7 图片 / 视频媒体类型：`reference_image` / `reference_video`

```json
"media": [
  { "type": "reference_image", "url": "https://..." },
  { "type": "reference_video", "url": "https://..." }
]
```

---

## 8. 输出结果

脚本会打印 JSON 结果，并将文件写入配置中的输出目录。

### 图片任务输出
- PNG 图片
- 同名 `.prompt.txt` sidecar

### 视频任务输出
- MP4 视频
- 同名 `.prompt.txt` sidecar
- 如果启用后处理，还会额外生成：
  - `.narration.mp3`
  - `.srt`
  - `.narrated.mp4`
  - `.final.mp4`

### 真正成功的判定

以下条件都满足，才算真正成功：
1. API 返回成功
2. 图片任务拿到了可解码或可下载的图片内容，或视频任务拿到了 `video_url`
3. 输出文件实际写入成功
4. `.prompt.txt` 文件实际生成
5. `output_files` 指向真实存在的文件

---

## 9. 常见排查

### 图片任务
1. 先看 `config.yaml` 是否存在
2. 再看 `wan.api_key` 是否存在
3. 再看 scene / style 是否有效
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

更细的行为说明见 `references/api-behavior.md`。

---

## 10. 安装为 Claude Code Skill

如果要安装到真正的技能目录：

```bash
cp -r /mnt/f/tmp/wewrite/WanCoverPlus ~/.claude/skills/wan-cover-plus
```

开发时更推荐软链接：

```bash
ln -s /mnt/f/tmp/wewrite/WanCoverPlus ~/.claude/skills/wan-cover-plus
```

如果是复制安装，别忘了创建本地配置：

```bash
cp ~/.claude/skills/wan-cover-plus/config.example.yaml ~/.claude/skills/wan-cover-plus/config.yaml
```

然后填写 `wan.api_key`。
