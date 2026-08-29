#!/usr/bin/env python3
"""video-agent-kit 环境体检: 逐项探测 → 输出「缺什么 / 挂哪个能力 / 本平台怎么装」。

跨平台 (macOS / Windows / Linux)。设计约束照 video2code 的同名脚本:
- **要求先于命令**: 每项先说清"需要什么"(名字 + 版本线), 再按当前平台给示例命令。
  用户机器长什么样这里不知道 (有没有 brew/winget、有没有管理员权限、是不是 conda
  环境), 所以命令是示例不是规定 —— 只有要求是硬的。
- **探测与修复分离**: 默认只读探测; `--fix` 才动手, 且只跑标了 auto 的项 (用户态、
  幂等)。系统级软件 (ffmpeg / 字体 / 系统库) 永远只打印, 不自动执行。
- **单一事实源**: SessionStart hook (`hooks/env_check.py`) 直接 import 这里的
  cheap 检查项和凭据探测, 依赖清单不许两处各写一份 (漂移过一次就永远漂移)。
- **探测顺序即依赖顺序**: 没装 ffmpeg 就不必再问它有没有 libass —— 后置项标
  `needs`, 前置失败则整项跳过 (报 skip 而不是伪失败), 免得一个根因炸出五条噪音。
- **"装了" ≠ "能用"**: 这个插件挂在"装了但不带某个 feature"上的次数比挂在"没装"上
  多 —— conda/静态包的 ffmpeg 常常没有 libass(烧不了字幕)或没有 libmp3lame;
  fc-match 问它要中文字体会把 DejaVu 交给你(渲染出豆腐块但编码成功)。所以
  ffmpeg 查编码器/滤镜、字体查 cmap 真覆盖, 不只查 PATH 上在不在。

用法:
  env_doctor.py            # 全量探测 + 修复计划
  env_doctor.py --cheap    # 只跑毫秒级项 (无网络), hook 用
  env_doctor.py --json     # 机器可读
  env_doctor.py --fix      # 探测后自动装 auto 项, 再复测这些项
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

def _resolve_plugin_root() -> Path:
    """定位插件根目录: 优先环境变量, 否则从本文件向上找含 requirements.txt 的目录,
    最后兜底用当前工作目录。"""
    for key in ("CLAUDE_PLUGIN_ROOT", "VE_PLUGIN_ROOT"):
        val = os.environ.get(key)
        if val:
            return Path(val)
    probe = Path(__file__).resolve()
    for parent in [probe.parents[i] for i in range(6)]:
        if (parent / "requirements.txt").is_file() and (parent / "mcp").is_dir():
            return parent
    return Path.cwd()


PLUGIN_ROOT = _resolve_plugin_root()
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR")
                   or os.environ.get("VE_PROJECT_DIR") or Path.cwd())
REQUIREMENTS = PLUGIN_ROOT / "requirements.txt"
PY = sys.executable or "python3"
# 命令行里用 PYQ: Windows 解释器路径常含空格, do_fix 又走 shell=True
PYQ = f'"{PY}"' if " " in PY else PY

OS = ("macos" if sys.platform == "darwin"
      else "windows" if os.name == "nt" else "linux")

# ── 国内镜像: 默认走, 不是"备选" ──────────────────────────────────────────────
# 面向的是普通用户, 官方源在国内经常几十 KB/s 甚至直接超时, 而 pip 的超时表现是
# "装了十分钟然后失败", 最容易被误判成别的毛病。所以默认就用镜像, 出问题再回官方源
# (VE_PIP_INDEX 可覆盖)。
PIP_TSINGHUA = "https://pypi.tuna.tsinghua.edu.cn/simple"
PIP_ALIYUN = "https://mirrors.aliyun.com/pypi/simple/"
PIP_INDEX = os.environ.get("VE_PIP_INDEX", PIP_TSINGHUA)

# ffmpeg / 字体的装法分平台, 国内都建议走镜像 —— 但不同包管理器换镜像的方式差很多:
#   brew   → 设 HOMEBREW_BOTTLE_DOMAIN (bottle 从 GitHub 下, 国内很慢/失败)
#   apt    → 换 sources.list 里的源 (改的是系统全局配置, 不是装一次就完)
#   conda  → 指定 channel URL, 最干净 (无 root、不动系统包管理器)
# Windows 上 winget 没有镜像概念, ffmpeg 静态包来自 gyan.dev, 可能慢 —— 用 conda 绕开。
HOMEBREW_BOTTLE = "https://mirrors.tuna.tsinghua.edu.cn/homebrew-bottles"
CONDA_FORGE_TSINGHUA = "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge"

# 直连 HTTP 兼容通道的端点。没有内置默认值: 这个通道是 legacy escape hatch, 只有
# 部署方显式注入端点时才存在, 所以未配置就是"这条通道不适用", 不是"探测失败"。
SPEECH_ENDPOINT = os.environ.get("VE_SPEECH_ASR_ENDPOINT") or os.environ.get("VE_CLOUD_ASR_ENDPOINT")
SPEECH_ENDPOINT_LABEL = "configured compatibility speech endpoint"


def under_zcode_host() -> bool:
    """在 ZCode 宿主里跑 → 语音走官方通道, 本地不需要任何 key。

    ZCODE_BASE_URL 由宿主 spawn 时注入。注意体检脚本是**独立进程**, 看不到随单次
    ``tools/call`` 的 ``_meta`` 下发的身份头, 所以这里只能判"官方通道在不在", 判不了
    "这次调用的身份好不好" —— 后者由 MCP 工具自己在调用时报。
    """
    return bool((os.environ.get("ZCODE_BASE_URL") or "").strip())

# 渲染要落 preview/final mp4 + 抽帧 contact sheet, 空间不够是"渲到一半炸"。
MIN_FREE_GB = 5


def by_os(**variants: list[str]) -> list[str]:
    """按当前平台取一份修复示例; 缺本平台条目时回落 any。"""
    return variants.get(OS) or variants.get("any") or []


def pip_install(*specs: str, no_deps: bool = False) -> str:
    quoted = " ".join(f'"{s}"' if any(c in s for c in "<>=") else s for s in specs)
    return f"{PYQ} -m pip install -i {PIP_INDEX}{' --no-deps' if no_deps else ''} {quoted}"


PIP_MIRROR_NOTES = [
    f"# 上面用的是清华镜像; 阿里云: -i {PIP_ALIYUN}",
    f"# 想一劳永逸设成默认 (改的是全局 pip 配置, 影响这台机器上所有项目, 先问用户):",
    f"#   {PYQ} -m pip config set global.index-url {PIP_INDEX}",
    "# 镜像同步滞后/缺包时才回官方源: 去掉 -i 参数重试",
]


# ── 检查项模型 ───────────────────────────────────────────────────────────────
@dataclass
class Check:
    id: str
    label: str
    why: str                              # 缺了会挂掉哪个能力 (给模型/用户判断优先级)
    probe: Callable[[], tuple[bool, str]]  # → (ok, 细节一行)
    need: str = ""                         # 硬要求一行 ("装什么、什么版本线")
    fix: list[str] = field(default_factory=list)   # 本平台示例命令 (可空)
    cheap: bool = False                   # 毫秒级、不碰网络 → hook 可跑
    auto: bool = False                    # --fix 允许自动执行 (只用户态、幂等)
    slow: bool = False                    # 修复耗时以分钟计, 需要长 timeout
    needs: str = ""                       # 前置检查项 id; 前置失败则本项 skip
    platforms: tuple[str, ...] = ()       # 限定平台 (空 = 全平台)
    env: dict[str, str] = field(default_factory=dict)  # 修复时注入的环境变量 (镜像等)
    soft: bool = False                    # 缺了只降级不致命 (不计入"未就绪"的硬缺口)


@dataclass
class Result:
    check: Check
    status: str   # ok | missing | skip | na
    detail: str


# ── 探测实现 ─────────────────────────────────────────────────────────────────
def probe_py_version() -> tuple[bool, str]:
    v = sys.version_info
    return v >= (3, 10), f"{v.major}.{v.minor}.{v.micro} at {PY}"


def probe_pip() -> tuple[bool, str]:
    """pip must be present AND not locked by PEP 668 (externally-managed),
    otherwise every --fix install silently fails. System Pythons on Debian 12+,
    Ubuntu 23.04+, Homebrew, and slim images are the common offenders."""
    if importlib.util.find_spec("pip") is None:
        return False, "未安装 (python -m pip 不可用)"
    import sysconfig

    candidates = [Path(sys.prefix) / "EXTERNALLY-MANAGED"]
    try:
        stdlib = Path(sysconfig.get_path("stdlib"))
        candidates.append(stdlib / "EXTERNALLY-MANAGED")
        candidates.append(stdlib.parent / "EXTERNALLY-MANAGED")
    except Exception:  # noqa: BLE001
        pass
    for c in candidates:
        try:
            if c.is_file():
                return False, ("外部托管环境 (PEP 668 externally-managed): pip 拒绝直接装包 — "
                               "用 venv/pipx, 或加 --break-system-packages")
        except OSError:
            continue
    return True, f"可用 {_dist_version('pip') or ''}".strip()


def probe_module(mod: str) -> Callable[[], tuple[bool, str]]:
    def _p() -> tuple[bool, str]:
        try:
            spec = importlib.util.find_spec(mod)
        except Exception as e:                       # 包坏了 (半装/依赖缺) 也算缺
            return False, f"find_spec 报错: {e}"
        return bool(spec), (spec.origin or "已装") if spec else "未安装"
    return _p


def _dist_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None


def probe_mcp() -> tuple[bool, str]:
    """mcp 1.x —— server_common.py 用的是 1.x 的 Server.list_tools/call_tool 装饰器
    API, 2.x 改了这套接口, "装了但是大版本不对"会让所有工具消失而不是报错。"""
    if importlib.util.find_spec("mcp") is None:
        return False, "未安装"
    ver = _dist_version("mcp")
    if ver is None:
        return True, "已装 (版本未知)"
    try:
        major = int(ver.split(".")[0])
    except ValueError:
        return True, f"已装 {ver} (版本号无法解析)"
    return major == 1, f"{ver}" + ("" if major == 1 else " [!] 需要 1.x (2.x 改了 Server API)")


def probe_cv2_conflict() -> tuple[bool, str]:
    """opencv-python(GUI) 与 opencv-python-headless 混装 —— 两个包提供同一个 cv2
    目录, pip 不认为它们冲突, 装第二个会覆盖第一个的文件, 结果是 import cv2 成功
    但某些符号缺失/崩在 libGL 上。requirements.txt 只要 headless。"""
    gui, headless = _dist_version("opencv-python"), _dist_version("opencv-python-headless")
    if gui and headless:
        return False, f"同时装了 opencv-python {gui} 和 opencv-python-headless {headless}"
    if gui and not headless:
        return True, f"只有 GUI 版 opencv-python {gui} [!] 无头机器上可能缺 libGL; 建议换 headless"
    return True, f"opencv-python-headless {headless}" if headless else "cv2 来源非 pip (自建/conda), 未见冲突"


def probe_bins(*bins: str) -> Callable[[], tuple[bool, str]]:
    def _p() -> tuple[bool, str]:
        found = {b: shutil.which(b) for b in bins}
        miss = [b for b, p in found.items() if not p]
        if miss:
            return False, "PATH 上找不到: " + " ".join(miss)
        return True, "; ".join(f"{b}={p}" for b, p in found.items())
    return _p


def _ffmpeg_list(kind: str) -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        return ""
    try:
        p = subprocess.run([exe, "-hide_banner", f"-{kind}"],
                           capture_output=True, text=True, timeout=60)
    except Exception:
        return ""
    return p.stdout + p.stderr


def probe_ffmpeg_encoders() -> tuple[bool, str]:
    """要的不是"有 ffmpeg", 而是"这个 ffmpeg 带我们用的编码器"。conda / 静态包的
    ffmpeg 经常裁掉 libx264 或 libmp3lame, 表现是渲染跑到最后一步才炸。"""
    text = _ffmpeg_list("encoders")
    if not text:
        return False, "ffmpeg -encoders 无输出"
    want = {"libx264": "预览/成片视频编码", "aac": "成片音频编码",
            "libmp3lame": "TTS/BGM 中间件 mp3"}
    miss = [f"{k}({v})" for k, v in want.items() if k not in text]
    if miss:
        return False, "缺编码器: " + ", ".join(miss)
    return True, "libx264 / aac / libmp3lame 齐"


def probe_ffmpeg_filters() -> tuple[bool, str]:
    """字幕烧录 = libass(subtitles/ass 滤镜), 标题卡/角标 = libfreetype(drawtext),
    段间溶解 = xfade。这三个缺任何一个都不会在启动时报错, 只会在渲染那一步失败。"""
    text = _ffmpeg_list("filters")
    if not text:
        return False, "ffmpeg -filters 无输出"
    want = {"subtitles": "字幕烧录 (libass)", "ass": "ASS 字幕烧录 (libass)",
            "drawtext": "标题卡/比分角标 (libfreetype)", "xfade": "段间溶解"}
    miss = [f"{k}({v})" for k, v in want.items() if f" {k} " not in text]
    if miss:
        return False, "缺滤镜: " + ", ".join(miss)
    return True, "subtitles / ass / drawtext / xfade 齐"


def _load_kit_module(name: str):
    """import 插件自己的 mcp/ve_tools/<name> —— 体检必须问代码本身, 不许在这里
    另写一份"字体/凭据怎么找"的逻辑 (那必然和渲染时的实际行为漂移)。"""
    sys.path.insert(0, str(PLUGIN_ROOT / "mcp"))
    from importlib import import_module

    return import_module(f"ve_tools.{name}")


def probe_font() -> tuple[bool, str]:
    """本机有没有能真写中文的字体 —— 而且要是**代码那条解析路径**找得到的。

    这里不查"某个目录下有没有某个文件", 而是直接调 ve_tools.fonts, 因为字幕
    分行是拿真字体量出来的, 体检和渲染必须看同一个结果。cmap 真覆盖也要查:
    fc-match 对着没装的中文族会返回 DejaVu, 烧出来是豆腐块但 ffmpeg 退出码 0。
    """
    try:
        fonts = _load_kit_module("fonts")
    except Exception as e:
        return False, f"ve_tools.fonts 不可用: {type(e).__name__}: {e}"
    d = fonts.diagnose()
    if not d["regular"]:
        dirs = ", ".join(d["existing_dirs"]) or "(以上目录都不存在)"
        return False, f"未找到任何中文字体; 已搜: {dirs}"
    covered = d["covers_cjk"]
    tail = (f"; family={d['ass_font_name']}"
            + ("" if covered is not False else " [!] 该字体 cmap 无中文, 会烧成豆腐块"))
    if covered is False:
        return False, f"{d['regular']}{tail}"
    if covered is None:
        # fontTools 还没装 → 覆盖度未知, 但文件在, 不当缺口 (py-fontTools 那项会报)
        return True, f"{d['regular']}{tail} (覆盖度未验证: 缺 fontTools)"
    return True, f"{d['regular']}{tail}"


def _status_line(module: str, func: str, extra: tuple[str, ...]) -> tuple[bool, str]:
    try:
        mod = _load_kit_module(module)
        st = getattr(mod, func)()
    except Exception as e:
        return False, f"状态探测失败: {type(e).__name__}: {e}"
    if st.get("available"):
        bits = [f"{k}={st[k]}" for k in extra if st.get(k)]
        return True, "可用" + (" (" + ", ".join(bits) + ")" if bits else "")
    return False, "; ".join(st.get("reasons") or ["未配置"])


def probe_asr() -> tuple[bool, str]:
    if under_zcode_host():
        return True, "官方通道 (宿主注入身份, 本地无需配置 key)"
    return _status_line("cloud_asr", "cloud_asr_status", ("auth_mode",))


def probe_tts() -> tuple[bool, str]:
    if under_zcode_host():
        return True, "官方通道 (宿主注入身份, 本地无需配置 key)"
    return _status_line("tts", "cloud_tts_status", ("model", "auth_mode"))


def probe_speech_net() -> tuple[bool, str]:
    """直连兼容端点的出网可达性。

    只有部署方显式配了兼容端点时才有意义: 官方通道走 ZCODE_BASE_URL, 远端 Speech MCP
    走 VE_SPEECH_MCP_URL, 两者都不经这个域名。没配就直接判"不适用", 免得体检去连一个
    根本不会被调用的主机, 再把结论报成缺口。

    分两条路, 都必须是**有界**的 (体检不能自己变成两分钟的挂起):
    - 配了 http(s)_proxy: 走 requests, 因为真调用也走代理, 结论才对得上;
      连的是代理那一个地址, 不会一路重试。
    - 没配代理: 自己解析 DNS 再 TCP 连**一个**地址。requests/urllib3 会把每个
      解析出来的 IP 各试一遍 (多 A 记录域名 → 5s×N), 而"通不通"只需要
      一次握手。DNS 失败与端口不通分开报: 前者是解析/网络策略, 后者多半是防火墙。
    """
    if not SPEECH_ENDPOINT:
        return True, "未配置直连兼容端点, 不适用 (官方通道 / 远端 Speech MCP 不经此域名)"
    proxy = next((f"{k}={v}" for k, v in sorted(os.environ.items())
                  if k.lower() in ("https_proxy", "http_proxy") and v), "")
    if proxy:
        try:
            import requests

            resp = requests.get(SPEECH_ENDPOINT, timeout=(5, 10), allow_redirects=False)
        except Exception as e:
            return False, (f"{SPEECH_ENDPOINT_LABEL} 经代理 ({proxy}) 连不上: "
                           f"{type(e).__name__}: {str(e).splitlines()[0][:160]}")
        # 任何 HTTP 响应都算可达: 不带鉴权访问根路径大概率 4xx, 链路照样是通的。
        return True, f"{SPEECH_ENDPOINT_LABEL} HTTP {resp.status_code} (经代理 {proxy})"

    import socket
    from urllib.parse import urlsplit

    parts = urlsplit(SPEECH_ENDPOINT)
    host = parts.hostname or SPEECH_ENDPOINT
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError as e:
        return False, f"{SPEECH_ENDPOINT_LABEL} DNS 解析失败: {e.__class__.__name__}: {e}"
    family, socktype, proto, _, addr = infos[0]
    try:
        with socket.socket(family, socktype, proto) as s:
            s.settimeout(5)
            s.connect(addr)
    except OSError as e:
        return False, (f"{SPEECH_ENDPOINT_LABEL} 连不上: {e.__class__.__name__}: {e}"
                       "; 未检测到 http(s)_proxy 环境变量")
    return True, f"{SPEECH_ENDPOINT_LABEL} 可连 (共 {len(infos)} 个地址)"


def probe_disk() -> tuple[bool, str]:
    target = PROJECT_DIR if PROJECT_DIR.exists() else PROJECT_DIR.parent
    try:
        free_gb = shutil.disk_usage(target).free / 2**30
    except OSError as e:
        return False, f"{target} 无法统计: {e}"
    return (free_gb >= MIN_FREE_GB,
            f"{target} 剩余 {free_gb:.1f}G" + ("" if free_gb >= MIN_FREE_GB else f" (<{MIN_FREE_GB}G)"))


# ── 检查清单 (顺序即展示顺序) ────────────────────────────────────────────────
PY_MODULES = [
    ("requests", "requests>=2.31.0", "cloud ASR / cloud TTS 的 HTTP 调用 — 缺则转录和 TTS 全废"),
    ("cv2", "opencv-python-headless>=4.8.0,<5.0.0", "video_ingest 抽帧 / 局部复看 / QC 扫描"),
    ("numpy", "numpy>=1.24.0", "抽帧索引与帧差计算"),
    ("PIL", "pillow>=10.0.0", "contact sheet 拼图 (模型能看到的那张图)"),
    ("jieba", "jieba>=0.42.1", "subtitle_build 的中文分词/词性 — 缺则字幕断行不可用"),
    ("fontTools", "fonttools>=4.40.0", "字体 cmap 校验 (烧字幕前拦下豆腐块)"),
]

CHECKS: list[Check] = [
    Check("py", "python3 ≥ 3.10", "hook 与 MCP server 用了 3.10+ 运行时语法 (X | Y 类型别名)",
          probe_py_version,
          need="Python 3.10 或更高 (CC 调 hook/MCP 用的就是这个解释器)",
          fix=["# 换一个 3.10+ 解释器, 例如 conda create -n va python=3.12"],
          cheap=True),
    Check("py-pip", "python 包管理: pip (非 PEP 668 外部托管)",
          "所有 auto 修复都靠 pip 装 — pip 缺失或被 externally-managed 拦住时, 一个包都装不上",
          probe_pip,
          need="pip 可用, 且不是 externally-managed 环境 (系统 Python 常被 PEP 668 锁; 用 venv/pipx 最稳)",
          fix=[f"# 推荐: 建虚拟环境再装, 不撞 PEP 668:",
               f"#   {PYQ} -m venv .venv && .venv/bin/python -m pip install -i {PIP_INDEX} -r {REQUIREMENTS}",
               f"# 或对当前解释器强行装 (仅当它是你专用、可被改的环境):",
               f"#   {PYQ} -m pip install -i {PIP_INDEX} --break-system-packages -r {REQUIREMENTS}",
               "# pip 本身缺失时先确保: python -m ensurepip --upgrade"],
          cheap=True, needs="py"),
    Check("py-mcp", "python 包: mcp (1.x)", "MCP server 本体 — 缺则所有剪辑工具都不存在",
          probe_mcp,
          need="pip 包 mcp>=1.0.0,<2.0.0 (装进上面那个解释器, 不是系统里随便哪个 python)",
          fix=[pip_install("mcp>=1.0.0,<2.0.0"), *PIP_MIRROR_NOTES],
          cheap=True, auto=True, slow=True, needs="py-pip"),
    *[Check(f"py-{mod}", f"python 包: {mod}", why, probe_module(mod),
            need=f"pip 包 {pkg} (装进上面那个解释器)",
            fix=[pip_install(pkg), *PIP_MIRROR_NOTES],
            cheap=True, auto=True, slow=True, needs="py-pip")
      for mod, pkg, why in PY_MODULES],
    Check("py-scenedetect", "python 包: scenedetect", "recap 流水线的镜头边界检测 (shots)",
          probe_module("scenedetect"),
          need="pip 包 scenedetect>=0.6, **必须 --no-deps 装** + 它的三个纯 python 依赖",
          fix=[pip_install("click>=8.0", "platformdirs>=3.0", "tqdm>=4.0"),
               pip_install("scenedetect>=0.6", no_deps=True),
               "# --no-deps 不是优化而是硬要求: scenedetect 声明依赖 opencv-python(GUI 版),",
               "#   直装会把 GUI 版盖到 opencv-python-headless 的 cv2 上, 两个包一起坏。",
               *PIP_MIRROR_NOTES],
          cheap=True, auto=True, slow=True, needs="py-pip"),
    Check("cv2-clean", "cv2 无 GUI/headless 混装", "混装会让 cv2 半坏: import 成功但抽帧崩在 libGL",
          probe_cv2_conflict,
          need="只装 opencv-python-headless 一个 (不要同时装 opencv-python)",
          # 卸载是破坏性动作 (可能是别的项目装的), 不自动执行。
          fix=[f"{PYQ} -m pip uninstall -y opencv-python   # 卸 GUI 版, 保留 headless",
               f"{PYQ} -m pip install --force-reinstall -i {PIP_INDEX} "
               '"opencv-python-headless>=4.8.0,<5.0.0"   # 再补回被覆盖的文件'],
          cheap=True, needs="py-cv2"),
    Check("ffmpeg", "ffmpeg + ffprobe", "剪切 / 渲染 / 抽帧 / 时长探测 —— 缺了整条流水线都起不来",
          probe_bins("ffmpeg", "ffprobe"),
          need="ffmpeg (含 ffprobe), 且在 PATH 上 —— 版本不挑, 4.3 起都行 (xfade 要 4.3+)",
          # by_os 的 any 只在"无本平台条目"时回落, 三平台都有条目就会吞掉 conda 行 ——
          # 但 conda 是跨平台最干净的国内源路径 (尤其 Windows, winget 没镜像), 必须显示。
          fix=by_os(
                  macos=["# brew 的 bottle 从 GitHub 下, 国内常慢/失败; 先切清华镜像再装:",
                         f"export HOMEBREW_BOTTLE_DOMAIN={HOMEBREW_BOTTLE}",
                         "brew install ffmpeg"],
                  windows=["# winget 没有镜像概念, ffmpeg 静态包来自 gyan.dev, 国内可能慢;",
                           "winget install --id Gyan.FFmpeg -e",
                           "# 或 choco install ffmpeg / scoop install ffmpeg",
                           "# 装完新开一个终端, 否则 PATH 不刷新"],
                  linux=["sudo apt-get install -y ffmpeg   # apt 源换清华/USTC 镜像更快 (改 sources.list, 系统级改动)"],
              ) + ["# 想走国内镜像 / 无 root / 不动系统包管理器 → 任何平台都用 conda:",
                   f"#   conda install -c {CONDA_FORGE_TSINGHUA} ffmpeg   # 清华镜像"],
          cheap=True),
    Check("ffmpeg-encoders", "ffmpeg 带 libx264/aac/libmp3lame", "渲染最后一步的编码; 缺了前面白跑",
          probe_ffmpeg_encoders,
          need="ffmpeg 编译时带 libx264、aac、libmp3lame (`ffmpeg -encoders` 能看到)",
          fix=by_os(
                  macos=[f"export HOMEBREW_BOTTLE_DOMAIN={HOMEBREW_BOTTLE}",
                         "brew reinstall ffmpeg   # brew 的 ffmpeg 是全功能构建"],
                  windows=["# gyan.dev 的 full 构建带全套; 精简版/自编译版才会缺",
                           "winget install --id Gyan.FFmpeg -e"],
                  linux=["sudo apt-get install -y ffmpeg   # 发行版包一般带全套; 缺的多是自编译/静态包"],
              ) + [f"# 换成 conda-forge 的全功能构建 (跨平台, 走清华镜像):",
                   f"#   conda install -c {CONDA_FORGE_TSINGHUA} ffmpeg",
                   "# 机器上有多个 ffmpeg 时先确认 PATH 上是哪个: 上面探测行里有路径"],
          cheap=True, needs="ffmpeg"),
    Check("ffmpeg-filters", "ffmpeg 带 libass/libfreetype", "字幕烧录 + 标题卡/角标 + 段间溶解",
          probe_ffmpeg_filters,
          need="ffmpeg 编译时带 libass (subtitles/ass 滤镜) 和 libfreetype (drawtext)",
          fix=by_os(
                  macos=[f"export HOMEBREW_BOTTLE_DOMAIN={HOMEBREW_BOTTLE}",
                         "brew reinstall ffmpeg"],
                  windows=["winget install --id Gyan.FFmpeg -e   # full 构建带 libass"],
                  linux=["sudo apt-get install -y ffmpeg   # 若是自编译: 重新 configure 加 --enable-libass --enable-libfreetype"],
              ) + [f"# conda 路线 (跨平台, 清华镜像): conda install -c {CONDA_FORGE_TSINGHUA} ffmpeg",
                   "# 注意: 部分极简/静态构建就是不带 libass, 换构建比补参数省事"],
          cheap=True, needs="ffmpeg"),
    Check("font-cjk", "中文字体 (真能写中文的)", "字幕烧录 / 标题卡 / 比分角标 / contact sheet 标签",
          probe_font,
          need="一个覆盖中日韩字形的字体文件; 首选 Noto Sans CJK, "
               "系统自带的雅黑/苹方/AR PL UMing 也算 (mac/Win 一般已自带)",
          fix=by_os(
                  linux=["sudo apt-get install -y fonts-noto-cjk   # Debian/Ubuntu",
                         "# 或 dnf install google-noto-sans-cjk-fonts / pacman -S noto-fonts-cjk"],
                  macos=["# 系统自带苹方(PingFang.ttc), 正常不会缺; 真缺了再装 Noto:",
                         f"export HOMEBREW_BOTTLE_DOMAIN={HOMEBREW_BOTTLE}",
                         "brew install --cask font-noto-sans-cjk-sc"],
                  windows=["# 系统自带微软雅黑(msyh.ttc), 正常不会缺;",
                           "# 真缺了从 https://github.com/notofonts/noto-cjk 下 NotoSansSC 放进字体目录"],
              ) + ["# 字体装在别处(或想指定用哪个)时, 把目录塞给 VE_FONT_DIRS 即可:",
                   f"#   {'set' if OS == 'windows' else 'export'} VE_FONT_DIRS=<字体目录>"
                   f"   (多个目录用 {os.pathsep!r} 分隔)",
                   "# 无 root 也可以: 下 NotoSansSC-400.ttf/-700.ttf 到任意目录再设 VE_FONT_DIRS"]),
    # 语音凭据永远是 soft 的, 而且在 ZCode 里根本不是一项配置。
    #
    # 默认通道是宿主注入身份的官方 Server MCP —— 本地一个 key 都不需要。独立的 doctor
    # 进程看不到随单次 ``tools/call`` 下发的身份头, 只能看见 ZCODE_BASE_URL 在不在;
    # 因此在 ZCode 里这两项直接报"官方通道", 不去探测兼容后端, 也不摆配置命令。
    # 0.4.2 之前这里会报"凭据未配置"并给出写 .env 的修复命令, 于是模型和用户都以为
    # 必须先在本地配 key 才能转录 —— 那是这条提示造成的错觉, 不是真实约束。
    Check("asr-cred", "语音转录通道", "speech_transcribe — 缺则没有转录, 语音类任务全瘸",
          probe_asr,
          need="ZCode 中无需配置 (宿主注入身份); 其他宿主需远端 Speech MCP, "
               "或直连兼容后端 VE_SPEECH_ASR_ENDPOINT + RESOURCE_ID + API_KEY",
          fix=["# 在 ZCode 中运行时无需任何配置: 官方通道用宿主随调用注入的身份",
               f"# 其他宿主 —— 写进 {PLUGIN_ROOT / '.env'} (插件级默认) 或 {PROJECT_DIR / '.env'} (按项目覆盖):",
               "#   VE_SPEECH_MCP_URL=<remote MCP URL>      # 推荐: 付费能力集中在服务端",
               "#   VE_SPEECH_MCP_TOKEN=<token>",
               "# 或自带直连服务 (端点与资源标识只从进程环境读, 不吃 .env):",
               "#   export VE_SPEECH_ASR_ENDPOINT=<https endpoint>",
               "#   export VE_SPEECH_ASR_RESOURCE_ID=<resource id>",
               "#   VE_SPEECH_ASR_API_KEY=<你的 key>",
               f"# 完整可配置项见 {PLUGIN_ROOT / '.env.example'}; 不要把 key 写进 .env.example"],
          needs="py-requests", soft=True),
    Check("tts-cred", "语音合成通道", "speech_synthesize / 解说旁白合成 — recap 类任务的必需项",
          probe_tts,
          need="ZCode 中无需配置 (宿主注入身份); 其他宿主需远端 Speech MCP, "
               "或直连兼容后端 VE_SPEECH_TTS_ENDPOINT + MODEL + API_KEY",
          fix=["# 在 ZCode 中运行时无需任何配置",
               f"# 其他宿主 —— 同上, 写进 {PLUGIN_ROOT / '.env'}:",
               "#   VE_SPEECH_MCP_URL=<remote MCP URL>",
               "#   VE_SPEECH_MCP_TOKEN=<token>",
               "# 或自带直连服务:",
               "#   export VE_SPEECH_TTS_ENDPOINT=<https endpoint>",
               "#   VE_SPEECH_TTS_MODEL=<model>",
               "#   VE_SPEECH_TTS_API_KEY=<你的 key>",
               "# 只做剪辑/字幕、不做配音的任务可以先不管这项"],
          needs="py-requests", soft=True),
    Check("speech-net", "直连兼容端点可达", "只在自带直连语音服务时适用",
          probe_speech_net,
          need=f"配了直连兼容端点时能访问 {SPEECH_ENDPOINT_LABEL}",
          fix=["# 公司网络/代理下先配代理再重试:",
               *by_os(windows=["#   set HTTPS_PROXY=http://<proxy>:<port>"],
                      any=["#   export https_proxy=http://<proxy>:<port>"]),
               "# 这个域名没有国内镜像可换 (是服务本身); 连不上就是网络策略问题",
               "# 首次经代理的请求偶尔会失败, 配好后重试一次再判断"],
          needs="py-requests", soft=True),
    Check("disk", f"项目盘可用空间 ≥ {MIN_FREE_GB}G", "预览/成片 mp4 + 抽帧图落在项目目录",
          probe_disk,
          need=f"{PROJECT_DIR} 所在盘 ≥ {MIN_FREE_GB}G 空闲 (长视频 recap 要更多)",
          fix=["# 清 out/ 与 .video_agent/ 下的旧产物, 或换一个盘上的工作目录"],
          cheap=True, soft=True),
]

MARK = {"ok": "[+]", "missing": "[!]", "skip": "[~]", "na": "[-]"}


def run_checks(cheap_only: bool = False, only: set[str] | None = None) -> list[Result]:
    results: list[Result] = []
    failed: set[str] = set()
    for c in CHECKS:
        if cheap_only and not c.cheap:
            continue
        if only is not None and c.id not in only:
            continue
        if c.platforms and OS not in c.platforms:
            results.append(Result(c, "na", f"本平台 ({OS}) 不适用, 无需处理"))
            continue
        if c.needs and c.needs in failed:
            results.append(Result(c, "skip", f"前置 {c.needs} 未通过, 跳过"))
            failed.add(c.id)          # 依赖链上的后续项一并跳过
            continue
        try:
            ok, detail = c.probe()
        except Exception as e:         # 探测本身炸了也是环境问题, 不许静默
            ok, detail = False, f"探测异常 {type(e).__name__}: {e}"
        if not ok:
            failed.add(c.id)
        results.append(Result(c, "ok" if ok else "missing", detail))
    return results


def cheap_missing() -> list[str]:
    """SessionStart hook 用: 只跑毫秒级项, 返回 "标签 (为什么需要)" 列表。"""
    return [f"{r.check.label} ({r.check.why})"
            for r in run_checks(cheap_only=True) if r.status == "missing"]


def credential_lines() -> list[str]:
    """SessionStart hook 用: 转录/合成通道一行一条 (不碰网络, 只看配置)。

    在 ZCode 里这两行报的是"官方通道就绪"。措辞要紧: 上一版这里会打
    "ASR: cloud_asr 不可用: credentials not set ...", 每个会话开头都摆在模型面前,
    于是模型把"去配一个 key"当成任务第一步 —— 而实际上官方通道本来就能用。
    """
    lines = []
    for label, probe in (("ASR (speech_transcribe):", probe_asr), ("TTS (speech_synthesize):", probe_tts)):
        try:
            ok, detail = probe()
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"
        if ok:
            lines.append(f"{label} {detail}")
        else:
            lines.append(
                f"{label} 未就绪: {detail}"
                " — 本地不需要 key; 在 ZCode 中运行即走官方通道, 其他宿主见 /env-check"
            )
    return lines


def render(results: list[Result]) -> str:
    lines = [f"[env] video-agent-kit 环境体检 (平台 {OS}; 解释器 {PY})"]
    for r in results:
        lines.append(f"  {MARK[r.status]} {r.check.label:30} {r.detail}")
    # na = 本平台不适用, 不是缺口 —— 不计进未就绪
    bad = [r for r in results if r.status in ("missing", "skip")]
    if not bad:
        lines.append("[env] 全部就绪 — 无需安装。")
        return "\n".join(lines)

    hard = [r for r in bad if not r.check.soft]
    lines.append(f"[env] {len(bad)}/{len(results)} 项未就绪"
                 + (f" (其中 {len(hard)} 项是硬缺口)" if len(hard) != len(bad) else "")
                 + "。下面每项先说**要什么**, 再给本平台的示例命令 "
                   "(用你惯用的装法也行, 要求才是硬的):")
    for i, r in enumerate(bad, 1):
        if r.status == "skip":
            # 没真探测过 → 不摆修复命令, 免得照着装一个可能压根不缺的东西
            lines.append(f"  {i}. {r.check.label} [未探测: 前置 {r.check.needs} 没过] — "
                         f"{r.check.why}; 修好前置后重跑本脚本")
            continue
        tag = "自动可装" if r.check.auto else "要你自己装"
        if r.check.soft:
            tag += ", 只降级不致命"
        if r.check.slow:
            tag += ", 耗时数分钟 → Bash timeout 拉到 600000"
        lines.append(f"  {i}. {r.check.label} [{tag}] — 缺了挂: {r.check.why}")
        if r.check.need:
            lines.append(f"       需要: {r.check.need}")
        for cmd in r.check.fix:
            lines.append(f"       {cmd}")
    if any(r.check.auto for r in bad if r.status == "missing"):
        lines.append(f"[env] 自动项可一把过: python3 {Path(__file__).name} --fix "
                     "(只跑上面标 自动可装 的命令)")
        if REQUIREMENTS.is_file():
            lines.append(f"[env] 也可以照 requirements.txt 一次装齐 pip 依赖: "
                         f"{PYQ} -m pip install -i {PIP_INDEX} -r {REQUIREMENTS} "
                         f"&& {PYQ} -m pip install -i {PIP_INDEX} --no-deps \"scenedetect>=0.6\"")
    return "\n".join(lines)


def do_fix(results: list[Result]) -> list[Result]:
    """跑 auto 项的修复命令, 然后只复测这些项。非 auto 项一律不碰。"""
    todo = [r for r in results if r.status == "missing" and r.check.auto]
    if not todo:
        print("[env] 没有可自动装的项 (剩下的要你自己装, 见上面的『需要』行)。")
        return results
    fixed: set[str] = set()
    for r in todo:
        env = {**os.environ, **r.check.env} if r.check.env else None
        for cmd in r.check.fix:
            if cmd.lstrip().startswith("#"):
                continue
            print(f"[env] $ {cmd}", flush=True)
            p = subprocess.run(cmd, shell=True, timeout=1800, env=env)
            if p.returncode != 0:
                print(f"[env] [!] 失败 (退出码 {p.returncode}): {r.check.label} — "
                      "先看上面的报错; 常见根因: externally-managed (PEP 668, 用 venv/"
                      "--break-system-packages)、镜像源/代理、或 pip 权限不足",
                      flush=True)
                break
        else:
            fixed.add(r.check.id)
    if not fixed:
        return results
    recheck = {res.check.id: res for res in run_checks(only=fixed)}
    return [recheck.get(r.check.id, r) for r in results]


def main() -> int:
    # On Windows the locale encoding (cp936 etc.) cannot encode some symbols;
    # force UTF-8 with errors="replace" so a diagnostic never dies as a
    # UnicodeEncodeError.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description="video-agent-kit 环境体检")
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    ap.add_argument("--cheap", action="store_true", help="只跑毫秒级项 (hook 用)")
    ap.add_argument("--fix", action="store_true", help="自动安装 auto 项后复测")
    args = ap.parse_args()

    results = run_checks(cheap_only=args.cheap)
    if args.fix:
        results = do_fix(results)

    payload = {"plugin_root": str(PLUGIN_ROOT),
               "platform": OS,
               "python": PY,
               "pip_index": PIP_INDEX,
               "checks": [{"id": r.check.id, "label": r.check.label,
                           "status": r.status, "detail": r.detail,
                           "why": r.check.why, "need": r.check.need,
                           "auto": r.check.auto, "soft": r.check.soft,
                           "fix": r.check.fix if r.status == "missing" else []}
                          for r in results]}
    # na (本平台不适用) 不算缺口; skip (前置没过) 算 —— 它背后有个真缺口没修
    payload["missing"] = [c["id"] for c in payload["checks"]
                          if c["status"] in ("missing", "skip")]
    payload["blocking"] = [c["id"] for c in payload["checks"]
                           if c["status"] in ("missing", "skip") and not c["soft"]]

    # 落回执: 下一轮/别的会话不用重跑一遍全量探测就知道上次结论。
    try:
        out = PROJECT_DIR / ".video_agent"
        out.mkdir(parents=True, exist_ok=True)
        (out / "env_report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass

    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json
          else render(results))
    return 1 if payload["blocking"] else 0


if __name__ == "__main__":
    sys.exit(main())
