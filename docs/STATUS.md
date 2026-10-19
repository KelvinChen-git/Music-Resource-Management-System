# 项目状态与交接

最后更新：2026-10-19（America/Chicago）。当前阶段：**P0 前，协作文件已编写；多模态功能未开发。**

## 当前源码与交付

- 仓库：`https://github.com/KelvinChen-git/Music-Resource-Management-System`
- 核对基线：`main` 上的 `b81f57c79e1cefb96c2055df4ae438aa24fb475c`。
- 文档任务分支：`docs/multimodal-collaboration`。
- 本次范围：AGENTS.md、README.md、PROJECT.md、CONTRACTS.md、STATUS.md 共五份；没有修改业务源码 / SQL / 依赖。
- 交付状态：本地分支和文档提交；当前连接只读，尚未推送到 GitHub，也未创建 PR。最终提交 SHA 由交接消息 / `git log -1` 给出，不在同一提交中循环引用自身。
- 当前集成负责人：本轮文档由账号 A（本会话）整理；业务开发尚无人认领。开始下一轮时显式指定负责人并更新本节，A / B 角色可互换。
- 无正在运行的业务开发任务；未认领不是默认授权两个账号同时写全部模块。

## 能力状态

| 内容 | 状态 | 证据 / 限制 |
|---|---|---|
| 旧 Java / Vue 管理系统 | 源码存在 | 静态确认 controller / mapper / Vue 页面；未完整运行 |
| 文件分片 / 续传、审核、回收站 | 源码存在 | 新路线应复用，不能重复宣称为新增检索能力 |
| 前端安装和生产构建 | 已通过 | 见下方检查记录 |
| 后端编译 / 测试 / 启动 | 未验证 | 测试命令被依赖下载阻塞；不能判断测试结果 |
| CLAP / Python 模块 / 片段索引 | 未实现 | 仅 CONTRACTS 中有建议边界 |
| 2,000 首 / 70,000 片段 / 120 查询 | 计划 / 算例 | 没有实际导入或标注 |
| nDCG、P95、吞吐和用户收益 | 未测量 | 不可直接写入已完成项目证据 |

## 基线检查记录

环境：Linux、OpenJDK 17.0.20、Node 24.19.0、npm 11.9.0。检查代码基线同上。

| 工作目录 | 命令 | 结果 |
|---|---|---|
| `web/` | `npm ci --ignore-scripts --no-audit --no-fund --fetch-retries=0 --fetch-timeout=30000` | exit 0；244 packages；没有升级 lockfile |
| `web/` | `npm run build` | exit 0；Vite 6.2.4；部分 bundle >500kB 警告，无构建错误 |
| `music/` | `sh ./mvnw -B -ntp test` | exit 1，环境阻塞：无法解析 repo.maven.apache.org，Spring Boot 3.4.4 parent POM 未下载；未进入编译 / 测试 |
| 仓库根 | `git diff --check`；五文件本地链接、代码围栏、JSON 示例及源码版本引用检查 | 通过；仅五份 Markdown 文档发生变更 |

未执行：MySQL 初始化、后端启动、邮件、登录 / 上传 / 播放联调、全部命名测试、Python / 模型实验。根因不明的后端运行兼容性不能写成已通过。

## 优先阻塞与源码差异

| 编号 | 发现 | 首次处理任务 |
|---|---|---|
| B-01 | 没有提交 application.yml 或可重复本地配置；Vite proxy 硬编码 8080 | MUS-001 |
| B-02 | SQL 多套结构不一致；music_db.sql 的 recycle_bin_settings INSERT 顺序 / 字段问题；schema.sql 的 FK 命名问题；JSON / TEXT 差异 | MUS-001 |
| B-03 | 匿名文件和静态上传路由与原权限描述不一致；需验证审批 / 删除后访问规则 | MUS-001 → MUS-005 |
| B-04 | 默认 Surefire 只跑 *ServiceImplTest.java，其他 Test 被遗漏；测试依赖存在跨版本组合，兼容性未运行确认 | MUS-001 |
| B-05 | README 历史描述的评论 / 点赞 / 收藏等未找到对应服务端实现；Swagger 未发现对应依赖 / 配置；20MB 限制与代码不符 | 已在新 README 更正，后续按需核验 |
| B-06 | 素材、许可、准确 checkpoint、Python 版本 / 包锁 / 硬件未准备 | MUS-002 |
| B-07 | 根 ignore 尚未覆盖计划中的模型、音频、Python 缓存与索引目录 | MUS-001，在生成这些数据前解决 |

