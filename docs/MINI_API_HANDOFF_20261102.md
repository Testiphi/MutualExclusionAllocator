# 网站原生接口完成回交

2026-11-02启动；2026-11-03收尾。根据用户交来的小程序识图任务实施。继续使用 `map-layout-parser` / `feature/map-layout-parser`，基线198999a9ff5ca2ad524c50112ac6e03f5f18149f；本轮提交号、精确文件归属/SHA与保全记录在外层 `offline-evaluation/mini-api-20261102-01/commit-receipt.json`。未改动小程序树，未向其他对话派任务，未推送/合并/构正式包/操作生产或微信后台。

## 给小程序侧的接线入口

先按 [固定协议](MINI_API_CONTRACT_20261102.md) 实现HTTP适配；[配置/本地启动及配套](MINI_DEPLOYMENT_20261102.md) 列明默认关闭、独立schema、原生状态/凭据、模板执行顺序及回退。共享五模块仍来自198999a，本轮没有改共享计算、车型规则、估算、地图映射或维护数据。

路径 `/api/mini/v1`；Bearer会话；POST session的code/client_schema/request_key放JSON。快照以files中原始UTF-8 text/SHA/bytes封装，CN两文件、Global三文件，先原子核验再计算。catalog与快照都提供identity/catalog_version。上传server/catalog_version/request_key全部放query，multipart仅一份image。GET jobs/by-request提供found/reading/interrupted/not_found恢复；GET/DELETE jobs/{id}仍需server/catalog_version query。时间戳/Retry-After均秒，客户端转retryAfterMs。完整响应/错误与边界见协议，不从聊天另猜字段。

当前可用本地基址 `http://127.0.0.1:8043/api/mini/v1`，**仅显式fixture平台验证**；该地址对真实手机不直接可达，也不是已登记的HTTPS域名。本轮已经占用fixture-code-1；fixture-code-2需配同一 `request_key:local-fixture-session-02`，会话未过期时可恢复同token（仅客户端内存接收，文件不保存token）。会话到期后不能复用同code续期；需要新建独立fixture lab或安全配置真实平台验证，不修改旧库/放宽校验。原生API现有本地状态按创建回执独立生成，没有复制8033账号库或旧测试状态。

完整真实结构示例保存在外层 `snapshot-cn.example.json`、`snapshot-global.example.json`（公开运行数据和当前会话identity，无token/秘密）；未冻结的4504/693只作本地联调，不能当发布冻结来源。真实平台联调使用用户既有AppID，另需服务端私有AppSecret文件、允许调用微信验证的隔离后端、TLS/合法request/upload域名、真实wx.login code及已确定的图片安全策略。不要求把密钥或正式账号库发送到聊天。

## 实现及验证

- 默认关闭的独立原生ASGI前缀：不改变网页Origin/Cookie/CSRF/raw门禁。独立访客schema1/HMAC令牌、3600秒TTL、撤销、同code/key响应恢复、代码交换不确定拒绝及限流；没有创建网页用户、角色/投稿/积分或绑定user_id。
- 活动版本原字节快照和目录绑定；单图8MiB/16M像素、总封装8MiB+64KiB、有界单文件解析/20秒读取截止；独立读取租约和原key恢复；委托同一JobStore/worker/全局容量/可信IP配额。PNG/JPEG/WebP仍实际解码验证，未知part MIME不直接放行任意二进制。
- 查询/取消含owner/服别/目录/到期限制；五槽固定顺序，不返回无关OCR原文。原生图片/结果1小时和元数据额外10分钟也在本地fixture验证；不公开照片URL、不混业务备份。原队列120秒等待、生产45秒硬截止/冷却模型不复制。
- 前端131项通过。Python全量352项执行，351通过、1项既有平台相关跳过；日志 `frontend.log`、`python-full.log`。其中原生/API/生产形态和发布定向38项先行通过，之后又加入旧包组件兼容测试并纳入全量。新测试覆盖身份/跨服/目录变化/会话与任务过期、multipart大小/字段/真实格式、上传连接中断/同key幂等、共享网页/原生可信IP与全局队列、取消迟到结果、快照字节、默认关闭、生产拒绝fixture配置及私有schema边界。
- 全量之后又补齐可选OCR依赖的延迟加载：不含OCR组件的应用包也能默认关闭原生并正常冷启动；最终40项原生/生产形态/发布/OCR定向通过，日志targeted-package-final.log。这是后续定向验证，不冒称又跑了一次完整全量。原生上传401还用真实HTTP Expect:100-continue核对在正文传输前拒绝；CLI支持互斥的fixture或用户私有真实平台配置，真实平台模式仍未调用验证。
- 8043真实CPU OCR：已有获准游戏截图attack06.png经原生multipart→原唯一worker→查询与原key恢复，五张地图及顺序全部正确，约5.47秒；结果 `real-ocr.json`。仅是单样本本机观测，不是容量/SLA。微信验证为fixture，不能写成真实微信或小程序模拟器/手机验收。
- 本轮自有8043进程在无未完成任务且核验cmdline/父子PID后更新为最新源码；新worker ready，原会话跨重启仍能用同code/key恢复。实际交付时PID/目录见process-delivery.json，不凭旧PID操作。8033未启停，两服活动版本保持原接手值。29个既有修改文件SHA/大小/mtime全部保持，见preservation.json。

## 仍待验证及配套边界

Docker CLI存在但引擎管道不可用，WSL仅停止的docker-desktop；本轮不擅自启动其他服务。因此未运行本轮Linux/systemd 45秒硬截止/取消后回收/崩溃恢复、nginx -t及真实TLS限流。生产形态夹具证明新owner进入相同队列及过期逻辑，不能替代这些内核/进程验收。后续必须在独立Linux环境完成，不向生产注入故障。

图片安全审核仍未接入。原生配置image_policy默认disabled；隔离fixture显式private_unmoderated仅用于本次私有识图，不代表已审核/合规。未向微信或其他外部服务送图；实际采用什么图片安全策略及平台声明由用户按真实实施协调，不拿OCR当审核。

当前运行JSON、INDEX、MINIPROGRAM_COMPATIBILITY和map_recognition.js等原修改全部不纳入本提交。源码新增mini_local只用于本地fixture，不纳入正式运行包白名单；发布工具已包含必要原生模块、协议与配置模板，并继续校验历史旧包。构正式包仍缺维护侧重新冻结与批准功能/源码范围，必须独立干净检出，不能套旧冻结或覆盖正式score-state。

下一步由用户将本文件、协议和固定源码交给小程序对话：接会话exchange、快照原子缓存、HTTP错误/恢复端口、页面/前后台及应用前绑定复验，再分别记录开发者工具真实会话/uploadFile、iOS/Android真机和用户验收。网站生产配置/部署及体验版上传/审核/发布继续另行授权。
