---
name: tech-article-diagram
description: |
  为技术长文自动识别插图位置,并生成 16:9 概念图/流程图/对比图/架构图。支持七种风格:手绘网格笔记本风(notebook)、专业扁平信息图(infographic)、现代高级科技商务风(executive-tech)、温暖手绘卡片风(cozy-handdrawn)、技术简笔画风(tech-doodle)、卡通信息图风(cartoon-infographic)和白板手绘风(whiteboard-sketch)。当用户需要给已经写好的文章配插图、加配图、排版优化、让长文不那么单调时使用。触发词包括:加插图、配图、加几张图、让文章更生动、排版优化、文章太单调了、给文章画几张手绘图、手绘示意图、信息图、商务风配图、科技商务风。skill 的核心价值在于"智能识别文章里哪些段落值得配图"——优先选抽象概念、流程循环、对比分类、架构组件这四类地方,不在每段机械配图。通过 ai-image-generator 生图执行层生成(默认 MuleRun Nano Banana 2, 也可切换 APImart/Atlas/Agnes),支持通过 --style 切换不同视觉风格。不要用于封面图(走封面 skill)、截图替代、纯代码展示、表情包生成。
---

# 技术长文插图生成器

把一篇 3000~8000 字的技术长文,自动加上 4-5 张概念图、流程图、对比图,让长文不再单调。

## 什么时候触发这个 skill

明确触发:
- "帮我给这篇文章加几张图"
- "这篇太单调了,配几张手绘图"
- "加点插图,不要太多,关键位置就行"
- "你看看哪里可以配图"
- "给我画几张示意图"

不要触发的场景:
- 封面图需求 → 走 `ai-image-generator` skill
- 产品截图、报错截图等纪实类图片 → 这些应该是真实截图,不该由 AI 生成
- 表情包、头像、单图海报 → 走别的工具
- 纯代码展示 → 代码块就够了,不需要插图
- 小红书九宫格 → 风格完全不同

## 核心流程(四步走)

### 第零步:确认风格

在开始之前,先问用户想要哪种风格:

**notebook（手绘笔记本风）**
黑墨水主笔 + 绿正向 + 红强调，网格纸背景。适合工程师向、技术教程、个人博客。
> "用笔记本手绘风就好"

**infographic（专业信息图风）**
米白底 + 深褐红标题，蓝/橙双色对比。适合商业演示、对比分析、品牌内容。
> "来张专业信息图风格的"

**cozy-handdrawn（温暖手绘卡片风）**
米白纸感底 + 黑色手绘线条 + 粉彩圆角卡片 + 轻漫画式信息图布局 + 个人动画形象辅助叙事。适合中文技术长文、概念解释、流程拆解、对比分析、公众号教程配图。
> "用温暖手绘卡片风"

**tech-doodle（技术简笔画风）**
暖白奶油底 + fine-liner 墨线笔触 + 极淡粉彩上色 + 极简火柴人角色 + 底部荧光笔金句高亮。适合技术博客、知识管理、架构讲解、个人品牌内容。
> "用技术简笔画风"

**cartoon-infographic（卡通信息图风）**
干净白底 + 手绘圆角容器 + 功能性柔和多色 + 可选 host 卡通形象辅助叙事。适合技术博客、产品文档、知识管理、教程配图。需要小人的场景自动走 edit 模式引入卡通参考图,不需要的走纯 generation。
> "用卡通信息图风"

**whiteboard-sketch（白板手绘风）**
暖奶油底 + 黑色手绘马克笔线条 + 柔和粉彩圆角容器 + 简约火柴人角色 + 教育图示布局。像一位 skilled illustrator 在白板上随手画的示意图,亲切、清晰、有温度。适合技术教程、概念讲解、流程说明、架构入门。
> "用白板手绘风"

如果用户没明确偏好，**必须先问用户要 notebook、infographic、executive-tech、cozy-handdrawn、tech-doodle、cartoon-infographic 还是 whiteboard-sketch，再继续**。不要直接用默认风格生成。

### 第一步:分析文章,识别 4-5 个"值得配图"的位置

**这是整个 skill 里最重要的一步,直接决定文章读起来舒服不舒服**。

读完文章后,按下面四类识别候选位置,**按每类的价值密度挑出总共 4-5 个**:

