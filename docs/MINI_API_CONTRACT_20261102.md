# 原生访客、快照与截图识别协议 v1

2026-11-02；网站分支归口实现。源码提交及逐文件SHA见本轮外层 `offline-evaluation/mini-api-20261102-01/commit-receipt.json`，提交号随交付回传。本文为客户端固定接线协议；共享计算继续使用198999a，不改算法/成绩/车辆规则。原生路由默认关闭，本轮未生产部署、配置微信后台、上传/提审/发布小程序。

## 传输、身份与错误

前缀 `/api/mini/v1`。除POST session外，全部请求使用 `Authorization: Bearer <token>`，不使用Cookie、Origin、客户端identity、Referer或AppID作为HTTP身份。带Origin/Cookie或OPTIONS请求403；无CORS放行。网页原Cookie/Origin/CSRF/raw上传路径保持。

所有JSON响应UTF-8，`Cache-Control:no-store`。时间戳均Unix秒（整数），duration/TTL/HTTP Retry-After均秒；客户端HTTP适配转换成 `retryAfterMs = Number(header)*1000`。不返回HTTP-date形式。令牌不得放URL/日志/持久客户端存储；进程内存丢失时重新登录，不能借新身份访问或重传旧任务。

业务错误体：`{"schema_version":1,"code":"SESSION_EXPIRED","detail":"说明"}`。边缘Nginx自身429/413可能为HTML，客户端按HTTP状态及Retry-After处理，不要求能解析JSON。

| HTTP | code例子 | 客户端处理 |
|---|---|---|
| 400 | INVALID_QUERY / INVALID_MULTIPART / INVALID_SESSION_BODY | 修复输入；缺失、重复、额外query字段拒绝 |
| 401 | SESSION_REQUIRED / SESSION_INVALID / SESSION_EXPIRED / PLATFORM_CODE_REJECTED | 保留地图/车库草稿，显式重新登录；不自动换身份重传旧图 |
| 403 | NATIVE_ONLY / JOB_FORBIDDEN / RECOGNITION_SERVER_DISABLED | 不重试跨owner/跨服任务；国际仅手选计算 |
| 404 | NATIVE_DISABLED / JOB_NOT_FOUND | 前者未启用；后者不证明可以新key重传 |
| 409 | CATALOG_CHANGED / REQUEST_KEY_CONFLICT / UPLOAD_READING / UPLOAD_REPLACED / CODE_ALREADY_CLAIMED / CODE_EXCHANGE_UNCERTAIN | 目录更新或身份不确定不自动重传；UPLOAD_READING带Retry-After，查询原key |
| 410 | JOB_EXPIRED | 原图/结果到期；保留草稿，不自动换key上传 |
| 413 | BODY_TOO_LARGE / IMAGE_TOO_LARGE | 单图或总封装超限 |
| 415 | JSON_REQUIRED / MULTIPART_REQUIRED / IMAGE_TYPE_UNSUPPORTED | 修复请求编码/实际图片格式 |
| 422 | IMAGE_INVALID | 解码、尺寸、像素、动画或实际格式不符；保留手选 |
| 429 | RATE_LIMITED / PLATFORM_RATE_LIMITED / OCR_LIMITED / UPLOAD_READ_LIMITED | 按Retry-After等待；查询可继续同id，上传先恢复原key |
| 503 | PLATFORM_UNAVAILABLE / OCR_UNAVAILABLE / SNAPSHOT_UNAVAILABLE / READ_TIMEOUT / UPLOAD_INTERRUPTED / NATIVE_STATE_UNAVAILABLE / RECOGNITION_DISABLED | 查原key或同id；配置关闭需准备环境，不能无限自动上传 |

应用429均给正整数Retry-After；可恢复503通常给2/5/30秒，RECOGNITION_DISABLED不含重试承诺。未列code不能推导为可重传，优先保留本地草稿。

## POST /session 与 DELETE /session

POST为 `Content-Type:application/json`，≤4096字节，无query，正文恰好三个字段：

```json
{"code":"wx.login临时代码","client_schema":1,"request_key":"至少16最多80个ASCII字母数字下划线横线"}
```

服务端固定向微信HTTPS code2Session端点验证，8秒平台超时、8192字节响应上限、禁止重定向，不把平台错误原文/URL/凭据返回客户端。AppSecret只从服务端私有文件读取；V1不读取资料/手机号，交换返回的session_key不使用、不保存、不下发。平台OpenID仅存用途隔离HMAC摘要，无网页账号/角色/user_id绑定。

