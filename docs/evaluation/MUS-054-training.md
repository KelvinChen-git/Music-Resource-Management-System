# MUS-054 首轮生成caption适配训练

2026-11-01 America/Chicago；A；base19afdcb；branch codex/MUS-054-caption-adapter-training。本轮实际训练轻量适配层，CLAP冻结，不是重新训练整个CLAP。配方见[固定配置](MUS-054-training-config.json)与CONTRACTS E28。

从053 typed train取209对512维音频/生成文字、37录音/33作者组件，q_i=1/37/该录音区间数。原caption的CLAP前77token向量全部使用，110条长训练caption不事后剔除或重写；14长val描述也按原规则。模型W为512×512，固定alpha1.0，min sum(q_i||X_i W-T_i||²)+alpha||W-I||F²；weighted dual闭式一次求解/无学习率或epoch选择，解析残差和objective下降检查。检索时音频unit(XW)，文本不变；训练是未归一化MSE，下降不能自动当余弦排序改善。

输入/源码/runtime/配方提交并freeze，持久fit-started.json单fit声明保留，失败不清零/换目录重试。先持久W/fit收据，再获取val视图/旧人写dev作分析；train reader的完整性校验会物理加载共享NPZ的val数组，只有返回的209train用于loss，不能说此前未读取任何val字节。7录音23段val不作alpha选择，旧dev已看过、不是新独立test；141+160和保留test不输入fit。

比较identity和新caption-ridge-1.0，主开发指标继续140候选/24人写query/20录音整曲宏MRR，固定报告20/140池整曲及三窗口R1/R5/MRR；另报7val录音23query、23精确区间候选的已知配对排名与7录音max区间排名。所有已知配对外的语义均未知，不当真负例；按录音先均值再宏平均，固定2000次按录音配对bootstrap/seed20261101054仅描述性。无自动选模/扩训/部署或保留test打开，即使单点上升也不改主模型。

133相关检查passed（9新/124旧），包括weighted dual/primal一致、重复某一录音全部段不改变权重和解、零残差identity、非法权重/向量、录音macro/固定tie以及禁止搜参/新编码。实际结果见[验证](../verification/MUS-054.md)。旧045–053、原版/UI/Java/DB/main/原B047卡保持，私有.local/a/mus054目录700/文件600，不下载/重编码/新增人工包或租GPU。


## 实际结果

干净 `4afd75cd2d75ce1aaab8e08aabac21c16a7f6270` 首次实际fit/eval exit0。训练37录音/33组件/209段，CPU13.7358ms、全含缓存校验和固定比较257.740ms；只说明已预编码的小线性层，没有新音频或CLAP模型加载，不是全量训练时间/吞吐/P95。W含262,144参数，objective1.313145→1.148083、normal equation maxabs1.03e-16，独立512维primal解与训练dual解最大差1.33e-15。这个解析最优不是检索质量最优。

| 固定比较 | identity MRR | caption-ridge-1.0 MRR |
|---|---:|---:|
| 人写dev / 140池整曲（主） | 0.420808 | 0.447163 |
| 人写dev / 140池窗口 | 0.394723 | 0.451502 |
| 人写dev / 20池整曲 | 0.708333 | 0.677500 |
| 人写dev / 20池窗口 | 0.676250 | 0.683810 |
| 生成val / 23精确区间 | 0.390929 | 0.427504 |
| 生成val / 7录音max区间 | 0.579167 | 0.620238 |

主MRR差+.026355，2000次配对录音bootstrap95%[-.006304,.082660]，含零；主R1 .31→.37/R5 .49不变。140窗口次要MRR差+.056779，区间[.000354,.130647]，不能用次要指标替代未通过的主目标或当新独立test。20池整曲MRR下降-.030833；生成val精确区间差+.036575，区间[-.000331,.093498]，只有7录音且其余语义未判。完整R1/R5/MRR/query宏与所有区间均在[聚合结果](../verification/MUS-054-results.json)，不挑报有利池/模式。

历史045/046/049的alpha.1主MRR.465839仍高于本轮.447163；这是原已用dev上下文，不是本轮预注册第三对照、额外fit或可部署冠军。原模型保持identity，不追加alpha/epoch搜索、保留test或自动扩训。当前已进入并完成实际生成caption适配训练，后续改进需单独明确假设，不能把不断准备当作尚未开始训练。

133相关检查passed（9新/124旧）；同操作者独立primal/目标/残差/所有2模型×2人写池×2mode与2生成val指标/6组全部bootstrap复算一致，不导入新learner/生产metrics，不冒充B独立审核。W/fit先保存再打开分析的时序和输入source/runtime pin通过；实际原目录FileExistsError、新目录在持久fit-started.json拒绝，额外fit0，原W/收据/claim集合SHA保持。新目录保留freeze/failure原件，无删除重试。旧045–053/hash、951输入/原B047卡/23源码/54离线cache/043044/160及原版f3b0da1干净保持，私有700/600。
