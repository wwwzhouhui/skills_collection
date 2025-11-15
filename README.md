# Claude Code Skills Collection

本项目是个人开发的 Claude Code Skills 集合，提供实用的技能工具，助力提升开发效率和内容创作。

分享一些好用的 Claude Code Skills，自用、学习两相宜，适用于 Claude Code v2.0 及以上版本。

## 📖 什么是 Claude Skills

Claude Skills 是 Claude Code 的扩展能力，通过编写技能文档（Skill.md），可以让 Claude 在特定场景下自动激活相应的专业知识和能力。

## 使用说明

### 1. 安装 Skills

将 Skill 文件夹复制到你的 Claude Code Skills 目录：

```bash
# Linux/Mac
cp -r skill-name ~/.claude/skills/

# Windows
xcopy /E /I skill-name %USERPROFILE%\.claude\skills\skill-name
```

如果是windows平台可以手工复制到 C:\Users\xxx\.claude\skills

![image-20251110164730420](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110164730420.png)

![image-20251110165041134](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110165041134.png)

  我们检查一下这个skills是否可以使用。

### 2. 验证安装

在 Claude Code 中输入相关关键词，Claude 会自动激活对应的 Skill。

![image-20251112173259755](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112173259755.png)

### 3. 开始使用

直接与 Claude 对话，提出相关需求即可：

```
"请基于上面的数据帮我生成图表统计，比如饼状图、柱状图、条形图等。请在原来生成的2025年101中学其中考试统计表20251112.xlsx表中生成"
```

![image-20251112171230648](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112171230648.png)

## Skills 清单

| Skill 名称              | 功能说明                                                     | 技术栈                               | 更新时间       | 作者       | 版本  |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------ | -------------- | ---------- | ----- |
| excel-report-generator  | 自动化 Excel 报表生成器，支持从 CSV、DataFrame、数据库生成专业 Excel 报表，包含图表、样式、模板填充等高级功能 | Python、pandas、openpyxl、xlsxwriter | 2025年1月12日  | wwwzhouhui | 2.0.0 |
| xiaohuihui-tech-article | 专为技术实战教程设计的公众号文章生成器，遵循小灰灰公众号写作规范，自动生成包含前言、项目介绍、部署实战、总结的完整技术文章 | Markdown、模板生成                   | 2025年11月10日 | wwwzhouhui | 2.0.0 |
| jimeng_mcp_skill        | AI 图像和视频生成技能，通过 jimeng-mcp-server 实现文生图、图像合成、文生视频、图生视频四大核心能力 | MCP、Python、Docker、即梦 AI         | 2025年11月15日 | wwwzhouhui | 1.0.0 |

## Skill 功能详解

### 📊 Excel Report Generator

**核心功能：**

- ✅ 从多种数据源生成 Excel（CSV、DataFrame、数据库）
- ✅ 创建专业图表（柱状图、折线图、饼图等）
- ✅ 应用样式和格式化
- ✅ 模板填充和批量生成
- ✅ 条件格式和数据验证
- ✅ 公式和自动计算

**适用场景：**

- 数据分析报表
- 业务报告自动化
- 系统数据导出
- 模板批量处理

**示例用法：**

```
请基于上面的数据帮我生成图表统计，比如饼状图、柱状图、条形图等
```

![image-20251112171422425](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112171422425.png)

---

### 📝 XiaoHuiHui Tech Article

**核心功能：**

- ✅ 标准四段式结构（前言→项目介绍→部署实战→总结）
- ✅ 三段式开头（问题引入+解决方案+实战预告）
- ✅ 详细部署步骤（环境→安装→配置→实现→测试）
- ✅ 单段长句总结（300-500字）
- ✅ 口语化技术表达
- ✅ 完整资源附加（GitHub+体验地址+网盘）

**文章结构：**

- **第1章**：前言（三段式，约300字）
- **第2章**：项目介绍（约500字）
- **第3章**：部署实战（约1500-2000字）
- **第4章**：总结（单段300-500字）
- **第5章**：附加资源

**示例用法：**

```
请认真分析https://github.com/wwwzhouhui/in_animation开源项目，请帮我使用xiaohuihui-tech-article skill基于这个开源项目生成一个公众号文章。输出"20251101in_animation公众号文章.md"
```

