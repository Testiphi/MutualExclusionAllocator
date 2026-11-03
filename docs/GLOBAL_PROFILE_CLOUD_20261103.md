# 国际服账号云车库与暂停交接

2026-11-03。用户要求国际服车库现在接入账号云端，完成后暂停。此要求覆盖本轮A批先前“国际服仅本机”的阶段描述。本文件记录最终语义；不作为生产迁移、部署、上传或上线授权。

## 行为与接口

网页国服/国际服共用RacePick账号登录，车库记录分开保存：原profiles保持国服；新profiles_global仅国际服，包含cars、stars、ocMap、独立revision/updated_at。国际计算仍五区满星理论，OC与普通成绩独立；未修改算法、估算、车型/星级/地图规则或运行JSON。

网页沿用Cookie/Origin/CSRF/X-Account-ID/X-Profile-Save:explicit门禁。GET/PUT `/api/me/profile?server=global` 使用国际记录；省略server继续为国服。GET无记录为revision=0/profile=null，合法空车库为cars=[]/stars={}/ocMap={}，不混淆。PUT字段为revision/cars/stars/ocMap；stars为原始1–6整数，ocMap为严格boolean映射，true仅允许当前国际目录有OC成绩的车型。不存在或非法车型/星级/OC拒绝，不回退国服。相同revision的并发保存只有一个成功，另一个409。

原生沿用新A批 `/api/mini/account/v1/profile?server=cn|global`，账号Bearer+X-Account-ID，两个服都返回storage=account、remote_supported=true。国际PUT示例：

```json
{"schema":1,"request_key":"random-global-save-key","explicit_save":true,"intent":"import_guest","confirm_guest_import":true,"revision":0,"cars":[],"stars":{},"ocMap":{}}
```

正常账号编辑intent=save；游客导入必须明确确认，登录/GET不自动写云端。响应包含server/revision。409 PROFILE_CONFLICT含server、current远端完整profile及submitted本地原revision/profile（含OC）；两份都保留，由用户选择加载或以最新revision明确保存。原生相同key不能跨服复用，改服409；恢复路径为 `/operations/{key}?action=profile-save&server=cn|global`，其余action仍只有action query。恢复也复核actor/服别，不从国服返回国际数据。

网页本机游客车库、旧分服草稿与云端分别保留。国际账号草稿使用带.global的user键，国服原键不变；登录不自动导入，本机导入只先进入账号临时草稿，明确保存才上传。登出/切账号不把账号车库写回游客，也不串国服/国际服；失败GET不覆盖本机，冲突不自动覆盖。网页已接回国际账号、OC加载/保存与分服草稿，使用同一ProfileStore原模块，不增加第二套状态机。已有旧服务器/静态页面没有云组件标志时继续保留原本机流程。

## schema与迁移边界

新增独立global_profile_schema=1及profiles_global，原主schema6与国服profiles不改。仅**新建隔离本地账号库**自动初始化空组件；已有本地库及所有生产库启动不自动迁移。组件未准备时原生国际云请求503、features.profiles.global=unavailable，不能把失败当空库覆盖设备数据。

本地显式迁移仅接受已标记的独立score-version lab：

```powershell
python -B -m backend.global_profiles migrate-local --data-dir <新隔离lab的accounts>
```

生产迁移入口仅准备：`python -B -m backend.global_profiles migrate-production --config <私有生产配置>`。须后续用户单独授权并由运维在Linux停服/服务锁下执行；先核验schema0或已完整schema1、成套备份/恢复点，再创建空国际车库表。已迁移幂等，不导入本机车库、工作簿或种子。保留原业务逐表指纹并检查不变；异常即停并保全现场，不清表重建。**本轮未执行该生产命令**。

账号数据库一致性备份自动包含新表；备份manifest新增global_profile_schema声明，恢复演练检查其与SQLite一致，并计数profiles_global。旧无组件备份按0读取。发布capability新增global_profile_schema:1，启用后标准激活工具拒绝回退到不能识别国际账号车库的旧应用。回退需兼容代码并保留新增车库，不能靠旧库覆盖；整库恢复另行授权。

## 源码、验证与暂停

代码和A批身份/会话一起本地固定，精确提交与文件SHA见本轮交付回执。五个198999a共享模块不改；网页auth.js/index.html/api.js为必要云车库接线，保留现有页面、特殊跑法按钮、截图文案与“新功能”标识。map_recognition.js及其他会话文档、运行数据不纳入提交。

验证分别记录网页/原生分服读写、星级/OC、revision冲突、空车库、失败不覆盖、显式导入、账号/跨服隔离、迁移幂等、备份恢复与旧程序兼容拒绝。新增隔离端口与原有服务分开；已有8033/8043/8044不启停、不写库。真实微信身份、手机相册/iOS/Android/TLS域名、Linux正式迁移仍待验收，本轮不会据本机测试宣称上线。

完成固定源码与交接后按用户要求暂停：不继续B–E或正式主页presenter，不构正式包、不提交维护数据、不推送/合并、不操作生产或微信后台、不创建监控或清理旧状态。
