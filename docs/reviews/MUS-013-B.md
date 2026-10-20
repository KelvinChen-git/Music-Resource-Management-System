# MUS-013-R1-B：修复发现的增量复核

- task_id: MUS-013-R1-B；assignment_revision: 1；owner: B；集成负责人 / STATUS 写入方: A。
- reviewed_sha / base_sha: `c100fd6510fe1061396be16973a7560ed2b89e7f`。
- comparison_base_sha: `d7c9faa7c13ae8531fdd50f2e2d566cef1fa09ea`。
- assignment_source_sha / 补充证据来源: `d384a8fc66778ba24344f1ef19507db718872623`。
- ack_peer_feed_sha: `10503b986617fbd2c83e865c27605cd21c94eba7`。
- branch: `review/MUS-013-B-review-findings`；日期: 2026-10-19 America/Chicago。
- claim_source_sha: `0f49505b53810634dd18a3a18470dd12d9c6e0b0`；claim_feed_sha: `c8505d5f753f8daf17d802cf9969100ad9edad41`；先发布领取且已 sync 回读。
- task_status: review_completed；review_verdict: **request_changes**。
- runtime_supplement: **java_pass / database_http_blocked**；原审核时的DNS失败及后续修复分别记录，最终交付SHA以own feed为准。

## 结论

上一轮 R1 / R2 / R3 在本次固定源码中均已修复；profile 整实体回写安全字段也已改为显式可编辑列。A 提供的修复前 / 后真实结果可复核，不能再把三项旧问题描述成当前仍未修复。

本次新增一项 **P2 / R4：新回归脚本的异常清理失败会跳过临时管理员降权**。B 已调用实际脚本函数并替换 HTTP / SQL 传输，注入故障确认该控制流，不是纯粹猜测；没有在真实数据库制造残留账号。request_changes 针对任务卡第5项的清理保证，**不重开已经修复的三项产品缺陷，也不把 B 的环境阻塞当成代码失败**。

## 原发现及 profile 修复核对

| 范围 | 固定源码证据 | 本次复核结论 |
|---|---|---|
| R1 旧硬删除 | MusicController:41–45 先 requireViewer；MusicService:24–28 直接抛410，不再调用 repository.deleteById；MusicServiceTest 验证 repository 无交互 | 原绕过在源码中关闭。当前有效账号410，匿名 / 失效401，锁定403；标准软删除未改 |
| R2 createUser 头像 | UserServiceImpl:151–159 重新 requireViewer / ADMIN，hasText avatar 在 insert 前400，空白归一NULL；UserController:87–88 透传 ResponseStatusException | 原新账号头像注入关闭；无头像创建路径保留。锁定管理员拒绝、新头像拒绝和空白头像归一有新增测试 |
| R3 未知结构迁移 | upload_ownership_migration.py:26–70，先精确表名和必要上传列 / 主键 / 自增，再判断版本与 owner；重入验证 nullable / NULL default / 非生成及非唯一 BTREE 索引列序 | 原“同数量换表”反例被首个只读查询拒绝，B 重放后写语句0；V001/V002 均逐字节未变 |
| profile 写列 | UserServiceImpl:344–349，userMapper.update(null, LambdaUpdateWrapper)，只 set name / avatar / updated_at；UploadOwnershipHttpTest 新断言 SQL set 不含 role / is_locked / password | 原完整实体覆盖安全字段的路径关闭；测试为 SQL 写列边界，不能冒称真实并发测试 |

Java 路径均在 `music/src/main/java/com/taffy/music/` 下；Python 路径在 `scripts/` 下；以上位置针对 reviewed_sha，非 A 文档分支最新 HEAD。原报告 `docs/reviews/MUS-012-B.md` 保持原文，不改写历史结论。

## R4 / P2：finally 中一项清理失败，后续管理员降权不再执行

