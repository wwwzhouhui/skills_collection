---
name: xiaohuihui-tech-article
description: 专为技术实战教程设计的公众号文章生成器,遵循小灰灰公众号写作规范,自动生成包含前言、项目介绍、部署实战、总结的完整技术文章,配有详细操作步骤、代码示例,并通过即梦AI生成配图上传至腾讯云COS图床
version: 2.1.0
---

# 小灰灰技术文章生成器

专业的技术实战教程创作助手,完全遵循小灰灰公众号的写作风格和结构规范。**新增即梦AI自动配图功能,一键生成并上传至腾讯云COS图床。**

## 核心功能

- ✅ **标准四段式结构**: 前言 → 项目介绍 → 部署实战 → 总结
- ✅ **三段式开头**: 问题引入 + 解决方案 + 实战预告
- ✅ **详细实战步骤**: 环境准备 → 依赖安装 → 配置 → 实现 → 测试
- ✅ **单段长句总结**: 300-500字深度总结(必须单段不分段)
- ✅ **口语化技术文**: "呵呵"、"好家伙"、"手把手教"等亲和表达
- ✅ **完整资源附加**: GitHub + 体验地址 + 网盘下载
- ✅ **智能配图生成**: 调用即梦AI(jimeng-mcp-server)自动生成配图
- ✅ **图床自动上传**: 生成的图片自动上传至腾讯云COS图床

## 使用方法

### 基础用法
```
用小灰灰公众号风格写一篇 [技术/项目] 的部署教程
```

### 详细用法
```
帮我写一篇小灰灰风格的技术文章:
- 主题: [具体技术名称]
- 核心功能: [要介绍的功能]
- 部署平台: [Docker/本地/云服务]
- 技术栈: [相关技术]
```

### 带自动配图的用法
```
帮我写一篇小灰灰风格的技术文章,并自动生成配图:
- 主题: [具体技术名称]
- 核心功能: [要介绍的功能]
- 配图风格: [3D插画/扁平化/科技感/手绘风格]
- 是否上传图床: 是
```

---

## 图片生成与上传功能

### 前置条件

使用图片自动生成功能前,请确保以下服务已正确配置:

1. **即梦MCP服务器运行中**
   - jimeng-mcp-server 通过 stdio/SSE/HTTP 模式运行
   - 环境变量 `JIMENG_API_KEY` 已配置

2. **腾讯云COS配置**
   - 已创建存储桶
   - 配置以下环境变量或在代码中设置:
     - `COS_REGION`: 地域(如 ap-nanjing)
     - `COS_SECRET_ID`: 腾讯云 SecretId
     - `COS_SECRET_KEY`: 腾讯云 SecretKey
     - `COS_BUCKET`: 存储桶名称

### 工作流程

```
生成文章内容 → 识别图片占位符 → 生成图片描述(prompt)
     ↓
调用即梦text_to_image → 获取生成图片URL → 下载图片
     ↓
上传至腾讯云COS → 获取永久链接 → 替换占位符
```

### 图片生成规则

#### 1. 图片描述生成

根据文章上下文自动生成图片描述(prompt):

| 图片类型 | prompt模板 | 示例 |
|----------|------------|------|
| 项目架构图 | `技术架构图,{项目名称},{核心技术},3D等距视角,蓝色科技风格,简洁专业` | `技术架构图,DeepSeek-OCR,Python FastAPI VLLM,3D等距视角,蓝色科技风格` |
| 功能演示图 | `软件界面展示,{功能描述},现代UI设计,深色主题,专业感` | `软件界面展示,OCR文字识别结果对比,现代UI设计,深色主题` |
| 环境配置图 | `服务器配置界面,{平台名称},终端命令行,技术感,清晰展示` | `服务器配置界面,AutoDL云服务器,终端命令行,技术感` |
| 代码运行图 | `代码编辑器界面,{编程语言}代码,语法高亮,深色主题,专业开发` | `代码编辑器界面,Python代码,语法高亮,深色主题` |
| 结果展示图 | `{功能}效果展示,前后对比,成功状态,绿色指示,清晰直观` | `OCR识别效果展示,前后对比,成功状态,绿色指示` |

#### 2. 即梦MCP工具调用

