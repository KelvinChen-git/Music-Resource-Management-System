# 接口、数据与音频契约

历史源码基线：`b81f57c79e1cefb96c2055df4ae438aa24fb475c`，2026-10-19 静态核对；MUS-001 的运行及映射修复见下文与 verification/MUS-001.md。

**A 部分为已有代码行为；B–F 为待实现的 discovery-v0 建议契约。** 新接口、表和处理规则尚不存在。MUS-002 必须结合模型 spike 冻结版本，并建立请求 / 响应 fixtures；本文件不能替代可执行的 OpenAPI 或契约测试。冻结前不让两个任务自行假设字段。

## A. 已有接口与实体

### A1. 路径、鉴权和返回

前端 Axios baseURL 是 `/api`；开发代理读取 `VITE_PROXY_TARGET`（默认 `http://127.0.0.1:8080`），不 rewrite。MUS-001 的 `application-local.yml` 在显式启用 local profile 后提供 `/api` 和可配置端口；未启用该 profile 的部署仍需自己的配置。

一般 JSON 返回来自 `common/Result.java`：

```json
{"code": 200, "message": "success", "data": null}
```

Axios 成功拦截器返回整个 envelope，调用方通过 `res.data` 取业务数据。二进制响应例外：配置 `responseType: 'blob'` 时直接返回 Blob。历史接口有 HTTP 200 + 业务错误码的情况；不要据 HTTP 状态独自判断成功。JWT 头为 `Authorization: Bearer <token>`，登录返回 `data.token`。

| 方法与浏览器路径（context path 为 `/api` 时） | 代码确认的用途 |
|---|---|
| `POST /api/auth/register`、`POST /api/auth/login` | 注册、登录 |
| `GET /api/auth/profile` | 当前用户 |
| `GET /api/music-resources/list` | 普通资源列表 |
| `GET /api/music-resources/list-with-deleted` | 包含回收站选项的列表 |
| `GET /api/music-resources/{id}`、`PUT`、`DELETE` | 详情、修改、软删除 |
| `POST /api/music-resources/metadata?fileId=...` | 上传完成后解析 / 保存 MP3 元数据，可接收可选 metadata body |
| `POST /api/music-resources/{id}/approve`、`/reject` | 审核 |
| `GET /api/music-resources/{id}/file` | 文件响应；`pay=1` 或 `true` 增加播放计数，非支付接口 |
| `GET /api/music-resources/export-music-data`、`/export-music-files` | JSON 元数据 / ZIP 文件导出 |
| `POST /api/file/create` | 创建上传记录；body：fileName、fileSize、fileMd5、chunkCount |
| `GET /api/file/check?fileMd5=...` | 文件哈希匹配 / 续传检查 |
| `POST /api/file/chunk` | multipart：fileId、chunkIndex、chunk、chunkMd5 |
| `POST /api/file/merge?fileId=...` | 合并；data 内有 filePath |
| `GET /api/file/missing-chunks?fileId=...` | 缺失分片 |
| `GET /api/file/status/{fileId}` | 上传状态 |

列表参数：`title`、`artist`、`album`、`categoryId`、`username`、`email`、`approvalStatus`、`onlyMine`（默认 true）、`current`（1-based，默认 1）、`pageSize`（默认 10）、`orderBy`（默认 uploadTime）、`orderType`（默认 desc）、重复 `tagIds`、`startDate`、`endDate`、`keyword`。返回 MyBatis Plus Page，主要字段 `records/current/size/total`。分页插件当前上限 20。

源码差异必须保留为待修问题：

- 普通列表对非管理员清除 username / email / approvalStatus 筛选；管理员与普通用户的 onlyMine 行为也不同。不能给新搜索机械复用未经测试的可见性条件。
- XML 的 tagIds 条件使用 `IN`：任意标签匹配，不是所有标签交集。日期 endDate 通过加一天包含完整结束日。
- 历史文件接口有 `@Anonymous`、静态 uploads 排除 JWT，MUS-001 / 010 实跑确认匿名 200。MUS-011 已改为 A4 的授权 / 缓存规则，并保留授权后的 Resource Range；2026-10-19 两个本机隔离环境已重启并各通过 144 项真实数据库 / HTTP 矩阵，直连 / 代理匿名入口均为 401；独立 B 账号审核另列。
- MUS-011 的 createMusicUrl / 列表与文件下载通过 fetchMedia 显式携带 JWT 获取 Blob；页面地址导航不作为私有音频下载入口。
- UploadView 检查 10GiB，分片 5MiB；原 README 写 20MB。服务端总文件限制未锁定，还受本地 multipart 配置影响。

