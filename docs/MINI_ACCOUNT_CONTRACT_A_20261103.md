# 原生完整镜像 · A批账号、会话与车库协议

2026-11-03。用户将范围扩大为个人主体原生镜像网站全部外观/功能，不用web-view；旧“四项V1”仅为历史，不再作为删减理由。本文固定A批**后端端口**，不代表对应小程序页面已验收。B/C/D/E及正式主页presenter继续分批，清单见 MINI_MIRROR_ROLLOUT_20261103.md；未固定的接口客户端不得猜测。

本批不修改五个共享模块198999a。保留c26a708交付的 `/api/mini/v1` 访客/快照/OCR契约，不将访客权限静默升级。源码提交/逐文件Git blob与SHA见本批交付回执。没有部署、真实账号迁移、生产写入、外发邮件/通知或微信后台操作。

## 两种身份与固定前缀

新增 `/api/mini/account/v1`。它是可独立关闭的账号命名空间，schema_version=1；不是修改旧访客schema。配置没有account_state_dir时所有此处路由404 NATIVE_DISABLED，旧访客路由原样工作。

- **微信访客Bearer**：仍来自 `/api/mini/v1/session`，用于快照/OCR及本批注册/登录/验证/重置等入口。不能读写账号车库或声明角色。
- **RacePick账号Bearer**：形如 `rpa1.<opaque>`，只在用户明确提交邮箱/密码、通过同一网站校验后签发。不使用网页Cookie，不给客户端Cookie/CSRF。不能把这个token用于旧访客接口；客户端按路径保留两个独立的内存transport。
- **关联**：仅本次会话关联，不建立OpenID↔user_id永久绑定，不按邮箱文字静默建号/合并。注册是单独、明确的用户操作。退出/DELETE association仅撤销当前原生账号关联，保留原微信访客及本机草稿；没有永久绑定可静默解绑。

除guest认证入口外，私有读写发 `Authorization: Bearer <账号token>`，并发 `X-Account-ID:<当前actor.id>`；GET/DELETE session不强制该头，token本身仍绑定唯一actor。其他私有路径缺头或不一致401 ACTOR_CHANGED，防止切账号时迟到请求进入另一账号。所有原生路径拒绝Origin/Cookie/OPTIONS，不全局放宽网页门禁。网站Cookie、Origin、CSRF、手动保存及原请求路径不变。

## 账号会话与权限

成功登录200：

```json
{
  "schema_version":1,"session_kind":"racepick_account","token_type":"Bearer","token":"rpa1.<opaque>",
  "actor":{"id":"server-user-id","email":"own-email","verified":true,"role":"player"},
  "expires_at":1793000000,"authenticated_at":1792996400,
  "association":{"kind":"session_only","persistent_binding":false,"guest_identity":"server-identity"},
  "features":{
    "website":{"coverage":true,"contributions":true,"feedback":true,"notifications":true},
    "profiles":{"cn":"account","global":"account"},
    "authentication":{"mail_mode":"file","mail_token_ttl_seconds":1800,"persistent_wechat_binding":false,"reauth_max_age_seconds":600},
    "native_batches":{"A":"ready","B":"pending","C":"pending","D":"pending","E":"pending"}
  },
  "high_privilege_writes_ready":false
}
```

示例值仅示意，角色/开关来自服务器。role为player/admin/superadmin；未登录/访客actor=null。website开关是现有服务器组件状态，native_batches是本批API交付状态；它们不代表页面移植/真机验收，也不允许客户端绕过权限。令牌、密码只在必要的进程内存，不进URL/日志/本机持久存储/仓库。所有时间为Unix整数秒。

原生账号有效期最多3600秒且不晚于父访客会话；不滑动续期。每个访客同时一个当前账号：同一访客显式登录另一个账号/再认证，会撤销该访客旧原生账号token及其服务端撤销锚；其他设备/网页会话不因此退出。每次请求复核原生会话、父访客有效期/撤销、网站账号停用和实时角色。密码重置、网站“全部退出”、角色变更等既有撤销机制会使原生token失效；不缓存管理员身份作为权力来源。

网站sessions里仅创建本次登录的撤销锚，客户端拿不到该Cookie；独立原生状态只存锚的哈希与账号/访客关联。身份传递使用服务器创建的每app私有对象标记及上下文，任何HTTP头/正文都不能声明这个身份。账号权限、邀请码、密码哈希、邮件和车库CAS仍执行原网页处理函数。

GET `/session`：访客token返回session_kind=wechat_guest、actor=null及功能状态；账号token返回上述会话信息但不重新输出token。无有效身份401。客户端每次恢复/切服/权限变化重新读取；私有缓存按actor.id/server/revision隔离，401/账号停用清除权限缓存并保留该账号的未保存草稿，不套用到游客/其他账号。

DELETE `/session` 或 `/association`：账号token，返回 `{"logged_out":true,"scope":"current_native_account_session","guest_session_retained":true,"website_other_sessions_revoked":false}`。重复旧token可能401，客户端视为已失效，不重新登录恢复旧关联。它不删除账号、车库、投稿、本机数据，也不调用微信平台“解绑”。

