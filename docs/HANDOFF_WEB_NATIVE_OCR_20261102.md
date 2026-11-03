# 请交网站开发对话：开始小程序原生识图后端接通

2026-11-02。用户现在明确要求开始接通小程序识图。共享核心和后端仍由网站分支归口，小程序分支不代写backend、不放宽网页门禁、不自行向其他对话派任务。**请用户将本文件交给网站开发对话执行并回交固定源码/协议。** 本文件可直接作为下一阶段任务，不要求重做已完成的共享核心。

## 请从这里开始

继续使用网站 `map-layout-parser` / `feature/map-layout-parser`，本轮小程序实查网站HEAD `198999a9ff5ca2ad524c50112ac6e03f5f18149f`。先检查实际分支/工作树/并行修改；当前网站数据、INDEX、MINIPROGRAM_COMPATIBILITY和map_recognition.js有未提交修改，不代提交、不覆盖。小程序已经固定接收198999a的五个共享Git blob，并完成真实本地计算及原生模拟器验证，不改这些算法/成绩/规则。

网站本轮归口 `backend/**`、对应测试/配置模板、生产打包工具和网站自己的接口交接文档；小程序客户端归口 `miniapp/**`、客户端测试/脚本及本交接。不要操作小程序树，也不要在两个树同时改公共文件。

请先固定下面协议细节并在网站分支实现默认关闭的原生适配，复用既有唯一OCR队列/worker/配额/模型。只开发和隔离本地验证，不部署生产、不操作微信后台、不上传/提审/发布。审核状态仍未确认通过。

## 需要交付的接口

| 路径（沿原方案前缀） | 必需行为 |
|---|---|
| POST `/api/mini/v1/session` | 接收`code/client_schema:1/request_key`，服务端验证微信临时代码后签发最低权限访客token；不创建网页账号、不要求头像/昵称/手机号、不自动绑定user_id。固定expires_at时间单位、TTL/撤销、签发限流、code一次性和响应丢失/重试语义。 |
| GET `/api/mini/v1/snapshot?server=cn或global` | 同一活动版本原子读取；明确`server/version/capabilities/files`与每文件原始UTF-8文本/SHA/字节数。CN两文件、Global三文件，不重序列化当原文件，不回退另一服。客户端必须先校验快照再计算/识图。 |
| GET `/api/mini/v1/map-recognition/catalog?server=cn` | 同一活动目录/版本绑定，固定会话身份绑定字段或等价语义；只开放中文国服截图。说明上限、worker可用性及任务保留策略。 |
| POST `/api/mini/v1/map-recognition/jobs` | multipart单文件`image`，绑定`server/catalog_version/request_key`。固定字段放form或query的具体位置，受限字段数/长度；先鉴权/预算再有界读取。单文件≤8MiB/≤16M像素，总封装≤8MiB+64KiB，保持实际格式/解码校验。 |
| GET/DELETE `/api/mini/v1/map-recognition/jobs/{id}` | 查询/取消限定同owner、服别、目录版本，固定queued/running/succeeded/failed/cancelled/expired及到期语义；取消幂等，替图无需等取消返回才继续。 |
| 按request_key恢复原上传 | 上传响应丢失时，提供原请求查询或严格同key/同文件幂等恢复方式，并写明未找到/仍在读取/已完成的区分。具体路径由网站交接固定；客户端默认不会用新key重复上传。 |

请保留现有网页任务响应的可复用语义：`id/server/catalog_version/state/result/error/expires_at`。当前网页expires_at为Unix秒，若原生不同须明确。结果保持`schema_version:1/server/catalog_version/status/slots`，恰好五槽且`slot`为1..5；matched带目录身份，ambiguous/unresolved留空，不把未知槽压缩、猜被截断文字或回显无关OCR原文。对应来源为现有`backend/map_recognition.py`/`map_layout.py`。

