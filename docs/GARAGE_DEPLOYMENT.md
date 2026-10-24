# 车库工具栏布局升级（2026-10-23）

状态：用户已确认上线后页面验收完成。下文保留部署方案，实际结果见文末；本次收尾仅提交推送文档后暂停。

本次源码3baf0b3，仅index.html和styles.css的运行内容改变，后端、账号/成绩/贡献/反馈schema保持。保留当前线上4a28f6d76b9d3e93d3227120作为待现场核验基线，不合main。

本次不执行任何生产迁移或初始化，不重跑反馈/贡献/成绩迁移，不用包内JSON覆盖服务器成绩，不修改工作簿、Nginx、SMTP、systemd配置或旧目录。

每步回传后继续：
1. 只读核对current、服务、实际进程cwd、公网health、timer、备份和空间。现有schema6/community1/contribution1/feedback1应保持，成绩版本以现场为准。
2. 上传本目录全部11文件，SHA清单应10项OK。用本目录deploy_production.py --bundle racepick-accounts-release.zip仅暂存。
3. 到返回的新版本目录运行bash production/install-runtime.sh，离线依赖及临时库自检通过后再继续。自检中的迁移仅针对临时数据库，不是正式库操作。
4. 用当前旧代码生成成套备份，校验并独立目录恢复演练；保留真实路径、版本和counts，active_database_replaced必须为false。
5. 经用户确认短暂维护窗口后暂停timer，等待已有备份结束，停止网站并生成停服最终成套备份。无需数据库迁移。
6. 使用本次工具--version真实新ID --activate，再启动网站。核对current、服务状态、/proc/MainPID/cwd、公网health四项；账号/成绩/贡献/反馈开关及版本保持。
7. 新版成套备份校验和独立恢复演练通过，恢复timer并核对enabled/active(waiting)/明确NEXT。公网复核手机微信和桌面布局，保存/恢复/清空/全选/排序正常。

本地已检查320/360/390及1280px；真实微信端效果待用户公网验收。暂不清理任何旧发布目录、备份或演练数据。若异常，先保留现场核对日志；不恢复旧SQLite、不修改车库或成绩来处理布局问题。

包对比补充：backend/feedback_production.py相对上次交付仅LF/CRLF不同，规范化换行后完全一致；有逻辑/布局变化的运行文件只有index.html和styles.css。旧包不改动。

## 实际上线与验收记录

证据来自用户服务器回传及明确确认，不是代理直接登录生产服务器。文档更新不修改已上传交付目录和发布包，不合并main，不改变任何业务数据或工作簿。

### 交付和切换

- 发布ID：6ee40a45b00b0e347bf973fe；源码3baf0b3970dc638afd9910723943f3a7ad6a0781；数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。
- 本地交付.production-build/delivery-20261023-garage共11文件；ZIP SHA256为fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb。服务器目录/root/racepick-deploy/20261023-garage-6ee40a45。
- 用户简述确认上传完成、10个文件校验全部OK、暂存成功、离线运行环境及临时库原生自检通过；未提供这些步骤的完整输出。
- 本次没有生产迁移。用户确认停服最终备份校验通过、成绩未变，再明确授权激活。
- 激活完整回传：上一版4a28f6d76b9d3e93d3227120；新current及/proc/138683/cwd均为/opt/racepick/releases/6ee40a45b00b0e347bf973fe，active/running。PID仅是当时记录。
- 首次curl 502，重试后health正常。最后完整health：production、schema6/community1/contribution1/feedback1，贡献/反馈均true，成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。
- 用户最后明确确认页面验收完成，覆盖此前要求的桌面、手机微信布局和五项操作；未提供新的真机截图，不能声称代理独立进行了真机测试。

### 备份与定时器

- 部署前完整回传证明10月23日04:16:09开始、04:16:10结束的自动备份Result=success、ExecMainStatus=0，生成scores-20261022T201610532450Z.zip（155551字节）。这是旧反馈应用4a28f6d…运行时的自动执行证据，不是新布局应用的首次自动备份。
- 旧版在线成套备份及独立恢复演练由用户确认通过，active_database_replaced=false；停服最终备份生成/校验通过；新版成套备份及独立演练通过，active_database_replaced=false、网站健康正常。没有提供这三步的具体备份路径或演练目录，不补造文件名。若后续需要精确恢复点，现场只读核对清单。
- timer于2026-10-23 **10:46:44 CST**恢复，enabled、active(waiting)，NEXT为2026-10-24 **04:16:12 CST**，LAST为10月23日04:16:09。调度恢复不等于明日执行已经成功。
- 恢复timer后的第一份health输出末尾被截断；随后用户单独执行并回传完整health确认各schema、成绩版本及开关保持，未依据截断输出提前断言。

### 收尾与暂停

用户授权更新交接并完成必要推送后暂停。只提交文档到fix/garage-toolbar-responsive，包含本轮源码提交的历史；main保持未合并。原8011及其他本地测试环境、账号/成绩/反馈/备份和工作簿全部保留；不继续删除旧目录、不重启服务、不重跑迁移、不新增监控或提醒。之后等待用户新指令。
