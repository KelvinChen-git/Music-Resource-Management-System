# MUS-053 时间对应区间特征

2026-11-01 America/Chicago；owner A；base53d4466；branch `codex/MUS-053-interval-feature-cache`。本阶段只构建特征，不训练或评价模型质量。

输入为[MUS-052预检](MUS-052-pair-preflight.md)固定44录音232段生成caption：train37录音/33作者组件/209段，validation7/7/23；固定输入SHA见[配置](MUS-053-feature-config.json)，接口边界见CONTRACTS E27。原051隔离/052许可与3参考局限保持，teacher确切缓存音频未取得，当前3参考相符不能外推所有232语义/时序为真。

原音频只读，重新实际EOF解码至48k mono并核PCM哈希。每区间原float起止finite、15–30秒、不超实际EOF，再round至样本；从区间首、中、末取10秒，三个起点去重，只编码这些窗，先unit、均值、再unit。三窗在15–30秒区间可能重叠，不等于完整逐帧编码；不用旧整曲/首120秒表示冒充精确区间。每split的每录音总权重1/N，再平均到该录音各区间，209段不称209首独立样本。

原caption逐字输入固定CLAP A，SDK77token截断，全部长度保存私有并公开聚合截断数量，不按语义/得分过滤。模型冻结、MPS FP32、audio batch3/text batch6、无autocast/fallback/下载；来源/源码/环境/模型/配方在模型加载前冻结。固定hash先选3不同train作者组件区间，在CPU编码9窗/3caption，再同一固定模型转MPS正式编码；maxabs/cosine各<=1e-4才通过数值抽检，不冒充全232 CPU一致或质量验证。

新私有目录 `.local/a/mus053` 已ignore且目录0700/文件0600。只在所有行/边界/PCM/unit/CPU抽检及输入源码环境末次复核通过后写 `cache.json` ready_for_bounded_pilot。consumer显式split/期望设备和模型，校验清单/result/key/NPZ SHA/全部行分组权重，返回本split音频和文本向量、录音/作者组件/权重，不返回另一split或原caption，不加载Torch/CLAP。特征ready只用于另行预注册的有界pilot准备。

实现阶段124相关检查passed（14新/110既有）；真实运行/独立复算结果在[验证](../verification/MUS-053.md)补录。无Java/Vue/数据库/依赖锁/原备份/main/B047卡变化，不运行无关Maven/build，不开项目保留test或新的人工评分包。


## 实际结果

干净716b3fcea1902a54fe17a5e4b64db78334ddb28a首次构建exit0，44/232全部通过，696窗口用途引用即696唯一窗口；新构建产物22,414,359 bytes。MPS窗口SDK20,057.00ms/文本2,293.81ms、完整含完整性47,599.44ms；没有匹配全量CPU时间，不算加速比/P95。三项CPU差分别2.26e-7（9窗）、1.89e-7（3区间均值）、3.01e-7（3caption），最大cosine距离1.68e-12。独立重建232边界/696绑定/录音权重/聚合（差0）、全原文hash/离线token长度、key/源码提交与输入hash一致，3原音频单独EOF解码的9控制窗逐点完全相同。

全部原caption17–178token；124/232（53.45%）超过77，train110/209、validation14/23。实际输入为原文tokenizer的前77token，不声称覆盖完整长描述；不事后换样本/改写文本。CPU三个固定caption为49/76/64token均未截断，数值抽检范围不包含长caption。独立tokenizer长度复核不等同语义质量；长描述监督遗漏要在下一轮训练协议显式处理。当前cache ready_for_bounded_pilot、training_protocol_frozen=false，不能将ready称为人工benchmark或已获训练质量批准。

两个实际consumer为209/23×512、录音37/7、组件33/7、各split权重和1；未加载Torch/CLAP，未返回另一split/原文。原输出重跑在模型加载前FileExistsError，原工件集合与SHA保持。旧045–052集合/哈希、原951输入+原B047卡、23冻结源码/54离线cache/043044/160原件和保留版f3b0da1干净保持；新私有目录700/文件600，仅aggregate/方法/hash公开。124检查只计一次14新+110旧，同操作者独立复算不冒充B审核。B047仍未认领，不外推053批准。
