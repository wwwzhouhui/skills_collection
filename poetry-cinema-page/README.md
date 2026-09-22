# poetry-cinema-page · 沉浸式古诗词网页生成技能

> **一句话**：给它一首中国古典诗、词、曲或古风散文诗，它走完「文学分镜 → 视觉圣经 → 逐张生图 → 朗诵配音 → 滚动网页 → 浏览器验收 →（可选）口播视频」整条生产线，交付一个**真正可运行的电影感页面**，而不是一张网页草图。
>
> 图像双服务商：火山引擎方舟 Doubao Seedream 5.0（`pro` / `lite`）与第三方 GPT-Image 网关（`gpt-2` / `gpt-2.5`），四档位可按段落混用，主视觉参考链跨服务商不断。

---

## 目录

- [它能做什么](#它能做什么)
- [工作原理](#工作原理)
- [目录结构](#目录结构)
- [环境依赖](#环境依赖)
- [配置与密钥](#配置与密钥)
- [使用方法](#使用方法)
- [命令行参考](#命令行参考)
- [服务商与模型](#服务商与模型)
- [语音引擎与音色](#语音引擎与音色)
- [口播视频](#口播视频)
- [常见问题](#常见问题)
- [版本记录](#版本记录)

---

## 它能做什么

输入一首诗（最多再加几句偏好），输出一条完整交付链：

- ✅ **文学分镜**：核对作品与异文，按空间、时间、人物、动作、修辞与情绪转折拆成 5–8 个视觉段落，而不是机械地每两句配一张图
- ✅ **统一视觉圣经**：朝代、地理、人物、服饰、色彩、光线与镜头语言先锁死；主视觉用文生图定调，之后每张图都以它作图生图参考，人物与地理不会漂移
- ✅ **双服务商生图**：一份 `plan.json` 跑完整首诗，可按档位混用服务商；已完成的图重跑时自动跳过
- ✅ **联系表强制检查**：生成后输出 `contact-sheet.html`，未经人工检查的图不允许进页面
- ✅ **沉浸式滚动页面**：固定图片舞台、双层交叉淡入、克制视差、章节导航；桌面端文案卡片不超半屏，移动端 `contain` 主图 + 模糊全屏背景
- ✅ **文学解读**：逐段直译、关键词与动词节奏解释、对照 / 时间线 / 情绪刻度等微型视觉组件，收尾给出体式、意象系统与核心张力
- ✅ **朗诵配音**：两个引擎 23 个中文音色，输出音轨 + 逐行时间轴 sidecar + SRT 字幕，页面内置自动播放与可访问的朗读开关
- ✅ **口播视频（可选）**：Remotion 渲染 1920×1080/30fps，每段一镜的克制运镜、硬切双层级字幕、片头片尾字卡、胶片颗粒与暗角，确定性渲染

---

## 工作原理

```
输入诗词
  → ① 检查项目（框架 / 构建脚本 / 路由 / 未提交文件）
  → ② 核对原文与异文，写出文学分镜（scene-map）
  → ③ 建立视觉圣经：时代、地理、人物、色彩、镜头语言、禁止项
  → ④ 文生图出主视觉（hero），再以它为参考逐段图生图（scene-1…n）
  → ⑤ 联系表检查：人物一致性、时代错误、意外文字、风格漂移
  → ⑥ 生成朗诵音轨（edge-tts 或豆包 seed-tts）+ 时间轴 sidecar + SRT
  → ⑦ 实现滚动页面并接入音频，保留始终可用的朗读开关
  → ⑧ 生产构建 + 真实浏览器 QA（桌面 / 移动端 / 音频 / 控制台 / prefers-reduced-motion）
  → ⑨（可选）video-plan.json → Remotion 渲染口播视频
```

三条不可动摇的规则：

1. **参考链优先**——除主视觉外每张图都必须带 `ref`，这是把整套图锁成同一个世界的唯一机制
2. **不静默改原文**——用户给的文本原样呈现，有意义的异文单独说明，不在正文里标注
3. **视频层不生产内容**——口播视频只复用已有场景图、人声与设计 tokens，唯一「创作」的是运镜

---

## 目录结构

```text
poetry-cinema-page/
├── SKILL.md                        # 技能入口：8 步必需工作流 + 质量红线
├── README.md                       # 本文件
├── agents/
│   └── openai.yaml                 # 技能元信息（显示名、默认提示词）
├── config/
│   ├── ark.config.json             # 唯一配置入口：图像 + 语音 + 视频
│   ├── ark.local.json              # 火山方舟本地密钥（不进仓库）
│   └── gpt-image.local.json        # GPT-Image 网关本地密钥（不进仓库）
├── references/                     # 按需加载的参考文档，共 6 篇
│   ├── poetry-analysis.md          # 原文保护、分镜边界、解读标准
│   ├── image-direction.md          # 视觉圣经与提示词写法
│   ├── ark-api.md                  # 两个图像服务商的完整 API 参考
│   ├── narration.md                # 配音引擎、命令与报错排查
│   ├── page-pattern.md             # 页面结构、响应式策略与 QA 清单
│   └── video.md                    # 口播视频流水线
├── assets/
│   ├── page-template/              # Vite / TypeScript / CSS 页面模板
│   └── video-template/             # Remotion 口播视频工程模板
│       ├── remotion.config.ts
│       └── src/
│           ├── index.ts / Root.tsx / PoemVideo.tsx
│           ├── timeline.generated.ts     # 由 scripts/video.py build 生成
│           └── lib/                      # 运镜 / 字幕 / 字卡 / 颗粒 / 转场
├── scripts/
│   ├── ark_image.py                # probe / t2i / i2i / batch
│   ├── narration.py                # voices / probe / audition / say / build
│   ├── video.py                    # probe / init / build / still / render / frames / run
│   └── extract_imagegen_results.py # 遗留兜底（仅 Codex 内置 ImageGen）
└── examples/
    └── jiang-jin-jiu/              # 完整示例：李白《将进酒》（纯文本产物）
        ├── scene-map.md            # 文学分镜与视觉圣经
        ├── plan.json               # 方舟生图计划（hero + 7 段，带 ref 参考链）
        ├── plan-gpt.json           # 同题网关计划（提示词相同，档位换 gpt-2.5）
        ├── narration.txt / narration-poem.json
        ├── video-plan.recitation.json     # 口播视频：朗诵版
        ├── video-plan.with-meaning.json   # 口播视频：讲解版（原文 + 释义）
        └── index.html / styles.css / page.js / poem-config.js / compare.html
```

---

## 环境依赖

| 依赖 | 要求 | 用途 |
| --- | --- | --- |
| Codex / Claude Code | 能发现本地 Skills | 运行环境 |
| Python | 3.8+ | 三个 CLI |
| 图像服务商密钥 | 至少一个（方舟 和／或网关） | 生图 |
| edge-tts | `pip install edge-tts` | 免费本地配音 |
| ffmpeg | 含 ffprobe | 配音拼接、转码、时长测量 |
| Node.js + Remotion 4 | 18+，`npm install` | 口播视频（可选） |
| Chrome / Edge | 本机已安装 | Remotion 渲染浏览器（自动探测） |
| 前端项目 | Vite + TypeScript 为默认模板 | 页面宿主，会优先复用当前技术栈 |

---

## 配置与密钥

所有可调项集中在 `config/ark.config.json`：

- `image.provider` 默认服务商；`image.providers.<名称>` 配接口地址、超时、重试、参考图传输方式与尺寸限制
- `models` 四个档位对应的服务商与模型 ID；`routing` 决定 hero / beat 走 `pro`、draft / repair 走 `lite`
- `defaults` 默认角色、档位、尺寸（`2560x1440`）、`response_format`、`watermark`
- `size_presets`：`web_16_9` / `web_16_9_1080` / `square` / `portrait` / `auto`
- `narration` 引擎、音色、采样率、行间与段间停顿、响度归一化
- `video` fps、分辨率、交叉溶解帧数、颗粒强度、片尾时长、离线 `node_modules` 复用

**密钥不进 `ark.config.json`**（该文件会提交）。解析顺序：

1. 环境变量：`ark` → `ARK_API_KEY`，`gpt-image` → `GPT_IMAGE_API_KEY`
2. 本地覆盖文件：`config/ark.local.json` / `config/gpt-image.local.json`（已在 `.gitignore` 中）
3. 配置块里的 `api_key` 字段——仅本地临时试验

```json
{ "api_key": "ark-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" }
```

---

## 使用方法

在 Codex / Claude Code 中直接说人话：

```text
使用 $poetry-cinema-page，把李白《将进酒》制作成沉浸式页面。
使用 $poetry-cinema-page，把苏轼《定风波·莫听穿林打叶声》制作成电影感沉浸式网页。
使用 $poetry-cinema-page，在当前 Vite 多页面项目中新建《蜀道难》页面，保留已有诗词页面并互相添加导航。
使用 $poetry-cinema-page，把《琵琶行》做成适合高中生阅读的沉浸式页面，解释关键动词、音乐描写和情绪转折。
使用 $poetry-cinema-page，把王维《山居秋暝》制作成留白克制的摄影风景页面，不要仙侠感。
使用 $poetry-cinema-page，把《将进酒》的页面再做成一支口播视频。
```

开工前先自检凭据，避免把时间浪费在无效密钥上：

```bash
python scripts/ark_image.py probe          # 免费：不生成图片，只验证地址与密钥
python scripts/narration.py probe          # 会真的念一句，非零成本；加 --dry-run 只报告
python scripts/video.py probe              # 渲染链路自检
```

---

## 命令行参考

### `scripts/ark_image.py`

```bash
python scripts/ark_image.py probe
python scripts/ark_image.py t2i   --prompt "<提示词>" --out public/generated/<slug>/hero.jpg
python scripts/ark_image.py i2i   --prompt "<提示词>" --ref public/generated/<slug>/hero.jpg --out public/generated/<slug>/scene-1.jpg
python scripts/ark_image.py batch --plan plan.json
```

常用参数：`--config PATH`、`--tier pro|lite|gpt-2|gpt-2.5`、`--provider NAME`、`--model NAME`、`--size WxH|预设名`、`--role hero|beat|draft|repair`、`--n N`、`--out-dir DIR`、`--name NAME`、`--dry-run`、`--json`。

batch 计划（主视觉必须排在引用它的段落之前）：

```json
{
  "out_dir": "public/generated/<poem-slug>",
  "images": [
    {"name": "hero",    "role": "hero", "prompt": "..."},
    {"name": "scene-1", "role": "beat", "ref": ["hero"], "prompt": "..."}
  ]
}
```

跑完会在 `out_dir` 写入 `prompts.json`（请求与响应记录）和 `contact-sheet.html`（联系表）。

### `scripts/narration.py`

```bash
python scripts/narration.py voices      # 打印音色目录，* 标记当前音色
python scripts/narration.py audition    # 同一句话用整份目录各念一遍，并写出试听页
python scripts/narration.py say   --text "君不见，黄河之水天上来" --out public/audio/x.mp3
python scripts/narration.py build --text-file narration.txt --out public/audio/x.mp3 --srt public/audio/x.srt
```

`build` 的朗诵稿格式：`#` 开头是注释，空行分段（段间停顿更长），其余每行单独朗读。产物是音轨 + 同名时间轴 `x.mp3.json`（逐行 `start` / `end` / `duration`）+ SRT。

### `scripts/video.py`

| 子命令 | 作用 |
| --- | --- |
| `probe` | 渲染链路自检 |
| `init` | 建 Remotion 工作区，支持离线复用现成 `node_modules` |
| `build` | 从 video-plan.json + 配音 sidecar 生成帧级时间轴 |
| `still` | 逐镜头静帧验收 |
| `render` | 整片渲染 |
| `frames` | 成片抽帧回看 |
| `run` | 一条龙到成片 |

---

## 服务商与模型

| 服务商键 | 类型 | 是什么 | 密钥环境变量 | 本地密钥文件 |
| --- | --- | --- | --- | --- |
| `ark` | `ark` | 火山引擎方舟 Doubao Seedream | `ARK_API_KEY` | `config/ark.local.json` |
| `gpt-image` | `openai-images` | GPT-Image 网关（第三方，OpenAI 兼容） | `GPT_IMAGE_API_KEY` | `config/gpt-image.local.json` |

| 档位 | 服务商 | 模型 ID | 默认用途 |
| --- | --- | --- | --- |
| `pro` | `ark` | `doubao-seedream-5.0-pro` | hero / beat |
| `lite` | `ark` | `doubao-seedream-5.0-lite` | draft / repair |
| `gpt-2` | `gpt-image` | `gpt-image-2` | 按需指定 |
| `gpt-2.5` | `gpt-image` | `gpt-image-2.5` | 按需指定 |

档位是唯一决定服务商的东西，所以一首诗里混用是正常操作。方舟尺寸较严，`2560x1440` 是两个方舟档位共同接受的唯一 16:9 尺寸；网关保留请求的宽高比（16:9 统一归一到 1672×941）。

**网关的几个坑**（详见 `references/ark-api.md`）：

- 图生图必须走 multipart `/images/edits`，参考图放名为 `image` 的字段；传给 `/images/generations` 会被静默忽略，返回 200 却生成一张全新文生图
- 必须带浏览器 UA（Cloudflare 拦截，缺 UA 直接 1010）
- 参考图上传前会压到 `reference_max_edge`（1536 px）
- 网关稳定性较差，`max_retries` 已提到 5；**重跑同一条 batch 计划**就是官方补救方式，已完成的不重复生成
- 它的模型 ID 无法用免费 `probe` 验证，只有 `probe --live` 能证明

---

## 语音引擎与音色

| 引擎 | 是什么 | 密钥 | 原始输出 | 默认音色 |
| --- | --- | --- | --- | --- |
| `edge-tts` | 微软 edge-tts，本地合成 | 不需要 | mp3 | `zh-CN-YunxiNeural` |
| `doubao-seed-tts` | 火山引擎豆包 `seed-tts-2.0` | 复用 Ark 密钥 | wav（转码为 mp3） | `zh_male_qingcang_uranus_bigtts` |

内置 23 个中文音色：

- **edge-tts（8 个）**：云希（默认）、云扬、云健、云夏、晓晓、晓伊 + 辽宁话、陕西话
- **doubao-seed-tts（15 个）**：男声 8（青苍、深夜播客、儒雅青年、温暖阿虎、liufei、渊博小叔、少年自信、阳光青年），女声 7（vv、xiaohe、清新女声、高冷御姐、邻家女孩、柔美女友、魅力女友）

另有 3 个音色被排除（不属于 `seed-tts-2.0`，会返回 `55000000 resource ID is mismatched`）。

**先试听再定音色**：音色 ID 说明不了听感，跑一次 `narration.py audition` 再填配置。

---

## 口播视频

```bash
python scripts/video.py probe
python scripts/video.py run --plan examples/jiang-jin-jiu/video-plan.recitation.json \
                           --workspace <你的输出目录>/video
```

产物：`out/<slug>.mp4`；验收静帧在 `out/qa/`，成片抽帧在 `out/qa_extracts/`。

- **先有人声，后有镜头**：权威时间轴来自 `narration.py build` 的逐行 sidecar，镜头边界钉在两句之间的静默中点
- **双层级字幕**：原文行 64px 衬线大字，释义行 42px 小一号，判定靠「这句话是否出现在原诗里」
- **确定性渲染**：禁 `Math.random()`，伪随机全部固定种子，两次渲染逐帧一致
- 离线环境用配置里的 `video.node_modules` 指向任何已装 `remotion@4` 的目录

---

## 常见问题

**必须两个服务商密钥都配吗？**
不必，至少一个即可。只配方舟就默认走 `pro` / `lite`；想在某首诗里用网关再补 `GPT_IMAGE_API_KEY`。

**没有图像密钥能先试流程吗？**
可以。页面模板、edge-tts 配音和视频流水线都不依赖图像密钥，`--dry-run` 只报告不发请求。

**为什么不直接让模型生成一个网页？**
难点不是单次写 HTML，而是让文本、解读、图像世界、滚动节奏和移动端构图彼此一致。这个 Skill 把容易遗漏的检查固化成了流程。

**生成的图要再压缩吗？**
方舟返回的就是 2560×1440、约 250–500 KB 的 JPEG，已在交付预算内；网关返回约 2 MB 的 PNG，需要更小体积时再派生 WebP/AVIF。

**会覆盖已有页面吗？**
不会。明确要求新建路由或独立 HTML 入口，并在多页面项目中补充导航。

**能用于现代诗吗？**
可以尝试，但当前分析规则、体式说明和视觉方向主要针对中国古典诗、词、曲与古风长诗。

---

## 版本记录

### v1.0.0（2026-09）

- ✅ 发布 `poetry-cinema-page`：文学分镜、视觉圣经、双服务商生图、沉浸式滚动页面、朗诵配音、浏览器验收
- ✅ 图像双服务商四档位，支持同首诗内混用，主视觉参考链跨服务商成立
- ✅ 配音双引擎，内置 23 个中文音色与试听页
- ✅ 口播视频流水线：Remotion 1920×1080/30fps，确定性运镜、双层级硬切字幕、片头尾字卡、胶片颗粒与暗角
- ✅ 完整示例《将进酒》：分镜文档、两套生图计划、朗诵稿、两支口播视频计划
- ✅ 配套文档：`SKILL.md` + 6 篇 `references`
