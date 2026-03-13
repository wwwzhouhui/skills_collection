# Obsidian CLI 查询模式

## 核心命令

- 文本搜索：`obsidian search query="关键词"`
- 带上下文搜索：`obsidian search:context query="关键词"`
- 读取文件：`obsidian read file="笔记名"`
- 列文件：`obsidian files folder="目录"`
- 查任务：`obsidian tasks todo`
- 查标签：`obsidian tags counts`
- 查某标签：`obsidian tag name="#标签" verbose`
- 查属性：`obsidian properties counts`
- 查反链：`obsidian backlinks file="笔记名" counts`
- 查出链：`obsidian links file="笔记名"`
- 查大纲：`obsidian outline file="笔记名" format=md`

## 搜索类参数

- `query=<text>`：搜索词，必填
- `path=<folder>`：限制目录范围
- `limit=<n>`：限制返回文件数
- `format=text|json`：需要稳定总结时优先 `json`
- `case`：大小写敏感
- `total`：仅返回数量或附带数量

## 文件定位规则

- 已知笔记标题但路径不确定：用 `file=`
- 已知精确路径：用 `path=`
- 想先枚举目录候选：用 `files folder=`
- 搜到文件后需要正文：再用 `read`

## 常见自然语言映射

### 1. 找某主题的笔记

用户说法：

- “找一下会议纪要”
- “搜一下 AI 编程相关笔记”
- “有哪些笔记提到了信用管理”

优先命令：

```bash
obsidian search query="会议纪要" limit=10
obsidian search query="AI 编程" path="计算机技术" limit=10
obsidian search query="信用管理" format=json limit=20
```

### 2. 看关键词出现的上下文

用户说法：

- “看看哪些地方提到了 obsidian cli”
- “把包含工作流的原句找出来”

优先命令：

```bash
obsidian search:context query="obsidian cli" limit=10
obsidian search:context query="工作流" path="work" format=json limit=20
```

### 3. 找待办事项

用户说法：

- “看看我有哪些未完成任务”
- “今天日报里还有什么待办”

优先命令：

```bash
obsidian tasks todo
obsidian tasks daily todo
obsidian tasks path="daily_reports/2026-03-07" todo verbose
```

### 4. 看标签或分类分布

用户说法：

- “我的知识库里常用标签有哪些”
- “#claude-code 都在哪些文件里”

优先命令：

```bash
obsidian tags counts format=json
obsidian tag name="#claude-code" verbose
```

### 5. 看某篇笔记的关系

用户说法：

- “谁引用了这篇笔记”
- “这篇文档都链接到了哪里”

优先命令：

```bash
obsidian backlinks file="Obsidian CLI 命令行接口" counts format=json
obsidian links file="Obsidian CLI 命令行接口"
```

### 6. 看某目录里有什么

用户说法：

- “列出 work 目录下的文档”
- “看看最近日报目录里有哪些 md 文件”

优先命令：

```bash
obsidian files folder="work"
obsidian files folder="daily_reports" ext=md total
```

### 7. 读取并总结具体笔记

推荐两步法：

```bash
obsidian search query="Obsidian CLI" limit=5
obsidian read file="Obsidian CLI 命令行接口"
```

必要时补充：

```bash
obsidian outline file="Obsidian CLI 命令行接口" format=md
```

## 组合查询策略

### 先搜再读

适用于“帮我总结某个主题”。

```bash
obsidian search query="主题词" format=json limit=5
obsidian read file="候选笔记A"
obsidian read file="候选笔记B"
```

### 先列再筛

适用于“某目录有哪些笔记”。

```bash
obsidian files folder="目标目录"
```

如果结果仍然太多，再增加目录、扩展名或后续读取步骤。

### 先看关系再读正文

适用于“这篇笔记和哪些内容相关”。

```bash
obsidian backlinks file="目标笔记" format=json
obsidian links file="目标笔记"
obsidian read file="目标笔记"
```

## 注意事项

- Obsidian CLI 需要桌面版 Obsidian 正在运行；若未运行，首个命令可能会自动启动。
- 在 Windows 上要确保可执行的是 `obsidian` 对应的 `.com` 终端重定向器。
- 搜索命令默认只返回路径，不返回正文；要看命中内容用 `search:context`。
- 如果 `search:context` 执行成功但没有任何输出，不要直接判定无结果；先用相同关键词执行 `obsidian search`，确认是否有命中文件，再改用 `read` 读取候选文件。
- `search` 的 `path=` 接收文件夹路径，不是文件路径。
- 若结果为空，不要臆测；明确说明并尝试更宽松关键词。

## 真实演示示例

### 示例 1：主题搜索

用户输入：

```text
帮我找一下和 obsidian 相关的笔记
```

建议命令：

```bash
obsidian search query="obsidian" limit=5
```

回答风格：

- 先说找到多少篇
- 再列出最相关的文件路径
- 如果用户显然是想“深入看内容”，追加建议：继续读取其中 1-2 篇并总结

### 示例 2：反向链接查询

用户输入：

```text
obsidian api接口 这篇笔记有哪些反向链接？
```

建议命令：

```bash
obsidian backlinks file="obsidian api接口" counts format=json
```

回答风格：

- 先说共有几个反链来源
- 再按文件列出引用来源和次数
- 最后补一句这些反链说明它在知识库里扮演的角色

### 示例 3：标签统计

用户输入：

```text
我的知识库里最常用的标签有哪些？
```

建议命令：

```bash
obsidian tags counts format=json
```

回答风格：

- 不要把全部标签原样贴给用户
- 只提炼前 5-10 个高频标签
- 用 1 句话总结这些高频标签反映出的知识库重心
