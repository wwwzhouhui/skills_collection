# Seedance 2.0 分镜视频创作工具

将创意想法转化为专业分镜提示词，通过即梦 API 先生成参考图，再基于图片+提示词生成视频、自动下载。

融合了 [elementsix-skills](https://github.com/elementsix/elementsix-skills) 的专业分镜提示词生成能力和 [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all) 的 Seedance 2.0 视频生成接口。

## 功能特点

- **三阶段工作流**：分镜提示词 → 文生图首帧 → 图片+提示词生成视频
- **专业分镜引导**：从创意到完整分镜提示词的引导流程
- **多模态支持**：支持多图参考、角色一致性、运镜复刻
- **自动首帧生成**：无用户图片时自动调用文生图 API 生成首帧参考图
- **一键生成视频**：分镜提示词生成后直接调用 API 生成视频
- **自动下载**：视频生成后自动下载到本地
- **6 套分镜模板**：叙事/产品/角色/风景/延长/编辑
- **7 个完整示例**：覆盖常见视频创作场景（含三阶段工作流示例）

## 核心约束

**Seedance 2.0 必须至少提供一张参考图片**，不支持纯文本生成视频。当用户没有提供图片时，工具会自动：
1. 生成首帧图片提示词（静态画面描述）
2. 调用文生图 API（`/v1/images/generations`）生成首帧参考图
3. 下载首帧图片到本地
4. 用首帧图片 + 视频分镜提示词调用 Seedance 2.0 生成视频

## 目录结构

```
seedance-video-creator/
├── SKILL.md                        # Skill 主文件（Claude Code 入口）
├── README.md                       # 本文件
├── templates/
│   └── storyboard-template.md      # 6 套分镜模板 + 词汇表
├── examples/
│   └── example-prompts.md          # 7 个完整示例（含三阶段工作流）
└── scripts/
    └── generate_video.sh           # 独立视频生成脚本（支持三阶段）
```

## 前置条件

### 1. 部署 jimeng-free-api-all（必须）

> **重要**：Seedance 2.0 系列模型**必须**使用 `jimeng-free-api-all` 镜像（非 `jimeng-free-api`）。
> 旧版 `jimeng-free-api` 不包含 Seedance 路由和浏览器代理（Playwright + bdms 签名），传入 `seedance-2.0-fast` 会被静默回退为 `jimeng-video-3.0`。

```bash
docker pull wwwzhouhui569/jimeng-free-api-all:latest
docker run -it -d --init --name jimeng-free-api-all \
  -p 8000:8000 -e TZ=Asia/Shanghai \
  wwwzhouhui569/jimeng-free-api-all:latest
```

验证 Seedance 模型可用：

```bash
curl -s http://127.0.0.1:8000/v1/models -H "Authorization: Bearer ${SESSION_ID}" | jq '.data[] | select(.id | contains("seedance"))'
```

如果返回结果包含 `seedance-2.0-fast`，说明部署正确。

### 2. 获取 SessionID

1. 打开 https://jimeng.jianying.com 并登录
2. F12 → Application → Cookies → 复制 `sessionid` 值

### 3. 配置环境变量（可选）

```bash
export JIMENG_API_URL="http://127.0.0.1:8000"  # 只填基础地址，不要包含路径
export JIMENG_SESSION_ID="your_sessionid_here"
```

## 使用方式

### 方式一：Claude Code Skill（推荐）

安装到 Claude Code 后，直接对话即可：

```
用户：帮我生成一个女孩在海边跳舞的视频
→ 自动引导分镜
→ 生成首帧提示词 + 视频提示词
→ 文生图生成首帧参考图
→ 首帧图片 + 提示词 → Seedance 2.0 生成视频
→ 下载视频
```

### 方式二：独立脚本

```bash
# 无图片 → 自动生成首帧 → 生成视频（三阶段）
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --image-prompt "海边沙滩，女孩穿白裙站在海边，夕阳逆光" \
  --prompt "@1 作为首帧参考，女孩开始旋转起舞..." \
  --ratio 9:16 --duration 4

# 有图片 → 直接生成视频（跳过文生图）
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --prompt "@1 和 @2 两人开始跳舞" \
  --files dancer1.jpg dancer2.jpg \
  --ratio 4:3 --duration 10

# 使用 Pro 模型 + 高分辨率
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --prompt "@1 和 @2 两人开始跳舞" \
  --files dancer1.jpg dancer2.jpg \
  --model jimeng-video-seedance-2.0 \
  --ratio 4:3 --duration 10 --resolution 1080p
```

## Seedance 2.0 参数说明

| 参数 | 可选值 | 默认值 |
|------|--------|--------|
| model | `seedance-2.0-fast`（推荐）, `jimeng-video-seedance-2.0-fast`, `jimeng-video-seedance-2.0`（Pro版）, `seedance-2.0`, `seedance-2.0-pro` | `seedance-2.0-fast` |
| ratio | `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `3:2`, `2:3`, `21:9` | `9:16` |
| resolution | `480p`, `720p`, `1080p` | `720p` |
| duration | `4` - `15` 秒（连续范围） | `4` |

## API 调用格式

### 文生图（生成首帧参考图）

```bash
curl -s --max-time 120 -X POST "${API_URL}/v1/images/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "jimeng-4.5",
    "prompt": "首帧画面描述...",
    "ratio": "9:16",
    "resolution": "2k"
  }'
```

### Seedance 视频生成（必须带图片）

```bash
curl -s --max-time 300 -X POST "${API_URL}/v1/videos/generations" \
  -H "Authorization: Bearer ${SESSION_ID}" \
  -F "model=seedance-2.0-fast" \
  -F "prompt=视频分镜描述，@1 作为首帧参考..." \
  -F "ratio=9:16" \
  -F "resolution=720p" \
  -F "duration=4" \
  -F "files=@/tmp/first_frame.png"
```

**注意**：
- Authorization 头**需要** `Bearer` 前缀，格式为 `Bearer your_sessionid`
- Seedance 2.0 **必须**至少上传一张图片
- 提示词中的 `@1`、`@2` 对应 `files` 参数中图片的上传顺序
- **必须使用 `jimeng-free-api-all` 镜像**，旧版 `jimeng-free-api` 不支持 Seedance 模型

## 多图引用语法

提示词中使用 `@N` 引用上传的图片（按上传顺序）：

```
@1 作为画面首帧参考
@1 和 @2 两人面对面站立，开始双人舞
```

等价写法：`@1` = `@image1` = `@图1`

## 致谢

- [elementsix-skills](https://github.com/elementsix/elementsix-skills) - Seedance 2.0 分镜提示词 Skill
- [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all) - 即梦 API 逆向接口

## 许可证

MIT License
