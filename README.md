# Music Resource Management System

现有 Java / Vue 音乐资源管理应用，正在规划增量升级为 **Music Discovery Platform：多模态音乐检索与片段定位**。

**当前只有管理系统代码；CLAP、片段向量索引、Python 检索模块和检索质量结果尚未实现。** 文档区分源码现状、建议契约和未来目标，避免将规划当作交付。

## 新协作者入口

先读 [AGENTS.md](AGENTS.md)，再读 [项目路线](docs/PROJECT.md)、[接口与数据契约](docs/CONTRACTS.md)、[任务状态与交接](docs/STATUS.md)。源码核对基线：`b81f57c79e1cefb96c2055df4ae438aa24fb475c`（2026-10-19）。后续会话以实际 HEAD 和 STATUS 为准。

## 现有源码

| 能力 | 代码入口 | 核验范围 |
|---|---|---|
| JWT 登录、注册、账户管理 | `music/src/main/java/com/taffy/music/controller/AuthController.java`、`UserController.java` | 静态确认；邮件和数据库流程未联调 |
| 资源列表、组合筛选、元数据、审核 | `MusicResourceController.java`、`service/impl/MusicResourceServiceImpl.java`、`resources/mapper/MusicResourceMapper.xml`（均在 `music/src/main/` 下） | 静态确认 |
| 文件 MD5 检查、分片、续传、合并 | `FileUploadController.java`、`web/src/views/UploadView.vue` | 静态确认；不是音频内容去重 |
| 分类、标签、回收站与清理 | 对应 controller / service、`web/src/views/` | 静态确认 |
| 音频播放、文件下载、导出 | `MusicResourceController.java`、`web/src/components/PlayerBar.vue` | 静态确认；访问策略存在待核验差异 |
| Java 测试源码 | `music/src/test/java/` | 已有测试；本次未能执行到测试阶段 |

不要将原说明中的“评论、点赞、收藏、播放历史服务端持久化”、完整 Swagger 配置或生产部署状态视为当前已验证能力；核对代码后再补充。播放计数不等于播放历史。

### 技术与目录

| 目录 | 用途 |
|---|---|
| `music/` | Java 17、Spring Boot 3.4.4；MyBatis Plus 3.5.5 与 JPA 并存；MySQL、Druid、Caffeine、JWT、mp3agic |
| `music/src/main/resources/db/` | 多份历史 SQL；不是已验证的顺序迁移 |
| `music/src/test/java/` | JUnit / Mockito 等测试 |
| `web/` | Vue 3、Pinia、Vue Router、Axios、Element Plus、Vite 6；ES modules JavaScript |
| `docs/` | 目标、契约、协作状态 |

尚无 Python 模块、容器编排、检索 CI 或可执行的模型服务命令。后续新增路径需在文档中标明 implemented / proposed。

## 环境准备

以下为本地开发配置指导，**不代表已通过后端启动验收**。先完成 STATUS 中的 MUS-001，建立可重复的数据库初始化与配置。

- JDK 17；Maven wrapper 指向 Maven 3.9.9。首次运行需要能访问 Maven Central。
- MySQL 8；历史 SQL 使用 `utf8mb4_0900_ai_ci`。
- Node.js 22 LTS 建议作为团队统一版本（待 MUS-001 锁定）；本次前端构建使用 Node 24.19.0、npm 11.9.0，通过现有 lockfile 安装。
- 邮件功能需要本地 SMTP 接收器或明确授权的 SMTP 测试账户。当前没有随仓库提供邮件测试服务。
- Python / FFmpeg / GPU 暂非运行现有前端的前提；模型实验环境在 MUS-002 中锁定。

### 前端

```bash
cd web
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

默认开发地址：`http://127.0.0.1:5173`。构建和预览：

```bash
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

预览仅服务静态构建；Vite 开发代理不等于部署反向代理，完整 API 联调仍需单独配置。

`web/src/utils/request.js` 使用相对 `/api`，`web/vite.config.js` 将 `/api` 原样代理到 `http://localhost:8080`。本地后端应配置 context path `/api`；controller 本身没有再加 `/api`。不要把路径配置成 `/api/api/...`。

`web/src/utils/url.js` 还会检查 `VITE_API_BASE_URL`；若头像路径需要它，可在被 ignore 的 `web/.env.local` 写入 `VITE_API_BASE_URL=http://localhost:8080`。它目前不控制 Axios baseURL，也不改变 Vite proxy target。

### 后端本地配置

`music/src/main/resources/application.yml` 被根 `.gitignore` 排除，没有提交。可以自行建立该文件，按下列**候选配置**起步；值、schema 兼容性与启动结果由 MUS-001 验证。

