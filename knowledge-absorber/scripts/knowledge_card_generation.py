from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from knowledge_card_rendering import build_output_paths, infer_card_theme, render_html, render_markdown
from rule_card_generator import build_rule_card_data
from system_prompt_contract import load_contract
from validate_knowledge_card import validate_card_payload


@dataclass
class GenerationArtifacts:
    output_dir: Path
    markdown_path: Path
    source_html_path: Path
    data_path: Path


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_meaningful_text(value: Any) -> str:
    cleaned = normalize(str(value or "")).strip("* ")
    if cleaned.lower() in {"", "none", "null", "untitled", "unknown", "nan"}:
        return ""
    return cleaned


def ensure_list_of_strings(value: Any) -> List[str]:
    if isinstance(value, list):
        return [normalize(str(item)) for item in value if normalize(str(item))]
    if isinstance(value, str) and normalize(value):
        return [normalize(value)]
    return []


def ensure_truth_anchor(value: Any) -> Dict[str, str]:
    if isinstance(value, dict):
        return {
            "text": normalize(str(value.get("text") or "")),
            "status": normalize(str(value.get("status") or "")),
            "note": normalize(str(value.get("note") or "")),
        }
    return {"text": "", "status": "", "note": ""}


def normalize_faq(value: Any, faq_count: int) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    if not isinstance(value, list):
        return items
    for item in value:
        if not isinstance(item, dict):
            continue
        question = normalize(str(item.get("question") or ""))
        answer = normalize(str(item.get("answer") or ""))
        if question or answer:
            items.append({"question": question, "answer": answer})
    return items[:faq_count]


def source_meta_from_audit(audit_report: Dict[str, Any]) -> Dict[str, str]:
    source_meta = audit_report.get("source_meta") if isinstance(audit_report.get("source_meta"), dict) else {}
    title_candidates = audit_report.get("title_candidates") if isinstance(audit_report.get("title_candidates"), list) else []
    resolved_title = normalize_meaningful_text(source_meta.get("title"))
    if not resolved_title:
        for candidate in title_candidates:
            resolved_title = normalize_meaningful_text(candidate)
            if resolved_title:
                break
    return {
        "title": resolved_title,
        "author": normalize(str(source_meta.get("author") or "")),
        "source": normalize(str(source_meta.get("url") or source_meta.get("file") or "")),
    }


def normalize_card_data(
    candidate: Dict[str, Any],
    contract: Dict[str, Any],
    generation_mode: str,
    degraded_mode: bool,
    verification_report: Dict[str, Any],
    audit_report: Dict[str, Any],
) -> Dict[str, Any]:
    header = candidate.get("header") if isinstance(candidate.get("header"), dict) else {}
    module0 = candidate.get("module0") if isinstance(candidate.get("module0"), dict) else {}
    module1 = candidate.get("module1") if isinstance(candidate.get("module1"), dict) else {}
    module2 = candidate.get("module2") if isinstance(candidate.get("module2"), dict) else {}
    module3 = candidate.get("module3") if isinstance(candidate.get("module3"), dict) else {}
    module4 = candidate.get("module4") if isinstance(candidate.get("module4"), dict) else {}
    module5 = candidate.get("module5") if isinstance(candidate.get("module5"), dict) else {}
    meta = candidate.get("meta") if isinstance(candidate.get("meta"), dict) else {}
    source_meta = source_meta_from_audit(audit_report)
    faq_count = contract["modules"]["module5"]["faq_count"]

    resolved_title = normalize(str(header.get("title") or "")) or source_meta["title"]
    resolved_source = normalize(str(header.get("source") or "")) or source_meta["source"]
    resolved_author = normalize(str(header.get("author") or "")) or "叫我小杨同学的小码酱"

    normalized = {
        "header": {
            "title": resolved_title,
            "author": resolved_author,
            "tags": ensure_list_of_strings(header.get("tags"))[:8],
            "source": resolved_source,
            "audience_positioning": normalize(str(header.get("audience_positioning") or "")),
        },
        "module0": {
            "one_sentence": normalize(str(module0.get("one_sentence") or "")),
            "analogy": normalize(str(module0.get("analogy") or "")),
            "truth_anchor": ensure_truth_anchor(module0.get("truth_anchor")),
        },
        "module1": {
            "mnemonic": normalize(str(module1.get("mnemonic") or "")),
            "story": normalize(str(module1.get("story") or "")),
            "ascii_visual": normalize(str(module1.get("ascii_visual") or "")),
        },
        "module2": {
            "core_mechanism": ensure_list_of_strings(module2.get("core_mechanism")),
            "system_position": ensure_list_of_strings(module2.get("system_position")),
            "evolution": ensure_list_of_strings(module2.get("evolution")),
            "why_design": ensure_list_of_strings(module2.get("why_design")),
            "mermaid": normalize(str(module2.get("mermaid") or "")),
        },
        "module3": {
            "anti_intuition": normalize(str(module3.get("anti_intuition") or "")),
            "conflicts_or_version_diff": ensure_list_of_strings(module3.get("conflicts_or_version_diff")),
            "search_internalized_tags": ensure_list_of_strings(module3.get("search_internalized_tags"))[:6],
            "learner_takeaway": normalize(str(module3.get("learner_takeaway") or "")),
        },
        "module4": {
            "getting_started": ensure_list_of_strings(module4.get("getting_started")),
            "pitfalls": ensure_list_of_strings(module4.get("pitfalls")),
            "roi": ensure_list_of_strings(module4.get("roi")),
        },
        "module5": {
            "faq": normalize_faq(module5.get("faq"), faq_count),
            "review_entry": normalize(str(module5.get("review_entry") or "")),
            "resources": ensure_list_of_strings(module5.get("resources"))[:8],
        },
        "coverage_trace": candidate.get("coverage_trace") if isinstance(candidate.get("coverage_trace"), dict) else {},
        "meta": {
            "generation_mode": normalize(str(meta.get("generation_mode") or generation_mode or "auto")),
            "degraded_mode": bool(meta.get("degraded_mode", degraded_mode)),
            "verification_summary": normalize(str(meta.get("verification_summary") or verification_report.get("summary") or "")),
        },
    }

    for category in contract["coverage"]["required_categories"]:
        if category in normalized["coverage_trace"]:
            normalized["coverage_trace"][category] = bool(normalized["coverage_trace"][category])
    return normalized


