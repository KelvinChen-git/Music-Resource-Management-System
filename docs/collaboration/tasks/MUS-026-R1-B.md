# MUS-026-R1-B：审阅底栏与手动seek增量复核

- task_id / assignment_revision：MUS-026-R1-B / 1；owner B；assigned未认领。
- reviewed_sha `d766dcd09df3cc1e54130ca80aefb946985ee2b3`；comparison_base_sha `0ae63f9d6a4632ffbfa1c0cedc017aad6cea862c`。
- 分支`review/MUS-026-B-review-controls`；仅写`docs/reviews/MUS-026-B.md`与`docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡A handoff.source_sha；先claimed并回传准确task/revision/reviewed/comparison/assignment/ack，再审。025限定批准已正式接收，不重复025全37或整个旧系统。

用户反馈审阅音频未显示底栏/页面不能seek，新范围为CONTRACTS E3与verification/MUS-026.md/results.json。仅6实现文件：reviewAudio/helper test、ReviewWorkspace、sonoraPlayer store/test、SonoraPlayer.vue；无API/schema/依赖锁/公共JSON/原标注改变。

## 增量验收

1. 固定Node22运行verification中的四文件命令，A为31（8包11音频6媒体6store），build使用现有lock，不重装/升级无关依赖。store测试实际Pinia/Vue，API/user/audio替身明确，不能算真实HTTP。
2. 自己隔离slot/clone/普通测试账号/合成MP3与E1包，可沿用B025私有适配但不改产品，别访问A服务/私有51包。真实整曲与片段试听应在底栏显示对应候选/模式/时间，两处滑块改变同一audio。整曲定位中间，双向seek/暂停时seek不自动播放/继续新GET；片段钳制选定start/end，seek终点停止，终点继续从该范围起点重播。手机页面实际操作slider/按钮与1440布局，无横溢。
3. 底栏暂停/继续、音量静音与页面一致；审阅时普通随机/循环/上一首/下一首不可用，避免从片段跑到旧队列。原普通非空队列/当前曲目保留且暂停；主动点队列曲目接管审阅，离开研究页后原普通控件可恢复。正常播放普通曲目的pay请求原行为单列，审阅请求无pay/JWT query。
4. 暂停释放Blob，继续重新GET/完整SHA字节校验，错SHA与拒绝继续后两处seek/取点禁用，无旧音频复活。在自己的隔离合成账号做最小真实403或404重播拒绝即可，别重复全部旧矩阵；锁/删除等夹具来源与恢复清理披露。
5. 检查普通pending切歌/旧响应不能夺回审阅；旧review publisher不能污染新会话、普通ended不能自动推进；离页/换候选/导入/退出/换账号清理绑定。原用户标注/草稿不因控制操作改变，不自动填真实评分。本轮只用明确test标注fixture，模型/音频非真实质量评测。

不用重做025全标注/83CLI/上传/模型/完整权限审计。A实际普通队列为空，队列非空/旧响应隔离只有store替身补证，优先补真实控制链。私有原始日志/截图未传不可声称复算A；运行准备/失败与最终各自记录，不累加。没环境明确blocked/执行数，不能拿fake audio当浏览器。

不访问A3307/8080/5175/账号/缓存/曲库，不改Java/Python/API/schema/锁/公共JSON或A台账。只启停自己进程，结束核对端口释放；生成数据/私有适配仅.local，交付两报告。完成写review_completed与approve_scoped/request_changes/blocked、准确SHA/计数/失败/边界/占用释放，publish并回读；顺序备用发布披露非原子，发布不等于A接收，无后台轮询/main合并。