```yaml
server:
  port: 8080
  servlet:
    context-path: /api
spring:
  datasource:
    druid:
      url: jdbc:mysql://127.0.0.1:3306/music_dev_a?useUnicode=true&characterEncoding=UTF-8&serverTimezone=UTC
      username: ${MUSIC_DB_USER}
      password: ${MUSIC_DB_PASSWORD}
      driver-class-name: com.mysql.cj.jdbc.Driver
  jpa:
    hibernate:
      ddl-auto: none
    open-in-view: false
  sql:
    init:
      mode: never
  servlet:
    multipart:
      max-file-size: 32MB
      max-request-size: 40MB
  mail:
    host: 127.0.0.1
    port: 1025
    username: ${MUSIC_SMTP_USER:}
    password: ${MUSIC_SMTP_PASSWORD:}
mybatis-plus:
  mapper-locations: classpath*:/mapper/**/*.xml
jwt:
  secret: ${MUSIC_JWT_SECRET}
  expiration: 86400000
upload:
  path: ${MUSIC_UPLOAD_PATH}
  temp-path: ${MUSIC_UPLOAD_TEMP_PATH}
  allowed-types: mp3,jpg,jpeg,png
  chunk-size: 5242880
```

说明：`DruidConfig` 绑定的是 `spring.datasource.druid`；JWT 使用 HS512，秘密值需至少 64 字节；`jwt.expiration` 单位为毫秒。上传路径必须是可写绝对路径。multipart 示例约束单次 HTTP 请求，不代表整个分片文件最大大小。

启动前在当前 shell 设置上述变量，使用自己的数据库账户和本地目录。可用 `openssl rand -hex 64` 生成本地 JWT secret；不要把真实值提交到 Git 或交接消息。邮件示例需有监听 1025 的本地 SMTP 服务，否则邮件流程不会成功。

### 数据库前提

**不要直接按文件名依次执行 `db/*.sql`。** 静态发现：

- `music_db.sql` 有先向 `recycle_bin_settings` 插入、后建表的顺序问题；该 INSERT 还涉及最终建表中不存在的通知字段。
- `schema.sql` 中部分外键使用 `users.user_id` / `music_tags.tag_id` 等，与主导实体和 dump 命名不一致。
- `MusicResources.additionalMetadata` 实体声明 JSON，dump 使用 TEXT；不能依赖自动 DDL 静默修补。
- 其他 SQL 可能包含重复建表 / 删表 / ALTER；没有 Flyway / Liquibase 迁移链。

MUS-001 必须在新建的隔离开发库上整理并验证初始化入口，禁止对已有数据盲跑这些脚本。本次仅更新文档，没有修改 SQL。

在已有经过验证的开发库、配置和环境变量后，使用：

```bash
cd music
sh ./mvnw -B -ntp test
sh ./mvnw spring-boot:run
```

wrapper 当前未设 executable bit，因此使用 `sh ./mvnw`；不要写成 `sh mvnw`。Windows 使用 `mvnw.cmd`。

## 检查与已知基线

| 检查 | 当前状态（2026-10-19） |
|---|---|
| `npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=0 --fetch-timeout=30000`（`web/`） | 通过；使用现有 package-lock |
| `npm run build`（`web/`） | 通过；Vite 报告部分 bundle 超过 500kB 的非阻塞警告 |
| `sh ./mvnw -B -ntp test`（`music/`） | blocked：Maven Central 域名解析失败，未进入编译 / 测试 |
| 后端启动、数据库、邮件、登录和上传联调 | 未执行；需本地配置与可靠 schema |
| 新检索功能和效果 | 未实现 / 未测量 |

默认 Surefire include 为 `**/*ServiceImplTest.java`，会遗漏如 `MusicServiceTest`、`ChunkCacheServiceTest`。需要检查全部 `*Test` 时另执行 `sh ./mvnw -B -ntp -Dtest='*Test' test` 并记录结果；不把“默认测试通过”解释为全部测试通过。前端暂未定义 `test` / `lint` script。

其他待核验项：上传页实际检查 10GiB，原文档写 20MB，后端限制又依赖本地配置；`/{id}/file` 有 `@Anonymous`，不能从前端禁用按钮推出后端已执行审批限制；标签 XML 当前是任意标签匹配。详情见 CONTRACTS / STATUS。

## 两账号协作

- 两个账号分别授权访问同一仓库，使用独立 clone / worktree；聊天记忆不作为同步渠道。
- 使用任务分支，推送后通过分支和提交编号交接。工作区有修改时不要直接 pull 或切分支。
- 当前集成负责人串行维护 STATUS；一个任务一个写入方；共享 API / schema / lockfile 先协调。
- 同机第二套后端例如 8081、前端 5174、数据库 `music_dev_b`、独立上传目录。当前 Vite target 硬编码 8080，仅改后端端口不够；需在后续配置任务中参数化，或使用不同设备 / 隔离环境。
- 新索引按环境和版本分目录。生成媒体 / 权重 / 索引前先补齐 ignore 规则。

下一步：在 [STATUS](docs/STATUS.md) 认领 MUS-001，先恢复可重复的旧系统基线，再建立小语料检索闭环。
