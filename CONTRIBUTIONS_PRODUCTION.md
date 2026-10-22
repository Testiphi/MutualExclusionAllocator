# 贡献排行榜与主页导航生产升级

2026-10-22：排行榜、公开昵称与主页导航已通过用户本地验收。本轮在独立release/contribution-production目录准备生产适配，整合功能0938886与main数据73e3f8b，保留8009原验收环境，不合并main。尚未操作服务器。

## 范围与数据保护

新增质量0–10＋正式采用10分、总榜/月榜、个人明细、公开昵称/匿名，以及个人中心、数据贡献、管理工作台导航。原账号、车库、公告、投稿审核和成绩发布功能保留，擂台表解锁不在范围。

停服后仅显式新增5张贡献附属表。所有历史投稿不登记资格，不转换旧0–5评分；从新规则启用后的新建投稿开始计分。迁移核对所有既有业务表逐行指纹，保持活动成绩版本和写回开关。存在未完成成绩执行/回滚批次时拒绝迁移。

继续使用/var/lib/racepick/accounts.sqlite3和score-state。包内JSON仅用于基线及临时库冒烟，绝不覆盖服务器成绩。不改Nginx、SMTP、证书、配置或systemd定义；不运行configure/init，不重跑分离成绩或community迁移。工作簿不操作。

## 历史基线须现场核验

最后用户回传应用651ea3d88a27bdff95088b75，current与进程cwd一致、服务active，schema6/community1；成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true，包含肥龙★6四区高手34.90及普通镜像。服务器可能已有新发布，不能强行恢复历史版本。

备份timer曾于08:25停止，用户10:41恢复为active(waiting)，当时NEXT为2026-10-23 04:18:17 CST。本轮重新核对，不依据旧记录假定调度仍在运行。

## 交付内容

新目录共9文件：racepick-accounts-release.zip、deploy_production.py、production_release_tools.py、PRODUCTION_DEPLOYMENT.md、SCORE_PRODUCTION_DEPLOYMENT.md、COMMUNITY_DEPLOYMENT.md、CONTRIBUTIONS_PRODUCTION.md、RELEASE.json、SHA256SUMS.txt。后三份历史部署说明中的首次初始化/迁移步骤不重跑，本次顺序以本文为准。

RELEASE.json绑定代码/数据提交及内容哈希。离线wheels复用已验收Ubuntu24.04 x86_64 / Python3.12锁定依赖。包内不含账号库、登录资料、工作簿、日志、截图、演示脚本或实验室。

## 逐步执行，每步回传后继续

### 1. 只读检查

核对current、racepick-accounts状态、MainPID实际/proc/cwd和公网/api/health，记录当前score_version和score_writes。检查backup.timer的enabled/active/NEXT、最近backup.service结果及ZIP时间、磁盘空间。此时不停止服务、不启动备份。

### 2. 上传、校验、暂存和临时库自检

上传全部9文件到本次新的交付目录。执行sha256sum -c SHA256SUMS.txt，应显示8个文件OK（清单不校验自身）。执行python3 deploy_production.py --bundle racepick-accounts-release.zip，只暂存，不加activate。

记录真实NEW_ID，进入/opt/racepick/releases/NEW_ID，运行bash production/install-runtime.sh。脚本离线安装、核对依赖并以临时库验证账号、成绩迁移、贡献迁移、Linux服务锁、页面资源及成套备份/演练，不发邮件或操作正式库。失败先停在此步，禁止重复覆盖已有venv。

### 3. 新版本在线只读预检

仍在新版本目录执行：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.contribution_production preflight
```

核对score_version与当前health一致、score_writes保持、pending_batches=0、contribution_schema=0、账号/车库/投稿数量及活动JSON哈希。schema已为1时先核对操作记录，不重建或清零。输出仅数量和指纹，不输出身份或密码。

### 4. 旧版成套备份及维护窗口

从仍在运行的真实旧版本目录执行backend.production backup，记录实际ZIP；用旧版backend.score_production verify-backup和restore-drill验证完整恢复。通过后暂停racepick-backup.timer，确认可能正在运行的backup.service已结束，再停止racepick-accounts。

停服后仍使用旧版本再生成最终成套备份并校验。不能仅保存SQLite。后续迁移还会额外生成事务前成套备份。此阶段可能短暂502，不要混淆终端目录与current。

### 5. 显式迁移贡献表

进入新版本目录，把EXPECTED_VERSION替换为刚核验的实际活动成绩版本：

```bash
runuser -u racepick -- .venv/bin/python -B -m backend.contribution_production migrate --expected-version EXPECTED_VERSION
```

要求existing_rows_preserved=true、historical_submissions_enrolled=0、contribution_schema=1；四张业务贡献表数量均0；活动成绩、写回开关、原业务数量不变。记录backup路径。工具持有服务独占锁及成绩维护锁；版本漂移、未完成批次会拒绝。事务失败不留下部分表；成功后的同版本重试返回already_migrated=true，不再次初始化。

### 6. 激活并核对实际运行版本

用本次交付目录deploy_production.py --version NEW_ID --activate切换，再systemctl start racepick-accounts。

```bash
readlink -f /opt/racepick/current
systemctl show racepick-accounts -p ActiveState -p SubState -p MainPID -p WorkingDirectory
racepick_pid="$(systemctl show racepick-accounts -p MainPID --value)"
if [ "${racepick_pid:-0}" -gt 0 ]; then readlink -f "/proc/$racepick_pid/cwd"; fi
curl --fail --silent --show-error --max-time 20 https://racepick.cn/api/health
printf '\n'
```

current和进程cwd均为新ID，服务active/running；health应为production/schema6/community_schema1/contribution_schema1/contributions=true。score_version和score_writes保持迁移前值。生产启动只读取已迁移规则，不自动迁移。

### 7. 新版备份、恢复演练与定时器

运行racepick-backup.service并核对退出成功，记录新版ZIP实际路径。从新current目录用新版backend.score_production verify-backup和restore-drill验证；输出应含contribution_schema=1、贡献表数量、版本和原业务数量、active_database_replaced=false。完整SQLite已包含昵称和贡献记录。

通过后systemctl start racepick-backup.timer，确认enabled、active(waiting)及明确NEXT；再核对网站服务及公网健康。一次性backup.service成功后inactive正常，timer本身必须active(waiting)。

### 8. 用户公网验收

核对原账号登录、车库和计算；三类导航可用、玩家不显示管理入口；榜单初始不纳入历史投稿、公开接口不暴露邮箱，昵称/匿名可保存。质量分与采用奖励仅用后续真实投稿验证，不为验收发布模拟成绩。历史投稿仍可正常处理但不获得贡献奖励。

## 失败处理与回退边界

迁移前失败：保留原版本和数据，排查暂存/依赖；尚未迁移且已停服时，可按实际检查恢复原服务和timer。

迁移后禁止切回不能记录贡献的旧代码，否则会漏记新投稿。新激活工具检查contribution_schema和必要组件并阻止旧版回退，不能用旧部署工具或手工ln绕过。优先修复支持新schema的代码。

不提供自动撤销贡献迁移或单SQLite恢复。灾难恢复须保留失败现场、独立目录演练成套备份，再另行确认账号库、成绩状态与配置整体恢复范围，避免吞掉备份后的数据。

## 验证边界

Windows临时库验证生产入口、质量/发布/回滚、历史排除、既有表保留、迁移事务回滚、版本兼容及成套备份恢复。Windows测试使用服务锁替身；Linux真实锁及Python3.12离线环境由服务器暂存安装脚本验证，只有通过才可切换。本地包准备好不表示已上线。
