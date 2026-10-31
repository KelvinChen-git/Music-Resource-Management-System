# Audio search feasibility spike

当前包含 MUS-002 合成编码探针和 MUS-022 真实小语料离线候选排序，**不是检索 API、可发布索引或已通过质量验收的音乐搜索产品**。实际结果与局限见 [model-spike.md](../../docs/model-spike.md)。discovery-v0 仍未冻结。

本轮环境：CPython 3.12.10、macOS arm64。只对该平台生成 resolved version lock；不能据此声称 Linux / CUDA / MPS 或 Python 3.14 可用。

在自己的独立 clone / slot 中创建环境（下例为 A；B 不写 A 目录）：

```bash
python3.12 -m venv .local/a/clap-venv
.local/a/clap-venv/bin/python -m pip install -r services/audio-search/requirements-spike-macos-arm64.lock.txt
.local/a/clap-venv/bin/python -m pip check
.local/a/clap-venv/bin/python -m unittest discover -s services/audio-search -p 'test_*.py' -v
```

checkpoint 只使用以下固定版本（约 2.35GB；未纳入 Git / bundle）：

```bash
mkdir -p .local/a/models
curl -fL --retry 2 -o .local/a/models/music_audioset_epoch_15_esc_90.14.pt \
  https://huggingface.co/lukewys/laion_clap/resolve/b3708341862f581175dba5c356a4ebf74a9b6651/music_audioset_epoch_15_esc_90.14.pt
```

探针在任何反序列化前流式检查固定 SHA-256。它使用 PyTorch weights_only=True / mmap 和已知 NumPy 标量类型，而非 SDK 的通用 weights_only=False。加载严格核对全部参数，只移除 Transformers 不再持久化的非学习 position_ids buffer。

```bash
HF_HOME="$PWD/.local/a/hf-cache" HF_HUB_DISABLE_XET=1 WANDB_MODE=disabled \
  .local/a/clap-venv/bin/python services/audio-search/probe.py \
  --checkpoint .local/a/models/music_audioset_epoch_15_esc_90.14.pt \
  --report .local/a/logs/clap-probe.json
```

首次构造还会下载固定 revision 的 FacebookAI/roberta-base 模型 / tokenizer（SDK 构造依赖，随后文本权重被 CLAP checkpoint 严格覆盖）。probe.py 仅在构造期间对这两个 from_pretrained 调用加入固定 revision；没有修改安装包文件。首次有网完成后，可加 HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1，并使用新的报告文件名离线复跑。已有报告拒绝覆盖。

输入是合成 44.1kHz 立体声正弦波：先平均声道、soxr_hq 重采样，按整数采样点长度裁齐 / 补齐，再右侧补零至 480000 点。传入 SDK 的长度恒为 10 秒，避免它默认 repeatpad / rand_trunc 改变短尾段。probe 不是任意长音频切片器；超过 10 秒明确拒绝。SDK 仍执行自己的 int16 往返量化。

9 项预处理测试包含 1 秒 / 10 秒的 44.1→48kHz 长度、短段补零、立体声、非整比例长度、无效值及长输入拒绝。曾发现浮点 ceil 多出一个采样点，已用整数长度计算修正，不放宽断言。

原MUS-002检查点尚缺真实解码/语料处理，现已由下述MUS-022补部分运行证据；仍需人评、效果/模型对照与契约fixtures。不建立线上服务、不提交权重/音频/生成索引，不报告质量或P95。


## 真实小语料探针（MUS-022）

`corpus.py`校验已记录输入/下载证明与字节哈希，解码实际MP3/WAV，并提供候选10s/5s窗口及精确向量排序规则；`corpus_probe.py`复用固定checkpoint，生成当前checkout `.local/` 下的新run目录，拒绝覆盖既有run，模型缓存强制离线。音频根目录显式给出，仅按数字sourceId查找，拒绝逃逸/不匹配/重复内容；不接受任意远程输入。不要把此离线读取替代Java权限核验。

首次真实运行已对20首/933片段、8英文文字与3参考片段完成512维编码/排序；23项测试通过。完整实跑命令、原始工件位置/摘要、未标注边界见 [MUS-022](../../docs/verification/MUS-022.md)。生成向量/排序仅保留ignore目录，不提交Git；探索查询fixture不是评测集，reference同源自匹配不能算质量。原输入只读共享，输出需独立；B在自己的合法输入/缓存/slot运行，不依赖A本机路径。

