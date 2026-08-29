# video-agent-kit

`video-agent-kit` 是自动化视频剪辑工具包。它把视频剪辑需要的特殊能力封装成 MCP 工具和 CLI：媒体探查、标准云端语音转录与合成、完整视频抽帧观察、局部高 fps 复看、基础视频操作、timeline 校验、预览渲染、QC 和可审计修复。

## 设计边界

- 不假设主模型可以直接接收视频文件；视频会先按固定规则抽帧并拼成带时间戳的 contact sheet，再通过 MCP 图片结果返回给 Claude Code 主 Agent。
- 不依赖任何插件目录之外的脚本：抽帧索引逻辑完整内置在 `mcp/ve_tools/video_observe.py`，本工具包不会构造 `image_url` 请求，也不会在工具内部调用任何外部推理服务。
- 当前只处理用户提供的视频/音频素材，不处理素材库检索，也不做图像/视频生成。
- 自动化造数据场景下不等待用户澄清或确认。

## MCP 工具

- `inspect_media`：ffprobe 媒体探查；总体时长优先读 format duration，缺失时回退到 stream duration；`NaN` / `Infinity` 不会被当成有效时长。
- `speech_transcribe`：标准语音转录工具。配置 `VE_SPEECH_MCP_URL` 时调用远端 HTTP MCP；未配置时，在 ZCode 中优先使用宿主随 `tools/call` 注入身份的官方通道，其他宿主回退到本地兼容后端。对外统一为 `cloud_asr`，不会暴露内部服务商名称。并发限制、限流、网络和服务端瞬时错误默认额外重试 3 次，可用 `retries` / `retry_count` 和 `retry_backoff_seconds` 覆盖；缺凭据、provider 不可用、输入/参数错误不会重试。长媒体会自动拆成最多 `chunk_seconds` 秒的重叠块（默认不超过 1700s）分别转写并合并，块级结果缓存可断点续跑；分块说话人标签带 `p{chunk}_` 前缀，跨块同一人物可能有不同标签。毫秒时间戳会归一成秒；静音音频返回带 `silent_audio` 标注的有效空转录。`transcribe` 保留为兼容 alias。
- `video_ingest`：完整视频抽帧并返回 contact sheet，必须先跑；Claude Code 主 Agent 自己看图并形成理解。显式传入的 `transcript_path` 必须存在；不传 transcript 才表示允许无转录观察；在同一个 MCP 会话里，如果重新观察此前已绑定过 transcript 的同一视频指纹，会复用该视频对应的 transcript。同一路径的视频文件如果被覆盖或替换，必须重新调用 `video_ingest`。只有成功产出 observation package 后，工具才会把该视频记为已 full-ingest；抽帧失败不会推进会话状态。
- `video_watch_segment`：局部高 fps 复看；单窗口用 `start_time/end_time/fps`，多窗口用 `segments=[{start,end}, ...]` + `fps`，返回片段 contact sheet 和匹配转录。显式传 `video_path` 可直接复看任意存在的视频，不要求先跑完整 `video_ingest`。不带 `video_path` 时默认使用会话里的 active video；如果 active 文件被覆盖或替换，隐式复看会报错并要求显式传当前 `video_path` 或重新 `video_ingest`。显式传入的 `transcript_path` 必须存在；在同一个 MCP 会话里，如果显式传入此前已绑定过 transcript 的同一视频指纹且未传 transcript 参数，会复用该视频对应的 transcript。非数字时间参数会返回结构化错误；明显超过视频时长的窗口会报错，不会静默截断成较短观察。窗口台账按 `(start, end, fps)` 判重：只有时间和 fps 都相同的窗口才会被跳过，换一个 fps 重看同一窗口是新的观察；确有需要时可传 `force=true` 跳过判重。只有成功产出新 contact sheet 后，局部复看才会更新 active-video 会话状态；抽帧失败或 `skipped_duplicate` 不算新的视觉证据，多窗口部分失败时整体结果会带 `[ERROR]` 前缀汇总。
- `video_basic_operation`：OpenChatCut 风格的确定性基础操作封装，支持 `trim`、`splice`、`speed`、`crop`、`scale`、`rotate`、`flip`、`freeze_frame`。它适合源素材预处理或单步变换；timeline 成片仍应走 `validate_timeline` / `render_preview`。
- `speech_synthesize`：标准语音合成工具。配置 `VE_SPEECH_MCP_URL` 时调用远端 HTTP MCP；未配置时，在 ZCode 中优先使用宿主注入身份的官方通道，其他宿主回退到本地兼容后端。对外统一为 `cloud_tts`；`allowed_providers` 提供时是硬白名单。并发限制、限流、网络和服务端瞬时错误默认额外重试 3 次，可用 `retries` / `retry_count` 和 `retry_backoff_seconds` 覆盖；参数错误、缺凭据、格式不支持不会重试。`speed` 会映射为 `speech_rate`，也可显式传 `speech_rate` / `pitch_rate` / `loudness_rate` / `sample_rate` / `output_format`，本工具只暴露可被 ffprobe 稳定校验的 `wav` / `mp3` / `ogg_opus` 输出，并拒绝 `output_path` 后缀与 `output_format` 不一致。`tts_generate` 保留为兼容 alias。
- `validate_timeline`：校验 timeline 项目 JSON；依赖 ffprobe 检查源素材时长边界，时长优先读 format duration，缺失时回退到 stream duration，且同一源文件的时长探测会缓存。除了旧版线性 `clips[]`，也支持更接近剪辑软件项目文件的 `project` / `sequence` / `output_canvas` / `assets` / `tracks` / `markers` / `transitions` / clip effects 元数据校验。`tracks[]` timeline 中非视频轨的 clip（字幕 / overlay / callout 计划）可以用非空 `text` 代替媒体 `source`；视频 / main 轨 clip 和顶层 `clips[]` 仍必须有 `source`。
- `render_preview`：用 FFmpeg / ffprobe 渲染预览；render report 会记录 timeline hash 和 output hash。顶层 `clips[]` 仍按 legacy/debug 线性拼接渲染；项目式 `tracks[]` 会按 sequence 画布和 `timeline_start` 编译成基础多轨预览：主视频铺到画布并在片尾补少量末帧降低边界闪帧，源视频音频与 `audio/music/voiceover` 轨先烘焙成全片长度、已按时间线定位的 wav bed，再非归一化混音，`subtitle/text` 轨用 `drawtext` 烧录，`overlay/image` 轨按启用窗口叠加。父轨道没有 `type/name/track_type` 时不会被默认当作主视频轨；未知 track 类型会记录到 render plan 的 unsupported tracks 中，而不是声称完整渲染。
- `qc_preview`：硬性质量检查，包括容器、黑帧、短编辑边界黑帧、静音、冻结帧、音量、音频覆盖时长和空文件；媒体探测失败或显式传入的 `timeline_path` 不存在时直接报错，黑帧 / 静音 / 冻结 / 音量扫描失败会作为 QC error 写入报告。静音和音量扫描只在存在音轨时运行；完全没有音轨的成片会记一条 warning（整片无声），不会静默通过。
- `timeline_diff`：记录或应用 timeline 修复；`patch` 必须是 JSON object，`apply` 必须是 boolean。支持 `set_timeline_fields`、`set_track_fields`、`add_assets`、`update_assets`、`remove_asset_indices`、`add_tracks`、`insert_tracks`、`replace_tracks`、`remove_track_indices`、`update_clips`、`replace_clips`、`remove_clip_indices`、`move_clips`、`insert_clips` 和 `add_clips`。`update_clips` 是浅层字段合并，字段值为 `null` 表示删除该字段；`set_timeline_fields` 可改项目元数据但不能直接改 `clips/tracks`。`replace/update/remove/move` 索引按补丁前扁平 clip 顺序解释，asset/track 操作用各自数组内的索引解释；结构性 track 操作（add/insert/replace/remove tracks）不能和 clip 操作混在同一个 patch，必须拆成两次 `timeline_diff`。`move_clips` 每次 patch 最多一条，不能与删除操作混用，也不能指向同一个 patch 新插入的 clip。工具会先校验 patch 操作本身和 patch 后的 timeline。`apply=true` 遇到越界 index、非对象 clip/fields、空 patch、多条 move、结构性 track 操作和 clip 操作混用等非法操作时只写 diff 报告，不修改原 timeline。

