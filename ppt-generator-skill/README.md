# PPT生成器 - 使用说明

## 📁 项目结构

```
/data/ppt/
├── .claude/
│   └── skills/
│       └── ppt-generator.md      # PPT生成技能定义文档
├── 11.pptx                        # 参考模板1（年终总结风格）
├── 22.pptx                        # 参考模板2（工作述职风格）
├── 33.pptx                        # 参考模板3（莫兰迪色系风格）
├── analyze_ppt.py                 # PPT分析工具
├── ppt_generator.py               # PPT生成器（核心工具）
├── 2025年度工作总结.pptx         # 生成的示例PPT
└── README.md                      # 本说明文档
```

## 🎯 功能特点

### 基于3个商务模板的特点
- **固定25页结构**：封面→目录→4章节（每章节5页）→结束→字体说明→版权
- **专业设计风格**：商务简约、暖色调、莫兰迪色系三种主题
- **规范化布局**：统一的页面布局和文本规范
- **自动生成**：输入配置即可自动生成完整PPT

### PPT结构（25页）
1. **第1页**：封面 - 主标题、副标题、年份
2. **第2页**：目录 - 4个章节列表
3. **第3-7页**：第一章节（1个过渡页 + 4个内容页）
4. **第8-12页**：第二章节（1个过渡页 + 4个内容页）
5. **第13-17页**：第三章节（1个过渡页 + 4个内容页）
6. **第18-22页**：第四章节（1个过渡页 + 4个内容页）
7. **第23页**：结束页 - "谢谢观看"
8. **第24页**：字体说明
9. **第25页**：版权声明

## 🚀 快速开始

### 方法1：直接运行示例

```bash
python3 ppt_generator.py
```

这将生成一个名为 `2025年度工作总结.pptx` 的示例PPT。

### 方法2：使用JSON配置文件

1. 创建配置文件 `my_ppt_config.json`：

```json
{
  "title": "我的项目汇报",
  "subtitle": "项目汇报 / 工作总结 / 述职报告",
  "year": "2025",
  "theme": "商务简约",
  "filename": "我的项目汇报.pptx",
  "chapters": [
    {
      "title": "项目背景",
      "description": "介绍项目的背景和目标",
      "pages": [
        {
          "title": "项目概述",
          "content": [
            {"title": "项目目标", "description": "实现XXX功能，提升用户体验"},
            {"title": "项目周期", "description": "2024年1月-2025年12月"}
          ]
        }
      ]
    }
  ]
}
```

2. 运行生成器：

```bash
python3 ppt_generator.py my_ppt_config.json
```

### 方法3：在代码中使用

```python
from ppt_generator import PPTGenerator

# 创建生成器实例
generator = PPTGenerator(theme="商务简约")

# 配置PPT内容
config = {
    "title": "2025年度总结",
    "subtitle": "工作总结 / 汇报",
    "year": "2025",
    "chapters": [...]  # 章节配置
}

# 生成PPT
generator.generate_full_ppt(config)
generator.save("output.pptx")
```

## 🎨 主题风格

支持3种主题风格：

1. **暖色调** - 活泼热情，适合创意类汇报
2. **商务简约**（默认） - 专业稳重，适合工作总结
3. **莫兰迪色系** - 优雅柔和，适合品牌展示

使用方法：
```python
generator = PPTGenerator(theme="暖色调")
```

## 📝 配置说明

### 完整配置结构

```json
{
  "title": "主标题",
  "subtitle": "副标题 / 场景描述",
  "year": "2025",
  "theme": "商务简约",
  "filename": "输出文件名.pptx",
  "chapters": [
    {
      "title": "章节标题",
      "description": "章节描述（200字以内）",
      "pages": [
        {
          "title": "页面标题",
          "content": [
            {
              "title": "要点标题",
              "description": "要点描述（50-100字）"
            }
          ]
        }
      ]
    }
  ]
}
```

### 配置要点

- **4个章节必填**：每个PPT必须有4个主要章节
- **每章节4页内容**：不足自动补充占位页
- **每页最多4个要点**：采用2x2布局
- **文本简洁**：描述控制在50-100字

## 🛠️ 工具使用

### 1. 分析现有PPT

```bash
python3 analyze_ppt.py
```

这将分析 `11.pptx`、`22.pptx`、`33.pptx` 三个模板文件，输出结构信息。

### 2. 查看技能文档

```bash
cat .claude/skills/ppt-generator.md
```

详细的技能定义和使用规范。

## 💡 使用技巧

### 1. 内容准备
在生成PPT前，先准备好：
- 明确的主题和目标
- 4个逻辑清晰的章节
- 每个章节的关键要点（3-5个）
- 简洁的文字描述

### 2. 快速迭代
- 先生成初版PPT查看效果
- 根据需要调整配置
- 重新生成并对比

### 3. 后期优化
生成的PPT可以在PowerPoint中进一步编辑：
- 调整布局和间距
- 添加图片和图表
- 微调颜色和字体

## 📋 示例场景

### 场景1：年度工作总结
```json
{
  "title": "2025年度工作总结",
  "chapters": [
    {"title": "年度工作概况"},
    {"title": "重点项目回顾"},
    {"title": "数据成果展示"},
    {"title": "明年工作计划"}
  ]
}
```

### 场景2：项目汇报
```json
{
  "title": "XXX项目汇报",
  "chapters": [
    {"title": "项目背景与目标"},
    {"title": "实施方案介绍"},
    {"title": "项目进展情况"},
    {"title": "后续计划安排"}
  ]
}
```

### 场景3：产品发布
```json
{
  "title": "新产品发布会",
  "chapters": [
    {"title": "市场机会分析"},
    {"title": "产品核心功能"},
    {"title": "竞争优势对比"},
    {"title": "上市推广计划"}
  ]
}
```

## ⚙️ 技术要求

### 依赖库
```bash
pip install python-pptx
```

### Python版本
- Python 3.7+

### 字体要求
建议安装以下字体以获得最佳效果：
- 阿里巴巴普惠体 2.0
- HarmonyOS Sans SC
- MiSans Heavy
- 思源宋体 CN

如果没有这些字体，系统会使用默认字体替代。

## 🔧 自定义开发

### 修改主题颜色

编辑 `ppt_generator.py` 中的 `COLOR_SCHEMES`：

```python
COLOR_SCHEMES = {
    "自定义主题": {
        "primary": RGBColor(R, G, B),
        "secondary": RGBColor(R, G, B),
        "accent": RGBColor(R, G, B),
        "text": RGBColor(R, G, B),
        "background": RGBColor(R, G, B),
    }
}
```

### 修改页面布局

修改 `create_content_slide()` 方法中的 `positions` 数组来调整内容布局。

### 添加新的幻灯片类型

继承 `PPTGenerator` 类并添加新的方法：

```python
def create_custom_slide(self, ...):
    slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
    # 自定义布局代码
    return slide
```

## 📞 问题反馈

如果遇到问题或有改进建议，可以：
1. 检查配置文件格式是否正确
2. 确认依赖库已正确安装
3. 查看错误信息定位问题

## 📄 许可说明

本工具基于3个商务PPT模板的分析结果开发，仅供学习和参考使用。

生成的PPT可以自由使用和修改，建议根据实际需要进行二次编辑。

---

**生成时间**: 2025-12-04
**版本**: v1.0
**作者**: o3sky