尚需人工相关性/区间标注、效果和模型对照及discovery-v0冻结；当前不提供online API或前端检索。原MUS-002合成探针保持原样。


## 完成人评后的探索比较（MUS-029）

`evaluate_review.py`只用Python标准库，对E1固定run和已完成判断作双SHA验证后，按原rankings两mode的top5计算P@5（>=2）及pooled nDCG@5（指数gain、同query已判并集IDCG）。所有候选需已判；None或错误的期望SHA、缺判/未知/重复/短top5拒绝。IDCG0返回null并从nDCG宏均值排除、披露计数；不把缺判当0，不支持全库Recall或定位IoU。包中的ID排序不是检索排名。

```sh
python3 -m unittest discover -s services/audio-search -p 'test_*review*.py' -v
python3 services/audio-search/evaluate_review.py \
  --run-dir .local/a/mus022/run-01 \
  --catalog web/public/demo-catalog.json \
  --report-sha256 90e7b4939cc1d77f40863403a699926881c03e41a1b634c9b4f06c23a96d9108 \
  --pack .local/a/mus028/received-judgments.json \
  --pack-sha256 774c2083f3ffae16e24472bf2a8e69271ce748f78049eac2302cacd9ab382869 \
  --output .local/a/mus029/evaluation.json
```

上述为A本机固定工件，B用自己的合成fixture/独立目录，不要求接收A原始标签。已有output拒绝覆盖，重复实跑需新文件名；结果仅本checkout的.local、0600，stdout只有聚合摘要，原输入只读。实际38检查和首次8query探索结果/失败/限制见[MUS-029](../../docs/verification/MUS-029.md)。模型建议可见、同20曲小池，非held-out；不以此调参/训练、冻结模型或报告10%提升。


## 未入池诊断包（MUS-030）

`diagnostic_pack.py build|validate`同时固定report、已完整标注E1基包SHA及显式query IDs，从校验过的完整manifest减各query旧池；输出独立新schema/指纹，人工字段初始null、无模型建议/分数，不修改原包。新包只用于补齐当前曲库判断，E4评估不会直接接收它。原路径0600独占、只.local，CLI只打印汇总；完整命令与实际5query/67对见[MUS-030](../../docs/verification/MUS-030.md)。浏览器原E1规则保留，新schema支持每query<=100；最终来源仍需CLI。

标准库相关检查：`PYTHONPATH=services/audio-search python3 -m unittest test_review_pack test_evaluate_review test_diagnostic_pack -v`，实际53通过。不加载CLAP或音频，不对诊断新对自动打分、融合、训练或作held-out结论。


## 新来源素材核查（MUS-033）

`source_review_pack.py build|validate`显式固定source manifest、decode report、私有import catalog、query fixture四份SHA，另重建selection及原20基线。只接收新来源已导入真实Java身份、完整内容/证明与解码绑定；输出5描述各4首、20首互异的新schema包，所有人工字段null、模型区间为空。它确认素材是否适合已知描述，不能作为模型排序/held-out，也不能直接交给旧Jamendo-only corpus/probe。

导入入口是根目录`scripts/import_research_music.py`，使用既有普通owner与现有HTTP接口，独立私有40曲catalog；原公开20曲与118判断保持。精确本机命令/哈希见[MUS-033](../../docs/verification/MUS-033.md)。B用独立合成fixture，不需要A私有数据或凭据。标准库检查：

```sh
python3 -m unittest discover -s scripts -p test_research_import.py -v
PYTHONPATH=services/audio-search python3 -m unittest test_review_pack test_evaluate_review test_diagnostic_pack test_source_review_pack -v
```

实际27+72通过，不加载CLAP。新包CLI重建原不可变结构，只准人工四字段改变，已有输出拒绝覆盖；浏览器导出须再次CLI验证。实际页面初始0/20，新来源整曲仅在完整JWT媒体/字节/SHA验证后按较短浏览器端点播放，不改解码记录；旧schema和真正片段边界不放宽。新40曲索引与模型比较属于后续任务。


## 两来源40曲开发检索对照（MUS-035）

