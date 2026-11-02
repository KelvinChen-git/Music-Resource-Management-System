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

### E4. MUS-029已判候选池探索比较（非discovery-v0验收）

- 标准库离线CLI同时显式固定report与已判pack的SHA256；沿用E1从run/catalog重建并验证不可变候选，所有候选必须已判断，缺判不能当0。只使用原rankings中两模式各5首的原顺序，包中的ID展示序不能当排名，分数tie保留冻结运行的既定顺序；短于5/未知ID/重复或缺判拒绝。
- P@5固定relevance>=2为正相关，分母5；pooled nDCG@5固定gain=2^relevance-1、discount=log2(rank+1)，IDCG从本查询两模式已判并集取最佳5。IDCG=0返回null、不进nDCG宏均值，并披露数量；P@5仍计0。每查询等权，两个模式同一已判池，不推断未入池曲目的标签；输出各query分布与pool正相关数辅助解释高nDCG/低覆盖。
- 不报告Recall、nDCG@10、定位IoU、显著性/held-out泛化、P95或10%提升，不据本轮调参/改阈值/训练。两模式比较只适用于这8个探索描述/当前池；模型提示可见且原语料小，不能区分曲库缺失和模型误排的完整原因。
- 结果绑定输入报告、catalog、pack、rankings、模型/pipeline和评估源码哈希；保留原输入及所有人工判断。逐曲排名/标签/案例仅本机ignore的.local、0600独占创建；提交聚合指标/方法/限制与非敏感汇总。不得自动把模型建议当人工定位，原始包/音频/向量只读，无网络/数据库/新API。

### E5. MUS-030未入池诊断补标（仅当前小曲库，非新召回）

- 新格式`sonora-diagnostic-pack-v1`，split仍`exploratory_only_not_held_out`。顶层与E1相同；provenance保留E1运行/catalog/model/pipeline/artifact字段，selection=`unjudged_complement_for_selected_queries`、ordering仍`query_fixture_order_then_track_id_ascending`、labeling_aid=`no_model_intervals_for_diagnostic_complement`，另必需base_judgments_sha256、base_dataset_sha256和diagnostic_query_ids有序唯一列表。
- Python标准库CLI先对report和已完整标注E1基包显式固定SHA，再重建/校验E1。只选显式query IDs，在原查询fixture顺序输出“固定全曲库减该query的旧候选池”；所有原候选池外曲目都在，无重复/漏曲/旧已判对。读取固定manifest得到原音频绑定；每query1–100候选、总文件<=2MiB。未知/重复query、空补集、错base或run、漏判基包拒绝。
- 所有新人工四字段初始null，不复制基包已判记录、模型分数或区间；model_suggested_intervals_ms固定空数组。无模型重新排序，按ID展示，只试听整曲/手动seek。原51已判、空白包、run/音频只读；新包/草稿/export指纹不同，不覆盖或静默恢复旧包。
- 浏览器保持E1原规则和上限（<=10），仅新schema允许<=100且要求准确的新provenance字段/有序query IDs对齐/空模型区间；owner/SHA字节/JWT逐次媒体/人工输入/本机草稿原行为保持。新增就近说明“核查未入选曲目、已完成判断保留、不提供模型建议”，不重做UI。
- 固定run+基包CLI最终校验重建完整补集，仅人工四字段可变，沿用0..3/代号/UTC/合法可选人工区间。浏览器只校验结构与自洽指纹，不能独立认证补集来源；交回仍需CLI。E4评估不接受新诊断schema，不把补标当原top5评分或held-out；本轮不自动合并标签/训练/扩库/定拒绝阈值。

### E6. MUS-032定向来源候选（独立source-only版本）

- 当前五描述已用于探索失败分析，按其收集的新曲只属于development扩充，不命名held-out/test或宣称效果提升。新静态selection固定五个query_id各4个不重复ISRC；提供方乐器/情绪说明只是选曲线索，不是人工relevance，后续人评仍需显式用户动作。
- 采用作者官方Incompetech来源及其CC BY4.0署名/下载说明，单独记录官方catalog、曲目展示模板、许可说明的原始快照SHA和每个ISRC记录；音频只从官方HTTPS限定路径取得，保留原字节、长度、SHA、来源/许可/作者/未修改说明。拒绝非官方重定向、越界路径、超限/空/HTML内容、重复ISRC/内容和旧20曲内容。完整录音允许30–600秒，不把短录音拼接或截成假整曲。
- 输出独立`sonora-source-candidates-v1`，split=`development_source_candidates_not_held_out`，身份为provider+ISRC，不填/假造Java musicId或owner，不直接传给旧probe/标注页。原public catalog、原下载证明/音频/run/118判断只读；新目录必须是当前checkout ignore的.local下，0700，文件0600，已存在目录拒绝覆盖；显式固定selection和旧catalog SHA。
- 本任务完成来源候选收集/内容证明与实际解码检查，不自动变成人类确认的正例、不写本机数据库/账号/API、不重跑CLAP或改排序。后续通过原普通owner HTTP导入取得真实musicId，再生成独立catalog/run/标注指纹；原20基线继续可复验。单作者集中度与围绕已知描述选样的偏差需披露，独立测试另建。

### E7. MUS-033来源导入与20条素材核查（非模型召回包）

- 已有普通演示owner经现有A本机HTTP接口登录/上传/metadata导入，登录失败停止，不新注册/改密/提权/自动审核。显式固定032 manifest、decode结果和原20 catalog SHA；先核实完整音频/下载证明/解码绑定，后登录和写入；原账号状态/上传证明/公开catalog/118判断只读。导入checkpoint/锁/副本/结果只在本checkout独立ignore.local目录；同输入重跑核验复用，拒绝错误owner/输入变更/歧义资源/坏证明，不用删ledger掩盖。
- `sonora-research-catalog-v1`是新私有已导入版本：ownerId、slot、baseline_catalog_sha256、source_manifest_sha256、decode_report_sha256、importer_sha256、audioTracks。保留原20记录并在副本增加sourceProvider=jamendo；新增20以sourceProvider=incompetech/sourceId=大写ISRC保存来源，musicId/fileId必须为HTTP返回真实正整数。新曲含contentBytes、decodedDurationMs与原provider durationSeconds；官方sourceURL精确为`https://incompetech.com/music/royalty-free/index.html?isrc=<same>`，CC BY4.0。每首Range206/完整响应SHA匹配才记verified；不修改原文件。数据量40不等于已建40曲向量/检索结果。
- 先核验新素材是否适合五条已知描述，再做扩大曲库检索对照。新增`sonora-source-review-pack-v1`，split=`development_source_candidates_not_held_out`；沿用顶层schema/split/owner_user_id/provenance/queries/dataset_sha256。provenance精确键为source_manifest_sha256、import_catalog_sha256、decode_report_sha256、source_selection_sha256、query_fixture_sha256、selection=`targeted_source_candidates_by_metadata`、ordering=`query_fixture_order_then_track_id_ascending`、labeling_aid=`no_model_intervals_source_qualification`，不伪造模型/checkpoint/report。
- 仅五个目标query按原fixture顺序、每个4个新曲，共20个独立query-track对，按真实track_id升序；candidate为E1共同字段加`source_provider`，仅incompetech、source_id严格ISRC，track_id仍Java Long；来源和许可精确绑定，model_suggested_intervals_ms为空，人工四字段null。按source ID/内容/真实Java ID三者去重，catalog/manifest/decode SHA必须显式固定重建，只允许人工四字段改变。新指纹/owner隔离草稿，不复制旧评分，也不改旧包/指纹。
- 浏览器只新增此明确schema/split/精确provenance分支，保留旧E1/诊断原规则。新包5query各4、20不同曲目，严格ISRC/sourceURL/CC BY4.0/空模型建议；页内说明“新素材核查、仅20条、非模型排序”。沿用JWT+完整音频SHA/字节、原播放器/seek/评分/草稿/导出，不重做UI。最终仍需新CLI绑定本机输入验证，浏览器自洽不等于认证来源/听音。
- 本卡不改旧corpus/probe/两旧schema或跑CLAP。40曲private catalog/真实ID与20条素材核查完成后，后续另建provider-aware索引与模型候选版本；定向选样/单作者仍是development，不能宣称独立测试、曲库已足够或模型提升。

MUS-033真实浏览器补充：Morning同一已核SHA MP3的soundfile时长153555ms、浏览器153253.22ms，原100ms边界保护拒播。仅新Incompetech来源的整曲请求（0到记录全长），在JWT/字节/SHA已通过且浏览器时长有限正值后，实际播放上限取记录时长与浏览器时长的较小值，状态/seek/暂停继续共用该范围，内部另存原整曲请求范围，每次重新获取后重算端点，当前位置>=新端点则拒绝，不改包中的解码时长；源文件/人工字段保持。片段请求及两旧schema继续原边界保护，不能通过此适配扩展允许时间范围。不得以此声称两种解码器采样时间完全相同。

### E8. MUS-035两来源40曲离线检索对照（development）

- 新增research_corpus.py/provider-aware只读适配、research_probe.py独立运行与research_evaluate.py有界对照，旧corpus/probe/E1/E4/诊断/source包工具字节保持。不扩Java/Vue/API/schema/依赖/模型版本。显式固定033私有40catalog、032 source manifest/decode、原20基线、selection、8查询fixture的SHA；沿用E7重建输入，新旧复制音频/证明再次验证、provider+source_id与真实track/file/content去重，不接受任意来源或路径。新manifest显式source_provider/source_id/Java track_id，区间以真实解码采样为准；与E7新20历史头部记录核对并另存实际读取结果，来源提供秒数继续独立保留。
- 每次构建完整40曲重新解码/编码，不复用旧NPZ/旧索引伪装新运行。固定同一music_audioset SHA/revisions/HTSAT-base/no fusion/strict load/CPU预处理，原10s窗口5s步长/尾段右零填充、窗口均值整曲归一化、片段最大分数/IoU抑制和ID并列规则均复用既有函数。仅8个原英文查询、两mode各top5，暂不生成新的参考音频查询；记录实际维度/帧数/片段/时长和单次耗时，非P95。不得读取人工标签参与编码/排序。
- 真实run-01补充：新来源Morning的SoundFile头部帧数6771806，但read实际返回6761088；历史032使用blocks()的yield长度计数，把估计末尾算成实际，旧decode报告与E7时长因此仅作历史头部记录保留，不能填零凑齐。新增来源专用decoder `soundfile-read-out-65536-actual-eof-v1`：固定65536帧float32 out缓冲，按每次实际返回len与tell增量计数、至实际0帧EOF、有限/30–600s/帧数上限检查后按原DSP均值单声道与整数ceil48k重采样；旧20仍用原decode_mono，旧代码/结果不改。头部元数据须匹配recorded_decode历史记录；新source_frames以实际返回计，另存declared_source_frames。新manifest/report均明确source_decoder_version，窗口/时长按actual，旧包/标签原字节保持。不同read块大小可有float32舍入差，固定读取块定义版本，不声称PCM位级相同；不得把header和actual不符当已补齐的完整解码。新比较只对track/content与无人工区间的相关度，不能借此评价旧时长的定位精度。
- 新run/report有独立schema：manifest=sonora-research-corpus-v1（原pipeline_version、tracks、visibility/evidence，tracks追加provider），report=sonora-research-probe-v1，status=passed_private_research_pipeline_only；queries.json保留原fixture，rankings.json沿用kind=text/query_id/text/whole_track/segment有序数组、judgments=unjudged，不能送旧E1工具。report记录source SHA/dirty、精确源码hash、输入各SHA、全部工件hash、模型/pipeline/environment/counts/provenance与限制。源码提交干净后实跑，所有输入构建前后重核，失败独立failure记录，不覆盖既有成功或失败run；输出只当前checkout已ignore.local、0700/0600、无symlink，不改原音频/共享模型缓存。
- 在看新排名前冻结对照范围为exp-02/03/04/07/08五描述：旧20曲各全部已判，新20仅每query4条素材标签，合计每query24已知/16未知。评估显式固定旧run/report、40新run/report、原51/67/新20包三份SHA，并各用原工具重建验证、内存关联不可变身份/内容/查询文本；不生成混合schema、不给未判补0。旧两mode原top5与新两mode原top5均保留顺序，不按标签重排；两run模型/数值预处理一致且原20内容/解码/片段规则一致才对照；新来源实际EOF读取版本/actual与declared字段另行核对，不把历史估计帧数当实际。
- 新top5记known_relevant r（>=2）、known_nonrelevant、unknown u，P@5下限r/5、上限(r+u)/5；u=0时才exact P@5，否则null。每query等权汇总上下限，披露各mode未知总数/完全已判query数；不通过排除未知query制造总体精确提升。另列新20已确认素材进入top5数量及旧20原top5已知命中供解释。没有全40真值，不报新nDCG/Recall/IoU/显著性/held-out提升或新旧可比总体精确提升；原029池内指标不改。
- 原138/三完成与三空白包/原20 run及033 catalog和来源证明只读。新逐曲排名/标签关联/向量/日志留私有ignore目录，公开Git仅源码、方法、聚合与hash；单作者/围绕已知失败描述定向选样仍development。新top5若未判，只记录缺口，需另立有界标注补集后才算exact，不能自动打分或调阈值/训练。MUS-002效果验收/discovery-v0仍未冻结，B033准确卡保留，不外推027批准。