使用 `mcp__jimeng-mcp-server__text_to_image` 工具生成图片:

```json
{
  "prompt": "技术架构图,DeepSeek-OCR光学压缩技术,Python FastAPI VLLM推理引擎,3D等距视角,蓝色科技风格,简洁专业,高清",
  "ratio": "16:9",
  "resolution": "2k",
  "model": "jimeng-4.5",
  "sample_strength": 0.5,
  "negative_prompt": "模糊,低质量,文字错误,乱码"
}
```

**参数说明:**
- `ratio`: 宽高比,推荐 16:9 适合公众号文章
- `resolution`: 分辨率,推荐 2k 平衡质量与速度
- `model`: 默认 jimeng-4.5,高质量生成
- `sample_strength`: 0.3-0.7,值越高越有创意

#### 3. 图片下载

从即梦返回的URL下载图片到本地:

```python
import httpx
import os
from datetime import datetime

async def download_image(image_url: str, save_dir: str = "/tmp/article_images") -> str:
    """
    下载图片到本地
    :param image_url: 即梦生成的图片URL
    :param save_dir: 保存目录
    :return: 本地文件路径
    """
    os.makedirs(save_dir, exist_ok=True)

    # 生成文件名: image-YYYYMMDD-HHMMSS.png
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"image-{timestamp}.png"
    filepath = os.path.join(save_dir, filename)

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(image_url)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

    return filepath
```

#### 4. 上传至腾讯云COS

使用 `cos_utils.py` 中的 `TencentCOSUploader` 类上传图片:

```python
from cos_utils import TencentCOSUploader
import os

# COS配置 (建议通过环境变量配置)
COS_CONFIG = {
    "region": os.getenv("COS_REGION", "ap-nanjing"),
    "secret_id": os.getenv("COS_SECRET_ID"),
    "secret_key": os.getenv("COS_SECRET_KEY"),
    "bucket": os.getenv("COS_BUCKET", "mypicture-1258720957")
}

def upload_to_cos(local_path: str, target_name: str = None) -> str:
    """
    上传图片到腾讯云COS
    :param local_path: 本地图片路径
    :param target_name: COS中的文件名,不填则使用本地文件名
    :return: 图片永久访问URL
    """
    uploader = TencentCOSUploader(**COS_CONFIG)

    # 生成COS中的文件名
    if not target_name:
        target_name = os.path.basename(local_path)

    result = uploader.upload_from_file(local_path, target_name)

    if result["success"]:
        return result["url"]
    else:
        raise Exception(f"上传失败: {result['error']}")

# 使用示例
# cos_url = upload_to_cos("/tmp/article_images/image-20251214-143703.png")
# 返回: https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251214-143703.png
```

#### 5. 内存直接上传(推荐)

无需保存本地文件,直接从内存上传:

```python
import httpx
from cos_utils import TencentCOSUploader
from datetime import datetime

async def download_and_upload_image(image_url: str, cos_config: dict) -> str:
    """
    下载图片并直接上传到COS(不保存本地)
    :param image_url: 即梦生成的图片URL
    :param cos_config: COS配置字典
    :return: COS永久访问URL
    """
    # 1. 下载图片到内存
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        image_content = response.content

    # 2. 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"image-{timestamp}.png"

    # 3. 上传到COS
    uploader = TencentCOSUploader(**cos_config)
    result = uploader.upload_from_memory(image_content, filename)

    if result["success"]:
        return result["url"]
    else:
        raise Exception(f"上传失败: {result['error']}")
```

### 完整图片生成流程

#### 步骤1: 生成文章时标记图片位置

在生成文章时,使用特定格式标记需要配图的位置:

```markdown
![项目架构图]({{IMAGE:技术架构图,DeepSeek-OCR,3D等距视角,蓝色科技风}})

![功能演示]({{IMAGE:软件界面展示,OCR识别结果,现代UI设计}})
```

#### 步骤2: 解析图片占位符

```python
import re

def extract_image_placeholders(article_content: str) -> list:
    """
    提取文章中的图片占位符
    :return: [(alt_text, prompt), ...]
    """
    pattern = r'!\[(.*?)\]\(\{\{IMAGE:(.*?)\}\}\)'
    matches = re.findall(pattern, article_content)
    return matches

# 示例
# [("项目架构图", "技术架构图,DeepSeek-OCR,3D等距视角,蓝色科技风")]
```

