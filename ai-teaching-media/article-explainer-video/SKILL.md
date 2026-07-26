---
name: article-explainer-video
description: 把一篇技术长文/论文解读自动做成章节式解说视频(1080p, 5-8 分钟)。双主题:warm(奶油底+珊瑚红+cozy-handdrawn 透明插图,亲和感)和 midnight(深蓝黑底+琥珀金+宋体标题+executive-tech 插图,AI 科技感),storyboard 一个 theme 字段切换。每章三种 layout 混排:illustration(左文右图+Ken Burns)/grid(卡片网格逐块入场)/statement(全屏大字)。管线:文章 → 分镜 storyboard.json(6-10 章) → 每章插图(复用 tech-article-diagram + ai-image-generator,warm 需去底) → Minimax / Edge 逐句 TTS(默认自定义克隆音色) → HyperFrames 数据驱动渲染成 MP4。当用户说"文章转视频""把这篇文章做成视频""解说视频""文章讲解视频""图文解说""article to video"或给一篇长文要做成带配音的视频时使用。不用于:单概念教学动图(走 edu-teaching-animation)、视频封面(走 short-video-cover)、文章配图(走 tech-article-diagram)。
---

# 文章解说视频 (article → 章节式解说视频)

输入一篇技术长文(或一个可展开的主题) → 输出 1080p 章节式解说 MP4:

- **版式**: 每章三种 layout 可选, 混排制造节奏感——
  - `illustration`(默认): 左栏标题+要点卡+术语标签, 右栏 AI 插图(全章 Ken Burns 缓推缓拉)
  - `grid`: 右栏换成卡片网格, 每块跟旁白逐个长出来(步骤/对比/清单类章节用, 信息感强)
  - `statement`: 无右栏, 全屏大字判断句(≤3 句的短促章节用, 做呼吸点)
  - `terminal`: 右栏 macOS 风格终端窗口, 命令逐行打字机入场(讲 CLI 的章节用; HTML 直接渲染, 命令绝不会错字)
  - 底部逐句字幕 + 章节进度条 + 右上灰色大章号全 layout 通用
  - **8-10 章里建议 2-4 章用 grid/statement**, 全片全是大图会拖节奏, 完播率差
- **视觉**: cozy-handdrawn 温暖手绘系 — 奶油纸底、珊瑚红强调、低饱和粉彩、手绘偏移阴影卡片;插图用 tech-article-diagram 的 cozy-handdrawn 风格(edit 模式 + 可选角色参考图),页面配色与插图同族,整体统一
- **节奏**: 6-10 章、每章 30-60 秒、全片 5-8 分钟

## 管线总览 (5 步)

```bash
# 0. 写分镜 (必读 references/storyboard-guide.md)
#    读文章 → <project_dir>/storyboard.json: 每章 kicker/headline/subhead/card/tags/
#    narration(句子数组)/illustration.brief。分镜质量决定成片质量。

# 1. 插图 (需要任一生图 key: MULERUN/APIMART/ATLASCLOUD/AGNES; 多 key 请 --provider; 三个脚本跨 skill 复用)
python3 scripts/make_manifest.py <project_dir>                     # → diagrams.json
python3 ../tech-article-diagram/scripts/inject_style.py \
    --style cozy-handdrawn --manifest <project_dir>/diagrams.json  # → diagrams-styled.json
python3 ../ai-image-generator/scripts/generate.py \
    --manifest <project_dir>/diagrams-styled.json \
    --output-dir <project_dir>/images --parallel                   # → images/ch-NN.png

# 1b. 插图去底 (需要 Pillow) — 抠掉纯色背景, 透明 PNG 浮在页面上, 换背景直接兼容
python3 scripts/strip_background.py <project_dir>/images           # 原图备份到 images/raw/

# 2. 逐句 TTS
# 默认: storyboard.voice.provider → 有 MINIMAX_API_KEY 用 minimax, 否则 edge（需外网）
# pip install -r ../requirements-tts.txt
python3 scripts/tts_pipeline.py <project_dir> --provider edge       # → audio/ + timeline.json
# 续跑/指纹匹配跳过:
# python3 scripts/tts_pipeline.py <project_dir> --provider edge --skip-existing

# 3. 合成 index.html (全数据驱动, 不需要手写场景)
python3 scripts/scaffold.py <project_dir>                          # → index.html

# 4. 出片
bash scripts/build.sh <project_dir>                                # → renders/<name>.mp4 + 蒙太奇
```

注意 inject_style.py / generate.py 的路径按实际 skill 安装位置解析(它们分别属于
`tech-article-diagram` 和 `ai-image-generator`)。

环境: Node.js ≥22 + ffmpeg (`npx hyperframes doctor` 自检); 插图 key（`MULERUN_API_KEY` / `APIMART_API_KEY` / `AGNES_API_KEY` 等）。
配音可选: `MINIMAX_API_KEY` 或免费 Edge TTS（`pip install edge-tts`, **需外网**, 批量可能限流）。

## 主题 (storyboard 的 `theme` 字段)

