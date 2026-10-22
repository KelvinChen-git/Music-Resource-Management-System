# SONORA · Music Discovery Platform

## 当前开发入口：Sonora 副本

用户已确认 MUS-018 设计。MUS-019 将新版界面接入真正的 Vue 应用，后续前端开发使用 **`Music-Sonora` 工作目录；当前增量分支 `feat/MUS-025-listening-review`**。原 `Music-Resource-Management-System` 目录停留在 `design/MUS-018-ui-preview@f3b0da1`，其旧 `web/` 与原 5173 页面作为保留版，不在两个目录同时修改前端。

新版本机入口：**http://127.0.0.1:5175/music**。它通过代理连接现有 A 后端 8080，使用原登录账号和已有曲库；本次没有复制或迁移数据库，也没有启动另一个 Java 服务。原服务仍是 MUS-014 运行版本，不把较新源码当作已运行版本。

在本副本 `web/` 目录开发：

```sh
VITE_DEV_PORT=5175 VITE_PROXY_TARGET=http://127.0.0.1:8080 npm run dev
```

稳定浏览构建版本（先停止占用 5175 的本副本进程）：

```sh
npm run build
VITE_DEV_PORT=5175 VITE_PROXY_TARGET=http://127.0.0.1:8080 npm run preview -- --host 127.0.0.1 --port 5175 --strictPort
```

使用 `.nvmrc` 的 Node 22；本机工具包位于相邻 `.music-tools/node-v22.23.3-darwin-arm64/bin`。首次安装仍用当前 lockfile 的 `npm ci`，不升级依赖。备份精确源码为 `f3b0da1e97113d28c81aa49be61c5cbcc49eebce`，此提交内的 `web/` 就是原版；新分支也保留该祖先。

新 `/music` 是封面曲库；旧完整资源管理在 `/manage/music`；上传、分类、标签、回收站、个人资料及管理员入口沿用原组件和权限。收藏与播放历史仅保存在本浏览器，按账号 ID 分隔，未实现跨设备同步。播放器使用现有 JWT 媒体 helper 获取音频，页面切换继续播放；退出或换账号清理音频和队列。曲库按后端每页 20 首加载，封面区域分批展开；风格与排序只作用于已加载曲目，页面会提示未全部加载的情况。

验证与边界见 [MUS-019](docs/verification/MUS-019.md)。下文原有后端/双账号基线文档仍保留，不意味着本副本已配置了第二套数据库。


保留 Java / MySQL / Vue 管理系统，增量开发多模态音乐检索与片段定位。

**当前面向浏览器的多模态检索尚未实现。** MUS-022已补上20首真实MP3的离线解码、933片段及固定CLAP候选排序；尚无人工相关性验收或线上检索接口。已建立MUS-001本地功能基线；模型效果、正式索引、研究集标注和性能仍需验证。2,000 首、约 70,000 片段、120 查询、300ms P95 和 10% 提升均不是现有成果。

新会话按顺序阅读 [AGENTS](AGENTS.md) → 本文件 → [PROJECT](docs/PROJECT.md) → [CONTRACTS](docs/CONTRACTS.md) → [STATUS](docs/STATUS.md)。当前集成负责人为账号 A；由 A 串行维护 STATUS。

两账号固定交接见 [collaboration/README.md](docs/collaboration/README.md)：开始时 `python3 scripts/collab.py sync --account a`，结束提交后 `python3 scripts/collab.py publish --account a`，B 用 `b`。采用每账号独立交接分支，保留任务分支 / 精确 SHA，不自动合并。A/B 远端 feed 已可互读；A 自动发布仍受连接写权限 / 受管终端网络阻塞，不能声称双方全自动推送均通过。

## 代码与验证边界

| 路径 | 当前能力 |
|---|---|
| `music/` | Java 17、Spring Boot 3.4.4、MyBatis Plus 3.5.5 与部分 JPA；MySQL、Druid、Caffeine、JWT、mp3agic |
| `web/` | Vue 3、Pinia、Axios、Element Plus、Vite 6；ES modules JavaScript |
| `music/src/main/resources/db/baseline/` | MUS-001 的空开发库初始化；历史同级 SQL 不作为顺序迁移 |
| `scripts/dev.py` | 生成独立 slot 配置；拒绝覆盖已有配置；只初始化空开发库 |
| `scripts/smoke.py` | 合成 MP3 的旧业务 API 流程验证；不是检索评测或听感验证 |
| `docs/` | 当前事实、建议契约、任务边界与交接证据 |
| `services/audio-search/` | MUS-002合成探针与MUS-022真实小语料解码/候选排序；非线上检索服务 |

