# MUS-021-R1-B 独立增量审核

## 结论与交接身份

**approve_scoped**：E1 空对象与 E2 六入口专属写列在本卡范围内通过，未发现新的阻断问题。仅批准准确实现提交及下述证据范围；不代表整个用户系统、Sonora 全站、生产部署或 main 合并。

- task / owner：MUS-021-R1-B / B；assignment_revision：1；status：review_completed。
- branch：`review/MUS-021-B-user-update-boundaries`；审核/分支基线 `0f12212123616809ea0a917e43fc11e5f564ab46`。
- comparison_base_sha：`a9655750b6a4a5df07c2d64abd7f809fdd1e5978`。
- assignment_source_sha：`69a3965e88d37d71a0067f263d207f2cb62fe668`。
- ack_peer_feed_sha：`feec5afd7f605d73e8a55114ea794ff4bf4ea4d0`；开始和结束前检查点 sync exit0、双方 fetched，A 未变。
- 主动认领 source `b20ca04ce13de06bb947eb521f5c4341ecfc0c3f` / B feed `12031410a2cced452cd469797e8a13b52d5dfa4f`，先发布、回读再审核。最终交付 SHA 见 handoff.source_sha。
- 修改仅本报告及 `docs/collaboration/account-b/latest.md`；无业务、A 台账/任务卡、接口、schema、依赖锁变化。完成后两报告活动占用释放。

## 静态检查

检查准确 diff、CONTRACTS A10、MUS-021 A 验证/结果 JSON、MUS-017 报告/接收 JSON 与新卡；没有重复 MUS-017/019/020 全面审核。A 导入的 MUS-017-B 与历史 B source `082d243161c5774a96d242a473b17c483a77cc4e` 原文逐字节一致，SHA-256 `4fee2bc5937f82031defd5de499c3551d7518f498a7b3292d7cc857381ae9c44`。

- `UserController.java:180`、`AdminUpdateUserDTO.java:8`：输入限定 name/email/avatar/role，忽略未知列；body userid 不映射，目标继续绑定路径 id；管理员检查保留。没有全局移除 Users 身份注解或改 Jackson/NULL 设置。
- `UserServiceImpl.java:246`、`:266`、`:379`：锁定/解锁按操作列写；两种上锁均显式写 unlock_time=NULL；有原因只在非 null 时写本次原因，解锁保留已有原因/锁时间。
- `UserServiceImpl.java:304`、`:401`、`:482`：三个密码入口只写 password/updated_at，以当前目标 userid 为 WHERE；原确认、旧密码、验证码、编码及成功后 evict 分支保留。
- 核对 POM、web/package-lock.json、AGENTS 相对比较基线不变；未改前端/Python/schema。准确目标 music 树 `8761503685932be8c7ab7bd2ad94e357860ecf3d` 与认领文档提交内完全相同。

## 命令与失败记录

Linux 独立 B clone；私有 Java 17.0.20 启动器、Maven 3.9.9 缓存/当前代理设置、既有 ByteBuddy 1.15.11 测试 agent、原生 MySQL 8.0.41/TCP 适配。MySQL 私有兼容库和禁 Unix socket 的包装只改变运行路径/传输，不改产品 SQL、权限或断言。每次运行新建 `/tmp/music-b-users21-*/checkout` 和空 slot B 库；先配置 ignore 目录。不使用 A 的 8080/5175、账号、曲库或凭据。

| 实际命令/阶段 | 独立结果 |
|---|---|
| `python3 .local/b/maven/run.py --with-test-agent -o clean test` | exit1，离线缓存缺 maven-clean-plugin 3.4.1，测试执行0；旧 target XML 为历史，不计入本次 |
| 比较基线新临时 clone，复制准确实现中的 UserWriteBoundaryTest / UploadOwnershipHttpTest；`python3 .local/b/maven/run.py --with-test-agent -o -Dtest=UserWriteBoundaryTest,UploadOwnershipHttpTest test` | exit1；64项，7 failures/1 error/0 skipped。两空对象与六入口旧实现边界回归；不是旧真库并发覆盖实证 |
| `python3 .local/b/runtime/run_mus021.py`，第一轮 `baseline-20261021-062148-218` | 整命令 exit1/status blocked；其冷编译默认 Java 14类332项通过；5项业务检查完成后，私有探针把匿名 HTTP401 的空 body 当 JSON 解析而停止。仅修探针空 body 处理，不改产品/校验断言；自建进程已停、两端口释放 |
| 同入口最终 `baseline-20261021-062234-10` | exit0/status passed；准确目标的全新 checkout 冷编译 `sh ./mvnw -B -ntp -o test`（适配器注入私有 settings/cache/agent），14类332项，0失败/错误/跳过；24项增量业务通过 |
| `git diff --check`、精确源码/报告字节/JSON/哈希核验 | 通过；最终发布后另回读 source/feed |

