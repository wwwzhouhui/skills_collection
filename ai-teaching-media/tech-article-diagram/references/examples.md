# 完整提示词案例

前四个案例按图类型拆分,最后补一个 `executive-tech` 风格的完整案例,方便 Claude 在第三种风格下直接套用。

---

## 🧠 案例 1:抽象概念可视化 · Agent Profile 的真隔离

**来源文章**:Hermes 多 Agent 踩坑实战(已发)
**用在哪段**:正文"先聊聊 profile,这是整个多 Agent 的基础"这一节里

```
Diagram showing the concept of "Agent Profile" and "True Isolation."

Title: "Agent Profile & 真隔离 (True Isolation)"

Left side conceptual diagram: "Agent Profile 的本质 (Essence of Agent Profile)"
A central stylized "brain" or "avatar" icon labeled "AI 分身 (AI Doppelganger)."
Surrounding this icon, several labeled document icons point inward:
1. "config.yaml"
2. ".env"
3. "SOUL.md"
4. "独立的 Memory (Independent Memory)"
5. "独立的 Skills (Independent Skills)"
All icons connected to the central "AI 分身."

Center diagram: "物理隔离的实现 (Implementation of Physical Isolation)"
Two separate vertical process icons.
Left process: Inside a bordered box, an avatar with a "Process" text (indicating active).
Below it, another bordered box labeled "独立的 Gateway 进程 (Independent Gateway Process)."
Right process: Identical structure to the left.
Above both processes, a large upward-pointing arrow labeled "HERMES_HOME 环境变量切换根目录 (HERMES_HOME Environment Variable Switches Root Directory)."
A callout text box pointing to this arrow: "朴素实现, 实打实隔离 (Simple implementation, real-world isolation)."

Right side diagram: "对比与优势 (Comparison & Advantages)"
A stylized vs. comparison section.
Top section: A small diagram with a single gear icon (shared process). Text below: "OpenClaw (配置层面切换)"
Bottom section: A comparison diagram showing two separate gear icons (independent processes). A large directional arrow points to this. Text below: "Hermes (进程级物理隔离)."
A callout box on the right: "为什么是物理隔离? \n1. 一个挂了, 其他照常 (One crashes, others continue) \n2. 互不依赖, 稳定性高 (No interdependence, high stability)"

Bottom summary text: "用进程隔离打造真实的多 Agent 协作基础"

```

---

## 🔄 案例 2:流程/循环 · 知识复利循环

**来源文章**:LLM Wiki 知识管理(参考示例)
**用在哪段**:讲 Wiki 的自我积累机制时

```
Diagram showing a knowledge compound loop.

Title: "知识复利循环 (Knowledge Compound Loop)"

Main circular flow with four nodes connected by arrows forming a loop:
1. "用户提问" (top left) - arrow pointing right to
2. "Wiki 检索回答" (top right) - with annotation "基于已编译的知识,带引用" - arrow pointing down to
3. "高质量答案归档" (bottom right) - with annotation "自动存入 queries/ 目录" - arrow pointing left to
4. "Wiki 知识更厚" (bottom left) - with annotation "下次查询更快更准" - arrow pointing up back to node 1

Center of the loop: a large upward spiral arrow icon representing growth, with text "复利"

Right side callout box: "你的探索、提问、分析、发现 → 不消失在聊天记录里 → 持续积累到 Wiki"

Bottom summary text: "Wiki 不只是编译库,更是你思考过程的沉淀层"

```

---

## ⚖️ 案例 3:对比/分类 · delegate_task vs 多 Agent 协作

**来源文章**:Hermes 多 Agent 踩坑实战
**用在哪段**:"Step 6:以为成功了,结果发现是假的"这一节,讲两种协作模式差异时

