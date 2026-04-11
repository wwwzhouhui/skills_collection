from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Dict, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"
BASE_CSS_PATH = ASSETS_DIR / "knowledge_card_base.css"
MODERN_CSS_PATH = ASSETS_DIR / "knowledge_card_modern.css"
INK_CSS_PATH = ASSETS_DIR / "knowledge_card_ink.css"
INK_ENHANCED_CSS_PATH = ASSETS_DIR / "knowledge_card_ink_enhanced.css"
DESIGN_CSS_PATH = ASSETS_DIR / "knowledge_card_design.css"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def safe_name(name: str, fallback: str = "knowledge-card") -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', " ", name).strip().rstrip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:48] or fallback


def short_slug(title: str, fallback: str = "knowledge-card") -> str:
    cleaned = safe_name(title, fallback=fallback)
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned[:20] or fallback


def infer_card_theme(title: str, tags: Sequence[str], paragraphs: Sequence[str], source: str) -> str:
    # 扩展的国学关键词列表
    humanities_keywords = [
        # 经典文献
        "论语", "庄子", "道德经", "史记", "诗经", "易经", "孟子", "荀子",
        "春秋", "左传", "礼记", "周易", "尚书", "大学", "中庸",
        # 学派与思想
        "国学", "古文", "佛", "儒", "道", "哲学", "人文",
        "儒家", "道家", "佛家", "法家", "墨家", "兵家",
        "禅宗", "理学", "心学", "玄学",
        # 历史人物
        "孔子", "老子", "孟子", "庄子", "荀子", "墨子", "韩非子",
        "朱熹", "王阳明", "程颐", "程颢",
        # 文学体裁
        "古诗", "词", "赋", "骈文", "散文", "文言文",
        # 其他
        "经史子集", "四书五经", "诸子百家", "传统文化"
    ]

    # 组合标题、来源、标签和前几段内容进行检测
    combined = "\n".join([title, source, *list(tags[:5]), *list(paragraphs[:5])])

    # 如果包含任何国学关键词，使用水墨风格
    if any(keyword in combined for keyword in humanities_keywords):
        return "ink"

    # 否则使用现代风格
    return "modern"


def load_card_styles(theme: str) -> str:
    if theme == "ink":
        # Use enhanced ink CSS with full Chinese classical styling
        return read_text(INK_ENHANCED_CSS_PATH)
    elif theme == "modern":
        return read_text(DESIGN_CSS_PATH)

    # Default to enhanced ink for Chinese content
    return read_text(INK_ENHANCED_CSS_PATH)


def build_output_paths(output_root: Path, title: str, date_stamp: str) -> tuple[Path, Path, Path, Path]:
    stable_hash = __import__("hashlib").sha1(title.encode("utf-8")).hexdigest()[:8]
    folder_name = f"knowledge_{date_stamp}_{short_slug(title)}_{stable_hash}"
    output_dir = output_root / folder_name
    markdown_path = output_dir / "knowledge_card.md"
    source_html_path = output_dir / "knowledge_card.source.html"
    data_path = output_dir / "_internal" / "knowledge_card.data.json"
    return output_dir, markdown_path, source_html_path, data_path


def status_label(status: str) -> str:
    mapping = {"confirmed": "已确认", "disputed": "存在争议", "outdated": "已过时", "unverified": "待人工确认"}
    return mapping.get(status, status or "待人工确认")


def list_markdown(items: Sequence[str]) -> str:
    return "\n".join([f"- {item}" for item in items]) if items else ""


