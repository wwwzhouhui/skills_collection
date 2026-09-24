---
name: hailaobao-gzh-design
display_name: 海老豹排版
display_name_en: Hailaobao WeChat Typesetter
description: 把 Markdown 文章排版成微信公众号可直接粘贴的 HTML，内置 7 套排版风格。触发词：公众号排版、微信排版、gzh 排版、typeset for wechat、Markdown 转公众号。不触发：只想改文字不改格式、要生成小红书图文。
description_zh: 给一篇 Markdown，输出带「复制到公众号」按钮的 HTML 页面。浏览器打开点一下按钮，排好版的正文就进了剪贴板，粘贴到公众号编辑器样式全保留。内置 7 套风格：玉石商务、暖色编辑部、极客单色、香槟品牌、雾霾笔记、午夜研究报告、森绿演示（forest-demo）。
description_en: Turn a Markdown article into a WeChat Official Account ready HTML page with a one-click copy button. Paste into the editor and all inline styles survive. Seven built-in schemes - jade-business, warm-editorial, mono-tech, champagne-brand, mist-notebook, midnight-report, forest-demo. Trigger words include 公众号排版 and typeset for wechat.
category: writing
version: 1.0.0
author: hailaobao2026
---

# 公众号排版 (hailaobao-gzh-design)

把任意一篇 Markdown 文章排版成微信公众号编辑器可直接粘贴的 HTML。

> **本 skill 对 agent 不挑食。** Claude Code 会读上面的 YAML frontmatter 自动挂载；其他 agent（Codex / WorkBuddy / Cursor / Windsurf / Cline / 手动 Prompt）没有相同的自动发现机制，但只要把整个 [.claude/skills/hailaobao-gzh-design/](.) 目录交给它们并让它们按下面的工作流走，产物完全一致 —— 依赖只有 Node.js。同目录的 [AGENTS.md](AGENTS.md) 是给这些 agent 的对等入口。

## 什么时候用这个 skill

用户说以下任何一句就用它：
- "帮我排版这篇文章"（当前上下文有 Markdown 文件）
- "公众号排版" / "微信排版"
- "把 xxx.md 排成公众号可以粘贴的样式"
- `/gzh-typeset <file>` 或类似显式调用

不适用：
- 用户只想改文字不想改格式 → 直接改 Markdown 即可
- 用户想生成小红书图文 → 请用 `/xhs-planner`（如果存在）或图片导出中心

## 工作流

分五步。**每一步都不要跳过。**

### 步骤 1：读文章 + 判断类型

读用户指定的 Markdown 文件（或 stdin/剪贴板里的正文）。分类到以下之一：

- **方法论 / 深度分析**：观点密集、结构清晰、有小节标题
- **教程 / 工作流**：分步骤、代码块、命令行
- **产品评测 / 工具对比**：多个对象横向比较、优缺点
- **心得 / 复盘 / 故事**：第一人称、时间线、情绪起伏
- **资讯 / 快评**：短，1-2 屏可读完

### 步骤 2：确认排版风格（**必做**，除非用户已经指定或授权自动决策）

风格是主观的编辑决定，**默认要问用户**，即使你已经有推荐。

跳过的两种情况：
- 用户在触发时已经点名 scheme（"用玉石商务风"、"midnight-report 走一版"）→ 直接用，不问
- 用户在触发时明确说了"你决定 / 自动挑 / 你看着办 / auto" → 按内容类型选一个，不问

其余所有情况：先读 [references/style-schemes.md](references/style-schemes.md)，根据步骤 1 的分类得出：

- **首选** scheme（写清楚为什么它匹配这篇）
- **备选** scheme（同类型下第二合适）
- **反差款** scheme（气质明显不同，用来让用户能一眼跳出你的类型判断，比如推荐 `jade-business` 时反差款给 `midnight-report`）

然后用**你所在 agent 环境提供的用户问答机制**问用户：
- 在 Claude Code 里 → 用 `AskUserQuestion`，把三套 scheme 做成选项，首选加 `(推荐)` 后缀
- 在 Codex / 命令行 / 其他环境 → 直接在文本里列三条选项，让用户回复编号或名字

问题模板：

