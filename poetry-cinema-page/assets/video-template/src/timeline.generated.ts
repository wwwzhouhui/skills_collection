/* eslint-disable */
// 自动生成文件 —— 请勿手工编辑。
// 由 scripts/video.py build 从 video-plan.json + 配音时间轴 sidecar 生成。
// 仓库里这份占位让模板在没跑流水线时也能编译、能被 remotion studio 打开。

import type { ShotFx } from './lib/fx';

export type ShotRole = 'title' | 'beat' | 'outro';
export type CaptionRole = 'verse' | 'prose' | 'title';

export interface Shot {
  index: number;
  from: number;
  durationInFrames: number;
  /** 相对 public/ 的路径 */
  src: string;
  /** 运镜名，`auto` 由镜头序号轮转派生 */
  move: string;
  role: ShotRole;
  seed: number;
  /** 转场：crossfade | dip-black | flash-warm | push-through | light-leak */
  transition: string;
  /** 镜内气层：预设名（dust|mist|snow|ember|quiet|auto）或自定义强度对象 */
  fx?: string | ShotFx;
}

export interface Caption {
  text: string;
  start: number;
  end: number;
  role: CaptionRole;
  shot: number;
}

export const timeline = {
  slug: 'placeholder',
  fps: 30,
  width: 1920,
  height: 1080,
  durationInFrames: 30,
  audio: null as string | null,
  audioVolume: 1,
  bgm: null as string | null,
  bgmVolume: 0.3,
  title: '示例',
  author: '',
  era: '',
  genre: '',
  closing: '',
  palette: {
    ink: '#0d0f10',
    moon: '#e6e2d6',
    gold: '#d9a84e',
    amber: '#a8641f',
    ochre: '#b8763a',
  },
  font: {
    serif: '"Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", "SimSun", "KaiTi", serif',
    sans: '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
  },
  crossfadeFrames: 14,
  grainOpacity: 0.07,
  motionGain: 1,
  handheldPx: 3.4,
  captionReveal: true,
  shots: [] as Shot[],
  captions: [] as Caption[],
};
