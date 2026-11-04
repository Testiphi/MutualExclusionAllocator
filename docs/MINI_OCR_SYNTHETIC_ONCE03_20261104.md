# 域名同步后新授权单次调用：上传202、任务返回、五槽未匹配

2026-11-04，接手aba4abc。用户说明前次未配置uploadFile域名，现在要求先确认工具同步，再仅用原SHA合成图新执行一次，独立预约、失败不重试。未扩大到真实游戏截图、手机实图、服务器/微信后台修改、账号/B–E或小程序上传提审发布。

## 工具同步确认先于上传

普通UI和CLI没有直接提供有效的当前域名列表。安装包源码显示工具以当前项目runtimeAttr.network生成模拟器network配置；通过官方miniprogram-automator的evaluate，只读获取当前模拟器 `__devtoolsConfig.network` 中目标origin的request/upload成员关系与urlCheck，不输出用户资料、AppID、其他域名、token或完整配置。它是工具运行配置的诊断字段，不当作服务端鉴权来源，字段缺失/不符时驱动停止。

当前运行模拟器实测：urlCheck=true，requestConfigured=true，uploadConfigured=true，目标均为https://mini-test.racepick.cn。独立预检时间13:31:54.862Z；单次驱动在核对工程标识后再次复验，时间13:32:25.343Z，确认后才创建预约和执行wx.uploadFile。同步事实来自当前工程，不采用旧已保存项目缓存来推断；后者可能仍为空，不能代替运行配置。

本轮没有为继续而关闭域名/TLS/证书校验，没有改微信后台或服务器，没有清缓存/重设账号。前面UI/元数据只读检查没有调用uploadFile，也没有生成本次执行预约。

## 授权与调用结果

- 新授权IDmini-ocr-synthetic-20261104-03，工程标识90f6a5e3f838bb2dfbc8。独立目录 `offline-evaluation/mini-ocr-synthetic-once-20261104-03/`，新建独占预约，原01和02预约/原始报告/回执SHA逐项保持。
- 只使用原87085字节合成PNG，SHA256 `82dafe81e5f48f50fe4ab42eec79499627be61efcfaea3631964bc691a30c54f`。native_api发送前重算文件SHA，未换图/改图。相册返回用受控fixture指向原样图，wx.login/request/uploadFile均实际调用，不作为真实相册或真机验收。
- 真实访客与两服固定原字节快照、CN83图目录及worker ready通过，image_policy对应目录content_safety=required_approval。上传前再次核目录，未调用账号/管理/统计接口。
- **wx.uploadFile一次，HTTP 202**；随后原任务查询5次，返回合法五槽结果，客户端phase=finished / state=pending_confirmation。没有上传重试、任务恢复、取消或其他图片调用。
- 五个候选槽位均null（未匹配），correctFiveMaps=false，没有确认或应用地图。不能写成“五图正确识别通过”；合成布局也不能代表真实游戏截图准确率。未单独定位未匹配原因，不靠更多付费调用猜测。
- 按已固定服务端契约，任务获准进入OCR并返回结果意味着其通过部署的安全准入门禁；客户端没有供应商原始审核回执或账单，不能据此证明阿里云实际计费条数或供应商内部留存。新POST仅一次，允许的审核费用范围未扩大。
- 驱动记录realOcrVerified=true的含义仅是取得合法OCR任务返回，不表示五图匹配正确；明确以correctFiveMaps=false和pending五空槽限定结论。报告顶层httpStatus=null表示没有失败HTTP状态，本次上传状态在lastUpload.httpStatus=202，不应误读为上传无响应。
- 最终运行内存和生成配置均锁回maxUploads=0/uploadDomainDeclared=false，预约保留。旧任务未恢复，本机车库/已验收工程未改。没有手机实图、上传体验版/提审/发布或生产操作。

## 精确时间（客户端时钟）

| 事件 | 北京时间 UTC+08:00 | UTC |
|---|---|---|
| 实际wx.uploadFile开始 | 2026-11-04 21:32:27.177 | 2026-11-04T13:32:27.177Z |
| 实际上传202回调 | 2026-11-04 21:32:27.742 | 2026-11-04T13:32:27.742Z |
| 客户端收集最终五槽结果 | 2026-11-04 21:32:35.522 | 2026-11-04T13:32:35.522Z |

上传回调间隔约565毫秒，开始至结果收集约8.345秒；仅本样本观测，不是审核/CPU各自耗时、服务容量或SLA。时间来自调用包装器与驱动时钟，不宣称已校准服务器时钟。

## 证据与后续

domain-sync.json为上传前只读同步证据；attempt/once-result.json为本次脱敏原始报告；authorization-attempt.reserved.json为独立执行预约；另有截图、permit、生成清单和提交回执。CLI私有日志仅本地保留，不入Git。主代码本轮仅给单次驱动加运行域名确认前置，node语法检查及本次实际门禁通过；未再修改算法或重跑上一轮122项测试冒称新全量。

至此完成本次新授权。实际游戏截图识别与手机测试仍待另行确定样图/费用/设备范围，不能复用本次预约或自动继续发图。
