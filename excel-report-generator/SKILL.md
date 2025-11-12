---
name: excel-report-generator
description: Automatically generate Excel reports from data sources including CSV, databases, or Python data structures. Supports data analysis reports, business reports, data export, and template-based report generation using pandas and openpyxl. Activate when users mention Excel, spreadsheet, report generation, data export, or business reporting.
---

# Excel Report Generator

自动化 Excel 报表生成工具，支持从多种数据源生成专业的 Excel 报告。

## 功能概述

这个 Skill 可以帮助你：
- 📊 从 CSV、数据库或 Python 数据结构生成 Excel 报表
- 📈 创建包含图表、格式化和公式的数据分析报告
- 📋 基于模板填充数据生成业务报告
- 💾 将系统数据批量导出为格式化的 Excel 文件
- 🎨 应用专业的样式、颜色和条件格式

## 核心技术栈

- **pandas**: 数据处理和分析
- **openpyxl**: Excel 文件读写和格式化
- **xlsxwriter**: 高级图表和格式支持（可选）

## 使用场景

### 1. 数据分析报表
从原始数据生成包含统计分析、透视表和可视化图表的综合报告。

**示例请求**:
- "帮我从这个 CSV 生成销售分析报表"
- "创建一个包含月度趋势图的数据分析 Excel"
- "生成带有统计汇总的财务报表"

### 2. 业务报告
定期生成标准化的业务报告，如销售报告、KPI 仪表板等。

**示例请求**:
- "生成本月的销售业绩报告"
- "创建 KPI 跟踪报表"
- "导出季度业务总结 Excel"

### 3. 数据导出
将数据库查询结果或系统数据导出为格式化的 Excel 文件。

**示例请求**:
- "把用户数据导出到 Excel"
- "将数据库查询结果保存为 Excel 文件"
- "导出多个工作表的数据集"

### 4. 模板填充
基于预定义的 Excel 模板填充动态数据。

**示例请求**:
- "使用这个模板生成报告"
- "填充 Excel 模板中的数据"
- "批量生成基于模板的发票"

## 使用方法

### 基本工作流程

1. **准备数据源**: CSV 文件、pandas DataFrame、数据库连接或 Python 字典
2. **定义报表需求**: 描述所需的格式、图表、样式
3. **生成报表**: 自动创建格式化的 Excel 文件
4. **验证输出**: 检查生成的文件是否符合要求

### 命令示例

**从 CSV 生成报表**:
```
请从 sales_data.csv 生成一个销售分析报表，包含：
- 按产品分类的销售汇总
- 月度销售趋势图
- Top 10 产品排名
```

**从 DataFrame 生成报表**:
```
我有一个 pandas DataFrame，帮我生成 Excel 报表，包括：
- 数据透视表
- 条件格式高亮异常值
- 自动筛选和冻结首行
```

**使用模板**:
```
基于 templates/monthly_report.xlsx 模板，填充当月数据并生成报告
```

## 实现指南

当用户请求生成 Excel 报表时，遵循以下步骤：

### Step 1: 数据准备
```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

# 读取数据
df = pd.read_csv('data.csv')
# 或从数据库
# df = pd.read_sql(query, connection)
```

### Step 2: 数据处理
```python
# 数据清洗和转换
df_clean = df.dropna()

# 统计分析
summary = df.groupby('category').agg({
    'sales': ['sum', 'mean', 'count'],
    'profit': 'sum'
})
```

### Step 3: 创建 Excel 文件
```python
# 使用 pandas ExcelWriter
with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    # 写入原始数据
    df_clean.to_excel(writer, sheet_name='Raw Data', index=False)

    # 写入汇总数据
    summary.to_excel(writer, sheet_name='Summary')

    # 获取 workbook 进行格式化
    workbook = writer.book
    worksheet = writer.sheets['Summary']
```

### Step 4: 格式化和样式
```python
# 标题样式
header_font = Font(bold=True, color='FFFFFF')
header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')

# 应用样式到标题行
for cell in worksheet[1]:
    cell.font = header_font
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal='center')

# 列宽自动调整
for column in worksheet.columns:
    max_length = 0
    column_letter = column[0].column_letter
    for cell in column:
        if len(str(cell.value)) > max_length:
            max_length = len(str(cell.value))
    worksheet.column_dimensions[column_letter].width = max_length + 2
```

