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
| mp-cover-generator      | 公众号封面生成器，根据主题和标题生成现代风格的公众号封面图，支持描边卡通字体、垂直居中布局，可输出 HTML 和高清图片（PNG/JPG），使用 Playwright 实现完整页面截图 | MCP、HTML/CSS、Node.js、Playwright、即梦 AI | 2025年11月15日 | wwwzhouhui | 3.1.1 |
| siliconflow-api-skills  | 硅基流动（SiliconFlow）云服务平台文档技能，提供大语言模型 API 调用、图片生成、向量模型、Chat Completions API、Stream 模式等完整文档和最佳实践 | API、Python、REST、LLM               | 2025年11月19日 | wwwzhouhui | 1.0.0 |
| dify-dsl-generator      | 专业的 Dify 工作流 DSL/YML 文件生成器，根据用户业务需求自动生成完整的 Dify 工作流配置文件，支持各种节点类型和复杂工作流逻辑 | YAML、Dify DSL、工作流设计           | 2025年11月22日 | wwwzhouhui | 1.0.0 |
| xiaohuihui-dify-tech-article | 专为 Dify 工作流案例分享设计的公众号文章生成器，遵循小灰灰公众号写作规范，自动生成包含前言、工作流制作、总结的完整 Dify 案例文章 | Markdown、Dify、腾讯云 COS           | 2025年11月22日 | wwwzhouhui | 1.0.0 |
| ppt-generator-skill     | 基于商务模板的专业 PPT 生成器，支持固定 25 页结构（封面→目录→4章节→结束），提供暖色调、商务简约、莫兰迪色系三种主题风格，支持 JSON 配置和代码调用 | Python、python-pptx                 | 2025年12月4日  | o3sky      | 1.0.0 |

## Skill 功能详解

### 📊 PPT Generator (PPT 生成器)

**核心功能：**

- ✅ 固定 25 页专业商务 PPT 结构（封面→目录→4章节→结束→字体说明→版权）
- ✅ 三种主题风格：暖色调、商务简约（默认）、莫兰迪色系
- ✅ 每章节 5 页（1 个过渡页 + 4 个内容页）
- ✅ 支持 JSON 配置文件和代码调用两种方式
- ✅ 专业设计风格：商务简约、暖色调装饰、莫兰迪色系
- ✅ 规范化布局：统一页面布局和文本规范

**PPT 结构（25 页）：**

1. **第1页**：封面 - 主标题、副标题、年份
2. **第2页**：目录 - 4 个章节列表
3. **第3-7页**：第一章节（1 个过渡页 + 4 个内容页）
4. **第8-12页**：第二章节（1 个过渡页 + 4 个内容页）
5. **第13-17页**：第三章节（1 个过渡页 + 4 个内容页）
6. **第18-22页**：第四章节（1 个过渡页 + 4 个内容页）
7. **第23页**：结束页 - "谢谢观看"
8. **第24页**：字体说明
9. **第25页**：版权声明

**适用场景：**

- 年度工作总结
- 项目汇报
- 工作述职
- 产品发布
- 季度/月度报告

**使用方式：**

```bash
# 方法1：直接运行生成示例 PPT
python3 ppt_generator.py

# 方法2：使用 JSON 配置文件
python3 ppt_generator.py my_ppt_config.json
```

**JSON 配置示例：**

```json
{
  "title": "2025年度工作总结",
  "subtitle": "工作总结 / 汇报",
  "year": "2025",
  "theme": "商务简约",
  "filename": "2025年度工作总结.pptx",
  "chapters": [
    {
      "title": "年度工作概况",
      "description": "介绍全年工作整体情况",
      "pages": [
        {
          "title": "工作概述",
          "content": [
            {"title": "项目数量", "description": "完成 15 个重点项目"},
            {"title": "团队规模", "description": "团队扩展至 20 人"}
          ]
        }
      ]
    }
  ]
}
```

