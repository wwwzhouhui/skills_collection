#!/usr/bin/env bash
set -euo pipefail

# Seedance 2.0 视频生成脚本（三阶段工作流）
# 阶段一：如果没有图片，先调用文生图 API 生成首帧参考图
# 阶段二：下载首帧图片到本地
# 阶段三：用参考图 + 提示词调用 Seedance 2.0 生成视频
#
# 用法:
#   generate_video.sh --prompt "视频提示词" [--image-prompt "首帧图片提示词"] [--files file1.jpg] [--options]

# 默认参数
API_URL="${JIMENG_API_URL:-http://127.0.0.1:8000}"
SESSION_ID="${JIMENG_SESSION_ID:-}"
MODEL="seedance-2.0-fast"
RATIO="9:16"
DURATION=4
PROMPT=""
IMAGE_PROMPT=""
OUTPUT_DIR="."
FILES=()
TIMEOUT=300
IMAGE_MODEL="jimeng-4.5"
IMAGE_RESOLUTION="2k"
RESOLUTION="720p"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
  cat << 'EOF'
Seedance 2.0 视频生成脚本（三阶段工作流）

重要：Seedance 2.0 必须至少提供一张图片，不支持纯文本生成视频。
当没有提供图片时，脚本会自动通过文生图 API 生成首帧参考图。

用法:
  generate_video.sh [选项]

必需参数:
  --prompt TEXT          视频描述提示词（含 @1 引用首帧图片）
  --session-id ID        即梦 SessionID（或设置 JIMENG_SESSION_ID 环境变量）

条件必需（无 --files 时必需）:
  --image-prompt TEXT    首帧图片描述提示词（用于文生图生成首帧）

可选参数:
  --model MODEL          视频模型名称 (默认: seedance-2.0-fast，可选: jimeng-video-seedance-2.0-fast/jimeng-video-seedance-2.0/seedance-2.0-pro)
  --ratio RATIO          画面比例 (默认: 9:16，可选: 1:1/4:3/3:4/16:9/9:16/3:2/2:3/21:9)
  --resolution RES       视频分辨率 (默认: 720p，可选: 480p/720p/1080p)
  --duration SEC         时长秒数 (默认: 4，范围: 4-15)
  --files FILE...        参考图片路径（可多个，有图片时跳过文生图阶段）
  --image-model MODEL    文生图模型 (默认: jimeng-4.5)
  --output-dir DIR       输出目录 (默认: 当前目录)
  --api-url URL          API 地址 (默认: http://127.0.0.1:8000)
  --timeout SEC          超时秒数 (默认: 300)
  -h, --help             显示帮助

示例:
  # 无图片 → 自动生成首帧 → 生成视频（三阶段）
  generate_video.sh --session-id "xxx" \
    --image-prompt "海边沙滩，女孩穿白裙站在海边，夕阳逆光" \
    --prompt "电影级写实风格，4秒，9:16竖屏\n\n@1 作为画面首帧参考\n\n0-1秒：中景，女孩面朝大海\n1-3秒：女孩开始旋转起舞\n3-4秒：远景拉远定格" \
    --ratio 9:16 --duration 4

  # 有图片 → 直接生成视频（跳过文生图）
  generate_video.sh --session-id "xxx" \
    --prompt "@1 和 @2 两人跳舞" \
    --files dancer1.jpg dancer2.jpg \
    --ratio 4:3 --duration 10

  # 使用快速模型
  generate_video.sh --session-id "xxx" \
    --prompt "@1 和 @2 两人跳舞" \
    --files dancer1.jpg dancer2.jpg \
    --model jimeng-video-seedance-2.0-fast \
    --ratio 4:3 --duration 10 --resolution 1080p
EOF
  exit 0
}

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

log_phase() {
  echo -e "${BLUE}[阶段]${NC} $1"
}

# 解析参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --prompt)
      PROMPT="$2"
      shift 2
      ;;
    --image-prompt)
      IMAGE_PROMPT="$2"
      shift 2
      ;;
    --session-id)
      SESSION_ID="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --ratio)
      RATIO="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --resolution)
      RESOLUTION="$2"
      shift 2
      ;;
    --files)
      shift
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do
        FILES+=("$1")
        shift
      done
      ;;
    --image-model)
      IMAGE_MODEL="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --api-url)
      API_URL="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      log_error "未知参数: $1"
      usage
      ;;
  esac
done

# 参数验证
if [[ -z "${PROMPT}" ]]; then
  log_error "缺少必需参数: --prompt"
  exit 1
fi

if [[ -z "${SESSION_ID}" ]]; then
  log_error "缺少 SessionID，请通过 --session-id 或 JIMENG_SESSION_ID 环境变量提供"
  exit 1
fi

