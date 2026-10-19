# 账号 A 最新交接

- account：A；日期：2026-10-19 America/Chicago；集成负责人 / STATUS 写入方：A。
- 当前任务：MUS-009 上传完整性；branch `fix/MUS-009-upload-integrity`；base `83b94029412d12b52e3fd1e3a0938357b1bde782`。最终源码 SHA 由发布后的 handoff.json 提供。
- status：blocked（实现与单测完成，真实数据库 / 进程重启待补验）。尚未完成最终合并。
- ack_peer_feed_sha：05d4e9fe7c9528923796ef46508cadb05e94bd1b；B source 6e4118cc316e95d2ba0f3c1fc1cf7ae15fecefbc、审核基线 7ab0d39。
- 发布状态：本地检查点；A 上次远端 feed 为 d0a8381 / source 0ba0a96。本次将尝试 publish；在成功前不声称 B 已收到新代码或 ack。

## 实现与证据

- 删除即时 save + 缓存批量重写、未注册 insertBatchSomeColumn；标准 CRUD 单一同步持久化。新服务使用事务与上传行锁，分片和计数一起写入，持久化失败无成功 ACK。
- 按实际字节校验分片 / 整文件 MD5 与大小；相同内容重试不重复计数，冲突不覆盖，可原内容修复损坏分片；完整连续分片才能合并，完成事务提交后清理来源，重复合并复用原路径。公共接口与 envelope 保留，CONTRACTS A3 已记录。
- 旧基线两项控制器负例均复现 code=200；修复后 clean test 105 通过，补边界后全量 107 通过，0 failures / errors / skipped。新增 2 控制器 + 23 服务测试；mock 回调不等同真实 SQL / 回滚测试。
- MySQL 启动 signal 11；HTTP 回环 Errno 1 Operation not permitted。真实数据库、并发和进程重启验证仍未运行，功能检查执行 0；不能因为单测通过就宣称恢复可靠性已全部验收。
- 证据：[MUS-009 验证](../../verification/MUS-009.md)、[机器汇总](../../verification/MUS-009-results.json)。新两阶段命令：`python3 scripts/upload_integrity_smoke.py --slot a --phase prepare`，人工记录 PID 并重启后端后运行 `--phase resume`。

## 路径与 B 后续审核输入

A 本任务修改上传控制器、新完整性服务、旧缓存 / 批量 mapper 及其测试、新 smoke、README / CONTRACTS / STATUS / A latest / MUS-009 验证文件；未改 schema、依赖锁、B 报告或 B feed。B 两份报告仍仅由 B 写入。

供 B 在收到新 feed 后审核：按 handoff.source_sha 核对事务管理器与 MyBatis 同源事务、FOR UPDATE 并发语义、错误 ACK、完成后清理时序、旧客户端兼容；在可运行的隔离库补真实 SQL、失败回滚、并发重试与进程重启证据。当前未收到 B 接受或新审核，不视为已分配 / 已审核。

## 其余状态

B MUS-001-R1 报告已接收；其 done 只代表报告交付，B 后端执行仍为 0。共享 feed 可直接读取，但 A 连接 push=false / 受管终端 DNS 阻塞，不能把本地 commit 当远端交付。B 通过可写接口顺序发布，不等同双方终端原子推送通过。

P1 媒体匿名入口与一年缓存、上传归属仍待治理，公开 discovery 继续阻断。MUS-002 只有固定 CLAP 合成编码 / 缓存离线可行性；真实许可语料、解码 / 检索效果、索引、线上 API / 界面仍未完成。
