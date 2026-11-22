#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-qr-rotator 核心 CLI
=========================
把「换一张微信群二维码」这件事，变成一条命令流水线：

  upload        图片 → 图床公网 URL（PicList，兼作缓存击穿）
  replace-skill 更新 skill 源码（SKILL.md / README.md / templates/*.md）
  sync-runtime  覆盖安装到运行环境 skills 目录
  plan          把用户给的项目清单与 projects.json 比对，输出 新增/移出
  update-repos  批量替换 N 个仓库 README.md 里的群二维码
  push          精确提交并推送（只 add README.md，不碰无关改动）
  verify        全链路核对（skill 文件 + 仓库 + 远端 HEAD）
  rollback      用备份目录整批还原
  status        一眼看当前基准链接与清单规模

设计约束（都是踩过的坑，勿删）：
1. 只改「技术交流群」章节里的第一张图；其他二维码（微信/打赏）绝不动，
   改动前后用图片 URL 集合做护栏，多改一处就整文件回滚。
2. 文件编码按实际探测（utf-8 / utf-8-sig / utf-16），不假设。
3. 所有 git 操作用 `-c safe.directory=*` 绕过属主不一致的 dubious ownership。
4. 提交只 `git add -- README.md`，并校验本次提交只含该文件。
5. 每次写盘前备份，备份目录写 index.json 供 rollback 使用。

仅用标准库，Python 3.8+。
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

try:  # Windows 控制台默认 cp936，中文/箭头会炸，强制 utf-8
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = SKILL_ROOT / "config.json"
PROJECTS_PATH = SKILL_ROOT / "projects.json"
STATE_PATH = Path(tempfile.gettempdir()) / "qr-rotator" / "state.json"

# ---------------------------------------------------------------- 基础工具


def die(msg, code=1):
    print("\n[ERROR] " + msg, file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print("[WARN]  " + msg)


def info(msg):
    print(msg)


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as e:
        die(f"{path} 不是合法 JSON：{e}")


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config(args=None):
    cfg = load_json(CONFIG_PATH)
    if cfg is None:
        die(f"找不到配置文件：{CONFIG_PATH}")
    if args is not None:
        if getattr(args, "base_dir", None):
            cfg["base_dir"] = args.base_dir
        if getattr(args, "skill_source", None):
            cfg["skill_source"] = args.skill_source
        if getattr(args, "runtime_dir", None):
            cfg["runtime_skills_dir"] = args.runtime_dir
    return cfg


def load_manifest():
    m = load_json(PROJECTS_PATH)
    if m is None:
        die(f"找不到项目清单：{PROJECTS_PATH}")
    m.setdefault("active", [])
    m.setdefault("excluded", [])
    m.setdefault("rounds", [])
    return m


def save_manifest(m):
    m["updated_at"] = datetime.date.today().isoformat()
    save_json(PROJECTS_PATH, m)


def load_state():
    return load_json(STATE_PATH, {}) or {}


def save_state(patch):
    st = load_state()
    st.update(patch)
    save_json(STATE_PATH, st)


def now_tag():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------- 编码读写


def read_text(path):
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "utf-8-sig", raw
    for enc in ("utf-8", "utf-16"):
        try:
            return raw.decode(enc), enc, raw
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法识别编码：{path}（NUL 字节 {raw.count(chr(0).encode())} 个）")


def write_text(path, text, enc):
    data = text.encode("utf-8") if enc == "utf-8-sig" else text.encode(enc)
    if enc == "utf-8-sig":
        data = b"\xef\xbb\xbf" + data
    Path(path).write_bytes(data)


# ---------------------------------------------------------------- 二维码定位

HEAD_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+\S", re.M)
MD_IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)")
HTML_IMG_RE = re.compile(r"<img\b[^>]*?\bsrc=[\"'](?P<url>[^\"']+)[\"']", re.I)
ALT_FILENAME_RE = re.compile(
    r"^(?:image-\d+|[\da-f]{8}-[\da-f-]{16,}|[\w.\-]+\.(?:png|jpe?g|gif|webp))$", re.I
)


def all_image_urls(text):
    urls = [m.group("url") for m in MD_IMG_RE.finditer(text)]
    urls += [m.group("url") for m in HTML_IMG_RE.finditer(text)]
    return urls


def find_section(text, keyword):
    """返回 (start, end)：keyword 所在标题之后到下一个标题之前的区间。"""
    head = re.compile(r"^[ \t]{0,3}#{1,6}[^\n]*" + re.escape(keyword) + r"[^\n]*$", re.M)
    m = head.search(text)
    if m:
        start = m.end()
    else:  # 没有独立标题，就退化成正文里的关键词
        idx = text.find(keyword)
        if idx < 0:
            return None
        start = idx + len(keyword)
    nxt = HEAD_RE.search(text, start)
    end = nxt.start() if nxt else len(text)
    if end <= start:
        return None
    return start, end


def find_first_image(text, start, end):
    seg = text[start:end]
    cands = []
    m = MD_IMG_RE.search(seg)
    if m:
        cands.append(
            {
                "kind": "md",
                "url": m.group("url"),
                "alt": m.group("alt"),
                "url_span": (start + m.start("url"), start + m.end("url")),
                "alt_span": (start + m.start("alt"), start + m.end("alt")),
            }
        )
    m = HTML_IMG_RE.search(seg)
    if m:
        cands.append(
            {
                "kind": "html",
                "url": m.group("url"),
                "alt": "",
                "url_span": (start + m.start("url"), start + m.end("url")),
                "alt_span": None,
            }
        )
    if not cands:
        return None
    return sorted(cands, key=lambda c: c["url_span"][0])[0]


def replace_span(text, span, new):
    return text[: span[0]] + new + text[span[1] :]


def url_stem(url):
    name = url.split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    return name.rsplit(".", 1)[0] if "." in name else name


def rotate_text(text, keyword, new_url):
    """把 keyword 章节里的第一张二维码换成 new_url。返回 (新文本, info)。"""
    sec = find_section(text, keyword)
    if not sec:
        return text, {"status": "NO_SECTION"}
    img = find_first_image(text, *sec)
    if not img:
        return text, {"status": "NO_IMAGE"}

    old_url = img["url"]
    if old_url == new_url:
        return text, {"status": "ALREADY", "old_url": old_url, "count": 0}

    before = set(all_image_urls(text))
    new_stem = url_stem(new_url)

    # 1) alt 若是「文件名式」，跟着换；语义化 alt（技术交流群/微信群二维码）保留原样
    cur = text
    delta = 0
    alt_updated = False
    alt = (img.get("alt") or "").strip()
    if img["kind"] == "md" and img["alt_span"] and alt and ALT_FILENAME_RE.match(alt) and alt != new_stem:
        cur = replace_span(cur, img["alt_span"], new_stem)
        delta = len(new_stem) - len(alt)
        alt_updated = True

    # 2) 换 URL（前面 alt 变长/变短会让 URL 位置平移 delta）
    us, ue = img["url_span"]
    cur = cur[: us + delta] + new_url + cur[ue + delta :]

    # 3) 护栏：除这一张二维码外，不允许有任何图片链接变化
    after = set(all_image_urls(cur))
    if (before - after) != {old_url} or (after - before) != {new_url}:
        return text, {
            "status": "GUARD_FAILED",
            "removed": sorted(before - after),
            "added": sorted(after - before),
        }

    other = text.count(old_url) - 1  # 章节外是否还有同一张旧图（本工具不改它们）
    return cur, {
        "status": "ROTATED",
        "old_url": old_url,
        "count": 1,
        "other_occurrences": max(other, 0),
        "alt_updated": alt_updated,
    }


def exact_replace(text, old_url, new_url):
    """退路：章节识别失败时，按旧 URL 精确替换（仍然只换这一张图）。"""
    if old_url == new_url or not old_url or old_url not in text:
        return text, {"status": "NO_MATCH", "count": 0}
    before = set(all_image_urls(text))
    cnt = text.count(old_url)
    cur = text.replace(old_url, new_url)
    after = set(all_image_urls(cur))
    if (before - after) != {old_url} or (after - before) != {new_url}:
        return text, {"status": "GUARD_FAILED"}
    return cur, {"status": "ROTATED_EXACT", "old_url": old_url, "count": cnt}


# ---------------------------------------------------------------- 备份


class Backup:
    def __init__(self, root=None):
        cfg = load_json(CONFIG_PATH) or {}
        base = root or cfg.get("backup_root") or str(Path(tempfile.gettempdir()) / "qr-rotator")
        self.dir = Path(base) / ("backup-" + now_tag())
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index = []

    def add(self, path):
        src = Path(path)
        if not src.is_file():
            return
        rel = src.name + "." + hashlib.sha1(str(src).encode()).hexdigest()[:8]
        sub = self.dir / rel
        sub.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, sub / src.name)
        self.index.append({"origin": str(src), "backup": str((sub / src.name).relative_to(self.dir)).replace("\\", "/")})

    def close(self):
        if self.index:
            save_json(self.dir / "index.json", self.index)
        return self.dir


# ---------------------------------------------------------------- git


def git(repo, *args, timeout=180, check=False):
    cmd = ["git", "-c", "safe.directory=*", "-C", str(repo)] + [str(a) for a in args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "timeout")
    if check and p.returncode != 0:
        raise RuntimeError(f"git {' '.join(map(str, args))} 失败：{p.stderr.strip()[:300]}")
    return p


def is_git_repo(path):
    p = git(path, "rev-parse", "--is-inside-work-tree")
    return p.returncode == 0 and p.stdout.strip() == "true"


def repo_toplevel(path):
    p = git(path, "rev-parse", "--show-toplevel")
    return p.stdout.strip() if p.returncode == 0 else None


def remote_owner(repo):
    p = git(repo, "remote", "get-url", "origin")
    url = p.stdout.strip()
    if not url:
        return None
    m = re.search(r"github\.com[/:]([^/]+)/", url)
    return m.group(1) if m else None


def commit_identity(repo):
    n = git(repo, "config", "user.name").stdout.strip()
    e = git(repo, "config", "user.email").stdout.strip()
    if n and e:
        return n, e, "仓库既有配置"
    owner = remote_owner(repo) or "unknown"
    return owner, f"{owner}@users.noreply.github.com", "按 remote 归属临时指定"


# ---------------------------------------------------------------- paths


def norm_dir(s, base_dir):
    s = s.strip().strip("\"'`").replace("\\", "/").rstrip("/")
    m = re.match(r"^/mnt/([A-Za-z])/(.*)$", s)
    if m:
        s = f"{m.group(1).upper()}:/{m.group(2)}"
    b = base_dir.replace("\\", "/").rstrip("/")
    if re.match(r"^[A-Za-z]:/", s) and s.lower().startswith(b.lower() + "/"):
        s = s[len(b) + 1 :]
    return s


def repo_path(cfg, d):
    p = Path(d)
    return p if p.is_absolute() else Path(cfg["base_dir"]) / d


def extract_dirs(text, base_dir):
    """从任意粘贴内容（markdown 表格 / 纯路径列表）里抠出目录。"""
    pat = re.compile(r"(?:/mnt/[A-Za-z]/[^\s|`'\"]+|[A-Za-z]:/[^\s|`'\"]+)")
    seen, out = set(), []
    for m in pat.finditer(text):
        d = norm_dir(m.group(0).rstrip(".,;)，。）"), base_dir)
        if d and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def split_dirs(s, base_dir):
    """--dirs 支持逗号 / 分号 / 换行分隔。"""
    parts = [x for x in re.split(r"[,;\n]+", s or "") if x.strip()]
    return [norm_dir(x, base_dir) for x in parts]


def resolve_targets(cfg, args, manifest):
    """按 policy 算出本轮要处理的仓库列表。"""
    policy = getattr(args, "policy", None) or "keep"
    provided = []
    if getattr(args, "dirs", None):
        provided = split_dirs(args.dirs, cfg["base_dir"])
    elif getattr(args, "list", None):
        provided = extract_dirs(Path(args.list).read_text(encoding="utf-8", errors="replace"), cfg["base_dir"])

    active = list(manifest["active"])
    if policy == "keep":
        return active, {}, provided
    if not provided:
        die("policy 为 merge/new-only/replace 时必须提供 --list 或 --dirs")
    same = [d for d in provided if d in active]
    added = [d for d in provided if d not in active]
    removed = [d for d in active if d not in provided]
    if policy == "merge":
        return active + added, {"same": same, "added": added, "removed": removed}, provided
    if policy == "new-only":
        return added, {"same": same, "added": added, "removed": removed}, provided
    if policy == "replace":
        return provided, {"same": same, "added": added, "removed": removed}, provided
    die(f"未知 policy：{policy}")


# ---------------------------------------------------------------- upload


IMG_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"GIF8": "gif",
}


def sniff_image(data):
    for magic, ext in IMG_MAGIC.items():
        if data.startswith(magic):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def http_status(url, timeout=20, method="HEAD"):
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.headers.get("Content-Type", ""), r.headers.get("Content-Length", "")
    except urllib.error.HTTPError as e:
        return e.code, "", ""
    except Exception as e:
        return None, str(e)[:120], ""


def cmd_upload(args):
    cfg = load_config(args)
    src = Path(args.image)
    if not src.is_file():
        die(f"图片不存在：{src}")
    data = src.read_bytes()
    ext = sniff_image(data)
    if not ext:
        die("这不像一张图片（magic bytes 不匹配 png/jpg/gif/webp）")
    if len(data) < 8 * 1024:
        warn(f"图片只有 {len(data)} 字节，可能是缩略图，二维码恐难扫描")
    sha = hashlib.sha256(data).hexdigest()[:16]

    up_dir = Path(tempfile.mkdtemp(prefix="qr-upload-"))
    if cfg["upload"].get("unique_filename", True) and not args.keep_filename:
        # 唯一文件名 = 新 URL，避免 CDN / GitHub camo 缓存旧图
        name = f"qr-{now_tag()}-{os.urandom(3).hex()}.{ext}"
        up = up_dir / name
        shutil.copy2(src, up)
    else:
        up = src

    api = cfg["upload"]["api"]
    payload = json.dumps({"list": [str(up).replace("/", "\\")]}).encode("utf-8")
    info(f"上传中：{up.name}  （{len(data)} 字节，sha256:…{sha}）")
    try:
        req = urllib.request.Request(api, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=cfg["upload"].get("timeout", 90)) as r:
            resp = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        die(f"上传失败：{type(e).__name__} {e}\n"
            f"  检查 PicList 是否运行：curl {api.replace('/upload','/heartbeat')}")

    if not resp.get("success") or not resp.get("result"):
        die(f"图床返回失败：{json.dumps(resp, ensure_ascii=False)[:400]}")
    url = resp["result"][0]

    st, ctype, clen = http_status(url)
    if st not in (200, 206):
        warn(f"上传成功但 URL 回访异常：HTTP {st} {ctype}")

    # 记下当前基准（供 update-repos 当 from_url 用）
    skill_md = Path(cfg["skill_source"]) / "SKILL.md"
    from_url = None
    if skill_md.is_file():
        txt, _, _ = read_text(skill_md)
        sec = find_section(txt, cfg.get("qr_section_keyword", "技术交流群"))
        if sec:
            img = find_first_image(txt, *sec)
            from_url = img["url"] if img else None

    save_state({"last_upload": {"url": url, "source": str(src), "sha256": sha,
                                "at": datetime.datetime.now().isoformat(timespec="seconds")},
                "from_url": from_url, "to_url": url})

    print("\n=== 上传成功 ===")
    print(f"  新链接 : {url}")
    print(f"  回访   : HTTP {st}  {ctype}  {clen} bytes")
    print(f"  原链接 : {from_url or '（未取到）'}")
    if from_url == url:
        warn("新旧链接相同！说明文件名重复覆盖，请加 --keep-filename 之外的唯一命名，或换图重传")
    print(f"\n-> 下一步：python scripts/qr_rotator.py replace-skill --url \"{url}\"")
    return url


# ---------------------------------------------------------------- skill 文件


def expand_files(cfg):
    out = []
    for pat in cfg.get("skill_files", ["SKILL.md", "README.md", "templates/*.md"]):
        p = Path(cfg["skill_source"]) / pat
        if any(ch in pat for ch in "*?["):
            out += sorted(Path(cfg["skill_source"]).glob(pat))
        elif p.is_file():
            out.append(p)
    return [p for p in out if p.suffix.lower() == ".md"]


def current_skill_url(cfg):
    skill_md = Path(cfg["skill_source"]) / "SKILL.md"
    if not skill_md.is_file():
        return None
    txt, _, _ = read_text(skill_md)
    sec = find_section(txt, cfg.get("qr_section_keyword", "技术交流群"))
    if not sec:
        return None
    img = find_first_image(txt, *sec)
    return img["url"] if img else None


def cmd_replace_skill(args):
    cfg = load_config(args)
    kw = cfg.get("qr_section_keyword", "技术交流群")
    new_url = args.url or (load_state().get("last_upload") or {}).get("url")
    if not new_url:
        die("没有新链接：先跑 upload，或显式传 --url")

    # SKILL.md 可能已被手工改成新图（常见路径），此时旧链接要显式给或从其它文件推断。
    # 不在此处直接返回：还要检查 templates / README 是否落后。
    old_url = getattr(args, "from_url", None) or current_skill_url(cfg)
    if old_url == new_url:
        info("SKILL.md 已是目标链接，改为逐文件检查 templates / README 是否落后…")
        old_url = ""
    info(f"基准旧链接：{old_url or '（SKILL.md 已是最新，按文件逐个判断）'}")
    info(f"目标新链接：{new_url}\n")

    targets = expand_files(cfg)
    if not targets:
        die(f"在 {cfg['skill_source']} 下没找到任何可改的 md 文件")

    bk = Backup(args.backup_dir)
    rows, changed = [], 0
    for f in targets:
        rel = f.relative_to(cfg["skill_source"])
        try:
            txt, enc, _ = read_text(f)
        except ValueError as e:
            rows.append((str(rel), "DECODE_FAIL", str(e)[:50]))
            continue
        new_txt, meta = rotate_text(txt, kw, new_url)
        if meta["status"] == "ROTATED":
            bk.add(f)
            write_text(f, new_txt, enc)
            chk, _, _ = read_text(f)
            ok = new_url in chk
            rows.append((str(rel), "ROTATED" if ok else "VERIFY_FAIL",
                         f"alt{'已' if meta.get('alt_updated') else '未'}改"))
            changed += 1
        elif meta["status"] == "ALREADY":
            rows.append((str(rel), "ALREADY", ""))
        else:
            rows.append((str(rel), meta["status"], str(meta)[:60]))

    bdir = bk.close()
    print("=== skill 源码替换 ===")
    print(f"{'文件':<34}{'状态':<14}备注")
    print("-" * 70)
    for rel, st, note in rows:
        print(f"{rel:<34}{st:<14}{note}")
    print("-" * 70)
    print(f"共 {len(rows)} 个文件，改写 {changed} 个")
    if changed:
        print(f"备份：{bdir}")
        save_state({"last_backup": str(bdir)})
        print(f"\n-> 下一步：python scripts/qr_rotator.py sync-runtime")


def cmd_sync_runtime(args):
    cfg = load_config(args)
    src_root = Path(cfg["skill_source"])
    dst_root = Path(cfg["runtime_skills_dir"]) / cfg["runtime_skill_name"]
    fresh = not dst_root.exists()
    dst_root.mkdir(parents=True, exist_ok=True)

    rows, bad = [], 0
    skip = set(cfg.get("install_exclude", [])) | {"logs", "__pycache__"}
    if fresh:
        info(f"运行环境无此 skill，执行完整安装 → {dst_root}")
        for item in src_root.iterdir():
            if item.name.startswith(".") or item.name in skip:
                continue
            tgt = dst_root / item.name
            if item.is_dir():
                shutil.copytree(item, tgt, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns(".mimosa", "__pycache__", ".ipynb_checkpoints"))
            else:
                shutil.copy2(item, tgt)
            rows.append((item.name, "COPIED", ""))
    else:
        info(f"覆盖同步 → {dst_root}")
        for f in expand_files(cfg):
            rel = f.relative_to(src_root)
            tgt = dst_root / rel
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, tgt)
            same = tgt.read_bytes() == f.read_bytes()
            rows.append((str(rel), "SYNCED" if same else "MISMATCH", ""))
            if not same:
                bad += 1

    print("\n=== 运行环境同步 ===")
    for rel, st, note in rows:
        print(f"  {rel:<40}{st}")
    print(f"共 {len(rows)} 项，异常 {bad} 项")
    if not bad:
        print("\n-> 下一步：python scripts/qr_rotator.py update-repos --url \"%s\""
              % (args.url or (load_state().get("last_upload") or {}).get("url", "<URL>")))
    return bad


# ---------------------------------------------------------------- plan


def cmd_plan(args):
    cfg = load_config(args)
    m = load_manifest()
    if args.dirs:
        provided = split_dirs(args.dirs, cfg["base_dir"])
    elif args.list:
        provided = extract_dirs(Path(args.list).read_text(encoding="utf-8", errors="replace"),
                                cfg["base_dir"])
    else:
        die("需要 --list <清单文件> 或 --dirs \"a,b,c\"")
    if not provided:
        die("没能从输入里解析出任何目录路径")

    active = list(m["active"])
    excluded = {e["dir"]: e.get("reason", "") for e in m["excluded"]}
    same = [d for d in provided if d in active]
    added = [d for d in provided if d not in active and d not in excluded]
    hit_excluded = [d for d in provided if d in excluded]
    removed = [d for d in active if d not in provided]

    print("=== 清单比对 ===")
    print(f"  清单条目 : {len(provided)}")
    print(f"  存量一致 : {len(same)}")
    print(f"  新增     : {len(added)}")
    print(f"  移出     : {len(removed)}")
    print(f"  命中排除 : {len(hit_excluded)}")
    if added:
        print("\n  新增目录：")
        for d in added:
            print("    + " + d)
    if removed:
        print("\n  本次清单里没有（原有但未出现）：")
        for d in removed:
            print("    - " + d)
    if hit_excluded:
        print("\n  已在排除名单（无二维码可换，不会处理）：")
        for d in hit_excluded:
            print("    ! " + d + "  ← " + excluded[d][:60])

    verdict = "SAME" if not added and not removed else "CHANGED"
    print(f"\nVERDICT={verdict}")
    print(json.dumps({"same": len(same), "added": added, "removed": removed,
                      "excluded": hit_excluded, "verdict": verdict}, ensure_ascii=False))
    if verdict == "CHANGED":
        print("\n[必须询问用户] 清单与 projects.json 不一致，按下面四选一后再继续：")
        print("  1 merge    原有 + 新增（推荐）      -> update-repos --policy merge --update-manifest")
        print("  2 keep     只处理原有，忽略新增      -> update-repos --policy keep")
        print("  3 new-only 只处理新增                -> update-repos --policy new-only --list <清单>")
        print("  4 replace  完全按新清单（移出项不再更新）-> update-repos --policy replace --list <清单> --update-manifest")
    return verdict


# ---------------------------------------------------------------- repos


def cmd_update_repos(args):
    cfg = load_config(args)
    kw = cfg.get("qr_section_keyword", "技术交流群")
    m = load_manifest()
    new_url = args.url or (load_state().get("last_upload") or {}).get("url")
    if not new_url:
        die("没有新链接：先跑 upload，或显式传 --url")
    if new_url != current_skill_url(cfg):
        warn("新链接与 SKILL.md 当前链接不一致（你是不是漏了 replace-skill / sync-runtime？）")

    old_url = args.from_url or load_state().get("from_url")
    targets, diff, _ = resolve_targets(cfg, args, m)
    if diff:
        print(f"策略 {args.policy}：原有 {len(m['active'])} + 新增 {len(diff['added'])} "
              f"- 移出 {len(diff['removed'])} → 实际处理 {len(targets)}")

    bk = Backup(args.backup_dir)
    rows, stat = [], {}
    for d in targets:
        rp = repo_path(cfg, d)
        name = rp.name
        readme = rp / "README.md"
        if not rp.is_dir():
            rows.append((d, "MISSING", "")); stat["MISSING"] = stat.get("MISSING", 0) + 1; continue
        if not readme.is_file():
            rows.append((d, "NO_README", "")); stat["NO_README"] = stat.get("NO_README", 0) + 1; continue
        try:
            txt, enc, raw = read_text(readme)
        except ValueError as e:
            rows.append((d, "DECODE_FAIL", str(e)[:40])); stat["DECODE_FAIL"] = stat.get("DECODE_FAIL", 0) + 1; continue

        if args.dry_run:
            sec = find_section(txt, kw)
            img = find_first_image(txt, *sec) if sec else None
            st = "WOULD_ALREADY" if img and img["url"] == new_url else ("WOULD_ROTATE" if img else "WOULD_NO_QR")
            rows.append((d, st, img["url"].split("/")[-1] if img else ""))
            stat[st] = stat.get(st, 0) + 1
            continue

        new_txt, meta = rotate_text(txt, kw, new_url)
        if meta["status"] == "NO_SECTION" and old_url:
            new_txt, meta = exact_replace(txt, old_url, new_url)
            if meta["status"] == "ROTATED_EXACT":
                meta["status"] = "ROTATED_EXACT"

        st = meta["status"]
        if st in ("ROTATED", "ROTATED_EXACT"):
            bk.add(readme)
            write_text(readme, new_txt, enc)
            chk, _, _ = read_text(readme)
            if new_url not in chk:
                rows.append((d, "VERIFY_FAIL", "")); stat["VERIFY_FAIL"] = stat.get("VERIFY_FAIL", 0) + 1; continue
            note = ""
            if meta.get("other_occurrences"):
                note = f"章节外还有 {meta['other_occurrences']} 处旧图（未改）"
            rows.append((d, st, note))
        else:
            rows.append((d, st, ""))
        stat[st] = stat.get(st, 0) + 1

    bdir = bk.close() if bk.index else None
    print("\n=== 仓库 README 替换 ===")
    print(f"{'仓库目录':<56}{'状态':<16}备注")
    print("-" * 100)
    for d, st, note in rows:
        print(f"{d:<56}{st:<16}{note}")
    print("-" * 100)
    print("汇总：" + "  ".join(f"{k}={v}" for k, v in sorted(stat.items())))
    legend = {"ROTATED": "章节内二维码已换", "ROTATED_EXACT": "按旧链接精确替换",
              "ALREADY": "已是新图，跳过", "NO_SECTION": "无「技术交流群」章节",
              "NO_IMAGE": "章节内无图片", "NO_README": "无 README.md",
              "MISSING": "目录不存在", "DECODE_FAIL": "编码无法识别（疑似损坏）",
              "NO_MATCH": "章节与旧链接都没命中",
              "WOULD_ROTATE": "预演：将被替换", "WOULD_ALREADY": "预演：已是新图",
              "WOULD_NO_QR": "预演：无二维码可换"}
    for k, v in legend.items():
        if k in stat:
            print(f"  {k:<16}{v}")

    if bdir:
        print(f"\n备份：{bdir}")
        save_state({"last_backup": str(bdir)})

    if args.update_manifest and not args.dry_run:
        if args.policy in ("merge", "new-only", "replace"):
            m["active"] = targets
            save_manifest(m)
            info(f"\n已更新 projects.json：active = {len(m['active'])} 个")
        elif added_dirs := diff.get("added"):
            m["active"] = list(dict.fromkeys(m["active"] + added_dirs))
            save_manifest(m)
            info(f"\n已把 {len(added_dirs)} 个新增目录并入 projects.json")

    done = stat.get("ROTATED", 0) + stat.get("ROTATED_EXACT", 0)
    if args.dry_run:
        would = stat.get("WOULD_ROTATE", 0)
        print(f"\n预演：将改写 {would} 个仓库（未执行，加 --dry-run 去掉即可真跑）")
    else:
        print(f"\n实际改写 {done} 个仓库")
        if done:
            print("-> 下一步：python scripts/qr_rotator.py push")


# ---------------------------------------------------------------- push


def build_push_plan(cfg, args, m):
    """生成 [(仓库根, [相对路径...])]，同一仓库只出现一次。"""
    kw = cfg.get("qr_section_keyword", "技术交流群")
    targets, _, _ = resolve_targets(cfg, args, m)
    plan, order = {}, []
    for d in targets:
        rp = repo_path(cfg, d)
        if not (rp / "README.md").is_file():
            continue
        top = repo_toplevel(rp)
        if not top:
            continue
        rel = str((rp / "README.md").relative_to(Path(top))).replace("\\", "/")
        if top not in plan:
            plan[top] = []; order.append(top)
        plan[top].append(rel)

    if args.include_skill:
        sroot = Path(cfg["skill_source"])
        top = repo_toplevel(sroot)
        if top:
            if top not in plan:
                plan[top] = []; order.append(top)
            for f in expand_files(cfg):
                rel = str(f.relative_to(Path(top))).replace("\\", "/")
                if rel not in plan[top]:
                    plan[top].append(rel)
        else:
            warn("skill 源码不在 git 仓库内，--include-skill 已忽略")
    return [(t, plan[t]) for t in order]


def cmd_push(args):
    cfg = load_config(args)
    m = load_manifest()
    msg = args.message or cfg["git"]["commit_message"]
    plan = build_push_plan(cfg, args, m)
    if not plan:
        die("没有可推送的目标")

    rows, ok, fail = [], 0, 0
    for top, rels in plan:
        name = Path(top).name
        status = git(top, "status", "--porcelain", "--", *rels).stdout.strip()
        if not status:
            rows.append((name, "CLEAN", "", "")); continue
        if args.dry_run:
            rows.append((name, "WOULD_PUSH", str(len(rels)) + " 个文件", "")); continue

        git(top, "add", "--", *rels)
        staged = [x for x in git(top, "diff", "--cached", "--name-only").stdout.splitlines() if x.strip()]
        extra = [x for x in staged if x not in rels]
        if extra:
            git(top, "reset", "--quiet", "--", *extra)
            staged = [x for x in staged if x in rels]
            warn(f"{name}: 暂存区混入无关文件已剔除 → {extra[:3]}")
        if not staged:
            rows.append((name, "NOTHING", "", "")); continue

        un, ue, how = commit_identity(top)
        c = subprocess.run(["git", "-c", "safe.directory=*", "-C", top,
                            "-c", f"user.name={un}", "-c", f"user.email={ue}",
                            "commit", "-m", msg, "--quiet"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if c.returncode != 0:
            rows.append((name, "COMMIT_FAIL", c.stderr.strip()[:40], "")); fail += 1; continue
        head = git(top, "rev-parse", "--short", "HEAD").stdout.strip()

        pushed, perr = False, ""
        for attempt in range(1, cfg["git"].get("push_retry", 2) + 1):
            p = git(top, "push", "origin", "HEAD", timeout=300)
            if p.returncode == 0:
                pushed = True
                break
            perr = (p.stderr or p.stdout).strip().splitlines()
            perr = perr[-1][:60] if perr else ""
            if attempt < cfg["git"].get("push_retry", 2):
                time.sleep(3)
        if pushed:
            rows.append((name, "PUSHED", head, how)); ok += 1
        else:
            rows.append((name, "PUSH_FAIL", perr, "")); fail += 1

    print("\n=== 提交推送 ===")
    print(f"{'仓库':<34}{'状态':<13}{'commit':<10}身份")
    print("-" * 84)
    for n, st, h, how in rows:
        print(f"{n:<34}{st:<13}{h:<10}{how}")
    print("-" * 84)
    if args.dry_run:
        would = sum(1 for r in rows if r[1] == "WOULD_PUSH")
        print(f"预演：将推送 {would} 个仓库（未执行）")
    else:
        print(f"推送成功 {ok} 个，失败 {fail} 个")

    if ok and not args.dry_run and not args.no_record:
        to_url = current_skill_url(cfg)
        m["rounds"].append({"date": datetime.date.today().isoformat(),
                            "from": load_state().get("from_url"),
                            "to": to_url, "repos": ok, "pushed": ok})
        save_manifest(m)
        info("已把本轮记录写入 projects.json → rounds")
    if fail:
        sys.exit(1)


# ---------------------------------------------------------------- verify


def cmd_verify(args):
    cfg = load_config(args)
    kw = cfg.get("qr_section_keyword", "技术交流群")
    m = load_manifest()
    expected = args.url or current_skill_url(cfg)
    if not expected:
        die("取不到基准链接")
    print(f"基准链接：{expected}\n")

    bad = 0
    print("=== skill 源码 ===")
    print(f"{'文件':<34}{'状态':<14}当前图")
    print("-" * 78)
    for f in expand_files(cfg):
        rel = f.relative_to(cfg["skill_source"])
        txt, _, _ = read_text(f)
        sec = find_section(txt, kw)
        img = find_first_image(txt, *sec) if sec else None
        cur = img["url"] if img else ""
        okf = cur == expected
        bad += 0 if okf else 1
        print(f"{str(rel):<34}{'OK' if okf else 'DRIFT':<14}{cur.split('/')[-1] or '-'}")
    print("-" * 78)

    print("\n=== 运行环境副本 ===")
    rt = Path(cfg["runtime_skills_dir"]) / cfg["runtime_skill_name"]
    if rt.is_dir():
        rt_bad = 0
        for f in expand_files(cfg):
            rel = f.relative_to(cfg["skill_source"])
            tgt = rt / rel
            if not tgt.is_file():
                print(f"  {str(rel):<40}MISSING"); rt_bad += 1; continue
            same = tgt.read_bytes() == f.read_bytes()
            if not same:
                print(f"  {str(rel):<40}DIFF"); rt_bad += 1
        print(f"  → {'与源码一致' if not rt_bad else str(rt_bad) + ' 个文件不一致'}")
        bad += rt_bad
    else:
        print(f"  {rt} 不存在"); bad += 1

    print("\n=== 仓库 README ===")
    print(f"{'仓库目录':<56}{'状态':<12}说明")
    print("-" * 96)
    for d in m["active"]:
        rp = repo_path(cfg, d)
        readme = rp / "README.md"
        if not readme.is_file():
            print(f"{d:<52}{'NO_README':<12}"); bad += 1; continue
        txt, _, _ = read_text(readme)
        sec = find_section(txt, kw)
        img = find_first_image(txt, *sec) if sec else None
        cur = img["url"] if img else ""
        if cur == expected:
            st, note = "OK", ""
        elif not cur:
            st, note = "NO_QR", "无二维码"
        else:
            st, note = "DRIFT", cur.split("/")[-1]
        if st != "OK":
            bad += 1
        dirty = git(rp, "status", "--porcelain", "README.md").stdout.strip()
        if dirty:
            note = (note + " 未提交").strip()
            bad += 1
        print(f"{d:<56}{st:<12}{note}")
    print("-" * 96)

    if args.check_remote:
        print("\n=== 远端 HEAD（较慢）===")
        for d in m["active"][: args.remote_limit]:
            rp = repo_path(cfg, d)
            l = git(rp, "rev-parse", "HEAD").stdout.strip()
            r = git(rp, "ls-remote", "origin", "refs/heads/main", timeout=90).stdout.split()
            r = r[0] if r else ""
            same = l == r
            bad += 0 if same else 1
            print(f"  {d:<50}{'SAME' if same else 'DIFF'}  {l[:7]}")

    print(f"\n{'全部通过 ✓' if not bad else '存在 %d 项问题 ✗' % bad}")
    sys.exit(0 if not bad else 1)


# ---------------------------------------------------------------- rollback / status


def cmd_rollback(args):
    bdir = Path(args.backup)
    idx = bdir / "index.json"
    if not idx.is_file():
        die(f"备份目录缺少 index.json：{bdir}")
    items = load_json(idx)
    n = 0
    for it in items:
        src = bdir / it["backup"]
        dst = Path(it["origin"])
        if not src.is_file():
            warn(f"备份缺失：{src}"); continue
        shutil.copy2(src, dst)
        n += 1
        print(f"  还原 {dst}")
    print(f"\n共还原 {n} 个文件")


def cmd_status(args):
    cfg = load_config(args)
    m = load_manifest()
    print("=== wechat-qr-rotator 状态 ===")
    print(f"  skill 源码 : {cfg['skill_source']}")
    print(f"  运行环境   : {Path(cfg['runtime_skills_dir']) / cfg['runtime_skill_name']}")
    print(f"  仓库清单   : {len(m['active'])} 个在册 / {len(m['excluded'])} 个排除")
    hb = http_status(cfg["upload"]["api"].replace("/upload", "/heartbeat"), method="GET")[0]
    print(f"  图床接口   : {cfg['upload']['api']}  " + ("在线" if hb == 200 else f"不可用(HTTP {hb})"))
    cur = current_skill_url(cfg)
    print(f"  当前群二维码: {cur}")
    if m.get("rounds"):
        last = m["rounds"][-1]
        print(f"  最近一轮   : {last.get('date')}  {last.get('repos')} 个仓库 → {str(last.get('to')).split('/')[-1]}")
    st = load_state()
    if st.get("last_backup"):
        print(f"  最近备份   : {st['last_backup']}")


# ---------------------------------------------------------------- CLI


def main():
    ap = argparse.ArgumentParser(prog="qr_rotator", description="微信群二维码批量轮换工具")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--base-dir", help="仓库根目录（默认取 config.json）")
    common.add_argument("--skill-source", help="github-readme-generator 源码目录")
    common.add_argument("--runtime-dir", help="运行环境 skills 目录")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, help_text):
        return sub.add_parser(name, help=help_text, parents=[common])

    s = add("upload", "上传二维码图片，取公网 URL")
    s.add_argument("image")
    s.add_argument("--keep-filename", action="store_true", help="保留原文件名（默认改唯一名以防缓存）")
    s.set_defaults(func=cmd_upload)

    s = add("replace-skill", "更新 skill 源码里的群二维码")
    s.add_argument("--url")
    s.add_argument("--from-url", help="显式指定旧链接（SKILL.md 已被手工改成新图时用）")
    s.add_argument("--backup-dir")
    s.set_defaults(func=cmd_replace_skill)

    s = add("sync-runtime", "覆盖安装到运行环境 skills 目录")
    s.add_argument("--url")
    s.set_defaults(func=cmd_sync_runtime)

    s = add("plan", "清单比对：新增/移出")
    s.add_argument("--list")
    s.add_argument("--dirs")
    s.set_defaults(func=cmd_plan)

    s = add("update-repos", "批量替换仓库 README 二维码")
    s.add_argument("--url")
    s.add_argument("--from-url", help="显式指定旧链接（默认读 state 里的 from_url）")
    s.add_argument("--policy", default="keep", choices=["keep", "merge", "new-only", "replace"])
    s.add_argument("--list")
    s.add_argument("--dirs")
    s.add_argument("--update-manifest", action="store_true", help="按 policy 回写 projects.json")
    s.add_argument("--backup-dir")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_update_repos)

    s = add("push", "精确提交并推送")
    s.add_argument("--policy", default="keep", choices=["keep", "merge", "new-only", "replace"])
    s.add_argument("--list")
    s.add_argument("--dirs")
    s.add_argument("--only-changed", action="store_true", help="占位：默认就是只推有改动的")
    s.add_argument("--include-skill", action="store_true", help="同时提交 skill 源码文件")
    s.add_argument("--message")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--no-record", action="store_true", help="不写 rounds 记录")
    s.set_defaults(func=cmd_push)

    s = add("verify", "全链路核对")
    s.add_argument("--url")
    s.add_argument("--check-remote", action="store_true")
    s.add_argument("--remote-limit", type=int, default=5)
    s.set_defaults(func=cmd_verify)

    s = add("rollback", "用备份目录还原")
    s.add_argument("backup")
    s.set_defaults(func=cmd_rollback)

    s = add("status", "当前状态一览")
    s.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
