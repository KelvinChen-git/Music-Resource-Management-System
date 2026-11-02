# MUS-065：Clotho人写研究训练候选容量

**本轮固定规则下只剩1段、5条人工描述，不采用Clotho承担音乐扩训主库，不下载音频或追加训练。** 元数据审计完成，audio_ready/training_ready/independent_benchmark_ready均false；不把所有环境声描述当音乐训练。

A；2026-11-02 America/Chicago；branch `codex/MUS-065-human-source-capacity`，base `77aabf4d3d77b99e4876b77a7f07c11b5222874f`，完成源码 `b6f69c973a4511726ac07865f5de85eee5b7427c`。前三次失败与显式修复链全部保留；最终交付SHA见A feed handoff.source_sha。A同操作方独立复算不冒充B审核，B047批准不外推。

## 统计范围与实际容量

按[E39](../CONTRACTS.md#e39mus-065-clotho人写训练候选容量2026-11-02)与[原固定配置](MUS-065-source-config.json)，只统计[Clotho v2.1固定发布](https://zenodo.org/records/4783391)的三个metadata CSV和development人工caption文件。取得6份文档/metadata（含CLAP README）2,636,946 bytes，正常TLS、Zenodo5文件官方MD5及本地SHA匹配，预记12MiB小于16MiB，无重试或音频。原发布网页汇总与实际三CSV范围不同，本轮仅报告实际有对应metadata的3,839/1,045/1,045，共5,929段；不把网页全条目数当已审计数量。

固定21个whole-tag关键词为music/musical及乐器词，规范case/分隔符，不作substring、caption语义或模型筛选。它是保守metadata投影，**19不是全库所有真实音乐的穷尽数量**，乐器tag也不保证完整音乐/对应caption主语义。

| 规则阶段 | development（训练来源） | validation（仅metadata） | evaluation（仅metadata） |
|---|---:|---:|---:|
| 原metadata片段 | 3,839 | 1,045 | 1,045 |
| 固定音乐/乐器tag命中 | 19 | 8 | 8 |
| 其中显式music/musical | 3 | 1 | 2 |
| 命中且音频BY/BY-SA | 6 | 2 | 1 |
| 来源绑定通过 | 6 | 2 | 1 |
| 跨split来源/上传者组件排除 | 5 | 1 | 1 |
| 剩余隔离片段 | **1** | 1 | 0 |
| 剩余来源/组件 | **1 / 1** | 1 / 1 | 0 / 0 |

全部训练metadata与3,839行caption文件名逐项匹配，每文件5个非空原caption，共19,195个配对；本轮候选只有1段/5个配对。没有语义审阅、截断、重写、tokenization、模型输入或质量评分，val/eval caption正文没有获取。各split全部许可家族、来源缺失和offset缺失数见[聚合JSON](../verification/MUS-065-results.json)。

## 来源、文字许可与评测边界

音频许可按逐文件原URI另核。训练19个tag命中中BY6、BY-NC6、CC0 6、unknown1；只按预定BY/BY-SA进入候选，**CC0另报并非认为它的许可更严格或不可用**，本轮不按结果更换许可门槛。caption有独立[原Tampere许可](https://zenodo.org/records/4783391/files/LICENSE?download=1)，限制实验/非商业用途、须保留原notice，商业服务与结果分发不能据此获得授权。音频CC不能替代文字许可。

全部metadata按同sound ID、同casefold uploader建闭包；不只拿选中片段作排除。2,181个组件，其中638个跨split、涉及3,998段，跨split双边排除、不搬移官方split。19条原记录缺sound ID/URL，仍保留上传者边但不作候选，不把Not found当共同来源ID。另2条metadata uploader与URL uploader重音拼写不同，不自动认同身份，两个键仅作保守排除边、原行不能进候选，已知sound边保留。上传者关系不是穷尽音乐作者/作品/翻唱/声学近重复或跨Jamendo/FMA身份的证明。

[CLAP官方README固定commit](https://github.com/LAION-AI/CLAP/blob/1fd4c37df5ffbfcfbad5415c170bc66cf94c9994/README.md#pretrained-models)明确说明公开checkpoint按AudioCaps/Clotho四个检索分数的平均值选取，且列出当前A。故Clotho不能直接称当前预训练模型从未用于选择的全新独立测试；这不等于已证明具体文件进入训练，精确训练成员仍未知。

[Clotho原论文§2.1](https://arxiv.org/html/1910.09387#S2.SS1)还说明初始收集排除表明音乐/语音等内容的tags。这与本轮音乐tag投影容量少一致，但初版采集说明不是对每个v2.1片段的内容判定。短环境声音库、现有许可和评测选择历史均不适合直接充当Sonora完整曲目主训练库。

## 执行、失败与验证

原源码/config先提交后audit，输入/tag/rights/split没有按结果变动。过程如实保留：

1. `def5a6c` / run-01：19条官方Not found/NA被严格ID检查拒绝。
2. `f66fbf8` / repair-01：显式[缺失来源修复](MUS-065-format-repair-config.json)，随后被2条上传者拼写冲突拒绝。
3. `0b88fe6` / repair-v2-01：显式[保守身份边修复](MUS-065-format-repair-v2-config.json)，统计后出处检查因程序错误要求两句在单行而失败，结果未发布。
4. `b6f69c9` / repair-v3-01：只修相邻README两行解析，[配置](MUS-065-provenance-repair-config.json)绑定全部原config/claim/failure SHA，实际exit0。没有源文件编辑、文字/标签/许可门槛变动或模型成绩驱动的重选。

57相关检查passed（25新/32既有），覆盖固定tag、全split闭包/传递桥、缺失ID、两种uploader边、原许可保留、caption绑定与零操作、所有claim拒绝和README相邻两行证据。最早合成48项的12 errors来自编码名utf8-sig拼写错误，真实运行前修为utf-8-sig，失败日志保留；不把本轮称首次全过。未重复Java/Vue build，范围仅离线metadata Python。

独立标准库程序不导入生产audit/parser，以CSV列序、独立图遍历、许可分类和计数重建5,929条/2,181组件、638跨组/3,998片段、所有split筛选/许可分布/缺失、3,839 caption绑定和唯一候选，全部匹配。官方MD5/TLS/6文件字节与checkpoint两行证据hash复现。四种实际claim各在原目录和新目录共8次拒绝，全部在新输出/audit前停止，4原claim、失败、成功结果SHA保持，额外audit0。

旧045–064全部1,115文件集合/hash、历史951+B047快照/23源码/54offline cache/043044/160判断、相邻原版f3b0da1干净保持，新私有目录700/文件600。无新音频、编码、fit、保留测试输入、人工包、UI/Java/DB/API/依赖锁/main变化。

## 决策

停止Clotho音乐扩训路线，保留其容量/来源审计与候选原件。现有基线identity和原全文本策略保持；本轮没有训练或模型提升结论。下一阶段应把来源范围收紧到专门音乐的人写配对数据，优先核MusicCaps的可用音频/逐来源权利与独立划分，不能直接下载来源不明的镜像、把caption许可当音频授权，或把“公开人写数量”当本机已准备曲库。不继续靠已有26首开发结果搜参，也不增加用户全组合标注。
