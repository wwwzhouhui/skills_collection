# WorkBuddy 技能仓库维护与安装

## 两类目录不要混淆

| 用途 | 路径 |
| --- | --- |
| 本机技能真实文件 | `F:\work\code\github\wwwzhouhui\skills_collection\workbuddy-data-migrator` |
| ZCode 用户级安装入口 | `%USERPROFILE%\.agents\skills\workbuddy-data-migrator` |
| 技能默认迁移的数据目标 | `D:\aiwork\WorkBuddy_C` |

本次将技能文件迁入仓库，原安装入口改为指向仓库真实目录的 NTFS junction。没有迁移、扫描或清理 `%USERPROFILE%\.workbuddy` 数据。作者保持 `hailaobao2026`，默认数据目标保持不变。

今后修改仓库内的技能文件，原安装入口会访问同一份内容，不需要另行复制。F 盘和仓库路径必须保持可用；移动仓库前应先调整安装入口。不要在仓库内用 junction 代替真实源码，也不要把迁移状态文件、会话、数据库或凭据加入仓库。

## 文件范围

完整保留技能原有六个文件：

- `SKILL.md`：技能规则、作者及默认数据目标。
- `scripts/workbuddy-migrate.ps1`：迁移辅助脚本，未修改。
- `references/safety-and-recovery.md`：安全与恢复说明。
- `docs/target-directory.md`：默认数据目标使用说明。
- `docs/SKILL.before-target-change.2026-11-04.md.bak`：历史原文备份，不是当前配置。
- `progress.md`：技能已有历史记录，保留原样；本次迁移记录在仓库根 `progress.md`。

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

- 迁入前后逐文件比对相对路径、数量、字节数及 SHA-256：六个文件，共 35,927 字节。
- 核对 `name: workbuddy-data-migrator`、`author: hailaobao2026` 和默认数据目标。
- 用 PowerShell `System.Management.Automation.Language.Parser.ParseFile` 仅解析脚本语法，不执行或点源加载脚本。
- 检查原安装入口的 `LinkType` 和 `Target`，从入口读取文件并重新加载技能。
- 提交前检查 README 清单数量、文档链接、Git 差异及暂存范围；不提交仓库中其他未完成改动。

本次验证不包含 WorkBuddy 真实数据的 `Inspect`、`Migrate`、`Rollback` 或应用验收。实际迁移仍须按 [技能说明](../workbuddy-data-migrator/SKILL.md) 重新检查并征得明确确认。

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
