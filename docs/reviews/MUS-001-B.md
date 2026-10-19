# MUS-001-R1：账号 B 基线与媒体访问审核

- task / owner：MUS-001-R1 / B；集成负责人及 STATUS 写入方仍为 A。
- reviewed_sha / base_sha：`7ab0d39d920a538b28878cf92ecbe90e55994ec3`。
- review branch：`review/MUS-001-B-baseline`；审核开始时 HEAD 与 base_sha 逐字相同。
- ack_peer_feed_sha：`d0a8381ee015077100f84354d3f39720da41c4de`。
- A source_sha：`0ba0a968d135f3199112f2dfa703b70a04d79617`。
- 日期：2026-10-19，America/Chicago。本文不是 b81f57c 首轮报告的再次发布。

## 审核结论

MUS-001 已建立独立 local 配置、唯一空库 SQL、参数化前端代理及扩大后的测试选择。B 在固定 Node/npm 下复跑前端安装和构建成功，slot B 配置隔离、拒绝覆盖及 strictPort 成功；源码层面未发现这些改动阻断本地前端开发。

后端复跑仍为 **blocked**：B 环境不能解析 Maven Central，并且没有 MySQL 或 Docker。B 实际执行 Java 测试 **0 项**，未独立完成空库初始化、后端启动、两条完整 smoke 或媒体 HTTP 矩阵。A 提交中的 9 类 / 89 tests、11 表、两次 13 项 smoke 是已读取的 A 证据，不能记为 B 的通过项。需要可运行环境补证后才能独立确认完整后端基线。

**对外 discovery 的媒体权限验收仍阻塞。** 三条媒体入口都缺少统一的资源可见性核验，长期缓存策略还会延长失效内容的可用期。分片持久化除重复路径外，还存在自定义批量 mapper 未注册的静态缺口；不能只将其视为无害重复主键日志。本轮按任务卡只报告，不修复服务或公共契约。

## 接入、范围与证据来源

1. 先读取固定 A feed 的 handoff.json / latest.md，再读取 source_sha 中的 BOOTSTRAP_B、AGENTS、README、PROJECT、CONTRACTS、STATUS、任务卡和协作协议。feed 报告 SHA-256 为 `c37bfd798b4a11ba0a10c11fd6d876407d8dcd47d06938a0dcf9a974257e4f97`，与 source_sha 内原报告副本逐字一致。
2. 沿用 B 独立 clone，创建指定任务分支；只从固定 A source 提取本机 `.local/collaboration/collab.py`，其 SHA-256 为 `fd672cd0ab15dfc30400f134605cec0a47638bcc2c20a248bf9004ceac27ad14`。没有将脚本加入审核分支或修改 A 的脚本。
3. `sync --account b` exit 0；新 receipt 为 A=fetched / feed_sha=d0a8381…、source_sha=0ba0a968…，B=not_published。A 正文中的“尚未发布”按用户说明视作历史；本轮已实际从远端获取 A feed。
4. diff 范围为 `b81f57c79e1cefb96c2055df4ae438aa24fb475c..7ab0d39d920a538b28878cf92ecbe90e55994ec3`：24 文件，含文档提交 8f1fb6b 及实现 7ab0d39。重点检查配置、V001、pom、mapper、标签关联和测试 fixture，另读任务要求的旧媒体与分片路径。
5. 本轮仅写本文及 `docs/collaboration/account-b/latest.md`；未修改 STATUS、A feed、schema、契约、业务源码、配置、pom 或 lockfile。B 仅使用 8081 / 5174 / 3308 与 music_dev_b，没有连接 A 的 3307 或目录。

## B 的实际复跑

环境：Linux，OpenJDK 17.0.20（确认 jdk.compiler 模块存在；javac 命令未在 PATH），Python 3.12.14；在 slot B 私有工具目录安装并使用 Node **22.23.3** / npm **10.9.9**。没有修改项目依赖锁。

