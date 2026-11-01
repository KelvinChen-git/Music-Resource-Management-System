# Account B — MUS-047 device-calibration review completed

- task_id / assignment_revision / owner / slot：MUS-047-R1-B / 1 / b / B。
- status：review_completed；verdict：approve_scoped；限定合成数值/设备策略/cache/流式边界及静态runner，无范围内阻塞发现。
- source_branch：review/MUS-047-B-device-calibration；交付source SHA见同次feed handoff。
- reviewed_sha：d8555fa2ee888107cc9fac9e0eda373fd9c2e777。
- comparison_base_sha：aaf5e4bbffa61969b3d7bf993b408acec195a818。
- assignment_source_sha：338146a81392169b33965bb3bf01179d8f092fc8（本次A固定入口，047/rev1原卡保持）。
- ack_peer_feed_sha：09c24cd9ee9b2636e216dd7038175568259b5c0b。
- claimed source/feed：5789d4aecfa23e3db1c83bb1a710adbb6220d695 / 3750d46f3fa612f9b98bc8b9d22a01d8c744a2d9，先发布精确回读再测。
- report：[docs/reviews/MUS-047-B.md](../../reviews/MUS-047-B.md)；report_sha256：0cfe428687ce6ffa499ee89c435137b43c00050f356fe0f99ca1c35f53420cbb。
- 只修改上述报告与own latest，交付后释放两文件占用。

原12项NumPy/标准库测试与B独立7项检查均首轮exit0/0失败错误跳过，无产品或测试修复，不加计内部子例或A66项。独立FP32(9,512)/(6,512)数值/整曲与三窗分数/余弦/稳定次序一致，1e-4附近一ULP区分通过与失败，近并列实际反转仍单列；稳定翻转和异常向量拒绝。10组合成inventory与8缓存变体/独立canonical SHA一致，不是实际设备验证。

B真实17,280,264-byte NPZ超过旧16MiB可stream校验并回读；32MiB容量接受/+1拒绝，JSON仍16MiB/+1拒绝，symlink/祖先/hardlink/目录/空文件和变更pin拒绝。权重准确size/SHA由旧checkpoint guard静态核对，未读真实权重。原小文件helpers未改。

静态核对独占输出172行先于inventory174/package179/load198，freeze194行先于严格CPU加载，再显式迁移/全参数device/FP32/冻结；Torch2.6旧精度与2.9新ieee分支、no autocast/TF32、同步/1warmup3timed、设备/本机环境独立key及前后输入/模型/源码复核。参考官方版本源码/API，不冒充真实Torch/GPU/CLAP或跨主机路径实跑。

命令：PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_device_calibration -v；PYTHONDONTWRITEBYTECODE=1 python3 .local/b/runtime/review047.py；git diff --check。Python3.12.14/NumPy2.3.5，B无Torch但本卡合成检查不blocked；不安装依赖或模型shim。私有verified-evidence.json SHA256 2852fc889ed40f4e5a1ceebd698f30912ed70ce7f807fbf23091191fb165e1db，未上传，不假设A能读。

未读A音频/描述/特征/权重/旧141或160评分，不下载/训练/租卡/上传云端/启动服务或执行保留test/真实设备计时；A MPS约2.73倍仅其9窗热SDK实测，非B或训练/P95/CUDA认证。046原字节接收已核；054真实小fit/主区间含零/保留identity仅状态同步，本卡不扩到048–054或模型质量。B无产品/API/schema/配置/锁/真实数据/模型/索引或main变化。

下一步A精确接收报告并串行更新STATUS；本卡无待修产品项，实际GPU路径仍未验证。GitHub接口顺序发布source再自身feed，非原子，须回读报告及两个feed文件，交付SHA/实际发布状态以handoff/回执为准；发布不等于A接收或main合并。交付后释放占用，无后台轮询。
