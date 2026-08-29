---
name: movie-recap
description: Turn a full movie into a narrated recap short video (电影解说) using the dialogue-driven "arrange footage first, write narration second" pipeline. The agent reads the film's dialogue axis like a screenplay, writes the outline and narration itself, and deterministic tools do shot detection, footage arrangement, sentence-level shot binding, TTS, and final render. Use for movie recap / film commentary / 几分钟看完一部电影 tasks on films with substantial spoken dialogue.
---

# Movie Recap(电影解说:先排片、后成稿)

把一部电影自动剪成"几分钟看完一部电影"式的解说短片。

**核心纪律:大纲决定讲什么,画面决定能讲多久,文案把两者缝起来;禁止让每句话拿着秒数去素材库里凑碎片。** 新接缝只允许出现在剧情要点/拍的边界;拍内画面是连续原片块,节奏就是原片剪辑师的节奏。

分工红线:工具不调用任何大模型。剧情理解、大纲、旁白全部由你(主 Agent)完成;工具只做确定性媒体操作(切镜/排片/TTS/DP绑定/渲染)。

适用性:本技能靠台词轴理解剧情,**只适用于台词量充足的片子**(对白稀少的动作片/默片,`arrange_footage action=dialogue` 会返回 `empty_transcript` 或台词行数极少——此时回退 `video-edit-agent` 通用流程,靠抽帧观察理解)。

外语片同样适用,**不需要单独的机翻步骤**:ASR 用 `language="auto"` 转写(**不要传 en/ja/ko 等具体语种**——cloud ASR 兼容后端的说话人分离通常只在 language 为空/auto/zh-CN 时开启,传了具体外语语种可能丢失说话人标签,人物归属就只能盲猜)。auto 模式外语文本会比专用语种模式略糙(个别词听岔),但说话人标签对剧情理解更关键,听岔的词靠上下文和视觉校对兜底。台词轴保持原文;你读原文台词轴理解剧情,大纲和旁白直接用中文写——"理解时读原文,落笔时已是中文"。注意三点:①人物名先定一套中文译名(常用译名或音译),写进角色表并全程统一;②大纲要点的 text 用中文写,但 dlg 引用仍指向原文台词行;③旁白里引用台词时用意译,不要生硬直译。

**外语片(或任何说话人标签缺失/稀疏的片子)必须加第 3.5 步视觉校对,不能只靠台词轴盲写大纲。** 台词轴能给逐句精确文本和时间戳,但给不出"谁是谁"(无 speaker 聚类时人物全靠称呼语境猜,猜错率高)和台词里压根不提的视觉事实(画的画、墙上的字、道具细节)。**抽帧拼图不能反过来替代 ASR**:抽帧是稀疏采样(通常 10s+ 一帧),对话密集的场景大概率一句字幕都逮不到(哪怕片源带内嵌字幕),没法当逐句台词源用——两者分工不能互换,缺一不可。

## 产物契约(全部在项目目录 out/ 下)

| 文件 | 谁产出 | 是什么 |
|---|---|---|
| `out/media.json` | inspect_media | 源片元数据 |
| `out/transcript.json` | transcribe | 带说话人的全片 ASR |
| `out/shots.json` | detect_shots | 全片镜头时间轴(连续无洞) |
| `out/dialogue_axis.txt` + `out/dialogue_index.json` | arrange_footage(dialogue) | 带 D 编号的台词轴(D 编号唯一权威) |
| `out/outline.json` | **你写** | 角色表+分拍大纲(要点引 D 编号) |
| `out/reel.json` + `out/plan.json` + `out/writing_brief.txt` | arrange_footage(arrange) | 排片卷+写作简报(真实画面秒数/字数硬预算) |
| `out/writer_script.json` | **你写** | 分拍旁白(句子标注要点号) |
| `out/narration_script.json` + `out/graph.json` | arrange_footage(anchor) | 句级锚定解说稿+事件图 |
| `out/script_tts.json` | synthesize_narration | 配音音频+句级时长 |
| `out/edl.json` + `out/edl_qc.json` | bind_narration | 成片剪辑表+硬质检报告 |
| `out/final.mp4` | render_narrated | 成片(配音+字幕，不加 BGM) |
| `out/spot_review.json` + `out/report.md` | **你写** | 抽查记录+收尾报告 |

每一步产物已存在且校验通过即可跳过 = 断点续跑。

## 流程

### 1. 素材勘察与转录

`inspect_media(input_path=<film>)` → `speech_transcribe(input_path=<film>, language=<中文片传 zh,外语片传 auto>)`。长片(>30分钟)自动分块转录(块级缓存,断点续跑);transcript 应使用 ASR 的 speaker 字段。分块结果的说话人标签带 `p{块号}_` 前缀,同一人在不同块可能是不同标签——推断人物时按"称呼+语境"归并,不能只信标签。**块级缓存不区分 language:换 language 重转必须换 `work_dir`(或清掉旧的 `.video_agent/asr/<stem>_<hash>/`),否则会静默复用旧语种的块结果。**