| 命令 / 检查 | 退出码与实测结果 | 结论 |
|---|---|---|
| `python3 .local/collaboration/collab.py sync --account b` | 0；A=fetched，B=not_published，feed 与用户指定 SHA 相同 | passed |
| `python3 scripts/dev.py setup --slot b` | 0；8081 / 5174 / 3308，schema/user=music_dev_b，SMTP=1026，独立上传/分片路径 | passed |
| 重复同一 setup，比较前后三个私有文件的哈希及权限 | setup=1；原文件未变；slot 目录 0700、三个配置文件 0600；JWT secret 长度满足 HS512 要求，未输出秘密值 | passed（拒绝覆盖） |
| `python3 scripts/dev.py init-db --slot b` | 1；`ERROR: [Errno 2] No such file or directory: 'docker'`；mysql/mysqld/podman 也不可用 | blocked；未连接数据库 |
| `sh ./mvnw -B -ntp test`，带 slot B 环境 | 1；Spring Boot 3.4.4 parent POM 不可解析；`repo.maven.apache.org: Temporary failure in name resolution` | blocked；编译、testCompile、测试均未进入，执行数 0 |
| `sh ./mvnw -B -ntp -Dtest='*Test' test`，带 slot B 环境 | 1；同一 parent POM/DNS 错误 | blocked；执行数 0 |
| `npm ci --no-audit --no-fund --fetch-retries=0 --fetch-timeout=30000`，Node 22.23.3/npm 10.9.9 | 0；244 packages，约 8 秒，lockfile 不变 | passed |
| `npm run build`，相同环境 | 0；Vite 6.2.4，构建约 5.20 秒；有非阻塞 >500kB 警告 | passed |
| 用 Vite `resolveConfig` 加载真实 slot B 环境 | 0；host=127.0.0.1、port=5174、strictPort=true、proxyTarget=http://127.0.0.1:8081 | passed |
| 本检查占用 127.0.0.1:5174 后启动 `npm run dev` | Vite=1；`Port 5174 is already in use`；未漂移端口，测试 socket 已释放 | passed（端口冲突拒绝） |
| `python3 scripts/smoke.py --slot b` | 1；`<urlopen error [Errno 111] Connection refused>` | blocked；功能检查 0 |
| `python3 scripts/smoke.py --slot b --via-proxy` | 1；相同 connection refused；本次未保持 Vite/后端服务运行 | blocked；功能检查 0 |
| Python 语法编译、pom XML 解析、V001 表声明及 FK 目标核对 | 通过；11 个表声明；FK 引用目标列存在；无 DROP/USE/CREATE DATABASE 或禁用 FK 的执行语句 | passed（静态；不等于 MySQL 执行） |
| Git diff / 明确文件检查 | 修改范围仅 B 两份报告；受审源文件与锁与 reviewed_sha 一致 | passed |

未执行：真实 MySQL 的空库初始化与非空库拒绝、实际后端启动及 JPA 仓储、完整业务 smoke、48 个媒体 HTTP 单元格、缓存/Range 故障复现、重启/并发上传、损坏哈希负例、真实邮件、浏览器试听及模型/索引/检索评测。环境阻塞不记为代码测试失败。

## A 已提交证据及改动的交叉核对

