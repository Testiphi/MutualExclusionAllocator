# 小程序A账号与双服云车库：HTTPS只读交接

交付批次标识：20261105。整理日期：2026-11-06，Asia/Shanghai。服务器执行证据来自用户依次回传，step20未附完成时间戳，不据文件名反推执行时刻。本文可由用户转交小程序侧，不自动向其他对话派工。

固定机器材料：[同名JSON](MINI_ACCOUNT_A_READONLY_HANDOFF_20261105.json)。现有协议仍为 [A契约](MINI_ACCOUNT_CONTRACT_A_20261103.md)、[Global云车库契约](GLOBAL_PROFILE_CLOUD_20261103.md)，不另发明账号或车库协议。

## 已就绪与尚未验收

**网站侧A只读联网准备已完成**：`https://account-test.racepick.cn` 已接通实际HTTPS与独立服务，公网健康200、固定五份数据SHA/bytes、未认证门禁和原生头部拒绝通过。真实微信交换、真实账号登录、认证后的双服读取、网页/原生真实记录同步、显式保存/冲突/退出/身份变化及手机账号验收均未通过，不能用健康200或401代替。

当前服务 `enabled=true`、`cloud_writes=false`，仅隔离测试，不是正式账号接入。服务未开机自启；证书已签发、实际TLS/主机名/系统CA已验证，自动续期及Nginx后续加载尚未验证。新origin在微信合法request域名中的状态未核实；本网站侧任务没有操作微信后台、上传体验版/提审/发布。

## 固定来源

| 项目 | 值 |
|---|---|
| origin | `https://account-test.racepick.cn` |
| 原生A前缀 | `/api/mini/account/v1` |
| 该origin的访客前缀 | `/api/mini/v1` |
| 只读健康 | `/_account-test/health` |
| delivery_id | `7c5f53fc366b7af555214846` |
| 封存代码source_commit | `null` |
| source_base_commit | `bfcf97e1511ee3d418a1f558c30a3ba0148d5286` |
| 原候选ZIP SHA256 | `6c0ff251985638c62a232689a9aa3a3fd568544f2b8ad812e567e342bcef2648` |
| 原候选ZIP bytes | `11220353` |
| CANDIDATE.json SHA256 | `13545e697ca7dfcf0fb68f4f52e8b4003474c3accb4586419aaafd8fc096fe3b` |

base提交不是完整候选源码。包由显式文件清单固定，不能只检出bfcf97e便称同一交付；后续Git归档也不能倒改本包source_commit。原OCR封存35bd的source_commit=null和运行补件记录同样不倒改。本轮未提交推送合并。

五个共享模块仍匹配198999a。新服务没有创建或调用第二套OCR模型/队列；原网站、mini-test访客/OCR、正式数据及既有状态未因本次准备迁移或恢复旧库。

## 身份与同库边界

这个新origin使用**新独立GuestStore、原生账号状态与业务库**。网页和原生处理函数绑定同一个隔离业务Store；两服分开保存，Global包含OC和独立revision。源码及本地fixture已验证同库接线，真实账号跨网页/原生读写同一记录仍待验收，不能用两个null宣称实际同步完成。

沿原WechatVerifier做真实微信交换，但必须在**新origin重新建立父访客**。不能复用 `mini-test.racepick.cn` 的访客Bearer、旧wx.login code或旧session，也不能把账号token拿去旧OCR接口。旧OCR origin、transport、额度预约和草稿保持独立；不为账号验收再发图、恢复旧图或清掉旧OCR身份。

原生账号仍为rpa1账号Bearer，私有路径另带X-Account-ID；账号与访客令牌独立，网页Cookie/Origin/CSRF不桥接。服务端复核父访客、网页撤销锚、账号状态和实时角色；TTL至多3600秒且不晚于父访客。association仅session_only，不永久绑定微信身份。

账号页与双服车库继续复用完整镜像中的AccountClient、198999a ProfileStore；独立account-probe仅用于分阶段验收，不替代最终产品，不另写算法。

## 当前组件与状态

- business schema6、Global profile schema1、guest schema1、native account schema1实际准备；Global OC严格boolean、两服revision独立。
- `profiles.cn/global=account` 的能力来自固定features实现、真实Global组件schema与完整A组件初始化；认证后的profile响应尚未现场验证。
- native batches：A ready，B/C/D/E pending；`mail_mode=file`，image_policy disabled，OCR关闭。
- 新服务coverage_schema=0、global_score_schema=0：只加载A，成绩来源为固定JSON snapshot，不是正式活动成绩组件。**不要为补这两个0重跑coverage/Global score迁移。**
- 已由用户在服务器私下输入新密码，创建1个隔离普通玩家账号，file outbox本地消费一次性验证token，非真实邮箱投递验证。创建前后备份和独立恢复通过。用户自行保管隔离邮箱/密码，材料不包含凭据。
- 准备结束时认证会话0、两服profile行0、未用邮件token0、原生/微信身份未创建。step20后身份/车库/邮件/操作/schema行保持，只有门禁限流预算可能变化。

## 当前精确范围

| 方法与路径 | 身份/当前状态 |
|---|---|
| POST `/api/mini/v1/session` | 此origin的新真实微信访客交换；网站检查未提交code |
| GET `/api/mini/v1/snapshot?server=cn\|global` | 此origin访客Bearer |
| GET A `/session` | 访客或账号Bearer |
| DELETE A `/session` | 当前原生账号Bearer，保留父访客 |
| POST A `/auth/login` | 父访客Bearer，用户亲自输入隔离凭据 |
| POST A `/auth/reauth` | 账号Bearer+X-Account-ID |
| GET A `/profile?server=cn\|global` | 账号Bearer+X-Account-ID |
| PUT A `/profile?server=cn\|global` | 框架保留；当前cloud_writes=false，禁止在只读阶段发送 |
| GET A `/operations/{original_key}?action=login\|reauth` | 原父访客Bearer，仅查询原操作 |
| GET A `/operations/{original_key}?action=profile-save&server=cn\|global` | 账号Bearer+X-Account-ID，仅查询原操作 |

