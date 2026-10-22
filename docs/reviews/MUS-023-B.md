# MUS-023-R1-B 导入恢复与来源证明增量复核

## 结论和交接身份

**approve_scoped**：准确实现中的R1注册恢复、R2证明绑定、条件性R3公开链接规范化及必要回归通过；建议A在接收后关闭MUS-016对应三项发现。本增量未发现新阻断问题，不代表整个导入器、生产许可、MUS-022质量或main合并。

- task / owner：MUS-023-R1-B / B；assignment_revision：1；status：review_completed。
- branch：`review/MUS-023-B-demo-import-recovery`；base / reviewed_sha：`ab8205827456ec6aeab3bcb289722a236e644f6b`。
- comparison_base_sha：`81566b1634aa19cb8493d2c2740c6d002a75ba4e`。
- assignment_source_sha：`ec6317cce9c178a27063fcbb8c2ef3c4953727b5`。
- ack_peer_feed_sha：`6577bed0dea8389f94215efdb50a4ad02c4e769f`；开始和结束前检查点sync exit0，双方fetched，A未变。
- 先认领source `ca4c12430f8560d073c5a4b0c2d7a39c78d29795` / B feed `2ceb01bc157315d10f7afb1e172546555edef94b`，主动发布回读后执行审核。最终交付SHA见handoff.source_sha。
- 只改本报告和own latest.md，无产品、A台账/任务卡、接口/schema/依赖锁修改；两报告活动占用释放，main未合并。

## 范围与静态核对

按准确A source读取派发、完整卡、CONTRACTS A11、MUS-023验证/结果JSON与MUS-016接收记录。A导入MUS-016-B与B source `0c5efad944e8f546498d7791019060ca5967b40b`原文逐字节一致，报告SHA-256 `16566f87e707bfc34c87e141c4a2863b52054972a7e1730d8fb925d656ad8485`。历史request_changes保留，不重新执行016全13场景，也未重审017/019/020/021/022。

- `scripts/import_demo_music.py:86` / `:115`：先核对pending/confirmed与凭据指纹，pending仅对原login明确business500/准确Invalid email or password重试同凭据注册；profile为USER、目标ID一致后confirmed；confirmed失败不回退注册。异常状态/指纹保留失败，LocalApiError的公开str不直接输出server_message。
- `scripts/import_demo_music.py:125`：缓存大小、SHA、必需字段、来源ID和准确CC BY版本绑定；`:27`/`:39`提供一致规范化，旧http许可仅同准确路径等价。错误证明不会被重造或重新下载掩盖。
- `scripts/import_demo_music.py:27`及新证明/manifest写入：输入来源匹配HTTPS主机/ID且无userinfo/异常端口，输出按ID构造canonical页，不复制query/fragment/slug；许可query/fragment/userinfo拒绝。
- `web/src/utils/catalogLinks.js:2`与DemoCatalogView导入：链接helper移除不允许的数据，Apple仅保留单一正整数i。Vue diff只有helper导入/删除内联函数，template/style/owner与导航未变；两个公开JSON原字节保留。
- Java目录树与既有B编译输入相同 `8761503685932be8c7ab7bd2ad94e357860ecf3d`；POM、schema、依赖锁和模型代码无本卡变更。

## 命令和真实结果

使用独立B clone，复用私有Linux MySQL8.0.41兼容库/TCP包装、Java17.0.20、Python3.12.14及逐命令生成的Maven代理设置/独立缓存。每轮新建`/tmp/music-b-import23-*/checkout`、空slot B库及上传目录，准确checkout目标SHA。catalog输出由一次性副本承接，审核checkout已跟踪公共JSON未改；不访问A3307/8080/5175、账号/Client ID/原曲库。

