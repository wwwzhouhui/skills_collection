# 配音通道（小米 / 火山 / edge）

三条通道实现在 `lib/tts/`，由 `config.json` 的 `tts.engine` 切换。**同一时刻只用一个**，失败不回退到别的引擎（保证全片音色一致）。

> ⚠️ 本仓库已把全部外部命令改成**异步**调用（`lib/tts/run.mjs`）。
> 本机 Node 的同步进程调用（`execFileSync`/`spawnSync`）一律抛 `EBUSY`，连 `cmd /c echo` 都起不来；
> 异步 `spawn` 完全正常。**在新代码里不要写 `execFileSync`。**

## 怎么选

| 通道 | 音色 | 逐字时间戳 | 语速参数 | 成本 | 什么时候用 |
|---|---|---|---|---|---|
| **`volc`** 火山引擎 | 官方音色 + 你自己的声音复刻 | ✅ **有** | 原生 `speech_rate` | 按量付费 | 要**逐字跟读高亮**、要声音复刻、要最好的音色 |
| **`mi`** 小米 MiMo | 固定九个 | ❌ 只有小句级（静音检测估算） | ❌ 只能本地 `atempo` 后处理 | 走 token-plan Key | 默认通道，够用且省事 |
| **`edge`** edge-tts | 微软云希/晓晓等 | ❌ | 原生 `rate` | 免费 | 没额度时的备胎，音色偏"播报" |

**要字幕逐字高亮就选 `volc`**；只要句子级字幕（本 skill 已按小句聚合，观感没问题）用 `mi` 就行。

## 配置

`config.json`：

```jsonc
"tts": {
  "engine": "mi",                                    // volc | mi | edge
  "speed": 1.15,                                     // 倍率，1=原速
  "loudness": 1,

  "voice": "zh_male_liufei_uranus_bigtts",           // ← 火山专用
  "resourceId": "seed-tts-2.0",                      // ← 火山专用，必须与音色配套
  "endpoint": "plan",                                // ← 火山专用，见下
  "style": "",                                       // 火山仅 2.0 音色响应

  "mi": {
    "baseUrl": "https://token-plan-cn.xiaomimimo.com/v1",
    "model": "mimo-v2.5-tts",
    "voice": "冰糖",                                  // ← 小米专用，九个里选
    "style": "语速偏快、语气轻松自然"                    // 作为 user 消息一起发
  },

  "edge": { "voice": "zh-CN-YunxiNeural", "python": "<装了 edge_tts 的解释器>" }
}
```

**三个引擎的音色字段不能混填** —— 互相顶替会报 `Unknown voice`，这是最常见的坑。

凭证在 `.env`：

```
VOLC_TTS_API_KEY=ark-xxxx          # 火山：控制台发的 ark- 开头 Key
VOLC_TTS_ENDPOINT=plan             # ark- Key 只认 plan 域
VOLC_TTS_RESOURCE_ID=seed-tts-2.0  # 与音色配套
VOLC_TTS_VOICE=zh_male_liufei_uranus_bigtts

MI_TTS_API_KEY=tp-xxxx             # 小米：token-plan 的 tp- 开头 Key
```

## 火山：两个调用域互不相通

| 域 | 端点 | 认哪种 Key |
|---|---|---|
| `standard` | `openspeech.bytedance.com/api/v3/tts/unidirectional` | 控制台直购 / 旧版 AppId+Token |
| `plan` | `openspeech.bytedance.com/api/v3/plan/tts/unidirectional` | 方舟套餐域签发的 `ark-` Key |

`ark-` 开头打标准域会报 `45000010 Invalid X-Api-Key` —— **这是打错域，不是额度问题**，别去充值。
`resourceId` 与音色必须配套：2.0 音色（`*_uranus_bigtts`）→ `seed-tts-2.0`；1.0 音色 → `seed-tts-1.0`；声音复刻（`S_` 开头）→ `volc.megatts.default`。

**要逐字时间戳必须同时开 `enable_timestamp` 与 `enable_subtitle`**（本仓库已开）。实测 `seed-tts-2.0` + 2.0 音色只开 `timestamp` 会返回 `words=[]`。

## 小米：九个音色，没有语速参数

音色只有这些（写错一个字符就报 `Unknown voice` 并列出全部可选值）：

```
mimo_default / 冰糖 / 茉莉 / 苏打 / 白桦 / Mia / Chloe / Milo / Dean
```

- 正文必须放在 `assistant` 角色的消息里，`user` 角色放 `style`（自然语言风格指令，如"语速偏快、语气轻松自然"）。
- 端点只有 `{baseUrl}/chat/completions` 一个入口 —— `/audio/speech`、`/tts` 都是 404。
- **接口没有语速参数**：`tts.speed` 是本地 ffmpeg `atempo` 后处理（实测传 0.5 与不传返回的字节完全相同，说明接口自己忽略）。
- **不返回逐字时间戳**：句子级时间由静音检测估算（`silencedetect=noise=-35dB:d=0.10` + 动态规划吸附到停顿区间）。这个阈值是实测选出来的，**别凭直觉"调灵敏点试试"**——更灵敏反而更差。

## 自检

```bash
I=<仓库>/bin/iph
$I voice
```

会回显 engine / 端点 / 模型 / 音色 / 时间戳粒度，并真合成一句到 `build/_voice-check.wav`。改完 TTS 配置先跑它。

## 排错

| 报错 | 原因 |
|---|---|
| `Unknown voice: xxx` | 音色字段填错引擎（小米只有九个固定音色） |
| `45000010 Invalid X-Api-Key` | 火山调用域打错（`ark-` 只认 `plan`） |
| `401/403 Invalid X-Api-Key` | 火山 Key 本身无效或没授权 |
| `mismatched with speaker` | 火山 `resourceId` 与音色不配套 |
| `Invalid X-Api-Resource-Id` | 资源 ID 拼错 |
| `assistant role` / `voicedesign` | 小米模型选错（合成请用 `mimo-v2.5-tts`） |
| `429` / `rate limit` | 限流，等几秒重试（本仓库逐段串行，不并发） |
| 字幕整体偏移 | 改过语速但没重新 build（时间戳必须与音频同一次产出） |
