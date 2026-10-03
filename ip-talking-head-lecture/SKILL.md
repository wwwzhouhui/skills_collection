---
name: ip-talking-head-lecture
description: IP 卡通数字人口播动画课件视频工厂。用 Remotion 把「一段逐字稿 + 一张 IP 形象图」变成一条成片：主讲 IP 以圆形头像常驻右下角讲课（待机浮动 + 口型开合 + 说话光环 + 声波条），主画面是自动排版的动画课件（封面 / 概念 / 步骤 / 对比 / 数据 / 总结 六套版式），底部居中烧录字幕并做跟读高亮，另有品牌水印与顶部进度条；配音走小米 MiMo 或火山引擎或 edge-tts，时长由实际音频反推所以音画字幕天然对齐，一条命令同时出 16:9 横屏与 9:16 竖屏；并自动产出各平台发布文案（含 YouTube 中英双语标题/描述与自动合并的章节时间轴）与中英双语字幕文件（SRT + VTT）。内置两套口播形象可一键切换：动物卡通（海老豹）与人物卡通（眼镜青年），也支持自己加形象。当用户说"做一条数字人口播视频 / 卡通数字人讲课 / IP 形象口播 / 右下角数字人 / 动画课件视频 / 把我的形象做成讲师 / talking head 讲解视频 / 换成人物卡通形象 / 换个数字人 / 写发布文案 / YouTube 描述和标签 / 中英双语字幕 / 时间轴字幕文件 / 视频号小红书抖音文案"，或要在本仓库新建一期、改课件版式、换 IP 形象或口型帧、切换动物/人物卡通形象、换配音音色、重出片、改画幅、出静帧看版式、导出字幕时使用。全链路本地：Remotion + ffmpeg + 小米/火山 TTS，不需要剪辑软件、不需要联网渲染。
description_zh: IP 卡通数字人口播动画课件视频工厂（Remotion + 小米/火山/edge TTS）。右下角圆形 IP 数字人讲课 + 六套动画课件版式 + 烧录字幕跟读高亮 + 横竖双画幅；内置动物卡通 / 人物卡通两套形象可切换；自动出各平台发布文案（YouTube 中英双语 + 章节时间轴）与中英双语字幕（SRT/VTT）。
display_name: IP 数字人口播视频工厂
category: video
version: 1.2.0
author: hailaobao666
agent_created: true
---

# ip-talking-head-lecture：IP 数字人口播动画课件出片

工具就是本仓库（下文 `<仓库>`），CLI 是 `<仓库>/bin/iph`，参数全在 `<仓库>/config.json`。每期内容在 `dirs.projects`（默认 `<仓库>/episodes/<日期 标题>/`），中间产物与成片在 `dirs.build`（默认 `<仓库>/build/<日期 标题>/`）。

**一句话概括工作流**：写一个 `script.json`（每场景一段 `narration` + `heading` + `kind` + `data`）→ `iph all` → 拿到 mp4。

细节按需翻 `references/`：

| 文件 | 讲什么 |
|---|---|
| `references/script-format.md` | `script.json` 全字段与六套版式的 `data` 结构（要写脚本就看这个） |
| `references/voices.md` | 小米 MiMo / 火山 / edge 三条 TTS 通道的差异、音色怎么选、报错速查 |
| `references/avatar.md` | 口播形象：内置两套（动物卡通 / 人物卡通）怎么切、新形象怎么加、三帧口型素材怎么准备（含 AI 生成口型帧的提示词写法） |
| `references/publish.md` | 发布文案与字幕：`publish` 段怎么写、YouTube 章节的 10 秒硬规则、中英字幕怎么对齐、各平台口径 |
| `references/delivery-qa.md` | 成片验收清单（机器 + 目视）与常见坑 |

## 视觉规格（出厂设定，改 `config.json` 就改片）

