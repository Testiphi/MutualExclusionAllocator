# 云端部署交接提示词

```text
请接手RacePick成绩覆盖表新版本的云端部署上线。先给我当前服务器只读核验命令，我执行回传，一步一步来，不要一次性给整套写操作脚本。开发对话只完成实现、构包和Git推送，未操作生产。

交付包：RacePick-Coverage661-20261029-fe8a9aff-delivery.zip
本地：E:\hzz\work\MutualExclusionAllocator\repo\.production-build\RacePick-Coverage661-20261029-fe8a9aff-delivery.zip
完整归档SHA256：ca73947e14bbe8bc3671531c5b4f5398f4531da71878c0db34dd53d9ec347953
发布ID：fe8a9aff0cf6871d5d7f0212
源码提交：a8ad5c36a113033375c84c2ef683fb1f312907e7
数据提交：d06cd7d54838230976342c19c21638b90a5632ac
内层包SHA256：821485c5f05d778f15ca39719c49bff1238dbff122f6b6884089360a5dd35e60
目标：Ubuntu24.04 x86_64 / CPython3.12，19个锁定离线wheel。

先读包内README、RELEASE.json、DATA_SCOPE.json、PACKAGE_VERIFICATION.json，以COVERAGE_DEPLOYMENT.md作为已有站点升级顺序。其他旧文档的首次初始化和旧组件迁移不能照抄。

范围：主页风格统一且RacePick标志仅主页、审核意见单份输入、富士山提示按实际数据、新国际车辆和urs旧车库兼容；新增真实Excel式覆盖表、每图每区1条非OC普通满星理论公开参考、国服空格预填投稿和真实贡献解锁。国际服仅浏览和公开参考，不开放投稿或国服积分解锁。真实版已本地自动化与假账号浏览器验证，用户原型验收通过；真实版用户逐项及生产验收仍待进行。

数据：包内国服4458键仅冻结基线，生产保持现有独立score-state及云端新增，禁止用代码JSON覆盖成绩或车辆规则。若需同步国服数据，先列实际差异并交我协调数据维护，不能临时整表导入。国际静态运行661条、46车、44图全覆盖、21OC/48特殊，版本0ae6a89d46c8e7707ee3387c7879b59bea69c911c54e07866c38953c8cb9f593。完整维护700键、国际四区/高手、36参考和工作簿不入运行。

先只读核对实际current、MainPID/cwd、health/schema、正式国服成绩版本、国际版本、pending_batches、磁盘、系统/架构/Python、实际Nginx路径和限流、备份timer和最近真实备份结果。旧171d872a只是历史记录；不照用旧PID/成绩版本，不输出凭据。包内01-readonly-preflight.sh可作为起点，仍需补齐实际版本和未完成批次等核验。

我上传后：
1. 核对完整归档SHA，解包后sha256sum -c SHA256SUMS.txt；用本包新部署工具仅暂存、不激活。进入新发布目录，离线install-runtime.sh必须通过Linux原生临时库自检。Windows模拟锁/依赖目标解析不能替代这一步。
2. 从新版本工具创建在线成套备份、verify-backup及独立restore-drill。确认维护窗口，暂停备份timer、确认备份服务结束、停应用并核实MainPID0；再做停服最终成套备份/校验/演练。
3. 从新版本目录使用其.venv及现有正式config，执行backend.coverage_production preflight；核对旧组件/贡献schema1、正式score版本和pending0。固定现场实际国服score版本，执行coverage_production migrate --expected-version <该现场版本>，不能用发布ID、Git提交或国际版本代替。优先服务用户racepick与既有权限链，不重新configure/init/bootstrap，不重跑旧迁移。
4. 新选择/事件表初始为空，coverage_schema1，existing_rows_preserved=true，旧业务行、积分和score-state保持；不导入演示库或假权限。迁移后再做包含新组件声明的成套备份/恢复演练。
5. 本轮没有新增Nginx/系统服务/环境变量要求，保留既有业务与统计双桶、证书、端口和其他站点。核验现场实际路由及静态资源来源，不擅自放宽限流或整份覆盖配置。依赖/备份/演练/兼容未通过，不切current。
6. 用新部署工具兼容检查后激活并启动，核对current、PID实际cwd、health主schema6和coverage_schema1、原组件/score版本保持；国际三件套版本数量匹配。回归原双服计算、登录、车库草稿、投稿/反馈、样式/单份审核意见和新表格。验证游客只见公开参考、空格登录回跳与预填、本人待审不占格、账号隔离、真实账本权益和国际不能误投国服。普通账号若未达门槛，等级变化留待真实事件验证，不能写假积分/假生产投稿来凑验收。桌面及手机微信由我实际确认。
7. 恢复原备份timer，核对一次真实新组件成套备份及恢复演练和下一次计划，记录实际版本、配置/备份路径与SHA、数量和验收；未发生的计划不能记为成功。

异常即停并保留现场。新三表启用后不能只切旧应用链接，不用旧部署工具绕过兼容检查。优先兼容版本修复；整套数据恢复须先保存升级后新增、演练并另获明确授权，不删除新表、不单库恢复、不用包内JSON覆盖score-state。

保护账号、成绩、车库、投稿、反馈、凭据、测试数据、工作簿、备份、旧包、旧版和演练。不要发布公告、自动清理、创建监控或向其他对话派任务。缺少证据时说明具体缺项，不编造完成状态。
```
