# MUS-014-R1-B 独立审核

## 结论与准确对象

- task_id: MUS-014-R1-B；assignment_revision: 1；owner: B
- task_status: review_completed；review_verdict: approve（限定本任务增量及下述验证边界）
- reviewed_sha / base_sha: `7c973b5d9eac219e289623e7eb6d44eda73cb09d`
- comparison_base_sha: `d384a8fc66778ba24344f1ef19507db718872623`
- assignment_source_sha / 补证来源: `a433e2bd6a72a6f31cc6b608220f5dcf87bd8a54`
- ack_peer_feed_sha: `0093ae4030d35b2b7a2dbdc97f431ed95dff2e78`
- branch: `review/MUS-014-B-upload-recovery`
- claim_source_sha: `b56acccd75647bb9440984297e986e6ec1080162`
- claim_feed_sha: `0405107fa6045f3b7f35d6b02c3faf52a4832225`
- 最终delivery_sha由本次B handoff.json.source_sha给出，避免同提交自引用。

在本卡五项范围内未发现需退回修改的问题。B已独立执行Java317、Python45及9项真实Python子进程/TCP保护检查。MySQL/应用HTTP/跨JVM上传由A本机两槽提供归档，B只核对这些已提交JSON与源码的一致性，没有将其算作B实跑。approve不代表main已合并、生产验收或公开discovery可以开放。

## 审核范围与依据

### 父锁、RR快照和当前读

核对UploadAccessService.requireOwnedLocked、UploadIntegrityService.uploadChunk / merge、FileChunkServiceImpl与唯一索引。requireViewer普通查询可能先建立RR快照，随后父行FOR UPDATE即使等待另一事务提交，也不会更新普通快照；因此旧分片普通查询可读到旧行集合。修复前归档file44的12行/12索引/持久计数10/API12与这个原因相符，属于A实证，B未多连接重现旧故障。

新FileChunkServiceImpl.java:27使用固定FOR UPDATE、fileId条件和索引排序。UploadIntegrityService.java:61、96、120分别在父上传锁之后、@Transactional(rollbackFor=Exception.class)方法内使用当前读，覆盖重复判断、持久计数和合并输入。查遍调用点仅此三处；只读进度仍用旧普通查询。file_chunk的(file_id,chunk_index)唯一索引保留，无schema修改。

Java单测仍使用mock，不能单独证明真实InnoDB锁/隔离语义；A补证的两槽新版本计数与并发结果另列，不混淆证据类型。

### R4原字节集成

本基线两文件与B交付1534e4d完全相同：
- scripts/review_findings_smoke.py SHA256: 9f7aa781b749615e2ddd201d97f8b9b062486e54fdadfb2e3c68a3199f7d732d
- scripts/test_review_findings_smoke.py SHA256: e43a8ee8cce1ae534f32f8502a25d976bc9b7364e0718966e42f3d36cb316d37

提升在保护范围内，DELETE与降权独立尝试，普通清理错误全部报告并保留主异常；成功流程清理不完整会失败，不返回passed。11项原回归本轮实际通过。该部分原作者为B；本轮是原字节集成核对及复跑，不宣称另一个独立作者审核了B自己的实现。A已另行报告独立39测试/真实HTTP11的集成验证。

### 故障注入范围和清理

scripts/upload_fault_smoke.py:38先验证隔离slot、固定回环端口/开发库及本checkout上传目录。create:69核对新合成owner的上传；inject:98核对随机约束名不存在、fixture filename+owner唯一。CHECK仅限定file_id或该filename+owner；标识符来自固定表/白名单，未发现修改权限、全局配置或删除既有约束的路径。

registry以O_EXCL/0600创建；DDL前先登记名字，覆盖SQL已提交但响应报错的清理情形。release与finally都核对约束不存在；cleanup_constraints逐项独立尝试，失败保留注册文件并报错，已有注册文件拒绝覆盖。文件阻断器用xb且只位于本fileId目录；修复磁盘损坏也只改本次fixture。

fault18涵盖INSERT失败、计数失败回滚、文件写失败、合并发布失败和损坏重传，不涵盖整库中断或commit ACK丢失。隔离slot有其他人并发写入时的rglob全目录比较也不作保证，脚本limits已明确。

### 进程生命周期与重启证明

scripts/baseline.py:131使用start_new_session登记Popen对象；stop_owned:332按对象身份拒绝未登记进程，只向其进程组发信号并wait，移出children。重启先停止本次backend，再用free_port拒绝仍存在的监听者，确认端口释放后启动替代后端并等待401就绪。未发现按端口搜索/杀死外来服务的路径。

proof和校验绑定slot、checkout、checkpoint SHA256、不同的正整数launcher PID、退出/端口释放/就绪标记与先后时间。resume拒绝缺证明、其他slot日志路径或不匹配证明；concurrency phase不声称重启。该证明是受信任本机baseline产生的观测记录，不是对恶意伪造本地JSON的认证机制。

