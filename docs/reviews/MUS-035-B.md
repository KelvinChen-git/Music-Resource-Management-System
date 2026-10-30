# MUS-035-R1-B 两来源离线工具独立审核

2026-10-29（America/Chicago）；owner/account B；revision 1；status `review_completed`；verdict **`approve_scoped`**。本卡未发现阻塞性源码问题，另有N1（P3）输出权限健壮性问题回传A。

批准限于三工具的静态审核、可运行的标准库/NumPy分组，以及明确使用替身的解码/编码驱动控制逻辑。**原生完整测试入口被缺依赖阻塞**，没有真实MP3解码、soxr DSP、Torch/CLAP加载或A私有结果复算，不将本结论外推成模型/质量验收。

## 任务与固定输入

| 字段 | 值 |
|---|---|
| task / owner / assignment_revision | MUS-035-R1-B / b / 1 |
| reviewed_sha / 分支开发基础 | `9797ed4b8766f8cd5f6cd7759b86bd309cef2f7d` |
| comparison_base_sha | `b42b767afc0bd3ddb76601a436f8073c3d72106c` |
| assignment_source_sha | `74645de71c173c43811d7d0d98548089a1836491`，本次固定A入口，035/rev1原卡 |
| ack_peer_feed_sha | `9aa68ee154142dcdc8d336130a8498ccc80aa775` |
| source_branch | `review/MUS-035-B-expanded-retrieval` |
| claimed source / B feed | `d6742716bf629b75acb8939e90fd3fb0002ee1ee` / `a2f53b2ce51ed46a42614fb96808e0d9bdb89b6c` |
| 交付 SHA | 本次B feed `handoff.json.source_sha`，不在同一提交自引用 |
| 唯一修改文件 | `docs/reviews/MUS-035-B.md`、`docs/collaboration/account-b/latest.md` |

从固定feed读取handoff/latest后按source读dispatch、准确卡、E8和035报告/results及实际diff；根AGENTS未变化，无子目录AGENTS。先发布claimed并精确回读再审。开始及检查点sync均exit0/fetched，A入口仍为上述SHA。本轮write通过已授权GitHub接口实际确认，不请求Token或假定原生push凭据。

033限定批准已正式接收：接收JSON与A导入原报告核对SHA `3c41a66a6e0db5e304631b4a0ca97d474626a42377d7faa34c12e79069f47d8d`一致；不重复033。本卡assignment来源不是035真实编码提交`17a31f5…`。A已推进到039，并已有037的141判断/精确开发比较；这些只作当前文档事实读取，不把035历史138/区间当全局最新结果。

## N1：特殊umask生成不可读工件（P3，非阻塞）

文件：`services/audio-search/research_probe.py`第99行的`private_output`，第103–113行的`write_json` / `write_vectors`。

这些入口只给`mkdir`/`os.open`传入0700/0600，没有在创建后明确设置模式。在B独立新目录中设置`umask 0777`后，三个真实函数均成功返回，目录、JSON及NPZ实际mode全部为`000`。这没有扩大访问权限，但普通用户后续无法正常进入目录或读取报告/向量，且不符合E8约定的0700/0600；本轮常规`umask 0077`的合成完整运行不受影响，因此列P3而非阻断本卡批准。没有执行另一个普通uid进程；模式及函数行为是实测，后续普通用户访问影响据文件权限推断。

建议A在独占创建目录后明确`chmod(0700)`，在两个独占文件fd上执行`os.fchmod(fd, 0600)`再写入，保留O_EXCL/O_NOFOLLOW和不覆盖规则；补一个受限umask可读性回归。复现命令为`python3 .local/b/runtime/permissions35.py`，exit0表示**问题复现成功**，不是产品权限检查通过。原035源码未改；记录模式后仅将B私有fixture恢复为0700/0600。

## 源码检查

只审核新增`research_corpus.py`、`research_probe.py`、`research_evaluate.py`及三测试。实际diff另含必要文档；旧corpus/preprocess/probe/source_review_pack等只读作依赖。六源码与准确9797ed4逐字节相同，并匹配A公开035-results所列SHA；未修改产品/API/schema/依赖锁、公开catalog、模型版本或A台账。

