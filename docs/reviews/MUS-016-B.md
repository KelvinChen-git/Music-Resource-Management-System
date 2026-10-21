# MUS-016-R1-B 演示导入器首次独立审核

## 结论与准确交接

**request_changes**：2项P2（R1注册失败恢复、R2缓存下载证明一致性），另有1项P3条件性来源URL公开边界（R3）。正常重复导入与若干中断恢复已实证通过，但不能据此批准全部故障幂等或真实来源许可。只提交报告，最小修复交A协调。

- task / owner：MUS-016-R1-B / B；assignment_revision：1；status：review_completed；2026-10-21 America/Chicago。
- branch：`review/MUS-016-B-demo-import`；base / reviewed_sha：`69a3965e88d37d71a0067f263d207f2cb62fe668`。
- original_implementation_sha：`3092ae273e4a448246b8272fd20f3cd7de37dc91`；comparison_base_sha：`dbb631218b8ee7c87823ce594494b908b2849e32`，只定位MUS-016原新增范围。
- assignment_source_sha：`ebae5eb9fba158152aa8f3061b25fb93f502e95a`；ack_peer_feed_sha：`596642d75c8d3186650f7c6790313d3f371b5553`。开始及结束前sync exit0，双方fetched、A未变。
- 先主动认领 source `0c8d43a27c28d19e6ab8108ef66ff353abc29b1f` / B feed `42b32b1a61c2602f48703458c9c21c4e746af324`，远端回读通过后执行审核。最终交付SHA由handoff.source_sha给出。
- 修改仅本报告及own latest.md。无产品代码、A STATUS/任务卡、接口/schema/依赖锁/模型/索引修改；报告活动占用释放，main未合并。

## 发现

### R1 / P2：注册前失败后，已保存凭据导致重跑永远跳过注册

位置：`scripts/import_demo_music.py:165–174`。首次先atomic_json保存demo-account.json，再调用POST register；后续仅以文件存在判定已经注册，直接login。持久化凭据是必要的，但它不是注册提交成功的证据。

**真实本地HTTP补证**：在urlopen边界注入注册发出前的URLError；独立SQL证明本次未创建用户，凭据文件已存在。取消故障后原run重跑，实际只调用login，返回业务错误 `Invalid email or password`；没有第二次register，数据库账号/上传/资源计数均不变。缓存与凭据保留，但正常重跑不能推进。相反，服务器注册已成功、仅响应丢失的独立场景可以正常login恢复，始终仅一个账号；不能把后一成功概括为前者也可恢复。

影响：首次网络失败、进程在凭据写入和注册之间退出或明确注册拒绝时，需要人工处理私有文件，脚本声称的可恢复导入不完整。建议区分“凭据已保存/注册待确认/注册确认”状态，保留同一凭据；重跑先确认自身账号，未确认时安全重试同一注册，已有账号冲突或凭据不匹配时保留现场并给出明确恢复状态。不要删除凭据或生成第二套随机账号掩盖问题。补注册前中断、明确拒绝、成功响应丢失的独立回归。

### R2 / P2：缓存证明只比SHA，来源/许可/大小不一致仍标passed

位置：`scripts/import_demo_music.py:125–128`；初次证明写入在`:143–144`。完整缓存重跑仅检查proof.sha256与当前音频，未检查proof.size/source/license与真实字节及选曲记录的绑定。

**篡改fixture实证**：保持本轮合成音频与正确SHA，单独把已有download.json的size改1、source改为不同域、license改为不同许可地址。实际run仍完成，HTTP完整音频校验也通过，返回passed并生成公开catalog；伪造证明内容未被拒绝或改回。原文件与证明是B主动修改的隔离fixture，不宣称A的真实证明错误，也不证明原音频没有许可。

影响：误配、损坏或手工拷贝的证明可以被当作完整缓存证据继续使用；“字节相同”不能证明来源/许可/大小记录自洽。建议严格校验证明结构、字节长度、SHA、来源和准确许可与本选曲记录一致，异常保留现场并失败；缓存重跑仍可不联网，不要求把原下载证明变成实时许可查询。不要仅重新生成一份证明覆盖不一致。

### R3 / P3：上游来源URL原样进入公开JSON，允许携带敏感query

位置：`scripts/import_demo_music.py:27–43`未核验shareurl；`:224`/`:232`直接公开它。`DemoCatalogView.vue:16`的safeLink检查协议/host但保留query（也未排除userinfo）。

**条件性provider fixture实证**：仅在合成上游shareurl添加与本次配置相同的Client ID canary query，其他授权字段和下载origin均满足原eligible；原run通过并把该query完整写入一次性副本web/public/demo-catalog.json。独立执行原safeLink也保留该query。正常fixture的公开catalog没有Client ID、账号邮箱/密码；仓库现有JSON也未发现这些秘密字段。没有真实提供方反射/泄漏或A现有catalog泄漏的证据。

影响与建议：公开输出的“不含Client ID/下载URL”保证依赖上游来源字段规范；页面路由需登录也不会替公开静态JSON移除秘密。建议按来源构造/规范化HTTPS原页URL，排除userinfo、意外域/协议和敏感query/fragment；公开只保留可审查的来源字段。此项单独是输入/发布边界加固，不作为已发生外部泄漏或法律结论。

