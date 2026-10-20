# MUS-012-R1-B：媒体与上传所有权独立审核

- task_id: MUS-012-R1-B；assignment_revision: 1；owner: B；集成负责人 / STATUS 写入方: A。
- reviewed_sha / base_sha: `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea`。
- comparison_base_sha: `436908938989ba4d331b90e2795a8a5f3f702bb2`；覆盖 MUS-011 / MUS-012，不重做模型审计。
- assignment_source_sha: `6a29de4cab2da6ac149b816165b5f058612bd133`。
- ack_peer_feed_sha: `c9c291344715a1d86894d8b6016d3983538fd899`。
- branch: `review/MUS-012-B-access-ownership`；日期: 2026-10-19 America/Chicago（运行日志 UTC 2026-10-20）。
- 领取 source: `65a26e6007455f314c15dc7702312ed5ab46ed53`；领取 feed: `8fad65cca4ca0ce418d5ca9cdcb24d4f549b11f9`；已发布并 sync 回读。
- task_status: review_completed；review_verdict: **request_changes**。
- runtime_supplement: **partial_pass / backend_blocked**；这是完成审核的结论，不是后端独立验收通过。最终交付 SHA 由 B feed 的 handoff.json 指定。

## 结论与事实层级

三项需处理发现：P1 旧 JPA 硬删除入口与新增 orphan 下载策略形成审核绕过；P2 管理员创建用户遗漏头像归属检查；P2 迁移对未知表集合的保护不足。前两项为固定提交的完整源码调用链结论，B 未实跑其 HTTP 复现；第三项执行了实际 Python 迁移函数的合成元数据回调探针，未执行真实 MySQL DDL。不得把推断写成服务端日志或已测 HTTP 状态。

三入口的常规授权、缓存和上传 owner 隔离实现较旧基线有实质修复；A 两套本机运行证据可复核。但现有矩阵未覆盖下列替代写入口，不能凭矩阵通过断言整条授权链封闭。建议 A 修复后给出明确新 SHA，再派发增量复核；本次不修改业务代码或擅自合并。

## R1 / P1：旧硬删除入口可以抹掉审核引用，使受限文件回到 owner orphan 分支

**位置（均为 reviewed_sha）：**

- `music/src/main/java/com/taffy/music/controller/MusicController.java:38–41`：DELETE /music/{id} 直接调用 MusicService.deleteMusic。
- `music/src/main/java/com/taffy/music/service/MusicService.java:24–27`：调用 JPA repository.deleteById；没有当前数据库账号、owner、审核或软删除校验。
- `music/src/main/java/com/taffy/music/repositories/MusicResourceRepository.java:6`：普通 JpaRepository，无软删除覆盖；MusicResources 无 JPA 软删除注解。
- `music/src/main/java/com/taffy/music/service/MediaAccessService.java:65–69`：只要资源引用列表为空，完整上传立即按持久 owner 允许下载。
- `music/src/main/java/com/taffy/music/service/impl/MusicResourceServiceImpl.java:313–321`：反重绑定同样依赖仍然存在的引用。

**触发前提 / 最小复现（待 A 在自己的隔离环境执行）：**

1. 合成 owner 上传并绑定一首 MP3，tagIds=[]；管理员将该唯一资源设为 rejected。选择没有 music_resource_tags、audit_logs、recycle_bin 外键引用的该资源，排除外键碰巧阻止硬删除的情形。
2. owner 的 GET /api/music-resources/{musicId}/file 与 GET /api/file/download/{fileId} 应均为 404。
3. 用 owner，或另一个有效普通 JWT，发送 DELETE /api/music/{musicId}。
4. 查 music_resources 主记录和 file_upload：源码预计 JPA 删除主记录、上传行和字节保留。再用 owner 请求原始下载，引用列表已空，预计被允许；metadata 也可重新绑定为新的 pending 记录。

**实际 / 预期：** 静态已确认旧删除路径只有 JWT 有效性门槛，没有资源级授权，并绕过标准软删除流程。上述 204 / 200 的端到端结果是待实跑预测，B 没有发起这些 HTTP 请求。预期普通他人不能硬删资源；owner 的删除也不能抹掉审核 / 删除屏障，之后下载与重新绑定仍按冻结策略拒绝。

