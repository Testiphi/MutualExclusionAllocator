# RacePick 云端部署交接（2026-10-22）

## 可直接复制给接手模型的提示词

```text
请接手 RacePick 的云端部署与运维工作，先读文档、核对现状，再按我每一步回传推进。

工作区：E:\hzz\work\MutualExclusionAllocator。
先读 community-controls/CLOUD_HANDOFF.md、COMMUNITY_DEPLOYMENT.md、PRODUCTION_DEPLOYMENT.md、SCORE_PRODUCTION_DEPLOYMENT.md，以及根目录 CLAUDE.md、context.md。历史段落中的“仅本地/未上线”可能已被较新的记录覆盖，以最新验收记录为准。

Git：PR #2 https://github.com/Testiphi/MutualExclusionAllocator/pull/2 已合入远端main，已核实合并提交fdc3a43包含b3798ca。后续先git fetch并核对最新远端，不假定main仍停在这个提交。此次文档交接位于community-controls工作目录、docs/cloud-handoff-20261022分支。主目录repo的本地main仍为2b1196a，不能把本地旧HEAD当最新基线。

保护范围：保留现有账号库、.local-accounts、独立测试库和所有工作簿。repo有用户未跟踪的gauntlet_data_shared.xlsx及_star_curve_fit.py；不要reset --hard、clean、覆盖、删除或自动同步工作簿。同步main前先看status和差异，必要时另建工作目录。不要把本地测试数据库、SMTP密码、工作簿或演示公告放进发布包。

最近用户确认的生产状态（后续操作前须重新只读核验）：
- 域名https://racepick.cn，服务器8.138.47.110，Ubuntu24.04 x86_64、Python3.12、Nginx HTTPS反向代理至127.0.0.1:8001。
- 服务racepick-accounts，current与运行进程cwd均已确认指向/opt/racepick/releases/651ea3d88a27bdff95088b75。
- 发布源码880333d；源码PR合并没有自动重部署，不能仅因main有新提交就再次上线。
- /var/lib/racepick/accounts.sqlite3，核心schema=6、community_schema=1。迁移时用户/车库/投稿数7/7/0只是历史基线，勿强行修回这些数量。
- 独立成绩状态位于/var/lib/racepick/score-state，最后确认score_version=c8889ff96eb29714d80248cca283b9fa，score_writes=true。正式成绩可能后续变化，不能拿包内JSON覆盖。
- 配置/etc/racepick/production.json；SMTP通过systemd LoadCredential读取/etc/racepick/smtp-password，不输出密码、不重新初始化账号库。
- 公告三种提醒、全部账号管理、停用恢复/强制退出/主号保护、默认手动车库保存已上线，用户确认验收完成；临时清空选单车/调星级不会覆盖已保存车库。历史公告和提醒设置可恢复。
- 新版scores成套备份、verify-backup及独立目录restore-drill成功，active_database_replaced=false，racepick-backup.timer已恢复。新版备份文件名未提供，勿编造；需要时现场查验。

已知备份：旧版在线scores-20261022T002419086391Z.zip；停服最终scores-20261022T002503031601Z.zip，均位于/var/lib/racepick/backups。它们是升级前备份，不能作为新版运行后的常规数据库回退来源。

部署要求：先准备完整可校验发布包，再一步一步带我上传、暂存、安装独立环境、临时库冒烟、成套备份/演练、必要时停服迁移、切换、验收、恢复定时器。依赖来自锁定离线wheels。旧交付目录community-controls/.production-build/delivery-20261022-community有8个文件，绑定651ea3d88a27bdff95088b75；不可原地修改旧包冒充新版本。

坑点：终端所在目录不代表线上current。曾因current仍为旧版、服务停用而出现502，开头版本断言返回1导致备份块无输出且未执行。每次切换必须核对readlink -f /opt/racepick/current、systemd服务状态、/proc/<MainPID>/cwd以及公网/api/health。

回退限制：community_schema=1后不可切回不识别账号停用状态的旧程序。已分离成绩后不可仅恢复单个SQLite；保留失败现场，在独立目录演练完整恢复，不能用旧库吞掉新账号/投稿。日常成绩回滚与灾难恢复是不同流程。不要重跑已经完成的分离迁移或community迁移。

PHP排查：用户只读输出未发现安装中的PHP/Apache软件包或运行服务，Nginx PHP配置只是注释，实际使用Python代理；Docker检查无输出。当前证据未发现PHP2Shell活动入口，不等于全面安全审计，也未完全排除手工安装面板。没有因此安装PHP、停服或修改配置。

开始时先总结你读到的当前状态及下一步需要核对的信息。如果我尚未给出新的部署目标，先确认本次要部署什么，不重复执行已完成的上线流程。不得把历史上线授权理解为任意后续生产修改授权。
```
