# 输入 Schema

这个文件不是给用户看的参数百科，而是给 Claude 判断**什么时候字段足够、什么时候不能乱猜**用的。

## 什么时候必须读取这个文件

只在以下情况读取：
- 用户没有直接给 JSON，而是给自然语言需求
- 你不确定是图片任务还是视频任务
- 你不确定哪些字段必须补齐
- 你在构造输入文件前，不确定最小可运行输入
- 用户给的是零散信息、参考图或参考视频，你不确定是否已经足够运行

如果用户已经给了完整 JSON，**不要为了保险把这个文件再读一遍**。

---

## 一、先判断 `task_type`

优先判断任务类型，而不是直接从 scene 开始。

### `image`
适合：
- 封面图
- 头图
- 种草图
- 海报重排版

### `text_to_video`
适合：
- 用户只有文字描述
- 想直接生成一段短视频
- 没有参考图或参考视频

### `image_to_video`
适合：
- 用户给了一张静态图
- 想让画面“动起来”
- 核心是保留主体、加自然动态

### `reference_to_video`
适合：
- 用户给了参考图或参考视频
- 希望保留主体一致性、风格或动作节奏
- 可以同时带图片和视频参考素材

如果用户明确说“静态图转视频”“图片转视频”，优先 `image_to_video`。

如果用户明确说“参考视频转视频”“按这个参考视频做一个新视频”，优先 `reference_to_video`。

---

## 二、最小可运行输入

### A. 图片任务

以下 3 个字段缺一不可：

```json
{
  "title": "string",
  "scene": "wechat_cover | xiaohongshu_cover | relayout_poster",
  "style": "tech_media | warm_lifestyle | premium_brand | cute_note"
}
```

### B. 文生视频

至少满足下面任一结构：

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

### C. 静态图转视频

```json
{
  "task_type": "image_to_video",
  "title": "string",
  "reference_images": ["/absolute/path/or/url"]
}
```

### D. 参考图 / 参考视频转视频

```json
{
  "task_type": "reference_to_video",
  "title": "string",
  "reference_images": ["/absolute/path/or/url"],
  "reference_videos": ["/absolute/path/or/url"]
}
```

`reference_to_video` 至少要有一类参考素材：
- `reference_images`
- `reference_videos`

二者可以只给其一，也可以同时给。

---

## 三、常用可选字段

```json
{
  "subtitle": "string | null",
  "highlights": ["string"],
  "brand_colors": ["#RRGGBB"],
  "reference_images": ["string"],
  "reference_videos": ["string"],
  "need_variants": 1,
  "need_text_layout": true,
  "edit_instruction": "string | null",
  "prompt": "string | null",
  "negative_prompt": "string | null",
  "duration_seconds": 5,
  "resolution": "720P | 1080P",
  "aspect_ratio": "16:9 | 9:16 | 1:1 | 4:3 | 3:4",
  "model": "string | null",
  "camera_instruction": "string | null",
  "motion_instruction": "string | null",
  "shot_type": "single | multi",
  "audio": false,
  "enable_narration": true,
  "enable_subtitles": true,
  "narration_text": "string | null",
  "subtitle_text": "string | null",
  "subtitle_mode": "burned | sidecar | both",
  "tts_voice": "string | null",
  "tts_rate": "string | null",
  "tts_volume": "string | null"
}
```

---

## 四、字段决策规则

### `title`

图片任务里通常必填。

视频任务里：
- 如果已经有很完整的 `prompt`，可以没有 `title`
- 如果没有 `prompt`，至少要有 `title`

不要为了结构完整而乱补一个标题。

### `prompt`

适合：
- 视频任务需要精确动作、镜头、节奏描述
- 用户已经明确给了完整画面或视频描述

不要乱补，当：
- 用户只给了模糊需求
- 你只能凭空猜视频内容

### `reference_images`

适合：
- 用户明确给了图片路径或 URL
- 任务是 image-to-video
- 任务是 reference-to-video 且需要保留主体特征

不要因为用户说“像这种风格”就伪造图片路径。