| theme | 视觉 | 插图策略 |
|---|---|---|
| `warm`(默认) | 奶油纸底 + 珊瑚红 + 粉彩 | cozy-handdrawn + **去底**(透明浮空) |
| `midnight` | 深蓝黑底 + 琥珀金 + 宋体大标题(AI 科技风) | executive-tech + **不去底**(暗色相框) |

同一份分镜改 `theme` 字段即可换肤, 版式/动画/时间轴全部继承。差异只在第 1 步:
- warm: `inject_style.py --style cozy-handdrawn` → 生图 → `strip_background.py`
- midnight: `inject_style.py --style executive-tech` → 生图 → **跳过去底**(黑线手绘在深底上看不见, 深色设计图自带底色, 直接入框)

加新主题: 模板里复制一个 `body[data-theme="..."]` 变量块 + 选一个 tech-article-diagram 风格, 十分钟的事。

## TTS Provider（配音引擎）

未显式指定时优先级：

1. `storyboard.voice.provider`
2. 已设置 `MINIMAX_API_KEY` → `minimax`
3. 否则 → `edge`

| Provider | 费用 | 依赖 | 说明 |
|---|---|---|---|
| `minimax` | 付费 | `MINIMAX_API_KEY` | 高质量，模型 `speech-02-hd`；支持克隆音色 |
| `edge` | 免费 | `pip install edge-tts` + **外网** | Microsoft 在线 TTS；批量逐句易限流 |
| `say` | 免费 | macOS 内置 | 仅本地预览 |

```bash
# 免费 edge-tts
python3 scripts/tts_pipeline.py <project_dir> --provider edge --voice zh-CN-YunxiNeural
export EDGE_TTS_VOICE=zh-CN-YunxiNeural   # 仅覆盖默认音色（未指定 --voice / storyboard.voice_id 时）

# Minimax
export MINIMAX_API_KEY=...
python3 scripts/tts_pipeline.py <project_dir> --provider minimax --voice male-qn-jingying

# 指纹匹配才复用旧 mp3；改 provider/voice/speed/text 会自动重生成
python3 scripts/tts_pipeline.py <project_dir> --provider edge --skip-existing
```

storyboard.json 示例：
```json
{
  "voice": {
    "provider": "edge",
    "voice_id": "zh-CN-YunxiNeural",
    "speed": 1.05
  }
}
```

音色优先级：`--voice` > `storyboard.voice.edge_voice_id`/`minimax_voice_id` > 兼容 `voice_id` >（edge 时）`EDGE_TTS_VOICE` > 内置默认。
CLI 显式 `--provider edge` 时，不会把 Minimax 克隆音色（如 `host-voice-default`）直接传给 Edge；请配置 `edge_voice_id` 或 `EDGE_TTS_VOICE`。

Edge 常用中文音色：`zh-CN-XiaoxiaoNeural` / `zh-CN-XiaoyiNeural` / `zh-CN-YunxiNeural` / `zh-CN-YunyangNeural`。

语速范围：`0.5 ~ 2.0`。Edge 单句超时默认 60s（`EDGE_TTS_TIMEOUT`）。批量失败时用 `--skip-existing` 续跑，或切 `--provider minimax`。

## 配音音色

默认男声 `male-qn-jingying`(host 是男博主), 语速 1.05。在 storyboard.json 的 `voice` 块改。

**用自己的声音**: Minimax 支持声音克隆, 一次克隆终身可用:

```bash
# 录一段 10s~5min 的干净人声 (安静环境、无 BGM、自然语速, 3 分钟左右最佳)
python3 scripts/clone_voice.py my-voice.m4a --voice-id host-voice-default \
    --preview-text "大家好，欢迎收看本期内容。"
# 完成后把 voice_id 填进 storyboard.json 的 voice.voice_id
```

注意: 克隆音色首次合成时 Minimax 收一次性费用; 克隆声音只能用于本人授权的内容。

## 节奏

时间轴常量在 `tts_pipeline.py` 顶部: HEAD_PAD 0.7 / GAP 0.18 / TAIL_PAD 0.75。
右侧插图全章做 Ken Burns 缓推缓拉(奇偶章交替方向), 画面不会死停。
如果还嫌慢: 先提 `voice.speed`(1.05→1.15), 再砍 narration 句数, 不要去动模板动画时长。

## 为什么是逐句 TTS

narration 写成**句子数组**,每句单独 TTS。得到的句级时间轴同时驱动三件事:
1. **字幕逐句同步**(参考片效果,整段字幕会显得呆)
2. **要点卡条目锚定**: card.items 里的 `at: N` 表示该条目在第 N 句开口时入场
3. **改一句只重跑一句**: 改 narration 后指纹变化会自动重生成；也可用 `--skip-existing` 续跑未完成句子

## 迭代惯例

| 改了什么 | 重跑什么 |
|---|---|
| 某句旁白 | 改 storyboard 后 `tts_pipeline.py --skip-existing`（指纹不匹配会重生成）→ `scaffold.py` → `build.sh` |
| 某章插图 | 改 storyboard 的 brief → `make_manifest.py` → 注入+生成(只留要重跑的 item) → 直接 `build.sh` |
| 卡片/标题文案 | `scaffold.py` → `build.sh`(不用重跑 TTS) |
| 增删章节/句子 | 全链路重跑 (时间轴变了) |

