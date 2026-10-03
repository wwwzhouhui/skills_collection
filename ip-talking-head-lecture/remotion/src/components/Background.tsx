import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { Palette } from '../theme';

/** 背景层：柔和渐变 + 缓慢漂浮的色块 + 极淡点阵，给浅色画面一点"呼吸" */
export const Background: React.FC<{ p: Palette; accent: string }> = ({ p, accent }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const t = f / 30;

  const blob = (seed: number, size: number, x: number, y: number, color: string, op: number) => {
    const dx = Math.sin(t * 0.13 + seed) * 26;
    const dy = Math.cos(t * 0.11 + seed * 1.7) * 20;
    return (
      <div
        key={seed}
        style={{
          position: 'absolute',
          left: x + dx,
          top: y + dy,
          width: size,
          height: size,
          borderRadius: '50%',
          background: color,
          filter: `blur(${size * 0.28}px)`,
          opacity: op,
        }}
      />
    );
  };

  return (
    <div style={{ position: 'absolute', inset: 0, background: p.bg, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, background: p.bgGrad }} />
      {blob(1.2, width * 0.36, -width * 0.08, -height * 0.12, p.accent, 0.1)}
      {blob(3.7, width * 0.3, width * 0.72, height * 0.5, p.accent, 0.07)}
      {blob(5.1, width * 0.24, width * 0.36, height * 0.72, accent, 0.05)}
      {/* 点阵 */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `radial-gradient(${p.ink}14 1.4px, transparent 1.4px)`,
          backgroundSize: '34px 34px',
          opacity: 0.5,
        }}
      />
    </div>
  );
};
