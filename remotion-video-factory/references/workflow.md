# workflow — 八步工作流细节

每步给出操作、产出与已知坑。入口规则见 SKILL.md。

---

## §1 简报（不写代码先定方向）

产出 `DESIGN.md` 头部：主题 / 观众 / 时长 / 风格 / 核心结论 / 渠道 / 品牌素材。

判断依据：
- 内容以**结构/数据/流程**为主 → 本流水线最强项
- 需要引用**产品真实界面** → 让用户提供截图/录屏（AI 编造 UI 必穿帮），或改走 video-shotcraft
- 需要真人出镜 → 本流水线不适合

时长预估：旁白字数 ÷ 4.2 字/秒 + 每场景 1.3s 尾巴 ≈ 成片时长。

---

## §2 旁白稿 + 分镜表

1. 写 `VOICEOVER_ZH.md`：**一段 = 一个场景**，段落间空行。口语化短句，单段 ≤120 字。
2. 写 `DESIGN.md` 分镜表：每镜一行，含 `id`（与 scenes.json 一致）、画面、动画模式
   （查 animation-vocabulary.md）、SFX 计划、`visualMin`（纯视觉动画需要的最短帧数）。

visualMin 估法：动画完成帧 + hold ≥45f。例：矩阵动画 127f 完成 → visualMin ≈ 300。

---

## §3 搭工程

```bash
cp -r <skill>/assets/template-project <video_dir>    # PowerShell: Copy-Item -Recurse
cd <video_dir> && npm install && npx tsc --noEmit   # 必须先过类型检查
```

模板自带：lib 三件套（theme/primitives/audio）、示例 3 场景、静音占位音频
（保证 `npm install` 后**零配置可渲**）、预置 props-nobgm.json。真实配音/音效到位后覆盖占位文件。

改场景清单时：`src/types.ts` 与 `src/timeline.ts` 由 build-timeline.mjs **每次重跑自动重生成**，
只需同步 `Video.tsx` 的 sceneNodes。

模板按 **1920×1080 横屏**设计；竖屏 9:16 需改 Composition 的 width/height 并重排布局，
本 skill 未提供竖屏预设。

---

## §4 配音（tts.py）

```bash
python3 <skill>/scripts/tts.py --script VOICEOVER_ZH.md --out . --voice yunyang
# Windows 命令是 python（无 python3）；可选 --rate +10%（提速）/ -5%（放慢）
```

稿子里的 Markdown 标题（#）、引用（>）、代码块会被 tts.py 自动剥离，只有正文段落进入配音。

产出 `public/vo/scene{N}.mp3` + `build/durations.json`（实测每段秒数与帧数）。

音色：yunyang 播报（技术讲解默认）/ yunjian 沉稳 / yunxi 阳光 / xiaoxiao 女声通用。
429 限流：脚本已内置 3 次退避重试；仍失败换网络或稍后再跑（幂等，重跑覆盖）。

**审听点**：技术名词读音（GQA/Q/KV 是否别扭）、断句是否破坏语义。
不满意 → 改稿子重跑本步，成本 1 分钟。

---

## §5 时间线（build-timeline.mjs）

手写 `build/scenes.json`（与分镜表一一对应）：

```json
[
  {"id": "hook", "visualMin": 300},
  {"id": "matrix", "visualMin": 420, "tail": 60},
  {"id": "logo", "visualMin": 150, "vo": false}
]
```

```bash
node <skill>/scripts/build-timeline.mjs
```

产出 `src/timeline.ts`（FPS / SHOTS / SCENE_ORDER / VO_MAP / TOTAL_FRAMES）+
`src/types.ts`（SceneId 联合类型）——两者**每次重跑自动覆盖**，勿手改；
`build/subtitles.srt`（逐句切分，按句长在配音区间内加权估算；精确逐词对齐走 voice-to-video）。

规则：场景时长 = `max(visualMin, 配音帧数 + tail(默认40))`；
`vo:false` 的纯视觉镜头不消耗配音段。脚本会校验 id 唯一性、数值合法性与段数一致。
注意：`build/scenes.json` 与 DESIGN.md 分镜表是同一信息的两份拷贝，改分镜时两处同步。

---

## §6 场景实现（最重的阶段）

1. 每个场景一个组件，签名 `React.FC<SceneProps>`（`{D}` = 场景时长）。
2. 动画模式从 `animation-vocabulary.md` 选，**一种手法全片只当一次主角**。
3. 场景根元素 `opacity: fade(frame, D)` —— 出点自动跟随时间线重建。
4. **每镜头完成即 QA**（最高频动作，别攒到最后）：

```bash
npx remotion still src/index.ts Video out/qa/<scene>-a.png --frame=<入场中>
npx remotion still src/index.ts Video out/qa/<scene>-b.png --frame=<落定后>
```

肉眼检查：构图 / 文字锐度 / 穿帮 / 动画是否在 D 内完成。

5. 全片第一次渲染后 ffmpeg 抽帧回看关键镜头：

```bash
ffmpeg -y -v error -i out/final.mp4 -vf "select='not(mod(n,150))',scale=480:270,tile=4x3" -frames:v 1 out/qa/contact-sheet.png
```

已知坑：
- Root.tsx 渲染的必须是 `<MyComposition />`，不是场景组件（报 "No video config found"）
- 确定性：禁 `Date.now()/Math.random()`，伪随机用 `mulberry32(seed)`
- 文字放在 120px 安全边距内；1080p 主标题 ≥70px、正文 ≥28px

---

## §7 声音设计

详见 `sound-design.md`。要点：
- SFX 钉帧表集中在 Video.tsx 顶部，`from` 一律 `SHOTS.x.from + offset`
- 长音效（>1.5s）必给 `d`（durationInFrames）
- 大 slam 全片 ≤3 处；连发音效用音量阶梯递减
- BGM 由 `bgm` inputProp 包裹（模板已内置）

---

## §8 渲染与交付

```bash
npx tsc --noEmit          # 先过类型
npx remotion render src/index.ts Video out/final.mp4 --concurrency=4
npx remotion render src/index.ts Video out/final-nobgm.mp4 --props=props-nobgm.json
# props-nobgm.json 模板已预置；Windows 勿用 echo > 生成（PowerShell 会写 UTF-16 导致解析失败）
```

验收清单：
- [ ] `ffprobe` 成片：分辨率/帧率/时长正确；音轨为 AAC 非静音
- [ ] `volumedetect`：完整版 mean ≈ -20dB，max ≤ -2dB（削波即返工）
- [ ] 抽查 3–4 个时间点音画对应（旁白说到 X 时画面正是 X）
- [ ] 交付：final.mp4 + final-nobgm.mp4 + build/subtitles.srt + out/qa 静帧

向用户报告：成片路径、时长、两版差异、改稿/改画面分别重跑哪步
（改稿 → §4§5 两脚本 + 重渲；改画面 → §6 + 重渲；换 BGM → 换文件 + 重渲）。
