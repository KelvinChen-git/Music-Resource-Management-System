**Music 项目：账号 B 首次接入与基线审核**

审核日期：2026-10-19，America/Chicago。最终源码及工作区检查时间：16:15:13 -05:00。

结论：可见远端仍为原管理系统基线；协作文档尚未出现在可见远端分支，附件没有分配给 B 的开发任务。前端依赖安装、生产构建本轮通过；后端在下载 parent POM 时被 DNS 阻塞，编译、测试及业务联调均未验证。建议由 A 先发布 DOC-001 并串行认领 MUS-001，再交给 B 审核精确提交。本轮不修复业务代码、不更新 STATUS、不应用补丁。

**接入、版本与授权边界**

| 项目 | 本轮核验结果 |
|---|---|
| 仓库 | https://github.com/KelvinChen-git/Music-Resource-Management-System |
| 隔离目录 | `/workspace/scratch/8e47b726e4cb/music-account-b`，本轮新建独立 clone |
| 远端默认分支 | `main`；两次 ls-remote 均仅列出这一分支；末次也查询了 tags，未列出 tag |
| 被审源码 SHA | `b81f57c79e1cefb96c2055df4ae438aa24fb475c` |
| 本地审核位置 | detached HEAD 固定到 `origin/main`；未创建开发任务分支 |
| 工作区 | 审核前后均干净；安装、构建只产生被 ignore 的输出；无 tracked 文件差异 |
| 最新仓库指令 | 166 个 tracked 文件中没有 AGENTS.md；没有上级目录 AGENTS.md；按用户指定顺序阅读附件指令 |
| 文档版本 | 附件补丁头为 `aa720da5b32473cc072477fbc0747a11ed5407eb`；clone 中无此 commit，未尝试按该 SHA fetch |
| 文档远端状态 | 未发现 `docs/multimodal-collaboration` 分支；AGENTS.md、docs/PROJECT.md、docs/CONTRACTS.md、docs/STATUS.md 未进入当前 main；main 的 README 仍是旧版 |
| 补丁检查 | 只执行适用性检查 `git apply --check -`，exit 0；没有执行 apply/am。补丁范围确为五份 Markdown |
| 仓库权限 | 已证实 refs 读取和 clone 可用；未取得账号写权限的权威元数据，未试推，不能据此宣称有或没有 push 权限 |
| B 开发分配 | 附件 STATUS 的 MUS-001 至 MUS-007 均为 todo / unassigned；DOC-001 为 review / A；没有 B 的任务、允许路径或开发验收授权 |

上述远端观察不能证明 A 的本地目录没有未推送工作，也未检查未公开的 PR。后续交接必须重新核对 A 提供的分支和 SHA。

附件读取顺序为 AGENTS → README → PROJECT → CONTRACTS → STATUS，随后读取 APPLY.md 和补丁范围。原附件 SHA-256：`1cc1c2fe7e06a849b113e106958da608a7a153faf7d1c2662290e7e53447528d`。

**当前能力与证据等级**

| 能力 | 可以确认的内容 | 本轮限制 |
|---|---|---|
| 登录、注册、账户管理 | AuthController、UserController、JWT interceptor、UserServiceImpl 等源码存在 | 未联调数据库、SMTP、注册和登录 |
| 资源管理、分类标签、筛选、审核 | controller / service / mapper 和对应 Vue 页面存在 | 权限、筛选与 UI 描述不能视作运行验收 |
| 分片上传、续传、合并 | FileUploadController、FileChunkService、ChunkCacheService、UploadView 形成代码路径 | 未验证恢复、并发、归属和完整性；详见后文 |
| MP3 元数据 | mp3agic 接入并写资源元数据 | 时长等字段受 ID3v2 分支影响，并非每条资源都齐全 |
| 播放、下载、导出、回收站 | 文件响应、PlayerBar、回收站和清理代码存在 | 未实际上传、播放、seek、下载、恢复或删除 |
| 前端可构建性 | 本轮 npm 安装及 Vite 生产构建通过 | 不代表页面和后端已能联调 |
| Python / CLAP / discovery | 当前 tracked 源码无 Python 模块、discovery 路由、模型文件或片段索引实现 | 属于待开发范围 |
| 规模、质量、性能 | 没有发现对应实测工件 | 2,000 首、约 70,000 片段、10 秒/5 秒、120 查询、300ms、10% 提升继续标为规划、建议或算例 |