**位置：** `scripts/review_findings_smoke.py:51–55,94–96`。这是本次新增脚本，不是旧产品 API 的另一个授权漏洞。

脚本先创建三个合成账号并将其中一个提升 ADMIN。退出时 finally 顺序执行“删除绕过测试用户”和“临时管理员降权”。第一条 query 抛异常会直接退出 finally，第二条 UPDATE role='USER' 完全不被调用；另外提升操作尚在 try 之外。普通成功路径的清理和 A 的两套通过结果，不覆盖这里的故障分支。

**触发 / 最小重现：**

1. 替换实际模块的 urlopen / subprocess.run，前三次合成注册及对应登录成功，SQL 提升返回成功。
2. 在提升后的第一条业务 HTTP 请求注入异常；在 finally 的 DELETE FROM users 清理查询注入一次独立失败。
3. 调用实际 review_findings_smoke.run('b', mode='verify', mysql=...)，收集 SQL 输入。
4. B 观察到仅两次 SQL 调用：提升 ADMIN、失败的清理 DELETE；没有 role='USER' 的降权尝试，向外抛 Synthetic fixture SQL failed，原 HTTP 错误也被覆盖。

可在自己的隔离 checkout 以如下纯替身传输复现，不连接 HTTP / MySQL：

```python
import sys, json, subprocess
from unittest.mock import patch
sys.path.insert(0, "scripts")
import review_findings_smoke as m
calls, created = [], 0
class Reply:
    status = 200
    def __init__(self, data):
        self.data = json.dumps({"code": 200, "data": data}).encode()
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.data
def http(req, timeout):
    global created
    if req.full_url.endswith("/auth/register"):
        created += 1
        return Reply({"userid": created})
    if req.full_url.endswith("/auth/login"):
        return Reply({"token": "synthetic-test-token"})
    raise RuntimeError("injected HTTP failure after promotion")
def sql(cmd, **kw):
    text = kw["input"]
    calls.append(text)
    return subprocess.CompletedProcess(cmd, 1 if text.startswith("DELETE FROM users") else 0,
                                       stdout="", stderr="injected cleanup failure")
with patch.object(m, "urlopen", side_effect=http), patch.object(m.subprocess, "run", side_effect=sql):
    try:
        m.run("b", mode="verify", mysql="/synthetic/nonexecuted/mysql")
    except RuntimeError:
        pass
assert len(calls) == 2
assert "role='ADMIN'" in calls[0]
assert calls[1].startswith("DELETE FROM users")
assert not any("role='USER'" in text for text in calls)
```

B 使用本 clone 已存在的 slot B 配置，read_env / validate 未替换；上面两种传输全部由替身执行。**这是实际 Python 函数的异常控制流复现，不是真实数据库中已遗留管理员的观测**。预期即使删除用户失败，也要独立尝试恢复合成管理员角色；数据库完全不可用时不能保证降权成功，应明确记录未清理 fixture 并返回失败，而不是跳过尝试。

**影响：** baseline 会如实失败，不会假报11项通过，但可在持久开发库留下已提升的合成管理员；反复失败会累积残留，违背本卡要求的脚本隔离 / 清理边界。只涉及隔离开发脚本，没有证据表明真实用户被提升或生产数据被操作。

**最小建议：** A 在同一小脚本内将提升与整个运行置于保护范围，用独立或嵌套 try/finally 保证删除失败也尝试降权，并保留各项清理错误信息。给 HTTP 故障、清理 DELETE 故障、降权故障增加无网络的替身传输回归；断言降权尝试不被前一项失败跳过、仅使用本次随机合成 ID / email，且仍返回非零 / 不发布 passed。无需改业务 API、schema、依赖或基础设施。

## 脚本与隔离检查

