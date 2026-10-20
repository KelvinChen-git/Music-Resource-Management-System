# MUS-021-R1-B：空对象与用户专属写列增量复核

- task_id / assignment_revision：MUS-021-R1-B / 1；owner B；assigned未认领。
- reviewed_sha `0f12212123616809ea0a917e43fc11e5f564ab46`；comparison_base_sha `a9655750b6a4a5df07c2d64abd7f809fdd1e5978`。
- 任务分支 `review/MUS-021-B-user-update-boundaries`；只允许写 `docs/reviews/MUS-021-B.md` 与 `docs/collaboration/account-b/latest.md`。
- assignment_source_sha必须取发布本卡的A handoff.source_sha，不能拿reviewed_sha替代；开始主动claimed并回传实际ack_peer_feed_sha。

MUS-017限定批准已由A正式接收，C1关闭，原报告按历史feed/source原字节归档，E1/E2转本新任务。MUS-020已完成并有B已读确认，不重复领取017/019/020。当前A源已包含Sonora前端，但本卡不修改/重做UI，不把后台增量批准当整站或现有演示服务升级。

## 准确范围与输入

输入CONTRACTS A10、verification/MUS-021.md/results.json、MUS-017-B及接收JSON。业务仅UserController、AdminUpdateUserDTO、UserServiceImpl；测试增加HTTP3/六入口6并适配旧fixture3。schema/锁文件/POM/前端/Python无变。A旧业务加新测试定向64：7 failures/1 error；修复后默认和显式*Test分别14类332项零失败/错误/跳过，两个命令各自证据记录，不把旧负例写为真库覆盖复现。

1. E1：管理员PUT /users/{id}用独立四字段DTO，`{}`和全null保持业务字段，仅updated_at更新。正常name/email/role/avatar沿用原约定，省略/null保持、avatar空串清空、非空同值/新值仍经原上传锁校验。未知/保护字段及body userid忽略；WHERE/返回绑定路径目标。普通用户空对象走管理员拒绝，匿名仍经JWT入口。不全局移除Users身份注解或改NULL/Jackson配置。检查响应与独立SQL，不只看HTTP200。
2. E2六入口：lockUser仅is_locked/lock_time/unlock_time/updated_at；lockUserWithReason再写本次非null lock_reason；unlockUser仅is_locked/unlock_time/updated_at，保留锁原因/锁时间。上锁明确清NULL旧unlock_time是本轮冻结行为，不能因ORM旧忽略NULL而漏掉回归。密码三入口changePassword/resetUserPassword/resetPassword仅password/updated_at；目标userid/原校验/编码/成功后验证码evict保留。
3. 真库补验用自己的新临时clone/库/合成账号/图片；至少覆盖空对象与全null、未知/保护字段/伪造body id、普通用户拒绝，以及六入口实际持久值/专属写列。具备环境时用SQL fixture持有目标行，让正常请求读旧快照并在UPDATE等待，另一连接改头像/邮箱/角色/其他安全列后提交，核验专属写入及未提交新值保留。锁入口应与密码入口分别取证，不能只查最终avatar就宣称所有列均受保护。不得把A捕获wrapper的合成状态harness当真实并发。
4. 密码验证码路径不要发送真实邮件或要求用户邮箱：可在隔离测试进程私有缓存fixture中设置合成code，或用实际Spring上下文调用并明确区分服务调用与普通HTTP；不得改产品SQL/鉴权/断言来制造成功。无法安全执行则精确blocked该分支，不用已有成功项覆盖。保留密码不匹配/错误code/mapper失败时不写入或不失效的原行为检查。
5. 不改鉴权撤销竞争、同密码并发请求/验证码原子消费、其他删除路径、生产部署或整个用户系统。发现不属本卡的新问题单列静态/实证，不擅自扩实现范围。无需重复完整019/020浏览器、前端安装/构建、Python或MUS-016导入器审核。

## 验证与交付边界

先核对准确源码/原lock与上述输入；Java可重用既有隔离环境，必要时冷编译默认全量，显式测试对照若不新跑要如实标未运行。新旧失败、独立测试命令、最终业务项和环境适配分别记录，不拼成一次全passed。B可使用既有私有Linux工具/TCP路径适配，必须披露；不得访问A8080/5175、演示账号或原曲库，不迁移已有库、不发真实邮件。进程仅停止自己登记者，并确认自建端口释放。

只提交两允许报告，release占用并写review_completed及approve_scoped/request_changes/blocked、task/revision/reviewed/comparison/assignment/ack、实际运行结果/未执行/原始哈希。私有日志未交付时A不能自行重算；SQL fixture与正常HTTP参与者、实际观察锁等待与最终结果分别表述。publish --account b或已授权的顺序备用路径后回读，披露原子/非原子；不把发布说成A已接收。

MUS-016独立审核仍待后续派发，main未合并；本任务不允许修改A业务/台账/任务卡或其他报告。协议仅会话工作，不启动轮询或后台唤醒。
