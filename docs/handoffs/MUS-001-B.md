# 账号 B：MUS-001-R1 基线与媒体访问审核

任务已由集成负责人 A 分配；B 尚未确认接收，不能将本文件当成已开始或已完成的审核。

## 任务卡

- task_id：MUS-001-R1；owner：账号 B；集成负责人 / STATUS 写入方：账号 A。
- branch：`review/MUS-001-B-baseline`，必须在 B 的独立 clone 中创建。
- base_sha：`7ab0d39d920a538b28878cf92ecbe90e55994ec3`；这是已完成验证的 MUS-001 实现提交，审核前 `git rev-parse HEAD` 与其逐字核对。远端 main 仍是 b81f57c，不含本次修改。
- depends_on：DOC-001 已应用；MUS-001 实现和验证文件已交付；无需等待模型 spike。
- allowed_paths：**仅 `docs/reviews/MUS-001-B.md`**。可读所有源代码 / A diff；不得修改 STATUS、共享契约、SQL、Java / Vue 实现、配置、pom 或 lockfile。
- runtime：自己的 slot B、独立数据库端口 3308 / schema music_dev_b、Java 8081、Vite 5174、独立上传 / 索引。不要连接 A 的 3307、目录或数据库。若工具不足，写 blocked 与原始错误，不编造通过。
- next_handoff：报告 commit / 分支、是否推送、复跑证据、严重性和最小建议，交给 A；不要自行合并。

## 获取交付

当前远端连接无写权限；不能只 clone GitHub main 后开始审查。用户提供的 Git bundle 包含任务分支和基线历史。B 若没有本地仓库，可以从 bundle 克隆：

```bash
git clone --branch chore/MUS-001-dev-baseline /absolute/path/music-account-a.bundle Music-B
cd Music-B
git remote set-url origin https://github.com/KelvinChen-git/Music-Resource-Management-System.git
git status --short --branch
git rev-parse HEAD
# 任务文档可能有后续提交，审核源码固定为以下 SHA：
git switch -c review/MUS-001-B-baseline 7ab0d39d920a538b28878cf92ecbe90e55994ec3
```

已有 clone：先检查干净工作区，再从 bundle fetch 到新的 account-a 跟踪 ref；不 reset / clean / stash，不覆盖已存在分支。

```bash
git fetch /absolute/path/music-account-a.bundle refs/heads/chore/MUS-001-dev-baseline:refs/remotes/account-a/MUS-001
git switch -c review/MUS-001-B-baseline 7ab0d39d920a538b28878cf92ecbe90e55994ec3
```

依序读 AGENTS → README → PROJECT → CONTRACTS → STATUS，再读 development.md 和 verification/MUS-001.md。

## 审核范围与验收

1. 对照 `b81f57c..交付SHA`，检查空库 schema 是否覆盖当前实体 / mapper，JSON / FK / audit 列改动有无兼容问题。确认仅适用于空库，不是既有库迁移。特别检查 JPA 分类 ID 与资源 ID 类型差异。
2. 独立复跑配置生成、空库初始化、非空库拒绝、默认测试及显式 *Test、前端构建、两条 smoke；记录测试类和数量。原始 75 tests / 3 errors 和最终 89 tests / 0 errors 不混为同一版本。
3. 建立媒体矩阵：匿名 / owner / other user / admin × pending / approved / rejected / deleted × resource file / raw file download / static uploads。只在自己的合成数据上检查；有缺口就写未覆盖。核查 cache-control 与删除 / 撤销的关系，以及 Range 行为。
4. 检查即写分片后 saveBatch 重复持久化与 MD5 未比对的影响；提出最小后续任务及可验证断言。当前分支不修服务代码。
5. 每条发现提供 severity、具体文件位置、最小重现、实际 / 预期、是否阻断本地开发 / 对外 discovery、建议修改路径。对没有问题的范围简要说明；不要用“89 tests 通过”替代权限审核。

接受标准是报告有可复核证据并明确局限，不要求把所有缺陷修好。报告不包含真实秘密、个人数据、原始曲库、权重或索引。需要新增路径或改契约时先回报 A。

## 固定交接

```text
任务 / owner：MUS-001-R1 / B
分支 / base SHA / 报告 SHA：
推送状态（已推送 / 本地已提交 / 失败）：
只修改的文件：docs/reviews/MUS-001-B.md
执行命令、退出码、测试数量：
发现（severity / 证据 / 最小修改边界）：
未验证 / blocked：
建议后续任务 / 是否释放文件占用：
```

没有向另一账号的自动消息通道；由用户传递本任务和 bundle。B 推送失败时同样导出可导入提交，不声称 A 已收到。
