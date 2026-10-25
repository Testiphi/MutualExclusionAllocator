# 国际服选车部署与验收（2026-10-24）

## 2026-10-25 当前上线状态：171d872a，提醒真实事件待验证

本轮已由用户逐步执行并回传完成：新包暂存、Linux原生运行时（用户确认）、正式通知schema1迁移、统计schema1初始化、完整备份/恢复演练、Nginx双桶配置和激活。11:05:50 CST应用171d872a414dea28be25eaa1启动，current与PID156079实际cwd一致；最终health主schema6、notification/usage及原组件均schema1、开关正常。正式国服成绩保持4bdaa0734cbfa4b178d1cbb1a081a8c7，未用应用包冻结国服JSON覆盖score-state。国际601条/44车/21OC/39特殊，版本1bb0253ce327210b6c02fb2c2ea49682ee628086fec6c7bc987326121b4a6efc，640维护/四区/高手/36参考及工作簿未混入运行。

Nginx11:05:06 reload成功：统计POST独立2r/s burst10，业务5r/s burst30及启动GET豁免保留；11:08:00新版成套备份和演练通过后恢复timer，enabled/active(waiting)，NEXT2026-10-26 04:15:51 CST，未来执行未核验。桌面与手机微信已验收双服计算、登录、车库草稿、统计权限及活动筛选；独立已读及投稿人审核/反馈回复提醒因无真实新事件待验证。完整版本、配置SHA、恢复点和证据边界见[CLOUD_HANDOFF.md](CLOUD_HANDOFF.md)文首。

下方未部署和旧版本为历史阶段，不重复初始化、旧迁移或切回不兼容66b9d32c。升级后回退须用兼容工具并保留全部新增；数据整套恢复需另行授权。用户已授权仅提交推送本轮部署/交接文档，远端核验后暂停；独立已读及投稿人提醒继续待真实事件验证，不改数据、不发公告、不清理或创建监控。

## 2026-10-24 当前：快速切服修复已上线并验收，保持599条

用户逐步执行命令并回传：应用`66b9d32c1857d2b3c2cc533f`（源码/包内数据`4ff5f6f159bf579c3dd058f78d7bc7f6659967ce`）于18:18:15 CST启动，current与PID150824实际cwd一致、active/running。两份Nginx配置已备份并成套改为`racepick_api_requests`，nginx -t通过、18:17:09 reload成功；原证书/转发/80和8080监听保留。生产旧限流拦截启动资源的429已由实际配置及日志确认。

health正常，国服成绩版本`42d62fde9b81197ac0558087a9a25f97`不变。国际服仍599条，版本`f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e`，49车、21OC/38SC；没有迁移或初始化正式库、覆盖score-state、导入测试数据。三次成套备份及独立恢复演练完整回传通过，39用户/21车库/3投稿，active_database_replaced=false，内部哈希一致。18:18:43 timer恢复enabled/active(waiting)，NEXT2026-10-25 04:18:33 CST，未来执行尚未核验。

公网78次启动资源GET全部200，无429，api.js与新版字节相同；用户确认桌面和手机微信连续切服、计算、OC/特殊跑法和分服车库/草稿均通过。完整备份路径、SHA及证据边界见[CLOUD_HANDOFF.md](CLOUD_HANDOFF.md)最新节。本地601条/616维护键、工作簿和公告草稿继续保留，不发布；仅提交推送部署文档后暂停，不清理、不监控。下方未部署/待执行及旧版本描述均为历史阶段，不应续跑迁移或发布步骤。

## 2026-10-24 最新交接：快速切换修复已推送，599条完整包就绪（尚未部署）

修复源码提交`4ff5f6f159bf579c3dd058f78d7bc7f6659967ce`已推送origin/main，并用git ls-remote核对一致。随后仅追加发布完成交接文档提交，不重建或改变已绑定源码的交付包。原5份本地JSON/工作簿修改和3个未跟踪用户文件未加入提交；601条数据继续留本地，国服Excel保存改动未自动回代，公告未发布。

