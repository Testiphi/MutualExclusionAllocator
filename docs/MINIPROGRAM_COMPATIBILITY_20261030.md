# 微信小程序兼容核查与媒体识别接入边界

用户计划上线微信小程序，框架尚未确定；要求核查当前功能和未来图片/视频识别地图、车库的兼容性。核查对象是本功能工作树（含国际服投稿/版本链），不代表已上线版本。本轮不创建小程序项目、不改生产、不配置微信后台、不接入付费识别、不上传用户媒体。

## 已实施与当前限制

`allocator.js`、`race_scores.js`、`app_state.js` 已补充 CommonJS 导出，保留原浏览器全局绑定与全部计算逻辑。`profile_store.js` 本来就通过注入 request/storage 工作并支持 CommonJS，可继续复用。新增导入测试覆盖无DOM运行、浏览器与模块导入分配结果相同、星级插值与OC分离、车库过滤不写存储。最终前端124项通过；未重复后端全量，因为本轮没有更改后端或业务规则。

这只是共享核心的导入兼容。当前仓库没有原生小程序工程、wx网络/存储适配、原生登录、媒体任务服务或OCR模型，不能宣称微信小程序已可上线。此前Windows、本地浏览器和Node测试不代替微信开发者工具、iOS/Android真机或审核验收。国服/国际服数据及工作簿未改，维护主树的并行数据更新未同步。

## 当前明确冲突

| 范围 | 实际实现 | 小程序适配要求 |
|---|---|---|
| 页面与交互 | index内联UI，document/window、DOM表格、dialog、location/history、Pointer Events | 用原生页面/组件或所选框架重新实现视图；保留当前主题变量和信息层级。不能把HTML/CSS/DOM脚本直接当原生页面导入 |
| 网络与鉴权 | fetch＋HttpOnly Cookie；写API要求精确同站Origin、JSON、有效会话、CSRF、账号ID | 原生网络须有明确客户端会话协议。原网页API会拒绝不满足该边界的请求；不能简单放开Origin或把Referer/AppID当身份 |
| 账号 | 邮箱注册/验证/重置，邮件链接回网页；无微信身份绑定 | 决定原账号登录及绑定流程。微信code仅服务端交换并绑定现有内部user_id，不按同名/同邮箱文字直接合并账号；AppSecret/session_key不下发客户端。角色、停用和会话撤销必须继续生效 |
| 草稿与车库 | localStorage、分服键、按用户草稿和revision；国际车库目前本机保存 | 通过存储接口接wx存储；保留用户＋服别隔离、冲突/配额错误处理。小程序与浏览器本机存储不天然互通，不能自动覆盖旧车库 |
| 版本校验 | crypto.subtle、TextEncoder/Decoder和原始字节SHA；国际原子三件套 | 提供经验证的UTF-8/SHA适配，继续校验原始响应字节和目录版本；不能删校验，也不能用JSON重序列化代替原字节 |
| 证据上传 | FileReader把图片转base64 JSON；API限制约3MB请求、2MB图片，Pillow重编码JPEG | wx.uploadFile是multipart，当前中间件直接不兼容该类型。新增专门二进制上传适配，先鉴权/限额再读取；保留旧网页JSON图片接口，不改所有写API的类型检查 |
| 私有图片 | 图片GET按Cookie会话与投稿权限读取 | 小程序下载请求需带正确会话，再用本地文件预览；或设计短期授权媒体URL。不能为显示图片将全部证据公开 |
| 视频与识别 | video_url仅保存来源链接，不下载；没有视频上传/转码/任务队列 | 独立媒体与异步识别服务，不把长视频塞进base64 JSON、证据SQLite BLOB或同步业务请求；不能把任意外链直接交服务端抓取 |
| 计算 | 分配核心纯JS，但候选生成和结果显示仍在页面中，调度不等于后台线程 | 抽取页面内候选/规则派生逻辑后共用；真机基准决定是否引入Worker。浏览器速度不能当手机流畅度证明 |
| 导航与状态恢复 | URL query/hash预填、登录回跳、beforeunload、页面内通知轮询 | 原生路由和前后台生命周期适配；离开/返回后恢复草稿与任务，重新校验用户/服别/目录版本；长任务不依赖页面持续前台 |

原生方案与web-view方案要分别验收。这里按用户选择的原生微信小程序准备；未假定主体具有web-view权限，也未通过更改X-Frame-Options替代原生适配。

## 登录与API边界建议

适配层应放在业务接口之前，向现有服务提供经过验证的内部账号与会话，而不是复制投稿、贡献、权益、版本和回滚规则。

- 保留网页Cookie/Origin/CSRF路径；原生客户端另用有明确有效期、撤销与绑定语义的服务端会话协议。原生专用入口在未配置时关闭，不能仅凭 `X-Client-Type`、来源头或可伪造AppID放行。
- 原生登录是否使用wx.login、是否先提供邮箱账号绑定，需在客户端方案确定后实现和测试。微信身份不能自动变成管理员，原投稿/贡献/两服选图仍关联内部user_id。
- 客户端用统一request/storage/media/hash/id生成接口承接具体框架API；网页继续原实现。不要让共享算法直接引用wx或Taro，也不把平台API注入正式成绩规则。
- idempotency request_key、revision、X-Account-ID类账号变化检查的业务语义、两服目标键、数据能力门禁均保留；原生失败重试不能重复建稿、加分或覆盖版本。
- 首期用户功能可以原生化，审核/正式发布后台可以继续网页；若迁移管理功能，仍须独立验收超级管理员重验、逐项确认和审计，不因为微信登录而跳过这些门禁。

