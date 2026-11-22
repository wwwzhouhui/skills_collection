---
name: wechat-qr-rotator
description: 微信群二维码「一键换新」全链路工具。用户只给一张群二维码图片（或对话里直接发图），自动完成：上传图床取公网 URL → 更新 github-readme-generator 的 SKILL.md 技术交流群章节 → 同步 templates 全部模板 → 覆盖安装到运行环境 skills 目录 → 批量替换 N 个 GitHub 仓库 README.md → 精确提交并推送（只动 README.md）。仓库清单可增长（25→26→27），清单变化时强制询问「保持原有 / 合并新增」。Rotate a WeChat group QR code across a skill package and all its downstream GitHub repos in one shot.
version: 1.0.0
author: wwwzhouhui
---

# 微信群二维码轮换器

## 这个 skill 解决什么

「技术交流群二维码过期了」这件事以前要做五遍手工活：换 SKILL.md、改 6 个模板、重装 skill、改 25 个仓库 README、逐个 commit push。现在只要**丢一张图进来**，五项一次跑完。

核心价值不是「批量替换」，而是**不出错**：
- 只改「技术交流群」那一张图，作者微信码、打赏码一个字都不碰（改动前后用图片 URL 集合做护栏，多改一处整文件回退）
- 提交只 `git add -- README.md`，仓库里几十项无关改动一个都带不走
- 每一步都落备份，随时能整批回滚

## 何时使用

用户表达下列任一意图时触发：

- 给了二维码图片 + 「换群二维码 / 更新二维码 / 二维码过期了」
- 「把 README 里的技术交流群二维码换成新的」
- 「同步到所有仓库」+ 二维码
- 提到 `技术交流群`、`群二维码`、`扫码进群`、`二维码过期`

反面：只是想**新增**一个 README 章节、或改作者微信码 —— 不属于本 skill。

## 前置条件（开跑前先体检）

```bash
python scripts/qr_rotator.py status
```

一次看全：skill 源码路径、运行环境路径、清单规模（在册/排除）、图床接口是否在线、当前群二维码链接、最近一轮记录。

必须满足：

| 项 | 要求 | 不满足怎么办 |
|---|---|---|
| 图床服务 | `curl http://127.0.0.1:36677/heartbeat` 返回 `alive` | 让用户启动 PicList；或改用 `--keep-filename` 之外的现成 URL，直接跳过 `upload` |
| `config.json` 路径 | `skill_source` / `runtime_skills_dir` / `base_dir` 存在 | 换机器或换目录时必须先改，否则会改到不存在的路径 |
| 二维码图片 | 是 png/jpg/gif/webp，且 ≥ 8KB | 太小的多半是缩略图，扫不出来，要求重发原图 |

Python 用系统 `python` 即可；WorkBuddy 环境可用 `C:/Users/75271/.workbuddy/binaries/python/versions/3.13.12/python.exe`。

## 五步流程

> 按顺序跑，**不要跳步**。每步都会打印状态码表，失败项按提示处理后再进下一步。

### 第 1 步：图片 → 公网 URL

```bash
python scripts/qr_rotator.py upload "<图片绝对路径>"
```

- 默认把图片**另存成唯一文件名**（`qr-20261024-1030-ab12cd.jpg`）再上传。这一步是为了击穿缓存：URL 不变的话 GitHub camo 和 COS 都可能继续吐旧图。
- 输出里会同时给「新链接」和「原链接」。**若两者相同，说明上传覆盖了同名文件，必须换图重传**，否则第 2 步会变成空操作。
- URL 拿到后全程复用，后面每步都用 `--url "<URL>"` 显式传入，不依赖隐式状态。

### 第 2 步：更新 skill 源码

```bash
python scripts/qr_rotator.py replace-skill --url "<URL>"
```

改 8 个文件：`SKILL.md`、`README.md`、`templates/` 6 个模板。

alt 策略（自动判断，不用管）：
- `SKILL.md` 里 alt 是文件名式（`image-2026…` / UUID）→ 跟着换成新文件名
- 模板里 alt 是语义化的 `技术交流群` → 原样保留

出现 `ALREADY` 是正常的（已经是新图）。出现 `NO_SECTION` / `NO_IMAGE` 说明该文件被人改坏了，去 `references/pitfalls.md` 对照处理。

### 第 3 步：安装到运行环境

```bash
python scripts/qr_rotator.py sync-runtime --url "<URL>"
```

- 目标目录**不存在** → 完整安装（含 examples / SKILL.assets，自动跳过 `logs`、开发脚本、`.mimosa`）
- 目标目录**已存在** → 只覆盖 `SKILL.md` / `README.md` / 6 个模板，逐文件比对字节确认一致

这一步不做完，用户实际调用 skill 时看到的还是旧二维码——文件改了但没生效，是最容易漏的一步。

### 第 4 步：批量替换仓库 README（含清单决策）

**4.1 当用户给了项目清单，先比对：**

```bash
python scripts/qr_rotator.py plan --list "<清单文件>"
```

清单怎么给都行——`/mnt/f/...` 的 markdown 表格、`F:\...` 纯文本、一列路径，脚本都能抠出目录并自动把 `/mnt/f/` 映射成 `F:/`。

输出 `VERDICT=SAME` 表示清单没变，直接用 `--policy keep` 继续。
输出 `VERDICT=CHANGED` 表示**有新增或移出，必须先问用户**，见下节。

