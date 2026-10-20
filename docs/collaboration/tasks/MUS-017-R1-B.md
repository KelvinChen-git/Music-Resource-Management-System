# MUS-017-R1-B：管理员NULL头像及局部更新复核

- task_id / revision：MUS-017-R1-B / 1；owner B，assigned未认领。
- reviewed_sha `f351b0e2030e5411b6f530ca039c694d4ca091d3`；comparison_base_sha `d443966148336b719cebdb041ea175dfbbfdc500`。
- 任务分支 `review/MUS-017-B-admin-avatar-null`；仅允许写 `docs/reviews/MUS-017-B.md` 和 `docs/collaboration/account-b/latest.md`。

MUS-015-R1-B已完成范围内approve，A收到feed23ecb673/source8f622775并原字节导入报告，未将含16完成项的blocked命令改写为全通过，也未将另两项锁专项和三正常HTTP竞争混淆。C1的P2既有NULL回显/持久值差异由本卡处理，不重复领取旧卡。MUS-016导入前端的独立审核仍单列，不因审查本卡而默认批准。

按当前A handoff.source_sha读取入口与本卡，先检查自身同task_id/revision是否已claimed/completed；首次发布claimed，包含assignment_source_sha、实际ack_peer_feed_sha、准确reviewed_sha。完成回传review_completed与approve/request_changes/blocked、实际运行数/阻塞/报告路径并释放占用，不由A代认领。

## 复核内容

1. 契约：管理员PUT /users/id的name/email/role/avatar缺字段或null保持；avatar:""清空，非空路径每次requireAvatar。全局NULL策略/schema/API字段不改；profile行为不改变。回应只修改非null提交字段，不额外宣称读取快照总是最新值。
2. 管理员从完整entity updateById改为局部UPDATE。仅提交name时不出现avatar/email/role/is_locked/password/lock_reason列；明确role/email/新头像正常写，WHERE绑定目标userid。避免为了null返回保留旧avatar而把旧引用A回写，检查是否存在未覆盖写路径。
3. 同值/新非空头像仍校验目标owner、完成、未删除，FOR UPDATE及原事务覆盖到写引用；未新增绕过。清空不需要创建新的文件引用。不要将局部写列单元断言当多连接实证。
4. 测试：新增三个MockMVC/mapper用例，在旧业务+新测试的55项中3失败；新完整Java323通过。核对null/省略的响应+不含avatar写列、显式空串参数、仅名称响应保持未提交邮箱/角色且保护列不写。既有安全回归继续通过。
5. 用自身既有新隔离库/合成PNG补真HTTP/SQL：null、缺字段、空串、合法同值与新头像、他人/删除/未完成/NULL owner拒绝；逐步比较响应和独立SQL值。检查仅名称不会回写旧头像/安全列，具备环境时做受控多连接时序，精确区分SQL fixture、普通HTTP参与者、观察到的锁与最终结果。

## 输入、环境与边界

输入docs/verification/MUS-017.md、MUS-017-results.json、MUS-015-B-acceptance.json与自己的原报告。A本机新323单元通过，但当前A网站/20首演示和本机B服务仍跑MUS-014；不要把请求A旧服务当新版本验收。可沿用已披露B私有工具/loopback TCP适配，在准确SHA的新临时clone上验证，不改仓库实现/断言、不要触碰A服务或演示数据。

私有原始文件未提交时只能提供自己确实观测的数字/原始哈希/环境适配；失败命令与已完成检查分开，不把重试合并伪装单次passed。无Python/前端更改，避免重复无关构建/安装。

只写两允许报告路径，不直接修业务、契约、A台账/任务卡、schema、依赖锁或main。保留未提交工作，不reset/clean/stash覆盖。完成提交后publish --account b，披露原子或备用顺序路径；A直接sync，无需用户搬运正文，协议不负责后台唤醒。
