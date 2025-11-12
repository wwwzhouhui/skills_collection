# Excel Report Generator Skill

欢迎使用 Excel Report Generator！这是一个用于自动化 Excel 报表生成的 Claude Code Skill。

## 📋 目录结构

```
excel-report-generator/
├── SKILL.md                    # Skill 主文档（Claude Code 读取）
├── REFERENCE.md                # 详细 API 参考文档
├── README.md                   # 本文件 - 用户指南
├── examples/                   # 示例脚本
│   ├── basic_report.py        # 基础报表生成
│   ├── advanced_report.py     # 高级功能示例
│   ├── template_fill.py       # 模板填充示例
│   └── quick_reference.py     # 快速参考代码片段
└── templates/                  # Excel 模板存放目录
    └── README.md              # 模板使用说明
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pandas openpyxl xlsxwriter
```

### 2. 运行示例

```bash
# 基础报表示例
cd ~/.claude/skills/excel-report-generator/examples
python basic_report.py

# 高级功能示例
python advanced_report.py

# 快速参考（包含所有代码片段）
python quick_reference.py
```

### 3. 在 Claude Code 中使用

只需在对话中提及 Excel 报表相关的需求，Claude 会自动激活这个 Skill：

**示例对话**:
```
你: 帮我从 sales_data.csv 生成一个 Excel 销售分析报表
Claude: [自动激活 excel-report-generator Skill 并生成代码]

你: 我需要一个包含图表的业务报告
Claude: [使用 Skill 中的高级功能生成带图表的报表]

你: 基于这个模板填充数据
Claude: [使用模板填充功能]
```

## 💡 核心功能

### ✅ 支持的功能

- 📊 从 CSV、DataFrame、数据库生成 Excel
- 📈 创建各类图表（柱状图、折线图、饼图等）
- 🎨 应用专业样式和格式
- 📋 使用模板批量生成报表
- 💾 数据导出和批量处理
- 🔄 条件格式和数据验证
- 📐 公式和自动计算

### 🎯 适用场景

1. **数据分析报表** - 从原始数据生成分析报告
2. **业务报告** - 定期生成标准化业务报表
3. **数据导出** - 将系统数据导出为 Excel
4. **模板填充** - 基于模板批量生成报告

## 📚 学习资源

### 新手入门

1. 先看 `examples/basic_report.py` 了解基础用法
2. 查看 `examples/quick_reference.py` 学习常用代码片段
3. 参考 `SKILL.md` 了解完整功能

### 进阶学习

1. 研究 `examples/advanced_report.py` 学习高级功能
2. 阅读 `REFERENCE.md` 深入了解 API
3. 实践 `examples/template_fill.py` 掌握模板使用

## 🔧 常用命令速查

### 基础操作

```python
# 1. CSV 转 Excel
import pandas as pd
df = pd.read_csv('data.csv')
df.to_excel('output.xlsx', index=False)

# 2. 创建多工作表
with pd.ExcelWriter('report.xlsx', engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name='Sheet1')
    df2.to_excel(writer, sheet_name='Sheet2')

# 3. 应用样式
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

wb = load_workbook('output.xlsx')
ws = wb.active
ws['A1'].font = Font(bold=True, size=14)
ws['A1'].fill = PatternFill(start_color='FFFF00', fill_type='solid')
wb.save('output.xlsx')
```

### 图表创建

```python
from openpyxl.chart import BarChart, Reference

chart = BarChart()
chart.title = "Sales"
data = Reference(ws, min_col=2, min_row=1, max_row=10)
chart.add_data(data, titles_from_data=True)
ws.add_chart(chart, "E5")
```

### 条件格式

```python
from openpyxl.formatting.rule import ColorScaleRule

ws.conditional_formatting.add(
    'B2:B100',
    ColorScaleRule(start_type='min', start_color='F8696B',
                   end_type='max', end_color='63BE7B')
)
```

## ❓ 常见问题

### Q: 如何处理大文件（>10万行）？

使用 `write_only` 模式：

```python
from openpyxl import Workbook

wb = Workbook(write_only=True)
ws = wb.create_sheet()

for row in large_data:
    ws.append(row)

wb.save('large_file.xlsx')
```

### Q: 中文显示乱码怎么办？

```python
# 读取时指定编码
df = pd.read_csv('data.csv', encoding='utf-8-sig')

# 写入时确保使用 UTF-8
df.to_excel('output.xlsx', encoding='utf-8-sig')
```

### Q: 如何自动调整列宽？

```python
for column in ws.columns:
    max_length = max(len(str(cell.value)) for cell in column)
    ws.column_dimensions[column[0].column_letter].width = max_length + 2
```

### Q: 图表不显示怎么办？

确保：
1. 数据引用范围正确
2. 数据类型为数值型
3. 使用正确的图表类型

## 🛠️ 故障排查

| 问题 | 解决方法 |
|------|---------|
| 文件无法打开 | 检查文件扩展名为 `.xlsx`，验证文件权限 |
| 公式不计算 | 在 Excel 中打开文件，公式会自动计算 |
| 样式不生效 | 确保保存前已应用样式，检查 openpyxl 版本 |
| 性能慢 | 使用 `write_only` 模式，减少格式化操作 |

## 📖 扩展阅读

- [SKILL.md](./SKILL.md) - 完整的 Skill 使用指南
- [REFERENCE.md](./REFERENCE.md) - 详细 API 参考
- [templates/README.md](./templates/README.md) - 模板使用说明
- [pandas 官方文档](https://pandas.pydata.org/docs/)
- [openpyxl 官方文档](https://openpyxl.readthedocs.io/)

## 🤝 贡献

这是个人 Skill，你可以：
- 添加自己的模板到 `templates/` 目录
- 在 `examples/` 中添加新的示例脚本
- 优化和改进现有代码

## 📝 版本信息

- **版本**: v1.0.0
- **创建日期**: 2025-01-12
- **技术栈**: Python 3.8+, pandas, openpyxl, xlsxwriter
- **适用平台**: Claude Code

## 💬 获取帮助

如果在使用过程中遇到问题：

1. 查看 `examples/` 中的示例代码
2. 参考 `REFERENCE.md` 中的 API 文档
3. 在 Claude Code 中直接询问相关问题

---

**开始使用**: 运行 `python examples/basic_report.py` 生成你的第一个 Excel 报表！
