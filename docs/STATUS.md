# 项目状态与交接

最后更新：2026-10-20（America/Chicago）。当前集成负责人：**账号 A**。STATUS 仅由当前集成负责人串行更新；账号 B 的报告由 A 整合。

## Git 与交付状态

- 仓库：`https://github.com/KelvinChen-git/Music-Resource-Management-System`。
- 最新远端检查（2026-10-19 17:34 America/Chicago）：A 源分支 chore/MUS-008-account-sync@0ba0a96、A feed collab/account-a@d0a8381、B 源分支 review/MUS-001-B-baseline@6e4118c、B feed collab/account-b@05d4e9f 均可读。main 仍为 b81f57c；无 PR / 最终合并。
- 五份协作文档原先均未发布；已在 `docs/multimodal-collaboration` 应用附件补丁，提交 `8f1fb6b`。逐字节核对与附件相同。原 aa720da 是旧会话提交，不能假设存在于当前 Git 历史。
- MUS-001 交付分支：`chore/MUS-001-dev-baseline`（HEAD 1b1faa1），基于上述文档分支；实现提交 `7ab0d39d920a538b28878cf92ecbe90e55994ec3`。MUS-002 检查点分支为 `spike/MUS-002-clap-feasibility`，基线 1b1faa1，HEAD 6e4140b。A 当前工作分支为 chore/MUS-010-dual-dev-baseline；未改动 MUS-002 分支。
- A 当前 GitHub 连接仍 permissions.push=false；受管终端 DNS 仍阻塞。用户已在普通 Mac 终端成功发布 A 源码 / feed；B 已从固定入口读取并主动 ack。B 用可写 GitHub 接口顺序发布其源码 / feed；不能声称双方终端自动发布都通过。本次 A ack 仅本地更新、尚未发布。
- MUS-008 工作分支：chore/MUS-008-account-sync，base 6e4140b，已发布检查点 0ba0a96。本轮 A 接收 B feed 05d4e9fe7c9528923796ef46508cadb05e94bd1b / source 6e4118cc316e95d2ba0f3c1fc1cf7ae15fecefbc，核验报告哈希、源码副本、审核基线和仅两文件 diff；与此前导入的 b81f57c 首轮报告区分。

## 能力与证据

| 内容 | 状态 | 证据 / 限制 |
|---|---|---|
| Java / Vue 旧管理系统 | 源码存在，部分流程实跑通过 | 注册登录、标签分类筛选、上传合并、MP3 元数据、软删除恢复 |
| 前端依赖 / build | passed | Node 22.23.3 / npm 10.9.9；现有 lockfile；非阻塞 bundle 警告 |
| Java 单测 | passed（当前本机 A/B 各 107） | 用户普通终端两个独立 checkout 均 10 类 107，0 failures / errors / skipped；B 账号此前独立审核测试仍执行 0，两者区分 |
| 空开发库 / local 启动 | passed（原生 MySQL） | V001 建立 11 表；重复初始化拒绝；Compose 未执行 |
| API 直连 / 开发代理流程 | passed（本机 A/B） | 两个独立 checkout 各直连 13 / 代理 13，真实 Range 206；见 MUS-010 四份原始结果 |
| 两套本地环境隔离 | 实跑 passed | A 复用已有库，独立 B worktree 新建空库各 11 表；六端口同时监听。此本机代跑不冒充 B 账号独立验收 |
| 媒体入口权限 | 本机修复实跑通过 | MUS-011 两套环境匿名三入口均 401；上传所有权与 B 独立审核仍待完成 |
| CLAP 文本 / 音频编码 | 可行性 passed | 固定 checkpoint CPU 严格加载，实际 512 维，合成输入，9 项预处理测试；有网 / 缓存离线复跑通过 |
| Python 检索 / 索引 / 搜索界面 | 未实现 | 只有离线探针；未冻结 discovery-v0 |
| 30–50 / 2,000 首，约 70,000 片段，120 查询 | 计划 / 算例 | 未导入或标注；合成 smoke 不是音乐语料 |
| 质量、P95、并发和提升比例 | unmeasured | 不得写作已完成成果 |

详细命令与机器生成结果见 [verification/MUS-001.md](verification/MUS-001.md)。旧会话网络阻塞只是历史：本轮 Maven 已能下载和实跑。原始默认 75 tests 有 3 errors；修正 fixture 后才得到全量 89 tests 通过。

## 任务与占用

状态仅 todo / in_progress / blocked / review / done。A / B 为当前角色；未最终合并不自动代表所有内容完成。