### `reference_videos`

适合：
- 用户明确给了参考视频路径或 URL
- 任务是 reference-to-video
- 用户强调保留动作节奏、镜头感或运动方式

不要因为用户说“像短片一样”就伪造视频地址。

### `resolution`

当前只允许：
- `720P`
- `1080P`

如果用户没说，允许按默认值运行，不要自己发明别的分辨率。

### `aspect_ratio`

当前只允许：
- `16:9`
- `9:16`
- `1:1`
- `4:3`
- `3:4`

如果用户没说，视频任务可按默认值运行。

### `duration_seconds`

当前建议范围：
- `2` 到 `15`

如果用户没说，允许用默认值。

### `camera_instruction`

适合：
- 需要明确镜头推进、横移、俯仰或稳定镜头表达

不要乱补，当：
- 用户根本没表达镜头诉求
- 你只能凭空发明复杂调度

### `motion_instruction`

适合：
- 用户明确要丝滑动态、自然动作、轻微动效
- 需要约束“不要乱动、不要夸张变形”

这是视频任务里很有价值的字段，但不要写得过于空泛。

---

## 五、参考素材规则

### 本地路径

支持本地绝对路径，例如：

```text
/mnt/f/tmp/wewrite/2985_4733.png
```

要求：
- 路径真实存在
- 不要猜路径

### URL

也支持 URL，但前提是：
- 链接是可访问的
- 不是你凭空猜出来的地址

如果用户只说“网上有一张图”，不要擅自补一个 URL。

---

## 六、冲突字段处理

### 情况 1：用户给了标题，但没给 `task_type`
- 如果请求明显是封面图/头图/海报改版，默认按图片任务判断
- 如果请求明显是视频，先补 `task_type` 再运行

### 情况 2：用户给了静态图，还说“做一段动态视频”
- 不要走图片 scene
- 优先 `image_to_video`

### 情况 3：用户给了参考视频，还说“参考这个节奏做一个新视频”
- 不要误判成文生视频
- 优先 `reference_to_video`

### 情况 4：用户给了很多卖点，但没有副标题
- 可以没有 `subtitle`
- 不要为了让结构好看硬补一句营销话术

### 情况 5：用户没给品牌色
- 允许留空
- 不要臆造品牌色来让输入“更完整”

---

## 七、推荐构造方式

### 图片任务：公众号封面

```json
{
  "title": "本地蒸馏模型接入 Claude Code 实测",
  "subtitle": "Qwen3.5 9B 已可用，但还不够可托付",
  "highlights": [
    "LM Studio 本地部署",
    "Claude Code 接入实测",
    "9B 与 27B 差异判断"
  ],
  "scene": "wechat_cover",
  "style": "tech_media",
  "brand_colors": ["#0F172A", "#10B981"],
  "reference_images": [],
  "need_variants": 1,
  "need_text_layout": true,
  "edit_instruction": null
}
```

### 视频任务：静态图转视频

```json
{
  "task_type": "image_to_video",
  "title": "静态图转丝滑动态视频",
  "prompt": "保留参考图主体和整体色彩氛围，让画面产生自然的镜头运动和细节动感。",
  "style": "premium_brand",
  "reference_images": [
    "/mnt/f/tmp/wewrite/2985_4733.png"
  ],
  "duration_seconds": 5,
  "resolution": "720P",
  "aspect_ratio": "9:16",
  "shot_type": "single",
  "audio": false
}
```

---

## NEVER

- **NEVER** 在缺 `scene` 时直接运行图片任务
- **NEVER** 在缺 `style` 时让脚本兜底猜图片风格
- **NEVER** 在视频任务缺少参考素材时伪造 `reference_images` 或 `reference_videos`
- **NEVER** 臆造品牌色、参考图路径、参考视频路径或编辑说明
- **NEVER** 因为想让输入“更完整”而补虚构字段
- **NEVER** 用字段完整性覆盖任务真实性
- **NEVER** 把图片 scene 判断规则误套到视频任务上
