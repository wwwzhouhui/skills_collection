import { Composition } from "remotion";
import { Video, VideoProps } from "./Video";
import {FPS, TOTAL_FRAMES} from "./timeline";

export const MyComposition = () => (
  <Composition
    id="Video"
    component={Video}
    durationInFrames={TOTAL_FRAMES}
    fps={FPS}
    width={1920}
    height={1080}
    defaultProps={{bgm: true} as VideoProps}
  />
);
