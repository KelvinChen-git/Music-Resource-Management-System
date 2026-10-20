# MUS-015-R1-B：头像重新校验独立审核

## 结论与版本

- task_id / revision：MUS-015-R1-B / 1；owner B；task_status review_completed。
- review_verdict：approve（限同值头像重新校验增量及原空字符串清空兼容；下列C1既有NULL语义不计作本次新增阻断）。
- reviewed_sha / base_sha：`d9a2a15791da0db4374c5de093a752a5aa202a25`。
- comparison_base_sha：`feb935ad5c7eb4eb8a11065f3d5c18ed2a93dab1`。
- assignment_source_sha：`dbb631218b8ee7c87823ce594494b908b2849e32`。
- ack_peer_feed_sha：`c618062350efb32a30cb7065694945fab02dd39c`。
- branch：review/MUS-015-B-avatar-revalidation。
- claim_source_sha / 实际新代码运行SHA：`80e65a6e493f12b3355689cb04cd0016fc5fd54c`（相对reviewed仅B领取latest）。
- claim_feed_sha：`e940ba956c04bc620511e63a39bd793bbf0b30ff`。
- delivery_sha：本轮B handoff.json.source_sha，不在同提交自引用。

本次两处条件修复未发现新增阻断问题。B独立运行Java320，复现旧代码52测试中3项预期失败，并以真实HTTP/MySQL验证了两入口等待后读取当前删除状态以及引用写入前持有上传锁。另发现avatar:null成功回显与持久化不一致的既有行为，见C1；不能将它写成“所有空值清除已验收通过”。

## 范围与代码核对

UserServiceImpl.java:164/318两个公开写方法均为现有@Transactional；:175与:336不再比较旧avatar相等性，非空输入均进入UploadAccessService.requireAvatar。它按目标owner、file_path、status=1进行LIMIT 1 FOR UPDATE当前读；逻辑删除条件及显式deleted/owner/status核对仍在，旧用户普通读取产生的RR快照不能代替当前上传状态。

profile在:344使用LambdaUpdateWrapper只写请求中的name/avatar及updated_at；不把旧role/is_locked/password等列写回。仅名称更新不会写回读取到的旧avatar。管理员仍使用旧updateById整实体路径，未借本轮声称它的所有安全列并发问题也已治理。

FileUploadController.deleteFile持有父上传行锁后调用requireUnreferenced；用户/音乐引用以FOR UPDATE当前读核验，再逻辑删除。头像输入校验与删除共享上传锁。真实锁证据见下，不仅根据注解或mock作结论。

静态交错目标为T1读取旧A，其他事务把引用切到B并删除A，T1随后恢复旧同值A。本轮真实SQL控制试验让T1在A锁上等待，再由仅本次fixture的另一SQL事务原子切到B并标记A删除；profile返回404，管理员旧封装HTTP200/业务非200，数据库均保留B。此为真实多连接受控试验；中间切换/删除由直接fixture SQL完成，不冒充三个正常HTTP参与者完整复现。

## C1：P2既有兼容性观察，NULL清空回显与持久化不一致

位置：UserServiceImpl.java:177–183与Users.avatar字段映射。对一个已设置合法头像A的新合成用户，管理员PUT /users/{id}提交name/email/role及avatar:null：
- 实际HTTP200、业务code200，返回data.avatar为null。
- 随后独立SQL读取users.avatar仍为A。
- 相同fixture提交avatar:""则SQL确实变为空字符串。

影响：采用null表示清空的调用者会收到成功/空头像回显，但持久引用没有清除；后续重新读取或上传删除仍按旧引用处理。当前实体updateById的NULL字段写入策略与返回内存对象造成差异。base与reviewed均有相同setAvatar/updateById路径和映射，本轮只删相等性分支，故这不是本次新增回归。

建议A明确区分“未提交”“显式null”“空字符串”。若维持空字符串为唯一清空方式，应将此写清并使null响应与实际持久值一致；若要支持显式null清空，应使用能识别字段是否提交的DTO/局部更新，并补真库断言。不要为此直接全局开启NULL写入，否则现有管理员不提交avatar的编辑可能意外清空。该建议未在B擅自实施。

原始探针将此记作R1/P2，本报告以C1标识其非增量性质。审核批准覆盖本次安全条件修复和已实跑的空字符串行为，不批准尚未明确的NULL清空契约；请A登记后续处理。

## B独立验证与准确计数

### Java与旧实现负回归

1. 在comparison_base的独立原生临时clone保留旧业务源码，只放入reviewed版本的UploadOwnershipHttpTest测试文件，执行：
   python3 .local/b/maven/run.py --with-test-agent -o -Dtest=UploadOwnershipHttpTest test。
   实际exit1，52 tests / 3预期failures / 0 errors / 0 skipped；三个新增case均命中。不是旧缺陷的真库并发复现。