```
Diagram showing a comparison between two Multi-Agent collaboration modes.

Title: "delegate_task vs Discord 点名 · 两种多 Agent 协作模式"

Layout: split vertically into two halves with a large "VS" indicator in the middle.

Left side: "delegate_task · 隐式协作"
- Main icon: a single large closed box labeled "Admin Agent"
- Inside the box, several small ghostly figures labeled "subagent (无状态)"
- Arrow from Admin to ghosts with label "spawn"
- Arrow back with label "only final summary"
- Check: "Token 极省"
- Check: "速度快"
- X marker: "Profile 不生效"
- X marker: "无状态,无记忆"
- Small label below: "临时打工仔,用完即焚"

Right side: "Discord 点名 · 显式协作"
- Main icon: three connected avatar boxes labeled "Admin", "Search", "Ink"
- Arrows between them labeled "@mention"
- Check: "Profile 完整生效"
- Check: "人格独立,可追溯"
- X marker: "Token 消耗 3-5x"
- X marker: "速度慢"
- Small label below: "正规军接力,各司其职"

Callout box (bottom right corner): "zero-context-cost 的代价,就是 zero-profile-data"

Bottom summary text: "追求效率用 delegate,追求团队感用点名协作"

```

---

## 🏗️ 案例 4:架构/组件 · 三人 AI 小组的角色分工

**来源文章**:Hermes 多 Agent 踩坑实战
**用在哪段**:"Step 1:建三个 Agent,分工明确"这一节,列出三个 Agent 后

```
Diagram showing the role architecture of a three-Agent team.

Title: "林家班三人小组 · 角色架构 (Three-Agent Team Architecture)"

Layered role-based structure from top to bottom:

Top layer: "用户 (User)"
  - Simple stick figure or user icon
  - Arrow pointing down with label "提交需求"

Middle layer: "林小管 · Admin (调度员 / Planner)"
  - A box with a clipboard/planner icon
  - Small annotation: "拆解任务,公开点名"
  - Two arrows branching down to two executors

Executor layer (side by side, parallel):
  - Left box: "林小探 · Search (情报专家 / Searcher)"
    - Magnifying glass icon
    - Annotation: "联网调研,引用信源"
  - Right box: "林小墨 · Ink (文案专家 / Writer)"
    - Pen icon
    - Annotation: "Markdown 整理,Obsidian 双链"

At the bottom, a thin line connecting both executors back up to Admin with label "任务完成汇报"

Right side callout box: "身份隔离 · 严禁越权 · 一个 Agent 就是一个岗位"

Bottom summary text: "三人小组的最小协作单元:一个调度 + 两个执行"

```

---

## 🟣 案例 5:executive-tech 风格 · 新的运营闭环更像这样

**来源文章**:社区运营 / AI 助手 / 知识库方法论类文章  
**用在哪段**:文章在解释“新的运营闭环”时,希望做成低密度、高级感、流程感很强的横向步骤图

```
Professional presentation-style infographic showing the concept of "新的运营闭环，更像这样。"

Headline layout:
- Huge bold Chinese title aligned on the left:
  "新的运营闭环"
  "更像这样。"
- Highlight the phrase "这样" in deep indigo/violet.
- One short supporting line below:
  "观察 → 响应 → 升级 → 学习 → 回写知识。"

Overall composition:
- Premium editorial layout with asymmetrical but balanced structure
- Large title block on the left
- A concise takeaway on the upper right
- Five large horizontal step cards across the lower half
- Plenty of warm off-white negative space
- The page should feel spacious, calm, and premium, not crowded

Upper-right takeaway:
- Small two-line statement:
  "观察 → 响应 → 升级 → 学习 → 回写知识。"
  "每一次处理，都让下一次更稳。"

Main process flow:
- Five large rounded-corner cards arranged horizontally from left to right
- Cards connected with subtle dotted arrows
- Each card contains only:
  - A circular step badge
  - One short Chinese title
  - One short explanatory sentence
  - One integrated processed duotone image or UI panel in the lower half

Card 1:
- Step badge: "01"
- Title: "观察"
- Text: "看见真实的需求与情绪信号。"
- Visual: processed indigo-toned person with conversation bubbles / user feedback context

Card 2:
- Step badge: "02"
- Title: "响应"
- Text: "AI 先接住重复层，人处理高信任层。"
- Visual: stylized AI assistant UI on a laptop or phone

Card 3:
- Step badge: "03"
- Title: "升级"
- Text: "识别模式与机会，升级为行动或策略。"
- Visual: processed meeting wall / notes / decision card

Card 4:
- Step badge: "04"
- Title: "学习"
- Text: "沉淀经验与判断，形成可复用能力。"
- Visual: laptop screen + subtle chart or summary card

Card 5:
- Step badge: "05"
- Title: "回写知识"
- Text: "更新知识库与 SOP，让团队与 AI 共同进步。"
- Visual: clean knowledge-base card stack with status label "已更新"

Image integration:
- Photos should be processed into textured indigo-toned halftone / dot-matrix / etch-style imagery
- Each image should stay embedded inside its card rather than floating everywhere across the page
- Overlap is allowed, but very restrained
- Avoid using too many separate object cutouts on one page

Human-touch details:
- Optional one small handwritten-style note or one subtle sticky note near one card edge
- Keep these details sparse and supporting only

Visual language:
- Card-based UI with subtle soft shadows
- Minimal geometric icons in deep violet and lavender
- Only tiny supporting UI accents or very small chart fragments if needed
- Subtle dashed connector lines guiding the eye
- Text in dark charcoal grey, accents in deep violet, supporting tones in lavender and misty grey-blue
- Do not build a busy dashboard; prioritize step clarity and rhythm

Bottom summary text:
"先接住问题，再把经验沉淀成系统。"
```

