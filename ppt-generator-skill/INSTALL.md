# PPT生成器 Skill 安装指南

## 📦 包含内容

- `skills/ppt-generator.md` - Skill技能定义文档
- `ppt_generator.py` - PPT生成核心工具
- `config_template.json` - 配置文件模板
- `README.md` - 完整使用说明
- `INSTALL.md` - 本安装指南

## 🔧 安装步骤

### 方法1：完整安装（推荐）

```bash
# 1. 解压到你的项目目录
unzip ppt-generator-skill.zip -d /your/project/path/

# 2. 进入目录
cd /your/project/path/

# 3. 安装依赖
pip install python-pptx

# 4. 测试运行
python3 ppt_generator.py
```

### 方法2：仅安装Skill（用于Claude Code）

```bash
# 1. 确保你的项目有 .claude/skills 目录
mkdir -p .claude/skills

# 2. 将 skills/ppt-generator.md 复制到 .claude/skills/
cp skills/ppt-generator.md .claude/skills/

# 3. 将 ppt_generator.py 复制到项目根目录
cp ppt_generator.py ./

# 4. 安装依赖
pip install python-pptx
```

### 方法3：在Claude Code中调用

解压后，在Claude Code对话中说：
- "生成一个工作总结PPT"
- "帮我制作年度汇报演示文稿"
- "创建项目汇报PPT"

Claude Code会自动识别并使用这个skill。

## 📝 快速开始

### 生成示例PPT
```bash
python3 ppt_generator.py
```

这会生成一个 `2025年度工作总结.pptx` 示例文件。

### 使用配置文件生成
```bash
# 1. 复制配置模板
cp config_template.json my_ppt.json

# 2. 编辑 my_ppt.json 填入你的内容

# 3. 生成PPT
python3 ppt_generator.py my_ppt.json
```

### 在Python代码中使用
```python
from ppt_generator import PPTGenerator

# 创建生成器
generator = PPTGenerator(theme="商务简约")  # 可选：暖色调、商务简约、莫兰迪色系

# 准备配置
config = {
    "title": "我的PPT",
    "subtitle": "副标题",
    "year": "2025",
    "chapters": [...]  # 4个章节配置
}

# 生成并保存
generator.generate_full_ppt(config)
generator.save("output.pptx")
```

## 🎨 主题风格

支持3种预设主题：
- `暖色调` - 活泼热情
- `商务简约` - 专业稳重（默认）
- `莫兰迪色系` - 优雅柔和

## 📋 配置文件说明

配置文件必须包含：
- **title**: 主标题
- **subtitle**: 副标题
- **year**: 年份
- **chapters**: 4个章节数组，每个章节包含：
  - title: 章节标题
  - description: 章节描述
  - pages: 4个页面数组（不足自动补充）

详见 `config_template.json` 示例。

## ⚙️ 系统要求

- Python 3.7+
- python-pptx 库

### 安装依赖
```bash
pip install python-pptx
```

### 可选字体（获得最佳效果）
- 阿里巴巴普惠体 2.0
- HarmonyOS Sans SC
- MiSans Heavy
- 思源宋体 CN

## 📖 完整文档

详细使用说明请查看 `README.md`

## 🎯 PPT结构

自动生成25页完整PPT：
1. 封面（1页）
2. 目录（1页）
3. 第一章节（5页：1过渡+4内容）
4. 第二章节（5页：1过渡+4内容）
5. 第三章节（5页：1过渡+4内容）
6. 第四章节（5页：1过渡+4内容）
7. 结束页（1页）
8. 字体说明（1页）
9. 版权声明（1页）

## 💡 使用提示

1. **内容准备**：先准备好4个章节的标题和要点
2. **文本简洁**：每页描述控制在200字以内
3. **快速迭代**：先生成初版，再根据需要调整
4. **后期编辑**：生成后可在PowerPoint中继续编辑

## 🐛 常见问题

### Q: 生成的PPT打不开？
A: 确保 python-pptx 版本正确：`pip install --upgrade python-pptx`

### Q: 字体显示不正常？
A: 安装推荐字体，或者系统会自动使用默认字体替代

### Q: 如何修改颜色主题？
A: 编辑 `ppt_generator.py` 中的 `COLOR_SCHEMES` 字典

### Q: 能否生成其他页数的PPT？
A: 目前固定25页结构，可以修改代码自定义

## 📞 技术支持

查看 `README.md` 获取更多帮助信息。

---

**版本**: v1.0
**更新日期**: 2025-12-04
**适用于**: Claude Code / Python 3.7+
