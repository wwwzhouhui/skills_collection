# Siliconflow - Userguide

**Pages:** 6

---

## 批量推理

**URL:** llms-txt#批量推理

**Contents:**
- 1. 概述
- 2. 使用流程
  - 2.1 准备批量推理任务的输入文件
  - 2.2 上传批量推理任务的输入文件

Source: https://docs.siliconflow.cn/cn/userguide/guides/batch

通过批量 API 发送批量请求到 SiliconFlow 云服务平台，不受在线的速率限制和影响，预期可以在 24 小时内完成，且价格降低 50%。该服务非常适合一些不需要立即响应的工作，比如大型的任务评估、信息分类与提取、文档处理等。批量处理结果文件的 URL 有效期为一个月，请及时转存，以防过期影响业务。

### 2.1 准备批量推理任务的输入文件

批量推理任务输入文件格式为 .jsonl，其中每一行都是一个完整的 API 请求的消息体，需满足以下要求：

* 每一行必须包含`custom_id`，且每个`custom_id`须在当前文件中唯一；
* 每一行的`body`中的必需包含`messages`对象数组，且数组中消息对象的`role` 为`system`、`user`或`assistant`之一，并且整个数组以`user`消息结束；
* 您可以为每一行数据按需设置相同或不同的推理参数，如设定不同的`temperature`、`top_p`；
* 如果您希望使用 OpenAI SDK 调用 SiliconFlow 批量推理，您需要保证同一输入文件中`model`是统一的。
* 每 batch 限制：单个 batch 对应的输入文件的大小最大1 G
* 批量推理输入限制：单个 批量推理 对应的输入文件的大小不超过 1 G，**文件行数不超过 5000 行**。
  下面是一个包含 2 个请求的输入文件示例：

其中`custom_id`和`body`的`messages`是必须内容，其他部分为非必需内容。

对于推理模型，可以通过 thinking\_budget 字段控制模型的思维链输出长度，示例如下：

### 2.2 上传批量推理任务的输入文件

您需要首先上传输入文件，以便在启动批量推理时使用。以下为使用 OpenAI SDK 调用 SiliconFlow 输入文件的示例。

```python  theme={null}
from openai import OpenAI
client = OpenAI(
    api_key="YOUR_API_KEY", 
    base_url="https://api.siliconflow.cn/v1"
)

batch_input_file = client.files.create(
    file=open("batch_file_for_batch_inference.jsonl", "rb"),
    purpose="batch"
)
print(batch_input_file)

**Examples:**

Example 1 (unknown):
```unknown
其中`custom_id`和`body`的`messages`是必须内容，其他部分为非必需内容。

对于推理模型，可以通过 thinking\_budget 字段控制模型的思维链输出长度，示例如下：
```

Example 2 (unknown):
```unknown
### 2.2 上传批量推理任务的输入文件

您需要首先上传输入文件，以便在启动批量推理时使用。以下为使用 OpenAI SDK 调用 SiliconFlow 输入文件的示例。
```

---

## JSON 模式

**URL:** llms-txt#json-模式

**Contents:**
- 1. 使用场景
- 2. 使用方式
- 3. 支持模型列表
- 4. 使用示例

Source: https://docs.siliconflow.cn/cn/userguide/guides/json-mode

目前，硅基流动的大模型 API 平台 SiliconFlow 默认生成**非结构化文本**，但在某些应用场景中，您可能希望模型以**结构化**的形式输出内容，但用提示词的方式直接告诉大模型却无法获得正确的结构化输出。

作为一种标准化、轻量级的数据交换格式，JSON 模式是支持大模型 API 进行结构化输出的重要功能。当您调用大模型的 API 进行请求时，模型返回的结果以 JSON 格式呈现，易于人类阅读和编写，同时也易于机器解析和生成。

现在，SiliconFlow 平台上除了 VL 模型外，其他主要语言模型均已支持 JSON 模式，能让模型输出 JSON 格式的字符串，以确保模型以预期的结构输出，便于后续对输出内容进行逻辑解析。

比如，您现在可以通过 SiliconFlow API 对以下案例尝试结构化输出：

* 从公司相关报道中构建新闻数据库，包括新闻标题、链接等。
* 从商品购买评价中提取出情感分析结构，包括情感极性（正面、负面、中性）、情感强度、情感关键词等。
* 从商品购买历史中提取出产品列表，包括产品信息、推荐理由、价格、促销信息等。

目前线上，平台提供的大语言类模型都支持上述参数。

<Note>注意：支持的模型情况可能会发生变化，请查阅本文档了解最新支持的模型列表。</Note>
<Note>你的应用必须检测并处理可能导致模型输出不完整JSON对象的边缘案例。</Note>
<Note>请合理设置max\_tokens，防止JSON字符串被中断。</Note>

**Examples:**

Example 1 (unknown):
```unknown
## 3. 支持模型列表