```
背景   浅色纸感（径向白→薄荷绿渐变）+ 缓慢漂浮的色块 + 极淡点阵
主色   品牌绿 #2f9e44（强调下划线、序号、高亮字、数字人光环）
字体   HarmonyOS Sans SC（标题）/ MiSans（正文）—— 都是本机已装字体
页眉   左上胶囊小标签 → 大标题 → 副标题；右上 "02 / 06" 场景进度
内容区 横屏 (104,296) 起 1316×592；竖屏 (72,330) 起 936×1030
数字人 横屏：圆形 340px，圆心 (1690,752)；竖屏：280px，圆心 (880,1520)
       形象可选：haibao=动物卡通（海老豹）｜human=人物卡通（眼镜青年）
字幕   底部居中深色圆角胶囊，普通白字 + **正在读的字用品牌色加粗**
品牌层 左下角「名称 · slogan」水印 + 右上角「✦ 博主名」角标（brand.corner）+ 顶部 5px 进度条
片尾卡 build 自动追加 outro 场景：标识图/手写博主名 + 品牌色划线 + slogan + 黄色便签 CTA（brand.endCard）
```

> 数字人**必须**压在右下角、且不与字幕条重叠；字幕条**必须**用深色底（浅色背景上纯白字会糊）。改 `config.json` 的 `layout.<画幅>` 调整位置。

## 硬规矩

1. **一处为主：`script.json` 是唯一手写源。** 旁白、版式、标题、数据全在里面。`timeline.json`、`字幕.srt`、`旁白稿.md` 都是生成物，不手改——改了下次 build 就被覆盖。想调时长就调旁白字数，**永远不要手填帧数或秒数**。
2. **时长是算出来的，不是写死的。** 每个场景时长 = `leadPadding(0.85s) + 该段配音实际时长 + tailPadding(0.7s)`，下限 `minSceneSeconds(3.2s)`。所以改一句旁白，整条片子自动重排，音、画、字幕三者天然对齐。
3. **先定旁白，再定 `data`。** 旁白是"念出来的话"（口语、短句、不写标点层级）；`heading` 是"屏上大字"（≤12 字）；`data` 是具体要点的短词。三者不要互相复制粘贴，否则画面只是在重复字幕。
4. **配音通道先自检。** 改过 `tts` 就跑到 `iph voice`：它回显引擎/端点/模型/音色并真合成一句，比出片到一半才报 `Unknown voice` 省事。三个引擎各有**自己**的音色字段（火山 `tts.voice` / 小米 `tts.mi.voice` / edge `tts.edge.voice`），互相顶替是最常见的配置坑。
5. **数字人是"贴着讲"，不是"念稿"。** 口型开合节奏由 `remotion/src/components/TalkingAvatar.tsx` 的伪随机音节函数驱动；素材只给一张图也能跑（退化为轻微挤压 + 光环 + 声波条），但**三帧口型（闭口/微张/张口）明显更像真人**。内置动物卡通（`haibao`）与人物卡通（`human`）两套形象，`iph avatars` 看列表、`iph preset <名>` 或 `--preset=<名>` 切换，见 `references/avatar.md`。
6. **交付：成片（横屏 + 竖屏）+ 字幕 + `旁白稿.md` + `发布文案.md`。** 字幕与发布文案是 `iph build` 的副产品，不额外花时间：中英各出 SRT + VTT 两版；发布文案含 YouTube 中英双语板块。给用户的回复里**直接贴主用标题 + 各平台描述**，不要只丢一句"任务已完成"。
7. **YouTube 章节必须满足「首条 00:00 ／ 至少 3 条 ／ 每条至少 10 秒」，任一条不满足整组章节都会被忽略。** 所以章节由分镜自动合并（`lib/publish.mjs` 的 `groupChapters`），**不要手写时间戳**——手写的那种改一句旁白就过期了。平台文案里的时间轴一律写 `{{chapters}}` 占位符。
8. **不联网渲染。** 字体用本机已装的中文字体，素材全部本地。Remotion 首次渲染会尝试下载 chrome-headless-shell；下载被拦时 `lib/render.mjs` 会自动改用本机 Playwright 已装的 Chromium。
9. **时间基准：`timeline.json` 里每个场景的 `cues` / `words` 时间都是「相对本场景起点」（秒）**，不是全局时间（`toSrt()` 导出时才补 `scene.start`）。消费它们的组件如果挂在顶层（`useCurrentFrame()` 拿到的是全局帧），就**必须自己加上 `scene.start`**——见 `IpLecture.tsx` 的 `toGlobal()`。改动这块务必**两个画幅都看、且至少抽一帧「非首场景」**：首场景 `start = 0`，会把所有偏移错误掩盖掉。
10. **英文字幕逐条复用中文字幕的时间轴**，所以 `publish.en.cues` 的条数必须与中文条数严格相等（`iph srt <期>` 可数）。**条数不符时 build 会跳过英文字幕并警告**，不会硬凑——错位的时间轴比没有更糟。

