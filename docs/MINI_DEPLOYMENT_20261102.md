# 原生适配配置、本地联调与后续运维准备

2026-11-02。仅本地开发/隔离验证/材料准备，不是生产执行授权。网站feature/map-layout-parser归口；共享核心仍198999a。新源码、测试及协议SHA见本轮commit-receipt.json，正式包尚未构建，4504/693维护数据未重新冻结。

## 默认关闭及独立状态

未设置 `RACEPICK_MINI_CONFIG` 时，所有 `/api/mini/v1` 路由404，不创建原生状态。现有网页Origin/Cookie/CSRF/raw上传均不变。显式配置使用 `production/mini-config.example.json`，读取与校验失败即停止启动，不静默降级成无鉴权入口。

配置字段恰好kind/state_dir/appid/app_secret_file/image_policy。示例AppID为占位，不能当真实项目AppID。AppSecret通过服务端独立600私有文件读取，不贴聊天、不进客户端/仓库/日志；目录及配置也由运行用户拥有，700/600，禁止链接。服务器通过code2Session验证，不把Referer/AppID当身份；未读取手机号/昵称/头像，session_key未使用即丢弃。真实调用还需正确平台AppID/AppSecret及平台允许的服务器调用条件，本轮没有调用微信真实接口。

`python -B -m backend.mini_auth provision --state-dir <全新独立目录>` 只创建新原生会话schema1、标记、token.key及guests.sqlite3；已存在目录拒绝，不打开/迁移网页账号或正式成绩库。`check`只核验已初始化结构。此命令未来现场执行需授权，本轮只在新本地fixture目录运行。

独立schema1包含sessions/codes/budgets/uploads/meta；存平台身份用途隔离HMAC、code/request摘要与上传租约，不存OpenID明文/原code/AppSecret/session_key/令牌明文。token.key是服务端签名秘密，不可随应用分发。会话TTL3600秒、撤销与重启后仍生效；code占用24小时，上传恢复状态清理边界4200秒。数据库最多8192页、预算桶20000、code/上传记录各10000，满额拒绝503。客户端令牌仅内存。

会话状态不加入既有业务33文件备份，不修改既有备份/恢复工具；新目录按独立临时身份状态管理，丢失/换key会撤销全部原生会话、旧任务不能换身份找回，但不影响网页账号/车库。回退/恢复时保留目录及新增记录，不自行清空。需要持久保全原生会话时，由运维单独制定私有加密备份策略，不能混入发布包。

## 本轮隔离本地环境

只用新端口8043，不改写/启停8033或其账号库；本轮环境和进程观察记录位于外层 `offline-evaluation/mini-api-20261102-01/local-lab.json`、process*.json、server*.log。PID仅为当时证据，启停前须再次验证真实cmdline/父子进程/目录和未完成任务。

复现创建（显式核验接收SHA，只取五份运行JSON和已验收模型路径，不复制任何旧账号/成绩状态）：

```powershell
python -B -X utf8 -m backend.mini_local create --source . --receipt ..\offline-evaluation\data-sync-20261102-01\sync-receipt.json --model-config ..\.score-version-sandboxes\9f326b2976b6637b90f07be5\config.json
python -B -X utf8 -m backend.mini_local serve --lab <上一步返回的新lab路径> --port 8043 --fixture-auth
```

本地fixture明确只接受 fixture-code-1 / fixture-code-2；不是wx.login真实code验证。每个code首次使用的request_key需客户端保留，响应丢失仅同key恢复。不要用该模式证明真实微信鉴权，也不将任意code设为有效。没有平台秘密仍可完成本地后端/worker业务测试；小程序当前低层HTTP适配需按协议接线，开发者工具对真实平台会话、wx.uploadFile及真机验证另行记录。

准备好服务端真实平台配置后，可在这个**新建隔离lab**上将serve参数换为 `--mini-config <私有配置路径>`，与 `--fixture-auth` 互斥。配置state_dir必须等于create回执中的guest_state，不能接旧账号/测试会话目录；AppSecret只从用户安全配置的文件读取。此模式不会自动配置微信域名/TLS或连接生产。本轮只验证了CLI边界及fixture流程，尚未使用真实AppSecret或调用真实平台登录。

独立本地模式复用原RecognitionService/CPU worker，**不包含Linux生产监督者的systemd/fcntl硬截止**。取消晚结果拒绝和队列状态自动化通过，不代表Windows本地已完成45秒杀进程故障演练。生产路径继续复用原唯一ProductionRecognitionService/systemd监督者，原生不另启动worker；Linux硬截止/崩溃恢复应在将来独立Linux状态验证后再考虑生产。本机Docker CLI存在但Linux引擎管道不可用，WSL只登记已停止的docker-desktop；本轮未擅自启动Docker/WSL服务，未执行或编造Linux/Nginx运行时通过记录。