`research_corpus.checked_assets`在E7固定输入上读取独立40曲音频副本；`research_probe.py`重新处理全部40曲，复用固定模型/数值DSP和原两mode排序；8原文字查询、无新音频参考。六份输入SHA与checkpoint均显式固定，源码必须已提交且工作区干净，前后重核输入/模型/源码；私有新run只在ignore.local、0700/0600独占创建，已有成功或失败目录均拒绝覆盖。

新来源使用`soundfile-read-out-65536-actual-eof-v1`。旧032 blocks()的yield长度把MP3头部估计计为实际，不能作为真实EOF；旧报告与033 catalog/已判包保留为历史记录。新manifest同时保存recorded_decode/declared_source_frames及实际source_frames，按实际读到的0帧EOF、固定65536 out缓冲、有限值/位置/30–600s上限处理；旧20 decoder/窗口/排序字节保持，原数值预处理规则相同。不要通过补零迎合历史头部，或在原dataset内修改已判包时间。

`research_evaluate.py`标准库CLI同时固定旧/新report、E7六输入、原51/67/新20判断共11 SHA。五目标描述各24已知/16未知；top5只报告r/n/u、P@5上下限，全部5个位置已判时才提供该条exact，不排除unknown query做宏均值。新旧queries各自raw哈希仍核验，但逻辑同一fixture重新序列化后的空白差异按canonical对象比较。新来源时间由历史header绑定+actual精确ceil分别校验；当前三包人工区间必须0，只做track级比较。旧E1/两旧schema和评估器保持，不能把新run直接交给旧CLI。

实际run-02为40曲/1557片段/8文字、512维；原20重新编码最大差0，最终168单测和独立矩阵/排名复算通过。真实固定命令/源码与工件SHA、初次失败及开发比较见[MUS-035](../../docs/verification/MUS-035.md)。环境继续复用原版只读venv/checkpoint/HF缓存，NUMBA_CACHE_DIR写本次私有目录，不安装或升级依赖。未实现在线API或正式质量验收。

## 新top5未知补判包（MUS-036）

`supplement_pack.py build|validate`增加独立包，使用research_evaluate原11输入SHA及`--evaluation`/`--evaluation-sha256`完整重建035结果，再选未判top5并集。候选从035 actual manifest取时间，不改033历史包；初始全null、空模型建议，新dataset隔离草稿。沿用现有试听页的最小schema适配，浏览器导出仍须同固定输入CLI校验。已有输出拒绝覆盖，通用CLI仅写本checkout已ignore的.local私有子目录，本轮仅.local/a/mus036，0700/0600。

实际仅2query/3对/3不同曲目，已有138保留；20新Python检查，最终全目录188通过；前端新9、连旧共77及build通过。原035排序/指标不改、未跑模型或收到新标签。固定完整命令/哈希/保留失败和18项真实浏览器增量见[MUS-036](../../docs/verification/MUS-036.md)，新schema不能交给原E1或source-review CLI。


## 独立测试来源准备（MUS-039，source-only）

根目录`scripts/collect_holdout_music.py`已实现固定LOC FMA/MusicBox两框的完整输入重建和source-only收集，显式提供frame、group-review、old-group-review三SHA；这些私有快照与人工关系审查仍需按协议准备，不是通用采集/消歧命令。只取固定官方整item MP3、保留原字节，MusicBox是原音频/视频的官方音轨派生版；共同实际EOF65536/DSP与creator cap4/同作品首项、固定hash队列，不接收query/模型/标签。

已有只读环境执行的新测试：

```sh
PYTHONDONTWRITEBYTECODE=1 ../Music-Resource-Management-System/.local/a/clap-venv/bin/python -m unittest discover -s scripts -p test_holdout_music.py -v
```

这是从仓库根目录执行的命令，26项通过；真实收集完整命令/三pins与输出名见[MUS-039验证](../../docs/verification/MUS-039.md)。本次收集已成功，原输出重跑拒绝覆盖。没有安装/升级依赖或加载CLAP，共享模型/cache只读，新NUMBA缓存只在本次私有目录。

20条新source-only录音/9保守群与8新query已冻结，旧40开发材料保持；尚无Java身份/HTTP权限映射、新test标注包/runner、向量或人评。现有review/research CLI与页面不自动接收新格式，不能改split复用旧包冒充test；040先冻结新契约/映射/模型安全dev预检和G2，之后才出160项包，G5前不读新qrels。本小样本/元数据关系审查及精确SHA排重不证明声学无近重复或预训练未见。


