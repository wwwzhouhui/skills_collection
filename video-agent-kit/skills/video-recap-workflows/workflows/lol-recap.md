---
name: lol-recap
description: >-
  Turn a full League of Legends pro match into a narrated highlight recap with
  story-driven Chinese esports commentary (英雄联盟赛事解说集锦), using the
  narration-driven pipeline. The agent reads the entire original caster ASR
  axis, writes a start-to-finish timestamped interpretation script, and uses
  deterministic tools to fit footage to the narration with hard shout-lines
  pinned to action frames. Use for LoL/esports match recaps on full per-game
  replays that have caster commentary.
---

# LOL Recap(英雄联盟解说集锦:先懂全局、稿子先行、画面按稿摘)

把一局(或一场 BO)完整职业比赛录像,自动剪成一条"解说带你看懂这局怎么打赢的"叙事集锦。

**核心范式(mode="script",默认):解说稿是成片的脊柱,画面是台词的函数。**
你先从头到尾理解整场比赛,写出一篇连贯的全场解读稿——**每句标注它讲的是比赛第几秒(`t`)**;
工具按稿摘画面:每组台词摘一段刚好讲完的切片(硬事件句由 VLM 钉到动作帧,呐喊后留呼吸口让原声欢呼透出来)。
没有词的画面根本不会被摘进来,**长空窗在结构上不存在**。
禁止反着做("先框画面窗口再往里塞词、塞不满再补")——那是旧 window 模式,只作兼容保留(`mode="window"`,窗口+字数预算+弹性伸窗,遇到长窗口会出大空窗)。

**音频定调:全程生成解说当主音轨;原声动态 ducking——有解说压到 0.10,无解说的短空窗(呐喊呼吸口/动作收尾)0.4s 内平滑抬到 0.85 当氛围。不保留原声解说当叙事。**

分工红线:工具不做叙事脑。比赛理解/解读稿/冷读/抽查全部由你(主 Agent)完成;工具只做确定性媒体操作(接入/排片/TTS/渲染混音/QC 门)。

适用性:需要 (a) 逐局完整比赛录像;(b) 带解说原声——**解说 ASR 轴是理解比赛故事的主通道**;(c) 你自己看帧钉出的 events.json(见第 3 步;不依赖外部视觉模型)。

## 产物契约(全部在 out/)

