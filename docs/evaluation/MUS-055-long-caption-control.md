# MUS-055 完整描述长度对照

2026-11-01 America/Chicago；A；base338146a；branch codex/MUS-055-long-caption-control。方案见[固定配置](MUS-055-control-config.json)和CONTRACTS E29。本轮只比较同一批原文编码长度77与256，其余歌曲、音频、作者分组、录音权重、alpha1 ridge和固定开发指标不变。原77默认截断属于SDK策略，当前RoBERTa分支支持显式tokenizer；配置容量检查仍需真正前向运行/数值/质量复核，不能仅改数字就宣称改善。

先绑定053 cache/052原文/原CLAP A/model环境/源码，按固定hash从train短<=77与长>77各取3个、6不同creator控制，选择不看相似度或排名。每条原未截断token IDs必须与256实际非pad IDs完全相同、padding/mask合法，全部长度<=256/顺序和原文SHA保持，否则失败。CPU77控制对旧053 MPS77、CPU256控制对新MPS256、全部108短描述256对旧77，maxabs/cosine各<=1e-4；全部通过才写私有text-only overlay ready，不覆盖原cache/重新解码或编码音频。

训练在另一个CPU进程使用overlay typed train209/37，原77W只读取不重训，新256唯一alpha1加权ridge fit。encode-started/fit-started持久声明阻止换目录重复预算，失败保留不删claim。W和fit收据保存后才分析7val23/旧已看dev；完整性reader会物理读共享NPZ，只有返回train进入solver。

主指标固定原048的24条人写query特征、140候选整曲宏MRR，新256减已存05477；identity作为锚。完整报告3W×两人写池20/140×整曲/窗口；生成val再交叉3W×2查询文字长度77/256×精确区间与7录音max两指标。只有主human查询保持不变时，才可把主差异归到本次训练文字长度改变；生成val新查询自身的变化另列。2000次/seed20261101055按录音配对bootstrap为描述性开发证据，数据已经看过，非新盲测；生成标签仍弱监督、未知配对语义未判，不能当分类准确率或任意相关曲全量评分。

143合成相关检查（10新/133旧）passed；首次157为14个导入TestCase重复发现，已改模块导入/保留原日志，只计去重后的143，不存在产品或数值门槛修复。实际模型/训练/独立复算结果将在[验证](../verification/MUS-055.md)与聚合JSON记录。旧045–054/141+160/权重/cache/SDD/保留test分界/原版/UI/Java/DB/main只读，无新音频/下载/人工包/云端或自动选模部署。B047仅其设备工具合成/静态限定批准已接收，原派发快照保持，不外推本轮。
