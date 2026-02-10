#!/usr/bin/env bash
set -euo pipefail

# Seedance 2.0 视频生成脚本
# 用法:
#   generate_video.sh --prompt "提示词" [--files file1.jpg file2.jpg] [--options]

# 默认参数
API_URL="${JIMENG_API_URL:-http://127.0.0.1:8000}"
SESSION_ID="${JIMENG_SESSION_ID:-}"
MODEL="seedance-2.0"
RATIO="16:9"
RESOLUTION="720p"
DURATION=10
PROMPT=""
OUTPUT_DIR="."
FILES=()
TIMEOUT=300

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
  cat << 'EOF'
Seedance 2.0 视频生成脚本

用法:
  generate_video.sh [选项]

必需参数:
  --prompt TEXT        视频描述提示词
  --session-id ID      即梦 SessionID（或设置 JIMENG_SESSION_ID 环境变量）

可选参数:
  --model MODEL        模型名称 (默认: seedance-2.0)
  --ratio RATIO        画面比例 (默认: 16:9，可选: 1:1/4:3/3:4/16:9/9:16)
  --resolution RES     分辨率 (默认: 720p，可选: 480p/720p/1080p)
  --duration SEC       时长秒数 (默认: 10，可选: 4/5/10)
  --files FILE...      参考图片路径（可多个）
  --output-dir DIR     输出目录 (默认: 当前目录)
  --api-url URL        API 地址 (默认: http://127.0.0.1:8000)
  --timeout SEC        超时秒数 (默认: 300)
  -h, --help           显示帮助

示例:
  # 纯文本生成
  generate_video.sh --session-id "xxx" --prompt "海边女孩跳舞"

  # 多图参考生成
  generate_video.sh --session-id "xxx" \
    --prompt "@1 和 @2 两人跳舞" \
    --files dancer1.jpg dancer2.jpg \
    --ratio 4:3 --duration 10
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

# 解析参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --prompt)
      PROMPT="$2"
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
    --resolution)
      RESOLUTION="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --files)
      shift
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^-- ]]; do
        FILES+=("$1")
        shift
      done
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

# 构建请求
log_info "开始生成视频..."
log_info "模型: ${MODEL}"
log_info "比例: ${RATIO}"
log_info "分辨率: ${RESOLUTION}"
log_info "时长: ${DURATION}秒"
log_info "参考图片: ${#FILES[@]}张"

RESPONSE=""

if [[ ${#FILES[@]} -gt 0 ]]; then
  # multipart/form-data 方式（有图片）
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

  RESPONSE=$(curl "${CURL_ARGS[@]}")
else
  # JSON 方式（纯文本）
  RESPONSE=$(curl -s --max-time "${TIMEOUT}" -X POST "${API_URL}/v1/videos/generations" \
    -H "Authorization: Bearer ${SESSION_ID}" \
    -H "Content-Type: application/json" \
    -d "{
      \"model\": \"${MODEL}\",
      \"prompt\": $(echo "${PROMPT}" | jq -Rs .),
      \"ratio\": \"${RATIO}\",
      \"resolution\": \"${RESOLUTION}\",
      \"duration\": ${DURATION}
    }")
fi

# 解析响应
VIDEO_URL=$(echo "${RESPONSE}" | jq -r '.data[0].url // empty')

if [[ -z "${VIDEO_URL}" ]]; then
  ERROR_MSG=$(echo "${RESPONSE}" | jq -r '.error.message // .message // empty')
  if [[ -n "${ERROR_MSG}" ]]; then
    log_error "生成失败: ${ERROR_MSG}"
  else
    log_error "生成失败，API 响应:"
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