![image-20251110175146630](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110175146630.png)

​     ![image-20251110175215254](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110175215254.png)

---

### 🎨 Jimeng MCP Skill

**核心功能：**

- ✅ 文本生成图像（text-to-image）
- ✅ 图像合成（image composition）
- ✅ 文本生成视频（text-to-video）
- ✅ 图像生成视频（image-to-video）
- ✅ 支持多种分辨率和宽高比
- ✅ 可调节采样强度控制创意性

**适用场景：**

- AI 内容创作（博客配图、短视频制作）
- 产品宣传素材生成
- UI 原型快速生成
- 创意头脑风暴可视化

**前置条件：**

1. jimeng-free-api-all Docker 容器运行
2. 配置 JIMENG_API_KEY 环境变量
3. jimeng-mcp-server 正确安装

#### 示例 1: 文本生成图像

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

![image-20251115142311334](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142311334.png.png)

![image-20251115142336204](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142336204.png.png)

#### 示例 2: 图像合成

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

![image-20251115142702314](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142702314.png.png)

![image-20251115142736917](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115142736917.png.png)

#### 示例 3: 文本生成视频

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

![image-20251115143025496](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143025496.png.png)

![image-20251115143113549](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143113549.png.png)

#### 示例 4: 图像生成视频

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

![image-20251115143553127](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143553127.png.png)

![image-20251115143620819](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115143620819.png.png)

**技术特点：**

- 基于 MCP（模型上下文协议）标准
- 支持 stdio、SSE、HTTP 三种运行模式
- 完全免费（每日 66 积分）
- 响应时间：图像 10-20秒，视频 30-60秒

## 更新说明

### 2025年11月15日 - version 0.0.3

- ✅ 新增 jimeng_mcp_skill Skill
- ✅ 支持 AI 图像和视频生成
- ✅ 集成即梦 AI 多模态能力

### 2025年1月12日 - version 0.0.2

- ✅ 新增 excel-report-generator Skill
- ✅ 支持数据分析报表生成
- ✅ 支持图表创建和样式应用

### 2025年11月10日 - version 0.0.1

- ✅ 新增 xiaohuihui-tech-article Skill
- ✅ 实现标准四段式结构
- ✅ 支持口语化技术写作

## 技术文档地址（飞书）

https://aqma351r01f.feishu.cn/wiki/HF5FwMDQkiHoCokvbQAcZLu3nAg?table=tbleOWb4WgXcxiHK&view=vewGwwbpzl

![image-20241115093319205](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20241115093319205.png)

## 开发指南

### 创建新的 Skill

1. 在项目根目录创建新的 Skill 文件夹
2. 创建 `Skill.md` 文件，定义 Skill 的元数据和功能
3. 添加示例代码和文档
4. 测试 Skill 在 Claude Code 中的表现

**Skill.md 基本结构：**

```markdown
---
name: your-skill-name
description: Skill 的简短描述
version: 1.0.0
---

# Your Skill Name

详细的功能说明和使用文档...
```

### 贡献 Skills

欢迎提交你的 Claude Code Skills：

1. Fork 本项目
2. 创建你的 Skill 分支 (`git checkout -b feature/new-skill`)
3. 提交你的更改 (`git commit -am 'Add new skill'`)
4. 推送到分支 (`git push origin feature/new-skill`)
5. 创建 Pull Request

## 🎉 致谢

感谢以下项目对本项目提供的灵感和支持：