| 任务 | 状态 / owner | 分支 / 基线 / 依赖 | 允许修改与验收 |
|---|---|---|---|
| DOC-001 协作文件 | review / A | docs/multimodal-collaboration / b81f57c | 五文件已应用并包含于远端 A 源码历史；main 未合并 |
| MUS-001 可重复开发基线 | review / A | chore/MUS-001-dev-baseline / b81f57c + 8f1fb6b；依赖 DOC-001 | A 的空库、local 启动、测试、build、smoke 通过；B 静态审核 / 前端 / 隔离通过，独立后端运行补证 blocked |
| MUS-001-R1 基线与媒体审查 | done / B（审核交付完成，后端运行补证未通过） | review/MUS-001-B-baseline / 7ab0d39；delivery 6e4118c | 只新增 B 审核正文和 latest；B feed 05d4e9f 已由 A 核验。48 格媒体矩阵均明确未运行，不将文档表格当测试通过 |
| MUS-002 模型 spike / 契约冻结 | blocked / A | spike/MUS-002-clap-feasibility / 1b1faa1；已测探针 ab5d6f3 | services/audio-search/ 与 docs/model-spike.md；准确 checkpoint / 预处理 / 实际输出 / 依赖锁；素材和效果未验证前不冻结 |
| MUS-003 切片与索引 | todo / unassigned | MUS-002 | 冻结契约后的 Python 模块，边界测试与精确检索 |
| MUS-004 搜索界面 | todo / unassigned | MUS-002 | web discovery 页面；先明确 fixtures，禁止自行假设 API |
| MUS-005 Java 集成与权限 | todo / unassigned | MUS-003 / 004，及媒体权限治理 | 检索 gateway、可见性复核、旧匿名路径治理、片段试听 |
| MUS-006 评测 | todo / unassigned | MUS-005 | manifest / qrels / dev-test / 基线和原始结果，不预填指标 |
| MUS-007 恢复 / 扩容 / 演示 | todo / unassigned | MUS-006 | 根据瓶颈推进，不先堆基础设施 |
| MUS-008 固定交接与同步 | review / A（原生 git 发布 / 同步已验收） | chore/MUS-008-account-sync / 6e4140b | A/B feed 均已发布，B 完成 sync / ack，A 本轮直接读取 B；9 项脚本本地 Git 检查通过。A后续原子publish / sync已成功；B新审核须按独立任务回传确认 |
| MUS-009 上传完整性 | blocked / A（正常 SQL 已补证；故障 / 并发 / 重启验收未完） | fix/MUS-009-upload-integrity / 83b9402 | 107 tests 通过，MUS-010 两环境正常上传 / 合并实跑通过；失败回滚、并发与进程重启仍待真实验证 |
| MUS-010 两套前后端开发基线 | done / A（本机运行验收） | chore/MUS-010-dual-dev-baseline / f15d842 | 普通终端 A/B 独立 worktree 各 107 tests、build、11 表、直连 13 / 代理 13；六端口监听。B 账号独立审核 / 远端发布另列，不代表 main 合并 |
| MUS-011 媒体授权 / 缓存 | review / A | fix/MUS-011-media-access / 4369089 | 266 Java（含 144 个模拟 HTTP 组合）、6 前端 helper、build、8 启动保护通过；原始下载 / ZIP / 静态 / 元数据重绑定均校验。本机 A/B 各 144 真实矩阵 + 8 附加检查通过；上传持久所有权、B 独立审核待完成 |
| MUS-012 上传持久所有权 | review / A（本机矩阵通过；B request_changes，待MUS-013复核） | fix/MUS-012-upload-ownership / dbdcae2 | 308 Java / 22 Python 通过；owner / MD5 / 首次绑定 / 头像隔离；A/B V002 已迁移且旧 owner 保持 NULL，两套本机各 65 上传 / 144 媒体检查已通过 |
| MUS-012-R1-B 媒体与上传所有权独立审核 | review_completed / B（request_changes） | review/MUS-012-B-access-ownership / d7c9faa | 仅 B 审核正文与自身 latest；任务卡由 A 发布，B 独立记录运行 / 阻塞，不将本机 B 槽当其确认 |
| MUS-013 B审核发现修复 | review / A（本机修复后实跑通过，B增量待复核） | fix/MUS-013-b-review-findings / 6a29de4；实现c100fd6 | Java317 / Python28通过；R1/R2旧服务已复现，两套各修复后HTTP11 / 临时库8已通过 |
| MUS-013-R1-B 增量复核 | assigned / B（待确认） | review/MUS-013-B-review-findings / c100fd6 | 仅新B审核正文与own latest；复核R1/R2/R3和profile字段更新、脚本隔离 |

### MUS-001 A 路径范围（review 检查点）

`AGENTS.md`、`README.md`、`docs/PROJECT.md`、`docs/CONTRACTS.md`、`docs/STATUS.md`、`docs/development.md`、`docs/verification/MUS-001*`、`docs/handoffs/MUS-001-B.md`、`.gitignore`、`.nvmrc`、`compose.dev.yml`、`scripts/dev.py`、`scripts/smoke.py`、`music/pom.xml`、`music/src/main/resources/application-local.yml`、`music/src/main/resources/db/baseline/V001__development.sql`、`music/src/main/java/com/taffy/music/domain/MusicResourceTags.java`、`music/src/main/resources/mapper/MusicResourceMapper.xml`、`music/src/test/java/MusicResourceServiceImplTest.java`、`web/vite.config.js`、`web/.env.example`。

扩展到 mapper / 单测的原因是实跑暴露 JSON 返回 null 和三项无效测试前提，详见验证文档。没有更改前端 lockfile 或重写业务服务。B 不在这些路径直接修复；需要扩大范围时先将具体路径交给 A 协调。

B 独占 `docs/reviews/MUS-001-B.md` 与自己的 `docs/collaboration/account-b/latest.md`；A 不创建这两份报告或 B feed。首次报告只导入独立 imports 路径，以免伪造 R1“已审核”。正式任务见 [handoffs/MUS-001-B.md](handoffs/MUS-001-B.md)。

## 未解决事项

