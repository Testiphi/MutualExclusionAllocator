# 第一阶段真实微信客户端验收

2026-11-04，小程序工作树 `feature/miniprogram-v1`，接手基线76985b2。仅授权访客会话与两服快照；OCR、账号/B–E、上传、提审及发布仍关闭。

## 已执行

用户回交隔离HTTPS激活材料，并明确确认已添加request合法域名 `https://mini-test.racepick.cn`，没有要求添加uploadFile/downloadFile域名。网站当前固定源码 `0b97dae9e1003c1bc2c4c5b7a189b81cb4002112`；本轮只读参考其激活回执和协议，未改网站树、服务器或微信后台。

原始激活回执位于网站树 `docs/MINI_GUEST_STAGE1_ACTIVATION_RECEIPT_20261104.json`。客户端期望版本与五文件SHA/字节数逐项匹配回执，单独固定到 [非秘密期望清单](MINI_STAGE1_EXPECTED_20261104.json)。注意b57d97a8是冻结ID，不是Git提交；准备时第一次误用Git对象查询失败，未发生配置修改或网络调用。保留该阶段生成的disabled工程，随后按激活回执核对并生成新工程；不将失败写成通过。

网络探针额外约束本次固定交付：两服版本、五文件SHA/bytes、Global dataset、map_recognition=false和catalog_version=null。服务自洽但不是本次交付的快照也拒绝。session与snapshot的identity仅在内存比较，不写报告；code、key、token均不写存储或输出。探针只允许一次session及两服snapshot路径，不调用DELETE session或任何账号/业务/上传接口，不写车库。

官方CLI打开独立工程后，用本机已安装miniprogram-automator通过9421连接，未mock wx.login或wx.request。真实调用结果：

- wx.login 1次、POST session 1次成功；GET CN / Global各1次成功。
- CN版本593ecc7222ceea5856b2f576b4f5bca8；Global版本e29f52e7f81c3e337985bf05dedb7e88，五份原UTF-8 text重编码SHA/字节数全部匹配，国际三件套与数据集绑定通过。
- session与两服snapshot identity一致；两服识图false、catalog_version=null。
- 工程setting.urlCheck=true，未携带project.private.config.json，不关闭合法域名/TLS/证书校验。用户确认域名登记，加上本次SDK实际成功构成本阶段证据；不声称读取过微信后台配置。原始探针报告domainRegistrationVerified=false指探针自身不能证明后台登记事实，不能误读为此次请求失败。
- 页面异常为空；已查看成功页截图。SDK断开后会话只在检查工程运行内存，未执行服务端撤销（第一阶段不开放该路径），由服务端TTL失效。

本地105项客户端测试全部通过，覆盖新固定交付与能力越界拒绝，以及原104项回归。证据位于外层 `offline-evaluation/mini-guest-stage1-client-20261104-01/`：`client-tests.log`、`intake.json`、`sdk-result/network-result.json`、`sdk-result/network-check.png`。CLI原输出仅在本地私有日志，不纳入源码或回传。

## 用户真机下一步

使用本轮独立 `network-probe-sdk` 工程：

`E:\hzz\work\MutualExclusionAllocator\offline-evaluation\mini-guest-stage1-client-20261104-01\network-probe-sdk`

1. 开发者工具切换/导入上述目录，确认项目名 `RacePick-network-probe`。保留“校验合法域名、web-view（业务域名）、TLS版本以及HTTPS证书”校验，不勾选跳过检查。工具中如已显示此检查工程可直接使用，不需要切换离线主页项目。
2. 由用户手动点“预览”，使用有权限的微信扫码。不要点上传、提交审核或发布；本轮没有自动调用预览或生成体验版。
3. 手机打开后点一次“检查微信访客会话与快照”。应显示“网络基础检查通过；OCR与账号尚未验收”，报告state=passed、fixture=false、identityMatched=true，两服阶段均passed且mapRecognitionDeclared=false。不要反复点或换工程重试消耗代码；失败先保留failedStage、httpStatus、errorCode及原提示。
4. 回传手机型号、系统版本、Wi-Fi或移动网络，以及“通过”或检查页截图即可。截图报告不含code/token；不要打开或回传调试器网络请求头、AppSecret、登录code或token。遇到成员/隐私/网络提示保留原文，不绕过校验。

手机基本网络通过后，再按需要补前后台与切换网络检查。此独立工具没有账号或图片入口，不能据此宣布OCR、账号、云车库或完整应用已真机通过。

## 保全与后续

主工程仍保留原fixture设置；既有phone-local及车库未改。只修改本机忽略的platform.profile.local.json以记录本次入口和已确认的三个前置声明，上传/下载声明仍false；这些声明本身不等于验收。完整主页面不在此阶段接入隔离服务，避免顺带启动账号/统计等未开放路由。

OCR后续必须先明确图片隐私/内容安全和共享执行容量，按用户另行授权推进；不改变disabled策略或用private_unmoderated试跑。账号/B–E保持404。没有进行服务器变更、生产操作、正式构包、推送/合并、自动预览、上传、提审或发布。
