# Claude Code Skills Collection

本项目是个人开发的 Claude Code Skills 集合，提供实用的技能工具，助力提升开发效率和内容创作。

分享一些好用的 Claude Code Skills，自用、学习两相宜，适用于 Claude Code v2.0 及以上版本。

## 📖 什么是 Claude Skills

Claude Skills 是 Claude Code 的扩展能力，通过编写技能文档（Skill.md），可以让 Claude 在特定场景下自动激活相应的专业知识和能力。

## 使用说明

### 1. 安装 Skills

将 Skill 文件夹复制到你的 Claude Code Skills 目录：

```bash
# Linux/Mac
cp -r skill-name ~/.claude/skills/

# Windows
xcopy /E /I skill-name %USERPROFILE%\.claude\skills\skill-name
```

如果是windows平台可以手工复制到 C:\Users\xxx\.claude\skills

![image-20251110164730420](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110164730420.png)

![image-20251110165041134](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110165041134.png)

  我们检查一下这个skills是否可以使用。

### 2. 验证安装

在 Claude Code 中输入相关关键词，Claude 会自动激活对应的 Skill。

![image-20251112173259755](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112173259755.png)

### 3. 开始使用

直接与 Claude 对话，提出相关需求即可：

```
"请基于上面的数据帮我生成图表统计，比如饼状图、柱状图、条形图等。请在原来生成的2025年101中学其中考试统计表20251112.xlsx表中生成"
```

![image-20251112171230648](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112171230648.png)

## Skills 清单

| Skill 名称              | 功能说明                                                     | 技术栈                               | 更新时间       | 作者       | 版本  |
| ----------------------- | ------------------------------------------------------------ | ------------------------------------ | -------------- | ---------- | ----- |
| excel-report-generator  | 自动化 Excel 报表生成器，支持从 CSV、DataFrame、数据库生成专业 Excel 报表，包含图表、样式、模板填充等高级功能 | Python、pandas、openpyxl、xlsxwriter | 2025年1月12日  | wwwzhouhui | 2.0.0 |
| xiaohuihui-tech-article | 专为技术实战教程设计的公众号文章生成器，遵循小灰灰公众号写作规范，自动生成包含前言、项目介绍、部署实战、总结的完整技术文章 | Markdown、模板生成                   | 2025年11月10日 | wwwzhouhui | 2.0.0 |

## Skill 功能详解

### 📊 Excel Report Generator

**核心功能：**

- ✅ 从多种数据源生成 Excel（CSV、DataFrame、数据库）
- ✅ 创建专业图表（柱状图、折线图、饼图等）
- ✅ 应用样式和格式化
- ✅ 模板填充和批量生成
- ✅ 条件格式和数据验证
- ✅ 公式和自动计算

**适用场景：**

- 数据分析报表
- 业务报告自动化
- 系统数据导出
- 模板批量处理

**示例用法：**

```
请基于上面的数据帮我生成图表统计，比如饼状图、柱状图、条形图等
```

![image-20251112171422425](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251112171422425.png)

---

### 📝 XiaoHuiHui Tech Article

**核心功能：**

- ✅ 标准四段式结构（前言→项目介绍→部署实战→总结）
- ✅ 三段式开头（问题引入+解决方案+实战预告）
- ✅ 详细部署步骤（环境→安装→配置→实现→测试）
- ✅ 单段长句总结（300-500字）
- ✅ 口语化技术表达
- ✅ 完整资源附加（GitHub+体验地址+网盘）

**文章结构：**

- **第1章**：前言（三段式，约300字）
- **第2章**：项目介绍（约500字）
- **第3章**：部署实战（约1500-2000字）
- **第4章**：总结（单段300-500字）
- **第5章**：附加资源

**示例用法：**

```
请认真分析https://github.com/wwwzhouhui/in_animation开源项目，请帮我使用xiaohuihui-tech-article skill基于这个开源项目生成一个公众号文章。输出"20251101in_animation公众号文章.md"
```

![image-20251110175146630](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110175146630.png)

​     ![image-20251110175215254](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20251110175215254.png)

## 更新说明

### 2025年1月12日 - version 0.0.2

- ✅ 新增 excel-report-generator Skill
- ✅ 支持数据分析报表生成
- ✅ 支持图表创建和样式应用

### 2025年11月10日 - version 0.0.1

- ✅ 新增 xiaohuihui-tech-article Skill
- ✅ 实现标准四段式结构
- ✅ 支持口语化技术写作

## 技术文档地址（飞书）

https://aqma351r01f.feishu.cn/wiki/HF5FwMDQkiHoCokvbQAcZLu3nAg?table=tbleOWb4WgXcxiHK&view=vewGwwbpzl

![image-20241115093319205](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/image-20241115093319205.png)

## 开发指南

### 创建新的 Skill

