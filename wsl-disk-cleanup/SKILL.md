---
name: wsl-disk-cleanup
description: 一键扫描并清理 WSL 磁盘占用：Docker 容器/镜像/卷/缓存全清 + ext4.vhdx 原生压缩（WSL 3.0.3+，无需管理员权限）。当用户要求"清理 WSL"、"压缩 vhdx / ext4.vhdx"、"清理 WSL 里的 Docker"、"释放 WSL 磁盘空间"、"WSL 占用的磁盘越来越大"、"删了镜像 vhdx 没变小"时使用。固定流程：扫描列清单 → 用户确认范围 → 停用 1Panel 自愈服务 → Docker 全清 → vhdx 压缩 → 前后对比报告。内置 sparse/compact 互斥、wsl.exe 命令替换陷阱、UNC 路径限制等避坑知识。
agent_created: true
---

# WSL 磁盘清理（Docker 全清 + vhdx 压缩）

## 目的

在不进入 WSL Linux 终端的前提下，通过 Windows 侧 `wsl.exe` 完成 WSL 磁盘维护：
只读扫描占用 → 用户确认删除范围 → 清理 Docker（容器/镜像/卷/构建缓存）→
原生压缩 ext4.vhdx → 输出前后对比报告。全程无需管理员权限（要求 WSL ≥ 3.0.3）。

## 何时使用

- 用户说"清理 WSL"、"压缩 vhdx"、"WSL 占的磁盘太大"、"清一下 Docker 腾空间"
- 删除大量镜像/数据后 vhdx 物理大小没有回落
- WSL 定期维护、Docker 数据日积月累需要回收

## 铁律（动手前必读）

1. **先扫描、后确认、再执行**。任何删除前必须先跑 `scan.sh` 并向用户展示清单，
   用 AskUserQuestion 确认范围。用户长期坚持此安全习惯，禁止跳过。
2. **发行版名必须是注册名**（不是想当然的 `Ubuntu`，本机是 `Ubuntu-22.04`）。
   每次先 `wsl -l -v` 枚举。
3. **清 Docker 前必须先停用 1Panel**（`1panel-agent.service` + `1panel-core.service`），
   否则它会自动重建容器（kill 进程也会被 systemd 拉起，必须 `systemctl disable --now`）。
4. **`--compact` 与 sparse 互斥**：compact 前必须先 `--set-sparse false`。
5. **压缩会 shutdown 整个 WSL**（停止所有发行版及其中全部服务），执行前告知用户。
6. **`wsl --shutdown` 与 `--compact` 只在 Windows 侧执行**，脚本分两侧：
   WSL 内部脚本用 `wsl -d <distro> -- bash -s <` 送入；Windows 侧脚本直接 `bash` 跑。

## 脚本清单

| 脚本 | 执行位置 | 作用 |
|------|----------|------|
| `scripts/scan.sh` | WSL 内部 | 只读扫描：系统信息、Docker 容器/镜像/卷/占用、1Panel 状态、目录占用 TOP |
| `scripts/clean-docker.sh` | WSL 内部 | 停 1Panel → 强制删全部容器 → prune 镜像/网络/缓存/卷 → 验证零状态 |
| `scripts/compact-vhdx.sh` | Windows 侧 | shutdown → set-sparse false → compact → 前后大小对比 |

## 脚本执行方式（关键）

脚本文件在 Windows 磁盘，送入 WSL 执行时**统一用 stdin 管道**，
避免 MSYS 路径转换和 `$()` 被外层 shell 提前展开的陷阱：

```bash
export WSL_UTF8=1 MSYS_NO_PATHCONV=1
wsl -d <发行版名> -- bash -s < "<skill目录>/scripts/scan.sh"
```

Windows 侧脚本直接执行（在 Git Bash / Bash 工具中）：

```bash
bash "<skill目录>/scripts/compact-vhdx.sh" <发行版名> <vhdx路径>
```