两轮冷编译来自不同的新原生临时 checkout，第二轮用于修正探针后的干净真库验收；不把两轮332相加。B没有新跑显式 `-Dtest='*Test'` 对照，A 的该结果不冒充 B 执行。既有 Druid POM 诊断及故障测试预期 ERROR 日志保留，以退出码和 Surefire 汇总判定。

## 真实业务检查：24 项

**E1：11 项。** 对 `{}`、四字段全 null、仅未知字段、伪造 body userid/密码/锁/验证/时间等保护字段，核对 HTTP envelope、目标 userid 和独立 SQL 全字段快照；前三者业务字段保持，只变 updated_at，保护字段不写入，另一个账号未变。普通用户空对象为 HTTP200/business403，匿名为 HTTP401/空 body。有效同值头像、新自有头像、空串清空、四正常字段编辑均通过；非空同路径对应上传已被 fixture 标记 deleted 后，返回业务500且用户行不变，仍有原上传校验。图片由两次正常自有 HTTP 上传建立，不是伪造上传所有权。

**E2：7 次受控交错。** 六个正式入口均走正常 HTTP；额外 null 原因分支使用真实 Spring 事务代理服务调用（HTTP LockUserDTO 会拒绝 null 原因，不绕过该校验）。每次 fixture SQL 连接先锁住目标 users 主键；正常调用读旧快照，到 UPDATE 等待时，通过独立 root 观察连接直接读取 performance_schema.data_locks + threads.PROCESSLIST_INFO，确认目标 PRIMARY 记录 WAITING 和下表精确 SET 列。随后持锁连接把头像/邮箱/姓名/角色/验证状态/密码/锁状态与原因/各时间等改为不同并发值并提交，待请求完成后用独立 SQL 核对所有非本操作列、另一个目标账号及本操作值。

| 操作/真实入口 | 观察到的精确 SET 列（均含 updated_at） | 等待事务 |
|---|---|---|
| lockUser / PUT users/{id}/lock | is_locked, lock_time, unlock_time, updated_at | 1489 |
| unlockUser / PUT users/{id}/unlock | is_locked, unlock_time, updated_at | 1495 |
| lockUserWithReason / PUT users/{id}/lock-with-reason | is_locked, lock_reason, lock_time, unlock_time, updated_at | 1501 |
| lockUserWithReason(id,null) / 私有真实 Spring 服务 | is_locked, lock_time, unlock_time, updated_at | 1507 |
| changePassword / POST auth/change-password | password, updated_at | 1513 |
| resetUserPassword / PUT users/{id}/reset-password | password, updated_at | 1519 |
| resetPassword / POST auth/reset-password | password, updated_at | 1525 |

锁定后的 unlock_time 确为 SQL NULL；普通锁/空原因保留并发原因，指定原因写本次值，解锁保留并发 lock_reason/lock_time。三种密码结果均经实际 PasswordEncoder BCrypt matches 验证，其他最新安全列保持。code reset 成功后原邮箱 code 已从实际 cache 失效，虽然 fixture 在 UPDATE 等待期间改变了邮箱，也仍绑定先前查询到的目标 userid。没有仅凭最终 avatar 推断所有列安全。

**负例6项。** 修改密码确认不匹配、旧密码错误；重置密码确认不匹配、验证码错误、验证码缺失：独立 SQL 均不变，已有 code 不失效。第六项让单独无上传的合成 victim 的正常 code-reset 请求读到用户、UPDATE 等待（事务1536）后，由 fixture 删除该 victim 行并提交，实际 mapper 返回零影响行，HTTP200/business500，cache 中 code 仍保留；这是 affected-rows=0 分支，不是数据库中断/SQL异常/提交失败测试。

