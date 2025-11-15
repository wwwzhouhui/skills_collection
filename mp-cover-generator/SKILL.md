---
name: "公众号封面生成器"
description: "根据主题和标题生成现代风格的公众号封面图，使用jimeng-mcp-server生成3D插画风格底图，叠加文字层生成HTML，并可选择性转换为高质量PNG/JPG图片"
version: "3.1.1"
dependencies:
  - "jimeng-mcp-server (基于即梦AI的MCP服务器)"
  - "HTML/CSS 知识"
  - "Python 3.10+ 环境"
  - "即梦AI Session ID (JIMENG_API_KEY)"
  - "jimeng-free-api-all Docker 容器"
  - "Node.js 16+ 环境（图片输出功能需要）"
  - "Playwright (HTML转图片功能)"
---

# 公众号封面生成器 Skill

## 🎯 核心任务

根据用户给定的**主题**、**标题**、**日期**和**作者名**，创建一个符合现代科技/生活方式调性的**公众号封面图**。

**输出格式支持：**
1. **HTML 格式**：固定宽高比为 21:9 的完整 HTML 文件，包含内联样式，可在浏览器中直接查看
2. **图片格式**：通过 Playwright 将 HTML 转换为高质量 PNG 或 JPG 图片（可选）

## 🎨 视觉风格总览

* **主题风格**: **可爱、圆润、简洁的3D插画风格 (Cute, Soft, Minimalist 3D Illustration)**。质感类似皮克斯动画或黏土定格动画，具有柔和的光影和玩具般的亲和力。
* **色彩**: 整体色调和谐、明快。背景为低饱和度的纯色或同色系渐变，以确保左侧文字有良好的可读性。
* **构图**: 严格的非对称式"右图左文"布局，视觉焦点清晰，主次分明。
* **文字样式**:
  - **描边标题**: 核心标题使用**鲜艳色彩+白色/深色描边**效果，类似卡通字体，醒目突出
  - **主标题**: 红色/橙红色 + 白色描边（`#FF3333`、`#FF6B35`）
  - **副标题**: 橙黄色 + 深色描边（`#FFB84D`、`#FFA726`）
  - **立体感**: 使用 `text-shadow` 多层阴影模拟描边，增强视觉冲击力
  - **参考风格**: 类似参考图片中"MCP案例分享"的描边卡通字体效果

## 何时使用此 Skill

当用户需要：
- 创建公众号文章封面
- 生成社交媒体横幅图
- 制作带有标题和日期的宣传图
- 需要 3D 插画风格的图文结合设计

关键触发词：公众号封面、封面图、banner、头图、宣传图

## MCP 配置

### jimeng-mcp-server 设置

本技能使用 jimeng-mcp-server MCP 来生成图片。需要确保以下条件已满足：

#### 前置条件

1. **jimeng-free-api-all Docker 容器运行**
   ```bash
   docker run -it -d --init \
     --name jimeng-free-api-all \
     -p 8001:8000 \
     -e TZ=Asia/Shanghai \
     wwwzhouhui569/jimeng-free-api-all:latest
   ```

2. **环境变量已配置**
   - `JIMENG_API_KEY`: 您的即梦 API 密钥（从即梦网站 cookies 获取 sessionid 值）
   - `JIMENG_API_URL`: API 端点（默认：http://127.0.0.1:8001）
   - `JIMENG_MODEL`: 模型名称（推荐使用 jimeng-3.1）

#### MCP 客户端配置

**Claude Desktop 配置示例：**

配置文件位置：
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jimeng-mcp-server": {
      "command": "python3",
      "args": ["-m", "jimeng_mcp.server"],
      "env": {
        "JIMENG_API_KEY": "your_sessionid_here",
        "JIMENG_API_URL": "http://127.0.0.1:8001"
      }
    }
  }
}
```

**Cherry Studio SSE 模式：**

1. 启动 SSE 服务器：
   ```bash
   cd jimeng-mcp-server
   source .venv/bin/activate
   python -m jimeng_mcp.server --transport sse --port 8080
   ```

2. 在 Cherry Studio 中添加服务器：
   - 名称：jimeng-mcp-server
   - 类型：SSE
   - URL：`http://localhost:8080/sse`

