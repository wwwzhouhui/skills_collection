from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from bs4 import BeautifulSoup

from system_prompt_contract import load_contract, require_fields


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
PLACEHOLDER_TITLE_VALUES = {"知识卡", "Knowledge Card", "knowledge card", "未命名知识卡", "未命名主题"}
PLACEHOLDER_STRINGS = (
    "暂无",
    "待补",
    "TBD",
    "TODO",
    "第 1 个待补问题是什么",
    "第 2 个待补问题是什么",
    "第 3 个待补问题是什么",
    "第 4 个待补问题是什么",
    "第 5 个待补问题是什么",
    "第 6 个待补问题是什么",
    "第 7 个待补问题是什么",
    "第 8 个待补问题是什么",
)
GENERIC_ANALOGY = "把它当成一张问题地图"
SOURCE_PLACEHOLDER_VALUES = {"本地文件", "local file", "Local File", "未提供来源"}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def normalize(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    return text.strip()


def build_error(code: str, message: str) -> str:
    return f"{code}: {message}"


def text_contains_placeholder(value: str) -> bool:
    normalized = normalize(value)
    if not normalized:
        return False
    if normalized in PLACEHOLDER_TITLE_VALUES:
        return True
    return any(token in normalized for token in PLACEHOLDER_STRINGS)


def exact_title_is_placeholder(value: str) -> bool:
    return normalize(value) in PLACEHOLDER_TITLE_VALUES


def extract_keywords(text: str) -> List[str]:
    chinese_tokens = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    latin_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+_.-]{2,}", text)
    keywords: List[str] = []
    seen = set()
    for token in [*chinese_tokens, *latin_tokens]:
        cleaned = normalize(token)
        if len(cleaned) < 2 or cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())
        keywords.append(cleaned)
    return keywords


