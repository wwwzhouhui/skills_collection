---
name: seedance-2x
description: 调用火山方舟 Seedance 2.5 / 2.0 系列生成视频，配合 Seedream 5.5 / 5.0 生成图片。当用户要做文生视频、图生视频、首尾帧视频、参考图生视频、视频编辑、视频延长，或"先文生图再图生视频"的成片流程时使用。内置模型选型表、参数约束校验、可直接运行的 Node 调用脚本。
---

# Seedance 2.x + Seedream 成片技能包

## 适用判断

- 用户说"生成一段视频""把这张图做成视频""用参考图/参考视频做片""把视频改一下/延长"→ 用本技能的视频部分。
- 用户说"先出一张图再让它动起来""做分镜首帧"→ 用本技能的图片部分 + 视频部分串联。
- 只是要写提示词、不上 API → 提示词深水区交给 `seedance-prompt-zh` / `seedance-prompt-en`，本技能只给结构和可直接用的模板。

Seedance 是**纯视频模型**，本身不产图。文生图走同平台的 Seedream（Doubao-Seedream 系列），这是两条独立接口。

## 选型速查

### 视频（`/contents/generations/tasks`）

| 需求 | 模型 ID | 理由 |
|---|---|---|
| 默认首选 | `doubao-seedance-2-5-260628` | 4–30s、1080p/4K、可带音频入参、参考上限 30 图 |
| 快速试片 / 控成本 | `doubao-seedance-2-5-flash-261115` | 同代能力，480p/720p，参考上限 10 图 |
| 沿用 2.0 先例 / 老脚本 | `doubao-seedance-2-0-260128` | 4–15s，1080p/4K，参考上限 9 图 |
| 2.0 批量便宜档 | `doubao-seedance-2-0-fast-260128`、`doubao-seedance-2-0-mini-260615` | 480p/720p，4–15s |

`doubao-seedance-1-0-pro-250528`、`doubao-seedance-1-0-pro-fast-251015` 官方标"即将下线"，不要用于新项目。

### 图片（`/images/generations`）

| 需求 | 模型 ID | 说明 |
|---|---|---|
| 默认首选 | `doubao-seedream-5-5-261028` | 1K/1.5K/2K，最多 10 张参考图，支持分层与 RGBA |
| 高并发/便宜 | `doubao-seedream-5-0-flash-260915` | 1K/1.5K/2K，10 张参考图 |
| 质量优先 | `doubao-seedream-5-0-pro-260628` | 1K/1.5K/2K，10 张参考图 |

`doubao-seedream-4-0-250828`、`4-5-251128`、`5-0-260128`(lite) 官方标"即将下线"，且是唯一支持"一次调用出多图"的几档；新项目按单次单图设计。

## 两条主流程

### A. 文生图 → 图生视频（推荐，可控性最高）

```
1. Seedream 出首帧  → 挑图（构图/人物/风格对了再往下走）
2. 首帧作为 first_frame 提交视频任务
3. 轮询取 video_url → 24h 内下载落地
4. 多镜头时开 return_last_frame，用上一镜尾帧接下一镜首帧
```

### B. 纯文生视频

```
1. 直接文本提交（ratio 留 `adaptive` 让模型判，或显式给 9:16 / 16:9 等）
2. 4–30s（2.5）/ 4–15s（2.0）；分辨率是成本的主要杠杆
```

## 脚本用法

零依赖 Node（本机 Node v24 自带 fetch），无需 npm install。

```bash
S="C:/Users/75271/.agents/skills/seedance-2x/scripts/ark-media.mjs"

# 文生图（比例由 --size 的像素决定，图片接口没有 ratio 参数）
node "$S" img --prompt "雨夜霓虹街头的赛博朋克女黑客，中景，浅景深" \
  --size 2048x1152 --no-watermark --out ./out

# 图生图（用参考图保持人物一致）
node "$S" img --prompt "同一个人物，改成海边黄昏" --ref ./hero.png --out ./out

# 图生视频（首帧；文件名用上一步实际产出的那个）
node "$S" vid --prompt "镜头缓慢推近，人物抬头看向窗外" \
  --first ./out/img-20261117-231500-0.jpeg --res 1080p --dur 5 --no-audio --out ./out

# 首尾帧
node "$S" vid --prompt "从门口走到窗边" --first ./a.png --last ./b.png --dur 6

# 参考图/参考视频生视频（2.5 全模态）
node "$S" vid --prompt "参考@图像1的人物，参考@视频1的运镜" \
  --ref-img ./hero.png --ref-video https://example.com/ref.mp4 --task-type reference

# 视频编辑 / 延长
node "$S" vid --prompt "编辑视频：把天空改成黄昏色调" --ref-video https://example.com/in.mp4 --task-type edit
node "$S" vid --prompt "向后延长5秒，人物继续走向镜头" --ref-video https://example.com/in.mp4 --task-type extend --dur 5

# 先出 480p 试片再出正式片
node "$S" vid --prompt "..." --draft --out ./out                        # 打印出 draft 任务 ID
node "$S" vid --draft-from <draftId> --res 1080p --out ./out

# 只生成请求体不花钱（无 key 也能跑，用于校验）
node "$S" vid --prompt "..." --first ./a.png --dry-run

# 查询/续接已有任务
node "$S" task <taskId> --out ./out
```