### 环境要求

确保系统已安装：
- Python 3.10+
- Docker（用于运行 jimeng-free-api-all）
- jimeng-mcp-server 已正确安装
- 即梦 AI Session ID（需要从即梦网站 cookies 获取）

## 📐 生成规范与流程

### 第一部分：底图生成 (使用 jimeng-mcp-server)

此区域用于生成无任何文字的、符合构图和风格规范的背景插图。

#### 尺寸与布局
* **图片宽高比**: **21:9** (3024x1296 像素)
* **主体位置**: 核心的 3D 视觉元素（如人物、设备、场景）**必须全部位于画面右侧的 30%-40% 区域内**
* **留白区域**: 画面**左侧 60%-70% 的区域必须是干净的留白**，可以是纯色或非常微妙的渐变，不能有任何干扰视觉的元素

#### 【极其重要】禁止的视觉元素
* **严禁任何形式的文字**: 生成的底图中绝对不能包含任何字母、数字或符号
* **严禁边框**: 图片不能有任何形式的内外边框

#### 插图生成要求

**内容**: 插图需根据用户输入的**主题关键词**，象征性地创作一个场景。

**背景**: 背景必须是简单的纯色或从左到右的同色系渐变 (`subtle monochromatic gradient background`)。

**【风格重点 - 严格遵守】**:

**核心风格**:
- ✅ **必须是可爱、圆润的卡通3D风格 (Cute, rounded, cartoon 3D style)**
- ✅ 所有模型都应有**柔和的边缘**和**哑光或黏土般的材质 (soft edges, matte or clay-like material)**
- ✅ 整体感觉类似**皮克斯动画 (Pixar animation style)** 或**玩具质感 (toy-like texture)**
- ✅ 光照必须是明亮且柔和的 (`bright and soft lighting`)

**规避风格**:
- ❌ **严格禁止**生成以下风格：
  - **霓虹/赛博朋克风 (NO neon, NO cyberpunk)**
  - **暗黑深沉风 (NO dark themes)**
  - **抽象科技线条风 (NO abstract tech lines)**
  - **玻璃质感或写实渲染风 (NO glassmorphism, NO photorealism)**

### 第二部分：文字层叠加 (Agent HTML实现)

此部分基于第一步生成的底图，通过绝对定位的方式精确添加文字层。

#### HTML结构
* 创建一个主容器 `div`，`position: relative;`
* 底图作为 `<img>` 标签置于容器底层，`width: 100%; display: block;`
* 所有文字元素分别使用独立的 `div` 或 `p` 标签，并通过 `position: absolute;` 进行定位

#### 字体
优先使用流行的中文字体

#### 内容与样式 (基于父容器尺寸)

1. **日期 (Date)**:
   * 内容: 获取当前星期和日期，格式: Fri. 9.15
   * 样式: `position: absolute; top: 8%; left: 6%;` 字号 `font-size: 1.5vw;` (或等效的px值), 颜色 `color: #999999;`

2. **核心标题 (Headline)**:
   * 内容: [由用户指定，需拆分为两行]
   * 样式: `position: absolute; top: 50%; transform: translateY(-50%); left: 6%;` 字号 `font-size: 5vw;` (或等效的px值), **加粗** `font-weight: bold;`
   * **描边效果** (重要):
     - 使用 CSS `text-stroke` 或 `text-shadow` 创建文字描边
     - 描边颜色：白色或深色（根据文字颜色对比选择）
     - 描边宽度：`-webkit-text-stroke: 3px #FFFFFF;` 或使用多层阴影模拟描边
     - 主标题颜色：鲜艳色彩（如 `#FF3333` 红色、`#FF6B35` 橙红色）
     - 副标题颜色：对比色（如 `#FFB84D` 橙黄色、`#FFA726` 橙色）
   * 文字阴影: `text-shadow: 2px 2px 4px rgba(0,0,0,0.3);` 增强立体感
   * 行高 `line-height: 1.3;` 确保双行标题紧凑
   * **布局要求**: 第二行文字使用 `white-space: nowrap;` 确保不折行
   * **参考效果**: 类似描边卡通字体，文字醒目突出，适合公众号封面