---

## 🟣 案例 6:executive-tech 风格 · 岗位没有消失,重心变了

**来源文章**:AI 对岗位影响 / 组织转型 / 能力迁移类文章  
**用在哪段**:文章在解释“岗位不是消失,而是工作重心发生迁移”时,适合用人物主视觉 + 环绕概念卡的低密度版式

```
Professional editorial-style infographic showing the concept of "岗位没有消失，重心变了。"

Headline layout:
- Huge bold Chinese title aligned on the left:
  "岗位没有消失，"
  "重心变了。"
- Highlight the phrase "重心变了" in deep indigo/violet.
- One short supporting line below:
  "重复执行在退场，判断、协同与经营关系在上升。"

Overall composition:
- Premium executive-tech presentation slide
- Large title block on the left
- One processed indigo-toned human portrait on the right or center-right
- Four floating concept cards arranged around the portrait
- Strong whitespace and very light connector lines
- The page should feel calm, reflective, and authoritative

Main visual:
- A processed duotone halftone portrait of a professional woman or operator
- Indigo/violet tone only, textured and editorial
- The portrait is the visual anchor; cards orbit around it instead of competing with it

Orbiting cards:
Card 1:
- Title: "回复消息"
- Text: "标准化回应，正在被 AI 接手。"
- Small icon: chat bubble

Card 2:
- Title: "识别意图"
- Text: "重点从回答问题，转向判断真正需求。"
- Small icon: target or radar

Card 3:
- Title: "升级策略"
- Text: "高价值动作来自模式识别与策略选择。"
- Small icon: layered cards or spark line

Card 4:
- Title: "经营关系"
- Text: "长期价值来自信任、节奏与持续互动。"
- Small icon: network or handshake

Connector logic:
- Use sparse anchor lines or dotted connectors between the portrait and the cards
- Avoid arrows everywhere; the relationship can feel orbital rather than mechanical

Human-touch details:
- One tiny handwritten-style note or one subtle sticky note is allowed near one corner
- Keep it restrained; the page still needs to feel like a premium business slide

Bottom summary text:
"被替代的不是岗位本身，而是岗位里最机械的那一层。"
```

---

## 🟣 案例 7:executive-tech 风格 · 写作 Agent 的方法论架构

**来源文章**:AI 工作流 / Agent 方法论 / 系统设计类文章  
**用在哪段**:文章在解释“一个写作 Agent 系统到底由哪些层组成”时,适合用模块化系统板式而不是传统上下箭头框图