## 已验证范围

按当前A source读取任务卡、CONTRACTS/STATUS与MUS-016验证/结果。五个限定文件与原3092ae2逐字节一致：导入脚本、5项保护测试、demo-catalog.json、artist-references.json、DemoCatalogView.vue。MUS-021接收JSON指向本账号真实交付，A导入MUS-021-B与原文逐字节一致；不重审017/019/020/021，不批准A新增MUS-022模型/离线结果。

静态核对eligible：显式True下载标记、CC BY 2.0/2.5/3.0/4.0准确路径/域、HTTPS子域下载与无userinfo、ID/60–420秒界限；选曲按ID/作者去重并排除remix。下载最多30MiB+1、最终HTTPS Jamendo子域、拒绝空/HTML；没有不安全TLS设置。仅完整缓存重跑不重新查提供方；缺部分证明时重新查询选曲ID，原选择失去资格则失败。没有把许可URL/布尔值当作真实授权核验。

**本地真实链路**：每轮新临时clone/slot B/空MySQL8.0.41 V001/V002、8081 Java17；不访问A的3307/8080/5175、用户/凭据/曲库。两段ffmpeg生成的60秒440/550Hz MP3。Jamendo API与下载在产品urlopen边界返回合成结构/字节，保留原eligible/validate/URL断言/TLS context验证；不联网取得任何提供方音乐/Client ID。所有正常本地register/login/profile/check/upload/metadata/list/media请求为真实HTTP，观察连接只读SQL计数；没有提权、自动审核、迁移旧库或邮件。catalog输出只覆盖一次性原生临时副本，不修改审核checkout的已跟踪JSON。

| 主运行场景 | 具体观察 |
|---|---|
| 首次2首导入、完整缓存重跑 | 首次1普通账号/2上传/2资源；206前64字节和200完整SHA验证；重跑不新增三者，不再调用提供方JSON/下载 |
| 缺一个下载证明、重新查询 | 查询原2个ID，只重下载缺证明的1首；本地账号/上传/资源不增加 |
| 证明JSON损坏、SHA不匹配 | 在本地API前失败，保留现场；不同于R2“其他字段错而SHA对”的静默通过 |
| 部分缓存重查资格变更 | 失败在本地API前，未放宽下载/许可条件 |
| 注册提交前失败、成功后丢响应 | 前者R1；后者恢复且不重复账号 |
| 上传成功/ledger写入前、写入后中断 | 后续实际run复用upload，补齐metadata，始终本场景1上传/1资源 |
| metadata成功响应丢失、后续lookup传输失败 | 重跑查到既有资源，不重复上传/metadata；二者独立场景 |
| 两条同元数据资源 | 私有fixture经普通HTTP创建不同标题的第二资源，再用owner编辑接口改同名；原run检测歧义并失败，无新增写入 |
| 唯一同元数据但音频不同 | 实际完整媒体SHA检测不匹配，未生成该场景passed result；没有仅凭标题/作者/专辑宣称绑定正确。场景保留了多出的自有上传，未假称自动清理 |
| 下载最终origin错误/超限/HTML | 源响应模拟，原校验在注册/上传前拒绝 |
| 来源query canary | 条件性R3，明确不是正常现有JSON泄漏 |

主运行13场景/26次run调用，52项预期检查中包含26次lock清理断言；它不是52项独立HTTP场景或52项无缺陷批准。3项发现单列，整运行status为review_findings。

另用新库**只补无结果分支**：metadata真实创建成功，实际GET list之后私有urlopen响应fixture仅一次把records改空，原run报Imported resource lookup failed并保留ledger。取消fixture重跑复用原账号/上传/资源，新增均0。这个“空结果”是故障响应模拟，不称真实后端自然返回空；其余请求是真HTTP。该补验2次调用/4项检查，未重复13场景主矩阵。

## 命令、失败及证据

环境维护已清理前次scratch/旧私有日志与工具；本轮从远端重建独立B clone，历史已发布报告可读，但不声称旧私有原始证据仍能重算。复用系统Java17编译模块的私有javac启动器、Maven当前代理/独立缓存；原生MySQL官方8.0.41归档SHA `f50bbb1611955ace3993f84590ecfd636d3b83550799110f8fcddb04601b7219`。首次兼容库URL404/503、库路径/执行位探测失败后，按官方Ubuntu目录取得私有libaio/ncurses5/tinfo5并修正启动器；未改系统配置或产品。

