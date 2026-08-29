---
description: 使用 video-agent-kit 完成视频剪辑任务
argument-hint: "[任务说明]"
skills: video-edit-agent
---

处理这个视频剪辑任务。

- 默认素材位置：当前工作目录（如果任务说明指定了文件或文件夹，优先使用指定路径）
- 任务说明：`$2`

必须遵守：

1. 先根据任务说明解析素材路径；如果未指定素材路径，优先读取当前工作目录下的 `materials_manifest.json`；如果该文件不存在、过期或不完整，再用 `find . -maxdepth 2 -type f -not -path './out/*' -not -path './.video_agent/*' -not -path './.claude/*' -not -path './.git/*' -not -name '.*' | sort` 盘点当前工作目录中的素材。识别视频、音频、图片和其它文件，不要假设只有一个固定源文件。
2. 根据任务说明和素材清单选择主源素材与辅助素材。对每个会参与剪辑的视频/音频素材调用 `inspect_media`；对高光截取、混剪、预告片类任务，或需要场景边界/静音/黑场辅助规划的任务，紧接着调用 `analyze_media(input_path)` 获取候选片段提示。多素材时把清单和关键 metadata 汇总写入 `out/media.json`。
3. 对需要理解语音内容的视频/音频，紧接着调用 `speech_transcribe(input_path)` 生成对应 transcript（单主视频可用 `out/transcript.json`；多素材用 `out/transcripts/<素材名>.json`）。`provider=auto`（默认）使用配置的 cloud ASR（带分句时间戳与说话人聚类）。静音音频返回的空转录是有效结果，不是失败。只有当 cloud ASR 不可用时才允许继续无转录流程，并把该限制记入 `out/report.md`；不要伪造转录。
4. 必须对每个需要做剪辑判断的源视频调用 `video_ingest(video_path, transcript_path=...)` 看完整视频；它会按内嵌抽帧逻辑把视频变成带时间戳的 contact sheet，并附带匹配转录。你必须自己读取这些图片后再做剪辑判断。图片素材需要用文件读取/视觉检查，不能忽略。
5. 只有在需要确认剪切点、动作连续性、字幕遮挡、表情或画面细节时，才调用 `video_watch_segment` 局部高 fps 复看；如果已经知道多个疑点，用 `segments=[{"start":..., "end":...}, ...]` 一次批量复看。
6. 生成 timeline JSON 后先 `validate_timeline`，再 `render_preview`，最后 `qc_preview(video_path="out/preview.mp4", timeline_path="out/timeline.json")`。项目式 `tracks[]` timeline 会按 sequence 画布、轨道、`timeline_start`、字幕/文字、图片叠加和音频混音编译成 preview，并生成 `out/preview.render_report.json`、`out/preview.render_plan.json`、`out/preview.edit_decisions.json`。
7. 如需视觉自检 preview，用 `video_ingest(video_path="out/preview.mp4", output_json="out/preview_ingest.json", ...)`，不要覆盖源素材的 `out/video_ingest.json`。之后不带 `video_path` 的 `video_watch_segment` 会默认复看 preview；如果 preview 被重新渲染到同一路径，先重新 `video_ingest`，再做隐式局部复看。如果还要回看原始素材，显式传原始素材路径；这个路径必须仍是此前 full-ingest 过的同一文件指纹，同一 MCP 会话内会复用此前绑定的源素材 transcript。
8. 如 QC 或内容自检发现问题，用 `timeline_diff` 记录修复，再重新验证。

自动化造数据场景下不要等待用户澄清或确认。缺信息时基于任务说明和视频内容做保守选择，并把假设写入输出报告。
