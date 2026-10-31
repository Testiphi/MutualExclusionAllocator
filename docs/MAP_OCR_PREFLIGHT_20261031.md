# OCR上线前核验完成，等待单独上线授权

最终状态更新：用户后续明确授权上线，c06cc48b已于当日19:03现场核验激活；正式单元隔离、备份恢复和timer收尾完成，用户最终回复“验收均正常”。本文余下内容为上线前阶段事实与限制，不作为尚未上线或仍待授权的实时结论。当前事实见CLOUD_HANDOFF.md文首及MAP_OCR_DEPLOYMENT_RECEIPT_20261031.json。

后续授权更新：用户已明确“确认授权上线”。下文“仍禁止上线/等待授权”记录准备阶段边界，已由该新授权覆盖；部署仍由用户逐步执行并回传，每次只推进当前步骤。授权不包含维护成绩导入、开启国际写回、合并main、提交推送或发布公告。当前开始上线前最后只读漂移核对；尚未发生正式切换，后续实况见TAKEOVER_20261031.md追加记录。

2026-10-31。本轮服务器操作由用户逐步执行回传；代理未登录服务器。授权仅覆盖上线准备核验与隔离演练，仍禁止上线。没有改生产配置/业务数据库、切换current、安装正式OCR单元、开启国际写回、重复业务迁移或发布维护成绩。

## 交付绑定

- 发布c06cc48b2b55b7bcec58e68b，源码f44e3c219bceb185d055b1ae9e5570ed639e2786，数据9e7d21f656b61a39282389fb62c0e71149d43c1e。
- 完整ZIP159835801字节，SHA256=4a5a318d7ad7d57a8049910593287571068790201888d56b41d9e440ec9e9373；服务器上传及外层31项/内层制品暂存校验通过。
- 准备release：/opt/racepick-ocr-preflight-c06cc48b/releases/c06cc48b2b55b7bcec58e68b，仅供演练。
- 包内国服4487/国际664是批准代码包基线，不是正式活动成绩导入授权。完整维护703、工作簿、参考与候选不进入运行包。

## 正式状态实查

current和实际进程cwd均为/opt/racepick/releases/3d978fd30812fa8f72ba928d；业务active，health正常。主schema6/coverage2/global-score1，其余业务组件schema1。国服活动e209f3e32d0de1dfa7fe6c811a5d5c46，国际活动1252565e65bc887e81e0c677bfeec9ab；国服写回开、国际写回关，两服pending0（开关及pending为前置查询时快照）。国际运行659，未导入本地664。

自动备份服务2026-10-31 04:16:03–04:16:04 CST success/0，对应/var/lib/racepick/backups/scores-20261030T201604446276Z.zip，2026624字节，SHA256=942f4672ea5af11a2786207445288069c3c720184d308b89d33769b26f3adafd；33项逐项校验通过，双服版本及usage1/coverage2/global-score1一致。本轮未对该新备份执行独立恢复演练。timer enabled/active(waiting)，前置查询NEXT2026-11-01 04:19:41 CST，仅未来计划，不记为已执行；后续各步仅复核active。

主机x86_64/Python3.12.3/2CPU/总内存1740MiB，初始available1237MiB、系统盘可用29G；这是当时采样，后续空闲内存有波动，不是容量保证。

## 现场隔离验证

所有独立任务使用隐藏正式业务路径、私有网络、非root UID999（安装任务除外）、只读release、1CPU/768MiB/禁swap。未对公网开放测试端口，未占用宿主生产端口。

