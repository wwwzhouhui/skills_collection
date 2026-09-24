# hailaobao-gzh-design (Agent 入口)

这是给**任何** AI agent 用的入口文档 —— Claude Code 走同目录的 [SKILL.md](SKILL.md)，其他 agent（Codex / WorkBuddy / Cursor / Windsurf / Cline / 自建 agent / 手动 Prompt）走这份。**两份文档指向的是同一套工作流和同一套脚本，产物完全一致。**

## 这个工具是干什么的

把一篇 Markdown 文章排版成微信公众号编辑器可直接粘贴的 HTML。产物是一个自包含的 HTML 页面，顶栏有「复制到公众号」按钮，用户在浏览器打开点一下按钮就能把带样式的正文写进剪贴板，粘贴到公众号后台样式全保留。

## 什么时候触发

用户说：
- "帮我排版这篇文章"（附带一个 Markdown 文件路径）
- "公众号排版" / "微信排版"
- "把 xxx.md 排成公众号能贴的样式"

不触发：
- 用户想生成小红书图文（走另一个 skill 或图片导出模块）
- 用户只想改文字不改格式

## 依赖

只有一个：**Node.js**（>= 16，用了 ESM）。脚本零 npm 依赖，只调用 Node 内置的 `fs/path`。

如果你所在环境不能执行本地 Node 脚本，这个工具**不能用** —— 请告诉用户切到能跑 Node 的环境。

## 五步工作流

### 步骤 1 — 读文章，判断类型

读入 Markdown。分类到以下之一：**方法论**、**教程**、**评测**、**心得**、**资讯**。

### 步骤 2 — 让用户挑排版风格（**默认必做**）

读 [references/style-schemes.md](references/style-schemes.md) 挑三套：首选（`(推荐)` 后缀 + 理由）+ 同类型备选 + 反差款。用你的问答机制问用户；用户挑了就用。

跳过的两种情况：
- 用户触发时已经点名 scheme（"用玉石商务风"、"midnight-report 走一版"）→ 直接用
- 用户明确说了"你决定 / 自动 / auto" → 按类型自动选首选

**scheme id 只能从 [references/style-schemes.md](references/style-schemes.md) 目录里选，不要自造。** 目录现为 7 套。演示型工具文的深绿标题条用 `forest-demo`。

### 步骤 3 — 改写 Markdown

读 [references/formatting-rules.md](references/formatting-rules.md) 和 [references/typesetting-syntax.md](references/typesetting-syntax.md)。**你自己按规则改**（不要再调外部 LLM，你已经是 LLM 了）。「工具教程 / 案例演示」体裁（穿插 Agent 提示词、安装导出步骤、案例效果）先加读 [references/demo-article-patterns.md](references/demo-article-patterns.md)。核心操作：

- 主标题加 `序号 | 主标题 | 副标题` 的竖线语法
- **kicker 匹配段落语义**：顺序动作 `STEP`、并列要点纯数字 `01/02`、案例 `CASE`、章节 `PART A`、问答 `Q1`、误区 `AVOID`、原则 `RULE`、技巧 `TIP`、数据 `FACT`。**不要通篇甩 `STEP`**（除非真是"先做 A 再做 B"）。拿不准用纯数字兜底。完整表见 formatting-rules.md。
- 每 2-3 段挑一处关键短语 `**加粗**`
- 独立成立的判断句拆成 `> 引用`
- 章节之间放 `---`
- 有自然的收束段落时插 `<SummaryCard title="…">…</SummaryCard>`
- 有前置条件 / 警告时插 `<InfoCard title="…">…</InfoCard>`

**铁律**：不加事实、不删观点、不换立场、代码块一字不改。总改动 ≤ 30%。

把改写结果写到临时文件（比如 `<原路径>.rewritten.md`），**不要覆盖原文件**。

### 步骤 4 — 调用渲染脚本

```bash
node <skill-dir>/scripts/typeset.mjs \
  --input <rewritten.md> \
  --scheme <scheme-id> \
  --title "<文章标题>" \
  --out <目标>.html
```

`<skill-dir>` 是这个 skill 的安装目录：WorkBuddy / Codex / Cursor 等通常是 `~/.workbuddy/skills/hailaobao-gzh-design/`，Claude Code 项目级安装是 `.claude/skills/hailaobao-gzh-design/`。不确定就先 `ls` 目录再执行。

参数：
- `--input`：改写后的 Markdown 路径（必填）
- `--scheme`：步骤 2 敲定的 scheme id（必填；未指定默认 `jade-business`）
- `--title`：显示在 HTML 顶栏的文章名（可选）
- `--out`：产物 HTML 路径（可选，默认放到 `<input>` 同目录同名 `.html`）

未知 `--scheme` 会 exit 1 并在 stderr 列出可用 id。

### 步骤 5 — 给用户交付

回复用户 3 件事：
1. **用了哪个 scheme** + 一句为什么（呼应用户的选择或你的自动决策）
2. **改动了原文的哪 3-5 处**（列表：标题重整 / 加粗几处 / 引用几处 / 插入什么卡片）
3. **产物 HTML 的绝对路径** + 一句"在浏览器打开后点顶栏「复制到公众号」按钮"

不要展开列每段的改动。用户要 diff 会自己查。

## 常见误区

- **不要**直接生成 HTML 贴给用户 —— 必须走脚本，否则得不到"复制按钮"页面
- **不要**修改用户原始 Markdown 文件 —— 改写产物写到临时文件
- **不要**引入 `SummaryCard` / `InfoCard` 之外的自定义组件（渲染器不认）
- **不要**在改写时插入原文没有的观点、事实、承诺
- **不要**在没问用户的情况下擅自定 scheme（除非用户已经指定或授权 auto）

## 目录结构

```
<skill-dir>/               # ~/.workbuddy/skills/hailaobao-gzh-design/ 或 .claude/skills/hailaobao-gzh-design/
├── SKILL.md              # Claude Code 入口（YAML frontmatter 触发）
├── AGENTS.md             # 本文档：给其他 agent 的对等入口
├── references/
│   ├── style-schemes.md      # 7 套 scheme 目录（含 forest-demo）
│   ├── typesetting-syntax.md # 扩展 Markdown 语法
│   ├── formatting-rules.md   # 改写方法论 + before/after 示例
│   └── demo-article-patterns.md # 工具教程/演示型文章的排版模式
├── scripts/
│   ├── schemes.mjs           # 7 套 scheme 的 inline style 生成器（含 forest-demo）
│   └── typeset.mjs           # 主渲染脚本
└── examples/
    ├── demo.md               # 样例输入（冒烟测试）
    ├── demo.html             # 样例输出
    ├── remotion-demo.md      # 演示型文章样例输入（WorkBuddy+Remotion）
    └── remotion-demo.html    # 演示型文章样例输出
```