## 固定checkpoint安全加载与旧20预检（MUS-040第一检查点）

`checkpoint_model.py`支持038已注册A/B两文件，严格filename/bytes/SHA+构造前后复核，拒绝symlink/hardlink、weights_only/mmap/CPU/strict，不回退或在线下载。当前应用/旧probe的A常量不改，新增B仅本轮私有models目录；依赖/原HF cache继续只读。

`checkpoint_preflight.py`只接受原20开发catalog/显式33c9d7fd… SHA与旧五描述，完整20重新解码/编码，沿用原窗口/DSP/两mode；不接039新素材/新query/qrels，不能当test runner或G2。源码已提交干净才实跑，前后输入/源码/模型与音频证明核验，独占0700/0600输出/私有NUMBA缓存，拒绝覆盖并保留失败。真实完整命令见[MUS-040](../../docs/verification/MUS-040.md)。

96相关合成测试：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search ../Music-Resource-Management-System/.local/a/clap-venv/bin/python -m unittest test_research_corpus test_research_probe test_research_evaluate test_checkpoint_model test_checkpoint_preflight -v
```

本次B真实严格加载512维、旧20/933片段/5文字通过；原100开发判断整曲A0.16/B0.20、片段均0.20，A为旧022排名、B为新预检，非test/模型升级。原research_probe只补3行chmod/fchmod与两回归修N1，数值/模型不改。040余下新20身份导入、test资产/五配置runner/包schema/G2尚未完成，当前160新包/判断/test run仍0；035 B批准不外推本轮。


## 新20身份导入（MUS-040第二检查点）

根目录scripts/holdout_assets.py以显式binding SHA重建G1全框/审查/原20来源与old40排除、原件/proof/实际时间，另验证新私有20 catalog/真实Java身份/独立音频证明副本。scripts/import_holdout_music.py只经现有普通owner HTTP接口导入，旧40前后核验、原catalog不写，锁和原子ledger支持响应丢失恢复，错误身份/变更/路径与重复保护保留。真实命令及三份pins见[MUS-040第二检查点](../../docs/verification/MUS-040-phase02.md)。

已新增20 pending，账号自有60曲（开发40/新测试20），实际EOF/PCM/Range/full SHA过；CLI重复0创建、42核心文件不变，额外20匿名401。78合成检查通过（source26+research-import27+asset10+holdout-import15）：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -m unittest test_holdout_music test_research_import test_holdout_assets test_holdout_import -v`。介质/HTTP替身与真实本机证据区分。新20未建测试索引，160新包/标签/G2仍待实现，不将60资源当60曲模型run。


## 独立test冻结、全矩阵包与五配置runner（MUS-040第三检查点）

`holdout_contract.py`标准库验证显式G1 binding/catalog pins、20真实身份/独立副本、8冻结描述与runtime config；`holdout_runner.py freeze`要求干净已提交源码，实际A/B严格加载，仅合成音频/旧通用文本检查512，新描述仅tokenizer长度，保存G2；`run`必须显式G2 SHA，再对20×8完整新编码，保存双权重各whole/segment和title-only log-TF/smoothed-IDF词面控制五组排名。输入/源码/依赖/离线cache/权重前后核验，独占输出/失败保留，不读取qrels或计算成绩。

`holdout_review.py build`在G2后生成四批2描述×20曲、共160项，固定hash呈现/全null/无模型提示；前端新增独立schema、中文可听线索与0–3规则、四字段完成回执。完整判断由标注者本机保管，G5前只提交回执；`seal`仅在labeler侧以显式原包SHA校验本地导出，打印总完成数/合法性/两SHA，不打印评分分布。旧四schema/草稿/播放保持；G2/包/排名准备不等于正式质量验收。真实运行状态另见[第三检查点验证](../../docs/verification/MUS-040-phase03.md)。

## 独立测试G5比较（MUS-042）