### 2. 切镜头(可与转录并行)

`detect_shots(input_path=<film>)` → `out/shots.json`。约 150s/2小时片,有缓存。

### 3. 台词轴

`arrange_footage(action="dialogue", transcript_path="out/transcript.json")`。返回台词行数/字数;行数过少(<200 行长片)说明台词驱动不适用,回退 video-edit-agent。

### 3.5 视觉校对(外语片/说话人标签缺失时必做)

`video_ingest(video_path=<film>, transcript_path="out/transcript.json")` → 全片时间戳拼图(约每 10~15 分钟一张)。逐张对着台词轴看,边看边记人物/场景更正清单(谁是谁、关键道具、误读的动作主体),这份清单直接喂给下一步的大纲——**不是可选的美化步骤,是台词轴信息不足时唯一能修正人物归属和补全画面事实的通道**。中文片若说话人聚类清晰、台词自足,可跳过。

### 4. 你写大纲(读剧本)

通读 `out/dialogue_axis.txt`(有视觉校对清单时一并对照),像读剧本一样理解剧情,然后 Write `out/outline.json`:

```json
{"characters": [{"name": "潘生", "who": "一句话身份"}],
 "beats": [{"summary": "这拍剧情一句话",
            "points": [{"text": "要点(只写台词能支撑的事实)", "dlg": ["D0012", "D0013"]}]}]}
```

硬规则(逐条遵守):
- 拆约 `3×目标分钟数` 拍(13分钟≈39拍),每拍讲一个完整的小事,2~4 个要点。
- 拍与拍严格按电影时间顺序,不许倒叙穿插;保留主线因果链和反转,砍支线;删就整拍删,不许无中生有。
- 从台词内容推断人物名字(互相称呼/身份线索);推断不出的用"男主/反派头目"这类安全称谓。
- 每个要点必须引用真实存在的 D 编号(时间上邻近,跨度≤90秒)。**台词看不出的画面细节宁虚不编。**

### 5. 排片

`arrange_footage(action="arrange", dialogue_index_path="out/dialogue_index.json", shots_path="out/shots.json", outline_path="out/outline.json", minutes=<目标分钟>, chars_per_sec=<按音色>)`。

**chars_per_sec 必须按实际音色传**(默认 3.4 偏保守,成片会比目标短)。当前固定使用电影解说默认音色；首次批量运行前先 TTS 一两段实测总字数/speech_dur，再把测得值传给 arrange，不能沿用旧测速标定。

返回 `outline_invalid` → 按 data 里的 issues 重写大纲再试(≤2 次)。成功后看 `est_film_sec` 与目标的偏差、`seams_per_beat`(应≤2.5)。

### 6. 你写旁白(文案迁就画面)

**写之前先定文风**(不做这步写出来是"剧情复述",不是解说):
1. 给片子标类型(灾难/犯罪/爱情/科幻…),从技能内置的 `references/jieshuo_corpus.jsonl` 挑 1~2 篇同类高赞稿通读。库共 38 篇，字段为 `movie_types`/`like`/`script`；先按 `movie_types` 和 `like` 筛选再读取对应 `script`，不要一次把整库载入上下文。
2. 萃取"文风卡"写进 `out/style_card.md`,**只学手法不抄内容**。常见手法:悬念先行信息后置;人物先身份代称再揭名("这个煎蛋的男人叫杰夫,退役特种兵");短句动作链;可/却/竟/直到 转折词推进;关键台词冒号直给;用具体数字不用形容词;重音前破折号悬停("倒下的,是伊恩");结尾跳出剧情扣观众。禁忌:设问全片≤3处,代称揭名后就用名字。
3. 后续大纲、旁白、抽查都对照文风卡自检。**初稿写完后再做一次结构对照**:把范文和自己的稿子并排看,不比修辞比节奏——人家 10 秒推进几个信息、新人物怎么引入、多线怎么处理、哪里留白;差在哪就照人家的节奏改,像编辑改稿,不是套句式。

读 `out/writing_brief.txt`(每拍/每要点的真实画面秒数与字数预算),Write `out/writer_script.json`:

```json
{"beats": [{"idx": 1, "sentences": [{"text": "一句旁白。", "point": 1}], "highlight": true}]}
```

