#!/usr/bin/env bash
# 无声循环 MP4 渲染管线 (HyperFrames, silent 模式)
# 用法: ./build_silent.sh <project_dir> [output.mp4]
#   project_dir: 含 index.html 的 HyperFrames 项目 (与配音视频共用同一个 index.html)
#   output.mp4:  输出文件名 (默认 renders/<dirname>-silent.mp4)
# 产物:
#   <project_dir>/renders/<name>-silent.mp4   1080p 无声循环 (~32s), 公众号内嵌自动播放
#   <project_dir>/preview/montage-silent.png  7 场景中点蒙太奇
#
# 原理: index.html 用 mode 变量 (video/silent) 单文件双用。silent 模式紧凑时间轴 (每段
# SILENT_SEG 秒)、无字幕、不淡出、保留全部质感和动效。本脚本生成一个临时子目录, 把
# data-duration 改成 silent 总时长 + 删掉 <audio>, 用 --variables mode=silent 渲染。

set -euo pipefail

FFMPEG=${FFMPEG:-ffmpeg}
FFPROBE=${FFPROBE:-ffprobe}
SILENT_SEG=${SILENT_SEG:-4.6}   # 与 index.html 里的 SILENT_SEG 一致

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <project_dir> [output.mp4]"
  exit 1
fi
PROJECT_DIR=$1
shift
cd "$PROJECT_DIR"
NAME=$(basename "$(pwd)")
OUTPUT=${1:-renders/${NAME}-silent.mp4}
mkdir -p renders preview

# silent 总时长 = 7 段 × SILENT_SEG
TOTAL=$(python3 -c "print(round(7 * $SILENT_SEG, 2))")

# ---- 1. 生成临时构建目录 (改 data-duration + 删 audio, 自包含) ----
echo "==> 准备 silent 构建 (每段 ${SILENT_SEG}s, 总 ${TOTAL}s)..."
BUILD=.silentbuild
rm -rf "$BUILD" && mkdir -p "$BUILD"
python3 - "$TOTAL" <<'PY'
import re, sys
total = sys.argv[1]
s = open("index.html", encoding="utf-8").read()
# 根 div 的 data-duration 改成 silent 总时长 (只改根, 不动 audio 的 data-duration)
s = re.sub(r'(data-composition-id="main"[^>]*?data-duration=")[\d.]+(")',
           rf'\g<1>{total}\g<2>', s, count=1, flags=re.S)
s = re.sub(r'(data-start="0" data-duration=")[\d.]+(")', rf'\g<1>{total}\g<2>', s, count=1)
# 删 <audio> (无声不需要)
s = re.sub(r'\s*<audio[^>]*></audio>', '', s)
open(f".silentbuild/index.html", "w", encoding="utf-8").write(s)
PY

# ---- 2. 渲染 silent 模式 ----
echo "==> render (silent)..."
( cd "$BUILD" && npx --yes hyperframes render --quality standard \
    --variables '{"mode":"silent"}' --output silent.mp4 2>&1 | tail -2 )
RAW="$BUILD/silent.mp4"
[ -f "$RAW" ] || RAW=$(find "$BUILD" -name 'silent*.mp4' | head -1)
if [[ ! -f "$RAW" ]]; then echo "❌ 渲染产物未找到"; exit 1; fi
cp "$RAW" "$OUTPUT"

# ---- 3. 蒙太奇 (7 段中点) ----
echo "==> 蒙太奇..."
mkdir -p preview/.frames && rm -f preview/.frames/*.png
i=1
for k in 0 1 2 3 4 5 6; do
  T=$(python3 -c "print(round($k * $SILENT_SEG + $SILENT_SEG / 2, 2))")
  $FFMPEG -y -loglevel error -ss "$T" -i "$OUTPUT" -frames:v 1 "preview/.frames/f-$i.png"
  i=$((i + 1))
done
$FFMPEG -y -loglevel error -framerate 1 -i "preview/.frames/f-%d.png" \
  -vf "scale=480:-1,tile=2x4:padding=12" -frames:v 1 -update 1 "preview/montage-silent.png"
rm -rf preview/.frames "$BUILD"

# ---- 4. 元信息 ----
echo ""
$FFPROBE -v error -show_entries format=duration,size -show_entries stream=width,height \
  -of default=noprint_wrappers=1 "$OUTPUT"
echo "✅ 无声循环 MP4: $OUTPUT ($(($(wc -c < "$OUTPUT")/1024))KB)"
echo "✅ 蒙太奇: preview/montage-silent.png"