| 类型 | 什么时候算"值得配图" |
|---|---|
| 🧠 **抽象概念可视化** | 文章在讲一个读者难以凭空想象的概念(比如"进程隔离"、"上下文污染"、"人格档案") |
| 🔄 **流程/循环/时序** | 文章描述一个多步骤过程或者循环(比如"任务接力"、"知识复利"、"踩坑闭环") |
| ⚖️ **对比/分类** | 文章在做 A vs B、或者列举几种分类(比如"隐式协作 vs 显式协作"、"三种 clone 策略") |
| 🏗️ **架构/组件关系** | 文章讲一个系统由哪些部件组成(比如"SOUL.md 的组成"、"三个 Agent 的角色分工") |

**什么地方不配图**:
- 纯代码段落(代码本身就是视觉元素)
- 文章已经用了 markdown 表格、列表、代码块的地方
- 一句话就能讲清楚的事实陈述
- 情绪段落(吐槽、金句、感慨——这些靠文字的节奏感,图反而打断)

**4-5 张图的分布节奏**:
- 开头(前 300 字):不放图,让读者先进入文字
- 第一个核心概念出现时:第 1 张(通常是🧠抽象概念可视化)
- 中段:2-3 张(穿插流程/对比/架构图)
- 压轴金句或总结段:1 张(可选,只有文章有升维总结才加)
- 结尾钩子后:不加图

**识别后,把选中的位置用下面的结构记下来,给用户看一眼再生图**:

```
我在文章里挑出了这 5 个建议插图的位置:

1. 【第 X 段,讲 profile 是什么】
   类型:🧠 抽象概念可视化
   图名:「Agent Profile & 真隔离」
   核心要表达:profile 是一个 AI 分身,由多个文件组成,靠进程隔离

2. 【第 Y 段,讲三个 Agent 的分工】
   类型:🏗️ 架构/组件关系
   图名:「三人小组的角色分工」
   核心要表达:林小管调度 / 林小探搜集 / 林小墨整理

...(共 4-5 个)

要按这个方案生图吗?或者你想调整某几处?
```

**等用户确认后再进第二步。** 这一步不能省,因为:
1. 用户可能想保留某些位置的"文字纯净度",不加图
2. 用户可能想在你没选的位置加
3. 这是一个协作决策点,省了会让用户觉得失控

### 第二步:按风格模板生成提示词

读取 `references/prompt_template.md` 获取骨架模板,把文章素材填进去。**只写图表内容描述,不写风格前缀**——风格前缀在第三步由 `inject_style.py` 自动注入。

对每张图,使用骨架模板,把以下信息填进去:

- **图的标题**(中文 + 英文对照)
- **主体结构**(是"中心辐射式" / "流程循环式" / "左右对比式" / "分层架构式")
- **每个节点的中文标签 + 注释**
- **强调要点**
- **底部总结文字**(给图一个金句收尾)

**风格前缀**(由 references/styles/{style}.md 提供,**不要改风格本身**)——notebook 风格是黑绿红网格纸基线; infographic 风格是米白底蓝橙双色信息图基线; executive-tech 风格是深靛紫主色 + 卡片式 UI + 杂志化商务科技风; cozy-handdrawn 风格是米白纸感底 + 黑色手绘线条 + 粉彩圆角卡片 + 个人动画形象辅助叙事; tech-doodle 风格是暖白奶油底 + fine-liner 墨线笔触 + 极淡粉彩上色 + 极简火柴人 + 底部荧光笔金句; cartoon-infographic 风格是干净白底 + 手绘圆角容器 + 功能性柔和多色 + 可选 host 卡通形象。

### 第三步:注入风格并调用脚本生成

**3a. 注入风格前缀**

用 `scripts/inject_style.py` 把用户选择的风格前缀注入到 prompt 中:

```bash
# 先写好不含风格前缀的 manifest JSON(diagrams.json),然后注入:
python3 scripts/inject_style.py \
    --style {用户选择的风格} \
    --manifest diagrams.json
# 输出: diagrams-styled.json(已注入风格前缀的完整 manifest)
```

也支持单文件注入(用于重跑某张图):
```bash
python3 scripts/inject_style.py \
    --style notebook \
    --prompt-file diagram-01.txt
# 输出: diagram-01-styled.txt
```

**注意**:manifest JSON 中的 prompt 只写图表内容描述(不要写风格前缀),风格前缀由 `inject_style.py` 自动注入。`inject_style.py` 会自动处理重复注入(切风格重跑时去掉旧前缀)。

**3b. 调用 ai-image-generator 生成**

用 `ai-image-generator` skill 的脚本,传入注入风格后的 manifest:

```bash
python3 ../ai-image-generator/scripts/generate.py \
    --provider agnes \
    --manifest diagrams-styled.json \
    --output-dir ./diagrams/xxx \
    --parallel
```

