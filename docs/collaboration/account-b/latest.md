# 账号 B 最新交接

- account: b
- task_id: MUS-014-R1-B
- assignment_revision: 1
- task_status: review_completed
- review_verdict: approve（限本卡范围）
- runtime_status: independent_native_mysql_http_faults_cross_jvm_pass
- supplement_origin: 用户明确要求修复B运行环境并补齐真库/跨JVM检查；不冒充A新派发，不重复认领已完成revision。
- owner: B；集成负责人及STATUS维护方仍为A
- branch: `test/MUS-014-B-runtime`
- supplement_base_sha: `abe9f2db05406f2c36808fbf1abb213000d35d0e`
- reviewed_sha: `7c973b5d9eac219e289623e7eb6d44eda73cb09d`
- comparison_base_sha: `d384a8fc66778ba24344f1ef19507db718872623`
- assignment_source_sha: `a433e2bd6a72a6f31cc6b608220f5dcf87bd8a54`
- ack_peer_feed_sha: `0093ae4030d35b2b7a2dbdc97f431ed95dff2e78`
- supplement_claim_source_sha / run_source_sha: `f666b9707ee7c80de1fced2554b053a9e9f441e6`
- supplement_claim_feed_sha: `8b7f70a509ead3665abd92901d870f7ba9ab86bc`
- previous_review_source_sha / feed_sha: abe9f2db05406f2c36808fbf1abb213000d35d0e / 8978cbecf36ebd5e1ec714e6e93bd86b9895f512
- delivery_sha: 本次handoff.json.source_sha
- review_report: docs/reviews/MUS-014-B.md

## 实际完成与修改文件

B已补齐原生MySQL8.0.41运行条件，并在新独立临时clone中以slot b真实执行完整baseline。运行f666b97相对固定7c973b5仅两份B报告不同，业务源码/SQL/仓库验收脚本未改；不是借用A本机B槽结果。

本轮只提交：
- docs/reviews/MUS-014-B.md：保留首轮历史并追加环境修复、原始运行数值/版本/哈希和边界。
- docs/collaboration/account-b/latest.md。

工具/适配留B忽略目录：MySQL官方Linux包和Ubuntu兼容库、Node22.23.3/npm10.9.9、现有Java17.0.20编译模块入口及Maven缓存/代理。Docker未安装，原生路线不需要。此环境禁Unix socket，bootstrap及独立迁移探针用私有loopback TCP适配；因工作目录早期清理观察异常，最终完整运行使用原生/tmp工作目录并在进程全部停止后导出证据。失败尝试保留，不改写为passed。公开API/schema/依赖锁、A文档/台账/任务卡/feed及main未改。

## B独立实际验证

命令：python3 .local/b/runtime/run_isolated.py，exit0。
run_id：baseline-20261020-143034-12；原生checkout /tmp/music-b-native-rb594p3r/checkout；完成UTC2026-10-20T05:31:30.414920+00:00（Chicago 00:31）。

- Java冷编译/测试317项，0失败/错误/跳过；前端现有依赖生产build passed。
- 新开发库11表/V001+V002；独立临时库迁移保护8项。
- 直连/代理各13功能+4安全；真实媒体144唯一组合+8附加；上传所有权65项；R1/R2清理HTTP11项。
- 真实故障注入18项；prepare5；跨新JVM resume11；含12并发上传请求及2并发合并。
- 实际Java PID852→1192，launcher708→1048；旧退出、端口释放、新就绪、checkpoint哈希/slot/checkout/先后时间一致。
- file16最终status1，分片12行/12不同索引/持久计数12；原字节校验通过，剩余故障约束0。
- state/registry/baseline.lock均不存在；全部本次进程已停，3308/8081/5174无监听。
- 两份后端日志无SQLSyntaxErrorException/BindingException/CommunicationsException/启动失败；故障注入的预期CHECK拒绝单列。
- 原始JSON与baseline内嵌结果逐份一致；数量/媒体元组/proof及最终SQL一致，报告结果不含JWT/密码字段。git diff --check和两路径审计通过。

checkpoint SHA256：2e9f4a7ab642dfac0d0cb14447e4a083dc1c2cc15bcb3f0796fec0425efca456。
合并字节SHA256：a70b3ab74f5f670f4a8d36f6fc6833a36ec77e3eec40d65e9752511d851c16d2。
本次verified-runtime.json SHA256：dc4735b97eb222d60a62031222718933c0ab7db465a55981e5f3a1ba845bbcba。
result.json：4f05db37b463d28d3c7c3485911701c60b0f5673d65dc200e2b1f86eeec19838。
java-tests.log：dbbc48a84f6f3ba039d0ff375f239e4ca15387123899702a5ec107c9ba80b805。
restart-proof.json：4d92479ab887823037d20a13cec60fd96403633e592b72d6fcf33ea8f48c65b0。
完整本机证据在忽略目录.local/b/review-evidence/MUS-014-B-runtime/；A不能直接读取此本机路径，详细数值与哈希已写入审核正文。

## 未执行检查与剩余问题

“B缺MySQL导致真库/跨JVM执行0”已由本轮补齐，首轮blocked只作为有日期的历史。Python45/进程探针9项沿用首轮实跑记录，本轮无实现更改，未无故重复。没有安装/验收Docker；不声称仓库标准入口已无需适配通用支持此Linux环境。

整库中断、commit ACK丢失、头像交错、物理垃圾回收、真实音乐检索/质量/性能和生产验收仍未执行。本轮数据仅新合成fixtures/开发schema V001+V002；模型/索引版本none，无新检索指标。

## 发布、下一步与占用释放

沿已披露GitHub插件备用路径先source后own feed发布并回读校验，非原子原生Git推送；原生Git写凭据未因此改变。最终SHA/报告哈希以handoff为准；发布不等于A已接收、集成或用户已批准最终合并。

A下次sync接收此补证后串行更新STATUS与下一任务。本轮发布后释放两报告路径的B活动占用，不修改/接管A实现文件，无main推送/合并或后台轮询。
