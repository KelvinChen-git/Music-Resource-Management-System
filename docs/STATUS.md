# 项目状态与交接

最后更新：2026-10-29（America/Chicago）。当前集成负责人：**账号 A**。STATUS 仅由当前集成负责人串行更新；账号 B 的报告由 A 整合。

## Git 与交付状态

- 当前检查点（2026-10-29 America/Chicago）：MUS-040第二检查点完成、整体in_progress。源码2b2d287已通过普通owner HTTP导入20新录音，账号自有资源60（开发40/测试20）、新20 pending，实际EOF/PCM/真实ID/Range/full SHA通过；CLI重跑0新增/42核心保持，额外20匿名401。78相关测试/838原件保护通过。G1新20/8query/141旧判断/双权重与旧索引保持；G2/160包/test run未生成。N1 B卡035-R2仍assigned，原版/UI/main保持。

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
| CLAP 文本 / 音频编码 | 原40链路及B旧20预检passed，正式效果未验收 | MUS-035全40/1557片段/8文本、512维；原20重编码差0、168测试/独立工件复算；无新参考音频/线上API |
| Python离线候选 / 线上检索 | 两来源40曲离线实跑，线上未实现 | 独立私有新run，原窗口/两mode规则；无Java gateway/共享索引/浏览器检索，discovery-v0未冻结 |
| 研究语料与标注 | 自有资源60首（开发40/新测试20）；累计141开发判断 | 原933/新1557片段run保持；037三补判完成、四原包分别保留，五描述123/200已知、77未知，8描述141/320已知、179未知；非held-out/2,000首/70,000片段/120查询 |
| 质量、P95、并发和提升比例 | 五开发描述精确top5已测，正式质量/P95未验收 | 037 whole25/25相关、segment24/25，P@5=1.00/0.96；旧20同五描述0.16/0.20；原029八query/035区间保持，定向扩库非held-out/10%提升 |
| 独立测试/模型对照 | 039 G1/040预检与新20身份导入通过；G2–G5未执行 | B旧20/933片段/五文本512实跑；新20真实ID/媒体绑定、78相关检查；160包/新标签/test run均0，待新runner/G2 |

详细命令与机器生成结果见 [verification/MUS-001.md](verification/MUS-001.md)。旧会话网络阻塞只是历史：本轮 Maven 已能下载和实跑。原始默认 75 tests 有 3 errors；修正 fixture 后才得到全量 89 tests 通过。

## 任务与占用

状态仅 todo / in_progress / blocked / review / done。A / B 为当前角色；未最终合并不自动代表所有内容完成。

| 任务 | 状态 / owner | 分支 / 基线 / 依赖 | 允许修改与验收 |
|---|---|---|---|
| DOC-001 协作文件 | review / A | docs/multimodal-collaboration / b81f57c | 五文件已应用并包含于远端 A 源码历史；main 未合并 |
| MUS-001 可重复开发基线 | review / A | chore/MUS-001-dev-baseline / b81f57c + 8f1fb6b；依赖 DOC-001 | A 的空库、local 启动、测试、build、smoke 通过；B 静态审核 / 前端 / 隔离通过，独立后端运行补证 blocked |
| MUS-001-R1 基线与媒体审查 | done / B（审核交付完成，后端运行补证未通过） | review/MUS-001-B-baseline / 7ab0d39；delivery 6e4118c | 只新增 B 审核正文和 latest；B feed 05d4e9f 已由 A 核验。48 格媒体矩阵均明确未运行，不将文档表格当测试通过 |
| MUS-002 模型 spike / 契约冻结 | blocked / A（开发效果已测，独立测试/冻结未完） | 原探针ab5d6f3；真实补证022/035，开发比较037 | 新40曲/1557片段、141判断，五query精确开发P@5已补；仍缺独立测试/模型对照，discovery-v0未冻结 |
| MUS-023 演示导入恢复/来源边界 | done / A（B限定批准已接收） | fix/MUS-023-demo-import-recovery / ebae5eb；契约81566b1 | pending/confirmed、完整缓存证明、canonical来源；62 Python/8链接/build通过 |
| MUS-032 定向来源候选 | review / A（收集/全解码完成，工具待独立复核） | codex/MUS-032-targeted-corpus-candidates / 2e2db1e | 五描述各4首，20/20原MP3/SHA/证明/解码、18保护检查；source-only，未写库/人评 |
| MUS-033 新来源导入与身份适配 | done / A（B限定批准已接收） | codex/MUS-033-source-import-review / 7704051；实现dc7e1e4、播放f9192fc、边界10880f8 | B对准确10880f8的独立合成审核通过；真实导入与034收件保持，历史header时长勘误见035，不外推模型 |
| MUS-034 新20素材标注接收 | done / A（接收/素材汇总完成，非模型验收） | codex/MUS-034-source-label-receipt / 7879a7d | 20/20全3分/原字节归档、固定CLI及同会话复核通过，累计138；186保护文件保持 |
| MUS-035 扩大语料检索对照 | done / A（B工具限定批准已接收；非正式质量验收） | codex/MUS-035-expanded-retrieval / b42b767；实跑17a31f5 | 全40/1557片段/8文本；168测试/独立矩阵复算/新素材20命中，P@5仅区间；旧run/138保留 |
| MUS-036 新top5未知补判包 | review / A（工具就绪；3判断已由037接收） | codex/MUS-036-top5-supplement / 9797ed4；真实生成125076d | E9独立包/实际EOF/新指纹/空建议，历史188 Python/77 Node/build/18真实浏览器通过，工具独立审核未完成 |
| MUS-037 补判接收与完整top5比较 | done / A（接收/开发比较完成，非正式模型验收） | codex/MUS-037-supplement-receipt / 49c255c；依赖036 | 3/3固定CLI/原字节归档/独立复算；累计141；whole1.00/segment0.96，284保护输入保持 |
| MUS-038 独立评测与模型对照方案 | done / A（仅方案设计，未执行测试） | codex/MUS-038-independent-eval-protocol / efd7be5；依赖037 | 仅冻结20新曲×8新query/全160判断方案、复用旧100作dev预检、两checkpoint×两mode和词面对照；不采集/跑模型/生成新包 |
| MUS-039 独立测试来源与描述冻结 | review / A（G1完成，工具待独立审核） | codex/MUS-039-independent-corpus-freeze / bc653e0；真实收集e668a74 | v2全221框、20条新source-only/9群/20work/8新query；26单测、独立EOF/完整队列通过；未导入/生成标注包/跑模型 |
| MUS-040 独立格式与模型预检 | in_progress / A（安全dev预检/新20导入完成，新test适配未完） | codex/MUS-040-independent-runner-preflight / 74645de；实跑de255c7，依赖038/039 | 先普通owner HTTP导入20源/真实ID与权限Range/SHA映射，立新test包/runner契约；B权重本地SHA/严格加载/512及旧100 dev预检，G2后新包；不升级依赖/重做UI |
| MUS-033-R1-B 新来源核查复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-033-B-source-review / 10880f8；交付4f57837 | 原字节报告/接收JSON归档，B27/72 Python、68 Node/build/独立15+7及23浏览器断言；均合成范围 |
| MUS-035-R1-B 两来源离线工具复核 | done / B（限定批准已接收；N1由A修复另卡复核） | review/MUS-035-B-expanded-retrieval / 9797ed4；对比b42b767 | 三新工具/三测试/E8，独立合成输入；不读A原件/跑模型，不外推036新包/UI |
| MUS-035-R2-B 输出权限N1增量 | assigned / B（待主动认领） | review/MUS-035-B-output-permissions / de255c7，对比74645de | 仅3个输出函数/两新回归与极端umask真实mode/读回/拒绝覆盖；不扩到040模型/039收集器 |
| MUS-031 补标接收与覆盖诊断 | done / A（接收/探索诊断完成，非模型验收） | codex/MUS-031-diagnostic-receipt / d9f6f2d | 67/67校验/原字节归档，累计118；五query各20曲完整，新增2正例；汇总见031 |
| MUS-030 诊断补标包 | review / A（工具/包完成；真人接收见031） | codex/MUS-030-diagnostic-review-pack / 4e8115c | 5query/67新对/18曲，53 Python/39 Node/build/20浏览器断言通过；原51保留；工具独立B仍待协调 |
| MUS-029 两模式探索评估 | review / A（实现/本机探索完成，非模型验收） | codex/MUS-029-exploratory-evaluation / ef5e388 | 38检查/固定51人评实跑通过，P@5整曲0.40/片段0.45；原包只读，不调参/训练 |
| MUS-028 首轮标注接收 | done / A（格式/来源绑定验收，非模型质量验收） | codex/MUS-028-label-receipt / df50001 | 51/51已判，0/1/2/3=19/13/9/10；原字节私有归档/固定run校验通过，0人工区间 |
| MUS-027 评分入口提示 | done / A（B限定批准已接收） | fix/MUS-027-review-rating-entry / 2ed661d | 就近必填代号/明确校验；8包检查/build、17浏览器断言及合成导出CLI通过 |
| MUS-027-R1-B 评分入口复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-027-B-rating-entry / 2ed661d；交付f9911e5 | B8 helper/build/25最终浏览器断言及两导出CLI；合成login/profile非真实Java/JWT；原字节接收见027-B-acceptance |
| MUS-026 审阅底栏/进度控制 | done / A（B限定批准已接收） | fix/MUS-026-review-player-controls / d766dcd | 两处控同一已验证音频，31检查/build及真实桌面/手机seek通过，原队列与标签保留 |
| MUS-026-R1-B 播放控制复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-026-B-review-controls / d766dcd | 仅新报告/own latest；独立合成环境补真实队列/控制链，不重复025全套 |
| MUS-025 试听审阅入口 | done / A（B原范围限定批准已接收；新体验问题转026） | feat/MUS-025-listening-review / cdc2fc5 | 本地包/JWT及SHA验证试听、人工草稿/导出，21检查/build/浏览器增量通过，原51空白包保留；已填副本见028 |
| MUS-025-R1-B 试听审阅复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-025-B-listening-review / cdc2fc5 | 仅新B报告/own latest；隔离合成数据、HTTP/浏览器，不访问A或代填真人标签 |
| MUS-024 探索人工标注包 | done / A（B限定批准已接收） | feat/MUS-024-judgment-pack / 1e83454 | 标准库CLI/17新增检查，全离线40通过；8查询51对全null，无试听新页面/人评/质量结论 |
| MUS-024-R1-B 标注包完整性复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-024-B-judgment-pack / 1e83454 | 仅新报告/own latest，合成fixture验证；不得称复算A私有工件或模型质量 |
| MUS-023-R1-B 导入恢复增量复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-023-B-demo-import-recovery / 00f10a6 | 原字节报告/接收JSON已归档，勿重复领取 |
| MUS-022 真实小语料离线探针 | review / A（链路实跑完成，质量未评） | spike/MUS-022-real-corpus-probe / ef8588a | 20首/933片段/8文字/3参考；23测试，51候选标签全null；离线工件不提交 |
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
| MUS-017 管理员NULL头像 | done / A（B限定批准正式接收，未升级演示服务） | fix/MUS-017-admin-avatar-null / f351b0e | C1关闭；23预期真库业务项+E1单列，E1/E2转MUS-021 |
| MUS-021 用户写入边界 | done / A（B限定批准已接收，未升级演示服务） | fix/MUS-021-user-update-boundaries / 0f12212 | B默认332 Java及24真库增量通过；E1/E2本卡关闭，边界见接收JSON |
| MUS-021-R1-B 用户写入增量复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-021-B-user-update-boundaries / 0d4d98f | 原字节报告/接收JSON已归档；固定入口转016，勿重复领取 |
| MUS-016 授权演示导入 | review / A（首审历史保留，对应R1/R2/R3由023关闭） | 原实现3092ae2；本次审核输入69a3965 | 导入器/保护测试/公开目录与原实现字节相同；不触碰A曲库 |
| MUS-016-R1-B 导入器独立审核 | done / B（review_completed / request_changes已接收） | review/MUS-016-B-demo-import / 69a3965 | 只交新B报告与own latest；许可声明过滤、秘密隔离、重复/失败恢复及目录边界 |
| MUS-019 Sonora 应用副本 | review / A（R1/R2已由MUS-020关闭） | feat/MUS-019-sonora-app / f68b7fb | 真实Vue新界面保留；不把增量批准外推整站、完整上传或管理写操作 |
| MUS-020 Sonora R1/R2修复 | done / A（本卡范围已验收，未合并main） | fix/MUS-020-sonora-review / 802da6b | B限定批准已核验接收；仅文档接收，不重做UI |
| MUS-020-R1-B 增量复核 | done / B（review_completed / approve_scoped已接收） | review/MUS-020-B-sonora-findings / d8bba9d | 原字节报告与接收记录已归档；020已关闭，固定入口见本轮016派发 |

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