### Step 5: 添加图表（可选）
```python
from openpyxl.chart import BarChart, Reference

# 创建图表
chart = BarChart()
chart.title = "Sales by Category"
chart.x_axis.title = "Category"
chart.y_axis.title = "Sales"

# 数据引用
data = Reference(worksheet, min_col=2, min_row=1, max_row=10)
categories = Reference(worksheet, min_col=1, min_row=2, max_row=10)

chart.add_data(data, titles_from_data=True)
chart.set_categories(categories)

# 添加到工作表
worksheet.add_chart(chart, "E5")
```

## 高级功能

### 条件格式
```python
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule

# 色阶格式
worksheet.conditional_formatting.add(
    'B2:B100',
    ColorScaleRule(start_type='min', start_color='FF6347',
                   mid_type='percentile', mid_value=50, mid_color='FFFF00',
                   end_type='max', end_color='90EE90')
)

# 基于规则的格式
red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
worksheet.conditional_formatting.add(
    'C2:C100',
    CellIsRule(operator='lessThan', formula=['0'], fill=red_fill)
)
```

### 数据验证
```python
from openpyxl.worksheet.datavalidation import DataValidation

# 下拉列表
dv = DataValidation(type="list", formula1='"优秀,良好,一般,较差"', allow_blank=True)
worksheet.add_data_validation(dv)
dv.add('D2:D100')
```

### 公式应用
```python
# 添加求和公式
worksheet['B11'] = '=SUM(B2:B10)'

# 添加平均值公式
worksheet['C11'] = '=AVERAGE(C2:C10)'
```

## 最佳实践

### 1. 性能优化
- 对于大数据集（>10万行），使用 `openpyxl` 的 `write_only` 模式
- 分批处理数据，避免内存溢出
- 使用 `xlsxwriter` 引擎处理复杂图表和格式

### 2. 错误处理
```python
try:
    df = pd.read_csv('data.csv')
except FileNotFoundError:
    print("数据文件不存在")
except pd.errors.EmptyDataError:
    print("数据文件为空")
```

### 3. 文件命名规范
```python
from datetime import datetime

# 使用时间戳避免文件覆盖
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f'sales_report_{timestamp}.xlsx'
```

### 4. 数据验证
```python
# 检查必需列
required_columns = ['date', 'product', 'sales']
if not all(col in df.columns for col in required_columns):
    raise ValueError(f"缺少必需列: {required_columns}")

# 数据类型验证
df['date'] = pd.to_datetime(df['date'])
df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
```

### 5. 模板管理
- 将常用模板存放在 `~/.claude/skills/excel-report-generator/templates/` 目录
- 使用相对路径引用: `templates/monthly_report.xlsx`
- 保持模板简洁，只包含结构和样式，不包含数据

## 快速参考

### 常用代码片段

查看 `examples/quick_reference.py` 获取常用代码片段，包括：
- 基本 Excel 创建
- 多工作表管理
- 样式和格式化
- 图表创建
- 条件格式
- 公式应用

### 示例文件

- `examples/basic_report.py` - 基础报表生成示例
- `examples/advanced_report.py` - 高级功能示例
- `examples/template_fill.py` - 模板填充示例
- `templates/business_report.xlsx` - 业务报告模板
- `templates/data_analysis.xlsx` - 数据分析模板

## 依赖安装

确保已安装必需的 Python 包：

```bash
pip install pandas openpyxl xlsxwriter
```

可选依赖：
```bash
pip install matplotlib seaborn  # 用于数据可视化
pip install sqlalchemy pymysql  # 用于数据库连接
```

## 故障排查

### 常见问题

**Q: 生成的 Excel 文件无法打开**
A: 确保使用 `.xlsx` 扩展名，检查文件权限，验证数据中没有非法字符

**Q: 图表不显示**
A: 检查数据引用范围是否正确，确保数据类型为数值型

**Q: 中文乱码**
A: 使用 `encoding='utf-8-sig'` 读取 CSV，或在 Excel 中使用 UTF-8 编码

**Q: 大文件生成很慢**
A: 使用 `write_only=True` 模式，减少格式化操作，分批写入数据

## 相关资源

- [pandas 官方文档](https://pandas.pydata.org/docs/)
- [openpyxl 官方文档](https://openpyxl.readthedocs.io/)
- [xlsxwriter 官方文档](https://xlsxwriter.readthedocs.io/)
- 查看 `REFERENCE.md` 获取详细 API 参考

## 版本历史

- v1.0.0 (2025-01-12) - 初始版本，支持基础报表生成和模板填充
