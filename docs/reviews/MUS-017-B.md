# MUS-017-R1-B 独立审核

## 结论与准确输入

`review_completed / approve_with_scope_limits`。本次增量未发现阻断问题。管理员有效请求中的null/缺字段保持、空字符串清空、非空头像重新校验以及局部写列已获独立Java与真HTTP/MySQL证据；MUS-015原C1（avatar:null假回显清空）在本轮验证中关闭。下述E1/E2单列给A，不把批准外推至所有用户写入口或空请求。

- task_id / assignment_revision：MUS-017-R1-B / 1；owner B。
- reviewed_sha：`f351b0e2030e5411b6f530ca039c694d4ca091d3`。
- comparison_base_sha：`d443966148336b719cebdb041ea175dfbbfdc500`。
- assignment_source_sha：`d34f282a499b3e93c94f90c83c38d35dcb21ca3a`。
- ack_peer_feed_sha：`35c357212f6ee12a255dae934d43ac8bf84768c0`；开始及结束前检查点一致。
- branch：`review/MUS-017-B-admin-avatar-null`。
- 已先主动发布claimed：source `067f6c3d6517da0852a10d6396fdc23161102525`，B feed `0748515936eb5cb41446279acc29e52725781c1e`。
- 仅交付`docs/reviews/MUS-017-B.md`及`docs/collaboration/account-b/latest.md`。A的业务、任务卡、STATUS、契约、schema、依赖锁、main均未修改。

## 源码核对

比较基线至目标仅7文件；业务增量为UserServiceImpl和UploadOwnershipHttpTest，其他为说明。`UserServiceImpl.java:164–190`保留@Transactional，非空头像仍先requireAvatar，所有本次非null的name/email/avatar/role才进入LambdaUpdateWrapper；WHERE绑定路径id，另写updated_at。user只在内存中应用非null请求字段再返回；未提交字段返回的是已读快照，不代表并发最新值。

`Users`全局NULL策略、`UploadAccessService.requireAvatar`及控制器管理员检查均未改。上传校验仍限定目标owner、status=1、deleted=0并FOR UPDATE；空字符串解除引用，不创建新引用。profile保持原来仅写可编辑列的实现。没有通过保留旧avatar再updateById的方式引入旧快照回写。

三新增测试核对响应/null/省略、明确空串参数和局部写列；旧业务换新测试失败并不表示旧空串清空本身失效，其中也有mapper调用形态断言。真正持久化结论来自下面独立SQL查询。

## B实际执行与结果

所有业务运行均位于目标准确SHA的新临时clone、slot B新库/上传目录，不请求A或旧B服务，不触碰演示曲库。原始文件保留在忽略目录`.local/b/review-evidence/MUS-017-R1-B/`；运行工具亦未提交。日志显示+09:00，交接时间为UTC，不据此混淆代码版本。

1. 比较基线的临时clone，仅用目标测试文件替换UploadOwnershipHttpTest，执行`python3 .local/b/maven/run.py --with-test-agent -o -Dtest=UploadOwnershipHttpTest test`：55项，3预期失败、0错误/跳过，命令exit1。失败准确为三个新用例，非真实并发复现。
2. 目标准确SHA冷编译完整Java：私有RuntimeBaseline适配后执行`sh ./mvnw -B -ntp -o test`（增加当前进程代理settings、B专用缓存及现有ByteBuddy agent）：323项、0失败/错误/跳过，BUILD SUCCESS。run `baseline-20261020-154029-217`。该运行随后因空对象请求不符合成功预期而exit1/status blocked；已完成的全null业务检查1项与Java323不能被改写成全命令passed。
3. 保留上述失败证据，私有探针将空对象差异记录为finding并继续执行其余验收，不改产品代码、仓库测试或SQL。新的目标临时clone运行`python3 .local/b/runtime/run_mus017.py`，内部`mus017_native.py`启动自己的原生MySQL/JVM；run `baseline-20261020-154132-16`，命令exit0，结果明确`review_findings`：23项预期业务检查通过，另1项E1差异。该次引用前轮准确SHA的Java323及旧55/3结果，均未重复执行；不称“24项全通过”。

