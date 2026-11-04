2026-11-04 分功能Git交付：内容安全/共享队列cea4386、原生网关5d39af5、离线交付及启动依赖修复eeb966c、阶段文档bfcf97e，已推feature/map-layout-parser；主repo仅归档现场交接，不合并功能分支、不重新部署、不倒改封存包来源。用户已转交小程序侧，手机OCR验收仍待后续。见[Git回执](GIT_DELIVERY_20261104.json)。

2026-11-04 最新线上：网站7241、原生交付35bd加已记录的单文件运行依赖补件；CN OCR服务端已开启，baselineCheck唯一合成审核通过，共享桥/guest active并开机启用，原队列schema1仅迁移一次。Global OCR及账号/B–E关闭，正式双服成绩及原网站/worker保持，backup.timer active。真实微信/手机OCR和激活后的实图完整链路尚未验收。见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首、[现场回执](MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json)、[小程序回交](MINI_OCR_CN_CLOUD_HANDOFF_20261104.md)。下方disabled与a933记录按历史阅读。

2026-11-04 最新兼容上线：网站7241d9d67cc99178bd7d2d14、隔离访客网关交付35bd5c5d2e618b555de3a70c的实际PID/cwd及公网健康/关闭门禁通过；原双服成绩指针、原网页OCR和单队列保留，原生图片disabled、bridge停止、未迁移队列或配阿里密钥/付费。最新业务备份独立恢复及访客/原队列保全完成，backup.timer恢复enabled/active；未来定时执行和本次真实微信/手机重验未核实。见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首及[现场回执](MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json)。下方a933及第一阶段记录为历史。

2026-11-04 隔离访客测试入口：https://mini-test.racepick.cn 已通过服务端TLS/门禁/资源及挂载隔离核验，真实微信SDK/真机待验证；主网站a933保持。仅访客会话和4516/694固定快照，图片/账号/B–E关闭；新服务未设开机自启。见[小程序回交](MINI_GUEST_STAGE1_CLOUD_HANDOFF_20261104.md)、[激活回执](MINI_GUEST_STAGE1_ACTIVATION_RECEIPT_20261104.json)及[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首。

2026-11-03 main源码整合：已合入所有本地分支的已提交分支头，包括网站共享核心/原生接口、小程序客户端、安全配置修复、独立Demo和旧PR文档；保留main已上线4516/694原字节。前端212通过，Python399执行/397通过/2项Linux专用跳过；并行小程序未提交外观/管理页开发仍留原树。仅Git整合，不重新部署。见[整合回执](MAIN_INTEGRATION_20261103.json)。

2026-11-03 数据Git归档：批准冻结对应五份运行数据已分别按国服/国际服提交，组合数据提交613c9bfb4ddfccfe335a949af4f83f41d8369269的Git blob逐字节匹配冻结。原已部署包的data_commit=null仍作为构包历史保留，不倒改制品。详见[Git数据交付回执](DATA_GIT_DELIVERY_20261103.json)。来源表、分享表、研究工具仅仓库归档，不扩大应用包。

当前生产（2026-11-03，部署及用户验收完成）：网站a933c9b7与维护CN4516/Global694同批正式上线，国际云车库schema1、cc850规则及国际fxxk入池生效，活动及公网五文件SHA已核验。国服写开/国际写关、原生API关闭；新版真实备份/独立恢复通过，timer恢复，NEXT11月4日04:15:05尚待未来执行。见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首及[部署回执](WEB_DATA_DEPLOYMENT_RECEIPT_20261103.json)。下方旧记录为历史。

当前生产（2026-10-31，部署及用户验收完成）：OCR发布c06cc48b已上线，正式worker隔离及资源配置核验通过，用户桌面/手机微信验收均正常。仍使用原双服活动成绩（国际659，不导入包基线664），国际写回关闭。新版真实备份/独立恢复及timer恢复完成，未来自动执行尚未核验；见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首、[部署回执](MAP_OCR_DEPLOYMENT_RECEIPT_20261031.json)、[执行记录](TAKEOVER_20261031.md)及[准备阶段核验](MAP_OCR_PREFLIGHT_20261031.md)。下方旧上线/未部署状态均为历史。

当前生产（2026-10-30 22:58）：3d978fd3已上线，coverage2/国际独立成绩schema1，运行659；国际写回关闭，国服开关保持。双服备份恢复与timer恢复已核验，用户桌面/手机微信验收待进行。见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首和[双服部署回执](GLOBAL_SUBMISSIONS_DEPLOYMENT_RECEIPT_20261030.json)。下方bbd与旧状态为历史。

