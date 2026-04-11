from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import base64
import hashlib
import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"
CONFIG_DIR = SKILL_DIR / "config"

DEFAULT_PROFILE_PATH = CONFIG_DIR / "api_profile.json"
MAX_SUMMARY_CHARS = 18000
MAX_SECTION_TITLES = 10
MAX_SOURCE_SNIPPETS = 8
MAX_SOURCE_SNIPPET_CHARS = 700
KDF_ITERATIONS = 300000


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def unique_preserve_order(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def truncate_paragraphs(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    paragraphs = [segment.strip() for segment in re.split(r"\n{2,}", text) if segment.strip()]
    collected: List[str] = []
    total = 0
    for paragraph in paragraphs:
        separator = 2 if collected else 0
        next_total = total + len(paragraph) + separator
        if next_total <= limit:
            collected.append(paragraph)
            total = next_total
            continue
        remaining = limit - total - separator
        if remaining > 120:
            collected.append(paragraph[:remaining].rstrip() + "…")
        break
    return "\n\n".join(collected).strip()


def make_script_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def infer_theme(html_text: str) -> str:
    lowered = html_text.lower()
    if "noto serif sc" in lowered or "songti sc" in lowered or "☯️" in html_text:
        return "ink"
    return "modern"


def extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string and soup.title.string.strip():
        return soup.title.string.strip()
    heading = soup.find(["h1", "h2"])
    if heading:
        return heading.get_text(" ", strip=True)
    return "Interactive Knowledge Lesson"


def select_analysis_root(soup: BeautifulSoup):
    selectors = [
        {"id": "content-area"},
        {"name": "main"},
        {"name": "article"},
        {"id": "overview"},
        {"name": "body"},
    ]
    for selector in selectors:
        if "id" in selector:
            node = soup.find(id=selector["id"])
        else:
            node = soup.find(selector["name"])
        if node is not None:
            return node
    return soup


def prune_noise(root: BeautifulSoup) -> None:
    for tag in root.select(
        "script, style, noscript, nav, footer, aside, form, button, input, textarea, svg, canvas, iframe"
    ):
        tag.decompose()
    for tag in root.select("#mentor-classroom, #mentor-connect-panel, #mentor-assessment-panel, #mentor-feedback-panel, #mentor-chat-panel"):
        tag.decompose()


def extract_section_titles(root: BeautifulSoup) -> List[str]:
    titles = [
        element.get_text(" ", strip=True)
        for element in root.find_all(["h1", "h2", "h3"])
    ]
    cleaned = []
    for title in titles:
        if len(title) < 2:
            continue
        cleaned.append(title)
    return unique_preserve_order(cleaned)[:MAX_SECTION_TITLES]


def extract_summary_text(html_text: str) -> Tuple[str, List[str], str]:
    analysis_soup = BeautifulSoup(html_text, "html.parser")
    root = select_analysis_root(analysis_soup)
    section_titles = extract_section_titles(root)
    prune_noise(root)
    summary_text = normalize_whitespace(root.get_text("\n", strip=True))
    summary_text = truncate_paragraphs(summary_text, MAX_SUMMARY_CHARS)
    title = extract_title(analysis_soup)
    return title, section_titles, summary_text


def score_source_block(block: str) -> int:
    lowered = block.lower()
    length = len(block)
    score = 0
    if 120 <= length <= 700:
        score += 5
    elif 80 <= length <= 900:
        score += 3
    else:
        score -= 1
    if any(marker in block for marker in ["。", ".", "：", ":", "？", "?", "!", "！"]):
        score += 2
    if lowered.startswith(("http", "title:", "url:", "source", "来源", "作者")):
        score -= 4
    if "===" in block or "[system" in lowered:
        score -= 4
    if re.search(r"[\u4e00-\u9fffA-Za-z]{20,}", block):
        score += 2
    if len(set(block.split())) < 10:
        score -= 2
    return score


def extract_source_snippets(raw_text: str) -> List[Dict[str, str]]:
    blocks = [
        normalize_whitespace(block)
        for block in re.split(r"\n\s*\n+", raw_text.replace("\r\n", "\n"))
    ]
    filtered: List[Tuple[int, int, str]] = []
    seen = set()
    for index, block in enumerate(blocks):
        if not block:
            continue
        shortened = block[:MAX_SOURCE_SNIPPET_CHARS].strip()
        key = shortened.lower()
        if key in seen:
            continue
        seen.add(key)
        filtered.append((score_source_block(shortened), index, shortened))
    filtered.sort(key=lambda item: (-item[0], item[1]))
    chosen = sorted(filtered[:MAX_SOURCE_SNIPPETS], key=lambda item: item[1])
    snippets = []
    for index, (_, _, snippet_text) in enumerate(chosen, start=1):
        snippets.append({"id": f"src{index}", "text": snippet_text})
    if snippets:
        return snippets
    fallback = [block[:MAX_SOURCE_SNIPPET_CHARS] for block in blocks if block][:3]
    return [{"id": f"src{index}", "text": value} for index, value in enumerate(fallback, start=1)]


def derive_self_test_seed(section_titles: Sequence[str], summary_text: str) -> List[str]:
    seeds = list(section_titles[:6])
    if len(seeds) >= 5:
        return seeds
    sentence_candidates = [
        normalize_whitespace(sentence)
        for sentence in re.split(r"[。！？!?\n]", summary_text)
    ]
    for sentence in sentence_candidates:
        if len(sentence) < 12:
            continue
        if sentence in seeds:
            continue
        seeds.append(sentence[:60])
        if len(seeds) >= 8:
            break
    return unique_preserve_order(seeds)[:8]


def load_profile(profile_path: Path) -> Dict[str, str]:
    profile_data = json.loads(read_text_file(profile_path))
    profile = profile_data.get("default_profile")
    if not isinstance(profile, dict):
        raise ValueError("profile file must contain a default_profile object")
    required_keys = ["label", "base_url", "model", "api_key"]
    missing = [key for key in required_keys if not str(profile.get(key, "")).strip()]
    if missing:
        raise ValueError(f"profile file is missing keys: {', '.join(missing)}")
    return {
        "label": str(profile["label"]).strip(),
        "base_url": str(profile["base_url"]).strip(),
        "model": str(profile["model"]).strip(),
        "api_key": str(profile["api_key"]).strip(),
    }


def encrypt_profile(profile: Dict[str, str], unlock_pass: str) -> Dict[str, Any]:
    payload = json.dumps(
        {
            "base_url": profile["base_url"],
            "model": profile["model"],
            "api_key": profile["api_key"],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        unlock_pass.encode("utf-8"),
        salt,
        KDF_ITERATIONS,
        dklen=32,
    )
    ciphertext = AESGCM(key).encrypt(iv, payload, None)
    return {
        "version": 1,
        "label": profile["label"],
        "algorithm": "AES-GCM",
        "kdf": "PBKDF2-SHA256",
        "iterations": KDF_ITERATIONS,
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "iv_b64": base64.b64encode(iv).decode("ascii"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
    }


def ensure_document_shell(soup: BeautifulSoup) -> None:
    if soup.html is None:
        html_tag = soup.new_tag("html")
        soup.append(html_tag)
        existing = list(soup.contents)
        for node in existing:
            if node is html_tag:
                continue
            html_tag.append(node.extract())
    if soup.head is None:
        head_tag = soup.new_tag("head")
        if soup.html:
            soup.html.insert(0, head_tag)
    if soup.body is None:
        body_tag = soup.new_tag("body")
        if soup.html:
            soup.html.append(body_tag)


def remove_existing_enhancement(soup: BeautifulSoup) -> None:
    removable_ids = [
        "mentor-classroom",
        "ka-course-payload",
        "ka-encrypted-profile",
        "ka-runtime-options",
        "ka-mentor-prompts",
        "ka-mentor-style",
        "ka-mentor-runtime",
    ]
    for node_id in removable_ids:
        node = soup.find(id=node_id)
        if node is not None:
            node.decompose()


def build_runtime_options(mode: str, has_injected_profile: bool) -> Dict[str, Any]:
    allow_manual = mode in {"manual", "both"}
    allow_injected = has_injected_profile and mode in {"injected", "both"}
    return {
        "version": 1,
        "mode": mode,
        "allow_manual": allow_manual,
        "allow_injected": allow_injected,
        "relay_url": "http://127.0.0.1:8760",
    }


def build_classroom_markup(mode: str, has_injected_profile: bool) -> str:
    manual_note = "可手动填写 OpenAI 兼容接口参数。" if mode in {"manual", "both"} else "当前课件未启用手动连接。"
    injected_note = (
        "输入打包时设置的解锁口令后，可直接使用预置连接。"
        if has_injected_profile
        else "当前课件没有嵌入默认连接配置。"
    )
    return f"""
<button id=\"mentor-sidebar-toggle\" class=\"mentor-toolbar-button\" type=\"button\" aria-controls=\"mentor-classroom\" aria-expanded=\"false\">导师模式</button>
<div id=\"mentor-sidebar-backdrop\" class=\"mentor-backdrop mentor-hidden\"></div>
<aside id=\"mentor-classroom\" class=\"mentor-shell mentor-sidebar\" aria-hidden=\"true\">
  <div class=\"mentor-sidebar-header\">
    <div>
      <p class=\"mentor-kicker\">Mentor Classroom</p>
      <h2>导师课堂</h2>
      <p id=\"mentor-classroom-intro\" class=\"mentor-muted\"></p>
    </div>
    <button id=\"mentor-sidebar-close\" class=\"mentor-icon-button\" type=\"button\" aria-label=\"收起导师模式\">×</button>
  </div>
  <div class=\"mentor-pill-list mentor-pill-list-sidebar\">
    <span class=\"mentor-pill\">先完整学习</span>
    <span class=\"mentor-pill\">再诊断测验</span>
    <span class=\"mentor-pill\">错题补讲</span>
    <span class=\"mentor-pill\">继续问老师</span>
  </div>

  <div id=\"mentor-connect-panel\" class=\"mentor-card mentor-card-compact\">
    <div class=\"mentor-section-head\">
      <div>
        <h3>连接模型</h3>
        <p class=\"mentor-muted\">先完成连接，再开始诊断式测验。</p>
      </div>
    </div>
    <div class=\"mentor-connect-grid\">
      <div id=\"mentor-manual-card\" class=\"mentor-method\">
        <h4>手动填写</h4>
        <p class=\"mentor-muted\">{manual_note}</p>
        <label class=\"mentor-label\" for=\"mentor-base-url\">Base URL 或完整 Endpoint</label>
        <input id=\"mentor-base-url\" class=\"mentor-input\" type=\"text\" placeholder=\"https://api.openai.com/v1 或 https://api.openai.com/v1/chat/completions\">
        <label class=\"mentor-label\" for=\"mentor-model\">Model</label>
        <input id=\"mentor-model\" class=\"mentor-input\" type=\"text\" placeholder=\"gpt-4.1-mini\">
        <label class=\"mentor-label\" for=\"mentor-api-key\">API Key</label>
        <input id=\"mentor-api-key\" class=\"mentor-input\" type=\"password\" placeholder=\"sk-...\">
        <button id=\"mentor-manual-connect\" class=\"mentor-button mentor-button-primary\" type=\"button\">使用手动连接</button>
      </div>

      <div id=\"mentor-injected-card\" class=\"mentor-method\">
        <h4>解锁默认配置</h4>
        <p class=\"mentor-muted\">{injected_note}</p>
        <label class=\"mentor-label\" for=\"mentor-unlock-password\">解锁口令</label>
        <input id=\"mentor-unlock-password\" class=\"mentor-input\" type=\"password\" placeholder=\"输入打包时设置的口令\">
        <button id=\"mentor-unlock-button\" class=\"mentor-button\" type=\"button\">解锁默认连接</button>
      </div>
    </div>
    <div id=\"mentor-connection-status\" class=\"mentor-status\">尚未连接模型接口。</div>
    <div class=\"mentor-action-row\">
      <button id=\"mentor-test-connection\" class=\"mentor-button mentor-button-secondary\" type=\"button\">测试连接</button>
    </div>
  </div>

  <div id=\"mentor-assessment-panel\" class=\"mentor-card mentor-card-compact\">
    <div class=\"mentor-section-head\">
      <div>
        <h3>诊断式测验</h3>
        <p class=\"mentor-muted\">系统会基于当前课件内容生成 6 题测验，并在交卷后给出讲评与补讲。</p>
      </div>
      <button id=\"mentor-generate-quiz\" class=\"mentor-button mentor-button-primary\" type=\"button\" disabled>开始 6 题诊断</button>
    </div>
    <div id=\"mentor-quiz-status\" class=\"mentor-status mentor-status-inline\">等待开始。</div>
    <div id=\"mentor-quiz-container\" class=\"mentor-empty\">暂无题目。连接模型后点击开始。</div>
  </div>

  <div id=\"mentor-feedback-panel\" class=\"mentor-card mentor-card-compact\">
    <div class=\"mentor-section-head\">
      <div>
        <h3>讲评与补讲</h3>
        <p class=\"mentor-muted\">这里会显示总体掌握度、逐题讲评、薄弱点补讲与追问。</p>
      </div>
    </div>
    <div id=\"mentor-feedback-overall\" class=\"mentor-empty\">提交答案后显示总体讲评。</div>
    <div id=\"mentor-feedback-items\" class=\"mentor-stack\"></div>
    <div id=\"mentor-follow-up-container\" class=\"mentor-stack\"></div>
  </div>

  <div id=\"mentor-chat-panel\" class=\"mentor-card mentor-card-compact\">
    <div class=\"mentor-section-head\">
      <div>
        <h3>问老师</h3>
        <p class=\"mentor-muted\">只围绕当前课件内容追问。若课件未覆盖，老师会明确告诉你边界。</p>
      </div>
    </div>
    <div id=\"mentor-chat-log\" class=\"mentor-chat-log\">
      <div class=\"mentor-chat-placeholder\">连接模型后，就可以继续提问这份课件的内容。</div>
    </div>
    <label class=\"mentor-label\" for=\"mentor-chat-input\">你的问题</label>
    <textarea id=\"mentor-chat-input\" class=\"mentor-textarea\" rows=\"4\" placeholder=\"比如：请把这个概念再用更白话的方式讲一次\"></textarea>
    <div class=\"mentor-action-row\">
      <button id=\"mentor-chat-send\" class=\"mentor-button mentor-button-primary\" type=\"button\" disabled>问老师</button>
    </div>
  </div>
</aside>
"""


def inject_enhancement(
    original_html: str,
    payload: Dict[str, Any],
    runtime_options: Dict[str, Any],
    mentor_prompts: Dict[str, Any],
    mentor_css: str,
    mentor_js: str,
    encrypted_profile: Optional[Dict[str, Any]],
) -> str:
    soup = BeautifulSoup(original_html, "html.parser")
    ensure_document_shell(soup)
    remove_existing_enhancement(soup)

    style_tag = soup.new_tag("style", id="ka-mentor-style")
    style_tag.string = mentor_css
    soup.head.append(style_tag)

    classroom_fragment = BeautifulSoup(
        build_classroom_markup(runtime_options["mode"], bool(encrypted_profile)),
        "html.parser",
    )

    toggle_button = classroom_fragment.find(id="mentor-sidebar-toggle")
    backdrop = classroom_fragment.find(id="mentor-sidebar-backdrop")
    sidebar = classroom_fragment.find(id="mentor-classroom")

    toolbar_actions = soup.find(id="knowledge-toolbar-actions")
    if toggle_button is not None:
        if toolbar_actions is not None:
            toolbar_actions.append(toggle_button)
        else:
            soup.body.append(toggle_button)

    if backdrop is not None:
        soup.body.append(backdrop)
    if sidebar is not None:
        soup.body.append(sidebar)

    payload_tag = soup.new_tag("script", id="ka-course-payload", type="application/json")
    payload_tag.string = make_script_json(payload)
    soup.body.append(payload_tag)

    runtime_tag = soup.new_tag("script", id="ka-runtime-options", type="application/json")
    runtime_tag.string = make_script_json(runtime_options)
    soup.body.append(runtime_tag)

    prompts_tag = soup.new_tag("script", id="ka-mentor-prompts", type="application/json")
    prompts_tag.string = make_script_json(mentor_prompts)
    soup.body.append(prompts_tag)

    if encrypted_profile is not None:
        encrypted_tag = soup.new_tag("script", id="ka-encrypted-profile", type="application/json")
        encrypted_tag.string = make_script_json(encrypted_profile)
        soup.body.append(encrypted_tag)

    runtime_script = soup.new_tag("script", id="ka-mentor-runtime")
    runtime_script.string = mentor_js
    soup.body.append(runtime_script)
    return str(soup)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package a summary HTML file into an interactive mentor lesson.")
    parser.add_argument("--input-html", required=True, help="Path to the source summary HTML file.")
    parser.add_argument("--raw-content", required=True, help="Path to the raw content text file.")
    parser.add_argument("--output", required=True, help="Path to the interactive HTML output.")
    parser.add_argument(
        "--profile-file",
        default=str(DEFAULT_PROFILE_PATH),
        help="Path to the optional API profile JSON file.",
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "injected", "both"],
        default="both",
        help="Which connection methods should be available in the final lesson.",
    )
    parser.add_argument(
        "--unlock-pass",
        default="",
        help="Passphrase used to encrypt the injected API profile when injected access is enabled.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_html_path = Path(args.input_html).resolve()
    raw_content_path = Path(args.raw_content).resolve()
    output_path = Path(args.output).resolve()
    profile_path = Path(args.profile_file).resolve()

    if not input_html_path.exists():
        raise FileNotFoundError(f"input HTML not found: {input_html_path}")
    if not raw_content_path.exists():
        raise FileNotFoundError(f"raw content not found: {raw_content_path}")
    if input_html_path == output_path:
        raise ValueError("output path must be different from input HTML path")

    original_html = read_text_file(input_html_path)
    raw_text = read_text_file(raw_content_path)

    title, section_titles, summary_text = extract_summary_text(original_html)
    source_snippets = extract_source_snippets(raw_text)
    self_test_seed = derive_self_test_seed(section_titles, summary_text)
    theme = infer_theme(original_html)

    payload = {
        "version": 1,
        "title": title,
        "summary_text": summary_text,
        "section_titles": section_titles,
        "source_snippets": source_snippets,
        "self_test_seed": self_test_seed,
        "meta": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "theme": theme,
        },
    }

    encrypted_profile: Optional[Dict[str, Any]] = None
    if args.mode in {"injected", "both"}:
        if profile_path.exists():
            if not args.unlock_pass:
                raise ValueError("--unlock-pass is required when injected access is enabled and a profile file is present")
            encrypted_profile = encrypt_profile(load_profile(profile_path), args.unlock_pass)
        elif args.mode == "injected":
            raise FileNotFoundError(f"profile file not found: {profile_path}")

    runtime_options = build_runtime_options(args.mode, bool(encrypted_profile))
    mentor_css = read_text_file(ASSETS_DIR / "mentor_runtime.css")
    mentor_js = read_text_file(ASSETS_DIR / "mentor_runtime.js")
    mentor_prompts = json.loads(read_text_file(ASSETS_DIR / "mentor_prompts.json"))

    enhanced_html = inject_enhancement(
        original_html=original_html,
        payload=payload,
        runtime_options=runtime_options,
        mentor_prompts=mentor_prompts,
        mentor_css=mentor_css,
        mentor_js=mentor_js,
        encrypted_profile=encrypted_profile,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(enhanced_html, encoding="utf-8")

    print(f"Interactive mentor lesson saved to: {output_path}")
    print(f"Connection modes: manual={runtime_options['allow_manual']} injected={runtime_options['allow_injected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
