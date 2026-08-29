---
name: basketball-recap
description: Turn a complete basketball broadcast into a narrated Chinese highlight recap (篮球/NBA/CBA 比赛解说集锦) with the same narration-driven workflow as lol-recap. Use for full-game basketball replays with original commentary; read the complete ASR axis, pin scoring and momentum events to frames, write a timestamped story script, and reuse the deterministic lol_ingest/lol_tts/lol_arrange/lol_render tools to cut and render it. Do not use short official highlight compilations as the source.
---

# Basketball Recap（篮球解说集锦：全场理解、稿子先行、画面按稿摘）

把一场完整篮球转播做成有比赛主线、比分起伏和关键回合的中文解说集锦。

核心范式与 `lol-recap` 相同：先通读整场原声 ASR，写完句句带源时间 `t` 的解说稿，再让确定性工具按稿摘画面。复用 `lol_ingest`、`lol_tts`、`lol_arrange(mode="script")`、`lol_render`，不复制媒体实现。工具内部字段仍叫 `game`、`kill` 等，这是兼容层字段，不改变篮球语义。

## 硬性前提

- 只接完整比赛录像或完整四节录像，不接几分钟官方集锦。短集锦每个回合只有数秒，旁白会挤占下一个回合，无法稳定句画对齐。
- 原片必须有完整原声解说。中文转录传 `language="zh"`；英文或混合语言传 `language="auto"`。
- 单文件全场推荐作为 `game=1`；若素材按四节拆分，则按 Q1～Q4 作为 games 1～4，所有 `t` 都是对应分段内的秒数。
- 全程生成中文旁白为主轨，转播原声只作压低的现场氛围。

## 产物契约

全部产物写入项目 `out/`：

| 文件 | 产出者 | 内容 |
|---|---|---|
| `match.json` | `lol_ingest` | 队伍、完整比赛视频与时长 |
| `transcript_g{N}.json` | `transcribe` | 全场原声 ASR |
| `commentary_axis.txt`、`commentary_index.json` | `lol_ingest(action="axis")` | C 编号全场解说轴 |
| `events.json` | 主 Agent | 逐帧确认的关键回合区间 |
| `outline.json` | 主 Agent | 比分走势与叙事拍骨架 |
| `writer_script.json` | 主 Agent | 句句带源时间的中文解说稿 |
| `script_tts.json` | `lol_tts` | cloud TTS 逐句配音与真实时长 |
| `reel.json`、`coverage_report.txt` | `lol_arrange` | 按稿摘片与覆盖审计 |
| `final.mp4`、`qc.json` | `lol_render` | 成片与 QC |
| `spot_review.json`、`report.md` | 主 Agent | 句画抽查与报告 |

已有且校验通过的产物可以断点复用。

## 流程

### 1. 接入完整比赛

复用 LoL 接入适配器；`source` 必须保留为工具支持的 `"lol"`：

```text
lol_ingest(source="lol", home="主队", away="客队",
  event_title="赛事与场次",
  games=[{"name":"Full Game","video":"完整比赛.mp4"}])
```

这里的 `source="lol"` 只是底层合同兼容值，`home/away/event_title` 必须填写真实篮球信息。

### 2. 全场转录、切镜与解说轴

对每个完整视频运行 `transcribe` 和 `detect_shots`，再运行：

```text
lol_ingest(action="axis", transcript_paths=["out/transcript_g1.json", ...])
```

必须通读完整解说轴，先整理：每节比分、领先交换、犯规与暂停、球星状态、连续得分潮、最后两分钟和终场结果。不要只搜索“扣篮/三分/绝杀”等关键词拼高光。

### 3. 看帧钉关键回合

ASR 喊声通常晚于出手或入网 1～3 秒。对候选回合用 `video_watch_segment` 查看前后窗口，确认球出手、入网、记分牌跳分和回放边界，再写 `events.json`：

```json
[{"game":"1","src_start":4182.0,"src_end":4187.0,"event":"反超三分，记分牌跳至 86-85"}]
```

