# 项目清单示例

把这份内容存成任意 `.md` 或 `.txt`，然后：

```bash
python scripts/qr_rotator.py plan --list "project-list.md"
```

## 格式一：markdown 表格（推荐，和现有清单一致）

`/mnt/f` 会被自动映射成 `F:/`，第三列随便写什么都能忽略。

| 目录 | 拉取 | 推送 |
| --- | --- | --- |
| /mnt/f/work/code/github/wwwzhouhui/skills_collection | 是 | 是 |
| /mnt/f/work/code/github/wwwzhouhui/seedance2.0 | 是 | 是 |
| /mnt/f/work/code/github/xiaohuihui202504/wechat_downloader | 是 | 否 |

## 格式二：纯路径，一行一个

```
F:\work\code\github\wwwzhouhui\skills_collection
F:/work/code/github/wwwzhouhui/seedance2.0
wwwzhouhui/model-checker
```

相对路径（不含盘符）会被视为相对于 `config.json` 里的 `base_dir`。

## 格式三：直接命令行传

```bash
python scripts/qr_rotator.py update-repos \
  --policy replace \
  --dirs "wwwzhouhui/skills_collection, wwwzhouhui/seedance2.0"
```

逗号、分号、换行都能分隔。

## 注意事项

- 目录路径要指到**仓库根**（含 `README.md` 的那一层），不是子模块
- 重复项会自动去重
- 清单里出现 `projects.json → excluded` 的目录时，`plan` 会单独标出来，不会处理
- 只想看差异不动手：`plan` 永远是只读的