| 文件 | 谁产出 | 是什么 |
|---|---|---|
| `out/match.json` | lol_ingest | 队伍 + 逐局视频/时长 |
| `out/transcript_g{N}.json` | speech_transcribe | 每局全场解说 cloud ASR(分块缓存) |
| `out/commentary_axis.txt` + `commentary_index.json` | lol_ingest(axis) | C 编号解说轴(理解故事+引用权威) |
| `out/events.json` | (可选) 外部 VLM 检测 | 精确高光 in/out,给硬句钉帧 |
| `out/outline.json` | **你写** | 章节骨架(拍 kind/t/highlight + through_line + 冷开场 + 终结卡) |
| `out/writer_script.json` | **你写** | 全场解读稿(**每句带 t**,呐喊句 hard) |
| `out/script_tts.json` | lol_tts | 逐句配音 + 真实时长(句级缓存) |
| `out/reel.json` + `coverage_report.txt` | lol_arrange(mode=script) | 摘片卷 + 逐句摆放计划 + 覆盖审计(空窗一目了然) |
| `out/final.mp4` + `qc.json` | lol_render | 成片 + QC 硬门(时长/响度/像素格式/**最大空窗≤9s**) |
| `out/report.md` | **你写** | 收尾报告 |

## 流程(注意顺序:写稿 → TTS → 摘片 → 渲染;摘片需要每句真实时长)

### 1. 接入 + 转录 + 解说轴
- `lol_ingest(source="lol", home, away, event_title, games=[{name,video}...])` → match.json
- `speech_transcribe(<每局视频>, language="zh")` —— **必须转全局**,全场解说轴是理解故事的事实来源
- `lol_ingest(action="axis", transcript_paths=[...])` → C 编号解说轴

### 2. 你通读全场,把比赛看懂(最重要的一步)
像读剧本一样通读解说轴:开局思路、一血怎么来的、雪球靠什么滚、**中间有没有对手回血/翻盘尝试(别把有来有回讲成一路平推)**、哪波团/哪条龙是转折、怎么终结。
**关键事实必须回轴核对确切时刻和归属**,不要凭印象写——典型翻车:名场面的发生时刻记错了 150 秒、资源归属搞反(团赢了但先锋被对面捡走)。拿不准就 grep 轴、必要时 `video_watch_segment` 看帧。

### 3. 你亲自看帧钉事件(out/events.json)——默认做法,不依赖外部视觉模型
解说喊话常晚于动作 1~3 秒,ASR 还会带错字;**每个 hard 句的时刻必须看过帧再定**:
- 对每个呐喊时刻 t,抽 `[t-9, t+15]` 的 3×3 时间码宫格(ffmpeg 抽帧烧秒数拼图,或 `video_watch_segment`),**亲眼找横幅/击杀提示出现的那一秒**(第一滴血/击败峡谷先锋/击杀纳什男爵/终结!/killfeed)。
- 顺带核事实:资源归属看横幅颜色(红方/蓝方);**顶部记分条消失 = 导播回放画面,一律不用**(ASR 轴不会告诉你这是回放,这是只有看帧才能抓住的坑)。
- 看完立刻落盘 `out/events.json`(不靠会话记忆):每个时刻写**一条紧凑段**(动作帧前后 ±2s,中心=横幅/击杀那一秒,呐喊句吸附的就是这个中心)+ 可选**若干余波段**(间隔 ≤6s 会被链起来,决定"动作演完再切"的出点):
```json
[{"game":"1","src_start":2398.5,"src_end":2402.5,"event":"大龙到手(横幅@2401)"},
 {"game":"1","src_start":2404.0,"src_end":2420.0,"event":"枪阵清算"}]
```
批量场景(几十场无人值守)才考虑外部 VLM 检测脚本产 events.json,契约相同;单场精剪一律亲自看。

### 4. 你写章节骨架(out/outline.json)
```json
{"teams_cn": {"home": "EDG", "away": "TT"},
 "through_line": "一句话悬念主线",
 "open_title": "...", "cold_open": {"flashes": [{"game":1,"t":1890}, ...]},
 "end_card": {"line1": "...", "line2": "..."},
 "beats": [
  {"idx": 1, "kind": "open", "summary": "阵容与看点"},
  {"idx": 2, "kind": "kill", "game": 1, "t": 950, "highlight": true, "summary": "一血"},
  {"idx": 12, "kind": "ending", "game": 1, "t": 2563, "highlight": true, "summary": "终结"}]}
```
- kind ∈ open/fight/kill/objective/tower/ending;拍按 t 严格递增;`highlight` 只给 3~5 个强拍(呐喊后加呼吸口)。
- **章节要覆盖全场剧情**,包括对手的反扑段——完整故事,不是击杀合集。
- `ending` 的 t = 基地水晶爆炸那一刻(在轴里找"恭喜/拿下比赛"倒推);冷开场快闪选 2~4 个名场面。

### 5. 你写全场解读稿(out/writer_script.json)——句句带 t
先读 `references/lol-style-card.md`(电竞文风,只学手法)。
```json
{"beats": [{"idx": 2, "sentences": [
  {"text": "开局上路,格温带点燃一次次找贾克斯换血。", "tier": 0, "t": 936},
  {"text": "赵信悄悄摸上来,贾克斯闪现全交——都没用。", "tier": 1, "t": 944},
  {"text": "跟闪一枪捅到,一血到手!", "tier": 2, "t": 950, "hard": true},
  {"text": "十几刀领先,外加一血入账。", "tier": 1, "t": 965}]}]}
```
硬规则:
1. **`t` = 这句讲的画面在源视频的秒数**(从解说轴来,有据可查)。无 t 的句子跟随前句(画面连续讲下去)。同拍内 t 差 >6s 会自动跳切成蒙太奇——这是想要的效果(官方集锦中位 6s 一切)。
2. 呐喊句 `hard: true` + tier 2,**每组至多一个**;它会被钉到事件帧,前面的铺垫句自动向前回填(解说早于画面起口是自然的)。悬念铺垫("但赵信更快一步——")也要标 t(略早于硬句),保证和呐喊在同一切片里,话音落就兑现。
3. 情绪三档 tier 0/1/2 只由语速+响度区分,音调恒零。
4. **词面纪律**:不留英文单词(中文音色念英文生硬);原解说的梗必须自解释否则弃用;一次性事件的关键名词不跨拍撞车(如"中路高地"vs 终结的"基地");只写轴/画面能支撑的事实,宁虚不编。
5. 整篇顺读像一个人从头讲到尾:开场句(open 拍,无 t)骑在冷开场快闪上;每拍首句衔接上文交代 through_line;结尾扣主题。
6. **写完做冷读者测试**:纯文本稿丢给无上下文子代理,抓时间跳跃/身份没户口/指代不清/因果断层,修到 ≤2 条。

### 6. TTS(先于摘片!)
`lol_tts(script_path="out/writer_script.json", provider="cloud_tts", voice="zh_male_wennuanahu_uranus_bigtts")` → script_tts.json(真实时长)。LoL 固定使用该解说音色；每次显式传 provider/voice，避免项目环境覆盖。句级缓存包含音色指纹，改稿只重合成改动句，切换音色则自动全量重合成。生成式 TTS 可能添字/加语气词，强拍必须抽听；不忠实的句子改成短句直述后只重合成该句。

### 7. 摘片
`lol_arrange(match_path, outline_path, shots_paths={}, events_path, script_path="out/script_tts.json", mode="script")` → reel.json(含逐句摆放计划)+ **coverage_report.txt**。
看报告:切片数/语音覆盖率/最大空窗(门 9s)。有 issues(首句缺 t/开场白超长/切片重叠)按提示改稿,重跑 6→7(缓存使未改句免费)。

### 8. 出片
`lol_render(reel_path, script_tts_path, outline_path, output_path)` → final.mp4(yuv420p/High/faststart,中文黑体字幕烧录,动态 ducking)。
- `placement_invalid` → 稿子和 reel 不同步,按 6→7→8 顺序重跑。
- `qc_failed` 看 qc.json:时长/响度/像素格式/**narr_gap(最大空窗)**——空窗超门说明稿子对某段画面失语,回稿子补讲那段(先查轴里那里发生了什么),不是去剪短画面。

### 9. 句画抽查 + 收尾
抽 6~8 句,`video_watch_segment` 核对"说的"与"演的"一致(重点抽 hard 句和带具体事实的句),矛盾句回炉。写 `out/report.md`。

## 常见失败模式
- **把比赛讲错**(最致命):事件时刻/资源归属凭印象写 → 第 2 步逐条回轴核对 + 第 3 步看帧核横幅;实测抓过:先锋归属搞反、名场面时刻记偏 150 秒。
- **把导播回放当新画面**(ASR 抓不住):回放段顶部记分条消失、横幅/击杀提示重复出现 → 看帧识别,一律不用;成片里同一场团战只能出现一次。
- **一路平推叙事**:漏掉对手的反扑/回血段 → 章节骨架必须覆盖全场剧情起伏。
- **空窗/全是原声**:某段画面没词 → 这在 script 模式意味着稿子没讲那段;查轴补稿,勿靠拉长画面糊弄。呐喊后呼吸口+句子 t 离群也会造成空窗:把该句 t 拉近前一动作,或接受跳切。
- **呐喊句和画面错位**:hard 句没标 t 或 t 没看帧核过;悬念铺垫没标 t 被分到上一个切片,隔着跳切才兑现。
- **十个击杀连播**:through_line/衔接句敷衍 → 回第 4/5 步补叙事骨架。
