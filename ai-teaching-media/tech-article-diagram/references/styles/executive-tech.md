# 风格: 现代高级科技商务风 (executive-tech)

**适用场景**: AI 产品方案、商业洞察、咨询式内容、品牌化技术表达。传达"科技的冷峻逻辑 + 人文的温暖呼吸"。

## 风格基因(每个提示词开头必须包含)

```
Style: Professional, clean, sophisticated digital infographic and presentation slide design. Minimalist, balanced, and structured. Blend high-tech professionalism with human-centric details.

Background: very light warm off-white cream or light beige (#FBFBFB or #FFF8F0). Clean, open, and premium.

Color palette:
- Key accents (titles, main icons, data points): deep indigo or vibrant violet (#5136A2 or #4B0082)
- Supporting accents: soft lavender (#B29EEF), misty grey-blue (#A7ADB5)
- Occasional complementary accent: soft desaturated terracotta or peach for local contrast only
- Text: dark charcoal grey (#333333)

Typography:
- Modern clean professional sans-serif
- Strong hierarchy: huge bold titles, medium headers/card titles, avoid small body text
- Major concepts in bold clear Chinese
- Text on the image must be predominantly in Chinese; only use English for established technical terms (e.g. API, Agent, CLI)
- Minimize mixing Chinese and English in the same label or card — this causes garbled Chinese rendering
- Prefer short Chinese phrases (2-6 characters) for all labels, titles, and card headers
- Avoid long sentences or paragraphs inside cards — use icons + short labels instead
- Each card or panel should contain at most one short label and one short value, no dense text blocks
- Small decorative text that cannot be rendered clearly should be omitted entirely

Visual language:
- Card-based UI layout with clean rounded-corner panels/cards and subtle soft shadows
- Minimal geometric icons in deep violet or lavender
- Sleek modern charts like wave graphs, progress indicators, and highlighted KPI cards
- Process flow guided by subtle lines, dashed or solid connectors, and anchor points
- Non-symmetrical but balanced composition with large title on the left or top-left
- Generous negative space, editorial clarity, and premium presentation-slide polish

Image treatment:
- Deep violet should be the primary tone for any imagery
- Do not add decorative photos, screens, notebooks, coffee cups, or other physical objects unless explicitly requested in the content prompt
- Do not add post-it notes, handwritten annotations, or extra screens — these cause the model to invent fake garbled text

Content fidelity:
- All text, numbers, metrics, and labels on the image must come from the actual diagram content prompt only
- Never invent any text, annotations, labels, or UI elements that do not exist in the source content
- If the content has no metrics, use descriptive cards instead of fake KPI panels

Do:
- Keep the overall result premium, reflective, structured, and businesslike
- Make it feel like a crossover of editorial design, dashboard UI, bento cards, and duotone visual storytelling

Content fidelity:
- All numbers, metrics, KPI values, and labels must come from the actual diagram content
- Never invent random percentages, statistics, or KPI numbers that do not exist in the source material
- If the content has no metrics, use descriptive cards instead of fake KPI panels

Do not:
- No childish illustration style
- No heavy saturation
- No cluttered dashboard overload
- No 3D rendering
- No gaudy gradients or flashy neon cyberpunk effects
```

## 版式原型

同一个 `executive-tech` 风格下,允许根据内容类型切换不同构图原型。不要把所有内容都硬塞成同一种密集卡片流。

### 原型 A: Hero + Orbital Cards

适合:角色转变、概念升级、认知迁移、抽象主题。

```
Composition:
  Large editorial headline on the left or top-left.
  One processed duotone human portrait or object image on the right or center-right.
  4-5 floating concept cards orbiting or surrounding the main subject.
  Use sparse connector lines or anchor points only.

Density rule:
  Each orbit card should carry one concept only.
  Do not turn the surrounding cards into mini dashboards.
```

### 原型 B: Hero + 5 Step Workflow

适合:流程、闭环、时序、方法步骤。

```
Composition:
  Huge left headline.
  One short takeaway block on the upper right.
  4-5 large horizontal step cards across the lower half or middle band.
  Use dotted or dashed arrows to guide the sequence.

Density rule:
  Keep the steps spacious and narrative-led.
  Prefer one sentence per step and almost no extra side modules.
```

### 原型 C: Hero + KPI Row

适合:指标解读、结果复盘、能力评估、成熟度判断。

```
Composition:
  Strong editorial headline and one short supporting sentence.
  One hero image or one clean chart zone in the upper area.
  3-5 KPI cards or metric panels aligned in one row or a clean grid below.
  Optional tiny annotations or mini labels only.

Density rule:
  Let the numbers breathe.
  Avoid stacking many charts, notes, and icons in the same area.
```

### 原型 D: Hero + Modular System Stack

适合:系统架构、方法论分层、输入输出模块、AI 工作流系统。

```
Composition:
  Large left title block.
  Right side uses stacked panels, modular boards, or layered system cards.
  The main board should feel like a premium SaaS system map instead of plain rectangles.
  One small note, metric, or processed image area may be inserted to break symmetry.

Density rule:
  Limit the number of primary modules.
  Keep hierarchy obvious: core layer first, support layers second.
```

### 原型 E: Hero + Editorial Desk Collage

适合:产品方法论、品牌化技术表达、人与 AI 协同、案例洞察。

