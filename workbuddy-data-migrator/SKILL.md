---
name: workbuddy-data-migrator
author: hailaobao2026
description: 安全迁移 Windows 的 WorkBuddy 用户数据与缓存目录到非系统盘，保留原路径的目录联接并支持回滚。用户提到 WorkBuddy/workbudd 占满 C 盘、.workbuddy 太大、缓存搬家、迁移数据目录或无损搬家时使用。先只读检查，获得明确确认后再执行；不把会话、数据库、配置和身份数据当作可删除缓存。
---

# WorkBuddy 数据无损搬家

## 范围与原则

只处理用户指定的 `.workbuddy` 目录，默认源是当前用户的 `%USERPROFILE%\.workbuddy`。默认迁移目标是 `D:\aiwork\WorkBuddy_C`；这是最终数据目录，不要再追加 `.workbuddy` 子目录。用户明确指定其他目标时以本次指定为准。

`.workbuddy` 不只是缓存，可能包含会话、数据库及 WAL/SHM、项目、配置、插件和身份材料。保持同一 Windows 用户、同一电脑使用；不读取或展示配置、令牌、数据库正文，不上传数据。文章中提到的 `WorkBuddy` 和 `.workbuddy-key-fallback` 不在本技能范围内。

采用“退出软件 → 复制 → SHA-256 校验 → 原目录改名保留 → 建立 junction → 应用验证”。不剪切、不镜像删除、不自动修改工作空间或安装目录、不强杀进程、不自动提权。

**旧备份保留在 C 盘期间，原数据占用仍在。迁移成功不等于已释放这些空间。** 删除备份必须是后续独立确认，不提供默认自动清理。

## 工具入口

辅助脚本位于本技能目录的 `scripts\workbuddy-migrate.ps1`。使用 Windows PowerShell 5.1 及系统 robocopy；路径用参数传入，不拼接为 shell 命令文本。

```powershell
$tool = Join-Path $env:USERPROFILE '.agents\skills\workbuddy-data-migrator\scripts\workbuddy-migrate.ps1'
& $tool -Action Inspect
& $tool -Action Inspect -Target 'D:\aiwork\WorkBuddy_C'
```

如果执行策略阻止本地脚本，可在告知用户后，使用仅对这次进程生效的调用；不要修改系统执行策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$tool" -Action Inspect -Target 'D:\aiwork\WorkBuddy_C'
```

用户要求“写一个技能”或“参考文章”不构成实际迁移授权。用户只说检查时，只运行 Inspect。

## 1. 只读检查

1. 推导实际当前用户目录；只有用户指定其他源路径时才传 `-Source`，不写死用户名。
2. 需要检查目标或准备迁移时，默认使用 `D:\aiwork\WorkBuddy_C`；用户明确指定其他目标时使用该目标，并在命令中显式传入 `-Target`。用户只检查源数据时可不传目标。默认路径不构成迁移授权。
3. 报告数据体积、文件数、运行中的 WorkBuddy 进程、源是否已是 junction，以及用户给定目标的可用性和空间。Inspect 不复制、不改权限、不写迁移记录。
4. 脚本保守支持本地固定 NTFS 盘；拒绝 C 盘目标、非空目标、源目标嵌套、源或路径祖先为联接、内部 reparse point、Windows 保留设备名和长路径。遇到这些情况停下解释，不跳过文件，更不能使用文件粉碎。
5. 非空目标不清空、不覆盖，也不擅自选择另一个目标。权限失败不自动提权。

## 2. 实际迁移前确认

展示并取得本次明确确认：

- 精确源路径、最终目标路径（不是仅盘符）。
- 托盘完全退出 WorkBuddy，包括 WorkBuddyAI 等相关进程；提示操作，脚本不会替用户强杀。
- 整目录保留，目标仅当前用户及 SYSTEM/Administrators 可访问；不搬其他身份文件、不改登录协议。
- 原目录会改名为同级 `.workbuddy.backup-<标识>`，在应用验证和单独批准清理前保留；临时需要源、目标两份空间。

取得确认且用户表示软件已退出后，先重新 Inspect，再运行：

```powershell
& $tool -Action Migrate -Target 'D:\aiwork\WorkBuddy_C' -Confirmed -AppClosed
```

两个开关是已获得用户确认和退出声明的记录，不是代替询问的捷径。脚本仍会检查进程。辅助脚本没有忽略进程的生产入口。

迁移脚本会：

1. 检查路径、权限可用性和目标空间，完整枚举源并计算 SHA-256。
2. 创建空目标，收紧并核验目标 ACL，再用 robocopy `/E /COPY:DAT /DCOPY:DAT /XJ` 复制（内部联接在前置检查中已拒绝，不会静默漏搬）。
3. 返回码必须小于 8，并且源再次校验、目标校验都与复制前清单一致；仅返回码成功不能通过。
4. 保存迁移状态 JSON；源改名为备份，建立 junction，核验指向。源与目标都不递归删除。

输出包含 `Source`、`Target`、`Backup`、`StateFile` 和状态。保存这些路径，后续回滚必须使用这一轮的 StateFile。错误时根据实际状态汇报；保留失败复制的目标，不默认重复执行或清空它。

## 3. 应用验收（不可用文件校验替代）

请用户启动 WorkBuddy，检查：

- 登录状态、历史会话、项目和设置是否正常。
- 新建一条可辨认的测试会话或内容，退出后再启动，确认仍可见。
- 只看路径元数据，确认原入口还是指向指定目标的 junction。

不要代替用户发送会话内容到模型服务。没有做以上检查时，只说“文件迁移及联接校验通过，WorkBuddy 使用验证待完成”。迁移不保证其他 C 盘目录不再增长。

## 4. 回滚与旧备份清理

回滚先阅读 `references\safety-and-recovery.md`，重新让用户退出软件，并确认本次回滚。

```powershell
& $tool -Action Rollback -StateFile 'C:\Users\实际用户名\.workbuddy.backup-本轮标识.migration.json' -Confirmed -AppClosed
```

脚本核实源入口确实是本轮 junction、备份完整、目标是普通目录，才会非递归移除联接入口并恢复备份。目标永不自动删除。

若迁移后有新增、删除或修改，默认拒绝回滚：旧备份不能代表最新状态。先说明回滚会回到迁移前状态，新状态会完整保留在目标但不再从原路径访问；用户明确接受后才补 `-AcceptNewDataInTarget`。不自动合并数据库、不覆盖新文件、不改数据库结构。

删除 C 盘旧备份不是 Migrate/Rollback 的一部分。应用验收通过后，若用户要求释放空间，再确认精确备份路径、可靠的外盘备份和恢复代价。清理前重新检查该备份是普通目录且不是活跃入口；不要递归删除 junction 或根据通配符批量删除。

## 交付报告

简短说明：已完成哪一阶段；目标、备份和状态文件的位置；文件校验与应用验收分别是否通过；C 盘空间是否实际释放；最小下一步。不把未执行的步骤说成已完成。

## 使用示例

- “看看我 C 盘的 `.workbuddy` 多大，先别搬。”→ 只读 Inspect，不要求退出也不写文件。
- “把 `.workbuddy` 搬到默认目录。”→ 目标为 `D:\aiwork\WorkBuddy_C`；预检、展示精确路径和备份策略、确认退出后迁移，应用验收和清理分别确认。
- “搬家后想回到原路径，新会话别丢。”→ 读取本轮状态、检查差异，解释保留目标与恢复旧状态的区别；未接受差异前不切换。