网页为同一origin的原账号/车库页面及必要静态资源；仅auth/me、login/logout、me/profile等白名单，Cookie/Origin/CSRF保持原语义。网页PUT同样被cloud_writes=false阻断。

公网注册、验证/重发/找回/重置、邀请、DELETE association别名、B–E、图片/证据/OCR、统计、任意网页/管理路径均未开放。操作者的离线账号准备不表示这些公网功能启用。

HTTPS精确Host、可信回环代理与实际客户端IP，原生Cookie/Origin/OPTIONS拒绝，no-store；JSON64KiB，独立API桶5r/s、burst10，静态数据不进入登录桶。应用原签发/登录预算保持；429带Retry-After:60，不保证日预算已恢复，不自动重发。未进行现场限流饱和测试。

## 固定运行数据

固定CN snapshot `593ecc7222ceea5856b2f576b4f5bca8`；Global snapshot `e29f52e7f81c3e337985bf05dedb7e88`；Global dataset `9b83ddd062a4d4b0c15d51dc0eed323aabb8e599e3e9544bc91714b70a7a4259`。这是隔离原生固定数据，不是正式活动成绩指针，不来自本轮维护工作簿。

| 文件 | bytes | SHA256 |
|---|---:|---|
| cars.json | 83653 | `ea42daedfdb73a4963e2e70c6cdf91deb29ae6bec5143b697e50d8c877961b17` |
| gauntlet_data.json | 225341 | `2e8bf6ba763a64f24cd1e93be0afbaca8c77e24efcb9a96812952de800b018b6` |
| cars.global.json | 29852 | `6d35da66c9c0d2d7335b3e80d6a7351bbc494911a5b1d8dab0a0c2137cbc9759` |
| gauntlet_data.global.json | 133918 | `79958b507b814fb0823e03aa8f97843fafe9b61a558c428336a4879587a33bd2` |
| global-data-manifest.json | 1866 | `7e38469bc6bd6de5498bc1e38c16898c0a34eddb86ead72d610e0e1883e6dbe6` |

## 分层证据与非秘密样例

Windows账号套件60/60、生产边界模拟8/8（SMTP mock）、前端27/27；独立断网Linux离线hash锁安装/pip check及打包副本共库/恢复模拟通过。这些不是微信/真实账号验收。

用户服务器回执已证明固定来源、离线运行时、真实非root UID/挂载隔离/内核资源限额、私有配置断网解析、完整A组件构造、HTTPS公网健康/固定数据/匿名门禁/原生头部拒绝、1个隔离账号准备及前后独立恢复。健康里的A ready只代表组件，不代表客户端或权限验收。

现场观察：无Bearer GET A session →401 `SESSION_REQUIRED`；无账号Bearer GET双服profile →401 `ACCOUNT_SESSION_REQUIRED`；均no-store。Cookie/Origin/OPTIONS被拒绝；排除路径GET为404。没有用真实账号登录、验证权限或查到认证后车库。

以下是**固定契约/本地fixture样例，非本次真实账号现场成功响应**：

```json
{"server":"cn","storage":"account","remote_supported":true,"revision":0,"profile":null}
```

```json
{"server":"global","storage":"account","remote_supported":true,"revision":0,"profile":null}
```

null表示未保存；合法已保存空车库是CN的`{"cars":[],"stars":{}}`或Global额外`"ocMap":{}`。当前PUT预期503 `ACCOUNT_CLOUD_WRITE_DISABLED`，本轮没有为验证这个错误而发送保存。密码错误401 `CREDENTIALS_REJECTED`不能清父访客；登录/再认证用原key恢复；退出/替换/撤销后旧结果不能复活。409 PROFILE_CONFLICT保留current/submitted两份；跨服key拒绝。404 OPERATION_NOT_FOUND不证明未执行，不能换新key重发密码、邮件或保存。

## 接收后的顺序

1. 保留客户端cloudWrites=false，先核固定来源、组件及数据绑定；新origin合法request域名状态待用户/小程序侧核实。网站侧不操作后台，不关闭校验走捷径，不添加图片上传范围。
2. 用独立account-probe transport在新origin获取新的真实微信父访客；保留旧mini-test/OCR transport及其状态，确认访客/账号身份分离。
3. 用户在客户端私下输入已准备的隔离邮箱/密码，只登录一次并保留原key；检查token类型、真实角色、期限和实际父访客association，不在报告中输出令牌/code/OpenID或密码。
4. 双服仅GET；确认GET/login不导入，保留本机草稿，不把错误/503当空库，不把两个null当真实同步已完成。不发送PUT。
5. 未知结果保留原key/action/server，仅查询原操作；恢复404也不自动重放。不持久化原密码或邮件token。
6. 只读证据通过后，再单列暂存、显式保存、重载、冲突、退出及身份变化的写范围；服务端cloud_writes仍false，不能自行声称保存验收通过。
7. DevTools与真实账号只读阶段之后再给用户手机步骤，不复测已通过的手机基础OCR、不上传/提审/发布。

本文及同名JSON只含固定来源、隔离状态、开关/schema、非秘密样例及分层证据，不含实际AppID/AppSecret、密码、Bearer、微信code/session_key/OpenID、邮件token、正式账号数据或私有备份。