应用发布ID：`66b9d32c1857d2b3c2cc533f`，85个manifest文件、19个锁定离线wheel，代码/数据provenance均绑定本次源码提交。使用干净独立检出与build_production.py构建；包内国服两份JSON、国际服三份JSON逐字节等于已上线0ee524e3包，国际服数据版本仍f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e，仅五区满星理论599（578非OC+21OC、561普通+38特殊），49车44图42有值，其他区档不混入。没有工作簿、601数据、维护台账、账号/成绩库、凭据或测试材料。

完整上传包：`repo/.production-build/RacePick-SwitchFix599-20261024-66b9d32c-delivery.zip`，10949010字节；SHA256：`f35d888ef61a5a9591a99e1bccecc433946a166136b36322e9963605ca15171a`，同目录有.sha256.txt。展开交付为`repo/.production-build/delivery-20261024-switchfix599`，17文件，SHA256SUMS.txt覆盖其余16文件；外层ZIP逐项回读相等。应用包SHA256为c224289955714d6f54e1b5fdb3ba5d3c7484c3e8b34f3e79157253d510b09984。RELEASE.json和PACKAGE_VERIFICATION.json为独立校验入口。

已完成：干净构建前端86全通过、Python214执行/213通过/1个Linux专用跳过；源码逐字节回比、599条无重复和五区满星隔离、19wheel锁定哈希与Linux CPython3.12离线解析、交付自带部署工具独立暂存未激活、Windows临时数据库HTTP/备份恢复/组件冒烟。Nginx本地旧/新模板78请求对照45次429降为0，登录和管理员等接口仍限流；不是生产Linux原生验收。两份当前/上一完整旧归档SHA和11份本地数据/工作簿哈希保持。

本轮没有访问生产、执行nginx -T、修改/etc/nginx、迁移/初始化正式库、切换current、重启服务或改变备份调度。线上版本仅沿用此前0ee524e31734b44fb7771b79/599条用户验收记录，不视为已实时核验。

后续部署第一步必须用户执行只读核验Nginx生效配置和429日志，同时核对current/进程/health/备份timer。交付附01-readonly-preflight.sh（bash -n通过）；标准日志无结果不等于没有429，按nginx -T中的实际日志路径继续核实。回传审核后才逐步推进上传校验、暂存/独立运行时、成套备份演练及版本/配置切换，禁止一口气执行历史部署脚本。修复须成套更新Nginx map/新zone和站点limit_req，移除旧全站限流，先nginx -t再审核reload；应用切换不会自动改Nginx。证书/其他站点保持，旧版本、备份、演练目录保留，不重复迁移，不用代码包覆盖服务器score-state。

本地完整回执：本地归档/server-switch-fix-20261024/release-receipt.json及application-verification.json。本轮到“可校验包就绪、等待用户开始只读核验”为止，不自动执行部署。

## 2026-10-24 最新：599条国际服更新已上线，桌面与手机微信验收通过

本轮部署及验收已经完成，没有半途部署需要续跑。服务器操作均由用户执行命令并回传，代理未登录服务器；以下是本轮回传与用户确认所证明的状态，不是之后自动持续监控的结果。用户要求本次交接提交推送后暂停，不继续开发、部署、清理或创建监控。

### 实际运行与发布范围

2026-10-24 13:13:28 CST启用应用`0ee524e31734b44fb7771b79`，源码和包内数据均绑定`a0298cd25da9cbf46a9909d7e5b3723e82adea8f`。`current`与`/proc/148673/cwd`均指向`/opt/racepick/releases/0ee524e31734b44fb7771b79`，服务active/running。PID148673仅为当时快照，以后须重新核对。上一应用`bd12e3fb2c2519b0238afd90`保留。

公网global manifest回传数据版本`f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e`，仅五区满星理论599＝578非OC＋21OC，561普通路线/38特殊，49车、44图42有值；四区/高手没有进入运行数据。614键完整维护数据、四区11理论、两区三星高手与普通镜像、36条独立参考及工作簿仍只在维护侧。国服完整health保持ok/production/schema6/community1/contribution1/feedback1，contributions/feedback/score_writes均true，成绩版本`42d62fde9b81197ac0558087a9a25f97`未变。未执行正式库初始化、schema迁移或本地成绩/账号/测试数据导入，也未用代码包覆盖score-state。

