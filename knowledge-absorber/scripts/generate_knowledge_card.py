from __future__ import annotations

import argparse
from pathlib import Path

from knowledge_card_generation import generate_outputs


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_DIR = SKILL_DIR / "config"
DEFAULT_RAW_PATH = CONFIG_DIR / "raw_content.txt"
DEFAULT_AUDIT_REPORT = CONFIG_DIR / "raw_content.audit.json"
DEFAULT_VERIFICATION_REPORT = CONFIG_DIR / "verification_report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a contract-driven knowledge card from structured audit data")
    parser.add_argument("--raw-content", default=str(DEFAULT_RAW_PATH), help="Path to raw_content.txt")
    parser.add_argument("--audit-report", default=str(DEFAULT_AUDIT_REPORT), help="Path to raw_content.audit.json")
    parser.add_argument("--verification-report", default=str(DEFAULT_VERIFICATION_REPORT), help="Path to verification_report.json")
    parser.add_argument("--output-root", default=str(SKILL_DIR), help="Root directory where knowledge card folders are written")
    parser.add_argument(
        "--card-generation-mode",
        choices=["auto", "model", "rule"],
        default="rule",
        help="Card generation strategy. Use 'rule' for local fallback; 'auto'/'model' require external card data generation.",
    )
    parser.add_argument("--card-data-file", help="Path to model-authored knowledge_card.data.json used for rendering")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_path = Path(args.raw_content).resolve()
    audit_report_path = Path(args.audit_report).resolve()
    verification_report_path = Path(args.verification_report).resolve()
    output_root = Path(args.output_root).resolve()
    card_data_path = Path(args.card_data_file).resolve() if args.card_data_file else None
    if not raw_path.exists():
        raise FileNotFoundError(f"raw content not found: {raw_path}")
    if not audit_report_path.exists():
        raise FileNotFoundError(f"audit report not found: {audit_report_path}")
    if not verification_report_path.exists():
        raise FileNotFoundError(f"verification report not found: {verification_report_path}")
    if card_data_path is not None and not card_data_path.exists():
        raise FileNotFoundError(f"card data file not found: {card_data_path}")
    artifacts = generate_outputs(
        raw_path=raw_path,
        output_root=output_root,
        audit_report_path=audit_report_path,
        verification_report_path=verification_report_path,
        card_generation_mode=args.card_generation_mode,
        card_data_path=card_data_path,
    )
    print(f"Knowledge card Markdown saved to: {artifacts.markdown_path}")
    print(f"Knowledge card HTML saved to: {artifacts.source_html_path}")
    print(f"Knowledge card data saved to: {artifacts.data_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