JWT 账户、分类标签、筛选、分片上传、元数据、审核、播放下载与回收站有源码。MUS-001 实跑覆盖注册登录、标签及分类筛选、部分上传续传请求、合并、MP3 元数据、Range 媒体响应、软删除及恢复。未覆盖全部管理 / 审核 / 邮件分支、浏览器人工试听或重启后的上传恢复。

不能将评论、点赞、收藏、播放历史服务端持久化、完整 Swagger 或生产部署当作已验证能力。

## 一次启动并验收前后端

在普通本地终端、自己的独立 checkout 根目录运行 `python3 scripts/baseline.py --slot a --keep-running`；B 在另一 checkout 用 b。原生 MySQL、Java / Vue、两条 smoke 流程和私有结果文件由入口串联。已有库不清空。用户已在普通 macOS 终端跑通 A/B 两套独立工作目录：各 107 项 Java 测试、前端 build、直连 / 代理各 13 项通过；受管终端自身仍限制回环，不代表限制已解除。详见 [MUS-010 验证与启动步骤](docs/verification/MUS-010.md)。

## 开发启动

要求：JDK 17、Node **22.23.3**（[.nvmrc](.nvmrc)，本轮 npm 10.9.9）、Python 3.9+、MySQL **8.0.41**。Maven wrapper 指向 3.9.9。首次下载依赖需要联网。

以下从仓库根目录执行，适用于自己的独立 clone：

```bash
python3 scripts/dev.py setup --slot a
. .local/a/env.sh
# 有 Docker Compose v2 时启动独立 MySQL；本轮仅原生 MySQL 路线实跑。
docker compose --env-file .local/a/compose.env -p music-a -f compose.dev.yml up -d --wait
python3 scripts/dev.py init-db --slot a
cd music
sh ./mvnw -B -ntp test
sh ./mvnw spring-boot:run
```

另一个终端：

```bash
. .local/a/env.sh
cd web
npm ci
npm run dev
```

再用一个终端验证后端及开发代理：

```bash
python3 scripts/smoke.py --slot a
python3 scripts/smoke.py --slot a --via-proxy
```

原生 MySQL、slot B、启动顺序、配置字段及限制见 [development.md](docs/development.md)。未安装 Docker 的机器不能直接运行上面的 Compose 命令；不能把配置存在解释为容器路线已验收。

## 配置与安全边界

- `application-local.yml` 已提交，必须显式启用 local profile；setup 生成的 shell 环境会启用它。`application.yml` 仍不提交，已有私有配置不会被覆盖。
- local 后端只绑定 127.0.0.1，context path 为 `/api`。Vite 将相对 `/api` 原样转发，读取 `VITE_PROXY_TARGET`；`VITE_DEV_PORT` 冲突即失败。
- 配置、密钥、上传、数据库和索引放在被 ignore 的 `.local/<slot>/`。每账号独立 clone，不能共享写入数据库、上传或索引。
- `VITE_API_BASE_URL` 仅是旧头像 helper 的非空开关；该 helper 实际返回相对 `/api/uploads/...`。它不控制 Axios baseURL 或代理。
- **媒体权限本机实跑通过**：MUS-011 已实现三入口 / ZIP 授权与 no-store、受控头像及前端 JWT；本机 A/B 隔离环境各通过 144 项真实媒体权限矩阵，直连 / 代理匿名入口均为 401。B 账号独立审核待完成。MUS-012 已加入上传所有权及头像绑定检查，308 项 Java / 22 项 Python 测试通过；两套本机新服务各通过 65 项真实上传权限检查和 144 项媒体矩阵，公开 discovery 继续阻断。历史匿名 200 证据及当前验收边界见 [MUS-011](docs/verification/MUS-011.md)。
- 初始化 SQL 仅适用于空开发库。没有提供既有数据库迁移，不向已有库运行历史 dump。