目前线上，平台提供的大语言类模型都支持上述参数。

<Note>注意：支持的模型情况可能会发生变化，请查阅本文档了解最新支持的模型列表。</Note>
<Note>你的应用必须检测并处理可能导致模型输出不完整JSON对象的边缘案例。</Note>
<Note>请合理设置max\_tokens，防止JSON字符串被中断。</Note>

## 4. 使用示例

下面是在 OpenAI 中使用的例子：
```

Example 2 (unknown):
```unknown
模型将输出：
```

---

## OneDiff 多模态推理加速引擎

**URL:** llms-txt#onediff-多模态推理加速引擎

Source: https://docs.siliconflow.cn/cn/userguide/products/onediff

---

## SiliconFlow 平台

**URL:** llms-txt#siliconflow-平台

Source: https://docs.siliconflow.cn/cn/userguide/products/siliconcloud

---

## 企业级 MaaS 平台

**URL:** llms-txt#企业级-maas-平台

Source: https://docs.siliconflow.cn/cn/userguide/products/siliconllm

---

## Rate Limits

**URL:** llms-txt#rate-limits

**Contents:**
- 1. Rate Limits 概述
  - 1.1 什么是 Rate Limits
  - 1.2 为什么做 Rate Limits
  - 1.3 Rate Limits 指标
  - 1.4 不同模型的 Rate Limits 指标
  - 1.5 Rate Limits 主体
- 2. Rate Limits 规则
  - 2.1 免费模型Rate Limits
  - 2.2 收费模型 Rate Limits
  - 2.3 用户用量级别与 Rate Limits

Source: https://docs.siliconflow.cn/cn/userguide/rate-limits/rate-limit-and-upgradation

### 1.1 什么是 Rate Limits

Rate Limits 是指用户 API 在指定时间内访问 SiliconFlow 平台服务频次规则。

### 1.2 为什么做 Rate Limits

Rate Limits 是 API 的常见做法，其实施原因如下：

* **保障资源的公平性及合理利用**：确保资源公平使用。 防止某些用户过多请求，影响其他用户的正常使用体验。
* **防止请求过载**：提高服务可靠性。帮助管理平台总体负载，避免因请求激增而导致服务器出现性能问题。
* **安全防护**：防止恶意性攻击，导致平台过载甚至服务中断。

### 1.3 Rate Limits 指标

* RPM（ requests per minute，一分钟最多发起的请求数）
* RPH（ requests per hour，每小时允许的最大请求数）
* RPD (Requests per day，每天允许的最大请求数)
* TPM（ tokens per minute，一分钟最多允许的 token 数）
* TPD（ tokens per day，每天最多允许的 token 数）
* IPM（ images per minute，一分钟最多生成的图片数）
* IPD（ images per day，一天最多生成的图片数）

### 1.4 不同模型的 Rate Limits 指标

| 模型名称                      | Rate Limit指标 | 当前指标                               |
| ------------------------- | ------------ | ---------------------------------- |
| 语言模型(Chat)                | RPM、 TPM     | RPM=1000-10000 TPM=50000-5000000   |
| 向量模型(Embedding)           | RPM、 TPM     | RPM:2000-10000 TPM:500000-10000000 |
| 重排序模型(Reranker)           | RPM、 TPM     | RPM:2000 TPM:500000                |
| 图像生成模型(Image)             | IPM、IPD      | IPM:2  IPD:400                     |
| 多模态模型 (Multimodal Models) | -            | -                                  |

Rate Limits 可能会因在任一选项（RPM、RPH、RPD、TPM、TPD、IPM、IPD）中达峰而触发，取决于哪个先发生。
例如，在 RPM 限制为20，TPM 限制为 200K 时，一分钟内，账户向 ChatCompletions 发送了 20 个请求，每个请求有 100个Token ，限制即触发，即使账户在这些 20 个请求中没有发满 200K 个 Token。

<Note>注意：每个模型的Rate Limits 可以通过[模型广场](https://cloud.siliconflow.cn/me/models)进行查询。</Note>

### 1.5 Rate Limits 主体

1. Rate Limit是在用户账户级别定义的，而不是密钥（API key）维度。
2. 每个模型**单独设置  Rate Limits**，一个模型请求超出  Rate Limits 不影响其他模型正常使用。

* 当前免费模型 Rate Limits 指标是固定值，收费模型根据账户[用量级别](https://account.siliconflow.cn/user/settings)有不同的 [Rate Limits 指标](https://cloud.siliconflow.cn/models)。
* 同一用量级别下，模型类别不同、模型参数量不同，Rate Limits 峰值不同。

### 2.1 免费模型Rate Limits

1. **[实名认证](/faqs/authentication)后使用全部的免费模型。**
2. **免费模型调用免费**，账户的[费用账单](https://cloud.siliconflow.cn/bills)中看到此类模型的费用为调用消耗是 0。
3. **免费模型的 Rate Limits 固定**。对于部分模型，平台同时提供**免费版**和**收费版**。免费版按照原名称命名；收费版会在**名称前加上“Pro/”以示区分**。例如，Qwen2.5-7B-Instruct 的免费版命名为“Qwen/Qwen2.5-7B-Instruct”，收费版则命名为“Pro/Qwen/Qwen2.5-7B-Instruct”。

### 2.2 收费模型 Rate Limits

1. 按照用量付费。API 调用消耗**计入**账户[费用账单](https://cloud.siliconflow.cn/bills)。
2. 根据账户**用量级别**进行分层  Rate Limits 。 Rate Limits 峰值随着用量级别提升而增大。
3. 同一用量级别下，模型类别不同、模型参数量大小不同， Rate Limits 峰值不同。

### 2.3 用户用量级别与 Rate Limits

平台依据账户每月消费金额将其划分为不同的用量级别，每个级别有各自的  Rate Limits 标准。月消费达到更高级别标准时，自动升级至相应用量级别。升级立即生效，并提供更宽松的  Rate Limits。

* **月消费金额**：包含充值金额消费和赠送金额在内的账户每个月的总[消费金额](https://cloud.siliconflow.cn/bills)。
* **级别设置**：比较**上个自然月**和**当月 1 号到今日**的消费金额，取最高值换算成对应的用量级别。新用户注册后初始用量级别为L0。

| 用量级别 | 资质（单位：人民币元）                    |
| ---- | ------------------------------ |
| L0   | 上月或当月消费金额最高值 \< ¥50            |
| L1   | ¥50 ≤ 上月或当月消费金额最高值 \< ¥200     |
| L2   | ¥200 ≤ 上月或当月消费金额最高值 \< ¥2000   |
| L3   | ¥2000 ≤ 上月或当月消费金额最高值 \< ¥5000  |
| L4   | ¥5000 ≤ 上月或当月消费金额最高值 \< ¥10000 |
| L5   | ¥10000 ≤ 上月或当月消费金额最高值          |

### 2.4 具体模型的 Rate Limits

平台目前提供文本生成、图像生成、向量化、重排序和语音五大类，具体模型的  Rate Limits 指标在[模型广场](https://cloud.siliconflow.cn/models)中查看。

## 3. 超出 Rate Limits 处理

### 3.1 超出 Rate Limits 报错信息

如果超出  Rate Limits 调用限制，用户的 API 请求将会因为超过  Rate Limits 而失败。用户需要等待一段时间待满足  Rate Limits 条件后方能再次调用。对应的 HTTP 错误信息为：

### 3.2 超出 Rate Limits 处理方式

* 在已有的Rate Limits下，可以参考 [超出  Rate Limits 处理](https://github.com/siliconflow/siliconcloud-cookbook/blob/main/examples/how-to-handle-rate-limit-in-siliconcloud.ipynb)
  进行错误回避。
* 也可以通过提升用量级别来提升模型  Rate Limits 峰值，业务目标。

## 4. 如何提升模型 Rate Limits 指标

* 根据用量自动升级：您可以通过提高用量来增加[月消费金额](https://cloud.siliconflow.cn/bills)，满足下一级别资质时，会自动升级。
* 购买等级包快速提升：如果您需要**快速达到**更高用量级别、提高  Rate Limits 峰值，请[联系我们](https://siliconflow.feishu.cn/share/base/form/shrcnxIMbsUUDf7xjrRIjenRYoh?hide_user_id=1\&prefill_user_id=sfd17aubjk20jc73ada8ng)。

---