MUS-001 列表查询改为显式 JSON resultMap，API smoke 确认 additionalMetadata 中的 duration / sampleRate 可读。VITE_API_BASE_URL 只作为旧头像 helper 的非空开关；helper 实际仍返回相对 `/api/uploads/...`，它不控制 Axios 或代理。

### A2. 现有数据

| 意义 | 现有字段 / 表 | 新功能注意 |
|---|---|---|
| 音乐主键 | `music_resources.musicid` / Java Long | 新 API 的 track_id 映射它，不另造无关联歌曲 ID |
| 分类 / 用户 | categoryid / userid | 新 API 使用字符串 ID，边界处显式转换 |
| 文件路径 | file_path / filePath，相对 upload.path | 不能直接暴露绝对文件系统路径 |
| 审核 | approval_status，写入 pending / approved / rejected | 保留小写约定，不以测试里的大写样例覆盖实际契约 |
| 删除 | is_deleted / deleted_at 等 | 索引过滤后仍需源库核验 |
| 扩展元数据 | additional_metadata / additionalMetadata | 现有 MP3 解析写入 duration（秒）、sampleRate 等；不是标准化向量存储字段 |
| 上传主键 | file_upload.id | 不是 musicid；metadata 流程产生资源，不能将 fileId 直接当 track_id |
| 文件分片 | file_chunk，(file_id, chunk_index) 唯一索引 | 文件传输块与用于检索的音频时间片段不同 |
| 标签 | music_tags + music_resource_tags(musicid, tagid) | 新 tag_match 需显式定义 |

MUS-001 的空库入口是 `db/baseline/V001__development.sql`：11 表，additional_metadata 为 JSON，关联表为 musicid / tagid；audit_logs 按 JPA 采用 audit_id / admin_id / music_id。历史 SQL 不再作为初始化命令；这不是已有数据库的迁移方案。JPA 与 MyBatis 的分类 ID Java 类型仍不同（Integer / Long），未启用 Hibernate 自动 DDL / validate，不能从 smoke 推断所有 JPA 仓储路径均通过。

MD5 当前用于文件传输 / 秒传判断，不能证明音频内容相同，也不能代替新内容版本的 SHA-256。

### A3. MUS-009 上传完整性契约（本任务实现 / 验证）

保留 `/file/create|chunk|merge|missing-chunks|status` 和旧 HTTP 200 + code/message/data envelope；失败以 code 非 200 表示。fileMd5 / chunkMd5 要求 32 位十六进制，大小必须为正，索引在 [0, chunkCount)；不强制客户端块大小恰好等于服务端配置。

- 分片按保存后的实际字节校验 MD5。只在文件写入完成、分片与计数事务提交后返回成功；数据库是唯一续传依据，取消缓存延迟批量写入。同 fileId 的上传 / 合并在数据库事务中锁上传行串行执行。
- 同索引、同内容的重试不重复插入 / 累加；不同内容返回冲突错误，不覆盖已接收分片。已接收分片丢失或损坏时允许原内容重传修复。完成记录拒绝新分片，重复 merge 返回原路径。
- 合并只接收完整且连续的成功分片，逐片核验磁盘大小 / MD5，最终核验总大小 / fileMd5，再提交完成路径和 status=1。校验失败保持未完成状态（0），保留分片供重试，不返回可用路径。
- 临时分片只在完成事务提交后清理；失败目标删除。进程在文件落盘与数据库提交之间崩溃可能留下未引用文件，本轮不提供全面垃圾回收或跨文件系统 / 数据库的原子事务。file/status 的进度来自成功分片记录。
- 消费方仍为现有 UploadView / smoke；无需新增字段或 schema。媒体可见性和上传归属仍属独立未解决事项。

### A4. MUS-011 媒体授权与缓存

资源 `/music-resources/{id}/file` 与原始 `/file/download/{fileId}` 必须有有效 JWT，且当前数据库账号存在并未锁定。每次 GET / HEAD / Range 读取源记录，权限一致：

| 状态 | 普通其他用户 | 上传者 | 管理员 |
|---|---|---|---|
| approved 且未删除 | 允许 | 允许 | 允许 |
| pending 且未删除 | 404 | 允许预览 | 允许审核预览 |
| rejected 且未删除 | 404 | 404 | 允许审核预览 |
| deleted / 不存在 / 未知状态 | 404 | 404 | 404 |

