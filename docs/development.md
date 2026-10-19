# 可重复本地开发（MUS-001）

这是空的隔离开发环境入口，不是生产部署或旧数据库迁移。所有命令从独立 clone 根目录开始；账号 A / B 不使用同一个工作目录。

## 版本与前提

本轮实跑：macOS arm64、Temurin JDK 17.0.20.1、Maven 3.9.9、Node 22.23.3、npm 10.9.9、MySQL Community 8.0.41、Python 3.12.10。`.nvmrc` 固定 Node；Java 17、Boot 3.4.4 和现有前端 lockfile 保留。下载 runtime 到私有目录不构成跨机器安装步骤；另一机器需先准备这些工具。

`sh ./mvnw` 可用于 wrapper 没有 executable bit 的仓库。不要让 JAVA_HOME 指向 JRE；需要 JDK。Windows 的 Maven 命令是 mvnw.cmd，生成的 env.sh 需要 POSIX shell（例如 Git Bash / WSL），未验收原生 PowerShell 路线。

## 每个 clone 初始化一次配置

```bash
python3 scripts/dev.py setup --slot a
. .local/a/env.sh
```

slot B 将命令中的 a 改为 b，并在另一 clone 执行。

| 内容 | A | B |
|---|---|---|
| Java | 127.0.0.1:8080 | 127.0.0.1:8081 |
| Vite | 127.0.0.1:5173 | 127.0.0.1:5174 |
| MySQL TCP | 127.0.0.1:3307 | 127.0.0.1:3308 |
| schema / application user | music_dev_a | music_dev_b |
| Compose project / volume | music-a / music-a_mysql-data | music-b / music-b_mysql-data |
| SMTP receiver（自行启动） | 1025 | 1026 |
| 文件 / 密钥 / 索引 | 本 clone 的 .local/a/ | 另一 clone 的 .local/b/ |

配置写入 .local/<slot>/config.json、env.sh 和 compose.env，权限为 0600，目录 0700。数据库密码、root 密码和 HS512 JWT secret 每次随机生成；两个 clone / slot 不复用。重复 setup 拒绝覆盖整个现有 slot；不会 reset、删数据或自动换密钥。目录中发生部分创建失败时需先检查，不应自动删除。

每个启动终端都 source 对应 env.sh。配置变更后需同步 config.json、env.sh 和 compose.env；不要在已初始化数据库后随意更改密码，文件修改不会自动修改数据库账户。`VITE_*` 会进入前端配置，只放端口 / URL，不放秘密。

## 路线一：Docker Compose v2（配置已建立，本轮未实跑）

```bash
docker compose --env-file .local/a/compose.env -p music-a -f compose.dev.yml up -d --wait
python3 scripts/dev.py init-db --slot a
```

先等待健康检查，再初始化。MySQL 的初始 database / user 来自 slot；命名卷不绑定另一个 clone 的磁盘目录。只发布回环地址。已有 Compose 卷不会因 env 文件改变而重设账户。不要使用同一个 project name 启动两个 clone。

普通停止可执行：

```bash
docker compose --env-file .local/a/compose.env -p music-a -f compose.dev.yml down
```

不加 -v，保留数据库。此任务没有提供清空或覆盖数据库的自动命令。

## 路线二：已有原生 MySQL（本轮实跑）

使用自己的隔离 MySQL 8.0.41 实例，按 config.json 中的 MUSIC_DB_HOST / PORT 建立 music_dev_a 和对应用户，并仅授予 music_dev_a.*。可在受控管理员会话中使用下列结构，替换 <local-password> 为配置中的应用密码；不把真实值提交或粘贴到交接。

```sql
CREATE DATABASE music_dev_a CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'music_dev_a'@'127.0.0.1' IDENTIFIED BY '<local-password>';
GRANT ALL ON music_dev_a.* TO 'music_dev_a'@'127.0.0.1';
```

host grant 需符合本机 MySQL 的账户匹配规则；连接被拒绝时检查 `CURRENT_USER()` / host，而不是扩大到远程通配账户。本轮实例只监听 127.0.0.1:3307。原生 server 的数据目录也需独立；macOS Unix socket 路径应较短，长项目绝对路径可能超过限制。

```bash
python3 scripts/dev.py init-db --slot a --mysql /absolute/path/to/mysql
```

脚本从 config.json 读取应用凭据，通过 MYSQL_PWD 环境传给 client，不将密码放命令参数。数据库名须精确匹配 music_dev_a；已有任意表即拒绝。空库检查不是并发锁，初始化期间必须保持该库只有一个写入方。MySQL DDL 非整体事务；中途失败会保留部分表，脚本不会清理或修复。

唯一 SQL 入口为 `music/src/main/resources/db/baseline/V001__development.sql`：

- 按依赖顺序建立 11 张表，外键保持启用，无 DROP / USE / CREATE DATABASE。
- JSON 类型、标签关联列、audit_logs 列按本轮实际使用的 MyBatis / JPA 路径对齐。
- categoryid 可空，与现有可选分类保存逻辑一致；种子分类 ID 1 为 Uncategorized。
- 回收站设置 seed 自动清理为关闭，避免开发样本被定时删除。
- development_schema_version 记录版本；SQL SHA-256 在初始化成功时输出。

历史 db/*.sql 保留参考；不要依次执行。未提供旧 TEXT 元数据的数据迁移；未启用 Hibernate 自动 DDL 或 validate。分类实体 Integer / 资源实体 Long 的既有 Java 类型差异仍需后续审核。

## 后端、前端与检查

终端一：

```bash
. .local/a/env.sh
cd music
sh ./mvnw -B -ntp test
sh ./mvnw spring-boot:run
```

终端二：

```bash
. .local/a/env.sh
cd web
npm ci
npm run dev
```

终端三：

```bash
python3 scripts/smoke.py --slot a
python3 scripts/smoke.py --slot a --via-proxy
```

smoke 建立随机合成账户、标签及约 1 秒静音 MPEG fixture，保留在自己的开发库，重复运行不依赖旧 IDs。不导入外部曲库或发送邮件。检查 envelope 与 HTTP 状态；不是只检查请求是否返回 200。验证 2 个小上传分片的续传请求、合并哈希、元数据、过滤、实际 Range 206、软删除及恢复。没有重启进程来验证上传恢复，也没有验证主观听感。

输出的 legacy_exposure_http_status 是缺陷观测，不是权限通过标记；当前 pending、静态路径和 deleted 的匿名访问都是 200。新 discovery 对外接入前必须解决，不能因为 local profile 限制监听地址就声称权限修复。

生产静态预览只执行 `npm run build` / `npm run preview`；preview 不提供 Vite 开发代理，需要自己的 API 反向代理。SMTP 连接到本地接收器的端口，但仓库未启动 SMTP；密码重置邮件不在本轮验收中。

## MUS-010 一次运行前后端基线

原生 MySQL 路线新增入口（从自己的独立 checkout 根目录）：

```bash
python3 scripts/baseline.py --slot a --keep-running
```

B 在独立 clone / worktree 用 `--slot b`。入口识别已有本机工具，依次检查权限 / 配置、Java 测试、前端构建、数据库、后端 / Vite、直连与代理 smoke；已有非空库不重新初始化，只有新 slot / 全新空库可建立基线。Ctrl+C 关闭本次创建的进程，外部已有数据库保留。详细限制、工具路径和最新实跑状态见 [verification/MUS-010.md](verification/MUS-010.md)。当前受管终端在回环权限检查即阻塞，完整入口尚未端到端验收，不能将入口存在当作两端已跑通。
