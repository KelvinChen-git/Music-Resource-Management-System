# 两账号固定交接入口

同一 GitHub 仓库是固定入口，两边继续使用独立 clone / worktree。ChatGPT 的聊天、Library 和本地路径不会因使用同一个项目名称而跨账号共享。

**2026-11-13：用户已授权暂由 B 接手后续开发和集成。** A 发布 [MUS-067-B](tasks/MUS-067-B.md) 后暂停开发与台账写入。B 自己发布有效认领后，唯一现行台账是 B feed `handoff.source_sha` 所指的 `docs/STATUS.md`。A 的发布作为授权和历史快照保留；B 阶段交付无需再由 A 整合。再次改变角色由用户明确指定，最终合并决定仍归用户。

仓库：<https://github.com/KelvinChen-git/Music-Resource-Management-System>。

**启用状态：远端交接已启用。** 2026-10-19 A 原生 git publish / sync 已成功，B feed 05d4e9f 可读取；MUS-012 验收已发布为d7c9faa / feed5592274。GitHub读取连接先前push=false不代表原生git当前仍不能写。任务发布仅说明远端可读，B须通过自己的feed主动确认；本机B槽测试不能代替独立B账号审核。B首轮环境为Linux `/workspace`，不能将A的macOS路径当共享目录。

## 固定位置与归属

| 位置 | 写入方 | 内容 |
|---|---|---|
| `collab/account-a` 分支根目录 `latest.md`、`handoff.json` | A | 最新 A 交接，以及准确源码分支 / SHA / 报告哈希 |
| `collab/account-b` 分支根目录 `latest.md`、`handoff.json` | B | 最新 B 交接，格式相同 |
| 源码任务分支 `docs/collaboration/account-a/latest.md` | A | A 用于发布的报告；任务、测试、阻塞、下一步及已读 B feed SHA |
| 源码任务分支 `docs/collaboration/account-b/latest.md` | B | B 用于发布的报告；包括认领或当前职责、运行结果和占用 |
| 当前负责人发布源码的 `docs/STATUS.md` | 当前集成负责人 | 唯一任务台账；MUS-067-B 有效认领后指向 B 源码，A 版本留作移交快照 |
| A 发布源码的 `docs/collaboration/tasks/account-b.json` | A | A 发出的任务或移交授权、修订号、准确基线及任务卡路径 |
| `docs/collaboration/tasks/MUS-067-B.md` | A | 本次开发接管的授权、启动方式、待办和验收 |
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
# 先读两份报告，核对任务授权与认领，再按当前负责人报告中的 source_sha 查阅 STATUS。
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


## 固定领取与角色移交

1. 首次领取从 A `handoff.source_sha` 读取固定任务入口 `docs/collaboration/tasks/account-b.json` 和对应任务卡。B 使用独立环境，缺脚本按 [BOOTSTRAP_B.md](BOOTSTRAP_B.md) 接入。B 以 `task_id` / `assignment_revision` 核对历史；同一授权已认领则从自己的最新发布继续。
2. `assigned` 只表示 A 已派发。B 在自己的 feed 发布 `claimed`、任务和修订、`assignment_source_sha` 与实际 `ack_peer_feed_sha`。普通审核卡从 `reviewed_sha` 开始并回报其准确值；开发移交从任务卡的 `start_ref` 启动，并回报 `base_sha` 与 `active_owner`。MUS-067-B 的 `start_ref` 是发布该卡的源码 SHA。
3. 普通审核时，B 交独立报告，由当时的集成负责人维护台账。MUS-067-B 是角色移交：认领提交同时更新 B 源码中的 `docs/STATUS.md`；此后 B 独立采用自己的 feed 发布任务与结果。后续报告保留 `active_owner: b`、MUS-067-B 授权 ID/修订及认领凭据，使跨任务发布仍可追溯。A 只读，不能用旧快照恢复写入；同步失败记 `blocked`，不根据缓存或时间推定角色已变更。
4. 角色移交不变更 Git 权限、账号凭据或私有文件归属。A 与 B 只写自己的 feed，不擅自推送或合并 `main`。B 可独立创建任务分支和提交 PR；阶段任务完成不改变角色。

这套机制在会话运行时生效，不会自动启动 B 的会话。B 启动后按固定入口领取即可，无需用户搬运任务正文。