| 编号 | 当前事实 | 后续 |
|---|---|---|
| B-01 | 缺配置 / proxy 硬编码已解决；可重复命令已建立 | B 复跑；Compose 仍未实跑 |
| B-02 | 空库 V001 已验证；历史 SQL 保留，不可顺序执行 | 既有数据库迁移另立任务；分类 ID Java 类型差异待审 |
| B-03 | 旧匿名媒体 / 静态路径 / 删除后访问问题已实证 | MUS-011 本机两套真实矩阵已通过，三匿名入口均 401；独立复核及上传归属仍待完成 |
| B-04 | 默认测试遗漏 / 跨版本测试依赖已解决 | 全量 89 tests 通过；不代表全业务 / 全权限覆盖 |
| B-05 | 分片即时 save 后又 saveBatch；自定义 insertBatchSomeColumn 在项目中没有 SQL / 注入注册 | B R1 与 A 静态核对确认代码缺口；真实 SQL 调用、写失败 / 重启负例待补证。另保留 Druid POM / JSqlParser 诊断，不将所有批量失败归因于重复键 |
| B-06 | 无许可明确的真实音乐 manifest / 查询 / qrels | MUS-002 素材获取与效果评估前提；不能用静音样本替代 |
| B-07 | A 连接只读、受管终端 DNS 阻塞；用户普通终端发布成功。B 可写接口已发布、终端认证仍受阻 | 协调可写连接 / 可联网执行环境；本次 A 回执仅本地更新。无需反复修改已验证无效的配置 |
| B-08 | MD5 合并后计算但未校验请求哈希；续传未做进程重启验证 | 后续上传完整性任务，不能宣称全面可靠 |
| B-09 | B 首轮新增上传无归属、ID / 文件大小窄化、ID3v2 元数据依赖、导出可能仅 20 条、202 envelope 适配等静态发现 | 见 collaboration/B-INITIAL-REVIEW.md；尚未对本轮实现逐项复现，分别纳入 MUS-002/003/005 后续 |
| B-10 | 双方固定 feed 已启用；B 已 ack A，A 本轮已读取 B | A 远端回执待发布；共享交接可用不等同完全自动发布通过 |

## 下一检查点与交接

1. A 已接收并核验 B feed 05d4e9f / source 6e4118c；B 审核交付完成。本次 A ack / STATUS 仅本地更新、尚未发布；未擅自合并 B 报告分支或 main。
2. 将后端补证放到可运行的隔离环境；先明确媒体授权 / 缓存、分片单一持久策略 / SQL 绑定、哈希负例的最小修复边界。B 环境缺依赖，不反复执行相同阻塞命令充当进度。
3. A 已完成 MUS-002 离线编码可行性实跑，独立 spike 分支和占用已建立；共享 API / schema 仍须冻结后才让 MUS-003 / 004 并行。
4. 外部公开检索之前解决媒体绕过；最终合并由用户决定，不直接 push main 或 force push。

交接必须写：task / owner、branch / base_sha / delivery_sha、推送状态、修改路径、命令及结果、未执行检查 / 原因、未完成内容、模型 / 数据工件位置与哈希、下一任务、文件占用与负责人。额度不足时先提交并停在明确检查点；本地 commit 不等于另一账号已收到。

## MUS-002 本轮占用

- owner A；branch spike/MUS-002-clap-feasibility；base 为 MUS-001 交接文档提交（`git log -1 chore/MUS-001-dev-baseline`），实现基线 7ab0d39。
- allowed_paths：`services/audio-search/`、`docs/model-spike.md`、`docs/STATUS.md`、必要的 README / PROJECT / CONTRACTS 事实更新；不修改 MUS-001 已冻结实现或 B 的审核报告。
- 先验证官方 music checkpoint、预处理和 CPU 编码，记录实际依赖与输出；真实许可语料 / 查询 / qrels 尚缺，不报告音乐效果，不冻结 discovery-v0。

### MUS-002 当前检查点

- 探针代码提交 `ab5d6f3697f37ecfbc96c3aa062a7f2b6702ca6d`；checkpoint music_audioset_epoch_15_esc_90.14.pt，HTSAT-base / no fusion，文件哈希与官方 LFS 元数据一致。Python 3.12 / macOS arm64 / CPU 实跑，实际文本与音频均为 512 维，float32，范数约 1。
- 9 项预处理测试、pip check、有网缓存运行与 HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE 复跑通过。源码 / 安装包哈希、准确版本和单次观测见 model-spike.md / verification/MUS-002-probe*.json。
- SDK 默认 repeatpad / rand_trunc 与候选短尾段零填充不同，探针先显式补到 480000 点；44.1→48kHz 浮点多一采样点问题以整数长度修复。
- blocked 原因：尚无来源 / 许可 / 内容哈希明确的真实音乐 manifest、相关性标注和真实查询。合成波形只证明模型能运行，不能据此冻结音乐检索方案。Python MP3 / WAV 解码亦未验收。
- 没有索引、线上检索 API、新界面或质量 / P95 结果。保留 MUS-002 owner A，等待语料与效果验收；B 只审 MUS-001。MUS-003 / 004 不提前并行写 API。

## 2026-10-19 B R1 接收评估

- B 交付审核的是 7ab0d39，不是旧 main；相对该基线仅有两个报告文件变更，未改实现、STATUS、schema 或锁文件。B 最新报告已 ack A d0a8381。
- A 核验 B feed 报告 SHA-256 为 31ac8198e0eefac154e1479bb7f46c9f1782cbcdd5f6908911e6d6fd35eca20a，与 B 源提交内副本一致；feed 根目录仅 handoff.json / latest.md。
- B 的配置与前端复跑通过；Maven DNS、缺 MySQL / Docker 导致 Java 测试及后端功能检查实际执行 0。MUS-001-R1 的 done 仅表示审核报告交付与接收，不代表 MUS-001 的独立后端验收完成。
- P1 媒体三入口与一年缓存风险保持阻断公开 discovery。P2 分片重复持久化 / 批量映射缺口、MD5 未比对需要运行负例，不能用 89 项单测概括为已覆盖。
- 本轮不新增业务修复或替 B 创建报告；B 两份报告活动占用已释放，其唯一写入方仍为 B。A 继续串行维护台账。后续先补运行证据 / 最小修复，再推进真实许可语料与 MUS-002；MUS-003/004 不提前冻结接口。

## MUS-009 上传完整性（本轮占用）