def render_markdown(data: Dict[str, Any], verification_report: Dict[str, Any]) -> str:
    faq_block = "\n".join([f"- **{item['question']}**：{item['answer']}" for item in data["module5"]["faq"]])
    pending = [str(item) for item in (verification_report.get("unverified_items") or []) if isinstance(item, str)]
    pending_count = len(pending)
    pending_block = f"\n\n> 待人工确认：{pending_count} 条（为保持文件简洁，此处不展开明细）。" if pending_count else ""
    return f"""# {data['header']['title']}

> 作者：{data['header']['author']}
> 标签：{' / '.join(data['header']['tags'])}
> 来源：{data['header']['source']}
> 适用对象 / 一句话定位：{data['header']['audience_positioning']}

## 模块 0：核心摘要

### 一句话讲透
{data['module0']['one_sentence']}

### 认知挂钩
{data['module0']['analogy']}

### 真理锚点
> [{status_label(data['module0']['truth_anchor']['status'])}] {data['module0']['truth_anchor']['text']}
>
> 说明：{data['module0']['truth_anchor']['note']}

## 模块 1：概念破冰

### 巧记卡片
{data['module1']['mnemonic']}

### 故事引入
{data['module1']['story']}

### 可视化
```text
{data['module1']['ascii_visual']}
```

## 模块 2：深度解析

### 核心机制
{list_markdown(data['module2']['core_mechanism'])}

### 系统位置 / 协同关系
{list_markdown(data['module2']['system_position'])}

### 演化脉络
{list_markdown(data['module2']['evolution'])}

### 为什么这样设计
{list_markdown(data['module2']['why_design'])}

```mermaid
{data['module2']['mermaid']}
```

## 模块 3：深度裂变

### 反常识点
{data['module3']['anti_intuition']}

### 冲突 / 版本差异
{list_markdown(data['module3']['conflicts_or_version_diff'])}

### 搜索内化标签
{list_markdown(data['module3']['search_internalized_tags'])}

### 对学习者的启示
{data['module3']['learner_takeaway']}

## 模块 4：实战指南

### 如何开始
{list_markdown(data['module4']['getting_started'])}

### 避坑指南
{list_markdown(data['module4']['pitfalls'])}

### ROI 分析
{list_markdown(data['module4']['roi'])}

## 模块 5：温故知新

### FAQ
{faq_block}

### 温故而知新入口
{data['module5']['review_entry']}

### 参考资源
{list_markdown(data['module5']['resources'])}

### 验证摘要
{data['meta']['verification_summary']}{pending_block}
"""


def render_status_badge(status: str) -> str:
    return f'<span class="truth-status-badge status-{html.escape(status)}">{html.escape(status_label(status))}</span>'


def list_html(items: Sequence[str], section_id: str, heading_id: str) -> str:
    li_html = "".join(
        [
            f'<li data-search-block="true" data-parent-section="{html.escape(section_id)}" data-parent-heading="{html.escape(heading_id)}">{html.escape(item)}</li>'
            for item in items
        ]
    )
    return f"<ul>{li_html}</ul>"


def build_search_script() -> str:
    return """
<script>
const savedTheme=localStorage.getItem('knowledge-card-theme')||'light';document.documentElement.setAttribute('data-theme',savedTheme);document.getElementById('theme-toggle').addEventListener('click',()=>{const next=document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',next);localStorage.setItem('knowledge-card-theme',next)});const searchInput=document.getElementById('search-input');const sections=Array.from(document.querySelectorAll('section[data-section-id]'));const headings=Array.from(document.querySelectorAll('[data-heading-id]'));const blocks=Array.from(document.querySelectorAll('[data-search-block="true"]'));function showNode(node){if(node)node.classList.remove('hidden')}function hideNode(node){if(node)node.classList.add('hidden')}function restoreAll(){sections.forEach(showNode);headings.forEach(showNode);blocks.forEach(showNode)}function showParentHeading(block){const sectionId=block.getAttribute('data-parent-section');const headingId=block.getAttribute('data-parent-heading');if(sectionId){const section=document.querySelector(`section[data-section-id="${sectionId}"]`);showNode(section);if(section){showNode(section.querySelector('h2[data-heading-id]'))}}if(headingId){showNode(document.querySelector(`[data-heading-id="${headingId}"]`))}}function applyStrictFilter(term){if(!term){restoreAll();return}sections.forEach(hideNode);headings.forEach(hideNode);blocks.forEach(hideNode);blocks.forEach((block)=>{const text=(block.innerText||block.textContent||'').toLowerCase();if(text.includes(term)){showNode(block);showParentHeading(block)}})}if(searchInput){searchInput.addEventListener('input',(event)=>{applyStrictFilter((event.target.value||'').toLowerCase().trim())})}document.querySelectorAll('.faq-item > summary').forEach((summary)=>{summary.addEventListener('click',(event)=>{event.preventDefault();const item=summary.parentElement;const willOpen=!item.hasAttribute('open');document.querySelectorAll('.faq-item').forEach((other)=>{other.removeAttribute('open')});if(willOpen){item.setAttribute('open','open')}})});mermaid.initialize({startOnLoad:true,securityLevel:'loose'});
</script>
""".strip()


