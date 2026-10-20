# 账号 B 一次性接入与固定领取

A / B 远端固定交接已启用。当前任务入口是 A 发布源码中的 `docs/collaboration/tasks/account-b.json`；每次从 A 的 handoff.source_sha 读取，不能假定 main 或旧 clone 已更新。

## 一次性加入 B 项目固定指令

> 你是 Music 账号 B。共同仓库为 https://github.com/KelvinChen-git/Music-Resource-Management-System 。每次开始先读取远端 collab/account-a 分支根目录 handoff.json、latest.md；有同步脚本则在自己的独立 clone 执行 python3 scripts/collab.py sync --account b，成功后按 handoff.source_sha 读取 docs/collaboration/tasks/account-b.json 及其 task_card_path。检查自己的 B feed 是否已经领取或完成同一 task_id + assignment_revision，继续在途任务，已完成不重复。新任务先核对 reviewed_sha 和允许写入路径，保留未提交工作，从卡片指定 SHA 创建或继续任务分支。先在自己的 latest.md 回传 claimed，含 task_id、assignment_revision、reviewed_sha、assignment_source_sha、实际 ack_peer_feed_sha，提交允许文件后 publish --account b；完成后再回传审核结论、独立实际命令与结果、阻塞及释放占用。不修改 A 的 STATUS / 任务入口 / feed，不自动合并或推送 main，不按旧附件自行推测下一步。网络 / 环境阻塞如实记录，不能以 A 的测试数字冒充 B 已实跑。缺脚本时先按下述方式只读接入，不覆盖原工作。

这段只需设置一次。之后每次启动 B 会话，B 从固定入口取得当时任务；不是后台常驻自动运行。

## 首次缺少同步脚本

1. 通过已有 GitHub 读取连接，打开固定 A feed 的 `handoff.json` 和 `latest.md`，记下 source_branch、source_sha，以及这次 A feed 的实际 SHA。不要把凭据发到聊天。
2. 在独立 B clone 先检查工作区；只 fetch handoff 指向的源分支，校验该 source_sha 可达，不 checkout / reset / clean / stash 覆盖已有工作。不直接沿用旧 MUS-001 审核基线作为当前任务。
3. 用 `git show` 在准确 source_sha 下读取任务入口 / 卡片和 `scripts/collab.py`。如需本机脚本，提取到被 ignore 的 `.local/collaboration/collab.py`，仅在文件不存在时创建，已有文件先核对不覆盖。该脚本的 root 识别使用当前 git 仓库，因此可以从旧审核基线读取新交接。
4. 执行 `python3 .local/collaboration/collab.py sync --account b`，成功后只读 receipt.status=fetched 的交接。记录真实 feed SHA；不能把旧缓存当本次成功。
5. 按本卡 reviewed_sha 建立当前 B 工作分支。卡片基线含正式 `scripts/collab.py` 时，后续用正式路径即可。若未提交修改或已有同名分支，先保留并核对，不擅自覆盖。

## 当前审核与回传

MUS-012-R1-B审核基线固定为 `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea`。任务发布所在的A source_sha可能更新，仅按任务入口的revision判断是否需要重新领取，不能把新的A文档提交当成新的审核对象。

具体范围、B分支与交付路径以 [任务卡](tasks/MUS-012-R1-B.md) 为准。只允许 B 创建 / 更新自己的审核报告和 latest；A 没有替 B 创建领取确认。没有独立 Java / MySQL 运行条件时继续静态审核并单列运行blocked，不重复失败命令，不写已经通过。

回传使用 `python3 scripts/collab.py publish --account b`（旧基线缺脚本时可用本机提取副本）。原子发布源码任务分支与B feed，成功后A可自行获取；用户无需复制正文。若B只有读权限，领取和报告回传仍blocked，需要其自身运行环境具备Git写权限，不能声称A已收到。

历史 MUS-001-R1 的目标为7ab0d39，B交付6e4118c / feed05d4e9f，仅是旧任务背景，不再作为当前领取任务。A的macOS路径不是B账号共享盘；B继续使用自己的隔离clone、端口、数据库及上传目录。
