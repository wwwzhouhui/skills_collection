# wsl-disk-cleanup：WSL 磁盘一键清理（Docker 全清 + vhdx 原生压缩）

> [skills_collection](../../README.md) 合集的一部分。

给智能体一句话——**"清理 WSL" / "压缩 vhdx" / "清一下 Docker 腾空间"**——它就在 Windows 侧把活全干了：扫描 WSL 磁盘占用 → 列清单等你确认 → 停掉会自愈的 1Panel → Docker 容器/镜像/卷/缓存全清 → 原生压缩 ext4.vhdx → 交回前后对比报告。**不用进 WSL 的 Linux 终端，不用管理员权限。**

本 skill 沉淀自一次真实运维：Docker 数据 24 GB、vhdx 物理占用 80 GB 的 Ubuntu-22.04，一轮操作后 Docker 数据剩 150 MB、vhdx 降到 57 GB。

## 实测效果（真实运行数据）

| 指标 | 清理前 | 清理后 |
| --- | --- | --- |
| ext4.vhdx 物理占用 | 80 GB | **57 GB** |
| WSL 文件系统已用 | 53 GB | 36 GB |
| Docker 数据（/var/lib/docker） | 24 GB | 150 MB |
| 容器 / 镜像 / 卷 | 10 / 12 / 37 | **0 / 0 / 0** |
| 宿主机 D 盘可用空间 | 55 GB | 63 GB |

压缩后 vhdx 物理 = 逻辑（无空洞）；sparse 保持关闭，以后想再收缩，一条命令即可：

```bash
wsl --shutdown && wsl --manage <发行版名> --compact
```

## 它是怎么做的

```
枚举发行版（wsl -l -v，注册名不是想当然的 Ubuntu）
   → scan.sh 只读扫描（Docker 容器/镜像/卷/占用 + 1Panel 状态 + 目录占用 TOP）
   → 列清单 + AskUserQuestion 确认范围（A 只删容器 / B 全清 / C 删容器+镜像留卷）
   → clean-docker.sh（先 systemctl disable --now 1Panel，再删容器、prune 全清）
   → compact-vhdx.sh（shutdown → set-sparse false → compact，前后大小对比）
   → 验证零状态 + 前后对比报告
```

| 环节 | 做法 |
| --- | --- |
| 不进 WSL 终端 | 全部通过 Windows 侧 `wsl.exe` 非交互调用；WSL 内文件也可走 `\\wsl.localhost\<发行版>\` UNC 路径直读 |
| 脚本送入 WSL | **stdin 管道**：`wsl -d <发行版> -- bash -s < script.sh`——脚本在 WSL 内部 bash 里整体解释，`$()` 完全不受外层 shell 干扰，同时免掉 MSYS 把 `/tmp` 改写成 Windows 路径的坑 |
| 防 1Panel 自愈 | 清理第一步先 `systemctl disable --now 1panel-agent 1panel-core`——1Panel 以 systemd 服务运行，删掉的容器会被它按 compose 应用自动重建，kill 进程也会被立刻拉起 |
| vhdx 压缩 | WSL 3.0.3+ 原生 `wsl --manage <发行版> --compact`，**无需管理员**；与 sparse 互斥，必须先 `--set-sparse false` 再 compact |
| 安全底线 | 铁律：先扫描列清单、经用户确认后才执行删除；报告必须给前后对比；`wsl --shutdown` 停所有发行版会提前告知 |

## 仓库内容

| 路径 | 说明 |
| --- | --- |
| `SKILL.md` | 技能入口，AI 读这个：五步标准流程 + 6 条铁律 + 脚本执行方式 |
| `README.md` | 本文件，给人看 |
| `scripts/scan.sh` | WSL 内只读扫描：系统信息、根分区、Docker 容器/镜像/卷/磁盘占用、1Panel 自愈排查、目录占用 TOP |
| `scripts/clean-docker.sh` | WSL 内 Docker 全清：停 1Panel → 强制删全部容器 → prune 镜像/网络/缓存/卷 → 兜底清命名卷 → 验证零状态 |
| `scripts/compact-vhdx.sh` | Windows 侧压缩：shutdown → set-sparse false → compact → 前后大小对比，失败时给 diskpart 降级提示 |
| `references/wsl-gotchas.md` | 14 条实战避坑：黑名单放行、发行版名、WSL_UTF8 乱码、命令替换陷阱、1Panel 自愈、sparse/compact 互斥、UNC 限制、ext4 inode 下限等 |

## 安装

**用户级（推荐，跨项目可用）**：把整个目录拷到

```
C:\Users\<用户名>\.workbuddy\skills\wsl-disk-cleanup
```

**项目级（与团队共享）**：放到项目的 `.workbuddy/skills/` 下。

装完对着智能体说"清理 WSL"即触发，无需记任何命令。

## 已知边界（管理预期用）

- **vhdx 有物理下限**：WSL 默认创建 1 TiB ext4，预分配约 6710 万 inode ≈ 16 GB inode 表 + journal，属文件系统结构性开销；数据 36 GB 时约 57 GB 即接近下限。再瘦只能 `wsl --export` + `--import` 重建（临时打包大、耗时长、默认用户可能重置），非必要不做。
- **shutdown 影响全量**：`wsl --shutdown` 会停掉所有发行版及其中全部服务（Docker、pentagi 等），压缩前智能体会先告知。
- **版本要求**：原生压缩需 WSL ≥ 3.0.3（`wsl --version` 可查）；旧版本降级到管理员 diskpart 方案，命令在 `references/wsl-gotchas.md` 第 8 节。
- **UNC 局限**：`\\wsl.localhost\` 上 chmod/chown 不生效、`/etc/os-release` 是 symlink 直读报错（改读 `/usr/lib/os-release`）、大量小文件慢——查看和轻量编辑可以，重活放进 WSL 内部执行。
