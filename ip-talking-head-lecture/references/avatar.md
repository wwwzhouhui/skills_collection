# 口播形象与口型素材

数字人的观感由**三张同构图的图**决定：闭口 / 微张 / 张口。三张必须**同机位、同光照、同画风**，否则口型开合时整张脸会跳。

## 内置两套形象

| 预设名 | 形象 | 风格 | 素材目录 |
|---|---|---|---|
| `haibao` | 海老豹 | 动物卡通（雪豹崽，浅蓝底） | `assets/avatars/haibao/` |
| `human` | 眼镜青年 | 人物卡通（3D 渲染，绿底，格纹毛衣） | `assets/avatars/human/` |

```bash
iph avatars                        # 列出所有形象 + 三帧齐不齐 + 当前默认（* 标记）
iph preset human                   # 切换**默认**形象（写进 config.json，之后所有期都用它）
iph all <期> --preset=human         # 只给这一期换形象，不动全局默认
iph still <期> 12 --ratio=16:9 --preset=human   # 换形象后先出静帧看机位
```

也可以在某一期的 `script.json` 里写死：

```jsonc
"avatar": { "preset": "human" }
```

**优先级**：`--preset=` > `script.json` 的 `avatar.preset` > `config.json` 的 `avatar.preset` > 老式兜底路径。

> ⚠️ **换形象必须重新 build**。形象信息是在 build 时写进 `timeline.json` 的，只改 config 不出片。
> `iph still/render` 带了 `--preset=` 会自动先 build 一次（配音走缓存，很快）。

## 目录结构

```
<仓库>/assets/avatars/<形象名>/
├── image.png        闭口（必给）
├── mouth-mid.png    微张（可选）
└── mouth-open.png   张口（可选）
```

- **扩展名不限**（png / jpg / webp 都认）。
- 主名认三种写法：`image|avatar`、`mouth-mid|mouthMid|avatar-mid`、`mouth-open|mouthOpen|avatar-open`。
- **期专属形象**放 `episodes/<期>/assets/`（或期目录根下），同名会**优先于**预设目录 —— 只想给某一期换脸时用它，不用动全局配置。
- 只给 `image` 也能出片：口型退化为"轻微挤压 + 说话光环 + 声波条"。三帧齐全时明显更像真人在讲。

## 加一套新形象（四步）

```bash
A=<仓库>/assets/avatars
mkdir -p "$A/<新名>"

# 1. 裁底图（下一节）→ $A/<新名>/image.png
# 2. 生成两张口型帧    → $A/<新名>/mouth-mid.png、mouth-open.png
# 3. 在 config.json 的 avatar.presets 登记一行：
#    "<新名>": { "label": "动物卡通 · 海豹", "kind": "animal",
#                "dir": "assets/avatars/<新名>", "focus": "50% 24%", "scale": 1.04 }
# 4. 确认素材被发现（三列都该是 ✓）：
iph avatars
```

`presets` 里每一项的字段：

| 字段 | 作用 |
|---|---|
| `label` | 列表里显示的名字（`iph avatars`） |
| `kind` | 自用分类标签（`animal` / `human` / 随便写） |
| `dir` | 素材目录，相对 skill 根；也接受绝对路径与 `~` |
| `focus` | CSS `object-position`，**只有素材不是正方形时才有意义**（决定方形圆里取哪一块）。方图忽略 |
| `scale` | 圆内放大倍数，默认 `1.04`。想让脸更大就 `1.08~1.2` |

## 底图怎么裁

数字人是**圆形头肩半身**机位，底图请裁成**正方形**，且脸的焦点大致落在画面上 45% 的位置。

```bash
# 从一张 1024×1536 的全身立绘裁出"头肩半身"方图
ffmpeg -i 立绘.png -vf "crop=880:880:60:170,scale=1024:1024:flags=lanczos" -q:v 2 image.png
#                    └宽 ┘└高 ┘└x┘└y┘
```

判断标准：**头顶留一点空（约 8%）、下巴以下露到胸口、左右刚好到肩外缘**。

裁完一定直接看一眼（用 Read 打开这个 png），别盲调 crop 参数：

> 经验 1：全身立绘里头部通常比直觉更靠下。先按估算裁一次，看图，再按偏差修正 `y`。
> 经验 2：**头顶留白宁可多给**。圆形裁切会把上边缘往内收，头顶贴边会显得人"顶出画框"。
> 经验 3：两套内置形象都是这么来的 —— 人物卡通那张原图是 1024×768 的头肩半身，用了 `crop=700:700:162:0` 再放大到 1024。