def render_html(data: Dict[str, Any], verification_report: Dict[str, Any], theme: str) -> str:
    styles = load_card_styles(theme)
    tags_html = "".join([f'<span class="tag">{html.escape(tag)}</span>' for tag in data["header"]["tags"]])

    def compact_text(value: Any, limit: int = 240) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "…"

    def looks_like_codeish(value: str) -> bool:
        text = str(value or "")
        lowered = text.lower()
        if any(token in lowered for token in ["name_for_human", "name_for_model", "description_for_model", "parameters"]):
            return True
        if any(token in lowered for token in ["payload =", "json.dumps", "headers =", "def ", "class ", "import "]):
            return True
        if re.search(r"[{}\[\]]", text) and (":" in text or "=" in text):
            return True
        if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*=\s*.+", text):
            return True
        return False

    claims = verification_report.get("claims") if isinstance(verification_report.get("claims"), list) else []
    counts = {"confirmed": 0, "disputed": 0, "outdated": 0, "unverified": 0}
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        status = str(claim.get("status") or "")
        if status in counts:
            counts[status] += 1
    total_claims = sum(counts.values())

    badges = []
    if bool((data.get("meta") or {}).get("degraded_mode", False)):
        badges.append('<span class="badge badge-info">生成：本地规则</span>')
    elif (data.get("meta") or {}).get("generation_mode"):
        badges.append(f'<span class="badge badge-info">生成：{html.escape(str(data["meta"]["generation_mode"]))}</span>')

    if total_claims:
        if counts["unverified"]:
            badges.append(f'<span class="badge badge-warn">待确认：{counts["unverified"]}/{total_claims}</span>')
        else:
            badges.append(f'<span class="badge badge-ok">验证：{counts["confirmed"]}/{total_claims}</span>')
        if counts["disputed"]:
            badges.append(f'<span class="badge badge-warn">争议：{counts["disputed"]}</span>')
        if counts["outdated"]:
            badges.append(f'<span class="badge badge-warn">过时：{counts["outdated"]}</span>')

    verification_summary = str((data.get("meta") or {}).get("verification_summary") or "")
    unverified_items = [str(item) for item in (verification_report.get("unverified_items") or []) if isinstance(item, str)]

    pending_section = ""
    if unverified_items:
        display_items = [item for item in unverified_items if not looks_like_codeish(item)]
        shown = display_items[:6]
        li_html = "".join(
            [
                f'<li data-search-block="true" data-parent-section="pending-verification" data-parent-heading="pending-verification-heading"><span>{html.escape(compact_text(item))}</span></li>'
                for item in shown
            ]
        )
        if shown:
            more_note = (
                f'<p class="small muted">仅展示前 {len(shown)} 条；共 {len(unverified_items)} 条。</p>'
                if len(unverified_items) > len(shown)
                else ""
            )
        else:
            more_note = '<p class="small muted">待确认项多为代码/参数片段，为保持页面清爽，这里不展示明细。</p>'
        pending_section = (
            '<section id="pending-verification" class="quality-subdetails">'
            '<details>'
            f'<summary data-heading-id="pending-verification-heading"><span>待人工确认</span><span class="badge badge-warn">{len(unverified_items)}</span></summary>'
            f'<ul class="pending-list">{li_html}</ul>' if li_html else ""
            f"{more_note}"
            "</details>"
            "</section>"
        )

    checked_urls = [str(item) for item in (verification_report.get("checked_urls") or []) if isinstance(item, str)]
    fetch_notes = verification_report.get("evidence_fetch_notes") if isinstance(verification_report.get("evidence_fetch_notes"), dict) else {}
    source_section = ""
    if checked_urls:
        url_li = "".join(
            [
                (
                    f"<li><code>{html.escape(url)}</code>"
                    + (
                        f' <span class="small muted">({html.escape(str(fetch_notes.get(url) or ""))})</span>'
                        if str(fetch_notes.get(url) or "") and str(fetch_notes.get(url) or "") != "ok"
                        else ""
                    )
                    + "</li>"
                )
                for url in checked_urls[:6]
            ]
        )
        source_section = (
            '<section class="quality-subdetails">'
            "<details>"
            f"<summary>已尝试验证的链接（{len(checked_urls)}）</summary>"
            f'<ul class="url-list">{url_li}</ul>'
            "</details>"
            "</section>"
        )

    gen_note = (
        '<p class="small"><strong>生成方式：</strong>本地规则（无需模型；内容可能更简略）。</p>'
        if bool((data.get("meta") or {}).get("degraded_mode", False))
        else ""
    )
    summary_line = f'<p class="small"><strong>验证摘要：</strong>{html.escape(verification_summary)}</p>' if verification_summary else ""
    badges_html = "".join(badges)
    quality_panel = (
        '<section class="quality-panel" id="quality-panel">'
        "<details>"
        f'<summary><span class="quality-title">质量与验证</span><span class="quality-badges">{badges_html}</span></summary>'
        f'<div class="quality-body">{gen_note}{summary_line}{pending_section}{source_section}</div>'
        "</details>"
        "</section>"
    )
    faq_html = "\n".join([
        '<details class="faq-item" data-search-block="true" data-parent-section="module-5" data-parent-heading="module-5-faq">'
        f'<summary>{html.escape(item["question"])}</summary><div class="faq-answer"><p>{html.escape(item["answer"])}</p></div></details>'
        for item in data["module5"]["faq"]
    ])
    search_tags_html = "".join([
        f'<span class="tag" data-search-block="true" data-parent-section="module-3" data-parent-heading="module-3-tags">{html.escape(tag)}</span>'
        for tag in data["module3"]["search_internalized_tags"]
    ])
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light" data-card-theme="{html.escape(theme)}">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(data['header']['title'])}</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>{styles}</style>
</head>
<body>
  <div id="knowledge-toolbar" class="toolbar"><div class="toolbar-inner"><input id="search-input" class="toolbar-search" type="text" placeholder="搜索当前正文内容..."><div class="toolbar-actions" id="knowledge-toolbar-actions"><button id="theme-toggle" class="toolbar-button secondary" type="button">🌓</button><button class="toolbar-button primary" type="button" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">回到顶部</button></div></div></div>
  <div class="shell">
    <header class="hero">
      <p class="muted">作者：{html.escape(data['header']['author'])}</p>
      <h1>{html.escape(data['header']['title'])}</h1>
      <p class="hero-subtitle">适用对象 / 一句话定位：{html.escape(data['header']['audience_positioning'])}</p>
      <p class="source-line">来源：<code>{html.escape(data['header']['source'])}</code></p>
      <div class="meta">{tags_html}</div>
    </header>
    
    <main id="content-area">
      <section data-section-id="module-0">
        <div class="module-0-left">
          <h2 data-heading-id="module-0-heading">模块 0：核心摘要</h2>
          <h3 data-heading-id="module-0-one-sentence">一句话讲透</h3>
          <p data-search-block="true" data-parent-section="module-0" data-parent-heading="module-0-one-sentence" style="font-size: 20px; font-weight: 500;">{html.escape(data['module0']['one_sentence'])}</p>
          <h3 data-heading-id="module-0-analogy">认知挂钩</h3>
          <p data-search-block="true" data-parent-section="module-0" data-parent-heading="module-0-analogy">{html.escape(data['module0']['analogy'])}</p>
        </div>
        <div class="module-0-right">
          <h3 data-heading-id="module-0-truth-anchor">真理锚点</h3>
          <div class="truth-anchor" data-search-block="true" data-parent-section="module-0" data-parent-heading="module-0-truth-anchor">
            <div class="truth-status-row">{render_status_badge(data['module0']['truth_anchor']['status'])}</div>
            <blockquote class="quote" style="font-size: 16px;">{html.escape(data['module0']['truth_anchor']['text'])}</blockquote>
            <p style="font-size: 13px; margin-top: 8px;">{html.escape(data['module0']['truth_anchor']['note'])}</p>
          </div>
        </div>
      </section>

      <section data-section-id="module-1"><h2 data-heading-id="module-1-heading">模块 1：概念破冰</h2><h3 data-heading-id="module-1-mnemonic">巧记卡片</h3><div class="mnemonic-card" data-search-block="true" data-parent-section="module-1" data-parent-heading="module-1-mnemonic">{html.escape(data['module1']['mnemonic'])}</div><h3 data-heading-id="module-1-story">故事引入</h3><p data-search-block="true" data-parent-section="module-1" data-parent-heading="module-1-story">{html.escape(data['module1']['story'])}</p><h3 data-heading-id="module-1-visual">可视化</h3><div class="ascii" data-search-block="true" data-parent-section="module-1" data-parent-heading="module-1-visual">{html.escape(data['module1']['ascii_visual'])}</div></section>
      <section data-section-id="module-2"><h2 data-heading-id="module-2-heading">模块 2：深度解析</h2><div class="module-subgrid"><div><h3 data-heading-id="module-2-core-mechanism">核心机制</h3>{list_html(data['module2']['core_mechanism'],'module-2','module-2-core-mechanism')}</div><div><h3 data-heading-id="module-2-system-position">系统位置 / 协同关系</h3>{list_html(data['module2']['system_position'],'module-2','module-2-system-position')}</div><div><h3 data-heading-id="module-2-evolution">演化脉络</h3>{list_html(data['module2']['evolution'],'module-2','module-2-evolution')}</div><div><h3 data-heading-id="module-2-why-design">为什么这样设计</h3>{list_html(data['module2']['why_design'],'module-2','module-2-why-design')}</div></div><h3 data-heading-id="module-2-mermaid">Mermaid 图表</h3><div class="mermaid" data-search-block="true" data-parent-section="module-2" data-parent-heading="module-2-mermaid">{html.escape(data['module2']['mermaid'])}</div></section>
      <section data-section-id="module-3"><h2 data-heading-id="module-3-heading">模块 3：深度裂变</h2><div class="fission-section"><h3 data-heading-id="module-3-anti-intuition">反常识点</h3><p data-search-block="true" data-parent-section="module-3" data-parent-heading="module-3-anti-intuition">{html.escape(data['module3']['anti_intuition'])}</p><h3 data-heading-id="module-3-conflicts">冲突 / 版本差异</h3>{list_html(data['module3']['conflicts_or_version_diff'],'module-3','module-3-conflicts')}<h3 data-heading-id="module-3-tags">搜索内化标签</h3><div class="search-tags">{search_tags_html}</div><h3 data-heading-id="module-3-takeaway">对学习者的启示</h3><p data-search-block="true" data-parent-section="module-3" data-parent-heading="module-3-takeaway">{html.escape(data['module3']['learner_takeaway'])}</p></div></section>
      <section data-section-id="module-4"><h2 data-heading-id="module-4-heading">模块 4：实战指南</h2><div class="grid-two"><div><h3 data-heading-id="module-4-getting-started">如何开始</h3>{list_html(data['module4']['getting_started'],'module-4','module-4-getting-started')}</div><div><h3 data-heading-id="module-4-pitfalls">避坑指南</h3>{list_html(data['module4']['pitfalls'],'module-4','module-4-pitfalls')}</div></div><h3 data-heading-id="module-4-roi">ROI 分析</h3>{list_html(data['module4']['roi'],'module-4','module-4-roi')}</section>
    </main>

    <aside class="sidebar-content">
      {quality_panel}
      <section data-section-id="module-5">
        <h2 data-heading-id="module-5-heading" style="font-size: 20px;">模块 5：温故知新</h2>
        <h3 data-heading-id="module-5-faq">FAQ</h3>
        <div class="faq-grid">{faq_html}</div>
        <div class="mentor-entry-card" data-search-block="true" data-parent-section="module-5" data-parent-heading="module-5-review-entry" style="padding: 24px;">
          <p style="font-size: 14px;">{html.escape(data['module5']['review_entry'])}</p>
          <a href="#knowledge-toolbar" class="mentor-entry-link" data-open-mentor="true" style="font-size: 14px; padding: 8px 20px;">打开导师模式</a>
        </div>
        <h3 data-heading-id="module-5-resources" style="margin-top: 24px;">参考资源</h3>
        {list_html(data['module5']['resources'],'module-5','module-5-resources')}
      </section>
    </aside>
  </div>
  {build_search_script()}
</body>
</html>"""