硬规则：

- `hard` 句只钉真实动作帧，不钉解说喊声时间。
- 直播与导播回放重复出现时只选直播动作；拿不准就看记分牌和转播回放标识。
- 每个具体比分都要从记分牌或解说轴交叉核验，禁止凭赛事记忆补写。
- `events.json` 只收关键事件；普通衔接句直接依赖自身 `t` 跳切。

### 4. 写叙事大纲

`outline.json` 使用 LoL 合同允许的 kind：

- `open`：背景、系列赛形势、核心对位；
- `kill`：单个决定性得分回合，如三分、扣篮、二加一；
- `fight`：连续攻防或一波得分潮；
- `objective`：篮板、抢断、封盖、犯规等改变球权和走势的回合；
- `tower`：拉开或追回分差的阶段性节点；
- `ending`：最后一攻、终场哨与结果。

拍按比赛时间严格递增。主线必须交代比分如何变化、落后方如何回应、胜负在哪个回合定型；不能变成十个进球镜头连播。`highlight: true` 只给 3～5 个最强回合。

### 5. 写句句带 `t` 的解说稿

`writer_script.json` 与 `lol-recap` 合同一致；需要节奏参考时读 `references/lol-style-card.md`，但术语、比分和球员关系必须回到篮球转播事实：

```json
{"beats":[{"idx":2,"sentences":[
  {"text":"尼克斯把分差追到只剩两分。","tier":0,"t":4175.0},
  {"text":"布伦森借掩护横移一步——","tier":1,"t":4181.5},
  {"text":"三分命中，反超！","tier":2,"t":4184.2,"hard":true}
]}]}
```

- `t` 是该句所讲画面的源视频秒数；分节素材还要写正确 `game` 拍归属。
- 同一拍内讲到不同回合时，每句分别标 `t`，让 script 模式主动跳切。
- 每组最多一个 `hard` 句。具体球员、比分、助攻、犯规必须有轴或画面依据。
- 写完整篇后做无上下文冷读，检查时间跳跃、球员身份、比分状态和因果链。

### 6. Cloud TTS 逐句配音

篮球固定显式调用：

```text
lol_tts(script_path="out/writer_script.json",
  provider="cloud_tts", voice="zh_male_liufei_uranus_bigtts")
```

逐句缓存会把 provider、voice 和文本纳入指纹；切换音色后会自动重新合成。生成式 TTS 可能改写引语，篮球稿尽量用直接叙述和短句；抽听强拍，发现添字或变声就改写该句再合成。

### 7. 按稿摘片并渲染

```text
lol_arrange(match_path="out/match.json", outline_path="out/outline.json",
  shots_paths={"1":"out/shots_g1.json"}, events_path="out/events.json",
  script_path="out/script_tts.json", mode="script")
lol_render(reel_path="out/reel.json", script_tts_path="out/script_tts.json",
  outline_path="out/outline.json", output_path="out/final.mp4")
```

查看 `coverage_report.txt`：最大空窗必须不超过 9 秒，且不能有硬钉被相邻回合挤走的 issue。问题优先通过修句子 `t`、拆拍或缩短文案解决，不用短集锦补画面。

### 8. 句画抽查与收尾

抽查至少 8 句，必须覆盖所有 hard 句、具体比分句和最后两分钟。对成片窗口核对“说的球员、动作、比分”与画面一致；矛盾句回到写稿、TTS、排片、渲染闭环。最终写 `spot_review.json` 和 `report.md`。

## 常见失败模式

- 使用官方短集锦：一句尚未讲完画面已经进入下一回合。换完整转播原片重做。
- ASR 时间直接当入网秒：喊声滞后导致呐喊落在回放或下一球。逐帧钉动作。
- 只讲强队进球：漏掉追分、暂停调整和领先交换，故事失真。按全场比分流重建大纲。
- 同一球直播和回放都入片：检查记分牌、回放标识和事件去重。
- 生成式 TTS 添字或演绎对白：改为短句直接叙述，只重合成失败句。