成功200：`{"schema_version":1,"token":"不透明字符串","token_type":"Bearer","identity":"会话比较标识","expires_at":1793...,"expires_in":3600}`。TTL固定3600秒，不滑动续期；新session有新owner，即使同一平台身份亦不继承旧任务。identity供客户端绑定比较，不作为请求认证字段。

同code+同request_key且原会话仍有效，返回同token/identity/到期时间，平台只交换一次，可恢复响应丢失。code配另一key返回409。平台已拒绝、网络不确定、进程在交换中退出或并发交换未完成时，旧code保持占用：409 CODE_EXCHANGE_UNCERTAIN，不再次交换；取得新的wx.login code和新的会话key。code占用摘要保留24小时。首次平台失败可能返回401/429/503，后续重试同code会409；这与OCR上传恢复规则不同。

签发限流：可信IP每600秒10次，全局每600秒100次（含重试/失败）；原生总请求IP每60秒300次、会话每60秒120次。DELETE同路径（Bearer、无query）撤销当前会话，之后401；不删除草稿或自动取消/清空其他任务。该会话不能重新获得原token。关闭原生入口后全部路由404，不影响网页。

## GET /snapshot?server=cn 或 global

每次从现有同服活动版本管理器一次读取，返回同一不可变版本的全部文件。CN恰好cars.json、gauntlet_data.json；Global恰好cars.global.json、gauntlet_data.global.json、global-data-manifest.json。不跨服回退或从维护完整表补数据。

结构示意（text内容仅演示转义，不可作为运行种子）：

```json
{
  "schema_version":1,"server":"cn","version":"活动版本ID",
  "catalog_version":"绑定活动版本及成绩原始字节的64位SHA或null",
  "identity":"当前原生会话标识",
  "capabilities":{"zones":["zone5","zone4"],"tiers":["理论","高手","普通","自动"],"map_recognition":true},
  "files":{"cars.json":{"text":"{\"cars\":[]}\n","sha256":"原文件SHA256","bytes":12},
           "gauntlet_data.json":{"text":"原始UTF-8文件全文","sha256":"原文件SHA256","bytes":12345}}
}
```

Global能力只含zone5/理论、map_recognition=false、catalog_version=null。CN未启用识图时也可读取计算快照，map_recognition=false/catalog_version=null。客户端先核对server/identity、文件白名单、每份text重新编码UTF-8后的SHA及字节数，再验证国际manifest/数据绑定，整体成功后原子替换缓存。校验对象是**原文件字节**，不是HTTP封装JSON、Content-Encoding压缩字节或解析后重新序列化的对象。标准HTTP客户端先解压传输层，解析封装、恢复text、UTF-8编码；保留文件换行。失效快照不得部分替换当前缓存。

给共享核心的适配对象仍为 `{server,version,cars:parsedCars,data:parsedScores}`；不要把catalog_version当活动version。目录/任务绑定使用catalog_version，后端校验本次目录与活动快照一致，读取期间变化409。

## GET /map-recognition/catalog?server=cn

成功含 `server:"cn",version,catalog_version,identity,maps:[{big,small}],max_bytes:8388608,max_pixels:16000000,max_envelope_bytes:8454144,worker,retention_seconds:3600,metadata_grace_seconds:600,content_safety:"not_integrated"`。version与catalog_version是同一目录绑定值；identity须与已验证快照/当前会话一致。worker为ready/starting/unavailable等现有状态，非ready时客户端保留手选并等待；接口并不启动第二个worker。Global返回403，不猜截断中文、不推进英文/拍屏/视频识别。

## 上传：POST /map-recognition/jobs

query恰好 `server=cn&catalog_version=<64位SHA>&request_key=<16..80 ASCII key>`；三个字段**不放form**。multipart/form-data恰好一个文件part：`name="image"`，filename≤255字符，part头≤8192字节，不接受其他字段、多个文件、重复part头或额外尾部数据。HTTP库负责生成boundary。整包≤8454144字节，单图≤8388608字节、≤16000000像素；仅静态PNG/JPEG/WebP、完整横屏等原校验继续适用。image/png、image/jpeg、image/webp按实际解码复核；wx.uploadFile发application/octet-stream或不发part MIME时，先按文件签名识别，再做同样完整解码验证，任意二进制仍拒绝。

