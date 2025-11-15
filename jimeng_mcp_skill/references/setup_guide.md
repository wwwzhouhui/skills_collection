# 即梦 MCP 服务器设置指南

即梦-mcp-server 的完整安装和配置指南。

## 目录

1. [前置条件](#前置条件)
2. [后端 API 设置](#后端-api-设置)
3. [MCP 服务器安装](#mcp-服务器安装)
4. [客户端配置](#客户端配置)
5. [验证](#验证)
6. [故障排除](#故障排除)

---

## 前置条件

### 系统要求

- **操作系统**：Ubuntu 20.04+ / macOS 12+ / Windows 10/11 (WSL2)
- **内存**：至少 4GB RAM
- **磁盘空间**：至少 10GB 可用空间
- **Python**：3.10 或更高版本
- **Docker**：最新版本
- **Git**：用于克隆仓库

### 检查前置条件

```bash
# 检查 Python 版本
python --version  # 应该是 3.10.x 或更高版本

# 检查 Docker
docker --version
docker-compose --version

# 检查 Git
git --version
```

---

## 后端 API 设置

jimeng-mcp-server 需要 jimeng-free-api-all 后端服务。

### 步骤 1：获取即梦 API 密钥

1. 访问 https://jimeng.jianying.com/
2. 登录您的账户
3. 打开浏览器开发者工具（F12）
4. 前往 Application > Cookies
5. 找到 `sessionid` 值 - 这就是您的 API 密钥
6. 复制 sessionid 值（格式：`Bearer <sessionid>`）

### 步骤 2：拉取 Docker 镜像

```bash
docker pull wwwzhouhui569/jimeng-free-api-all:latest
```

### 步骤 3：启动后端容器

```bash
docker run -it -d --init \
  --name jimeng-free-api-all \
  -p 8001:8000 \
  -e TZ=Asia/Shanghai \
  wwwzhouhui569/jimeng-free-api-all:latest
```

**端口说明：**
- 主机端口 8001 → 容器端口 8000
- 访问地址：http://localhost:8001

### 步骤 4：验证后端

```bash
# 检查容器是否运行
docker ps | grep jimeng

# 测试 API 端点
curl http://localhost:8001/health
```

预期响应：`{"status": "ok"}`

---

## MCP 服务器安装

### 步骤 1：克隆仓库

```bash
git clone https://github.com/wwwzhouhui/jimeng-mcp-server.git
cd jimeng-mcp-server
```

### 步骤 2：安装依赖

**方法 A：使用 uv（推荐）**

```bash
# 如果尚未安装，请先安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或在 Windows 上：.venv\Scripts\activate

# 安装依赖
uv pip install -e .
```

**方法 B：使用 pip**

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或在 Windows 上：.venv\Scripts\activate

# 安装依赖
pip install -e .
```

### 步骤 3：配置环境

在项目根目录创建 `.env` 文件：

```bash
touch .env
```

编辑 `.env` 文件，填入您的配置：

```env
# 即梦 API 配置

# 您的即梦 API 密钥（必需）- 使用从 cookies 获取的 sessionid
JIMENG_API_KEY=your_sessionid_here

# API 基础 URL（可选，默认：https://jimeng.duckcloud.fun）
JIMENG_API_URL=http://127.0.0.1:8001

# 模型名称（可选，默认：jimeng-4.0）
JIMENG_MODEL=jimeng-4.0
```

**重要说明：**
- `JIMENG_API_KEY`：粘贴从即梦网站获取的 sessionid 值
- `JIMENG_API_URL`：本地后端使用 `http://127.0.0.1:8001`
- 不要在值周围添加引号

---

## 客户端配置

### Claude Desktop

**配置文件位置：**
- **macOS**：`~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**：`%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**：`~/.config/Claude/claude_desktop_config.json`

**stdio 模式（本地）：**

```json
{
  "mcpServers": {
    "jimeng": {
      "command": "python",
      "args": ["-m", "jimeng_mcp.server"],
      "env": {
        "JIMENG_API_KEY": "your_sessionid_here",
        "JIMENG_API_URL": "http://127.0.0.1:8001"
      }
    }
  }
}
```

**使用 .env 文件的替代方案：**

```json
{
  "mcpServers": {
    "jimeng": {
      "command": "python",
      "args": ["-m", "jimeng_mcp.server"]
    }
  }
}
```

如果使用此方法，请确保 `.env` 文件存在于项目目录中。

### Cherry Studio

**SSE 模式配置：**

1. 打开 Cherry Studio 设置
2. 导航到 MCP 服务器
3. 添加新服务器：
   - **名称**：Jimeng
   - **类型**：SSE
   - **URL**：`http://localhost:8080/sse`

**启动 SSE 服务器：**

```bash
cd jimeng-mcp-server
source .venv/bin/activate
python -m jimeng_mcp.server --transport sse --port 8080
```

### Cline / 其他 MCP 客户端

类似于 Claude Desktop 配置。根据您的客户端需要调整路径和环境变量。

---

## 验证

### 测试文本生成图像

在您的 MCP 客户端（Claude Desktop、Cherry Studio 等）中：

```
生成一张图片：樱花树下的柴犬
```

或

```
Generate an image: a cute dog under cherry blossom tree
```

**预期行为：**
1. 客户端识别请求
2. 调用 jimeng-mcp-server 的 `text_to_image` 工具
3. 返回图片 URL
4. 可以查看/下载图片

### 测试图像合成

```
合成这两张图片：
- 图片1: [URL]
- 图片2: [URL]
创建无缝融合效果
```

### 测试文本生成视频

```
创建一个视频：小猫在钓鱼
```

**注意**：视频生成需要 30-60 秒。

### 测试图像生成视频

```
为这张图片添加动画效果：[image URL]
添加轻柔的运动和镜头缩放
```

---

## 故障排除

### 问题："服务器无响应"

**症状：**
- 连接被拒绝错误
- 调用工具时超时

**解决方案：**

1. 检查后端容器状态：
   ```bash
   docker ps | grep jimeng
   ```

2. 如果未运行，重启后端：
   ```bash
   docker restart jimeng-free-api-all
   ```

3. 验证端口可访问性：
   ```bash
   curl http://localhost:8001/health
   ```

4. 检查防火墙设置

### 问题："API 密钥无效"

**症状：**
- 身份验证错误
- "未授权"响应

**解决方案：**

1. 从即梦网站获取新的 sessionid：
   - 登录到 https://jimeng.jianying.com/
   - F12 > Application > Cookies > sessionid
   - 复制新值

2. 更新 `.env` 文件：
   ```env
   JIMENG_API_KEY=new_sessionid_value
   ```

3. 重启 MCP 服务器

### 问题："生成失败"

**症状：**
- 工具返回错误
- 没有生成图片/视频

**解决方案：**

1. 检查后端日志：
   ```bash
   docker logs jimeng-free-api-all
   ```

2. 验证提示词不为空

3. 检查到即梦 API 的网络连接

4. 先尝试更简单的提示词

5. 确保有足够的 API 积分（免费层每天 66 积分）

### 问题："生成超时"

**症状：**
- 请求时间过长
- 60+ 秒后仍无响应

**解决方案：**

1. 对于视频，最多等待 90 秒
2. 尝试较低分辨率（720p 而非 1080p）
3. 检查服务器资源使用情况：
   ```bash
   docker stats jimeng-free-api-all
   ```
4. 如果 CPU/内存占用高，重启后端

### 问题："模块未找到"

**症状：**
- Python 导入错误
- "No module named 'jimeng_mcp'"

**解决方案：**

1. 确保虚拟环境已激活：
   ```bash
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 重新安装依赖：
   ```bash
   pip install -e .
   ```

3. 验证 Python 版本：
   ```bash
   python --version  # 必须是 3.10+
   ```

---

## 高级配置

### 运行多个实例

要运行多个 jimeng-mcp-server 实例：

1. **为后端使用不同端口：**
   ```bash
   docker run -d -p 8001:8000 --name jimeng-api-1 ...
   docker run -d -p 8002:8000 --name jimeng-api-2 ...
   ```

2. **配置不同的 MCP 服务器：**
   ```json
   {
     "mcpServers": {
       "jimeng-1": {
         "command": "python",
         "args": ["-m", "jimeng_mcp.server"],
         "env": {"JIMENG_API_URL": "http://127.0.0.1:8001"}
       },
       "jimeng-2": {
         "command": "python",
         "args": ["-m", "jimeng_mcp.server"],
         "env": {"JIMENG_API_URL": "http://127.0.0.1:8002"}
       }
     }
   }
   ```

### 自定义 API 端点

如果使用托管的 jimeng-free-api-all 实例：

```env
JIMENG_API_URL=https://your-domain.com
JIMENG_API_KEY=your_api_key
```

### 日志配置

启用调试日志：

```env
LOG_LEVEL=DEBUG
```

查看日志：
```bash
# 对于 stdio 模式：查看客户端日志
# 对于 SSE 模式：查看服务器控制台输出
```

---

## 安全最佳实践

1. **永远不要将 .env 文件提交到版本控制**
   - 将 `.env` 添加到 `.gitignore`

2. **保护 API 密钥**
   - 不要公开分享 sessionid
   - 如果泄露请重新生成

3. **限制网络暴露**
   - 尽可能使用 localhost (127.0.0.1)
   - 不要公开暴露 Docker 端口

4. **保持依赖更新**
   ```bash
   pip install --upgrade jimeng-mcp-server
   ```

5. **监控使用情况**
   - 跟踪 API 积分消耗
   - 为配额限制设置警报

---

## 卸载

### 移除 MCP 服务器

```bash
# 停用虚拟环境
deactivate

# 移除项目目录
rm -rf jimeng-mcp-server
```

### 停止后端

```bash
# 停止并移除容器
docker stop jimeng-free-api-all
docker rm jimeng-free-api-all

# 移除镜像（可选）
docker rmi wwwzhouhui569/jimeng-free-api-all:latest
```

### 移除客户端配置

编辑 MCP 客户端配置文件，移除 jimeng 服务器条目。

---

## 获取帮助

- **GitHub 问题**：https://github.com/wwwzhouhui/jimeng-mcp-server/issues
- **文档**：查看项目 README 和 API 参考
- **社区**：查看讨论或论坛

---

## 更新日志

### 最新更新

查看 GitHub 发布页面了解版本历史和变更：
https://github.com/wwwzhouhui/jimeng-mcp-server/releases

---

**最后更新**：2025-11-15
**版本**：1.0.0