#### 步骤3: 批量生成并上传

```python
async def process_article_images(article_content: str, cos_config: dict) -> str:
    """
    处理文章中的所有图片占位符
    :param article_content: 原始文章内容
    :param cos_config: COS配置
    :return: 替换后的文章内容
    """
    placeholders = extract_image_placeholders(article_content)

    for alt_text, prompt in placeholders:
        # 1. 调用即梦生成图片 (使用MCP工具)
        # 这里需要通过MCP客户端调用 mcp__jimeng-mcp-server__text_to_image
        image_result = await generate_image_with_jimeng(prompt)

        if image_result and image_result.get("data"):
            image_url = image_result["data"][0]["url"]

            # 2. 下载并上传到COS
            cos_url = await download_and_upload_image(image_url, cos_config)

            # 3. 替换占位符
            old_placeholder = f"![{alt_text}]({{{{IMAGE:{prompt}}}}})"
            new_image_tag = f"![{alt_text}]({cos_url})"
            article_content = article_content.replace(old_placeholder, new_image_tag)

    return article_content
```

### 图片命名规范

最终上传到COS的图片命名格式:

```
image-YYYYMMDD-HHMMSS.png
```

**示例:**
```
image-20251214-143703.png
image-20251214-143715.png
image-20251214-143728.png
```

**完整URL格式:**
```
https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251214-143703.png
```

---

## 文章结构模板

### 第1章: 前言 (三段式,约300字)

#### 第一段: 问题/背景引入 (100-150字)

描述行业痛点或技术趋势,使用对比或反问句引出话题。

**示例:**
```
在AI辅助开发工具快速发展的今天,如何让AI更高效地处理日常开发任务成为了开发者关注的焦点。
传统的开发方式往往需要开发者花费大量时间手动编写重复代码,而效果又难以达到理想水平。
```

#### 第二段: 解决方案介绍 (100-150字)

引入项目/技术名称,说明核心原理,列举关键优势,配图。

**示例:**
```
DeepSeek-OCR 是由 DeepSeek AI 团队推出的开源视觉语言模型,
核心目标是通过"光学压缩"把长文本转化为图像,再将图像压缩为少量视觉token,
实现对超长文本的高效OCR与上下文理解。

![项目架构图]({{IMAGE:技术架构图,DeepSeek-OCR,光学压缩OCR,3D等距视角,蓝色科技风格,简洁专业}})

DeepSeek-OCR 通过光学压缩技术,突破了传统OCR在长文本场景下的瓶颈,
实现10-20倍token压缩,同时保持97%以上识别精度。
```

#### 第三段: 文章目标与亮点 (50-80字)

使用时效性词汇,明确说明实战内容。

**固定句式:**
```
这2天[项目名称]非常火爆,今天我们在[平台]手把手教大家部署这个[项目],
体验和感受一下这个[项目]的能力。
```

---

### 第2章: 项目介绍 (约500字)

#### 核心特性 (列表形式)
```markdown
## ✨ 核心特性

- **🚀 特性1**: 高效处理,10-20倍性能提升
- **🎯 特性2**: 高精度识别,准确率达97%+
- **💰 特性3**: 低成本运行,24GB显存即可
- **🔧 特性4**: 易于部署,Docker一键启动
- **📦 特性5**: 开源免费,社区活跃

![功能演示]({{IMAGE:软件功能演示界面,OCR文字识别,现代UI设计,深色主题,专业感}})
```

#### 技术栈说明 (表格形式)
```markdown
## 🛠️ 技术栈

### 后端
- **框架**: FastAPI / Flask
- **语言**: Python 3.11+
- **推理**: VLLM / TensorRT
- **部署**: Docker

### 前端
- **框架**: Vue 3 / React
- **语言**: TypeScript
- **构建**: Vite
```

#### 应用场景
```markdown
## 🎯 应用场景

- **文档识别**: PDF/图片文档批量OCR识别
- **票据处理**: 发票/收据自动化信息提取
- **表格识别**: 复杂表格结构化数据提取
```

