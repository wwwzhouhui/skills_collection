import {Easing, interpolate} from "remotion";

// ---------------- 设计 tokens：一支片子一套，换风格改这里 ----------------
export const C = {
  bg: "#050712",      // 全局底色（深色科技）
  surface: "#0b1024", // 卡片/面板
  cyan: "#56e5ff",    // 主强调
  violet: "#8b7cff",  // 次强调
  warm: "#ffcf66",    // 警示/关键数字
  text: "#f5f7ff",    // 正文
  muted: "#9aa8c7",   // 次级文字
};

export const FONT = 'Inter, "Noto Sans SC", "Microsoft YaHei", sans-serif';
export const MONO = '"JetBrains Mono", "SFMono-Regular", Consolas, monospace';

// ---------------- 动效性格 tokens（专业信赖型，换品类整套换） ----------------
export const clamp = {extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const};
export const ease = Easing.bezier(0, 0, 0.2, 1); // 主入场缓动：快进慢停，不弹

// 场景淡入淡出（进出各 ≤18f；短场景自动缩短淡入淡出，<5f 不淡）。
// 出点必须用场景时长 D，不写死数字。
export const fade = (frame: number, duration: number) => {
  if (duration < 5) return 1; // 极短场景直接不淡，避免插值区间退化
  const f = Math.min(18, Math.max(1, Math.floor((duration - 2) / 4)));
  return interpolate(frame, [0, f, duration - f, duration], [0, 1, 1, 0], clamp);
};

// 每个场景组件统一接收 {D: 场景时长}，供 fade / hold 计算
export type SceneProps = {D: number};

// 固定种子伪随机（mulberry32）——确定性渲染铁律：禁 Math.random()
export const mulberry32 = (seed: number) => () => {
  seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
