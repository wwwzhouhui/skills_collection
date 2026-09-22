import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import type { Caption } from '../timeline.generated';
import { clamp01 } from './motion';

export type CaptionRole = 'verse' | 'prose' | 'title';

interface Style {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  letterSpacing: string;
  color: string;
  maxWidth: number;
}

/**
 * 两种字幕对应两种文本层，正好承接页面的「原文 + 直译」结构：
 *
 * - `verse`（原文）：大号衬线，宽字距，月白。它是被朗诵的主体，要压得住画面。
 * - `prose`（释义）：小一号，字距收紧，半透明。它是解释，不该和原文抢读。
 */
const stylesFor = (role: CaptionRole, moon: string, serif: string, sans: string): Style => {
  if (role === 'verse') {
    return {
      fontFamily: serif,
      fontSize: 64,
      lineHeight: 1.42,
      // maxWidth 按「最长一句 × 64px × (1+0.08)」再放宽一档：23 字的收尾句
      // 必须单行放下，否则「与尔同销万古愁。」会拆出孤字成行——
      // 中文字幕最刺眼的破相。配 textWrap: balance 兜底。
      letterSpacing: '0.08em',
      color: moon,
      maxWidth: 1740,
    };
  }
  return {
    fontFamily: sans,
    fontSize: 42,
    lineHeight: 1.62,
    letterSpacing: '0.02em',
    color: 'rgba(230, 226, 214, 0.88)',
    maxWidth: 1240,
  };
};

/**
 * 已念到与未念到之间的透明度差。
 *
 * 0.42 是实测的下限：再暗一点（试过 0.32），在黄河那张亮水面和破晓那张亮天空上，
 * 还没念到的后半句就糊进背景里、读不出来了。观众需要能"预览"整句话才不会
 * 被逐字节奏牵着走——逐字点亮要做的是**加一处高光**，不是**遮住其余的字**。
 */
const DIM = 0.42;

/**
 * 口播字幕。
 *
 * 三件事同时发生，缺一件就会回到"字直接贴上去"的塑料感：
 *
 * 1. **模糊入场**：`blur 6px → 0`，10 帧。中文笔画密，纯 fade 会像贴纸，
 *    从虚到实才像"显影"。
 * 2. **上浮入场**：18px 位移。给眼睛一个来处。
 * 3. **逐字点亮**（仅原文层）：按字数把整句摊在自己的人声区间里，念到的字
 *    全额、还没念到的字 0.32 透明度。这是口播片字幕的标准形态——字幕不再是
 *    一句标语，而是跟着声音长出来的一条线。
 *
 * 释义层刻意不给逐字：那是一整句解释，逐字闪会逼着观众盯着找节奏，
 * 反而读不进去。切得干脆才是解释该有的样子。
 */
export const VerseCaption: React.FC<{
  caption: Caption;
  moon: string;
  serif: string;
  sans: string;
  bottomOffset: number;
  /** 原文层是否逐字点亮；缺省开。 */
  reveal?: boolean;
}> = ({ caption, moon, serif, sans, bottomOffset, reveal = true }) => {
  const frame = useCurrentFrame();
  const IN = 10;
  const OUT = 7;
  const end = caption.end - caption.start;

  const enter = interpolate(frame, [0, IN], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const exit = interpolate(frame, [end - OUT, end], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const opacity = Math.min(enter, exit);
  const rise = (1 - enter) * 18;
  const blur = (1 - enter) * 6;

  const role: CaptionRole = caption.role === 'prose' ? 'prose' : 'verse';
  const st = stylesFor(role, moon, serif, sans);

  // 逐字时间基准：整句 84% 的区间用来铺字，留 16% 给尾音——
  // 人声的最后一个字往往比 sidecar 的 end 早，铺满会让字幕拖着等声音。
  const chars = role === 'verse' && reveal ? Array.from(caption.text) : null;
  const per = chars ? (end * 0.84) / Math.max(1, chars.length) : 0;

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: bottomOffset,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        opacity,
        transform: `translateY(${rise.toFixed(2)}px)`,
        filter: blur < 0.05 ? undefined : `blur(${blur.toFixed(2)}px)`,
      }}
    >
      <div
        style={{
          position: 'relative',
          maxWidth: st.maxWidth,
          textAlign: 'center',
          fontFamily: st.fontFamily,
          fontSize: st.fontSize,
          lineHeight: st.lineHeight,
          letterSpacing: st.letterSpacing,
          fontWeight: role === 'verse' ? 500 : 400,
          color: st.color,
          padding: '0 40px',
          // 均衡断行：避免中文逐字换行拆出孤字，也让长释义的两行长度接近
          textWrap: 'balance',
        }}
      >
        {/* 柔性暗晕：月亮、雪地、白衣人物这类高亮前景会把白字幕吃掉，
            textShadow 不够，需要在文字正后方垫一层椭圆暗底。 */}
        <div
          style={{
            position: 'absolute',
            inset: '-26px -60px',
            background:
              'radial-gradient(ellipse 50% 62% at 50% 50%, rgba(13,15,16,0.6) 0%, rgba(13,15,16,0.34) 52%, rgba(13,15,16,0) 78%)',
            zIndex: -1,
          }}
        />
        {chars
          ? chars.map((ch, i) => (
              // 逐字只改 opacity、不改 display，断行结果与整句完全一致，
              // 不会因为包了 span 就多出一次换行。
              <span
                key={i}
                style={{ opacity: DIM + (1 - DIM) * clamp01((frame - i * per) / 5) }}
              >
                {ch}
              </span>
            ))
          : caption.text}
      </div>
    </div>
  );
};
