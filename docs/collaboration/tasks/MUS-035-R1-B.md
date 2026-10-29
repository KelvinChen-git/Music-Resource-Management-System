# MUS-035-R1-B：两来源40曲离线工具增量复核

- owner b；revision 1；status assigned，先发布claimed并回读。
- reviewed_sha `9797ed4b8766f8cd5f6cd7759b86bd309cef2f7d`；comparison_base_sha `b42b767afc0bd3ddb76601a436f8073c3d72106c`。
- 建议branch `review/MUS-035-B-expanded-retrieval`；仅允许`docs/reviews/MUS-035-B.md`与own `docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡的A handoff.source_sha，不与035真实模型编码提交`17a31f5d5f4a04873d299c52f722dd3a890b9b5e`混淆。
- 033/rev1限定批准已接收，见[原字节接收记录](../../verification/MUS-033-B-acceptance.json)，原卡保留；不要重做033审核。036包工具/UI是后续单独增量，不在本卡批准范围。

阅读E8、[035报告](../../verification/MUS-035.md)、results及准确diff。只审新增research_corpus/research_probe/research_evaluate及三测试；旧corpus/preprocess/probe/source_review_pack等只读依赖。自造独立20旧+20新合成catalog/证明/解码、排名和人评，不读取A本机账号/音频/138判断/run/向量或缓存，不要求下载真实模型/音频。测试判断不算真人标签。

1. 两provider身份、前缀文件/证明/内容校验、显式六SHA、原20只读及跨来源去重、路径/硬链/symlink保护。新来源header与actual EOF分存、固定65536 float32 out读至实际0帧，长度/tell/finite/30–600s检查；不填零迎合header。用可控decoder替身检查真实返回长度，不称合成数据为真实MP3解码。
2. driver必须在模型构造前拒绝脏/非提交源码，输入/source/checkpoint前后核验、strict pinned512模型、原DSP/完整窗口/整曲均值/两mode top5与tie规则；独占输出和失败保留，禁止部分run复用。合成encoder/NumPy验证与实际CLAP推理明确区分；环境缺依赖就记录阻塞，不安装或改锁来掩盖。
3. evaluator对原三包/11 SHA/原新report和五工件完整绑定，查询raw pin后canonical相等，原20解码/窗口一致；新来源实际整数ceil/历史declared分开。五描述r/n/u与P@5上下限、未知则exact null、所有五query宏平均不排除未知、new hit计数，不把未判补0。独立构造含未知/交叉mode重叠/无未知和非法输入，手算聚合；原035实际输出只按公开聚合核文档，不冒充复算A私有结果。
4. 有界运行相关合成测试（`python3 -m unittest discover -s services/audio-search -p 'test_research_*.py' -v`需现有NumPy；可按可用环境分组），写清命令/exit/计数/失败与修复。新增独立断言不与作者168或子集累加；无需重复033浏览器/Java/MySQL/全站、训练/模型重跑、质量/P95。

当前A证据是开发语料扩展：同一模型40曲、1557片段，新20均在对应top5；whole23相关/2未知、segment24/1未知，未知并集3，精确宏值null。035勘误已明确032/033历史时长是header估计，原件保留；不能用本批准认证真实EOF/许可/独立效果或自动冻结discovery-v0。

只写两报告并释放占用，记录准确task/revision/reviewed/comparison/assignment/ack A feed、review_completed及approve_scoped/request_changes/blocked。发布source与own feed并回读，顺序发布披露非原子；不修改A台账/dispatch或产品，不合并main，无后台轮询。