`<skill目录>` 即本 SKILL.md 所在目录（用户级：`C:\Users\75271\.workbuddy\skills\wsl-disk-cleanup`，
Git Bash 中写 `C:/Users/75271/.workbuddy/skills/wsl-disk-cleanup`）。

## 标准流程（五步）

### 第 1 步：枚举发行版 + 扫描

```bash
export WSL_UTF8=1 MSYS_NO_PATHCONV=1
wsl -l -v
wsl -d <发行版名> -- bash -s < "<skill目录>/scripts/scan.sh"
```

vhdx 物理大小在 Windows 侧查（WSL 内部看不到宿主机文件大小）：

```bash
ls -lh <vhdx路径> && du -h <vhdx路径>
```

vhdx 路径未知时，用 PowerShell 查注册表拿实际路径（见 references/wsl-gotchas.md 第 2 节）。

### 第 2 步：展示清单 + 确认范围（AskUserQuestion，必做）

把扫描结果整理成表格呈现，然后提供典型选项让用户选择：

- **A：只删容器，保留镜像+卷**——最稳，服务可 `docker compose up -d` 原样恢复，数据无损；vhdx 靠压缩回收空洞
- **B：全清**（容器+镜像+卷+构建缓存）——释放最大；数据库数据不可恢复，需重新拉镜像重建
- **C：删容器+镜像，保留卷**——折中；数据卷还在，但恢复需重新 pull/构建镜像

### 第 3 步：执行 Docker 清理

```bash
wsl -d <发行版名> -- bash -s < "<skill目录>/scripts/clean-docker.sh"
```

### 第 4 步：压缩 vhdx

```bash
bash "<skill目录>/scripts/compact-vhdx.sh" <发行版名> <vhdx路径>
```

### 第 5 步：验证 + 报告

- WSL 内：`docker ps -a` / `docker images` / `docker volume ls` 应为空
- Windows 侧：`ls -lh` + `du -h` 对比 vhdx 前后大小
- 报告格式：清理项表格（删了什么/释放量）+ vhdx 前后对比 + 宿主机磁盘可用前后对比

## 深度清理（可选，需单独确认）

扫描中若发现非 Docker 大户（`/root` 内核源码、`~/.nvm` 旧版本、`~/.cache`、
旧 snap 挂载等），单独列清单让用户确认后再删，不混入 Docker 清理流程。

常见可清项：`/usr/src` 下旧 WSL2 内核源码、`~/.cache`、`~/.npm`、
`/var/lib/docker`（已由上流程清空）。

## 已知限制（提前告知用户，管理预期）

- vhdx 有物理下限：1TiB ext4 预分配约 6710 万 inode ≈ 16GB inode 表 + journal，
  数据 36GB 时 vhdx 约 57GB 即接近下限。突破需 export/import 重建文件系统
  （临时打包大、耗时长、默认用户可能重置），除非用户明确要求否则不做。
- `\\wsl.localhost\<distro>\etc\os-release` 是 symlink，UNC 直读报错，改读 `/usr/lib/os-release`。
- UNC 路径 chmod/chown 不生效，大量小文件慢；重活放进 WSL 内部执行。
- 每次 `wsl --` 都是新 shell，`cd` 不跨调用保留；需 cd 时写 `bash -lc "cd /path && cmd"`。
- `wsl --shutdown` 停止所有发行版（含 pentagi 等）。

## Resources

### scripts/

- `scan.sh` —— WSL 内部只读扫描（stdin 管道送入执行）
- `clean-docker.sh` —— WSL 内部 Docker 全清（stdin 管道送入执行）
- `compact-vhdx.sh` —— Windows 侧 vhdx 原生压缩（直接 bash 执行）

### references/

- `wsl-gotchas.md` —— 14 条实战避坑：黑名单放行、发行版名、WSL_UTF8、
  MSYS_NO_PATHCONV、命令替换陷阱、1Panel 自愈、sparse/compact 互斥、
  diskpart 降级方案、逻辑/物理大小、ext4 inode 下限、UNC 限制、
  shell 状态、shutdown 影响面、本机环境事实。执行异常时先查此文件。
