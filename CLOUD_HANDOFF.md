# RacePick 云端运维交接（2026-10-24 更新）

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

## 以下为历史交接记录

## 2026-10-23 本轮接手核验（未进行新部署）

以下为本轮只读检查结果；不延续历史部署步骤，不表示已重新核验服务器内部状态。

- 已读取根目录CLAUDE.md/context.md及本仓库交接、车库部署与验收记录。根目录说明仍停在发布准备阶段；README部分版本/合并描述也有历史残留，不能据此判断实时状态。
- git fetch origin成功；本地main、origin/main及git ls-remote的main均为90db8b90969214f696501455f74a113af8d6e590。已包含3baf0b3车库修复和1760a11上线验收记录。相对打包源码3baf0b3，HEAD只变更CLOUD_HANDOFF.md、CLOUD_HANDOFF_PROMPT.md、GARAGE_DEPLOYMENT.md、GARAGE_LAYOUT_FIX.md四份文档，没有待发布的运行代码。
- 全部10个已登记工作树没有已跟踪文件的未提交改动（本记录写入前）；repo仍有既存未跟踪_star_curve_fit.py、gauntlet_data_shared.xlsx，均未操作。feature/track-top-three虽显示领先自己的旧远端25项，但它是当前main的祖先（main领先21项、该本地分支独有0项），不构成新的待发布功能。没有合并、切换分支、推送或清理。
- 本轮直接HTTPS读取/api/health返回200：status=ok、mode=production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true、score_version=42d62fde9b81197ac0558087a9a25f97、score_writes=true。首页/返回200；按backend.app的首页注入规则生成预期内容，与公网响应完全一致；styles.css公网与本地SHA256均为07d51cf3530b3b52ff96fb01ac68409fac214002b0a32c5773e9c5012e2fb4e0。/index.html返回404符合路由白名单，主页实际入口为/。
- 公网health不包含应用发布ID，因此6ee40a45b00b0e347bf973fe仍是最近用户回传确认的应用版本，不能仅据本轮HTTP检查声称重新确认了current或实际进程cwd。本轮未登录服务器，也未核验当前systemd、备份文件或timer；最近自动备份及下次调度证据仍见下方验收记录，10月24日计划执行不能提前记为成功。
- 本地8000–8011范围仅发现127.0.0.1:8011监听；PID8776的命令指向garage-toolbar-responsive/.local-accounts/preview，health为local、贡献/反馈关闭。其余历史环境文件保留，端口未监听不代表数据已删除。本轮未启动、停止或重建任何测试环境。
- 现有11文件车库交付目录保留，ZIP SHA256重新读取仍为fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb；没有重打包或变更旧包。本次未重跑回归，沿用既有验收记录；HTTP检查不替代登录、真实邮件及手机交互验收。

当前没有明确的新开发或发布目标，先由用户确定范围。账号、成绩、反馈、备份、测试数据、工作簿和未跟踪文件继续保留；服务器仍按给命令、用户执行并回传的方式逐步推进。本轮交接更新仅保留在工作区，尚未授权提交推送。

## 主线整合与通用交接入口

用户随后授权合并main。已验收的fix/garage-toolbar-responsive是远端main的后继，使用快进整合，无冲突；本地两份JSON、两份工作簿及保留脚本的哈希与修改时间均未变化。下文“未合并main”属于当时的历史状态，不再作为当前Git结论。源码整合未重新部署或修改生产环境，后续先fetch核对最新状态。

长期复用、无需填写版本号的提示词见[CLOUD_HANDOFF_PROMPT.md](CLOUD_HANDOFF_PROMPT.md)。该提示词以“上一轮部署已完成”为交接起点，要求接手模型自主探索代码和运行状态；本文件继续保留具体历史证据。

## 最新交接：车库布局修复已上线验收，工作暂停

本节覆盖下方历史状态。用户于2026-10-23确认页面验收完成，并要求更新交接、完成必要推送后暂停。以下生产证据来自用户回传，本次文档收尾未访问或修改生产环境。

