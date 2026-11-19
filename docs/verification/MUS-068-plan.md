# MUS-068：真实音频在线索引导出与云端复验计划

日期：2026-11-18（America/Chicago）。owner / coordinator B，revision1；职责继承 MUS-067 的完整移交，A 继续暂停，无需重复领取旧卡或 A 串行批准。

- 分支：codex/MUS-068-real-discovery-index；准确基线：85537787606a138f0747cc8f776637c43745e0b7。
- 已读 A feed：45b366229170f3af00456ba96fbada5946e5f61e；B 前次 feed a2ec41d76e96deda45391f4f6d6d4461cbdd7f7d / source8553778；两边固定入口已实取并 sync。
- GitHub 连接已返回 push=true，且从8553778成功新建本任务分支；不推 main，不最终合并。
- 运行位置是 B 新的独立网页云端 Linux clone / slot B；Mac 目录和原 A/B ignored 资产均未挂载。上轮345/89/14和联调数字只保留历史，不当新环境复现。

## 允许范围与占用

新增 services/audio-search/discovery_build.py，scripts/build_discovery_index.py、test_discovery_build.py、verify_discovery_runtime.py；必要窄改 discovery_index.py / discovery_server.py 以绑定真实构建证明及完整文本验证，复用原 checkpoint_model.py / preprocess.py 的冻结参数，不改旧研究源码或模型版本。允许更新 AGENTS、README、PROJECT、CONTRACTS、唯一 STATUS、verification/MUS-068* 和 own latest。Java/Vue/数据库/API/依赖锁/A feed/派发/历史报告不改；本任务不重跑无关 Java/Vue全套，不把旧结果当新执行。

为满足独立云端环境重建，补充允许 scripts/prepare_discovery_assets.py、scripts/test_discovery_assets.py 及 docs/verification/MUS-068-assets.json：固定本轮已核权重/cache/两曲内容pins，只在显式--download且输出全新时获取；--verify-only不得联网或修改已有资产。运行服务/构建不自动下载，现有模型/索引/查询算法不变。原私有获取和运行证据保留，新准备工具不冒充已经重下全部资产；另做本地guard测试与既有资产只读校验。

## 冻结验收与内部契约 E42

1. 私有 catalog 明确资源 ID、源音频 basename、bytes/MD5/SHA256、来源/许可及固定证明；严格 JSON、唯一身份、只读正常文件、拒绝链接/越界/内容变更。生产构建不访问用户 URL、下载源文件、接收测试编码器或读取 qrels。
2. 真实 MP3 从 soundfile blocks 读到 EOF：原速率8–192kHz/单或双声道/最多600秒；单声道平均、soxr_hq一次重采样48kHz、10秒窗口/5秒步长、右补零，时间只含真实样本。窗口规则继承 corpus.window_bounds 的确定策略，保留声明帧数与实际帧数差异，不能把文件头长度当 EOF。
3. 只用既定 A checkpoint fae3e9c0/HTSAT-base/no fusion/CPU FP32/identity/fulltext256。显式本地checkpoint+离线cache；库和缓存缺失失败，不联网兜底。音频逐小批编码，whole=unit(mean(unit(segment)))，512维有限归一化，不训练/ANN/参考上传/重新调评测。
4. E41 manifest/features格式保留；clap_identity新增必需build_proof_sha256，绑定私有build-proof.json（数据/来源证明/模型/预处理/样本边界/源码与特征SHA）。真实worker加载时复核证明/特征/模型一致。synthetic_fixture的旧显式 opt-in行为保持。
5. 输出仅本clone .local/b，0700/0600且目录全新；失败/部分输出保留。模型/数据重校通过及可执行loader验证后才激活manifest，不覆盖旧索引。重复输出应在编码前拒绝，失败不得留下可消费manifest。
6. 先做有明确标记的合成边界测试，覆盖短/尾/无效音频、EOF、内容与证明篡改、路径、版本、非finite/整曲配方、部分失败和重跑拒绝；再单列真实模型/音乐/HTTP实跑证据，不能从模拟结果宣称实模或语义质量。

## 本轮有界资产准备（显式设置步骤，不是运行时下载）

- 新建 B 私有 Python venv，使用既有 requirements-spike.txt 的准确顶层版本；CPU wheel来源为官方 PyTorch与PyPI，不升级旧锁，不做系统安装或关闭TLS。
- 只尝试固定CLAP A文件（HF lukewys/laion_clap revision b3708341862f581175dba5c356a4ebf74a9b6651、2352471003 bytes、完整SHA），以及固定FacebookAI/roberta-base revision e2da8e2f811d1448a5b465c236feacd80ffbac7b的必要cache。固定pins校验后才允许restricted weights_only/strict loader。
- 2026-11-18导入预检发现laion-clap1.1.7的training/data.py会在import时构造BERT、RoBERTa别名和BART三个分词器（未参与本A/RoBERTa推理的额外模型分支）。补充固定的必要离线分词器缓存：google-bert/bert-base-uncased revision86b5e0934494bd15c9632b12f734a8a67f723594与facebook/bart-base revisionaadd2ab0ae0c8268c7c9693540e9904811f36177，只取tokenizer/config文件（合计上限8MiB），不取BERT/BART神经权重。RoBERTa别名从已核同revision缓存复制。旧import阻塞原件保留，不mock真实编码器、不修改旧研究模块或切模型；新增cache文件及别名refs纳入构建/查询指纹校验，仍包含在总6GiB预算内。
- 音乐最多2首，固定复用既有development_source_candidates_not_held_out的USUAN2300003 Morning与USUAN1100695 Take the Lead；从当前官方Incompetech元数据、作品页及CC BY4.0证明核验后获取。每文件<=30MiB，许可/身份/访问不通过就记录blocked，不自动换曲或扩库。保留attribution/原字节与获取收据；不读项目保留test/原标注，不声明来源独立或新增评测集。
- 总下载预算6GiB（模型/缓存/CPU依赖/两音频），无付费服务/新密钥/秘密扫描；持久文件仅本slot。网络/资源失败的具体状态和原件保留，不靠换模型或替身伪装通过。
- 固定运行探针文本为 Calm acoustic guitar music. 与 Energetic instrumental rock music.，另做>77且<=256完整token及>256拒绝探针；只验模型/索引/允许候选/时间/HTTP契约，不根据排名换数据或调参，不宣称质量提高。

本计划先提交再实施。完成后记录真实命令、失败与最终结果、代码/模型/数据/索引SHA、未执行范围；发布任务分支与B固定feed并回读，B保留后续职责，用户决定合并。
