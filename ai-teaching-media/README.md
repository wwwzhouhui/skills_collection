# AI 教学媒体一体化 Skill

一个文件夹内包含 6 个可联动子 skill，覆盖教学内容从插图到视频的完整生产链路。

## 包含能力

1. `ai-image-generator`：通用生图执行层
2. `tech-article-diagram`：技术长文智能插图
3. `edu-subject-infographic`：学科知识点竖版信息图
4. `edu-teaching-animation`：教学动图 + 配音教学视频
5. `short-video-cover`：短视频 3:4 封面
6. `article-explainer-video`：长文转章节解说视频

## 推荐使用方式

- 只要安装/启用 `ai-teaching-media` 这一个 skill 目录
- 对话时直接提目标，由总入口 `SKILL.md` 路由到子 skill
- 需要“全套教学资产”时，按总入口里的流水线 A/B/C 串联执行

## 环境变量

- 图片：`MULERUN_API_KEY` / `APIMART_API_KEY` / `ATLASCLOUD_API_KEY` / `AGNES_API_KEY`（设一个即可）
- 配音：`MINIMAX_API_KEY`（可选）或免费 `edge-tts`（`pip install edge-tts`，`--provider edge`）
- 渲染：Node.js ≥ 22 + ffmpeg

## 结构

```text
ai-teaching-media/
├── SKILL.md
├── README.md
├── ai-image-generator/
├── tech-article-diagram/
├── edu-subject-infographic/
├── edu-teaching-animation/
├── short-video-cover/
└── article-explainer-video/
```
