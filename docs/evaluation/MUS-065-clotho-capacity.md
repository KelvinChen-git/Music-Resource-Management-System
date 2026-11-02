# MUS-065：Clotho人写研究训练候选容量

准备完成，实际容量统计待干净提交后执行。A；2026-11-02 America/Chicago；branch codex/MUS-065-human-source-capacity，base77aabf4d3d77b99e4876b77a7f07c11b5222874f。

按[E39](../CONTRACTS.md#e39mus-065-clotho人写训练候选容量2026-11-02)和[固定配置](MUS-065-source-config.json)，统计Clotho v2.1三split metadata中的固定whole music/instrument tags，BY/BYSA音频、同sound/uploader闭包跨split双边排除，development每文件5个人写caption仅查绑定/完整性，不读取语义或给模型输入。CC0另报，未进入本轮既定BY/BYSA门槛不表示其权利更严格。

[官方v2.1发布](https://zenodo.org/records/4783391)提供人工短音频描述及逐文件音频许可；[原caption许可](https://zenodo.org/records/4783391/files/LICENSE?download=1)限制实验与非商业使用，不能据音频CC推断caption商用权利。[CLAP官方README固定版本](https://github.com/LAION-AI/CLAP/blob/1fd4c37df5ffbfcfbad5415c170bc66cf94c9994/README.md#pretrained-models)说明Clotho/AudioCaps检索指标用于检查点选择，故不称当前A上的全新独立benchmark；精确训练成员仍未知。

本轮不取音频归档/val与eval caption正文，不fit/编码/评分/开项目封存测试或新人工包。只产生有来源字段的私有metadata候选，不标audio_ready/training_ready；声源/上传者不是穷尽音乐作者/作品身份，音乐tag不代表完整歌曲或caption语义审核。原版/UI/DB/main/B047卡保持，旧045–064共1115文件已快照。
