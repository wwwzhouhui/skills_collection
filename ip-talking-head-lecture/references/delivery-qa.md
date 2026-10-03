# 成片验收

出片后**必须**走一遍。清单按「机器能查的 → 只能眼看的」排序。

## 一、机器可查

```bash
F="<build>/<期>/outputs/final-16x9.mp4"

# 1. 规格对得上吗
ffprobe -v error -show_entries format=duration,size,bit_rate \
  -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames \
  -of default=noprint_wrappers=1 "$F"
#   期望：h264 + aac / 1920x1080 / 30fps / 时长 = 旁白稿里的秒数 ±0.2s
#   竖屏版应是 1080x1920

# 2. 有没有音轨、响度正不正常
ffmpeg -v error -i "$F" -af "volumedetect" -f null - 2>&1 | grep -E "mean_volume|max_volume"
#   max_volume 接近 0dB 说明削波了 → 把 config.json 的 tts.loudness 调小

# 3. 有没有静默断片（某段配音没生成成功）
ffmpeg -v error -i "$F" -af "silencedetect=noise=-45dB:d=2.5" -f null - 2>&1 | grep silence_start
#   正常只会出现在首尾；中间出现长静音 = 那段音频缺失

# 4. 抽关键帧看一眼（每个场景抽一帧）
ffmpeg -v error -ss 3 -i "$F" -frames:v 1 -q:v 2 f1.jpg

# 5. 字幕条数：中英必须一致（不一致说明英文没生成）
grep -c -- "-->" "<期>/字幕.srt" "<期>/字幕.en.srt"
#   两个数字应当相同；只列出中文那一行 = 没有英文字幕（publish.en.cues 没填或条数不符）
```

**时长是否对得上，看旁白稿**：`<期>/旁白稿.md` 里有每场景的起止秒与总时长，和 ffprobe 的总时长应当一致。

## 二、只能眼看的（抽帧逐项核对）

对每个场景抽一帧，检查：

- [ ] **数字人在右下角**，圆内没有露出版权水印 / LOGO（AI 生成的口型帧容易带水印）
- [ ] **口播形象是预期的那套**（`timeline.json` 的 `avatar.preset` 字段）= 成片里看到的那套。换过 `--preset` 却没重 build 会出旧形象
- [ ] **数字人没有被字幕挡**，也没有压到内容卡片
- [ ] **字幕在底部居中**，一行不超宽、不与数字人重叠、没有溢出画面
- [ ] **字幕文字与旁白一致**，断句读起来顺
- [ ] **标题不超框**：长标题会不会顶到右边进度号、会不会换行得很丑
- [ ] **内容卡片没有溢出**内容区（尤其 `steps`/`compare` 在竖屏下）
- [ ] **左下角水印**存在且不遮挡内容
- [ ] 顶部进度条在走

## 二之二、发布文案与字幕（`发布文案.md`）

- [ ] **YouTube 章节满足三条件**：首条 `0:00`、至少 3 条、**每条 ≥10 秒**。任一条不满足 YouTube 会**整组丢弃**章节 —— 这份是脚本按「不足 10 秒并入上一章」自动合并过的，改分镜后要重看
- [ ] **中英字幕同一条时间轴**（`grep -c -- "-->"` 两个数字相同），英文不是机翻腔
- [ ] **章节在中英两段描述里都是对应语言**（英文段里不该出现中文标题 → 说明 `chapterTitlesEn` 没填）
- [ ] **平台文案里没有残留的 `{{chapters}}`**（拼错了就会原样印出来）
- [ ] **文案里的数字与成片一致**：时长、分镜数（改了旁白就会改时长，文案里那句"56 秒 / 6 个分镜"要跟着改）
- [ ] YouTube 标题 ≤100 字符、描述 ≤5000 字符、tags ≤500 字符

## 三、必须两版都看

横屏版式（多列横排）和竖屏版式（纵向堆叠）**是两套布局**，横屏好看不代表竖屏好看。

```bash
iph still <期> 12                # 横屏
iph still <期> 12 --ratio=9:16   # 竖屏
```

竖屏重点看：卡片是否被压成窄条、字号是否太小、数字人是否和内容打架。

## 四、已知的坑（本机环境）

| 现象 | 真因 | 处置 |
|---|---|---|
| `spawnSync/execFileSync ... EBUSY` | 本机 Node 的**同步**进程调用不可用 | 已全部改成异步（`lib/tts/run.mjs`）；新代码别写 `execFileSync` |
| `SAFE_DELETE_BULK_GUARD_ERROR` | 本机 safe-delete 拦批量删除 | 别用 `fs.rmSync(dir,{recursive:true})`；改成按文件名覆盖写入 |
| 渲染时出现 `PROGRAM BLOCKED BY SECURITY POLICY - WMIC.exe` | Remotion 的 studio-server 会探测本机编辑器进程，调了 WMIC，被安全策略拦下 | **无害**，渲染照常继续。想彻底消掉就在安全中心把 WMIC 移出黑名单 |
| 首次渲染很慢 | Remotion 在打包 webpack bundle（每次调用一次） | 正常。一次 `iph render` 只 bundle 一次，多出静帧反而慢（每张都要 bundle） |
| 渲染中文变方块 | 缺中文字体 | 装 HarmonyOS Sans SC / MiSans / 思源黑体任一 |
| **只有第 1 个场景有字幕，数字人也只有首场景有说话光环/声波条** | `timeline.json` 的 `cues`/`words` 是**相对场景**时间，而 `<Subtitles>`/`<TalkingAvatar>` 挂在顶层拿的是**全局帧**，`sceneStart` 被加了两次（首场景 `start=0` 恰好掩盖） | 已在 `IpLecture.tsx` 用 `toGlobal()` 统一平移到全局时间并传 `sceneStart={0}`。改字幕/口型相关代码后，**必须抽一帧非首场景**核对 |
| 竖屏字幕条超出画面左右边 | `Subtitles` 的 `maxWidth` 默认 1240 > 1080 | 已在 `config.layout.<画幅>.subtitle.maxWidth` 收敛（竖屏 940）；改画幅时确认该值小于画幅宽度 |
| 竖屏卡片被拉得很长、卡内大片空白 | 版式组件里写了 `flex: 1`，横屏（row）是横向分栏，竖屏 `flex-direction: column` 下会被**纵向拉伸填满内容槽** | 竖屏一律用 `flex: col ? '0 0 auto' : 1`。新增版式时两种画幅都要看 |
| 竖屏长字幕折行后第二行只剩一两个字 | 1080 宽放不下 24 字的句子 | `Subtitles` 已加 `textWrap: 'balance'` 让两行均衡；若仍难看就调 `subtitle.fontSize` 降一档 |

## 五、交付

- 成片：`outputs/final-16x9.mp4`、`outputs/final-9x16.mp4`
- 字幕：`<期>/字幕.srt` · `字幕.vtt`（中文）· `字幕.en.srt` · `字幕.en.vtt`（英文）
- 旁白稿：`<期>/旁白稿.md`（含每场景起止秒，改稿对着它改）
- 发布文案：`<期>/发布文案.md`（主用标题 + YouTube 中英双语 + 各平台）
- 给用户的回复里**直接贴主用标题 + 各平台描述**，别只说"任务完成"。