| 范围 | 已检查行为及限度 |
|---|---|
| 两来源适配器 | 六显式SHA、E7重建、provider/source与Java track/file/content去重、前缀副本和原证明绑定，拒绝symlink/hardlink/逃逸，原20只读；返回资产不混人工字段，按数值Java ID排序。 |
| 新来源decoder | 固定65536 float32 out缓冲，复制实际返回部分、至0帧EOF，检查tell增量、finite、30–600s，分开declared/history和actual，不补零迎合header。替身覆盖头部长/短于actual及poisoned未用尾块；实际SoundFile/librosa/soxr未运行。 |
| 编码driver | 源码干净且有提交身份、六输入/源码/checkpoint前后核对；checkpoint不符先于构造/反序列化，restricted loader参数、strict load、512维、完整40曲新编码、原窗口/整曲归一化均值/两mode规则。独占输出，失败/成功目录不复用；N1为例外模式缺口。 |
| 评估器 | 原三包/11 SHA、旧新report/五工件及源码绑定；query各自raw pin后canonical相等，旧20解码/窗口不变，新来源history/declared/actual与整数ceil分离。保留冻结rank数组，r/n/u、P@5上下限、exact null和五query等权，无未知补0或按标签重排。 |

标准库评估器验证的是显式pin及结构，不解码音频或加载NPZ来证明真实模型推理；本审核没有用自造report的固定模型元数据冒充认证权重。

## 实际命令、环境与计数

独立B clone/slot B；Python **3.12.14**、现有NumPy **2.3.5**。当前无`soundfile`、`librosa`、`soxr`、`torch`、`laion_clap`，未安装或修改依赖来掩盖。没有使用A模型cache/venv、账号、音频、标签、run或向量，没有启动Java/MySQL/浏览器/服务。

从仓库根目录执行，日志均在ignore的`.local/b/review-evidence/MUS-035-R1-B/`：

| 实际命令 | exit / 结果 |
|---|---|
| `python3 -m unittest discover -s services/audio-search -p 'test_research_*.py' -v` | **1 / blocked**：入口显示45 tests、24 errors，含子测试错误与driver模块导入占位；根因为缺soundfile/librosa/torch。不能写成45项业务失败或完整73通过。 |
| `PYTHONPATH=services/audio-search python3 -m unittest test_research_corpus.ResearchCorpusTests test_research_evaluate -v` | 0，**36 passed**：14资产+22评估；实际标准库/NumPy环境，无依赖shim。与首轮已完成项不累加。 |
| `python3 .local/b/runtime/mocked_dependencies35.py` | 0，**37 passed**：8 EOF+29 driver，显式缺依赖替身环境；不是原生37通过。 |
| `python3 .local/b/runtime/independent35.py` 最终 | 0，45独立断言/预期拒绝及N1观察，`passed_with_observation`；B自造40资产/三包/解码与SDK边界，原Git和NumPy实际运行。 |
| `python3 .local/b/runtime/metric_cases35.py` | 0，另4独立手算断言，部分跨模式重叠/4条已判+1条含未知/全已判无相关，修改的私有fixture最后恢复原字节。 |
| `python3 .local/b/runtime/permissions35.py` | 0，N1模式缺口复现；JSON/NPZ/目录均000，非产品通过。 |
| 独立脚本内真实子进程 `python3 services/audio-search/research_evaluate.py …` | 首次CLI exit0；相同输出重建、逃逸.local输出分别预期exit1；完整11pins/命令在`independent-result.json.commands`。 |
| `git diff --check`、允许路径/源码字节/文档检查 | 通过；交付只B两报告。 |

37项替身测试在新进程显式注入5个模块边界；真正未替换的数值计算为NumPy，`fix_length`仅用NumPy pad/truncate。未使用的真实codec/模型构造/加载默认直接抛错，作者测试仍对SoundFile返回、resample调用、SDK、load_state_dict及torch.load按原有测试设置替身。没有将shim安装为真实包或修改其源码；结果只支持调用参数、shape、pin及控制流，不支持真实重采样/模型兼容或安全反序列化实际执行。完整原生入口仍blocked，不把分组拼写成A的168或全环境验收。

## B 独立合成闭环

