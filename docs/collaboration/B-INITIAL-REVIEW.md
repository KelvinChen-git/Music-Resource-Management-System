# B 首轮报告的接收与整合

账号 A 于 2026-10-19 接收用户提供的 `Music_Account_B_Baseline_Review_2026-10-19.md`；原文保存于 [imports/account-b/2026-10-19-baseline-review.md](imports/account-b/2026-10-19-baseline-review.md)，仅做文件导入，不改写 B 的结论。来源记录见同目录 `provenance.json`。

B 审核基线是 `b81f57c79e1cefb96c2055df4ae438aa24fb475c`，不是 A 后来完成的 `7ab0d39`。B 的 Maven DNS 阻塞和 A 本机 89 项测试通过分别属于不同环境 / 版本，均保留。B 当时未看到任务卡不表示 A 没有本地分配；真正缺口是 A 的产出没有发布到双方都能读取的远端。

| B 发现 | 当前处理 | 后续验收 |
|---|---|---|
| #1 旧媒体匿名路径 / 长缓存 | A 已另行运行确认部分匿名绕过；未修复 | R1 扩权限矩阵；MUS-005 在公开检索前治理旧路径和缓存 |
| #2 上传无用户归属 | 接收为待处理静态发现，不据此声称已复现跨用户利用 | MUS-005 设计归属 / 必要迁移与跨用户断言；参考音频另设私有归属 |
| #3 历史 SQL；#4 配置、测试选择 | A MUS-001 已建立空库 SQL、隔离配置和全命名测试证据 | B 必须审核 7ab0d39 并独立复跑；既有库迁移未提供 |
| #5 Long/Integer ID；#7 文件大小窄化 | 接收为待处理静态发现 | MUS-002/005 明确解析、边界和实际上传上限；不顺手改旧公共 API |
| #6 MD5 只存储而未校验 | 与 A 未解决项一致 | 独立上传完整性任务；content_sha256 计算实际文件字节 |
| #8 元数据依赖 ID3v2 | 接收为待处理静态发现 | MUS-002/003 用实际解码结果生成 duration / samples / channels |
| #9 tags any / 新 all、approved | 契约仍为 proposed | 冻结 fixtures；新 discovery 显式适配，不静默改旧列表 |
| #10 导出可能仅前 20 条 | 尚未数据库复现 | 单列待验证；语料清单必须核对数量，不信任“全量导出”名称 |
| #11 JWT 取流与 HTTP 202 / body code | 尚未冻结 | MUS-002 明确 HTTP / envelope 组合，MUS-004/005 适配及测试 |
| #12 Python / 工件 ignore | A MUS-001 已补实际目录模式 | B R1 核对；不把权重、语料、索引或本机配置放进交接 |

本次不把 B 的原始报告放到独占的 `docs/reviews/MUS-001-B.md`，不替 B 发布 `collab/account-b`。MUS-001-R1 继续为“任务已准备、待 B 确认”。同步机制 MUS-008 为本轮工作，A 负责其脚本 / 约定 / STATUS，B 仅按任务卡新增自己的报告与交接。
