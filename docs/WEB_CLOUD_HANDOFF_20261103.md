# 网站发布准备交接：2026-11-03

本轮仅完成本地开发、分功能推送、冻结核验、独立干净构包及隔离验证。没有访问或操作生产、迁移正式库、修改微信后台、上传/提审小程序或上线。请云端部署对话接手；**先给用户当前一步只读命令，用户执行回传后再逐步推进**，不要把本文件当作批量执行脚本。

## 固定来源与范围

发布源码 `765a4a62567c97a9a2d4f48cf3a8955e3e8cd715`（覆盖旧777b30a包），分支 `feature/map-layout-parser`，独立干净检出 `build-web-code-20261103`。最终网站发布ID `a933c9b746c2e276a9b68d14`；旧730a61cd包已被本次包含维护正式发布的交付取代。后续交接文档提交不改变包内源码。main未合并，小程序树未改；逐功能提交与远端回执见随包 `SOURCE_PUSHES.json`。

维护侧 `DATA_FREEZE_20261103.json` SHA256 `940f8660585c495a780390b709dfd52e80f7610f57e0179c5da937c53c4e4282`，freeze_id=`b57d97a8f4e484be69238ab0`；原冻结ZIP SHA256 `feddf28ce165da510a30936a1efe083b6d3725c3b4b43a7fc781b196957cb9d0`。数据提交为 **null**，没有代维护侧提交。ZIP内34项的大小/SHA/CRC、内外清单及五份runtime原字节均已核对；仅五份runtime入包。

本次正式维护发布目标CN4516键/83图，Global694条/48车/44图/21OC/52SC，dataset=`9b83ddd062a4d4b0c15d51dc0eed323aabb8e599e3e9544bc91714b70a7a4259`。完整维护733、36参考、工作簿、台账、测试状态、账号库和私有截图不入交付。cc850两区共同min3/四区max3、fxxk进入国际运行池来自批准维护冻结，不是功能侧推断。

网站功能包括保留原页面/特殊跑法按钮和成绩表“新功能”、截图五图中文名说明及截图选择限制、共享核心、国际服账号云车库、OC成绩展示及DOM无关主页presenter。原生会话/账号/OCR及B–E协议源码随包，**网站上线仍关闭原生入口**：不设置 `RACEPICK_MINI_CONFIG`、AppSecret或原生账号开关，不创建原生状态目录，不开放Nginx原生上传；B–E生产写受硬门禁禁止。真实微信身份/平台审核/图片内容安全服务没有因此完成。

## 已上线、本地通过与待验收

历史最新运维证据在主树 `repo/docs/CLOUD_HANDOFF.md` 文首及 `MAP_OCR_DEPLOYMENT_RECEIPT_20261031.json`：10月31日c06cc48b已由用户验收，主schema6、coverage2、global-score1；CN活动版本e209f3e32d0de1dfa7fe6c811a5d5c46，Global1252565e65bc887e81e0c677bfeec9ab/659，国际写关闭。**这些是历史值，不是本轮生产现场核验。** 功能树旧CLOUD_HANDOFF不得覆盖主树新运维记录。

本轮冻结数据的具体测试数、Linux真实CPU OCR/配额/取消/硬超时/备份演练及耗时峰值以随包 `VALIDATION.json` 和 `native-integration-receipt.json` 为准。此前失败尝试保存在本地验证目录，不包装为通过。Linux容器是隔离非root进程+真实Nginx/API/OCR，未运行正式systemd；单元只做语法验证。Windows测试、fixture微信身份均不能替代真机或真实平台验收。

网站真实账号CN/国际云车库、OC保存/冲突/切账号，以及桌面和手机微信识图/相册仍待上线后用户验收。浏览器文件选择菜单最终由操作系统/浏览器决定；扩展名accept与无capture用于引导已有截图，不能保证所有移动浏览器绝不显示系统拍照入口。

## 云端逐步执行顺序

