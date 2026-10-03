import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { Palette } from '../theme';
import { FONT } from '../theme';

/**
 * 极简线描图标 + 点阵标记。
 * DotMark 是照 IP 的"半调点阵拱形"做的 —— 每期画面上留一个，等于是自家 IP 的签名。
 */

const S = (props: { children: React.ReactNode; size?: number; stroke?: string; w?: number }) => (
  <svg
    width={props.size ?? 56}
    height={props.size ?? 56}
    viewBox="0 0 48 48"
    fill="none"
    stroke={props.stroke ?? 'currentColor'}
    strokeWidth={props.w ?? 2.6}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {props.children}
  </svg>
);

export const IconBulb = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <path d="M24 6a12 12 0 0 0-7 21.8V34h14v-6.2A12 12 0 0 0 24 6Z" />
    <path d="M19 39h10M20 43h8" />
  </S>
);

export const IconChart = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <path d="M7 41h34M12 41V28M22 41V16M32 41V23M41 41V11" />
  </S>
);

export const IconChip = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <rect x="13" y="13" width="22" height="22" rx="4" />
    <path d="M20 20h8v8h-8z" />
    <path d="M19 6v7M29 6v7M19 35v7M29 35v7M6 19h7M6 29h7M35 19h7M35 29h7" />
  </S>
);

export const IconLayers = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <path d="M24 6 6 15l18 9 18-9-18-9Z" />
    <path d="M6 24l18 9 18-9M6 33l18 9 18-9" />
  </S>
);

export const IconChat = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <path d="M40 26a13 13 0 0 1-13 13H16L7 44l2.4-7.6A13 13 0 0 1 18 9h9a13 13 0 0 1 13 13v4Z" />
    <path d="M17 22h14M17 29h9" />
  </S>
);

export const IconRocket = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <path d="M24 5c7 5 10 12 10 20l-5 5H19l-5-5C14 17 17 10 24 5Z" />
    <circle cx="24" cy="20" r="3.4" />
    <path d="M19 30l-5 6 7-1M29 30l5 6-7-1M24 36v7" />
  </S>
);

export const IconTarget = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <circle cx="24" cy="24" r="17" />
    <circle cx="24" cy="24" r="9" />
    <circle cx="24" cy="24" r="2" />
  </S>
);

export const IconBook = ({ size, stroke }: { size?: number; stroke?: string }) => (
  <S size={size} stroke={stroke}>
    <path d="M6 10h13a5 5 0 0 1 5 5v25a4 4 0 0 0-4-4H6V10Z" />
    <path d="M42 10H29a5 5 0 0 0-5 5v25a4 4 0 0 1 4-4h14V10Z" />
  </S>
);

export const ICONS = {
  bulb: IconBulb,
  chart: IconChart,
  chip: IconChip,
  layers: IconLayers,
  chat: IconChat,
  rocket: IconRocket,
  target: IconTarget,
  book: IconBook,
};

export type IconName = keyof typeof ICONS;

/** 半调点阵拱形 —— IP 的图形签名，点在网格上按掩膜点亮 */
export const DotMark: React.FC<{ size?: number; color: string; cols?: number; rows?: number; opacity?: number }> = ({
  size = 96,
  color,
  cols = 9,
  rows = 7,
  opacity = 0.5,
}) => {
  const fs = 7;
  const gap = size / cols;
  const r = gap * 0.19;
  const dots: React.ReactNode[] = [];
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const nx = (x + 0.5) / cols - 0.5;
      const ny = (y + 0.5) / rows;
      // 拱形掩膜：下半实心 + 上半弧形收窄，模仿 IP 的印章轮廓
      const arc = 0.52 - 0.34 * Math.sqrt(Math.max(0, 0.25 - nx * nx)) * 2;
      const inside = ny > arc && Math.abs(nx) < 0.5 - Math.abs(ny - 0.55) * 0.35;
      if (!inside) continue;
      dots.push(
        <circle key={`${x}-${y}`} cx={gap * (x + 0.5)} cy={gap * (y + 0.5)} r={r} fill={color} />,
      );
    }
  }
  return (
    <svg width={size} height={size} viewBox={`0 0 ${gap * cols} ${gap * rows}`} style={{ opacity }}>
      {dots}
    </svg>
  );
};

/** 数字徽章（步骤序号） */
export const StepNumber: React.FC<{ n: number; p: Palette; size?: number }> = ({ n, p, size = 62 }) => {
  const f = useCurrentFrame();
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: size * 0.32,
        background: p.accent,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: FONT.display,
        fontSize: size * 0.52,
        fontWeight: 800,
        boxShadow: `0 8px 20px ${p.accent}55`,
        transform: `rotate(${Math.sin(f / 26) * 1.2}deg)`,
      }}
    >
      {n}
    </div>
  );
};
