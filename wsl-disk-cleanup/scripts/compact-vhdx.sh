#!/bin/bash
# ============================================================
# vhdx 原生压缩（WSL 3.0.3+，无需管理员权限）
#
# 用法（在 Windows 的 Git Bash / WorkBuddy Bash 工具中执行）：
#   bash "<skill目录>/scripts/compact-vhdx.sh" <发行版名> [vhdx路径]
# 例：
#   bash "<skill目录>/scripts/compact-vhdx.sh" Ubuntu-22.04 "D:/WSL/instances/Ubuntu/ext4.vhdx"
#
# 注意：
#   1. compact 与 sparse 互斥，必须先 --set-sparse false
#   2. wsl --shutdown 会停止所有发行版（含 pentagi 等）
#   3. vhdx 路径可选；不传则跳过前后大小对比
# ============================================================

DISTRO="${1:?- 用法: compact-vhdx.sh <发行版名> [vhdx路径]}"
VHDX="${2:-}"

size_report() {
    if [ -n "$VHDX" ] && [ -f "$VHDX" ]; then
        ls -lh "$VHDX" | awk '{print "  逻辑大小: "$5}'
        du -h "$VHDX" | awk '{print "  物理占用: "$1}'
    else
        echo "  (未提供 vhdx 路径或文件不存在，跳过)"
    fi
}

echo "=== 压缩前 vhdx 状态 ==="
size_report

echo "=== 关闭 WSL（所有发行版）==="
wsl --shutdown
sleep 2

echo "=== 关闭 sparse（与 compact 互斥，必须先关）==="
wsl --manage "$DISTRO" --set-sparse false

echo "=== 执行原生压缩 ==="
wsl --manage "$DISTRO" --compact
rc=$?
if [ $rc -ne 0 ]; then
    echo "❌ compact 失败（退出码 $rc）。常见原因：WSL 版本 < 3.0.3 不支持 --manage。"
    echo "   降级方案：管理员 PowerShell 中执行 diskpart compact vdisk（见 references/wsl-gotchas.md）"
    exit $rc
fi

echo "=== 压缩后 vhdx 状态 ==="
size_report
echo "✅ 压缩完成"
