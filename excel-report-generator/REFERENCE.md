# Excel Report Generator - API Reference

详细的 pandas 和 openpyxl API 参考指南

## 目录

1. [pandas Excel 操作](#pandas-excel-operations)
2. [openpyxl 核心 API](#openpyxl-core-api)
3. [样式和格式化](#styling-formatting)
4. [图表 API](#charts-api)
5. [条件格式 API](#conditional-formatting-api)
6. [高级功能](#advanced-features)
7. [性能优化技巧](#performance-tips)

---

## pandas Excel 操作

### 读取 Excel

```python
import pandas as pd

# 基本读取
df = pd.read_excel('file.xlsx')

# 指定工作表
df = pd.read_excel('file.xlsx', sheet_name='Sheet1')

# 读取多个工作表
excel_file = pd.ExcelFile('file.xlsx')
df1 = excel_file.parse('Sheet1')
df2 = excel_file.parse('Sheet2')

# 读取所有工作表到字典
all_sheets = pd.read_excel('file.xlsx', sheet_name=None)

# 高级参数
df = pd.read_excel(
    'file.xlsx',
    sheet_name='Sheet1',
    header=0,              # 标题行
    index_col=0,           # 索引列
    usecols='A:D',         # 只读取特定列
    skiprows=2,            # 跳过前 2 行
    nrows=100,             # 只读取 100 行
    dtype={'A': str},      # 指定数据类型
    na_values=['N/A', ''],  # 缺失值标识
    converters={'B': lambda x: x.strip()}  # 自定义转换
)
```

### 写入 Excel

```python
# 基本写入
df.to_excel('output.xlsx', index=False)

# 使用 ExcelWriter（推荐）
with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name='Sheet1', index=False)
    df2.to_excel(writer, sheet_name='Sheet2', index=False)

# 追加到现有文件
with pd.ExcelWriter('existing.xlsx', engine='openpyxl', mode='a') as writer:
    df.to_excel(writer, sheet_name='NewSheet')

# 高级参数
df.to_excel(
    'output.xlsx',
    sheet_name='Data',
    index=False,           # 不写入索引
    header=True,           # 写入列名
    startrow=0,            # 起始行
    startcol=0,            # 起始列
    na_rep='',             # 缺失值表示
    float_format='%.2f',   # 浮点数格式
    columns=['A', 'B'],    # 只写入特定列
    freeze_panes=(1, 0)    # 冻结窗格
)
```

---

## openpyxl 核心 API

### 工作簿操作

```python
from openpyxl import Workbook, load_workbook

# 创建新工作簿
wb = Workbook()
wb = Workbook(write_only=True)  # 只写模式（性能优化）

# 加载工作簿
wb = load_workbook('file.xlsx')
wb = load_workbook('file.xlsx', read_only=True)  # 只读模式
wb = load_workbook('file.xlsx', data_only=True)   # 只读取值，不读取公式

# 保存工作簿
wb.save('output.xlsx')
wb.save('output.xlsx')
wb.close()  # 只读模式需要关闭
```

### 工作表操作

```python
# 获取工作表
ws = wb.active                    # 活动工作表
ws = wb['SheetName']              # 按名称
ws = wb.worksheets[0]             # 按索引

# 创建工作表
ws = wb.create_sheet('NewSheet')           # 末尾添加
ws = wb.create_sheet('FirstSheet', 0)      # 指定位置
ws = wb.copy_worksheet(wb['Sheet1'])       # 复制工作表

# 工作表属性
ws.title = 'New Name'             # 重命名
ws.sheet_properties.tabColor = 'FF0000'  # 标签颜色

# 删除工作表
wb.remove(ws)
del wb['SheetName']

# 遍历工作表
for sheet in wb:
    print(sheet.title)
```

### 单元格操作

```python
# 读取单元格
value = ws['A1'].value
value = ws.cell(row=1, column=1).value

# 写入单元格
ws['A1'] = 'Hello'
ws['A1'] = 123
ws['A1'] = datetime.now()
ws.cell(row=1, column=1, value='Hello')

# 单元格范围
for row in ws['A1:C3']:
    for cell in row:
        print(cell.value)

# 按行遍历
for row in ws.iter_rows(min_row=1, max_row=10, min_col=1, max_col=3):
    for cell in row:
        print(cell.value)

# 按列遍历
for col in ws.iter_cols(min_row=1, max_row=10, min_col=1, max_col=3):
    for cell in col:
        print(cell.value)

# 追加行
ws.append([1, 2, 3])
ws.append({'A': 1, 'B': 2, 'C': 3})

# 插入/删除
ws.insert_rows(1, 3)      # 在第 1 行前插入 3 行
ws.insert_cols(1, 2)      # 在第 1 列前插入 2 列
ws.delete_rows(5, 2)      # 从第 5 行开始删除 2 行
ws.delete_cols(3, 1)      # 删除第 3 列

# 合并/取消合并
ws.merge_cells('A1:D1')
ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=4)
ws.unmerge_cells('A1:D1')
```

---

## 样式和格式化

### 字体 (Font)

```python
from openpyxl.styles import Font

# 基本字体
font = Font(
    name='Arial',           # 字体名称
    size=12,                # 字号
    bold=True,              # 粗体
    italic=False,           # 斜体
    underline='single',     # 下划线: single, double, singleAccounting, doubleAccounting
    strike=False,           # 删除线
    color='FF0000',         # 颜色（16进制）
    vertAlign='baseline'    # 垂直对齐: baseline, superscript, subscript
)

ws['A1'].font = font
```

### 填充 (PatternFill)

```python
from openpyxl.styles import PatternFill

# 实心填充
fill = PatternFill(
    start_color='FFFF00',   # 开始颜色
    end_color='FFFF00',     # 结束颜色
    fill_type='solid'       # 填充类型
)

# 渐变填充
gradient_fill = PatternFill(
    fill_type='lightGray',  # 填充图案类型
    start_color='FFFFFF',
    end_color='000000'
)

ws['A1'].fill = fill

# 常用填充类型
# solid, darkGray, mediumGray, lightGray, gray125, gray0625
# darkHorizontal, darkVertical, darkDown, darkUp, darkGrid, darkTrellis
# lightHorizontal, lightVertical, lightDown, lightUp, lightGrid, lightTrellis
```

### 边框 (Border)

```python
from openpyxl.styles import Border, Side

# 定义边框样式
side = Side(
    style='thin',           # 线条样式
    color='000000'          # 颜色
)

# 创建边框
border = Border(
    left=side,
    right=side,
    top=side,
    bottom=side,
    diagonal=side,
    diagonal_direction=0    # 0: 无, 1: 向下, 2: 向上, 3: 双向
)

ws['A1'].border = border

# 线条样式选项
# thin, medium, thick, double, hair, dotted, dashed, dashDot, dashDotDot
# mediumDashed, mediumDashDot, mediumDashDotDot, slantDashDot
```

### 对齐 (Alignment)

```python
from openpyxl.styles import Alignment

alignment = Alignment(
    horizontal='center',    # 水平对齐: left, center, right, fill, justify, centerContinuous, distributed
    vertical='center',      # 垂直对齐: top, center, bottom, justify, distributed
    text_rotation=0,        # 文本旋转: 0-180
    wrap_text=True,         # 自动换行
    shrink_to_fit=False,    # 缩小字体以适应
    indent=0                # 缩进级别
)

ws['A1'].alignment = alignment
```

### 数字格式 (Number Format)

```python
# 内置格式
ws['A1'].number_format = numbers.FORMAT_NUMBER  # 常规数字
ws['A2'].number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1  # 千分位
ws['A3'].number_format = numbers.FORMAT_PERCENTAGE  # 百分比
ws['A4'].number_format = numbers.FORMAT_CURRENCY_USD_SIMPLE  # 美元货币
ws['A5'].number_format = numbers.FORMAT_DATE_XLSX14  # 日期

# 自定义格式
ws['B1'].number_format = '#,##0.00'           # 千分位，两位小数
ws['B2'].number_format = '0.00%'              # 百分比，两位小数
ws['B3'].number_format = '$#,##0.00'          # 美元货币
ws['B4'].number_format = '¥#,##0.00'          # 人民币
ws['B5'].number_format = 'yyyy-mm-dd'         # 日期格式
ws['B6'].number_format = 'h:mm:ss AM/PM'      # 时间格式
ws['B7'].number_format = '[Red]-#,##0.00;[Blue]#,##0.00'  # 正负不同颜色
```

### 命名样式 (Named Styles)

```python
from openpyxl.styles import NamedStyle

# 创建命名样式
highlight = NamedStyle(name='highlight')
highlight.font = Font(bold=True, size=12)
highlight.fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
highlight.border = Border(left=Side(style='thin'), right=Side(style='thin'))

# 注册样式
wb.add_named_style(highlight)

# 使用样式
ws['A1'].style = 'highlight'
```

---

## 图表 API

### 柱状图 (BarChart)

```python
from openpyxl.chart import BarChart, Reference

chart = BarChart()
chart.type = 'col'              # col: 柱状图, bar: 条形图
chart.style = 10                # 图表样式 1-48
chart.title = "Sales Chart"
chart.y_axis.title = 'Sales'
chart.x_axis.title = 'Products'

# 数据引用
data = Reference(ws, min_col=2, min_row=1, max_row=10, max_col=3)
categories = Reference(ws, min_col=1, min_row=2, max_row=10)

chart.add_data(data, titles_from_data=True)
chart.set_categories(categories)

# 图表位置和大小
chart.width = 15        # 宽度（厘米）
chart.height = 7.5      # 高度（厘米）
ws.add_chart(chart, "E5")

# 堆叠和分组
chart.grouping = 'stacked'      # clustered, stacked, percentStacked
chart.overlap = 100             # 重叠百分比
```

### 折线图 (LineChart)

```python
from openpyxl.chart import LineChart, Reference

chart = LineChart()
chart.title = "Sales Trend"
chart.style = 12
chart.y_axis.title = 'Sales'
chart.x_axis.title = 'Month'

# 平滑线条
chart.smooth = True

data = Reference(ws, min_col=2, min_row=1, max_row=13)
chart.add_data(data, titles_from_data=True)

ws.add_chart(chart, "E5")
```

### 饼图 (PieChart)

```python
from openpyxl.chart import PieChart, Reference
from openpyxl.chart.series import DataPoint

chart = PieChart()
chart.title = "Market Share"
chart.style = 10

data = Reference(ws, min_col=2, min_row=2, max_row=6)
labels = Reference(ws, min_col=1, min_row=2, max_row=6)

chart.add_data(data, titles_from_data=False)
chart.set_categories(labels)

# 数据标签
chart.dataLabels = DataLabelList()
chart.dataLabels.showCatName = True
chart.dataLabels.showVal = True
chart.dataLabels.showPercent = True

ws.add_chart(chart, "E5")
```

### 散点图 (ScatterChart)

```python
from openpyxl.chart import ScatterChart, Reference, Series

chart = ScatterChart()
chart.title = "Correlation Analysis"
chart.x_axis.title = 'X Values'
chart.y_axis.title = 'Y Values'

xvalues = Reference(ws, min_col=1, min_row=2, max_row=20)
yvalues = Reference(ws, min_col=2, min_row=2, max_row=20)

series = Series(values=yvalues, xvalues=xvalues, title="Series 1")
chart.series.append(series)

ws.add_chart(chart, "E5")
```

---

## 条件格式 API

### 色阶规则 (ColorScaleRule)

```python
from openpyxl.formatting.rule import ColorScaleRule

# 两色色阶
rule = ColorScaleRule(
    start_type='min',
    start_color='F8696B',   # 红色
    end_type='max',
    end_color='63BE7B'      # 绿色
)

# 三色色阶
rule = ColorScaleRule(
    start_type='min',
    start_color='F8696B',   # 红色
    mid_type='percentile',
    mid_value=50,
    mid_color='FFEB84',     # 黄色
    end_type='max',
    end_color='63BE7B'      # 绿色
)

ws.conditional_formatting.add('A1:A100', rule)

# 类型选项: min, max, num, percent, percentile, formula
```

### 数据条规则 (DataBarRule)

```python
from openpyxl.formatting.rule import DataBarRule

rule = DataBarRule(
    start_type='min',
    start_value=0,
    end_type='max',
    end_value=100,
    color='4472C4',         # 蓝色
    showValue=True,         # 显示数值
    minLength=0,            # 最小长度
    maxLength=100           # 最大长度
)

ws.conditional_formatting.add('B1:B100', rule)
```

### 单元格规则 (CellIsRule)

```python
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import PatternFill, Font

red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
red_font = Font(color='9C0006')

# 小于
rule = CellIsRule(operator='lessThan', formula=['0'], fill=red_fill, font=red_font)
ws.conditional_formatting.add('C1:C100', rule)

# 大于
rule = CellIsRule(operator='greaterThan', formula=['1000'], fill=green_fill)
ws.conditional_formatting.add('C1:C100', rule)

# 操作符选项:
# lessThan, lessThanOrEqual, equal, notEqual, greaterThanOrEqual, greaterThan
# between, notBetween, containsText, notContainsText, beginsWith, endsWith
```

### 图标集规则 (IconSetRule)

```python
from openpyxl.formatting.rule import IconSetRule

rule = IconSetRule(
    icon_style='3TrafficLights1',  # 图标集样式
    type='percent',                 # num, percent, formula, percentile
    values=[0, 33, 67],            # 阈值
    showValue=True,                # 显示数值
    reverse=False                  # 反转图标顺序
)

ws.conditional_formatting.add('D1:D100', rule)

# 图标集样式选项:
# 3Arrows, 3ArrowsGray, 3Flags, 3TrafficLights1, 3TrafficLights2, 3Signs, 3Symbols, 3Symbols2
# 4Arrows, 4ArrowsGray, 4RedToBlack, 4Rating, 4TrafficLights
# 5Arrows, 5ArrowsGray, 5Rating, 5Quarters
```

---

## 高级功能

### 数据验证 (Data Validation)

```python
from openpyxl.worksheet.datavalidation import DataValidation

# 下拉列表
dv = DataValidation(
    type="list",
    formula1='"优秀,良好,一般,较差"',
    allow_blank=True
)
ws.add_data_validation(dv)
dv.add('E2:E100')

# 整数范围
dv = DataValidation(type="whole", operator="between", formula1=0, formula2=100)
dv.add('F2:F100')

# 日期范围
from datetime import datetime
dv = DataValidation(
    type="date",
    operator="between",
    formula1=datetime(2024, 1, 1),
    formula2=datetime(2024, 12, 31)
)
dv.add('G2:G100')

# 自定义公式
dv = DataValidation(type="custom", formula1='=ISTEXT(A2)')
dv.add('H2:H100')

# 错误提示
dv.error = '输入无效！'
dv.errorTitle = '错误'
dv.showErrorMessage = True

# 输入提示
dv.prompt = '请选择一个选项'
dv.promptTitle = '提示'
dv.showInputMessage = True
```

### 表格 (Table)

```python
from openpyxl.worksheet.table import Table, TableStyleInfo

# 创建表格
tab = Table(displayName="SalesData", ref="A1:D10")

# 表格样式
style = TableStyleInfo(
    name="TableStyleMedium9",       # 表格样式名称
    showFirstColumn=False,
    showLastColumn=False,
    showRowStripes=True,            # 显示行条纹
    showColumnStripes=False         # 显示列条纹
)
tab.tableStyleInfo = style

ws.add_table(tab)

# 表格样式选项:
# TableStyleLight1-21, TableStyleMedium1-28, TableStyleDark1-11
```

### 工作表保护

```python
from openpyxl.styles import Protection

# 保护工作表
ws.protection.sheet = True
ws.protection.password = 'mypassword'
ws.protection.enable()

# 保护选项
ws.protection.selectLockedCells = True
ws.protection.selectUnlockedCells = True
ws.protection.formatCells = False
ws.protection.formatColumns = False
ws.protection.formatRows = False
ws.protection.insertColumns = False
ws.protection.insertRows = False
ws.protection.deleteColumns = False
ws.protection.deleteRows = False

# 解锁特定单元格
ws['A1'].protection = Protection(locked=False)
```

### 冻结窗格

```python
# 冻结第一行
ws.freeze_panes = 'A2'

# 冻结第一列
ws.freeze_panes = 'B1'

# 冻结前两行和前两列
ws.freeze_panes = 'C3'

# 取消冻结
ws.freeze_panes = None
```

### 自动筛选

```python
# 启用自动筛选
ws.auto_filter.ref = 'A1:D10'
ws.auto_filter.ref = ws.dimensions  # 整个数据区域

# 添加筛选条件
from openpyxl.worksheet.filters import FilterColumn, CustomFilters, CustomFilter

# 数值筛选
ws.auto_filter.add_filter_column(1, ['Value1', 'Value2'])

# 自定义筛选
flt = FilterColumn(colId=2)
flt.customFilters = CustomFilters()
flt.customFilters.customFilter.append(CustomFilter(operator='greaterThan', val=100))
ws.auto_filter.filterColumn.append(flt)
```

---

## 性能优化技巧

### 只写模式 (Write-Only Mode)

```python
from openpyxl import Workbook

# 适用于写入大量数据（>50,000 行）
wb = Workbook(write_only=True)
ws = wb.create_sheet()

# 只能使用 append() 方法
for row in range(100000):
    ws.append([row, row*2, row*3])

wb.save('large_file.xlsx')
```

### 只读模式 (Read-Only Mode)

```python
# 适用于读取大文件
wb = load_workbook('large_file.xlsx', read_only=True, data_only=True)
ws = wb.active

for row in ws.iter_rows():
    for cell in row:
        print(cell.value)

wb.close()  # 记得关闭
```

### 批量操作技巧

```python
# ❌ 慢速方法：逐个设置样式
for row in range(1, 10000):
    ws.cell(row=row, column=1).font = Font(bold=True)

# ✅ 快速方法：创建样式对象并复用
bold_font = Font(bold=True)
for row in range(1, 10000):
    ws.cell(row=row, column=1).font = bold_font

# ✅ 更快：使用 iter_rows
for row in ws.iter_rows(min_row=1, max_row=10000, min_col=1, max_col=1):
    row[0].font = bold_font
```

### 内存优化

```python
# 使用生成器而不是列表
def data_generator():
    for i in range(100000):
        yield [i, i*2, i*3]

wb = Workbook(write_only=True)
ws = wb.create_sheet()

for row in data_generator():
    ws.append(row)

wb.save('output.xlsx')

# 及时清理不需要的对象
del wb
import gc
gc.collect()
```

### pandas 性能优化

```python
# 分块读取大文件
chunk_size = 10000
chunks = pd.read_excel('large_file.xlsx', chunksize=chunk_size)

for chunk in chunks:
    # 处理每个数据块
    process_chunk(chunk)

# 使用 xlsxwriter 引擎（更快）
with pd.ExcelWriter('output.xlsx', engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='Data')

# 禁用不需要的功能
df.to_excel('output.xlsx', index=False, freeze_panes=(1, 0))
```

---

## 常见问题解决

### 中文乱码

```python
# pandas 读取
df = pd.read_csv('data.csv', encoding='utf-8-sig')

# pandas 写入
df.to_excel('output.xlsx', encoding='utf-8-sig')
```

### 日期格式问题

```python
# 确保日期列被正确识别
df['date'] = pd.to_datetime(df['date'])

# 写入时保持日期格式
with pd.ExcelWriter('output.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Data')
    ws = writer.sheets['Data']
    for cell in ws['B']:  # 假设 B 列是日期
        if cell.row > 1:
            cell.number_format = 'yyyy-mm-dd'
```

### 公式不计算

```python
# 加载时设置 data_only=False
wb = load_workbook('file.xlsx', data_only=False)

# 或在 Excel 中打开文件后公式会自动计算
```

---

## 其他资源

- [pandas 官方文档](https://pandas.pydata.org/docs/)
- [openpyxl 官方文档](https://openpyxl.readthedocs.io/)
- [Excel 样式参考](https://support.microsoft.com/excel)
- [颜色代码查询](https://htmlcolorcodes.com/)

---

*最后更新: 2025-01-12*