**五份文档与源码的差异**

| 文档 | 对照结果 | 对下一阶段的影响 |
|---|---|---|
| AGENTS.md | 附件的角色、串行 STATUS、任务分支及事实边界可作为本轮指令；远端未发布 | A/B 尚不能通过 clone 获得同一份协作入口。由 A 核对当前工作后发布，B 不重复应用 |
| README.md | 附件新版大体准确；远端旧 README 仍声称 20MB、标签交集、评论/点赞/收藏/播放历史及 Swagger；源码不支持将这些描述全部记为已验证 | 新协作者只读 main README 会误判能力。完整权限矩阵和部署状态仍无运行证据；附件应成为 DOC-001 的审核对象 |
| docs/PROJECT.md | 附件正确区分现状和计划；P0→P1→P2 的依赖与源码状态一致；远端缺文件 | 当前应恢复旧系统基线，再做模型 spike；没有证据支持跳过 MUS-001 开始并行检索开发 |
| docs/CONTRACTS.md | A 部分多数静态行为得到复核；B–F 的 discovery-v0 仍是建议，未发现实现或 fixtures | 冻结前补清 Long ID 的适配、202 envelope、音频元数据来源、上传归属；不能拿旧 list/file 方法直接充当新权限边界 |
| docs/STATUS.md | 附件 B-01/02/03/04/06/07 仍有效；B-05 的更正只在附件新版 README 内；无 B 开发任务 | 不创建竞争台账。本文补充问题交 A 整合进既有任务，是否拆分子任务及 owner 由 A 决定 |

附件对 schema.sql 的说明可进一步写准：该文件先定义 `users.user_id` 和 `music_categories.category_id`，随后资源外键却引用 `users.userid` 和 `music_categories.categoryid`；问题是文件内部自相矛盾，而不只是与另一份 dump 命名不同。

**需要 A 纳入后续任务的审核发现**

以下优先级表示建议处理顺序，不新增任务、不认领文件。除命令运行结果外，均为固定 SHA 下的静态发现；本轮没有执行漏洞复现或数据库测试。