默认文件契约为 `out/media.json`、`out/transcript.json`、源素材 `video_ingest` 观察包、`out/timeline.json`、`out/timeline_validation.json`、`out/preview.mp4`、`out/preview_qc_report.json` 和 `out/report.md`。其中 `out/transcript.json` 是 cloud ASR 可用时的预期产物；如果 cloud ASR 不可用，应在 `out/report.md` 记录限制并继续完成其余闭环。单素材任务可使用 `out/video_ingest.json`；多素材任务可以显式传 `output_json` 写到 `out/ingest/*.json` 或 `out/video_ingest_<source>.json`，并在 `out/media.json` 汇总。

`video-recap-workflows` 覆盖完整电影、足球、LoL 和篮球解说剪辑。电影解说使用 `detect_shots` / `arrange_footage` / `synthesize_narration` / `bind_narration` / `render_narrated`；足球使用 `soccer_ingest` / `soccer_arrange` / `soccer_tts` / `soccer_render`；LoL 与篮球复用 `lol_ingest` / `lol_arrange` / `lol_tts` / `lol_render`。这些流程通常产出 `out/final.mp4` 和 workflow-specific QC，而不是通用 `out/preview.mp4`。

`out/media.json` 保留给源素材探测。`qc_preview` 和 `tts_generate` 内部做媒体探测时会写 `out/preview_media.json`、`out/tts_*_media.json` 这类 sidecar，不覆盖源素材 metadata。`validate_timeline` 和 `qc_preview` 会在报告中写入文件 hash；Stop hook 会拒绝已经过期的 validation / QC report。

