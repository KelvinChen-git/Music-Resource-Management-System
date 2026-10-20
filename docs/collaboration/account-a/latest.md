# 账号 A 最新交接

## 当前：MUS-019 Sonora 应用开发副本

A；2026-10-20 America/Chicago；branch `feat/MUS-019-sonora-app`；base `f3b0da1e97113d28c81aa49be61c5cbcc49eebce`；review / 已接入可用，待用户体验。

用户已批准应用MUS-018设计并另存开发副本。后续前端工作目录 **Music-Sonora**，原 Music-Resource-Management-System / design/MUS-018-ui-preview 保留，旧web未改。新5175的构建版本代理现有A8080，后端运行仍MUS-014，不启动新库或Java进程。

新Vue外壳/真实曲库/收藏历史/歌手资料/鉴权播放器，旧资源管理 `/manage/music`、上传与其他页面保留。生产build、5组播放器竞态/换号/错误检查、6媒体helper检查、diff检查通过；真实登录20首、搜索/筛选/收藏/详情/历史/歌手/上传页/旧管理播放/跨页播放/退出清理/重新登录收藏保持，以及1440/390px布局已验收。完整命令与限制见docs/verification/MUS-019.md。无Java/Python/API/schema/锁文件变化，未跑完整上传写入/管理员写操作；收藏历史仅分账号浏览器本地。

ack_peer_feed_sha `bb64dcafb37b021e468b207560c8ae98c28b87a3`，B source `082d243161c5774a96d242a473b17c483a77cc4e`：已读取latest的MUS-017有限定批准及E1/E2发现；完整报告正式接收留到后续后端轮次，不冒充原始证据重算。此次用户要求UI接入，不另派后端新卡。新前端复核卡MUS-019-R1-B/revision1已放入固定入口，reviewed_sha `f68b7fbba63ea58ad10dfe326d0197d1cc6b15ce`，assigned未认领；B无需重复旧017任务。main未合并。

## 上一轮交接（保留）


## 当前：MUS-018 独立 UI 预览

A；2026-10-20 UTC；branch `design/MUS-018-ui-preview`；base `d34f282a499b3e93c94f90c83c38d35dcb21ca3a`；review / 等用户确认设计。仅新增 `design-previews/sonora/` 与更新 A 交接/台账。

自包含 HTML、桌面/手机截图和 README；深色唱片风格，可交互曲库/收藏/歌手/详情/队列/导入弹窗；播放为模拟状态。桌面、窄窗口和手机已检查，浏览器无 JS error。未改 web/、API、数据库或在跑服务。本轮 sync 读取 B feed `0748515936eb5cb41446279acc29e52725781c1e` / source `067f6c3d6517da0852a10d6396fdc23161102525`：B 已主动 claimed MUS-017-R1-B，尚未完成验证；无新设计审核任务，也未冒充 B 批准。脚本 node --check 与 git diff --check 通过。用户确认后才安排接入现有前端。

## 上一轮后端交接（保留）

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