## MUS-017 管理员更新NULL头像语义（已限定验收；下列为历史实现检查点）

- owner A，branch fix/MUS-017-admin-avatar-null，base3092ae2。范围UserServiceImpl、UploadOwnershipHttpTest、CONTRACTS/STATUS/README/own交接/verification/MUS-017*/派发；B原报告只导入不改。
- 契约：avatar缺字段或null保持当前值，空字符串清空，非空路径每次requireAvatar。管理员仅写本次非null提交字段，避免为响应保留旧值而把旧头像/锁/密码等实体状态回写；不改全局NULL写入策略、schema或依赖。
- 目标确定性持久写列/响应回归；新真库验收单列，现有服务与20首演示音频不停止、不覆盖。

### MUS-017 实现检查点

- 管理员updateUser仅应用/写入非null提交字段，avatar省略/null保持，空字符串明确清除；旧role/email/avatar不因名称编辑回写，锁/密码等安全列不进入UPDATE。返回值不再对null回显已清空；保留读取快照语义，不承诺并发最新响应。
- 新三项回归在旧实现55测试中3失败；修复后Java323零失败/错误/跳过。新版本真库响应/持久化及受控交错待B补证，不能沿用旧015批准为017批准。
- 前端/Python/schema/依赖无改动，现有网站、两套旧服务与演示20首音频保留；不要求用户本轮重启。后续卡待准确提交SHA。

- MUS-017实现f351b0e2030e5411b6f530ca039c694d4ca091d3，新卡MUS-017-R1-B/revision1固定该SHA、比较d443966148336b719cebdb041ea175dfbbfdc500，assigned未认领；旧015已按B实际完成接收。用户演示数据和在跑服务保持。


## MUS-018 独立 UI 设计预览

- owner A；branch `design/MUS-018-ui-preview`；base `d34f282a499b3e93c94f90c83c38d35dcb21ca3a`；status review（待用户确认视觉方案）。允许路径 `design-previews/sonora/`、本台账及 own latest。
- 交付自包含静态 HTML，原创 SVG 概念封面，曲库/歌手/收藏/最近播放、搜索筛选排序、详情、队列、文件选择和模拟播放器。无 backend fetch、音频播放或真实上传；19 首精选资料与 20 条外部歌手资料。
- 已检查 1440 / 660 / 390px 布局、搜索/收藏/列表/详情/歌手/导入弹窗/播放状态；修复手机主视觉重叠、列表收藏按钮状态与抽屉焦点恢复；浏览器未记录 JS error，静态脚本语法及 diff 检查另见提交验证。
- 不替换 web/、不发布现有站点、不重启服务、不变更数据库，不要求用户操作终端。B 的 MUS-017-R1-B 卡保持；设计确认前不派发替换页面任务。

- 本检查点已同步 B feed `0748515936eb5cb41446279acc29e52725781c1e` / source `067f6c3d6517da0852a10d6396fdc23161102525`，其最新报告明确 claimed MUS-017-R1-B，尚未完成，不外推批准。原静态脚本 `node --check`、`git diff --check` 通过。


## MUS-019 Sonora 应用副本（当前占用）

- owner A；branch feat/MUS-019-sonora-app；base f3b0da1e97113d28c81aa49be61c5cbcc49eebce；review。用户已批准将设计接入网站并保存开发副本，后续在副本基础上开发。
- 原目录 Music-Resource-Management-System 保留原 Vue 界面与运行服务；新 worktree Music-Sonora 作为前端开发基线，端口 5175，仅代理现有 A 后端 8080；不启动第二个后端或迁移/复制数据库。
- allowed_paths：web/src/App.vue、web/src/router/index.js、web/src/components/Sonora*、web/src/stores/sonora*、web/src/stores/musicStore.js（旧管理路由监听边界）、web/src/views/Sonora*、web/src/styles/sonora.css、web/src/utils/sonoraArt.js、web/scripts/verify-sonora-player.mjs、web/index.html、README/PROJECT/STATUS/own latest/本任务验证文档。保留旧管理组件与 API/权限路径，B 的 MUS-017 审核路径不接管。
- 目标：真实曲库/鉴权播放、搜索筛选、收藏/最近播放、歌手资料、上传和原管理入口；收藏与历史限定当前浏览器及账号，不冒充服务端持久化。

### MUS-019 实现与验收

- 新副本完整 Vue 应用接入 Sonora：新 App 外壳、主曲库/收藏/历史/歌手页、鉴权真实音频播放器。原管理页移至 `/manage/music`，原组件与业务 API 保留。原目录 git 工作区保持干净，旧 5173 与新 5175 均 HTTP200。当前新 5175 使用构建产物，避免开发依赖首次优化触发页面刷新。
- 已通过 `npm ci`（lockfile 未改）、生产 build、5 组播放器边界/竞态/账号隔离验证、原媒体 helper 6 项检查与 diff check；无 Java/Python/schema 变动，不重复跑不受影响的后端全套。
- 真实浏览器：演示账号登录读取20首；What Is Love 真实时长212.022653秒，播放到7.293254秒、readyState4、无音频错误后暂停；原管理页Grupo真实播放86.0122秒时长，跨页仍在播放。搜索/空结果/风格/收藏/列表/历史/详情授权链接/歌手20条及Drake10条/上传页面/资源表格/退出清理/重新登录保留收藏已检查。没有新上传、编辑、删除、审核或迁移用户数据；播放计数正常增加。
- 桌面1440与手机390断点通过，手机文档宽384不超过视口390；保存截图。浏览器错误与旧管理store监听的修正见后续补充。脚本第一轮关闭时曾出现Vite依赖扫描噪声，修正无发现扫描配置后5组检查再次exit0且无扫描错误；不隐去首轮诊断。
- npm ci 报原 lockfile 的59项依赖审计提示（11 low/12 moderate/34 high/2 critical），未为本UI任务擅自升级；build仍有既有>500kB chunk提示。完整新增上传链路、管理写操作及管理员浏览器场景本轮未重跑。
- status review / 已接入，待用户体验；本副本为后续开发基线。新 UI 使用现有 A 后端与曲库，不宣称数据库隔离或生产部署。B feed bb64dcafb37b021e468b207560c8ae98c28b87a3/source082d243161c5774a96d242a473b17c483a77cc4e 的latest已读，其017批准有限定范围；完整报告正式接收与E1/E2后续处理另轮完成，本UI任务不改后端也不冒充验收。

- 集成验收发现旧Pinia管理store离开页面后仍监听全局query，在退出附近记录过一条旧列表失败；将其监听限定在 `/manage/music`，并放到方法定义后，避免新曲库/登录触发旧后台搜索及带参数直达管理页的声明前调用。最终构建另行核验，不把此条旧错误隐去。

- 最终构建再次通过；带keyword直达 `/manage/music` 返回1首What Is Love，再从顶部搜索Energy切回Sonora成功；最终检查时间段无新增warn/error。实现 `f68b7fbba63ea58ad10dfe326d0197d1cc6b15ce`，B增量任务 MUS-019-R1-B / revision1，assigned未认领，仅复核前端与真实媒体边界。MUS-017 B已完成报告，但A正式接收和E1/E2协调仍单列。


## MUS-020 Sonora B复核修复（已验收；下列为修复时检查点）

- owner A，branch fix/MUS-020-sonora-review，base c19b64833b78a2cd958959b77a1c9703f2fc9281，review。已验证B feed f9fc32ec4e49b7876e0387f58c9f7a1fd7a7af46/source30bbd71ce34d0df6580680180498dc7eb22a19e6、latest hash与仅两报告路径diff，原字节导入MUS-019-B报告。结论request_changes，不称整个UI批准。
- R1：390px列表长标题撑宽；R2：管理员username/email两入口仍指向新/music导致筛选丢失。范围sonora.css、admin/user/index.vue、必要的导航兼容/测试、README/STATUS/own latest/本任务verification/派发。无后端/schema/依赖更新，不接管B报告。
- B独立build、5组player和6media检查通过；真实隔离浏览器26项预期行为通过并观察3条失败（R1+R2两入口），8次前期blocked不相加。私有原始证据未交付，A仅核对报告字节，不重算其日志。
- 本轮5175前端已退出、A8080仍返回匿名401；先恢复前端，再在新副本修复与验收，不要求用户操作终端。

### MUS-020 修复检查点

- R1仅收缩列表信息/标题容器；R2仅两管理员入口目标改/manage/music。原版目录、后端、API/schema/依赖不改。
- A：生产build、5组player、6media、diff检查通过；离线真实CSS长标题390px旧1432→新390，收藏x327–354可点；真实20首手机列表文档384≤390、20控件在视口内。R2实际handler体旧两个目标/music、新/manage/music及query/缺字段保持已检验；router/message为替身，管理员真实HTTP回归仍待B。
- 5175已由独立会话前端进程恢复，现有A8080保留；普通账号20首/真实Grupo播放正常后暂停。PID/日志在忽略.local，无系统自启动或永久可用承诺。详见verification/MUS-020.md。状态review / 待B增量；没有把mock或离线fixture写成真实管理员全链路。

- MUS-020实现 `802da6bb1ee3f7906a19c963efb5aeac2115d223`；新B卡MUS-020-R1-B/revision1固定该SHA、比较c19b648，assigned未认领；复用R1长标题与R2两管理入口最小真库/浏览器回归，不重复整套019。


### MUS-020 B限定批准接收（2026-10-20 America/Chicago）

- owner A；接收基线 `0566bc26ca88c5600072db717a26119c8983ed3f`；MUS-020 status done 仅表示 R1/R2 修复与限定验收完成，MUS-019 整体继续 review，不代表 main 合并或整站批准。本轮只写本台账、A latest、B任务入口/原卡接收注记、MUS-020验证文档/接收JSON及原字节导入报告；不改产品代码。
- A/B 固定入口本次 sync 均 fetched。ack_peer_feed_sha `5c0cebf85a20d14ccf0cdfe132a0f08d1d513fa1` / B source `d8bba9d9199f802a3b5ceb0e7de0c2ab564f9688`；B task MUS-020-R1-B/revision1、reviewed `802da6bb1ee3f7906a19c963efb5aeac2115d223`、comparison `c19b64833b78a2cd958959b77a1c9703f2fc9281`、assignment source 0566bc2 与 ack A ec6cdbb 均匹配。B已主动claimed并review_completed/approve，本轮正式接收为approve_scoped。
- 核验latest的hash及source字节、仅两B报告路径diff、web树/锁哈希声明；原字节导入 [MUS-020-B](reviews/MUS-020-B.md)，不改B latest/feed或原MUS-019-B报告。机器记录 [MUS-020-B-acceptance.json](verification/MUS-020-B-acceptance.json)。MUS-019 R1（390px长标题溢出）与R2（两处管理员查询入口）关闭，本增量无新增阻断发现。
- B独立报告：build通过，实际handler/替身router-message 4项通过；新隔离clone/slot B/MySQL/JVM/Chromium最终run baseline-20261020-171644-11 exit0，16项增量通过。真实长标题列表document390、收藏x327–354可点击，网格390/桌面1440；鉴权合成音频播放/跨页暂停通过。管理员Username/Email六链路按owner得到2/1/0资源，XHR原参数及API/UI集合一致；普通用户路由边界和普通keyword保留。
- 两次准备命令171408/171512各exit1/blocked、浏览器0项，原因分别为用户名超20和标题超100字符；最终16项单独记录。193字符压力标题由隔离SQL fixture设置，不冒称正常API允许。B中文字体缺失；私有原始日志/工具/截图未交付，A仅核验报告与声明，未重算其原始证据哈希。B自行停止进程并报告3308/8081/5174释放，顺序GitHub发布并非原子。
- 本地只读检查：原版 `Music-Resource-Management-System` 仍 `design/MUS-018-ui-preview@f3b0da1e97113d28c81aa49be61c5cbcc49eebce` 且干净，当前分支保留该祖先；5175/music HTTP200、8080匿名profile HTTP401。未重启服务、触碰库/音频或重做UI。
- 本轮文档检查见交接；不重复运行未改的build/player/media/Java/Python或完整浏览器套件。MUS-017正式接收/E1/E2、MUS-016独立审核继续单列，不自动关闭；完整上传/管理写操作、旧手工深链兼容、跨设备/生产/检索质量未补验。B两报告活动占用释放；固定入口waiting，无新卡，勿重复领取020。提交后按约定发布A回执，最终SHA和发布结果由交接消息给出。


