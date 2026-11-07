# A账号隔离服务本地候选 · 2026-11-05

本轮是本地代码、离线候选与模拟验证，不是现场部署/正式账号接入授权。现有mini-test、OCR/队列/worker、正式业务库、成绩指针和已完成迁移均未操作。原封存包来源记录保持。

## 入口及数据归属

新独立origin尚未选定、未配置DNS/TLS。模板account-test.invalid是保留的占位域名，不能用于实际验收；现有mini-test的账号可用性没有新证据。默认enabled=false/cloud_writes=false；关闭启动只解析声明，不读业务/访客/原生状态或平台凭据。

`backend.mini_account_service`是新隔离启动器。启用只接受专用isolation.json标记、固定origin、同一根下三个独立状态目录，签名key/数据库私有且禁止链接。新root显式provision才建立空schema6/Global profile1/Guest1/native account1及账号控制schema1；启动只读检查三库结构指纹、完整性、私有路径和快照。旧schema/混入旧库一律拒绝，不自动迁移或创建。原正式coverage2/global_score1没有复建；本阶段不用其业务组件，健康中明确为0，固定snapshot另列版本，不能把快照伪装成正式活动成绩组件。

网页与原生由同一create_app实例的Store处理，网页使用安全Cookie/Origin/CSRF，原生用独立GuestStore→rpa1→网页撤销锚。父访客真实交换仍由原WechatVerifier完成；测试中只patch平台返回，不能称真实微信已验收。新origin使用新的父访客命名空间，不能复用mini-test已有Bearer。

CN/Global校验、OC、独立revision、null/空车库、显式保存、冲突及未知操作恢复沿原实现；算法五模块不改。网页/原生均受同一cloud_writes开关，先只读，再按另行授权开启写验收。

## 精确开放范围

- 原生：POST /api/mini/v1/session、GET /api/mini/v1/snapshot；A GET/DELETE session、POST auth/login和auth/reauth、GET/PUT profile?server=cn|global、GET operations/{key}。恢复仅login/reauth/profile-save，profile-save必须明确server。
- 网页：GET/HEAD /及固定静态资源；GET /api/auth/me、POST /api/auth/login和logout、GET/PUT /api/me/profile。仍是既有网页账号/车库产品；登录页按服务能力隐藏注册/找回/重发，不用测试页取代镜像页面。
- GET /_account-test/health仅提供候选ID、schema、开关、双服固定版本等非秘密来源信息；同样要求精确Host、回环可信代理、HTTPS和合法真实IP。原通用/api/health未开放，避免混称正式业务健康。
- 公网注册/验证/重发/重置/邀请、网页投稿/公告/管理、B–E、统计、图片和OCR均拒绝。Nginx模板只有相同精确路径和静态资源白名单，没有任意网页转发或通配Origin。

JSON64KiB、账号/签发限流复用原组件；网页及原生响应no-store。账号Token不用于访客/网页Cookie接口。A身份GET/login不导入游客数据，不把503或关闭视为空车库；404恢复也不允许自动重发。

## 离线新测试账号方式（当前未现场执行）

候选包含prepare-account-stopped本地运维入口：必须显式确认全新隔离账号、独占锁且服务已停，交互隐藏输入密码和确认，不接收命令行/管道密码。复用原register/verify处理函数，只写隔离file outbox并在本地消费一次性验证token，输出不含邮箱、密码、token。原生与网页公网不因此启用注册/邮件。

已有邮箱一律拒绝重放；若结果未知，先查原隔离状态，不自动重发/换号。outbox私有700/600，随隔离业务备份保留，不能上传或发聊天。真实注册准备仍待用户明确邮箱及操作范围；真实外发邮件完全未启用，须另明确地址/次数/不确定恢复策略。

## 固定候选及恢复

builder只复制代码白名单、五份固定snapshot及接收绑定、默认关闭模板和hash锁定的Linux x86_64 CPython3.12离线wheel。没有账号库、测试状态、密钥、模型、工作簿或维护树数据。当前未提交代码：source_commit=null，source_base_commit仅历史基底；delivery_id由实际文件清单计算，后续Git提交不会倒改本包来源。ZIP SHA及验证结果在本轮候选回执，不复用OCR发布ID。

服务在ASGI启动时持有独占锁。备份只在该隔离服务停止后可获取锁，检测journal/WAL/SHM并拒绝活动状态；三库、签名key、file outbox及快照成套复制，逐文件前后SHA一致才通过。备份含秘密，只能私有保存。restore-new只允许新的独立目录，拒绝覆盖活动根或旧备份。关闭入口/回退兼容候选仍保留当前全部状态，不靠旧DB撤销保存或恢复旧队列。

## 证据及现场边界

本轮回执分别列Windows模拟、打包副本验证、离线依赖和Linux结果；未运行的项目标待核验。进程内TestClient的HTTPS代理模拟不等同实际TLS/Nginx或Linux权限验收。fixture账号、平台身份及file outbox不是真实账号/真实微信/邮件验收。

下一现场步骤仅在用户授权后，由用户执行新的只读环境核对，确定独立origin/DNS/TLS、UID/GID、端口/路径、备份及恢复方案，再逐步部署默认关闭候选。不提供或执行一键生产写脚本。不自行启停原服务、不复跑迁移、不操作微信后台或小程序上传发布、不推送合并、不清理或新设监控。

小程序后续顺序保持：固定来源/组件→真实父访客与账号分离→用户输入隔离凭据、登录与双服只读证明无导入→另授权暂存/显式保存/重载/冲突/退出/身份变化→最后手机步骤。无新真实验收时不能提前标通过。
