# ip-talking-head-lecture · IP 数字人口播动画课件视频工厂

把「**一段逐字稿 + 一张 IP 形象图**」变成一条成片：主讲 IP 以圆形头像常驻**右下角讲课**，主画面是**自动排版的动画课件**，底部**烧录字幕并逐字跟读高亮**，配音可选小米 MiMo / 火山引擎 / edge-tts。一条命令同时出 **16:9 横屏**与 **9:16 竖屏**。

内置**动物卡通**与**人物卡通**两套口播形象，一条命令切换，也可以加自己的。

顺手还出**发布文案**（YouTube 中英双语标题 / 描述 / 自动章节时间轴 + 视频号 / 小红书 / 抖音 / 公众号）和**中英双语字幕文件**（SRT + VTT，共用同一条时间轴）。

不需要剪辑软件，不需要联网渲染，不需要手算时长。

```
script.json  ──►  TTS（小米/火山）  ──►  timeline.json  ──►  Remotion  ──►  final-16x9.mp4
  ↑ 你只写这个        实际音频时长          音画字幕唯一真相        渲染           final-9x16.mp4
                                                                └──►  字幕.srt/.vtt（中英）
                                                                      发布文案.md
```

## 快速开始

```bash
I=bin/iph

$I new "什么是大模型"        # 建期，生成 script.json 模板
#  → 编辑 episodes/<日期> 什么是大模型/script.json
#    scenes[].narration = 要念的话 ；heading = 屏上大字 ；kind = 版式 ；data = 要点
$I voice                     # （换过音色才需要）配音自检
$I all "什么是大模型"         # 出片
```

产物：

```
build/<日期> 什么是大模型/
├── outputs/final-16x9.mp4     ← 横屏成片
├── outputs/final-9x16.mp4     ← 竖屏成片
└── work/{audio,out,timeline-*.json}
episodes/<日期> 什么是大模型/
├── script.json                ← 唯一手写源（含 publish 段）
├── 旁白稿.md                   ← 每场景起止秒 + 旁白
├── 发布文案.md                 ← 各平台文案（YouTube 中英双语 + 章节时间轴）
├── 字幕.srt / 字幕.vtt         ← 中文字幕（剪映可编辑 / 上传 YouTube）
└── 字幕.en.srt / 字幕.en.vtt   ← 英文字幕（与中文共用同一条时间轴）
```

## 命令

| 命令 | 作用 |
|---|---|
| `iph new "<标题>"` | 建期（从模板复制 `script.json`） |
| `iph list` | 列出所有期 |
| `iph voice` | 配音自检：回显引擎/端点/音色 + 真合成一句 |
| `iph build <期>` | 配音 + 生成时间轴 / 字幕（中英 × SRT/VTT）/ 旁白稿 / 发布文案 |
| `iph publish <期>` | 同 build —— 只改了 `publish` 段时用（配音走缓存，秒级） |
| `iph still <期> [秒]` | 出静帧看版式（支持 `--still=2,12,25` 一次多张） |
| `iph render <期>` | 渲染成片 |
| `iph all <期>` | build + render 一条龙 |
| `iph srt <期>` | 列出字幕条时间与文本（核对断句 / 数英文字幕条数） |
| `iph kinds` | 列出可用课件版式 |
| `iph avatars` | 列出可用口播形象（三帧齐不齐 + 当前默认） |
| `iph preset <形象名>` | 切换默认口播形象 |
| `iph open <期>` | 打开期目录与后台目录 |

开关：`--ratio=16:9,9:16`｜`--preset=human`（本条片子临时换形象）｜`--force-tts`｜`--scene=2`（只渲一场）｜`--still=2,12,25`

## 六套课件版式

| kind | 画面 | 典型用途 |
|---|---|---|
| `cover` | 大标题 + 画出来的下划线 + 标签 | 开场 |
| `idea` | 核心概念圆章 + 带连接线的要点卡 | 抛一个概念 |
| `steps` | 带序号徽章的流程卡 | 讲步骤 |
| `compare` | 左右两栏 + VS 圆章 | 讲区别 |
| `numbers` | 数据滚动（缓出） | 摆事实 |
| `recap` | 总结卡 + 收尾 CTA | 收尾 |

版式是**组件**：在 `remotion/src/scenes/index.tsx` 加一个组件、在文件末尾的 `SCENES` 登记即可，横竖屏两种布局都要照顾到。

## 数字人是怎么"说话"的

只有句子/逐字时间轴，没有音素级口型数据，所以用**三层信号**叠出可信感：

1. **口型开合** —— 闭口 / 微张 / 张口 三帧交叉淡入，节奏由伪随机音节函数驱动（约 6.5~9.5 Hz 漂移，不是匀速正弦，否则像抽搐）。只给一张图会自动退化为"轻微挤压"。
2. **身体** —— 待机浮动（3.4s 一周期）+ 说话时更大振幅的起伏 + ±1.2° 摆动，下半脸随音节轻微下压。
3. **说话指示** —— 外圈脉冲光环 + 跨在圆边上的声波条，句子之间自动收。