- review_findings_smoke 的普通路径使用 slot 白名单、随机合成账号 / 资源；observe 明确返回 observed，verify 才返回 passed。verify 的11项由实际 check 调用产生，baseline 同时要求 status=passed 和 check_count=11；正常成功路径的测试用户删除与管理员降权具备随机 email / ID 限定。R4 是失败路径的清理缺口。
- migration_guard_probe 使用新 /tmp 私有目录、全新 datadir、唯一 music_probe schema、指定 Unix socket、--no-defaults / --skip-networking / --mysqlx=0。客户端只指定此新 socket，不连接既有库；DROP 限于新实例自己的 schema，finally 只 terminate / kill 所创建的 Popen 对象，退出后清理自己的临时目录。未发现接管 A 进程或修改已有库的路径。
- 临时库脚本的8项计数与 baseline 对 status / count 的检查一致：升级及 NULL legacy、幂等、换表拒绝、拒绝后结构保留、缺列、登记中断恢复、错误默认、唯一索引。缺本机 mysql / mysqld，B 未启动该实例，不能把静态检查和 --help 记为8项真库通过。
- 前端、pom、依赖锁、V001/V002 SQL 相对比较起点均未变化；按卡不重新安装依赖或重复前端构建。

## 仍待并发任务验证的交错风险（非本次实跑故障）

显式写列修复了 profile 覆盖 role / is_locked / password 的风险，尚不代表所有头像绑定交错安全。UserServiceImpl:325,335–349 仍以首次读到的 user.avatar 判断“值未变”并跳过 requireAvatar，但只要请求有 avatar 字符串，最终仍 set avatar。

具体待测交错：T1 读到旧头像 A 并请求同值 A，暂停；T2 将头像换为 B 并提交；T3 删除已无引用的自有上传 A（逻辑删除）并提交；恢复 T1，它因旧快照相等跳过上传行锁 / deleted 检查，再把 A 写入 users.avatar。建议在 A 已计划的多连接任务用屏障验证最后的 avatar / deleted 状态，再决定锁顺序和同值更新规则。此条是源码推断，**未观察到真实竞态结果，不将其混入本轮11项HTTP或新的已复现R4**；不要求B擅自扩展实现范围。

## B 原审核检查点的执行与未执行项（后续补证见下节）

环境：独立 Linux clone / slot B；OpenJDK17.0.20（javac 不在 PATH），Python3.12.14。没有使用 A 的 macOS 工作树、账号或数据库。运行代码为 reviewed_sha；领取提交只新增 own latest。

| 命令 / 检查 | B 实际结果 |
|---|---|
| python3 -m unittest discover -s scripts -p 'test_*.py' | exit0，28 tests，0失败，2.329s |
| music/ 下 sh ./mvnw -B -ntp test | exit1，Spring Boot3.4.4 parent POM / repo.maven.apache.org DNS 失败；Java实际0项，未编译 |
| py_compile：迁移器、新两个探针与 baseline | exit0 |
| migration_guard_probe.py --help；review_findings_smoke.py --help | 各exit0，仅命令入口 |
| 原R3合成元数据回调重放 | 拒绝同数量换表；只有首个SELECT，0写入；从V001 SQL独立提取11表名与保护集合一致 |
| R4替身HTTP / SQL故障探针 | 已复现“清理DELETE失败后未尝试降权”；实际函数调用，非真库测试 |
| A归档与源码一致性 | 12份新原始JSON及1份旧observe结果核对通过，详见下节 |
| git diff --check 与路径审计 | 发布前执行，仅两份允许B文档 |

mysql / mysqld / docker 均缺失，故 B 的真实迁移8、HTTP11、媒体144 / 上传65 / 两条smoke、Java317、事务故障 / 并发 / 跨进程续传均 not_run / blocked。没有反复执行相同 Maven 失败命令；无前端改动，因此本轮不重复 Node6 / build 的旧通过项，也不把旧 B 结果当成本轮执行。