## MUS-017正式接收与MUS-021占用（2026-10-20 America/Chicago）

- A从干净 `5d3441a97979b8d3b9fe23f511472c8fc0a1dc11` 创建 `fix/MUS-021-user-update-boundaries`；新任务MUS-021 owner A、in_progress。允许路径：UserController、新AdminUpdateUserDTO、UserServiceImpl、对应Java回归、CONTRACTS/STATUS/README必要事实、A latest、MUS-017接收/MUS-021验证文档及A任务派发。无UI/schema/依赖升级，不重启现有MUS-014演示服务，不合并main。
- 本次sync A feed45776bf/source5d3441a；最新B feed `8b49b6b19aa58ec4f09ccf4cfe939fab6a1a01ff` / source `86fa91dfa596a1dd86dce9413c39e80684d69a96` 已主动ack A45776bf，确认020关闭/waiting；不因已读确认再派020或触发回执循环。
- 正式接收历史MUS-017-R1-B/revision1：B feedbb64dcaf/source082d2431、reviewedf351b0e、comparisond443966、assignmentd34f282及ack A35c3572匹配；hash/source字节与仅两B报告diff已核验。原字节导入 [MUS-017-B](reviews/MUS-017-B.md)，[机器接收记录](verification/MUS-017-B-acceptance.json)。approve_scoped，C1关闭；MUS-017限定范围验收完成，现有A运行版本不因接收升级。
- B报告Java323来自后续blocked命令；独立最终命令exit0/status review_findings，23预期业务检查通过及1项E1差异单列，不写24全passed。旧55/3预期失败、SQL fixture受控交错与performance_schema锁证据保留；不是三个正常HTTP参与者竞争。私有日志/工具未交付，A不重算其原始哈希。
- E1/P3：空对象在实体身份反序列化时业务500；选择与全null相同的“保持字段”语义，仅updated_at可更新，以专用四字段DTO解除实体身份绑定，不改全局Jackson/NULL策略。E2/P2静态风险：lockUser/unlockUser/changePassword/lockUserWithReason/resetUserPassword/resetPassword六处完整实体写入，改为各自实际变更列；未复现真库并发覆盖前不声称已证实漏洞。契约先更新，精确实现提交后派B增量真库复核。
- B固定入口暂waiting；MUS-016导入器独立审核另列。原版备份和现有曲库/服务保留；本轮不触碰真实邮件或用户数据。


### MUS-021实现与检查点

- E1专用AdminUpdateUserDTO解除Users输入身份绑定，空对象仅写updated_at，管理员/普通权限与路径目标、四字段/保护列边界保持；E2六入口均改专属LambdaUpdateWrapper，密码仅password/updated_at、锁定仅本操作列。新上锁显式清unlock_time，解锁保留锁原因/时间。无全局NULL/schema/依赖/UI变更，契约A10。
- 修复前定向64项：7 failures/1 error/0 skipped；两项空对象MockMVC业务500及六入口mapper写列边界失败/错误，codeReset旧mock返回0导致原异常；不是旧并发覆盖真库复现。修复后默认和显式*Test两个独立命令均14类332项零失败/错误/跳过，选择逐类一致；新9项，旧3fixture适配mapper调用。共享JDK逐命令JAVA_HOME，未改系统Java。见 [MUS-021验证](verification/MUS-021.md) / [结果JSON](verification/MUS-021-results.json)。
- 六入口测试捕获wrapper赋值并应用到合成并发状态，校验目标/专属列和未改字段保留；不把它称作HTTP/MySQL并发。B精确实现提交后补真库响应/受控时序；现有A/B演示仍旧MUS-014，不重启、不触碰真实邮箱/数据。MUS-016独立审核继续待办。


### MUS-021准确提交与派发

- implementation_sha `0f12212123616809ea0a917e43fc11e5f564ab46`；源码比较基线 `a9655750b6a4a5df07c2d64abd7f809fdd1e5978`，任务起点5d3441a。新卡MUS-021-R1-B/revision1 assigned未认领，固定入口已更新；B仅写新报告与own latest，补E1/E2真库/受控交错，不重复020或全部UI。
- 提交前检查点A/B sync均fetched，B仍8b49b6b/source86fa91d；本地只读检查备份干净f3b0da1、新5175/music200、旧8080匿名profile401。MUS-017限定批准已正式接收，MUS-016独立审核待后续。本轮没有新后端启动或用户/曲库/邮件写入。
- 文档链接/fence、JSON/源码哈希/原字节报告、git diff --check均通过；UI/schema/POM/依赖/Python路径未改。实现提交与本派发文档提交后按约定原子publish；结果和最终source SHA以发布回读及最终交接为准。


## MUS-021 B限定批准接收与下一审核（2026-10-21 America/Chicago）

- owner A；本轮接收基线69a3965，允许路径STATUS/CONTRACTS必要事实/README、A latest、021原卡/验证/接收JSON及原字节B报告导入、新016卡/固定入口。不改业务/UI/schema/依赖/数据，无新进程或服务升级。
- A/B sync均fetched：A feedfeec5afd/source69a3965；ack_peer_feed_sha `c32868c6a5c74dca5961b53e6bf2a846978e3ada` / B source `0d4d98fed6f5e876c9a87ab95c1d7e56b4332280`。MUS-021-R1-B/revision1已主动claimed并review_completed/approve_scoped；reviewed0f12212、comparisona965575、assignment69a3965/ack Afeec5afd均匹配。
- 核验latest hash/source字节、仅两B报告路径diff及music树87615036；原字节归档 [MUS-021-B](reviews/MUS-021-B.md) 与 [接收JSON](verification/MUS-021-B-acceptance.json)，不改B latest/feed。E1/E2在本卡范围关闭，不将旧E2静态风险称为旧JVM真库漏洞已复现。
- B独立默认冷编译332 Java；最终baseline-20261021-062234-10 exit0/status passed，24项=E1 HTTP/SQL11+E2受控交错7+负例6。23正常HTTP、1真实Spring null原因分支。performance_schema实际观察UPDATE行WAITING/专属SET，fixture并发更新后独立SQL验证全部非本操作列保留；BCrypt与实际缓存成功/失败行为补证。
- cache由同JVM私有mode600 IPC设置/查询，无新产品HTTP后门或邮件；七交错有SQL fixture参与，不是三个正常HTTP竞争。删除单独合成victim产生mapper0行分支，不代表整库中断/提交失败。私有日志/工具/库未交付，A未重算其原始哈希。
- 前置offline clean缺插件exit1/测试0；首轮探针误解析匿名401空body导致exit1/blocked，其中Java332和5业务完成单列。最终24与前5不相加、两轮Java不相加，B显式*Test未新跑。进程停止与3308/8081释放为B报告事实；顺序GitHub发布非原子。
- 下一卡MUS-016-R1-B/revision1，reviewed69a3965，原实现3092ae2/比较dbb6312，仅审导入器/既有保护测试/公开目录及路由兼容所需片段；输入脚本/测试/两个JSON/视图相对原实现字节未变。assigned未认领，B只写新报告和own latest，不重领017/019/020/021、不直接修实现。不访问A服务/缓存/凭据/曲库，隔离合成源fixture与真实本地HTTP须分别标明。
- 本地只读：备份仍干净f3b0da1，5175/music200、8080匿名profile401。文档专用本轮不重复Maven/UI/Python套件；完成JSON/hash/链接/fence/diff检查后提交发布回执与新卡。未合并main，权限撤销/验证码原子消费/同密码竞争/生产与检索质量仍单列。


## MUS-022真实小语料离线探针（2026-10-21；当前占用）

- owner A；branch spike/MUS-022-real-corpus-probe；base2c122130f2fc7f848f81d53e6719809ef6ab9811；in_progress。允许services/audio-search/中的离线解码/候选窗口/探针及测试、独立探索查询fixture，docs/model-spike/STATUS/PROJECT/README必要事实、own latest和verification/MUS-022*。不改Java/Vue/依赖锁/公共API/schema，不提前冻结discovery-v0或开放搜索。
- 本轮sync B仍c32868c6/source0d4d98fe，MUS-016-R1-B未有主动认领，固定卡保持task/revision/准确输入，不覆盖。A不修改或重复执行导入器，不写B两报告。
- 已只读定位原版目录本地20份MP3/20份下载证明、现有固定checkpoint/CLAP venv/HF缓存；原音频/证明/权重只读共享，所有新工件写当前副本已ignore的.local/a/mus022，不改原版工作区或数据库。现有soundfile能列出MP3解码格式，真实解码尚待运行，不记为已验收。
- 验收：逐首内容/来源声明/原下载证明匹配，MP3实际解码时长/声道/采样率及无效文件/短尾段边界；使用既有候选10s/5s规则和固定模型，在当前20首范围生成整曲聚合/片段精确排序及少量文字/参考音频探索查询。所有结果绑定源码/输入/模型/pipeline/工件哈希，拒绝覆盖旧run。
- 排序结果无人工qrels，仅用于看候选/失败和后续标注；不写质量提升/P95/正式评测通过，不把候选离线向量当线上索引或最终模型选择。素材下载时声明不冒充本轮实时许可复核。若真实语料/效果仍不足，MUS-002不冻结，003/004不并行实施未定API。


### MUS-022运行完成检查点

- implementation/run_sha `ef8588a76a3c068bf5f281efd59a33ce95820d94`，运行时工作区干净。原20份MP3/20下载证明只读校验，内容hash/size/source/license一致；20首全为44100Hz MP3，真实解码4722246ms，候选10s/5s共933片段/20补零末段。前后重校输入，原版数据/模型/服务不改。
- 固定原checkpoint restricted/strict加载，实际933片段+20整曲均值聚合+8英文探索+3库内参考共964个有限归一化512维向量。11组top5整曲/片段精确排序，按每曲最大score与IoU>0.5抑制；所有933边界与向量/工件/源码hash独立复核通过。
- 23测试exit0（原9+新增14），MP3由20首真实run补验；run-01 exit0/passed_offline_pipeline_only。再次同output exit1/FileExistsError为预期拒绝，工件hash未变，不算第二次成功。仅一次CPU总约79.6秒含构建，不是查询P95。详细 [MUS-022](verification/MUS-022.md) / [结果JSON](verification/MUS-022-results.json)。
- 8文字查询的整曲/片段top5候选并集形成51对，标注包relevance/人工区间/annotator全部null；参考来自候选本身，自匹配不代表held-out质量。无人工qrels/质量指标/模型对比结论，002仍blocked于效果与冻结，不提前实现未定003/004/API。
- 新工件只在本副本.local/a/mus022；Git不提交原音频/模型/生成索引，现有20资源仍owner/pending离线范围，无实时数据库权限刷新，不能进入共享discovery。许可只匹配原下载记录，非实时源复核。Java/Vue/Python依赖锁/API/schema不改，无关Maven/前端套件不重复。
- 检查点sync B仍c32868c6/source0d4d98fe，固定MUS-016-R1-B/revision1保持assigned未主动认领，未被本任务覆盖。原版备份干净f3b0da1、5175/music200、原8080匿名profile401，main未合并。下一步人工候选判断/失败分析，再做模型效果/方案对照和契约冻结；B016审核发现另行接收。


## MUS-023 导入器B审核发现修复（2026-10-21；当前占用）

- owner A；branch fix/MUS-023-demo-import-recovery；baseebae5eb9fba158152aa8f3061b25fb93f502e95a；in_progress。B feede1da44f8/source0c5efad9、reviewed69a3965、assignmentebae5eb/ack A596642d7已核验，原字节导入MUS-016-B与接收JSON。MUS-016-R1-B review_completed/request_changes已接收，不再assigned未认领。
- R1/P2注册请求前失败后的凭据恢复、R2/P2证明size/source/license绑定、R3/P3条件性上游来源query公开风险，全部按最小修复处理。不声称A原证明错误/现有公开JSON秘密泄漏；MUS-022已逐份核对的离线工件继续保留，无新质量结论。
- B主矩阵52预期断言含26锁检查及3发现，status review_findings；补验4、首轮blocked内console40/2另列，不相加。5保护与9提取代码组通过、Java仅compile未测；提供方为fixture，本地HTTP/MySQL真实，私有原始证据未交付，A不重算。
- 允许scripts/import_demo_music.py及保护/恢复测试、DemoCatalogView与独立安全链接helper/测试（不改布局）、README/CONTRACTS/STATUS/own latest/verification/MUS-023*/016接收和新派发。无Java/schema/依赖锁/公共JSON/原音频/现有数据库更新；不重做UI、不升级演示后端、不合并main。
- 先更新行为契约：凭据保存不等于注册完成；pending用相同凭据先login，只有明确原接口身份拒绝时尝试register，模糊网络/服务器失败保留现场；成功login/profile USER后confirmed。缓存证明严格核对结构/大小/SHA/来源/许可，失败不覆盖。公开Jamendo来源按已核对ID构造canonical HTTPS URL，页面外链无userinfo/敏感query/fragment，Apple仅保留必要数字i参数。
- B固定旧016卡标review_completed/request_changes，等待A准确实现后派MUS-023-R1-B新卡。原MUS-022/51空标签及审阅入口计划暂缓于本轮审核修复，不自动填标签。