上传完整归档SHA256`85ee2e8e26045b51f4b67dbbb439dfda21ce95d0673b1ddc4da57f84cde9c448`及10929698字节核对；交付目录13项SHA、应用包85文件、599/21OC/38SC范围均通过。用户确认19个离线依赖安装、pip check和Linux/Python3.12临时库原生自检通过，新版独立.venv成功；本轮安装完整日志未回传，不扩写成Linux全量测试套件均已重跑。旧包及新包均未重建或修改；包构建记录中的“PENDING server”是构建当时状态，本节是后续实际验收结果。

### 成套备份与独立恢复演练

| 阶段 | 备份（/var/lib/racepick/backups/） | 独立演练（/var/lib/racepick/restore-drills/） | 证据 |
| --- | --- | --- | --- |
| 旧版在线 | scores-20261024T050437147757Z.zip | e354e96ad92c1b79e112b266 | 完整回传通过 |
| 停服最终 | 未回传具体路径 | 未回传具体目录 | 用户明确确认备份/演练通过、正式库未替换；不得猜测路径或SHA |
| 新版在线 | scores-20261024T051434290756Z.zip | 7fc34c4d8b50be02f8e3713a | 完整回传通过 |

两份已完整回传备份均159785字节、racepick:racepick、mode600；旧版ZIP SHA256`d8d097aca054ab05d9123aa2bf4eda09252b1d862a965f151621c4e04bdf0b38`，新版ZIP SHA256`7342fe3b17eb98dfc1683c3ac5e808b4af6db1d60ac37989bd2f617c41950cd0`。两份解包内容哈希一致：accounts.sqlite3=`7f1cd5db2c7d0d404f00cd1aed3dab6aa68e2e753acbbef26e862130cfe8d81d`，国服当前成绩JSON=`bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9`。恢复结果39用户、21车库、3投稿，pending_batches0、active_database_replaced=false；贡献schema1，contributions0/sources1/events0/preferences1；反馈schema1，tickets/events/requests均0。上述计数仅对应两份完整回传，不为缺失最终备份日志补造计数。

### 调度与公网验收

2026-10-24 13:17:20 CST回传，racepick-backup.timer已恢复enabled、active(waiting)，LAST2026-10-24 04:16:12 CST，NEXT2026-10-25 04:18:31 CST。这证明调度恢复；不是宣称10月25日任务已执行。上次04:16:13定时备份成功见本轮最初journal回传。恢复调度后health仍ok，成绩版本及开关保持。

用户明确确认桌面浏览器与手机微信公网验收通过。此前所列国服正常、国际五区理论选车计算/OC/SC、分服车库、三行布局、c2兔子搜索与国际服隐藏R筛选的验收，以用户本轮整体通过确认为依据；代理未独立操作微信或取得逐项截图。没有遗留的待执行部署步骤。本轮保留旧版本、全部备份/演练、工作簿和测试数据；没有系统升级、Nginx重配或目录清理。

### 本次收尾边界

仅更新部署/交接文档并按授权提交推送；不改代码、成绩JSON、运行manifest、维护台账或现有Excel，不重新打包、不重启服务、不重复演练或迁移。精确记录在工作区maintenance/deployment-global599-20261024/DEPLOYMENT_RECEIPT.json。唯一记录缺项为停服最终备份路径、SHA及演练目录未回传；其成功由用户确认，不影响已经完成的部署验收结论。以后的新任务先读最新文档并核对现场，不能照历史PID和目录状态续跑。提交推送完成后暂停。


## 2026-10-24 最新：599条更新已提交推送，完整发布包就绪，尚未部署

本轮代码/数据提交a0298cd25da9cbf46a9909d7e5b3723e82adea8f已推送main，git ls-remote核对一致；随后本段交接记录单独提交，不改变发布包源码绑定。构建使用新的干净独立检出release-build-global599-20261024，旧release-build-20261024和旧交付包均保留。原未跟踪源表、shared工作簿和_star_curve_fit.py未加入提交或打包。

