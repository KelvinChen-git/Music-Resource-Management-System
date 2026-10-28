# MUS-026-R1-B：审阅底栏与seek增量独立审核

- task / assignment_revision / owner：MUS-026-R1-B / 1 / b。
- status / verdict：review_completed / approve_scoped；2026-10-24（America/Chicago）。
- reviewed_sha：`d766dcd09df3cc1e54130ca80aefb946985ee2b3`。
- comparison_base_sha：`0ae63f9d6a4632ffbfa1c0cedc017aad6cea862c`。
- assignment_source_sha：`d90bfcb7be6454f7cff0aa82943b0e7a0d2f6882`。
- ack_peer_feed_sha：`76249e30de6457eb33ab41a60aa58076815dfeb5`。
- branch：`review/MUS-026-B-review-controls`；交付SHA由B feed根目录`handoff.json.source_sha`记录，避免同提交自引用。
- 先领取再审：source `2541449560deed809c28de5f116fd7e8c09ac002` / feed `969db551eb8461757b7229ff2df4c5b9bf2e02e1`，远端回读相符。

## 结论与范围

准确6文件增量、E3与任务卡范围内，未发现新增阻塞问题，限定批准。完整审查reviewAudio及其测试、ReviewWorkspace、sonoraPlayer store及测试、SonoraPlayer.vue；226增/33删。另有一项既有开发配置的非阻塞观察N1，见下文。批准不等于main合并或整套系统、检索质量验收。

A已接收025限定批准；导入报告与B交付逐字节相同，SHA256 `a5cdccb79cc658169292391b00e66cd7901de06f5c8adb861090992a93c6e8dd`。本轮未重复025全37或024全83CLI，也未复算旧私有证据。旧scratch已被环境维护清理，本轮从远端重建独立B clone，并恢复必要工具/现有锁依赖。

仅提交`docs/reviews/MUS-026-B.md`及`docs/collaboration/account-b/latest.md`。真实运行另用准确实现SHA的临时独立clone、slot B和新空库；MySQL3308、Java8081、生产预览5174，均由B登记启停。不访问A3307/8080/5175、私有账号/曲库/51包/缓存。无产品源码、API、schema、锁、公共JSON、A台账或备份变更。

## 实际命令与结果

| 范围 / 命令 | B执行结果 |
|---|---|
| 固定Node22.23.3 `node --test web/src/utils/reviewPack.test.js web/src/utils/reviewAudio.test.js web/src/utils/media.test.js web/src/stores/sonoraPlayer.test.js` | exit0；31项（8包/11音频/6媒体/6store），0失败/跳过；store实际Vue/Pinia，user/API/audio边界为替身 |
| 固定Node22/npm10.9.9：在`web/`执行`npm ci`、`npm run build` | 两命令exit0；因旧环境清理恢复244依赖包，现有lock不变、不升级；保留>500kB构建警告及Node实验性代理提示 |
| `python3 .local/b/runtime/run26.py` 最终运行 | `baseline-20261024-010925-6`，exit0/status passed；30项真实浏览器断言全部通过，另有1次最终导出CLI验证 |
| 浏览器 / 后端 | 官方Chrome Headless Shell151.0.7922.34、Playwright、真实HTMLAudioElement与现有Java/MySQL HTTP；Linux无Unix socket适配采用single-process/no-zygote及私有MySQL TCP适配，不改产品 |
| 固定合成run `review_pack.py build` / 最终`validate --pack browser-export.json` | 各exit0；最终1查询/2候选、1个明确测试0分/1个null、人工区间0，身份/听音未验证 |
| `git diff --check` / 源码与锁指纹 / 固定入口sync | 交付前通过；开始、检查点均exit0/fetched，A feed和派发未变；交付后另行回读 |

31项Node与30项浏览器分别计数，不加A的31/旧21或早期已完成检查。后端以`-Dmaven.test.skip=true spring-boot:run`编译启动，Java单测执行0；不把编译当单测。真实库初始化11表/V001-V002仅针对B新空库，没有迁移既有库或升级A服务。

## 真实控制链补证

