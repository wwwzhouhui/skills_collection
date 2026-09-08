/**
 * Video.tsx — 组装层：场景节点表 + VO 挂载 + SFX 钉帧表 + BGM 开关。
 *
 * 三件套（lib/）提供 tokens / 基础组件 / 音频骨架；
 * 场景组件动画模式见 skill 的 references/animation-vocabulary.md。
 */
import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
} from "remotion";
import {C, FONT, MONO, clamp, ease, fade, SceneProps} from "./lib/theme";
import {GridBackground, Header, Caption} from "./lib/primitives";
import {SfxTracks, BgmTrack, Sfx} from "./lib/audio";
import {SHOTS, SCENE_ORDER, VO_MAP, TOTAL_FRAMES, FPS} from "./timeline";

export type VideoProps = {bgm?: boolean};

// ============================== 场景组件示例 ==============================
// 模式 A：数字滚动钩子（interpolate + round）
const Hook: React.FC<SceneProps> = ({D}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 55], [0.72, 1], {...clamp, easing: ease});
  const count = Math.round(interpolate(frame, [0, 65], [0, 1000000], clamp));
  return (
    <AbsoluteFill style={{opacity: fade(frame, D)}}>
      <GridBackground />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexDirection: "column",
          fontFamily: FONT,
        }}
      >
        <div style={{fontSize: 28, letterSpacing: 10, color: C.cyan, fontWeight: 700}}>DEMO · COUNTER</div>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 190,
            color: C.text,
            fontWeight: 800,
            letterSpacing: -14,
            transform: `scale(${scale})`,
            marginTop: 8,
          }}
        >
          {count.toLocaleString()}
        </div>
      </div>
      <Caption>数字滚动 + 缩放落定 —— 开场钩子模式</Caption>
    </AbsoluteFill>
  );
};

// 模式 B：矩阵逐格点亮（(行+列) 交错时序）
const Matrix: React.FC<SceneProps> = ({D}) => {
  const frame = useCurrentFrame();
  const n = 14;
  return (
    <AbsoluteFill style={{opacity: fade(frame, D)}}>
      <GridBackground accent={C.violet} />
      <Header kicker="DEMO · MATRIX" title="交错网格" accent={C.violet} />
      <div
        style={{
          position: "absolute",
          left: 150,
          top: 315,
          width: 650,
          height: 650,
          display: "grid",
          gridTemplateColumns: `repeat(${n}, 1fr)`,
          gap: 8,
        }}
      >
        {Array.from({length: n * n}).map((_, i) => {
          const row = Math.floor(i / n);
          const col = i % n;
          const delay = 35 + (row + col) * 2; // 对角波前
          const p = interpolate(frame, [delay, delay + 20], [0, 1], clamp);
          return (
            <div
              key={i}
              style={{
                borderRadius: 5,
                background: `rgba(139,124,255,${0.14 + p * 0.62})`,
                transform: `scale(${0.4 + p * 0.6})`,
              }}
            />
          );
        })}
      </div>
      <Caption>每个格子按 (行+列) 时序入场 —— 矩阵/热力图模式</Caption>
    </AbsoluteFill>
  );
};

// 模式 C：卡片弹簧入场（spring + 交错）
const Cards: React.FC<SceneProps> = ({D}) => {
  const frame = useCurrentFrame();
  const items = [
    ["FIRST", "错峰入场", C.cyan],
    ["SECOND", "弹簧物理", C.violet],
    ["THIRD", "呼吸留白", C.warm],
  ] as const;
  return (
    <AbsoluteFill style={{opacity: fade(frame, D)}}>
      <GridBackground />
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: FONT,
        }}
      >
        <div style={{fontSize: 28, letterSpacing: 7, color: C.muted, fontWeight: 700}}>DEMO · CARDS</div>
        <div style={{display: "flex", gap: 28, marginTop: 60}}>
          {items.map(([a, b, color], i) => {
            const p = spring({frame: frame - i * 18, fps: FPS,
              config: {damping: 18, stiffness: 110, mass: 0.8}});
            return (
              <div
                key={a}
                style={{
                  width: 470,
                  height: 240,
                  borderRadius: 28,
                  border: `2px solid ${color}`,
                  background: C.surface,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexDirection: "column",
                  transform: `translateY(${(1 - p) * 60}px)`,
                  opacity: p,
                }}
              >
                <div style={{fontFamily: MONO, fontSize: 33, color, fontWeight: 800}}>{a}</div>
                <div style={{fontSize: 35, color: C.text, marginTop: 28}}>{b}</div>
              </div>
            );
          })}
        </div>
      </div>
      <Caption>三卡片 spring 交错 —— 总结/要点模式</Caption>
    </AbsoluteFill>
  );
};

// ============================== SFX 钉帧表 ==============================
// 示例：真实项目按 sound-design.md 选音效文件放入 public/sfx/ 后启用。
const SFX: Sfx[] = [
  // {from: SHOTS.hook.from + 55, src: "sfx/bass-hit.mp3", volume: 0.5, d: 60},
  // {from: SHOTS.matrix.from + 40, src: "sfx/sweep.mp3", volume: 0.24, d: 36},
  // {from: SHOTS.cards.from + 45, src: "sfx/pop.mp3", volume: 0.35, d: 16},
];

// ============================== 组装 ==============================
export const Video: React.FC<VideoProps> = ({bgm = true}) => {
  const sceneNodes: Record<string, React.ReactNode> = {
    hook: <Hook D={SHOTS.hook.duration} />,
    matrix: <Matrix D={SHOTS.matrix.duration} />,
    cards: <Cards D={SHOTS.cards.duration} />,
  };

  return (
    <AbsoluteFill style={{background: C.bg}}>
      {/* 画面：按 SCENE_ORDER 顺序挂 Sequence */}
      {SCENE_ORDER.map((id) => (
        <Sequence key={id} from={SHOTS[id].from} durationInFrames={SHOTS[id].duration}>
          {sceneNodes[id]}
        </Sequence>
      ))}

      {/* 配音：VO_MAP 声明哪些场景有配音（public/vo/scene{N}.mp3） */}
      {SCENE_ORDER.filter((id) => VO_MAP[id]).map((id) => (
        <Sequence key={`vo-${id}`} from={SHOTS[id].from} durationInFrames={SHOTS[id].duration}>
          <Audio src={staticFile(`vo/scene${VO_MAP[id]}.mp3`)} volume={1} />
        </Sequence>
      ))}

      {/* 音效钉帧表 */}
      <SfxTracks sfx={SFX} />

      {/* BGM：bgm inputProp 控制，出无 BGM 版时传 {"bgm":false} */}
      {bgm ? <BgmTrack total={TOTAL_FRAMES} /> : null}
    </AbsoluteFill>
  );
};