3. **作者 (Author)**:
   * 内容: 固定为：o3sky
   * 样式: `position: absolute; bottom: 8%; left: 6%;` 字号 `font-size: 1.5vw;` (或等效的px值), 颜色 `color: #666666;`

## 💡 系统执行流程

### 第一步：收集必要信息

从用户处获取以下信息：
1. **主题关键词**：用于生成插画内容（必填）
2. **标题**：封面的核心标题文字（必填）

自动生成的信息：
- **日期**：自动获取当前星期和日期，格式为 `Fri. 11.15`
- **作者名**：固定为"o3sky"

### 第二步：使用 jimeng-mcp-server 生成底图

调用 jimeng-mcp-server 的 `text_to_image` 工具来生成底图。

#### MCP 调用示例

使用 `mcp__jimeng-mcp-server__text_to_image` 工具生成底图：

```python
# 调用 jimeng-mcp-server 的 text_to_image 工具
mcp__jimeng-mcp-server__text_to_image(
    prompt="Create a cute, rounded, cartoon 3D illustration with [主题关键词] theme. Style: Pixar-like animation, toy-like texture, soft edges, matte/clay-like materials, bright and soft lighting, vibrant colors. Main elements: [具体描述主题相关的物体和图标]. NO people, NO characters. Composition: Main elements positioned in RIGHT 30-40% of frame. LEFT 60-70% clean space with gradient background. Aspect ratio: 21:9 ultra-wide. IMPORTANT: NO text, NO people, NO characters, NO neon/cyberpunk, NO dark themes, NO abstract tech lines, NO glassmorphism, NO photorealism.",
    width=3024,
    height=1296,  # 21:9比例
    model="jimeng-3.1",  # 推荐使用 jimeng-3.1 模型
    sample_strength=0.6
)
```

#### 生成提示词模板

**默认模板：**
```
Create a cute, rounded, cartoon 3D illustration with [主题关键词] theme.
Style: Pixar-like animation, toy-like texture, soft edges, matte/clay-like materials, bright and soft lighting, vibrant colors.
Main elements: [具体描述主题相关的物体和图标，如：AI brain with floating skill badges, glowing lightbulbs, stacked books, interlocking gears]
Composition: Main elements positioned in RIGHT 30-40% of frame.
LEFT 60-70% must be clean space with gradient background or subtle geometric patterns.
Aspect ratio: 21:9 (ultra-wide)
IMPORTANT: NO text, NO letters, NO numbers, NO borders, NO people, NO characters, NO neon/cyberpunk, NO dark themes, NO abstract tech lines, NO glassmorphism, NO photorealism.
```

#### 返回结果处理

jimeng-mcp-server 会返回 4 张不同风格的图片 URL：

```
✅ 成功生成 4 张图像

📷 图像URL列表:
图像 1: https://p26-dreamina-sign.byteimg.com/...
图像 2: https://p26-dreamina-sign.byteimg.com/...
图像 3: https://p26-dreamina-sign.byteimg.com/...
图像 4: https://p26-dreamina-sign.byteimg.com/...
```

选择最符合要求的一张图片（通常选择第一张）作为封面底图。

### 第三步：构建 HTML 文件

基于生成的底图，创建包含文字层的 HTML 文件。

