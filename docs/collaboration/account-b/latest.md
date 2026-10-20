# 账号 B 最新交接

- account: b
- task_id: MUS-015-R1-B
- assignment_revision: 1
- task_status: claimed
- owner: B；集成负责人/STATUS写入方A
- branch: review/MUS-015-B-avatar-revalidation
- base_sha / reviewed_sha: `d9a2a15791da0db4374c5de093a752a5aa202a25`
- comparison_base_sha: `feb935ad5c7eb4eb8a11065f3d5c18ed2a93dab1`
- assignment_source_sha: `dbb631218b8ee7c87823ce594494b908b2849e32`
- ack_peer_feed_sha: `c618062350efb32a30cb7065694945fab02dd39c`
- allowed_output_paths: docs/reviews/MUS-015-B.md；docs/collaboration/account-b/latest.md

开始sync成功，核对A固定入口/完整卡片、工作区及精确SHA，从准确reviewed_sha新建本分支。首次主动领取本卡revision1；前MUS-014-R1-B及其独立真库补证已完成且A确认接收，不重复领取。

复核两入口同值头像重新校验、事务与上传锁覆盖至引用写入、删除路径锁顺序/当前读；名称单独修改、合法同值、新头像与管理员清空、NULL owner/他人/删除/未完成拒绝；核对新增三项回归的旧实现失败与修复后结果。独立验证只操作本次B开发库/合成fixture，不连接A本机服务。

本轮仅占用上述两报告路径，不改业务源码/API/schema/依赖锁、A台账/任务卡/feed或main；接口/模型/索引变化none。尚无新审核verdict；A的Java320不冒充B执行。既有私有Linux工具/TCP/原生临时目录适配可供运行，检查结果完成后如实回传。

沿已披露GitHub插件备用顺序路径发布source再feed并回读，非原子原生Git推送；最终delivery_sha由handoff指定，发布不代表A接收。下一步独立审核/验证；完成后释放两报告路径，无后台轮询或最终合并。