## 两张口型帧怎么来

三种办法，从好到次：

**① AI 图生图（推荐，质量最好）**

用 `ImageGen` 工具，把 `image.png` 当 `image1` 传进去，提示词要点：

- **先锁死不变的东西**：构图、机位、姿势、背景、毛发/发丝质感、斑点、眼镜、眼睛、耳朵、衣服纹理 —— 逐项列出来。
- **把"不要动脸"写死**：`Do NOT widen the eyes. Do NOT raise the eyebrows. Do NOT change the facial expression or the head angle.`
  （不写这句，模型十有八九顺手给你一个"惊讶脸"，而眼睛一变，三帧交叉时整张脸会跳。）
- **再描述唯一的改动**：
  - 微张 = `lips parted into a small natural opening, roughly 20% open, upper front teeth barely visible`
  - 张口 = `mouth open in a natural speaking way, roughly 60% open, upper teeth and dark mouth interior visible`
    补一句 `NOT exaggerated, NOT a surprised face, NOT a shout`，否则会得到一张惊愕脸。
- **参数**：`size` 与原图一致（如 `1024x1024`），`input_fidelity: "high"`，`quality: "high"`。
- **一次只生成一张**：同一秒内并发两次会**撞文件名互相覆盖**，用不同的 `output_dir` 分开放。
- **检查**：生成结果右下角会带平台水印。先确认它落在**圆形裁切之外**（圆内可见区域 ≈ 以图心为圆心、半径 = 边长 48% 的圆）；
  为防以后调机位露出来，用 `delogo` 抹掉。⚠️ delogo 的区域**不能贴到图片边缘**（会报 `Logo area is outside of the frame`），留 4px 余量：

```bash
ffmpeg -i raw.png -vf "delogo=x=852:y=932:w=152:h=76" -q:v 2 mouth-open.png
#                         └x ┘└y ┘└宽 ┘└高┘  —— 右下角水印大致就是这个区域（1024×1024 素材）
```

**② 从表情表里抠**

如果已有九宫格表情表（含"张嘴笑""唱歌"），可以把对应格整张当 `mouth-open`。
⚠️ 前提是**同一套画风、同一机位**。3D 立绘配 2D 贴纸格会前后风格断裂。

**③ 直接加两张近似图**

把 `mouth-mid` / `mouth-open` 都指向同一张略作缩放的闭口图 —— 动作幅度小，但至少不会崩。

## 机位微调

三处可调，从粗到细：

```jsonc
// config.json
"layout": {
  "16:9": { "avatar": { "size": 340, "x": 1690, "y": 752 }, ... }   // ③ 圆的大小与位置
},
"avatar": {
  "presets": {
    "human": { "focus": "50% 24%", "scale": 1.04 }                 // ② 圆内取景
  }
}
```

| 想改什么 | 调哪里 |
|---|---|
| 脸在圆里偏上/偏下、想让脸更大 | 该形象的 `scale`（越大脸越大，肩越少） |
| 素材不是正方形、想选圆里取哪块 | 该形象的 `focus`（CSS `object-position`） |
| 圆太小/太大 | `layout.<画幅>.avatar.size` |
| 圆挡住字幕或内容 | 抬高 `y`（数值变小）或右移 `x`（数值变大） |

- 记住约束：**数字人右下角 + 字幕底部居中，两者不能重叠**；内容区已经按这两者让出了空间。
- 改完出静帧看：`iph still <期> 12 --ratio=16:9 --preset=<名>`（**横竖屏都要看**，两者数字人尺寸不同）。

## 想让它更"活"（可选进阶）

`remotion/src/components/TalkingAvatar.tsx` 里几个可调的量：

| 变量 | 作用 |
|---|---|
| `mouthSignal()` 的 `rate` | 音节开合频率（默认 7.6 Hz 上下漂移） |
| `amp` | 单次开合幅度 |
| `bob` | 上下浮动像素 |
| `tilt` | 左右摆动角度 |
| 光环 `pulse` 的 `1.55` | 脉冲速度 |

改完 `iph still <期> 12 --ratio=16:9` 看一帧，注意**别把幅度调大**——卡通形象一旦变形就廉价了。
