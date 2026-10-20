# 账号 A 最新交接

- account A；2026-10-19 America/Chicago；集成负责人 / STATUS 写入方 A。
- task MUS-013 B审核发现修复；branch `fix/MUS-013-b-review-findings`；base `6a29de4cab2da6ac149b816165b5f058612bd133`；status review：两套本机修复后真实运行通过，B增量复核待完成。
- ack_peer_feed_sha: `31b564b7cce09994ec661c48b7544964ebabb052`；B source `21d002c7592f21a81b8fc715bdc245ad1ae3ee6c`，reviewed_sha d7c9faa，MUS-012-R1-B revision1已主动claimed并review_completed，verdict request_changes。A接受发现，不代写B报告或批准。
- B独立Python22 / Node6 / build通过，Java0（Maven依赖DNS阻塞）、无独立MySQL/HTTP。A本机双槽旧308/144/65结果不算B执行，也不能覆盖其发现。

## 当前修复与证据

R1旧DELETE /music/{id}已停用，有效当前账号410，匿名/失效401、锁定403，MusicService不再JPA硬删；保留标准软删除。R2 createUser重新核验当前管理员并在insert前400拒绝非空avatar，空白归一NULL。profile改为仅写可编辑列，避免完整实体回写role/is_locked/password。

R3迁移在DDL/版本登记前验证准确11表集合、file_upload必要列/主键，owner列NULL默认/nullable/非生成、索引列序/非唯一/BTREE；SQL V001/V002不改、不回填。加严检查对现有A V002只读复核通过。

Java **317 / 0 failures / errors / skipped**，Python **28项通过**（baseline9 / collab9 / migration10）。修复前R1/R2在旧普通终端服务用合成数据实测：他人旧DELETE204后主记录0、原始下载200且重绑定成功；createUser登记他人图片后匿名200。测试绕过账号已删除、资源引用恢复并软删除、临时管理员finally降权。

验证正文 [MUS-013](../../verification/MUS-013.md)、机器汇总 [results](../../verification/MUS-013-results.json)、旧服务真实复现 [JSON](../../verification/MUS-013-a-before-http.json)。这是旧漏洞实证，不是修复后通过。

## 修复后真实运行通过

普通终端A run baseline-20261019-213038-91461 / sourceda060d5，本机B run baseline-20261019-213013-91055 / sourcec100fd6，均passed；仅8份文档不同，运行源码相同。两套各317 Java / Vue build、8项独立临时库迁移保护、直连和代理各13功能+4安全、媒体144组合+8附加、上传65项、B发现修复后HTTP11项通过。

R1两套均旧删除410、资源行1、raw404，软删除后引用保留且重绑定拒绝；R2两套均createUser400、插入行0、匿名图片401。原始JSON与baseline内嵌汇总一致，媒体元组无重复且状态正确；新后端日志无SQLSyntaxErrorException / BindingException / CommunicationsException。

12份原始JSON及 [真实运行汇总](../../verification/MUS-013-live-results.json) 已归档，A已直接读取，无需搬运。新服务保持运行，本轮无需重启。历史受管进程网络/初始化阻塞不是本轮普通终端验收状态。

## B任务与后续

MUS-012-R1-B已完成request_changes。新派发MUS-013-R1-B revision1，owner B，status assigned未认领。固定入口 `docs/collaboration/tasks/account-b.json`，task_card_path `docs/collaboration/tasks/MUS-013-R1-B.md`；按本handoff.source_sha读取，审核对象固定 `c100fd6510fe1061396be16973a7560ed2b89e7f`，比较d7c9faa。

B分支 `review/MUS-013-B-review-findings`，仅允许 `docs/reviews/MUS-013-B.md` 与 own latest；先发布claimed，再增量复核R1/R2/R3/profile字段更新及新脚本隔离。修复后真实运行证据已补齐，B从当前A handoff.source_sha读取补充资料；独立静态结论与自身运行缺口分开。不重复旧任务，不冒充B已收到或批准。

实现c100fd6已提交，本机B源码已同步，两套服务已重启并完成验收。最终远端source以成功publish的handoff.json为准。

本轮因审核阻断优先修复，事务故障/并发/重启恢复顺延。未知legacy归属、物理清理、公开discovery、main合并仍未完成。B两份原文只读，schema SQL和依赖锁不改。
