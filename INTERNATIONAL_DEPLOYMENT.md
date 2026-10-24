# 国际服选车部署与验收（2026-10-24）

用户已完成逐步部署，明确确认桌面及手机微信验收通过。生产应用bd12e3fb2c2519b0238afd90，成绩版本保持42d62fde9b81197ac0558087a9a25f97；本次无生产迁移。详细实际结果与备份路径见文末及CLOUD_HANDOFF.md最新节。下文保留发布前准备和执行流程。

## 交付与范围

复用build_production.py、deploy_production.py及production_release_tools.py的完整生产交付流程，使用干净提交构建；代码与国服JSON均绑定提交，离线19个Linux/Python3.12依赖必须与requirements-linux-py312.lock逐哈希匹配。外层SHA256SUMS.txt、RELEASE.json和ZIP内manifest.json可独立核对。国际服三份JSON及生成/验证工具作为完整组件打包，缺件、混用版本或哈希错误均拒绝；旧包仍可校验。

交付只包含白名单程序、国服基线JSON、国际服运行JSON和离线依赖，不含真实账号、数据库、凭据、反馈、工作簿、候选资料或本地测试数据。production/selfcheck.py增加国际服数据和HTTP读取检查，全部在新建临时库执行；Linux原生环境和迁移分支仍须上传后运行，不能以Windows自检代替。

国际服首期仅五区满星理论，321条（315非OC/6OC）、29辆基础车、44图/42有值，普通291/SC30。富士最后两图暂无成绩；4辆EVO参数待补。国际车库/OC/草稿独立保存在本机；国际云车库、投稿、审核、发布链、自审免积分和OCR未实现。国服已有账号/成绩/贡献/反馈链继续沿用，无新增生产schema迁移。

## 生产成绩边界

包内国服JSON是代码提交的数据基线，包含本次本地授权的白龙×幽灵船22.84；线上启用score-state后，实际成绩优先使用独立版本库，部署程序不会以包内JSON覆盖它。这个数值是否已在服务器存在、是否另需正式成绩版本发布，须上线时根据实际当前版本只读核对，再单独给出差异。不得初始化、重复迁移或用完整本地JSON覆盖线上新投稿。

国际服JSON是这次新增的静态独立数据集；与国服score-state、账号资料和反馈库隔离。

## 后续执行顺序

参照已验收的GARAGE_DEPLOYMENT.md。每一步得到用户回传并核对后才给下一步命令，不一次性执行以下全流程。

1. 现场只读核对current、systemd服务、实际进程cwd、完整health、备份调度/最近结果、备份目录及空间。历史应用6ee40a45b00b0e347bf973fe、成绩42d62fde…仅为待核基线，不预设现场相同。
2. 用户上传整个交付目录，核对外层全部SHA、ZIP内manifest及真实新发布ID；deploy_production.py默认只暂存，不激活。
3. 在返回的新版本目录运行既有install-runtime.sh，安装锁定离线依赖并通过Linux/Python3.12临时库原生自检。这里临时库迁移不是正式库迁移。
4. 用当前旧程序生成成套备份，校验并独立目录恢复演练，记录当前成绩版本、各类counts和active_database_replaced=false。
5. 用户确认维护窗口后暂停备份timer，等正在执行的备份结束，停网站并生成停服最终成套备份。无需生产迁移/导入/初始化。
6. 用本次交付工具激活真实发布ID，启动网站，核对current、服务状态、/proc/MainPID/cwd和完整公网health；原schema、成绩版本及开关保持。
7. 验证新版成套备份和独立恢复，恢复timer，确认enabled、active(waiting)及明确NEXT；再做国服/国际服桌面和手机微信验收、分服草稿/车库、OC/SC、五图互斥、空图显示。

若异常先保留现场和日志，依据兼容性及实际旧版本讨论代码回退；不恢复旧SQLite或覆盖用户车库来处理页面问题。不自动清理旧发布目录、工作簿、备份或测试数据。

## 2026-10-24 国际服上线及公网验收完成，工作暂停

