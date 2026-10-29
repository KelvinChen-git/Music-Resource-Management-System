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
