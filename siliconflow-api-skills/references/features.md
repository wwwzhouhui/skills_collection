# Siliconflow - Features

**Pages:** 2

---

## LazyLLM

**URL:** llms-txt#lazyllm

**Contents:**
- API 申请和环境配置
  - 1. 账号注册
  - 2. 环境配置
- API 使用测试
  - 0. 设置环境变量
  - 1. 实现对话和图片识别
  - 2. 实现文生图和文生语音
  - 3. 10+行代码实现知识库问答

Source: https://docs.siliconflow.cn/cn/usercases/use-siliconcloud-in-lazyllm

LazyLLM 是由商汤 LazyAGI 团队开发的一款开源低代码大模型应用开发工具，提供从应用搭建、数据准备、模型部署、微调到评测的一站式工具支持，以极低的成本快速构建 AI 应用，持续迭代优化效果。

* 注册硅基流动账号。[点击注册](https://cloud.siliconflow.cn/i/TR9Ym0c4)
* 进入控制台，[获取 API key](https://cloud.siliconflow.cn/account/ak)。

参考网页：[快速开始 - LazyLLM](https://docs.lazyllm.ai/zh-cn/stable/)

可以使用以下命令设置对应的环境变量。或从代码中显示给入:

填好 api\_key 后，运行下面代码可以迅速调用模型并生成一个问答形式的前端界面:

我们询问“什么是 LazyLLM ”，运行结果如下:

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=5c524605d1d5f9f768e1a08a872043b5" data-og-width="1910" width="1910" data-og-height="923" height="923" data-path="images/usercases/LazyLLM/1.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=baac190a4f940a18846c4c3c3d1f831e 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=40c0863b8a37b3628142f3ca3b7c3aeb 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=9d203d2b1284af2fe1ca4799f833efce 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=c28a38044c1f9b31f9aa19bc4f5f4951 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=c237e0ed8b9f9b8f22e67b82f3e06c1c 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/1.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=00424887097696c93d8ff7178d1b599b 2500w" />
</Frame>

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=aab59e6fe140f254606a024eb2674281" data-og-width="1910" width="1910" data-og-height="923" height="923" data-path="images/usercases/LazyLLM/2.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=e340db97d1a08fdf32d4a398852ea79e 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=65779b6681b79958d805214e40db0364 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=fb6f63397dfb45439ff999ead9ddbd19 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=b5dad1165ff859fbf3f71f380239a594 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=a15ec1e5f4a9e2497b28c3f3610b9d12 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/2.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=3305ffbc877876f4e49eec8f5935307f 2500w" />
</Frame>

在输入中通过 lazyllm\_files 参数传入一张图片，并询问图片的内容，就可以实现多模态的问答。

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=2bebba994217eacd7be23e9efe4ff3b2" data-og-width="554" width="554" data-og-height="555" height="555" data-path="images/usercases/LazyLLM/3.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=b7ec9f8719c89240cbf140a2d654ca65 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=9e81e4fc99be3b4519411a0ce51c6f3d 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=dd05c0cf69f6d68848b5295c8892e1d6 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=606eede14ca92d842d3a4122bf63ef1e 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=40596bc9093ddf63eea3d50c39d17a60 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/3.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=a7fd0b4b3a11fae0ff1c3681cff337ba 2500w" />
</Frame>

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=777dbe36a162128ea8be071d7bb02463" data-og-width="1488" width="1488" data-og-height="49" height="49" data-path="images/usercases/LazyLLM/4.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=0d6e84f803fec26ede87dcb381047e53 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=e93797f405d0ceab995b6f67b961f4b7 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=eb08fc308c526a7f124b95e609c576f7 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=5ef455f541455fb600ab1d6d33b3f482 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=558eb7f75886332535e8df1332bd46a5 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/4.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=520e07c8b7a307a135e24ef3217af7de 2500w" />
</Frame>

使用`OnlineMultiModalModule`进行文生图和文生语音，运行后会输出生成的文件路径

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=55af397cf01449ddc96d596d195c2201" data-og-width="564" width="564" data-og-height="566" height="566" data-path="images/usercases/LazyLLM/5.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=a1d9981d9116ebfc7bfd947b8b642dc6 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=3b17ee7154d328107681b6bc7e10713c 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=f466a04acba012732896ccdb4274c59b 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=7a389e9034990fc8b990b974eb2776b6 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=a10bade263735181d3062b35188b2f59 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/5.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=ca275773b01b196a986249f7d4d9b505 2500w" />
</Frame>

| [tmpck44zfds.mp3](https://ones.ainewera.com/wiki/?/team/JNwe8qUX/share/7fy5a6mk/page/FUcz8wKs/) | 55.13 KB | 2025-10-27 23:13 |
| ----------------------------------------------------------------------------------------------- | -------- | ---------------- |

#### 实现 Eembed 和 Rerank 功能

运行下面代码，使用`OnlineEmbeddingModule`进行向量化嵌入；设置`type='rerank'`调用重排序模型。

我们使用中国古典文籍作为示例知识库，下载后放在 database 文件夹。示例数据集下载链接：[示例数据集下载](https://huggingface.co/datasets/LazyAGI/Chinese_Classics_Articles/tree/main)

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=0f75b8b4bb6c42971a19b137fc14d174" data-og-width="1640" width="1640" data-og-height="797" height="797" data-path="images/usercases/LazyLLM/6.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=d31dcea11682f4628203dd49545482a5 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=d1b0742fea021c73b3c0cf52f3d97a82 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=a1d731daa7c8c18d900b7ca3a86466a9 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=74d1635cfd7b08a812aea09aa1ad63e2 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=3069f26527bc4f8e7f4e2b8527bdd647 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=af8b441621548aef505feb661e3f148e 2500w" />
</Frame>

首先定义 embed 模型，然后使用 LazyLLM 的 Document 组件创建文档管理模块，以实现知识库的导入。

现在有了外部知识库，LazyLLM 中使用 Retriever 组件可以实现检索知识库并召回相关内容。
使用示例：

结合上述模型、文档管理和检索模块，搭配 LazyLLM 内置的 Flow 组件进行完整的数据流搭建，完整代码如下：

可以看到 RAG 很好地从《道德经》等中取回了有关天道的内容，并传给大模型进行回答。

<Frame>
  <img src="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=0f75b8b4bb6c42971a19b137fc14d174" data-og-width="1640" width="1640" data-og-height="797" height="797" data-path="images/usercases/LazyLLM/6.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=280&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=d31dcea11682f4628203dd49545482a5 280w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=560&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=d1b0742fea021c73b3c0cf52f3d97a82 560w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=840&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=a1d731daa7c8c18d900b7ca3a86466a9 840w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=1100&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=74d1635cfd7b08a812aea09aa1ad63e2 1100w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=1650&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=3069f26527bc4f8e7f4e2b8527bdd647 1650w, https://mintcdn.com/siliconflow-37161621/2dL2FkzVjBU52Ce2/images/usercases/LazyLLM/6.png?w=2500&fit=max&auto=format&n=2dL2FkzVjBU52Ce2&q=85&s=af8b441621548aef505feb661e3f148e 2500w" />
</Frame>

**Examples:**

Example 1 (unknown):
```unknown
export LAZYLLM_SILICONFLOW_API_KEY=<申请到的api key>
```

Example 2 (unknown):
```unknown
import lazyllm
    from lazyllm import OnlineChatModule,WebModule
    api_key = 'sk-' #替换成申请的api
    # # 测试chat模块
    llm = OnlineChatModule(source='siliconflow', api_key=api_key, stream=False)
    w = WebModule(llm, port=8846, title="siliconflow")
    w.start().wait()
```

Example 3 (unknown):
```unknown
import lazyllm
    from lazyllm import OnlineChatModule
    api_key = 'sk-' #替换成申请的api
    llm = OnlineChatModule(source='siliconflow', api_key=api_key,
    model='Qwen/Qwen2.5-VL-72B-Instruct')
    print(llm('你好，这是什么？', lazyllm_files=['your_picture.png']))
```

Example 4 (unknown):
```unknown
import lazyllm
    from lazyllm import OnlineMultiModalModule
    api_key = 'sk-xxx'
    # 测试文生图 fuction=text2image
    llm =OnlineMultiModalModule(source='siliconflow',api_key=api_key,function='text2image')
    print(llm("生成一个可爱的小狗"))
    #测试文生语音 function=tts
    llm = OnlineMultiModalModule(source='siliconflow',api_key=api_key,function='tts')
    print(llm("你好，你叫什么名字",voice='fnlp/MOSS-TTSD-v0.5:anna'))
```

---

## 定义 OpenAI 的 function calling tools

**URL:** llms-txt#定义-openai-的-function-calling-tools

tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': 'Get the current weather for a given city.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {
                        'type': 'string',
                        'description': 'The name of the city to query weather for.',
                    },
                },
                'required': ['city'],
            },
        }
    }
]

---
