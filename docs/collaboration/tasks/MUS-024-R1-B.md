# MUS-024-R1-B：探索标注包完整性复核

- task_id / assignment_revision：MUS-024-R1-B / 1；owner B；review_completed / approve_scoped已由A接收，勿重复领取。
- reviewed_sha `1e83454474413fb6c58a73d82ace579656749bc0`；comparison_base_sha `3c7552ad2071847959eecf520956690dc083411e`。
- 分支`review/MUS-024-B-judgment-pack`；仅写`docs/reviews/MUS-024-B.md`和`docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡的A handoff.source_sha；先主动claimed，回传准确task/revision/reviewed/comparison/assignment及ack_peer_feed_sha，再执行复核。

MUS-023限定批准已由A正式接收，旧016对应R1/R2/条件性R3关闭，不重复领取。新任务只审Python标准库标注准备/校验，不重演导入器、后端、UI、CLAP编码或质量评估。先读CONTRACTS E1、verification/MUS-024.md/results.json及源码两文件。

## 验收与边界

1. 在自己的独立clone运行`python3 -m unittest discover -s services/audio-search -p test_review_pack.py -v`。A为17项；这是标准库测试，不需要下载SDK、音频、模型或访问数据库。若运行既有40全套，缺旧依赖须明确blocked，不能为本卡安装大模型依赖或把未执行23算通过。
2. 在自己的`.local/b/`构建独立合成run/catalog及报告hash，实际调用CLI build/validate，核对输出0600、null/0区分、候选并集排序/无score、准确内容/owner/来源/模型绑定；可参考仓库6曲目fixture，但额外命令/检查须单列，不把相同17测试相加。无需A私有run/51包，也不能声称复算A私有包或原始日志hash。
3. 明确期望report hash及四工件/catalog变化时失败；重算自有合成hash后，语义不一致、未知/重复ID、查询/segment错配仍拒绝。提交包修改split/owner/hash/候选/文本/时长/来源/建议区间或指纹都不得被当人工字段接受；仅手工四字段允许变化。
4. 相关性只整数0..3，null与0区分；缺匿名代号/合法UTC时间、布尔/浮点评分、空判断带人工数据、负/越界/重叠/倒序/浮点区间、0相关性带正区间均拒绝。部分合成判断/无定位的正相关可通过；校验不验证身份/真人听音，不把测试fixture称真实人评。
5. 输出仅当前clone `.local/`；已有文件/符号链接拒绝覆盖，逃逸路径拒绝。重复命令失败后旧字节/原输入保留。没有原始音频读取/权限刷新/HTTP/公开媒体服务，不能将包视为播放授权；断电/fsync/恶意并发FS不在本卡。
6. 审查文档事实边界：8查询/51对仍全null仅A声明的本机结果；模型建议可见非盲评、pool非穷尽/held-out，无质量指标或discovery-v0冻结。真实人评/试听页面仍后续，不评价模型效果。

不访问A服务/数据库/凭据/缓存/音频、不请求真实账号或人工标注个人信息、不改A台账/产品/依赖/锁/公共JSON，不创建服务器/定时任务或合并main。新工件只在自己的忽略目录，合成标注代号明确test。保留失败命令及已完成检查，不累加伪装成功。

最终两报告写review_completed、approve_scoped/request_changes/blocked、准确命令/计数/源SHA/各边界和占用释放；提交后publish并回读，备用顺序发布要披露非原子。发布不等于A接收；无后台轮询，勿把A feed变化当重复领取依据。

## A接收

B feed `76b8244407e9f27f3edbaa113437c1575902e966` / source `b15ead23e0a9f7ebb91b9d5344559c4d46353877` 已核验，原字节报告及[接收JSON](../../verification/MUS-024-B-acceptance.json)已归档。限定工具/合成数据范围，不外推真实51对人评或质量。