## 命令

```bash
I=<仓库>/bin/iph
$I new "<标题>"                    # 建期：<episodes>/<日期> <标题>/script.json（从模板复制）
$I list                            # 列出所有期
$I voice                           # 配音自检：回显档位 + 真合成一句
$I build <期>                      # 配音 + 生成时间轴 / 字幕（中英 × SRT/VTT）/ 旁白稿 / 发布文案
$I publish <期>                    # 同 build —— 只改了 publish 段时用这个，配音走缓存秒级完成
$I still <期> [秒]                 # 出静帧看版式 → <build>/<期>/work/out/still-*.png
$I render <期>                     # 渲染成片 → <build>/<期>/outputs/final-<画幅>.mp4
$I all <期>                        # build + render 一条龙
$I srt <期>                        # 只看字幕条时间与文本（核对断句，也可用来数英文条数）
$I kinds                           # 列出可用课件版式
$I avatars                         # 列出可用口播形象（含三帧齐不齐 + 当前默认）
$I preset <形象名>                  # 切换默认口播形象（写进 config.json）
$I open <期>                       # 打开期目录与后台目录
```

常用开关：`--ratio=16:9,9:16`（画幅，可只出一个）｜`--preset=human`（本条片子临时换形象）｜`--force-tts`（忽略配音缓存重配）｜`--scene=2`（只渲某个场景，快速看版式）｜`--still=2,12,25`（一次出多张静帧）。

`<期>` 可以是目录名或标题的任意子串，例如 `iph all 全流程`。

## 标准流程

```bash
I=<仓库>/bin/iph

# 1. 建期 + 写脚本
$I new "什么是大模型"
#    → 编辑 episodes/<日期> 什么是大模型/script.json
#      scenes[].narration 写"要念的话"，heading 写"屏上大字"，kind 选版式，data 填要点

# 2. 配音自检（换了音色才需要）
$I voice

# 3. 出片（横竖两版一起出）
$I all "什么是大模型"
#    → build/<日期> 什么是大模型/outputs/final-16x9.mp4
#    → build/<日期> 什么是大模型/outputs/final-9x16.mp4
```

## 六套课件版式

`kind` 决定画面怎么排；`data` 是各版式专属内容（完整字段见 `references/script-format.md`）。

| kind | 用在哪 | data |
|---|---|---|
| `cover` | 封面/开场：大标题 + 下划线 + 标签 | `eyebrow` `tags[]` |
| `idea` | 一个核心概念 + 2~4 个要点 | `center` `icon` `points[{title,text}]` |
| `steps` | 2~4 步流程，带序号徽章 | `items[{title,text,icon}]` |
| `compare` | 左右两栏对比 + VS 圆章 | `left/right{title,items[]}` |
| `numbers` | 1~3 个数据滚动 | `items[{value,unit,label,prefix}]` `note` |
| `recap` | 2~3 张总结卡 + 收尾 CTA | `items[{title,text}]` `cta` |
| `outro` | 片尾品牌卡（无配音，`brand.endCard.enabled` 时 build 自动追加，一般不用手写） | `name` `slogan` `cta` `logo`（由 config.brand 注入） |