---

### 第3章: 部署实战 (约1500-2000字)

#### 3.1 环境准备

**模板:**
```markdown
## 环境准备

我们首先需要在[平台]开启带有GPU的服务。

在个人主页选择[功能选项],环境镜像选择最新版本。

![环境配置]({{IMAGE:云服务器配置界面,GPU环境选择,终端命令行,技术感,专业}})

启动完成后等待几分钟,看到以下界面说明环境就绪。

![环境就绪]({{IMAGE:服务器启动成功界面,绿色状态指示,终端就绪,清晰展示}})
```

#### 3.2 项目下载

**模板:**
````markdown
## 项目下载

在终端输入以下命令下载项目:

```shell
# 下载到指定目录
git clone https://github.com/xxx/project.git /path/to/dir
cd /path/to/dir
```

![下载进度]({{IMAGE:终端git clone进度界面,代码下载中,进度条显示,技术感}})

等待几分钟后下载完成。

![下载完成]({{IMAGE:终端下载完成界面,绿色成功提示,文件列表显示,清晰}})
````

#### 3.3 依赖安装

**模板:**
````markdown
## 依赖安装

官方测试环境: Python 3.11 + CUDA 12.1

所需依赖:
```python
torch==2.6.0
transformers==4.46.3
fastapi==0.104.1
```

安装命令:
```shell
pip install -r requirements.txt
```

**注意**: 需要修改 numpy 版本为 1.26.4,否则会报错。

![依赖安装]({{IMAGE:终端pip install界面,依赖安装进度,绿色成功提示,技术感}})
````

#### 3.4 配置文件

**模板:**
````markdown
## 配置文件

创建 .env 配置文件:

```shell
touch .env
```

编辑配置内容:
```yaml
API_KEY=your-api-key
BASE_URL=https://api.example.com
MODEL=gpt-4
PORT=8000
```

![配置文件]({{IMAGE:代码编辑器配置文件界面,env环境变量,语法高亮,深色主题}})
````

#### 3.5 启动服务

**模板:**
````markdown
## 启动服务

使用Docker启动:

```shell
docker run -d \
  --name app \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env:ro \
  --restart unless-stopped \
  image:latest
```

![启动命令]({{IMAGE:终端Docker启动命令界面,容器运行,技术感,专业}})

检查运行状态:
```shell
docker logs -f app
```

![运行日志]({{IMAGE:终端Docker日志界面,服务运行状态,绿色正常,清晰}})
````

#### 3.6 测试验证

**模板:**
````markdown
## 测试验证

浏览器访问 http://localhost:8000

![访问首页]({{IMAGE:Web应用首页界面,现代UI设计,深色主题,专业美观}})

输入测试内容:

![功能测试]({{IMAGE:软件功能测试界面,输入框填写,操作演示,清晰直观}})

查看结果:

![测试结果]({{IMAGE:测试结果展示界面,成功标识,数据对比,绿色指示}})

通过对比来看效果不错,基本达到预期。呵呵是不是很简单?
````

---

### 第4章: 总结 (单段300-500字,禁止分段)

**标准模板** (必须严格遵守):

```
今天主要带大家了解并实现了 [项目全称] 的 [核心功能] 完整流程,
该 [项目类型] 以 "[核心技术1 + 核心技术2]" 为核心优势,
结合 [应用场景] 需求,
通过 [技术方案/平台] 与 [工具/框架],
形成了一套从 [起点] 到 [终点] 的全链路 [解决方案类型]。
通过这套实践方案,[用户群体] 能够高效突破 [传统痛点] —— 
借助 [具体操作](包括 [步骤1]、[步骤2]、[步骤3]),
无需 [传统障碍],
就能快速 [核心价值](如本次演示的 "[案例名称]")。
无论是 [功能1]、[功能2],还是 [功能3]、[功能4],
都能通过 [实现方式] 完成,
极大 [提升维度]。
在实际应用中,该 [项目/工具] 不仅 [优势1],还 [优势2],
适配性远优于 [传统方案];
特别是通过 [关键技术点],有效解决了 [具体问题] 的难题。
同时,方案具备良好的扩展性 —— 
小伙伴们可以基于此扩展更多 [应用场景],
如 [场景1]、[场景2]、[场景3] 等,
进一步发挥 [核心价值] 在 [领域1]、[领域2]、[领域3] 等领域的应用价值。
感兴趣的小伙伴可以按照文中提供的步骤进行实践,
根据实际 [需求类型] 调整 [可调整项]。
今天的分享就到这里结束了,我们下一篇文章见。
```

