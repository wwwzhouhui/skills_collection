from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
DEFAULT_AUDIT_REPORT = CONFIG_DIR / "raw_content.audit.json"
DEFAULT_OUTPUT_PATH = CONFIG_DIR / "verification_report.json"
CURRENT_YEAR = datetime.now().year
OFFICIAL_HINTS = (
    "docs",
    "developers",
    "platform",
    "api",
    "openai.com",
    "anthropic.com",
    "google.com",
    "microsoft.com",
    "github.com",
    "readthedocs",
    "w3.org",
    "developer.mozilla.org",
)
LOW_VALUE_PATTERNS = (
    "发布于",
    "浏览",
    "评论",
    "举报",
    "社区首页",
    "专栏",
    "登录",
    "注册",
    "推荐阅读",
    "热门",
    "Copyright",
    "版权所有",
    "腾讯云 版权所有",
    "作者头像",
    "http-save",
)
LOW_VALUE_URL_HINTS = (
    "console.cloud.tencent.com",
    "qcloudimg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    "beian.",
)


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    return text.strip()


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


def classify_claim(text: str) -> str:
    lowered = text.lower()
    if any(token in text for token in ["步骤", "首先", "然后", "最后", "如何", "先", "再", "通过"]) or "how to" in lowered:
        return "procedure"
    if any(token in text for token in ["建议", "最好", "更适合", "值得", "应该", "不推荐"]) or any(token in lowered for token in ["should", "best", "recommend"]):
        return "judgment"
    if any(token in text for token in ["是", "指", "意味着", "可以理解为"]) and len(text) < 120:
        return "definition"
    return "fact"


def risk_level(text: str) -> str:
    lowered = text.lower()
    if re.search(r"\b(19|20)\d{2}\b", text) or re.search(r"\bv\d+(?:\.\d+){0,2}\b", lowered) or re.search(r"\d+(?:\.\d+)?", text):
        return "high"
    if any(token in text for token in ["必须", "唯一", "最强", "永远", "从不", "总是"]):
        return "high"
    if any(token in lowered for token in ["api", "sdk", "release", "model", "version"]):
        return "medium"
    return "low"


def score_candidate_url(url: str, source_domain: str) -> int:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return -1
    score = 0
    hostname = parsed.netloc.lower()
    path = parsed.path.lower()
    if source_domain and hostname.endswith(source_domain):
        score += 80
    if any(hint in hostname or hint in path for hint in OFFICIAL_HINTS):
        score += 60
    if path.endswith((".md", ".txt", ".html", "/docs", "/api")):
        score += 10
    return score


def select_urls(audit_report: Dict[str, object]) -> List[str]:
    source_meta = audit_report.get("source_meta") if isinstance(audit_report.get("source_meta"), dict) else {}
    source_url = str((source_meta or {}).get("url") or "").strip()
    linked_urls = audit_report.get("linked_urls") if isinstance(audit_report.get("linked_urls"), list) else []
    candidates = unique_preserve_order([source_url, *[str(item) for item in linked_urls if isinstance(item, str)]])
    source_domain = urlparse(source_url).netloc.lower()
    scored = sorted(candidates, key=lambda item: score_candidate_url(item, source_domain), reverse=True)
    return [item for item in scored if item.startswith(("http://", "https://")) and not any(hint in item.lower() for hint in LOW_VALUE_URL_HINTS)][:6]


def is_low_value_claim(text: str) -> bool:
    cleaned = normalize(text)
    if not cleaned:
        return True
    if any(pattern.lower() in cleaned.lower() for pattern in LOW_VALUE_PATTERNS):
        return True
    if cleaned.startswith(("http://", "https://")):
        return True
    if re.search(r"^\d+$", cleaned):
        return True
    return False


def fetch_url_text(url: str) -> Tuple[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0 Safari/537.36",
    }
    response = requests.get(url, timeout=10, headers=headers)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if "html" in content_type:
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup.select("script, style, noscript"):
            tag.decompose()
        return normalize(soup.get_text("\n", strip=True)), "ok"
    return normalize(response.text), "ok"


def summarize_fetch_failure(exc: Exception) -> str:
    raw = str(exc) or exc.__class__.__name__
    lowered = raw.lower()
    if "read timed out" in lowered or "timeout" in lowered:
        return "抓取失败：超时"
    code_match = re.search(r"\b(401|403|404|405|408|409|410|429|451|500|502|503|504)\b", raw)
    if code_match:
        code = code_match.group(1)
        reason_match = re.search(rf"{code}\\s+(?:Client|Server) Error:\\s+(.+?)\\s+for url", raw)
        reason = reason_match.group(1).strip() if reason_match else ""
        reason = re.sub(r"\\s+", " ", reason)
        return f"抓取失败：HTTP {code}{(' ' + reason) if reason else ''}".strip()
    return f"抓取失败：{raw[:80].strip()}"


