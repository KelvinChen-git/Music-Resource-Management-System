# MUS-014-R1-B 独立审核

## 结论与准确对象

- task_id: MUS-014-R1-B；assignment_revision: 1；owner: B
- task_status: review_completed；review_verdict: approve（限定本任务增量及下述验证边界）
- reviewed_sha / base_sha: `7c973b5d9eac219e289623e7eb6d44eda73cb09d`
- comparison_base_sha: `d384a8fc66778ba24344f1ef19507db718872623`
- assignment_source_sha / 补证来源: `a433e2bd6a72a6f31cc6b608220f5dcf87bd8a54`
- ack_peer_feed_sha: `0093ae4030d35b2b7a2dbdc97f431ed95dff2e78`
- branch: `review/MUS-014-B-upload-recovery`（首轮）；补证分支 `test/MUS-014-B-runtime`
- current_runtime_status: independent_database_http_and_cross_jvm_pass；本轮补证见末节
- claim_source_sha: `b56acccd75647bb9440984297e986e6ec1080162`
- claim_feed_sha: `0405107fa6045f3b7f35d6b02c3faf52a4832225`
- 最终delivery_sha由本次B handoff.json.source_sha给出，避免同提交自引用。

在本卡五项范围内未发现需退回修改的问题。首轮B已独立执行Java317、Python45及9项进程保护检查，当时真库/跨JVM只核对A归档。2026-10-20用户要求补齐运行条件后，B现已独立完成真库、18故障与跨新JVM续传11项；以末节补证为当前结果。approve不代表main已合并、生产验收或公开discovery可以开放。

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

## 首轮B独立执行（补证前历史）

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

## 首轮未执行与下一步（历史）

本环境mysql/mysqld/docker均不在PATH，B本轮实际真库/应用HTTP/跨JVM上传检查为0，保持blocked；未重复启动已知缺失工具。进程探针9项不能替代上传prepare5/resume11。前端本轮无变更，未重复npm安装/build。

本次仅新增docs/reviews/MUS-014-B.md并更新own latest；不改业务实现、公共API、schema SQL、依赖锁、A STATUS/任务卡/feed或main。接口变化none；数据/模型/索引版本none。未处理头像同值更新交错、整库中断/commit ACK丢失、物理垃圾回收或公开检索。

交付以GitHub插件先source后feed顺序发布并回读，非原子原生Git推送；精确源SHA及报告哈希以B handoff为准。A下次sync接收此结论后串行更新STATUS，再按用户决定集成；无擅自merge/main推送。完成发布后释放两报告路径活动占用，无后台轮询。


## B 独立真库与跨 JVM 补证（2026-10-20，当前结果）

用户明确要求解决前述B缺MySQL/Docker导致的运行缺口。本轮是已完成MUS-014-R1-B/revision1的运行补证，不伪造A新派发、不重复认领或改变固定reviewed_sha。A检查点仍为feed0093ae4/sourcea433e2b。

- 补证分支：test/MUS-014-B-runtime；补证基础：abe9f2db05406f2c36808fbf1abb213000d35d0e。
- 进行中source：f666b9707ee7c80de1fced2554b053a9e9f441e6；进行中feed：8b7f70a509ead3665abd92901d870f7ba9ab86bc。
- 实际运行source：f666b9707ee7c80de1fced2554b053a9e9f441e6；与7c973b5仅B两份报告不同，业务、SQL和仓库验收脚本未改。
- 新独立原生临时clone：/tmp/music-b-native-rb594p3r/checkout；只用slot b。不是A本机B槽，也不是复用其数据库。
- run_id：baseline-20261020-143034-12；完成时间：2026-10-20T05:31:30.414920+00:00（America/Chicago 00:31）。

### 环境修复与真实适配范围

1. 从MySQL官方档案下载Linux原生8.0.41 minimal版及本机Node22.23.3/npm10.9.9；兼容libaio1/libncurses5/libtinfo5从Ubuntu档案提取至B私有目录，不安装系统服务或改全局配置。MySQL vendor MD5核对相同，归档SHA256为f50bbb1611955ace3993f84590ecfd636d3b83550799110f8fcddb04601b7219；Node官方SHA256核对相同，为df450af89261115ef9f9e3830c3eeb2cc9213b63c720b1af623cb5dcbe2e02de。Docker仍未安装，本次原生路线无需它。
2. 现有Java17.0.20带jdk.compiler模块但没有javac入口；私有启动器调用真实编译模块，javac -version为17.0.20。Maven沿用B缓存、运行时代理设置及既有ByteBuddy1.15.11 agent，无POM/锁文件或全局Maven设置修改。
3. 此执行环境拒绝Unix socket；已用真实MySQL验证空socket配置加127.0.0.1 TCP可运行。B私有mysqld包装器关闭Unix监听；bootstrap改走本次3308回环TCP，并保留主机名解析，因实证skip-name-resolve会拒绝新root@localhost的127.0.0.1连接。MySQL --user=root仅适配本沙箱实际UID0，不更改业务账号权限或系统服务。
4. migration_guard_probe的本机副本只替换连接传输及对应说明：新临时datadir、随机新loopback端口和唯一schema；原8项SQL/拒绝断言保持原样。不是把仓库原“Unix socket/networking disabled”字段冒充适用于此环境。
5. 首次工作目录试跑的业务检查通过，但额外清理观察发现注册文件可见性异常，另有停止后再开库时redo文件缺失；这些尝试保留为失败/blocked，不计最终通过。没有据此认定产品逻辑有缺陷。随后把完整源码checkout、数据库、上传和状态放入全新原生/tmp目录，所有运行结束后再导出日志；最终清理与持久化观察均通过。没有清空或修写A/旧库。

