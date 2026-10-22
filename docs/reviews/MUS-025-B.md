# MUS-025-R1-B：试听与判断工作区独立审核

- task / assignment_revision / owner：MUS-025-R1-B / 1 / b。
- status / verdict：review_completed / approve_scoped；2026-10-22（America/Chicago）。
- reviewed_sha：`cdc2fc5c00dbc4c2889068023d9d37ce8744a532`。
- comparison_base_sha：`133fecbcda96585a09d6e0cf67af608c768c9151`。
- assignment_source_sha：`c382cbc412accd090429c836314e6a3d0b9d78fc`。
- ack_peer_feed_sha：`c674c7073b0bb05e93deecc16c867846ca630012`。
- branch：`review/MUS-025-B-listening-review`。交付SHA由B feed根目录`handoff.json.source_sha`记录。
- 审核前已主动发布领取并回读：source `9323b99d5934386b9d9cd032554d25b75ea5d3af`；feed `37f380760fe8802c5ed7face90c183eac2bedfc4`。

## 审核结论及修改边界

在准确7文件增量、任务卡与CONTRACTS E2范围内未发现阻止接收的问题，限定批准。审查全部新增view/helper/tests、App菜单与router登录路由；比较范围仅7文件、538增/2删。浏览器只核对包结构与自洽指纹，仍需原run CLI认证候选绑定，页面和包都不授予媒体权限。

B使用独立Linux clone；实际服务再次在准确实现SHA的独立临时clone运行，slot B：MySQL3308 / Java8081 / Vue5174，未访问A8080/5175/3307或A私有账号、包、音频、缓存、数据库。只有两份B报告提交：本文件及`docs/collaboration/account-b/latest.md`。所有工具、运行数据、导出与截图留在忽略的`.local/b/`；未改产品、Java、Python、schema、依赖锁、公共JSON、A台账或备份。

A已正式接收024限定批准，导入报告与B原文逐字节相同，SHA256 `0d3e9f7ae49ccf33fec213785a82018753a9ed7361d1821df353fc070bfb22d2`；未重复024的83CLI或将024批准外推本页面。

## 命令、结果及计数

| 执行命令 / 范围 | B实际结果 |
|---|---|
| Node22.23.3 `node --test web/src/utils/reviewPack.test.js web/src/utils/reviewAudio.test.js web/src/utils/media.test.js` | exit0；21项（8+7+6），0失败/错误/跳过；含fake audio/fetch，不称真实HTTP |
| 固定Node22/npm10.9.9，在`web/`执行`npm ci`和`npm run build` | 两命令exit0；安装244包，使用现有lock；保留既有>500kB构建警告与Node实验性代理提示，未升级依赖 |
| `python3 .local/b/runtime/run_mus025.py` 最终运行 | `baseline-20261022-143336-11`，exit0/status passed；37项浏览器断言全部通过，0产品发现 |
| 子进程真实浏览器 | 官方Chrome Headless Shell151.0.7922.34 + Playwright，真实HTMLAudioElement/HTTP；前端固定Node22的Vite dev，构建另已验证；私有Linux无Unix socket适配用single-process/no-zygote，不改产品 |
| 两个合成输入包 `review_pack.py build` | 每个exit0；2真实上传的合成MP3、2合成文字查询、4候选对，初始人工字段全null；两普通账号分别有owner匹配包，无模型推理 |
| 浏览器4份导出 `review_pack.py validate --run-dir <自己的run-1> --catalog <自己的catalog-1.json> --report-sha256 17ed0a7454e6d7e02783a7fe7f1ca2a3198fe25d0a00882250b5fdeb9d3b25b6 --pack <导出文件>` | 4命令分别exit0；固定run重建通过，不把四次算四个人评或加进21项 |
| `git diff --check` / 允许路径、源码及锁指纹 | 交付前通过；产品与lock无改动 |
| 开始与检查点 `python3 scripts/collab.py sync --account b` | exit0/fetched；上述A feed及派发保持；交付后再回读源码报告和自身feed |

37项为最终一轮的断言计数，不是37种互不重叠的HTTP场景，不加前期已完成检查、不加21项或A的结果。后端以`-Dmaven.test.skip=true spring-boot:run`编译启动，未运行Java单测。数据库11表与V001/V002仅属于B新临时库。

## 真实浏览器及HTTP证据

