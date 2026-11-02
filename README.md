# SONORA · Music Discovery Platform

## 当前开发入口：Sonora 副本

用户已确认 MUS-018 设计。MUS-019 将新版界面接入真正的 Vue 应用，后续前端开发使用 **`Music-Sonora` 工作目录；当前开发分支 `codex/MUS-060-centered-residual-training`**。原 `Music-Resource-Management-System` 目录停留在 `design/MUS-018-ui-preview@f3b0da1`，其旧 `web/` 与原 5173 页面作为保留版，不在两个目录同时修改前端。

新版本机入口：**http://127.0.0.1:5175/music**。它通过代理连接现有 A 后端 8080，使用原登录账号和已有曲库；本次没有复制或迁移数据库，也没有启动另一个 Java 服务。原服务仍是 MUS-014 运行版本，不把较新源码当作已运行版本。

在本副本 `web/` 目录开发：

```sh
VITE_DEV_PORT=5175 VITE_PROXY_TARGET=http://127.0.0.1:8080 npm run dev
```

稳定浏览构建版本（先停止占用 5175 的本副本进程）：

```sh
npm run build
VITE_DEV_PORT=5175 VITE_PROXY_TARGET=http://127.0.0.1:8080 npm run preview -- --host 127.0.0.1 --port 5175 --strictPort
```

使用 `.nvmrc` 的 Node 22；本机工具包位于相邻 `.music-tools/node-v22.23.3-darwin-arm64/bin`。首次安装仍用当前 lockfile 的 `npm ci`，不升级依赖。备份精确源码为 `f3b0da1e97113d28c81aa49be61c5cbcc49eebce`，此提交内的 `web/` 就是原版；新分支也保留该祖先。

新 `/music` 是封面曲库；旧完整资源管理在 `/manage/music`；上传、分类、标签、回收站、个人资料及管理员入口沿用原组件和权限。收藏与播放历史仅保存在本浏览器，按账号 ID 分隔，未实现跨设备同步。播放器使用现有 JWT 媒体 helper 获取音频，页面切换继续播放；退出或换账号清理音频和队列。曲库按后端每页 20 首加载，封面区域分批展开；风格与排序只作用于已加载曲目，页面会提示未全部加载的情况。

验证与边界见 [MUS-019](docs/verification/MUS-019.md)。下文原有后端/双账号基线文档仍保留，不意味着本副本已配置了第二套数据库。


保留 Java / MySQL / Vue 管理系统，增量开发多模态音乐检索与片段定位。

**当前面向浏览器的多模态检索尚未实现。** MUS-022已补上20首真实MP3的离线解码、933片段及固定CLAP候选排序；MUS-028/031累计接收118条探索人工判断，五条描述各完成全20曲判断，MUS-029已完成首轮候选池探索比较。正式模型效果验收及线上检索接口仍未完成。已建立MUS-001本地功能基线；模型效果、正式索引、独立研究测试集和性能仍需验证。2,000 首、约 70,000 片段、120 查询、300ms P95 和 10% 提升均不是现有成果。

MUS-035已用同一固定CLAP重新处理40首，生成1557片段/40整曲向量和8条文字查询的两模式离线排名。五条目标描述中，两模式均将新增20首各自排进前5；整曲25位置已知相关23/未判2，片段24/未判1，对应P@5范围0.92–1.00/0.96–1.00，不能当精确总体指标或独立测试提升。原20向量重编码差为0，138判断/旧run/空白包保留；新top5跨模式尚有3个不同组合待判。新来源实际EOF读取也纠正了历史头部估计时长（原记录保留），详见[MUS-035](docs/verification/MUS-035.md)。当前仍是私有离线结果，网页多模态检索/共享线上索引尚未实现。

MUS-036已把这3对准备为独立补判包：钢琴1、爵士2，3首不同音乐，实际EOF时间/新指纹/全null/空模型建议；现有试听页可导入、播放和导出，已有138保留。188 Python/77 Node/build及18真实浏览器断言通过，等待用户判断后再更新精确开发指标。本轮接收B033限定批准并明确派发035独立工具审核，不外推036。见[MUS-036](docs/verification/MUS-036.md)。

MUS-037已接收3/3补判并独立复算，累计141条；固定五描述的新40曲整曲top5相关25/25、片段24/25，精确宏P@5=1.00/0.96，剩余top5未知0。原20同五描述为0.16/0.20；原035区间/029八描述指标及四原包保留，不重排或训练。全8×40仍有179对未知，定向开发结果不等于独立测试；后续独立评测设计见MUS-038，尚未执行测试。见[MUS-037](docs/verification/MUS-037.md)。

