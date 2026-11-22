## 2026-11-05 - Task: 迁入 WorkBuddy 数据迁移技能并更新项目文档

### What was done

- 将 `workbuddy-data-migrator` 完整六文件迁入仓库根目录，保留原有作者 `hailaobao2026`、默认数据目标 `D:\aiwork\WorkBuddy_C`、安全规则、历史记录和备份；未修改迁移脚本。
- 原 `%USERPROFILE%\.agents\skills\workbuddy-data-migrator` 改为指向本仓库技能目录的 NTFS junction，当前会话已通过原入口重新加载技能。
- README 新增技能清单、功能介绍、Windows 安装方法、只读示例、目录结构和更新记录；按页面既有清单口径统一为 33 项，不重写其他技能内容或虚构版本号。
- 新增维护说明，明确技能存放位置与数据迁移目标的区别，提供安装位置回滚方法。
- 使用独立分支 `feat/workbuddy-data-migrator`，仅纳入本轮技能及文档；已有其他本地修改和未跟踪文件保持原样，不纳入提交。提交与远程推送结果以实际 Git 记录和远程引用核验为准。

### Testing

- PASS：源与目标均为普通目录，目标同名目录原先不存在，源内无重解析点；C、F 均为本地固定 NTFS 盘。
- PASS：迁入前后六文件共 35,927 字节；与本轮原目录副本逐文件比较 SHA-256 一致，原安装入口读取结果亦全部一致。
- PASS：原入口 `LinkType=Junction`，目标为 `F:\work\code\github\wwwzhouhui\skills_collection\workbuddy-data-migrator`；当前环境 Skill 工具重新加载成功。
- PASS：技能 name、author 及六处默认数据目标引用保持不变。
- PASS：README 技能清单 33 项，数量徽章与总数一致；新增本地文档链接全部可解析。
- PASS：迁移辅助脚本通过 PowerShell 语法解析，未执行脚本；README 与维护说明共四个 PowerShell 代码块通过语法解析。
- PASS：README 和新增维护说明保持 UTF-8 无 BOM、LF 换行；`git diff --check -- README.md` 通过。现有 `core.autocrlf=true` 提示未来 Git 操作可能转换换行，本轮未修改该配置，也未执行全量转码。
- PASS：六个技能文件未命中常见令牌或私钥特征；这不是完整安全审计，也未检查无关文件。
- PASS：Git 远程身份为 `github.com/wwwzhouhui/skills_collection`，远端默认分支为 `main`；任务开始时本地基线与远端 main 均为 `311d266650540cf58f2f24729d46ce3a54d1a8c6`，暂存区为空。
- 检查工具情况：计划模式未执行受限 Git/PowerShell 查询，批准后补齐；Git 因跨 Windows 用户所有权报告 dubious ownership，后续仅用单次 `-c safe.directory=F:/work/code/github/wwwzhouhui/skills_collection`，未修改全局信任配置。一次静态检查命令因 Markdown 围栏反引号转义产生 PowerShell 解析错误，修正后完整重跑通过。
- GitHub CLI 未找到，本次使用现有 Git 完成提交与推送，不额外安装工具；推送权限以实际推送结果验证。
- 未执行：WorkBuddy 数据 Inspect、Migrate、Rollback、应用验收、全仓测试或 GitHub Release；本轮只验证技能文件迁移、加载与文档。

### Notes

改动文件清单：

- `workbuddy-data-migrator/SKILL.md`：按原内容迁入技能说明、作者及目标路径规则。
- `workbuddy-data-migrator/scripts/workbuddy-migrate.ps1`：按原内容迁入迁移脚本。
- `workbuddy-data-migrator/references/safety-and-recovery.md`：按原内容迁入安全与恢复说明。
- `workbuddy-data-migrator/docs/target-directory.md`：按原内容迁入默认目标说明。
- `workbuddy-data-migrator/docs/SKILL.before-target-change.2026-11-04.md.bak`：按原内容保留历史技能原文备份。
- `workbuddy-data-migrator/progress.md`：按原内容保留技能历史日志，不改写历史。
- `README.md`：新增技能介绍、安装及只读使用示例，并同步本页清单统计。
- `docs/workbuddy-data-migrator.md`：新增仓库维护、安装入口、验证边界及可执行回滚说明。
- `progress.md`：新增本轮迁移与验证记录。

仓库外变动：原 C 盘技能目录改为 junction；本轮临时原目录副本位于 `%USERPROFILE%\.agents\skills\.workbuddy-data-migrator.move-backup-20261105`，按获批方案保留至发布核验完成，只清理这个临时副本，不清理技能内部历史备份。未改变其他技能、工作区或 WorkBuddy 数据。