## 本轮验证

| 检查 | 2026-10-19 结果 |
|---|---|
| `npm ci`、`npm run build` | 通过，保留 lockfile；bundle >500kB 为非阻塞警告 |
| `sh ./mvnw -B -ntp test` | 9 类、89 tests，0 failures / errors / skipped |
| 原生 MySQL 空库初始化与 local 启动 | 通过；11 表；非空库重复初始化被拒绝 |
| 后端直连 / Vite 代理 smoke | 各 13 项功能检查通过；Range 实际返回 206 |
| 两 slot 配置 / strictPort | 配置分离；B 为 8081 / 5174 / 3308；端口冲突拒绝启动 |
| CLAP 文本 / 音频 CPU 编码 | 固定音乐 checkpoint 已通过合成输入可行性检查；实际 512 维；9 项预处理测试通过 |
| Compose、真实邮件、全部浏览器交互、检索质量 | 未验证 |

默认 Surefire 已从仅 `*ServiceImplTest` 改为全部 `*Test.java`，并要求非空选择。可用 `-Dtest='*Test'` 对照。前端无 `test` / `lint` / `typecheck` script。

原始源码默认测试实跑 75 tests 有 3 errors；修正失效 fixture / mock 后才获得上述结果。旧会话 Maven 网络阻塞不再描述为本轮状态。详情见 [验证记录](docs/verification/MUS-001.md)。

源码仍有非阻塞 Druid 1.2.11 POM / JSqlParser count 优化警告。MUS-009 本地任务已修复分片重复写库和哈希未校验，保留旧接口；当前全量 Java 107 tests 通过，真实数据库 / 并发 / 进程重启验收因环境阻塞待补，不属于上表历史 89 项证据。见 [上传完整性验证](docs/verification/MUS-009.md) 与 [STATUS](docs/STATUS.md)。

MUS-002 的准确 checkpoint、实际环境与限制见 [model-spike.md](docs/model-spike.md)。真实音乐语料与效果验收仍缺，discovery-v0 尚未冻结。


**独立审核补充：** B在d7c9faa发现旧硬删除、管理员createUser头像和迁移结构保护缺口。MUS-013源码已修复，Java317 / Python28通过；旧服务中的R1/R2已复现，两套本机修复后HTTP11项及独立临时库8项均已通过，B增量复核待完成。详见 [MUS-013](docs/verification/MUS-013.md)，公开服务仍保持阻断。

## MUS-012 上传所有权升级

新上传按当前数据库账号保存 `owner_user_id`。文件列表、MD5 秒传 / 续传、详情、分片 / 合并 / 删除与元数据绑定只处理自己的上传；不能登记他人的图片为头像。已有音乐的媒体读取继续按审核状态控制。

V001 保留不变，V002 为加列与索引迁移。旧上传保留 NULL owner 并隔离，不能自动认领；已有关联音乐仍按媒体策略读取。需要继续旧上传时重新上传新记录。删除自有未引用上传只做逻辑删除，物理清理待后续任务；音乐 / 头像引用会阻止删除。

2026-10-19 两套本机环境已重启并完成验收；以后需要启动时，在各自 checkout 中运行：

```bash
# A checkout
python3 scripts/baseline.py --slot a --migrate-upload-ownership --keep-running
```

```bash
# 本机独立 B checkout
python3 scripts/baseline.py --slot b --migrate-upload-ownership --keep-running
```

该迁移选项只接受隔离开发配置，已升级的库重复运行不会回填 owner 或重建表；空库自动初始化到 V002。新 baseline 会执行原功能与媒体矩阵，再执行上传所有权真实回归。报告与限制见 [MUS-012](docs/verification/MUS-012.md)。两个本机槽不代表 B 账号已独立审核。


MUS-014 基线新增18项真实上传故障检查，并自动完成“部分上传 → 停止本次后端 → 新后端就绪 → 续传与并发合并”检查。旧基线若仍在运行，先在各自终端按 Ctrl+C，再用上述命令启动。无需手动执行prepare/resume，也无需复制私有状态；失败状态会保留以便定位，不自动覆盖。当前修复的317 Java / 45 Python通过；2026-10-19 23:18两套普通终端基线已通过真实并发计数回归与跨JVM续传（各18故障、prepare5、resume11），服务保持运行，无需再次重启。见 [MUS-014](docs/verification/MUS-014.md)。


