---
name: wan-cover-plus
description: 使用 Wan2.7-image 生成公众号封面图、小红书封面图、种草图和海报改版视觉稿，并支持文生视频、静态图转丝滑动态视频、参考图 / 参考视频转视频，以及为视频自动补 Edge TTS 配音与字幕烧录。视频任务兼容 Wan 2.6 与 Wan 2.7 模型，可通过 config.yaml 默认配置或输入 JSON 的 model 字段覆盖。用于把标题、副标题、卖点、品牌色、结构化 JSON、参考图或参考视频转成真实图片或视频输出；当用户提到封面图、头图、配图、种草图、视觉稿、海报重排版、横版改竖版、文生视频、图片转视频、静态图转动态视频、参考图转视频、参考视频转视频、丝滑动态视频、视频配音、字幕烧录、Edge TTS 配音时，必须优先考虑这个技能。支持 Prompt 构建、场景选择、真实 Wan API 调用、PNG / MP4 文件输出与 prompt sidecar 保存。
---

# WanCover+

WanCover+ 是一个面向**内容视觉生产**的 Claude Code Skill。

它适合两类任务：
- **图片生成**：公众号封面图、小红书封面图、种草图、海报重排版
- **视频生成**：文生视频、静态图转丝滑动态视频、参考图 / 参考视频转视频

## 什么时候必须使用这个技能

当用户的目标是**做图**或**做视频**，而不是单纯写文章、写文案、做摘要时，优先判断是否属于以下任务：

- 公众号封面图
- 文章头图
- 小红书封面
- 种草图
- 海报改版
- 横版改竖版
- 文生视频
- 图片转视频
- 静态图转动态视频
- 参考图转视频
- 参考视频转视频
- 丝滑动态视频

如果用户只是讨论文案，没有明确图片或视频交付目标，不要误触发这个技能。

## 重要：路径解析

这个技能可能安装在不同位置。执行任何命令前，先根据当前加载的 `SKILL.md` 所在目录确定技能根目录，然后把下文中的 `<SKILL_DIR>` 替换成实际路径。

---

## 一、图片任务：先判断任务性质，再选场景

### 第一步：判断是“从零出图”还是“改已有视觉”

- 如果用户重点是“根据标题/卖点生成一张图”，按**从零出图**处理
- 如果用户重点是“保留原主体 / 保留信息层级 / 横改竖 / 重排版”，按**改已有视觉**处理

这个判断优先级高于平台词。

### 第二步：再判断目标平台或传播形态

- 横版文章头图、公众号封面、技术媒体头图 → `wechat_cover`
- 竖版信息流封面、小红书封面、种草图 → `xiaohongshu_cover`
- 保留原视觉结构并改版 → `relayout_poster`

### 图片 scene 冲突裁决表

| 冲突输入 | 正确处理 |
|---|---|
| “小红书封面” + “保留原海报主体” | 优先 `relayout_poster`，因为任务本质是改版，不是从零出图 |
| “公众号头图” + “竖版传播” | 先确认平台目标；如果最终是社媒竖版卡片，优先 `xiaohongshu_cover` |
| “做个封面” + “横版改竖版” | 优先 `relayout_poster` |
| “技术文章头图” + “给我更像小红书一点” | 优先看最终分发平台；公众号发文优先 `wechat_cover`，小红书分发优先 `xiaohongshu_cover` |
| “就用这个标题出图” + “保留信息层级” | 如果没有旧视觉结构，仍是从零出图，不要误选 `relayout_poster` |

---

## 二、视频任务：先判断 `task_type`

视频任务不要误走图片 scene 路由，优先按 `task_type` 判断。

### `text_to_video`
适合：
- 用户只给文字描述
- 想直接生成一段产品演示、氛围片、短视频片段
- 没有参考图或参考视频也能跑

### `image_to_video`
适合：
- 用户明确给了一张静态图
- 想让静态图“动起来”
- 重点是保留主体、加轻微镜头运动和自然动态
- 默认模型位：`wan2.7-i2v`
- 也兼容：`wan2.6-i2v-flash`
- 协议差异：Wan 2.6 用 `input.img_url`，Wan 2.7 用 `input.media`，图片类型为 `first_frame`

### `reference_to_video`
适合：
- 用户有参考图或参考视频
- 希望保留主体一致性、参考素材风格或动作节奏
- 可接受本地路径或 URL
- 默认模型位：`wan2.7-r2v`
- 也兼容：`wan2.6-r2v-flash`
- 协议差异：Wan 2.6 用 `input.reference_urls`，Wan 2.7 用 `input.media`，图片 / 视频类型分别为 `reference_image` / `reference_video`

### 视频任务的判断原则

- **只有静态图** → 优先 `image_to_video`
- **有参考图或参考视频，希望保留参考特征** → 优先 `reference_to_video`
- **没有任何参考素材，只有文字创意** → `text_to_video`

---

## 三、最小输入判断

只保留最小判断，不在主文件里展开完整字段手册。

### 图片任务
至少要能确定：
- `title`
- `scene`
- `style`

### 视频任务
- `text_to_video`：至少有 `title` 或 `prompt`
- `image_to_video`：至少有 `reference_images`
- `reference_to_video`：至少有 `reference_images` 或 `reference_videos`

如果字段不确定，不要猜，转去读 `references/input-schema.md`。

---

## 四、什么时候读 reference

- **字段不确定时**：读 `references/input-schema.md`
- **图片 scene 不确定时**：读 `references/scenes.md`
- **API / 输出 / 配置 / 成功判定不确定时**：读 `references/api-behavior.md`

不要一次性把所有 references 全读一遍。

- 只是图片生成，不要把视频排查说明一起加载
- 只是视频生成，不要把 `scenes.md` 当视频路由文档
- 用户已给完整 JSON 时，不要为了保险重读字段手册

---

## 五、如何判断是否真的成功

以下条件都满足，才算真正成功：

1. API 返回成功
2. 图片任务拿到了可解码或可下载的图片内容，或视频任务拿到了 `video_url`
3. 输出文件实际写入成功
4. `.prompt.txt` 文件实际生成
5. JSON 里的 `output_files` 指向真实存在的文件

缺任意一项，都不应被表述为“已经成功生成”。

---

## NEVER 列表

- **NEVER** 在缺少 `wan.api_key` 时假装可以正常生成图片或视频
- **NEVER** 在用户没有要求出图或出视频时误触发这个技能
- **NEVER** 把 `relayout_poster` 当成所有视觉任务的默认兜底场景
- **NEVER** 在字段不完整时臆造品牌色、参考图、参考视频、URL 或编辑指令
- **NEVER** 把视频任务错路由到图片 scene 上
- **NEVER** 在 API 返回失败时伪造“生成成功”的结果
- **NEVER** 在没有真正拿到 `.png` 或 `.mp4` 文件时声称任务完成
- **NEVER** 把 `config.example.yaml` 当成真实配置直接使用后又不提醒用户补 key
- **NEVER** 为了凑效果擅自改变用户的核心主题、参考素材或任务类型

---

## 参考文档

- `references/README.md`
- `references/input-schema.md`
- `references/scenes.md`
- `references/api-behavior.md`