| 命令/运行 | 结果及边界 |
|---|---|
| `python3 -m unittest discover -s scripts -p 'test_demo*.py' -v` | exit0，17项，0失败/错误；含原5保护与新12恢复方法。本地API/提供方均为仓库测试替身，不是真库证据 |
| `node --test web/src/utils/catalogLinks.test.js` | 初次系统Node24.19.0为8项exit0；另下载并按官方SHA核对项目Node22.23.3，以其bin/node运行同命令亦8项exit0，0失败/跳过，不相加。实际helper与现有20来源/许可+20外部资料链接；纯函数/静态数据，不冒充浏览器 |
| `python3 .local/b/runtime/run_mus023.py`首轮baseline-20261022-051042-23 | exit1/status blocked；私有JAVA_HOME/bin/java链接缺失，后端未启动，业务检查0。MySQL停止、端口释放；仅恢复B私有链接，不改产品 |
| 同入口最终baseline-20261022-051143-11 | exit0/status passed；15组增量fixture、39次实际run/_run、84条预期断言，其中39条锁清理、45条其他断言；无新发现 |
| 最终运行的后端启动 | `sh ./mvnw -B -ntp -s <B-settings> -Dmaven.repo.local=<B-cache> -Dmaven.test.skip=true spring-boot:run`；按需编译90个Java源文件，未执行Java单测；真实JVM/MySQL/HTTP就绪 |
| `git diff --check`、限定路径/源码/JSON/报告字节核验 | 通过；source/feed发布后另作远端回读 |

不将首轮blocked与最终成功相加，不把84条断言写成84个独立HTTP场景。B未新跑A的全scripts62、旧业务负例、前端npm ci/build、完整UI/player/media或Java单测；本轮只改纯链接helper，8项覆盖现有目的页，Vue模板未变，未无理由重建整个前端。Maven启动编译不是Java测试通过。

## R1：真实恢复与状态边界

源API/音频仅在urlopen边界提供合成Jamendo结构和60秒MP3，原eligible/validate/URL校验及TLS context保持；其余正常本地API为真实Java/MySQL HTTP，独立SQL核对计数。以下三种注册状态分别建新普通账号，凭据文件字节保留、状态0600、指纹与确认userid匹配实际数据库，最后每组恰好一个账号/上传/资源：

| 故障 | 第一次与取消故障后的观察 |
|---|---|
| 凭据保存后、register尚未送达 | 私有transport在送达前抛URLError；首次login/register尝试/回查login后保持pending，真实SQL账号/上传/资源新增均0。重跑同凭据先login，再实际register/login/profile，转confirmed |
| 明确register拒绝 | 持有本次新库users的READ表锁，观察本次B JDBC连接35的INSERT处于Waiting for table metadata lock，仅取消该等待语句。原controller返回HTTP200/business500，事务未建号；未替换拒绝响应、未改产品SQL/schema。释放锁后原run回查login并保持pending，重跑同凭据成功 |
| register实际成功、响应丢失 | 私有transport读取真实成功响应后抛URLError；原run当次fallback login/profile就转confirmed并继续导入。后续重跑无第二次register，账号/上传/资源不重复；不强制首次失败 |

明确拒绝是只针对自建B数据库和自己等待语句的故障注入，不是整库中断、服务进程kill或生产DB故障证明。SQL holder正常关闭，未取消他人服务或连接。

其他必要状态分支：

- legacy凭据对应真实已建账号，删除新状态fixture后重跑仅login/profile确认，无register/新对象；完整缓存不调用提供方。
- confirmed后由普通用户原change-password HTTP改自身密码，再以原凭据run，真实login拒绝；不再register，confirmed原字节不变。
- pending网络错误在发送前模拟；其他business500分类在真实login HTTP后仅替换message。这两个分支都保持pending、不register；后者是响应故障fixture，非真实服务器生成该特定消息。
- locked分支是真实服务判断：只用SQL把本轮新建普通合成账号is_locked置1，再实际login，原返回锁定拒绝；pending不register。无管理员提权/真实用户改动。
- 凭据指纹变化、未知/损坏状态、缺指纹均在本地API前失败，原状态不覆盖；confirmed记录的目标ID与真实profile不同也拒绝，不register。nonUSER是实际profile HTTP后仅改role字段的fixture，数据库仍USER；该分支验证confirm保护，不冒称数据库已提权或真正管理账号测试。

接口身份错误分类按本卡冻结的旧login envelope验证，没有额外承诺权限撤销、所有上游数据库错误分类或账号系统整体安全。

## R2：证明失败保持与离线兼容

正常首次导入后，以同一真实MP3与正确SHA作逐字段变体：size错误、size为bool、source错误域/错误ID/异常端口、license换准确版本、license附query，以及分别缺size/sha256/source/license。原run均在本地API前失败，无提供方重查、本地对象无变化；原音频和故障证明保留，不重造证明。对于七个字段值变体还逐字节核对旧result.json未更新，没有把旧passed文件误称本次成功。

完整合法缓存正常重跑不查询提供方、不下载、不新增本地对象。旧http CC BY 4.0与https同准确版本、旧同ID来源slug/query/fragment经规范化兼容，证明原字节不改，导出仍canonical。此为B合成旧格式兼容，不是访问A原20份证明，也不声称实时重新核验提供方许可。