### E9. MUS-036：扩大语料top5未知补判包（本轮冻结）

- 独立`sonora-retrieval-supplement-pack-v1`，split=`development_not_held_out`，顶层沿用schema/split/owner_user_id/provenance/queries/dataset_sha256。只取E8五目标描述的新两mode原top5并集减三包全部已判组合，按原fixture顺序、每query数值track_id升序；无未知的query省略。每query1–10个、总量1–50个，禁止添加已判/漏掉未知/按评分重排或任意扩充描述。
- 新标准库supplement_pack.prepare先按显式evaluation SHA读取035评估，再调用未改的research_evaluate.evaluate以原11输入SHA完整重建并canonical比对；不信任孤立evaluation或自行重签候选。新候选metadata/content/bytes/双provider来源及duration_ms来自已校验035 manifest，时间用035 actual EOF，不能用033历史header估计。构建与校验共享相同固定输入，原138/所有旧包/run/排名只读，不加载模型/改排序。
- provenance精确字段：source_report_sha256、run_code_sha、input_catalog_sha256、checkpoint_sha256、pipeline_version、source_decoder_version、artifact_sha256（035完整五工件）、evaluation_sha256、known_judgments_sha256（base/diagnostic/source三SHA）、supplement_query_ids（有未知的有序query ID）、selection=`unjudged_union_whole_track_top5_and_segment_top5`、ordering=`query_fixture_order_then_track_id_ascending`、labeling_aid=`no_model_intervals_retrieval_supplement`。run_code_sha仍035编码提交，不伪装成本次包工具提交。
- 候选沿用E1四个人工字段及source_provider；jamendo十进制source_id/规范Jamendo与CC BY URL，incompetech严格ISRC/官方ISRC URL/CC BY4。track_id为Java Long十进制字符串；内容、来源身份及跨query同track元数据一致，禁止不同track共享来源或content。初始四人工字段全null，model_suggested_intervals_ms必须空；允许人工四字段按原0–3/代号/UTC/区间规则填写，不提供模型区间或默认判断。dataset以新schema/provenance/实际时间及null人工字段canonical签名，草稿按owner+新指纹隔离，不能迁移旧判断。
- 浏览器只最小新增schema校验及“本轮仅补判未判断结果”的说明，原布局/播放/评分/草稿/旧三schema规则保留。整曲沿用完整JWT媒体字节/SHA校验后Incompetech较短端点保护，每次fresh恢复重算；不改旧播放器。浏览器校验不认证固定来源，导出必须由CLI以原输入重建校验。本轮真实新包/工件仅写ignore.local/a/mus036；可复用CLI限制为本checkout已ignore的.local私有子目录，不硬编码任务号。目录0700/文件0600（文件创建后fchmod，不受umask影响），拒绝symlink/逃逸/覆盖既有输出。
- 本轮仅准备包与工具，未接收新真人标签前保持035未知范围和指标；后续接收另立任务。不训练/调阈值/新跑模型，不产生新质量指标或将这3对称独立测试。033 B限定批准只接收原卡范围，035另派独立审核，不外推批准。

### E10. MUS-037：补判接收与固定排名的完整top5比较

- 只接收E9原包同一dataset的用户导出，按035 evaluation及原11输入显式SHA用既有supplement_pack CLI完整重建验证；新包SHA另行记录、原字节归档，不改原下载/旧138/空白包/历史时间/排名。接收检查四人工字段合法且3对全判，个人代号/时间与逐条判断仅私有0700/0600。缺判时只记录缺口，不预填评分或报告精确值。
- 在看本轮评分前沿用E8冻结五描述exp-02/03/04/07/08、两mode原top5顺序、>=2相关、每条固定分母5和五条等权宏均值。将三旧包138与新补判3仅在分析内存按query/track/content关联，组合不得重叠；不生成混合schema或将标签放入索引/排序。原035 evaluation保留，本轮分析使用新的私有文件与报告，不回写旧有界指标。
- 原035每个top5位置须在四包中恰有有效判断才给本轮精确P@5；逐query/逐mode同时披露相关/不相关/剩余未知，未知不补0。有人工区间时仅按实际包规则校验并计数，不将其用于模型区间准确率或强行拒收合法track判断。原20曲同五描述的固定排名也按已有人评单列；不与029八描述指标混分母，不计算新nDCG/Recall/IoU/显著性/阈值或held-out提升。
- 本轮仅原件收件、既有CLI运行、私有一次性分析/独立复算与必要文档，无应用/检索工具/模型重跑或评分调整。即使top5均已判，也不代表40曲×8描述完整真值；披露新增后累计已判与全体未知、定向单作者development/模型选样及相关度主观性限制。B035原卡准确9797/rev1保持assigned直至独立feed确认，既有033批准不外推本轮。

### E11. MUS-038：独立小样本评测设计（执行仍planned）

- 冻结方案与机器计划见`docs/evaluation/MUS-038-protocol.md/.json`，仅设计工件，不是已实现数据/runner/标注接口。旧40曲/141标签/179未判/8旧query与同意图改写全部development；复用原20×五query已完整100对作dev预检，不另增cal标签。新test计划20新曲×8新英文query的完整160对、四批各40；实际新曲/query正文/标注/权重下载/run均0。
- 新test索引仅20新曲，不混旧40，作者/合作/同作品版本与近重复组排除旧材料，至少5新群、每群最多4曲。query及解释先于候选查阅/新排名冻结，采样框提供方/纳入条件/枚举快照与SHA先于新query编写/披露冻结，素材只按固定hash优先序与非相关性排除规则；不足20曲/5新群则blocked或另版，不按query挑正例或放宽分组。SHA非近重复证明，关系不明隔离；预训练录音重叠unknown，不能声称CLAP未见。替补只允许数据冻结与任何test模型运行/标注前，后续错误保留并中止该版本，不静默换曲。
- 比较A当前music、B官方同家族music_speech_audioset候选，各whole/segment共四组及title-only词面sanity。A/B固定revision/文件SHA见计划；B仅远端pin核验，本地SHA/严格加载/实际512维与兼容性待实施。共同actual EOF/DSP、各自独立向量和固定排序；主Bwhole−Awhole，次Bsegment−Asegment与各checkpoint内消融，全四组保留，不按dev胜者删组，不将权重差异因果归因speech或不同架构。无当前模型版本/依赖变化。
- 全矩阵model-blind单用户标注、null保留不强0；title/来源提示限制披露，非双盲/专家或一致性已验收。8条含2条可能无匹配边界需求，但实际0正例由完整人评决定，不能据此改query。主macroP@5相关>=2、分母5、全8等权含零正例；次full20-IDCG nDCG@5指数gain，IDCG0为null/仅该宏指标排除并披露；全1分无二值正例却nDCG=1须明确。任一未判则不出完整正式成绩，不删query。报告预注册成对差值/胜平负，不报首批显著性/Recall/IoU/P95或广泛泛化，成绩不提升不使有效评测失败。
- 运行冻结收据须在任何test run/可读qrels打开前绑定协议/数据/query/分组/呈现、双方本地checkpoint/源码/依赖/全部配置SHA；标注者保管可读test原导出至G5，G2收据、160合法判断和5组runs持久化hash齐全后才交运行方一次解封；此前仅收SHA/总完成数/合法性，不收标签分布或可读正文/路径。hash不是访问控制，要记录实际保管/打开步骤；看test后修改则旧test转development回归。当前四旧包/CLI/页面不自动支持此新test，另立新契约/实现，不能改split冒充。下一步039来源/描述/分组manifest，再040安全模型预检和新runner/包最小适配；本轮无采样/下载/编码/应用修改。

### E12. MUS-039：独立来源框、新描述与source-only语料（不含模型运行）

- 源于038协议SHA f83a3b456ce51a6dc25b1e4b5c8ae3c77a37168f2b2b11645ccb14a65bebc9e8。先冻结官方LibraryOfCongress/citizen-dj固定revision的loc-fma全部132条元数据及137原始快照；不按genre/query截取。公开冻结回执见docs/evaluation/MUS-039-source-frame.json；完整frame/原始快照/逐条来源仅ignore.local/a/mus039，0700/0600。freeze时新query正文/音频下载均0，frame不可按随后query改写。
- 新source-frame schema=sonora-holdout-source-frame-v1，固定protocol/source_revision/provider/metadata_file/snapshots/tracks/priority_seed，snapshots为相对安全路径→SHA。132身份从官方metadata完整重建；逐item frontmatter必须绑定uid/title/contributors/permalink/stream_url/rights，数字标题只规范为原显示字符串。下载仅官方模板的HTTPS S3固定bucket/audio/items/loc-fma/fma-N.mp3；不得下载samplepack/one-shot替代整曲。rights原文为public-domain dedication，不能补造其没有的CC0 URI；有新证据冲突先隔离。
- 作者/合作/作品审查独立sonora-holdout-group-review-v1，绑定frame与旧40种子SHA。records完整覆盖132个source_id，decision仅eligible/quarantined/old_overlap，creator_group/work_group/理由/有SHA证据必需。不同显示名不证明独立，已证实别名/合作连通组合并；身份/作品/许可未决先quarantine，原旧40作者/作品群排除。没有运行音频指纹时如实只称元数据/关系审查与字节排重。
- 新收集CLI显式固定frame/group-review/old-group-review三SHA，不接收新query正文、模型分数或人评；校验所有来源快照与旧种子后按038 SHA256(seed+newline+provider+newline+source_id)升序，再provider/source_id排序。整作者群最多4，同work/版本群仅首个合格录音，不足20/至少5群则blocked，不放宽或按相关性替补。只有固定技术/内容/许可/身份排除才能从同队列继续，保留排除流水。网络/校验错误不得伪称已解码；独立运行目录重名拒绝，失败原件/日志保留。
- 新源全部共同实际EOF65536 float32 out读取，header与actual分存，不补零凑header；复用既有research_corpus数值解码/DSP，经只读现有环境到48k准确整数ceil。MP3/30–600s/≤30MiB，有限值，内容SHA与旧40及新批次排精确重复。原始下载字节保留，HTTP证明绑定源/最终URL/字节/SHA/rights原快照。不写JavaID/owner，不导入数据库，不建向量/加载模型。
- 成功source-only输出sonora-holdout-corpus-v1，split=independent_test_source_only，20条来源/creator与work组/原字节SHA/实际时间/下载与解码证明，所有标签不存在或null，不提供模型分数/建议。只有真实20/≥5群/所有输入复核通过才冻结dataset SHA；不能将部分批次称G1完成。当前旧CLI/页面不接此格式，040另立契约。
- frame冻结后由未看任何候选的新同会话作者编写8英文描述/中文可听说明与0–3规则、2个可能无匹配边界槽；须区别旧8意图，采样方在20曲与替补队列冻结前不读正文。query文件独立指纹/收据，不自动生成160标注或读标签；本任务不执行G2模型冻结/G3新包/G4排名/G5解封。

