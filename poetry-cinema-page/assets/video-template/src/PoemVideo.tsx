import React from 'react';
import { AbsoluteFill, Audio, Sequence, staticFile } from 'remotion';
import { timeline } from './timeline.generated';
import { ScenePlane } from './lib/scene-stage';
import { VerseCaption } from './lib/captions';
import { TitleCard, EndCard } from './lib/cards';
import { Grain, Vignette } from './lib/atmosphere';
import { FilmAir } from './lib/fx';
import { TransitionVeil, type TransitionKind } from './lib/transitions';

const DEFAULT_SERIF =
  '"Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", "KaiTi", serif';
const DEFAULT_SANS = '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';

/**
 * 诗词口播「影像成片」。
 *
 * 时间轴的权威来源是 audio sidecar（narration.py 逐行产出的 start/end），
 * 画面只是被钉到已经存在的一条人声上——这是口播片和宣传片最本质的区别：
 * 先有声音，后有镜头；不是先排动画再往里塞人声。
 *
 * 图层自下而上是：场景图（含镜内运镜/呼吸/光扫）→ 雾 → 暗角 → 颗粒浮尘 →
 * 转场覆盖层 → 字卡与字幕 → 声音 → 胶片颗粒。
 * 顺序都是有用的：雾必须在暗角之下，否则暗角压不住它、画面会发灰；
 * 浮尘必须在暗角之上，否则片边的尘埃会被压没；转场必须在字幕之下，
 * 否则压黑和闪白会连字幕一起吞掉。
 */
export const PoemVoiceover: React.FC = () => {
  const t = timeline;
  const { width, height } = t;
  const cross = t.crossfadeFrames;

  const palette = t.palette;
  const serif = t.font?.serif || DEFAULT_SERIF;
  const sans = t.font?.sans || DEFAULT_SANS;

  const titleShot = t.shots.find((s) => s.role === 'title');

  // 片头字卡自带这两行信息，字幕再念一遍就是重复信息。
  const captions = t.captions.filter(
    (c) => c.role !== 'title' && !(titleShot && c.shot === titleShot.index),
  );

  const lastCaptionEnd = captions.reduce((m, c) => Math.max(m, c.end), 0);
  // 末句人声一落就接片尾字卡；tail_seconds 默认 3s 起步，字卡才站得住。
  const endCardFrom = Math.min(Math.max(lastCaptionEnd + 8, 0), Math.max(0, t.durationInFrames - 60));

  const veils = t.shots
    .map((s, i) => ({ s, i }))
    .filter(({ s, i }) => i > 0 && s.transition && s.transition !== 'crossfade');

  return (
    <AbsoluteFill style={{ backgroundColor: palette.ink, overflow: 'hidden' }}>
      {/* 1. 图像层：每个 Sequence 多活 crossfade 帧，后一张淡入压在前一张尾巴上，形成真正的交叉溶解。 */}
      {t.shots.map((s, i) => (
        <Sequence
          key={s.index}
          from={s.from}
          durationInFrames={Math.max(1, s.durationInFrames + cross)}
        >
          <ScenePlane
            shot={s}
            isFirst={i === 0}
            crossfade={cross}
            width={width}
            height={height}
            fps={t.fps}
            sweepColor={palette.gold}
            gain={t.motionGain ?? 1}
            handheldPx={t.handheldPx ?? 3.4}
          />
        </Sequence>
      ))}

      {/* 2. 大气层（雾）：属于场景内部，要压在暗角下面 */}
      <FilmAir
        part="haze"
        shots={t.shots}
        crossfade={cross}
        width={width}
        height={height}
        color={palette.gold}
      />

      {/* 3. 暗角 */}
      <Vignette ink={palette.ink} />

      {/* 4. 大气层（浮尘）：属于镜头前，要压在暗角上面 */}
      <FilmAir
        part="motes"
        shots={t.shots}
        crossfade={cross}
        width={width}
        height={height}
        color={palette.moon}
        seed={7}
      />

      {/* 5. 转场覆盖层：压黑、闪暖光、暖光渗边。做在字幕之下，不吞文字。 */}
      {veils.map(({ s }) => (
        <TransitionVeil
          key={`veil-${s.index}`}
          kind={s.transition as TransitionKind}
          at={s.from}
          ink={palette.ink}
          gold={palette.gold}
          width={width}
          height={height}
        />
      ))}

      {/* 6. 片头字卡 */}
      {titleShot && (
        <Sequence from={titleShot.from} durationInFrames={Math.max(1, titleShot.durationInFrames)}>
          <TitleCard
            title={t.title}
            author={t.author}
            era={t.era}
            genre={t.genre}
            moon={palette.moon}
            gold={palette.gold}
            serif={serif}
            sans={sans}
            frames={titleShot.durationInFrames}
          />
        </Sequence>
      )}

      {/* 7. 字幕层 */}
      {captions.map((c, i) => (
        <Sequence key={`cap-${i}`} from={c.start} durationInFrames={Math.max(1, c.end - c.start)}>
          <VerseCaption
            caption={c}
            moon={palette.moon}
            serif={serif}
            sans={sans}
            bottomOffset={c.role === 'prose' ? 132 : 116}
            reveal={t.captionReveal ?? true}
          />
        </Sequence>
      ))}

      {/* 8. 片尾 */}
      <EndCard
        title={t.title}
        author={t.author}
        closing={t.closing}
        moon={palette.moon}
        gold={palette.gold}
        serif={serif}
        sans={sans}
        from={endCardFrom}
        duration={t.durationInFrames}
      />

      {/* 9. 声音 */}
      {t.audio && <Audio src={staticFile(t.audio)} volume={t.audioVolume ?? 1} />}
      {t.bgm && <Audio src={staticFile(t.bgm)} volume={t.bgmVolume ?? 0.3} />}

      {/* 10. 颗粒压在最上层，把所有层次的边缘揉到一起 */}
      <Grain opacity={t.grainOpacity ?? 0.07} />
    </AbsoluteFill>
  );
};