1. **高：媒体入口仍绕开审核和删除可见性（复核 STATUS B-03）。**

   证据：[MusicResourceController.java:465](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/controller/MusicResourceController.java#L465) 的 `/{id}/file` 有 `@Anonymous`，只核对资源及文件存在；[MusicResourceServiceImpl.java:221](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/service/impl/MusicResourceServiceImpl.java#L221) 的查询不限制 approved 或 is_deleted；[WebMvcConfig.java:21](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/config/WebMvcConfig.java#L21) 排除 `/uploads/**` 的 JWT，且把它映射到整个 upload.path。

   影响：只新增一个受保护 discovery media 路由仍不能封住旧访问入口。文件响应还设置一年 max-age（controller:502），需一并审查缓存策略。建议在 MUS-001→005 明确音频与头像的访问边界，并用实际 HTTP 验证匿名、跨用户、pending/rejected、软删除及缓存行为。Range/206 尚未测试，不能从 Accept-Ranges 声称通过，也不能仅据 controller 未显式解析 Range 断言失败。

2. **高：上传记录没有用户归属，不能直接复用为私有参考音频任务（本轮补充）。**

   证据：[FileUpload.java:13](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/domain/FileUpload.java#L13) 没有 uploader/owner；[FileUploadController.java:87](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/controller/FileUploadController.java#L87) 创建记录不绑定用户，chunk:145、merge:209 按 fileId 操作而无归属校验；[MusicResourceServiceImpl.java:293](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/service/impl/MusicResourceServiceImpl.java#L293) 从任意已完成 fileId 取文件，并在 :388 把新资源归给当前用户。

   影响：登录验证不等于文件所有权验证；知道他人的 fileId 时，源码没有表达“只能操作自己的上传”。建议 A 在 MUS-001/005 协调归属与授权方案、跨用户测试及必要迁移；临时 query_audio 的用户隔离不能建立在旧 fileId 可信的假设上。全局文件复用若是刻意设计，也需要独立授权关联。

3. **高：历史 SQL 不能充当可重复的新库初始化（复核 B-02，补精确证据）。**

   证据：[music_db.sql:205](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/resources/db/music_db.sql#L205) 在建 recycle_bin_settings 前 INSERT，并使用随后表结构没有的 notify 字段；:211 又 DROP 表。[schema.sql:41](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/resources/db/schema.sql#L41) 引用该文件未定义的 userid/categoryid；:60 的 INT music_id 引用 BIGINT musicid；:86 还留下不完整的 REFERENCES。MusicResources:80 声明 JSON，dump:115 为 TEXT。

   影响：无法从干净 clone 可靠恢复数据库，新增音频资产表也没有可靠迁移起点。建议 MUS-001 选定统一实体/schema，先在隔离新库实际初始化并验证，再允许新迁移接入；本轮没有执行这些 SQL。

4. **高：环境与测试仍不具备后端验收证据（复核 B-01/B-04）。**

   证据：当前树没有 application 配置或样例；根 .gitignore:10 排除 application.yml；[vite.config.js:27](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/web/vite.config.js#L27) 固定 proxy target=8080。DruidConfig:16 绑定 spring.datasource.druid，UploadProperties 的 path 无默认值。后端本轮未能解析 Spring Boot parent POM。

   [pom.xml:260](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/pom.xml#L260) 只选择 `*ServiceImplTest.java`；9 个 Test 类中 7 个命名匹配，遗漏 ChunkCacheServiceTest、MusicServiceTest。这是执行选择，不意味着未选中的测试源码不参与 testCompile。pom:172–219 还混有旧 JUnit/Spring Test/Mockito/PowerMock 的显式版本，兼容性未运行确认。

   建议 MUS-001 固定可复制配置、代理与隔离参数，并在依赖可下载的环境分别记录默认和全部命名测试的实际执行数、结果以及旧系统 smoke；不把当前阻塞记为代码测试失败或通过。

5. **中：Long 主键与 Integer 旧接口不一致（本轮补充）。**

   证据：MusicResources:30 为 Long；MusicResourceService:73、实现:221、资源详情 controller:298 和文件 controller:467 使用 Integer；[MusicResourceController.java:342](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/controller/MusicResourceController.java#L342) 对 Long 调用 intValue。

   影响：契约中的十进制字符串只解决浏览器表示问题，不能防止 Java 窄化；大于 Integer 上限的 ID 会拒绝解析或被截断。建议 MUS-002/005 明确全链路 Long 解析和安全序列化，避免 discovery 经旧 Integer helper 取资源；公共接口调整需 A 协调。

6. **中：MD5 存在性查询不等于传输完整性校验（本轮补充）。**

   证据：[FileUploadController.java:183](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/controller/FileUploadController.java#L183) 保存客户端 chunkMd5 而未比对分片内容；:283 计算 mergedFileMd5，后续没有与 fileUpload.fileMd5 比较，随后 :292 将状态置为完成。/check 的用途是按已存 MD5 查询。

   影响：不能把现有上传 status 或客户端哈希当作索引内容版本的可信证据。建议 A 在基线验收中增加损坏/声明哈希不符用例；MUS-002/003 的 content_sha256 必须由受控文件实际字节计算，不复用 MD5 字段冒充。

7. **中：10GiB 前端允许值与 Integer 文件大小冲突（复核旧限制差异，补充窄化影响）。**

   证据：[UploadView.vue:259](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/web/src/views/UploadView.vue#L259) 上限为 10×1024³；FileUpload.fileSize 为 Long，MusicResources.fileSize 为 Integer；[MusicResourceServiceImpl.java:384](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/service/impl/MusicResourceServiceImpl.java#L384) 调用 intValue。旧 README 的 20MB 没有对应一致的服务端验收。

   影响：大于约 2GiB 的资源大小会溢出；单次 multipart 限制也不能代替合并总大小限制。建议 MUS-001 协调实际支持上限和服务端验证，是否改字段类型由 A 决定。discovery 临时参考音频的候选 10MiB 限制属于另一输入类型。

8. **中：现有 MP3 元数据不能保证提供片段索引所需字段（本轮补充）。**

   证据：[MusicResourceServiceImpl.java:392](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/service/impl/MusicResourceServiceImpl.java#L392) 把 bitrate/sampleRate/channels/duration 的填充全部放在 hasId3v2Tag 内；duration 用整秒，channels 用 getChannelMode。metadata body 为空时 :340 提前返回读取结果，不创建资源。

   影响：无 ID3v2 的有效 MP3 可能缺这些字段，不能直接把 additionalMetadata.duration 当作权威 duration_ms，也不能把 channel mode 当作声道数。建议 MUS-002/003 以解码结果生成时长、样本数和声道数，并覆盖无标签、非整秒等素材。

9. **中：标签任意匹配与新默认 all 不同；旧 list 也不强制 approved（复核 CONTRACTS A）。**

   证据：[MusicResourceMapper.xml:157](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/resources/mapper/MusicResourceMapper.xml#L157) 使用 tagid IN；:125 的审核过滤只有参数非空时才添加；MusicResourceController:96–105 对非管理员清空该过滤。

   影响：不能把旧列表筛选当作新 discovery 的硬过滤实现。建议在 MUS-002 冻结 all/any fixtures；MUS-005 独立强制 approved、未删除，测试多标签与跨用户状态。保留旧列表兼容性，不能为了新检索静默改变旧筛选语义。

10. **中：导出“所有资源”可能只导出第一页 20 条（本轮补充）。**

    证据：[MusicResourceController.java:621](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/controller/MusicResourceController.java#L621) 和 :727 以 page=1、size=1000 查询；实际调用 XML 分页路径 service:673；[MyBatisPlusConfig.java:25](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/music/src/main/java/com/taffy/music/config/MyBatisPlusConfig.java#L25) 设 maxLimit=20，导出没有继续翻页。

    影响：若直接借此导出 30–50 首开发语料，可能遗漏资源；运行影响尚未用数据库复现。建议 A 决定是否纳入 MUS-001 修复；MUS-002 manifest 构建必须核对数量、ID、文件存在性，不能假定旧导出完整。

11. **中：受保护试听及 202 返回尚缺与现有客户端的冻结适配（JWT 问题已在附件，202 歧义为本轮补充）。**

    证据：[web/src/api/music.js:137](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/web/src/api/music.js#L137) 使用不带 Authorization 的 fetch；[request.js:53](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/b81f57c79e1cefb96c2055df4ae438aa24fb475c/web/src/utils/request.js#L53) 只接受 body.code=200；Result.success 固定 code=200。附件建议参考上传和索引任务返回 202 envelope，但未明确 HTTP 202 时 body.code 的取值。

    影响：收紧媒体权限而不同时适配播放取流会使播放失败；若新接口使用 body.code=202，会被现有请求拦截器拒绝。建议 MUS-002 明确 HTTP/业务码组合并提供 ready/queued/failed/错误 fixtures；MUS-004/005 用携带 JWT 的 adapter 获取媒体，并验证 seek、片段终点停止、Blob URL 清理。不要全局修改旧 envelope 语义而不协调。

12. **生成模型或索引前需补 ignore（复核 STATUS B-07）。**

    根 .gitignore 只覆盖前端依赖/输出、后端 target 和 application.yml、IDE 与日志；没有规划中的 Python 缓存、模型权重、音频语料和索引工件规则。建议 MUS-001 先冻结并加入实际使用路径的 ignore，再生成工件；本轮未下载模型、音频或生成索引。

**本轮执行及未执行检查**

环境：Linux，OpenJDK 17.0.20，Node v24.19.0，npm 11.9.0，Git 2.51.1；未找到系统 mvn 或 mysql 客户端。Maven wrapper 指向 3.9.9，mvnw 的 git mode 为 100644，使用 `sh ./mvnw`。

| 位置 | 实际命令 / 检查 | 结果 |
|---|---|---|
| 独立 clone / 远端 | `git ls-remote --symref ... HEAD 'refs/heads/*'`；末次加 `'refs/tags/*'` | exit 0；HEAD/main 均为上述完整 SHA；无可见文档分支 |
| 根目录 | `git status --short --branch`、`git rev-parse HEAD`、`git branch -a -vv`、`git log -5 --oneline` | HEAD 固定且干净；仅 main/origin/main；最新历史为 b81f57c 与 5acdc68 |
| 根目录 | `git diff --check`、`git diff --stat` | exit 0，无 tracked 差异 |
| 根目录 | 将 ZIP 中补丁字节通过 stdin 送入 `git apply --check -` | exit 0；仅检查适用性，没有应用 |
| 根目录 | `git cat-file -e 'aa720da5b32473cc072477fbc0747a11ed5407eb^{commit}'` | 非零；本地对象不存在，不等于远端保证不可获取；未进一步按 SHA fetch |
| web/ | `npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=0 --fetch-timeout=30000` | exit 0；added 244 packages in 10s；保留 lockfile |
| web/ | `npm run build` | exit 0；Vite 6.2.4；1668 modules；built in 4.71s；部分 chunk >500kB 的非阻塞警告 |
| music/ | `sh ./mvnw -B -ntp test` | exit 1 / blocked；Non-resolvable parent POM，repo.maven.apache.org: Temporary failure in name resolution；未进入编译/testCompile/测试 |
| 源码静态检查 | tracked 文件、路由/权限、SQL、实体、mapper、元数据、上传、前端 adapter、pom/test 命名 | 完成上述范围核对；没有新增测试或业务改动 |

未执行：`-Dtest='*Test'`（同一 parent POM 阻塞，不重复执行相同失败路径）、MySQL 初始化、后端启动、邮件、注册/登录、真实分片/续传、并发/损坏文件、权限与删除后的媒体访问、Range/206、导出超过 20 条的复现、浏览器业务联调、模型或音频实验、检索/质量/性能评测、push/PR/合并。

检查通过的证据只覆盖对应命令；Maven 的环境阻塞不证明其后阶段能通过，也不证明测试代码失败。新增问题保持静态发现状态，待 A 分配任务后验证。

**依赖与可交给 A 的下一步**

1. A 先核对自己的工作区和未推送提交，串行发布/整合 DOC-001；附件补丁本轮仅检查可适用，不能代替版本协调。
2. A 在最新 STATUS 认领 MUS-001，给出精确 branch/base_sha、允许路径、配置/schema/权限/测试范围及验收；B 可审核其精确提交，避免重复修复。
3. MUS-001 取得可复现旧流程证据后，MUS-002 冻结准确 checkpoint、预处理、依赖与设备、素材/许可 manifest、查询和媒体接口、版本字段及 fixtures。
4. MUS-003/004 在 MUS-002 冻结后才适合并行。本轮不提前选 CLAP checkpoint、Python 框架、数据库结构或索引基础设施。

**固定交接**

```text
任务 / owner：首次启动只读接入与基线审核 / B（用户直接指定）；无已分配的 MUS 开发任务。
分支 / 基础 SHA / 交付 SHA：
  远端 main；本地 detached HEAD。
  基础及被审 SHA = b81f57c79e1cefb96c2055df4ae438aa24fb475c。
  交付 SHA = 无；本轮没有仓库改动或新 commit。
代码位置或 PR：独立 clone /workspace/scratch/8e47b726e4cb/music-account-b；无 PR。
修改文件与实际完成内容：仓库修改文件为 0；产出本审核报告，完成附件/远端/源码对照及基线验证。
接口 / schema / 配置变更：无；未应用附件补丁，未更新 STATUS 或依赖锁。
执行命令与结果：远端读取、clone、补丁适用性检查、diff 检查通过；npm ci 和 build 通过；Maven parent POM DNS 阻塞。
未执行检查：数据库、后端编译/测试/启动和业务联调、全量命名测试、权限/Range 等运行复现、模型/索引/评测；见报告明细。
未完成问题：附件协作文档未进入可见远端；无 B 开发任务；既有阻塞未修；本轮补充发现待 A 归入现有任务。
数据 / 模型 / 索引版本与获取：均未建立；未导入语料、下载模型或生成索引；附件 SHA-256 见报告。
下一步：A 发布 DOC-001并在 STATUS 串行分配 MUS-001；B 按指定分支/SHA及边界审核或接手明确子任务。
推送状态：未创建提交、未推送、未试推；读取权限已确认，写入权限未确认；未合并 main。
文件占用释放：无文件写入占用，审核后已释放；B 未接任集成负责人，A 继续负责集成与 STATUS。
```

本报告是提交给 A 的一次审核交付，不替代仓库中的 STATUS；最终任务状态和修复分配由当前集成负责人串行维护。