- 新发布ID：0ee524e31734b44fb7771b79；目标Ubuntu24.04/x86_64/Python3.12。
- 本地交付目录：repo/.production-build/delivery-20261024-global599，14文件，SHA256SUMS.txt覆盖其余13文件。
- 完整上传归档：repo/.production-build/RacePick-International599-20261024-0ee524e3-delivery.zip，10929698字节；SHA256：85ee2e8e26045b51f4b67dbbb439dfda21ce95d0673b1ddc4da57f84cde9c448，旁有.sha256.txt。
- 内层应用ZIP：racepick-accounts-release.zip，10858488字节；SHA256：b39d06f2cec0de56f09be985222921139ed35c8da25174be3ec15ae29220f29d；85个manifest文件，含19个锁定离线依赖。
- source/data provenance均绑定a0298cd25da9cbf46a9909d7e5b3723e82adea8f；三份国际JSON及国服两份JSON逐字节等于已提交内容，其余文本仅有Windows检出行尾差异，已逐项规范化回比。相较上一发布包仅PRODUCTION_DEPLOYMENT.md、三份global JSON、index.html、styles.css、tools/build_global_data.py改变；账号/成绩/贡献/反馈运行代码和两份国服JSON均与旧包一致。

发布范围仅五区满星理论599（578非OC+21OC，561普通路线+38特殊），49车、44图42有值，数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。包内其他区档为空，无显式低星成绩；四区11理论、两区三星高手、2个普通镜像、36参考记录、614键完整维护JSON/台账与所有Excel均未打包。包内国服JSON与上一发布包字节一致，不额外发布国服成绩；更不能覆盖服务器score-state。没有数据库/账号/凭据/反馈/候选/测试数据或未跟踪文件。

本轮验证：JavaScript81通过；Python214执行、213通过、1个Linux专用检查在Windows跳过。完整维护614键/运行599键隔离核对、原434来源与旧发布包哈希、85文件/19wheel锁定哈希、外层13SHA与14文件归档回读均通过。用交付目录内独立deploy_production.py在本地新目录暂存成功，未激活；解包程序production/selfcheck.py以Windows临时数据库通过HTTP、备份/恢复和组件自检，不发邮件、不用现有用户库；19wheel按Linux CPython3.12标签离线解析成功并逐哈希相等。PACKAGE_VERIFICATION.json/RELEASE.json保存可独立核验结果。Linux原生安装/正式库现场兼容性仍待用户上传后执行，不冒充已在Linux或生产运行。

本轮没有登录/读取/修改生产服务器，也没有运行迁移、初始化、切换或清理。最后已知生产仍为用户此前验收的bd12e3fb2c2519b0238afd90；其PID、健康、成绩版本、备份调度和公网情况须部署时先只读重核。下一轮用户开始部署后，再逐步给命令、等待回传核对，不能直接续跑旧部署步骤。国服原表/目录、源工作簿、614维护数据、OC、36参考、旧包/备份/演练/测试数据保持。原完整工作树只保留3个既存未跟踪文件；不clean/reset或自动同步工作簿。


## 2026-10-24 本轮599条国际服更新：提交与完整发布包准备

用户已授权提交推送本轮更新并准备完整可校验发布包，明确暂不操作服务器。发布仍严格限定国际服五区满星理论：599条＝578非OC＋21OC，561普通路线/38特殊，49辆可计算车，44图42有值，富士最后两图空。数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。维护侧完整JSON/台账/现有Excel的614键及36条高手参考均保留；四区11理论、两区三星高手和普通可用镜像只用于维护，不装入运行包。Git跟踪的Excel可以提交，但发布白名单排除所有工作簿、完整维护JSON/台账、候选、真实账号/成绩库、凭据和测试数据。

与最后验收的bd12e3fb2c2519b0238afd90相比，待发布内容还包含此前已提交未上线的三行分组布局与c2“兔子”别名，本轮国际服隐藏R级占位、已授权OC估算来源绑定及国际数据维护成果。国服已跟踪数据/原表未改；包内国服基线来自已提交版本，不能覆盖线上独立score-state，不导入本地成绩或重跑迁移。

fetch后main与origin/main同为4d261611f666685bb865dd81cc83e5ad9ea9697a，无新远端变更，无需合并。发布前JavaScript81项通过，Python214项运行/213通过/1项Linux专用跳过；完整维护614键、运行投影599键、manifest哈希与纯生成器校验均通过。复用build_production.py和19个哈希锁定的Ubuntu24.04/x86_64/Python3.12离线wheel，从本轮提交的干净检出构建。具体源码提交、发布ID、包哈希和独立验证结果以本轮RELEASE.json与PACKAGE_VERIFICATION.json为准；旧包不覆盖。