- status blocked（实现与单测完成；真实数据库补验未通过）；owner A；branch `fix/MUS-009-upload-integrity`；base `83b94029412d12b52e3fd1e3a0938357b1bde782`。B feed 仍为 05d4e9f / source 6e4118c，无新占用冲突。
- allowed_paths：FileUploadController、FileChunkService / Impl / Mapper、删除旧 ChunkCacheService、新 UploadIntegrityService 及对应 Java 测试；`scripts/upload_integrity_smoke.py`；README、CONTRACTS、STATUS、A latest、`docs/verification/MUS-009*`。不改 B 报告、schema、依赖或锁文件。
- 验收：分片同步一次写库，写失败无成功 ACK；按实际字节校验分片 / 合并 MD5 与总大小；重复同内容上传不重复计数，冲突内容不覆盖；数据库行锁串行化同文件上传 / 合并，计数和分片同事务；重启后从数据库续传；合并失败保留可重试分片并删除未发布目标。
- 公共旧路径 / envelope 保留；详见 CONTRACTS A3。上传归属、媒体授权 / 缓存、已有数据库迁移和全面磁盘垃圾回收不在本任务；最终 merge 由用户决定。

### MUS-009 检查点与剩余工作

- 旧 base 负例 2/2 复现：错误分片哈希和 save=false 均 code=200。新实现 clean test 105 通过，补两项边界后全量 107 通过；其中新控制器 2 / 服务 23。已移除旧缓存 5 项和虚构批量映射 2 项测试；不是将 107 全部算新增。
- B-05 / B-08 已有最小修复及单测，真实 MySQL SQL / 事务回滚、跨请求并发和后端重启仍未验收，不能将 unresolved 直接标为 done。新两阶段 smoke 脚本已建立，HTTP 功能检查实际执行 0。
- 当前 JDK / Maven 缓存可离线运行；MySQL 8.0.41 初始化原生 signal 11，HTTP 回环 Errno 1 Operation not permitted。未改已有 schema、未重新初始化库。准确证据 / 命令见 verification/MUS-009.md 与 JSON。
- 下一步由可运行环境补验并请 B 针对本任务最终提交审核；B 未确认，不自动占用其实现路径。媒体权限 / 缓存仍为 P1，公开 discovery 继续阻断。本任务待推送结果见 A latest；最终合并由用户决定。

- MUS-009 实现已本地提交 `949603fe45e3f90637dd7dc2578e41f80945afb5`。实际 publish 在 ls-remote exit 128 阶段失败；单独确认 github.com DNS 无法解析，未推送任何源码 / feed。本地工作检查点不是 B 已收到；网络恢复后在任务分支重试 publish。

## MUS-010 前后端 / 两账号开发基线（本轮占用）

- status done（本机两套前后端实跑通过）；owner A；branch `chore/MUS-010-dual-dev-baseline`；base `f15d842344f8df0b251f90d65811206efb589555`。优先跑通数据库、Java、Vue 及直连 / 代理 smoke；暂停新业务扩展。
- allowed_paths：`scripts/baseline.py`、必要的启动辅助测试、README / development / STATUS / A latest、`docs/verification/MUS-010*`。不改业务实现、schema、依赖锁或 B 报告。
- 验收：隔离 slot、工具可用、空新库初始化 / 已有库不覆盖、后端与 Vite 启动、直连和代理各 13 检查；A/B 各自独立 clone 或 worktree。A 本机代跑 B slot 不算 B 账号独立确认。
- 当前受管终端 Python socket bind/connect(127.0.0.1) 均 Errno 1，DNS 亦失败；这是本轮已测阻塞。继续完成无需端口的构建与可复现入口，不重复启动 MySQL 崩溃充当进度。

- MUS-010 本轮 Java 显式全部测试 107、Vue build、启动入口 8 项保护检查通过；完整入口在 A/B 的 socket 预检 Errno 1 停止。真实数据库 / 直连 / 代理功能执行 0，不能将构建通过当联通通过。详见 verification/MUS-010.md / JSON。
- 本机准备独立 B worktree Music-Dev-B-MUS010，供普通终端代跑 slot B；不更改 B 远端报告，不代表 B 已验收。下一步优先取得两个 checkout 的 result.json；暂停新业务和真实语料扩展。

- MUS-010 启动入口提交 e89b4db4496b13ab28ab6944f1db82c600d80066；已实际创建独立 B worktree，并在该目录全新生成 slot b 配置，B 预检仍明确 Errno 1。publish 实际在 ls-remote exit 128 阻塞，未进入推送；远端无本轮新交付。

### MUS-010 普通终端实跑接收（18:18–18:19 America/Chicago）

- 用户运行后，A 读取原始 result.json、逐字比对四份 smoke 日志并核对 Java 汇总；A@699da38、B worktree@e89b4db 的代码只差三份交接 / 验证文档，业务与启动入口相同。
- 两边各 Java 107 / build passed、11 表、直连 13 / 代理 13。A 复用已有库，B 全新空库初始化；6 个服务端口仍监听。真实结果及哈希见 verification/MUS-010-live-results.json 和四份 smoke JSON。
- 本机两套开发基线 done；此前受管进程 Errno 1 保留为历史，不推断受管网络已恢复。普通终端已经能正常运行 MySQL，不再把原生崩溃视作本机整体不可用。
- B 账号独立审核、MUS-009 故障回滚 / 并发 / 进程重启、公开媒体权限和自动远端发布均未因本轮通过而完成。B npm ci 的 20 个依赖漏洞、既有 JSqlParser 优化警告单列待查，不在本轮自动升级依赖或改业务。

## MUS-011 媒体访问与缓存（本轮占用）

