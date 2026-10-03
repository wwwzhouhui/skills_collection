import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { Scene, BrandSpec } from '../types';
import type { Palette } from '../theme';
import { FONT } from '../theme';
import { riseIn, popIn, seg } from '../utils/anim';

/** 版面尺寸：横竖屏各一套，保证内容区不被右下角数字人和底部字幕压到 */
export type Layout = {
  pad: number;
  portrait: boolean;
  /** 内容舞台（不含页眉） */
  stage: { left: number; top: number; width: number; height: number };
  headingSize: number;
  subSize: number;
  kickerSize: number;
  cardRadius: number;
  gap: number;
};

export function layoutFor(width: number, height: number): Layout {
  const portrait = height > width;
  if (portrait) {
    return {
      pad: 72,
      portrait: true,
      // 底部留出数字人（右下角）与字幕条的地盘
      stage: { left: 72, top: 330, width: width - 144, height: height - 330 - 560 },
      headingSize: 76,
      subSize: 34,
      kickerSize: 28,
      cardRadius: 24,
      gap: 22,
    };
  }
  return {
    pad: 104,
    portrait: false,
    stage: { left: 104, top: 296, width: 1316, height: 592 },
    headingSize: 76,
    subSize: 34,
    kickerSize: 28,
    cardRadius: 24,
    gap: 30,
  };
}

/** 顶部胶囊小标签（如 "1956" / "第 1 步"） */
export const Kicker: React.FC<{ text: string; p: Palette; size: number }> = ({ text, p, size }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const a = popIn(f, 4, Math.round(fps * 0.42));
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 10,
        padding: `${Math.round(size * 0.3)}px ${Math.round(size * 0.78)}px`,
        borderRadius: 999,
        border: `2.5px solid ${p.accent}`,
        color: p.accent,
        background: 'rgba(255,255,255,0.7)',
        fontFamily: FONT.display,
        fontSize: size,
        fontWeight: 700,
        letterSpacing: 1.2,
        ...a,
      }}
    >
      {text}
    </div>
  );
};

/**
 * 场景外壳：页眉（kicker / 主标题 / 副标题）+ 内容槽 + 右上角进度。
 * 各版式模板只负责往内容槽里塞东西。
 */
export const SceneShell: React.FC<{
  scene: Scene;
  p: Palette;
  layout: Layout;
  index: number;
  count: number;
  children?: React.ReactNode;
  /** 品牌层：右上角博主名角标（brand.corner） */
  brand?: BrandSpec;
  /** 页眉对齐：left（默认）| center */
  align?: 'left' | 'center';
  /** 是否隐藏页眉（封面自己排版） */
  bare?: boolean;
}> = ({ scene, p, layout, index, count, children, brand, align = 'left', bare = false }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = Math.round(scene.duration * fps);

  // 出场 / 收场。
  // ⚠️ 入场必须比出场**快**：两个场景在交界处同时存在（pacing.sceneGap），
  //    如果入场也是 0.45s，交界那一刻新旧都只有半透明 → 整屏"发灰闪一下"。
  //    现在入场 0.22s、出场 0.3s，交界处新场景已经是 1.0、旧的正在退，覆盖度不掉。
  const inA = seg(f, 0, Math.max(2, Math.round(fps * 0.22)));
  const outA = seg(f, dur - Math.round(fps * 0.3), dur, 1, 0);
  const isLast = index === count - 1;
  const opacity = isLast ? inA : Math.min(inA, outA);

  const center = align === 'center';

  // 右上角：博主名角标（brand.corner，text 留空退用 brand.name）+ 场景进度。
  // 片尾卡（outro）是纯品牌画面，不叠角标与进度。
  const isOutro = scene.kind === 'outro';
  const corner = brand?.corner;
  const cornerText = String((corner && (corner.text || brand?.name)) || '').trim();
  const showCorner = !isOutro && corner?.enabled !== false && cornerText.length > 0;

  return (
    <div style={{ position: 'absolute', inset: 0, opacity }}>
      {/* 右上角：博主名 + 进度 */}
      <div
        style={{
          position: 'absolute',
          right: layout.pad,
          top: layout.pad - 6,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: 8,
        }}
      >
        {showCorner ? (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              fontFamily: FONT.display,
              fontSize: layout.portrait ? 24 : 26,
              fontWeight: 700,
              letterSpacing: 1.6,
              color: p.accent,
              opacity: seg(f, Math.round(fps * 0.2), Math.round(fps * 0.6), 0, 0.9),
              whiteSpace: 'nowrap',
            }}
          >
            ✦ {cornerText}
          </div>
        ) : null}
        {!isOutro && (
          <div
            style={{
              fontFamily: FONT.mono,
              fontSize: 26,
              fontWeight: 600,
              letterSpacing: 2,
              color: p.muted,
              opacity: seg(f, Math.round(fps * 0.3), Math.round(fps * 0.7)),
            }}
          >
            {String(index + 1).padStart(2, '0')} / {String(count).padStart(2, '0')}
          </div>
        )}
      </div>

      {!bare && (
        <div
          style={{
            position: 'absolute',
            left: layout.pad,
            right: layout.pad,
            top: layout.pad,
            display: 'flex',
            flexDirection: 'column',
            alignItems: center ? 'center' : 'flex-start',
            textAlign: center ? 'center' : 'left',
          }}
        >
          {scene.kicker ? (
            <div style={{ marginBottom: 22 }}>
              <Kicker text={scene.kicker} p={p} size={layout.kickerSize} />
            </div>
          ) : null}
          {scene.heading ? (
            <div
              style={{
                fontFamily: FONT.display,
                fontSize: layout.headingSize,
                fontWeight: 800,
                lineHeight: 1.14,
                letterSpacing: 0.5,
                color: p.ink,
                ...riseIn(f, 8, Math.round(fps * 0.5), 24),
              }}
            >
              {scene.heading}
            </div>
          ) : null}
          {scene.sub ? (
            <div
              style={{
                marginTop: 16,
                fontFamily: FONT.body,
                fontSize: layout.subSize,
                fontWeight: 500,
                color: p.muted,
                letterSpacing: 0.4,
                ...riseIn(f, 16, Math.round(fps * 0.5), 18),
              }}
            >
              {scene.sub}
            </div>
          ) : null}
        </div>
      )}

      {/* 内容槽：封面（bare）自己排版，所以给它整帧；其余压在安全区内 */}
      <div
        style={
          bare
            ? { position: 'absolute', inset: 0 }
            : {
                position: 'absolute',
                left: layout.stage.left,
                top: layout.stage.top,
                width: layout.stage.width,
                height: layout.stage.height,
              }
        }
      >
        {children}
      </div>
    </div>
  );
};
