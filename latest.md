# Account B — MUS-068：网页云端真实 CLAP 索引链路通过

- 任务／owner：MUS-068 / revision1 / review；active_owner b，slot B。B 保留完整开发、验证、发布与唯一 STATUS，A 继续暂停；用户决定最终合并，阶段完成不归还职责。
- 分支／基础 SHA：codex/MUS-068-real-discovery-index / 85537787606a138f0747cc8f776637c43745e0b7。准确交付 SHA 由本次固定入口 handoff.source_sha 给出，不在自身提交内预填未知 SHA。
- ack_peer_feed_sha：45b366229170f3af00456ba96fbada5946e5f61e；A source 082dadc35213a696107d6f4f966735d854d860d3；当前无再次移交。计划先发布 source6539631d4a7bfb679fb8e1653cd5647083f9005b / B feed462c147b12cfa79d55931787b8c94a13e0c6037b。
- 实模准确运行基线：已发布且工作区干净的 **173763ca3da0f9b9ab84e95893b2189f27c52a45**，B feed de5feb676a71aa5c41b4b4bcc98279aa585c8b66。之后仅补显式资产准备工具/8项测试及文档；本轮模型和索引核心源码未再改。

实际完成：MP3 实际EOF、单声道/48kHz soxr_hq、10s/5s窗口及右补零；固定 CLAP A CPU FP32 / identity / fulltext256 生成512维精确片段索引与整曲均值。内容/来源、模型/cache、源码和有效样本边界由 build-proof 绑定，消费者复核后才激活 manifest，失败/重跑不覆盖旧索引。真实文本保留全部实际 token ID；超过256明确400。新增固定pins资产工具，仅显式下载至全新私有目录，或只读校验，不由运行服务下载。

修改文件：services/audio-search/discovery_build.py、窄改 discovery_index.py / discovery_server.py；scripts/build_discovery_index.py、verify_discovery_runtime.py、test_discovery_build.py、prepare_discovery_assets.py、test_discovery_assets.py；AGENTS、README、PROJECT、CONTRACTS、唯一 STATUS、docs/verification/MUS-068*、本 latest。无 Java/Vue/schema、依赖锁、旧冻结研究代码、A feed/派发或历史报告修改。接口变化仅 E42 生产 manifest 必需 build_proof_sha256 及内部证明/缓存校验；E41 Java 浏览器 API 不变。

验证命令与结果：

| 检查 | 实际结果 |
|---|---|
| test_discovery_build.py / test_discovery.py / unittest test_preprocess test_checkpoint_model / test_discovery_assets.py | 23+14+19+8 = **64**项单测/回归通过，0失败/错误/跳过；显式合成桩不计实模 |
| build_discovery_index.py | 2首真实开发音乐、**74片段**，exit0，38.24s墙钟；不是P95 |
| verify_discovery_runtime.py | **63项断言**通过；3文本×2模式、独立余弦复算、允许集合/内容/版本/auth及时间；100实际token完整，>256拒400 |
| 正式worker CLI和失败保护 | **5案例**通过：4个正确拒绝、1个真实查询200；旧索引全文件hash不变，worker均停止 |
| 冻结EOF reader PCM对照 | 2首逐样本严格相同，最大差0；B同操作方另实现复算，不是A独立验收 |
| 固定资产 --verify-only / pip check | 通过；22 cache pins；只读校验无外连、无神经模型导入；通用完整下载以假HTTP验证，未重下整包 |

构建/runtime/正式CLI的Python socket审计外部尝试均0；该检查不等同全操作系统网络审计。真实初次获取的原始收据、完整命令/日志、失败目录与生成资产在本B ignored目录留存；公开[报告](../../verification/MUS-068.md) / [聚合JSON](../../verification/MUS-068.json)只归档结果与hash，不把私有文件hash说成原件已传Git。

数据／模型／索引版本：既有development中固定 Morning / USUAN2300003 与 Take the Lead / USUAN1100695，Kevin MacLeod / CC BY4，来源及署名留存；checkpoint SHA fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd；RoBERTa revision e2da8e2f811d1448a5b465c236feacd80ffbac7b；辅助BERT/BART只取SDK import固定tokenizer，不取/运行其神经权重。model clap-A-fae3e9c0-identity-fulltext256-v1；index mus068-clap-a-identity-v1；manifest SHA 49aafb30426646936a0d3d3b82bba3871a9d1e0b99c83820d35b06e0b43790bb；其余完整pins见聚合JSON/资产计划。

未执行／问题：未在本云端重跑 Java/MySQL/Vue；清单ID680001/680002尚不是本轮Java真库资源。未验证实模浏览器整链路、多人权限变更、P95/负载/生产部署、参考音频上传或质量提升；未训练/微调/读held-out/做人评。两首同作者开发音乐不外推正式语义质量。首次float64 fixture失败、辅助tokenizer import阻塞和私有harness sys.path错误均留原始日志；修正后单列通过，不把错误原因的exit1计成功。原067的345/89/14/43/13均为历史，不称本环境本轮执行。

下一步：**MUS-069 / B / todo**，依现行STATUS建立独立Java/MySQL/Vue运行配置，真实上传/审核后绑定数据库资源ID，在全新目录重建索引，再验证真实gateway/页面片段与权限闭环；不复用本轮受控ID假称已整合，不等待A接回。质量评估另列，不根据两曲排名换曲调参。

推送／释放：native CLI push128已留原始日志；使用已获写权限的GitHub API，按 source→B feed 顺序非原子发布，成功必须逐项回读 SHA、tree及latest正文，实际结果由发布回执/最终回复给出。成功后本任务实现路径解除占用，所有私有worker停止；B仍保留职责与STATUS写入，A不因此恢复。未推/合并main，未force push。