MUS-038已冻结首次独立小样本评测方案：旧40曲/141判断继续作为development，复用原20×五描述完整100对预检；计划新增20曲×8条新英文描述、全160对盲于模型的人工判断，分四批各40。比较两个固定CLAP检查点的整曲/片段四组，加标题词面对照；先冻结来源范围、描述、作者作品隔离和运行配置，全部排名保存后才解封标签。本轮仅设计与官方元数据核查，新音乐/描述正文/权重下载/新标注包/独立run实际均0，旧页面尚不支持新格式。见[评测方案](docs/evaluation/MUS-038-protocol.md)及[MUS-038验证](docs/verification/MUS-038.md)。

MUS-039已完成G1独立来源/描述冻结：20条新录音（16 FMA、4 MusicBox）、9个保守创作者群、20个作品群，固定hash队列选取并实际EOF/独立复核通过；8条全新英文描述有中文可听线索和评分规则。初框容量仅19，故在采样方未读旧描述时显式另版、重新编写8条；先冻结完整语料再打开新描述，没有按模型/相关度选样。26项新单测通过。新20仍source-only，未导入数据库、未生成新160项标注包或模型结果，页面暂不可导入；已导入40首/141旧判断保持。下一步040做真实身份导入、新test格式/runner与安全模型预检，见[MUS-039验证](docs/verification/MUS-039.md)和[冻结描述](docs/evaluation/MUS-039-queries-v2.json)。原版/UI/main保持。

MUS-040第一检查点已完成：接收B035限定批准并修复极端umask输出权限；第二个预注册CLAP权重正常TLS/SHA核验、严格加载通过，旧20首重新处理为933片段/5文本、512维，96相关测试及分脚本排名复算通过。复用旧100开发判断，整曲P@5由原A0.16到B0.20，仅多1个相关位置；片段均0.20，不是独立测试提升或模型切换。新20仍未导入，160项新包/G2/test run均0；040余下要完成真实身份/新test适配与冻结。N1另派准确de255c7增量复核，不外推B批准；见[MUS-040](docs/verification/MUS-040.md)。

MUS-040第二检查点已真实导入新20首：普通账号自有资源60首（开发40/独立测试20），新20全部pending、真实Java身份/Range/完整SHA通过，CLI重跑0新增、42核心文件保持；额外20匿名请求均401。78相关检查通过，G1原件/新描述/141旧标注/双权重与索引保持；新20尚未编码进测试索引，160项包/G2未生成。见[导入验证](docs/verification/MUS-040-phase02.md)。

MUS-040第三检查点已完成G2运行冻结、四批独立标注包和五组新测试排名：20首×8新描述共160项，四批各40，全部初始判断为空、无模型提示，页面有中文可听线索和0–3说明。A/B各755片段/20整曲/8文本，另标题词面对照，共40个全20排名；源/权重/源码/依赖先冻结，排名全部保存后才交标注。238音频Python/78来源导入/84 Node/build及20首真实浏览器播放通过，原141/备份/旧run保持。当前等待用户标注，先交完成回执、完整判断自存至通知；未打开新qrels或计算正式质量。第1批已在本机试听页空白载入，见[第三检查点验证](docs/verification/MUS-040-phase03.md)。

MUS-041已按用户要求调整后续数据路线：既有标注作为训练/开发主来源，人工仅保留有界抽检和项目验收，当前四批仍照常完成。已核MTG-Jamendo固定版本55,609条标签metadata，官方split-0 train32,859/validation11,101/test11,565且作者ID无交叉，原开发20 Jamendo有9首重叠须排除；SDD可作外部人写caption评测候选，但也含已用作者。已比较MusicCaps/MusicBench/生成caption的角色与许可，实际仅下载约31.7MB文档/metadata，未取音频或训练。首选MTG仅按非商业研究评估，不能当商用授权；当前160与五配置/G5不改，新训练不能据已看test调参后仍称盲测。详见[现成标注路线](docs/evaluation/MUS-041-labeled-data.md)。

MUS-042已接收四批原始完整判断并完成首次独立小样本比较：四回执SHA全部相符、160/160合法，5组原排名不变、单次解封且独立分脚本复算一致。全8描述宏P@5：A整曲0.125、A片段0.175、B整曲0.075、B片段0.125、标题0.075；5描述没有2/3分匹配，全样本理想上限0.225。B相对A两模式均低5个百分点，无模型切换/训练；nDCG及逐query/限制见[MUS-042](docs/verification/MUS-042.md)。这不是总体质量验收或线上检索，旧开发指标不能与新样本直接算提升；用户已完成四批，后续按041现成标注路线而非追加大量全矩阵标注。

MUS-043已建立MTG现成标签adapter与20首真实音频预检：固定官方split-0/183标签、原60及SDD已知组排除后得到7,577个metadata候选，固定首批20首/20作者/49标签，20/20官方逐曲SHA/实际EOF/48k mono与1,004窗口验证通过。66相关检查及独立分脚本复算通过；实际音频约65.4MB，官方单曲获取、未拉tar。只在私有研究目录，未导入Java或训练，未声称1–2k语料就绪/提升；原模型/141+160/五排名/原版保持，详见[MUS-043](docs/verification/MUS-043.md)。