回滚点：迁入前仓库基线为 `311d266650540cf58f2f24729d46ce3a54d1a8c6`。先按 `docs/workbuddy-data-migrator.md` 的校验复制步骤恢复 C 盘真实安装目录，再针对本次迁入提交执行 `git revert`。可在仓库中用 `git log -1 --format=%H -- workbuddy-data-migrator/SKILL.md` 获取迁入提交号，审核后回退；不要强推、不要 reset 丢弃其他工作区修改。回滚完成后仅在日志末尾追加记录。

## 2026-11-05 - Task: 确认 GitHub 发布并完成临时副本清理

### What was done

- 已提交并推送主体变更 `2b13bf2ff589baa6888f81196fee5222236838a7`，包含本次九个文件；远程分支为 `origin/feat/workbuddy-data-migrator`，未修改或合并 `main`。
- 提交署名经用户明确确认，仅本次使用 `wwwzhouhui <75271002@qq.com>`；未修改全局或仓库 Git 身份配置。
- 发布核验完成后，重新检查本轮临时原目录副本及六文件 SHA-256，仅删除六个已确认重复文件并非递归移除空目录；技能内部历史备份、仓库真实目录和原安装入口保留。

### Testing

- 首次 commit 因 `Author identity unknown` 失败，未创建提交；用户确认本次署名后，提交成功。
- PASS：暂存区严格为本次九个路径；每个暂存对象与工作文件原始字节一致，`git diff --cached --check` 通过。
- PASS：`git push -u origin feat/workbuddy-data-migrator` 成功；`git ls-remote` 返回提交号与本地主体提交 `2b13bf2ff589baa6888f81196fee5222236838a7` 一致。
- PASS：清理前临时副本为普通目录，无内部重解析点，六文件共 35,927 字节；与仓库和安装入口的 SHA-256 均一致。清理后仅该临时副本不存在，正式技能仍为六个文件且内部历史备份存在。
- 未执行 WorkBuddy 数据迁移、强推、自动合并或 Release；其他本地修改未加入本次提交。

### Notes

本轮改动文件：

- `progress.md`：仅追加发布、身份确认及临时副本清理结果，不改写前一轮记录。
- `%USERPROFILE%\.agents\skills\.workbuddy-data-migrator.move-backup-20261105`：删除本次临时副本内六个已校验重复文件及空目录，不删除正式文件或内部历史备份。

回滚方式：临时副本内容仍完整保存在仓库及主体提交中；按 `docs/workbuddy-data-migrator.md` 的校验复制步骤可恢复 C 盘真实安装目录。若需撤销主体仓库变更，先恢复安装入口，再审核执行 `git revert 2b13bf2ff589baa6888f81196fee5222236838a7`；保留历史日志，另行追加回滚说明。

## 2026-11-06 - Task: 合并 WorkBuddy 跨平台迁移更新到主分支

### What was done

- 将功能分支 `feat/workbuddy-data-migrator` 的跨平台更新合并到 `main`，保留原有 Windows 目录联接方案，并增加 Linux/macOS 符号链接迁移脚本、临时数据自检和平台说明。
- Windows 状态文件改为临时文件写入后原子替换，降低写入中断留下不完整 JSON 的风险。
- 同步更新仓库维护文档，使文件清单、验证方式和平台边界与当前九文件技能目录一致。
- 使用独立 Git worktree 完成合并，未带入原工作区其他目录的未提交修改或未跟踪文件。

### Testing

- PASS：合并预演无冲突，合并后的功能改动严格为 `workbuddy-data-migrator` 下六个文件；维护文档与本日志为本轮要求的同步记录。
- PASS：PowerShell 迁移脚本通过 `System.Management.Automation.Language.Parser.ParseFile` 语法解析，未执行真实数据迁移。
- PASS：两个 Python 脚本在 WSL Python 3 下通过隔离语法编译。
- PASS：POSIX 临时数据端到端自检通过，结果为 `26 passed, 0 failed`，覆盖 Inspect、Migrate、链接核验、变更后回滚拒绝、显式回滚及危险目标拒绝。
- PASS：`git diff --cached --check` 通过；主分支与功能分支上重复的二维码更新补丁内容一致，没有形成额外文件差异。
- 未执行真实 WorkBuddy 数据迁移、Windows robocopy 实机迁移、macOS 实机迁移或应用验收。

### Notes

改动文件清单：

- `workbuddy-data-migrator/SKILL.md`：扩展为 Windows、Linux 和 macOS 三平台迁移流程。
- `workbuddy-data-migrator/references/platform-paths.md`：新增平台路径、链接机制及限制说明。
- `workbuddy-data-migrator/references/safety-and-recovery.md`：补充三平台共同安全边界、状态机和恢复规则。
- `workbuddy-data-migrator/scripts/selftest_posix.py`：新增只使用临时测试数据的 POSIX 端到端自检。
- `workbuddy-data-migrator/scripts/workbuddy-migrate.ps1`：状态文件改为临时写入后原子替换。
- `workbuddy-data-migrator/scripts/workbuddy_migrate.py`：新增 Linux/macOS Inspect、Migrate 与 Rollback 实现。
- `docs/workbuddy-data-migrator.md`：同步当前文件范围、验证入口和平台验证边界。
- `progress.md`：追加本轮合并、验证与回滚记录。

