# MUS-046-R1-B：扩大候选池诊断工具限定复核

- owner：b；assignment_revision：1；状态由固定account-b.json派发，B先claimed再审核。
- reviewed_sha：`e4e6bfdf320a4608953cd653fa60c6398a3ee601`。
- comparison_base_sha：`e109b5c2ebc0531c059ddca844c63ad1b101ca84`。
- review_branch：`review/MUS-046-B-expanded-caption`。
- assignment_source_sha：以包含本卡且派发046-R1/rev1的A feed `handoff.source_sha`为准，与reviewed_sha区分。
- 允许输出：仅新 `docs/reviews/MUS-046-B.md` 与 `docs/collaboration/account-b/latest.md`。不改产品/STATUS/A任务入口/原B报告/历史审核。

## 输入与范围

读A固定feed与准确source任务卡后，从reviewed_sha建立独立工作分支；检查新 `services/audio-search/expanded_caption_metrics.py`、`scripts/diagnose_expanded_caption.py`、`scripts/test_expanded_caption.py`，以及E21和046固定config的契约一致性。原045/CLAP/Java/Vue/权限/大规模训练工具不扩审。原035-R2已接收限定批准/关闭，不重复领取。

重点：

1. 原20配对录音可在有额外无query候选时计算；未配对语义unknown，多caption先录音内平均；稳定ID并列、非finite/缺本曲/重复候选拒绝；MRR/R1/R5与两池/两模式分开。
2. Bootstrap按录音配对分组，三指标、固定seed/次数；几何平均两两余弦的公式与分组caption均值，不作因果或显著性声明。
3. 140候选固定来源升序、不按成绩筛选；120旧train/val新编码首120秒同视图、20旧dev窗口/整曲/24文字特征复用，实际source/PCM/receipt/features/W/原环境/模型绑定，输入与源码前后检查。只能静态检查真实模型/文件路径，不访问A私有文件冒充复现。
4. 无新fit/下载/测试输入/模型选择，独占输出已有目录在模型操作前拒绝；源窗口先映射与整曲聚合后映射区分；不把三窗作定位能力。报告中的正开发信号不等同独立test/部署批准。

## 验证

最低独立合成验证（无需torch/codec/CLAP）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_expanded_caption -v
```

当前12个合成方法需NumPy；有可用依赖则直接运行，不为此安装/升级依赖。另写少量独立NumPy/标准库fixture核对已知rank/多caption等权/额外候选/区间/几何，保留真实结果及失败；缺依赖原样记blocked，不注入模型shim冒充真实模型运行。可静态检查driver序列与绑定，但不要把静态观察计作真实CLAP运行。

无需下载模型/音频、读取A私有140音频/描述/特征/W/141或160评分、启动服务或改配置/锁。A报告的54项和真实140比较不是B本人检查。记录准确命令、唯一计数、首轮错误/修复、未运行项与原因，最终verdict approve_scoped/request_changes及适用边界。

完成后以自身feed发布 task_id/revision/reviewed_sha/comparison_base_sha/assignment_source_sha/ack_peer_feed_sha、报告SHA、实际结果与占用释放。不得合并main，不能将工具批准当模型质量验收。A串行接收更新STATUS；无需后台轮询。