### MUS-023实现/验证检查点

- pending/confirmed恢复及credential指纹，只有旧login明确身份拒绝可register同一凭据；profile普通USER/目标确认后confirmed。完整下载证明schema/size/hash/source/license严格匹配，错误保留；Jamendo来源按ID canonical化、页面外链去敏感query/fragment/userinfo，Apple保留合法i，目录布局/公开JSON不改。契约A11。
- A首轮新fixture未建.local/a导致11方法14 errors，未触达产品；修fixture后旧业务11方法10 failures/2 errors（含subTest）触达边界。第一版修复定向16通过；增加账号状态保护后全scripts62通过，Node链接8、前端build通过。提供方和本地API均替身，非真HTTP/JVM/SQL；旧5保护fixture补shareurl新必需字段，不隐藏旧基线失败。原日志/源码hash见MUS-023-results.json。
- 原A20条选曲/完整下载证明只读20/20匹配，新verify不做API/提供方请求或重写，不指认已有证明错误。原版备份干净f3b0da1、5175/music200、原8080匿名profile401；无Java/schema/依赖锁/真实账号/曲库改动，不重启后端或合并main；未重复无关Java/player/media完整套件。
- 旧016卡已完成request_changes，新实现精确SHA提交后派MUS-023-R1-B/revision1补最小真库增量。MUS-022质量/人工标签不自动通过，原可试听标注入口留后续。


### MUS-023准确提交与新卡

- implementation_sha `ab8205827456ec6aeab3bcb289722a236e644f6b`，comparison_base `81566b1634aa19cb8493d2c2740c6d002a75ba4e`，任务起点ebae5eb。新B卡MUS-023-R1-B/revision1 assigned未认领，固定入口替换已完成016任务，不重复原全矩阵；R1/R2/R3在B增量前仍待独立验收，不先写closed。
- 检查点sync B仍e1da44f8/source0c5efad9；A完成JSON/hash/原报告字节/链接/fence/diff校验，Java/公共目录/依赖锁/MUS-022/原B报告未变。原版备份/后端保持，main未合并。提交后原子publish并回读，最终source SHA由handoff/交接消息提供。


## MUS-023限定批准接收与MUS-024占用（2026-10-21）

- A核验B feed `1391d53a467462fea03658dc6aa48712dc0a0f4e` / source `00f10a6bb04ac6dbf64927a55d90f72f94022e54`：latest hash/源字节/仅两报告差异、准确reviewed ab82058/comparison81566b1/assignmentec6317c/ack A6577bed匹配，原字节归档MUS-023-B及接收JSON。R1/R2/条件性R3本卡关闭，旧016 request_changes保留历史；不外推整个导入器、许可法律或模型质量。
- B相关Python17/Node22链接8通过；最终真实本地HTTP/SQL15组fixture、39次导入、84断言（39锁清理+45其他），源提供方/MP3为替身；首轮JAVA_HOME缺链接blocked业务0独立保留。其他business500/nonUSER为响应fixture，数据库拒绝/锁定/改密真实。B无Java单测/全62/build新运行，私有证据未传A不重算，详情见接收JSON。
- MUS-024 owner A，branch feat/MUS-024-judgment-pack，baseec6317c。允许services/audio-search/review_pack.py、test_review_pack.py、README/CONTRACTS/STATUS/A latest、verification/MUS-024*及B派发；本次同时允许023接收文档及原报告导入。先冻结CONTRACTS E1，生成包/校验人工字段/防候选串改、测试与实际51空标签包校验；新工件只在本副本.local/a/mus024。
- 无Java/Vue/schema/API/依赖/公开JSON修改，无音频复制、模型重跑、旧包覆盖/自动人评或质量指标。B固定入口waiting，待准确源码后新卡；B两报告释放，不接管其feed。不升级演示后端，不改备份/原曲库，不合并main。


### MUS-024实现与派发检查点

- implementation `1e83454474413fb6c58a73d82ace579656749bc0`；comparison/scope `3c7552ad2071847959eecf520956690dc083411e`。新增review_pack.py与test_review_pack.py，标准库，无依赖改变。四工件/catalog hash与显式report pin，候选/owner/音频内容/来源/模型/实测时长绑定；只允许四人工字段改变，null与0严格分开，区间与代号/UTC时间校验。输出仅本副本.local，0600、独占创建/拒绝覆盖。
- 定向17通过；首轮16通过1 error为macOS临时目录/var别名fixture，修fixture根路径resolve后通过。原音频模块全40通过（含17，不相加），不涉及CLAP编码/HTTP；真实数据build/validate在干净1e83454各exit0，8查询51对全null，与原包候选集合一致。重复build exit1/FileExistsError预期拒绝，原7工件hash及正式包字节不变。正式包43475字节/0600，仅ignore目录；见verification/MUS-024.md/results.json。
- 无人工听音/质量/held-out或新试听页面，包只绑定记录，不刷新当前音频/权限/许可，不是媒体授权。后续仍需JWT媒体读取与内容校验；MUS-002质量/冻结仍blocked。Java/Vue/schema/API/锁/公开JSON/原备份/曲库/服务不改，未重复无关Java/build/导入器套件，main未合并。
- 检查点sync A fb8c7d5c/source3c7552a、B仍1391d53a/source00f10a6b，023限定批准已接收；新MUS-024-R1-B/revision1 assigned未主动认领，准确reviewed1e83454/comparison3c7552a，只B报告/own latest。B用独立合成fixture补CLI/完整性，不要求A私有51包或重复模型/导入/UI审核。提交本派发后publish并回读，发布不等于B已接收。


## MUS-024接收与MUS-025占用（2026-10-21）

- B feed `76b8244407e9f27f3edbaa113437c1575902e966` / source `b15ead23e0a9f7ebb91b9d5344559c4d46353877`，reviewed1e83454/comparison3c7552a/assignment6fef7d9/ack A43748a0匹配。latest字节/hash/仅两报告核验，MUS-024-B原字节与接收JSON归档，approve_scoped正式接收。B17标准库检查、83 CLI（4成功79预期拒绝）、独立7合成曲目/12候选，不累加A40，不冒充复算A私有51或真人标注；私有日志未传A不重算。
- MUS-025 owner A；base6fef7d9；允许web/src/views/ReviewWorkspace.vue、web/src/utils/reviewPack.js/reviewAudio.js及对应test、router单一路由、App侧栏单入口，以及README/CONTRACTS/STATUS/A latest/verification/MUS-025*/B派发；同时允许024接收文档/原字节报告。草稿/QA/导出仅ignore的.local/a/mus025，本地原包/音频/索引不改，不写B feed/own latest。
- E2先约定仅本地包/既有JWT媒体读取、SHA字节核对、逐次重鉴权、竞态/退出回收与分账号草稿/人工字段显式输入。无Java/Python处理器/schema/依赖锁/公开JSON/API改动，不预填51人评、不重做UI/升级后端或合并main。B入口waiting，准确源码后再派；现有MUS-002仍等质量/冻结。


### MUS-025完成与准确派发（2026-10-22）

- implementation `cdc2fc5c00dbc4c2889068023d9d37ce8744a532`；comparison/scope `133fecbcda96585a09d6e0cf67af608c768c9151`；初版1fbaac8。新/research/review登录路由、侧栏单入口、新view及两个helper/对应测试，原UI/播放器/媒体helper不重写。包本地<=2MiB/严格字段重复键整数/owner/内容指纹，草稿按owner+dataset且显式恢复，部分导出兼容固定run CLI。每次现有JWT媒体GET、完整SHA字节核验才建Blob，seek/终点停止/切换取消回收；成功音频才允许取点。
- 新15（8包7音频）通过；加既有6media为21通过，最终补verified断言再21通过，不相加。固定Node22 build通过，>500kB旧warning保留。首轮浏览器发现错误SHA拒播后取点仍enabled，cdc2fc5已修、补断言/build/实际拒播disabled复验。一次QA过早goto中断登录等待timeout，按正常UI等登录后通过，非产品认证失败。
- 原8查询51包实际导入0/51、Energy28真实55–65s Blob试听/终点1:05释放，最终build再验证起播55.118844s/230.478526s时长、取点、在1:02退出清包/音频、匿名深链登录保护、重登不残留包；错owner文件拒绝保留原判断、错SHA实际授权音频无src/取点disabled。390 scroll384、1440 scroll1434，截图已查看，最终warn/error空。
- 正/0评分、1–2s区间、越界13s拒绝、草稿刷新显式恢复与导出仅独立6合成曲目/12候选，在初版1fbaac8验证；两个实际浏览器导出对各自合成run CLI通过。最终真实浏览器导出原run CLI通过0/51、0人工区间，旧7工件及原024包SHA未变，无自动真人标签或质量指标。
- 同账号退出/重登已验；真实第二账号/撤权矩阵、真实两播放器竞争、存储quota故障未新验，假音频/网络检查与真实HTTP分别记录。剪辑为浏览器事件/计时非采样精度，当前已交付字节不能追溯撤销；来源最终须CLI固定run核验，不把自洽包当可信来源/权限。详情verification/MUS-025.md/results.json。
- B仍feed76b82444/sourceb15ead23，024 approve_scoped已接收，固定入口MUS-025-R1-B/revision1 assigned未认领，准确reviewedcdc2fc5/comparison133fecb，只交新B报告/own latest，不重复024/模型/导入/UI全面审核。现有后端/Java/Python处理器/schema/依赖锁/公共JSON/原备份/账号曲库不改，无新服务/迁移/资源写操作，main未合并。文档/JSON/hash/链接/diff后提交publish并回读，发布不等于B已接收。


## MUS-026占用与025接收（2026-10-24）

- owner A，basec382cbc；B feed 0907de0959bae0e8de3f9110caaefd536243106d/source7c93a512817b5a82f89ddf746ec54265016cfc16、准确reviewedcdc2fc5/assignmentc382cbc/ackc674c707匹配，latest hash/只两报告核验，025-B原字节及接收JSON归档。B21/build、最终37浏览器断言/4导出CLI通过，预期4HTTP console error/0 pageerror及前期失败边界保留，不累加或复算私有证据。原批准不覆盖用户新要求。
- 新026允许web/src/utils/reviewAudio.js及test、views/ReviewWorkspace.vue、stores/sonoraPlayer.js及新增test、components/SonoraPlayer.vue；契约/台账/README/A latest/verification/MUS-026*/B派发；同时025接收文档/原报告。无Java/Python/schema/API/依赖锁/公共JSON变更，用户现有标注与原包只读，不预填人评。
- 原因：审阅独立audio无底栏状态登记且页面无range input。先E3：临时控制会话接现有底栏，整曲/片段手动seek、暂停后逐次鉴权继续，片段边界/旧响应隔离/原队列保留。B入口waiting，精确实现后新卡；备份/旧服务保持，main不合并。


### MUS-026完成与准确派发（2026-10-24）