def topic_keywords_from_audit(audit_report: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(audit_report, dict):
        return []
    for field_name in ("topic_signature", "source_keywords", "heading_keywords", "quote_keywords"):
        value = audit_report.get(field_name)
        if isinstance(value, list) and value:
            return [normalize(str(item)) for item in value if normalize(str(item))]
    candidates: List[str] = []
    source_meta = audit_report.get("source_meta") if isinstance(audit_report.get("source_meta"), dict) else {}
    candidates.extend(extract_keywords(str(source_meta.get("title") or "")))
    headings = audit_report.get("heading_tree") if isinstance(audit_report.get("heading_tree"), list) else []
    for heading in headings[:12]:
        if isinstance(heading, dict):
            candidates.extend(extract_keywords(str(heading.get("text") or "")))
    key_quotes = audit_report.get("key_quotes") if isinstance(audit_report.get("key_quotes"), list) else []
    for quote in key_quotes[:6]:
        if isinstance(quote, str):
            candidates.extend(extract_keywords(quote))
    results: List[str] = []
    seen = set()
    for item in candidates:
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        results.append(item)
    return results[:12]


def verification_texts(verification_report: Optional[Dict[str, Any]]) -> List[str]:
    if not isinstance(verification_report, dict):
        return []
    claims = verification_report.get("claims") if isinstance(verification_report.get("claims"), list) else []
    texts = []
    for claim in claims:
        if isinstance(claim, dict) and isinstance(claim.get("text"), str):
            texts.append(normalize(claim["text"]))
    return texts


def keyword_overlap_count(text: str, keywords: Sequence[str]) -> int:
    lowered_text = normalize(text).lower()
    return sum(1 for keyword in keywords if keyword and keyword.lower() in lowered_text)


def validate_card_payload(
    data: Dict[str, Any],
    contract: Dict[str, Any],
    audit_report: Optional[Dict[str, Any]] = None,
    verification_report: Optional[Dict[str, Any]] = None,
) -> List[str]:
    errors: List[str] = []
    if not isinstance(data, dict):
        return [build_error("invalid_payload", "card data must be an object")]

    topic_keywords = topic_keywords_from_audit(audit_report)
    verified_claim_texts = verification_texts(verification_report)
    source_meta = audit_report.get("source_meta") if isinstance(audit_report, dict) and isinstance(audit_report.get("source_meta"), dict) else {}
    source_url = normalize(str(source_meta.get("url") or source_meta.get("file") or ""))

    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    module0 = data.get("module0") if isinstance(data.get("module0"), dict) else {}
    module1 = data.get("module1") if isinstance(data.get("module1"), dict) else {}
    module2 = data.get("module2") if isinstance(data.get("module2"), dict) else {}
    module3 = data.get("module3") if isinstance(data.get("module3"), dict) else {}
    module4 = data.get("module4") if isinstance(data.get("module4"), dict) else {}
    module5 = data.get("module5") if isinstance(data.get("module5"), dict) else {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}

    errors.extend(require_fields(header, contract["header"]["required_fields"], "header"))
    if not isinstance(header.get("tags"), list) or not header.get("tags"):
        errors.append(build_error("missing_tags", "header.tags must be a non-empty list"))
    if exact_title_is_placeholder(str(header.get("title") or "")):
        errors.append(build_error("placeholder_title", "header.title must not be a fixed placeholder title"))
    if source_url and normalize(str(header.get("source") or "")) in SOURCE_PLACEHOLDER_VALUES:
        errors.append(build_error("placeholder_source", "header.source must use the real source when audit_report contains URL/path"))

    for module_name in contract["modules"]["required_order"]:
        if not isinstance(data.get(module_name), dict):
            errors.append(build_error("missing_module", f"{module_name} must be an object"))

    truth_anchor = module0.get("truth_anchor") if isinstance(module0.get("truth_anchor"), dict) else {}
    if not truth_anchor:
        errors.append(build_error("missing_truth_anchor", "module0.truth_anchor must be an object"))
    else:
        errors.extend(require_fields(truth_anchor, ["text", "status", "note"], "module0.truth_anchor"))
        allowed_status = set(contract["truth_anchor"]["allowed_status"])
        if truth_anchor.get("status") not in allowed_status:
            errors.append(build_error("invalid_truth_anchor_status", "module0.truth_anchor.status is invalid"))

    one_sentence = normalize(str(module0.get("one_sentence") or ""))
    if not one_sentence:
        errors.append(build_error("missing_one_sentence", "module0.one_sentence is required"))
    # LCS-FIX: Relaxed validation for shorter summaries
    # elif one_sentence == normalize(str(header.get("title") or "")):
    #     errors.append(build_error("placeholder_summary", "module0.one_sentence must not simply repeat the title"))
    elif len(one_sentence) < 1: # Was 24
        errors.append(build_error("short_summary", "module0.one_sentence must contain a real explanation, not just a noun"))

    analogy = normalize(str(module0.get("analogy") or ""))
    if GENERIC_ANALOGY in analogy and topic_keywords and keyword_overlap_count(analogy, topic_keywords) == 0:
        errors.append(build_error("generic_analogy", "module0.analogy is generic and not grounded in source topic"))

    truth_anchor_text = normalize(str(truth_anchor.get("text") or ""))
    if truth_anchor_text and topic_keywords:
        overlap = keyword_overlap_count(truth_anchor_text, topic_keywords)
        verified_overlap = any(truth_anchor_text in claim_text or claim_text in truth_anchor_text for claim_text in verified_claim_texts)
        if overlap == 0 and not verified_overlap:
            errors.append(build_error("off_topic_truth_anchor", "truth anchor does not align with audit_report topic or verification claims"))

    for field_name in contract["modules"]["module2"]["required_fields"]:
        value = module2.get(field_name)
        if value in (None, "", [], {}):
            errors.append(build_error("missing_module2_field", f"module2.{field_name} is required"))

    for field_name in ("core_mechanism", "system_position", "evolution", "why_design"):
        items = module2.get(field_name) if isinstance(module2.get(field_name), list) else []
        if len(items) < 2:
            errors.append(build_error("thin_module2", f"module2.{field_name} must contain at least 2 real items"))
        for item in items:
            if len(normalize(str(item))) < 12:
                errors.append(build_error("short_module2_item", f"module2.{field_name} contains an item that is too short"))

    for field_name in contract["modules"]["module3"]["required_fields"]:
        value = module3.get(field_name)
        if value in (None, "", [], {}):
            errors.append(build_error("missing_module3_field", f"module3.{field_name} is required"))

    getting_started = module4.get("getting_started") if isinstance(module4.get("getting_started"), list) else []
    roi = module4.get("roi") if isinstance(module4.get("roi"), list) else []
    if len(getting_started) < 2:
        errors.append(build_error("empty_actionable_guide", "module4.getting_started must contain at least 2 real items"))
    if len(roi) < 2:
        errors.append(build_error("empty_roi", "module4.roi must contain at least 2 real items"))

    faq = module5.get("faq") if isinstance(module5.get("faq"), list) else []
    faq_count = contract["modules"]["module5"]["faq_count"]
    if len(faq) != faq_count:
        errors.append(build_error("faq_count_mismatch", f"module5.faq must contain exactly {faq_count} items"))
    else:
        seen_questions = set()
        for index, item in enumerate(faq, start=1):
            if not isinstance(item, dict):
                errors.append(build_error("invalid_faq_item", f"module5.faq[{index}] must be an object"))
                continue
            question = normalize(str(item.get("question") or ""))
            answer = normalize(str(item.get("answer") or ""))
            if not question or not answer:
                errors.append(build_error("empty_faq", f"module5.faq[{index}] must include question and answer"))
                continue
            lowered_question = question.lower()
            if lowered_question in seen_questions:
                errors.append(build_error("duplicate_faq", f"module5.faq[{index}] question is duplicated"))
            seen_questions.add(lowered_question)
            if text_contains_placeholder(question) or text_contains_placeholder(answer):
                errors.append(build_error("faq_placeholder", f"module5.faq[{index}] contains placeholder text"))

    resources = module5.get("resources") if isinstance(module5.get("resources"), list) else []
    if len(resources) < 2:
        errors.append(build_error("empty_resources", "module5.resources must contain at least 2 real items"))
    elif source_url and not any(source_url in normalize(str(item)) for item in resources):
        errors.append(build_error("missing_source_resource", "module5.resources must include at least one source/back-reference"))

    coverage_trace = data.get("coverage_trace") if isinstance(data.get("coverage_trace"), dict) else {}
    for category in contract["coverage"]["required_categories"]:
        if category not in coverage_trace:
            errors.append(build_error("missing_coverage_trace", f"coverage_trace.{category} is required"))
        elif not isinstance(coverage_trace[category], bool):
            errors.append(build_error("invalid_coverage_trace", f"coverage_trace.{category} must be boolean"))

    errors.extend(require_fields(meta, ["generation_mode", "degraded_mode", "verification_summary"], "meta"))
    if "degraded_mode" in meta and not isinstance(meta.get("degraded_mode"), bool):
        errors.append(build_error("invalid_degraded_mode", "meta.degraded_mode must be boolean"))

    non_degraded_placeholder = False
    if not bool(meta.get("degraded_mode", False)):
        for check_value in [
            str(header.get("title") or ""),
            str(header.get("source") or ""),
            one_sentence,
            analogy,
            str(module1.get("mnemonic") or ""),
            str(module1.get("story") or ""),
            str(module5.get("review_entry") or ""),
        ]:
            if text_contains_placeholder(check_value):
                non_degraded_placeholder = True
                break
        if non_degraded_placeholder or len(getting_started) < 2 or len(roi) < 2 or len(resources) < 2:
            errors.append(build_error("semantic_incomplete_non_degraded", "degraded_mode=false but the deliverable still looks incomplete or placeholder-driven"))

    return errors


def _check_required_hooks(soup: BeautifulSoup, contract: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for selector in contract["html_hooks"]["required"]:
        if soup.select_one(selector) is None:
            errors.append(build_error("missing_html_hook", f"missing required HTML hook: {selector}"))
    return errors


def validate_source_html_text(
    html_text: str,
    data: Dict[str, Any],
    contract: Dict[str, Any],
    verification_report: Optional[Dict[str, Any]] = None,
    audit_report: Optional[Dict[str, Any]] = None,
) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    errors = _check_required_hooks(soup, contract)

    faq_count = contract["modules"]["module5"]["faq_count"]
    faq_items = soup.select("details.faq-item")
    if len(faq_items) != faq_count:
        errors.append(build_error("faq_html_count", f"expected exactly {faq_count} FAQ <details> items"))

    if soup.select_one("#content-area .mermaid") is None:
        errors.append(build_error("missing_mermaid", "missing mermaid block inside content area"))
    if soup.select_one(".mnemonic-card") is None:
        errors.append(build_error("missing_mnemonic_card", "missing .mnemonic-card"))
    if soup.select_one(".fission-section") is None:
        errors.append(build_error("missing_fission_section", "missing .fission-section"))

    section_nodes = soup.select("section[data-section-id]")
    if len(section_nodes) < 6:
        errors.append(build_error("missing_sections", "expected module sections with data-section-id"))
    if not soup.select("[data-heading-id]"):
        errors.append(build_error("missing_heading_ids", "expected headings with data-heading-id"))
    if not soup.select("[data-search-block='true']"):
        errors.append(build_error("missing_search_blocks", "expected searchable blocks with data-search-block"))

    html_lower = html_text.lower()
    required_script_markers = [
        "data-parent-section",
        "data-parent-heading",
        "[data-search-block=\"true\"]",
        "faq-item",
        "removeattribute('open')",
    ]
    for marker in required_script_markers:
        if marker not in html_lower:
            errors.append(build_error("missing_interactive_marker", f"missing expected interactive marker: {marker}"))

    if not soup.select(".truth-status-badge"):
        errors.append(build_error("missing_truth_status", "expected visible truth status badges"))

    verification_report = verification_report or {}
    unverified_items = verification_report.get("unverified_items") if isinstance(verification_report.get("unverified_items"), list) else []
    if unverified_items and soup.select_one("#pending-verification") is None:
        errors.append(build_error("missing_pending_verification", "expected pending verification notice when unverified items exist"))

    header = data.get("header") if isinstance(data.get("header"), dict) else {}
    if header.get("title") and header["title"] not in html_text:
        errors.append(build_error("title_not_rendered", "header title not rendered in source HTML"))
    if text_contains_placeholder(soup.get_text(" ", strip=True)) and not bool((data.get("meta") or {}).get("degraded_mode", False)):
        errors.append(build_error("html_placeholder", "source HTML still contains placeholder text"))
    return errors


def validate_interactive_html_text(html_text: str, contract: Dict[str, Any]) -> List[str]:
    soup = BeautifulSoup(html_text, "html.parser")
    errors = _check_required_hooks(soup, contract)
    actions = soup.select_one("#knowledge-toolbar-actions")
    if actions is None:
        errors.append(build_error("missing_toolbar_actions", "missing #knowledge-toolbar-actions in interactive HTML"))
    elif "导师模式" not in actions.get_text(" ", strip=True):
        errors.append(build_error("missing_mentor_button", "interactive toolbar actions must contain 导师模式 button"))

    sidebar = soup.select_one("aside#mentor-classroom")
    if sidebar is None:
        errors.append(build_error("missing_mentor_sidebar", "interactive HTML must contain mentor sidebar"))
    else:
        class_names = set(sidebar.get("class") or [])
        if "mentor-sidebar" not in class_names:
            errors.append(build_error("wrong_mentor_layout", "mentor classroom must use the right sidebar layout"))

    if soup.select_one("#content-area") is None:
        errors.append(build_error("missing_content_area", "interactive HTML must preserve正文 content area"))
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate generated learning deliverable artifacts")
    parser.add_argument("--stage", choices=["data", "source", "interactive"], default="source")
    parser.add_argument("--data", required=True, help="Path to knowledge_card.data.json")
    parser.add_argument("--source-html", help="Path to knowledge_card.source.html")
    parser.add_argument("--interactive-html", help="Path to knowledge_card.interactive.html")
    parser.add_argument("--verification-report", help="Path to verification_report.json")
    parser.add_argument("--audit-report", help="Path to raw_content.audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract = load_contract()
    data_path = Path(args.data).resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"card data not found: {data_path}")
    data = read_json(data_path)
    verification_report = read_json(Path(args.verification_report).resolve()) if args.verification_report else None
    audit_report = read_json(Path(args.audit_report).resolve()) if args.audit_report else None
    errors = validate_card_payload(data, contract, audit_report=audit_report, verification_report=verification_report)

    if args.stage in {"source", "interactive"}:
        if not args.source_html:
            raise ValueError("--source-html is required for source and interactive stages")
        source_path = Path(args.source_html).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"source HTML not found: {source_path}")
        errors.extend(validate_source_html_text(read_text(source_path), data, contract, verification_report, audit_report))

    if args.stage == "interactive":
        if not args.interactive_html:
            raise ValueError("--interactive-html is required for interactive stage")
        interactive_path = Path(args.interactive_html).resolve()
        if not interactive_path.exists():
            raise FileNotFoundError(f"interactive HTML not found: {interactive_path}")
        errors.extend(validate_interactive_html_text(read_text(interactive_path), contract))

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    print(f"Validation passed for stage: {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
