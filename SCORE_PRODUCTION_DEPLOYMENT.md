# 正式成绩版本化：分阶段生产准备

2026-10-21：用户已确认独立测试环境功能验收完成；生产适配在feature/score-versions-local准备，尚未迁移服务器、开启生产写回或合入main。现有账号、密码、车库、投稿及工作簿保留。本说明替代旧部署说明中关于“成绩始终从代码包读取”和“仅SQLite备份”的对应步骤，仅在本次迁移后生效。

## 已核对服务器基线

- 当前应用09897d5f81a696dca0b95c8e，服务active，health ok/production/schema6。
- 成绩JSON SHA256：c7d77a60ced1c2e6eb577e7c3de1577f94de4d94b097f2be9de23d273b58e1a8。
- cars.json SHA256：469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c。
- 两个哈希与该发布包清单完全一致；不将Windows工作区换行导致的文件哈希差异误判为车辆规则变化。
- 用户回传首次自动备份于2026-10-21 04:18:40 CST成功，文件accounts-20261020T201840460915Z.sqlite3，176K、600权限。下次计划2026-10-22 04:15:47 CST。证据来自用户服务器输出。

## 架构与开关

迁移后账号数据库仍在/var/lib/racepick/accounts.sqlite3。新成绩目录是/var/lib/racepick/score-state，版本文件位于scores/versions；源码发布目录不修改。数据版本指针、审批回执及状态在账号SQLite中同事务提交。

新增score_control把成绩目录与账号库绑定，并保存写回开关。迁移默认关闭；停服CLI明确enable后才允许超级管理员生成/执行/回滚批次。恢复未完成批次仍需超级管理员近期密码确认。只读阶段网站、账号和投稿审核正常，health附带score_version和score_writes=false。

前台通过一次snapshot读取成绩和规则，审核也读取当前版本。部署新代码不再以包内JSON覆盖活动成绩。规则本轮固定，未开放车辆/星级规则编辑。每项更慢成绩需要写回阶段再次确认及原因；评分与采纳不会自动发布。

## 操作顺序：每阶段检查后再继续

### 1. 上传、暂存、安装新版本（网站继续运行）

上传新交付目录全部6文件，进入该目录，先sha256sum -c SHA256SUMS.txt，再python3 deploy_production.py --bundle racepick-accounts-release.zip。记录返回的新ID，此时不加--activate。

进入/opt/racepick/releases/NEW_ID执行bash production/install-runtime.sh。NEW_ID必须替换为真实输出。安装脚本使用临时数据库，在Linux上检查迁移、持久化读取、开关、成套备份、恢复演练及服务锁；不会访问正式账号库或发送邮件。不要运行configure.py或production init。

### 2. 在线只读预检

从新版本目录执行（必须cd到新版本，避免导入旧模块）：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.score_production preflight \
  --source /opt/racepick/releases/09897d5f81a696dca0b95c8e \
  --expected-data c7d77a60ced1c2e6eb577e7c3de1577f94de4d94b097f2be9de23d273b58e1a8 \
  --expected-cars 469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c
```

核对来源哈希、数据库完整性及users/profiles/submissions计数。只显示数量，不输出邮箱、密码或链接；不新增成绩目录，不改数据库。如果正式数据已变，停止并重新核对基线，不跳过哈希检查。

### 3. 停服备份与迁移（短暂维护窗口）

先运行现有racepick-backup.service并确认成功。暂停racepick-backup.timer，确认一次性备份任务已结束，再停止racepick-accounts。避免旧版本备份进程与迁移同时操作。

仍在新版本目录执行：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.score_production migrate \
  --source /opt/racepick/releases/09897d5f81a696dca0b95c8e \
  --expected-data c7d77a60ced1c2e6eb577e7c3de1577f94de4d94b097f2be9de23d273b58e1a8 \
  --expected-cars 469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c
```

工具取得服务独占锁，先备份原账号库，从已确认源文件生成完整初始版本，再事务添加元数据。原有业务表逐行指纹必须保持一致。核对existing_rows_preserved=true、write_enabled=false、新数据版本和备份路径。中断时保留现场；完整文件已落位而数据库事务未完成的迁移可在同一基线下重试；未完成临时目录不作为活动来源。

### 4. 激活新应用并验证只读阶段

用新交付目录的deploy_production.py --version NEW_ID --activate，再启动racepick-accounts。不改Nginx、证书、SMTP凭据或账号配置。新激活工具会检查当前数据格式与目标应用兼容性，禁止迁移后直接切回旧的非版本化程序。

核对服务active、监听仍为127.0.0.1:8001，公网health为production/schema6，score_version与迁移结果一致、score_writes=false。核对网站成绩、车库、登录、投稿审核和超级管理员入口；正式成绩页显示只读，发布接口应拒绝写操作。迁移后的公开JSON内容与原版本完全相同。

### 5. 成套备份与演练