`icon` 可选：`bulb` `chart` `chip` `layers` `chat` `rocket` `target` `book`（线描图标，见 `remotion/src/components/Icons.tsx`）。

**典型 60~80 秒片子的骨架**：`cover` → `idea` → `steps` → `compare` → `numbers` → `recap`。六段各 6~10 秒，合计约 250~320 字旁白。

**新增版式**：在 `remotion/src/scenes/index.tsx` 写一个组件 → 在文件末尾的 `SCENES` 里登记 → 在 `references/script-format.md` 补 `data` 结构。横屏走左右分栏、竖屏一律纵向堆叠（`layout.portrait` 判断）。

## 横竖屏怎么兼容

同一份 `script.json` 出两种画幅：`timeline.json` 按画幅各生成一份（`layout.<画幅>` 里的数字人位置与字幕高度不同），渲染前覆盖写进 Remotion 工程。版式组件用 `layout.portrait` 判断横竖屏：横屏多列横排，竖屏纵向堆叠 + 字号降一档。**新增版式时必须两种都试**（`iph still <期> 12 --ratio=9:16`）。

## 发布文案与字幕（`iph build` 自动产出）

`script.json` 里写一个 `publish` 段，build 时就会一起出文案与字幕，不额外花时间：

| 产物 | 内容 |
|---|---|
| `发布文案.md` | 主用标题 + **YouTube 中英双语**（标题 / 描述 / 标签 / 章节时间轴）+ 视频号 / 小红书 / 抖音 · B 站 / 公众号导语 |
| `字幕.srt` · `字幕.vtt` | 中文字幕（VTT 是 YouTube 更推荐的格式） |
| `字幕.en.srt` · `字幕.en.vtt` | 英文字幕（需填 `publish.en.cues`） |

三条要点：

- **YouTube 章节是自动算出来的**，不手写：首条 `0:00`、至少 3 条、**每章至少 10 秒**。60 秒 6 分镜的片子单个分镜往往只有 8~9 秒，直接按分镜写会被 YouTube **整组丢弃** —— 所以 `lib/publish.mjs` 的 `groupChapters()` 会自动把不足 10 秒的分镜并进当前章节。章节名取组内首个分镜的 `heading`，想精确控制就填 `youtube.chapterTitles` / `chapterTitlesEn`。
- **中英字幕共用同一条时间轴**：`publish.en.cues` 与中文字幕**逐条一一对应**（`iph srt <期>` 可以数条数）。条数不符时 build 会跳过英文字幕并打印警告 —— 错位的时间轴比没有更糟。
- **平台文案里的 `{{chapters}}`** 会被替换成**场景级**时间轴（不合并），永远跟随成片时长；写死 `00:08` 那种改稿后就会过期。抖音 / B 站文案建议一律用占位符。

完整字段与各平台写作口径见 `references/publish.md`。

## 品牌与形象

- 品牌名/slogan/主色/水印位置在 `config.json` 的 `brand`；每期可用 `script.json` 的 `brand` 覆盖。
- **右上角博主名角标**：`brand.corner.enabled`（默认真）+ `text`（留空用 `brand.name`）。改一处全片生效，片尾卡上不叠角标。
- **片尾品牌卡**：`brand.endCard.enabled`（默认真）时 build 在末尾自动追加一个无配音 `outro` 场景（`seconds` 卡片时长、`cta` 便签文案）。博主标识图放 `brand.logo`（png/jpg 路径，期目录 `assets/` 下同名文件优先）；没图就手写大字博主名 + 品牌色划线 + slogan。关掉：`"endCard": { "enabled": false }` 或本期 `script.json` 写 `"brand": { "endCard": { "enabled": false } }`。
- **口播形象有两套内置**，`config.json` 的 `avatar.presets` 登记、`avatar.preset` 选当前默认：

  | 预设名 | 形象 | 素材目录 |
  |---|---|---|
  | `haibao` | 动物卡通 · 海老豹 | `assets/avatars/haibao/` |
  | `human` | 人物卡通 · 眼镜青年 | `assets/avatars/human/` |

  ```bash
  $I avatars                      # 看列表（三帧齐不齐 + 当前默认打 *）
  $I preset human                 # 切默认形象（全局）
  $I all <期> --preset=human       # 只给这一期换，不动全局
  ```

  优先级：`--preset=` > `script.json` 的 `avatar.preset` > `config.json` 的 `avatar.preset` > 老式兜底路径。
  **形象信息是 build 时写进 `timeline.json` 的 —— 换完形象必须重新 build 才会出片**（`still/render` 带 `--preset=` 会自动先 build）。
