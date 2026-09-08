# <视频标题> — 设计 spec

## 简报

- **主题**：
- **目标观众**：
- **时长**：
- **风格 / 调性**：
- **核心结论**（观众看完要记住的一句话）：
- **发布渠道**：
- **品牌素材**（Logo/色/字体，无则留空）：

## 视觉 tokens（theme.ts 对应值）

| 项 | 值 |
|---|---|
| 底色 / 面板 | #050712 / #0b1024 |
| 主强调 / 次强调 / 警示 | #56e5ff / #8b7cff / #ffcf66 |
| 主入场缓动 | bezier(0,0,0.2,1) ~21f |

## 分镜表（段落 = VOICEOVER_ZH.md 段落 = build/scenes.json 条目）

| # | id | 时长预估 | 画面 | 动画模式 | SFX | visualMin |
|---|---|---|---|---|---|---|
| 1 | hook | 10s | 大数字滚动 | counter | impact@+55 | 300 |
| 2 | matrix | 15s | 矩阵逐格点亮 | stagger-grid | sweep@+40 | 420 |
| 3 | cards | 10s | 三卡片弹簧 | spring-cards | pop×3 | 240 |

> 时长列在配音生成后由 build-timeline.mjs 覆盖为 `max(visualMin, 配音+40f)`。

> 此表与 `build/scenes.json` 一一对应（id / visualMin / tail / vo），改分镜时两处同步。
