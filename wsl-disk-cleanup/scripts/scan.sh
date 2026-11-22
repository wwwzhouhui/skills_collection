#!/bin/bash
# ============================================================
# WSL 磁盘占用扫描（只读，零删除、零修改）
#
# 用法（在 Windows 的 Git Bash / WorkBuddy Bash 工具中执行）：
#   export WSL_UTF8=1 MSYS_NO_PATHCONV=1
#   wsl -d <发行版名> -- bash -s < "<skill目录>/scripts/scan.sh"
#
# 说明：本脚本在 WSL 内部执行，扫描结果只读输出；
#       vhdx 物理大小需在 Windows 侧单独查看（本脚本看不到宿主机文件）。
# ============================================================

echo "========== [1] 系统信息 =========="
grep PRETTY_NAME /etc/os-release 2>/dev/null || head -2 /usr/lib/os-release
echo "内核: $(uname -r) | 内存: $(free -h | awk '/Mem:/{print $2}') | CPU: $(nproc) 核"

echo
echo "========== [2] 根分区使用情况 =========="
df -h /

echo
echo "========== [3] Docker 容器 =========="
if command -v docker >/dev/null 2>&1; then
    docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Size}}" 2>/dev/null || echo "(docker daemon 未响应)"
    echo "--- 容器总数（含停止）: $(docker ps -aq 2>/dev/null | wc -l) ---"
else
    echo "(未安装 docker)"
fi

echo
echo "========== [4] Docker 镜像 =========="
if command -v docker >/dev/null 2>&1; then
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}" 2>/dev/null
    echo "--- 镜像总数: $(docker images -q 2>/dev/null | wc -l) ---"
    echo "--- 悬空镜像: $(docker images -f dangling=true -q 2>/dev/null | wc -l) ---"
fi

echo
echo "========== [5] Docker 卷 =========="
if command -v docker >/dev/null 2>&1; then
    docker volume ls 2>/dev/null
    echo "--- 卷总数: $(docker volume ls -q 2>/dev/null | wc -l) ---"
fi

echo
echo "========== [6] Docker 磁盘占用 =========="
docker system df 2>/dev/null || echo "(docker 不可用)"
du -sh /var/lib/docker 2>/dev/null

echo
echo "========== [7] 自愈服务排查（清理前必须确认）=========="
for svc in 1panel-agent 1panel-core; do
    active=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
    enabled=$(systemctl is-enabled "$svc" 2>/dev/null || echo "disabled")
    echo "$svc: active=$active enabled=$enabled"
done
ps -eo pid,cmd | grep -i 1panel | grep -v grep || echo "(无 1Panel 进程)"
echo "注意: 1Panel 启用时会在容器被删后自动重建，清理前必须先 systemctl disable --now"

echo
echo "========== [8] / 下目录占用 TOP11（含 / 自身）=========="
du -xh --max-depth=1 / 2>/dev/null | sort -rh | head -11

echo
echo "========== [9] /root 与 /home 明细（常见隐藏大户）=========="
du -xh --max-depth=1 /root 2>/dev/null | sort -rh | head -6
du -xh --max-depth=1 /home 2>/dev/null | sort -rh | head -6
