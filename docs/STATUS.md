# 项目状态与交接

最后更新：2026-10-19（America/Chicago）。当前集成负责人：**账号 A**。STATUS 仅由当前集成负责人串行更新；账号 B 的报告由 A 整合。

## Git 与交付状态

- 仓库：`https://github.com/KelvinChen-git/Music-Resource-Management-System`。
- 最新远端检查：仅 main，`b81f57c79e1cefb96c2055df4ae438aa24fb475c`。当前独立 clone 初始干净，没有继承未提交业务修改。
- 五份协作文档原先均未发布；已在 `docs/multimodal-collaboration` 应用附件补丁，提交 `8f1fb6b`。逐字节核对与附件相同。原 aa720da 是旧会话提交，不能假设存在于当前 Git 历史。
- MUS-001 交付分支：`chore/MUS-001-dev-baseline`（HEAD 1b1faa1），基于上述文档分支。当前 A 工作分支为 `spike/MUS-002-clap-feasibility`，其基线为 1b1faa1。实现提交 `7ab0d39d920a538b28878cf92ecbe90e55994ec3`，本条更新属于后续交接文档提交。
- GitHub 连接 permissions.push=false；CLI push --dry-run 缺少 HTTPS 凭据（exit 128），没有把任务分支推到远端，未创建 PR、未合并 main。通过 Git bundle / patch 交接也必须由接收者明确导入，不能称 B 已收到。

## 能力与证据

| 内容 | 状态 | 证据 / 限制 |
|---|---|---|
| Java / Vue 旧管理系统 | 源码存在，部分流程实跑通过 | 注册登录、标签分类筛选、上传合并、MP3 元数据、软删除恢复 |
| 前端依赖 / build | passed | Node 22.23.3 / npm 10.9.9；现有 lockfile；非阻塞 bundle 警告 |
| Java 单测 | passed | 默认及显式 *Test 均 9 类 89 tests，零失败 / 错误 / 跳过 |
| 空开发库 / local 启动 | passed（原生 MySQL） | V001 建立 11 表；重复初始化拒绝；Compose 未执行 |
| API 直连 / 开发代理流程 | passed | 各 13 项合成样本检查，真实 Range 返回 206 |
| 两账号环境隔离 | 配置及端口拒绝验证通过 | 独立配置 / 密钥 / 端口 / schema / 路径；未在 B 账号运行 |
| 旧媒体权限 | 已确认缺陷 | pending、静态上传及软删除后的匿名媒体均可 HTTP 200 读取 |
| CLAP 文本 / 音频编码 | 可行性 passed | 固定 checkpoint CPU 严格加载，实际 512 维，合成输入，9 项预处理测试；有网 / 缓存离线复跑通过 |
| Python 检索 / 索引 / 搜索界面 | 未实现 | 只有离线探针；未冻结 discovery-v0 |
| 30–50 / 2,000 首，约 70,000 片段，120 查询 | 计划 / 算例 | 未导入或标注；合成 smoke 不是音乐语料 |
| 质量、P95、并发和提升比例 | unmeasured | 不得写作已完成成果 |

详细命令与机器生成结果见 [verification/MUS-001.md](verification/MUS-001.md)。旧会话网络阻塞只是历史：本轮 Maven 已能下载和实跑。原始默认 75 tests 有 3 errors；修正 fixture 后才得到全量 89 tests 通过。

## 任务与占用

状态仅 todo / in_progress / blocked / review / done。A / B 为当前角色；未最终合并不自动代表所有内容完成。

| 任务 | 状态 / owner | 分支 / 基线 / 依赖 | 允许修改与验收 |
|---|---|---|---|
| DOC-001 协作文件 | review / A | docs/multimodal-collaboration / b81f57c | 五文件已应用，本地提交 8f1fb6b；远端发布 blocked |
| MUS-001 可重复开发基线 | review / A | chore/MUS-001-dev-baseline / b81f57c + 8f1fb6b；依赖 DOC-001 | 下方确切路径；原生空库、local 启动、全量测试、build、API smoke 已通过；B 审核待交付 |
| MUS-001-R1 基线与媒体审查 | todo / B（任务已分配，尚未确认接收） | review/MUS-001-B-baseline / 7ab0d39d920a538b28878cf92ecbe90e55994ec3 | 只写 docs/reviews/MUS-001-B.md；读源码和 diff，在自己的 clone / slot B 复核；不改 A 文件或 STATUS |
| MUS-002 模型 spike / 契约冻结 | blocked / A | spike/MUS-002-clap-feasibility / 1b1faa1；已测探针 ab5d6f3 | services/audio-search/ 与 docs/model-spike.md；准确 checkpoint / 预处理 / 实际输出 / 依赖锁；素材和效果未验证前不冻结 |
| MUS-003 切片与索引 | todo / unassigned | MUS-002 | 冻结契约后的 Python 模块，边界测试与精确检索 |
| MUS-004 搜索界面 | todo / unassigned | MUS-002 | web discovery 页面；先明确 fixtures，禁止自行假设 API |
| MUS-005 Java 集成与权限 | todo / unassigned | MUS-003 / 004，及媒体权限治理 | 检索 gateway、可见性复核、旧匿名路径治理、片段试听 |
| MUS-006 评测 | todo / unassigned | MUS-005 | manifest / qrels / dev-test / 基线和原始结果，不预填指标 |
| MUS-007 恢复 / 扩容 / 演示 | todo / unassigned | MUS-006 | 根据瓶颈推进，不先堆基础设施 |

