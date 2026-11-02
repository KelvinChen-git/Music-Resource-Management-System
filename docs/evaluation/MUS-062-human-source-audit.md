# MUS-062：其他人写来源与六组补充开发计划

**已冻结6首、6个未用作者组件、7条既有人写描述的补充development元数据计划。** 取自061原8候选，每组固定hash取1首；不凑20、不放宽原许可/作者作品隔离、无需新人工标注。音频、特征和模型评分均未产生，audio_ready=0。

A负责；分支 `codex/MUS-062-human-source-audit`，base `9c6d690bd9054599f4c7f1382729180e9c3731ad`，实际审计与选择源码 `69847dfac292e27190b1ba34c08044b8fade9f11`。最终交付SHA由A feed handoff.source_sha提供；工具独立B审核待安排，不外推已有B047批准。

## 外部来源实际核查

| 来源 | 本轮实际证据 | 当前结论 |
|---|---|---|
| WikiMuTe | 原all.csv 10,200行、8,832不同文件/URL；完整来源URL中Commons2,364、英语维基6,468 | 文字来自人写百科，但经模型抽取/配对；不能直接当人工听音真值。逐音频许可、音乐作者/作品身份仍未建立 |
| YouTube8M-MusicTextClips | 原train.csv实际1,000行/1,000视频/1,000个10秒区间；MusicCaps5,521视频和MusicBench5,079训练来源的ID交集均0 | 是人工听音描述；原Adobe非商业研究许可，CSV不附音频/音乐作者/作品。视频ID不重叠不等于跨音乐人/作品隔离或音频可用 |
| MuChin | 仅固定commit官方README，未取描述/音频/整库 | 中文人工描述候选；官方要求合法音频渠道，需独立语言评测协议，不能直接替代现有英文主评测 |

[WikiMuTe论文](https://arxiv.org/html/2312.09207v1)说明DistilBERT span提取及跨模态筛选；本轮只取[原始all发布](https://zenodo.org/records/10223363)，不取filtered_sf/mc，不把自动筛选样本当独立人工确认。代码MIT与文本数据CC BY-SA3.0分开，逐音频条件仍看原文件。该库不自动替换当前benchmark。

[YouTube8M原发布与LICENSE](https://zenodo.org/records/8040754)明确是Adobe Research License，本轮未沿用二手列表的CC BY-SA标签。文字描述许可不能替代YouTube源音频权利。[MuChin准确commit说明](https://github.com/CarlWangChina/MuChin/blob/be09ac633cfc4792100e7c2d2c88fdbc71bf33cf/README.md)同样不能用仓库代码许可替代歌曲权利。

WikiMuTe主工具只投影本轮支持的英语维基数字pageid：8,608行/7,533文件/7,497页面；同file/article/URL重复26行、737页面对应多文件，文件URL冲突0。另1,592行使用合法`commons:<数字>`页命名空间，**在本轮EN投影之外，并非官方坏数据/缺页ID**；上表8,832为全部原文件计数。两种统计范围必须区分，不把EN投影当全库容量，也不由Commons域名直接认定音频权利通过。

原CSV的caption/aspects/sentences/text正文经过结构解析但不被显示、语义审阅、抽取或编码。YouTube8M test.csv未下载，项目SDD封存20正文/音频和160判断未输入。媒体metadata抽检0：外部来源当前无法直接替代主人工clip评测，没有继续取音频。

## 六组小补充的固定方案

[配置](MUS-062-source-config.json)与[E36](../CONTRACTS.md#e36mus-062-外部人写来源审计与六组补充开发计划2026-11-01)在真实选择前提交。061已验证的8首/6组件按`SHA256(seed + 换行 + track_id)`每组取最低，seed=`MUS-062-unused-SDD-six-components-v1`；不看文字语义、描述数量或模型分数。结果6曲、6作品键、6官方音频SHA，与旧140曲ID无交集，共7条有效人工描述；同组剩余2曲不作失败后自动替补。

私有计划包含来源身份、原作者组件、历史逐曲许可、官方low路径及有效描述条数，不含新caption正文。原BY/BY-SA、30–600秒、旧全部关系排除与原20封存关系保持。061“未选择/不足新20”的历史结果不改，062另建小型development计划，不当正式质量验收或预训练无泄漏证明。

后续对照也已预定：identity与已存058的100曲全文本ridge，原140+新6共146同首120秒视图；主指标仅新6的recording-macro whole MRR差，次要新6 R1/R5和segment，旧20 queries在146池仅控制。没有新fit，也没有先看7描述来决定模型或比较口径。原全文本保持，未来256词元完整证明或超限失败，禁止静默截断。

下一步在独立任务先冻结有界逐曲获取/完整EOF/官方SHA、PCM/旧来源去重和逐曲元数据核验；实际通过后再编码7条描述及6首同视图片段、执行固定两模型对照。当前没有音频、MPS新编码、模型加载、质量指标或页面新包，小规模结果将仅供development诊断。

## 验证与交付

本机捕获13官方文件共5,083,052 bytes，正常TLS，Wiki/YouTube原文件官方MD5及本地SHA匹配；GitHub准确commit文档钉住。持久32MiB正文预算预记20MiB，每URL一次，无重试/重置，无整库音频。WikiMuTe代码版本 `246cba20d6a11edc2be91432bf1dfa5d4aca8b1b`；全部字节/hash/来源与运行证据见[聚合JSON](../verification/MUS-062-results.json)。

63相关检查passed（15新/48既有）。干净69847df生产审计/元数据选择首轮exit0；独立标准库脚本按CSV列序和集合算术复核全部投影/交叉计数、官方MD5/13收据/预算、8候选内逐组hash最低、6曲7描述/余2，全部相符。独立检查最初误断言1,592是缺页ID；确认Commons命名空间后只修核查假设，原失败脚本/日志保留，生产EN投影/六曲计划未变，也未重跑生产审计。

真实同目录/换目录两次重跑均在新增审计/选样或输出前拒绝；claim/plan/结果hash保持。旧045–061全部1,007文件集合/hash、历史951+B047快照、23源码/54offline cache、043/044与160原件、相邻原版f3b0da1干净保持；062目录700/文件600。A同操作方独立复算不是B审核。

只交付纯metadata工具/测试、E36/config/聚合方法和台账。没有UI/Java/DB/API/依赖锁/main变化，未重复Java/前端build。原identity、完整文本、人工判断、权重/缓存与封存test保持。
