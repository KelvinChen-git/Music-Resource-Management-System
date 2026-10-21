# 账号 B 最新交接

- task / owner：MUS-016-R1-B / B；assignment_revision：1；status：review_completed；verdict：request_changes。
- source_branch：review/MUS-016-B-demo-import；base/reviewed_sha：`69a3965e88d37d71a0067f263d207f2cb62fe668`。
- original_implementation_sha：`3092ae273e4a448246b8272fd20f3cd7de37dc91`；comparison_base_sha：`dbb631218b8ee7c87823ce594494b908b2849e32`（原新增范围定位）。五限定文件与原实现逐字节相同。
- assignment_source_sha：`ebae5eb9fba158152aa8f3061b25fb93f502e95a`。
- ack_peer_feed_sha：`596642d75c8d3186650f7c6790313d3f371b5553`；开始/结束前sync exit0、双方fetched且A未变。
- claim source/feed：`0c8d43a27c28d19e6ab8108ef66ff353abc29b1f` / `42b32b1a61c2602f48703458c9c21c4e746af324`，先发布回读再审核；最终source SHA见handoff。
- 报告：docs/reviews/MUS-016-B.md；仅本报告与own latest，无产品/API/schema/依赖/台账变化。

2项P2需修：R1保存凭据后注册发出前中断，原run重跑只login、不再register，真实本地SQL证明未建号，不能恢复。R2缓存证明仅比SHA，size/source/license被B合成fixture改错仍passed；不宣称A证明错误，不要求实时许可查询。另R3/P3为条件性公开边界：合成上游shareurl带Client ID canary时原样写公开JSON，safeLink也保留query；正常fixture/现有JSON未发现秘密，不冒称真实提供方或A已有泄漏。位置、影响、最小建议和原错误见报告。

仓库5项保护用例exit0，非历史50。恢复环境后Maven compile exit0/test.skip，未跑Java单测。node目录提取代码/替身store/API与JSON模板9组通过，含owner提示、外部资料不可播放、匿名guard及当前Sonora keyword；非浏览器/实际UI。

本地原生MySQL8.0.41+Java新slot B真HTTP，Jamendo HTTPS/MP3响应仅urlopen源fixture（TLS context仍验证）。主baseline-20261021-075843-10 exit0/status review_findings：13场景26次run，52预期断言含26锁清理，3发现另列，不称52全业务批准。首次2导入、完整缓存不联网重跑、部分缓存重查、上传ledger前后/metadata成功丢响应/lookup中断恢复、实际owner编辑构造歧义、错误音频完整SHA拒绝、错误origin/超限/HTML均分别取证。无个人Client ID/来源音乐/真实许可验证。

补验B16_ONLY_EMPTY=1另新库baseline-20261021-080006-10 exit0/passed，2次run/4项：真实metadata已建，成功GET list响应仅一次被私有fixture改空，原run失败保留，取消fixture重跑不增账号/上传/资源。不把该空结果称真实后端自然返回，不重复主矩阵。首轮baseline-20261021-075629-11 exit1/blocked保留，40条检查和2条发现来自console；当时私有fixture直接创建重复元数据被保护拒绝，改用普通owner编辑构造，未修改产品或断言。各轮数量不相加。

前次scratch已被环境维护清理，本轮从Git恢复独立clone/工具；旧已发布报告仍可核对，不称旧私有日志仍在。数据为本轮合成60秒MP3/新空V001/V002库/普通账号，主末9账号12上传11资源含故障残留；未访问A3307/8080/5175/曲库/凭据，无SQL写业务fixture、提权、自动审核、邮件、模型/索引变化。catalog输出仅一次性副本，审核checkout公共JSON未改。

主result hash817eb09d1211b3892673d0044f138020c2f238c14ad846da6d80e5c24162b681；补result cc2c7da7e1612bdeb9e8c0d71b9aefc316aa3229ae75f73f48e53b9e7a0ec437；verified-review-evidence ad1792fb618a149a4dec2574915981c6675df943e71aa3edbb77523359cb81e1。原始日志/适配器/音频/库未交付，A不能冒称重算；证据边界/失败/未跑项完整保留。

每轮自建进程停止、3308/8081释放，两报告活动占用释放。未新跑完整UI/build/Java/全Python/真实来源/生产或杀进程持久性；MUS-021已接受不重复，MUS-022不在B批准范围。下一步A接收并协调R1/R2最小修复、评估R3、派准确增量卡。GitHub插件先源码后feed顺序发布（非原子），回读后报告实际交付；发布不等于A接收或main合并，无后台轮询。
