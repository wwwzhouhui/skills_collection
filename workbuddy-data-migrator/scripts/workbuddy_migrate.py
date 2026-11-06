#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workbuddy_migrate.py - WorkBuddy 数据目录无损迁移（Linux / macOS）

流程：只读检查 -> 复制 -> 全量 SHA-256 校验 -> 原目录改名保留 -> 建立符号链接。
回滚只删除经核验的符号链接入口，恢复本轮备份；目标目录永不自动删除。

安全边界：
  - 只接受名为 .workbuddy 或 WorkBuddy 的用户数据目录。
  - 源目录本身不能是符号链接；路径祖先含符号链接时默认拒绝，可用
    --accept-symlinked-ancestors 显式接受。
  - 源内部出现符号链接或特殊文件时停止，不做静默跳过或跟随。
  - 目标必须为空、不与源嵌套、不位于系统目录、空间足够。
  - migrate / rollback 必须带 --confirmed 与 --app-closed，并复查进程。

仅使用 Python 3.8+ 标准库。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import uuid
from datetime import datetime


VERSION = 1
MB = 1024 * 1024
MIN_RESERVE = 256 * MB
ALLOWED_SOURCE_NAMES = {".workbuddy", "WorkBuddy"}
EXACT_FORBIDDEN_TARGETS = {
    "/", "/Volumes", "/home", "/Users", "/mnt", "/media", "/tmp", "/opt", "/root",
}
PREFIX_FORBIDDEN_TARGETS = (
    "/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/proc",
    "/sbin", "/sys", "/usr", "/var", "/System", "/Library", "/Applications",
    "/private", "/cores",
)


class MigrationError(Exception):
    """可解释的拒绝或中止。"""


class Refused(MigrationError):
    """安全规则拒绝执行。"""


def eprint(message):
    print(message, file=sys.stderr)


def human_bytes(value):
    value = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return "%.1f %s" % (value, unit)
        value /= 1024


def normalize(path, base=None):
    expanded = os.path.expanduser(str(path))
    if not os.path.isabs(expanded):
        expanded = os.path.join(base or os.getcwd(), expanded)
    return os.path.normpath(expanded)


def is_symlink(path):
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except OSError:
        return False


def assert_ordinary_directory(path, label):
    try:
        st = os.lstat(path)
    except OSError as exc:
        raise MigrationError("%s 不可访问：%s（%s）" % (label, path, exc.strerror))
    if stat.S_ISLNK(st.st_mode):
        raise Refused("%s 是符号链接，不是普通目录：%s" % (label, path))
    if not stat.S_ISDIR(st.st_mode):
        raise Refused("%s 不是目录：%s" % (label, path))


def symlink_ancestors(path):
    found = []
    cursor = os.path.dirname(os.path.abspath(path))
    while True:
        if is_symlink(cursor):
            found.append(cursor)
        parent = os.path.dirname(cursor)
        if parent == cursor:
            break
        cursor = parent
    return found


def assert_ancestors(path, accept):
    found = symlink_ancestors(path)
    if found and not accept:
        raise Refused(
            "路径祖先包含符号链接：%s。确认这是预期布局后，显式添加 "
            "--accept-symlinked-ancestors 再执行。" % ", ".join(found)
        )
    return found


def forbidden_target_reason(path):
    real = os.path.realpath(path)
    if real in EXACT_FORBIDDEN_TARGETS:
        return real
    for prefix in PREFIX_FORBIDDEN_TARGETS:
        if real == prefix or real.startswith(prefix + os.sep):
            return prefix
    return None


def assert_separate(source, target):
    # 用 realpath 比较，避免符号链接别名把目标实际嵌入源目录。
    real_source = os.path.realpath(source)
    real_target = os.path.realpath(target)
    try:
        common = os.path.commonpath([real_source, real_target])
    except ValueError as exc:
        raise Refused("源与目标无法比较：%s" % exc)
    if common == real_source or common == real_target:
        raise Refused("源与目标不能相同或互相嵌套：%s <-> %s" % (source, target))