**写作姿势(先讲人话,再对画面)**:通读 writing_brief 了解每拍画面空间后,**先忘掉字数预算,像"昨晚看了部特好玩的电影、现在讲给没看过的朋友听"那样把整个故事讲下来**——自然的详略、自然的钩子(可谁想到/他不知道的是),然后再按拍归位。你是讲故事的人,不是填格子的人。给听众讲和给看过的人写摘要是两回事:听众只听一遍、没有画面记忆、记不住一次涌来的人名。所以——
- 每拍只推进**一件事**;一句里塞两个新人物/两层因果的,拆开或删掉一个。
- 新人物先给身份再给名("保卫科长包世宏"),一带而过的次要人物**不点名**(用"他手下/买家/那个助理")。
- 数字和细节只留影响剧情的;"赔了三千、驾照抵车灯钱"这类电报式堆叠,砍到一个。
- 多线剧情别跟着电影平行跳:一条线讲到段落再切,切线带一句路标(而另一边/镜头转到)。
- **故事完整优先,时长服从故事**:主线因果链一环不缺、关键转折和结局都要讲透,不许为省时长砍成梗概;篇幅不够讲完整,就在大纲阶段加拍、把目标分钟取大,**用时长换密度**——绝不许用"压缩句子塞信息"换时长。单拍内预算仍是上限不是目标:一拍讲一件事,讲完就停,画面多出来的就是呼吸。

硬规则:
1. 每拍字数不得超过它的总预算(宁少勿满,不许超);每个要点的句子总字数也不许超该要点上限,画面撑不起的宁可少讲;"无画面"要点不单独成句,一笔带过融进邻句。
2. 每拍只讲本拍要点,按要点顺序讲,不剧透后面的拍;每句标注它表达第几个要点(point,从 1 数)。
3. 口语化、短句、有悬念钩子;第一拍要有抓人的引子;人名用角色表名字;不写"镜头/画面/我们看到"。
4. 拍与拍衔接要有因果/转折连接(于是/没想到/而此时),整篇顺着读像一个人讲故事。
5. 要点若出自电话、转述或画外音台词,说话人多半不在画面里——措辞不点名动作主体,用"消息传来/电话那头/有人告诉他"这类说法,避免张冠李戴。
6. **挑 5~8 个强拍标 `"highlight": true`**(枪响/死亡/重大转折/开场炸点/结尾题眼)。只有这些拍的解说结束后会留 1~3s 原声呼吸留白——留白是标点不是空格,拍拍都停等于没有停,观感反而怪。

**写完必须做复述测试**(闭环改稿后同样要重做)。**测试不能自己做**——作者读自己的稿子永远觉得通顺,必须把纯文本稿丢给一个**不带任何上下文的子代理**(只给稿子,不给大纲/台词轴/你的对话历史),让它模拟"普通观众只听一遍、匀速念、不能回看",然后要它做两件事:
1. **闭卷复述**:读完后用自己的话把故事主线复述一遍(谁、想干什么、遇到什么、最后怎样)。**它复述不出来、复述错、张冠李戴的地方,就是稿子没讲明白的地方**——这是"听懂了没"的直接度量,比任何检查清单都准。
2. **感受流**:标出听到哪里"跟不上了/人物记混了/信息太密想倒回去/开始走神"。跟不上多半是信息密度超了,走神多半是流水账没钩子。

另外专项盯这几类硬伤——
- **信息断层**:动作/场景突然出现,没交代原因去向(人怎么到的、决定何时做的);
- **人物没户口/线头不收**:人名首次出现必须带身份钩子;开头出场的人物后文必须接住;隔场回归的人物补一笔关系;
- **修辞绕弯**:反着说的祝愿、双重否定、要"转弯"才懂的句子,口播一遍过来不及转;
- **结尾因果链**:高潮后的硬信息(谁赢了/危机怎么解的/底牌哪来的)不许被抒情句替代,翻盘用的每张牌前文必须见过;
- **指代/引语**:冒号引语前必须有说话主体;一句里多个"他"指不同人必拆;"这句话/那个人"必须有实体。
按复述缺口和感受流逐条修——**优先删和拆,不是补**(密度超了就删次要信息,不是加解释句;修复不许发明电影里没有的事实,只许删减、拆句、补过渡、补身份、把已有事实提前铺垫)。修完稿子变了要再测一轮,直到代理能把主线因果**顺畅复述**且感受流无"跟不上"。

### 7. 锚定

`arrange_footage(action="anchor", reel_path="out/reel.json", plan_path="out/plan.json", script_path="out/writer_script.json", title=<片名>)`。

- `over_budget` → data 里列了超预算的拍:删修饰不删事实,压缩改写那几拍后重跑(≤2 次)。
- `script_invalid` → 补齐缺拍。

### 8. TTS(逐句 + 忠实度回验,必开)

`synthesize_narration(script_path="out/narration_script.json", provider="cloud_tts", voice="zh_male_ruyaqingnian_uranus_bigtts", by_sentence=true, flatten_quotes=true, verify="asr")`。Movie 固定使用该解说音色；即使 `.env` 已配置，也要显式传 provider/voice，避免项目级环境覆盖。段级缓存会把音色纳入指纹，切换音色不会误复用旧产物；失败段会列出，`require_complete` 默认 true。

