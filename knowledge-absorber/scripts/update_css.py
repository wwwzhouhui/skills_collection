"""Replace CSS in existing HTML with enhanced ink style"""
from pathlib import Path
import re

# Paths
ASSETS_DIR = Path(__file__).parent.parent / "assets"
OUTPUT_DIR = Path(__file__).parent.parent / "outputs" / "knowledge_20260316_老子想尔注-中华文库_ce1706c5"
HTML_FILE = OUTPUT_DIR / "knowledge_card.interactive.html"
CSS_FILE = ASSETS_DIR / "knowledge_card_ink_enhanced.css"

def main():
    # Read files
    html_content = HTML_FILE.read_text(encoding="utf-8")
    new_css = CSS_FILE.read_text(encoding="utf-8")

    # Find and replace CSS between <style> tags
    # The pattern matches from <style> to </style>
    pattern = r'<style>.*?</style>'

    # Replace with new CSS
    new_style_block = f'<style>{new_css}</style>'
    updated_html = re.sub(pattern, new_style_block, html_content, flags=re.DOTALL, count=1)

    # Write back
    HTML_FILE.write_text(updated_html, encoding="utf-8")
    print(f"✓ CSS updated successfully in: {HTML_FILE}")
    print(f"  Applied enhanced Chinese classical styling")

if __name__ == "__main__":
    main()
