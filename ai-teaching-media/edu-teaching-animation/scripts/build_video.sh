#!/usr/bin/env bash
# 教学视频渲染管线 (HyperFrames)
# 用法: ./build_video.sh <project_dir> [output.mp4] [--draft]
#   project_dir: 含 index.html + audio/ 的 HyperFrames 项目目录
#   output.mp4:  输出文件名 (默认 renders/<dirname>.mp4)
#   --draft:     快速草稿渲染 (迭代用)
# 输出:
#   <project_dir>/renders/<name>.mp4
#   <project_dir>/preview/montage.png  (7 场景抽帧蒙太奇, 与 GIF 管线一致)

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

# ---- 1. 静态检查 ----
echo "==> lint..."
npx --yes hyperframes lint

# ---- 2. 视觉审计 (WCAG 对比度等, 警告不阻断; 有警告要回去改色值) ----
echo "==> validate..."
npx --yes hyperframes validate || echo "⚠ validate 有警告 (见上), 渲染继续 — 对比度问题请回去调色"

# ---- 3. 渲染 ----
echo "==> render ($QUALITY)..."
npx --yes hyperframes render --quality "$QUALITY" --output "$OUTPUT"

if [[ ! -f "$OUTPUT" ]]; then
  echo "❌ 渲染产物未找到: $OUTPUT"
  exit 1
fi

# ---- 4. 抽帧蒙太奇: 优先按 durations.json 的场景中点 (避开转场糊帧), 无则七等分 ----
echo "==> 蒙太奇..."
mkdir -p preview/.frames && rm -f preview/.frames/*.png
if [[ -f audio/durations.json ]]; then
  TIMES=$(python3 -c "
import json
d = json.load(open('audio/durations.json'))
print(' '.join(f\"{s['start'] + s['duration'] / 2:.2f}\" for s in d['segments']))")
else
  DUR=$($FFPROBE -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT")
  TIMES=$(python3 -c "
d = float('$DUR')
print(' '.join(f'{d / 7 * (i + 0.5):.2f}' for i in range(7)))")
fi
i=1
for T in $TIMES; do
  $FFMPEG -y -loglevel error -ss "$T" -i "$OUTPUT" -frames:v 1 "preview/.frames/f-$i.png"
  i=$((i + 1))
done
$FFMPEG -y -loglevel error -framerate 1 -i "preview/.frames/f-%d.png" \
  -vf "scale=480:-1,tile=2x4:padding=12" -frames:v 1 -update 1 "preview/montage.png"
rm -rf preview/.frames

# ---- 5. 元信息 ----
echo ""
echo "==> 输出:"
$FFPROBE -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUTPUT"
ls -lh "$OUTPUT" preview/montage.png
