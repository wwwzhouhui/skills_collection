// 时间轴数据类型 —— lib/timeline.mjs 生成 timeline.json，本工程只读它，不在 React 里做业务计算。
// 坐标系：像素，左上角为原点。所有时间单位统一用**秒**（Remotion 帧数在组件里按 fps 换算）。

export type Cue = {
  /** 一条字幕的文本（通常是一个小句） */
  text: string;
  /** 起始秒 */
  start: number;
  /** 结束秒 */
  end: number;
};

export type Word = {
  /** 字/词（火山返回逐字，小米返回逐小句） */
  w: string;
  s: number;
  e: number;
};

export type Scene = {
  id: string;
  /** 版式模板 */
  kind: SceneKind;
  /** 场景在整片中的起始秒 */
  start: number;
  /** 场景时长（秒），= 配音时长 + 尾部留白 */
  duration: number;
  /** 配音文件名（相对 public/，如 audio/scene-1.wav）；空串表示无配音（如片尾卡） */
  audio: string;
  /** 配音是否循环补足场景时长（片尾卡用） */
  loopAudio?: boolean;
  /** 配音在场景内偏移（秒），默认 0；用来做"先入画再开口" */
  audioOffset?: number;
  /** 顶部胶囊小标签（如 "1956" / "第 1 步"） */
  kicker?: string;
  /** 主标题 */
  heading?: string;
  /** 副标题 / 说明 */
  sub?: string;
  /** 版式专属数据 */
  data?: any;
  /** 字幕条 */
  cues: Cue[];
  /** 逐字时间（做跟读高亮） */
  words: Word[];
};

export type SceneKind =
  | 'cover'
  | 'idea'
  | 'steps'
  | 'compare'
  | 'numbers'
  | 'recap'
  | 'outro';

export type AvatarSpec = {
  /** public/ 下的头像图（建议正方形，人物居中偏上） */
  image: string;
  /** 轻微张口（可选，与 image 同构图，用于口型开合） */
  mouthMid?: string;
  /** 明显张口（可选） */
  mouthOpen?: string;
  /** 当前使用的形象预设名（config.avatar.presets 的键，仅作标识） */
  preset?: string;
  /** 圆形直径（像素） */
  size: number;
  /** 圆心 x（像素） */
  x: number;
  /** 圆心 y（像素） */
  y: number;
  /** 圆形裁切时的对焦点（CSS object-position），动物与人物形象机位不同，按预设给 */
  focus?: string;
  /** 圆内放大倍数（默认 1.04：让头略大、把肩裁掉一点） */
  scale?: number;
  /** 外圈颜色 */
  ringColor: string;
  /** 是否显示说话光环与声波条 */
  showRing: boolean;
};

export type BrandSpec = {
  name: string;
  slogan: string;
  /** 品牌主色 */
  accent: string;
  /** 水印位置 */
  watermark?: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
  /** 片尾卡标识图（public/ 下相对路径，build 时从 brand.logo 拷入；空 = 手写名） */
  logo?: string;
  /** 右上角博主名角标（text 留空用 name；enabled=false 关闭） */
  corner?: { enabled?: boolean; text?: string };
  /** 片尾品牌卡配置（build 用；渲染端只读 cta 进 outro data） */
  endCard?: { enabled?: boolean; seconds?: number; cta?: string };
};

export type Timeline = {
  title: string;
  width: number;
  height: number;
  fps: number;
  /** 整片总时长（秒） */
  total: number;
  /** 背景基调：light（浅色纸感，默认）| dark */
  tone?: 'light' | 'dark';
  brand: BrandSpec;
  avatar: AvatarSpec;
  /** 字幕条几何（由 config.layout.<画幅>.subtitle 写入；缺省时组件按画幅自行推导） */
  subtitle?: {
    /** 字幕条中心距底部的像素距离 */
    bottom?: number;
    /** 字号（px） */
    fontSize?: number;
    /** 字幕条最大宽度（px），超过会被截断/溢出 */
    maxWidth?: number;
  };
  scenes: Scene[];
};
