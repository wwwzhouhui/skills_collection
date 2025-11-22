# Dify DSL 结构详解

本文档详细说明 Dify 工作流 DSL (YML) 文件的完整结构和字段含义。

## 文件结构概览

```yaml
app:                    # 应用配置
dependencies:           # 插件依赖
kind: app
version: 0.3.0
workflow:              # 工作流配置
  conversation_variables: []
  environment_variables: []
  features: {}
  graph:
    edges: []          # 节点连接
    nodes: []          # 节点定义
```

## App 配置详解

```yaml
app:
  description: '工作流的详细描述'
  icon: '🤖'                    # Emoji 图标
  icon_background: '#FFEAD5'    # 图标背景色(16进制)
  mode: advanced-chat           # 工作流模式
  name: '工作流名称'
  use_icon_as_answer_icon: false  # 是否使用图标作为回答图标
```

### 工作流模式 (mode)

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `advanced-chat` | 高级对话模式(Chatflow) | 多轮对话、智能客服 |
| `workflow` | 标准工作流模式 | 单次任务、数据处理 |
| `agent-chat` | AI Agent 模式 | 工具调用、复杂任务 |

## Dependencies 依赖配置

```yaml
dependencies:
- current_identifier: null
  type: marketplace              # 类型: marketplace(市场插件)
  value:
    marketplace_plugin_unique_identifier: 插件完整标识符
```

### 常用插件标识符

```yaml
# OpenAI 兼容接口
langgenius/openai_api_compatible:0.0.16@哈希值

# Markdown 导出器
bowenliang123/md_exporter:1.2.0@哈希值

# 数据库插件
plugin_author/database_plugin:版本@哈希值
```

## Workflow 配置详解

### Conversation Variables (对话变量)

```yaml
conversation_variables:
- id: 变量ID
  name: 变量名称
  value_type: string              # 类型: string, number, object, array
  description: 变量描述
```

### Environment Variables (环境变量)

```yaml
environment_variables:
- id: 环境变量ID
  name: 环境变量名
  value: 默认值
  description: 变量说明
```

### Features (功能配置)

#### 文件上传

```yaml
features:
  file_upload:
    enabled: true
    allowed_file_extensions:
    - .jpg
    - .png
    - .pdf
    allowed_file_types:
    - image
    - document
    allowed_file_upload_methods:
    - local_file
    - remote_url
    fileUploadConfig:
      audio_file_size_limit: 500      # MB
      batch_count_limit: 5            # 批量数量
      file_size_limit: 15             # MB
      image_file_size_limit: 100      # MB
      video_file_size_limit: 500      # MB
      workflow_file_upload_limit: 10  # 工作流文件限制
    image:
      enabled: true
      number_limits: 3                # 图片数量限制
      transfer_methods:
      - local_file
      - remote_url
    number_limits: 3                  # 总文件数量限制
```

#### 语音功能

```yaml
features:
  speech_to_text:
    enabled: true
    language: zh-CN                   # 语言代码
  text_to_speech:
    enabled: true
    language: zh-CN
    voice: alloy                      # 语音ID
```

#### 其他功能

```yaml
features:
  opening_statement: '欢迎消息'         # 开场白
  retriever_resource:
    enabled: true                     # 启用知识库检索
  sensitive_word_avoidance:
    enabled: false                    # 敏感词过滤
  suggested_questions:                # 建议问题
  - 问题1
  - 问题2
  suggested_questions_after_answer:
    enabled: false                    # 回答后建议问题
```

## Graph 图结构

### Nodes (节点)

每个节点的通用结构:

```yaml
nodes:
- data:
    # 节点数据
  id: '节点唯一ID'
  position:
    x: 100
    y: 300
  positionAbsolute:
    x: 100
    y: 300
  selected: false
  sourcePosition: right
  targetPosition: left
  type: custom
  width: 244
  height: 90
```

### Edges (连接)

