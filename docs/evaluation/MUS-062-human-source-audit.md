# MUS-062：其他人写来源与小型补充开发计划

当前：方案已固定，干净提交后运行元数据审计和六曲计划生成；没有新音频、编码、拟合或质量评分。A负责，base9c6d690，分支codex/MUS-062-human-source-audit。

[配置](MUS-062-source-config.json)和[E36](../CONTRACTS.md#e36mus-062-外部人写来源审计与六组补充开发计划2026-11-01)固定所有输入/选择与未来比较。63相关检查passed（15新/48既有）；实际结果后补。

官方来源显示：WikiMuTe是维基人写文章经自动抽取的音乐配对，不等同于人工听音真值；YouTube8M原许可为Adobe非商业研究许可，train文件仅视频ID/区间/描述字段，音频权利和音乐作者作品另核；MuChin为中文人工描述候选，但官方仍要求合法音频渠道，不能把仓库代码许可当音频许可。[WikiMuTe论文](https://arxiv.org/html/2312.09207v1)、[发布记录](https://zenodo.org/records/10223363)、[YouTube8M原发布/许可](https://zenodo.org/records/8040754)、[MuChin官方说明](https://github.com/CarlWangChina/MuChin)。

本轮13官方元数据/文档5,083,052 bytes，固定32MiB持久预算中预记20MiB，全部正常TLS/版本/官方MD5或Git commit及SHA记录。只投影身份/URL/区间，不观察新caption正文；YT test.csv未下载，Wiki两个模型筛选版未取，无音频/模型下载。

061剩余8首只涉及6作者组，不能凑20。这里独立冻结小型补充：每组按固定hash取1首，保留原许可与隔离规则；不按模型、文字内容、描述数量选曲，原封存20保持。未来主比较固定identity和已存100曲全文本ridge，新6的MRR为主、146同视图候选、旧20只作控制；当前不评分/选模型。小规模只为新增development覆盖，不作正式验收。
