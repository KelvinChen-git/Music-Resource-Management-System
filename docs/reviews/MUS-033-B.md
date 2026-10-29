# MUS-033-R1-B 独立增量审核

2026-10-29（America/Chicago）；owner / account：B；assignment_revision：1；status：review_completed；verdict：**approve_scoped**。

准确基线的新导入器、source-review 包与前端分支、原整曲时长适配，在本卡允许的合成输入范围内未发现阻塞问题。本结论不认证真实服务、来源许可或解码时长，不外推到032收集器、035模型链路或正式检索质量。

## 固定输入与领取

| 项目 | 值 |
|---|---|
| task / owner | MUS-033-R1-B / b，revision 1 |
| reviewed_sha / 开发基础 | `10880f87f4073dc8f2d260fb72a07c9e52e59791` |
| comparison_base_sha | `7704051f9a844816174c710d09e6f92e5b23f0e7` |
| assignment_source_sha | `9797ed4b8766f8cd5f6cd7759b86bd309cef2f7d` |
| ack_peer_feed_sha | `bf1f855a542e7e12d22c9e512967307e4422568a` |
| source_branch | `review/MUS-033-B-source-review` |
| 领取 source / B feed | `87f42f604776a1ff26c1551c601c5b622096c957` / `cd8467d53e34e2d2b199b740cfa42110adfc1c13` |
| 交付 SHA | 由本次 B feed `handoff.json.source_sha` 给出，避免同一提交自引用 |
| 唯一修改文件 | `docs/reviews/MUS-033-B.md`、`docs/collaboration/account-b/latest.md` |

从固定A入口读取handoff/latest，按source读取033/rev1卡及E7、验证报告和实际diff。首次与提交前sync均exit0/fetched，A feed未变；先发布claimed并回读精确字节，再审核。已对照027接收JSON和A/B两处报告，原字节SHA均为`54034af6288c3f6fed2c1500175fa25f4234664876252d34b52c07cac0c67728`；027已接收，不重新领取。

独立B clone/slot B；忽略目录中的`fake-backend/.local/a`仅是B自造目录，用于满足导入器固定slot-a配置校验，所有HTTP均为内存transport替身。没有访问A目录、账号、音频、草稿、138判断或3307/8080/5175服务，也没有真实B Java/MySQL进程。

## 检查范围与结论

| 源码 | 检查结果及实际边界 |
|---|---|
| `scripts/import_research_music.py`、对应独立测试 | 三显式SHA、原20证明/音频、新20元数据和解码报告先于登录；普通owner/profile校验后才写入。缺失legacy状态仅在不存在且非symlink时回退；已有坏状态不得回退。新ID取自transport响应、拒绝歧义/错owner/错文件、Range/full绑定；不注册、提权、审核或写旧资源。私有输出/锁/ledger、丢响应后恢复与重复运行核验见下。 |
| `source_review_pack.py`、对应测试 | 固定五输入哈希、官方快照/证明/原20/新20绑定；五query各4，20独立ISRC/Java ID/内容，30–600s，固定query及track顺序、全null/空建议。CLI只允许人工四字段变化，已有输出拒绝覆盖。 |
| `reviewPack.js`、`sourceReviewPack.test.js`、`ReviewWorkspace.vue` | 明确source schema/split/provenance，严格ISRC/URL/CC BY4/数量/去重/Long字符串；旧E1和诊断规则保留。就近代号、0/null、人工区间、草稿隔离/显式恢复、导出绑定和必要提示通过。浏览器允许自洽重新签名的输入，最终来源认证仍须固定输入CLI，不能把浏览器导入当认证来源。 |
| `reviewAudio.js`、对应测试 | 完整字节/SHA后，仅Incompetech原整曲取min(recorded,browser)。保存原请求身份，每次暂停后seek/恢复重算，位置>=fresh端点拒绝；输入不变、不延长时间；真正片段和两旧schema保留100ms保护。B内存音频独立覆盖fresh缩短53ms、等于/超出端点和校验失败先于适配。 |

上述范围相对7704051的实际diff为11文件；032 collector helper只读作依赖上下文。没有修改产品、API、数据库、依赖锁、模型版本或公共catalog，也没有重做UI或向main合并。

## B 实际命令与结果

以下从B clone根目录执行。`NODE=.local/b/runtime-tools/node-v22.23.3-linux-x64/bin/node`（22.23.3），npm10.9.9；沿用现有node_modules及lock，未重新安装或升级依赖。Python3.12标准库；浏览器为官方headless-shell151.0.7922.34，Playwright使用现有主运行时模块，CJK字体复用B私有配置。

