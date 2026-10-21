# MUS-016-R1-B：演示导入器与公开目录独立审核

- task_id / assignment_revision：MUS-016-R1-B / 1；owner B；review_completed/request_changes已接收（2026-10-21）。
- reviewed_sha `69a3965e88d37d71a0067f263d207f2cb62fe668`：当前Sonora/用户写入修复后的完整源码快照。
- original_implementation_sha `3092ae273e4a448246b8272fd20f3cd7de37dc91`；comparison_base_sha `dbb631218b8ee7c87823ce594494b908b2849e32`：仅用于定位原MUS-016新增范围，不审此后所有业务改动。
- 分支 `review/MUS-016-B-demo-import`；只交 `docs/reviews/MUS-016-B.md` 与 `docs/collaboration/account-b/latest.md`。
- assignment_source_sha取发布本卡的A handoff.source_sha，与reviewed_sha区分。先主动claimed，包含task/revision/准确输入/实际ack_peer_feed_sha；同任务历史完成不重复领取。

MUS-021-R1-B限定批准已由A接收，E1/E2在本卡范围关闭；不重复017/019/020/021，不改产品UI或main。现在只处理一直单列的MUS-016首次独立审核，不暗示旧导入已有B批准。

## 输入和限定路径

重点只读：scripts/import_demo_music.py、scripts/test_demo_music_import.py、web/public/demo-catalog.json、web/public/artist-references.json、web/src/views/DemoCatalogView.vue；这五文件在reviewed_sha与原3092ae2逐字节一致。辅助读取baseline.validate/dev.read_env、既有上传/metadata/list/media接口和当前路由守卫、Sonora keyword消费片段，避免机械沿用旧/music页面假设；不因此扩为后端或整站重审。

证据：docs/verification/MUS-016.md/results.json、README演示段。A历史20首导入、重复运行、完整SHA/Range和浏览器观测是A运行事实，不充当B新运行。现有两个公开JSON是元数据，不是可跨clone复制的音频/数据库；A现有曲库/凭据不可访问。不要重新执行A slot或索取其Client ID。

## 审核与最小验证

1. 来源声明/过滤：显式audiodownload_allowed=true、准确CC BY版本与来源域/协议、ID/时长/唯一歌曲与作者规则、最大音频/下载最终来源、完整字节/Range及公开manifest字段。核对许可证据属于下载时还是重跑实时查询；不把URL/布尔值或合成音频测试当成真实提供方许可有效性的法律/生产结论。
2. 隔离与秘密：baseline/dev slot校验、O_EXCL锁拒绝、锁生命周期/异常退出、私有凭据/原始音频/下载证明/台账权限与ignore、TLS不降级；公开JSON/输出/异常中是否出现Client ID/JWT/密码/可下载完整音乐URL。外部歌手区仅资料/官方链接，不应下载或生成其音频/试听/封面。必要时用合成canary秘密核验，不读取A真实文件。
3. 幂等与失败恢复：实际调用run/_run入口覆盖首次导入、完整缓存重跑不下载、部分缓存/下载证明异常、账号注册前后错误或响应不确定、上传成功/台账写入前后与metadata成功/重查阶段中断。核对是否重复账号/上传/资源、资源匹配是否与正确音频绑定、歧义/无结果时是否保留现场并失败。分别记录正常重跑与故障恢复，不能用“已有20行”推断所有故障幂等。
4. 在自身临时clone/独立slot B/空库/上传目录用少量合成MP3/账号作本地真实HTTP补验。无个人Client ID或不宜访问真实来源时，用私有provider transport fixture在urlopen边界返回明确合成的Jamendo结构与合成音频，保留产品eligible/validate/TLS设置/URL断言/本地API逻辑不变；标明来源响应mock、哪些URL没真实联网、哪些本地请求是真HTTP。不得把替身源结果称为真实Jamendo获取/许可验证。不要修改产品或断言以让失败变通过；无法执行的分支精确blocked。
5. 目录/当前导航：只做必要回归，核对公开元数据结构/来源与许可安全链接、owner提示、外部资料不可播放、未登录路由保护、普通owner关键词查找走当前Sonora。公开页面无法独立证明本地曲库可见性；若需浏览器用自己的合成fixture，不使用A演示账号。避免重跑整套019/020浏览器。
6. 先运行相关保护用例，例如仓库根目录 `python3 -m unittest discover -s scripts -p test_demo_music_import.py`；它当前只有5项，历史50是当时完整Python回归，别把5说成50。按需要补私有故障harness/HTTP运行，报告不改源码。未变的Java/前端安装/全量构建无需机械重复；若未新执行要明确，不引用A通过当B通过。

## 运行与交付边界

仅使用B自己的新临时clone/库/端口/下载目录；检查配置后再生成数据。模拟源/公开输出只能落一次性临时目录或被ignore的工件位置，不改审核checkout中的已跟踪公共JSON，不提交合成catalog/音频/账号/模型。run会生成catalog，必要时让一次性副本承接输出，报告说明适配；不改生产代码/校验/权限。无A8080/5175/3307、A凭据/缓存/曲库读写，无提权既有用户、自动批准音乐、迁移旧库或邮件发送。

任务允许在自己的空库创建/清理合成普通账号与上传；需要管理员的场景本卡没有默认要求。保留失败原文、每轮退出码/已完成数量与修正的私有探针，旧结果/多轮不相加，provider mock与实际HTTP/SQL分开。原始日志/适配器未交付时A不能重算，交报告可核对的source/hash声明。最终清理自己登记的进程并报告端口释放，不清理他人的服务。

仅两报告路径，写review_completed与approve_scoped/request_changes/blocked、准确基线/任务/assignment/ack、命令/观测/未执行及限制，释放占用。新发现以实证/静态推断区分，建议最小修复交A，不直接写实现/STATUS/任务卡。发布源码与feed后回读，说明原子或已授权顺序备用路径；不把发布说成A已接收。main不合并，无后台轮询/唤醒。


## A接收注记（2026-10-21；原任务输入保留）

B feede1da44f8/source0c5efad9原字节报告及派发已核验，request_changes接收；[报告](../../reviews/MUS-016-B.md) / [接收JSON](../../verification/MUS-016-B-receipt.json)。R1/R2与条件性R3由A MUS-023修复，不把正常场景通过外推全部导入批准。上文assigned/先claimed为原约定，勿重复领取；等待固定入口023准确新卡，不直接改A实现或main。