- implementation `d766dcd09df3cc1e54130ca80aefb946985ee2b3`，comparison/scope `0ae63f9d6a4632ffbfa1c0cedc017aad6cea862c`。临时review会话向现有底栏提供曲目/状态/时间及控制，页面range input/暂停继续；保留普通队列，审阅时禁用普通前后首/循环/随机。活动已验证音频内seek，暂停释放/seek保持暂停/继续新GET校验；seek限整曲或片段范围，终点停止后重播从范围起点。
- 固定Node22最终31通过（8包11音频6媒体6真实Pinia-store替身边界）；旧21/初30不累加。普通pending/旧publish/账号/token/取消切歌错标题字节等回归通过。干净实现build通过，旧500kB warning保留，无依赖升级。
- 实际Energy28整曲底栏标题/歌手/模式；页面键盘跳23s/底栏10%，底栏跳转audio54.633564/page54600ms，暂停src释放/从77.718596附近继续，暂停鼠标选中间页面1:55/底栏50%。片段55–65s可跳56s，底栏拖终点1:05释放，再从55.111655s重播；错误SHA拒播/两处进度disabled，离页恢复普通空底栏。
- 手机390 scroll384，实际seek23s/暂停0:23且底栏Energy；桌面1440 scroll1434，截图已视觉核对，最终warn/error空。一次resize后slider超时，快照在/manage/music，原因未确证；重新进入/导入/读新状态后通过，原失败保留不算产品路由缺陷。音量仅UI切换与store转发证据，CUA代理未暴露实际audio.volume。
- 非空队列/迟到普通响应仅store替身验证，未新真实双播放器/撤权矩阵，B按新卡补最小增量。原51包SHA与人工字段/用户草稿未写，QA0/51；备份干净f3b0da1、原后端MUS-014保持。无Java/Python/schema/API/依赖锁/公共JSON/模型或原音频改变，无main合并；细节见verification/MUS-026.md/results.json。
- 检查点B仍0907de09/source7c93a512（025原批准），新MUS-026-R1-B/revision1 assigned未认领，准确reviewedd766dcd/comparison0ae63f9。只B两报告，独立合成HTTP/浏览器，不访问A或重复整个025。文档JSON/hash/链接/fence/diff检查后提交publish并回读，发布不等于B已接收/批准。


## MUS-027占用与026接收（2026-10-27）

- owner A；base d90bfcb；允许 `web/src/views/ReviewWorkspace.vue`、README/CONTRACTS/STATUS/A latest、verification/MUS-027*及B派发；另导入026原字节B报告与接收JSON。不改评分格式/规则、媒体/播放器/后端/依赖/原包，不代填真人标签。
- B feed dc5ec6ce/source dd049fdf、reviewed d766dcd/comparison0ae63f9/assignment d90bfcb/ack76249e30匹配，latest字节/hash、仅两报告已核验。026限定批准接收；B31/build、最终30浏览器/1导出CLI及1预期404/0pageerror均为B报告，不复算私有证据或累加。旧失败和N1开发浮层观察保留，N1非本次评分入口范围。
- 代码证据：fieldset因空/非法alias整体disabled，唯一代号输入在远处页顶。先约定E2评分区就近必填代号/具体格式提示，合法后启用0..3，填写本身不生成判断；清除或非法代号不清空已有判断。B入口暂waiting，准确实现后派新卡。

### MUS-027完成与准确派发

- implementation `2ed661daff6e66856cdef6a6789a9edea7a2dc5d`，comparison `a945927d45d982e7bda22cc7a84dce930787b52f`；仅ReviewWorkspace产品文件，匿名代号移到评分旁，空值/非法明确说明，单独禁用radio不禁用输入。原规则/人工动作/草稿/播放器/备份/后端保留。
- 固定Node22包8检查/build通过，17浏览器断言通过；桌面/390真实指针评分、键盘、清除、切换、刷新后显式恢复及格式提示已验。合成导出固定run CLI通过：0和3各一，其余10null，无真人标签或质量结论。End键未选择值不计成功，Space/箭头通过；手机后续合成草稿改2与桌面导出分开。
- 真实原包SHA/51null不变，原版备份干净f3b0da1；warn/error空，viewport恢复。日志/截图仅.local/a/mus027，未动用户真实草稿。B新卡MUS-027-R1-B/rev1 assigned未认领；准确SHA小增量，不重复026媒体/权限/模型/Java全套。详见verification/MUS-027.md/results.json。


## MUS-028首轮标注接收占用（2026-10-28）

- owner A；base df50001；允许README/PROJECT/STATUS/A latest与verification/MUS-028*。用户文件只读、原字节副本/含人工字段的明细和日志仅ignore的.local/a/mus028，先核对ignore再创建0600。不得修改评分/人工区间/原024空白包；无应用源码/契约/schema/依赖/API变更。
- 既有validate对固定run/report/catalog核对，不新增评分器/训练/阈值或正式质量指标；同会话子代理只读复核不冒充独立B验收。B固定MUS-027-R1-B保持原assigned卡，不能用本接收替换或宣称已认领。
- 首次误用不存在的.local/a/mus022/catalog.json导致exit1/FileNotFound；改回文档的web/public/demo-catalog.json后exit0，保留错误及最终结果，不算产品校验失败。

### MUS-028接收完成

- 用户提交及私有原字节归档SHA774c2083…/44495 bytes一致，副本0600、目录0700；既有固定run/report/catalog CLI对原件及归档exit0。8查询/20曲/51对全部有合法判断；0/1/2/3=19/13/9/10，无人工区间。原空白包及原运行不变，原下载不改，个人代号/逐条记录不入Git。
- 同会话子代理只读复核一致，不是B独立审核。仅汇总/receipt证据文档，未计算模型指标或定位IoU，不能把19/51当Precision/Recall/准确率；未做阈值/训练/线上权限刷新。详见verification/MUS-028.md/results.json。MUS-002仍blocked于模型/效果对照及冻结，后续评测需定义口径、保留本轮，扩库另建版本。
- 本轮无源码/API/schema/依赖/服务改变，不重跑无关应用测试；备份干净f3b0da1，不合并main。B固定027卡原字节保留、仍assigned未认领；检查点同步后发布本机接收汇总，不向B传原始私有标注或外推027批准。


## MUS-029占用与评估口径（2026-10-28）

- owner A；base3e6c517。允许新增services/audio-search/evaluate_review.py及test_evaluate_review.py，模块README，根README/PROJECT/CONTRACTS/STATUS/A latest与verification/MUS-029*。不改旧review_pack/模型/切片/排序/前端/后端/锁/公共目录。
- E4先固定完整人评、两模式原top5顺序、P@5>=2、指数gain的pooled nDCG@5/零IDCGnull与宏均值口径；明细/案例只在.local/a/mus029，原run/已判归档/空白包只读；无Recall/10%提升/阈值/训练。
- 同会话只读代理独立复算方法/数字；另一代理只写新合成test文件，A拥有实现与台账，路径互斥。同会话协作不冒充B审核。B027卡原字节保留，开始sync双方fetched，B仍dc5ec6ce/source dd049fdf；本任务不替换其在途派发。

### MUS-029实现与首次探索结果

- implementation `ef5e38842c6d0cf632d7401d77a61271fb8eb50d`；comparison/scope c206567055416832a67ceead67c922452aefa71d。新增evaluate_review.py/test_evaluate_review.py，旧标注校验/模型/排序不改。P@5>=2/固定5，pooled nDCG指数gain/并集IDCG；原rankings顺序、完整人评/显式双SHA，0IDCG=null并披露/排除nDCG宏均值。
- 新21和旧17合计38通过，不与独立21/首轮18相加；初18有2失败（函数允许None SHA与测试手算漏0.5），已补双SHA校验/修手算，转录摘要而非原始完整日志保留。独立同会话代理复算/审查一致，不冒充B验收。
- 干净实现上实跑exit0：8描述/51已判/20曲，P@5 whole0.40/segment0.45，pooled nDCG0.82985163/0.90620039；P逐query片段胜平负2/6/0，nDCG5/0/3、8有效/0零IDCG。overwrite与错SHA实际exit1且不覆盖/不产物；全部原run/catalog/包hash未变。
- 逐曲私有复查表与结果只.local/a/mus029，0600；Git仅聚合方法/数字。160可能对中109未知，五个弱描述尚67未知；低分不能直接证明库缺类型或模型误排，后续先补核查覆盖再补样，扩库另建版本。不报Recall/定位IoU/显著性/P95/held-out或10%提升，不训练/调阈值。
- 备份仍干净f3b0da1，未重启/升级后端、重做UI/改API/schema/锁/公共目录或合并main；不重跑无关Maven/前端/模型。B027原卡保持assigned，029独立B卡待其返回后协调，不能替换当前任务或称本实现已获B批准。详见verification/MUS-029.md/results.json。


## MUS-030占用与诊断补标范围（2026-10-28）

- owner A；base5c9c55f。允许新services/audio-search/diagnostic_pack.py、test_diagnostic_pack.py；web/src/utils/reviewPack.js、新diagnosticPack.test.js及views/ReviewWorkspace.vue必要提示；README/模块README/PROJECT/CONTRACTS/STATUS/A latest/verification/MUS-030*。旧review_pack/evaluate_review/媒体/播放器/API/Java/schema/依赖/公共目录不改。
- 先E5明确独立schema、基包双SHA/补集重建、5个弱query显式选择、无旧已判对/模型建议、每query<=100，旧E1仍<=10；新指纹/草稿隔离，仅本机.private.ignore生成0600，不覆盖旧包或代填判断。
- 根agent负责Python实现和台账；前端代理独占reviewPack.js/新diagnosticPack.test.js/ReviewWorkspace.vue；测试代理仅test_diagnostic_pack.py。同会话协作非B审核。B027固定卡保持原字节assigned，sync双方fetched，B仍dc5ec6ce/source dd049fdf，不按时间接管或替换。

### MUS-030包与试听入口就绪

- implementation `4e8115c3c19f836359a52860f9fda7820dd6088d`，comparison/scope f07b76893bc9b7964432939818e8d070d815a7f3。新标准库CLI/独立测试，前端helper严格新schema/提示及新测试；旧E1上限/媒体/播放器/评分/草稿行为保持。
- 已产出.local/a/mus030/diagnostic-review-pack.json，5query 13/13/15/14/12=67全null、18不同曲目，无旧已判对；44966bytes/0600，SHA b706492f…，dataset77cf9d56…；基包SHA774c2083…及原51判断不变。
- Python53（旧38+新15）、Node39（旧31+新8）/build通过，不与独立定向重复相加；真实浏览器20断言及合成2判断1区间/真实0-67导出CLI均通过。原51包兼容导入51/51；What Is Love试听、暂停释放/21.2s暂停seek、底栏一致，390/1440无横溢，截图已看，warn/error空/viewport恢复。首次seek读到loading后按后续实际暂停态复核，未把中间态当最终完成。
- 原run/catalog/空白包/完成标签与原下载前后SHA不变；原用户草稿未写，最终独立页面导入0/67待用户，评分未代填。完整命令/哈希/限制见verification/MUS-030.md/results.json。无Java/API/schema/依赖锁/公共目录/模型或后端变更、不重启、不重做UI/合并main，备份干净f3b0da1。
- B027固定卡保持原assigned，030尚无独立B批准；同会话只读代理/测试代理路径隔离，不混称B。当前仅67判断待用户供给；补完才判断漏召回/覆盖问题，非盲评/held-out，不自动融合、训练/定阈值/扩库。

## MUS-031补充标注接收与覆盖诊断占用（2026-10-28）

- owner A；base d9f6f2dadb075ffd537385a350f9c24d1047fcaa；branch codex/MUS-031-diagnostic-receipt。允许README/PROJECT/STATUS/A latest及verification/MUS-031*；只接收、既有CLI校验、原字节私有归档和汇总诊断，不改应用/契约/schema/模型/排序。
- 用户新67与原51及run只读，先核对ignore再在.local/a/mus031独占创建0600副本/日志。仅在分析内存按query-track对照，原两包各自保留，不生成可重新导入的混合schema，不修改或补填真人判断；公开只放聚合/哈希/方法。
- 同会话代理只读复核非B审核；固定B027卡原字节保持。开始sync双方fetched，B仍dc5ec6ce/source dd049fdf。诊断仅这五条描述×固定20曲，相关为>=2；不将其外推正式测试或8描述全量，不调参/训练/扩库/合并main。

### MUS-031接收与诊断完成

