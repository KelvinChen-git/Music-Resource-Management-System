# Account B — MUS-068 web/cloud development started

- task_id / revision / status：MUS-068 / 1 / in_progress；active_owner b，slot B；完整开发/台账职责继续，不归还A。
- source_branch：codex/MUS-068-real-discovery-index；base_sha：85537787606a138f0747cc8f776637c43745e0b7；准确本次source_sha由feed给出。
- ack_peer_feed_sha：45b366229170f3af00456ba96fbada5946e5f61e；双方固定入口已取并sync。前次B feed a2ec41d/source8553778，本轮不重复旧认领或把A assigned快照覆盖台账。
- 用户选择网页云端开发；新独立Linux clone/slot B，未连接Mac，A/B旧私有数据未随Git恢复。GitHub返回push=true且已从准确base创建新任务分支；无main修改或merge。

范围：先冻结E42和[计划](../../verification/MUS-068-plan.md)，再交真实音频->在线索引导出、构建证明/故障测试及独立CLAP运行尝试。允许新discovery_build/build/test/runtime脚本、必要窄改discovery_index/server和文档；Java/Vue/DB/锁/旧研究模块/A派发不改。占用在唯一STATUS。

资产准备有界：固定A checkpoint+固定RoBERTa cache、既有requirements顶层版本和CPU wheel、最多两首既有development的官方CC BY4音乐，总下载<=6GiB、仅B私有目录。真实CLAP当前仍未运行，缺资产状态保留；不会把mock或067旧345/89/14/43/13当本新环境实测。无训练/保留test/扩库/参考上传/质量或P95结论。

本检查点仅计划/契约/台账/own latest；产品未改，应用/模型/新测试执行0，文档检查单列。先发布该冻结检查点，再实施；发布source/feed并分别回读，CLI优先，API fallback时注明非原子。完成或blocked都报告实际SHA/命令/结果/未跑范围，B保留后续职责。