**代码调用示例：**

```python
from ppt_generator import PPTGenerator

# 创建生成器实例
generator = PPTGenerator(theme="商务简约")

# 配置 PPT 内容
config = {
    "title": "2025年度总结",
    "subtitle": "工作总结 / 汇报",
    "year": "2025",
    "chapters": [...]  # 章节配置
}

# 生成并保存 PPT
generator.generate_full_ppt(config)
generator.save("output.pptx")
```

**主题风格：**

| 主题 | 特点 | 适用场景 |
|------|------|----------|
| 暖色调 | 活泼热情 | 创意类汇报 |
| 商务简约 | 专业稳重（默认） | 工作总结 |
| 莫兰迪色系 | 优雅柔和 | 品牌展示 |

**技术要求：**

- Python 3.7+
- 依赖库：python-pptx (`pip install python-pptx`)
- 推荐字体：阿里巴巴普惠体 2.0、HarmonyOS Sans SC、MiSans Heavy、思源宋体 CN

**配置要点：**

- 4 个章节必填：每个 PPT 必须有 4 个主要章节
- 每章节 4 页内容：不足自动补充占位页
- 每页最多 4 个要点：采用 2x2 布局
- 文本简洁：描述控制在 50-100 字

---

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

**技术特点:**

- 基于 MCP(模型上下文协议)标准
- 支持 stdio、SSE、HTTP 三种运行模式
- 完全免费(每日 66 积分)
- 响应时间:图像 10-20秒,视频 30-60秒

---

### 🎨 MP Cover Generator (公众号封面生成器)

**核心功能:**

- ✅ 根据主题自动生成 3D 插画风格封面底图
- ✅ 智能叠加文字层（日期、标题、作者）
- ✅ 描边卡通字体效果（鲜艳色彩 + 多层描边）
- ✅ 垂直居中布局，视觉平衡完美
- ✅ 双格式输出：HTML + 高清图片（PNG/JPG）
- ✅ 完整页面截图（5120x2916，2x 像素密度）
- ✅ 可爱圆润的卡通 3D 风格（类似皮克斯）
- ✅ 返回 4 张不同风格供选择

**适用场景:**

- 公众号文章封面图制作
- 社交媒体横幅图生成
- 技术博客头图创作
- 宣传海报快速设计

**前置条件:**

1. jimeng-free-api-all Docker 容器运行
2. 配置 JIMENG_API_KEY 环境变量
3. jimeng-mcp-server 正确安装
4. Node.js 16+ 环境（图片输出功能）
5. Playwright 已安装（自动安装）

**生成流程:**

1. **收集信息**：主题关键词、标题文字
2. **生成底图**：调用 jimeng-mcp-server text_to_image 工具
3. **构建 HTML**：叠加文字层、响应式样式、描边效果
4. **输出文件**：保存为独立 HTML 文件
5. **转换图片**：使用 Playwright 自动转换为 PNG/JPG

**使用示例:**

```
请使用 mp-cover-generator skill 生成一个 MCP案例分享 claude调用AI生图视频教程 介绍的文章的公众号封面
```

![image-20251115183718247](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115183718247.png.png)

![image-20251115183746503](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115183746503.png.png)

**生成参数:**

- 日期：自动获取当前星期和日期（格式：Fri. 11.15）
- 作者：固定为"O3sky"
- 模型：推荐使用 jimeng-3.1
- 尺寸：1536x864（16:9 比例）
- 采样强度：0.6（平衡创意性和真实性）
- 字号：5vw（大字体，响应式）
- 位置：垂直居中（`top: 50%; transform: translateY(-50%);`）

**视觉风格:**