## storyboard.json 结构 (完整规范见 references/storyboard-guide.md)

```json
{
  "topic": "j-lens",
  "title": "AI 没说出口的想法，第一次被直接读到了",
  "voice": { "provider": "minimax", "voice_id": "female-chengshu", "speed": 1.0 },
  "chapters": [
    {
      "id": 1,
      "kicker": "开场 / AI 黑箱",
      "headline": ["AI 没说出口的想法", "第一次被直接读到了"],
      "subhead": "Anthropic 的 J-lens，正在把模型内部的沉默概念变成可读信号",
      "card": {
        "title": "先记住这件事",
        "items": [
          { "label": "以前", "text": "只能看 AI 说了什么", "at": 2 },
          { "label": "现在", "text": "开始能看它没说什么", "at": 4, "bar": 0.7 }
        ]
      },
      "tags": ["J-space", "J-lens", "silent thoughts"],
      "narration": [
        "你大概会把自己跟AI的聊天记录翻出来，看看它到底说了什么。",
        "但你看到的，永远只是它说出口的那部分。"
      ],
      "illustration": {
        "id": "ch-01",
        "brief": "{插图内容提示词, 不含风格前缀, 写法见 storyboard-guide}"
      }
    }
  ]
}
```

## 产物结构

```
<project_dir>/
├── storyboard.json        # 分镜 (人工可改的唯一事实源)
├── diagrams.json          # 插图 manifest (make_manifest 产物)
├── diagrams-styled.json   # 注入 cozy-handdrawn 后
├── images/ch-NN.png       # 每章插图
├── audio/
│   ├── ch-NN-sNN.mp3      # 每句配音
│   └── timeline.json      # 章节+句级时间轴
├── index.html             # scaffold 产物 (勿手改, 改 storyboard 重新 scaffold)
├── renders/<name>.mp4     # 成片
└── preview/montage.png    # 每章中点蒙太奇 (渲染后必看)
```

## 质检清单

1. `build.sh` 内置 lint + validate;lint 必须 0 error
2. 渲染后**必看 `preview/montage.png`**: 每章有没有空插图/文字溢出/标题换行难看
3. 插图人工过一遍: host 形象是否走形、中文标注是否乱码(乱码就改 brief 里的文字为双语或重跑)
4. 抽两章听配音: 断句是否自然,数字/英文是否读对(读错就改 narration 写法,如 "J-lens" 写成 "J透镜")

## 实测坑

| 现象 | 对策 |
|---|---|
| 插图把风格词画成了画面文字(实测 "wobble" 出现在图里) | brief 里不要出现英文形容词式描述;发现后改 brief 重跑该张 |
| host 形象服装在多张图间漂移(灰T/紫T/黑T) | brief 里统一写死 "host 形象穿灰色T恤";一个视频 8-10 张连续出场比文章插图更显眼 |
| Minimax 逐句调用容易撞 RPM 限流 | tts_pipeline.py 已内置 1002 限流 21s 退避；也可改用 `--provider edge` 或 `--skip-existing` 续跑 |
| Edge 批量限流/网络超时 | 单句默认 60s 超时并重试；需外网；失败后可用 `--skip-existing` 续跑或切 minimax |
| `<audio>` 没有 id 渲染时静音 | scaffold.py 已自动生成 id,手改 index.html 时别删 |
| 去底把插图里的近白面板一起抠掉 | 泛洪只抠与边缘连通的色块;插图里若有大块 ≈背景色 的面板会被吃掉。brief 里给面板明确写粉彩底色(蓝/绿/紫/橙),或对个别图 `--tolerance 12` 重跑 |
| 本机代理(127.0.0.1:8899)自签证书导致 Minimax TLS 失败 | 脚本已默认绕过系统代理;需要走代理 `export MINIMAX_USE_PROXY=1` |

## 已知边界

- 要点卡条目 ≤4 条、text ≤18 字,超了会挤(模板不裁切,靠分镜自律)
- headline 每行 ≤11 个汉字,两行为宜
- 每章 narration 4-9 句、每句 ≤32 字(一行字幕)
- 插图纵横比固定 4:3,object-fit contain,别的比例也能放但会留白
- 模板无 silent 模式(这是解说片,无声没有意义)

## 资源

- `assets/template/index.html` — 数据驱动 HyperFrames 模板(占位符由 scaffold.py 填充)
- `scripts/make_manifest.py` — storyboard → 插图 manifest
- `scripts/tts_pipeline.py` — 逐句 Minimax / Edge / say TTS + 指纹缓存 + 时间轴
- `scripts/scaffold.py` — 合成 index.html
- `scripts/build.sh` — lint + render + 蒙太奇
- `references/storyboard-guide.md` — 分镜拆解规范(第 0 步必读)
- 跨 skill 依赖: `tech-article-diagram`(风格注入) + `ai-image-generator`(生图)
