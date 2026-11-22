# 火山引擎 TTS：调用域与可用音色

`wb voice` 会回显当前档位并真跑一句合成；换音色改 `config.json` 的 `tts.voice`（或 `.env` 的 `VOLC_TTS_VOICE`）后重跑本命令试听。

## 一、两个调用域，互不相通

| 域 | 端点 | 谁用它 |
|---|---|---|
| `standard` | `https://openspeech.bytedance.com/api/v3/tts/unidirectional` | 直购 / 常规额度、旧版控制台 AppId+AccessKey |
| `plan` | `https://openspeech.bytedance.com/api/v3/plan/tts/unidirectional` | 方舟「套餐」域签发的 `ark-` 开头 API Key |

配置：`config.json` 的 `tts.endpoint` = `"plan"` / `"standard"` / 完整 URL；留空则按 Key 前缀自动判定（`ark-` → `plan`）。

**2026-09-29 实测**：同一个 `ark-` Key 打 `standard` 报 `45000010 Invalid X-Api-Key`，打 `plan` 才 HTTP 200 出音频。打错域的表现和"没额度"长得一样，很容易误判——先确认域，再怀疑额度。

⚠️ `https://ark.cn-beijing.volces.com/api/plan/v3` 是方舟**另一套（非 TTS）**入口，单独调 401；**不要**拿它当 TTS 的 baseURL 拼路径。

## 二、resourceId 必须和音色配套

| 音色家族 | resourceId | 说明 |
|---|---|---|
| 官方 2.0，ID 形如 `*_uranus_bigtts` | `seed-tts-2.0` | 推荐。有逐字时间戳（需 `enable_subtitle: true`，本仓库已开），支持 `context_texts` 风格描述 |
| 官方 1.0，ID 形如 `*_moon_bigtts` | `seed-tts-1.0` | 逐字时间戳靠 `enable_timestamp`，字为 tn 归一化后文本 |
| 声音复刻，ID 形如 `S_xxxx` | `volc.megatts.default` | 你自己的声音；2.0 复刻可另配 `req_params.model` |

配错的表现是 `55000000 resource ID is mismatched with speaker related resource`（HTTP 200，不是 4xx）。

## 三、实测可用音色（2026-09-29，`ark-` Key + `seed-tts-2.0` + `plan` 域）

**可用（✓ 实测出音频）**

| 音色 ID | 听感 |
|---|---|
| `zh_male_liufei_uranus_bigtts` | 男声，稳，默认首选 |
| `zh_male_yuanboxiaoshu_uranus_bigtts` | 男声，渊博讲解感 |
| `zh_male_wennuanahu_uranus_bigtts` | 男声，温暖 |
| `zh_male_taocheng_uranus_bigtts` | 男声 |
| `zh_male_dayi_uranus_bigtts` | 男声 |
| `zh_male_naiqimengwa_uranus_bigtts` | 男童声 |
| `zh_male_m191_uranus_bigtts` | 男声 |
| `zh_female_cancan_uranus_bigtts` | 女声，灿灿 |
| `zh_female_vv_uranus_bigtts` | 女声 |
| `zh_female_meilinvyou_uranus_bigtts` | 女声，女友感 |
| `zh_female_tianmeitaozi_uranus_bigtts` | 女声，甜美 |

**这套 Key 未授权（✗ 报 `mismatched with speaker`）**：`zh_male_jieshuonansheng_uranus_bigtts`、`zh_male_yushu_uranus_bigtts`、`zh_female_yuanqinvyou_uranus_bigtts`、`zh_female_sajiaonvyou_uranus_bigtts`，以及全部 1.0 的 `*_moon_bigtts` 音色。

> **授权是按账号走的**，换账号可用范围会变，这张表只是参考。拿到报错别猜，用下面两招自查：
> - `wb voice`：一句话真打一次接口，直接给错因和下一步。
> - 完整音色列表以火山控制台「音色广场」为准，按 `2.0` 筛，复制 ID 填 `tts.voice`。

## 四、排查速查

| 现象 | 真正原因 | 处理 |
|---|---|---|
| `45000010 Invalid X-Api-Key` | Key 与调用域不匹配（`ark-` Key 打了 `standard`） | `tts.endpoint` 改 `"plan"`（或反过来改 `"standard"`） |
| `45000030 ... requested resource not granted` | `resourceId` 没开通 | 控制台开通对应服务，或改 `tts.resourceId` |
| `55000000 ... mismatched with speaker` | 音色不属于该 `resourceId`（如 1.0 音色配了 2.0 资源），或该音色未授权 | 换成本文档第三节的 ✓ 音色，或改 `resourceId` |
| `40402003 TTSExceededTextLimit` | 单次提交文本超长 | 把这一段旁白拆成两段 |
| `quota exceeded ... concurrency` | 并发超限 | 等其它合成任务跑完再重试 |
| HTTP 200 但 `words=0` | 没开 `enable_subtitle` | 2.0 音色必须开（`lib/tts/tts.mjs` 已开，别关） |

## 五、缓存与端点

音频缓存键包含 `文本 + 引擎 + 端点域 + resourceId + 音色 + 语速 + 音量 + 风格`。**换域、换音色、改语速都会自动重配**，不需要手动删音频；要强制重配全部用 `FORCE_TTS=1 wb tts <期>`。
