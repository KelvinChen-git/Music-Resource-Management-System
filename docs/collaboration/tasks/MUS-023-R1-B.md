# MUS-023-R1-B：导入恢复/证明绑定/公开来源增量复核

- task_id / assignment_revision：MUS-023-R1-B / 1；owner B；review_completed / approve_scoped，A已接收；勿重复领取。
- reviewed_sha `ab8205827456ec6aeab3bcb289722a236e644f6b`；comparison_base_sha `81566b1634aa19cb8493d2c2740c6d002a75ba4e`（已接收016报告、业务修改前）。
- 分支 `review/MUS-023-B-demo-import-recovery`；只允许写 `docs/reviews/MUS-023-B.md` 与 `docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡的A handoff.source_sha，不能用reviewed_sha替代；先主动claimed并回传实际ack_peer_feed_sha/任务/revision/准确输入。

MUS-016-R1-B已完成request_changes，A核验并原字节接收原报告/receipt；不要重复旧016全部13场景、017/019/020/021或把MUS-022离线结果当本卡批准范围。只补R1/R2与条件性R3最小增量；不直接改产品/台账/任务卡。

## 范围和输入

CONTRACTS A11、verification/MUS-023.md/results.json、MUS-016-B及receipt。业务仅scripts/import_demo_music.py、DemoCatalogView的安全helper调用、web/src/utils/catalogLinks.js；另为相关测试。目录布局/Java/schema/依赖锁/公开JSON/原音频/MUS-022代码不变。新的本地状态demo-account-state.json先由.local ignore覆盖，0600，仅pending/confirmed、凭据SHA256指纹和确认userid。

A定向旧业务早期11方法subset为10 failures/2 errors（含subTest），不是HTTP/MySQL；当前新增恢复测试已12方法，不能机械与早期计数比较。首轮fixture错误14 errors未触达产品，日志单列。固定源码全scripts62/链接8/build通过（全62有两个独立成功命令不相加），旧5保护fixture补shareurl；A原20证明仅只读兼容验证，无新导入。A无真HTTP/MySQL新恢复证据，不能沿用B旧016成果当新代码验收。

## 增量验收

1. R1自己的新临时clone/slot B/空库，用合成普通账号/音频，提供方可沿用原urlopen源fixture，本地API保持真实HTTP。分别注入“保存凭据后、register未送达”“明确register拒绝”“register已成功、响应丢失”；取消故障重跑同一凭据，核对状态pending→confirmed、凭据字节不变、真实user/upload/resource不重复。响应丢失可能同次login恢复，不强制第一run失败，记录真实调用顺序/结果。
2. pending先login；仅旧/auth/login business500+精确Invalid email or password可register；网络/其他business500/锁定不判定账号不存在。confirmed登录失败不再register，legacy无state但真实已建账号只login确认；credential指纹不匹配/确认userid变化或非USER不得改写confirmed或自动建新账号。新状态0600，未知/损坏状态保留失败。不要删凭据/生成第二账号掩盖。
3. R2完整缓存正确SHA的前提下，分别改proof.size/source/license或移除必需字段：预期在本地API前失败，保留原字节/证明，不生成本次passed结果，不重造证明。正确完整缓存仍不查提供方，正常重跑计数不变；旧http CC许可与https同路径可兼容，source按验证过的同track ID canonical匹配。错误源host/ID和准确许可版本变更不能因SHA正确得到认可。不是要求实时源许可查询。
4. R3合成shareurl带Client ID canary/query/fragment或slug：来源需匹配HTTPS www.jamendo.com/track/ID、无userinfo/意外端口，公开catalog只含按ID构造的canonical来源，不能携带canary。错误源身份/host/端口在本地API前拒绝。许可有query/fragment/userinfo拒绝。新下载证明也只写canonical source/license，cache读校验与导出一致。
5. 页面只换helper不改布局：运行node --test web/src/utils/catalogLinks.test.js，核对现有20来源/许可及20外部资料链接保留目的页、无userinfo/异常端口/query/fragment；Apple仅保留单一数字i，重复/非数字拒绝。此为纯函数/静态数据检查，不冒充浏览器。必要时build，无需无理由npm ci或重复019/020UI与player/media完整套件。
6. 原B016已通过的上传ledger/metadata中断、歧义/空结果等无需全套重演；选必要正常首次/缓存重跑回归。发现新旁支或未测边界按实证/静态单列，勿改代码使之成功。本卡也不要求确认所有kill进程/断电持久性、法律/生产许可、模型质量或MUS-022标签。

## 环境、报告和发布

不访问A3307/8080/5175、A账号/Client ID/私有缓存/曲库，不下载现实音乐或要求用户真实凭据；不发邮件、提权既有用户、自动审核或写旧库。数据仅本轮新普通账号/合成音频/空库；catalog输出承接在一次性临时副本，不修改审核checkout跟踪的公共JSON。提供方HTTPS/音频替身与真实本地HTTP/SQL清楚分开；保留TLS/产品输入校验/权限/断言，适配只限私有路径/传输。

A旧证明“20匹配”不是B新实跑，R3仍是条件性输入公开风险而非已发生外部泄漏；不可把fixture内容称真实提供方/A已泄密或证明错误。每轮失败与已完成检查、成功命令分别记录，不累加伪装全passed；无私有原始日志交付时A不能重算其指纹。最终停止自己登记进程、确认端口释放，释放报告占用。

只交两B报告：review_completed与approve_scoped/request_changes/blocked，准确task/revision/reviewed/comparison/assignment/ack、命令/真实计数/未执行/源fixture边界。提交后publish或既有授权GitHub顺序备用路径并回读，披露原子/非原子，不把发布当A接收。main不合并，不建后台轮询。51人工标签仍null，试听审阅入口留下一独立任务。

## A接收

B source `00f10a6bb04ac6dbf64927a55d90f72f94022e54` / feed `1391d53a467462fea03658dc6aa48712dc0a0f4e` 已核验并原字节归档，接收范围仅R1/R2/条件性R3与必要回归。见 [接收记录](../../verification/MUS-023-B-acceptance.json)。旧016 request_changes保留历史，本卡对应发现关闭，不代表整个导入器或模型质量批准。