读取前执行Bearer认证、会话/IP预算与共享队列容量检查；请求体流式累计有界，20秒读取截止。原生同时读入最多8个、每owner最多2个，读取占用30秒租约，不是另一套OCR任务容量。实际入队仍走唯一JobStore的原子事务：网页+原生合计8个待处理，每owner2个，owner与可信IP各20次/600秒。生产可信IP摘要与网页完全共用，不各开20次额度。重试同key恢复已提交任务不再消耗新任务额度，仍受请求和读取限制。

202返回完整任务形态：`id/server/catalog_version/state/result/error/expires_at`。相同owner+key+文件SHA+目录返回同id，换文件/目录409。新建key用于一次用户明确选择的上传；断网和响应丢失不能直接改key重传。

## 恢复：GET /map-recognition/jobs/by-request

query与上传三个字段完全相同，Bearer同会话：

- `{"recovery":"found", ...完整任务字段}`：队列已提交，可能尚未开始或已完成；继续查同id。即使上传响应在入队后丢失，仍从共享队列按owner+key恢复。
- `{"recovery":"reading","retry_same_key":false}` + Retry-After:2：另一请求仍在读取；继续查原key。
- `{"recovery":"interrupted","retry_same_key":true}`：读取中断/拒绝/租约超过30秒且无队列任务；可按原key、同文件、同目录重试一次上传。
- `{"recovery":"not_found","retry_same_key":true}`：尚无保留记录；可能旧请求未到达。只允许原key/文件重试，不能断言服务端从未收到网络数据。若旧请求随后提交，唯一键事务仍避免重复任务。

恢复不会返回其他会话任务；401/403/409/410不要自动重传。需要用户改图/目录重新确认时使用新key。重复上传与原读取并发时409 UPLOAD_READING；租约失效的旧读取无法发布新结果。

## GET / DELETE /map-recognition/jobs/{id}

query恰好server=cn/catalog_version，Bearer同owner。返回完整任务字段；到期时间为整数Unix秒。任务状态queued/running/succeeded/failed/cancelled；expired为内部到期状态，HTTP410 JOB_EXPIRED，不作为正常可继续处理的任务返回。清理元数据后按id可能404，原key保留记录可410；会话有效期与到期拒绝仍优先适用。

DELETE幂等返回state=cancelled、result=null；立即移除图像，不发布迟到结果。客户端替图/退出不用等DELETE才继续；正在执行的CPU解码不承诺即时中断，继续受唯一生产监督者45秒硬截止/子进程回收约束。queued等待120秒失败；模型启动120秒、滚动5分钟3次重启/冷却维持。查询断网、429或客户端等待超时后可继续同id，不能重复上传。

成功result仅返回 `schema_version:1,server, catalog_version,status,slots,needs_user_confirmation:true`。slots恰好5个且slot=1..5；matched带当前目录big/small，ambiguous/unresolved两者null。保留原解析器complete/partial/rejected状态；不返回observed、boxes、diagnostics或与地图无关OCR原文。应用前客户端再次核对会话identity、server/catalog_version、草稿revision，五图核对确认后才填入。

图片/结果1小时，元数据另留10分钟；取消/失败按现有队列处理，任务媒体仅队列私有目录，无公开媒体URL、不入长期业务备份。服务停机时不承诺准点删除。会话与队列分开存储，取消不会创建账号、投稿、积分、权益或正式成绩写回。

## 验收与剩余边界

本轮使用新独立8043及新状态，从接收SHA显式读取4504/693，未重新冻结。真实attack06.png通过原生multipart→同一个既有CPU worker→查询/原key恢复，5槽顺序正确，单样本约5.47秒；微信交换为显式fixture，不是真实微信鉴权/开发者工具/手机证据。原生生产形态测试验证可信代理、跨网页/原生同IP配额、队列过期等；真实Linux/systemd硬截止与Nginx运行时仍待现场隔离演练，不以Windows夹具代替。

图片安全审核未接入。默认image_policy=disabled；仅在隔离fixture显式选择private_unmoderated，语义为私有识图用途/格式/所有权/期限控制，**不是已通过安全审核**。生产是否采用此策略或接入审核由用户按实际平台要求确定；本轮未向微信内容审核/第三方传图、开户或付费。

客户端归口miniapp/**、session exchange、原子快照缓存、HTTP错误规范化、任务端口/页面/前后台接线；网站归口本协议/backend/模板/发布工具。不要只把本地recognize替换为网页fetch，也不要搬账号库或改共享计算。配置与本地启动、生产配套及回退见 MINI_DEPLOYMENT_20261102.md。
