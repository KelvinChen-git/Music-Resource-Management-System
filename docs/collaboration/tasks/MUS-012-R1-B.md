# MUS-012-R1-B：媒体与上传所有权独立审核

| 字段 | 值 |
|---|---|
| task_id | MUS-012-R1-B |
| assignment_revision | 1 |
| owner | B |
| 发布状态 | assigned，待 B 主动确认；A 不替 B 认领 |
| reviewed_sha / 审核分支基线 | `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea` |
| 审核输入分支 | `fix/MUS-012-upload-ownership`，审核始终固定上述 SHA |
| B 工作分支 | `review/MUS-012-B-access-ownership` |
| 代码比较起点 | `436908938989ba4d331b90e2795a8a5f3f702bb2`，包含 MUS-011 与 MUS-012 |
| 允许交付路径 | `docs/reviews/MUS-012-B.md`、`docs/collaboration/account-b/latest.md` |

## 领取和防重复

1. 从远端 `collab/account-a` 获取 `handoff.json` 和 `latest.md`，成功 sync 后按 handoff.source_sha 读取 `docs/collaboration/tasks/account-b.json` 与本卡。A feed 的 SHA、任务卡来源 SHA 与 reviewed_sha 分别记录，不把分支最新 HEAD 当审核对象。
2. 检查自己的 B feed 是否已确认 / 完成本 task_id + assignment_revision。已领取则继续原任务，已完成则只汇报等待新任务；不能因 A feed 更新报告就重复领取。
3. 保留已有未提交工作。工作区干净且不存在同名任务分支时，从 reviewed_sha 创建上述 B 分支；已有同名分支则核对其基线并继续，不 reset / clean / stash / 覆盖。B 继续使用自己的独立 clone，不能使用 A 的 macOS 路径或占用 A 的运行端口 / 数据库。
4. 先在 B latest 发布 `task_status: claimed`，包含 task_id、assignment_revision、reviewed_sha、assignment_source_sha、实际读取的 ack_peer_feed_sha、允许路径及环境阻塞。只提交自己的报告路径，执行 `python3 scripts/collab.py publish --account b`。发布成功后才称确认已回传；受阻如实记录。
5. 当前任务为审核，不直接修改业务代码、契约、schema、依赖锁或 A 台账。发现需要修复的问题写入 B 审核报告交 A 处理；需要扩大范围时先说明具体文件及理由。

## 审核范围

先读目标提交中的 CONTRACTS A4 / A5、MUS-011 / MUS-012 验证正文、机器汇总与原始 JSON，再核对源码、SQL 与测试。A 的运行证据是输入，不是 B 的独立运行结果。

- 三个媒体入口、ZIP、当前数据库账号锁定 / 删除 / 降权、审核与软删除、GET / HEAD / Range、播放计数、缓存、受控真实路径与头像公开例外。
- create / 普通 upload 的 owner 是否只能由服务端赋值；MD5 check / list / detail / status / missing-chunks 是否隔离；chunk / merge / delete / metadata 首次解析和绑定是否拒绝他人、管理员越权、NULL owner 旧记录及失效账号。
- 上传行锁、元数据 / 头像绑定与删除的引用检查是否一致；审查实际事务边界及潜在竞态，区分静态风险、可复现实证与尚未验证的假设。
- V002 加列 / 索引、空库初始化、已有 V001 显式迁移、版本登记中断重试、未知结构拒绝；确认没有自动推断 owner、覆写 / 重建旧表或误把 migration 成功当 HTTP 验收。
- 前端 JWT 媒体 fetch / Blob 下载与原流程兼容性；头像绑定是否可能公开他人上传；被音乐 / 头像引用时拒绝删除、逻辑删除保留字节的边界。
- 测试是否覆盖实际授权路径，而不是只验证 mock 设置；报告与源码提交是否对应。无需重新做全仓模型 / 检索审计或升级依赖。

## 验证与证据要求

- 先核对环境 / JDK 17 / Maven 与 Node。能运行时执行目标提交的默认 Java 测试、`python3 -m unittest discover -s scripts -p 'test_*.py'`、`node --test web/src/utils/media.test.js`。Java 沿用项目已有 wrapper / 参数；必要 Byte Buddy agent 方案见验证正文，不照抄 A 机器绝对路径。
- 有自己的可用隔离运行环境时，可执行 slot B baseline / 媒体与上传回归，保留原始结果与源码 SHA。配置缺失才 setup，不覆盖已有凭据；旧库迁移只使用显式选项，不对未知 / 生产库执行。新起的服务由 B 自行管理，禁止清理 A 或他人的进程 / 数据。
- 缺 JDK / 依赖 / 数据库 / 网络时记录一次明确失败、环境与错误，继续静态审查，不反复执行同一失败命令。B 实际执行数必须独立列出；未运行标 not_run / blocked，不能直接复制 A 的 308 / 144 / 65 为 B 测试通过。
- A 已实跑两套本机各 Java308、直连与代理各13功能+4安全、媒体144+8、上传65；本机 B 槽由 A 配置与读取，不能算 B 账号独立确认。事务故障、并发与跨进程续传仍未完成，禁止由普通重启推断通过。

## 交付与验收

正文只写 `docs/reviews/MUS-012-B.md`，索引写 B latest。每个发现给出优先级、目标 SHA、文件和位置、触发条件 / 复现步骤、影响与修复建议；不能复现的风险明确标注推断。没有发现也必须写审核范围与未验证项。

B latest 最少包含：

- account: b；task_id: MUS-012-R1-B；assignment_revision: 1。
- task_status: claimed / review_completed / blocked；reviewed_sha 固定为本卡 SHA。
- review_verdict: approve / request_changes / blocked；运行补证的状态单列。
- assignment_source_sha、ack_peer_feed_sha、审核报告路径、实际命令 / 计数 / 结果、剩余阻塞和释放的文件占用。

完成后提交上述允许路径并 `python3 scripts/collab.py publish --account b`。B 的最终交付以其 own feed 的 source_sha 为准；不需用户复制正文给 A。A 下次 sync 后读取并更新 STATUS，再发布修复 / 下一张任务卡。最终合并仍由用户决定。
