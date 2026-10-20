# MUS-019-R1-B：Sonora 独立审核

## 结论及准确基线

`review_completed / request_changes`。确认两个P2回归：R1手机列表长标题撑宽页面；R2管理员按用户名/邮箱查音乐时丢失筛选。请A修复后按新准确提交派发增量复核，不据本报告批准整个UI。

- task_id / assignment_revision：MUS-019-R1-B / 1；owner B。
- reviewed_sha：`f68b7fbba63ea58ad10dfe326d0197d1cc6b15ce`。
- comparison_base_sha：`f3b0da1e97113d28c81aa49be61c5cbcc49eebce`。
- assignment_source_sha：`c19b64833b78a2cd958959b77a1c9703f2fc9281`。
- ack_peer_feed_sha：`a7c8d9c148f42e8b023070b1d550ad504a731ed7`；完成前sync仍为该feed。
- 分支：`review/MUS-019-B-sonora-app`。
- 首次claimed已发布：source `74804ada8ceb8d93e65b7f9408581cf7baeabf33` / feed `fdcb27f43928296ad098d9621c7a1d0002c4c400`。
- 仅写本报告和`docs/collaboration/account-b/latest.md`。未改业务、检查脚本断言、A总台账/任务卡、API、schema、依赖锁或main。

MUS-017已经完成；A本轮确认读取其latest，完整报告正式接收及E1/E2由A另轮处理。MUS-016导入器不在本次审核范围。

## R1 / P2：手机列表不能收缩长标题，收藏控件被推出视口

位置：`web/src/styles/sonora.css:2`中`.listmode .album-info{padding:0;flex:1}`，以及`web/src/views/SonoraLibrary.vue:94–98`的列表信息/收藏控件布局。

复现：自己的真实账号拥有正常MP3资源及一条标题为`B19 `加9次`LongTitleWithoutSpaces`的合成元数据。390×844视口进入/music，选择“列表视图”。最终原源码浏览器实测innerWidth=390、document.documentElement.scrollWidth=1464；长标题整行伸出，同行收藏按钮随之移到右侧视口外。390px封面网格及1440px桌面网格分别无整页横向溢出，不能外推列表也通过。已目视检查原始mobile-list.png。

原因：`.album-info`作为flex子项保留默认min-width:auto，内部标题的最小内容宽度阻止收缩；已有按钮ellipsis不足以约束外层flex项。影响正常长歌名的手机浏览及操作，不涉及权限提升。

建议：为列表信息flex项和必要的标题容器明确`min-width:0`及可收缩宽度，保持标题省略/换行策略；验证收藏按钮仍可见可点。不要仅用页面级overflow-x:hidden遮住超出的交互。B未实施或验证建议补丁；请在长无空格标题的390列表、网格、桌面及播放器场景做增量回归。

## R2 / P2：保留的管理员用户页跳到新曲库后丢失用户名/邮箱筛选

位置：新增路由替换`web/src/router/index.js:51–54`；`web/src/views/SonoraLibrary.vue:44`只把keyword传给getMusicList；现存调用点`web/src/views/admin/user/index.vue:648`和`:656`仍分别导航`/music?username=...`、`/music?email=...`。

真实复现：新临时库3个合成账号，owner有25条目录记录，other无任何资源。完成测试中仅软删除本轮owner的一条资源后，管理员可见总数24。管理员用户页选择other的Actions → Search Music (Username)，再单独选择Search Music (Email)：

| 入口 | 带准确筛选参数的同账号真实GET /music-resources/list | 实际新页面 |
|---|---|---|
| username | HTTP200/业务200，total=0 | URL有username，发出的列表请求却无该参数；total=24、首屏8张 |
| email | HTTP200/业务200，total=0 | URL有email，发出的列表请求却无该参数；total=24、首屏8张 |

原MusicListView的store会解析这些管理筛选；/music改为SonoraLibrary后，同名导航没有同步迁移。两个调用点虽未改，其目标路由本次变更产生了明确功能回归。影响管理员按指定用户定位资源的准确性；管理员本来就能查看全库，不能描述成越权泄露。

建议：将这两个管理查询入口导向`/manage/music`并保留query，或明确处理兼容深链；保留管理员边界。补零资源目标与两个不同owner的username/email导航检查，验证请求带正确参数、页面不显示别的owner结果。不要把DemoCatalog仍适用的keyword入口一律改走管理页。B未修改这些实现。

## 已核对的源码边界