MUS-044已固定train1,000/validation200/reserved-test200的metadata分组计划（音频尚未下载），并首次真实拟合轻量适配层：复用043的20首、固定60窗口/183标签prototype，冻结原CLAP，只以已知正tag均值训练512×512 identity-prior ridge，单lambda100/无超参搜索。目标27.808→26.469，但训练已知tag Recall@5保持28.13%，没有验证/测试或检索提升结论；原模型不切换。32相关检查、独立primal参数复算和旧数据保护通过，详见[MUS-044](docs/verification/MUS-044.md)。

MUS-045已接收B的044计划审查建议并完成140首真实研究音频（100训练/20标签验证/20人写描述开发）与三组适配比较；20开发录音对应24条既有描述，无新增人工包。原模型整曲配对R@1为54%，三候选最好仍54%；较强适配标签Recall@5由15.1%到22.1%，却降低描述检索，故保留原模型、不启动千首扩训。20候选池原模型R@5已100%，门槛出现天花板，后续需另预注册更有区分度的开发池并检查监督目标，不能凭此宣称泛化无效或改实验造收益。42相关检查、独立参数/排名复算及真实零额外下载恢复通过；新保留测试文本/音频/模型输入/评分均0。研究数据未导入页面曲库，原版/UI/main保持，见[MUS-045](docs/verification/MUS-045.md)。

MUS-046已统一现有140候选的首120秒视图，复用原24描述/三W完成扩大池诊断，无新拟合或音频下载。原模型整曲R1/R5/MRR为31%/49%/0.4208，原alpha0.1为36%/60%/0.4658；主MRR差的95%开发区间包含零，继续保留identity，不据此扩训或部署。54检查和独立两池/两模式指标区间复算通过，原20控制指标复现，保留测试未用。B035权限N1准确限定批准已接收关闭，046工具的合成/静态限定批准也已接收，未外推为模型质量验收。见[MUS-046](docs/verification/MUS-046.md)。

MUS-047已建立独立设备校准：固定3训练曲/9窗/6tag，CPU参考与本机Apple MPS通过；9窗热SDK编码中位耗时656.31→240.35ms，约2.73倍，最大向量差5.07e-7、两模式各18稳定次序无翻转。只是小批次编码证据，不是训练/P95；CUDA本机不可用明确blocked，无fallback。66相关检查/独立复算/重复输出保护通过，原模型和生产缓存不切换、不租卡/上传/新训练，保留测试未用；新047工具另派限定审核。见[MUS-047](docs/verification/MUS-047.md)。

MUS-048已完成140首MPS双视图缓存：100训练/20标签验证用整曲实际EOF，140检索用首120秒，780用途引用按起点去重为624窗，另183tag/24dev文本。CPU全量数值及四旧模型两池两模式16组宏R1/R5/MRR复现，前5集合和顺序保持；只有一个查询第111/112名近并列交换，未隐去。76检查/独立复算/实际consumer/重复保护通过，新ready缓存按device/model/view显式读取，CPU可读训练100/验证20且不加载模型/不返回dev文字。没有新训练/下载/保留test/旧缓存替换或部署，B047原审核卡保持，048独立审核待安排，见[MUS-048](docs/verification/MUS-048.md)。

MUS-049已复用MPS特征完成一次CPU正标签逐项分数训练：100首/335已知正tag、唯一alpha.01，拟合约0.67秒。loss下降，但达到200步上限未满足收敛阈值；140候选主整曲MRR由identity0.4208到新W0.4203，未改善，也低于旧alpha0.1的0.4658，继续保留原模型。86检查/独立目标梯度与全部检索指标复算/实际重复保护通过；无追加调参、保留test、下载或部署。下一轮优先审查现成文本—音乐描述训练来源及隔离容量，再立方案；B047原卡保持，原版/UI/main不变。见[MUS-049](docs/verification/MUS-049.md)。

MUS-050已完成描述训练来源的固定metadata实核：MusicBench52,768训练行实际5,079来源视频ID，TestA/B为同400音频；自身train/test ID无交叉，但train含2,631个MusicCaps AudioSet-eval来源，不能混作无重叠测试。2,448个非eval/未增强路径仅是metadata候选框，缺音乐作者/作品关系与就绪音频；JamendoMax两小样本1,944行/494ID且有许可冲突，完整生成caption尚未取。下一步优先审计生成caption与现有研究训练音频的白名单覆盖/区间/权限，再决定训练；本轮只取约93MiB metadata，新fit/音频0，原模型/SDD评测/备份/UI/main保持。见[MUS-050](docs/verification/MUS-050.md)。

MUS-051已完整流式核JamendoMax固定caption文件787MB/SHA：1,812,352行/360,740来源ID，现100train/20val匹配287行；按15–30秒/实际EOF固定规则保留270区间，覆盖train49首/246段、val8首/24段。15短尾和2个约2ms越EOF原样隔离，无重复/冲突/重叠；只保存白名单原行，不落全库正文。98检查/独立原行重建/两种实际重跑保护通过；当前是生成caption候选，逐曲权限与波形版本/区间对齐待核，尚未训练。下一步先做匹配57来源的有界预检，原模型/SDD评测/备份/UI/main保持，见[MUS-051](docs/verification/MUS-051.md)。