#### HTML 结构模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>公众号封面</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }

        /* 主容器样式 */
        .cover-container {
            position: relative;
            width: 100%;
            max-width: 2560px;
            aspect-ratio: 21/9;
            overflow: hidden;
            background: #ffffff;
        }

        /* 背景图片 */
        .cover-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        /* 日期样式 */
        .date {
            position: absolute;
            top: 8%;
            left: 6%;
            font-size: 1.5vw;
            color: #999999;
            font-weight: 400;
            letter-spacing: 0.05em;
        }

        /* 主标题样式 - 带描边效果 */
        .headline {
            position: absolute;
            top: 50%;
            transform: translateY(-50%);
            left: 6%;
            max-width: 55%;
            font-size: 5vw;  /* 加大字号 */
            font-weight: bold;
            line-height: 1.3;
            letter-spacing: -0.01em;
            /* 描边效果 - 使用多层阴影模拟描边 */
            color: #FF3333;  /* 主标题红色 */
            text-shadow:
                /* 白色描边效果 */
                -3px -3px 0 #FFFFFF,
                 3px -3px 0 #FFFFFF,
                -3px  3px 0 #FFFFFF,
                 3px  3px 0 #FFFFFF,
                -3px  0   0 #FFFFFF,
                 3px  0   0 #FFFFFF,
                 0   -3px 0 #FFFFFF,
                 0    3px 0 #FFFFFF,
                /* 立体阴影 */
                 4px  4px 6px rgba(0, 0, 0, 0.3);
            /* Webkit 浏览器的描边支持 */
            -webkit-text-stroke: 0.5px rgba(255, 255, 255, 0.3);
        }

        /* 副标题样式（如果标题分两行，第二行可用此样式）*/
        .headline-secondary {
            color: #FFB84D;  /* 副标题橙黄色 */
            white-space: nowrap;  /* 禁止折行 */
            text-shadow:
                -3px -3px 0 #8B4513,
                 3px -3px 0 #8B4513,
                -3px  3px 0 #8B4513,
                 3px  3px 0 #8B4513,
                -3px  0   0 #8B4513,
                 3px  0   0 #8B4513,
                 0   -3px 0 #8B4513,
                 0    3px 0 #8B4513,
                 4px  4px 6px rgba(0, 0, 0, 0.4);
            -webkit-text-stroke: 0.5px rgba(139, 69, 19, 0.3);
        }

        /* 作者信息样式 */
        .author {
            position: absolute;
            bottom: 8%;
            left: 6%;
            font-size: 1.5vw;
            color: #666666;
            font-weight: 500;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            .date {
                font-size: 2.5vw;
            }

            .headline {
                font-size: 6vw;
                max-width: 60%;
            }

            .author {
                font-size: 2.5vw;
            }
        }

        @media (max-width: 480px) {
            .date {
                font-size: 3.5vw;
            }

            .headline {
                font-size: 7vw;
                max-width: 70%;
            }

            .author {
                font-size: 3.5vw;
            }
        }
    </style>
</head>
<body>
    <div class="cover-container">
        <!-- 背景图片 -->
        <img src="[从 jimeng-mcp-server 返回的图片 URL]" alt="封面背景">

        <!-- 日期 -->
        <div class="date">[当前日期，格式: Fri. 11.15]</div>

        <!-- 标题 -->
        <h1 class="headline">[用户指定的标题]</h1>

        <!-- 作者 -->
        <div class="author">O3sky</div>
    </div>
</body>
</html>
```

#### 智能文字样式决策

**描边标题方案（推荐）：**
- 使用**鲜艳色彩 + 描边**的组合，确保在任何背景下都醒目突出
- **主标题**：红色/橙红色文字 + 白色描边（`color: #FF3333; text-shadow: 多层白色阴影`）
- **副标题**：橙黄色文字 + 深色描边（`color: #FFB84D; text-shadow: 多层深色阴影`）
- 描边通过 8 层 `text-shadow` 模拟，创建厚重的轮廓效果
- 额外添加立体阴影增强视觉冲击力

