# 真实微信访客与快照：独立第一阶段服务准备

本轮仅本地开发、隔离测试和制品准备，不授权服务器创建目录/用户/状态、DNS、证书申请、Nginx/systemd安装、微信后台登记或发布。线上仍是a933c9b7；原生API关闭。后续一次给用户当前一步命令，核对回传再继续，不能将模板当作批量执行脚本。

## 已收到的现场证据

2026-11-03 19:54 CST用户回传：服务器可用内存1077MiB、磁盘可用27GiB，网站和唯一OCR均active/running，current为a933c9b746c2e276a9b68d14。racepick.cn解析8.138.47.110，已验证TLS证书仅含racepick.cn，有效至2027-01-13；mini-test.racepick.cn未解析。不得将该IP直接当作添加DNS的授权，也不把主域证书当子域证书。

后续只读回传确认：发布manifest完整校验通过，源码765a4a62567c97a9a2d4f48cf3a8955e3e8cd715；FastAPI0.138.1/Uvicorn0.49.0/Pydantic2.12.5。正式包有mini_api/mini_auth，无mini_local或独立访客启动器。候选8011无监听，racepick-mini-test用户及/opt、/etc、/var/lib同名隔离目录均不存在，certbot命令存在。这些是当时快照，安装前仍需核对漂移。

## 独立启动器与固定快照

backend.mini_guest_service只复用既有MiniGateway和WechatVerifier，不导入backend.app、账号/B–E、OCR或模型。production-shaped可信代理规则继续生效：只绑定127.0.0.1:8011、关闭Uvicorn proxy_headers，强校验显式HTTPS origin的Host、真实回环TCP peer、X-Forwarded-Proto=https及X-Real-IP。不能照搬mini_local serve或使用fixture模式开放公网。

第一阶段外层白名单仅POST /api/mini/v1/session和GET /api/mini/v1/snapshot?server=cn|global，其余路径包括账号、B–E、OCR和DELETE session均404；图片策略硬性disabled，拒绝account_state_dir和private_unmoderated配置。既有code/request_key恢复与访客配额、内存token和原始快照契约保持。没有RacePick账号、网页Cookie身份或管理员接口。

独立包仅取已批准b57d97a8冻结的五份runtime原字节，通过已校验a933网站ZIP核对来源；不读取服务器正式账号库、正式score-state或旧测试状态。snapshot.json绑定五文件SHA/大小，启动时再次验证国际三件套原子绑定并将快照固定在内存。两服测试版本由各自文件SHA确定，**不是正式活动指针**；具体ID和源码提交见交付DELIVERY.json。变更快照需新的完整包和显式服务切换，不自动跟踪生产投稿。

## 部署提案（均未执行）

- 候选origin=https://mini-test.racepick.cn；DNS、CA可信TLS、SDK合法域名和真实平台交换均尚未验证，不能直接回交为可用入口。
- 独立用户racepick-mini-test；新release在/opt/racepick-mini-test/releases/<交付ID>，只读current；访客状态仅/var/lib/racepick-mini-test/guests。原站点服务、账号库、成绩、唯一OCR和备份timer不修改、不重启。
- /etc/racepick-mini-test及状态父目录700，私有配置/AppSecret/签名密钥600，均由该独立用户拥有；真实App ID和AppSecret只由用户在服务端安全配置，不写Git、交付或聊天。不接受fixture凭据作为真实微信证据。
- systemd仅该状态目录可写，隐藏正式/var/lib/racepick和/etc/racepick，网络仅为反代和WechatVerifier出站使用。提案High96MiB/Max128MiB/CPU25%/Swap0/Tasks32，须结合隔离Linux测试和现场复核，不是长期容量保证。
- 新Nginx站点只代理两个精确路径，默认404，不反代正式网页；独立5r/s/burst10边缘预算、session4KiB、body5秒、upstream12秒，原生层仍有10次/600秒/IP及100次/600秒全局交换预算。保留原Cookie/Origin拒绝、不加CORS、不开放上传路径。
- 域名获明确授权后，先独立HTTP ACME challenge站点（不动原80默认站点），采用webroot申请独立子域证书；不要用需停原Nginx的standalone模式，不使用自签名或跳过TLS。成功后再逐步安装新HTTPS站点；每步nginx -t，原配置及服务保持。
- 离线安装脚本仅处理**新release**的.venv，不初始化业务、访客或队列。首次访客目录必须显式provision，已存在则停下，不重用旧状态。配置真实微信前仍可核验包和运行时，但不得用fixture成功冒称平台成功。

## 执行与回交顺序

1. 交付包及隔离Linux验证先固定，提供真实SHA和测试边界，申请当前必要的服务器准备权限。DNS、CA申请、新站点/服务/私有状态分别明确授权；不一次给完整写脚本。
2. 用户上传校验、暂存并离线安装新release，保持原服务不变；显式新建独立用户/目录/访客状态，再由用户安全配置凭据，不能聊天回传密钥或code。
3. 域名/证书/反代逐项核验。先验证可信TLS、未知Host/来源拒绝、两服未登录401、账号/OCR/B–E404，再由用户登记实际request合法域名。
4. 小程序侧以真实wx.login一次性code，在内存交换访客token，核验两服原始UTF-8/SHA/字节和identity；先开发者工具再真机。回交只含origin、固定code/data来源、隔离状态摘要和非秘密证据；不返回AppSecret/session_key/code/token/OpenID明文。
5. OCR随后另核图片安全/隐私与共享容量；不自动将策略改为private_unmoderated，不启动第二套OCR。RacePick账号/云车库及B–E继续关闭，后续另行协调。

停用只应停止独立服务和禁用独立测试入口，保留新状态和证据；不重启原站点或恢复旧SQLite。首次部署前尚无真实平台配置、DNS/TLS、SDK/真机结果和本服务长期容量证据。

## 本轮本地验证边界

新增入口9项测试及原生访客协议19项，共28项在Windows通过；新增入口最终定向9项再次通过。测试使用新建独立访客目录和显式mock平台验证，不调用真实微信。覆盖可信回环/Host/HTTPS代理/IP、网页Cookie/Origin与OPTIONS拒绝、原始双服快照、图片/账号/B–E硬关闭、不自动初始化状态、文件混入/损坏拒绝以及不导入业务/OCR模块。

本机Docker Linux引擎在准备验证时无法连接，未擅自启动Docker/WSL；Linux离线安装、真实Nginx/systemd/资源上限尚待后续明确授权的新隔离环境验证。本地测试不是服务器容量、可信TLS或真实微信成功证据。
