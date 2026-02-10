# Seedance 2.0 分镜视频创作工具

将创意想法转化为专业分镜提示词，并通过即梦 API 直接生成视频、自动下载。

融合了 [elementsix-skills](https://github.com/elementsix/elementsix-skills) 的专业分镜提示词生成能力和 [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all) 的 Seedance 2.0 视频生成接口。

## 功能特点

- **专业分镜引导**：5 步引导流程，从创意到完整分镜提示词
- **多模态支持**：支持多图参考、角色一致性、运镜复刻
- **一键生成视频**：分镜提示词生成后直接调用 API 生成视频
- **自动下载**：视频生成后自动下载到本地
- **6 套分镜模板**：叙事/产品/角色/风景/延长/编辑
- **7 个完整示例**：覆盖常见视频创作场景

## 目录结构

```
seedance-video-creator/
├── SKILL.md                        # Skill 主文件（Claude Code 入口）
├── README.md                       # 本文件
├── templates/
│   └── storyboard-template.md      # 6 套分镜模板 + 词汇表
├── examples/
│   └── example-prompts.md          # 7 个完整示例（含 API 调用）
└── scripts/
    └── generate_video.sh           # 独立视频生成脚本
```

## 前置条件

### 1. 部署 jimeng-free-api-all

```bash
docker pull wwwzhouhui569/jimeng-free-api-all:latest
docker run -it -d --init --name jimeng-free-api-all \
  -p 8000:8000 -e TZ=Asia/Shanghai \
  wwwzhouhui569/jimeng-free-api-all:latest
```

### 2. 获取 SessionID

1. 打开 https://jimeng.jianying.com 并登录
2. F12 → Application → Cookies → 复制 `sessionid` 值

### 3. 配置环境变量（可选）

```bash
export JIMENG_API_URL="http://127.0.0.1:8000"
export JIMENG_SESSION_ID="your_sessionid_here"
```

## 使用方式

### 方式一：Claude Code Skill（推荐）

安装到 Claude Code 后，直接对话即可：

```
用户：帮我生成一个女孩在海边跳舞的视频
→ 自动引导分镜 → 生成提示词 → 调用 API → 下载视频
```

### 方式二：独立脚本

```bash
# 纯文本生成
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --prompt "电影级写实风格，10秒，海边女孩跳舞..."

# 多图参考生成
./scripts/generate_video.sh \
  --session-id "your_sessionid" \
  --prompt "@1 和 @2 两人开始跳舞" \
  --files dancer1.jpg dancer2.jpg \
  --ratio 4:3 --duration 10
```

## Seedance 2.0 参数说明

| 参数 | 可选值 | 默认值 |
|------|--------|--------|
| model | `seedance-2.0`, `seedance-2.0-pro` | `seedance-2.0` |
| ratio | `1:1`, `4:3`, `3:4`, `16:9`, `9:16` | `16:9` |
| resolution | `480p`, `720p`, `1080p` | `720p` |
| duration | `4`, `5`, `10` | `10` |

## 多图引用语法

提示词中使用 `@N` 引用上传的图片（按上传顺序）：

```
@1 和 @2 两人面对面站立，开始双人舞
```

等价写法：`@1` = `@image1` = `@图1`

## 致谢

- [elementsix-skills](https://github.com/elementsix/elementsix-skills) - Seedance 2.0 分镜提示词 Skill
- [jimeng-free-api-all](https://github.com/wwwzhouhui/jimeng-free-api-all) - 即梦 API 逆向接口

## 许可证

MIT License