`schemas/video_observation.schema.json` 对应工具真实落盘的 observation package，即 `video_ingest` / `video_watch_segment` 生成的帧清单、sheet 清单、媒体元数据、抽帧参数和匹配转录。模型读图后的主观摘要、候选片段和风险判断应写入 `out/report.md` 或后续独立的 review 文件，不写回这个工具产物 schema。

## 插件使用

把本目录作为 Claude plugin 使用时，`.mcp.json` 会启动 `mcp/video_edit_server.py`。命令入口在：

```text
commands/video-edit.md
commands/env-check.md
skills/env-setup/SKILL.md
skills/video-edit-agent/SKILL.md
skills/video-edit-assembly/SKILL.md
skills/video-speech-workflows/SKILL.md
skills/video-recap-workflows/SKILL.md
```

`video-edit-agent` 是总控入口，负责素材发现、任务分类、通用文件契约、timeline
验证、渲染、QC 和修复闭环；`video-edit-assembly` 是多素材组装成片子流程，
用于多段视频/音频/图片素材的分组、选择、去重、排序和成片结构规划；
`video-speech-workflows` 处理单源语音压缩和字幕；`video-recap-workflows`
处理完整电影/赛事/比赛回放的解说剪辑；`env-setup` 只管环境（体检 + 装依赖，
跨 macOS / Windows / Linux），不碰剪辑任务。

首次使用前装环境（推荐走体检脚本，它跨 macOS / Windows / Linux 且默认用国内镜像）：

```bash
# 只体检：逐项报"要什么 / 缺了挂哪个能力 / 本平台怎么装"
python3 video-agent-kit/skills/env-setup/scripts/env_doctor.py
# 体检 + 自动装可自动装的 pip 包（清华源）
python3 video-agent-kit/skills/env-setup/scripts/env_doctor.py --fix
```

