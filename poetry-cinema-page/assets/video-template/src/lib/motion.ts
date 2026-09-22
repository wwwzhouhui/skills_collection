/**
 * 确定性运动工具 + 运镜词库。
 *
 * 铁律：禁止 Date.now() / Math.random()。一切伪随机走固定种子
 * （mulberry32，seed 由镜头序号派生），保证逐帧可复现、两次渲染零抖动。
 */

/** 32 位整数哈希，用来把任意 seed 折成一个 uint32。 */
export const hashSeed = (input: number): number => {
  let h = input | 0;
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b);
  h = h ^ (h >>> 16);
  return h >>> 0;
};

/** mulberry32：小而稳定的 PRNG，返回 [0,1)。 */
export const mulberry32 = (seed: number) => {
  let a = hashSeed(seed) >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);

/**
 * 线性与 easeInOutSine 的混合。
 *
 * 纯粹的匀速会被眼睛抓到硬启停，纯粹的 easeInOutSine 中段又飘。
 * k 控制"抹掉两端"的强度：0 是匀速，1 是完全的正弦缓动。
 */
export const softRamp = (t: number, k = 0.5): number => {
  const x = clamp01(t);
  const sine = 0.5 * (1 - Math.cos(Math.PI * x));
  return clamp01((1 - k) * x + k * sine);
};

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export type MoveName =
  | 'push-in'
  | 'pull-out'
  | 'drift-left'
  | 'drift-right'
  | 'rise'
  | 'settle'
  | 'breath'
  | 'tilt-up'
  | 'tilt-down'
  | 'arc-left'
  | 'arc-right'
  | 'creep'
  | 'sway';

export interface MoveSpec {
  s0: number;
  s1: number;
  /** 位移极值，单位是占画面宽/高的比例（0.06 = 画面宽的 6%）。 */
  tx0: number;
  tx1: number;
  ty0: number;
  ty1: number;
  /** 弧形运镜的纵向弯曲量（占画面高比例），0 是直线。 */
  arc?: number;
  /** 镜头内旋转，单位度（0.3 已是肉眼刚好能感觉到的上限）。 */
  roll0?: number;
  roll1?: number;
  /** 主行程的缓动强度。 */
  ease: number;
  /** 主行程在镜头前多少比例内走完，剩下的时间留给"落点"。 */
  settleAt?: number;
  /** 主行程占总位移的比例，剩下的 1-x 是收尾的慢速余量。 */
  travel?: number;
}

/**
 * 运镜词库：一镜只讲一个动作。
 *
 * 所有 scale 都 ≥ 1.15，这不是随手写的——图与画面同为 16:9，scale=1 就刚好
 * 铺满，位移空间只有 (s-1)/2。旧版把 scale 压在 1.06–1.17，位移只剩 ±1.4%，
 * 观众根本看不出在动。把基线抬到 1.15 以上，等于主动裁掉原图边缘 13%，
 * 换来 ±7% 的平移余量：画面终于推得动、摇得开，而任何一帧都不会露黑边。
 *
 * **上限锁在 1.26。** 这是被实测逼出来的：`settle` 原来从 1.31 起（裁掉 24%），
 * 在《将进酒》终镜那张破晓图上，人物的幞头顶端被画框切掉了——场景图是
 * 居左的人物 + 大远景，裁掉 12% 的顶部就切到人。1.26 对应每边 10.3%，
 * 是"远景里头顶还在画框内"的上限。再往上收紧，代价就直接落在构图上。
 *
 * 实测：1.32→1.16 这段 11% 的缩放，同镜头内人物变小约 15%、整体右移 4.6%
 * （1920 宽下约 88px），肉眼一眼可辨。所以不需要更狠的幅度。
 */