匿名 / 无效 JWT 返回真实 HTTP 401；已锁定账号 403，不可见记录 404。原始上传按相同 file_path 关联资源后应用同一策略；MUS-012 新源码进一步要求没有任何关联的已完成上传仅持久所有者可下载，NULL owner 的旧 orphan 不开放下载（包括管理员）。有关联但资源已删除不能被当成无关联上传绕过。旧 metadata 解析 / 保存接口在引用已有资源的 file_path 前应用同一规则，防止重新绑定成自己的 pending 资源来绕过。MUS-012 的持久 owner / 首次绑定契约见 A5；真实服务验证仍待普通终端加载，不据自动测试开放公开服务。

取消 `/uploads/**` 的磁盘静态映射。该路径不再提供任何音乐文件（登录也不绕过）；只保留被 users.avatar 引用、无 music_resources 关联、可识别 JPEG / PNG / GIF 且 <=5MiB 的头像图片，供现有 img 显示。任意路径、未登记图片和指向音乐的 avatar 引用不构成公开文件权限。

成功、401 / 403 / 404、HEAD 和 Range 响应均 `Cache-Control: private, no-store`、Vary Authorization、nosniff；不返回旧一年缓存或无条件跨域通配。路径经规范化与真实路径校验，不允许绝对路径、.. 或越出 upload 根目录的符号链接。播放计数在授权和物理文件检查之后，HEAD / Range 不计数。ZIP 音乐导出逐条应用同一可见性与受控路径校验，不能成为拒绝审核 / 删除的替代下载。

Vue 播放 fetch、列表下载与文件管理下载均携带存储的 JWT；没有令牌不发媒体请求。媒体下载直接按 fetch 返回的 Blob 处理，避免把 Blob 当作 res.data。接口 URL 和 JWT 不进入 query 参数。已下载或旧缓存的副本不能由本次响应头撤销。


### A5. MUS-012 上传持久所有权

- file_upload 新增 nullable BIGINT owner_user_id 与 owner / MD5 / deleted 索引；新记录仅由服务端当前有效数据库账号赋值，请求不能指定所有者。管理角色也不能通过文件 API 代操作他人的上传。
- create / 普通 upload、MD5 check、list、detail、status、missing-chunks、chunk、merge、delete、metadata 解析和绑定均核验当前数据库账号未锁定 / 未删除；check 和 list 仅查询自己的非删除记录，同 MD5 不跨账号秒传，不透露他人 ID / 路径。未知 / 他人 / NULL owner 返回 HTTP 404，失效账号 401，锁定账号 403。
- chunk / merge 在上传行锁内检查所有者；metadata 在同一上传行锁内核验所有者再解析 / 绑定，避免抢先认领。已有审核状态 / deleted 防重绑定规则继续生效。批准资源的媒体读取仍按 A4，读取权限不授予上传管理权限。
- 删除只给未关联任何音乐资源的自有上传加逻辑删除标志，保留字节和分片待后续清理；有关联（含 deleted 或已登记头像）的记录返回 409，避免破坏读取 / 回收恢复。没有物理垃圾回收承诺。
- V001 保持不变；V002 为加列 / 索引迁移，无自动 owner 回填。旧记录保留 NULL：不能认领、续传、删除、绑定或从 orphan 下载；已有关联音乐读取仍按 A4。需要继续上传时重新上传新记录；人工迁移归属需独立可信证据，不能仅凭 MD5 / 音乐引用推断。
- 空开发库初始化到 V002；既有 V001 库须显式迁移选项，通过隔离库 / 配置白名单后只做加列 / 索引和版本登记，不重建表、不清数据、不更改凭据。中途失败保留现场，可在结构符合预期时重试。

- 头像登记属于文件绑定：新头像必须来自目标账号自己的完整图片上传；不能把他人的图片路径写进 profile 使其公开。已登记的旧头像可保持不变；音乐路径继续不能伪装头像。


### A6. MUS-013 独立审核发现修复

