# 账号A与双服云车库只读接收

整理日期2026-11-06，Asia/Shanghai。接手工作树 `feature/miniprogram-v1`，初始HEAD `dd8731fa154d44da53bbdb955d23549e1354e3b8`，初始暂存/未提交/未跟踪均空。复用原工作树，没有reset、clean或另建工作树。网站主树main `19e5c18`，功能树 `feature/map-layout-parser` / `bfcf97e`，二者既有修改/未跟踪材料继续由网站侧持有，本轮未写这些文件。

## 固定来源与范围

完整读取本分支ACCOUNT_NETWORK_PREPARATION、HANDOFF_ACCOUNT_NETWORK、PHONE_OCR_ACCEPTED_20261104、HANDOFF_MINIPROGRAM_DEV_20261102，以及主repo的20261105只读交接MD/JSON/SHA、网络阶段机器回执、A契约、Global云车库契约和CLOUD_HANDOFF文首。根CLAUDE/context相关最新记录同时核对。没有发现适用于本轮路径的AGENTS.md。

最新批次20261105，整理日期2026-11-06；step20完成时刻未知。新origin `https://account-test.racepick.cn`，delivery `7c5f53fc366b7af555214846`；封存source_commit仍null，base `bfcf97e1511ee3d418a1f558c30a3ba0148d5286`不是完整候选源码。本轮来源绑定写入 `miniapp/services/account_readonly_binding.js`，精确来自固定JSON，不从dirty网页抽规则。

仅新origin的新父访客、固定快照、用户明确登录一次与双服认证GET。`allowCloudWrites=false`，新只读模式在路由和动作两层禁止PUT、DELETE、再认证、注册/邮件、图片、B–E及统计。保留原AccountClient/CloudProfile及198999a ProfileStore、8da1609机器契约；未修改共享五模块、正式页面、运行数据、工作簿、后端或生产。

## 客户端实现

- 复用原UTF-8/SHA和verifyNativeSnapshot，增加精确GET snapshot白名单；验证原文五文件的固定SHA/bytes、两服版本、身份、Global三件套元数据/manifest绑定和dataset。客户端健康必须匹配固定交付、schema和只读开关，全部完成才允许账号登录。
- 新增只读plan示例，旧mini-test关闭示例保持。新工程有独立planId/草稿作用域，创建全新内存访客transport，不读写旧OCR身份、预约和草稿。
- 本次登录至多一次。未知结果仍交给原AccountClient保留key/action，只查询原登录；404不解除保留、不换key。429记录Retry-After、拒绝等待窗口内动作，无自动重发。
- 只读页面不展示暂存、保存、远端覆盖或退出。页面重开复用App进程内原probe，保留未知操作；关闭整个进程后不将丢失内存误认作未执行。密码不持久化，提交前清表单字段，必要请求正文仅内存；报告不含邮箱、actor ID、父identity、key、code或token。
- 双服profile先验证server/storage/remote_supported/revision及profile结构，再交原ProfileStore；null、合法空库与读取失败分开，失败不覆盖已读取结果/本机草稿。Global OC必须boolean。report只输出角色、关联校验布尔值、revision、null/empty/saved和计数。

## 已实际完成的验证

独立证据目录：`E:/hzz/work/MutualExclusionAllocator/offline-evaluation/mini-account-readonly-20261106-01`。

1. `delivery-reception.json`：核对固定MD/JSON原字节SHA、候选ZIP大小/SHA/CRC、CANDIDATE SHA及其全部文件；HTTPS健康与公网五份原UTF-8数据逐项SHA/bytes、Global三件套通过。只有6次GET，没有账号或微信登录。该层不证明真实鉴权。
2. `client-tests.log`：12个文件147项通过，包含原140项和新增7项。新增覆盖固定数据替换拒绝、健康不符前置拒绝、只读完整fixture、禁写/退出、null与empty及503、未知登录原key/404、429等待；fixture不是真实账号证据。
3. 用户文字确认并提供后台截图：request合法域名含account-test且保留mini-test，原uploadFile仅mini-test，downloadFile为空。仅记录配置证据，不等同手机网络通过；本轮未操作微信后台。
4. 官方CLI/SDK实际运行 `account-check-js`：CLI真实autoPort **9433**，页面buildId **8e4c4dde18ffa581caeb**，SDK3.17.6/platform devtools，AppID匹配布尔true，urlCheck=true、无private override。已实际新wx.login/父访客POST1，snapshot GET2，A访客session GET1，health GET1；固定校验通过、异常0。`devtools-js/result.json`和输入凭据前截图记录此层。authPosts/profileReads/profileWrites/logouts/recoveries当时均0。

