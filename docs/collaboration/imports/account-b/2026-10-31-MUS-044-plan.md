# MUS-044训练计划审查与状态同步（B，用户直派）

2026-10-31，America/Chicago。review_id `MUS-044-PLAN-B` / owner B / review_revision 1。结论：**现有20首smoke作为链路预检合理；扩大训练前需要修订验证、正则化与推理契约，建议 `needs_revision_before_scale_up`。** 保留冻结CLAP与轻量适配方向；现有证据尚不能决定启用适配器。

本报告是用户直接要求的计划审核，不是A正式派发044工具验收。A固定dispatch仍为`MUS-035-R2-B/revision1`、assigned/unclaimed，原卡不修改、不冒充领取或关闭。本次只写本报告与B latest；不改训练配置、A台账或产品，不执行真实音频/模型训练和批量下载。

## 固定入口、范围与交接

| 项目 | 精确值 |
|---|---|
| 用户任务 | 同步项目状态并审查拟定的训练计划是否需要优化（044） |
| reviewed_sha / 开发基础 | `46b52db8b2999ab015084f423545e4f2cd5c4e03` |
| A source_branch | `codex/MUS-044-tag-adapter-training-smoke` |
| ack_peer_feed_sha | `3a1b158299ee3a9665488e97b85997ec6e4ddc3c` |
| 044 implementation_base | `83ebeea8e32d41c9652d4c8dbdf75f24e8024fab` |
| A报告的真实训练源码 | `5bce9190386053d76d056e68fd0e7cd1d936f338` |
| B source_branch | `review/MUS-044-B-training-plan` |
| B claim source / feed | `79b4c8a71370d5e9a356959cca874a332a4a5a5e` / `f514779c865cae876024c6d018364f671a923071` |
| 交付 SHA | 本轮B feed `handoff.json.source_sha`，不在本提交自引用 |
| 唯一修改文件 | `docs/reviews/MUS-044-PLAN-B.md`、`docs/collaboration/account-b/latest.md` |

开始与检查点`python3 scripts/collab.py sync --account b`均exit0/fetched，A入口未变。按source读取五文档/E19、044配置及报告/results，读真实adapter、planner、runner和相关测试；先发布claim并回读，再验证。独立B clone，未访问A本机音频、标签、特征、W、模型/cache或1400条原始私有计划；A运行数字按公开交付记录引用，未冒充B复算。

## 同步后的当前状态

| 项目 | 已有证据与事实边界 |
|---|---|
| 主应用 | A文档记录普通账号60资源（原开发40+040新增20），Java/MySQL/Vue保留；MTG研究音频未导入Java。面向浏览器的多模态搜索/API仍未完成，当前模型结果为离线工件。B本轮未检查在跑服务。 |
| 040/042小样本 | 四批160判断已完成、G5已解封并比较五配置，无需再等用户提交。A整曲/片段P@5=0.125/0.175，另一检查点B=0.075/0.125，标题=0.075；8描述中5条无正例、理想P@5上限0.225。这些是冻结小样本的历史结果，不是044新模型成绩。 |
| 043预检 | A记录20首MTG研究音频已取回并验证字节/实际EOF，20作者、49标签。仍是研究素材，不是页面新增20曲或千首语料。 |
| 044真实拟合 | 20首全用于training smoke，60固定窗口、183 tag prototype，冻结A CLAP，拟合512×512 identity-prior ridge层；真实validation/test各0。目标27.808→26.469，训练已知tag Recall@5仍0.281309524。 |
| 044规模计划 | 1000 train / 200 validation / 200 reserved-test，仅metadata；作者组件450/106/105，标签覆盖172/133/128。新增1400音频未下载/验证/训练，未得验证或保留test指标。 |
| B与集成 | 035-R1已接收；A已修复N1，准确035-R2增量卡仍待B认领。本次计划审查不覆盖其OS权限回归，也不构成044全工具、真实训练或部署批准；main未合并。 |

042的低绝对P@5同时受到素材覆盖上限限制，不能只用“继续训练”解释或解决。已有160若用于新适配器决策，只能作为development回归，不能再给新模型使用其原盲测称谓；全矩阵人工标注本轮不追加。

## 值得保留的设计

