# 五步流程详解与参数全表

## 数据流

```
二维码图片
   │  upload（PicList → 腾讯 COS）
   ▼
公网 URL  ─────────────────────────────────┐
   │                                        │
   ├─ replace-skill → SKILL.md / README.md / templates ×6
   │        │                               │
   │        ▼                               │
   │  sync-runtime → ~/.workbuddy/skills/github-readme-generator
   │                                        │
   ├─ plan（清单比对，可能触发用户决策）      │
   │        │                               │
   │        ▼                               │
   └─ update-repos → N 个仓库 README.md ◄───┘
            │
            ▼
        push（只 add README.md）
            │
            ▼
        verify（全链路核对）
```

## 步骤细节

### upload

| 参数 | 说明 |
|---|---|
| `image` | 图片绝对路径，必填 |
| `--keep-filename` | 保留原文件名。默认会改名成 `qr-<时间戳>-<随机hex>.<ext>`，用于击穿 CDN/GitHub camo 缓存 |

内部动作：
1. magic bytes 校验（png / jpg / gif / webp），非图片直接拒绝
2. `< 8KB` 告警（多半是缩略图）
3. `POST config.upload.api`，body `{"list": ["<windows 路径>"]}`
4. 取 `result[0]`，再 HEAD 回访确认 200/206
5. 把 `from_url`（当前 SKILL.md 的群二维码）和 `to_url` 写进 state，供后续 `update-repos` 兜底

state 位置：`%TEMP%/qr-rotator/state.json`。跨命令靠它传 `from_url`，但**关键参数仍然显式传 `--url`**，不依赖隐式状态。

### replace-skill

改哪些文件由 `config.skill_files` 决定，默认 `SKILL.md`、`README.md`、`templates/*.md`。

单文件替换算法：
1. 找标题行：`^#{1,6}[^\n]*技术交流群`；找不到就退化成正文关键词定位
2. 章节范围 = 标题行末尾 → 下一个任意标题行之前
3. 取章节内**最靠前**的图片（markdown `![]()` 或 HTML `<img src>`）
4. alt 若匹配文件名式（`image-\d+`、UUID、或带图片后缀）→ 换为新文件名；否则保留
5. **护栏**：替换前后收集全文所有图片 URL，必须满足 `删掉的 == {旧群码}` 且 `新增的 == {新群码}`，否则整文件放弃、回退原文

第 5 条是防「手一抖把打赏码改了」的最后一道闸，别绕过它。

### sync-runtime

| 目标状态 | 行为 |
|---|---|
| 运行环境无此 skill | 完整安装：顶层所有条目（跳过 `.` 开头、`logs`、`config.install_exclude`、`.mimosa`、`__pycache__`） |
| 运行环境已有 | 只覆盖 `config.skill_files` 列出的 8 个文件，并逐字节比对 |

判定「是否最新」用 `diff` 或字节比较，不看时间戳——时间戳会被 git checkout 之类打乱。

### plan

输入解析能力：

| 输入形态 | 是否支持 |
|---|---|
| `/mnt/f/work/code/github/...` | ✅ 自动映射成 `F:/work/code/github/...` |
| `F:\work\code\github\...` | ✅ 反斜杠转正斜杠 |
| markdown 表格整段粘贴 | ✅ 正则抠路径 |
| 一列纯路径 | ✅ |
| 相对路径 `wwwzhouhui/xxx` | ✅ 视为相对 `base_dir` |

比对结果四分类：`same`（在册且在清单）、`added`（清单有、不在册）、`removed`（在册、清单没有）、`excluded`（命中排除名单）。

`removed` **不会自动从清单里删**——只有 `--policy replace --update-manifest` 才会。

### update-repos

| 参数 | 默认 | 说明 |
|---|---|---|
| `--url` | state 里的 `to_url` | 目标新链接 |
| `--from-url` | state 里的 `from_url` | 章节识别失败时的精确替换兜底 |
| `--policy` | `keep` | `keep` / `merge` / `new-only` / `replace` |
| `--list` | — | 清单文件，`merge` 等策略必需 |
| `--dirs` | — | 逗号/分号/换行分隔的目录，绕过清单直接用 |
| `--update-manifest` | 关 | 按 policy 把结果写回 `projects.json` |
| `--backup-dir` | `%TEMP%/qr-rotator` | 备份根目录 |
| `--dry-run` | 关 | 只报告不写盘 |

单仓库处理顺序：
1. 目录不存在 → `MISSING`
2. 无 README.md → `NO_README`
3. 编码探测失败 → `DECODE_FAIL`
4. 章节内二维码 == 新链接 → `ALREADY`
5. 章节内找到二维码 → 换 → `ROTATED`
6. 章节找不到，但 `--from-url` 在文里 → 精确替换 → `ROTATED_EXACT`
7. 都没有 → `NO_MATCH` / `NO_SECTION`

写盘后立即回读校验新链接存在，不通过则记 `VERIFY_FAIL`。

### push

组装 `[(仓库根, [相对路径])]`：
- 每个在册仓库 → `README.md`
- `--include-skill` 时追加 skill 源码 8 个文件（按 skill 源码所在 git 仓库算相对路径）
- 同一仓库只出现一次，避免重复提交

每个仓库：
1. `git status --porcelain -- <paths>` 无输出 → `CLEAN` 跳过
2. `git add -- <paths>`（`--` 后面跟精确路径，禁止 `.`）
3. 校验 `diff --cached --name-only` 全部在 paths 内，多出来的 `git reset` 掉并告警
4. commit（身份：仓库既有配置 → 否则 remote owner 临时指定）
5. push（失败重试 `config.git.push_retry` 次）
6. 记录 short hash

### verify

| 段 | 检查项 |
|---|---|
| skill 源码 | 每个文件章节内链接 == 基准 |
| 运行环境副本 | 8 个文件与源码字节一致、不缺失 |
| 仓库 README | 章节内链接 == 基准；README 无未提交改动 |
| `--check-remote` | 抽取前 N 个仓库比对 `ls-remote` 与本地 HEAD |

## 四选项决策矩阵（清单变化时）

| 场景 | 建议 policy | 是否要 `--update-manifest` |
|---|---|---|
| 用户加了 1-2 个新项目，其余不变 | `merge` | 是 |
| 用户给的清单里有些项目已被删 | `merge`（先确认 removed 是否要保留） | 是 |
| 只补跑新加的项目 | `new-only` | 否（不污染原清单） |
| 用户明确「以这份清单为准」 | `replace` | 是 |
| 用户没给清单 | `keep` | 否 |

`merge` 与 `replace` 的区别只在 `removed`：`merge` 保留被移出的旧项目继续更新，`replace` 只更新新清单里的。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 / verify 全绿 |
| 1 | 有失败项（push 失败、verify 有问题、参数非法） |

批量脚本里可以直接 `if ! python scripts/qr_rotator.py verify; then ... fi` 卡口。
