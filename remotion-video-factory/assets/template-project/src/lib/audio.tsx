import React from "react";
import {Audio, interpolate, Sequence, staticFile, useCurrentFrame} from "remotion";
import {clamp} from "./theme";

// SFX 钉帧表条目：from 一律写相对表达式（SHOTS.x.from + offset），时间线平移自动跟随。
// d = durationInFrames：长音效（>1.5s）必须给，靠 Sequence 截断，防拖到后续镜头。
export type Sfx = {from: number; src: string; volume: number; d: number};

export const SfxTracks: React.FC<{sfx: Sfx[]}> = ({sfx}) => (
  <>
    {sfx.map((s, i) => (
      <Sequence key={i} from={s.from} durationInFrames={s.d}>
        <Audio src={staticFile(s.src)} volume={s.volume} />
      </Sequence>
    ))}
  </>
);

// BGM：恒定电平 + 首尾淡入淡出（30f 入 / 90f 出），endAt 兜底截断
export const BgmTrack: React.FC<{src?: string; total: number; level?: number}> = ({
  src = "bgm/bgm.mp3", total, level = 0.34,
}) => {
  const frame = useCurrentFrame();
  const vol = interpolate(frame, [0, 30, total - 90, total], [0, level, level, 0], clamp);
  return <Audio src={staticFile(src)} volume={vol} endAt={total} />;
};
