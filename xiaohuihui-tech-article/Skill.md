---
name: xiaohuihui-tech-article
description: 专为技术实战教程设计的公众号文章生成器,遵循小灰灰公众号写作规范,自动生成包含公众号卡片、前言、项目介绍、部署实战、总结、往期推荐的完整技术文章,配有详细操作步骤、代码示例,并通过 Gemini-3-Pro-Image-Preview 模型(支持自建API和Gemai公益站双通道)生成配图上传至腾讯云COS图床
version: 2.4.0
---

# 小灰灰技术文章生成器

专业的技术实战教程创作助手,完全遵循小灰灰公众号的写作风格 and 结构规范。**支持 Gemini-3-Pro-Image-Preview 双通道自动配图(自建API + Gemai公益站),一键生成并上传至腾讯云COS图床。** **v2.4.0 新增 Gemai 公益站文生图通道。**

## 核心功能

- ✅ **公众号卡片**: 文章前言上方自动插入作者公众号名片卡片
- ✅ **标准四段式结构**: 公众号卡片 → 前言 → 项目介绍 → 部署实战 → 总结 → 往期推荐
- ✅ **三段式开头**: 问题引入 + 解决方案 + 实战预告
- ✅ **详细实战步骤**: 环境准备 → 依赖安装 → 配置 → 实现 → 测试
- ✅ **单段长句总结**: 300-500字深度总结(必须单段不分段)
- ✅ **往期推荐**: 文章结尾自动附加最新5篇公众号文章链接
- ✅ **口语化技术文**: "呵呵"、"好家伙"、"手把手教"等亲和表达
- ✅ **智能配图生成**: 调用 Gemini-3-Pro-Image-Preview 自动生成配图(双通道)
- ✅ **Gemai 公益站**: 支持 Gemai 公益站 API(api.gemai.cc)作为备用文生图通道
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

1. **Gemini API 配置（双通道,任选其一）**

   **通道一: 自建API（默认）**
   - 访问地址: `http://115.190.165.156:3000/v1/chat/completions`
   - API Key: `sk-LYGZYPL2zZhGcRizHRiZv2nEXsuVHeof7LtTsT4OWwkWCFT0`
   - 模型名称: `gemini-3-pro-image-preview`

   **通道二: Gemai 公益站（备用）**
   - 访问地址: `https://api.gemai.cc/v1/chat/completions`
   - API Key: 通过环境变量 `GEMAI_API_KEY` 或命令行 `--api-key` 参数提供
   - 模型名称: `gemini-3-pro-image-preview`
   - 特点: 公网可达,无需自建服务,支持 OpenAI 标准格式
   - 工具类: `gemai_image_generator.py` (GemaiImageGenerator)

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
调用 Gemini API → 获取 base64 图片数据 → 解码图片
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

#### 2. Gemini API 调用

使用 `gemini-3-pro-image-preview` 模型生成图片,支持两种调用方式:

**方式一: 自建API调用**

```json
{
  "model": "gemini-3-pro-image-preview",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "技术架构图,DeepSeek-OCR光学压缩技术,Python FastAPI VLLM推理引擎,3D等距视角,蓝色科技风格,简洁专业,高清"
        }
      ]
    }
  ]
}
```

**方式二: Gemai 公益站调用（OpenAI 标准格式）**

```json
{
  "model": "gemini-3-pro-image-preview",
  "messages": [
    {
      "role": "user",
      "content": "技术架构图,DeepSeek-OCR光学压缩技术,Python FastAPI VLLM推理引擎,3D等距视角,蓝色科技风格,简洁专业,高清"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 4096
}
```

**Gemai API 请求头:**
```
Content-Type: application/json
Authorization: Bearer <你的GEMAI_API_KEY>
```

**参数说明:**
- `model`: 必须为 `gemini-3-pro-image-preview`
- `content`: 图片描述文本(自建API为数组格式,Gemai为字符串格式均可)
- `temperature`: 创造性程度 0.0-1.0（Gemai通道可选,默认0.7）
- `max_tokens`: 最大令牌数（Gemai通道可选,默认4096）

#### 3. 图片生成与处理

支持两种生成器,根据网络环境选择:

**方式一: 使用 GeminiImageGenerator（自建API）**

使用 `gemini_image_generator.py` 中的 `GeminiImageGenerator` 类进行生成与上传:

```python
from gemini_image_generator import GeminiImageGenerator
import os

# 初始化生成器
generator = GeminiImageGenerator()

def generate_and_get_url(prompt: str) -> str:
    """
    生成图片并直接上传到COS,返回永久访问URL
    :param prompt: 图片描述
    :return: COS永久访问URL
    """
    return generator.generate_and_upload(prompt)

# 使用示例
# cos_url = generate_and_get_url("技术架构图,DeepSeek-OCR,3D等距视角,蓝色科技风格")
# 返回: https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251214-143703.png
```

**方式二: 使用 GemaiImageGenerator（Gemai公益站）**

使用 `gemai_image_generator.py` 中的 `GemaiImageGenerator` 类,通过 Gemai 公益站 API 生成图片:

```python
from gemai_image_generator import GemaiImageGenerator
from cos_utils import TencentCOSUploader
import base64
import re
import os
from datetime import datetime

# 初始化 Gemai 生成器（API Key 从环境变量或参数传入）
gemai_generator = GemaiImageGenerator(
    api_key=os.getenv("GEMAI_API_KEY"),
    base_url="https://api.gemai.cc"
)

# 初始化 COS 上传器
cos_uploader = TencentCOSUploader(
    region=os.getenv("COS_REGION", "ap-nanjing"),
    secret_id=os.getenv("COS_SECRET_ID"),
    secret_key=os.getenv("COS_SECRET_KEY"),
    bucket=os.getenv("COS_BUCKET", "mypicture-1258720957")
)

def gemai_generate_and_upload(prompt: str, style: str = None, aspect_ratio: str = None) -> str:
    """
    使用 Gemai 公益站生成图片并上传到 COS
    :param prompt: 图片描述
    :param style: 图片风格(realistic/anime/oil-painting/watercolor/sketch)
    :param aspect_ratio: 宽高比(1:1/16:9/9:16/4:3/3:4)
    :return: COS永久访问URL 或 None
    """
    kwargs = {}
    if style:
        kwargs["style"] = style
    if aspect_ratio:
        kwargs["aspect_ratio"] = aspect_ratio

    # 1. 调用 Gemai API 生成图片
    result = gemai_generator.generate_image(prompt=prompt, **kwargs)

    # 2. 从响应中提取 base64 图片数据
    image_data = _extract_base64_from_response(result)
    if not image_data:
        return None

    # 3. 解码并上传到 COS
    image_bytes = base64.b64decode(image_data)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_name = f"image-{timestamp}.png"

    upload_result = cos_uploader.upload_from_memory(image_bytes, file_name)
    if upload_result.get("success"):
        return upload_result["url"]
    return None

def _extract_base64_from_response(result: dict) -> str:
    """从 Gemai API 响应中提取 base64 图片数据"""
    if "choices" not in result:
        return None

    for choice in result["choices"]:
        content = choice.get("message", {}).get("content", "")
        if isinstance(content, str):
            # 尝试 Markdown 格式: ![image](data:image/png;base64,...)
            pattern = r'data:image/[^;]+;base64,([A-Za-z0-9+/=\n\r]+)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).replace('\n', '').replace('\r', '').strip()
    return None

# 使用示例
# cos_url = gemai_generate_and_upload("技术架构图,DeepSeek-OCR,3D等距视角,蓝色科技风格")
# cos_url = gemai_generate_and_upload("软件界面展示", style="realistic", aspect_ratio="16:9")
```

**双通道自动切换策略:**