## 注册、登录、验证、邮件和邀请码

以下POST均为Content-Type:application/json、≤65536字节、无query。正文共有 `schema:1,request_key:<16..80 ASCII字母数字_横线>`，再加表中字段，未知字段拒绝。响应丢失保留同key/同正文；不要自动换key重发密码/邮件。邮箱/密码/邀请码/token的格式及错误均复用现有网站校验，邮箱规范化、密码12–128字符、邮件token30分钟/单次/同类新token使旧token失效均不变。

| 路径 /auth/... | Bearer | 额外正文 | 成功 |
|---|---|---|---|
| register | 访客 | email,password,invite_code可省略为空 | message；不自动登录，不自动导入车库 |
| login | 访客 | email,password | 上述独立账号会话；必须邮箱已验证、账号未停用 |
| resend-verification | 访客 | email | 沿用网页防枚举message与实际邮件限额 |
| forgot-password | 访客 | email | 沿用网页message；不暗示邮箱必定存在 |
| verify-email | 访客 | token | message；只消费对应未过期token |
| reset-password | 访客 | token,password | message；原网页和原生撤销锚均失效，需重新登录 |
| redeem-invitation | 账号，须X-Account-ID | invite_code | 沿用邮箱绑定/单次管理员邀请；不能获得超管。成功后旧会话撤销，重新登录读角色 |
| reauth | 账号，须X-Account-ID | password | 再次执行原密码验证并轮换原生账号会话；返回新token/认证时间，旧token失效 |

再认证时间仅为A批身份信息；E批高权限写入仍须按原业务对象/原有专属再认证规则实现，不能凭此时间自动开放发布/回滚。

邮件链接仍沿用现有30分钟URL，不强行加入未经验证的小程序深链。**不使用web-view**：用户可在邮件浏览器确认验证/重置后返回原生登录；也可将链接中的一次性token显式带入原生验证/重置页，发上述接口。打开链接本身不消费token。客户端不得将token持久化/记日志或自动替用户确认。当前mail_mode=file只写隔离outbox，不是实际外发；smtp/production须用户安全配置且遵守既有发送/重发/日限额，发送不确定不自动重试。

## 幂等和恢复

同一身份作用域+request_key+action+完全相同正文，已完成操作返回原结果，不重复发送邮件、保存或创建会话。相同key换正文/动作409 OPERATION_KEY_CONFLICT。登录结果恢复时重新核验会话/actor，已退出/被替换/撤销的旧结果不会重新登录。

GET `/operations/{request_key}?action=<action>`：除profile-save外query恰好一个action；profile-save还必须明确server=cn或global。

- register/login/resend-verification/forgot-password/verify-email/reset-password及reauth恢复使用父**访客token**，作用域为该访客；reauth提交本身仍要求旧账号token。这样再认证响应丢失后可用父访客恢复新token。
- redeem-invitation/profile-save恢复使用**账号token+X-Account-ID**；成功兑换导致旧权限会话失效时，先重新登录，不自动重复兑换。
- 完成时返回原HTTP状态/响应；登录/再认证成功才重新构造原token（数据库不存token明文）。404 OPERATION_NOT_FOUND不证明从未执行，不自动重发；409 OPERATION_UNCERTAIN + Retry-After:2表示进行中/跨库提交结果不确定，先核对邮箱/车库/身份，不再次执行同key。恢复状态最多保留24小时，失效身份不能借换账号读取旧操作。

退出不需要request_key，401即已失效。密码/邮件token/invite_code仅保存用途隔离HMAC指纹，不缓存原正文；成功注册/邮件message和必要车库冲突快照属于独立私有恢复记录。既有账号/车库库没有拷贝到客户端或原生状态。

## 分服车库

GET `/profile?server=cn|global`，账号token+X-Account-ID。query不允许缺失、重复或额外字段。

两服成功形态相同，记录及revision分开。CN成功：`{"server":"cn","storage":"account","remote_supported":true,"revision":0,"profile":null}`。profile=null指账号尚未保存，**合法空车库**为 `{"cars":[],"stars":{}}`，两者不混淆。实际已保存返回整数revision及完整cars/stars；GET失败不覆盖当前本机草稿。

Global成功：`{"server":"global","storage":"account","remote_supported":true,"revision":0,"profile":null}`；已保存profile包括cars/stars/ocMap。2026-11-03用户追加要求现阶段接入国际账号云车库，覆盖早先仅本机的阶段结论。国际计算仍五区满星理论，云端OC为严格boolean映射。组件尚未迁移时503，features.profiles.global=unavailable，不以失败/空响应覆盖本机。详见 GLOBAL_PROFILE_CLOUD_20261103.md。

PUT同路径按server分别接受：

```json
{"schema":1,"request_key":"random-key-at-least-16","explicit_save":true,"intent":"save","revision":0,"cars":[],"stars":{}}
```

