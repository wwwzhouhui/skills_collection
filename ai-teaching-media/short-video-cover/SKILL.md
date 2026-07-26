---
name: short-video-cover
description: |
  根据视频口播文案,为视频号/抖音/小红书短视频生成 3:4 竖版封面图。当用户需要给短视频做封面、配缩略图、出竖版题图时使用。触发词包括:做视频封面、生成视频封面图、视频号封面、抖音封面、小红书视频封面、竖版封面、3:4 封面、短视频题图。即使用户只是说"帮我给这个视频做个封面"或"封面还没做",只要上下文涉及短视频发布,都应该触发。通过 ai-image-generator 的 edit 模式生成(默认 MuleRun Nano Banana 2, 也可切换 APImart/Atlas/Agnes),以主持人参考图为参考图,提供 11 种可选视觉风格(默认深色科技标题风),产出符合短视频平台爆款规律的竖版封面图。不要用于公众号宽幅题图(2.35:1)、朋友圈九宫格、头像、海报等非 3:4 短视频封面场景；本 skill 只处理 3:4 竖版短视频封面。
---

# 短视频封面图生成(3:4 竖版)

为视频号/抖音/小红书短视频一键生成 3:4 竖版封面图,走 ai-image-generator edit 模式,以主持人参考图为参考图,产出符合短视频平台爆款规律的封面。

## 本 skill 的适用范围

本 skill 只生成 **3:4 竖版短视频封面**,用于视频号/抖音/小红书等平台的短视频缩略图。

| 维度 | 本 skill 的固定范围 |
|---|---|
| **比例** | 3:4 竖版(API 走 3:4,1080×1440) |
| **使用场景** | 视频号/抖音/小红书短视频缩略图 |
| **视觉风格** | 11 种可选(默认黑底暗网格 + 青蓝黄高对比 + 巨型标题主导) |
| **文字位置** | 中部 2-3 行巨型标题 + 顶部 hook 条 + 底部标签 |
| **人物表情** | **稳定且自信微笑**,看镜头,像导师分享技巧 |
| **UI 元素** | **暗色工作流截图 + Agent 对话碎片 + 结果缩略图** |

**触发判断**:
- 用户提"视频""抖音""视频号""小红书视频""竖版""3:4""缩略图" → 走本 skill
- 用户提"公众号""文章题图""宽幅""2.35:1" → **不要触发本 skill**

## 什么时候触发这个 skill

明确触发场景:
- 用户说「给这个视频做个封面」「视频封面图」「视频号封面」
- 用户说「抖音封面」「小红书视频封面」「短视频题图」
- 用户说「竖版封面」「3:4 封面」「9:16 封面」
- 用户写完口播稿后问「视频封面怎么办」「封面还没做」
- 任何与"短视频发布前最后一步配图"相关的场景

不要触发的场景:
- 公众号宽幅文章封面(2.35:1 横幅题图)
- 朋友圈九宫格
- 头像、logo、海报
- 视频内贴图、字幕条等非缩略图素材

## 核心流程

这个 skill 分五步执行(第零步到第四步),**每一步都有质检点,不通过不往下走**。

### 第零步:选风格

生成提示词之前,先问用户选哪种封面风格。列出 `references/style_catalog.md` 里的 11 种风格,让用户选一种:

| 编号 | 风格名 | 对应模板 |
|---|---|---|
| 1 | **深色科技标题风** | `references/styles/dark-tech-title.md` |
| 2 | **明亮 YouTuber 风** | `references/styles/bright-youtuber.md` |
| 3 | **双屏对比叙事风** | `references/styles/split-screen-narrative.md` |
| 4 | **产品主视觉风** | `references/styles/product-hero.md` |
| 5 | **拼贴信息飓风** | `references/styles/collage-info-storm.md` |
| 6 | **工作台场景风** | `references/styles/workspace-scene.md` |
| 7 | **故障警示风** | `references/styles/glitch-warning.md` |
| 8 | **Agent 号召风** | `references/styles/agent-hype.md` |
| 9 | **卡片展示人设风** | `references/styles/card-showcase.md` |
| 10 | **萌宠代码风** | `references/styles/cute-mascot.md` |
| 11 | **手持设备展示风** | `references/styles/device-showcase.md` |

**用户不选时,默认走风格一(深色科技标题风)。**

选定风格后,读取 `references/styles/{风格}.md` 的完整模板,并始终遵守 `references/brand_baseline.md` 中的品牌基线。

选定风格后,所有后续填空都按该风格的模板执行,不要跨风格混用元素。

### 第一步:读懂口播,提炼封面素材

把视频口播文案吃透,从中抽出六个关键素材:

1. **主标题(顶部大字)** —— 4-8 字,**必须是"人话"不能用行话**。把文案的核心痛点用最大众的词重写。例如:
   - ❌ "接了API不能联网?"(行话)
   - ✅ "Claude 不能上网了?"(人话)
2. **副标题(底部大字)** —— 4-6 字,给出**承诺/解决方案**。例如"10秒解决""一键搞定""3步搞定"
3. **辅助小标题(主标题下方)** —— 6-12 字,补充上下文。例如"Claude Desktop · 避坑指南""保姆级教程"
4. **UI 元素叙事(画面中间的视觉故事)** —— 必须是**"问题→解决"的双截图对比**:
   - 元素 1:**报错/失败状态**截图(主导视觉)
   - 元素 2:**成功状态**截图(辅助,体积更小)
   - 两者用箭头连接,讲一个"❌ → ✅"的转变故事
5. **表情**:**稳定使用"自信微笑、看镜头、像导师"**——绝不用惊讶/瞪眼/夸张表情,因为 host 的人设是"踏实分享干货",不是"震惊体博主"
6. **手势** —— **不必和参考图保持一致**,根据风格/构图自然选择。例如:深色科技标题风用"食指轻抬指向标题",产品主视觉风用"手指向 UI",双屏对比风用"双手分指左右"。`references/brand_baseline.md` 里有完整手势选项。

**关键判断:主标题是不是人话?**

把主标题给一个**完全不懂技术的人**看,他能秒懂吗?
- "API"、"Token"、"Webhook"、"协议" → 不是人话,要重写
- "不能上网"、"用不了"、"找不到"、"搜不到" → 是人话

如果不确定,问自己:"我妈/我老婆能看懂吗?"

### 第二步:按模板生成完整提示词

根据第零步选定的风格,到 `references/styles/{风格}.md` 读取对应风格的提示词模板,把第一步提炼的素材填进去。所有风格都必须遵守 `references/brand_baseline.md` 中的品牌基线。

**关键坚持——品牌基线(不管什么风格都不能动)**:

- **画幅**:3:4 竖版(API 用 3:4)
- **人物**:以 `references/host_ref_face.png` 为准的本账号主持人形象(默认手办形象),半身出镜;用户可替换该文件
- **表情默认**:**自信微笑、看镜头**,坚决排除"惊讶/瞪眼/夸张"(除非故障警示风需要稍严肃,但也不允许震惊)
- **标题原则**:必须是人话,4-8 字主标题,技术行话必须翻译成大众词汇
- **视觉层级默认**:标题是第一主角,人物占 20-30%,不抢戏
- **水印**:右下角"@wwwzhouhui",白字描边
- **参考图固定**:默认本地 `references/host_ref_face.png`(当前维护者手办形象),edit 模式保持五官一致;不要再使用外部旧作者 URL

**关键坚持——风格一(深色科技标题风)的默认视觉(其他风格按 catalog 模板替换)**:

- **背景色调**:深色科技感,但**不要把背景写死成同一个黑底模板**;可以按主题改成暗色工作台、暗色 UI 画布、暗色渐变、暗色拼贴
- **主视觉**:2-3 行巨型中文标题,必须是画面第一主角
- **手势**:一只手轻微抬起,食指向上提示重点,不要抢标题戏份
- **标题颜色**:青蓝 #00D4FF + 白字青描边 + 亮黄 #FFD93D 的三段式组合
- **信息层**:顶部 hook 条 + 中部 UI 碎片 + 底部标签,但都只能服务主标题

**可以每篇不同的部分**:
- 选定的风格
- 顶部/底部标题文字
- 辅助小标题
- UI 截图的具体内容(根据视频主题改)
- 报错文字内容
- 背景具体色调和场景(在风格允许的范围内)

### 第三步:调用 ai-image-generator 生成图片

使用 `ai-image-generator` skill 的脚本,传入完整提示词:

```bash
python ../ai-image-generator/scripts/generate.py \
  --provider agnes \
  --mode edit \
  --prompt-file ./prompt.txt \
  --image "references/host_ref_face.png" \
  --blocklist references/blocklist.txt \
  --aspect-ratio 3:4 \
  --name-tag video-cover-{视频关键词} \
  --output-dir ./video-covers
```

脚本会自动完成:创建 edit 任务 → 轮询结果 → 下载图片 → 保存 prompt 和元数据。

**参数固定值**:
- 参考图:默认 `references/host_ref_face.png`(本 skill 包内本地主持人参考图;用户可替换为自己的形象)
- `--mode edit`(必须)
- `--aspect-ratio 3:4`
- resolution: `2K`(脚本默认值)
- `--output-dir ./video-covers`(**当前工作目录**下的 `video-covers/`,不要把生成结果写进 skill 目录)