2. 新代码80e65a6原生临时clone执行完整Maven test，实际320 tests、0 failures/errors/skipped、BUILD SUCCESS（冷编译）；日志位于baseline-20261020-145215-11。与固定d9a2a15的业务/测试字节一致。
3. Java已通过后，后续只调整B忽略目录探针，没有重复完整320测试。Python/前端无改动，没有重装依赖或重跑45 Python/Vue build。

### 真实HTTP与旧快照当前读

baseline-20261020-145619-11保留16项已完成业务检查：
- profile/管理员的合法同值与切换新自有头像：4项。
- 仅名称修改仍可用，头像/role/is_locked持久值保持预期：1项。
- 同值输入遇到deleted、未完成、NULL owner、其他owner，两入口均拒绝，引用不变：8项。
- 管理员空字符串清除的SQL持久值核对：1项。
- 两入口各一次受控旧快照/上传锁等待/删除后拒绝，数据库保留B：2项。

C1的null观察单列，未混入16个通过项。该次命令在后续锁等待采样断言处exit1，result.status=blocked；上面是原始completed_checks中已完成的16项，不能声称该整次命令passed。早期一次BIT列解码误判、一次不支持的诊断变量及等待字符串采样问题均为B探针问题，保留失败现场，不归因于产品。

### 锁覆盖引用写入的专项试验

改用performance_schema.data_locks的实际锁记录，baseline-20261020-145841-11专项命令exit0，2项通过。分别对profile/管理员：
- 本次fixture SQL事务先锁用户主键行。
- 真实HTTP校验合法头像并等待用户写入。
- 同一HTTP事务在users.PRIMARY上为WAITING，同时file_upload.PRIMARY的A行为GRANTED/X；B对这两条记录的同一ENGINE_TRANSACTION_ID做了程序断言。
- 释放SQL事务后，写入成功；并发DELETE最终409，上传deleted仍为0、头像引用仍为A。

摘录锁证据（仅合成数据）：

| 入口 | HTTP事务ID | users主键1 | file_upload主键1 | 并发DELETE最终HTTP |
|---|---|---|---|---|
| profile | 1451 | WAITING X | GRANTED X | 409 |
| 管理员 | 1457 | WAITING X | GRANTED X | 409 |

information_schema.innodb_trx的trx_query/state采样并不总能反映实际等待，管理员采样甚至显示SELECT @@session.transaction_read_only；本结论依据performance_schema真实行锁记录。DELETE请求未在采样中出现file_upload等待，不声称观察到该等待链；其最终409只作结果核验。

两轮合计18个完成的正向/拒绝业务检查，分布在上述不同命令；另有1项C1兼容性观察。真实SQL只改本次新fixture，不连接A服务、不创建schema补丁/约束或修改全局权限。

## 环境、证据与未验证内容

沿用B已披露的私有Linux原生MySQL8.0.41、Java17.0.20编译模块入口、Maven私有缓存/运行时代理和loopback TCP适配；源码/数据库/上传处于新/tmp独立clone，slot b（3308/8081）。没有Docker依赖，没有操作A本机两槽。各次拥有进程和SQL客户端均已关闭，最终3308/8081无监听。

本机完整证据在忽略目录.local/b/review-evidence/MUS-015-R1-B/，原始日志未上传，不宣称A能读取此路径。报告/结果JSON未包含JWT或密码字段；HTTP token仅在进程内使用。

SHA256：
- 旧实现52/3负回归日志：00ff7c33b5c8d2c1bbd96b2c2274beab7ff06b14785bd38f8ff15c5b0591c1da。
- B新代码Java320日志：386b4c73f78bd69c719c536ab38db0cfa0741ad1d917b5aa71c65268595a05fc。
- 16完成检查及C1的result.json：325714eb87dc502b2fe1eade363494b2d5c1c5ad3e72434bfac99ef627cec2c3。
- 两入口锁专项result.json：136ae8490e8a2a12233e94aeaeed7554b2642b1ad0216ff72bd69b6412da05d8。
- verified-review-evidence.json：a3dc2f8a37157cf0846854ce38cd9e07fdb6bf2e7472c0e0b09c54240a17f763。

没有三正常HTTP参与者全流程竞争、整库中断/commit ACK丢失、压力/性能、物理GC或公开检索验收。对锁生命周期的证据限上述合成受控时序；未外推所有管理员角色/锁状态并发。数据为全新开发库V001/V002及本次合成PNG/账号；模型/索引版本none。

仅提交docs/reviews/MUS-015-B.md与own latest；接口/业务/schema/依赖锁/A台账/派发/feed均未修改。git diff --check与允许路径核对通过。沿已披露GitHub插件先source后feed顺序发布并回读，非原子原生Git推送；精确交付SHA以handoff为准。

发布后释放两报告路径活动占用。A下次sync接收approve的准确范围、独立运行证据与C1后串行更新STATUS/后续任务；main未推送或合并，无后台轮询。
