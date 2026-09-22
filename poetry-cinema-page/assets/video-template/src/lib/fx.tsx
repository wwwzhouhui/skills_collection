import React from 'react';
import { useCurrentFrame } from 'remotion';
import { clamp01, hashSeed, lerp, mulberry32, softRamp } from './motion';

/**
 * 画面内部动态层。
 *
 * 这是让"静图口播"不再是一张幻灯片的第二把钥匙。运镜只能让整幅画平移缩放，
 * 观众的眼睛很快会把它归成"背景在动，内容没动"；真正把静图点活的是**画面里
 * 自己会动的东西**：浮起的尘埃、横移的水汽、掠过一次的光。
 *
 * 全部走 CSS 渐变与确定性 PRNG，不用 SVG 滤镜——feTurbulence + feDisplacementMap
 * 那种真位移每帧要几百毫秒，两千多帧的成片会被拖成半小时。这里零滤镜成本，
 * 单帧开销可以忽略。
 */

export interface ShotFx {
  /** 浮尘/飞雪强度 0–1 */
  motes?: number;
  /** 雾气流强度 0–1 */
  haze?: number;
  /** 光扫强度 0–1 */
  sweep?: number;
  /** 明暗呼吸强度 0–1 */
  breathe?: number;
  /** 颗粒颜色，缺省取调色板的金 */
  moteColor?: string;
  moteBlend?: 'screen' | 'normal' | 'plus-lighter';
}

export type FxSettings = Required<Omit<ShotFx, 'moteColor'>> & { moteColor?: string };

/** 六位十六进制转 rgba；非法输入原样返回，不会把画面打黑。 */
export const withAlpha = (color: string, a: number): string => {
  const m = /^#?([0-9a-f]{6})$/i.exec(color.trim());
  if (!m) return color;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

/**
 * 五个气层预设。
 *
 * 名字按"空气里飘的是什么"取，而不是按强度取——诗词片的氛围本来就该
 * 由诗句决定：黄河大远景要水汽，将进酒要酒气与火星，破晓要霜雪。
 */
export const FX_PRESETS: Record<string, FxSettings> = {
  dust: { motes: 0.52, haze: 0.26, sweep: 0.38, breathe: 0.5, moteBlend: 'screen' },
  mist: { motes: 0.18, haze: 0.88, sweep: 0.2, breathe: 0.45, moteBlend: 'screen' },
  snow: { motes: 0.92, haze: 0.3, sweep: 0.12, breathe: 0.4, moteBlend: 'normal' },
  ember: { motes: 0.74, haze: 0.36, sweep: 0.52, breathe: 0.62, moteBlend: 'screen' },
  quiet: { motes: 0.16, haze: 0.14, sweep: 0.1, breathe: 0.3, moteBlend: 'screen' },
};

/** `auto` 时的气层轮转，跟运镜一样刻意避开连续同款。 */
const AUTO_FX = ['dust', 'mist', 'ember', 'dust', 'snow', 'mist', 'ember', 'quiet'];

export const resolveFx = (spec: string | ShotFx | undefined, index: number): FxSettings => {
  const base = FX_PRESETS.quiet;
  if (!spec || spec === 'auto') return FX_PRESETS[AUTO_FX[index % AUTO_FX.length]];
  if (typeof spec === 'string') return FX_PRESETS[spec] ?? base;
  return { ...base, ...spec };
};

const settingsLerp = (a: FxSettings, b: FxSettings, t: number): FxSettings => ({
  motes: lerp(a.motes, b.motes, t),
  haze: lerp(a.haze, b.haze, t),
  sweep: lerp(a.sweep, b.sweep, t),
  breathe: lerp(a.breathe, b.breathe, t),
  moteColor: t < 0.5 ? a.moteColor : b.moteColor,
  moteBlend: t < 0.5 ? a.moteBlend : b.moteBlend,
});

/**
 * 浮尘 / 飞雪 / 火星。
 *
 * 两层景深：远的小、暗、慢、模糊；近的大、亮、快、锐。景深差是"空气中的
 * 颗粒"和"屏幕上的脏点"之间唯一的区别，所以 size/rise/alpha 全部按 depth 插值。
 */
export const Motes: React.FC<{
  frame: number;
  width: number;
  height: number;
  settings: FxSettings;
  color: string;
  seed?: number;
}> = ({ frame, width, height, settings, color, seed = 1 }) => {
  const s = clamp01(settings.motes);
  if (s <= 0.02) return null;

  const count = Math.round(lerp(8, 38, s));
  const rnd = mulberry32(hashSeed(seed * 104729 + 12345));
  const span = height + 140;
  const nodes: React.ReactNode[] = [];

  for (let i = 0; i < count; i++) {
    const depth = rnd();
    const x0 = rnd() * (width + 140) - 70;
    const y0 = rnd() * span;
    const size = lerp(1.8, 6.6, depth);
    const rise = lerp(4.5, 25, depth);
    const amp = lerp(10, 42, depth);
    const w = lerp(0.005, 0.016, depth);
    const phase = rnd() * Math.PI * 2;
    const alpha = lerp(0.13, 0.46, depth) * lerp(0.32, 1, s);
    // 只在竖向取模，颗粒就永远朝上飘，不会"反弹"下来
    const y = height + 70 - ((y0 + rise * frame) % span);
    const x = x0 + Math.sin(frame * w + phase) * amp;

    nodes.push(
      <div
        key={i}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          width: size,
          height: size,
          borderRadius: '50%',
          transform: `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`,
          background: `radial-gradient(circle, ${color} 0%, ${withAlpha(color, 0)} 74%)`,
          opacity: alpha,
          willChange: 'transform',
        }}
      />,
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        mixBlendMode: settings.moteBlend,
        pointerEvents: 'none',
      }}
    >
      {nodes}
    </div>
  );
};

