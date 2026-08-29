---
name: soccer-recap
description: Turn a full football match into a narrated highlight reel with story-driven Chinese commentary (足球集锦解说) using the "outline first, footage-locked, narration fitted" pipeline. The agent reads the original English commentary axis like a screenplay, writes the narrative outline and commentary itself, and deterministic tools do video adaptation, shot detection, footage arrangement, cloud TTS, placement/mixing and hard QC gates. Use for football/soccer match recap, highlight reel with commentary, 足球比赛解说集锦 tasks.
---

# Soccer Recap（足球解说集锦：大纲先行、画面锁死、文案迁就）

把一场完整足球比赛自动剪成"天下足球"式叙事解说集锦。

**核心纪律：大纲决定讲什么故事，比赛事件锁死画面时刻，文案把两者缝起来；禁止跳过大纲直接按事件表逐句填词——那样产出的是十条进球快讯连播，不是一个人讲完整场球。** 与 movie-recap 的根本差异：电影里画面跟着大纲选，足球里呐喊必须钉在进球秒上——画面时刻不可协商，弹性全在文案。

分工红线：工具不调用任何大模型。比赛理解、大纲、旁白、冷读、抽查全部由你（主 Agent）完成；工具只做确定性媒体操作（数据源适配/切镜/排片/TTS/渲染混音/QC 门）。

适用性：需要原声带解说的比赛视频——解说轴是理解比赛故事的主通道（进球者/助攻/背景/情绪峰值），无解说的素材退化严重，需大量抽帧兜底。事件时刻由"轴时间戳粗定位 → 抽帧确认"得出，以内联 `event{half,t,minute,score_after}` 写进 outline。

## 视频模式（source="video"）纪律

- **进球秒必须抽帧钉死**：解说轴的呐喊时间戳只做 ±5s 粗定位，对每个进球用 `video_watch_segment` 看候选窗口，找到球过线/爆庆祝的那一秒才写进 `event.t`。禁止凭轴时间戳直接报秒。
- **比分流自己记账**：每个 goal 拍内联 `score_after`（主-客），比分角标全靠它；写完在轴里找比分复述句（"two nil"）交叉验证一遍。
- **先写 story 再写 outline**：通读全轴后先产 `out/story.md`（完整赛场过程：每个进球的来龙去脉+人物+情绪），outline 从 story 里挑拍——这是"理解→叙事→选画面"的顺序，别跳。
- 疑似进球但轴里含糊（VAR/吹掉/乌龙）：抽帧看记分牌数字有没有跳，宁缺毋滥。


## 产物契约（全部在项目目录 out/ 下）

| 文件 | 谁产出 | 是什么 |
|---|---|---|
| `out/match.json` | soccer_ingest | 标准比赛合同：队伍/半场视频；事件稍后以内联 event 写进 outline |
| `out/transcript_h1/h2.json` | transcribe | 上下半场全场 ASR（language=auto，分块缓存） |
| `out/shots_h1/h2.json` | detect_shots | 全半场镜头轴（224p 低清视频上检测） |
| `out/commentary_axis.txt` + `commentary_index.json` | soccer_ingest(axis) | 带 C 编号的英文解说轴（引用权威） |
| `out/outline.json` | **你写** | 叙事拍大纲（内联 event + C 编号引用 + 悬念状态机 + 终场哨定位） |
| `out/reel.json` + `writing_brief.txt` | soccer_arrange | 排片卷（卷轴时间）+ 每拍真实秒数/字数硬预算 |
| `out/writer_script.json` | **你写** | 分拍旁白（句子带情绪档+锚点类型） |
| `out/script_tts.json` | soccer_tts | 逐句配音+真实时长（句级缓存） |
| `out/final.mp4` + `placement.json` + `qc.json` | soccer_render | 成片+摆放表+QC 硬门报告 |
| `out/spot_review.json` + `report.md` | **你写** | 句画抽查记录+收尾报告 |

每一步产物已存在且校验通过即可跳过 = 断点续跑。

## 流程

### 1. 接入

`soccer_ingest(source="video", game=..., video_root=...)`（或直接传 `halves={"1":路径,"2":路径}` + home/away）→ match.json 只含半场视频与时长，events 为空；事件后面由你以内联形式写进 outline：

```json
{"idx": 2, "kind": "goal", "event": {"half": 1, "t": 1178.5, "minute": 19, "score_after": "0-1", "team": "away"},
 "replays": 2, "highlight": true, "summary": "...", "points": [...]}
```

冷开场同理可用内联时刻：`"cold_open": {"flashes": [{"half":1,"t":1178.5}, ...]}`。

### 2. 转录 + 切镜（可并行）