明确401/403/409/410/413/415/429/503及Retry-After单位/格式：过期会话、owner拒绝、目录变化和过期任务不自动换身份重传。Query的断网/限流/等待超时可继续查同id；中断upload的恢复能力单独说明。所有新增协议均由网站写入固定交接，而非仅在聊天口头同意。

## 边界与配套

- 网页Cookie/Origin/CSRF/raw-body路径不变，不全局放开Origin或multipart，不把Referer/AppID当身份。原生owner有独立命名空间及会话状态，不能取得网页贡献/管理权益；不复制正式账号库/旧测试状态。
- AppID已由用户提供并在小程序project.config.json，属于项目标识。AppSecret/session_key只在服务端；需真实平台配置时由用户安全配置，不把密钥贴回聊天或客户端。没有配置时默认关闭，可用显式fixture做业务测试，但不可算真实微信验证。
- 复用一个OCR模型服务和全局容量，不给小程序另开第二套worker/8任务额度。保留现有取消/队列等待/硬超时、私有图片访问和1小时图片/结果、另留10分钟元数据的策略，并验证原生同样落实；停机时不承诺准点清理。
- 明确图片内容安全策略及失败处理。OCR/格式校验不是内容安全审核；微信/外部审核未接入就如实记未实施，不开户付费、不自行外送图片。
- 新默认关闭环境项、会话schema/目录、Nginx精确路由大小/限流/TLS/可信IP、启动/回退顺序由网站成套列清；本轮只准备，不执行生产。隔离本地服务另查空闲端口和独立状态，不擅自启停/改写8033及其账号库。
- 目前4504/693运行数据未重新冻结，可按已有接收回执SHA显式用于本地测试；不搬732完整维护/工作簿/台账，不构正式包或用JSON覆盖正式score-state。

## 小程序侧已做好与待接线

已完成：原生页面、仅相册单图、预览、五槽核对/页内下拉/确认、真实共享计算、UTF-8/原始字节SHA、安全请求ID、内存会话端口和默认关闭的低层request/upload适配。`miniapp/services/recognition_jobs.js`新增任务生命周期端口（无HTTP路径、无实际连接）：一次upload、轮询/429等待、断网同id恢复、保留上传request_key、取消迟到响应回收、后台暂停/恢复和严格结果/身份/目录校验。它只依赖注入的API，未挂到当前页面，不冒充已接通。

内部API端口为`upload/query/cancel`与可选`recover`；`currentBinding()`必须来自已验证的**原生活动快照与会话**，不是本地`local-unfrozen`版本。identity仅为客户端绑定比较，不作为HTTP可信身份字段；HTTP适配必须用服务端认证。Retry-After先由HTTP适配规范为retryAfterMs。10项隔离测试通过，不是真实OCR或鉴权证据。

接口确定后，小程序侧负责：HTTP/session exchange、服务端快照原子缓存、异步任务页面/前后台接线、重试按钮与取消、当前草稿revision及应用前复验；不能简单把本地service.recognize替换成网页fetch。当前页面仍明确显示识图尚未接入，不请求生产。

## 网站侧完成后请交回

1. 固定源码提交、逐文件归属和完整接口契约（包括快照JSON示例、时间单位/编码、错误体、恢复路径）。
2. 默认关闭配置、独立本地启动方式/端口/状态目录、真实微信验证需要用户提供的最少前置；不要发送密钥或账号库。
3. 网页回归和原生接口测试：owner/跨服/目录变化/过期拒绝、multipart边界、全局配额、响应丢失幂等、取消/硬超时、401/429/503/断网恢复、快照原字节和既有数据保持。
4. 可用时在独立状态让真实已获准截图经过同一个worker，明确是否只用stub微信验证；客户端后续再做开发者工具实际会话/uploadFile、iOS/Android真机和用户验收。

固定提交和契约交回小程序后，即可继续真实接口联调。正式域名/后台配置、生产部署、体验版上传、提审和上线仍另行授权，不因本交接自动执行。
