# MUS-050：文本—音乐描述训练来源的实际核查

2026-11-01 America/Chicago；A；分支 `codex/MUS-050-caption-source-audit`，基线ea54ffc。承接049“正tag训练未改善主整曲检索”的结果，改变数据核查方向，尚未启动新训练。**当前优先完成描述与现有研究音频的覆盖核查，不能把网络上的caption样本数当本项目可训练曲库数量。**

## 核查结果与角色

| 来源 | 本轮证据 | 结论与后续角色 |
|---|---|---|
| MusicCaps | 官方固定CSV全5,521个视频ID，各10秒；AudioSet train2,663/eval2,858 | 专家人写描述候选；只发ID/时间/文字，没有原音频或音乐作者身份。不能据`author_id`作音乐作者隔离，它是描述撰写者ID |
| MusicBench | 官方原始训练JSON52,768行，实际5,079视频ID、42,611个音频路径；测试A/B各400 | 包含音频增强/模板/ChatGPT改写，不能算52,768首不同音乐或新人工真值。它有可发布音频归档，但还不是本项目可用音频 |
| JamendoMaxCaps | 固定卡片/列表；两个日期metadata文件实际1,944行/494个ID；caption文件HEAD=787,366,586 bytes，正文未取 | 生成描述的弱监督备选；可按Jamendo身份与本项目已用/保留组核关系，下一步先核现有训练录音的caption覆盖和区间，不先下载整库音频 |
| LP-MusicCaps-MTT | 固定卡片/文本parquet列表，仅卡片声称train18,706/valid1,825/test5,329；未取parquet核数 | tag→LLM伪描述备选，不称新人工标签或已通过作者/作品划分。作者明确不建议默认使用attribute-prediction/pseudo-attribute |
| Song Describer | 继承041/045的既有划分，本轮未读其保留描述 | 继续评测角色；不挪用已保留/已用开发caption作训练，后续生成caption匹配也要先排除全部SDD关系组 |

