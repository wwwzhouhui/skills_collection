import React from 'react';
import { Img, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Scene } from '../types';
import type { Layout } from '../components/SceneShell';
import type { Palette } from '../theme';
import { FONT } from '../theme';
import { riseIn, popIn, seg, countUp, breathe } from '../utils/anim';
import { ICONS, DotMark, StepNumber, type IconName } from '../components/Icons';

/**
 * 动画课件版式模板。
 * 每个模板只画"内容槽"里的东西，页眉（kicker/标题/副标题）和背景由外壳负责。
 * 横屏（16:9）走左右分栏/多列；竖屏（9:16）一律改纵向堆叠 —— 手机上横排三列会挤成一条。
 * 新增版式：写一个组件 → 在 SCENES 里登记 → references/script-format.md 补 data 结构。
 */

type BodyProps = { scene: Scene; p: Palette; layout: Layout; width: number; height: number };

const icon = (name: IconName | undefined, fallback: IconName): IconName =>
  name && ICONS[name] ? name : fallback;

const cardBase = (p: Palette, radius: number): React.CSSProperties => ({
  background: p.panel,
  border: `2px solid ${p.panelBorder}`,
  borderRadius: radius,
  boxShadow: p.shadow,
});

const AccentBar: React.FC<{ p: Palette }> = ({ p }) => (
  <div style={{ width: 54, height: 6, borderRadius: 3, background: p.accent, marginBottom: 14 }} />
);

