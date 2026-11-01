# MUS-047-R1-B：设备校准工具限定审核

2026-11-01（America/Chicago），owner / slot：b / B，revision 1，`review_completed`。结论 **`approve_scoped`**：未发现本卡范围内阻塞问题；仅批准准确源码的合成数值、设备策略、缓存身份、文件边界及静态 runner，不认证真实 CPU/MPS/CUDA 编码、速度或模型质量。

| 身份 | 准确值 |
|---|---|
| task_id | MUS-047-R1-B |
| branch | review/MUS-047-B-device-calibration |
| reviewed_sha | d8555fa2ee888107cc9fac9e0eda373fd9c2e777 |
| comparison_base_sha | aaf5e4bbffa61969b3d7bf993b408acec195a818 |
| assignment_source_sha | 338146a81392169b33965bb3bf01179d8f092fc8 |
| ack_peer_feed_sha | 09c24cd9ee9b2636e216dd7038175568259b5c0b |
| claimed source / feed | 5789d4aecfa23e3db1c83bb1a710adbb6220d695 / 3750d46f3fa612f9b98bc8b9d22a01d8c744a2d9 |

从固定 A 入口读取同 source 的派发、[准确任务卡](https://github.com/KelvinChen-git/Music-Resource-Management-System/blob/338146a81392169b33965bb3bf01179d8f092fc8/docs/collaboration/tasks/MUS-047-R1-B.md)、E22/config/状态和 046 接收记录。原 047/rev1 卡仍有效，未扩到 A 后续 048–054。独立 B clone 从干净 reviewed SHA 建任务分支，先发布 claimed 并逐字回读，再审核。本次只修改本报告与 [own latest](../collaboration/account-b/latest.md)，由 A 串行更新 STATUS。最终交付 SHA 取完成 feed 的 `handoff.source_sha`。

## 实际验证

| 检查 | 结果 | 适用范围 |
|---|---|---|
| 原 `test_device_calibration` | 12 方法，exit 0，0 failure/error/skip | 原生 NumPy/标准库，含原 17 MiB 二进制边界 fixture |
| B 独立 fixture | 7 方法，exit 0，0 failure/error/skip | 独立求和/归一化、设备策略、canonical hash 与实际私有文件 |
| runner/E22/config/官方 API | 静态检查未发现阻塞问题 | 不计作真实模型、Torch 分支或 GPU 运行 |
| 文档/交付 | `git diff --check`、链接/字段/仅两允许路径核对 | 文档检查 |

两套测试首轮均通过，没有产品或测试修复；内部阈值子例、10 组合成 inventory、8 个缓存变体不另加为测试方法数，也不累加 A 的 66 项。环境 Python 3.12.14 / NumPy 2.3.5，B 未安装 Torch；本卡 NumPy 检查无需 Torch，不因缺失实际设备而记为 blocked。没有安装依赖或注入模型 shim。

实际命令，仓库根目录：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_device_calibration -v
PYTHONDONTWRITEBYTECODE=1 python3 .local/b/runtime/review047.py
git diff aaf5e4bbffa61969b3d7bf993b408acec195a818 d8555fa2ee888107cc9fac9e0eda373fd9c2e777 -- services/audio-search/device_calibration.py scripts/calibrate_encoder_device.py scripts/test_device_calibration.py docs/evaluation/MUS-047-device-config.json
git diff --check
```

私有证据仅在 B 本机忽略区 `.local/b/review-evidence/MUS-047-R1-B/`，`verified-evidence.json` SHA256 为 `2852fc889ed40f4e5a1ceebd698f30912ed70ce7f807fbf23091191fb165e1db`，覆盖两套日志/结果、独立脚本与准确源码 hash、静态观察及官方参考。证据未上传，不假设 A 能读取 B 本地路径。

## 审核结果

- [device_calibration.py](../../services/audio-search/device_calibration.py) 的 `valid_vectors/compare`：固定 shape、finite、单位范数与三个 `1e-4` 数值容差，整曲三窗均值归一化和三窗最大得分分别计算；只将参考分差严格大于 `2e-4` 的候选对判作稳定，近并列单列。B 用 FP32 `(9,512)` / `(6,512)` 合成特征、标准库独立归一化/逐项求和复算，向量/余弦/两模式得分及稳定/近并列/翻转计数一致。比较器内部 FP64 数值运算不是实际 FP32 GPU 执行证据。
- 阈值未改：存储为 FP32 的扰动 `9.999999747378752e-5` 通过，紧邻的下一浮点数 `1.0000000474974513e-4` 失败。另一 fixture 在 `1e-4` 近并列内实际反转次序，向量/得分误差仍合格，两模式各 12 稳定对/6 近并列对/0 稳定翻转，正确单列而不宣称全 rank 相同。稳定次序交换例两模式各 8 次翻转且失败；shape/NaN/Inf/零向量/超单位范数拒绝。全过程使用原冻结 policy，不放宽容差。
- 同模块 `device_status`：只接受 cpu/mps/cuda:0；缺 Torch、MPS 不可用、CUDA build/availability/count 任一不足均 blocked，原请求 device 保留；MPS CPU fallback 为 true 时拒绝。B 的 10 组 inventory 是纯合成字典，不是 GPU 可用性检查。
- 同模块 `cache_key`：B 独立重建 canonical JSON/SHA256，基准值 `f738f9f00f7b8a2a474facd6a7612254ef799a3a5606898a8acdab51c36a69ae` 一致。分别更改设备、环境、模型、波形输入、配方、源码内容/名称均产生不同 key；仅调整字典插入顺序保持。错误 digest 和非有限 JSON 拒绝。实际 runner 的非空源码集合、固定模型及输入由其绑定检查约束。
- [calibrate_encoder_device.py](../../scripts/calibrate_encoder_device.py) 的 `check_bound_files`：准确新 helper 使用 regular 文件校验、stat 上限及原流式 SHA helper。B 创建真实 9×480000 float32 NPZ，大小 **17,280,264 bytes**，超过旧 16 MiB 上限，校验并以 `allow_pickle=False` 回读成功；前后两次检查间追加一字节后原 pin 拒绝。32 MiB 原始容量 fixture 接受，32 MiB+1 即便提供正确 SHA 也拒绝；该容量 fixture 不冒充 NPZ 解码。JSON 16 MiB 接受、+1 拒绝；symlink、symlink 祖先、hardlink、目录和空文件拒绝。fixture 全在 B 自建私有临时目录，未读取 A 原件。
- checkpoint 的上限 helper 不能单独代表权重可信：runner 另调用旧 `checked_checkpoint`，按固定文件名、准确 **2,352,471,003 bytes** 与原 A SHA 验证后才反序列化。静态核对原 strict CPU loader 的 weights_only/mmap/CPU/strict 和前后 pin 检查；未创建或读取真实权重。原 `holdout_assets` 16 MiB JSON helper、`holdout_contract` 和 checkpoint loader 在本审核 diff 中逐字未改，未为大 NPZ 放宽旧小文件入口。

静态 runner 的关键顺序及边界：

| 位置 | 观察 |
|---|---|
| prepare / run 独占输出 | prepare 在模型操作前建独占目录；run 第 172 行建目录，174/175 行才查 inventory/策略，179 行才读 package，198 行才载模型。已有目录在模型前拒绝；不可用设备路径写 blocked/model_loads0 后返回。B 未执行真实模型 CLI 重试。 |
| prepare 固定输入 | 原 train 按 source ID 升序前 3、前 6 tag 模板；完整 EOF/PCM 后首 min120 秒、首中尾 9 窗，CPU 参考与原音频/文字控制对照；新输入和 freeze 先于模型操作。无 outcome 驱动选样、下载、fit 或保留 test 模型输入。 |
| run 第 186/188/194/198/199 行 | 包/NPZ/模型先校验，freeze 先写；原严格 CPU loader 完整加载，随后显式 `.to(target)` 并更新 SDK device。全参数冻结，参数 device 与 floating dtype FP32 逐个核对，输入波形 shape/FP32/finite 检查。 |
| setup / benchmark | Torch 2.9 前走旧 allow_tf32=false，2.9 起走 matmul/conv 的 ieee 分支；无 autocast，deterministic，audio3/text6、1 warmup+3 timed。GPU 同步包围 timed SDK 调用，CUDA 峰值 allocated 与 MPS 运行后观测值分名记录；加载与热 SDK 编码时间分开，不称 P95/训练加速。 |
| 跨主机与结束复核 | 包绑定相同输入/模型/源码/配方，但本地 checkpoint 显式传入，不要求原参考机器路径存在；设备/本机环境单独入 key，GPU 不复用 CPU key。第 211–213 行复核输入、准确模型、当前环境与源码。 |

Torch 精度与同步只按官方 API/源码静态核对：参照 [v2.6.0 Context](https://github.com/pytorch/pytorch/blob/v2.6.0/aten/src/ATen/Context.cpp)、[v2.6.0 cuBLAS handle](https://github.com/pytorch/pytorch/blob/v2.6.0/aten/src/ATen/cuda/CublasHandlePool.cpp)、[2.9 CUDA 精度说明](https://docs.pytorch.org/docs/2.9/notes/cuda.html)、[MPS synchronize](https://docs.pytorch.org/docs/2.9/generated/torch.mps.synchronize.html) 和 [CUDA synchronize](https://docs.pytorch.org/docs/2.9/generated/torch.cuda.synchronize.html)。未将新版文档替代 2.6 源码，不声称实际覆盖这些 Torch/硬件分支。

## 范围与交接

[固定 config](../evaluation/MUS-047-device-config.json) SHA256 `0ae18eb1c42e9538403aa221c3d158ba3963618a2c10450652529ff543019cb1` 与 E22 一致；三个新文件/config 在 reviewed 与本次 assignment source 间字节相同。完整性/数值阈值固定，A 初次大包错误是旧 JSON 容量入口误用，不是 B 重现的 MPS 算子失败，也未以此放宽门槛。

未独立执行真实 CPU 参考/MPS/CUDA/CLAP/codec、真实 checkpoint/环境/跨主机传输或计时；未读 A 私有音频、描述、权重、特征、run、141/160 评分或保留 test。真实 GPU 分支保持未验证；A 约 2.73 倍是其固定 9 窗热 SDK 小样本证据，不是 B 认证、训练速度、P95 或 CUDA 结果。没有真实设备在 B 通过的声明，不重复 045/046、048–054、Java/Vue/MySQL 或部署检查。

046 报告 SHA `4ea8503942be5663e2dbd936d049b7a096e0d6091e83df5f935d4fba7416a9e4` 已与 A 接收归档逐字 hash 核对，原限定批准已被接收。A 最新 054 记录为一次小 caption 适配器实际 fit、主 MRR 区间仍含零、保留 identity；仅同步公开状态，不将本卡外推为后续训练/模型质量批准。

接口变化：B 无。数据/模型/索引版本：仅 B 合成数值与临时二进制 fixture，无真实版本新增/切换。未启动服务，不改产品、API/schema、配置/依赖锁、A STATUS/派发或 main。

下一步由 A 精确接收报告、串行更新台账并确定后续有界卡；本卡无待修复产品项。source 与自身 `collab/account-b` 采用 GitHub 接口先后发布，非原子，须精确回读报告和两个 feed 文件；交付 source/feed SHA 与实际发布结果见回执。发布不等于 A 接收或 main 合并。交付后释放两文件占用，无后台轮询。