- 禁用旧 DELETE /music/{id} 硬删除入口：有效且未锁定账号返回410，引导使用标准音乐资源软删除；匿名 / 失效账号401、锁定403。MusicService也禁止直接JPA硬删，不能通过该入口抹掉审核 / deleted引用。
- 管理员createUser必须重新验证当前有效管理员；新建用户不接受非空avatar，目标账号完成自己的图片上传后通过受控更新绑定。空白avatar归一为NULL，拒绝发生在insert之前。
- profile更新仅写name / avatar / updated_at，不把读取的role / is_locked / password等完整实体写回，避免覆盖并发安全状态。此处补确定性的字段写入验证，真实并发仍需单独验证。
- 开发库迁移在DDL或版本登记前核对V001的准确表名集合、file_upload必要列 / 主键；已有V002还核对owner列nullable / NULL默认 / 非生成列及owner索引列序 / 非唯一 / BTREE属性。未知结构拒绝且无DDL / 版本写入；V001/V002 SQL保持原样。

### A7. MUS-014 上传故障与受控重启验收

- A先审查并按原字节集成B交付1534e4d的清理修复；B报告不改写。异常时清理步骤独立尝试、失败不返回passed，但数据库不可用时不能承诺远端角色一定已恢复。
- 故障探针仅限baseline.validate通过的隔离开发slot和本次合成owner新建上传。数据库故障通过临时CHECK约束注入，分片约束按已核对owner的本次file_id命中；上传表约束按核对唯一的合成filename+owner命中同一记录（MySQL禁止CHECK引用自增id）；正常退出独立尝试清理全部自建约束并核对不存在，不接触既有约束或其他上传。
- 新基线在自己启动且就绪的后端上准备部分上传，再只停止自己登记的后端进程组、确认端口空闲、启动新后端并续传。记录新旧启动PID、partial state哈希、就绪和端口释放证据；没有重启证据不得将单纯resume称为跨进程恢复。
- 上传事务先锁定父上传记录，再对分片执行FOR UPDATE当前读；不能依赖身份查询后已建立的REPEATABLE READ快照计算计数或判定重复/合并。只读进度接口保留普通查询。
- 私有状态中的JWT只存.local/<slot>，0600且不进报告。通过/失败数、持久计数/行数、响应与字节结果可归档，清理不完整必须失败。并发上传/合并是真实并行HTTP请求，不能把mock回调或服务对象重建当新JVM恢复。

### A8. MUS-015 头像同值请求校验

- profile与管理员更新用户时，每次非空avatar输入均须经requireAvatar锁定读取所属上传并核对目标用户、完成状态和未删除标记，即使与读到的旧avatar相同也不能跳过。
- 头像校验先持有上传行锁，再写用户引用，与上传删除路径共享锁顺序；旧profile快照不作为上传仍有效的证明。
- 不提交avatar的仅名称修改继续可用；管理员清空avatar行为保留。legacy NULL owner或已删除/未完成上传不会因相同路径输入而得到认可。
- 本次确定性MockMVC/mapper回归与真实多连接交错分开记录；HTTP状态/旧管理员业务错误封装保持现状，schema和API字段不变。

### A9. MUS-017 管理员用户编辑的空值与写列

- PUT /users/{id}继续由管理员权限入口控制。name/email/role/avatar缺字段或null均保持已读值；明确avatar:""写入空字符串以解除引用，非空路径每次执行原requireAvatar当前上传校验。
- 使用局部UPDATE，仅写本次非null提交的name/email/role/avatar及updated_at，不通过完整实体回写未提交头像、锁定、密码或其他安全列。不得为支持清空而全局开启NULL覆盖。
- 返回对象只应用本次已提交字段，avatar:null不再回显已清空。本返回保持读取快照语义，不额外承诺未提交字段在并发中的最新值；未提交字段不会作为写入值。
- profile入口行为不变；空字符串清空约定只针对管理员编辑。真库响应/持久值与受控交错验证须单列，不用写列mock替代。

### A10. MUS-021 用户请求边界与专属写列（B范围内真库增量已验收）

- 管理员PUT /users/{id}使用独立输入DTO，仅接受name/email/avatar/role；其他字段继续忽略，不由body userid改变路径目标。`{}`与全null输入均保持业务字段，仅沿用updated_at更新。原权限入口、响应快照及旧HTTP200业务envelope保持，不全局移除Users身份注解或改变NULL策略。
- lockUser仅写is_locked/lock_time/unlock_time/updated_at；lockUserWithReason再写本次非null lock_reason。新上锁明确将旧unlock_time清NULL；unlockUser仅写is_locked/unlock_time/updated_at，继续保留既有锁原因/锁时间。
- changePassword、resetUserPassword、resetPassword仅写password/updated_at；校验、编码、返回及验证码成功后失效行为保留。六入口均以本次目标userid为WHERE，不回写读取快照中的头像/邮箱/角色/其他安全列。
- 本项限制写入列，不能据此宣称旧密码并发请求、验证码消费、权限撤销竞争或三个正常HTTP参与者竞争已解决；真实多连接验收须单列。消费者仍原前端，不新增浏览器API字段；B在准确实现SHA上补限定审核。