1. 冻结CLAP和文本编码器、先缓存特征再拟合轻量层，适合当前CPU和小数据试验；实际训练对象与CLAP编码区分清楚。
2. 旧60/SDD排除，官方split之外再检查作者credit连通组、作品名和官方字节SHA；每组最多4首/作品1首，固定hash取样，不按训练分数挑数据。保留实际下载后的内容与可用近重复核查，不把metadata隔离当全部声学隔离证明。
3. 未记录tag保留unknown；当前没有把它们做BCE伪负例，训练指标名称也没有冒充自然语言P@5。继续沿用043已有研究用途和逐曲许可边界。
4. 固定一次20首smoke、单lambda、保留旧权重/旧结果、不按训练loss自动切模型。这次smoke无需重做，也无需把历史配置改写成新方案。

“262,144参数/20样本”本身不足以断言过拟合：本算法有identity先验，且`rank(W−I)≤min(N,512)`；本20样本更新的秩最多20，正交于训练X行空间的方向保持identity。问题在于产品目标未被验证，以及扩大N后正则含义变化，不是参数矩阵存储个数单独决定结论。

## 扩训前需要补的四项

### R1：验证目标要覆盖自然语言检索（最高优先级的计划门槛）

位置：[044配置](../evaluation/MUS-044-training-config.json)的`training_diagnostics_only`；[tag_adapter.py](../../services/audio-search/tag_adapter.py)第13–18、39–47行；[044下一步](../verification/MUS-044.md)第56–60行。

当前优化的是“音频向量→已知tag prototype均值”，只输出训练MSE和已知tag Recall@5，runner没有持出验证/模型选择入口。MTG标签是曲风/乐器/情绪主题等上传者标签，不是完整自然语言相关度或时间区间标注。即使在200首MTG validation上tag Recall变好，仍不足以证明“用户一句描述找到合适音乐”。

建议下一阶段先冻结一个小型自然语言**开发**验证协议，采用已排除训练的现成人写caption来源（如SDD），在打开caption或跑新适配器前按作者/录音/多caption组划分caption-dev与最终caption-test；若坚持SDD全留最终评测，就另冻caption-dev来源，不临时挪用test选参数。优先使用既有标注，不再请求大规模人工笛卡尔积。

主指标可预注册为**已知caption–录音配对**的text→audio R@5，辅以R@1/MRR，固定候选池及同曲多caption/multi-positive规则；这是配对匹配口径，未配对不等于真实语义负例，不能据此产出全相关度P@5。tag诊断保留，按genre/instrument/mood与训练seen/rare/unseen支持量分桶；日志应公布训练缺少的11个词表标签及各桶支持，而不是假定validation也恰有11个未见标签。

同样views、同一候选池下对照原A `W=I` 与适配器；在开发集选参，预先写好差值、回退与保留基线的规则，按作者/录音分组报告配对差异和不确定性。小开发集无稳定收益时保留原模型；不依训练loss选模型，也不把smoke训练Recall未升直接归因于lambda或样本数量。

SDD作者明确将其人写音频caption用于音乐语言评测；它适合上述候选角色，但本文的dev/test划分和门槛是B建议，不是该论文指定的项目方案。官方来源见末尾。

### R2：lambda需要有稳定的样本尺度定义

位置：[tag_adapter.py](../../services/audio-search/tag_adapter.py)第21–36行；044配置第31–32行。

现目标为`Σ_i ||x_i W−y_i||² + λ||W−I||²`。044的固定`N=20, λ=100`作为一次smoke没有问题；若后续把`N`改成1000而沿用100，则等价平均损失正则`α=λ/N`由5降至0.1，强度减弱50倍。因而“同一个lambda”并不代表规模改变后同等identity约束。

建议新版本明示平均损失`(1/N)Σ_i ||…||² + α||W−I||²`，或者保留sum形式并记录`λ=Nα`；N以曲目为单位，不把同曲三个窗口当三份独立样本。这里是每曲平方范数均值；若使用`np.mean((XW-Y)**2)`还会除以512，正则也须相应缩放，不能只替换sum函数名。只在开发集对预注册小菜单做选择，例如`α∈{0.1,1,5}`加`W=I`，最多3个拟合候选；这些数是预算可控的建议起点，不是已验证最优。不能直接宣称lambda5000适合真实1000首——它只对应原20 smoke的每曲正则强度。

B合成复现：将相同20行重复50次，固定λ100所得W与原20行λ2相同；同步把λ改成5000才保持原20行λ100解。两项参数最大差分别5.44e-15和2.22e-16。这是数学尺度验证，不是训练数据扩增或真实模型改善证据。

### R3：明确通用训练runner与推理、聚合和片段的边界

位置：[train_tag_adapter.py](../../scripts/train_tag_adapter.py)第27–36、65–85行；044配置的`aggregation`/`target`。

