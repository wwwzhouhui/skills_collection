from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\r", " ").replace("\n", " ")).strip()


def unique_preserve_order(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        cleaned = normalize(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def summarize_sentence(text: str, fallback: str) -> str:
    cleaned = normalize(text)
    if not cleaned:
        return fallback
    if len(cleaned) <= 120:
        return cleaned
    parts = re.split(r"(?<=[。！？!?])\s+", cleaned)
    return parts[0].strip() if parts and parts[0].strip() else cleaned[:120].rstrip() + "…"


def pick_meaningful_paragraph(paragraphs: Sequence[str], fallback: str) -> str:
    normalized_fallback = normalize(fallback).lower()
    for paragraph in paragraphs:
        cleaned = normalize(paragraph)
        if len(cleaned) < 16:
            continue
        if cleaned.lower() == normalized_fallback:
            continue
        if not any(token in cleaned for token in ["。", "：", ":", "是", "需要", "可以", "能够", "版本", "流程", "系统"]):
            continue
        return cleaned
    return fallback


def meaningful_analysis_items(paragraphs: Sequence[str], title: str) -> List[str]:
    def looks_like_codeish(text: str) -> bool:
        lowered = text.lower()
        if any(token in lowered for token in ["name_for_human", "name_for_model", "description_for_model", "parameters"]):
            return True
        if any(token in lowered for token in ["payload =", "json.dumps", "headers =", "def ", "class ", "import "]):
            return True
        if re.search(r"[{}\[\]]", text) and (":" in text or "=" in text):
            return True
        if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*.+", text):
            return True
        if text.count("'") + text.count('"') >= 8 and (":" in text or "{" in text or "[" in text):
            return True
        return False

    results: List[str] = []
    for paragraph in paragraphs:
        cleaned = normalize(paragraph)
        if len(cleaned) < 12:
            continue
        if cleaned.lower() in {title.lower(), "source a", "source b"}:
            continue
        if looks_like_codeish(cleaned):
            continue
        results.append(cleaned)
    return results or [title]


def derive_keywords(title: str, headings: Sequence[Dict[str, Any]], paragraphs: Sequence[str]) -> List[str]:
    candidates = [title]
    candidates.extend(str(item.get("text") or "") for item in headings[:6] if isinstance(item, dict))
    for paragraph in paragraphs[:8]:
        candidates.extend(re.findall(r"[\u4e00-\u9fff]{2,8}|[A-Za-z][A-Za-z0-9+_.-]{2,}", paragraph))
    keywords = unique_preserve_order(candidates)
    filtered: List[str] = []
    for keyword in keywords:
        if len(keyword) < 2:
            continue
        if keyword in filtered:
            continue
        filtered.append(keyword)
        if len(filtered) >= 8:
            break
    return filtered or [title]


def build_mermaid(title: str, headings: Sequence[Dict[str, Any]]) -> str:
    labels = [str(item.get("text") or "") for item in headings if isinstance(item, dict) and item.get("text")]
    while len(labels) < 3:
        labels.append(f"阶段 {len(labels) + 1}")
    first, second, third = labels[:3]
    return "\n".join(
        [
            "flowchart TD",
            f'  A["问题入口：{title}"] --> B["核心机制：{first}"]',
            f'  B --> C["系统协同：{second}"]',
            f'  C --> D["落地与复盘：{third}"]',
            '  D --> E["验证与修正"]',
            '  E --> B',
        ]
    )


def pick_truth_anchor(verification_report: Dict[str, Any], paragraphs: Sequence[str], fallback: str) -> Dict[str, str]:
    claims = verification_report.get("claims") if isinstance(verification_report.get("claims"), list) else []
    preferred = next((claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "confirmed"), None)
    if preferred:
        return {
            "text": str(preferred.get("text") or fallback),
            "status": str(preferred.get("status") or "confirmed"),
            "note": str(preferred.get("evidence_note") or "已在证据来源中获得支持。"),
        }
    if claims and isinstance(claims[0], dict):
        return {
            "text": str(claims[0].get("text") or fallback),
            "status": str(claims[0].get("status") or "unverified"),
            "note": str(claims[0].get("evidence_note") or "当前没有补充证据说明。"),
        }
    return {
        "text": summarize_sentence(paragraphs[0] if paragraphs else fallback, fallback),
        "status": "unverified",
        "note": "未发现可直接复用的结构化验证主张。",
    }


def build_faq(title: str, tldr: str, faq_count: int) -> List[Dict[str, str]]:
    base = [
        {"question": "这份内容最核心的问题是什么？", "answer": tldr},
        {"question": "为什么不能只背结论？", "answer": "因为真正决定迁移能力的是概念之间的因果结构，而不是一句结果。"},
        {"question": "应该先抓定义还是先看流程？", "answer": "先抓定义，再立刻定位流程；没有流程的定义很快会变成空壳。"},
        {"question": "最容易忽略的边界是什么？", "answer": "时间点、版本差异、前提假设和默认环境最容易被读者跳过。"},
        {"question": "怎么把它转成自己的笔记？", "answer": "建议按概念、机制、场景、误区四层来记，而不是照抄原文段落。"},
        {"question": "如果我现在读不懂，先补什么？", "answer": "先补主线：它解决什么问题、为什么重要、执行链路怎么走。"},
        {"question": "怎么判断自己真的学会了？", "answer": "试着不用原文措辞，把关键机制讲给一个完全没背景的人。"},
        {"question": "这份学习成品怎么用最值？", "answer": f"先通读《{title}》的主线，再用搜索、FAQ 和导师模式反向检查自己的理解。"},
    ]
    return base[:faq_count]


def build_rule_card_data(
    audit_report: Dict[str, Any],
    verification_report: Dict[str, Any],
    contract: Dict[str, Any],
    generation_mode: str,
    degraded_mode: bool,
) -> Dict[str, Any]:
    source_meta = audit_report.get("source_meta") if isinstance(audit_report.get("source_meta"), dict) else {}
    title = str(source_meta.get("title") or "").strip() or "未命名主题"
    author = "叫我小杨同学的小码酱"
    source = str(source_meta.get("url") or source_meta.get("file") or "").strip() or "未提供来源"
    headings = audit_report.get("heading_tree") if isinstance(audit_report.get("heading_tree"), list) else []
    paragraphs = [str(item) for item in (audit_report.get("cleaned_paragraphs") or []) if isinstance(item, str)]
    key_quotes = [str(item) for item in (audit_report.get("key_quotes") or []) if isinstance(item, str)]
    conflicts = [str(item) for item in (verification_report.get("conflicts") or []) if isinstance(item, str)]
    outdated_items = [str(item) for item in (verification_report.get("outdated_items") or []) if isinstance(item, str)]
    unverified_items = [str(item) for item in (verification_report.get("unverified_items") or []) if isinstance(item, str)]
    tags = derive_keywords(title, headings, paragraphs)
    best_paragraph = pick_meaningful_paragraph(paragraphs, title)
    tldr = summarize_sentence(best_paragraph, title)
    truth_anchor = pick_truth_anchor(verification_report, paragraphs, tldr)
    analysis_seed = meaningful_analysis_items(paragraphs, title)[:10] or key_quotes or [title]
    faq_count = int(contract["modules"]["module5"]["faq_count"])
    module3_conflicts = conflicts[:4]
    if not module3_conflicts:
        module3_conflicts = ["当前未检出显性多源冲突，但仍需结合时间点和版本环境理解原文。"]
    if outdated_items:
        module3_conflicts.append("可能过时的内容：" + "；".join(outdated_items[:2]))
    if unverified_items:
        module3_conflicts.append(f"待人工确认：{len(unverified_items)} 条（为保持正文清爽，明细已收纳到“质量与验证”面板）。")

    return {
        "header": {
            "title": title,
            "author": author,
            "tags": tags,
            "source": source,
            "audience_positioning": "面向零基础读者，把复杂材料整理成可复盘、可搜索、可继续追问的最终学习成品。",
        },
        "module0": {
            "one_sentence": tldr,
            "analogy": f"你可以把《{title}》理解成一张任务地图：它不是只告诉你结论，而是试图交代为什么、怎么做、哪里容易踩坑。",
            "truth_anchor": truth_anchor,
        },
        "module1": {
            "mnemonic": f"先抓主线，再拆机制；先懂 why，再做 how；碰到边界，回到证据。关键词：{' / '.join(tags[:4])}。",
            "story": f"如果你第一次接触《{title}》，很容易被术语和结论带着跑。更稳的读法是先抓主线，再拆机制，最后回到场景验证自己是否真懂了。",
            "ascii_visual": "问题入口\n   |\n   v\n核心概念 ---> 关键机制 ---> 实战场景\n   ^                          |\n   |                          v\n误区修正 <--- 反馈复盘 <--- 证据校验",
        },
        "module2": {
            "core_mechanism": analysis_seed[:3],
            "system_position": analysis_seed[3:5] or analysis_seed[:2],
            "evolution": analysis_seed[5:7] or ["建议把原文中的版本与路线变化单独摘出来复盘。"],
            "why_design": analysis_seed[7:9] or ["之所以这样设计，通常是为了在复杂度、效果和可操作性之间取得平衡。"],
            "mermaid": build_mermaid(title, headings),
        },
        "module3": {
            "anti_intuition": next((paragraph for paragraph in paragraphs if any(token in paragraph for token in ["并非", "不是", "而是", "然而"])), tldr),
            "conflicts_or_version_diff": module3_conflicts,
            "search_internalized_tags": tags[:5],
            "learner_takeaway": "遇到看似确定的结论时，先问自己：它依赖什么时间点、什么版本、什么适用边界。",
        },
        "module4": {
            "getting_started": [
                f"先用一句话复述《{title}》要解决的核心问题。",
                "把关键阶段抄成自己的流程图，而不是只看原文结论。",
                "挑一个最小场景，解释输入是什么、决策在哪里、输出是什么。",
            ],
            "pitfalls": [
                "不要只记术语，不理解术语之间的因果关系。",
                "不要把作者结论直接当成绝对真理，先核对时间点和版本边界。",
                "不要跳过示例与过程，它们最能暴露真正机制。",
            ],
            "roi": [
                "投入：需要花时间把原文拆成主线、机制、边界三层。",
                "收益：你会从知道名词升级为能解释为什么。",
                "回报：后续迁移到输出、考试或落地实践时成本更低。",
            ],
        },
        "module5": {
            "faq": build_faq(title, tldr, faq_count),
            "review_entry": "如果你想继续温故而知新，请打开导师模式，让系统基于这份正文继续出题、追问、讲评和补讲。",
            "resources": unique_preserve_order(
                [
                    f"原始来源：{source}",
                    str(verification_report.get("summary") or ""),
                    "建议回读原文里的定义段、流程段、边界段和版本说明。",
                ]
            )[:6],
        },
        "coverage_trace": {
            "core_definition_and_value": True,
            "mechanism_and_runtime_logic": True,
            "system_position_and_collaboration": True,
            "history_and_version_changes": bool(audit_report.get("version_sensitive_sentences") or outdated_items),
            "scenarios_and_roi": True,
            "risks_misuse_and_boundaries": True,
        },
        "meta": {
            "generation_mode": generation_mode,
            "degraded_mode": degraded_mode,
            "verification_summary": str(verification_report.get("summary") or "当前没有验证摘要。"),
        },
    }