游客导入必须 `intent:"import_guest",confirm_guest_import:true`，由用户明确选择；不在登录/GET时自动写入。intent=save不要求confirm_guest_import，explicit_save必须为true。字段只允许schema/request_key/explicit_save/intent/confirm_guest_import/revision/cars/stars，global另外允许ocMap。两服stars保存网页原始1–6整数，显示时仍由原共享分区星级规则处理；不在后端重新推算规则。不接收客户端角色/user_id或国际OC混入CN。国际ocMap的true仅限当前国际目录有OC数据的车型；不改车辆规则。

成功200：`{"server":"cn","revision":1}`。同key同正文重试只保存一次。revision冲突409：

```json
{"schema_version":1,"code":"PROFILE_CONFLICT","detail":"说明",
 "current":{"revision":2,"profile":{"cars":[],"stars":{}}},
 "submitted":{"revision":1,"profile":{"cars":[],"stars":{}}}}
```

客户端保留两份及原base revision，由用户选加载远端或明确以最新revision再保存；不用旧key修改正文，不后台自动覆盖。不同设备/网页与原生共用同一CAS。Global保存独立写入profiles_global，不写CN作为回退。同一request_key跨服复用409；恢复query为action=profile-save&server=cn或global。本机游客数据保持，首次导入仍需显式确认。登出/切账号清权限与已发布视图，草稿继续按actor.id/server分开保留。

## 错误与权限拒绝

错误体统一 `{"schema_version":1,"code":"...","detail":"..."}`，不回显密码/token/完整校验输入。401包括ACCOUNT_SESSION_REQUIRED/INVALID/EXPIRED、ACCOUNT_SESSION_REVOKED、ACTOR_CHANGED、ROLE_CHANGED、CREDENTIALS_REJECTED及父访客失效；全部要求保留草稿、清旧账号/角色缓存。403包括NATIVE_ONLY、EMAIL_NOT_VERIFIED、ACCOUNT_DISABLED、ACCOUNT_FORBIDDEN。400/422分别为原生结构/现有业务字段拒绝。409包括幂等/确认/车库冲突；404/405 ACCOUNT_ROUTE_PENDING为未固定路径/方法，不意味着客户端可猜另一个权限入口。

429 ACCOUNT_RATE_LIMITED沿用现有网站限流/邮件预算，本批Retry-After为秒，通常60，表示保守最短等待，不保证日预算已恢复，不自动重复邮件操作。OPERATION_UNCERTAIN使用2秒供查询退避。503包括ACCOUNT_STATE_UNAVAILABLE、ACCOUNT_CAPACITY、ACCOUNT_DELIVERY_OR_SERVICE_UNCERTAIN；先恢复/核对，不把超时当未执行。

未登录→私有入口401；微信访客→账号车库401；普通/管理员/超管→仅能按自己的实时actor访问A批账号/车库；伪造X-Account-ID/角色不授权。停用、撤销、角色变化后重新检查拒绝。B–E尚未固定原生路径，不能把A批角色字段当成已有管理API或真实审核/发布授权。网站现有高权限写路径仍需Cookie/Origin/CSRF及自身对象权限，原生Bearer直接调用被拒绝。

## 配置与隔离复现

现有RACEPICK_MINI_CONFIG可选增加 `account_state_dir`；省略则A关闭，旧五字段配置不变。示例 production/mini-account-config.example.json。先由运行用户对**全新独立目标**执行 `python -B -m backend.mini_accounts provision --state-dir <新目录>`；启动只检查schema1，不自动初始化/迁移旧访客/网页数据库。新目录/标记/签名key/SQLite为私有700/600、运行用户拥有、禁止链接；必须与访客/OCR队列互不包含。ProtectSystem=strict时独立目录需成套追加ReadWritePaths，配置只读。

独立原生账号schema1含sessions/operations/events/meta；存撤销锚哈希、uid、父访客sid、认证时角色/到期时间、操作HMAC和必要恢复结果，不存密码/Cookie/token明文。DB限制8192页、活动会话10000、恢复记录20000。它不加入应用包/现有业务备份；丢失会撤销原生账号关联，网页账号/车库不删除。关闭account_state_dir后只关闭A前缀，旧访客/识图仍可用。无需改正式业务schema。

本地命令（不复用8033/8043/8044状态；先检查空闲端口）：

```powershell
python -B -X utf8 -m backend.mini_local create --accounts --source . --receipt ..\offline-evaluation\data-sync-20261102-01\sync-receipt.json --model-config ..\.score-version-sandboxes\9f326b2976b6637b90f07be5\config.json
python -B -X utf8 -m backend.mini_local serve --lab <新建lab> --port 8045 --fixture-auth
```

create只显式核对五份4504/693运行JSON SHA与模型SHA，全部账号/会话状态新建，未冻结数据不当正式包来源。fixture只证明业务，不是真实微信验证；邮件只写该lab的outbox。真实平台配置模式仍需私有AppSecret/允许域名/TLS，并且account_state_dir匹配本次--accounts创建的新目录，不发送秘密到聊天。A请求使用现有Nginx业务5r/s桶/默认3m，应用正文另限64KiB；不新增大上传路径或放宽Origin。回退先移除account_state_dir并重启API，保留状态/业务新增，再按兼容流程回退代码；不恢复旧库或覆盖score-state。任何生产配置/新目录创建仍需后续授权，本轮只本地验证。