- 匿名深链跳`/login?redirect=/research/review`；正常UI登录，匹配owner文件导入后评分/人工区间/匿名代号均未预填。错owner导入拒绝并保留原有部分判断。重复键、数字拼写、未知字段、同曲目一致性与多段重叠等由源码和21项中的包测试核对，不冒充全部浏览器负例。
- 显式评分0得到1已判断/3未判断；刷新后重导入仍以文件全null开始，只有“恢复本机草稿”才返回0判断。显式3分和人工1–2s区间、第二候选0分可导出；99s越界拒绝，模型建议1–3s未自动写入人工字段。清除本条判断恢复四字段null。
- 实际获取自己上传的MP3，经完整SHA/字节校验建立Blob，1–3s片段观测起播1.000s、解码时长12s；取点实际写入1.166/1.166秒输入框，没有自动保存人工区间。终点前的真实pause调用位置2.999840s，随后src释放、元素时间重置0、UI显示0:03；这是浏览器精度，非采样精确剪辑。
- 每次重播重新GET。全部已记录11个媒体响应分为10个审阅响应与1个旧全局播放器响应；审阅均无query/pay/JWT URL，除测试侧剥除Authorization的401外均有Bearer头。旧播放器自身的一次`pay=true`请求保留其原行为，单独归属；没有把它误记成审阅请求。取消的请求不一定产生response，不以响应数表示请求总数。
- 自洽包重算指纹后仍故意写错内容SHA，真实音频获取后被拒，未附src且取点disabled。切候选取消请求：测试侧先获取真实授权字节，控制延迟交付，再释放迟到响应，未恢复旧src；只有传输时序受控，不是fake音频或假后端响应。离页销毁审阅audio，播放中退出后音频节点为0，重登需重新导入。
- 真API由owner软删除自己的资源，重新试听返回404，无src；随后真回收站API恢复该资源。第二普通账号导入自己的自洽包仍无法读取第一账号pending资源，真实404。针对第二个自建普通账号，仅在私有文件IPC请求后由B夹具SQL将其is_locked设true，再重播真实403，无src；随后恢复false。该403是锁标志SQL夹具，非正常管理员HTTP操作，也未赋予角色权限。
- 401通过测试侧仅删除媒体请求的Authorization头，让真实后端拒绝，未伪造响应体/状态。这些负例产生4条预期浏览器HTTP console error（404/401/404/403）；0未捕获pageerror，不声称warn/error列表全空。后端既有SQL解析/Druid诊断保留，不在本卡扩大修复。
- 全局播放器实际播放后开启审阅会暂停它，队列仍为2首；再恢复全局播放器会停止并释放审阅src。双方均使用真实HTML音频；队列弹窗实际检查，未用fake pause hook替代本项。
- 草稿写入故障仅对`sonora:review:`键的Storage.setItem注入QuotaExceededError，登录存储不变；页面提示未保存，仍能导出并通过CLI。第二账号不显示第一账号草稿；返回第一账号重导入后可显式恢复原草稿。按owner/dataset的键与不可变包比对另有单测，未宣称跨设备同步。
- 390×1000与1440×1000的document.scrollWidth分别390/1440，长标题100个字符，无横溢；手机端实际点击评分、填写/保存区间并导出成功，未只凭isVisible判断交互。截图已视觉核对。早期Linux缺中文字形，最终使用私有Noto Sans CJK字体，未改前端样式；full-page截图内固定播放器的位置反映截图方法，不是整个长页面都固定遮挡。

四个最终浏览器导出分别由原合成run CLI验证：

| 文件 | 已判断 / 未判断 | relevance计数 | 人工区间数 |
|---|---|---|---|
| `browser-zero.json` | 1 / 3 | 0分1个 | 0 |
| `browser-partial.json` | 2 / 2 | 0分1个、3分1个 | 1 |
| `browser-quota-export.json` | 1 / 3 | 2分1个 | 0 |
| `browser-mobile.json` | 1 / 3 | 2分1个 | 1 |

这些是明确`test-b25`代号的自动化合成判断，不是真人听音。后两个是离页后重新导入文件的工作状态，不与前一个导出累加。CLI统一返回identity_or_listening_verified=false。

## 保留的失败与校正

| 运行ID / 准备命令 | 原结果及原因 |
|---|---|
| Playwright常规浏览器安装 | exit1；CDN包损坏及stale lock异常，业务0项 |
| 官方完整Chrome下载/启动准备 | 下载193282658字节、ZIP完整；可选sandbox文件名chmod错误导致命令exit1；随后一次hydrated执行权限EACCES、一次完整Chrome process_singleton失败，均业务0项；改用同版本官方headless-shell并同调用chmod后预检通过 |
| `baseline-20261022-142817-14` | exit1/blocked，浏览器0项；夹具196字符标题违反既有100字符API限制，缩至合法100字符，不改产品或数据库绕过限制 |
| `baseline-20261022-142859-11` | exit1/blocked，12项通过+1检查断言失败；检查脚本错误地要求释放src后元素currentTime仍约3s，实际HTML元素重置0；改为观察真实pause前时间及释放后状态 |
| `baseline-20261022-142957-11` | exit1/blocked，30项完成；脚本误等跨账号访问403提示而超时，实际契约返回404；按真实不可见资源策略更正，另以自建账号锁夹具补403 |
| `baseline-20261022-143148-11` | exit1/blocked，34项通过+1检查断言失败；脚本混计旧全局播放器pay请求，改为发起时记录用途并分别核对，不改产品请求 |
| `baseline-20261022-143336-11` | exit0/passed，37项通过、四导出CLI通过；不与上述轮次计数相加 |