export const MOVES: Record<MoveName, MoveSpec> = {
  'push-in': { s0: 1.15, s1: 1.26, tx0: 0, tx1: 0, ty0: 0.018, ty1: -0.018, ease: 0.5 },
  'pull-out': { s0: 1.26, s1: 1.15, tx0: 0, tx1: 0, ty0: -0.015, ty1: 0.015, ease: 0.5 },
  'drift-left': { s0: 1.18, s1: 1.24, tx0: 0.055, tx1: -0.055, ty0: 0.014, ty1: -0.014, ease: 0.45 },
  'drift-right': { s0: 1.19, s1: 1.23, tx0: -0.055, tx1: 0.055, ty0: -0.012, ty1: 0.012, ease: 0.45 },
  rise: { s0: 1.16, s1: 1.24, tx0: 0.014, tx1: -0.014, ty0: 0.05, ty1: -0.05, ease: 0.55 },
  'tilt-up': { s0: 1.19, s1: 1.23, tx0: 0.008, tx1: -0.008, ty0: 0.062, ty1: -0.062, ease: 0.5 },
  'tilt-down': { s0: 1.21, s1: 1.18, tx0: -0.008, tx1: 0.008, ty0: -0.058, ty1: 0.058, ease: 0.5 },
  settle: { s0: 1.24, s1: 1.15, tx0: -0.03, tx1: 0.022, ty0: -0.042, ty1: 0.004, ease: 0.62 },
  breath: { s0: 1.15, s1: 1.21, tx0: -0.024, tx1: 0.024, ty0: 0.016, ty1: -0.016, ease: 0.4 },
  'arc-left': { s0: 1.18, s1: 1.24, tx0: 0.06, tx1: -0.06, ty0: 0.012, ty1: -0.012, arc: -0.026, ease: 0.5 },
  'arc-right': { s0: 1.18, s1: 1.24, tx0: -0.06, tx1: 0.06, ty0: -0.012, ty1: 0.012, arc: 0.026, ease: 0.5 },
  creep: { s0: 1.15, s1: 1.21, tx0: 0.006, tx1: -0.006, ty0: 0.006, ty1: -0.006, ease: 0.4, settleAt: 0.96, travel: 1 },
  sway: { s0: 1.17, s1: 1.22, tx0: -0.038, tx1: 0.038, ty0: 0.008, ty1: -0.008, roll0: -0.28, roll1: 0.28, ease: 0.35 },
};

export const MOVES_LIST = Object.keys(MOVES) as MoveName[];

/** push-through 入场放大的上限。见 transformAt 里的说明。 */
export const MAX_ENTER_SCALE = 1.42;

/**
 * `auto` 时的轮转次序。
 *
 * 刻意不按 MOVES 的声明顺序：相邻两镜必须换方向、换轴、换速度，
 * 否则连着两个 push-in 就读成"卡住了"。
 */
const AUTO_CYCLE: MoveName[] = [
  'push-in',
  'drift-left',
  'rise',
  'pull-out',
  'arc-right',
  'tilt-up',
  'settle',
  'drift-right',
  'creep',
  'sway',
  'arc-left',
  'tilt-down',
  'breath',
];

/** 由镜头序号派生运镜动作，同一首诗反复重渲染时结果完全一致。 */
export const moveForShot = (index: number, explicit?: string): MoveName => {
  if (explicit && explicit in MOVES) return explicit as MoveName;
  return AUTO_CYCLE[index % AUTO_CYCLE.length];
};

/**
 * 两段式行程。
 *
 * 关键改动。旧版是"整镜匀速滑到底"，Motion 分布太均匀，眼睛很快就把它
 * 归成静止背景。这里把镜头拆成两段：前 `settleAt` 帧走完 `travel` 的行程
 * （一次能被看见的移动），剩下 10% 用几乎停滞的速度慢慢收。
 * 于是每个镜头都有**明确的落点**——移到位置、停住、画面开始呼吸。
 * 这是纪录片镜头和"电子相册幻灯片"手感上的分水岭。
 */
export const twoPhase = (t: number, settleAt = 0.66, travel = 0.9, ease = 0.55): number => {
  if (t <= settleAt) return travel * softRamp(t / settleAt, ease);
  return travel + (1 - travel) * softRamp((t - settleAt) / (1 - settleAt), 0.9);
};

/** 手持微抖：两个不同频率的正弦叠加，极轻，但把"CG 输出"变成"有人在掌机"。 */
export const handheld = (seed: number, frame: number, amount: number) => {
  const r = mulberry32(seed * 6151 + 7);
  const p1 = r() * Math.PI * 2;
  const p2 = r() * Math.PI * 2;
  const p3 = r() * Math.PI * 2;
  const f1 = 0.09 + r() * 0.05; // rad/frame，周期约 1.4–3.5s 的呼吸
  const f2 = 0.17 + r() * 0.07;
  return {
    x: amount * (Math.sin(frame * f1 + p1) * 0.62 + Math.sin(frame * f2 + p2) * 0.38),
    y: amount * (Math.sin(frame * f1 * 1.37 + p3) * 0.55 + Math.sin(frame * f2 * 0.83 + p1) * 0.45),
    roll: 0.07 * Math.sin(frame * f2 * 1.11 + p2),
  };
};

