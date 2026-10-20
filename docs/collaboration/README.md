# 两账号固定交接入口

同一 GitHub 仓库是固定入口，两边继续使用独立 clone / worktree。ChatGPT 的聊天、Library 和本地路径不会因使用同一个项目名称而跨账号共享。

仓库：<https://github.com/KelvinChen-git/Music-Resource-Management-System>。

**启用状态：远端交接已启用。** 2026-10-19 A 原生 git publish / sync 已成功，B feed 05d4e9f 可读取；MUS-012 验收已发布为d7c9faa / feed5592274。GitHub读取连接先前push=false不代表原生git当前仍不能写。任务发布仅说明远端可读，B须通过自己的feed主动确认；本机B槽测试不能代替独立B账号审核。B首轮环境为Linux `/workspace`，不能将A的macOS路径当共享目录。

## 固定位置与归属

| 位置 | 写入方 | 内容 |
|---|---|---|
| `collab/account-a` 分支根目录 `latest.md`、`handoff.json` | A | 最新 A 交接，以及准确源码分支 / SHA / 报告哈希 |
| `collab/account-b` 分支根目录 `latest.md`、`handoff.json` | B | 最新 B 交接，格式相同 |
| 源码任务分支 `docs/collaboration/account-a/latest.md` | A | A 用于发布的报告；任务、测试、阻塞、下一步及已读 B feed SHA |
| 源码任务分支 `docs/collaboration/account-b/latest.md` | B | B 用于发布的报告；包括审核针对的 SHA、运行结果和占用释放 |
| A 源码任务分支 `docs/STATUS.md` | 当前集成负责人 A | 唯一任务台账；B 通过自己的 feed 汇报，不能直接争写 |
| A 源码任务分支 `docs/collaboration/tasks/account-b.json` | A | B 当前待领取任务、修订号、固定审核 SHA 与任务卡路径 |
| A 源码任务分支 `docs/collaboration/tasks/MUS-012-R1-B.md` | A | 当前 B 审核任务的范围、允许路径、验收及回传要求 |
| `docs/collaboration/imports/` | 导入人，保留来源 | 历史交付原文，不能冒充当前任务审核或对方发布 |
| 各 clone `.local/collaboration/inbox/account-{a,b}/` | 本机同步程序 | 只读使用的接收缓存；不提交、不当共享目录 |

固定浏览入口：

- [账号 A 交接](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/collab/account-a/latest.md)
- [账号 B 交接](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/collab/account-b/latest.md)

交接分支只有两份小文本文件，通过 Git 历史保留旧版本；源码留在对应任务分支。程序不会切换当前分支、合并代码、改数据库、自动 stage 工作文件或推送 main。

## 每次工作：开始读、结束发

从自己的仓库根目录执行，B 将 `a` 换成 `b`：

```bash
python3 scripts/collab.py sync --account a
# 只在 exit 0 后查看 receipt.status=fetched 的 latest.md / handoff.json。
# 先读对方报告，再按其中 source_sha 查阅源码 / STATUS / 任务卡。
# 开发、验证，更新自己的报告；在任务分支只提交本任务的明确文件。
python3 scripts/collab.py publish --account a
```

`sync` 获取双方 feed 和所引用源码分支，检查报告哈希和源码提交可达性，写缓存但不 checkout 或 merge。源码对象位于 `refs/music-collab/sources/account-a/<任务分支>` 等本地 ref；可用 `git show <source_sha>:docs/STATUS.md` 读取 A 台账，不需要修改当前工作区。

`publish` 要求工作区干净、当前为任务分支、自身报告已提交。它仅读取 HEAD 中的报告，原子推送“源码任务分支 + 自身交接分支”；任一 ref 冲突则全部失败。不会执行 force push、reset、clean、stash 或自动合并。另一个账号不能用自己的身份替对方发布 feed。Git 中的写入权限仍由仓库控制，逻辑归属不是自动强制的 ACL。

网络 / 凭据 / 非快进错误返回非零，旧缓存仍保留，但**不是本次成功同步**。远端缺少某个 feed 返回 `not_published`，不能解释为对方已接收任务。失败后继续做不依赖新状态的工作；修改共享路径、API 或接管任务必须先完成协调。

