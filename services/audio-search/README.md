# Audio search feasibility spike

当前仅为 MUS-002 的离线 CPU 编码探针，**不是检索 API、索引或已验证的音乐搜索产品**。实际结果与局限见 [model-spike.md](../../docs/model-spike.md)。discovery-v0 仍未冻结。

本轮环境：CPython 3.12.10、macOS arm64。只对该平台生成 resolved version lock；不能据此声称 Linux / CUDA / MPS 或 Python 3.14 可用。

在自己的独立 clone / slot 中创建环境（下例为 A；B 不写 A 目录）：

```bash
python3.12 -m venv .local/a/clap-venv
.local/a/clap-venv/bin/python -m pip install -r services/audio-search/requirements-spike-macos-arm64.lock.txt
.local/a/clap-venv/bin/python -m pip check
.local/a/clap-venv/bin/python -m unittest discover -s services/audio-search -p 'test_*.py' -v
```

checkpoint 只使用以下固定版本（约 2.35GB；未纳入 Git / bundle）：

```bash
mkdir -p .local/a/models
curl -fL --retry 2 -o .local/a/models/music_audioset_epoch_15_esc_90.14.pt \
  https://huggingface.co/lukewys/laion_clap/resolve/b3708341862f581175dba5c356a4ebf74a9b6651/music_audioset_epoch_15_esc_90.14.pt
```

探针在任何反序列化前流式检查固定 SHA-256。它使用 PyTorch weights_only=True / mmap 和已知 NumPy 标量类型，而非 SDK 的通用 weights_only=False。加载严格核对全部参数，只移除 Transformers 不再持久化的非学习 position_ids buffer。

```bash
HF_HOME="$PWD/.local/a/hf-cache" HF_HUB_DISABLE_XET=1 WANDB_MODE=disabled \
  .local/a/clap-venv/bin/python services/audio-search/probe.py \
  --checkpoint .local/a/models/music_audioset_epoch_15_esc_90.14.pt \
  --report .local/a/logs/clap-probe.json
```

首次构造还会下载固定 revision 的 FacebookAI/roberta-base 模型 / tokenizer（SDK 构造依赖，随后文本权重被 CLAP checkpoint 严格覆盖）。probe.py 仅在构造期间对这两个 from_pretrained 调用加入固定 revision；没有修改安装包文件。首次有网完成后，可加 HF_HUB_OFFLINE=1、TRANSFORMERS_OFFLINE=1，并使用新的报告文件名离线复跑。已有报告拒绝覆盖。

输入是合成 44.1kHz 立体声正弦波：先平均声道、soxr_hq 重采样，按整数采样点长度裁齐 / 补齐，再右侧补零至 480000 点。传入 SDK 的长度恒为 10 秒，避免它默认 repeatpad / rand_trunc 改变短尾段。probe 不是任意长音频切片器；超过 10 秒明确拒绝。SDK 仍执行自己的 int16 往返量化。

9 项预处理测试包含 1 秒 / 10 秒的 44.1→48kHz 长度、短段补零、立体声、非整比例长度、无效值及长输入拒绝。曾发现浮点 ceil 多出一个采样点，已用整数长度计算修正，不放宽断言。

后续还需：真实 MP3 / WAV 解码路径、许可语料 manifest、真实文本 / 音频检索对照、片段边界、人评与契约 fixtures。当前不建立线上服务、不提交权重 / 音频 / 索引、不报告质量或 P95。
