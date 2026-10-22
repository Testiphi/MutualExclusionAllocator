# 公告、账号管理、手动车库升级

目标：升级代码并新增 community_schema=1；保留现有账号、车库、投稿、公告以外业务数据及服务器当前成绩版本。不要重新初始化数据库，不上传本地账号库或工作簿。本地完整验收已由用户确认。生产环境尚待下面逐步验收。

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