会话里也可以直接用 `/env-check`（对应 `env-setup` skill）。体检结论落在
`.video_agent/env_report.json`，不必每轮重跑。

它查的不止"包在不在"：ffmpeg 有没有带 `libx264` / `aac` / `libmp3lame` 与
`libass`（缺了字幕烧录必挂，但只在渲染最后一步才炸）、本机中文字体的 cmap 是不是
真覆盖中文（`fc-match` 对着没装的中文族会返回 DejaVu，烧出来是豆腐块而 ffmpeg
退出码 0）、以及语音走的是哪条通道（在 ZCode 里就是"官方通道，本地无需 key"，不会催你配凭据）。

也可以手工只装 Python 依赖（注意 `scenedetect` 必须 `--no-deps`，否则会把 GUI 版
opencv 盖到 `opencv-python-headless` 的 `cv2` 上，两个包一起坏）：

```bash
python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r video-agent-kit/requirements.txt
python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-deps "scenedetect>=0.6"
```

字体不在标准目录时不用改代码，把目录塞给 `VE_FONT_DIRS`（多个目录用
`os.pathsep` 分隔）即可；查找顺序见 `mcp/ve_tools/fonts.py`：`VE_FONT_DIRS` →
`/root/.fonts`、`/usr/share/fonts` → 本平台系统字体目录（macOS 苹方 / Windows
微软雅黑，所以这两个平台通常不需要装字体）→ `fc-list :lang=zh`。

MCP 工具调用的 `arguments` 顶层必须是 JSON object；如果入口传入数组、字符串等非对象参数，server 会直接返回结构化错误，不把异常泄漏成工具 traceback。

插件启动时会通过 `hooks/env_check.py` 做一次非阻塞环境检查（只跑毫秒级项，清单直接从 `skills/env-setup/scripts/env_doctor.py` 的 cheap 检查项取，不在 hook 里另写一份），提示缺失的 `ffmpeg`、`ffprobe`、MCP SDK、抽帧依赖，并报出语音走哪条通道（ZCode 下即"官方通道，本地无需 key"）；要做全量体检（ffmpeg 编码器与 libass 滤镜、中文字体真覆盖、直连兼容端点连通性）走 `/env-check`。TTS 调用依赖按需懒加载；缺 TTS 依赖只应影响 `speech_synthesize` / `tts_generate`，不应影响媒体探测、抽帧、timeline、渲染和 QC。用户 prompt 出现本地视频路径时，`hooks/check_video_input.py` 会提示标准流程：先 `speech_transcribe` 产出 `out/transcript.json`，再带 `transcript_path` 调 `video_ingest`；只有当剪辑流水线产物（`out/timeline.json`、`out/timeline_validation.json`、`out/preview.mp4` 或 `out/preview_qc_report.json`）出现后，`hooks/check_closeout.py` 才会在停止前检查 `out/media.json`（或任一 `*media.json` sidecar）、`out/transcript.json`（仅当 cloud ASR 可用时要求）、源素材 `video_ingest` 观察包（单素材 `out/video_ingest.json`，多素材 `out/ingest/*.json` 或 `out/video_ingest_<source>.json`）、`out/timeline.json`、`out/timeline_validation.json`、`out/preview.mp4`、`out/preview_qc_report.json` 和非空 `out/report.md` 是否闭环；当 recap 后期产物（如 `out/reel.json`、`out/edl.json`、`out/final.mp4`、`out/qc.json`）出现后，同一个 hook 会改查 recap 合同：最终视频、绑定/QC 报告、TTS 忠实度失败、句画抽查和 `out/report.md`。单步任务（如只做 `inspect_media` 或 `speech_transcribe`）不会触发契约。闭环 strike 计数按会话隔离，最多拦 3 次后放行并记录 violation。QC 报告必须由 `qc_preview(video_path="out/preview.mp4", timeline_path="out/timeline.json")` 生成，否则缺少 timeline hash 会被视为未闭环。