本轮没有放宽安全边界，也没有新增可被生产调用的原生鉴权入口；相关认证改造和迁移需作为后续明确开发任务完成。

## 图片/视频识别的统一接线

建议采用“用户选择媒体→私有上传→异步识别→候选校验→用户确认→既有选图/车库草稿”的流程。识别与投稿证据分开存储和处理：证据接口的JPEG重编码与2400像素缩放可以继续用于证据展示，识别应使用获准处理的原图/视频帧，不能只拿压缩后的展示图识别小字。

### 逻辑接口约定（设计稿，尚非已发布API）

- 上传返回不透明 `media_id`，记录所有者、image/video类型、实际MIME/大小、哈希、尺寸/时长/旋转和保留期限。平台临时路径不能当服务端资源ID，不接受客户端提交任意服务器文件路径。
- 识别任务输入：`schema_version`、`request_key`、`media_id`、目标 `maps/garage`、显式 `server`、`catalog_version`、可用分区/档位、客户端当前草稿revision。用户未明确的服别/分区不能由模型猜测后直接写入。
- 异步返回 `job_id/status`，结果轮询或受支持推送；采用queued/running/succeeded/failed/cancelled状态，任务失败可重试而不重复创建。客户端切后台不要求长HTTP请求维持在线。
- 每个候选包含原始文字、目录匹配候选、置信信息、歧义/冲突、证据定位（图片区域或视频frame_ms/区域），并返回任务所用目录版本。置信度不是“识别正确”的证明，不用一个阈值自动授权写入。
- 地图候选必须落到当前服别认可的大地图/小地图身份；车库候选必须落到当前服别车辆身份，星级与OC明确区分已识别值和unknown。未识别到某辆车不等于用户没有这辆车；遮挡、不完整视频和只拍到部分车库不得自动清空其他选择。
- 同一视频多帧识别的同车/同图去重，保留帧来源；昵称、车型、EVO/普通、OC、星级有冲突时交用户确认，不把相似名称直接合并。新增别名、地图映射、车辆规则交维护侧处理，不让识别模型修改权威规则。
- 结果到达时再次检查任务所有者、当前账号、服别、目录版本和草稿revision；账号切换、数据更新或草稿已编辑时不给旧结果自动覆盖机会。
- 用户确认后只进入既有临时选择/草稿；显式“保存车库”或原投稿审核链继续生效。识别不直接写正式成绩、积分、权益、JSON、Excel或维护台账。

### 媒体服务的配套要求

媒体传输使用专用上传接口或私有对象存储短期上传凭证；不要全局提高现有业务请求上限。上传、下载和任务查询按所有者鉴权；限制实际文件类型、总量、视频时长、解码像素和任务并发。视频帧处理/识别在后台任务执行，不能长期占用现有登录/投稿请求的工作线程。

后续若引入对象存储、worker、识别供应商或更大媒体上传，需要另外列出服务器进程/队列、存储、预算、域名、Nginx上传与超时策略和备份/回退边界。当前仓库的3m请求上限和业务限流不能冒充已支持视频处理。原视频及派生帧的生命周期、删除与备份策略也须明确，不能无限保留或默认复用为训练样本。

微信侧须按实际媒体能力完成隐私声明/授权交互，取消授权或选择不上传时可继续手动选图/录入。以上是功能所需接线条件，本轮未配置微信后台或替用户授予权限。

## 后续顺序与验收

1. 确定客户端框架/最低基础库与账号绑定方式；共享核心保持当前模块接口，不先按某个框架重写全站。
2. 明确并实施原生会话、request/storage/hash/router适配，在隔离库验证登录/退出/停用/账号切换、国服/国际服、投稿证据、权益和版本快照；网页原流程持续回归。
3. 先接图片选取、私有上传和任务协议，用固定本地样本验证地图/车库候选确认流程，再选择并获授权接识别模型。最后扩展视频抽帧/合并/后台恢复，不先把所有媒体堆入现有图片接口。
4. 微信开发者工具、iOS/Android真机、前后台/弱网/取消、无权限与存储不足分别验收；核对合法request/upload/download域名、证书和隐私接口。服务端/云端配置与发布仍由运维对话另行执行。

## 核查来源

代码：`backend/app.py`的会话与boundary、`backend/submissions.py`的Picture/图片鉴权、`production/nginx-https-location.conf`、`api.js`的存储与哈希、`submissions.js`的FileReader/DOM、纯计算模块及ProfileStore。

官方文档于2026-10-30只读核对（网页工具无法打开时，直接读取同一官方地址并解压gzip；摘录保存在本地归档/miniprogram-compatibility-20261030/OFFICIAL_DOCS.json）：

- [网络与域名](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)
- [wx.request](https://developers.weixin.qq.com/miniprogram/dev/api/network/request/wx.request.html)
- [wx.uploadFile](https://developers.weixin.qq.com/miniprogram/dev/api/network/upload/wx.uploadFile.html)
- [wx.chooseMedia](https://developers.weixin.qq.com/miniprogram/dev/api/media/video/wx.chooseMedia.html)
- [wx.login](https://developers.weixin.qq.com/miniprogram/dev/api/open-api/login/wx.login.html)
- [隐私协议开发指南](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/PrivacyAuthorize.html)

小程序账号主体、AppID、域名配置、实际权限和平台审核状态未核对，未据文档推定用户已经具备上线条件。框架未确定前，不称已经完成原生端兼容。
