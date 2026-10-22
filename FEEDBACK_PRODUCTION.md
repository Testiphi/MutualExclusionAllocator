# 账号昵称、按钮与反馈生产升级

2026-10-22。账号昵称展示、统一按钮和站内文字反馈已完成生产升级，用户确认公网验收通过。功能提交28d4c96，生产适配b17d6fc，发布版本4a28f6d76b9d3e93d3227120。下文保留部署方案，最新实际结果与证据边界见文末。8010及8009环境保留，不合并main。

## 本次范围

- 超级管理员账号管理展示昵称、公开/匿名状态，支持邮箱或昵称搜索；复用已存在的contribution_preferences，不复制昵称。
- 返回与导航链接显示为统一按钮，保留链接语义；原车库、投稿、成绩发布和管理权限不变。
- 已验证用户在个人中心提交和查看自己的文字反馈；仅超级管理员查看全部反馈、回复与调整状态，普通管理员不获得反馈管理权限。
- 本版无附件、无反馈通知邮件、不采集浏览器日志或车库、不计贡献分。来源只保留页面路径，不带URL查询参数；发布包运行时附带真实发布ID。
- 国际服不在本轮范围。

## 保留与迁移边界

只新增feedback_schema、feedback_tickets、feedback_events、feedback_requests及相应索引。已有账号、车库、投稿、公告、昵称、贡献记录、成绩版本、写回开关、备份全部保留。新反馈业务表必须为空，不导入本地模拟数据。

先成套备份，再持有服务锁和成绩维护锁事务迁移。工具比较所有既有业务表逐行指纹；版本漂移、未完成成绩批次、不完整反馈表均拒绝。成功后重试返回already_migrated=true，不清空现有反馈。生产启动只读取已完成的schema，不自动迁移。

本次要求已有schema6/community1/contribution1及独立score-state。不重跑账号初始化、成绩分离、community或贡献迁移，不改Nginx/证书/SMTP/生产配置/systemd服务定义。包内JSON仅用于基线及临时库自检，绝不覆盖服务器活动成绩。本地工作簿不修改。

## 历史基线（现场复核后使用）

最后已验收应用1fcc18c06a7b920ed0aa8b0b，成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true、contributions=true。上轮迁移时24用户/13车库/2投稿只是历史快照，本轮不得强行恢复旧数量。服务器可能已有新成绩或贡献，必须以本次preflight为准。

上轮timer于2026-10-22 20:28:08 CST恢复，计划2026-10-23 04:19:44；此记录不代表本轮仍在运行或计划已实际执行。旧目录清理已经完成，本轮不再清理或扩大旧删除授权，详见CLOUD_HANDOFF.md。

## 交付文件

新交付目录共10文件：racepick-accounts-release.zip、deploy_production.py、production_release_tools.py、PRODUCTION_DEPLOYMENT.md、SCORE_PRODUCTION_DEPLOYMENT.md、COMMUNITY_DEPLOYMENT.md、CONTRIBUTIONS_PRODUCTION.md、FEEDBACK_PRODUCTION.md、RELEASE.json、SHA256SUMS.txt。

本次流程以FEEDBACK_PRODUCTION.md为准，其余部署文档保留历史背景，不重跑已完成步骤。RELEASE.json绑定源码/数据提交和内容哈希，依赖复用已验收的Ubuntu24.04 x86_64 / Python3.12离线wheels锁定集合。白名单排除账号库、LOGIN、工作簿、截图、日志、反馈模拟脚本和实验室数据。

## 分步部署：每步回传后继续

### 1. 只读核对运行状态

核对current链接、racepick-accounts状态、MainPID对应/proc/cwd、公网health。记录当前应用、成绩版本、写回开关、贡献schema及是否已有feedback字段。检查timer的enabled/active/NEXT、最近备份service结果、最新ZIP和磁盘。此时不停止服务或触发备份。

### 2. 上传、校验、暂存及原生自检

新建本次上传目录，不覆盖旧交付目录。上传全部10文件，sha256sum -c SHA256SUMS.txt应有9个文件OK，清单自身不校验。运行python3 deploy_production.py --bundle racepick-accounts-release.zip，仅暂存。

