# diagram-video-factory · 图解动画视频工厂

扁平图解动画风"图随话动"讲解视频出片 skill——把一个技术概念做成"程序员老王"式的科普视频：
米白纯色背景 + 白卡片 + 橙红绿语义色图形，元素随旁白逐个生长出现，章节制结构，结尾列参考文献。

- **SKILL.md** 是给 AI 看的完整工作规范（流程、规矩、命令、排错）。
- **lib/** 是流水线：场景 DSL（Excalidraw 格式，可在 Obsidian 微调）→ Playwright/Chromium 渲染 → ffmpeg 合成 → 字幕/封面/发布文案。
- **bin/dg** 是 CLI；**config.json** 是全部配置；**references/** 是细分手册。

```bash
bin/dg new "残差流是什么"     # 建期
bin/dg build "残差流是什么"   # 出片
```

姊妹项目：`whiteboard-video-factory`（手绘白板逐笔动画风）。同一条流水线，两种视觉语言：
| | whiteboard（白板） | diagram（图解） |
|---|---|---|
| 质感 | 手绘线条、纸底、逐笔画出 | 扁平矢量、米白底、淡入生长 |
| 适合 | 轻快科普、工具上手 | 硬核概念讲解、原理拆解 |
| 记忆点 | 画笔动画 | 语义色纪律 + 招牌图（架构流/聊天UI/卡片堆/向量） |

依赖：Node.js、ffmpeg/ffprobe、（贴纸生图）本地 codex CLI、（配音）火山或小米或 edge-tts 凭证（`.env`）。