```python
def generate_image_with_fallback(prompt: str, **kwargs) -> str:
    """
    双通道自动切换: 优先自建API,失败时回退到 Gemai 公益站
    :return: COS永久访问URL
    """
    # 通道一: 自建API
    try:
        url = generate_and_get_url(prompt)
        if url:
            return url
    except Exception as e:
        print(f"自建API失败: {e}, 切换到 Gemai 公益站...")

    # 通道二: Gemai 公益站
    try:
        url = gemai_generate_and_upload(prompt, **kwargs)
        if url:
            return url
    except Exception as e:
        print(f"Gemai 公益站也失败: {e}")

    return None
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
from gemini_image_generator import GeminiImageGenerator

# 初始化生成器(方式一: 自建API)
generator = GeminiImageGenerator()

# 或使用方式二: Gemai 公益站
# from gemai_image_generator import GemaiImageGenerator
# gemai_gen = GemaiImageGenerator(
#     api_key="sk-5Tgi5fdeaCfonclflYenie6XHaoXwNdrRoFal5bqWlCXe7ST",
#     base_url="https://api.gemai.cc"
# )

def process_article_images(article_content: str, use_gemai: bool = False) -> str:
    """
    处理文章中的所有图片占位符
    :param article_content: 原始文章内容
    :param use_gemai: 是否使用 Gemai 公益站(默认False使用自建API)
    :return: 替换后的文章内容
    """
    placeholders = extract_image_placeholders(article_content)

    for alt_text, prompt in placeholders:
        if use_gemai:
            # 使用 Gemai 公益站生成
            cos_url = gemai_generate_and_upload(prompt)
        else:
            # 使用自建API生成
            cos_url = generator.generate_and_upload(prompt)

        if cos_url:
            # 替换占位符
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

### 公众号卡片 (文章最顶部,前言之前)

在文章正文最开头、前言之前,**必须**插入作者公众号名片卡片。直接在 Markdown 文件中输出以下 HTML 代码,渲染出可视化的公众号名片效果:

**HTML 卡片代码（每篇文章必须在最顶部原样输出）:**

```html
<section style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 16px 0; display: flex; align-items: center; background: #fff;">
  <img src="{{AVATAR_URL}}" style="width: 48px; height: 48px; border-radius: 50%; margin-right: 12px; object-fit: cover;" />
  <div style="flex: 1;">
    <div style="font-size: 16px; font-weight: bold; color: #333;">海老豹666</div>
    <div style="font-size: 13px; color: #888; margin-top: 4px;">科技、管理、经济、学习、成长等文章</div>
    <div style="font-size: 12px; color: #aaa; margin-top: 2px;">207篇原创内容</div>
  </div>
  <span style="font-size: 12px; color: #576b95; white-space: nowrap;">公众号</span>
</section>
```

**公众号卡片固定参数:**

| 参数 | 值 | 说明 |
|------|------|------|
| 头像 | {{AVATAR_URL}} | 公众号头像图片地址(用户提供后替换) |
| 名称 | 海老豹666 | 公众号名称 |
| 简介 | 科技、管理、经济、学习、成长等文章 | 公众号简介 |
| 原创数 | 207篇原创内容 | 原创文章数量 |

**使用规则:**
1. 卡片必须放在文章正文最顶部,前言标题之前
2. 卡片与前言标题之间空一行
3. 每篇文章只需一个公众号卡片
4. 直接输出上述 HTML 代码,**不要**使用 `{{ACCOUNT_CARD}}` 之类的占位符
5. HTML 代码必须原样输出,不要修改样式或结构

**文章开头示例:**
```markdown
<section style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 16px 0; display: flex; align-items: center; background: #fff;">
  <img src="{{AVATAR_URL}}" style="width: 48px; height: 48px; border-radius: 50%; margin-right: 12px; object-fit: cover;" />
  <div style="flex: 1;">
    <div style="font-size: 16px; font-weight: bold; color: #333;">海老豹666</div>
    <div style="font-size: 13px; color: #888; margin-top: 4px;">科技、管理、经济、学习、成长等文章</div>
    <div style="font-size: 12px; color: #aaa; margin-top: 2px;">207篇原创内容</div>
  </div>
  <span style="font-size: 12px; color: #576b95; white-space: nowrap;">公众号</span>
</section>

# 1.前言