- 当前应用 **6ee40a45b00b0e347bf973fe**，打包源码3baf0b3970dc638afd9910723943f3a7ad6a0781，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与实际进程cwd均已确认，切换时PID138683仅作历史记录。
- 最后完整health：status=ok、mode=production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true，成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。本次无数据库迁移，没有用包内JSON覆盖成绩。
- 用户确认页面验收完成；范围为此前要求的桌面对齐、手机微信分行以及保存/恢复/点亮/清空/排序。没有提供新的真机截图，不声称代理独立完成真机检查。
- 旧版在线备份演练、停服最终备份校验、新版备份演练均由用户简述确认通过，新版active_database_replaced=false；具体ZIP及演练目录未回传，不编造恢复点路径。
- 完整回传确认 **10月23日04:16:09–04:16:10 CST自动备份成功，退出码0**，文件scores-20261022T201610532450Z.zip，155551字节。这是升级前反馈版本的自动备份证据，覆盖下文“10月23日自动执行尚未核实”。
- 本次timer于 **2026-10-23 10:46:44 CST** 恢复enabled/active(waiting)，NEXT为 **2026-10-24 04:16:12 CST**。该次未来计划尚未执行核验；一条health回传被截断，随后单独回传完整JSON确认正常。
- 交付garage-toolbar-responsive/.production-build/delivery-20261023-garage共11文件，服务器上传目录/root/racepick-deploy/20261023-garage-6ee40a45。ZIP SHA256：fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb。包内只有index.html和styles.css有运行内容变化，另一个后端文件仅LF/CRLF不同，逻辑一致；旧包不修改。
- 最新交接分支 **fix/garage-toolbar-responsive**。main仍73e3f8b，未合并；反馈与其他已验收功能都在本分支历史中。先fetch核对最新状态，不把源码同步当成再次部署。
- 原8011、8010、8009测试环境及账号库、工作簿、未跟踪文件保留；本轮不清理目录、不改配置、不新增监控。当前6ee40a…与旧4a28f6d…及备份均保留。

详细记录见[GARAGE_DEPLOYMENT.md](GARAGE_DEPLOYMENT.md)和[GARAGE_LAYOUT_FIX.md](GARAGE_LAYOUT_FIX.md)。完成本轮文档推送后暂停，不自动继续合并、部署、清理或核验未来备份。

## 上一轮交接：反馈功能已上线验收（2026-10-22，历史）

本节为最新状态，覆盖下文上一轮排行榜升级的历史快照。所有生产事实来自用户服务器回传或明确反馈，本次文档收尾未访问生产环境。

- 当前应用 **4a28f6d76b9d3e93d3227120**，打包源码b17d6fcfe1c831b3f7fbb2b4923ea0a9efb33168，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与实际进程cwd已确认一致，切换时PID132627仅作历史记录。
- health：production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true；最后成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。用户确认昵称展示、按钮统一、文字反馈公网验收通过，功能正常。不能重新执行已完成的反馈/贡献/成绩迁移。
- 新版成套备份及独立恢复演练由用户简述确认通过，feedback_schema=1、contribution_schema=1、active_database_replaced=false；新版ZIP和演练目录未回传，不编造路径。
- timer于 **2026-10-22 21:46:12 CST** 恢复enabled/active(waiting)，NEXT为 **2026-10-23 04:15:58 CST**，替代下文旧的04:19:44计划；LAST仍为10月22日04:18:37，尚无新版首次定时执行成功证据。
- 本次已核实的旧版在线备份为scores-20261022T134206474628Z.zip，演练目录6ed23e688a30ec2f6f7418fd，counts27/15/2、昵称偏好1、未替换活动库。停服最终备份、迁移保护备份、新版备份的具体路径未提供，若需恢复点须现场只读核验。
- 当前文档分支 **release/account-feedback-production**；功能基线feature/account-feedback=28d4c96，生产适配b17d6fc；main最后核对73e3f8b，未合并。先fetch核对最新状态，源码同步不等于部署。
- 本次交付account-feedback-production/.production-build/delivery-20261022-feedback，共10文件，绑定4a28f6d…；ZIP SHA256为89fc52c23d5aea9f16eee985124f4eb51dd73706d0799b44d1529fac1cfe4b78。服务器上传目录/root/racepick-deploy/20261022-feedback-4a28f6d7保留。文档更新不修改已部署包。
- 先读本节和[反馈生产验收记录](FEEDBACK_PRODUCTION.md)文末，再查下文的历史部署、清理和保护约束。原8010及8009测试环境、账号、工作簿和未跟踪文件继续保留。
- 本轮未进一步清理目录。当前4a28f6d…、上一1fcc18c…及此前保留的651ea3d…不因新部署被自动删除。反馈schema1后不能直接切回不支持反馈的旧程序；禁止单SQLite恢复或用旧工具绕过兼容检查。

