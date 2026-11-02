# 微信开发者工具可用性核查

结论：适合作为本项目原生 JS/WXML/WXSS 的本地开发与模拟验收工具；当前机器常见路径、卸载登记、运行进程未发现该工具，尚未实际导入/编译。用户提供的“1.0版本”介绍不能作为当前工具版本依据；本轮未下载安装、登录、预览分发或上传代码。

2026-11-02 官方资料只读核对：网页工具直接打开失败后，从相同官方 URL 读取正文，HTML/正文及 SHA 证据保存在外层 `offline-evaluation/miniprogram-v1-20261102-01/`。`stable.html` 本轮返回404，保留失败记录；[下载入口](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 可以访问，但本轮未从其动态内容核实最新稳定版本号，不猜测版本。

- [CLI文档](https://developers.weixin.qq.com/miniprogram/dev/devtools/cli.html)：本机工具提供 CLI/HTTP 调用；Windows 入口为安装目录 `cli.bat`，需要设置中开启服务端口。CLI同时具备打开、自动化、预览、上传等命令；本轮仅准备本地导入，不执行分发/上传。
- [自动化快速开始](https://developers.weixin.qq.com/miniprogram/dev/devtools/auto/quick-start.html)：官方 SDK `miniprogram-automator` 可启动并控制工具、页面和组件，需要本机工具及 CLI/HTTP 调用开关。适合后续重复验证五槽选择、车库、确认流程；本轮未安装 SDK 或运行自动化。
- [wx.chooseMedia](https://developers.weixin.qq.com/miniprogram/dev/api/media/video/wx.chooseMedia.html)：支持仅 image、album、original，本项目限制单张；这只限制选择来源，不证明文件一定是游戏截图，也不是拍屏检测。
- [wx.request](https://developers.weixin.qq.com/miniprogram/dev/api/network/request/wx.request.html) 和 [wx.uploadFile](https://developers.weixin.qq.com/miniprogram/dev/api/network/upload/wx.uploadFile.html)：分别处理 request 和 multipart；本轮 transport 默认关闭、保留原始响应字节，不复用网页 Cookie/CSRF 协议。真实域名/TLS与访客会话待配置验证。
- [安全随机数](https://developers.weixin.qq.com/miniprogram/dev/api/device/crypto/wx.getRandomValues.html)：从2.15.0支持，异步返回 ArrayBuffer；用于请求ID，无 Math.random 降级。真实基础库未实测。
- [隐私指南](https://developers.weixin.qq.com/miniprogram/dev/framework/user-privacy/PrivacyAuthorize.html)：接口权限与后台声明相关，平台有隐私弹窗和拒绝状态。本轮未配置后台；相册失败可继续手选，不能把模拟器通过写成隐私配置完成。

当前可以完成：源码准备、Node 单测、页面事件夹具、mock 交互、共享源码字节一致性、原始字节哈希。安装后可以继续：记录工具/基础库/渲染器版本，导入 `miniapp`，核对 WXML/WXSS 编译、控制台、不同宽度及长列表。`touristappid` 是本地占位，不是实际项目身份；可用能力须现场验证，相关能力受限时再提供真实 AppID/开发者权限。

模拟器不能替代的验收：iOS/Android 相册/隐私授权、临时路径生命周期、真机存储不足、键盘/长列表、前后台和弱网、CPU耗时/计算取消、原生会话与服务端微信验证、真实同worker OCR、合法域名/TLS、体验成员权限和平台审核。审核仍进行中，不因本地工具可用推定已通过。
