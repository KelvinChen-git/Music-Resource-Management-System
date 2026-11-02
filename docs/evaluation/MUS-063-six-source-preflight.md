# MUS-063：六曲补充开发音频预检

方案已固定，待干净提交执行。A；2026-11-02 America/Chicago；base d88d4c3，branch codex/MUS-063-six-source-preflight。

只使用062原六曲/六credit组/七有效人工描述计划，核历史元数据/官方low音频SHA、实际EOF及片段、旧音频与新6精确bytes/PCM去重。固定单曲20MiB/总128MiB持久body预算，每曲一次、不替补；新caption正文/编码/模型加载/fit/评分/封存test和人工包均0。

[配置](MUS-063-preflight-config.json)和[E37](../CONTRACTS.md#e37mus-063-六曲开发补充音频预检2026-11-02)在正式获取前提交；86相关检查passed（15新/71旧，含8实际EOF边界）。源码/输入/decoder runtime先freeze再网络；失败原件和claim保持。

旧内容池296条来源引用、295唯一bytes/PCM（旧60/04320/045140/05776）。新6若与旧或彼此重复则拒绝；此为精确去重，不穷尽不同编码、偏移、变速或翻唱。历史逐曲BY/BYSA记录不等于当前在线权利确认或SDD 320kbps确切版本，原文与全部旧素材保持。

后续另冻特征和两模型146池比较；本轮ready仅表示具备构建特征的音频前提，不当模型质量通过。无对应源码变化，不运行Java/前端build。实际结果/证据执行后补入。
