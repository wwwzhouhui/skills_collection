# script.json 全字段说明

`script.json` 是**唯一手写源**。改它 → `iph build` → 时间轴、字幕、旁白稿全部自动重排。

## 顶层字段

```jsonc
{
  "title": "什么是大模型",              // 片名，写进旁白稿标题
  "tone": "light",                      // light（浅色纸感，默认）| dark
  "brand": {                            // 可选，覆盖 config.json 的 brand
    "name": "海老豹666",
    "slogan": "AI 工具实测 · 讲人话",
    "accent": "#2f9e44"
  },
  "avatar": {                           // 可选：本期换口播形象 / 微调取景
    "preset": "human",                  // 用哪套形象（iph avatars 看列表；不给就用 config 的默认）
    "focus": "50% 24%",                 // 可选，覆盖该形象的取景对焦点（CSS object-position）
    "scale": 1.08                       // 可选，圆内放大倍数（想让脸更大就调大，默认 1.04）
  },
  "publish": { /* 见下 */ },             // 可选：各平台发布文案 + YouTube 双语 + 英文字幕
  "video":    { "ratios": ["16:9", "9:16"], "fps": 30, "crf": 18, "concurrency": 4 },
  "pacing":   { "leadPadding": 0.85, "tailPadding": 0.7, "minSceneSeconds": 3.2, "sceneGap": 0.2 },
  "cues":     { "maxChars": 20, "minChars": 6 },
  "scenes": [ /* 见下 */ ]
}
```

`video` / `pacing` / `cues` 都可以整块省略，省略就用 `config.json` 的值。

### pacing 怎么理解

| 字段 | 含义 | 调它的后果 |
|---|---|---|
| `leadPadding` | 场景开头先出画面、过多久配音才开口 | 太小会觉得"话赶画面"；太大场景间会空 |
| `tailPadding` | 说完留白多久 | 太小下一场景压得太紧；太大会拖 |
| `minSceneSeconds` | 场景最短时长 | 防止极短旁白造成一闪而过的镜头 |
| `sceneGap` | 相邻场景交叉重叠的秒数 | >0 时前后场景做交叉溶解，0 则硬切 |

## 场景字段

```jsonc
{
  "kind": "steps",                      // 版式，六选一（见下表）
  "narration": "第一步，给一张形象图。",   // 要念的话。留空 = 无配音场景（片尾卡）
  "heading": "你只需要做三件事",          // 屏上大字，建议 ≤12 字
  "kicker": "三步走",                    // 左上角胶囊小标签，可省
  "sub": "不用写分镜",                   // 副标题，可省
  "data": { /* 各版式专属，见下 */ },

  "leadPadding": 1.2,                   // 可选：只覆盖这一个场景
  "tailPadding": 0.5,
  "minSeconds": 4.0,
  "duration": 6,                        // 仅在 narration 为空时生效（决定片尾卡多长）
  "id": "scene-3"                       // 可选，音频文件名用它；不给就按顺序 scene-1、scene-2…
}
```

**写旁白的口径**：像说话，不像写文章。短句、口语、一次说清一件事。小米/火山都会按标点断句，
所以标点该用就用（`，` `。` 决定停顿）。别写 `（停顿）` 这类提示词——它不是 SSML。
不要在旁白里念标点符号本身，数字可以直接写阿拉伯数字（`100 积分`），TTS 会念对。

## 六套版式与 data

### `cover` — 封面/开场

```jsonc
"data": {
  "eyebrow": "AI 工具实测 · 第 1 期",     // 顶部胶囊
  "tags": ["脚本", "配音", "动画"]        // 标题下方的标签，第一个用品牌色
}
```
画面：大标题（横屏 132px / 竖屏 86px）+ 画出来的强调下划线 + 副标题 + 标签。
标题居中占上半屏，避开右下角数字人。

### `idea` — 一个核心概念 + 要点

```jsonc
"data": {
  "center": "生产线",                    // 左侧圆章上的短词（建议 ≤4 字）
  "icon": "layers",                     // 圆章里的线描图标
  "points": [
    { "title": "Miora", "text": "生成角色、场景与动态素材" },
    { "title": "Remotion", "text": "用代码控制位置、时间与转场" }
  ]                                        // 2~4 个
}
```
横屏：左圆章 + 右侧带连接竖线的序号卡；竖屏：圆章在上、卡片纵向堆叠。

### `steps` — 流程/步骤

```jsonc
"data": {
  "items": [
    { "title": "给一张形象图", "text": "用来锁住角色一致性", "icon": "target" }
  ]                                        // 2~4 个
}
```

### `compare` — 左右对比

```jsonc
"data": {
  "left":  { "title": "传统生成", "items": ["不满意只能重新抽", "改一个字要重做全片"] },
  "right": { "title": "代码驱动", "items": ["逐帧可改、可反复渲染", "换脚本就换片"] }
}
```
右栏用品牌色高亮（"更好"的那一栏放右边）。中间是 VS 圆章。

### `numbers` — 数据滚动