```
Professional premium infographic showing the architecture of "写作 Agent 的方法论架构。"

Headline layout:
- Large bold title on the left:
  "写作 Agent"
  "的方法论架构。"
- One short subtitle below:
  "不是一个提示词，而是一套可分层协作的系统。"

Overall composition:
- Warm off-white editorial background
- Title block on the left third
- A modular system board on the right two-thirds
- The system board uses stacked rounded panels, clean spacing, and subtle shadows
- The page should feel like a premium SaaS strategy slide, not a textbook diagram

Main system board:
Top input layer:
- Card title: "输入层"
- Modules: "选题", "资料", "上下文", "目标读者"
- Small note: "决定写什么、为谁写"

Core reasoning layer:
- Largest center card titled: "策略核心"
- Sub-labels inside: "拆解", "判断", "取舍", "组装"
- This is the visual core of the page

Execution layer:
- Three aligned cards below or to the side:
  1. "结构设计"
  2. "段落生成"
  3. "语气校准"
- Each card contains one short sentence only

Memory / refinement layer:
- Smaller support cards:
  - "案例库"
  - "知识库"
  - "反馈回写"

Side support area:
- One processed indigo-toned laptop screen or notebook image
- Optional tiny metric or checklist chip like:
  - "一致性"
  - "可复用"
  - "可迭代"

Connector logic:
- Use clean vertical or lateral flow lines between layers
- Keep connectors subtle; hierarchy should be obvious without heavy arrows

Bottom summary text:
"真正可复用的写作 Agent，靠的是分层方法，而不是单次灵感。"
```

---

## 🟣 案例 8:executive-tech 风格 · 社区运营,正在从回复消息转向经营关系系统

**来源文章**:社区运营 / 客户成功 / AI 助手与知识库协同类文章  
**用在哪段**:文章需要同时表达“关系经营升级、运营流程、关键指标、AI 与知识库支撑”时,适合受控密集的洞察看板式版面

```
Professional premium infographic showing the concept of "社区运营，正在从回复消息转向经营关系系统。"

Headline layout:
- Huge bold Chinese title on the left:
  "社区运营，"
  "正在从回复消息"
  "转向经营"
  "关系系统。"
- Highlight the phrase "经营关系系统" in deep indigo/violet.
- One short supporting sentence below:
  "真正被沉淀的，不是消息本身，而是关系、判断与长期复利。"

Overall composition:
- Warm off-white editorial background
- Strong left-side headline block as the first reading anchor
- One large processed indigo-toned collaborative human photo in the center-left or lower-left as the emotional anchor
- A structured dashboard board on the right side
- One grounded desk-object zone along the lower edge with notebook / coffee / laptop fragments
- Dense but controlled: modules must be grouped, not scattered

Dashboard grouping:
Zone 1: KPI strip on the upper-right
- 3 compact KPI cards:
  - "成员活跃度 92%"
  - "成员留存率 89%"
  - "成员满意度 4.6/5"
- Each card contains one tiny smooth wave chart only

Zone 2: relationship / value flow in the middle-right
- A horizontal five-node flow:
  1. "吸引"
  2. "连接"
  3. "价值"
  4. "共创"
  5. "沉淀"
- Use minimal line icons and subtle dashed connectors
- One short label above:
  "社区运营关系系统，闭环流程"

Zone 3: support modules in the lower-right
- Three clean support cards:
  - "AI 助手"
  - "知识库"
  - "关键指标看板"
- Each card should show only a few lines or tiny metrics, not a full software screenshot

Visual anchors:
- The human image should visually connect the title area and the dashboard area
- One handwritten annotation or sticky note may point to the relationship system idea
- One notebook or desk object at the bottom can stabilize the composition and add warmth

Density rules:
- Dense is acceptable here because the article itself contains strategy, process, metrics, and system support at the same time
- Still preserve a clear reading order:
  title -> human anchor -> KPI strip -> relationship flow -> support cards
- Use only 3 major groups on the right, not many evenly sized floating modules
- Do not let the support cards overpower the headline

Bottom summary text:
"先经营关系，再让 AI 和知识把这套关系经营能力固化下来。"
```

---

## 使用这些案例的方法

给新文章生成插图时:

1. **先判断这个位置属于四类中的哪一类**
2. **找对应案例作为模板骨架**
3. **把案例里的 `{{占位符}}` 或具体内容换成新文章的内容**
4. **不要额外手写 `Style: ...` 段落**，脚本会按 `--style` 自动注入风格前缀
5. **提交给 API 之前,过一遍 `prompt_template.md` 里的三条自检**
