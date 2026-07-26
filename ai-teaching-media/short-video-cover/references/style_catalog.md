# 短视频封面 · 风格目录索引（3:4 竖版）

本文档只负责**快速选风格**。每种风格的完整提示词模板放在 `references/styles/{风格}.md`，通用品牌基线和填空指引见 `references/brand_baseline.md`。

## 全风格通用品牌基线

不变的元素见 [`brand_baseline.md`](./brand_baseline.md)：画幅、人物、表情默认值、标题原则、视觉层级、水印、禁用项以及通用填空指引。

## 风格快速选择表

| 编号 | 风格名 | 文件 | 核心特征 | 最适合的内容 |
|---|---|---|---|---|
| 1 | **深色科技标题风** | [`styles/dark-tech-title.md`](./styles/dark-tech-title.md) | 黑底暗网格 + 巨型标题 + 小比例人物 + 青蓝/亮黄 | 通用技术教程，安全牌 |
| 2 | **明亮 YouTuber 风** | [`styles/bright-youtuber.md`](./styles/bright-youtuber.md) | 暖米/浅灰明亮背景 + 粗体描边字 + 人物稍大居中 | 科普、生活化 AI 技巧、破圈内容 |
| 3 | **双屏对比叙事风** | [`styles/split-screen-narrative.md`](./styles/split-screen-narrative.md) | 问题截图 vs 解决截图，人物居中连接 | 避坑、报错修复、前后对比 |
| 4 | **产品主视觉风** | [`styles/product-hero.md`](./styles/product-hero.md) | UI/产品界面占 60-70%，人物边角指引 | 工具测评、软件教程、产品演示 |
| 5 | **拼贴信息飓风** | [`styles/collage-info-storm.md`](./styles/collage-info-storm.md) | 多张 UI 碎片分层叠加，纵深感和信息密度高 | 工作流、多工具组合、复杂流程 |
| 6 | **工作台场景风** | [`styles/workspace-scene.md`](./styles/workspace-scene.md) | 真实 desk/setup 场景，人物在环境里 | Vlog 式教程、设备评测、真实演示 |
| 7 | **故障警示风** | [`styles/glitch-warning.md`](./styles/glitch-warning.md) | 暗色底 + glitch/故障效果 + 红色警示元素 | Bug 排查、安全提醒、避坑指南 |
| 8 | **Agent 号召风** | [`styles/agent-hype.md`](./styles/agent-hype.md) | 深蓝紫底 + 蓝紫渐变云朵图标 + 亮黄对话气泡 + 巨型白字黄强调 | AI 工具推荐、Agent 概念、开发者效率、行动号召类内容 |
| 9 | **卡片展示人设风** | [`styles/card-showcase.md`](./styles/card-showcase.md) | 黑橙渐变 + 人物居中 + 2-4 张内容卡片 | 工具合集、产品对比、技巧盘点 |
| 10 | **萌宠代码风** | [`styles/cute-mascot.md`](./styles/cute-mascot.md) | 深蓝底 + 渐变粉橙大标题 + 3D 小龙虾吉祥物 + 漂浮代码积木 | 轻松入门、趣味性编程、AI 技巧 |
| 11 | **手持设备展示风** | [`styles/device-showcase.md`](./styles/device-showcase.md) | 深空星云背景 + 人物双手持设备怼镜头 + 屏幕展示 UI | 网页/App 展示、UI 设计、作品集、高端产品演示 |

## 如何新增风格

1. 在 `references/styles/` 新建 `{style-slug}.md`。
2. 文件内包含：风格一句话定位、`视觉特征`/`固定`/`变量`、完整的提示词模板代码块。
3. 必须引用 [`brand_baseline.md`](./brand_baseline.md) 中的品牌基线。
4. 在本文件的“风格快速选择表”里加一行。
5. 在 `SKILL.md` 第零步的风格列表里同步新增。
