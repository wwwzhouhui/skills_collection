# 小米 MiMo TTS：端点、参数与时间轴

`config.json` 的 `tts.engine` 设成 `"mi"` 才走这条通道，凭证在 `.env` 的 `MI_TTS_API_KEY`（token-plan 的 `tp-` 开头 Key）。
改完先跑 `wb voice` —— 它会回显档位并真合成一句到 `build/_voice-check.wav`，试听即知音色对不对。

初次接入请先读第二节的三条「坑」：**小米和火山的参数规矩几乎处处不同**，拿火山的经验套会连着踩。

## 一、接口形态

```
POST  {baseUrl}/chat/completions          baseUrl 默认 https://token-plan-cn.xiaomimimo.com/v1
Authorization: Bearer <MI_TTS_API_KEY>
{
  "model": "mimo-v2.5-tts",
  "messages": [
    { "role": "user",      "content": "语速偏快、语气轻松" },   // 可选，只当风格指令
    { "role": "assistant", "content": "要朗读的正文" }          // 必须，正文放在这里
  ],
  "audio": { "voice": "冰糖", "format": "wav" }
}
→ choices[0].message.audio.data = base64 音频
```

- **只有这一个入口。** `/audio/speech` 和 `/tts` 都返回 openresty 的 HTML 404；`/models` 可用（用来核对模型名）。
- 同一域名下还有 `mimo-v2.5-asr`（语音识别）、`mimo-v2.5-tts-voiceclone`（声音复刻，要额外传参考音频）、`mimo-v2.5-tts-voicedesign`（音色设计，要给 user 消息写音色描述）——**都不是本通道用的**，选错模型会拿到对应的 `Param Incorrect`。
- `format` 支持 `wav` / `mp3` / `pcm` / `pcm16`（`opus`、`aac` 不支持）。本仓库固定 `wav`（24kHz 单声道 16bit），少一次转码。
- 也支持 `stream: true`（SSE，`delta.audio.data` 分片），但**流式同样没有时间戳**，对出片没用。

## 二、三条和火山完全不同的规矩

### 1. 正文必须放在 `assistant` 角色的 content 里

只给 `user` 消息会报 `messages must contain an assistant role for TTS model`。这类「语音设计」模型的通例是：**user 描述音色与风格，assistant 是模型要"说"的话**。`lib/tts/mi.mjs` 已按此构造；`tts.mi.style`（或 `.env` 的 `MI_TTS_STYLE`）填了才会带上 user 消息。

### 2. 没有语速参数

顶层 `speed`、`audio.speed`、`audio.speech_rate` **全部被接口忽略**。实测证据：同一个 Key、同一段文本，`audio.speed=0.5` 与完全不传返回的**字节数完全相同**（506924B / 17 个 token），而 `speed=2` 反而更长——差异纯属合成随机性（同一文本两次实测可差 0.5s 上下）。

所以 `config.json` 的 `tts.speed` 对小米通道是**本地 ffmpeg `atempo` 后处理**（保持音高，实测时长误差 ≤ 0.014s），见 `lib/tts/mi.mjs` 的 `atempoChain()`（超过 2 倍会自动串联多个 atempo）。同理 `tts.loudness` 走 `volume=` 滤镜；小米输出已经接近满刻度（实测 max_volume ≈ -0.2dB），**调大音量会削波**，一般别动。

### 3. 不返回逐字时间戳

`audio.transcript` 恒为 `null`，流式也没有时间事件；连 `mimo-v2.5-asr` 都只回文本、不给时间。**火山那套「拿引擎逐字时间戳排字幕」在这里行不通。**

本仓库的做法（`lib/tts/mi.mjs` → `estimateWords`）：

1. 把正文按标点切成小句（与 `lib/captions.cjs` 的 `splitText` **逐字一致**，所以两边小句数天然相等，字幕配对走"数量一致"分支）。
2. 先按规范化字数比例分配各小句的起止时间。
3. `ffmpeg silencedetect` 找出真实停顿区间，用**单调 DP** 把小句边界吸附到停顿上。停顿区间取**两个端点**：前一句在停顿**开始**处结束、后一句在停顿**结束**处开始，字幕就不会盖住静音。
4. 保底时长兜底，杜绝出现 0.05s 的"句子"。
5. **标点集合不含顿号**（`ALIGN_VERSION = 3`，2026-09-29 实测加）。顿号是并列顿开，TTS 在它上面的停顿**弱且不稳**：实测 28 处顿号边界里 10 处在音频里根本没有 ≥0.10s 的停顿，DP 无锚点可吸附、只能按字数插值，把「做 PPT 都行」这类小句的起点推早了 1.16s；而 ，。？！；： 的平均停顿是 0.27~0.36s，锚点可靠。去掉顿号后这些并列项并进相邻小句，两端都落在真实停顿上。**改这个集合必须同时改 `lib/captions.cjs` 的 `PUNCT` / `splitText`（两边必须逐字一致，否则配对数不等会整体退化成等比）并把 `ALIGN_VERSION` +1**（它进了缓存键，不 +1 会一直命中旧时间轴）。

**实测质量**（5 段真实旁白、1.2 倍速）：各句"字/秒"的变异系数 0.144，有声覆盖 81%，0 个退化句、0 处重叠、字数覆盖率 100%。

**字幕锚定率**（2026-09-29，35 场景实测口径）：`node lib/diag-captions.mjs <期目录>` 可以量化字幕与语音的贴合度——它用 `silencedetect` 取真实有声区间，逐条算覆盖率、起点偏移，并统计有多少条字幕的起点**正好落在语音小句边界上**（锚定）而不是靠字数插值。本期调优后：79 条字幕 **100% 锚定**，起点偏移中位数 −0.08s（那 0.08s 就是 `captions.leadSeconds` 的有意提前量）。**判据：锚定率越接近 100% 越好；出现"长小句被 maxChars 硬拆"的条目就是插值来源**——要么把 `captions.maxChars` 放大到能装下最长小句，要么给那句旁白补个逗号，别让它被拆。