def load_external_card_data(
    card_data_path: Path,
    contract: Dict[str, Any],
    verification_report: Dict[str, Any],
    audit_report: Dict[str, Any],
    card_generation_mode: str,
) -> Dict[str, Any]:
    candidate = read_json(card_data_path)
    meta = candidate.get("meta") if isinstance(candidate.get("meta"), dict) else {}
    generation_mode = normalize(str(meta.get("generation_mode") or card_generation_mode or "auto"))
    degraded_mode = bool(meta.get("degraded_mode", False))
    return normalize_card_data(candidate, contract, generation_mode, degraded_mode, verification_report, audit_report)


def generate_card_data(
    audit_report: Dict[str, Any],
    verification_report: Dict[str, Any],
    contract: Dict[str, Any],
    card_generation_mode: str,
    card_data_path: Path | None = None,
) -> Dict[str, Any]:
    if card_data_path is not None:
        return load_external_card_data(card_data_path, contract, verification_report, audit_report, card_generation_mode)
    if card_generation_mode == "rule":
        return build_rule_card_data(audit_report, verification_report, contract, generation_mode="rule", degraded_mode=True)
    raise ValueError(
        "当前 CLI 不负责调用第二个模型来生成正文。"
        "在 skill 使用场景中，应由当前模型直接生成 knowledge_card.data.json，再通过 --card-data-file 交给脚本渲染；"
        "如果只想本地兜底，请使用 --card-generation-mode rule。"
    )


def generate_outputs(
    raw_path: Path,
    output_root: Path,
    audit_report_path: Path,
    verification_report_path: Path,
    card_generation_mode: str,
    card_data_path: Path | None = None,
) -> GenerationArtifacts:
    contract = load_contract()
    audit_report = read_json(audit_report_path)
    verification_report = read_json(verification_report_path)
    card_data = generate_card_data(audit_report, verification_report, contract, card_generation_mode, card_data_path=card_data_path)
    errors = validate_card_payload(card_data, contract, audit_report=audit_report, verification_report=verification_report)
    if errors:
        raise ValueError("Generated card data failed validation: " + " | ".join(errors))

    title = card_data["header"]["title"]
    if not title:
        raise ValueError("header.title is required after normalization")

    theme = infer_card_theme(title, card_data["header"]["tags"], audit_report.get("cleaned_paragraphs") or [], card_data["header"]["source"])
    markdown = render_markdown(card_data, verification_report)
    html_output = render_html(card_data, verification_report, theme)
    date_stamp = datetime.now().strftime("%Y%m%d")
    output_dir, markdown_path, source_html_path, data_path = build_output_paths(output_root, title, date_stamp)
    internal_dir = data_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    source_html_path.write_text(html_output, encoding="utf-8")
    data_path.write_text(json.dumps(card_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal_dir / "raw_content.audit.json").write_text(json.dumps(audit_report, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal_dir / "verification_report.json").write_text(json.dumps(verification_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return GenerationArtifacts(output_dir=output_dir, markdown_path=markdown_path, source_html_path=source_html_path, data_path=data_path)