// ───────────────────────────── cover ─────────────────────────────
const Cover: React.FC<BodyProps> = ({ scene, p, layout, width, height }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const col = layout.portrait;
  // 封面占上半屏，避开右下角数字人；竖屏上头像更大，所以压得更高一点
  const boxH = col ? height * 0.5 : height * 0.68;
  const titleSize = col ? 86 : 132;

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: 0,
        height: boxH,
        padding: `0 ${layout.pad}px`,
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {d.eyebrow ? (
        <div style={{ marginBottom: col ? 24 : 30, ...popIn(f, 2, Math.round(fps * 0.4)) }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 12,
              padding: col ? '10px 24px' : '12px 30px',
              borderRadius: 999,
              border: `2.5px solid ${p.accent}`,
              background: 'rgba(255,255,255,0.72)',
              color: p.accent,
              fontFamily: FONT.display,
              fontSize: col ? 26 : 30,
              fontWeight: 700,
              letterSpacing: 1.4,
              whiteSpace: 'nowrap',
            }}
          >
            <DotMark size={24} color={p.accent} opacity={0.9} cols={7} rows={5} />
            {d.eyebrow}
          </div>
        </div>
      ) : null}

      <div
        style={{
          textAlign: 'center',
          fontFamily: FONT.display,
          fontSize: titleSize,
          fontWeight: 800,
          lineHeight: 1.12,
          letterSpacing: 1,
          color: p.ink,
          ...riseIn(f, 6, Math.round(fps * 0.55), 34),
        }}
      >
        {scene.heading}
      </div>

      <div
        style={{
          marginTop: 24,
          width: seg(f, Math.round(fps * 0.55), Math.round(fps * 1.1), 0, col ? 260 : 340),
          height: 10,
          borderRadius: 5,
          background: `linear-gradient(90deg, ${p.accent}, ${p.accent}55)`,
        }}
      />

      {scene.sub ? (
        <div
          style={{
            marginTop: 30,
            fontFamily: FONT.body,
            fontSize: col ? 36 : 44,
            fontWeight: 500,
            color: p.muted,
            letterSpacing: 1,
            textAlign: 'center',
            ...riseIn(f, 18, Math.round(fps * 0.5), 20),
          }}
        >
          {scene.sub}
        </div>
      ) : null}

      {d.tags?.length ? (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: 14,
            marginTop: col ? 38 : 52,
            maxWidth: width - layout.pad * 2,
          }}
        >
          {d.tags.map((t: string, i: number) => (
            <div
              key={i}
              style={{
                padding: col ? '11px 24px' : '14px 30px',
                borderRadius: 16,
                background: i === 0 ? p.accent : 'rgba(255,255,255,0.8)',
                color: i === 0 ? '#fff' : p.inkSoft,
                border: `2px solid ${i === 0 ? p.accent : p.panelBorder}`,
                fontFamily: FONT.body,
                fontSize: col ? 26 : 30,
                fontWeight: 700,
                ...popIn(f, 26 + i * 5, Math.round(fps * 0.45)),
              }}
            >
              {t}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

// ───────────────────────────── idea ─────────────────────────────
const Idea: React.FC<BodyProps> = ({ scene, p, layout }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const points: { title: string; text?: string }[] = d.points || [];
  const Ico = ICONS[icon(d.icon, 'bulb')];
  const col = layout.portrait;
  const badge = col ? 208 : 300;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: col ? 'column' : 'row',
        gap: col ? 30 : 56,
        height: '100%',
        alignItems: 'center',
        justifyContent: col ? 'flex-start' : 'center',
      }}
    >
      {/* 核心概念圆章 */}
      <div
        style={{
          width: badge,
          height: badge,
          flex: '0 0 auto',
          borderRadius: '50%',
          background: `radial-gradient(120% 120% at 30% 20%, #ffffff 0%, ${p.accentSoft} 100%)`,
          border: `3px solid ${p.accent}33`,
          boxShadow: p.shadow,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: col ? 8 : 14,
          transform: `translateY(${breathe(f, 6, 96)}px) scale(${0.94 + seg(f, 0, Math.round(fps * 0.6)) * 0.06})`,
        }}
      >
        <Ico size={col ? 66 : 92} stroke={p.accent} />
        <div
          style={{
            fontFamily: FONT.display,
            fontSize: col ? 34 : 40,
            fontWeight: 800,
            color: p.ink,
            textAlign: 'center',
            padding: '0 20px',
            lineHeight: 1.2,
          }}
        >
          {d.center || ''}
        </div>
      </div>

      {/* 要点卡 */}
      <div
        style={{
          position: 'relative',
          flex: col ? '0 0 auto' : 1,
          width: col ? '100%' : undefined,
          display: 'flex',
          flexDirection: 'column',
          gap: col ? 16 : 20,
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: 31,
            top: 40,
            bottom: 40,
            width: 3,
            background: `linear-gradient(180deg, ${p.accent}, ${p.accent}22)`,
            opacity: 0.5,
          }}
        />
        {points.map((pt, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 20,
              ...riseIn(f, 14 + i * 9, Math.round(fps * 0.5), 26),
            }}
          >
            <div
              style={{
                width: col ? 56 : 64,
                height: col ? 56 : 64,
                flex: '0 0 auto',
                borderRadius: 18,
                background: p.accent,
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: FONT.display,
                fontSize: col ? 26 : 30,
                fontWeight: 800,
                boxShadow: `0 8px 20px ${p.accent}44`,
                zIndex: 1,
              }}
            >
              {i + 1}
            </div>
            <div style={{ ...cardBase(p, layout.cardRadius), padding: col ? '16px 24px' : '20px 30px', flex: 1 }}>
              <div style={{ fontFamily: FONT.display, fontSize: col ? 34 : 40, fontWeight: 700, color: p.ink }}>
                {pt.title}
              </div>
              {pt.text ? (
                <div
                  style={{
                    marginTop: 4,
                    fontFamily: FONT.body,
                    fontSize: col ? 25 : 28,
                    color: p.muted,
                    lineHeight: 1.35,
                  }}
                >
                  {pt.text}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ───────────────────────────── steps ─────────────────────────────
const Steps: React.FC<BodyProps> = ({ scene, p, layout }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const items: { title: string; text?: string; icon?: IconName }[] = d.items || [];
  const col = layout.portrait;
  const n = Math.max(1, items.length);
  const colW = (layout.stage.width - layout.gap * (n - 1)) / n;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: col ? 'column' : 'row',
        gap: col ? 18 : layout.gap,
        height: '100%',
        alignItems: 'stretch',
        justifyContent: col ? 'flex-start' : undefined,
      }}
    >
      {items.map((it, i) => {
        const Ico = ICONS[icon(it.icon, 'target')];
        return (
          <div
            key={i}
            style={{
              width: col ? '100%' : colW,
              ...cardBase(p, layout.cardRadius),
              padding: col ? '20px 26px' : 34,
              display: 'flex',
              flexDirection: col ? 'row' : 'column',
              alignItems: col ? 'center' : undefined,
              gap: col ? 22 : 18,
              ...riseIn(f, 16 + i * 10, Math.round(fps * 0.55), col ? 26 : 40),
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: col ? 'flex-start' : 'space-between',
                gap: 14,
                flex: col ? '0 0 auto' : undefined,
              }}
            >
              <StepNumber n={i + 1} p={p} size={col ? 50 : 58} />
              {!col ? (
                <div style={{ color: p.accent, opacity: 0.75 }}>
                  <Ico size={54} stroke={p.accent} />
                </div>
              ) : null}
            </div>
            <div style={{ flex: col ? 1 : undefined, minWidth: 0 }}>
              {!col ? <AccentBar p={p} /> : null}
              <div
                style={{
                  fontFamily: FONT.display,
                  fontSize: col ? 34 : 44,
                  fontWeight: 800,
                  color: p.ink,
                  lineHeight: 1.18,
                }}
              >
                {it.title}
              </div>
              {it.text ? (
                <div
                  style={{
                    marginTop: col ? 4 : 10,
                    fontFamily: FONT.body,
                    fontSize: col ? 25 : 29,
                    color: p.muted,
                    lineHeight: 1.42,
                  }}
                >
                  {it.text}
                </div>
              ) : null}
              {/* 卡片底部：把空出来的地方用一个极淡的大图标收住，比留一片白好看 */}
              {!col ? (
                <>
                  <div style={{ flex: 1 }} />
                  <div
                    style={{
                      alignSelf: 'flex-end',
                      color: p.accent,
                      opacity: 0.1,
                      marginBottom: -18,
                      marginRight: -12,
                    }}
                  >
                    <Ico size={150} stroke={p.accent} />
                  </div>
                </>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// ───────────────────────────── compare ─────────────────────────────
const Compare: React.FC<BodyProps> = ({ scene, p, layout }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const left = d.left || { title: 'A', items: [] };
  const right = d.right || { title: 'B', items: [] };
  const col = layout.portrait;

  const Col: React.FC<{ side: any; i: number; tone: 'muted' | 'accent' }> = ({ side, i, tone }) => {
    const accent = tone === 'accent';
    return (
      <div
        style={{
          // ⚠️竖屏是 flex-direction: column —— 这里若还写 flex: 1，两张卡会被**纵向拉伸填满整个内容槽**，
          //    卡内只剩三行字，底下留出一大片空白。竖屏必须让它按内容高度收缩。
          flex: col ? '0 0 auto' : 1,
          ...cardBase(p, layout.cardRadius),
          padding: col ? 24 : 34,
          display: 'flex',
          flexDirection: 'column',
          gap: col ? 10 : 16,
          borderColor: accent ? `${p.accent}66` : p.panelBorder,
          background: accent ? p.accentSoft : p.panel,
          ...riseIn(f, 18 + i * 10, Math.round(fps * 0.5), col ? 24 : 34),
        }}
      >
        <div
          style={{
            fontFamily: FONT.display,
            fontSize: col ? 36 : 42,
            fontWeight: 800,
            color: accent ? p.accent : p.inkSoft,
          }}
        >
          {side.title}
        </div>
        <div style={{ height: 3, background: accent ? `${p.accent}44` : p.panelBorder, borderRadius: 2 }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: col ? 10 : 14, marginTop: 2 }}>
          {(side.items || []).map((t: string, k: number) => (
            <div
              key={k}
              style={{
                display: 'flex',
                gap: 12,
                alignItems: 'flex-start',
                fontFamily: FONT.body,
                fontSize: col ? 26 : 30,
                color: p.inkSoft,
                lineHeight: 1.38,
                ...riseIn(f, 30 + i * 10 + k * 6, Math.round(fps * 0.4), 16),
              }}
            >
              <span
                style={{
                  marginTop: col ? 11 : 13,
                  width: 12,
                  height: 12,
                  borderRadius: 4,
                  flex: '0 0 auto',
                  background: accent ? p.accent : p.muted,
                }}
              />
              <span>{t}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: col ? 'column' : 'row',
        gap: col ? 16 : 26,
        height: '100%',
        alignItems: col ? 'stretch' : 'stretch',
        justifyContent: col ? 'flex-start' : undefined,
      }}
    >
      <Col side={left} i={0} tone="muted" />
      <div
        style={{
          width: col ? '100%' : 92,
          height: col ? 52 : undefined,
          flex: '0 0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          ...popIn(f, 34, Math.round(fps * 0.5)),
        }}
      >
        <div
          style={{
            width: col ? 62 : 76,
            height: col ? 62 : 76,
            borderRadius: '50%',
            background: p.ink,
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: FONT.display,
            fontSize: col ? 26 : 30,
            fontWeight: 800,
            boxShadow: p.shadow,
          }}
        >
          VS
        </div>
      </div>
      <Col side={right} i={1} tone="accent" />
    </div>
  );
};

// ───────────────────────────── numbers ─────────────────────────────
const Numbers: React.FC<BodyProps> = ({ scene, p, layout }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const items: { value: number; unit?: string; label: string; decimals?: number; prefix?: string }[] =
    d.items || [];
  const col = layout.portrait;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: col ? 'column' : 'column',
        height: '100%',
        justifyContent: 'center',
        gap: col ? 30 : 44,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: col ? 'column' : 'row',
          gap: col ? 26 : layout.gap,
          alignItems: col ? 'stretch' : 'stretch',
        }}
      >
        {items.map((it, i) => {
          const start = 12 + i * 8;
          const v = countUp(f, start, Math.round(fps * 1.15), it.value, it.decimals ?? 0);
          return (
            <div key={i} style={{ flex: 1, ...riseIn(f, start, Math.round(fps * 0.5), 30) }}>
              <div
                style={{
                  fontFamily: FONT.display,
                  fontSize: col ? 96 : 118,
                  fontWeight: 800,
                  lineHeight: 1,
                  color: i === 0 ? p.accent : p.ink,
                  letterSpacing: -2,
                }}
              >
                {it.prefix || ''}
                {v}
                <span style={{ fontSize: col ? 44 : 54, marginLeft: 8, fontWeight: 700, color: p.muted }}>
                  {it.unit || ''}
                </span>
              </div>
              <div
                style={{ marginTop: 12, height: 4, width: 90, borderRadius: 2, background: p.accent, opacity: 0.6 }}
              />
              <div
                style={{
                  marginTop: 12,
                  fontFamily: FONT.body,
                  fontSize: col ? 28 : 32,
                  fontWeight: 600,
                  color: p.inkSoft,
                }}
              >
                {it.label}
              </div>
            </div>
          );
        })}
      </div>
      {d.note ? (
        <div
          style={{
            fontFamily: FONT.body,
            fontSize: col ? 26 : 30,
            color: p.muted,
            lineHeight: 1.4,
            ...riseIn(f, 40, Math.round(fps * 0.5), 18),
          }}
        >
          {d.note}
        </div>
      ) : null}
    </div>
  );
};

// ───────────────────────────── recap ─────────────────────────────
const Recap: React.FC<BodyProps> = ({ scene, p, layout }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const items: { title: string; text?: string }[] = d.items || [];
  const col = layout.portrait;
  const n = Math.max(1, items.length);
  const colW = (layout.stage.width - layout.gap * (n - 1)) / n;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: col ? 22 : 30 }}>
      <div
        style={{
          display: 'flex',
          flexDirection: col ? 'column' : 'row',
          gap: col ? 16 : layout.gap,
          flex: col ? '0 0 auto' : 1,
          alignItems: 'stretch',
        }}
      >
        {items.map((it, i) => (
          <div
            key={i}
            style={{
              width: col ? '100%' : colW,
              ...cardBase(p, layout.cardRadius),
              padding: col ? '18px 24px' : 30,
              display: 'flex',
              flexDirection: col ? 'row' : 'column',
              alignItems: col ? 'center' : undefined,
              gap: col ? 18 : 14,
              ...riseIn(f, 16 + i * 9, Math.round(fps * 0.5), 34),
            }}
          >
            <div
              style={{
                width: col ? 44 : 52,
                height: col ? 44 : 52,
                flex: '0 0 auto',
                borderRadius: 14,
                background: p.accentSoft,
                color: p.accent,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontFamily: FONT.display,
                fontSize: col ? 24 : 28,
                fontWeight: 800,
                border: `2px solid ${p.accent}55`,
              }}
            >
              ✓
            </div>
            <div style={{ flex: col ? 1 : undefined, minWidth: 0 }}>
              <div
                style={{
                  fontFamily: FONT.display,
                  fontSize: col ? 34 : 40,
                  fontWeight: 800,
                  color: p.ink,
                  lineHeight: 1.2,
                }}
              >
                {it.title}
              </div>
              {it.text ? (
                <div
                  style={{
                    marginTop: 4,
                    fontFamily: FONT.body,
                    fontSize: col ? 25 : 28,
                    color: p.muted,
                    lineHeight: 1.42,
                  }}
                >
                  {it.text}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
      {d.cta ? (
        <div
          style={{
            fontFamily: FONT.display,
            fontSize: col ? 38 : 42,
            fontWeight: 800,
            color: p.accent,
            textAlign: 'center',
            letterSpacing: 1.4,
            ...popIn(f, 46, Math.round(fps * 0.55)),
          }}
        >
          {d.cta}
        </div>
      ) : null}
    </div>
  );
};

// ───────────────────────────── outro（片尾品牌卡） ─────────────────────────────
// 无配音收尾卡：博主标识图（brand.logo，缺省手写大名）+ 品牌色划线 + slogan + 黄色便签 CTA。
// 版式参考 whiteboard-video-factory 的 brandEndCard；数据由 lib/build.mjs 从 config.brand 写进 data。
const Outro: React.FC<BodyProps> = ({ scene, p, layout, height }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const d = scene.data || {};
  const col = layout.portrait;
  const name = String(d.name || scene.heading || '').trim();
  // 整体压在画面上 2/3：右下角站着数字人，左下角有水印
  const boxH = col ? height * 0.62 : height * 0.72;

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: 0,
        height: boxH,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: `0 ${layout.pad}px`,
        boxSizing: 'border-box',
      }}
    >
      {d.logo ? (
        <div style={{ ...popIn(f, 2, Math.round(fps * 0.5)), marginBottom: col ? 30 : 36 }}>
          <Img src={staticFile(d.logo)} style={{ height: col ? 240 : 280, width: 'auto', objectFit: 'contain' }} />
        </div>
      ) : name ? (
        <div style={{ position: 'relative' }}>
          <span
            style={{
              position: 'absolute',
              left: -Math.round((col ? 96 : 132) * 0.9),
              top: -10,
              color: p.accent,
              fontSize: col ? 44 : 54,
              ...popIn(f, 18, Math.round(fps * 0.4)),
            }}
          >
            ✦
          </span>
          <div
            style={{
              fontFamily: FONT.display,
              fontSize: col ? 96 : 132,
              fontWeight: 800,
              lineHeight: 1.12,
              letterSpacing: 2,
              color: p.ink,
              ...riseIn(f, 4, Math.round(fps * 0.55), 30),
            }}
          >
            {name}
          </div>
        </div>
      ) : null}

      {/* 品牌色划线：从左往右"画"出来 */}
      <div
        style={{
          marginTop: 26,
          width: seg(f, Math.round(fps * 0.5), Math.round(fps * 1.05), 0, col ? 300 : 420),
          height: 10,
          borderRadius: 5,
          background: `linear-gradient(90deg, ${p.accent}, ${p.accent}55)`,
        }}
      />

      {d.slogan ? (
        <div
          style={{
            marginTop: 28,
            fontFamily: FONT.body,
            fontSize: col ? 34 : 40,
            fontWeight: 500,
            color: p.muted,
            letterSpacing: 2,
            textAlign: 'center',
            ...riseIn(f, 20, Math.round(fps * 0.5), 20),
          }}
        >
          {d.slogan}
        </div>
      ) : null}

      {d.cta ? (
        <div
          style={{
            marginTop: col ? 56 : 64,
            padding: col ? '18px 44px' : '22px 54px',
            borderRadius: 14,
            background: '#ffe9a3',
            border: `2.5px solid ${p.ink}`,
            color: p.ink,
            fontFamily: FONT.body,
            fontSize: col ? 30 : 34,
            fontWeight: 700,
            letterSpacing: 2,
            transform: 'rotate(-2deg)',
            boxShadow: p.shadow,
            ...popIn(f, 34, Math.round(fps * 0.5)),
          }}
        >
          {d.cta}
        </div>
      ) : null}
    </div>
  );
};

// ───────────────────────────── 登记表 ─────────────────────────────
export const SCENES: Record<string, { comp: React.FC<any>; bare?: boolean; desc: string }> = {
  cover: { comp: Cover, bare: true, desc: '封面/开场：大标题 + 下划线 + 标签（data.eyebrow / data.tags）' },
  idea: { comp: Idea, desc: '一个核心概念 + 2~4 个要点卡（data.center / data.icon / data.points）' },
  steps: { comp: Steps, desc: '2~4 步流程卡，带序号（data.items[].title/text/icon）' },
  compare: { comp: Compare, desc: '左右两栏对比 + VS（data.left / data.right，各含 title + items[]）' },
  numbers: { comp: Numbers, desc: '1~3 个数据滚动（data.items[].value/unit/label/prefix + data.note）' },
  recap: { comp: Recap, desc: '2~3 张总结卡 + 收尾 CTA（data.items[] + data.cta）' },
  outro: { comp: Outro, bare: true, desc: '片尾品牌卡：标识图/手写名 + 划线 + slogan + 便签 CTA（无配音，时长用 duration；一般由 config.brand.endCard 自动追加）' },
};

export const SCENE_KINDS = Object.keys(SCENES);
