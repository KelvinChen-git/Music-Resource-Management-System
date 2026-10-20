# 账号 A 最新交接

- account A；2026-10-19 America/Chicago；集成负责人 / STATUS 写入方 A。
- task MUS-012 上传持久所有权；branch `fix/MUS-012-upload-ownership`；base `dbdcae2cbbce4aeb7ee25418f9c3464de63ebe73`；status review（实现及自动测试通过，新源码真实 HTTP 验收 blocked）。
- ack_peer_feed_sha：05d4e9fe7c9528923796ef46508cadb05e94bd1b；本轮开始原生 git sync 成功，B 仍为 source 6e4118c / reviewed 7ab0d39，无新交付；不替 B 写报告或确认。
- 已发布前批：MUS-011 最终 dbdcae2 / feed a74abe3，本机 B 同步入口已拉取。两套本机 266 Java / 144 真媒体矩阵通过属该旧版本，不代替本任务新结果。

## 本次改动

契约先记入 CONTRACTS A5。新上传持久保存 owner_user_id，按当前数据库有效账号隔离 create / upload、MD5 check / list、详情 / 进度 / 缺片、分片 / 合并 / 删除、metadata 首次解析与绑定；管理员不能代操作他人上传。首绑定 / 写操作在上传行锁内检查所有者，保留审核 / 删除的反重绑定检查。新头像绑定只接受目标账号自己的完整图片上传，避免 profile 将他人图片公开。

删除未引用的自有上传只逻辑删除并保留字节 / 分片，音乐（含 deleted）或头像引用返回 409。已有音乐媒体继续按审核可见性读取；无引用完整上传仅持久 owner 下载，旧 NULL owner 不构成可认领上传。

V001 不变，V002 只加 nullable owner 列与索引。旧记录保留 NULL，不凭 MD5 / 音乐引用推断 owner；要继续旧上传需重新上传。空库升至 V002，已有 V001 需显式开发迁移选项，无重建表 / 回填 / 凭据变更。A 真库已成功迁移，10 条旧上传保持 NULL；本机 B 已由干净工作树同步至实现提交078a82b并成功迁移，6条旧上传保持NULL；具体事实见 [机器汇总](../../verification/MUS-012-results.json)。

## 验证与阻塞

Java **308 / 0 failures / errors / skipped**：原266 + 新HTTP40 + MD5隔离2。Python全量22通过（baseline9 / migration4 / collab9），脚本 py_compile / --help 通过。前端与依赖未改，未单独重复 build。验证正文见 [MUS-012](../../verification/MUS-012.md)。

候选 Java 连接本机 MySQL 报 SocketException: Operation not permitted，Druid / JPA 未初始化，端口18080未就绪；候选已停止。Python / native MySQL可连不代表 Java 可连，Maven BUILD SUCCESS 也不表示服务启动成功。**新65项真实上传权限检查执行未通过，不能提前标 passed**。原普通终端两套服务保留 MUS-011 版本。

源码与两库已准备好；两个原终端各 Ctrl+C，在各自目录运行 `python3 scripts/baseline.py --slot a --migrate-upload-ownership --keep-running` / `--slot b`。新 baseline 会自动补原功能、媒体144矩阵和新上传65检查；A 直接读取本地报告，不需用户搬运。已升级库重复选项无回填 / 重建。

## 下一步与边界

先接收新版本真实矩阵，再补 MUS-009 事务失败 / 并发 / 重启续传。未知 legacy 归属人工迁移与物理垃圾回收仍待独立任务。B 账号独立审核尚未进行，不把本机 B 工作树测试当账号 B 确认；不开放公开 discovery、不合并 main、不升级依赖、不写 B 独占报告。

本次实现提交078a82b4082e192258252bafe617e849ac4925f5已发布，feed检查点8ead1264a276eabdbf9ace52e8889fc9d9930aba；最终报告提交继续发布到同一任务分支，source_sha以远端handoff.json为准。发布不代表B已读取或审核。