### A11. MUS-023 演示导入恢复与公开链接（B范围内真库增量已验收）

- 私有demo-account.json保留同一凭据，新增.local/<slot>/music-catalog/demo-account-state.json（0600）记录pending/confirmed及凭据指纹/确认目标。legacy凭据首次兼容按pending确认；confirmed登录失败不重新注册。pending先login，只有旧/auth/login明确Invalid email or password业务拒绝才用同一凭据register；网络/其他业务错误不猜测账号不存在。注册响应丢失可再login确认，拒绝/不确定则保留pending，不删除凭据或生成第二账号。profile确认为USER并核对目标后才confirmed，不改变注册/登录API。
- 缓存下载证明须为完整结构，实际字节长度/SHA与证明和选曲记录一致；source/CC BY许可按明确规范化规则匹配，不一致即失败并保留原字节/证明，不重新造证明掩盖。旧http CC许可等价为https相同准确版本；不要求缓存重跑实时查询提供方。
- Jamendo公开来源仅按验证过的track ID构造https://www.jamendo.com/track/{id}；原来源须为该HTTPS主机与匹配track路径且无userinfo/异常端口，query/fragment不公开。许可必须准确CC BY路径、无userinfo/query/fragment；页面四允许主机继续限定HTTPS，无userinfo/意外端口，移除query/fragment，Apple官方曲目仅保留单一数字i查询参数。
- 新本地状态先由ignore覆盖，不提交账号/原音频/缓存/生成目录；不改已存在公开catalog或A曲库，不将B的条件性fixture结果称为真实泄漏或法律结论。独立真HTTP/SQL补验与替身回归分开记录。

## B. 建议的公开 discovery-v0 契约（尚未实现）

### B1. 搜索

`POST /api/discovery/search`，沿用登录 JWT。首版不分页，返回 top_k 个不同 track；top_k 为 1–20，默认 10。每个 track 最多 3 个经去重的片段，片段按相关性降序。

以下是合成示例，不是实际数据或分数：

```json
{
  "query": {"kind": "text", "text": "energetic instrumental music for a racing montage"},
  "filters": {"category_id": null, "tag_ids": [], "tag_match": "all"},
  "retrieval_mode": "segment",
  "top_k": 10
}
```

query 恰好选一种：

| kind | 必需字段 | 约束 |
|---|---|---|
| text | text | trim 后非空，最长 1,000 字符；首版英文基线 |
| audio | reference_track_id 或 query_audio_id，二选一 | 只能引用调用者可使用的资源；临时上传参考见 B2 |

禁止 text query 混入 audio 字段；首版不支持文字 + 音频同时加权。`retrieval_mode` 为 metadata / whole_track / segment / hybrid，表示同一冻结候选库上的对照方案；未实现的 mode 返回明确错误，不静默降级。

