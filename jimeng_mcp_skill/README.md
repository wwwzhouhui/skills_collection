# 即梦 MCP Skill (jimeng_mcp_skill)

<div align="center">

**🎨 AI 驱动的图像和视频生成技能**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/wwwzhouhui/jimeng-mcp-server)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-purple.svg)](https://code.anthropic.com)

</div>

## 📖 概述

`jimeng_mcp_skill` 是一个为 Claude Code 设计的技能包，通过集成 [jimeng-mcp-server](https://github.com/wwwzhouhui/jimeng-mcp-server) 提供强大的 AI 图像和视频生成能力。该技能利用即梦 AI 的多模态生成引擎，让你可以通过自然语言指令直接创建高质量的视觉内容。

### ✨ 核心特性

- 🎨 **文本生成图像** - 从文本描述生成高质量图像
- 🎭 **图像智能合成** - 合并和融合多张图片
- 🎬 **文本生成视频** - 从文本提示创建短视频
- 🎞️ **图像生成视频** - 为静态图像添加动画效果

### 🎯 适用场景

- 内容创作：快速生成博客、文章的配图
- 视频制作：为视频项目创建素材
- 设计辅助：快速原型设计和概念可视化
- 教育培训：生成教学演示素材
- 社交媒体：创建吸引眼球的视觉内容

---

## 🚀 快速开始

### 前置要求

在使用此技能前，请确保已完成以下配置：

1. **安装 jimeng-mcp-server**
   ```bash
   # 克隆仓库
   git clone https://github.com/wwwzhouhui/jimeng-mcp-server.git
   cd jimeng-mcp-server
   
   # 安装依赖
   pip install -r requirements.txt
   ```

2. **配置环境变量**

   创建 `.env` 文件并配置：
   ```bash
   JIMENG_API_KEY=your_api_key_here
   JIMENG_API_URL=http://127.0.0.1:8001
   JIMENG_MODEL=jimeng-4.0
   ```

3. **启动后端服务**
   ```bash
   # 使用 Docker 启动 jimeng-free-api-all
   docker run -d \
     --name jimeng-api \
     -p 8001:8001 \
     -e JIMENG_API_KEY=your_api_key \
     ghcr.io/wwwzhouhui/jimeng-free-api-all:latest
   ```

4. **在 Claude Code 中配置 MCP**

   编辑 `~/.config/claude-code/mcp.json`：
   ```json
   {
     "mcpServers": {
       "jimeng-mcp-server": {
         "command": "python",
         "args": ["/path/to/jimeng-mcp-server/src/jimeng_mcp_server/server.py"],
         "env": {
           "JIMENG_API_KEY": "your_api_key",
           "JIMENG_API_URL": "http://127.0.0.1:8001"
         }
       }
     }
   }
   ```

### 安装技能

将此技能复制到 Claude Code 的 skills 目录：

```bash
# 方法 1: 使用 tar.gz 包
tar -xzf jimeng_mcp_skill-latest.tar.gz -C ~/.claude/skills/

# 方法 2: 直接克隆
git clone https://github.com/wwwzhouhui/jimeng-mcp-skill.git ~/.claude/skills/jimeng_mcp_skill
```

重启 Claude Code 使技能生效。

---

## 💡 使用示例

### 示例 1: 文本生成图像

**用户输入：**
```
请使用jimeng_mcp_skill帮我生成一张图：小猫和小兔子打架  使用 jimeng-3.1模型生成
```

**系统行为：**

- 自动识别为文本生成图像任务
- 调用 `text_to_image` 工具
- 使用参数：
  - `prompt`: "樱花树下的柴犬，夕阳余晖，动漫风格"
  - `width`: 1536
  - `height`: 864
  - `sample_strength`: 0.6

**返回结果：**
```
✅ 成功生成 4 张图像

📷 图像URL列表:
1. https://example.com/image1.png
2. https://example.com/image2.png
3. https://example.com/image3.png
4. https://example.com/image4.png
```

---

![image-20251115142311334](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142311334.png)

![image-20251115142336204](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142336204.png)

### 示例 2: 图像合成

**用户输入：**
```
请使用jimeng_mcp_skill 将这两张图像合成在一起:
- 图像1: https://p3-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/bab623359bd9410da0c1f07897b16fec~tplv-tb4s082cfz-resize:0:0.image?lk3s=8e790bc3&x-expires=1788961069&x-signature=cbtnyeSIcqWpngHdoYWFkCra3cA%3D
- 图像2: https://p3-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/6acf16d07c47413898aea2bdd1ad339e~tplv-tb4s082cfz-resize:0:0.image?lk3s=8e790bc3&x-expires=1788961069&x-signature=30S2i%2FvCH0eRR32CehcEaK8t5ns%3D
创建一个艺术风格的无缝融合
```

**系统行为：**
- 识别为图像合成任务
- 调用 `image_composition` 工具
- 使用参数：
  - `prompt`: "将两张图片无缝融合，保持第一张图片的艺术风格"
  - `images`: ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
  - `sample_strength`: 0.6

**返回结果：**

```
✅ 合成成功！ 使用 jimeng_mcp_skill 成功将两张图片进行了艺术风格的无缝融合！

  🎨 合成结果

  合成参数：
  - 📐 输出尺寸：1536x864 (16:9 横向)
  - 🎭 合成强度：0.6（中等，保持原图特征的同时进行融合）
  - 🖼️ 输入图片：2 张
  - ✨ 生成结果：4 个不同的合成版本

  生成的 4 张合成图片：

  1. https://p26-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/681e949c9c184045b17e334f2b51eae4~tplv-tb4s082cfz-aigc_resize_mark:0:0.png?lk3s=43402efa&x-expires=1763193600
  &x-signature=04Us2jkxE%2By28%2FiVzSgVbKT%2FeIo%3D&format=.png
  2. https://p3-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/9bf159ff3c2445ffb10204a25dce480c~tplv-tb4s082cfz-aigc_resize_mark:0:0.png?lk3s=43402efa&x-expires=1763193600&
  x-signature=6heDK7SHkjpAnMmVYW2p2XukAs4%3D&format=.png
  3. https://p3-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/5cc0dbbeb78a41aca6620beed302cffb~tplv-tb4s082cfz-aigc_resize_mark:0:0.png?lk3s=43402efa&x-expires=1763193600&
  x-signature=U90xgPtFij2ltsGvA2cf69AwwIQ%3D&format=.png
  4. https://p26-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/6462f90eb51c484da6d67eb745c5af4d~tplv-tb4s082cfz-aigc_resize_mark:0:0.png?lk3s=43402efa&x-expires=1763193600
  &x-signature=X%2BYZ5%2FrRXDBN%2Fofov%2BkLounfluU%3D&format=.png

  即梦 AI 为你生成了 4 个不同风格的合成版本，每个都以不同的方式融合了两张原始图片，创造出和谐统一的艺术效果。点击链接查看哪个版本最符合你的期望！
```

---

![image-20251115142702314](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142702314.png)

![image-20251115142736917](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142736917.png)

### 示例 3: 文本生成视频

**用户输入：**
```
请使用jimeng_mcp_skill 生成一个视频：小猫在钓鱼，阳光明媚的午后
```

**系统行为：**
- 识别为文本生成视频任务
- 调用 `text_to_video` 工具
- 使用参数：
  - `prompt`: "一只橘色小猫坐在河边，手持鱼竿专注地钓鱼，阳光明媚的午后"
  - `resolution`: "720p"

**返回结果：**
```
jimeng-mcp-server - text_to_video (MCP)(prompt: "一只可爱的橘色小猫坐在河边，手持鱼竿专注地钓鱼，阳光明媚的午后，温暖的阳光洒在水面上，微风轻拂，画面温馨惬意", resolution:
                                         "720p")
  ⎿  ✅ 成功生成 1 个视频                                                                                                                                                 

     🎬 视频URL列表:
     … +12 lines (ctrl+o to expand)

● ✅ 视频生成成功！ 使用 jimeng_mcp_skill 为你创建了"小猫在钓鱼"的视频！

  🎬 视频信息

  视频参数：
  - 📐 分辨率：720p (1280x720)
  - 🎨 场景：小猫在河边钓鱼
  - 🌤️ 氛围：阳光明媚的午后
  - ⏱️ 时长：约 3-5 秒
  - 📦 格式：MP4

  视频描述：
  一只可爱的橘色小猫坐在河边，手持鱼竿专注地钓鱼，阳光明媚的午后，温暖的阳光洒在水面上，微风轻拂，画面温馨惬意。

  观看视频：
  https://v6-artist.vlabvod.com/8c0b6d0cef156188f2421ba30e048279/69215838/video/tos/cn/tos-cn-v-148450/o80OeeDwJAeDGoIIgR1IkDCEOBMLQAHaSgtTUo/?a=4066&ch=0&cr=0&dr=0&er=0&l
  r=display_watermark_aigc&cd=0%7C0%7C0%7C0&br=6796&bt=6796&cs=0&ds=12&ft=5QYTUxhhe6BMyqlgLwVJD12Nzj&mime_type=video_mp4&qs=0&rc=ODZoNDQ0Zmk7ZGg8PDM7NEBpanJrZ3c5cjs0NzczND
  M7M0A2Yi1iNDZhNV4xNGE2LS0wYSM0MWheMmRjb2BhLS1kNC9zcw%3D%3D&btag=c0000e00008000&dy_q=1763188147&feature_id=7bed9f9dfbb915a044e5d473759ce9df&l=20251115142907E08B3618064D3A
  8100D9

  点击链接即可在浏览器中播放视频！视频展现了一个温馨惬意的场景，非常适合用于社交媒体分享或内容创作。
```

---

![image-20251115143025496](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143025496.png)

![image-20251115143113549](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143113549.png)

### 示例 4: 图像生成视频

**用户输入：**
```
请使用jimeng_mcp_skill 为这张照片添加动画效果，让它有电影感
https://p3-dreamina-sign.byteimg.com/tos-cn-i-tb4s082cfz/bab623359bd9410da0c1f07897b16fec~tplv-tb4s082cfz-resize:0:0.image?lk3s=8e790bc3&x-expires=1788961069&x-signature=cbtnyeSIcqWpngHdoYWFkCra3cA%3D
添加轻柔的运动和自然的镜头缩放
```

**系统行为：**
- 识别为图像生成视频任务
- 调用 `image_to_video` 工具
- 使用参数：
  - `prompt`: "添加轻柔的运动效果和自然的镜头缩放，营造电影感"
  - `file_paths`: ["https://example.com/photo.jpg"]
  - `resolution`: "720p"

**返回结果：**
```
✅ 成功从 1 张图像生成 1 个视频                                                                                                                                      

     🎬 视频URL列表:
     … +12 lines (ctrl+o to expand)

● ✅ 动画视频生成成功！ 使用 jimeng_mcp_skill 成功为你的照片添加了电影感的动画效果！

  🎬 视频信息

  动画参数：
  - 📐 分辨率：720p (1280x720)
  - 🎥 效果：轻柔的运动 + 自然的镜头缩放
  - 🎭 风格：电影感，流畅优雅
  - ⏱️ 时长：约 3-5 秒
  - 📦 格式：MP4

  动画描述：
  为静态照片添加了专业的运动效果和镜头缩放，营造出电影般的视觉体验，画面流畅优雅。

  观看动画视频：
  https://v9-artist.vlabvod.com/de4b56757300cd0f8cc1a9ad504004e7/6921598c/video/tos/cn/tos-cn-v-148450/oIA5ahNODinkfEp8bjAA8EMS2eRWQBvDCAE3eM/?a=4066&ch=0&cr=0&dr=0&er=0&l
  r=display_watermark_aigc&cd=0%7C0%7C0%7C0&br=6909&bt=6909&cs=0&ds=12&ft=5QYTUxhhe6BMyqXJLwVJD12Nzj&mime_type=video_mp4&qs=0&rc=OWY8N2ZnM2g3Njg2OGU4NEBpM2U1aW05cnc0NzczND
  M7M0BiMTEvYC0zX18xMi9jMTFgYSM2YnBiMmRzcWBhLS1kNC9zcw%3D%3D&btag=c0000e00008000&dy_q=1763188487&feature_id=7bed9f9dfbb915a044e5d473759ce9df&l=202511151434466D5091F99E5924
  7F9CB3

  点击链接即可在浏览器中播放动画视频！静态照片现在变得生动起来了，带有专业的电影感效果。
```

---

![image-20251115143553127](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143553127.png)

![image-20251115143620819](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143620819.png)

## 🔧 高级用法

### 自定义参数

你可以在对话中指定更详细的参数：

**指定分辨率：**
```
生成一张 1920x1080 的图片：未来城市夜景
```

**调整创意度：**
```
生成图片，创意度要高一些：抽象的太空场景
# sample_strength 会自动设置为 0.7-0.8
```

**使用负面提示词：**
```
生成图片：可爱的小狗，但不要有猫
# 会自动添加 negative_prompt: "猫"
```

### 批量生成

```
帮我生成3张不同风格的图片：
1. 写实风格的山水画
2. 卡通风格的城市街景
3. 抽象艺术风格的宇宙
```

系统会依次处理每个请求并返回所有结果。

### 链式操作

```
1. 先生成一张图片：森林中的小屋
2. 然后为这张图片添加动画效果
```

系统会：
1. 使用 `text_to_image` 生成图片
2. 使用生成的图片 URL 调用 `image_to_video`
3. 返回最终的动画视频

---

## 📚 API 参考

### 文本生成图像 (text_to_image)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 图像描述 |
| `width` | int | ❌ | 1536 | 图像宽度 (512/768/1024/1536/2048) |
| `height` | int | ❌ | 864 | 图像高度 (512/768/864/1024/2048) |
| `sample_strength` | float | ❌ | 0.5 | 采样强度 (0.0-1.0) |
| `negative_prompt` | string | ❌ | "" | 负面提示词 |

### 图像合成 (image_composition)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 合成描述 |
| `images` | array | ✅ | - | 图片URL数组 (2-5张) |
| `width` | int | ❌ | 1536 | 输出宽度 |
| `height` | int | ❌ | 864 | 输出高度 |
| `sample_strength` | float | ❌ | 0.5 | 合成强度 |

### 文本生成视频 (text_to_video)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 视频场景描述 |
| `resolution` | string | ❌ | "720p" | 分辨率 (480p/720p/1080p) |
| `width` | int | ❌ | 1280 | 视频宽度 |
| `height` | int | ❌ | 720 | 视频高度 |

### 图像生成视频 (image_to_video)

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `prompt` | string | ✅ | - | 动画效果描述 |
| `file_paths` | array | ✅ | - | 图片URL数组 |
| `resolution` | string | ❌ | "720p" | 输出分辨率 |
| `width` | int | ❌ | 1280 | 视频宽度 |
| `height` | int | ❌ | 720 | 视频高度 |

---

## 🛠️ 故障排除

### 常见问题

**Q: 提示 "Unknown skill: jimeng_mcp_skill"**

A: 重启 Claude Code 使技能生效：
```bash
# 重启 Claude Code CLI
claude-code restart
```

**Q: 生成失败，提示连接错误**

A: 检查后端服务是否运行：
```bash
# 检查 Docker 容器
docker ps | grep jimeng

# 检查服务健康状态
curl http://127.0.0.1:8001/health
```

**Q: 提示 "Invalid API key"**

A: 验证 API key 配置：
1. 登录 https://jimeng.jianying.com/
2. 打开浏览器开发者工具 → Application → Cookies
3. 复制 `sessionid` 的值
4. 更新 `.env` 文件中的 `JIMENG_API_KEY`

**Q: 生成速度慢或超时**

A: 这是正常现象：
- 图片生成：通常 5-15 秒
- 视频生成：通常 30-60 秒
- 可以降低分辨率以加快速度

**Q: 生成质量不理想**

A: 优化提示词：
- 使用更具体、详细的描述
- 添加艺术风格、光照、氛围等细节
- 调整 `sample_strength` 参数
- 使用负面提示词排除不需要的元素

---

## 📂 项目结构

```
jimeng_mcp_skill/
├── SKILL.md              # 技能定义文件（Claude Code 核心）
├── README.md             # 本文档
├── assets/               # 资源文件
│   └── examples/         # 示例图片和视频
├── references/           # 参考文档
│   ├── setup_guide.md    # 详细安装配置指南
│   └── api_reference.md  # 完整 API 文档
└── scripts/              # 辅助脚本
    └── test_connection.py # 测试 MCP 连接
```

---

## 🔗 相关资源

- **jimeng-mcp-server**: https://github.com/wwwzhouhui/jimeng-mcp-server
- **jimeng-free-api-all**: https://github.com/wwwzhouhui/jimeng-free-api-all
- **即梦官网**: https://jimeng.jianying.com/
- **Claude Code 文档**: https://code.anthropic.com/docs

---

## 📝 更新日志

### v1.0.0 (2025-01-15)
- ✅ 初始版本发布
- ✅ 支持文本生成图像
- ✅ 支持图像合成
- ✅ 支持文本生成视频
- ✅ 支持图像生成视频
- ✅ 完整的文档和示例

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎贡献！请随时提交 Issue 或 Pull Request。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 💬 联系方式

- GitHub: [@wwwzhouhui](https://github.com/wwwzhouhui)
- Email: 75271002@qq.com

---

<div align="center">

**Made with ❤️ by the Jimeng MCP Community**

</div>
