import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import type { Shot } from '../timeline.generated';
import { moveForShot, transformAt } from './motion';
import { LightSweep, breatheAt, resolveFx } from './fx';

/**
 * 一个镜头 = 一张已经生成好的场景图 + 一次摄像机推进 + 一层镜内动效。
 *
 * 视频层完全不做「手搓画面」：素材就是页面管线用 hero 参考链锁出来的那套
 * 场景图，人物、地理、光照在世界观层面已经自洽。镜头层要做的只有三件事，
 * 按重要性排序：让画面**动起来**、让画面**呼吸**、让画面**别抢戏**。
 */
export const ScenePlane: React.FC<{
  shot: Shot;
  isFirst: boolean;
  crossfade: number;
  width: number;
  height: number;
  fps: number;
  /** 光扫的颜色，取调色板的金或月白。 */
  sweepColor: string;
  /** 全局运镜倍率。 */
  gain?: number;
  /** 手持微抖幅度（像素）。 */
  handheldPx?: number;
}> = ({ shot, isFirst, crossfade, width, height, fps, sweepColor, gain = 1, handheldPx = 3.4 }) => {
  const frame = useCurrentFrame();
  const total = shot.durationInFrames + crossfade;

  const move = moveForShot(shot.index, shot.move);
  const fx = resolveFx(shot.fx, shot.index);

  // push-through：新镜头从略微过曝的放大位落回本位，读起来像"穿过"了上一镜。
  const pushThrough = shot.transition === 'push-through' && !isFirst;

  const { scale, tx, ty, roll } = transformAt({
    move,
    seed: shot.seed,
    frame,
    frames: total,
    width,
    height,
    gain,
    handheldPx,
    enterBoost: pushThrough ? 0.14 : 0,
    enterFrames: 20,
  });

  const brightness = breatheAt(frame, fx.breathe, shot.seed, fps);

  // 首个镜头不淡入，否则片头会先黑一下；其余镜头在交叉窗口里淡入。
  // push-through 是例外：它必须几乎硬切。14 帧的溶解配上 1.4 倍的入场放大，
  // 会得到两个不同比例的人物各半透明地叠在一起，像印刷套版没对准，
  // 而不是"镜头扎进去"。5 帧之内压满，观感才是撞进去的。
  const fadeIn = pushThrough ? 5 : crossfade;
  const opacity = isFirst
    ? 1
    : interpolate(frame, [0, fadeIn], [0, 1], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp',
      });

  return (
    <AbsoluteFill style={{ opacity }}>
      <Img
        src={staticFile(shot.src)}
        style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${scale.toFixed(
            5,
          )}) rotate(${roll.toFixed(3)}deg)`,
          filter: brightness === 1 ? undefined : `brightness(${brightness.toFixed(4)})`,
          willChange: 'transform',
        }}
      />
      {/* 光扫跟着画面层走，但不吃运镜的 transform——它是掠过镜头的光，不是场景里的东西。 */}
      <LightSweep frame={frame} frames={total} strength={fx.sweep} color={sweepColor} />
    </AbsoluteFill>
  );
};