### E13. MUS-039 v2：首次来源框不足后的显式修订

- 039初始132框经别名/合作/work审查理论上限19<20（尚未下载/解码），按038允许的“blocked或另版协议”选择另版，原038协议、039初框/审查/8条未打开的旧封存描述均原字节保留。v1描述不进入v2；不看其中正文/模型分数/标签再改框。
- 新协议docs/evaluation/MUS-039-protocol-v2.json，SHA83bc7bf3f00a91634a56fd269daaf6720192c19507860ddff9df33c3063de63b，继承038预算/指标/模型/冻结规则，仅将来源范围显式扩为同一官方revision的全部132 FMA+全部89 MusicBox。完整221框SHAd4f2faaa1d5106626ec64ab8913d7588e96b5f61820ef6e1763506f91e3c8a3e与公开回执先提交；新v2 query正文编写在其后，采样方仍不提前读取。
- 新frame schema sonora-holdout-source-frame-v2，绑定原FMA frame/review精确SHA，新增92份MusicBox元数据/collection/data/逐首rights快照及完整221规范行。MusicBox source_provider=loc-citizen-dj-musicbox，source_id为原始官方录音UID（包含DR字母数字及不同长度数字ID，不补零/截断），官方S3路径仅/audio/items/loc-musicbox/<same>.mp3。原metadata文件名可为.m2ts；下载为官方完整item音轨的MP3派生版，保留官方字节，不伪称原视频/原始录音母带、不本地转码或截取。rights使用原逐首free-use-and-reuse文案和AFC来源，不造CC0 URI。
- MusicBox共享录制项目/创作者池保守合为一个creator_group、上限仍4，不将45署名当45独立群；规范原作者/performer与summary/credit均保留，原40已知身份/作品重叠或身份/作品未决隔离。已有FMA132审查决定原字节复用，不为数量放宽Lucas/Keith等隔离。全221按同seed/provider/source_id SHA顺序，work版本只留首个合格，全部provider用共同actualEOF/48k DSP和原技术边界。
- 新collector仅在完整重建两官方框/rights/模板、旧种子与绑定group evidence后支持v2；同时保留v1验证，不以新代码改旧记录。构建前后重核来源/collector/DSP与全部已保存音频/证明。原v1源码提交保留在历史，v2源码清洁提交后才真实运行。仍需20/≥5群才能输出成功；本修订不意味着20已取得或G1已通过，040新包/runner/模型预检未执行。


### E14. MUS-040：独立格式/运行准备与安全开发预检（第一检查点）

- 继承039 v2协议/20来源/8描述/所有G2–G5规则，原冻结文件不写。先按feed准确接收B035/rev1限定批准；N1仅修research_probe独占输出mkdir后chmod0700、JSON/NPZ fd上fchmod0600，保留O_EXCL/O_NOFOLLOW/重复输出拒绝；不改旧模型、排序、历史run或DSP。
- 新`checkpoint_model.py`仅接受协议中A/music与B/music_speech_audioset两种固定filename/bytes/SHA，不接受任意checkpoint metadata。构造前及反序列化前流式验SHA/大小、拒绝symlink/hardlink；仅复用固定offline roberta构造，无网络回退。torch.load必须weights_only=True/mmap=True/map_location=cpu，strict=True，仅可移除已注册非学习position_ids；错误不得strict=False回退。当前线上/旧工具模型常量不改，新B仅存在本轮私有models目录。
- 新`checkpoint_preflight.py`第一阶段只支持旧20 Jamendo开发catalog与原8描述中的exp02/03/04/07/08，显式catalog SHA及固定旧query fixture；拒绝039新素材/query和qrels输入。完整20重新编码、原窗口/DSP/整曲均值/片段最大规则，英文5条、512维/finite/norm与token<=77。输出新私有manifest/segments/vectors/rankings/report，独占0700/0600、已提交干净源码、前后源码/输入/音频/证明/checkpoint/hash核验；失败保留，不复用部分运行。该driver是开发预检，尚不是可运行test适配器或G2收据。
- 新B权重只从038已固定官方revision下载到ignore.local/a/mus040，保留原TLS错误/不完整文件，不覆盖/替换原共享A权重或cache；依赖/SDK只读复用。正常TLS/准确SHA/严格加载及实际输出通过前不得称B可用。模型下载/构造只在本轮被授权的开发预检，不读取新20音频/query/人评，预检胜负不删任何预注册配置。
- 原100开发判断可在新预检排名固定后只读关联另存聚合，不改分/不当test成绩。039新20仍source-only；本检查点不生成标注包、不导入数据库、不生成test排名/读test标签。040余下需普通owner HTTP身份/权限Range/SHA映射、新test包/runner/词面控制、G2全部运行配置源码环境冻结，之后才G3四批160项；qrels仍由标注者保管至G5。

### E15. MUS-040第二检查点：新20录音导入与可复用只读资产适配

- 新标准库`holdout_assets.py`读取独立`sonora-holdout-input-binding-v1`，必须显式binding SHA；固定协议/frame/group/old-group/source manifest/G1 source-freeze各path+SHA，以及原已导入40 catalog SHA/独立音频root。所有本checkout绑定路径安全相对路径、无symlink/hardlink/越界，完整重建官方221来源关系与原manifest20/作品/作者cap/精确排重/实际时间/下载证明、dataset canonical hash和冻结收据，不接query/模型/评分。原G1文件不增加Java字段或改字节。
- 新`import_holdout_music.py`只使用原普通owner经现有HTTP登录/profile/上传/metadata/Range/完整媒体SHA；不注册、改权限、自动审核、SQL或迁移。先完整验证原40身份/音频/证明与HTTP媒体，再导入新20，结束再核原40。新曲名/完整作者串原样、现有100/50长度边界，album为固定`SONORA independent test <source_dataset前16hex>`；不因元数据长度改素材/截字。新上传与metadata均pending，单独记录真实Java music/file ID，不改已有40 catalog。
- 新私有目录独占锁、原子checkpoint可恢复已提交上传或metadata但响应丢失；绑定/source/helper SHA、owner/slot固定，拒绝未知/篡改ledger、身份交叉/重复、错误旧资源、输出覆盖/路径/硬链/symlink。新20音频/证明独立复制，不复制旧40；全部新目录0700/文件0600且极端umask下明确设置。完成后同目录重试只验证/不重复创建，目录已有非本工具内容则拒绝；错误原件/日志保留，不按时间删除他人锁。
- 导入前按G1同版本65536 actual EOF/PCM完整复核新20，NUMBA仅本检查点私有目录；源码/绑定/新旧原件前后SHA保持。输出独立`sonora-holdout-import-catalog-v1`，split=`independent_test_imported_assets`，仅新20+owner、旧40 catalog SHA/源binding/source_dataset、importer/helper SHA及真实身份/原始完整元数据/Range/full验证；旧catalog和G1原件不写。后续runner通过同只读适配器校验私有catalog/原源/独立副本，按数值Java ID返回新20。
- 本检查点不生成160项包、G2或test排名/标签；下一步在此身份映射上建立五配置runner、固定呈现和独立标注契约/最小页面支持。历史141判断/开发与预检run/双权重/cache/原版及main保持。新资源导入是已授权增量，该普通账号自有资源从40到60须以真实运行结果为准，不能把源码完成写成已导入。

### E16. MUS-040第三检查点：G2运行冻结与四批独立标注格式

- 继承039 v2全部采样/模型/指标/G5规则，机器运行参数见docs/evaluation/MUS-040-runtime-config.json（20/8/160、五配置、共同actual EOF/48k/10s窗口5s步长、512维、seed0/CPU2、词面控制和固定呈现）。新holdout_contract.py只读校验原G1/20真实身份catalog/query原文/参数，明确schema与source/input SHA；旧工具/模型常量/标签不改。
- 新holdout_runner.py的freeze在已提交干净源码上绑定协议/dataset/import catalog/frame/group/新query/呈现、两本地权重SHA、SDK与依赖/环境和五配置源码。A/B实际严格加载，用固定合成音频和旧通用文本检查实际512/finite/norm，不编码新20录音/新query；新query仅tokenizer<=77检查。新G2收据sonora-independent-runner-freeze-v1必须在任何test编码或qrels打开之前保存/hash，失败保留且不静默替换模型/文本。
- runner另提供run：只接显式freeze SHA和独占输出，重新验证全部数据/源码/权重与环境；共同65536 actual EOF/PCM匹配G1后分别完整编码新20/8英文，整曲归一化窗口均值/片段最大与原代表窗口规则，五完整排名分别保存，title-only按预注册NFKC/casefold/unigram/logTF/smoothedIDF/20标题df/余弦与Java数值ID并列。A/B向量独立、不读qrels、不复用旧索引；前后SHA，失败/部分run保留，全部五组hash齐后才有all-runs commitment。本检查点run实现/合成验证与实际test运行须分开报告。
- 新holdout_review.py从已验证G2/input重建四批包，schema=sonora-independent-review-pack-v1、split=independent_test，每批两条固定query×全部20首=40，共160，不按topk选池。query保留英文text及中文gloss/cues/0–3规则/可能无匹配标记；candidate按SHA256(presentation_seed+newline+query_id+newline+recording_key)升序，含真实track/source/来源权利URL/原字节/实际时长，model_suggested_intervals_ms恒空、四人工字段初始null。批号放provenance，顶层仍schema/split/owner_user_id/provenance/queries/dataset_sha256；新dataset指纹隔离旧草稿。
- provenance固定runner_freeze_sha256/source_dataset_sha256/import_catalog_sha256/query_manifest_sha256/runtime_config_sha256/test_dataset_sha256、batch(1–4)、batches=4、selection=full20_per_query_model_blind、ordering=preregistered_hash_recording_order、labeling_aid=no_model_hints。test_dataset为全20身份/8query/固定呈现与source pins canonical hash，批dataset再按null人字段签名；旧包schema不改split冒充test。
- 前端只新增新schema严格校验、中文线索/规则、批次/保管提示及完成回执导出；原评分/播放器/草稿/旧四schema保留。来源为LOC两provider，rights_url使用官方对应/use页面，不造CC0 URI；整曲完整JWT/bytes/SHA验证后可按新LOC已知provider较短实际浏览器终点播放，包时长不改。无模型名/排序/分数/建议展示，原版UI布局不重做。
- labeler端可导出完整/部分判断自行保管；只有该批40全合法已判时可导出四字段完成回执dataset_sha256/payload_sha256/total_completed_count/validation_status。回执hash针对同一exportReviewPack实际字节，其他个人字段/等级分布/正文路径不得提前回传；CLI标签校验仅labeler侧读取基包+本地导出、可只打印允许回执。A在G5前不打开可读qrels，模型五runs全部持久化hash与160合法完成回执齐全后再记录一次解封。新包工具/页面校验不认证身份或听音，也不是访问控制。
- 新输出仅ignore.local/a/mus040/phase03，0700/0600、不覆盖、不写数据库/服务/线上模型。实际新test模型run/评分仍须独立记录，不因G2/包已准备声称模型质量、定位、显著性或MUS-002/discovery-v0完成。B N1原在途卡不扩到本增量。

## F. 契约变更

