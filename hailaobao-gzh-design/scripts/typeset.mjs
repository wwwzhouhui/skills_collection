#!/usr/bin/env node
// hailaobao-gzh-design 主渲染脚本
// Usage: node typeset.mjs --input <md> --scheme <id> [--title <t>] [--out <html>]

import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, dirname, basename } from 'node:path';
import { getSchemeStyles, SCHEMES } from './schemes.mjs';

// -----------------------------------------------------------------------------
// CLI 参数解析（零依赖，避免用户 npm install）
// -----------------------------------------------------------------------------
const args = process.argv.slice(2);
const getArg = (flag) => {
  const i = args.indexOf(flag);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : undefined;
};

const inputPath = getArg('--input');
const schemeId = getArg('--scheme') || 'jade-business';
const title = getArg('--title') || '公众号排版';
let outPath = getArg('--out');

if (!inputPath) {
  console.error('缺少 --input <markdown 文件>');
  console.error('可用 scheme:', Object.keys(SCHEMES).join(', '));
  process.exit(1);
}

const resolvedInput = resolve(process.cwd(), inputPath);
if (!outPath) {
  const dir = dirname(resolvedInput);
  const base = basename(resolvedInput).replace(/\.[^.]+$/, '');
  outPath = resolve(dir, `${base}.html`);
} else {
  outPath = resolve(process.cwd(), outPath);
}

const markdown = readFileSync(resolvedInput, 'utf-8');
const { scheme, styles } = getSchemeStyles(schemeId);