- `speech_transcribe(input_path=<半场视频>, language="auto", output_json="out/transcript_h{1,2}.json")`——**必须转全场两个半场，不是转成片**：全场解说轴是后面选任何窗口的事实来源，也是训练样本导出的原料。
- `detect_shots(input_path=<半场224p>, output_json="out/shots_h{1,2}.json")`——全半场镜头轴，回放收编和切点吸附都靠它。

### 3. 解说轴

`soccer_ingest(action="axis", transcript_paths=["out/transcript_h1.json", "out/transcript_h2.json"])` → C 编号解说轴。**通读它，像读剧本一样理解这场比赛**：谁进的球、有什么背景故事（旧将回府/处子球/门将失误）、原解说在哪些非进球时刻情绪爆了（这些是张力段候选）。

### 4. 你写大纲（out/outline.json）

```json
{"teams_cn": {"home": "皇马", "away": "沙尔克"},
 "through_line": "一句话悬念主线(整片反复回答它走到哪了)",
 "open_title": "2015.3.10 欧冠1/8决赛次回合",
 "gap_card": {"line1": "皇马  vs  沙尔克", "line2": "2015.3.10 欧冠1/8决赛次回合"},
 "cold_open": {"flashes": [{"half": 1, "t": 1178.5}, {"half": 2, "t": 932.0}]},
 "end_card": {"line1": "总比分 5 - 4", "line2": "皇马惊险晋级八强"},
 "beats": [
  {"idx": 1, "kind": "open", "summary": "背景+悬念抛出", "points": [{"text": "...", "c": ["C0003"]}]},
  {"idx": 2, "kind": "goal", "event": {"half": 1, "t": 1178.5, "minute": 19, "score_after": "0-1", "team": "away"},
   "replays": 2, "highlight": true, "pre": 18,
   "summary": "富克斯撕开剧本", "link": "但沙尔克不这么想",
   "points": [{"text": "只写解说轴/事件能支撑的事实", "c": ["C0041"]}]},
  {"idx": 7, "kind": "chance", "event": {"half": 2, "t": 2286.0, "minute": 83}, "summary": "绝杀前奏"},
  {"idx": 9, "kind": "ending", "whistle_t": 2926.0, "in_t": 2909.0, "out_t": 2935.8,
   "highlight": true, "summary": "死里逃生"}]}
```

硬规则（逐条遵守）：
- 一拍一个叙事单元：所有进球各一拍 + 冷开场一拍 + 结尾一拍 + 0~3 个张力拍（chance）。张力拍从"射正×原解说情绪峰值×比分摇摆邻近"里挑，宁缺毋滥。
- 拍严格按比赛时间顺序；每拍写 `link`（与上一拍的因果/转折衔接词），**这是"完整叙事"的骨架**。
- `through_line` 是悬念状态机（如"总比分安全垫还剩几个球"），后面写稿时每个桥接句都要交代它的当前值。
- 回放变奏：首球/新星时刻/决定性进球 `replays: 2`，中段进球 1，防八段一个模子的节奏疲劳。
- `highlight: true` 只给 3~5 个强拍（首球/绝杀/终场），呐喊后会强制留白透欢呼。
- **ending 拍的 `whistle_t` 你来定位**：解说轴里找 "full time / that's it / goes through" 类表述，对不准时抽帧确认（90:00 时钟+握手镜头）；`out_t` 通常取半场视频末尾附近。
- 冷开场快闪选"故事对手方"的进球（客队逆袭选客队 4 球；屠杀局选胜方连击），不是机械选客队。

### 5. 排片

`soccer_arrange(match_path, outline_path, shots_paths={"1": ..., "2": ...})` → `out/reel.json` + `out/writing_brief.txt`。

- `outline_invalid` → 按 issues 修大纲重跑（≤2 次）；常见：两拍画面窗口重叠（合并为一拍或调小 pre）。
- brief 里每拍的铺垫/事件后秒数是**真实画面秒数**，字数是硬预算（呐喊槽和留白已扣除）。

### 6. 你写旁白（out/writer_script.json）

先读 `references/soccer-style-card.md`（天下足球文风卡：只学手法不抄内容），再读 writing_brief。

```json
{"beats": [{"idx": 2, "sentences": [
  {"text": "但沙尔克的反扑，来得比想象更快。", "tier": 0, "anchor": "bridge"},
  {"text": "迈尔挑起进攻，巴内塔巧妙一漏——", "tier": 1, "anchor": "event", "offset": -8.8},
  {"text": "富克斯！爆射！球进了！", "tier": 2, "anchor": "event", "offset": 0.1, "hard": true},
  {"text": "伯纳乌安静了。", "tier": 1, "anchor": "post", "offset": 6.4}]}]}
```

