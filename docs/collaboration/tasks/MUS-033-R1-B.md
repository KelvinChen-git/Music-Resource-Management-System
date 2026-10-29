# MUS-033-R1-B：新来源导入与素材核查增量

- owner b；revision 1；status assigned，先在 own feed 主动 claimed 并回读。
- reviewed_sha `10880f87f4073dc8f2d260fb72a07c9e52e59791`；comparison_base_sha `7704051f9a844816174c710d09e6f92e5b23f0e7`。
- 分支建议 `review/MUS-033-B-source-review`；准确输入与范围以本卡为准，不从main或旧clone推测。
- 027限定批准已由A接收，见[接收记录](../../verification/MUS-027-B-acceptance.json)；其占用释放。本卡不是要求重新审026/027、032收集器全链或真实模型。

## 输入、占用与输出

阅读E7、033验证报告与准确diff。重点是新`scripts/import_research_music.py`/独立测试、`source_review_pack.py`/测试、reviewPack新source分支/测试、View最小提示以及reviewAudio时长修复/测试。032 collector helper仅作为依赖上下文阅读，不将本卡批准外推032收集/许可结论。

只允许写`docs/reviews/MUS-033-B.md`与own `docs/collaboration/account-b/latest.md`。不得改A台账、dispatch、产品、公开catalog、锁或模型版本。B在独立clone/slot自造合成fixture；不读取A账号/音频/草稿/已判118原件，不把合成身份或模拟HTTP称真实Java/JWT验证。不需要新建账号或下载模型/真实音频；本卡内存音频与HTTP替身明确披露。

## 有界验收

1. 固定SHA、普通owner既有登录、缺失legacy状态限定回退、拒绝坏状态/错owner/歧义、原20只读、独立目录权限/路径/锁和恢复，真实ID必须来自HTTP。核对上传前输入/元数据/解码、Range/full响应验证与不提权/不自动审核；合成替身不能证明真实服务运行。
2. 新source-review精确schema/provenance/五query各4/严格ISRC和URL/30–600s、原20与新20去重、真实JavaID、初始全null/空模型建议、只能改人工字段、输出不覆盖。固定输入重建应与浏览器规则一致；保留旧两schema边界。
3. 独立合成包验证原UI导入、代号启用/0与null、评分与可选人工区间、草稿隔离与显式恢复、导出后CLI绑定校验；手机/桌面检查必要提示，无默认评分或旧标签迁移。记录实际执行与未执行范围，不要求重复旧完整矩阵。
4. 时长修复仅Incompetech原整曲：完整字节/SHA验证后取min(recorded,browser)，输入不突变；暂停/seek/恢复每次以原整曲身份重新计算，fresh终点比原有效端点短53ms也不得越界；当前位置>=fresh终点拒绝，旧schema/真正片段仍原100ms保护。相关Node测试可合成metadata，无需真人试听或A音频。

测试命令与A证据见[033](../../verification/MUS-033.md)。按实际风险选择独立增量；记完整命令/exit/计数/失败原因、hash和输入类型，不叠加旧运行。最终发布source和own feed并回读；报告准确reviewed_sha、comparison、revision、verdict、ack A feed。发布不等于A接收，不合并main，无后台轮询。