推荐工作流：

```text
video-edit-agent classify
  -> video-edit-assembly       # 多素材组装成片任务
  -> video-speech-workflows    # 单源语音压缩、说话人字幕、speech pipeline
  -> video-recap-workflows     # 电影/足球/LoL/篮球解说剪辑
  -> inspect_media
  -> transcribe
  -> video_ingest           # 一次性把完整视频变成可看的 contact sheet，附带完整转录
  -> video_watch_segment    # 只在需要时局部高 fps 复看；多个疑点应批量传 segments
  -> 生成 timeline.json
  -> validate_timeline
  -> render_preview
  -> qc_preview             # 传 video_path=out/preview.mp4 和 timeline_path=out/timeline.json
  -> 内容自检               # 如需看 preview，video_ingest 写到 out/preview_ingest.json，不覆盖源视频 out/video_ingest.json
  -> timeline_diff 修复 loop
```

注意：对 `out/preview.mp4` 调用 `video_ingest` 或显式 `video_watch_segment(video_path="out/preview.mp4", ...)` 后，后续不带 `video_path` 的 `video_watch_segment` 默认会复看 preview。若修复时还需要回看原始素材，应显式传原始 `video_path`；在同一个 MCP 会话里，工具会按视频指纹复用此前绑定过的源素材 transcript。如果某个 active video 路径上的文件内容被重新渲染、覆盖或替换，隐式局部复看会拒绝继续使用旧 active 状态；显式传当前 `video_path` 可直接复看当前文件，完整 `video_ingest` 只在需要全片 contact sheet 时再跑。CLI 每次调用都是新进程，不共享这份会话记忆，因此 CLI 直接复看时应显式传 `transcript_path` 或 `transcript_text`。

## 环境变量

所有配置统一走 `.env` 配置文件（KEY=VALUE），不需要在启动 shell 里手动 export。加载优先级：

1. 进程环境变量（最高，用于临时覆盖）；
2. 项目目录 `.env`（按项目覆盖）；
3. 插件根目录 `.env`（插件级默认值）。

完整可配置项参考 `.env.example`。SessionStart 环境检查会打印实际加载了哪些 `.env` 文件。

**语音在 ZCode 里不需要任何配置。** `speech_transcribe` / `speech_synthesize` 默认走官方通道，
身份由宿主随每次 `tools/call` 注入，没有 key 可配、也没有端点要指。下面这些只对非 ZCode 宿主有意义，
`/env-check` 里这两项也永远是 soft，不是硬缺口。

必须或高价值配置：

- `VE_SPEECH_MCP_URL` / `VE_SPEECH_MCP_TOKEN`：Claude Code 等非 ZCode 宿主可配置的远端 HTTP MCP 语音服务，也是这类宿主的推荐做法（付费能力与凭据都留在服务端）。ZCode 清单不暴露这两个用户配置。显式设置 URL 时远端 MCP 优先级最高；`VE_SPEECH_MCP_ASR_TRANSFER=auto|path|base64` 控制 ASR 媒体传输，默认对 localhost/shared-storage 走路径，对非本机远端抽取压缩音频后 base64 上传。
- `VE_ASR_PROVIDER`：`speech_transcribe` / `transcribe` 的 provider 选择，`auto`（默认）/ `cloud_asr`。
- 直连 HTTP 兼容后端（legacy escape hatch，自带语音服务时才用）：插件不内置任何服务地址、模型名或资源标识，全部由部署方提供。
  - `VE_SPEECH_ASR_ENDPOINT` / `VE_SPEECH_TTS_ENDPOINT` **只从进程环境读，不吃 `.env`**：项目级 `.env` 是不可信输入，若它能指定端点，仓库里的一个 `.env` 就能把带着 API key 的请求导向攻击者主机。请在启动 server 的地方 export。
  - `VE_SPEECH_ASR_RESOURCE_ID`（必填）、`VE_SPEECH_ASR_FLASH_RESOURCE_ID`（可选，同步回退资源）。
  - `VE_SPEECH_ASR_API_KEY`，或 `VE_SPEECH_ASR_APP_KEY` + `VE_SPEECH_ASR_ACCESS_KEY`。
  - `VE_SPEECH_TTS_MODEL`（必填）、`VE_SPEECH_TTS_API_KEY`（未配置时复用 ASR key）、`VE_SPEECH_TTS_VOICE`。
