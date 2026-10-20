# MUS-020-R1-B：Sonora R1/R2 增量复核

## 结论与交接输入

`review_completed / approve`，仅限本卡两项修复及必要回归。MUS-019的R1长标题溢出、R2管理员查询丢失筛选均关闭，本增量未发现新的阻断问题。不是整站、生产或所有历史待办批准。

- task_id / assignment_revision：MUS-020-R1-B / 1；owner B。
- reviewed_sha：`802da6bb1ee3f7906a19c963efb5aeac2115d223`。
- comparison_base_sha：`c19b64833b78a2cd958959b77a1c9703f2fc9281`。
- assignment_source_sha：`0566bc26ca88c5600072db717a26119c8983ed3f`。
- ack_peer_feed_sha：`ec6cdbb737a07fbace25db9ea9be3c4d1b97704a`；结束前sync仍一致。
- 分支：`review/MUS-020-B-sonora-findings`。
- 已先主动claimed，source `987e3ca2f72357567fb1d34d41fbad1981489134` / B feed `f31f1757235c44bcd3eab2ce42c9c0f6b4271ef6`。
- 仅交付本报告及`docs/collaboration/account-b/latest.md`；最终交付SHA由B feed的handoff.source_sha记录，避免同次提交自引用。

A已接收MUS-019 request_changes。B本轮另核对A实现中的docs/reviews/MUS-019-B.md与B source30bbd71中的原报告字节相同；没有重复领取019或覆盖其原正文。MUS-017正式接收/E1/E2与MUS-016独立审核继续单列。

## 静态增量核对

业务仅两文件：

1. `web/src/styles/sonora.css:2`把`.listmode .album-info`由flex:1改为flex:1 1 0并min-width:0；新增标题/副标题容器min-width:0、max-width:100%，标题按钮min-width:0、flex-basis:0。其他规则保持；未新增页面级overflow-x:hidden/clip。
2. `web/src/views/admin/user/index.vue:648、656`只把两个handler的目标/music改成/manage/music，原username/email参数及值、缺字段警告保持。

已按Git对象逐字节确认package-lock、播放器store、media helper及6项测试、5组player脚本、路由守卫、旧musicStore、DemoCatalogView均未变化。旧store已有/manage/music限定监听并解析username/email；普通keyword入口仍走Sonora曲库。无Java/Python/API/schema/依赖升级。

## 独立实际验证

### 构建与handler边界

B使用现有Node22.23.3/npm10.9.9依赖，在web执行`npm run build`：exit0，既有>500kB chunk提示保留。执行HEAD987e3ca仅比准确目标多B认领文档；web树与目标完全相同：`f68c47b401f6be53374e18e3b2893d7b90cb480d`。锁SHA256仍为`8df2bc2e97e9743265a30e11c52518ade9d8f1fdebffead45bbe508cc92b7980`。

执行`node .local/b/runtime/mus020_handlers.cjs`，4项通过：两个实际handler体分别保留路径/原始query（含空格、+及中文）；每个缺字段/空字符串分支均只警告、不导航。该私有harness使用router/message替身，不称真实管理员HTTP；两个missing/empty输入各计在对应一个检查中。

本轮不再npm ci或重跑未变的player5/media6、Java/Python及019完整26场景。它们的上轮结果不冒充本轮新执行；以源码/锁哈希核对及下面实际增量播放/查询补证。

### 新隔离真库与浏览器：16项通过

命令`python3 .local/b/runtime/run_mus020.py`，内部准确SHA新临时clone、slot B新库/上传目录、MySQL8.0.41、JDK17/JVM、B生产构建产物与本地代理、Chromium151.0.7922.34。最终run `baseline-20261020-171644-11`，命令exit0，status=passed，16项检查；未访问A8080/5175、A曲库或A凭据。

R1使用同一压力标题`B19 `加9次`LongTitleWithoutSpaces`：

| 检查 | B实测 |
|---|---|
| 390×844列表 | documentWidth390；html/body overflowX均visible，未以页面裁切隐藏问题 |
| 长标题 | clientWidth218、scrollWidth1328、text-overflow:ellipsis、white-space:nowrap |
| 列表收藏按钮 | x327–354、宽27；真实点击可命中，aria-pressed发生切换 |
| 手机网格 | documentWidth390 |
| 1440桌面列表 | documentWidth1440；收藏x1359–1386，可见 |
| 桌面网格 | documentWidth1440 |
| 必要播放器回归 | 正常鉴权获取合成MP3并播放，duration24、currentTime0.223471、无audio error；SPA去歌手页保持同一音频，随后可暂停 |

原019 B相同长标题曾撑到1464；本轮真实Vue/真库场景收敛到390。已查看本轮手机列表/网格及桌面列表截图。B环境缺中文字体，截图仅支持布局/Latin标题省略/控件结论，不宣称中文排印或像素一致。reducedMotion设置为reduce以避免过渡帧采样。

R2从真实管理员用户菜单分别点击Username、Email，观察由Axios发出的XHR，核对解码后的原始参数、/manage/music地址、后端IDs/total、UI行标题/分页total。测试账号的name含空格和+，email含+，未用模拟router替代这些六条链路：

