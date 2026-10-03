# Claude Code Skills Collection

个人开发的 Claude Code Skills 集合，提供实用的技能工具，助力提升开发效率和内容创作。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.0.32-green.svg)
![Skills](https://img.shields.io/badge/skills-29-orange.svg)

> 分享一些好用的 Claude Code Skills，自用、学习两相宜，适用于 Claude Code v2.0 及以上版本。

## 项目介绍

本项目是个人开发的 Claude Code Skills 集合，提供实用的技能工具，助力提升开发效率和内容创作。分享一些好用的 Claude Code Skills，自用、学习两相宜，适用于 Claude Code v2.0 及以上版本。

Claude Skills 是 Claude Code 的扩展能力，通过编写技能文档（Skill.md），可以让 Claude 在特定场景下自动激活相应的专业知识和能力。

### 核心功能

- **自动化工具**: Excel 报表生成、PPT 生成、GitHub Trending 追踪
- **内容生成**: 技术文章、公众号封面、README 文档生成
- **公众号排版**: Markdown 一键排成公众号可粘贴 HTML（hailaobao-gzh-design）——7 套排版风格、AI 按规则改写、页面上一键复制、粘进编辑器样式全保留，零 npm 依赖
- **AI 多模态**: 即梦 AI 图像和视频生成、Seedance 2.0 分镜视频创作、AI 教学媒体一体化（插图/信息图/教学视频/封面/解说视频）、Grok Imagine 文生图
- **视频剪辑**: 自动化视频剪辑与解说（video-agent-kit）——通用剪辑、电影解说、足球/篮球/电竞集锦、口播配音成片（Edge TTS 免费配音）
- **视频生成**: 口播文字稿一键成片（voice-to-video）——TTS 词级时间戳 + HTML 动画引擎 + 确定性逐帧渲染，画面/字幕/语音逐词对应，13 套画面风格
- **动画视频**: 声明式分镜动画（hyperframes-10s-video）——一段文字 → 横屏动画视频 + 同名 SRT 字幕，时长（任意秒）/配色（10 套皮肤）/画幅（横竖屏）/配音（AI 口播）全部参数化，无头 Chromium 逐帧确定性渲染
- **白板讲解**: 手绘白板「边画边讲」讲解视频工厂（whiteboard-video-factory）——Excalidraw 逐笔动画 + 火山/小米/edge-tts 三通道配音 + 烧录字幕（含逐段跟读高亮） + 手绘品牌层 + 三画幅封面（4:3 / 3:4 / 9:16 抖音）+ 五平台发布文案，**时长不限（2 分钟短片到 30 分钟长片同一套流水线，按场景数伸缩）**，自带查证/合规/成片验收公共工序，画面上每一笔都是代码画的，不开剪辑软件
- **数字人口播**: IP 卡通数字人口播动画课件视频工厂（ip-talking-head-lecture）——一段逐字稿 + 一张 IP 形象图 → Remotion 成片：右下角圆形数字人常驻讲课（待机浮动 + 口型开合 + 说话光环）、主画面六套动画课件版式、字幕烧录跟读高亮，三通道配音（小米 MiMo / 火山 / edge-tts）时长由实际音频反推、音画字幕天然对齐，一条命令同出 16:9 + 9:16，自动产出各平台发布文案（YouTube 中英双语 + 章节时间轴）与中英双语 SRT/VTT，含右上角博主角标与片尾品牌卡
- **数据采集**: 微信公众号文章获取（单篇/批量下载、元数据提取、图片下载、Markdown转换）、公众号文章聚合（按公众号名称批量采集最新文章）
- **工作流工具**: Dify DSL/YML 文件生成器
- **API 文档**: 硅基流动云服务平台完整文档
- **合规审查**: 微信公众号文章合规审查（违规风险识别、修改建议）

### 适用场景

- Claude Code 用户扩展能力
- 自动化办公和内容创作
- 开源项目文档规范化
- 技术学习和实践

## Skills 清单

| Skill 名称 | 功能说明 | 技术栈 | 更新时间 | 作者 | 版本 |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------ | -------------- | ---------- | ----- |
| ip-talking-head-lecture | IP 卡通数字人口播动画课件视频工厂：一段逐字稿 + 一张 IP 形象图 → Remotion 成片。主讲 IP 以圆形头像常驻右下角讲课（待机浮动 + 三帧口型开合 + 说话光环 + 声波条），主画面自动排版的六套动画课件版式（封面 / 概念 / 步骤 / 对比 / 数据 / 总结），底部烧录字幕并做跟读高亮，品牌水印 + 顶部进度条 + **右上角可自定义博主角标** + **片尾自动追加品牌卡**（标识图或手写名 + 品牌色划线 + slogan + 黄色便签 CTA）；配音三通道（小米 MiMo / 火山引擎逐字对齐 / edge-tts 免费备胎），**时长由 TTS 实际音频反推**——改一句旁白重新 build 整体自动重排，画面、配音、字幕天然对齐，不手写任何帧数；一条命令同时出 16:9 横屏与 9:16 竖屏（另支持 1:1）；内置两套口播形象（动物卡通·海老豹 / 人物卡通·眼镜青年）一键切换、加新形象只需一个目录三帧图；自动产出各平台发布文案（视频号 / 小红书 / 抖音 / B 站 / 公众号 + YouTube 中英双语标题描述与自动合并的章节时间轴）与中英双语字幕（SRT + VTT）；全链路本地（Remotion + ffmpeg + TTS），无剪辑软件、无联网渲染 | Node.js、TypeScript、React、Remotion、小米 MiMo TTS / 火山引擎 TTS / edge-tts、ffmpeg | 2026年10月3日 | wwwzhouhui | 1.2.0 |
| whiteboard-video-factory | 手绘白板「边画边讲」讲解视频工厂：一句话选题 → 查证、写旁白、出 Logo 与贴纸、画场景、配音对字幕、逐笔渲染、混配乐、出封面、写发布文案全链路本地完成。rough.js + SVG dashoffset 逐笔手绘动画（场景可导出 Excalidraw 回灌渲染），TTS 逐字时间戳同时驱动画面排期与字幕切句（小米通道无时间戳时用静音检测估算），字幕支持**逐段跟读高亮**（卡拉OK式，念到哪一段那一段字转反白、背后套品牌色块，火山/小米/edge 三引擎通用），4 路独立 Chromium 确定性出帧（`framemd5` 可验 0 帧差），三套配音通道（火山引擎 / 小米 MiMo / edge-tts 免费备胎），**时长不限**（渲染按场景分段出片再 concat、TTS 逐场景缓存，场景数不受限，2 分钟到 30 分钟同一套流水线；长片配 `bgm.playlist` 多首轮播避免单曲循环），三画幅封面一次出（4:3 / 3:4 / 9:16 抖音），五平台发布文案（视频号 / 小红书 / 抖音 / B 站 / 公众号），自带事实核查、合规自查、成片验收与交付边界公共工序 | Node.js、Playwright（无头 Chromium）、rough.js、Excalidraw DSL、火山引擎 TTS / 小米 MiMo TTS / edge-tts、ffmpeg | 2026年9月29日 | wwwzhouhui | 1.0.0 |
| hyperframes-10s-video | HyperFrames 声明式分镜动画视频技能：一段文字 → 横屏动画视频 + 同名 SRT 字幕。**三个维度全参数化**——① 时长任意（`--total=` 或 `duration` 字段，各幕按比例精确归一，长片靠加幕）；② 配色 10 套皮肤（tech/wuding/aurora/sunset/ocean/forest/midnight/gold/candy/paper，附可视化画廊 + 预览页实时换肤）；③ 音频可选（默认无声无音轨，edge-tts 配音一键混音）。含 9 种场景类型、抽帧核验、字幕自动生成（不手写）、横竖屏可切换 | Node.js、GSAP、无头 Chromium、ffmpeg、Python（edge-tts） | 2026年9月24日 | wwwzhouhui | 2.0.0 |
| hailaobao-gzh-design | 公众号排版技能：AI 按改写规则把 Markdown 文章重排为编辑部风格（序号竖线标题、kicker 语义匹配、金句引用、摘要/信息卡片），**7 套内置风格**（玉石商务、暖色编辑部、极客单色、香槟品牌、雾霾笔记、午夜研究报告、森绿演示），一键生成带「复制到公众号」按钮的自包含 HTML，粘贴到公众号编辑器样式全保留；原始 Markdown 不改、总改动 ≤30%、代码块一字不动 | Node.js（≥16，ESM）、零 npm 依赖 | 2026年9月24日 | hailaobao2026 | 1.0.0 |
| poetry-cinema-page | 沉浸式古诗词网页生成技能：给一首中国古典诗词，走完文学分镜 → 视觉圣经 → 双服务商逐张生图（火山方舟 Doubao Seedream 5.0 / GPT-Image 网关，四档位可混用，主视觉参考链）→ 联系表检查 → 朗诵配音（edge-tts / 豆包 seed-tts-2.0，23 个中文音色）→ 滚动页面 → 浏览器验收，可选 Remotion 口播视频成片 | Python、火山引擎方舟、GPT-Image 网关、edge-tts、Vite/TypeScript、Remotion、ffmpeg | 2026年9月22日 | wwwzhouhui | 1.0.0 |
| remotion-video-factory | 视觉优先的程序化视频生产流水线：Remotion + React 代码渲染精确图形动画（矩阵/连线/图表/数字滚动/流程图解），edge-tts 中文配音自动测长并重建时间线，三层音频（配音/BGM/SFX 钉帧表），确定性渲染，双版本成片交付 | TypeScript、React、Remotion、edge-tts、ffmpeg | 2026年9月7日 | wwwzhouhui | 1.1.0 |
| photo-homework-a4 | 将拍照上传的手写作业清单识别、按科目整理并分类打标，基于固定模板生成一页 A4 纸即可打印的 HTML 作业清单，包含科目卡片、统计条、温馨提示和学生/家长签名区 | HTML/CSS、模板生成、图像识别、A4 打印 | 2026年9月5日 | wwwzhouhui | 1.0.0 |
| voice-to-video | 口播文字稿一键成片技能包：Edge TTS 配音（逐词时间戳）→ 一句口播一个场景的 HTML 动画合成 → 无头浏览器逐帧确定性渲染 MP4，文字稿/语音/画面逐词对应；13 套画面风格（每套含独立版式 DNA） | Python、edge-tts、Playwright、HTML/CSS/JS、ffmpeg | 2026年9月5日 | wwwzhouhui | 1.4.0 |
| video-agent-kit | 自动化视频剪辑与解说视频技能包：通用剪辑、电影解说（几分钟看完）、足球/篮球集锦、LOL 电竞集锦、口播配音成片，37 个 MCP 工具（抽帧理解/时间线/渲染/QC），TTS 默认 Edge TTS 免费开箱即用 | Python、MCP、ffmpeg、OpenCV、Edge TTS | 2026年8月29日 | wwwzhouhui | 0.4.3 |
| knowledge-absorber | 深度解析链接/文档/代码，生成导师级教学笔记 + Wan 2.7 知识海报。支持 PDF/Word/Markdown/代码/图片，自动真理锚定验证，国学内容自动水墨风格，11 种海报风格可选 | Python、DashScope API、Wan 2.7、真理锚定验证、信息图设计 | 2026年4月11日 | zlu | 0.0.1 |
| ai-teaching-media | AI 教学媒体一体化技能包：一个目录串联 6 个子能力（生图执行层、技术长文插图、学科信息图、教学动图/视频、短视频封面、文章解说视频），支持知识点/长文全套教学生产链路 | Python、HyperFrames、Minimax TTS、Nano Banana 2 / GPT Image 2 / Agnes Image 2.1 Flash | 2026年7月19日 | wwwzhouhui | 1.0.0 |
| grok-imagine-image | 使用 grok-imagine-image 模型，通过兼容 Grok2API / OpenAI 风格接口（`/v1/images/generations`）文生图；自带本地脚本，支持环境变量/参数覆盖、URL 改写下载、JSON 输出 | Python、Grok2API、OpenAI Images API | 2026年7月26日 | hailaobao2026 | 1.0.0 |
| github-trending-wan | GitHub Trending Top 5 中文信息图海报生成器，抓取热门项目→翻译中文摘要→生成 Wan 2.7 海报 Prompt→可视化海报，支持 10 种视觉风格，3 步引导式工作流 | Python、DashScope API、Wan 2.7、信息图设计 | 2026年4月8日 | hailaobao2026 | 1.0.0 |
| wan-cover-plus | 使用 Wan2.7-image 生成公众号封面图、小红书封面图、种草图和海报改版视觉稿，并支持文生视频、静态图转丝滑动态视频、参考图/参考视频转视频，以及为视频自动补 Edge TTS 配音与字幕烧录 | Bash、Python、Wan API、Edge TTS | 2026年4月5日 | hailaobao2026 | 1.0.0 |
| wechat-compliance-reviewer | 微信公众号文章合规审查专家，根据微信公众平台运营规范审查文章内容，识别违规风险点并给出修改建议，支持诱导分享/欺诈信息/营销推广/版权侵权等 9 大类违规检测 | Markdown、模板系统、合规审查 | 2026年3月29日 | hailaobao2026 | 1.0.0 |
| obsidian-search | Obsidian CLI 查询助手，根据自然语言检索需求生成合适的 Obsidian CLI 查询命令，支持搜索笔记、查找上下文、筛选任务、标签、属性、反链、文件列表等 | Bash、Obsidian CLI | 2026年3月13日 | hailaobao2026 | 1.0.0 |
| xiaohuihui-tech-article | 专为技术实战教程设计的公众号文章生成器，遵循小灰灰公众号写作规范，集成Gemini-3-Pro-Image-Preview双通道(自建API+Gemai公益站)自动配图与腾讯云COS上传功能，自动生成包含公众号卡片、前言、项目介绍、部署实战、总结、往期推荐的完整技术文章 | Markdown、模板生成、Gemini API、Gemai API、腾讯云COS | 2026年2月23日 | hailaobao2026 | 2.4.0 |
| wechat-article-aggregator | 微信公众号文章聚合器，通过 mptext.top API 批量获取指定公众号博主的最新文章，支持按名称或 fakeid 获取，预置 8 个热门 AI 技术公众号，输出 Markdown/HTML/Text/JSON 格式 | Python、requests、BeautifulSoup、html2text、mptext API | 2026年2月23日 | hailaobao2026 | 1.0.0 |
| seedance-video-creator | Seedance 2.0 分镜视频创作工具，三阶段工作流（分镜提示词→文生图首帧→图片+提示词生成视频），默认使用 seedance-2.0-fast 模型，支持多图参考、6 套分镜模板，自动生成首帧参考图，一键生成视频并自动下载 | Bash、curl、即梦 API、Seedance 2.0 | 2026年2月22日 | hailaobao2026 | 1.2.0 |
| wechat-article-fetcher | 微信公众号文章获取器，支持单篇和批量下载，自动提取标题、作者、公众号名称、正文、图片等元数据，支持转换为 Markdown 格式，自动下载文章图片到本地 | Python、requests、BeautifulSoup、html2text | 2026年2月22日 | hailaobao2026 | 1.0.0 |
| github-readme-generator | 专业的 GitHub 项目 README.md 生成器，自动生成符合开源社区规范的文档结构，支持 6 种项目模板（basic/full/library/webapp/cli/api），交互式生成和自动识别项目类型 | Markdown、文档生成、模板系统 | 2026年1月23日 | hailaobao2026 | 1.0.0 |
| github-trending | 获取 GitHub Trending 前五项目 README 与摘要，并发送企业微信消息，适用于热门项目跟踪、技术趋势简报与团队分享 | Python、GitHub Trending、企业微信机器人 | 2026年1月22日 | hailaobao2026 | 1.0.0 |
| jimeng_mcp_skill | AI 图像和视频生成技能，升级至 jimeng-4.5 模型，支持 ratio/resolution 新参数系统，文生图、图像合成、文生视频、图生视频四大核心能力 | MCP、Python、Docker、即梦 AI | 2025年12月14日 | hailaobao2026 | 2.0.0 |
| xiaoppt-generator-skill | 基于商务模板的专业 PPT 生成器，支持固定 25 页结构（封面→目录→4章节→结束），提供暖色调、商务简约、莫兰迪色系三种主题风格，支持 JSON 配置和代码调用 | Python、python-pptx | 2025年12月4日 | hailaobao2026 | 1.0.0 |
| dify-dsl-generator | 专业的 Dify 工作流 DSL/YML 文件生成器，根据用户业务需求自动生成完整的 Dify 工作流配置文件，支持各种节点类型和复杂工作流逻辑 | YAML、Dify DSL、工作流设计 | 2025年11月22日 | hailaobao2026 | 1.0.0 |
| xiaohuihui-dify-tech-article | 专为 Dify 工作流案例分享设计的公众号文章生成器，遵循小灰灰公众号写作规范，自动生成包含前言、工作流制作、总结的完整 Dify 案例文章 | Markdown、Dify、腾讯云 COS | 2025年11月22日 | hailaobao2026 | 1.0.0 |
| siliconflow-api-skills | 硅基流动（SiliconFlow）云服务平台文档技能，提供大语言模型 API 调用、图片生成、向量模型、Chat Completions API、Stream 模式等完整文档和最佳实践 | API、Python、REST、LLM | 2025年11月19日 | hailaobao2026 | 1.0.0 |
| mp-cover-generator | 公众号封面生成器，根据主题和标题生成现代风格的公众号封面图，支持描边卡通字体、垂直居中布局，可输出 HTML 和高清图片（PNG/JPG），使用 Playwright 实现完整页面截图 | MCP、HTML/CSS、Node.js、Playwright、即梦 AI | 2025年11月15日 | hailaobao2026 | 3.1.1 |
| excel-report-generator | 自动化 Excel 报表生成器，支持从 CSV、DataFrame、数据库生成专业 Excel 报表，包含图表、样式、模板填充等高级功能 | Python、pandas、openpyxl、xlsxwriter | 2025年11月12日 | hailaobao2026 | 1.0.0 |

## Skill 功能详解

### 🎤 IP Talking Head Lecture（IP 数字人口播动画课件视频工厂）

**核心功能：**

- ✅ **一句话概括工作流**：写一个 `script.json`（每场景一段 `narration` 旁白 + `heading` 标题 + `kind` 版式 + `data` 内容槽）→ `iph all <期>` → 拿到 mp4；期目录、配音、时间轴、字幕、发布文案全部由命令生成，**唯一手写的就是 script.json**
- ✅ **IP 数字人常驻讲课**：主讲形象以圆形头像常驻右下角（横屏）/ 底部（竖屏），待机时极缓浮动，说话时三帧口型（闭口/微张/张口）随音频开合，外圈品牌色「说话光环」+ 声波条；内置两套形象可一键切换——动物卡通（海老豹）与人物卡通（眼镜青年），加新形象 = 一个目录放三帧同名图 + config 登记一行，`iph avatars` 即可见
- ✅ **六套动画课件版式**：封面 cover / 概念 idea / 步骤 steps / 对比 compare / 数据 numbers（数字滚动 countUp）/ 总结 recap，横屏走左右分栏多列、竖屏自动改纵向堆叠；每个场景按旁白逐条揭示要点，画面跟着声音走
- ✅ **时长由实际音频反推**：TTS 逐场景合成后用真实音频时长重建时间轴（lead + 音频 + tail），每个词的时间戳同时驱动字幕切句与跟读高亮——改一句旁白重新 build 就整体重排，不需要手调任何帧数
- ✅ **三通道配音**：小米 MiMo TTS（默认，小句级时间戳）／ 火山引擎（逐字对齐，支持声音复刻）／ edge-tts 免费备胎；语速、响度、音色全在 `config.json`，凭证走 `.env`
- ✅ **品牌层可配置**：左下水印、**右上角博主角标**（`brand.corner`，text 留空自动用 `brand.name`，可关）、顶部场景进度条，以及**片尾品牌卡**（`brand.endCard`：build 时自动在末尾追加一个静音 outro 场景——标识图或手写体博主名 + 星花 + 品牌色划线逐笔画出 + slogan + 黄色便签 CTA「点赞 · 关注 · 评论区聊聊」），`brand.logo` 给图就代替手写名
- ✅ **一条命令双画幅**：16:9（1920×1080，B 站/课程）与 9:16（1080×1920，抖音/视频号/小红书）同时出片，另支持 1:1；crf、并行度可调
- ✅ **发布物料一并产出**：中文 SRT/VTT +（条数对齐时）英文 SRT/VTT、旁白稿表格、各平台发布文案（视频号 / 小红书 / 抖音 / B 站 / 公众号 + YouTube 中英双语标题描述与**自动合并的章节时间轴**，满足 YouTube ≥3 章、每章 ≥10s 的规则）
- ✅ **确定性本地渲染**：Remotion + ffmpeg 全本地，无需剪辑软件、无需云端；配音与逐场景产物带缓存，只改文案时秒级重发布案

**工作流程：**

`iph new "<标题>"` 建期 → 写 `episodes/<期>/script.json`（口播短句、heading ≤12 字）→ `iph voice` 配音自检 → `iph build <期>`（TTS + 时间轴 + 字幕 + 发布文案）→ `iph still` 抽静帧查版式 → `iph render` 出成片 → 抽帧目视验收（角标 / outro / 字幕高亮）→ 交付

**关键命令：**

```bash
SK="~/.claude/skills/ip-talking-head-lecture"
I="$SK/bin/iph"

$I new "Meta Muse国内0门槛注册全攻略"      # 建期目录 + script.json 模板
$I voice                                   # 配音自检：回显引擎/音色/端点并真跑一句
$I build "Meta Muse国内0门槛注册全攻略"     # TTS + 时间轴 + 字幕 + 发布文案
$I still "Meta Muse国内0门槛注册全攻略" 8   # 第 8 秒静帧，看版式
$I render "Meta Muse国内0门槛注册全攻略" --ratio=16:9,9:16
$I all "Meta Muse国内0门槛注册全攻略"       # build + render 一条龙
$I avatars                                 # 列出可用口播形象
$I preset human                            # 切换默认形象（写进 config.json）
$I srt "Meta Muse国内0门槛注册全攻略"       # 只看字幕条时间与文本
```

**参数速查：**

| 维度 | 在哪儿改 | 默认 |
| --- | --- | --- |
| 配音引擎 / 音色 / 语速 | `config.json` → `tts.engine`（`mi` / `volc` / `edge`）、`tts.voice`、`tts.speed` | 小米 MiMo · 冰糖 @1.15x |
| TTS 凭证 | `.env`（`VOLC_TTS_API_KEY` / `MI_TTS_API_KEY` 等，**勿提交**） | — |
| 画幅集合 / 帧率 / 并行度 | `video.ratios` / `fps` / `concurrency` | 16:9 + 9:16 / 30 / 4 |
| 节奏 | `pacing.leadPadding` / `tailPadding` / `minSceneSeconds` / `sceneGap` | 0.85 / 0.7 / 3.2 / 0.25 |
| 品牌层 | `brand.name` / `accent` / `slogan` / `corner` / `endCard` / `logo` | 见 config |
| 数字人形象 | `avatar.preset` 或 `iph preset <名>`；形象目录三帧 `image/mouth-mid/mouth-open` | haibao |
| 字幕切句 | `cues.*`（每句字数上下限等） | 见 config |
| 期目录 / 产物目录 | `dirs.projects` / `dirs.build` | `episodes/` / `build/` |

**目录要点：** `bin/iph`（CLI：new / build / publish / render / all / still / srt / voice / kinds / avatars / preset）、`lib/build.mjs`（script.json → 配音 → timeline-16x9/9x16.json + 字幕 + 发布文案，时间轴是"整个视频的唯一真相"）、`lib/tts/`（小米 / 火山 / edge 三通道）、`lib/publish.mjs`（各平台文案渲染）、`remotion/`（React 工程：`SceneShell` 品牌层与角标、`scenes/index.tsx` 六套版式 + outro、`Avatar` 口型数字人）、`references/`（script-format / avatar / voices / publish / delivery-qa 五份）、`templates/`（每期 script.json 模板）

**适用场景：** 有固定 IP 形象（卡通头像即可）的知识口播 / 工具实测 / 热点讲解账号内容；一条稿子要同时喂 B 站横屏与抖音/视频号竖屏；需要改一句话就整体自动重排、拒绝手调时间轴；与 `whiteboard-video-factory`（手绘白板边画边讲）、`voice-to-video`（无形象口播逐词成片）、`remotion-video-factory`（纯图形动画）互补，覆盖「有 IP 真人感出镜」这一环

**示例成片：** 《Meta Muse 爆火，国内 0 门槛注册全攻略》——8 场景 + 自动片尾卡，128.2 秒，16:9 与 9:16 双画幅一次出，含中英双语字幕与各平台发布文案（由文章稿 → `script.json` → `iph all` 全流程产出），点击下方播放器直接在线观看

**横屏 16:9（1366×768）：**

<p align="center">
  <video src="https://github.com/user-attachments/assets/7269fb42-47e7-4b49-bba8-52acab3f5784" controls muted playsinline width="100%"></video>
</p>

**竖屏 9:16（768×1366）：**

<p align="center">
  <video src="https://github.com/user-attachments/assets/7d425a7d-43d1-4dd6-9fcd-9060bf56fe21" controls muted playsinline width="45%"></video>
</p>

### 🖊️ Whiteboard Video Factory（手绘白板「边画边讲」讲解视频）

**核心功能：**

- ✅ **一句选题 → 一条成片**：查证 → 写旁白（按 `|` 切 beat）→ 出 Logo 与贴纸 → 画场景 → 配音对字幕 → 逐笔渲染 → 混配乐 → 出封面 → 写发布文案，全链路本地跑，不开剪辑软件、不露脸
- ✅ **逐笔手绘动画**：rough.js（Excalidraw 底层同款）生成线条，SVG `stroke-dashoffset` 按子路径顺序描边、rough.js 的「每条边描两遍」拆成 A/B 两层错时浮现，笔尖跟着走；场景同时导出 Excalidraw 格式，能在 Obsidian 里改图再回灌渲染
- ✅ **音画同步不拍时间轴**：TTS 返回的逐字时间戳同时驱动画面排期与字幕切句（6~20 字），改一句旁白只重配那一段
- ✅ **配音双通道**：火山引擎语音合成（官方音色或自己的声音复刻，默认 1.2 倍语速）／ 没有凭证时切 edge-tts 免费出片，两者输出同格式逐字时间戳，字幕链路不用改
- ✅ **贴纸与真实 Logo**：贴纸走本地 codex CLI 出 2×2 四宫格（一次额度同风格，自动抠白底、去杂点、去邻格残片）；公司/产品 logo 走 Wikimedia Commons 官方 SVG，`--vs` 可拼 A VS B 对比封面图，出处自动记录
- ✅ **确定性并行渲染**：4 路独立 Chromium 交错出帧，主进程按帧号顺序喂 ffmpeg；`workers=1` 与 `workers=4` 出的帧用 `framemd5` 比对必须 0 帧不同
- ✅ **三画幅封面一次出**：同一个 `coverLayout` 出 4:3（1440×1080）／ 3:4（1080×1440）／ 9:16（1080×1920 抖音，内容压在中央安全区），标题 ≤2 行、钩子行自动马克笔高亮
- ✅ **品牌层自动带**：右上角手写水印（第一幕逐笔画入）+ 片尾品牌卡 + 封面品牌标，名字 / 品牌色 / slogan 都在配置里
- ✅ **自带公共工序（合并自 `video-common`）**：事实核查与来源台账、发布前合规自查、成片机器与目视验收、交付边界，全部收在 `references/`，装一个目录即可跑

**工作流程：**

选题 → 查证（数字进期目录 `README.md`）→ 写旁白（`scenes.js`）→ `wb logo` / `wb image` 出素材 → 画场景 → `wb stills` 逐 beat 静帧检查 → 写 `cover` 函数出三张封面 → `wb build` 一条龙出片（TTS + 渲染 + 混音 + 封面）→ 抽帧验收 → 写 `发布.md`（五平台文案）

**关键命令：**

```bash
SK="~/.claude/skills/whiteboard-video-factory"
W="$SK/bin/wb"

$W new "为什么定了计划总是坚持不下去"          # 建期目录（scenes.js + 发布.md 模板）
$W logo "标题" logo-claude="Claude AI symbol.svg"   # 官方 Logo → assets/
$W image "标题" stepper="A simple side-view bicycle"  # 贴纸，一次 ≤4 张
$W stills "计划"                                 # 每 beat 静帧，逐张查排版
$W cover "计划"                                  # 封面-4x3 / 封面-3x4 / 封面-9x16
$W build "计划"                                  # 出片 → build/<期>/outputs/final.mp4
```

**参数速查：**

| 维度 | 在哪儿改 | 默认 |
| --- | --- | --- |
| 语速 | `config.json` → `tts.speed` | 1.2 倍 |
| 配音引擎 / 音色 | `tts.engine`（`volc` / `edge`）、`tts.voice`、`.env` | 见 config |
| 配乐音量与闪避 | `bgm.gain` / `bgm.speak` / `bgm.gap` | 0.5 / 0.1 / 0.22 |
| 笔速与每字秒数 | `render.pen.speed` / `pen.charSeconds` | 1000 px/s / 0.06~0.2s |
| 出帧并行度 | `render.workers` | 4 路 |
| 字幕字号 / 基线 | `captions.fontSize` / `baselineY` | 46 / 1022 |
| 品牌层 | `brand.name` / `accent` / `slogan` / `logo` | 见 config |
| 封面画幅与系列标签 | `cover.ratios` / `cover.seriesTag` | 4:3 / 3:4 / 9:16 |
| 每期内容目录 | `dirs.projects` / `dirs.build`（可指到 Obsidian 仓库） | `./episodes` / `./build` |

**目录要点：** `bin/wb`（CLI 一条龙）、`lib/scene-dsl.js`（场景 DSL，一行一个元素，导出 Excalidraw + 旁白稿 + 封面）、`lib/render.html` + `lib/render.js`（逐笔渲染器与并行出帧）、`lib/tts-volc.mjs` + `lib/tts-edge.py`（双配音通道，均带内容指纹缓存）、`lib/captions.cjs`（逐字时间戳切句、烧录并导出 SRT）、`lib/gen-image.mjs`（codex 生图 + Canvas 抠图）、`lib/fetch-logo.mjs`（Commons 官方 Logo）、`lib/mix-bgm.mjs`（手写 DSP 闪避配乐）、`references/`（dsl / scene-patterns / stickers / publish / fact-check / compliance / delivery-qa 七份）、`examples/`（一期完整示例）

**适用场景：** 概念与机制讲解、公司／产品／财报拆解、热点背后的原理科普、需要不露脸且能批量出片的账号内容；与 `hyperframes-10s-video`（声明式分镜动画）、`remotion-video-factory`（代码级精确图形动画）、`voice-to-video`（口播逐词成片）互补，覆盖四种不同的视频生产方式

**🎬 示例成片：** 一期完整的白板讲解片（1920×1080 / 30fps，AI 配音 + 烧录字幕 + 手绘品牌层），由本技能「选题 → 查证 → 写旁白 → 画场景 → 配音对字幕 → 逐笔渲染 → 混配乐」全流程产出，点击下方播放器直接在线观看

<p align="center">
  <video src="https://github.com/user-attachments/assets/88c6c222-7661-4a9b-ae5e-6c555de8c69e" controls muted playsinline width="100%"></video>
</p>

另有仓库内可直接播放的 [白色背景前 40 秒样片](whiteboard-video-factory/assets/sample-preview.mp4)，以及 [字幕跟读高亮字幕带特写](whiteboard-video-factory/assets/sample-highlight.gif)（色块随语音跳到当前念到的字）；完整示例工程在 `whiteboard-video-factory/examples/`

### 🎞️ HyperFrames Kinetic Video（声明式分镜动画视频）

**核心功能：**

- ✅ **声明式分镜**：`scenes.json` 描述「结构 + 每幕动作」，GSAP 按时间轴执行；内置 9 种场景类型（`title` / `end` / `bigword` / `quote` / `flow` / `points` / `bars` / `typewriter` / `free`）
- ✅ **时长全参数化**：默认 10 秒，`--total=20` 或顶层 `"duration": 15` 可产任意时长——各幕 `dur` 按比例归一、末幕吸收舍入漂移，总和**精确等于目标**（0.01s 级）；长片靠「加幕」而非拉长单幕，避免画面长久静止
- ✅ **10 套配色皮肤**：`tech` / `wuding` / `aurora` / `sunset` / `ocean` / `forest` / `midnight` / `gold` / `candy` / `paper`（含浅底深字），同一分镜换肤即换风格；附可视化挑色画廊，预览页控制条下拉框可实时切换
- ✅ **音频可选、不写死**：默认无声（无音轨）；要求「带语音」即写 `script.json` → edge-tts 生成整轨配音 → `--keep-dur` 让配音贴合每幕时长 → 混音为 `<slug>-...-a.mp4`
- ✅ **字幕自动生成（不手写）**：`make_srt.mjs` 按分镜或语音时间轴切分，时间轴与画面同源（`--eff` / `--timing`），长片也不会错位；某幕可用 `"srt"` 字段精确覆盖
- ✅ **逐帧确定性渲染**：渲染走 `window.__KINETIC__.seek(t)`（GSAP timeline pause + seek），与机器快慢无关——不掉帧、同输入同输出
- ✅ **画幅与帧率可切**：`--orient=portrait` 出竖屏 1080×1920，`--fps=60` 改帧数不改时长
- ✅ **先抽帧后全量**：全量渲染前必看 `_preview` 静帧或跑 `check_overflow.mjs`，程序化拦截文字溢出与页面报错

**工作流程：**

内容拆幕 → 写 `scenes.json`（定皮肤、定目标时长）→ `build_html.mjs` 生成自包含动画页（顺带产出 `*.effective.json` 生效分镜）→ 抽帧核验 → 全量逐帧渲染 → `encode.mjs` 编码 H.264 →（可选）TTS 生成配音并混音 → `make_srt.mjs` 出字幕 → ffmpeg 复核 Duration / 码流 → 交付

**关键命令：**

```bash
SK="~/.workbuddy/skills/hyperframes-10s-video"

# 构建：20 秒 + candy 配色（同时产出 out.effective.json）
node "$SK/scripts/build_html.mjs" scenes.json out.html --total=20 --skin=candy

# 抽帧核验 → 全量渲染 → 编码成片
node "$SK/scripts/render.mjs"  out.html _preview --only=60,240,500
node "$SK/scripts/render.mjs"  out.html _frames
node "$SK/scripts/encode.mjs"  _frames out-1920x1080-30fps.mp4

# 自动字幕（务必用 build 产出的生效分镜，保证与画面同源）
node "$SK/scripts/make_srt.mjs" scenes.json out-1920x1080-30fps.srt --eff=out.effective.json

# 带 AI 配音：先写 script.json（每幕一句口播），再 TTS + 混音
python "$SK/scripts/tts_scenes.py" script.json scenes.json . --keep-dur --rate=+15%
ffmpeg -y -i out-1920x1080-30fps.mp4 -i voice.mp3 -c:v copy -c:a aac -b:a 192k -shortest out-1920x1080-30fps-a.mp4
```

**参数速查：**

| 维度 | 怎么给 | 默认 |
| --- | --- | --- |
| 时长 | `--total=20` 或 `scenes.json` 顶层 `"duration": 15` | 10 秒 |
| 配色 | `--skin=candy` 或 `"skin":"candy"`（10 选 1，未知值回退 `tech`） | `tech` |
| 音频 | 说「带语音」或 `"audio":true` | 无声 |
| 画幅 / 帧率 | `--orient=portrait` / `--fps=60` | 横屏 1920×1080 / 30fps |
| 角标 / 页脚 | `--badge=` / `--foot=` | `海老豹666` / 空 |

**目录要点：** `assets/template.html`（动画模板 + 10 套皮肤 + 控制条）、`scripts/`（7 个可独立运行的脚本）、`references/scenes_schema.md`（分镜字段完整定义）、`references/prompt-template.md`（对话用标准提示词模板）、`references/skin-gallery.html`（10 套配色实拍帧画廊）、`references/example-rsi/`（完整可复现范例：分镜 + 字幕）

**适用场景：** 概念/观点的动画讲解短视频、公众号与视频号配套动画、产品与数据要点可视化、需要批量换配色出多版本的投放素材；与 `remotion-video-factory`（代码级精确图形动画）、`voice-to-video`（口播逐词成片）互补，覆盖三种不同的视频生产方式

**🎬 演示视频（示例成片）：** AI 自我进化（RSI）主题动画讲解片（1920×1080 / 30fps，含 AI 配音），即由本技能「一句话 → 分镜 → 渲染 → 混音」全流程产出，点击下方播放器直接在线观看

<p align="center">
  <video src="https://github.com/user-attachments/assets/398430c5-7277-4382-8d2d-feff8727ff9f" controls muted playsinline width="100%"></video>
</p>

### 📐 Hailaobao GZH Design（公众号排版 —— Markdown 一键变可粘贴 HTML）

**核心功能：**

- ✅ **Markdown → 公众号可粘贴 HTML**：产物是自包含 HTML 页面，顶栏一个 **[ 复制到公众号 ]** 按钮，点一下把带内联样式的正文写进剪贴板（`text/html`），粘进公众号后台样式全保留 —— 不经过任何第三方排版网站，不丢格式
- ✅ **7 套排版风格**：`jade-business`（玉石商务）/ `warm-editorial`（暖色编辑部）/ `mono-tech`（极客单色）/ `champagne-brand`（香槟品牌）/ `mist-notebook`（雾霾笔记）/ `midnight-report`（午夜研究报告）/ `forest-demo`（森绿演示）；每套是「主题色 + 版式 + 强调样式 + 组件皮肤」的整套预设，传未知 id 会直接报错并列出可用值
- ✅ **AI 按规则改写，不生成新事实**：标题加「序号 | 主标题 | 小字副标题」竖线语法；kicker 语义匹配（顺序动作用 `STEP`、并列要点用纯数字 `01/02`、案例 `CASE`、章节 `PART A`、问答 `Q1`、误区 `AVOID`、数据 `FACT`…不一律甩 `STEP`）；关键短语加粗、金句转引用、`---` 控制视觉呼吸、按需插 `<SummaryCard>` / `<InfoCard>` 卡片
- ✅ **原文零损伤**：改写结果写到临时文件，原始 Markdown 一个字不动；总改动 ≤ 30%，代码块一字不改，不加原文没有的观点与事实
- ✅ **先问风格再动手**：风格是编辑决策，默认必须让用户挑 —— 给出「首选（附理由）+ 同类型备选 + 反差款」三选一；用户点名了 scheme 或说了「你决定 / auto」才自动选
- ✅ **零依赖、跨 agent**：只需 Node.js ≥ 16（ESM），脚本仅用内置 `fs` / `path`，无 npm 包、无需联网；Claude Code 读 `SKILL.md` 的 YAML frontmatter 自动挂载，Codex / WorkBuddy / Cursor / Cline / 手动 Prompt 走同目录 `AGENTS.md` 对等入口，产物完全一致

**工作流程：**

读文章并判定体裁（方法论 / 教程 / 评测 / 心得 / 资讯）→ 问用户挑 scheme → AI 按改写规则产出临时 Markdown → `typeset.mjs` 渲染带复制按钮的 HTML → 交付（说清用了哪套风格、改了哪 3–5 处、产物绝对路径）

**关键命令：**

```bash
node ~/.workbuddy/skills/hailaobao-gzh-design/scripts/typeset.mjs \
  --input article.rewritten.md \
  --scheme forest-demo \
  --title "文章标题" \
  --out article.html
```

**参数速查：**

| 参数 | 说明 | 默认 |
| --- | --- | --- |
| `--input` | 改写后的 Markdown 路径 | 必填 |
| `--scheme` | 7 选 1 的风格 id（未知值 exit 1 并列出可用 id） | `jade-business` |
| `--title` | HTML 顶栏显示的文章名 | `公众号排版` |
| `--out` | 产物 HTML 路径 | 与 `--input` 同目录同名 `.html` |

**体裁 → 风格匹配（速查）：** 方法论 / AI 观点 → `jade-business`；教程 / 命令行 / bug 复盘 → `mono-tech`；工具教程 / 案例演示 → `forest-demo`；心得 / 复盘 / 阅读 → `warm-editorial`；品牌 / 活动 / 产品发布 → `champagne-brand`；学习笔记 / 干货清单 → `mist-notebook`；行业分析 / 数据 / 财经 → `midnight-report`；拿不准默认 `jade-business` 兜底

**目录要点：** `SKILL.md` + `AGENTS.md`（双入口）、`references/style-schemes.md`（7 套 scheme 目录 + 匹配决策表）、`references/formatting-rules.md`（改写方法论 + before/after）、`references/typesetting-syntax.md`（扩展 Markdown 语法）、`references/demo-article-patterns.md`（工具教程/演示型文章排版模式）、`scripts/schemes.mjs`（风格样式生成）+ `scripts/typeset.mjs`（主渲染脚本）、`examples/`（demo 与 remotion-demo 两组样例输入输出）

**适用场景：** 公众号长文/技术文/复盘文一键排版；同一篇稿换多套风格出 A/B 版本；从 Markdown 工作流（Obsidian 等）直通公众号后台；与 `xiaohuihui-tech-article`（写稿 + 配图 + COS 图床）、`wechat-compliance-reviewer`（发布前合规审查）串成「写稿 → 排版 → 合规 → 发布」链路 —— 本 skill 只负责其中「排版」一环，不改文字内容

**使用示例：**

```
帮我排版这篇文章，用森绿演示风格：E:\notes\remotion-article.md
把这篇 md 排成公众号能直接粘贴的样式，风格你决定
```

### 🏮 Poetry Cinema Page（沉浸式古诗词网页生成）

**核心功能：**

- ✅ **文学分镜**：按空间/时间/人物/动作/修辞/情绪转折拆 5–8 个视觉段落，不是机械地每两句配一张图
- ✅ **统一视觉圣经 + 参考链**：主视觉文生图定调，后续每张图都以它作图生图参考，人物、地理、服饰、色彩与镜头语言整套锁死
- ✅ **双服务商四档位**：火山引擎方舟 Doubao Seedream 5.0（`pro`/`lite`）与 GPT-Image 网关（`gpt-2`/`gpt-2.5`），可按段落混用，参考链跨服务商不断
- ✅ **沉浸式滚动页面**：固定图片舞台、双层交叉淡入、克制视差、章节导航；桌面卡片不超半屏，移动端 contain 主图 + 模糊背景
- ✅ **内置朗诵配音**：edge-tts（免费本地）与豆包 seed-tts-2.0 双引擎、23 个中文音色，输出音轨 + 逐行时间轴 + SRT
- ✅ **口播视频（可选）**：Remotion 渲染 1920×1080/30fps，每段一镜的克制运镜、硬切双层级字幕、片头尾字卡、胶片颗粒与暗角，确定性渲染
- ✅ **完整工程验收**：生产构建 + 真实浏览器 QA（桌面/移动端/音频/控制台/prefers-reduced-motion），生成图必须过联系表才允许进页面

**工作流程：**

核对原文与分镜 → 建立视觉圣经 → 文生图出主视觉 → 逐段图生图（带 `ref`）→ 联系表检查 → 生成朗诵音轨 → 实现滚动页面 → 生产构建与浏览器 QA →（可选）video-plan → Remotion 成片

**关键命令：**

```bash
python scripts/ark_image.py probe                  # 免费验证密钥与地址
python scripts/ark_image.py batch --plan plan.json # 整首诗一次跑完，重跑跳过已完成
python scripts/narration.py audition               # 23 个音色试听后再定音色
python scripts/video.py run --plan video-plan.json --workspace out/video
```

**适用场景：** 古典诗词电影感网页、面向学生的教学解读页、已有诗词站扩页与互链、把已生成语料再做成朗诵/讲解视频、复用「主视觉 → 参考链」一致性方法论

**示例作品（讲解版口播视频）：** 李白《将进酒》讲解版成片（1920×1080 / 30fps），点击下方播放器直接在线观看

<p align="center">
  <video src="https://github.com/user-attachments/assets/598b5cd5-ffe9-47be-b858-0182c92a204a" controls muted playsinline width="100%"></video>
</p>

<p align="center">
  <a href="https://github.com/wwwzhouhui/skills_collection/releases/download/poetry-cinema-demo/jiang-jin-jiu-with-meaning.mp4"><img alt="下载 1080p 高清版（MP4）" src="https://img.shields.io/badge/%E2%AC%87%20%E4%B8%8B%E8%BD%BD%201080p%20%E9%AB%98%E6%B8%85%E7%89%88-MP4-181717?style=for-the-badge&logo=github&logoColor=white"></a>
</p>

### 🎬 Remotion Video Factory（视觉优先的程序化视频工厂）

**核心功能：**

- ✅ **精确图形动画**：注意力矩阵、拓扑连线、数据图表、数字滚动、流程图解全部由 Remotion + React 代码绘制，文字零乱码、结构可参数化
- ✅ **AI 配音自动对齐**：edge-tts 分段生成 + ffprobe 实测时长，build-timeline.mjs 按实测重建时间线（场景 = max(视觉最短, 配音+40f)），旁白永不被画面切走
- ✅ **三层音频**：配音 + BGM（淡入出，可开关）+ SFX 钉帧表（相对帧表达式，时间线平移自动跟随）
- ✅ **确定性渲染与双版本交付**：同样输入永远渲出同样的帧；带 BGM / 无 BGM 双版本 + 逐句 SRT 字幕

**工作流程：**

简报与分镜 → 拷贝模板工程 → tts.py 生成配音并测长 → build-timeline.mjs 重建时间线 → 逐镜头实现场景组件（8 种动画模式词汇表）→ 声音设计 → 双版本渲染交付

**适用场景：** 技术讲解/科普动画视频；把概念、数据、架构、算法做成动画演示（矩阵、连线、图表、公式、流程为主角的内容）

**🎬 演示视频（示例成片）：**

<p align="center">
  <video src="https://github.com/user-attachments/assets/a9d6086a-b423-47f1-af17-d698485dc942" controls muted playsinline width="100%"></video>
</p>

> **▶️ 下载原片**：[备用直链](https://obsidian.duckcloud.fun/files/final-a96bf69c66dc90f4c03e5bf691d232ecb27d92d0.mp4)

### 📝 Photo Homework A4（拍照作业 → A4 打印清单）

**核心功能：**

- ✅ **手写作业识别**：读取用户上传的作业照片，逐条提取作业内容并按科目分组
- ✅ **作业分类打标**：自动识别背诵类、书面类、阅读类和材料类作业，并使用对应颜色标签
- ✅ **A4 单页清单**：基于内置模板生成固定版面的 HTML 文件，包含科目卡片、统计条、温馨提示和签名区
- ✅ **打印友好**：严格遵循 A4 纵向单页约束，支持打印后手写勾选和学生/家长签名
- ✅ **内容统计**：自动统计科目数、作业总数以及背诵类、书面类、材料类作业数量
- ✅ **可选交互版**：用户未限定只要打印版时，可额外生成支持点击打卡和进度条的屏幕交互版

**工作流程：**

1. 读取作业照片，识别手写内容和日期
2. 按语文、数学、英语等科目整理作业条目
3. 根据作业语义添加背诵、书面、阅读或材料标签
4. 复制 `assets/homework-a4-template.html` 并填充识别结果
5. 调整科目卡片、颜色和统计数据，检查总高度不超过一页
6. 输出 `作业清单-A4打印版.html`，并附上可核对的作业内容表格

**版面特点：**

- 使用双列科目卡片布局，科目数量较多或条目较长时自动收窄间距和字号
- 内置蓝、绿、紫、橙、红、青六套主题色，科目重复时循环使用
- 内置物理、数学、化学、英语、历史、语文、生物、地理、政治等科目图标
- 保留卡片内分页保护，避免打印时单张科目卡片被拆分

**使用示例：**

```
请识别这张作业照片，按科目整理成一页 A4 可打印的作业清单。
```

**输出与打印：**

- 输出 HTML 文件，使用浏览器打开后按 `Ctrl + P` 打印
- 打印设置选择 A4、纵向，边距选择“无”或“默认”，确保完整打印在一页纸上
- 对识别不确定的手写条目，在交付时单独提醒用户核对

**效果图：**

![image-20260905123556184](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20260905123556184.png)


---

### 🎬 自动化视频剪辑与解说（video-agent-kit）

**核心功能：**

- ✅ **通用视频剪辑**：素材发现 → 抽帧理解 → 时间线编辑 → 预览渲染 → QC 质检
- ✅ **电影解说**：全片抽帧 + 对白转写 → 解说词编排 → 字幕烧录 → 配音成片
- ✅ **体育/电竞集锦**：足球、篮球、LOL 比赛自动高光编排 + 中文解说配音
- ✅ **口播配音成片**：脚本/文档 → Edge TTS 逐段配音 → 图文画面 → ffmpeg 合成
- ✅ **TTS 免费开箱即用**：默认 Edge TTS（晓晓/云希/云健等中文音色），无需 API Key
- ✅ **37 个 MCP 工具**：`inspect_media`、`video_ingest`、`video_watch_segment`、`subtitle_build/render`、`validate_timeline`、`render_preview`、`qc_preview`、`synthesize_narration`、`bind_narration`、`render_narrated`、`soccer_*`、`lol_*` 等

**5 个子技能：**

| 子 skill | 作用 | 典型输入 | 输出 |
|---------|------|----------|------|
| `video-edit-agent` | 总控制器：任务分类与路由 | 任意剪辑需求 | 任务方案与执行路由 |
| `video-edit-assembly` | 多素材组装/混剪/去重/蒙太奇 | 素材文件夹 | 组装后的时间线/成片 |
| `video-recap-workflows` | 电影解说 + 足球/篮球/电竞集锦 | 电影/比赛视频 | 中文解说成片 final.mp4 |
| `video-speech-workflows` | 口播浓缩/字幕修复/视频流水线 | 口播视频 | 精剪/字幕/流水线方案 |
| `env-setup` | 环境体检与依赖安装 | 新机器 | 依赖报告/自动修复 |

**快速使用：**

```text
# 文档/文章 → 中文解说视频
请把这篇文档转成一段 2 分钟的中文解说视频：<贴入内容>

# 本地视频混剪
把 footage/ 目录下的素材剪成一条 30 秒的混剪，突出动作镜头，配上字幕

# 电影解说
几分钟看完《<电影名>》：<电影文件路径>

# 足球集锦
把这场球赛剪成 3 分钟集锦，带中文解说：<比赛文件路径>
```

> 详细安装与配置（MCP 注册、Python 依赖、TTS 音色）见 [video-agent-kit/README.md](video-agent-kit/README.md)。

### 🎬 口播文字稿一键成片（voice-to-video）

**核心功能：**

- ✅ **无素材出片**：输入一段口播文字稿（甚至只给一个主题），即可生成完整视频，画面全部程序化生成
- ✅ **TTS 词级时间戳**：Edge TTS 合成配音并返回每个词的精确时间，自动产出逐句/逐词时间轴与 SRT 字幕
- ✅ **画音逐词对应**：一句口播 = 一个动画场景，底部字幕逐词卡拉OK高亮——声音念到哪，画面切到哪
- ✅ **确定性渲染**：无头浏览器逐帧 seek 截图后合成，同样输入永远渲出同样每一帧，可 git 管理、看 diff、断点续渲
- ✅ **13 套画面风格**：BlockFrame 积木、暗夜 HUD、编辑杂志、终端极客、手绘白板、极简瑞士、国潮水墨、玻璃拟态、黏土软胶、蓝图工程、像素游戏等，每种风格有独立版式 DNA（布局骨架/编排/动效签名，非简单换色）
- ✅ **外挂字幕**：自动产出 `subtitles.srt` 供视频平台上传
- ✅ **作者水印**：`--watermark laohaibao2025` 一键右下角落款（渲染时注入、不改合成页，深浅底色均清晰）

**🎬 视频案例：公众号文章 → 深蓝舞台解说视频（端到端实拍成片）**

<p align="center">
  <video src="https://github.com/user-attachments/assets/5618e4fb-5acb-402e-ac87-c329cd2a6d46" controls muted playsinline width="100%"></video>
</p>

> **▶️ 下载 1080p 原片**：[仓库文件](https://github.com/wwwzhouhui/skills_collection/blob/main/README.assets/voice-to-video-demo-kimi.mp4) · [备用直链](https://obsidian.duckcloud.fun/files/final-fcdaf7c2dda61ee8a0d04ce89f896a8d27e28262.mp4)
>
> 上方案例由本技能端到端生成：输入公众号文章《Kimi 快跟上 Fable 5 了？》（约 2500 字）→ 浓缩为 600 字口播稿 → Edge TTS 配音（词级时间戳）→ 深蓝舞台风格 8 场景合成 → 无头浏览器确定性渲染成片。**成片 1 分 54 秒 · 1080p30 · 约 6MB**。
>
> 案例看点：画面元素逐词跟随配音出场——念到「2.5 万亿」参数卡弹入、念到「蒸馏了」渐变大字砸出、念到「封神 / 贴脸」红绿对比卡先后出现、念到「≈1%」价格大数字弹出；底部字幕逐词卡拉OK高亮，声音念到哪，高亮到哪；右下角 `laohaibao2025` 为作者水印落款。

**目录结构：**

```
voice-to-video/
├── SKILL.md                        # 技能入口：六步工作流（自检→定稿→TTS→合成→预览→渲染）
├── scripts/
│   ├── tts.py                      # 口播稿 → voice.mp3 + timeline.json + subtitles.srt/js
│   └── render.py                   # 合成页 → 逐帧截图 → ffmpeg 合成 MP4（支持断点续渲）
├── assets/
│   ├── engine.js                   # 确定性动画引擎（HF.seek，一切画面状态是时间的纯函数）
│   ├── kit.css + kits/（12 套）     # 画面风格皮肤
│   └── template.html               # 合成页模板
└── references/
    ├── composition-guide.md        # 合成页编写规范
    └── styles.md                   # 风格目录 + 版式 DNA + 自动匹配规则
```

**工作流程：**

1. 整理口播稿（纯文本，按句读分段；只给主题则先写稿确认）
2. `tts.py` 生成配音与逐句/逐词时间轴
3. 按所选风格的版式 DNA 编写 `composition.html`（时间戳驱动场景与元素出场）
4. 本地预览（空格播放，检查字幕高亮与场景切换）
5. `render.py` 逐帧渲染合成 MP4（渲染耗时约为片长 2 倍，支持 `--style-kit` 一键换风格重渲）

**使用示例：**

```text
把这段稿子做成视频：（粘贴口播稿）
用国潮水墨风做一条介绍 XX 的口播视频
这条视频换个终端极客风重渲一版
```

**与 video-agent-kit 的分工：**

- `voice-to-video`：**无素材 → 有视频**，画面由引擎生成，适合知识口播、工具介绍、教程解说
- `video-agent-kit`：**有素材 → 剪成片**，画面来自源文件，适合电影解说、球赛/电竞集锦、混剪
- 两者可接力：先无素材出片，再做浓缩剪辑或字幕精修

> 详细文档（管线原理、timeline.json 格式、脚本参数、常见问题）见 [voice-to-video/README.md](voice-to-video/README.md)。

### 🎨 AI 教学媒体一体化（ai-teaching-media）

**核心功能：**

- ✅ **6 子 skill 一体化**：一个目录覆盖生图执行层、技术长文插图、学科信息图、教学动图/视频、短视频封面、文章解说视频
- ✅ **意图自动路由**：根据用户目标自动进入对应子 skill，并按流水线串联整套教学资产
- ✅ **知识点全套生产**：信息图 → 教学动图/配音视频 → 3:4 短视频封面
- ✅ **技术长文全套生产**：16:9 智能插图 → 章节解说视频 → 可选封面
- ✅ **多通道生图执行层**：统一调用 MuleRun / APImart / AtlasCloud / Agnes 等供应商
- ✅ **配音与成片**：支持 Minimax TTS / Edge TTS，结合 HyperFrames + ffmpeg 渲染 1080p 视频

**6 个子 skill：**

| 子 skill | 作用 | 典型输入 | 输出 |
|---------|------|----------|------|
| `ai-image-generator` | 通用生图执行层（被其它子 skill 调用） | prompt / 参考图 | PNG |
| `tech-article-diagram` | 技术长文智能插图（多风格） | Markdown 长文 | 16:9 插图 |
| `edu-subject-infographic` | 学科知识点竖版信息图 | 知识点名称 | 9:16 信息图 |
| `edu-teaching-animation` | 教学动图 + 配音教学视频 | 学科概念 | 无声 MP4 / 配音 MP4 |
| `short-video-cover` | 短视频竖版封面 | 口播文案 | 3:4 封面图 |
| `article-explainer-video` | 长文章节解说视频 | 技术文章 | 1080p MP4 |

**推荐串联流水线：**

| 流水线 | 适用场景 | 路径 |
|--------|----------|------|
| A 知识点全套 | 勾股定理、光合作用等单点知识 | 信息图 → 教学动图/视频 → 短视频封面 |
| B 技术长文全套 | 技术教程 / Markdown 长文 | 文章插图 → 章节解说视频 → 可选封面 |
| C 口播发布包 | 已有口播稿/脚本 | 3:4 封面 + 教学视频/解说视频 |

**适用场景：**

- 给技术文章自动补流程图、架构图、对比图
- 把学科知识点做成竖版信息图和教学短视频
- 为视频号/抖音/小红书生成 3:4 封面
- 把长文拆成章节解说视频一站式产出

**使用示例：**

```
请使用 ai-teaching-media，围绕「勾股定理」生成全套教学资产：
信息图 + 教学动图/配音视频 + 短视频封面
```

```
请用 ai-teaching-media 给这篇技术长文生成插图，并做成章节解说视频
```

**效果图：**

![image-20260726104118522](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20260726104118522.png)

https://cdn.jsdelivr.net/gh/hailaobao2026/ai-teaching-video-platform@main/docs/videos/math-pythagorean-theorem.mp4

**环境要求：**

| 变量 / 依赖 | 必需 | 说明 |
|-------------|------|------|
| `MULERUN_API_KEY` / `APIMART_API_KEY` / `ATLASCLOUD_API_KEY` / `AGNES_API_KEY` | 是（任选其一） | 生图供应商密钥 |
| `MINIMAX_API_KEY` | 否 | 配音；也可用免费 `edge-tts` |
| Node.js ≥ 22 + ffmpeg | 是（视频链路） | 渲染教学视频/解说视频 |

**技术特点：**

- 总入口 `SKILL.md` 负责路由，子 skill 独立约束与实现
- 同主题内容可复用色系与术语，保证信息图/动图/视频风格一致
- 生图统一走 `ai-image-generator`，避免多处重复对接供应商
- 支持从单点知识点到整篇文章的完整教学生产链路

---

### 🖼️ Grok Imagine Image (grok-imagine-image)

**核心功能：**

- ✅ **Grok Imagine 文生图**：调用 `grok-imagine-image` 模型生成图片
- ✅ **OpenAI 风格接口**：仅使用 `POST /v1/images/generations`，兼容 Grok2API
- ✅ **本地脚本开箱即用**：`scripts/generate.py` 支持 prompt 文件、批量数量、尺寸、超时
- ✅ **媒体 URL 自动改写**：接口返回 `127.0.0.1` 时自动替换为配置的公网主机并下载
- ✅ **Agent 友好输出**：支持 `--json` 机器可读结果，便于后续工作流解析
- ✅ **配置可覆盖**：支持环境变量与命令行参数覆盖 API Base / API Key / Model

**默认配置：**

| 项目 | 默认值 |
|------|--------|
| API 地址 | `http://43.163.230.83:8000/v1` |
| 模型 | `grok-imagine-image` |
| 尺寸 | `1024x1024` |
| 超时 | `180` 秒 |
| API Key | `scripts/generate.py` 中的 `DEFAULT_API_KEY`（可替换/环境变量覆盖） |

**适用场景：**

- 明确要求使用 Grok Imagine / grok-imagine-image 生图
- 其他 Skill 或本地工作流需要调用该模型
- 需要把生成结果下载到工作区 `outputs/` 再继续处理

**使用示例：**

```
请使用 grok-imagine-image 生成一张图片：
a cozy reading nook with soft daylight
保存到 ./outputs
```

**命令行使用：**

```bash
python scripts/generate.py   --prompt "a cozy reading nook with soft daylight"   --output-dir ./outputs   --name-tag reading-nook   --json
```

```bash
python scripts/generate.py   --prompt-file ./prompt.txt   --output-dir ./outputs   --size 1024x1024   --n 1   --timeout 180
```

**效果图：**

![image-20260726104231877](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20260726104231877.png)

![image-20260726104250036](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20260726104250036.png)

**环境要求：**

| 变量 | 必需 | 说明 |
|------|------|------|
| `GROK_IMAGINE_API_KEY` | 建议 | API 密钥；也可通过 `--api-key` 或脚本默认值配置 |
| `GROK_IMAGINE_API_BASE` | 否 | API 地址，默认见上表 |
| `GROK_IMAGINE_MODEL` | 否 | 模型名，默认 `grok-imagine-image` |

**技术特点：**

- 严格走 Images API，不误用 Chat Completions
- 生图成功后优先回报本地路径与可访问公网 URL
- 支持 `--no-download` 仅返回 URL，适合调试网关
- 适合作为独立生图技能，或被其他内容生产链路复用

---

### 📚 Knowledge Absorber (知识吸收器)

**核心功能：**

- ✅ **深度解析链接/文档/代码**：支持 URL 链接、本地文件（PDF/Word/Markdown/代码/图片）
- ✅ **导师级教学笔记**：生成结构化知识卡片，包含核心概念、FAQ、认知地图（Mermaid）
- ✅ **真理锚定验证**：自动联网验证事实性内容（数据、API 签名、版本号、历史事件），标注不确定内容
- ✅ **Wan 2.7 知识海报**：可选生成信息图海报，11 种视觉风格自动判断
- ✅ **国学风格自动触发**：检测国学关键词自动使用水墨风格（风格 11）
- ✅ **交互式 HTML 输出**：生成可交互的知识卡片 HTML，支持折叠/展开、搜索、导航

**11 种海报风格：**

| # | 风格 | 核心特征 | 适用场景 |
|---|------|----------|----------|
| 1 | 🧪 坐标蓝图 | 坐标系统 + 技术网格 | 技术参数、专业评测 |
| 2 | 📐 复古波普 | 瑞士网格 + 粗黑线 | 干货清单、对比表格 |
| 3 | 📁 文件夹 | 3D 文具 + 剪贴板 | 系统指南、分类清单 |
| 4 | 🧾 热敏纸 | 票据穿孔 + 3D 图标 | 步骤清单、时间线 |
| 5 | 📓 复古手帐 | 拼贴证据板 + 图钉 | 案例研究、调查分析 |
| 6 | ✏️ 陶土手绘 | 涂鸦粗轮廓 + 几何形 | 轻松干货、亲和科普 |
| 7 | 💾 酸性复古 | Y2K 像素 + 镭射渐变 | 数码评测、极客内容 |
| 8 | 🎫 剧场票据 | 票根胶片 + 五幕剧 | 故事演进、系列指南 |
| 9 | 🖼️ 矢量插图 | 黑轮廓线稿 + 几何简化 | PPT 封面、场景插画 |
| 10 | 🎨 孟菲斯网格 | 可见网格 + 模块色块 | 高密度信息、艺术指南 |
| 11 | ☯️ 水墨国学 | 水墨背景 + 传统字体 | 国学经典、人文哲学 |

**适用场景：**

- 学习新技术/框架，生成可搜索的知识卡片
- 分析开源项目代码，提取核心架构和设计模式
- 整理文档/教程，形成结构化学习笔记
- 国学经典解读，自动生成水墨风格海报
- 技术趋势分析，生成信息图海报分享

**工作流程（3 步引导法）：**

```
步骤 1: 启动询问 → 收集用户偏好（目标读者、海报需求、分辨率）
步骤 2: 知识摄取与验证 → 摄取内容 → 真理锚定 → 生成知识卡片 → (可选)海报 Prompt
步骤 3: 确认后生图 → 用户确认后调用 Wan 2.7 → 返回图片 URL
```

**真理锚定验证规则：**

| 必须验证 | 不需要验证 |
|---------|-----------|
| 具体数据（如 "Python 3.12 于 2023 年发布"） | 观点、建议、方法论 |
| API 签名（如 `fetch(url, options)`） | 个人经验、主观判断 |
| 版本号（如 "React 19 支持新特性"） | 设计模式、最佳实践 |
| 历史事件（如 "1991 年 Linux 发布"） | 推理过程、逻辑分析 |

**标注规范：**

| 类型 | 标注 | 示例 |
|------|------|------|
| 过时信息 | `[已过时]` | "Python 2 是主流 [已过时]" |
| 有争议 | `[存在争议]` | "最佳框架是 X [存在争议]" |
| 无法确认 | `[待确认]` | "该 API 返回 Promise [待确认]" |

**国学触发关键词：**

| 类别 | 关键词示例 |
|------|----------|
| 经典文献 | 论语、庄子、道德经、史记、诗经、易经、孟子、荀子、春秋、左传 |
| 学派思想 | 国学、古文、儒、道、佛、哲学、人文、儒家、道家、禅宗 |
| 历史人物 | 孔子、老子、孟子、庄子、荀子、墨子、韩非子、朱熹、王阳明 |
| 文学体裁 | 古诗、词、赋、骈文、散文、文言文 |
| 其他 | 经史子集、四书五经、诸子百家、传统文化 |

**效果图：**

![比亚迪2025年报水墨海报](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/%E6%AF%94%E4%BA%9A%E8%BF%AA2025%E5%B9%B4%E6%8A%A5%E6%B0%B4%E5%A2%A8%E6%B5%B7%E6%8A%A5.png)

![魔法液体科普海报_陶土手绘](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/%E9%AD%94%E6%B3%95%E6%B6%B2%E4%BD%93%E7%A7%91%E6%99%AE%E6%B5%B7%E6%8A%A5_%E9%99%B6%E5%9C%9F%E6%89%8B%E7%BB%98.png)

![武汉OPC政策海报_复古手帐](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/%E6%AD%A6%E6%B1%89OPC%E6%94%BF%E7%AD%96%E6%B5%B7%E6%8A%A5_%E5%A4%8D%E5%8F%A4%E6%89%8B%E5%B8%90-17758858211784.png)

**输出目录结构：**

```
outputs/knowledge_YYYYMMDD_HHMMSS/
├── knowledge_card.md           # 知识卡片 Markdown
├── knowledge_card.interactive.html  # 交互式 HTML
├── wan_prompt.txt              # 海报 Prompt（可选）
└── wan_result.json             # 生图结果（可选）
```

**环境要求：**

| 变量 | 必需 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 是 | DashScope API 密钥，用于翻译和 Wan 2.7 生图 |

**技术特点：**

- 智能内容摄取：支持动态页面渲染（DrissionPage）、静态页面解析
- 真理锚定协议：联网验证事实性内容，标注不确定信息
- 3 步引导式工作流：用户确认后再执行生图，避免资源浪费
- 海报风格智能判断：根据内容类型自动选择最合适的视觉风格
- 国学内容自动触发水墨风格：检测关键词自动切换风格 11

---

### 🎬 Seedance Video Creator (Seedance 2.0 分镜视频创作)

**核心功能：**

- ✅ **三阶段工作流**：分镜提示词 → 文生图首帧 → 图片+提示词生成视频
- ✅ **自动首帧生成**：无用户图片时自动调用文生图 API（jimeng-4.5）生成首帧参考图
- ✅ 分镜引导流程（理解想法→挖掘细节→构建分镜→生成双提示词→优化确认）
- ✅ 6 套分镜模板（叙事/产品/角色/风景/延长/编辑）
- ✅ 多模态支持：多图参考（最多9张）、角色一致性、运镜复刻
- ✅ 一键调用即梦 Seedance 2.0 API 生成视频
- ✅ 自动下载生成的视频到本地
- ✅ 镜头语言/氛围关键词速查表

**重要约束**：Seedance 2.0 **必须至少提供一张参考图片**，不支持纯文本生成视频。当用户没有提供图片时，工具会自动通过文生图 API 生成首帧参考图。

**适用场景：**

- 短视频创作（抖音/快手/视频号）
- 产品宣传视频制作
- 创意分镜脚本编写
- AI 视频生成效果探索

**前置条件：**

1. **jimeng-free-api-all** Docker 容器运行（端口 8000）— 必须是 `jimeng-free-api-all` 镜像，旧版 `jimeng-free-api` 不支持 Seedance
2. 即梦平台 SessionID（从网站 Cookies 获取）

**使用示例：**

```
帮我生成一个女孩在海边跳舞的视频
→ 生成首帧图片提示词 + 视频分镜提示词
→ 文生图生成首帧参考图
→ 首帧图片 + 提示词 → Seedance 2.0 生成视频
→ 下载视频
```

```bash
# 独立脚本使用（无图片 → 三阶段工作流）
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --image-prompt "海边沙滩，女孩穿白裙站在海边，夕阳逆光" \
  --prompt "@1 作为首帧参考，女孩开始旋转起舞..." \
  --ratio 9:16 --duration 4

# 有图片 → 直接生成视频
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --prompt "@1 和 @2 两人跳舞" \
  --files dancer1.jpg dancer2.jpg \
  --ratio 4:3 --duration 10
```

**视频参数：**

| 参数 | 可选值 | 默认值 |
|------|--------|--------|
| model | seedance-2.0-fast, jimeng-video-seedance-2.0-fast, jimeng-video-seedance-2.0(Pro) | seedance-2.0-fast |
| ratio | 1:1, 4:3, 3:4, 16:9, 9:16 | 9:16 |
| resolution | 480p, 720p, 1080p | 720p |
| duration | 4 - 15 秒（连续范围） | 4 |

**技术特点：**

- 融合 [elementsix-skills](https://github.com/elementsix/elementsix-skills) 分镜引导 + [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all) 视频生成
- 三阶段工作流：文生图（`/v1/images/generations`）→ 下载首帧 → Seedance 视频生成（`/v1/videos/generations`）
- Authorization 头需要 Bearer 前缀，格式为 `Bearer your_sessionid`
- API 同步阻塞调用，自动轮询等待生成完成
- **必须使用 `jimeng-free-api-all` 镜像**（旧版 `jimeng-free-api` 不含 Seedance 路由，会静默回退到 jimeng-video-3.0）
- 提供独立 Bash 脚本，支持 CI/CD 集成

---

### 📰 WeChat Article Fetcher (微信公众号文章获取器)

**核心功能：**

- ✅ 获取微信公众号文章完整内容
- ✅ 支持单篇和批量下载（空格或逗号分隔多个链接）
- ✅ 自动提取元数据（标题、作者、公众号名称、发布时间、摘要、封面图）
- ✅ 自动下载文章内所有图片到本地
- ✅ HTML 转 Markdown 格式
- ✅ 生成格式化的独立 HTML 文件
- ✅ 导出文章元数据 JSON
- ✅ 支持短链接和长链接两种格式
- ✅ 批量下载间隔控制，避免触发反爬

**适用场景：**

- 公众号文章离线保存和归档
- 文章内容素材提取
- 批量采集公众号文章
- 文章格式转换（HTML → Markdown）

**使用方式：**

```bash
# 单篇下载
python scripts/fetch_wechat_article.py "https://mp.weixin.qq.com/s/xxxxx"

# 批量下载（空格分隔）
python scripts/fetch_wechat_article.py "url1" "url2" "url3" --output-dir ./output

# 批量下载（逗号分隔）
python scripts/fetch_wechat_article.py "url1,url2,url3" --output-dir ./output

# 仅输出元数据 JSON
python scripts/fetch_wechat_article.py "url" --json

# 自定义下载间隔（默认3秒）
python scripts/fetch_wechat_article.py "url1" "url2" --interval 5
```

**输出结构：**

```
output/<公众号名称>/<日期>_<标题>/
├── index.html    # 格式化的独立HTML文件
├── article.md    # Markdown版本
├── meta.json     # 文章元数据
└── images/       # 下载的图片
```

**Python 库调用：**

```python
from scripts.fetch_wechat_article import fetch_article, batch_fetch

# 单篇获取
result = fetch_article("https://mp.weixin.qq.com/s/xxxxx", output_dir="./output")

# 批量获取
urls = ["url1", "url2", "url3"]
stats = batch_fetch(urls, output_dir="./output", interval=3.0)
print(f"成功{stats['success']}篇, 失败{stats['fail']}篇")
```

**技术要求：**

- Python 3.7+
- 依赖库：`pip install beautifulsoup4 html2text requests`

**注意事项：**

- 优先使用短链接（`/s/xxxxx`），长链接可能触发验证码
- 批量下载时默认间隔3秒，可通过 `--interval` 调整
- 自动使用微信移动端 User-Agent 绕过访问限制

---

### 📰 WeChat Article Aggregator (微信公众号文章聚合器)

**核心功能：**

- ✅ 通过 mptext.top API 批量获取指定公众号博主的最新文章列表
- ✅ 自动下载文章内容并解析为 Markdown/HTML/纯文本/JSON 格式
- ✅ 支持按公众号名称或 fakeid 获取，预置 8 个热门 AI 技术公众号
- ✅ 智能 HTML 正文解析，提取 `#js_content` 区块内容
- ✅ 生成结构化的 summary.json 元数据汇总文件
- ✅ 可选依赖，自动降级：无 beautifulsoup4 时使用内置解析器

**预置公众号：**

| 公众号 | 分类 | fakeid |
|--------|------|--------|
| 饼干哥哥AGI | AI编程 | MjM5NDI4MTY3NA== |
| 赛博禅心 | AI前沿 | MzkzNDQxOTU2MQ== |
| 可怜的小互 | AI技术 | MzkzMTcyMTgxNg== |
| 宝玉的工程技术分享 | 技术翻译 | Mzk1NzgxMjQ0OA== |
| 苍何 | AI实战 | Mzg3MTk3NzYzNw== |
| 老金开源 | Claude Code | MzI0NzU2MDgyNA== |
| 玩转AI工具 | AI工具 | MzU4NTE1Mjg4MA== |
| 袋鼠帝AI客栈 | AI实战 | MzkwMzE4NjU5NA== |

**使用方式：**

```bash
# 命令行方式：按 fakeid 获取
python3 scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "MzkzNDQxOTU2MQ==" --limit 2

# 按公众号名称获取
python3 scripts/fetch_articles.py --api-key YOUR_KEY --fakeids "赛博禅心,老金开源" --limit 3

# 获取所有预置公众号的最新文章
python3 scripts/fetch_articles.py --api-key YOUR_KEY --fakeids all --limit 1

# 查看预置公众号列表
python3 scripts/fetch_articles.py --list-accounts
```

**Claude Code 中使用：**

```
"请使用 wechat-article-aggregator 获取赛博禅心最新2篇公众号文章"
"请帮我获取所有预置公众号的最新文章"
```

**技术要求：**

- Python 3.7+
- 必需依赖：`pip install requests`
- 可选依赖：`pip install beautifulsoup4 html2text`（增强 HTML 解析效果）
- mptext.top API Key

**注意事项：**

- API Key 通过 `--api-key` 参数或 `MPTEXT_API_KEY` 环境变量配置
- 默认每次请求间隔 2 秒，可通过 `--interval` 调整
- 部分图片密集型或付费文章可能无法提取文本内容

---

### 📊 PPT Generator (PPT 生成器)

**核心功能：**

- ✅ 固定 25 页专业商务 PPT 结构（封面→目录→4章节→结束→字体说明→版权）
- ✅ 三种主题风格：暖色调、商务简约（默认）、莫兰迪色系
- ✅ 每章节 5 页（1 个过渡页 + 4 个内容页）
- ✅ 支持 JSON 配置文件和代码调用两种方式
- ✅ 专业设计风格：商务简约、暖色调装饰、莫兰迪色系
- ✅ 规范化布局：统一页面布局和文本规范

**PPT 结构（25 页）：**

1. **第1页**：封面 - 主标题、副标题、年份
2. **第2页**：目录 - 4 个章节列表
3. **第3-7页**：第一章节（1 个过渡页 + 4 个内容页）
4. **第8-12页**：第二章节（1 个过渡页 + 4 个内容页）
5. **第13-17页**：第三章节（1 个过渡页 + 4 个内容页）
6. **第18-22页**：第四章节（1 个过渡页 + 4 个内容页）
7. **第23页**：结束页 - "谢谢观看"
8. **第24页**：字体说明
9. **第25页**：版权声明

**适用场景：**

- 年度工作总结
- 项目汇报
- 工作述职
- 产品发布
- 季度/月度报告

**使用方式：**

```bash
# 方法1：直接运行生成示例 PPT
python3 ppt_generator.py

# 方法2：使用 JSON 配置文件
python3 ppt_generator.py my_ppt_config.json
```

**JSON 配置示例：**

```json
{
  "title": "2025年度工作总结",
  "subtitle": "工作总结 / 汇报",
  "year": "2025",
  "theme": "商务简约",
  "filename": "2025年度工作总结.pptx",
  "chapters": [
    {
      "title": "年度工作概况",
      "description": "介绍全年工作整体情况",
      "pages": [
        {
          "title": "工作概述",
          "content": [
            {"title": "项目数量", "description": "完成 15 个重点项目"},
            {"title": "团队规模", "description": "团队扩展至 20 人"}
          ]
        }
      ]
    }
  ]
}
```

**代码调用示例：**

```python
from ppt_generator import PPTGenerator

# 创建生成器实例
generator = PPTGenerator(theme="商务简约")

# 配置 PPT 内容
config = {
    "title": "2025年度总结",
    "subtitle": "工作总结 / 汇报",
    "year": "2025",
    "chapters": [...]  # 章节配置
}

# 生成并保存 PPT
generator.generate_full_ppt(config)
generator.save("output.pptx")
```

**主题风格：**

| 主题 | 特点 | 适用场景 |
|------|------|----------|
| 暖色调 | 活泼热情 | 创意类汇报 |
| 商务简约 | 专业稳重（默认） | 工作总结 |
| 莫兰迪色系 | 优雅柔和 | 品牌展示 |

**技术要求：**

- Python 3.7+
- 依赖库：python-pptx (`pip install python-pptx`)
- 推荐字体：阿里巴巴普惠体 2.0、HarmonyOS Sans SC、MiSans Heavy、思源宋体 CN

**配置要点：**

- 4 个章节必填：每个 PPT 必须有 4 个主要章节
- 每章节 4 页内容：不足自动补充占位页
- 每页最多 4 个要点：采用 2x2 布局
- 文本简洁：描述控制在 50-100 字

---

### 📊 Excel Report Generator

**核心功能：**

- ✅ 从多种数据源生成 Excel（CSV、DataFrame、数据库）
- ✅ 创建专业图表（柱状图、折线图、饼图等）
- ✅ 应用样式和格式化
- ✅ 模板填充和批量生成
- ✅ 条件格式和数据验证
- ✅ 公式和自动计算

**适用场景：**

- 数据分析报表
- 业务报告自动化
- 系统数据导出
- 模板批量处理

**示例用法：**

```
请基于上面的数据帮我生成图表统计，比如饼状图、柱状图、条形图等
```

![image-20251112171422425](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112171422425.png)

---

### 🎬 WanCover+ (Wan2.7 封面图和视频生成)

**核心功能：**

- ✅ **图片生成**：公众号封面图、小红书封面图、种草图、海报重排版
- ✅ **视频生成**：文生视频、静态图转丝滑动态视频、参考图/参考视频转视频
- ✅ **视频后处理**：自动 Edge TTS 配音、SRT 字幕生成、字幕烧录
- ✅ **智能场景识别**：自动判断任务类型（从零出图 vs 改版重排）
- ✅ **多平台适配**：支持微信横版封面、小红书竖版封面等多种规格
- ✅ **Wan 2.6 / 2.7 兼容**：视频任务兼容两代模型协议

**图片任务场景：**

| 场景 | scene | 适用场景 |
|------|-------|----------|
| 公众号封面图 | `wechat_cover` | 横版文章头图、技术媒体头图 |
| 小红书封面 | `xiaohongshu_cover` | 竖版信息流封面、种草图 |
| 海报改版 | `relayout_poster` | 保留原主体/信息层级的改版设计 |

**视频任务类型：**

| 类型 | task_type | 默认模型 | 适用场景 |
|------|-----------|----------|----------|
| 文生视频 | `text_to_video` | `wan2.7-t2v` | 纯文字描述生成视频 |
| 图转视频 | `image_to_video` | `wan2.7-i2v` | 静态图转动态视频 |
| 参考转视频 | `reference_to_video` | `wan2.7-r2v` | 参考图/参考视频转视频 |

**适用场景：**

- 公众号文章封面图制作
- 小红书笔记封面图生成
- 产品种草图快速出图
- 海报横版改竖版重排版
- 产品演示短视频生成
- 静态图片转动态视频
- 视频自动配音和字幕

**使用示例：**

```
请使用 wan-cover-plus 生成一个技术文章公众号封面图
标题：Claude Code Skills 集合
副标题：15+ 实用技能工具
风格：tech_media
```

![6eac583cb3d4458881fcff2f4978138e_2](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/6eac583cb3d4458881fcff2f4978138e_2.png)

**命令行使用：**

```bash
# 图片任务
python3 scripts/generate.py --input examples/demo_wechat_cover.json
python3 scripts/generate.py --input examples/demo_xiaohongshu_cover.json
python3 scripts/generate.py --input examples/demo_relayout_poster.json

# 视频任务
python3 scripts/generate.py --input examples/demo_text_to_video.json
python3 scripts/generate.py --input examples/demo_image_to_video.json
python3 scripts/generate.py --input examples/demo_reference_to_video.json
```

**输入格式示例：**

```json
// 图片任务最小输入
{
  "title": "string",
  "scene": "wechat_cover | xiaohongshu_cover | relayout_poster",
  "style": "tech_media | warm_lifestyle | premium_brand | cute_note"
}

// 文生视频最小输入
{
  "task_type": "text_to_video",
  "title": "string"
}

// 图转视频最小输入
{
  "task_type": "image_to_video",
  "title": "string",
  "reference_images": ["/absolute/path/or/url"]
}
```

**配置说明：**

```yaml
wan:
  api_key: "your_wan_api_key"
  base_url: "https://dashscope.aliyuncs.com/api/v1"
  image_model: "wan2.7-image"
  text_to_video_model: "wan2.7-t2v"
  image_to_video_model: "wan2.7-i2v"
  reference_to_video_model: "wan2.7-r2v"

defaults:
  task_type: "image"
  scene: "wechat_cover"
  style: "tech_media"
  variants: 1
  output_dir: "output"
  video_duration_seconds: 5
  video_resolution: "720P"
  video_aspect_ratio: "16:9"

postprocess:
  ffmpeg_bin: "ffmpeg"
  ffprobe_bin: "ffprobe"
  tts_voice: "zh-CN-XiaoxiaoNeural"
  tts_rate: "+0%"
  tts_volume: "+0%"
  subtitle_mode: "burned"
```

**技术特点：**

- 基于 Wan 2.7 系列模型的强大生成能力
- 视频任务兼容 Wan 2.6 / 2.7 两代协议
- 智能场景判断和任务路由
- 支持本地路径和 URL 两种参考源
- 自动生成 prompt sidecar 文件
- Edge TTS 配音和多语言字幕支持
- 字幕烧录到视频的完整后处理流程

**前置条件：**

1. 配置 `config.yaml` 文件（复制 `config.example.yaml`）
2. 填写 `wan.api_key` 和 `wan.base_url`
3. 视频配音和字幕功能需要安装 `ffmpeg` 和 `ffprobe`

**输出结果：**

- 图片任务：PNG 图片 + `.prompt.txt` sidecar
- 视频任务：MP4 视频 + `.prompt.txt` sidecar
- 启用后处理：额外生成 `.narration.mp3`、`.srt`、`.narrated.mp4`、`.final.mp4`

---

### 🔥 GitHub Trending

**核心功能：**

- ✅ 抓取 GitHub Trending 今日前 5 热门项目
- ✅ 获取 README 并生成中文摘要（项目是什么、解决问题、技术栈、Star 数量）
- ✅ 企业微信机器人推送摘要
- ✅ 支持 GITHUB_TOKEN 提升 API 额度

**适用场景：**

- 技术趋势日报/周报
- 团队技术分享与学习
- 新项目调研与选型

**使用方式：**

```
请帮我使用github-trending-skill 这个skill获取今天最热门的github开源项目内容，并使用ui-ux-pro-max-skill
这个skill生成科技风格的日报信息，并输出html当前文件夹下
```

企业微信收到的消息

![image-20260123234615323](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20260123234615323.png)

使用ui-ux-pro-max-skill 生成的html效果

![image-20260122235640833](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20260122235640833.png)

**配置说明：**

- `GITHUB_TOKEN`：可选，用于提高 GitHub API 额度
- `WEIXIN_WEBHOOK`：可选，覆盖默认企业微信机器人地址

---

### 🎨 GitHub Trending Wan (GitHub 热门开源信息图海报)

**核心功能：**

- ✅ 抓取 GitHub Trending **Top 5** 项目，获取 Star、语言、技术栈、README 摘要等元数据
- ✅ 调用 DashScope 兼容 API，将英文摘要字段翻译为简体中文
- ✅ 生成低信息密度的中文简报（Markdown）和 Wan 2.7 海报 Prompt
- ✅ 支持 **10 种视觉风格**（坐标蓝图 / 复古波普 / 文件夹 / 热敏纸 / 复古手帐 / 陶土手绘 / 酸性复古 / 剧场票据 / 矢量插图 / 孟菲斯网格）
- ✅ 采用 **3 步引导式工作流**：启动询问 → 信息提取 → 确认生图

**10 种视觉风格：**

| # | 风格 | 核心特征 | 适用场景 |
|---|------|----------|----------|
| 1 | 🧪 坐标蓝图 | 坐标系统 + 技术网格 | 技术参数、专业评测 |
| 2 | 📐 复古波普 | 瑞士网格 + 粗黑线 | 干货清单、对比表格 |
| 3 | 📁 文件夹 | 3D 文具 + 剪贴板 | 系统指南、分类清单 |
| 4 | 🧾 热敏纸 | 票据穿孔 + 3D 图标 | 步骤清单、时间线 |
| 5 | 📓 复古手帐 | 拼贴证据板 + 图钉 | 案例研究、调查分析 |
| 6 | ✏️ 陶土手绘 | 涂鸦粗轮廓 + 几何形 | 轻松干货、亲和科普 |
| 7 | 💾 酸性复古 | Y2K 像素 + 镭射渐变 | 数码评测、极客内容 |
| 8 | 🎫 剧场票据 | 票根胶片 + 五幕剧 | 故事演进、系列指南 |
| 9 | 🖼️ 矢量插图 | 黑轮廓线稿 + 几何简化 | PPT 封面、场景插画 |
| 10 | 🎨 孟菲斯网格 | 可见网格 + 模块色块 | 高密度信息、艺术指南 |

**适用场景：**

- 开源日报/周报可视化
- 技术趋势信息图海报
- GitHub Trending 中文解读分享
- 小红书/公众号技术内容配图

**工作流程：**

```
步骤 1: 启动询问 → 收集日期、受众、风格偏好
步骤 2: 信息提取 → 抓取、翻译、生成简报
步骤 3: 确认生图 → 用户确认后调用 Wan 2.7
```

**使用示例：**

```bash
# 步骤 1：抓取 Trending Top 5
python3 scripts/fetch_daily_top10.py --top 5 --date-label "2026-04-08"

# 步骤 2：翻译为中文
python3 scripts/translate_daily_top.py --input output/daily_top10.json

# 步骤 3：生成简报和 Wan Prompt（孟菲斯网格风格）
python3 scripts/build_daily_poster_assets.py --style 10 --size 2K --ratio 3:4

# 步骤 4：调用 Wan 2.7 生图
python3 scripts/run_wan_generation.py --prompt output/wan_prompt.txt
```

**输出示例：**

生成海报效果：

![github_trending_top5_today_wan_20260408](github-trending-wan-skill/output/github_trending_top5_today_wan_20260408.png)

**环境要求：**

| 变量 | 必需 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 是 | DashScope API 密钥，用于翻译和 Wan 2.7 生图 |
| `GITHUB_TOKEN` | 否 | GitHub Personal Access Token，减少 API 限流 |
| `WAN_SKILL_DIR` | 否 | Wan 2.7 脚本目录 |

**外部依赖：**

本 Skill 依赖 [Wan-skills-main](https://github.com/anthropics/wan-skills) 提供的 Wan 2.7 生图脚本。

---

### 📝 XiaoHuiHui Tech Article

**核心功能：**

- ✅ 公众号卡片：文章前言上方自动插入作者公众号名片卡片
- ✅ 标准四段式结构（公众号卡片→前言→项目介绍→部署实战→总结→往期推荐）
- ✅ 三段式开头（问题引入+解决方案+实战预告）
- ✅ 详细部署步骤（环境→安装→配置→实现→测试）
- ✅ 单段长句总结（300-500字）
- ✅ 往期推荐：文章结尾自动附加最新5篇公众号文章链接
- ✅ 口语化技术表达
- ✅ 完整资源附加（GitHub+体验地址+网盘）
- ✅ **Gemini-3-Pro-Image-Preview 双通道自动配图**（自建API + Gemai公益站）
- ✅ 图片占位符自动替换为真实URL
- ✅ 腾讯云COS图床自动上传

**文章结构：**

- **公众号卡片**：HTML格式名片卡片
- **第1章**：前言（三段式，约300字）
- **第2章**：项目介绍（约500字）
- **第3章**：部署实战（约1500-2000字）
- **第4章**：总结（单段300-500字）
- **第5章**：往期推荐（最新5篇文章链接）

**配图系统（v2.4.0 双通道）：**

- 🤖 **通道一（自建API）**：调用自建 Gemini API 生成技术配图
- 🌐 **通道二（Gemai公益站）**：调用 api.gemai.cc 生成配图（备用通道）
- ☁️ 自动上传至腾讯云COS图床
- 🔗 自动替换文章中的图片占位符
- 📸 支持多种图片类型：架构图、界面图、终端图、代码图、结果图
- 💾 内存上传，无需本地缓存文件
- 🔄 双通道自动切换：自建API优先，失败回退Gemai公益站

**Gemai公益站命令行工具：**

```bash
# 通过环境变量设置 API Key
export GEMAI_API_KEY="你的API密钥"
python3 gemai_image_generator.py --prompt "技术架构图,3D等距视角,蓝色科技风格"

# 或通过命令行参数传入
python3 gemai_image_generator.py --api-key "你的密钥" --prompt "描述内容" -o output.png

# 支持风格、宽高比、批量生成
python3 gemai_image_generator.py --prompt "架构图" --style realistic --aspect-ratio 16:9 --num-images 2
```

**配置要求：**

1. 配置腾讯云COS环境变量：
   - `COS_SECRET_ID`：腾讯云访问密钥ID
   - `COS_SECRET_KEY`：腾讯云访问密钥Key
   - `COS_BUCKET`：COS存储桶名称
   - `COS_REGION`：COS存储桶所在地域

2. 配置图片生成API（二选一）：
   - **自建API**：配置 Gemini API 地址和 Key
   - **Gemai公益站**：设置 `GEMAI_API_KEY` 环境变量

**示例用法：**

```
请认真分析https://github.com/wwwzhouhui/in_animation开源项目，请帮我使用xiaohuihui-tech-article skill基于这个开源项目生成一个公众号文章。输出"20251101in_animation公众号文章.md"
```

![image-20251110175146630](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110175146630.png)

![image-20251110175215254](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110175215254.png)

---

### 🎨 Jimeng MCP Skill

**核心功能：**

- ✅ 文本生成图像（text-to-image）
- ✅ 图像合成（image composition）
- ✅ 文本生成视频（text-to-video）
- ✅ 图像生成视频（image-to-video）
- ✅ 支持多种分辨率和宽高比
- ✅ **v2.0.0** 升级至 jimeng-4.5 模型
- ✅ **v2.0.0** 新参数系统：ratio（宽高比）+ resolution（分辨率）
- ✅ **v2.0.0** 替代旧参数：width/height + sample_strength

**模型升级（v2.0.0）：**

- 🆙 **jimeng-4.0** → **jimeng-4.5**：更强大的生成能力
- 📐 **ratio 参数**：16:9、4:3、1:1、3:4、9:16 等
- 🎯 **resolution 参数**：360p、480p、720p、1080p 等
- 📝 简化参数配置，提升易用性

**适用场景：**

- AI 内容创作（博客配图、短视频制作）
- 产品宣传素材生成
- UI 原型快速生成
- 创意头脑风暴可视化

**前置条件：**

1. jimeng-free-api-all Docker 容器运行
2. 配置 JIMENG_API_KEY 环境变量
3. jimeng-mcp-server 正确安装（支持 jimeng-4.5 模型）

**技术特点:**

- 基于 MCP(模型上下文协议)标准
- 支持 stdio、SSE、HTTP 三种运行模式
- 完全免费(每日 66 积分)
- 响应时间:图像 10-20秒,视频 30-60秒

---

### 🎨 MP Cover Generator (公众号封面生成器)

**核心功能:**

- ✅ 根据主题自动生成 3D 插画风格封面底图
- ✅ 智能叠加文字层（日期、标题、作者）
- ✅ 描边卡通字体效果（鲜艳色彩 + 多层描边）
- ✅ 垂直居中布局，视觉平衡完美
- ✅ 双格式输出：HTML + 高清图片（PNG/JPG）
- ✅ 完整页面截图（5120x2916，2x 像素密度）
- ✅ 可爱圆润的卡通 3D 风格（类似皮克斯）
- ✅ 返回 4 张不同风格供选择

**适用场景:**

- 公众号文章封面图制作
- 社交媒体横幅图生成
- 技术博客头图创作
- 宣传海报快速设计

**前置条件:**

1. jimeng-free-api-all Docker 容器运行
2. 配置 JIMENG_API_KEY 环境变量
3. jimeng-mcp-server 正确安装
4. Node.js 16+ 环境（图片输出功能）
5. Playwright 已安装（自动安装）

**使用示例:**

```
请使用 mp-cover-generator skill 生成一个 MCP案例分享 claude调用AI生图视频教程 介绍的文章的公众号封面
```

![image-20251115183718247](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115183718247.png.png)

![image-20251115183746503](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251115183746503.png.png

---

### 🤖 Dify DSL Generator

**核心功能：**

- ✅ 自动生成完整的 Dify 工作流 DSL/YML 文件
- ✅ 支持多种节点类型（start、llm、answer、code、http-request、if-else、tool 等）
- ✅ 智能生成节点间的连接关系（edges）
- ✅ 自动配置模型参数和提示词
- ✅ 识别并配置所需的 Dify 插件依赖
- ✅ 严格遵循 Dify 0.3.0 版本的 DSL 规范
- ✅ 基于 86+ 真实工作流案例深度学习

**适用场景：**

- 快速构建 Dify 工作流配置文件
- 批量生成工作流模板
- 学习 Dify DSL 文件结构
- 自动化工作流开发

**知识库覆盖：**

- App 配置（mode、icon、描述等）
- Dependencies 依赖管理
- 各类节点详解（LLM、Code、HTTP、If-Else、Tool、Variable Aggregator、Parameter Extractor）
- Edges 连接规则
- Position 坐标布局
- 变量引用格式

**示例用法：**

```
生成一个 Dify 工作流用于图片 OCR 识别:
- 功能: 上传图片并识别文字
- 输入: 图片文件
- 处理: 使用 LLM 视觉能力进行 OCR
- 输出: 识别到的文字内容
```

![image-20251122214416059](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251122214416059.png)

生成的dsl导入dify 平台

![image-20251122214446776](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251122214446776.png)

**技术特点：**

- 完整 DSL 结构生成（app + dependencies + workflow）
- 智能节点 ID 生成（时间戳格式）
- 合理的节点布局坐标
- 支持复杂工作流逻辑（分支、循环、聚合）
- 提供常用提示词模板（Text-to-SQL、数据提取、HTML 生成）

---

### 📝 XiaoHuiHui Dify Tech Article

**核心功能：**

- ✅ Dify 专属三段式结构（前言 → 工作流制作 → 总结）
- ✅ 工作流节点详细配置说明
- ✅ 插件安装和授权步骤图文教程
- ✅ MCP Server 部署集成指南
- ✅ 优先展示工作流效果
- ✅ 口语化技术表达（"话不多说"、"手把手搭建"）
- ✅ 魔搭社区免费模型推荐
- ✅ 自动生成配图并上传腾讯云 COS 图床

**文章结构：**

- **前言**（300-400字）：技术背景 + 问题引入 + 解决方案展示
- **工作流制作**（1500-2500字）：前置准备 + 节点配置 + 测试验证
- **总结**（单段300-400字）：完整流程回顾 + 核心价值 + 扩展场景

**配图系统：**

- 工作流全局图（1张）
- 节点配置截图（6-10张）
- 插件安装截图（2-3张）
- 效果演示图（2-3张）
- 代码配置图（1-2张）
- 总计要求 >= 10 张实际截图

**示例用法：**

```
用小灰灰公众号风格写一篇 Dify 文生视频工作流的案例分享:
- 功能: 调用即梦AI实现文生视频
- 涉及插件: Agent策略插件
- 核心节点: LLM、Agent、代码执行
- 技术栈: MCP、即梦API
```

**质量标准：**

- 总字数 > 1800字（优秀 > 2500字）
- 标题格式：`dify案例分享-[功能名称]`
- 工作流截图 >= 10个（优秀 >= 15个）
- 节点配置说明 >= 5个
- 代码块 >= 3个
- 总结单段 300-400字，禁止分段
- 固定结束语："今天的分享就到这里结束了,我们下一篇文章见。"

**技术特点：**

- 遵循小灰灰公众号写作规范
- 专注 Dify 工作流案例分享
- 包含完整的插件安装教程
- 支持 MCP Server 集成说明
- 提供腾讯云 COS 图床上传脚本
- 真实图片 URL，无占位符

---

### 🔍 Obsidian Search (Obsidian CLI 查询助手)

**核心功能：**

- ✅ 将自然语言检索需求转换为 Obsidian CLI 查询命令
- ✅ 支持搜索笔记、查找上下文、筛选任务、标签、属性
- ✅ 查询反向链接、文件列表、文档大纲
- ✅ 自动选择最合适的 CLI 命令模式
- ✅ 结果聚类和简洁总结

**核心命令：**

| 命令 | 功能说明 |
|------|----------|
| `obsidian search` | 文本搜索，查找包含关键词的笔记 |
| `obsidian search:context` | 带上下文搜索，显示关键词出现的行 |
| `obsidian read` | 读取指定笔记的完整内容 |
| `obsidian files` | 列出指定目录下的文件 |
| `obsidian tasks` | 查询待办事项 |
| `obsidian tags` | 查看标签分布统计 |
| `obsidian backlinks` | 查询反向链接 |
| `obsidian links` | 查询出链 |
| `obsidian outline` | 查看笔记大纲/标题层级 |

**适用场景：**

- 快速查找知识库中的笔记
- 查看关键词出现的上下文
- 整理待办事项和任务清单
- 分析标签使用情况和知识分类
- 查看笔记之间的引用关系
- 浏览指定目录下的文档列表
- 总结特定主题在知识库中的分布

**使用示例：**

```
帮我找一下和 obsidian 相关的笔记
→ obsidian search query="obsidian" limit=5
```

```
看看哪些地方提到了 obsidian cli
→ obsidian search:context query="obsidian cli" limit=10
```

```
我的知识库里常用标签有哪些
→ obsidian tags counts format=json
```

```
谁引用了这篇笔记
→ obsidian backlinks file="Obsidian CLI 命令行接口" counts format=json
```

```
列出 work 目录下的文档
→ obsidian files folder="work"
```

**查询策略：**

- **先搜再读**：先用 `search` 缩小范围，再用 `read` 读取内容
- **先列再筛**：先用 `files folder` 枚举目录，再筛选目标文件
- **先看关系再读正文**：先用 `backlinks`/`links` 查看引用关系，再深入阅读

**技术要求：**

- 桌面版 Obsidian 正在运行
- Obsidian CLI 已安装并配置

**注意事项：**

- 搜索命令默认只返回路径，不返回正文
- 要看命中内容使用 `search:context`
- `search` 的 `path=` 接收文件夹路径，不是文件路径
- 若结果为空，会明确说明并尝试更宽松关键词

---

### 🛡️ Wechat Compliance Reviewer (微信公众号文章合规审查专家)

**核心功能：**

- ✅ 根据微信公众平台运营规范审查文章内容
- ✅ 识别 9 大类违规风险（诱导分享、欺诈信息、营销推广、版权侵权等）
- ✅ 提供详细修改建议和合规话术替代方案
- ✅ 支持快速审查清单和深度审查两种模式
- ✅ 输出结构化审查报告（风险等级 + 违规位置 + 修改建议）
- ✅ 内置违规话术对照表和合规模板

**审查范围：**

| 风险等级 | 违规类型 | 检测内容 |
|---------|---------|---------|
| 🔴 高风险 | 诱导分享/关注 | "白嫖"、"薅羊毛"、"速转"、"分享给朋友"等 |
| 🔴 高风险 | 营销推广/优惠码 | 优惠码、推荐链接（含 ref 参数）、购买链接 |
| 🔴 高风险 | 欺诈/虚假信息 | "0 元"实际需绑卡、"免费"实际后续收费 |
| 🔴 高风险 | 版权/知识产权 | 未授权转载、搬运内容、盗用图片 |
| 🟡 中风险 | 金融/支付相关 | 指导绑卡、跨境支付、投资建议 |
| 🟡 中风险 | 技术外挂/绕过付费 | 破解教程、绕过订阅、API 滥用 |
| 🟡 中风险 | 夸大/虚假宣传 | 虚假参数、夸张用语、未证实数据 |
| 🟠 低风险 | 外部链接/导流 | 外部网站链接、小程序跳转 |
| 🟠 低风险 | 敏感话题 | 政治、色情、赌博、暴力 |

**适用场景：**

- 公众号文章发布前合规审查
- 识别诱导分享、欺诈信息等违规风险
- 获取合规修改建议和话术替代
- 学习微信公众平台运营规范
- 降低账号被封禁风险

**使用方式：**

```
请帮我审查这篇公众号文章，看看有没有违规风险

[粘贴文章内容]
```

```
请使用 wechat-compliance-reviewer 审查这篇文章，检查是否有诱导分享、营销推广等违规行为
```

**审查报告示例：**

```markdown
## 审查结果总览

| 风险等级 | 违规项数量 | 建议 |
|---------|-----------|------|
| 高风险 | 3 项 | 必须修改 |
| 中风险 | 2 项 | 强烈建议修改 |
| 低风险 | 1 项 | 可考虑修改 |

**综合结论**：❌ 不建议按当前版本发布，存在较高封号风险

## 详细问题清单

### 问题 1：诱导分享行为
- **位置**：第 3 段
- **原文**："赶紧分享给你的朋友们，一起薅羊毛！"
- **违规原因**：违反《微信公众平台运营规范》，禁止诱导用户分享行为
- **风险等级**：⭐⭐⭐⭐⭐
- **修改建议**：直接删除该句，或改为"如果你觉得有用，欢迎分享给需要的朋友"
```

**参考资料：**

- `violation-types.md` - 违规类型详解（10 大类违规行为和处罚措施）
- `case-studies.md` - 处罚案例库（10 个真实封号案例和分析）
- `compliant-templates.md` - 合规话术模板（违规话术替代方案和场景模板）

**技术特点：**

- 基于《微信公众平台运营规范》官方条款
- 收录真实处罚案例分析
- 提供合规话术对照表
- 支持快速审查清单（8 项检查）
- 分级处理（高风险必须修改，低风险酌情处理）
- 考虑文章整体意图和上下文

**处罚措施参考：**

| 违规类型 | 首次处罚 | 多次处罚 | 严重处罚 |
|---------|---------|---------|---------|
| 诱导分享 | 删除文章 | 限制功能 7-30 天 | 永久封号 |
| 营销推广 | 删除文章 | 限制流量 | 封禁广告功能 |
| 欺诈信息 | 删除文章 | 封号 | 移交司法 |
| 版权侵权 | 删除文章 | 赔偿 | 账号降权 |

---

### 🌐 SiliconFlow API Skills

**核心功能：**

- ✅ 大语言模型 API 调用指南
- ✅ Chat Completions API 完整文档
- ✅ Stream 流式输出模式支持
- ✅ 图片生成 API 使用说明
- ✅ 向量模型/Embedding API 文档
- ✅ 模型列表和参数配置
- ✅ 最佳实践和代码示例

**适用场景：**

- 在 Claude Code 中调用硅基流动 API
- 开发基于 SiliconFlow 的 AI 应用
- 学习大语言模型 API 调用方式
- 调试和优化 API 调用代码
- 了解 SiliconFlow 平台功能特性

**参考文档：**

- `api_reference.md` - API 参考文档
- `deployment.md` - 部署文档
- `faqs.md` - 常见问题
- `features.md` - 功能特性
- `models.md` - 模型列表
- `userguide.md` - 用户指南
- `use_cases.md` - 使用案例

**示例用法：**

```
请帮我使用siliconflow-api-skills 这个skill技能包生成调用硅基流动的API 实现文本生成的模型接口，使用python 代码实现，
使用deepseek-ai/DeepSeek-V3.2-Exp 模型
```

![image-20251119171818824](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251119171818824.png)

**技术特点：**

- 基于官方文档自动生成
- 包含完整的代码示例
- 支持多种编程语言
- 涵盖从入门到高级的所有内容

---

### 📖 GitHub README Generator

**核心功能：**

- ✅ 自动生成标准的 GitHub README.md 文档
- ✅ 支持 6 种项目模板（basic/full/library/webapp/cli/api）
- ✅ 交互式生成和基于现有项目自动生成
- ✅ 自动识别项目类型和技术栈
- ✅ 生成 Badge 和 Star History
- ✅ 包含作者联系和打赏信息
- ✅ 生成常见问题 FAQ
- ✅ 支持中英文双语

**适用场景：**

- 新项目快速创建 README
- 现有项目文档规范化
- 开源项目文档优化
- 学习标准文档结构

**使用示例：**

```
请使用 full 模板为我的 Vue 项目生成 README

项目信息：
- 名称：vue-admin
- 简介：一个现代化的 Vue 后台管理系统
- 技术栈：Vue 3, Vite, Element Plus, Pinia
- 功能：权限管理、动态路由、图表统计
```

**可用模板：**

| 模板 | 说明 | 适用场景 |
|------|------|----------|
| basic | 基础模板 | 所有项目 |
| full | 完整模板（包含所有章节） | 中大型项目 |
| minimal | 极简模板 | 小型工具 |
| library | 库/SDK 专用模板 | npm 包、Go 库等 |
| webapp | Web 应用模板 | 前后端项目 |
| cli | CLI 工具模板 | 命令行工具 |
| api | API 服务模板 | REST API 服务 |

**技术特点：**

- 支持交互式引导生成
- 自动分析项目结构和技术栈
- 根据项目类型调整文档结构
- 包含完整的最佳实践指南
- 提供多种模板示例参考

**版本历史：**

- v1.0.0（2026-01-23）：初始版本，支持 6 种项目模板

---

## 技术栈

| 技术 | 版本 | 用途 | 官网 |
|------|------|------|------|
| Python | 3.7+ | 主要开发语言 | https://www.python.org |
| Node.js | 16+ | 前端工具和脚本 | https://nodejs.org |
| Markdown | - | 文档编写 | https://www.markdownguide.org |
| MCP | 1.0 | 模型上下文协议 | https://modelcontextprotocol.io |
| pandas | Latest | Excel 数据处理 | https://pandas.pydata.org |
| openpyxl | Latest | Excel 文件操作 | https://openpyxl.readthedocs.io |
| python-pptx | Latest | PPT 生成 | https://python-pptx.readthedocs.io |
| Playwright | Latest | 浏览器自动化 | https://playwright.dev |
| ffmpeg | Latest | 视频处理/渲染（video-agent-kit） | https://ffmpeg.org |
| OpenCV | 4.8+ | 视频抽帧/画面分析（video-agent-kit） | https://opencv.org |
| Edge TTS | Latest | 免费中文语音合成（video-agent-kit） | https://github.com/rany2/edge-tts |
| Remotion | 4.x | 口播视频确定性渲染（poetry-cinema-page、remotion-video-factory、ip-talking-head-lecture） | https://www.remotion.dev |
| 小米 MiMo TTS / 火山引擎 TTS | - | 数字人口播配音与逐字/小句时间戳（ip-talking-head-lecture，可选 edge-tts 免费备胎） | https://micmi.global.s.xiaomi.com / https://www.volcengine.com/product/tts |

### 技术架构

本项目采用模块化架构，每个 Skill 独立运作，通过 Claude Code 的技能激活机制自动加载：

```
skills_collection/
├── skills/           # 各个独立技能模块
│   ├── excel-report-generator/
│   ├── ppt-generator-skill/
│   ├── github-trending/
│   ├── xiaohuihui-tech-article/
│   ├── jimeng_mcp_skill/
│   ├── mp-cover-generator/
│   ├── dify-dsl-generator/
│   ├── xiaohuihui-dify-tech-article/
│   ├── siliconflow-api-skills/
│   ├── github-readme-generator/
│   ├── seedance-video-creator/
│   ├── wechat-article-fetcher/
│   ├── wechat-article-aggregator/
│   ├── wechat-compliance-reviewer/
│   ├── wan-cover-plus/
│   ├── ai-teaching-media/
│   ├── grok-imagine-image/
│   ├── video-agent-kit/
│   ├── poetry-cinema-page/
│   ├── hailaobao-gzh-design/
│   ├── hyperframes-10s-video/
│   ├── whiteboard-video-factory/
│   └── obsidian-search/
└── README.md         # 项目总文档
```

---

## 项目结构

```
skills_collection/
├── poetry-cinema-page/           # 沉浸式古诗词网页生成技能
│   ├── SKILL.md
│   ├── README.md
│   ├── agents/
│   ├── config/
│   ├── references/
│   ├── assets/
│   ├── scripts/
│   └── examples/
├── hailaobao-gzh-design/         # 公众号排版技能（Markdown → 可粘贴 HTML，7 套风格）
│   ├── SKILL.md                  # Claude Code 入口（YAML frontmatter 触发）
│   ├── AGENTS.md                 # 其他 agent（Codex/WorkBuddy/Cursor）对等入口
│   ├── references/               # 7 套 scheme 目录 / 改写规则 / 扩展语法 / 演示文排版模式
│   ├── scripts/                  # schemes.mjs（风格样式生成）+ typeset.mjs（主渲染脚本）
│   └── examples/                 # demo 与 remotion-demo 两组样例输入输出
├── hyperframes-10s-video/        # HyperFrames 声明式分镜动画视频技能
│   ├── SKILL.md                  # 完整 SOP 与 8 条铁律
│   ├── README.md                 # 使用说明（时长/配色/音频三开关）
│   ├── assets/template.html      # 动画模板 + 10 套皮肤 + 控制条
│   ├── scripts/                  # build_html / render / encode / make_srt / tts_scenes 等 7 个脚本
│   └── references/               # 分镜字段定义 / 提示词模板 / 配色画廊 / 可复现范例
├── whiteboard-video-factory/     # 手绘白板「边画边讲」讲解视频工厂（合并自 whiteboard-video + video-common）
│   ├── SKILL.md                  # 技能入口：8 条硬规矩 + 命令表 + 七步流程 + 修改类请求对照表 + 跨平台说明
│   ├── README.md                 # 使用说明 + 来源与合并说明（逐条差异清单）
│   ├── bin/wb                    # CLI：new / scenes / stills / image / logo / tts / render / mix / cover / build / clean
│   ├── lib/                      # scene-dsl（场景 DSL）· render.html + render.js（逐笔渲染器 + 4 路并行出帧）
│   │                             # tts-volc.mjs + tts-edge.py（双配音通道）· captions.cjs（切句烧字幕）
│   │                             # gen-image.mjs（codex 生图 + Canvas 抠图）· fetch-logo.mjs（Commons 官方 Logo）
│   │                             # mix-bgm.mjs（手写 DSP 闪避配乐）· chromium.cjs / proxy.mjs / svg2png.mjs
│   ├── references/               # dsl / scene-patterns / stickers / publish / fact-check / compliance / delivery-qa
│   ├── templates/                # 每期 scenes.js 与 发布.md 模板
│   ├── examples/                 # 一期完整示例（旁白、7 场景、4 贴纸、封面函数、资料来源、发布稿）
│   ├── assets/                   # 小赖手写字体（OFL）+ 样片与封面示例图
│   └── config.json               # 目录 / 语速 / 配乐 / 笔速 / 字幕 / 品牌层 / 封面画幅
├── ip-talking-head-lecture/       # IP 数字人口播动画课件视频工厂（Remotion 出片）
│   ├── SKILL.md                  # 技能入口：硬规矩 + 命令表 + 修改类请求对照表
│   ├── README.md                 # 使用说明
│   ├── bin/iph                   # CLI：new / list / build / publish / render / all / still / srt / voice / kinds / avatars / preset
│   ├── lib/                      # build.mjs（script.json → 配音 → 时间轴/字幕/发布文案）· cues.mjs · publish.mjs
│   │                             # tts/（小米 MiMo / 火山 / edge 三通道配音，带缓存与逐字时间戳）· paths.cjs
│   ├── remotion/                 # React 渲染工程：SceneShell（品牌层/角标/进度条）· Avatar（三帧口型数字人）
│   │                             # scenes/index.tsx（cover/idea/steps/compare/numbers/recap/outro 版式）· src/（含 node_modules，装好即用）
│   ├── references/               # script-format / avatar / voices / publish / delivery-qa
│   ├── templates/                # 每期 script.json 模板
│   ├── assets/                   # 内置两套口播形象（动物卡通·海老豹 / 人物卡通·眼镜青年，各三帧口型）
│   ├── episodes/                 # 每期唯一手写源 script.json 所在
│   ├── config.json               # 目录 / 配音 / 画幅 / 节奏 / 形象 / 品牌层（角标 + 片尾卡）
│   └── .env.example              # TTS 凭证模板（实际 .env 已被 .gitignore 排除）
├── github-trending/              # GitHub Trending 追踪技能
│   ├── Skill.md
│   └── fetch_trending.py
├── ai-teaching-media/             # AI 教学媒体一体化（含 6 个子 skill）
│   ├── SKILL.md                   # 总入口与路由
│   ├── README.md
│   ├── ai-image-generator/        # 通用生图执行层
│   ├── tech-article-diagram/      # 技术长文智能插图
│   ├── edu-subject-infographic/   # 学科知识点竖版信息图
│   ├── edu-teaching-animation/    # 教学动图 + 配音教学视频
│   ├── short-video-cover/         # 短视频 3:4 封面
│   └── article-explainer-video/   # 长文转章节解说视频
├── grok-imagine-image/            # Grok Imagine 文生图技能
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── assets/
│   └── scripts/
│       └── generate.py            # Grok2API 生图脚本
├── excel-report-generator/       # Excel 报表生成技能
│   ├── Skill.md
│   └── excel_generator.py
├── xiaohuihui-tech-article/      # 技术文章生成技能
│   ├── Skill.md
│   ├── cos_utils.py
│   ├── gemai_image_generator.py
│   └── templates/
├── jimeng_mcp_skill/             # 即梦 AI 图像视频生成技能
│   ├── Skill.md
│   └── jimeng_curl.txt
├── mp-cover-generator/           # 公众号封面生成技能
│   ├── Skill.md
│   ├── generate_cover.py
│   └── node_modules/
├── dify-dsl-generator/           # Dify DSL 生成技能
│   ├── Skill.md
│   ├── references/
│   └── examples/
├── xiaohuihui-dify-tech-article/ # Dify 案例文章生成技能
│   ├── Skill.md
│   └── templates/
├── siliconflow-api-skills/       # 硅基流动 API 文档技能
│   ├── Skill.md
│   └── references/
├── ppt-generator-skill/          # PPT 生成技能
│   ├── Skill.md
│   └── ppt_generator.py
├── github-readme-generator/      # GitHub README 生成技能
│   ├── Skill.md
│   ├── templates/               # 各种项目模板
│   │   ├── basic.md
│   │   ├── full.md
│   │   ├── library.md
│   │   ├── webapp.md
│   │   ├── cli.md
│   │   └── api.md
│   ├── examples/                # 示例 README
│   └── README.md
├── seedance-video-creator/      # Seedance 2.0 分镜视频创作技能
│   ├── SKILL.md
│   ├── README.md
│   ├── templates/               # 分镜模板
│   │   └── storyboard-template.md
│   ├── examples/                # 示例提示词
│   │   └── example-prompts.md
│   └── scripts/                 # 视频生成脚本
│       └── generate_video.sh
├── wechat-article-fetcher/      # 微信公众号文章获取技能
│   ├── SKILL.md
│   ├── scripts/                 # 文章获取脚本
│   │   └── fetch_wechat_article.py
│   └── references/              # 参考文档
│       └── wechat_html_structure.md
├── wechat-article-aggregator/   # 微信公众号文章聚合技能
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/                 # 文章聚合脚本
│   │   └── fetch_articles.py
│   └── references/              # 预置公众号列表
│       └── accounts.json
├── obsidian-search/             # Obsidian CLI 查询技能
│   ├── SKILL.md
│   └── references/
│       └── cli-query-patterns.md
├── wechat-compliance-reviewer/  # 微信公众号文章合规审查技能
│   ├── SKILL.md
│   ├── .claude-plugin/
│   │   └── marketplace.json
│   └── references/              # 合规审查参考资料
│       ├── violation-types.md   # 违规类型详解
│       ├── case-studies.md      # 处罚案例库
│       └── compliant-templates.md # 合规话术模板
├── wan-cover-plus/              # Wan2.7 封面图和视频生成技能
│   ├── SKILL.md
│   ├── README.md
│   ├── config.example.yaml      # 配置示例文件
│   ├── requirements.txt         # Python 依赖
│   ├── examples/                # 示例输入 JSON
│   │   ├── demo_wechat_cover.json
│   │   ├── demo_xiaohongshu_cover.json
│   │   ├── demo_relayout_poster.json
│   │   ├── demo_text_to_video.json
│   │   ├── demo_image_to_video.json
│   │   └── demo_reference_to_video.json
│   ├── references/              # 参考文档
│   │   ├── README.md
│   │   ├── input-schema.md
│   │   ├── scenes.md
│   │   └── api-behavior.md
│   ├── assets/                  # 资源文件
│   │   ├── templates/
│   │   └── prompts/
│   └── scripts/                 # Python 脚本
│       ├── generate.py
│       ├── parser.py
│       ├── postprocess.py
│       ├── prompt_builder.py
│       ├── router.py
│       ├── schema.py
│       ├── validator.py
│       └── wan_client.py
│   ├── knowledge-absorber/       # 知识吸收器技能
│   │   ├── SKILL.md
│   │   ├── scripts/              # 处理脚本
│   │   │   ├── content_ingester.py
│   │   │   ├── run_full_pipeline.py
│   │   │   ├── run_wan_generation.py
│   │   │   └── check_wan_task_status.py
│   │   ├── assets/               # CSS/JS 资源
│   │   │   ├── knowledge_card_base.css
│   │   │   ├── knowledge_card_design.css
│   │   │   ├── knowledge_card_ink.css
│   │   │   └── mentor_prompts.json
│   │   └── references/
│   │       └── system_prompt.md
├── video-agent-kit/             # 自动化视频剪辑与解说技能包
│   ├── README.md                # 使用说明（含 Edge TTS 配置）
│   ├── README.upstream.md       # 上游原始文档
│   ├── mcp/                     # MCP 服务器（37 个工具）
│   │   ├── video_edit_server.py # stdio 入口
│   │   └── ve_tools/            # 工具实现（含 edge_tts_provider.py）
│   ├── skills/                  # 5 个子技能
│   │   ├── env-setup/           # 环境体检与依赖安装
│   │   ├── video-edit-agent/    # 总控制器与路由
│   │   ├── video-edit-assembly/ # 多素材组装/混剪
│   │   ├── video-recap-workflows/ # 电影解说 + 体育/电竞集锦
│   │   └── video-speech-workflows/ # 口播浓缩/字幕修复
│   ├── hooks/                   # 会话钩子（可选）
│   ├── commands/                # 斜杠命令（可选）
│   ├── schemas/                 # 工具 JSON Schema
│   ├── examples/                # 使用示例
│   └── requirements.txt         # Python 依赖
├── .gitignore
└── README.md
```

---

## 安装说明

### 环境要求

- Claude Code v2.0 及以上版本
- Python 3.7+（部分技能需要）
- Node.js 16+（部分技能需要）

### 安装步骤

```bash
# 方式一：安装单个 Skill
# Linux/Mac
cp -r skill-name ~/.claude/skills/

# Windows 手动复制
C:\Users\xxx\.claude\skills\skill-name

# 方式二：克隆整个项目
git clone https://github.com/wwwzhouhui/skills_collection.git
cd skills_collection

# 批量安装所有 Skills
cp -r */ ~/.claude/skills/
```

如果你想用中文搜索和安装 skills，可以顺手看看 Skills宝：https://skilery.com

### 配置说明

部分技能需要配置环境变量：

```bash
# 腾讯云 COS（xiaohuihui-tech-article 需要）
export SECRET_ID="your-secret-id"
export SECRET_KEY="your-secret-key"
export COS_BUCKET="your-bucket"
export COS_REGION="your-region"

# Gemai 公益站 API Key（xiaohuihui-tech-article 配图备用通道）
export GEMAI_API_KEY="your-gemai-api-key"

# 即梦 API / Seedance 2.0（jimeng_mcp_skill、mp-cover-generator、seedance-video-creator 需要）
export JIMENG_API_KEY="your-api-key"

# 即梦 API 地址（seedance-video-creator 需要，只填基础地址，不要包含路径）
export JIMENG_API_URL="http://127.0.0.1:8000"

# 即梦 SessionID（seedance-video-creator 需要）
export JIMENG_SESSION_ID="your-sessionid"

# mptext.top API Key（wechat-article-aggregator 需要）
export MPTEXT_API_KEY="your-mptext-api-key"

# DashScope API Key（knowledge-absorber、github-trending-wan 需要）
export DASHSCOPE_API_KEY="your-dashscope-api-key"

# AI 教学媒体生图供应商（ai-teaching-media，任选其一）
export MULERUN_API_KEY="your-mulerun-api-key"
export APIMART_API_KEY="your-apimart-api-key"
export ATLASCLOUD_API_KEY="your-atlascloud-api-key"
export AGNES_API_KEY="your-agnes-api-key"

# AI 教学媒体配音（ai-teaching-media，可选；也可用 edge-tts）
export MINIMAX_API_KEY="your-minimax-api-key"

# Grok Imagine（grok-imagine-image）
export GROK_IMAGINE_API_KEY="your-grok-imagine-api-key"
export GROK_IMAGINE_API_BASE="http://43.163.230.83:8000/v1"
export GROK_IMAGINE_MODEL="grok-imagine-image"

# GitHub Token（github-trending 可选）
export GITHUB_TOKEN="your-github-token"

# 企业微信 Webhook（github-trending 可选）
export WEIXIN_WEBHOOK="your-webhook-url"

# ip-talking-head-lecture（IP 数字人口播视频；凭证写进 skill 根目录 .env，参考 .env.example，勿提交）
export MI_TTS_API_KEY="your-xiaomi-mimo-tts-key"   # 默认引擎：小米 MiMo TTS
export VOLC_TTS_API_KEY="your-volcengine-tts-key"  # 火山引擎 TTS（逐字时间戳，可选）
# 三通道之一 edge-tts 免费无需 Key；引擎/音色/语速在 config.json 的 tts 段切换

# video-agent-kit（视频剪辑与解说；TTS 用 Edge TTS 免费无需配置，ASR 需自备 Key）
export VE_PLUGIN_ROOT="/path/to/skills_collection/video-agent-kit"  # 插件根目录（可自动探测）
export VE_EDGE_TTS_VOICE="zh-CN-XiaoxiaoNeural"    # Edge TTS 默认音色（可选）
export VE_NARRATION_TTS_VOICE="zh-CN-YunxiNeural"  # 口播默认音色（可选）
export VE_BGM_DIR=""                                # 背景音乐目录（可选）
# ASR 转写（可选，不配置则 speech_transcribe 不可用）
export VE_SPEECH_ASR_ENDPOINT="https://your-asr-host"
export VE_SPEECH_ASR_RESOURCE_ID="your-resource-id"
export VE_SPEECH_ASR_API_KEY="your-api-key"
```

---

## 使用说明

### 快速开始

1. 将 Skill 文件夹复制到 `~/.claude/skills/` 目录
2. 在 Claude Code 中输入相关关键词
3. Claude 会自动激活对应的 Skill

### 使用示例

```
# Excel 报表生成
"请基于上面的数据帮我生成图表统计，比如饼状图、柱状图、条形图等"

# PPT 生成
"请使用 ppt-generator-skill 生成一个年度总结 PPT"

# GitHub Trending
"请帮我使用 github-trending 获取今天最热门的 github 开源项目"

# 技术文章生成
"请使用 xiaohuihui-tech-article skill 为这个项目生成公众号文章"

# README 生成
"请使用 github-readme-generator full 模板为我的项目生成 README"

# 微信公众号文章获取
"请帮我获取这篇微信公众号文章 https://mp.weixin.qq.com/s/xxxxx"

# 微信公众号文章聚合
"请使用 wechat-article-aggregator 获取赛博禅心和老金开源最新2篇公众号文章"

# 知识吸收器
"请帮我学习这篇文档 https://example.com/article 并生成知识卡片"
"请分析这个开源项目的代码架构并生成导师级教学笔记"
"请帮我整理这份 PDF 文档，生成知识海报（使用孟菲斯网格风格）"

# IP 数字人口播视频
"请使用 ip-talking-head-lecture 把这篇文章做成数字人口播视频，右下角用我的卡通形象"
"换成人物卡通形象重出一版，片尾卡换成我的标识图"
```

### 高级用法

- **组合使用**: 多个 Skill 可以组合使用，如先用 github-trending 获取项目，再用 xiaohuihui-tech-article 生成文章
- **自定义模板**: 每个 Skill 的模板都可以根据需求自定义修改
- **批量处理**: 部分技能支持批量处理多个文件或项目

---

## 文档地址

- [飞书文档](https://aqma351r01f.feishu.cn/wiki/HF5FwMDQkiHoCokvbQAcZLu3nAg?table=tbleOWb4WgXcxiHK&view=vewGwwbpzl)
- [GitHub 仓库](https://github.com/wwwzhouhui/skills_collection)

![image-20241115093319205](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20241115093319205.png)

---

## 开发指南

### 本地开发

```bash
# 克隆项目
git clone https://github.com/wwwzhouhui/skills_collection.git
cd skills_collection

# 创建新的 Skill 文件夹
mkdir my-new-skill
cd my-new-skill

# 创建 Skill.md 文件
touch Skill.md
```

**Skill.md 基本结构：**

```markdown
---
name: your-skill-name
description: Skill 的简短描述
version: 1.0.0
author: your-name
---

# Your Skill Name

详细的功能说明和使用文档...
```

### 构建部署

Skills 是纯文本配置文件，无需构建部署，直接复制到 Claude Code 的 skills 目录即可使用。

### 贡献指南

欢迎提交你的 Claude Code Skills：

1. Fork 本项目
2. 创建你的 Skill 分支 (`git checkout -b feature/new-skill`)
3. 提交你的更改 (`git commit -am 'Add new skill'`)
4. 推送到分支 (`git push origin feature/new-skill`)
5. 创建 Pull Request

---

## 常见问题

<details>
<summary>如何知道 Skill 是否已激活？</summary>

当 Claude 识别到相关关键词时，会自动激活对应的 Skill。你可以通过 Claude 的回复内容判断，如果回复包含 Skill 中定义的特定结构或风格，说明已成功激活。

</details>

<details>
<summary>Skill 不生效怎么办？</summary>

1. 确认 Skill 文件夹位置正确（~/.claude/skills/）
2. 检查 Skill.md 文件格式是否正确
3. 尝试重启 Claude Code
4. 使用更明确的触发关键词

</details>

<details>
<summary>如何自定义 Skill？</summary>

你可以直接编辑 Skill.md 文件，修改功能说明、触发关键词、输出格式等。修改后 Claude 会在下次激活时使用新的配置。

</details>

<details>
<summary>Skill 冲突怎么办？</summary>

如果多个 Skill 的触发关键词重叠，可以：
1. 使用更具体的关键词
2. 在对话中明确指定要使用的 Skill 名称
3. 调整 Skill.md 中的描述和触发条件

</details>

<details>
<summary>Excel 生成的文件打不开？</summary>

1. 确认安装了正确版本的依赖（pandas、openpyxl）
2. 检查文件扩展名是否为 .xlsx
3. 验证数据格式是否正确
4. 查看错误日志排查具体问题

</details>

<details>
<summary>技术文章风格不符合预期？</summary>

1. 在提示中明确指定"使用小灰灰公众号风格"
2. 提供更详细的项目信息和技术栈
3. 可以要求 Claude 调整特定段落的风格
4. 参考 Skill.md 中的标准模板

</details>

<details>
<summary>jimeng 图像/视频生成失败？</summary>

1. 确认 jimeng-free-api-all Docker 容器正在运行
2. 检查 JIMENG_API_KEY 是否正确配置
3. 验证后端服务可访问：curl http://localhost:8001
4. 确保有足够的 API 积分（免费层每天 66 积分）
5. 图像生成需要 10-20 秒，视频生成需要 30-60 秒，请耐心等待

</details>

<details>
<summary>公众号封面生成器无法生成图片？</summary>

1. 确认 jimeng-free-api-all Docker 容器正在运行
2. 检查 JIMENG_API_KEY 是否正确配置
3. 确保使用 jimeng-3.1 模型（在生成时指定）
4. 图像生成需要 10-20 秒，请耐心等待
5. 检查后端服务可访问：curl http://localhost:8001
6. 验证有足够的 API 积分（免费层每天 66 积分）
7. 如果 HTML 转图片失败，确认已安装 Node.js 16+ 和 Playwright

</details>

<details>
<summary>Dify DSL 生成的工作流无法导入?</summary>

1. 检查 YAML 格式是否正确（使用在线 YAML 验证器）
2. 确认 Dify 版本是否兼容（推荐 0.3.0+）
3. 检查节点 ID 是否唯一
4. 验证变量引用格式是否正确（{{#节点ID.变量#}}）
5. 确保所有必填字段完整
6. 查看 Dify 导入错误提示并修复对应问题

</details>

<details>
<summary>微信公众号文章获取失败？</summary>

1. 优先使用短链接格式（`https://mp.weixin.qq.com/s/xxxxx`），长链接可能触发验证码
2. 批量下载时增大间隔时间：`--interval 5`
3. 确认已安装依赖：`pip install beautifulsoup4 html2text requests`
4. 短时间内频繁请求可能被限流，稍后重试即可
5. 如遇到"环境异常"页面，可尝试配置 Cookie 参数

</details>

<details>
<summary>公众号文章聚合器获取文章内容为空？</summary>

1. 部分图片密集型文章（如纯图片推文）无法提取文本内容，属于正常现象
2. 付费阅读或已被删除的文章无法获取完整内容
3. 确认 API Key 有效：检查 mptext.top 账户状态
4. 如遇 API 限流，增大请求间隔：`--interval 5`
5. 确认已安装可选依赖以获得更好的解析效果：`pip install beautifulsoup4 html2text`

</details>

<details>
<summary>Gemai 公益站文生图失败？</summary>

1. 确认已设置 API Key：`export GEMAI_API_KEY="你的密钥"` 或使用 `--api-key` 参数
2. 检查网络是否能访问 `https://api.gemai.cc`
3. 公益站密钥可能有调用限额，建议申请自己的 Key
4. 图片生成需要较长时间（30-120秒），请耐心等待
5. 如遇到频率限制，稍后重试即可

</details>

<details>
<summary>PPT 生成器生成的文件打不开?</summary>

1. 确认安装了 python-pptx 库：pip install python-pptx
2. 检查 Python 版本是否为 3.7+
3. 确认文件扩展名为 .pptx
4. 验证 JSON 配置文件格式是否正确
5. 使用 PowerPoint 或 WPS 打开文件查看具体错误

</details>

<details>
<summary>知识吸收器内容摄取失败？</summary>

1. URL 链接摄取失败：检查链接有效性，部分动态页面（知乎/CSDN/微信公众号）需要 DrissionPage 渲染
2. PDF 摄取失败：检查是否为扫描件（需要 OCR），确认 PDF 未加密
3. 确认已安装依赖：`pip install requests beautifulsoup4 drissionpage`
4. 网络问题：检查是否能访问目标 URL，部分网站可能需要代理
5. 内容为空：确认 URL/文件有实际内容，部分付费文章无法获取

</details>

<details>
<summary>知识吸收器 Wan 生图失败？</summary>

1. 确认已配置 `DASHSCOPE_API_KEY` 环境变量
2. 检查 API Key 是否有效：登录 DashScope 控制台验证
3. 确认在步骤 2 完成后，用户明确回复"确认生图"才执行步骤 3
4. 生图任务可能需要 10-30 秒，请耐心等待
5. 如遇 `RUNNING` 状态：使用 `--task-id` 参数查询任务状态
6. 海报 Prompt 长度应在 800-2000 字符范围内

</details>

<details>
<summary>真理锚定验证超时？</summary>

1. 真理锚定依赖联网搜索，网络不稳定可能导致超时
2. 即使验证失败，知识卡片仍会生成，标注"真理锚定未完成"
3. 部分 API 签名/版本号可能无法实时验证，标注 `[待确认]`
4. 如频繁超时：检查网络环境，或暂时跳过验证环节
5. 观点、方法论等主观内容不需要验证，可直接输出

</details>

---

## 技术交流群

欢迎加入技术交流群，分享你的 Skills 和使用心得：

![技术交流群](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20260927104256287.png)

---

## 作者联系

- **作者**: wwwzhouhui
- **微信**: laohaibao2025
- **邮箱**: 75271002@qq.com

![微信二维码](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Screenshot_20260123_095617_com.tencent.mm.jpg)

---

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

**微信支付**

![微信支付](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

---

## 项目统计

### 技能统计

- **总技能数**: 29
- **自动化工具**: 5 (excel-report-generator, ppt-generator-skill, github-trending, github-trending-wan, github-readme-generator)
- **内容生成**: 5 (xiaohuihui-tech-article, mp-cover-generator, xiaohuihui-dify-tech-article, knowledge-absorber, hailaobao-gzh-design)
- **AI 多模态**: 7 (jimeng_mcp_skill, seedance-video-creator, wan-cover-plus, ai-teaching-media, grok-imagine-image, video-agent-kit, poetry-cinema-page)
- **视频生成**: 5 (voice-to-video, remotion-video-factory, hyperframes-10s-video, whiteboard-video-factory, ip-talking-head-lecture)
- **数据采集**: 2 (wechat-article-fetcher, wechat-article-aggregator)
- **API 文档**: 1 (siliconflow-api-skills)
- **工作流工具**: 1 (dify-dsl-generator)
- **效率工具**: 2 (obsidian-search, photo-homework-a4)
- **合规审查**: 1 (wechat-compliance-reviewer)

### 最新版本动态

- **ip-talking-head-lecture**: v1.2.0 (2026-10-03) - 迁入本仓库。IP 卡通数字人口播动画课件视频工厂（Remotion + 小米/火山/edge 三通道 TTS）：右下角圆形 IP 数字人讲课（三帧口型 + 说话光环 + 待机浮动）+ 六套动画课件版式 + 烧录字幕跟读高亮；**时长由 TTS 实际音频反推**，改一句旁白整体自动重排，音画字幕天然对齐；一条命令同出 16:9 / 9:16（另支持 1:1）；内置动物卡通（海老豹）/ 人物卡通（眼镜青年）两套形象一键切换，加新形象 = 一个目录三帧图；自动产出各平台发布文案（YouTube 中英双语 + 章节时间轴自动合并）与中英双语 SRT/VTT；v1.2.0 新增**右上角可自定义博主角标**（`brand.corner`）与**片尾品牌卡**（`brand.endCard`，build 时自动追加静音 outro 场景：标识图或手写名 + 品牌色划线 + slogan + 黄色便签 CTA，`brand.logo` 可换成博主标识图）
- **whiteboard-video-factory**: v1.0.0 (2026-09-29) - 初始版本（由 `whiteboard-video` + `video-common` **合并并重命名**），手绘白板边画边讲讲解视频工厂：rough.js 逐笔手绘动画（场景可导出 Excalidraw 回灌）+ 火山/小米/edge-tts 三通道配音 + 字幕逐段跟读高亮（卡拉OK式，色块随语音跳） + TTS 逐字时间戳同时驱动画面排期与字幕切句 + 4 路独立 Chromium 确定性出帧（framemd5 可验）+ 三画幅封面一次出（4:3 / 3:4 / 9:16 抖音）+ 五平台发布文案（视频号 / 小红书 / 抖音 / B 站 / 公众号）+ **时长不限**（按场景数伸缩，2 分钟短片到 30 分钟长片同一套流水线；长片可配 `bgm.playlist` 多首轮播，并提供 `wb tts/render <期> <场景>` 断点续跑）+ 自带事实核查 / 合规自查 / 成片验收 / 交付边界公共工序；全链路本地，不开剪辑软件
- **hailaobao-gzh-design**: v1.0.0 (2026-09-24) - 初始版本，公众号排版：Markdown → 带「复制到公众号」按钮的自包含 HTML，粘进公众号编辑器样式全保留；7 套排版风格（玉石商务 / 暖色编辑部 / 极客单色 / 香槟品牌 / 雾霾笔记 / 午夜研究报告 / 森绿演示）、AI 按规则改写（序号竖线标题 · kicker 语义匹配 · 金句引用 · SummaryCard/InfoCard 卡片 · 总改动 ≤30%）；原始 Markdown 不改动，零 npm 依赖，只需 Node.js ≥ 16
- **hyperframes-10s-video**: v2.0.0 (2026-09-24) - 初始版本，HyperFrames 声明式分镜动画视频：一段文字 → 横屏动画视频 + 同名 SRT 字幕。**三个维度全参数化**——时长任意（`--total=` / `duration` 字段，各幕比例归一、精确到 0.01s，长片靠加幕）、配色 10 套皮肤（tech/wuding/aurora/sunset/ocean/forest/midnight/gold/candy/paper，含可视化画廊 + 预览页实时换肤）、音频可选（默认无声无音轨，edge-tts 配音可一键混音）；9 种场景类型、抽帧核验、字幕自动生成（不手写）、横竖屏与帧率可切，无头 Chromium 逐帧确定性渲染
- **poetry-cinema-page**: v1.0.0 (2026-09-22) - 初始版本，沉浸式古诗词网页生成：文学分镜 + 视觉圣经 + 双服务商四档位生图（火山方舟 Doubao Seedream 5.0 / GPT-Image 网关，主视觉参考链跨服务商）+ edge-tts / 豆包 seed-tts 双引擎 23 音色配音 + 滚动页面 + 浏览器验收，可选 Remotion 口播视频成片
- **remotion-video-factory**: v1.1.0 (2026-09-07) - 审查修复版：tts.py 剥离旁白稿 Markdown 结构行、时间线/字幕/短场景淡入淡出健壮性加固，并新增 check-env.mjs 一键环境自检；视觉优先的程序化视频生产流水线（Remotion + React 代码绘制图形动画 · edge-tts 自动测长配音 · 三层音频 · 确定性渲染 · 双版本交付）
- **video-agent-kit**: v0.4.3 (2026-08-29) - 初始版本，自动化视频剪辑与解说视频技能包：通用剪辑、电影解说（几分钟看完）、足球/篮球集锦、LOL 电竞集锦、口播配音成片；37 个 MCP 工具（抽帧理解/时间线/渲染/QC）；TTS 默认 Edge TTS 免费开箱即用
- **grok-imagine-image**: v1.0.0 (2026-07-26) - 初始版本，通过兼容 Grok2API / OpenAI 风格的 `/v1/images/generations` 调用 `grok-imagine-image` 文生图；内置本地脚本，支持环境变量覆盖、媒体 URL 改写下载与 JSON 输出
- **ai-teaching-media**: v1.0.0 (2026-07-19) - 初始版本，AI 教学媒体一体化技能包，串联 6 个子能力（生图执行层、技术长文插图、学科信息图、教学动图/视频、短视频封面、文章解说视频），支持知识点/长文全套教学生产链路
- **knowledge-absorber**: v0.0.1 (2026-04-11) - 初始版本，深度解析链接/文档/代码，生成导师级教学笔记 + Wan 2.7 知识海报。支持 PDF/Word/Markdown/代码/图片，自动真理锚定验证，国学内容自动水墨风格，11 种海报风格可选
- **github-trending-wan**: v1.0.0 (2026-04-08) - 初始版本，GitHub Trending Top 5 中文信息图海报生成器，抓取热门项目→翻译中文摘要→生成 Wan 2.7 海报 Prompt→可视化海报，支持 10 种视觉风格，3 步引导式工作流
- **wan-cover-plus**: v1.0.0 (2026-04-05) - 初始版本，使用 Wan2.7-image 生成公众号封面图、小红书封面图、种草图和海报改版视觉稿，并支持文生视频、静态图转丝滑动态视频、参考图/参考视频转视频，以及为视频自动补 Edge TTS 配音与字幕烧录。视频任务兼容 Wan 2.6 与 Wan 2.7 模型
- **wechat-compliance-reviewer**: v1.0.0 (2026-03-29) - 初始版本，微信公众号文章合规审查专家，支持 9 大类违规风险检测（诱导分享/欺诈信息/营销推广/版权侵权等），提供详细修改建议和合规话术替代，内置违规类型详解/处罚案例库/合规话术模板三份参考资料
- **obsidian-search**: v1.0.0 (2026-03-13) - 初始版本，Obsidian CLI 查询助手，支持自然语言检索、笔记搜索、上下文查找、任务/标签/属性筛选、反链查询等
- **wechat-article-aggregator**: v1.0.0 (2026-02-23) - 初始版本，支持批量获取公众号文章，预置8个AI技术公众号
- **wechat-article-fetcher**: v1.0.0 (2026-02-22) - 初始版本，支持单篇和批量下载
- **seedance-video-creator**: v1.2.0 (2026-02-22) - 默认模型切换为 seedance-2.0-fast，修复 API 版本兼容问题
- **github-readme-generator**: v1.0.0 (2026-01-23) - 初始版本
- **github-trending**: v1.0.0 (2026-01-22) - 初始版本
- **xiaohuihui-tech-article**: v2.4.0 (2026-02-23) - 新增Gemai公益站双通道文生图,移除硬编码API Key,支持环境变量配置
- **jimeng_mcp_skill**: v2.0.0 (2025-12-14) - 升级至 jimeng-4.5 模型，参数系统重构

### 开发语言

- Python: 6
- Node.js/JavaScript: 3
- Markdown: 3
- MCP: 2
- YAML/DSL: 1
- Bash/Shell: 2

### 维护状态

- ✅ 活跃维护中
- 🔄 持续更新
- 📚 文档完善

---

## 路线图

### 计划中的 Skills

- [ ] **code-reviewer**: 代码审查助手
- [ ] **api-doc-generator**: API 文档生成器
- [ ] **test-case-generator**: 测试用例生成器
- [ ] **database-designer**: 数据库设计助手
- [ ] **deployment-helper**: 部署配置助手

### 优化计划

- [ ] 添加更多 Excel 报表模板
- [ ] 扩展技术文章支持的平台风格
- [ ] 提供交互式配置工具
- [ ] 增加中英文双语支持
- [ ] 扩展 Dify DSL 生成器支持更多节点类型
- [ ] 优化 Dify 案例文章的图片自动生成功能
- [ ] 添加 Dify 工作流 DSL 校验工具

---

## 更新说明

### 2026 年 10 月 3 日 - version 0.0.32

- ✅ 新增 **ip-talking-head-lecture** Skill v1.2.0（IP 卡通数字人口播动画课件视频工厂，自本机 skill 目录迁入）
- ✅ 出片链路：唯一手写源 `episodes/<期>/script.json`（每场景 narration/heading/kind/data）→ `bin/iph` CLI → `lib/build.mjs` 逐场景 TTS 合成 → 按**实际音频时长**反推 timeline.json（16:9 / 9:16 各一份，音画字幕天然对齐）→ Remotion/React 确定性渲染 MP4
- ✅ 画面构成：主画面六套动画课件版式（cover / idea / steps / compare / numbers / recap，横屏左右分栏、竖屏纵向堆叠），主讲 IP 圆形头像常驻右下角（待机浮动 + 三帧口型开合 + 品牌色说话光环 + 声波条），底部烧录字幕逐段跟读高亮，顶部进度条与品牌水印
- ✅ 三通道配音：小米 MiMo TTS（默认，冰糖音色 @1.15x，小句级时间戳）／ 火山引擎（逐字对齐，支持声音复刻）／ edge-tts 免费备胎；引擎、音色、语速、响度全在 `config.json`，凭证走 `.env`（已 `.gitignore` 排除，**入库前务必确认不提交**）
- ✅ 形象系统：内置动物卡通（海老豹）与人物卡通（眼镜青年）两套预设，`iph preset <名>` 一键切换；新增形象 = 一个目录放 `image / mouth-mid / mouth-open` 三帧 + config 登记一行；期目录同名文件可覆盖本期形象
- ✅ v1.2.0 新增品牌层两处可配置项：**右上角博主角标**（`brand.corner.enabled/text`，text 留空自动用 `brand.name`，片尾卡出现时自动隐藏）与**片尾品牌卡**（`brand.endCard`：build 时自动在末尾追加一个静音 `outro` 场景——`brand.logo` 标识图或手写体博主名 + 星花 + 品牌色划线逐笔画出 + slogan + 黄色便签 CTA；`seconds` 调卡片时长，`cta` 留空不出便签，`enabled:false` 关闭）
- ✅ 发布物料：中/英双语字幕 SRT + VTT（英文需 `publish.en.cues` 与中文字幕条数一致才生成，避免时间轴错位）、旁白稿、各平台发布文案（视频号 / 小红书 / 抖音 / B 站 / 公众号 + YouTube 中英双语标题描述，章节时间轴自动合并并满足 ≥3 章、每章 ≥10s）
- ✅ 使用示例：《Meta Muse 爆火，国内 0 门槛注册全攻略》一期实测——文章稿 → 8 场景 script.json → `iph all` 出 128.2s 双画幅成片 + 全套发布物料；抽帧验收角标、片尾卡与字幕高亮均正常
- ✅ 注意：`remotion/node_modules` 一并迁入（约 534MB / 10,619 文件），clone 后无需 `npm install` 即可渲染；若做 git 提交，请先确认 `.env`、`build/`、`remotion/node_modules` 等在 `.gitignore` 覆盖范围内
- ✅ 项目统计：技能 28 → 29；视频生成类 4 → 5

### 2026 年 9 月 29 日 - version 0.0.31

- ✅ 新增 **whiteboard-video-factory** Skill v1.0.0（手绘白板「边画边讲」讲解视频工厂）——由 `whiteboard-video` + `video-common` **两个 skill 合并并重命名**而来
- ✅ 合并原则：白板出片全链路（DSL / 逐笔渲染器 / 双通道 TTS / 字幕 / 混音 / 封面 / 发布文案 / 示例工程）+ 原本散在公共工序里的事实核查、合规自查、成片机器与目视验收、交付边界，并为一体；装入一个目录即可跑，不再需要并列安装 `video-common`
- ✅ 公共工序去重与改写：`platform-copy.md`（多平台文案机制）折进 `references/publish.md` 开头的「动手前先记住三条」与「口吻」；`cover-qa.md` 是用 AI 生图出封面的比例规则，白板封面由 Excalidraw 程序化生成（画幅由代码决定，不存在 AI 画错比例的问题）**不适用故未并入**，其中与画幅无关的目视验收要点折进 `references/delivery-qa.md` 的「封面验收」；原文「四条线 / 其他账号 skill 共用」的跨线表述改写为白板自己的说法
- ✅ 文档入口本地化：`SKILL.md` 里所有 `../video-common/...` 指针改为本仓库 `references/...`，并新增七份 reference 的用途表；README 增加「来源与合并说明」章节，逐条记录取舍
- ✅ 新增 **9:16 封面画幅**（1080×1920，抖音竖屏）：`COVER_SIZES` 加 `9:16`，`coverLayout` 新增长竖版分支，关键内容压在中央安全区（抖音封面上下会被裁到约 1080×1464）；`config.json` 的 `cover.ratios` 默认由两张变三张
- ✅ 新增 **抖音发布规范**：`references/publish.md` 平台表加抖音行 + 新增「抖音怎么写」整节（标题即描述前 55 字、描述 100~200 字、话题 3~5 个整串排最后、不堆 `#热门 #涨粉`、AIGC 必须标注、横版成片在竖屏信息流用 9:16 封面兜底）；模板与示例发布稿同步补抖音小节
- ✅ 修复上游遗留 bug：`lib/render.js` 的 `~` 展开仍在用 `process.env.HOME`（Windows 下会拼出 `C:\c\Users\...` 而 ENOENT），改为 `require('os').homedir()`，与 `lib/paths.cjs`、`lib/scene-dsl.js` 一致
- ✅ 文档加固：`SKILL.md` 的「在 Windows 上跑（本机已适配）」改写为通用的「跨平台说明（Windows / macOS / Linux）」，并修正 edge-tts 缓存的过时说法（现在是缓存键对不上自动重配，不必手删 `work/audio`）；合并两处互相矛盾的渲染耗时说明
- ✅ 冒烟验证：从新目录实跑 `wb new` / `wb scenes` / `wb cover` 全通，三张封面实测 1440×1080 / 1080×1440 / 1080×1920，无重叠越界
- ✅ 项目统计：技能包 44 个文件、约 24 MB（含 22 MB 小赖手写字体），Node.js 脚本 13 个 + Python 1 个 + Bash CLI 1 个，直接 npm 依赖仅 3 个（playwright / roughjs / lz-string）

### 2026 年 9 月 24 日 - version 0.0.30

- ✅ 新增 **hailaobao-gzh-design** Skill v1.0.0（公众号排版：Markdown → 可直接粘贴的公众号 HTML）
- ✅ 一键复制：产物是自包含 HTML，顶栏「复制到公众号」按钮把带内联样式的正文写进剪贴板（`text/html`），粘进公众号编辑器样式全保留，不依赖任何第三方排版网站
- ✅ 7 套排版风格：玉石商务 `jade-business` / 暖色编辑部 `warm-editorial` / 极客单色 `mono-tech` / 香槟品牌 `champagne-brand` / 雾霾笔记 `mist-notebook` / 午夜研究报告 `midnight-report` / 森绿演示 `forest-demo`；每套是「主题色 + 版式 + 强调样式 + 组件皮肤」的整套预设，未知 id 直接报错并列出可用值
- ✅ AI 按规则改写、不生成新事实：标题「序号 | 主标题 | 小字副标题」竖线语法、kicker 语义匹配（STEP / 纯数字 / CASE / Q1 / AVOID / FACT …，不一律甩 STEP）、关键短语加粗、金句转引用、`---` 控呼吸、`<SummaryCard>` / `<InfoCard>` 插卡片
- ✅ 原文零损伤：改写结果落临时文件，原始 Markdown 一个字不动；总改动 ≤ 30%，代码块一字不改，不加原文没有的观点与事实
- ✅ 先问风格再动手：默认必须让用户三选一（首选附理由 + 同类型备选 + 反差款），用户点名 scheme 或授权 auto 才自动选
- ✅ 零依赖、跨 agent 通用：只需 Node.js ≥ 16（ESM），脚本仅用内置 `fs` / `path`，无 npm 包、无需联网；Claude Code 走 `SKILL.md` frontmatter 自动挂载，Codex / WorkBuddy / Cursor / Cline 等走同目录 `AGENTS.md` 对等入口，产物一致
- ✅ 交付物：自包含 HTML（复制按钮 + 正文预览）+ 改写后的临时 Markdown；附 `references/` 四份规则文档（scheme 目录 / 改写规则 / 扩展语法 / 演示文模式）与 `examples/`（demo、remotion-demo）两组样例输入输出
- ✅ 项目统计：技能包 13 个文件（含 `.pi` 任务记录），Node.js 脚本 2 个，零 npm 依赖
- ✅ 文档：**HyperFrames Kinetic Video** 章节补上在线演示视频（README 内联播放器，AI 自我进化 RSI 主题成片：1920×1080 / 30fps，含 AI 配音），读者不必下载即可直接观看

### 2026 年 9 月 24 日 - version 0.0.29

- ✅ 新增 **hyperframes-10s-video** Skill v2.0.0（声明式分镜动画视频）
- ✅ 声明式分镜：`scenes.json` 描述「结构 + 每幕动作」，GSAP 按时间轴执行，内置 9 种场景类型（title/end/bigword/quote/flow/points/bars/typewriter/free）
- ✅ 时长全参数化：默认 10 秒，`--total=20` 或顶层 `"duration": 15` 可产任意时长——各幕 `dur` 按比例归一、末幕吸收舍入漂移，总和精确等于目标（0.01s 级）；长片靠「加幕」而非拉长单幕
- ✅ 配色 10 套皮肤：tech/wuding/aurora/sunset/ocean/forest/midnight/gold/candy/paper（含 paper 浅底深字），同一分镜换肤即换风格；附可视化挑色画廊与预览页控制条实时切换下拉框
- ✅ 音频可选、不写死：默认无声无音轨；要求「带语音」时写 `script.json` → edge-tts 生成整轨配音 → `--keep-dur` 让配音贴合每幕时长 → 混音为 `-a.mp4`
- ✅ 字幕自动生成、不手写：`make_srt.mjs` 按分镜或语音时间轴切分，时间轴与画面同源（`--eff` / `--timing`），长片也不会错位；某幕可用 `"srt"` 字段精确覆盖
- ✅ 逐帧确定性渲染：走 `window.__KINETIC__.seek(t)`（timeline pause + seek），与机器快慢无关，同输入同输出；全量渲染前强制抽帧核验或跑 `check_overflow`
- ✅ 画幅与帧率可切：`--orient=portrait` 出竖屏 1080×1920，`--fps=60` 改帧数不改时长
- ✅ 交付物：MP4（+ 有声版 `-a.mp4`）+ 同名 SRT + 可实时换肤的交互预览页 + 生效分镜 `effective.json` + `gen-log.txt` 生成时间记录
- ✅ 配套文档：SKILL.md（完整 SOP 与 8 条铁律）+ README.md（使用说明）+ references（分镜字段定义 / 提示词模板 / 10 套配色画廊 / 可复现范例）
- ✅ 项目统计：技能包 16 个文件、约 3.6 MB，Node.js 脚本 7 个，输出 1920×1080@30fps

### 2026 年 9 月 22 日 - version 0.0.28

- ✅ 新增 **poetry-cinema-page** Skill v1.0.0（沉浸式古诗词网页生成）
- ✅ 文学分镜 + 视觉圣经：按戏剧功能拆 5–8 个视觉段落，主视觉文生图定调，后续每张图以它作图生图参考，人物与地理不漂移
- ✅ 图像双服务商四档位：火山引擎方舟 Doubao Seedream 5.0（pro/lite）与 GPT-Image 网关（gpt-2/gpt-2.5），可按段落混用，参考链跨服务商成立；batch 计划一次跑完整首诗，重跑自动跳过已完成
- ✅ 配音双引擎 23 个中文音色：edge-tts（免费本地）与豆包 seed-tts-2.0，输出音轨 + 逐行时间轴 sidecar + SRT，附整目录试听页
- ✅ 沉浸式滚动页面：固定图片舞台、双层交叉淡入、克制视差、章节导航，桌面卡片不超半屏、移动端 contain 主图 + 模糊背景，内置可访问的朗读开关
- ✅ 口播视频（可选）：Remotion 渲染 1920×1080/30fps，确定性运镜、双层级硬切字幕、片头尾字卡、胶片颗粒与暗角
- ✅ 完整示例《将进酒》：分镜文档、方舟与网关两套生图计划、朗诵稿、朗诵版与讲解版两支视频计划
- ✅ 项目统计：技能包 30 个文本文件，Python 2,915 行（ark_image 1,429 · narration 765 · video 678 · extract 43），TypeScript/TSX 1,257 行，6 篇参考文档

### 2026 年 9 月 8 日 - version 0.0.27

- ✅ 新增 **remotion-video-factory** Skill v1.1.0（视觉优先的程序化视频工厂）
- ✅ Remotion + React 代码绘制精确图形动画（注意力矩阵/连线拓扑/数据图表/数字滚动/流程图解），文字零乱码、结构可参数化、改数据自动重排
- ✅ edge-tts 中文配音分段生成 + ffprobe 实测时长自动重建时间线（场景 = max(视觉最短, 配音+40f)），旁白永不被画面切走
- ✅ 三层音频：配音 + BGM（淡入出，可开关）+ SFX 钉帧表（相对帧表达式）；确定性渲染，同样输入永远渲出同样的帧
- ✅ 双版本交付：带 BGM / 无 BGM + 逐句 SRT 字幕；配套 5 个脚本（check-env / selftest / tts.py / build-timeline / render.mjs）
- ✅ 配套文档：SKILL.md + README.md（含项目统计与更新说明）+ references（八步工作流 · 8 种动画模式 · 声音设计）+ examples 实战案例复盘（《1M 上下文的秘密》125s）
- ✅ 项目统计：技能包 ≈285 KB、文本文件 28 个、代码 ≈1,063 行（ts/tsx ≈403 · mjs 518 · py 142）、1920×1080@30fps、8 种动画模式

### 2026 年 9 月 5 日 - version 0.0.26

- ✅ 新增 **photo-homework-a4** Skill v1.0.0
- ✅ 支持从手写作业照片中识别作业内容，按科目整理并提取日期
- ✅ 支持背诵类、书面类、阅读类和材料类作业分类打标与数量统计
- ✅ 基于 `assets/homework-a4-template.html` 生成一页 A4 纵向可打印 HTML 作业清单
- ✅ 内置科目卡片、主题配色、温馨提示、打印勾选框和学生/家长签名区
- ✅ 功能说明效果图暂留空位，待后续补充
- ✅ 新增 **voice-to-video** Skill v1.2.0（口播文字稿一键成片）
- ✅ 无素材出片：口播稿 → Edge TTS 配音（逐词时间戳）→ HTML 动画合成 → 无头浏览器逐帧确定性渲染 MP4
- ✅ 画音逐词对应：一句口播一个场景，字幕逐词卡拉OK高亮，场景切换/元素出场全部由词级时间戳驱动
- ✅ 确定性渲染：同输入同输出，可 git 管理、看 diff，支持断点续渲与 `--style-kit` 一键换风格重渲
- ✅ 13 套画面风格（BlockFrame/暗夜HUD/编辑杂志/终端极客/手绘白板/极简瑞士/国潮水墨/玻璃拟态/黏土软胶/蓝图工程/像素游戏等），每种含独立版式 DNA
- ✅ 配套文档：SKILL.md（六步工作流）+ README.md（完整说明书）+ references（合成规范/风格目录与版式 DNA）

### 2026 年 8 月 29 日 - version 0.0.25

- ✅ 新增 **video-agent-kit** Skill v0.4.3
- ✅ 自动化视频剪辑与解说视频技能包：通用剪辑、电影解说、体育/电竞集锦、口播配音成片
- ✅ 5 个子技能：`env-setup`（环境体检）、`video-edit-agent`（总控制器）、`video-edit-assembly`（多素材组装）、`video-recap-workflows`（解说/集锦）、`video-speech-workflows`（口播浓缩/字幕）
- ✅ 37 个 MCP 工具：抽帧理解、局部复看、字幕烧录、时间线、预览渲染、QC 质检
- ✅ TTS 默认 **Edge TTS**（免费免 Key），中文音色开箱即用（晓晓/云希/云健等）
- ✅ 文档：独立 README.md（使用说明）+ README.upstream.md（上游原始文档）

### 2026 年 7 月 26 日 - version 0.0.24

- ✅ 新增 **grok-imagine-image** Skill v1.0.0
- ✅ 使用 `grok-imagine-image` 模型，通过兼容 Grok2API / OpenAI 风格接口文生图
- ✅ 仅调用 `POST /v1/images/generations`，避免误用 Chat Completions
- ✅ 内置本地脚本 `scripts/generate.py`，支持 prompt 文件、尺寸、数量、超时参数
- ✅ 媒体 URL 自动改写：接口返回 `127.0.0.1` 时替换为配置的公网主机并下载
- ✅ Agent 友好输出：支持 `--json` 机器可读结果，便于后续工作流解析
- ✅ 配置可覆盖：支持 `GROK_IMAGINE_API_KEY` / `GROK_IMAGINE_API_BASE` / `GROK_IMAGINE_MODEL` 与命令行参数
- ✅ 默认配置：API `http://43.163.230.83:8000/v1`、尺寸 `1024x1024`、超时 180 秒
- ✅ 适用场景：明确指定 Grok Imagine 生图，或其他 Skill/本地工作流复用该模型

### 2026 年 7 月 19 日 - version 0.0.23

- ✅ 新增 **ai-teaching-media** Skill v1.0.0
- ✅ AI 教学媒体一体化技能包：一个目录串联 6 个子能力
- ✅ 子 skill 覆盖：
  - `ai-image-generator` - 通用生图执行层（MuleRun / APImart / AtlasCloud / Agnes）
  - `tech-article-diagram` - 技术长文智能插图（16:9）
  - `edu-subject-infographic` - 学科知识点竖版信息图（9:16）
  - `edu-teaching-animation` - 教学动图 + 配音教学视频
  - `short-video-cover` - 短视频 3:4 封面
  - `article-explainer-video` - 长文转章节解说视频（1080p）
- ✅ 意图自动路由：根据用户目标进入对应子 skill，并按流水线串联整套教学资产
- ✅ 推荐流水线：
  - 知识点全套：信息图 → 教学动图/配音视频 → 短视频封面
  - 技术长文全套：文章插图 → 章节解说视频 → 可选封面
  - 口播发布包：3:4 封面 + 教学/解说视频
- ✅ 配音与成片：支持 Minimax TTS / Edge TTS，结合 HyperFrames + ffmpeg 渲染
- ✅ 环境依赖：生图供应商 API Key（任选其一）+ Node.js ≥ 22 + ffmpeg

### 2026 年 4 月 11 日 - version 0.0.22

- ✅ 新增 **knowledge-absorber** Skill v0.0.1
- ✅ 深度解析链接/文档/代码，生成导师级教学笔记 + Wan 2.7 知识海报
- ✅ 支持 PDF/Word/Markdown/代码/图片等多种输入格式
- ✅ 自动真理锚定验证（联网验证数据、API 签名、版本号、历史事件）
- ✅ 标注不确定内容：[已过时]、[存在争议]、[待确认]
- ✅ 11 种海报风格自动判断（坐标蓝图/复古波普/文件夹/热敏纸/复古手帐/陶土手绘/酸性复古/剧场票据/矢量插图/孟菲斯网格/水墨国学）
- ✅ 国学内容自动触发水墨风格（风格 11）
- ✅ 3 步引导式工作流：启动询问 → 知识摄取与验证 → 确认后生图
- ✅ 输出知识卡片 Markdown + 交互式 HTML + 海报 Prompt（可选）
- ✅ 依赖 DashScope API 提供翻译和 Wan 2.7 生图能力

### 2026 年 4 月 8 日 - version 0.0.21

- ✅ 新增 **github-trending-wan** Skill v1.0.0
- ✅ GitHub Trending Top 5 中文信息图海报生成器
- ✅ 抓取热门项目 → 翻译中文摘要 → 生成 Wan 2.7 海报 Prompt → 可视化海报
- ✅ 支持 10 种视觉风格（坐标蓝图 / 复古波普 / 文件夹 / 热敏纸 / 复古手帐 / 陶土手绘 / 酸性复古 / 剧场票据 / 矢量插图 / 孟菲斯网格）
- ✅ 采用 3 步引导式工作流：启动询问 → 信息提取 → 确认生图
- ✅ 输出文件：中文简报 Markdown、Wan 2.7 Prompt、可视化海报 PNG
- ✅ 依赖 Wan-skills-main 提供 Wan 2.7 生图能力

### 2026 年 4 月 5 日 - version 0.0.20

- ✅ 新增 **wan-cover-plus** Skill v1.0.0
- ✅ 使用 Wan2.7-image 生成公众号封面图、小红书封面图、种草图和海报改版视觉稿
- ✅ 支持文生视频、静态图转丝滑动态视频、参考图/参考视频转视频
- ✅ 视频后处理：自动 Edge TTS 配音、SRT 字幕生成、字幕烧录
- ✅ 智能场景识别：自动判断任务类型（从零出图 vs 改版重排）
- ✅ 多平台适配：支持微信横版封面、小红书竖版封面等多种规格
- ✅ Wan 2.6 / 2.7 兼容：视频任务兼容两代模型协议
- ✅ 图片任务场景：
  - `wechat_cover` - 横版文章头图、技术媒体头图
  - `xiaohongshu_cover` - 竖版信息流封面、种草图
  - `relayout_poster` - 保留原主体/信息层级的改版设计
- ✅ 视频任务类型：
  - `text_to_video` - 纯文字描述生成视频
  - `image_to_video` - 静态图转动态视频
  - `reference_to_video` - 参考图/参考视频转视频
- ✅ 输出格式：PNG/MP4 + `.prompt.txt` sidecar，支持视频配音和字幕烧录

### 2026 年 3 月 29 日 - version 0.0.19

- ✅ 新增 **wechat-compliance-reviewer** Skill v1.0.0
- ✅ 微信公众号文章合规审查专家，根据微信公众平台运营规范审查文章内容
- ✅ 识别违规风险点并给出修改建议，支持发布前合规检查
- ✅ 支持 9 大类违规检测：
  - **高风险违规**：诱导分享/诱导关注、营销推广/优惠码、欺诈/虚假信息、版权/知识产权
  - **中风险违规**：金融/支付相关、技术外挂/绕过付费、夸大/虚假宣传
  - **低风险违规**：外部链接/导流、敏感话题（政治、色情、赌博、暴力）
- ✅ 快速审查清单：一键检查诱导分享词汇、优惠码链接、绝对化用语、版权风险等
- ✅ 分级处理机制：高风险必须修改、中风险强烈建议修改、低风险可考虑修改
- ✅ 违规话术对照表：提供合规替代方案（如"白嫖"→"免费体验"、"最强"→"优秀"）
- ✅ 审查报告输出：包含风险等级总览、详细问题清单、修改建议、综合发布结论
- ✅ 参考资料：
  - `references/violation-types.md` - 违规类型详解与处罚标准
  - `references/case-studies.md` - 10 个真实处罚案例分析
  - `references/compliant-templates.md` - 合规话术模板库


### 2026 年 3 月 13 日 - version 0.0.18

- ✅ 新增 **obsidian-search** Skill v1.0.0
- ✅ Obsidian CLI 查询助手，根据自然语言检索需求生成合适的 Obsidian CLI 查询命令
- ✅ 支持多种查询模式：
  - `obsidian search` - 文本搜索，查找包含关键词的笔记
  - `obsidian search:context` - 带上下文搜索，显示关键词出现的行
  - `obsidian read` - 读取指定笔记的完整内容
  - `obsidian files` - 列出指定目录下的文件
  - `obsidian tasks` - 查询待办事项
  - `obsidian tags` - 查看标签分布统计
  - `obsidian backlinks` - 查询反向链接
  - `obsidian links` - 查询出链
  - `obsidian outline` - 查看笔记大纲/标题层级
- ✅ 智能命令选择：根据用户自然语言描述自动匹配最合适的 CLI 命令
- ✅ 结果聚类总结：不原样倾倒输出，提供简洁的关键发现汇总
- ✅ 支持组合查询策略：先搜再读、先列再筛、先看关系再读正文
- ✅ 参考资料：`cli-query-patterns.md` 常用查询命令、参数选择和自然语言到命令的映射


### 2026年2月23日 - version 0.0.17

- ✅ **重要更新** xiaohuihui-tech-article Skill 至 v2.4.0
- ✅ 新增 Gemai 公益站（api.gemai.cc）作为备用文生图通道
- ✅ 新增 `gemai_image_generator.py` 工具类，支持 OpenAI 标准格式调用 Gemini-3-Pro-Image-Preview 模型
- ✅ 支持双通道自动切换策略（自建API优先，失败回退Gemai公益站）
- ✅ Gemai通道支持批量生成（1-4张）、负向提示词、风格控制、宽高比
- ✅ 移除硬编码 API Key，改为环境变量 `GEMAI_API_KEY` 或命令行 `--api-key` 参数传入
- ✅ 新增命令行调用方式，支持 `python3 gemai_image_generator.py` 直接生成图片
- ✅ 更新图片生成文档，补充双通道调用示例和参数说明

### 2026年2月23日 - version 0.0.16

- ✅ 新增 wechat-article-aggregator Skill v1.0.0
- ✅ 通过 mptext.top API 批量获取指定公众号博主的最新文章列表
- ✅ 支持按公众号名称或 fakeid 获取，预置 8 个热门 AI 技术公众号
- ✅ 自动下载文章 HTML 并解析为 Markdown/HTML/纯文本/JSON 格式
- ✅ 智能 HTML 正文解析，提取 `#js_content` 区块内容
- ✅ 可选依赖自动降级，无 beautifulsoup4 时使用内置解析器
- ✅ 生成 summary.json 元数据汇总文件
- ✅ 支持 `--list-accounts` 查看预置公众号列表

### 2026年2月22日 - version 0.0.15

- ✅ 新增 wechat-article-fetcher Skill v1.0.0
- ✅ 支持微信公众号文章获取，自动提取标题、作者、公众号名称、正文、图片等元数据
- ✅ 支持单篇和批量下载（空格或逗号分隔多个链接）
- ✅ 自动下载文章内所有图片到本地
- ✅ HTML 转 Markdown 格式，生成格式化独立 HTML 文件
- ✅ 批量下载间隔控制（`--interval`），避免触发微信反爬机制
- ✅ 支持仅输出元数据 JSON（`--json`）模式
- ✅ 提供 Python 库调用接口（`fetch_article` 和 `batch_fetch`）

### 2026年2月22日 - version 0.0.14

- ✅ **重要更新** seedance-video-creator Skill 至 v1.2.0
- ✅ 默认模型从 `jimeng-video-seedance-2.0` 切换为 `seedance-2.0-fast`（快速版）
- ✅ 所有 curl 示例添加 `resolution` 参数（默认 `720p`）
- ✅ 修复 Authorization 头说明：需要 `Bearer` 前缀
- ✅ 新增重要说明：**必须使用 `jimeng-free-api-all` 镜像**
- ✅ 旧版 `jimeng-free-api` 不含 Seedance 路由和浏览器代理，会静默回退到 `jimeng-video-3.0`
- ✅ README 新增 Seedance 模型可用性验证命令
- ✅ 更新 `generate_video.sh` 脚本默认模型和帮助文本
- ✅ 同步更新所有示例文件的模型名和参数

### 2026年2月11日 - version 0.0.13

- ✅ **重大更新** seedance-video-creator Skill 至 v1.1.0
- ✅ 实现三阶段工作流：分镜提示词 → 文生图首帧 → 图片+提示词生成视频
- ✅ 修复 Seedance 2.0 纯文本生成报错（`code: -2001`，必须至少一张图片）
- ✅ 新增自动调用文生图 API（jimeng-4.5）生成首帧参考图
- ✅ 生成双提示词：首帧图片提示词（静态画面）+ 视频分镜提示词（含 @1 引用）
- ✅ 视频时长扩展为 4-15 秒连续范围
- ✅ 新增模型名 `jimeng-video-seedance-2.0`（兼容 `seedance-2.0`）
- ✅ 修复 Authorization 头不需要 Bearer 前缀
- ✅ 更新 generate_video.sh 脚本支持三阶段工作流（新增 `--image-prompt` 参数）
- ✅ 更新所有示例、模板、文档匹配新工作流

### 2026年2月10日 - version 0.0.12

- ✅ 新增 seedance-video-creator Skill
- ✅ 融合 Seedance 2.0 专业分镜提示词生成 + 即梦 API 视频生成
- ✅ 5 步分镜引导流程，6 套场景模板
- ✅ 支持多图参考（最多9张）、角色一致性、运镜复刻
- ✅ 一键调用 API 生成视频并自动下载
- ✅ 三种工作模式：完整引导/快速生成/纯提示词
- ✅ 提供独立 Bash 脚本 generate_video.sh

### 2026年1月23日 - version 0.0.11

- ✅ 新增 github-readme-generator Skill
- ✅ 专业的 GitHub 项目 README.md 生成器
- ✅ 支持 6 种项目模板（basic/full/library/webapp/cli/api）
- ✅ 交互式生成和基于现有项目自动生成
- ✅ 自动识别项目类型和技术栈

### 2026年1月22日 - version 0.0.10

- ✅ 新增 github-trending Skill
- ✅ 自动抓取 GitHub Trending 今日前 5 热门项目
- ✅ 拉取 README 并生成中文摘要（项目是什么、解决问题、技术栈、Star 数量）
- ✅ 企业微信机器人推送摘要
- ✅ 支持 GITHUB_TOKEN/WEIXIN_WEBHOOK 可选配置

### 2025年12月14日 - version 0.0.9

- ✅ **重大更新** xiaohuihui-tech-article Skill 至 v2.1.0
- ✅ 新增即梦AI自动配图与腾讯云COS上传功能
- ✅ 集成 jimeng_mcp_skill 实现 AI 图片生成
- ✅ 新增 cos_utils.py 实现腾讯云COS文件上传
- ✅ 支持图片占位符自动替换为真实URL
- ✅ 支持内存直接上传避免本地缓存
- ✅ **重要更新** jimeng_mcp_skill 升级至 v2.0.0
- ✅ 模型升级：从 jimeng-4.0 升级至 jimeng-4.5
- ✅ 参数系统重构：ratio 替代 width/height，resolution 替代 sample_strength
- ✅ 添加新的宽高比和分辨率预设选项
- ✅ 更新所有文档、示例和 API 参考

### 2025年12月4日 - version 0.0.8

- ✅ 新增 ppt-generator-skill Skill
- ✅ 基于商务模板的专业 PPT 生成器
- ✅ 固定 25 页结构（封面→目录→4章节→结束→字体说明→版权）
- ✅ 三种主题风格：暖色调、商务简约、莫兰迪色系
- ✅ 支持 JSON 配置文件和 Python 代码调用
- ✅ 适用于年度总结、项目汇报、工作述职等场景

### 2025年11月22日 - version 0.0.7

- ✅ 新增 dify-dsl-generator Skill
- ✅ 支持自动生成 Dify 工作流 DSL/YML 文件
- ✅ 基于 86+ 真实案例深度学习
- ✅ 支持所有主要节点类型和复杂工作流逻辑
- ✅ 新增 xiaohuihui-dify-tech-article Skill
- ✅ 专为 Dify 工作流案例分享设计
- ✅ 遵循小灰灰公众号写作规范
- ✅ 包含工作流节点详解、插件安装教程、MCP 集成指南
- ✅ 支持自动生成配图并上传腾讯云 COS 图床

### 2025年11月19日 - version 0.0.6

- ✅ 新增 siliconflow-api-skills Skill
- ✅ 支持硅基流动云服务平台完整文档
- ✅ 包含大语言模型 API、图片生成、向量模型等文档
- ✅ 提供 Chat Completions API 和 Stream 模式指南

### 2025年11月15日 - version 0.0.5

- ✅ 更新 mp-cover-generator Skill 到 v3.1.1
- ✅ 新增描边卡通字体效果（鲜艳色彩 + 多层描边）
- ✅ 新增垂直居中布局（完美视觉平衡）
- ✅ 增大字体（4vw → 5vw），更加醒目
- ✅ 禁止副标题折行（保持单行显示）
- ✅ 新增 HTML 转图片功能（Playwright 驱动）
- ✅ 完整页面截图（修复截断问题，5120x2916 高清）
- ✅ 自动检测内容高度并调整视口
- ✅ 支持 PNG 和 JPEG 双格式输出

### 2025年11月15日 - version 0.0.4

- ✅ 新增 mp-cover-generator Skill v3.0.0
- ✅ 从 jimeng-image-generator 迁移到 jimeng-mcp-server
- ✅ 支持 21:9 公众号封面图生成
- ✅ 返回 4 张可选图片,提供更多风格选择

### 2025年11月15日 - version 0.0.3

- ✅ 新增 jimeng_mcp_skill Skill
- ✅ 支持 AI 图像和视频生成
- ✅ 集成即梦 AI 多模态能力

### 2025年11月12日 - version 0.0.2

- ✅ 新增 excel-report-generator Skill
- ✅ 支持数据分析报表生成
- ✅ 支持图表创建和样式应用

### 2025年11月10日 - version 0.0.1

- ✅ 新增 xiaohuihui-tech-article Skill
- ✅ 实现标准四段式结构
- ✅ 支持口语化技术写作

---

## 🎉 致谢

感谢以下项目对本项目提供的灵感和支持：

1. [Claude Code](https://claude.ai/code)

   Anthropic 官方推出的 AI 编程助手，提供强大的代码理解和生成能力。

2. [pandas](https://github.com/pandas-dev/pandas)

   强大的 Python 数据分析库，excel-report-generator 的核心依赖。

3. [openpyxl](https://github.com/theorchard/openpyxl)

   用于读写 Excel 2010 xlsx/xlsm 文件的 Python 库。

4. [jimeng-mcp-server](https://github.com/wwwzhouhui/jimeng-mcp-server)

   基于 MCP 协议的即梦 AI 集成服务器，jimeng_mcp_skill 的核心依赖。

5. [即梦 AI](https://jimeng.jianying.com/)

   字节跳动旗下的多模态 AI 生成平台，提供图像和视频生成能力。

6. [elementsix-skills](https://github.com/elementsix/elementsix-skills)

   Seedance 2.0 分镜提示词 Claude Code Skill，seedance-video-creator 的分镜引导参考。

7. [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all)

   即梦 AI 逆向 API 接口，seedance-video-creator 的视频生成后端。

---

## 问题反馈

如有问题，请在 GitHub Issue 中提交，在提交问题之前，请先查阅以往的 issue 是否能解决你的问题。

---

## License

MIT License

---

## Star History

如果觉得项目不错，欢迎点个 Star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=wwwzhouhui/skills_collection&type=Date)](https://star-history.com/#wwwzhouhui/skills_collection&Date)

---

**开始使用**: 选择一个 Skill，按照使用说明安装，然后在 Claude Code 中尽情使用吧！

**文档生成时间**: 2026 年 10 月 3 日 (v0.0.32)