- 37wheel离线安装、pip check、临时库原生迁移/锁/恢复自检通过。合成图3.088秒；非root合成图2.78秒，进程RSS峰值323968KiB。
- Supervisor就绪/正常停止及worker回收通过，首次空队列0任务。
- 私有队列9图地图/顺序9/9正确，中位4.693秒/最大6.047秒，worker VmHWM峰值452636KiB。
- 受控worker崩溃2.116秒恢复；执行中暂停并取消后49.169秒完成硬截止及重载，取消图片移除、迟到结果拦截、全部测试worker退出。
- 独立Nginx/API及临时活动快照：9图地图/顺序9/9正确，中位4.482227秒/样本最大5.498042秒，worker VmHWM峰值461092KiB（约450.3MiB），观测最大HTTP275.840ms。有效4MiB上传通过，>8MiB拒绝，其他路径3m；8排队任务完成、第9拒绝，测试health可响应。临时双服版本保持、users0/国际写回关、主页“新功能”保持。

systemd汇总Memory peak约1–2M不用于模型容量判断；上述资源依据进程VmHWM/RSS。系统swap采样66–67MiB不等于测试任务使用swap，也不用于宣称全机无swap。

## 已审阅候选配置

目录/root/racepick-ocr-preflight-c06cc48b/config-review，包含before/candidate、diff及REVIEW_RESULT.json。正式配置原哈希保持：

| 文件 | SHA256 |
| --- | --- |
| /etc/nginx/conf.d/racepick-rate.conf | 9f7c5e7ee70765b9a89a7fdaf6901086fe230e2034cca48f5ba056c62feab428 |
| /etc/nginx/sites-available/racepick | d14f300947a4a9d35eab953e2b587f609763c4dab9783eed614aab280e131dee |
| rate候选 | 5733a21ba635e1da1398e6c752d65227cb1fb1855dad786f4a5c4df9b9a25bfc |
| site候选 | d86906e947e4c459f4a8c5f36f8a9806b58be7110980a9f3f49022117bd5476a |
| racepick-map-ocr.service候选 | 93af8577e3d652c1a42d89e6202a430875c4c9191622219aa952114edf2f321c |
| accounts-ocr.candidate.conf | 7e40db60ca1d721819f78945f866a063a71eca0fd04b763a694e17ab33f628ed |
| ocr-config.candidate.json | 2629128c0f3d3aa2b65aef35e0a3ebd5ffccd86ccc7d41d6934359ff2d08fdb4 |

候选仅新增OCR独立6r/s burst12、精确上传路由8m及环境/单元草稿；原业务5r/s burst30、统计2r/s burst10、默认3m、TLS/Certbot/HTTP跳转/8080/可信代理头保留。单元候选High640M/Max768M/禁swap/CPU100%，不同于包模板High768M/Max1G；不得上线时误用原内存模板。

候选在unshare私有挂载命名空间中以真实完整Nginx配置执行nginx -t通过，退出后宿主哈希不变；候选OCR单元systemd-analyze语法通过，未安装或运行。两条cloudmonitor.service警告来自已有云监控单元，本轮不修改。

## 待授权后的步骤及边界

目前停在授权点，不给出或执行生产写操作。获得单独上线授权后，先重新核对现场current/活动双服版本/pending/开关/配置哈希；按最新流程保全新增、成套备份及独立恢复演练，再准备正式release、OCR私有队列和配置，验证正式单元真实挂载/权限/资源与进程回收。按授权成套应用Nginx与服务配置、激活，再核对实际进程cwd/健康/原成绩及开关、公网TLS/真实登录/手机微信/回退、真实备份服务与timer收尾。不能将隔离临时systemd任务视为正式模板运行验收。

当前版本不需要业务schema迁移。不重跑旧迁移，不自动开启国际写回，不用代码包覆盖score-state，不夹带维护成绩。持续并发容量、正式公网及手机尚无本轮验证；既有成功样本不证明未知布局、低清或英文截图可用。

服务器证据保存在/var/lib/racepick-ocr-preflight-c06cc48b下：real9-result/console、fault-result/console、http-console.log、http-results/native-integration-receipt.json及测试库/日志/样本。原包、旧版本、备份、用户文件及所有测试资料保留。不发公告、不清理、不创建监控；本轮文档未提交推送。完整逐步事实见TAKEOVER_20261031.md。