最初 `account-check` / 9432没有取得页面，不能算编译成功；该目录保留。固定绑定改为JS模块后生成 `account-check-js` 才获得上述页面与SDK证据。SDK旧版page.callMethod调用另遇方法错误，改用官方evaluate调用明确connect；失败均未发送账号登录。没有用端口请求值代替实际autoPort，也没有清缓存/认证状态。

## 真实隔离账号开发者工具只读通过

用户已明确回复“已完成登录及双服读取”。随后官方SDK仅读取同一buildId的probe.report，未重新登录、编译、截图或触发业务请求。固定证据为外层 `devtools-account-acceptance/result.json`：真实player登录1次、认证profile GET2次，CN与Global均revision0/profile=null；tokenKind、parentIdentityMatches、sessionOnly、expiresWithinParent、roleMatches均true，无pendingAuth、无errorCode、异常0。profileWrites/recoveries/logouts均0；两服dirty=false，无pendingSave/冲突。ProfileStore内部status=saved在此仅表示读取状态就绪，不能解释为发送过云保存。用户操作的精确完成时间未提供，不以文件落盘时间推断。

本次已满足开发者工具真实隔离账号只读通过条件：原AccountClient验证rpa1、有效期及实际父association/session_only，双服GET均成功、revision/profile状态明确、写入计数0。两个null只证明本次认证读到未保存状态，不能证明网页/原生同记录同步或真实保存；真实合法空车库读取也未由此覆盖，null/empty区分仍另有本地fixture证据。

已在开发者工具真实账号只读通过后准备独立手机工程，见下节。手机账号、真实同记录同步、保存/冲突/退出/再认证/撤销及身份变化专项仍未验收；不恢复OCR额度、不发图、不发邮件、不注册，不操作服务器/数据库/生产/微信后台、上传提审发布或推送合并。服务未开机自启、证书续期加载待核，不属于本轮客户端执行范围。

本轮代码可本地提交；准确提交ID另记外层commit-receipt.json，不倒改已生成工程的原始source/dirty或封存交付source_commit。

## 手机独立只读工程与步骤（尚未执行真机）

路径：`E:/hzz/work/MutualExclusionAllocator/offline-evaluation/mini-account-readonly-phone-20261106-01/account-check`。
planId：`mini-account-probe-readonly-phone-20261106-01`；buildId：`89883d823650ca3c7e38`。保持独立origin/actor/server/plan作用域；AppID仅在本机工程配置，未加入Git。旧开发者工具账号会话与旧OCR工程/预约保持，没有退出或撤销。

官方CLI实际autoPort9434；官方SDK核页面buildId、AppID匹配布尔true、urlCheck=true、无private override、SDK3.17.6、异常0。仅完成编译，所有请求计数0，connected=false/loginAttempted=false。证据在新外层preflight/result.json与输入凭据前截图。没有自动预览、上传体验版、提审或发布。

用户手机步骤：

1. 确认开发者工具打开的是上述手机独立工程，目录尾为 `mini-account-readonly-phone-20261106-01/account-check`，保持域名/TLS/证书校验；在开发者工具点“预览”，手机微信扫描这份工程的新二维码。无需添加任何uploadFile/downloadFile域名。
2. 手机上点一次“核固定来源、双服快照与访客入口”。等待报告connected=true、bindingVerified=true、snapshotChecks.cn/global=true；失败即停留原页，不重开/换码或恢复旧身份。此处必须是手机新wx.login与新父访客，不能接用模拟器凭据。
3. 在手机私下输入同一隔离邮箱/密码，只点一次“明确登录”。不要故意输错，不注册、不重置、不再认证；未知结果只保留原操作，先回传错误码，不换key重登。
4. 依次选国服、国际服，各点一次“读取该服云车库”。预期真实player、两服authenticatedRead=true；当前无写入情况下预期revision0/kind=null。任何失败/503均不当空库。不要保存/导入/退出。
5. 仅复制页面底部的脱敏JSON报告为文字，并告知手机型号、系统和微信版本；不发送邮箱、密码、token、code或带输入框的截图。该工程buildId由本固定生成回执绑定。报告应显示authPosts1、profileReads2、profileWrites0；这是待核标准，不是已发生计数。

若429，遵守Retry-After且不自动重试；不假定日预算恢复。若未知登录结果，保留原key/action于当前进程，只核对原登录；404也不证明未执行，不关闭进程或新开工程重登。手机结果回交前不得记录真机通过，不扩大为Android/其他设备/切网前后台/退出/云写验收。