后续待证据：10月23日04:15:58计划备份的实际结果；本次未回传的具体备份路径。此处不自行新增监控或重复生产操作。本轮仅提交推送文档，不合main、不修改生产。

## 上一轮排行榜已验收状态（历史）

本交接依据用户服务器回传和明确验收反馈，不是代理独立登录服务器的结论。历史文档中的“仅本地/尚未上线”以最新验收记录覆盖；未来操作前重新只读核验。

- 域名https://racepick.cn；Ubuntu24.04、Python3.12、Nginx代理127.0.0.1:8001。服务racepick-accounts，应用链接/opt/racepick/current，数据/var/lib/racepick。
- 当前已验收应用 **1fcc18c06a7b920ed0aa8b0b**，源码fa23531106e4eec54ccf9cd91164475888f354a9，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与运行进程cwd已确认一致；主进程当时130103，后续不能盲用旧PID。
- health：production、schema6、community_schema1、contribution_schema1、contributions=true；最后成绩版本42d62fde9b81197ac0558087a9a25f97、score_writes=true。版本和数量是历史快照，勿强制修回。
- 排行榜质量0–10＋正式采用10分、历史不补计、公开昵称/匿名、三类主页导航已上线，用户确认功能正常。原公告、账号管理、手动车库及成绩版本化均已完成，不重复迁移。
- 备份和独立恢复演练通过。timer在2026-10-22 20:28:08 CST恢复enabled/active(waiting)，NEXT为2026-10-23 04:19:44 CST；尚无该次定时执行回传。

## 先读与后续操作

先读本文件及[本次部署与清理记录](CONTRIBUTIONS_PRODUCTION.md)，再查COMMUNITY_DEPLOYMENT.md、SCORE_PRODUCTION_DEPLOYMENT.md、PRODUCTION_DEPLOYMENT.md和工作区根目录CLAUDE.md/context.md。本次文档分支release/contribution-production；main最后核对73e3f8b，功能分支feature/contribution-leaderboard为0938886，生产适配fa23531在release分支，未合main。先fetch核对最新Git状态，不把源码同步当成部署。

本地交付位于contribution-production/.production-build/delivery-20261022-contributions，9文件，绑定1fcc18c…；不可修改旧包冒充新版本。完整ZIP SHA256：aa7e70ba59f203c6ed2870d5689a840c8202c7534fd2234f10a5108e2ad0e0d9。当前服务器上传目录/root/racepick-deploy/20261022-contributions-1fcc18c0保留。

先确认新的任务范围；没有新部署目标时不重跑上线。发布先准备完整校验包，再按用户回传逐步暂存、临时库自检、备份、必要迁移、切换、验收和恢复timer。每次切换必须核对current、服务状态、/proc/<MainPID>/cwd、公网health，不能只看终端目录。

## 数据与恢复边界

保留所有账号库、测试环境和工作簿，特别是repo/gauntlet_data_shared.xlsx、repo/_star_curve_fit.py；不reset --hard、clean或自动同步工作簿。原8009独立模拟环境保留，不能把其数据导入公网。

成绩从独立score-state读取，代码包JSON不覆盖正式成绩。main的73e3f8b仅同步了云端肥龙★6四区高手34.90和普通镜像，工作簿未同步；后续云端写回不会自动同步本地JSON/工作簿。

迁移前最终成套备份scores-20261022T122554381864Z.zip；迁移保护备份scores-20261022T122638564366Z.zip；新版运行后盘点备份scores-20261022T122749408259Z.zip。均在/var/lib/racepick/backups。原始演练输出及证据限制见部署记录，不编造备份与演练目录映射。

禁止单SQLite恢复；灾难恢复须保留现场、独立目录演练并核对整套数据。贡献schema1后不能直接切回旧代码，即使保留了上一版本651ea3d…也不代表兼容回退。不要使用旧部署工具或手工ln绕过兼容检查。SMTP密码不输出、不打包。

## 已清理与继续保留

用户已确认删除旧应用目录09897d5f81a696dca0b95c8e、3ac58aba697f3189b751d6ea、7a0f2927404cab20f0a5a020、c907541d0c209f9a38a181a5；以及/root/racepick-deploy下accounts-release、accounts-credentials-fix、data-20261021、score-versions-20261021。旧包本地留档及校验已核实。约释放300M，非精确测量。