原始本机证据在忽略目录 `.local/b/review-evidence/MUS-013-R1-B/`。Python日志 SHA-256 `bd9c136b4ca83dec14fbb8f68b81b5876425cbd503a28c40666393994c0de147`；Java失败日志 `c2bbf6b63d97dece1fe1fa5a56a01150d1ac0432b34470ca4f455cd12b7a68fb`；R4探针JSON `394a5ebe570bdee77726bd3d32f433aad7410221ef650f7dde707ea9ea1343e5`；R3回调JSON `4333a5859e53574491e248a0a7d50bdb6d5068fe7bc5f1b44ad615b82b4fa59d`。

## A 证据核对（不计为 B 执行）

按 assignment_source_sha 读取 MUS-013 验证正文、results / live-results、修复前 observe 和两套共12份原始 JSON。12份归档字节哈希逐份等于 live-results 的对应 .log 哈希；旧observe哈希与 results 一致。suite总和为317；两套运行源码分别为 da060d520800f61ec096779967236022efdf8aeb / c100fd6510fe1061396be16973a7560ed2b89e7f，相对 reviewed_sha 仅文档有差异。

每套证据含：直连 / 代理各13功能+4安全、144唯一媒体元组+8附加、上传65、临时库8、修复HTTP11。媒体状态逐格核对，计数36×401 / 72×404 / 24×200 / 12×206。修复HTTP observation 均为旧DELETE410、资源行1、raw404，createUser400、插入0、匿名图片401；与旧observe的204 / 行0 / raw200 / 重绑定成功及头像匿名200形成明确前后对照。未把 observe 当 verify。raw / count / hash一致只能证明所归档覆盖，不能证明 R4 异常清理或并发已跑。

未读取 A 全部原始 Java / 后台日志，故未独立重算其后台日志哈希或观察“无SQL异常”；这些仍为 A 汇总事实。B 没有获得真实模型 / 数据 / 索引，也没有搜索质量或性能结论。

## 后续补证：B 本机 Maven 网络已修复，Java317独立通过

用户明确要求修复B的Maven DNS阻塞后，B只调整忽略目录内的本机配置。没有改pom、wrapper、依赖锁、业务代码或A配置；本节补充新运行事实，不把上节曾经执行0项的失败记录改写成当时已通过。

根因：本执行环境提供HTTP/HTTPS代理，普通curl经代理访问Maven Central的准确parent POM返回200；Maven没有自动采用环境代理，原先直接解析repo.maven.apache.org而失败。另外代理端口随执行环境调用变化，跨命令写死一次settings端口会connection refused。修复为在同一调用内从当前HTTPS_PROXY/HTTP_PROXY解析代理，生成B私有settings，再启动Maven；依赖缓存也独立置于.local/b/maven/repository。全局~/.m2/settings.xml不变。

实际命令（仓库根目录）：

```bash
python3 .local/b/maven/run.py --with-test-agent -U test
```

Maven3.9.9 / OpenJDK17.0.20，采用项目现有Byte Buddy1.15.11依赖的显式javaagent，不新增或升级依赖。**exit0，13类 / 317 tests，0 failures / 0 errors / 0 skipped，BUILD SUCCESS，Maven耗时43.513s**。已直接读取13份Surefire XML求和，不是复制A的317数字。源码为ff23271833631305524022924d46daaacfc02a64，与本卡reviewed_sha c100fd6相比仅B报告文档不同，运行实现一致。包括MediaAccessHttpTest155、UploadOwnershipHttpTest49、UploadIntegrityServiceTest23等既有回归。

本机日志.local/b/maven/test-runtime-proxy.log的SHA-256：b3840bc1c41bcfe0ff7180d7f383a0574239a247a29f0f49b102f96c9da2de11；机器汇总verification.json与Surefire XML保留在B私有目录。373份POM、164份JAR已缓存；随后独立执行python3 .local/b/maven/run.py -o validate，exit0 / BUILD SUCCESS（0.219s），确认缓存模型可离线读取。无需手改系统DNS或切换第三方仓库。

