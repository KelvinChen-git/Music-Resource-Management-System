# 账号 B 最新交接

- task / owner：MUS-023-R1-B / B；assignment_revision：1；status：review_completed；verdict：approve_scoped，仅R1/R2/条件性R3及本卡必要回归。
- branch：review/MUS-023-B-demo-import-recovery；base/reviewed_sha：`ab8205827456ec6aeab3bcb289722a236e644f6b`。
- comparison_base_sha：`81566b1634aa19cb8493d2c2740c6d002a75ba4e`。
- assignment_source_sha：`ec6317cce9c178a27063fcbb8c2ef3c4953727b5`。
- ack_peer_feed_sha：`6577bed0dea8389f94215efdb50a4ad02c4e769f`；开始及结束前检查点sync exit0/双方fetched/A未变。
- 主动claim source/feed：`ca4c12430f8560d073c5a4b0c2d7a39c78d29795` / `2ceb01bc157315d10f7afb1e172546555edef94b`，先发布回读再审核。
- 报告 docs/reviews/MUS-023-B.md；仅本报告与own latest改动，实际最终SHA见handoff.source_sha。

未发现本卡新阻断；R1/R2/R3验证通过，建议A接收后关闭对应MUS-016发现。A导入016报告与原文逐字节一致，旧request_changes保留。Java树/POM/schema/锁/公共JSON未变，Vue只换helper引用/内联函数，模板样式不改；无接口/数据模型/索引改动。

相关Python17（5保护+12恢复）和项目Node22.23.3链接8均exit0/零失败；初次系统Node24链接8亦通过，两运行不相加。不是B重跑A全scripts62/前端build。最终python3 .local/b/runtime/run_mus023.py，baseline-20261022-051143-11 exit0/status passed：15组fixture，39次实际run/_run，84条断言=39锁清理+45其他，无新发现，不说成84独立HTTP场景。

R1新slot B真HTTP/SQL三故障分别通过：register未送达、真实数据库明确拒绝、成功响应丢失；同凭据状态pending→confirmed、0600/指纹/目标userid，最终每组仅1账号/上传/资源。明确拒绝用自有READ锁观察B连接35 INSERT等表元数据锁，仅取消这条语句，得到实际HTTP200/business500后保留pending并可重试，无schema/产品SQL或拒绝响应替换。成功丢响应可同次login确认，不强制首次失败。

实际legacy已建账号仅login确认；confirmed在真实改密后登录失败不register；pending真实锁定账号拒绝（SQL只置本轮新普通账号锁位）。网络故障在传输前注入；其他business500消息、nonUSER profile字段是在实际HTTP后分别替换的响应fixture，后者数据库仍USER，无提权。指纹变化/未知损坏状态/确认目标变化都保留并失败，范围不扩为整个认证系统。

R2正确SHA下size/布尔size、source域/ID/端口、license版本/query及四必需字段缺失均在本地API前拒绝并保留证明/字节，无重新造证明；旧result不冒称本次成功。完整正常cache无提供方调用/新对象，旧http同准确许可与同ID来源规范化兼容。R3新证明/公开来源canonical不含合成canary；错误来源/许可身份在下载与账号API前拒绝。node8覆盖20目录/20外部链接、Apple单一数字i、userinfo/端口/危险协议等。

提供方HTTPS/API/合成60秒440Hz MP3仅urlopen源fixture，原TLS/输入/权限保持；其余正常本地API为真实Java/MySQL。不是实际Jamendo/Apple获取或许可/法律结论，也不指认A曾泄密/证明错误。最终新库6普通账号5上传5资源含1锁定负例；无A3307/8080/5175/凭据/曲库访问、邮件、自动审核或管理员提升。

首轮baseline-20261022-051042-23 exit1/blocked，私有JAVA_HOME/bin/java链接缺失，后端未启动/业务0，MySQL与端口已清理；只恢复私有链接后新临时库再跑，不隐去失败或累加。后端启动按需编译90源文件但test.skip，无Java单测。未重演016全矩阵、全UI/player/media/Python或MUS-022质量，未测kill进程/断电/整库中断。

最终result hash08ee3f77e659f288bef920c679d12fdc287879c3dc81e04a291096c65532a0a7；verified-review-evidence hasha0a02ba546d0e7d4cebad68ea1fae8cc12fc4ab6765ae6edcdb814b86b310e85。私有原始日志/工具/音频/库未交付，A不能声称重算原始指纹；报告包含准确命令、观察与限制。

每轮自建MySQL/Spring/SQL holder停止、3308/8081释放，两报告占用释放。下一步A接收限定批准并串行更新台账/派发；main未合并。授权GitHub插件先源码后B feed顺序发布（非原子），回读确认实际交付；发布不代表A已接收，无后台轮询。