当前版和上一版应用保留；当前上传目录、community-20261022、20261016-icp、nginx-before-accounts-ghnuwvit及顶层静态发布文件保留。所有业务数据、成套备份、历史SQLite、score-state、恢复演练和/var/www静态目录均未清理。Nginx仍引用静态root，不可仅因代理已启用就删静态目录。以后清理重新核对路径/引用并取得具体范围授权，不扩大本轮删除授权。

## 尚无新证据的事项

- 10月23日04:19:44计划备份是否实际成功。
- 新规则启用后的真实投稿计分与发布回执逐项证据（不否定用户已确认的功能验收）。
- 公告由用户自行发布；本轮没有代发或核验其发布状态。

本次收尾仅更新并推送文档，不合并main，不修改生产、发布包或任何账号/成绩/工作簿数据。

## 反馈生产准备阶段记录（已被文首验收结果覆盖）
功能基线28d4c96，在独立release/account-feedback-production准备生产适配与交付。随后用户逐步完成安装、迁移、切换、备份演练及timer恢复，并确认公网功能正常。完整证据边界见FEEDBACK_PRODUCTION.md文末，最新状态以本文件首节为准。

## 2026-10-24 国际服本地验收通过，提交及发布包准备

用户明确本地验收通过，授权统一Excel为旧字体格式、提交推送并准备完整可校验包；本轮禁止服务器操作。国际服五区满星理论321条（315非OC/6OC），普通291/SC30，29基础车、44图42有值，富士两空图仍在最后。运行版本c7ea2f354e90bf70711c04ae05ced8d894ac9c1168a9b4c18393c9a9fd1b31f0，国际云车库/投稿/版本链及自审免积分/OCR未实现。

国际维护表与shared已统一宋体10pt及旧表头风格，成绩、行列、冻结及OC/SC区分不变；国服主表和同步副本已有宋体，字节保持。修改前原件在数据源/international-prep-20261023/maintenance/change-history/style-unification-20261024，历史表和资料均保留。gauntlet_data.global.xlsx为当前国际321条版本库副本。shared仅格式调整，仍是未跟踪文件；不将其历史缺项当删除授权。

现有生产打包器已补国际组件及独立哈希校验，保留旧包读取兼容；自检增加三JSON及国际入口HTTP检查。发布从干净提交及锁定Linux离线依赖构建，工作簿、账号/成绩状态、反馈、凭据及本地测试库不入包。包内国服JSON新增22.84不会自动覆盖服务器score-state，是否需要单独发布该成绩须现场核对。具体流程见INTERNATIONAL_DEPLOYMENT.md，包内RELEASE.json绑定真实源码/数据提交。

本轮未访问或修改生产，当前运行应用、health、备份timer及公网验收未重核。之后仍由代理给一条命令、用户执行回传后逐步核对，不重跑生产迁移、不初始化、不清理旧文件。

### 本轮发布包已生成并校验（尚未上线）

源码/国服数据提交5ade7ea3598eb104f136365fb0a51574c16d8013已推送main并用ls-remote核对。发布ID bd12e3fb2c2519b0238afd90；完整目录repo/.production-build/delivery-20261024-international共14文件，外层SHA清单13项全部通过，ZIP内85白名单文件（含19锁定离线依赖）。内层racepick-accounts-release.zip SHA256：1ecc93ea6d36eec12a5e3ca0ed96acddf8847dc6f549546c52d1eac9c11939ee。

便于完整上传的归档repo/.production-build/RacePick-International-20261024-bd12e3fb-delivery.zip，SHA256：ac6016cf81b3fa5f900a4d1aea1bc7c538d1b4218916fb8947d1fa8c835c8036；归档含上述完整14文件目录，已逐字节回读。PACKAGE_VERIFICATION.json保留详细回执。使用提交的干净独立检出构建，保护原工作树未跟踪脚本/shared；数据JSON与提交字节一致，Windows代码检出换行差异已独立核对，内层manifest绑定实际交付字节。

本轮Node80+Python125共205项通过，交付目录自带工具的独立本地暂存、解包目录验证和临时库HTTP自检通过；原始434资料哈希保持。Linux/Python3.12离线安装及原生自检尚待上传后用户执行。未操作服务器、未激活、未生产迁移；实际运行版本、健康、备份调度、线上成绩差异和公网验收均留待部署轮核对。后续文档提交不改变该已校验包绑定的源码提交。