// -----------------------------------------------------------------------------
// 极小 Markdown parser。够用：headings、paragraphs、bold、italic、code、
// blockquote、hr、lists、images、links、代码块、SummaryCard、InfoCard。
// -----------------------------------------------------------------------------
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// 内联元素：**bold**、*em*、`code`、[link](url)、允许 <span style="color:#XXX">
const renderInline = (text) => {
  let t = text;

  // 保护 code span（先占位再回填，避免其他规则破坏它）
  const codeSpans = [];
  t = t.replace(/`([^`]+)`/g, (_, code) => {
    codeSpans.push(code);
    return `CODE${codeSpans.length - 1}`;
  });

  // 保护允许的 <span style="color:#XXX">…</span>
  const colorSpans = [];
  t = t.replace(/<span\s+style="color:(#[0-9A-Fa-f]{6})">([\s\S]*?)<\/span>/g, (_, color, inner) => {
    colorSpans.push({ color, inner });
    return `COLOR${colorSpans.length - 1}`;
  });

  // 其余 HTML 标签清理掉
  t = t.replace(/<\/?[^>]+>/g, '');

  // escape 剩余的 & < > "
  t = esc(t);

  // 加粗、斜体、链接
  t = t.replace(/\*\*([^*]+)\*\*/g, (_, s) => `<strong style="${styles.strong}">${s}</strong>`);
  t = t.replace(/(^|[^*])\*([^*\n]+)\*/g, (_, pre, s) => `${pre}<em style="${styles.em}">${s}</em>`);
  t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, txt, url) => {
    const safe = /^https?:\/\//.test(url) ? url : '#';
    return `<a href="${esc(safe)}" style="${styles.link}">${txt}</a>`;
  });

  // 回填 code span 与 color span
  t = t.replace(/CODE(\d+)/g, (_, i) => `<code style="${styles.inlineCode}">${esc(codeSpans[+i])}</code>`);
  t = t.replace(/COLOR(\d+)/g, (_, i) => {
    const { color, inner } = colorSpans[+i];
    return `<span style="color:${color}">${renderInline(inner)}</span>`;
  });

  return t;
};

// 标题的 `|` 高级语法
const renderBadgeBar = (serial, main, sub) => {
  const bb = styles.badgeBar;
  let html = `<section style="${bb.wrap}"><section style="${bb.badge}">${esc(serial)}</section><section style="${bb.title}">${renderInline(main || '')}</section><section style="${bb.rule}"><span><br /></span></section>`;
  if (sub) html += `<span style="${styles.subtitle}">${renderInline(sub)}</span>`;
  return `${html}</section>`;
};

const renderHeading = (level, raw) => {
  const parts = raw.split('|').map((p) => p.trim()).filter(Boolean);
  if (styles.badgeBar && parts.length > 1 && (level === 1 || level === 2)) {
    return level === 1
      ? renderBadgeBar(parts[0], parts[1], parts[2])
      : renderBadgeBar(parts[0], parts[1]);
  }
  if (level === 1) {
    if (parts.length === 1) return `<h1 style="${styles.h1}">${renderInline(parts[0])}</h1>`;
    const [serial, main, sub] = parts;
    let html = `<h1 style="${styles.h1}"><span style="${styles.kicker}">${esc(serial)}</span>${renderInline(main || '')}`;
    if (sub) html += `<span style="${styles.subtitle}">${renderInline(sub)}</span>`;
    return html + `</h1>`;
  }
  if (level === 2) {
    if (parts.length === 1) return `<h2 style="${styles.h2}">${renderInline(parts[0])}</h2>`;
    const [tag, main] = parts;
    return `<h2 style="${styles.h2}"><span style="${styles.kicker}">${esc(tag)}</span>${renderInline(main || '')}</h2>`;
  }
  if (level === 3) {
    if (parts.length === 1) return `<h3 style="${styles.h3}">${renderInline(parts[0])}</h3>`;
    const [tag, main] = parts;
    return `<h3 style="${styles.h3}"><span style="${styles.kicker}">${esc(tag)}</span>${renderInline(main || '')}</h3>`;
  }
  return `<h4 style="${styles.h4}">${renderInline(parts[0] || raw)}</h4>`;
};

// -----------------------------------------------------------------------------
// 块级 parser：一行行扫，按缓冲区攒 paragraph / list / blockquote / code block /
// 自定义组件
// -----------------------------------------------------------------------------
const lines = markdown.split(/\r?\n/);
const out = [];
let i = 0;

const flushParagraph = (buf) => {
  if (buf.length === 0) return;
  const text = buf.join(' ').trim();
  if (text) out.push(`<p style="${styles.p}">${renderInline(text)}</p>`);
  buf.length = 0;
};

const paraBuf = [];

while (i < lines.length) {
  const line = lines[i];
  const trimmed = line.trim();

  // 空行 = 段落分界
  if (trimmed === '') { flushParagraph(paraBuf); i += 1; continue; }

  // 代码块 ```
  const codeFence = trimmed.match(/^```(\w*)\s*$/);
  if (codeFence) {
    flushParagraph(paraBuf);
    const codeLines = [];
    i += 1;
    while (i < lines.length && !lines[i].trim().startsWith('```')) {
      codeLines.push(lines[i]);
      i += 1;
    }
    i += 1; // 关闭的 ```
    if (styles.promptWindow) {
      const pw = styles.promptWindow;
      const dots = pw.dots.map((c) => `<span style="display:inline-block;margin-right:6px;font-size:13px;line-height:34px;vertical-align:middle;color:${c}">●</span>`).join('');
      out.push(`<section style="${pw.root}"><section style="${pw.bar}">${dots}</section><pre style="${pw.body}"><code>${esc(codeLines.join('\n'))}</code></pre></section>`);
    } else {
      out.push(`<pre style="${styles.code}"><code>${esc(codeLines.join('\n'))}</code></pre>`);
    }
    continue;
  }

  // 分割线
  if (/^-{3,}$/.test(trimmed) || /^\*{3,}$/.test(trimmed)) {
    flushParagraph(paraBuf);
    out.push(`<hr style="${styles.hr}" />`);
    i += 1;
    continue;
  }

  // 标题
  const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
  if (headingMatch) {
    flushParagraph(paraBuf);
    out.push(renderHeading(headingMatch[1].length, headingMatch[2]));
    i += 1;
    continue;
  }

  // 引用块
  if (trimmed.startsWith('>')) {
    flushParagraph(paraBuf);
    const quoteBuf = [];
    while (i < lines.length && lines[i].trim().startsWith('>')) {
      quoteBuf.push(lines[i].trim().replace(/^>\s?/, ''));
      i += 1;
    }
    out.push(`<blockquote style="${styles.blockquote}">${renderInline(quoteBuf.join(' '))}</blockquote>`);
    continue;
  }

  // 无序列表
  if (/^[-*+]\s+/.test(trimmed)) {
    flushParagraph(paraBuf);
    const items = [];
    while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
      items.push(lines[i].trim().replace(/^[-*+]\s+/, ''));
      i += 1;
    }
    out.push(`<ul style="${styles.ul}">${items.map((it) => `<li style="${styles.li}">${renderInline(it)}</li>`).join('')}</ul>`);
    continue;
  }

  // 有序列表
  if (/^\d+\.\s+/.test(trimmed)) {
    flushParagraph(paraBuf);
    const items = [];
    while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
      items.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
      i += 1;
    }
    out.push(`<ol style="${styles.ol}">${items.map((it) => `<li style="${styles.li}">${renderInline(it)}</li>`).join('')}</ol>`);
    continue;
  }

  // 图片行（单独一行的 ![alt](url)）
  const imgMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)\s*$/);
  if (imgMatch) {
    flushParagraph(paraBuf);
    const url = /^https?:\/\//.test(imgMatch[2]) ? imgMatch[2] : '';
    if (url) out.push(`<img src="${esc(url)}" alt="${esc(imgMatch[1])}" style="${styles.img}" />`);
    i += 1;
    continue;
  }

  // SummaryCard 组件
  const sumOpen = trimmed.match(/^<SummaryCard\s+title="([^"]+)">\s*$/);
  if (sumOpen) {
    flushParagraph(paraBuf);
    const inner = [];
    i += 1;
    while (i < lines.length && !lines[i].trim().startsWith('</SummaryCard>')) {
      inner.push(lines[i]);
      i += 1;
    }
    i += 1;
    const innerHtml = renderInnerMarkdown(inner.join('\n'));
    out.push(`<section style="${styles.summary.root}"><div style="${styles.summary.title}">${esc(sumOpen[1])}</div><div style="${styles.summary.body}">${innerHtml}</div></section>`);
    continue;
  }

  // InfoCard 组件
  const infoOpen = trimmed.match(/^<InfoCard\s+title="([^"]+)">\s*$/);
  if (infoOpen) {
    flushParagraph(paraBuf);
    const inner = [];
    i += 1;
    while (i < lines.length && !lines[i].trim().startsWith('</InfoCard>')) {
      inner.push(lines[i]);
      i += 1;
    }
    i += 1;
    const innerHtml = renderInnerMarkdown(inner.join('\n'));
    out.push(`<section style="${styles.info.root}"><div style="${styles.info.title}">${esc(infoOpen[1])}</div><div style="${styles.info.body}">${innerHtml}</div></section>`);
    continue;
  }

  // 其余归到 paragraph
  paraBuf.push(trimmed);
  i += 1;
}
flushParagraph(paraBuf);