可复用入口在本机.local/b/maven/run.py，SHA-256为3c35bec0dac762dd95d7d83a41a9c3c36e428814ca5a83524446f247822c5313。该私有文件不作为新增公共脚本提交；在新B工作区需要重建时，将下面源码保存到相同相对路径（先建立已ignore目录）即可。代理在每次调用中重新读取，不复制上一会话的端口；--with-test-agent针对当前冻结依赖版本，依赖基线变化时须重新核对。

```python
#!/usr/bin/env python3
"""Run this clone's Maven with the current environment proxy and a B-only cache."""
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as E

state = Path(__file__).resolve().parent
root = state.parents[2]
proxy_url = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy') or os.environ.get('HTTP_PROXY')
settings = E.Element('settings', xmlns='http://maven.apache.org/SETTINGS/1.2.0')
if proxy_url:
    value = urllib.parse.urlsplit(proxy_url)
    if value.scheme != 'http' or not value.hostname or value.username or value.password:
        raise SystemExit('Expected the environment HTTP proxy without embedded credentials.')
    proxy = E.SubElement(E.SubElement(settings, 'proxies'), 'proxy')
    for key, text in {'id': 'music-b-runtime-proxy', 'active': 'true', 'protocol': 'http',
                      'host': value.hostname, 'port': str(value.port or 80),
                      'nonProxyHosts': 'localhost|127.0.0.1|[::1]'}.items():
        E.SubElement(proxy, key).text = text
E.indent(settings, space='  ')
path = state / 'settings.xml'
E.ElementTree(settings).write(path, encoding='UTF-8', xml_declaration=True)
path.chmod(0o600)
arguments = sys.argv[1:] or ['test']
if '--with-test-agent' in arguments:
    arguments.remove('--with-test-agent')
    # The existing Spring Boot 3.4.4 test dependency graph uses this agent.
    agent = state / 'repository/net/bytebuddy/byte-buddy-agent/1.15.11/byte-buddy-agent-1.15.11.jar'
    arguments.insert(0, '-DargLine=-javaagent:' + str(agent))
command = ['sh', './mvnw', '-B', '-ntp', '-s', str(path),
           '-Dmaven.repo.local=' + str(state / 'repository'), *arguments]
print('Using current runtime proxy and B-only Maven settings/cache.', flush=True)
raise SystemExit(subprocess.call(command, cwd=root / 'music'))
```

Java编译/单测的DNS阻塞已解除；真实MySQL、临时库迁移8、TCP/HTTP11、并发/事务故障/跨进程续传仍未由B执行。单元/MockMvc通过不等于真库验收。**R4脚本清理问题的request_changes保持不变**，本次环境修复不修改审核对象或冒充A已修复R4。

## 交付与下一步

仅改 `docs/reviews/MUS-013-B.md` 和 `docs/collaboration/account-b/latest.md`。接口变化 none；不改业务代码、旧B报告、SQL、契约、依赖锁、A台账 / 派发卡 / feed；无 main 推送、合并或集成角色移交。

领取原生 publish 本次 exit1、内部 git push128，已使用 GitHub 插件先核验源分支再快进发布 own feed 的顺序备用路径，非原子推送。领取已 sync 回读；最终报告沿同一路径，以最终 B handoff.json 的 source_sha 为准，不冒称终端认证通过。先前不同元数据的本地提交保留归档分支，不冒充远端SHA。

A 下次sync接收并记录准确ack，串行更新STATUS；将旧R1/R2/R3与profile写列修复标明已复核，针对R4安排小脚本清理修复及无网络负例，再派发精确新SHA的增量检查。后续并发 / 进程恢复继续由A协调，不把已修复项反复重做。本检查点发布后释放两份B文档活动占用，B仍为唯一写入方；无实现路径占用。后续按固定入口、task_id+revision去重领取，无后台轮询。