MUS-052已完成57匹配来源逐曲metadata与参考预检：固定53文件/Git blob和长度全核，按全行许可/下载/身份/时长规则保留44来源232区间（train37首209段、val7首23段），13来源因许可规则/作品名差异隔离。固定3个已有训练来源参考MP3、9个中心10秒anchor均通过，NCC0.99804–0.99994、8k网格峰lag0、实际时长差0；不外推teacher确切缓存/全44或语义质量。110检查/独立FFT与直接点积/真实重跑保护通过，下一步可构建对应区间特征再另定训练，不重做本轮预检。参考仅同ID新快照，无新曲库/fit/模型切换，备份/UI/main保持，见[MUS-052](docs/verification/MUS-052.md)。

新会话按顺序阅读 [AGENTS](AGENTS.md) → 本文件 → [PROJECT](docs/PROJECT.md) → [CONTRACTS](docs/CONTRACTS.md) → [STATUS](docs/STATUS.md)。当前集成负责人为账号 A；由 A 串行维护 STATUS。

两账号固定交接见 [collaboration/README.md](docs/collaboration/README.md)：开始时 `python3 scripts/collab.py sync --account a`，结束提交后 `python3 scripts/collab.py publish --account a`，B 用 `b`。采用每账号独立交接分支，保留任务分支 / 精确 SHA，不自动合并。A/B 远端 feed 已可互读；早期A连接阻塞为历史；后续原生Git原子publish/sync已有成功记录。每次以本轮结果为准，发布不等于对方接收或审核。

## 代码与验证边界

| 路径 | 当前能力 |
|---|---|
| `music/` | Java 17、Spring Boot 3.4.4、MyBatis Plus 3.5.5 与部分 JPA；MySQL、Druid、Caffeine、JWT、mp3agic |
| `web/` | Vue 3、Pinia、Axios、Element Plus、Vite 6；ES modules JavaScript |
| `music/src/main/resources/db/baseline/` | MUS-001 的空开发库初始化；历史同级 SQL 不作为顺序迁移 |
| `scripts/dev.py` | 生成独立 slot 配置；拒绝覆盖已有配置；只初始化空开发库 |
| `scripts/smoke.py` | 合成 MP3 的旧业务 API 流程验证；不是检索评测或听感验证 |
| `docs/` | 当前事实、建议契约、任务边界与交接证据 |
| `services/audio-search/` | MUS-002合成探针与MUS-022真实小语料解码/候选排序；非线上检索服务 |

JWT 账户、分类标签、筛选、分片上传、元数据、审核、播放下载与回收站有源码。MUS-001 实跑覆盖注册登录、标签及分类筛选、部分上传续传请求、合并、MP3 元数据、Range 媒体响应、软删除及恢复。未覆盖全部管理 / 审核 / 邮件分支、浏览器人工试听或重启后的上传恢复。

不能将评论、点赞、收藏、播放历史服务端持久化、完整 Swagger 或生产部署当作已验证能力。

## 一次启动并验收前后端

在普通本地终端、自己的独立 checkout 根目录运行 `python3 scripts/baseline.py --slot a --keep-running`；B 在另一 checkout 用 b。原生 MySQL、Java / Vue、两条 smoke 流程和私有结果文件由入口串联。已有库不清空。用户已在普通 macOS 终端跑通 A/B 两套独立工作目录：各 107 项 Java 测试、前端 build、直连 / 代理各 13 项通过；受管终端自身仍限制回环，不代表限制已解除。详见 [MUS-010 验证与启动步骤](docs/verification/MUS-010.md)。

## 开发启动

要求：JDK 17、Node **22.23.3**（[.nvmrc](.nvmrc)，本轮 npm 10.9.9）、Python 3.9+、MySQL **8.0.41**。Maven wrapper 指向 3.9.9。首次下载依赖需要联网。

以下从仓库根目录执行，适用于自己的独立 clone：

```bash
python3 scripts/dev.py setup --slot a
. .local/a/env.sh
# 有 Docker Compose v2 时启动独立 MySQL；本轮仅原生 MySQL 路线实跑。
docker compose --env-file .local/a/compose.env -p music-a -f compose.dev.yml up -d --wait
python3 scripts/dev.py init-db --slot a
cd music
sh ./mvnw -B -ntp test
sh ./mvnw spring-boot:run
```

另一个终端：

```bash
. .local/a/env.sh
cd web
npm ci
npm run dev
```

再用一个终端验证后端及开发代理：

```bash
python3 scripts/smoke.py --slot a
python3 scripts/smoke.py --slot a --via-proxy
```

