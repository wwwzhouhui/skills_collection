import React from 'react';
import { useCurrentFrame, useVideoConfig, Img, staticFile } from 'remotion';
import type { AvatarSpec, Cue } from '../types';
import { clamp01 } from '../utils/anim';

/**
 * 右下角圆形卡通数字人。
 *
 * 真实的"口型同步"需要逐音素时间轴，我们只有句子/逐字时间，所以这里用**三层信号**叠出"在讲课"的可信感：
 *   1) 口型开合：闭口 → 微张 → 张口 三帧交叉淡入淡出，节奏由伪随机"音节"函数驱动（约 6–9 Hz 抖动，
 *      不是匀速正弦，否则像抽搐）。素材只给一张图时自动退化为"轻微挤压"，同样不会呆。
 *   2) 身体：待机浮动（sin）+ 说话时更大振幅的上下起伏 + ±1.2° 轻微摆动。
 *   3) 说话指示：外圈脉冲光环 + 底部声波条（只在 cue 区间内出现，句子间自动收）。
 */

type Props = {
  avatar: AvatarSpec;
  /** 本片的全部字幕条 —— 用来判断"此刻是否在说话" */
  cues: Cue[];
  /** 当前场景起点（秒），用于把全局时间映射到该场景内 */
  sceneStart: number;
};

/** 伪随机但可复现的 hash（同一帧永远同一结果，保证逐帧渲染一致） */
function hash(n: number) {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
}

/** 音节开合信号：0=闭口，1=全开。快速抖动 + 停顿，模仿连续说话的爆破音节奏。 */
function mouthSignal(t: number) {
  if (t <= 0) return 0;
  // 音节速率 6.5~9.5 Hz 之间缓慢漂移，避免机械感
  const rate = 7.6 + Math.sin(t * 0.9) * 1.4;
  const phase = t * rate;
  const i = Math.floor(phase);
  const frac = phase - i;
  // 每个音节的开合幅度不同（有的字口型大，有的小）
  const amp = 0.45 + hash(i) * 0.55;
  // 音节内部：快开慢合（说话时张口比闭口快）
  const shape = frac < 0.32 ? Math.pow(frac / 0.32, 0.7) : Math.pow(1 - (frac - 0.32) / 0.68, 1.6);
  return clamp01(shape * amp);
}

export const TalkingAvatar: React.FC<Props> = ({ avatar, cues, sceneStart }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps; // 场景内秒
  const globalT = sceneStart + t;

  // —— 是否在说话：cue 区间内算说话，句子之间留 0.12s 宽容
  const speaking = cues.some((c) => globalT >= c.start - 0.12 && globalT <= c.end + 0.06);
  const m = speaking ? mouthSignal(t) : 0;

  // —— 身体运动
  const idle = Math.sin((t * Math.PI * 2) / 3.4); // 3.4s 一个呼吸周期
  const bob = idle * (speaking ? 5.2 : 3.0);
  const tilt = Math.sin((t * Math.PI * 2) / 5.1) * (speaking ? 1.25 : 0.7);

  // 说话时下半脸轻微下压（"下巴在动"的错觉）：只压一点点，过大会变形
  const squash = speaking ? 1 + m * 0.012 : 1;

  // —— 口型三帧交叉
  const hasMouth = Boolean(avatar.mouthMid || avatar.mouthOpen);
  // m ∈ [0,1] → 闭口权重 / 微张权重 / 张口权重
  const wClosed = 1 - clamp01(m * 2.2);
  const wMid = clamp01(Math.min(m * 2.2, (1 - m) * 2.6));
  const wOpen = clamp01((m - 0.55) / 0.45);

  // —— 说话光环：两条错相脉冲
  const pulse = (offset: number) => {
    if (!speaking || !avatar.showRing) return 0;
    const p = ((t * 1.55 + offset) % 1 + 1) % 1;
    return p;
  };
  const p1 = pulse(0);
  const p2 = pulse(0.5);

  // —— 声波条：5 根，高度随音节信号变化
  const bars = 5;

  const D = avatar.size;
  // 形象机位（对焦点 / 放大倍数）由 config.avatar.presets.<名> 给：动物与人物形象的取景不同
  const focus = avatar.focus || '50% 24%';
  const zoom = Number.isFinite(avatar.scale) ? Number(avatar.scale) : 1.04;
  const imgStyle: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    objectFit: 'cover',
    // 靠 objectPosition 把脸框进圆里（不同形象的机位不一样）
    objectPosition: focus,
    transform: `scale(${zoom * squash}) translateY(${-D * 0.005 * (m || 0)}px)`,
    transformOrigin: '50% 42%',
  };

  return (
    <div
      style={{
        position: 'absolute',
        left: avatar.x - D / 2,
        top: avatar.y - D / 2,
        width: D,
        height: D,
        transform: `translateY(${bob}px) rotate(${tilt}deg)`,
        willChange: 'transform',
      }}
    >
      {/* 说话脉冲光环（在圆外） */}
      {avatar.showRing &&
        [p1, p2].map((p, i) =>
          p === 0 ? null : (
            <div
              key={i}
              style={{
                position: 'absolute',
                inset: -8,
                borderRadius: '50%',
                border: `3px solid ${avatar.ringColor}`,
                opacity: (1 - p) * 0.5,
                transform: `scale(${1 + p * 0.34})`,
              }}
            />
          ),
        )}

      {/* 外圈 + 投影 */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: '#ffffff',
          boxShadow: '0 22px 48px rgba(20,40,28,0.20), 0 2px 6px rgba(20,40,28,0.10)',
          border: `6px solid ${avatar.ringColor}`,
        }}
      />

      {/* 头像本体（圆形裁切） */}
      <div
        style={{
          position: 'absolute',
          inset: 6,
          borderRadius: '50%',
          overflow: 'hidden',
          background: '#e8efe9',
        }}
      >
        <Img src={staticFile(avatar.image)} style={{ ...imgStyle, opacity: hasMouth ? wClosed : 1 }} />
        {avatar.mouthMid ? (
          <Img src={staticFile(avatar.mouthMid)} style={{ ...imgStyle, opacity: wMid }} />
        ) : null}
        {avatar.mouthOpen ? (
          <Img src={staticFile(avatar.mouthOpen)} style={{ ...imgStyle, opacity: hasMouth ? wOpen : 0 }} />
        ) : null}

        {/* 顶部高光，给圆罩一点玻璃感 */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(70% 50% at 32% 14%, rgba(255,255,255,0.42) 0%, rgba(255,255,255,0) 60%)',
            pointerEvents: 'none',
          }}
        />
      </div>

      {/* 声波条：跨在圆的右下边缘上（贴太远会显得和圆脱节），只在说话时出现 */}
      {avatar.showRing && (
        <div
          style={{
            position: 'absolute',
            right: -8,
            bottom: '9%',
            display: 'flex',
            alignItems: 'flex-end',
            gap: 4,
            height: 34,
            opacity: speaking ? 1 : 0,
            transition: 'opacity 200ms',
          }}
        >
          {Array.from({ length: bars }).map((_, i) => {
            const env = speaking ? clamp01(mouthSignal(t + i * 0.055) * 1.25) : 0;
            const h = 8 + env * 26;
            return (
              <div
                key={i}
                style={{
                  width: 5,
                  height: h,
                  borderRadius: 3,
                  background: avatar.ringColor,
                  opacity: 0.9,
                  boxShadow: '0 2px 6px rgba(20,40,28,0.18)',
                }}
              />
            );
          })}
        </div>
      )}
    </div>
  );
};