当前生产（2026-10-30）：bbd92687已激活，运维/公网接口/新组件备份恢复及timer恢复已验证；用户桌面与真实手机微信验收待进行。见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首和[部署回执](COVERAGE_DEPLOYMENT_RECEIPT_20261030.json)。下方“未部署”属于历史构包阶段。

# 文档索引

2026-11-04 最新本地完整交付：[主交接](CLOUD_HANDOFF.md)。原生HTTP接桥、Ubuntu离线锁与v2候选35bd5c5d完成；功能树docs/MINI_OCR_RELEASE_RECEIPT_20261104.json绑定整包SHA及验证，docs/ALIYUN_OCR_RELEASE_PREPARATION_20261104.md为配置/部署边界。Ubuntu124项、Windows122通过20跳过及包内临时库/CPU合成识别通过；公网OCR关闭、未部署或真实送审，数据仅作种子，源码仍未提交封存快照。先核v2 README_FIRST及主repo最新交接，不续跑历史业务迁移。

2026-11-04 最新本地SDK/共享桥：[主交接最新记录](CLOUD_HANDOFF.md)。网站功能树docs/ALIYUN_SDK_QUEUE_BRIDGE_LOCAL_20261104.md及机器回执记真实SDK模拟HTTP、Unix socket单队列桥与WSL断网非root隔离46项通过；真实阿里调用、原生HTTP接线、Ubuntu/systemd/生产均未验收，公网OCR仍关闭。共用JobStore新增识图安全schema只能显式迁移，现场未执行。

2026-11-04 阿里云baselineCheck本地准备：用户已选定基础检测并确认服务开通；本地适配器/配置模板及23项模拟、48项既有回归通过，默认disabled，真实SDK传输/生产共享桥尚待完成。功能树说明 `map-layout-parser/docs/ALIYUN_BASELINE_LOCAL_PREPARATION_20261104.md`，实际状态见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)。未真实传图、付费调用或上线。

2026-11-04 最新阶段：第一阶段真实访客/固定快照已由用户回交开发者工具和“诊断版2手机”通过；OCR仅网站侧方案准备，提供方未选、公网OCR关闭。详见[CLOUD_HANDOFF最新记录](CLOUD_HANDOFF.md)。本地设计、协议草案、响应示意和回执保存在网站功能工作树 `map-layout-parser/docs/MINI_OCR_STAGE2_*_20261104.*`，未提交、未实现新桥/安全审核、未形成可部署包。

2026-10-31 小程序开发注意：[UGC声明、审核缺口与验收要求](MINIPROGRAM_COMPATIBILITY_20261030.md)。已记录成绩投稿、公开昵称、识图图片、反馈等入口；内容安全API/昵称审核等尚未完成，不能用OCR或成绩业务审批冒充内容安全审核。本次仅固定文档，未改功能/数据/发布包；后续开发须按首版实际范围落实并验收。

2026-10-31 构包完成：[地图识别发布回执](MAP_OCR_RELEASE_RECEIPT_20261031.json)、[交接提示](MAP_OCR_CLOUD_HANDOFF_20261031.md)。发布c06cc48b，功能源码f44e3c2/数据9e7d21f，最终Linux包验证通过，未推送功能、未合并main、未上线；生产只读核验/真实systemd/容量/TLS/手机微信待云端逐步处理。用户已验收整合页面，成绩表“新功能”保留。

2026-10-31 当前：[地图识别正式发布准备](MAP_OCR_RELEASE_PREPARATION_20261031.md)、[完整配套部署说明](MAP_OCR_DEPLOYMENT.md)。整合页面已由用户验收，成绩表“新功能”保留；已授权提交功能分支和构包，不推送、不合并main、不上线。生产缺项已实现并完成本地Linux演练，最终包复验及现场待核验以交付回执为准。下方早期“仍阻塞/页面待审”是历史阶段。

2026-10-31 地图识别发布准备：[发布核查与整合审核](MAP_RELEASE_READINESS_20261031.md)、[云端运维交接](MAP_OCR_CLOUD_HANDOFF_20261031.md)。最新整合预览 http://127.0.0.1:8032/ ，保留成绩表“新功能”标识，待用户审核；生产接入/原生验证/依赖与构包仍有阻塞，未上线、未构建应用发布包。下方其他功能发布记录按对应日期及云端最新回执阅读。

当前交付：[覆盖表发布完成回执](COVERAGE_RELEASE_RECEIPT_20261029.json)、[云端可复制提示词](COVERAGE_CLOUD_PROMPT_20261029.md)。最终包9f9b2e2b已构建校验，未部署；fe8候选保留但已被替代；历史阶段状态以最新CLOUD_HANDOFF为准。