## 应用包外配套：仅准备，未安装

模板变更是成套方案，不能单独复制一个location：

1. 保留现有Nginx map/zone/证书/ACME/端口/可信代理和OCR现场High640M/Max768M等资源设置，不照抄旧模板覆盖。`nginx-rate.conf`将精确原生路由纳入**同一个**racepick_map_requests 6r/s burst12预算，排除业务/统计桶；不是新增第二份OCR容量。数据库进一步实施签发/owner/IP配额。Nginx自身429可能无Retry-After，客户端无头时保守等5秒。
2. `nginx-https-location.conf`只给精确原生jobs路径8256k（8MiB+64KiB），旧网页jobs仍8m，其余路径仍3m；API再次限制multipart/单文件8MiB与像素。只代理到回环8001，保持Host、X-Forwarded-Proto=https和真实X-Real-IP。后端拒绝非可信代理/无效Host/IP；不得新增公网worker端口。
3. accounts服务模板新增可选 `/etc/racepick/mini.env`；默认文件不存在即可关闭。该文件只放RACEPICK_MINI_CONFIG路径，秘密不放环境或命令行。配置和AppSecret只读，独立原生状态可写。**若状态使用示例的 `/var/lib/racepick-mini-guests`，accounts单元的ProtectSystem=strict必须另外授权 `ReadWritePaths=/var/lib/racepick-mini-guests`**（现有模板仅允许/var/lib/racepick）；不扩大OCR worker的只写队列挂载。
4. image_policy默认disabled：会话/计算快照可用，原生OCR503。只有用户确认实际图片安全策略并在隔离环境验证后才选择private_unmoderated或另行实现审核；此值不代表已实施内容安全审核。OCR、格式检查和私有存储均不能在后台申报成审核服务。本轮没有外送图片。

示例独立目录对应的accounts drop-in（仅准备，路径需与配置state_dir完全一致；未来授权后才安装到 `/etc/systemd/system/racepick-accounts.service.d/40-mini.conf`）：

```ini
[Service]
EnvironmentFile=-/etc/racepick/mini.env
ReadWritePaths=/var/lib/racepick-mini-guests
```

原生配置/AppSecret文件归运行用户且0600，父目录允许该用户只读遍历；mini.env只放配置路径。没有新端口、新worker或正式账号迁移。关闭入口时删除mini.env中的环境项并重启API；保留原生状态和drop-in本身不等于启用路由。

## 将来经授权的执行顺序与回退

先只读核对现场版本、配置/服务、活动双服版本、真实OCR预算/队列、恢复点和剩余资源；不能按历史PID操作。维护数据重新冻结与批准源码/功能后才在独立干净检出构包，纳入新模块/协议/模板、离线依赖/来源及逐文件/整包SHA，排除账号库、原生状态/密钥、队列图片、测试截图、完整维护732及工作簿。当前实现没有新增第三方Python依赖，multipart为有界单文件解析器，不全局安装/放宽multipart。

在独立Linux临时状态验证：默认关闭/真微信code交换（需安全配置）、原字节快照、wx.uploadFile、身份/过期/目录变化、网页门禁、全局/可信IP配额、multipart边界、响应丢失恢复、队列120秒/运行45秒/取消/退出/崩溃恢复、私有权限和保留策略。Windows测试、fixture平台验证、本机CPU真实OCR、Linux/systemd、开发者工具及iOS/Android真机分别记录。

现场成套备份及可恢复性核验后，单独授权新建独立原生状态/凭据、成套Nginx修改及nginx -t、服务可写路径与可选配置。先保持image_policy=disabled，确认网页和两服活动成绩不变；再按用户图片策略及原生联调验收决定开启。不得自动迁移正式账号、重播种score-state、开启国际写回、发布维护成绩或小程序体验版。

任一身份隔离/资源/原字节/配额/旧网页回归失败，停止推进；优先撤销RACEPICK_MINI_CONFIG并重启API以关闭原生入口，原OCR和网页继续既有服务。保留新会话状态/队列和日志，不回滚正式业务新增。回退应用仍须兼容coverage2/global-score1及全部既有组件；无正式业务schema迁移，不恢复旧账号库、不以包JSON覆盖活动成绩。Nginx恢复先验证再按授权reload，整套数据恢复另行授权。
