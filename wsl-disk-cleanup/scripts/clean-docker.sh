#!/bin/bash
# ============================================================
# WSL Docker 全清（危险操作：删除全部容器/镜像/卷/缓存）
#
# 用法（在 Windows 的 Git Bash / WorkBuddy Bash 工具中执行）：
#   export WSL_UTF8=1 MSYS_NO_PATHCONV=1
#   wsl -d <发行版名> -- bash -s < "<skill目录>/scripts/clean-docker.sh"
#
# 前提：已向用户展示扫描清单并获得明确确认。
# 流程：记录基线 → 停用 1Panel 自愈服务 → 强制删全部容器
#       → prune 镜像/网络/缓存/卷 → 兜底清命名卷 → 验证零状态
# ============================================================

echo "=== [0/5] 清理前基线 ==="
before_docker=$(du -sh /var/lib/docker 2>/dev/null | cut -f1)
before_c=$(docker ps -aq 2>/dev/null | wc -l)
before_i=$(docker images -q 2>/dev/null | wc -l)
before_v=$(docker volume ls -q 2>/dev/null | wc -l)
echo "docker 数据目录: ${before_docker:-未知}"
echo "容器 ${before_c} 个 / 镜像 ${before_i} 个 / 卷 ${before_v} 个"

echo
echo "=== [1/5] 停用 1Panel 自愈服务（防止删后自动重建）==="
systemctl disable --now 1panel-agent.service 1panel-core.service 2>/dev/null
sleep 2
if ps -eo cmd | grep -i 1panel | grep -v grep >/dev/null 2>&1; then
    echo "⚠️ 1Panel 仍在运行，kill 兜底"
    pkill -f 1panel 2>/dev/null
    sleep 1
fi
if ps -eo cmd | grep -i 1panel | grep -v grep >/dev/null 2>&1; then
    echo "❌ 1Panel 仍存活，请人工检查（否则容器会被反复重建）"
else
    echo "✅ 1Panel 已停止且禁用开机自启"
fi

echo
echo "=== [2/5] 强制删除全部容器（含运行中）==="
if [ "$before_c" -gt 0 ]; then
    docker rm -f $(docker ps -aq) 2>&1 | tail -3
else
    echo "(无容器)"
fi

echo
echo "=== [3/5] 全清镜像 / 网络 / 构建缓存 / 卷 ==="
docker system prune -a --volumes -f 2>&1 | tail -5

echo
echo "=== [4/5] 兜底：清理未使用命名卷 ==="
docker volume prune -a -f 2>&1 | tail -3

echo
echo "=== [5/5] 验证零状态 ==="
after_c=$(docker ps -aq 2>/dev/null | wc -l)
after_i=$(docker images -q 2>/dev/null | wc -l)
after_v=$(docker volume ls -q 2>/dev/null | wc -l)
after_docker=$(du -sh /var/lib/docker 2>/dev/null | cut -f1)
echo "剩余: 容器 ${after_c} / 镜像 ${after_i} / 卷 ${after_v}"
echo "docker 数据目录: ${before_docker:-?} -> ${after_docker:-?}"
if [ "$after_c" -eq 0 ] && [ "$after_i" -eq 0 ] && [ "$after_v" -eq 0 ]; then
    echo "✅ Docker 已完全清空"
else
    echo "⚠️ 存在残留，检查是否有其他守护进程（如 1Panel、k8s）在重建"
fi
