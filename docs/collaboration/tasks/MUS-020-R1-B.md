# MUS-020-R1-B：Sonora R1/R2 增量复核

- task_id / revision：MUS-020-R1-B / 1；owner B；review_completed / approve_scoped，A已接收；固定入口waiting，无新任务。
- reviewed_sha `802da6bb1ee3f7906a19c963efb5aeac2115d223`；comparison_base_sha `c19b64833b78a2cd958959b77a1c9703f2fc9281`。
- 分支 `review/MUS-020-B-sonora-findings`；只允许写 `docs/reviews/MUS-020-B.md` 和 `docs/collaboration/account-b/latest.md`。

A已接收B feed f9fc32ec/source30bbd71c的request_changes，核验hash及仅两报告diff，原字节导入MUS-019-B，不改B正文。MUS-019任务完成不重复领取，也不当成整个UI批准。先按当前A handoff.source_sha读取入口，首次主动claimed，回传assignment_source_sha/实际ack_peer_feed_sha/准确reviewed_sha/revision。

## 增量范围

1. R1：CSS仅把.listmode信息列改为flex:1 1 0/min-width:0，标题/副标题容器限宽，标题按钮可收缩。复用B先前同样B19+9次LongTitleWithoutSpaces数据，在390×844列表核对document不超视口，长标题省略/布局可读、收藏可见可点；补手机网格、1440桌面及播放器。不得用overflow-x:hidden遮住控件。
2. R2：admin/user/index.vue两个搜索handler现在都跳/manage/music，保留原username/email字段和原始值；旧store已有该路由限定监听及参数解析。用有资源owner、不同owner和零资源目标，分别从管理员用户菜单走Username/Email，比较实际请求参数、后端total与渲染结果，确认不显示其他owner结果。缺字段提示不回退全库；普通keyword/DemoCatalog入口不改。
3. 只复核两项增量及必要回归，不重复完整25条/26场景基线、Java/Python或MUS-017后端。源码无API/schema/锁变更，npm run build与必要的旧media6/player5检查按变化选择，避免无理由重复安装。

## A本轮证据和不足

A旧CSS离线fixture在390px实测1432宽（与B1464字体环境区别保留），修复后390、收藏x327–354且可点；手机网格390及桌面列表1440无溢出。该fixture使用真实产品CSS和同歌曲行DOM，不是对Vue真库的冒称。另真实普通账号20首列表文档384≤390、20收藏按钮在视口，最长真实标题100字。

R2执行实际handler体、router/message替身：旧两个/music目标回归，新/manage/music且含空格/+查询原样保留、缺字段不导航；不称真实管理员HTTP。未新建/提权用户或改演示元数据，完整管理员浏览器/HTTP差异验证由本卡补。A build、player5组、media6项与diff通过，真实Grupo播放/暂停正常。见verification/MUS-020.md及json/截图。

使用自己的隔离临时库/合成账号/音频，不请求A现有服务或搬运其凭据。无环境时明确blocked；截图/探针/真实HTTP边界分别披露。A5175已恢复，仍代理旧A8080运行服务，不是新Java验收。

完成只交两B报告，写review_completed与approve/request_changes/blocked、准确命令/观察/未跑项，不改A源码/总台账/任务卡/main。发布后回读核验并披露原子或顺序路径；不能把发布当A已接收或后台唤醒。MUS-017正式接收/E1/E2及MUS-016仍单列。


## A接收注记（2026-10-20；原派发范围保留）

B feed `5c0cebf85a20d14ccf0cdfe132a0f08d1d513fa1` / source `d8bba9d9199f802a3b5ceb0e7de0c2ab564f9688` 已主动交付本卡限定批准；A核验并接收，R1/R2关闭。详见 [接收记录](../../verification/MUS-020-B-acceptance.json) 与 [原字节B报告](../../reviews/MUS-020-B.md)。上文“先claimed/留B补验”等为原任务输入，现不再待执行；无新任务或重复领取。MUS-017/E1/E2与MUS-016仍单列，main未合并。
