from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
DEFAULT_RAW_PATH = CONFIG_DIR / "raw_content.txt"
DEFAULT_OUTPUT_PATH = CONFIG_DIR / "raw_content.audit.json"
NOISE_PATTERNS = [
    "关注",
    "推荐",
    "热榜",
    "专栏",
    "圈子New",
    "付费咨询",
    "知学堂",
    "切换模式",
    "登录/注册",
    "直答",
    "点赞",
    "收藏",
    "转发",
    "分享",
    "订阅",
    "广告",
    "赞助",
]
NOISE_SUBSTRINGS = [
    "下载知乎App",
    "打开知乎App",
    "验证码登录",
    "密码登录",
    "获取短信验证码",
    "获取语音验证码",
    "其他方式登录",
    "登录即可查看",
    "扫码下载知乎 App",
    "开通机构号",
    "无障碍模式",
    "中国 +86",
    "关注我们",
    "加入我们",
    "联系我们",
    "更多内容",
    "查看更多",
    "展开全文",
    "收起",
    "相关推荐",
    "猜你喜欢",
    "热门文章",
    "最新文章",
    "阅读全文",
    "继续阅读",
    "立即下载",
    "立即注册",
    "免费试用",
    "立即购买",
    "了解更多",
    "点击这里",
    "微信扫码",
    "支付宝",
    "微信支付",
    "谢谢大佬的支持",
]
HEADING_STOPWORDS = {
    "目录",
    "推荐阅读",
    "社区首页",
    "发布于",
    "评论",
    "热度",
    "最新",
    "热门产品",
    "热门推荐",
    "更多推荐",
    "腾讯云开发者",
}
TIME_PATTERN = re.compile(r"\b(19|20)\d{2}\b|今天|昨日|最近|目前|当前|latest|recent|today|yesterday", re.IGNORECASE)
VERSION_PATTERN = re.compile(r"\bv\d+(?:\.\d+){0,2}\b|版本|release|api|sdk|model|接口", re.IGNORECASE)
ABSOLUTE_PATTERN = re.compile(r"总是|从不|必须|唯一|最好|最强|永远|always|never|must|best|only", re.IGNORECASE)
PLACEHOLDER_VALUES = {"", "none", "null", "untitled", "unknown", "nan"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalize(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_meaningful_text(text: str) -> str:
    cleaned = normalize(text).strip("* ")
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    if cleaned.lower() in PLACEHOLDER_VALUES:
        return ""
    return cleaned


def extract_source_header(raw_text: str) -> Dict[str, str]:
    title_match = re.search(r"^Title:\s*(.+)$", raw_text, re.MULTILINE)
    author_match = re.search(r"^Author:\s*(.+)$", raw_text, re.MULTILINE)
    source_match = re.search(r"^--- SOURCE 1:\s*(.+?)\s*---$", raw_text, re.MULTILINE)
    file_match = re.search(r"^=== FILE:\s*(.+?)\s*===$", raw_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    title = re.sub(r"\s*-\s*知乎$", "", title)
    title = normalize_meaningful_text(title)
    return {
        "title": title,
        "author": normalize_meaningful_text(author_match.group(1).strip()) if author_match else "Unknown",
        "url": source_match.group(1).strip() if source_match else "",
        "file": file_match.group(1).strip() if file_match else "",
    }


def extract_content_block(raw_text: str) -> str:
    marker = "=== CONTENT ==="
    if marker not in raw_text:
        return raw_text
    return raw_text.split(marker, 1)[1]


def parse_sources(raw_text: str) -> List[Dict[str, str]]:
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    pattern = re.compile(
        r"--- SOURCE\s+(\d+):\s*(.+?)\s*---\s*=+\s*(.*?)(?=(?:\n=+\n--- SOURCE\s+\d+:)|\Z)",
        flags=re.DOTALL,
    )
    sources: List[Dict[str, str]] = []
    for match in pattern.finditer(normalized):
        source_id, source_path, payload = match.groups()
        title_match = re.search(r"^Title:\s*(.+)$", payload, re.MULTILINE)
        author_match = re.search(r"^Author:\s*(.+)$", payload, re.MULTILINE)
        source_match = re.search(r"^Source:\s*(.+)$", payload, re.MULTILINE)
        date_match = re.search(r"^Date:\s*(.+)$", payload, re.MULTILINE)
        content = extract_content_block(payload)
        sources.append(
            {
                "source_id": source_id.strip(),
                "path": source_path.strip(),
                "title": normalize(title_match.group(1)) if title_match else Path(source_path.strip()).name,
                "author": normalize(author_match.group(1)) if author_match else "Unknown",
                "source": normalize(source_match.group(1)) if source_match else "",
                "date": normalize(date_match.group(1)) if date_match else "",
                "content": normalize(content),
            }
        )
    if sources:
        return sources
    return [
        {
            "source_id": "1",
            "path": "",
            "title": extract_source_header(raw_text).get("title") or "",
            "author": extract_source_header(raw_text).get("author") or "Unknown",
            "source": "",
            "date": "",
            "content": normalize(extract_content_block(raw_text)),
        }
    ]


def markdown_link_to_text(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\(<[^>]*>\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[]\(<[^>]*>\)", "", text)
    return text


def looks_noisy(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("![") or stripped.startswith("[](") or stripped.startswith("http"):
        return True
    if stripped in NOISE_PATTERNS:
        return True
    if any(token in stripped for token in NOISE_SUBSTRINGS):
        return True
    if sum(1 for token in NOISE_PATTERNS if token in stripped) >= 2 and len(stripped) <= 40:
        return True
    if len(stripped) <= 2 and not stripped.startswith("#"):
        return True
    return False


def clean_lines(raw_text: str) -> Tuple[List[str], List[str]]:
    content = markdown_link_to_text(extract_content_block(raw_text))
    lines = [normalize(line) for line in content.splitlines()]
    cleaned: List[str] = []
    noise: List[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                cleaned.append("")
            blank = True
            continue
        if looks_noisy(line):
            noise.append(line)
            continue
        if re.fullmatch(r"[\W_]+", line):
            noise.append(line)
            continue
        cleaned.append(line)
        blank = False
    return cleaned, noise


def extract_headings(lines: Sequence[str]) -> List[Dict[str, object]]:
    headings: List[Dict[str, object]] = []
    for line in lines:
        if not line.startswith("#"):
            continue
        level = len(line) - len(line.lstrip("#"))
        text = re.sub(r"^#+\s*", "", line).strip("* ")
        if text:
            headings.append({"level": level, "text": text})
    return headings


def paragraph_blocks(lines: Sequence[str]) -> List[str]:
    blocks: List[str] = []
    current: List[str] = []
    for line in lines:
        if not line:
            if current:
                blocks.append(normalize(" ".join(current)))
                current = []
            continue
        if line.startswith("#"):
            if current:
                blocks.append(normalize(" ".join(current)))
                current = []
            blocks.append(re.sub(r"^#+\s*", "", line).strip("* "))
            continue
        current.append(line)
    if current:
        blocks.append(normalize(" ".join(current)))
    return [block for block in blocks if block]


def split_sentences(text: str) -> List[str]:
    normalized = normalize(text)
    if not normalized:
        return []
    pieces = re.split(r"(?<=[。！？!?])\s+|(?<=\.)\s+(?=[A-Z0-9\u4e00-\u9fff])", normalized)
    return [piece.strip() for piece in pieces if piece and piece.strip()]


def unique_preserve_order(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def extract_keywords(text: str) -> List[str]:
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    latin_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+_.-]{2,}", text)
    results: List[str] = []
    seen = set()
    for token in [*chinese_tokens, *latin_tokens]:
        cleaned = normalize(token)
        if len(cleaned) < 2:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        results.append(cleaned)
    return results


def clean_heading_keywords(headings: Sequence[Dict[str, object]]) -> List[str]:
    keywords: List[str] = []
    for heading in headings:
        if not isinstance(heading, dict):
            continue
        heading_text = normalize(str(heading.get("text") or ""))
        if not heading_text or heading_text in HEADING_STOPWORDS:
            continue
        if any(stopword in heading_text for stopword in HEADING_STOPWORDS):
            continue
        keywords.extend(extract_keywords(heading_text))
    return unique_preserve_order(keywords)[:16]


def clean_quote_keywords(quotes: Sequence[str]) -> List[str]:
    keywords: List[str] = []
    for quote in quotes:
        cleaned = normalize(quote)
        if not cleaned:
            continue
        if any(token in cleaned for token in ["Copyright", "版权所有", "评论", "推荐阅读", "热门"]):
            continue
        keywords.extend(extract_keywords(cleaned))
    return unique_preserve_order(keywords)[:16]


def extract_urls(text: str) -> List[str]:
    matches = re.findall(r"https?://[^\s\]>'\")]+", text, flags=re.IGNORECASE)
    return unique_preserve_order([match.rstrip(".,;)") for match in matches])


def select_key_quotes(paragraphs: Sequence[str]) -> List[str]:
    scored: List[Tuple[int, str]] = []
    for paragraph in paragraphs:
        length = len(paragraph)
        if length < 40:
            continue
        score = 0
        if 60 <= length <= 240:
            score += 4
        if "：" in paragraph or ":" in paragraph:
            score += 2
        if ABSOLUTE_PATTERN.search(paragraph):
            score += 1
        if TIME_PATTERN.search(paragraph) or VERSION_PATTERN.search(paragraph):
            score += 2
        scored.append((score, paragraph))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [item[1] for item in scored[:8]] or list(paragraphs[:5])


def select_claim_candidates(paragraphs: Sequence[str]) -> List[Dict[str, str]]:
    candidates: List[str] = []
    for paragraph in paragraphs[:40]:
        for sentence in split_sentences(paragraph):
            length = len(sentence)
            if length < 18 or length > 280:
                continue
            if sentence in candidates:
                continue
            if any(token in sentence for token in ["是", "可以", "能够", "需要", "必须", "通过", "用于", "意味着", "并非", "而是"]):
                candidates.append(sentence)
                continue
            if TIME_PATTERN.search(sentence) or VERSION_PATTERN.search(sentence) or ABSOLUTE_PATTERN.search(sentence):
                candidates.append(sentence)
    return [{"id": f"claim-{index}", "text": text} for index, text in enumerate(candidates[:18], start=1)]


def find_time_sensitive_sentences(paragraphs: Sequence[str]) -> List[str]:
    results: List[str] = []
    for paragraph in paragraphs:
        for sentence in split_sentences(paragraph):
            if TIME_PATTERN.search(sentence):
                results.append(sentence)
    return unique_preserve_order(results)[:12]


def find_version_sensitive_sentences(paragraphs: Sequence[str]) -> List[str]:
    results: List[str] = []
    for paragraph in paragraphs:
        for sentence in split_sentences(paragraph):
            if VERSION_PATTERN.search(sentence):
                results.append(sentence)
    return unique_preserve_order(results)[:12]


def build_title_candidates(header: Dict[str, str], headings: Sequence[Dict[str, object]], paragraphs: Sequence[str]) -> List[str]:
    candidates = [normalize_meaningful_text(header.get("title", ""))]
    candidates.extend(normalize_meaningful_text(str(item["text"])) for item in headings[:4] if isinstance(item.get("text"), str))
    candidates.extend(normalize_meaningful_text(paragraph[:48]) for paragraph in paragraphs[:2])
    return unique_preserve_order([candidate for candidate in candidates if candidate])[:6]


def resolve_best_title(header: Dict[str, str], headings: Sequence[Dict[str, object]], paragraphs: Sequence[str], source_packages: Sequence[Dict[str, str]]) -> str:
    candidates: List[str] = [normalize_meaningful_text(header.get("title", ""))]
    for package in source_packages:
        if not isinstance(package, dict):
            continue
        candidates.append(normalize_meaningful_text(str(package.get("title") or "")))
    candidates.extend(normalize_meaningful_text(str(item.get("text") or "")) for item in headings[:6] if isinstance(item, dict))
    candidates.extend(normalize_meaningful_text(paragraph[:72]) for paragraph in paragraphs[:3])
    for candidate in candidates:
        if candidate:
            return candidate
    return ""


def build_audit_report(raw_text: str) -> Dict[str, object]:
    header = extract_source_header(raw_text)
    source_packages = parse_sources(raw_text)
    combined_content = "\n\n".join([package["content"] for package in source_packages if package.get("content")])
    cleaned_lines, noise_lines = clean_lines(combined_content)
    paragraphs = paragraph_blocks(cleaned_lines)
    headings = extract_headings(cleaned_lines)
    linked_urls = extract_urls(raw_text)
    resolved_title = resolve_best_title(header, headings, paragraphs, source_packages)
    source_keywords = unique_preserve_order(extract_keywords(resolved_title) + extract_keywords(" ".join(str(item.get("title") or "") for item in source_packages if isinstance(item, dict))))[:16]
    heading_keywords = clean_heading_keywords(headings)
    quote_keywords = clean_quote_keywords(select_key_quotes(paragraphs))
    topic_signature = unique_preserve_order([*source_keywords, *heading_keywords, *quote_keywords])[:12]
    return {
        "source_meta": {
            "title": resolved_title,
            "author": header.get("author") or "Unknown",
            "url": header.get("url") or header.get("file") or "",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
        "source_packages": source_packages,
        "title_candidates": build_title_candidates(header, headings, paragraphs),
        "cleaned_paragraphs": paragraphs,
        "heading_tree": headings,
        "key_quotes": select_key_quotes(paragraphs),
        "linked_urls": linked_urls,
        "possible_noise_blocks": unique_preserve_order(noise_lines)[:20],
        "time_sensitive_sentences": find_time_sensitive_sentences(paragraphs),
        "version_sensitive_sentences": find_version_sensitive_sentences(paragraphs),
        "claim_candidates": select_claim_candidates(paragraphs),
        "source_keywords": source_keywords,
        "heading_keywords": heading_keywords,
        "quote_keywords": quote_keywords,
        "topic_signature": topic_signature,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a structured source package from raw_content.txt")
    parser.add_argument("--raw-content", default=str(DEFAULT_RAW_PATH), help="Path to raw_content.txt")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path to raw_content.audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_path = Path(args.raw_content).resolve()
    output_path = Path(args.output).resolve()
    if not raw_path.exists():
        raise FileNotFoundError(f"raw content not found: {raw_path}")
    report = build_audit_report(read_text(raw_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Structured source package saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