**传统方案（可选）：**
- 自动检测底图左侧区域的亮度
- 如果背景偏暗 → 标题颜色使用白色 (`#FFFFFF`)
- 如果背景偏亮 → 标题颜色使用深色 (`#000000`)

**推荐使用描边方案**，效果更加醒目，适合公众号封面的视觉需求。

### 第四步：输出 HTML 文件

1. 保存为独立的 HTML 文件（例如：`mp_cover_[日期].html`）
2. 向用户展示预览效果
3. 提供完整代码和文件路径

### 第五步：HTML 转图片（可选）

如果用户需要图片格式，可以使用 Playwright 将 HTML 转换为高质量图片。

#### 安装依赖

首次使用前需要安装 Playwright 和浏览器：

```bash
cd /mnt/f/work/code/other/skill/mp-cover-generator
npm install
npx playwright install chromium
```

#### 使用 capture.js 转换图片

**基本用法：**
```bash
node scripts/capture.js mp_cover_20251115.html mp_cover_20251115.png
```

**生成 JPEG 格式（文件更小）：**
```bash
node scripts/capture.js mp_cover_20251115.html mp_cover_20251115.jpg --quality 95
```

**自定义参数：**
```bash
node scripts/capture.js cover.html cover.png \
  --width 2560 \
  --height 1097 \
  --scale 2 \
  --wait 2000
```

#### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--width` | 视口宽度（像素） | 2560 |
| `--height` | 视口高度（像素） | 1097（21:9 比例） |
| `--quality` | JPEG 质量（1-100） | 95 |
| `--wait` | 等待时间（毫秒） | 2000 |
| `--scale` | 设备像素比（高清） | 2 |

#### 输出特点

- **高质量**：默认 2倍像素密度，实际输出 5120x2194 像素
- **格式支持**：PNG（无损）和 JPG（较小文件）
- **自动加载**：等待所有图片和字体加载完成
- **精确尺寸**：严格按照视口大小截图，无多余空白

## 示例对话流程

**用户输入：**
```
生成一个关于 AI 的公众号封面，标题是"即梦无限画布"
```

**Assistant 执行：**

1. **收集信息**
   - 主题：AI/科技创新
   - 标题：即梦无限画布
   - 日期：Fri. 11.15（自动获取）
   - 作者：O3sky（固定）

2. **使用 jimeng-mcp-server 生成底图**
   - 调用 `mcp__jimeng-mcp-server__text_to_image` 工具：
     ```python
     mcp__jimeng-mcp-server__text_to_image(
         prompt="Create a cute, rounded, cartoon 3D illustration with AI/technology theme. Style: Pixar-like animation, toy-like texture, soft edges, matte/clay-like materials, bright and soft lighting, vibrant colors. Main elements: Glowing AI brain icon with floating skill badges, lightbulbs, books, gears and neural network nodes. NO people, NO characters. Composition: Elements positioned in RIGHT 30-40% of frame. LEFT 60-70% clean space with purple-blue gradient background. Aspect ratio: 21:9 ultra-wide. IMPORTANT: NO text, NO people, NO characters, NO borders, NO neon/cyberpunk, NO dark themes, NO abstract tech lines, NO glassmorphism, NO photorealism.",
         width=3024,
         height=1296,
         model="jimeng-3.1",
         sample_strength=0.6
     )
     ```
   - 从返回的 4 张图片中选择第一张作为底图

3. **构建 HTML**
   - 创建包含底图和文字层的完整 HTML 文件
   - 根据背景亮度自动调整文字颜色
   - 使用从 jimeng-mcp-server 返回的图片 URL

4. **输出 HTML**
   - 保存为 `mp_cover_{当前日期}.html`
   - 向用户展示文件路径

