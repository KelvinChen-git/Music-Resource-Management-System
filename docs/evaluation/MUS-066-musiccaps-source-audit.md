# MUS-066：MusicCaps来源可用性与权利证据

**固定20个来源全部返回有效公开metadata；逐视频许可、音乐作者/作品和实际音频尚未核验，训练就绪仍为0。** 这次抽查解决的是metadata访问前提，没有证明20个视频可播放、可下载或满足训练权利条件，不排除MusicCaps后续可用。

A；2026-11-02 America/Chicago；branch `codex/MUS-066-musiccaps-source-audit`，base `4780f09ee73829ff82d970a2ef4435cda133968a`，实际干净源码 `4218f737e4bca3494083558561be5fe20312869b`。首次实际运行exit0，最终交付SHA见A feed handoff.source_sha。本轮A同操作方独立复核非B审核，B047限定批准不外推。

## 固定抽查与实际结果

按[E40](../CONTRACTS.md#e40mus-066-musiccaps来源可用性与证据分层2026-11-02)和[配置](MUS-066-source-config.json)复用050已pin原MusicCaps CSV/官方卡和2448个“非AudioSet-eval、有MusicBench未增强路径”metadata框。全部5521行元数据绑定保持，AudioSet train2663/eval2858；author_id是描述撰写者，未用于音乐作者分组。没有重新下载caption库或观察caption语义。共享CSV为hash和metadata解析会物理读取包含全部caption的原字节；程序只访问ID/起止/AudioSet flag，不抽取caption字段，AudioSet-eval不作probe或模型输入。

抽查按SHA256(seed+换行+videoID)排序取最低20，seed=MUS-066-MusicCaps-source-probe-v1。源码/config/输入/TLS CA/Python/OpenSSL在选择与网络前冻结，持久单claim，不按内容/模型/许可/访问结果补选。这个框尚未成为项目train/dev/test，AudioSet flag不能替代跨音乐人/作品/来源内容隔离。

| 检查 | 实际结果 |
|---|---:|
| 固定候选框 / 本轮选定来源 | 2,448 / 20 |
| 实际oEmbed请求 | 20，各一次 |
| HTTP200、JSON、YouTube provider、同ID iframe绑定与uploader URL | 20/20通过 |
| oEmbed元数据不可用、超限、网络错误 | 均0 |
| 访问停止条件触发 / 未尝试来源 | 0 / 0 |
| 已核实逐视频许可 | 0（未知，不是证明无许可） |
| 已核实音乐作者/作品 / 实际10秒音频 | 0 / 0 |
| audio_ready / training_ready | 0 / 0 |
| 音频/归档下载、编码、fit、保留测试输入、人工包、付费资源 | 均0 |

20/20只说明本机该时点这20个来源的oEmbed元数据可读取，**不是全5521的可用率/权利容量估计，也不说明播放器或原音频已验证**。返回title/uploader/iframe等原字段只保存在私有目录，HTML只解析src，不执行或展示，不据标题中的CC等词自动批准。

## 三种尚缺的证据

1. **逐来源许可与取得方式。** [MusicCaps固定卡片](https://huggingface.co/datasets/google/MusicCaps/blob/0a51889b340037bb75a9a0858af2e4ece21f7f89/README.md)的文字许可不等于视频原音频授权，MusicBench公开归档也不自动完成逐源权利核验。[YouTube许可说明](https://support.google.com/youtube/answer/2797468?hl=en)区分默认YouTube许可与CC BY；[视频API文档](https://developers.google.com/youtube/data/reference/rest/v3/videos#status.license)的status.license才是相应字段，licensedContent是内容合作伙伴上传/主张的状态，embeddable是嵌入设置，均不能替代许可。获取途径另看[服务条款](https://www.youtube.com/static?template=terms)，本轮未运行音频提取器或据未知状态下“违法/禁止训练”的结论。
2. **音乐人/作品及跨来源关系。** oEmbed的author_name/author_url是上传者或频道，未确认录音及作品作者，不能据20个不同视频ID声称20首独立歌曲或作者隔离。原项目SDD封存组、Jamendo/FMA已用来源与翻唱/合辑/上传重复仍需对应证据。
3. **音频和原描述的真实对应。** 尚无取得的音频、实际EOF/10秒原区间/版本/PCM去重/完整文本token及特征验证。配对metadata数量不能当可训练音频数量。原caption全文保持，后续若进入模型仍遵守完整token证明/超限失败。

许可API调查当前记为blocked：本轮没有调用YouTube Data API、没有得到任何status.license记录。freeze只观察标准YOUTUBE_API_KEY环境项未配置，不等于已扫描并否定本机所有可能的凭据；不读取或打印密钥、不创建云项目或付费资源。[官方API准备](https://developers.google.com/youtube/data/getting-started)需要启用服务与配置项目凭据，补此字段也不会单独解决其余两项。

## 网络预算与文档完整性

4份官方说明加20个oEmbed固定URL共24请求，正常TLS，每URL一次/无redirect/重试/补选。持久账本在每次请求前预记正文上限+1；总预记5,505,048 bytes<8MiB，实际正文1,525,435 bytes，音视频字节0。probe单64KiB、文档单1MiB；多读最多1 byte仅判定超限，预算含此byte。

API资源、API准备和服务条款3份本地响应完整；license_help HTTP200正文超过1MiB，保存1,048,577 bytes并明确oversize=true，**不是完整文档快照**，没有增预算/重取。原始部分响应与hash保留，官方许可页面的事实说明来自浏览器读取的原页，不用截断副本冒充完整许可审阅。20份probe JSON均完整。

## 验证、保护与交付

29相关检查passed（14新/15既有），覆盖固定5521/2448绑定、AudioSet-eval/增强路径拒绝、固定hash选择、返回视频/厂商/uploader绑定、HTTP404和网络错误不推媒体不存在、标题CC/自带license/licensedContent不提升权利、禁止redirect、访问停止与任务claim。没有新增依赖，未重复Java/Vue build（来源metadata Python范围）。

独立标准库程序未导入生产probe、未联网或加载模型，按列读取原数据、重算全部20选项、逐响应JSON/iframe ID/未知证据状态、24收据/字节/hash/请求前预算/停止规则，全部匹配；源码与输入/TLS CA hash保持。真实原目录和新目录两次重跑均在新输出/网络前拒绝，原claim/账本/响应/结果SHA保持，额外请求0。

旧045–065全部1170文件集合/hash、历史951+B047快照/23源码/54offline cache/043044/160判断与相邻原版f3b0da1干净保持，新目录700/文件600。无UI/Java/DB/API/依赖锁/main/B047卡改动，无新音频/模型/fit/用户任务。逐源证据私有，仅聚合/hash见[验证JSON](../verification/MUS-066-results.json)。

## 下一步

MusicCaps的链接元数据抽查已通过，暂缓媒体获取与训练。下一步是补齐逐源许可记录、可核音乐作者/作品与允许的音频取得路径，再决定是否做有界10秒音频预检；不把API key本身或oEmbed成功当训练许可。当前不扩到5521逐一访问，不下载16.76GB MusicBench归档，不继续按旧26开发样本调参或新派人工全组合标注，identity与全文本策略保持。