1. 先只读。用户上传完整交付并校验整包SHA后，给出 `bash 01-readonly-preflight.sh`；脚本不输出私有配置/账号内容/令牌。核对current、两个PID真实cwd、health/schema/双服活动版本/写开关、资源/磁盘、Nginx精确上传门禁及timer。另核最近一次实际备份文件SHA/完整性/执行结果，不把NEXT当已成功。若现场不同，停在只读核对，不照抄历史路径/PID。
2. 按 `SHA256SUMS.txt` 全量验证。用随包 `deploy_production.py --bundle racepick-accounts-release.zip` 仅暂存；核对返回目录ID。进入该新目录执行 `bash production/install-runtime.sh`，离线37wheel、pip check、临时数据库/锁/备份恢复和合成OCR自检通过。该安装不是正式初始化/迁移。不要运行 `backend.production init`、旧迁移或provision；不要覆盖全站Nginx/systemd/SMTP配置。
3. 从当前运行版本做在线成套备份，`backend.score_production verify-backup` 后独立 `restore-drill`，参数使用现场私有配置和实际备份路径。保留SHA/文件数/版本/计数和 `active_database_replaced=false`。新源码同样应先验证它能读取该备份；不能复制测试库或用包JSON覆盖正式score-state。
4. 迁移与短维护窗口需用户明确确认。暂停备份timer并等待既有备份完成；先停止网站接新请求，等OCR queued/running清零，再停止唯一OCR单元。保留图片/结果/元数据和独立队列目录，不重新provision或删队列。生成并验证停服最终备份、独立恢复；核对业务行/双服活动版本及开关未漂移。
5. **账号组件新增迁移**是 `global_profile_schema 0→1`。新目录使用 `.venv/bin/python -B -m backend.global_profiles migrate-production --config <现场私有配置路径>`。源码持有服务锁并先备份，只创建空国际车库组件；须得到 `existing_rows_preserved=true`、profiles_global=0，或完整既有schema1的幂等回执。异常即停、保全现场，不清表或整库还原。不要重跑主schema6/coverage2/global-score1或初始化国际成绩。迁移后再做新版成套备份与独立恢复。
5a. 本次必须一并发布维护数据。完整读取MAINTENANCE_RELEASE_20261103.md，以新包的backend.maintenance_release先对现场只读preview；核对所有新增/删除/变慢/规则变化，不只核19/2项本轮新增。批准摘要绑定现场双服base/五文件SHA/开关/源码冻结。停服最终备份与独立恢复及global-profile迁移完成后，以原账号库owner运行apply，保持服务锁/双服锁，原子创建两服新版本并切换指针。确认目标五文件精确等于批准冻结、CN4516/Global694、cc850规则及国际fxxk入池，原业务行和写开关保持。中断用status恢复；不得手改指针、覆盖JSON或重跑初始化。
6. 用随包激活工具 `--version a933c9b746c2e276a9b68d14 --activate`，仅在前述证据通过且用户批准切换后执行。保留原Nginx、账号/SMTP/成绩开关和OCR路径沙箱。先启动唯一OCR单元，再启动网站；health ready、current与两个实际cwd一致。**生产历史OCR High640MiB/Max768MiB/CPU100%/Swap0/Tasks64**，模板可能为768MiB/1GiB，不能盲覆；现场值需先核。新原生模板路由不因网站发布而开放。已有精确网页OCR8MiB、默认3MiB、业务及统计限流/TLS/可信IP保持。
7. 逐项检查health主6/coverage2/global-score1/global-profile1、双服活动版本等于维护apply回执的两个target，五文件SHA等于批准冻结；写开关与部署前相同，未创建测试用户/投稿/反馈。本次上线验收必须证明CN4516/Global694及新规则已经实际活动，不能只依据包内有这些文件就宣布数据已更新。若现场含未批准覆盖的后续成绩，停在计划核对阶段，不默默删除。
8. 用户验收真实账号登录、国服云车库保持、国际车库显式游客导入/保存/读取/OC、409保留两份、两服草稿和登出/切账号隔离；失败GET不覆盖本机。桌面/手机微信核五图中文名说明、相册入口、五槽核对/替图取消/识图/计算/手选、特殊跑法按钮、成绩表“新功能”、OC/SC筛选和方案次序。无真实权益账号的权限档位记待验收，不造积分。
9. 新版成套备份、全量校验及独立恢复通过，保留profiles_global/OC与原业务计数；手动触发真实备份服务并核成功退出及实际新备份，恢复timer并记NEXT。后续自动执行尚未发生就记待验证。保留旧包/旧release/备份/演练，不清理、不发公告、不新增监控。

上述涉及正式停服、迁移、切换、生产写入的步骤仅交接准备，当前对话没有执行；云端不得一次提供整段写脚本让用户盲跑。

## 回退与故障停止

启用global-profile1后旧c06及旧激活工具不兼容，不能为了回退代码恢复旧账号库或强行改capability。保留新增国际车库及全部当前业务状态；整套灾难恢复另获授权，并先保存新增数据。

随包另附 `compat/` 的schema1兼容候选，源码 `a38faaf4c7fa05f853b89ae2db31708ec2f8b52d`，使用**同一新冻结**，发布ID和校验见 `COMPAT.json`。它保留国际云车库，去掉后续B–E/presenter/OC表及最新截图文案。它不能读取本次新规则，必须先按MAINTENANCE_RELEASE的严格双服target/CAS条件完成定点数据回退（不恢复SQLite、不丢账号/车库），确认旧规则可读后才可能使用；新维护版本仍applied时，新激活工具明确拒绝该候选。它与主包共用云车库实现，**不能当作修复云车库缺陷的保障**；其安装自检验证范围见VALIDATION。切换仍须停服保留状态、始终使用本轮新激活工具并重新核对所有版本。若云车库/schema/数据一致性失败，保持维护并保全现场，不强切旧c06。

## 交回记录

云端执行后追加独立部署回执：实际包SHA/current/源码、迁移前后组件/计数/逐表保持、双服活动版本和开关、所有恢复点SHA/演练目录、实际资源限制、PID/cwd/ready、真实用户验收、备份执行及timer、未完成项。不要覆盖本轮维护冻结或其他对话dirty文件。小程序原生上线另行授权，不因网站包携带源码自动开放。