| 命令 | exit / 结果 |
|---|---|
| `python3 -m unittest discover -s scripts -p test_research_import.py -v` | 0，27 passed；作者提供的合成transport保护测试，由B独立执行 |
| `PYTHONPATH=services/audio-search python3 -m unittest test_review_pack test_evaluate_review test_diagnostic_pack test_source_review_pack -v` | 0，72 passed；含原53及新source19，不将72全部算新测 |
| `$NODE --test web/src/utils/*.test.js web/src/stores/*.test.js` | 0，68 passed；包括reviewAudio20与旧schema回归 |
| `PATH="$PWD/.local/b/runtime-tools/node-v22.23.3-linux-x64/bin:$PATH" $NODE .local/b/runtime-tools/node-v22.23.3-linux-x64/lib/node_modules/npm/bin/npm-cli.js --prefix web run build` | 0；保留现有>500kB bundle警告，npm升级提示未执行 |
| `python3 .local/b/runtime/fixture33.py` | 0；B新写fixture/transport，15项独立断言；CLI build/validate各0；重建同输出、重新签名改metadata各预期exit1 |
| `$NODE --test .local/b/runtime/independent33.mjs` | 0，7 passed；B新写跨Python/JS、草稿、音频边界检查，参数子情形不额外累计 |
| `python3 .local/b/runtime/run33.py` 最终`run-20261029-010011` | 0/passed；23浏览器断言；空白/桌面/手机三导出CLI分别exit0；改provenance导出以原固定输入校验预期exit1 |
| `git diff --check`及允许路径/源码字节核对 | 通过；交付仅B两报告，5核心实现文件与准确reviewed SHA逐字节相同 |

复现用CLI通用参数来自B忽略的`config.json`（不是A私有输入）：

```sh
python3 services/audio-search/source_review_pack.py validate \
  --source-manifest .local/b/review-evidence/MUS-033-R1-B/synthetic/batch/manifest.json \
  --source-manifest-sha256 847fc72436038c67d7293a53518c0f829f17de4e0bd79fdb6882c3e27e0286cf \
  --decode-report .local/b/review-evidence/MUS-033-R1-B/synthetic/decode.json \
  --decode-report-sha256 45f2ffbddd4ba85a89b94f242b7fbfbdece8438c7b65d3534ece26d43c5fd0d8 \
  --import-catalog .local/b/review-evidence/MUS-033-R1-B/synthetic/fake-importer/.local/imported/catalog.json \
  --import-catalog-sha256 a4be7d926c4136f2ab00d0ab86b7a899fe0367f3e2d225ed0bd01bf2433665fb \
  --query-fixture .local/b/review-evidence/MUS-033-R1-B/synthetic/queries.json \
  --query-fixture-sha256 8865d396ad4f52d5e31c297af0b9db8a64f48cfb996533b65cb66b7c22aabb22 \
  --selection .local/b/review-evidence/MUS-033-R1-B/synthetic/fake-importer/services/audio-search/targeted_sources.json \
  --baseline-catalog .local/b/review-evidence/MUS-033-R1-B/synthetic/baseline.json \
  --pack .local/b/review-evidence/MUS-033-R1-B/run-20261029-010011/export-mobile.json
```

这些本机工具、日志和输入仅留在B的ignore目录，未作为交付源文件；A未获得或重算原始私有工件。已有fixture禁止原地重建覆盖，本轮通过后不重复整套测试。

## 独立输入与运行证据

B自行构造20旧+20新资源、五query各4，伪提供方快照/字节/解码元数据；引用公共selection的ISRC/标题不意味着下载或许可核验。普通owner、接近Java Long上界的新musicId均为transport返回的合成值。没有真正MP3、音频解码、真人代号或标注；实际CLI均明确`identity_or_listening_verified=false`。

导入的15项断言包括：首次metadata已提交后模拟响应丢失，exit异常并保留partial ledger/释放锁；后续完成和完整重跑仍恰20 upload/20 metadata、共40资源，catalog字节不变；旧20对象不变；80独立副本/无hardlink、output和audio0700/文件0600；输入原字节不变；不保存合成凭据/token；已有锁保留且不发HTTP；pending状态在登录前拒绝；缺失legacy且profile错owner只执行login/profile后停止。替身实现每页最多7条，但正常fixture的精确标题各只匹配1条，因此**本独立运行没有实际走多页lookup**，不冒充分页验收。原27测试/静态pagination检查另述。

独立7项Node检查：Python生成source包到JS原对象往返（Long不丢精度）；重签后非法ID、ISRC、URL、query/候选数、重复内容、29999/600001ms拒绝，30000/600000ms通过；改变provenance或owner不能恢复旧draft；内存音频完整字节核验先于时长适配，较长browser不能延长，fresh端点缩短53ms和后续缩短每次重算；resume/paused seek到达或超出端点均不新增play，源片段/legacy仍按旧边界拒绝。EventTarget/Response/WebCrypto是真实Node API，audio.duration/事件是替身，不是实际解码器证据。

