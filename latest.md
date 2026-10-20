# 账号 B 最新交接

- task_id / assignment_revision：MUS-017-R1-B / 1；owner B；status review_completed；verdict approve_with_scope_limits。
- source_branch：review/MUS-017-B-admin-avatar-null。
- reviewed_sha：`f351b0e2030e5411b6f530ca039c694d4ca091d3`。
- comparison_base_sha：`d443966148336b719cebdb041ea175dfbbfdc500`。
- assignment_source_sha：`d34f282a499b3e93c94f90c83c38d35dcb21ca3a`。
- ack_peer_feed_sha：`35c357212f6ee12a255dae934d43ac8bf84768c0`；结束前sync仍一致。
- claim source/feed：`067f6c3d6517da0852a10d6396fdc23161102525` / `0748515936eb5cb41446279acc29e52725781c1e`。
- 报告：docs/reviews/MUS-017-B.md。

本卡有效管理员请求的null/缺字段保留、空串清空、非空同值/新头像校验与局部更新通过。MUS-015原C1（avatar:null回显清空而库保留）已在准确新源真HTTP/SQL关闭。仅交付两B报告，无业务/接口/schema/依赖/总台账变化，不合并main、不触碰演示音频或旧服务。

独立B命令与结果：比较基线仅换目标测试，`python3 .local/b/maven/run.py --with-test-agent -o -Dtest=UploadOwnershipHttpTest test`，55项/3预期失败/0错误跳过；目标准确SHA新临时clone的私有RuntimeBaseline执行`sh ./mvnw -B -ntp -o test`（settings/cache/现有agent适配），Java323全通过。首轮baseline-20261020-154029-217后续空对象请求断言失败，整命令exit1/blocked，已完成业务1项，未伪装全通过。保留后续重试：`python3 .local/b/runtime/run_mus017.py`，run baseline-20261020-154132-16，exit0/status review_findings，23项预期业务通过+1项E1；复用已通过Java323/旧55证据，未重复执行。

真库23项包括响应/SQLnull和省略保留、空串清空后可删、合法同值/新头像、显式列/路径目标、保护列与body userid忽略、两入口拒绝他人/已删/未完成/NULL owner、非管理员拒绝；受控SQL/HTTP证明改名不覆盖另一连接已改头像/邮箱/角色/锁/密码/原因，上传锁覆盖引用写入，同值旧头像删后拒绝。performance_schema直接记录同事务上传X锁GRANTED及用户写WAITING；未观察DELETE等待，不宣称三正常HTTP参与者竞争。

新增单列观察：E1/P3 `{}`请求在既有@JsonIdentityInfo反序列化时HTTP200/业务500、库不变；正常省略avatar改名及显式null通过。E2/P2是其他既有锁定/密码入口完整实体updateById的静态旧快照回写风险，未做其多连接复现。本卡批准不外推E1/E2，详见报告位置/影响/建议；请A分别协调后续，不由B顺手改源码。

环境：独立新clone/slot B新库/MySQL8.0.41/JDK17，私有工具路径、Unix socket转loopback TCP、每进程代理settings，未改业务SQL/断言。两次自身进程及SQL客户端停止，3308/8081释放。私有原始证据未提交，Java日志hash `3f3aaf67d25fd62bd83a5ef0c615108a6cc2de5ad2b777c0775a390348434b5a`；最后原始result `c02cabb36721ec57ece2fb71e2b21dac5ea67ab0a648060e648beb83ac526434`；汇总证据 `5b04b59e142408134c316dff5d30d48a32f34f7f8f320812b521f32595b7c3ee`，A不能声称重算未交付原始文件。

未执行：无关Python/前端重复构建、MUS-016独立审核、其他用户入口并发、三HTTP时序、整库中断/ACK丢失/GC/生产/检索质量。数据仅合成账号与PNG，模型/索引无变化。两报告占用已释放。下一步A接收批准并决定后续任务，B继续从固定入口领取，不重复旧卡。

发布：原生Git写凭据仍未配置，采用已授权GitHub插件先源码分支后B feed的顺序备用路径，非原子；提交对象/两文件feed/hash将回读核验，最终交付SHA见handoff.source_sha。发布与A接收/合并区分。
