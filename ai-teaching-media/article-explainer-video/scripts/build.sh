#!/usr/bin/env bash
# 文章解说视频渲染管线 (HyperFrames)
# 用法: ./build.sh <project_dir> [output.mp4] [--draft]
# 输出:
#   <project_dir>/renders/<name>.mp4
#   <project_dir>/preview/montage.png  (每章中点抽帧蒙太奇)

set -euo pipefail

FFMPEG=${FFMPEG:-ffmpeg}
FFPROBE=${FFPROBE:-ffprobe}

if [[ $# -lt 1 ]]; then
  echo "用法: $0 <project_dir> [output.mp4] [--draft]"
  exit 1
fi
PROJECT_DIR=$1
shift
OUTPUT=""
QUALITY="standard"
for arg in "$@"; do
  case "$arg" in
    --draft) QUALITY="draft" ;;
    *) OUTPUT="$arg" ;;
  esac
done

cd "$PROJECT_DIR"
NAME=$(basename "$(pwd)")
OUTPUT=${OUTPUT:-renders/${NAME}.mp4}
mkdir -p renders preview

echo "==> lint..."
npx --yes hyperframes lint

echo "==> validate..."
npx --yes hyperframes validate || echo "⚠ validate 有警告 (见上), 渲染继续 — 对比度问题请回去调色"

echo "==> render ($QUALITY)..."
npx --yes hyperframes render --quality "$QUALITY" --output "$OUTPUT"

if [[ ! -f "$OUTPUT" ]]; then
  echo "❌ 渲染产物未找到: $OUTPUT"
  exit 1
fi

# ---- 抽帧蒙太奇: 每章中点 (避开转场糊帧), 3 列网格 ----
echo "==> 蒙太奇..."
mkdir -p preview/.frames && rm -f preview/.frames/*.png
TIMES=$(python3 -c "
import json
d = json.load(open('audio/timeline.json'))
print(' '.join(f\"{c['start'] + c['duration'] / 2:.2f}\" for c in d['chapters']))")
N=$(echo "$TIMES" | wc -w | tr -d ' ')
ROWS=$(python3 -c "import math; print(math.ceil($N / 3))")
i=1
for T in $TIMES; do
  $FFMPEG -y -loglevel error -ss "$T" -i "$OUTPUT" -frames:v 1 "preview/.frames/f-$i.png"
  i=$((i + 1))
done
$FFMPEG -y -loglevel error -framerate 1 -i "preview/.frames/f-%d.png" \
  -vf "scale=480:-1,tile=3x${ROWS}:padding=12" -frames:v 1 -update 1 "preview/montage.png"
rm -rf preview/.frames

echo ""
echo "==> 输出:"
$FFPROBE -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUTPUT"
ls -lh "$OUTPUT" preview/montage.png