这些是开发输入，不是本次已修复的问题；不要顺手扩大文档 PR 为全面重构。

## 任务台账

状态只用 todo / in_progress / blocked / review / done。owner 未认领时写 unassigned。完成需要提交和验收证据，不能仅凭任务描述改成 done。

| 任务 | 状态 / owner | 依赖 | 修改边界与验收 |
|---|---|---|---|
| DOC-001 协作基础 | review / A（本会话） | 无 | 五份文档；本地差异、路径和示例检查；只读连接导致尚未远端发布 |
| MUS-001 可重复开发基线 | todo / unassigned | DOC-001 应用后 | 配置样例、参数化 proxy / 端口、隔离 schema 初始化、ignore、测试选择；新库恢复旧流程并记录运行结果。触及 web / music / SQL / lockfile 时先认领具体文件 |
| MUS-002 模型 spike / 契约冻结 | todo / unassigned | MUS-001 | 建议 services/audio-search/；30–50 首素材清单、准确模型与预处理、维度、依赖锁、CONTRACTS 和 fixtures；先验证模型可用 |
| MUS-003 切片与索引基线 | todo / unassigned | MUS-002 | Python 处理模块及测试；边界音频、可追溯索引、整曲 / 片段精确查询，不修改 Vue |
| MUS-004 搜索界面 | todo / unassigned | MUS-002 | web discovery 页面、API adapter 和片段试听；先用明确标注的 fixtures，不修改后端 schema |
| MUS-005 Java 集成与可见性 | todo / unassigned | MUS-003、MUS-004 | discovery gateway / 内部调用 / 处理状态；库内参考、临时参考上传、权限与删除校验；单一集成负责人协调 |
| MUS-006 评测与调优 | todo / unassigned | MUS-005 | 标注清单、qrels、评分脚本、原始结果；dev/test、候选库和版本冻结后比较，不先预填效果 |
| MUS-007 恢复 / 扩容 / 演示 | todo / unassigned | MUS-006 | 持久任务、并发、索引升级 / 回退、数据扩展和演示；基于瓶颈选择基础设施 |

认领记录的最小内容：`task_id / owner / branch / base_sha / allowed_paths / dependencies / acceptance / next_handoff`。当前 owner 与路径占用由集成负责人串行写入；另一账号先报告拟认领范围，避免同时改这张表。

## 下一步启动指令

1. 在有写权限的本地 clone 应用文档提交，检查 HEAD；不要假设只读会话已推送。
2. 让账号 B 阅读 AGENTS → README → PROJECT → CONTRACTS → STATUS，并先复述“当前有什么、下一步做什么、哪些只是目标”。
3. 指定本轮集成负责人，在任务分支认领 MUS-001。
4. 先审查并整理隔离数据库初始化和本地配置，不向真实数据库运行历史 dump。锁定一套 Node / Java / MySQL 环境。
5. 在后端依赖可下载的环境重跑默认及全部命名测试，核对 selected tests；完成旧系统 smoke 后再开始模型开发。
6. MUS-002 契约冻结前不同时开发两套不同检索 API。冻结后 MUS-003 / 004 才适合并行。

## 固定交接模板

复制以下结构到任务交接消息；负责人将摘要更新到本文件。

```text
任务 / owner：
分支 / 基础 SHA / 交付 SHA：
代码位置或 PR：
推送状态（本地已提交 / 已推送 / 失败）：
修改文件与实际完成内容：
接口 / schema / 配置变更：
执行命令、退出状态、关键结果：
未执行检查及原因：
未完成内容、临时实现、已知问题：
数据 / 模型 / 索引版本与工件获取方式：
下一任务、入口文件、依赖：
是否释放文件占用 / 接任负责人：
```

账号切换：原账号推送后停在明确检查点；接手者先 fetch，再在干净工作区切到准确分支 / SHA。不要自动覆盖本地改动或以聊天里“最新”代替 Git 版本。合并与冲突解决由当前集成负责人负责，审核对准具体 commit。