MUS-002 冻结时记录版本、日期、负责人与 fixtures 位置。修改字段、时间单位、可见性、索引身份或错误语义前：列出生产者 / 消费者，更新本文及 fixtures，协调两个任务，再实现与验证。旧接口与新契约存在差异时显式适配，不静默更改旧用户流程。

MUS-002 候选实跑补充：固定 music_audioset checkpoint、HTSAT-base / no fusion，实际文本与音频投影输出 512 维；这仅适用于该准确 checkpoint / SDK 组合。探针显式零填充以避开 SDK 默认 repeatpad；尚未用真实音乐证明效果，D 部分规则及 discovery-v0 继续为 proposed，不凭这次编码检查宣称契约已冻结。

### E17. MUS-042：G5一次解封与固定五组比较

- 继承038/039v2/E16与已发布3655fb3的四回执请求资格；用户现主动交付四批结果ZIP。先只读ZIP目录与四JSON原字节SHA，全部匹配四回执承诺后才允许解析任一评分；不解压系统metadata或接受替代文件，不覆盖原件。新工具仅标准库，独占ignore .local/a/mus042（0700/0600），原ZIP/四JSON/全hash检查与首次解析时间记录留存；每个输出目录仅允许一次打开，重算使用已归档文件且不伪造新盲测。
- 解封前重验原G2输入/23源码/双权重/已装环境54cache、五run commitment及全部排名/向量hash、四空包与重建包一致。新比较代码不属于G2推理源码，不修改其冻结列表或重跑模型。严格原四人工字段规则、160全合法/8描述各20互异同集为计算前提，未知不补0；五组每query全20原顺序不改。原validator返回的旧split汇总常量不用作新test元数据；新结果显式independent_test。
- P@5按>=2、固定分母5、全8等权含无正例；nDCG@5按2^grade−1与log2(rank+1)、全部20判断IDCG，IDCG0仅nDCG排除并披露。逐query正例数/可达P@5、五组得分/宏均值、预注册B-whole−A-whole主对照及三次要对照的差值/百分点和win-tie-loss齐报；不按成绩更换主对照，不调参/训练/改query/补标。另用独立分脚本复算并区分同操作者与B审核。
- 公开仅聚合、query代号、方法、来源提交和hash；个人代号/原逐曲评分/真实Java身份/原ZIP及JSON仍私有。单用户主观模型盲、20首/8query的小项目测试不是双盲、预训练未见证明或总体显著性，不报Recall/IoU/P95。已看test后的新训练调参将它降为development回归，后续模型另设独立评测。041现成标注训练路线保持，原版/UI/main不变。

### E18. MUS-043：既有标签metadata adapter与20首音频预检

- 继承041路线，独立分支codex/MUS-043-mtg-adapter-preflight、base7b592d2；本轮只建立固定MTG cafd8e20…官方split-0/标签/名称/逐曲许可/低码率音频SHA adapter和有界train预检，不训练/编码CLAP或接入Java/页面。原160已解封只作原五组报告，不读取其逐曲评分作筛选、定模板或训练；官方validation/test与SDD不进入train。
- 所有输入显式SHA/固定source revision，校验base及三split的track/artist/album交集与tag子集、合法路径、duration；保留未知标签而非负例，英文模板仅逐字转述已有tag，不添加音乐属性/时序/边界。首批只按源标识hash、非相关性技术限制和作者数量上限选择20；选择方法/适用音频卷先冻结，不能依040测试结果挑歌曲/标签。
- 用已用60首来源/标题/作者及SDD录音/作者构造排除，已知source ID/artist ID/规范化作者名和作品名冲突隔离，获取后再查精确音频SHA/解码PCM SHA重复。只报告实际匹配方法，未穷尽别名/合作/翻唱/声学近重复或预训练隔离，未解决者不能声称新盲测。官方train可用于train/dev来源候选，现有数据不擅自改split。
- 当前仅本地非商业研究预检，metadata CC BY-NC-SA4、逐音频只准明确BY/BY-SA家族；NC/ND/ArtLibre/未知等保留原URI但排除本次候选，不据此宣称产品商用授权。保留逐曲原许可/出处/官方音频SHA和download证据；源标签是上传者整曲弱监督，不是专业片段真值。
- 优先官方低码率文件；若只能tar，须验证服务器206/准确Content-Range/总长度及稳定ETag或Last-Modified，每次有界Range，仅读取tar头和预选成员、校验tar校验和/拒绝link/path逃逸，再核官方逐曲SHA。绝不调用整库download/unpack或extractall；不支持可靠Range时报告blocked，不自动下载46–508GB整库。全轮网络body上限256MiB、每音频<=20MiB/30–600秒/20首，重试有界，失败原证据留存；输出只独占ignore.local/a/mus043，0700/0600，不覆盖旧run。
- 预检需实际EOF有效finite音频/头部与真实frames分别记录、48k mono规范化/合法10s/5s窗口与尾段padding，官方源hash与项目旧内容/PCM去重；通过只证明数据链路，不是训练或模型提升。adapter/相关合成验证和实际聚合交付，旧141/160原件/五排名/权重/缓存/Java/Vue/DB/依赖/原版/main保持。

### E19. MUS-044：千首级metadata划分与20首真实轻量适配训练试运行

- 独立分支codex/MUS-044-tag-adapter-training-smoke，从83ebeea开始。复用043固定metadata/20首官方SHA音频/同65536实际EOF规范；新增train1000/validation200/reserved-test200的metadata计划，整组以artist-ID及规范化credit别名连通分量隔离、作品名和官方低码率SHA跨split冲突隔离、SDD及旧60排除后按预先固定hash挑选、每作者组最多4首/每作品名1首。不以模型分数/160判断或训练结果选语料，不下载千首音频或伪称语料就绪；未来test仅metadata保留，不能称新盲测已完成。
- 首次真实训练使用043已验证的20首（全部只作训练smoke，无验证/测试质量结论）。冻结A原CLAP/checkpoint/英文tag文本编码器，CPU2、inference_mode及requires_grad=False；每首预先固定起点/中点/终点三个10秒窗口、normalized window均值后再L2 normalize。短尾补零规则同043，先复核全部原音频/PCM pin，位置不按标签或模型选择。
- 183原tag各生成唯一短英文模板“Music tagged with 类别: tag.”，不添加细节，确认token<=77再编码。每曲目标Y为其已知tag prototype的平均后L2归一化；未出现tag仍unknown，不作为0/BCE负例、不人工补全。训练X→Y的512×512线性残差适配器，固定lambda=100，唯一目标||XW−Y||²+lambda||W−I||²，闭式W=I+Xᵀ(XXᵀ+lambda I)⁻¹(Y−X)。只有20训练样本，不选lambda或按训练成绩替换主模型。
- 保存原样特征/正例prototype/适配器NPZ及训练前后目标值/MSE/正规方程梯度残差/参数变化/输入与代码环境SHA；仅训练sanity，观察标签Recall@5只作训练诊断（分母为该曲已记录tag数），不是缺失标签均为负例的precision、自然语言检索P@5或泛化提升。不得与042指标直接对比。轻量层拟合才计训练，CLAP编码不计训练；本阶段无整库微调/部署/模型切换/Java导入。
- 运行前冻结数据/窗口/标签模板/单一lambda/源码环境与原A权重；原20 train smoke不能当验证/测试，真实拟合只运行一次，计算复核不改变模型选择。扩展语料与未来训练/验证/测试另行实际下载/内容排除后才可运行，本轮141/160不用于选参或训练。
- 只写ignore.local/a/mus044，0700/0600独占输出，不覆盖043与旧run。现有API/UI/DB/依赖/双原权重/缓存/原版/main保持；保留非商业研究metadata与逐曲许可。数据计划仍不能证明全别名/翻唱/声学近重复/预训练隔离，新增比较不可冒充B独立审核。适配相关测试、实际训练证据和限制作交付。

### E20. MUS-045：接收B计划审查、小批真实语料与人写caption开发门控

- 接收B用户直派MUS-044-PLAN-B/rev1（reviewed46b52db，peer feed0faad731/source1724630），verdict needs_revision_before_scale_up；它不是044正式工具批准或035-R2认领/关闭。044原20训练结果/配置保留，不立即下载1000；本阶段固定044 train列表前100、validation前20，各后续20/4为技术替补，保留原200 test。替补只因下载/校验/解码/内容重复等技术原因，按冻结顺序及原组限制，不因模型或标签分数改样本。
- 人写来源固定041 SDD CSV SHA/validated子集；只按metadata/逐曲BY/BY-SA许可/30–600秒/官方低文件SHA、旧60+043 pilot与044全部计划作者credit/作品名和源SHA关系排除，按固定hash作者组件/录音取caption-dev20与final-caption-test20、独立dev技术reserve2，每组1录音；全部相关caption随录音归组。derived test仅metadata，不传caption文本/音频给模型、不评分；源CSV已为本机metadata原件，不把hash当访问控制或自称双盲。统计容量不足时blocked或新明确协议，不挪test补dev。
- 首轮只获取100train/20tag-val/20caption-dev，总body预算1.5GiB、磁盘2GiB、2下载worker、每音频20MiB/最多3尝试、总1800秒。逐track独占attempt目录、原字节SHA/严格206与validator/实际EOF/finite/同65536规范PCM、append-only费用与结果日志、单进程flock及显式同plan/config恢复；不覆盖partial/原件、没有证明完整的记录不进ready。中断后复核有效receipt/audio再复用；请求失败/崩溃的预算保守按已预留body计费，不能重启清零。只读旧40音频补同规格PCM，加旧20既有pin，以排除旧60 exact-file/PCM以及新split间精确内容重复；仍不冒充全声学近重复/翻唱/预训练排除。
- 泛化runner另立，不改044 smoke。冻结原A及文本空间，每曲固定3窗口，先unit窗口、mean后unit；拟合均值损失alpha∈[0.1,1,5]，lambda=Ntracks*alpha，identity对照，最多3拟合，N>=D用primal否则dual，复用同一模型/DSP/窗口/数据SHA/文本与源码版本绑定的特征缓存。不把同曲3窗当3独立训练样本。whole=unit(Xwhole W)，text原空间不乘W；segment=各窗口unit(zW)取max，作为独立次要结果，不继承whole收益，不作时间定位/全窗口或参考音频能力声明。
- 主指标caption-dev已知配对text→audio R@5，候选固定dev20录音，每caption只已知本录音为正、多caption先每录音平均再20录音等权；未配对不等于语义负例，不能报全相关度P@5。另报R@1/MRR/query宏/tag已记录Recall、genre/instrument/mood与训练seen/rare/unseen支持和三窗口segment结果。候选必须whole R5相对identity≥0.05且R1不降，按R5/R1/较大alpha选；否则identity并不扩大。开发结论不当最终test或显著性，不看保留test/141/160评分选参，不自动部署/换索引。
- 只写ignore.local/a/mus045、0700/0600，保留非商业研究/逐曲许可与所有旧工件/权重/cache/Java/Vue/DB/原版/main。公开只aggregate/方法/hash。新科学问题如centroid监督损失信息、caption不完整真值与小样本不确定性要明示，结果可为无收益，不为造提升改描述或换样本。
- SDD描述对应录音开头最多2分钟，caption-dev只用完整验证后的低码率源前min(120秒,EOF)三窗口，与训练整曲视图分开；它不是原SDD320kbps音频的字节等价官方benchmark。两模型用完全相同视图/文本，固定77token截断并报告超长数，不因分数删query。
- 候选门槛还需配对录音bootstrap（seed20261031、2000次）R5差值95%区间下界不为负，仅作本开发样本不确定性描述，非最终显著性声明；tag支持按训练正tag出现次数unseen0/rare1–4/seen>=5分桶。


### E21. MUS-046：扩大开发候选池、复用原适配器的诊断

