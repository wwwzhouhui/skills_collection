// 视觉主题 —— 浅色纸感 + 品牌绿点缀，贴近参考片「清爽科普」的调性。
// 想换风格只改这里（或让 config.json 的 brand.accent 覆盖主色）。

export const FONT = {
  // HarmonyOS Sans SC / MiSans / PingFang 都是本机已安装字体，中文字形完整、笔画现代。
  display: '"HarmonyOS Sans SC", "MiSans", "PingFang SC", "Microsoft YaHei", sans-serif',
  body: '"MiSans", "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif',
  mono: '"Cascadia Mono", "Consolas", "SF Mono", monospace',
};

export type Tone = 'light' | 'dark';

export type Palette = {
  bg: string;
  bgGrad: string;
  panel: string;
  panelBorder: string;
  ink: string;
  inkSoft: string;
  muted: string;
  accent: string;
  accentSoft: string;
  accentInk: string;
  shadow: string;
};

export function palette(tone: Tone, accent: string): Palette {
  if (tone === 'dark') {
    return {
      bg: '#101613',
      bgGrad: 'radial-gradient(120% 90% at 22% 0%, #1b2620 0%, #101613 55%, #0b0f0d 100%)',
      panel: 'rgba(255,255,255,0.06)',
      panelBorder: 'rgba(255,255,255,0.12)',
      ink: '#f4f7f4',
      inkSoft: '#dde6df',
      muted: 'rgba(244,247,244,0.55)',
      accent,
      accentSoft: 'rgba(255,255,255,0.10)',
      accentInk: '#ffffff',
      shadow: '0 24px 60px rgba(0,0,0,0.45)',
    };
  }
  return {
    bg: '#f4f7f4',
    bgGrad: 'radial-gradient(115% 85% at 18% 0%, #ffffff 0%, #f3f8f3 42%, #e9f1ea 100%)',
    panel: 'rgba(255,255,255,0.86)',
    panelBorder: 'rgba(30,42,34,0.10)',
    ink: '#1d2621',
    inkSoft: '#38443c',
    muted: 'rgba(29,38,33,0.52)',
    accent,
    accentSoft: 'rgba(47,158,68,0.10)',
    accentInk: '#ffffff',
    shadow: '0 18px 44px rgba(24,44,30,0.10)',
  };
}

// 16:9 / 9:16 通用安全边距
export const PAD = 104;