```yaml
edges:
- data:
    isInIteration: false          # 是否在迭代中
    isInLoop: false               # 是否在循环中
    sourceType: start             # 源节点类型
    targetType: llm               # 目标节点类型
  id: 唯一连接ID                  # 格式: 源ID-source-目标ID-target
  source: '源节点ID'
  sourceHandle: source            # 固定值
  target: '目标节点ID'
  targetHandle: target            # 固定值
  type: custom                    # 固定值
  zIndex: 0                       # 层级
```

## 节点类型详细配置

### Start 节点

```yaml
data:
  desc: ''
  title: 开始
  type: start
  variables:
  - label: 变量标签
    max_length: 1000
    options: []                   # 下拉选项(type为select时)
    required: true
    type: paragraph               # 变量类型
    variable: 变量名
```

**变量类型完整列表**:
- `paragraph`: 多行文本
- `text-input`: 单行文本
- `select`: 下拉选择
- `number`: 数字
- `file`: 文件上传
- `files`: 多文件上传

### LLM 节点

```yaml
data:
  context:
    enabled: false                # 是否启用上下文
    variable_selector: []
  model:
    completion_params:
      temperature: 0.7
      max_tokens: 2000
      top_p: 0.9
      frequency_penalty: 0
      presence_penalty: 0
    mode: chat                    # chat 或 completion
    name: gpt-4
    provider: openai
  prompt_template:
  - id: 提示词块ID
    role: system
    text: 系统提示词
  - id: 提示词块ID
    role: user
    text: 用户提示词 {{#变量#}}
  title: LLM节点名称
  type: llm
  variables: []                   # 外部变量
  vision:
    enabled: false                # 是否启用视觉
    configs:
      detail: high                # low, high, auto
      variable_selector:
      - 节点ID
      - 变量名
```

### Code 节点

```yaml
data:
  code: |
    def main(arg1: str) -> dict:
        return {"result": "value"}
  code_language: python3
  desc: ''
  outputs:
    变量名:
      type: string                # string, number, object, array[...]
      children: null
  title: 代码执行
  type: code
  variables:
  - value_selector:
    - 源节点ID
    - 源变量名
    variable: 目标变量名
```

### HTTP Request 节点

```yaml
data:
  authorization:
    config:
      api_key: ''
      header: ''
    type: no-auth                 # no-auth, api-key, bearer
  body:
    data: '{"key": "value"}'
    type: json                    # none, form-data, x-www-form-urlencoded, json, raw-text
  headers: 'Content-Type: application/json'
  method: post                    # get, post, put, patch, delete, head
  timeout:
    max_connect_timeout: 0
    max_read_timeout: 0
    max_write_timeout: 0
  title: HTTP请求
  type: http-request
  url: https://api.example.com/endpoint
  variables:
  - value_selector:
    - 节点ID
    - 变量名
    variable: 变量名
```

### If-Else 节点

```yaml
data:
  cases:
  - case_id: case1
    conditions:
    - comparison_operator: contains
      id: 条件ID
      value: 期望值
      variable_selector:
      - 节点ID
      - 变量名
    id: case1
    logical_operator: and         # and, or
  logical_operator: or            # 多个case之间: and, or
  title: 条件判断
  type: if-else
```

**比较运算符**:
- `is`: 等于
- `is not`: 不等于
- `contains`: 包含
- `not contains`: 不包含
- `start with`: 开头是
- `end with`: 结尾是
- `is empty`: 为空
- `is not empty`: 不为空
- `>`: 大于
- `<`: 小于
- `>=`: 大于等于
- `<=`: 小于等于

### Tool 节点

```yaml
data:
  provider_id: builtin
  provider_name: 提供者名称
  provider_type: builtin          # builtin, api, plugin
  title: 工具调用
  tool_configurations: {}
  tool_label: 工具标签
  tool_name: 工具名称
  tool_parameters:
    参数名:
      type: mixed                 # mixed, string, number, boolean
      value: 参数值或变量引用
  type: tool
```

### Parameter Extractor 节点