记录返回的真实NEW_ID，进入/opt/racepick/releases/NEW_ID运行bash production/install-runtime.sh。离线安装并校验锁定依赖，临时库自检包括旧迁移链、反馈迁移、真实Linux服务锁、反馈页面/样式和成套备份演练。仅临时库执行，不发送邮件、不操作正式库；失败停下，不重复覆盖已有venv。

### 3. 新版本在线只读预检

在新版本目录执行：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.feedback_production preflight
```

应有feedback_schema=0、contribution_schema=1、pending_batches=0；score_version与当前health一致，score_writes保持。记录账号/车库/投稿数量、贡献各表数量及活动JSON哈希。贡献数不要求为0，不能清零；输出不包含账号身份、昵称内容或反馈正文。

### 4. 旧版在线备份演练与维护窗口

从当前真实旧版本目录运行backend.production backup，用其返回的真实ZIP路径执行backend.score_production verify-backup和restore-drill。确认active_database_replaced=false、版本和数量可解释后，再进入经用户确认的维护窗口。

停止racepick-backup.timer，确认可能运行的backup.service已经结束，再停止racepick-accounts并核对MainPID=0。从旧版本生成停服最终成套备份并校验，记录真实文件名。停服期间可能502；不要把终端所在目录当current。

### 5. 新版本显式反馈迁移

进入新版本目录，EXPECTED_VERSION替换为刚核验的实际成绩版本：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.feedback_production migrate --expected-version EXPECTED_VERSION
```

工具额外生成迁移前成套备份。核对existing_rows_preserved=true、test_feedback_imported=0、feedback_schema=1、三张反馈业务表数量为0；账号/车库/投稿与贡献数量、成绩版本、活动文件哈希、score_writes均保持。记录backup路径。失败保留现场，不重复旧迁移、不初始化数据目录。

### 6. 激活、启动与四项核对

使用本次上传目录的deploy_production.py --version NEW_ID --activate，再systemctl start racepick-accounts。核对current、新进程cwd均指向NEW_ID，服务active/running，公网health正常。

期望health为production、schema6、community_schema1、contribution_schema1、contributions=true、feedback_schema1、feedback=true，成绩版本与写回开关保持。第一次502可在启动阶段短暂出现，必须以重试成功及实际进程检查为准。

### 7. 新版备份、演练与恢复定时器

从新current生成成套备份，使用新版verify-backup及restore-drill校验。演练结果应同时包含contribution_schema/counts、feedback_schema/counts和active_database_replaced=false。完整SQLite包含反馈原文、回复及幂等记录，不能单独恢复SQLite。

通过后systemctl start racepick-backup.timer，核对enabled、active(waiting)和明确NEXT。再核对网站active、公网health；不能把timer enabled误认为正在运行，不能把未来计划当成实际执行成功。

### 8. 公网功能验收

站长查看既有昵称和匿名状态、按邮箱或昵称搜索；检查返回/导航按钮及原功能。玩家从个人中心提交必要的真实反馈，站长回复并改变状态，玩家能看到自己的回复记录。普通管理员不能查看全部反馈。原成绩和积分不因反馈操作变化。不要导入本地测试反馈或发布模拟成绩。

## 回退与异常边界

迁移前失败：保留旧应用和数据，先处理暂存或依赖问题。若尚未迁移且已经停服，按现场状态恢复原服务及timer。

迁移后不能直接切回不支持反馈schema的旧程序。新激活工具检查兼容标记与必要组件并阻断旧版；不得用旧部署工具或手工ln绕过。优先修复兼容新schema的程序，不自动删除反馈表。

不提供单SQLite恢复或一键覆盖活动库。灾难恢复须保留当前完整现场、独立目录演练并另行确认整套恢复范围，避免丢失备份后的账号、成绩、贡献或反馈。

## 验证边界

Windows临时库验证只读预检、事务迁移保留、幂等、版本漂移/未完成批次/部分表拒绝、生产HTTP反馈及完整备份恢复、兼容激活与包白名单。Windows使用服务锁替身；Linux真实锁与Python3.12离线依赖必须由服务器暂存安装脚本验证。本地准备完成不等于上线完成。

本轮实测：后端132项通过；根目录62项执行61通过、1项原有Linux专用检查跳过；JS63项通过；页面启动、生产入口临时库HTTP冒烟、语法和Git空白检查通过。包解压验证与交付哈希校验另行在生成后执行。服务器实际安装、迁移及公网验收尚未执行。