- 主题风格：可爱、圆润、简洁的 3D 插画
- 质感：类似皮克斯动画或黏土定格动画
- 色彩：和谐明快，低饱和度渐变背景
- 构图：右图左文，主体位于右侧 30-40% 区域
- 留白：左侧 60-70% 干净留白供文字显示
- 文字样式：
  - **主标题**：红色（#FF3333）+ 白色描边，8 方向文字阴影
  - **副标题**：橙黄色（#FFB84D）+ 深棕色描边，单行不折行
  - **立体感**：多层阴影模拟描边 + 额外立体阴影

**禁止元素:**

- ❌ 任何形式的文字、数字、符号
- ❌ 霓虹/赛博朋克风格
- ❌ 暗黑深沉风格
- ❌ 抽象科技线条
- ❌ 玻璃质感或写实渲染

**技术特点:**

- 基于 jimeng-mcp-server MCP 协议
- 返回 4 张可选图片，提供更多选择
- Playwright 驱动，高性能截图
- 自动检测内容高度并调整视口
- 完整页面截图，无截断
- 响应式设计，支持多设备显示
- 完全本地化处理，无需上传

**输出对比:**

| 格式 | 文件大小 | 分辨率 | 质量 | 用途 |
|------|---------|--------|------|------|
| HTML | 4.5 KB | 响应式 | 最佳 | 网页预览、编辑 |
| PNG | 4.10 MB | 5120x2916 | 无损 | 高质量发布、打印 |
| JPEG | 1.44 MB | 5120x2916 | 优秀 | 一般发布、节省空间 |

**版本历史:**

- v3.1.1（2025-11-15）：新增描边卡通字体、垂直居中布局、完整页面截图
- v3.1.0（2025-11-15）：新增 HTML 转图片功能，集成 Playwright
- v3.0.0（2025-11-15）：从 jimeng-image-generator 迁移到 jimeng-mcp-server
- v2.0.0：初始版本，使用 jimeng-image-generator

---

### 🤖 Dify DSL Generator

**核心功能：**

- ✅ 自动生成完整的 Dify 工作流 DSL/YML 文件
- ✅ 支持多种节点类型（start、llm、answer、code、http-request、if-else、tool 等）
- ✅ 智能生成节点间的连接关系（edges）
- ✅ 自动配置模型参数和提示词
- ✅ 识别并配置所需的 Dify 插件依赖
- ✅ 严格遵循 Dify 0.3.0 版本的 DSL 规范
- ✅ 基于 86+ 真实工作流案例深度学习

**适用场景：**

- 快速构建 Dify 工作流配置文件
- 批量生成工作流模板
- 学习 Dify DSL 文件结构
- 自动化工作流开发

**知识库覆盖：**

- App 配置（mode、icon、描述等）
- Dependencies 依赖管理
- 各类节点详解（LLM、Code、HTTP、If-Else、Tool、Variable Aggregator、Parameter Extractor）
- Edges 连接规则
- Position 坐标布局
- 变量引用格式

**示例用法：**

```
生成一个 Dify 工作流用于图片 OCR 识别:
- 功能: 上传图片并识别文字
- 输入: 图片文件
- 处理: 使用 LLM 视觉能力进行 OCR
- 输出: 识别到的文字内容
```

![image-20251122214416059](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251122214416059.png)

生成的dsl导入dify 平台

![image-20251122214446776](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251122214446776.png)

**技术特点：**

- 完整 DSL 结构生成（app + dependencies + workflow）
- 智能节点 ID 生成（时间戳格式）
- 合理的节点布局坐标
- 支持复杂工作流逻辑（分支、循环、聚合）
- 提供常用提示词模板（Text-to-SQL、数据提取、HTML 生成）

---

### 📝 XiaoHuiHui Dify Tech Article

**核心功能：**

- ✅ Dify 专属三段式结构（前言 → 工作流制作 → 总结）
- ✅ 工作流节点详细配置说明
- ✅ 插件安装和授权步骤图文教程
- ✅ MCP Server 部署集成指南
- ✅ 优先展示工作流效果
- ✅ 口语化技术表达（"话不多说"、"手把手搭建"）
- ✅ 魔搭社区免费模型推荐
- ✅ 自动生成配图并上传腾讯云 COS 图床