原生 MySQL、slot B、启动顺序、配置字段及限制见 [development.md](docs/development.md)。未安装 Docker 的机器不能直接运行上面的 Compose 命令；不能把配置存在解释为容器路线已验收。

## 配置与安全边界

- `application-local.yml` 已提交，必须显式启用 local profile；setup 生成的 shell 环境会启用它。`application.yml` 仍不提交，已有私有配置不会被覆盖。
- local 后端只绑定 127.0.0.1，context path 为 `/api`。Vite 将相对 `/api` 原样转发，读取 `VITE_PROXY_TARGET`；`VITE_DEV_PORT` 冲突即失败。
- 配置、密钥、上传、数据库和索引放在被 ignore 的 `.local/<slot>/`。每账号独立 clone，不能共享写入数据库、上传或索引。
- `VITE_API_BASE_URL` 仅是旧头像 helper 的非空开关；该 helper 实际返回相对 `/api/uploads/...`。它不控制 Axios baseURL 或代理。
- **媒体权限本机实跑通过**：MUS-011 已实现三入口 / ZIP 授权与 no-store、受控头像及前端 JWT；本机 A/B 隔离环境各通过 144 项真实媒体权限矩阵，直连 / 代理匿名入口均为 401。B 账号独立审核待完成。MUS-012 已加入上传所有权及头像绑定检查，308 项 Java / 22 项 Python 测试通过；两套本机新服务各通过 65 项真实上传权限检查和 144 项媒体矩阵，公开 discovery 继续阻断。历史匿名 200 证据及当前验收边界见 [MUS-011](docs/verification/MUS-011.md)。
- 初始化 SQL 仅适用于空开发库。没有提供既有数据库迁移，不向已有库运行历史 dump。

## 本轮验证

| 检查 | 2026-10-19 结果 |
|---|---|
| `npm ci`、`npm run build` | 通过，保留 lockfile；bundle >500kB 为非阻塞警告 |
| `sh ./mvnw -B -ntp test` | 9 类、89 tests，0 failures / errors / skipped |
| 原生 MySQL 空库初始化与 local 启动 | 通过；11 表；非空库重复初始化被拒绝 |
| 后端直连 / Vite 代理 smoke | 各 13 项功能检查通过；Range 实际返回 206 |
| 两 slot 配置 / strictPort | 配置分离；B 为 8081 / 5174 / 3308；端口冲突拒绝启动 |
| CLAP 文本 / 音频 CPU 编码 | 固定音乐 checkpoint 已通过合成输入可行性检查；实际 512 维；9 项预处理测试通过 |
| Compose、真实邮件、全部浏览器交互、检索质量 | 未验证 |

默认 Surefire 已从仅 `*ServiceImplTest` 改为全部 `*Test.java`，并要求非空选择。可用 `-Dtest='*Test'` 对照。前端无 `test` / `lint` / `typecheck` script。

原始源码默认测试实跑 75 tests 有 3 errors；修正失效 fixture / mock 后才获得上述结果。旧会话 Maven 网络阻塞不再描述为本轮状态。详情见 [验证记录](docs/verification/MUS-001.md)。

源码仍有非阻塞 Druid 1.2.11 POM / JSqlParser count 优化警告。MUS-009 本地任务已修复分片重复写库和哈希未校验，保留旧接口；当前全量 Java 107 tests 通过，真实数据库 / 并发 / 进程重启验收因环境阻塞待补，不属于上表历史 89 项证据。见 [上传完整性验证](docs/verification/MUS-009.md) 与 [STATUS](docs/STATUS.md)。

MUS-002 的准确 checkpoint、实际环境与限制见 [model-spike.md](docs/model-spike.md)。真实音乐语料与效果验收仍缺，discovery-v0 尚未冻结。


**独立审核补充：** B在d7c9faa发现旧硬删除、管理员createUser头像和迁移结构保护缺口。MUS-013源码已修复，Java317 / Python28通过；旧服务中的R1/R2已复现，两套本机修复后HTTP11项及独立临时库8项均已通过，B增量复核待完成。详见 [MUS-013](docs/verification/MUS-013.md)，公开服务仍保持阻断。

## MUS-012 上传所有权升级

新上传按当前数据库账号保存 `owner_user_id`。文件列表、MD5 秒传 / 续传、详情、分片 / 合并 / 删除与元数据绑定只处理自己的上传；不能登记他人的图片为头像。已有音乐的媒体读取继续按审核状态控制。

V001 保留不变，V002 为加列与索引迁移。旧上传保留 NULL owner 并隔离，不能自动认领；已有关联音乐仍按媒体策略读取。需要继续旧上传时重新上传新记录。删除自有未引用上传只做逻辑删除，物理清理待后续任务；音乐 / 头像引用会阻止删除。

2026-10-19 两套本机环境已重启并完成验收；以后需要启动时，在各自 checkout 中运行：

```bash
# A checkout
python3 scripts/baseline.py --slot a --migrate-upload-ownership --keep-running
```

```bash
# 本机独立 B checkout
python3 scripts/baseline.py --slot b --migrate-upload-ownership --keep-running
```

