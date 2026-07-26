# 分镜脚本指南 (storyboard.json)

> 两条管线共用的第一步: 概念 → 7 段分镜。
> 配音视频和无声动图共用同一份分镜和同一个 `index.html`: 先按分镜跑 TTS, 再生成 `index.html`。
> **同一概念先写一份 storyboard, 再分别产出**, 保证 GIF 和视频的知识点拆解、配色、结构完全一致。

## 7 段结构 (锁定)

| 段 | 角色 | 内容要求 |
|---|---|---|
| 1 | 标题引入 | 主题名 + 子概念一览 + 主题图标; 旁白抛出问题或生活场景钩子 |
| 2 | 核心概念 | 最根本的那条原理 (如"声音由振动产生") |
| 3-6 | 子概念展开 | 每段讲透一个点; 有对比的用对比 (高频vs低频、大振幅vs小振幅) |
| 7 | 总结收尾 | 关键数字/公式 + 全章要点回顾 + summary bar |

**拆解原则**:
- 子概念按教材逻辑排序 (是什么 → 怎么传 → 有什么特性 → 怎么用), 不按趣味排序
- 每段只讲一个点, 讲不完就砍内容, 不要压缩语速
- 有具体数字就用具体数字 (声速 340 m/s、光速 3×10⁸ m/s), 数字是记忆锚点
- 拆解要对着教材知识点走, 参考 `examples/sound-video/storyboard.json` 的结构:
  振动发声 → 声波传播 → 音调 → 响度 → 音色 → 声速与总结

## storyboard.json 格式

```json
{
  "topic": "声现象",
  "topic_slug": "sound-phenomena",
  "chapter": "初二物理·第2章",
  "palette": "sound",
  "voice": { "provider": "minimax", "voice_id": "female-chengshu", "speed": 1.0 },
  "segments": [
    {
      "id": 1,
      "title": "引入",
      "narration": "同学们，你有没有想过，我们每天听到的各种声音，到底是怎么产生、又是怎么传到耳朵里的？今天我们就来揭开声现象的秘密。",
      "visual": "主标题'声现象' + 音叉图标 + 六个子概念胶囊横排; 标题从下方浮入, 图标随后淡入",
      "transition": "blur-crossfade",
      "min_duration": 6
    }
  ]
}
```

字段说明:
- `palette`: 对应 `references/color-palettes.md` 里的主题族 (sound/light/mechanics/electricity/heat/biology/chemistry/history/math)
- `visual`: 画面描述, 要具体到"左边什么示意图、右边什么卡片、什么东西动"; 这段文字就是写 HTML 场景的依据
- `transition`: 该段**结束时**的转场; `blur-crossfade` (默认, 平缓) / `push-up` (推进感, 用在进入总结段等转折处), 全片 push 不超过 2 次
- `min_duration`: 可选, 画面复杂时保底时长 (默认 5s)

## 旁白文案规范

**像老师在课堂上讲, 不是念课本。**

- 每段 30-50 字。中文口语约 4-5 字/秒, 50 字 ≈ 11 秒, 再长画面就拖了
- 口语化: 用"同学们看""你发现没有""这就是为什么"; 用短句, 读起来要有停顿感
- **不读公式**: 画面上写 `v=340m/s`, 旁白说"每秒能跑 340 米"; 画面写 `F₁L₁=F₂L₂`, 旁白说"力乘力臂, 两边相等"
- 数字读法写进文案: "3×10⁸" 写成"三亿米每秒"; TTS 是照字念的
- 首段要有钩子 (提问/生活场景), 末段要有收束 ("这就是……的全部秘密")
- 每段结尾自然收口, 不要"接下来我们看"式的悬空 (转场自己会衔接)

参考范例 (振动发声段, 42 字):
> 同学们看，当我们拨动这根弦，它来回振动，就会发出声音。振动停了，声音也跟着消失了。这就是声音产生的原理。

## 配音 (Minimax / Edge TTS)

```bash
# 默认: storyboard.voice.provider → 有 MINIMAX_API_KEY 用 minimax, 否则 edge（需外网）
# pip install -r ../requirements-tts.txt   # edge-tts
# export MINIMAX_API_KEY=...              # 仅 minimax 需要
# export EDGE_TTS_VOICE=zh-CN-YunxiNeural  # 仅覆盖 edge 默认音色
python3 scripts/minimax_tts.py storyboard.json --outdir audio/ --provider edge
# 或: python3 scripts/minimax_tts.py storyboard.json --outdir audio/ --provider minimax
# 续跑: --skip-existing（成功句即时写入 tts-cache.json 指纹）
```

storyboard 可写 provider 专属音色：

```json
{
  "voice": {
    "provider": "minimax",
    "voice_id": "host-voice-default",
    "edge_voice_id": "zh-CN-YunxiNeural",
    "speed": 1.0
  }
}
```

- 没有 API key 时默认走 edge；也可用 `--provider say` (macOS 内置) 预览管线
- Edge 是在线服务：需外网，可能限流；批量失败用 `--skip-existing` 续跑或切 minimax