- 从已发布e109b5c另立codex/MUS-046-expanded-caption-diagnostic；045原冻结/结果/门控不改。只复用140已验证音频、原24描述特征和原三W加identity，不新拟合/下载音频/新增人工评分；20描述录音仍development，原200标签test与20caption-test不取音频/文本/模型输入/评分。
- 参数先固定docs/evaluation/MUS-046-diagnostic-config.json。候选源身份升序、全140（含100训练/20标签验证作未判语义干扰项），不根据rank/模型/标签抽样。为避免自己20只开头而其他整曲的视图偏差，所有候选统一已校验源前min120秒/同65536 EOF/48k mono、三个首中尾10秒窗口；仅重新编码120干扰录音，原20开发窗口/文本严格复用。没有全窗口或定位真值。
- 新诊断runner独立，不修改045编码器或指标。严格校验原config/cache/NPZ/corpus/收据/音频/原G2/权重/环境/三W哈希与shape/finite/源码，干净已提交源码先写freeze再模型加载；输出只ignore.local/a/mus046独占0700/0600，失败/重复目录拒绝，前后复核源和输入。
- 主报告录音等权已知caption本曲配对MRR（无R5的20池天花板要求），另完整R1/R5/query宏及三窗口；同24描述同时报告原20和扩大140池、四模型，不把未配对当确认负例。bootstrap按20配对录音分组、seed20261031046、2000次报三指标差与区间，仅开发描述性结果。
- 本次不再按新指标挑选或部署模型、不凭开发改善放大训练，固定保留identity；新评估因已知045结果而设计，不能冒充重新独立盲测/推翻045原门槛。目标是检查扩大池后差异与监督信息：公开仅100训练特征/正tag目标的平均两两余弦、配对caption对原音频及tag均值的聚合余弦；只是几何诊断，不作训练原因的因果证明。
- B035-R2/rev1真实approve_scoped收到后，仅关闭准确三输出函数/两测试范围N1，原生全driver缺torch仍blocked；不外推为045或046批准。A串行更新STATUS/接收记录/自身feed，B旧报告按原字节归档；原模型/全部旧评分/音频/缓存/原版/UI/DB/main保持。


### E22. MUS-047：冻结模型的小样本设备校准

- 用户要求继续GPU准备；独立codex/MUS-047-device-preflight、baseaaf5e4b。本阶段不训练/扩容/租卡/上传云端，不改旧23冻结源码、046 runner、模型版本、API或生产缓存；接收B046准确限定工具批准，质量结论保持原边界。
- docs/evaluation/MUS-047-device-config.json先冻结：仅既有100train按源ID升序前3、首120秒/原65536 EOF与48k mono/3个10秒首中尾，共9窗；前6原183tag模板，非人写caption，保留测试输入0。先CPU准备独占校准包（预处理波形/原提示/CPU参考向量及模型/数据/源码/SHA），3轨3窗与046缓存/文字与045prototype作控制，不根据设备差异改样本或阈值。
- 新设备runner显式cpu/mps/cuda:0，不auto、不静默回退CPU/MPS fallback；未安装torch/无可用设备写blocked，不算passed。复用原严格CPU checkpoint loader核sha/weights_only/mmap/strict，之后显式移动全部模型参数到目标设备并核验，FP32/inference_mode/无autocast/无TF32；MPS是本机实验路线，不冒充CUDA验证，CUDA需另机实际运行。
- 缓存key含设备/环境/源码/模型/输入/配方。跨主机允许环境不同但必须单独完整记录包版本/SDK代码与离线cache hash；模型/配方/校准输入及算法源码须同，旧CPU缓存不得伪作GPU输出。原参考路径不要求远端存在，运行显式本机checkpoint和已传入校准目录；本阶段不传输权重/私有数据或配置云端。
- 验证仅数值/排序一致性：向量最大绝对差<=1e-4、余弦距离<=1e-4、整曲/三窗得分差<=1e-4；参考分差>2e-4的候选两两次序必须保持，近并列单独计数，不称全rank字节相同。拒绝非finite/shape或单位范数异常/数据与源码/权重SHA改变。阈值预先固定，未通过保留证据、不放宽后重试选优。
- 每设备同batch（audio3/text6）、一次warmup后3次同步计时，分加载/纯SDK编码（含其CPU前处理与传输）、不含解码/下载/训练；CUDA或MPS计时前后同步，记录CUDA峰值allocated、MPS观测值，按CPU实测计算仅本小批次速度比。不叫P95/服务性能或训练加速；没有真实GPU通过就不标GPU可用或速度收益。
- 输出独占ignore.local/a/mus047，目录0700/文件0600；先干净提交与freeze再模型操作，输入/源码/权重/环境前后核验，重复目录在模型前拒绝；原音频/141+160/三W/全部旧run/原版/UI/DB/main只读。本地可用MPS则尝试一次，不支持算子或数值失败原样记录，不fallback，后续CUDA单独验证。B工具批准与设备实测区分。


### E23. MUS-048：有界140首MPS特征缓存与显式视图消费

- 独立codex/MUS-048-device-feature-cache、basecb77a01；仅复用140已有研究音频/045标签与24已用dev描述、原三W/identity/047 MPS校准，不新下载/fit/扩大曲库/改模型或测试。本轮B047-R1/rev1仍原卡assigned，未收到新feed不接管/改审047源码，048不冒充已获批准。
- 参数docs/evaluation/MUS-048-cache-config.json先冻结：MPS/FP32/audio batch3/text batch6/no TF32/no autocast/no fallback，047同设备校准与环境/source/模型须通过；先核完整旧绑定/音频收据/实际EOF规范PCM/源码及原G2/环境，freeze后加载原严格checkpoint再迁设备，前后复核。无可用或无匹配校准设备明确blocked。
- 按源ID全140取固定视图：tag_training100与tag_validation20完整实际EOF的首中尾10秒，caption_retrieval140首min120秒的三窗。两种视图每录音同起点的10秒窗可按精确sample起点去重；是780个view-window引用，不称780不同片段，实际唯一数从来源记录。24原dev文本和183原tag模板重新编码、逐条text SHA/原次序保持，保留test未进入输入。
- GPU整窗/聚合向量、三类视图/prototype/text均与045/046原CPU校验：最大绝对差及余弦<=1e-4，整曲/三窗得分差<=1e-4、CPU分差>2e-4的稳定两两次序必须保持，近并列单报；四旧模型/两池两模式的录音宏R1/R5/MRR需在1e-12内复现，否则不发布ready缓存，不放宽阈值或改数据选优。它是设备一致性验证，不作新效果提升/选模或独立test。
- 只在ignore.local/a/mus048独占0700/0600生成新特征与manifest。key绑定device/环境/模型/数据/源码/配方，所有检查通过后才写ready manifest；失败向量/报告留存但不能被consumer读为ready。consumer需显式缓存SHA、expected_device/model_sha与tag_training/tag_validation/caption_retrieval view，校验manifest与NPZ hash/shape/finite/norm/身份/标签索引，拒绝混设备/混模型/混视图/partial。旧CPU缓存/API不改，不自动替换生产索引。
- 记录唯一窗口及解码/加载/SDK编码/核验/总时长范围，GPU调用前后同步；原CPU全量未同次计时，不由047小批次2.73比外推全量加速/训练或P95。新cache供后续离线CPU拟合显式读取，当前不训练/部署、不读141/160选参/保留test、不改原版/UI/Java/DB/main。


### E24. MUS-049：GPU缓存上的一次CPU正标签分数训练

- 从已发布e7fea73另立codex/MUS-049-positive-score-training，048 typed cache及其source/model/device/完整parity保持。B047-R1/rev1仍原assigned卡，不修改其或048源码，不外推049批准。只新增独立正标签分数适配模块/runner/相关验证、参数及必要文档，私有ignore.local/a/mus049，原版/UI/DB/main不变。
- docs/evaluation/MUS-049-training-config.json在真实拟合前冻结。只读tag_training100完整EOF特征与183原prototype/已知正tag，先fit落盘后才加载tag_validation20和caption_retrieval140/24已用dev文本；不将缺失tag当负例，不读141/160或两保留test，不编码/下载音频/模型，不扩大训练。
- 原始CLAP/prototype固定、W从I开始。每个已观察标签单独冻结target=min(1,identity余弦+0.05)，未记录项mask=0而非0目标；每曲先平均其已知正项再100曲等权。损失mean_track mean_positive[(unit(xW)·p-target)^2]+alpha||W-I||²，alpha=0.01唯一候选，归一化在损失内避免只靠增大向量长度满足目标。它是本项目预注册实验设计，不称已验证标准训练改进或全语义监督。
- CPU/NumPy float64 full-batch GD，初始步长1、Armijo1e-4/回退0.5最多20、最多200步，训练梯度max<=1e-8或相对loss变化<=1e-12早停；不以验证/描述分数选epoch/参数。记录loss轨迹、步数、梯度、正标签余弦变化、||W-I||和停止原因；到步数上限须明示未证收敛，loss下降不等于检索提升。最多1fit，无grid/重启选优。
- 比较identity/旧alpha0.1/1/5与新W，原三W保持。主开发指标140候选整曲录音等权MRR，完整报两池两模式R1/R5/MRR/query宏及标签验证分桶；新W分别相对identity和旧alpha0.1作20录音配对bootstrap（seed20261031049、2000次）。旧alpha0.1是已看046中旧三组最好的MRR，仅作明确开发锚点；其余两旧候选仍全报，不作新盲测或显著性外推。
- 固定本轮不自动选模/扩训/部署/开保留test。实现数值梯度/正项mask/等权/归一化不靠长度/确定性与优化下降验证；干净提交先freeze，绑定cache/NPZ/原W/参数/源码/NumPy环境，前后重验，独占输出重复在fit前拒绝。W/逐曲细节只私有，公开聚合/hash；CPU训练过程不导入或加载Torch/CLAP，旧缓存及所有评分原件只读。


### E25. MUS-051：现有研究音频的生成caption覆盖审计

- base2e13f61，独立codex/MUS-051-caption-coverage。先核043全部源metadata/044组计划/045当前100train20val/官方音频与收据SHA/实际EOF；冻结全SDD、旧60、caption-dev/保留caption-test及200tag-test的录音ID、完整名称表上credit别名连通组件、规范化作品名/源SHA/已知旧PCM排除。新发现跨train/val作者关系两边均隔离，不补选、不按文字/分数更改。只用SDD身份列，不输出其caption或作模型输入；metadata文件可读不是访问隔离或预训练未见证明。
- 固定JamendoMax13090d7的final_caption30sec.jsonl，787366586 bytes、SHA256 320c09a261b8bea0e9dbeb11b7ec5471582d27d7518c08df7857a80fb445cb7e；config先提交、干净源码先保存allowlist/freeze再请求正文。TLS、只准官方HTTPS/HF跳转、identity编码/完整Content-Length、逐行<=64KiB/对象/正整数ID/JSON finite；全流SHA/长度通过才出完整结果。任务级ignore账本flock、预记全文件body、fsync，总1GiB，无自动重试，失败仍计费；不同输出不能重置预算，已有输出在网络前拒绝。
- 未列白名单的caption不保存/返回/作监督或模型输入，流式处理会物理读取整文件，不冒充其不存在。只保存匹配白名单的原行作独立核查，不存整库正文；matched生成caption必须有finite合法start/end、15–30秒、end<=原实际EOF、不裁切补标签，非空<=8192字符。精确重复只算一次，同ID/区间不同文字全部隔离，其他重叠区间明确报出；生成来源固定model_generated，未知组合不当确认负例。
- 完整报白名单排除数、原文件行数/身份数、matched/合法/重复/冲突/越EOF和train/val覆盖录音/creator组件/区间分布，公开仅aggregate/hash。coverage候选不叫training_ready：原MTG许可与收据只证明已用音频来源，JamendoMax逐曲metadata许可/下载标志差异及版本波形/区间对齐仍待核；原048整曲/三窗特征不能视作任意30s caption的已对齐特征。没有新音频/解码/编码/模型加载/fit/质量评分、项目保留test文字模型输入/云端或应用变化，不自动扩训/部署。
- 标准库模块/runner/适配合成检查、一次有界真实扫描及匹配原行的独立计数复算一起交付。私有仅.local/a/mus051/0700/0600、失败保留；旧045–050/141+160/原权重/54cache/23源码/原版/UI/DB/main不变。B047原assigned卡不扩范围/不竞争派卡，051工具独立审核另待安排。