- `VE_NARRATION_TTS_PROVIDER` / `VE_NARRATION_TTS_VOICE` / `VE_NARRATION_TTS_RATE`：`synthesize_narration` 的用户级默认 cloud TTS 后端、音色和语速。
- `VE_LOL_TTS_PROVIDER` / `VE_LOL_TTS_VOICE`：`lol_tts` 的默认 cloud TTS 后端和音色。
- `VE_SOCCER_TTS_PROVIDER` / `VE_SOCCER_TTS_VOICE`：`soccer_tts` 的默认 cloud TTS 后端和音色。
- `VE_BGM_DIR`：`render_narrated` 可选 BGM 曲库目录；当前 movie-recap skill 默认 `bgm=false`，未配置时不会阻塞无 BGM 成片。

`speech_transcribe` 和 `speech_synthesize` 都支持 `retries` / `retry_count` 表示瞬时错误的额外重试次数，默认 3，范围 0~10；`retry_backoff_seconds` 是指数退避初始秒数，`speech_transcribe` 默认 30 秒，`speech_synthesize` 默认 3 秒。只重试网络、timeout、429/5xx、服务端错误、并发/限流等瞬时失败；缺 key、provider 不可用、输入/参数错误不会重试。

`speech_synthesize` 的 `preferred_provider` 必须是 `auto`、`cloud` 或 `cloud_tts`；未知值会直接返回结构化错误。`allowed_providers` 是硬白名单，提供时只能包含通用 cloud TTS provider；错误类型或未知 provider name 会直接返回结构化错误。`sample_mode` 提供时必须是 boolean，不能用字符串 `"false"` / `"true"` 代替。`speed` 必须是有限正数。TTS 额外参数中，`speech_rate` 必须在 `[-50,100]`，`pitch_rate` 必须在 `[-12,12]`，`loudness_rate` 必须在 `[-50,100]`，`sample_rate` 必须是接口支持的采样率，`output_format` 必须是 `wav` / `mp3` / `ogg_opus`。TTS 音频生成后必须能被 `ffprobe` 探测到有效正数时长，否则工具会返回错误，避免把未知时长的旁白写进 timeline。

## CLI 使用

CLI 和 MCP 共用同一套实现：

```bash
python video-agent-kit/cli/video_agent_tool.py inspect_media --input_path input.mp4 --pretty
python video-agent-kit/cli/video_agent_tool.py transcribe --input_path input.mp4 --language zh --pretty
python video-agent-kit/cli/video_agent_tool.py video_ingest --args-file video-agent-kit/examples/video_ingest_args.json --pretty
python video-agent-kit/cli/video_agent_tool.py video_watch_segment --video_path input.mp4 --start_time 12 --end_time 16 --fps 6 --pretty
python video-agent-kit/cli/video_agent_tool.py video_basic_operation --operation trim --input_path input.mp4 --start_time 3 --end_time 8 --output_path out/trim.mp4 --pretty
python video-agent-kit/cli/video_agent_tool.py video_basic_operation --operation splice --args-json '{"clips":[{"source":"input.mp4","start":0,"end":3},{"source":"input.mp4","start":8,"end":12}],"output_path":"out/splice.mp4"}' --pretty
python video-agent-kit/cli/video_agent_tool.py validate_timeline --timeline_path out/timeline.json --pretty
python video-agent-kit/cli/video_agent_tool.py render_preview --timeline_path out/timeline.json --output_path out/preview.mp4 --pretty
# 可选：显式指定预览画布，适合横竖屏或不同分辨率素材混剪
python video-agent-kit/cli/video_agent_tool.py render_preview --timeline_path out/timeline.json --output_width 1080 --output_height 1920 --pretty
python video-agent-kit/cli/video_agent_tool.py qc_preview --video_path out/preview.mp4 --timeline_path out/timeline.json --pretty
```