**检查清单:**
- [ ] 单段不分段
- [ ] 300-500字
- [ ] 包含核心技术(引号标注)
- [ ] 列举4+功能
- [ ] 对比传统方案
- [ ] 3+扩展场景
- [ ] 固定结束语

---

## 语言风格规范

### 口语化词汇库

**必用词汇:**
- 问候语: "小伙伴们"、"大家"
- 语气词: "呵呵"、"好家伙"、"话不多说"
- 疑问引导: "是不是非常简单?"、"效果还不错吧?"
- 对话感: "我们接下来..."、"大家可以..."

**时效性标签:**
- "这2天非常火爆"
- "最新推出"
- "今天就带大家..."

**强调词:**
- 实用性: "手把手教"、"全流程"、"一键部署"
- 效果性: "轻松实现"、"极大提升"、"完美解决"

---

## 视觉元素规范

### 图片格式说明

#### 方式一: 自动生成配图(推荐)

使用图片占位符,系统自动生成并上传:

```markdown
![项目架构图]({{IMAGE:技术架构图,{项目名称},{核心技术},3D等距视角,蓝色科技风格}})
```

**处理后变为:**
```markdown
![项目架构图](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251214-143703.png)
```

#### 方式二: 直接使用COS链接

如已有图片,直接使用COS链接:

```markdown
![image-20251110-143703](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110-143703.png)
```

**命名规则**: image-YYYYMMDD-HHMMSS

### 图片占位符类型对照表

| 占位符类型 | prompt模板 | 适用场景 |
|------------|------------|----------|
| `{{IMAGE:架构图,...}}` | 技术架构图,3D等距视角,蓝色科技风格 | 项目介绍章节 |
| `{{IMAGE:界面图,...}}` | 软件界面展示,现代UI设计,深色主题 | 功能演示 |
| `{{IMAGE:终端图,...}}` | 终端命令行界面,技术感,代码高亮 | 环境配置/命令执行 |
| `{{IMAGE:代码图,...}}` | 代码编辑器,语法高亮,专业开发 | 代码展示 |
| `{{IMAGE:结果图,...}}` | 效果展示,成功状态,对比展示 | 测试结果 |
| `{{IMAGE:流程图,...}}` | 流程图,步骤展示,箭头连接,简洁清晰 | 工作流说明 |

### 表格模板

**对比表:**
```markdown
| 特性 | 传统方案 | 新方案 |
|------|----------|--------|
| 效率 | 慢(需2小时) | 快(仅需5分钟) |
| 成本 | 高(¥500) | 低(¥50,省90%) |
| 难度 | 复杂 | 简单 |
```

**配置表:**
```markdown
| 参数 | 说明 | 默认值 | 必填 |
|------|------|--------|------|
| API_KEY | API密钥 | 无 | 是 |
| PORT | 端口号 | 8000 | 否 |
```

---

## 代码块规范

### Shell命令
````markdown
```shell
# 下载项目
git clone https://github.com/xxx/project.git

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```
````

### Python代码
````markdown
```python
# 导入库
from fastapi import FastAPI

# 创建应用
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello"}
```
````

### 配置文件
````markdown
```yaml
# 应用配置
app:
  name: "MyApp"
  port: 8000
  debug: false
```
````

---

## 质量标准

### 合格标准 (必达)
- ✅ 总字数 > 2000字
- ✅ 代码块 >= 5个
- ✅ 截图占位符 >= 8个
- ✅ 对比表格 >= 1个
- ✅ 总结单段 300-500字
- ✅ 固定结束语
- ✅ 资源链接

### 优秀标准 (建议)
- 🌟 总字数 > 3000字
- 🌟 代码块 >= 8个
- 🌟 截图占位符 >= 12个
- 🌟 对比表格 >= 2个
- 🌟 成本/性能分析