发布成功只表示“远端可读”；收到方在自己的下一份报告中记录 `ack_peer_feed_sha`，才表示已经读取。不根据时间推断对方已停止。原始状态、任务、摘要仍由报告正文表达，不用机器时间判定工作成果。

## 一次性启用（已完成的接入流程）

1. 为 A、B 所用运行环境各配置同一仓库的 Git 读取和任务分支写入权限。GitHub 连接的 `push=false` 是当时该连接的访问状态；调整 ChatGPT 的“是否询问”偏好不会增加 GitHub OAuth / 仓库权限。不要把 token、私钥或密码写进聊天、仓库或报告。
2. A 在 `chore/MUS-008-account-sync` 完成本地提交后执行 `publish --account a`。该操作发布完整 A 源码历史及固定 A feed；成功前 B 从远端 main 仍取不到这些产出。
3. B 第一次获取 A feed，按 [BOOTSTRAP_B.md](BOOTSTRAP_B.md) 将同步约定加入自己的项目固定指令；以后每次开始 / 检查点 / 结束调用同步命令，无需用户逐次搬运报告。A 不能替独立账号设置项目指令。
4. B 的首份主动发布确认任务接收，并写 `ack_peer_feed_sha`；A 下次 sync 检查到该确认后更新 STATUS。不能把本次导入的旧报告充当这份确认。

此流程是**任务会话运行时的自动协作约定**。它没有启动后台服务，不会在两个账号都停用时唤醒模型，也不会自动决定合并代码。需要定时检查时另行安排定时任务；不把缓存同步等同持续自主开发。

如终端无法联网但账号有 GitHub 读取连接，可直接读固定分支的 `handoff.json` 和 `latest.md`，再按 `source_sha` 读取源码。发布仍须有 Git 写入能力；当前脚本依赖 Python 3.9+ 和支持原子推送的 Git 远端，原生 GitHub 发布 / 拉取链路已验收；单个账号的新环境仍需分别核对权限。

## 报告字段

每份 `latest.md` 至少包含：account / task、reviewed_sha（审核时）、本轮修改及验证、未完成或 blocked、占用与允许路径、下一任务、`ack_peer_feed_sha`。`handoff.json` 的 source_sha 由程序在提交后填写，避免在同次提交中自引用最终 SHA。

导入 B 的第一份报告见 [原文](imports/account-b/2026-10-19-baseline-review.md) 和 [整合说明](B-INITIAL-REVIEW.md)。它基于 b81f57c；针对 7ab0d39 的 MUS-001-R1已有B交付6e4118c，后端补证仍blocked；当前新审核以固定任务入口为准。A 本轮不修改 B 独占的 `docs/reviews/MUS-001-B.md` 或伪造 B feed。


## 固定领取 B 任务

1. B每次开始先sync并校验A feed，再从其handoff.source_sha读取 `docs/collaboration/tasks/account-b.json`，按task_card_path读完整卡片。缺脚本的首次接入见 [BOOTSTRAP_B.md](BOOTSTRAP_B.md)。无需用户每轮复制任务正文。
2. 派发由A写入，认领和完成由B在自己的feed确认。A派发状态assigned不意味着B已认领；B先发布claimed与task_id、assignment_revision、reviewed_sha、assignment_source_sha、实际ack_peer_feed_sha，再执行任务。
3. B以task_id + assignment_revision检查自己的历史：在途继续，已完成不重复；A feed变更本身不是新任务。固定reviewed_sha与发布任务卡的source_sha是两种不同输入，不混用。
4. A每轮结束发布自身结果时同步维护B任务入口。有在途任务就保留；只有确需调整时才增加修订或发布新task_id，并在交接说明原因。无可分配工作则明确waiting，不让B猜测下一步或自行抢占源码。
5. B完成后发布自己的报告，A下次sync读取、处理发现并串行更新STATUS。B不能修改A固定任务入口、STATUS或擅自扩大写入范围。

当前卡片是 [MUS-012-R1-B](tasks/MUS-012-R1-B.md)。该机制只在会话运行时执行，没有创建轮询进程或定时任务，也不会自动启动B的聊天。首次仍需用户启动B并发一次固定入口指令。
