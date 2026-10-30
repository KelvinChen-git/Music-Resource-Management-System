# MUS-040 第三检查点：G2/G3/G4完成，等待160项真人标注

准确干净源码 `1671b134ccec92819a8c041373b6330630800812`，延续5023721第二检查点；A串行实现，无子代理。契约先见CONTRACTS E16，机器配置SHA `8c91b0da29aea117d0ab174397f61adf727e70e46c4cc54b91689e8a8d45db38`。源20/8新描述/原141开发判断/旧40及全部历史工件保持。MUS-040为review（运行/包已就绪，工具待独立审核），不是正式模型质量验收；B035-R2 N1准确原卡不扩到此增量。

## 运行冻结与五组排名

G2真实exit0，24.550秒：两固定checkpoint按已知SHA/weights_only/mmap/CPU/strict加载，无missing/unexpected；固定220Hz两秒合成音频补零10秒、原通用文本各实际1×512/float32/finite/unit。新8描述仅tokenizer检查（19–36≤77），未编码新音乐/描述/读取qrels。绑定447输入、源码/参数/协议/框/组/身份/内容、5141已安装源码配置/原54个离线cache文件、两权重；收据先保存再G3/G4，SHA `1898f2bd0f286f1d1f66f074df552ead78d853002657481801deb3570efd1d83`。

G3真实exit0，5.752秒：四批各2描述×20录音=40，总160，20首不同音乐，每query固定hash打乱，全部人工字段null/无模型建议。四包同test dataset `93423365583e9fcc19c9cde09524bb100ca5c3d5038e530ba2b58ef3d301a684`，批指纹不同；正文/来源身份/owner/逐条内容仅私有，不进Git。

G4真实exit0，154.978秒（单次非P95）：A/B各重新解码20源到实际EOF，原PCM SHA匹配G1，各755片段/20整曲/8英文文本、512维；整曲为归一化窗口均值，片段最大/原代表窗口规则。另固定title-only NFKC/casefold/unigram/logTF/smoothedIDF/20标题df/余弦，对未见词零向量保留20首数值ID并列顺序。全部五组×8=40完整排名、各20位置，独立双套向量/片段文件；无qrels输入/新成绩/模型选择。all-runs commitment SHA `d3b03f47be712c9ac8f3aa40d01c1d31430b7cd8e6616809fdde48826271a6c1`，各排名SHA见results.json。保留原SDK meshgrid/初始roberta pooler警告；随后CLAP严格加载完全覆盖，没有训练或改依赖。

A另写脚本只用NumPy/math，不导入生产runner/corpus/ranking：按新catalog的实际采样长度重建755窗口、两套整曲均值（最大差各1.49e-8）、32个声学全20排名及代表片段/IoU规则、8个标题词面排名；冻结447输入/源码和全部持久化文件SHA通过。它仍是同操作者核查，非B或独立真人评测。G3/G4已有输出各再真实CLI一次，均exit1/FileExistsError、模型加载前拒绝，原5/10文件不变。

真实命令在仓库根执行；这些output已存在，不能覆盖重跑：

```sh
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 WANDB_MODE=disabled \
HF_HOME="$PWD/../Music-Resource-Management-System/.local/a/hf-cache" \
NUMBA_CACHE_DIR="$PWD/.local/a/mus040/phase03/freeze-cache" \
../Music-Resource-Management-System/.local/a/clap-venv/bin/python services/audio-search/holdout_runner.py freeze \
  --binding .local/a/mus040/phase02/binding.json --binding-sha256 56b74cd137ac0ae4442cf7c13a8e2c2bd9ceda0429cf7e7cfdc84cafaa1c5561 \
  --catalog .local/a/mus040/phase02/import/catalog.json --catalog-sha256 ea7eb53a6c3c29d9d5d052b2f786c794550cd332cf60162e45b722c1387766f8 \
  --audio-root .local/a/mus040/phase02/import/audio \
  --checkpoint-a ../Music-Resource-Management-System/.local/a/models/music_audioset_epoch_15_esc_90.14.pt \
  --checkpoint-b .local/a/mus040/models/music_speech_audioset_epoch_15_esc_89.98.pt \
  --output .local/a/mus040/phase03/freeze-01

# 同一只读环境（HF_HOME/离线环境同上），显式G2 SHA；build为标准库，可用python3。
python3 services/audio-search/holdout_review.py build \
  --freeze .local/a/mus040/phase03/freeze-01/freeze.json --freeze-sha256 1898f2bd0f286f1d1f66f074df552ead78d853002657481801deb3570efd1d83 \
  --output .local/a/mus040/phase03/packages-01

# 下条需同上HF_HOME/离线环境和只读venv。
../Music-Resource-Management-System/.local/a/clap-venv/bin/python services/audio-search/holdout_runner.py run \
  --freeze .local/a/mus040/phase03/freeze-01/freeze.json --freeze-sha256 1898f2bd0f286f1d1f66f074df552ead78d853002657481801deb3570efd1d83 \
  --output .local/a/mus040/phase03/runs-01
```

