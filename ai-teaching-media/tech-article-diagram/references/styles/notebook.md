# 风格: 网格笔记本手绘风 (notebook)

**适用场景**: 技术教程、个人博客、工程师向内容。传达"实战经验、接地气"的感觉。

## 风格基因(每个提示词必须包含)

```
Style: Hand-drawn sketch style diagram on grid notebook paper.
Black ink main strokes with slight irregularity (hand-drawn feel).
Green color for positive/growth elements and correct flow lines.
Red color for emphasis callouts (bordered red box).
Clean minimal layout, abundant white space.
Chinese text primary. English translations in parentheses for key concepts.
No photographs. No 3D rendering. No gradient fills. No shadows.
Hand-drawn arrows with slight irregularity.
```

## 补充说明

- **主笔**: 黑色墨水线条，带轻微不规整感（手绘感）
- **颜色分工**:
  - 绿色: 正向元素、正确流程、增长箭头
  - 红色: 强调 callout、关键警告、必记要点（必须用 bordered box）
  - 其他一律黑色
- **布局**: 简洁最小化，留足空白，不要密集信息堆砌
- **禁忌**: no photographs / no 3D / no gradients / no shadows

## 三条自检

每张图生成前过一下：

1. **对应原文**：这张图的"核心要表达"能在文章里找到支撑段落吗？不是说出来的，是从文章里找出来的。
2. **标题精准**：能不能用一句话概括？（好："Agent Profile & 真隔离"；烂："讲一下配置"）
3. **底部金句**：读者能不能记住并复述？（好："用进程隔离打造真实的多 Agent 协作基础"；烂："这就是 profile 的工作方式"）

## 骨架模板

每种图类型的完整骨架在 `prompt_template.md` 里，四种类型：

- 🧠 **抽象概念可视化**（中心辐射式）: 核心概念 + 多个子元素用箭头指向中心
- 🔄 **流程/循环/时序**: 线性步骤 or 循环流程
- ⚖️ **对比/分类**: 左右分栏 + VS 标识
- 🏗️ **架构/组件关系**: 分层架构，层层往下