# 如果没有图片且没有首帧提示词，报错
if [[ ${#FILES[@]} -eq 0 ]] && [[ -z "${IMAGE_PROMPT}" ]]; then
  log_error "Seedance 2.0 必须至少提供一张图片。请通过 --files 提供图片，或通过 --image-prompt 提供首帧图片描述（脚本将自动生成首帧图片）"
  exit 1
fi

# 检查依赖
for cmd in curl jq; do
  if ! command -v "${cmd}" &> /dev/null; then
    log_error "${cmd} 未安装，请先安装"
    exit 1
  fi
done

# 验证图片文件存在
for f in "${FILES[@]}"; do
  if [[ ! -f "${f}" ]]; then
    log_error "文件不存在: ${f}"
    exit 1
  fi
done

# 创建输出目录
[[ -d "${OUTPUT_DIR}" ]] || mkdir -p "${OUTPUT_DIR}"

# ============================================================
# 阶段一 & 二：文生图生成首帧（仅在没有图片时执行）
# ============================================================
if [[ ${#FILES[@]} -eq 0 ]]; then
  log_phase "=== 第一阶段：文生图生成首帧参考图 ==="
  log_info "模型: ${IMAGE_MODEL}"
  log_info "比例: ${RATIO}"
  log_info "分辨率: ${IMAGE_RESOLUTION}"
  log_info "首帧提示词: ${IMAGE_PROMPT:0:80}..."

  IMAGE_RESPONSE=$(curl -s --max-time 120 -X POST "${API_URL}/v1/images/generations" \
    -H "Authorization: Bearer ${SESSION_ID}" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"${IMAGE_MODEL}\",
      \"prompt\": $(echo "${IMAGE_PROMPT}" | jq -Rs .),
      \"ratio\": \"${RATIO}\",
      \"resolution\": \"${IMAGE_RESOLUTION}\"
    }")

  IMAGE_URL=$(echo "${IMAGE_RESPONSE}" | jq -r '.data[0].url // empty')

  if [[ -z "${IMAGE_URL}" ]]; then
    ERROR_MSG=$(echo "${IMAGE_RESPONSE}" | jq -r '.error.message // .message // empty')
    if [[ -n "${ERROR_MSG}" ]]; then
      log_error "文生图失败: ${ERROR_MSG}"
    else
      log_error "文生图失败，API 响应:"
      echo "${IMAGE_RESPONSE}" | jq . 2>/dev/null || echo "${IMAGE_RESPONSE}"
    fi
    exit 1
  fi

  log_info "首帧图片生成成功"

  log_phase "=== 第二阶段：下载首帧图片 ==="
  IMAGE_FILE="/tmp/seedance_frame_$(date +%Y%m%d_%H%M%S).png"
  if curl -sL -o "${IMAGE_FILE}" "${IMAGE_URL}"; then
    IMAGE_SIZE=$(du -h "${IMAGE_FILE}" | cut -f1)
    log_info "首帧图片已下载: ${IMAGE_FILE} (${IMAGE_SIZE})"
    FILES=("${IMAGE_FILE}")
  else
    log_error "首帧图片下载失败"
    log_info "图片 URL: ${IMAGE_URL}"
    exit 1
  fi
fi

# ============================================================
# 阶段三：Seedance 2.0 视频生成
# ============================================================
log_phase "=== 第三阶段：Seedance 2.0 视频生成 ==="
log_info "模型: ${MODEL}"
log_info "比例: ${RATIO}"
log_info "分辨率: ${RESOLUTION}"
log_info "时长: ${DURATION}秒"
log_info "参考图片: ${#FILES[@]}张"

CURL_ARGS=(-s --max-time "${TIMEOUT}" -X POST "${API_URL}/v1/videos/generations")
CURL_ARGS+=(-H "Authorization: Bearer ${SESSION_ID}")
CURL_ARGS+=(-F "model=${MODEL}")
CURL_ARGS+=(-F "prompt=${PROMPT}")
CURL_ARGS+=(-F "ratio=${RATIO}")
CURL_ARGS+=(-F "resolution=${RESOLUTION}")
CURL_ARGS+=(-F "duration=${DURATION}")

for f in "${FILES[@]}"; do
  CURL_ARGS+=(-F "files=@${f}")
done

log_info "正在生成视频（通常需要 60-120 秒）..."
RESPONSE=$(curl "${CURL_ARGS[@]}")

# 解析响应
VIDEO_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url // empty')

if [[ -z "${VIDEO_URL}" ]]; then
  ERROR_MSG=$(echo "${RESPONSE}" | jq -r '.error.message // .message // empty')
  ERROR_CODE=$(echo "${RESPONSE}" | jq -r '.code // empty')
  if [[ "${ERROR_CODE}" == "-2001" ]]; then
    log_error "Seedance 2.0 需要至少一张图片（错误码: -2001）"
    log_error "请检查图片文件是否正确上传"
  elif [[ -n "${ERROR_MSG}" ]]; then
    log_error "视频生成失败: ${ERROR_MSG}"
  else
    log_error "视频生成失败，API 响应:"
    echo "${RESPONSE}" | jq . 2>/dev/null || echo "${RESPONSE}"
  fi
  exit 1
fi

# 下载视频
OUTPUT_FILE="${OUTPUT_DIR}/seedance_$(date +%Y%m%d_%H%M%S).mp4"
log_info "视频生成成功，开始下载..."

if curl -L -s -o "${OUTPUT_FILE}" "${VIDEO_URL}"; then
  FILE_SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
  log_info "下载完成!"
  log_info "文件路径: ${OUTPUT_FILE}"
  log_info "文件大小: ${FILE_SIZE}"
else
  log_error "视频下载失败"
  log_info "视频 URL: ${VIDEO_URL}"
  exit 1
fi
