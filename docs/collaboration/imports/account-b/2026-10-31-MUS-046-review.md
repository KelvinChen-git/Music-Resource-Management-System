# MUS-046-R1-B：扩大候选池诊断工具限定审核

2026-10-31（America/Chicago），owner / slot：b / B，revision 1，`review_completed`。结论 **`approve_scoped`**：未发现本卡范围内需要阻断交付的问题；批准仅适用于准确源码的合成指标和静态 runner 审核，不是模型质量、扩训或部署批准。

| 身份 | 准确值 |
|---|---|
| task_id | MUS-046-R1-B |
| branch | review/MUS-046-B-expanded-caption |
| reviewed_sha | e4e6bfdf320a4608953cd653fa60c6398a3ee601 |
| comparison_base_sha | e109b5c2ebc0531c059ddca844c63ad1b101ca84 |
| assignment_source_sha | aaf5e4bbffa61969b3d7bf993b408acec195a818 |
| ack_peer_feed_sha | aa3dfc1c2e6c816a5b355bc9469babe973ce984b |
| claimed source / feed | dd3cccbcf8e4c758f5aa05c20451882aa01cf217 / 2bcb2c8314d2a97624ecad1030ce7853ce8da353 |

从固定 A feed 读取同 source 的派发和 [准确任务卡](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/aaf5e4bbffa61969b3d7bf993b408acec195a818/docs/collaboration/tasks/MUS-046-R1-B.md)，核对 E21、固定 config、STATUS 和 035-N1 接收记录。独立 B clone 从干净 reviewed SHA 建立本分支，先发布 claimed 并逐字回读，再验证。本次只交付本报告与 [own latest](../collaboration/account-b/latest.md)；不改产品、A 任务入口或唯一 STATUS。最终交付提交由完成 feed 的 `handoff.source_sha` 给出。

## 实际验证

| 检查 | 结果 | 证据性质 |
|---|---|---|
| 原 `test_expanded_caption` | 12 方法，exit 0，0 failure/error/skip | 原生导入，真实 NumPy/标准库，无模型 shim |
| B 独立计算 fixture | 7 方法，exit 0，0 failure/error/skip | 直接计数 rank、分组重采样及显式向量运算作独立参考 |
| E21/config、runner 顺序与绑定 | 范围内一致 | 静态源码检查，不能记为真实 CLAP/文件运行 |
| 文档与交付范围 | `git diff --check`、链接/字段及仅两允许路径核对 | 文档检查 |

两套测试均首轮通过，没有测试或产品修复，不把内部 16 组指标/12 组差值或原 54 项 A 检查再累加为测试方法数。准备领取文档时，reviewed 基线没有 B 个人交接目录，首次写文件报缺父目录；创建允许路径的父目录后正常提交，不涉及产品或测试修改。

