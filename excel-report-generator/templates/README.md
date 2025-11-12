# Excel Templates Directory

这个目录用于存放 Excel 报表模板文件。

## 模板使用说明

### 什么是模板？

Excel 模板是预先设计好格式和结构的 Excel 文件，包含：
- 固定的表头和标题
- 预设的样式和格式
- 公式和计算逻辑
- 图表和可视化框架

### 如何使用模板

1. **准备模板文件**
   - 在 Excel 中设计好报表结构
   - 使用占位符标记需要填充的位置
   - 保存为 .xlsx 文件并放入此目录

2. **使用 Python 填充数据**
   ```python
   from openpyxl import load_workbook

   # 加载模板
   wb = load_workbook('templates/business_report.xlsx')
   ws = wb.active

   # 填充数据
   ws['B2'] = '2024年度销售报告'
   ws['B4'] = total_sales
   ws['B5'] = total_orders

   # 保存为新文件
   wb.save('reports/monthly_report_2024_01.xlsx')
   ```

3. **参考示例**
   查看 `examples/template_fill.py` 了解详细用法

## 推荐的模板类型

### 业务报告模板 (business_report.xlsx)

**建议包含**:
- 公司 Logo 和标题区域
- 报告期间和生成日期
- 关键指标（KPI）展示区
- 数据表格区域
- 图表区域
- 备注和审批区

**模板结构示例**:
```
+----------------------------------+
|        公司名称 / Logo            |
|     [报告标题] [报告期间]          |
+----------------------------------+
| KPI 指标 1: [值]  | KPI 指标 2: [值] |
| KPI 指标 3: [值]  | KPI 指标 4: [值] |
+----------------------------------+
|           数据明细表              |
| 产品 | 销售额 | 利润 | 增长率     |
|------|--------|------|-----------|
| [数据行 - 可批量填充]             |
+----------------------------------+
|         图表展示区                |
|   [柱状图]    |    [折线图]      |
+----------------------------------+
| 备注: [说明文字]                  |
| 制表人:       审核人:             |
+----------------------------------+
```

### 数据分析模板 (data_analysis.xlsx)

**建议包含**:
- 原始数据工作表
- 数据透视表工作表
- 趋势分析工作表
- 可视化仪表板
- 统计汇总表

**工作表结构**:
1. **Raw Data**: 原始数据存放
2. **Summary**: 汇总统计
3. **Trends**: 趋势分析和图表
4. **Dashboard**: KPI 仪表板

### 财务报表模板 (financial_report.xlsx)

**建议包含**:
- 损益表
- 资产负债表
- 现金流量表
- 财务比率分析

### 发票模板 (invoice_template.xlsx)

**建议包含**:
- 公司信息区
- 客户信息区
- 发票编号和日期
- 明细项目表格（描述、数量、单价、小计）
- 合计和税费计算
- 付款条款和备注

## 模板命名规范

推荐的命名格式：
- `{类型}_{用途}_{版本}.xlsx`
- 示例：
  - `business_monthly_report_v1.xlsx`
  - `sales_analysis_template_v2.xlsx`
  - `invoice_standard_v1.xlsx`

## 模板设计最佳实践

### 1. 使用命名范围

在 Excel 中为关键单元格或区域定义名称，便于 Python 代码引用：

```python
# Excel 中: 选择单元格 B2，定义名称为 "ReportTitle"
# Python 中:
wb.defined_names['ReportTitle'].value = '2024年度报告'
```

### 2. 使用一致的数据区域

将数据填充区域设计在固定位置，方便批量操作：

```python
# 从 A7 开始填充数据表格
start_row = 7
for idx, row_data in enumerate(data_rows):
    for col_idx, value in enumerate(row_data, start=1):
        ws.cell(row=start_row+idx, column=col_idx, value=value)
```

### 3. 预设公式和格式

在模板中预先设置好公式，数据填充后自动计算：

```
# Excel 模板中的公式示例
B11: =SUM(B7:B10)      # 合计
C7:  =B7*D7            # 小计 = 数量 * 单价
E10: =AVERAGE(E7:E9)   # 平均值
```

### 4. 使用表格样式

使用 Excel 表格功能，自动扩展格式：

```python
from openpyxl.worksheet.table import Table, TableStyleInfo

# 创建表格
tab = Table(displayName="SalesData", ref="A6:E15")
style = TableStyleInfo(name="TableStyleMedium9", showRowStripes=True)
tab.tableStyleInfo = style
ws.add_table(tab)
```

## 现有模板文件

目前此目录为空，你可以：

1. 创建自己的模板文件并放置在此目录
2. 从 `examples/` 目录运行示例代码生成测试报表
3. 参考上述建议设计符合业务需求的模板

## 获取模板资源

### 在线资源
- [Microsoft Office Templates](https://templates.office.com/)
- [Vertex42 Templates](https://www.vertex42.com/)
- [Template.net Excel Templates](https://www.template.net/excel-templates/)

### 自定义模板
如果你需要定制模板，可以：
1. 在 Excel 中手工设计
2. 使用 Python 生成基础模板
3. 参考 `examples/` 中的脚本生成模板框架

## 示例代码

### 创建简单模板

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active

# 标题
ws['A1'] = '销售报告模板'
ws['A1'].font = Font(size=16, bold=True)
ws.merge_cells('A1:E1')
ws['A1'].alignment = Alignment(horizontal='center')

# 表头
headers = ['产品', '数量', '单价', '小计', '备注']
for col, header in enumerate(headers, start=1):
    cell = ws.cell(row=3, column=col, value=header)
    cell.font = Font(bold=True)
    cell.fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')

# 数据行（预留 10 行）
for row in range(4, 14):
    ws.cell(row=row, column=4, value=f'=B{row}*C{row}')  # 小计公式

# 合计行
ws.cell(row=14, column=1, value='合计')
ws.cell(row=14, column=4, value='=SUM(D4:D13)')
ws.cell(row=14, column=1).font = Font(bold=True)

wb.save('templates/simple_sales_template.xlsx')
```

---

*需要帮助？查看 `../examples/template_fill.py` 获取详细示例*