---

## 错误避免

### ❌ 禁止
1. 总结分段
2. 学术化语言
3. 省略步骤
4. 缺少截图
5. 遗漏资源

### ✅ 正确
1. 口语化专业
2. 步骤完整
3. 截图充分
4. 代码可用
5. 总结深入

---

## 触发方式

自动触发关键词:
- "小灰灰公众号"
- "技术教程" + "部署"
- "实战" + "手把手"

图片生成触发:
- "自动配图" / "生成配图"
- "图片占位符" + "替换"
- "上传图床"

---

## 图片生成快速参考

### MCP工具调用示例

#### 1. 基础文生图调用

**工具名称:** `mcp__jimeng-mcp-server__text_to_image`

**基础参数:**
```json
{
  "prompt": "图片描述内容",
  "ratio": "16:9",
  "resolution": "2k",
  "model": "jimeng-4.5",
  "sample_strength": 0.5,
  "negative_prompt": "模糊,低质量,文字错误"
}
```

**参数说明:**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| prompt | string | 是 | - | 图片描述,越详细效果越好 |
| ratio | string | 否 | "1:1" | 宽高比: 1:1/4:3/3:4/16:9/9:16/3:2/2:3/21:9 |
| resolution | string | 否 | "2k" | 分辨率: 1k/2k/4k |
| model | string | 否 | jimeng-4.5 | 模型: jimeng-3.0/jimeng-4.5 |
| sample_strength | float | 否 | 0.5 | 创意度: 0.0-1.0,越高越有创意 |
| negative_prompt | string | 否 | "" | 负面提示词,避免生成的内容 |

#### 2. 常用比例与分辨率配置

**宽高比(ratio)对照表:**
| ratio | 说明 | 适用场景 |
|-------|------|----------|
| 1:1 | 正方形 | 头像、图标、社交媒体帖子 |
| 4:3 | 标准横向 | 通用图片、博客配图 |
| 3:4 | 标准竖向 | 人像照片、手机壁纸 |
| 16:9 | 宽屏横向 | 公众号封面、视频封面、Banner |
| 9:16 | 宽屏竖向 | 手机竖屏、短视频封面 |
| 3:2 | 经典横向 | 摄影作品 |
| 2:3 | 经典竖向 | 海报、杂志封面 |
| 21:9 | 超宽屏 | 电影画幅、Banner |

**分辨率(resolution)对照表:**
| resolution | 说明 | 推荐场景 |
|------------|------|----------|
| 1k | 标准分辨率 | 快速预览、网页小图 |
| 2k | 高清分辨率（推荐） | 通用使用、社交媒体、公众号 |
| 4k | 超高清分辨率 | 印刷品、高质量展示 |

#### 3. 完整调用示例

**示例1: 生成项目架构图**
```json
{
  "prompt": "技术架构图,微服务架构设计,包含API网关、服务注册中心、多个微服务模块,3D等距视角,蓝色科技风格,简洁专业,高清,无文字",
  "ratio": "16:9",
  "resolution": "2k",
  "model": "jimeng-4.5",
  "sample_strength": 0.5,
  "negative_prompt": "模糊,低质量,杂乱,文字,中文,英文"
}
```

**示例2: 生成终端界面**
```json
{
  "prompt": "终端命令行界面,黑色背景,绿色代码文字,显示git clone命令执行,进度条,专业技术感,清晰",
  "ratio": "16:9",
  "resolution": "2k",
  "model": "jimeng-4.5",
  "sample_strength": 0.4,
  "negative_prompt": "模糊,低质量,乱码"
}
```

**示例3: 生成软件界面**
```json
{
  "prompt": "现代Web应用界面,深色主题,左侧导航栏,右侧数据展示区,图表和卡片布局,科技感UI设计,专业美观",
  "ratio": "16:9",
  "resolution": "2k",
  "model": "jimeng-4.5",
  "sample_strength": 0.5,
  "negative_prompt": "模糊,低质量,老旧设计"
}
```

---

### 常用Prompt模板大全

#### 1. 项目架构图模板

**基础模板:**
```
技术架构图,{项目名称},{核心组件},3D等距视角,蓝色科技风格,简洁专业,高清,无文字
```