### E26. MUS-052：匹配57来源元数据与3条参考版本区间预检

- 从4a534fe独立codex/MUS-052-caption-pair-preflight；只051固定57录音/270区间，不扩来源/挪split/读评分。按043原MTG release date映射以2008-01-01为锚的5日metadata文件，选择与050已核两样本范围一致；53文件232610550 bytes/固定JamendoMax13090d7树对象先成私有plan，正常TLS取原字节并核Git blob SHA1/长度，原行/SHA和捕获脚本记录私有，不按caption或模型更换日期/样本。总body512MiB、metadata<=384MiB，既有045–051/模型/原版只读。
- 新reconcile聚合同ID所有匹配行；所有原URI须明确BY/BY-SA且规范化scheme后URI唯一、download flag全true、artist ID和规范化作品名与原音频一致、各metadata时长对实际EOF差<=1秒且自身无不同数值。缺失/未知/NC/ND/权限或身份/时长冲突全部隔离，不取首行/较宽松版本；参考下载URL须绑定同Jamendo ID的明确HTTPS mp32端点。原MTG许可/数据整体非商业研究限制保留，不当商用授权。
- config/源码提交后先freeze再参考GET；在metadata合格train中要求>=3原区间，按固定seed SHA、不同creator组件取最多3来源，不补取验证/外部录音。每个最多20MiB单次请求、正常TLS/HTTPS Jamendo跳转、完整Content-Length/文件SHA/头部与实际EOF；任务级lock+持久body预记，metadata已费计入总额，失败保留无自动重试，不换输出重置已开始参考任务。
- 原音频重新按旧65536实际EOF/48k mono严格复核PCM pin；参考是当前同ID来源快照，拿不到teacher确切缓存字节，不冒充字节相等。原caption首/中/末3区间各取中心10秒，sample边界四舍五入且必须原EOF内；两音频同scipy resample_poly到8k，固定±250ms搜索归一化互相关，音量增益/DC不影响；所有anchor correlation>=.95且峰lag绝对值<=50ms、整曲实际duration差<=.25秒才报该参考预检passed。不得按声学相似度改crop/阈值/样本或把3条外推全57。
- 报metadata合格/隔离原因和原270区间过滤、3参考请求/成功或blocked、每条anchor相关/lag/时长差与费用，生成caption仍model_generated，training_ready保持false（新精确区间特征/独立训练方案未做）。只输出合成检查/私有原音频参考/探针数组/聚合hash，不能称语义质量/定位真值、teacher全部版本相同或训练提升；无CLAP/Torch/模型加载/fit/新曲库/云端/UI/DB/main变化，B047原卡保持。


## E27：MUS-053 时间对应区间特征（2026-11-01）

只用052固定44来源232个model_generated区间（train37/33组件/209，validation7/7组件/23）。原始音频/PCM/许可、051排除与052预检结果绑定SHA，未满足时不写ready，不重复参考下载或扩大样本。每段原起止必须finite、15–30秒、在实际EOF内；48k样本边界round，区间内first/middle/last10秒，起点去重、单窗unit后均值再unit。不能用整曲或旧首120秒代替该区间，也不声称三窗是逐帧完整编码/teacher版本全等。

原caption逐字输入固定CLAP A，不改写/按得分过滤；SDK 77token截断，保存token长度并聚合披露。录音及creator组件不得跨train/validation；每split权重1/录音数/该录音区间数。仅新MPS/FP32缓存，不自动CPU fallback；复用047校准环境，在首次模型加载前冻结全输入/源码/设备/模型/配方，固定hash选3个不同train组件的区间，CPU编码全部9窗和3原caption作新配方数值抽检，容差maxabs/cosine各1e-4；抽检不冒充全232 CPU复算或检索质量。

新manifest及NPZ独立私有保存，只在全边界/PCM/finite-unit/抽检/输入源码环境复核通过后写ready_for_bounded_pilot。consumer必须显式选train或validation和期望设备/模型，检查manifest/result/key/数组SHA、完整行/分组/权重，返回对应区间音频/文字向量及录音/组件，不返回另一split或原caption、不加载模型。重复输出在模型加载前拒绝，失败保留。特征ready不等于训练方案批准/人工语义真值/质量提升，训练方案仍另冻；本轮fit/新音频/新模型下载/保留测试/评分/部署0。原权重、缓存、原141+160/SDD分界、备份/UI/Java/DB/main及B047原卡保持。


## E28：MUS-054 固定一次生成caption适配层训练（2026-11-01）

复用053 typed train返回的209×512音频/文本、37录音/33作者组件；q=1/37/每录音段数。原文经CLAP前77token的现有向量全部保留，不丢弃110长训练描述/改写/重编码，生成标签不当人工真值。CLAP权重冻结，仅CPU float64拟合512×512 W，文本不映射；固定alpha1.0，目标sum(q||XW-T||²)+alpha||W-I||F²，weighted dual闭式解，一fit无搜索。这个未归一化凸目标不等同检索余弦；检索时unit(XW)。解析残差/目标下降仅证明求解正确，不能称质量提升。

干净源码/config/input/model/cache/source/runtime先冻结，持久fit-started.json独占声明阻止换目录再次fit；失败保留不清claim/不自动重试。先保存W/fit收据再获取validation分析视图和旧140/24人写dev作固定比较。typed reader为完整性会物理读取含val的NPZ数组，但只返回train209参与求解；不冒称val字节此前从未读取。val7/23不参与loss/alpha选择；旧dev已看过，保留test/141+160不用作fit。

主开发指标继续固定140池整曲已知配对recording宏MRR，identity/新W两组必报；次要两池20/140整曲/窗口R1/R5/MRR、validation23精确区间已知配对与7录音max区间检索。除已知配对外语义未判，不把同曲其他区间/其他歌当真负例；validation录音等权，23段不是23独立录音。固定2000次/seed20261101054按录音配对bootstrap仅描述性，不作选择；7条小验证/已看dev不称独立总体效果。即使点估计好也不自动部署/扩训/打开test。原缓存/identity/UI/Java/DB/main/原版/B047卡保持，本轮新下载/CLAP编码/人工包0。


## E29：MUS-055 77/256完整描述有界对照（2026-11-01）

固定052原232生成caption/053音频与录音作者分组、054 alpha1加权ridge；只改变文本编码长度77→256，不重写/按结果删样本/新音频或原CLAP微调。77是当前SDK默认截断长度，RoBERTa分支可显式传tokenizer；新长度需实际前向与数值验证，不把支持更长等同质量改善。所有untruncated token IDs须与256非pad序列逐条相等、232长度<=256/原文SHA与053顺序一致，否则不写ready。

同原CLAP A/环境/MPS FP32，freeze先于模型加载。按固定hash从train短<=77/长>77各3、6不同creator组件取控制：CPU77对原053、CPU256对新MPS256；所有108短描述新256对旧77向量各maxabs/cosine<=1e-4。全部通过才写新text-only overlay manifest/NPZ，不覆盖原缓存；显式consumer绑定baseSHA/rows/key/期望设备模型和256长度，split只返回本组音频/新文字/原权重，完整性验证会读取共享NPZ但val不输入solver。

重用054已存77权重、不重训77；新256只一次相同alpha1拟合，持久fit-started claim阻止换目录二fit，失败保留；W/fit收据先存才分析val及旧dev。主指标人写24查询特征仍原048不变/140整曲宏MRR，新256减已存77，identity另作锚；两人写池两mode完整报告。生成val另交叉3权重(identity/77/256)×2查询文字版本(77/256)×2指标(精确区间/录音max)，避免把查询改变与训练改变混为单一收益。2000次/seed20261101055按录音bootstrap，仅已看开发/小样本描述性结果，不是新盲测。无验证搜参/保留test/自动切换部署/扩训，旧原件/原版/UI/DB/main保持；B047原范围限定接收不外推本轮。


## E30：全文本默认与MUS-056归一化配对训练（2026-11-01）

用户明确“保留全文本”。后续训练默认沿用055已验证完整原文token序列/256预算；超256必须失败并另定长度或分段方案，禁止静默截断/退回77/改写原文，历史77工件只读保留。256是本批178最长的已验证编码预算，不是未来任意长文本完整性的承诺。旧24人写query实际11–30token、原048特征已经覆盖全文，继续复用不用重新编码。

本轮唯一假设：054/055未归一化MSE与检索unit(XW)的目标存在差别。固定同37录音209段/33作者组件、全文本T和q=每录音等权、alpha1，只改loss为sum(q||unit(XW)-T||²)+alpha||W-I||F²，等价正配对余弦距离尺度；只已知配对，不把其他录音/区间当负例。原CLAP冻结，CPU float64/2线程，从identity全batch梯度下降/固定Armijo(step1/max200/backtracks20/c1e-4/factor.5)，只训练内grad1e-8或relative loss1e-12停，不用val/开发选步数/参数。归一化目标非凸，停机条件不声称全局最优；达到上限必须披露，不追加步数。

先绑定source/config/cache/W与runtime，持久fit-started claim阻止换目录第二fit，失败保留。先保存新W/fit再分析val7/23全文本与旧人写dev；reader为完整性会物理读取共享NPZ的val，但solver只用train209。两对照identity/055已存全文本ridge不重训，新cosine仅一fit；主固定140整曲录音宏MRR相对全文本ridge，完整两池两mode及2生成val指标/对两锚bootstrap(2000/seed20261101056)必报，不搜alpha/长度、不自动部署/扩训/开保留test。原141+160不用fit、生成文字非人工语义真值；已看dev不称新盲测。


## E31：MUS-057 源数据扩样（2026-11-01）

从044已冻结1000train/200val计划的未用来源中扩展，保持官方split，先按051完整names credit闭包排除SDD全部身份/作者、旧60及保留dev/test的身份/作者/作品/字节SHA；加上045已有120训练验证的ID/作品/字节排除，全部现有与新增的作者/作品/字节跨split关系双边隔离，作者总录音上限4。早于2008固定日期锚或不在固定revision日期树中的来源直接隔离，先写框/输入/源码/config hash再联网。

对同一固定787,366,586-byte caption源完整一次GET验证SHA，仅存允许框匹配原行，不保存整库。预扫描仅使用600秒解码上界，不能称实际EOF；15–30秒非冲突区间存在后，按seed固定hash取最多96train/20val候选，与文字内容/模型分数无关。按2008-01-01五日映射冻结全部候选metadata文件，匹配固定revision Git blob SHA1/长度及本地SHA256；052同文件只读复用，新增metadata预留上限512MiB，超限失败不自适应缩小。

全部metadata行沿用052一致许可BY/BY-SA、download true、同作者作品/来源时长±1秒规则，预判时长仅源metadata，下载后必须用实际EOF重判。按固定候选次序、split达标即停，最多76个音频尝试，每曲仅一尝试/官方range+低码率SHA、8MiB上限；最终目标新63train/13val，技术失败或候选不足如实报告实际数量，不变seed/换监督门槛补数。实际解码48k mono float32 PCM与原60/045全140及所有新增去重，原caption重新验证实际EOF/15–30秒/无重叠。固定hash选3个不同train作者、至少3区间的来源，各当前同ID参考first/mid/last10秒，沿用052相关>=.95、峰lag<=.05秒、总时长差<=.25秒；这不是teacher历史精确音频或全曲语义验收。