### MUS-001 A 路径范围（review 检查点）

`AGENTS.md`、`README.md`、`docs/PROJECT.md`、`docs/CONTRACTS.md`、`docs/STATUS.md`、`docs/development.md`、`docs/verification/MUS-001*`、`docs/handoffs/MUS-001-B.md`、`.gitignore`、`.nvmrc`、`compose.dev.yml`、`scripts/dev.py`、`scripts/smoke.py`、`music/pom.xml`、`music/src/main/resources/application-local.yml`、`music/src/main/resources/db/baseline/V001__development.sql`、`music/src/main/java/com/taffy/music/domain/MusicResourceTags.java`、`music/src/main/resources/mapper/MusicResourceMapper.xml`、`music/src/test/java/MusicResourceServiceImplTest.java`、`web/vite.config.js`、`web/.env.example`。

扩展到 mapper / 单测的原因是实跑暴露 JSON 返回 null 和三项无效测试前提，详见验证文档。没有更改前端 lockfile 或重写业务服务。B 不在这些路径直接修复；需要扩大范围时先将具体路径交给 A 协调。

B 独占 `docs/reviews/MUS-001-B.md`；A 不创建该报告，以免伪造“已审核”。正式任务见 [handoffs/MUS-001-B.md](handoffs/MUS-001-B.md)。

## 未解决事项

| 编号 | 当前事实 | 后续 |
|---|---|---|
| B-01 | 缺配置 / proxy 硬编码已解决；可重复命令已建立 | B 复跑；Compose 仍未实跑 |
| B-02 | 空库 V001 已验证；历史 SQL 保留，不可顺序执行 | 既有数据库迁移另立任务；分类 ID Java 类型差异待审 |
| B-03 | 旧匿名媒体 / 静态路径 / 删除后访问问题已实证 | MUS-001-R1 提出矩阵与最小方案，MUS-005 接入前修复 |
| B-04 | 默认测试遗漏 / 跨版本测试依赖已解决 | 全量 89 tests 通过；不代表全业务 / 全权限覆盖 |
| B-05 | Druid POM、JSqlParser count 回退、分片重复持久化仍有诊断 | 记录，不扩成全面重构；B 审核影响 |
| B-06 | 无许可明确的真实音乐 manifest / 查询 / qrels | MUS-002 素材获取与效果评估前提；不能用静音样本替代 |
| B-07 | 没有 GitHub 写权限 / CLI 凭据 | 本地提交及可导入 bundle；未发给 B、未发布分支 |
| B-08 | MD5 合并后计算但未校验请求哈希；续传未做进程重启验证 | 后续上传完整性任务，不能宣称全面可靠 |

## 下一检查点与交接

1. A 已提交 MUS-001，导出 bundle；B 获取准确 SHA 后认领审核分支，不把远端 main 当作交付分支。
2. B 在独立 clone 用 slot B 复跑；写清 passed / failed / blocked 和权限矩阵；只提交自己的报告，不碰 STATUS。
3. A 已完成 MUS-002 离线编码可行性实跑，独立 spike 分支和占用已建立；共享 API / schema 仍须冻结后才让 MUS-003 / 004 并行。
4. 外部公开检索之前解决媒体绕过；最终合并由用户决定，不直接 push main 或 force push。

交接必须写：task / owner、branch / base_sha / delivery_sha、推送状态、修改路径、命令及结果、未执行检查 / 原因、未完成内容、模型 / 数据工件位置与哈希、下一任务、文件占用与负责人。额度不足时先提交并停在明确检查点；本地 commit 不等于另一账号已收到。

## MUS-002 本轮占用

- owner A；branch spike/MUS-002-clap-feasibility；base 为 MUS-001 交接文档提交（`git log -1 chore/MUS-001-dev-baseline`），实现基线 7ab0d39。
- allowed_paths：`services/audio-search/`、`docs/model-spike.md`、`docs/STATUS.md`、必要的 README / PROJECT / CONTRACTS 事实更新；不修改 MUS-001 已冻结实现或 B 的审核报告。
- 先验证官方 music checkpoint、预处理和 CPU 编码，记录实际依赖与输出；真实许可语料 / 查询 / qrels 尚缺，不报告音乐效果，不冻结 discovery-v0。

### MUS-002 当前检查点

- 探针代码提交 `ab5d6f3697f37ecfbc96c3aa062a7f2b6702ca6d`；checkpoint music_audioset_epoch_15_esc_90.14.pt，HTSAT-base / no fusion，文件哈希与官方 LFS 元数据一致。Python 3.12 / macOS arm64 / CPU 实跑，实际文本与音频均为 512 维，float32，范数约 1。
- 9 项预处理测试、pip check、有网缓存运行与 HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE 复跑通过。源码 / 安装包哈希、准确版本和单次观测见 model-spike.md / verification/MUS-002-probe*.json。
- SDK 默认 repeatpad / rand_trunc 与候选短尾段零填充不同，探针先显式补到 480000 点；44.1→48kHz 浮点多一采样点问题以整数长度修复。
- blocked 原因：尚无来源 / 许可 / 内容哈希明确的真实音乐 manifest、相关性标注和真实查询。合成波形只证明模型能运行，不能据此冻结音乐检索方案。Python MP3 / WAV 解码亦未验收。
- 没有索引、线上检索 API、新界面或质量 / P95 结果。保留 MUS-002 owner A，等待语料与效果验收；B 只审 MUS-001。MUS-003 / 004 不提前并行写 API。
