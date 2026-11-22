#!/usr/bin/env python3.12
"""CloakBrowser Google Search Example

使用 CloakBrowser（隐身 Chromium）搜索 Google，
绕过常见的 bot 检测。

安装: pip install cloakbrowser
运行: python3.12 google_search_worldcup.py
"""

from cloakbrowser import launch

browser = launch(headless=True)
page = browser.new_page()

# 打开 Google
page.goto("https://www.google.com", timeout=30000)
page.wait_for_timeout(2000)

# 处理 Cookie 同意页面（如果有）
accept_btn = (
    page.query_selector('button:has-text("Accept all")')
    or page.query_selector('button:has-text("全部接受")')
    or page.query_selector('[aria-label*="Accept"]')
)
if accept_btn:
    accept_btn.click()
    page.wait_for_timeout(2000)

# 搜索
search_box = page.query_selector('textarea[name="q"]') or page.query_selector('input[name="q"]')
search_box.fill("2026年6月12日世界杯情况")
search_box.press("Enter")

# 等待结果加载
page.wait_for_timeout(5000)
print(f"搜索: {page.title()}\n")

# 提取搜索结果
results = page.query_selector_all(".tF2Cxc")
for i, result in enumerate(results[:10], 1):
    title_el = result.query_selector("h3")
    link_el = result.query_selector("a")
    title = title_el.inner_text() if title_el else "No title"
    href = link_el.get_attribute("href") if link_el else "No URL"
    print(f"{i}. {title}")
    print(f"   {href}\n")

browser.close()
