# Account B — MUS-035 N1 incremental review completed

- account / task_id / assignment_revision / owner：b / MUS-035-R2-B / 1 / b。
- status：review_completed；verdict：approve_scoped；准确N1修复可关闭。
- source_branch：review/MUS-035-B-output-permissions；交付SHA由feed handoff.source_sha给出。
- reviewed_sha：de255c7724926c6f823abceecf0b9a487a467d6d。
- comparison_base_sha：74645de71c173c43811d7d0d98548089a1836491。
- assignment_source_sha：e109b5c2ebc0531c059ddca844c63ad1b101ca84（本次A固定入口，同035-R2/rev1原卡）。
- ack_peer_feed_sha：7809c74f81559fb3cf5142ba6c518064945b9d25。
- claimed source/feed：11f7c2a50be7c6287f2f99ccc9b9bec3e9c37612 / 2d134ad3a200741eae8045752ae9430c2aedf845，已发布回读后开测。
- 唯一修改：[docs/reviews/MUS-035-N1-B.md](../../reviews/MUS-035-N1-B.md)；docs/collaboration/account-b/latest.md。交付后释放两文件占用。

已按固定入口读取准确任务卡/E14首条/040 N1验证及diff。三输出函数只新增chmod/fchmod共3行；移除后三行，完整driver AST同base，模型/数值/run/输入规则及O_EXCL/O_NOFOLLOW不变。两新测试加import os以外，完整测试AST同base。

独立真实OS/Git/NumPy函数边界最终9项通过（7个B检查+2个原新增方法体配B最小fixture）：旧umask0777重现0000/0000/0000，新0000/0022/0077/0777均0700/0600/0600并实际JSON/NPZ回读，已有输出/目录、文件和目录symlink/悬空链接及边界拒绝，字节/mode保持、umask恢复。原生完整driver因缺torch导入exit1，31方法实际0项，不将AST边界记作全套通过。首轮B脚本八进制文本比较错误已改AST比较，失败日志保留，两轮不累加。

验证命令和限制见报告；git diff --check。私有证据verified-evidence.json SHA256 ff500011096af26a7d596958aaf5833e0cfc6c1ba757655a888dced741afa60c，仅B本地。不安装依赖/下载模型，不改产品/API/schema/配置/锁/模型/main。无真实数据/模型/索引版本变更，未读A私有数据或启动服务。双checkpoint/040/039/045工具不纳入本批准，UI/Java/MySQL/完整035未重测。

同时确认用户直派MUS-044-PLAN-B已由A原字节接收：报告SHA569b09b207b9a35d4e9a422de66d81db394c820c07a93a43b0bb5263a5d74c13与归档相同，R1–R4已在045执行有界140首开发比较；A记录选择identity、不开千首扩训，R5天花板及整曲R1/MRR无提升仍保留。仅同步公开证据，不将本卡外推为045独立审核或新计划批准。

只交两报告，A串行维护STATUS；下一步请A接收准确报告并关闭N1，原生driver完整检查仍blocked。GitHub接口顺序发布source再B feed，非原子，须精确回读；交付SHA见handoff，发布回读不等于A接收或main合并。交付后释放占用，无后台轮询。
