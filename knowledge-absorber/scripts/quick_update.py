import re
from pathlib import Path

# 读取文件
html_path = Path(r"E:\开源Skills\skill\.trae\skills\knowledge-absorber\outputs\knowledge_20260316_老子想尔注-中华文库_ce1706c5\knowledge_card.interactive.html")
css_path = Path(r"E:\开源Skills\skill\.trae\skills\knowledge-absorber\assets\knowledge_card_ink_enhanced.css")

html_content = html_path.read_text(encoding="utf-8")
new_css = css_path.read_text(encoding="utf-8")

# 替换CSS
pattern = r'<style>.*?</style>'
new_style_block = f'<style>\n{new_css}\n</style>'
updated_html = re.sub(pattern, new_style_block, html_content, flags=re.DOTALL, count=1)

# 保存
html_path.write_text(updated_html, encoding="utf-8")
print("CSS updated successfully!")
