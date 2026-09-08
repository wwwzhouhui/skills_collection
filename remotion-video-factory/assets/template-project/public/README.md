# 素材目录说明

- `vo/scene{N}.mp3` — tts.py 生成的分段配音（模板自带静音占位，跑 tts.py 后被真实配音覆盖）
- `sfx/*.mp3` — 音效素材。从免费商用音效库拷入，按场景命名子目录或直接平铺；
  钉帧表（Video.tsx 的 SFX 数组）引用路径相对本目录，如 `"sfx/impact.mp3"`。
  **只放确认过授权的素材**（推荐：Pixabay / freesound CC0 / video-shotcraft 技能的 audio/sfx）
- `bgm/bgm.mp3` — 背景音乐（可选；模板自带静音占位）。注意峰值电平，BgmTrack 默认 0.34 增益
