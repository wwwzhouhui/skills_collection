---
name: obsidian-search
description: 根据用户的自然语言检索需求，生成合适的 Obsidian CLI 查询命令，执行查询，并将结果总结返回。用于用户想在 Obsidian 仓库中搜索笔记、查找上下文、筛选任务、标签、属性、反链、文件列表或结构化查询时，例如“帮我找最近的会议记录”“搜一下包含某关键词的笔记”“看看某篇笔记有哪些反向链接”。
---

# Obsidian Search

使用 Obsidian CLI 把自然语言需求转换为可执行查询，再基于输出给出简洁结论。优先复用 `obsidian search`、`search:context`、`tasks`、`tags`、`properties`、`backlinks`、`files`、`outline` 等现成命令，而不是手写文件遍历逻辑。

## 工作流

按以下顺序执行：

1. 判断用户真正想要的结果类型：文件列表、命中上下文、任务、标签、属性、链接关系、某篇笔记内容，还是需要组合查询。
2. 读取 [references/cli-query-patterns.md](references/cli-query-patterns.md)，选择最贴切的命令模式。
3. 组装命令时优先使用：
   - `query=` 传入用户关键词或搜索表达式
   - `path=` 缩小目录范围
   - `file=` 用文件名解析目标笔记
   - `format=json` 在需要稳定总结时优先使用
   - `limit=` 控制结果规模，避免输出过长
4. 使用 Bash 执行 Obsidian CLI 命令。
5. 如果 `search:context` 执行成功但没有返回内容，不要立刻假设“无结果”；先改用同关键词的 `obsidian search` 验证是否存在匹配文件，再决定是否补充 `read`、`outline` 等后续命令。
6. 阅读结果并直接回答用户问题，不原样倾倒大段终端输出。
7. 如果首轮结果过宽或歧义明显，基于结果再执行一轮更具体的查询。

## 查询决策

先匹配下列场景：

- 用户要“找包含某词的笔记” -> `obsidian search`
- 用户要“看匹配词出现在哪些行/上下文” -> `obsidian search:context`
- 用户要“找待办/已完成事项” -> `obsidian tasks`
- 用户要“看标签、某标签用了多少次” -> `obsidian tags` 或 `obsidian tag`
- 用户要“看属性分布或某文件属性” -> `obsidian properties`
- 用户要“看谁链接到这篇笔记” -> `obsidian backlinks`
- 用户要“看这篇笔记链接到了谁” -> `obsidian links`
- 用户要“列出某目录下文件” -> `obsidian files folder=<path>`
- 用户要“看文档结构/标题层级” -> `obsidian outline`
- 用户要“直接读某篇命中的笔记内容” -> 先 `search`/`files` 定位，再 `obsidian read`

如果用户的问题本质上是“总结某个主题在知识库中的分布或观点”，优先采用两步法：

1. `obsidian search` 或 `obsidian search:context` 缩小范围
2. 对最相关的少量文件使用 `obsidian read`、`outline` 或 `backlinks` 补充信息后总结

## 命令构造规则

- 把 `vault=<name>` 放在命令最前，仅在必须切换仓库时使用。
- 包含空格的值用双引号包裹，例如 `query="会议纪要"`。
- `file=` 适合按笔记名解析；需要精确定位时改用 `path=`。
- 用户说“最近”“最新”时，CLI 本身不直接支持按时间排序；先查出候选文件，再结合仓库工具补充判断。
- 用户要统计数量时，优先加 `total` 或选择 `format=json` 后自行汇总。
- 用户要机器可读结果时，优先 `format=json`；用户只要快速答复时可用默认文本格式。
- 单次不要返回过多文件；除非用户明确要求全量，一般加 `limit=10` 或更小。
- 当前环境下 `search:context` 可能出现“命令成功但无输出”的情况；遇到这种情况时，优先降级到 `obsidian search`，必要时再对候选文件执行 `read`。

## 总结规则

- 先给结论，再给依据。
- 结果少时，直接列出关键文件或关键行。
- 结果多时，聚类总结主题、标签、目录分布或高频模式。
- 若没有结果，明确说明“未找到”，并给出下一步可尝试的更宽松查询词。
- 若 `search:context` 无输出但 `search` 有命中，应明确告诉用户“已找到相关文件，但当前 CLI 未返回上下文行”，并改为总结候选文件。
- 若查询语义不够清晰，先做最稳妥的一轮搜索，再根据结果决定是否追问。

## 输出格式

默认按这个顺序组织回答：

1. 一句话回答用户问题
2. 关键发现（2-5条）
3. 必要时给出执行过的命令
4. 必要时建议下一步更精确的查询方向

## 参考资料

- [references/cli-query-patterns.md](references/cli-query-patterns.md)：常用查询命令、参数选择和自然语言到命令的映射
