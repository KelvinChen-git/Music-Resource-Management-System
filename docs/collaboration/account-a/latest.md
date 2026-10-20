# 账号 A 最新交接

- account A；2026-10-19 America/Chicago；集成负责人 / STATUS 写入方 A。
- task MUS-013 B审核发现修复；branch `fix/MUS-013-b-review-findings`；base `6a29de4cab2da6ac149b816165b5f058612bd133`；status review，修复后真实运行待补。
- ack_peer_feed_sha: `31b564b7cce09994ec661c48b7544964ebabb052`；B source `21d002c7592f21a81b8fc715bdc245ad1ae3ee6c`，reviewed_sha d7c9faa，MUS-012-R1-B revision1已主动claimed并review_completed，verdict request_changes。A接受发现，不代写B报告或批准。
- B独立Python22 / Node6 / build通过，Java0（Maven依赖DNS阻塞）、无独立MySQL/HTTP。A本机双槽旧308/144/65结果不算B执行，也不能覆盖其发现。

## 当前修复与证据

R1旧DELETE /music/{id}已停用，有效当前账号410，匿名/失效401、锁定403，MusicService不再JPA硬删；保留标准软删除。R2 createUser重新核验当前管理员并在insert前400拒绝非空avatar，空白归一NULL。profile改为仅写可编辑列，避免完整实体回写role/is_locked/password。

R3迁移在DDL/版本登记前验证准确11表集合、file_upload必要列/主键，owner列NULL默认/nullable/非生成、索引列序/非唯一/BTREE；SQL V001/V002不改、不回填。加严检查对现有A V002只读复核通过。

Java **317 / 0 failures / errors / skipped**，Python **28项通过**（baseline9 / collab9 / migration10）。R1/R2在旧普通终端服务用合成数据实测：他人旧DELETE204后主记录0、原始下载200且重绑定成功；createUser登记他人图片后匿名200。测试绕过账号已删除、资源引用恢复并软删除、临时管理员finally降权。

验证正文 [MUS-013](../../verification/MUS-013.md)、机器汇总 [results](../../verification/MUS-013-results.json)、旧服务真实复现 [JSON](../../verification/MUS-013-a-before-http.json)。这是旧漏洞实证，不是修复后通过。

## 当前运行边界

原两套普通终端仍运行MUS-012，新Java受管启动限制没有反复尝试。独立临时MySQL初始化在受管环境失败，未连接现有数据库；未知结构真库探针仍blocked。新baseline已自动加入8项独立临时库探针和11项修复后HTTP负例，普通终端A/B各Ctrl+C后在原目录运行 `python3 scripts/baseline.py --slot a --migrate-upload-ownership --keep-running` / `--slot b`。

原Java/Vue/媒体/上传回归照常执行，结果自动存各slot日志，A直接读取；不要把Maven构建成功当应用启动、不要把普通重启当未完成上传恢复。

## B任务与后续

MUS-012-R1-B已完成request_changes。A将在实现提交产生后，按固定 `docs/collaboration/tasks/account-b.json` 派发MUS-013增量复核，要求准确reviewed_sha、独立实际验证和未运行项。不得自行重复旧卡或将待补实跑当批准。

本轮因审核阻断优先修复，事务故障/并发/重启恢复顺延。未知legacy归属、物理清理、公开discovery、main合并仍未完成。B两份原文只读，schema SQL和依赖锁不改。