当前runner明确要求20首、lambda100、183 prototype且没有validation/test流程；它是smoke工具，不能只把planned_counts改成1000就充当千首trainer。下一阶段应另立通用runner/模型选择/保存与回读验收契约，保留044历史配置和工件不变。

同时冻结评分定义：若沿用当前训练目标，文本query/tag prototype保持原文本空间，音频使用`normalize(zW)`；不能未验证地同时对文本也乘W。整曲要明确W放在原窗口归一化聚合之后还是之前。`normalize(mean(normalize(z_i))W)`与`normalize(mean(normalize(z_iW)))`一般不同；B二维构造的向量距离0.32036仅用于证明不等价，**不是生产退化实测**。

训练仅用固定起/中/尾三窗口的整曲均值；实际片段检索是单窗口，既有整曲检索还可能聚合全窗口。建议第一轮将整曲作为主任务，三窗口原A与适配器严格同views对照，另做有界三窗口/全窗口敏感性检查；片段模式单列结果和回退，不自动继承整曲收益。整曲tag没有提供片段真值，当前数据不能验证起止时间/否定条件或时序变化。参考音频query也须另明确是否应用同一音频映射。

特征缓存按音频/PCM SHA、checkpoint、decoder/DSP、窗口位置/聚合、tag词表/模板及encoder源码版本绑定；适配器、索引、query端各记W hash和应用顺序。冻结CLAP后，有限alpha比较直接复用同一特征，无需每个候选重新编码。

### R4：先让来源计划成为可运行且不泄漏的数据门槛

位置：[mtg_plan.py](../../services/audio-search/mtg_plan.py)第19–65行；[044数据计划与下一步](../verification/MUS-044.md)。

1000/200/200和450/106/105作者组件可以保留为目标；现阶段未下载的1400份不能用于承诺可训练数量、网络成本或完成时间。扩训前还需固定批量逐曲获取总body/请求/磁盘/编码时间预算、重试及独占恢复、实际EOF/字节/PCM/可用近重复复核、坏文件的预注册替补队列与相同分组约束。替补只能因技术/来源规则，不能因标签分数、模型表现或难例删除。

原043的20首永远留作training pilot，不挪入持出验证/测试。按已冻结训练和验证列表取固定前缀做第一批预算门槛，再逐步扩展；保留200 reserved-test和最终caption-test用于最后一次固定方案验收，不能在扩训中反复查看test表现。完整别名、翻唱/版本、声学近重复和预训练未见仍不能据此宣称已排除。

另需把042的素材覆盖与模型排序分开：5/8描述无正例不是仅靠排序学习就能补出的素材。后续无匹配展示/阈值若立项，须基于开发集中确认的相关度与无匹配例校准；MTG缺失tag不能提供这种负例。当前已看160可作透明的development诊断，不能作为新适配器独立成功门槛。

## 低成本实现优化与建议的下一轮顺序

Ridge本身适合作为保留基线，暂不因本20首结果扩大到全backbone训练。正tag均值并不保留所有多标签信息：B用三个单位prototype构造，互异正集合`{0,1}`和`{2}`的归一化均值完全相同。这说明该目标不能保证标签/文本排序，不证明真实MTG已发生塌缩。先用R1验证；若确证该瓶颈，再另立有明确caption/正例关系及unknown mask的检索目标，不用随意的batch内伪负例替代目前保守设计。

代码目前总解N×N dual系统。20首用dual很合适；扩到N=1000、d=512后可选等价的512×512 primal系统`(XᵀX+λI)W=XᵀY+λI`，按`min(N,d)`选择求解维度，仍用solve，不显式求逆。B在20×512合成问题中primal/dual差5.55e-16；不据理论复杂度宣称实测加速比例。闭式解没有epoch/学习率/early-stopping选择问题，主要待选择项是监督、视图/聚合和正则。

建议A下一实施任务按下面的门槛推进（任务编号、owner和路径仍由A台账确定，本报告不创建竞争任务）：

1. **先冻结新协议**：caption-dev/final-test、已知配对指标、原A identity对照、alpha小菜单、聚合/片段策略与数据/网络/算力预算；不回写044 smoke配置。
2. **先运行小批门槛**：从固定1000/200清单取约100–200 train、50–100 validation的固定前缀（数量是建议预算，不是已取得数据），完成实际内容/分组验证、测出真实下载与编码成本，缓存冻结特征。caption开发来源也先按组冻结。
3. **比较有限候选**：最多三alpha加identity，主看独立caption-dev检索、辅看tag各桶与已知旧场景回归；无稳定收益或有明显退化则保留identity并分析覆盖/监督，不按训练loss自动切换。
4. **门槛通过再扩至1000/200**，沿相同规则验证与选定一个方案；最后一次打开保留test和caption-test，报告正/负/无提升结果。仍不自动部署Java/Vue或更改索引。

