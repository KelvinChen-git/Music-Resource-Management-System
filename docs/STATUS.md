# 项目状态与交接

最后更新：2026-10-19（America/Chicago）。当前集成负责人：**账号 A**。STATUS 仅由当前集成负责人串行更新；账号 B 的报告由 A 整合。

## Git 与交付状态

- 仓库：`https://github.com/KelvinChen-git/Music-Resource-Management-System`。
- 最新远端检查（2026-10-19 17:34 America/Chicago）：A 源分支 chore/MUS-008-account-sync@0ba0a96、A feed collab/account-a@d0a8381、B 源分支 review/MUS-001-B-baseline@6e4118c、B feed collab/account-b@05d4e9f 均可读。main 仍为 b81f57c；无 PR / 最终合并。
- 五份协作文档原先均未发布；已在 `docs/multimodal-collaboration` 应用附件补丁，提交 `8f1fb6b`。逐字节核对与附件相同。原 aa720da 是旧会话提交，不能假设存在于当前 Git 历史。
- MUS-001 交付分支：`chore/MUS-001-dev-baseline`（HEAD 1b1faa1），基于上述文档分支；实现提交 `7ab0d39d920a538b28878cf92ecbe90e55994ec3`。MUS-002 检查点分支为 `spike/MUS-002-clap-feasibility`，基线 1b1faa1，HEAD 6e4140b。本轮 A 当前工作分支为下条 MUS-008，未改动 MUS-002 分支。
- A 当前 GitHub 连接仍 permissions.push=false；受管终端 DNS 仍阻塞。用户已在普通 Mac 终端成功发布 A 源码 / feed；B 已从固定入口读取并主动 ack。B 用可写 GitHub 接口顺序发布其源码 / feed；不能声称双方终端自动发布都通过。本次 A ack 仅本地更新、尚未发布。
- MUS-008 工作分支：chore/MUS-008-account-sync，base 6e4140b，已发布检查点 0ba0a96。本轮 A 接收 B feed 05d4e9fe7c9528923796ef46508cadb05e94bd1b / source 6e4118cc316e95d2ba0f3c1fc1cf7ae15fecefbc，核验报告哈希、源码副本、审核基线和仅两文件 diff；与此前导入的 b81f57c 首轮报告区分。

## 能力与证据

| 内容 | 状态 | 证据 / 限制 |
|---|---|---|
| Java / Vue 旧管理系统 | 源码存在，部分流程实跑通过 | 注册登录、标签分类筛选、上传合并、MP3 元数据、软删除恢复 |
| 前端依赖 / build | passed | Node 22.23.3 / npm 10.9.9；现有 lockfile；非阻塞 bundle 警告 |
| Java 单测 | passed（A 历史运行）；B blocked | A 默认及显式 *Test 均 9 类 89 tests，零失败 / 错误 / 跳过；B 两种命令均未进入测试，执行数 0 |
| 空开发库 / local 启动 | passed（原生 MySQL） | V001 建立 11 表；重复初始化拒绝；Compose 未执行 |
| API 直连 / 开发代理流程 | passed | 各 13 项合成样本检查，真实 Range 返回 206 |
| 两账号环境隔离 | 配置及端口拒绝验证通过 | B 独立复跑 slot B、拒绝覆盖、0700/0600、Vite 代理及 strictPort 通过；B 数据库 / 完整服务未启动 |
| 旧媒体权限 | 已确认缺陷 | pending、静态上传及软删除后的匿名媒体均可 HTTP 200 读取 |
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
| MUS-008 固定交接与同步 | review / A（共享读取可用；A 自动发布 blocked） | chore/MUS-008-account-sync / 6e4140b | A/B feed 均已发布，B 完成 sync / ack，A 本轮直接读取 B；9 项脚本本地 Git 检查通过。B 接口顺序发布不等同原子脚本通过；A 回执待发布 |
| MUS-009 上传完整性 | blocked / A（实现与单测完成，DB 补验待运行） | fix/MUS-009-upload-integrity / 83b9402 | 单一同步持久化、事务 / 行锁、分片与整文件校验、幂等重试；107 tests 通过。MySQL signal 11 / 回环 Errno 1 阻塞 SQL / 并发 / 进程重启验收；见 verification/MUS-009.md |