1. [Claude Code](https://claude.ai/code)

   Anthropic 官方推出的 AI 编程助手，提供强大的代码理解和生成能力。

2. [pandas](https://github.com/pandas-dev/pandas)

   强大的 Python 数据分析库，excel-report-generator 的核心依赖。

3. [openpyxl](https://github.com/theorchard/openpyxl)

   用于读写 Excel 2010 xlsx/xlsm 文件的 Python 库。

4. [jimeng-mcp-server](https://github.com/wwwzhouhui/jimeng-mcp-server)

   基于 MCP 协议的即梦 AI 集成服务器，jimeng_mcp_skill 的核心依赖。

5. [即梦 AI](https://jimeng.jianying.com/)

   字节跳动旗下的多模态 AI 生成平台，提供图像和视频生成能力。

## 问题反馈

如有问题，请在 GitHub Issue 中提交，在提交问题之前，请先查阅以往的 issue 是否能解决你的问题。

## 常见问题汇总

<details>
<summary>如何知道 Skill 是否已激活？</summary>
当 Claude 识别到相关关键词时，会自动激活对应的 Skill。你可以通过 Claude 的回复内容判断，如果回复包含 Skill 中定义的特定结构或风格，说明已成功激活。
</details>


<details>
<summary>Skill 不生效怎么办？</summary>
1. 确认 Skill 文件夹位置正确（~/.claude/skills/）<br>
2. 检查 Skill.md 文件格式是否正确<br>
3. 尝试重启 Claude Code<br>
4. 使用更明确的触发关键词
</details>


<details>
<summary>如何自定义 Skill？</summary>
你可以直接编辑 Skill.md 文件，修改功能说明、触发关键词、输出格式等。修改后 Claude 会在下次激活时使用新的配置。
</details>


<details>
<summary>Skill 冲突怎么办？</summary>
如果多个 Skill 的触发关键词重叠，可以：<br>
1. 使用更具体的关键词<br>
2. 在对话中明确指定要使用的 Skill 名称<br>
3. 调整 Skill.md 中的描述和触发条件
</details>


<details>
<summary>Excel 生成的文件打不开？</summary>
1. 确认安装了正确版本的依赖（pandas、openpyxl）<br>
2. 检查文件扩展名是否为 .xlsx<br>
3. 验证数据格式是否正确<br>
4. 查看错误日志排查具体问题
</details>


<details>
<summary>技术文章风格不符合预期？</summary>
1. 在提示中明确指定"使用小灰灰公众号风格"<br>
2. 提供更详细的项目信息和技术栈<br>
3. 可以要求 Claude 调整特定段落的风格<br>
4. 参考 Skill.md 中的标准模板
</details>

<details>
<summary>jimeng 图像/视频生成失败？</summary>
1. 确认 jimeng-free-api-all Docker 容器正在运行<br>
2. 检查 JIMENG_API_KEY 是否正确配置<br>
3. 验证后端服务可访问：curl http://localhost:8001<br>
4. 确保有足够的 API 积分（免费层每天 66 积分）<br>
5. 图像生成需要 10-20 秒，视频生成需要 30-60 秒，请耐心等待
</details>

<details>
<summary>如何获取即梦 API 密钥？</summary>
1. 访问 https://jimeng.jianying.com/ 并登录<br>
2. 按 F12 打开浏览器开发者工具<br>
3. 前往 Application > Cookies<br>
4. 找到并复制 sessionid 值<br>
5. 将此值配置为 JIMENG_API_KEY 环境变量
</details>


## 技术交流群

欢迎加入技术交流群，分享你的 Skills 和使用心得：

![微信图片_20251113205305_66_292](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/%25E5%25BE%25AE%25E4%25BF%25A1%25E5%259B%25BE%25E7%2589%2587_20251113205305_66_292.jpg)

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

支付宝

![image-20250914152823776](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152823776.png)

微信

![image-20250914152855543](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

## 📊 项目统计

### 技能统计

- **总技能数**: 3
- **自动化工具**: 1 (excel-report-generator)
- **内容生成**: 1 (xiaohuihui-tech-article)
- **AI 多模态**: 1 (jimeng_mcp_skill)

### 开发语言

- Python: 2
- Markdown: 1
- MCP: 1

### 维护状态

- ✅ 活跃维护中
- 🔄 持续更新
- 📚 文档完善

## 路线图

### 计划中的 Skills

- [ ] **code-reviewer**: 代码审查助手
- [ ] **api-doc-generator**: API 文档生成器
- [ ] **test-case-generator**: 测试用例生成器
- [ ] **database-designer**: 数据库设计助手
- [ ] **deployment-helper**: 部署配置助手

### 优化计划

- [ ] 添加更多 Excel 报表模板
- [ ] 扩展技术文章支持的平台风格
- [ ] 提供交互式配置工具
- [ ] 增加中英文双语支持

## License

MIT License

## Star History

如果觉得项目不错，欢迎点个 Star ⭐

![claude-skills](https://api.star-history.com/svg?repos=yourusername/claude-skills&type=Date)

---

**开始使用**: 选择一个 Skill，按照使用说明安装，然后在 Claude Code 中尽情使用吧！