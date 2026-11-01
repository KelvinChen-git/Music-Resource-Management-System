# MUS-056 全文本归一化配对训练

2026-11-01 America/Chicago；owner A；base19fab38；branch codex/MUS-056-fulltext-cosine-training。用户偏好成为后续训练默认：保留完整原文token，当前256缓存最长178、零截断，超预算失败再明确处理，禁止无提示截断/回退77/改写；完整性沿055 token proof/缓存SHA验证。人写24query本来只有11–30token，旧048特征已覆盖全文，继续复用。配置见[固定协议](MUS-056-training-config.json)、CONTRACTS E30。

新假设：此前ridge拟合XW到T，排序却用unit(XW)，故本轮固定37train209/33组件/7val23、全文本向量、q每录音等权和alpha1，仅目标改为sum(q||unit(XW)-T||²)+alpha||W-I||F²。T是单位完整文字向量，数据项等价2(1-已知配对余弦)，只鼓励已知正配对，不造其他音乐不相关标签；这个目标更接近余弦，但仍不直接优化排名/处理完整语义。

CPU float64/2线程、identity起点、full batch gradient/Armijo：initial step1/max200/backtracks20/c1e-4/factor.5，只有train grad max1e-8或relative loss1e-12停止，验证不参与。归一化目标非凸，迭代和旧闭式ridge方法不同；停机不当全局最优，达到上限披露而不追加步数/放宽容差。先冻结input/source/config/runtime、单fit持久claim，失败保留，W/fit保存后才val分析。reader完整性会读取共享NPZ的val数组，但solver仅用209train。

完整报告identity/已存055全文本ridge/新全文本cosine，两人写池20/140整曲及窗口R1/R5/MRR，主140整曲宏MRR新cosine减已存全文本ridge；7val23只用全文本query、精确区间/7录音max指标。2000次/seed20261101056录音配对bootstrap对两锚完整披露。全是已看开发/小生成验证，不称新独立test或未知曲真负例，不能凭次要改善自动切模型/扩训/开保留test。

154相关检查passed（11新/143旧），日志只私有.local/a/mus056，目录700/文件600；有限差分验证归一化梯度、尺度不变/配对余弦关系、重复某录音全部区间不改变权重和解、train-only停止/步数上限/Armijo失败不重启、全文本超限/截断拒绝。真实训练与独立复算见[验证](../verification/MUS-056.md)，此实现检查点尚未实跑。旧045–055/141+160/权重/cache/SDD/保留test/原版/UI/Java/DB/main只读，不下载/新编码/人工包/云端/租卡/自动部署；B047原限定批准不外推新工具/质量，不派新卡。
