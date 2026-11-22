# article-cover-generator 双模型配置与维护

## 支持范围

`article-cover-generator` 使用同一个 Node.js 入口生成并下载一张文章封面：

| 模型 | 服务 | 选择方式 | 比例控制 |
| --- | --- | --- | --- |
| `gpt-image-2.5` | 第三方中转站 | 默认，或 `--model gpt-image-2.5` | 请求体发送 `size` |
| `MiniMax/MiniMax-H3-Image` | 魔搭社区 ModelScope | `--model MiniMax/MiniMax-H3-Image` | 提示词追加比例要求，最终以实际图片为准 |

脚本保持零 npm 依赖，要求 Node.js 18 或更高版本。两条调用链共享图片下载、落盘、格式检测和结果 JSON，不共享任务查询协议。

## 配置

把 `article-cover-generator/.env.example` 复制为同目录 `.env`。只需填写当前要使用的模型对应密钥：

```dotenv
# GPT 中转站
ARTICLE_COVER_MODEL=gpt-image-2.5
ARTICLE_COVER_API_BASE=https://image.mlgb7.com
ARTICLE_COVER_API_KEY=

# ModelScope MiniMax
ARTICLE_COVER_MODELSCOPE_API_BASE=https://api-inference.modelscope.cn
ARTICLE_COVER_MODELSCOPE_API_KEY=
```

脚本兼容技能目录 `.env` 的旧配置名 `MODEL` / `API_BASE` / `API_KEY` / `MODELSCOPE_API_BASE` / `MODELSCOPE_API_KEY`。进程环境只读取 `ARTICLE_COVER_*`，避免与其他工具的通用变量碰撞。除精确的 `MiniMax/MiniMax-H3-Image` 外，既有 `.env` 自定义 `MODEL` 值继续发送到 GPT 兼容网关。

配置优先级从高到低为：

1. 命令行 `--model`（只覆盖模型选择）。
2. 当前进程 `ARTICLE_COVER_*` 变量。
3. 技能目录 `.env` 中的 `ARTICLE_COVER_*` 变量，其次为兼容旧名。
4. 脚本内非敏感默认值。

同一服务的 BASE 与 KEY 必须来自同一层、同一套命名；如果进程只覆盖 BASE 而密钥只存在本地 `.env`，脚本会在发起网络请求前拒绝，避免把本地密钥发送到意外端点。

`.env` 已由仓库根 `.gitignore` 排除。Token 不得写进脚本、测试、提示词、README、进度日志或命令示例，也不要把带 Token 的终端截图提交到仓库。

## 使用命令

默认 GPT（Windows PowerShell / cmd 单行命令）：

```powershell
node article-cover-generator/scripts/gen_cover.mjs --prompt-file prompt.txt --ratio 16:9 --out cover.png
```

ModelScope MiniMax（Windows PowerShell / cmd 单行命令）：

```powershell
node article-cover-generator/scripts/gen_cover.mjs --model MiniMax/MiniMax-H3-Image --prompt-file prompt.txt --ratio 16:9 --out cover.png
```

支持的 `--ratio` 为 `16:9`、`9:16`、`3:4`、`4:3`、`1:1`，缺省为 `4:3`。`--size` 只用于 GPT 路径；ModelScope 托管接口的现有调用样例没有证明其接受该字段，因此 MiniMax 路径会拒绝 `--size`，避免发送未经确认的参数。

成功时标准输出最后一行是 JSON：

```json
{"ok":true,"path":"cover.png","format":"png","width":1280,"height":720,"ratio":"16:9","task_id":"...","provider":"modelscope","model":"MiniMax/MiniMax-H3-Image"}
```

其中 `ratio` 是请求的构图比例，`width` 和 `height` 是能从下载图片中识别出的实际尺寸。交付前仍需预览图片，核对文字、构图和真实比例。

## 两条异步协议

### GPT 中转站