素材准备（含用 AI 生成口型帧的提示词写法）见 `references/avatar.md`。

## 发布文案与双语字幕

`script.json` 里写一个 `publish` 段，`iph build` 会一并产出（不额外花时间）：

```jsonc
"publish": {
  "title": "主用标题",
  "videoAccount": "视频号 / 朋友圈文案…",
  "xiaohongshu": "小红书文案…",
  "douyin": "抖音 / B 站文案…\n\n{{chapters}}",   // 自动换成时间轴
  "youtube": {
    "title": "中文标题", "titleEn": "English title",
    "desc": "中文描述…", "descEn": "English description…",
    "tags": ["AI video", "Remotion"]
  },
  "en": { "cues": ["English line 1", "…"] }       // 与中文字幕逐条一一对应
}
```

两件事是**自动**的：

- **YouTube 章节时间轴** —— 从分镜时间算出来，并把不足 10 秒的分镜并进上一章。YouTube 要求「首条 00:00 / 至少 3 条 / **每条至少 10 秒**」，任一条不满足**整组章节会被直接丢弃**；60 秒片子的单个分镜通常只有 8~9 秒，按分镜直写必挂。
- **中英双语字幕** —— `en.cues` 逐条复用中文字幕的时间轴（同一份时间码，只换文本）。条数不符会跳过英文并打印警告 —— 错位的时间轴比没有更糟。`iph srt <期>` 能逐条列出中文条数供对照。

各平台文案里写 `{{chapters}}` 会被替换成**场景级**时间轴（不合并），永远跟随成片时长，不会像手写时间戳那样改稿后过期。

完整字段与各平台写作口径见 `references/publish.md`。

## 文档

| 文件 | 讲什么 |
|---|---|
| `SKILL.md` | 工作流、硬规矩、视觉规格（给 AI 看的操作手册） |
| `references/script-format.md` | `script.json` 全字段 + 六套版式的 `data` 结构 |
| `references/voices.md` | 三条 TTS 通道差异、音色怎么选、报错速查 |
| `references/avatar.md` | 口播形象：两套内置怎么切、新形象怎么加、三帧口型素材准备 |
| `references/publish.md` | 发布文案与字幕：`publish` 段、YouTube 章节规则、中英字幕对齐 |
| `references/delivery-qa.md` | 成片验收清单与常见坑 |

## 口播形象：两套内置，可切换

| 预设名 | 形象 | 风格 |
|---|---|---|
| `haibao` | 海老豹 | 动物卡通（雪豹崽 · 浅蓝底） |
| `human` | 眼镜青年 | 人物卡通（3D 渲染 · 绿底 · 格纹毛衣） |

```bash
iph avatars                      # 看列表：三帧齐不齐、当前默认是哪个
iph preset human                 # 切换全局默认形象
iph all "什么是大模型" --preset=human   # 只给这一期换，不动全局
```

也可以在某一期的 `script.json` 里写死 `"avatar": { "preset": "human" }`。
优先级：`--preset=` > `script.json` > `config.json` 默认。

> 形象信息是在 **build 时**写进 `timeline.json` 的，换完形象要重新 build 才会出片（`iph still/render` 带 `--preset=` 会自动先 build）。

### 加一套自己的形象

1. 把形象裁成**头肩半身正方形图**（脸的焦点约在画面上 45%），存到 `assets/avatars/<新名>/image.png`
2. 准备 `mouth-mid.png`（微张）与 `mouth-open.png`（张口）—— 用 AI 图生图效果最好，提示词写法见 `references/avatar.md`
3. 在 `config.json` 的 `avatar.presets` 里登记一行：`{ "label": "...", "dir": "assets/avatars/<新名>", "focus": "50% 24%", "scale": 1.04 }`
4. `iph avatars` 确认三列都是 ✓

只想给某一期换脸（不动全局），把三帧丢进该期的 `assets/` 目录即可，同名优先于预设目录。

## 环境要求

- Node 22+（Remotion 4.0.484 + React 19），`remotion/node_modules` 需就位（`npm install`，或从别的 Remotion 工程拷一份）
- ffmpeg / ffprobe 在 PATH 里
- 中文字体：HarmonyOS Sans SC / MiSans / 思源黑体任一（用于标题与正文）
- 首次渲染会自动获取 Chromium；下载被拦时会自动改用本机 Playwright 已装的 `chrome-headless-shell`

### 本机环境的两条硬约束（已在本仓库内绕过）

- **Node 的同步进程调用不可用**：`execFileSync` / `spawnSync` 一律 `EBUSY`（连 `cmd /c echo` 都起不来），异步 `spawn` 正常。所有外部命令走 `lib/tts/run.mjs`。
- **批量删除被 safe-delete 拦截**：`fs.rmSync(dir, {recursive:true})` 会报 `SAFE_DELETE_BULK_GUARD_ERROR`。素材一律按文件名覆盖写入，不做目录清理。

渲染时若看到 `PROGRAM BLOCKED BY SECURITY POLICY - WMIC.exe`，**属正常噪音**（Remotion 探测本机编辑器进程），不影响出片。

## 授权

MIT