最后已知生产部署为用户此前验收的bd12e3fb2c2519b0238afd90（321条国际数据），成绩版本42d62fde9b81197ac0558087a9a25f97。本轮未登录服务器或重新核验线上，不把历史PID/备份调度时间当现场状态。以后部署仍先给只读核验命令，由用户执行回传逐步核对，再暂存/安装运行环境/成套备份演练/切换/恢复调度/公网验收；不初始化、重复迁移、覆盖服务器成绩或清理旧版本、备份和演练目录。


用户已完成逐步部署，明确确认桌面及手机微信验收通过。生产应用bd12e3fb2c2519b0238afd90，成绩版本保持42d62fde9b81197ac0558087a9a25f97；本次无生产迁移。详细实际结果与备份路径见文末及CLOUD_HANDOFF.md最新节。下文保留发布前准备和执行流程。

## 交付与范围

复用build_production.py、deploy_production.py及production_release_tools.py的完整生产交付流程，使用干净提交构建；代码与国服JSON均绑定提交，离线19个Linux/Python3.12依赖必须与requirements-linux-py312.lock逐哈希匹配。外层SHA256SUMS.txt、RELEASE.json和ZIP内manifest.json可独立核对。国际服三份JSON及生成/验证工具作为完整组件打包，缺件、混用版本或哈希错误均拒绝；旧包仍可校验。

交付只包含白名单程序、国服基线JSON、国际服运行JSON和离线依赖，不含真实账号、数据库、凭据、反馈、工作簿、候选资料或本地测试数据。production/selfcheck.py增加国际服数据和HTTP读取检查，全部在新建临时库执行；Linux原生环境和迁移分支仍须上传后运行，不能以Windows自检代替。

上次已部署国际服首期为321条（315非OC/6OC）、29辆基础车，普通291/SC30；本轮新包为599条（578非OC/21OC）、49辆基础车，普通561/SC38，均只五区满星理论、44图/42有值。富士最后两图暂无成绩；4辆EVO参数待补。国际车库/OC/草稿独立保存在本机；国际云车库、投稿、审核、发布链、自审免积分和OCR未实现。国服已有账号/成绩/贡献/反馈链继续沿用，无新增生产schema迁移。

## 生产成绩边界

包内国服JSON是代码提交的数据基线，包含本次本地授权的白龙×幽灵船22.84；线上启用score-state后，实际成绩优先使用独立版本库，部署程序不会以包内JSON覆盖它。这个数值是否已在服务器存在、是否另需正式成绩版本发布，须上线时根据实际当前版本只读核对，再单独给出差异。不得初始化、重复迁移或用完整本地JSON覆盖线上新投稿。

国际服JSON是这次新增的静态独立数据集；与国服score-state、账号资料和反馈库隔离。

## 后续执行顺序

参照已验收的GARAGE_DEPLOYMENT.md。每一步得到用户回传并核对后才给下一步命令，不一次性执行以下全流程。

1. 现场只读核对current、systemd服务、实际进程cwd、完整health、备份调度/最近结果、备份目录及空间。最后已知应用bd12e3fb2c2519b0238afd90、成绩42d62fde…仅为待核基线，不预设现场相同。
2. 用户上传整个交付目录，核对外层全部SHA、ZIP内manifest及真实新发布ID；deploy_production.py默认只暂存，不激活。
3. 在返回的新版本目录运行既有install-runtime.sh，安装锁定离线依赖并通过Linux/Python3.12临时库原生自检。这里临时库迁移不是正式库迁移。
4. 用当前旧程序生成成套备份，校验并独立目录恢复演练，记录当前成绩版本、各类counts和active_database_replaced=false。
5. 用户确认维护窗口后暂停备份timer，等正在执行的备份结束，停网站并生成停服最终成套备份。无需生产迁移/导入/初始化。
6. 用本次交付工具激活真实发布ID，启动网站，核对current、服务状态、/proc/MainPID/cwd和完整公网health；原schema、成绩版本及开关保持。
7. 验证新版成套备份和独立恢复，恢复timer，确认enabled、active(waiting)及明确NEXT；再做国服/国际服桌面和手机微信验收、分服草稿/车库、OC/SC、五图互斥、空图显示。