```
Composition:
  Editorial statement on the left or top-left.
  Right side mixes UI cards, processed imagery, objects such as notebook / coffee / laptop, and sparse annotations.
  Elements may overlap slightly to create depth and narrative.

Density rule:
  Use overlap as a premium editorial device, not as decoration.
  The page still needs strong whitespace and one dominant reading path.
```

### 原型 F: Hero + Dense Insight Board

适合:运营看板、指标体系、策略仪表盘、成熟度画像、需要同时承载多个高价值模块的内容。

```
Composition:
  Huge editorial headline occupies the left or top-left as the primary anchor.
  One processed human portrait, object, or desk scene acts as the emotional anchor.
  The right side or upper-right side hosts a structured dashboard board of cards, KPI tiles, charts, and process modules.
  The lower area may contain one grounded physical-object zone such as notebook / laptop / coffee to stabilize the composition.

Density rule:
  Dense is allowed only when the modules are clearly grouped into 2-3 zones.
  Every card must earn its space: KPI / module / process / support note.
  Keep one dominant reading path: headline -> hero anchor -> dashboard zones.
  Do not scatter small cards evenly across the whole page.
  Even in dense mode, preserve breathing room between groups.
```

## 内容类型与原型映射

优先按内容性质选原型:

- 抽象概念 / 角色变化 / 认知迁移 -> `Hero + Orbital Cards` 或 `Hero + Editorial Desk Collage`
- 流程 / 闭环 / 操作步骤 -> `Hero + 5 Step Workflow`
- 指标 / 判断 / 结果对比 -> `Hero + KPI Row`
- 架构 / 分层 / 方法论系统 -> `Hero + Modular System Stack`
- 品牌化产品叙事 / 人机协同 / 顾问式表达 -> `Hero + Editorial Desk Collage`
- 运营看板 / 指标系统 / 策略态势图 / 多模块洞察页 -> `Hero + Dense Insight Board`

## 密度升级条件

`executive-tech` 默认优先低密度。只有在下面这些情况,才允许升级为受控密集:

- 内容本身就是多个指标、多个模块、多个关系同时成立
- 单一 KPI 行或单一流程卡,已经无法表达文章重点
- 读者需要一眼看到“系统正在如何运转”,而不只是一个步骤或一个概念

即使升级为受控密集,也要遵守:

- 先有大标题锚点,再有视觉主角,最后才是信息板块
- 信息板块必须分区,通常是 `KPI 区` + `流程/关系区` + `支撑模块区`
- 允许 6-10 个模块,但不要让每个模块都同等抢眼
- 小图表可以多,但每个图表必须足够简洁,不能像真实 BI 系统那样满屏细节
- 人物、桌面物件、便利贴只作为节奏锚点,不能把主信息遮住

### 对比类图 (A vs B)

```
Header: Huge bold Chinese headline aligned left or top-left in dark charcoal.
Key phrase highlight: use deep indigo/violet only for the most important phrase.

Main body:
  Use asymmetric bento-card layout instead of rigid equal columns.
  A-side and B-side can still be visually separated, but by cards, data blocks, and subtle connector lines.
  For metric-heavy comparisons, prefer the "Hero + KPI Row" logic.
  If both sides each contain multiple metrics or modules, allow the "Hero + Dense Insight Board" logic.
  For concept-vs-concept comparisons, allow one processed image or object to bridge both sides.

Supporting modules:
  - KPI or metric cards only when the actual content provides real numbers
  - One or two small comparison charts
  - Processed duotone object/person image bridging the sections
```

### 流程/循环类图

```
Header: Large editorial-style title on the left or top-left.

Density rule:
  Prefer low-density narrative process layout.
  Use 4 to 5 main steps only.
  Each step card should contain:
    - Step number
    - Short title (2-4 Chinese characters preferred)
    - One short explanatory sentence only
  Do not overload each step with many bullets, dense labels, or too many side metrics.

Main flow:
  Use premium rounded-corner step cards connected by subtle dotted or dashed arrows.
  The overall feeling should be closer to an editorial workflow board than a crowded analytics dashboard.
  At most one small supporting metric strip or one small chart cluster for the entire page.
  If the process itself is already clear, omit KPI cards entirely.
  Only when the article is truly about operational status, system health, or layered execution context, allow a denser side dashboard.

Image integration:
  Prefer one processed duotone image per 1-2 steps, or one larger integrated image area shared by the whole flow.
  Images should support the narrative, not compete with the process cards.

Composition reference:
  Think "huge left title + 4/5 horizontal cards + one concise top-right takeaway + sparse connector lines".
  Preserve generous breathing room between modules.
```

### 架构/分层类图

```
Header: Large title plus one smaller supporting subtitle.

Structure:
  Use the "Hero + Modular System Stack" logic by default.
  Use layered bento cards or modular dashboard panels instead of plain boxes.
  Relationships should feel like a high-end SaaS system map.
  If the architecture also needs to show KPIs, actors, and live system states at once, allow a controlled "Hero + Dense Insight Board" variant.
  One side can contain metrics, notes, or a processed image to avoid overly rigid symmetry.
```

## 禁忌

- No hand-drawn notebook look
- No flat generic corporate template without texture
- No oversaturated purple gradient aesthetic
- No chaotic card stacking
- No visual noise that weakens readability
- No dense process slide packed with too many KPI cards, notes, labels, and charts at once
- No fake density: if the content does not justify many modules, go back to a lower-density prototype
