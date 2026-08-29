# video-agent-kit 视频剪辑与解说视频技能包

自动化视频剪辑工具包：云端语音转录与合成、完整视频抽帧理解、局部复看、时间线、预览渲染、QC 和 TTS 配音。支持**通用视频剪辑**、**电影解说（几分钟看完）**、**足球/篮球集锦**、**电竞（LOL）集锦**、**口播配音成片**等场景。

> 本技能包由 [Z.ai video-agent-kit](https://z.ai) v0.4.3 改造而来，已适配 **Claude Code / WorkBuddy** 等通用宿主，并将默认 TTS 通道替换为 **Edge TTS（免费、无需 API Key）**。

## 功能特点

- **🎬 通用视频剪辑**：素材发现 → 抽帧理解 → 时间线编辑 → 预览渲染 → QC 质检
- **🎙️ 完整语音能力**：ASR 语音转写（需自备 Key）+ TTS 语音合成（Edge TTS 免费开箱即用）
- **🎞️ 电影解说**：全片抽帧理解 + 对白转写 + 解说词编排 + 字幕烧录 + 配音成片
- **⚽ 体育集锦**：足球 / 篮球比赛 → 自动进球/机会镜头编排 → 解说配音成片
- **🎮 电竞集锦**：LOL 比赛回放 → 击杀/团战高光 → 解说配音成片
- **🔍 局部复看**：`video_watch_segment` 对不确定的画面按时间窗高帧率抽帧复查
- **✅ 硬 QC 门禁**：渲染前后自动校验时间线、黑帧、静音、音画同步

## 目录结构

```
video-agent-kit/
├── SKILL.md 系列（5 个技能，装入宿主 skills 目录）
│   ├── env-setup/              # 环境体检与依赖安装（ffmpeg/字体/pip 包）
│   ├── video-edit-agent/       # 总控制器：任务分类与路由
│   ├── video-edit-assembly/    # 多素材组装/混剪/去重/蒙太奇
│   ├── video-recap-workflows/  # 电影解说 + 足球/篮球/电竞集锦工作流
│   └── video-speech-workflows/ # 口播浓缩/字幕修复/视频流水线
├── mcp/                        # MCP 服务器（37 个工具）
│   ├── video_edit_server.py    # MCP stdio 入口
│   └── ve_tools/               # 工具实现（含 edge_tts_provider.py）
├── hooks/                      # 会话钩子脚本（可选）
├── commands/                   # Claude Code 斜杠命令（可选）
├── schemas/                    # 工具 JSON Schema
├── examples/                   # 使用示例
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量参考
└── README.upstream.md          # 上游原始文档（详细设计说明）
```

## 前置条件

### 1. Python 3.10+

建议使用独立虚拟环境，避免污染系统环境：

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
# 额外安装（必须，需与 opencv-python-headless 共存）
pip install --no-deps "scenedetect>=0.6"
```

### 2. ffmpeg / ffprobe

需包含 `libx264`、`aac`、`libmp3lame`、`libass`、`libfreetype` 编解码与滤镜（字幕烧录依赖）。

```bash
# Windows: winget install ffmpeg 或官网下载后加入 PATH
ffmpeg -version    # 验证
```

### 3. 中文字体

字幕/标题烧录需要 CJK 字体：
- Windows：微软雅黑（`C:\Windows\Fonts\msyh.ttc`）默认可用
- macOS：`/System/Library/Fonts/PingFang.ttc`
- Linux：`apt install fonts-noto-cjk` 或 `fc-list | grep -i cjk`

### 4. 环境体检（推荐）

首次使用前运行环境体检，自动探测缺失项：

```bash
# 在 video-agent-kit 目录下
python skills/env-setup/scripts/env_doctor.py          # 只体检
python skills/env-setup/scripts/env_doctor.py --fix    # 体检 + 自动装可装的依赖
```

## 安装为宿主技能

### Claude Code

将 5 个技能目录复制到 `~/.claude/skills/`：

```bash
cp -r skills/env-setup skills/video-edit-agent skills/video-edit-assembly \
      skills/video-recap-workflows skills/video-speech-workflows ~/.claude/skills/
```

### WorkBuddy

复制到 `~/.workbuddy/skills/`，并在 `~/.workbuddy/mcp.json` 注册 MCP 服务器：

```json
{
  "mcpServers": {
    "video-edit": {
      "type": "stdio",
      "command": "C:/path/to/your/.venv/Scripts/python.exe",
      "args": ["C:/path/to/video-agent-kit/mcp/video_edit_server.py"],
      "cwd": "C:/your/workspace",
      "env": { "VE_PLUGIN_ROOT": "C:/path/to/video-agent-kit" },
      "timeoutMs": 900000
    }
  }
}
```

> 注册后需在 WorkBuddy 连接器管理页点击「信任」启用；改动 MCP 配置后重启会话生效。

## TTS 语音合成（Edge TTS · 免费免 Key）

本改造版将默认 TTS 通道切换为 **Edge TTS**，无需任何 API Key 即可合成中文语音：

| 能力 | 说明 |
|------|------|
| 默认音色 | `zh-CN-XiaoxiaoNeural`（晓晓，女声） |
| 口播音色 | `zh-CN-YunxiNeural`（云希，男声）— narrate 系列默认 |
| 集锦音色 | `zh-CN-YunjianNeural`（云健，男声）— soccer/lol 默认 |
| 输出格式 | mp3（原生）/ wav / ogg_opus（自动转码） |
| 语速 | `speech_rate`（-50~100）或 `speed`（如 1.2） |
| 音调 | `pitch_rate`（-12~12） |
| 响度 | `loudness_rate`（-50~100） |

常用音色：`zh-CN-XiaoxiaoNeural`（晓晓）、`zh-CN-XiaoyiNeural`（晓伊）、`zh-CN-YunxiNeural`（云希）、`zh-CN-YunjianNeural`（云健）、`zh-CN-YunyangNeural`（云扬）、`zh-TW-HsiaoChenNeural`（曉臻）等。

> 旁白任务可通过 `VE_NARRATION_TTS_VOICE` 环境变量覆盖默认音色。

## 快速开始

### 场景 1：文档/文章 → 解说视频（配音）

```text
请把这篇文档转成一段 2 分钟的中文解说视频：<贴入内容>
```

工具链：脚本提炼 → Edge TTS 逐段配音 → 图文卡片/画面 → ffmpeg 合成 → QC。

### 场景 2：本地视频剪辑

```text
把 footage/ 目录下的素材剪成一条 30 秒的混剪，突出动作镜头，配上字幕
```

入口：`video-edit-agent` 自动分类 → 抽帧理解 → 时间线 → 渲染 → QC。

### 场景 3：电影解说

```text
几分钟看完《<电影名>》：<电影文件路径>
```

入口：`video-recap-workflows`（mode=movie-recap）→ 转写 + 抽帧 → 解说词 → 成片。

### 场景 4：足球集锦

```text
把这场球赛剪成 3 分钟集锦，带中文解说：<比赛文件路径>
```

入口：`video-recap-workflows`（mode=soccer-recap）。

## 环境变量

| 变量 | 说明 |
|------|------|
| `VE_PLUGIN_ROOT` | 插件根目录（脚本自动探测时可省略） |
| `VE_EDGE_TTS_VOICE` | Edge TTS 默认音色 |
| `VE_NARRATION_TTS_VOICE` | 口播默认音色 |
| `VE_BGM_DIR` | 背景音乐库目录（`<emotion>/*.mp3`） |
| `VE_MAX_INLINE_IMAGES` | 单次工具结果内联图片上限（默认 16） |
| `VE_PIP_INDEX` | pip 镜像源（默认清华源） |
| `VE_SPEECH_MCP_URL` | 远程语音 MCP 服务地址（可选） |
| `VE_SPEECH_ASR_API_KEY` 等 | 自备云端 ASR Key（转写功能需要） |

## 已知限制

- **ASR 语音转写**（`speech_transcribe`）：原 ZCode 官方通道需要宿主 JWT 鉴权，本改造版不包含。如需转写，请自备语音服务 API Key（如火山引擎 `VE_SPEECH_ASR_*`）或配置远程语音 MCP。
- **TTS 已开箱即用**：Edge TTS 免费无需任何配置，覆盖配音/口播/集锦全部合成场景。
- hooks / commands 为可选增强，不安装不影响核心功能。

## 许可证

MIT（沿用上游 video-agent-kit）
