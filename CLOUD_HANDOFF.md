# RacePick 云端运维交接（2026-10-22 更新）

## 最新交接：反馈功能已上线验收（2026-10-22）

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
