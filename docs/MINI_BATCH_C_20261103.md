# C：投稿、证据、贡献与个人中心

共用传输见 MINI_FEATURES_COMMON_20261103.md；精确模型见固定OpenAPI。下列路径相对账号前缀，私有调用需账号Bearer/X-Account-ID，写需Idempotency-Key及显式隔离环境。

| 方法/路径 | 输入/分页 | 成功响应 |
|---|---|---|
| GET /submissions/catalog | server=cn/global | server/capabilities/tracks[{big,small}]/cars[{name,title,zones,limits}]/routes/basis/reference_label |
| POST /submissions | request_key须同幂等头；entries 1..20个Score | {ids:[id],batch_id} |
| GET /submissions | scope=mine/review，status空或draft/pending/needs_info/accepted/ignored；q≤100，offset≥0，server可省略或cn/global；每页50 | {total,items} |
| GET /submissions/{sid} | 无query | 下述详情 |
| PUT /submissions/{sid} | {revision,entry:Score} | revision及原业务返回状态 |
| POST /submissions/{sid}/submit | {revision} | {revision,status} |
| POST /submissions/{sid}/images | {revision,data:纯base64}，JSON≤3000000 | {id,revision} |
| POST /submissions/{sid}/images/upload | query revision≥1，multipart仅image，原生wx.uploadFile可用 | 同上；文件≤2MiB，封装额外≤64KiB |
| GET /submissions/{sid}/images/{iid} | 认证下载 | image/jpeg，原私有展示衍生图 |
| DELETE /submissions/{sid}/images/{iid} | JSON {revision} | {revision} |
| GET /contributions/leaderboard | period=month/all/YYYY-MM，公开 | {period,items,enabled_at,as_of} |
| GET /contributions/me | 同period，私有 | {preference,positions,items} |
| PUT /contributions/preferences | {revision,nickname≤30,anonymous:bool} | {revision} |

Score字段：server默认cn、oc默认false、big/small≤100、zone五区/四区、tier高手/理论/普通/自动、car≤150、stars严格1..6或null、route≤40、time数字字符串≤24、notes≤2000、video_url≤1000、unlisted默认false。源校验再核对地图/车辆/区档/星级/OC/跑法能力；草稿可不完整，提交按源规则要求成绩与理论来源说明/证据。Global仅当前已开放五区满星理论。已建sid不能换服；同key/同内容不会重复建稿，跨内容409。

列表item固定基础字段id/batch_id/owner_id/revision/status/payload/decision_reason/review_score/updated_at；按updated_at DESC,id DESC。组件存在时含contribution_info、application及独立未读装饰。详情包含原投稿行、payload、accepted_payload(nullable)、baseline(nullable)、images[{id,digest,url}]、events[{revision,actor_id,action,snapshot,created_at}]、application_scope/local或production、application(nullable)、contribution_info、comparison/basis、same_target及read_cursor。详情读取不自动标记已读。

图片URL已改写为原生前缀；用wx.downloadFile携带账号Bearer/X-Account-ID，得到本机临时文件后展示。普通用户不能读他人投稿/图片；管理员也不能读他人draft，审核需pending之后。上传/删除仅本人draft/needs_info且revision匹配，每条active最多3、累计含历史最多10。源实际格式/动画/16M像素检查及JPEG重编码、最长边2400保留，支持竖图证据，不套用OCR横屏限制。删除按原业务停用证据，历史/审计BLOB保留，不承诺OCR式1小时物理删除；旧历史id仍按原所有权/审核权限读取。没有公开媒体目录或任意服务器路径参数。

multipart重试按图片字节/对象/revision/同key幂等，文件名/boundary变化不重复创建；响应丢失先查feature-operations，不自动新key上传。JSON与multipart是不同路径，不能用同key在两路径交换。视频仅来源链接，不下载/上传/抽帧，不把它当视频文件服务。

贡献positions按月/all/所选period返回本人名次项目，items为每项贡献原记录及sources/events；来源payload/snapshot按原JSON/字符串类型保留，不能自己重算分/权益。榜单period按Asia/Shanghai月份；默认month动态映射当前月，列出达到第50名同分线的项目，不伪造分页。匿名设置由服务器校验，公开昵称不得空/含邮箱符号/控制字符；格式检查不是内容安全审核，未接入审核事实明确，本次业务写只在隔离lab开放。