`holdout_evaluate.py`只用标准库，先核用户ZIP中四JSON原字节与已发布回执承诺，再核原G2/输入/模型环境/五run工件和四包；独占私有归档及首次解析事件记录后才一次读取完整160评分。按038既定全8等权P@5及全20 IDCG的nDCG@5报告五组、逐query正例数/上限和四个预注册成对比较。原推理代码、权重和排序不变；不训练或加载CLAP，结果不是线上检索或总体质量保证。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search python3 -m unittest test_holdout_evaluate test_review_pack test_evaluate_review -v
# 实际G5命令须使用原冻结的HF_HOME与已有完整依赖运行时：
python services/audio-search/holdout_evaluate.py \
  --archive /absolute/path/to/user-submitted.zip \
  --gate docs/verification/MUS-040-G5-request.json --gate-sha256 EXPECTED_REQUEST_SHA256 \
  --freeze .local/a/mus040/phase03/freeze-01/freeze.json \
  --runs .local/a/mus040/phase03/runs-01 \
  --packages .local/a/mus040/phase03/packages-01 \
  --output .local/a/mus042/opening-01
```

上述路径为本机示意，输出父目录需事先存在并被ignore；重复输出拒绝覆盖。B使用独立合成输入，不接收A私有评分/用户ZIP。`compare`只输出聚合及query代号，不暴露逐曲标签/真实身份/标注代号；完整原件仅0700/0600私有归档。看test后的新模型选参须另设独立评测。

## 现成标签adapter与音频预检（MUS-043）

`mtg_dataset.py`显式pin MTG base/split-0/逐曲许可/名称/低码率音频SHA、原60目录及SDD metadata；只从train按固定hash、每作者1首选20做链路预检。原tag直接转述成英文文本，未出现tag仍unknown。名称使用literal TSV，异常分隔行隔离；旧source/artist/album/规范化credit组件/作品名与SDD组排除，不等于穷尽别名/翻唱/近重复或预训练隔离。

`scripts/preflight_mtg.py prepare|fetch|decode`分别建立私有冻结选择、官方单曲206/ETag或Last-Modified/官方SHA有界下载、实际EOF/48k/10s和5s窗口预检。只准精确官方单曲URL，不拉tar，不调Java或训练模型。使用现有音频运行时和正常TLS CA；全部输出独占ignore.local下0700/0600目录，不覆盖原件。参数见`python3 scripts/preflight_mtg.py --help`及各子命令，policy为docs/evaluation/MUS-043-mtg-config.json；实际结果另见MUS-043验证报告。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_mtg_dataset test_preflight_mtg -v
```

本阶段仅非商业研究数据链路，metadata及逐曲许可均保留；没训练、没模型质量成绩、没把已有160变成新模型训练集。后续规模扩展/训练loss/未知与负例/划分/预算需单独冻结，先保留现有CLAP基线。

## 轻量适配训练试运行（MUS-044）

`mtg_plan.py`调用metadata adapter的可选partition/pool接口，默认043行为保持；追加跨官方split的creator别名组件、作品名及官方低文件SHA冲突隔离，再固定1000/200/200 metadata计划，尚不下载这些音频。`tag_adapter.py`以已知正tag prototype均值为目标、未知tag不作负例，固定lambda=100对512维音频特征拟合带identity先验的ridge残差层；无超参搜索。

`scripts/train_tag_adapter.py`显式pin043选择/音频/PCM、044配置与数据计划、原G2模型环境和干净源码后，先保存训练freeze，再加载冻结A编码器。每首固定起/中/尾3个10秒片段，183个短tag模板；全部20首只训练smoke，没有验证或测试质量结论。NPZ只私有输出，原CLAP权重/现有排名/UI不变。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_tag_adapter test_mtg_dataset test_preflight_mtg -v
python3 scripts/train_tag_adapter.py --help
```

实际运行需已有音频venv和原冻结的绝对HF_HOME；首阶段真实训练记录与限制由MUS-044报告提供，不能把训练loss/已记录tag recall当自然语言检索P@5或泛化提升。

## 小批caption开发门控（MUS-045）

接收B的044计划建议后，先固定100 train/20 tag-validation及SDD validated caption-dev20，另caption-test20仅metadata封存。prepare_caption_gate冻结元数据/技术替补；acquire_caption_gate用flock、append-only预算和逐attempt不可覆盖记录支持恢复，先完整EOF和旧60/new split精确文件与PCM校验。未知tag不作负例；SDD视图为对应录音开头最多120秒的官方低码率派生，非原SDD字节等价benchmark。

evaluate_caption_gate的encode只编码一次并绑定checkpoint/环境/DSP/窗口/来源/文本/源码hash；compare复用特征，对mean-per-track loss的alpha0.1/1/5（sum lambda=Nalpha）加identity对照，按预注册已知caption配对R@5开发门槛/配对录音bootstrap和R@1保留条件选择。文本空间不映射W；whole映射在3窗口归一化均值之后，segment单窗映射作为次要结果，不自动继承whole收益。缺配对不等于语义负例，tag诊断另报seen/rare/unseen及类别支持。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_caption_gate test_tag_adapter test_mtg_dataset test_preflight_mtg -v
python3 scripts/acquire_caption_gate.py --help
python3 scripts/evaluate_caption_gate.py encode --help
python3 scripts/evaluate_caption_gate.py compare --help
```