该迁移选项只接受隔离开发配置，已升级的库重复运行不会回填 owner 或重建表；空库自动初始化到 V002。新 baseline 会执行原功能与媒体矩阵，再执行上传所有权真实回归。报告与限制见 [MUS-012](docs/verification/MUS-012.md)。两个本机槽不代表 B 账号已独立审核。


MUS-014 基线新增18项真实上传故障检查，并自动完成“部分上传 → 停止本次后端 → 新后端就绪 → 续传与并发合并”检查。旧基线若仍在运行，先在各自终端按 Ctrl+C，再用上述命令启动。无需手动执行prepare/resume，也无需复制私有状态；失败状态会保留以便定位，不自动覆盖。当前修复的317 Java / 45 Python通过；2026-10-19 23:18两套普通终端基线已通过真实并发计数回归与跨JVM续传（各18故障、prepare5、resume11），服务保持运行，无需再次重启。见 [MUS-014](docs/verification/MUS-014.md)。


MUS-014已收到B独立复核的范围内批准及其真库/跨JVM运行补证；详见[接收记录](docs/verification/MUS-014-B-acceptance.json)。MUS-015进一步补上同值头像请求重新校验，Java320通过，新版本真实运行尚未验收；当前服务仍保持已验收的MUS-014版本，见[MUS-015](docs/verification/MUS-015.md)。


## 演示音乐

A环境已导入20首Jamendo CC BY完整音乐。打开 http://127.0.0.1:5173/demo-catalog ，侧栏Demo Catalog可查看作者、来源和许可，并进入Music播放。另列Post Malone/Drake各10条资料与官方链接，无其完整音频。本机普通演示账号凭据在忽略文件.local/a/music-catalog/demo-account.json；本次内置浏览器已登录。

重复导入验证：`python3 scripts/import_demo_music.py --slot a --count 20`。Client ID、账号和音频缓存仅存.local，新环境需自己的配置；不把Git清单当作已拥有本地音频。详见[导入验收](docs/verification/MUS-016.md)。


管理员用户编辑的MUS-017候选约定：头像省略或null保持，空字符串清空，非空路径校验；按提交字段局部写入，避免旧头像/安全字段回写。Java323通过，尚待新版本真库验收；现有服务未重启。详见[MUS-017](docs/verification/MUS-017.md)。

MUS-020 已接收B的两项request_changes并作最小修复：手机长标题列表明确允许信息列收缩；管理员按用户名/邮箱查音乐改至 `/manage/music`。复核与运行边界见 [MUS-020](docs/verification/MUS-020.md)，新B增量卡按准确实现SHA派发。


MUS-017的B限定批准已正式接收，C1关闭；E1空对象与E2其他用户写入口风险由MUS-021继续处理。MUS-021源码使用独立管理员输入DTO及六入口专属写列，默认/显式Java测试各332通过；B限定批准已接收，其独立默认332 Java和24项隔离真库增量通过。现有演示后端仍MUS-014，本轮不重启服务或迁移数据。见 [MUS-021](docs/verification/MUS-021.md)。


MUS-022离线实跑：20首MP3、933候选片段、8英文文字和3库内参考完成512维编码及整曲/片段精确排序；23项测试和工件校验通过。51个探索标注对仍全null，未计算质量或P95、不冻结discovery-v0，生成向量仅ignore目录。命令/证据/限制见 [MUS-022](docs/verification/MUS-022.md)。现有网页/演示后端与原版备份保留。


MUS-016首次B审核已返回request_changes。MUS-023源码补上pending/confirmed账号恢复、缓存证明完整绑定与canonical公开来源/目录链接；62 Python/8链接检查及前端构建通过，新的真HTTP/SQL增量已获B限定批准。原版备份/既有20首证明及MUS-022结果保留，没有重跑真实A导入或升级后端。见 [MUS-023](docs/verification/MUS-023.md)。

MUS-023已接收B限定批准，关闭MUS-016对应R1/R2/条件性R3；B真实本地HTTP/SQL补证与提供方替身边界见[接收记录](docs/verification/MUS-023-B-acceptance.json)。MUS-024已实现本地探索标注包生成/校验，17新增检查及全离线40项通过，实际8查询51对全null；B工具限定批准已接收，原UI布局与演示后端保持。使用步骤见[MUS-024](docs/verification/MUS-024.md)。