| 目标 | username：后端total/UI total/返回IDs | email：后端total/UI total/返回IDs |
|---|---|---|
| owner A，有2资源 | 2 / 2 / [1,2] | 2 / 2 / [1,2] |
| owner B，有1资源 | 1 / 1 / [3] | 1 / 1 / [3] |
| zero，无资源 | 0 / 0 / [] | 0 / 0 / [] |

六次均HTTP200/业务200，页面行标题集合与相应owner资源精确一致，未显示其他owner结果。普通用户访问/admin/users仍被前端守卫转回/music且无管理员菜单；这是浏览器路由回归，不新增声称服务端全部角色矩阵已测。

16项为：R1列表几何/省略1、收藏真实点击1、手机网格1、桌面列表1、桌面网格1、真实鉴权播放1、SPA保持/暂停1、普通用户路由边界1、上述管理查询6、普通/music?keyword查找B资源1、无未捕获pageerror1。keyword仍使用Sonora界面；DemoCatalog只做未改字节核对，不假装点击了A演示账号才有的查找链接。

### 样本、失败运行与环境适配

最终新库只有4个合成账号、2次真实普通HTTP音频上传/metadata登记、3个目录资源。owner A的额外1条资源及193字符压力标题通过SQL fixture布置；不是声称3次正常上传或193字符标题经metadata API通过。MP3由ffmpeg生成24秒440Hz正弦波，SHA256 `2abede801159ea9fe8435d17e5f3b57d7db7bd6b1ea540598a2c586a943e0313`，无音乐语料/听感/检索评估。

两次准备失败保留：

- `baseline-20261020-171408-10`：生成的用户名24字符，违反既有RegisterDTO上限20，注册未成功；exit1/blocked，浏览器0项。
- `baseline-20261020-171512-11`：直接提交193字符音乐标题被既有100字符校验拒绝；exit1/blocked，浏览器0项。

缩短注册样本后，使用正常短标题完成登记，再仅在自己的隔离库按任务指定SQL设置压力标题；输入校验、产品实现和仓库断言未改。最终171644-11单独16项passed，不将前两命令改写为passed，也不相加。长标题超过正常API输入上限是本压力fixture的明确边界。

沿用既有B私有Linux工具路径、每进程代理settings、Maven缓存、Unix socket到loopback TCP适配；没有依赖下载/全局NULL/schema/权限契约变更。可变库位于单次exec的原生/tmp。每次finally降权本次生成admin并停止自己登记的进程；最终3308/8081/5174均确认无监听。未触碰现有A服务或演示数据。

## 私有证据与限制

原始目录`.local/b/review-evidence/MUS-020-R1-B/`及私有运行器未随两报告交付，A不能声称自行重算未交付原始日志。B已核对结果、截图及原始哈希；汇总含各轮状态/源码及工具哈希：

| 文件 | SHA256 |
|---|---|
| build.log | `d5c8bfa8ef4bf6d4fafdd049490fa7c5d97fbcd8240acf1818ff2593bff3aa63` |
| build-result.json | `2e5b9f92a35bba250a7e87256a3bfab91d72e08fca2f8922e67b769240b6b3b9` |
| handler-result.json | `e8d04f885da983e53961a565e4e79a69ce374151e452c1e722ff9f5979ed237d` |
| unchanged-source-hashes.json | `5ac1afd3e1341f5acafadb236bb85af17986b9f1656639fd4799aa5bf21a2781` |
| baseline-20261020-171644-11/browser-result.json | `4843819ed52a8e683ea7c8af567184ed4c98815c5f10afe0522e48a6bc72e7fb` |
| baseline-20261020-171644-11/result.json | `1ccd2f1ea9238e668ea5661c9f6c9b77367c04ce9760b5c4631bf6b541ada79b` |
| baseline-20261020-171644-11/mobile-list.png | `d4325d8cecc731cb957d52ad3f1ec34de556cca128d7052d18511b24744c93b6` |
| verified-review-evidence.json | `d15d40b9e3e03ed128b696f9f4fe336b5205f563aff1608c80e258066e791316` |

未执行：019完整基线、未变player5/media6重跑、Java/Python测试、完整浏览器上传/续传与管理写操作、旧手工/music?username/email深链兼容扩展、跨设备收藏、生产或模型/检索质量。旧深链兼容不是本卡承诺；本轮关闭的是产品两处管理菜单入口。

## 交付

任务/owner、分支、基础SHA及准确审核SHA见首节；仅两B报告变化，接口变化无，数据仅本轮临时fixture，模型/索引版本无变化。未修A源码/总台账/任务卡，不推main、不最终合并。两报告占用释放。

下一步A串行接收本卡范围内批准并关闭019 R1/R2，再从固定入口派发后续任务；MUS-017正式接收/E1/E2与MUS-016不自动关闭。发布沿用已授权GitHub插件源码分支→B feed顺序路径，非原子；本轮未配置新的原生Git写凭据。发布后回读源码树、报告及两文件feed/hash，实际最终SHA见handoff。发布与A接收/合并区分。