**文章结构：**

- **前言**（300-400字）：技术背景 + 问题引入 + 解决方案展示
- **工作流制作**（1500-2500字）：前置准备 + 节点配置 + 测试验证
- **总结**（单段300-400字）：完整流程回顾 + 核心价值 + 扩展场景

**配图系统：**

- 工作流全局图（1张）
- 节点配置截图（6-10张）
- 插件安装截图（2-3张）
- 效果演示图（2-3张）
- 代码配置图（1-2张）
- 总计要求 >= 10 张实际截图

**示例用法：**

```
用小灰灰公众号风格写一篇 Dify 文生视频工作流的案例分享:
- 功能: 调用即梦AI实现文生视频
- 涉及插件: Agent策略插件
- 核心节点: LLM、Agent、代码执行
- 技术栈: MCP、即梦API
```

**质量标准：**

- 总字数 > 1800字（优秀 > 2500字）
- 标题格式：`dify案例分享-[功能名称]`
- 工作流截图 >= 10个（优秀 >= 15个）
- 节点配置说明 >= 5个
- 代码块 >= 3个
- 总结单段 300-400字，禁止分段
- 固定结束语："今天的分享就到这里结束了,我们下一篇文章见。"

**技术特点：**

- 遵循小灰灰公众号写作规范
- 专注 Dify 工作流案例分享
- 包含完整的插件安装教程
- 支持 MCP Server 集成说明
- 提供腾讯云 COS 图床上传脚本
- 真实图片 URL，无占位符

---

### 🌐 SiliconFlow API Skills

**核心功能：**

- ✅ 大语言模型 API 调用指南
- ✅ Chat Completions API 完整文档
- ✅ Stream 流式输出模式支持
- ✅ 图片生成 API 使用说明
- ✅ 向量模型/Embedding API 文档
- ✅ 模型列表和参数配置
- ✅ 最佳实践和代码示例

**适用场景：**

- 在 Claude Code 中调用硅基流动 API
- 开发基于 SiliconFlow 的 AI 应用
- 学习大语言模型 API 调用方式
- 调试和优化 API 调用代码
- 了解 SiliconFlow 平台功能特性

**参考文档：**

- `api_reference.md` - API 参考文档
- `deployment.md` - 部署文档
- `faqs.md` - 常见问题
- `features.md` - 功能特性
- `models.md` - 模型列表
- `userguide.md` - 用户指南
- `use_cases.md` - 使用案例

**示例用法：**

```
请帮我使用siliconflow-api-skills 这个skill技能包生成调用硅基流动的API 实现文本生成的模型接口，使用python 代码实现，
使用deepseek-ai/DeepSeek-V3.2-Exp 模型
```

![image-20251119171818824](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251119171818824.png)

接下来AI 获取这个技能包api_reference.md 生成接口代码

![image-20251119165401648](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251119165401648.png)

我们查看生成的接口代码

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硅基流动（SiliconFlow）API 文本生成接口
使用 DeepSeek-V3.2-Exp 模型

基于 SiliconFlow 技能包文档生成
API 文档: https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions
"""

import os
from openai import OpenAI

# ============================================================
# 配置部分
# ============================================================

# API 配置
API_KEY = os.getenv("SILICONFLOW_API_KEY", "YOUR_API_KEY")  # 从环境变量获取或直接填写
BASE_URL = "https://api.siliconflow.cn/v1"
MODEL = "deepseek-ai/DeepSeek-V3.2-Exp"  # 使用 DeepSeek-V3.2-Exp 模型

# 初始化客户端
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)


# ============================================================
# 方式一：普通请求（非流式）
# ============================================================

def chat_completion(
    messages: list,
    model: str = MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    top_p: float = 0.7
) -> str:
    """
    普通对话请求（非流式）

    Args:
        messages: 对话消息列表
        model: 模型名称
        temperature: 温度参数，控制随机性 (0-1)
        max_tokens: 最大生成 token 数
        top_p: 核采样参数

    Returns:
        生成的文本内容
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=False
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"请求错误: {e}")
        raise


