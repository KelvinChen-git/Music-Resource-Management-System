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
- 文件接口有 `@Anonymous`；`getMusicResourceById` 未额外判断审核或删除状态，静态 `/uploads/**` 也被排除 JWT。MUS-001 实跑确认 pending 媒体、静态上传和软删除后的媒体均能匿名 HTTP 200 读取；旧文件路由真实 Range 请求返回 206。完整权限矩阵仍未成立。
- `createMusicUrl` 使用 fetch 获取 Blob、没有自动走 Axios JWT；不能假设统一拦截器会保护这条调用。
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

## F. 契约变更

MUS-002 冻结时记录版本、日期、负责人与 fixtures 位置。修改字段、时间单位、可见性、索引身份或错误语义前：列出生产者 / 消费者，更新本文及 fixtures，协调两个任务，再实现与验证。旧接口与新契约存在差异时显式适配，不静默更改旧用户流程。

MUS-002 候选实跑补充：固定 music_audioset checkpoint、HTSAT-base / no fusion，实际文本与音频投影输出 512 维；这仅适用于该准确 checkpoint / SDK 组合。探针显式零填充以避开 SDK 默认 repeatpad；尚未用真实音乐证明效果，D 部分规则及 discovery-v0 继续为 proposed，不凭这次编码检查宣称契约已冻结。
