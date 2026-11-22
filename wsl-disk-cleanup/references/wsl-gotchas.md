# WSL 操作避坑指南（wsl-disk-cleanup 参考）

本文件记录从真实运维中沉淀的 WSL 操作陷阱与解法，执行清理时如遇异常先查这里。

## 1. wsl.exe 被沙箱黑名单拦截

WorkBuddy 沙箱默认可能拦截 `wsl.exe`。报错表现为调用被拒绝。解法：用户需在
**WorkBuddy → 安全中心 → 命令安全 → 程序黑名单 → 移除 `wsl.exe`**。这是环境配置问题，
不是系统故障，不要反复重试。

## 2. 发行版名不是想当然的 `Ubuntu`

`wsl -d Ubuntu` 可能报 `WSL_E_DISTRO_NOT_FOUND`。实际注册名可能是
`Ubuntu-22.04`、`Ubuntu-24.04` 等。**每次操作前先 `wsl -l -v` 枚举**。
本机事实：默认发行版 `Ubuntu-22.04`，另有 `pentagi`。

vhdx 路径也同理，不要猜。未知时用 PowerShell 查注册表：

```powershell
Get-ChildItem HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss |
  ForEach-Object { $p = Get-ItemProperty $_.PSPath; if ($p.DistributionName) { "$($p.DistributionName) => $($p.BasePath)" } }
```

## 3. 中文输出乱码

Git Bash 调 `wsl.exe` 输出中文/表格乱码时，先执行：

```bash
export WSL_UTF8=1
```

## 4. MSYS 路径转换

Git Bash 会把 `/tmp/xxx` 改写成 Windows 临时目录，导致 WSL 内找不到文件。执行
`wsl -d <distro> -- bash /tmp/script.sh` 前先：

```bash
export MSYS_NO_PATHCONV=1
```

## 5. 命令替换陷阱（最隐蔽的坑）

通过 `wsl -d <distro> -- bash -c '...'` 传命令时，`$(...)` 会被**外层 Git Bash
提前展开**，导致命令错乱（表现为大量 "command not found"，只有个别命令执行成功）。

**解法（按优先级）**：

1. 把逻辑写进脚本文件，用 stdin 管道送入：`wsl -d <distro> -- bash -s < script.sh`
   —— 脚本在 WSL 内部的 bash 里整体解释，完全不受外层影响，`$()` 可正常使用。
2. 必须内联时，用显式对象 ID，不用命令替换：
   `docker rm -f <id1> <id2> <id3>`
3. 写脚本到 WSL 内时，UNC 路径（`\\wsl.localhost\...`）的 Write 工具可能不真正落盘，
   写完必须 `wsl -d <distro> -- ls -la /path` 验证；不可靠，优先用方案 1。

## 6. 1Panel 会自动重建容器

1Panel（`1panel-agent.service` + `1panel-core.service`，systemd 管理、开机自启）
会在其管理的 compose 容器被删后**自动重建并拉镜像**。`kill` 进程无效——systemd
立刻拉起新进程。

**清理 Docker 前必须**：

```bash
systemctl disable --now 1panel-agent.service 1panel-core.service
```

若之后还要用 1Panel：`systemctl enable --now 1panel-agent.service 1panel-core.service`，
但恢复前先在面板里卸载对应应用，否则又开始自动拉镜像。

## 7. sparse 与 compact 互斥

`wsl --manage <distro> --compact` **拒绝处理 sparse 文件**（报
ERROR_VIRTUAL_DISK_LIMITATION）。正确顺序：

```bash
wsl --shutdown
wsl --manage <distro> --set-sparse false
wsl --manage <distro> --compact
```

压缩后保持 sparse 关闭，下次想再压缩一条命令即可（比 sparse 自动 trim 更可控）。

## 8. diskpart 压缩需要管理员权限

旧方案（管理员 PowerShell + diskpart `compact vdisk`）有效但需要管理员，
且沙箱内无法代劳。**WSL 3.0.3+ 优先用原生 `--compact`**，无需管理员。

## 9. vhdx 逻辑大小 vs 物理占用

`ls -lh` 看到的是逻辑大小，`du -h` 才是物理占用。删除文件后逻辑大小不变、
物理收缩有延迟。判断真实占用一律 `du -h`。

## 10. ext4 结构性下限（为什么压不到更小）

WSL 默认创建 1TiB ext4 文件系统，预分配约 6710 万个 inode × 256B ≈ **16GB
inode 表**，加 journal 和元数据约 2GB。这是文件系统结构性开销，与数据量无关。
实测数据 36GB 时 vhdx 压到 57GB 即接近下限。要突破只能
`wsl --export` + `--import` 重建文件系统，代价：36GB 临时打包、十几分钟、
重新导入后默认用户可能重置需修 `/etc/wsl.conf`。**除非用户明确要求，不建议。**

## 11. UNC 路径的局限

- `\\wsl.localhost\<distro>\etc\os-release` 是 symlink，直读报 I/O error；
  改读 `/usr/lib/os-release`（实体文件）。
- UNC 上 `chmod`/`chown` 不生效（drvfs 限制）。
- 大量小文件读写比 WSL 内部慢——UNC 当"另一个磁盘"做查看和轻量编辑，
  重活扔进 WSL 内部执行。

## 12. shell 状态不跨调用保留

每次 `wsl --` 调用都是全新 shell，`cd` 不保留。需要 cd 时：

```bash
wsl -d <distro> -- bash -lc "cd /path && cmd"
```

## 13. shutdown 影响所有发行版

`wsl --shutdown` 会停掉整个 WSL（所有发行版 + 里面所有服务，含 Docker、
pentagi 等）。执行 compact 前告知用户。

## 14. 本机环境事实（2026-10-17 验证）

| 项 | 值 |
|----|----|
| 发行版 | `Ubuntu-22.04`（默认）、`pentagi` |
| vhdx | `D:\WSL\instances\Ubuntu\ext4.vhdx` |
| WSL 版本 | 3.0.3（支持 `--manage --compact`，无需管理员） |
| Windows 侧 Docker CLI | 未安装，docker 只能在 WSL 内跑 |
| WSL 内用户 | `zhouhui`、`openmind` |
