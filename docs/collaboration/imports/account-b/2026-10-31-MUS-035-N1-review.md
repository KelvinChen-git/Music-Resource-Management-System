# MUS-035-R2-B：N1 输出权限增量复核

2026-10-31，账号 B，revision 1。状态 `review_completed`，结论 **`approve_scoped`**：准确提交中的 N1 修复可关闭；未发现本卡范围内需要修改的问题。

| 身份 | 准确值 |
|---|---|
| task / owner / slot | MUS-035-R2-B / b / B |
| branch | review/MUS-035-B-output-permissions |
| reviewed_sha | de255c7724926c6f823abceecf0b9a487a467d6d |
| comparison_base_sha | 74645de71c173c43811d7d0d98548089a1836491 |
| assignment_source_sha | e109b5c2ebc0531c059ddca844c63ad1b101ca84 |
| ack_peer_feed_sha | 7809c74f81559fb3cf5142ba6c518064945b9d25 |
| claimed source / feed | 11f7c2a50be7c6287f2f99ccc9b9bec3e9c37612 / 2d134ad3a200741eae8045752ae9430c2aedf845 |

领取前核对固定 A feed、同 source 的 account-b dispatch/035-R2 卡、准确 E14 第一条和 A 的 MUS-040 验证 N1 段。独立 B clone 从干净 reviewed SHA 创建任务分支；claimed 已通过自己的 source/feed 发布并精确回读，随后开始验证。交付 SHA 由完成 feed 的 `handoff.source_sha` 给出，不与被审核源码或领取 SHA 混用。

本卡仅覆盖 [research_probe.py](../../services/audio-search/research_probe.py) 的 `private_output/write_json/write_vectors` 新增三行 chmod/fchmod，以及 [test_research_probe.py](../../services/audio-search/test_research_probe.py) 两个新方法。只修改本报告与 [B latest](../collaboration/account-b/latest.md)，不更新 A 串行 STATUS。相同 diff 中的双 checkpoint、040 preflight/新模型、039、044/045 工具均不在此批准内。

## 检查与结果

N1 原影响：严格 `umask 0777` 会将创建请求中的 owner 权限也屏蔽，旧三个入口生成 mode `0000` 的目录/文件，普通 owner 无法按正常流程继续写入或重读。修复在成功新建目录后 chmod `0700`，两个独占新建 fd 上 fchmod `0600`。B 使用准确旧/新源码在自己新建的 fixture 上重现和验证，建议关闭此非阻塞 P3。

| 源码 / umask | 目录实际 mode | JSON 实际 mode | NPZ 实际 mode | 实际行为 |
|---|---|---|---|---|
| base / 0777 | 0000 | 0000 | 0000 | 重现旧问题；观测后仅恢复 B 自建 fixture 权限以继续/清理 |
| reviewed / 0000 | 0700 | 0600 | 0600 | JSON/NPZ 正常回读，已有输出拒绝覆盖 |
| reviewed / 0022 | 0700 | 0600 | 0600 | 同上 |
| reviewed / 0077 | 0700 | 0600 | 0600 | 同上 |
| reviewed / 0777 | 0700 | 0600 | 0600 | 同上 |

