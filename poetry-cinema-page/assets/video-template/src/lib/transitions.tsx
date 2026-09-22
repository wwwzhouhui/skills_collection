import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { clamp01 } from './motion';
import { withAlpha } from './fx';

/**
 * 转场。
 *
 * 旧版全片只有一种 14 帧交叉溶解，于是每一次剪切的心理重量完全一样，
 * 观众读不出"这一段完了、下一段开始"。句子之间该有轻重：悲怆起句要压黑，
 * 豪言出口要给一记暖光，同一口气里的两句就该是普通溶解。
 *
 * 三种覆盖层（dip-black / flash-warm / light-leak）在镜头交界处独立渲染，
 * 不动图像的 Sequence 结构，因此不会干扰已经对准人声的镜头边界。
 * push-through 是唯一的例外——它必须改图像本身的缩放曲线，做在 ScenePlane 里。
 */
export type TransitionKind =
  | 'crossfade'
  | 'dip-black'
  | 'flash-warm'
  | 'push-through'
  | 'light-leak';

/** 每种转场的覆盖层长度：负数是压在当前镜头尾上，正数是压在新镜头头上。 */
export const TRANSITION_SPAN: Record<TransitionKind, { before: number; after: number }> = {
  crossfade: { before: 0, after: 0 },
  'dip-black': { before: 12, after: 17 },
  'flash-warm': { before: 3, after: 21 },
  'light-leak': { before: 4, after: 24 },
  'push-through': { before: 0, after: 0 },
};

export const TransitionVeil: React.FC<{
  kind: TransitionKind;
  /** 新镜头的第一帧（全局帧号）。 */
  at: number;
  ink: string;
  gold: string;
  width: number;
  height: number;
}> = ({ kind, at, ink, gold, width, height }) => {
  const frame = useCurrentFrame();
  const span = TRANSITION_SPAN[kind];
  if (span.before + span.after === 0) return null;

  const p = frame - at;
  if (p < -span.before || p > span.after) return null;

  if (kind === 'dip-black') {
    // 谷底正好落在剪切帧上：观众感觉"眼前一暗"，而不是"画面淡出了"。
    const incoming = interpolate(p, [-span.before, 0], [0, 0.94], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.inOut(Easing.quad),
    });
    const outgoing = interpolate(p, [0, span.after], [0.94, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.inOut(Easing.quad),
    });
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: ink,
          opacity: Math.min(incoming, outgoing),
          pointerEvents: 'none',
        }}
      />
    );
  }

  if (kind === 'flash-warm') {
    // 峰值迟到 5 帧：光先于画面的记忆建立，于是"亮"被读成新镜头的开场。
    const peak = 5;
    const rise = interpolate(p, [-span.before, peak], [0, 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.quad),
    });
    const fall = interpolate(p, [peak, span.after], [1, 0], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.in(Easing.quad),
    });
    const k = Math.min(rise, fall) * 0.42;
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          mixBlendMode: 'screen',
          background: `radial-gradient(ellipse 92% 78% at 50% 46%, ${withAlpha(gold, k)} 0%, ${withAlpha(gold, k * 0.42)} 46%, ${withAlpha(gold, 0)} 82%)`,
          pointerEvents: 'none',
        }}
      />
    );
  }

  // light-leak：暖光从侧边渗进来，像暗房里不小心漏的那一下。
  const rise = interpolate(p, [-span.before, 9], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });
  const fall = interpolate(p, [9, span.after], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.inOut(Easing.quad),
  });
  const k = Math.min(rise, fall);
  const cx = interpolate(clamp01(rise), [0, 1], [-12, 26]);

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        mixBlendMode: 'screen',
        opacity: k * 0.55,
        pointerEvents: 'none',
        background: `radial-gradient(ellipse ${Math.round(
          width * 0.52,
        )}px ${Math.round(height * 0.9)}px at ${cx.toFixed(1)}% 48%, ${withAlpha(
          gold,
          0.7,
        )} 0%, ${withAlpha(gold, 0.3)} 40%, ${withAlpha(gold, 0)} 74%)`,
      }}
    />
  );
};