/**
 * 雾气流 / 水汽 / 炊烟。
 *
 * 三层不同大小、不同速度的柔光团横向漂移，位置错开周期也错开，
 * 所以看不见循环。层与层之间用 screen 叠，暗部几乎不受影响，
 * 只在中间调和高光处浮起来——正好是水汽该在的地方。
 */
export const Haze: React.FC<{
  frame: number;
  settings: FxSettings;
  color: string;
  seed?: number;
}> = ({ frame, settings, color, seed = 1 }) => {
  const s = clamp01(settings.haze);
  if (s <= 0.02) return null;

  const rnd = mulberry32(hashSeed(seed * 15485863 + 7));
  const speeds = [0.031, -0.019, 0.043].map((v) => v * (0.7 + rnd() * 0.6));
  const yOffsets = [36, 62, 28].map((v) => v + (rnd() - 0.5) * 14);
  const pos = speeds.map((sp, i) => {
    const p = ((frame * sp + rnd() * 200) % 240) - 70;
    return `${p.toFixed(1)}% ${yOffsets[i].toFixed(1)}%`;
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        mixBlendMode: 'screen',
        opacity: lerp(0.5, 1, s),
        pointerEvents: 'none',
        backgroundImage: [
          `radial-gradient(ellipse 46% 34% at 50% 50%, ${withAlpha(color, 0.17 * s)} 0%, ${withAlpha(color, 0)} 72%)`,
          `radial-gradient(ellipse 38% 44% at 50% 50%, ${withAlpha(color, 0.13 * s)} 0%, ${withAlpha(color, 0)} 76%)`,
          `radial-gradient(ellipse 56% 28% at 50% 50%, ${withAlpha(color, 0.11 * s)} 0%, ${withAlpha(color, 0)} 70%)`,
        ].join(', '),
        backgroundSize: '78% 64%, 92% 58%, 62% 46%',
        backgroundRepeat: 'no-repeat',
        backgroundPosition: pos.join(', '),
      }}
    />
  );
};