MUS-025新增[本机试听审阅入口](http://127.0.0.1:5175/research/review)：用标注包归属账号导入`.local/a/mus024/review-pack.json`，现有JWT媒体与完整SHA/字节验证后试听片段，人工评分/区间、分账号本机草稿及JSON导出。21项helper检查/build和本机浏览器增量通过，B原范围限定批准已接收，新控制修复见MUS-026；真实51条仍全null，无质量结论。原Sonora布局/管理页/后端保留，使用步骤与限制见[MUS-025](docs/verification/MUS-025.md)。

MUS-026修复试听审阅的底栏与进度：整曲/片段现在同步显示曲名、歌手与实际位置，底栏和页内进度条控制同一已验证音频；支持暂停/继续，片段拖动限原范围并在终点停止。31检查/build及真实桌面/手机增量通过，B限定批准已接收。原队列、标注/草稿、媒体校验与备份保留，见[MUS-026](docs/verification/MUS-026.md)。已有页面先导出当前工作再刷新，重新导入原包或明确恢复本机草稿。

MUS-027将必填匿名标注代号移到相关度选项上方，空值/格式错误就近提示；填写合法代号后可勾选评分，填写本身不自动判断。8包检查/build、17浏览器断言与合成导出CLI通过，B增量待复核。先导出当前工作再刷新，原包/真实标注不改；见[MUS-027](docs/verification/MUS-027.md)。

MUS-028接收用户完成的首轮相关度标注：8查询/20曲/51对全部已判，0/1/2/3=19/13/9/10；固定运行校验通过，原字节副本仅本机私有归档，原空白包保留。无人工定位区间，未计算模型质量/held-out指标；见[MUS-028接收汇总](docs/verification/MUS-028.md)。

MUS-029完成两模式首次探索比较：原8描述上整曲/片段P@5=0.40/0.45，pooled nDCG@5=0.8299/0.9062，38检查和固定输入实跑通过。只适用于已判候选池，非held-out/全库Recall或定位精度，不调整阈值/训练；原标注/UI/后端保持。方法、低分诊断及未判109对边界见[MUS-029](docs/verification/MUS-029.md)。

MUS-030已准备独立补充诊断包`.local/a/mus030/diagnostic-review-pack.json`：五条较弱描述共67个新组合、18首不同音乐，全null；原51判断保留。现有试听页支持导入/手动定位/独立草稿，不显示模型建议；53 Python/39 Node/build及真实浏览器增量通过。使用步骤见[MUS-030](docs/verification/MUS-030.md)，完成后导出新JSON交回，不重复旧组合。

MUS-031已接收并校验补充67/67，原字节私有归档，原51与两份空白包保持。五条描述×20曲共100对已完整判断；每条仅1–2首>=2，补集新增2个原候选联合池漏选的相关组合。结果同时支持当前素材适配稀少和存在漏选，不能外推所有音乐类型或正式模型效果。总计118/160已知，其他三描述42对仍未知；详见[MUS-031接收与诊断](docs/verification/MUS-031.md)。后续应针对具体描述补充合适素材并建立独立测试版本，不用当前标注调参后宣称正式提升。

MUS-032已按五描述各4首，从作者Incompetech官网独立收集20首CC BY4.0来源候选（约115MB、实测53分9.548秒），20/20完整MP3解码和SHA/证明匹配，18项合成保护检查通过；原20曲内容无重复。新增仅source-only开发批次，不等于网页已有40首或20首已被人评为相关；单作者偏差与6首官网时长差异保留，按实际解码时长用于后续定位。原118判断/公开catalog/旧run/原版保持。清单、命令及后续真实ID导入边界见[MUS-032](docs/verification/MUS-032.md)。


MUS-053实际完成：干净716b3fcea1902a54fe17a5e4b64db78334ddb28a首次CLI exit0，固定44录音232生成caption区间构建696唯一10秒窗及232音频/文字向量，512维、原PCM/边界与输入源码环境复核passed；train37录音/33组件/209段，validation7/7/23，每录音等权，两个consumer只返回本split且不加载模型/原caption。CPU3训练区间9窗/3文本数值抽检最大差3.01e-7、独立9真实波形重解逐点相同；124相关检查、独立所有行/窗口/权重/聚合/token复算、真实重复输出拒绝和旧045–052/模型/cache/备份保护通过。

重要限制：232原描述17–178token，124条超过77并按冻结SDK规则截断（train110/209、val14/23）；未事后筛除或改写。CPU三文本为49/76/64token均未截断，此抽检不证明所有长caption CPU/MPS一致。新cache只ready_for_bounded_pilot，训练方案未冻结、无fit或质量提升结论。下阶段先明确77token截断对训练目标的边界，再另预注册一次小训练，不能按已看dev继续搜参。原identity/141+160/SDD/保留test/UI/Java/DB/main/B047卡保持，不租卡/下载/新增人工全矩阵。见[验证](docs/verification/MUS-053.md)。


MUS-054已实际完成首轮文本—音频配对适配训练：干净4afd75cd2d75ce1aaab8e08aabac21c16a7f6270首次唯一fit，37录音/33作者组件/209段、录音等权/固定alpha1的512×512 identity-prior ridge，CPU闭式拟合13.736ms（复用已生成GPU特征，无CLAP全量微调/重编码），解析残差1.03e-16、objective1.313145→1.148083。先存W和fit收据后才分析7录音23段验证及旧20/140池24个人写dev query；共享NPZ为完整性会物理加载val数组，但只有train209输入求解，不作val选择。

主140整曲宏MRR identity0.420808→新0.447163，配对差+.026355的95%描述性区间[-.006304,.082660]仍含零；R1 .31→.37/R5 .49保持。20池整曲MRR .708333→.677500下降，validation23精确区间宏MRR .390929→.427504也只是7录音生成标签；不宣称稳定/总体质量提升，保留identity。历史旧alpha.1同主指标.465839仍高于新W，仅说明历史上下文、非本轮新增候选或调参。133检查/独立primal与全部排名bootstrap复算/同目录及换目录单fit拒绝通过，旧045–053/原141+160/权重/cache/备份/UI/DB/main/B047卡保持。原110训练长caption依前77token全保留，不新增人工包/下载/租卡；原CLAP未微调。见[训练验证](docs/verification/MUS-054.md)。


MUS-055已完成同批77/256长度对照：干净635060a8d15d679e51f5dbe88516af209018abfc两个stage首次exit0，同232原文实际非pad token全部等于未截断原序列（17–178token），原124截断全部消除。固定train长短各3/6不同作者组件CPU-MPS控制最大差3.65e-7，全108短描述对原77差<=2.90e-7；只新文本overlay，不重编码音频/改原CLAP。37train209对固定alpha1新256唯一CPU fit10.457ms，旧77W不重训，7val23与人写20/140固定比较完成。

主140整曲宏MRR原identity .420808、旧77 .447163、新256 .447149，新减77=-.00001462，95%区间[-.00043860,.00038012]含零；R1 .37/R5 .49保持，当前完整描述没有带来主指标收益，不能外推长文本无用或所有任务瓶颈。生成val两查询版本交叉完整披露，未把换查询当训练提升。143去重检查/独立232token与primal/全部排名和16组bootstrap/实际consumer及两stage同目录与换目录拒绝passed，原045–054/模型cache/原141+160/备份/UI/main保持，不搜参/部署/开保留test。B047工具准确限定批准已核原字节接收，不外推本轮质量。见[长度对照验证](docs/verification/MUS-055.md)。


MUS-056已保留全文本为后续训练默认（当前256/全部232零截断，超限报错、不静默回77），并在干净ab668808de94b977c5d403d089460d5f070778f9完成一次归一化正配对训练：同37train209/33组件与alpha1，CPU107.217ms、12步/25次objective评估，按训练relative loss1e-12停止；梯度max2.13e-8仍高于1e-8，未称梯度门槛达标/全局最优。objective1.315548→1.176624、训练配对余弦.342226→.469107，原全文本ridge不重训/原CLAP不微调。

主140整曲宏MRR全文本ridge .447149→新 .448184，差+.001035、95%描述性区间[.000083,.002522]，4胜16平0负；R1 .37/R5 .49保持。对identity差区间仍含零，生成val精确区间MRR .407273→.396378下降；这不是新盲测/稳定泛化或部署依据，不按多轮已看开发区间宣称正式显著提升，继续保留identity。154检查/独立投影梯度与16坐标有限差分/固定日志路径和全部排名12组bootstrap/原与新目录单fit保护passed。原045–055/141+160/模型cache/备份/UI/DB/main保持，无编码/下载/云端/新人工包；下一阶段应改进监督或评测覆盖，不继续在这20开发录音上换loss/alpha挤分，全文本默认不变。见[训练验证](docs/verification/MUS-056.md)。


MUS-058已完成全文本扩样训练：复用旧232区间，只编码新367文字与1101窗口，合计599描述17–195token全部256完整/零截断；CPU/MPS控制与原向量逐元素保护通过。固定alpha1/录音等权，用100录音539区间一次CPU拟合（约26ms），原CLAP和旧37全文本ridge保持。主140整曲MRR旧37 .447149→新100 .447217，差+.000068、95%描述性区间[-.000738,.000888]含零；生成验证精确区间下降，20候选整曲也下降，尚无明确扩样收益、保留identity。176检查/独立完整token与primal/全部排名16组bootstrap/真实消费者与两stage换目录保护通过，旧045–057/原版/UI/main保持，无新下载/保留test/部署。见[扩样训练报告](docs/evaluation/MUS-058-expanded-training.md)。


MUS-059已只读诊断扩样停滞：599描述未发现整段重复或固定5gram近重复；100曲适配更新约89.79%能量在共同残差方向，已知配对与其他录音平均分同步上升，相对差异只小幅变化。100训练曲43/20验证曲11仅一个合格描述区间，同曲比较仅57/9首有支持；这不表示整曲音频不完整。训练/人写查询在长度与本批词面覆盖上不同，不能当CLAP词表外或语义错误证明。192检查、独立聚合复算/原与修复claim保护通过；两次失败和显式修复链保留，无新fit/编码/标签编辑/保留test。原版/UI/main保持，下一轮先冻结训练内共同残差中心化的有界对照，见[诊断报告](docs/evaluation/MUS-059-supervision-diagnostic.md)。
