from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SYSTEM_PROMPT_PATH = SKILL_DIR / "references" / "system_prompt.md"
CONTRACT_BEGIN = "<!-- KA_CONTRACT:BEGIN -->"
CONTRACT_END = "<!-- KA_CONTRACT:END -->"


def load_prompt_text(path: Path | None = None) -> str:
    target_path = path or SYSTEM_PROMPT_PATH
    return target_path.read_text(encoding="utf-8-sig")


def extract_contract_block(prompt_text: str) -> str:
    pattern = re.compile(
        rf"{re.escape(CONTRACT_BEGIN)}\s*```yaml\s*(.*?)\s*```\s*{re.escape(CONTRACT_END)}",
        flags=re.DOTALL,
    )
    match = pattern.search(prompt_text)
    if not match:
        raise ValueError("system_prompt.md does not contain a KA contract block")
    return match.group(1).strip()


def load_contract(path: Path | None = None) -> Dict[str, Any]:
    prompt_text = load_prompt_text(path)
    raw_contract = extract_contract_block(prompt_text)
    try:
        contract = json.loads(raw_contract)
    except json.JSONDecodeError as exc:
        raise ValueError(f"KA contract block is not valid JSON-compatible YAML: {exc}") from exc
    validate_contract_shape(contract)
    return contract


def _ensure_string_list(values: Any, field_name: str) -> List[str]:
    if not isinstance(values, list) or not values or not all(isinstance(item, str) and item.strip() for item in values):
        raise ValueError(f"{field_name} must be a non-empty list of strings")
    return values


def _require_mapping(container: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    value = container.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_bool(container: Dict[str, Any], field_name: str) -> bool:
    value = container.get(field_name)
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def validate_contract_shape(contract: Dict[str, Any]) -> None:
    if not isinstance(contract, dict):
        raise ValueError("contract root must be an object")
    schema_version = contract.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("schema_version must be a non-empty string")

    header = _require_mapping(contract, "header")
    _ensure_string_list(header.get("required_fields"), "header.required_fields")

    coverage = _require_mapping(contract, "coverage")
    _ensure_string_list(coverage.get("required_categories"), "coverage.required_categories")

    modules = _require_mapping(contract, "modules")
    required_order = _ensure_string_list(modules.get("required_order"), "modules.required_order")
    for module_name in ("module2", "module3", "module5"):
        _require_mapping(modules, module_name)
    _ensure_string_list(modules["module2"].get("required_fields"), "modules.module2.required_fields")
    _ensure_string_list(modules["module3"].get("required_fields"), "modules.module3.required_fields")
    faq_count = modules["module5"].get("faq_count")
    if not isinstance(faq_count, int) or faq_count <= 0:
        raise ValueError("modules.module5.faq_count must be a positive integer")
    if required_order != ["module0", "module1", "module2", "module3", "module4", "module5"]:
        raise ValueError("modules.required_order must be module0..module5 in order")

    html_hooks = _require_mapping(contract, "html_hooks")
    _ensure_string_list(html_hooks.get("required"), "html_hooks.required")

    mentor = _require_mapping(contract, "mentor")
    _ensure_string_list(mentor.get("required"), "mentor.required")

    search = _require_mapping(contract, "search")
    _require_bool(search, "show_parent_headings")

    truth_anchor = _require_mapping(contract, "truth_anchor")
    allowed_status = _ensure_string_list(truth_anchor.get("allowed_status"), "truth_anchor.allowed_status")
    expected_status = {"confirmed", "disputed", "outdated", "unverified"}
    if set(allowed_status) != expected_status:
        raise ValueError("truth_anchor.allowed_status must match the expected status set")


def require_fields(container: Dict[str, Any], required_fields: Iterable[str], scope: str) -> List[str]:
    errors: List[str] = []
    for field_name in required_fields:
        value = container.get(field_name)
        if value in (None, "", [], {}):
            errors.append(f"{scope}.{field_name} is required")
    return errors

