# MUS-040 第三检查点：独立运行冻结、完整标注包和五配置执行

本增量延续5023721第二检查点，契约先见CONTRACTS E16、运行参数MUS-040-runtime-config.json。G1新20/8描述/原141开发判断/旧40及全部历史工件保持，不改权重/依赖/Java/API/数据库/main，不重做UI。源码提交后才实际G2；本提交时真实G2/G3/G4仍待执行，下段由运行结果补齐。

三个新模块分别负责标准库输入/源码与环境pin、G2合成预检和五组无qrels runner、四批全20×2模型不可见包及labeler侧回执。UI最小支持新schema/中文线索与评分规则/批次及保管说明；原四schema/草稿/评分/播放器保持。新LOC两来源经原完整JWT字节/SHA校验后使用较短浏览器终点，包时长不变。

检查：音频工具目录238项passed（原211+新27），source/import相关78项passed，Node84项passed（原77+新7），build passed，保留旧bundle>500kB警告。新27包括完整221合成来源/20身份重建、160全矩阵/hash呈现/空判断、只合成输入预检、token/维度/norm拒绝、五组/失败无commitment、PCM/512、手算TFIDF、G2 source/input/environment篡改、回执无分布、Python↔浏览器canonical及确切导出字节hash、旧schema/播放回归。合成fixture/模型不能冒充真实权重、codec或真人标注。

初24项有12个fixture准备错误（fake query SHA未同步runtime config、fake Path未序列化），修正后新27/完整238通过，失败日志原样保留；失败/早期子集不累计。没有新qrels、成绩、显著性、P95或线上检索验收。源码/运行/页面实测与保护结果待干净源码实跑补充。
