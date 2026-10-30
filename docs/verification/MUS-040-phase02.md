# MUS-040第二检查点：新20首导入与身份映射

2026-10-29（America/Chicago），A；branch `codex/MUS-040-independent-runner-preflight`，本段base48eeeca、真实源码`2b2d28796bcd8c74aa96f45f9f38bc602d309220`。**新20已导入，MUS-040整体仍进行中**；[机器结果](MUS-040-phase02-results.json)。

新增[holdout_assets.py](../../scripts/holdout_assets.py)和[import_holdout_music.py](../../scripts/import_holdout_music.py)及25项合成检查/共享fixture；旧导入器/collector/DSP/Java/Vue不改。E15先冻结，source binding显式SHA56b74cd1…绑定原v2协议/全部221来源框、分组/原40排除、20原manifest和G1收据，以及原40 catalog/音频根；完整输入404文件hash及来源/作品/creator cap/原字节/证明/实际时间重建。G1原文件不加Java字段，导入前按原65536 actual EOF/PCM版本再次完整解码20，新NUMBA缓存只在本轮目录。

普通owner的原HTTP接口真实上传20/建metadata20，全部pending；每首实际Java music/file身份、Range206/完整200字节SHA与原源匹配。旧40在前后各核身份/metadata/媒体，原catalog不写。无注册/提权/自动审核/SQL迁移；曲名最长100、作者串最长40，均原样使用，album按source dataset前16位固定区分新测试材料。账号自有资源现在60，其中开发40、独立新20；不是全数据库总量或已建60曲检索索引。

新私有catalog schema=sonora-holdout-import-catalog-v1、split=independent_test_imported_assets，仅新20/owner/源与旧40 pins/真实身份/完整元数据/媒体验证；20原音频+20证明独立副本。source dataset仍2172565f…，新catalog SHA `ea7eb53a6c3c29d9d5d052b2f786c794550cd332cf60162e45b722c1387766f8`。模型权重/新8query/141标签/旧向量与排名保持。

真实首次函数调用exit0、约12.955秒；以实际CLI同目录复跑exit0、约9.660秒，新上传/metadata均0，42核心文件（40副本/ledger/catalog）原SHA保持。可恢复已提交上传/metadata但响应丢失，绑定source/helper/owner/slot，O_EXCL锁/原子checkpoint，不按时间移除外来锁；输入、复制字节或catalog坏则拒绝而不修复覆盖。

仓库根实际CLI重验（已导入，可重复验证，不重复创建）：

```sh
PYTHONDONTWRITEBYTECODE=1 ../Music-Resource-Management-System/.local/a/clap-venv/bin/python scripts/import_holdout_music.py \
  --binding .local/a/mus040/phase02/binding.json \
  --binding-sha256 56b74cd137ac0ae4442cf7c13a8e2c2bd9ceda0429cf7e7cfdc84cafaa1c5561 \
  --backend-checkout ../Music-Resource-Management-System \
  --output-state .local/a/mus040/phase02/import
```

另一个A私有脚本不调用新importer/asset adapter，直接把G1源、私有catalog与真实HTTP三方关联：owner USER、60资源集合=旧40+新20、身份不交叉，20新资源pending且metadata/file ID/Range206/full200 SHA通过，匿名20次均401。是同操作者分脚本核查，非B或独立人员；未创建另一个真实用户测试跨用户权限。播放仍需每次现有JWT媒体鉴权，catalog不构成授权。

78相关合成测试通过（原source26+import27、新asset10+import15），最终14.841秒；早23新测试子集不相加。覆盖完整221来源重建、篡改重签/音频/证明/身份/路径/硬链、错误owner/role、EOF/PCM失败在HTTP前停止、响应丢失恢复、媒体失败保留、重复/锁/极端umask/完成catalog不覆盖。介质/HTTP替身不冒充真实codec；真实证据由上述实际导入/重验提供。

保留三项准备错误：旧Jamendo证明http而catalog为https的同一CC BY地址初检被拒，复用原严格规范化后通过且原件不写；测试复用上一子例已提交的fake backend，使metadata丢失注入未触发，分离fake状态后通过；额外HTTP核查pageSize100实际返回20、第二页空，改用现有UI的20分页后通过，没有修改应用分页。失败不计成功。

838旧文件SHA保持，包含两个checkpoint、所有039/第一检查点原件与旧卡/dispatch；54共享HF cache常规文件集合/hash不变，原备份干净f3b0da1，8080 PID96842/5175 PID4143保持。新数据仅ignore.local/a/mus040/phase02、0700/0600；不提交真实ID/owner/音频/逐条数据，不跑无关Maven/build/浏览器/CLAP，不改UI或合并main。

2026-10-30T01:39:22Z及02:12:49Z sync双方fetched；A95ce190/source48eeeca，B610c03e/source0e8de159，ack B；N1新卡035-R2准确de255c7仍assigned，原卡/dispatch保持，不把035批准外推新导入。接下来需要新test五配置runner/固定呈现、新标注格式及G2冻结；本检查点160包/新判断/test模型run均0，G5前可读qrels仍由标注者保管。来源分组/精确SHA并非声学近重复或预训练未见证明，MUS-002质量/discovery-v0未完成。
