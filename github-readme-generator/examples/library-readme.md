# use-toolkit

一个现代化的 JavaScript 工具库，提供常用的工具函数。

![npm](https://img.shields.io/npm/v/use-toolkit.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Downloads](https://img.shields.io/npm/dm/use-toolkit.svg)

> 让你的开发更高效

## 项目介绍

use-toolkit 是一个轻量级的 JavaScript 工具库，提供日常开发中常用的工具函数。

### 为什么选择 use-toolkit

- 轻量级：全部代码仅 20KB (gzipped)
- TypeScript：完整的类型定义
- Tree-shakable：按需引入，减小打包体积
- 现代化：支持 ESM 和 CommonJS

### 核心特性

- 字符串处理
- 数组操作
- 对象处理
- 日期格式化
- 数值计算
- DOM 操作

## 快速开始

### 安装

```bash
# npm
npm install use-toolkit

# yarn
yarn add use-toolkit

# pnpm
pnpm add use-toolkit
```

### 基础用法

```javascript
// ESM
import { trim, isEmpty, formatDate } from 'use-toolkit'

// CommonJS
const { trim, isEmpty, formatDate } = require('use-toolkit')

// 使用
trim('  hello  ') // 'hello'
isEmpty('') // true
formatDate(new Date(), 'YYYY-MM-DD') // '2025-01-23'
```

### API 文档

详见 [API 文档](https://use-toolkit.dev/docs/api)

## 功能清单

| API | 说明 | 参数 | 返回值 |
|-----|------|------|--------|
| trim | 去除首尾空格 | str: string | string |
| isEmpty | 判断是否为空 | val: any | boolean |
| formatDate | 格式化日期 | date: Date, format: string | string |
| debounce | 防抖函数 | fn: Function, delay: number | Function |
| throttle | 节流函数 | fn: Function, delay: number | Function |
| deepClone | 深拷贝 | obj: any | any |

## 示例代码

### 示例 1：字符串处理

```javascript
import { trim, capitalize, truncate } from 'use-toolkit'

const str = '  hello world  '

trim(str) // 'hello world'
capitalize(str) // 'Hello world'
truncate(str, 10) // 'hello wor...'
```

### 示例 2：数组操作

```javascript
import { uniq, chunk, shuffle } from 'use-toolkit'

const arr = [1, 2, 2, 3, 4, 4]

uniq(arr) // [1, 2, 3, 4]
chunk(arr, 2) // [[1, 2], [2, 3], [4, 4]]
shuffle(arr) // [4, 1, 3, 2, 2, 4]
```

### 示例 3：日期处理

```javascript
import { formatDate, addDays, diffDays } from 'use-toolkit'

const now = new Date()

formatDate(now, 'YYYY-MM-DD HH:mm:ss') // '2025-01-23 10:30:00'
addDays(now, 7) // 7 天后的日期
diffDays(now, new Date('2025-01-01')) // 22
```

## 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| locale | string | 'zh-CN' | 语言环境 |
| timezone | string | 'Asia/Shanghai' | 时区 |

## TypeScript 支持

本项目使用 TypeScript 编写，提供完整的类型定义：

```typescript
import type { StringUtil, DateUtil } from 'use-toolkit'

const trim: StringUtil = (str: string): string => {
  return str.trim()
}

const formatDate: DateUtil = (date: Date, format: string): string => {
  // ...
}
```

## 浏览器支持

| 浏览器 | 版本 |
|--------|------|
| Chrome | 最新 |
| Firefox | 最新 |
| Safari | 14+ |
| Edge | 最新 |

## 更新日志

### v2.0.0

- 新增 DOM 操作工具函数
- 优化日期处理性能
- 修复 isEmpty 函数类型问题

查看 [完整更新日志](CHANGELOG.md)

## 常见问题

<details>
<summary>如何按需引入？</summary>

使用 ESM 方式即可自动 tree-shake：

```javascript
import { trim } from 'use-toolkit'
```

</details>

<details>
<summary>支持 SSR 吗？</summary>

支持，本库不依赖浏览器环境。

</details>

## License

MIT License

## 相关链接

- [API 文档](https://use-toolkit.dev/docs/api)
- [更新日志](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)

---

**文档生成时间**: 2025-01-23
