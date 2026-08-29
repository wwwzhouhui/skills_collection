#!/usr/bin/env python3
"""SessionStart: 依赖检查 + 插件路径通告 + ASR/TTS 可用性。

stdout 会进入会话上下文, 这里输出:
- 插件根路径与 MCP server 路径 (同时落 .video_agent/plugin_root 文件);
- 实际加载了哪些 .env;
- 缺失依赖清单 (只报不阻塞 —— 让模型/用户知道哪些能力会不可用) + 指向 env-setup skill;
- cloud ASR / cloud TTS 是否配好 (决定转录和配音能不能做)。

依赖清单和凭据判断都不在这里维护: 从 env-setup skill 的 env_doctor.py 取
(cheap 检查项 = 毫秒级、不碰网络), 两处各写一份必然漂移 —— 0.4.0 就是两份,
结果 requirements.txt 里要 --no-deps 装的 scenedetect 在这里被当成普通必需项报,
而真正致命的"ffmpeg 没带 libass"、"机器上没有中文字体"一个字都没提。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_common import plugin_root, project_dir  # noqa: E402

DOCTOR_DIR = plugin_root() / "skills" / "env-setup" / "scripts"


def doctor():
    """→ (module, 异常说明)。异常说明非空时表示体检脚本本身没跑起来。"""
    sys.path.insert(0, str(DOCTOR_DIR))
    try:
        import env_doctor  # noqa: PLC0415

        return env_doctor, ""
    except Exception as exc:
        return None, (f"环境体检脚本不可用 ({DOCTOR_DIR / 'env_doctor.py'}): "
                      f"{type(exc).__name__}: {exc}")


def main() -> None:
    # Hook stdout is a pipe; on Windows the default locale encoding (cp936 etc.)
    # cannot encode symbols like ✓/⚠. Force UTF-8 with errors="replace" so the
    # report is never replaced by a UnicodeEncodeError traceback.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    root = plugin_root()
    lines = [
        f"[video-agent-kit] plugin_root: {root}",
        f"[video-agent-kit] MCP server: {root / 'mcp' / 'video_edit_server.py'}",
    ]
    # plugin_root 标记写失败 (只读项目目录等) 只是附属品, 绝不能吞掉下面的
    # 全部环境诊断输出
    work = project_dir() / ".video_agent"
    try:
        work.mkdir(parents=True, exist_ok=True)
        (work / "plugin_root").write_text(str(root), encoding="utf-8")
    except OSError as exc:
        lines.append(f"[video-agent-kit] warn: cannot write {work / 'plugin_root'}: {exc}")

    try:
        sys.path.insert(0, str(root / "mcp"))
        from ve_tools.run_context import env_files

        loaded = [str(path) for path in env_files() if path.is_file()]
        if loaded:
            lines.append("[video-agent-kit] config files (.env): " + ", ".join(loaded))
    except Exception:
        pass

    mod, err = doctor()
    if err:
        lines.append(f"[video-agent-kit] [!] {err} — 依赖状态未知, 跑流程前先人工体检")
    else:
        missing = mod.cheap_missing()
        if missing:
            # 只报不阻塞, 但必须给出下一步动作: 这里只跑了毫秒级项 (没探测 ffmpeg 带不带
            # libass / 有没有中文字体 / 出网通不通), 所以指向 env-setup 做全量体检+安装,
            # 而不是让模型对着这行自己猜装什么。
            lines.append("[video-agent-kit] [!] 缺失依赖: " + "; ".join(missing))
            lines.append("[video-agent-kit] → 装之前先 Skill(env-setup) 或 /env-check: "
                         "全量体检 (含 ffmpeg 编码器/滤镜、中文字体真覆盖、语音服务连通性) "
                         "+ 逐项修复命令 (默认走国内镜像); 缺 mcp/ffmpeg 时相关工具直接不可用, 别硬跑")
        lines.extend(f"[video-agent-kit] {line}" for line in mod.credential_lines())
    print("\n".join(lines))


if __name__ == "__main__":
    main()