回滚方式：先确认后续提交未依赖新增的 POSIX 脚本，再执行 `git revert -m 1 "$(git log -1 --format=%H --grep='^merge: 合并 WorkBuddy 跨平台迁移更新$' main)"`；不要强推或重置其他人的主分支历史。回滚只撤销仓库代码，不触碰任何真实 WorkBuddy 数据、迁移目标或备份目录。
## 2026-11-17 - Task: article-cover-generator 新增 ModelScope MiniMax-H3-Image 选择

### What was done

- 保留 `gpt-image-2.5` 默认路径并新增 `MiniMax/MiniMax-H3-Image` 模型选择，同一 Node.js 入口分别适配 GPT 中转站与 ModelScope 的异步创建、轮询和图片下载协议；旧版自定义 GPT 模型仍可继续使用。
- 配置改用 `ARTICLE_COVER_*` 命名空间并兼容技能目录 `.env` 的旧变量名，GPT 与 ModelScope 凭证分离；进程环境只读取命名空间变量，端点与密钥必须来自同一配置来源，避免环境变量碰撞时把本地密钥发送到意外地址。
- 创建任务只提交一次，网络结果不明确时标记为不可安全重试；无效/重复/缺值参数、无效比例和尺寸均在联网前拒绝，轮询临时错误只查询同一个 task_id。
- 下载结果在写盘前验证 PNG、JPEG 或 WebP 结构并读取实际尺寸，错误页不再作为图片落盘；同时修复纯文件名和默认输出路径的目录创建问题。
- 同步技能说明、配置模板、根 README 和双模型维护文档，明确 MiniMax 当前只能通过提示词约束比例，不能承诺精确画幅。

### Testing

- PASS：Windows Node.js `v24.21.0` 下，`node --check` 通过生产脚本和测试脚本语法检查。
- PASS：`node --test article-cover-generator/scripts/gen_cover.test.mjs` 共 12 项全部通过，覆盖默认 GPT、自定义 GPT 兼容、通用进程变量隔离、ModelScope 请求合同与首图下载、失败即停、所选模型密钥隔离、端点密钥同源、创建不重试、轮询恢复、无效输入零网络请求、错误页拒绝落盘和纯文件名输出。
- PASS：经用户明确授权只进行 1 次真实 ModelScope 创建；任务返回 `SUCCEED`，下载 910,426 字节的有效 PNG，脚本读取实际尺寸 760×1280，临时图片随后删除。提示词要求 16:9 但服务返回竖图，因此文档明确记录该限制；未再次创建任务验证比例。
- PASS：目标文件未命中用户提供的 Token；Token 只用于单次进程环境变量注入，未写入仓库文件或脚本输出。由于 Token 曾在对话中明文提供，交付时提醒用户在 ModelScope 后台轮换。
- PASS：`git diff --check` 通过本轮受跟踪文件；Git 仅提示现有 `core.autocrlf` 将来可能把 LF 转为 CRLF，本轮未修改 Git 配置或全量转码。
- 未执行：GPT 真实接口、JPEG/WebP 线上下载、Node.js 18 实机测试、提交、推送或发布；仓库原有大量无关未提交/未跟踪内容保持不动。

### Notes

改动文件清单：

- `article-cover-generator/scripts/gen_cover.mjs`：新增双模型路由、ModelScope 异步协议、安全配置合并、参数校验、计费安全和图片结构/尺寸校验。
- `article-cover-generator/scripts/gen_cover.test.mjs`：新增 12 项零依赖模拟接口与回归测试。
- `article-cover-generator/.env.example`：增加两套服务的空凭证模板、命名空间和旧变量兼容说明。
- `article-cover-generator/SKILL.md`：补充模型选择、凭证、比例差异、交付检查和失败处理规则。
- `docs/article-cover-generator.md`：新增双模型配置、协议、计费边界、验证结果与回滚说明。
- `README.md`：同步技能清单、功能、命令、配置、技术栈、目录树和 2026-11-17 更新记录，不改写 2026-10-25 历史条目或技能数量。
- `progress.md`：仅在末尾追加本轮实现与验证记录。

回滚方式：仓库当前存在其他未完成改动，禁止使用 `git reset --hard` 或整仓覆盖。审核工作区后，仅还原上述 `article-cover-generator` 受跟踪文件和根 README 的本轮差异，删除本轮新增的 `gen_cover.test.mjs` 与 `docs/article-cover-generator.md`，并在本日志末尾另行追加回滚记录；已有本地 `.env` 含用户凭证，不属于版本回滚范围，不要删除或提交。
