# 模型矩阵

核对时间：2026-11-17。数据来自火山方舟模型列表与视频/图片生成接口文档。**模型 ID 带日期后缀，官方会滚动更新**；接生产前到控制台模型列表复核一次。

## 视频模型

| 模型 | Model ID | 分辨率 | 时长 | 帧率 | 输出格式 | 参考上限 | 限流（非4K） |
|---|---|---|---|---|---|---|---|
| Seedance 2.5 | `doubao-seedance-2-5-260628` | 480p / 720p / 1080p(10bit) / 4K(10bit) | 4–30s 或 -1 | 24fps | mp4、mov | 图 30 / 视频 10 / 音频 10 | 600 RPM（企业）、180（个人）；并发 10 / 3 |
| Seedance 2.5 flash | `doubao-seedance-2-5-flash-261115` | 480p / 720p | 4–30s 或 -1 | 24fps | mp4、mov | 图 10 / 视频 5 / 音频 5 | 600 / 180；并发 10 / 3 |
| Seedance 2.0 | `doubao-seedance-2-0-260128` | 480p / 720p / 1080p / 4K | 4–15s 或 -1 | 24fps | mp4 | 图 9 / 视频 3 / 音频 3 | 600 / 180；并发 10 / 3 |
| Seedance 2.0 fast | `doubao-seedance-2-0-fast-260128` | 480p / 720p | 4–15s 或 -1 | 24fps | mp4 | 图 9 / 视频 3 / 音频 3 | 600 / 180；并发 10 / 3 |
| Seedance 2.0 mini | `doubao-seedance-2-0-mini-260615` | 480p / 720p | 4–15s 或 -1 | 24fps | mp4 | 图 9 / 视频 3 / 音频 3 | 600 / 180；并发 10 / 3 |
| Seedance 1.0 pro（即将下线） | `doubao-seedance-1-0-pro-250528` | 480p / 720p / 1080p | 2–12s | 24fps | mp4 | 首尾帧/首帧/文生 | 600 RPM；并发 10 |
| Seedance 1.0 pro fast（即将下线） | `doubao-seedance-1-0-pro-fast-251015` | 480p / 720p / 1080p | 2–12s | 24fps | mp4 | 首帧/文生 | 600 RPM；并发 10 |

4K 档单独限流：RPM 15、并发 1。

## 视频能力矩阵

| 能力 | 2.5 | 2.5 flash | 2.0 / fast / mini |
|---|---|---|---|
| 文生视频 | ✓ | ✓ | ✓ |
| 首帧生视频 | ✓ | ✓ | ✓ |
| 首尾帧生视频 | ✓ | ✓ | ✓ |
| 全模态参考生视频 | ✓ | ✓ | ✓ |
| 仅音频参考 | ✓ | ✓ | ✗（必须配图或视频） |
| 视频编辑 | ✓ | ✓ | ✓ |
| 视频延长 | ✓ | ✓ | ✓ |
| 音频生成 | ✓ | ✓ | ✓ |
| 联网搜索 `tools` | ✓ | ✓ | ✓ |
| 返回尾帧 `return_last_frame` | ✓ | ✓ | ✓ |
| 草稿试片 `draft` | ✓ | ✗ | ✗ |
| 离线推理 | ✗ | ✗ | ✗ |

参考素材时长上限：2.5 系列视频/音频单条 2–30s、累计 ≤30s、音频单条 ≤15MB；2.0 系列累计 ≤15s。编辑任务源片须 4–30s。

## 视频关键默认值

| 参数 | 2.5 / 2.0 默认 | 可选值 |
|---|---|---|
| `resolution` | `720p` | 480p / 720p / 1080p / 4k（依模型） |
| `ratio` | `adaptive` | 16:9 / 4:3 / 1:1 / 3:4 / 9:16 / 21:9 / adaptive |
| `duration` | 2.5 默认 `-1`；2.0 需在 4–15 内取值 | 2.5: 4–30 或 -1；2.0: 4–15 或 -1 |
| `generate_audio` | `true` | 布尔，输出恒为立体声 |
| `watermark` | `false` | 布尔，true 打"AI生成" |
| `output_format` | `mp4` | mp4 / mov（仅 2.5） |
| `return_last_frame` | `false` | 布尔，true 时可从查询结果取 `content.last_frame_url`（JPEG、无水印） |
| `omni_reference_task_type` | `auto` | auto / reference / edit / extend（仅 2.5） |
| `draft` | `false` | true 时只能 480p，产出供正式片复用的 draft 任务 |

1.0 系列额外有 `frames`（25+4n，29–289，优先生效）、`seed`、`camera_fixed`；2.x 不再需要这些。

## 图片模型

| 模型 | Model ID | 尺寸档位 | 参考图上限 | 备注 |
|---|---|---|---|---|
| Seedream 5.5 | `doubao-seedream-5-5-261028` | 1K / 1.5K / 2K（默认 2K） | 10 | 分层拆分（≤99层）、原生 RGBA、交互编辑 |
| Seedream 5.0 pro | `doubao-seedream-5-0-pro-260628` | 1K / 1.5K / 2K（默认 2K） | 10 | 分层（≤16层） |
| Seedream 5.0 flash | `doubao-seedream-5-0-flash-260915` | 1K / 1.5K / 2K（默认 2K） | 10 | 性价比档 |
| Seedream 5.0 lite（即将下线） | `doubao-seedream-5-0-lite-260128` | 2K / 3K / 4K | 14 | 支持一次多图、流式、联网搜索 |
| Seedream 4.5（即将下线） | `doubao-seedream-4-5-251128` | 2K / 4K | 14 | 支持一次多图、流式 |
| Seedream 4.0（即将下线） | `doubao-seedream-4-0-250828` | 1K / 2K / 4K | 14 | 支持一次多图、流式 |

图片限流：500 IPM。

### 尺寸与像素规则

| 模型 | 像素区间 | 宽高比区间 |
|---|---|---|
| 5.5 / 5.0 pro / 5.0 flash | 921600 – 4624220 | 1/16 – 16 |
| 5.0 lite / 4.5 | 3686400 – 16777216 | 1/16 – 16 |
| 4.0 | 921600 – 16777216 | 1/16 – 16 |

- 单张参考图 ≤30MB，边长 >14px；支持 jpeg/png/webp/bmp/tiff/gif/heic/heif。
- `size` 可写档位名（`2K`）、写像素（`2048x2048`）或写 `auto`。
- 一次多图（`sequential_image_generation: auto`）只在 5.0 lite / 4.5 / 4.0 可用，且输入图 + 输出图合计 ≤15。当前主力档（5.5 / 5.0 pro / flash）**一次一图**，要多图就多调几次。

## 版本选择建议

- 成本敏感的长片批量：2.5 flash 出草稿 → 2.5 正式重生成，或直接 2.0 fast 定稿。
- 需要 10 秒以上单镜、或多素材参考（人物 + 服装 + 运镜 + BGM 一起给）：只有 2.5 系列够用（30s、30 图、30s 音频）。
- 已有 2.0 生产流水线且提示词已调优：不要为了新版本号迁移，2.0 的 4–15s 和 9 图上限仍够用且单价更低。
