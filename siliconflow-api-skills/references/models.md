# Siliconflow - Models

**Pages:** 23

---

## 这里选择代理模型类依赖安装

**URL:** llms-txt#这里选择代理模型类依赖安装

**Contents:**
  - 3.3 配置基础的环境变量

pip install -e ".[proxy]"
bash  theme={null}

**Examples:**

Example 1 (unknown):
```unknown
### 3.3 配置基础的环境变量
```

---

## 使用 SiliconFlow 的代理模型

**URL:** llms-txt#使用-siliconflow-的代理模型

LLM_MODEL=siliconflow_proxyllm

---

## 配置具体使用的模型名称

**URL:** llms-txt#配置具体使用的模型名称

SILICONFLOW_MODEL_VERSION=Qwen/Qwen2.5-Coder-32B-Instruct
SILICONFLOW_API_BASE=https://api.siliconflow.cn/v1

---

## 配置使用 SiliconFlow 的 Embedding 模型

**URL:** llms-txt#配置使用-siliconflow-的-embedding-模型

EMBEDDING_MODEL=proxy_http_openapi
PROXY_HTTP_OPENAPI_PROXY_SERVER_URL=https://api.siliconflow.cn/v1/embeddings

---

## 配置具体的 Embedding 模型名称

**URL:** llms-txt#配置具体的-embedding-模型名称

PROXY_HTTP_OPENAPI_PROXY_BACKEND=BAAI/bge-large-zh-v1.5

---

## 配置使用 SiliconFlow 的 rerank 模型

**URL:** llms-txt#配置使用-siliconflow-的-rerank-模型

RERANK_MODEL=rerank_proxy_siliconflow
RERANK_PROXY_SILICONFLOW_PROXY_SERVER_URL=https://api.siliconflow.cn/v1/rerank

---

## 配置具体的 rerank 模型名称

**URL:** llms-txt#配置具体的-rerank-模型名称

**Contents:**
  - 3.5 启动 DB-GPT 服务
- 4.通过 DB-GPT Python SDK 使用 SiliconFlow  的模型
  - 4.1  安装 DB-GPT Python 包
  - 4.2. 使用 SiliconFlow  的大语言模型
  - 4.3 使用 SiliconFlow 的 Embedding 模型
  - 4.4 使用 SiliconFlow 的 rerank 模型
- 5. 上手指南
  - 1. 添加数据源
  - 2. 选择对话类型
  - 3. 开始数据对话

RERANK_PROXY_SILICONFLOW_PROXY_BACKEND=BAAI/bge-reranker-v2-m3
bash  theme={null}
dbgpt start webserver --port 5670
bash  theme={null}
pip install "dbgpt>=0.6.3rc2" openai requests numpy
python  theme={null}
import asyncio
import os
from dbgpt.core import ModelRequest
from dbgpt.model.proxy import SiliconFlowLLMClient

model = "Qwen/Qwen2.5-Coder-32B-Instruct"
client = SiliconFlowLLMClient(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    model_alias=model
)

res = asyncio.run(
    client.generate(
        ModelRequest(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个乐于助人的 AI 助手。"},
                {"role": "human", "content": "你好"},
            ]
        )
    )
)
print(res)
python  theme={null}
import os
from dbgpt.rag.embedding import OpenAPIEmbeddings

openai_embeddings = OpenAPIEmbeddings(
    api_url="https://api.siliconflow.cn/v1/embeddings",
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    model_name="BAAI/bge-large-zh-v1.5",
)

texts = ["Hello, world!", "How are you?"]
res = openai_embeddings.embed_documents(texts)
print(res)
python  theme={null}
import os
from dbgpt.rag.embedding import SiliconFlowRerankEmbeddings