现有backup定时服务不需要更换命令：新backend.production backup检测版本化状态后自动生成成套zip，包含一致性SQLite副本、所有完整数据版本、批次备份/回执所需材料、生产绑定标记及哈希清单。不会包含SMTP密码。复制账号数据库和读取版本集合共用成绩维护锁；备份使用流式读写，避免一次把全部历史载入内存。

手动运行racepick-backup.service并确认成功。用输出的实际zip路径执行：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.score_production verify-backup --backup /var/lib/racepick/backups/实际文件.zip
runuser -u racepick -- .venv/bin/python -B -m backend.score_production restore-drill --backup /var/lib/racepick/backups/实际文件.zip
```

演练只解压到新建的/var/lib/racepick/restore-drills/随机目录，检查哈希、SQLite完整性/外键、账号绑定和全部批次引用的数据版本，不覆盖活动数据库。核对active_database_replaced=false、版本与用户/车库/投稿数量。演练成功后恢复启用racepick-backup.timer并核对下次时间。备份及演练目录不自动删除，定期检查磁盘占用。

### 6. 明确启用生产写回，验证一条真实成绩

只读阶段和成套恢复演练通过后，短暂停止账号服务，从当前新版本目录执行backend.score_production enable，再启动服务。health应显示score_writes=true。此步骤单独进行，不与迁移或发布包激活合并。

由主号选择一条真实、已核对的投稿，输入当前密码验证身份，逐项确认、对更慢项再次确认并填写原因，核对普通镜像后发布。检查新数据版本、前台成绩及回执；不得使用模拟成绩在生产验收。不要为验收而无故回滚真实成绩。

## 暂停写回、回退与恢复边界

- 暂停新写回：停服后运行backend.score_production disable并启动，当前成绩仍从持久化版本读取，不回退旧JSON。
- 撤销刚完成的迁移：仅当开关关闭、当前为初始数据版本、没有任何发布批次/回执时，允许停服运行revert-migration --source 原应用目录。工具先做成套备份，仅移除成绩版本元数据表，保留所有现有账号业务行，并将成绩目录改名保留。之后才可使用新激活工具切回原应用。过程有日志，中断可重试；不自动删除成绩目录或恢复旧账号备份。
- 开启并产生批次后：禁止撤销迁移或激活不支持当前数据格式的旧应用。成绩回滚只处理当前批次；有后续数据版本时需新的反向变更，不覆盖后来更新。
- 版本化后禁止用旧restore命令只恢复一个SQLite文件，否则可能丢失或错配成绩指针。完整灾难恢复须先在新目录演练、停服并留存当前全套数据，再由运维核对后整体恢复；本工具不提供自动覆盖活动数据目录的命令。恢复会影响备份之后的账号/投稿，不能作为日常成绩回滚使用。
- 本轮未实现本地工作簿三方合并、Excel批量导入、Git自动同步。后续代码发布不会自动带入本地JSON编辑；正式成绩需要明确发布批次，不能重新依赖代码包覆盖。

## 验证与状态

本地使用临时生产配置和数据库测试迁移保留账号、只读默认值、哈希不符拒绝、启用后发布、成套备份/演练、绑定异常拒绝、禁止单SQLite恢复及只读阶段撤销迁移。Linux服务锁和迁移演练由随包selfcheck在服务器暂存阶段实际运行。服务器尚未执行本次迁移、开启写回或验收新服务；该文档不表示已经上线。

本轮本地完整回归159项执行：158通过、1项Linux专用跳过；JS53项、启动冒烟、语法与空白检查通过。CLI预检/迁移还要求source与当前/opt/racepick/current一致，防止使用已经过时的应用目录作为迁移来源。尚未在实际服务器执行新包的原生迁移检查。

打包补充：正式JSON取自已提交Git对象，避免Windows检出换行改变服务器基线；新增对应测试通过。累计Python159项通过、1项跳过，打包相关5项复核通过。交付目录包含两份部署说明，共7个文件。

最终整合：准备期间main新增2b1196a（单图前三折叠参考），已正常同步到本功能分支，未修改main。补跑包含该功能的JS回归59项全部通过，页面启动冒烟与生产入口临时库冒烟通过；后端未因这次主线同步改变，沿用此前回归结果。发布使用最终整合包，早期v1试构建包不用于本次部署。

## 2026-10-22 用户回传进展（覆盖上文准备期状态）

用户已切换生产应用到 `7a0f2927404cab20f0a5a020`，健康检查 score_version=`c8889ff96eb29714d80248cca283b9fa`。迁移保留 7 个账号、7 份车库、0 条投稿，初始写回关闭；成套 scores ZIP 校验和独立目录恢复演练通过，active_database_replaced=false。用户确认网站功能正常、定时器恢复后，随后确认开启写回成功。本轮只据回传更新记录，没有访问或改动线上数据库；尚无实际正式成绩发布批次的验收证据。新的公告/账号管理/手动车库功能见 COMMUNITY_LOCAL.md，仍未上线。