### MUS-001 A 路径范围（review 检查点）

`AGENTS.md`、`README.md`、`docs/PROJECT.md`、`docs/CONTRACTS.md`、`docs/STATUS.md`、`docs/development.md`、`docs/verification/MUS-001*`、`docs/handoffs/MUS-001-B.md`、`.gitignore`、`.nvmrc`、`compose.dev.yml`、`scripts/dev.py`、`scripts/smoke.py`、`music/pom.xml`、`music/src/main/resources/application-local.yml`、`music/src/main/resources/db/baseline/V001__development.sql`、`music/src/main/java/com/taffy/music/domain/MusicResourceTags.java`、`music/src/main/resources/mapper/MusicResourceMapper.xml`、`music/src/test/java/MusicResourceServiceImplTest.java`、`web/vite.config.js`、`web/.env.example`。

扩展到 mapper / 单测的原因是实跑暴露 JSON 返回 null 和三项无效测试前提，详见验证文档。没有更改前端 lockfile 或重写业务服务。B 不在这些路径直接修复；需要扩大范围时先将具体路径交给 A 协调。

B 独占 `docs/reviews/MUS-001-B.md` 与自己的 `docs/collaboration/account-b/latest.md`；A 不创建这两份报告或 B feed。首次报告只导入独立 imports 路径，以免伪造 R1“已审核”。正式任务见 [handoffs/MUS-001-B.md](handoffs/MUS-001-B.md)。

## 未解决事项

| 编号 | 当前事实 | 后续 |
|---|---|---|
| B-01 | 缺配置 / proxy 硬编码已解决；可重复命令已建立 | B 复跑；Compose 仍未实跑 |
| B-02 | 空库 V001 已验证；历史 SQL 保留，不可顺序执行 | 既有数据库迁移另立任务；分类 ID Java 类型差异待审 |
| B-03 | 旧匿名媒体 / 静态路径 / 删除后访问问题已实证 | MUS-001-R1 提出矩阵与最小方案，MUS-005 接入前修复 |
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

- status blocked（构建通过，服务联通被回环权限阻塞）；owner A；branch `chore/MUS-010-dual-dev-baseline`；base `f15d842344f8df0b251f90d65811206efb589555`。优先跑通数据库、Java、Vue 及直连 / 代理 smoke；暂停新业务扩展。
- allowed_paths：`scripts/baseline.py`、必要的启动辅助测试、README / development / STATUS / A latest、`docs/verification/MUS-010*`。不改业务实现、schema、依赖锁或 B 报告。
- 验收：隔离 slot、工具可用、空新库初始化 / 已有库不覆盖、后端与 Vite 启动、直连和代理各 13 检查；A/B 各自独立 clone 或 worktree。A 本机代跑 B slot 不算 B 账号独立确认。
- 当前受管终端 Python socket bind/connect(127.0.0.1) 均 Errno 1，DNS 亦失败；这是本轮已测阻塞。继续完成无需端口的构建与可复现入口，不重复启动 MySQL 崩溃充当进度。

- MUS-010 本轮 Java 显式全部测试 107、Vue build、启动入口 8 项保护检查通过；完整入口在 A/B 的 socket 预检 Errno 1 停止。真实数据库 / 直连 / 代理功能执行 0，不能将构建通过当联通通过。详见 verification/MUS-010.md / JSON。
- 本机准备独立 B worktree Music-Dev-B-MUS010，供普通终端代跑 slot B；不更改 B 远端报告，不代表 B 已验收。下一步优先取得两个 checkout 的 result.json；暂停新业务和真实语料扩展。