- 用户原件及私有原字节归档46306bytes、SHA38f8a4d0…一致，0600/目录0700；既有CLI对原件及归档exit0。5query/67已判/0未判，0/1/2/3=59/6/2/0，0人工区间，18不同曲目；新旧对无重复，累计118/160，等级78/19/11/10。
- 五描述各20曲完整，共100对，等级77/16/6/1、>=2共7对；原池5、补池2。原声/摇滚/钢琴/爵士/管弦分别2/1/1/2/1相关；整曲top5分别1/1/1/0/1、片段1/1/1/1/1。新增相关原声/爵士各1均在两原top5之外。支持这些具体描述下素材适配稀少与排序漏选同时存在，不称类型完全缺失或正式模型效果。
- 仅内存对照，未生成可导入混合包/逐条公开人评；private分析脚本、校验日志与原始包在ignore.local，公开聚合/哈希/方法见verification/MUS-031.md/results.json。同会话只读复核与CLI/计数一致，非B审核；原run/向量/catalog/原51/两空白包/下载/B027卡SHA全部保持。
- 原029指标口径与数值保留，不把五描述诊断混成八描述全库结果；其他三描述42对未知。无新排名指标/定位IoU/P95、模型重跑/训练/阈值/扩库；本任务仅文档和私有接收，不重复无关应用测试。下一步针对具体描述补充素材、另建独立测试和模型对照；不提前冻结discovery-v0。
- 检查点sync双方fetched，B仍dc5ec6ce/source dd049fdf、027卡assigned保持；原版备份干净f3b0da1，未动前后端/服务/依赖/API/schema或合并main。原始包不跨账号发布；本机收件与同会话复核不等于B独立验收。

## MUS-032定向来源候选占用（2026-10-28）

- owner A；base2e2db1e；branch codex/MUS-032-targeted-corpus-candidates。允许新scripts/collect_research_music.py、test_research_music.py、services/audio-search/targeted_sources.json，README/PROJECT/CONTRACTS/STATUS/A latest及verification/MUS-032*。先E6固定source-only身份/仅development/独立输出和不代填人评；不改原importer/corpus/probe、前端/Java/依赖/公共catalog。
- 计划五描述各4新曲，先以官方作者来源/CC BY4.0/元数据筛选，再固定ISRC下载并实际解码，原字节与证明只ignore.local/a/mus032，文件0600/目录0700；旧曲按内容hash排除。研究代理只读查来源，测试代理只写新test，A独占实现/selection/台账。同会话非B审核，B027原assigned卡保持。
- 现有Jamendo热门导入不能增量且会覆盖旧公开catalog；本轮不用旧入口。官方Jamendo API另有离线/缓存条款，新增素材改由作者官网明确CC授权/下载入口获取；保留旧证据、不据新调查改写历史验收或作法律结论。输出不是Java已导入曲库，也不是已确认相关曲目或独立测试；后续真实ID映射与独立版本另立集成检查。

### MUS-032收集与全解码完成

- 新收集器/固定selection仅标准库，无依赖升级；18项合成边界检查通过，同会话只读代码与真实全解码复核一致，非B。真实batch-01收20/20、各bucket4，共115494136bytes，20内容与旧20无交集、无新重复；manifest SHA2747406a…，source-only无JavaID/owner，全部human_relevance null。
- 20/20 MP3全帧读完、有限值、SHA/完整证明/官方metadata record匹配，实际总3189548ms、最短52702/最长244102ms。官网时长仅14/20在2s内，另6差+2561..3659ms，保留差异并以实际音频时长用于后续窗口。首核验把2s当必需断言失败已保留；不裁音频或覆盖metadata掩盖差异。
- 三份许可依据为官方完整catalog、通用动态曲目展示/署名下载模板、许可说明快照，非20份静态逐首许可页。全部为Kevin MacLeod，已知描述定向选样，只用于development，不能声称已确认20正例或held-out。完整音频/证明/原快照/日志仅ignore.local/a/mus032，0600/目录0700；公开仅代码/ISRC清单/聚合/哈希。
- 真实重名输出exit1/FileExistsError，44个批次文件hash不变；旧音频/证明/selection/ledger/result/run/catalog/118判断/B027卡共55文件前后SHA保持。首次环境预检误查Sonora本地cache/venv路径（不存在），改回022文档的原版共享只读环境后通过，不算产品失败或解码通过。
- 本任务无UI/Java/API/数据库schema/依赖锁/公开catalog/服务或main变化，不重跑无关Maven/前端/CLAP。下一步033需真实owner/JavaID与新provider适配，不能直接把ISRC包送旧probe/审阅页。B027固定卡保留，032独立工具卡待前卡返回后协调；细节见verification/MUS-032.md/results.json。

## MUS-033占用与新素材核查（2026-10-28）

- owner A；base7704051；branch codex/MUS-033-source-import-review。允许新增scripts/import_research_music.py、test_research_import.py；services/audio-search/source_review_pack.py、test_source_review_pack.py；web/src/utils/reviewPack.js、新sourceReviewPack.test.js和ReviewWorkspace.vue必要提示；README/模块README/PROJECT/CONTRACTS/STATUS/A latest/verification/MUS-033*。不改旧importer/corpus/probe/播放器/Java/API/数据库schema/依赖锁/公开catalog。
- 先E7固定新source-only到真实Java ID的HTTP映射与两新私有格式；原20/118/032批次只读。计划20新曲普通owner导入、每首Range/完整SHA核验、独立40曲catalog和仅20条新素材判断；无假checkpoint、模型结果或自动打分，不要求重做旧标注。40曲检索/held-out后续另建。
- 导入代理独占新importer/test；Python包代理独占source_review_pack/test；前端代理独占reviewPack.js/新test/View最小提示；A串行台账、实跑、浏览器和交接。开始sync双方fetched，B仍dc5ec6ce/source dd049fdf，027固定卡原assigned保持；同会话代理非独立B。
- 真实UI增量发现Morning整曲已通过SHA/字节但浏览器时长153253.22ms短于soundfile153555ms，触发100ms保护拒播。范围扩展仅web/src/utils/reviewAudio.js及既有test：新来源整曲经完整验证后取两种时长较小播放上限并共享seek/继续；不改原包时长、旧schema/片段保护、底栏布局或原队列。修复后必须真实播放/暂停/seek并保持0/20人工字段，不能把初次拒播记为passed。


### MUS-033本机交付与B027接收检查点（2026-10-28）

- 源码实现dc7e1e4，整曲播放修复f9192fc；27导入保护+72包相关/68 Node/build通过，实际导入重复运行均40且catalog SHA一致，新增20 pending/无自动审核。真实整曲/底栏/暂停/seek/继续与0/20导出CLI通过；合成包2/20+区间/草稿恢复独立验证，不代填真实人评。
- 新私有40曲catalog SHA1cf24cff…，新包20不同曲目/五描述各4，dataset b225ef4d…，初始20条人工四字段null。旧音频/证明/run/catalog/两完成及两空白包/032批次共99非任务卡输入哈希保持；100项原保护检查在B卡更新前全通过。随后仅固定卡因接收027/派发033按明确状态变更，不把其变更隐藏成仍100项不变。公开目录仍20，不写原版配置/Java/数据库schema/依赖/模型，不重做UI或合并main。
- 浏览器Morning153555ms/153.25322s与Hot Swing52702ms/49.999979s差异均保留，验证后以较短整曲端点播放；原片段/旧schema100ms保护保持。只读审计发现fresh恢复53ms边界缺口后修正：内部保留原整曲requestRange，每次获取重算min，位置>=新终点拒绝；最终独立合成复查关闭。非B审核、非decoder时间完全等价。
- 结束检查点sync读到B feed44a7f90a/source f9911e5，精确027/rev1限定批准；A核对feed/source latest哈希、两允许文件、reviewed2ed661d View SHA与原字节报告，接收docs/verification/MUS-027-B-acceptance.json。B最终25浏览器断言/两导出/8 helper/build是其报告范围，非真实服务/人评；两早期blocked不累加。027完成，033新卡assigned，不冒充认领/批准；032等旧工具独立审核未自动关闭。
- 允许文档范围扩展为B027原字节报告导入、027接收记录与固定dispatch/033卡；A串行维护，B own latest不改。A latest ack最新B feed，提交后原子publish/回读。下一步只收新20真人核查，再协调provider-aware新run与独立测试；旧118不需重做。

- 发布前交叉复查另发现新source浏览器时长下限仍1ms、与Python30s不一致；已仅新schema收紧到30000–600000ms，fixture/29999拒绝与30000通过边界补齐，原两schema保持。提交10880f8，最终68Node/build通过，独立内存重签复查关闭；B033准确审核输入更新10880f8（尚未发布派发，无重复修订/认领）。


## MUS-034新20素材标注接收占用（2026-10-28）

- owner A；branch codex/MUS-034-source-label-receipt；base7879a7d1494ce8822bf2aaf2e144e321112964de，依赖033。用户交回新source-review包，先以既有E7 CLI固定manifest/decode/import catalog/query fixture/selection/旧基线重建，核验人工字段与完成度，再以原字节私有归档、统计五描述素材适配。
- 允许README/PROJECT/STATUS/A latest及verification/MUS-034.md/results.json；私有收件/分析/日志只ignore.local/a/mus034、0700/0600。原118/旧空白包/新20空白包/40catalog/音频证明/旧run/B033固定卡只读；不改应用/CLI/模型/API/schema/依赖或重跑模型/合并main。
- A独占归档与台账；同会话代理只读固定CLI复核/聚合，非独立B审核。开始sync双方fetched，B仍44a7f90a/sourcef9911e5，033/rev1 assigned保持，不替换/冒充认领。此次先完成收件与素材判断汇总，40曲provider-aware模型对照后续另立。


### MUS-034接收完成检查点（2026-10-29）

- 用户下载16218字节，SHA eccc4af2c765bcc2dab45c43e5abc9afc9e0ded65d64890e29266c0c44353c96；固定E7下载/原字节归档两CLI exit0，20/20已判、0/1/2/3=0/0/0/20、人工区间0。五query各4新音乐/20不同曲目，与原118 query-track无交集，累计138、等级78/19/11/30。
- 原20完整五query的相关2/1/1/2/1，加本次每query4，现已知相关至少6/5/5/6/5；每query仅24/40已知（16未知），非全40相关真值/模型P@5。8×40为138已知/182未知，五query120已知/80未知。只内存关联，不写混合schema或把未判当0；原029指标保持。
- 原件/旧已判及三空白包/40catalog与80副本/032/旧run/B033卡等186文件SHA保持；private0700/0600、原版干净f3b0da1。分析JSON实际有效，一次多余格式预检误判条件导致断言与不存在的final脚本路径失败，未改变有效分析输出/包；记录私有preflight-note，未将该尝试记passed。
- 仅本机接收与文档，无应用/工具源码/API/schema/依赖/模型/服务或main变更，不重复无关Maven/build/CLAP。独立同会话固定CLI/计数复核一致，非B，B033/rev1原assigned保持；开始/检查点sync以最新实际结果为准。下一步MUS-035先建provider-aware40曲新run/模型候选对照，独立测试版本另立，当前素材评价不等于质量提升。


## MUS-035范围与占用（2026-10-29）

- owner A；base b42b767afc0bd3ddb76601a436f8073c3d72106c；branch codex/MUS-035-expanded-retrieval。先E8冻结40曲双来源/固定同模型全量重新编码、8原查询/两mode排名、五目标描述P@5上下限与unknown显式计数，未判不补0、不调阈值/训练。旧source/code/138人评/原20run/03340catalog/音频证明/公共catalog只读。
- 允许新增services/audio-search/research_corpus.py、research_probe.py、research_evaluate.py及三独立test；README/模块README/PROJECT/CONTRACTS/STATUS/A latest/verification/MUS-035*。私有输入保护/运行/分析仅ignore.local/a/mus035、0700/0600。无前后端/旧probe工具/依赖/API/schema/模型版本/共享缓存或main改变。
- 语料代理独占research_corpus/test；运行代理独占research_probe/test；评估代理独占research_evaluate/test；A串行契约/台账、源码审查、真实模型运行及独立工件复算。同会话不算B。开始sync双方fetched，B仍44a7f90a/sourcef9911e5，033/rev1 assigned原卡保持，不接管或替换。

- 035真实run-01失败保留：旧20全部编码后Morning触发旧decoder的完整性保护（sf头部6771806帧，read实际6761088）。调查证实032 blocks()计yield长度含估计末尾，旧frame/duration证据需明确纠正而非填零或改旧报告。E8新增来源实际EOF读取版本/declared与actual分存，旧20 decoder不动；三代理仍只改本任务六新源码。修复后另run-02完整40重新编码，不复用run-01部分结果；历史138标注只按track/content关联，原人工区间0保持。


### MUS-035成功运行与勘误检查点（2026-10-29）