# ============================================================
# 方式二：流式请求（实时输出）
# ============================================================

def chat_completion_stream(
    messages: list,
    model: str = MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    top_p: float = 0.7
):
    """
    流式对话请求

    Args:
        messages: 对话消息列表
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大生成 token 数
        top_p: 核采样参数

    Yields:
        生成的文本片段
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        print(f"请求错误: {e}")
        raise


# ============================================================
# 方式三：使用 requests 库直接调用 API
# ============================================================

def chat_completion_requests(
    messages: list,
    model: str = MODEL,
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 2048
):
    """
    使用 requests 库直接调用 API

    Args:
        messages: 对话消息列表
        model: 模型名称
        stream: 是否启用流式输出
        temperature: 温度参数
        max_tokens: 最大生成 token 数

    Returns:
        生成的文本内容或流式响应
    """
    import requests

    url = f"{BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream
    }

    try:
        if stream:
            # 流式请求：payload 和 request 都需要设置 stream
            response = requests.post(url, headers=headers, json=payload, stream=True)
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data != '[DONE]':
                            import json
                            chunk = json.loads(data)
                            if chunk['choices'][0]['delta'].get('content'):
                                yield chunk['choices'][0]['delta']['content']
        else:
            # 非流式请求
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        raise


# ============================================================
# 高级功能：多轮对话
# ============================================================

class ChatSession:
    """多轮对话会话管理"""

    def __init__(self, system_prompt: str = None, model: str = MODEL):
        """
        初始化对话会话

        Args:
            system_prompt: 系统提示词
            model: 模型名称
        """
        self.model = model
        self.messages = []

        if system_prompt:
            self.messages.append({
                "role": "system",
                "content": system_prompt
            })

    def chat(self, user_input: str, stream: bool = False, **kwargs):
        """
        发送消息并获取回复

        Args:
            user_input: 用户输入
            stream: 是否使用流式输出
            **kwargs: 其他参数

        Returns:
            助手的回复
        """
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_input
        })

        if stream:
            # 流式输出
            full_response = ""
            for chunk in chat_completion_stream(self.messages, model=self.model, **kwargs):
                print(chunk, end="", flush=True)
                full_response += chunk
            print()  # 换行

            # 保存助手回复
            self.messages.append({
                "role": "assistant",
                "content": full_response
            })

            return full_response
        else:
            # 普通输出
            response = chat_completion(self.messages, model=self.model, **kwargs)

            # 保存助手回复
            self.messages.append({
                "role": "assistant",
                "content": response
            })

            return response

    def clear(self):
        """清空对话历史（保留系统提示词）"""
        if self.messages and self.messages[0]["role"] == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []

    def get_history(self):
        """获取对话历史"""
        return self.messages.copy()


# ============================================================
# 使用示例
# ============================================================

def main():
    """主函数 - 演示各种使用方式"""

    print("=" * 60)
    print("硅基流动 API 文本生成示例")
    print(f"模型: {MODEL}")
    print("=" * 60)

    # 示例消息
    messages = [
        {
            "role": "system",
            "content": "你是一个有帮助的 AI 助手。"
        },
        {
            "role": "user",
            "content": "请用简洁的语言解释什么是机器学习？"
        }
    ]

    # --------------------------------------------------------
    # 示例 1: 普通请求
    # --------------------------------------------------------
    print("\n【示例 1】普通请求（非流式）:")
    print("-" * 40)

    try:
        response = chat_completion(messages)
        print(response)
    except Exception as e:
        print(f"错误: {e}")

    # --------------------------------------------------------
    # 示例 2: 流式请求
    # --------------------------------------------------------
    print("\n【示例 2】流式请求:")
    print("-" * 40)

    try:
        for chunk in chat_completion_stream(messages):
            print(chunk, end="", flush=True)
        print()  # 换行
    except Exception as e:
        print(f"错误: {e}")

    # --------------------------------------------------------
    # 示例 3: 多轮对话
    # --------------------------------------------------------
    print("\n【示例 3】多轮对话:")
    print("-" * 40)

    try:
        # 创建对话会话
        session = ChatSession(
            system_prompt="你是一个专业的 Python 编程助手。",
            model=MODEL
        )

        # 第一轮对话
        print("用户: 什么是列表推导式？")
        print("助手: ", end="")
        session.chat("什么是列表推导式？", stream=True)

        # 第二轮对话（上下文相关）
        print("\n用户: 能给我一个例子吗？")
        print("助手: ", end="")
        session.chat("能给我一个例子吗？", stream=True)

    except Exception as e:
        print(f"错误: {e}")

    print("\n" + "=" * 60)
    print("示例完成")
    print("=" * 60)


# ============================================================
# 快速使用函数
# ============================================================

def quick_chat(prompt: str, stream: bool = True) -> str:
    """
    快速对话函数

    Args:
        prompt: 用户输入
        stream: 是否使用流式输出

    Returns:
        助手的回复
    """
    messages = [
        {"role": "user", "content": prompt}
    ]

    if stream:
        response = ""
        for chunk in chat_completion_stream(messages):
            print(chunk, end="", flush=True)
            response += chunk
        print()
        return response
    else:
        return chat_completion(messages)


if __name__ == "__main__":
    # 检查 API Key
    if API_KEY == "YOUR_API_KEY":
        print("⚠️  请先设置 API Key!")
        print("")
        print("方式 1: 设置环境变量")
        print("  export SILICONFLOW_API_KEY='your-api-key'")
        print("")
        print("方式 2: 直接修改代码中的 API_KEY 变量")
        print("")
        print("获取 API Key: https://cloud.siliconflow.cn/account/ak")
        exit(1)

    main()
```

我们填入API key让它测试一下 

![image-20251119165745083](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251119165745083.png)

**技术特点：**

- 基于官方文档自动生成
- 包含完整的代码示例
- 支持多种编程语言
- 涵盖从入门到高级的所有内容

## 更新说明

### 2025年12月4日 - version 0.0.8

- ✅ 新增 ppt-generator-skill Skill
- ✅ 基于商务模板的专业 PPT 生成器
- ✅ 固定 25 页结构（封面→目录→4章节→结束→字体说明→版权）
- ✅ 三种主题风格：暖色调、商务简约、莫兰迪色系
- ✅ 支持 JSON 配置文件和 Python 代码调用
- ✅ 适用于年度总结、项目汇报、工作述职等场景

### 2025年11月22日 - version 0.0.7

- ✅ 新增 dify-dsl-generator Skill
- ✅ 支持自动生成 Dify 工作流 DSL/YML 文件
- ✅ 基于 86+ 真实案例深度学习
- ✅ 支持所有主要节点类型和复杂工作流逻辑
- ✅ 新增 xiaohuihui-dify-tech-article Skill
- ✅ 专为 Dify 工作流案例分享设计
- ✅ 遵循小灰灰公众号写作规范
- ✅ 包含工作流节点详解、插件安装教程、MCP 集成指南
- ✅ 支持自动生成配图并上传腾讯云 COS 图床

### 2025年11月19日 - version 0.0.6

- ✅ 新增 siliconflow-api-skills Skill
- ✅ 支持硅基流动云服务平台完整文档
- ✅ 包含大语言模型 API、图片生成、向量模型等文档
- ✅ 提供 Chat Completions API 和 Stream 模式指南

### 2025年11月15日 - version 0.0.5

- ✅ 更新 mp-cover-generator Skill 到 v3.1.1
- ✅ 新增描边卡通字体效果（鲜艳色彩 + 多层描边）
- ✅ 新增垂直居中布局（完美视觉平衡）
- ✅ 增大字体（4vw → 5vw），更加醒目
- ✅ 禁止副标题折行（保持单行显示）
- ✅ 新增 HTML 转图片功能（Playwright 驱动）
- ✅ 完整页面截图（修复截断问题，5120x2916 高清）
- ✅ 自动检测内容高度并调整视口
- ✅ 支持 PNG 和 JPEG 双格式输出

### 2025年11月15日 - version 0.0.4

- ✅ 新增 mp-cover-generator Skill v3.0.0
- ✅ 从 jimeng-image-generator 迁移到 jimeng-mcp-server
- ✅ 支持 21:9 公众号封面图生成
- ✅ 返回 4 张可选图片,提供更多风格选择

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

<details>
<summary>公众号封面生成器无法生成图片？</summary>
1. 确认 jimeng-free-api-all Docker 容器正在运行<br>
2. 检查 JIMENG_API_KEY 是否正确配置<br>
3. 确保使用 jimeng-3.1 模型（在生成时指定）<br>
4. 图像生成需要 10-20 秒，请耐心等待<br>
5. 检查后端服务可访问：curl http://localhost:8001<br>
6. 验证有足够的 API 积分（免费层每天 66 积分）<br>
7. 如果 HTML 转图片失败，确认已安装 Node.js 16+ 和 Playwright
</details>

<details>
<summary>生成的封面风格不符合预期怎么办？</summary>
1. 在主题关键词中更明确地描述期望的元素<br>
2. 尝试调整 sample_strength 参数（0.3-0.7 之间）<br>
3. jimeng-mcp-server 返回 4 张图片，可以选择最合适的一张<br>
4. 确认提示词中包含了风格要求（可爱、圆润、3D 插画）<br>
5. 避免使用会触发禁止风格的词汇（霓虹、赛博朋克、暗黑等）
</details>

<details>
<summary>如何自定义封面的文字内容？</summary>
1. 标题：在请求时指定，会自动智能换行<br>
2. 日期：自动获取当前日期，格式为英文星期缩写（如 Fri. 11.15）<br>
3. 作者：目前固定为"O3sky"，如需修改需编辑 SKILL.md 中的规范<br>
4. 文字样式：描边卡通字体，主标题红色 + 白色描边，副标题橙黄色 + 深棕色描边<br>
5. 字体位置：垂直居中（`top: 50%; transform: translateY(-50%);`）
</details>

<details>
<summary>HTML 转图片失败怎么办？</summary>
1. 确认 Node.js 版本：node --version（需要 16+）<br>
2. 安装依赖：cd skill目录 && npm install<br>
3. 安装 Chromium：npx playwright install chromium<br>
4. 检查 HTML 文件路径是否正确<br>
5. 增加等待时间：--wait 3000<br>
6. 查看详细错误信息并根据提示修复
</details>

<details>
<summary>Dify DSL 生成的工作流无法导入?</summary>
1. 检查 YAML 格式是否正确（使用在线 YAML 验证器）<br>
2. 确认 Dify 版本是否兼容（推荐 0.3.0+）<br>
3. 检查节点 ID 是否唯一<br>
4. 验证变量引用格式是否正确（{{#节点ID.变量#}}）<br>
5. 确保所有必填字段完整<br>
6. 查看 Dify 导入错误提示并修复对应问题
</details>

<details>
<summary>生成的 Dify DSL 节点连接有问题?</summary>
1. 检查 edges 数组中的连接关系是否完整<br>
2. 验证 sourceType 和 targetType 是否与节点实际类型匹配<br>
3. 确认每个节点（除 start）都有入边<br>
4. 检查是否有孤立节点未连接<br>
5. 验证最终是否连接到 answer 或其他输出节点
</details>

<details>
<summary>Dify 案例文章图片如何上传到 COS?</summary>
1. 在项目根目录创建 .env 文件<br>
2. 配置腾讯云 COS 信息（SECRET_ID、SECRET_KEY、BUCKET、REGION）<br>
3. 安装依赖：pip install -r scripts/requirements.txt<br>
4. 使用命令上传：python scripts/upload_to_cos.py /path/to/image.png<br>
5. 复制返回的 URL 用于文章中
</details>

<details>
<summary>Dify 案例文章质量不达标怎么办?</summary>
1. 检查总字数是否 > 1800字<br>
2. 确认工作流截图 >= 10个<br>
3. 验证节点配置说明 >= 5个<br>
4. 检查是否包含代码块 >= 3个<br>
5. 确认总结是否单段 300-400字且未分段<br>
6. 检查是否包含固定结束语
</details>

<details>
<summary>如何自定义 Dify DSL 生成模板?</summary>
编辑 dify-dsl-generator/SKILL.md 文件，修改节点模板、提示词模板等。可以参考 references/dsl-structure.md 了解完整的 DSL 结构规范。
</details>

<details>
<summary>PPT 生成器生成的文件打不开?</summary>
1. 确认安装了 python-pptx 库：pip install python-pptx<br>
2. 检查 Python 版本是否为 3.7+<br>
3. 确认文件扩展名为 .pptx<br>
4. 验证 JSON 配置文件格式是否正确<br>
5. 使用 PowerPoint 或 WPS 打开文件查看具体错误
</details>

<details>
<summary>PPT 生成的样式与预期不符?</summary>
1. 确认使用了正确的主题参数（暖色调、商务简约、莫兰迪色系）<br>
2. 检查配置文件中的 4 个章节是否完整<br>
3. 验证每页内容要点是否不超过 4 个<br>
4. 确保文本描述控制在 50-100 字以内<br>
5. 可在生成后使用 PowerPoint 进行微调
</details>

<details>
<summary>PPT 字体显示不正确?</summary>
1. 推荐安装字体：阿里巴巴普惠体 2.0、HarmonyOS Sans SC、MiSans Heavy、思源宋体 CN<br>
2. 如果没有这些字体，系统会使用默认字体替代<br>
3. 可在 PowerPoint 中手动替换为已安装的字体<br>
4. 编辑 ppt_generator.py 中的字体配置自定义使用的字体
</details>

<details>
<summary>如何自定义 PPT 主题颜色?</summary>
编辑 ppt_generator.py 中的 COLOR_SCHEMES 字典，添加或修改主题颜色配置。每个主题包含 primary、secondary、accent、text、background 五种颜色。
</details>


## 技术交流群

欢迎加入技术交流群，分享你的 Skills 和使用心得：

![image-20251204212933573](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251204212933573.png)

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

支付宝

![image-20250914152823776](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152823776.png)

微信

![image-20250914152855543](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

## 📊 项目统计

### 技能统计

- **总技能数**: 8
- **自动化工具**: 2 (excel-report-generator, ppt-generator-skill)
- **内容生成**: 3 (xiaohuihui-tech-article, mp-cover-generator, xiaohuihui-dify-tech-article)
- **AI 多模态**: 1 (jimeng_mcp_skill)
- **API 文档**: 1 (siliconflow-api-skills)
- **工作流工具**: 1 (dify-dsl-generator)

### 开发语言

- Python: 3
- Markdown: 3
- MCP: 1
- YAML/DSL: 1

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
- [ ] 扩展 Dify DSL 生成器支持更多节点类型
- [ ] 优化 Dify 案例文章的图片自动生成功能
- [ ] 添加 Dify 工作流 DSL 校验工具

## License

MIT License

## Star History

如果觉得项目不错，欢迎点个 Star ⭐

![claude-skills](https://api.star-history.com/svg?repos=yourusername/claude-skills&type=Date)

---

**开始使用**: 选择一个 Skill，按照使用说明安装，然后在 Claude Code 中尽情使用吧！