一级来源：[MusicCaps固定卡片](https://huggingface.co/datasets/google/MusicCaps/blob/0a51889b340037bb75a9a0858af2e4ece21f7f89/README.md)、[MusicBench固定卡片](https://huggingface.co/datasets/amaai-lab/MusicBench/blob/b141e962aacc19ffd51c15732738040377989203/README.md)、[JamendoMaxCaps固定卡片](https://huggingface.co/datasets/amaai-lab/JamendoMaxCaps/blob/13090d785d071dcd617636deaa4a9775936ac995/README.md)、[LP-MTT固定卡片](https://huggingface.co/datasets/seungheondoh/LP-MusicCaps-MTT/blob/64c5d14e25b8919c98e58f1e048eb470ba702933/README.md)、[SDD用途](https://github.com/mulab-mir/song-describer-dataset/blob/main/docs/datasheet.md)。实际计数来自本机固定原文件，不是网页估算；全文件SHA/字节见[聚合结果](../verification/MUS-050-results.json)。

## MusicBench：样本、来源与测试不可混计

按音频路径basename提取11字符YouTube ID，后续可选`_整数`是增强后缀；必须与MusicCaps CSV逐一关联，时间以原CSV为准。训练各组样本数：3,412组各14行、1,666组各3行、1组2行，总52,768。训练`data/`15,236行实际只有5,079个未增强路径；`data_aug2/`37,532行。来源视频仍不等于去除翻唱/合辑/上传重复后的独立作品，不能称已隔离5,079首歌曲。

MusicBench自身train与test的来源ID交集0。TestA/TestB是完全相同次序的400个音频路径/ID，仅文字条件不同，不能合并算800首或独立两批测试。train+test共5,479个MusicCaps ID，原5,521中42个未在该版出现。

但其train不是AudioSet-train：5,079中2,631个来自MusicCaps的AudioSet-eval，另2,448来自AudioSet-train；行级flag全部与原CSV相符。因此使用全部MusicBench训练后，不能再把原MusicCaps AudioSet-eval当无重叠测试。这不是MusicBench自身train/test重叠错误，而是两套split定义不同造成的跨数据源泄漏风险。

若以后采用专家原描述，应直接从MusicCaps CSV取canonical caption，并匹配同视频的未增强音频，不能默认MusicBench某caption列全是原文。实际train的52,768行仅6,745行`alt_caption`逐字等于原CSV，且均在未增强路径；这只是字节等同性核对，不判其余文字错误或测量描述质量。

已私有保存2,448个“MusicCaps非eval且存在MusicBench-train未增强路径”的候选metadata框，不作最终train/dev/test或就绪音频。两表均缺足够音乐作者/作品字段，无法核跨视频/跨Jamendo/FMA关系；10个`author_id`属于描述作者，不能替代音乐人分组。还需合法可用音频、真实EOF、原clip时间、内容去重和作者/作品核查。固定列表中的MusicBench音频归档为16,757,993,240 bytes、gzip格式；本轮未取任何音频/归档，不为小预检自动取约16.76GB。

## JamendoMaxCaps：先去重、核权限和描述时间范围

只按文件名取最早两个日期metadata，不按音乐标签/模型/描述选取；它们不是代表全库的随机样本。2008-01-01为944行/248ID，2008-01-06为1,000行/246ID，两文件ID交集0；完全重复行分别585/613。同一个ID的元数据也可能不同：合并494ID中7个有不同许可URI，252个audio字段值不同，不能默认第一行或最宽松许可有效。第二文件29行download_allowed=false；许可还包含NC/ND等，不因数据卡整体CC-BY-SA声明就覆盖逐曲条件。

该小样本与现有100train/20tagval/20caption-dev的录音ID交集均0，**不推断全库无覆盖或无交叉**。caption正文787,366,586 bytes约750.89MiB，超过本轮预算，仅HEAD读长度、未取正文/核总条数/训练ID覆盖。卡片描述的是Qwen2-Audio生成的30秒区间caption；它不是人写真值，也不能直接监督整曲或把已有首中尾三窗当对应区间。完整caption/作者作品关系与实际可用容量仍未知。

## 下一步的固定入口与门槛

下一任务先做**有界、只保留白名单ID的caption覆盖审计**，优先检查已有100训练/20标签验证研究录音，复用已验证官方音频，不自动获取更多音频：

1. 在读取caption正文前，冻结现有训练/验证ID、作者/合作组件、作品/内容关系及排除集合；全部SDD、已用caption-dev、保留caption-test/原200tag-test及旧60关系组排除。保留metadata原split，不为凑覆盖挪测试或已用开发样本。
2. 固定JamendoMaxCaps版本/文件SHA或稳定表示与完整长度，再另定可承受的metadata流式预算/恢复账；当前约0.79GB单文件不能复用本轮96MiB预算静默下载。只把允许ID的caption与起止时间输出给训练准备模块；未知/冲突/无明确BY或BY-SA逐曲许可、禁止下载者排除，冲突要查清或隔离。
3. 先报告覆盖多少已有独立录音/作者组、每组caption数、有效时间区间及重复/冲突；保留描述真实来源`model_generated`，不得自动改为human/人工判断。容量不足如实报告，不补造描述或改排除来凑数量。
4. 有足够覆盖后，另立区间对应音频特征和新训练方案，再比较预先固定的弱监督方法与identity。当前048特征不能因来自同一首音乐就视为任意30秒caption的匹配特征；未配对曲目也不自动算确认负例。继续使用现有SDD作为已看开发比较，最终保留测试不提前打开。

这是一条先验证覆盖、再决定训练的工程顺序，并非认定生成描述优于整曲tag。备选是上述2,448个MusicCaps来源框，前提同样是有界合法音频与身份关系核查，不能把候选容量写成已就绪训练集。当前**新增训练就绪音频0、新fit0、模型保持identity**，不要求用户继续全矩阵人工标注，也不租GPU或改变页面。
