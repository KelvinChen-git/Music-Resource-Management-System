# MUS-054 首轮生成caption适配训练

2026-11-01 America/Chicago；A；base19afdcb；branch codex/MUS-054-caption-adapter-training。本轮实际训练轻量适配层，CLAP冻结，不是重新训练整个CLAP。配方见[固定配置](MUS-054-training-config.json)与CONTRACTS E28。

从053 typed train取209对512维音频/生成文字、37录音/33作者组件，q_i=1/37/该录音区间数。原caption的CLAP前77token向量全部使用，110条长训练caption不事后剔除或重写；14长val描述也按原规则。模型W为512×512，固定alpha1.0，min sum(q_i||X_i W-T_i||²)+alpha||W-I||F²；weighted dual闭式一次求解/无学习率或epoch选择，解析残差和objective下降检查。检索时音频unit(XW)，文本不变；训练是未归一化MSE，下降不能自动当余弦排序改善。

输入/源码/runtime/配方提交并freeze，持久fit-started.json单fit声明保留，失败不清零/换目录重试。先持久W/fit收据，再获取val视图/旧人写dev作分析；train reader的完整性校验会物理加载共享NPZ的val数组，只有返回的209train用于loss，不能说此前未读取任何val字节。7录音23段val不作alpha选择，旧dev已看过、不是新独立test；141+160和保留test不输入fit。

比较identity和新caption-ridge-1.0，主开发指标继续140候选/24人写query/20录音整曲宏MRR，固定报告20/140池整曲及三窗口R1/R5/MRR；另报7val录音23query、23精确区间候选的已知配对排名与7录音max区间排名。所有已知配对外的语义均未知，不当真负例；按录音先均值再宏平均，固定2000次按录音配对bootstrap/seed20261101054仅描述性。无自动选模/扩训/部署或保留test打开，即使单点上升也不改主模型。

133相关检查passed（9新/124旧），包括weighted dual/primal一致、重复某一录音全部段不改变权重和解、零残差identity、非法权重/向量、录音macro/固定tie以及禁止搜参/新编码。实际结果见[验证](../verification/MUS-054.md)。旧045–053、原版/UI/Java/DB/main/原B047卡保持，私有.local/a/mus054目录700/文件600，不下载/重编码/新增人工包或租GPU。
