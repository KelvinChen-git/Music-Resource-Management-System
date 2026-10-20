# Music Resource Management System → Music Discovery Platform

保留 Java / MySQL / Vue 管理系统，增量开发多模态音乐检索与片段定位。

**当前多模态检索尚未实现。** 已建立 MUS-001 本地功能基线；模型、索引、小语料、质量和性能指标仍需逐项验证。2,000 首、约 70,000 片段、120 查询、300ms P95 和 10% 提升均不是现有成果。

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
| `services/audio-search/` | MUS-002 离线 CLAP 可行性探针，非线上检索服务 |

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
