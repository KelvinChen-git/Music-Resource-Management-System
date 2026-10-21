# Audio search feasibility spike

当前包含 MUS-002 合成编码探针和 MUS-022 真实小语料离线候选排序，**不是检索 API、可发布索引或已通过质量验收的音乐搜索产品**。实际结果与局限见 [model-spike.md](../../docs/model-spike.md)。discovery-v0 仍未冻结。

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

原MUS-002检查点尚缺真实解码/语料处理，现已由下述MUS-022补部分运行证据；仍需人评、效果/模型对照与契约fixtures。不建立线上服务、不提交权重/音频/生成索引，不报告质量或P95。


## 真实小语料探针（MUS-022）

`corpus.py`校验已记录输入/下载证明与字节哈希，解码实际MP3/WAV，并提供候选10s/5s窗口及精确向量排序规则；`corpus_probe.py`复用固定checkpoint，生成当前checkout `.local/` 下的新run目录，拒绝覆盖既有run，模型缓存强制离线。音频根目录显式给出，仅按数字sourceId查找，拒绝逃逸/不匹配/重复内容；不接受任意远程输入。不要把此离线读取替代Java权限核验。

首次真实运行已对20首/933片段、8英文文字与3参考片段完成512维编码/排序；23项测试通过。完整实跑命令、原始工件位置/摘要、未标注边界见 [MUS-022](../../docs/verification/MUS-022.md)。生成向量/排序仅保留ignore目录，不提交Git；探索查询fixture不是评测集，reference同源自匹配不能算质量。原输入只读共享，输出需独立；B在自己的合法输入/缓存/slot运行，不依赖A本机路径。

尚需人工相关性/区间标注、效果和模型对照及discovery-v0冻结；当前不提供online API或前端检索。原MUS-002合成探针保持原样。