1. 在项目根目录创建新的 Skill 文件夹
2. 创建 `Skill.md` 文件，定义 Skill 的元数据和功能
3. 添加示例代码和文档
4. 测试 Skill 在 Claude Code 中的表现

**Skill.md 基本结构：**

```markdown
---
name: your-skill-name
description: Skill 的简短描述
version: 1.0.0
---

# Your Skill Name

详细的功能说明和使用文档...
```

### 贡献 Skills

欢迎提交你的 Claude Code Skills：

1. Fork 本项目
2. 创建你的 Skill 分支 (`git checkout -b feature/new-skill`)
3. 提交你的更改 (`git commit -am 'Add new skill'`)
4. 推送到分支 (`git push origin feature/new-skill`)
5. 创建 Pull Request

## 🎉 致谢

感谢以下项目对本项目提供的灵感和支持：

1. [Claude Code](https://claude.ai/code)

   Anthropic 官方推出的 AI 编程助手，提供强大的代码理解和生成能力。

2. [pandas](https://github.com/pandas-dev/pandas)

   强大的 Python 数据分析库，excel-report-generator 的核心依赖。

3. [openpyxl](https://github.com/theorchard/openpyxl)

   用于读写 Excel 2010 xlsx/xlsm 文件的 Python 库。

## 问题反馈

如有问题，请在 GitHub Issue 中提交，在提交问题之前，请先查阅以往的 issue 是否能解决你的问题。

## 常见问题汇总

<details>
<summary>如何知道 Skill 是否已激活？</summary>
当 Claude 识别到相关关键词时，会自动激活对应的 Skill。你可以通过 Claude 的回复内容判断，如果回复包含 Skill 中定义的特定结构或风格，说明已成功激活。
</details>


<details>
<summary>Skill 不生效怎么办？</summary>
1. 确认 Skill 文件夹位置正确（~/.claude/skills/）<br>
2. 检查 Skill.md 文件格式是否正确<br>
3. 尝试重启 Claude Code<br>
4. 使用更明确的触发关键词
</details>


<details>
<summary>如何自定义 Skill？</summary>
你可以直接编辑 Skill.md 文件，修改功能说明、触发关键词、输出格式等。修改后 Claude 会在下次激活时使用新的配置。
</details>


<details>
<summary>Skill 冲突怎么办？</summary>
如果多个 Skill 的触发关键词重叠，可以：<br>
1. 使用更具体的关键词<br>
2. 在对话中明确指定要使用的 Skill 名称<br>
3. 调整 Skill.md 中的描述和触发条件
</details>


<details>
<summary>Excel 生成的文件打不开？</summary>
1. 确认安装了正确版本的依赖（pandas、openpyxl）<br>
2. 检查文件扩展名是否为 .xlsx<br>
3. 验证数据格式是否正确<br>
4. 查看错误日志排查具体问题
</details>


<details>
<summary>技术文章风格不符合预期？</summary>
1. 在提示中明确指定"使用小灰灰公众号风格"<br>
2. 提供更详细的项目信息和技术栈<br>
3. 可以要求 Claude 调整特定段落的风格<br>
4. 参考 Skill.md 中的标准模板
</details>


## 技术交流群

欢迎加入技术交流群，分享你的 Skills 和使用心得：

![微信图片_20251106202546_65_292](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20251106202546_65_292.jpg)

![微信图片_20251103212128_63_292](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/%E5%BE%AE%E4%BF%A1%E5%9B%BE%E7%89%87_20251103212128_63_292.jpg)

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

支付宝

![image-20250914152823776](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152823776.png)

微信

![image-20250914152855543](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

## 📊 项目统计

### 技能统计

- **总技能数**: 2
- **自动化工具**: 1 (excel-report-generator)
- **内容生成**: 1 (xiaohuihui-tech-article)

### 开发语言

- Python: 1
- Markdown: 1

### 维护状态

- ✅ 活跃维护中
- 🔄 持续更新
- 📚 文档完善

## 路线图

### 计划中的 Skills

- [ ] **code-reviewer**: 代码审查助手
- [ ] **api-doc-generator**: API 文档生成器
- [ ] **test-case-generator**: 测试用例生成器
- [ ] **database-designer**: 数据库设计助手
- [ ] **deployment-helper**: 部署配置助手

### 优化计划

- [ ] 添加更多 Excel 报表模板
- [ ] 扩展技术文章支持的平台风格
- [ ] 提供交互式配置工具
- [ ] 增加中英文双语支持

## License

MIT License

## Star History

如果觉得项目不错，欢迎点个 Star ⭐

![claude-skills](https://api.star-history.com/svg?repos=yourusername/claude-skills&type=Date)

---

**开始使用**: 选择一个 Skill，按照使用说明安装，然后在 Claude Code 中尽情使用吧！