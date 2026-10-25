# 云端部署运维交接提示词

```text
请接手 RacePick 本轮部署上线。功能开发与发布包已准备完成；本开发对话未操作生产。请先读交付包内 README.md、RELEASE.json、DATA_SCOPE.json、PACKAGE_VERIFICATION.json，按 UNREAD_USAGE_DEPLOYMENT.md 执行现有站点升级。历史文档中的首次初始化流程不适用于本次升级。

交付包：RacePick-UnreadUsage601-20261025-171d872a-delivery.zip
本地路径：E:\hzz\work\MutualExclusionAllocator\repo\.production-build\RacePick-UnreadUsage601-20261025-171d872a-delivery.zip
完整归档SHA256：05288fd2552c83d4337ac43d1dc22fce51c419a6f8586a648ac6f163faf4522b
发布ID：171d872a414dea28be25eaa1
源码提交：7651da519be92b7ae6ea184d2c30a985607c30f5
冻结数据提交：cbe9ea3dd3d0c130bef8dd15f890d618167e1539
内层racepick-accounts-release.zip SHA256：3f78707b58a623b1f285072bbd1c0ce4e6932ba0ae34faf1d4665bc087f5e649
目标：Ubuntu24.04 x86_64 / CPython3.12，19个锁定离线wheel。

发布范围：
1. 已本地验收的未读提醒和使用统计。管理员已读按账号独立；投稿人收到审核结果与反馈回复提醒。首页/折叠菜单右上角标记，反馈列表仅逐项未读；待处理数与未读分开。使用统计仅超级管理员可见，账号管理支持最近活动、活跃筛选和每日明细，已移除操作记录按钮但保留底层记录。
2. 国际服仅五区满星理论601条、44车、21OC、39特殊跑法，版本1bb0253ce327210b6c02fb2c2ea49682ee628086fec6c7bc987326121b4a6efc。完整维护640键、四区/高手、36条独立参考和工作簿均不进入运行。
3. 包内国服4423键是冻结基线。生产读取独立score-state，必须保留现有正式成绩及云端新增，严禁用代码包JSON覆盖。若生产需同步国服数据/五车规则，先只读比较并列明差异、来源和现有发布链，交我协调数据维护确认；本次不要自行整表导入、补成绩或修改规则。不能把包内数据条数当作正式库已更新的证明。

本地证据：JS97通过；Python239执行、238通过、1项Linux专用跳过；构包工具10通过。包内96文件/依赖逐项校验、7份数据/工作簿来源SHA、8份本地维护源核验、五份运行JSON精确字节、19个Linux目标wheel锁定解析均通过。独立暂存包HTTP与临时库迁移/幂等/成套备份恢复通过；Windows服务锁为模拟，不能替代Linux原生验证。生产验收待做。

执行方式：先给我当前服务器只读核验命令，我执行回传，一步一步来。不要一次性发整套有写操作的脚本。先核对实际current、MainPID/cwd、health/schema、国服score版本、国际版本、未完成批次、备份timer及最近真实备份结果、Python/架构/磁盘、Nginx实际文件及日志；现场状态和历史不符先解释。可使用包内01-readonly-preflight.sh作为只读预检起点，仍需补齐正式版本/批次及实际配置检查，不输出凭据。

后续顺序：
- 我上传后先核对完整归档SHA，解包执行sha256sum -c SHA256SUMS.txt；使用本包新deploy_production.py仅暂存，不激活。新发布目录执行离线install-runtime.sh，必须通过Linux原生临时库自检；失败保留现场。
- 新版本工具创建在线成套备份、校验及独立恢复演练；确认维护窗口，暂停备份timer并停服，核实停止，再做最终成套备份/校验/演练。
- 从新发布目录、用其.venv和现有正式config执行新组件preflight，固定现场国服score版本，依次notification_production migrate、usage_production initialize。不得使用发布ID/国际版本替代国服版本，不重跑旧初始化/旧迁移。未读历史作为已读基线，通知初始为空，统计初始为空；不导入演示库。核对旧业务行和score-state保持、统计库服务属主/0600及可写；再做包含新组件的成套备份/恢复演练。
- 应用包外必须成套处理Nginx：HTTP map/zone和实际HTTPS站点location同时调整，统计POST独立racepick_usage_events桶2r/s burst10，保留业务桶5r/s burst30与启动GET豁免。先备份实际配置，保留证书/端口/其他站点/自定义规则，nginx -t通过才reload。不要整份盲覆盖。
- 用新部署工具通过兼容检查后激活、启动服务，核对current/PID实际cwd/health，主schema6、新notification_schema1/usage_schema1、旧组件和正式成绩版本保持，国际601/44/21OC/39特殊版本吻合。原双服计算、登录、车库/草稿、投稿/反馈及备份链回归；管理员独立已读、投稿/反馈回复提醒、统计权限及账号活动过滤由实际验收确认。桌面和手机微信留给我验收，不伪造生产投稿/成绩或刷流量做压力测试。
- 恢复原备份timer，核对一次真实成功的新组件成套备份及恢复演练和下一次计划；未发生的计划不能记为成功。记录实际部署、配置SHA、备份路径/SHA、版本/数量和验收证据。

停止/回退：schema或版本漂移、未完成批次、备份/演练/权限/Nginx/进程或关键验收异常即停，保留现场。启用通知/统计后，旧66b9d32c不具备新schema能力，不能只切旧链接，不用旧工具绕过兼容门禁。优先兼容版本修复；数据恢复必须另行明确授权并成套演练，先保留升级后新增，不删除新表/usage.sqlite3、不单库恢复、不用包内JSON覆盖score-state。

保护账号、成绩、投稿、反馈、车库、测试数据、工作簿、备份、旧包与旧版本；不发公告、不自动清理、不创建监控。缺少包或授权/证据时先说明具体缺项，不编造路径、结果或完成状态。
```
