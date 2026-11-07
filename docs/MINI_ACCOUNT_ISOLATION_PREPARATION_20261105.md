# A账号与双服云车库隔离联网：接手检查与本地候选

2026-11-05，Asia/Shanghai。本轮只做本地检查、适配与进程内fixture测试。不是部署包、可用账号入口声明或现场操作授权。机器回执见 `MINI_ACCOUNT_ISOLATION_RECEIPT_20261105.json`。

## 当前证据

- 已先读外层CLAUDE.md/context.md，再读主repo/docs/CLOUD_HANDOFF.md、INDEX.md及固定A/Global契约。fetch成功。开始时main=e49d886；检查期间外部操作将main和origin/main更新至19e5c18742e9fe26cd5b38c3ee6b4f3ceb86669a，仅新增最新交接和INDEX。已重新阅读，没有覆盖这些修改。功能树及远端仍bfcf97e1511ee3d418a1f558c30a3ba0148d5286；本轮在该现有功能树做未提交适配。小程序本机dd8731fa154d44da53bbdb955d23549e1354e3b8，领先origin/feature/miniprogram-v1十九个提交，初查及复查均无工作树修改。未推送客户端或本轮代码。
- 主repo未跟踪的MINI_OCR_UPLOAD_INCIDENT_20261104.json保留。功能树初始干净；本轮新增/修改清单见回执。不动维护JSON、工作簿、共享五模块或小程序代码。
- 线上网站7241、mini-test origin、35bd加明确桥补件、CN OCR开启及Global/账号关闭，来自既有用户现场回执；本轮没有连接服务器或发起公网HTTP请求，不能称11月5日实时健康核验。原封存source_commit=null、schema迁移一次和正式成绩指针保持历史事实，不倒改来源、不重跑迁移。
- 已读miniprogram-v1/docs/PHONE_OCR_ACCEPTED_20261104.md与外层试次02 intake-success.json。属于用户iPhone14脱敏回传证据，不是本轮操作手机；基础五图识别及确认应用通过，不扩大为其他专项。与synthetic-once-02独立，不复用上传授权。
- 已读mini-account-network-prep-01/unauthenticated-account-gate.json：2026-11-05 00:05:35.927+08:00，mini-test A session未认证GET为404且不跟随重定向。没有组件/认证/权限验收含义。本轮未重测。
- 五份固定数据以主repo/docs/MINI_OCR_CN_BINDING_20261104.json为唯一接收绑定，对本地封存v2/snapshot逐项核SHA及bytes。不是维护树当前数据或正式活动成绩指针。具体核对结果和逐文件来源见回执。

## 可复用实现与实际缺口

`backend.app.create_app`建立网页处理函数及每app私有native marker；`mini_accounts`直接复用其登录/密码校验、角色、撤销锚和车库处理函数，不转发网页HTTP、Cookie或CSRF。`AccountStore`保存原生会话/操作恢复，`GuestStore`复核父访客有效及撤销；签发有效期取网页锚、父访客、3600秒上限的最小值。恢复不保存密码/token明文，不重建已退出的关联。

同一create_app实例的网页和原生使用同一个业务Store。CN为profiles，Global为profiles_global/schema1，OC严格boolean且revision独立；空记录null与已保存空车库不同。业务原始星级/OC校验和CAS沿原实现，无第二套车库算法。网页继续AccountClient/ProfileStore既有接线。

现有guest/mini_ocr_guest启动器明确拒绝account_store，且根本不建立native_accounts业务适配器；Nginx新增路径不能解决。现有完整组件已安装B–E并声明ready，必须在本阶段额外收口。现有production=True又强制SMTP/生产标记，而本阶段要求隔离file outbox，不能直接套生产启动器，不能简单传production=False绕开HTTPS/代理门禁。

## 隔离架构选择

推荐**独立账号验收origin与独立进程/状态**，其DNS名称、证书、端口、UID/GID及现场路径全部待授权核验；本文不编造新origin已就绪。现有已知origin仅https://mini-test.racepick.cn，其账号入口仍无新可用交付。新的独立origin承载固定路径POST /api/mini/v1/session和A前缀，用户明确建立新的真实微信父访客会话；原有mini-test访客/OCR状态、路由、队列、进程不动。

