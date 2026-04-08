# GitHub 今日热门开源 Top 5 简报

## 步骤1：启动确认

- 日期：2026-04-08
- 目标读者：开发者 / 技术团队
- 海报风格：孟菲斯网格
- 输出分辨率：2K
- 中文翻译模型：glm-5
- 当前模式：先生成内容与 Prompt，待确认后再生图

## 步骤2：内容整理

### 模块1【榜单概览】
- 日期：2026-04-08；榜单范围：GitHub Trending Top 5；主要语言：TypeScript×2、Kotlin×1、C++×1；热点方向：AI / Agent、前端 / Web、开发工具；目标读者：开发者 / 技术团队

### 模块2【Top 5 项目卡片】
1. google-ai-edge/gallery
项目是什么：一个展示端侧 ML/GenAI 用例的画廊，允许用户在本地试用和使用模型
解决什么问题：使用 Google AI Edge 探索、体验和评估端侧生成式 AI 的未来
技术栈：Kotlin、Agent Skills**：将你的 LLM 从对话者转变为……、AI Chat with Thinking Mode**：进行流畅的多轮对话……、Ask Image**：利用多模态能力识别物体、解决……
Star 数量：19066

2. google-ai-edge/LiteRT-LM
项目是什么：在 GitHub 上创建账号，为 google-ai-edge/LiteRT-LM 开发做出贡献。
解决什么问题：LiteRT-LM 是 Google 的生产级高性能开源推理框架，用于在边缘设备上部署大语言模型。
技术栈：C++、📱 跨平台支持：Android、iOS、Web、桌面端及 I…、树莓派)、🚀 硬件加速：通过 GPU 和 NPU 实现峰值性能……
Star 数量：2723

3. NVIDIA/personaplex
项目是什么：PersonaPlex 代码。在 GitHub 上创建账户，为 NVIDIA/personaplex 开发做出贡献。
解决什么问题：PersonaPlex 是一个实时、全双工的语音到语音对话模型，通过基于文本的角色提示和基于音频的声音条件控制实现角色控制。基于合成和……的组合数据训练。
技术栈：Python
Star 数量：8135

4. abhigyanpatwari/GitNexus
项目是什么：GitNexus：零服务器代码智能引擎 - GitNexus 是一个完全在浏览器中运行的客户端知识图谱创建器。放入一个 GitHub 仓库……
解决什么问题：⚠️ 重要提示：GitNexus 没有官方加密货币、代币或硬币。在 Pump.fun 或任何其他平台上使用 GitNexus 名称的任何代币/硬币均不隶属于、未受认可或未由本…
技术栈：TypeScript、层级 | CLI | Web、运行时 | Node.js (原生) | Browser (WASM)、解析 | Tree-sitter 原生绑定 | Tree-sitter WASM
Star 数量：24850

5. tobi/qmd
项目是什么：面向文档、知识库、会议记录等的小型 CLI 搜索引擎。追踪当前 SOTA 方法，且完全本地运行。
解决什么问题：一款用于记忆所有内容的本地搜索引擎。索引 Markdown 笔记、会议转录、文档和知识库。支持关键词或自然语言搜索。非常适合 Agent 流程。
技术栈：TypeScript
Star 数量：19808

### 模块3【热点方向】
- AI / Agent：代表项目 google-ai-edge/gallery、google-ai-edge/LiteRT-LM
- 前端 / Web：代表项目 google-ai-edge/LiteRT-LM、abhigyanpatwari/GitNexus
- 开发工具：代表项目 abhigyanpatwari/GitNexus、tobi/qmd

### 模块4【一句话结论】
- 今天榜单重点集中在 AI / Agent、前端 / Web、开发工具，主流语言偏向 TypeScript、Kotlin，适合优先关注能直接提升开发效率或 AI 应用落地的项目。

## 步骤3：确认后生图

- 检查 `wan_prompt.txt` 是否保持中文优先、信息适中、版面不拥挤
- 用户回复“确认生图”后，调用 Wan 2.7 生成单张 3:4 信息图海报
- 若返回 task_id，则继续查询任务状态直到出图