B自行创建20旧+20新伪音频/证明/历史decode和普通owner/catalog；仅复用B自己033的fixture生成方法，未用A测试fixture代替独立数据。使用公开固定selection/8原query文本，不访问提供方。假backend `.local/a`只是B目录中的合成配置材料，不连接A端口或真实账户。

适配器完整重建6pins和40资产，另在B自有副本上增加hardlink/symlink后确认拒绝，再恢复；缺任一pin拒绝。独立内存decoder以NaN污染out未用部分，实际有效视图变长、同一buffer复用；确认复制数据保留、0帧EOF额外调用、头部大/小于actual均可正确分离、tell/count错则拒绝。这不是MP3解码或来源许可证据。

driver使用实际Git身份`d674271…`（仅B领取文档，六核心源码等于9797ed4）、真实6pins/source hashes/只读资产，替换codec/SDK和模型加载边界。checkpoint是独立假sentinel字节，**测试内明确替换期望checkpoint SHA**；strict/weights_only/mmap及shape检查仍执行，不能称加载了官方checkpoint。测试脏Git仅临时创建本卡允许的B报告未跟踪标记，在finally删除；实际拒绝发生于模型构造前。错checkpoint也不构造/加载。

先在原20完成后注入新decoder失败，只留下`failure.json`；再用新输出重新完整处理40曲，没有复用半途向量。合成成功工件为**40 tracks / 459 segments / 8 text / 0 reference / 512维 / 20 padded tails**；这些不是A的1557片段结果。B另用NumPy逐曲复算窗口嵌入均值/归一化、完整窗口和16个排名数组，包括同分数值ID规则；真实NPZ以`allow_pickle=False`读取。已有成功与失败输出均FileExistsError，模型调用数和成功工件SHA不变。初始输入前后原字节保持。

评估专用旧/新report均为明确标记的**合成schema fixture**。为触发固定官方MODEL验证字段，评估fixture的MODEL元数据按契约填写；它与假checkpoint实际driver report分开保存，并有`synthetic_fixture_not_model_evidence=true`，不是权重认证。三合成判断包通过原工具生成后只填测试人工字段，数量精确51+67+20=138；不算真人判断。旧/新report、各工件及11pins绑定均由实际标准库CLI执行。

| 独立构造的情形 | 手算及实际结果 |
|---|---|
| 每模式5条query都含未知 | r/n/u总2/3/20，宏P@5下限0.08、上限0.88，exact null；三条query全5未知仍纳入五等权宏。 |
| 两模式同一批未知 | 每模式20个未知位置，共40个位置；去重20个query-track对、交集20，不重复当40项待判。 |
| 部分重叠且4条完整已判 | whole宏0.56–0.60、1未知；segment宏0.56–0.64、2未知；各4条完整，整体exact仍null；跨模式交集1/并集2/位置3。 |
| 全部返回项已判 | whole exact宏0.52，segment 0.60；未排除任何query，new confirmed source hits各10。 |
| 返回项全是显式0/1 | 两mode exact宏0，未知0/完整query5；不将0/1误作null或从宏中移除。 |

只读核对A公开035聚合：23/25及24/25对应0.92/0.96下限，未知2/1对应1.00上限、exact null，公开数字自洽。**没有复算A私有排名/三原包/真实向量或EOF**。A037后来得到开发whole1.00/segment0.96属于后续接收记录，不改写035历史区间或捆绑批准。

## 保留的阻塞与失败

原生discovery的缺依赖输出完整保留`research-tests.log`；37 shim测试单独保存，不将原入口改记passed。独立脚本首次在任何fixture/断言执行前因B局部变量`fixture`遮蔽同名生成函数而exit1，0断言；仅更正忽略的harness函数名，原日志/空结果保留为`independent-attempt1.*`。最终45及后续4断言不与首次0或原生discovery重复累计。该准备错误不是产品缺陷。

另有有意注入的dirty Git、错checkpoint、旧20后decoder失败、重名成功/失败输出、缺11pins和CLI输出保护拒绝，均按预期记录，不冒充真实服务故障或模型运行。NumPy2对既有`np.core`访问的弃用提示保持；未改旧依赖代码。本轮通过后没有再重复相关套件或无关Java/前端构建/浏览器。

