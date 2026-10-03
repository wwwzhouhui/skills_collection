import React from 'react';
import { Composition } from 'remotion';
import { IpLecture } from './IpLecture';
import type { Timeline } from './types';
// 默认 props = 构建期写进来的本期时间轴（lib/timeline.mjs 生成）。
// 渲染时不需要 --props，bundler 每次都会重新读这个文件，所以换个脚本重新 build 就换片。
import timeline from './generated/timeline.json';

const fallback = timeline as unknown as Timeline;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="IpLecture"
      component={IpLecture}
      durationInFrames={Math.max(2, Math.round(((fallback.total as number) || 1) * (fallback.fps || 30)))}
      fps={fallback.fps || 30}
      width={fallback.width || 1920}
      height={fallback.height || 1080}
      defaultProps={fallback}
      calculateMetadata={({ props }) => {
        const tl = props as Timeline;
        const fps = tl.fps || 30;
        // 时长由 timeline.json 的 total 决定（TTS 实际时长反推），不用手填帧数
        return {
          durationInFrames: Math.max(2, Math.round((tl.total || 1) * fps)),
          fps,
          width: tl.width || 1920,
          height: tl.height || 1080,
        };
      }}
    />
  );
};
