// 动画小工具 —— 只用 Remotion 自带的 interpolate / spring，避免额外依赖。
import { interpolate, spring, Easing } from 'remotion';

export const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

/** 入场：帧 f 从 from 起，用 durF 帧淡入并上移 dy */
export function riseIn(f: number, from: number, durF: number, dy = 28) {
  const p = clamp01((f - from) / Math.max(1, durF));
  const e = Easing.out(Easing.cubic)(p);
  return { opacity: e, transform: `translateY(${(1 - e) * dy}px)` };
}

/** 入场：带轻微缩放的浮现 */
export function popIn(f: number, from: number, durF: number, fromScale = 0.94) {
  const p = clamp01((f - from) / Math.max(1, durF));
  const e = Easing.out(Easing.back(1.4))(p);
  return { opacity: clamp01(p * 1.5), transform: `scale(${fromScale + (1 - fromScale) * e})` };
}

/** 弹簧入场（更有"活着"的手感），返回 0..1 进度 */
export function springIn(fps: number, f: number, from: number, { damping = 16, stiffness = 130, mass = 0.8 } = {}) {
  return spring({ fps, frame: f - from, config: { damping, stiffness, mass }, durationInFrames: undefined });
}

/** 区间映射（帧） */
export function seg(f: number, a: number, b: number, outA = 0, outB = 1) {
  return interpolate(f, [a, b], [outA, outB], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
}

/** 呼吸式浮动：返回位移像素 */
export function breathe(f: number, amp = 4, periodF = 90) {
  return Math.sin((f / periodF) * Math.PI * 2) * amp;
}

/** 数值滚动（用于数据场景），带缓出 */
export function countUp(f: number, from: number, durF: number, to: number, decimals = 0) {
  const p = clamp01((f - from) / Math.max(1, durF));
  const e = Easing.out(Easing.cubic)(p);
  const v = to * e;
  return decimals > 0 ? v.toFixed(decimals) : Math.round(v).toLocaleString('en-US');
}
