# MUS-025-R1-B：试听与判断工作区增量复核

- task_id / assignment_revision：MUS-025-R1-B / 1；owner B；assigned未认领。
- reviewed_sha `cdc2fc5c00dbc4c2889068023d9d37ce8744a532`；comparison_base_sha `133fecbcda96585a09d6e0cf67af608c768c9151`。初版1fbaac8仅说明验证历史，审核对象是cdc2fc5。
- 分支`review/MUS-025-B-listening-review`；仅写`docs/reviews/MUS-025-B.md`与`docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡A handoff.source_sha；先claimed并回传准确task/revision/reviewed/comparison/assignment/ack，再审。MUS-024限定批准已接收，勿重复领取。

先读CONTRACTS E2、verification/MUS-025.md/results.json及本卡。范围仅新Vue视图、reviewPack/reviewAudio/helper tests、router一条登录路由和App一项入口。没有新搜索API/Java/schema/锁/公共JSON改动。A真实8查询/51空标签与20曲目不是B可访问共享环境。

## 验收

1. 固定Node22运行`node --test web/src/utils/reviewPack.test.js web/src/utils/reviewAudio.test.js web/src/utils/media.test.js`，A为21项（8+7+6，不加先前15）；运行现有lockfile的build，不升级依赖。源码审查包大小/重复键/整数/owner/同曲目内容与dataset指纹、未知字段、null/0、人工区间/代号/UTC时间、草稿同账号同包与显式恢复。浏览器只验结构/自洽，最终仍需原run CLI；不是来源认证。
2. 自己独立clone/端口/库，在忽略目录建立合成run、JSON和音频；可复用私有B运行适配，但不改产品或解除权限。自己的普通账号上传/资源（不要A真实曲库），recorded hash/byte/duration与合成MP3对应，MUS-024工具可生成E1包；model/run字段明确合成，无需CLAP编码或模型下载。实际调用浏览器新入口，不把fake audio或Node21当浏览器/HTTP补证。
3. 登录保护、对应owner导入/错owner拒绝且保留旧内容；真实JWT媒体能播放，模型片段seek/终点停止；错误内容SHA（重新计算包自洽指纹）必须拒绝、无audio src且取点disabled。每次重播新GET，无JWT URL/pay；401/403/404/取消/切候选/离页/退出应回收，迟到响应不复活。可在自己的隔离合成账号/资源做最小撤权重播检查，不扩大完整旧媒体矩阵。已交付字节不能追溯撤销。
4. 合成包中明确0分与null区分，评分需匿名测试代号；人工区间不来自模型自动填充，越界/重叠输入拒绝（UI只编辑一个区间，导入可保留多段）。评分/区间/清除、自动草稿、刷新重导入先保留文件而非静默草稿，明确恢复、部分导出；浏览器导出对自建固定run CLI通过。身份/时间是用户输入/操作时间，不能称真实人评。
5. 同包草稿按账号隔离，退出清内存/音频，原草稿可在同账号重导入时明确恢复；若测第二合成账号不能读前账号草稿。检查全局播放器与审阅互斥且旧队列不丢；必要存储不可写故障用自己的受控环境，不移除校验。390手机长标题/1440桌面、按钮可达/无横溢，warn/error与失败观察保留。
6. 不重复024完整83CLI、导入恢复、旧管理写操作/完整上传或CLAP/质量测试。A原51数据、原始日志/截图只是A证据，B未收到不可说复算；额外合成数量不算真实查询。条件不足明确blocked及执行0/已完成检查，不能代填真人判断或索取A凭据/音频。

不访问A8080/5175/3307、私有run/账号/缓存/曲库；不发邮件、不改原数据/权限、不复制真实媒体到web/public，不新增检索服务/API或合并main。只运行自己登记的隔离服务，结束停止并核对端口释放。生成包/标注/工具/截图仅自己的.local，报告只两文件。

最终review_completed及approve_scoped/request_changes/blocked、准确SHA/命令/分组计数/每次失败/fixture与真实HTTP界限、未测/私有证据边界、占用释放。提交后publish并回读；顺序备用发布披露非原子，发布不等于A接收；无后台轮询。
