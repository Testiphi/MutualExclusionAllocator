# 手机uploadFile域名门禁：只读排查摘要

2026-11-04，接手a40c726。供用户审阅/协调后续平台排查，本文件没有对外发送，不授权传图或新审核费用。

## 已有证据

- 设备：iPhone14、iOS27.0.1、微信8.0.79，零上传诊断实测SDK3.17.6。
- 手机AppID与本地生成配置相等（仅布尔true，明文不入报告）；新二维码，buildId与本轮零上传工程相符。不是据未经确认的设备/截图推定版本。
- 用户原样回传同一小程序后台uploadFile合法域名：`https://mini-test.racepick.cn`。它与客户端目标完全一致，无显式端口。后台保存的大致时间尚未提供。
- 桌面模拟器当前有效request与upload列表均含目标origin，urlCheck=true；同AppID开发者工具在21:36的已获准attack06单次实图实际返回HTTP202，任务五图及顺序正确、确认通过。该事实不能当作手机域名列表已生效。
- 手机此前真实访客与双服快照成功；仅uploadFile在2026-11-04 **22:46:16.922–22:46:16.925 +08:00** 返回 `WX_REQUEST_FAILED`、`domain_rejected`、`errno=600002`，无HTTP状态、无任务id。不能据此证明服务器收到图片或确认审核/费用。
- 原手机构建的地址构造本地执行确认HTTPS主机为mini-test.racepick.cn，无`:443`，path=/api/mini/v1/map-recognition/jobs，query仅server/catalog_version/request_key。没有读取真实图片或调用真实网络，不冒充手机抓包。
- 当前零上传诊断：request/upload/query等全部0，diagnosisOnly=true，预约spent、额度0。无相册/上传入口，不自动登录/请求网络，不重置或清理本机数据。

官方[Errno表](https://developers.weixin.qq.com/miniprogram/dev/framework/usability/PublicErrno.html)将600002定义为URL不在安全域名列表；[网络配置文档](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)要求各API使用对应合法域名，显式端口须匹配。现有证据不支持为了排除此错误而改OCR、服务器证书/路由或关闭校验。未查到足以对本例承诺“等待X分钟必生效”的官方依据。

## 尚待区分

1. 用户添加uploadFile域名后是否完整关闭过手机微信进程再打开，当前已请求文字澄清。若从未完整重启，手机继续持有先前配置是优先排查假设，不是确认原因。不能把普通后台切回与完整进程重启混为一谈。
2. 若要做无损环境重新加载，只正常关闭本次小程序、把微信从后台关闭再打开；不退出登录、不清缓存/数据、不删除小程序或重装。随后仅打开零上传诊断页确认预约仍spent/额度0，**不通过新增上传判断是否恢复**。这一操作本身不构成域名修复成功证据。
3. 若此前已完整重启，或后台条目精确匹配后仍存在同类现象，需要平台提供手机端有效域名配置/生效机制的诊断。现阶段不直接断言iOS/微信版本bug，也不为了“验证缓存”消耗新图片费用。

## 可交平台方的具体问题

在上述同AppID、新预览二维码、后台uploadFile条目与请求origin精确匹配、工具域名校验开启且桌面实际成功的条件下，iOS客户端仍返回600002：

- 手机的有效uploadFile域名列表在何时/何处更新，是否与预览上下文或既有进程有关？
- 是否存在微信8.0.79 / iOS27.0.1 / 基础库3.17.6的已知限制或异常？请区分已知问题与猜测。
- 有无保留小程序本机数据、且无需再次传图或关闭安全校验的支持诊断途径？

对外协调时，AppID由用户通过平台自己的必要私有渠道提供，不贴本文件或公开日志。不要提供AppSecret、token/code/session_key/OpenID、Authorization、请求query值、图片正文或昵称等无关业务数据。本聊天未提交帖子、工单、通知或跨对话派工。

本轮只有记录更新；无新wx.uploadFile、无RacePick API、无新可上传预约、无费用授权续用，也未执行手机重启。原报告和预约保持。任何后续真实上传仍需用户另行明确范围。
