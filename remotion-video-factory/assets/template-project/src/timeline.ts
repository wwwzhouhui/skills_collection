// 示例时间线（3 场景演示）。真实项目由 scripts/build-timeline.mjs 按配音实测时长生成。
import type {SceneId} from "./types";

export const FPS = 30;

export const SHOTS: Record<SceneId, {from: number; duration: number}> = {
  hook: {from: 0, duration: 240},
  matrix: {from: 240, duration: 300},
  cards: {from: 540, duration: 240},
};

export const SCENE_ORDER: SceneId[] = ["hook", "matrix", "cards"] as const;

export const VO_MAP: Partial<Record<SceneId, number>> = {
  hook: 1,
  matrix: 2,
  cards: 3,
};

export const TOTAL_FRAMES = 780;
