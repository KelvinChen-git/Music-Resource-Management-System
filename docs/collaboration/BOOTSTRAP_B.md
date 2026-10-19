# 账号 B 一次性接入

以下内容可一次性加入 B 的 Music 项目固定指令。**必须先等 A 的远端发布成功；目前尚未发布。** 后续双方会话按固定 Git 位置读取，用户不再逐次复制两边报告。

> 你是 Music 账号 B。共同仓库为 https://github.com/KelvinChen-git/Music-Resource-Management-System 。开始每次工作先读取远端 `collab/account-a` 分支根目录 `handoff.json` 和 `latest.md`，再按 source_sha 读取 AGENTS.md、README.md、docs/PROJECT.md、docs/CONTRACTS.md、docs/STATUS.md 与任务卡。不要仅依据 main 或旧附件。使用自己的独立 clone 和 slot B。执行 `python3 scripts/collab.py sync --account b`；失败时明确阻塞并保留原工作，不拿缓存冒充最新状态。任务完成或检查点时更新 `docs/collaboration/account-b/latest.md`，写明审核 SHA、测试结果、阻塞、下一步和 ack_peer_feed_sha；提交明确授权文件后执行 `python3 scripts/collab.py publish --account b`。不写 A 的 feed 或 STATUS，不直接 push main、不自动合并。读取失败时继续独立可做的工作，不接管对方文件。

## 首次取得脚本

第一次可通过 GitHub 读取连接查看固定 A feed；其中 source_branch 应为 A 实际发布的任务分支，source_sha 为准确版本。新建独立 clone 的 B 可以直接 clone 该源码任务分支，随后创建自己的任务分支。

若已有 B clone，先查看 `git status --short --branch`，保留任何修改；只 fetch，不 reset / stash / clean。第一次 A 发布本任务后可执行：

```bash
git fetch origin refs/heads/chore/MUS-008-account-sync:refs/remotes/account-a/MUS-008
```

在未提交工作区中无需切换分支即可阅读：

```bash
git show refs/remotes/account-a/MUS-008:docs/collaboration/README.md
git show refs/remotes/account-a/MUS-008:docs/handoffs/MUS-001-B.md
```

MUS-001-R1 的准确审核源码仍固定为 `7ab0d39d920a538b28878cf92ecbe90e55994ec3`。该旧提交没有新同步脚本；可从已核对的 A 发布版本提取一份只用于本机的脚本，再进入准确审核分支：

```bash
# 仅当不存在同名文件时才创建；若已存在，先核对，不覆盖。
mkdir -p .local/collaboration
(set -C; git show refs/remotes/account-a/MUS-008:scripts/collab.py > .local/collaboration/collab.py)
python3 .local/collaboration/collab.py sync --account b
# 工作区干净且不存在同名分支时：
git switch -c review/MUS-001-B-baseline 7ab0d39d920a538b28878cf92ecbe90e55994ec3
```

审核报告正文只写 `docs/reviews/MUS-001-B.md`；交接索引另允许写 `docs/collaboration/account-b/latest.md`。后者由 B 自己新建，A 没有替 B 创建。提交后可用本机提取的脚本发布：

```bash
python3 .local/collaboration/collab.py publish --account b
```

第一次 B 报告说明已收到 MUS-001-R1、当前环境是否能复跑，以及已读 A feed 的提交号；不会因为原始首次审核已经完成而把 R1 标 done。

如 B 只有 GitHub 读取权限，仍可自动获取 A 的交接，但不能回传。写入配置是一次性前提，未解决前如实记录。原始报告和临时 clone 不能作为共享盘，也不要把机器绝对路径当作另一账号可读位置。