**4.2 没给清单（最常见）：**

```bash
python scripts/qr_rotator.py update-repos --url "<URL>" --policy keep
```

只处理 `projects.json` 里在册的仓库。

**4.3 先看再改（可选但推荐）：**

```bash
python scripts/qr_rotator.py update-repos --url "<URL>" --policy keep --dry-run
```

`--dry-run` 不写盘，只告诉你每个仓库会 `WOULD_ROTATE` 还是 `WOULD_ALREADY`。

### 第 5 步：提交并推送

```bash
# 建议先预演
python scripts/qr_rotator.py push --dry-run

# 正式推
python scripts/qr_rotator.py push
```

- 只 `git add -- README.md`；暂存区若混进别的文件会自动剔除并告警
- 提交后校验本次 commit 只含 README.md，不符合就跳过该仓库
- 仓库没配 `user.name/email` 时按 remote 归属临时指定 `<owner>@users.noreply.github.com`（**不写配置文件**）
- 推送失败自动重试（默认 2 次），仍失败则整批以非零退出码结束，便于你定位
- 成功后把本轮 `from → to → 仓库数` 追加进 `projects.json` 的 `rounds`

**推送是对外动作。** 除非用户明确说了「直接推送 / 全部做完不用问」，否则推送前先把第 4 步的汇总表贴出来并确认一次。

## 清单增长：25 → 26 → 27 的强制决策

用户下次给 26 个或 27 个目录时，`plan` 会算出 `added` / `removed`。**这是唯一必须打断询问的地方**，不能自己替用户选。

用 AskUserQuestion 问，四个选项：

| 选项 | policy | 行为 | 适用 |
|---|---|---|---|
| **合并（推荐）** | `merge` | 原有 25 + 新增全部，一起换 | 用户只是「又加了几个项目」 |
| **只处理原有** | `keep` | 忽略新增，只动在册 25 个 | 新增项目还没准备好 |
| **只处理新增** | `new-only` | 只换新加的那几个 | 补跑上次漏掉的 |
| **完全按新清单** | `replace` | 以新清单为准，`removed` 不再更新 | 用户下线了某些项目 |

确认后执行（`merge` / `replace` / `new-only` 要带 `--update-manifest` 把结果写回清单）：

```bash
python scripts/qr_rotator.py update-repos --url "<URL>" --policy merge \
  --list "<清单文件>" --update-manifest
python scripts/qr_rotator.py push --policy merge
```

`--update-manifest` 是唯一会改 `projects.json` 的开关，默认不写——**没经用户确认就不要加这个参数**。

## 收尾核对

```bash
python scripts/qr_rotator.py verify                 # 全量
python scripts/qr_rotator.py verify --check-remote   # 额外抽查远端 HEAD（慢）
```

四段检查：skill 源码 8 处、运行环境副本字节一致、25 个仓库 README 当前链接、git 是否干净。全绿才叫完成，退出码 0；有任何 `DRIFT` 都以非零退出。

## 出问题怎么退

每一步写盘前都备份，路径在输出里（`备份：...`）。

```bash
python scripts/qr_rotator.py rollback "<备份目录>"
```

会按 `index.json` 把这一轮改过的文件全部还原——skill 源码和仓库 README 可以分别回滚，因为它们各自记在自己的备份目录里。

已经 commit 但没 push？`git reset --soft HEAD~1` 撤回提交，文件改动保留，再 rollback 还原内容。
已经 push 了？只能靠新的 commit 反向操作，或者 `git revert`。

## 状态码字典

| 状态 | 含义 | 需要处理 |
|---|---|---|
| `ROTATED` | 章节内二维码已替换 | 否 |
| `ROTATED_EXACT` | 无章节标题，按旧 URL 精确替换 | 否 |
| `ALREADY` | 已是新图，跳过 | 否 |
| `NO_SECTION` | 找不到「技术交流群」章节 | 是，见 pitfalls |
| `NO_IMAGE` | 章节内没有图片 | 是，见 pitfalls |
| `NO_README` | 目录下没有 README.md | 确认目录选对没 |
| `MISSING` | 目录不存在 | 确认 `base_dir` 或清单路径 |
| `DECODE_FAIL` | 编码识别不了 | 多半文件已损坏，见 pitfalls |

## 目录结构

```
wechat-qr-rotator/
├── SKILL.md                  本文件
├── README.md                 GitHub 项目首页
├── config.json               机器相关路径（换电脑先改这里）
├── projects.json             仓库清单 + 排除名单 + 历史轮次
├── scripts/qr_rotator.py     全部逻辑（单文件，仅标准库）
├── references/
│   ├── workflow.md           五步流程详解、四选项决策矩阵、参数全表
│   └── pitfalls.md           已知坑：dubious ownership、NUL 文件、jpg→png、缓存
└── examples/
    └── project-list.sample.md  清单格式示例
```

## 边界（明确不做的事）

- 不改作者微信二维码、打赏码、任何其他图片
- 不改 README 里二维码以外的内容（alt 除文件名式外一律保留）
- 不提交 README.md 之外的任何文件（除非显式加 `--include-skill`）
- 不替用户决定清单增删
- 不处理已列入 `excluded` 的损坏文件——它们的 README 在 git 里就是坏的，需要先人工重写
