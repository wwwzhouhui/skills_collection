---
name: github-readme-generator
description: Generate professional GitHub project README.md with standard structure including project intro, features, installation, usage, documentation, FAQ, contact info, donation, statistics, roadmap, and license. Auto-detects project type and tech stack.
version: 1.0.0
author: wwwzhouhui
---

# GitHub README Generator

专业的 GitHub 项目 README.md 生成器，自动生成符合开源社区规范的文档结构。

## 功能概述

这个 Skill 可以帮助你：
- 📝 自动生成标准的 GitHub README.md 文档
- 🎯 根据项目类型自动调整文档结构
- 📊 生成项目统计和路线图
- 🔗 自动生成 Star History 和 Badge
- 📧 包含作者联系和打赏信息
- ❓ 生成常见问题 FAQ
- 📚 支持中英文双语

## 核心特性

### 标准文档结构
```markdown
# 项目标题
项目简介/副标题

## 项目介绍
- 项目概述
- 核心功能
- 技术栈

## 功能清单
| 功能名称 | 说明 | 状态 |
|---------|------|------|

## 安装说明
### 环境要求
### 安装步骤

## 使用说明
### 快速开始
### 配置说明
### 使用示例

## 项目结构
```

## 技术栈
| 技术 | 版本 | 用途 |

## 文档地址
- 飞书文档
- 在线文档

## 开发指南
### 本地开发
### 构建部署
### 贡献指南

## 常见问题
<details>
<summary>问题</summary>
回答
</details>

## 技术交流群
欢迎加入技术交流群，分享你的 Skills 和使用心得：

![微信图片_20260321212115_179_292](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20260321212115_179_292.jpg)

## 作者联系
- **微信**: laohaibao2025
- **邮箱**: 75271002@qq.com

![微信二维码](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Screenshot_20260123_095617_com.tencent.mm.jpg)

## 打赏
如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

**微信支付**

