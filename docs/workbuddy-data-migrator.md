# WorkBuddy 技能仓库维护与安装

## 两类目录不要混淆

| 用途 | 路径 |
| --- | --- |
| 本机技能真实文件 | `F:\work\code\github\wwwzhouhui\skills_collection\workbuddy-data-migrator` |
| ZCode 用户级安装入口 | `%USERPROFILE%\.agents\skills\workbuddy-data-migrator` |
| 技能默认迁移的数据目标 | `D:\aiwork\WorkBuddy_C` |

仓库最初将 Windows 版技能迁入版本管理，原安装入口改为指向仓库真实目录的 NTFS junction。当前版本已在原有安全流程上增加 Linux/macOS 支持，但没有迁移、扫描或清理本机 `%USERPROFILE%\.workbuddy` 数据。

今后修改仓库内的技能文件，原安装入口会访问同一份内容，不需要另行复制。F 盘和仓库路径必须保持可用；移动仓库前应先调整安装入口。不要在仓库内用 junction 代替真实源码，也不要把迁移状态文件、会话、数据库或凭据加入仓库。

## 文件范围

当前技能目录包含以下文件：

- `SKILL.md`：三平台使用流程、安全确认及资源入口。
- `scripts/workbuddy-migrate.ps1`：Windows Inspect / Migrate / Rollback 脚本。
- `scripts/workbuddy_migrate.py`：Linux/macOS Inspect / Migrate / Rollback 脚本。
- `scripts/selftest_posix.py`：只使用临时测试数据的 POSIX 端到端自检。
- `references/safety-and-recovery.md`：共同安全边界、状态机与恢复说明。
- `references/platform-paths.md`：平台路径、链接机制与支持限制。
- `docs/target-directory.md`：Windows 默认数据目标说明。
- `docs/SKILL.before-target-change.2026-11-04.md.bak`：历史原文备份，不是当前配置。
- `progress.md`：技能迁移历史记录；仓库发布记录写在根目录 `progress.md`。

历史记录含本机路径，按完整目录迁移保留。不要把历史备份里的旧目标路径当成当前配置，也不要自动覆盖回当前技能。

## 安装入口

当前电脑已建立入口，无需重复安装。在另一台 Windows 电脑上，可从仓库根目录运行：

```powershell
$skill = (Resolve-Path -LiteralPath '.\workbuddy-data-migrator').Path
$installRoot = Join-Path $env:USERPROFILE '.agents\skills'
$entry = Join-Path $installRoot 'workbuddy-data-migrator'
if (Test-Path -LiteralPath $entry) { throw '安装入口已存在，请先检查，勿覆盖。' }
[System.IO.Directory]::CreateDirectory($installRoot) | Out-Null
New-Item -ItemType Junction -Path $entry -Target $skill
```

此命令只安装技能，不执行数据迁移。权限失败时停下检查，不自动提权。其他客户端应使用各自支持的技能发现目录，命令中的脚本路径也应来自实际安装目录。

## 验证方式与边界

- Windows 脚本使用 PowerShell 解析器执行语法检查，不点源或操作真实数据。
- Linux/macOS 脚本先执行 Python 语法编译，再通过 `scripts/selftest_posix.py` 在临时目录完成 Inspect / Migrate / Rollback 端到端自检。
- 提交前检查 Git 差异、空白错误和暂存范围；不提交仓库中其他未完成改动。
- Windows 迁移逻辑未在本轮使用真实 WorkBuddy 数据执行；Linux 自检只覆盖模拟数据；macOS 仍需在目标机先运行自检。

实际迁移仍须按 [技能说明](../workbuddy-data-migrator/SKILL.md) 重新检查路径、空间和进程，并取得明确确认。

## 撤销本次安装位置迁移

仓库发布前保留本轮临时副本 `%USERPROFILE%\.agents\skills\.workbuddy-data-migrator.move-backup-20261105`；完成远程发布核验后仅清理这个临时副本，技能内部历史备份不清理。

需要恢复为 C 盘真实安装目录时，先确认当前入口仍指向本仓库，且没有其他工具正在改写技能文件。以下 PowerShell 命令从仓库复制当前技能到一个不存在的新暂存目录，逐文件校验后，只非递归移除 junction 入口，再将暂存目录改回原技能名。仓库文件保持不变；**这不是 WorkBuddy 数据回滚**。

```powershell
$ErrorActionPreference = 'Stop'
$repoSkill = 'F:\work\code\github\wwwzhouhui\skills_collection\workbuddy-data-migrator'
$entry = Join-Path $env:USERPROFILE '.agents\skills\workbuddy-data-migrator'
$restore = Join-Path $env:USERPROFILE '.agents\skills\.workbuddy-data-migrator.restore'
$link = Get-Item -LiteralPath $entry -Force
if ($link.LinkType -ne 'Junction' -or [string]$link.Target[0] -ne $repoSkill) {
    throw '入口不是本次目录联接，停止回滚。'
}
if (Test-Path -LiteralPath $restore) { throw '恢复暂存目录已存在，停止。' }
$sourceItems = @(Get-ChildItem -LiteralPath $repoSkill -Force -Recurse)
if ($sourceItems | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }) {
    throw '技能内存在重解析点，停止。'
}
$sourceFiles = @($sourceItems | Where-Object { -not $_.PSIsContainer })
Copy-Item -LiteralPath $repoSkill -Destination $restore -Recurse
$restoredFiles = @(Get-ChildItem -LiteralPath $restore -File -Force -Recurse)
if ($restoredFiles.Count -ne $sourceFiles.Count) { throw '文件数量不一致，入口未切换。' }
foreach ($file in $sourceFiles) {
    $relative = $file.FullName.Substring($repoSkill.Length + 1)
    $copied = Join-Path $restore $relative
    if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $copied -Algorithm SHA256).Hash) {
        throw "文件校验不一致，入口未切换：$relative"
    }
}
[System.IO.Directory]::Delete($entry, $false)
Rename-Item -LiteralPath $restore -NewName 'workbuddy-data-migrator'
```

恢复后重新加载技能验证。若最后改名失败，完整副本仍保留在 `$restore`，不要删除它；检查原因后再恢复入口。若另需撤销仓库提交，先恢复本地真实安装目录，再针对本轮提交执行 `git revert`；不要强推或丢弃其他工作区修改。
