# 账号 B 最新交接

- account: b
- task_id: MUS-012-R1-B
- assignment_revision: 1
- task_status: review_completed
- review_verdict: request_changes
- runtime_supplement: partial_pass / backend_blocked
- owner: B；集成负责人 / STATUS 写入方: A
- branch: `review/MUS-012-B-access-ownership`
- base_sha / reviewed_sha: `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea`
- comparison_base_sha: `436908938989ba4d331b90e2795a8a5f3f702bb2`
- assignment_source_sha: `6a29de4cab2da6ac149b816165b5f058612bd133`
- ack_peer_feed_sha: `c9c291344715a1d86894d8b6016d3983538fd899`
- claim_source_sha: `65a26e6007455f314c15dc7702312ed5ab46ed53`
- claim_feed_sha: `8fad65cca4ca0ce418d5ca9cdcb24d4f549b11f9`
- report_path: `docs/reviews/MUS-012-B.md`
- delivery_sha: 由本 feed 的 handoff.json.source_sha 指定，避免同提交自引用。

## 实际完成

从 A 固定入口读取 handoff / latest，在 source_sha 下读取 account-b.json 与完整任务卡，核对无同 task / revision 的旧领取，独立 clone 从准确 reviewed_sha 建分支。先发布 claimed 并 sync 回读，再审查 MUS-011 / MUS-012 契约 A4 / A5、61 个变更路径及相关旧入口、SQL、测试和 A 的运行归档。完成报告，不直接修改业务实现。

发现详情与复现条件见正文：
1. **P1** 旧 DELETE /music/{id} 通过 JPA 硬删资源、无 owner / 当前账号校验；可抹去 rejected 引用，使 raw 下载走 owner orphan 放行并允许重新绑定。静态调用链结论，待真库 / HTTP 复现；不是把预测状态写作实测。
2. **P2** POST /users 的 createUser 直接插入 avatar，绕过新头像归属检查，已知私有图片路径可被登记为其他新用户的公开头像。需要管理员身份，B 未实跑 HTTP。
3. **P2** 迁移只看表数量 / version，未检查表名集合；实际 migrate 的合成元数据回调接受未知 11 表结构并尝试 ALTER / 登记 V002。该探针不代表真实 MySQL DDL。

另记录 profile 完整实体更新可能覆盖并发锁定 / 降权的静态交错风险，交 A 的并发验证，不冒充已复现故障。

## 验证命令与结果

- python3 -m unittest discover -s scripts -p 'test_*.py'：exit 0，22 项通过。
- node --test web/src/utils/media.test.js：Node 22.23.3，exit 0，6 项通过。
- web/ 下 npm run build：npm 10.9.9，exit 0；5.46s；bundle 警告非阻塞。
- music/ 下 sh ./mvnw -B -ntp test：exit 1，repo.maven.apache.org DNS / Spring Boot 3.4.4 parent POM 解析失败，实际 Java 0 项；未重复相同失败命令。
- slot B 现有配置白名单校验、V001 与比较起点逐字节比对通过；凭据未改。
- A 的 14 份原始 JSON 哈希与归档汇总一致；媒体矩阵元组 / 状态、上传拒绝计数与源码版本核对通过。这些是证据审核，不是 B 独立 HTTP 运行。
- git diff --check 与允许路径检查在发布前执行；日志摘要和 SHA-256 见正文。

OpenJDK 17.0.20 / jdk.compiler 模块存在；Python 3.12.14。缺 mysql / mysqld / docker：真实库迁移 / 事务、HTTP 144 / 65、直连 / 代理 smoke、R1/R2 HTTP 负例、故障 / 并发 / 重启续传、浏览器人工试听均未执行。A 本机 B 槽结果不能计入账号 B 的执行数量。

## 发布与边界

原生脚本 publish 本次实际失败（exit 1，内部 git push exit 128）。领取已通过 GitHub 插件顺序发布并 sync 核验；最终报告沿同一备用路径先发布 / 核验任务源分支，再快进更新 own feed，明确非原子发布。最终远端 source_sha / 报告哈希以 handoff.json 为准；不声称终端 Git 认证或原子推送通过，不要求聊天提供 Token。

仅修改 `docs/reviews/MUS-012-B.md`、`docs/collaboration/account-b/latest.md`；接口变化 none；未改业务代码、schema、依赖锁、A STATUS / 派发卡 / feed。数据 / 模型 / 索引版本 none，未产生检索评测指标；无 main 推送、合并、集成角色移交。

## 下一步与占用释放

A 下次 sync 读取本轮 B feed，在 own latest 记录实际 ack 并串行维护 STATUS；优先处理报告 R1 / R2 的最小修复和真库负例、R3 迁移保护，按准确新 SHA 派发增量复核。没有把运行补证缺失标成产品测试失败，也没有用 A 的通过项代替 B 执行。

本检查点发布后释放两份 B 文档的活动占用，B 继续是唯一写入方；未占用 A 的实现路径。以后每次 B 开始均从 collab/account-a 读取 handoff / latest，按 source_sha 读取 docs/collaboration/tasks/account-b.json 和任务卡；同 task_id + revision 已完成则等待新任务，不重复领取。该约定在会话运行时执行，没有后台轮询或自动唤醒。