**鉴权**:
鉴权走 `ai-image-generator`：设置 `MULERUN_API_KEY` / `APIMART_API_KEY` / `ATLASCLOUD_API_KEY` / `AGNES_API_KEY` 之一；多个 key 时必须显式 `--provider`。Agnes 示例：`export AGNES_API_KEY=...` 后加 `--provider agnes`。注意 Agnes 忽略 `--resolution`，按 aspect_ratio 映射固定 size。

**批量生成注意**:
不同 provider 限流策略不同。MuleRun 同时活跃任务通常不宜过多；`--manifest --parallel` 大批量时建议分批。edit 模式偶尔一次返回 2 张变体(文件名带 `-0`/`-1` 后缀),属正常现象,自检时两张都看一眼选更好的。

### 第四步:读图自检(生成后必做)

生成的 PNG 必须用 Read 工具读回来看一遍,对照下面的清单逐项检查,不合格就按"常见翻车点与对策"表修改提示词重跑:

1. **标题文字**:主标题/副标题/标签逐字核对,有无错字、重复字、缺字(如"无法访问无法访问外部网络"这种重复)
2. **表情**:是否自信微笑看镜头(故障警示风允许专注严肃,但不能是不悦/冷漠/震惊)
3. **水印**:右下角"@wwwzhouhui"是否存在
4. **层级**:标题是否第一主角,人物是否只占 20-30%,副标题有没有压在关键 UI 或人脸上
5. **UI 元素**:关键短语(报错横幅/开关名)是否清晰可读;长句乱码若太显眼,重跑时按 brand_baseline 的"文字渲染与乱码控制"要求模糊化

自检通过才把结果交给用户;只有小瑕疵时,把瑕疵和重跑建议一并说明。

## 生成完毕后

脚本会自动把 `.png`(图片)、`.txt`(提示词)、`.json`(API 元数据)三个同名文件保存到 `--output-dir` 指定的 `./video-covers/`(当前工作目录下),命名格式为 `{name-tag}-{时间戳}`,无需手动另存。

给 host 的反馈信息要包括:
1. 图片文件路径
2. 如果图片有问题(文字糊/表情不对/UI 元素被弱化),建议微调哪个参数
3. 如果要重跑,告诉他改哪段提示词

## 常见翻车点与对策

| 翻车点 | 原因 | 对策 |
|---|---|---|
| 表情夸张/瞪眼 | 提示词没明确排除惊讶情绪 | 明确写 "NOT shocked, NOT wide-eyed" + 描述目标情绪"confident mentor smile" |
| 主标题用了行话(API/Token) | 第一步提炼时偷懒 | 必走"人话检查":你妈能看懂吗?看不懂就重写 |
| 背景看起来像同一张图反复换字 | 把背景模板写死了 | 明确写 "background must be newly composed for this topic, not reused 1:1"，只固定色系和层级,不固定具体构图 |
| UI 截图太小看不清 | 提示词没强调主导视觉 | 写 "headline dominates, UI supports the title"，UI 可倾斜/裁切/模糊做氛围层 |
| 整体太亮/像 YouTuber 缩略图 | 还在沿用旧版暖色背景词 | 明确写 "dark layered background, charcoal/blue-black base, cyan glow accents" |
| 人物太大抢戏 | 提示词没限制人物比例 | 明确写 "subject relatively small, bottom 20-25% only, text dominates 3-4x more than person" |
| 标签和小图太杂 | 把信息元素都做成主角了 | 强调 "all secondary elements are decorative/supporting only" |
| 标题出现错字/重复字 | 中文文字块没加渲染保护 | 每个中文文字块后追加 "Render every Chinese character EXACTLY as written, no duplicated or missing characters"(11 风格实测 0 错字) |
| UI 截图里长句乱码 | 让模型渲染超过短语长度的中文 | 可读文字只放 ≤8 字短语;长文本明确要求 "blur or fade long body text into unreadable soft texture" |
| 副标题压在关键内容上 | 没给副标题预留空位 | 写明 "reserve a clear zone for the subtitle; must not overlap key UI or the subject's face" |

## 参考资料

- 风格目录索引:`references/style_catalog.md`
- 品牌基线与通用填空指引:`references/brand_baseline.md`
- 11 种风格完整提示词模板:`references/styles/{dark-tech-title,bright-youtuber,split-screen-narrative,product-hero,collage-info-storm,workspace-scene,glitch-warning,agent-hype,card-showcase,cute-mascot,device-showcase}.md`
- 已验证案例(Claude 联网避坑封面):`references/examples.md`
- 通用图像生成脚本:`ai-teaching-media/ai-image-generator/scripts/generate.py`
