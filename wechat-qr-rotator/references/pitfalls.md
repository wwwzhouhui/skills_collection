# 已知坑位清单

都是实际踩过的，不是假设。新增坑请追加在末尾。

## 1. git `detected dubious ownership`

`F:/work/code/github` 下部分仓库属主 SID 与当前登录用户不一致，直接 `git` 会报这个错并失败。

```bash
git -c safe.directory='*' -C <dir> <cmd>
```

脚本里所有 git 调用都带了 `-c safe.directory=*`（用 `subprocess` 传参，不会被 shell 展开成通配符）。**不要**改全局 `safe.directory`，那会把整台机器的信任边界放宽。

## 2. 损坏的 README.md

两类真实案例：

| 文件 | 症状 | 根因 |
|---|---|---|
| `xiaohuihui202504/linuxdo-helper-extension/README.md` | 13641 字节，其中尾部 5449 字节全是 `\x00` | 内容在 8192 字节处截断，git 里存的就是这个坏文件 |
| `wwwzhouhui/doubao_mcp_server/README.md` | 14007 字节全是 `\x00` | 空文件被写成了 NUL 填充 |

这类文件**没有二维码可换**，脚本会报 `DECODE_FAIL` 或 `NO_SECTION`。正确处置：
1. 加进 `projects.json` 的 `excluded`，附原因
2. 提醒用户人工重写（它们在 GitHub 上等于空文件）

不要试图「修复」它们——NUL 填充里没有可恢复的内容。

## 3. 二维码链接的形态会变，别硬编码

同一个群码，历史上出现过三种写法：

```
Obsidian/20261016200151_1_3.jpg              # 时间戳 + 序号
Obsidian/d51aa2bf-8da0-4368-8ba7-...jpg      # UUID
Obsidian/image-20261024100147846.png         # Obsidian 粘贴命名，且是 png
```

所以：
- 不能按 `.jpg` 匹配（可能是 png）
- 不能按 UUID 正则匹配（可能是时间戳）
- **唯一的真相来源是 SKILL.md 的「技术交流群」章节**

脚本正是这么做的：旧链接 = 该章节当前那张图，不猜。

## 4. 图片缓存

URL 不变 = 图片可能不变。两层缓存：

- 腾讯 COS：同名覆盖后 CDN 边缘节点可能还吐旧图
- GitHub camo：`camo.githubusercontent.com` 按 URL 缓存，README 里换了链接才会重新抓

对策：`upload` 默认把图片改名成唯一文件名再上传（`qr-<时间戳>-<随机>.jpg`），URL 天然不同。**不要用 `--keep-filename` 反复传同名图**，除非你确认缓存已经过期。

## 5. PicList 的 heartbeat 只认 GET

`HEAD http://127.0.0.1:36677/heartbeat` 会返回非 200，看起来像服务挂了。实际服务是好的。

判断在线必须用 GET：

```bash
curl -s http://127.0.0.1:36677/heartbeat     # {"success":true,"result":"alive"}
```

## 6. PicList 上传要 Windows 反斜杠路径

`POST /upload` 的 `{"list": [...]}` 里传 `C:/a/b.jpg` 有时会被拒，传 `C:\\a\\b.jpg` 稳定。脚本里统一 `str(path).replace("/", "\\")`。

## 7. Windows 控制台 cp936 会炸

含中文和箭头的输出在默认 cp936 下抛 `UnicodeEncodeError`。脚本开头：

```python
sys.stdout.reconfigure(encoding="utf-8")
```

自己写新脚本时别忘了这两行。

## 8. README 编码五花八门

实测出现过：纯 UTF-8、UTF-8 with BOM、UTF-16 LE（带 BOM）。

- 必须按 BOM/探测结果读写，**写回时用原编码**
- 混用会整文件乱码，提交后 diff 一片红
- `grep` 匹配 UTF-16 文件会「找不到」，别据此判断内容不存在——用 Python 读

## 9. `skills_collection` 里有几十项无关改动

该仓库长期挂着 30+ 项未提交的产出物。**绝对禁止 `git add .` 或 `git add -A`**，会把这些一起推上去。

正确姿势：`git add -- README.md`（`--` 后面跟精确相对路径），提交后再用 `git diff-tree --no-commit-id --name-only -r HEAD` 核对只有目标文件。脚本的 `push` 两步都做了。

## 10. GitHub 网络会瞬时抽风

现象：`SSL/TLS handshake failure` 或直接卡到超时，重试一次就好。走本地代理时更明显。

- 单仓库别死等：脚本给 push 2 次重试，间隔 3 秒
- 批量几十个仓库整体超时上限设大到 10 分钟
- 判断网络是否真的不通：`curl -o /dev/null -w "%{http_code}" https://api.github.com`，拿到 200 就是瞬时抖动

## 11. remote URL 里内嵌明文 Token（安全问题）

部分仓库的 `remote.origin.url` 形如 `https://<token>@github.com/owner/repo.git`。风险：

- token 随 `.git/config` 落盘，目录被打包/备份就泄露
- `git push` 的报错输出会带出 URL，日志里也有

处置建议：改用 Git Credential Manager 存凭据，remote 换回 `https://github.com/owner/repo.git`。**脚本不会打印完整 remote URL**，`remote_owner()` 只提取 owner 段。

## 12. 章节里可能有多个二维码

「技术交流群」章节里只应有一张群码。如果人为塞了两张（比如群码 + 公众号码），脚本只换**最靠前**那张，并在备注里标「章节外还有 N 处旧图（未改）」。

看到这个备注就去人工确认一下，别默认它没问题。

## 13. alt 文本有两种语义，不要统一

| 位置 | alt 风格 | 原因 |
|---|---|---|
| `SKILL.md` | 文件名式 `image-20261024100147846` | 作者粘贴图片时 Obsidian 自动填的 |
| `templates/*.md`、仓库 `README.md` | 语义化 `技术交流群` | 对读者和屏幕阅读器有意义 |

脚本策略：alt 匹配文件名式才跟着换，语义化一律保留。**不要**为了「统一」把 `技术交流群` 改成文件名——那会让模板可读性变差。

## 14. `.mimosa` 是运行时垃圾

`templates/.mimosa/` 是工具跑任务留下的 hook 状态和日志（约 30KB）。同步到运行环境时必须排除，否则 `diff` 会一直报「只在源码存在」，看着像没同步干净。

## 15. `/mnt/f` 与 `F:\` 混用

用户在 WSL 视角下写清单（`/mnt/f/work/...`），脚本在 Windows Python 下跑。`norm_dir()` 负责映射：

```
/mnt/f/work/code/github/x  →  F:/work/code/github/x
```

顺带处理：反斜杠转正斜杠、去尾斜杠、绝对路径若在 `base_dir` 下则转成相对路径。

## 16. 首次安装会把开发脚本带进运行环境

`github-readme-generator/` 下有 `google_search_worldcup.py`、`logs/` 这类与 skill 无关的东西。首次完整安装时用 `config.install_exclude` 排除，别让运行环境变成垃圾场。