- status review（实现及两套本机真实服务矩阵通过；B 独立审核待完成）；owner A；branch `fix/MUS-011-media-access`；base `436908938989ba4d331b90e2795a8a5f3f702bb2`。开始时 GitHub 新鲜读取 B feed 仍为 05d4e9f，无新路径占用。
- allowed_paths：MusicResourceController / FileUploadController、新静态上传控制器；WebMvcConfig / JwtAuthenticationInterceptor / GlobalExceptionHandler；新 MediaAccessService / MediaResponses、MusicResourceServiceImpl 的既有关联元数据重绑定检查及测试；web api/music.js、utils/media.js 及测试、MusicListView / FileListView；scripts/smoke.py / media_access_smoke.py / baseline.py（增加权限实跑验收步骤）；README / CONTRACTS / STATUS / A latest / verification/MUS-011*。
- 验收：资源 / 原始下载重新校验当前登录用户、审核与删除状态；静态路径不能提供音乐；成功 / 拒绝 / Range / HEAD 不长期缓存，匿名不能计数；保留合法头像和前端携带 JWT 的播放 / 下载；矩阵与基线回归。策略先记入 CONTRACTS A4。
- 不改 schema、上传归属、依赖锁、B 报告、MUS-002；既有浏览器已下载字节无法追溯收回，不声称 no-store 可清除旧一年缓存。用户已在普通终端重启两套服务，新代码真实矩阵通过。

### MUS-011 检查点

- 已实现 CONTRACTS A4：当前账号与审核 / 删除状态、受控真实路径、no-store、静态仅登记头像、ZIP 与既有元数据重绑定检查；播放 / 下载显式 JWT。
- 全量 Java 266 / 0 failures / errors / skipped（原107 + HTTP155 + 重绑定4），前端 helper6、build、baseline guards8通过。155中144为MockMvc组合，另含实际WebMvcConfig，不冒充TCP / 真库矩阵。
- 两个普通终端已加载新代码；A aa65efa / 本机 B d29ccbb（仅三份文档不同）。各 266 Java / build、直连和代理各 13 功能 + 4 安全、144 真实组合 + 8 附加检查均通过。A 已直接读取原始日志并核对汇总，无需搬运。
- 补充发现：file_upload 无 owner，未关联上传首次归属 / 抢先绑定与上传写授权仍需 schema / 迁移任务。本次仅对已有资源引用加防重绑定；不能据三入口修复称整个上传权限已安全，公开 discovery 保持阻断。B-03 / B-09 不直接标 done。
- 证据见 verification/MUS-011.md / JSON。未修改依赖锁、schema、B 报告、模型 / 语料；真实媒体矩阵已完成；后续补上传所有权，再补 MUS-009 失败 / 并发 / 重启续传。

- MUS-011 实现提交 d29ccbb，已在干净工作区将本机独立 B worktree detach 同步到该提交；两套服务重启后的真实验收已完成。上次发布阻塞已恢复；本轮 396deda 源码 / 验收报告和 feed f00c35d 已成功发布并 sync 回读核验。远端 B 仍为 05d4e9f / source 6e4118c，不能声称 B 已读取或独立审核。


### MUS-011 真实运行归档（2026-10-19 America/Chicago）

- A run baseline-20261019-184734-83428；本机 B run baseline-20261019-184759-83718，整体均 passed。六份原始 JSON 与 MUS-011-live-results.json 已归档；原始日志 / 内嵌 JSON 一致，144 元组唯一且状态正确。每套 36×401 / 72×404 / 24×200 / 12×206。
- 三个匿名入口由历史 200 变为 401；授权 GET / Range、HEAD / 计数、头像与元数据反重绑定通过。每份后端日志的三个“文件不可用”属预期拒绝用例，无 SQLSyntaxErrorException / BindingException。
- 仍为 review：本机 B 槽通过不代替 B 账号独立审核；未处理上传持久所有权、首次抢先绑定、上传写授权、事务失败 / 并发和跨进程续传，不代表公开 discovery 可开放。

- 发布核验：2026-10-19 19:41 America/Chicago，原生 git publish 与 sync 均成功；当前任务分支可由 B 的同步入口获取。最终报告提交继续发布到同一分支，不触碰 main，不代写 B 的报告。


## MUS-012 上传持久所有权（当前占用）

- owner A；branch fix/MUS-012-upload-ownership；base dbdcae2cbbce4aeb7ee25418f9c3464de63ebe73；status review（实现、自动测试及两套本机真实 HTTP 通过；B 独立审核待完成）。开始 sync 确认 B feed 仍为 05d4e9f，未见新占用。
- allowed_paths：FileUpload / FileUploadController / FileUploadServiceImpl、新 UploadAccessService、UploadIntegrityService、MediaAccessService、MusicResourceServiceImpl / metadata controller 异常传递、对应测试；UserServiceImpl / AuthController 的头像绑定校验与测试；db/baseline/V002*、scripts/dev.py / baseline.py / 迁移及权限回归脚本与测试；README / CONTRACTS / STATUS / A latest / verification/MUS-012*。
- 契约见 A5；目标为所有上传操作隔离、首次绑定防抢先、旧记录隔离且可安全迁移、原媒体读取回归。保留 B 报告、依赖锁、main；真实事务故障 / 并发 / 重启恢复后续单列，不冒充本批通过。


### MUS-012 实现检查点（真实验收前的历史记录）

- 308 Java（原266 + 新所有权HTTP40 + MD5隔离2）与22 Python（baseline9 / migration4 / collab9）通过。真实持久化不在 MockMvc 中，不能据此称完整验收。
- A 真库 V002 已加列 / 索引并重复迁移通过，10 条旧上传保持 NULL；本机 B 干净同步至实现提交078a82b后已迁移成功，6条旧上传保持NULL。无 owner 自动回填。头像登记也检查目标账号上传归属，引用上传不允许删除，删除仅逻辑标记、保留字节。
- 候选 Java 连接 127.0.0.1:3307 被 Operation not permitted 拒绝，未成功启动；18080 候选已停止。原 8080 / 8081 服务仍为 MUS-011。Python / native mysql 可连不代表 Java 可连，新真实65项权限回归未通过。
- 普通终端新 baseline 将自动执行该回归；原终端各 Ctrl+C 后以 --migrate-upload-ownership --keep-running 运行。A 可直接读取结果，无需搬运。本机 B 槽非 B 账号审核；后续事务故障 / 并发 / 重启续传仍待验证。

