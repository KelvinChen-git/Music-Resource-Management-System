# MUS-002：CLAP 离线可行性结果

2026-10-21更新：MUS-022已补真实20首MP3解码/933片段/固定模型候选排序的运行证据；下文2026-10-19的“尚无真实语料/解码”是原检查点。当前仍无人工qrels/质量验收，不冻结模型或discovery-v0。详见 [MUS-022](verification/MUS-022.md)。

2026-10-19，owner A，分支 `spike/MUS-002-clap-feasibility`。功能基线来自 `chore/MUS-001-dev-baseline`；本次探针源码提交 `ab5d6f3697f37ecfbc96c3aa062a7f2b6702ca6d`。**只通过编码可行性检查；模型选择、检索效果及 discovery-v0 尚未冻结。**

## 已核对并实跑的候选

| 项目 | 本轮实际值 |
|---|---|
| checkpoint | music_audioset_epoch_15_esc_90.14.pt |
| 发布仓库 / revision | lukewys/laion_clap / b3708341862f581175dba5c356a4ebf74a9b6651 |
| 文件字节 / SHA-256 | 2352471003 / fae3e9c087f2909c28a09dc31c8dfcdacbc42ba44c70e972b58c1bd1caf6dedd |
| 架构 / fusion | HTSAT-base / false；不是默认 HTSAT-tiny |
| 文本构造依赖 | FacebookAI/roberta-base，revision e2da8e2f811d1448a5b465c236feacd80ffbac7b |
| 实际向量 | 文本 [2,512]，音频 [2,512]，float32；范数约 1 |
| 预处理 | 立体声均值→48kHz soxr_hq→右侧补零到 480000 点→SDK int16 往返量化 |
| 4 秒 / 10 秒实际输入 | 192000 / 480000 个真实采样点；分别补 288000 / 0 点 |
| 参数加载 | strict=True，missing=[]，unexpected=[]；仅去掉非学习 position_ids buffer |
| 重复编码 | 同一进程两次音频编码 max abs diff=0；不据此宣称跨所有平台 bitwise 一致 |
| 预处理测试 | 9 项通过，pip check 无依赖冲突 |

上游 HTSAT-base JSON 中 embed_dim=1024 是音频架构内部配置，不能直接作为对外向量维度；本轮实际投影输出为 512。RoBERTa 构造时会先提示 pooler 初始化，随后 CLAP strict load 覆盖所有模型参数；不将这一中间提示解读成需要额外训练。

官方依据：[LAION-AI/CLAP README](https://github.com/LAION-AI/CLAP)、[checkpoint 固定 revision](https://huggingface.co/lukewys/laion_clap/tree/b3708341862f581175dba5c356a4ebf74a9b6651)、[PyPI laion-clap 1.1.7](https://pypi.org/project/laion-clap/1.1.7/)。官方 README 的旧 CUDA / Python 3.10 训练环境不能直接描述为本机已经验证的环境；PyPI 包与 GitHub main 的代码也不完全相同，因此报告保存实际安装文件哈希。

## 可重复命令与证据

步骤见 [services/audio-search/README.md](../services/audio-search/README.md)。依赖锁为 CPython 3.12 / macOS arm64 解析结果，非跨平台锁；没有修改 Java / Vue 锁文件或部署模型服务。

原始非敏感结果：[首次成功探针](verification/MUS-002-probe.json)；[缓存离线复跑](verification/MUS-002-probe-offline.json) 同样 exit 0（HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1）。报告绑定源码 SHA、探针 / 预处理 / SDK 文件哈希、checkpoint 和 tokenizer revision、实际模型配置、包版本、向量形状、范数和单次耗时。

本轮 16GiB arm64 CPU，2 threads。一次缓存已存在的加载约 2371ms；两条音频首次批次约 173ms，重复批次约 135ms；两条文本约 64ms；进程峰值 RSS 约 1.95GiB（Darwin 的 ru_maxrss 为字节）。这些是单次探针观测，**不是 P50 / P95、并发或完整 Java API 延迟**，不能用于宣称达到 300ms 检索目标。

预处理测试先发现 44.1→48kHz 的浮点 ceil 多出一个采样点；实现改为整数长度，再由 resampler 裁齐 / 补齐。保留 1 秒、10 秒和非整比例长度回归用例。

## 尚未通过，下一步不能跳过

- 没有许可明确的 30–50 首真实音乐 manifest，没有人工查询 / 相关性判断；合成正弦波不是小音乐语料，也不能证明自然语言找音乐、氛围相似或片段定位有效。
- 未验证 Python 的 MP3 / WAV 解码、FFmpeg、不同编码格式与损坏文件；本轮只验证内存波形。Java 的 MP3 smoke 是另一条路径，不能替代 Python 解码验收。
- 未生成索引、整曲基线、片段搜索、Java gateway 或新界面。checkpoint 为候选，尚未比较其他模型。
- SDK 短音频默认重复填充，与项目零填充建议不同；当前探针先补到定长以避免隐式改变输入，真实短段效果仍需比较。RoBERTa tokenizer 上限 77 token；长文本截断策略需要进入契约决策，不能只看 1000 字符限制。
- 下一检查点：准备来源 / 许可 / 内容哈希明确的真实语料，验证解码及短尾段；建立小规模文本与参考音频查询和整曲 / 片段对照，再冻结模型与 pipeline 版本及契约 fixtures。

MUS-002 仍为 blocked（真实语料与效果验收未满足）；MUS-003 / MUS-004 不按未经冻结的 API 各自实现。账号 B 当前先审 MUS-001，不占用本目录或改共享 CONTRACTS。


## 2026-10-21：真实小语料补证

准确源码ef8588a，干净工作区运行：读取既有20首演示MP3及原下载证明，逐首哈希/来源声明匹配，实际解码总4722246ms；候选10s/5s生成933片段，20尾段零填充。固定原checkpoint严格加载后，片段/整曲聚合/8英文文字/3库内参考均实际输出有限归一化512维向量，生成两模式精确候选排序。23项预处理/语料/边界等测试及独立工件复核通过，拒绝覆盖旧run的负例按exit1单列。

所有生成向量/manifest/排序均在本副本ignore目录；未接Java/新网络服务或数据库。8查询51候选的后处理标注包标签全null，不是人工qrels或held-out测试；音频参考来自候选曲目。此处只是一次离线链路实证，不能报告质量提升、P95或生产授权。MUS-002剩余blocked为人工判断/模型效果比较和契约冻结，不再以“从未真实MP3解码”描述最新状态。