**为什么这三个参数必开**(Homestead 事故教训):LLM 类 TTS 不保证忠实朗读——遇到 `某人:"台词"` 会把冒号前当说话人标签吞掉、把引语拿去变声演绎,甚至自编对白(稿子"伊恩醒来时已过十天,珍娜坦然相告"被念成"我睡了多久?/你已经睡了十天了")。字幕烧原稿而语音是改写内容,观感就是"字幕的台词没有声音/多种人声/不像解说"。

- `by_sentence=true`:逐句合成,喂得短它没发挥空间;句级时间轴也从估算变真实,锚定更准。
- `flatten_quotes=true`:口播文本冒号→逗号、去引号(只动标点,字幕不动),消除"剧本腔"诱因。
- `verify="asr"`:每段合成后 ASR 回听,句级"内容命中+时长合理"双指标(ASR 自己会漏听,时长是独立第二证据),坏句自动删句缓存重合成 ≤2 轮。
- 返回 `verify.failed_seg_ids` 非空时**不许带病渲染**:看该段 `verify.failed_sentences` 里的句子,通常是内嵌引语/拟声的"死穴句"(如"一句你好都说不利索"),**改写该句**(去掉内嵌台词,换叙述表达)→ 重跑 anchor → 重 TTS(只有改的句子重合成)→ 复验通过再往下走。
- `verify.warn_seg_ids`(说话人>1 或命中偏低):抽听确认,多为引语演绎残留,可按同法改句或接受。

### 9. DP 绑定

`bind_narration(script_path="out/script_tts.json", graph_path="out/graph.json", timeline_path="out/shots.json", reel_path="out/reel.json")`。

- `footage_shortage` → data 指明哪拍的卷装不下旁白:压缩该拍文案 → 重跑 anchor → 重 TTS(缓存让未改的段免费)→ 重绑(≤3 轮)。
- 硬质检失败(短闪/倒退/重复)按 data 明细定位;正常情况排片器已保证不会发生。
- 呼吸留白默认只发给 highlight 拍(`tail_mode="highlight"`);要复刻旧的"拍拍留白"行为传 `"all"`,全关传 `"none"`。

### 10. 渲染与 QC

`render_narrated(edl_path="out/edl.json", video_path=<film>, timeline_path="out/shots.json", script_path="out/script_tts.json", bgm=false)` → `out/final.mp4`。

- **BGM 关闭**：固定传 `bgm=false`，当前流程不启用片内配乐。
- **外语片必须传 `bed_volume=0`**(解说期间垫底原声是**压低不是静音**,默认 0.13;外语片垫底几乎全是外语人声,必须归零。中文片保持 0.13 氛围垫底)。
- **留白透原声**:`tail_volume` 默认 0.85——高光拍的呼吸留白里原声 0.3s 渐入(枪响回荡/人群嘈杂/开门声);解说期间仍按 bed_volume 走。设 0 恢复留白纯静音。

然后 `qc_preview(video_path="out/final.mp4", timeline_path="out/shots.json")`(带 timeline 才有哈希追溯链,收尾门禁认它)。

### 11. 抽查与重绑(句画矛盾闭环)

从 `out/edl.json` 随机抽 ~10 个语义句窗口,用 `video_watch_segment`(源片,窗口的 source 时间,fps=3,批量 segments)逐句核对旁白与画面:

- **矛盾**(旁白断言的动作/人物与画面明显冲突):把该句窗口用到的 shot_id 收集起来,`bind_narration` 加 `avoid_shot_ids=[...]` 重绑一次,重新渲染;若仍矛盾,改写该句措辞(软化为台词能支撑的说法)走 anchor→TTS→bind。
- **中性**(画面不直接演绎但不冲突)不算失败。

结果写 `out/spot_review.json`(逐句 verdict)。矛盾率 >10% 时扩大抽查并优先怀疑大纲要点"把台词说的事写成了眼前发生的事"。

### 12. 收尾

`out/report.md`:目标/实际时长、拍数/句数/字数、节奏指标(edl_qc 的 rhythm:平均停留应 5.5~8s、<2s 碎片≤8%)、抽查矛盾率、遗留风险。

## 常见失败模式

- **旁白超时长**:永远先改文案,不动画面(anchor 的 over_budget / bind 的 footage_shortage 都是这个方向)。
- **张冠李戴**:台词在 A 场景说、事情在 B 场景发生——大纲要点只写"谁说了什么",旁白措辞用规则 5 的说法。
- **编号漂移**:大纲引用的 D 编号必须来自本次 `dialogue` action 的产物;换了 transcript 必须重跑 dialogue 和大纲。