043/044原配置和工件保持；本门控无收益则保留identity，不直接拉1000、打开保留test或部署新模型。实际记录见MUS-045报告。


## 扩大开发候选池诊断（MUS-046）

新diagnose_expanded_caption读取046固定config、045原特征/三W/原140音频，120干扰曲补首120秒相同视图、原20开发及24文字特征复用，不下载/拟合或读保留test。两池（20/140）两模式四原模型全报MRR/R1/R5与配对录音bootstrap，已知配对仅诊断、未配对语义unknown。本次没有模型选择/扩训门槛，保留identity；不能追认045门控通过。当前参数和shape约束仅本140首版本，非生产通用trainer。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_expanded_caption test_caption_gate test_tag_adapter test_mtg_dataset test_preflight_mtg
python3 scripts/diagnose_expanded_caption.py --help
```

真实运行需原音频Python环境、原绝对HF_HOME和config显式SHA；只支持独占ignore.local输出，先完整核旧输入/原G2/checkpoint/环境/源码再模型加载。公开聚合/证据与限制由MUS-046验证报告提供；没有应用/API变化。


## 设备校准（MUS-047）

calibrate_encoder_device是独立小样本校准入口，不改旧CPU工具或默认模型。prepare仅从现有train按ID前3选9窗、前6已有tag模板，核原数据/PCM/冻结权重/环境后建立CPU参考包；run显式cpu/mps/cuda:0，FP32、禁止自动设备或MPS CPU fallback，设备环境/源码参与独立cache key。各设备同batch、1次warmup后3次同步计时，并按预注册1e-4向量/余弦/得分容差和稳定分差排序检查。不可用设备返回blocked/exit2，不算passed；MPS不代表CUDA。原始音频与预处理波形/参考向量只在ignore.local，不上传云端或复制生产缓存。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_device_calibration test_expanded_caption test_caption_gate test_tag_adapter test_mtg_dataset test_preflight_mtg
python3 scripts/calibrate_encoder_device.py inventory
python3 scripts/calibrate_encoder_device.py prepare --help
python3 scripts/calibrate_encoder_device.py run --help
```

实际编码使用原音频Python环境与原绝对HF_HOME。prepare要求047配置显式SHA；run要求校准package显式SHA、本机显式checkpoint路径和独占输出。跨主机只验证同数据/模型/配方/源码、环境单独记录；此处没有远端启动/传输/资源购买或从零训练能力，校准通过也不自动切换旧模型或索引。


## 有界设备特征缓存（MUS-048）

build_device_feature_cache只重建140已有录音，不下载/训练/替换生产cache。固定MPS/FP32/audio3/text6，须同设备047校准成功且环境/原模型/源码匹配。按整曲train100/val20和首120秒检索140两个视图编码，同录音精确sample起点去重；24原dev描述/183tag模板保持。完整对原CPU向量/四旧模型两池两模式得分、稳定次序与录音宏指标通过后才创建ready manifest。

新device_feature_cache.ready_view必须传缓存显式SHA、expected_device/expected_model_sha256和tag_training/tag_validation/caption_retrieval，拒绝设备/模型/视图错配、partial/失败report/NPZ篡改。训练/验证返回相应100/20行与原弱正tag，不返回dev文本；检索视图140行/24dev文本，未配对语义仍unknown。旧045/046 consumer接口不改，所有新cache只ignore.local，不自动换线上索引。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_device_feature_cache test_device_calibration test_expanded_caption test_caption_gate test_tag_adapter test_mtg_dataset test_preflight_mtg
python3 scripts/build_device_feature_cache.py --help
```

实际构建使用现有音频Python环境/绝对HF_HOME、048配置显式SHA与独占ignore.local输出。只记录本次完整解码/SDK编码/总时长；没有匹配全量CPU测速，不能把047小批次2.73倍外推到整个语料或训练。
