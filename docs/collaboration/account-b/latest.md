# 账号 B 最新交接

- account: b
- task_id: MUS-015-R1-B
- assignment_revision: 1
- task_status: review_completed
- review_verdict: approve（限同值头像校验增量及现有空字符串清空；C1既有NULL语义单列）
- owner: B；集成负责人及STATUS维护方仍为A
- branch: `review/MUS-015-B-avatar-revalidation`
- base_sha / reviewed_sha: `d9a2a15791da0db4374c5de093a752a5aa202a25`
- comparison_base_sha: `feb935ad5c7eb4eb8a11065f3d5c18ed2a93dab1`
- assignment_source_sha: `dbb631218b8ee7c87823ce594494b908b2849e32`
- ack_peer_feed_sha: `c618062350efb32a30cb7065694945fab02dd39c`
- claim_source_sha / run_source_sha: `80e65a6e493f12b3355689cb04cd0016fc5fd54c`
- claim_feed_sha: `e940ba956c04bc620511e63a39bd793bbf0b30ff`
- delivery_sha: 本次handoff.json.source_sha
- review_report: docs/reviews/MUS-015-B.md

## 完成内容与修改文件

先从固定入口主动领取本卡revision1后独立复核。前MUS-014已由A接收，不重开旧任务。本次未发现同值头像两处条件修复新增阻断问题；approve不等于所有头像接口语义或main合并已验收。

仅新增docs/reviews/MUS-015-B.md并更新own latest；业务/API/schema/依赖锁、A STATUS/任务卡/feed未改。模型/索引版本none；数据为本次全新V001/V002开发库/合成PNG与账号，无检索指标。

## B实际独立执行

- 保持旧业务feb935a，仅把被审核版本的测试文件放入独立临时clone，执行Maven UploadOwnershipHttpTest：52 tests / 3预期failures / 0 errors/skipped，exit1，三新增回归确实命中旧条件。
- 新代码完整冷编译Java320 / 0失败错误跳过，BUILD SUCCESS；source80e65a6相对reviewed仅B领取latest，无实现变化。
- 真HTTP/MySQL普通与旧快照探针完成16项：两入口合法同值/新头像4，名称与安全列1，删除/未完成/NULL owner/他人同值拒绝8，管理员空字符串清空1，等待后删除旧头像拒绝2。
- 上述16项所在命令后续因B等待采样断言exit1，result.status=blocked；只记录其completed_checks，不冒称整次命令passed。
- 独立锁专项2项exit0：profile/管理员在等待用户写入时，同事务仍持有file_upload主键X锁；performance_schema中事务1451/1457均为users主键WAITING、上传主键GRANTED。随后并发DELETE均409，引用/未删除状态正确。
- 以上为不同运行中18个完成业务检查，不伪装单次18项全通过。受控旧快照状态切换用独立fixture SQL事务，不冒充三正常HTTP客户端流程；DELETE采样未出现文件锁等待，实际持锁结论来自performance_schema。
- 所有本次拥有的SQL客户端/服务均关闭，3308/8081无监听。py/frontend无改动，未重复已有测试/build。

## C1：既有NULL清空差异，交A登记

管理员avatar:null返回HTTP200/业务200和data.avatar=null，但真库仍是旧头像；avatar:""确实清空。对应UserServiceImpl.setAvatar/updateById路径与字段映射在base已存在，并非本次删除相等性分支引入。

此为P2既有兼容性观察（原始探针名R1），不掩盖为通过项，也不因此扩大B写范围。建议A明确缺字段/null/空字符串语义并补持久化断言；若null表示保持，应修正响应回显/文档，若要null清空则需识别字段是否提交并局部更新，不能全局开放NULL覆盖。审核批准不包含未明确的NULL清空契约。

## 证据与边界

沿用B私有MySQL8.0.41/Linux TCP、Java17.0.20编译入口及Maven缓存/运行时代理；每次用新原生/tmp checkout/slot b，未连接A现有服务，未改业务或SQL校验。B探针的BIT解码、无效诊断变量和trx_query等待采样问题保留为探针失败，不算产品缺陷。

本机忽略证据.local/b/review-evidence/MUS-015-R1-B/：
- 旧负回归日志SHA256：00ff7c33b5c8d2c1bbd96b2c2274beab7ff06b14785bd38f8ff15c5b0591c1da。
- Java320日志：386b4c73f78bd69c719c536ab38db0cfa0741ad1d917b5aa71c65268595a05fc。
- 16检查/C1结果：325714eb87dc502b2fe1eade363494b2d5c1c5ad3e72434bfac99ef627cec2c3。
- 锁专项结果：136ae8490e8a2a12233e94aeaeed7554b2642b1ad0216ff72bd69b6412da05d8。
- verified-review-evidence.json：a3dc2f8a37157cf0846854ce38cd9e07fdb6bf2e7472c0e0b09c54240a17f763。

原始日志只在B本机，A不能直接读取；准确数值/时序/哈希已提交正文，无JWT/密码入Git。尚未执行三HTTP参与者完整竞争、整库中断/commit ACK丢失、压力、物理GC、公开检索或生产验收；不将受控锁证据外推到全部管理员安全状态并发。

## 发布与下一步

git diff --check与仅两报告路径检查通过。沿已披露GitHub插件备用顺序路径发布source再own feed并回读；非原子原生Git推送，最终SHA/哈希以handoff为准。发布不代表A已接收或用户已批准最终合并。

A下次sync接收本次准确范围的approve、独立实跑与C1后串行更新STATUS/后续卡片。发布后释放两报告路径B活动占用，不接管A源码；无main推送/合并或后台轮询。