- 普通账号经真实注册/登录，正常上传两段40s/46s合成MP3，普通播放器先播放并建立2首队列。审阅启动后底栏显示当前候选、歌手、试听模式，普通audio真实暂停；队列/当前普通曲目保留，随机/循环/上/下一首均禁用。
- 页内Home/PageUp操作将真实audio移至8.000s，页面8000ms/底栏20%同步，活动Blob内seek没有新增GET。底栏鼠标点击中点后真实20.000s、页面20000ms/50%一致。
- 底栏暂停保留位置并释放src。暂停时点击页内约37.5%位置后新增真实GET/校验，保持暂停且src释放，位置14900ms；再从底栏继续新增GET，真实14.900s附近起播。不是暂停时自动播放或使用已释放旧Blob。
- 底栏音量操作实际HTMLAudioElement.volume为0.1，静音为0，取消静音恢复0.7；只测属性与控制转发，不推导实际声压/增益。
- 模型片段5–10s：页面min/max为5000/10000，Home限定起点，底栏End立即停在10000ms并释放src；继续重新GET后从约5s起播。仍是浏览器事件/计时精度，非采样精确剪辑。
- 导入新包释放临时绑定并恢复原普通暂停标题；自洽但错内容SHA的包实际GET后被拒，两处seek与取点均disabled、无src。正常播放后暂停，owner通过真实DELETE软删除自己的资源，底栏继续重新GET得到404，两处seek/取点禁用，无旧音频恢复；随后用真实回收站API恢复资源。未使用锁或假403/404响应，不重复完整权限矩阵。
- 主动点击普通队列曲目接管，审阅src清除、普通实际播放。普通切歌pending时，测试侧先取得真实授权字节并延迟交付；启动审阅后普通旧src被清除，释放迟到响应不能夺回审阅或把旧字节配新标题。另一组延迟旧审阅响应，在新候选已播放后交付，底栏/实际音频仍属于新候选。仅传输时间受控，不用fake audio代替本项。
- 离页后审阅audio销毁，原暂停队列和普通控件恢复，队列仍2首。退出后两个audio绑定均清除。普通ended自动推进、旧publisher主动release、token/换号边界由真实Vue/Pinia store替身检查与源码审查覆盖，没有冒充这些都是新增真实浏览器竞态。
- 390×1000和1440×1000均实际操作页内slider与暂停，底栏显示候选/试听模式；document.scrollWidth分别390/1440，无横溢。手机页内位置4800ms、桌面4000ms，暂停均无src，截图已查看。手机底栏沿用旧响应式简化布局，未声称测了其隐藏的滑块/音量。full-page截图的固定底栏/侧栏位置反映截图方法。
- 预置明确`test-b26`测试0分及同账号同包草稿，只操作播放控制。结束时草稿原始字符串完全一致，导出整包对象与原输入完全一致，并通过固定run CLI；没有评分/时间/人工区间被播放控制自动改写。

最终记录17个媒体响应：14个审阅响应均有Bearer头、无pay/JWT query；3个正常普通播放器响应按原pay行为单列。被取消的请求不一定产生response，17不是全部尝试总数。浏览器有1条预期404 HTTP console error，0未捕获pageerror，不宣称warn/error全空。后端既有SQL解析/Druid诊断保留，未扩大本卡修复。

## N1：开发模式浮层遮挡底栏中点（非阻塞，既有配置）

位置：`web/vite.config.js`的既有`vueDevTools()`插件及其注入的`#__vue-devtools-container__`，不在本卡6文件增量内。开发模式1440px，底栏“播放进度”中点被Vue DevTools anchor/panel截获，Playwright正常鼠标click持续超时，日志明确列出拦截元素；不能将该命令算通过或认定底栏鼠标已验收。键盘seek当轮通过。影响是开发服务器下该位置难以点击；生产build preview无此浮层，真实鼠标seek通过。建议A在需要开发模式指针验收时调整/关闭悬浮入口位置，或使用生产预览；开发配置变更另行协调，不在B报告任务内修改。未将它归因MUS-026新增控制逻辑。

## 保留的失败及校正