```jsonc
"data": {
  "items": [
    { "value": 60, "unit": "秒", "label": "成片时长" },
    { "value": 100, "prefix": "<", "unit": "积分", "label": "消耗上限" },
    { "value": 1.5, "decimals": 1, "unit": "倍", "label": "语速" }
  ],                                       // 1~3 个
  "note": "同一份工程还能一键出横屏和竖屏两版"   // 可选，底部小字
}
```
第一个数字自动用品牌色。`prefix` 会显示在数字前面（如 `<100`）。

### `recap` — 总结 + 收尾

```jsonc
"data": {
  "items": [
    { "title": "形象图锁角色", "text": "同一套素材，跨镜头不跑形" }
  ],                                       // 2~3 个
  "cta": "一句话，就是一条片子"            // 底部大字
}
```

### `outro` — 片尾品牌卡（一般不用手写）

`config.json` 的 `brand.endCard.enabled`（默认真）时，`iph build` 会在末尾**自动追加**一个无配音
`outro` 场景：博主标识图（`brand.logo`，没图则手写大字 `brand.name`）+ 品牌色划线 + slogan + 黄色便签 CTA。

```jsonc
"data": {
  "name": "海老豹666",              // 手写大名（build 从 brand.name 注入）
  "slogan": "AI 工具实测 · 讲人话",  // 划线下方小字
  "cta": "点赞 · 关注 · 评论区聊聊", // 黄色便签文案，留空不出便签
  "logo": "brand/logo.png"          // 标识图（public/ 相对路径，build 从 brand.logo 拷入）
}
```

时长用场景的 `duration` 字段（无配音时生效），默认 `brand.endCard.seconds`（4.2s）。
本期不想出片尾卡：`script.json` 写 `"brand": { "endCard": { "enabled": false } }`。
右上角的「✦ 博主名」角标走 `brand.corner`（`text` 留空用 `brand.name`，`enabled:false` 关闭）。

## 一条片子的骨架建议
| 时长 | 字数（@1.15x 小米） | 场景 | 骨架 |
|---|---|---|---|
| 30 秒 | 约 130 字 | 3 | cover → idea → recap |
| 60~80 秒 | 约 250~320 字 | 5~6 | cover → idea → steps → compare → numbers → recap |
| 2 分钟 | 约 550 字 | 8~10 | 上面基础上拆细 + 再来一组 steps/compare |

**别把一段旁白写太长。** 单个场景超过约 15 秒，画面会显得停在原地。
拆成两个场景（换版式）比在一个场景里堆内容好看得多。

## publish（发布文案 + 双语字幕）

可选的整块。写了它，`iph build` 就会一并产出 `<期>/发布文案.md` 和四个字幕文件（中英 × SRT/VTT）。

```jsonc
"publish": {
  "title": "主用标题（全平台通用）",
  "titles": ["备选标题 1", "备选标题 2"],          // 可选

  "videoAccount": "视频号 / 朋友圈文案。多段用 \n\n 分隔",
  "xiaohongshu": "小红书文案（含 #话题）",
  "douyin": "抖音 / B 站文案\n\n{{chapters}}",     // {{chapters}} → 场景级时间轴
  "articleLead": "公众号导语",

  "tags": ["AI工具", "WorkBuddy"],                 // 通用标签
  "hashtags": "#AI视频 #AIGC",

  "youtube": {
    "title": "中文标题",
    "titleEn": "English title",
    "desc": "中文描述正文（章节会自动追加在后面）",
    "descEn": "English description body",
    "tags": ["AI video", "Remotion"],
    "cta": "中文行动引导",
    "ctaEn": "English call to action",
    "chapterMinSeconds": 10,                       // YouTube 硬性下限，别调低
    "chapterTitles": ["章节名 1", "..."],           // 与 scenes 一一对应，不给就用 heading
    "chapterTitlesEn": ["Chapter 1", "..."]
  },

  "en": { "cues": ["English line 1", "..."] }      // 英文字幕，与中文字幕逐条对应
}
```

三条要记牢：

- **`en.cues` 的条数必须等于中文字幕条数**（不是分镜数）。用 `$I srt <期>` 数一下 —— 条数不符会**跳过英文字幕并打印警告**（错位的时间轴比没有更糟）。
- **YouTube 章节是自动合并的**：不足 10 秒的分镜会被并进上一章，因为 YouTube 要求每章 ≥10 秒，不满足则**整组章节失效**。所以它和各平台文案里的 `{{chapters}}`（场景级、不合并）条数不同，是正常的。
- **平台文案里的时间轴一律写 `{{chapters}}` 占位符**，不要手写 `00:08` 这类时间戳 —— 改一句旁白就过期了，占位符会自动跟随成片时长。

各平台写作口径、英文翻译口径、YouTube 上传步骤：`references/publish.md`。

## 改完必查

```bash
I=<仓库>/bin/iph
$I srt <期>                    # 字幕断句对不对、时间有没有重叠
$I still <期> 12               # 横屏第 12 秒
$I still <期> 12 --ratio=9:16  # 竖屏第 12 秒（竖屏版式和横屏不同，两种都要看）
```
