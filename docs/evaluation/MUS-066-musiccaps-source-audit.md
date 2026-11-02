# MUS-066：MusicCaps来源可用性与权利证据

准备完成，实际20来源网络抽查待干净提交后执行。A；2026-11-02 America/Chicago；branch codex/MUS-066-musiccaps-source-audit，base4780f09ee73829ff82d970a2ef4435cda133968a。

按[E40](../CONTRACTS.md#e40mus-066-musiccaps来源可用性与证据分层2026-11-02)和[配置](MUS-066-source-config.json)复用050原MusicCaps CSV、2448非AudioSet-eval且有MusicBench未增强路径的metadata框；固定seed hash取20，不能按访问结果/描述/模型/许可补选。本轮只访问oEmbed公开metadata和4份官方文档，不取音频或模型输入。

原[MusicCaps固定卡片](https://huggingface.co/datasets/google/MusicCaps/blob/0a51889b340037bb75a9a0858af2e4ece21f7f89/README.md)的caption许可不替代视频音频权利。[YouTube视频API](https://developers.google.com/youtube/data/reference/rest/v3/videos#status.license)的status.license、contentDetails.licensedContent、embeddable表示不同事实；[许可说明](https://support.google.com/youtube/answer/2797468?hl=en)和[服务条款](https://www.youtube.com/static?template=terms)另列，不能据可访问或标题CC认定已允许本项目音频获取/训练。API调用需要[项目凭据准备](https://developers.google.com/youtube/data/getting-started)，本轮不调用API或创建凭据，许可核查缺口保持blocked。

每URL一次/正常TLS/不跟redirect，固定8MiB持久预记；连续3次网络或访问限制错误就停止余项，无重试/替补。200/JSON/provider/同videoID iframe与uploader URL核对，只可标metadata可用，不当可播放、可下载、音乐作者/作品或权利确认。完整原文字保留，caption语义/AudioSet-eval/保留20/160不用模型；无新fit/音频/云端/人工包/UI/Java/DB/main/B047卡变化。旧045–065全部1170文件已快照，结果结束再核。
