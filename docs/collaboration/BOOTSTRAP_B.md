# 账号 B 一次性接入与固定领取

A / B 远端固定交接已启用。首次领取从当前 A `handoff.source_sha` 读取 `docs/collaboration/tasks/account-b.json`。接管开发后从自己的有效发布继续，不能假定 main 或旧 clone 已更新。

## 一次性加入 B 项目固定指令

> 你是 Music 账号 B。共同仓库为 https://github.com/KelvinChen-git/Music-Resource-Management-System 。每次开始在自己的隔离 checkout 同步 A/B 固定入口（python3 scripts/collab.py sync --account b），按 A 的 handoff.source_sha 核对任务入口和本卡，并检查自己的 B feed 是否已领取同一任务/修订。普通审核按 reviewed_sha；MUS-067-B 开发移交按卡片要求从 assignment_source_sha 启动，先提交 STATUS 和自己的 latest，记录 claimed、任务/修订、active_owner、base_sha、assignment_source_sha 与实际 ack_peer_feed_sha，再 publish --account b 并回读。认领后 B 独立开发、验收、发布和维护唯一 STATUS，从 B 最新有效源码续做，不等 A 汇总，不代写 A 报告/派发/交接分支。只有用户明确指定才再次移交；不自动合并或推送 main。保留未提交工作，环境和网络阻塞如实记录，不以 A 的结果冒充 B 实跑。缺脚本时按下方只读接入。

这段只需设置一次。之后每次启动 B 会话，B 从固定入口取得当时任务；不是后台常驻自动运行。

## 首次缺少同步脚本

1. 通过已有 GitHub 读取连接，打开固定 A feed 的 `handoff.json` 和 `latest.md`，记下 source_branch、source_sha，以及这次 A feed 的实际 SHA。不要把凭据发到聊天。
2. 在独立 B clone 先检查工作区；只 fetch handoff 指向的源分支，校验该 source_sha 可达，不 checkout / reset / clean / stash 覆盖已有工作。不直接沿用旧 MUS-001 审核基线作为当前任务。
3. 用 `git show` 在准确 source_sha 下读取任务入口 / 卡片和 `scripts/collab.py`。如需本机脚本，提取到被 ignore 的 `.local/collaboration/collab.py`，仅在文件不存在时创建，已有文件先核对不覆盖。该脚本的 root 识别使用当前 git 仓库，因此可以从旧审核基线读取新交接。
4. 执行 `python3 .local/collaboration/collab.py sync --account b`，成功后只读 receipt.status=fetched 的交接。记录真实 feed SHA；不能把旧缓存当本次成功。
5. 按本卡指定起点建立 B 工作分支。普通审核用 `reviewed_sha`；MUS-067-B 用发布本卡的 `assignment_source_sha`，它包含移交规则。该提交含正式 `scripts/collab.py` 时，后续用正式路径即可。若有未提交修改或已有同名分支，先保留并核对，不擅自覆盖。

## 当前接管与回传

当前入口为 [MUS-067-B](tasks/MUS-067-B.md) 暂时开发移交，旧审核任务不重复领取。A 已暂停，B 用独立 checkout 发布认领后维护自己发布源码的 `docs/STATUS.md`，并依卡片推进第一个在线检索检查点。

具体范围、B 分支、验收及职责以 [任务卡](tasks/MUS-067-B.md) 为准。A 没有替 B 创建领取确认。没有独立 Java / MySQL / 模型运行条件时，记录对应阻塞，继续不依赖缺失条件的工作；不把静态或替身检查写为实际运行通过。

优先使用 `python3 scripts/collab.py publish --account b`（旧基线缺脚本时可用本机提取副本），原子发布源码任务分支与 B feed。CLI 不可用时，按任务卡沿用 B 既往的 GitHub 写入方式，先发布源码再写自身 feed，分别回读核验并注明非原子。认领后用户和 A 可直接读取 B 的现行状态，用户无需复制正文。若 B 只有读权限，领取和回传仍 blocked；需要 B 自己的 Git 写权限，不能声称已回传。

历史 MUS-001-R1 的目标为7ab0d39，B交付6e4118c / feed05d4e9f，仅是旧任务背景，不再作为当前领取任务。A的macOS路径不是B账号共享盘；B继续使用自己的隔离clone、端口、数据库及上传目录。