硬规则：
1. 每拍字数不超 brief 预算（可少 10% 不许超）；情绪三档 tier 0 铺垫/1 拔高/2 爆发，**只由语速和响度区分，音调恒零**。
2. 锚点语法：`event`+offset 钉在事件秒（呐喊句必须 `hard: true`）；`bridge` 骑跨段首缝时间跳跃（每拍开头的衔接句都该用它）；`post` 事件后评论（highlight 拍自动让出欢呼留白）；`flow` 顺流。
3. 呐喊句短促有力（"富克斯！爆射！球进了！"），顿号断句出顿挫（"只！差！一！球！"）；解读句只写画面或解说轴能支撑的事实——**球员表情/看台细节必须先抽帧看过再写**（`video_watch_segment` 或抽帧拼图），宁虚不编。
4. 整篇顺着读像一个人讲完整场球：桥接句用 link 的衔接词开头，交代 through_line 当前值；结尾一句跳出比赛扣主题（贺炜式）。
5. 人名/队名全篇统一中文译名（写进 outline 的 teams_cn 与首拍 points）。

**写完必须做冷读者测试**：把纯文本稿（只有句子，按顺序）丢给**不带任何上下文的子代理**，让它模拟"普通观众只听一遍、不懂这场比赛"，专抓：时间跳跃没交代（怎么就到 78 分钟了）、人物没户口（亨特拉尔是谁）、指代不清、因果断层、悬念线丢失（总比分现在到底几比几）。按清单修（只许补过渡/补身份/拆句，不许发明事实），修完再冷读一轮，直到 ≤2 条可接受项。

### 7. TTS

`soccer_tts(script_path="out/writer_script.json")`。默认使用配置好的标准云端 TTS；需要切换音色时通过参数显式传入。句级缓存包含音色指纹，改稿只重合成改动句，切换音色则自动全量重合成。生成式 TTS 的强拍和人名句要抽听，不忠实的句子改为短句直述后重合成。

### 8. 出片

`soccer_render(reel_path, script_tts_path, outline_path, base_transcript_path=<可选:底版转录>, output_path=...)`。

渲染语法（工具内置，不用你操心）：段间 0.3s 溶解转场——时长守恒（边界两侧各多取 0.15s 素材喂 xfade，时间轴与解说锚点不动）；冷开场后 0.7s 黑场压 `gap_card` 标题卡（缺省用 teams_cn + open_title，不留裸黑屏）；全片按摆放时刻烧录底部居中解说字幕（`subtitles=false` 可关）。

- `over_budget` → 压缩对应拍文案（删修饰不删事实）→ 重跑 soccer_tts + soccer_render（缓存让未改句免费）。**永远先改文案，不动画面。**
- `qc_failed` → 看 qc.json：blackdetect 有意外黑场=排片/渲染 bug；硬锚偏差>1s=摆放冲突；响度出 [-19.5,-12.5]=混音异常。
- base_transcript_path 给成片底版（render_work/base.mp4）的转录时，英文原解说区间也会进压音并集；不给则只压中文句区间（欢呼透传更多，英文残留也更多——原声英文解说较密的比赛建议给）。

### 9. 句画矛盾抽查

抽 8~10 句解读句（写了画面细节的），`video_watch_segment` 对成片对应窗口核对"说的"与"演的"一致。矛盾句软化措辞回炉 6→7→8。写 `out/spot_review.json`。有条件再做两个音频抽查：成片首尾窗口回喂 ASR 验呐喊钉点；解说拼轨说话人聚类应=1。

### 10. 收尾

`out/report.md`：时长/拍数/句数、冷读轮次与残留项、QC 门结果、抽查矛盾率、遗留风险。

## 常见失败模式

- **十条快讯感**（最常见）：跳过大纲或 link/through_line 敷衍。回到第 4 步补叙事骨架，不要在句子层修补。
- **旁白超预算**：永远压文案不动画面；成段超说明大纲要点太多，删要点。
- **呐喊漂移**：hard 句没标 hard，或前句太长把它挤晚——soccer_render 会报，缩前句。
- **声音听感不一致**：任何情绪档都不许动音调（工具已强制 +0Hz）；云端音色偶发漂移句，聚类抓出重摇该句。
- **黑屏闪切/裸黑屏**：蒙太奇内部禁止淡入淡出（工具已内置硬切语法）；唯一设计黑场必须压标题卡（工具已内置 gap_card）；qc.json blackdetect 兜底。
- **切片生硬**：段间必须走溶解转场而非硬拼 concat（工具已内置时长守恒 xfade）；若观感仍跳，查切点是否吸附到了镜头边界（shots 质量）。
- **剧透**：比分角标必须进球瞬间才跳分（工具已内置）；冷开场快闪别配读出比分的旁白。
- **张冠李戴**：解说轴说的事 ≠ 画面演的事（"三周前的客场胜利"是解说轴背景，画面没有）；写稿区分"轴事实"与"画面事实"，画面细节必须看帧。
