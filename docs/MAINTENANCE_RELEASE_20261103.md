# 同批发布维护冻结：双服成绩与车辆规则

2026-11-03用户明确纠正：本次网站更新必须同时发布维护侧更新，不能只携带种子。本文件覆盖上一版“正式维护数据另行更新”的范围判断。此处准备本地工具、验证与云端步骤；本对话仍不操作生产。

目标是冻结b57d97a8f4e484be69238ab0的五份runtime原字节：CN4516键/83图，Global694条/48车/44图/21OC/52SC。清单SHA940f8660585c495a780390b709dfd52e80f7610f57e0179c5da937c53c4e4282；data_commit=null。cc850两区共同min3/四区max3、国际fxxk入池也在本次正式更新范围。完整维护733、工作簿/参考/台账不入运行。不能只应用本轮19/2项而漏掉此前11月1日已批准并包含在冻结中的更新。

## 为什么增加离线发布入口

现有网页投稿发布不允许改车辆规则；已有生产score-state不会因切代码而刷新。新入口 `backend.maintenance_release` 只支持服务端离线CLI，没有HTTP路由、客户端权限或自动启动导入。它复用现有不可变版本库、账号库、双服锁与成套备份；不改旧seed、不重播种、不覆盖旧版本文件，不伪造投稿/贡献积分或已读事件。

preview从SQLite mode=ro读取两个活动指针/开关及全部五文件来源SHA，只写用户指定的新计划文件。完整差异列出每个地图/区档/车/星级/OC/SC身份的新增、删除、提速、变慢和其他变化；另列完整车辆规则/目录差异。计划绑定现场双服base、原五文件SHA、两个control绑定与开关、账号绑定、源码发布ID/冻结SHA及目标五文件SHA；canonical JSON SHA为批准摘要。现场有投稿或其他更新不在冻结中时，删除/冲突必须在此明确显示并停止核对，不能默默丢掉。这里不能拿本地旧种子演练差异冒充生产差异。

apply必须提供已复核计划及摘要、`--confirm-all-differences`。只在Linux服务锁下、以账号库现有owner执行，网站必须停止，备份timer/其他维护命令也暂停；先成套备份并校验，再按CN→Global锁顺序操作。车辆绑定标记只追加按计划/冻结SHA授权的新目录哈希，保留原哈希与历史，原账号绑定、initial/seed和开关不改。两份标记均注册后才创建不可变新版本，最后提交SQLite指针：中断保留可读原版本及可备份的历史；两个活动指针及审计行在同一事务提交，不会只发布一服。新版本及标记保留原服务owner/mode。旧业务逐表指纹不变，唯一新增表maintenance_releases存计划/双服parent/target/备份SHA/状态/时间。不存在正式账号导入、账号资料迁移或成绩积分补造。

同计划响应丢失可 `status --id <计划摘要>` 恢复；重新apply同一计划只在原目标仍活动且审计applied时幂等返回。有新版本、已回退、源/开关/计划变化均拒绝，需重新预览。中断于注册或事务前可能留未引用的不可变版本，它们不活动、不删除；原指针仍有效，重新运行同批准计划即可。不可人为改指针来“修复”。

## 云端逐步命令模板（仅准备）

先按网站交接只读核验、上传校验、暂存、离线安装/临时库自检和在线备份恢复；用户回传后逐步推进。这里的路径/摘要必须替换成现场核对值，不是一段授权批量执行脚本。

```sh
# 只读现场预览；新包暂存目录为SOURCE，CONFIG是原私有配置，不贴聊天内容。
cd "$SOURCE"
.venv/bin/python -B -m backend.maintenance_release preview --config "$CONFIG" --source "$SOURCE" --freeze-id b57d97a8f4e484be69238ab0 --output "$NEW_PLAN"
```

用户核对完整计划（包含删除、变慢、两服规则和全部历史维护更新）后固定摘要。停服最终备份和独立恢复通过，global-profile组件显式迁移后，如活动版本/开关未变可继续；不变的账号新组件不使计划失效。若现场变化则重新preview，不覆盖旧证据。

```sh
# 正式数据写入，云端必须先逐项回传核对并取得当前步骤授权。
.venv/bin/python -B -m backend.maintenance_release apply --config "$CONFIG" --source "$SOURCE" --plan "$NEW_PLAN" --expected-plan "$APPROVED_DIGEST" --confirm-all-differences --output "$NEW_APPLY_RECEIPT"
# 输出丢失时用同id读审计，不能改key重复发布。
.venv/bin/python -B -m backend.maintenance_release status --config "$CONFIG" --id "$APPROVED_DIGEST" --output "$NEW_STATUS_RECEIPT"
```

先确认双服target、精确五文件SHA、CN4516/Global694及两份规则变更真实活动，再切新版代码、启动唯一OCR和网站。国际网页投稿写开关保持原值（可仍关闭），本离线冻结发布不靠临时开启它绕过门禁。随后新成套备份、独立restore-drill、原账号/车库/反馈/贡献行保持、真实页面及国际云车库验收。原生默认关闭不变。

## 定点回退

不恢复旧SQLite或旧score-state目录。新工具 `rollback` 同样要求停服服务锁/成套备份、明确审计id及当前审计canonical SHA；且两服活动版本仍恰好是该次target、没有进行中的发布批次。任何后续真实成绩版本都使回退拒绝，需另拟保留新数据的处理方案。回退只原子恢复两个parent指针并记reverted，保留所有新版本、目录授权、账号/国际车库及其他业务行，不能撤销global_profile_schema1。

```sh
.venv/bin/python -B -m backend.maintenance_release rollback --config "$CONFIG" --id "$APPROVED_DIGEST" --expected-receipt "$CURRENT_CANONICAL_RECEIPT_SHA" --output "$NEW_ROLLBACK_RECEIPT"
```

维护发布仍applied时，新激活工具拒绝旧777/a38/c06不兼容包；a38兼容候选只可在这次维护数据已成功定点回退、实际旧规则可读后使用，且仍不能修复共享的云车库实现缺陷。c06因global-profile1始终不可直接回退。所有回退须先用户确认，不能自动因一项页面验收失败丢掉维护更新。