23项通过内容：

| 范围 | 数量 | 实际观测 |
|---|---:|---|
| 全部可编辑字段显式null、avatar:null改名、省略avatar改名 | 3 | HTTP/业务200；响应与单独SQL一致，旧头像/邮箱/角色保留 |
| 空字符串清空及随后删除上传 | 2 | 响应/SQL avatar均空串；解除引用后DELETE成功，上传deleted=1 |
| 合法同值/新owned头像 | 2 | 响应和SQL均为请求路径 |
| 显式name/email/role/avatar、忽略请求保护列及伪造body userid | 2 | 只改路径目标；未提交安全值保持 |
| deleted/incomplete/NULL owner/他人头像，两入口 | 8 | 管理员HTTP200/业务500、profile HTTP404；SQL快照不变 |
| 普通用户调用管理员编辑 | 1 | HTTP200/业务403，目标不变 |
| 名称编辑受控交错 | 1 | 只写name/updated_at，保留另一连接新头像/邮箱/角色/锁/密码/原因 |
| 旧同值头像等待上传锁后重新校验，两入口 | 2 | 上传在等待期间删除后请求拒绝，SQL保留新头像B |
| 上传锁覆盖用户引用写入，两入口 | 2 | 同事务users写WAITING且file_upload主键X锁GRANTED；最后DELETE409，引用和上传保留 |

名称交错为独立SQL fixture连接持有users目标行，正常HTTP管理员改名读到头像A后到达UPDATE等待。performance_schema/threads直接观察事务1540等待SQL：SET仅name/updated_at、WHERE userid=1。fixture事务改为头像B、邮箱/角色/锁/密码/原因新值并将A标删除，再提交。HTTP成功，响应仍含已读A（符合冻结快照语义），独立SQL的B及全部新值均保留；并非声称响应始终最新。

另两旧同值时序直接观察上传行WAITING（事务1548/1555），fixture切B并删A后，管理员业务500/profile404，SQL保持B。锁期限两项直接观察同一HTTP事务1562/1568在users主键WAITING时仍拥有file_upload主键X,REC_NOT_GAP/GRANTED，提交后正常HTTP DELETE409。未采样到DELETE本身的锁等待，不宣称三个正常HTTP参与者竞争已验收；受控数据变更参与者是SQL fixture。

两次均停止所有自己登记的JVM/MySQL及SQL客户端；最终3308/8081无监听。临时库仅3个合成账号、3个合成PNG上传，无音乐数据。无Python/前端变更，未重复其安装/构建或无关旧全矩阵。

## 单列观察与建议

### E1 / P3：空对象请求在实体反序列化阶段返回服务器错误

位置：`music/src/main/java/com/taffy/music/domain/Users.java:14`的@JsonIdentityInfo、`controller/UserController.java:180`直接绑定实体，以及`config/GlobalExceptionHandler.java:25–27`兜底。

实测管理员PUT /users/1、body `{}`：HTTP200、业务code500，消息含`JSON parse error: No Object Id found`及userid，数据库不变。同一目标body含显式null字段则200/200并保持；省略avatar但提交name也通过。不能将“缺字段保持”外推为完全空对象请求已成功。

上述实体注解、控制器绑定与异常处理在比较基线中已存在且未改；既有来源为静态确认，未在旧JVM重跑该HTTP。影响是空请求错误分类/契约边界，不是本次局部UPDATE造成的数据覆盖。建议A明确空对象是允许无操作还是拒绝请求；随后用专用输入DTO或针对性绑定/400处理，并补请求边界测试，不为此全局改NULL策略。E1不阻断本卡正常字段请求的修复批准。

