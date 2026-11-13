# MUS-067-B：暂由 B 负责 Sonora 后续开发与集成

| 字段 | 值 |
|---|---|
| 用户授权 | 2026-11-13（America/Chicago），暂时把开发任务完全转交 B |
| owner / revision | `b` / `1` |
| 初始状态 | `assigned`，认领由 B 自行发布 |
| 产品实现基线 | `codex/MUS-066-musiccaps-source-audit` @ `b296f35227cf399c4f645bbd433567a02c519825` |
| 启动分支 | `codex/MUS-067-b-development`，从本卡的 `assignment_source_sha` 创建 |
| 首次认领入口 | `collab/account-a` 的 `handoff.json` / `latest.md`，以及该源码提交的任务入口和本卡 |
| 认领后的唯一状态入口 | `collab/account-b` 的 `handoff.source_sha` 指向的 `docs/STATUS.md` |

`assignment_source_sha` 取 A 发布本卡时 `handoff.json` 中的完整 SHA。它包含移交文档并直接继承上述产品基线。这不是一次复审；为兼容旧入口，任务 JSON 的 `reviewed_sha` 同时记录旧产品基线，**不能用它替代启动分支的起点**。A 发布后停止开发和台账写入。B 认领后接管开发、测试、集成协调、阶段发布和台账，可继续拆分任务及创建分支/PR，无需 A 串行批准或整合。单个检查点完成不归还职责；等用户另行明确移交。

## 第一次领取

1. 在 B 自己的独立 clone/worktree 先查 Git 状态并同步、核验 A/B 固定入口。旧环境缺脚本按 [BOOTSTRAP_B](../BOOTSTRAP_B.md) 接入。保留旧分支和未提交工作；不重置、不覆盖，不使用 A 的运行目录。
2. 核对任务 ID `MUS-067-B`、revision `1`、实际 A feed SHA、`assignment_source_sha` 与 `base_sha`。确认源码基线包含已发布的产品提交和本卡；从任务卡源码提交创建 `codex/MUS-067-b-development`。同名分支存在先核对来源，已认领的同任务/修订从 B 最新有效交付续做，不重复领取。
3. 在一次提交中把 `docs/STATUS.md` 顶部改为 B 当前负责、记录时间及占用，并写 `docs/collaboration/account-b/latest.md`：`task_id`、`assignment_revision`、`task_status: claimed`、`active_owner: b`、`base_sha`、`assignment_source_sha`、`ack_peer_feed_sha`（实际收到的 A feed SHA）、计划首个检查点与环境阻塞。优先用 `python3 scripts/collab.py publish --account b` 发布，再核对源码和报告。若 CLI 不可用，沿用 B 既往验证过的 GitHub 写入方式，先发布 B 源码分支，再发布 B 固定 feed，分别回读并注明非原子；仅源码已推或仅本地提交时，认领回执仍未送达。先修通发布，再开始产品开发。
4. 此后 B 按自己的最新已发布源码读取、更新 `docs/STATUS.md`，每个检查点同步双方 feed、写自己的报告并发布当前任务分支。A 的任务入口是此次授权凭据，保留原样；阶段任务和阻塞记在现行台账，由 B 维护。

## 接手时的进度与待办

- Java/Vue 音乐管理、鉴权媒体、上传恢复和试听审阅已有本地运行或针对性验证。A 本轮仅复核页面 HTTP：新版 `5175/music` 和 `/research/review` 返回 200，A 后端 `8080` 与原版 `5173` 拒绝连接；不据页面响应宣称业务通过，也不要求 B 连接 A 的服务。
- Python 已有离线 CLAP 文本/音频检索、时间片段排序、人工评测和轻量适配层。研究对照已用 146 首候选；100 录音、539 配对区间的适配层未证明稳定收益，继续使用冻结 CLAP 的 identity 基线，保留全文本策略和已有评测划分。相关依据见 [MUS-064](../../evaluation/MUS-064-six-source-retrieval.md)、[MUS-058](../../evaluation/MUS-058-expanded-training.md)。
- 在线搜索尚未接入；[discovery-v0](../../CONTRACTS.md#b-建议的公开-discovery-v0-契约尚未实现) 是建议契约。第一优先级是 B 自建/验证隔离运行环境，然后用现有基线打通鉴权文字查询、候选片段及可试听的最小闭环。初期不以新增训练、参考音频上传、重做界面或扩库为前置条件。
- MusicCaps 的固定 20 个公开元数据来源均可读取；逐视频许可、音乐人/作品及实际音频仍未核验，训练就绪 0。见 [MUS-066](../../evaluation/MUS-066-musiccaps-source-audit.md)。训练扩展作为独立待办，有明确来源及使用权利、音频和划分证据后再进入。B 不必重复已经接受的 [MUS-047 限定复核](../../verification/MUS-047-B-acceptance.json)。

## 开发范围和第一个可交付结果

B 可按任务修改 `music/`、`web/`、`services/audio-search/`、`scripts/`、关联测试与文档、`README.md`、`AGENTS.md`，以及自己的 latest 和唯一台账。具体文件占用由 B 在各任务开始时登记。公共 API、迁移、依赖或模型变更先更新契约并协调依赖。A 的 latest、固定派发入口及历史参考报告保留原样。保留现有界面和音乐管理链路，做增量接入；B 可以独立提交、推送其任务分支及提出 PR，用户仍保留最终合并决定；不向 `main` 推送或自动合并。

首个阶段验证：独立启动相应前端/后端/数据库；记录真实媒体权限及受控样本证据；以小量可用素材连接 Java 鉴权、Python 精确检索和 Vue 试听。契约至少覆盖有效结果、空结果、无效输入、合理片段时间、索引与模型版本不符，以及删除、拒绝或越权候选不返回且不可获取媒体。模型/可用音频缺失时可先完成契约及有明确标记的测试替身，真实模型链路保留 blocked，不能用替身或 A 的测试数字作实际通过。下一阶段由 B 拆分并串行维护状态。

本次跨账号交付为代码和仓库内证据。A `.local`、数据库、音频、模型缓存、向量、原始标注和凭据并不随 Git 转交；B 先盘点自己的环境，使用分离的端口、数据库、媒体和索引目录。私有复现资产经批准另行提供或从合适的来源重建；不将其提交进 Git，不凭 A 私有工件哈希声称 B 已复现。不用保留测试调参，也不自行开通付费服务。
