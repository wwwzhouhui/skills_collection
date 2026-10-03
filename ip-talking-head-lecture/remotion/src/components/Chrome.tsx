import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { BrandSpec } from '../types';
import type { Palette } from '../theme';
import { FONT } from '../theme';
import { DotMark } from './Icons';
import { seg } from '../utils/anim';

/** 品牌层：角落水印 + 顶部进度条 */
export const Watermark: React.FC<{ brand: BrandSpec; p: Palette; total: number }> = ({ brand, p, total }) => {
  const f = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const pos = brand.watermark ?? 'bottom-left';
  const pad = Math.round(width * 0.055);

  const anchor: React.CSSProperties =
    pos === 'bottom-left'
      ? { left: pad, bottom: pad * 0.62 }
      : pos === 'bottom-right'
        ? { right: pad, bottom: pad * 0.62 }
        : pos === 'top-left'
          ? { left: pad, top: pad * 0.62 }
          : { right: pad, top: pad * 0.62 };

  return (
    <div
      style={{
        position: 'absolute',
        ...anchor,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        opacity: seg(f, Math.round(fps * 0.8), Math.round(fps * 1.6), 0, 0.78),
      }}
    >
      <DotMark size={22} color={p.ink} opacity={0.45} cols={7} rows={5} />
      <span
        style={{
          fontFamily: FONT.body,
          fontSize: 26,
          fontWeight: 600,
          letterSpacing: 1.2,
          color: p.muted,
          whiteSpace: 'nowrap',
        }}
      >
        {brand.name}
        {brand.slogan ? ` · ${brand.slogan}` : ''}
      </span>
    </div>
  );
};

/** 顶部细进度条 */
export const ProgressBar: React.FC<{ p: Palette; total: number; height: number }> = ({ p, total, height }) => {
  const f = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const prog = seg(f, 0, Math.max(1, Math.round(total * fps)), 0, 1);
  const h = height > width ? 5 : 5;
  return (
    <div style={{ position: 'absolute', left: 0, top: 0, width, height: h, background: `${p.ink}10` }}>
      <div
        style={{
          width: `${prog * 100}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${p.accent}aa, ${p.accent})`,
          boxShadow: `0 0 12px ${p.accent}66`,
        }}
      />
    </div>
  );
};