embedding = SiliconFlowRerankEmbeddings(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    model_name="BAAI/bge-reranker-v2-m3",
)
res = embedding.predict("Apple", candidates=["苹果", "香蕉", "水果", "蔬菜"])
print(res)
```

以数据对话案例为例，数据对话能力是通过自然语言与数据进行对话，目前主要是结构化与半结构化数据的对话，可以辅助做数据分析与洞察。以下为具体操作流程：

首先选择左侧数据源添加，添加数据库，目前DB-GPT支持多种数据库类型。选择对应的数据库类型添加即可。这里我们选择的是MySQL作为演示，演示的测试数据参见测试样例（[https://github.com/eosphoros-ai/DB-GPT/tree/main/docker/examples/sqls）。](https://github.com/eosphoros-ai/DB-GPT/tree/main/docker/examples/sqls）。)

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=5b6392f41c8cead1dd4fff26c708124d" data-og-width="1080" width="1080" data-og-height="898" height="898" data-path="images/usercases/db-gpt/image_1.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?w=280&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=e27c445a08f746daa58478eb1e0d5546 280w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?w=560&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=bd3da2b01beedea0b6aff80d6ecae524 560w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?w=840&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=cf043949cd7dc84054d104c31a2ab9be 840w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?w=1100&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=2f00641f6f476200afc616a559ded492 1100w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?w=1650&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=f810211af996130727703850a2159c27 1650w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_1.png?w=2500&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=dfdb60313546156c7ff4cbd2e42468f9 2500w" />
</Frame>

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=62ad4e41f80b6aa593a58d43eef01caf" data-og-width="1080" width="1080" data-og-height="868" height="868" data-path="images/usercases/db-gpt/image_2.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?w=280&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=ad432cccd09ca0e12bda5da6a9936e24 280w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?w=560&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=64ae008d0e9e055e2e374971b2244c56 560w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?w=840&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=5d51c25177a40ee7ab75b105e6bf674b 840w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?w=1100&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=1f382ea48eaf7844e88eaf13d979d813 1100w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?w=1650&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=ad29bdf13ffc6b80c0f88f91c3316d1e 1650w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_2.png?w=2500&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=d97fb20171b1e3d1702cc0b4a71ccee0 2500w" />
</Frame>

注意：在对话时，选择对应的模型与数据库。同时DB-GPT也提供了预览模式与编辑模式。

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=77a3a291ed5f02c2cb7cf61d06605bfd" data-og-width="1080" width="1080" data-og-height="765" height="765" data-path="images/usercases/db-gpt/image_3.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?w=280&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=53f2fd91cc07b38d96d70f80f1cae484 280w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?w=560&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=3e6b86380eb1ac532e043dab96ab2222 560w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?w=840&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=15ba2ecd26cada58464a40e91292f088 840w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?w=1100&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=17c75f07f9689c79cbc20ed2c36c4ae1 1100w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?w=1650&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=98b8372097f84d88cb42f9f6e794f249 1650w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_3.png?w=2500&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=0ae9248d0da8c139bf2133f12dcc5f26 2500w" />
</Frame>

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=0e1ba1cc08b14644f931d219e67039f4" data-og-width="1080" width="1080" data-og-height="521" height="521" data-path="images/usercases/db-gpt/image_4.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?w=280&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=cda9ba01de955da9d2a7ed2990f7e489 280w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?w=560&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=12d538b4563c0c6d100be8ee72987848 560w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?w=840&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=d84a8e288e821dcb851e1ee059b7e931 840w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?w=1100&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=1c8c475c29d8701e8b46f705f62c50ea 1100w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?w=1650&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=f1f2deb90353a841633c0cf4adb91178 1650w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/db-gpt/image_4.png?w=2500&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=343538dfc7060f05f50709a5b52c4de4 2500w" />
</Frame>

**Examples:**

Example 1 (unknown):
```unknown
注意，上述的 `SILICONFLOW_API_KEY`、 `PROXY_HTTP_OPENAPI_PROXY_SERVER_URL` 和`RERANK_PROXY_SILICONFLOW_PROXY_API_KEY`环境变量是您在步骤 2 中获取的 SiliconFlow 的 Api Key。语言模型（`SILICONFLOW_MODEL_VERSION`)、 Embedding 模型（`PROXY_HTTP_OPENAPI_PROXY_BACKEND`）和 rerank 模型(`RERANK_PROXY_SILICONFLOW_PROXY_BACKEND`) 可以从 [获取用户模型列表 - SiliconFlow](https://docs.siliconflow.cn/api-reference/models/get-model-list)  中获取。

### 3.5 启动 DB-GPT 服务
```

Example 2 (unknown):
```unknown
在浏览器打开地址 [http://127.0.0.1:5670/](http://127.0.0.1:5670/) 即可访问部署好的 DB-GPT

## 4.通过 DB-GPT Python SDK 使用 SiliconFlow  的模型

### 4.1  安装 DB-GPT Python 包
```

Example 3 (unknown):
```unknown
为了后续验证，额外安装相关依赖包。

### 4.2. 使用 SiliconFlow  的大语言模型
```

Example 4 (unknown):
```unknown
### 4.3 使用 SiliconFlow 的 Embedding 模型
```

---

## FastGPT

**URL:** llms-txt#fastgpt

**Contents:**
- 2. 修改 FastGPT 环境变量

Source: https://docs.siliconflow.cn/cn/usercases/use-siliconcloud-in-fastgpt

<Note>
  本文转载自 [FastGPT](https://fastgpt.run) 的官方文档，介绍了如何在 FastGPT 中使用 SiliconFlow 的模型。[原文地址](https://doc.tryfastgpt.ai/docs/development/modelconfig/siliconcloud/)
</Note>

[SiliconFlow](https://cloud.siliconflow.cn/i/TR9Ym0c4) 是一个以提供开源模型调用为主的平台，并拥有自己的加速引擎。帮助用户低成本、快速的进行开源模型的测试和使用。实际体验下来，他们家模型的速度和稳定性都非常不错，并且种类丰富，覆盖语言、向量、重排、TTS、STT、绘图、视频生成模型，可以满足 FastGPT 中所有模型需求。

如果你想部分模型使用 SiliconFlow 的模型，可额外参考[OneAPI接入硅基流动](https://doc.tryfastgpt.ai/docs/development/modelconfig/one-api/#%E7%A1%85%E5%9F%BA%E6%B5%81%E5%8A%A8--%E5%BC%80%E6%BA%90%E6%A8%A1%E5%9E%8B%E5%A4%A7%E5%90%88%E9%9B%86)。

本文会介绍完全使用 SiliconFlow SiliconFlow 账号

1. [点击注册硅基流动账号](https://cloud.siliconflow.cn/i/TR9Ym0c4)
2. 进入控制台，获取 API key: [https://cloud.siliconflow.cn/account/ak](https://cloud.siliconflow.cn/account/ak)

## 2. 修改 FastGPT 环境变量

```bash  theme={null}
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

---

## MindSearch

**URL:** llms-txt#mindsearch

**Contents:**
- 1. 获取 API Key
- 2. 部署MindSearch

Source: https://docs.siliconflow.cn/cn/usercases/use-siliconcloud-in-mindsearch

1. 打开 SiliconFlow [官网](https://cloud.siliconflow.cn/) 并注册账号（如果注册过，直接登录即可）。
2. 完成注册后，打开[API密钥](https://cloud.siliconflow.cn/account/ak) ，创建新的 API Key，点击密钥进行复制，以备后续使用。

1. 复制 MindSearch 到本地并安装相关依赖后（参考 [https://github.com/InternLM/MindSearch/blob/main/README.md）](https://github.com/InternLM/MindSearch/blob/main/README.md）) ，

2. 修改：
   `/path/to/MindSearch/mindsearch/models.py`

3. 加上调用硅基流动 API 的相关配置。配置如下：

加入这段配置后，可以执行相关指令来启动 MindSearch。

**Examples:**

Example 1 (unknown):
```unknown
internlm_silicon = dict(type=GPTAPI,
                        model_type='internlm/internlm2_5-7b-chat',
                        key=os.environ.get('SILICON_API_KEY', 'YOUR SILICON API KEY'),
                        openai_api_base='https://api.siliconflow.cn/v1/chat/completions',
                        meta_template=[
                            dict(role='system', api_role='system'),
                            dict(role='user', api_role='user'),
                            dict(role='assistant', api_role='assistant'),
                            dict(role='environment', api_role='system')
                        ],
                        top_p=0.8,
                        top_k=1,
                        temperature=0,
                        max_new_tokens=8192,
                        repetition_penalty=1.02,
                        stop_words=['<|im_end|>'])
```

---

## Global LLM configuration

**URL:** llms-txt#global-llm-configuration

[llm]
model = "Qwen/QwQ-32B" # 或者平台中的其他支持 function calling 模型，参见[Function Calling](https://docs.siliconflow.cn/cn/userguide/guides/function-calling)
base_url = "https://api.siliconflow.cn/v1"
api_key = "your_api_key_from_siliconcloud"
max_tokens = 16384
temperature = 0.6

---

## Optional configuration for specific LLM models

**URL:** llms-txt#optional-configuration-for-specific-llm-models

**Contents:**
- 3. 使用 OpenManus
  - 3.1 下面是某次运行的大致流程：
  - 3.2 执行日志

[llm.vision]
model = "Qwen/Qwen2-VL-72B-Instruct" # 或者平台中的其他视觉语言模型，参见[vision](https://docs.siliconflow.cn/cn/userguide/capabilities/vision)
base_url = "https://api.siliconflow.cn/v1"
api_key = "your_api_key_from_siliconcloud"
shell  theme={null}
python main.py

<tool_call>
    "name": "google_search",
    "arguments": {
      "query": "global soybean market analysis 2025 report",
      "num_results": 10
    }
  </tool_call>
  ```

如需查看详细结果，请[参见此处链接](https://raw.githubusercontent.com/siliconflow/siliconcloud-cookbook/refs/heads/main/examples/openmanus/30-step-log.txt)
</Accordion>

**Examples:**

Example 1 (unknown):
```unknown
## 3. 使用 OpenManus

通过命令行
```

Example 2 (unknown):
```unknown
### 3.1 下面是某次运行的大致流程：

| 步骤 | 工作内容                | 使用工具            | 输入/参数                                              | 输出/结果         |
| -- | ------------------- | --------------- | -------------------------------------------------- | ------------- |
| 1  | 分析用户需求，确定搜索策略       | google\_search  | "global soybean market analysis 2025 report"       | 搜索结果链接列表      |
| 2  | 分析搜索结果，决定使用中文搜索     | google\_search  | "全球大豆市场 2025 年分析报告"                                | 搜索结果链接列表      |
| 3  | 分析中文搜索结果，决定访问USDA网站 | browser\_use    | action: "navigate", url: USDA网站链接                  | 成功导航到USDA网站   |
| 4  | 获取USDA网站HTML内容      | browser\_use    | action: "get\_html"                                | 网页HTML内容      |
| 5  | 分析HTML内容，决定保存数据     | file\_saver     | 保存HTML内容到文件                                        | 成功保存HTML文件    |
| 6  | 分析如何处理HTML数据        | -               | -                                                  | 思考处理HTML的策略   |
| 7  | 编写Python脚本解析HTML数据  | python\_execute | 解析HTML的Python代码                                    | 解析结果（大豆产量数据）  |
| 8  | 分析解析结果，决定获取更多数据     | browser\_use    | action: "navigate", url: FAO网站链接                   | 成功导航到FAO网站    |
| 9  | 获取FAO网站HTML内容       | browser\_use    | action: "get\_html"                                | 网页HTML内容      |
| 10 | 编写Python脚本解析FAO数据   | python\_execute | 解析FAO数据的Python代码                                   | 解析结果（FAO大豆数据） |
| 11 | 编写Python脚本合并数据      | python\_execute | 合并USDA和FAO数据的代码                                    | 合并后的数据集       |
| 12 | 编写Python脚本生成图表      | python\_execute | 生成图表的Python代码                                      | 生成的图表数据       |
| 13 | 保存生成的图表             | file\_saver     | 保存图表数据到文件                                          | 成功保存图表文件      |
| 14 | 搜索气候变化对大豆影响         | google\_search  | "climate change impact on soybean production 2025" | 搜索结果链接列表      |
| 15 | 访问气候变化研究网站          | browser\_use    | action: "navigate", url: 气候研究网站链接                  | 成功导航到气候研究网站   |
| 16 | 获取气候研究网站HTML        | browser\_use    | action: "get\_html"                                | 网页HTML内容      |
| 17 | 编写Python脚本分析气候数据    | python\_execute | 分析气候数据的Python代码                                    | 气候影响分析结果      |
| 18 | 编写Python脚本整合所有数据    | python\_execute | 整合所有数据的Python代码                                    | 整合后的完整数据集     |
| 19 | 编写Python脚本生成报告框架    | python\_execute | 生成报告框架的Python代码                                    | 报告HTML框架      |
| 20 | 编写Python脚本添加数据到报告   | python\_execute | 添加数据到报告的Python代码                                   | 带数据的报告HTML    |
| 21 | 编写Python脚本添加图表到报告   | python\_execute | 添加图表到报告的Python代码                                   | 带图表的报告HTML    |
| 22 | 编写Python脚本添加气候分析到报告 | python\_execute | 添加气候分析的Python代码                                    | 带气候分析的报告HTML  |
| 23 | 编写Python脚本添加结论到报告   | python\_execute | 添加结论的Python代码                                      | 带结论的完整报告HTML  |
| 24 | 保存完整报告HTML          | file\_saver     | 保存报告HTML到文件                                        | 成功保存报告HTML文件  |
| 25 | 编写Python脚本将报告转为PDF  | python\_execute | HTML转PDF的Python代码                                  | 报告PDF数据       |
| 26 | 保存报告PDF             | file\_saver     | 保存PDF数据到文件                                         | 成功保存报告PDF文件   |
| 27 | 编写Python脚本创建报告摘要    | python\_execute | 创建摘要的Python代码                                      | 报告摘要文本        |
| 28 | 保存报告摘要              | file\_saver     | 保存摘要到文件                                            | 成功保存摘要文件      |
| 29 | 编写Python脚本发送报告邮件    | python\_execute | 发送邮件的Python代码                                      | 邮件发送结果        |
| 30 | 总结完成的工作，等待下一步指示     | -               | -                                                  | 最终总结和下一步建议    |

### 3.2 执行日志

<Accordion title="部分执行日志">
  INFO     \[browser\_use] BrowserUse logging setup complete with level info
  INFO     \[root] Anonymized telemetry enabled. See [https://docs.browser-use.com/development/telemetry](https://docs.browser-use.com/development/telemetry) for more information.
  Enter your prompt (or 'exit' to quit): 全球大豆市场 2025 年分析报告
  2025-03-08 18:08:00.304 | WARNING  | **main**:main:15 - Processing your request...
  2025-03-08 18:08:00.305 | INFO     | app.agent.base:run:137 - Executing step 1/30
  2025-03-08 18:08:25.067 | INFO     | app.agent.toolcall:think:53 - ✨ Manus's thoughts: 好的，我现在需要处理用户关于“全球大豆市场2025年分析报告”的请求。首先，用户想要一份分析报告，这可能包括市场趋势、产量、价格、主要生产国、消费国以及未来预测等方面的信息。由于报告涉及未来数据，可能需要最新的行业数据和预测，而这些信息通常来自市场研究公司或权威机构的报告。

  接下来，我需要考虑如何获取这些信息。用户提供的工具包括Google搜索、浏览器使用、Python执行和文件保存。首先，我应该使用Google搜索来查找相关的分析报告或数据来源。可能需要搜索关键词如“global soybean market analysis 2025 report”或者“大豆市场预测2025”，看看是否有权威机构如美国农业部（USDA）、国际粮食政策研究所（IFPRI）或市场研究公司如Frost & Sullivan、Mordor Intelligence等发布的报告。

  使用Google搜索工具时，我需要构造合适的查询词，并可能需要多个关键词组合来确保找到最新的信息。搜索结果返回的链接可能包括PDF报告、行业分析文章或新闻稿。之后，可能需要使用浏览器工具访问这些链接，查看具体内容，提取关键数据。如果某些报告需要付费或注册，可能需要寻找免费摘要或通过其他途径获取。

  另外，用户可能希望报告以结构化的方式呈现，比如图表或数据表格。这时候可能需要使用Python来处理数据，例如从网页中抓取数据，或者生成图表。但首先需要确保有可用的数据源。如果搜索到的数据是文本形式，可能需要手动整理或使用Python的解析库如BeautifulSoup或Pandas来处理。

  保存最终的报告或分析结果可能需要使用文件保存工具，将整理好的数据、图表或总结文本保存为文档或代码文件。例如，将分析结果写入Markdown或PDF文件，或者生成一个HTML页面展示图表。

  现在，第一步应该是执行Google搜索，收集相关链接。然后根据搜索结果决定下一步行动，可能是访问具体网页提取数据，或者发现需要进一步处理的数据。如果搜索结果中有直接可下载的PDF报告，可能需要使用浏览器工具下载文件，但可能需要处理文件内容，比如使用Python读取PDF内容。如果报告需要付费，可能需要寻找替代资源或建议用户购买。

  另外，可能需要考虑时间因素，2025年的预测数据可能在2023或2024年的报告中已经存在，因此搜索时可能需要限定时间范围。不过Google搜索工具的参数中没有时间选项，可能需要在查询词中加入年份，如“2023 global soybean market forecast 2025”。

  总结步骤：

  1. 使用Google搜索查找相关报告链接。
  2. 分析搜索结果，访问相关网页，提取关键数据。
  3. 使用Python处理和整理数据，生成图表或分析结果。
  4. 将最终报告保存为文件。

  现在，首先执行Google搜索，看看能找到哪些资源。可能需要多次调整关键词以确保找到足够的信息。如果搜索结果不够，可能需要进一步细化查询，例如按地区、主要公司或特定方面（如价格趋势、产量预测）来搜索。
```

---

## 使用哪个大模型。比如你这里可以填写 Qwen/Qwen3-32B ， 具体模型可以通过 https://cloud.siliconflow.cn/models 获得

**URL:** llms-txt#使用哪个大模型。比如你这里可以填写-qwen/qwen3-32b-，-具体模型可以通过-https://cloud.siliconflow.cn/models-获得

translate.service.openai.model=Qwen/Qwen3-32B

---

## 生图模型

**URL:** llms-txt#生图模型

**Contents:**
- 1.生图模型简介
- 2.体验地址
- 3.支持模型列表

Source: https://docs.siliconflow.cn/cn/userguide/capabilities/images

平台提供的生图模型主要有以下两种使用方式：一种是根据prompt输入直接生成图像；一种是根据现有图像，加上prompt输入，生成图像变体。

在使用文生图的大模型时，为了生成更高质量的图像，输入的prompt（提示词）需要精心设计。以下是一些有助于提高生成图像质量的提示词输入技巧：

* **具体描述**：尽量详细地描述你想要生成的图像内容。比如，如果你想生成一幅日落的海滩风景，不要仅仅输入“海滩日落”，而是可以尝试输入“一个宁静的海滩上，夕阳西下，天空呈现出橙红色，海浪轻轻拍打着沙滩，远处有一艘小船”。

* **情感和氛围**：除了描述图像的内容，还可以加入对情感或氛围的描述，比如“温馨的”、“神秘的”、“充满活力的”等，这样可以帮助模型更好地理解你想要的风格。

* **风格指定**：如果你有特定的艺术风格偏好，比如“印象派”、“超现实主义”等，可以在prompt中明确指出，这样生成的图像更有可能符合你的期待。

* **避免模糊不清的词汇**：尽量避免使用过于抽象或模糊不清的词汇，比如“美”、“好”等，这些词汇对于模型来说难以具体化，可能会导致生成的图像与预期相差较大。

* **使用否定词**：如果你不希望图像中出现某些元素，可以使用否定词来排除。例如，“生成一幅海滩日落的图片，但不要有船”。

* **分步骤输入**：对于复杂场景，可以尝试分步骤输入提示词，先生成基础图像，再根据需要调整或添加细节。

* **尝试不同的描述方式**：有时候，即使描述的是同一个场景，不同的描述方式也会得到不同的结果。可以尝试从不同的角度或使用不同的词汇来描述，看看哪种方式能得到更满意的结果。

* **利用模型的特定功能**：一些模型可能提供了特定的功能或参数调整选项，比如调整生成图像的分辨率、风格强度等，合理利用这些功能也可以帮助提高生成图像的质量。

通过上述方法，可以有效地提高使用文生图大模型时生成图像的质量。不过，由于不同的模型可能有不同的特点和偏好，实际操作中可能还需要根据具体模型的特性和反馈进行适当的调整。

> A futuristic eco-friendly skyscraper in central Tokyo. The building incorporates lush vertical gardens on every floor, with cascading plants and trees lining glass terraces. Solar panels and wind turbines are integrated into the structure's design, reflecting a sustainable future. The Tokyo Tower is visible in the background, contrasting the modern eco-architecture with traditional city landmarks.

> An elegant snow leopard perched on a cliff in the Himalayan mountains, surrounded by swirling snow. The animal’s fur is intricately detailed with distinctive patterns and a thick winter coat. The scene captures the majesty and isolation of the leopard's habitat, with mist and mountain peaks fading into the background.

有部分生图模型支持通过已有图像生成图像变体，这种情况下，仍然需要输入适当的prompt，才能达到预期的效果，具体prompt输入，可以参考上面内容。

可以通过 [图像生成](https://cloud.siliconflow.cn/playground/image) 体验生图的功能，也可以通过 [API文档](https://docs.siliconflow.cn/api-reference/images/images-generations) 介绍，通过API进行调用。

* **image\_size**：控制参数的图像分辨率，API请求时候，可以自定义多种分辨率。

* **num\_inference\_steps**：控制图像生成的步长。

* **batch\_size**：一次生成图像的个数，默认值是1，最大值可以设置为4

* **negative\_prompt**：这里可以输入图像中不想出现的某些元素，消除一些影响影响因素。

* **seed**：如果想要每次都生成固定的图片，可以把seed设置为固定值。

目前已支持的生图模型，可以通过[模型广场](https://cloud.siliconflow.cn/sft-siliconflow/models?types=to-image)查看。

<Note>注意：支持的生图模型可能发生调整，请在「模型广场」筛选“生图”标签，了解支持的模型列表。</Note>

---

## 多模态模型（视觉/音频/视频）

**URL:** llms-txt#多模态模型（视觉/音频/视频）

**Contents:**
- 1. 概述
- 2. 支持模型概览
- 3. 使用方式
  - 3.1 基本消息格式
  - 3.2 通用参数说明
- 4. 使用示例
  - 4.1 视觉理解
  - 4.2 视频理解
  - 4.3 音频理解
  - 4.4 全模态分析

Source: https://docs.siliconflow.cn/cn/userguide/capabilities/multimodal-vision

多模态模型是能够同时处理多种模态信息（文本、图像、音频、视频）的大语言模型。SiliconFlow 提供了多个支持不同模态组合的强大模型，能够：

1. **视觉理解**：理解图片内容、OCR、图像描述
2. **视频分析**：提取视频帧、理解视频内容、动作识别
3. **音频处理**：语音识别、音频内容分析
4. **多模态融合**：同时处理多种媒体类型的综合分析

| 模型系列               | 视觉输入 | 音频输入 | 视频输入 | 主要特点            |
| ------------------ | ---- | ---- | ---- | --------------- |
| **Qwen3-Omni 系列**  | ✅    | ✅    | ✅    | 全面多模态支持，音视频同时处理 |
| **Qwen3-VL 系列**    | ✅    | ❌    | ✅    | 视觉+视频理解，无音频支持   |
| **GLM 系列**         | ✅    | ❌    | ❌    | 仅视觉理解           |
| **Qwen2-VL 系列**    | ✅    | ❌    | ❌    | 仅视觉理解           |
| **DeepseekVL2 系列** | ✅    | ❌    | ❌    | 仅视觉理解           |
| **Step3**          | ✅    | ❌    | ❌    | 仅视觉理解           |
| **DeepSeek-OCR**   | ✅    | ❌    | ❌    | 仅视觉理解，支持pdf输入   |

<Note>
  通过[模型广场](https://cloud.siliconflow.cn/me/models?tags=%E8%A7%86%E8%A7%89)查看当前支持的多模态模型列表。
  支持的模型可能发生调整，请以平台实际展示为准。
</Note>

所有多模态模型都通过 `/chat/completions` 接口调用，使用标准化的 `messages` 格式，其中 `content` 可以包含不同类型的内容部分。

#### 图像参数 (`image_url`)

* `url`: 图像 URL 或 base64 编码数据，DeepSeek-OCR 还支持 PDF URL 或 base64 编码数据
* `detail`: 细节级别 (`auto`, `low`, `high`)

#### 视频参数 (`video_url`)

* `url`: 视频 URL 或 base64 编码数据
* `detail`: 细节级别 (`auto`, `low`, `high`)
* `max_frames`: 最大提取帧数
* `fps`: 每秒提取帧数，最终帧数为 `min(fps × T, max_frames)`

#### 音频参数 (`audio_url`)

* `url`: 音频 URL 或 base64 编码数据

DeepSeek-OCR 还支持 PDF URL 或 base64 编码数据。

DeepSeek-OCR 支持多种场景的提示词：

## 5. Python SDK 使用示例

```python  theme={null}
response = client.chat.completions.create(
    model="Qwen/Qwen3-Omni-30B-A3B-Instruct",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {
                        "url": "https://example.com/product-demo.mp4",
                        "detail": "high",
                        "max_frames": 16,
                        "fps": 1
                    }
                },
                {
                    "type": "text",
                    "text": "这个产品演示视频展示了哪些核心功能？目标用户群体可能是什么？"
                }
            ]
        }
    ],
    stream=True
)

**Examples:**

Example 1 (unknown):
```unknown
### 3.2 通用参数说明

#### 图像参数 (`image_url`)

* `url`: 图像 URL 或 base64 编码数据，DeepSeek-OCR 还支持 PDF URL 或 base64 编码数据
* `detail`: 细节级别 (`auto`, `low`, `high`)

#### 视频参数 (`video_url`)

* `url`: 视频 URL 或 base64 编码数据
* `detail`: 细节级别 (`auto`, `low`, `high`)
* `max_frames`: 最大提取帧数
* `fps`: 每秒提取帧数，最终帧数为 `min(fps × T, max_frames)`

#### 音频参数 (`audio_url`)

* `url`: 音频 URL 或 base64 编码数据

## 4. 使用示例

### 4.1 视觉理解

#### 图像分析
```

Example 2 (unknown):
```unknown
#### 多图对比
```

Example 3 (unknown):
```unknown
#### PDF OCR

DeepSeek-OCR 还支持 PDF URL 或 base64 编码数据。

DeepSeek-OCR 支持多种场景的提示词：
```

Example 4 (unknown):
```unknown

```

---

## 推理模型

**URL:** llms-txt#推理模型

**Contents:**
- 1. 概述
- 2. 平台支持推理模型
- 3. 使用建议
  - 3.1 API 参数
  - 3.2 DeepSeek-R1 使用建议
- 4. OpenAI 请求示例
  - 4.1 流式输出请求

Source: https://docs.siliconflow.cn/cn/userguide/capabilities/reasoning

推理模型是基于深度学习的AI系统，通过逻辑推演、知识关联和上下文分析解决复杂任务，典型应用包括数学解题、代码生成、逻辑判断和多步推理场景。这类模型通常具备以下特性：

* 结构化思维：采用思维链（Chain-of-Thought）等技术分解复杂问题
* 知识融合：整合领域知识库与常识推理能力
* 自修正机制：通过验证反馈回路提升结果可靠性
* 多模态处理：部分先进模型支持文本/代码/公式混合输入

平台支持的推理模型，可以通过[模型广场](https://cloud.siliconflow.cn/sft-siliconflow/models?tags=%E6%8E%A8%E7%90%86%E6%A8%A1%E5%9E%8B)查询。

* **最大思维链长度（thinking\_budget）**：模型用于内部推理的 token 数，合理设置 thinking\_budget ，可以控制回答的思维链长度。

* **最大回复长度（max\_tokens**）：用于限制模型最终输出给用户的回复 token 数，控制回复的最大长度。

**最大上下文长度（context\_length）**：非请求参数，不需要用户自己设置。不同模型支持的最大上下文长度可通过[模型广场](https://cloud.siliconflow.cn/sft-siliconflow/models)页面进行查看。

* 若“思考阶段”生成的 `token` 数达到 `thinking_budget`，因 `Qwen3` 系列推理模型原生支持该参数模型将强制停止思维链推理，其他推理模型有可能会继续输出思考内容。
* 若最大回复长度超过 `max_tokens`或上下文长度超过`context_length` 限制，回复内容将进行截断，响应中的 `finish_reason` 字段将标记为 `length`，表示因长度限制终止输出。

* **返回参数**:
  * reasoning\_content：思维链内容，与 content 同级。
  * content：最终回答内容

### 3.2 DeepSeek-R1 使用建议

* 将 temperature 设置在 0.5-0.7 范围内（推荐值为 0.6），以防止无限循环或不连贯的输出。

* 将 top\_p 的值设置在 0.95。

* 避免添加系统提示,所有指令应包含在用户提示中。

* 对于数学问题，建议在提示中包含一个指令，例如：“请逐步推理，并将最终答案写在 \boxed{} 中。”

* 在评估模型性能时，建议进行多次测试并平均结果。

```python  theme={null}
from openai import OpenAI

url = 'https://api.siliconflow.cn/v1/'
api_key = 'your api_key'

client = OpenAI(
    base_url=url,
    api_key=api_key
)

---

## 语言模型

**URL:** llms-txt#语言模型

**Contents:**
- 1. 模型核心能力
  - 1.1 基础功能
  - 1.2 进阶能力
- 2. 接口调用规范
  - 2.1 基础请求结构
  - 2.2 消息体结构说明
- 3. 模型系列选型指南
- 4. 核心参数详解
  - 4.1 创造性控制

Source: https://docs.siliconflow.cn/cn/userguide/capabilities/text-generation

文本生成：根据上下文生成连贯的自然语言文本，支持多种文体和风格。

语义理解：深入解析用户意图，支持多轮对话管理，确保对话的连贯性和准确性。

知识问答：覆盖广泛的知识领域，包括科学、技术、文化、历史等，提供准确的知识解答。

代码辅助：支持多种主流编程语言（如Python、Java、C++等）的代码生成、解释和调试。

长文本处理：支持4k至64k tokens的上下文窗口，适用于长篇文档生成和复杂对话场景。

指令跟随：精确理解复杂任务指令，如“用Markdown表格对比A/B方案”。

风格控制：通过系统提示词调整输出风格，支持学术、口语、诗歌等多种风格。

多模态支持：除了文本生成，还支持图像描述、语音转文字等多模态任务。

您可以通过 openai sdk进行端到端接口请求

<AccordionGroup>
  <Accordion title="生成对话（点击查看详情）">
    
  </Accordion>

<Accordion title="分析一幅图像（点击查看详情）">
    
  </Accordion>

<Accordion title="生成json数据（点击查看详情）">
    
  </Accordion>
</AccordionGroup>

| 消息类型      | 功能描述                            | 示例内容               |
| --------- | ------------------------------- | ------------------ |
| system    | 模型指令，设定AI角色，描述模型应一般如何行为和响应      | 例如："你是有10年经验的儿科医生" |
| user      | 用户输入，将最终用户的消息传递给模型              | 例如："幼儿持续低烧应如何处理？"  |
| assistant | 模型生成的历史回复，为模型提供示例，说明它应该如何回应当前请求 | 例如："建议先测量体温..."    |

你想让模型遵循分层指令时，消息角色可以帮助你获得更好的输出。但它们并不是确定性的，所以使用的最佳方式是尝试不同的方法，看看哪种方法能给你带来好的结果。

可以进入[模型广场](https://cloud.siliconflow.cn/models)，根据左侧的筛选功能，筛选支持不同功能的语言模型，根据模型的介绍，了解模型具体的价格、模型参数大小、模型上下文支持的最大长度及模型价格等内容。

支持在[playground](https://cloud.siliconflow.cn/playground/chat)进行体验（playground只进行模型体验，暂时没有历史记录功能，如果您想要保存历史的回话记录内容，请自己保存会话内容），想要了解更多使用方式，可以参考[API文档](https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions)

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=02fc8e406ca7af85592cea9669650347" data-og-width="3198" width="3198" data-og-height="1880" height="1880" data-path="images/guides/capabilities/image.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=280&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3c825d781b12895c87f28637a700889e 280w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=560&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=1adab41906fd72156acd7f1d6ebfab02 560w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=840&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=d676a9ab2ae2a80e188adee7de97e08f 840w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=1100&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=051f9814f583a8fe8b70b315894efc45 1100w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=1650&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=0addd51d3fc8e5f13e254001f5598d80 1650w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=2500&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3513c59c72f2bbc5011f91d182fdb7ac 2500w" />
</Frame>

```bash  theme={null}

**Examples:**

Example 1 (unknown):
```unknown
</Accordion>

  <Accordion title="分析一幅图像（点击查看详情）">
```

Example 2 (unknown):
```unknown
</Accordion>

  <Accordion title="生成json数据（点击查看详情）">
```

Example 3 (unknown):
```unknown
</Accordion>
</AccordionGroup>

### 2.2 消息体结构说明

| 消息类型      | 功能描述                            | 示例内容               |
| --------- | ------------------------------- | ------------------ |
| system    | 模型指令，设定AI角色，描述模型应一般如何行为和响应      | 例如："你是有10年经验的儿科医生" |
| user      | 用户输入，将最终用户的消息传递给模型              | 例如："幼儿持续低烧应如何处理？"  |
| assistant | 模型生成的历史回复，为模型提供示例，说明它应该如何回应当前请求 | 例如："建议先测量体温..."    |

你想让模型遵循分层指令时，消息角色可以帮助你获得更好的输出。但它们并不是确定性的，所以使用的最佳方式是尝试不同的方法，看看哪种方法能给你带来好的结果。

## 3. 模型系列选型指南

可以进入[模型广场](https://cloud.siliconflow.cn/models)，根据左侧的筛选功能，筛选支持不同功能的语言模型，根据模型的介绍，了解模型具体的价格、模型参数大小、模型上下文支持的最大长度及模型价格等内容。

支持在[playground](https://cloud.siliconflow.cn/playground/chat)进行体验（playground只进行模型体验，暂时没有历史记录功能，如果您想要保存历史的回话记录内容，请自己保存会话内容），想要了解更多使用方式，可以参考[API文档](https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions)

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=02fc8e406ca7af85592cea9669650347" data-og-width="3198" width="3198" data-og-height="1880" height="1880" data-path="images/guides/capabilities/image.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=280&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3c825d781b12895c87f28637a700889e 280w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=560&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=1adab41906fd72156acd7f1d6ebfab02 560w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=840&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=d676a9ab2ae2a80e188adee7de97e08f 840w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=1100&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=051f9814f583a8fe8b70b315894efc45 1100w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=1650&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=0addd51d3fc8e5f13e254001f5598d80 1650w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/capabilities/image.png?w=2500&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3513c59c72f2bbc5011f91d182fdb7ac 2500w" />
</Frame>

## 4. 核心参数详解

### 4.1 创造性控制
```

---

## 核采样（top_p）

**URL:** llms-txt#核采样（top_p）

**Contents:**
  - 4.2 输出限制
  - 4.3 语言模型场景问题汇总
- 5. 计费与配额管理
  - 5.1 计费公式
  - 5.2 支持模型列表及单价
- 6. 应用案例
  - 6.1 技术文档生成
  - 6.2 数据分析报告

top_p=0.9  # 仅考虑概率累积90%的词集  
json  theme={null}
max_tokens=1000  # 单词请求最大生成长度  
stop=["\n##", "<|end|>"]  # 终止序列，在返回中遇到数组中对应的字符串，就会停止输出 
frequency_penalty=0.5  # 抑制重复用词（-2.0~2.0）  
stream=true # 控制输出是否是流式输出，对于一些输出内容比较多的模型，建议设置为流式，防止输出过长，导致输出超时
python  theme={null}
    payload = {
        "model": "Qwen/Qwen2.5-Math-72B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": "1+1=?",
            }
        ],
        "max_tokens": 200,  # 按需添加
        "temperature": 0.7, # 按需添加
        "top_k": 50,        # 按需添加
        "top_p": 0.7,       # 按需添加
        "frequency_penalty": 0 # 按需添加
    }
python  theme={null}
from openai import OpenAI
client = OpenAI(api_key="YOUR_KEY", base_url="https://api.siliconflow.cn/v1")
response = client.chat.completions.create(  
    model="Qwen/Qwen2.5-Coder-32B-Instruct",  
    messages=[{  
        "role": "user",  
        "content": "编写Python异步爬虫教程，包含代码示例和注意事项"  
    }],  
    temperature=0.7,  
    max_tokens=4096  
)  
python  theme={null}
from openai import OpenAI
client = OpenAI(api_key="YOUR_KEY", base_url="https://api.siliconflow.cn/v1")
response = client.chat.completions.create(  
    model="Qwen/QVQ-72B-Preview",  
    messages=[    
        {"role": "system", "content": "你是数据分析专家，用Markdown输出结果"},  
        {"role": "user", "content": "分析2023年新能源汽车销售数据趋势"}  
    ],  
    temperature=0.7,  
    max_tokens=4096  
)  
```

<Note> 模型能力持续更新中，建议定期访问[模型广场](https://cloud.siliconflow.cn/models)获取最新信息。 </Note>

**Examples:**

Example 1 (unknown):
```unknown
### 4.2 输出限制
```

Example 2 (unknown):
```unknown
### 4.3 语言模型场景问题汇总

**1. 模型输出乱码**

目前看到部分模型在不设置参数的情况下，容易出现乱码，遇到上述情况，可以尝试设置`temperature`，`top_k`，`top_p`，`frequency_penalty`这些参数。

对应的 payload 修改为如下形式，不同语言酌情调整
```

Example 3 (unknown):
```unknown
**2. 关于`max_tokens`说明**

max\_tokens 与`上下文长度`相等，由于部分模型推理服务尚在更新中，请不要在请求时将 max\_tokens 设置为最大值（上下文长度），建议留出 10k 左右作为输入内容的空间。

**3. 关于`context_length`说明**

不同的LLM模型，`context_length`是有差别的，具体可以在[模型广场](https://cloud.siliconflow.cn/models)上搜索对应的模型，
查看模型具体信息。

**4. 模型输出截断问题**

可以从以下几方面进行问题的排查：

* 通过API请求时候，输出截断问题排查：
  * max\_tokens设置：max\_token设置到合适值，输出大于max\_token的情况下，会被截断。
  * 设置流式输出请求：非流式请求时候，输出内容比较长的情况下，容易出现504超时。
  * 设置客户端超时时间：把客户端超时时间设置大一些，防止未输出完成，达到客户端超时时间被截断。
* 通过第三方客户端请求，输出截断问题排查：
  * CherryStdio 默认的 max\_tokens 是 4096，用户可以通过设置，打开“开启消息长度限制”的开关，将max\_token设置到合适值

<Frame>
  <img width="500" src="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=b77a496c600c494ff27b8f1c6203bb5d" data-og-width="2126" data-og-height="1324" data-path="images/faqs/mic/image_5.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?w=280&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=ed7d0698216adf85842b12f357c55053 280w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?w=560&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=64487aefdf2a783e6748ddc6ace9134a 560w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?w=840&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=175aff66b443fec3f909995629e9c4da 840w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?w=1100&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=07de4aecf2d7bc13f0dbeefad8d84beb 1100w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?w=1650&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=c50064e5887225d8e47f593f1c23f09b 1650w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/faqs/mic/image_5.png?w=2500&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=bbf19aa1ef2119ec830c2a0fceeb9a29 2500w" />
</Frame>

**5. 错误码处理**

| 错误码     | 常见原因           | 解决方案                        |
| ------- | -------------- | --------------------------- |
| 400     | 参数格式错误         | 检查temperature等请求参数的取值范围     |
| 401     | API Key 没有正确设置 | 检查API Key                   |
| 403     | 权限不够           | 最常见的原因是该模型需要实名认证，其他情况参考报错信息 |
| 429     | 请求频率超限         | 实施指数退避重试机制                  |
| 503/504 | 模型过载           | 切换备用模型节点                    |

## 5. 计费与配额管理

### 5.1 计费公式

`总费用 = (输入tokens × 输入单价) + (输出tokens × 输出单价) `

### 5.2 支持模型列表及单价

支持的模型及具体价格可以进入[模型广场](https://cloud.siliconflow.cn/me/models?types=chat)下的模型详情页查看。

## 6. 应用案例

### 6.1 技术文档生成
```

Example 4 (unknown):
```unknown
### 6.2 数据分析报告
```

---

## 视频生成模型

**URL:** llms-txt#视频生成模型

**Contents:**
- 1. 使用场景
- 2. 使用建议
- 3. 体验地址
- 4. 支持模型
  - 4.1 文生视频模型
  - 4.2 图生视频模型

Source: https://docs.siliconflow.cn/cn/userguide/capabilities/video

视频生成模型是一种利用文本或图像描述生成动态视频内容的技术，随着技术的不断发展，它的应用场景也越来越广泛。以下是一些潜在的应用领域：

1. 动态内容生成：视频生成模型可以生成动态的视觉内容，用于描述和解释信息；
2. 多模态智能交互：结合图像和文本输入，视频生成模型可用于更智能、更交互式的应用场景；
3. 替代传统视觉技术：视频生成模型可以替代或增强传统的机器视觉技术，解决更复杂的多模态问题； 随着技术的进步，视频生成模型的多模态能力会与视觉语言模型融合，推动其在智能交互、自动化内容生成以及复杂场景模拟等领域的全面应用。此外，视频生成模型还能与图像生成模型（图生视频）结合，进一步拓展其应用范围，实现更加丰富和多样化的视觉内容生成。

在编写提示词时，请关注详细、按时间顺序描述动作和场景。包含具体的动作、外貌、镜头角度以及环境细节，所有内容都应连贯地写在一个段落中，直接从动作开始，描述应具体和精确，将自己想象为在描述镜头脚本的摄影师，提示词保持在200单词以内。

为了获得最佳效果，请按照以下结构构建提示词：

* 从主要动作的一句话开始
  * 示例：A woman with light skin, wearing a blue jacket and a black hat with a veil,She first looks down and to her right, then raises her head back up as she speaks.
* 添加关于动作和手势的具体细节
  * 示例：She first looks down and to her right, then raises her head back up as she speaks.
* 精确描述角色/物体的外观
  * 示例：She has brown hair styled in an updo, light brown eyebrows, and is wearing a white collared shirt under her blue jacket.
* 包括背景和环境的细节
  * 示例：The background is out of focus, but shows trees and people in period clothing.
* 指定镜头角度和移动方式
  * 示例：The camera remains stationary on her face as she speaks.
* 描述光线和颜色效果
  * 示例：The scene is captured in real-life footage, with natural lighting and true-to-life colors.
* 注意任何变化或突发事件
  * 示例：A gust of wind blows through the trees, causing the woman's veil to flutter slightly.

<video width="560" height="315" controls autoplay>
  <source src="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/cn/userguide/capabilities/example.mp4?fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3088db3989cb6186b90289b5da0ddf3d" type="video/mp4" data-path="cn/userguide/capabilities/example.mp4" />

Your browser does not support the video tag.
</video>

可以点击 [playground](https://cloud.siliconflow.cn/playground/text-to-video) 进行体验，也可以通过 [API文档](/cn/api-reference/videos/videos_submit) 查看 api 调用方式。

* Wan-AI/Wan2.2-T2V-A14B

* Wan-AI/Wan2.2-I2V-A14B

2. 图生视频的分辨率
   根据用户上传图片的宽高比自动匹配分辨率：

* 16:9 👉 1280×720
* 9:16 👉 720×1280
* 1:1 👉 960×960

为了保证最佳生成效果，建议您使用宽高比为 16:9 / 9:16 / 1:1 的图片生成视频。

<Note>注意：支持的文生视频模型可能发生调整，请在「模型广场」筛选“视频”标签，了解支持的模型列表。</Note>

---

## 模型微调

**URL:** llms-txt#模型微调

**Contents:**
- 1. 模型微调简介
- 2. 使用流程
  - 2.1 准备数据
  - 2.2 新建并配置微调任务
  - 2.3 开始训练
  - 2.4 调用微调模型
- 3. 参数配置详解
- 4. 基于SiliconFlow微调服务来优化业务实战
  - 4.1 在平台上使用“智说新语”的语料按照上述进行微调。
  - 4.2 对比微调前后的效果

Source: https://docs.siliconflow.cn/cn/userguide/guides/fine-tune

模型微调是一种在已有预训练模型的基础上，通过使用特定任务的数据集进行进一步训练的技术。这种方法允许模型在保持其在大规模数据集上学到的通用知识的同时，适应特定任务的细微差别。使用微调模型，可以获得以下好处：

* 提高性能：微调可以显著提高模型在特定任务上的性能。
* 减少训练时间：相比于从头开始训练模型，微调通常需要较少的训练时间和计算资源。
* 适应特定领域：微调可以帮助模型更好地适应特定领域的数据和任务。

**SiliconFlow 平台提供高效的模型微调能力，目前有以下模型支持微调**：

* 对话模型已支持：
  * Qwen/Qwen2.5-7B-Instruct
  * Qwen/Qwen2.5-14B-Instruct
  * Qwen/Qwen2.5-32B-Instruct
  * Qwen/Qwen2.5-72B-Instruct

最新支持的模型参考[模型微调](https://cloud.siliconflow.cn/fine-tune)

仅支持 `.jsonl` 文件，且需符合以下要求：

1. 每行是一个独立的 `JSON` 对象；
2. 每个对象必须包含键名为 `messages` 的数组，数组不能为空；
3. `messages` 中每个元素必须包含 `role` 和 `content` 两个字段；
4. `role` 只能是 `system`、`user` 或 `assistant`；
5. 如果有 `system` 角色消息，必须在数组首位；
6. 第一条非 `system` 消息必须是 `user` 角色；
7. `user` 和 `assistant` 角色的消息应当交替、成对出现，不少于 `1` 对

* 选择 `对话模型微调` 或者 `生图模型微调`
* 填写任务名称
* 选择基础模型
* 上传或选取已上传的训练数据
* 设置验证数据，支持训练集按比例切分（默认 10%），或单独选定验证集
* 配置训练参数

* 点击"开始微调"
* 等待任务完成
* 获取模型标识符

* 复制模型标识符
  在[模型微调页](https://cloud.siliconflow.cn/fine-tune)复制对应的模型标识符。

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=46546901e87a07293f46ca42c94288cb" data-og-width="3312" width="3312" data-og-height="1042" height="1042" data-path="images/guides/fine-tuning/fine-tuning-models.jpeg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=280&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=998ae38ed5188263997da01d51d5f72b 280w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=560&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=dead565b4c623964dc8d8d3e1471f8c7 560w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=840&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=5186b904fcad3a186a33979411025f9a 840w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=1100&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=83e9140e9ebf5df34020f2a012818cc5 1100w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=1650&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3dbb9122c376a0a88cde65de1345688a 1650w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=2500&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=2872c27b12ffbc745fa6cbff2fd3a1fd 2500w" />
</Frame>

* 通过 `/chat/completions` API 即可直接调用微调后的模型

下面是基于 OpenAI 的chat.completions 接口访问微调后模型的例子：

|        参数名       |   说明  |  取值范围  |   建议值  |     使用建议     |
| :--------------: | :---: | :----: | :----: | :----------: |
|   Learning Rate  |  学习速率 |  0-0.1 | 0.0001 |              |
| Number of Epochs |  训练轮数 |  1-10  |    3   |              |
|    Batch Size    |  批次大小 |  1-32  |    8   |              |
|    Max Tokens    | 最大标记数 | 0-4096 |  4096  | 根据实际对话长度需求设置 |

|      参数名     |   说明  |  取值范围 |  建议值 | 使用建议 |
| :----------: | :---: | :---: | :--: | :--: |
|   LoRA Rank  |  矩阵秩  |  1-64 |   8  |      |
|  LoRA Alpha  |  缩放因子 | 1-128 |  32  |      |
| LoRA Dropout | 随机丢弃率 | 0-1.0 | 0.05 |      |

|  场景  | Learning Rate | Epochs | Batch Size | LoRA Rank | LoRA Alpha | Dropout |
| :--: | :-----------: | :----: | :--------: | :-------: | :--------: | :-----: |
| 标准方案 |     0.0001    |    3   |      8     |     8     |     32     |   0.05  |
| 效果优先 |     0.0001    |    5   |     16     |     16    |     64     |   0.1   |
| 轻量快速 |     0.0001    |    2   |      8     |     4     |     16     |   0.05  |

## 4. 基于SiliconFlow微调服务来优化业务实战

之前硅基流动开发了[智说新语](https://mp.weixin.qq.com/s/5KXjWwAXT-LfjGVJDE4Eiw)应用，我们通过提示词工程提供一个复杂的提示词来让大模型生成“金句”风格的描述语句。
现在，我们可通过平台的微调功能来压缩提示词并提升效果，让整个的文本生成风格更统一，速度更快，且进一步优化成本。

### 4.1 在平台上使用“智说新语”的语料按照上述进行微调。

步骤见[模型微调使用流程](/guides/fine-tune#2)<br />
详细语料和测试代码见[siliconcloud-cookbook](https://github.com/siliconflow/siliconcloud-cookbook/tree/main/examples/fine-tune)

使用方式见[模型微调调用模型](/guides/fine-tune#2-4)

* 微调前：
  Qwen2.5-7B-Instruct 系统Prompt:

* Qwen2.5-7B-Instruct+智说新语微调后的Prompt:

| 输入   | Qwen2.5-7B-Instruct 模型                                                                                                                   | Qwen2.5-7B-Instruct 微调模型                             |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- |
| 五道口  | VLG，不过是知识的轻轨与资本的交汇站，文青与土豪在此擦肩而过，孰是求知的信徒，孰是逐利的信徒，全凭幸存者的微笑。                                                                                | 知识的殿堂与商业的洪流交织，学人的笔记与商人的谈资齐飞，地名犹在，荣光已非。               |
| 新时代  | claimed to break旧 mold yet still clings to the stirring rhetoric of progress, like a fashion plate who ignores the evolution of fashion。 | 新时代的号角已吹响，然砥砺前行时，方显初心易失之难。                           |
| 创新   | 看似凤凰涅槃的奇迹，实则多数人不过是换汤不换药的换皮游戏。                                                                                                            | 标新立异本是勇气的象征，却在同质化的社会中成了猎奇的代名词。                       |
| 降维打击 | 所谓降维打击，实则是现代文明中的一种高级愚民术，用高深莫测的科技iscard，让普通人以为自己正生活在理性与进步之中，却不知已在智力与道德的低维空间中遭受碾压。。                                                        | 高维智慧轻而易举地碾压低维凡尘，却不知低维众生早已习于在自己的平庸中寻觅慰藉，哪里还懂得高维打击的意义。 |
| 基金   | 看似为财富增值保驾护航的金融巨轮，实则多数人不过是随波逐流的浮萍，最终沦为填补市场波动的牺牲品。                                                                                         | 投资者的白日梦，用钱铺路，却常跌入夜的陷阱。                               |

1. 微调后的输出内容风格更统一，输出效果更稳定可控。
2. 微调后整个输入长度大大降低，从原始的553个token，降低至8个token，显著降低了输入tokens长度，速度更快，成本得以进一步优化。

**Examples:**

Example 1 (unknown):
```unknown
### 2.2 新建并配置微调任务

* 选择 `对话模型微调` 或者 `生图模型微调`
* 填写任务名称
* 选择基础模型
* 上传或选取已上传的训练数据
* 设置验证数据，支持训练集按比例切分（默认 10%），或单独选定验证集
* 配置训练参数

### 2.3 开始训练

* 点击"开始微调"
* 等待任务完成
* 获取模型标识符

### 2.4 调用微调模型

#### 2.4.1 对话微调模型调用

* 复制模型标识符
  在[模型微调页](https://cloud.siliconflow.cn/fine-tune)复制对应的模型标识符。

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=46546901e87a07293f46ca42c94288cb" data-og-width="3312" width="3312" data-og-height="1042" height="1042" data-path="images/guides/fine-tuning/fine-tuning-models.jpeg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=280&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=998ae38ed5188263997da01d51d5f72b 280w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=560&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=dead565b4c623964dc8d8d3e1471f8c7 560w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=840&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=5186b904fcad3a186a33979411025f9a 840w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=1100&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=83e9140e9ebf5df34020f2a012818cc5 1100w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=1650&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=3dbb9122c376a0a88cde65de1345688a 1650w, https://mintcdn.com/siliconflow-37161621/lraNstG3w6Lot0Ag/images/guides/fine-tuning/fine-tuning-models.jpeg?w=2500&fit=max&auto=format&n=lraNstG3w6Lot0Ag&q=85&s=2872c27b12ffbc745fa6cbff2fd3a1fd 2500w" />
</Frame>

* 通过 `/chat/completions` API 即可直接调用微调后的模型

下面是基于 OpenAI 的chat.completions 接口访问微调后模型的例子：
```

Example 2 (unknown):
```unknown
## 3. 参数配置详解

1. 基础训练参数

|        参数名       |   说明  |  取值范围  |   建议值  |     使用建议     |
| :--------------: | :---: | :----: | :----: | :----------: |
|   Learning Rate  |  学习速率 |  0-0.1 | 0.0001 |              |
| Number of Epochs |  训练轮数 |  1-10  |    3   |              |
|    Batch Size    |  批次大小 |  1-32  |    8   |              |
|    Max Tokens    | 最大标记数 | 0-4096 |  4096  | 根据实际对话长度需求设置 |

2. LoRA参数

|      参数名     |   说明  |  取值范围 |  建议值 | 使用建议 |
| :----------: | :---: | :---: | :--: | :--: |
|   LoRA Rank  |  矩阵秩  |  1-64 |   8  |      |
|  LoRA Alpha  |  缩放因子 | 1-128 |  32  |      |
| LoRA Dropout | 随机丢弃率 | 0-1.0 | 0.05 |      |

3. 场景化配置方案

**对话模型**

|  场景  | Learning Rate | Epochs | Batch Size | LoRA Rank | LoRA Alpha | Dropout |
| :--: | :-----------: | :----: | :--------: | :-------: | :--------: | :-----: |
| 标准方案 |     0.0001    |    3   |      8     |     8     |     32     |   0.05  |
| 效果优先 |     0.0001    |    5   |     16     |     16    |     64     |   0.1   |
| 轻量快速 |     0.0001    |    2   |      8     |     4     |     16     |   0.05  |

## 4. 基于SiliconFlow微调服务来优化业务实战

之前硅基流动开发了[智说新语](https://mp.weixin.qq.com/s/5KXjWwAXT-LfjGVJDE4Eiw)应用，我们通过提示词工程提供一个复杂的提示词来让大模型生成“金句”风格的描述语句。
现在，我们可通过平台的微调功能来压缩提示词并提升效果，让整个的文本生成风格更统一，速度更快，且进一步优化成本。

### 4.1 在平台上使用“智说新语”的语料按照上述进行微调。

步骤见[模型微调使用流程](/guides/fine-tune#2)<br />
详细语料和测试代码见[siliconcloud-cookbook](https://github.com/siliconflow/siliconcloud-cookbook/tree/main/examples/fine-tune)

### 4.2 对比微调前后的效果

使用方式见[模型微调调用模型](/guides/fine-tune#2-4)

#### 4.2.1 模型输入

* 微调前：
  Qwen2.5-7B-Instruct 系统Prompt:
```

Example 3 (unknown):
```unknown
* Qwen2.5-7B-Instruct+智说新语微调后的Prompt:
```

---

## Function Calling

**URL:** llms-txt#function-calling

**Contents:**
- 1. 使用场景
- 2. 使用方式
  - 2.1 通过 REST API 添加 tools 请求参数
  - 2.2 通过 OpenAI 库请求
- 3. 支持模型列表
- 4. 使用示例
  - 4.1. 示例 1：通过function calling 来扩展大语言模型的数值计算能力
  - 4.2. 示例 2：通过function calling 来扩展大语言模型对外部环境的理解

Source: https://docs.siliconflow.cn/cn/userguide/guides/function-calling

Function Calling 功能让模型能够调用外部工具，来增强自身能力。
该能力可以通过外部工具，通过大模型作为大脑调用外部工具（如搜索外部知识、查阅行程、或者某些特定领域工具），有效解决模型的幻觉、知识时效性等问题。

### 2.1 通过 REST API 添加 tools 请求参数

### 2.2 通过 OpenAI 库请求

该功能和 OpenAI 兼容，在使用 OpenAI 的库时，对应的请求参数中添加`tools=[对应的 tools]`
比如：

可以通过[模型广场](https://cloud.siliconflow.cn/sft-d29cu3l6d3ps738g4d60/models?tags=Tools)查看当前支持tools的模型。

<Note>注意：支持的模型列表在不断调整中，请查阅[本文档](/features/function_calling)了解最新支持的模型列表。</Note>

### 4.1. 示例 1：通过function calling 来扩展大语言模型的数值计算能力

本代码输入 4 个函数，分别是数值的加、减、比较大小、字符串中重复字母计数四个函数
来演示通过function calling来解决大语言模型在tokens 预测不擅长的领域的执行问题。

### 4.2. 示例 2：通过function calling 来扩展大语言模型对外部环境的理解

本代码输入 1 个函数，通过外部 API 来查询外部信息

```python  theme={null}
import requests
from openai import OpenAI

client = OpenAI(
    api_key="您的 APIKEY", # 从https://cloud.siliconflow.cn/account/ak获取
    base_url="https://api.siliconflow.cn/v1"
)

**Examples:**

Example 1 (unknown):
```unknown
比如完整的 payload 信息：
```

Example 2 (unknown):
```unknown
### 2.2 通过 OpenAI 库请求

该功能和 OpenAI 兼容，在使用 OpenAI 的库时，对应的请求参数中添加`tools=[对应的 tools]`
比如：
```

Example 3 (unknown):
```unknown
## 3. 支持模型列表

可以通过[模型广场](https://cloud.siliconflow.cn/sft-d29cu3l6d3ps738g4d60/models?tags=Tools)查看当前支持tools的模型。

<Note>注意：支持的模型列表在不断调整中，请查阅[本文档](/features/function_calling)了解最新支持的模型列表。</Note>

## 4. 使用示例

### 4.1. 示例 1：通过function calling 来扩展大语言模型的数值计算能力

本代码输入 4 个函数，分别是数值的加、减、比较大小、字符串中重复字母计数四个函数
来演示通过function calling来解决大语言模型在tokens 预测不擅长的领域的执行问题。
```

Example 4 (unknown):
```unknown
模型将输出：
```

---

## 前缀续写

**URL:** llms-txt#前缀续写

**Contents:**
- 1. 使用场景
- 2. 使用方式
- 3. 支持模型列表
- 4. 使用示例

Source: https://docs.siliconflow.cn/cn/userguide/guides/prefix

前缀续写中，用户提供希望输出的前缀信息，来让模型基于用户提供的前缀信息来补全其余的内容。
基于上述能力，模型能有更好的指令遵循能力，满足用户一些特定场景的指定格式的问题。

目前[大语言类模型](https://cloud.siliconflow.cn/models?types=chat) 中非推理模型支持上述参数，推理模型中 Qwen3 系列，需要通过增加`enable_thinking=true`关闭推理后，支持上述参数，deepseek R1系列暂时不支持上述参数。

<Note>注意：支持的模型情况可能会发生变化，请查阅本文档了解最新支持的模型列表。</Note>

下面是基于 OpenAI 库使用前缀续写的例子：

print(response.choices[0].message.content)
````

**Examples:**

Example 1 (unknown):
```unknown
## 3. 支持模型列表

目前[大语言类模型](https://cloud.siliconflow.cn/models?types=chat) 中非推理模型支持上述参数，推理模型中 Qwen3 系列，需要通过增加`enable_thinking=true`关闭推理后，支持上述参数，deepseek R1系列暂时不支持上述参数。

<Note>注意：支持的模型情况可能会发生变化，请查阅本文档了解最新支持的模型列表。</Note>

## 4. 使用示例

下面是基于 OpenAI 库使用前缀续写的例子：
```

---

## 快速上手

**URL:** llms-txt#快速上手

**Contents:**
- 1. 登录平台
- 2. 查看模型列表和模型详情
- 3. 在 playground 体验 GenAI 能力
- 4. 使用 SiliconFlow API 调用GenAI 能力
  - 4.1 创建API key
  - 4.2 通过REST 接口进行服务调用
  - 4.3 通过 OpenAI 接口调用

Source: https://docs.siliconflow.cn/cn/userguide/quickstart

访问[ SiliconFlow官网 ](https://siliconflow.cn/zh-cn/siliconcloud)并点击右上角[“登录”](https://cloud.siliconflow.cn/)按钮，按照提示填写您的基本信息进行登录。
（目前平台支持短信登录、邮箱登录，以及 GitHub、Google 的 OAuth 登录）

通过[ 模型广场 ](https://cloud.siliconflow.cn/models)查看当前可用的模型详情、模型价格、用户可用的最高限速等信息，并可以通过模型详情页的“在线体验”进入到模型体验中心。

## 3. 在 playground 体验 GenAI 能力

进入[“体验中心( playground )”](https://cloud.siliconflow.cn/)页面，左侧栏可选择语言模型、文生图模型和图生图模型，选择相应模型即可开始实时体验。输入相关参数及 prompt ，点击“运行”按钮，即可看到模型生成的结果。

## 4. 使用 SiliconFlow API 调用GenAI 能力

进入[API密钥](https://cloud.siliconflow.cn/account/ak)页面，点击“新建API密钥”，创建您的API key

### 4.2 通过REST 接口进行服务调用

您可以直接在平台的[“文档链接”](https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions)中使用您的 API key 进行在线调用，此处可以生成对应语言的代码。

### 4.3 通过 OpenAI 接口调用

当前大语言模型部分支持以 OpenAI 库进行调用，
安装 Python3.7.1 或更高版本并设置虚拟环境后，即可安装 OpenAI Python 库。从终端/命令行运行：

完成此操作后， running 将显示您在当前环境中安装的 Python 库，确认 OpenAI Python 库已成功安装。
之后可以直接通过 OpenAI 的相关接口进行调用，目前平台支持 OpenAI 相关的大多数参数。

**Examples:**

Example 1 (unknown):
```unknown
完成此操作后， running 将显示您在当前环境中安装的 Python 库，确认 OpenAI Python 库已成功安装。
之后可以直接通过 OpenAI 的相关接口进行调用，目前平台支持 OpenAI 相关的大多数参数。
```

---

## 在编程工具中使用本文档

**URL:** llms-txt#在编程工具中使用本文档

**Contents:**
- 1. 在 Cursor 中使用本文档
  - 1.1 在 Cursor 中增加 SiliconFlow 模型
  - 1.2 在 Cursor 中配置 SiliconFlow 文档
  - 1.3 在 Cursor 中使用文档
- 2. 关于 llmx.txt 的相关介绍
  - 2.1 协议背景
  - 2.2 文件结构：

Source: https://docs.siliconflow.cn/cn/userguide/use-docs-with-cursor

SiliconFlow 文档站支持 [llms.txt 协议](https://llmstxt.org/)，既可供用户直接查阅，也可无缝对接各类支持该协议的工具进行使用。<br />
考虑到部分用户可能对  [llms.txt 协议](https://llmstxt.org/) 不够熟悉，下面将简要介绍使用流程及相关概述。

## 1. 在 Cursor 中使用本文档

### 1.1 在 Cursor 中增加 SiliconFlow 模型

* 进入 Cursor 设置的 Models 页面，在 Models Names 列表底部输入框填写 SiliconFlow 平台的模型名称，点击`Add model`添加模型；
* 在 Models Names 列表中打开刚刚填入的模型开关；
* 在 OpenAI API Key 中 填写 SiliconFlow API Base URL 和 SiliconFlow API Key，点击 Verify 验证成功。

<Frame>
  <img width="500" src="https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=c5e9d057a098bd4b44cfeca0099158f4" data-og-width="2272" data-og-height="2204" data-path="images/usercases/genai-tools/cursor.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?w=280&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=917eee58a4e7c283f7c4cb9c3aec0a82 280w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?w=560&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=67bb456ade18fa1ea97fd8734298083d 560w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?w=840&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=16d62e3172250992cf618fd815a85580 840w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?w=1100&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=4c3413fa8a185461198d53f5f87fea77 1100w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?w=1650&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=17733a1e20795d897d065f48d3f71231 1650w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor.png?w=2500&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=39c9279cc2a134209fcadf867a1c9c65 2500w" />
</Frame>

### 1.2 在 Cursor 中配置 SiliconFlow 文档

配置 `Cursor` 的 `@Docs` 数据源，可以很方便的将本文档丢给 `Cursor` 使用。

<Frame>
  <img width="500" src="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=5acb9a2e680c796373b85fba3081e86e" data-og-width="1268" data-og-height="1012" data-path="images/usercases/genai-tools/cursor-1.jpeg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?w=280&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=10af45a975a34b6e6c67fcfd8b1d9514 280w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?w=560&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=e8d341e91dce3b26d7adda57c5dfacd1 560w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?w=840&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=01d55a665ab9b2574559c182ddfc385c 840w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?w=1100&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=c16a4ef8a06444979b545bb2e926a518 1100w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?w=1650&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=01d399ff76f89a7de17a5ac61aad7cdb 1650w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-1.jpeg?w=2500&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=cecdae378049b9bddbe0210dd5968b89 2500w" />
</Frame>

<Frame>
  <img width="500" src="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=75a80226da5e82a6dc1a4214eeeb9f50" data-og-width="2728" data-og-height="1460" data-path="images/usercases/genai-tools/cursor-3.jpeg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?w=280&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=7b542d5c8b9706af886d19e9332721e5 280w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?w=560&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=4277c8d527e534b7b7a68157002da092 560w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?w=840&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=ee06eba3f1bdce31ba2607f7a82d032f 840w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?w=1100&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=3a759b6ed2333446aeb7406b0a5c8c0e 1100w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?w=1650&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=4146b48fcdbf2e6aedf1c1333cf995bf 1650w, https://mintcdn.com/siliconflow-37161621/U5A4_TpbD-AXNY4h/images/usercases/genai-tools/cursor-3.jpeg?w=2500&fit=max&auto=format&n=U5A4_TpbD-AXNY4h&q=85&s=633b5d1af43ccd584d90c1526a093c8d 2500w" />
</Frame>

<Frame>
  <img width="500" src="https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=e2d1fba1a4f7bfd8dec8eb00d3a1496d" data-og-width="1728" data-og-height="794" data-path="images/usercases/genai-tools/cursor-4.jpeg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?w=280&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=cc21faf1da333621f6eff611f0136d00 280w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?w=560&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=818a81c4549fdbd8054ae3cb79b9c866 560w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?w=840&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=21755069d3490a1a90f98da51793e1be 840w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?w=1100&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=b3b97346ffe4e33465c506e7207132e3 1100w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?w=1650&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=9c7d497ac675d3dae3556463f2284237 1650w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-4.jpeg?w=2500&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=f5ab53684355c34e619c0ebdd0d402ee 2500w" />
</Frame>

### 1.3 在 Cursor 中使用文档

<Frame>
  <img width="500" src="https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=37d5a9df7f603aaeba680fc40f0526c6" data-og-width="1232" data-og-height="1804" data-path="images/usercases/genai-tools/cursor-5.jpeg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?w=280&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=f7ae6dfdf5097badb13d4d1f5c20b1ba 280w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?w=560&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=d2ae754db193a4e2d90cf9887bcd3160 560w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?w=840&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=163c0790526a3e2f59776385c0fb1736 840w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?w=1100&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=51e9356906d52b0e35dc116d59191bd7 1100w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?w=1650&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=41de5cd93273d71266b59b6085926cf9 1650w, https://mintcdn.com/siliconflow-37161621/JDJmbIjXH1Wv44Zd/images/usercases/genai-tools/cursor-5.jpeg?w=2500&fit=max&auto=format&n=JDJmbIjXH1Wv44Zd&q=85&s=79697d95d6f476d5a68367b31f16413b 2500w" />
</Frame>

## 2. 关于 llmx.txt 的相关介绍

llms.txt 是一种新兴的 Web 标准，旨在帮助大型语言模型（LLMs）更有效地访问和理解网站内容。通过在网站根目录下创建 llms.txt 文件，网站所有者可以为 AI 系统提供清晰的导航和指引，从而提升信息检索的效率。

llms.txt 文件采用 Markdown 格式，通常包含以下部分：

1. 标题：网站名称或项目名称。
2. 描述（可选）：对网站或项目的简要介绍。
3. 详细信息（可选）：提供更多背景信息或链接到其他文档。
4. 章节：列出网站的重要部分，每个部分包含链接和可选的详细说明。

示例如下（参考：[https://docs.siliconflow.cn/llms.txt](https://docs.siliconflow.cn/llms.txt) 和 [https://docs.siliconflow.cn/llms-full.txt](https://docs.siliconflow.cn/llms-full.txt) 文件)

```markdown  theme={null}

---
