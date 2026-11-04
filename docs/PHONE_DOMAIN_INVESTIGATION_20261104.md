# 手机域名校验继续排查：零上传报告及原地址构造

更新：用户已原样回传后台uploadFile合法域名为https://mini-test.racepick.cn，与原客户端目标一致且无端口。保存时间未提供；不再把条目拼写/端口差异当首要待查项。当前转查手机配置生效上下文，尚未确认根因，未恢复额度或上传。

2026-11-04，接手1d267ee。用户回交零上传诊断报告并明确要求继续排查、不恢复额度、不再传图。本轮只记录事实、读取官方文档并作原客户端地址构造本地干跑；没有RacePick API调用、真实wx.uploadFile、图片外发、后台/服务器改动或预约重置。

## 最新手机证据确认的范围

- buildId537c227edbcb1497bd01与零上传diagnostic工程一致，phoneUiRevision=2，diagnosisOnly=true。
- 手机getAccountInfoSync返回的AppID与本地生成配置相等（报告只存布尔值true），platform=ios、iOS27.0.1、微信8.0.79、SDK3.17.6。排除的是“手机运行标识与本地不一致”，不是替用户证明后台所查看对象必定相同。
- 原预约仍spent、maxUploads=0、canResume=false，无taskId；所有session/snapshot/catalog/upload/query/recovery/cancel计数0，没有调用任何业务网络。这是诊断页预期结果，不是手机OCR成功，也不提供手机原生上传域名列表。
- 结合前次手机domain_rejected/errno600002、22:46:16.922–.925+08:00、未收到HTTP状态的记录，故障仍定位在手机上传域名门禁，尚无服务端OCR或审核失败证据。
- 用户已说明扫码的是新生成二维码；不把“肯定扫了旧码”作为结论。当前证据也不足以认定iOS/微信bug、配置传播延迟或手机缓存为根因。

最新回传原样字段保存在外层 `offline-evaluation/mini-phone-domain-investigation-20261104-01/user-zero-upload-report.json`，原失败报告、设备回传、生成文件及旧回执均保护并核SHA。

## 原手机构建的实际地址构造干跑

直接加载原phone-ocr工程（buildId501ec160cfa4c9d46b57）的generated/config及adapters/native_api，不以当前已修源码替代。使用纯本地wx mock和3字节非图片占位buffer，只捕获参数；没有调用真实wx.login/request/uploadFile，没有读取attack06或向外发送任何图片。

实际构造结果为：

- HTTPS origin/hostname：`https://mini-test.racepick.cn` / `mini-test.racepick.cn`。
- 无显式端口，尤其未拼入`:443`。
- path：`/api/mini/v1/map-recognition/jobs`。
- query字段仅server、catalog_version、request_key，服别CN，目录沿固定交付。

这排除了该构建地址拼接时使用了其他域名/协议或显式端口的代码差异；它是原源码的本地执行，不冒充失败手机的实际抓包，也不能证明代理/平台后续处理。已在original-client-url-dryrun.json明确kind与realNetworkCalls/realUploadCalls=0，未记录完整query值/请求头/凭据。

## 官方规则与配置核对

官方[网络文档](https://developers.weixin.qq.com/miniprogram/dev/framework/ability/network.html)本轮实际HTTP200读取：request/uploadFile等分别受服务器域名配置约束；配置有无端口要与URL一致，无端口请求不能拿显式443配置随意替代。官方指出开发调试可跳过校验，但不应以此判断各平台正常。本工程保持校验，不采用关调试/清数据/关闭HTTPS等绕过方法。实际正文保存在official-network-body.txt，与review.json一同保留。

官方文档没有为本案例提供可据此断言的“等X分钟必定生效”时间，不给未经验证的固定等待承诺，也不把搜索到的第三方清缓存建议当作解决方案。

当前最有区分度且尚缺的是：**同一个小程序后台uploadFile合法域名行的原始值，以及最近保存成功的大致时间**。已请用户只读回传该行域名与时间，不需AppID/密钥，不要求改配置。应核对完整https子域、是否显式端口、是否确为uploadFile而非request/业务域名。电脑工具此前有效列表包含目标origin并不自动证明手机同一时刻已应用该列表。

若后台行存在差异，可据实际差异再协调修正；若精确匹配，才进一步调查预览环境/版本及微信侧域名列表生效差异。当前没有结论性证据需要改服务器证书、API路由、OCR算法或安全策略；也不新增上传试探域名校验。

本轮代码运行逻辑未改，仅新增排查记录；只跑原构建本地URL干跑，不重复旧131项或冒称新全量通过。原额度保持已使用，后续任何实图仍需新范围授权。