**影响：** 既有写入口与本轮 orphan 放行形成集成缺口；可绕过拒绝审核并破坏他人元数据。旧入口本身并非本轮新增，不将其说成本轮刚引入的所有权漏洞；它直接破坏本轮安全验收目标，应阻断该目标批准及公开 discovery。

**最小建议：** A 协调 MusicController / MusicService，将旧删除入口禁用或委托到同一当前账号、owner 和软删除策略；保留审核 / 删除引用，不能用硬删让文件变回“从未绑定”。补实际 MVC 配置及真库用例：他人、锁定 / 已删除账号拒绝；无标签 rejected 资源删除后，raw 下载与 metadata 不能恢复访问。现有 MusicServiceTest:74–84 只断言 repository.deleteById 被调用，并不验证授权；新 MockMvc / live 矩阵也未调用此旧入口。

## R2 / P2：管理员创建用户绕过新头像绑定检查

**位置：**

- `music/src/main/java/com/taffy/music/controller/UserController.java:76–86`：管理员 POST /users 接收完整 Users，包括 avatar。
- `music/src/main/java/com/taffy/music/service/impl/UserServiceImpl.java:149–154`：createUser 直接 insert，未调用 requireAvatar，也未拒绝非空 avatar。
- 对照本轮同文件 :167–170、:329–332：只有更新用户 / 更新自己 profile 时才检查新头像。
- `music/src/main/java/com/taffy/music/service/MediaAccessService.java:92–116`：publicAvatar 信任 users.avatar 登记；不再次检查上传 owner，符合保留旧头像的设计，但要求所有新登记入口受控。

**触发 / 最小复现：** 合成 owner 普通上传一张 <=5MiB、真实可识别、未被音乐引用的 PNG，保持未登记头像。另一个合成管理员通过 POST /api/users 创建新账号，将 avatar 设为该私有上传路径；随后匿名 GET /api/uploads/{path}。源码预计新 user 插入后该图片被当成登记头像公开。这里需要管理员身份与已知路径；不是匿名直接上传或普通用户提权。即便管理员本人拥有该文件，新目标账号也不是持久 owner。

**实际 / 预期：** 静态确认创建路径不执行新增校验；B 未实跑图片公开请求。预期所有新增 avatar 绑定遵守 A5 的目标账号所有权、完整状态与有效账号规则，管理员创建账号不能成为例外。保留已登记旧头像并不授权新建任意引用。

**影响与建议：** 新头像防越权承诺存在替代写入口。最小修复可在创建用户时拒绝非空 avatar，待目标账号自行上传后走已校验更新流程；或由 A 设计同一绑定校验。补 UserController 实际分派测试和合成 HTTP 负例，确认拒绝后 users.avatar 未新增引用、图片仍非公开。当前 UploadOwnershipHttpTest:78 只注册 file / metadata / auth 控制器；头像负例与真实 smoke 都只覆盖 PUT /auth/profile。

## R3 / P2：迁移只核对表数量，未知 11 表结构仍会进入 ALTER 和版本登记

**位置：** `scripts/upload_ownership_migration.py:14–30`，及 `scripts/baseline.py:64–73,193–205`。

**触发：** 同一白名单 slot 的开发库仍有 version=1 和 11 张表，但 file_chunk 已被误改名为 file_chunk_unexpected，file_upload 仍保持可加列的 V001 结构。migrate 只读取表数量 / version / 新 owner 列和索引，从未读取表名集合或原有必要结构；ALTER 可成功后登记 version=2，baseline 也可能把它当已识别的库。

**B 已执行的复核：** 调用目标提交中的实际 migrate 函数，提供合成元数据回调：development_schema_version、file_upload 和 9 个 unexpected 表，总数 11；返回 version=1 与无 owner 列，模拟 DDL 后新列 / 索引符合预期。函数未查询任何表名，调用 ALTER、登记版本并返回 version=2。这是迁移保护逻辑反例，不是真库 DDL 成功证据。原始查询及结果位于本 clone 忽略目录 migration-guard-probe.json，SHA-256 为 `50010a61d7de80ebe98a8a4848542f32f2915c2a12144f51b0b42657b777a311`。

**实际 / 预期：** 保护逻辑将“数量与 marker 正确”当作已识别基线；与任务卡的“未知结构拒绝”不一致。预期在任何 DDL / 版本写入前拒绝缺表或被替换的表集合，保留现场。