- 每个形象目录里三帧同名文件：`image.*`（闭口）+ `mouth-mid.*`（微张）+ `mouth-open.*`（张口），扩展名不限。期专属形象放期目录 `assets/`，优先于预设目录。
- 加新形象 = 建一个目录放三帧 → 在 `config.json` 的 `avatar.presets` 登记一行（`label` / `dir` / `focus` / `scale`）→ `iph avatars` 确认。完整步骤与口型帧生成提示词见 `references/avatar.md`。

## 常见故障

| 症状 | 原因与处置 |
|---|---|
| `Unknown voice: xxx` | 三个引擎的音色字段混了。小米只有九个固定音色（`mimo_default/冰糖/茉莉/苏打/白桦/Mia/Chloe/Milo/Dean`） |
| `45000010 Invalid X-Api-Key` | 火山调用域打错（`ark-` 开头 Key 只认 `plan` 域），不是额度问题 |
| 字幕整句同时点亮、没有逐字跟读 | 正常：小米通道只有小句级时间戳。想要逐字高亮就把 `tts.engine` 换成 `volc` |
| `spawnSync ffprobe EBUSY` | 本机 Node 的**同步**进程调用不可用（本仓库已全部改成异步 `lib/tts/run.mjs`）。别在新代码里写 `execFileSync` |
| 递归删目录报 `SAFE_DELETE_BULK_GUARD_ERROR` | 本机 safe-delete 会拦批量删除。别用 `fs.rmSync(dir,{recursive:true})`，改成按文件名覆盖写入 |
| 渲染报 Chromium 相关错误 | 手动指定：`REMOTION_BROWSER=<chrome-headless-shell 路径> iph render <期>` |
| 渲染很慢 / 内存吃紧 | 把 `config.json` 的 `video.concurrency` 从 4 降到 2 |
| 数字人挡住字幕 | 调 `layout.<画幅>.avatar.y` 抬高，或调 `layout.<画幅>.subtitle.bottom` 让字幕更靠底 |
| `presets 里没有形象「xxx」` | 名字拼错或没登记。`iph avatars` 看可用列表 |
| 换了形象但成片还是旧的 | 形象是 **build 时**写进 `timeline.json` 的。跑 `iph build <期> --preset=xxx`（或干脆 `iph all`） |
| `iph avatars` 里底图显示 ✗ | 该形象目录没有 `image.*`（或主名不匹配）。见 `references/avatar.md` 的目录结构 |
| 没生成《发布文案.md》 | `script.json` 没写 `publish` 段（字幕仍会生成） |
| 警告 `publish.en.cues 有 N 条，但中文字幕是 M 条` | 英文字幕条数没对齐，已跳过。用 `iph srt <期>` 数中文条数后逐条补齐 |
| 发布文案里 `{{chapters}}` 原样印出来了 | 占位符拼错（两个半角花括号、大小写敏感） |
| 提示"分镜不足以凑出 3 个 ≥10 秒的章节" | 片子总长不足 30 秒，YouTube 章节用不上，描述里别放时间戳 |
| 中文变方块 | 缺中文字体。装 HarmonyOS Sans SC / MiSans / 思源黑体任一 |