- 准确 AST 函数边界套件最终 **9 项通过，exit 0，0 failures/errors/skips**：7 个 B 独立检查方法，另两个为准确原新增测试方法体，在 B 最小私有 fixture 上执行。保留真实 `os/subprocess/Path/json`、当前 NumPy 及实际 Git ignore 检查；未重写产品函数、注入依赖 shim 或模拟文件系统。
- JSON 包含中文及嵌套值，NPZ 使用真实 float32/int64 数组并以 `allow_pickle=False` 重新加载，值和 dtype 一致。四种 umask 下两个 writer 重复调用均为 `FileExistsError`，原字节和 mode 保持。
- 两个 writer 均拒绝已有文件 symlink 和悬空 symlink，链接/目标字节及目标 mode 保持，不创建悬空目标。目录 symlink、symlink 祖先和悬空目录 symlink 均拒绝。现有目录即使 mode 0500 也拒绝且不被新 chmod 改为 0700；现有普通文件保持，`.local` 本身、其外部和缺父目录拒绝。无效非有限 JSON 在创建文件前失败。每个测试检查并恢复 umask。
- 仅从新 driver AST 移除这三条新增权限调用后，**整个模块 AST 与 base 完全相同**：原 `O_EXCL | O_NOFOLLOW`、run/数值算法/模型常量/输入规则保持。新测试模块仅增加 `import os` 和两个方法，移除后整个 AST 与 base 相同；driver 方法数由 29 变 31。
- 原生完整 driver 导入仍因 `ModuleNotFoundError: No module named 'torch'` 阻塞：命令 exit 1，unittest 显示的 1 个 `_FailedTest` 是导入失败占位，**原生 31 个 driver 方法实际执行 0 项**。2 个原方法体执行没有使用原 full-driver setUp，不能记成全套原生通过。环境为 Python 3.12.14 / NumPy 2.3.5；torch、soundfile、librosa、laion_clap 未安装。按卡无需为此安装依赖或下载模型。

实际命令（仓库根目录）：

```bash
PYTHONPATH=services/audio-search python3 -m unittest test_research_probe -v
python3 .local/b/runtime/review_n1_r2.py
git diff 74645de71c173c43811d7d0d98548089a1836491 de255c7724926c6f823abceecf0b9a487a467d6d -- services/audio-search/research_probe.py services/audio-search/test_research_probe.py
git diff --check
```

首轮 B 脚本的静态比较错误地把 `ast.unparse` 的十进制数字与原八进制字面文本比较，9 项中该项失败；改为准确 AST 结构比较后最终 9 项通过。首轮脚本/日志保留，仅修 B 忽略区脚本，未修改产品代码；两轮不相加。B 私有证据 `.local/b/review-evidence/MUS-035-R2-B/verified-evidence.json` 的 SHA256 为 `ff500011096af26a7d596958aaf5833e0cfc6c1ba757655a888dced741afa60c`，涵盖原生阻塞、两轮日志、准确函数及最终结果的 hash。该证据未上传，不假设 A 可读取 B 本地路径。

## 限制与交接

未重做 035-R1 全套、真实 codec/CLAP/checkpoint/训练/索引/质量或 040/045 独立审核，未运行 UI/Java/MySQL。未测试并发恶意替换路径、其他 UID 或不同 OS/文件系统；本卡按准确源码和本机实际 mode/回读关闭 N1，不声称完成通用路径竞态加固。A 的 96 项/模型实跑不计为 B 的检查。

接口变化：B 无；被审核修复仅确定独占新输出 owner mode。数据/模型/索引版本：仅 B 合成 JSON/NumPy fixture，无真实数据/模型/索引生成或切换。未读取 A 私有音频、标签、权重、凭据或 run，未启动服务。

同步状态：A 已按原字节接收 MUS-044-PLAN-B（SHA256 `569b09b207b9a35d4e9a422de66d81db394c820c07a93a43b0bb5263a5d74c13`）。A source e109b5c 的 MUS-045 记录为 140 首有界开发比较、R1–R4 已执行、候选未通过扩训门槛，保留 identity；整曲 R5 天花板和 R1/MRR 未提升仍需在下一实验设计中区分。仅同步 A 证据，不视作 045 工具或训练质量已获 B 独立批准。

下一步由 A 精确接收本报告、在唯一 STATUS 关闭 N1，并按依赖安排后续有界卡。本卡没有未完成的范围内修复；原生完整 driver 检查保持 blocked。最终 source 与 `collab/account-b` 采用 GitHub 接口先后发布，非原子，须精确回读两 feed 文件和本报告；本报告的交付 SHA 及实际发布状态由 feed/发布回执确认。未推 main、未合并。交付后释放本卡两文件占用；无后台轮询。
