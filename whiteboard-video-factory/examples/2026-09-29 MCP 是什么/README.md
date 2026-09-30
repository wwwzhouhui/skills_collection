# MCP 是什么

MCP（Model Context Protocol，模型上下文协议）的科普期。讲三件事：它替掉的是什么（M×N 的对接工作量）、它由哪几个角色组成（Host / Client / Server）、以及不到两年里它长成了什么样。主角是协议本身，不涉及具体人物。

## 资料来源

- 官网首页 https://modelcontextprotocol.io/ ——"Think of MCP like a USB-C port for AI applications."（正片里"官方比喻：MCP 就是 AI 应用的 USB-C 口"）。查阅日期 2026-09-29。
- 官方架构文档 https://modelcontextprotocol.io/docs/learn/architecture ——三个角色：`MCP Host`（协调一个或多个 client 的 AI 应用）/ `MCP Client`（维持与某个 server 的连接、为 host 取上下文）/ `MCP Server`（提供上下文的程序）；原文 "The MCP host accomplishes this by creating one MCP client for each MCP server."；协议分 data layer（JSON-RPC，含 tools/resources/prompts）与 transport layer（stdio / Streamable HTTP、消息分帧、授权）；server 三个原语 Tools / Resources / Prompts。查阅日期 2026-09-29。
- Anthropic 捐赠公告 https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation ——"more than 10,000 active public MCP servers"、"97M+ monthly SDK downloads across Python and TypeScript"、采纳方 ChatGPT / Cursor / Gemini / Microsoft Copilot / Visual Studio Code。2025-12-09。
- Linux 基金会新闻稿 https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation ——AAIF 成立（Anthropic / Block / OpenAI 共同发起，Platinum 含 AWS、Anthropic、Block、Bloomberg、Cloudflare、Google、Microsoft、OpenAI），founding projects 为 MCP、goose、AGENTS.md；"more than 10,000 published MCP servers"。2025-12-09。
- MCP 官方博客 https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/ ——同上口径（97 million monthly SDK downloads、10,000 active servers）。
- "M×N 变 M+N" 的表述来源：一篇介绍性文章把它总结为 "This turns an M-by-N integration problem into an M-plus-N one."（https://fit.neu.edu.vn/en/post/model-context-protocol-open-standard-connecting-tools-and-data-for-ai ）。正片把它简化成 M×N → M+N，属通俗化表述。

## 口径

- **"10,000+"**：官方原文是 "more than 10,000 active public MCP servers"，时间是 2025-12-09 的捐赠公告。正片说"超过一万个"，不加"实时"二字。
- **"9700 万"**：官方原文 97M+ monthly SDK downloads，统计范围是 **Python 与 TypeScript 两个官方 SDK 的月下载量**，不是"用户数"也不是"全部 SDK"。正片卡片写"9700 万"、标注"SDK 每月下载次数"。
- **"不到两年"**：MCP 开源于 2024-11-25，正片制作于 2026-09，中间约 22 个月。
- **"10 个 AI 工具 × 10 个数据源 = 100 套对接"**：正片里的**举例说明**，用来解释乘法关系，不是任何机构的实测数字。
- **"一个 Server 配一个 Client"**：架构文档原文 "one MCP client for each MCP server"。正片说"权限才能分开管"是这条设计的实际效果（每个连接独立隔离），不是官方原话。
- **技术细节核对过但未进正片**：协议当前修订版为 `2026-07-28`（改为无状态请求、移除会话、引入扩展框架与 `server/discover`）；客户端原语现为 Elicitation，Sampling 与 Logging 在该版本起弃用。这些对普通观众过细，未使用。

## 制作

本仓库 whiteboard-video-factory 工具；配音走**火山引擎语音合成**（`seed-tts-2.0` / `zh_male_liufei_uranus_bigtts`，`plan` 调用域，1.2 倍语速，凭证在 `.env`）；画面**全部由 Excalidraw 图元绘制**（本期没有用 AI 生成贴纸，`fanIcon` / `chip` / `card` 三个辅助函数写在 `scenes.js` 里）；无配乐。

## 验收

- 1920×1080，H.264 + AAC 立体声，126.0 秒（含 5.5 秒片尾品牌卡），1.2 倍语速。
- 7 场景 22 张逐 beat 静帧 + 三张封面（4:3 / 3:4 / 9:16）逐张检查；成片 3、34、120 秒抽帧检查（字幕在底、水印在右上、逐笔正常）。
- 74 条字幕；7/7 场景 TTS 逐字时间戳齐全，无缺口。