> 这篇看着是 <类型>。三套风格你想哪一款？
> 1. **玉石商务** (推荐) — 克制清晰，方法论首选
> 2. **雾霾笔记** — 蓝调网格，读起来像干货笔记
> 3. **午夜研究报告** — 深色反色，数据分析感

**问完等用户回答再往下走。**用户挑了哪套就用哪套，不要二次质疑。

### 步骤 3：AI 排版 —— 改写 Markdown

读 [references/formatting-rules.md](references/formatting-rules.md) 和 [references/typesetting-syntax.md](references/typesetting-syntax.md)，然后**你自己**（不要再调外部 LLM）把原 Markdown 改写。如果文章是「工具教程 / 案例演示」体裁（通篇围绕一个工具体验，穿插发给 Agent 的提示词、安装导出步骤、案例效果），先加读 [references/demo-article-patterns.md](references/demo-article-patterns.md)——纯数字 kicker、提示词收代码块、金句引用、结尾 SummaryCard 的完整模式都在里面，可对照 [examples/remotion-demo.md](examples/remotion-demo.md) 看成品。这篇样本源文的深绿标题条（#255E4A / #F1F4F3）对应 scheme `forest-demo`，不要误选 `jade-business`。

- 给标题加序号 + 竖线副标题（`# 01 | 主标题 | 小字副标题`）
- **kicker 要匹配段落语义**：顺序动作用 `STEP`、并列要点用纯数字 `01/02`、案例用 `CASE`、章节用 `PART A`、问答用 `Q1`、误区用 `AVOID`、原则用 `RULE`、技巧用 `TIP`、数据用 `FACT`。**不要一律用 `STEP`**（除非真的是"先做 A 再做 B"）。拿不准就用纯数字。完整表见 formatting-rules.md。
- 关键短语加 `**加粗**`
- 关键判断句拆成 `> 引用`
- 段落之间插 `---` 分割线，控制视觉呼吸
- 需要总结时插入 `<SummaryCard title="...">...</SummaryCard>`
- 需要提示时插入 `<InfoCard title="...">...</InfoCard>`
- 不改文章原意，不添加原文没有的事实

改写后的 Markdown 写到一个临时文件（比如 `.hailaobao-gzh-design/rewritten.md`），保留原文件不动。

### 步骤 4：渲染 HTML

用改写后的 Markdown 调用渲染脚本：

```bash
node <skill-dir>/scripts/typeset.mjs \
  --input <rewritten.md> \
  --scheme <scheme-id> \
  --title "<文章标题>" \
  --out <目标文件>.html
```

`<skill-dir>` 是这个 skill 的安装目录：
- WorkBuddy / Codex / Cursor 等 → `~/.workbuddy/skills/hailaobao-gzh-design/`
- Claude Code 项目级安装 → `.claude/skills/hailaobao-gzh-design/`

不确定就先 `ls` 一下 skill 目录，别硬猜路径。

参数：
- `--input`：改写后的 Markdown 路径
- `--scheme`：步骤 2 里用户确认（或授权自动挑）的 scheme id
- `--title`：显示在 HTML 页面顶栏的文章名（可选）
- `--out`：产物 HTML 路径，默认放到 `<input>.html` 同目录

脚本产物是一个可以直接在浏览器打开的 HTML：
- 顶部有 **[ 复制到公众号 ]** 按钮
- 中间是完整排好版的正文预览
- 点按钮后，样式化 HTML 被写入剪贴板（`text/html`），可直接粘贴到微信公众号编辑器

## 步骤 5：交付

给用户三个信息：
1. 选了哪个 scheme（一句话说明为什么选它）
2. 改动了原文的哪几处（标题重整 / 加粗 / 插入卡片等，简短列 3-5 条）
3. 产物 HTML 的绝对路径 + 一句"在浏览器打开后点复制到公众号"

不要展开列所有段落改了什么。用户如果想 diff 会自己去看。

## 常见误区

- **不要**直接生成 HTML 交给用户 —— 必须走脚本，否则得不到"复制按钮"页面
- **不要**修改原始 Markdown 文件 —— 改写产物写到临时文件
- **不要**引入未在 typesetting-syntax.md 列出的自定义组件（SummaryCard/InfoCard 之外的都不认识）
- **不要**在改写时插入原文没有的观点或事实
