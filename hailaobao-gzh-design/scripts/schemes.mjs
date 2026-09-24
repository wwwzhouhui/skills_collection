// 七套 style scheme 的配色 + 组件样式。样式全部走 inline style，微信编辑器粘贴时会保留。
// 每套 scheme 都是一个函数集合：给定"元素类型"，返回一段 CSS-in-JS 字符串。

const S = (obj) =>
  Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${k.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())}:${v}`)
    .join(';');

const base = () => ({
  fontFamily: "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', sans-serif",
  fontSize: '16px',
  lineHeight: '1.85',
  wordBreak: 'break-word',
});

// --- helpers ---------------------------------------------------------------
const h1 = (accent, ink) => S({
  ...base(),
  fontSize: '22px',
  fontWeight: 800,
  color: ink,
  margin: '32px 0 16px',
  paddingBottom: '10px',
  borderBottom: `2px solid ${accent}`,
  letterSpacing: '0.02em',
});

const h2 = (accent, ink) => S({
  ...base(),
  fontSize: '19px',
  fontWeight: 800,
  color: ink,
  margin: '28px 0 14px',
  paddingLeft: '12px',
  borderLeft: `4px solid ${accent}`,
});

const h3 = (accent, ink) => S({
  ...base(),
  fontSize: '17px',
  fontWeight: 700,
  color: ink,
  margin: '22px 0 10px',
});

const h4 = (ink) => S({
  ...base(),
  fontSize: '15px',
  fontWeight: 700,
  color: ink,
  margin: '18px 0 8px',
});

const kickerBadge = (bg, fg) => S({
  display: 'inline-block',
  background: bg,
  color: fg,
  fontSize: '12px',
  fontWeight: 700,
  padding: '2px 10px',
  borderRadius: '4px',
  marginRight: '10px',
  letterSpacing: '0.1em',
  verticalAlign: 'middle',
});

const subtitle = (subtle) => S({
  display: 'block',
  fontSize: '13px',
  fontWeight: 400,
  color: subtle,
  marginTop: '6px',
  letterSpacing: '0.02em',
});

const p = (ink) => S({
  ...base(),
  color: ink,
  margin: '14px 0',
  textAlign: 'justify',
});

const strong = (color, styleId) => {
  if (styleId === 'plain-bold') return S({ fontWeight: 800 });
  if (styleId === 'underline')
    return S({ fontWeight: 700, borderBottom: `2px solid ${color}`, paddingBottom: '1px' });
  if (styleId === 'soft-fill')
    return S({ fontWeight: 700, background: color, padding: '0 4px', borderRadius: '2px' });
  if (styleId === 'light-band')
    return S({ fontWeight: 700, backgroundImage: `linear-gradient(transparent 55%, ${color} 55%, ${color} 92%, transparent 92%)`, padding: '0 2px' });
  // gradient
  return S({ fontWeight: 700, backgroundImage: `linear-gradient(120deg, ${color} 0%, ${color}00 100%)`, padding: '0 4px', borderRadius: '2px' });
};

const em = (ink) => S({ fontStyle: 'italic', color: ink });

const link = (accent) => S({ color: accent, textDecoration: 'none', borderBottom: `1px solid ${accent}` });

const inlineCode = (bg, ink) => S({
  fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
  fontSize: '13px',
  background: bg,
  color: ink,
  padding: '1px 6px',
  borderRadius: '4px',
});

const blockquote = (bg, accent, ink) => S({
  background: bg,
  borderLeft: `4px solid ${accent}`,
  margin: '20px 0',
  padding: '14px 18px',
  color: ink,
  fontSize: '15px',
  lineHeight: '1.75',
  borderRadius: '4px',
});

const ul = () => S({ margin: '14px 0', paddingLeft: '24px' });
const li = (ink) => S({ ...base(), color: ink, margin: '6px 0' });

const hr = (accent) => S({
  border: 'none',
  height: '1px',
  background: `linear-gradient(90deg, transparent 0%, ${accent}66 50%, transparent 100%)`,
  margin: '32px 0',
});

const img = (radius) => S({ display: 'block', width: '100%', margin: '18px 0', borderRadius: radius });

const codeBlock = (bg, ink, accent, terminal) => {
  if (terminal) {
    return S({
      background: '#111',
      color: '#F4F4F4',
      padding: '18px 20px',
      borderRadius: '8px',
      margin: '18px 0',
      fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
      fontSize: '13px',
      lineHeight: '1.6',
      overflowX: 'auto',
      whiteSpace: 'pre',
    });
  }
  return S({
    background: bg,
    color: ink,
    borderLeft: `3px solid ${accent}`,
    padding: '16px 20px',
    borderRadius: '4px',
    margin: '18px 0',
    fontFamily: "'JetBrains Mono', 'Fira Code', Menlo, Consolas, monospace",
    fontSize: '13px',
    lineHeight: '1.6',
    overflowX: 'auto',
    whiteSpace: 'pre',
  });
};

const summaryCard = (bg, accent, ink) => ({
  root: S({
    background: bg,
    border: `1px solid ${accent}55`,
    borderTop: `3px solid ${accent}`,
    borderRadius: '8px',
    padding: '18px 22px',
    margin: '26px 0',
  }),
  title: S({
    ...base(),
    color: accent,
    fontSize: '15px',
    fontWeight: 800,
    letterSpacing: '0.06em',
    marginBottom: '10px',
  }),
  body: S({ ...base(), color: ink, fontSize: '15px' }),
});

const infoCard = (bg, accent, ink) => ({
  root: S({
    background: bg,
    borderLeft: `4px solid ${accent}`,
    borderRadius: '4px',
    padding: '14px 18px',
    margin: '20px 0',
  }),
  title: S({
    ...base(),
    color: accent,
    fontSize: '13px',
    fontWeight: 800,
    letterSpacing: '0.1em',
    marginBottom: '6px',
    textTransform: 'uppercase',
  }),
  body: S({ ...base(), color: ink, fontSize: '14px', lineHeight: '1.75' }),
});

// --- 七套 scheme。前六套配色和组件几何不变；forest-demo 另加徽章标题条和提示词窗口。
export const SCHEMES = {
  'jade-business': {
    name: '玉石商务',
    palette: { paper: '#FFFFFF', ink: '#1F2937', accent: '#059669', soft: '#CBE6D8', subtle: '#6B7280', codeBg: '#F5F7F5' },
    emphasisStyleId: 'gradient',
    emphasisColor: '#CBE6D8',
    codeTerminal: true,
    imageRadius: '8px',
  },
  'warm-editorial': {
    name: '暖色编辑部',
    palette: { paper: '#FBF6EC', ink: '#3B2A1F', accent: '#B45309', soft: '#FDE68A', subtle: '#8C7355', codeBg: '#F3EBDA' },
    emphasisStyleId: 'soft-fill',
    emphasisColor: '#FDE68A',
    codeTerminal: false,
    imageRadius: '10px',
  },
  'mono-tech': {
    name: '极客单色',
    palette: { paper: '#FFFFFF', ink: '#111827', accent: '#EF4444', soft: '#F3F4F6', subtle: '#6B7280', codeBg: '#F9FAFB' },
    emphasisStyleId: 'plain-bold',
    emphasisColor: '#EF4444',
    codeTerminal: true,
    imageRadius: '0',
  },
  'champagne-brand': {
    name: '香槟品牌',
    palette: { paper: '#FBF7EF', ink: '#3F2E17', accent: '#C79A50', soft: '#F2DFB0', subtle: '#8F7A55', codeBg: '#F1E8D2' },
    emphasisStyleId: 'gradient',
    emphasisColor: '#F2DFB0',
    codeTerminal: false,
    imageRadius: '12px',
  },
  'mist-notebook': {
    name: '雾霾笔记',
    palette: { paper: '#F5F8FC', ink: '#25324B', accent: '#3B6FB3', soft: '#C9D9EA', subtle: '#5B6B85', codeBg: '#E9EEF6' },
    emphasisStyleId: 'light-band',
    emphasisColor: '#C9D9EA',
    codeTerminal: false,
    imageRadius: '6px',
  },
  'midnight-report': {
    name: '午夜研究报告',
    palette: { paper: '#0F172A', ink: '#E5E7EB', accent: '#7AB0F0', soft: '#1E293B', subtle: '#94A3B8', codeBg: '#1E293B' },
    emphasisStyleId: 'underline',
    emphasisColor: '#7AB0F0',
    codeTerminal: true,
    imageRadius: '4px',
  },
  'forest-demo': {
    name: '森绿演示',
    palette: { paper: '#FFFFFF', ink: '#1F2329', accent: '#255E4A', soft: '#F1F4F3', subtle: '#5C6B66', codeBg: '#242A33' },
    emphasisStyleId: 'plain-bold',
    emphasisColor: '#255E4A',
    codeTerminal: true,
    imageRadius: '9px',
    badgeBar: true,
    promptWindow: true,
  },
};

export const getSchemeStyles = (schemeId) => {
  const s = SCHEMES[schemeId];
  if (!s) throw new Error(`未知 scheme: ${schemeId}。可用值：${Object.keys(SCHEMES).join(', ')}`);
  const { paper, ink, accent, soft, subtle, codeBg } = s.palette;
  const styles = {
    article: S({ ...base(), background: paper, color: ink, padding: '24px 20px', maxWidth: '760px', margin: '0 auto' }),
    h1: h1(accent, ink),
    h2: h2(accent, ink),
    h3: h3(accent, ink),
    h4: h4(ink),
    kicker: kickerBadge(accent, paper),
    subtitle: subtitle(subtle),
    p: p(ink),
    strong: strong(s.emphasisColor, s.emphasisStyleId),
    em: em(subtle),
    link: link(accent),
    inlineCode: inlineCode(codeBg, accent),
    blockquote: blockquote(soft, accent, ink),
    ul: ul(),
    ol: ul(),
    li: li(ink),
    hr: hr(accent),
    img: img(s.imageRadius),
    code: codeBlock(codeBg, ink, accent, s.codeTerminal),
    summary: summaryCard(soft, accent, ink),
    info: infoCard(soft, accent, ink),
  };
  // 保持前六套返回结构不变，仅给明确启用的 scheme 增补演示样式
  if (s.badgeBar) {
    styles.badgeBar = {
      wrap: S({ margin: '34px 0 18px', padding: '0 0 0 15px' }),
      badge: S({
        display: 'inline-block',
        width: '51px',
        height: '42px',
        margin: '0 0 -38px -4px',
        borderRadius: '3px 14px 3px 14px',
        background: '#255E4A',
        color: '#FFFFFF',
        textAlign: 'center',
        lineHeight: '42px',
        fontSize: '18px',
        fontWeight: 'bold',
        boxSizing: 'border-box',
      }),
      title: S({
        display: 'block',
        minHeight: '42px',
        padding: '8px 14px 7px 43px',
        background: '#F1F4F3',
        color: '#255E4A',
        fontSize: '18px',
        lineHeight: '1.5',
        fontWeight: 'bold',
        boxSizing: 'border-box',
      }),
      rule: S({
        display: 'block',
        width: '88px',
        height: '3px',
        margin: '-1px 8px 0 auto',
        borderRadius: '3px',
        background: '#255E4A',
        opacity: '0.32',
      }),
    };
  }
  if (s.promptWindow) {
    styles.promptWindow = {
      root: S({
        margin: '18px 0 22px',
        borderRadius: '8px',
        overflow: 'hidden',
        background: '#242A33',
        border: '1px solid #2F3742',
      }),
      bar: S({
        height: '34px',
        padding: '0 16px',
        background: '#242A33',
        lineHeight: '34px',
        fontSize: '0',
      }),
      body: S({
        margin: '0',
        padding: '14px 18px 18px',
        background: '#242A33',
        color: '#EEF2F7',
        fontFamily: 'Menlo, Monaco, Consolas, monospace',
        fontSize: '13px',
        lineHeight: '1.9',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }),
      dots: ['#FF5F57', '#FFBD2E', '#28C940'],
    };
  }
  return { scheme: s, styles };
};
