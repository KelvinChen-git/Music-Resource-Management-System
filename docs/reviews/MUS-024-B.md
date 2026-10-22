# MUS-024-R1-B：探索标注包完整性独立审核

- task_id / assignment_revision / owner：MUS-024-R1-B / 1 / b。
- status / verdict：review_completed / approve_scoped。
- reviewed_sha：`1e83454474413fb6c58a73d82ace579656749bc0`。
- comparison_base_sha：`3c7552ad2071847959eecf520956690dc083411e`。
- assignment_source_sha：`6fef7d9a461ad322a169918ca8ff0dd62728359f`。
- ack_peer_feed_sha：`43748a0b1f5a29bd944d6a5e613fcd2dde3523e1`。
- 分支：`review/MUS-024-B-judgment-pack`；交付SHA由B feed根目录`handoff.json.source_sha`记录，避免同提交自引用。
- 领取已先发布：source `4184de69d3418592f1ae05f40f83fc0d66a05bb6`；B feed `835909f0d404c7f65b1fb559ba5fc52eb2faef8e`，API回读字节一致后执行审核。

## 结论与范围

在准确实现提交的两文件增量及本卡合成数据范围内，未发现需要阻止接收的问题，限定批准。审核了`services/audio-search/review_pack.py`和`test_review_pack.py`全部源码，并对照A源提交的CONTRACTS E1、MUS-024验证文档与结果JSON。比较基线到实现提交仅这两份Python文件，新增642行，无产品接口、依赖或数据库变更。

B使用独立Linux clone、Python 3.12.14。新增的两个B交付文件仅为本报告和`docs/collaboration/account-b/latest.md`；运行工件均在已忽略的`.local/b/review-evidence/MUS-024-R1-B/`。没有修改A源码、台账、任务卡、公共目录、锁文件或原曲库。

A已接收MUS-023，原字节报告SHA256 `fcdc2501e3613c0501143fcd57d543dbc3751bc623dd1461101a4e3e325e4988`与B交付一致，接收JSON的任务/版本/基线/交付信息相符。旧016对应问题不重复审核或领取。

## 实际执行

所有命令在独立clone根目录执行。下列计数分别报告，不把CLI调用加成单测数量；不把A的40项或私有51对算作B实跑。

| 命令 / 检查 | 实际结果 |
|---|---|
| `python3 -m unittest discover -s services/audio-search -p test_review_pack.py -v` | exit 0；17项全部通过，无failure/error/skipped |
| `python3 .local/b/review-evidence/MUS-024-R1-B/independent_cli.py` | exit 0；83次真实子进程CLI调用，4次成功，79次预期exit 1拒绝；所有预期匹配，0项发现 |
| `git diff --check` | 交付前通过；交付仅两个允许报告路径 |
| 开始与检查点 `python3 scripts/collab.py sync --account b` | 固定入口校验、任务/源SHA/报告哈希核对；发布后另行回读确认 |

83次调用直接执行`services/audio-search/review_pack.py build/validate`，没有导入产品模块、修改REPO常量或复用仓库单测fixture。独立数据包括7条合成曲目、非字典序ID、2条文字查询、1条只用于确认排除的合成audio排名记录。两种top5并集各6条，共12候选；查询保持fixture顺序，候选按数值ID排序，模型分数不入包。owner使用Java Long最大十进制字符串，核对曲目内容SHA/字节/时长/来源/许可及模型、pipeline、run源码SHA绑定。仅有合成声明与记录，不读取或生成真实音频，不编码模型。

四次成功为首次build、初始validate、含0/3分及相邻合法区间的部分合成判断、正相关但不标区间的部分合成判断。初始0已判断/12未判断；部分判断2已判断/10未判断，0分明确计数1次，人工区间2段；移除正相关区间仍可通过。dataset指纹不随四个人工字段变化。所有标注代号为`test-b`，时间是测试fixture，不是真实听音记录。

79次预期拒绝覆盖：