## 2026-10-22 公网上线验收完成

本节覆盖上文准备期状态。证据来自用户服务器完整回传及明确的“公网验收通过，功能均正常”反馈，不是代理独立登录服务器的结论。本次收尾只更新文档并推送release/account-feedback-production，不访问或修改生产环境、不重启、不重复迁移、不重新打包、不合并main。

### 发布与运行

- 应用ID：`4a28f6d76b9d3e93d3227120`；打包源码 `b17d6fcfe1c831b3f7fbb2b4923ea0a9efb33168`，数据基线 `73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee`。文档后续提交不改变已部署发布包。
- 上传目录：`/root/racepick-deploy/20261022-feedback-4a28f6d7`。用户简述确认10文件上传、9文件校验全部OK、暂存成功、离线安装和临时数据库原生自检通过，未提供这些步骤的完整原始日志。
- 激活完整输出确认current及实际进程cwd均为 `/opt/racepick/releases/4a28f6d76b9d3e93d3227120`，当时MainPID=132627，服务active/running。首个公网请求502，重试得到健康JSON，最终服务正常。
- 最后完整health：status=ok、mode=production、schema6、community_schema1、contribution_schema1、contributions=true、feedback_schema1、feedback=true；成绩版本 `42d62fde9b81197ac0558087a9a25f97`，score_writes=true。
- 用户确认账号昵称展示/搜索、按钮统一和文字反馈公网验收通过，功能均正常。未获取真实反馈正文或逐条处理回执，不编造或公开这些内容。

### 预检、迁移与备份演练

预检完整输出：feedback_schema=0、contribution_schema=1、pending_batches=0，27个账号/15份车库/2条投稿；contributions、contribution_sources、contribution_events均0，contribution_preferences=1。数量是当时快照，不强制修回。活动cars.json哈希469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c；成绩文件哈希bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9。

旧版在线成套备份与演练有完整回传：

- `/var/lib/racepick/backups/scores-20261022T134206474628Z.zip`，153533字节，racepick:racepick，600权限，清单校验通过。
- 演练目录 `/var/lib/racepick/restore-drills/6ed23e688a30ec2f6f7418fd`；版本42d62fde…、counts27/15/2、贡献schema及数量与预检一致，pending_batches=0、active_database_replaced=false；网站及timer当时保持active。

用户随后简述确认网站和timer暂停、停服最终成套备份生成并校验通过，成绩不变；反馈迁移返回feedback_schema=1、existing_rows_preserved=true、test_feedback_imported=0，成绩版本和写回开关保持。没有提供这两步的完整输出，故不填写停服最终备份或迁移保护备份的具体文件名，也不将迁移时账号数量写成重新核实的值。

切换后用户简述确认新版备份和独立恢复演练通过，feedback_schema=1、contribution_schema=1、active_database_replaced=false，网站健康正常。没有提供新版ZIP路径、演练目录或反馈表数量，不补造；将来需要精确恢复点时，现场只读核对备份清单。

账号、昵称、贡献、成绩及备份沿用原持久化目录，没有导入本地模拟反馈、覆盖服务器成绩或改动工作簿，没有重跑旧贡献或成绩分离迁移。

### 定时备份恢复

完整输出确认timer于 **2026-10-22 21:46:12 CST** 恢复，enabled、active(waiting)，NEXT为 **2026-10-23 04:15:58 CST**，覆盖上一轮04:19:44的计划时间。

LAST仍为2026-10-22 04:18:37；确认的是调度恢复，不是新版首次定时执行已成功。最后网站active、反馈和贡献功能启用、成绩版本及写回开关不变。后续按需核验实际执行，不自行新增监控任务。

### 本轮收尾边界

新版本4a28f6d…、上一版本1fcc18c…及上传包保留，本轮不继续清理任何旧目录或备份。反馈schema1后不能直接切回不兼容旧代码，不用旧部署脚本或手工链接绕过检查，不单独恢复SQLite。

原8010/8009和测试数据保留。本轮只更新文档并推送release/account-feedback-production，main未合并；后续先fetch核对分支，再按新任务核对生产状态，不能把源码同步当成部署。
