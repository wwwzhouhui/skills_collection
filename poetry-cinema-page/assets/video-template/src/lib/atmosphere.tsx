import React from 'react';
import { useCurrentFrame } from 'remotion';
import { hashSeed, mulberry32 } from './motion';

const GRAIN_SVG = `<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>
<filter id='n' x='0' y='0' width='100%' height='100%'>
<feTurbulence type='fractalNoise' baseFrequency='0.86' numOctaves='3' stitchTiles='stitch'/>
<feColorMatrix type='saturate' values='0'/>
</filter>
<rect width='220' height='220' filter='url(%23n)'/>
</svg>`;

const GRAIN_URL = `url("data:image/svg+xml;utf8,${GRAIN_SVG.replace(/\n/g, '')}")`;

/**
 * 胶片颗粒 + 暗角。
 *
 * 颗粒用 feTurbulence 现场生成，不依赖任何位图素材；每帧把背景偏移
 * 抖一格（位移来自帧号派生的种子，所以仍然逐帧确定），静止噪点会像
 * 蒙了一层脏屏幕，动起来才像真正的胶片。
 */
export const Grain: React.FC<{ opacity?: number; amplitude?: number }> = ({
  opacity = 0.07,
  amplitude = 220,
}) => {
  const frame = useCurrentFrame();
  const rnd = mulberry32(hashSeed(frame) ^ 0x9e3779b9);
  const ox = Math.floor(rnd() * amplitude);
  const oy = Math.floor(rnd() * amplitude);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: GRAIN_URL,
        backgroundRepeat: 'repeat',
        backgroundPosition: `-${ox}px -${oy}px`,
        opacity,
        mixBlendMode: 'overlay',
        pointerEvents: 'none',
      }}
    />
  );
};

/**
 * 暗角 + 上下压暗。
 *
 * 上方那层很轻，只压住天空和水面这些容易过曝的地方；下方重一些，
 * 给字幕留出可读的底。颜色取自诗词页自己的松墨色，不引入外来色。
 */
export const Vignette: React.FC<{ ink: string }> = ({ ink }) => (
  <>
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `radial-gradient(ellipse 78% 78% at 50% 46%, rgba(0,0,0,0) 42%, ${ink}cc 100%)`,
        opacity: 0.82,
        pointerEvents: 'none',
      }}
    />
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `linear-gradient(to bottom, ${ink}59 0%, rgba(0,0,0,0) 26%, rgba(0,0,0,0) 55%, ${ink}d9 100%)`,
        pointerEvents: 'none',
      }}
    />
  </>
);