- 基础实现895af4b，实际EOF修复/干净实跑17a31f5d5f4a04873d299c52f722dd3a890b9b5e；run-02完整40（两来源各20）、1557片段/40整曲/8文本/0新参考，512维，7892191ms实际音频，137.924s单次离线构建。独立NPZ/范数/完整窗口/16组top5重算通过，原20向量/文本最大差0；新run6工件与251保护/54共享cache文件保持，实际重复output exit1且6工件不变，无模型重入。
- 最终168 tests（旧95+新22/29/22）通过；早期154与代理子集不累加。真实新20 EOF与两种read块帧数一致，float32有<=2.980232238769531e-7舍入差，固定65536来源版本。旧032/033 duration实际是头部估计：20/20 header高于EOF，旧总3189548ms、actual3169945ms，多19603ms；actual20均与官网整数秒在-433..+464ms内。旧6个>2s差异不能继续当实际录音时长差，旧报告/包仍原字节保存，时间定位只能用035 actual版本。
- 五目标原20 top5相关4/25与5/25，新whole23相关/0已知负/2未知、segment24/0/1，macro上下限0.92–1.00/0.96–1.00，exact均null。两mode各有20个新素材确认对进入top5；unknown并集3、交集0。只适用于定向development语料变化，非模型训练/held-out提升、全库Recall/定位IoU/P95；原029八query池内指标不改。
- 评估使用三包显式SHA重建，原138只内存关联，evaluation重算另output byte-identical且CLI exit0，同会话独立原排名+标签计数一致，非B。一次私有包装漏import os，子CLI已产出结果但记录阶段NameError；另包装输出recheck成功，原包装失败保留不记passed。首次模型run-01失败/PCM位级一致性误设/两合成测试准备差异均记录，不覆盖旧证据。
- 只新增六离线源码/测试与必要文档；无Java/Vue/旧工具/依赖/API/schema/模型版本/服务重启或main合并。B033/rev1固定card字节保持，feed仍44a7f90a/sourcef9911e5，工具035独立审核未派发/未获批准；A latest披露033历史时长勘误，不修改B自身feed。下一步036仅补3未知对并冻结新时间/包指纹，独立测试与discovery-v0另立。

## MUS-036范围与占用（2026-10-29）

- A集成，base9797ed4b8766f8cd5f6cd7759b86bd309cef2f7d，branch codex/MUS-036-top5-supplement，先E9冻结再实现。允许新增services/audio-search/supplement_pack.py及test_supplement_pack.py，web/src/utils/reviewPack.js新分支/新supplementPack.test.js、ReviewWorkspace最小提示；必要README/模块README/PROJECT/CONTRACTS/STATUS/A latest/verification/MUS-036*。旧三schema/播放器/原工具/035源及所有人评/音频/模型/run只读。
- 后端包代理只写supplement_pack/test；前端代理只写helper/新test/View；A串行契约/台账、私有生成与浏览器核验，同会话代理非B。私有仅ignore.local/a/mus036，0700/0600，不改数据库/API/锁/模型、不重做UI/合并main。
- 开始sync A bf1f855/source9797ed4，B16b06c8/source4f57837；收到033/rev1 approve_scoped，准确reviewed10880f8/base7704051/ack bf1f855，已完成只读来源与报告核验，待A原字节归档接收及独立035新卡串行更新。不改B自身latest，不将033批准外推035/本轮。
- A接收033原字节报告SHA3c41a66a…及receipt；核source/claim仅两允许报告、准确卡来源9797与五源码SHA，A未收到/重算B私有证据。B27 importer/72包/68 Node/build、独立15断言+7 Node、最终23浏览器/三导出均按B报告记录，早20断言失败不累加。033历史时长不受本批准认证。旧033卡保留，固定入口明确转035/rev1准确9797，新卡仅离线三工具及合成复核；本轮036另列，不静默捆绑批准。

### MUS-036包交付检查点

- 实现bde85a1、权限修复/真实build125076d3d9bd336ab7928dcd7f9ecd9a0a8a3316；包4284bytes/SHA85f1ac61000aad1ed9b86e9b2662ee799b647d92ce6dc0378a76c5113bf1780d，dataset4c00b2ee…，2query/3不同音乐，exp04为1、exp07为2，全null/空建议。固定evaluation+原11pins完整重建，actual时间；build/validate exit0，重复输出/错pin预期exit1且不改输出。
- 最终188 Python（原168+新20）/77 Node（原68+新9）及现有lock build通过；极端umask创建mode000的合成审计问题已fchmod+回归关闭，E9澄清可复用CLI私有目录与本轮实际目录，早187/代理子集不累加。独立合成Python→JS→Python 10未知/测试2判断1区间通过，非真人/B。
- 实际原账号/服务三曲完整媒体校验/底栏/暂停/20800ms暂停seek/恢复及切query释放通过，18断言；0/3浏览器导出对象与原包相同且固定CLI exit0。默认668宽无横溢，未强制改视口/称390或1440实测。最终原空白包留页、alias空/无draft恢复；新包核验warning/error0。
- 私有初次包装日志与前端build.log重名，CLI后日志阶段FileExistsError，不记包装passed；另v1包和pack-*日志真实成功，原输出保持且逐字节相同。首次登录跨build旧chunk两错误保留，reload后新构建核验通过，不修改产品绕过。原版干净f3b0da1，259保护中258不变，唯一计划变化是A dispatch033→035，旧033卡/54缓存/模型/138/run/原音频保持。
- 本轮只包CLI/测试与最小前端分支/说明、必要文档/B接收派发；无Java/API/schema/锁/模型版本/服务重启/UI重做/main合并，无关Maven/模型不重跑。同步末次06:29:53Z双方fetched，B仍16b06c8/source4f57837；035/rev1 assigned不等于已认领，036未受B独立批准。下一步等3条真人导出交回再另立接收/精确开发比较，035当前未知和指标保持。

## MUS-037范围与占用（2026-10-29）

- A集成，base49c255ccdd528a68995fef3fffdf178cd2605d32，branch codex/MUS-037-supplement-receipt；先E10冻结补判接收/五描述固定原排名、>=2/5条等权P@5再读新评分。只改README/PROJECT/CONTRACTS/STATUS/A latest/verification/MUS-037*，私有归档/一次分析/独立复算仅ignore.local/a/mus037，0700/0600。无源工具/前后端/依赖/API/schema/模型或main改变。
- 原51/67/20、036空白/浏览器导出/用户下载/旧新run/原音频证明/checkpoint/cache/035 B卡只读。A串行归档与台账；同会话代理仅独立只读复算/自有聚合输出，不算B审核。开始sync双方fetched，A52ef10/source49c255c，B16b06c8/source4f57837，035/rev1仍assigned原卡保持；本轮不替换或冒充认领。

### MUS-037接收与对照检查点

- 新原件4344bytes、SHA1147aacb6befc1ed1d90ad56b865db8c027ae833360b5e3ed4dc6396a691c779，dataset4c00b2ee…；下载及原字节归档固定12pins CLI均exit0，3/3已判、0/1/2/3=1/0/1/1、0人工区间。私有仅.local/a/mus037、0700/0600，原件/空白包/旧138不写，四完成包分开保持，累计141、等级79/19/12/31。
- E10先冻结五query/原两mode top5/相关>=2/每条5与五条等权后读标签。新40whole25相关/0负/0未知、segment24/1/0，精确P@5=1.00/0.96；片段仅exp07为4相关/1负，其余四query两mode均5相关。旧20同五querywhole4/25=0.16、segment5/25=0.20，原035区间和029八query不改。
- 根侧私有分析与独立同会话固定输入/原排名复算逐query/模式/覆盖一致，独立聚合SHA8ffd50bb…，非B审核。仅内存关联query/track/content，不混schema、不重排/训练/调阈值或跑模型。8×40仍141/320已知、179未知，目标五query123/200已知、77未知；无新nDCG/Recall/IoU/P95/显著性/独立提升。
- 284保护文件SHA及54cache常规文件集合保持，原备份干净f3b0da1，原8080/5175 PID保持未重启。只原件接收/私有分析/文档，不重复无关应用单测/build/浏览器/CLAP，也不将036历史188/77当本轮运行。同步末次16:10:26Z双方fetched，B035/rev1仍assigned且原card/dispatch字节保持，不外推033批准；无API/schema/依赖/UI/模型版本/main变化。下一阶段038先冻结独立评测/模型对照方案，当前五描述不充作held-out。

## MUS-038范围与占用（2026-10-29）

- A集成；baseefd7be584b9f30e61ac86474c038d0d79f43ec39；branch codex/MUS-038-independent-eval-protocol。允许README/PROJECT/CONTRACTS/STATUS/A latest、docs/evaluation/MUS-038-protocol.md及.json、verification/MUS-038*。仅可复核计划/官方元数据/既有实现事实；本轮不采曲/下载权重/新编码/改检索工具或UI/生成新标注包，actual新曲/query/人评均0。
- A串行编写协议与台账；同会话代理只读指标/泄漏/官方模型候选研究与审查，非B。私有来源元数据/保护记录仅ignore.local/a/mus038，0700/0600。旧40/141/8原query及179未知均development，原始素材/标签/run/缓存只读。
- 开始sync双方fetched，A0ea759a/sourceefd7be5、B16b06c8/source4f57837；B035/rev1准确9797卡/dispatch保持assigned，未经独立feed不替换/冒充已认领。仅提出未来候选checkpoint，不修改当前模型版本/依赖/API/schema/服务或main。


### MUS-038方案完成检查点

- 设计JSON/MD与E11已冻结20新曲×8新英文描述/160全矩阵、四批各40；原20×五描述已有100完整判断复用，全部旧40/141/179未知仍development。新test索引仅新20，至少5未进入旧材料的作者/合作/作品群、每群≤4；不把预训练未见或总体代表性作为事实。
- 采样框提供方/纳入条件/枚举快照SHA先于新query编写/披露冻结；query作者不看候选，后续按固定hash队列/技术边界取20，不按相关度凑正例。数量不足blocked/另版，不放宽作者规则。G2固定本地模型/源码/环境/全部配置，标注者侧保管/校验qrels至G5；之前仅收SHA/总完成数/合法性，160完整与五runs哈希齐全后才一次解封。
- 两个官方同架构不同权重CLAP候选，各whole/segment共四声学组，加固定标题TF-IDF sanity；主Bwhole−Awhole，三次比较与全部配置预注册，不按dev胜者删组，不归因speech因果。B仅固定revision官方元数据核验，本地下载/严格加载/512/兼容仍待040；不修改当前模型/环境。
- 42项一次性文档一致性与假设指标边界核验通过（非42应用测试/真实评测），同会话三方向只读审查完成，非B。首次Python HTTPS信任链失败保留；正常TLS的系统curl重试仅元数据成功，未绕过证书或下载权重。294保护输入与54cache文件集合/哈希、B035卡/dispatch保持；原版干净f3b0da1，8080/5175原PID未重启，私有0700/0600。
- 检查点2026-10-29T21:07:32Z双方fetched，A仍0ea759a/sourceefd7be5、B16b06c8/source4f57837；035/rev1准确9797原assigned，不替换/冒充认领，033批准不外推本轮。本轮仅九份文档，不改工具/Java/Vue/API/schema/锁/模型/服务/UI/main；无新曲/query正文/标签/包/模型run，未运行无关应用构建或测试。细节verification/MUS-038.md/results.json。
- 下一步039才做来源/描述/分组与实际manifest，再040新契约/runner及B安全dev预检；现有旧包/页面不支持新独立格式。本方案完成不等于MUS-002正式质量、discovery-v0冻结或上线完成。


## MUS-039范围与占用（2026-10-29）

- A集成；basebc653e05eb722224bdd6ca395a0835ffeafab910；branch codex/MUS-039-independent-corpus-freeze。允许新独立source-only收集/验证工具及合成测试、来源框/新query规范文件，README/模块README/PROJECT/CONTRACTS/STATUS/A latest/verification/MUS-039*；旧工具/包/标签/模型/缓存/公开catalog及038协议原字节保持，不改Java/Vue/API/schema/依赖/UI/main。
- 先冻结来源提供方/纳入条件/枚举快照SHA，再由未看候选的独立同会话代理编写8新英文query与中文可听说明；采样方在20曲/替补队列冻结前不读新query，按038固定hash队列/cap4/≥5新群与技术边界收集20，实际EOF65536读取，新来源只写ignore.local/a/mus039、0700/0600。若来源数量不足如实blocked，不以相关度换框。
- A独占台账/契约/来源采样与实际运行；来源代理只读官方目录/许可，旧群代理仅旧40身份/作品，工具代理先只读实现建议；同会话非B。开始sync2026-10-29T21:16:59Z双方fetched，A860729d/sourcebc653e0，B16b06c8/source4f57837；035/rev1原assigned卡/dispatch保持。本轮不下载模型/跑分/生成可标注test包/导入数据库或读取新标签。

