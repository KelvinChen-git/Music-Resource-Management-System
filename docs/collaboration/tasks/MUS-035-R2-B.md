# MUS-035-R2-B：N1输出权限增量复核

- owner b；revision 1；status assigned，先通过本人feed发布claimed并回读。
- reviewed_sha `de255c7724926c6f823abceecf0b9a487a467d6d`；comparison_base_sha `74645de71c173c43811d7d0d98548089a1836491`。
- branch `review/MUS-035-B-output-permissions`；只允许`docs/reviews/MUS-035-N1-B.md`和`docs/collaboration/account-b/latest.md`，报告后释放。
- assignment_source_sha取本次A handoff.source_sha，不能与reviewed源码SHA混淆。
- 035/rev1已按原字节接收approve_scoped，见[接收记录](../../verification/MUS-035-B-acceptance.json)。原035卡和报告保持，不重复035全套；仅复核非阻塞N1的修复。

范围：`services/audio-search/research_probe.py`的private_output/write_json/write_vectors（新增chmod/fchmod共3行）及`test_research_probe.py`两个新测试；读E14第一条和040验证记录中的N1部分。准确diff还含双checkpoint预检及接收文档，均不属于本卡批准范围。不得据此声称040加载器/模型/新包/039已获批准。

1. 自建私有临时目录，在umask0777下调用三入口，实际mode必须目录0700、JSON/NPZ0600，能正常重新读取。恢复umask于finally；只修复B自己创建fixture的模式，不能改源码或A目录。
2. 验证仍O_EXCL/O_NOFOLLOW、不覆盖已有输出或跟随symlink；原run入口/数值代码/模型常量/输入规则未改。可运行原31个driver合成测试则独立记录；缺依赖如实blocked，不要求安装依赖或下载模型来完成此有界卡。
3. 若导入模块被B缺torch/soundfile等阻塞，可在自有脚本AST提取准确源码的require/private_output/write_json/write_vectors，使用真实os/subprocess/Path/JSON和现有NumPy直接测三函数；明确这是函数边界验证，不冒充全driver/真实模型或codec运行。禁止用简化重写函数替代产品实现或将shim计为原生全套通过。
4. 不读取A私有音频/凭据/标签/run/权重，原035审核证据不必重做；不测UI/Java/MySQL、不训练或改依赖、不合并main。

A证据：96相关合成测试（75 research包含新2，21 checkpoint）通过；N1另用准确源码函数真实OS/NumPy复现旧000，再验新0700/0600及读回/重复拒绝，非B。预检20旧曲/933片段/5文本与新模型开发命中仅040另列，不外推本卡。

报告须含task/revision/reviewed/comparison/assignment/A ack、claim source/feed、命令/exit/实际模式、允许路径和限制，给review_completed及approve_scoped/request_changes/blocked。只发布自己的source/feed并精确回读；非原子需说明。没有后台轮询。