| 命令/运行 | 实际结果 |
|---|---|
| `python3 -m unittest discover -s scripts -p test_demo_music_import.py` | exit0，5项，0错误/失败；不是历史50项 |
| `sh ./mvnw -B -ntp -s <B-settings> -Dmaven.repo.local=<B-cache> -Dmaven.test.skip=true compile` | exit0，为恢复真实HTTP服务编译90个源文件；没有执行Java测试 |
| `python3 .local/b/runtime/run_importer_review.py`首轮baseline-20261021-075629-11 | exit1/status blocked；私有歧义fixture直接创建重复元数据，被现有后端保护拒绝。console保留40条已完成检查/2条发现，非整命令通过；当时未写progress JSON，数量来自保留console |
| 修正私有fixture后同入口baseline-20261021-075843-10 | exit0/status review_findings；主矩阵52项预期断言、3项发现；最终9普通账号/12上传/11资源含故障残留，不误称全部正常导入数据 |
| `B16_ONLY_EMPTY=1 python3 .local/b/runtime/run_importer_review.py`，baseline-20261021-080006-10 | exit0/status passed，仅额外空结果恢复4项；另一新库，不与主矩阵/首轮数量混为一次运行 |
| `node .local/b/runtime/catalog_checks.cjs` | exit0，9组必要目录检查；执行原safeLink/owner计算/router guard/Sonora load提取代码，store/API为替身；JSON与模板静态检查，不是浏览器/真实UI/HTTP |
| `git diff --check`、JSON/源码/限定路径与原报告字节校验 | 通过；最终发布后再回读source/feed |

目录9组覆盖4个允许HTTPS host/拒绝伪装host及危险协议、现有20唯一目录ID与来源许可、Post Malone/Drake各10资料且audioImported=false/无preview或封面字段、owner数字/字符串ID提示、外部区无播放/曲库链接、匿名真实guard代码跳login及普通登录允许、当前Sonora load保留含空格/+中文keyword。没有重新执行完整UI/前端安装/build/Java单测/全Python套件，不拿A历史浏览器通过当B新运行。

私有日志/适配器/库/音频未交付。A可核对报告字节，不能声称自己重算以下原始证据。以下路径均在B的`.local/b/review-evidence/MUS-016-R1-B/`；运行名按工具实际ID保留，不以host时区推断用户操作时间。

| 工件 | SHA-256 |
|---|---|
| backend-compile.log | 6a44be45846ae1cf844213e36bdc7cf3a9858458c6743fb37a9b39c9e111c804 |
| repository-guards-result.json | d552bc9b5a78d5df07a00920c0252b738ce54bf456bf3d5663be364c4e348cea |
| 首轮native-console-20261021-075629.log | 100e60e70e5edb5555048b12925ac655f5541d43672de01087d8b35a7bf7a637 |
| 首轮blocked result.json | 4191884651bb3aaa81faaa27011aa60cdeddcc1cc20194fb699887a842b901a4 |
| 主运行result.json | 817eb09d1211b3892673d0044f138020c2f238c14ad846da6d80e5c24162b681 |
| 主运行importer-result.json | 254f1dda83ebb0900dbc5953308558486ff077636331baee703e0aafb159e070 |
| 主运行summary.json | e2b43de78c379d431e8646de5e056aa17b26e1b0f79c1c020640db18d55368af |
| 补验result.json | cc2c7da7e1612bdeb9e8c0d71b9aefc316aa3229ae75f73f48e53b9e7a0ec437 |
| 补验importer-result.json | 323097d67012de123c5ffa1c0727e3b84cf5282d4fbfa9c598cf6a0f089d321b |
| catalog-result.json | 44e1939eb92d987b23b94da1a80492eac3b76e898958d212199f5587f9a01933 |
| verified-review-evidence.json | ad1792fb618a149a4dec2574915981c6675df943e71aa3edbb77523359cb81e1 |
| primary-executed-importer_harness.py | 6d5ba0f6c65addca1cfa6b6cc3921535aa27ed58a161af1b4943a067c970d258 |
| 当前私有harness（含额外空结果分支） | 9d4961ebfb45afca1395671e28439070b0678cccd2e0dc6d7aa4137d9e8ee8ec |

数据版本为B16合成fixture，新V001/V002库，60秒MP3 SHA分别`d6ed17e8cd1ad9f927ec8db24940a0531692b353578f01c9f897369644d8c215`、`74dda243dcaabf98567b1cc8e64f33a685f0932f03ffda3ba08ab1bbc7212afc`；没有新模型、checkpoint或索引。私有schema初始化为新空库，不迁移/清理A已有数据。

## 限制、下一步与发布

未访问真实Jamendo/Apple歌曲接口或重新核验现实许可；未下载歌手区音频/试听/封面。未做人听相关性、生产授权/服务升级、真实浏览器UI、杀进程/断电文件持久性、整库故障或commit ACK丢失。私有异常注入不等于真实进程崩溃。现有公开JSON是元数据/声明，不证明别的clone拥有音频或资源权限。

每轮自建MySQL/Spring均停止，3308/8081确认释放；无A服务操作，无提权或自动审核。两B报告占用释放。下一步A接收request_changes，按R1/R2协调最小修复、评估R3，再派准确提交增量复核；不由B直接改实现/STATUS/任务卡，不重领旧任务。

发布沿用已授权GitHub插件先源码分支、后collab/account-b，顺序非原子；没有配置新原生Git写凭据。source/feed回读成功后才记已发布，精确交付以handoff.source_sha为准；发布不代表A已接收或main合并，无后台轮询。
