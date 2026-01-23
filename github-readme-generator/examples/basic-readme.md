# My Awesome Project

一个简洁的项目示例，展示基础 README 结构

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-v1.0.0-green.svg)

## 项目介绍

这是一个示例项目，用于展示基础 README 的标准结构。

### 核心功能

- 功能一：用户管理
- 功能二：数据同步
- 功能三：报表导出

## 功能清单

| 功能名称 | 功能说明 | 状态 |
|---------|---------|------|
| 用户管理 | 用户增删改查 | 已完成 |
| 数据同步 | 定时同步数据 | 开发中 |
| 报表导出 | Excel/PDF 导出 | 计划中 |

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Go | 1.19 | 后端服务 |
| Vue | 3.2 | 前端界面 |
| MySQL | 8.0 | 数据存储 |

## 安装说明

### 环境要求

- Go 1.19+
- Node.js 16+
- MySQL 8.0+

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/user/my-awesome-project.git

# 安装后端依赖
cd backend
go mod download

# 安装前端依赖
cd ../frontend
npm install

# 配置数据库
cp .env.example .env
vim .env

# 启动服务
make dev
```

## 使用说明

### 快速开始

```bash
# 启动所有服务
make dev

# 访问应用
open http://localhost:8080
```

### 配置说明

编辑 `.env` 文件配置数据库连接：

```bash
DB_HOST=localhost
DB_PORT=3306
DB_NAME=myapp
DB_USER=root
DB_PASS=password
```

### 使用示例

```bash
# 创建用户
curl -X POST http://localhost:8080/api/users \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","email":"zhangsan@example.com"}'

# 查询用户
curl http://localhost:8080/api/users/1
```

## 常见问题

<details>
<summary>安装失败怎么办？</summary>

1. 检查网络连接
2. 尝试使用国内镜像
3. 清理缓存后重新安装

</details>

<details>
<summary>数据库连接失败？</summary>

1. 确认 MySQL 服务已启动
2. 检查 .env 配置是否正确
3. 验证数据库用户权限

</details>

## License

MIT License

---

**文档生成时间**: 2025-01-23