在AI辅助开发工具快速发展的今天...
```

---

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
就能快速 [核心价值](如本次演示 of "[案例名称]")。
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

### 第5章: 往期推荐 (文章结尾,总结之后)

在总结段落结束后,**必须**附加最新5篇公众号往期文章链接,供读者延伸阅读。

**格式规范:**

```markdown
[文章标题1](文章链接1)
[文章标题2](文章链接2)
[文章标题3](文章链接3)
[文章标题4](文章链接4)
[文章标题5](文章链接5)
```

**当前最新5篇文章列表 (按时间倒序):**

```markdown
[99元/年！腾讯云部署OpenClaw，手把手教你打造7×24小时AI私人助手](https://mp.weixin.qq.com/s/jIM4d36W3vz6PaWnpLlrUQ)
[1分钱部署私人AI助手！百度云OpenClaw极速版，3分钟搞定零代码](https://mp.weixin.qq.com/s/CdZqi-9O835g8QDuMGuAAg)
[2026年2月炸场！手把手教你Docker一键部署Seedance 2.0双模型Web应用](https://mp.weixin.qq.com/s/zOiVLL31ib7ZVCTTzz8mQA)
[字节Seedance 2.0炸场！3张图+一句话，小白秒变视频导演](https://mp.weixin.qq.com/s?__biz=Mzg3OTYzMjc1NQ==&mid=2247491362&idx=1&sn=70db14b15fa5bae811aaaf46e368c9c7&scene=21#wechat_redirect)
[2天10万Star！GitHub史上最快开源项目OpenClaw，手把手教你免费实现部署私人AI助手](https://mp.weixin.qq.com/s?__biz=Mzg3OTYzMjc1NQ==&mid=2247491335&idx=1&sn=6a0cb2ca20fea7d3419495bd61fdd6ea&scene=21#wechat_redirect)
```

**使用规则:**
1. 总结段落结束后空一行,直接排列文章链接
2. 每篇链接独占一行,使用 Markdown 链接格式
3. 链接按发布时间倒序排列(最新的在最前)
4. 固定5篇,不多不少
5. 当有新文章发布时,更新此列表:移除最旧的一篇,在列表最前添加最新一篇
6. 链接文字为文章完整标题,不要缩写

**完整文章结尾示例:**

```markdown
...感兴趣的小伙伴可以按照文中提供的步骤进行实践,
根据实际使用场景调整模型选择和通道配置。今天的分享就到这里结束了,我们下一篇文章见。

[99元/年！腾讯云部署OpenClaw，手把手教你打造7×24小时AI私人助手](https://mp.weixin.qq.com/s/jIM4d36W3vz6PaWnpLlrUQ)
[1分钱部署私人AI助手！百度云OpenClaw极速版，3分钟搞定零代码](https://mp.weixin.qq.com/s/CdZqi-9O835g8QDuMGuAAg)
[2026年2月炸场！手把手教你Docker一键部署Seedance 2.0双模型Web应用](https://mp.weixin.qq.com/s/zOiVLL31ib7ZVCTTzz8mQA)
[字节Seedance 2.0炸场！3张图+一句话，小白秒变视频导演](https://mp.weixin.qq.com/s?__biz=Mzg3OTYzMjc1NQ==&mid=2247491362&idx=1&sn=70db14b15fa5bae811aaaf46e368c9c7&scene=21#wechat_redirect)
[2天10万Star！GitHub史上最快开源项目OpenClaw，手把手教你免费实现部署私人AI助手](https://mp.weixin.qq.com/s?__biz=Mzg3OTYzMjc1NQ==&mid=2247491335&idx=1&sn=6a0cb2ca20fea7d3419495bd61fdd6ea&scene=21#wechat_redirect)
```

**检查清单:**
- [ ] 总结段落后有往期推荐
- [ ] 恰好5篇文章链接
- [ ] 按时间倒序排列
- [ ] 链接格式正确可点击
- [ ] 标题完整无缩写

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
- ✅ 文章顶部有公众号名片卡片（HTML 格式）
- ✅ 总字数 > 2000字
- ✅ 代码块 >= 5个
- ✅ 截图占位符 >= 8个
- ✅ 对比表格 >= 1个
- ✅ 总结单段 300-500字
- ✅ 固定结束语
- ✅ 资源链接
- ✅ 文章结尾有5篇往期推荐链接

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
6. 缺少公众号卡片
7. 缺少往期推荐链接

### ✅ 正确
1. 口语化专业
2. 步骤完整
3. 截图充分
4. 代码可用
5. 总结深入
6. 文章顶部有公众号卡片
7. 文章结尾有5篇往期推荐

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

### Gemini API 调用示例

#### 1. 基础文生图调用

**模型名称:** `gemini-3-pro-image-preview`

**通道一: 自建API 基础参数:**
```json
{
  "model": "gemini-3-pro-image-preview",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "图片描述内容"
        }
      ]
    }
  ]
}
```

**通道二: Gemai 公益站基础参数:**
```json
{
  "model": "gemini-3-pro-image-preview",
  "messages": [
    {
      "role": "user",
      "content": "图片描述内容"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 4096
}
```

**Gemai 公益站命令行调用:**
```shell
# 方式一: 通过环境变量设置 API Key（推荐）
export GEMAI_API_KEY="你的API密钥"
python gemai_image_generator.py --prompt "技术架构图,DeepSeek-OCR,3D等距视角,蓝色科技风格"

# 方式二: 通过命令行参数传入 API Key
python gemai_image_generator.py --api-key "你的API密钥" --prompt "技术架构图"

# 指定输出文件
python gemai_image_generator.py --prompt "软件界面展示,OCR识别,现代UI" -o demo.png

# 指定风格和宽高比
python gemai_image_generator.py --prompt "技术架构图" --style realistic --aspect-ratio 16:9

# 生成多张图片
python gemai_image_generator.py --prompt "代码编辑器界面" --num-images 3 -o code.png

# 使用负向提示词
python gemai_image_generator.py --prompt "服务器配置界面" --negative "blurry, low quality"
```

**参数说明（双通道通用）:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model | string | 是 | 必须为 `gemini-3-pro-image-preview` |
| text | string | 是 | 图片描述,越详细效果越好 |
| ratio | string | 否 | "1:1" | 宽高比: 1:1/4:3/3:4/16:9/9:16/3:2/2:3/21:9 |
| resolution | string | 否 | "2k" | 分辨率: 1k/2k/4k |
| temperature | float | 否 | Gemai通道专属,创造性程度 0.0-1.0(默认0.7) |
| max_tokens | int | 否 | Gemai通道专属,最大令牌数(默认4096) |
| n | int | 否 | Gemai通道专属,生成图片数量 1-4(默认1) |
| style | string | 否 | Gemai通道专属,风格: realistic/anime/oil-painting/watercolor/sketch |

#### Gemai 公益站额外功能

| 功能 | 说明 |
|------|------|
| 批量生成 | 支持一次生成1-4张图片(`--num-images`) |
| 负向提示词 | 排除不想要的内容(`--negative`) |
| 风格控制 | 5种预设风格(realistic/anime/oil-painting/watercolor/sketch) |
| 宽高比 | 5种常用比例(1:1/16:9/9:16/4:3/3:4) |
| 创造力调节 | temperature参数控制生成多样性 |

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

---

## 更新日志

### v2.4.0 (2026-02-23)
- ✅ 新增 Gemai 公益站(api.gemai.cc)作为备用文生图通道
- ✅ 新增 `gemai_image_generator.py` 工具类,支持 OpenAI 标准格式调用
- ✅ 支持双通道自动切换策略(自建API优先,失败回退Gemai公益站)
- ✅ Gemai通道支持批量生成(1-4张)、负向提示词、风格控制、宽高比
- ✅ 新增命令行调用方式,支持 `python gemai_image_generator.py` 直接生成图片
- ✅ 更新图片生成文档,补充双通道调用示例和参数说明

### v2.3.1 (2026-02-23)
- ✅ 公众号卡片从 `{{ACCOUNT_CARD}}` 占位符升级为 HTML 可视化名片卡片
- ✅ 卡片在 Markdown 文件中直接渲染，无需手动替换
- ✅ 样式参考微信公众号原生名片效果（圆形头像、名称、简介、原创数、公众号标签）

### v2.3.0 (2026-02-23)
- ✅ 新增公众号卡片功能：文章前言上方自动插入作者公众号名片（`{{ACCOUNT_CARD}}` 占位符）
- ✅ 新增往期推荐功能：文章结尾自动附加最新5篇公众号文章链接
- ✅ 文章结构升级为：公众号卡片 → 前言 → 项目介绍 → 部署实战 → 总结 → 往期推荐
- ✅ 更新质量标准检查清单，增加卡片和往期推荐的校验项

### v2.2.0 (2026-01-05)
- ✅ 将图片生成模型从即梦 (jimeng-mcp-server) 更换为 Gemini-3-Pro-Image-Preview
- ✅ 新增 `gemini_image_generator.py` 封装 API 调用与 COS 上传逻辑
- ✅ 优化图片占位符替换流程，支持 base64 直接解码上传
- ✅ 更新文档中的 API 调用示例和 Prompt 模板

### v2.1.0 (2025-12-14)
- ✅ 更新即梦MCP接口参数：width/height → ratio/resolution
- ✅ 默认模型升级为 jimeng-4.5

### v2.0.0 (2025-12-14)
- ✅ 新增即梦AI自动配图功能
- ✅ 集成腾讯云COS图床上传

---

## 技术支持

参考文档:
- 小灰灰公众号特点.md
- skill创建帮助文档.md

图片生成相关:
- gemini_image_generator.py - Gemini 图片生成与上传工具类(自建API通道)
- gemai_image_generator.py - Gemai 公益站图片生成工具类(备用通道,api.gemai.cc)
- cos_utils.py - 腾讯云COS上传工具类

项目链接:
- **Gemini API(自建)**: http://115.190.165.156:3000/
- **Gemai 公益站**: https://api.gemai.cc/
- **腾讯云COS**: https://cloud.tencent.com/product/cos