总正文持久预记2GiB，metadata/参考先预记上限、官方音频每次read先预记；原目录/换目录均不能隐式再跑，失败保留原claim/正文/日志、无自动重试。全流程无torch/CLAP/训练/新人工标注/保留测试模型输入。原caption完整字节及原行SHA保留，新缓存编码另行冻结，仍遵守E30完整token/超限拒绝；生成文字是弱标签，training_ready=false。本轮不更改训练loss/alpha，不用旧20dev挑来源或参数。原045–056工件/原版/141+160/模型缓存/UI/Java/DB/main/B原派发卡保持。


## E32：MUS-058 全文本扩样特征与固定数据量训练对照（2026-11-01）

固定057新76录音367区间与旧052/053/055的44录音232区间，canonical录音/时间排序共599，train100/539/83作者组件、validation20/60/19组件。旧232音频/全文本与696窗口逐元素复用，新367区间对应1101个唯一10秒窗口，只编码新增音频/文字；每split重新按录音等权再按该录音区间等权。调用原有区间planner的显式expected参数，不修改旧缓存/消费者/训练实现。新增独立typed consumer绑定明确model/device/配方/key/全部行、权重、token证明、NPZ与成功报告，并只返回指定split；完整性会物理读取共享验证数组/原始metadata，不将它们输入solver。

源码/config/全部新音频和receipt/旧缓存/模型与原MPS环境先冻结，持久encode claim先于Torch/SDK加载。原CLAP A严格CPU加载后冻结，MPS FP32/no autocast/no fallback；所有599原文untruncated token IDs与显式256非pad逐条完全相同、旧232 token SHA相同，否则超限失败，不裁文/删样本/退77。tokenization后、任何编码前固定新训练短<=77和长>77各3/6不同作者的hash文字控制，以及先固定3不同新train作者区间/9窗口音频控制；CPU对新MPS各maxabs/cosine<=1e-4，旧232逐元素相同，全部检查才写新ready缓存。特征ready不当检索质量。

同一次干净源码/config分两个独立进程：新缓存明确SHA供CPU-only fit读取，CLAP/Torch不进入fit进程。只train539/100录音参与固定alpha1原有weighted dual ridge闭式解，目标sum(q||XW-T||²)+alpha||W-I||F²、文本不映射；这是对055已存37train全文本ridge的数据量对照，非056新loss继续调参。唯一fit与encode各有task持久claim，原目录/换目录均禁止隐式再跑；失败原件/claim保持。W/fit收据先保存后分析验证和旧human dev，旧37权重不重训。

三组identity/已存37全文本ridge/新增100全文本ridge，主固定旧140整曲录音宏MRR（新100减旧37）；两池20/140×整曲/窗口全部必报。生成验证另报扩展20/60与原7/23子集，两组精确区间/录音max已知配对；旧7数值/identity与旧37的人写dev须完整复现。原24人写查询已覆盖全文（11–30tokens）与候选池不变。对两个锚固定2000次/seed20261101058按录音bootstrap仅描述性比较，不用验证搜参数、步数或挑来源，不称新盲测/人工相关度分类。生成caption是弱监督，原141+160/保留test不用fit/评分；无新下载/人工包/付费GPU/部署，默认保持identity。原045–057/权重缓存/备份/UI/Java/DB/main/B047卡保持。


## E33：MUS-059 监督与评测覆盖诊断（2026-11-01）

只读058现有599完整描述/特征、旧37与新100已存ridge W、048原24人写dev/140候选及058已发布比较；无新拟合/解方程/候选权重/编码/下载/标签编辑或保留test评分。固定train100/539、旧37/209、新63/330、val20/60四子集全部报告，不按结果挑子集。原文与全部旧工件保持，诊断正规化token仅用于统计，不替换模型输入。

英文词/数字NFKC小写统计保留否定词，5gram用集合Jaccard>=.8标近重复；词典只用100train、按不同录音出现比例>=.2定义常用5gram，再报告其覆盖原词位置比例。完整规范化词序列重复/至少5词完整句的跨录音重复均计数；同曲与跨曲分开，所有结果只表示措辞相似，不自动判错误/清洗/删样本。各子集CLAP原token长度、英文词数、对训练词典OOV采用录音等权，另报已存在人写24描述的长度和词面覆盖；OOV/长度差不当语义分布失配证明。

音频/文字各按录音等权计算mean norm、中心化方差trace与participation ratio=trace(C)^2/||C||F^2、同曲异区间及异曲平均余弦。对两个已存模型只核正规方程：G=X'Q(T-X)=outer(muX,mu(T-X))+Gcenter；报告两项norm/cosine与已存deltaW在共同残差方向上的正交投影能量比例，不求解新W、不评估投影分量为候选，不把非正交RHS范数比冒充贡献百分比或因果证明。

三个原模型identity/旧37/新100在四子集的已知配对余弦、其他录音等权平均/最大分数、同录音其他区间均分与差值全部报告；其他组合语义未判，不能称真负例/分类准确率。人写dev只复算旧37→100已有整曲排序的known-pair名次/R1/R5阈值/top5集合顺序/全序变化，连同058已发布MRR差展示指标覆盖和分辨情况，不添加新质量选择规则/打开160或SDD保留test。

源码/config/input/CPU NumPy运行时先冻结，task持久diagnostic claim防止换目录反复修改阈值/隐式重跑；纯CPU缓存运算、不导入Torch/CLAP。只发布聚合和私有证据hash，原句、5gram正文、近重复对及逐查询名次留私有，不生成新人工包。结论以描述统计和限定推断表达，audible semantic correctness仍未验证；后续训练需另冻假设，当前保持identity/原版/UI/Java/DB/main/B047卡。

059执行修复记录：68878c0预检将原24查询误按新候选排序读取，SHA拦截、无freeze/claim；c3e70f6已修复原缓存顺序。该版实际诊断在单区间合法录音上失败，原run-02/freeze、failure和diagnostic-started claim保持原字节，无结果/新fit。新的显式repair config原样继承所有原输入/子集/阈值，只添加钉住的原config/claim/freeze/failure与单区间支持规则：所有录音仍进跨曲/geometry；同曲异区间量只在至少两区间的录音间重新等权，同时披露支持数/覆盖率，无支持返回null。仅准上述准确失败的一次diagnostic-repair-started独占修复，先核原输入hash、无旧完成结果，禁止通用重跑/重置旧claim/更改阈值或来源。保留两个失败目录和日志，修复结果独立输出；不把修复冒称首轮成功。


## E34：MUS-060 训练残差中心化单次对照（2026-11-01）

复用058全部599完整描述特征（17–195原词元、256无截断）、100train539/83作者组件与20val60/19组件，单区间来源全部保留，原文/向量/权重/候选池不变。唯一新假设来自059：正配对ridge更新主要沿共同残差方向。训练q仍每录音等权再区间等权，R=T-X，仅用train539算mu=sum(qR)，目标sum(q||X(W-I)-(R-mu)||²)+alpha||W-I||F²、alpha1固定；X不居中，不给标签加新负例，不把mu从推理结果再扣一遍。只更新512×512适配W、原CLAP/文字不改，推理仍unit(XW)与原文字向量。

纯CPU float64/2线程，primal闭式解一次，无lambda/中心化强度/子集搜索；mu仅训练、中心化目标加权均值接近0、正规方程残差/新目标下降必须通过，目标值不能跨不同目标直接比较为质量收益。已有identity/055已存37全文本ridge/058已存100全文本ridge均不重训；唯一新centered100与三锚完整报告。原始输入/源码/config/NumPy runtime先冻结，持久fit claim禁止原目录或换目录二fit，失败保持原件/claim且不自动重试；W、mu和fit收据先保存再分析validation/人写dev。完整性会物理读共享验证数组与token证明，但solver/均值只用train539。

主指标旧140整曲recording宏MRR新centered100减已存100；次要两池20/140×整曲/窗口R1/R5/MRR、生成val20/60和原7/23两个子集的精确区间/录音max，三旧锚结果必须完整复现058。固定2000次/seed20261102060按录音配对bootstrap，仅已看dev描述性区间，不能称新盲测或正式显著性。另复用059定义，仅描述train100/val20已知配对与未判其他歌曲/区间的差值、共同残差方向投影能量；同曲统计按多区间支持57/9曲条件等权，不按这些诊断选模型/删除来源。

本轮不编码/下载/改文本标签/开保留test/新增人工包或付费GPU，默认仍保持identity，不自动部署。新W与训练mu只存私有目录，发布聚合/方法/hash，不发真实ID/正文/逐项排名。独立验证训练mu/dual等价解/目标正规方程/全部排名和24组bootstrap、chronology及实际单fit保护，保留旧045–059全部工件与原版/UI/Java/DB/main/B047原卡。结果若不支持假设如实记录，不在该dev上追加参数试验。


## E35：MUS-061 人写描述评测元数据容量（2026-11-01）

只复用043固定输入、044全1400计划、045原分组、043 pilot和057实际扩样记录，所有输入SHA先核。SDD原CSV字节需校验和结构解析，立即只投影caption_id唯一性、track_id、artist_id、is_valid_subset，caption/familiarity正文不观察、提取、比较、发布或编码；原sealed20身份元数据只用作排除，不改封存分组。不调用模型/训练/检索评分/网络，不使用未看描述内容或模型分数选样。

作者关系采用全部55k names表上精确规范化全名及拆分credit alias的全局连通闭包，先建图再筛caption；旧Jamendo ID回查当前名字的作者关系，即使显示名变化也排除同组。排除旧60（含外部credit）、043 pilot、044全部train1000/val200/test200、045全部已用/备用与封存caption-test20、057实际76新音频的ID/完整credit组件/规范化作品名/官方音频SHA关系。候选须有至少1条valid flag、base+names一致、官方test身份、30–600秒、BY/BY-SA及官方low SHA；所有失败原因非互斥报告，不按效果放宽规则。

只报告剩余录音/有效描述/credit组件的容量；每组件一首的组件数仅上界，需同时报告组件间同作品或同SHA冲突，不把caption条数当独立样本数。候选ID和排除关系仅私有；本轮不实际分配新dev/test、不导出未见正文、不获取音频/PCM、不编码/fit/评分。元数据许可是固定历史快照，音频版本、实际EOF、PCM/近重复、逐曲权利仍需后续有界核验，不称audio_ready/预训练未见或完整相关度真值。

干净提交后冻结source/config/inputs/runtime，再创建任务持久audit claim；失败原件保留，禁止换目录隐式重试。合成隔离边界、独立全图连通与全部集合/计数复算、实际重复保护和旧045–060全文件保护后才记完成。仅聚合及证据hash发布，原全文本偏好、identity、备份/UI/Java/DB/main及B047原卡保持。下一步另冻有界新增development计划，不在原20开发上继续搜去均值强度，也不打开保留test为新方案选参。

061实际格式修复：8eb8c6e第一次审计在SDD纯数字ID上失败，原freeze/failure/claim/run日志全部保留。原CSV还有332条空valid flag，按旧045原规则其不为true，保持未验证，不提升为有效。新增仅支持ASCII纯数字或原前缀整数ID，以及空flag=false的格式适配；未知非空flag/负数/小数/Unicode数字仍拒绝。显式repair config钉住原config/claim/freeze/failure，继承所有输入/隔离/权利规则不变，只准audit-repair-started一次，禁止重置原claim/泛化修复或换目录再跑；未产出原轮容量结果，不冒称首轮成功。


## E36：MUS-062 外部人写来源审计与六组补充开发计划（2026-11-01）

