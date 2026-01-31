# Claude Code Skills Collection

个人开发的 Claude Code Skills 集合，提供实用的技能工具，助力提升开发效率和内容创作。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-0.0.11-green.svg)
![Skills](https://img.shields.io/badge/skills-10-orange.svg)

> 分享一些好用的 Claude Code Skills，自用、学习两相宜，适用于 Claude Code v2.0 及以上版本。

## 项目介绍

本项目是个人开发的 Claude Code Skills 集合，提供实用的技能工具，助力提升开发效率和内容创作。分享一些好用的 Claude Code Skills，自用、学习两相宜，适用于 Claude Code v2.0 及以上版本。

Claude Skills 是 Claude Code 的扩展能力，通过编写技能文档（Skill.md），可以让 Claude 在特定场景下自动激活相应的专业知识和能力。

### 核心功能

- **自动化工具**: Excel 报表生成、PPT 生成、GitHub Trending 追踪
- **内容生成**: 技术文章、公众号封面、README 文档生成
- **AI 多模态**: 即梦 AI 图像和视频生成
- **工作流工具**: Dify DSL/YML 文件生成器
- **API 文档**: 硅基流动云服务平台完整文档

### 适用场景

- Claude Code 用户扩展能力
- 自动化办公和内容创作
- 开源项目文档规范化
- 技术学习和实践

## Skills 清单

| Skill 名称              | 功能说明                                                     | 技术栈                               | 更新时间       | 作者       | 版本  |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------ | -------------- | ---------- | ----- |
| github-readme-generator | 专业的 GitHub 项目 README.md 生成器，自动生成符合开源社区规范的文档结构，支持 6 种项目模板（basic/full/library/webapp/cli/api），交互式生成和自动识别项目类型 | Markdown、文档生成、模板系统 | 2026年1月23日 | wwwzhouhui | 1.0.0 |
| github-trending | 获取 GitHub Trending 前五项目 README 与摘要，并发送企业微信消息，适用于热门项目跟踪、技术趋势简报与团队分享 | Python、GitHub Trending、企业微信机器人 | 2026年1月22日 | wwwzhouhui | 1.0.0 |
| xiaohuihui-tech-article | 专为技术实战教程设计的公众号文章生成器，遵循小灰灰公众号写作规范，集成即梦AI自动配图与腾讯云COS上传功能，自动生成包含前言、项目介绍、部署实战、总结的完整技术文章 | Markdown、模板生成、即梦AI、腾讯云COS | 2025年12月14日 | wwwzhouhui | 2.1.0 |
| jimeng_mcp_skill        | AI 图像和视频生成技能，升级至 jimeng-4.5 模型，支持 ratio/resolution 新参数系统，文生图、图像合成、文生视频、图生视频四大核心能力 | MCP、Python、Docker、即梦 AI         | 2025年12月14日 | wwwzhouhui | 2.0.0 |
| ppt-generator-skill     | 基于商务模板的专业 PPT 生成器，支持固定 25 页结构（封面→目录→4章节→结束），提供暖色调、商务简约、莫兰迪色系三种主题风格，支持 JSON 配置和代码调用 | Python、python-pptx                 | 2025年12月4日  | o3sky      | 1.0.0 |
| dify-dsl-generator      | 专业的 Dify 工作流 DSL/YML 文件生成器，根据用户业务需求自动生成完整的 Dify 工作流配置文件，支持各种节点类型和复杂工作流逻辑 | YAML、Dify DSL、工作流设计           | 2025年11月22日 | wwwzhouhui | 1.0.0 |
| xiaohuihui-dify-tech-article | 专为 Dify 工作流案例分享设计的公众号文章生成器，遵循小灰灰公众号写作规范，自动生成包含前言、工作流制作、总结的完整 Dify 案例文章 | Markdown、Dify、腾讯云 COS           | 2025年11月22日 | wwwzhouhui | 1.0.0 |
| siliconflow-api-skills  | 硅基流动（SiliconFlow）云服务平台文档技能，提供大语言模型 API 调用、图片生成、向量模型、Chat Completions API、Stream 模式等完整文档和最佳实践 | API、Python、REST、LLM               | 2025年11月19日 | wwwzhouhui | 1.0.0 |
| mp-cover-generator      | 公众号封面生成器，根据主题和标题生成现代风格的公众号封面图，支持描边卡通字体、垂直居中布局，可输出 HTML 和高清图片（PNG/JPG），使用 Playwright 实现完整页面截图 | MCP、HTML/CSS、Node.js、Playwright、即梦 AI | 2025年11月15日 | wwwzhouhui | 3.1.1 |
| excel-report-generator  | 自动化 Excel 报表生成器，支持从 CSV、DataFrame、数据库生成专业 Excel 报表，包含图表、样式、模板填充等高级功能 | Python、pandas、openpyxl、xlsxwriter | 2025年1月12日  | wwwzhouhui | 1.0.0 |

## Skill 功能详解

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

### 📝 XiaoHuiHui Tech Article

**核心功能：**

- ✅ 标准四段式结构（前言→项目介绍→部署实战→总结）
- ✅ 三段式开头（问题引入+解决方案+实战预告）
- ✅ 详细部署步骤（环境→安装→配置→实现→测试）
- ✅ 单段长句总结（300-500字）
- ✅ 口语化技术表达
- ✅ 完整资源附加（GitHub+体验地址+网盘）
- ✅ **新增** 即梦AI自动配图与腾讯云COS上传功能
- ✅ **新增** 图片占位符自动替换为真实URL
- ✅ **新增** 内存直接上传避免本地缓存

**文章结构：**

- **第1章**：前言（三段式，约300字）
- **第2章**：项目介绍（约500字）
- **第3章**：部署实战（约1500-2000字）
- **第4章**：总结（单段300-500字）
- **第5章**：附加资源

**配图系统（v2.1.0新增）：**

- 🤖 自动调用即梦AI生成技术配图
- ☁️ 自动上传至腾讯云COS图床
- 🔗 自动替换文章中的图片占位符
- 📸 支持多种图片类型：工作流截图、效果演示图、代码配置图
- 💾 内存上传，无需本地缓存文件

**配置要求（v2.1.0）：**

1. 配置腾讯云COS环境变量：
   - `SECRET_ID`：腾讯云访问密钥ID
   - `SECRET_KEY`：腾讯云访问密钥Key
   - `COS_BUCKET`：COS存储桶名称
   - `COS_REGION`：COS存储桶所在地域

2. 确保 jimeng-mcp-server 正常运行

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
│   └── github-readme-generator/
└── README.md         # 项目总文档
```

---

## 项目结构

```
skills_collection/
├── github-trending/              # GitHub Trending 追踪技能
│   ├── Skill.md
│   └── fetch_trending.py
├── excel-report-generator/       # Excel 报表生成技能
│   ├── Skill.md
│   └── excel_generator.py
├── xiaohuihui-tech-article/      # 技术文章生成技能
│   ├── Skill.md
│   ├── cos_utils.py
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

### 配置说明

部分技能需要配置环境变量：

```bash
# 腾讯云 COS（xiaohuihui-tech-article 需要）
export SECRET_ID="your-secret-id"
export SECRET_KEY="your-secret-key"
export COS_BUCKET="your-bucket"
export COS_REGION="your-region"

# 即梦 API（jimeng_mcp_skill、mp-cover-generator 需要）
export JIMENG_API_KEY="your-api-key"

# GitHub Token（github-trending 可选）
export GITHUB_TOKEN="your-github-token"

# 企业微信 Webhook（github-trending 可选）
export WEIXIN_WEBHOOK="your-webhook-url"
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
<summary>PPT 生成器生成的文件打不开?</summary>

1. 确认安装了 python-pptx 库：pip install python-pptx
2. 检查 Python 版本是否为 3.7+
3. 确认文件扩展名为 .pptx
4. 验证 JSON 配置文件格式是否正确
5. 使用 PowerPoint 或 WPS 打开文件查看具体错误

</details>

---

## 技术交流群

欢迎加入技术交流群，分享你的 Skills 和使用心得：

   ![image-20260131100545915](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20260131100545915.png)

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

![微信支付](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20250914152855543-17691448865182.png)

---

## 项目统计

### 技能统计

- **总技能数**: 10
- **自动化工具**: 4 (excel-report-generator, ppt-generator-skill, github-trending, github-readme-generator)
- **内容生成**: 3 (xiaohuihui-tech-article, mp-cover-generator, xiaohuihui-dify-tech-article)
- **AI 多模态**: 1 (jimeng_mcp_skill)
- **API 文档**: 1 (siliconflow-api-skills)
- **工作流工具**: 1 (dify-dsl-generator)

### 最新版本动态

- **github-readme-generator**: v1.0.0 (2026-01-23) - 初始版本
- **github-trending**: v1.0.0 (2026-01-22) - 初始版本
- **xiaohuihui-tech-article**: v2.1.0 (2025-12-14) - 新增即梦AI自动配图与腾讯云COS上传
- **jimeng_mcp_skill**: v2.0.0 (2025-12-14) - 升级至 jimeng-4.5 模型，参数系统重构

### 开发语言

- Python: 4
- Markdown: 3
- MCP: 1
- YAML/DSL: 1

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

**文档生成时间**: 2026年1月23日
