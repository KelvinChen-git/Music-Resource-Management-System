# MUS-027-R1-B：评分入口增量独立审核

- task / assignment_revision / owner：MUS-027-R1-B / 1 / b。
- status / verdict：review_completed / approve_scoped；2026-10-28（America/Chicago）。
- reviewed_sha：`2ed661daff6e66856cdef6a6789a9edea7a2dc5d`。
- comparison_base_sha：`a945927d45d982e7bda22cc7a84dce930787b52f`。
- assignment_source_sha：`7704051f9a844816174c710d09e6f92e5b23f0e7`（本轮固定入口发布同一revision任务卡的源码SHA）。
- ack_peer_feed_sha：`23497a7c2a43902fd90a71975463748aabb3b7ff`。
- branch：`review/MUS-027-B-rating-entry`；交付SHA见B feed根目录`handoff.json.source_sha`，不在同次提交自引用。
- 先claimed并回读后审核：source `3fef9253386576cc5de249ea525b626d985119d1` / feed `5d49036f212667e8bcb5e663a6d598e7f6573b73`。

## 结论与边界

准确单view增量和E2交互补充范围内未发现阻止接收的问题，限定批准。审查`ReviewWorkspace.vue`全部变更（14增/5删）：就近输入、空值/格式提示、输入与radio分别启用、aria关联和响应式样式；原judge/UTC/persist/恢复/导出处理未被改写。文件SHA256 `75703a7f5c35988719964f5fdf2730f3288755c2dc12fd5e16f7d5e236b5447b`与A声明一致。

B独立clone只新增本报告与自身latest，不改产品、依赖锁、API、schema、公共JSON、A台账或任务卡。026已接收，导入报告与B交付逐字节相同，SHA256 `4ee7231d470b66820eb28adf7cfa2c1bec9816b1d02607b9d34bd83d8afcea50`。N1开发浮层不在本卡，不重复026音频或旧完整矩阵。

当前A入口已推进至032，027原卡revision1仍assigned，所以本轮领取该准确旧实现；不把此批准外推A后续029评估、030诊断schema/UI、032收集器或033待办。A后续真实判断/语料进度仅按其文档读取，未访问其私有原件，不能再用历史“51全null”概括当前全部判断状态。

## 实际执行与证据范围

| 命令 / 范围 | B结果 |
|---|---|
| 固定Node22.23.3 `node --test web/src/utils/reviewPack.test.js` | exit0；8项通过，0失败/跳过 |
| 固定Node22/npm10.9.9，在`web/`执行`npm run build` | exit0；复用现有lock及依赖，未npm ci或升级；保留既有>500kB警告与npm升级notice |
| `python3 .local/b/runtime/fixture27.py` | exit0；独立构造4曲/2query/8候选E1元数据fixture，CLI build成功；未生成/读取音频或加载模型 |
| `python3 .local/b/runtime/run27.py` 最终 | `run-20261028-213730`，exit0/status passed；25项浏览器断言通过；两导出CLI分别exit0 |
| `git diff --check` / 源码、允许路径及锁核对 | 交付前通过，只两份B报告 |
| 开始及检查点 `python3 scripts/collab.py sync --account b` | exit0/fetched，上述A feed/任务修订未变；交付后另回读 |

25为最终一轮断言，不是25个真实HTTP场景，不与8项、A的17或旧31/30/37累加。前端为5174生产preview，真实Vue/Pinia/DOM、原生radio、localStorage、下载和WebCrypto；Chrome Headless Shell151.0.7922.34/Playwright，Linux私有single-process适配。

登录API和profile在浏览器请求边界各返回一次明确合成USER/id/token响应；实际生产user store与路由在此前端上下文运行，**没有Java服务或真实服务器JWT身份鉴权**。owner `270042`和候选ID都是测试占位。未知API或外部请求被阻止，实际无未知/外部/媒体调用，未接触A服务/账号/用户草稿。这里只验证卡允许的前端交互边界，不能称真实普通账号/媒体权限验收。

## 浏览器结果

