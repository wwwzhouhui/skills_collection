import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer('angle');
// 低核机器上 REMOTION 会把并发上限压到 2；诗词语境片子帧数不多，
// 保持 4 并发，低配环境由 CLI 的 --concurrency=1 覆盖。
Config.setConcurrency(4);