脚本会:
1. 对每张图 POST 到 generation 接口,拿到 task_id
2. 轮询任务直到完成
3. 下载图片到本地
4. 保存每张图的 prompt 和元数据

**参数**:
- manifest 中的 `mode`: `generation`(纯文本生图)
- aspect_ratio: `16:9`(脚本默认值)
- resolution: `2K`(脚本默认值)

**鉴权**: 设置 `MULERUN_API_KEY` / `APIMART_API_KEY` / `ATLASCLOUD_API_KEY` / `AGNES_API_KEY` 之一；多个 key 时必须显式 `--provider`（例如 `--provider agnes`）。Agnes 会忽略 `resolution=2K`，输出为固定 size token。

#### Manifest JSON 格式(注入风格前)

在第二步写好图表内容描述后,生成如下 JSON(**不包含风格前缀**):

```json
{
  "mode": "generation",
  "items": [
    {
      "id": "diagram-01-profile-isolation",
      "prompt": "{图表内容提示词,不含风格前缀}"
    },
    {
      "id": "diagram-02-role-division",
      "prompt": "{图表内容提示词,不含风格前缀}"
    },
    {
      "id": "diagram-03-flow-with-character",
      "prompt": "{图表内容提示词,不含风格前缀}",
      "needs_character": true
    }
  ]
}
```

然后用 `inject_style.py --manifest diagrams.json --style notebook` 生成 `diagrams-styled.json`,再调 `ai-image-generator`。

#### 生成插图位置清单

脚本运行完成后,根据结果中的 item id 和第一步记录的插入位置信息,手动生成一份 `diagrams_manifest.md`:

```markdown
# 本次生成的插图 · 插入位置清单

## 插图 1: diagram-01-profile-isolation.png
**建议插入位置**:在"先聊聊 profile"这段后面

## 插图 2: diagram-02-role-division.png
**建议插入位置**:在"Step 1:建三个 Agent"小节开头
```

## 产物结构

```
diagrams/2026-04-21-hermes-multi-agent/
├── diagram-01-profile-isolation.png       # 第 1 张图
├── diagram-01-profile-isolation.txt       # 第 1 张图的提示词
├── diagram-02-role-division.png           # 第 2 张图
├── diagram-02-role-division.txt           # 第 2 张图的提示词
├── ...
└── diagrams_manifest.md                   # 插入位置清单
```

`diagrams_manifest.md` 长这样:

```markdown
# 本次生成的插图 · 插入位置清单

## 插图 1: diagram-01-profile-isolation.png
**建议插入位置**:在"先聊聊 profile,这是整个多 Agent 的基础"小节下,"底层实现其实挺朴素"这段后面

## 插图 2: diagram-02-role-division.png
**建议插入位置**:在"Step 1:建三个 Agent,分工明确"小节开头,列出三个 Agent 名字后

...
```

用户按这个清单把图插进文章就行。

## 常见翻车点和对策

| 翻车点 | 对策 |
|---|---|
| 中文字符渲染错乱 | Nano Banana 2 对中文支持比中文字符密度低的版本好,但仍建议关键文字用 **英文 + 中文** 双语标注;实在不行后期 PS 覆盖 |
| 图太花哨,脱离手绘风 | 提示词末尾反复强调 `clean minimal layout`、`hand-drawn sketch`、`no photographs`、`no 3D rendering` |
| 绿色红色用反了 | 绿色=正向/流程正确/增长,红色=强调/警告/关键要点。提示词里明确 `Green for positive, red for emphasis only` |
| 图之间风格不统一 | 所有图用同一个风格声明段落,只改主体内容 |
| 图和文章上下文脱节 | 每张图的"核心要表达"必须从文章原文里找依据,不能自由发挥 |

## 参考资料

- 风格模板:`references/styles/notebook.md`(手绘笔记本风) | `references/styles/infographic.md`(信息图风) | `references/styles/executive-tech.md`(现代高级科技商务风) | `references/styles/cozy-handdrawn.md`(温暖手绘卡片风) | `references/styles/tech-doodle.md`(技术简笔画风) | `references/styles/cartoon-infographic.md`(卡通信息图风) | `references/styles/whiteboard-sketch.md`(白板手绘风)
- 手绘图提示词结构化骨架:`references/prompt_template.md`
- 4 种图类型案例 + 1 个 `executive-tech` 风格完整案例:`references/examples.md`
- 通用图像生成脚本:`ai-teaching-media/ai-image-generator/scripts/generate.py`