## B 实际验证及限制

执行环境Python3.12.14、NumPy2.3.5。以下均在独立B目录，原生标准库/NumPy，无依赖shim、无包安装。32项为已有相关合成测试由B独立执行，不是A私有训练重跑；9项为另写数值/事实核验，不与32重复累计为真实音频测试。

| 命令 | 结果 |
|---|---|
| `PYTHONPATH=services/audio-search python3 -m unittest test_tag_adapter test_mtg_dataset test_preflight_mtg -v` | exit0，32 passed；metadata、transport替身和adapter数学检查，无真实下载/codec或CLAP。 |
| `OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 python3 .local/b/runtime/review_plan44.py` | exit0，9独立检查；实际512维primal/dual、rank/正交保持、重复样本正则缩放、centroid反例、聚合不交换及公开smoke事实。 |
| 精确源码/配置核对 | 涉及9个核心文件逐字节等于46b52db；044 config SHA匹配公开结果，无源码修改。 |
| `git diff --check`及报告链接/围栏/允许路径检查 | 通过，交付仅B两文件。 |

B无Torch/SoundFile/CLAP包，本次计划审核不需要安装或假装运行它们。未执行A20首真实CLAP训练、重算其W/特征/Recall，未读1400私有metadata逐行重分组，未验证许可适用/服务端/浏览器/完整训练工具故障与权限；无Java/Maven/前端变更，不重跑无关套件。数学检查的合成线性拟合不是项目真实音乐训练或模型选择。

证据目录`.local/b/review-evidence/MUS-044-PLAN-B/`，`verified-evidence.json` SHA256 **`759604e71cbcefd2568b098352cb1a735b1006247b849df69ee3c3e13d330478`**；32日志`aae50802e9af49a9a885e0778912dece7e74e22d0781721fd367fd399678381c`，独立结果`1913a842bdfe7dd069b1f86a7713a108b4894b5eac25089cd4c80adda756aecb`。原始合成矩阵和脚本仅B ignore，公开报告不含A原始私人数据。

关键源码SHA：tag_adapter `a3a68218b50db81385a283a54b38bc2177634f63486cb484bfa5df475dddf025`；planner `c5599e92f32757dea7b649f0f1ffe19af7830c8e928f561560bc67df0f1afd1e`；runner `63c66e8a95ecc3570d4f9fdaf6e0f160155cccb47d1f70992fe3b62f9d7484c0`；044 config `7865eb81c66a7d30a3a651c903d7fa03ad1fc46afff59a83d2574a0cdc35c927`。

## 一手资料与交付状态

- [MTG官方固定revision README](https://github.com/MTG/mtg-jamendo-dataset/blob/cafd8e20c265ed84f1e61f1c875327971f43a62f/README.md)：确认其目标是上传者标签的auto-tagging，split的类别词表与metadata/逐曲许可分离；B经GitHub接口读取准确revision。网页固定URL抓取一次受限，未据失败页作结论。
- [Song Describer原论文v3](https://arxiv.org/abs/2311.10057v3)及[作者仓库](https://github.com/mulab-mir/song-describer-dataset)：人写caption用于音乐语言评测，支持R1的候选数据角色，不提供本项目所有语义负例或定位真值。本轮仅阅论文/README，未读取caption数据正文来训练或评价。
- [LAION官方CLAP仓库](https://github.com/LAION-AI/CLAP)：核对music checkpoint属于其发布模型；不因此保证与本项目数据无预训练重叠或本轮模型效果。

实际完成：状态同步、计划与相关源码审查、32已有测试和9独立检查、R1–R4及分阶段优化建议。接口变化：无；数据/模型/索引版本：A原件不变，B只有固定seed440031的合成矩阵，未产生项目候选模型。下一步A接收建议并串行冻结下一实施任务；035-R2保持原状。

以已授权GitHub接口顺序发布source再B feed，非原子，交付SHA及实际可读状态由handoff/精确回读给出；远端可读不等于A接受计划或训练已获效果验收。两报告交付后释放，无服务/端口、后台轮询或main推送/合并。
