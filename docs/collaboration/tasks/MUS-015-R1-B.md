# MUS-015-R1-B：头像同值请求校验复核

- task_id / revision：MUS-015-R1-B / 1；owner B，assigned未认领。
- reviewed_sha `d9a2a15791da0db4374c5de093a752a5aa202a25`；comparison_base_sha `feb935ad5c7eb4eb8a11065f3d5c18ed2a93dab1`。
- 分支 `review/MUS-015-B-avatar-revalidation`；仅允许写 `docs/reviews/MUS-015-B.md` 和 `docs/collaboration/account-b/latest.md`。

MUS-014-R1-B已完成approve限定范围；A收到B feed8d1ae4ac/source7175ddf1并核对原字节报告和准确SHA。运行补证及私有Linux适配已接收，A不会将旧blocked当当前状态，也不宣称重算B未交付的私有日志。勿重复认领旧卡。

按A handoff.source_sha读取卡和固定入口；先检查自身同task_id/revision有无claimed/completed，首次主动回传claimed、assignment_source_sha、实际ack_peer_feed_sha，再执行。完成回传review_completed和approve/request_changes/blocked、准确reviewed_sha、实际运行/未执行项和释放占用。

## 复核范围

1. UserServiceImpl两个写入口不再依据旧user.avatar==请求avatar跳过requireAvatar。非空avatar必须锁定读取上传并校验目标owner、完成、未删除状态；检查同值请求旧快照/切换/删除/再绑定的静态交错是否被阻断。
2. requireAvatar及两个写方法现有事务/上传锁能否覆盖校验至引用写入；检查删除路径锁顺序与当前读。若发现剩余问题，给出具体时序，区分证据与推断，不声称未跑的真实竞争已解决。
3. 仅名称修改、合法同值、新头像、管理员空值清除兼容；legacy NULL owner、他人/已删除/未完成上传不能因路径相等获准。profile仍仅写可编辑列。管理员旧错误封装HTTP200/业务非200未改，不将业务200当拒绝。
4. 新三项HTTP/mapper测试先在旧代码3失败、修复后Java320全通过；检查测试能拒绝删除上传且不执行用户更新，合法同值确实校验FOR UPDATE。它们是MockMVC，不是多连接真库实证。

输入 docs/verification/MUS-015.md / MUS-015-results.json。没有新Python/前端改动，避免无必要重装依赖。B可用自身已建立隔离环境验证，允许真实fixture/多连接只在本次独立开发库；报告工具/传输适配和原始证据边界。不能操作A本机服务，不能直接修业务源码或改A台账/契约/派发/schema/依赖锁/main。缺环境时单列blocked和实际数字，不复制A数字。

保留B未提交工作，不reset/clean/stash覆盖；仅提交两允许文件后publish --account b，披露原子或备用顺序发布路径。A直接sync接收，无需用户复制正文；固定入口不负责后台唤醒B。