### E2 / P2静态风险：其他既有用户写入口仍可能回写旧快照

位置：`service/impl/UserServiceImpl.java`的lockUser:255、unlockUser:269、changePassword:321、lockUserWithReason:377、resetUserPassword:392及resetPasswordWithCode:499仍对读取的完整Users调用updateById。这些位置与比较基线一致，不属于本次updateUser替换。

推断影响：这些事务读到旧头像/角色/安全列后，另一事务完成相关更新，原完整实体的非null值可能把新值覆盖；本卡管理员仅改名的保护不能外推到这些路径。未在本轮对上述入口做真库时序复现，不把风险写成已证实漏洞或新回归。建议A独立立卡，将每个入口限制为其实际修改列并补受控并发验证；B没有擅改源码或扩大认领。

## 环境、证据和限制

Linux隔离进程，JDK17.0.20、Maven3.9.9、MySQL8.0.41，真库REPEATABLE-READ。沿用B私有vendor工具/兼容库路径、JDK编译器launcher、现有ByteBuddy agent和每进程代理settings/cache。当前环境不支持Unix socket，因此仅bootstrap客户端/私有mysqld启动参数转loopback TCP；移除私有进程skip-name-resolve并保留root@localhost绑定，未改产品SQL/schema/权限契约或验收断言。新clone/DB的可变状态全在单次exec的原生/tmp内，停止后复制不可变证据。

| 私有原始文件 | SHA256 |
|---|---|
| before-tests.log | `f5f2842dc35aee9d1e564e0cca1ce44a0df15293a993d7de97d0ee76e0c2fe2b` |
| baseline-20261020-154029-217/java-tests.log | `3f3aaf67d25fd62bd83a5ef0c615108a6cc2de5ad2b777c0775a390348434b5a` |
| baseline-20261020-154029-217/result.json（blocked） | `417c9cd16e566906de80b3d1985e632a9b68a3406510e69734c3279f74e72a5b` |
| baseline-20261020-154132-16/result.json（23+E1） | `c02cabb36721ec57ece2fb71e2b21dac5ea67ab0a648060e648beb83ac526434` |
| verified-review-evidence.json | `5b04b59e142408134c316dff5d30d48a32f34f7f8f320812b521f32595b7c3ee` |
| private-probe-manifest.json（最终私有适配代码哈希） | `418af5e91b2cdf4d7ffc43b246a5df736664af197c125e1f67121f58b38e8086` |

原始日志/适配工具未随两份报告交付；A可以核对本报告和feed/hash声明，不能声称已自行重算私有日志。两次运行分别列示，不合并伪装单次全通过。原Baseline通用limits中的“非另账号确认”是复用工具模板，实际本报告明确为独立B clone亲自执行，不将其等同生产验收。

数据版本：合成1×1 PNG，SHA256 `8d10b5f3d2f76e8088b12fa666ec9a0f60b6b7fd4e25b5fcc5eff000dfac044e`；独立新库仅fixture。模型/索引版本：无，不涉及音乐检索或质量指标。未执行：MUS-016独立审核、其他用户写入口多连接复现、三正常HTTP参与者竞争、整库中断/提交ACK丢失/GC/生产及检索质量验收。

## 交付与下一步

任务/owner：MUS-017-R1-B revision1 / B；分支、基础和准确审核SHA见上；最终交付SHA由collab/account-b的handoff.source_sha记录。仅两份B报告，接口变化无，数据/模型/索引无持久变更。工作完成并释放两报告路径；A继续串行更新总台账，接收本卡范围内批准并决定E1/E2后续，MUS-016仍单列。不得据此宣称main已合并或现有演示服务已升级。

发布使用已授权GitHub插件的源码分支→B feed顺序备用路径，非原子；原生Git写凭据未配置，不请求Token。实际发布及回读结果以最新B feed/handoff和最终交接为准，发布不等于A已接收。