5. **转换为图片（可选）**
   - 如果用户需要图片格式，使用 Playwright 转换：
     ```bash
     node scripts/capture.js mp_cover_20251115.html mp_cover_20251115.png
     ```
   - 输出高质量 PNG 图片（5120x2194 像素，2x 像素密度）
   - 或输出 JPEG 格式以减小文件大小：
     ```bash
     node scripts/capture.js mp_cover_20251115.html mp_cover_20251115.jpg --quality 95
     ```

## 注意事项

### 技术要求
- **图片尺寸配置**：严格使用 3024x1296（21:9比例），但 jimeng-mcp-server 限制最大 2048 宽度，实际使用 2048x864 或 1536x864
- **模型选择**：推荐使用 jimeng-3.1 模型，效果更好
- **采样强度**：建议设置为 0.6，平衡创意性和真实性
- **等待时间**：图像生成需要 10-20 秒，请耐心等待
- **Node.js 环境**：图片输出功能需要 Node.js 16+ 和 Playwright（首次使用需安装依赖）

### 布局要求
- **布局比例调整**：主体元素严格位于右侧30%-40%区间，左侧60%-70%必须保持干净留白
- 确保生成的底图完全符合风格规范，特别是可爱圆润的卡通3D风格
- 文字层的定位使用相对单位（vw/%），确保响应式

### 内容规范
- 标题如果过长，需要智能换行，保持在 2-3 行以内
- 星期和日期格式必须为英文星期缩写格式（如 Fri. 11.15）
- 作者名固定为"O3sky"，不接受用户自定义

### 故障排查

**如果图片生成失败：**
1. 确认 jimeng-free-api-all Docker 容器正在运行
2. 检查 JIMENG_API_KEY 是否正确配置
3. 验证后端服务可访问：`curl http://localhost:8001`
4. 确保有足够的 API 积分（免费层每天 66 积分）
5. 图像生成需要 10-20 秒，请耐心等待

**如果 HTML 转图片失败：**
1. 确认已安装 Node.js 16+ 环境：`node --version`
2. 安装 Playwright 依赖：
   ```bash
   cd /mnt/f/work/code/other/skill/mp-cover-generator
   npm install
   npx playwright install chromium
   ```
3. 检查 HTML 文件路径是否正确（使用绝对路径或相对路径）
4. 如果图片未加载，增加 `--wait` 时间：`--wait 3000`
5. 查看详细错误信息，根据提示修复问题

## 版本更新说明

### v3.1.1 (2025-11-15)
- ✅ 新增描边卡通字体效果
- ✅ 标题垂直居中布局
- ✅ 增大字体（4vw → 5vw）
- ✅ 禁止副标题折行（white-space: nowrap）
- ✅ 完整页面截图（修复截断问题）
- ✅ 自动检测内容高度并调整视口
- ✅ 高质量输出（5120x2916，2x 像素密度）

### v3.1.0 (2025-11-15)
- ✅ 新增 HTML 转图片功能
- ✅ 集成 Playwright 实现高质量截图
- ✅ 支持 PNG 和 JPEG 两种输出格式
- ✅ 默认 2x 像素密度，输出 5120x2194 高清图片
- ✅ 添加 capture.js 脚本工具
- ✅ 添加完整的参数配置支持

### v3.0.0 (2025-11-15)
- ✅ 从 jimeng-image-generator 迁移到 jimeng-mcp-server
- ✅ 使用标准 MCP 协议调用
- ✅ 支持 jimeng-3.1 模型
- ✅ 返回 4 张可选图片，提供更多选择
- ✅ 更新配置说明和故障排查指南

### v2.0.0
- 初始版本，使用 jimeng-image-generator

## 相关资源

- **jimeng-mcp-server GitHub**: https://github.com/wwwzhouhui/jimeng-mcp-server
- **jimeng-free-api-all GitHub**: https://github.com/wwwzhouhui/jimeng-free-api-all
- **即梦 AI 官网**: https://jimeng.jianying.com/
- **MCP 协议文档**: https://modelcontextprotocol.io/
