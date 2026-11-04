# 手机首轮OCR失败：域名门禁、额度保留为已使用

2026-11-04，接手e9632c6。用户回交手机报告并反馈反复选图后“上传并识别”才可点，最终WX_REQUEST_FAILED/600002、额度已用完。补充设备为iPhone14 / iOS27.0.1 / 微信8.0.79，使用刚生成二维码；这是用户报告，不扩展为其他系统或设备。

## 已知与未知

- buildId=501ec160cfa4c9d46b57，与已交付phone-ocr相同。本报告wx.uploadFile计数1，任务查询/恢复/取消均0，taskKnown=false，无五图结果，原手选五图为空。反复选图或按钮交互不能直接当作多次实际上传。
- 原始错误domain_rejected / errno600002，HTTP状态null；实际上传调用窗口为2026-11-04T14:46:16.922Z–14:46:16.925Z，即北京时间 **22:46:16.922–22:46:16.925 +08:00**，约3毫秒。不能把此失败算作OCR服务处理失败，也不能据客户端报告确认服务器收图、阿里云调用或实际费用。
- 官方[Errno表](https://developers.weixin.qq.com/miniprogram/dev/framework/usability/PublicErrno.html)实际读取到600002=url not in domain list；[网络文档](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)说明request/uploadFile/downloadFile等各自须配置通讯域名。官方原文摘录与读取HTTP200记录在外层official-reference.json，不依赖第三方“关校验/清缓存”建议。
- 新二维码这一事实排除了“用户自述一直扫旧二维码”的简单解释，但不能据此断言平台传播/手机缓存、所用AppID或微信版本中哪一项导致门禁未生效。没有直接读取手机的有效上传域名列表，也不将桌面列表当成手机生效证据。
- 当前工具只读复核（14:56:18.953Z）显示urlCheck/requestConfigured/uploadConfigured均true，限桌面当前模拟器。此前对原项目的SDK读取不可用，没有假装通过；随后在新零上传诊断工程读取成功。未登录/发图、改后台或更改任何安全设置。
- 预约spent、额度0保持。taskPhase=recoverable是通用传输层状态，不代表手机授权允许重传；无id时canResume=false、禁止by-request。没有清预约、换授权ID、新建可上传额度或自动重试。

## 已修交互

选图入口此前不显示已选成功和上传前置缺项，换图/前后台又会重置同意项，按钮仅变灰，容易导致用户重复打开相册。不能仅凭截图确认用户每次具体时序，但上述UI缺口已在代码确认。

现在增加：相册单次打开保护、打开/已选择/取消/拒绝状态；明确提示“先核对目录”“先选图片”“需勾选同意”“可上传一次”“本次额度已使用”；spent按钮显示“额度已用完”。不改变单次同意或安全门禁，不自动上传，不因为交互修复重置授权。131项客户端测试通过，含连续点选只开一次相册、后台返回刷新、缺项提示、诊断零额度即使空存储也无法上传、AppID只输出相等布尔值且不回显标识。

## 零上传诊断工程（可扫码，只看报告）

新目录：

`E:\hzz\work\MutualExclusionAllocator\offline-evaluation\mini-phone-ocr-failure-20261104-01\diagnostic`

该工程沿用原预约键，但磁盘配置直接锁maxUploads=0/uploadDomainDeclared=false/diagnosisOnly=true，即使原预约不存在也不允许发图，不提供相册/上传按钮，也不自动登录或请求网络。页面只读本机运行信息与预约状态。expectedAppId仅在忽略的本地生成文件，报告输出appIdMatches布尔值，不输出AppID明文；另输出platform/system/微信与SDK版本，不读取或发送昵称/OpenID等资料。

已由官方SDK核对最终工程编译及唯一标识，所有接口计数0、无异常；截图已看。预检中DevTools平台也阻止额度，磁盘手机额度0。本轮没有消耗新审核调用或让工具替用户预览。

用户下一步只需在此工程手动生成预览，手机扫码后直接回传底部报告，重点device.appIdMatches、phoneUiRevision、reservationState；不用选图、勾选或上传。保留原缓存/预约，不卸载或清数据。若要核对平台，仅只读查看与此小程序相同AppID下的uploadFile合法域名行是否精确含https://mini-test.racepick.cn，不用更改条目、不回传密钥。当前不需新增付费授权，先明确手机生效状态。

原用户报告保存在user-phone-report.json，设备补充在user-device.json；原phone-ocr工程、permit/生成/提交回执保持原SHA，主工程与车库不修改。后续任何新实图必须另外明确授权，当前手机OCR仍未验收通过。
