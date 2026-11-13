# Account B — MUS-067 development handover claimed

- task_id / assignment_revision / task_status：MUS-067-B / 1 / claimed。
- active_owner / slot：b / B；B 接管开发、验证、集成、发布与唯一 STATUS，直到用户明确再次移交；A 已暂停写入。
- source_branch：codex/MUS-067-b-development；认领提交见同次feed handoff.source_sha。
- base_sha：b296f35227cf399c4f645bbd433567a02c519825（产品实现基线）。
- assignment_source_sha：082dadc35213a696107d6f4f966735d854d860d3（实际启动点，直接继承base）。
- ack_peer_feed_sha：45b366229170f3af00456ba96fbada5946e5f61e。
- 唯一现行台账：本次及后续B feed.source_sha内docs/STATUS.md；不再以A旧快照覆盖。

独立B clone原分支/提交806dc9c保持且工作区干净；从准确移交提交建立开发分支，已读固定入口、任务卡、五份指令及建议discovery契约，确认原047限定审核已由A接收，不重复复审。先发布领取source/feed并精确回读，再开始产品开发；CLI优先，若写入不可用沿用GitHub接口顺序发布，明确非原子。

首检查点MUS-067-CP1：先盘点自身隔离端口/数据库/上传/依赖/模型，冻结并实现Java鉴权文字查询→Python精确候选片段→Vue JWT试听的最小闭环，保留当前设计/旧业务。占用与验收范围见STATUS顶部；公共接口先更契约再编码。验证至少覆盖正常/空/无效输入、时间范围、索引模型版本、删除/拒审/越权不返回且不可取媒体。真实模型/资产缺失可先交明确标记替身，真实CLAP仍blocked，不把替身或A数字当实跑效果。

初查：Java21/Node24、B本地runtime-tools/maven缓存与web/node_modules存在；系统无MySQL/Docker，实际工具/端口/库待核；NumPy/FastAPI/uvicorn有，torch/soundfile/laion_clap缺。A的数据库、音频、模型、向量、凭据和原判断不随Git交接，不读取A运行目录，不自开付费服务。在线discovery当前未接入，146候选/100录音适配研究无稳定提升，identity/全文本保持，MusicCaps训练就绪0。

本认领只改STATUS和own latest，产品/API/数据/模型/索引未改，未运行应用或真实模型，不推/合并main。B保留后续开发职责和占用；无后台轮询。