私有入口为python3 .local/b/runtime/run_isolated.py，exit0。它从固定源码建立临时clone、生成独立slot b，以本机适配调用未修改的Baseline.run，执行完后保存证据并关闭本次全部服务。适配只涉及工具路径/传输与运行目录；不改HTTP、业务算法、FOR UPDATE、schema或验收断言。

### 本轮独立实际结果

| 检查 | B实际结果 |
|---|---|
| 冷编译与Java测试 | 317项，0失败/错误/跳过，BUILD SUCCESS |
| Node22/npm10前端生产构建 | passed，使用现有node_modules及lockfile |
| 全新开发库初始化 | 11表，V001/V002；无旧owner回填 |
| 独立临时库迁移保护 | 8项通过；本机原生TCP传输适配 |
| 后端直连 / Vite代理 | 各13功能+4安全通过 |
| 真实媒体权限 | 144唯一组合+8附加通过 |
| 真实上传所有权 | 65项通过 |
| R1/R2与清理修复HTTP回归 | 11项通过 |
| 真实SQL/文件故障注入 | 18项通过 |
| 部分上传prepare | 5项通过 |
| 跨新JVM续传resume | 11项通过；12并发上传请求、2并发合并 |
| 独立最终SQL与磁盘观察 | file16完成，12行/12不同索引/持久计数12，原字节校验通过，剩余故障约束0 |
| 停机与私有清理 | state/registry/baseline.lock均不存在；3308/8081/5174无监听 |

实际Java PID为852→1192；Maven launcher为708→1048。原进程退出、端口释放后才启动替代进程；新实例就绪后执行resume。两份后端原始日志均未见SQLSyntaxErrorException/BindingException/CommunicationsException/APPLICATION FAILED TO START；故障注入预期的CHECK拒绝不作为异常SQL语法故障。

机器证据摘录（非JWT）：

```json
{
  "slot": "b",
  "file_id": 16,
  "old_java_pid": 852,
  "new_java_pid": 1192,
  "old_backend_launcher_pid": 708,
  "new_backend_launcher_pid": 1048,
  "stopped_at_unix": 1792474281.7764778,
  "restarted_at_unix": 1792474288.3367646,
  "prepared_state_sha256": "2e9f4a7ab642dfac0d0cb14447e4a083dc1c2cc15bcb3f0796fec0425efca456",
  "persisted_uploaded_chunks": 12,
  "chunk_count": 12,
  "chunk_rows": 12,
  "unique_chunk_indexes": 12,
  "remaining_fault_constraints": 0,
  "published_bytes_sha256": "a70b3ab74f5f670f4a8d36f6fc6833a36ec77e3eec40d65e9752511d851c16d2",
  "private_state_removed": true,
  "fault_registry_removed": true,
  "baseline_lock_removed": true
}
```

逐份解析原始JSON并与baseline.result内嵌内容比较，检查数、媒体唯一元组、prepare/proof/final哈希、时间、fileId与最终计数一致；结果JSON未发现token/password/JWT字段或JWT串。此次不再借用A的数字。

### 原始证据与剩余边界

本机证据导出至忽略目录.local/b/review-evidence/MUS-014-B-runtime/，包含完整本轮baseline日志、结果、proof、final-observation.json及verified-runtime.json；配置/密码/私有JWT未纳入报告或Git。原始日志仅本机持有，不宣称A能读取此路径。已提交报告提供精确SHA、命令、环境适配、数值与哈希，供A审核；继续遵守本卡只写两份B报告的边界。

- verified-runtime.json SHA256：dc4735b97eb222d60a62031222718933c0ab7db465a55981e5f3a1ba845bbcba
- result.json：4f05db37b463d28d3c7c3485911701c60b0f5673d65dc200e2b1f86eeec19838
- java-tests.log：dbbc48a84f6f3ba039d0ff375f239e4ca15387123899702a5ec107c9ba80b805
- frontend-build.log：9c363c1e6cf0d17538309d8c03c3ef528e24be60aa36b2ce6b5914c055d61a0a
- backend.log：cdcdec3eef47de507f2cd9fbd9dad531d1863c3ec98d7143593230e8f368575d
- backend-restarted.log：1970694303a21feb156acc922a5515ed0ac9095c6c2138ede76ba1d7e1d2a418
- restart-proof.json：4d92479ab887823037d20a13cec60fd96403633e592b72d6fcf33ea8f48c65b0

工作目录早期失败的自建数据/注册文件已移到B忽略的失败现场目录保留，不清空、不修写计数或约束来掩盖失败；其运行进程已停止。最终通过来自新的原生临时库，不能把此前失败尝试改写为通过。此运行适配留在B忽略目录，不声称仓库标准入口已经获得无适配的通用Linux兼容性。

原“B缺MySQL而真库/跨JVM执行0”仅为首轮历史，本次该缺口已补齐。Python45与子进程探针9项沿用首轮独立通过记录，本次未无故再跑；真实上传不能由这些旧测试数字替代。本轮仍未模拟整库中断或提交ACK丢失，未验收头像交错、物理GC、检索质量/性能或生产部署；main未合并。

本次依旧只改本审核正文与own latest，发布后释放两报告路径活动占用。A下次sync接收补证后串行更新STATUS；最终集成/合并仍由用户决定。