// 组件内部：跑一遍简化的段落 / 列表 / 内联渲染
function renderInnerMarkdown(text) {
  const ls = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const chunks = [];
  const bullets = [];
  const flushBullets = () => {
    if (bullets.length) {
      chunks.push(`<ul style="${styles.ul}">${bullets.map((b) => `<li style="${styles.li}">${renderInline(b)}</li>`).join('')}</ul>`);
      bullets.length = 0;
    }
  };
  for (const l of ls) {
    if (/^[-*+]\s+/.test(l)) { bullets.push(l.replace(/^[-*+]\s+/, '')); continue; }
    flushBullets();
    chunks.push(`<p style="${styles.p}">${renderInline(l)}</p>`);
  }
  flushBullets();
  return chunks.join('');
}

// -----------------------------------------------------------------------------
// 拼装最终 HTML：包一层"复制到公众号"外壳
// -----------------------------------------------------------------------------
const bodyHtml = out.join('\n');
const escapedTitle = esc(title);

const page = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>${escapedTitle} · 公众号排版</title>
<style>
  html,body{margin:0;background:#F1F3F6;color:#111;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}
  .topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:16px;background:#0F172A;color:#F1F5F9;padding:12px 20px;box-shadow:0 4px 20px rgba(15,23,42,.14)}
  .topbar .name{font-size:14px;font-weight:600;letter-spacing:.04em}
  .topbar .scheme{font-size:12px;opacity:.7}
  .topbar .grow{flex:1}
  .btn{appearance:none;border:0;padding:10px 22px;border-radius:999px;background:#10B981;color:#052E1D;font-weight:700;font-size:14px;cursor:pointer;transition:transform .12s ease,background .12s ease}
  .btn:hover{background:#0EA36F}
  .btn:active{transform:scale(.97)}
  .btn.copied{background:#F1F5F9;color:#059669}
  .canvas{padding:32px 12px 80px}
  .paper{background:#fff;border-radius:14px;box-shadow:0 8px 40px rgba(15,23,42,.06);max-width:860px;margin:0 auto;overflow:hidden}
  .tips{max-width:860px;margin:20px auto 0;font-size:12px;color:#64748B;padding:0 12px;line-height:1.7}
  .tips code{background:#E2E8F0;padding:1px 6px;border-radius:4px}
</style>
</head>
<body>
<div class="topbar">
  <span class="name">${escapedTitle}</span>
  <span class="scheme">· ${esc(scheme.name)}</span>
  <div class="grow"></div>
  <button id="copyBtn" class="btn">复制到公众号</button>
</div>
<div class="canvas">
  <div class="paper">
    <article id="preview" style="${styles.article}">
${bodyHtml}
    </article>
  </div>
  <div class="tips">
    点击「复制到公众号」按钮 → 打开微信公众号编辑器 → 直接 <code>Ctrl/⌘+V</code> 粘贴。<br />
    如果你的浏览器不支持富文本剪贴板，会自动回退到 HTML 源码复制；在这种情况下，用微信编辑器的"编辑源码"入口贴进去即可。
  </div>
</div>
<script>
  const btn = document.getElementById('copyBtn');
  const preview = document.getElementById('preview');
  btn.addEventListener('click', async () => {
    const html = preview.outerHTML;
    const plain = preview.innerText;
    try {
      if (navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([
          new ClipboardItem({
            'text/html': new Blob([html], { type: 'text/html' }),
            'text/plain': new Blob([plain], { type: 'text/plain' }),
          }),
        ]);
      } else {
        // 回退：用 document.execCommand('copy')
        const range = document.createRange();
        range.selectNodeContents(preview);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.execCommand('copy');
        sel.removeAllRanges();
      }
      btn.textContent = '已复制 ✓ 去公众号粘贴';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = '复制到公众号'; btn.classList.remove('copied'); }, 2200);
    } catch (err) {
      alert('复制失败，请手动选中正文复制。\\n错误: ' + err.message);
    }
  });
</script>
</body>
</html>
`;

writeFileSync(outPath, page, 'utf-8');
console.log(`[hailaobao-gzh-design] 已生成: ${outPath}`);
console.log(`[hailaobao-gzh-design] scheme: ${schemeId} (${scheme.name})`);
console.log(`[hailaobao-gzh-design] 请在浏览器打开产物，点顶栏「复制到公众号」`);