## 证据与版本

全工件、方法源码及环境清单在B忽略目录`verified-evidence.json`，SHA256 **`84fce408abcfe872dc1b5ad014e262101cbf354a0022e5f0d90cb603b927d4ab`**。原始数据/向量/判断和忽略脚本不提交，不要求A拥有B绝对路径或声称A已重算。

| 工件 | SHA256 |
|---|---|
| 原生blocked日志 | `38c72bddd735160b35927839b647ba42c555d9b635d2563935bc2cf0d2c0f0da` |
| 原生36日志 | `7fe24b3e56a383dab88b9fd89909e10a7a167ddfd7bd9b6cb0b017c1dd3137f7` |
| 显式shim37日志 | `0e13598b0d11b30101a03999f70f7d3a4e5c3f84e56fd19c7935a79b486ba256` |
| 独立45断言/命令结果 | `41dee5d1544d8e0d5ef620de519725d32a1014ea8cc4ec7f16858541696dd970` |
| 另4手算断言结果 | `f3ba721635820338695e1264eef940585243b95dbd69e73fe8d98b482a3379e5` |
| N1三入口复现 | `6ec2eca558e24a0c0ad1f18cc0681d0fafea30be278bd473e7908b897fde9d1c` |
| 假checkpoint driver report | `3e43c32f7d4c458ad1a22880fbc05f24a7cd9bc613b5ce57b4c499dc6caa5869` |
| 含未知 / 全已判评估 | `16c42bfc095d3e519fca0749c005e4178875663a02c0689bfa277ef42c666312` / `b67b97ffe2efd8545be4e06e720c1f8ae3aa4973da458d138ffbb510ce26c481` |
| 部分重叠 / 零相关评估 | `7045b7a0df35fd8826741f6668d954b2edc17b74f8b027610cee294a981c450b` / `c022a0c4957dbac33263b89feb88c1454b59f8b25feb1b21cf3fb8544dc18f02` |

三B dataset：E1 `ec8ebc69236a11dbd35c0be67875ebd6846db41c74b743c56b6ba900d99f8fe9`；diagnostic `0a369aa4e7d097aad8ea9aab07c45ae9a90f2a633d8e0072810d125658a5d2f1`；source `15916c42b4ffdb57df94e902a498e6394cbb570a3a1cb9d67608379eae49e466`。模型/索引：只有测试sentinel/合成向量，官方模型未加载或更改；decoder版本仅验证控制逻辑`soundfile-read-out-65536-actual-eof-v1`。

六源码SHA分别为：research_corpus `58219780f73d94914fff4be1d1aaf48e5fdc5a2352fb47dbebe1347ed2794a79`；其测试`4eb453e633aa9b02041c3a257678e5fd7122eaabc6a982f2c13b7c9671e6e1e3`；research_probe `dc3253913e1f0bbb461aba5190e8c3c7b5f39cb05b9d7ca6d8e0e508bc233750`；其测试`f66695a6e06819b729f5d9d92955895254173e2da1c58e5baa7f779a8cf0d245`；research_evaluate `83a671fbd1995ae13e8e9613dbfcb388f6549015ef5346d474961d286fb7c13e`；其测试`c1d2b94e0e6fefcb422c44dfd7693830fc26cd2211947e60a82559b8b2a0645d`。

## 交接与剩余范围

实际完成：本卡三工具/三测试/E8审核、36原生与37显式边界测试、49独立断言/观察、真实标准库CLI和N1复现。接口变化：无。未完成：B原生完整依赖环境/真实模型与解码验收未执行；N1由A按范围安排修复，B未占用产品文件。没有真实新人工标签/许可/检索质量/held-out/P95/定位/显著性或discovery-v0结论。

下一步A接收本限定批准并处理N1或分配有界增量复核；036 UI/补判包、037接收、038方案、039收集器和040未来工作均不随本卡关闭。已有A141判断、后端/网页/备份与模型/cache只读保持，main未推送或合并。

已授权GitHub接口顺序发布任务source再B feed，**非原子**；最终SHA与实际可读状态由handoff及回读给出，发布不等于A接收。交付后两报告占用释放，无服务/端口占用或后台轮询；原生blocked与N1没有被改写成全项目通过。