CLI 的 `--args-json` / `--args-file` 必须是合法 JSON，且顶层必须是 JSON object；非法 JSON 或数组 / 字符串等非对象参数会在入口处直接报错。`--key value` 简写会自动解析 JSON object / array 字符串，所以可以直接传结构化 patch，例如 `--patch '{"add_clips":[...]}'`；复杂参数仍推荐使用 `--args-file`。

## 基础视频操作

`video_basic_operation` 是 OpenChatCut 风格的单步基础操作工具，所有操作都通过 FFmpeg 落成可检查的视频文件，并写同名 `.basic_operation.json` 报告。当前支持：

- `trim`：`input_path` + `start_time` + `end_time` / `duration`，剪出一个时间范围。
- `splice`：`clips=[{"source","start","end"}]`，把多个片段归一到同一画布后拼接。
- `speed`：`speed=0.1..8.0`，可选 `reverse=true`；音频用 `atempo` 链同步变速。
- `crop` / `scale` / `rotate` / `flip`：基础构图和方向调整；`scale.mode` 支持 `fit`、`fill`、`stretch`。
- `freeze_frame`：`at_time` + `duration`，从某一帧生成静帧视频。

这个工具适合素材预处理、局部变换验证和构造中间素材。正式剪辑决策仍应写入 `out/timeline.json`，再走 `validate_timeline`、`render_preview`、`qc_preview`。

## 抽帧默认参数

这些是内置抽帧索引逻辑的默认值：

- `video_fps=2.0`
- `video_t_patch_size=2`
- `video_sampling_mode=prod`
- `max_video_frames=600`
- `video_frame_normalize_jpeg_quality=90`
- `video_label_mode=timestamp`
- `sheet_cols=4`
- `sheet_max_cells=24`
- `sheet_width=1568`
- `jpeg_quality=85`

输出形态是带时间戳的 contact sheet 图片。MCP 会内联前 16 张图片；如果更多，工具结果会列出剩余图片路径，Claude Code 主 Agent 必须继续读取这些图片。sheet 上的时间戳始终按实际帧索引换算成源视频时间（能读到解码器 PTS 时优先用 PTS，兼容可变帧率素材）；局部复看也不改成片段内相对时间。`video_ingest` 会复用相同视频、时间范围、prompt、转录和抽帧设置的既有 sheet，但不会按空白、近重复内容或重复 frame index 折叠采样帧；视频剪辑任务需要尽量完整地看到固定采样覆盖到的画面。`video_watch_segment` 会按源视频路径、大小和修改时间生成独立窗口台账，按 `(start, end, fps)` 跳过同一源视频的精确重复复看窗口（换 fps 重看不算重复，`force=true` 可强制重看）；被跳过的重复窗口不会产生新的 contact sheet，工具会返回 `skipped_duplicate` 状态，且不会把这次调用当成新的视觉观察来更新 active video。重叠但不精确相同的窗口会提示已覆盖范围；这个台账只管理时间窗，不折叠帧内容。active video 也使用同一类指纹保护，避免源文件被覆盖后继续沿用旧 transcript 或旧全片观察结论。

抽帧读取视频元数据时优先使用 OpenCV / python_vali；ffprobe 兜底路径会同时读取 stream duration 和 format duration，避免只有容器时长或只有流时长的视频无法采样。

## Timeline 项目格式

