# 账号 A 最新交接

- A；2026-10-20 America/Chicago 01:31；task MUS-017；branch fix/MUS-017-admin-avatar-null；status review / new runtime acceptance pending。
- implementation_sha `f351b0e2030e5411b6f530ca039c694d4ca091d3`；comparison_base `d443966148336b719cebdb041ea175dfbbfdc500`。后续handoff.source_sha只补交接/派发及015接收状态文档。
- ack_peer_feed_sha `23ecb6738bc8c3441b79f690eada757eeb0533d1`；B source `8f62277513b3537cc78a4cd2a99f6b8398e6bf57`。

## 接收MUS-015 B复核

MUS-015-R1-B/revision1 review_completed/approve限定同值头像校验及既有空串清空；准确reviewed d9a2a15、assignment dbb6312、ack Ac618062。A核对hash、只差两B报告路径、原字节导入docs/reviews/MUS-015-B.md，不改B正文。

B独立Java320，旧55之前的52项测试3预期失败；真HTTP/SQL16完成业务项来自后续blocked命令，不改写整命令passed。另一轮performance_schema锁专项2项独立exit0，观察同一事务用户行WAITING/上传行X锁GRANTED；SQL fixture控制旧快照时序下同值删除头像被拒，引用保留B。不是三正常HTTP参与者竞争，私有日志不能由A重算。接收记录MUS-015-B-acceptance.json。

## C1修复：MUS-017

B发现既有P2差异：管理员avatar:null响应null而真库仍保留旧头像；空字符串确实清空。新契约明确name/email/role/avatar缺字段或null保持，avatar空串清空，非空路径每次requireAvatar。

管理员改为仅更新非null提交列及updated_at，不用完整实体回写旧头像/角色/锁/密码等状态。返回对象只应用提交字段，null不再假回显清空，未提交字段保持读取快照语义，不承诺并发最新值。

三新增MockMVC/mapper回归旧业务55项中3失败；修复后完整Java323零失败/错误/跳过。新真库响应/持久值与受控交错未验收，旧015批准不外推017。无Python/前端/schema/依赖变更，不无故重复50Python/Vue build；没有新A后端启动。

现有A/B服务、A20首授权演示歌曲与20条外部资料保持；后端仍MUS-014。无需用户本轮停止终端，MUS-016前端入口与已验证播放保留，独立复核仍单列。

## 新B固定任务

MUS-017-R1-B/revision1，reviewed_sha `f351b0e2030e5411b6f530ca039c694d4ca091d3`，comparison_base `d443966148336b719cebdb041ea175dfbbfdc500`，assigned未认领。入口docs/collaboration/tasks/account-b.json；仅写docs/reviews/MUS-017-B.md和own latest。先主动claimed，再按准确SHA补真HTTP/SQL；前015任务完成不重复领取，不代写B批准。

B可沿用既有私有Linux工具/TCP适配，新临时库/clone，仅fixture写入；失败运行和完成检查分别披露。协议无后台唤醒。main未合并，生产/整库中断/commit ACK丢失/GC/检索质量尚未验收。
