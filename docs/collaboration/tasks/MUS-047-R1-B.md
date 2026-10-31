# MUS-047-R1-B：设备校准工具限定审核

owner b；revision1；reviewed_sha `d8555fa2ee888107cc9fac9e0eda373fd9c2e777`；comparison_base_sha `aaf5e4bbffa61969b3d7bf993b408acec195a818`；review_branch `review/MUS-047-B-device-calibration`。assignment_source_sha由发布本卡的A feed source_sha给出，B先同步/claimed并精确回读再审核。

仅允许输出新 `docs/reviews/MUS-047-B.md` 和 `docs/collaboration/account-b/latest.md`，不改产品/STATUS/A任务入口。046-R1已完成approve_scoped并由A接收，不重复领取或外推。

准确新增范围：`services/audio-search/device_calibration.py`、`scripts/calibrate_encoder_device.py`、`scripts/test_device_calibration.py`、E22及047固定config。只做合成数值/设备策略/流式输入边界与静态runner审核，无需GPU/torch/CLAP或A私有数据。

重点核对：

1. FP32向量shape/finite/单位范数、1e-4预注册误差阈值、整曲/三窗得分、参考分差>2e-4稳定次序及近并列单列；拒绝异常/稳定排序翻转，不依据实际结果放宽阈值。
2. 显式cpu/mps/cuda:0、无auto/无设备返回blocked、MPS CPU fallback拒绝、设备/环境/源码/模型/输入/配方的缓存key隔离。合成inventory不是实际GPU验证。
3. 17MiB NPZ可流式校验（32MiB上限），JSON保持原上限、checkpoint限制原准确大小与SHA，regular/symlink拒绝/输入前后哈希。不得修改旧被冻结的小文件helper；首失败是JSON入口容量误用，不是MPS算子失败。
4. 静态确认原严格CPU loader完整加载后显式迁移目标device，所有参数device/FP32/冻结检查，no autocast/no TF32、计时前后同步、1warmup+3timed、数据/模型/环境/源码前后复核，现有目录先拒绝。只涉及3train9窗6tag，无训练/下载/保留test/部署。
5. 跨主机包只绑定同模型/波形输入/算法源码，设备/环境独立记录；不使用CPU缓存key冒充GPU。MPS通过不能推成CUDA通过，也不把小批次SDK编码速度当训练/P95。CPU参考/模型/真实MPS路径只静态核对，不访问A数据冒充复现。

最低命令（NumPy与标准库即可，不为此装torch或拉模型）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/audio-search:scripts python3 -m unittest test_device_calibration -v
```

原12项合成检查，另补少量独立fixture验证数值/近并列/缓存key/显式设备/流式边界；缺依赖记blocked，不注入模型shim。A66项/真实CPU-MPS运行不计为B证据。B可以审查Torch版本分支/同步调用等静态路径，但不能称真实GPU/模型运行passed。

报告准确命令/唯一计数/首轮错误/未执行项与原因、verdict和范围；本轮MPS编码约2.73倍为A的小样本实测，非B独立效果认证。完成通过自身feed发布task/revision/reviewed/base/assignment-source/ack-peer/report SHA及释放占用，A串行接收，不合并main，无后台轮询。