- 空代号输入位于评分fieldset内且可编辑；fieldset本身未disabled，4个radio均disabled且未默认选中，旁边原因可见。输入通过aria-describedby关联具体提示。
- `_invalid`、中文、含空格值各显示1–64位/允许字符原因，aria-invalid=true，radio保持禁用；合法`test-b27`后4项立即启用、仍无默认评分。单填代号导出后全部8条人工四字段仍null，没有自动UTC时间或草稿判断。
- 鼠标选择3分，只对本条写入test代号与合法UTC秒时间，其余7条null。改成非法或清空代号后，整个已判包对象与之前完全相同，包括原代号/时间；既有选中3仍保留但不能新选。清除本条判断后四字段全部null；重新显式0分后1已判断/7未判断，0不等于null。
- 切候选保留当前输入代号，但新候选仍无分。原生Space、ArrowRight操作选择3；草稿位于当前owner+dataset键，2条已判断且不含模拟token。
- 刷新并重新导入原文件后，先保持8条null而非静默恢复；明确点击恢复后保留原0/3判断，代号输入仍空，下一次编辑必须填写。桌面导出为2已判/6null、0与3各1条、0人工区间。
- 390×844手机填写中文得到格式提示/禁用，改为`test-b27-mobile`后实际点击2分并导出，第一条变2、第二条3、仍6null；这份导出与桌面0/3版分开验证，不混称同一对象。
- 1440×1000及390×844的scrollWidth分别1440/390，输入、提示和选项均在同一框内，无横溢。手机输入左右52/338px，fieldset37/353px，实际控件可点击；两图已视觉查看。full-page截图固定播放器位置反映截图方法，不作为页面整体遮挡结论。
- 最终浏览器warning/error/pageerror均0。两份下载都由固定run CLI重建验证，identity_or_listening_verified=false；未判断null保持，全部匿名代号/分数是明确synthetic测试，不能称真人听音。

实际CLI参数为`review_pack.py validate --run-dir <fixture/run> --catalog <fixture/catalog.json> --report-sha256 e8b7a2dc564646f91862dfd9f819d766a28acd0bdd960c2fc8055ebec07cee05 --pack <desktop-export.json或mobile-export.json>`，两次均2query/8候选/2已判/6未判；桌面等级0/3各1，手机2/3各1。

## 保留的失败

`run-20261028-213540`与`run-20261028-213656`分别exit1/blocked，各23项完成+1项脚本误报：网络断言以substring `file`误把允许的`/api/auth/profile`归作媒体端点。实际两次仅合成login/profile、未知/媒体/外部请求均0。首次字符串替换尝试未命中、断言失败，随后一次重跑仍沿用旧条件；最终按完整API路径段更正检查后25项通过，未改产品或放宽未知请求阻止规则。前两轮完整浏览器输出/包/截图已分别归档，不改写成功、不累加检查数。前端进程三轮均停止，5174逐轮及最终再次确认释放；未启动MySQL/Java。

## 数据及本机指纹

合成pipeline `b27-synthetic-alias-v1`、伪run代码`c×40`、伪checkpoint `d×64`，内容SHA来自合成元数据字符串；不是实际编码/音频处理结果或新增真实模型/索引版本。dataset SHA256 `a7b799442a8b039d209c7a2788dff28aca5b99f96f2380bbd5b39fcebe55e695`。

证据在B忽略目录`.local/b/review-evidence/MUS-027-R1-B/`；私有工具/原日志/截图/导出未交给A，不声称A可据报告重算原始证据。

| 工件 | SHA256 |
|---|---|
| `node8.log` | `c4439da53ee0e2dce0cab16b3aa4f903d5ba0c1ecf9746d8bf7667d09e078ecb` |
| `build.log` | `5f0cabd024de3036427427b26ca361f74a17dfe14c90252987d58da8a369f262` |
| `browser-result.json` | `2dea2af424c961f1fea22075a36c581462ba5b89c3d9b2149292bd55c5c07172` |
| `desktop-export.json` | `8f749b5e4e892ccae8541934556bde472b3881e3e89bc33b2ee6e32f2bee5d90` |
| `mobile-export.json` | `d2195c6cfbc91cb8a66e420a631d2958238a2ab48d5cdfd04bca9ff1d5e64e17` |
| 最终`run-20261028-213730/result.json` | `ff9c24fb53fcbe316e2b4b09e7dc0e98a0f92da7651f3b684d1747bb28cdaab3` |
| `verified-evidence.json` | `de6d450e30b35f2533adcc720abec3d172858fe0b01637d1b958b6a83cd0d87a` |

## 交接与未执行

接口变化无，未修改产品或A总台账。未重新验收真实后端/媒体/音频控制/上传/完整权限矩阵、Java、CLAP/质量、人评、P95、模型比较或discovery-v0冻结，也未访问A后续真实118判断、新来源原件或原私有截图日志。未做真实移动设备/跨浏览器/读屏器体验；aria关联和原生键盘行为已按上述浏览器范围检查。

下一步A接收本限定批准，再协调后续明确任务；B不自行接管029/030/032或修改其源码。GitHub先任务分支、后collab/account-b顺序发布，非原子；交付SHA及回读由发布记录给出，发布不等于A接收。交付后两报告占用释放，无自建服务/端口占用、main合并或后台轮询。