审核范围为基线至目标的19文件。新/music、favorites/recent/artists保留requiresAuth，原/manage/music与上传/分类/标签/回收站/个人资料入口可达；管理员路由requiresAdmin与导航角色判断未放宽。原/files菜单也是管理员专属，未将其菜单变化误报为普通用户功能丢失。

新App不再启动旧musicStore；旧store监听已移到方法定义之后且仅处理/manage/music。准确新版本带keyword直达管理页已实跑，无声明前调用错误；离开该路由的监听有显式边界。R2是另两个旧导航未迁移，并非该keyword修正无效。

所有新播放调用createMusicUrl(id,true)，后续fetchMedia限制/api/、从当前存储取JWT、no-store、redirect:error。旧管理注入的playUrl未直接喂给audio，最终也由新store按id请求。代次保护、旧Blob释放、换号reset和分账号收藏/历史均有既有5组检查和本轮部分真实场景证据。收藏/历史只保存ID，进入页面重新请求详情；授权来源链接限制HTTPS与白名单host，SVG标题/artist转义，未改后端/API/schema/包锁。

## B独立命令与通过结果

在B独立clone执行Node22.23.3/npm10.9.9：

| 命令 | 结果 |
|---|---|
| web目录`npm ci` | exit0，原锁SHA256保持；244包安装 |
| web目录`npm run build` | exit0；仍有>500kB chunk告警，未作为构建失败或擅自升级依赖 |
| `node web/scripts/verify-sonora-player.mjs` | 原字节5组全部通过，真实Vue/Pinia、账号/媒体边界为替身；非真实HTTP音频 |
| `node --test web/src/utils/media.test.js` | 原字节6项通过，0失败/跳过；非浏览器全链路 |
| `git diff --check` | 通过 |
| `python3 .local/b/runtime/run_mus019.py`（私有运行器） | 最终exit0、status=review_findings，26项预期浏览器行为通过，2项P2共3条失败观察 |

前四项执行HEAD是claimed提交74804ad；已用Git对象校验其web树与固定目标完全相同：`9b3a595bfc32197c9b8854fc07768ace2a82d782`。package-lock SHA256 `8df2bc2e97e9743265a30e11c52518ade9d8f1fdebffead45bbe508cc92b7980`，未变。B的npm ci日志没有输出A原先59项audit结果，不能宣称本轮重算其安全通告。

真实浏览器最终run `baseline-20261020-163739-11`。新临时clone直接checkout准确f68b7fb，新slot B原生MySQL8.0.41、JVM、B构建产物与本地代理、Chromium151.0.7922.34。原A/B服务及20首演示不请求、不复制、不修改。

26项通过：匿名保护路由；真实登录；20条分页首屏8、展开16/20并加载到25且去重；已加载风格/名称排序；SVG无脚本节点；真实合成MP3播放；SPA切页保持与最近播放；收藏重取详情；详情metadata；关键词与空结果；旧管理keyword直达及鉴权播放；上传页面；歌手20条官方链接；1440/390网格几何；手机菜单导航关闭；退出移除audio；换号收藏隔离、原账号重登保留；实际被拒的持久ID隐藏；无未捕获pageerror。R1手机列表未通过，R2两入口未通过，不称全部UI验收通过。

主曲库音频实测duration=24、currentTime=0.31257、paused=false、error=null；旧管理也成功启动。两次媒体请求均为本地5174的/api/music-resources/1/file?pay=1且含Authorization，仅记录布尔值，不保存JWT值。实际音频由ffmpeg生成24秒440Hz正弦波，非真实歌曲或听感评估。

数据为3个合成账号、1次真实普通HTTP上传/metadata登记，加24条直接SQL目录fixture用于分页和长标题，合计25资源。没有将24条SQL插入算成24次上传验收。另只删除本轮一个自建资源；为了验证拒绝缓存，向other自己命名的localStorage写入一个其无权读取的资源ID，再重新进入favorites，真实详情拒绝、页面隐藏；未以另一账号元数据快照回退。

既有后端仍允许所有者读取其软删除资源的详情（实测HTTP/业务200），本轮没有改其契约。因此不把该场景冒充“拒绝后的缓存”，也不宣称软删除收藏一定消失；真正拒绝ID场景使用上述无权限账号。

## 失败运行、私有适配与证据

保留全部8次前期exit1/blocked运行；只修私有探针的误期望、等待与歧义选择器，没有改仓库检查脚本或断言。最终通过检查不与重试相加。

