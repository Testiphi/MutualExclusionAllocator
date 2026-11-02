# 原生识图接线与网站车库行为同步

2026-11-03。接收网站c26a7088efba783b69baf986f291e593d8aa411d的固定协议/部署说明/提交回执，18项文件SHA核对一致；共享计算五模块仍198999a。仅修改小程序客户端、自有测试和文档，未改网站后端/数据/公共文件。用户后续扩大为全网页镜像，见WEB_MIRROR_SCOPE_20261103.md；当前不宣称全镜像已完成。

## 接线

- 原生访客session JSON、Bearer request、单image multipart上传及query参数按固定协议实现；token仅内存。fixture显式限制开发者工具+回环HTTP，正常平台配置要求HTTPS并使用真实wx.login；未配置AppSecret或调用微信真实验证。
- 快照按server/identity/精确文件白名单、原UTF-8 SHA/bytes及国际manifest整体验证后才更新内存context/缓存；按服务origin/服别隔离缓存，无令牌。坏快照不部分替换，离线仅使用已验证计算缓存，OCR需重新连接。
- 目录版本和活动版本分别处理，任务使用catalog_version；五槽结果转换回活动快照供controller核对。开始/重试/恢复/确认前复验会话/目录，编辑使旧结果失效。后台暂停保留同job，前台可继续查同id；未确认upload响应只按原key恢复reading/found/interrupted/not_found，不盲目用新key重传。
- 401不自动换身份重传；429/HTML边缘错误与Retry-After秒转换，真实错误不清地图/车库。应用前异步复验成功才填五图；所有识别结果仍需用户确认。
- 图片按实际原字节指纹限制同key恢复同文件；文件系统跨JS执行域ArrayBuffer改为本地Uint8Array规范化，修复真实工具中instanceof误报大小变化。恢复已有任务允许worker忙，不误把忙碌当任务不可查询；新上传仍按ready门禁。

## 本地环境与安全边界

最初使用交回的8043和fixture-code-2/原request_key恢复同会话，未持久token。该会话按3600秒实际到期（检测时已过期约86秒）；未清库、复用code续期、修改TTL或放宽验证。

依据交接允许的新建隔离lab方式，新建本轮环境：

- origin `http://127.0.0.1:8044`，fixture-code-1 / `client-fixture-session-20261103`，仅本机工具联调。
- lab `.score-version-sandboxes/0194da463148eb76832bbb68`；原生访客状态 `.mini-session-sandboxes/f8a382e727bad9d7be9159bc`，均由网站mini_local create新建，运行数据逐文件SHA一致，不复制旧账号/队列。
- 8044在创建前无监听；由工具可管理的exec会话启动（session7314，观察PID54292），不是生产服务。隐藏Start-Process启动曾被自动策略拒绝，改为可管理前台服务后成功；没有绕过凭据/安全门禁。后续操作仍须核对实际PID/cmdline，不能按本文旧PID启停。
- 原8043及8033未启停/清库。新环境调用原RecognitionService/唯一worker，不部署第二套模型；这是独立新lab的测试worker，不等于Linux生产监督者/45秒回收验收。
- 开发者工具更新重启后重建连接；用户手动勾选本地“不校验合法域名…”后回环HTTP可用。该设置不等于真实手机合法域名/TLS，不由代理代改。后台/生产/平台声明未操作。

配置生成：prepare_miniapp.cjs新增--native-origin及显式fixture-code/key参数，生成物仍被忽略；无原生参数默认关闭，不包含AppSecret或token。当前生成配置指向本轮8044fixture，不能直接作为体验版配置；会话到期需新环境或用户安全配置的真实平台验证，不能换key重用旧code。

## 用户要求的同步

补齐筛选后全部点亮、当前分区全部清空、字母/性能分降升序、等级筛选、昵称/真实标题搜索；方案摘要含逐槽选车及Σ优先级，算法顺序不变。车辆改为按名称自然宽度排列。星级、方案和SC也使用页内下拉，无原生滚轮。有效星级由共享核心计算，切四区显示正确上限但保留五区原输入。恢复车库保留当前地图/区档，未保存选择先确认，不自动覆盖账号车库。

## 实际验证

- 最终Node客户端/共享/适配测试57项通过，包括跨realm文件、原始UTF8、错误/恢复、原子缓存拒绝坏文件、离线、busy任务恢复、排序/筛选、批量操作和恢复地图语义；日志/最终机器回执另存本轮外层。
- Node HTTP适配先经8043真实CPU识别获五图（无真实微信）；随后在新的8044，以开发者工具实际wx.request/wx.uploadFile再次通过。
- 官方automator仅mock相册返回获准attack06.png临时路径，未mock request/uploadFile/worker。临时图片SHA `4eee6ddf88543d96f826b0258f09668d2e09a4f3f8b493787c0ffe5c4efc1cd7`；不向外部/生产送图。
- `verified/native-ocr-report.json` success=true，5组检查、exceptions=[]、storageRestored=true：双服原字节快照、车库/排序/星级、真实CPU五图顺序、模拟hide/show同id且uploads=1、确认前复验和后续共享计算/方案选择。所用SDKVersion3.17.5、390px devtools；工具本轮已更新，未从截断标题补造完整构建号。
- 五图依次：明珠港口/触摸天空、冰火岛/地心之外、海港博物馆/飞越城市、沙漠迷雾/国王的复兴、摩登城市/富豪之旅。
- 用户已有本机local草稿未迁移/覆盖；测试备份并恢复native-fixture两服草稿和视图偏好，移除仅本次写入的临时图片，保留原缓存/日志/失败报告。无token写入存储或测试报告。

证据根：`offline-evaluation/miniprogram-native-integration-20261103-01/`。first/second/final等目录保留未完成/失败的阶段；verified为最终通过。首次星级操作前控件未滚入稳定位置、一次工具reload元数据未就绪、fixture到期、ArrayBuffer跨realm与busy误拒绝均保留记录；不把它们抹成通过。失败报告中首轮预设upload标志已单独纠正说明，最终标志按实际执行填写。

## 限制与下一步

fixture平台身份、受控图片选择、本机CPU、模拟页面生命周期不等于真实微信登录、手机相册/真机前后台、系统级45秒回收、容量或审核通过。图片内容安全仍未接入，本地private_unmoderated不是已审核策略。真实手机还需用户安全配置服务端AppSecret、真实wx.login、隔离HTTPS/合法域名、图片策略和iOS/Android分别验收。未推送、正式构包、上传/预览分发、提审、发布或生产操作。

下一步先确定用户主体类型，以选择完整网页镜像复用路径；不可继续将当前原生四项实现写成所有网页功能均完成。
