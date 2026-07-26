---
name: ai-teaching-media
description: |
  AI 教学媒体一体化技能包。在一个 skill 内串联 6 个子能力：通用生图执行层、技术长文智能插图、学科知识点竖版信息图、教学动图+配音教学视频、短视频 3:4 封面、长文章节解说视频。当用户需要给文章配图、做学科信息图、教学动图/视频、短视频封面、文章转解说视频，或希望从知识点/文章一路产出图文视频全套教学资产时使用。触发词包括：教学媒体、文章配图、技术长文插图、学科信息图、教学动图、教学视频、短视频封面、文章转视频、解说视频、知识卡片、配音讲解、3:4 封面。不要用于与教学/内容可视化无关的纯代码修改。
---

# AI 教学媒体一体化 Skill

把“内容理解 → 插图/信息图 → 动图/视频 → 封面/成片”收成一个可联动技能包。用户安装本目录即可使用全部 6 个子 skill，并按场景串成完整教学生产链路。

## 目录结构

```text
ai-teaching-media/
├── SKILL.md                      # 总入口与路由
├── README.md                     # 使用说明
├── ai-image-generator/           # ① 通用生图执行层
├── tech-article-diagram/         # ② 技术长文智能插图
├── edu-subject-infographic/      # ③ 学科知识点竖版信息图
├── edu-teaching-animation/       # ④ 教学动图 + 配音教学视频
├── short-video-cover/            # ⑤ 短视频 3:4 封面
└── article-explainer-video/      # ⑥ 长文转章节解说视频
```

## 6 个子 skill 一览

| 子 skill | 作用 | 典型输入 | 输出 |
|---------|------|----------|------|
| `ai-image-generator` | 生图执行层（被其它子 skill 调用） | prompt / 参考图 | PNG |
| `tech-article-diagram` | 技术长文智能插图（7 风格） | Markdown 长文 | 16:9 插图 |
| `edu-subject-infographic` | 学科知识点信息图 | 知识点名称 | 9:16 信息图 |
| `edu-teaching-animation` | 教学动图 + 配音视频 | 学科概念 | 无声 MP4 / 配音 MP4 |
| `short-video-cover` | 短视频竖版封面 | 口播文案 | 3:4 封面图 |
| `article-explainer-video` | 长文章节解说视频 | 技术文章 | 1080p MP4 |

## 如何选择能力（路由）

收到用户请求后，先判断意图，再进入对应子 skill 的 `SKILL.md`：

1. **只生图 / 批量生图 / 带参考图修图**  
   → 读 `ai-image-generator/SKILL.md`
2. **给技术长文加插图、流程图、架构图、对比图**  
   → 读 `tech-article-diagram/SKILL.md`  
   → 生图时调用 `ai-image-generator`
3. **做一个知识点信息图 / 知识卡片 / 学科图解**  
   → 读 `edu-subject-infographic/SKILL.md`  
   → 生图时调用 `ai-image-generator`
4. **教学动图、无声循环、配音教学视频**  
   → 读 `edu-teaching-animation/SKILL.md`
5. **视频号/抖音/小红书 3:4 封面**  
   → 读 `short-video-cover/SKILL.md`  
   → 生图时调用 `ai-image-generator`
6. **把整篇文章做成章节解说视频**  
   → 读 `article-explainer-video/SKILL.md`  
   → 复用 `tech-article-diagram` + `ai-image-generator`

如果用户目标是“整套教学产出”，不要只做一个单点结果，按下面流水线串联。

## 推荐串联流水线

### 流水线 A：知识点 → 全套教学资产

适用：用户给一个知识点（如“勾股定理”“光合作用”）

```text
1) edu-subject-infographic
   产出 9:16 学科信息图（可先确认色系/年级）
2) edu-teaching-animation
   同主题产出：无声循环动图 + 配音教学视频
3) short-video-cover
   用口播文案/标题生成 3:4 短视频封面
```

交付建议：
- 信息图 PNG
- 无声动图 MP4（公众号内嵌）
- 配音教学视频 MP4
- 短视频封面 PNG

### 流水线 B：技术长文 → 图文 + 解说视频

适用：用户给一篇技术长文 / 教程 Markdown

```text
1) tech-article-diagram
   识别 4-5 个插图位，生成 16:9 概念/流程/对比/架构图
2) article-explainer-video
   文章分镜 → 章节插图 → TTS → HyperFrames 成片
3) short-video-cover（可选）
   为成片做竖版封面
```

交付建议：
- 插图清单 + PNG
- 章节解说视频 MP4
- 可选短视频封面

### 流水线 C：口播/短视频发布包

适用：用户已有口播稿或教学视频脚本

```text
1) short-video-cover
   生成 3:4 封面
2) 若还缺讲解视频：
   - 单概念 → edu-teaching-animation
   - 长文讲解 → article-explainer-video
```

## 执行原则

1. **先路由，再执行**：总是先读对应子 skill 的 `SKILL.md`，不要跳过子 skill 约束。
2. **保持同主题一致**：同一知识点/文章的信息图、动图、视频尽量复用同一套主题色与术语。
3. **底层生图统一走** `ai-image-generator`：其它 skill 负责策划与 prompt，不重复实现 API。
4. **跨 skill 脚本路径**：子 skill 之间以相对路径调用，例如：
   - `../ai-image-generator/scripts/generate.py`
   - `../tech-article-diagram/scripts/inject_style.py`
5. **缺依赖时先说明**：图片 API key / Minimax / Node+ffmpeg 未就绪时，先告知用户，不要静默失败。

## 环境依赖

| 能力 | 依赖 |
|------|------|
| 生图类（①②③⑤，以及 ⑥ 的插图） | `MULERUN_API_KEY` 或 `APIMART_API_KEY` 或 `ATLASCLOUD_API_KEY` 或 `AGNES_API_KEY` |
| 配音视频（④⑥） | `MINIMAX_API_KEY`（可选）或免费 `edge-tts`（`pip install edge-tts`） |
| 视频渲染（④⑥） | Node.js ≥ 22、ffmpeg、HyperFrames（`npx` 获取） |

## 快速触发示例

```text
# 单点
帮这篇文章加几张插图，用 notebook 风格
做一张“声现象”学科信息图
把勾股定理做成教学动图和配音视频
给这段口播做个 3:4 短视频封面
把这篇文章转成章节解说视频

# 串联
围绕“光合作用”产出全套教学资产：信息图 + 动图 + 配音视频 + 封面
把这篇 Claude Code 教程做成插图版文章，并再出一版解说视频和封面
```

## 子 skill 入口

- `ai-image-generator/SKILL.md`
- `tech-article-diagram/SKILL.md`
- `edu-subject-infographic/SKILL.md`
- `edu-teaching-animation/SKILL.md`
- `short-video-cover/SKILL.md`
- `article-explainer-video/SKILL.md`

开始任务时：先根据用户目标选择上面的路由或流水线，再进入对应子 skill 严格执行。