| 运行 / 准备 | 原结果 |
|---|---|
| 工具恢复 | 固定官方Node/MySQL/headless/CJK下载和哈希核对成功；libncurses下载曾503，第一次`mysql --version` exit127/缺libncurses.so.5，业务0项；官方URL重试恢复后版本8.0.41通过 |
| `baseline-20261024-010429-6` | exit1/blocked，4项完成；开发模式DevTools浮层截获鼠标，见N1；改为同源生产构建preview验收，未隐藏/改动产品DOM |
| `baseline-20261024-010606-6` | exit1/blocked，15项完成；B错SHA夹具重算dataset时误包含测试人工0分，包在导入即正确拒绝，等待成功提示超时；改为按E1将人工字段置null后计算指纹 |
| `baseline-20261024-010721-6` | exit1/blocked，17项完成；B夹具变量名覆盖了后端URL，真实删除API尚未发出就Invalid URL；修夹具局部变量名 |
| `baseline-20261024-010814-6` | exit1/blocked，22项完成；脚本通用`.el-drawer`同时匹配曲库详情和队列两个DOM，strict locator失败；改为限定包含`.queue-track`的弹窗 |
| `baseline-20261024-010925-6` | exit0/passed；最终30项和导出CLI通过，不累加前四轮 |

前四轮不改写为passed，夹具/选择器错误不作为产品缺陷。五轮自建进程均按登记停止，3308/8081/5174逐轮及最终再次确认释放；原失败日志/截图保留。

## 数据与证据

无真实模型/索引版本新增。pipeline `b26-synthetic-controls-v1`、伪run代码`a×40`、伪checkpoint `b×64`，来源URL仅合成记录，不访问提供方或证明许可。两音频实测解码40000/46000ms、320618/368475字节，SHA256分别`3f3c2b8c183fe650da0bbe52514f93f1cb343755aaa0708201323c4ffa434863`和`b9d378994b59bde4c74b0176cd9894f3f8e6b477e01a86697fe71dafd190ec2f`。

固定合成report SHA256 `431fa30ecdba273b56fb646a64e1ce539aff7d3c7ed5b585c02daa3a5717ede6`；dataset SHA256 `4c13b830d3f10c60e229f9c4826223871d6fd8c064475c3e1f9a922ae9119597`。CLI准确执行`validate --run-dir <本机fixture/run> --catalog <fixture/catalog.json> --report-sha256 <上述report哈希> --pack <最终browser-export.json>`；这只是格式/绑定检查，身份/真人听音验证false。

全部6份实现源码SHA256与A的MUS-026-results.json相同。B证据在忽略目录`.local/b/review-evidence/MUS-026-R1-B/`，最终子目录为最终运行ID；私有工具/日志/包/截图未交付A，A不能仅据报告重算原始证据。

| B本机工件 | SHA256 |
|---|---|
| `node31.log` | `30d234154b5cf9ef310786031be4651bd8b7337c2922b76ce5dd3d0c227ae20d` |
| `build.log` | `f156afce6b0b39289472f33b40128b33e7eae36ea6393cc87274d0ad761b4f77` |
| 最终`browser-result.json` | `4804e40fec161ed2fa92e223bbb63e760e7448c04cf911f92bd273538cb5d9b5` |
| 最终`result.json` | `cd3d9aa26eebe4a3d7f00c32cee20604d4fd3ec2b2a0ef7f0c3877c840926fb0` |
| 最终`browser-export.json` / `cli-export.log` | `530c29fa598c477813c300805b030ccfa3236ba134bec7e9f496e2376011dc0f` / `fa998fee20f2b998bfb6b92aad86cb7d02b84c7dd3083374c21447168d61feb8` |
| `verified-evidence.json` | `2401a248de08daf38d81aad177f34df76cb4f3f9768a52175d3b5b270916c0fc` |

## 交接与未执行内容

B接口变化无，提交仅两报告。未访问/复算A真实51包、20曲目或截图日志；未做真人相关性、质量、P95、held-out或discovery-v0冻结。没有新CLAP/索引/完整上传管理/025全标注/024全CLI/Java单测或完整旧权限矩阵。本卡两次上传只准备真实媒体fixture；已合法交付的字节不能追溯撤销。

未在浏览器重演全部token跨标签、第二账号换号、所有晚play promise或真实普通ended事件；已区分Node替身、源码审查与本轮真实增量证据。没有声称跨浏览器/真实移动设备兼容、声压测量或采样级时间精度。

下一步A接收本限定批准及N1开发环境观察，再从固定入口派发。GitHub采用先任务分支后`collab/account-b`的顺序发布，非原子；交付SHA及远端回读由发布记录给出，发布不等于A接收。交付后两报告占用释放，无自建服务/端口占用、main合并或后台轮询。