export interface Transform {
  scale: number;
  tx: number;
  ty: number;
  roll: number;
}

export interface TransformOptions {
  move: MoveName;
  seed: number;
  frame: number;
  /** 这支镜头自己占的总帧数（含交叉溶解的尾巴）。 */
  frames: number;
  width: number;
  height: number;
  /** 手持微抖幅度，单位像素；0 关闭。 */
  handheldPx?: number;
  /** 入场额外放大比例（push-through 转场用），到 `enterFrames` 内衰减回 0。 */
  enterBoost?: number;
  enterFrames?: number;
  /** 全局运镜倍率：1 是标准，1.3 更冲，0.6 更含蓄。 */
  gain?: number;
}

/**
 * 求某一帧的镜头 transforms。
 *
 * 安全钳位按**当前帧**的 scale 算，而不是整段最小 scale——图片在该帧的
 * 覆盖范围是 width*scale，可平移上限就是 width*(scale-1)/2，再留 12% 余量。
 * 旋转带来的角点外扩（0.3° 约 4px）也被这个余量吸收。
 */
export const transformAt = (o: TransformOptions): Transform => {
  const spec = MOVES[o.move];
  const gain = o.gain ?? 1;
  // 长镜头要动得久一点。196 帧的短镜 66% 就落位没问题；822 帧的终镜如果
  // 也这么早停住，最后五六秒会读成"卡住了"。所以按镜头长度把落点往后推，
  // 短镜利落、长镜绵长，全片才有呼吸的松紧。
  const adapt = clamp01((o.frames - 150) / 500);
  const settleAt = lerp(spec.settleAt ?? 0.66, 0.84, adapt);
  const travel = spec.travel ?? 0.9;

  const t = twoPhase(o.frames <= 1 ? 1 : o.frame / (o.frames - 1), settleAt, travel, spec.ease);

  const rnd = mulberry32(o.seed * 7919 + 13);
  const jitterA = (rnd() - 0.5) * 0.16; // ±8% 幅度扰动，避免每镜推进如出一辙
  const jitterB = (rnd() - 0.5) * 0.16;

  // gain 只缩放"移动的幅度"，不挪动基线：围绕 s0/s1 的中点收放。
  // gain=1 是完整行程；gain=0.9（讲解版）推拉只剩九成；gain=0 完全静止。
  // 结果始终落在 [s0, s1] 内，而两者都 ≥ 1.15，所以收幅度不会露黑边。
  const sMid = (spec.s0 + spec.s1) / 2;
  let scale = sMid + (lerp(spec.s0, spec.s1, t) - sMid) * gain;
  const rawTx = lerp(spec.tx0 * (1 + jitterA), spec.tx1 * (1 + jitterA), t);
  const rawTy = lerp(spec.ty0 * (1 + jitterB), spec.ty1 * (1 + jitterB), t);
  // 弧形运镜：横向走直线的同时，纵向叠一条抛物线，走出真正的弧。
  const arc = (spec.arc ?? 0) * Math.sin(Math.PI * t) * gain;
  const roll = lerp(spec.roll0 ?? 0, spec.roll1 ?? 0, t) * gain;

  // push-through：入场那一瞬额外放大，然后在十几帧内落回本位。
  // 封顶 1.42：有些运镜的起点本来就近景（pull-out 从 1.32 起），再叠 14% 会
  // 把原图裁掉三分之一，构图里贴边的主体就被切出去了。封顶之后"扎进去"的
  // 冲劲还在，但任何一镜都不会把自己裁残。
  if (o.enterBoost) {
    const ef = Math.max(1, o.enterFrames ?? 16);
    const decay = 1 - softRamp(clamp01(o.frame / ef), 0.42);
    scale = Math.min(scale * (1 + o.enterBoost * decay), MAX_ENTER_SCALE);
  }

  const hh = o.handheldPx ? handheld(o.seed, o.frame, o.handheldPx) : { x: 0, y: 0, roll: 0 };

  const limitX = ((scale - 1) * o.width) / 2 * 0.88;
  const limitY = ((scale - 1) * o.height) / 2 * 0.88;

  return {
    scale,
    tx: Math.max(-limitX, Math.min(limitX, rawTx * o.width * gain + hh.x)),
    ty: Math.max(-limitY, Math.min(limitY, (rawTy + arc) * o.height * gain + hh.y)),
    roll: roll + hh.roll,
  };
};