def find_mount(path):
    cursor = os.path.abspath(path)
    try:
        device = os.stat(cursor).st_dev
    except OSError:
        return None
    while True:
        parent = os.path.dirname(cursor)
        if parent == cursor:
            return cursor
        try:
            if os.stat(parent).st_dev != device:
                return cursor
        except OSError:
            return cursor
        cursor = parent


def sha256_file(path):
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise MigrationError(
            "无法读取文件（权限或 I/O 错误），未做任何修改：%s（%s）"
            % (path, exc.strerror)
        )
    return digest.hexdigest()


def scan_tree(root, with_hash):
    files = []
    directories = []
    symlinks = []
    specials = []
    total = 0
    stack = [""]
    while stack:
        relative_dir = stack.pop()
        absolute_dir = os.path.join(root, relative_dir) if relative_dir else root
        try:
            entries = list(os.scandir(absolute_dir))
        except OSError as exc:
            raise MigrationError("无法枚举目录：%s（%s）" % (absolute_dir, exc.strerror))
        for entry in entries:
            relative = os.path.join(relative_dir, entry.name) if relative_dir else entry.name
            try:
                st = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise MigrationError("无法读取文件元数据：%s（%s）" % (entry.path, exc.strerror))
            if stat.S_ISLNK(st.st_mode):
                symlinks.append(relative)
                continue
            if stat.S_ISDIR(st.st_mode):
                directories.append(relative)
                stack.append(relative)
                continue
            if stat.S_ISREG(st.st_mode):
                digest = sha256_file(entry.path) if with_hash else ""
                files.append({
                    "path": relative,
                    "size": st.st_size,
                    "mode": stat.S_IMODE(st.st_mode),
                    "sha256": digest,
                })
                total += st.st_size
                continue
            specials.append(relative)
    files.sort(key=lambda item: item["path"])
    directories.sort()
    symlinks.sort()
    specials.sort()
    return {
        "directories": directories,
        "files": files,
        "bytes": total,
        "file_count": len(files),
        "symlinks": symlinks,
        "specials": specials,
    }