| 范围 | B 核对结果 | 限制 |
|---|---|---|
| 测试选择和依赖 | pom:170–180 把 starter-test 限于 test scope、移除旧测试版本覆盖；:215–223 使用全部 `*Test.java` 并 failIfNoTests。9 个 Test 文件的 @Test 数量与 A 汇总逐类相同，总计 89，A 汇总 failures/errors/skipped 均为 0 | 静态统计及 A 证据一致；不能代替 B 实跑或证明实际依赖解析版本 |
| 修复的测试 fixture | MusicResourceServiceImplTest 的变更补齐设置及 update/delete stub、初始化 TableInfo、用 TempDir 和完整 MPEG 帧替换截断 fixture；保留资源 owner/pending/filePath 等断言 | 未通过变更生产业务来规避测试；本轮未执行这些测试 |
| 唯一空库 V001 | 11 表按依赖顺序声明；additional_metadata=JSON；关联列 musicid/tagid 与 JPA JoinColumn、Long IdClass 对齐；audit_id/admin_id/music_id 与 Auditlogs 对齐；categoryid 可空；auto_cleanup seed 为 0 | 只适用于空开发库；没有已有数据库迁移或完整 Hibernate validate 证据 |
| SQL 版本 | SHA-256=`e2c4b01537dabdf01354faabf4876821cdae7de7cc549809ee1a60708c99146e`，与 A 文档一致 | 本轮未实际初始化 |
| JSON 映射 | mapper:9–16 新 resultMap 明确 JacksonTypeHandler / Map，查询引用该 resultMap，实体仍保留 JSON 映射 | A 的 smoke 验证了带 ID3v2 合成文件；不等于所有音频元数据齐全 |
| local 配置 | profile 显式开启；后端绑定回环 /api，SQL init=never、DDL=none；Vite 读取 slot 环境，strictPort 已在 B 验证；.local 和模型/索引目录有 ignore | Compose / SMTP / 完整双端服务运行在 B 未验证 |
| A 的运行记录 | A 提交的默认及显式测试说明为 9 类/89；直连及代理 JSON 各有 13 项检查、资源 Range=206、三个匿名暴露状态=200 | 这是 A 的历史运行证据；B 本轮没有把它重命名为自己的 passed |