B额外使用真实Python监听子进程（非JVM/应用）验证9项：未登记子进程拒绝终止且保持监听；活跃端口拒绝free_port；登记进程确实退出并移出watchlist；端口释放；不同PID替代进程可绑定原端口；实际转换对应的proof通过校验；stop清理剩余登记子进程；外来监听进程始终存活。所有探针进程随后由本次调用清理。

### 检查数量和失败状态

fault返回前有18项check，prepare有5项，resume有11项；baseline逐一核对门槛，fault/resume还要求passed及resume restart_verified。12上传请求含同索引竞争，使用4线程及起步Barrier；2合并请求使用独立Barrier。并发后查询真库12行/12不同索引/持久计数12，合并后检查返回同一路径、重复merge幂等及准确原始字节。

prepare先拒绝已有state，最终O_EXCL/0600写私有JWT；失败resume不删除该state，只有全部检查成功才unlink。JWT未放入结果JSON。本轮22份归档未发现JWT串或token/password/jwt字段。

## B独立执行

运行源码提交为b56accc；相对固定reviewed_sha仅新增B领取latest，业务/脚本字节未改变。

| 命令/检查 | 实际结果 |
|---|---|
| python3 -m unittest discover -s scripts -p 'test_*.py' | exit0；45 tests，0 failures/errors/skipped；2.178s |
| python3 .local/b/maven/run.py --with-test-agent -o test | exit0；13 suites、317 tests，0 failures/errors/skipped；BUILD SUCCESS；Maven11.399s |
| B本机进程/TCP探针，直接调用Baseline.start/stop_owned/stop及validate_restart_proof | 9项通过；真实Python子进程和回环监听；全部探针进程清理 |
| python3 -m py_compile（本任务6个Python实现/测试文件） | exit0 |
| python3 scripts/upload_fault_smoke.py --help；python3 scripts/upload_integrity_smoke.py --help | 均exit0 |
| 两R4文件SHA256、源差异和允许路径审计；git diff --check | 通过 |

Maven使用已建立的忽略目录.local/b/maven/run.py、B独立缓存、已有ByteBuddy1.15.11 agent及离线模式；没有改POM、依赖锁或全局Maven设置。历史DNS阻塞不是本轮Java状态。

本机原始证据在忽略目录.local/b/review-evidence/MUS-014-R1-B/：
- python-all.log SHA256: 790fd0221e56707f9589e78b75cc21f2bfa27fbe429bd7265cdb8a186f94866b
- java-all.log SHA256: 246a49fce0f9acb39b20df9a8404454b3cd73264c808fda3d6a77e6e44789dfd
- independent-summary.json、process-probe.json、a-evidence-audit.json及命令元数据。
这些本机文件未推送，不假装A可读取本机目录。

## A补证的独立核对与限制

从准确assignment_source_sha读取MUS-014-live-results.json及所指22份JSON，解析/数量/跨文件关系一致。7c973b5至A运行05c9b6d只差4份docs文件，业务和脚本一致。两槽各：
- migration8、直连/代理各13功能+4安全、媒体144唯一(state,viewer,method,route)组合+8附加、ownership65、review-findings11、fault18、prepare5、resume11均与归档check数组相符。
- 媒体状态分布36×401 / 72×404 / 24×200 / 12×206。
- checkpoint声明哈希相同；prepare时间≤stop<restart；新旧launcher PID不同，退出/释放/就绪标记均true。
- prepare/resume/最终观测fileId一致（A65/B40）；并发请求12上传/2合并，最终12行/12索引/持久计数12、status1、约束0、published_bytes_match=true。
- A声明实际Java PID96493→96842，本机B槽97066→97275；这些Java PID来自A报告/汇总，不是B在该主机进程表或原日志中复核。

没有独立读取A主机、数据库、私有checkpoint或合并文件。22份归档未包含原baseline result.json与Java/后端日志；因此本轮只核对归档JSON内部一致性，不能独立重算私有state哈希/合并字节，也未自行确认原日志无SQL错误。A两槽的317 Java/build与日志声明不计为B额外执行次数。

## 未执行与下一步

本环境mysql/mysqld/docker均不在PATH，B本轮实际真库/应用HTTP/跨JVM上传检查为0，保持blocked；未重复启动已知缺失工具。进程探针9项不能替代上传prepare5/resume11。前端本轮无变更，未重复npm安装/build。

本次仅新增docs/reviews/MUS-014-B.md并更新own latest；不改业务实现、公共API、schema SQL、依赖锁、A STATUS/任务卡/feed或main。接口变化none；数据/模型/索引版本none。未处理头像同值更新交错、整库中断/commit ACK丢失、物理垃圾回收或公开检索。

交付以GitHub插件先source后feed顺序发布并回读，非原子原生Git推送；精确源SHA及报告哈希以B handoff为准。A下次sync接收此结论后串行更新STATUS，再按用户决定集成；无擅自merge/main推送。完成发布后释放两报告路径活动占用，无后台轮询。
