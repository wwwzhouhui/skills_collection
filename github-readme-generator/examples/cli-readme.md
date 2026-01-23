# devtool

一个强大的开发者 CLI 工具，提升你的开发效率。

![npm](https://img.shields.io/npm/v/devtool.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Homebrew](https://img.shields.io/homebrew/v/devtool.svg)

> 让开发更简单

## 项目介绍

devtool 是一个专为开发者设计的 CLI 工具，集成了常用的开发操作。

### 核心功能

- 项目脚手架
- 代码生成
- Git 工具
- 包管理加速
- 本地服务器

## 安装

### 方式一：包管理器安装

```bash
# npm
npm install -g devtool

# yarn
yarn global add devtool

# pnpm
pnpm add -g devtool
```

### 方式二：Homebrew (macOS/Linux)

```bash
brew tap user/tap
brew install devtool
```

### 方式三：二进制下载

下载对应平台的二进制文件：

- [macOS (Intel)](https://github.com/user/devtool/releases/latest/download/devtool-macos-x64)
- [macOS (Apple Silicon)](https://github.com/user/devtool/releases/latest/download/devtool-macos-arm64)
- [Linux (x64)](https://github.com/user/devtool/releases/latest/download/devtool-linux-x64)
- [Windows (x64)](https://github.com/user/devtool/releases/latest/download/devtool-windows-x64.exe)

### 方式四：源码编译

```bash
git clone https://github.com/user/devtool.git
cd devtool
cargo install --path .
```

## 使用说明

### 基本用法

```bash
devtool [command] [options]
```

### 命令列表

| 命令 | 简写 | 说明 | 示例 |
|------|------|------|------|
| create | c | 创建新项目 | `devtool create my-app` |
| generate | g | 生成代码 | `devtool generate component` |
| serve | s | 启动本地服务 | `devtool serve -p 8080` |
| git-changelog | - | 生成 Git 变更日志 | `devtool git-changelog` |
| npm-speedup | - | 加速 npm 源 | `devtool npm-speedup` |
| --help | h | 显示帮助 | `devtool --help` |
| --version | v | 显示版本 | `devtool --version` |

### 使用示例

```bash
# 创建 Vue 项目
devtool create my-vue-app --template vue

# 创建 React 项目
devtool create my-react-app --template react

# 生成组件
devtool g component Header

# 启动本地服务
devtool s -p 3000 -o

# 生成变更日志
devtool git-changelog --format markdown

# 加速 npm
devtool npm-speedup --registry taobao
```

## 配置文件

配置文件位置：`~/.devtool/config.yaml`

```yaml
# 默认模板
defaultTemplate: vue

# 默认端口
defaultPort: 8080

# npm 源
registry: https://registry.npmmirror.com

# Git 配置
git:
  username: yourname
  email: you@example.com
```

## 选项说明

| 选项 | 简写 | 类型 | 默认值 | 说明 |
|------|------|------|--------|------|
| --template | -t | string | - | 项目模板 |
| --port | -p | number | 8080 | 服务端口 |
| --open | -o | boolean | false | 自动打开浏览器 |
| --force | -f | boolean | false | 强制覆盖 |
| --verbose | -v | boolean | false | 显示详细日志 |
| --help | -h | - | - | 显示帮助 |

## 常见问题

<details>
<summary>安装后命令不可用？</summary>

检查 npm 全局安装路径是否在 PATH 中：

```bash
npm config get prefix
```

将输出路径添加到系统 PATH。

</details>

<details>
<summary>如何自定义模板？</summary>

在 `~/.devtool/templates/` 目录下创建自定义模板。

</details>

<details>
<summary>端口被占用怎么办？</summary>

使用 `--port` 指定其他端口，或使用 `-p 0` 自动分配可用端口。

</details>

## License

MIT License

## 相关链接

- [GitHub](https://github.com/user/devtool)
- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)

---

**文档生成时间**: 2025-01-23
