# MUS-064：六曲全文本特征与固定检索对照

准备阶段；实际编码与评分尚未执行。A；2026-11-02 America/Chicago；branch `codex/MUS-064-supplement-retrieval`，base `29873e11f5316cd25fdb978c77052c91ccf76d2c`。

按[062补充计划](MUS-062-human-source-audit.md)、[063音频预检](MUS-063-six-source-preflight.md)与[E38](../CONTRACTS.md#e38mus-064-六曲全文本特征与固定检索对照2026-11-02)，新6首/6组件/7人写描述全文本编码，旧140/624窗/24描述逐元素复用，合并146候选。全新向量CPU/MPS核查、256完整token证明后才可用；另CPU进程评identity/058已存100ridge，零fit。

[固定配置](MUS-064-retrieval-config.json)规定新6整曲录音宏MRR为主，两mode/R1/R5及旧20控制全报，原140控制复现058；bootstrap2000/seed20261102064仅描述性，不合并新旧查询集、不自动部署。先提交源码/方法/config，再冻结输入/环境与各阶段持久claim，不因失败换目录重跑。无新下载/人工包/封存test/CLAP微调，保留全文本与identity。

私有数据位于忽略目录.local/a/mus064，公开只聚合/hash。旧045–063共1087文件已快照，结束核全部集合/内容与原版/历史951/模型cache/B047原卡。数值一致性不是语义验收，六组不是独立20曲或正式测试；已知配对以外候选语义未标注，SDD描述与官方low版本的确切一致性和CLAP预训练重叠没有证明。