def inventory_key(inventory):
    return json.dumps(
        {"directories": inventory["directories"], "files": inventory["files"]},
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def inventory_equal(left, right):
    return inventory_key(left) == inventory_key(right)


def list_processes():
    """返回运行中的 WorkBuddy 进程。不使用 pgrep，避免依赖。"""
    self_pid = os.getpid()
    parent_pid = os.getppid()
    seen = {}
    if os.path.isdir("/proc"):
        for name in os.listdir("/proc"):
            if not name.isdigit():
                continue
            pid = int(name)
            if pid in (self_pid, parent_pid):
                continue
            try:
                with open("/proc/%d/comm" % pid, "r", encoding="utf-8", errors="replace") as handle:
                    comm = handle.read().strip()
            except OSError:
                continue
            exe = ""
            try:
                exe = os.readlink("/proc/%d/exe" % pid)
            except OSError:
                pass
            if _process_matches(comm) or _process_matches(exe):
                seen[pid] = os.path.basename(exe or comm)
        return [{"pid": pid, "name": seen[pid]} for pid in sorted(seen)]
    try:
        output = subprocess.run(
            ["ps", "-axo", "pid=,comm="],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            universal_newlines=True, check=False,
        ).stdout
    except OSError:
        return []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        if pid in (self_pid, parent_pid):
            continue
        if _process_matches(parts[1]):
            seen[pid] = os.path.basename(parts[1].strip())
    return [{"pid": pid, "name": seen[pid]} for pid in sorted(seen)]


def _process_matches(value):
    if not value:
        return False
    base = os.path.basename(value.strip()).casefold()
    return "workbuddy" in base


def assert_app_closed(args):
    if not getattr(args, "confirmed", False) or not getattr(args, "app_closed", False):
        raise Refused(
            "需要用户明确确认且声明应用已退出：--confirmed --app-closed。"
            "这两个开关是确认记录，不替代询问。"
        )
    running = list_processes()
    if running:
        detail = ", ".join("%s(%d)" % (item["name"], item["pid"]) for item in running)
        raise Refused(
            "检测到 WorkBuddy 仍在运行：%s。请从托盘/菜单完全退出后重试。" % detail
        )


def write_state(path, state):
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def read_state(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, ValueError) as exc:
        raise MigrationError("无法读取迁移状态文件：%s（%s）" % (path, exc))
    if state.get("Version") != VERSION:
        raise Refused("状态文件版本不受支持：%s" % state.get("Version"))
    return state


def source_path(value):
    path = normalize(value)
    if not os.path.exists(path):
        raise Refused("源目录不存在：%s" % path)
    assert_ordinary_directory(path, "源目录")
    base = os.path.basename(path)
    if base not in ALLOWED_SOURCE_NAMES:
        raise Refused(
            "为限定作用域，源目录名必须是 .workbuddy 或 WorkBuddy，当前为：%s" % path
        )
    if path == "/" or os.path.dirname(path) == path:
        raise Refused("不能把根目录作为源：%s" % path)
    return path


def prepare_target(value, source, required_bytes, for_migrate, accept_ancestors=False):
    target = normalize(value)
    reason = forbidden_target_reason(target)
    if reason:
        raise Refused("目标不能位于系统目录（%s）：%s" % (reason, target))
    assert_separate(source, target)
    parent = os.path.dirname(target)
    if parent == target:
        raise Refused("目标不能是文件系统根目录：%s" % target)
    if not os.path.isdir(parent):
        raise Refused(
            "目标父目录不存在或不是目录：%s。请先创建或挂载目标卷，不要依赖脚本自动创建多层路径。" % parent
        )
    if not os.access(parent, os.W_OK):
        raise Refused("目标父目录不可写：%s" % parent)
    if for_migrate:
        assert_ancestors(target, accept_ancestors)
    if os.path.lexists(target):
        assert_ordinary_directory(target, "目标目录")
        try:
            if os.listdir(target):
                raise Refused("目标目录非空，不会清空或覆盖：%s" % target)
        except OSError as exc:
            raise MigrationError("无法读取目标目录：%s（%s）" % (target, exc.strerror))
    # 目标已存在（空目录）时，以目标自身为准；否则以父目录所在卷为准。
    probe = target if os.path.isdir(target) else parent
    try:
        free = shutil.disk_usage(probe).free
    except OSError as exc:
        raise MigrationError("无法获取目标空间：%s（%s）" % (probe, exc.strerror))
    if for_migrate and free < required_bytes + MIN_RESERVE:
        raise Refused(
            "目标空间不足：可用 %s，需要 %s 加 256 MiB 余量。"
            % (human_bytes(free), human_bytes(required_bytes))
        )
    same_device = os.stat(source).st_dev == os.stat(probe).st_dev
    return {
        "target": target,
        "parent": parent,
        "free": free,
        "same_device": same_device,
        "mount": find_mount(probe),
    }


def copy_tree(source, target, inventory):
    os.makedirs(target, mode=0o700, exist_ok=True)
    for relative in inventory["directories"]:
        os.makedirs(os.path.join(target, relative), mode=0o700, exist_ok=True)
    for item in inventory["files"]:
        src_path = os.path.join(source, item["path"])
        dst_path = os.path.join(target, item["path"])
        shutil.copy2(src_path, dst_path, follow_symlinks=False)
    for relative in sorted(inventory["directories"], key=lambda value: value.count(os.sep), reverse=True):
        try:
            shutil.copystat(
                os.path.join(source, relative),
                os.path.join(target, relative),
                follow_symlinks=False,
            )
        except OSError:
            # 内容已单独校验；元数据复制失败不改变数据完整性结论。
            pass
    try:
        os.chmod(target, 0o700)
    except OSError:
        pass


def emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
        return
    for key, value in payload.items():
        if isinstance(value, list):
            if value and isinstance(value[0], dict):
                rendered = ", ".join(
                    "%s(%s)" % (item.get("name", "?"), item.get("pid", "?")) for item in value
                )
            else:
                rendered = ", ".join(str(item) for item in value)
            print("%s: %s" % (key, rendered if rendered else "none"))
        else:
            print("%s: %s" % (key, value))


def cmd_inspect(args):
    source = normalize(args.source)
    payload = {
        "Status": "Inspected",
        "Platform": "%s %s" % (sys.platform, os.uname().machine if hasattr(os, "uname") else ""),
        "Source": source,
        "RunningProcesses": list_processes(),
    }
    if not os.path.lexists(source):
        payload["Status"] = "SourceMissing"
        payload["Candidates"] = [
            "%s [%s]" % (candidate, "exists" if os.path.lexists(candidate) else "missing")
            for candidate in _candidate_paths()
        ]
        payload["Note"] = "源目录不存在。只读检查未修改任何数据。"
        emit(payload, args.json)
        return 0
    if is_symlink(source):
        payload["Status"] = "AlreadyLinked"
        payload["LinkTarget"] = os.readlink(source)
        payload["Note"] = "源路径已经是符号链接；不要重复迁移。"
        emit(payload, args.json)
        return 0
    assert_ordinary_directory(source, "源目录")
    ancestors = symlink_ancestors(source)
    if os.path.basename(source) not in ALLOWED_SOURCE_NAMES:
        scope_warning = (
            "源目录名不在迁移作用域内（只允许 .workbuddy 或 WorkBuddy）。"
            "Inspect 仍可只读检查，但 migrate 会拒绝。"
        )
    else:
        scope_warning = ""
    inventory = scan_tree(source, with_hash=False)
    payload.update({
        "Files": inventory["file_count"],
        "Directories": len(inventory["directories"]),
        "Bytes": inventory["bytes"],
        "BytesHuman": human_bytes(inventory["bytes"]),
        "SourceMount": find_mount(source),
        "SourceDevice": os.stat(source).st_dev,
        "SymlinkedAncestors": ancestors,
        "ScopeWarning": scope_warning,
        "InternalSymlinks": inventory["symlinks"][:20],
        "InternalSymlinkCount": len(inventory["symlinks"]),
        "SpecialFiles": inventory["specials"][:20],
        "SpecialFileCount": len(inventory["specials"]),
    })
    if args.target:
        try:
            prepared = prepare_target(args.target, source, inventory["bytes"], for_migrate=False)
        except MigrationError as exc:
            payload["TargetStatus"] = "Unusable"
            payload["TargetError"] = str(exc)
            payload["Note"] = "只读检查已完成，但目标不可用；未修改任何数据。"
            emit(payload, args.json)
            return 2
        target_ancestors = symlink_ancestors(prepared["target"])
        payload.update({
            "Target": prepared["target"],
            "TargetStatus": "Usable",
            "TargetMount": prepared["mount"],
            "TargetFreeBytes": prepared["free"],
            "TargetFreeHuman": human_bytes(prepared["free"]),
            "TargetSameFilesystem": prepared["same_device"],
            "TargetSymlinkedAncestors": target_ancestors,
        })
        if prepared["same_device"]:
            payload["TargetWarning"] = "源与目标在同一文件系统，迁移不会释放原盘空间。"
        if target_ancestors:
            payload["TargetWarning"] = (
                "目标路径祖先包含符号链接：%s。迁移与回滚都需要 "
                "--accept-symlinked-ancestors。" % ", ".join(target_ancestors)
            )
    payload["Note"] = (
        "只读元数据快照。未复制、未改权限、未写状态文件。"
        "应用验收与备份清理是独立步骤。"
    )
    emit(payload, args.json)
    return 0


def _candidate_paths():
    home = os.path.expanduser("~")
    return [
        os.path.join(home, ".workbuddy"),
        os.path.join(home, "Library", "Application Support", "WorkBuddy"),
    ]


def cmd_migrate(args):
    if os.name != "posix":
        raise Refused("本脚本面向 Linux/macOS；Windows 请使用 scripts/workbuddy-migrate.ps1。")
    source = source_path(args.source)
    assert_ancestors(source, args.accept_symlinked_ancestors)
    assert_app_closed(args)
    inventory = scan_tree(source, with_hash=True)
    if inventory["symlinks"]:
        raise Refused(
            "源目录内部存在符号链接，需单独处理后再迁移（示例：%s）。"
            % ", ".join(inventory["symlinks"][:10])
        )
    if inventory["specials"]:
        raise Refused(
            "源目录内部存在特殊文件（socket/fifo/设备），需单独处理后再迁移（示例：%s）。"
            % ", ".join(inventory["specials"][:10])
        )
    prepared = prepare_target(
        args.target, source, inventory["bytes"],
        for_migrate=True, accept_ancestors=args.accept_symlinked_ancestors,
    )
    target = prepared["target"]

    identifier = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    backup = source + ".backup-" + identifier
    state_file = backup + ".migration.json"
    for path in (backup, state_file):
        if len(os.fsencode(path)) >= 4096:
            raise Refused("备份或状态文件路径过长：%s" % path)

    state = {
        "Version": VERSION,
        "Status": "Copying",
        "Source": source,
        "Target": target,
        "Backup": backup,
        "Inventory": inventory,
        "Created": datetime.now().astimezone().isoformat(),
    }
    write_state(state_file, state)

    try:
        copy_tree(source, target, inventory)
        assert_app_closed(args)
        source_after = scan_tree(source, with_hash=True)
        if not inventory_equal(inventory, source_after):
            raise MigrationError("复制期间源目录发生变化；未执行切换。")
        target_after = scan_tree(target, with_hash=True)
        if not inventory_equal(inventory, target_after):
            raise MigrationError("目标内容校验失败；未执行切换。")
        state["Status"] = "Verified"
        write_state(state_file, state)

        os.rename(source, backup)
        try:
            os.symlink(target, source)
            if not is_symlink(source) or os.path.abspath(os.readlink(source)) != target:
                raise MigrationError("符号链接核验失败。")
            if os.path.realpath(source) != os.path.realpath(target):
                raise MigrationError("符号链接解析结果与目标不一致。")
        except Exception:
            if is_symlink(source):
                try:
                    if os.path.abspath(os.readlink(source)) == target:
                        os.unlink(source)
                except OSError:
                    pass
            if not os.path.lexists(source):
                os.rename(backup, source)
            raise
        state["Status"] = "Linked"
        write_state(state_file, state)
    except Exception as exc:
        eprint(
            "已中止，未删除数据。源：%s；目标：%s；备份：%s；状态：%s"
            % (source, target, backup, state_file)
        )
        if isinstance(exc, MigrationError):
            raise
        raise MigrationError("%s: %s" % (type(exc).__name__, exc))

    emit({
        "Status": "Linked-AppValidationPending",
        "Source": source,
        "Target": target,
        "Backup": backup,
        "StateFile": state_file,
        "Files": inventory["file_count"],
        "Bytes": inventory["bytes"],
        "TargetFreeHuman": human_bytes(prepared["free"]),
        "SameFilesystem": prepared["same_device"],
        "Note": (
            "SHA-256 与符号链接校验通过。旧备份仍占原盘空间；"
            "请先完成 WorkBuddy 应用验收，再单独决定是否清理备份。"
        ),
    }, args.json)
    return 0


def cmd_rollback(args):
    if os.name != "posix":
        raise Refused("本脚本面向 Linux/macOS；Windows 请使用 scripts/workbuddy-migrate.ps1。")
    assert_app_closed(args)
    state_file = normalize(args.state_file)
    state = read_state(state_file)
    if state.get("Status") != "Linked":
        raise Refused("状态不是已完成的符号链接迁移（当前：%s）。" % state.get("Status"))
    source = normalize(state.get("Source", ""))
    target = normalize(state.get("Target", ""))
    backup = normalize(state.get("Backup", ""))
    if os.path.basename(source) not in ALLOWED_SOURCE_NAMES:
        raise Refused("状态中的源路径不在允许范围：%s" % source)
    if os.path.dirname(backup) != os.path.dirname(source):
        raise Refused("备份不在源同级目录：%s" % backup)
    if not os.path.basename(backup).startswith(os.path.basename(source) + ".backup-"):
        raise Refused("备份路径与本轮迁移不匹配：%s" % backup)
    if os.path.abspath(state_file) != os.path.abspath(backup + ".migration.json"):
        raise Refused("状态文件与本轮备份不匹配：%s" % state_file)
    if not is_symlink(source):
        raise Refused("源入口不是符号链接，拒绝自动回滚：%s" % source)
    linked = os.path.abspath(os.readlink(source))
    if linked != target or os.path.realpath(source) != os.path.realpath(target):
        raise Refused("源入口不是指向本轮目标的链接，拒绝移除：%s -> %s" % (source, linked))
    assert_ordinary_directory(backup, "备份目录")
    assert_ordinary_directory(target, "目标目录")
    assert_ancestors(backup, args.accept_symlinked_ancestors)
    assert_ancestors(target, args.accept_symlinked_ancestors)

    backup_now = scan_tree(backup, with_hash=True)
    if not inventory_equal(state.get("Inventory", {}), backup_now):
        raise Refused("备份内容与迁移时不一致，自动回滚不安全。")
    target_now = scan_tree(target, with_hash=True)
    changed = not inventory_equal(state.get("Inventory", {}), target_now)
    if changed and not args.accept_new_data_in_target:
        raise Refused(
            "目标中存在迁移后的新增或修改数据。回滚会恢复到迁移前状态，"
            "新数据仍保留在目标但不再从原路径访问。用户明确接受后再加 "
            "--accept-new-data-in-target。"
        )

    os.unlink(source)
    try:
        os.rename(backup, source)
    except Exception:
        if not os.path.lexists(source):
            os.symlink(target, source)
        raise
    state["Status"] = "RolledBack"
    state["RolledBackAt"] = datetime.now().astimezone().isoformat()
    write_state(state_file, state)
    emit({
        "Status": "RolledBack",
        "Source": source,
        "RetainedTarget": target,
        "NewDataRetained": changed,
        "StateFile": state_file,
        "Note": "原入口已恢复为备份目录；目标目录保留，未自动删除。",
    }, args.json)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="WorkBuddy 数据目录无损迁移（Linux/macOS）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    inspect = subparsers.add_parser("inspect", help="只读检查，不修改任何数据")
    inspect.add_argument("--source", default=os.path.join(os.path.expanduser("~"), ".workbuddy"))
    inspect.add_argument("--target")
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=cmd_inspect)

    migrate = subparsers.add_parser("migrate", help="复制、校验并切换为符号链接")
    migrate.add_argument("--source", default=os.path.join(os.path.expanduser("~"), ".workbuddy"))
    migrate.add_argument("--target", required=True)
    migrate.add_argument("--confirmed", action="store_true")
    migrate.add_argument("--app-closed", action="store_true")
    migrate.add_argument("--accept-symlinked-ancestors", action="store_true")
    migrate.add_argument("--json", action="store_true")
    migrate.set_defaults(func=cmd_migrate)

    rollback = subparsers.add_parser("rollback", help="按状态文件恢复迁移前目录")
    rollback.add_argument("--state-file", required=True)
    rollback.add_argument("--confirmed", action="store_true")
    rollback.add_argument("--app-closed", action="store_true")
    rollback.add_argument("--accept-new-data-in-target", action="store_true")
    rollback.add_argument("--accept-symlinked-ancestors", action="store_true")
    rollback.add_argument("--json", action="store_true")
    rollback.set_defaults(func=cmd_rollback)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except Refused as exc:
        eprint("REFUSED: %s" % exc)
        return 2
    except MigrationError as exc:
        eprint("ERROR: %s" % exc)
        return 1
    except KeyboardInterrupt:
        eprint("已中断。未删除数据，请检查源、目标与状态文件。")
        return 130


if __name__ == "__main__":
    sys.exit(main())