所有五轮本机服务均已按本次登记的进程停止，3308/8081/5174逐轮及最终再次确认释放。前期命令的blocked不改写成passed，也不将夹具/检查错误归因产品；原日志和截图保留。

## 版本与证据指纹

真实上传的是12s/14s的440Hz/660Hz合成正弦MP3，96592/112475字节；SHA256分别`43840266e5d2985aed1ab2f196d481c67cca1ec59569551bcccb64d7a2aecdf1`、`59a961c0a44da925d31da0c6e8fb012b52133f9a26d0f7b2c9c9a428b37711ce`。实测解码12000/14000ms写入固定manifest。来源URL仅合成身份字段，未访问提供方、无来源/许可真实性结论。

合成pipeline `b25-synthetic-fixture-v1`、伪run源码`e×40`、伪checkpoint `f×64`，明确不是模型实跑。主fixture dataset SHA256 `ae2b840c3838a17c80f54ad727bd96ae08982b4f295bb661407bba8425d07172`，第二owner dataset `ad8cf138aca0c9d1ef57ccb89ae3bc6513473fbea3f882a8aa0fd72a632aa998`；无真实模型/索引版本新增。

全部7份实现文件SHA256与A的MUS-025-results.json相同；三个主要文件为：

| 文件 | SHA256 |
|---|---|
| `web/src/utils/reviewPack.js` | `2fd937d5f0bf94c9df7ba58a61c63e996ddcd54673ea1e0634740494db8c6994` |
| `web/src/utils/reviewAudio.js` | `0da0be1e8fd3e6e3f93383d69834ff3bfa5a13136033618d0863dd86545ce624` |
| `web/src/views/ReviewWorkspace.vue` | `0b6fde684568d5a716f664c123818b95381c12464375326038d5abef2b7b718b` |

本机证据根为`.local/b/review-evidence/MUS-025-R1-B/`，最终子目录为上述最终运行ID；不表示已向A传递私有原始文件。

| 本机工件 | SHA256 |
|---|---|
| `node21.log` | `911025990cba61f309df3643ddbbece4f804603b82f69d3711eedb71572a1e8f` |
| `build.log` | `0ef71f8ca7b9e4592f817ba99a689c46ffe14a2f7c7ccc1b3f4efb43f247c6f0` |
| 最终`browser-result.json` | `6ca9e8533f521e11ee9ea74ae1e1b7d6b5f3d59dad5bf5acddde2bf30ed2ffcc` |
| 最终`result.json` | `2ca5e153f217c94fbfed60eb713a727fd7d1801280282af3acc8be732a1d3464` |
| `verified-evidence.json` | `a11ba6c4a9da376cd866a0452f6107796c055ca97d475ef49a8b04c5d8b82636` |
| 最终390/1440截图 | `283a82512daeeccb8b5e98dc5ef3bc54af7ed109806e774463cca096f54cc6c6` / `6e301533845586cd5059db79586ee6a53947ec64515ee7b7d0dd015ff497673f` |

## 未执行内容与交接

未访问或复算A真实51包、20曲目、原run/日志/截图；A的51全null仍是A私有证据。没有真人相关性、时间IoU、质量/P95/held-out或discovery-v0冻结结论，模型建议可见的提示偏差仍存在。包自洽、CLI通过不认证人或当前媒体授权，合法交付的字节不能追溯撤销。

未在真实浏览器逐个重演所有晚play promise、token跨标签变化、退出时正在等待响应等交错；Node fake audio/fetch检查及Vue生命周期静态审查与本轮实际切候选迟到响应分开。未做全浏览器/移动设备兼容、精确采样剪辑、断电/存储介质故障或整个旧媒体矩阵。quota为定向受控故障，不是磁盘真正耗尽。

未重复Java单测、旧上传/管理全套、CLAP或024完整CLI；两次上传仅为本卡真实媒体fixture，不是完整上传验收。没有A服务升级、原数据写入、schema迁移到既有库、公共服务、main合并或后台轮询。

接口变化：无；B无待修产品发现。下一步由A接收限定批准，再安排真人判断/失败分析或其他明确任务。任务分支与B feed采用GitHub先源码后feed顺序发布，非原子，交付SHA和回读结果由发布记录给出；发布不等于A接收。交付后两报告占用释放，本轮服务与端口均无占用。