**影响与最小建议：** 不会自动清数据或回填 owner；风险是给异常库继续加列并登记成功版本，掩盖启动 / 恢复前提。A 在现有小迁移器中核对 V001 必要表名和 file_upload 必要列 / 键；重入时核对 owner 列与索引的必要属性（包括 nullable、NULL 默认和非唯一性），不需要引入新迁移基础设施。增加同数量替换表、缺必要列、登记中断与正常幂等负例；在独立废弃开发库实跑，禁止对生产库试验。

## 事务与竞态：检查范围及未验证风险

uploadChunk / merge 由服务的 @Transactional 包裹 requireOwnedLocked；metadata 为服务事务；删除为控制器事务；两种已有头像更新也有事务。引用检查使用 FOR UPDATE，MusicResources 没有 MyBatis @TableLogic，因此此查询包含 is_deleted 资源；FileUpload 的 @TableLogic 则排除逻辑删除上传。正向串行调用中，音乐 / 头像绑定和删除共享上传行锁，字节保留策略合理。

仍需 A 已计划的多连接验证，不能用 MockMvc 或普通重启推断通过。一个具体静态风险是 UserServiceImpl:319–336：profile 先读取完整 Users，最后 updateById 整个实体；与管理员锁定 / 降权并发时，旧对象中的 role / isLocked 可能覆盖刚提交的新值。可用屏障暂停 profile 在 selectById 后，另一连接完成 lock / demotion，再恢复 profile 并检查最终账号状态。建议 profile 只写可编辑字段，并明确账号 / 绑定检查的并发规则。**这是未运行的交错风险，不记为已经观察到账号被解锁，也不据此声称跨事务回滚失败。**

未知 legacy owner 的人工认定、物理垃圾清理、事务失败注入、死锁 / 并发与上传跨进程续传均仍独立待验收，不扩大本审核为这些任务的实施。

## 已检查且未发现新问题的范围

- 资源文件、raw 下载、静态音乐入口取消旧匿名放行 / 磁盘映射；当前账号存在 / 锁定 / 角色读取；approved / pending / rejected / deleted 的常规策略；ZIP 逐条核验及受控路径。
- MediaResponses 与拦截器提供 no-store / Vary Authorization / nosniff；HEAD / Range 与播放计数分离；根目录外路径 / 符号链接拒绝，公开头像再检查规范路径、格式与大小。没有撤回已下载字节或旧缓存的承诺。
- create / upload 从服务端有效账号赋 owner；check / list 按 owner 查询，固定排序字段；detail / status / missing-chunks / chunk / merge / delete / metadata 拒绝他人、管理员越权及 NULL owner；普通上传持久化失败清理候选。
- V001 与 comparison_base 逐字节一致；V002 单条加列 / 索引，无 DROP / 重建 / owner 自动回填；slot B 配置白名单校验通过，未覆盖凭据。上述 R3 是保护不足，不是指 SQL 主动破坏数据。
- 前端 fetchMedia 从本地 / session 取 JWT，只接受 /api/ 相对路径，关闭缓存和重定向；音乐 / 文件下载直接消费 Blob 并保留取消信号。新增导入和 Vue 打包通过，未改 package / lockfile。
- 审阅文件为 comparison_base..reviewed_sha 的 61 个变更路径，并沿媒体 / 绑定依赖读取旧写入口；没有重新审核全部管理、邮件、模型或检索实现。

## B 独立执行结果

环境为独立 Linux clone / slot B，OpenJDK 17.0.20（jdk.compiler 模块存在，javac 不在 PATH），Python 3.12.14，私有 Node 22.23.3 / npm 10.9.9。未使用 A 的本机 B worktree。运行源码为 reviewed_sha；领取提交相对它只新增 B latest。