> ⚠️ 两处容易改错的地方，改之前先看一眼：
> - **静音阈值 `-35dB/0.10s` 是实测选出来的，别凭直觉调灵敏。** 用"各句语速一致性"做指标扫过一圈：`-35/0.10 → 0.144`（最好）、`-38/0.08 → 0.152`、`-40/0.10 → 0.152`、`-45/0.06 → 0.197`、`-50/0.03 → 0.344`。**越灵敏越差**：多检出的停顿会被 DP 认领，反而把切分带偏；而漏检的短停顿只是优雅退回字数比例。
> - **配对必须用单调 DP，不能按距离贪心。** 先验自带 ±0.3s 噪声，某个先验可能正好落进停顿里而抢先认领，把相邻边界挤到下一段停顿，**整条链错位一格**——实测出现过"9 个字的句子只分到 0.28s"。

场景侧会记下时间轴来源，便于分辨：`work/audio/<scene>.json` 里 `align` 为 `silence-estimate`（可能带 `@1.2x`）。火山那边是 `native`（引擎逐字时间戳）。

## 三、九个音色（2026-09-29 实测全部可用）

| 音色 | 实测时长* | 听感取向 |
|---|---|---|
| `mimo_default` | 5.60s | 默认声线，语速偏快 |
| `冰糖` | 5.76s | 女声，清爽（本仓库默认） |
| `白桦` | 5.76s | 男声，偏沉稳 |
| `Dean` | 5.76s | 英文男声 |
| `茉莉` | 6.08s | 女声，轻柔 |
| `苏打` | 6.08s | 中性偏年轻 |
| `Mia` | 6.08s | 英文女声 |
| `Milo` | 6.40s | 英文男声，语速偏慢 |
| `Chloe` | 6.72s | 英文女声，最慢 |

\* 同一句 31 字「大家好，我是海老豹666。今天用一个视频，把 MCP 讲清楚。」的原始时长。**音色会影响语速与停顿习惯**，换音色请连同字幕一起重出。

音色只有这九个，写错一个字符就会报 `Unknown voice`（而且**报错里会列全部可选值**，照抄即可）：

```
Param Incorrect: Unknown voice: alloy. Available voices:
[mimo_default, 冰糖, 茉莉, 苏打, 白桦, Mia, Chloe, Milo, Dean]
```

## 四、排查速查

| 现象 | 真正原因 | 处理 |
|---|---|---|
| `404` + HTML（openresty） | baseUrl 或路径不对 | 只有 `{baseUrl}/chat/completions` 一个入口；`/audio/speech`、`/tts` 都是 404 |
| `Param Incorrect: Unknown voice: X` | 音色名不在九个之内 | 从第三节表里挑，或照报错里列出的 `Available voices` |
| `messages must contain an assistant role` | 正文放进了 user 消息 | 正文必须是 `assistant` 的 content（本仓库已实现） |
| `user message content must not be empty for voice design model` | 模型选成了 `mimo-v2.5-tts-voicedesign` | 普通合成用 `mimo-v2.5-tts` |
| `audio must not be empty for voice clone model` | 模型选成了 `mimo-v2.5-tts-voiceclone` | 同上 |
| `invalid audio format, only mp3/flac/m4a/wav/ogg are supported` | 把音频发给了 ASR 模型 | `mimo-v2.5-asr` 只做识别；合成用 `mimo-v2.5-tts` |
| `Unsupported audio format: opus` | `format` 不在允许集合内 | 用 `wav` / `mp3` / `pcm` / `pcm16` |
| `401` / `403` | Key 无效、过期或没余量 | 核对 `.env` 的 `MI_TTS_API_KEY` |
| `429` | 限流 | 等几秒重试（本仓库逐段串行合成，一般不会撞上） |

以上错因的识别与提示都写在 `lib/tts/mi.mjs` 的 `explainMiFailure()` 里，`wb tts` 遇到凭证/授权/音色类错误会**直接抛出**、不做 4 次无意义重试（`lib/tts-volc.mjs` 的 `HARD_FAIL`）。429 是例外的"值得重试"。

## 五、缓存

音频缓存键包含 `文本 + 引擎 + baseUrl + model + 音色 + 风格 + 语速 + 音量`。换音色、改语速（`atempo` 倍率变了）都会自动重配，不用手删音频；要强制重配全部用 `FORCE_TTS=1 wb tts <期>`。

## 六、和另外两条通道怎么选

| | 火山 `volc` | 小米 `mi` | edge `edge` |
|---|---|---|---|
| 字幕时间轴 | **引擎逐字时间戳（最准）** | 静音检测估算（实测边界误差约 0.05s，语速一致性 CV 0.144；调优后锚定率可达 100%） | 引擎逐字时间戳 |
| 语速控制 | 原生 `speech_rate`（不改时长结构） | 本地 `atempo` 后处理 | 引擎原生 rate |
| 音色数量 | 官方 2.0 十余个 + 声音复刻 | 固定九个 | 微软 Azure 全量 |
| 风格指令 | `context_texts`（仅 2.0） | user 消息自然语言 | 无 |
| 成本 | 按字符计费 | 按 token-plan 套餐 | 免费 |
| 适用 | 默认主力，字幕最省心 | 需要这几个音色、或换一条独立额度 | 没凭证时出片、验版式 |

**换通道后必须重跑 `wb tts`**：三家的音频、语速、停顿都不一样，字幕是跟着音频走的，缓存也是按引擎分开的。