![微信支付](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

## 项目统计
### 代码统计
### 版本历史

## 路线图
### 计划功能
### 优化项

## License
SPDX-License-Identifier: MIT

## Star History
[Star History 图片]
```

## 使用方法

### 方式一：交互式生成

直接提出需求，系统会引导你提供必要信息：

```
请帮我的项目生成一个 README.md

需要提供的信息：
1. 项目名称
2. 项目简介
3. 技术栈
4. 核心功能
5. 安装步骤
6. 使用示例
7. 作者信息
8. 是否需要打赏信息
```

### 方式二：基于现有项目自动生成

```
请基于当前项目自动生成 README.md
```

系统会自动分析：
- 项目结构（目录、文件）
- 技术栈（package.json, go.mod, pom.xml 等）
- 构建脚本（Makefile, build.sh）
- 配置文件
- 现有文档

### 方式三：使用模板快速生成

```
请使用 [模板名称] 生成 README
```

可用模板：
- `basic` - 基础模板
- `full` - 完整模板（包含所有章节）
- `minimal` - 极简模板
- `library` - 库/SDK 专用模板
- `webapp` - Web 应用模板
- `cli` - CLI 工具模板
- `api` - API 服务模板

## 文档结构说明

### 必选章节

| 章节 | 说明 | 优先级 |
|------|------|--------|
| 项目标题 | 清晰的项目名称和副标题 | P0 |
| 项目简介 | 一句话描述项目核心价值 | P0 |
| 功能清单 | 表格形式列出主要功能 | P0 |
| 安装说明 | 环境要求和安装步骤 | P0 |
| 使用说明 | 快速开始和基本用法 | P0 |
| License | 开源协议声明 | P0 |

### 推荐章节

| 章节 | 说明 | 适用场景 |
|------|------|----------|
| 项目结构 | 目录树展示 | 中大型项目 |
| 技术栈 | 技术选型说明 | 所有项目 |
| 开发指南 | 本地开发、构建、贡献 | 开源项目 |
| 常见问题 | FAQ | 用户向项目 |
| 文档地址 | 外部文档链接 | 复杂项目 |

### 可选章节

| 章节 | 说明 | 适用场景 |
|------|------|----------|
| 作者联系 | 微信、邮箱 | 个人项目 |
| 技术交流群 | 群二维码 | 社区项目 |
| 打赏 | 收款码 | 个人开源 |
| 项目统计 | 代码量、版本历史 | 成熟项目 |
| 路线图 | 未来计划 | 活跃项目 |
| Star History | Star 趋势图 | GitHub 项目 |

## 内容规范

### 标题规范

```
# [项目名称]

[一句话描述项目核心价值]

[可选：项目图标/Logo]

> [可选：项目标语/Slogan]
```

### 功能清单表格规范

```markdown
## 功能清单

| 功能名称 | 功能说明 | 技术栈 | 更新时间 | 版本 |
|---------|---------|--------|----------|------|
| 功能1 | 说明 | Go | 2025-01-23 | v1.0.0 |
| 功能2 | 说明 | Vue | 2025-01-23 | v1.0.0 |
```

### 安装说明规范

```markdown
## 安装说明

### 环境要求

- Node.js 16+
- Python 3.8+
- Go 1.19+

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/user/repo.git

# 安装依赖
npm install

# 配置
cp .env.example .env

# 启动
npm run dev
```
```

### 常见问题规范

```markdown
## 常见问题

<details>
<summary>安装失败怎么办？</summary>

1. 检查网络连接
2. 尝试使用国内镜像
3. 清理缓存后重新安装

</details>

<details>
<summary>如何配置 xxx？</summary>

详细配置说明...

</details>
```

## 项目类型适配

### Web 应用项目

特有章节：
- 在线演示地址
- 技术架构图
- API 文档链接
- 部署说明

### 库/SDK 项目

特有章节：
- 快速引入（npm install、go get 等）
- API 文档
- 示例代码
- 更新日志

### CLI 工具项目

特有章节：
- 安装方式（Homebrew、Cargo、npm 等）
- 命令行参数
- 使用示例（命令行输出）
- 配置文件说明

### API 服务项目

特有章节：
- API 端点列表
- 认证方式
- 请求/响应示例
- SDK 链接

## 高级功能

### 自动识别项目信息

系统能自动识别：
- 项目类型（Web/CLI/Library/API）
- 主要编程语言
- 构建工具
- 包管理器
- 测试框架
- 代码规范工具

### 生成 Badge

自动生成项目 Badge：
```markdown
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-v1.0.0-green.svg)
![Stars](https://img.shields.io/github/stars/user/repo.svg)
```

### 生成 Star History

```markdown
## Star History

如果觉得项目不错，欢迎点个 Star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=user/repo&type=Date)]
```

## 输出示例

### 基础模板输出

```markdown
# My Project

一个简洁的项目描述

## 功能清单

| 功能 | 说明 |
|------|------|
| 功能A | xxx |
| 功能B | xxx |

## 安装

\`\`\`bash
npm install
\`\`\`

## 使用

\`\`\`javascript
import { MyProject } from 'my-project'

const app = new MyProject()
app.run()
\`\`\`

## License

MIT
```

### 完整模板输出

包含所有推荐和可选章节的完整文档。

## 模板文件

### templates/basic.md
基础项目模板，包含核心章节

### templates/full.md
完整项目模板，包含所有章节

### templates/library.md
库/SDK 专用模板

### templates/webapp.md
Web 应用专用模板

### templates/cli.md
CLI 工具专用模板

### templates/api.md
API 服务专用模板

## 示例项目

查看 `examples/` 目录获取不同类型项目的 README 示例：
- `examples/basic-readme.md` - 基础示例
- `examples/full-readme.md` - 完整示例
- `examples/library-readme.md` - 库示例
- `examples/webapp-readme.md` - Web 应用示例

## 最佳实践

### README 撰写原则

1. **简洁优先**: 第一屏展示核心信息
2. **图文并茂**: 适当使用截图和架构图
3. **代码高亮**: 所有代码块标注语言
4. **版本信息**: 明确最低版本要求
5. **更新及时**: 随项目更新同步维护

### 图片规范

- 使用图床或 GitHub 仓库存储
- 图片大小 < 500KB
- 推荐 PNG/JPG 格式
- 添加 alt 文本

### 链接规范

- 使用相对路径链接内部文档
- 使用绝对路径链接外部资源
- 重要链接添加 Badge

## 故障排查

### 常见问题

**Q: 生成的 README 中文乱码**
A: 确保文件使用 UTF-8 编码保存

**Q: 表格显示不正常**
A: 检查表格对齐，确保每行列数一致

**Q: 图片无法显示**
A: 确认图片 URL 可访问，使用 HTTPS

**Q: 目录链接跳转失败**
A: 确保锚点名称与标题一致，空格替换为 `-`

## 版本历史

- v1.0.0 (2025-01-23) - 初始版本，支持基础模板生成