| 命令 / 检查 | B 实际结果 |
|---|---|
| 固定 feed sync、source / 报告哈希、任务去重、分支基线 | exit 0；A/B fetched；无本任务旧领取 |
| python3 -m unittest discover -s scripts -p 'test_*.py' | exit 0，22 tests，0 failures |
| node --test web/src/utils/media.test.js（Node 22.23.3） | exit 0，6 tests，0 failures |
| web/ 下 npm run build（相同锁文件与已有依赖） | exit 0，Vite 6.2.4；5.46s；>500kB 警告非阻塞 |
| music/ 下 sh ./mvnw -B -ntp test | exit 1，Spring Boot 3.4.4 parent POM 无法解析：repo.maven.apache.org Temporary failure in name resolution；实际 Java tests=0，未进入编译 |
| slot B baseline.validate 与 V001 字节比对 | 通过；没有重新 setup、覆盖密钥或迁移数据库 |
| migrate 合成元数据回调保护反例 | 已执行，观察到 R3；不是 MySQL DDL / HTTP 用例 |
| A 归档 JSON / 状态 / 哈希 / 源码一致性复核 | 下节所述通过；不是 B 的功能请求 |
| git diff --check、允许路径核对 | 发布前执行；仅两份 B 文档 |

mysql / mysqld / docker 均缺失；真实 V001→V002、重复迁移、MySQL 事务 / 回滚、真实 HTTP 144 / 65、两条 smoke、R1/R2 复现、并发与进程恢复、浏览器人工试听均 **not_run / blocked**。没有重跑同一 Maven 失败命令，也没有借用 A 数据库。Maven 依赖阻塞不是产品测试失败，Java 308 不记为 B 通过。

原始本机证据保留在忽略目录 `.local/b/review-evidence/MUS-012-R1-B/`，不提交凭据或扩大允许路径。日志 SHA-256：

| 日志 | SHA-256 |
|---|---|
| python-tests.log | 9b094589b49c6bb0e9bb9b9407cd32487e74692f6f0092d0a84017289845add3 |
| node-media-tests.log | e6cf1fb6afc27d82b292475f91bda5e9eab407239dba16914561824b2d23da09 |
| java-default.log | c2bbf6b63d97dece1fe1fa5a56a01150d1ac0432b34470ca4f455cd12b7a68fb |
| web-build.log | 321adf005c0ac9a44c71948f24331ab96af8e4af124b6df0ff7963d8c3c65ec7 |

## A 证据的独立核对（非 B 代跑）

已读 MUS-011 / MUS-012 验证正文、机器汇总及 14 份原始 JSON；原始 JSON 字节 SHA-256 均与 live-results 中对应 .log 哈希相符。Java suite 汇总分别为 266 / 308，与 A 正文一致。四份媒体 JSON 各 144 个唯一状态 / 身份 / 入口 / 方法元组，逐格状态符合策略，各为 36×401、72×404、24×200、12×206，另 8 项检查。四对直连 / 代理结果各有 13 功能和 4 安全检查；两份新上传 JSON 各 65 项、35 显式拒绝（7×401 / 7×403 / 21×404）。

MUS-012 的 A source `4b3ec3f142e993851da605cd8c38fa378ddb1958` 与本机 B source `078a82b4082e192258252bafe617e849ac4925f5`，分别与 reviewed_sha 比较，仅 README / docs 有差异，运行源码一致。MUS-011 为历史前一实现，不能替代 MUS-012 的新运行。未获得 A 的全部后台日志原始字节，故不能独立重算 Java / backend.log 哈希或把“无 SQL 异常”当 B 观察；相关值来自 A 汇总。

原始 JSON 证明脚本声明的覆盖和归档一致，不证明未包含的 R1 / R2 替代入口或并发安全。未创建真实语料、模型权重或索引；没有检索质量或性能结论。

## 发布、边界与交接

仅修改本报告与 `docs/collaboration/account-b/latest.md`，无接口 / schema / 依赖 / 锁文件变化，无 STATUS 或 A feed 写入，无 main 推送 / 合并。领取时原生脚本 publish 实际失败：exit 1、内部 git push exit 128；因此采用 GitHub 插件顺序发布，先核验 source 再快进更新 B feed，明确非原子传输。领取已回读验证，最终报告以 own feed 的 source_sha 为准。不同 GitHub 提交元数据造成的本地历史 SHA 不冒充远端 SHA。

下一步由 A sync B feed，记录准确 ack 并串行更新 STATUS；优先补 R1 / R2 的真实负例与最小修复、R3 保护，再派发准确新 SHA 的增量审核。A 的故障 / 并发 / 恢复任务继续由 A 协调。本检查点发布后释放两份 B 文档的活动占用，B 仍是唯一写入方；其余路径未占用。后续每次 B 会话均从 A 固定入口读取 source_sha 下的 account-b.json，按 task_id + assignment_revision 去重；没有后台轮询进程。