def build_evidence_corpus(urls: Sequence[str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    corpus: Dict[str, str] = {}
    notes: Dict[str, str] = {}
    for url in urls:
        try:
            text, status = fetch_url_text(url)
            corpus[url] = text
            notes[url] = status
        except Exception as exc:
            notes[url] = summarize_fetch_failure(exc)
    return corpus, notes


def extract_keywords(text: str) -> List[str]:
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    latin_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+_.-]{2,}", text)
    return unique_preserve_order([*chinese_tokens, *latin_tokens])[:8]


def numeric_signature(text: str) -> List[str]:
    versions = re.findall(r"\bv\d+(?:\.\d+){0,2}\b", text, flags=re.IGNORECASE)
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    numbers = re.findall(r"\d+(?:\.\d+)?(?:ms|s|%|x)?", text, flags=re.IGNORECASE)
    return unique_preserve_order([*versions, *years, *numbers])


def claim_topic_key(text: str) -> str:
    keywords = [keyword.lower() for keyword in extract_keywords(text) if len(keyword) >= 2]
    return "|".join(keywords[:3])


def detect_source_package_conflicts(audit_report: Dict[str, object]) -> List[Dict[str, object]]:
    source_packages = audit_report.get("source_packages") if isinstance(audit_report.get("source_packages"), list) else []
    sentence_entries: List[Dict[str, str]] = []
    for package in source_packages:
        if not isinstance(package, dict):
            continue
        content = normalize(str(package.get("content") or ""))
        for sentence in re.split(r"(?<=[。！？!?])\s+|\n+", content):
            cleaned = normalize(sentence)
            if len(cleaned) < 12:
                continue
            sentence_entries.append(
                {
                    "source_id": str(package.get("source_id") or ""),
                    "title": str(package.get("title") or package.get("path") or "source"),
                    "text": cleaned,
                }
            )
    conflicts: List[Dict[str, object]] = []
    for index, left in enumerate(sentence_entries):
        left_key = claim_topic_key(left["text"])
        left_numbers = numeric_signature(left["text"])
        left_keywords = set(extract_keywords(left["text"]))
        if not left_key or not left_numbers:
            continue
        for right in sentence_entries[index + 1 :]:
            if left["source_id"] == right["source_id"]:
                continue
            right_key = claim_topic_key(right["text"])
            right_numbers = numeric_signature(right["text"])
            right_keywords = set(extract_keywords(right["text"]))
            if not right_key or not right_numbers:
                continue
            if len(left_keywords & right_keywords) < 2:
                continue
            if left_numbers == right_numbers:
                continue
            conflicts.append(
                {
                    "left": left,
                    "right": right,
                    "message": f"来源 {left['title']} 与 {right['title']} 在同类主张上给出了不同数值/版本：{left['text']} <> {right['text']}",
                }
            )
    return conflicts


def detect_outdated(text: str, evidence_texts: Sequence[str]) -> bool:
    years = [int(item) for item in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    if years and max(years) <= CURRENT_YEAR - 2:
        return True
    lowered = text.lower()
    if re.search(r"\bv\d+(?:\.\d+){0,2}\b", lowered):
        evidence_joined = "\n".join(evidence_texts).lower()
        if evidence_joined and lowered not in evidence_joined and any(token in evidence_joined for token in ["deprecated", "legacy", "obsolete", "已弃用", "过时"]):
            return True
    return False


def evaluate_claim(text: str, evidence_corpus: Dict[str, str], notes: Dict[str, str]) -> Tuple[str, List[str], str]:
    evidence_urls = [url for url, evidence_text in evidence_corpus.items() if evidence_text]
    evidence_texts = list(evidence_corpus.values())
    keywords = extract_keywords(text)
    text_lower = text.lower()
    for url, evidence_text in evidence_corpus.items():
        evidence_lower = evidence_text.lower()
        if text_lower in evidence_lower:
            return "confirmed", [url], "在证据来源中找到了原句或高度相近表述。"
        if keywords and sum(1 for keyword in keywords if keyword.lower() in evidence_lower) >= max(2, min(4, len(keywords))):
            return "confirmed", [url], "在证据来源中找到了多个关键术语共现。"
    if detect_outdated(text, evidence_texts):
        return "outdated", evidence_urls[:2], "文本包含较早年份或旧版本痕迹，且证据来源未能支持其当前性。"
    if evidence_urls:
        return "disputed", evidence_urls[:2], "已检查可验证来源，但未找到足够证据支持该主张。"
    codes: List[str] = []
    for note in notes.values():
        match = re.search(r"\b(401|403|404|405|408|409|410|429|451|500|502|503|504)\b", str(note))
        if match and match.group(1) not in codes:
            codes.append(match.group(1))
    reason = ""
    if codes:
        if set(codes).issubset({"401", "403"}):
            reason = "（访问受限）"
        else:
            reason = "（抓取失败）"
    attempt_count = len([url for url in notes.keys() if url])
    attempt_suffix = f"已尝试 {attempt_count} 个链接。" if attempt_count else ""
    note = f"无法自动验证：来源抓取受限{reason}。{attempt_suffix}".strip()
    return "unverified", [], note


def build_verification_report(audit_report: Dict[str, object]) -> Dict[str, object]:
    selected_urls = select_urls(audit_report)
    evidence_corpus, notes = build_evidence_corpus(selected_urls)
    claim_candidates = audit_report.get("claim_candidates") if isinstance(audit_report.get("claim_candidates"), list) else []
    source_conflicts = detect_source_package_conflicts(audit_report)
    disputed_texts = set()
    for conflict in source_conflicts:
        left = conflict.get("left") if isinstance(conflict, dict) else None
        right = conflict.get("right") if isinstance(conflict, dict) else None
        if isinstance(left, dict) and left.get("text"):
            disputed_texts.add(str(left["text"]))
        if isinstance(right, dict) and right.get("text"):
            disputed_texts.add(str(right["text"]))
    claims: List[Dict[str, object]] = []
    conflicts: List[str] = []
    outdated_items: List[str] = []
    unverified_items: List[str] = []
    seen_texts: Dict[str, str] = {}
    filtered_candidates = []
    for item in claim_candidates:
        text = str(item.get("text") if isinstance(item, dict) else item).strip()
        if not text or is_low_value_claim(text):
            continue
        filtered_candidates.append(item)

    for index, item in enumerate(filtered_candidates, start=1):
        text = str(item.get("text") if isinstance(item, dict) else item).strip()
        if not text:
            continue
        claim_type = classify_claim(text)
        level = risk_level(text)
        status, evidence_urls, evidence_note = evaluate_claim(text, evidence_corpus, notes)
        if text in disputed_texts:
            status = "disputed"
            evidence_note = "跨来源比较发现同类主张存在不同数值或版本表述。"
        claim = {
            "id": str(item.get("id") if isinstance(item, dict) and item.get("id") else f"claim-{index}"),
            "text": text,
            "type": claim_type,
            "risk_level": level,
            "status": status,
            "evidence_urls": evidence_urls,
            "evidence_note": evidence_note,
        }
        claims.append(claim)
        if status == "outdated":
            outdated_items.append(text)
        if status == "unverified":
            unverified_items.append(text)
        if status in {"disputed", "outdated"}:
            conflicts.append(f"{text} [{status}]")
        normalized_key = re.sub(r"\s+", "", text[:40])
        if normalized_key in seen_texts and seen_texts[normalized_key] != status:
            conflicts.append(f"同类主张出现状态不一致：{text}")
        seen_texts[normalized_key] = status

    counts = {
        "confirmed": sum(1 for claim in claims if claim["status"] == "confirmed"),
        "disputed": sum(1 for claim in claims if claim["status"] == "disputed"),
        "outdated": sum(1 for claim in claims if claim["status"] == "outdated"),
        "unverified": sum(1 for claim in claims if claim["status"] == "unverified"),
    }
    summary = (
        f"共校验 {len(claims)} 条主张：已确认 {counts['confirmed']}，存在争议 {counts['disputed']}，"
        f"已过时 {counts['outdated']}，无法确认 {counts['unverified']}。"
    )
    return {
        "claims": claims,
        "conflicts": unique_preserve_order([*conflicts, *[str(item["message"]) for item in source_conflicts]]),
        "outdated_items": unique_preserve_order(outdated_items),
        "unverified_items": unique_preserve_order(unverified_items),
        "summary": summary,
        "checked_urls": selected_urls,
        "evidence_fetch_notes": notes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a truth-anchoring verification report")
    parser.add_argument("--audit-report", default=str(DEFAULT_AUDIT_REPORT), help="Path to raw_content.audit.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Path to verification_report.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit_report_path = Path(args.audit_report).resolve()
    output_path = Path(args.output).resolve()
    if not audit_report_path.exists():
        raise FileNotFoundError(f"audit report not found: {audit_report_path}")
    report = build_verification_report(read_json(audit_report_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Verification report saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
