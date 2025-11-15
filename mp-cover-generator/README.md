# 公众号封面生成器 (MP Cover Generator)

根据主题和标题自动生成现代风格的公众号封面图，支持 HTML 和高质量图片两种输出格式。

## ✨ 核心特性

- 🎨 **可爱圆润的 3D 插画风格**：类似皮克斯动画的卡通质感
- 🤖 **AI 智能生成**：基于 jimeng-mcp-server（即梦 AI）生成底图
- 📱 **16:9 宽高比**：专为公众号封面优化
- 🖼️ **双格式输出**：HTML 页面 + 高清图片（PNG/JPEG）
- ⚡ **高性能截图**：Playwright 驱动，2x 像素密度，完整页面截图（5120x2916）
- 🎯 **一键生成**：从提示词到成品，全自动化流程
- ✨ **描边卡通字体**：醒目的多层描边效果，主副标题对比鲜明
- 📐 **垂直居中布局**：核心标题完美居中，视觉平衡

## 📦 安装

### 前置要求

1. **jimeng-free-api-all** Docker 容器运行
2. **jimeng-mcp-server** 正确配置
3. **Node.js 16+** 环境（图片输出功能）

### 安装依赖

```bash
cd /mnt/f/work/code/other/skill/mp-cover-generator

# 安装 Playwright 依赖
npm install

# 安装 Chromium 浏览器
npx playwright install chromium
```

## 🚀 快速开始

### 1. 生成 HTML 封面

在 Claude Code 中直接使用：

```
请使用 mp-cover-generator skill 生成一个公众号封面：
主题：AI 技术
标题：即梦无限画布
```

将生成 `mp_cover_YYYYMMDD.html` 文件。

### 2. 转换为图片

生成后的 HTML 会自动转换为高质量图片（PNG 和 JPEG）。

**手动转换命令：**

```bash
# 生成 PNG（无损，高质量）
node scripts/capture.js mp_cover_20251115.html mp_cover_20251115.png

# 生成 JPEG（文件更小）
node scripts/capture.js mp_cover_20251115.html mp_cover_20251115.jpg --quality 95
```

**截图特性：**
- ✅ 完整页面截图（`fullPage: true`）
- ✅ 自动检测内容高度并调整视口
- ✅ 2x 像素密度，输出高清图片（5120x2916）
- ✅ 等待所有图片和字体加载完成

## 📐 参数配置

capture.js 支持以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--width` | 视口宽度（像素） | 2560 |
| `--height` | 视口高度（像素） | 1097（21:9） |
| `--quality` | JPEG 质量（1-100） | 95 |
| `--wait` | 等待时间（毫秒） | 2000 |
| `--scale` | 设备像素比 | 2 |

**示例：**
```bash
node scripts/capture.js cover.html cover.png \
  --width 2560 \
  --height 1097 \
  --scale 2 \
  --wait 3000
```

![image-20251115183718247](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115183718247.png)

![image-20251115183746503](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20251115183746503.png)



## 🎨 视觉风格

### 主题风格
- 可爱、圆润、简洁的 3D 插画
- 质感类似皮克斯动画或黏土定格动画
- 柔和的光影和玩具般的亲和力

### 文字样式（核心特色）
- **描边卡通字体**：鲜艳色彩 + 多层描边，醒目突出
- **主标题**：红色 (#FF3333) + 白色描边，8方向文字阴影
- **副标题**：橙黄色 (#FFB84D) + 深棕色描边，单行不折行
- **字号**：5vw（响应式大字体）
- **位置**：垂直居中（`top: 50%; transform: translateY(-50%);`）
- **立体感**：多层阴影模拟描边 + 额外立体阴影

### 布局规范
- **右图左文**：主体元素位于右侧 30-40%
- **左侧留白**：左侧 60-70% 干净空间供文字显示
- **低饱和度背景**：纯色或同色系渐变
- **垂直居中**：核心标题完美居中，视觉平衡

### 禁止风格
- ❌ 霓虹/赛博朋克风格
- ❌ 暗黑深沉风格
- ❌ 抽象科技线条
- ❌ 玻璃质感或写实渲染

## 📊 输出对比

以 "MCP案例分享 claude调用AI生图视频教程" 为例：

| 格式 | 文件大小 | 分辨率 | 质量 | 用途 |
|------|---------|--------|------|------|
| HTML | 4.5 KB | 响应式 | 最佳 | 网页预览、编辑 |
| PNG | 4.10 MB | 5120x2916 | 无损 | 高质量发布、打印 |
| JPEG | 1.44 MB | 5120x2916 | 优秀 | 一般发布、节省空间 |

**注**：实际分辨率会根据页面内容高度自动调整，确保完整截图无截断。

## 🔧 故障排查

### jimeng 图片生成失败

1. 确认 Docker 容器运行：`docker ps | grep jimeng`
2. 检查 API 密钥配置：`JIMENG_API_KEY`
3. 验证后端服务：`curl http://localhost:8001`
4. 确保有足够积分（免费层每天 66 积分）
5. 耐心等待（10-20 秒生成时间）

### HTML 转图片失败

1. 确认 Node.js 版本：`node --version`（需要 16+）
2. 重新安装依赖：
   ```bash
   npm install
   npx playwright install chromium
   ```
3. 检查 HTML 文件路径是否正确
4. 增加等待时间：`--wait 3000`
5. 查看错误信息并根据提示修复

## 📝 版本历史

### v3.1.1 (2025-11-15)
- ✅ **新增描边卡通字体效果**：多层阴影模拟描边，主副标题对比鲜明
- ✅ **标题垂直居中**：核心标题改为垂直居中布局（`top: 50%; transform: translateY(-50%);`）
- ✅ **增大字体**：字号从 4vw 提升到 5vw，更加醒目
- ✅ **禁止副标题折行**：使用 `white-space: nowrap` 确保第二行不折行
- ✅ **完整页面截图**：修复截断问题，自动检测内容高度并调整视口
- ✅ **高质量输出**：5120x2916 高清分辨率，2x 像素密度

### v3.1.0 (2025-11-15)
- ✅ 新增 HTML 转图片功能
- ✅ 集成 Playwright 实现高质量截图
- ✅ 支持 PNG 和 JPEG 两种输出格式
- ✅ 默认 2x 像素密度输出
- ✅ 添加完整的参数配置支持

### v3.0.0 (2025-11-15)
- ✅ 从 jimeng-image-generator 迁移到 jimeng-mcp-server
- ✅ 使用标准 MCP 协议
- ✅ 支持 jimeng-3.1 模型
- ✅ 返回 4 张可选图片

## 📚 相关资源

- [jimeng-mcp-server](https://github.com/wwwzhouhui/jimeng-mcp-server)
- [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all)
- [即梦 AI 官网](https://jimeng.jianying.com/)
- [Playwright 文档](https://playwright.dev/)

## 📄 许可证

MIT License

## 👤 作者

wwwzhouhui

---

**提示**：完整使用说明请查看 [SKILL.md](./SKILL.md)
