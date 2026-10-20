# 账号 A 最新交接

- account A；2026-10-19 America/Chicago；集成负责人 / STATUS 写入方 A。
- task MUS-012 上传持久所有权；branch `fix/MUS-012-upload-ownership`；base `dbdcae2cbbce4aeb7ee25418f9c3464de63ebe73`；status review（实现、自动测试及两套本机真实 HTTP 通过；B 独立审核待完成）。
- ack_peer_feed_sha：05d4e9fe7c9528923796ef46508cadb05e94bd1b；本轮验收时原生 git sync 成功，B 仍为 source 6e4118c / reviewed 7ab0d39，仍无新交付；不替 B 写报告或确认。
- 已发布实现：MUS-012 最终报告检查点4b3ec3f / feed51cb7a5；本轮真实运行A为4b3ec3f、本机B为078a82b，仅四份文档不同，运行源码一致。最新最终source以远端handoff.json为准。

## 本次改动

契约先记入 CONTRACTS A5。新上传持久保存 owner_user_id，按当前数据库有效账号隔离 create / upload、MD5 check / list、详情 / 进度 / 缺片、分片 / 合并 / 删除、metadata 首次解析与绑定；管理员不能代操作他人上传。首绑定 / 写操作在上传行锁内检查所有者，保留审核 / 删除的反重绑定检查。新头像绑定只接受目标账号自己的完整图片上传，避免 profile 将他人图片公开。

删除未引用的自有上传只逻辑删除并保留字节 / 分片，音乐（含 deleted）或头像引用返回 409。已有音乐媒体继续按审核可见性读取；无引用完整上传仅持久 owner 下载，旧 NULL owner 不构成可认领上传。

V001 不变，V002 只加 nullable owner 列与索引。旧记录保留 NULL，不凭 MD5 / 音乐引用推断 owner；要继续旧上传需重新上传。空库升至 V002，已有 V001 需显式开发迁移选项，无重建表 / 回填 / 凭据变更。A 真库已成功迁移，10 条旧上传保持 NULL；本机 B 已由干净工作树同步至实现提交078a82b并成功迁移，6条旧上传保持NULL；具体事实见 [机器汇总](../../verification/MUS-012-results.json)。

## 验证与阻塞

Java **308 / 0 failures / errors / skipped**：原266 + 新HTTP40 + MD5隔离2。Python全量22通过（baseline9 / migration4 / collab9），脚本 py_compile / --help 通过。前端与依赖未改，未单独重复 build。验证正文见 [MUS-012](../../verification/MUS-012.md)。

两个普通终端已于20:12–20:13加载新代码，结果均passed：各308 Java / Vue build、后端直连与Vite代理各13功能+4安全、144真实媒体矩阵+8附加项、65真实上传权限检查通过。原始JSON与内嵌结果一致，媒体矩阵无重复且状态正确；每套上传检查35个显式拒绝为7×401 / 7×403 / 21×404，拒绝后分片与计数未变。

真实检查覆盖owner落库、伪造owner、跨账号与管理员拒绝、同MD5隔离上传、续传合并、首次绑定、NULL owner、锁定/删除账号旧JWT、头像绑定与公开访问、引用保护和逻辑删除。两份后端日志均无SQLSyntaxErrorException / BindingException / CommunicationsException。

[真实运行汇总](../../verification/MUS-012-live-results.json) 与八份原始JSON已归档。历史受管候选Java网络阻塞未妨碍普通终端实跑；两套新服务保持运行，本轮无需再重启，A已直接读取报告，无需搬运。本机B槽通过不等于B账号读取或独立审核。

## 下一步与边界

新版本真实矩阵已接收；接下来补 MUS-009 事务失败 / 并发 / 重启续传。未知 legacy 归属人工迁移与物理垃圾回收仍待独立任务。B 账号独立审核尚未进行，不把本机 B 工作树测试当账号 B 确认；不开放公开 discovery、不合并 main、不升级依赖、不写 B 独占报告。

本次实现提交078a82b4082e192258252bafe617e849ac4925f5已发布，feed检查点8ead1264a276eabdbf9ace52e8889fc9d9930aba；最终报告提交继续发布到同一任务分支，source_sha以远端handoff.json为准。发布不代表B已读取或审核。