独立进程使用全新隔离业务库、全新GuestStore、全新AccountStore、独立file outbox。网页镜像入口与原生入口连接**同一个隔离业务库**；可在同一候选应用内按精确路径分流，网页保留自己的Cookie/Origin/CSRF，原生边界从不向网页回退。网页对外路径清单、静态文件来源和注册准备范围在完整启动器阶段单独固定。不给账号进程正式数据库、OCR队列、模型、供应商凭据或旧测试状态访问权。

真实微信code由服务器原WechatVerifier交换，父访客只从此隔离GuestStore验证；客户端提交身份文字/actor/角色均不作权力来源。rpa1与访客Bearer独立，X-Account-ID、实时角色/锚撤销/父访客检查沿原组件，每次复核。仅本次association，不永久绑定微信身份。

若用户要求沿用mini-test同一origin，必须先单独设计并验证原guest进程提供的最小父访客校验能力及签发归属。不能把同一路径随意改指新库、复制访客库或给新进程旧guest库全部写权限后宣称完成；当前候选不支持该替代方案，也未更改原路由。

## 本轮本地实现

- 新增 `backend/mini_account_boundary.py`，默认enabled=false/cloud_writes=false，关闭时不调用factory，不初始化API/状态。启用必须交付原MiniGateway且account_a_only=True；拒绝把完整网页app直接作为原生后备。
- 最小白名单为POST访客session、GET固定snapshot（既有只读数据能力）、A GET/DELETE session、POST auth/login/reauth、GET/PUT profile及GET operations。profile-save恢复必须带server，操作仅login/reauth/profile-save。PUT另受cloud_writes=false门禁；恢复查询仍可读，不用关闭写入阻断未知结果查询。
- 注册、验证、重发、重置、邀请码、association别名、B–E、图片/统计及任意网页路径均不开放。空Cookie/Origin头也拒绝，OPTIONS拒绝；返回no-store。精确Host、HTTPS可信回环代理及IP、签发/登录预算、JSON64KiB继续由原MiniGateway/A实现执行。
- mini_accounts新增可选account_a_only模式：A ready、B–E pending，不安装B–E路由，高权限写false。未设置该模式的既有fixture行为保持，旧功能树测试仍可运行。此内部模式只裁剪批次；完整上线必须使用外层白名单，不能只设flag就声称注册/邮件关闭。
- 新测试只用临时目录及进程内TestClient/fixture账号，file outbox不实际发信。没有监听端口、真实微信交换、真实账号登录或云写。既有轻量网关回归使用模拟桥，不调用模型/供应商，不新增实图OCR。

本候选仍缺完整的隔离HTTPS/file-outbox启动器、只读schema/路径归属预检、部署单元与包、Linux运行隔离、网页路径白名单和真实来源健康接口。不得据此把A接口标成公网ready。本地启动器需要在导入Store前拒绝旧/正式路径，启动不自动初始化或迁移；仅显式provision全新目标可建schema6/Global1等所需组件。coverage2/global_score1等成绩能力按实际需要固定来源，不为了复用启动器顺带开启业务或跑旧迁移。Global组件缺失必须503/unavailable，不能返回null冒充空库。

## 新测试账号与分层验收

完整候选准备后，再单列用户执行的隔离注册/验证方式：只允许指定的新隔离邮箱，密码由用户交互式隐藏输入；只在隔离file outbox写验证结果，由服务器本地受限步骤消费一次性token。密码/邮件token不写聊天、Git、交付回执或命令行参数。注册准备入口不并入原生白名单，不复制生产用户/密码哈希；该步骤仍需用户明确操作，当前未准备或运行现场写脚本。

先本地完整启动器与固定数据/能力检查，再备份及独立恢复/兼容回退演练，才能固定交付ID/逐文件SHA。其后由用户授权并逐步执行只读现场核对、新origin/DNS/TLS及UID/隔离路径准备、默认关闭部署；现场每步以回传为证据，失败保留状态，不回旧数据库。

启用与账号准备另定范围。收到固定交付的小程序先核来源/组件，再真实微信→账号分离；由用户输入隔离凭据，仅登录和双服读取，确认无导入；另授权保存范围后验证暂存、显式保存、重载、revision冲突、退出与身份变化，最后手机步骤。真实邮件若需要，再明确地址、次数、发送不确定的查询恢复策略，不能自动重发。

恢复404不证明未执行；不换新key重放密码/邮件/保存。只查询原key/action/server；未知结果保留，不自动重做。原OCR与业务迁移不纳入此阶段。