- 实现提交078a82b已发布，A feed检查点8ead126；本机B源码一致，两个旧Java PID83691 / 83977仍为旧运行实例。发布/迁移不等于新版本实跑验收，不要求B账号替A搬运输出。


### MUS-012 真实验收完成（2026-10-19 America/Chicago）

- A run baseline-20261019-201252-87403 / source4b3ec3f；本机 B run baseline-20261019-201303-87689 / source078a82b，整体均 passed。两个版本仅四份文档不同，运行源码一致。
- 两套各 308 Java / Vue build、直连和代理各13功能+4安全、144真实媒体矩阵+8附加项、65真实上传权限检查全部通过。每套35个显式拒绝为7×401 / 7×403 / 21×404，拒绝后计数 / 分片未变；原始JSON与内嵌汇总一致。
- 两份新后端日志均无 SQLSyntaxErrorException / BindingException / CommunicationsException；用户普通终端已加载新代码，历史候选Java阻塞不再是本轮验收状态。服务保持运行，无需重启或搬运。
- 八份原始JSON与MUS-012-live-results.json已归档。当前仍review：B账号独立审核未完成；遗留owner隔离、物理垃圾回收及MUS-009故障回滚 / 并发 / 跨进程续传仍单列。服务重启不等于上传中断恢复通过。


## B 首次固定领取任务：MUS-012-R1-B（已完成，当前见MUS-013新卡）

- A 发布任务，owner B；assignment_revision 1；reviewed_sha d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea；status assigned，未认领。开始时 sync 的 B feed 仍为05d4e9f / source6e4118c，不冒充B主动确认。
- 固定任务入口 `docs/collaboration/tasks/account-b.json`，正文 `docs/collaboration/tasks/MUS-012-R1-B.md`；必须按 A handoff.source_sha 读取。任务分支 `review/MUS-012-B-access-ownership` 从 reviewed_sha 创建。
- B允许写 `docs/reviews/MUS-012-B.md` 与自己的 `docs/collaboration/account-b/latest.md`；业务源码 / schema / 契约 / A STATUS 不归B修改。先回传claimed与实际ack_peer_feed_sha，再审查并回传最终verdict和证据；发现问题交A修复。
- A下一实现范围为MUS-009故障回滚 / 并发 / 重启恢复，暂未在本轮开启新业务修改；避免在B审核期间重写其准确审核对象。
- 后续A每次完成交接时维护B固定任务入口：有在途任务保留task_id / revision，不因新A feed重复分配；任务变化显式增加revision或新task_id。B的claimed / completed须来自B feed，不能由A根据时间推断。当前协议无后台唤醒，用户只需首次启动B读取固定入口。


## MUS-013 B审核发现修复（当前占用）

- owner A；branch fix/MUS-013-b-review-findings；base6a29de4cab2da6ac149b816165b5f058612bd133。ack B feed31b564b7cce09994ec661c48b7544964ebabb052 / source21d002c7592f21a81b8fc715bdc245ad1ae3ee6c，reviewed d7c9faa，verdict request_changes。
- MUS-012-R1-B已由B主动claimed并完成，运行补证partial_pass / backend_blocked；A承认B的Python22 / Node6 / build独立运行、Java0（Maven DNS阻塞），不把A的真库结果计入B。
- 接受R1旧JPA硬删、R2管理员createUser头像、R3迁移结构保护三项发现；前两项先作为静态确认，真实HTTP复现单列。附加profile完整实体回写风险作同范围最小字段更新，不声称已复现并发故障。
- allowed_paths：MusicController / MusicService、UserController / UserServiceImpl，相关Java测试；scripts/upload_ownership_migration.py / baseline.py及测试、新替代入口回归脚本；README / CONTRACTS / STATUS / own latest / verification/MUS-013* / collaboration/tasks增量卡。B两份报告只读，不覆盖、不伪造批准；依赖锁、schema SQL、main不修改。
- 故障回滚 / 并发 / 重启续传先让位这些审核阻断修复，后续继续。新复核卡必须针对准确修复SHA发布，不能让B审核尚未提交的HEAD。


### MUS-013 修复与验证检查点

- R1停用旧DELETE /music/{id}，有效账号410，当前账号校验保留；MusicService不再调用JPA硬删。R2新建用户重新核验管理员并拒绝预设avatar，空白归一NULL；profile只写name/avatar/updated_at。
- R3迁移在写入前校验准确11表集合、file_upload必要列/主键和owner列默认/可空/非生成与索引顺序/非唯一/BTREE。V001/V002 SQL不改。
- 旧服务中R1/R2已由A用合成fixture真实复现：他人旧DELETE204、主记录0、原始文件200、重新绑定成功；createUser插入avatar后图片匿名200。该绕过账号已删除，恢复资源引用并软删除，临时管理员降权；不是固定版本验收。
- Java317 / 0失败错误跳过，Python28通过；现有V002加严校验只读通过。独立临时MySQL初始化在当前受管进程失败，8项真库探针尚未执行，且没有连接现有库。新11项修复后HTTP验收未执行，不能以旧308/65/144矩阵概括。
- 新baseline已接入独立临时数据库8检查、修复后HTTP11检查，普通终端两端重启后自动运行。故障/并发/重启任务仍待后续，不冒充本批通过。


### MUS-013 实现提交与新复核派发

- 实现提交c100fd6510fe1061396be16973a7560ed2b89e7f；本机B干净工作树已同步至该提交，原Java进程未重启。新运行证据待普通终端补齐。
- 新卡MUS-013-R1-B / revision1，owner B，status assigned未认领；固定入口指向tasks/MUS-013-R1-B.md，reviewed_sha为c100fd6，比较d7c9faa。B只写docs/reviews/MUS-013-B.md与own latest，不重新认领已完成旧卡、不代写修复源码。
- A等待普通终端317 Java / 原基线 / 新8迁移与11HTTP证据，并接收B增量复核；故障/并发/恢复顺延。发布前不声称新卡已收到或已批准。


