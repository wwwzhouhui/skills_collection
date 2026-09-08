# 案例：《1M 上下文的秘密》2 分钟技术讲解片

本 skill 的第一个实战项目（2026-09）。输入：一个主题 + 8 段中文旁白。
产出：125s / 1920×1080 / 30fps，VO+BGM+SFX 完整版 + 无 BGM 版 + SRT。

## 分镜（8 场景）

| # | id | 内容 | 动画模式 | SFX |
|---|---|---|---|---|
| 1 | hook | 数字滚到 1,000,000 | counter | whoosh + impact + sparkle |
| 2 | context | 文档块流入 Transformer 窗口 | stagger 入场 + progress-fill | pop×6 递减 |
| 3 | cost | N×N 矩阵逐格点亮，O(n²) | stagger-grid | sweep-digital |
| 4 | sparse | 稠密矩阵过滤为稀疏连接 | filter-transition | whoosh + impact |
| 5 | gqa | 8 Query 头汇聚 2 组 KV | svg-lines | sweep-fast |
| 6 | cache | 逐 Token 激活 + 缓存累积 | incremental-activation | pop×9 递减 |
| 7 | summary | 三技术卡片总结 | spring-cards | bass-hit×3 递减 |
| 8 | closing | 大字定格 + 副标 | typographic-hold | riser→impact→sparkle |

时间线由实测配音重建：8 段 edge-tts（yunyang）总 113.6s，
场景 = max(visualMin, VO+40f)，全片 3760f = 125.3s。

## 数据

- 配音：zh-CN-YunyangNeural，8 段，峰值 -1.5～-3.6dB
- BGM：tech-house（峰值 0dB）→ 0.34 增益
- SFX：28 个钉帧点，全部 `SHOTS.x.from + offset` 相对表达式
- 混音：mean -20.5dB / max -2.5dB（无削波）

## 踩坑记录（已固化进 SKILL.md 硬规则）

1. Root.tsx 误渲染场景组件 → "No video config found"（坑时 15 分钟）
2. v1 无音频即交付 → 用户第一反馈就是"没声音"；音频是第一版就该有的，不是后补
3. 旁白实测普遍比估算长 10–15% → 时间线必须按实测重建，不能按字数估算拍脑袋
4. 长音效（impact-cine 8s）不截断会盖过后续镜头 → Sfx.d 必填
5. fade 出点写死数字 → 场景时长变化后淡出错位 → D prop 化

## 效果定性

- 技术图解（矩阵/连线/缓存流程）代码绘制：文字零乱码、结构精确、可参数化
- 对比口播优先方案（voice-to-video）：视觉表达力明显更强（矩阵逐格、SVG 拓扑、
  增量激活都是声明式动画体系写不了的），但迭代成本更高（改稿要重跑两个脚本 + 重渲）
