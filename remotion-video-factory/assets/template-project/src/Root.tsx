// 注意：这里渲染的是 <MyComposition />（Composition 注册器），
// 不是场景组件本身 —— 渲染场景组件会报 "No video config found"。
import { MyComposition } from "./Composition";

export const RemotionRoot: React.FC = () => (
  <>
    <MyComposition />
  </>
);
