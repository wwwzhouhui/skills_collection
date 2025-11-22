# 小灰灰 Dify 案例文章生成器 v1.0.0

专为 Dify 工作流案例分享设计的公众号文章生成器,遵循小灰灰公众号写作规范,自动生成包含前言、工作流制作、总结的完整 Dify 案例文章,配有详细的节点配置、插件安装步骤、代码示例,并支持自动生成图片上传到腾讯云COS图床。

## 新特性

- ✅ **Dify 专属结构**: 针对 Dify 工作流案例的特殊文章结构
- ✅ **工作流节点详解**: 详细的开始、LLM、Agent、代码执行等节点配置说明
- ✅ **插件安装指南**: 完整的插件搜索、安装、授权流程
- ✅ **MCP工具集成**: MCP server 部署和配置说明
- ✅ **魔搭社区推荐**: 优先使用魔搭社区提供的免费模型
- ✅ **效果展示优先**: 先展示工作流效果,再介绍制作过程

## 快速开始

### 1. 安装依赖

```bash
pip install -r scripts/requirements.txt
```

### 2. 配置 COS

复制 `.env.example` 为 `.env` 并填入你的腾讯云 COS 配置:

```bash
cp .env.example .env
```

编辑 `.env` 文件:
```bash
COS_SECRET_ID=your-secret-id
COS_SECRET_KEY=your-secret-key
COS_BUCKET=your-bucket-name
COS_REGION=your-region
```

**重要**: `.env` 文件包含敏感信息,请勿提交到版本控制系统。

### 3. 使用 Skill

在 Claude Code 中使用:

```
使用小灰灰公众号风格写一篇 Dify [工作流功能] 的案例分享文章
```

示例:
```
用小灰灰公众号风格写一篇 Dify 文生图工作流的案例分享
```

### 4. 上传图片

```bash
# 基础上传
python scripts/upload_to_cos.py /path/to/image.png

# 自定义文件名
python scripts/upload_to_cos.py /path/to/image.png --name workflow-20251122.png
```

## 与通用技术文章的区别

### xiaohuihui-tech-article (通用技术文章)
- 适用于: 通用项目部署、技术教程
- 结构: 前言 → 项目介绍 → 部署实战 → 总结
- 重点: 环境准备、依赖安装、Docker部署等
- 适用场景: DeepSeek、Docker、各类开源项目部署

### xiaohuihui-dify-tech-article (Dify 案例文章)
- 适用于: Dify 工作流案例分享
- 结构: 前言 → 工作流制作 → 总结
- 重点: 工作流节点配置、插件安装、MCP集成
- 适用场景: Dify 工作流案例、插件使用、MCP 工具集成

## 配置说明

### .env 文件

本项目使用 `.env` 文件管理敏感的 COS 配置信息。

**文件结构**:
- `.env.example` - 配置模板(可安全提交)
- `.env` - 实际配置(请勿提交,已在 .gitignore 中)

**安全提示**:
- ✅ `.env.example` 可以提交到 Git
- ❌ `.env` 绝不要提交到 Git
- ✅ `.gitignore` 已默认排除 `.env`
- ⚠️ 不要在代码中硬编码密钥

## Dify 文章特色

### 核心要素

1. **工作流节点详解**
   - 开始节点配置
   - LLM 模型选择(优先魔搭社区)
   - Agent 策略配置
   - 代码执行节点
   - HTTP 请求节点

2. **插件生态**
   - 插件市场搜索
   - 插件安装步骤
   - 插件授权配置
   - 常用插件推荐

3. **MCP 工具集成**
   - MCP server 部署
   - streamable-http 配置
   - MCP 工具使用

4. **效果展示**
   - 工作流全局图
   - 运行效果展示
   - 对比传统方案

### 写作风格

- **口语化**: "话不多说"、"手把手搭建"、"好很多"
- **实战导向**: 详细的配置步骤和截图
- **效果优先**: 先展示效果,再介绍制作
- **魔搭推荐**: 优先使用魔搭社区免费模型

## 文档

- `SKILL.md`: 完整的 skill 说明和写作规范
- `references/dify-workflow-guide.md`: Dify 工作流详细指南(待创建)
- `scripts/upload_to_cos.py`: COS 上传工具

## 示例文章

参考 `xiaohuihui-dify-tech-article2/` 目录下的示例文章:
- `37-dify案例分享-5 步解锁免费即梦文生视频工作流，轻松制作大片.md`
- `62-dify案例分享-Dify+RSS 聚合 8 大平台实时热点，新闻获取效率飙升 300%.md`
- `79-dify案例分享-5分钟搭建智能思维导图系统！Dify + MCP工具实战教程.md`

## 版本历史

### v1.0.0 (2025-11-22)
- ✅ 初始版本
- ✅ Dify 专属结构
- ✅ 工作流节点详解
- ✅ 插件安装指南
- ✅ MCP工具集成
- ✅ 口语化风格
- ✅ 质量标准

## 常见问题

### Q: 什么时候用 xiaohuihui-tech-article,什么时候用 xiaohuihui-dify-tech-article?

A:
- 如果是部署开源项目(如 DeepSeek、Docker 等),使用 `xiaohuihui-tech-article`
- 如果是 Dify 工作流案例分享,使用 `xiaohuihui-dify-tech-article`

### Q: Dify 文章必须包含哪些内容?

A:
1. 工作流全局图(必须)
2. 核心节点配置截图(至少5个)
3. 效果展示(必须)
4. 如有插件,必须包含安装和授权步骤
5. 优先推荐魔搭社区免费模型

### Q: 如何获取工作流截图?

A: 需要在 Dify 平台实际搭建工作流后截图,或使用测试环境截图。

## 技术支持

- Dify 官网: https://dify.ai
- 魔搭社区: https://modelscope.cn
- 小灰灰公众号: 搜索"wwzhouhui"