## R3：公开链接与必要回归

合成shareurl含slug、Client ID canary query和fragment时首次实际run通过，新download.json只保存canonical source/license，公开catalog无canary或fragment。错误source host/ID/端口/userinfo及许可query/fragment/userinfo分别在下载/本地API前拒绝，无新账号。

8项node链接检查验证当前20条曲目与20条歌手资料目的页保留；四允许主机/HTTPS限制、Jamendo/CC canonical、Apple只保留单一数字i、重复/非法i拒绝、userinfo/异常端口/伪装host/危险协议拒绝。没有改布局或访问真实Jamendo/Apple接口；这些是条件性输入/公开边界补证，不指认A曾泄漏秘密或原证明错误。

## 工件与未验证内容

数据版本为B23合成fixture，单段60秒440Hz MP3 SHA-256 `d6ed17e8cd1ad9f927ec8db24940a0531692b353578f01c9f897369644d8c215`；新V001/V002空库，初始化SQL SHA `e2c4b01537dabdf01354faabf4876821cdae7de7cc549809ee1a60708c99146e`。最终6个新普通账号、5上传、5资源，含1个仅用于锁定负例的账号；不是A曲库或新增模型/索引。

原始日志/私有工具/音频/库未交付。A只能核对报告字节与声明，不能冒称重算以下原始指纹。路径位于B私有`.local/b/review-evidence/MUS-023-R1-B/`，运行名保留工具实际ID，日期显示不代表用户时区。

| 工件 | SHA-256 |
|---|---|
| python-demo.log（17） | 8dd299ddc68e1c4481c8c16801768a1b6b2b98bfb9e630dc6b7d3dc75b1f9a28 |
| catalog-links.log（初次Node24，8） | 7009fdd197d75aeb9eaac5256a998332b53faa869c077d36c475639cbd11a20f |
| catalog-links-node22.log（项目固定版本，8） | 0b6ec95dbd2ce6419db8164dc3a0d4afdc32f5fdad257048fead9fe90873c63a |
| 首轮blocked result.json | 1b947861a29c06a5625192114b90d1baf827b630f81bc7a8e40cb43362d74ff8 |
| 首轮backend.log | 69415e1a7cb13c0b8877a38fa8537ba860cd8165fb80c2ec9c6d8a2bce840802 |
| 最终result.json | 08ee3f77e659f288bef920c679d12fdc287879c3dc81e04a291096c65532a0a7 |
| 最终importer-result.json | d5f727948fecd1feba6e400d5960234aa9b343dd81ea1d2b30b667e065484561 |
| 最终summary.json | 08bb492a588ee7149be740a852bdad14e924620249309dbd65f0cf92e2543d44 |
| verified-review-evidence.json | a0a02ba546d0e7d4cebad68ea1fae8cc12fc4ab6765ae6edcdb814b86b310e85 |
| 私有run_mus023.py | 3bf208845b29186751d4ba2ed37e880164f85f5af63d435197111f282d0db1ab |
| 私有native_mus023.py | fe0740ccda5c0cd3c8e9db86aa329f804b2e945025c5622103179038c476fc16 |
| 私有mus023_harness.py | 97ab1084b06fbff79e34ac9e62fb15386eb7bd8b5669fc1a42b64c73d1b8f0b6 |

未做真实提供方下载/实时许可/法律或生产结论、真实浏览器UI、断电/fsync/kill进程持久性、整库中断或commit ACK丢失。没有重跑旧016上传ledger/metadata/歧义/空结果全矩阵，未修改或评价MUS-022的51个空标签与模型质量。正常注册恢复新增的HTTP/SQL补证仅本卡范围。

Node22.23.3官方Linux归档SHA为`df450af89261115ef9f9e3830c3eeb2cc9213b63c720b1af623cb5dcbe2e02de`，仅用于固定运行时复核链接；未因此npm ci或改依赖锁。

每轮自建MySQL/Spring及自有SQL holder已停止，3308/8081释放；没有A服务重启/升级或旧库写入。下一步A接收限定批准、串行更新对应发现/台账并派发；两报告占用释放。

沿用已授权GitHub插件先源码任务分支后collab/account-b，顺序非原子，没有配置新原生Git写凭据。最终source/feed回读成功后才记已发布；精确交付见handoff.source_sha。发布不等于A接收或main合并，不启动后台轮询。