## 包与页面

新schema `sonora-independent-review-pack-v1` / `independent_test`，根仍6字段。`holdout_contract.py`标准库校验显式G1/catalog pins、20身份/独立副本和8原文；`holdout_review.py`重建全矩阵/新指纹，`seal`只供labeler侧原包SHA+本地导出，40项全合法才输出dataset/payload SHA、完成数和合法性四字段。浏览器新增中文可听线索/0–3说明、批次/保管提醒与完成回执；原四schema/草稿/评分/播放器保留。LOC两个provider完整JWT/bytes/SHA通过后按较短浏览器实际终点，包时长不改、rights用官方/use页面不造CC0。

真实现有8080/5175、原演示账号：四包逐一导入0/40/无旧草稿替换；三线索/四评分说明、07/08无匹配提醒、无模型提示、未完成回执禁用通过。实际20首全部获取/校验字节后可播放；FMA和MusicBox来源、底部曲名/暂停、页面PageUp进度约27秒/暂停/重新获取并续播通过。只填临时代号检查相关度启用，再清空，真实相关度/人工区间从未填写。

另一明确合成包用完全不同query/Java ID/来源ID/标题/内容SHA及独立指纹，不播放假音频；40项全合法后实际页面导出JSON和四字段回执，回执payload SHA等于同次完整导出确切字节，无分布/个人字段/正文路径。未对真实test生成假分；合成导入/导出不写草稿。最后恢复第1批0/40、代号空、试听停止、回执禁用；667px下scrollWidth667，无浏览器error，截图仅私有。早一次异步导入快照未完成即比较，等待可见批次后通过；原生App文件选择检查不可用，改用文档提供的浏览器filechooser成功，不是产品修复。

交付私有 `.local/a/mus040/phase03/packages-01/sonora-independent-batch-1..4.json`，四包及开始说明合成ZIP。完整判断由用户本机保管，先交四批完成回执；160合法与已保存五runs SHA齐全后才G5一次接收/打开完整导出。当前真实新判断/收到完成回执/打开qrels均0，未计算任何新test质量指标。

## 验证与保护

- 音频目录238项passed（原211+新27，最终15.573s）；source/import78项passed（17.555s）；Node84项passed（原77+新7）；npm build通过（2.18s），保留旧>500kB bundle提示。全部是实际执行，不把合成权重/输入冒充真实codec或真人。Python↔Node对同合成包canonical/完整导出字节与labeler seal回执相同。
- 初24有12个fixture准备错误（fake query SHA未同步runtime config、fake Path未序列化）；修正后新27/完整238通过，失败日志保留，子集/重复运行不累计。测试命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts:services/audio-search <venv-python> -m unittest discover -s services/audio-search -p 'test_*.py' -v`（同只读HF环境及本任务NUMBA缓存）；`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=scripts python3 -m unittest test_holdout_music test_research_import test_holdout_assets test_holdout_import -v`；Node22执行`node --test web/src/utils/*.test.js web/src/stores/*.test.js`；在web按现lockfile `npm run build`。现有依赖齐全，未重新安装/升级。
- 952保护文件SHA均保持（旧141/G1/原query/双权重/旧run及phase02原件/catalog/副本）；共享54cache集合/hash保持，原版干净f3b0da1；8080 PID96842/5175 PID4143不重启。新增本任务目录0700/文件0600，独占输出拒绝覆盖。无资源写API/SQL迁移/新上传/metadata修改/服务/锁/依赖/模型切换/main合并；浏览器只正常登录和读播放。
- 未重复无关Maven/数据库写入流程。仅单标注者、曲名/来源可见、元数据关系与字节排重不保证声学/预训练无重叠；没有双盲/专家一致性/参考音频/IoU/显著性/P95/生产或线上检索验收。正式P@5/nDCG及预注册差值待G5，不把排名准备当质量提升。

A/B 02:31:25Z与02:52:27Z sync均fetched，B610c03e/source0e8de159未变、已ack；B N1原035-R2卡/dispatch仍assigned，不替换或外推035限定批准。最终提交后原子publish/sync回读，远端可读不等于B认领/审核或main合并。