最新工作：[真实覆盖表与发布准备](COVERAGE_RELEASE_20261029.md)、[已有站点升级](COVERAGE_DEPLOYMENT.md)。用户已更新A方案范围，正式实现后与最新数据分组提交推送/构包；生产由云端运维另行执行。

最新本地整合：[20261029功能合并与数据配套](FEATURE_MERGE_20261029.md)。A原型不合并，数据未代提交，生产未操作。

最新本地修正：[审核意见合并输入](REVIEW_OPINION_20261027.md)，功能完成，用户验收待确认，未发布。

最新本地开发：[页面样式统一](STYLE_UNIFICATION_20261026.md)，独立分支样式已于2026-10-27通过用户本地验收，标志仅保留主页，未发布；A原型保留不合并；下方历史发布状态以CLOUD_HANDOFF最新记录为准。

本轮已完成main合并推送与完整构包（发布ID171d872a414dea28be25eaa1），未部署。先读 [完成回执](RELEASE_RECEIPT_20261025.json)、[云端交接提示词](UNREAD_USAGE_CLOUD_PROMPT_20261025.md) 与 [升级交接](UNREAD_USAGE_DEPLOYMENT.md)。历史限制仅对应此前阶段。

当前功能：未读提醒与使用统计已本地验收，构包源码7651da5、数据cbe9ea3。生产状态须运维现场核验；下方历史开发/接收记录不代表当前发布状态。

仓库说明集中在 `docs/`。以下路径从本目录出发；发布包仍沿用已验证的文档文件名和包内位置。

## 当前交接与部署

- [2026-10-30参考列与精简投稿完整包](COVERAGE_RELEASE_20261030.md)、[云端提示词](COVERAGE_CLOUD_PROMPT_20261030.md)、[机器回执](COVERAGE_RELEASE_RECEIPT_20261030.json)：本地构包完成，生产待核验；替代9f/fe8包。

- [云端交接记录](CLOUD_HANDOFF.md)：从最新记录开始，区分历史验收与本轮现场证据。
- [可复用交接提示词](CLOUD_HANDOFF_PROMPT.md)
- [生产部署流程](PRODUCTION_DEPLOYMENT.md)
- [快速切换服别的限流修复（599条已上线验收）](SERVER_SWITCH_FIX.md)
- [国际服部署与范围](INTERNATIONAL_DEPLOYMENT.md)
- [成绩版本与生产写回](SCORE_PRODUCTION_DEPLOYMENT.md)
- [静态部署](DEPLOYMENT.md)

## 功能开发与验收

| 功能 | 本地说明 | 部署或专项说明 |
|---|---|---|
| 国际服 | [本地与维护范围](LOCAL_INTERNATIONAL.md) | [部署](INTERNATIONAL_DEPLOYMENT.md) |
| 账号 | [本地账号](ACCOUNTS_LOCAL.md)、[邀请](INVITATIONS_LOCAL.md)、[邮件](MAIL_LOCAL.md) | [生产](PRODUCTION_DEPLOYMENT.md) |
| 投稿 | [成绩提交](SUBMISSIONS_LOCAL.md)、[预览](PREVIEWS_LOCAL.md) | [成绩生产流程](SCORE_PRODUCTION_DEPLOYMENT.md) |
| 公告与账号管理 | [本地](COMMUNITY_LOCAL.md) | [部署](COMMUNITY_DEPLOYMENT.md) |
| 贡献排行榜 | [本地](CONTRIBUTIONS_LOCAL.md) | [部署](CONTRIBUTIONS_PRODUCTION.md) |
| 反馈 | [本地](FEEDBACK_LOCAL.md) | [部署](FEEDBACK_PRODUCTION.md) |
| 车库布局 | [布局修复](GARAGE_LAYOUT_FIX.md) | [部署](GARAGE_DEPLOYMENT.md) |
| 成绩版本 | [本地版本](SCORE_VERSIONS_LOCAL.md) | [写回实验环境](WRITEBACK_LAB.md) |

## 未读提醒（独立工作树本地开发）

- [功能、隔离演示与验收](NOTIFICATIONS_LOCAL.md)：尚未提交、构包或上线；首页/菜单/条目按账号未读。

## 使用统计（本地开发，未提交）

- [采集口径、统计页、隔离演示与部署边界](USAGE_LOCAL.md)：新端口8017；模拟统计与线上事实分开。

## 数据维护

- [Python工具](PYTHON_TOOLS.md)
- [赛道标签](track_tags.md)
- 根目录保留数据文件和维护工具入口；`tests/` 存放顶层回归测试，`backend/` 内的后端测试继续与模块同目录，`examples/` 存放隔离演示脚本。

旧文档中的历史提交、线上版本及验收结果仅作为历史记录，不代表实时服务器状态。
