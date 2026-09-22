import { Composition } from 'remotion';
import { PoemVoiceover } from './PoemVideo';
import { timeline } from './timeline.generated';

export const Root: React.FC = () => {
  return (
    <Composition
      id="PoemVoiceover"
      component={PoemVoiceover}
      durationInFrames={timeline.durationInFrames}
      fps={timeline.fps}
      width={timeline.width}
      height={timeline.height}
    />
  );
};
