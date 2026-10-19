# Music Resource Management System → Music Discovery Platform

保留 Java / MySQL / Vue 管理系统，增量开发多模态音乐检索与片段定位。

**当前多模态检索尚未实现。** 已建立 MUS-001 本地功能基线；模型、索引、小语料、质量和性能指标仍需逐项验证。2,000 首、约 70,000 片段、120 查询、300ms P95 和 10% 提升均不是现有成果。

新会话按顺序阅读 [AGENTS](AGENTS.md) → 本文件 → [PROJECT](docs/PROJECT.md) → [CONTRACTS](docs/CONTRACTS.md) → [STATUS](docs/STATUS.md)。当前集成负责人为账号 A；由 A 串行维护 STATUS。

两账号固定交接见 [collaboration/README.md](docs/collaboration/README.md)：开始时 `python3 scripts/collab.py sync --account a`，结束提交后 `python3 scripts/collab.py publish --account a`，B 用 `b`。采用每账号独立交接分支，保留任务分支 / 精确 SHA，不自动合并。当前远端写权限与终端网络阻塞，首次发布未完成；不能声称已启用自动互通。

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
- **旧媒体权限尚未修复**：本轮确认 pending 媒体、静态上传和软删除后的媒体仍可匿名读取。local 的回环地址不是应用级鉴权修复；对外接入 discovery 前必须治理这些路径。
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

源码仍有非阻塞 Druid 1.2.11 POM / JSqlParser count 优化警告，以及分片重复持久化日志；本轮未扩大为依赖或上传服务全面重构。精确后续任务见 [STATUS](docs/STATUS.md)。

MUS-002 的准确 checkpoint、实际环境与限制见 [model-spike.md](docs/model-spike.md)。真实音乐语料与效果验收仍缺，discovery-v0 尚未冻结。
