# MUS-013-R1-B：独立审核发现的增量复核

| 字段 | 值 |
|---|---|
| task_id / revision | MUS-013-R1-B / 1 |
| owner / 派发状态 | B / assigned，等待B主动确认 |
| reviewed_sha / 分支基线 | `c100fd6510fe1061396be16973a7560ed2b89e7f` |
| 代码比较起点 | `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea` |
| B任务分支 | `review/MUS-013-B-review-findings` |
| 允许交付路径 | `docs/reviews/MUS-013-B.md`、`docs/collaboration/account-b/latest.md` |

## 任务与输入

前任务MUS-012-R1-B revision1已由B完成request_changes，交付source21d002c7592f21a81b8fc715bdc245ad1ae3ee6c / feed31b564b7cce09994ec661c48b7544964ebabb052。A接受并处理R1/R2/R3及profile整实体回写风险；这张新卡复核修复，不要求重做全部MUS-011/012审计。

按当前A handoff.source_sha读取固定派发入口和本卡，审核对象始终是上述c100fd6。先检查自己的B feed有无同task_id+revision已claimed/completed；新卡先回传claimed，再执行，完成后回传review_completed与approve/request_changes/blocked。包含assignment_source_sha、实际ack_peer_feed_sha、reviewed_sha、实际运行数、阻塞、报告路径与占用释放。A文档更新本身不触发重复领取。

## 复核要求

1. **R1**：MusicService不再调用JPA硬删；旧DELETE /music/{id}对有效当前账号410，匿名/失效401、锁定403。标准软删除仍保留引用；检查是否仍可通过该旧入口使rejected/deleted原始文件重新变orphan或重新绑定。
2. **R2**：管理员createUser重新核验当前账号，非空avatar在insert前拒绝，空白归一NULL；目标新账号不会因管理员已知路径而取得其他人的头像引用。确认错误透传与正常无头像创建兼容。
3. **R3**：迁移在任何DDL/版本登记前检查准确表名集合、必要上传列/主键；owner列NULL默认/nullable/非生成及索引列序/非唯一/BTREE。审查同数量换表、缺列、登记中断重试、幂等及异常结构不写入；V001/V002 SQL必须未变。
4. **profile风险**：仅更新name/avatar/updated_at；不把旧role/is_locked/password等写回。测试验证的是SQL写列边界，不冒称真实并发已跑；如发现剩余交错风险请具体列出。
5. 审查新脚本隔离：review_findings_smoke只操作合成账号/资源，observe与verify明确区分，清理绕过账号及临时管理员；migration_guard_probe只启动自己的全新datadir/唯一schema/Unix socket、禁用网络，不连接既有库、只终止自身子进程。baseline新增检查的passed条件必须与脚本真实检查数一致。

## 当前证据与未执行项

- A旧普通终端服务已真实复现R1：他人旧DELETE204、主记录0、raw200、再次绑定成功；R2：createUser插入头像后图片匿名200。原始JSON与说明见 `docs/verification/MUS-013*`。这不是修复后的通过证据。
- Java317、Python28通过；前端/依赖未改。现有A V002加严只读检查通过。
- 当前受管环境中新Java连接限制未反复尝试；独立临时mysqld初始化失败。因此修复后11项HTTP、8项临时库迁移探针仍未通过，A将通过普通终端基线补齐。若B完成前A又发布同实现的运行证据，请按A新handoff.source_sha读取补充资料，仍审核c100fd6，不重复领取。
- B可运行Python测试；Java环境若仍缺依赖/网络则明确blocked与实际0，避免反复相同失败。前端未变无需重新安装/升级依赖。拥有隔离环境时可运行脚本verify和独立迁移探针；否则完成静态审核并单列运行缺口，不复制A数字。

## 交付边界

只写新B审核正文和own latest；旧 `docs/reviews/MUS-012-B.md` 为历史输入，不改写，不修改业务源码、schema、契约、A台账/派发卡/依赖锁。发现继续交A修复，主分支最终合并由用户决定。

从准确审核基线创建/继续B任务分支，保留未提交工作，不reset/clean/stash/覆盖。提交明确允许文件后运行 `python3 scripts/collab.py publish --account b`；发布阻塞如实记录，原子脚本失败和备用顺序发布要区分。A会直接sync读取B结果，无需用户搬运正文。本协议无后台唤醒。
