# Account B — MUS-044 plan review completed (user-directed)

- review_id / owner / review_revision：MUS-044-PLAN-B / b / 1（用户直派计划审查，并非A正式044审核卡）。
- status / verdict：review_completed / needs_revision_before_scale_up（计划审查，不是044工具正式验收）。
- source_branch：review/MUS-044-B-training-plan；交付SHA由feed handoff.source_sha给出。
- reviewed_sha / base_sha：46b52db8b2999ab015084f423545e4f2cd5c4e03。
- implementation_base_sha：83ebeea8e32d41c9652d4c8dbdf75f24e8024fab；044实际训练源码5bce9190386053d76d056e68fd0e7cd1d936f338。
- assignment_basis：用户要求“同步项目状态并审查拟定的训练计划是否合需要优化（044）”。
- ack_peer_feed_sha：3a1b158299ee3a9665488e97b85997ec6e4ddc3c；A source46b52db8b2999ab015084f423545e4f2cd5c4e03。
- claim source / feed：79b4c8a71370d5e9a356959cca874a332a4a5a5e / f514779c865cae876024c6d018364f671a923071，先发布精确回读再审。
- standing_dispatch：MUS-035-R2-B / revision1 / assigned_unclaimed，准确de255c7724926c6f823abceecf0b9a487a467d6d，保留原卡，不替代/冒充领取。
- 本次唯一修改：docs/reviews/MUS-044-PLAN-B.md；docs/collaboration/account-b/latest.md，交付后释放。

结论：冻结CLAP+identity-prior ridge作为20首链路预检合理；扩大训练前补R1–R4。R1须有自然语言caption-dev/最终test及identity对照/已知配对检索主指标，tag Recall不能替代产品目标；现成人写数据优先，不追加大矩阵人工标注。R2 sum损失的lambda100从20扩1000会令lambda/N由5变0.1，强度减弱50倍，须规范化/用独立开发集选择有限alpha；原044 smoke配置保留。R3当前runner硬编码20/lambda100，需另立通用runner及文本保持/音频映射/聚合顺序/片段模式和版本缓存契约。R4先预算内实际下载/EOF/内容隔离/固定替补，把metadata计划变成可运行数据，不按模型成绩调样本。

建议先冻结caption-dev、均值损失alpha最多3候选+identity、聚合与预算，从现有1000/200清单固定前缀小批门控，有验证收益才扩大，再一次验收保留test。N>512可用等价512维primal，特征只编码一次；闭式ridge不需要epoch/学习率。20样本更新秩≤20，不能只以26万存储参数断言必然过拟合；正tag均值的信息损失和三窗口整曲/单窗口片段差异须实测，不将代数反例称真实退化。

32已有相关标准库/NumPy测试和9独立数值/事实核验exit0，无依赖shim/安装。512维primal/dual差5.55e-16、rank20/正交保持；重复样本50倍时lambda100等价原lambda2，lambda5000保持原解（并非真实最优建议）；centroid碰撞与归一化聚合不交换反例通过。只用B合成矩阵，无A私人音频/标签/特征/W/1400原表重算或真实CLAP训练。证据SHA759604e71cbcefd2568b098352cb1a735b1006247b849df69ee3c3e13d330478；详细位置/方法/建议见[计划审核报告](../../reviews/MUS-044-PLAN-B.md)。

同步状态：主应用A记录60首；040四批已完成、042全160小样本比较已出，A整曲/片段P@5=.125/.175，另检查点B=.075/.125，5/8无正例、理想上限.225；不只是模型排序问题。043研究20首已取回；044只有20 training/60窗口、目标下降但训练tag Recall仍.281309524，validation/test0；1000/200/200尚为metadata。已看160对新模型只能作development；本报告不改其历史结果或借035批准扩大验收。

下一步A接收并串行安排后续任务；standing035-R2不变。无应用/API/schema/锁/公共catalog/A台账/044配置/模型/索引变化，未启动实际下载/训练/部署。已授权GitHub接口顺序发布source再B feed，非原子；远端可读不等于A接受建议或035-R2关闭。两文件交付后释放，无服务/端口、后台轮询或main推送/合并。
