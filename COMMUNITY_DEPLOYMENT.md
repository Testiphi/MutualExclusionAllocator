# 公告、账号管理、手动车库升级

目标：升级代码并新增 community_schema=1；保留现有账号、车库、投稿、公告以外业务数据及服务器当前成绩版本。不要重新初始化数据库，不上传本地账号库或工作簿。本地完整验收已由用户确认。生产上线验收已完成；以下保留部署流程，实际结果见文末。

## 发布顺序

1. 在线收集 current、健康状态、定时器和备份状态。不能以历史成绩版本代替当前状态，线上可能已有新成绩发布。
2. 上传本目录全部文件，sha256sum -c SHA256SUMS.txt，使用 deploy_production.py --bundle racepick-accounts-release.zip 仅暂存。进入新版本目录运行 bash production/install-runtime.sh；仅临时库冒烟。
3. 使用仍在运行的旧代码先生成 scores 成套备份，并 verify-backup/restore-drill。记录备份路径、版本、账号/车库/投稿数量及当前写回开关。
4. 进入维护窗口：停止 racepick-backup.timer 和 racepick-accounts；等待可能正在运行的备份服务完成。使用旧版本再生成一份停服成套备份并验证，保存路径。停止网站服务期间可能短暂返回 502。
5. 从新版本运行：runuser -u racepick -- .venv/bin/python -B -m backend.community --config /etc/racepick/production.json。无需 SMTP 密码；服务锁防止活动服务并发，先备份 SQLite 再事务迁移附属表，不改变账号原表或成绩指针。
6. 用本包 deploy_production.py --version RELEASE_ID --activate 切换；systemctl start racepick-accounts。无需修改 Nginx、SMTP、systemd unit 或初始化账号。
7. 检查服务 active、127.0.0.1:8001、公网 health；score_version 与迁移前一致、score_writes 与原开关一致、账号/车库/投稿数量一致。验证超级管理员、管理接口权限、手动车库与已有成绩。
8. 生成新版成套备份，校验并独立目录恢复演练，然后恢复 racepick-backup.timer。发布正式公告由站长在网站新建，不从本地导入演示公告。

## 回退边界

迁移失败时事务回滚；保留原代码 current，不反复初始化。迁移成功后新服务异常：先停服务、保留失败时的成套现场，诊断或修补支持 community_schema=1 的代码。不能直接切回旧版，否则停用权限可能被绕过；本包激活工具会阻止不兼容回退。旧部署工具或手工 ln 不能用来绕过检查。

如果仅在停服升级窗口内，确认尚未恢复任何线上写入，可针对停服成套备份规划完整恢复；必须同时核对账号库、成绩状态与配置，不能只拿迁移前 SQLite 覆盖现有库。恢复前先独立目录演练，不提供一键覆盖生产命令。恢复业务后不可用旧库回退吞掉新增账号或投稿。

## 发布包的数据边界

包内 JSON 仅为固定代码基线及临时冒烟输入；生产已有 score-state 时继续使用服务器独立成绩目录，切换代码不会把包内 JSON 覆盖进正式成绩版本。不得运行旧分离迁移或以代码包 JSON 重新初始化。

## 2026-10-22 上线验收完成

证据来自用户回传的服务器输出及明确的验收完成反馈；本次文档更新不连接或修改生产环境。

- 应用发布版本 `651ea3d88a27bdff95088b75`，包源码 `880333d`；用户最终确认 current 链接和服务实际工作目录均指向该版本，服务 active，公网健康检查正常。
- 核心 schema=6，community_schema=1。迁移后核对 users/profiles/submissions 为 7/7/0；这是当时基线，不代表未来数量固定。旧账号、车库、投稿保留。
- 成绩版本保持 `c8889ff96eb29714d80248cca283b9fa`，score_writes=true；本次代码升级未发布新的成绩版本，也未修改本地工作簿。
- 用户确认公告、账号管理、手动车库保存上线验收通过；已有登录、车库星级、成绩及计算正常。对应完整本地验收包括三个公告提醒选项与恢复、停用/恢复/强制退出及主号保护、临时车库与已保存资料隔离、显式保存、多窗口冲突和角色权限隔离。
- 新版本成套备份及独立目录恢复演练成功，active_database_replaced=false，定时备份已恢复，服务与健康检查仍正常。用户未提供新版备份具体文件名，故不补造路径；旧版在线备份为 `scores-20261022T002419086391Z.zip`，停服最终备份为 `scores-20261022T002503031601Z.zip`，均在 `/var/lib/racepick/backups/`。

切换过程中曾出现无输出：版本断言返回1，current当时仍为旧版且服务停用，公网502；该次备份未执行。之后重新激活并核对实际进程目录，用户确认新版本运行后才重新备份演练并恢复定时器。不能用终端所在目录代替current与进程目录验证。

## 2026-10-22 PHP 漏洞排查

针对 CVE-2026-109618 / CVE-2026-109619（PHP2Shell）进行服务器只读排查。公告参考：[PHP官方公告](https://www.php.net/archive/2026.php#2026-10-21-5)、[Ubuntu官方说明](https://ubuntu.com/blog/php2shell-vulnerability-fixes-available)。本节记录当次排查，不代表持续监测或全面安全审计。

用户输出显示：
- 软件包查询的 apache2、php-crypt-gpg 状态都是 not-installed。原过滤 `grep installed` 会误匹配 not-installed，不可据此认为已安装。
- 进程匹配仅有查询用 grep 本身，没有发现 PHP/Apache 服务。
- Nginx 中 PHP/FastCGI 示例均被 # 注释；RacePick 实际反向代理至 127.0.0.1:8001 的 Python 服务。
- Docker检查没有输出，没有发现运行容器；不能单独据此断言 Docker 未安装。

结论：在已检查的软件包、进程和Nginx配置中，没有发现此次PHP漏洞的活动攻击入口；RacePick的Python架构不直接使用PHP，因此未因本漏洞停服、安装PHP或修改配置。手工安装的其他运行环境/面板尚未被完整盘点；若另有PHP服务仍须单独检查，不能将本结论等同于整台服务器绝对安全。

## 2026-10-22 PR 合并完成与交接

用户已通过 [PR #2](https://github.com/Testiphi/MutualExclusionAllocator/pull/2) 将功能分支合入 main。本轮 git fetch 后核验 origin/main=`fdc3a43`，合并提交包含 `b3798ca`（Git祖先检查通过）。该合并同时包含此前成绩版本功能基线。

源码合并不改变生产部署，最近用户确认的线上应用仍为 `651ea3d88a27bdff95088b75`（打包源码880333d）。本轮只更新文档，没有执行服务器命令、重新打包或重启服务。

主工作目录 repo 的本地 main 仍为2b1196a，保留未跟踪的 gauntlet_data_shared.xlsx 与 _star_curve_fit.py，未切换/拉取该工作目录；账号库和工作簿均未操作。文档在 community-controls 工作目录的新分支 docs/cloud-handoff-20261022 上更新，基于远端合并后的main。后续模型从 [CLOUD_HANDOFF.md](CLOUD_HANDOFF.md) 开始。