- 039第一检查点：全132条官方loc-fma元数据/逐首rights与模板等137快照已冻结frame SHA a9fd0079…；公开回执独立记录，freeze时query正文/音频下载均0。LOC现场页本机HTTP403如实保留，固定官方GitHub元数据正常TLS可读，整曲S3 HEAD200；不绕证书/鉴权。27个署名字面值不是27个独立作者，别名/合作/许可冲突仍在审查；旧40关系种子仅元数据，原307保护文件保持。先提交E12与frame回执，再让隔离作者编写query，尚未采集20曲或完成G1。

- 039第二检查点：初框完整重建+group review126可技术筛选/6隔离，作者cap4/同work首项理论仅19（实际音频0），feasibility-v1保留；新collector19合成检查/真实三pins只读校验通过，代码968b022。未放宽隔离/凑20，按原协议允许另版：v2全部132FMA+89MusicBox共221/新92快照，原8query保持封存且弃用，采样方未读正文；v2框先提交后才编写8条新描述。MusicBox官方MP3是视频item音轨派生版，原字节保留并披露，项目共享创作者池保守合一群cap4。实际20采集/G1未完成，B035原卡仍保持。


### MUS-039 G1完成检查点

- v1容量仅19，8条query原字节封存且采样方未打开；新协议83bc7bf3…/新框d4f2faaa…先在2ab6c94提交再另写新8条。v2全部221记录（132 FMA/89 MusicBox），212可技术筛选、9隔离、11可用群/理论23；原FMA决定不放宽。MusicBox同一录制项目保守一群cap4，原媒体可为音频或视频，下载保留官方整item MP3派生字节，不称原母带。
- 干净e668a745b67b1d914cd03d9223848a3679bfe4e6真实收集exit0，20条（16/4）、9群、20作品群；61,224,732bytes/3,824,645ms，32–441秒。221优先队列处理176：20入选/156排除（147群上限/8隔离/1实际14.984秒过短），余45未处理，不称其已解码。source manifest cf320f06…/dataset2172565f…/完整queue4dbcb6ae…。
- 最终26新合成单测通过，旧19/代理子集不累加；真实三pin输入重建221/276证据通过。独立同会话代理复核全部21保存音频实际EOF、20入选PCM/原字节/证明及176完整流程/156排除，297输入hash保持，非B。重名实跑预期exit1/FileExistsError，原91文件字节保持。保留LOC403、初框不足、审计准备错误及根侧误认未入选路径的纠正，不计为成功检查。
- 22:03:38.619Z先冻结20曲与完整替补队列，22:04:08.088Z才首次读v2正文，8条与封存源5c828557…逐字段相同；公开fixture6b3af0cc…。另8条v1依旧未读/弃用，整任务创作16、活动8。新query来自未看候选/模型的隔离同会话AI，非真人/B；两probe不保证0正例，不按可用素材改描述。
- 新20仍source-only、无Java ID/owner，未导入数据库/生成160项新包/模型或向量run/读取新标签。旧40已导入/141已判/179未知、四原包/两run/037开发指标保持，页面不会自动看到新20。后续040补普通owner HTTP映射/权限Range/SHA、新test契约/runner和B安全dev预检/G2，再生成新包，qrels仍G5才解封。
- 307保护文件SHA与54共享cache常规文件集合/hash保持，原备份干净f3b0da1，8080 PID96842/5175 PID4143未重启。首次私有权限终检发现两个新官方快照0644，改mode到0600且字节保持，失败报告保留，重检0700/0600通过。无应用/API/schema/锁/依赖/当前模型/UI/main变化，未重跑无关Maven/build/浏览器/CLAP。
- 检查点22:12:13Z双方fetched，A860729d/sourcebc653e0，B16b06c8/source4f57837；ack B，035/rev1准确9797/baseb42b767原卡/dispatch字节保持assigned未认领。同会话复核不算B批准，不外推033。G1完成不等于工具独立验收、预训练未见、声学无近重复或正式模型质量；详见verification/MUS-039.md/results.json。


## MUS-040范围与占用（2026-10-29）

- A集成，branch codex/MUS-040-independent-runner-preflight/base74645de71c173c43811d7d0d98548089a1836491。先E14冻结第一检查点：B035原字节接收/非阻塞N1权限修复、新固定双checkpoint安全加载器和旧20×五query开发预检；允许research_probe/test_research_probe的最小权限修复，新checkpoint_model/preflight及对应测试，必要契约/台账/README/模块README/A latest、B原报告/acceptance、B下一有界卡及verification/MUS-040*。本轮不启动子代理，所有修改由A串行完成，不伪装B。
- 新私有目录仅ignore.local/a/mus040，0700/0600；745旧文件建立保护基线，原039 source/query/两run/141判断/原A模型/cache/备份保持。允许有界改动旧driver与其测试、B035 dispatch接收/转新卡须逐项列明，不把预期修改记为全部保持。
- 开始sync2026-10-30T01:09:09Z双方fetched：A9aa68ee/source74645de，B610c03e/source0e8de159。已核B035/rev1准确9797/baseb42b767、assignment74645de/ack9aa68ee及claim d674271/a2f53b2；交付仅两允许文件/六源码字节同reviewed，原报告d5fc9e15…归档。批准仅合成/静态，B原生45入口缺依赖blocked；36原生/37显式shim/49独立观察分开，不外推真实加载/EOF或040。
- N1 P3修复前仍待处理。039已冻结新20/8query不改，040第一检查点只用原20/原五query及旧100开发判断；本轮新B下载/严格加载不切换原应用模型，不升级依赖。新20普通owner导入/新test适配/G2/160包/模型test/G5尚未实现，不提前收可读qrels。


### MUS-040第一检查点完成

- E14先冻结范围再实现；干净源码de255c7724926c6f823abceecf0b9a487a467d6d实际运行。B035报告d5fc9e15…/acceptance原字节归档，准确9797/baseb42b/assignment74645de/ack9aa68ee及claim链/六源码一致；不重算B私有证据、不将37shim或原生blocked记真实加载通过。
- N1仅3行chmod/fchmod、两新回归，真实OS/NumPy准确源码函数旧000→新0700/0600/0600且读回/重复拒绝通过，非独立B。原035卡保持；已接收035后dispatch转035-R2/rev1准确de255c7/base74645de，仅N1，assigned未认领，不外推040。
- 新checkpoint_model/preflight及两测试，双固定模型SHA/大小/filename、weights_only/mmap/CPU/strict/唯一非学习buffer例外，原模型常量不改。B正常TLS下载2352471003bytes/SHA51c68f12…，私有models；原HF/runtime只读，无依赖安装。旧20首全新编码933片段/5文本、512维/strict空缺键，约91.737秒非P95；新20/8描述不进模型。
- 最终96相关原生合成测试（research75含新2、checkpoint21），早20子集不累加。A分脚本NumPy不用driver窗口/聚合/排名函数，复核933窗口/20整曲均值/10排名与哈希/finite/norm，通过，均值差约1.49e-8；同操作者非B。真实重名预期exit1/FileExistsError，原52文件SHA保持。
- 排名保存后固定E1/E5 CLI重建旧51/67原包，五query×20全100已判只在内存关联。A复用022原排名whole4/25、segment5/25，B新预检5/25、5/25；宏0.16/0.20与0.20/0.20，只多原声1位置，不宣称显著/独立提升或据此换模型/删配置。旧40/141/037原开发指标保持，不改人评/新query。
- 745保护文件744原字节保持，唯一计划变化A dispatch在接收035后转N1；54共享cache集合/SHA保持，原备份干净f3b0da1，8080 PID96842/5175 PID4143保持；私有0700/0600。仅模型预检/源码/文档，无数据库/Java/Vue/API/schema/锁/依赖/原版/UI/main变动，不跑无关Maven/build/浏览器。
- 检查点2026-10-30T01:35:24Z双方fetched，A9aa68ee/source74645de，B610c03e/source0e8de159，已ack。040仍in_progress：新20普通owner HTTP身份/权限Range/SHA、独立test资产/五配置runner和词面对照/新包/UI最小适配及G2待实施；160包/test run/新判断仍0，不提前读test qrels。详见verification/MUS-040.md/results.json。


### MUS-040第二检查点范围与占用

- 延续codex/MUS-040-independent-runner-preflight，从48eeeca6c3891d2930f0423d80f6526387e5dc5e干净开始。A串行新增scripts/holdout_assets.py、import_holdout_music.py及各自合成测试，E15、必要README/模块README/PROJECT/STATUS/A latest、verification/MUS-040-phase02*；现有importer/corpus/DSP/Java/Vue/模型/038与039冻结文件只读。私有仅ignore.local/a/mus040/phase02，0700/0600。
- 先绑定原039框/审查/source20/G1收据和原033私有40 catalog，再普通owner现有HTTP导入新20，不改旧身份/metadata/catalog、不提权或自动审核。新20需实际EOF/PCM复核，独立新catalog/40音频证明副本、真实Range/full SHA，断点可恢复但不重复创建；本检查点不输出标注包/G2/test模型排名或读取新qrels。
- 2026-10-30T01:39:22Z sync双方fetched，A95ce190/source48eeeca，B610c03e/source0e8de159；B035-R2原卡/dispatch保持assigned未认领，不按等待时间接管/更换。本轮无子代理，N1独立审核与新导入范围分开。


### MUS-040第二检查点完成

- 源码2b2d28796bcd8c74aa96f45f9f38bc602d309220真实函数exit0约12.955秒，新20上传/metadata各20；原40前后真实ID/metadata/Range/full SHA保持，新20全pending，账号资源60，不代表全数据库总数。binding56b74cd1…/catalog ea7eb53a…，source dataset2172565f…保持；新20实际65536EOF/PCM与G1全部相同。
- CLI同目录实跑exit0约9.660秒，新增上传/metadata0，42核心文件保持；共享只读资产适配器可重建全部221框/404输入、原40排除内容集合、新20来源/组/真实身份及独立副本，无qrels/模型输入。原曲名max100/作者串max40原样，无截字或素材替换。
- 78相关合成检查通过（原source26/import27、新asset10/import15），初23的metadata响应丢失注入因fake状态复用未触发，已分离子例状态，不累加失败/子集。保留首次许可http/https等价初检拒绝、额外HTTP100分页准备误差；修复仅严格CC BY规范化/核查脚本20分页，原件/应用不改。
- 额外A分脚本直接关联G1/catalog/HTTP，角色USER、60身份集合=旧40+新20、新20pending/真实file ID/Range206/full200 SHA及匿名20次401均过；非B或独立操作者，未跑真实其他用户矩阵。838旧文件/54cache集合SHA/原备份干净f3b0da1与8080 PID96842/5175 PID4143保持，私有0700/0600；无Java/Vue/API/schema/锁/依赖/模型变动或main合并，现有后端仅授权新增20资源。
- 2026-10-30T02:12:49Z sync双方fetched，A95ce190/source48eeeca，B610c03e/source0e8de159；N1原035-R2卡/dispatch保持assigned。040仍in_progress，下一阶段固定五配置runner/词面对照/新包/最小页面与G2；160包/新判断/test模型run均0，141开发标签/旧run与G1新描述保持。详见verification/MUS-040-phase02.md/results.json。


### MUS-040第三检查点范围与占用

- 延续同分支，从5023721d411b3ea350df267962cf0c331005145e第二检查点继续。A串行新增holdout_contract/holdout_runner/holdout_review及测试、运行参数JSON；允许web/src/utils/reviewPack.js/reviewAudio.js、ReviewWorkspace.vue及新对应测试的最小独立schema/中文说明/回执适配，旧布局/四schema/评分/队列保留。E16先冻，原phase02 helper/catalog/G1/141/双权重/旧run只读；phase03仅私有ignore.local。
- G2先实际两固定模型合成512/strict检查并冻结全部输入/源码/依赖/五配置，再生成四批各40的空包；本检查点不接用户新qrels，不按模型结果改描述/采样。runner真实test与合成检查区分，首次真实G4可后续运行，G5仍等全160合法与五run hash。B035-R2卡仍独立，不把派发当批准。

- 第三检查点实现完成、真实G2/G3/G4待执行：三个新标准库契约/包模块与ML runner、27项新合成检查；音频工具目录238项、旧source/import78项、Node84项及build通过。首次27之前24项有12个合成fixture准备错误（fake query SHA未同步runtime config、fake Path未序列化），已修正并保留日志；不把失败或子集累加。允许在G2持久化后实际运行全部五组G4，无qrels/质量指标，随后核对四包/页面。原B N1卡保持。
