import React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame} from "remotion";
import {C, FONT, clamp, ease} from "./theme";

// 网格 + 双色光晕背景（accent 可随场景换色）
export const GridBackground: React.FC<{accent?: string}> = ({accent = C.cyan}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.bg, overflow: "hidden"}}>
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          transform: `translateY(${(frame * 0.12) % 64}px)`,
          maskImage: "linear-gradient(to bottom, transparent, black 20%, black 80%, transparent)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 900,
          height: 900,
          left: -260,
          top: -340,
          borderRadius: "50%",
          background: accent,
          opacity: 0.1,
          filter: "blur(140px)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 800,
          height: 800,
          right: -260,
          bottom: -380,
          borderRadius: "50%",
          background: C.violet,
          opacity: 0.1,
          filter: "blur(150px)",
        }}
      />
    </AbsoluteFill>
  );
};

// 场景标题区：kicker（小标签）+ 大标题，入场轻微上移
export const Header: React.FC<{kicker: string; title: string; accent?: string}> = ({
  kicker, title, accent = C.cyan,
}) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [0, 24], [28, 0], {...clamp, easing: ease});
  return (
    <div style={{position: "absolute", left: 120, top: 92, fontFamily: FONT, transform: `translateY(${y}px)`}}>
      <div style={{fontSize: 24, fontWeight: 700, letterSpacing: 5, color: accent, marginBottom: 18}}>{kicker}</div>
      <div style={{fontSize: 70, lineHeight: 1.12, fontWeight: 800, color: C.text, letterSpacing: -3}}>{title}</div>
    </div>
  );
};

// 底部字幕卡（整句显示；卡拉OK逐词高亮请用 voice-to-video 路线）
export const Caption: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div
    style={{
      position: "absolute",
      left: 250,
      right: 250,
      bottom: 62,
      color: C.text,
      fontFamily: FONT,
      fontSize: 34,
      lineHeight: 1.5,
      textAlign: "center",
      textShadow: "0 3px 16px rgba(0,0,0,.9)",
    }}
  >
    {children}
  </div>
);