1. `POST <API_BASE>/v1/images/generations`，提交模型、提示词和 size。
2. 从响应读取 `task_id` 或 `id`。
3. `GET <API_BASE>/api/image-tasks?ids=<task_id>`。
4. 成功后从 `items[0].results[0]` 下载 URL 或解码 `b64_json`。

### ModelScope MiniMax

1. `POST <MODELSCOPE_API_BASE>/v1/images/generations`，请求头带 `X-ModelScope-Async-Mode: true`。
2. 请求体只提交 `model` 和已补充比例要求的 `prompt`。
3. `GET <MODELSCOPE_API_BASE>/v1/tasks/<task_id>`，请求头带 `X-ModelScope-Task-Type: image_generation`。
4. `task_status=SUCCEED` 时下载 `output_images[0]`；`FAILED` 时停止并报告服务端错误。

ModelScope 托管协议按本次提供的接口样例实现。官方模型元数据中的原生 MiniMax `size`/`b64_json` 说明不等同于 ModelScope 托管接口，不能混用两套响应结构。

## 计费与失败边界

创建任务是可能计费且不可安全重复的操作。脚本对创建请求只提交一次：如果请求发送后连接中断，服务端可能已经创建任务，脚本会报错而不会自动再发。轮询阶段的临时网络错误可以继续查询同一个 task_id，但不会创建新任务。

出现以下情况时停止，不自动切换模型或重新生成：

- 创建请求网络结果不明确。
- 任务返回失败、取消或内容审核错误。
- 五分钟内未完成。
- 生成结果缺少图片地址。

重新生成、切换模型或改提示词都会产生新的任务，须先取得用户同意。

## 验证

静态与模拟验证：

```powershell
node --check article-cover-generator/scripts/gen_cover.mjs
node --check article-cover-generator/scripts/gen_cover.test.mjs
node --test article-cover-generator/scripts/gen_cover.test.mjs
```

测试使用 Node 内置 `node:test` 和模拟 HTTP 响应，不访问真实服务、不消耗额度，覆盖默认 GPT 路径、旧版自定义 GPT 模型、通用进程变量隔离、ModelScope 提交/轮询/首图下载、失败响应、模型密钥隔离、端点与密钥同源、无效参数零请求、无自动重复创建、轮询恢复、错误页拒绝落盘以及纯文件名输出。当前实测环境为 Windows Node.js `v24.21.0`；运行时代码要求 Node.js 18+，但本轮没有另行在 Node 18 执行测试。

真实 ModelScope 验证必须由用户明确授权，只生成一张临时测试图。Token 仅通过当前进程环境变量注入，测试图放在仓库外临时目录；验证返回 JSON、PNG/JPEG/WebP 魔数和实际尺寸后删除临时图，不把 Token 写入仓库文件或脚本输出。若 Token 曾在对话、工单或其他可留存渠道中明文提供，验证后应在 ModelScope 后台轮换。

2026-11-17 的一次获准验证中，任务一次创建后返回 `SUCCEED`，脚本下载并识别出 910,426 字节的 PNG（760×1280），临时文件随后删除。该次提示词要求 16:9 横图，但服务实际返回竖图，证明当前 ModelScope 路径不能保证提示词比例；使用 MiniMax 时必须按实际尺寸验收，不能把 `--ratio` 描述为精确尺寸控制。未为测试比例再次创建付费任务。

## 回滚

本次没有数据库、依赖或全局配置变更。若需撤销双模型支持，审核当前工作区后仅回退以下路径对应的本次差异：

- `article-cover-generator/scripts/gen_cover.mjs`
- `article-cover-generator/scripts/gen_cover.test.mjs`
- `article-cover-generator/.env.example`
- `article-cover-generator/SKILL.md`
- `docs/article-cover-generator.md`
- 根 `README.md` 与 `progress.md` 中 2026-11-17 对应条目

已存在的本地 `.env` 是用户凭证文件，不属于版本回滚范围，不要删除或提交。仓库当前可能包含其他未完成改动，禁止用 `git reset --hard` 或整仓覆盖回滚本功能。
