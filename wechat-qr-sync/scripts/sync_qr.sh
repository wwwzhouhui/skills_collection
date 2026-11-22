#!/usr/bin/env bash
# sync_qr.sh — 微信群二维码 URL 批量同步工具（scan / replace / push 三步）
# 依赖: bash, git, awk, sed, grep
#
# 用法:
#   sync_qr.sh scan    --new-url URL --list FILE                 扫描各项目 README 群二维码状态
#   sync_qr.sh replace --new-url URL --list FILE                 执行替换并自动复核
#   sync_qr.sh push    --list FILE [--message MSG] [--branch B]    逐仓库提交并推送 README.md
#
# 清单文件: 每行一个项目根目录，支持 /mnt/f/x（WSL）、/f/x（Git Bash）、F:\x（Windows），
# 行内多余列（表格 | 或 tab 分隔）自动忽略，空行跳过。
set -uo pipefail

AWK_PROG='
/^[ \t]*#+[ \t]*技术交流群/ { in_sec=1; next }
in_sec && /^[ \t]*#+[ \t]/ { in_sec=0 }
in_sec && !done && /^[ \t]*!\[[^]]*\]\(/ {
  line=$0
  sub(/^[^(]*\(/, "", line)
  sub(/\)[^)]*$/, "", line)
  print line
  done=1
  exit
}'

sanitize() { sed -E 's/gh[pousr]_[A-Za-z0-9]+/***/g'; }

usage() { grep '^#' "$0" | sed -n '2,12p' | sed 's/^# \{0,1\}//'; exit 2; }

normalize_dir() {
  local p="$1"
  p="${p//\\//}"          # 反斜杠先转正斜杠
  p="${p#\"}"; p="${p%\"}"
  while :; do
    case "$p" in
      ' '*|'	'*|'|'*|'['*) p="${p:1}" ;;
      *) break ;;
    esac
  done   # 剥离行首空白/表格竖线
  p="${p%%$'\t'*}"; p="${p%%|*}"; p="${p%% *}"               # 取第一列
  p="${p%/}"
  if [[ "$p" =~ ^([A-Za-z]):(.*)$ ]]; then
    local drv; drv=$(printf '%s' "${BASH_REMATCH[1]}" | tr 'A-Z' 'a-z')
    p="/${drv}${BASH_REMATCH[2]}"
  fi
  if [ -d /c ] && [ ! -d /mnt/c ]; then            # Git Bash
    case "$p" in /mnt/[a-z]/*|/mnt/[a-z]) p="${p#/mnt}" ;; esac
  elif [ -d /mnt/c ] && [ ! -d /c ]; then          # WSL
    if [[ "$p" =~ ^/([a-z])(/.*)?$ ]] && [ -d "/mnt/${BASH_REMATCH[1]}" ]; then
      p="/mnt$p"
    fi
  fi
  printf '%s' "$p"
}

validate_url() {
  local u="$1" host
  case "$u" in
    https://*|http://*) : ;;
    *) echo "错误: NEW_URL 必须以 http(s):// 开头: $u" >&2; return 1 ;;
  esac
  host=$(printf '%s' "$u" | sed -E 's#^https?://([^/:]+).*#\1#')
  case "$host" in
    localhost|127.*|10.*|192.168.*|169.254.*|0.0.0.0|::1|*.local)
      echo "错误: NEW_URL 指向内网/保留地址，拒绝执行: $host" >&2; return 1 ;;
  esac
  if [[ "$host" =~ ^172\.([0-9]+)\. ]]; then
    local o="${BASH_REMATCH[1]}"
    if [ "$o" -ge 16 ] 2>/dev/null && [ "$o" -le 31 ] 2>/dev/null; then
      echo "错误: NEW_URL 指向内网/保留地址，拒绝执行: $host" >&2; return 1
    fi
  fi
}

# load_list FILE -> 去重后的目录数组 REPOS
load_list() {
  local file="$1" line p
  REPOS=()
  while IFS= read -r line || [ -n "$line" ]; do
    line=$(printf '%s' "$line" | tr -d '\r')
    [ -z "${line// }" ] && continue
    case "$line" in '#'*|'---'*|':'*|'|'---*) continue ;; esac
    p=$(normalize_dir "$line")
    [ -z "$p" ] && continue
    REPOS+=("$p")
  done < "$file"
  # 去重
  if [ "${#REPOS[@]}" -gt 1 ]; then
    mapfile -t REPOS < <(printf '%s\n' "${REPOS[@]}" | awk '!seen[$0]++')
  fi
}

classify() {  # $1=readme $2=new_url -> "状态<TAB>路径[<TAB>旧URL]"
  local f="$1" new="$2" old
  old=$(awk "$AWK_PROG" "$f" 2>/dev/null)
  if [ -z "$old" ]; then
    printf 'NO-SEC\t%s\n' "$(dirname "$f")"
  elif [ "$old" = "$new" ]; then
    printf 'NEW-OK\t%s\t%s\n' "$(dirname "$f")" "$old"
  else
    printf 'HAS-OLD\t%s\t%s\n' "$(dirname "$f")" "$old"
  fi
}

cmd_scan() {
  local n_old=0 n_ok=0 n_sec=0 n_file=0 d f line
  echo "=== 扫描报告（共 ${#REPOS[@]} 个目录）==="
  for d in "${REPOS[@]}"; do
    f="$d/README.md"
    if [ ! -f "$f" ]; then
      printf 'NO-FILE\t%s\n' "$d"; n_file=$((n_file+1)); continue
    fi
    line=$(classify "$f" "$NEW_URL")
    case "$line" in
      HAS-OLD*) printf 'HAS-OLD\t%s\t旧URL: %s\n' "$d" "$(awk "$AWK_PROG" "$f")"; n_old=$((n_old+1)) ;;
      NEW-OK*)  printf 'NEW-OK\t%s\t已是最新\n' "$d"; n_ok=$((n_ok+1)) ;;
      *)        printf 'NO-SEC\t%s\tREADME 无"技术交流群"段落\n' "$d"; n_sec=$((n_sec+1)) ;;
    esac
  done
  echo "=== 汇总: 待更新 $n_old / 已最新 $n_ok / 无段落 $n_sec / 无README $n_file ==="
}

cmd_replace() {
  local n=0 d f old
  for d in "${REPOS[@]}"; do
    f="$d/README.md"
    [ -f "$f" ] || { echo "跳过(NO-FILE): $d"; continue; }
    old=$(awk "$AWK_PROG" "$f" 2>/dev/null)
    if [ -z "$old" ]; then echo "跳过(NO-SEC): $d"; continue; fi
    if [ "$old" = "$NEW_URL" ]; then echo "已是最新: $d"; continue; fi
    if sed -i "s|$old|$NEW_URL|g" "$f"; then
      echo "已替换: $d"
      echo "  旧: $old"; echo "  新: $NEW_URL"
      n=$((n+1))
    else
      echo "替换失败: $d"; FAILED_REPLACE+=("$d")
    fi
  done
  echo "=== 替换完成: $n 个文件，开始复核 ==="
  cmd_scan
  if [ "${#FAILED_REPLACE[@]}" -gt 0 ]; then exit 1; fi
}

cmd_push() {
  local n_ok=0 n_fail=0 n_skip=0 d branch cur out rc short
  echo "=== 逐仓库提交推送（仅 README.md）==="
  for d in "${REPOS[@]}"; do
    if [ ! -d "$d/.git" ] && ! git -C "$d" rev-parse --git-dir >/dev/null 2>&1; then
      echo "跳过(非git仓库): $d"; n_skip=$((n_skip+1)); continue
    fi
    branch="$PUSH_BRANCH"
    if [ -z "$branch" ]; then
      branch=$(git -C "$d" rev-parse --abbrev-ref HEAD 2>/dev/null)
    fi
    git -C "$d" add README.md 2>/dev/null
    if git -C "$d" diff --cached --quiet 2>/dev/null; then
      echo "跳过(无README改动): $d ($(basename "$d") @ $branch)"; n_skip=$((n_skip+1)); continue
    fi
    if ! git -C "$d" commit -m "$PUSH_MSG" >/dev/null 2>&1; then
      echo "✗ $(basename "$d"): 提交失败"; n_fail=$((n_fail+1)); continue
    fi
    short=$(git -C "$d" rev-parse --short HEAD 2>/dev/null)
    out=$(git -C "$d" push origin "$branch" 2>&1); rc=$?
    if [ $rc -eq 0 ]; then
      echo "✓ $(basename "$d") ($short @ $branch) 已推送"
      n_ok=$((n_ok+1))
    else
      echo "✗ $(basename "$d"): 提交成功($short)但推送失败 @ $branch"
      printf '%s\n' "$out" | sanitize | sed 's/^/    /'
      echo "    （本地提交已保留，可排查凭据后手动 git push）"
      n_fail=$((n_fail+1))
    fi
  done
  echo "=== 汇总: 推送成功 $n_ok / 失败 $n_fail / 跳过 $n_skip ==="
  [ $n_fail -gt 0 ] && exit 1
  exit 0
}

NEW_URL="" LIST_FILE="" PUSH_MSG="docs: 更新技术交流群微信群二维码为最新地址" PUSH_BRANCH=""
CMD="${1:-}"; [ $# -gt 0 ] && shift
FAILED_REPLACE=()

while [ $# -gt 0 ]; do
  case "$1" in
    --new-url) NEW_URL="$2"; shift 2 ;;
    --list)    LIST_FILE="$2"; shift 2 ;;
    --message) PUSH_MSG="$2"; shift 2 ;;
    --branch)  PUSH_BRANCH="$2"; shift 2 ;;
    *) echo "未知参数: $1" >&2; usage ;;
  esac
done

case "$CMD" in
  scan|replace|push) : ;;
  *) usage ;;
esac

if [ -z "$LIST_FILE" ]; then echo "错误: 缺少 --list 清单文件" >&2; exit 2; fi
if [ ! -f "$LIST_FILE" ]; then echo "错误: 清单文件不存在: $LIST_FILE" >&2; exit 2; fi
if [ "$CMD" != "push" ]; then
  [ -z "$NEW_URL" ] && { echo "错误: 缺少 --new-url" >&2; exit 2; }
  validate_url "$NEW_URL" || exit 2
fi

load_list "$LIST_FILE"
[ "${#REPOS[@]}" -eq 0 ] && { echo "错误: 清单中没有有效目录" >&2; exit 2; }

case "$CMD" in
  scan)    cmd_scan ;;
  replace) cmd_replace ;;
  push)    cmd_push ;;
esac
