import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { clamp01 } from './motion';

const fade = (frame: number, inFrom: number, inTo: number, outFrom: number, outTo: number) => {
  const enter = interpolate(frame, [inFrom, inTo], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const exit = interpolate(frame, [outFrom, outTo], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return Math.min(enter, exit);
};

/**
 * 片头字卡。
 *
 * 只出现在一个 `role: 'title'` 的镜头里，而且替掉那条同名字幕——
 * 大标题和朗读字幕同框是自我重复。
 *
 * 动效按"显影"而不是"弹出"来做：字从 16px 模糊里浮出来、字距从 0.34em 收拢到
 * 0.16em、金线从中间长出去。收拢字距这一步最关键——它让标题像被写上去的，
 * 而不是淡进来的。三件事共用同一条缓动曲线，所以读起来是一个动作。
 */
export const TitleCard: React.FC<{
  title: string;
  author: string;
  era: string;
  genre: string;
  moon: string;
  gold: string;
  serif: string;
  sans: string;
  frames: number;
}> = ({ title, author, era, genre, moon, gold, serif, sans, frames }) => {
  const frame = useCurrentFrame();
  const opacity = fade(frame, 8, 32, frames - 20, frames - 3);

  const develop = interpolate(frame, [8, 50], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const drift = (1 - develop) * 26;
  const blur = (1 - develop) * 16;
  const tracking = 0.34 - 0.18 * develop;

  const ruleGrow = interpolate(frame, [34, 74], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });
  const metaIn = interpolate(frame, [46, 82], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity,
        transform: `translateY(${drift.toFixed(2)}px)`,
      }}
    >
      <h1
        style={{
          margin: 0,
          fontFamily: serif,
          fontSize: 132,
          fontWeight: 500,
          letterSpacing: `${tracking.toFixed(3)}em`,
          color: moon,
          textShadow: '0 6px 42px rgba(0,0,0,0.68)',
          paddingLeft: `${tracking.toFixed(3)}em`,
          filter: blur < 0.05 ? undefined : `blur(${blur.toFixed(2)}px)`,
        }}
      >
        {title}
      </h1>

      <div
        style={{
          width: 120 * ruleGrow,
          height: 1,
          margin: '38px 0 30px',
          background: gold,
          opacity: 0.7 * ruleGrow,
        }}
      />

      <div
        style={{
          fontFamily: sans,
          fontSize: 34,
          letterSpacing: '0.34em',
          color: gold,
          paddingLeft: '0.34em',
          textShadow: '0 2px 16px rgba(0,0,0,0.6)',
          opacity: metaIn,
          transform: `translateY(${((1 - metaIn) * 14).toFixed(2)}px)`,
        }}
      >
        {author}
      </div>

      {(era || genre) && (
        <div
          style={{
            marginTop: 18,
            fontFamily: sans,
            fontSize: 24,
            letterSpacing: '0.2em',
            color: 'rgba(230, 226, 214, 0.62)',
            paddingLeft: '0.2em',
            opacity: metaIn,
            transform: `translateY(${((1 - metaIn) * 14).toFixed(2)}px)`,
          }}
        >
          {[era, genre].filter(Boolean).join(' · ')}
        </div>
      )}
    </div>
  );
};

/**
 * 片尾字卡。
 *
 * 人声结束后不立刻黑场——留一拍让最后那张图站住，再把书信息压上去。
 * 直接切黑会让整支片子像被拔了电源。
 *
 * 结尾的动效方向和片头相反：片头往上浮、字距收拢，片尾**缓慢下沉**、
 * 字距微微放开。一收一放，片子的呼吸才闭上。下沉做得很慢（80 帧 14px），
 * 慢到观众说不清哪里在动，只觉得画面还没停。
 */
export const EndCard: React.FC<{
  title: string;
  author: string;
  closing: string;
  moon: string;
  gold: string;
  serif: string;
  sans: string;
  from: number;
  duration: number;
}> = ({ title, author, closing, moon, gold, serif, sans, from, duration }) => {
  const frame = useCurrentFrame();
  // 只做淡入、不做淡出：字卡一直压到最后一帧。实测「淡入后又淡出」会把
  // 字卡的生命压到不足 1 秒，观众只看到一层残影。
  const opacity = fade(frame, from + 12, from + 40, duration + 60, duration + 61);

  const sink = interpolate(frame, [from + 12, from + 92], [0, 14], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });
  const tracking = 0.14 + 0.035 * clamp01((frame - from - 20) / 80);
  const ruleGrow = interpolate(frame, [from + 8, from + 44], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        opacity,
        transform: `translateY(${sink.toFixed(2)}px)`,
      }}
    >
      {/* 片尾常常落在天将破晓的高亮画面上，没有自己的暗底就会读不清。
          这层暗晕只罩字卡周围，不把整张结尾图压死。 */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse 62% 58% at 50% 50%, rgba(13,15,16,0.78) 0%, rgba(13,15,16,0.5) 46%, rgba(13,15,16,0) 76%)',
        }}
      />
      <div
        style={{
          position: 'relative',
          width: 90 * ruleGrow,
          height: 1,
          marginBottom: 34,
          background: gold,
          opacity: 0.6 * ruleGrow,
        }}
      />
      <div
        style={{
          position: 'relative',
          fontFamily: serif,
          fontSize: 76,
          letterSpacing: `${tracking.toFixed(4)}em`,
          color: moon,
          paddingLeft: `${tracking.toFixed(4)}em`,
          textShadow: '0 4px 30px rgba(0,0,0,0.66)',
        }}
      >
        {title}
      </div>
      <div
        style={{
          position: 'relative',
          marginTop: 22,
          fontFamily: sans,
          fontSize: 27,
          letterSpacing: '0.3em',
          color: gold,
          paddingLeft: '0.3em',
        }}
      >
        {author}
      </div>
      {closing && (
        <div
          style={{
            position: 'relative',
            marginTop: 40,
            fontFamily: sans,
            fontSize: 22,
            letterSpacing: '0.1em',
            color: 'rgba(230, 226, 214, 0.74)',
          }}
        >
          {closing}
        </div>
      )}
    </div>
  );
};