```yaml
data:
  instruction: 提取指令说明
  is_array: false                 # 是否提取数组
  model:
    completion_params: {}
    mode: chat
    name: gpt-4
    provider: openai
  parameters:
  - description: 参数描述
    name: 参数名
    required: true
    type: string                  # string, number, boolean, object, array
  query:
  - role: user
    text: '{{#输入变量#}}'
  reasoning_mode: prompt          # prompt, function_call
  title: 参数提取
  type: parameter-extractor
```

### Variable Aggregator 节点

```yaml
data:
  advanced_settings: null
  desc: ''
  groups:
  - group_name: 分组名称
    output_type: string           # string, number, object, array[string]
    variables:
    - value_selector:
      - 节点ID
      - 变量名
      variable: 输出变量名
  title: 变量聚合器
  type: variable-aggregator
```

### Answer 节点

```yaml
data:
  answer: |
    {{#节点ID.变量#}}

    可以包含多个变量引用和静态文本
  title: 直接回复
  type: answer
  variables: []
```

### Iteration 节点

```yaml
data:
  desc: ''
  iterator_selector:
  - 数组变量所在节点ID
  - 数组变量名
  output_selector:
  - 迭代内最后节点ID
  - 输出变量名
  output_type: string             # 迭代结果的输出类型
  startNodeType: code             # 迭代开始的节点类型
  start_node_id: 迭代起始节点ID
  title: 列表循环
  type: iteration
```

## 变量引用规范

### 基本格式

```
{{#节点ID.变量名#}}
```

### 系统变量

```
{{#sys.query#}}              # 用户输入
{{#sys.files#}}              # 用户上传的文件
{{#sys.conversation_id#}}    # 对话ID
{{#sys.user_id#}}            # 用户ID
```

### 节点输出变量

```
{{#1747991921941.text#}}           # LLM 节点的文本输出
{{#1748043739511.files#}}          # Tool 节点的文件输出
{{#1748043544283.param_name#}}    # Parameter Extractor 的提取结果
{{#code_node.result#}}             # Code 节点的输出
```

### 数组访问

```
{{#节点ID.数组变量.0#}}          # 访问数组第一个元素
{{#节点ID.对象.属性#}}           # 访问对象属性
```

## 坐标系统

### 推荐布局

**水平流程**:
```
节点1(100,300) → 节点2(400,300) → 节点3(700,300) → 节点4(1000,300)
```

**垂直分支**:
```
              → 分支1(700,150)
节点(400,300) →
              → 分支2(700,450)
```

### 节点尺寸

| 节点类型 | 推荐宽度 | 推荐高度 |
|----------|---------|---------|
| Start | 244 | 90-150 |
| LLM | 244 | 90 |
| Code | 244 | 90 |
| Tool | 244 | 90 |
| If-Else | 244 | 120 |
| Answer | 244 | 90-143 |

## 最佳实践

### 1. ID 生成规则

使用时间戳确保唯一性:
```javascript
const id = Date.now().toString()  // 例: "1747991921941"
```

### 2. 节点命名

- 使用中文描述性名称
- 避免过长(建议10字以内)
- 清晰表达节点功能

### 3. 提示词设计

- 系统提示词: 定义角色和规则
- 用户提示词: 包含输入变量
- 使用明确的输出格式要求

### 4. 错误处理

- 使用 If-Else 节点验证输出
- Code 节点包含 try-catch
- 提供默认值或错误提示

### 5. 性能优化

- 合理设置 max_tokens
- 避免不必要的节点
- 并行处理可以使用 Variable Aggregator

## 版本兼容性

| Dify 版本 | DSL 版本 | 兼容性 |
|-----------|----------|--------|
| 0.8.0+ | 0.3.0 | ✅ 完全支持 |
| 0.6.0-0.7.x | 0.2.0 | ⚠️ 部分兼容 |
| < 0.6.0 | 0.1.0 | ❌ 不兼容 |

## 参考资料

- Dify 官方文档: https://docs.dify.ai
- DSL Schema: https://github.com/langgenius/dify/tree/main/api/core/workflow
- 示例仓库: https://github.com/wwwzhouhui/dify-for-dsl