最终浏览器使用真正Vue/Pinia、文件选择、原生radio/输入、WebCrypto、localStorage和下载；只模拟login/profile API，两个owner串行独立浏览器，4次API响应，无媒体/外部/未知API。23断言覆盖新素材/非模型排序提示、5×4/0已判、精确来源/许可链接、空代号禁用且无默认分、合法代号不自动判、0与null、切候选不继承、3分保存1125–2875ms区间、Long导出、owner+dataset草稿、改变provenance全null不恢复旧稿、刷新原文件0/20后显式恢复2项且仍需代号、新query不继承、手机指针2分、另一合成owner拒绝导入，以及390/1440宽scrollWidth分别390/1440。截图已查看；最终console warning/error/pageerror均0。

空白导出全20 null且对象与原包相同；桌面0/3各1、18 null、1区间；手机保留0/3与原区间，另增2分1条、17 null。三导出经同一固定合成输入CLI验证；全为测试判断，不算新增真人判断或真实播放鉴权。

### 保留的失败运行

`run-20261029-005930`：exit1/blocked，先完成20项浏览器断言，创建第二个并发context的newPage时headless-shell退出；CLI执行0。环境必须使用`--single-process`且stderr有socket/DBus限制；未发现产品断言失败。仅修改B忽略的测试harness，将第二owner改为串行新浏览器，得到上述最终23项全通过。两轮日志/导出/截图分别保留，不将20与23相加。两轮自己的preview均停止，5174释放；没有为此改产品或占用A服务。

初次写claimed时准确基线不存在B报告父目录，写入失败、未提交/发布；创建允许父目录后成功。该准备失败不算产品检查或claim已发布；正式claim的source/feed与字节回读已单列。

### 哈希

证据目录：`.local/b/review-evidence/MUS-033-R1-B/`；文件清单及全哈希在`verified-evidence.json`，SHA256 `85b346bcae352718041907a00038fc94d8fba5e191b0a0e6fbe75bb2ad58051c`。

| 工件 | SHA256 |
|---|---|
| B初始包 | `3de0e912d3798c647f478d2657d2567cf20023a560674921dceaa6bdfb1635ae` |
| B dataset fingerprint | `44eda7af0c43c8b39f386f96194285e3fa21ad97b9dfbc7d2eaaf452dc7f1333` |
| B importer独立证据 | `fb5eec4347ed914c350bbb705814c8523e3fffa16d208cbdfeb5abe70edbb413` |
| 最终browser-result.json | `846477b11be6ab19a2946c1f2ce7768b014cda71a3b70c5fbe3dba1fbeca4409` |
| 最终result.json | `9566f2521ec8dda3a9a1f2d7d99f65f19e809c76fb9af8243d9beb4117ad4ffc` |
| 桌面 / 手机导出 | `01cfefd3ddad46f9c7acf29926004125dd706388fc6fa22557fa56987d467f00` / `304a40da6621a0843674dcc0f85f06a002a9a5dea7796f680467a6920b4e3512` |
| importer源码 | `fd37990c1e6f4d6dedc9480be7385e05143274c0f18d1da26e267333e609574a` |
| source_review_pack源码 | `c6630572817c70e4a80daa82cd9281877124f3db310821f8dee394f2d4f1dd15` |
| reviewPack / reviewAudio源码 | `31742899889a61057659e33b5f44011f0f733b30586ee096b8d992312355e463` / `28aeb3dd075a48d250046bed51024a3435adf68edf12b2d88265db28944af393` |
| ReviewWorkspace源码 | `fe244c3e53b50c4f48a308debba5811b3b8df7bba2a1f8c1771751892015bda2` |

## 未验证、剩余事项与交接

本卡无新增阻塞发现或产品修复。未新跑Java/Maven、真MySQL、真实账户/HTTP权限、提供方网络或许可证认证、实际MP3解码/试听、CLAP/索引、真实人评/质量/P95；这些不在卡片合成验收边界内，不能以本批准关闭。

A当前035交接已将032旧头部估计时长纠正为实际EOF，并明确保留033历史catalog/已判包。本审核只确认工具对固定输入的绑定和浏览器较短端点保护，**不认证033输入时长是实际EOF**。后续新包按035实际时长及新指纹生成；不改旧已判数据来掩盖差异，不把本批准外推035。A已有138真实判断等仅按远端文档读取，本轮未读取/复算原始判断；B合成20 null及测试0/2/3不改变全局人评事实。

数据版本：B synthetic source manifest/decode/catalog、source-review-v1及上述dataset；模型/索引版本：无，不加载或修改。接口变化：无。下一步A接收本033范围内报告，再明确派发后续工具审核；029/030/032/035独立复核不因本次自动完成。

发布经已授权GitHub接口，任务分支后B feed顺序更新、非原子；最终SHA及实际发布状态以feed handoff和回读为准。只提交两允许报告，不改A STATUS/dispatch/feed，不推送或合并main。交付后两报告占用释放，自己的浏览器/preview停止，5174释放，无Java/MySQL或后台轮询；发布不等于A已接收。
