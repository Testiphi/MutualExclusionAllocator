# 本地账号开发版（2026-10-18）

状态：第一版本地实现及用户本地验收已完成；仅推送feature/accounts-local，不合入main、不部署、不修改ECS/DNS/Nginx。生产站仍使用既有静态版本。
开发工作树：`accounts-local`，分支：`feature/accounts-local`，基于 `a3d01fb`。

## 启动

在本目录打开 PowerShell。建议新建独立虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -B -X utf8 -m backend.app
```

打开 http://127.0.0.1:8000/ 。不要改用 localhost，开发服务校验精确 Host/Origin。
端口可通过 `--port 8001` 更换，配套页面和邮件链接随之改变。
服务固定监听127.0.0.1；不支持通过此入口公开部署。

当前开发机已安装所需依赖，也可直接 `python -B -X utf8 -m backend.app`。
数据库/测试收件箱位于 `.local-accounts/`，已被Git忽略。默认仍是file模式；真实SMTP注册验证/密码重置的隔离验收步骤见 [真实邮件说明](MAIL_LOCAL.md)。环境配置和数据库均不会作为静态资源返回。

## 如何试用

1. 注册一个测试邮箱，密码12–128字符。只用测试资料，不发送真实邮件。
2. 打开 `.local-accounts/outbox` 最新JSON文件，把其中url复制到浏览器；点击“确认”验证邮箱。
3. 登录后修改车辆和星级，看到“已保存”再刷新核对。
4. “导入本机游客车库”展示条数并确认替换；原游客localStorage不会被删除。
5. 退出后恢复游客资料；再次登录恢复账号资料。新账号无资料时沿用全选当前区的初始行为；已保存的空车库保持为空。
6. 忘记密码会生成本地重置邮件；打开链接输入新密码，成功后刷新登录。重置撤销所有旧会话。验证/重置链接30分钟有效，单次使用；“重发验证邮件”使此前验证链接失效。

正式域名、localhost、127.0.0.1及不同端口的浏览器存储互相隔离，本地开发页面不能自动读取正式站的游客车库。本轮没有跨来源导出/导入文件功能。

## 同步和权限边界

- `auth.js`只由本地后端注入，普通静态入口不加载账号资源；公共车辆/成绩JSON和客户端计算保持原链路。
- 车库和星级作为一个快照保存。区档、排序等偏好仍按本机保存。
- SQLite事务内比较revision，冲突返回409；界面提供“加载账号资料”和明确确认的“用本窗口资料覆盖”。
- 写入串行化，连续修改在请求完成后保存最新快照。失败草稿按用户ID存在sessionStorage；本窗口刷新/退出再登录可恢复，关闭窗口可能丢失。存储失败有提示。
- 服务器根据会话确定用户ID，并校验前端预期账号ID，防止共享Cookie的另一标签页切换账号后将旧资料写入新账号。
- Argon2id密码哈希；数据库仅保存会话/验证令牌的SHA256。Cookie为HttpOnly、SameSite=Strict，本地HTTP开发没有Secure；校验Origin和CSRF，限制请求大小，登录/注册等有SQLite限流。
- 所有普通注册固定role=player，不接受客户端提权字段。role=admin现用于投稿审核，须通过本地维护命令授予；没有网页自助提权接口。
- `api.js`原有dataSource仍为static，个人资料另走账号适配层。不得直接把生产配置改成api模式。

## 接口

- GET `/api/auth/me`：当前用户和CSRF令牌；匿名访问也建立短期会话。
- POST `/api/auth/register`、`login`、`logout`。
- POST `/api/auth/verify-email`、`resend-verification`、`forgot-password`、`reset-password`。
- GET/PUT `/api/me/profile`：当前用户的cars/stars/revision，不接受请求指定其他user_id。

账号基础表包含users、sessions、profiles、auth_tokens及attempts。投稿开发扩展到模式v3，2026-10-20邮件通道扩展到v4；迁移与新增表分别见SUBMISSIONS_LOCAL.md、MAIL_LOCAL.md，不靠删库升级。

## 备份与恢复

```powershell
python -m backend.manage backup --file .local-accounts/backup-20261018.sqlite3
python -m backend.manage restore --file .local-accounts/backup-20261018.sqlite3 --data-dir .local-accounts/restored
python -m backend.app --data-dir .local-accounts/restored --port 8001
```

使用SQLite backup API，验证完整性及外键。目标文件存在时拒绝覆盖；恢复到新目录试运行。
备份包含账号与会话，作为私人文件保存；本地测试邮件不包含在数据库备份中。

## 验证

```powershell
python -B -X utf8 -m unittest backend.test_accounts -v
node --test test_profile_store.js test_allocator.js test_allocator_pruning.js test_race_scores.js test_app_state.js
node test_boot_smoke.js
```

后端测试覆盖会话、CSRF/Host/Origin、验证和重置、限流、越权、并发版本、非法车辆星级、静态资源允许列表及备份恢复。
前端状态机测试覆盖空车库、串行写入、断网草稿、账号隔离、冲突恢复、存储配额及退出冻结。

2026-10-18 自动化结果：账号后端10项通过、发布工具5项通过/1项Linux测试跳过、JS 51项通过、静态启动冒烟通过。备份恢复到新目录及完整性校验通过。

2026-10-18 实机内置Chromium验收：注册→本地邮件验证→登录→清空车库→刷新仍为空→确认导入游客76车→修改恶魔星级3→刷新保持3→十字路口生成方案→退出后游客恶魔仍为6。密码重置通过接口集成测试，未做浏览器全流程验收。
仅单机本地测试，未验证公网部署、真实邮件投递、手机账号界面或多人负载。当前环境TestClient使用httpx有上游弃用提示，测试仍通过。

## 用户本地验收完成（2026-10-18历史记录，邮件最新验收见文末）

用户明确反馈以下操作全部通过，本地账号基本使用流程验收完成：

- 使用本人邮箱成功注册并登录。
- 修改车库和星级，刷新后数据保留。
- 退出账号后游客车库不受影响；再次登录后账号资料恢复。
- 使用另一个浏览器登录同一账号，读取到一致的车库与星级。

上述结果来自用户实际操作后的确认；不是公网账号上线或真实邮件投递验收。验收账号邮箱、数据库、会话、验证链接和测试收件箱不写入公开开发文档或Git提交。

本轮仅补充验收记录，沿用上方已通过的代码测试结果，没有代码变更，因此未重复运行应用测试。按用户要求提交文档并推送功能分支，保持main及线上版本不变。截至当时，密码重置浏览器全流程、真实邮件、手机界面和多人负载仍未完成验收，成绩投稿及审核功能仍待设计；后续实现和2026-10-20邮件验收见下文。

## 玩家提交成绩与管理员审核（2026-10-18已实现本地闭环）

网页投稿、管理员审核、四档归类和0–5分评分已实现，操作与测试见 [投稿审核说明](SUBMISSIONS_LOCAL.md)。Excel批量导入、正式数据应用、发布和激励解锁仍未实现。以下保留原规划边界。

用户要求：登录后可提交车辆—地图成绩，管理员审核后修改、添加或忽略；上传方式和UI待定。

后续设计必须保持：

- 投稿绑定稳定users.id；保留投稿原文、来源、提交时间和版本，不能直接改`gauntlet_data.json`。
- 投稿库与正式成绩库分离。审核动作记录管理员身份、意见、修改前后值和时间；忽略也保留审核记录。
- 以大地图/小地图/分区/档位/车辆/星级/特殊跑法识别条目，保持现有SC与普通镜像规则；较慢成绩也需显式审核。
- 审核通过只产生待应用的变更清单，复用现有校验、预检和受控写回流程；不能把既有本地脚本直接公开成任意写入接口。
- 审核时复核权威数据基线，处理重复投稿和基线变化，发布版本与回滚需要另行设计。
- 首轮账号实现仅预留身份；后续本地开发已新增投稿表、私有图片证据和审核UI。现有规格见SUBMISSIONS_LOCAL.md，Excel批量导入另行实现。

公网账号上线仍需独立评估：真实邮件服务、生产安全配置、代理与备份策略、隐私/注销流程，以及按最终功能确认备案信息是否需要补正或变更。

2026-10-20：登录、注册、找回密码、邮箱链接验证和密码重置已统一为独立弹窗；注册和重置密码需二次确认。用户真实SMTP注册验证、密码重置、新密码登录、旧密码拒绝及旧登录会话失效均已验收通过（8002独立本地测试库，非公网验收）。详细记录见MAIL_LOCAL.md。

2026-10-20：超级管理员主号保护和邮箱绑定、限时单次管理员邀请已实现。原主号在8000库中升级为superadmin，8002独立邮件库不变；邀请注册及已有账号兑换流程见 [管理员邀请码说明](INVITATIONS_LOCAL.md)。模式升级v5，账号/车库/投稿保留。