正常TLS捕获WikiMuTe固定Zenodo10223363原all.csv（官方MD5）、YouTube8M-MusicTextClips固定Zenodo8040754原license/readme/train.csv（官方MD5），WikiMuTe/MuChin官方GitHub commit与准确commit文档、WikiMuTe论文/示例代码。私有持久32MiB body预记账，每URL最多一次、失败保留不重置；本轮13文件约5.08MB，预记20MiB，无音频。来源正文原件只私有；CSV投影仅读file/pageid/audio_url/page_url和video_id/start/end，原caption/aspects/text等语义正文不显示/提取/编码，项目封存test不打开。WikiMuTe all为未按跨模态分数筛选版，不用filtered_sf/mc作为独立人工真值；论文表明其human web文本由DistilBERT提取，非逐clip直接人工确认。YouTube8M采用原Adobe研究许可，不沿用二手CC标签；视频ID与10秒偏移交集分开，不假设音乐作者或音频权利。MuChin仅官方卡限制，未取中文描述/音频或自动翻译。

外部来源当前未满足直接人工clip/逐曲权利/作者作品隔离前提，仍保持原库和模型。为推进有限的新覆盖，本轮另冻六曲source-only development补充计划：从061准确已发布8候选/6全局credit组件及原固定SDD身份/有效标记，按seed MUS-062-unused-SDD-six-components-v1的SHA256(seed+换行+track_id)每组件取最低1首，不看正文/模型或描述条数选择；组内余2不作失败后自动替换。要求6组/6作品/6官方SHA、与旧140录音不交叉，保留原BY/BYSA、30–600秒、旧全部关系排除和封存20完整关系。061历史“未选择/不足新20”结果保持，062仅单独设计六曲小补充，不外推正式效果验收或新独立大样本测试。

本轮源码/config/source与输入SHA在干净提交后freeze，持久audit claim后仅运行一次元数据审计/选择，禁止换目录重跑。新plan记录6身份/许可/官方路径及全部有效描述条数，不取caption正文/音频/特征或模型分数，不发布真实ID。后续另任务先冻结逐曲有界音频/完整EOF/官方SHA/PCM和隔离核验预算，再构造同首120秒/同原全文本视图。任何失败保留不按结果补选；完整文本256原词元证明或超限拒绝，不静默截断。

后续比较也先固定：仅identity与已存058的100曲全文本ridge，无新fit；候选池旧140+新6共146，新6按录音等权whole MRR差为主、R1/R5及segment为次、旧20 query在146池只作控制。模型W/hash在本轮pin但不加载；原20封存test/160判断不输入，6组只作小型development诊断，不称正式显著性或部署依据。本轮不执行这次比较；音频/编码与评分须在后续独立冻结任务实际通过后才有结果。

合成schema/URL/精确decimal区间/冲突与确定性组选择、独立原文件列投影和全部集合计数/固定六曲选择、实际重复保护与旧045–061全文件保护通过后才记完成。原版、全文本、identity、UI/Java/DB/main/B047卡不改，公开仅方法/聚合与证据hash。


## E37：MUS-063 六曲开发补充音频预检（2026-11-02）

只获取062冻结六曲，不读取新caption正文/编码/fit/质量评分或项目封存test音频。先核062原plan/hash/summary与已发布063输入pin；重算061全names credit闭包及已用/分配/封存排除，确认原8候选保持，再核选定6组/6作品/6官方SHA、7有效描述、原官方test身份、base/names作者标题/原路径、逐曲历史BY/BYSA原URI/notice、官方low路径和哈希。当前是固定历史metadata映射核验，不冒称在线当前权利或SDD 320kbps原字节一致证明，不把metadata时长当实际解码。

正式网络前在干净提交freeze源码/config/全部输入及NumPy/SoundFile/librosa/soxr/SciPy/Numba/llvmlite/certifi版本和py/so/dylib代码hash、libsndfile/OpenSSL，再创建任务级preflight claim。固定官方HTTPS单曲low文件，复用既有严格206/Range/表示validator/长度与逐曲SHA流程，单曲20MiB、全128MiB持久body先记账再read、1次/曲、无全归档/fallback/自动重试。任务claim禁止原目录或换目录重启、并发只允许一个成功领取；失败文件/收据/账本/claim保持，六个固定slot分别记录，必须6/6通过才有ready catalog，组内余2不替补。

解码复用65536实际EOF读法，源MP3 8k–192k/单或双声道/实际30–600秒，float32均值单声道与soxr_hq到48k、整数ceil长度，不信MP3 header估计裁掉或补出样本。实际时长和原metadata差<=2秒；全finite/非全零波形、首尾10秒/5秒hop边界和右侧补零核验，记录整曲及首min(120秒,实际EOF)的PCM SHA，实际view不越界。音频检验保持样本/原文件，不做音质/风格语义确认。

用旧60、043pilot20、045全140、057实际76的钉住同decoder PCM/音频SHA（296来源引用，允许旧素材自身重复引用）先建精确排除集，新6对旧和彼此都拒绝同bytes或同标准化PCM。这里不宣称不同编码/偏移/变速/翻唱的完整声学近重复检测，作者/作品闭包亦非穷尽别名证明；这些限制保持公开，不把未检测当无重叠。

本轮只落私有MP3/传输/完整EOF/片段收据、尝试清单与6/6 catalog。结尾复核所有源/config/runtime hash，不导入Torch/CLAP。公开聚合/证据SHA、合成传输/固定来源/边界/重复/失败保护检查、独立真实波形重解/全部传输与计数、同/新目录实际拒绝和旧045–062全文件保护。原源/全文本/权重/cache、141+160判断、原版/UI/Java/DB/main与B047卡保持；不导入Java或给用户新标注包。

6/6 ready仅表示可构建同视图特征，不是训练就绪/质量通过。后续另冻完整原7文本与同首120秒特征/CPU数值检查及062既定identity对已存100ridge/146池比较；不因本轮下载成败更改选曲、模型/主指标或旧封存20。

063执行一致性记录：生产7ce3c15首次六曲获取全部通过。首次独立程序改用32768帧读取时精确PCM SHA不同；对同一官方字节、固定65536协议的独立实现重解全部复现。32K/64K最大采样差6.329967e-5仅作诊断，不新增事后接受容差，也不改原音频/catalog或重跑生产。失败核查与分块诊断原件保留；旧/新精确PCM排除键只在冻结decoder/runtime/DSP和65536读取协议内比较，不是跨分块/decoder/编码版本的不变指纹。


## E38：MUS-064 六曲全文本特征与固定检索对照（2026-11-02）

只用062固定6曲/6组件/7既有有效人写描述与063已验官方音频。原完整UTF8文字与不截断token序列逐项相等；256预算溢出失败，不改写/截断/回退77。按冻结65536帧解码协议核完整EOF/PCM，再在首min(120秒,EOF)取first/mid/last10秒18窗。原048的140整曲/624窗/24query逐元素复用且typed consumer重新核验，合并146候选/642窗；不更改旧consumer允许的140类型。

原A严格checkpoint/047环境与offline cache、FP32/MPS/无autocast或fallback，音频batch3/文字batch6。全18新窗、6整曲聚合、7全文本均另CPU编码核maxabs/余弦1e-4；原长度<=77的新描述另核CPU77与256，不存在则明确不适用。源码/config/全部输入/模型/env先冻后encode claim，失败原件保留，任务级单attempt阻止换目录再编码。

另独立CPU NumPy进程只评identity与058已存100曲全文本ridge，不fit或搜参。主指标沿用062：新6录音宏whole MRR saved100减identity；新6 R1/R5与segment、旧20在146池的两mode控制分开全报，不合并26曲。旧20原140池对两模型两mode须精确复现058。录音bootstrap2000/seed20261102064，六组仅描述性区间；其他候选语义未判定，不作真实负例。评测也先冻结/持久claim，原目录和换目录禁重复；不因结果自动切换模型，identity保持。

无下载/新fit/保留20或160测试输入/新人工任务/云端GPU/部署。raw正文、身份、音频、向量、W与逐曲排名仅私有.local/a/mus064(700/600)，公开聚合/hash/方法。先快照旧045–063全部文件集合/hash，结束核原版/历史证据/模型缓存/B047原卡；B047批准不外推064。


## E39：MUS-065 Clotho人写训练候选容量（2026-11-02）

仅取Clotho官方固定Zenodo4783391/v2.1的LICENSE、三split metadata与development captions；5文件各2MiB/总16MiB持久预记、每URL一次、正常TLS/官方MD5/本地SHA，无音频/val或eval正文/模型。先捕获固定来源，再提交统计源码与config/hash，持久单audit claim后实际统计；失败保留不换目录隐式重跑。

只按来源keywords选择：固定whole-tag标准化（casefold，把非ASCII字母数字转空格并合空格），候选tag集合为music,musical,piano,guitar,violin,cello,orchestra,orchestral,saxophone,trumpet,trombone,clarinet,flute,drum,drums,drumming,percussion,accordion,ukulele,synth,synthesizer。不按caption语义、模型相似度或此前dev分数筛。显式区分music/musical与仅乐器tag的容量，标签不证明实际是完整音乐或对应caption涵盖音乐。

按三官方split全部元数据的同Freesound sound ID或同manufacturer/uploader建立闭包；跨split组件双边排除，不搬移官方split或把metadata身份闭包等同全部作者/作品真值。同sound不同区间/文件不算独立录音。沿用BY/BY-SA音频URI规则，保留原URI/未知家族，caption自有Tampere许可独立核对，仅本地实验非商业研究候选，不能把音频CC当captionCC或产品授权。development每文件恰好5个非空caption，计数不读取/显示正文语义，不截断/重写；val/eval正文不取。

公开只聚合/hash/方法，私人目录700/600保存原元数据、源URL/许可、计数绑定的候选清单。只输出metadata候选，不声称audio_ready/training_ready或独立benchmark。检查当前CLAP是否曾用Clotho选checkpoint；未知的跨来源作者/作品/声学重复与预训练交集保留。无新fit/模型输入/音频归档/商用部署/人工任务/保留test/UI/DB/main；旧045–064集合/hash与原版/B047卡保持。

065另捕获CLAP官方README固定Git commit1fd4c37df5ffbfcfbad5415c170bc66cf94c9994（单文件2MiB预记，总12MiB<16MiB），只核当前A命名/Clotho与AudioCaps用于checkpoint选择的原说明，不把它当精确训练成员证明。该源同样绑定本地SHA/config。

065显式格式修复：首轮def5a6c被19条官方sound_id=Not found/sound_link=NA拒绝，run-01/原audit claim与失败保持。仅接受该成对marker为未解析来源，不合并所有缺失ID，保留各自uploader参与闭包且永不进候选；其他坏ID/错配URL仍拒绝。原输入/tag/rights/模型零操作不变；另repair config绑定原config/claim/failure SHA，独立repair-started单attempt，原claim不能重置，非按结果换规则。

065第二显式修复：f66fbf8首次repair被2条manufacturer与URL uploader的重音拼写不一致拒绝，repair-01/claim/失败保持。不静默去重音认同一人；保留原字段及URL的两个uploader键作保守闭包边（只会扩大排除），该行不能进候选；已知sound ID仍保留其闭包边。除19条缺失与2条不一致外仍严格拒绝坏host/URL ID。已单独核所有原文件无其他schema/offset/duplicate/caption-key缺失；v2 config绑定两次原失败链，repair-v2-started单次，不改tag/rights/split/输入或按成绩选择。

065出处解析修复：0b88fe6的v2在原README证据核查失败，程序错误要求checkpoint选择说明和四分数公式处于单行；准确固定来源实际为相邻两行。保留第三次失败/claim，只修相邻两行解析，不改Clotho数据/选择/统计规则；测试已覆盖同一行、相邻两行和断开无关段落拒绝，另直接核原已pin README。v3 config绑定此前全部链/新repair-v3单次，不重置任何旧claim、不增加来源或模型评分。