过滤：category_id 是精确匹配，tag_ids 去重；tag_match 为 all / any，默认 all。approved 且 is_deleted=false 是 Java 强制条件，不能由客户端关闭。模型推断的人声 / 情绪标签属于软信号；没有检测能力时不允许伪装成硬过滤。时长 / 许可等额外硬过滤须先有标准化字段与缺失值策略；首版不接受未实现的字段。

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "request_id": "example-request-001",
    "index_version": "example-index-v0",
    "model_version": "example-model-v0",
    "retrieval_mode": "segment",
    "timings_ms": {"query_encoding": 120, "retrieval": 25, "total": 165},
    "results": [
      {
        "track_id": "42",
        "title": "Example instrumental",
        "artist": "Example artist",
        "duration_ms": 180000,
        "score": 0.81,
        "segments": [
          {"segment_id": "example-segment-001", "start_ms": 65000, "end_ms": 75000, "score": 0.81}
        ],
        "preview_url": "/api/discovery/tracks/42/media"
      }
    ]
  }
}
```

ID 为十进制字符串（兼容 Java Long，不在浏览器中依赖超过安全整数范围的数值 ID）。score 为所声明模式的排序分数，不是概率；不同模型 / mode 分数不能直接比较。无结果仍返回成功 envelope，results=[]。timings_ms 是服务端测量；浏览器上传 / 下载和完整用户等待时间另测。

错误 envelope 结构与旧接口一致，但新接口同时设置正确 HTTP 状态：400 参数错误，401 未登录，403 无权限，404 引用不存在或对当前用户不可见，413 参考上传超限，415 不支持格式，409 尚未处理好，503 索引 / 模型不可用。错误 data 可含 request_id 和 error_type，不返回内部路径或堆栈。不要把没检索到音乐当作服务错误。

### B2. 参考音频与试听

- P3 先支持库内 reference_track_id，然后增加 `POST /api/discovery/query-audio`（multipart 的 `file` 字段）。后者用于短参考音频，不创建公开音乐资源。
- 建议限制：MP3 / WAV，文件 ≤10MiB，解码后 1–30 秒；服务端按实际解码验证。返回 202 envelope，data 含 query_audio_id 和 status=queued。
- `GET /api/discovery/query-audio/{id}` 返回 queued / processing / ready / failed；仅所属用户可见。ready 后才可用于搜索；临时文件与结果 24 小时后过期，过期引用返回 404。
- 查询音频只生成查询向量，不加入曲库索引。不得调用用户指定远程 URL 或任意本地路径。
- `GET /api/discovery/tracks/{track_id}/media` 每次核验登录、approved 和未删除状态，提供可 seek 的媒体；Range / 206 行为必须实际测试，不能仅设置 Accept-Ranges 就算支持。
- 前端以携带 JWT 的 fetch 获取可播放资源 / Blob，seek 到 start_ms/1000，在 end_ms/1000 停止并回收 Blob URL。也可另行设计短时签名方案，但不把 JWT 放进 URL。
- 旧匿名媒体 / 静态访问路径的治理属于 MUS-001 / MUS-005 的前提，不能因新增安全路由就声称旧路径已被保护。

### B3. 处理状态

建议 `POST /api/discovery/tracks/{track_id}/index-jobs` 和 `GET /api/discovery/index-jobs/{job_id}`，由 Java 做授权；内部导入任务也应使用同一状态模型。已接收返回 202；相同 track / content / pipeline / model 的活动任务复用，显式重建使用新版本。权限、重建和取消行为在 MUS-002 固定，不复用旧上传 status 数字。

## C. 新数据 / 索引约束（逻辑设计，尚无迁移）

| 逻辑实体 | 最小字段 | 不变量 |
|---|---|---|
| audio_asset | track_id, content_sha256, asset_ref, duration_ms, sample_rate_hz, channels, source_uri, license_id, license_uri | track_id 引用现有 musicid；asset_ref 为内部受控标识；文件修改需新 content version |
| audio_segment | segment_id, track_id, content_sha256, pipeline_version, start_ms, end_ms, padded_samples | 0 ≤ start < end ≤ duration；同一 track / content / pipeline / 时间区间唯一 |
| embedding | segment_id 或 whole_track 标识, model_version, pipeline_version, dimension, dtype, normalized, vector_ref | 维度与归一化一致；查询和索引不能混用不同模型版本 |
| processing_job | job_id, track_id, idempotency_key, status, stage, attempts, error_type, timestamps | 状态 queued → processing → ready / failed；重试 failed → queued，计数不重置；新文件另建任务 |
| index_manifest | index_version, corpus_manifest_hash, model_version, pipeline_version, dimension, dtype, metric, file_hashes, created_at | 构建后不可原地覆盖；校验后切换活动版本，保留可回退版本 |

逻辑名不是已存在表名。迁移以 MUS-001 整理后的基线为起点；版本化新增，不能直接重跑历史 DROP TABLE dump。

幂等键建议为 track_id + content_sha256 + pipeline_version + model_version 的稳定哈希。约束防重复持久结果，不保证 worker 只运行一次，也不保证外部推理费用不会重复。任务恢复和删除期间的写入必须检查源资源最新状态。

## D. 音频处理与检索规则（MUS-002 待冻结）

- 解码为 float32、单声道；重采样到准确 checkpoint 要求的采样率。输入曲目与参考音频使用相同预处理、幅值处理和编码器版本。
- 候选 W=10,000ms、H=5,000ms。D≤0 拒绝；D≤W 只生成一个片段并右侧补零；D>W 先生成全部完整窗口，若最后完整窗口没有覆盖结尾，再生成下一个步长的尾段并补零。不得增加超过终点的空片段。
- 时间区间为左闭右开，end_ms 是真实音频终点，不含补零。例：D=4s → [0,4)；D=10s → [0,10)；D=12s → [0,10)、[5,12)；D=15s → [0,10)、[5,15)；D=180s → 35 个完整片段。
- 实现先在采样点上计算边界，再统一转 ms，避免浮点累加漂移。测试非整秒、立体声、不同采样率、损坏文件和多次处理一致性。
- whole_track 基线先对同一曲目的窗口向量求均值并重新 L2 归一化；明确它是基于窗口聚合的整曲表示，不声称模型处理了整首长音频。
- 精确向量基线：L2 归一化向量点积（cosine）；拒绝 NaN / 零向量。维度通过真实模型输出确定，不能默认所有 CLAP checkpoint 都相同。
- segment 排序初始采用每曲目最大分数，记录长曲目偏差；同曲目高重叠候选按时间 IoU>0.5 合并 / 抑制，保留最高分代表及其原始区间，最多 3 段。
- metadata 基线沿用受控文本字段，记录 SQL / 排序规则；hybrid 初始候选为 RRF（k=60），在开发集比较。不得将 SQL LIKE 结果称为 BM25。
- 先按访问权和硬条件约束候选，再排序；如果索引先召回，Java 必须复核且在过滤后不足 top_k 时按有界策略补取。禁止为了凑数放宽权限。
- 新内容未就绪时明确状态，不把旧音频向量与新文件混用。所有响应记录实际 index_version。

### 内部 Python 边界

建议路径 `services/audio-search/`，当前不存在。内部提供 encode_text、encode_audio、build_index、search 所需能力；具体 HTTP / CLI / worker 形式由 MUS-002 决定。Java 到内部模块传 request_id、asset_ref、冻结 query、filters、top_k、预期模型 / 索引版本；模块返回候选 track / segment ID、时间、分数和版本，不替 Java决定权限。

模块只解析受控 asset_ref 到本机批准数据目录；不接受任意绝对路径。离线本地适配器可以先于网络服务实现，但必须共享同一契约 fixtures。

## E. 评测与证据契约

- 语料 manifest 至少含 track_id、内容哈希、时长、来源、许可、排除原因。不同版本混用会使比较无效。
- query 清单含 query_id、text / reference、类型、语言、split=dev/test；qrels 用 query_id、track_id、可选 segment 区间、relevance=0/1/2/3（不相关 / 弱相关 / 相关 / 高度相关）。冻结标注说明，多个模型召回池共同人评。
- 120 / 80 / 40 是计划；实际记录标注量、判定分歧和覆盖率。未标注结果与“不相关”要区分；标注不足时不把 Recall@k 当作穷尽标准答案上的真实召回。
- primary 建议 track-level nDCG@10；另报 Precision@5、约束违反率、人评片段相关性。时间定位有标注区间时才报告时间 IoU；无标注不能用向量相似分数自证相关。
- 超参数在 dev 选；test 只评估，不回流用于改参数。生成的参考变体与原曲分组，防止基线间候选或划分不一致。
- 性能分别记录解码、编码、检索 / 过滤 / 排序、完整 Java API、浏览器端到端耗时。说明预热、硬件、并发、请求数、语料量、是否复用 query cache；失败请求单列。
- 每条结果绑定 code_sha、manifest_hash、config、model_version、index_version 和原始输出位置。没有运行证据的项写 planned / unmeasured，不补造数字。

### E1. MUS-024探索标注包（先冻结本地格式，非discovery-v0）

- Python标准库CLI从已完成MUS-022运行生成包；必须显式给出期望report SHA256，核对catalog与manifest/queries/rankings/segments工件hash，绑定owner、track/content SHA/字节数/实测时长、来源/许可、模型/pipeline及源码SHA。只取文字查询两基线top5并集，按track ID排序且去分数，模型建议区间独立保留。旧v1包与原运行只读。
- schema为`sonora-judgment-pack-v1`，split固定`exploratory_only_not_held_out`。初始relevance/human_intervals_ms/annotator/judged_at均null；null是未判断，0是明确不相关，不能转换或补默认0。人工相关性仅整数0/1/2/3；已判断需手工填匿名标注代号、UTC时间，人工区间为可选有限个不重叠整数毫秒左闭右开区间，0<=start<end<=实测时长，不复制模型区间。
- 校验必须重新由运行重建不可变候选与音频绑定，拒绝改候选、重复/未知ID、变更split/owner/hash/文本/来源或时间。内容指纹不包含人工字段；校验不认证标注人身份、不替代真人听音，不自动导出质量/Recall/IoU。模型建议可见，存在提示偏差，不是盲评或held-out。
- 新输出只在当前checkout已ignore的.local内以0600独占创建，拒绝覆盖；不复制音频、权重或向量，不写公共JSON/数据库/API，不改变旧媒体权限。后续试听入口需每次经现有JWT媒体API鉴权并核对音频SHA/字节，不能把本包当可播放授权或静态路径白名单。

### E2. MUS-025本地试听审阅（增量Vue入口，非搜索API）

- `/research/review`登录保护，侧栏仅增一个入口，沿用现有Sonora；只导入用户明确选择的<=2MiB本地E1 JSON。浏览器严格结构/重复键/毫秒/标签/owner和dataset指纹校验，不声称认证原run；最终交接仍需E1 CLI对固定run验证。拒绝其他账号包，不把包当权限。
- 每次试听通过现有fetchMedia/JWT GET `/api/music-resources/{id}/file`（无pay，不在URL放JWT），受后端当前媒体权限限制。读取有字节上限并在建立Blob URL前核对完整字节数与SHA256；错误身份/401/403/404不播放。每次重播重新GET；切候选/包、离页、token或账号变化立即取消请求、停止并释放URL。模型片段左闭右开seek/终点暂停，仅浏览器事件/定时精度，非采样精确剪辑。全局播放器与审阅避免双音源，原队列保留。
- 初始不填评分/人工区间/标注代号。0..3只由显式用户动作写入，需匿名代号，UTC判断时间来自该次操作；未判断为null，人工区间不从模型建议自动复制。支持部分判断导出，split不变、不算质量指标。UI不能验证真人身份/听音事实；模型建议可见，仍探索非盲评/held-out。
- 浏览器草稿按当前账号+不可变dataset指纹隔离，仅保存标注包，无token/音频；用户可明确恢复同包草稿，不能静默覆盖新导入判断。导入文件/草稿/导出均校验；本地存储失败需提示并允许导出，退出仅清内存与音频，草稿保留在本机该账号槽。无跨设备/服务端标注写入。原始包及51个真实标签保持null，自动化正标签仅合成fixture。

MUS-027交互补充：评分区就近提供必填匿名代号输入；空值或非法格式时显示具体原因，仅禁用评分选项，不禁用代号输入。代号须1–64位、字母或数字开头，其余仅字母/数字/点/横线/下划线。合法输入即启用选项，但填写/修改代号本身不写评分、时间或已有标注；仍须显式选择0..3。

### E3. MUS-026审阅音频与底部控件

- 审阅音频在现有Pinia播放器登记临时控制会话，底栏显示该候选曲目、状态与实际时间，并把暂停/继续、进度与音量操作转给同一审阅音频。原普通队列/收藏/历史不自动改写；审阅期间禁用普通上一首/下一首/随机/循环，主动播放曲库/队列曲目则撤销审阅会话。
- 页面增加同源进度条及暂停/继续。整曲范围0..实测时长，片段限定原选择start..end；seek立即更新真实播放位置与停止计时，不能拖出片段。暂停保留位置并释放Blob，继续/已释放状态seek重新GET且验证SHA字节；在已验证活动Blob内seek不重新下载。终点后继续从该范围起点重播。
- 开始审阅取消普通播放器未完成的加载，防迟到普通响应/事件夺回播放；新会话/旧回调隔离。换候选/导入/离页/退出释放审阅控制并回到原暂停队列状态，账号退出仍清队列。原JWT/内容校验/不计pay/标注与草稿隔离保持。

## F. 契约变更

MUS-002 冻结时记录版本、日期、负责人与 fixtures 位置。修改字段、时间单位、可见性、索引身份或错误语义前：列出生产者 / 消费者，更新本文及 fixtures，协调两个任务，再实现与验证。旧接口与新契约存在差异时显式适配，不静默更改旧用户流程。

MUS-002 候选实跑补充：固定 music_audioset checkpoint、HTSAT-base / no fusion，实际文本与音频投影输出 512 维；这仅适用于该准确 checkpoint / SDK 组合。探针显式零填充以避开 SDK 默认 repeatpad；尚未用真实音乐证明效果，D 部分规则及 discovery-v0 继续为 proposed，不凭这次编码检查宣称契约已冻结。
