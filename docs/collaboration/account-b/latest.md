# 账号 B 最新交接

- account: b
- task_id: MUS-013-R1-B
- assignment_revision: 1
- task_status: review_completed
- review_verdict: request_changes
- runtime_supplement: partial_pass / backend_blocked
- owner: B；集成负责人及 STATUS 写入方: A
- branch: `review/MUS-013-B-review-findings`
- base_sha / reviewed_sha: `c100fd6510fe1061396be16973a7560ed2b89e7f`
- comparison_base_sha: `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea`
- assignment_source_sha / supplemental_evidence_source: `d384a8fc66778ba24344f1ef19507db718872623`
- ack_peer_feed_sha: `10503b986617fbd2c83e865c27605cd21c94eba7`
- claim_source_sha: `0f49505b53810634dd18a3a18470dd12d9c6e0b0`
- claim_feed_sha: `c8505d5f753f8daf17d802cf9969100ad9edad41`
- report_path: `docs/reviews/MUS-013-B.md`
- delivery_sha: 由 own handoff.json.source_sha 指定。

## 实际完成与结论

已从 A 固定入口读取派发及任务卡，按新 task_id / revision去重，独立clone从准确审核SHA建分支，先回传claimed并sync核验，再执行增量复核。旧MUS-012-R1-B不重复认领，旧报告不改写。

**原R1 / R2 / R3在本次源码中修复已落实**：旧MusicService不再JPA硬删、createUser新头像insert前拒绝、迁移写入前检查表名/必要列/主键及owner形状；profile仅写name/avatar/updated_at，原整实体回写安全字段路径已关闭。A修复后运行归档已核对，不将旧漏洞继续记作当前未修复。

**新增P2 / R4**：scripts/review_findings_smoke.py:94–96的finally中，清理用户DELETE失败会直接退出，随后临时管理员降权完全不被尝试。B对实际run函数替换HTTP/SQL传输并注入故障，确认只有提升和失败DELETE两次SQL调用，没有role='USER'；无真实数据库/网络操作。request_changes仅针对本卡脚本清理保证，不是因B环境失败，不重开旧三项发现。正文有可独立复制的无网络重现和最小修复建议。

另列profile“旧头像相等时跳过上传行锁、随后仍写avatar”的具体并发交错，属待A并发任务验证的静态风险，未冒称已复现。

## 验证与未执行项

- Python全量：exit0，28 tests，0失败；2.329s。
- Maven默认：exit1，repo.maven.apache.org DNS / Spring Boot3.4.4 parent POM解析失败，实际Java0，未编译；未重复同一失败命令。
- 新迁移/HTTP脚本--help和四脚本py_compile均exit0，仅入口/语法检查。
- 原R3回调重放：同数量换表由首个SELECT拒绝，0写入；V001表名与保护集合一致。
- R4清理故障替身探针：复现未尝试降权，非真库遗留账号观测。
- A的12份修复后原始JSON+旧observe哈希、计数、矩阵与运行源码核对通过；不是B独立HTTP/SQL运行。
- 前端、依赖、SQL未变，本轮不重复安装/构建或套用上轮B的Node6/build通过。diff --check和两路径审计在发布前执行。

环境OpenJDK17.0.20 / Python3.12.14，缺mysql/mysqld/docker；Java317、真实临时库8、HTTP11、144/65及smoke、故障/并发/重启续传均未由B执行。A本机B槽通过不计入账号B执行数量。

## 发布与范围

本次原生publish失败exit1（git push128）；领取已通过GitHub插件顺序发布并sync核验。最终报告继续先发布/核验任务源分支，再快进更新own feed，明确非原子路径。远端交付以handoff.source_sha为准，不声称原生Git认证通过。

仅修改docs/reviews/MUS-013-B.md与本文件；无接口、业务、schema、SQL、依赖锁、A台账/派发/feed或旧B报告变化；无main推送、合并、集成角色移交。数据/模型/索引版本none，无检索质量或性能指标。

## 下一步及占用释放

A同步本轮B feed并记录准确ack，串行更新STATUS；确认旧三项已复核，针对R4做小范围清理修复和无网络异常负例，再派发精确新SHA。并发/恢复继续由A另行协调，不重复全仓审计。

本检查点发布后释放两份B文档活动占用，B仍为唯一写入方，无A实现路径占用。以后每次开始继续按A固定入口/source_sha下account-b.json和任务卡读取；同task_id+revision已完成则等待新任务。无后台轮询或自动唤醒。