实际命令，仓库根目录：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_expanded_caption -v
PYTHONDONTWRITEBYTECODE=1 python3 .local/b/runtime/review046.py
git diff e109b5c2ebc0531c059ddca844c63ad1b101ca84 e4e6bfdf320a4608953cd653fa60c6398a3ee601 -- scripts/diagnose_expanded_caption.py services/audio-search/expanded_caption_metrics.py scripts/test_expanded_caption.py docs/evaluation/MUS-046-diagnostic-config.json
git diff --check
```

环境 Python 3.12.14 / NumPy 2.3.5。B 证据仅在本机忽略区 `.local/b/review-evidence/MUS-046-R1-B/`，`verified-evidence.json` SHA256 为 `c2a7c35c5e07e965f5db6cb1326d9162f1e9d6daa74dd3d90f714a5cc5824bbb`；包含原生日志、独立结果/脚本 hash、准确四文件 hash 与静态观察。未上传私有证据，不假设 A 可读取 B 本地路径。

## 具体审核结果

- [expanded_caption_metrics.py](../../services/audio-search/expanded_caption_metrics.py):9–27：额外未配对候选不要求 query，正例按本曲 ID 定位；降分排序、相同分按 ID 升序，拒绝非有限/空/shape 不符/重复候选/缺本曲。多描述先在录音内平均再录音等权，query 宏另报，输出明确未配对语义 unknown。B 不调用生产排序实现，按“更高分或同分更小 ID 的候选个数 + 1”独立算 rank，置换候选/query 顺序仍一致。
- 同文件:30–43：三个指标使用相同录音分组、有放回配对重采样；固定 seed `20261031046`、2000 次，按录音先求候选减 identity 再计算均值和分位区间。B 用显式逐次求和复算三指标区间及胜/平/负；重复某录音的整组描述后，录音均值及配对区间保持，避免把 24 条描述当独立的 24 首。
- 同文件:46–64：平均两两余弦与显式非对角点积一致，三向量 fixture 为 `-1/3`；caption/音频余弦先录音内平均，B fixture 为 `0.5`，区别于 query 等权的 `1/3`。仅几何描述，不支持因果结论。
- [diagnose_expanded_caption.py](../../scripts/diagnose_expanded_caption.py):44–61：整曲先均值聚合并归一化后映射 W、再归一化；三窗口各自映射后取最大分，分开报告。B 独立核对两池 × 四模型 × 两模式的 16 组结果及 12 组候选相对 identity 配对差值。另用两窗/对角 W 构造明确的不交换例，映射/聚合顺序最大向量差 `0.25989318568658953`，检查确实区分两种操作。
- 同文件:64–128：显式 config SHA，固定四模型/140/20/24/零新 fit/下载/test 模型输入，干净已提交源码；第 75 行独占输出先于环境检查和模型操作。cache/corpus/prior/G2 显式绑定，音频及 PCM 按 `(split, source ID)` 对应，特征/旧源码/三 W 校验 hash/shape/finite。第 108 行输入复核、110 行原 G2/环境检查、120 行 freeze，随后才在 128 行加载固定 A checkpoint。这里的 G2 验证会复核旧冻结元数据/源文件，不等于将其作为本轮模型输入。
- 同文件:130–171：全候选按 source ID 升序，不按 rank/tag/模型成绩筛选；120 个既有 train/val 录音完整 EOF 解码及 PCM hash 核对后取首 min120 秒、首中尾三个 10 秒窗；20 个原 dev 窗口复用，重新聚合必须与旧整曲向量完全一致。24 个原 text 特征及三 W 只读复用，无新 text encode/fit/download 路径；原 20 池所有 recording-macro 控制指标需在 `1e-12` 内重现。
- 同文件:181–198：结束前重核输入/本轮源码/环境/A checkpoint；保留 identity 决策固定，公开结果删除逐录音字段，只保留聚合。既有输出在进入 try/环境/模型前拒绝的顺序可静态确认；本次未执行真实 CLI 重试，不冒充实跑验证。
- [固定 config](../evaluation/MUS-046-diagnostic-config.json) SHA256 `fea78001f2693b0c3a590a29f0063a7ffc8a5742885273de98c30d9f90198a57`：与 E21 的 100 train/20 tag-val/20 caption-dev、全 140 候选、24 原描述、两池两模式、录音 bootstrap、只诊断不选模一致。三个新产品/测试文件和 config 在 reviewed 与 assignment 两个提交间字节相同；046 diff 未修改原 045 产品实现。

B 的已知 rank fixture 为 `[1,2,6,3,5,7]`，3 个录音、6 条不等数量描述、7 个候选（4 个未配对）。录音宏 R1/R5/MRR 精确为 `1/9`、`5/9`、`304/945`；query 宏为 `1/6`、`2/3`、`41/105`。移除四个额外候选后 R5 回到 1，验证扩大池能够消除该小 fixture 的 R5 天花板，不能外推成真实质量提升。

## 适用边界与交接

没有范围内阻塞发现，建议 A 接收此限定工具批准。真实 140 音频/24 描述/特征/旧 W/141 或 160 评分、CLAP/codec/G2 环境与 checkpoint 的实际文件运行均未独立复现，按卡只静态检查绑定；不安装依赖、下载模型或注入 shim。无真实 CLI/新训练/质量评测/保留 test/浏览器/Java/MySQL/旧 045 全套检查，A 的 54 检查及真实诊断不计为 B 证据。本卡不因上轮完整 driver 缺 torch 而将已通过的 12 个 NumPy 测试记作 blocked。

状态同步：035-R2 原报告 SHA `d7ef71af80b12ca7592dc918d17b3a6790a0b289a7348cc9f07b65f515a510e2` 已与 A 归档逐字 hash 核对，N1 关闭。046 中扩大池的正开发信号、MRR 区间含零等数值仅引用 A 已发布聚合；当前候选包含训练/标签验证录音，开发描述和候选已被看过，未配对语义 unknown，不能转述为新独立 test、显著收益、定位验收或部署依据。045 原门槛/结果不改，继续保留 identity。

接口变化：B 无；不改 API/schema/配置/锁/模型。数据/模型/索引版本：仅 B 自建合成 fixture，无真实版本新增或切换。未启动服务，未访问 A 私有工件，未合并或推送 main。

下一步由 A 精确接收报告、串行更新 STATUS，再另预注册后续训练/开发方案；本卡无需修复产品。source 与自身 `collab/account-b` 通过 GitHub 接口顺序发布，非原子，须精确回读报告及两个 feed 文件；最终 source/feed SHA 和实际结果见交付回执。发布不等于 A 接收。交付后释放本卡两文件占用，无后台轮询。