分类主键仍是已记录的范围限制：[MusicCategory.java:20](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/domain/MusicCategory.java#L20) 为 Integer，V001:25 和 MusicResources.categoryid 为 BIGINT/Long。普通 seed=1 路径不因此阻断；大于 Integer 上限的分类 ID 仍需端到端边界验证，不能宣称全链路 Long 支持。JPA 的 unique/nullable 声明也不与 SQL 完全等同，例如 category_name 的 unique 声明、recycle_bin.deleted_by 的 nullable 声明；本轮没有开启 validate 或测试所有 JPA 仓储，后续统一类型/约束需 A 协调，不在本审核直接改 schema。

## 发现：严重性、重现与最小后续范围

### P1：三条媒体路径缺少统一的资源权限与状态判断（既有缺陷，仍阻断对外 discovery）

- **位置**：[MusicResourceController.java:465](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/controller/MusicResourceController.java#L465) 的匿名 resource file；MusicResourceServiceImpl:221 只按 ID 取实体；[WebMvcConfig.java:24](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/config/WebMvcConfig.java#L24) 排除 raw download 和整个 uploads；[FileUploadController.java:469](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/controller/FileUploadController.java#L469) 只核对上传完成及文件存在。
- **最小复现**：在自己的 slot B 建立一个完成上传的合成文件及音乐资源，记录 musicid、fileId、filePath；对 pending/approved/rejected/资源软删除四种状态，以匿名、owner、other、admin 分别 GET `/api/music-resources/{musicid}/file`、`/api/file/download/{fileId}`、`/api/uploads/{filePath}`；校验 HTTP、Content-Type 和响应字节，不把 raw 下载的 HTTP 200 JSON 错误当音频。
- **实际/预期**：A 的证据已实测 pending resource、pending static、deleted resource 匿名为 200。B 源码核对显示三路均没有完整审核/删除/角色核验；B 完整 HTTP 矩阵未运行。共享 discovery 的已建议条件为登录、approved、未删除，不能依赖索引或 UI 按钮代替媒体授权；旧 owner/admin 审阅权限细节由 A 冻结。
- **影响**：不阻断受控回环开发；阻断对外 discovery 权限验收。只保护新增路由仍留下旧 raw/static 绕过。
- **最小建议路径**：由 A 协调 WebMvcConfig、上述两个 controller、统一资源可见性 helper 与媒体调用 adapter。音频原始入口应受相同授权或停止对外服务；头像可保留独立、明确范围的静态策略。删除 `/file/download/**` 的拦截排除还需注意当前排除路径连 JWT 用户上下文也不设置。改受保护媒体时一并适配旧不带 JWT 的 createMusicUrl，不在本轮修改公共行为。

### P1：资源文件的一年缓存与审核撤销/删除冲突（既有策略风险）

- **位置**：[MusicResourceController.java:502](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/controller/MusicResourceController.java#L502)：`Cache-Control: max-age=31536000`，同一 URL 未按权限/状态版本化。
- **最小复现**：浏览器/缓存代理先获取资源，随后把资源改为 rejected 或 soft-deleted，再在正常缓存模式下请求同一 URL；同时用强制发网的新请求验证服务端状态，并验证 Range 和条件请求。
- **实际/预期**：当前源码明确允许长时间 freshness；B 未做缓存端到端复现。预期未来每次受保护的联网媒体请求都要核验最新状态，缓存策略不能允许继续无条件复用受控媒体。
- **影响/建议**：不阻断本地启动，阻断“撤销后不可继续通过服务获取”的对外保证。由 A 在受保护响应采用合适的 private/no-store 或明确受控缓存方案并测试；已下载字节无法被远程撤回，不能承诺抹去用户既有副本。raw/static 的缓存和 Range 需另验，不从 resource route 的设置推断。

### P2：分片重复持久化之前，还存在自定义批量 SQL 未注册的缺口（本轮补充）

- **位置**：[ChunkCacheService.java:46](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/service/ChunkCacheService.java#L46) 先 `save`，:78–87 又 `saveBatch` 且失败只记日志；FileChunkServiceImpl:43–47 转发到 [FileChunkMapper.java:15](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/mapper/FileChunkMapper.java#L15) 的 insertBatchSomeColumn。
- **静态证据**：整个 main source/resources 中，该方法仅有上述声明和调用；没有对应 XML、注解 SQL 或自定义 SqlInjector 注册。另只读核对官方 MyBatis Plus **v3.5.5**，commit `0240b1fdda5237ecaeba85774d9ab9a79d4c3fcb`：[DefaultSqlInjector:36–55](https://github.com/baomidou/mybatis-plus/blob/0240b1fdda5237ecaeba85774d9ab9a79d4c3fcb/mybatis-plus-core/src/main/java/com/baomidou/mybatisplus/core/injector/DefaultSqlInjector.java#L36) 不含 InsertBatchSomeColumn；该方法是 extension 中另行选择的实现。本轮通过 Git 获取该官方固定 tag 核对，没有改变项目依赖。
- **最小复现**：在真实配置启动后，不用 mapper mock，调用一次 FileChunkService.saveBatch；先验证 `Configuration.hasStatement("com.taffy.music.mapper.FileChunkMapper.insertBatchSomeColumn")`。再上传一片并触发 missing-chunks/合并的 commit，区分 BindingException、重复键、成功写入和缓存清理。B 未运行此集成复现；从当前注册路径推断真实批量调用会遇到未绑定 statement，不能把该推断伪装成 B 日志。
- **实际/预期**：源码先写入的记录仍留缓存；后续批量路径既缺映射，又可能对已写入实体重复 insert。FileChunkServiceImplTest mock 了自定义方法，ChunkCacheServiceTest mock 了 service，不能验证真实 SQL 绑定或事务回滚。A 文档中的“重复分片持久化日志”不足以单独证明故障类型。
- **影响**：A 的小样本仍可能因即时 save 成功而完成；可靠恢复/并发/索引输入验收不能依赖该路径。缓存失败后保留、即时保存异常被吞，ACK 持久性需负例验证；不据此否定 A 已记录的 happy path。
- **最小建议路径/断言**：A 在 ChunkCacheService、FileChunkServiceImpl、FileChunkMapper 选择单一持久策略；如果保留即时 save，就避免后续重复 insert 并明确失败传播/缓存清理；如果保留批量，明确注册、幂等及恢复。验证同一分片重复提交只有一条记录、真实 SQL 可绑定、写失败不谎报 durable success、重启后 missing-chunks 与字节一致。不要仅注册一个批量方法后留下两次写入。

### P2：合并 MD5 只计算未比对，不能支持上传完整性结论（既有未修问题）

- **位置**：[FileUploadController.java:280](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/7ab0d39d920a538b28878cf92ecbe90e55994ec3/music/src/main/java/com/taffy/music/controller/FileUploadController.java#L280) 计算 mergedFileMd5 后未与 fileUpload.fileMd5 比较，:290–294 写完成；:183 只保存传来的 chunkMd5。
- **最小复现**：合成 fixture 的实际 MD5 与 create 声明值故意不同，正常提交真实片段并 merge；再单独使用错误 chunkMd5。断言不应进入 completed，也不应被 /check 误认作完整可复用文件。B 未运行 HTTP 负例。
- **实际/预期**：源码路径可在没有哈希一致性判断时标完成；A smoke 比较了成功样本最终字节，但没有覆盖声明哈希错误。预期错误输入明确失败、无不完整的完成状态，并有可恢复清理策略。
- **影响/最小建议路径**：不阻断离线探索；可靠上传完整性和按客户端 MD5 复用的验收受阻。由 A 在 FileUploadController 的 chunk/merge 边界补比对及恢复语义，并协调测试；后续索引 content_sha256 必须从实际文件计算，不能复用客户端 MD5。没有给新管线另立版本或更改数据库。

## 媒体矩阵与 Range 覆盖

`S/U` 表示**静态路径未见资源授权/审核状态过滤，B 本轮 HTTP 未验证**；不是“实测 200”或权限 passed。条件：物理文件存在、file_upload.status=1 且 deleted=0；deleted 列表示 music_resources 的软删除，上传记录仍活跃。文件物理删除或 file_upload 逻辑删除不属于这个状态，不混为同一用例。

| 调用身份 | 资源状态 | resource file | raw file download | static uploads |
|---|---|---|---|---|
| anonymous | pending | S/U | S/U | S/U |
| anonymous | approved | S/U | S/U | S/U |
| anonymous | rejected | S/U | S/U | S/U |
| anonymous | deleted | S/U | S/U | S/U |
| owner | pending | S/U | S/U | S/U |
| owner | approved | S/U | S/U | S/U |
| owner | rejected | S/U | S/U | S/U |
| owner | deleted | S/U | S/U | S/U |
| other user | pending | S/U | S/U | S/U |
| other user | approved | S/U | S/U | S/U |
| other user | rejected | S/U | S/U | S/U |
| other user | deleted | S/U | S/U | S/U |
| admin | pending | S/U | S/U | S/U |
| admin | approved | S/U | S/U | S/U |
| admin | rejected | S/U | S/U | S/U |
| admin | deleted | S/U | S/U | S/U |

三条实际 URL 分别为 `/api/music-resources/{musicid}/file`、`/api/file/download/{fileId}`、`/api/uploads/{filePath}`；ID 不是同一个实体，不能互换。

| HTTP 证据来源 | resource file | raw download | static uploads |
|---|---|---|---|
| A 已提交的匿名观测 | pending=200、资源软删除=200 | 未记录 | pending=200 |
| B 本轮所有角色/状态 | 未运行 | 未运行 | 未运行 |
| Range | A 对 resource route 实测 bytes=0-31 →206，且内容范围和字节正确；B 未复跑 | controller 为手动输出流，没有 Range 分支；实际响应待测 | ResourceHandler 路径，实际 206/416/条件请求待测 |

需要 A 冻结的验收预期：共享 discovery 媒体必须登录且资源 approved、未删除，所有角色均不得利用 raw/static 绕过；owner/admin 的私有审阅如需例外，必须是明确授权策略。恢复后是否可见也应复核当前审核状态。测试每个身份/状态时同时检查业务码、实际音频字节、Range 206/416、有效/过期凭据与 Cache-Control，不能仅比较 HTTP 200。

## Git 交付与后续

- 初次终端写入验证 exit 128：`fatal: could not read Username for 'https://github.com': terminal prompts disabled`。首次检查没有 gh 或可用 Git 凭据；回执 `ae93346576ecb262a452a144c2e322d3fd2d1160`、审核 `12743e6490d53707f4437961b0fc2e43782a1837` 提交后两次脚本 publish 均 exit 1，内部 git push exit 128。这些是未推送的本地历史检查点；此前可导入 bundle 仍是旧版本备用，不能冒充本次远端 SHA。
- 用户随后接通 GitHub，核验身份为 KelvinChen-git、仓库 push=true，实际通过已授权接口创建本任务报告 blob 成功。B 在私有忽略目录安装校验过的官方 GitHub CLI 并启动设备登录；用户完成浏览器授权后，CLI 访问 `https://api.github.com:443` 被运行环境网络策略拦截，未保存 hosts.yml/token。再次原子 dry-run 仍缺 Username。没有尝试绕过网络策略，没有向聊天或报告输出凭据。
- 本次采用已授权 GitHub 接口备用交付：以 reviewed_sha 的 tree 为基底，只写获准两份报告；先创建 B 任务分支并读取核验，再创建固定 B feed。保留 music-handoff-v1、source_branch/source_sha/report_path/report_sha256 和已读 A feed 的 ack。此路径为**顺序发布，未提供脚本的两 ref 原子保证**；若第二步失败，只能记源码已发布、feed 未交付，不会把缺失 feed 当确认。首次 feed 的 commit 父提交指向本次 B 源提交，根目录仍只有两份协议文本；sync 不要求首份 feed 为 orphan。由 A 协调后续传输机制，不把这次备用路径记为 MUS-008 原子脚本已通过。
- GitHub 创建的源 commit SHA 与旧本地 SHA 区分；最终交付 SHA 由 feed 的 handoff.json 及远端核验确定，不在同一次提交中自引用。发布后核对 source 的两个文件内容、相对 reviewed_sha 的修改范围、feed 根文件、报告哈希及 fresh sync，再将本机工作分支与远端检查点对齐，保留旧本地分支以防丢失历史。没有 force push、main 更新、PR 或合并。

下一步由 A 串行处理：记录 B 已接收及本报告的实际交付状态；在可运行环境补齐后端/数据库/48 格媒体复验；协调媒体入口与缓存、上传单一持久策略/SQL 映射、哈希负例的后续范围。MUS-002 继续归 A，B 不接管模型 spike，不冻结 discovery 契约，不提前实现 MUS-003/004。

```text
任务 / owner：MUS-001-R1 / B。
分支 / base SHA / 报告 SHA：review/MUS-001-B-baseline / 7ab0d39d920a538b28878cf92ecbe90e55994ec3 / 最终提交号由交接命令给出。
ack_peer_feed_sha：d0a8381ee015077100f84354d3f39720da41c4de。
只修改文件：docs/reviews/MUS-001-B.md、docs/collaboration/account-b/latest.md。
实际完成：固定 feed 校验和一次性接入、slot B 配置及前端复跑、指定 diff/SQL/测试/媒体/分片静态审核、明确的媒体矩阵与最小后续断言。
接口 / schema / 配置变更：无；没有修复业务源码、改变依赖锁或更新 STATUS。
验证：npm ci/build、配置隔离/拒绝覆盖、Vite B 代理/strictPort、静态检查 passed；Java 两种测试各0执行，DB及smoke blocked，详见正文。
未验证：后端运行、真实SQL与批量映射调用、权限/缓存/Range矩阵、重启并发/损坏输入及真实邮件/试听。
数据 / 模型 / 索引：无新增版本或工件；V001 hash已核对；无检索质量/性能结论。
推送状态：终端两次publish失败/登录受网络策略阻塞；当前通过已授权GitHub接口采用源码先、feed后的顺序交付，最终source/feed SHA以远端核验为准。远端可读不等于A已读取。
下一步：A从固定B feed读取并确认、串行整合；由A协调后续传输机制；运行阻塞解除后按精确SHA补证。
文件占用：报告交付检查点后释放B两份报告的活动占用；B仍是其唯一写入方，后续更新先同步。未接任集成负责人，无PR/main推送/合并。
```
