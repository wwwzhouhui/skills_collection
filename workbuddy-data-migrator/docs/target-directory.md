# 迁移目标目录

本技能默认将当前用户的 `%USERPROFILE%\.workbuddy` 迁移到 `D:\aiwork\WorkBuddy_C`。这是最终数据目录，不再追加 `.workbuddy` 子目录；用户明确指定其他目标时，以本次指定为准。

## 使用方式

默认路径由技能说明提供。辅助脚本保持不变，检查目标或执行迁移时仍须显式传入 `-Target`：

```powershell
$tool = Join-Path $env:USERPROFILE '.agents\skills\workbuddy-data-migrator\scripts\workbuddy-migrate.ps1'
& $tool -Action Inspect -Target 'D:\aiwork\WorkBuddy_C'
```

只有用户明确批准本次迁移并表示已完全退出 WorkBuddy 后，才可重新检查并执行：

```powershell
& $tool -Action Migrate -Target 'D:\aiwork\WorkBuddy_C' -Confirmed -AppClosed
```

设置默认目标不代表已经迁移，也不代表该目录通过实际预检。目标为空、磁盘类型与空间、完整性校验、备份保留及回滚等规则保持不变。此次只修改技能，不创建目标目录、不访问 WorkBuddy 数据。

## 验证范围

静态检查技能名称与描述、目标路径和命令示例的一致性；对比原文确认只调整目标相关说明；核对辅助脚本与安全参考文档的 SHA-256，并仅解析 PowerShell 语法，不执行脚本。实际目录可用性和 WorkBuddy 应用验收留待用户授权迁移时检查。

## 撤销本次修改

原始技能说明保存在 `docs\SKILL.before-target-change.2026-11-04.md.bak`。确认当前 `SKILL.md` 没有后续需要保留的修改后，可在 PowerShell 执行以下命令恢复本轮修改前的技能说明：

```powershell
$skill = Join-Path $env:USERPROFILE '.agents\skills\workbuddy-data-migrator'
Copy-Item -LiteralPath (Join-Path $skill 'docs\SKILL.before-target-change.2026-11-04.md.bak') -Destination (Join-Path $skill 'SKILL.md') -Force
```

这只恢复技能说明，不执行数据回滚。本页及 `progress.md` 保留为变更记录；撤销后应在日志末尾追加说明。
