import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Timeline } from './types';
import { palette } from './theme';
import { Background } from './components/Background';
import { SceneShell, layoutFor } from './components/SceneShell';
import { TalkingAvatar } from './components/TalkingAvatar';
import { Subtitles } from './components/Subtitles';
import { ProgressBar, Watermark } from './components/Chrome';
import { SCENES } from './scenes';

/**
 * 主合成：背景 → 每个场景（页眉 + 版式）→ 数字人 → 字幕 → 品牌层。
 * 时间全部来自 timeline.json（由 TTS 的实际音频时长反推），所以音、画、字幕天然对齐。
 */
export const IpLecture: React.FC<Timeline> = (props) => {
  const f = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const p = palette(props.tone ?? 'light', props.brand.accent);
  const layout = layoutFor(width, height);
  const t = f / fps;

  const scenes = props.scenes ?? [];
  // 进度计数不含片尾卡（outro 是纯品牌画面，不该把 "01 / 09" 的总数撑大）
  const contentCount = scenes.filter((s) => s.kind !== 'outro').length;

  // ⚠️契约：timeline 里每个场景的 cue / word 时间都是**相对本场景起点**的（见 lib/build.mjs → buildCues）。
  // 而 <Subtitles> 与 <TalkingAvatar> 都挂在顶层、拿到的帧是**全局帧**，所以这里先统一平移到全局时间，
  // 再把 sceneStart 传 0。否则场景起点会被加两次 —— 首场景（start=0）看不出问题，从第 2 个场景起
  // 字幕全部匹配不到 cue，数字人也会判定为"一直没在说话"。
  const toGlobal = <T extends { start?: number; end?: number; s?: number; e?: number }>(
    arr: readonly T[] | undefined,
    off: number,
  ): T[] =>
    (arr ?? []).map((x) => {
      const y = { ...x } as { start?: number; end?: number; s?: number; e?: number };
      if (typeof y.start === 'number') y.start += off;
      if (typeof y.end === 'number') y.end += off;
      if (typeof y.s === 'number') y.s += off;
      if (typeof y.e === 'number') y.e += off;
      return y as T;
    });

  const allCues = scenes.flatMap((s) => toGlobal(s.cues, s.start));
  const cur = scenes.find((s) => t >= s.start && t < s.start + s.duration) ?? scenes[0];
  const curCues = cur ? toGlobal(cur.cues, cur.start) : [];
  const curWords = cur ? toGlobal(cur.words, cur.start) : [];

  // 字幕条位置：优先用 timeline.subtitle（来自 config.layout.<画幅>.subtitle），
  // 没给就按画幅高度推导。竖屏离底更远，避开平台 UI 与数字人。
  const portrait = height > width;
  const subSpec = props.subtitle ?? {};
  const subBottom = subSpec.bottom ?? (portrait ? Math.round(height * 0.115) : Math.round(height * 0.126));
  const subFont = subSpec.fontSize ?? (portrait ? 42 : 46);
  // 竖屏/方形只有 1080 宽，默认的 1240 会横向溢出 —— 兜底按画幅宽度收敛
  const subMaxWidth = subSpec.maxWidth ?? Math.min(1240, Math.round(width * 0.86));

  return (
    <AbsoluteFill style={{ background: p.bg, fontFamily: 'sans-serif' }}>
      <Background p={p} accent={props.brand.accent} />

      {scenes.map((sc, i) => {
        const from = Math.round(sc.start * fps);
        const dur = Math.max(2, Math.round(sc.duration * fps));
        const def = SCENES[sc.kind] ?? SCENES.idea;
        const Body = def.comp;
        return (
          <Sequence key={sc.id ?? i} from={from} durationInFrames={dur} name={`${i + 1}·${sc.kind}`} layout="none">
            <SceneShell
              scene={sc}
              p={p}
              layout={layout}
              index={i}
              count={contentCount}
              brand={props.brand}
              bare={def.bare}
            >
              <Body scene={sc} p={p} layout={layout} width={width} height={height} fps={fps} />
            </SceneShell>

            {/* 配音：放在场景内偏移处，让画面先入再开口 */}
            {sc.audio ? (
              <Sequence from={Math.round((sc.audioOffset ?? 0) * fps)} layout="none">
                <Audio src={staticFile(sc.audio)} />
              </Sequence>
            ) : null}
          </Sequence>
        );
      })}

      {/* 数字人（全局时间，跨场景常驻） */}
      {props.avatar ? <TalkingAvatar avatar={props.avatar} cues={allCues} sceneStart={0} /> : null}

      {/* 字幕：只画当前场景的 cue。cue/word 已在上方平移为全局时间，故 sceneStart 传 0 */}
      {cur ? (
        <Subtitles
          cues={curCues}
          words={curWords}
          sceneStart={0}
          bottom={subBottom}
          fontSize={subFont}
          maxWidth={subMaxWidth}
          accent={props.brand.accent}
        />
      ) : null}

      <ProgressBar p={p} total={props.total} height={height} />
      <Watermark brand={props.brand} p={p} total={props.total} />
    </AbsoluteFill>
  );
};
