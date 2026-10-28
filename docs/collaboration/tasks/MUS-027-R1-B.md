# MUS-027-R1-B：相关度评分入口增量复核

- task_id / revision / owner：MUS-027-R1-B / 1 / B，assigned未认领。
- reviewed_sha `2ed661daff6e66856cdef6a6789a9edea7a2dc5d`；comparison_base_sha `a945927d45d982e7bda22cc7a84dce930787b52f`。
- branch `review/MUS-027-B-rating-entry`；仅允许 `docs/reviews/MUS-027-B.md`、`docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡A handoff.source_sha；先claimed并发布准确task/revision/reviewed/comparison/assignment/ack。

026限定批准已接收，原报告字节/receipt归档；N1开发浮层观察记录，不在本次范围。只审ReviewWorkspace.vue一个产品文件及E2交互补充；不重复026音频控制、权限、Java或CLAP。

1. 按verification/MUS-027运行8包helper检查及前端build，复用现有lock，不升级依赖。
2. 独立合成E1包/自有隔离登录会话：空alias时就近输入可用、四评分disabled且原因可见；非法开头/中文/空格提示格式，合法后全部可选，无默认评分；鼠标/键盘选择0/3，选择本身写代号/UTC，清除回null。非法或清空代号不抹已有判断，切候选不自动补分。
3. 按owner+dataset合成草稿保存、刷新后导入不静默覆盖，明确恢复可保留原判断；导出固定run CLI仍接受，未判断null不变0。手机/桌面输入提示与评分无横溢，可实际点击。测试标签明确synthetic，不能称真人人评。

允许复用自有B隔离运行/账号；只需前端标注流程，不要求新建媒体/重跑后端完整审计。若采用API/user边界替身，须明确披露，不声称真人身份/真实HTTP鉴权。不可访问A服务/账号/真实51包或用户草稿。生成工件仅ignore；无需读取A私有截图/日志来冒充复算。失败/执行数/边界分别记，不累加旧31/30/37。只启停自有进程并清理端口。

回传review_completed + approve_scoped/request_changes/blocked、准确SHA/计数/失败/限制及占用释放；发布并回读，顺序发布披露非原子。发布不等于A接收/main合并，无后台轮询。