**详细示例:**

| 场景 | Prompt |
|------|--------|
| 微服务架构 | `技术架构图,微服务架构,API网关+服务注册+配置中心+多服务模块,3D等距视角,蓝色渐变背景,简洁专业,高清` |
| AI项目架构 | `AI系统架构图,大模型推理服务,数据输入+模型处理+结果输出,流程箭头连接,紫色科技风,3D立体感` |
| 数据流架构 | `数据流架构图,ETL数据处理,数据采集+清洗+存储+分析,管道连接,蓝绿渐变,清晰直观` |
| 前后端分离 | `前后端分离架构图,Vue前端+FastAPI后端+MySQL数据库,三层结构,蓝色科技风,简洁专业` |
| Docker部署 | `Docker容器部署架构图,多容器编排,网络连接,数据卷挂载,蓝色背景,技术感,清晰` |

#### 2. 功能演示图模板

**基础模板:**
```
软件界面展示,{功能描述},现代UI设计,深色主题,专业感,清晰
```

**详细示例:**

| 场景 | Prompt |
|------|--------|
| OCR识别 | `OCR文字识别界面,左侧图片上传区,右侧识别结果展示,现代UI设计,深色主题,绿色成功提示` |
| 聊天界面 | `AI聊天对话界面,消息气泡布局,用户提问+AI回答,现代简洁设计,深色主题,专业美观` |
| 数据分析 | `数据分析仪表盘,多图表展示,折线图+饼图+柱状图,深色主题,科技感,数据可视化` |
| 文件管理 | `文件管理系统界面,文件列表展示,文件夹树形结构,操作按钮,现代UI,简洁专业` |
| 配置面板 | `系统配置面板界面,表单输入框,开关按钮,下拉选择,分组设置,深色主题,清晰` |

#### 3. 部署环境图模板

**基础模板:**
```
云服务器配置界面,{平台名称},终端命令行,技术感,专业,清晰展示
```

**详细示例:**

| 场景 | Prompt |
|------|--------|
| AutoDL | `AutoDL云服务器控制台,GPU实例列表,显存使用率,运行状态指示,蓝色科技风,专业界面` |
| 阿里云 | `阿里云ECS控制台界面,服务器实例管理,配置信息展示,蓝色主题,简洁专业` |
| Docker | `Docker Desktop界面,容器列表展示,运行状态,端口映射,深色主题,技术感` |
| K8s | `Kubernetes Dashboard界面,Pod状态展示,节点信息,资源监控,蓝色科技风` |
| 终端SSH | `SSH终端连接界面,黑色背景,绿色命令提示符,服务器信息显示,专业技术感` |

#### 4. 代码展示图模板

**基础模板:**
```
代码编辑器界面,{语言}代码,语法高亮,深色主题,VS Code风格
```

**详细示例:**

| 场景 | Prompt |
|------|--------|
| Python代码 | `VS Code编辑器界面,Python代码,语法高亮,深色主题,左侧文件树,底部终端,专业开发环境` |
| 配置文件 | `代码编辑器,YAML配置文件,语法高亮,缩进清晰,深色主题,专业感` |
| API代码 | `代码编辑器界面,FastAPI路由代码,装饰器+函数定义,Python语法高亮,深色主题` |
| Shell脚本 | `终端界面,Shell脚本执行,命令行高亮,绿色成功输出,黑色背景,技术感` |
| JSON数据 | `代码编辑器,JSON数据格式,语法高亮,折叠展开,深色主题,清晰展示` |

#### 5. 效果对比图模板

**基础模板:**
```
{功能}效果对比图,左侧原始右侧结果,成功标识,清晰直观,专业
```

**详细示例:**

| 场景 | Prompt |
|------|--------|
| OCR对比 | `OCR识别效果对比,左侧原始图片,右侧提取文字结果,绿色成功标识,白色背景,清晰直观` |
| 图像处理 | `图像处理效果对比,左侧原图右侧处理后,前后对比箭头,质量提升展示,专业` |
| 性能对比 | `性能对比图表,柱状图展示,优化前后对比,绿色提升标识,数据标注,清晰` |
| 代码优化 | `代码重构对比,左侧旧代码右侧新代码,高亮差异部分,深色主题,专业展示` |
| 部署成功 | `部署成功状态展示,绿色对勾标识,服务运行正常,健康检查通过,专业界面` |

