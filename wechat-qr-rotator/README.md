# WeChat QR Rotator · 微信群二维码批量轮换器

> 丢一张群二维码进来，自动换遍 skill 包和下游所有 GitHub 仓库，并推送。**只改那一张图，别的一个字都不动。**

![version](https://img.shields.io/badge/version-1.0.0-blue)
![python](https://img.shields.io/badge/python-3.8%2B-3776ab?logo=python&logoColor=white)
![license](https://img.shields.io/badge/license-MIT-green)
![platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## 目录

- [为什么需要它](#为什么需要它)
- [它到底做了什么](#它到底做了什么)
- [核心特性](#核心特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [清单增长与强制决策](#清单增长与强制决策)
- [命令一览](#命令一览)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [技术交流群](#技术交流群)
- [打赏](#打赏)
- [许可](#许可)

## 为什么需要它

做开源项目的人多半有这种经历：微信技术交流群的二维码 7 天就过期，而你把它贴在了十几个仓库的 README 里。

换一次群码意味着：

1. 改主 skill 的 `SKILL.md`
2. 改 `templates/` 下每一个模板
3. 重新安装到 WorkBuddy 运行环境
4. 改在册仓库的 `README.md`
5. 逐个 `git commit` + `git push`

手工做一遍 20 分钟，还容易漏、容易误伤作者微信码、容易顺手把无关改动一起提交。这个工具把那 20 分钟压成一条命令。

## 它到底做了什么

```
二维码图片
   │  upload           图片 → 腾讯 COS，返回公网 URL
   ▼
公网 URL
   ├─ replace-skill    SKILL.md + README.md + templates ×6
   ├─ sync-runtime     覆盖安装到 ~/.workbuddy/skills/<skill>
   ├─ update-repos     N 个仓库 README.md
   └─ push             只 add README.md，逐个提交推送
                        ↓
                     verify 全链路核对
```

## 核心特性

| 特性 | 说明 |
|---|---|
| **精确命中** | 只改「技术交流群」章节里的第一张图；靠图片 URL 集合做护栏，多改一处整文件回退 |
| **缓存击穿** | 上传时自动改名成唯一文件名，URL 变化让 COS/GitHub camo 重新抓图 |
| **编码安全** | UTF-8 / UTF-8-BOM / UTF-16 自动探测，写回沿用原编码 |
| **提交范围受控** | 只 `git add -- README.md`，暂存区混入别的文件会自动剔除并告警 |
| **可回滚** | 每次写盘前备份，`rollback <备份目录>` 整批还原 |
| **清单可增长** | `projects.json` 记在册仓库；清单变化时强制询问「保持原有 / 合并新增」 |
| **零依赖** | 单文件 CLI，只用 Python 标准库 |

## 安装

把整个目录放进 WorkBuddy 的用户级 skills 目录即可：

```bash
# macOS / Linux
cp -r wechat-qr-rotator ~/.workbuddy/skills/

# Windows
xcopy /E /I wechat-qr-rotator "%USERPROFILE%\.workbuddy\skills\wechat-qr-rotator"
```

前提条件：

- Python 3.8+
- [PicList](https://github.com/Kuingsmile/PicList) 在跑，且内置 HTTP 服务开启（默认 `127.0.0.1:36677`）。图片会走你配好的图床（本项目作者用的是腾讯云 COS）
- 目标 skill 目录（默认 `github-readme-generator`）已存在

## 快速开始

```bash
# 0. 体检
python scripts/qr_rotator.py status

# 1. 图片 → 公网 URL
python scripts/qr_rotator.py upload "C:/path/to/qr.jpg"

# 2. 改 skill 源码（8 个文件）
python scripts/qr_rotator.py replace-skill --url "<上面拿到的 URL>"

# 3. 装到运行环境
python scripts/qr_rotator.py sync-runtime --url "<URL>"

# 4. 批量改仓库 README（想先看效果就加 --dry-run）
python scripts/qr_rotator.py update-repos --url "<URL>" --policy keep

# 5. 提交推送
python scripts/qr_rotator.py push --dry-run     # 预演
python scripts/qr_rotator.py push               # 正式

# 6. 核对
python scripts/qr_rotator.py verify
```

## 清单增长与强制决策

新加了项目？把新清单丢给 `plan`，它会算出新增和移出：

```bash
python scripts/qr_rotator.py plan --list "new-list.md"
# VERDICT=CHANGED
# 新增目录：+ wwwzhouhui/new-project
```

然后按你的选择执行：

| 选择 | 命令 | 结果 |
|---|---|---|
| 合并（推荐） | `update-repos --policy merge --list new-list.md --update-manifest` | 原有 + 新增一起换 |
| 只处理原有 | `update-repos --policy keep` | 忽略新增 |
| 只处理新增 | `update-repos --policy new-only --list new-list.md` | 补跑新增 |
| 完全按新清单 | `update-repos --policy replace --list new-list.md --update-manifest` | 移出的不再更新 |

`plan` 永远只读；`--update-manifest` 是唯一会改 `projects.json` 的开关。

## 命令一览

| 命令 | 作用 |
|---|---|
| `upload <image>` | 上传二维码，返回公网 URL |
| `replace-skill` | 更新 skill 源码里的群码 |
| `sync-runtime` | 覆盖安装到运行环境 |
| `plan --list` | 清单比对（新增/移出） |
| `update-repos` | 批量替换仓库 README |
| `push` | 精确提交并推送 |
| `verify` | 全链路核对 |
| `rollback <备份>` | 用备份还原 |
| `status` | 当前状态一览 |

所有命令都支持 `--base-dir` / `--skill-source` / `--runtime-dir` 覆盖配置，写盘类还支持 `--dry-run`。

详细参数见 [`references/workflow.md`](references/workflow.md)。

## 配置说明

`config.json`（机器相关）：

```json
{
  "base_dir": "F:/work/code/github",
  "skill_source": ".../skills_collection/github-readme-generator",
  "runtime_skills_dir": "C:/Users/<you>/.workbuddy/skills",
  "runtime_skill_name": "github-readme-generator",
  "qr_section_keyword": "技术交流群",
  "upload": { "api": "http://127.0.0.1:36677/upload", "unique_filename": true },
  "git": { "commit_message": "docs: 更新技术交流群二维码为最新版本", "push_retry": 2 }
}
```

`projects.json`（仓库清单）：

```json
{
  "active": ["owner/repo", "..."],
  "excluded": [{ "dir": "owner/broken-repo", "reason": "README 损坏，无二维码" }],
  "rounds": [{ "date": "2026-10-24", "from": "...", "to": "...", "repos": 25 }]
}
```

## 常见问题

<details>
<summary>换完图，GitHub 上还是旧二维码？</summary>

两层缓存：COS 边缘节点 + GitHub camo。确认两件事：

1. `upload` 返回的 URL 和旧 URL **不同**（同名覆盖会导致 URL 不变）
2. 提交确实推送成功（`git log --oneline -1`、`git status`）

还不行就强制刷新页面 / 换个浏览器无痕窗口看。
</details>

<details>
<summary>报 `detected dubious ownership`？</summary>

仓库属主和当前用户不一致。脚本内部已用 `git -c safe.directory='*'` 处理；自己手敲命令时也要带这个参数。不建议改全局 git 配置。
</details>

<details>
<summary>某个仓库一直是 `NO_SECTION` / `DECODE_FAIL`？</summary>

多半是 README 本身坏了（尾部 NUL 填充、或整文件全 NUL）。这类文件没有二维码可换，加进 `projects.json → excluded` 并人工重写。详见 [`references/pitfalls.md`](references/pitfalls.md)。
</details>

<details>
<summary>会不会把作者的微信码、打赏码也换掉？</summary>

不会。「技术交流群」章节的范围是：标题行之后到下一个任意标题之前，只取其中第一张图。另外每次替换都用图片 URL 集合做前后比对，只要除目标图之外有任何图片变化，整个文件放弃、退回原文。
</details>

<details>
<summary>会不会把仓库里其他未提交的改动一起推上去？</summary>

不会。只 `git add -- README.md`，并且提交前校验暂存清单，混入的无关文件会被 `git reset` 剔除并告警。
</details>

## 技术交流群

欢迎加入技术交流群，分享你的 Skills 和使用心得：

![技术交流群](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20261024100147846.png)

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

**微信支付**

![微信支付](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

## 许可

[MIT](LICENSE) © wwwzhouhui