/**
 * 光扫。
 *
 * 一条柔和的斜向亮带，在镜头前半程从画面外扫到画面外，只走一次。
 * 用 soft-light 而不是 screen：前者只重新分配明暗，不会把画面整体提亮，
 * 像日照移动或门帘被掀开的瞬间。逐镜一次，多了就假。
 */
export const LightSweep: React.FC<{
  frame: number;
  frames: number;
  strength: number;
  color: string;
}> = ({ frame, frames, strength, color }) => {
  const s = clamp01(strength);
  if (s <= 0.02) return null;

  const dur = Math.max(26, Math.round(frames * 0.64));
  const p = clamp01(frame / dur);
  const opacity = Math.sin(Math.PI * p) * 0.46 * s;
  const x = lerp(-75, 175, softRamp(p, 0.22));

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        mixBlendMode: 'soft-light',
        opacity,
        transform: 'rotate(-8deg) scale(1.65)',
        backgroundImage: `linear-gradient(94deg, ${withAlpha(color, 0)} 0%, ${withAlpha(color, 0.3)} 40%, ${withAlpha(color, 0.46)} 50%, ${withAlpha(color, 0.3)} 60%, ${withAlpha(color, 0)} 100%)`,
        backgroundSize: '58% 100%',
        backgroundRepeat: 'no-repeat',
        backgroundPosition: `${x.toFixed(1)}% 50%`,
      }}
    />
  );
};

/**
 * 明暗呼吸。
 *
 * 幅度只有 ±2.2%，但人眼对亮度变化比对位移敏感得多——这一层最省成本地
 * 传达"画面是活的"。周期按 seed 在 4.6–7s 之间错开，几支镜头就不会同频闪。
 */
export const breatheAt = (frame: number, strength: number, seed = 1, fps = 30): number => {
  const s = clamp01(strength);
  if (s <= 0.02) return 1;
  const period = (4.6 + (hashSeed(seed) % 240) / 100) * fps;
  return 1 + 0.022 * s * Math.sin((frame / period) * Math.PI * 2);
};

/**
 * 全片共用的空气层。
 *
 * 刻意提到顶层、用全局帧号驱动，而不是塞进每个镜头里：空气不该在每次剪切时
 * 被重置。尘埃从第一个镜头飘到最后一个镜头，中间换的是密度和颜色，
 * 于是七次硬切读起来像同一个空间里的七个机位。
 */
export const FilmAir: React.FC<{
  shots: { from: number; durationInFrames: number; fx?: string | ShotFx }[];
  crossfade: number;
  width: number;
  height: number;
  color: string;
  seed?: number;
  /**
   * 两层分开挂：雾在暗角之下（它属于场景内部的空气），
   * 颗粒在暗角之上（它属于镜头前的空气，不该被片边压暗吃掉）。
   */
  part: 'haze' | 'motes';
}> = ({ shots, crossfade, width, height, color, seed = 1, part }) => {
  const frame = useCurrentFrame();
  if (!shots.length) return null;

  let i = shots.findIndex((s) => frame >= s.from && frame < s.from + s.durationInFrames);
  if (i < 0) i = shots.length - 1;

  let settings = resolveFx(shots[i].fx, i);
  if (i > 0) {
    // 剪切那十几帧里，前后两镜的气层互相渗透，不要"啪"地换掉。
    const k = clamp01((frame - shots[i].from) / Math.max(1, crossfade));
    if (k < 1) settings = settingsLerp(resolveFx(shots[i - 1].fx, i - 1), settings, k);
  }

  if (part === 'haze') return <Haze frame={frame} settings={settings} color={color} seed={seed} />;

  return (
    <Motes
      frame={frame}
      width={width}
      height={height}
      settings={settings}
      color={settings.moteColor || color}
      seed={seed}
    />
  );
};