- 外部期望report hash错误，以及catalog和四工件各自字节变化；未重算hash时均失败。
- 重算自有合成report/工件hash后，未知/重复manifest或catalog ID、内容/来源/许可/时长/pipeline不一致、布尔字节数、dirty run、模型维度/strict missing、统计数量、重复或未知查询、文本错配、重复/未知排名ID、top5不足、未知或跨曲目segment、segment毫秒与采样点/补零不一致仍失败。
- 包schema/split/owner/指纹、候选ID/来源ID/内容SHA/字节数/时长/标题/作者/来源/许可/模型建议区间、查询文本/候选增删重复或排序/provenance模型及额外字段的修改均失败；多数篡改还重算了提交包dataset指纹，不能绕过从原运行重建的比较。
- relevance布尔、浮点、字符串或越界，缺代号/时间、含空格代号、无效日期或非规定UTC格式，未判断项却带任一人工数据均失败；空、负、零长、越界、布尔/浮点、重叠、倒序、超过20段区间以及0分带区间均失败。仓库17项还覆盖缺失人工字段、重复JSON键、非有限数、超限JSON等边界。
- 原输出重复build、现存符号链接、悬空符号链接、`.local`外输出及父目录符号链接逃逸均拒绝。首次输出权限实测0600；拒绝后原包字节不变、链接保留、逃逸目标未创建，全部原始输入恢复且与起始字节相同。

CLI的预期失败是有效拒绝检查，不记录为产品异常或“83次成功生成”。本轮无非预期失败命令。未测断电/fsync、部分写入恢复或恶意并发文件系统操作；独占创建不等于这些持久性保证。

## 源码与本机证据指纹

准确实现源码SHA256与A声明相同：

| 文件 | SHA256 |
|---|---|
| `services/audio-search/review_pack.py` | `b9070f2ed73d97cc52f75bd4dcdb02cb9917ce6268ef29bdb81081d0dc2f3b24` |
| `services/audio-search/test_review_pack.py` | `a27e513d0135ea91b5ce421014756fd5c599b6c7dc5f475792a72c199d0c22c5` |

下列为B本机忽略目录证据，可定位本轮输出，不代表已向A交付原始日志：

| 工件 | SHA256 |
|---|---|
| `targeted.log` | `52e3e3aa879eeb38ad638a46a3d94c5c379816515b305b52d22a80557e767f5f` |
| `independent_cli.py` | `723f5494321feeafc840746e06ec60bc21f67ea1185cb0b4843c53120749d2a4` |
| `independent-cli.log` | `1c7a12130e579b9c2f670b693cd71bf61a6f30e7b9ece6e75d1683795a6fd603` |
| `cli-records.json` | `56e379a530e2e841678145c68427bdc2416659f41ad09765700be5c3a879005e` |
| `summary.json` | `71dcd421667aebbebf5763bc739bb7c1678f82d6f0776d88a99c0a19877b6016` |
| B合成原包 `fixture/pack.json` | `dced4ba563c8a703981cc87d2ce16a5f67164a540775b4cd11ad22fb16144cf9` |

B合成report SHA256 `9b8cdda8035a60902ac80db2fff8f99f73452dc90978424ee7f1109b6c5641cb`；dataset SHA256 `5b43d841e1f79f6bd778fc85381bdea7c40ed4d7c6aa54792bdc27658f62d731`。仅此fixture使用pipeline `b-synthetic-10s5s-v1`、伪checkpoint `d×64`及伪run SHA `c×40`；无真实模型/索引版本新增。

## 证据边界与下一步

A的8条文字/51候选全部null、43475字节/0600及其包/工件hash，是A声明的私有运行证据。B没有访问A的run、原始日志、音频、凭据或数据库，未复算这些私有字节。独立合成12候选不等于复现真实51对。

校验器核对固定运行内记录的内容身份与包完整性，不能证明标注代号的身份、是否真人听音、标签可靠性、当前许可或数据库权限。无HTTP、原始音频读取、下载或媒体服务；包不能作为播放授权。后续试听仍须现有JWT媒体鉴权，并在播放前核对SHA/字节。

模型建议可见，存在提示偏差；两基线pool不穷尽相关集合，不是盲评或held-out。没有真实人工qrels、质量指标、时间IoU、性能P95或提升比例结论；MUS-002及discovery-v0仍未冻结。后续由A接收本报告，再分配真实人工判断/试听流程或质量对照任务。

未执行既有40项全套（本卡只需17项标准库测试，未安装旧音频/大模型依赖）、CLAP推理、真实媒体/服务/数据库、Java/Maven、Vue构建或浏览器听音；这些不属于本卡增量。未新增服务器、定时任务、后台轮询或主线合并。

本次提交仅本报告和B latest；GitHub顺序发布任务分支再发布`collab/account-b`，非原子，最终SHA与回读结果由发布交接记录。发布可读不等于A接收。交付后两报告占用释放，无本轮服务/端口占用，无待修源码发现；保持等待A固定入口的下一任务。
