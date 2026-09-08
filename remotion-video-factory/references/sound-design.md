# sound-design — 三层音频与钉帧规则

## 三层结构

| 层 | 电平 | 说明 |
|---|---|---|
| VO 配音 | 1.0 | edge-tts 产物峰值 ≈ -2dB，不动 |
| BGM | ~0.34 | `BgmTrack` 首尾 30f/90f 淡入出；素材峰值接近 0dB 时 0.34 合适，录得轻的素材先归一化再入库 |
| SFX | 0.12–0.5 | 钉帧表逐点触发，见下 |

混音验收：完整版 `volumedetect` mean ≈ -20dB、max ≤ -2dB（削波即返工）。

## SFX 钉帧表规则

```tsx
const SFX: Sfx[] = [
  {from: SHOTS.hook.from + 55, src: "sfx/bass-hit.mp3", volume: 0.5, d: 60},
  {from: SHOTS.matrix.from + 40, src: "sfx/sweep.mp3", volume: 0.24, d: 36},
];
```

1. **from 一律相对表达式**（`SHOTS.x.from + offset`）——时间线重建后自动跟随，绝不写裸帧号。
2. **长音效（>1.5s）必给 `d`**（durationInFrames）：靠 Sequence 截断，否则拖到后续镜头。
3. **大 slam 全片 ≤3 处**（开场落定 / 中段转折 / 结尾字标），其余拍点只动元素层。
4. **连发防机枪感**：同款音效连打时音量阶梯递减。九连 pop 实测配方：
   `0.38 - i * 0.03`（第 1 声 0.38 → 第 9 声 0.14），间隔跟动画曲线走。
5. 钉帧时机 = 动画关键帧，不是"大概位置"：数字落定帧、卡片落地帧、过滤完成帧。
6. 画面时间线改动后，全表 SFX 重新核对一遍（音画错位是必查项）。

## 词汇 → 音效类别映射

| 画面动作 | 类别 | 音色判据 |
|---|---|---|
| 数字/字标落定 | impact | bass-hit / impact-cine |
| 过滤、扫过、转场 | transition | air-woosh / sweep |
| 铺垫、即将揭晓 | riser | riser-cine（长样本，必给 d） |
| 高亮、完成 | light | sparkle / shimmer（目录名是 light 不是 sparkle） |
| 逐项落入、激活 | ui·pop | 真实拟音 pop；合成 tone/bleep 一耳出戏，逐个试听 |
| 数字矩阵填充 | data | sweep-digital / data-compute |

禁用：游戏音包音色（卡通弹跳、合成器确认音）；但画面真有点击/开关就该配它的拟音——禁的是音色不是动作。

## BGM 选择

- 判据是"典型的信息视频"气质而不是"好听"：tech-house / 电子底鼓 / 纯节奏无强旋律
- 候选曲必须垫进成片试听（单听曲子选型不可靠）
- 强鼓点 BGM 的片子 SFX 克制：鼓点本身就是节拍音，SFX 只钉画面独有动作
- 文件放 `public/bgm/bgm.mp3`；无 BGM 版靠 `bgm:false` 渲出，不后期抽轨

## 结尾固定句式

```
riser（字标入场前 ~1.5s 起，d≈55）
  → impact（字标落定帧，全片音量峰值 0.5）
    → sparkle（+13f 余韵，0.26）
```

## 交付双版本

```bash
npx remotion render src/index.ts Video out/final.mp4 --concurrency=4
echo '{"bgm":false}' > props-nobgm.json
npx remotion render src/index.ts Video out/final-nobgm.mp4 --props=props-nobgm.json
```

无 BGM 版保留 VO + SFX，方便用户后期自配音乐或平台配乐。
Windows 下 `--props` 一律走文件（内联 JSON 的引号会被 shell 剥掉）。

## 素材来源

免费商用音效库（Pixabay、freesound CC0 等）或（若已安装）video-shotcraft 技能的
`assets/audio/`（149 个 SFX 按 16 类分目录，免费商用授权）。
**只放确认过授权的素材**；成片商用前自查授权链。