见 `examples/timeline_minimal.json`、`examples/timeline_project_rich.json` 和 `schemas/timeline.schema.json`。Pipeline 输出的 timeline 根节点必须是 JSON object，并且必须包含非空 `project`、`assets[]`、`tracks[]`，还必须包含 `sequence` 或 `output_canvas`。顶层 `clips[]` 只保留给 legacy/debug 兼容，不能满足项目文件契约。track 和 clip 都必须是 object；每个 clip 必须有 `start`、`reason`，并且必须提供 `end` 或 `duration`。视频 / main 轨的 clip 必须有 `source`；`tracks[]` 中非视频轨的 clip 可以用非空 `text` 代替 `source` 来记录字幕 / overlay 计划。如果同时提供 `end` 和 `duration`，`duration` 必须与 `end - start` 一致。所有时间值必须是有限数字，不能是 `NaN`、`Infinity` 或布尔值。

推荐新任务尽量写成项目文件，而不是只有裸 `clips[]`：`project` 记录任务和假设，`sequence` / `output_canvas` 记录分辨率、fps、时基和平台目标，`assets[]` 记录源素材清单，`tracks[]` 表达主视频、BGM、旁白、字幕、overlay、callout 等轨道计划，`markers[]` 记录关键节拍，`transitions[]` 或 clip 级 `transition_in/out` 记录转场计划，clip / track 可带 `effects[]`、`timeline_start`、`volume`、`opacity`、`enabled` 等编辑软件常见元数据。Validation 会校验这些字段的基本类型、数值边界、资产引用、轨内重叠和 sequence 时长边界。

`render_preview` 现在是基础项目渲染器：`tracks[]` 中父级 track 的 `type/name/track_type` 明确为 `video` / `main` / `primary` / `footage` 等主视频含义时，会按 `timeline_start` 放到 sequence 画布上并在片尾补少量末帧以降低边界闪帧；原视频音频与 `audio` / `music` / `voiceover` 等音频轨会先烘焙成全片长度、已按时间线定位的 wav bed，再用非归一化混音合成；`subtitle` / `text` 等文字轨会通过 `drawtext` 烧录；`overlay` / `image` 轨会按启用时间窗叠加静态图片。渲染后会额外写 `preview.render_plan.json` 和 `preview.edit_decisions.json`，方便检查 timeline 如何被编译成输出。

这个 renderer 仍不是完整 NLE：复杂关键帧、遮罩、任意转场曲线、嵌套序列、复杂调色、动态贴纸和多层高级合成仍应作为项目计划记录，不能声称已完整渲染。未知 track 类型会记录到 render plan 的 unsupported tracks 中。

```json
{
  "version": "1.0",
  "clips": [
    {
      "source": "input.mp4",
      "start": 0.0,
      "end": 5.0,
      "reason": "开场信息完整"
    }
  ]
}
```

`timeline_diff` 对 `clips[]` 和 `tracks[].clips[]` 都会原地修改对应 clip 容器，不会为了修复 tracks timeline 而额外生成顶层 `clips`。`patch` 必须是 JSON object，`apply` 必须是 boolean。可用操作包括：`set_timeline_fields`、`set_track_fields`、`add_assets`、`update_assets`、`remove_asset_indices`、`add_tracks`、`insert_tracks`、`replace_tracks`、`remove_track_indices`、`update_clips`、`replace_clips`、`remove_clip_indices`、`move_clips`、`insert_clips`、`add_clips`。`replace/update/remove/move` 索引按补丁前的扁平 clip 顺序解释；asset/track 操作用各自数组内的索引解释；结构性 track 操作（add/insert/replace/remove tracks）会改变 clip 容器，不能和 clip 操作混在同一个 patch，必须拆成两次 `timeline_diff`。`move_clips` 每次 patch 最多一条，移动已有 clip，随后才执行 `insert_clips` / `add_clips`；多次重排必须拆成多次 `timeline_diff`。对 `tracks[]` timeline 使用 `add_clips` 时，会优先加入第一个视频 / main 轨；`insert_clips` 和 `move_clips` 可传 `track_index` 指定目标轨道。重复索引、越界索引、非对象 clip/fields、空 `apply=true` patch、多条 move、结构性 track 操作和 clip 操作混用都会被校验拒绝。
