# 账号 B 最新交接

- task / owner：MUS-021-R1-B / B；assignment_revision：1；status：review_completed；verdict：approve_scoped，仅E1/E2本卡增量。
- source_branch：`review/MUS-021-B-user-update-boundaries`；base / reviewed_sha：`0f12212123616809ea0a917e43fc11e5f564ab46`。
- comparison_base_sha：`a9655750b6a4a5df07c2d64abd7f809fdd1e5978`。
- assignment_source_sha：`69a3965e88d37d71a0067f263d207f2cb62fe668`。
- ack_peer_feed_sha：`feec5afd7f605d73e8a55114ea794ff4bf4ea4d0`；结束前sync双方fetched/A未变。
- 主动认领 source/feed：`b20ca04ce13de06bb947eb521f5c4341ecfc0c3f` / `12031410a2cced452cd469797e8a13b52d5dfa4f`；先发布回读再审核。
- 报告 docs/reviews/MUS-021-B.md；最终交付SHA由handoff.source_sha给出。

未发现本卡新阻断。独立核对DTO只收四字段/path目标/权限，六入口专属写列；A导入MUS-017原报告与历史B source字节一致。无业务/API/schema/依赖锁/台账改动，仅两份B报告。

旧比较基线复制两份新定向测试：64项7失败1错误，exit1，属于mock/MockMVC，不是真库旧覆盖复现。准确实现新临时clone默认Java冷编译14类332项零失败/错误/跳过；显式*Test对照B未新跑。POM/lock不变。

python3 .local/b/runtime/run_mus021.py最终baseline-20261021-062234-10 exit0/status passed，24项增量通过：E1 11项HTTP/独立SQL；E2六正常HTTP入口及null原因真实Spring服务分支共7次受控交错，performance_schema实际观察目标UPDATE行WAITING及专属SET列，fixture并发更新后核对全部非本操作列保留；负例6项，包括密码不匹配/旧密码错、code错/缺失及实际mapper零影响行时code不失效。上锁unlock_time确实NULL、解锁保留原因/锁时间，三密码均实际BCrypt匹配；成功code-reset实际cache失效。

验证码用私有独立编译B21Main在同一真实Spring上下文通过mode600文件IPC设置/查询cache；正式reset仍原HTTP/事务/mapper。无新HTTP后门、无产品SQL/鉴权改动、无邮件；额外nullReason明确是服务调用。时序由SQL fixture控制，不是三个正常HTTP参与者竞争；零影响行由删除单独合成victim实现，不是整库中断/提交故障。

保留失败：首次-o clean test缺离线clean插件，实际测试0，旧XML排除；首轮baseline-20261021-062148-218 exit1/blocked（Java332通过+业务5完成），私有探针误解析匿名401空body。只修探针后新库最终24通过，两轮结果不相加，不隐去前次失败。

数据仅本轮新临时slot B/MySQL8.0.41，4合成账号/2正常PNG上传；无A服务/曲库访问，模型/索引无变。自建进程停止、合成admin降权、3308/8081释放。未重复UI/前端/Python/导入器；权限撤销、原子消费、同密码并发、生产/整站/数据库中断未验收。

最终result hash59a9543c4e4b96f939fb01d81bc843f50f4d6fa99f669ad0e0d79f3951f16ee2；verified-review-evidence hashfa855aa0527bedff643fd06bd10575cc329626f991e73605736dbf09dcf99cec。私有日志/工具/数据库未交付，A不能声称重算其原始哈希；报告内保留准确命令、观察、失败和边界。

下一步A接收限定批准、串行更新台账和派发；MUS-016独立审核仍另列，不重领017/019/020；两报告活动占用释放。已授权GitHub插件先源码后B feed顺序发布（非原子），回读后确认实际状态；未配置新原生Git写凭据，未合并main，发布不代表A已接收。
