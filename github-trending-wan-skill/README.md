# GitHub Trending Wan Skill

抓取 GitHub Trending 当日热门开源项目，翻译为中文摘要，生成信息图海报 Prompt，并调用 Wan 2.7 生成可视化海报。

## 功能概览

- 抓取 GitHub Trending **Top 5** 项目，获取 Star、语言、技术栈、README 摘要等元数据
- 调用 DashScope 兼容 API，将英文摘要字段翻译为简体中文
- 生成低信息密度的中文简报（Markdown）和 Wan 2.7 海报 Prompt
- 支持 **10 种视觉风格**（坐标蓝图 / 复古波普 / 文件夹 / 热敏纸 / 复古手帐 / 陶土手绘 / 酸性复古 / 剧场票据 / 矢量插图 / 孟菲斯网格）
- 采用 **3 步引导式工作流**：启动询问 → 信息提取 → 确认生图

## 目录结构

```
github-trending-wan-skill/
├── SKILL.md                           # Skill 定义文件（Claude Code 加载）
├── README.md                          # 本文件
├── scripts/
│   ├── fetch_daily_top10.py           # 抓取 GitHub Trending
│   ├── translate_daily_top.py         # 中文翻译
│   ├── build_daily_poster_assets.py   # 生成简报 + Wan Prompt
│   └── run_wan_generation.py          # 调用 Wan 2.7 生图
└── output/                            # 产出文件（自动生成）
    ├── daily_top10.json               # 抓取原始数据
    ├── daily_top5_zh.json             # 翻译后数据
    ├── daily_brief.md                 # 中文简报
    ├── wan_prompt.txt                 # Wan 2.7 Prompt
    └── wan_result.json                # 生图结果（task_id / 图片 URL）
```

## 环境要求

- Python 3.10+
- 网络可访问 GitHub 和 DashScope API

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 是 | DashScope API 密钥，用于翻译和 Wan 2.7 生图 |
| `GITHUB_TOKEN` | 否 | GitHub Personal Access Token，减少 API 限流 |
| `WAN_SKILL_DIR` | 否 | Wan 2.7 脚本目录，默认查找同级 `Wan-skills-main/skills/wan2.7-image-skill` |

## 外部依赖

本 Skill 依赖 [Wan-skills-main](https://github.com/anthropics/wan-skills) 提供的 Wan 2.7 生图脚本。

默认目录布局（零配置）：

```
parent-directory/
├── github-trending-wan-skill/    # 本项目
└── Wan-skills-main/              # Wan 2.7 脚本（同级目录）
    └── skills/wan2.7-image-skill/scripts/
```

自定义位置：

```bash
export DASHSCOPE_API_KEY=your-api-key
export WAN_SKILL_DIR=/your/path/to/wan2.7-image-skill
```

## 使用方式

### 方式一：作为 Claude Code Skill 使用（推荐）

将本项目放到 Claude Code 的 Skills 目录下，对话中触发即可：

```
用户：帮我看看今天 GitHub 有什么热门项目
用户：做一张开源日报海报
用户：GitHub trending Top 5
```

Claude Code 会自动加载 `SKILL.md`，按 3 步引导式流程执行。

### 方式二：命令行手动执行

#### 步骤 1：抓取 Trending

```bash
python3 scripts/fetch_daily_top10.py \
  --top 5 \
  --date-label "2026-04-08" \
  --output output/daily_top10.json
```

#### 步骤 2：翻译为中文

```bash
python3 scripts/translate_daily_top.py \
  --input output/daily_top10.json \
  --output output/daily_top5_zh.json
```

翻译模型从 12 个候选中随机选取，也可指定：

```bash
python3 scripts/translate_daily_top.py \
  --input output/daily_top10.json \
  --output output/daily_top5_zh.json \
  --model glm-5
```

#### 步骤 3：生成简报和 Prompt

```bash
python3 scripts/build_daily_poster_assets.py \
  --input output/daily_top5_zh.json \
  --brief-output output/daily_brief.md \
  --prompt-output output/wan_prompt.txt \
  --audience "开发者 / 技术团队" \
  --style 10 \
  --size 2K \
  --ratio 3:4
```

`--style` 参数对应 10 种视觉风格：

| 编号 | 风格 | 适用场景 |
|------|------|----------|
| 1 | 坐标蓝图 | 技术参数、专业评测 |
| 2 | 复古波普 | 干货清单、对比表格 |
| 3 | 文件夹 | 系统指南、分类清单 |
| 4 | 热敏纸 | 步骤清单、时间线 |
| 5 | 复古手帐 | 案例研究、调查分析 |
| 6 | 陶土手绘 | 轻松干货、亲和科普 |
| 7 | 酸性复古 | 数码评测、极客内容 |
| 8 | 剧场票据 | 故事演进、系列指南 |
| 9 | 矢量插图 | PPT 封面、场景插画 |
| 10 | 孟菲斯网格 | 高密度信息、艺术指南 |

#### 步骤 4：调用 Wan 2.7 生图

```bash
python3 scripts/run_wan_generation.py \
  --prompt output/wan_prompt.txt \
  --size 2K \
  --ratio 3:4 \
  --n 1
```

若返回 `task_id`，查询任务状态：

```bash
python3 scripts/run_wan_generation.py \
  --task-id <task_id>
```

## 数据流

```
GitHub Trending (Web)
       │
       ▼
fetch_daily_top10.py ──► daily_top10.json (英文原始数据)
       │
       ▼
translate_daily_top.py ──► daily_top5_zh.json (中文翻译数据)
       │
       ▼
build_daily_poster_assets.py ──► daily_brief.md (中文简报)
                               ├► wan_prompt.txt (Wan 2.7 Prompt)
       │
       ▼
run_wan_generation.py ──► wan_result.json (图片 URL / task_id)
```

## 输出示例

### 中文简报 (`daily_brief.md`)

包含 4 个模块：
1. **榜单概览** — 日期、语言分布、热点方向
2. **Top 5 项目卡片** — 项目名、是什么、解决什么问题、技术栈、Star 数
3. **热点方向** — AI/Agent、前端/Web、开发工具等
4. **一句话结论** — 当日趋势总结

### Wan Prompt (`wan_prompt.txt`)

包含完整的视觉目标、版式要求、禁止事项和画面文案，可直接提交 Wan 2.7 生成 3:4 信息图海报。

## 常见问题

**Q: 翻译失败怎么办？**
翻译脚本会从 12 个候选模型中随机选取。如果某个模型不可用，可用 `--model` 指定其他模型重试。

**Q: 没有 `DASHSCOPE_API_KEY` 能用吗？**
可以运行步骤 1（抓取）获取英文数据，但步骤 2（翻译）和步骤 4（生图）需要 API Key。

**Q: 如何自定义风格？**
修改 `scripts/build_daily_poster_assets.py` 中的 `STYLE_MAP` 字典，添加或调整风格配置。