### MUS-013 普通终端修复后验收（2026-10-19 America/Chicago 21:30）

- A run baseline-20261019-213038-91461 / sourceda060d5；本机B run baseline-20261019-213013-91055 / sourcec100fd6均passed，源码仅8份文档不同。
- 两套各317 Java、Vue build、独立临时库8项、直连与代理各13功能+4安全、媒体144组合+8附加、上传65项、B发现修复后HTTP11项全部通过。原始JSON与内嵌汇总一致，媒体元组唯一且状态正确。
- R1旧DELETE410、资源引用1、raw404；R2 createUser400、创建行0、图片匿名401。旧服务复现与新服务结果分别归档，不再把历史受管环境阻塞当当前验收状态。新后端日志无SQLSyntaxErrorException/BindingException/CommunicationsException。
- 12份原始JSON与MUS-013-live-results.json已归档；服务保持运行，本轮无需重启或搬运。B新feed仍31b564b（旧MUS-012-R1-B完成request_changes），MUS-013-R1-B尚无主动确认/批准，固定reviewed_sha c100fd6和revision1保持不变，只补输入证据。
- 真实回滚故障注入、跨请求并发与上传中断后的进程恢复仍未执行，后续A任务继续，不能因本次普通重启标为通过。


## MUS-014 上传故障与受控重启验收（当前占用）

- owner A；branch test/MUS-014-upload-recovery；base d384a8fc66778ba24344f1ef19507db718872623。ack B feed bbae3797ec5dbafaed7e7bde28bb6951ed2c2db4 / source1534e4d6101c7a8e889fd22fdda036666fa82ac3。
- B增量复核sourcea6474f48eba669b70c88a24daa0a90cfc01dbc83已读：原R1/R2/R3和profile安全写列已关闭，新增R4脚本清理缺口request_changes；B后续获用户授权实施并交付R4最小修复。A不将其自交付当独立批准。
- A按B声明哈希导入两个脚本/测试原字节，独立Python39及真实HTTP11通过；B报告和main不改。没有Java/前端变更，不重复其已通过Java317。
- allowed_paths：scripts/review_findings_smoke.py / test_review_findings_smoke.py（导入B原字节）、新upload_fault_smoke.py及保护测试、upload_integrity_smoke.py、baseline.py及测试；README / CONTRACTS / STATUS / own latest / verification/MUS-014* / own任务派发。本轮并发探针已暴露计数错误，扩展Java范围至FileChunkService / FileChunkServiceImpl / UploadIntegrityService及相关测试；schema SQL和依赖锁不改。
- 目标：真实写失败回滚及可重试、计数/唯一行、并行上传与合并、部分上传跨JVM重启恢复；新基线自动控制自己的后端重启，不要求用户手动在prepare/resume间搬运状态。
- B提出的头像同值更新交错仍是静态风险，单列后续多连接验证，不冒称已复现或本批已解决。

### MUS-014 当前验证检查点

- A对运行中的c100fd6业务代码真实并发：file44有12行/12不同分片，持久uploaded_chunks仅10，API却显示12；失败证据已归档，私有JWT状态留.local且移至failed文件，不修写库中计数掩盖故障。
- 源码判断：身份查询可能在等待父上传锁前建立RR快照，锁后普通分片查询仍读旧快照。修复为持有父锁的事务内FOR UPDATE当前读，覆盖重复判断、计数和合并输入。当前Java317、Python45通过，尚未在新JVM真实复测，不把单元通过当并发缺陷已验收。
- 真实SQL INSERT/计数更新/合并发布失败与文件写失败、磁盘损坏/重试共18项，在A旧服务c100fd6通过，所有自建CHECK清理完成。不是新Java版本验收，也未模拟整库中断/提交ACK丢失。
- baseline新增prepare5项、只停止自己登记进程组、确认端口释放、启动新JVM并执行resume11项（12并发上传请求/2并发合并）。重启后真实结果待用户普通终端两槽启动；不在受管Java网络被拒环境中反复尝试。

- 实现提交7c973b5d9eac219e289623e7eb6d44eda73cb09d；新派发MUS-014-R1-B/revision1固定审核该SHA，比较d384a8f，尚未认领。前MUS-013-R1-B已由B完成request_changes并交付R4，不继续显示其为未确认任务。

### MUS-014 两套普通终端真实验收完成（2026-10-19 America/Chicago 23:18）

- A run baseline-20261019-231744-96134/source05c9b6d，本机B baseline-20261019-231754-96494/source7c973b5均passed，仅四份派发/交接文档不同。
- 各317 Java/build、8迁移、直连/代理各13功能+4安全、媒体144+8、上传65、B发现HTTP11、故障18、prepare5/跨JVM resume11通过；原始JSON与内嵌结果一致，22份原始JSON及MUS-014-live-results.json已归档。
- 实际Java A96493→96842、B97066→97275；新旧launcher PID、退出/端口释放/就绪、时间及checkpoint哈希一致。新JVM后12并行上传请求/2并行合并验证通过。
- 再读真库：Afile65/Bfile40均12行/12不同索引/持久计数12/状态1，文件字节一致；故障CHECK均0，私有canonical state和registry均清理。旧file44失败不修写。
- 服务保持运行，无需再次重启。B feed仍bbae379/source1534e4d，MUS-014-R1-B未主动claimed/批准；审核SHA7c973b5/revision1不变，只补验收输入。不是本会话权限已解除，也不是独立B账号或生产验收。

### MUS-014 B独立复核及运行补证接收（2026-10-20 00:39 Chicago）

