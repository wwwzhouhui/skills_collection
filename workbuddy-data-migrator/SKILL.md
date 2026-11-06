---
name: workbuddy-data-migrator
description: |
  安全迁移 WorkBuddy 用户数据目录到非系统盘或其他卷，保留原路径入口并支持校验与回滚。Windows 使用目录联接（junction）与 robocopy，目标须为固定 NTFS 盘；Linux/macOS 使用符号链接。适用于 WorkBuddy 占满 C 盘或系统盘、.workbuddy 过大、缓存/数据搬家、迁移数据目录、无损搬家。先只读检查，取得明确确认后再迁移；不把会话、数据库、配置和身份数据当作可删除缓存。
  触发词：WorkBuddy 迁移、workbuddy-data-migrator、.workbuddy 太大、C 盘爆满、workbuddy 搬家、数据目录迁移、Linux 迁移、macOS 迁移。
allowed-tools: Bash(python3:*) Bash(powershell.exe:*) Bash(ps:*) Read
---

# WorkBuddy 数据无损搬家

## 范围与原则

只处理当前用户的 WorkBuddy 数据目录。Windows 默认源是 `%USERPROFILE%\.workbuddy`，默认目标是 `D:\aiwork\WorkBuddy_C`（最终数据目录，不再追加 `.workbuddy`）。Linux/macOS 默认源是 `~/.workbuddy`，目标必须显式指定。

这不是缓存目录：可能包含会话、数据库及 WAL/SHM、项目、配置、插件和身份材料。保持同一用户、同一台电脑；不读取、展示或上传配置、令牌与数据库正文。

固定流程：退出应用 → 只读检查 → 用户确认 → 复制 → 全量 SHA-256 校验 → 原目录改名保留 → 建立原路径入口 → 应用验收。不剪切、不镜像删除、不强杀进程、不自动提权、不自动清理备份。

**备份仍在原盘期间，原空间没有被释放。** 删除备份必须是后续独立确认。

## 平台入口

| 平台 | 脚本 | 入口机制 |
|---|---|---|
| Windows | `scripts/workbuddy-migrate.ps1`（PowerShell 5.1 + 系统 robocopy） | 目录联接 junction |
| Linux / macOS | `scripts/workbuddy_migrate.py`（Python 3.8+ 标准库） | 符号链接 symlink |

先确定本技能目录，把绝对路径代入命令；不要假设当前工作目录就是技能目录。

macOS 的实际数据目录也可能在 `~/Library/Application Support/WorkBuddy`。当默认源不存在时，先运行 Inspect 查看候选路径，确认后用 `--source "<实际源目录>"` 显式指定。

## 1. 只读检查

Windows：

```powershell
& "<技能目录>\scripts\workbuddy-migrate.ps1" -Action Inspect -Target 'D:\aiwork\WorkBuddy_C'
```

如果执行策略阻止本地脚本，可在告知用户后仅对这次进程绕过，不要修改系统执行策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<技能目录>\scripts\workbuddy-migrate.ps1" -Action Inspect -Target 'D:\aiwork\WorkBuddy_C'
```

Linux / macOS（目标必须是已存在挂载点下的目录）：

```bash
python3 "<技能目录>/scripts/workbuddy_migrate.py" inspect --target "<目标目录>"
```

报告数据体积与文件数、运行中的 WorkBuddy 进程、源是否已是链接、内部符号链接/特殊文件、目标可用性与空间、源与目标是否同一文件系统。Inspect 不复制、不改权限、不写状态文件。

脚本会拒绝：源本身是链接、路径祖先含链接（可用显式开关确认）、源内含符号链接或特殊文件、目标非空、源目标嵌套、目标位于系统目录、空间不足。遇到这些情况停下解释，不跳过文件、不粉碎数据。

## 2. 迁移前确认

展示并取得本次明确确认：

- 精确源路径与最终目标路径（不是仅盘符或挂载点）。
- 完全退出 WorkBuddy，包括托盘/辅助进程；脚本不会替用户强杀。
- 原目录会改名为同级 `<源>.backup-<标识>`，在应用验收和单独批准清理前保留。
- 切换后新写入进入目标盘，但旧备份仍占原盘空间，临时需要两份空间。

确认且用户声明应用已退出后，先重新 Inspect，再执行：

```powershell
& "<技能目录>\scripts\workbuddy-migrate.ps1" -Action Migrate -Target 'D:\aiwork\WorkBuddy_C' -Confirmed -AppClosed
```

```bash
python3 "<技能目录>/scripts/workbuddy_migrate.py" migrate --target "<目标目录>" --confirmed --app-closed
```

`-Confirmed/-AppClosed` 与 `--confirmed/--app-closed` 是确认记录，不是绕过询问。脚本仍检查进程；失败时保留源与部分目标，不清空重试。输出包含 `Source`、`Target`、`Backup`、`StateFile` 和状态，请保存这些路径。

## 3. 应用验收（不能由文件校验替代）

请用户启动 WorkBuddy，检查登录状态、历史会话、项目与设置是否正常；新建一条可辨认的测试内容，退出后再启动确认仍可见；确认原路径入口指向目标。没有完成这些检查时，只说“文件迁移与链接校验通过，应用验收待完成”。

## 4. 回滚与旧备份清理

先读 `references/safety-and-recovery.md`，让用户退出软件并确认本次回滚，使用本轮 StateFile：

```powershell
& "<技能目录>\scripts\workbuddy-migrate.ps1" -Action Rollback -StateFile "<StateFile>" -Confirmed -AppClosed
```

```bash
python3 "<技能目录>/scripts/workbuddy_migrate.py" rollback --state-file "<StateFile>" --confirmed --app-closed
```

脚本仅在入口确为本轮链接、备份完整、目标是普通目录时，非递归移除入口并恢复备份。目标永不自动删除。迁移后目标有新增或修改时默认拒绝回滚；用户明确接受“恢复到迁移前状态，新数据仍保留在目标但暂不活跃”后，才加 `-AcceptNewDataInTarget` / `--accept-new-data-in-target`。

如果源、目标或备份路径的祖先包含符号链接，迁移时使用了 `--accept-symlinked-ancestors`，回滚时也必须带同一开关；否则脚本为保证安全会拒绝执行。

删除旧备份不属于 Migrate/Rollback。应用验收通过且用户单独要求释放空间时，再确认精确备份路径、可靠的外盘恢复副本与恢复代价。不要递归删除链接，不要按通配符批量删除。

## 交付报告

简短说明：已完成哪一阶段；目标、备份和状态文件位置；文件校验与应用验收分别是否通过；原盘空间是否实际释放；最小下一步。不把未执行的步骤说成已完成。

## 使用示例

- “看看 `.workbuddy` 多大，先别搬” → 只读 Inspect，不要求退出也不写文件。
- “搬到默认目录/外接盘” → 预检、展示精确路径与备份策略、确认退出后迁移，应用验收与清理分别确认。
- “搬家后想回到原路径” → 读取本轮 StateFile，检查目标新数据，解释差异后再切换。

## 资源导航

| 资源 | 用途 |
|---|---|
| `scripts/workbuddy-migrate.ps1` | Windows Inspect / Migrate / Rollback |
| `scripts/workbuddy_migrate.py` | Linux / macOS Inspect / Migrate / Rollback |
| `scripts/selftest_posix.py` | Linux/macOS 临时目录端到端自检，不接触真实数据 |
| `references/safety-and-recovery.md` | 安全边界、状态机、失败恢复、空间释放 |
| `references/platform-paths.md` | 平台路径、链接机制差异、支持范围与限制 |