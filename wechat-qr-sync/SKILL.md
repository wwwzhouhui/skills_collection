---
name: wechat-qr-sync
description: Batch-update the WeChat group QR-code image URL under the "技术交流群" section across multiple project README.md files and push each repo to GitHub. Use when the user has updated their WeChat group QR code (new image URL) and wants it synced to many local repos (any number, from a user-provided directory list, WSL /mnt/ or Windows paths both fine), including template files if present, then committed and pushed repo-by-repo. 批量更新微信群二维码链接并逐仓库提交推送。
version: 1.0.0
author: wwwzhouhui
---

# WeChat QR Sync（微信群二维码批量同步）

把最新的微信群二维码图片 URL 批量同步到多个项目的 README.md（以及 README 模板文件），并逐仓库提交推送到 GitHub。项目数量不固定，完全由用户提供的目录清单决定。

## 输入

执行前先确认两件事，缺哪件就向用户要哪件：

1. **最新的二维码 URL（NEW_URL）**，两种来源：
   - 用户直接给出新 URL；
   - 用户说"我已经更新了某个文件"（如某 skill 的 SKILL.md、某个基准 README），从该文件的"技术交流群"段落提取最新图片 URL 作为 NEW_URL。
2. **项目目录清单**，用户提供（markdown 表格、纯文本、聊天消息均可）。每行一个项目根目录，路径可能是三种格式之一，脚本会自动转换：
   - WSL 路径：`/mnt/f/work/code/github/xxx`
   - Git Bash 路径：`/f/work/code/github/xxx`
   - Windows 路径：`F:\work\code\github\xxx`

   若用户给的是 markdown 表格等多列内容，先提取第一列路径整理成纯文本清单文件（每行一个路径）再交给脚本。

**URL 校验红线**：NEW_URL 必须是 `http(s)://` 开头的外部图床链接；host 不得是 localhost、127.x、10.x、192.168.x、172.16-31.x 等内网/保留地址。不满足则拒绝执行并向用户说明。

## 硬性边界（不要违反）

- 只改"**技术交流群**"段落下方的群二维码图片 URL。
- **不要动**"作者联系/联系作者"下的个人微信二维码、打赏/收款码、以及 README 中其他任何图片。
- 提交时**只暂存 README.md**（模板仓库则只暂存 templates 下被改的文件），绝不 `git add -A`，不碰用户其他未提交改动。
- 各项目旧二维码 URL 可能不同（有的项目还从未更新过），**必须先扫描、后替换、再验证**，不要盲改。

## 三步流程

配套脚本 `scripts/sync_qr.sh` 已实现全部三步，优先用脚本；脚本不可用时按每步给出的原生命令手工执行。

### 步骤一：同步模板目录（仅当当前仓库含 README 模板时）

如果当前工作仓库本身带有 `templates/*.md` 这类 README 模板（如 github-readme-generator），先让模板与基准文件（SKILL.md / 主 README）保持一致：

```bash
cd <模板仓库根目录>
grep -n -A3 "技术交流群" SKILL.md templates/*.md   # 确认各文件当前 URL
# 将模板中旧的群二维码 URL 替换为 NEW_URL（旧 URL 以扫描结果为准，逐个确认后替换）：
sed -i 's|旧群二维码URL|NEW_URL|g' templates/*.md
grep -n -A3 "技术交流群" templates/*.md            # 复核：个人微信码、打赏码未受影响
```

判断依据：只替换出现在"技术交流群"段落里的那张图；`Screenshot_*_com.tencent.mm.jpg` 形式的 URL 要先确认是群码还是个人码（看所在段落），不能按文件名猜测。

### 步骤二：扫描并批量替换各项目 README.md

先把清单存为纯文本文件（如 `/tmp/repo_list.txt`），然后：

```bash
bash scripts/sync_qr.sh scan    --new-url "NEW_URL" --list /tmp/repo_list.txt   # 只扫描，先看报告
bash scripts/sync_qr.sh replace --new-url "NEW_URL" --list /tmp/repo_list.txt   # 替换 + 自动复核
```

scan 报告会把每个项目归类：

- `HAS-OLD`：有"技术交流群"段落且二维码是旧地址，replace 时会被更新；
- `NEW-OK`：已经是最新地址，跳过；
- `NO-SEC`：README.md 存在但没有"技术交流群"段落，跳过（不要为此新建段落）；
- `NO-FILE`：README.md 不存在，跳过。

replace 会：定位"技术交流群"标题之后、下一个标题之前的第一个图片行，把其中的 URL 全文替换为 NEW_URL（群码 URL 为该图专属，全文替换安全），替换后自动重新扫描验证并输出结果。替换只改 URL 文本本身，不改行尾、编码与其他内容。

脚本不可用时的手工等价操作：

```bash
# 定位每个 README 中群码当前 URL（技术交流群标题后的第一个图片行）
for f in $(cat /tmp/repo_list.txt); do grep -A3 "技术交流群" "$f/README.md"; done
# 确认旧 URL 后逐文件替换并验证
sed -i 's|旧URL|NEW_URL|g' <各README.md>
grep -rl "旧URL" <各仓库根> --include=README.md   # 期望无输出
```

### 步骤三：逐仓库提交并推送

```bash
bash scripts/sync_qr.sh push --list /tmp/repo_list.txt \
     --message "docs: 更新技术交流群微信群二维码为最新地址" --branch main
```

脚本对清单中每个仓库：检查分支与远端 → `git add README.md` → 提交 → `git push origin <branch>`。无改动的仓库自动跳过，单个仓库失败不中断其余仓库，最后输出成功/失败汇总。

失败处理：

- **403 Permission denied**：远端 URL 内嵌 token 或凭据管理器中的账号对该仓库无写权限（常见于多账号维护，如 A 账号 token 推 B 账号仓库）。此时本地提交已保留，**不要回滚**，向用户报告，并给出选项：提供目标账号 PAT / 把常用账号加为协作者 / 用户自行推送。
- **推送 rejected（远端有新提交）**：先 `git pull --rebase origin <branch>` 再推，冲突则停下报告用户。
- 其余报错原样呈现给用户，不要静默重试超过一次。

## 执行顺序建议

scan 的报告先给用户过目（尤其 NO-SEC / NO-FILE 的项目），再执行 replace；replace 完成把验证结果给用户看；push 完成汇报每个仓库的提交哈希或失败原因。全程不要把 token 打印到输出里。

## 已验证案例

2026-09 用本流程把新版群二维码（`.../Obsidian/20260906214736_34_9.jpg`）同步到 25 个仓库并推送：24 个成功，1 个因远端 token 属于另一账号 403（本地提交保留，等用户提供凭据）。模板仓库 github-readme-generator 的 6 个 templates/*.md 同步在步骤一完成。