若异常先保留现场和日志，依据兼容性及实际旧版本讨论代码回退；不恢复旧SQLite或覆盖用户车库来处理页面问题。不自动清理旧发布目录、工作簿、备份或测试数据。

## 2026-10-24 国际服上线及公网验收完成，工作暂停

证据来自用户逐步执行服务器命令的完整回传及明确验收确认，代理未登录服务器。2026-10-24 08:30:27 CST启用新应用bd12e3fb2c2519b0238afd90，源码/数据提交5ade7ea3598eb104f136365fb0a51574c16d8013；current与/proc/145790/cwd均为/opt/racepick/releases/bd12e3fb2c2519b0238afd90，active/running。PID为当时记录，后续重新核对。

- 完整上传归档SHA、目录13项SHA均通过，发布ID及85文件清单核对；暂存未激活阶段旧版保持。Ubuntu24.04/x86_64/Python3.12.3，19个锁定离线依赖安装及pip check、Linux临时库原生自检均通过；临时库自检不等于生产迁移，本次没有生产初始化/迁移/导入。
- 上线后完整health：ok/production/schema6/community1/contribution1/feedback1，contributions=true、feedback=true、score_writes=true，成绩版本42d62fde9b81197ac0558087a9a25f97保持。当前国服成绩JSON哈希bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9；包内新增白龙普通22.84没有通过此次代码部署发布到score-state，后续如需发布须单独比较审核，不能用整包覆盖线上成绩。
- 三次成套备份及独立恢复演练均通过，均160113字节、racepick:racepick、权限600；恢复结果39用户/21车库/3投稿，pending_batches=0、active_database_replaced=false。贡献schema1，counts contributions0/sources1/events0/preferences1；反馈schema1，tickets/events/requests均0。停服最终备份与新版备份内各文件哈希一致，账号SQLite哈希cef5bfa17f519c03b59459e173a2ec48743464a2e24d49a1c31c696aaf8b201a。

| 阶段 | 备份（/var/lib/racepick/backups/） | 独立演练（/var/lib/racepick/restore-drills/） |
| --- | --- | --- |
| 旧版在线 | scores-20261024T002837971492Z.zip | 3f1ef0a291f8b20324111663 |
| 停服最终 | scores-20261024T002956371320Z.zip | 4e858de18e76f918a60f2029 |
| 新版在线 | scores-20261024T003107716123Z.zip | c7b65a1385de6745d3d7a78b |

- 2026-10-24 08:31:40 CST回传：备份timer已恢复enabled、active(waiting)，NEXT为2026-10-25 04:17:45 CST；LAST为10月24日04:16:12，实际04:16:13成功生成scores-20261023T201613699083Z.zip。这证明新版切换前的自动备份成功及切换后的调度恢复，不表示10月25日已执行。恢复timer后的完整health保持。
- 用户明确确认桌面和手机微信验收通过，覆盖此前五图选车/分服车库与草稿/OC及SC/空图项目；两张截图另指出控件排版偏好，不将此偏好混作既有功能验收失败。代理未独立操作手机微信。
- 登录提示另行只读核查：dpkg --audit无输出、无reboot-required标记，最近自动更新日志All upgrades installed，cloud-init被保留未升级；早期发行版元数据警告后近期日志不再出现。未执行apt升级、发行版升级或重启，不凭日志推断cloud-init保留原因。

### 已提交但尚未发布的两项后续修正

用户希望桌面恢复三行，手机档位换行时分组更清楚。476a9e2只改styles.css：服别/档位/分区各自一行，浅色分隔线；档位组内仍可换行。真实本地浏览器1280/390/320宽验证，无横向溢出；320宽自动档换到本组下一行，分区仍在下组，国际服隐藏项无残余分隔。1b2361b只在既有NICKNAME_ALIASES加入兔子→c2，保持车辆身份/目录/成绩不变，国服与国际服实际搜索均匹配c2。14项前端回归通过。截图位于repo/.production-build/layout-followup-20261024/。

这两项仅提交到源码，未重新打包或部署；生产仍为bd12e3fb2c2519b0238afd90，旧发布包及其校验值保持。未来需另行准备新包并由用户执行部署。用户要求完成交接推送后暂停：不清理旧应用、备份、演练、工作簿或测试数据，不继续系统维护、成绩发布或其他开发，无监控/提醒。