证据来自用户逐步执行服务器命令的完整回传及明确验收确认，代理未登录服务器。2026-10-24 08:30:27 CST启用新应用bd12e3fb2c2519b0238afd90，源码/数据提交5ade7ea3598eb104f136365fb0a51574c16d8013；current与/proc/145790/cwd均为/opt/racepick/releases/bd12e3fb2c2519b0238afd90，active/running。PID为当时记录，后续重新核对。

- 完整上传归档SHA、目录13项SHA均通过，发布ID及85文件清单核对；暂存未激活阶段旧版保持。Ubuntu24.04/x86_64/Python3.12.3，19个锁定离线依赖安装及pip check、Linux临时库原生自检均通过；临时库自检不等于生产迁移，本次没有生产初始化/迁移/导入。
- 上线后完整health：ok/production/schema6/community1/contribution1/feedback1，contributions=true、feedback=true、score_writes=true，成绩版本42d62fde9b81197ac0558087a9a25f97保持。当前国服成绩JSON哈希bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9；包内新增白龙普通22.84没有通过此次代码部署发布到score-state，后续如需发布须单独比较审核，不能用整包覆盖线上成绩。
- 三次成套备份及独立恢复演练均通过，均160113字节、racepick:racepick、权限600；恢复结果39用户/21车库/3投稿，pending_batches=0、active_database_replaced=false。贡献schema1，counts contributions0/sources1/events0/preferences1；反馈schema1，tickets/events/requests均0。停服最终备份与新版备份内各文件哈希一致，账号SQLite哈希cef5bfa17f519c03b59459e173a2ec48743464a2e24d49a1c31c696aaf8b201a。

| 阶段 | 备份（/var/lib/racepick/backups/） | 独立演练（/var/lib/racepick/restore-drills/） |
| --- | --- | --- |
| 旧版在线 | scores-20261024T002837971492Z.zip | 3f1ef0a291f8b20324111663 |
| 停服最终 | scores-20261024T002956371320Z.zip | 4e858de18e76f918a60f2029 |
| 新版在线 | scores-20261024T003107716123Z.zip | c7b65a1385de6745d3d7a78b |

- 2026-10-24 08:31:40 CST回传：备份timer已恢复enabled、active(waiting)，NEXT为2026-10-25 04:17:45 CST；LAST为10月24日04:16:12，实际04:16:13成功生成scores-20261023T201613699083Z.zip。这证明新版切换前的自动备份成功及切换后的调度恢复，不表示10月25日已执行。恢复timer后的完整health保持。
- 用户明确确认桌面和手机微信验收通过，覆盖此前五图选车/分服车库与草稿/OC及SC/空图项目；两张截图另指出控件排版偏好，不将此偏好混作既有功能验收失败。代理未独立操作手机微信。
- 登录提示另行只读核查：dpkg --audit无输出、无reboot-required标记，最近自动更新日志All upgrades installed，cloud-init被保留未升级；早期发行版元数据警告后近期日志不再出现。未执行apt升级、发行版升级或重启，不凭日志推断cloud-init保留原因。

### 已提交但尚未发布的两项后续修正

用户希望桌面恢复三行，手机档位换行时分组更清楚。476a9e2只改styles.css：服别/档位/分区各自一行，浅色分隔线；档位组内仍可换行。真实本地浏览器1280/390/320宽验证，无横向溢出；320宽自动档换到本组下一行，分区仍在下组，国际服隐藏项无残余分隔。1b2361b只在既有NICKNAME_ALIASES加入兔子→c2，保持车辆身份/目录/成绩不变，国服与国际服实际搜索均匹配c2。14项前端回归通过。截图位于repo/.production-build/layout-followup-20261024/。

这两项仅提交到源码，未重新打包或部署；生产仍为bd12e3fb2c2519b0238afd90，旧发布包及其校验值保持。未来需另行准备新包并由用户执行部署。用户要求完成交接推送后暂停：不清理旧应用、备份、演练、工作簿或测试数据，不继续系统维护、成绩发布或其他开发，无监控/提醒。