MUS-014已收到B独立复核的范围内批准及其真库/跨JVM运行补证；详见[接收记录](docs/verification/MUS-014-B-acceptance.json)。MUS-015进一步补上同值头像请求重新校验，Java320通过，新版本真实运行尚未验收；当前服务仍保持已验收的MUS-014版本，见[MUS-015](docs/verification/MUS-015.md)。


## 演示音乐

A环境已导入20首Jamendo CC BY完整音乐。打开 http://127.0.0.1:5173/demo-catalog ，侧栏Demo Catalog可查看作者、来源和许可，并进入Music播放。另列Post Malone/Drake各10条资料与官方链接，无其完整音频。本机普通演示账号凭据在忽略文件.local/a/music-catalog/demo-account.json；本次内置浏览器已登录。

重复导入验证：`python3 scripts/import_demo_music.py --slot a --count 20`。Client ID、账号和音频缓存仅存.local，新环境需自己的配置；不把Git清单当作已拥有本地音频。详见[导入验收](docs/verification/MUS-016.md)。


管理员用户编辑的MUS-017候选约定：头像省略或null保持，空字符串清空，非空路径校验；按提交字段局部写入，避免旧头像/安全字段回写。Java323通过，尚待新版本真库验收；现有服务未重启。详见[MUS-017](docs/verification/MUS-017.md)。

MUS-020 已接收B的两项request_changes并作最小修复：手机长标题列表明确允许信息列收缩；管理员按用户名/邮箱查音乐改至 `/manage/music`。复核与运行边界见 [MUS-020](docs/verification/MUS-020.md)，新B增量卡按准确实现SHA派发。


MUS-017的B限定批准已正式接收，C1关闭；E1空对象与E2其他用户写入口风险由MUS-021继续处理。MUS-021源码使用独立管理员输入DTO及六入口专属写列，默认/显式Java测试各332通过；B限定批准已接收，其独立默认332 Java和24项隔离真库增量通过。现有演示后端仍MUS-014，本轮不重启服务或迁移数据。见 [MUS-021](docs/verification/MUS-021.md)。


MUS-022离线实跑：20首MP3、933候选片段、8英文文字和3库内参考完成512维编码及整曲/片段精确排序；23项测试和工件校验通过。51个探索标注对仍全null，未计算质量或P95、不冻结discovery-v0，生成向量仅ignore目录。命令/证据/限制见 [MUS-022](docs/verification/MUS-022.md)。现有网页/演示后端与原版备份保留。


MUS-016首次B审核已返回request_changes。MUS-023源码补上pending/confirmed账号恢复、缓存证明完整绑定与canonical公开来源/目录链接；62 Python/8链接检查及前端构建通过，新的真HTTP/SQL增量已获B限定批准。原版备份/既有20首证明及MUS-022结果保留，没有重跑真实A导入或升级后端。见 [MUS-023](docs/verification/MUS-023.md)。

MUS-023已接收B限定批准，关闭MUS-016对应R1/R2/条件性R3；B真实本地HTTP/SQL补证与提供方替身边界见[接收记录](docs/verification/MUS-023-B-acceptance.json)。MUS-024已实现本地探索标注包生成/校验，17新增检查及全离线40项通过，实际8查询51对全null；B工具限定批准已接收，原UI布局与演示后端保持。使用步骤见[MUS-024](docs/verification/MUS-024.md)。

MUS-025新增[本机试听审阅入口](http://127.0.0.1:5175/research/review)：用标注包归属账号导入`.local/a/mus024/review-pack.json`，现有JWT媒体与完整SHA/字节验证后试听片段，人工评分/区间、分账号本机草稿及JSON导出。21项helper检查/build和本机浏览器增量通过，B独立复核待完成；真实51条仍全null，无质量结论。原Sonora布局/管理页/后端保留，使用步骤与限制见[MUS-025](docs/verification/MUS-025.md)。
