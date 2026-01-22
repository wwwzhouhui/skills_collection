---
name: github-trending
description: 获取 GitHub Trending 前五项目的 README 与摘要，并发送企业微信消息。适用于热门项目跟踪、技术趋势简报与团队分享。
---

# GitHub Trending 摘要推送

## 功能
- 抓取 https://github.com/trending 今日热门前 5 项目
- 拉取每个项目 README
- 生成包含项目是什么、解决问题、技术栈、Star 数量的中文摘要
- 通过企业微信机器人发送摘要

## 脚本
### 1. 抓取与保存
```bash
python fetch_trending.py --output trending_top5.json
```

### 2. 生成摘要并发送
```bash
python send_wecom_summary.py --input trending_top5.json
```

## 配置
- 可选环境变量 `GITHUB_TOKEN` 用于提高 GitHub API 额度
- 可选环境变量 `WEIXIN_WEBHOOK` 覆盖默认企业微信机器人地址
