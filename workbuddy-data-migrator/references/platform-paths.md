# 平台路径与链接机制

## 默认源与候选路径

Windows 默认源 `%USERPROFILE%\.workbuddy`，默认目标 `D:\aiwork\WorkBuddy_C`。

Linux/macOS 默认源 `~/.workbuddy`。Inspect 还会探测以下可迁移候选是否存在，仅作导航，不代表 WorkBuddy 的真实布局：

| 候选路径 | 说明 |
|---|---|
| `~/.workbuddy` | 与 Windows 布局一致的默认位置 |
| `~/Library/Application Support/WorkBuddy` | macOS 常见应用数据位置 |

以上两个目录名都在迁移作用域内，可直接作为 `--source`。其他目录名不在作用域内，需要先由用户确认实际数据目录并评估后单独处理。

## 目标目录选择

POSIX 平台没有固定的“C 盘”概念，必须由用户显式指定目标：

- 优先选择另一块物理磁盘或独立卷的已存在挂载点下的目录。
- 不要选择 `/`、`/usr`、`/var`、`/System`、`/Library`、`/Applications` 等系统目录。
- 目标父目录必须已存在且当前用户可写；脚本不会自动创建多层系统路径。
- 目标目录必须为空或不存在；不会清空、覆盖或改选其他目标。
- 源与目标位于同一文件系统时脚本给出警告：迁移不会释放原盘空间，只改变目录位置。

## 入口机制对比

| 平台 | 入口 | 创建方式 | 应用兼容性 | 脚本核验 |
|---|---|---|---|---|
| Windows | 目录联接 junction | `New-Item -ItemType Junction` | NTFS 上对应用透明 | 检查 `LinkType`、唯一目标、绝对路径一致 |
| Linux | 符号链接 symlink | `os.symlink(target, source)` | 取决于应用是否跟随链接 | 检查 `islink`、`readlink` 与 `realpath` |
| macOS | 符号链接 symlink | `os.symlink(target, source)` | 取决于应用是否跟随链接 | 检查 `islink`、`readlink` 与 `realpath` |

macOS 的 APFS 卷、firmlink 和 Finder alias 不在此技能范围内：普通用户无法可靠创建 firmlink，Finder alias 也不是 POSIX 路径入口。

## 复制与校验语义

- 复制保留目录结构、文件内容、权限位和时间戳；目标根目录权限收紧为 `0700`。
- 校验使用相对路径、文件大小、文件权限位和 SHA-256 的完整清单，源与目标必须同时与迁移前清单一致。
- 源目录在复制期间发生变化时中止，不执行切换。
- 复制失败时保留部分目标供检查，不清空重试；源目录保持原状。

## 已知限制

1. 符号链接需要应用自身支持。若 WorkBuddy 在 Linux/macOS 上拒绝符号链接路径，应用验收会发现问题，应按 `safety-and-recovery.md` 回滚。
2. 源内部的符号链接、socket、FIFO 和设备文件不做自动处理，迁移会停止并要求单独处理。
3. 不复制 ACL、扩展属性或资源分支的完整语义，可能影响依赖这些元数据的功能。
4. 迁移只覆盖确认过的单一数据目录，不覆盖安装目录、日志目录或其他缓存位置。
5. 目标与源同盘时，空间不会释放；报告时必须说明。