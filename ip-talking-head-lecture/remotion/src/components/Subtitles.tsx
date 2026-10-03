import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { Cue, Word } from '../types';
import { clamp01 } from '../utils/anim';
import { FONT } from '../theme';

/**
 * 底部居中字幕条（深色圆角胶囊）+ 逐字跟读高亮。
 *
 * 高亮来源：火山的逐字时间戳（scene.words）。把落在本 cue 时间窗内的字按顺序取出，
 * 逐字配到 cue 文本上，于是能判断"已读 / 正在读 / 未读"。
 * 小米通道只有句子级时间戳 → 退化为"整句同时点亮"，依然好读。
 */

type Props = {
  cues: Cue[];
  words: Word[];
  sceneStart: number;
  /** 字幕条中心距底部的距离（像素），默认 132 */
  bottom?: number;
  fontSize?: number;
  accent: string;
  maxWidth?: number;
};

type Glyph = { ch: string; s: number; e: number };

const visible = (s: string) => !/\s/.test(s);

/** cue 文本逐字对齐时间；拿不到逐字时间就整句同步 */
function glyphsFor(cue: Cue, words: Word[]): Glyph[] {
  const chars = [...cue.text];
  const whole = (): Glyph[] => chars.map((ch) => ({ ch, s: cue.start, e: cue.end }));

  // 1) 把 cue 时间窗内的 word 展开成"字"，小句级时间戳按字数等分
  const flat: Glyph[] = [];
  for (const w of words) {
    if (w.e <= cue.start - 0.02 || w.s >= cue.end + 0.02) continue;
    const ws = [...w.w];
    if (!ws.length) continue;
    const span = (w.e - w.s) / ws.length;
    ws.forEach((ch, i) => flat.push({ ch, s: w.s + span * i, e: w.s + span * (i + 1) }));
  }
  if (!flat.length) return whole();

  // 2) 逐字配时：文本与时间戳同源（都来自同一段旁白），正常情况下长度一致
  const usable = flat.filter((g) => visible(g.ch));
  const textChars = chars.filter(visible);
  // 长度差太多说明对不上（比如旁白被改过），别硬配，整句同步更安全
  if (Math.abs(usable.length - textChars.length) > Math.max(2, textChars.length * 0.25)) return whole();

  const out: Glyph[] = [];
  let k = 0;
  for (const ch of chars) {
    if (!visible(ch)) {
      const last = out[out.length - 1];
      out.push({ ch, s: last ? last.e : cue.start, e: last ? last.e : cue.end });
      continue;
    }
    if (k < usable.length) {
      out.push({ ch, s: usable[k].s, e: usable[k].e });
      k++;
    } else {
      const last = out[out.length - 1];
      out.push({ ch, s: last ? last.e : cue.start, e: cue.end });
    }
  }
  return out;
}

export const Subtitles: React.FC<Props> = ({
  cues,
  words,
  sceneStart,
  bottom = 132,
  fontSize = 46,
  accent,
  maxWidth = 1240,
}) => {
  const f = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const globalT = sceneStart + f / fps;

  const cue = cues.find((c) => globalT >= c.start - 0.14 && globalT <= c.end + 0.26);
  if (!cue) return null;

  const fadeIn = clamp01((globalT - (cue.start - 0.14)) / (6 / fps));
  const fadeOut = clamp01((cue.end + 0.26 - globalT) / (7 / fps));
  const opacity = Math.max(0, Math.min(fadeIn, fadeOut));

  const glyphs = glyphsFor(cue, words);
  const y = height - bottom;

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: y - fontSize * 0.95,
        display: 'flex',
        justifyContent: 'center',
        opacity,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          maxWidth,
          padding: `${Math.round(fontSize * 0.32)}px ${Math.round(fontSize * 0.7)}px`,
          borderRadius: 20,
          background: 'rgba(18,24,20,0.84)',
          boxShadow: '0 12px 32px rgba(12,22,16,0.26)',
          fontFamily: FONT.body,
          fontSize,
          fontWeight: 600,
          lineHeight: 1.34,
          letterSpacing: 0.6,
          textAlign: 'center',
          color: '#ffffff',
          // 长句在竖屏（1080 宽）会折行 —— 用 balance 让两行长度接近，
          // 否则会出现"第二行只剩一两个字"的孤字，很难看。
          textWrap: 'balance',
          textShadow: '0 1px 2px rgba(0,0,0,0.35)',
        }}
      >
        {glyphs.map((g, i) => {
          const spoken = globalT >= g.e;
          const current = !spoken && globalT >= g.s;
          return (
            <span
              key={i}
              style={{
                color: current ? accent : spoken ? '#ffffff' : 'rgba(255,255,255,0.52)',
                fontWeight: current ? 800 : 600,
              }}
            >
              {g.ch}
            </span>
          );
        })}
      </div>
    </div>
  );
};
