# Dify DSL 工作流生成器 v1.0.0

专业的 Dify 工作流 DSL/YML 文件自动生成工具,基于对 86+ 实际工作流案例的深度学习,能够根据用户的业务需求自动生成符合 Dify 规范的完整工作流配置文件。

## 特性

- ✅ **深度学习**: 基于 86+ 真实 Dify 工作流案例
- ✅ **完整生成**: 自动生成可直接导入 Dify 的 YML 文件
- ✅ **多节点支持**: 支持所有 Dify 节点类型
- ✅ **智能连接**: 自动建立节点间的逻辑关系
- ✅ **规范格式**: 严格遵循 Dify 0.3.0 DSL 规范

## 学习来源

本 skill 基于以下仓库的深度学习:
- **仓库**: https://github.com/wwwzhouhui/dify-for-dsl
- **案例数量**: 86+ 个真实工作流
- **覆盖场景**:
  - 音视频处理
  - AI 绘画与图像
  - 商业应用
  - 教育内容
  - 工具类应用
  - 数据可视化
  - MCP 集成

## 快速开始

### 基础使用

在 Claude Code 中直接使用:

```
生成一个 Dify 工作流用于图片 OCR 识别
```

### 详细使用

提供更详细的需求描述:

```
帮我生成一个 Dify 工作流 DSL 文件:
- 功能: 图片 OCR 识别并提取文字
- 输入: 用户上传图片
- 处理步骤:
  1. 接收图片上传
  2. 使用视觉模型识别文字
  3. 格式化输出结果
- 输出: 提取的文字内容
```

## 支持的节点类型

### 核心节点
- **Start**: 开始节点,定义工作流输入
- **LLM**: 大语言模型节点
- **Answer**: 直接回复节点
- **Code**: Python 代码执行节点

### 高级节点
- **HTTP Request**: HTTP API 调用
- **If-Else**: 条件判断分支
- **Tool**: 工具调用(内置/插件)
- **Variable Aggregator**: 变量聚合器
- **Parameter Extractor**: 参数提取器
- **Knowledge Retrieval**: 知识库检索
- **Template Transform**: 模板转换
- **Iteration**: 列表循环
- **Question Classifier**: 问题分类器

### 特殊节点
- **Conversation Variable Assigner**: 对话变量赋值
- **Assigner**: 变量赋值器

## 工作流类型

### 1. Chatflow (advanced-chat)
高级对话模式,支持多轮对话和上下文管理。

**适用场景**:
- 智能客服
- 问答系统
- 对话式应用

### 2. Workflow
标准工作流模式,单次执行流程。

**适用场景**:
- 数据处理
- 文件转换
- 批量操作

### 3. Agent (agent-chat)
AI Agent 模式,支持工具调用和自主决策。

**适用场景**:
- 复杂任务自动化
- 多工具协同
- 智能助手

## 实际应用案例

### 案例1: 英语单词口语练习

**需求**: 图片识别单词 → 生成互动 HTML → 语音练习

**生成的工作流**:
```
Start(图片上传) →
LLM(OCR识别) →
LLM(生成HTML) →
Parameter Extractor(提取代码) →
Tool(保存文件) →
Answer(返回结果)
```

### 案例2: 发票识别与提取

**需求**: 发票图片 → 识别信息 → 生成 Excel

**生成的工作流**:
```
Start(多图片上传) →
Iteration(循环处理) →
  LLM(识别发票) →
  Parameter Extractor(提取字段) →
Code(生成Excel) →
Answer(下载链接)
```

### 案例3: RSS 新闻聚合

**需求**: 平台选择 → 抓取新闻 → 格式化展示

**生成的工作流**:
```
Start(平台选择) →
If-Else(平台判断) →
  Tool(RSS抓取-平台1) →
  Tool(RSS抓取-平台2) →
  ...
Variable Aggregator(聚合结果) →
Code(格式化) →
LLM(生成摘要) →
Answer(展示结果)
```

## 使用技巧

### 1. 需求描述要清晰

**好的描述**:
```
生成一个工作流:
1. 用户上传 PDF 文件
2. 提取文本内容
3. 使用 AI 翻译成英文
4. 生成新的 PDF 并返回下载链接
```

**不好的描述**:
```
做一个翻译的东西
```

### 2. 指定关键参数

如果有特定要求,明确指出:
```
- 使用 GPT-4 模型
- 温度设置为 0.3(更确定性)
- 最大 token 2000
- 使用 markdown 格式输出
```

### 3. 说明预期输出

明确期望的输出格式:
```
- 输出: JSON 格式,包含 {name, age, email}
- 输出: HTML 表格
- 输出: Markdown 列表
```

### 4. 提及需要的插件

如果知道需要特定插件:
```
- 使用 md_exporter 插件保存文件
- 需要集成飞书 API
- 使用数据库插件查询
```

## 文件结构

```
dify-dsl-generator/
├── SKILL.md              # 核心提示词文件(14KB+)
├── README.md             # 本文件
├── examples/             # 示例 DSL 文件
│   ├── simple-ocr.yml
│   ├── text-to-sql.yml
│   └── agent-workflow.yml
└── references/           # 参考文档
    └── dsl-structure.md  # DSL 结构详细说明
```

## 常见问题

### Q: 生成的 DSL 可以直接导入 Dify 吗?

A: 是的,生成的 YML 文件完全符合 Dify 0.3.0+ 版本的规范,可以直接通过 Dify 的"导入 DSL"功能导入使用。

### Q: 支持哪些 Dify 版本?

A: 主要支持 Dify 0.3.0 及以上版本。基于 0.8.0+ 版本的案例学习,向下兼容性良好。

### Q: 如何处理复杂的业务逻辑?

A: 可以详细描述处理步骤,skill 会自动规划合适的节点组合。对于特别复杂的逻辑,可以分步骤生成,然后手动合并。

### Q: 生成的工作流性能如何优化?

A: skill 会根据最佳实践自动优化:
- 合理使用 LLM 温度参数
- 适当的 token 限制
- 避免不必要的节点
- 优化提示词长度

### Q: 可以生成带 MCP 集成的工作流吗?

A: 可以。只需在需求中说明需要 MCP 工具集成,skill 会自动配置相应的 Tool 节点和参数。

### Q: 生成后可以修改吗?

A: 当然可以。生成的 YML 文件可以手动编辑,或者在 Dify UI 中可视化修改。

## 版本历史

### v1.0.0 (2025-11-22)
- ✅ 初始版本发布
- ✅ 基于 86+ 案例深度学习
- ✅ 支持所有主要节点类型
- ✅ 完整的 DSL 生成能力
- ✅ 智能节点连接和布局
- ✅ 规范化的 YAML 输出

## 技术支持

- **Dify 官方文档**: https://docs.dify.ai
- **DSL 案例仓库**: https://github.com/wwwzhouhui/dify-for-dsl
- **Dify GitHub**: https://github.com/langgenius/dify
- **Dify 社区**: https://community.dify.ai

## 贡献

本 skill 基于开源案例学习而来,欢迎贡献更多案例和改进建议。

## 许可

基于 Dify 开源项目学习,遵循相同的 Apache 2.0 许可证。
