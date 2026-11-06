#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TEST DATA ONLY - Linux/macOS 端到端自检。

在用户主目录下创建临时工作区，模拟一个 `.workbuddy` 数据目录，完整执行
inspect -> migrate -> inspect(AlreadyLinked) -> rollback 流程，并验证拒绝路径。
不接触任何真实 WorkBuddy 数据，结束后删除临时目录。

用法：python3 scripts/selftest_posix.py
退出码：0 全部通过或跳过（应用运行中）；1 存在失败。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workbuddy_migrate.py")
PASSED = []
FAILED = []


def check(condition, message):
    if condition:
        PASSED.append(message)
        print("PASS: %s" % message)
    else:
        FAILED.append(message)
        print("FAIL: %s" % message)


def run(arguments, expect_zero=True):
    result = subprocess.run(
        [sys.executable, SCRIPT] + arguments,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, check=False,
    )
    if expect_zero and result.returncode != 0:
        print("  stdout: %s" % result.stdout.strip())
        print("  stderr: %s" % result.stderr.strip())
    return result


def write_file(path, content, binary=False):
    mode = "wb" if binary else "w"
    kwargs = {} if binary else {"encoding": "utf-8"}
    with open(path, mode, **kwargs) as handle:
        handle.write(content)


def main():
    if os.name != "posix":
        print("SKIP: 本自检只适用于 Linux/macOS。")
        return 0

    home_root = os.path.expanduser("~")
    try:
        workspace = tempfile.mkdtemp(prefix="wbm-selftest-", dir=home_root)
    except OSError as exc:
        print("SKIP: 主目录不可写，无法安全创建临时测试区（%s）。" % exc)
        return 0

    try:
        source = os.path.join(workspace, "home", ".workbuddy")
        target = os.path.join(workspace, "migrated-WorkBuddy")
        os.makedirs(os.path.join(source, "sessions", "2026"))
        os.makedirs(os.path.join(source, "db"))
        os.makedirs(os.path.join(source, "cache"))
        write_file(os.path.join(source, "config.json"), '{"test": true}\n')
        write_file(os.path.join(source, "sessions", "2026", "a.jsonl"), '{"role":"user"}\n')
        write_file(os.path.join(source, "db", "workbuddy.sqlite"), bytes(range(256)) * 8, binary=True)
        write_file(os.path.join(source, "empty.txt"), "")
        write_file(os.path.join(source, "会话记录.txt"), "TEST DATA ONLY\n")

        inspect_result = run(["inspect", "--source", source, "--target", target, "--json"])
        check(inspect_result.returncode == 0, "inspect 返回 0")
        try:
            inspected = json.loads(inspect_result.stdout)
        except ValueError:
            inspected = {}
        check(inspected.get("Status") == "Inspected", "inspect 状态为 Inspected")
        check(inspected.get("Files") == 5, "inspect 统计 5 个文件")
        check(inspected.get("Directories") == 4, "inspect 统计 4 个目录")
        check(not os.path.exists(target), "inspect 不创建目标目录")
        if inspected.get("RunningProcesses"):
            print("SKIP: 检测到 WorkBuddy 正在运行，跳过迁移测试。请先退出应用。")
            return 0

        migrate_result = run([
            "migrate", "--source", source, "--target", target,
            "--confirmed", "--app-closed", "--json",
        ])
        check(migrate_result.returncode == 0, "migrate 返回 0")
        check(os.path.islink(source), "原路径已变为符号链接")
        check(os.path.abspath(os.readlink(source)) == os.path.abspath(target), "链接指向目标")
        check(os.path.isfile(os.path.join(target, "sessions", "2026", "a.jsonl")), "目标包含嵌套文件")
        check(os.path.isfile(os.path.join(target, "会话记录.txt")), "目标保留非 ASCII 文件名")
        backup = None
        state_file = None
        try:
            state = json.loads(migrate_result.stdout)
            backup = state.get("Backup")
            state_file = state.get("StateFile")
        except ValueError:
            pass
        check(bool(backup) and os.path.isdir(backup) and not os.path.islink(backup), "备份是普通目录")
        check(bool(state_file) and os.path.isfile(state_file), "状态文件已生成")
        if state_file:
            with open(state_file, "r", encoding="utf-8") as handle:
                state_data = json.load(handle)
            check(state_data.get("Status") == "Linked", "状态文件为 Linked")

        linked_inspect = run(["inspect", "--source", source, "--json"])
        try:
            linked_payload = json.loads(linked_inspect.stdout)
        except ValueError:
            linked_payload = {}
        check(linked_payload.get("Status") == "AlreadyLinked", "重复 inspect 报告 AlreadyLinked")

        with open(os.path.join(target, "config.json"), "w", encoding="utf-8") as handle:
            handle.write('{"test": false, "changed": true}\n')
        refused = run(["rollback", "--state-file", state_file, "--confirmed", "--app-closed"])
        check(refused.returncode != 0, "目标有新数据时拒绝自动回滚")

        rolled = run([
            "rollback", "--state-file", state_file, "--confirmed", "--app-closed",
            "--accept-new-data-in-target", "--json",
        ])
        check(rolled.returncode == 0, "显式接受新数据后回滚成功")
        check(os.path.isdir(source) and not os.path.islink(source), "原路径恢复为普通目录")
        with open(os.path.join(source, "config.json"), "r", encoding="utf-8") as handle:
            restored = handle.read()
        check(restored == '{"test": true}\n', "源目录内容恢复到迁移前状态")
        with open(os.path.join(target, "config.json"), "r", encoding="utf-8") as handle:
            retained = handle.read()
        check("changed" in retained, "目标保留迁移后的新数据")
        if state_file:
            with open(state_file, "r", encoding="utf-8") as handle:
                state_data = json.load(handle)
            check(state_data.get("Status") == "RolledBack", "状态文件为 RolledBack")

        nonempty = os.path.join(workspace, "nonempty-target")
        os.makedirs(nonempty)
        write_file(os.path.join(nonempty, "keep.txt"), "keep\n")
        nonempty_result = run(["inspect", "--source", source, "--target", nonempty])
        check(nonempty_result.returncode == 2, "非空目标被拒绝")

        inside = os.path.join(source, "nested-target")
        nested_result = run(["inspect", "--source", source, "--target", inside])
        check(nested_result.returncode == 2, "源内嵌套目标被拒绝")

        missing_parent = os.path.join(workspace, "no", "such", "parent", "target")
        missing_parent_result = run(["inspect", "--source", source, "--target", missing_parent])
        check(missing_parent_result.returncode == 2, "目标父目录不存在被拒绝")

        alias_home = os.path.join(workspace, "alias-home")
        os.symlink(os.path.join(workspace, "home"), alias_home)
        alias_target = os.path.join(alias_home, ".workbuddy", "inner-target")
        alias_result = run(["inspect", "--source", source, "--target", alias_target])
        check(alias_result.returncode == 2, "符号链接别名嵌套目标被拒绝")
        check(not os.path.exists(alias_target), "拒绝嵌套目标时不产生部分拷贝")

        symlink_source = os.path.join(workspace, "home", ".workbuddy")
        os.symlink("../elsewhere", os.path.join(symlink_source, "linked-entry"))
        symlink_inspect = run(["inspect", "--source", symlink_source, "--json"])
        try:
            symlink_payload = json.loads(symlink_inspect.stdout)
        except ValueError:
            symlink_payload = {}
        check(symlink_payload.get("InternalSymlinkCount") == 1, "inspect 报告内部符号链接")
        os.unlink(os.path.join(symlink_source, "linked-entry"))
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    print("\nRESULT: %d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        for message in FAILED:
            print("  - %s" % message)
        return 1
    print("TEST DATA ONLY 自检通过，临时目录已清理。")
    return 0


if __name__ == "__main__":
    sys.exit(main())