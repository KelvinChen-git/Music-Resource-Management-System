# 账号 A 最新交接

- account：A；2026-10-19 America/Chicago；集成负责人 / STATUS 唯一写入方：A。
- task：MUS-010 两套前后端开发基线；status done（本机运行验收）。branch `chore/MUS-010-dual-dev-baseline`；base f15d842344f8df0b251f90d65811206efb589555。
- 运行代码：A@699da38cc44f9d5ff33f26c21336c5d5368ab250；本机独立 B worktree@e89b4db4496b13ab28ab6944f1db82c600d80066；只有三份台账 / 验证文档差异，业务和启动入口相同。
- ack_peer_feed_sha：05d4e9fe7c9528923796ef46508cadb05e94bd1b；已知 B source 6e4118cc316e95d2ba0f3c1fc1cf7ae15fecefbc，审核基线 7ab0d39。
- 发布边界：当前新验收结果仅本地，A 上次远端 feed d0a8381 / source 0ba0a96；受管终端此前 ls-remote DNS 阻塞，不能声称 B 已收到本次结果。源码最终 SHA 以成功发布后的 handoff.json 为准。

## 当前证据

用户在普通 macOS Terminal 运行两个独立 checkout，A 直接读取两边本地结果，并逐字比对原始 smoke JSON、解析 Java 汇总与核对 6 个监听端口：

| 检查 | A | 本机 B slot |
|---|---|---|
| Java 单测 | 107，0 failures / errors / skipped | 同左 |
| 前端 | build passed，复用既有依赖 | npm ci / build passed |
| MySQL | 复用已有库，11 表 | 全新数据目录 / 空库初始化，11 表 |
| 直连 / 代理 smoke | 13 / 13 passed | 13 / 13 passed |
| 端口 | 3307 / 8080 / 5173 | 3308 / 8081 / 5174 |

完成时间 A 18:18:02，B 18:19:35 America/Chicago。证据见 [运行记录](../../verification/MUS-010.md)、[本次真实汇总](../../verification/MUS-010-live-results.json) 及四份 MUS-010-*-smoke-*.json。私有日志保留在各 checkout .local/<slot>/logs；未提交配置 / 密钥或数据库。

普通终端跑通不等于受管终端网络权限恢复；本机 B worktree 代跑不等于 B 账号独立审核。原 B 报告中的 0 后端检查仍是当时事实，不改写 B 的报告或 feed。未合并 main。

## 未完成项与下一步

- MUS-009 正常分片保存、合并与元数据已有真实 SQL 正例；107 项单测仍不证明真实失败回滚、跨请求并发或后端进程重启续传，这些另补。MUS-009 实现提交 949603fe45e3f90637dd7dc2578e41f80945afb5。
- 媒体 pending / static / deleted 三个匿名入口仍 HTTP 200，公开 discovery 保持阻断；一年缓存和上传归属仍待治理。
- B npm ci 输出 20 个依赖漏洞（1 low / 3 moderate / 15 high / 1 critical）；既有 JSqlParser count 优化警告仍有，功能检查通过。本轮不自动改锁文件或做依赖升级。
- 后续在可运行普通终端补 MUS-009 故障 / 并发 / 进程重启，并由 B 收到精确 source_sha 后独立审核；当前未收到 B 新确认。不在本轮继续新增搜索或宣称语料 / 评测完成。

MUS-002 仍只有固定 CLAP 合成编码 / 缓存离线可行性；真实许可素材、解码 / 检索效果、索引、线上 API / 界面尚未完成。A / B 的报告路径仍分别独占，A 不写 B 两份报告。