#### 6. 流程图模板

**基础模板:**
```
流程图,{流程描述},步骤节点,箭头连接,简洁清晰,专业
```

**详细示例:**

| 场景 | Prompt |
|------|--------|
| 部署流程 | `部署流程图,环境准备→代码下载→依赖安装→配置→启动→测试,步骤节点,蓝色箭头,简洁专业` |
| 数据处理 | `数据处理流程图,数据输入→预处理→模型推理→后处理→输出,流程箭头,蓝色科技风` |
| CI/CD | `CI/CD流水线流程图,代码提交→构建→测试→部署→监控,自动化流程,蓝绿色调` |
| 用户操作 | `用户操作流程图,注册→登录→使用功能→获取结果,步骤清晰,简洁直观` |

---

### Prompt优化技巧

#### 1. 提升图片质量的关键词

**画质类:**
- `高清` / `4K` / `超清晰`
- `精细细节` / `高质量渲染`
- `专业级` / `商业级品质`

**风格类:**
- `3D等距视角` / `扁平化设计` / `拟物化`
- `科技感` / `未来感` / `现代简约`
- `蓝色调` / `深色主题` / `渐变背景`

**排除类(negative_prompt):**
- `模糊,低质量,噪点`
- `文字,中文,英文,乱码`
- `变形,扭曲,不自然`

#### 2. Prompt结构建议

```
[主体内容] + [细节描述] + [视角/构图] + [风格/色调] + [质量要求]
```

**示例:**
```
技术架构图(主体) + 微服务+API网关+数据库(细节) + 3D等距视角(构图) + 蓝色科技风(风格) + 高清专业(质量)
```

#### 3. 不同场景推荐配置

| 场景 | model | ratio | resolution | sample_strength |
|------|-------|-------|------------|-----------------|
| 架构图 | jimeng-4.5 | 16:9 | 2k | 0.5 |
| 界面图 | jimeng-4.5 | 16:9 | 2k | 0.4 |
| 终端图 | jimeng-4.5 | 16:9 | 2k | 0.3 |
| 流程图 | jimeng-4.5 | 16:9 | 2k | 0.5 |
| 效果对比 | jimeng-4.5 | 16:9 | 2k | 0.4 |
| 高质量图 | jimeng-4.5 | 16:9 | 4k | 0.5 |
| 方形图标 | jimeng-4.5 | 1:1 | 2k | 0.5 |
| 竖版海报 | jimeng-4.5 | 9:16 | 2k | 0.5 |

---

## 更新日志

### v2.1.0 (2025-12-14)
- ✅ 更新即梦MCP接口参数：width/height → ratio/resolution
- ✅ 默认模型升级为 jimeng-4.5
- ✅ 新增更多宽高比支持：3:2/2:3/21:9
- ✅ 优化参数说明和配置表格

### v2.0.0 (2025-12-14)
- ✅ 新增即梦AI自动配图功能
- ✅ 集成腾讯云COS图床上传
- ✅ 图片占位符自动替换为真实URL
- ✅ 支持多种配图类型模板
- ✅ 添加图片生成工作流程文档
- ✅ 内存直接上传,无需本地缓存

### v1.0.0 (2025-11-10)
- ✅ 初始版本
- ✅ 四段式结构
- ✅ 三段式开头
- ✅ 单段式总结
- ✅ 口语化风格
- ✅ 质量标准

---

## 技术支持

参考文档:
- 小灰灰公众号特点.md
- skill创建帮助文档.md

图片生成相关:
- jimeng_mcp_skill/SKILL.md - 即梦MCP技能文档
- jimeng_mcp_skill/references/api_reference.md - 即梦API参考
- cos_utils.py - 腾讯云COS上传工具类

项目链接:
- **即梦MCP服务器**: https://github.com/wwwzhouhui/jimeng-mcp-server
- **即梦后端API**: https://github.com/wwwzhouhui/jimeng-free-api-all
- **腾讯云COS**: https://cloud.tencent.com/product/cos
