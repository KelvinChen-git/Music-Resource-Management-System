# 账号 A 最新交接

- account：A；日期：2026-10-19 America/Chicago；集成负责人 / STATUS 写入方：A。
- 当前任务：MUS-010 前后端与两账号开发基线；branch `chore/MUS-010-dual-dev-baseline`；base `f15d842344f8df0b251f90d65811206efb589555`。暂停业务扩展，优先服务联通。最终源码 SHA 由成功发布后的 handoff.json 提供。
- status：blocked（实现与单测完成，真实数据库 / 进程重启待补验）。尚未完成最终合并。
- ack_peer_feed_sha：05d4e9fe7c9528923796ef46508cadb05e94bd1b；B source 6e4118cc316e95d2ba0f3c1fc1cf7ae15fecefbc、审核基线 7ab0d39。
- 实现提交：949603fe45e3f90637dd7dc2578e41f80945afb5；本次仅本地提交。
- 发布状态：`python3 scripts/collab.py publish --account a` 实际失败于 git ls-remote（exit 128）；单独确认 `Could not resolve host: github.com`。未进入推送，A 上次远端 feed 仍为 d0a8381 / source 0ba0a96；B 尚未收到本次代码或 ack。网络恢复后在本分支重试同一 publish 命令。

## MUS-010 本轮结果

- Java 显式全部 107 tests、Vue production build、原生基线入口 8 项保护测试通过。前端本轮使用已有 node_modules，未重跑 npm ci；不夸大为独立环境安装通过。
- 新鲜核对 B feed 仍为 05d4e9f；没有新的 B 确认。A/B slot 的 socket bind / connect 在当前受管进程均 Errno 1，服务联通、数据库与直连 / 代理功能实际执行 0。未重新初始化已有库或反复启动崩溃实例。
- 新 `scripts/baseline.py --slot a|b --keep-running` 串联原生数据库 / Java / Vue / 两条 smoke；每账号独立 checkout，普通终端执行后结果保存到 `.local/<slot>/logs/baseline-*/result.json`，可直接读文件，无需用户搬运输出。完整运行分支未验收，不以脚本存在代替通过。
- A 准备本机独立 B worktree Music-Dev-B-MUS010 供代跑，不冒充 B 账号验收。详见 [MUS-010 记录](../../verification/MUS-010.md) 与 [机器汇总](../../verification/MUS-010-results.json)。
- 下一步先获得两个独立环境的真实 result.json，再补 MUS-009 真实事务失败 / 并发与后端进程重启；媒体权限仍为 P1。本轮不向 B feed 写入或创建其报告。

## MUS-009 实现与证据

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
