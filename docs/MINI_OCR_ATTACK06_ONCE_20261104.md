# attack06真实游戏截图单次联调通过

2026-11-04，接手0a97d97。用户明确同意使用已有attack06.png一次，图中的游戏昵称和资源信息可随图发送阿里云审核，接受一次调用费用、失败不重试、暂不手机实图。此授权单独建立，不复用此前合成图预约。

## 来源与执行前检查

原图为外层 `offline-evaluation/maps-20261031-01/samples/attack06.png`，933025字节、1280×720、PNG，SHA256 `4eee6ddf88543d96f826b0258f09668d2e09a4f3f8b493787c0ffe5c4efc1cd7`，与原本地OCR样本固定SHA一致。未修改、裁剪、重编码或更换图片；发送前native_api再次验证文件SHA。图中具体昵称/资源正文不进入源码或回交日志。

单次permit新增kind=user-approved-game-screenshot-once，必须明确synthetic=false、containsGameAccountData=true、userConsentedAliyunGameInfo=true，除此仍只允许1次、指定SHA、失败锁定、禁止恢复。原合成图permit仍要求synthetic=true，默认无permit工程保持零上传。历史驱动文件名check_ocr_synthetic_once_devtools.cjs保留兼容，但已按permit正确区分游戏截图，报告不再硬编码为合成图。

新授权IDmini-ocr-attack06-once-20261104-01，新工程标识c46b941862b9ae503062。官方CLI/SDK实际连接前先核对工程标识；当前运行模拟器的request/upload域名均含https://mini-test.racepick.cn，urlCheck=true，读到时间为2026-11-04T13:36:46.708Z。保持域名、TLS/证书校验，没有改后台或服务器。

真实访客、两服固定原UTF-8快照、83图CN目录与worker ready通过。沿guest/bridge固定交付35bd5c5d2e618b555de3a70c；CN固定快照593ecc7222ceea5856b2f576b4f5bca8、Global e29f52e7f81c3e337985bf05dedb7e88、CN catalog 57876474bd3cd25c283e79a471be99ec76d4e58ed16fa0e2c8ae2a6cdf0b9ced。正式网站活动指针未被拿作测试快照。

## 本次实际结果

| 顺序 | 预期及实际大地图 | 预期及实际小地图 |
|---|---|---|
| 1 | 明珠港口 | 触摸天空 |
| 2 | 冰火岛 | 地心之外 |
| 3 | 海港博物馆 | 飞越城市 |
| 4 | 沙漠迷雾 | 国王的复兴 |
| 5 | 摩登城市 | 富豪之旅 |

**wx.uploadFile一次，HTTP 202；原任务查询5次后五槽全部正确且顺序一致。** 没有上传重试、by-request恢复或旧任务恢复。结果先处于pending_confirmation，原五图为空；驱动验证预期一致后显式执行确认、再次核目录，并验证confirmationApplied=true。仅影响独立工程内存五图，不写本机车库或任何正式账号资料。

服务端契约要求通过阿里云安全准入才能被唯一worker领取；本次取得合法完成结果，支持本次安全门禁后任务执行链路已走通。客户端没有供应商原始回执/账单，因此不另行声称实际账单计数、供应商内部删除时点或平台合规验收。未获取或保存token/code/session_key/OpenID，任务id/key和无关OCR正文不进入回交。

| 事件 | 北京时间 UTC+08:00 | UTC |
|---|---|---|
| 实际上传开始 | 2026-11-04 21:36:48.495 | 2026-11-04T13:36:48.495Z |
| 实际上传202回调 | 2026-11-04 21:36:48.965 | 2026-11-04T13:36:48.965Z |
| 收集五槽结果 | 2026-11-04 21:36:56.637 | 2026-11-04T13:36:56.637Z |

上传回调约470毫秒，上传开始至结果收集约8.142秒，仅一张样图的客户端观测，不是CPU/审核分别耗时或容量/SLA；客户端时钟未宣称与服务器校准。

## 保全、验证与范围

独立证据目录 `offline-evaluation/mini-ocr-attack06-once-20261104-01/` 保存样图元数据/非秘密permit、新独占预约、attempt/once-result.json及截图、CLI私有日志、生成与提交回执。原图留原位，临时模拟器文件在完成后移除，chooseMedia mock已恢复；wx.login/request/uploadFile未mock。运行与生成配置均锁回0额度，预约保留，旧合成图01/02/03预约/报告/回执SHA全部保持。

本轮仅扩展两份本地工具的明确单样图授权类型，Node语法检查和本次实际开发者工具流程通过；运行客户端算法/规则未改，未重跑之前122项全量，也不据此冒称新增全量通过。

结论限定为：**开发者工具中该真实游戏截图的授权上传、任务结果、五图顺序及确认通过。** 相册返回使用受控fixture，不计作真实手机相册、授权拒绝/取消、切网/前后台、iOS/Android或其他样图验收。没有手机实图、账号/B–E、服务器/后台修改、生产操作、正式构包/上传体验版/提审/发布。任何后续传图需要新的范围授权，不能复用本次预约。