鉴权：把 `.env.example` 复制成技能根目录的 `.env` 填 `ARK_API_KEY`；或直接设同名环境变量（环境变量优先）。网关可用 `ARK_BASE_URL` 覆盖，默认 `https://ark.cn-beijing.volces.com/api/v3`。

本地文件处理：**图片**可传本地路径，脚本自动转 base64 data URL；**视频/音频**必须给公网 URL，脚本遇到本地路径会直接报错（不做上传，避免假装成功）。

## 会花钱的坑，先看这张表

| 坑 | 事实 | 规避 |
|---|---|---|
| 图片默认加水印 | 图片接口 `watermark` 默认 **true**（打"AI生成"） | 正式图传 `--no-watermark` |
| 视频默认出音频 | 视频接口 `generate_audio` 默认 **true**（2.5/2.0） | 不要声音传 `--no-audio`，否则白算音频 token |
| 视频默认不加水印 | 视频 `watermark` 默认 **false** | 需要标"AI生成"才传 `--watermark` |
| 时长默认是自动 | 2.5 `duration` 默认 `-1`（模型自己定） | 明确要几秒就显式给 `--dur` |
| 比例默认自适应 | 2.x `ratio` 默认 `adaptive` | 要发抖音/小红书就显式 `9:16` |
| 链接会过期 | 产出 URL 24 小时失效，Seedance 2.5 下载次数上限 100 | 生成后立刻下载，别挂在链接上 |
| 任务 ID 会过期 | 普通任务 7 天，draft 任务 14 天 | draft 试片别拖两周再出正式片 |

## 模式互斥与硬约束

首帧、首尾帧、全模态参考**三种模式互斥，不能混用**。

| 模式 | 触发条件 | 硬约束 |
|---|---|---|
| 文生视频 | 只有文本 | — |
| 首帧 | 1 张 `first_frame` | 比例跟随首帧，`ratio` 须 `adaptive` |
| 首尾帧 | `first_frame` + `last_frame` | `ratio` 须 `adaptive` |
| 全模态参考 | all `reference_image/video/audio` | 2.0 系列不能只给音频 |
| 视频编辑 `edit` | 必须 ≥1 个 `reference_video` | `ratio=adaptive`、`duration=-1`、源片 4–30s、输出比例时长跟随源片（误差 ≤0.4s） |
| 视频延长 `extend` | 必须 1 个 `reference_video` | `ratio=adaptive`、`duration` 给**新增**时长 |

`omni_reference_task_type`（`auto`/`reference`/`edit`/`extend`）只有 2.5 系列支持。模型判出的类型与你指定的不符会报 `InvalidParameter.TaskTypeMismatch`；参数组合违规报 `InvalidParameter.TaskTypeConstraint`。所以：**提示词里带"编辑/增加/删除/替换"就配 `edit`，带"延长/续写"就配 `extend`**。

## 报错对照

| 现象 | 原因 | 处理 |
|---|---|---|
| `InvalidParameter.TaskTypeMismatch` | 提示词意图与 task_type 不符 | 改提示词关键词，或改 task_type |
| `InvalidParameter.TaskTypeConstraint` | 参数组合违规（如 edit 给了 duration≠-1） | 按上表改参数，脚本已做前置校验 |
| 401 / `AuthenticationError` | `ARK_API_KEY` 未设或失效 | 设环境变量后重跑 |
| 403 / 模型未开通 | 该模型未在控制台开通 | 控制台开通对应模型 |
| 任务 `failed` | 内容安全拦截或素材不合规 | 读 `error.message`；换素材或改提示词 |
| 任务 `expired` | 超时未执行 | 降低分辨率/时长重提 |

## 自检清单（交付前）

1. 比例、分辨率、时长是显式写死的，不是默认值漂移来的。
2. `ARK_API_KEY` 只在环境变量里，没有写进脚本或提示词。
3. 产出的视频/图片已经下载到本地目录，不是只给了 URL。
4. 试用新模型时先用 `--draft`（480p 试片）或 flash 档验证提示词，再上 1080p/4K。
5. 视频里要有人声/音效，确认 `generate_audio` 是你要的状态。

## 参考文件

- `references/models.md` — 全量模型矩阵：ID、分辨率、时长、参考上限、帧率、限流
- `references/video-api.md` — 视频接口逐字段说明 + 各模式完整 JSON + 轮询与返回结构
- `references/image-api.md` — 图片接口逐字段说明 + 尺寸规则 + 参考图用法
- `references/prompts.md` — 文生图/图生视频提示词结构与可套用模板（含 @ 引用语法）
- `scripts/ark-media.mjs` — 调用脚本，`--help` 看全部参数
