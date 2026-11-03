# 第一轮手机失败与诊断版2

2026-11-04，接手a140602。用户电脑检查通过，但手机扫码失败；原截图显示failedStage=wechat_session、httpStatus=null、NETWORK_OR_PROTOCOL_ERROR，累计login=1 / session=2 / cn=0 / global=0。两次会话请求不能当作两次微信登录，也不能认定服务端从未收到请求；未进入快照检查。手机真机验收未通过，前一轮开发者工具成功证据仍保留。

## 本地发现和修改

响应解析曾使用 `data instanceof ArrayBuffer`。用Node vm创建另一JS realm的真实ArrayBuffer可稳定复现“响应格式无效”，而相同本地ArrayBuffer可解析。该缺陷可能解释工具/手机差异，但截图不含原生错误，因此**尚未证明这就是本次手机失败原因**，不能提前写成修复后真机通过。

现在使用ArrayBuffer内建byteLength getter作真实类型检查，再创建本地Uint8Array视图解码。支持跨realm原生buffer与带offset的typed view；拒绝普通对象/伪造类型标签，继续限制大小与严格UTF-8，不改变快照原text/SHA/bytes验证。请求显式dataType=other/responseType=arraybuffer，避免自动JSON转换与二进制解析混用。

网络失败标记WX_REQUEST_FAILED，仅报告domain_rejected、tls_or_certificate、dns、timeout、cancelled、connection或unknown分类及数值原生错误码。响应解析失败有独立错误码，并保留已收到的HTTP状态与有限数据类型/字节数。探针只转录白名单诊断字段，不回显errMsg、URL、正文、凭据或异常栈。未知失败仍保留原code/request_key在内存，显式重试恢复原交换，不静默重建身份。

报告增加probeRevision=2，页面明确显示“诊断版 2”，以防手机仍打开旧预览。没有关闭域名/证书校验、修改服务端、开放图片或账号，也没有写车库。

## 验证与证据

108项客户端测试通过，新增跨realm响应/offset/假类型/非法UTF-8、网络错误分类及敏感信息排除、HTTP200解析失败与网络失败区分、未知结果同code/key恢复。诊断版真实开发者工具SDK再次完成wx.login一次、session一次、双服快照各一次，固定版本与五文件SHA/bytes保持匹配。未mock微信API；没有调用上传、账号、DELETE session、预览或提审。

外层证据目录 `offline-evaluation/mini-guest-phone-diagnostic-20261104-01/` 保存测试日志、SDK报告/截图、生成清单及用户电脑截图副本。手机附图已在本轮消息中读取，但所给微信临时文件路径在复制时已不存在，未保存其本地副本；上述手机字段来自消息内附图，不声称原文件已落盘保全。手机复测尚待用户执行；不能用本地模拟跨realm或再次SDK成功代替手机结果。

## 手机只需复测一次

开发者工具已打开/可导入的新目录：

`E:\hzz\work\MutualExclusionAllocator\offline-evaluation\mini-guest-phone-diagnostic-20261104-01\network-probe`

用户手动点击“预览”生成新二维码，再扫码；确认页面出现“诊断版 2”，点一次检查。若通过回传结果、机型/系统即可；若失败回传报告的failedStage、httpStatus、errorCode、diagnostic和counts或截图。不要回传网络请求头、code或token。暂不改变DNS/证书/后台配置、不清缓存、不连续重复点按钮。

旧独立检查工程、主工程、离线已验收项目及已有车库均保留。OCR、账号/B–E保持关闭；用户未授权后续开启、生产变更、上传/提审/发布。
