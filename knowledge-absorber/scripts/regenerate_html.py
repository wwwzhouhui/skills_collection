"""Quick script to regenerate HTML with new CSS styling"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from knowledge_card_rendering import render_html, infer_card_theme

# Path to the existing output
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "knowledge_20260316_老子想尔注-中华文库_ce1706c5"
DATA_FILE = OUTPUT_DIR / "_internal" / "knowledge_card.data.json"
VERIFICATION_FILE = OUTPUT_DIR / "_internal" / "verification_report.json"
HTML_OUTPUT = OUTPUT_DIR / "knowledge_card.source.html"

def main():
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}")
        print("Looking for alternative data files...")

        # Try to find data file in parent directory
        alt_data = OUTPUT_DIR / "knowledge_card.data.json"
        if alt_data.exists():
            print(f"Found alternative data file: {alt_data}")
            data_path = alt_data
        else:
            print("No data file found. Cannot regenerate HTML.")
            return 1
    else:
        data_path = DATA_FILE

    if not VERIFICATION_FILE.exists():
        print(f"Verification file not found: {VERIFICATION_FILE}")
        print("Using empty verification report...")
        verification_report = {
            "verified_count": 0,
            "disputed_count": 0,
            "outdated_count": 0,
            "unverified_count": 0
        }
    else:
        verification_report = json.loads(VERIFICATION_FILE.read_text(encoding="utf-8"))

    # Load card data
    card_data = json.loads(data_path.read_text(encoding="utf-8"))

    # Infer theme based on content
    title = card_data["header"]["title"]
    tags = card_data["header"]["tags"]
    # Get first few paragraphs for theme detection
    paragraphs = []
    if "module0" in card_data and "one_sentence" in card_data["module0"]:
        paragraphs.append(card_data["module0"]["one_sentence"])
    source = card_data["header"].get("source", "")

    theme = infer_card_theme(title, tags, paragraphs, source)

    print(f"Regenerating HTML with theme: {theme}")

    # Render HTML
    html_output = render_html(card_data, verification_report, theme)

    # Save HTML
    HTML_OUTPUT.write_text(html_output, encoding="utf-8")
    print(f"HTML regenerated successfully: {HTML_OUTPUT}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
