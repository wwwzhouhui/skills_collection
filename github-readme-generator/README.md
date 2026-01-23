# GitHub README Generator Skill

专业的 GitHub 项目 README.md 生成器 Skill，帮助快速生成符合开源社区规范的文档。

## 安装

将本 Skill 文件夹复制到你的 Claude Code Skills 目录：

```bash
# Linux/Mac
cp -r github-readme-generator ~/.claude/skills/

# Windows 手动复制
C:\Users\xxx\.claude\skills\github-readme-generator
```

## 使用说明

### 方式一：交互式生成

直接提出需求，系统会引导你提供必要信息：

```
请帮我的项目生成一个 README.md
```

系统会询问：
1. 项目名称
2. 项目简介
3. 技术栈
4. 核心功能
5. 安装步骤
6. 作者信息
7. 是否需要打赏信息

### 方式二：基于现有项目自动生成

```
请基于当前项目自动生成 README.md
```

系统会自动分析项目结构和配置文件。

### 方式三：使用模板快速生成

```
请使用 full 模板生成 README
```

可用模板：
- `basic` - 基础模板
- `full` - 完整模板（包含所有章节）
- `minimal` - 极简模板
- `library` - 库/SDK 专用模板
- `webapp` - Web 应用模板
- `cli` - CLI 工具模板
- `api` - API 服务模板

## 目录结构

```
github-readme-generator/
├── SKILL.md              # Skill 主文件
├── templates/            # 模板文件
│   ├── basic.md         # 基础模板
│   ├── full.md          # 完整模板
│   ├── library.md       # 库/SDK 模板
│   ├── webapp.md        # Web 应用模板
│   ├── cli.md           # CLI 工具模板
│   └── api.md           # API 服务模板
└── examples/            # 示例文件
    ├── basic-readme.md  # 基础示例
    ├── library-readme.md # 库示例
    └── cli-readme.md    # CLI 示例
```

## 模板说明

### basic.md
最基础的 README 模板，包含核心章节：
- 项目介绍
- 功能清单
- 技术栈
- 安装说明
- 使用说明
- 常见问题
- License

### full.md
完整的 README 模板，包含所有推荐和可选章节：
- 所有 basic 内容
- 功能详解
- 项目结构
- 文档地址
- 开发指南
- 技术交流群
- 作者联系
- 打赏
- 项目统计
- 路线图
- Star History

### library.md
库/SDK 专用模板：
- 快速引入
- API 文档
- 示例代码
- TypeScript 支持
- 浏览器支持
- 更新日志

### webapp.md
Web 应用专用模板：
- 在线体验地址
- 前后端技术栈
- 本地运行
- 部署说明
- 开发指南

### cli.md
CLI 工具专用模板：
- 多种安装方式
- 命令列表
- 配置文件
- 选项说明

### api.md
API 服务专用模板：
- API 端点列表
- 认证说明
- 使用示例
- 错误码
- SDK
- Webhook

## 标准文档结构

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

## 示例

### 示例 1：生成基础 README

```
请使用 basic 模板为我的 Go 项目生成 README

项目信息：
- 名称：go-api-starter
- 简介：一个简洁的 Go API 项目脚手架
- 技术栈：Go 1.19, Gin, GORM, MySQL
- 功能：用户认证、CRUD 操作、中间件
```

### 示例 2：生成完整 README

```
请使用 full 模板为我的 Vue 项目生成 README

项目信息：
- 名称：vue-admin
- 简介：一个现代化的 Vue 后台管理系统
- 技术栈：Vue 3, Vite, Element Plus, Pinia
- 功能：权限管理、动态路由、图表统计
- 作者：张三
- 微信：zhangsan2025
- 邮箱：zhangsan@example.com
```

### 示例 3：生成库 README

```
请使用 library 模板为我的 npm 包生成 README

项目信息：
- 名称：use-utils
- 简介：一个轻量级的 JavaScript 工具库
- 主要 API：trim, isEmpty, formatDate, debounce
- 支持 TypeScript
```

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

## 项目类型适配

Skill 会根据项目类型自动调整文档结构：

- **Web 应用**: 包含演示地址、部署说明
- **库/SDK**: 包含 API 文档、快速引入
- **CLI 工具**: 包含命令列表、多种安装方式
- **API 服务**: 包含端点列表、认证说明

## 版本历史

- v1.0.0 (2025-01-23) - 初始版本
  - 支持 6 种项目模板
  - 支持交互式和自动生成
  - 包含完整示例和文档

## License

MIT License
