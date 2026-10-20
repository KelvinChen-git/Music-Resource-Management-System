# MUS-014-R1-B：上传当前读修复与故障恢复脚本复核

- task_id MUS-014-R1-B，revision1，owner B，assigned（未替B认领）。
- reviewed_sha `7c973b5d9eac219e289623e7eb6d44eda73cb09d`；comparison_base_sha `d384a8fc66778ba24344f1ef19507db718872623`。
- 分支 `review/MUS-014-B-upload-recovery`；只允许写 `docs/reviews/MUS-014-B.md` 和 `docs/collaboration/account-b/latest.md`。

前任务MUS-013-R1-B由B完成request_changes（a6474f4），原R1/R2/R3/profile写列已关闭，R4后续由用户授权B实施1534e4d。A已核对声明哈希、原字节导入两文件至1b0eb59并独立验证Python39/HTTP11。新任务复核集成和新上传修复，不重复旧任务，也不将B自行交付作为集成批准。

按当前A handoff.source_sha读取固定入口与本卡；先核对自己的同task_id+revision状态，未认领则回传claimed与实际ack_peer_feed_sha、assignment_source_sha。完成回传review_completed、准确reviewed_sha、approve/request_changes/blocked、自身实际运行与缺口，释放占用。当前卡派发不代表B已收到或批准。

## 复核重点

1. 实际失败证据：c100fd6业务版本12行/12不同索引，持久计数10而API12；A未直接修计数。检查身份查询建立RR快照后等父锁的交错，以及新FOR UPDATE分片当前读是否覆盖重复判断/持久计数/合并输入。调用必须在父上传锁和事务内；只读接口不改。不要把mock视为多连接实证。
2. B清理候选两个文件哈希必须保持声明一致；异常时独立尝试删除/降权，不掩盖原异常、不在清理失败返回passed。A没有改写B报告。
3. upload_fault_smoke只能在validate隔离slot中新合成owner上注入；MySQL CHECK按file_id或核验唯一filename+owner限制到本fixture。名称白名单、固定表名、每步清理和最后核对、失败保留注册文件；不改权限/全局配置、不触碰既有约束。未模拟DB整体中断/commit ACK丢失。
4. baseline只能终止本次登记子进程组，等待退出并确认端口释放后才能启动替代后端；已停止后端从watchlist移除。重启证明与checkpoint哈希/slot/checkout/时间和不同PID一致；无证明resume必须拒绝。不能把concurrency phase当重启。
5. prepare5、resume11、fault18的真实检查数与passed门槛一致；失败私有状态不能覆盖，JWT不得进入报告。检查并发12上传请求及2合并、持久计数与唯一行及字节校验。

## 证据边界与交付

A Java317/Python45通过；旧服务fault18、B清理HTTP11通过；新Java真实并发回归及跨JVM续传待普通终端新baseline，不冒充通过。最新补证从当前handoff.source_sha下MUS-014报告读取，不因文档补证重复认领。

可在自身隔离环境运行Python/Java或真库；缺少环境则明确实际数量与blocked，不复制A数字。保留现有B未提交工作，不reset/clean/stash覆盖。业务源码/schema/依赖锁/A文档/任务卡不在B写范围，发现交A处理。提交后 `python3 scripts/collab.py publish --account b`，A直接sync；无后台唤醒、无需用户复制报告正文。main合并仍由用户决定。