| 前期run后缀（均baseline-20261020-） | 已完成检查 | 停止原因 |
|---|---:|---|
| 162749-23 | 3 | 私有探针误期望第二次本地展开显示24；实际本页只加载20 |
| 162828-11 | 4 | networkidle不是SPA业务完成条件，过早采样分页 |
| 162944-11 | 6 | 同上；临时“pagination R1”标记撤回，真实第二页响应21–25正常，随后最终DOM也显示25 |
| 163058-11 | 8 | /music同时有品牌和菜单链接，私有选择器歧义 |
| 163227-11 | 9 | 队列和详情两个drawer导致私有选择器歧义 |
| 163324-11 | 20 | 已复现最终R1；手机菜单关闭需等待route/aria状态 |
| 163509-11 | 24 | 已复现R1；误期望所有者软删详情必被拒，既有后端仍允许 |
| 163636-12 | 25 | 已复现R1；管理员隐藏dropdown重复菜单选择器歧义 |

最终163739-11单独完成26检查并捕获R1及R2两个入口，exit0仅表示探针完整执行，结果仍review_findings/request_changes。旧临时pagination标签与最终长标题R1不是同一发现。

沿用B私有Linux MySQL/JDK工具路径、现有Maven缓存/ByteBuddy和每进程代理settings；受管环境Unix socket不支持，bootstrap用loopback TCP，未改业务SQL/schema。可变库/上传状态位于单次exec的原生/tmp，停止后复制不可变证据。每轮finally尝试降权自己生成的admin并停止自己的进程；最终确认3308/8081/5174全部释放。Playwright CDN首轮返回195字节HTML导致下载失败；改用官方Google存储同版本ZIP后成功，未改项目依赖。下载SHA256 `3cfc2bd00d1bafcf8a68dc74c9c92bb7150ddc8d26ade948a776316e1cec4f14`。

B截图环境缺中文字体，截图/DOM检查仅支持结构、几何和溢出结论，不声称中文排印/像素一致；视口切换时的过渡帧不作为侧栏产品缺陷。长标题R1为独立Latin文本的实际布局溢出。浏览器存在预期受拒请求提示及Node运行器警告，“无未捕获pageerror”不等于历史日志从无warning。

私有证据目录`.local/b/review-evidence/MUS-019-R1-B/`未随两报告交付，A不能声称自行重算其原始日志。关键SHA256：

| 文件 | SHA256 |
|---|---|
| frontend-checks.json | `64f692a39247dd497dab2c11d9295f08951402a029f4178bcb0b611897f67340` |
| npm-ci.log | `ddbe71b36b8eddec20ba8ff1f592b32d2e34752d890f5f7d09ae795254a5b3e6` |
| build.log | `460dd9a5ecb3e3c1b056dccaeafeda03576507f4db93423b7d76a7a1cf9c464b` |
| player.log | `558e46549fd9815db7592bd057b785b3b3fb398da62ea68acfc43bc2b0334a02` |
| media.log | `841b26d86e74c9f3f99dbbabf5d3486519a8d5ec3c63c2aa44c7fe8bc95f9e51` |
| baseline-20261020-163739-11/browser-result.json | `4a282160e08c4bc71b4b7080efb82df9925a0ef101a1ddfd7eb24034dda24646` |
| baseline-20261020-163739-11/result.json | `e0f958ee5275c77cc1fd07deb989fc7101eddb09d0a3a609b52c63f273fc7f1f` |
| baseline-20261020-163739-11/mobile-list.png | `223cc273e8d6db82388addabc173f24b9fdcff9ec20efa6bb76b1c428156935b` |
| verified-review-evidence.json（含各轮/适配源码哈希） | `2919820e8f0a3f7bacde7f74b04872f2fb06e83008747869c1f8c84cc4951191` |

## 交付与下一步

任务/owner/分支/基础/审核SHA见首节；最终交付SHA在collab/account-b的handoff.source_sha，只有两报告路径变化。接口变化无；数据版本为本轮临时fixture，音频SHA256 `2abede801159ea9fe8435d17e5f3b57d7db7bd6b1ea540598a2c586a943e0313`；模型/索引无变化，无多模态检索实现或质量指标。

未执行：无关Java/Python全套；浏览器完整上传/续传及管理员创建编辑删除等写入；全部角色场景；跨设备收藏；真实音乐质量；生产部署、故障恢复或检索验收。浏览器上传仅检查页面，普通文件上传发生于自建fixture准备阶段。

R1/R2交A协调最小修复及新准确SHA增量复核；A串行更新STATUS，B不抢改源码。两报告占用释放，main未合并。原生Git写凭据仍未配置，使用已授权GitHub插件先源码分支再B feed的顺序备用路径，非原子；发布后回读源树、两文件feed及哈希。发布不等于A已接收，最终发布状态见B交接。
