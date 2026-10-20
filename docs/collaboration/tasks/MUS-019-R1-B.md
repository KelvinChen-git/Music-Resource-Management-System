# MUS-019-R1-B：Sonora 应用副本独立复核

- task_id / revision：MUS-019-R1-B / 1；owner B；assigned未认领。
- reviewed_sha `f68b7fbba63ea58ad10dfe326d0197d1cc6b15ce`；comparison_base_sha `f3b0da1e97113d28c81aa49be61c5cbcc49eebce`。
- 分支 `review/MUS-019-B-sonora-app`；只允许写 `docs/reviews/MUS-019-B.md` 和 `docs/collaboration/account-b/latest.md`。

用户已经确认MUS-018设计并授权建立新版应用副本作为后续开发基线。新A工作目录Music-Sonora，原目录/旧web保持。B的017报告已经发布，A本轮已读latest；正式报告接收及E1/E2后端协调仍单列，不让B重复017，也不声称该批准覆盖本UI。

先按当前A handoff.source_sha读取任务入口，再固定上述reviewed_sha检查代码；首次主动发布claimed，写明revision、实际assignment_source_sha/ack_peer_feed_sha，不由A代认领。

## 范围与检查

1. 新App壳与路由：新/music及favorites/recent/artists需鉴权；旧完整管理在/manage/music，上传/分类/标签/回收站/个人资料和管理员权限不能失去入口或放宽。检查legacy musicStore监听移至方法定义后且只处理/manage/music，带keyword直达不会声明前调用，也不对新曲库/登录发起旧后台列表请求。
2. 所有播放，包括旧管理页注入调用，必须通过createMusicUrl/fetchMedia JWT边界；无裸URL或外域泄露Bearer，Blob替换/快切旧结果/退出或换账号正确清理。收藏/历史按账号ID命名且明确本浏览器，重新进入按ID请求详情，拒绝资源不从缓存元数据展示。
3. 核对分页20、展开8、风格/排序仅已加载提示、关键字搜索、错误/空结果、详情来源/许可链接、歌手资料只跳官方页、SVG封面转义、防长标题溢出。新播放器路由切换保持播放，退出清理，不伪造播放状态。
4. 在准确SHA独立clone执行 `npm ci`、`npm run build`（web目录），仓库根执行 `node web/scripts/verify-sonora-player.mjs`（5组）与 `node --test web/src/utils/media.test.js`（6项）；使用Node22及现有锁，不修断言或升级依赖。没有必要重复无变化的Java/Python全套。
5. 如有浏览器/隔离后端，使用自己的合成账号/库补登录、真实播放/换页、收藏/退出换号、上传及管理入口、1440/390布局。没有环境则明确blocked，静态审查或mock检查不当成真实音频/权限验收。不得请求/写入A现有曲库、搬运A凭据或操作A服务。

## A 已知证据与边界

A生产build、5组播放器边界检查、6media helper检查通过；普通演示20首、What Is Love212.022653秒实际播放到7.293254秒、Grupo86.0122秒真实播放与切页保持、搜索/空结果/收藏/历史/详情/歌手/旧管理/上传页、退出清理及重新登录收藏、桌面/手机均有本机证据。见docs/verification/MUS-019.md及截图；不把A截图当B独立运行。

npm ci保留原锁的59项审计提示，bundle已有>500kB告警，未擅自扩为依赖升级。A旧管理store曾记录一条退出附近列表错误，已修路由监听边界；测试server首轮关闭时曾有扫描诊断，禁用测试依赖发现后再跑通过。未验证完整新增上传/管理写入/所有管理员浏览器场景、跨设备收藏、生产部署或检索能力。当前A后端运行仍MUS-014，不把源码MUS-017当已运行。

完成回传review_completed及结论、真实命令/数量/阻塞、未跑项与证据；只交两B报告，不直接改A实现/总台账/任务卡，不合并main。完成后publish --account b，披露实际发布方式。固定feed负责读写交换，不会后台唤醒B。