- B feed8d1ae4ac/source7175ddf1，准确审核7c973b5、assignment sourcea433e2b、ack A0093ae4；MUS-014-R1-B/revision1 review_completed，approve限定本卡范围。
- A核对feed哈希与源码仅两B报告差异，原字节导入docs/reviews/MUS-014-B.md。B独立报告Java317、先前Python45/真实进程保护9，并补齐真库18故障、prepare5/跨JVM resume11、12并发上传/2合并；file16持久12行/12索引/计数12。
- B环境通过私有Linux工具路径/Unix socket转回环TCP/临时目录适配完成，未改业务/SQL/验收断言。其私有原始日志未交付，A仅核对已提交报告与哈希声明，不宣称重算B原始证据或无适配Linux通用支持。
- 两槽本机实证与B独立报告均完成MUS-014范围；main未合并，整库中断/ACK丢失、头像交错、GC和公开检索仍单列。机器接收记录MUS-014-B-acceptance.json。

## MUS-015 头像同值请求重新校验（当前占用）

- owner A，branch fix/MUS-015-avatar-revalidation，base a433e2b；allowed_paths：UserServiceImpl及UploadOwnershipHttpTest、CONTRACTS/STATUS/README/own latest/verification/MUS-015*、own派发卡。B报告原字节导入单独提交，不改B正文。
- 删除“与已读avatar相同则跳过requireAvatar”的快捷分支，profile与管理员目标更新均需校验每个非空头像的归属/完成/未删除状态并持有上传行锁；保持名称单独修改与管理员清空头像行为。profile仍仅写可编辑列。
- 静态交错：T1读avatar A，T2改B，T3删除已解除引用A，T1旧同值A写回。新增确定性HTTP/mapper场景验证旧快照+已删除上传拒绝写入；不把MockMVC/mapper模拟当真实多连接复现。真实交错验证及新版本HTTP待后续补证。

### MUS-015 实现检查点

- 两处同值avatar跳过校验已移除，仍调用现有requireAvatar/上传行FOR UPDATE并在原事务写引用。profile可编辑列限制、名称单独更新、管理员空值清除均保留，无schema/API字段变更。
- 新三项MockMVC/mapper确定性回归在旧代码52测试中3失败，修复后全量Java320零失败/错误/跳过。不是旧缺陷真实多连接复现，也不是新版本真实HTTP验收；现有服务仍MUS-014，本轮不停止、不要求用户再重启。
- B新卡待准确实现SHA提交后派发；MUS-014已接收approve及独立运行补证，不再等待旧卡认领。

- MUS-015实现d9a2a15791da0db4374c5de093a752a5aa202a25；MUS-015-R1-B/revision1固定审核该SHA，比较feb935ad5c7eb4eb8a11065f3d5c18ed2a93dab1，assigned未认领。MUS-014审核批准已接收，新服务真实验证仍待后续。

## MUS-016 授权演示曲库（用户新增范围，2026-10-20 Chicago）

- owner A，branch feat/MUS-016-demo-music-import，base dbb6312；范围scripts/import_demo_music.py及保护测试、DemoCatalogView/路由/菜单/公开许可元数据清单、own交接和验证文档。无Java/schema/依赖锁变更。
- 已在A导入20首CC BY原音频/20位作者；逐首完整SHA256与206 Range匹配，真实重复导入后仍20资源/20上传/普通USER，pending未擅自批准。B数据库未导入。
- Post Malone/Drake各10条资料及官方链接单独展示，不下载其音频/试听/封面。Demo Catalog登录保护，公开JSON无账号凭据/Client ID/JWT。
- Python50、Vue生产构建通过，浏览器已用演示账号查看20+20、按标题找到1条并播放至0:40/3:32后暂停、Drake筛选10条；目录链接可供用户检查，无需终端重启。
- 私有缓存/凭据0600留.local，Git只交代码/元数据/结果。MUS-015-R1-B卡仍在途、准确SHA不变，不用本次导入覆盖旧审核任务；MUS-016后续待独立复核。Java015未加载，后端仍014已验收实例。

### MUS-015 B复核接收与C1（2026-10-20 Chicago 01:28）

- B feed23ecb673/source8f622775，固定审核d9a2a15、assignment dbb6312、ack Ac618062；MUS-015-R1-B/revision1 review_completed/approve仅同值条件及既有空字符串行为。
- A核对feed哈希、B仅两报告路径差异、原字节导入docs/reviews/MUS-015-B.md；接收记录MUS-015-B-acceptance.json。B独立Java320、旧52测试/3预期失败；一轮后续blocked命令内16业务检查完成，另两入口锁专项2项独立exit0。不把跨命令18项说成一次全passed。
- B真实受控SQL/HTTP旧快照中两入口拒绝已删除旧A，保留B；performance_schema确认等待用户写入时上传X锁仍持有。不是三正常HTTP参与者全流程竞争。私有原始日志不在A，A不重算其哈希。
- 新登记C1：管理员avatar:null响应null但真库保留旧头像，属于P2既有差异；旧空字符串确实清空。批准不涵盖NULL语义。A以MUS-017明确并修复，MUS-015新Java尚未在A本机重新启动。

## MUS-017 管理员更新NULL头像语义（当前占用）

- owner A，branch fix/MUS-017-admin-avatar-null，base3092ae2。范围UserServiceImpl、UploadOwnershipHttpTest、CONTRACTS/STATUS/README/own交接/verification/MUS-017*/派发；B原报告只导入不改。
- 契约：avatar缺字段或null保持当前值，空字符串清空，非空路径每次requireAvatar。管理员仅写本次非null提交字段，避免为响应保留旧值而把旧头像/锁/密码等实体状态回写；不改全局NULL写入策略、schema或依赖。
- 目标确定性持久写列/响应回归；新真库验收单列，现有服务与20首演示音频不停止、不覆盖。