24 = E1 11 + E2 7 + guard 6；其中23项通过HTTP入口、1项为null原因服务分支。缓存设置/查询和 BCrypt 核验是这些场景的辅助 fixture，不另算业务项。两次失败命令和首轮5项不得与最终24相加为更多成功项。

## fixture、证据与限制

数据版本为本轮 B21 合成 fixture：4个注册/登录合成账号（含独立删除 victim），2次自有 PNG 上传，新库 V001/V002（初始化SQL SHA-256 `e2c4b01537dabdf01354faabf4876821cdae7de7cc549809ee1a60708c99146e`）；不是 A 的真实音乐。模型/checkpoint/索引无新增或变更。

私有 `B21Main.java` 单独编译到 `.local/b/private-classes`，以准确 target/classes 和 Maven 实际测试类路径启动原 MusicApplication；未改产品类/SQL/HTTP路由/鉴权。它仅在新临时库所属进程读取 mode600 文件 IPC，取得实际 CacheManager 设置合成 code、查询存在性、核验 BCrypt，以及调用额外 nullReason 服务分支。正式 code-reset 仍经原 HTTP controller 与真实事务/mapper；从未调用 forgot-password 或发送邮件。fixture 线程与请求线程/SQL 连接明确区分；这不是三个正常 HTTP 参与者竞争，也不把 A wrapper harness 当真库证据。

原始日志、私有工具、IPC、数据库未交付/提交，A 不能声称自行重算其原始哈希。可核对的报告文字与下列原始证据指纹分别对待；文件位于 B 私有 `.local/b/review-evidence/MUS-021-R1-B/`。

| 工件 | SHA-256 |
|---|---|
| java-default.log（首次缺clean插件） | a12221c7b2cf8da4ea88d5003aad8a043e02741a2cfcfd093dcea9e48a7dc761 |
| before-regression.log | 7e4b2b18d10db2dba00e2bf6d0c8ad539778ee3137ca4645b8bd74bac9c5a60f |
| before-regression.json | 63778a41288c807720d6fb4000afe0c504e8da1944e4d96d8454e12c2d470a44 |
| 首轮 blocked result.json | 5fe52699f84d5d0333591a79100ae138c92dd88107caa0df9ac311fd8c223888 |
| 首轮 Java 默认日志 | 4682845777908d7459b5d0489247340117b8e25c4b6a2be60e2815d7a143174c |
| 最终 Java 默认日志 | 115a8e959a95fbee697cbf82647aadd4405c6aa1aac006c65c2af98461dbf724 |
| 最终 result.json | 59a9543c4e4b96f939fb01d81bc843f50f4d6fa99f669ad0e0d79f3951f16ee2 |
| baseline-20261021-062234-10-summary.json | feb9352cdddfd988b9801d901388eb997a61bf73d11a4715f07830f72c156848 |
| verified-review-evidence.json | fa855aa0527bedff643fd06bd10575cc329626f991e73605736dbf09dcf99cec |
| 私有运行器 run_mus021.py | 6c884fe707dec660f6bf83a6246b965c74af385f3959de39d7e92081239f6810 |
| 私有探针 mus021_native.py | 1b370e2692215452a0d1ecbf87e0c9bb3934952951a722ba7359eed53a8e07b9 |
| 私有同JVM fixture B21Main.java | 87b3d0471e606a3a41a55deac32a6863b0f8ff4817f7448ac4e010dc89f01984 |

所有本次登记的 MySQL/Spring 子进程停止，合成管理员已降权，3308/8081 关闭；无 A 服务停止或数据迁移。B报告文件占用释放，下一步由 A 接收本卡限定批准并串行更新台账/派发。MUS-016 独立导入器审核仍另列。

未验证权限撤销竞争、同密码并发请求/验证码原子消费、数据库整库中断/commit ACK丢失、生产和整站写操作；未新跑 UI/前端构建/Python/导入器或重启升级现有演示。未承诺所有未提交字段响应是并发最新快照；本卡验证持久写列边界。

发布沿用已授权 GitHub 插件，先源码任务分支再 collab/account-b，顺序非原子，未配置新原生 Git 写凭据。最终 source/feed 回读成功后才报告已发布；发布不等于 A 已接收或 main 已合并。
