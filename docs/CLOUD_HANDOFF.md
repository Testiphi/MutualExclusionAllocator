## 2026-11-10 跑法视频 1117 条批次 0272786b 上线

- 20:55:25 CST 生产复核通过，967 条启用绑定逐键零差异，154 条可新增、35 条待更新、4 条待停用，零冲突。冻结 ID `0272786bc62ca02ce75aee31`，计划 SHA-256 `0272786bc62ca02ce75aee319f21a8732f11c226c7a2c6b6181e763e88a8c467`。现场回执 `/root/racepick-deploy/video1117-recheck.5krxipCq/field.log`。
- 写入前成套备份 `scores-20261110T125721876273Z.zip`，SHA-256 `c1860b4e8cafc04e064b877de70198efe2917107f4d4431eb520ca3f0fcff4cf`。独立恢复目录 `4837196831605631b64b241c`，967 条基线、193 项及五份成绩文件核验通过。
- 生产单事务新增 154 条、更新 35 条、停用 4 条。回执 `/root/racepick-deploy/video1117-apply.6vm6kpFn/apply.json`，SHA-256 `6e6acfb7cca8bf794a9aa4a6fda0d28ef4b8b817a6a6d04c91142a762fa55215`。
- 21:00:16 CST 公网健康与矩阵逐格核对通过，国服 797 格／953 条，国际服 160 格／164 条。网站 PID 285482、OCR PID 285479 的实际目录和 current 均为 `/opt/racepick/releases/80fd1c937db91d3df4ac1170`。OCR ready，正式 A 云车库写关。本批仅发布视频数据，未切换网页或同步小程序。
- 双服活动成绩为国服 `d6c91bbffea4c2036d1e294887faba5b` 和国际服 `8f4c827ecd4b5b3466bc39bcbd1a521c`。写入前后备份和恢复副本的五份成绩文件哈希一致。
- 上线后成套备份 `scores-20261110T130143999959Z.zip`，SHA-256 `4c528ddadf72d060dc0c191fa00025f7902d3efd2365bd4e8842b88631c68224`。独立恢复 `a8f91369f55e591d35a81eed`，1117 条启用绑定逐键匹配冻结目标，193 项按行 ID 读回匹配写入回执。收尾回执 `/root/racepick-deploy/video1117-postwrite.kc6r0vKW`。备份 timer enabled、active(waiting)，下次触发 2026-11-11 04:18:00 CST.

## 2026-11-10 网站 80fd1c93 与视频批次 dfcb6de8 上线

- Workbench 13:08:06 CST 切换网站到 `80fd1c937db91d3df4ac1170`，源码 `f76c896e12e7b34f627d8a8506eb3920dd3b96c6`，前一版 `9ade659b378f4f94f17a9d10`。网站 PID 283003 与 OCR PID 282996 的实际目录均指向新版本。公网首页、健康和逐格视频矩阵通过。OCR ready，正式 A 云车库写关闭。切换回执 `/root/racepick-deploy/80fd-dfcb-cutover.3BXVG5bF`。
- 视频冻结 `dfcb6de86673be3e471a7db6`，计划 SHA256 `dfcb6de86673be3e471a7db6664358d8d8900c30ff5c512c8bebb68dfc19599a`。974 条旧基线零差异，单事务更新 13 条、停用 7 条，启用 967 条。公网国服 787 格／807 条，国际服 160 格／160 条。写入回执 `/root/racepick-deploy/80fd-dfcb-apply.4X5KyKze/apply.json`，SHA256 `43a883acb0f5a7cff846c167582ff8f75be025f4cab4cc2500984fc567682eb4`。首次写入命令在 Python 解析阶段退出，修正版重新验证 974 条旧基线后执行成功。切换时 SHA256 清单一行格式警告，收尾分别重验写入回执和 967 条种子通过。
- 国服活动成绩 `d6c91bbffea4c2036d1e294887faba5b`（4752 键），国际服 `8f4c827ecd4b5b3466bc39bcbd1a521c`（697 条）。写入前后备份清单与恢复副本的五份成绩文件哈希一致。本次范围为网页与跑法视频。
- 写入前备份 `scores-20261110T050421617554Z.zip`，SHA256 `3183b3a072ac7364e44f02a05651ce3a60888893ba729059f5787b85369bd6de`，恢复目录 `730ec0c20fda23cb081414e8`，恢复副本逐键匹配 974 条。
- 上线后备份 `scores-20261110T050915599459Z.zip`，SHA256 `1bca0e3836592f7ba9df2e0f841a921242def50d08553c6a3660fbc02c5ebc10`。恢复目录 `1f89c827f191c52787197859`，967 条启用绑定逐键匹配目标，7 条停用记录按原行 ID 和键核对通过。现场回执 `/root/racepick-deploy/80fd-dfcb-postcutover.6qZj2Lwd`。备份 timer enabled、active(waiting)，下次触发 2026-11-11 04:15:49 CST。

## 2026-11-10 网站 9ade659b 与 974 条跑法视频上线

- Workbench 确认 current、网站 PID 280752 和 OCR PID 280749 均指向 `/opt/racepick/releases/9ade659b378f4f94f17a9d10`，前一版本为 `6f0dfa79522b55f1b1530fb2`。公网首页和健康通过，OCR ready。正式 A 云车库写关，隔离账号服务 PID 241421 及健康开关与预检一致。
- 独立视频计划 `528ef822444581f665016dcb9c83060be850f6915a4f1c65fb2d390226876591` 实际更新 412 条、新增 17 条。写入后零待写、零冲突，公网矩阵国服 791 格／811 条，国际服 163 格／163 条。写入回执 `/root/racepick-deploy/video974-apply.H3yxG2yt`。
- 双服活动成绩维持已核验基线，国服 `d6c91bbffea4c2036d1e294887faba5b`（4752 键），国际服 `8f4c827ecd4b5b3466bc39bcbd1a521c`（697 条）。写入前后成套备份及恢复副本的五份成绩文件哈希一致。
- 写入前成套备份 `scores-20261110T024923789838Z.zip`，SHA256 `41810e09e21b25a680aab39378a9b5124205f1e59433f3b1e0b9b529c48930a1`，独立恢复目录 `8185b1a3528c84b6f04d922b`。恢复副本复现 412 条待更新、17 条待新增和零冲突。回执 `/root/racepick-deploy/video974-prewrite.0mgEvvYl`。
- 10:51:42 CST 启动上线后备份验收。成套备份 `scores-20261110T025143314101Z.zip`，SHA256 `1929a673e75b39810ef396cb5d86d9743e837564940076f2610d67f2f4bd7b04`，独立恢复目录 `82d264ed46ba9769255a8c00`。双服版本、五文件哈希及 974 条启用视频通过核验。回执 `/root/racepick-deploy/video974-postcutover.LKADseuO`，标记 VIDEO974_POST_CUTOVER_BACKUP_OK。
- 收尾通过标记表明备份 timer 已恢复为 enabled、active。此次回传片段未含恢复后的下次触发时间。

## 2026-11-09 跑法参考与双服成绩上线完成

- 用户确认导入 957 条跑法、发布双服成绩并切换网站。现网 current、网站 PID 276552 和 OCR PID 276545 均指向 `/opt/racepick/releases/6f0dfa79522b55f1b1530fb2`。切换前应用为 `0d730c500f276d055e664d90`。
- 公网首页与健康接口通过，OCR ready，正式 A 启用且云车库写关闭。公网跑法矩阵国服 783 格／798 条，国际服 159 格／159 条。导入回执 `/root/racepick-deploy/route-video-import.KYUsThjH`，写入后复核完全匹配 957 条、待新增及冲突均为 0。
- 成绩维护源 `fd6d716fb6841c5b006d3bf2`、冻结 `1c8f617337be89c7e0d9a2c4`。正式计划 `/root/racepick-deploy/maintenance-plan.DI7Ix6sS/plan.json`，执行摘要 `f395f5aeae874b6e15a5ef0636c319d08872d444cc88a53f085324231dabdde1`。应用回执 `/root/racepick-deploy/score-apply.PBpXe4h8/apply.json`，规范摘要 `f0476b17db356340100455cf2bfac25b854304cf2634dff0eb8a52977683e168`。活动国服 `d6c91bbffea4c2036d1e294887faba5b`（4752 键），国际服 `8f4c827ecd4b5b3466bc39bcbd1a521c`（697 条），五份活动文件与批准计划哈希一致，原业务行保留。
- 写入前成套备份 `scores-20261109T150525047525Z.zip`，SHA256 `692b9cc3c71ae673c02056af0badf677feb43c703b3ca8e5763482111da1325e`，独立恢复 `49f374fd39f60312153711e8` 通过。成绩工具另保存了已含跑法、成绩尚未切换的备份 `scores-20261109T150702414076Z.zip`。
- 上线后成套备份 `/var/lib/racepick/backups/scores-20261109T150847717302Z.zip`，SHA256 `2b1375e03795d555f4a35e48d05e033219684cb5470c7cd26f6588870a7d52cb`。独立恢复 `59af2a624e7160c9db0e72d8`，双服活动版本正确，待处理批次均为 0，跑法 schema 1，恢复 798 条国服及 159 条国际服启用记录。回执 `/root/racepick-deploy/postcutover-backup.D4Z8cPhN`，标记 POST_CUTOVER_BACKUP_OK。
- 备份 timer 已恢复为 enabled、active (waiting)，现场所示下次触发为 2026-11-10 04:17:16 CST。本次公网验收覆盖首页、健康与双服矩阵。

## 2026-11-09 Route-video and combined score preflight

- Candidate 6f0dfa79522b55f1b1530fb2 passed target Linux offline runtime, temporary database and OCR self-checks (CANDIDATE_LINUX_SELFCHECK_OK). The final current check matched 0d730c500f276d055e664d90.
- At 22:56:07 CST, backup scores-20261108T201926976965Z.zip (SHA256 50f12d23514c28f83c247e42599b33aeddb8a02d1f6d5ea342b19170e46da515) passed restore drill into e2619ddeec8ad17a4b6f2f18. Both active versions were recovered, both pending batch counts were zero, and active_database_replaced=false. Receipt: /root/racepick-deploy/restore-drill-20261109.WYf06k9R.log.
- At 22:58:57 CST, the production account database read-only route preview reported 957 additions, zero duplicates and zero conflicts. Receipt: /root/racepick-deploy/route-video-preview.TxMfcC5I.log.
- At 23:00:00 CST, the combined score review (approved maintenance freeze 3f4fc0cb55f4ece93aed8dcd plus five lap times and one availability entry) matched the local full diff. CN 4569 to 4752 (184 added, 14 faster, 1 removed), Global 694 to 697 (3 added, 7 faster). Removed CN key: Old Arena / Crossroads, zone 4 theory, Aion 3-star jump route, 24.30 s. Diff SHA256 73f0e8015162649b9aaa3bdecc482f0ea20b3d2b7f645b80bf407b947b2e4cc2. Review-only receipt /root/racepick-deploy/combined-score-review.AnQjQTWu/plan.json, SHA256 ed7f7da4f5e50d0d2364e3035e860cf96431a829cbba9242991c7f7c82bedea7.
- Await explicit approval of route import, score publication, and application cutover. The review-only receipt is evidence for preparing the executable score maintenance plan.

## 2026-11-09 跑法参考候选 6f0dfa79 只读核验

- 外层 ZIP SHA256 `162b762959b56ce322dfd662ecc76b7d63ee41a2b0e30276b027f21b3a4e727e`、外层 10 项 SHA256SUMS、内层 181 项 manifest 及重算发布 ID `6f0dfa79522b55f1b1530fb2` 均通过。8064 第 238 批种子共 957 条，国服 783 格／798 条，国际服 159 格／159 条。
- 用户回传 Workbench 2026-11-09 22:45:55 CST。current、网站 PID 266869 与 OCR PID 266860 的实际目录均为 `/opt/racepick/releases/0d730c500f276d055e664d90`，两个单元 active/running。公网健康 ok，OCR ready。
- 活动国服 `b195cd622bba75671c93308efc2b99ec`、国际服 `9121ae372bdc0b8ed8ac1cbafd769561`。五份活动文件 SHA256 均匹配各自活动 manifest，只有国服 cars.json 与候选种子同 SHA。国服 3 个 applied 批次，国际服无批次。投稿 5 个 accepted、1 个 ignored，已采纳无回执为 0，OCR 队列空。
- 公网活动逐键对照候选。国服 4569→4752 键，r兔仍 29.70、五区理论 f5 仍 31.49，帝国 21.48、银电 29.93、四区高手 f5★3 25.31 及其普通档镜像均缺键。另有 193 个范围外差异键。国际服 694→697 条，范围外差异 10 个（3 个包内新增、7 个实值变化）。候选成绩是种子。任何后续成绩更新须从真实活动指针制作并审核定点计划。
- 主站 Nginx 通用 location / 将跑法根路径及子路径交给 127.0.0.1:8001。公网列表及矩阵均返回 JSON 404，账号库尚无两张跑法表。后续先校验候选 Linux 运行条件、备份恢复和实际库只读预览，再另行授权导入与切换。
- 最近成套备份 `scores-20261108T201926976965Z.zip`，2271529 字节，SHA256 `50f12d23514c28f83c247e42599b33aeddb8a02d1f6d5ea342b19170e46da515`，全部成员哈希通过，清单指向上述双服活动版本。timer enabled/active(waiting)，上次 11-09 04:19:25，下次 11-10 04:15:36 CST，备份服务上次成功。最新列出的恢复目录 `e7f97f5876567566f94f8ff4` 尚未与源备份及成功回执配对。历史演练及其对应备份见下文。本轮只读，未导入、写成绩、迁移、改配置、重启或切换。

## 2026-11-07 最新交接：隔离双服云车库可写准备与现场回退通过，客户端 W1/W2 待接管；文档更新后暂停

本段覆盖下方旧阶段“cloud_writes=false／真实账号只读未验收”等当前态描述，旧记录原样保留。最后服务器现场验证为 **2026-11-07 02:41:43 Asia/Shanghai（UTC 2026-11-06T18:41:43.152877+00:00）**，本次文档收尾没有再次连接服务器，不能将归档时刻当成新现场检查。用户先授权只读，随后明确授权代理执行本次必要写入与配置修改；代理通过用户已登录的阿里云 Workbench 浏览器终端操作，没有直接 SSH。网站侧准备完成，真实客户端保存/重载尚未执行。本轮文档更新不提交、不推送、不合并，完成后暂停，不继续服务器、客户端、监控或跨对话派工。

### 固定来源、配置与可转交材料

- 实际 origin：**https://account-test.racepick.cn**。沿用候选 `7c5f53fc366b7af555214846`，服务器清单内112文件完整性通过；原 ZIP SHA256 `6c0ff251985638c62a232689a9aa3a3fd568544f2b8ad812e567e342bcef2648`，11220353 bytes；CANDIDATE SHA256 `13545e697ca7dfcf0fb68f4f52e8b4003474c3accb4586419aaafd8fc096fe3b`。封存 `source_commit=null`，base `bfcf97e1511ee3d418a1f558c30a3ba0148d5286` 不是完整候选源码；不检出base冒充交付、不倒改元数据。没有修改应用代码、重建候选或修改Nginx。
- 本次仅改变 `/etc/racepick-account-test/service.json` 的语义开关 `cloud_writes:false→true`，原子替换并保留UID995/GID986/0600；启用后配置SHA256 `b36e1842692f8f47ea9ecc1c95c02969742852cfa998750ae1038731096817f3`。同一state_root及GuestStore/native/业务Store保持，只有隔离服务短停/重启，其他服务PID保持。
- 最后健康：`enabled=true/cloud_writes=true/mail_mode=file/image_policy=disabled/ocr_enabled=false/production_business=false`；A ready，B–E pending。business6/global_profile1/guest1/native_account1保持，coverage0/global_score0为A-only正常范围，不补迁移。固定五份JSON、两服snapshot及Global dataset详见[机器回交](MINI_ACCOUNT_PROFILE_WRITABLE_HANDOFF_20261107.json)，不取维护工作簿或正式活动成绩。服务仍未开机自启；证书自动续期/后续加载未在本轮验证。
- [本轮机器回交](MINI_ACCOUNT_PROFILE_WRITABLE_HANDOFF_20261107.json)是浏览器终端结果的本地整理，不冒充服务器私有回执的逐字节下载副本。原件与可转交ZIP在外层 `offline-evaluation/mini-account-write-readiness-20261107-01/`；包名 `RacePick-Account-Profile-Writable-Handoff-20261107.zip`，**15139 bytes / SHA256 `ea5c04b0dfb75135b1e30c7eea14110933dc42c13cee600081508f2930b91b39`**。这是资料包，不是新应用候选；包含客户端说明、JSON校验清单及原v2准备ZIP。原v2准备包7223 bytes / SHA256 `8d56f31e4ed22cd643d3cac9b31b5d8c4ad116576ca811549c9e068ce431aac0` 已完整读取并核验；未带v2的历史材料保留。

### 现场核验、状态保护、备份与失败证据

- 真实Linux现场只读库核验：唯一player 1；业务sessions4、native sessions4、native operations2、guest sessions2；CN/Global profile行均0，三库schema匹配原隔离标记，当时无WAL/SHM/journal。这是当时服务器行计数，**不是本轮认证profile GET结果**；客户端写前仍须GET两服，不假定现在仍为空，不用两个null证明同步。未重建账号、重跑testuser19/初始化、迁移、删除标记或恢复旧库。
- 仅短停 `racepick-account-test`，以UID995/GID986、独立断网子进程复用原 `backup_stopped/restore_stopped`；当前三库、标记、签名状态和快照共15文件，在原状态、新备份及全新独立恢复目录逐字节一致。备份 `/var/lib/racepick-account-test/backups/pre-profile-write-20261106T183622Z`，独立恢复 `/var/lib/racepick-account-test/restore-drills/pre-profile-write-20261106T183622Z`。从未用恢复副本覆盖当前库；initial15、pre/post-test-account19及所有旧备份、会话、operations继续保留。私有备份/outbox/签名key未下载或打包。
- 私有现场证据目录 `/root/racepick-deploy/account-write-backup-20261107-__pgcufi`：原 `receipt.json`、`backup-private.log`、`writable-runtime-receipt.json` 保留；最终 `writable-runtime-receipt-v2.json` 与 `closeout-failure-diagnosis.json` 记录收尾及失败诊断，最终标记 `RPA_WRITABLE_CLOSEOUT_V2_OK`。回退工具 `disable-cloud-writes.py` 已实际执行并验证：只关闭cloud_writes、重启此隔离服务，保留账号/新增车库/operations及原state_root；之后重新启用。后续回退同样不能恢复旧库覆盖新增。
- 一次收尾把会维护限流预算的匿名门禁读取误纳入“所有文件字节完全不变”断言，失败保护已自动关写。逐表只读比较确认：仅 `guests/guests.sqlite3` 的 `budgets` 表变化（观测行数5→1），账号库/原生库所有表、其他guest表、schema、标记、快照和签名文件均保持。修正保护判据后再次启用并收尾通过；没有清预算或恢复旧预算，行数变化不证明日额度恢复。失败命令/现场证据保留，不把初次收尾写成成功。浏览器新版输入超时与未提交半行命令也未冒充核验结果，旧版终端验证可控后才执行后续操作。
- Nginx站点/代理/限流文件均匹配原step20渲染；最初本地指纹差异来自WindowsPath生成Linux include路径的分隔符，改本地比对后匹配，未覆盖现场文件。Nginx精确profile路由允许转发PUT，应用方法白名单和cloud_writes门禁负责权限。网页入口200，网页与原生双服未认证profile读取401；原生Origin/Cookie/OPTIONS403，排除feedback404，检查响应均no-store。保留精确Host/TLS、64KiB、5r/s burst10及Retry-After语义；未做PUT探测或限流饱和测试。

### 精确路由、分层证据与客户端接管点

- 原生：`GET/PUT /api/mini/account/v1/profile?server=cn|global`；恢复：`GET /api/mini/account/v1/operations/{original_key}?action=profile-save&server=cn|global`。仍为rpa1 Bearer + X-Account-ID；网页入口 `/` 与 `GET/PUT /api/me/profile?server=cn|global` 继续Cookie/Origin/CSRF/X-Account-ID/X-Profile-Save:explicit，身份不桥接。源码/fixture证明同Store接线，真实非空网页/原生同记录比较仍待W4。
- 本轮Windows既有边界/服务fixture19/19通过；历史Linux候选离线fixture不重新冒充本轮测试。本轮真实Linux证据为来源/config/schema/状态核验、当前备份和独立恢复、开/关/重开及匿名门禁。**真实PUT=0、代理认证profile GET=0；真实保存/重载/409/原key恢复未验收**，回交样例仅契约/fixture。
- 用户已确认完整镜像开发者工具和iPhone真实隔离player只读、双服读取、不自动导入、分服草稿/星级/OC/计算/页面往返通过，保存禁用。保留旧手机只读工程 buildId `4ce602ec7f6f5746ac25` / planId `mini-account-mirror-phone-20261107-01`。**“OC=true 用户确认检查通过”**；万达OC=true检查后误触关闭才使原JSON最终false，原证据未改，不据此宣称云保存通过。
- 客户端由用户在新对话接管 `miniprogram-v1`；保留原AccountClient/CloudProfile/ProfileStore和198999a共享模块，新建独立写验收plan/输出/草稿作用域，不直接改旧只读工程，不只改allowCloudWrites。新plan须核固定来源、实际可写health、validator/request/save facade/UI及身份/服别隔离；保留旧工程、身份、游客与草稿，不自动导入、不自动登录/重试/保存。用户已获可直接复制的客户端接手提示词；本对话未改小程序或派任务。
- 首轮仅W1/W2：先认证GET两服，若已有新记录停下核来源、不清库；W1分别由用户保存合法空CN/Global并各GET重载，区分null/已保存empty与独立revision；W2保存CN f5★5、Global ssc/万达且万达OC=true，再各GET重载。最多计划4次成功显式PUT、6次认证profile GET（含写前2次），不是重试预算；真实保存只由用户在新客户端点击。游客导入、W3冲突双份、W4网页/原生非空同记录比较另列，先开发者工具再手机。
- 未知结果只查询原key/action/server；404不证明未执行、不换key重发。429遵守Retry-After、不假定预算恢复或自动重登；503/读取失败不当空库。退出/再认证/撤销专项、角色/邮件/注册/图片/统计/B–E、生产、微信后台、上传提审发布、开机自启/证书续期不随本轮扩展。此处暂停，不因归档继续执行。

下方2026-11-06及更早记录均按其历史阶段阅读，未被删除或倒改。

## 2026-11-06 实时交接：小程序A账号/双服云车库公网只读准备完成，真实身份与车库验收待客户端（批次20261105）

所有服务器操作由用户逐步执行并回传，代理没有登录服务器。本批原始服务器回执保存在外层offline-evaluation/mini-account-isolation-20261105-01；step20未附完成时间戳，本文归档日不冒充现场观测时刻。用户要求已定范围内直接给操作、不再二次询问；文件上传只用服务器文件管理系统，ZIP优先、本地/服务器文件名相同，不使用本机PowerShell。本批无Git提交推送/合main，无新监控、公告、清理或跨对话派工。

### 当前可用范围及来源

- **实际origin：https://account-test.racepick.cn**。用户step20回传ACCOUNT_PUBLIC_HTTPS_A_READONLY_READY_20，回执 `/root/racepick-deploy/account-https-api-20-4ii2869y`。公网health200/ok、固定五JSON SHA/bytes、未认证A session401 SESSION_REQUIRED、双服profile401 ACCOUNT_SESSION_REQUIRED/no-store通过，原生Cookie/Origin/OPTIONS拒绝，注册/找回/B–E/统计等排除路径404。只修改该独立站点与新代理/新限流文件，Nginx备份及独立配置副本通过，所有原/新服务PID及原网站指针保持。
- 固定交付 **7c5f53fc366b7af555214846**，原ZIP SHA256 `6c0ff251985638c62a232689a9aa3a3fd568544f2b8ad812e567e342bcef2648` /11220353bytes，CANDIDATE.json SHA `13545e697ca7dfcf0fb68f4f52e8b4003474c3accb4586419aaafd8fc096fe3b`。**source_commit=null**，base=bfcf97e1511ee3d418a1f558c30a3ba0148d5286仅历史基底，不是完整候选源码；不倒改封存来源。发布 `/opt/racepick-account-test/releases/7c5f53fc366b7af555214846`，五共享模块仍匹配198999a。
- 实际配置 **enabled=true/cloud_writes=false/mail_mode=file/image_policy=disabled**。A ready，B–E pending；新服务只加载A，coverage_schema0/global_score_schema0不是缺迁移，不为补0复跑旧迁移。business6、Global profile1、guest1、native account1实际通过。固定snapshot CN593ecc7222ceea5856b2f576b4f5bca8 / Global e29f52e7f81c3e337985bf05dedb7e88仍是原固定五文件，不是正式活动成绩指针，不取维护工作簿。
- native白名单：新origin POST guest session、GET snapshot，A GET/DELETE session、POST login/reauth、GET双服profile、GET原operations恢复。PUT框架存在但cloud_writes=false拒绝，只读阶段不发送。公网注册/验证/重发/重置/邀请、association别名、B–E、图片/OCR、统计和任意管理路径仍关闭。必要网页账号页与原生共用一个隔离Store，保持网页Cookie/Origin/CSRF、原生rpa1/X-Account-ID的身份分离，不建立永久微信绑定。

### 隔离与备份证据

专用Unix用户racepick-account-test UID995/GID986；数据 `/var/lib/racepick-account-test/state`、私有配置 `/etc/racepick-account-test`。实际systemd/mount namespace及内核限额：仅state为持久RW，配置/固定快照/标记/签名key readonly，正式业务/旧guest/安全配置不可见；memory.high256MiB/max512MiB/swap0/cpu50%/pids32。新服务仅回环8012，Nginx精确HTTPS路径代理，服务**未开机自启**。源旧微信应用的AppID/Secret只在服务器内私有复制，未入本地/Git/包/聊天，17B在真实UID/挂载+独立断网环境解析通过；不是微信鉴权验收。

用户step19在服务器交互输入新测试密码，经原register/verify处理函数+file outbox本地消费邮件token，创建**唯一隔离player账号1个**，非生产账号、非真实邮箱收件验证。用户名留用户及服务器私有operator marker；不在本交接放邮箱、密码、token或备份。创建前后私有备份/独立恢复均通过：pre/post-test-account-19；初始initial15也保留。操作失败/未知不重复注册或邮件，不恢复空旧库覆盖新账号。step20后身份/车库/邮件/操作/schema行保持；双服profile0、无认证会话/微信身份，只有门禁限流预算可能增加。

原网站7241、旧mini-test访客/OCR与guest/bridge35bd加原明确补件维持既有归属；本批没有打开旧业务/访客/队列库、重跑迁移或新增OCR/供应商调用，不清理旧包/备份/失败证据。旧iPhone基础OCR试次02用户验收是独立历史事实，不在本批重传。新origin不是替代旧OCR origin：必须新建该origin的真实父访客，不复用旧mini-test Bearer/code或破坏其transport/草稿。

### 下一阶段边界

[可转交小程序侧的说明](MINI_ACCOUNT_A_READONLY_HANDOFF_20261105.md)、[无凭据固定JSON](MINI_ACCOUNT_A_READONLY_HANDOFF_20261105.json)、[完整网络阶段回执](MINI_ACCOUNT_NETWORK_PREPARATION_RECEIPT_20261105.json)。小程序本机交接仍见miniprogram-v1/docs/HANDOFF_ACCOUNT_NETWORK.md（只读复核本机dd8731f，工作树无修改，本批未改客户端）。只把安全交接材料由用户转交，不自动派工。

**尚未验收：真实微信交换、账号登录、认证双服GET、网页/原生真实记录同步、暂存/保存/重载/冲突/退出/身份变化、手机账号。** A ready和匿名401仅证明组件/门禁，不替代认证权限验收。新origin是否登记微信request合法域名待用户/小程序侧核实，网站侧未操作微信后台，不关闭校验绕过。接收后先核来源/组件，再新origin的新真实父访客→用户私下输入隔离邮箱/密码→仅登录/双服只读证明不导入。客户端cloudWrites及服务端cloud_writes保持false，不发PUT。未知结果保留原key/action/server，仅查询原操作，恢复404也不换key重放。只读证据后再明确写范围，最后手机步骤。固定AccountClient/198999a ProfileStore与完整镜像保持，不用探针替代产品。

证书SAN仅account-test.racepick.cn，DER SHA `3dfc725867c9858943b69b63c31350f46b583b27ccc21740b5790366909d3d91`，有效期2026-11-05T03:35:07Z—2027-02-03T03:35:06Z（有效期字段不是执行结束时间）。自动续期及Nginx后续加载尚未验证，不声称长期生产运维验收。正式账号库接入/迁移/恢复、真实邮件、生产启用、小程序上传/体验版/审核/发布均不据本批扩权。

下方旧“暂停/账号未接通/手机OCR待验收”等均按各自历史阶段阅读，不续跑旧部署。

## 2026-11-05 最新交接：iPhone基础OCR已验收，下一阶段仅A账号/双服云车库隔离联网准备；本对话文档推送后暂停

用户最新指令：只把最新状态和账号/云车库准备范围更新到主repo本文件与INDEX，单独提交推送后暂停，由新对话接手；不继续开发，不操作服务器/微信后台，不发图或新增审核/邮件/账号请求。本轮仅只读查看仓库资料并更新这两份文档，未重新核生产进程/健康/备份调度；下述线上信息沿既有用户回执，不冒充2026-11-05实时服务器检查。未跟踪排查回执等资料保留，不自动纳入本次提交。下方2026-11-04“手机待验收”“原生关闭”等段落均按各自历史阶段阅读。

### 最新已核资料与验收边界

- 网站/运维最近成功回执仍为网站7241d9d67cc99178bd7d2d14、原生35bd5c5d2e618b555de3a70c加已记录的单文件桥依赖补件；CN原生OCR开启，Global OCR及账号/B–E未随其开放。保持原唯一监督者/worker/JobStore、安全schema1及原正式CN/Global成绩指针；不续跑已完成的OCR部署、schema迁移或维护发布，也不恢复旧库回退。固定数据/83图目录来源仍见[CN服务端交接](MINI_OCR_CN_CLOUD_HANDOFF_20261104.md)与[原字节绑定](MINI_OCR_CN_BINDING_20261104.json)。
- 用户已回交iPhone基础OCR通过；本轮只读核对了工作区 `miniprogram-v1/docs/PHONE_OCR_ACCEPTED_20261104.md`（客户端验收提交089f4a8）。对象为iPhone14/iOS27.0.1/微信8.0.79/SDK3.17.6，独立 `mini-phone-ocr-20261104-02/phone-ocr-02`、buildId c49501bc653f5445f8bf。用户脱敏报告显示实际uploadFile1次/HTTP202、已确认应用五图，内容与顺序逐项匹配；上传UTC15:52:44.760—15:52:44.997，即2026-11-04北京时间23:52:44.760—23:52:44.997。原材料/摘要位于外层mini-phone-ocr-20261104-02，未经本对话重新发图或操作手机。仅本台设备/该获准截图的基础相册识图与确认路径通过，不泛化为Android、其他截图准确率、相册拒绝/取消、前后台/切网/恢复/到期或账号验收；237毫秒是上传回调时长，不是OCR总耗时/SLA。供应商原始回执、账单及留存删除时点未由手机报告独立核验。
- 早期 `mini-ocr-synthetic-once-01/02` 与上述 `mini-phone-ocr-02` 是不同工程/授权。18:52首次合成上传错误分类未留存；21:11:25.316—.318合成第二次明确domain_rejected/无HTTP响应。当时后台及工具uploadFile列表均曾为空，用户后来补入精确域名；后续手机资料记录完成微信关闭重开及新的独立02试次后通过。不能把相关性写成唯一根因已证为缓存/重启，也不能反推首次失败同因或0费用。旧预约、失败记录与授权均保留，不重用、不恢复任务或继续试图。
- 客户端A联网准备最新本机HEAD为dd8731fa154d44da53bbdb955d23549e1354e3b8，本轮只读定位了 `miniprogram-v1/docs/HANDOFF_ACCOUNT_NETWORK.md` 与 `ACCOUNT_NETWORK_PREPARATION.md`，不宣称已推远端。本次不提交/推送客户端分支、不把其功能合入main。客户端140项测试和官方SDK关闭工程编译为该阶段已有证据，本轮未重跑、未新增真实网络业务调用。
- 独立未认证GET `https://mini-test.racepick.cn/api/mini/account/v1/session` 曾返回404、未跟随重定向。原观察UTC为2026-11-04T16:05:35.927127Z，**北京时间是2026-11-05 00:05:35.927**，不是11月4日16点或午夜前。证据在外层 `offline-evaluation/mini-account-network-prep-01/unauthenticated-account-gate.json`。这仅确认该时刻该路径404，不证明账号组件/认证/权限验收通过；尚未回交可用账号入口的新固定交付。

### 新对话的网站侧账号/云车库准备范围

1. **固定契约与隔离架构**：以[原生A契约](MINI_ACCOUNT_CONTRACT_A_20261103.md)、[双服云车库](GLOBAL_PROFILE_CLOUD_20261103.md)为准，先核现有实现和归口，复用既有算法/AccountClient/ProfileStore，不另发明协议。现mini_guest/mini_ocr_guest是轻量访客/OCR入口，不能仅增加Nginx账号路由便声称已加载账号组件。需回交实际origin、固定代码/交付、启动器/进程权限/数据库归属及A可用前缀；未核实的DNS/TLS/新origin不编造就绪。不得因此启停原OCR、另开模型或改动原队列。
2. **父访客与账号分离**：沿真实微信交换由服务端校验父访客，账号Bearer为rpa1并按契约使用X-Account-ID，TTL不晚于父访客；角色、撤销、再认证和父身份变化由服务端校验。不能升级访客权限、桥接网页Cookie/Origin/CSRF或永久绑定微信身份，不能复制正式账号库、旧测试状态、密钥到客户端/包/聊天。
3. **同一隔离库与双服语义**：本阶段使用新独立测试账号与隔离业务库，网页和原生必须对同一隔离库的CN/Global记录读写，不用两套库假称“同账号/同车库”。确认A状态及profiles.cn/global均account、Global schema1/OC与独立revision；旧库不靠启动自动迁移，503/组件缺失不当空车库。登录/GET不导入，null与合法空车库分开；正式账号/库接入、迁移、恢复和生产启用另明确授权。回交五份固定运行数据与schema/capability来源，不改维护工作簿/正式成绩指针或共享算法模块。
4. **最小路由与安全**：列清POST访客session、A GET/DELETE session、auth/login/reauth、GET/PUT profile?server=cn|global、原operations/{key}?action及profile-save的server参数。注册/验证/重发/重置/邀请码如需启用，另列准确范围；B–E、图片证据/统计不随此启用。保持HTTPS、精确Host/可信代理/IP、no-store、Cookie/Origin/OPTIONS拒绝、JSON64KiB和签发/登录/邮件限流，不代理任意网页路径、不放通配Origin。
5. **测试账号与邮件**：提供新隔离账号的安全准备方法，首轮可用隔离file outbox，注册/验证由用户明确操作，不拿正式账号测试关闭入口。真实邮件另明确地址/范围/次数及发送不确定恢复策略后授权，不自动反复重发/开付费服务；不回传密码或邮件一次性token。
6. **恢复/冲突与固定回交**：准备非秘密成功/错误样例和模拟/开发机/Linux/现场分层证据，覆盖密码错误后父访客仍可用、会话失效/角色撤销、同key登录/再认证恢复、退出后迟到结果不能复活、双服null/空车库、revision冲突双份保留、跨服key拒绝及组件关闭/旧库兼容。未知结果不等于未执行，不换新key重放密码、邮件或保存。回交只含origin、固定来源/SHA、隔离状态、开关/schema及脱敏证据，不含AppSecret、密码、token/code/session_key/OpenID或正式账号数据。

### 客户端已完成与后续验收顺序

客户端已修密码错误401误清父访客，只有固定父会话失效码才清父身份，账号token401仍清账号缓存；登录install前核角色/有效期/真实平台父association与generation，身份变化清组件缓存，旧contract/迟到响应不覆盖新身份。未知auth保留内存原key/action，切表单/重开页不丢号盲发，不存原密码/邮件token，恢复404也不自动重发。独立account-probe默认enabled=false/cloudWrites=false，不初始化API或业务请求；开启后仅A基础白名单，无图片/注册/邮件/B–E，草稿独立planId前缀，不读写原游客/主应用账号草稿。既有fixture完整镜像页继续复用原AccountClient/198999a ProfileStore，本轮测试页不替代最终网页镜像产品。

网站固定交付回交后，先核来源/组件及真实访客→账号分离；用户自己输入隔离邮箱/密码，先真实登录与双服只读，证明login/GET不导入；再按明确写范围验证暂存、显式保存、重载、冲突、退出与身份变化，最后给手机步骤。当前真实账号/云车库/邮件/手机账号均未验收；不再要求复测已通过的手机基础OCR。

**暂停交接**：本轮仅提交推送本文件和INDEX，完成后本对话暂停。新对话先读根CLAUDE/context、本节和客户端交接，核工作树/远端，先总结现状与方案；后续实现/现场范围按用户新授权推进。保留全部业务数据、访客状态、队列、备份、旧发布、测试数据、工作簿和未跟踪文件；禁止reset --hard/clean、自动同步工作簿、代码包覆盖正式成绩、重复旧迁移或复用已消耗上传授权。服务器仍由用户一次一步执行回传，不把本条当作批量写/部署/登录/注册/云写/邮件/微信后台/上传提审发布/清理/监控或跨对话派工授权。

## 2026-11-04 18:52上传事件只读首查：日志无匹配、现存队列无该SHA，仍不能判未到达或0费用

用户回传READ_ONLY_INCIDENT_STEP_DONE：查询窗口18:50:59—18:55:00 CST、合成图SHA82dafe81e5f48f50fe4ab42eec79499627be61efcfaea3631964bc691a30c54f。磁盘Nginx站点及OCR proxy均access_log off；stage1 proxy片段未写off不等于其父站点开启日志。扫描报告scan_complete=true，匹配事件0，域名error日志仅3行；此为所选文件/解析器范围，无完整请求体接收字节证据。以原owner只读query_only查队列：safety_schema1，保留记录中该SHA全时段0、窗口0；未打印owner/key/请求正文/凭据。该schema未持久化供应商RequestId/计费证据，正常TTL可移除历史行，故结论仅“尚未取得到达/任务证据”，绝非“确认未到达/没送审/0费用”。本轮没有HTTP请求、上传、恢复、清理、迁移、服务修改或供应商调用。

后续只读协调方向：客户端保留本次失败原报告及授权预约，不重跑uploadFile/resume；核失败当时origin/路径（去query）、工程标识6b16fa597b83a4092e85与AppID配置一致性、uploadFile登记项及校验开关元数据。现在重新锁定的uploadDomainDeclared=false/maxUploads0是失败后保护动作，不能倒推失败时未登记或未授权。具体网络分类已遗失，后来代码的新诊断无法还原本次错误，不通过额外调用补证。供应商既有调用/费用记录由用户按原权限只读查同窗并脱敏回传；只有日期聚合或无可关联明细时仍记费用未知。未追加生产操作或推送本次排查文档。

## 2026-11-04 小程序单次合成图上传失败回交，仅授权只读排查，不得重传

用户转交客户端d557a26材料：一次wx.uploadFile在2026-11-04T10:52:59.371Z（CST18:52:59.371）返回WX_REQUEST_FAILED；唯一授权图SHA82dafe81e5f48f50fe4ab42eec79499627be61efcfaea3631964bc691a30c54f/87085字节。客户端称合法uploadFile域名已添加、真实会话/双服固定快照/83图目录已检查；这些是客户端回交，不扩为手机相册/上传或OCR五图验收。调用是否到达Nginx/应用、是否产生任务/供应商调用/费用未知，不能记成功上传或0费用。客户端once预约保留、maxUploads锁0，无查询/恢复/取消，不得用新owner/key重传或复用授权；先前服务端18:03单次合成审核是不同阶段/图片，不可混算本次18:52尝试。

本轮仅准备用户执行的只读18:50:59—18:55:00 CST日志/该SHA任务摘要查询。上传代理原access_log off，因此没有访问日志不能证明未到达；标准combined的body_bytes_sent是响应体字节，不是收到的图片字节。命令只输出时间/路径/状态/固定错误类别及按SHA过滤的job安全字段，不输出完整query、owner/key、token/code/OpenID、原文或图片；以原queue owner mode=ro/query_only查现有jobs/safety_checks，不实例化JobStore，不清理/迁移/恢复或调用站点/供应商。该schema未持久化provider RequestId或账单跟踪，TTL可清理旧行，查无行不能证无调用/费用。现场输出尚未回传；缺失根因不猜，不改服务/后台或追加上传，不自动提交推送本轮排查记录。

## 2026-11-04 按功能Git归档与推送，不重新部署；小程序侧已由用户转交

用户授权“分功能推送一下”，并确认小程序侧已转交；不据此推断客户端开发/真机验收完成。本轮功能树按白名单拆为：cea43865eb741d4971086efa8a0a4de6e585d83c（baselineCheck SDK/共享安全队列）、5d39af53f776dae6676b222e451679f2f5f41892（原生HTTP桥/原key恢复）、eeb966cd879060b64cb62a5bb68e606bf4e0acb2（离线交付/模板/桥启动依赖修复）、bfcf97e1511ee3d418a1f558c30a3ba0148d5286（阶段文档）；连同既有未推0b97dae已推送origin/feature/map-layout-parser，ls-remote已核。主repo仅归档最新现场交接/原字节绑定及本批Git回执，未把功能分支合入main。当前线上仍是封存35bd加明确补件，不宣称这些新Git提交已重新构包或部署；source_commit=null等历史包元数据不倒改。

提交前Windows本地相关143执行/120通过/23环境跳过，已有SDK专用venv加本机Pillow依赖路径另跑7项全部通过（均mock HTTP，无真实供应商/服务器请求；不能将重叠项简单相加）。新增打包依赖隔离导入回归已包含；仅去掉两纯模块额外EOF空行，未改行为。审查54个功能文件/7个现场文件的显式清单、JSON、密钥模式与diff空白；实际密钥、业务库、工作簿、模型、wheel/ZIP及现场脚本未加入Git，原资料保留。SDK专用venv首次因缺Pillow未能导入，补用已安装依赖路径后通过，未联网安装。详见[Git交付回执](GIT_DELIVERY_20261104.json)。本次没有服务器操作、额外付费审核、公告、清理或新监控。

## 2026-11-04 CN原生OCR服务端正式开启，唯一合成审核通过；真实微信/手机OCR待验收

用户执行最终续开命令回传CN_NATIVE_OCR_ACTIVATED，回执`/root/racepick-deploy/mini-ocr-20261104-35bd5c5d/native-final-nudoqb0h/activation.json`。bridge和guest active并enabled for boot；阿里配置mode live、bridge enabled true、guest image_policy aliyun_baseline。公网CN catalog无token401/no-store、双服snapshot无token401、账号路径404；peer UID996实际socket目录验证CN catalog57876474bd3cd25c283e79a471be99ec76d4e58ed16fa0e2c8ae2a6cdf0b9ced/83图，前次完整maps SHA7b4e180ed199d4319f4b756477039232038043214a9a239d20ac782f97670b54；Global请求明确拒绝。账号/B–E及Global OCR保持关闭，原唯一worker/网页OCR ready，正式CN c815b612a17433f403ae2965000fd74b / Global435d5b40fd1aa4a01753a395f28d1f89保持。backup.timer active；未观察未来定时任务成功，不增设监控或清理。

本轮授权的唯一一次非私人合成图baselineCheck已在native-enable-ddobc7_8阶段明确通过，后续修复/最终命令均无供应商调用，不重试、不额外传图；不据此声称正式启用后用户流量或账单次数。队列schema仅0→1一次，原jobs指纹保留、当时job_count0；完整guest/queue保全在native-enable-ddobc7_8/guest-and-original-queue.tar.gz，实际SHA见服务器preservation.json（尚未回传，不编造）。保持兼容网站7241，不回旧a933/旧队列库来撤销schema，避免丢新任务；关闭时只退原生配置/路由并保留兼容代码/schema1/状态。

实际运行来源为封存v2交付35bd加一个明确记录的运行依赖补件：bridge/backend/map_ocr_production.py取自已校验7241网站，SHA3c8a7d64564da8d7804bd0f35a8aba960ee922d86573af8973c857ec10718872、4495字节，回执bridge-repair-y_eccy1a/runtime-repair.json；原ZIP/SOURCE/manifest未倒改，不能宣称目录仍是零附加文件的原包。开发树builder已修正BRIDGE清单，并通过1项实际打包模块集合隔离导入回归；未提交推送/重构v3包。两次续开间最后公网门禁问题记录为：最终输出首次nginx404、短暂等待后401，说明reload后立即判失败过早；不是新一轮供应商失败。

完成范围仅服务端CN开放、唯一合成图审核和目录/未认证公网门禁。未做激活后的真实微信会话、multipart实图→审核→唯一worker→结果、同key恢复/取消/过期/切网/前后台或iOS/Android验收；供应商通过也不等于OCR五图识别通过。小程序回交见[CN原生OCR服务端交接](MINI_OCR_CN_CLOUD_HANDOFF_20261104.md)与[固定OCR绑定](MINI_OCR_CN_BINDING_20261104.json)。用户后续需独立OCR检查工程，真实uploadFile合法域名/平台声明/隐私提示及获准样图、额外调用按后续授权处理，本聊天不操作微信后台/上传提审发布或向其他聊天发任务。至此停止额外生产操作，保留所有失败/回退/备份证据。

## 2026-11-04 桥依赖与目录已通过，最后公网门禁异常回退，未获得正式开启成功证据

用户回传bridge-repair-y_eccy1a：已从7241网站补入bridge/backend/map_ocr_production.py，SHA3c8a7d64564da8d7804bd0f35a8aba960ee922d86573af8973c857ec10718872/4495字节，不改ZIP；BRIDGE_CATALOG_READY确认CN目录57876474bd3cd25c283e79a471be99ec76d4e58ed16fa0e2c8ae2a6cdf0b9ced、83图、maps SHA7b4e180ed199d4319f4b756477039232038043214a9a239d20ac782f97670b54、Global false。guest本地catalog401已通过，后续Nginx测试/重载执行后公网cn_catalog_gate断言失败，命令未输出实际status/body；reload异步生效竞争为可能原因，不可写成已确认根因。回退disabled配置/原site，bridge clean stop；rate/proxy新文件按设计保留，后续必须比较复用，不再“不存在”断言。schema/供应商探针均未重跑。下一步仅续已授权最后激活，明确打印实际HTTP、给reload有界就绪等待，失败自动关闭并保留路由诊断；无新付费/迁移。

## 2026-11-04 桥故障确认缺少map_ocr_production依赖，本地打包修复通过，现场续开待执行

用户journal确认ModuleNotFoundError backend.map_ocr_production；原站三服务及timer active、bridge inactive、审核/桥/guest均disabled，once标记保留、正式公网health和指针保持。已本地给build_mini_ocr_delivery.BRIDGE补map_ocr_production，并新增只使用实际BRIDGE文件集隔离导入启动依赖的回归，1项通过；不扩大为Linux/真实供应商新验收。拟现场仅补缺失文件，来源已激活7241网站backend/map_ocr_production.py，封存manifest SHA3c8a7d64564da8d7804bd0f35a8aba960ee922d86573af8973c857ec10718872、4495字节；这与开发树文件并非同字节，严禁拿开发树替换或改写网站文件。将原封存ZIP保留，在运行bridge新增该依赖并另记runtime修复回执，不倒改发布ID/manifest。后续只复用已有schema1及唯一审核通过证据，启动桥/CN网关/Nginx，无任何审核调用、迁移或业务库恢复。现场修复/续开尚未执行。

## 2026-11-04 schema1与唯一一次供应商合成审核已通过，桥未就绪，原生OCR尚未开放

用户执行合并命令回传：保全目录native-enable-ddobc7_8；QUEUE_PRESERVED_AND_SCHEMA_READY为0_to_1/jobs_preserved=true/job_count0；SINGLE_BASELINECHECK_APPROVED明确通过，唯一授权的非私人合成图审核调用已消耗，不得重试，保留base下baselineCheck-once-20261104.reserved标记。随后guest UID通过socket取catalog等待20次仍Bridge not ready，循环只捕获OSError/ValueError未输出具体原因，需桥journal定位。失败在guest image_policy切换及Nginx新路由之前；回退路径已运行恢复disabled配置、停止桥并恢复原服务/timer，实际健康待只读回传。schema1保留，不恢复旧队列、不重复迁移或付费。待核/修复仅桥启动与其目录访问，未知原因不得猜作已确认。

## 2026-11-04 用户明确授权schema/桥/一次非私人合成图审核及CN原生OCR上线，合并命令待执行

用户授权三项实际上线、限一次非私人合成图baselineCheck、不自动重试；保留业务/访客/原队列/备份，Global及账号/B–E关闭。已准备外部合并脚本offline-evaluation/mini-ocr-gateway-release-20261104-01/deployment-enable-native-22.py（不改封存v2）。计划停原生/网页准入后仅在原队列无进行中任务时短停唯一worker，保全guest/queue，再显式prepare_safety_schema 0→1并核原jobs指纹保持；schema1已存在则不重复。恢复原站后，写全局唯一一次调用保留标记，实际owner用已有SDK对内存合成图最多一次review（含必要临时OSS上传），无重试；只有明确通过才启动桥、peer UID目录检查、guest aliyun_baseline及新增CN精确Nginx路由，原session/snapshot预算和正式成绩保持。成功将bridge/guest设开机启用；失败保持兼容网站/schema1，退disabled配置/原站路由，不恢复旧DB、不重试付费。用户已获知CN开放后真实用户上传会正常产生按量审核费。脚本仅本地AST语法检查，不冒充生产执行；后续以用户回传为准，手机/真实微信OCR未验收。

## 2026-11-04 桥单元安装静态检查完成，用户要求直接推进真实上线

用户回传BRIDGE_UNIT_PREPARED_STATIC：单元loaded/inactive/dead/MainPID0/disabled，User racepick、Group racepick-mini-test，High256MiB/Max512MiB/Swap0/CPU100%/Tasks32，关键保护字段yes/strict；前后静态verify退出成功。现有cloudmonitor.service的KillMode=none及旧/var/run警告非本桥问题，未修改其单元。密钥/配置metadata保持，无队列迁移或供应商调用。用户明确不再逐项重复验证、尽快上线；后续不循环离线/静态测试。真实OCR仍受此前明确禁止迁移/启动桥/真实传图付费及原生关闭约束，需要一次明确新增上线范围后再给用户合并的必要部署步骤；静态完成不等于实际桥/供应商/公网OCR已启用。

## 2026-11-04 桥单元安装及静态检查获授权，待用户执行

用户授权继续准备桥服务单元并静态检查，仍保留现有密钥/数据，排除队列迁移、桥启动、真实传图/付费和公网原生OCR开启。拟严格对照封存bridge.service.in与既有prepared单元，核路径/UID/GID和disabled配置；在systemd-analyze verify通过后只新建/etc/systemd/system/racepick-ocr-bridge.service（已有单元/链接/drop-in则停并保留），root0644，daemon-reload后核loaded/inactive/disabled及关键隔离/资源字段，不enable/start。不会执行单元中的--allow-live-calls入口，配置仍false/disabled；不读取密钥正文或打开队列库。尚待用户执行回传，不记单元安装或静态检查已完成；静态验证不等于实际运行隔离/资源/供应商验收。

## 2026-11-04 disabled审核/桥配置已安装，离线校验通过

用户回传DISABLED_CONFIGS_READY及运行owner的纯解析检查结果：safety mode=disabled、service=baselineCheck、region=cn-shanghai；bridge enabled=false、allowed_uid996/socket_gid987。实际/etc/racepick-ocr-safety/aliyun-baseline.json和bridge.json均UID999/GID988/0600，对照原prepared候选及封存模板与现场路径完成安装，未改已封存包。检查只读这两份配置，credentials_loaded=false、queue_opened=false、provider_called=false；既有凭据文件stat身份/属主/权限/大小/mtime前后保持，未读取密钥正文。桥仍inactive、guest image_policy disabled，未迁移队列/启服务/传图/付费。此配置准备任务已完成，无API鉴权有效性或真实OCR通过证据。后续单元准备、队列schema、启动桥和联网调用均依后续明确授权逐步处理，不自动推进。

## 2026-11-04 仅disabled审核/桥配置安装获授权，待用户执行

用户授权继续准备disabled审核配置与桥配置，保留现有密钥/数据，禁止队列迁移、桥启动、真实传图/付费和原生OCR开放。拟复用先前prepared-configs的aliyun-baseline.json/bridge.json，先逐项对照封存包模板及实际guest UID996/GID987、snapshot路径；仅新建/etc/racepick-ocr-safety下两JSON（任一已存在先停止保留），owner999/group988/0600。随后以实际owner调用纯配置解析器离线校验，不初始化JobStore、不读凭据或调用供应商；目录与凭据仅stat前后比较。不开systemd单元、不改guest配置、不开关。尚无用户执行回传，不记配置已安装。

## 2026-11-04 baselineCheck凭据私有落盘及离线权限检查通过，仍未联网调用

用户回传OFFLINE_FORMAT_AND_OWNER_CHECK_PASSED、GUEST_ACCESS_DENIED_CHECK_PASSED及CREDENTIALS_PREPARED_OFFLINE。实际/etc/racepick-ocr-safety目录UID999/GID988/0700，aliyun-baseline-credentials.json文件UID999/GID988/0600；已由实际运行owner执行适配器read_credentials，仅离线检查格式、owner、私有mode等，访客用户os.access读取权限检查为拒绝。未在聊天/文档保存任何密钥值、长度或哈希；文件已存在，后续不得重跑创建命令覆盖或要求用户回传正文。桥inactive、guest image_policy disabled，经本步命令复核；未启动桥、改运行开关、迁移队列、外发图片或付费调用。RAM最小策略绑定为用户确认，密钥有效性、供应商鉴权/实际权限尚未联网核验；不能把离线检查当成阿里接通或OCR验收。首次落盘命令因/dev/tty以r+打开失败，在任何输入或落盘前退出；改w模式后用户成功执行，错误证据保留。当前凭据准备任务完成，后续配置/接入按新授权逐步执行，不自动推进。

## 2026-11-04 RAM准备用户确认完成，凭据私有落盘命令待执行

用户明确回传专用用户已创建、密钥私下保存、两项最小权限已绑定，属于用户确认，未以真实API调用验证授权。随后授权由用户执行隐藏输入写服务器凭据并核权限；仍排除真实传图/付费、桥启动和原生OCR开启。命令拟核桥inactive及guest disabled，仅新建/etc/racepick-ocr-safety/aliyun-baseline-credentials.json（已存在则停止保留），目录改为racepick主owner/group且0700、凭据0600，适配器read_credentials以实际owner离线读格式/权限，并核guest用户不能读取；不输出密钥、长度、哈希，不读取或输出其他秘密，不更改运行配置。尚待用户执行回传，不能记凭据已落盘/有效或供应商接通。该目录owner调整服务于原定UID999的未来读取，不能宣称与同UID网站存在独立账号隔离。

## 2026-11-04 新阶段仅授权准备baselineCheck专用RAM与凭据配置

用户要求先说明专用RAM权限、密钥准备及私有存放路径，仍由用户逐步执行回传；未授权真实传图/付费，原生OCR继续关闭。已对照当前适配器和阿里官方DescribeUploadToken/ImageModeration授权页核两Action及Resource*；策略不能把ImageModeration进一步限制为baselineCheck（官方未列此服务条件），baselineCheck由程序固定。拟让用户先在RAM控制台创建专用程序用户、附加两Action自定义策略、生成并私下保管AccessKey；尚无用户完成回传，不记创建/绑定/密钥落盘完成。当前适配器只接收access_key_id/access_key_secret两字段文件，不支持直接填STS三元组。计划路径/etc/racepick-ocr-safety/aliyun-baseline-credentials.json、运行owner racepick UID999、文件0600；现目录root700，后续落盘须显式准备可由该UID遍历的目录权限，不能只chown文件。现在不改服务器、不启桥、不改disabled配置、不迁移队列；本轮无供应商API调用。

## 2026-11-04 兼容网站7241与disabled访客网关35bd上线，公网只读收尾通过

本次服务器操作全部由用户逐步执行回传。最终READ_ONLY_CLOSEOUT_PASSED确认：网站current及accounts PID218390、原唯一OCR监督者PID218388的cwd为`/opt/racepick/releases/7241d9d67cc99178bd7d2d14`；guest PID218393的cwd为`/opt/racepick-mini-ocr/releases/35bd5c5d2e618b555de3a70c/guest`，三者active/running。网站沿a933仅叠加批准6个兼容文件；封存源码source_commit=null，不能把base提交当此次新源码提交。公网health200/ok/no-store，schema6/coverage2/global-profile1/global-score1；正式CN c815b612a17433f403ae2965000fd74b、Global435d5b40fd1aa4a01753a395f28d1f89保持，国服写开，原网页OCR enabled/worker ready。此次health未回Global写开关，不据旧备份推断实时状态。

原生图片policy disabled；双服公网snapshot无token均401/no-store，OCR catalog404（该404未返回Cache-Control，不声称所有关闭响应均no-store）。bridge inactive/dead/MainPID0；未迁移识图安全schema、启桥、配置阿里密钥或付费传图，账号/B–E和微信后台/上传提审/发布不在本次范围。guest实际High128MiB/Max256MiB、Swap0/CPU25%/Tasks32；原OCR640/768MiB、Swap0/CPU100%/Tasks64保持。该资源观测非高并发容量或真实OCR接入验收。

最终私有保全目录`/root/racepick-deploy/mini-ocr-20261104-35bd5c5d/cutover-final-b21osho2`，guest-queue-configs.tar.gz SHA `e4117c68d392900cfbfc55d9257da98f07325e018fd51bf4f86b71471672d13e`；最终业务备份`/var/lib/racepick/backups/scores-20261104T062600889850Z.zip` SHA `20890cd75924498920e5ad01cb765545257082437b598c391bd50ac1deae52c1`，独立恢复`/var/lib/racepick/restore-drills/d56fbfb914503c8898d758d6`通过。该备份快照50账号/25国服车库/0国际车库/6投稿，两服pending0，contribution/feedback/notification/coverage/global-profile/global-score/usage组件通过、active_database_replaced=false；计数不是后续实时库计数。全部业务数据、原访客状态/密钥、原队列、旧发布及历次备份/演练保留，无维护数据导入或旧库恢复。

backup.timer已enabled/active/waiting，NEXT2026-11-05 04:19:52 CST仅为计划；最近定时任务仍11月4日04:20:06—04:20:07 success/0，早于本次切换，不能宣称新版本定时备份已运行。新版本现场手动backup/独立drill在最终停写保全中已通过。真实微信会话/手机双服快照未在本次切换后重验，原生OCR更未实图验收。两次失败及回退证据保留：首次预检漏cwd/隐藏stderr，显式cwd后通过；第二次因缺失/etc/racepick-ocr-safety导致226/NAMESPACE，补空root700目录并完成短时沙箱inspect后再成功切换。后续部署必须预建此隔离目录，不修改已封存ZIP。

本轮兼容切换与HTTP收尾已完成；下一阶段schema/bridge/供应商调用/原生OCR启用等待单独新任务，不自动推进。未提交推送、发布公告、清理或创建监控。完整阶段证据见[部署准备与现场回执](MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json)；下方记录按历史时间阅读。

## 2026-11-04 用户回传兼容切换成功标记，公网收尾待核

用户仅回传COMPATIBLE_CUTOVER_READY; native OCR remains closed.，按成功标记记录本轮兼容切换完成反馈；完整cutover.json、新保全路径/SHA及现场PID未回传，不补造。下一步只读收尾核实际current/运行cwd、公网health与原生关闭门禁、备份timer及过滤后的切换回执。目标网站7241d9d67cc99178bd7d2d14、guest交付35bd5c5d2e618b555de3a70c；不据标记声称真实微信/手机重新验收，或未来备份成功。队列迁移/bridge/密钥/付费/原生OCR开放继续排除，未提交推送或发布公告。

## 2026-11-04 guest沙箱inspect成功，兼容切换重试待执行

用户创建/核空root700目录/etc/racepick-ocr-safety后，短时systemd检查racepick-mini-ocr-check-2bc092f0成功exit0、2.360秒；与候选guest相同关键挂载/用户/资源设置下只读快照五文件通过，未加载鉴权配置/GuestStore、未监听或启模型/供应商，现行服务保持。该inspect不等于实际HTTP/会话验收。下一步复用已安装且字节相同的disabled mini-ocr.json，短维护内刷新保全并重试兼容切换，仍不迁移队列/启动桥/写密钥/付费。尚无切换成功证据。

## 2026-11-04 guest失败根因已确认：缺失InaccessiblePaths目录导致226/NAMESPACE

用户journal明确候选guest在Python启动前因/etc/racepick-ocr-safety不存在而挂载命名空间失败。部署前置遗漏，不是应用HTTP401问题。current已退a933，三原服务active/running，bridge inactive/dead，timer active/waiting，公网health正常且两服指针及worker ready保持。候选mini-ocr.json现已存在、UID996/GID987/0600；重试时必须比较并复用，不能继续原来的“不存在”断言，也不删除它。下一步创建空root700 safety目录并短时systemd隔离inspect（只读快照、无GuestStore/凭据/监听），尚待执行；不写密钥或启桥。不改已封存v2 ZIP；后续部署说明须列该目录前置条件。

## 2026-11-04 第二次切换因guest就绪检查失败回退，待日志诊断

用户回传COMPATIBILITY_PASSED、FINAL_PRESERVATION_PASSED，新私有目录cutover-retry-q2p2wqw6；完整preservation.json/新备份SHA尚未回传。脚本已换兼容网站/安装disabled guest后，在guest snapshot未于时限内返回401处失败；未取得实际HTTP响应/日志，不能断言启动失败或特定原因。回退路径执行，原OCR/accounts/guest和timer恢复start exit0，实际current/健康待核；无业务库恢复、队列迁移或桥启动。下一步仅日志和恢复状态只读诊断，不重复切换。旧维护窗口保全及原版本均保留。

## 2026-11-04 显式候选cwd兼容检查通过，原服务/公网/备份调度恢复已确认

用户回传PRECHECK_EXIT=0及COMPATIBILITY_PASSED；current仍a933，accounts PID217801、OCR PID217799、guest PID217804均active/running，bridge inactive/dead，backup.timer active/waiting。公网健康ok、CN c815b612/Global435d5b40保持、原OCR worker ready。先前stderr未取得，不能断言其精确异常；显式cwd后检查通过，无候选不兼容证据。下一步在同一次用户执行的短维护内刷新停写保全并切兼容网站/disabled guest，避免停服等待另一轮；尚未执行。禁止队列迁移/bridge启动/密钥/付费/原生OCR开放的范围持续有效。

## 2026-11-04 切换在兼容预检失败，尚未改链接或单元，原服务恢复命令返回0

用户回传候选python经runuser执行verify/check_score_compatibility返回1；原脚本capture_output未显示stderr，且未给python -c设置候选cwd。工作目录/模块导入是可能原因，未经stderr验证不得定论。失败发生在任何配置安装或current切换之前，原代码未变；OCR/accounts/guest/timer恢复start均exit0，仅证明命令返回，实际健康待读。下一步只读重跑预检（显式cwd候选、显示stderr）并核原current/健康/timer，不重复停服、保全或切换，不迁移、不启动桥。

## 2026-11-04 最终保全完成，原服务与timer已停，兼容切换待用户执行

用户回传FINAL_PRESERVATION_READY：私有pre-cutover-ean3ghkc内guest/queue/config归档4156字节，SHA968232bd268baf11bacbaa90de34c7200ea36de35d4edc3a1c6a46fe636d170f。最终业务备份scores-20261104T061602123354Z.zip，SHAa6d28999b4a799771c802597771ba30109ea99b769e80009b7ff443ba0a7352f；独立restore-drills/a8e8236c59613f9630a24eb9通过，活动库未替换、两服指针/计数保持。原guest/accounts/OCR服务已停止，backup.timer inactive；尚未切换或迁移，bridge未启动。下一条命令拟安装disabled guest配置/单元、以业务owner执行新工具兼容检查后原子换current、启动原唯一OCR与网站及新guest并恢复timer；失败仅退代码/单元，不恢复旧业务库，不写为已完成。

## 2026-11-04 最新业务备份恢复通过，短维护窗口保全待执行

用户回传LATEST_BUSINESS_BACKUP_READY：新备份scores-20261104T061419070871Z.zip、2150420字节、SHA60ea305938ed111683fbe8692e981d109b89169586619b701fd4e09d41deaa82，严格校验及独立restore-drills/c17af807b720ca8752cc83ca通过；50账号/25国服车库/0国际车库/6投稿，CN c815b612/Global435d5b40，两服处理中0，active_database_replaced=false，无迁移切换。下一步短暂停原服务和timer、保全guest/原队列/配置并生成最终业务备份；尚未执行，不记停服或切换完成。最终保全成功后留在维护窗口等待下一条切换命令；如保全失败则尝试恢复原服务及timer，保留所有证据。

## 2026-11-04 兼容版本切换已授权，最新业务备份待用户执行

用户明确授权兼容网站/访客网关切换，图片继续disabled；保留全部业务数据、访客状态、原队列和备份。明确排除队列迁移、bridge启动、阿里密钥/付费调用及公网原生OCR开启。下一步由用户以现有racepick owner和a933工具生成最新成套业务备份并独立drill；本地已准备命令，尚无执行回传，不记为完成。该步骤不停服务、不切换；访客/原队列的停写保全留到后续短维护窗口。先前早晨备份与独立恢复证据保留，不冒充最新快照。

## 2026-11-04 v2候选配置生成完成，等待明确实际切换范围

用户回传PREPARED_CONFIGS_READY，5个候选文件仅保存在`/root/racepick-deploy/mini-ocr-20261104-35bd5c5d/prepared-configs`，guest UID996、queue owner999、socket GID987/现有racepick-mini-test组；image_policy=disabled、bridge enabled=false、safety mode=disabled，未写真实新凭据、/etc或启动服务，未迁移切换。源码、环境、备份独立恢复和候选配置的准备阶段完成；按用户要求不再循环验包。

拟请求的第一阶段实际授权为：保全现有业务/独立访客状态及原队列后，将兼容网站从a933切至7241候选，访客服务从9d856切至v2网关但图片仍disabled；复用既有OCR单元/队列与资源限制、原成绩指针及写开关，收尾恢复备份调度并验健康。不需要为这个关闭图片的阶段迁移识图安全schema，也不启动bridge。真实RAM配置、受控付费样图、queue schema0→1和公网OCR开启另阶段明确授权。当前尚未获实际切换授权，代理未操作服务器。

## 2026-11-04 v2三套离线运行环境服务器准备完成，待候选配置与切换授权

用户回传整条暂存/离线安装脚本成功标记PREPARATION_READY及No broken requirements found：guest/bridge固定目录`/opt/racepick-mini-ocr/releases/35bd5c5d2e618b555de3a70c`，网站候选`/opt/racepick/releases/7241d9d67cc99178bd7d2d14`。均为新暂存环境，未调用会加载第二模型的网站安装器自检；脚本未启动服务、迁移/activate或配置真实密钥及供应商调用。本轮不再重复用户已确认的核对。

下一步仅在`/root/racepick-deploy/mini-ocr-20261104-35bd5c5d/prepared-configs`新私有目录渲染默认关闭JSON与两服务单元，不写/etc。计划复用guest现有主组作socket共享组，新bridge进程仍以queue owner运行；不更改现行账号/用户组成员或队列权限。沿用已有微信字段及state，仅复制配置中的密钥文件引用，不读取/复制密钥文件本体；阿里credentials文件仍不创建。实际安装配置、队列schema迁移、服务切换/公网OCR及付费样图仍需明确后续范围，不能把“尽快准备上线”扩成真实密钥或正式切换授权。

## 2026-11-04 用户要求停止重复核对，直接推进v2暂存与离线环境准备

用户已回传v2服务器ZIP312131724字节/SHAf5f58f917ac2c41d26bc3b2ed4fc098ebd9ac4b139a83e4275c9f73fc032e41d通过，随后明确“无需再一项项核对，之前已经由其他对话核对完成了。尽快准备上线不要死扣核对”。按用户确认接受其他对话已完成的核对，不再重复压缩包清单验证，不把本聊天未执行的命令写成新实测证据。

下一步直接新目录解压暂存并离线安装guest/bridge及新网站7241候选的运行环境；尚待用户执行回传，不替换现行current、不启动新服务、不迁移业务/队列、不配真实密钥或真实传图付费。为保留唯一现有OCR模型及服务器资源，本步骤不调用网站install-runtime.sh中会额外加载模型的OCR自检，只按已锁wheel安装并pip check。所有旧发布、状态、备份和独立恢复目录保留；遇到已存在目标保留并回传，不删除重做。迁移/切换和开启公网仍须后续明确范围。

## 2026-11-04 v2部署准备第四步：独立恢复通过，正式服务未切换

用户按已明示范围以racepick执行，仅新建私有工作区`/var/lib/racepick/mini-ocr-restore-20261104-t35ng_gx`，对副本运行a933原工具，实际演练目录`restore-drills/1268d89c30fdadaa74fa1d80`。来源固定备份SHA2e6bdbfa17a75d4ac3a9ca585d56bfb0194bdea7a7f8e6b2ac2772d5b33c238e。恢复CN c815b612/Global435d5b40、50账号/25国服车库/0国际车库/6投稿，两服处理中0；contribution1及4/4/7/3、反馈1三表0、通知1及6/6、coverage2三表0、global-profile1/global-score1/usage1均通过，副本CN写开/Global写关。owner999/mode700，active_database_replaced=false、live_db_inode_preserved=true、live_migration_or_switch_performed=false，current前后a933断言通过。

上述计数仍为04:20备份恢复副本，不能当实时业务计数。独立目录写入与正式数据/配置写入分别记录；没有停服或调用正式restore/migrate，也不清理新旧演练目录。下一步仅拟新建私有上传暂存目录并让用户上传35bd5c5d v2完整ZIP及校验文件，尚未核服务器包字节，不解包/安装/启动；访客状态和原OCR队列的保全仍须在任何服务变更前单独完成。结构化事实并入MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json。

## 2026-11-04 v2只读准备第三步通过：备份SQL完整，独立目录恢复尚待执行

用户回传RAM-only核验：accounts/usage完整性及外键均ok，备份CN c815b612/Global435d5b40与清单一致，coverage2/global-profile1、usage1，CN写开/Global写关、两服处理中批次0。备份快照50账号/25国服车库/0国际车库/6投稿；不能把04:20快照当实时计数或认定之后未新增/删除车库。脚本未查询contribution_rules版本，不将输出中没有contribution_schema同名表解释为组件未启用。

截至第三步仍无文件解包、正式SQLite打开或生产写入，独立恢复未完成。已核当前工具drill会新建私有目录并校验全部版本/绑定；下一步拟以原数据owner在新的mini-ocr-restore-20261104-*私有工作区恢复副本，再对该副本调用a933原工具独立演练，避免改动既有restore-drills权限或触及正式SQLite sidecar。命令须明确新增目录写入范围，由用户执行回传；不授权业务迁移/切换或真实供应商调用。结构化事实见MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json。

## 2026-11-04 v2只读准备第二步通过：今日定时备份文件完整，恢复尚待验证

用户逐步回传同一固定备份scores-20261103T202007179082Z.zip（2149586字节/SHA2e6bdbfa17a75d4ac3a9ca585d56bfb0194bdea7a7f8e6b2ac2772d5b33c238e）：ZIP CRC、严格清单及40载荷逐项SHA通过，ZIP合计41成员含backup-manifest。备份声明CN c815b612/Global435d5b40、coverage2/global-score1/global-profile1/usage1，与第一步版本一致。服务实际ExecMainStart/Exit为11月4日04:20:06–04:20:07 CST，success/0；timer enabled、active/waiting，NEXT11月5日04:15:08，不能记未来运行成功。

本次没有解压、打开正式SQLite、恢复或替换正式库。备份SQL逻辑完整性/计数和独立落盘恢复尚待检查；备份快照不等于此刻账号/国际车库数量，不能从global-profile1声明推断具体行数。下一步仅将备份SQL镜像读入RAM核完整性/外键/指针和聚合计数，不读个人字段或写服务器文件；独立恢复并未因此完成。所有真实密钥/供应商调用、迁移/切换仍未授权，公网OCR继续关闭。结构化第二步证据已并入MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json。

## 2026-11-04 12:38 v2部署准备第一步只读回传，尚无生产写入

用户仅授权逐步只读准备，继续排除真实密钥/传图付费、迁移/切换和公网启用。用户回传确认网站current、accounts PID210016及OCR supervisor PID209663实际cwd均a933/源码765a4a6；访客PID214505实际cwd仍第一阶段9d856/0b97dae，image_policy=disabled，网站原生配置未设置。新桥unit not-found、两份安全配置不存在；内外health200/ok，主6/coverage2/global-score1/global-profile1，双服活动版本仍c815b612/435d5b40，CN写开；Global写开关本次health未返回，不据历史值冒充本次实查。所有PID仅为本次快照，worker209668来自state文件，尚未独立核其cwd。

服务器Python3.12.3，内存总1740MiB/可用1024MiB、系统swap已用81MiB，磁盘可用27GiB；OCR实际High640/Max768MiB/Swap0/Tasks64，guest Max128MiB。后续新增预算须现场评估，不能将候选上限相加当作实际占用或盲覆原单元。原队列999:988/目录700/SQLite600，guest996:987/状态目录700。

backup.service Result success/exit0，timer active(waiting)，LAST11月4日04:20:06、NEXT11月5日04:15:08。最新实际文件scores-20261103T202007179082Z.zip，2149586字节/SHA2e6bdbfa17a75d4ac3a9ca585d56bfb0194bdea7a7f8e6b2ac2772d5b33c238e，读取期间大小/mtime稳定；尚未核CRC/清单/逐项SHA或独立恢复，不写为恢复验收通过。原生仍关闭，代理未操作服务器。结构化记录MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json；下一步仍只读核该固定备份，不解包/恢复或迁移。

## 2026-11-04 原生HTTP接桥、Ubuntu离线锁与完整v2候选交付完成，未部署

用户授权仅本地HTTP接线、Ubuntu离线依赖与完整可校验包，继续排除真实密钥/供应商传图付费、服务器及公网启用。本轮新增独立mini_ocr_guest_service和socket-only端口，提取纯snapshot/result模块；原访客状态和session key不重建，账号/B–E及Global OCR关闭。默认image_policy=disabled/bridge enabled=false，默认仍只session/snapshot；显式开启的本地夹具验证CN目录及原key/owner/图片/目录恢复，关闭上传后保留原任务查/恢复/取消，guest不能配置队列/业务库或RAM凭据路径。

最终交付ID **35bd5c5d2e618b555de3a70c**，内层网站候选ID **7241d9d67cc99178bd7d2d14**；整包`offline-evaluation/mini-ocr-gateway-release-20261104-01/RacePick-MiniOCR-Baseline-20261104-delivery-v2.zip`，312131724字节，SHA256 **f5f58f917ac2c41d26bc3b2ed4fc098ebd9ac4b139a83e4275c9f73fc032e41d**。外层305文件/304项目录SHA、完整ZIP CRC及逐字节目录回读、源码清单、分环境锁和内层172文件manifest通过。源码为封存未提交快照，source_commit=null、开发base0b97dae9e1003c1bc2c4c5b7a189b81cb4002112，source tree SHA f0eb44207daede26e4f262c2fdbb430b36cb0fdb4ed930ce25eacf1d7b1bc1a5；不冒充新Git提交，本轮未提交推送。

网站严格以已验收a933为基底，仅叠加本轮6个共享后端/兼容文件；CODE_DIFF确认HTML/CSS/JS/模型和原37wheel字节保持，不自动发布其他本地页面更新。五JSON仅为b57d97a8批准快照/种子，data_commit=null，不覆盖正式score-state、不导入维护733/工作簿、不重复维护或业务迁移。新队列schema及兼容cap准备必须未来显式授权；新工具只读发现schema1/部分结构会拒绝旧容量代码。旧c06/global-profile回退限制继续有效，不能恢复旧库丢车库。

Windows合并142执行/122通过/20项Linux跳过；Ubuntu24.04.3用户态/CPython3.12.16完整124项通过无跳过，guest14/bridge37/web37/validation55 wheel均离线require-hashes安装和pip check通过。真实隔离Nginx HTTPS→guest UID10002→Unix→broker UID10001验证队列文件不可见、同key一次模拟审核、实际8MiB PNG202、封装/session超限413、Cookie/Origin403及Global OCR403，关闭上传后手选/取消保持。systemd255候选语法检查退出0，仅使用本地路径/数字UID和基线target夹具，非实际单元/cgroup验收。最终内层网站7241d9d6实际包又通过Ubuntu独立临时库迁移/锁/恢复与真实CPU合成RACEPICK识别自检（8.21秒）；无邮件或供应商请求，不等于游戏中文截图、真实微信或手机验收。

准备说明在功能树docs/ALIYUN_OCR_RELEASE_PREPARATION_20261104.md，最终机器回执docs/MINI_OCR_RELEASE_RECEIPT_20261104.json及上述artifact目录COMPLETE_DELIVERY_RECEIPT_20261104.json。首次Ubuntu夹具漏文件/测试依赖、Windows新测试连接未关闭、v1校验器计数显示问题均已纠正，失败/旧候选保留，唯一推荐v2。原15份数据/工作簿SHA/大小/mtime保持。现网仍仅沿最近a933及第一阶段已验收记录，本轮未重新核服务器current/健康/备份timer。

下一步若用户授权进入部署，先仅给当前一步只读核验，由用户执行回传；再结合成套备份/独立恢复、实际UID/GID/路径/资源确认兼容升级和queue schema所需授权。私有RAM配置、样图限量付费调用、Nginx/systemd/切换及微信uploadFile域名均后续分别按授权逐步办理。公网OCR仍关闭；无服务器/微信后台/上传提审发布、业务数据变更、公告、清理旧资料或监控。

## 2026-11-04 SDK传输及共享单队列桥本地实现完成，公网OCR仍关闭

用户授权继续本地真实SDK传输/共享桥/模拟及可做的Linux隔离验证，明确排除真实密钥、向审核服务传图/付费调用、服务器操作和公网启用。本轮功能树新增image_safety_sdk.py、ocr_queue_bridge.py及对应测试/默认关闭模板和独立SDK依赖清单，修改共用map_recognition.py支持显式safety schema、checking审核状态及共享配额。官方SDK签名/模型与oss2上传由模拟HTTP边界验证；真实SDK运行在独立、硬截止回收的子进程，默认配置和显式live授权双门禁。受限Unix socket桥验SO_PEERCRED/固定owner与CN目录，复用同一个JobStore；checking占8任务/owner2及同IP20/600秒额度但worker不能领取，取消/过期/关闭不允许审核迟到回包复活。

Windows新套件48执行/37通过/11项Linux专用跳过，另官方SDK模拟线测3项通过（含新增HTTP500不重试）；既有访客/原生/OCR相关53回归通过。本机Docker启动因Inference manager失败，用户截图确认；未reset、删镜像/卷或上传诊断。改在现有WSL的本轮独立Alpine root中，以mount/network/PID namespace、UID10001、只读root和96MiB临时tmpfs运行，46项全部通过，业务路径不可见且未加载OCR模型。真实SDK线测仅Windowsmock，Linux子进程测试为合成目标，不是Linux真实阿里调用或Ubuntu/systemd/cgroup验收。便携静态Python加载Pillow失败及首次临时空间不足如实留记；Alpine root完整归档/SHA后只删除本轮新建临时root释放空间，Docker原数据保持。

说明/机器回执在map-layout-parser/docs/ALIYUN_SDK_QUEUE_BRIDGE_LOCAL_20261104.md、ALIYUN_SDK_QUEUE_BRIDGE_LOCAL_RECEIPT_20261104.json；日志、SDK解析版本和Linux运行时归档在offline-evaluation/mini-ocr-sdk-bridge-20261104-01。15份运行JSON/工作簿SHA/大小/mtime保持；除明确修改的JobStore外，原网关/身份/worker/监督者6文件SHA保持。未提交推送/构部署包。原生HTTP网关尚未接桥，第一阶段仍session/snapshot和image disabled，不能仅填入密钥打开公网。下一步本地接线/Ubuntu离线锁/构包兼容后，才按用户授权配置真实凭据和现场UID/GID/路径；新增识图安全schema另需显式授权，serve不自动迁移，不重跑global-profile/维护迁移。旧a933网页JobStore不计算checking，未来须协调共用代码升级，不能只新增桥后混跑旧容量逻辑。保留正式账号/成绩/备份/原队列，不操作微信后台/账号B–E或小程序发布。

## 2026-11-04 用户选定baselineCheck，本地适配与模拟测试完成，公网OCR仍关闭

用户明确采用阿里云baselineCheck，后付费服务已由用户开通；本轮仅授权本地适配器/配置/模拟测试，排除真实传图/付费调用、服务器和公网开启。私有识图仅回传5槽地图名称，用户明确不购买广告引流专项；此前postImageCheck30元候选建议由本轮baselineCheck范围覆盖。基础安全审核与文字OCR仍分开，不能拿识别成功当审核通过。

功能树新增backend/image_safety_aliyun.py、image_safety_local.py、test_image_safety_aliyun.py，production/aliyun-baseline.config.example.json及两项Action的RAM策略提案。适配器只支持disabled/simulation，未实现真实SDK网络传输、不读凭据；本地回执表位于同一个临时识图SQLite，复用原JobStore，不建第二队列或模型。owner/key/图SHA/目录绑定，同key/并发/重启/响应丢失不重复模拟送审，明确none+nonLabel才入队，拒绝/未知/超时关闭。local recover诊断状态没有改原生HTTP契约。不能仅填入凭据就开启此准备版本。

新增23项模拟及既有访客/原生/OCR队列48项回归全部通过，Windows合成图/新临时目录，无真实阿里或微信调用。7份原网关/队列/worker代码与15份运行JSON/工作簿SHA/大小/mtime核对保持。说明与机器回执在map-layout-parser/docs/ALIYUN_BASELINE_LOCAL_PREPARATION_20261104.md、ALIYUN_BASELINE_LOCAL_RECEIPT_20261104.json，均未提交推送。生产socket桥/共享待审准入/待审取消及关闭收尾、Linux资源隔离、真实SDK/凭据加载、样图付费测试和现场切换仍待相应授权及验证。未操作服务器/微信后台、提交推送、公告、清理或监控；公网图片策略和原生入口保持原状态。

## 2026-11-04 OCR提供方公开文档核验完成，尚未选定或接入

用户要求优先核实微信官方再比较二进制送审；本轮普通HTTPS成功读取当前微信mediaCheckAsync官方正文/Markdown（页面标注2026-10-29编辑），补充了此前读取失败的证据。2.0要求真实OpenID且近2小时访问、media_url可下载、10M及有限图片格式，最终结果30分钟内异步回调。当前仅存HMAC摘要的GuestStore、无媒体下载入口和拟60秒安全截止都需调整，不能将wx.login通过当审核权限通过，也不能将30分钟回调当删除期限。当前官方单价及供应商留存期限未核实，不据非官方“免费”文章写0元保证。

建议下一步候选为阿里云国内同步ImageModeration的本地上传方式，较广范围可选postImageCheck30元/万次，baselineCheck15元/万次不涵盖全部治理风险；最终选择仍待用户决定。官方本地流程先上传提供方临时OSS，文件30分钟、结果查询近30天，不能宣称零留存。腾讯CI确有Base64批量接口但仍需绑定桶、按场景计费及>5MB大图处理；腾讯IMS为另一产品，其Base64后10MB限制不足接收原始8MiB图片。微信权限/scene匹配、云供应商数据删除与使用条款等未核项见功能树docs/MINI_OCR_SAFETY_PROVIDER_REVIEW_20261104.md。10份官方公开文档快照及SHA回执存offline-evaluation/mini-ocr-provider-review-20261104-01，不含秘密或私人图片。

本轮仅研究和本地交接更新，没有审核API调用/图片外发、服务开通/付费、服务器或微信后台操作、运行代码/开关修改、提交推送。公网OCR保持关闭；本报告是选型建议，不是接入授权或可部署包。

## 2026-11-04 第一阶段用户验收回交，第二阶段OCR仅方案准备

用户本轮回交：mini-test真实微信访客及双服固定快照已通过开发者工具，且“诊断版2手机上也通过了”。这是用户验收反馈；没有机型/系统版本，不能扩展为iOS/Android双系统、相册上传、OCR或账号验收。下方第一阶段“SDK待验证”为当时记录，原始回执保留。源码0b97dae/交付9d856fba仅session/snapshot，图片disabled；本轮未重新访问服务器，不声称现行进程、备份或证书续期已重核。

当前任务已由旧730交付部署请求转为网站侧OCR开发准备；730整包SHA、60文件逐字节、59项目录SHA、主168/兼容158文件及冻结绑定重新通过，但主站最新运维记录a933已完成部署验收，不能再拿730重跑迁移或覆盖上线来源。fetch和ls-remote核对main/origin/main为39dcce916e4bc7f82fb58d245df4d61f1426a286；网站功能树0b97dae较远端3c3fdd9领先1提交，本轮未推送/合并。25个登记工作树已查，既有修改与未跟踪资料保留；原测试服务未启停。

用户选择“尚未选择，先给接入方案”。网站功能树map-layout-parser/docs下新增MINI_OCR_STAGE2_PLAN_20261104.md、MINI_OCR_STAGE2_PROTOCOL_DRAFT_20261104.md、MINI_OCR_STAGE2_RESPONSE_DRAFT_20261104.json及MINI_OCR_STAGE2_PREPARATION_RECEIPT_20261104.json，均为未提交的本地方案，尚无新OCR运行代码、固定提交或交付ID。方案提出受限Unix socket桥接唯一JobStore/监督者、先审核后领取、共享事务配额和独立固定目录；协议增补仍待评审。安全提供方、外发/留存及实际平台声明未定，不启用private_unmoderated，不向外部送图，公网OCR继续关闭。

本轮Windows既有访客/原生协议33项通过，不证明新桥/审核实现。Docker Linux引擎不可连接，未启动Docker/WSL，新架构Linux隔离/资源/并发测试待完成。账号/B–E、生产变更、服务器安装切换、微信后台、上传体验版/提审/发布均排除；未向其他聊天派任务。后续先评审方案与选择安全提供方，再实现并隔离验证；现场操作另按用户授权一次一步，不重跑global-profile/维护迁移，不恢复旧库，不清理或创建监控。

## 2026-11-04 隔离小程序访客HTTPS入口已就绪，真实微信SDK验证待进行

本轮由用户逐步执行授权的独立测试准备、DNS、ACME证书和隔离服务接通。正式网站仍为下文a933，生产账号/车库/成绩/原OCR及备份调度保持，未部署主站新版本、开启主站原生API或重跑业务迁移。独立origin=https://mini-test.racepick.cn，源码0b97dae9e1003c1bc2c4c5b7a189b81cb4002112（本机功能树固定，未推送/合main）、交付9d856fba3f6b825b255bc17e；仅POST访客session及GET双服snapshot，image_policy=disabled，账号/B–E/OCR关闭。详见[回交小程序侧](MINI_GUEST_STAGE1_CLOUD_HANDOFF_20261104.md)及[独立激活回执](MINI_GUEST_STAGE1_ACTIVATION_RECEIPT_20261104.json)。

实际TLS域名/系统CA/呈现证书验证通过，接口门禁401/400/403/404/413符合预期，无真实微信code请求。私有真实平台配置已安全加载，不在Git/聊天/交付中记录值；不等于平台有效性已验证。独立UID996/GID987，服务PID214505/cwd固定release、仅127.0.0.1:8011，128MiB/25%CPU/Swap0/Tasks32及挂载隐藏正式文件已核验。最后观测schema1、sessions/codes/uploads均0；采样内存约34.5MiB/峰值34.9MiB仅短期未认证流量。服务active/running，**开机自启disabled**。原Nginx和两份证书26项基线保持；新配置、两个阶段备份、源SHA与证据边界见回执。

下一步由用户登记request合法域名，交小程序侧建独立网络检查工程，真实wx.login→内存访客token→双服UTF8原字节/SHA/bytes/identity验证；先开发者工具再用户手动真机，不跳过域名/TLS校验、不上传/提审。当前不宣称真实平台、SDK或手机通过。证书截至2027-02-01T15:03:46Z；00:11观测snap.certbot.renew.timer NEXT11月4日06:00仅为当时计划，新证书自动续期及续期后加载未验证。独立访客状态未加入正式业务备份，未新增监控/定时清理/备份任务。不开启OCR/账号下一阶段；Git收尾另按授权。

## 2026-11-03 当前上线：a933c9b7，网站与CN4516/Global694同批正式发布，用户验收通过

本轮生产命令全部由用户执行并逐步回传，代理未登录生产。用户明确纠正旧“新冻结只作种子”范围，本次正式发布维护冻结；旧730a61cd交付保留但不再用作本轮上线来源。后续用户授权直接迁移已审核内容，不重复逐条人工审核；仍完成现场完整计划绑定、漂移检查、成套备份及独立恢复。结构化证据见[网站与维护数据部署回执](WEB_DATA_DEPLOYMENT_RECEIPT_20261103.json)。下方c06及“维护数据未发布”均为历史阶段，不续跑旧迁移。

发布a933c9b746c2e276a9b68d14，源码765a4a62567c97a9a2d4f48cf3a8955e3e8cd715；冻结b57d97a8f4e484be69238ab0、清单SHA940f8660585c495a780390b709dfd52e80f7610f57e0179c5da937c53c4e4282，data_commit=null。整包317469943字节/SHA064f1fe563e237dd4ba4edcc94a83501f36aa0449ff956ab165b473181055c1b，外层62文件/目录61项SHA、内层171文件及兼容158文件通过；37wheel离线安装、pip check、Linux临时库自检及合成OCR通过。未把维护733、参考、工作簿、台账或测试库导入运行。

现场正式基线CN4391、Global659（不是本地4487/664演练）；计划cb40da88a20f8c04701ce2782f09eaaa50302823fbd59d103f4d8c7370a594bd绑定原双服版本/五文件SHA/开关/账号和目标冻结，迁移前自动重算一致。CN新增127/删除2/提速60/变慢5；Global新增35/删除0/提速11/变慢1。两条河畔漂移旧跳图19.9/19.5同值改名“旧跳图”，不是丢失成绩。全部目标内容已由用户批准，包含此前维护更新，不只本轮19/2项。

唯一新增账号组件迁移global_profile_schema0→1成功，existing_rows_preserved=true、初始国际车库0；未重跑主schema6/coverage2/global-score1。维护apply由原账号库owner racepick(UID999/GID988，0600)执行，持服务锁/双服锁，建立两服不可变版本、原子切换指针及保留审计；不重播种、不直接覆盖JSON。实际活动CN c815b612a17433f403ae2965000fd74b / Global435d5b40fd1aa4a01753a395f28d1f89，活动及公网五文件SHA均精确匹配冻结，实际4516/694；cc850共同min3/四区max3/default6与国际fxxk入池均核实。原国服写开/国际写关和绑定保持。

current及网站PID210016、OCR supervisor PID209663实际cwd均指向/opt/racepick/releases/a933c9b746c2e276a9b68d14；这些PID只是回传快照。内外health ok/production，schema6/coverage2/global-score1/global-profile1，其余组件1，OCR ready。原Nginx/systemd配置复用，未覆盖模板；OCR实际High640MiB/Max768MiB/CPU100%/Swap0/Tasks64、PrivateNetwork/ProtectSystem strict/AF_UNIX/control-group均核实。未复做实际挂载视图或长期容量测试。停止前OCR queued/running清零，原队列保留。

停服最终恢复点scores-20261103T083326088670Z.zip，SHA29c0013747491afa1ef9eb68bc1476c5f3bcf8452da2430cf1adadecfab2570b，演练fc53ba41df32485bb60d344d。维护后40文件恢复点scores-20261103T083710457516Z.zip，SHA8f9614dd0632c97d3e1209a6c3b3e884332acc4a5c6558382cf41ca75cd12f97，演练3458c3f1d4bed6999fd31e22。全部路径基于/var/lib/racepick/backups和restore-drills。所有独立恢复active_database_replaced=false；完整在线/迁移自动/迁移后/apply自动等恢复点及缺失字段见机器回执，不编造映射。

新版真实备份服务2026-11-03 16:45:11–16:45:12 CST success/exit0，实际新备份scores-20261103T084511778668Z.zip，2145403字节，SHAe6b8b72fe197f33f9dc9c35dece53ed9ddecd38eb753bd29f4a8a19420c1d851；40文件校验及独立恢复07d1cdc41550b8fb0c5c87d9通过。快照50账号/25国服车库/0国际车库/6投稿、贡献4/4/7/3、反馈0/0/0、通知6/6、覆盖三表0、双服pending0保持；该快照早于用户验收保存，不声称验收后计数仍为0。timer恢复enabled，NEXT2026-11-04 04:15:05 CST，未来执行未验证。本轮也核实11月3日04:17旧自动备份真实成功，非未来成功证明。

原生入口保持关闭：实际网站进程未设置非空RACEPICK_MINI_CONFIG，公网原生snapshot404；国际成绩写开关仍0。未操作微信后台、上传/提审/发布小程序。用户在被要求桌面/手机微信登录、原国服车库、国际云车库保存读取/OC、截图识别和计算后明确回复“验收都通过。”，为用户实际反馈，代理未独立操作手机。409保留两份、登出/切账号/失败GET隔离未单独逐项回传，不另造证据。

维护审计仍applied时a38候选不可直接用，须另获授权、满足双服target/CAS且无后续版本后定点回退维护指针；不恢复旧SQLite，不丢账号/国际车库。c06不兼容global-profile1，不能直接回退。若后续真实成绩版本已产生，禁止按旧target强行回退。

本轮部署与用户验收完成。保留全部业务状态、旧包/发布/备份/演练/队列、测试资料、工作簿和未跟踪文件；无公告、清理、监控、main合并、提交或推送。本次仅新增本地回执并前置更新交接索引，原有dirty内容保留，后续Git操作另按授权。

本轮文档Git收尾：用户随后明确授权仅提交推送本轮部署、验收和交接文档，完成后暂停。仅纳入本文件与INDEX的11月3日前缀及新部署回执；原有历史未提交记录、维护数据、工作簿、测试修改和未跟踪资料继续保留，不合并功能分支。准确提交及远端回执另存本地归档/webdata-deployment-closeout-20261103-a933c9b7/push-receipt.json，避免自引用提交SHA。

## 2026-10-31 当前上线：c06cc48b，OCR上线与桌面/手机微信验收完成

最终收尾：用户已回传正式常驻OCR单元enabled/active/running，实际CPUQuota1s（100%）、High671088640/Max805306368字节（640/768MiB）、MemorySwapMax0/TasksMax64、racepick用户组、PrivateNetwork/ProtectSystem strict/AF_UNIX及control-group回收均生效。实际supervisor挂载视图的/var/lib/racepick只包含map-recognition，worker为其直接子进程、ready；采样RSS152060KiB为就绪待机值，不替代真实识图峰值或长期容量结论。国际写回仍关闭。用户明确回复“验收均正常”，覆盖此前要求的桌面及手机微信真实截图识别、地图顺序确认/填入/计算、手动选图、双服切换、登录及原车库验收；这是用户实际验收反馈，非代理独立操作手机。运行/备份/timer与公网事实见下文，最终结构化回执见[OCR部署回执](MAP_OCR_DEPLOYMENT_RECEIPT_20261031.json)。本轮部署和验收完成，不继续发布维护成绩、公告、清理或监控；用户后续仅授权本轮部署、验收与交接文档提交推送；Git准确回执保存在工作区本地归档/ocr-deployment-closeout-20261031-01a19177，不夹带历史待提交记录。

用户明确授权上线后逐步执行并回传：发布c06cc48b2b55b7bcec58e68b于19:03前完成切换，源码f44e3c219bceb185d055b1ae9e5570ed639e2786、包数据9e7d21f656b61a39282389fb62c0e71149d43c1e；19:03:00现场current、accounts PID194010与OCR supervisor PID193967实际cwd均为/opt/racepick/releases/c06cc48b2b55b7bcec58e68b，两服务active/running，OCR单元enabled，health ok/production、map_recognition enabled/ready。PID为当时快照，不据此操作未来进程。

完整包159835801字节，SHA256=4a5a318d7ad7d57a8049910593287571068790201888d56b41d9e440ec9e9373，来源/内外制品及37wheel离线安装校验通过。独立系统沙箱9图、真实Nginx/API/上传大小/8任务第9拒绝、worker崩溃及取消后硬超时演练通过；正式路径挂载隔离/只写OCR队列/业务目录隐藏及正常进程退出已通过临时单元验证。正式单元High640M/Max768M/禁swap/1CPU，不照抄包内1GiB原模板。未对生产注入故障或导入测试库/假账号。

正式主schema6、coverage2、global-score1及其他组件schema1保持，没有业务迁移。国服成绩仍e209f3e32d0de1dfa7fe6c811a5d5c46、写回开；国际仍1252565e65bc887e81e0c677bfeec9ab/659条，国际写回现场前置核对为关闭，本轮未开启。4487/664包基线不覆盖已有双服score-state，703维护/工作簿/参考/台账不入运行。没有发布维护成绩。

Nginx候选已成套安装、nginx -t和reload通过，精确OCR上传8m/独立6r/s burst12，原默认3m/业务5r/s burst30/统计2r/s burst10/TLS/HTTP跳转/8080/可信代理保持。配置备份和activation.log位于/root/racepick-ocr-preflight-c06cc48b/activation-backup，旧配置与旧release保留。

本轮在线备份、停服最终备份及独立恢复均通过，正式库均未替换。停服最终恢复点/var/lib/racepick/backups/scores-20261031T110052179154Z.zip，2030875字节，SHA256=dc3e3228c8916d3469ed21b117d7fb272871df334282722f8948afb50b241fdf；恢复演练/var/lib/racepick/restore-drills/91306ad1b4d18c218b1bdee1。19:04:23–19:04:25新版真实备份服务手动触发success/0，/var/lib/racepick/backups/scores-20261031T110424620809Z.zip，2030875字节，SHA256=a67317f0e11c4f332a854e3bbab0916f832aa7a38968c51307d3e49153a2b462；33文件校验及演练/var/lib/racepick/restore-drills/d2b1d19692cb0894245f480d通过，48账号/24车库/6投稿、双服版本与组件保持，OCR图片未入业务备份。timer恢复enabled/active(waiting)，NEXT2026-11-01 04:16:52 CST，未来执行未验证；今日04:16自动备份真实成功已核验，非未来执行证明。

代理本轮公网HTTPS GET确认health/五份主要资源匹配新源码、主页“新功能”保留；普通游客会话分别读取CN83图/Global44图OCR目录，目录版本精确绑定两服活动版本ID及数据字节，worker ready、8MiB上限，国际仍659。未上传测试图到生产、未创建账号或业务投稿。随后用户已回传正式常驻单元有效属性/挂载视图核验结果，并确认桌面/手机微信验收均正常，范围见文首。

逐步证据、授权范围和全部恢复点见[本轮接手执行记录](TAKEOVER_20261031.md)、[准备阶段边界](MAP_OCR_PREFLIGHT_20261031.md)。旧“禁止上线”已被后续明确授权覆盖；下方旧部署状态为历史，不续跑迁移或重复provision。数据/用户文件/测试资料/旧包/备份保留，部署阶段未合并main、提交推送、发公告、清理或创建监控；后续仅授权本轮文档Git收尾及新公告草稿，草稿不发布。

## 2026-10-30 22:58 当前上线：3d978fd3，双服运维核验完成，用户验收待进行

本轮生产命令全部由用户逐步执行回传，代理未登录生产。源码1dba7e47eff47fb4423203e0008514aefb6337be，发布3d978fd30812fa8f72ba928d，于22:55:50 CST启动；current与PID188163实际cwd均为/opt/racepick/releases/3d978fd30812fa8f72ba928d，active/running（PID为当时快照）。原bbd92687及所有旧包、旧版、备份/演练均保留。下方旧schema1/国际只读/未部署记录为历史，不据此重跑迁移或回退旧应用。

完整上传包RacePick-Global659-Compat-20261030-3d978fd3-delivery.zip，11070099字节，SHA34d11ecaa1a23dc3e9225f8838b209a611ac178c551152cf23007b302eabbf35；内层SHA484e63317d8b75f152ef65fa136aeaa1e4e347616e2d23def393ed0033f0f429。外置SHA、外层23项清单、内层107文件、源码/种子绑定及CRC通过；19wheel离线LinuxPython3.12安装、临时库迁移/锁/恢复原生自检通过。数据来自批准冻结DATA_HANDOFF_20261030.json（SHA93745f665235ad8928e8514f1977b7948bf92bf14940466a1b9fff83246f4dae），不是新数据Git提交；20份交接文件哈希核验一致。本运维未代维护侧提交数据。

### 两服实际版本与迁移

health主schema6，community/contribution/feedback/notification/usage/global-score均1、coverage2。正式国服版本保持e209f3e32d0de1dfa7fe6c811a5d5c46；cars SHA469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c，成绩SHAb1d830d8390e38f4bd748d1a9341ee0a011226f97457df449e1a3496fe441e08，国服写回保持开启。国服4458代码基线未覆盖独立score-state或车辆规则。

现场先核实coverage1、国际三表和global-score-state目录均不存在、国服pending0；经在线/停服最终备份恢复后仅显式迁移coverage1→2，原业务行保持，新增coverage_global_choices为空。再从新版本目录按批准dataset b5aa1a40fae685bb9440a78b0453125c4d063cad02d9610e39c4daa934872392及现场国服版本首次初始化国际schema1，already_migrated=false、existing_rows_preserved=true，三件套逐字节等于批准种子。没有重播种已有国际状态或重跑旧组件迁移。

国际活动成绩版本1252565e65bc887e81e0c677bfeec9ab（与64位dataset标识区分），运行659/46车/44图全覆盖/21OC/48特殊；638非OC/611普通路线。完整维护698、四区/高手、36独立参考及工作簿/台账不入运行。国际写回默认关闭，本轮未enable，不影响正常国际投稿审核；正式应用/回滚未验收，开启需用户另行明确授权，不能据“已上线”推断可写。

最终48用户/24车库/6投稿，两服pending均0；贡献4/来源4/事件7/偏好3、反馈三表均0、通知事件6/已读6，国服选图/事件及国际选图均0。原业务行与开关保持，不伪造真实权益数据、不导入测试库。

### 备份恢复与timer

四次成套备份及独立恢复演练均通过、active_database_replaced=false。停服最终恢复点/var/lib/racepick/backups/scores-20261030T145159558604Z.zip，SHA97d7c0529a113810f99cb319b04a282197c784cf5f11fae721428046c46a1b6b；双服迁移后恢复点scores-20261030T145504483676Z.zip，SHA85491278d556547d3f4580831d741c96df851ead1cb8cee8719c44317f6c8f88，含33文件、双服状态、coverage2和统计。完整四次SHA/字节数、迁移自动备份、演练路径见[双服部署机器回执](GLOBAL_SUBMISSIONS_DEPLOYMENT_RECEIPT_20261030.json)。

新版真实备份服务22:58:06至22:58:07 CST手动触发success/exit0；生成/var/lib/racepick/backups/scores-20261030T145807317057Z.zip，2022262字节，SHAd438f26be2ae067739c512e75f68d11e6230ef7cb1e238e794d37695c1f87d23；33项校验、双服版本与coverage2/global-score1声明及独立恢复演练/var/lib/racepick/restore-drills/aeeb83fac7b027f85a3ed36d通过，原库未替换。

timer随后恢复enabled/active(waiting)，NEXT2026-10-31 04:15:48 CST，LAST2026-10-30 04:15:25 CST。本轮已确认今天04:15:25至04:15:26旧单服状态下自动备份真实成功，文件scores-20261029T201526363516Z.zip，SHAe5cd3a9579250d088391ec70253f136e892b9a4e954322f2236e6a906ec8bd7b，28项哈希通过。新双服备份服务手动执行已验证，明天未来定时执行未验证，不记为成功、不创建监控。

### 公网与待用户验收

公网api.js、coverage.js/css、submissions.js/css、score_versions.js及styles.css匹配新包，/score-table匹配文件。国服原子快照与实际活动版本JSON一致；国际原子快照、公开三件套及659批准种子精确字节一致。双服覆盖表只读POST正常、游客level0非参考格隐藏、投稿目标服别正确；错误Origin/CSRF均403，游客两服投稿目录均401。仅建立普通游客会话，未创建账号/投稿/积分，不记录令牌。Nginx原业务5r/s burst30、统计2r/s burst10和原转发保持，本轮未修改或reload配置。

用户桌面与真实手机微信的计算/车库草稿/新入口、真实登录后的双服投稿目录/预填/证据/审核隔离仍待验收；一级两服独立选图、共享累计分/二级权益与降级按真实资格验收，无适用账号则记待验证，不造积分或假数据。国际正式写回/回滚因开关关闭未验收，历史独立已读/审核/反馈真实事件亦不扩写为本轮完成。

本轮只追加本地运维记录，未提交推送；既有未提交659数据/工作簿、未跟踪维护交接和用户文件保留，未同步工作簿、发公告、清理或创建监控。coverage2/global-score1启用后不得切回旧应用/旧备份工具，整套数据恢复必须先保全新增并另获授权。

## 2026-10-30 当前上线：bbd92687，运维验证完成，用户验收待进行

本轮服务器全部操作由用户逐步执行并完整回传，代理未登录生产。应用bbd9268769daca031b1267ed于00:49:44 CST启动；current及PID182239实际cwd一致、active/running（PID为当时快照）。源码3fbc599482855490f1859bd65b3ab53ada30b753，包内数据d06cd7d54838230976342c19c21638b90a5632ac。完整ZIP11050389字节，SHA256=186d4e3cea05516bbb0b4da44e6cf5015cf285467898a5aa2e7a5236cbb42645；外层清单、内层103文件和来源绑定通过，19wheel离线LinuxPython3.12安装及原生临时库迁移/锁/恢复自检通过。下方“未部署”均为历史阶段，不重复迁移或续跑旧步骤。

### 正式数据与组件

health为ok/production，主schema6，community/contribution/feedback/notification/usage/coverage均1，原开关正常。正式国服score_version=e209f3e32d0de1dfa7fe6c811a5d5c46；cars SHA469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c，成绩SHAb1d830d8390e38f4bd748d1a9341ee0a011226f97457df449e1a3496fe441e08。包内4458基线未覆盖线上score-state或车辆规则。

国际三件套公网哈希与新包一致，运行661条/46车/44图全覆盖/21OC/48特殊，版本0ae6a89d46c8e7707ee3387c7879b59bea69c911c54e07866c38953c8cb9f593；完整维护700、四区/高手、36参考、工作簿与台账未混入运行包。公开参考按实际运行版本计算；国服五区理论本次为玻璃/杰皇/21c（与冻结基线r兔不同），国际为evo狼崽/帝国/9x8，不为迎合包内参考名单改生产成绩。

现场coverage三表均不存在、schema0；停服MainPID0且timer暂停、备份服务结束后，以现场国服版本仅执行coverage首次迁移。already_migrated=false、existing_rows_preserved=true、test_coverage_imported=0；schema1、coverage_choices/events均0。未重跑旧组件迁移。最终47用户/23车库/6投稿、pending_batches0；贡献4/来源4/事件7/偏好3、反馈三表均0、通知事件6/已读6保持。没有伪造积分、投稿或导入测试库；公网CSRF检查仅新增普通游客会话，令牌只在内存未记录。

### 备份、恢复与调度

在线迁移前、停服最终、迁移后和新应用上线后四套成套备份均校验28文件并独立恢复演练，active_database_replaced=false；路径、完整SHA及各演练目录见[本轮部署机器回执](COVERAGE_DEPLOYMENT_RECEIPT_20261030.json)。停服最终恢复点为scores-20261029T163803325040Z.zip，SHA229af5d2ef77cd546c7227cffb237afceb70c50d34fdfb55f33fb97098007196；迁移后恢复点scores-20261029T164845516129Z.zip，SHA7c233fc5ec6f403ac74d72bc6e9c6803a4006ddca85b36faafcf443f7c22dc2b。

上线后真实racepick-backup.service于00:53:40至00:53:41 CST手动触发执行success/exit0，生成/var/lib/racepick/backups/scores-20261029T165341254431Z.zip，1983284字节，SHA7b4549427f8e6038cc2566baa8385dd08eaf5f63bc177e57922d6bd18abfcaba；usage/coverage均schema1，恢复演练目录/var/lib/racepick/restore-drills/499d5f5624436de2a985316f通过，原业务数量与成绩保持。

随后原timer恢复enabled、active(waiting)，NEXT2026-10-30 04:15:21 CST，LAST2026-10-29 04:19:47 CST。新组件服务手动执行和演练已验证；04:15:21未来定时执行未验证，不记为成功、不创建监控。此前10月29日自动备份28项哈希也已核验，详见回执。

### 公网核验与剩余用户验收

公网api.js、coverage.js/css、theme.css、ui.css、submissions.js及styles.css匹配新包；/score-table匹配覆盖表文件，/submissions与生产页脚/统计脚本注入后的HTML逐字节匹配。最初错误探测/submissions.html得到404，是静态白名单设计；纠正测试路由后通过，未修改应用或Nginx。

国服/国际/api/coverage/view只读POST均通过、每组上限48；国服83行、国际44行/46列。游客非参考格无成绩、国际格无国服投稿目标，错误Origin和CSRF均403。生效Nginx已有业务5r/s burst30、统计2r/s burst10、可信回环转发保留；本轮未改配置或reload，未做生产限流压测。

用户桌面/真实手机微信的双服计算、登录/分服车库草稿、参考列/高手星级/筛选翻页、触屏二次轻点及滑动取消、投稿登录回跳/预填/可选证据/失败恢复仍待用户验收。真实账本一级选图/二级权益及账号隔离按现有真实资格验收，无资格或无真实事件的场景留待验证，不补假数据。历史独立已读及审核/反馈真实事件提醒仍待真实事件。代理未独立操作手机微信。

只更新本地交接与部署回执，尚未提交推送。旧包/版本/备份/演练/测试环境/工作簿/未跟踪文件保留；未公告、清理或创建监控。coverage启用后不能简单切回旧无覆盖表应用，需要整套数据恢复时另获授权并先保全新增。

## 2026-10-30 接手只读核验完成：等待本轮范围确认

本轮用户授权接手核验；不续跑历史部署。北京时间00:28左右公网只读采样；以下为本轮实查，历史发布回执单独标注。未登录服务器、未上传、迁移、切换、重启、发布公告或清理；未提交推送或创建监控。

- Git：fetch origin成功，main/origin/main及ls-remote一致为336730fb7ab8266eab995d291a9e4158782e47b5；feature/score-coverage远端为3fbc599482855490f1859bd65b3ab53ada30b753，main较该源码只多5份文档变化。17个登记工作树均检查；主树跟踪文件原先干净，保留3个未跟踪文件（来源Excel、_star_curve_fit.py、gauntlet_data_shared.xlsx）；unify-home-style保留未跟踪examples/unlock-table/。其余树无未忽略修改。community-controls相对main仍独有文档提交6ef9062；feature/track-top-three显示较旧上游领先25，不代表有25项未合入功能，不自动推送或合并。
- 公网GET https://racepick.cn/api/health 为200、ok/production，主schema6，community/contribution/feedback/notification/usage均1，原开关正常。正式国服score_version=e209f3e32d0de1dfa7fe6c811a5d5c46，已不同于10月25日回执；没有读取私有业务数据或尝试覆盖正式成绩。
- 公网global-data-manifest.json与api.js逐字节等于本地保存的171d872a制品。国际仍版本1bb0253ce327210b6c02fb2c2ea49682ee628086fec6c7bc987326121b4a6efc、601条/44车/44图42覆盖/21OC/39特殊；coverage.js为404。styles.css同时匹配旧制品和当前本地，单凭该文件不能证明新样式上线。以上支持被读取公网资源仍为旧版；服务器current/PID/cwd、实际发布ID及coverage表状态未现场核验，不能把HTTP证据写成服务端版本实查。
- 历史已验收功能：双服计算/分服车库、账号/邮件、投稿审核/正式成绩写回、公告/账号管理、贡献榜、反馈、未读提醒/统计及切服修复等，以既有回执的各自范围为准。本轮只读健康与资源核验不重新证明全部用户流程。独立已读及投稿/反馈真实事件提醒仍留待真实事件验证。
- 最新待发布完整包仍为bbd9268769daca031b1267ed，源码3fbc599、数据d06cd7d。RacePick-Coverage661-20261030-bbd92687-delivery.zip实际11050389字节，SHA256=186d4e3cea05516bbb0b4da44e6cf5015cf285467898a5aa2e7a5236cbb42645；内层SHA256=fc0e6ae9fc0efaf3e85d111a9f8038cefe1f86f2d7be79db46a5a21aecadf8c4。本轮重新核对外层22文件、SHA清单、内层103文件逐项大小/哈希、无未列文件及双层CRC通过；未重构包或激活。旧9f/fe8包已被此交付替代，全部保留。
- 待发布范围包含样式/主页标志、单份审核意见、富士山提示及urs旧车库兼容、真实覆盖表/账本解锁、固定参考车辆列/48列密度/高手选星、精简国服投稿及触屏二次轻点。仅为既有构包范围记录，本轮尚未获得部署授权。
- 本地国服4458键，validate_data零错误；国际完整维护700键与运行661条必须区分。运行版本0ae6a89d46c8e7707ee3387c7879b59bea69c911c54e07866c38953c8cb9f593、46车/44图全覆盖/21OC/48特殊，build_global_data --check通过。17份DATA_HANDOFF_20261029清单SHA全部匹配；未同步、导出或逐格重验工作簿。包内4458基线不得覆盖线上score-state；700完整维护、国际四区/高手、36参考、工作簿与台账不自动入运行包。
- 本机Python3.14.4、Node24.15.0，已装fastapi0.138.1/uvicorn0.49.0/argon2-cffi25.1.0/openpyxl3.1.5/httpx0.28.1。127.0.0.1:8023(PID10332)、8024(PID5576)监听且health200/local/coverage_schema1；仅是本次进程快照，不重用PID执行后续动作；未观察到8021监听。测试服务/库未启停或修改。目标生产仍为Ubuntu24.04 x86_64/CPython3.12，未安装或变更依赖。
- 本轮实跑58项JS定向（算法/剪枝/成绩/状态/覆盖表/精简投稿）全部通过，启动冒烟通过，国服全库及国际生成器只读检查通过。历史全量117前端/173后端/88工具通过1跳过及Windows演练属于构包回执，本轮未重复全量后端、Linux原生、浏览器或手机微信验收。
- 两份国际服公告草稿仍存在，未发布；保留所有账号/成绩/反馈/备份、测试库、工作簿和未跟踪文件。根CLAUDE/context与本交接仅追加接手核验记录，保持未提交。

下一步先确认本轮范围：继续本地开发、只核验生产，或启动bbd92687部署。若授权部署，复用COVERAGE_DEPLOYMENT.md及本包流程，只先给用户当前一步服务器只读命令，核对current/PIDcwd、正式score版本、pending_batches、coverage实际schema、Nginx和备份timer/最近真实备份恢复，再逐步推进。现场coverage0才执行本组件首次迁移；完整schema1只升级应用并保留选图/事件，不重跑旧组件迁移。生产现行版本、调度及恢复点仍待现场证据，不编造。

## 2026-10-30 当前完整交付：参考列与精简投稿bbd92687（未部署）

源码3fbc599482855490f1859bd65b3ab53ada30b753已在远端feature/score-coverage核对，main已快进整合；本收尾文档按授权随main推送，最终远端HEAD另记本地PUSH_RECEIPT。数据仍固定d06cd7d54838230976342c19c21638b90a5632ac，17份交接SHA及25份数据/工作簿/旧包保护路径保持。

最终交付包repo/.production-build/RacePick-Coverage661-20261030-bbd92687-delivery.zip，11050389字节；发布ID bbd9268769daca031b1267ed；完整SHA256 186d4e3cea05516bbb0b4da44e6cf5015cf285467898a5aa2e7a5236cbb42645；内层SHA256 fc0e6ae9fc0efaf3e85d111a9f8038cefe1f86f2d7be79db46a5a21aecadf8c4。103运行文件/依赖、19锁定离线wheel、外层22文件。本包替代下方9f/fe8交付；所有旧包保留原SHA，不混用旧清单或旧参考展示说明。

包含紧凑48车、参考车列而非地图整行、高手独立选星级、格子直达共用精简投稿页/证据可选、手机格旁二次轻点提示和滑动取消、统一导航按钮。普通跑法参考国服五区理论3列/高手7列、四区理论5列/高手9列，国际3列；其余仍按真实账本解锁。国服包内4458基线不得覆盖生产score-state，国际661条/46车/44图、21OC/48特殊，完整维护700/国际四区高手/36参考/工作簿不入运行。

JS117、后端173、工具88通过1跳过；制品来源逐字节Git回比、SHA/字节数/白名单/CRC、Linux目标离线解析及独立暂存通过；Windows临时库组件迁移/幂等/模拟锁/非空选图事件备份恢复、新只读POST及参考列HTTP通过。Linux原生锁/权限、正式库/备份timer与真实手机微信验收待云端，不把本地演练当上线。

coverage_schema保持1。现场0才执行本组件首次迁移并绑定真实国服score版本；现场1只升级应用并保留选图/事件，不重复迁移或清空。新schema异常/部分表即停。没有新增Nginx、服务或环境配置要求，但须核验新POST与静态资源路由、原业务/统计限流及成套备份恢复。保护原组件/score-state/真实新增，不重跑旧迁移。

[本轮云端可复制提示词](COVERAGE_CLOUD_PROMPT_20261030.md)、[机器回执](COVERAGE_RELEASE_RECEIPT_20261030.json)、[功能与测试](COVERAGE_RELEASE_20261030.md)、[已有站点升级顺序](COVERAGE_DEPLOYMENT.md)。此对话未服务器操作、未上线、未公告、未清理或创建监控，未向其他对话发消息。下方记录均保留为历史证据。

## 2026-10-29 最终交付修正：9f9b2e2b，替代fe8候选（未部署）

最终源码7dcd70248d9aac90faa95c43b4abba02e6737160已在origin/feature/score-coverage核对；数据仍固定d06cd7d54838230976342c19c21638b90a5632ac。真实多列表复核发现首组只能看见部分地图参考，已把同一公开样本固定为地图行旁纯文字，翻页/筛选不会消失，无参考/成绩按钮、不增加公开范围。国服投稿、权限、迁移及数据范围不变。

最终发布ID：9f9b2e2bba7ba566a0665332。归档repo/.production-build/RacePick-Coverage661-20261029-9f9b2e2b-delivery.zip，11047016字节；完整SHA256 373bad1e795f5f0000f4cc7aeb7559eadfbb72c141404609bff6639256b67568；内层SHA256 2a593ce59d2b586845bdb5767452d6187323ccd8bc96952b54109ef09fb3e47f。103运行文件/依赖、19锁定wheel、外层22文件；最终包重新核验来源、逐文件哈希/字节数、CRC和独立暂存、临时库迁移/模拟锁/非空选图事件成套恢复均通过，Linux原生仍待云端执行。

基线全量JS110/后端170/工具88通过1跳过；最后修正定向后端11/前端4通过。最终浏览器确认筛选杰哥列时地图行仍显示固定恶魔普通理论参考，一级仅首张地图值26可见、其他***，没有成绩按钮。假账号/测试SQL/旧Demo/原始维护资料不入包。真实用户逐项与生产手机微信验收待进行。

源码与数据按功能独立提交，main收尾文档按授权推送；远端核对留本地PUSH_RECEIPT。未上传服务器、未操作生产、未上线、未公告或清理。旧fe8完整包SHA仍为ca73947e14bbe8bc3671531c5b4f5398f4531da71878c0db34dd53d9ec347953，原样保留但不作为本轮最终部署交付；下方fe8完成节属于候选阶段，以本节和最新机器回执为准。

[最终机器回执](COVERAGE_RELEASE_RECEIPT_20261029.json)、[最终云端提示词](COVERAGE_CLOUD_PROMPT_20261029.md)、[升级/回退顺序](COVERAGE_DEPLOYMENT.md)。

## 2026-10-29 覆盖表真实版构包完成：fe8a9aff（未部署）

已完成真实覆盖表、国服投稿预填和账本解锁，整合此前样式/主页标志、单份审核意见、富士山及国际车库兼容。源码a8ad5c36a113033375c84c2ef683fb1f312907e7与数据d06cd7d54838230976342c19c21638b90a5632ac已在origin/feature/score-coverage核对；main本地包含相同功能，本收尾文档按授权随main推送，实际远端核验另记本地PUSH_RECEIPT。保留既有合并历史，不重写原提交。

- 发布ID：fe8a9aff0cf6871d5d7f0212。
- 完整包：repo/.production-build/RacePick-Coverage661-20261029-fe8a9aff-delivery.zip，11046200字节。
- 完整SHA256：ca73947e14bbe8bc3671531c5b4f5398f4531da71878c0db34dd53d9ec347953。
- 内层SHA256：821485c5f05d778f15ca39719c49bff1238dbff122f6b6884089360a5dd35e60。
- 内层103文件/依赖，外层22文件；CRC/逐项SHA和字节数/白名单/来源/独立暂存全部通过。19个锁定wheel离线LinuxPy312目标解析通过。
- 国服包内基线4458键；国际661/46车/44图全覆盖/21OC/48特殊。实际免费样本国服166、国际44（包内数据口径），正式国服按现场score-state；17源文件SHA保持。工作簿、维护700/36参考、账号/统计/反馈/测试库、凭据与原始证据不入包，旧包保留原SHA。
- JS110通过，后端170通过，工具89执行/88通过/1项Linux专用跳过；最终定向覆盖表11和前端4项通过。包内Windows HTTP与临时库迁移/幂等/模拟锁/含非空选图及审计恢复通过。首轮独立测试脚本的SQLite关闭问题只修正于本地harness，应用包无变动。真实假账号浏览器已跑通登录回跳/投稿待审/一级选图与不扣分，390px整页不溢出。
- 原型UI已获用户验收；真实版逐项用户验收、Linux原生锁/权限/运行时、生产迁移与生产桌面/手机微信验收待进行，不把本地或未来计划当作已完成。

本轮未上传服务器、未操作生产、未上线、未公告、未清理或监控。生产需新版本工具显式coverage_schema1迁移、成套备份恢复和兼容门禁；无额外Nginx/服务配置变更需求，但必须现场核验。国服score-state不被应用包更新，国服新成绩/规则同步另行审核协调。包与旧测试环境、模拟Demo、失败测试现场及所有工作树继续保留。

[完整机器回执](COVERAGE_RELEASE_RECEIPT_20261029.json)、[可复制云端提示词](COVERAGE_CLOUD_PROMPT_20261029.md)、[部署顺序/回退](COVERAGE_DEPLOYMENT.md)。下方“A未合并/数据未提交”均为此前阶段，不续跑历史任务。

## 2026-10-29 本轮新授权：真实覆盖表/投稿解锁、最新数据、分组推送构包

用户已明确包含覆盖表真实实现后构包，并授权最新数据与功能分别提交推送。数据已固定d06cd7d54838230976342c19c21638b90a5632ac；真实模块在feature/score-coverage独立开发，先前“A不合并”仅对应旧阶段，独立模拟Demo仍不入包。国服真实投稿与账本权限、公开样本和显式迁移已接入；实现及本地检查见 [本轮发布准备](COVERAGE_RELEASE_20261029.md)，部署顺序以 [覆盖表升级](COVERAGE_DEPLOYMENT.md) 为准。后续完成回执固定具体包/提交/SHA；本段不提前宣称构包或上线。

## 2026-10-29 本地合并完成：756ed5f，数据改动保留未提交，未发布

样式/主页标志、单份审核意见、动态富士山缺项提示和国际旧昵称车库兼容已合入本地main。新车从交付目录自动生成，不改国服规则或估算。实际661/46/44全覆盖快照和合并后工作区JS106通过，后端159通过、工具88通过/1项Linux专用跳过；17交接文件哈希通过，26保护文件SHA和mtime不变。六份最新数据/工作簿及10月29日交接未代提交，A原型仍不在Git树中。未推送/构包/生产操作；后续data/main推送可能带出已合并功能，需用户协调范围。完成明细见 [合并回执](FEATURE_MERGE_RESULT_20261029.json) 和 [配套改动说明](FEATURE_MERGE_20261029.md)。

## 2026-10-29 本轮授权本地功能合并与配套修正（未发布）

整合样式统一、主页标志和审核意见改进，按实际国际数据动态显示富士山缺项，验证新车由目录自动出现并兼容Ultima RS旧车库到urs。本轮只合并功能；主repo六份未提交数据/工作簿和10月29日交接原样保留，不代提交。A原型不暂存/不合并；不推送、不构包、不操作生产。来源、修改范围及验证见 [功能整合核对](FEATURE_MERGE_20261029.md)，最终本地合并提交和完整检查结果由完成回执记录。

## 2026-10-27 审核意见合并输入：本地待验收，未发布

按用户授权完成首次审核单份意见输入，复用现有两个保存字段；要求补充不受未完成评分阻塞；独立调分保留说明且不覆盖原审核意见，旧记录不同文字和历史保留。前端104项、后端审核/贡献/通知35项通过，浏览器确认单份输入。无数据迁移、计分变更或正式数据操作；未提交/推送/构包/上线，A方案仍不合并。详见 [审核意见改进](REVIEW_OPINION_20261027.md)。

## 2026-10-27 样式验收与标志范围确认

用户确认其余样式本地验收通过；RacePick仅在主页“擂台选车助手”旁保留，其他功能页和解锁Demo中的标志已移除。A方案继续独立保留、不合并，原型文件不纳入后续样式提交/发布范围。本轮没有提交、推送、合并、构包或上线；云端仍是此前发布版本。

## 2026-10-26 页面样式统一：独立分支本地待验收，未发布

按用户要求，以当前主页为基准统一各功能页及解锁Demo的颜色、控件、标题和页面外壳，保留RacePick标志。分支feature/unify-home-style，基线9cf09ed；六份公网样式只读核验与本地基线相同，偏差确实存在于线上资源。已本地修改，尚未提交/推送/合并/构包/上线。JS97通过、后端27通过、工具15通过/1项Linux专用跳过，浏览器桌面与390px检查完成，用户验收待进行。主repo并行数据/工作簿变化仅观察、未写入，详情和验收入口见 [页面样式统一](STYLE_UNIFICATION_20261026.md)。下方已上线171d872a仍为历史部署证据，不代表这些新样式已发布。

## 2026-10-25 最新上线交接：未读/统计与国际601已激活，真实事件提醒待验证

本轮服务器升级、实际新组件迁移、Nginx配套、激活、新版成套备份恢复及timer恢复均已完成。用户确认桌面浏览器和手机微信的双服计算、登录、分服车库草稿、统计权限及账号活动筛选正常。独立已读及投稿人审核/反馈回复提醒因没有真实新事件，明确留为待验证，不记为生产验收全通过。下方“未部署/待运维”均为构包或历史阶段；本节不构成自动继续操作授权。

### 实际版本与数据边界

服务器命令均由用户逐步执行回传，代理未登录服务器。应用`171d872a414dea28be25eaa1`，源码`7651da519be92b7ae6ea184d2c30a985607c30f5`，包内数据`cbe9ea3dd3d0c130bef8dd15f890d618167e1539`。2026-10-25 11:05:50 CST启动，current和PID156079的cwd均为`/opt/racepick/releases/171d872a414dea28be25eaa1`，active/running；PID仅是当时快照。旧66b9d32c及旧包保留，启用新组件后不能以旧工具或手工链接绕过兼容检查回退。

上传归档11017686字节，SHA256 `05288fd2552c83d4337ac43d1dc22fce51c419a6f8586a648ac6f163faf4522b`。外层20项SHA、内层96文件、19锁定wheel、源码/数据绑定和仅暂存阶段均完整回传核对通过。Linux离线安装和原生临时库自检由用户确认通过，完整安装日志未回传；不把构包时Windows模拟锁证据替代本轮Linux验证，也不扩写为生产全量测试。

正式国服成绩在本轮开始即为`4bdaa0734cbfa4b178d1cbb1a081a8c7`，不是昨日42d62fde；40用户/21车库/3投稿，pending_batches0。激活及最终health均保持此正式版本。国服活动cars.json SHA256 `469aca118891c398d1aa2777721d50449cffa2e48c984bbd57ede0c7cde92d3c`，gauntlet_data.json SHA256 `8524833657eb740cc5d3c4bd8b90b815a1506ad3c3e64b4233a7eed2b9abcf86`。包内国服4423键只是冻结基线，本轮没有整包覆盖score-state，没有同步国服成绩或五车规则；如需同步仍须独立列差异并协调数据维护确认。

国际运行版本`1bb0253ce327210b6c02fb2c2ea49682ee628086fec6c7bc987326121b4a6efc`，五区满星理论601条、44车、44图42覆盖、580非OC/21OC、562普通/39特殊。640键完整维护、四区/高手、36参考及工作簿不进入运行。本轮601与昨日曾保留的601不是同一个数据版本，不以相同条数推断数据相同。

### 新组件与正式库保护

按新包工具及原config执行，未重新初始化正式账号库、未重跑旧成绩/贡献/反馈迁移。停服确认MainPID0、应用inactive及timer暂停后，notification_production migrate绑定上述正式成绩版本：notification_schema1，events/reads均0，existing_rows_preserved=true、test_notification_imported0，旧内容作为已读基线；内部备份`scores-20261025T030202218287Z.zip`。usage_production initialize绑定同一正式成绩版本：usage_schema1，existing_accounts_preserved=true，内部备份`scores-20261025T030232342585Z.zip`。两份内部备份路径有回传，SHA未单独回传，不补造。usage.sqlite3实测racepick:racepick、0600，服务用户读写检查通过。

最终health为ok/production，主schema6，community/contribution/feedback/notification/usage均schema1，各组件开关及score_writes均true。原业务行、贡献counts1/1/1/2及反馈三项counts0保持。未导入演示账号、通知、统计数据，未伪造生产投稿或刷流量。

### 成套备份与独立恢复

新版本工具用于本轮各备份/演练。迁移前在线备份及演练仅获用户确认通过（版本保持、pending0、正式库未替换、两新schema0），具体ZIP路径/SHA/演练目录没有回传，保留缺项。

其余三次均有完整回传。备份目录`/var/lib/racepick/backups/`，演练目录`/var/lib/racepick/restore-drills/`：

| 阶段 | ZIP文件 | 字节 | SHA256 | 演练目录ID |
| --- | --- | --- | --- | --- |
| 停服最终（迁移前） | scores-20261025T030050154616Z.zip | 273021 | 2ec55e97544635967940ada3641c9703aaf9c0198c2d86bd5556456be5da65f7 | 88e9d955bb771d251e94720c |
| 新组件完成（激活前） | scores-20261025T030302148469Z.zip | 274625 | ff6fd2cb40ee914699f9fe05cef90de019912f9b98d40dd3f802e598ba697c71 | 5d9ee3861a70233fb36bfcce |
| 新版在线（页面验收后） | scores-20261025T030758901428Z.zip | 275367 | 806b6bc5c6e2d5edcefd4e6e76b590506e27cfd841cd240896b85118cfb3fa37 | 7bddb5f56b5f8c95ce0c3272 |

三份均racepick:racepick、0600，恢复结果均40用户/21车库/3投稿、pending_batches0、active_database_replaced=false，成绩版本保持。后两份包含usage.sqlite3，通知/统计schema均1；最终通知events/reads仍0。后两份accounts快照SHA相同`79271fad249c9e9d855f0a5d43b4630b998543a1ae158ef5830f3cd2afe337e0`；统计快照由`5e8b6343d8946cc1cbf8c6638c0654671886aaecbd85420adda3568effdbcd5d`变为`7948d470785891114ea84c1d585d82a0d76d53e80567a89bb5be99463c3d1891`。上线后统计库发生变化，不称全部文件/三份备份完全相同，也不由哈希推断具体事件数量或内容。

### Nginx配置与调度

完整实际配置核对后备份到`/root/racepick-deploy/20261025-unread-usage-171d872a/nginx-before-20261025-110359/`，root:root、0644。原站点SHA `3643f42a86a7237098f442f524e5c75d5d30afa89ea36b44c91260c26517edf2`，原rate SHA `2a48fb2cd84e3ed7cd18018cc458145a52a2e9a3f729e78a59f4af6edbd42a6a`，备份逐字节相同。

成套写入新map/zone及站点第二个limit_req：精确POST `/api/usage/session`与`/api/usage/events`使用独立racepick_usage_events桶2r/s、burst10；原业务racepick_api_requests仍5r/s、burst30，启动GET/HEAD豁免保持，超限429。站点仅新增统计桶引用，证书、80/8080、转发及其他站点保持。nginx -t通过，11:05:06 CST reload退出0，active/running。新rate SHA `9f7c5e7ee70765b9a89a7fdaf6901086fe230e2034cca48f5ba056c62feab428`，新site SHA `d14f300947a4a9d35eab953e2b587f609763c4dab9783eed614aab280e131dee`。本轮未做生产限流压测。

11:08:00 CST，以上新版在线备份演练通过后恢复原racepick-backup.timer，enabled、active(waiting)，NEXT2026-10-26 04:15:51 CST，LAST2026-10-25 04:18:39 CST。只读预检已确认10月25日04:18:40自动备份真实成功，文件`scores-20261024T201840512950Z.zip`，退出0；这是升级前旧版自动执行，不是新组件自动备份证据。本轮新版新组件成套备份实际由CLI执行；10月26日计划未到期，不宣称已成功。

### 验收边界与收尾

用户确认桌面和手机微信的双服计算、登录、分服车库/草稿、统计权限和活动筛选正常。独立已读、投稿人审核及反馈回复提醒待真实新事件验证，不伪造生产事件补验，不创建监控。代理未独立操作手机微信。

本地结构化回执：工作区`本地归档/unread-usage-deployment-20261025/DEPLOYMENT_RECEIPT.json`。用户随后授权仅提交推送本轮4份部署/交接文档，完成远端核验后暂停；独立已读及投稿人提醒继续待真实事件验证。不改程序、数据、台账、工作簿或既有发布包，不发布公告、不清理或创建监控。根CLAUDE/context和本地回执不纳入Git提交。构包时的PACKAGE_VERIFICATION等冻结回执保持原字节，其PENDING由本节后续现场证据补充，不重写历史包。公告未发布；旧包、旧版、备份、演练及测试数据全部保留，不自动清理或创建监控。

## 2026-10-25 合并构包完成（未部署）

已按本轮授权将未读提醒/使用统计与冻结数据合并至main并推送。构包源码固定 `7651da519be92b7ae6ea184d2c30a985607c30f5`；数据固定 `cbe9ea3dd3d0c130bef8dd15f890d618167e1539`。后续本完成回执是文档提交，不改变包内源码绑定。

- 发布ID：`171d872a414dea28be25eaa1`。
- 完整归档：`repo/.production-build/RacePick-UnreadUsage601-20261025-171d872a-delivery.zip`（11017686字节）。
- 完整归档SHA256：`05288fd2552c83d4337ac43d1dc22fce51c419a6f8586a648ac6f163faf4522b`；同目录独立 `.zip.sha256.txt`。
- 内层SHA256：`3f78707b58a623b1f285072bbd1c0ce4e6932ba0ae34faf1d4665bc087f5e649`。内层96文件/依赖，外层21文件；包内逐文件校验及外层完整归档复核通过。
- 数据7输入、8本地来源、五份运行JSON精确字节、实际国服4423键和国际601/44/21OC/39特殊已核对。640完整维护、四区/高手、36参考、工作簿、账号凭据和测试数据不入包；生产国服score-state不能被应用包覆盖。
- JS97通过；Python239执行、238通过/1项Linux专用跳过；构包工具10通过；19个锁定wheel目标解析通过。独立暂存包Windows HTTP和临时库新组件迁移/幂等/模拟锁/成套恢复通过；shell仅语法检查。用户已本地验收，Linux原生安装/锁/属主、生产迁移、Nginx配套与生产桌面/手机验收均待运维执行。
- 原7数据/8来源、主树3未跟踪文件、根CLAUDE/context的SHA与mtime_ns未变，旧包SHA未变。原8016/8017演示环境、所有其他工作树保留。新integration树为release/unread-usage-20261025，data树固定cbe，build树固定7651；均保留且干净，不清理。主树仅原3未跟踪文件；没有待提交功能修改。

[机器可核验完成回执](RELEASE_RECEIPT_20261025.json)、[可直接复制的云端提示词](UNREAD_USAGE_CLOUD_PROMPT_20261025.md)、[升级顺序与回退条件](UNREAD_USAGE_DEPLOYMENT.md)。本轮未访问生产、未正式迁移、未上线、未发公告。冻结数据交接中的旧“不构包”是之前阶段记录；本轮构包由用户后续授权，不能据此推定生产已部署。

## 2026-10-25 本轮授权：合并已验收未读/统计并构包（未上线）

用户已授权将feature/unread-notifications的b91e0e1与冻结数据cbe9ea3整合，准备完整可校验包，并要求完成后给出可复制给云端运维的部署交接提示词。本轮授权覆盖此前“仅接收、不合并、不构包”的阶段限制；仍不授权本开发对话访问生产、执行正式迁移、上线或发公告。

独立整合工作树integration-unread-usage-20261025基于cbe9ea3合并已验收功能，无文件冲突；源数据7文件不变，数据专用干净检出release-data-20261025固定cbe9ea3。已审阅更新国际44车及国服81/55车池、77条规则的旧启动断言，并增加已批准五车双区/五星派生核验，不修改成绩、车辆规则或工作簿。集成JS97通过；Python239执行（238通过/1项Linux专用跳过）。

构包器增强为五份双服运行JSON全部固定读取数据提交，新增独立快照覆盖源码目录中数据的回归；保留两份国服快照的旧调用兼容。原生自检增加通知/统计迁移、锁与恢复检查。Linux实际安装/原生运行、生产数据/配置兼容及公网验收仍待云端运维逐步执行，不以Windows测试冒充。

完整交付信息以本轮RELEASE.json、PACKAGE_VERIFICATION.json、外层SHA清单及后续完成回执为准，本段不提前宣称构包完成。国服score-state不能被代码包覆盖；国际601/44/21OC/39特殊，版本1bb0253ce327210b6c02fb2c2ea49682ee628086fec6c7bc987326121b4a6efc。最新执行顺序见 [升级交接](UNREAD_USAGE_DEPLOYMENT.md)。

## 2026-10-25 完成回执：功能源码已推送，数据仅接收核验

功能源码提交 `a5f09208d6843db1e895320f99205998301947a0` 已推送 `origin/feature/unread-notifications`，本轮 `git ls-remote` 已核对一致；用户确认本地验收通过。该源码提交不含任何成绩JSON/工作簿、账号/统计/测试数据库、凭据、截图或本地原始维护来源。后续仅交接文字提交不改变此功能源码绑定。

数据 `origin/main=cbe9ea3dd3d0c130bef8dd15f890d618167e1539` 同轮远端核对一致，接收回执已随功能分支交付。功能与数据未合并、组合验收未运行；主repo仍为数据提交，功能树保留原599基线。未来44车集成的两处旧49断言仍待授权处理。

本轮到功能分支提交推送和数据接收为止：未合并main、不构包、不上线、不操作生产、不发公告、不清理环境或创建监控。原用户文件、测试环境及其他工作树保留。详见 [数据接收回执](DATA_RECEIPT_20261025.md)；完整本地推送回执保存在 `.local-accounts/usage-validation/feature-push-result-20261025.json`。

## 2026-10-25 用户本地验收通过：功能分支提交推送与数据接收

用户已确认未读提醒和使用统计（含账号管理整合、移除操作记录按钮）的本地验收通过，授权提交推送现有feature/unread-notifications分支。本轮不合并main、不构包、不上线、不操作生产或发公告。具体功能提交SHA以本分支Git及完成回执为准，不能使用基线90b2dd9冒充功能实现提交。

新数据main=cbe9ea3dd3d0c130bef8dd15f890d618167e1539已fetch并核对远端一致，7文件工作区/提交/清单字节及SHA均相等；8份本地维护来源SHA/大小/mtime_ns通过。国服4423键、校验0错；国际完整维护640键，运行仅五区满星理论601条、44车、21OC、39特殊、版本1bb0253ce327210b6c02fb2c2ea49682ee628086fec6c7bc987326121b4a6efc。只读生成器--check通过，未写出或回代工作簿。

详见 [本轮数据接收回执](DATA_RECEIPT_20261025.md) 与机器清单。功能树仍原基线/599数据，不合并新数据；两处旧49车测试断言是未来44车集成轮待审事项，本轮不改测试迎合数据、不将两者称为组合验收通过。历史本地待验收状态以本节用户确认覆盖；原JS97/Python238（1跳过）验证仍限功能原基线。

原数据、3个主repo未跟踪文件、测试环境、旧包、备份及其他工作树保留。生产统计库/未读迁移、Nginx配套和Linux原生验证仍待未来授权；原始434来源和视频未在本轮逐项补验。下方旧“未提交/待验收”段落保留为历史，不作为本轮最新状态。

## 2026-10-25 本地后续整合：账号管理承载每日活动（未提交）

用户确认按账号查看访问与活跃。账号列表新增最近活动、活跃分类及排序，合并原重复列；点击账号查看默认近7天的每日明细，支持7/30/90天、自选日期、服别和每页10天。统计页移除全站每日长表和重复账号表，保留汇总/热力图及账号管理入口；游客不混入账号列表。随后按用户意见移除「操作记录」按钮/展示区，历史服务端记录和业务权限规则保留。

本轮仅界面与只读查询整合，不变更统计采集或库结构，不改成绩/规则/工作簿，不删历史账号/审计/统计数据。独立工作树及未提交状态保持；不提交推送、构包、上线、生产操作、清理或监控。原Nginx与迁移配套要求沿用统计说明，未在本轮重跑生产相关操作。

验证：JS97通过、Python238执行（237通过/1个Linux专用跳过）、语法和CRLF兼容diff检查通过。浏览器验证活跃筛选、7天默认、30天10+9行分页且无重复、单服筛选、无操作记录按钮，以及统计页336格热力图保留且两张长表消失。演示记录不代表线上分布，整体用户验收待确认。

验收入口 `http://127.0.0.1:8017/admin-accounts`；点击邮箱或「访问与活跃」。数据仍为ad8cc69d5fec46417fee121c演示库，原8016不重建。用户当前标签页未主动刷新；手动刷新可看到最新界面。完整边界和截图见 [使用统计](USAGE_LOCAL.md) 文末。

## 2026-10-25 独立工作树：使用统计本地开发完成（未提交，待用户验收）

本节仅适用于 `feature/unread-notifications` / `E:/hzz/work/MutualExclusionAllocator/unread-notifications`，基线 `90b2dd9fb84f7ba99556ff71f712d69f1c128045`；旧未读实现与本轮统计集成均保留未暂存/未提交，不覆盖主repo其他对话的成绩维护与生产交接。

已实现访问、可信实际交互的活跃分钟、少量关键功能事件及仅超级管理员可读取的统计页。账号跨设备去重、游客随机标识近似统计，两组分栏；北京时间热力图、日周月活、新识别/回访与新注册区分、两服比例、功能次数/人数和账号最近访问/交互。自动重算、后台放置、资源请求、未读轮询及统计页自身不计实际活跃。没有历史线上数据回填。

统计独立SQLite，不改变账号主schema；业务成功后尽力记录，统计失败不阻止业务。窄游客接口仍校验同源JSON和签名上下文，业务CSRF保持。原始90天清理仅提供显式预览/执行工具，无自动清理任务；长期汇总保持跨日人数去重。未来生产需显式初始化统计库、成套备份/独立恢复演练，以及成套更新Nginx独立统计限流桶；本轮不执行生产操作或构包。

最终前端97通过；Python236执行、235通过/1个Linux专用跳过。Windows临时库中的模拟服务锁及Windows Nginx环回假接口对照不冒充Linux/生产验收。浏览器验证主动生成/自动重算区分、本机/账号保存、两服切换及统计页不自计；功能页与336热力图数据格正常。统计页含明确标记的模拟数据，不是线上用户分布。

新验收入口 `http://127.0.0.1:8017/admin-usage`，演示库 `.score-version-sandboxes/ad8cc69d5fec46417fee121c`，其LOGIN说明保留。原8016未读验收库不重建。运行成绩/车池JSON、工作簿与未读内核哈希保持；其他对话修改、旧包和测试资料保留。本轮不提交推送、不合并、不上线、不发公告、不创建监控。整体本地用户验收待确认。

完整边界、复现和验证记录见 [使用统计](USAGE_LOCAL.md)；未读说明见 [未读提醒](NOTIFICATIONS_LOCAL.md)。后续先确认允许提交/构包的功能与数据范围，不把本地未提交实现当作已发布版本。

## 2026-10-24 独立工作树：按账号未读提醒本地开发完成（未提交，待用户验收）

本节仅描述 `feature/unread-notifications` / `E:/hzz/work/MutualExclusionAllocator/unread-notifications`；不覆盖主repo其他对话正在进行的数据维护或生产交接。基线为隔离时main最新 `90b2dd9`，本轮不合并、不提交推送、不构包、不上线。

新投稿/重提提醒所有管理员；审核结果和质量评分调整提醒投稿人；现有问题反馈的新建/补充提醒超级管理员，回复提醒提交人。读位置按账号独立保存，读取不改变处理状态，不清除别人提醒。外层菜单、内部入口和条目逐级导航；用户选定首页及卡片右上角小圆点。管理员反馈页去掉重复「全部反馈」按钮及页面级汇总点，仅条目提示。首页用户反馈待处理数量仍按真实pending状态计数。

最终前端92项通过、Python222项执行（221通过/1个Linux专用跳过）、JS语法及diff检查通过。真实浏览器检查超级管理员首页/菜单/反馈列表；其余账号隔离、事件游标竞态、重提/评分更新及成套备份恢复有隔离自动化测试。Windows临时库测试中的服务锁是模拟，生产Linux仍待核验。

新增notification_schema1和显式迁移工具，旧内容为已读基线、不回填事件；启动不自动生产迁移，部署兼容检查拒绝不支持新状态的旧包。未来发布仍需按当轮授权固定源码与数据、停服成套备份演练及显式迁移；本轮没有生产操作或交付包。现有成绩/车池/工作簿未改，主repo其他对话未提交修改保留。

本地验收 `http://127.0.0.1:8016/`；演示库 `.score-version-sandboxes/997fbb7750fbff84380f4c19` 和LOGIN保留。详见 [功能、复现和验收边界](NOTIFICATIONS_LOCAL.md)。本轮修改全部留在本工作树未暂存/未提交；用户只确认样式与局部交互，整体用户验收尚待完成。

# RacePick 云端运维交接（2026-10-24 更新）

## 2026-10-24 最新：快速切服修复已上线验收，599条保持，完成文档推送后暂停

本轮部署、备份恢复及公网验收均已完成，没有待续跑的部署步骤。服务器命令由用户逐步执行并回传，代理未登录服务器。下方“尚未部署”“等待范围确认”和旧版本状态均为历史记录，以本节为当前交接结论。

- 用户授权仅部署快速切服修复；沿用599条五区满星理论。本地601条、616键完整维护、工作簿修改和正式公告草稿继续保留，不提交数据、不发布公告。OC插值/外推仍暂缓。用户确认桌面浏览器与手机微信验收通过后，授权仅提交推送本轮部署文档，完成后暂停，不清理或创建监控。
- 实际应用为`66b9d32c1857d2b3c2cc533f`，源码/包内数据绑定`4ff5f6f159bf579c3dd058f78d7bc7f6659967ce`；2026-10-24 18:18:15 CST启动，current与当时PID150824的cwd均为`/opt/racepick/releases/66b9d32c1857d2b3c2cc533f`，active/running。旧应用`0ee524e31734b44fb7771b79`保留。PID仅为验收时快照。
- Ubuntu24.04.5/x86_64/Python3.12.3/Nginx1.24.0。上传包10949010字节，SHA256 `f35d888ef61a5a9591a99e1bccecc433946a166136b36322e9963605ca15171a`；用户完整回传交付16项SHA、85文件包校验、五份JSON与旧应用字节相同、暂存未激活成功。19锁定wheel的独立运行环境安装及临时库自检由用户确认通过，完整安装日志未回传，不写成生产全量测试。首次启动等待的一次curl连接失败后健康检查成功，不是最终启动失败。
- 生产只读证据已确认旧全站5r/s、burst30桶拦截api.js、styles.css、国际三份JSON及/api/scores/snapshot，错误日志和访问日志均明确429。两份配置已成套调整：公开资源/启动只读GET、HEAD使用空key，其他请求保持5r/s、burst30、超限429，新zone为`racepick_api_requests`。站点仅替换旧limit_req的zone名称，证书、转发参数、80重定向及127.0.0.1:8080监听保持。nginx -t通过，18:17:09 CST reload退出0、active/running。未执行生产登录/写入限流压测；保护额度依据实际配置，受保护接口仍触发429的对照为上轮本地证据，不混称本轮生产测试。
- Nginx原配置保留在`/root/racepick-deploy/20261024-switchfix-66b9d32c/nginx-before-20261024-181645/`：racepick-rate.conf SHA256 `f7114b0c3cce3725a1da3d7f3d19b07712b82beb1253fb6569beec47b40bfb9a`；racepick-site.conf SHA256 `db452b2382fb3493f0198779e363c7e80f5c7427a8d64166e7e4828edf04275d`。不能只回退应用就认为Nginx配置也已回退。
- 最终health为ok/production/schema6，community/contribution/feedback各schema1，contributions/feedback/score_writes均true；国服成绩版本`42d62fde9b81197ac0558087a9a25f97`保持。国际数据版本`f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e`，仅五区满星理论599=578非OC+21OC、561普通+38特殊，49车44图42有值；四区、高手和完整维护没有进入运行包。未迁移/初始化正式库，未覆盖score-state或导入本地账号/测试数据。

三次成套备份与独立恢复演练均有本轮完整回传，备份目录`/var/lib/racepick/backups/`，演练目录`/var/lib/racepick/restore-drills/`：

| 阶段 | 备份文件 | ZIP SHA256 | 演练目录ID |
| --- | --- | --- | --- |
| 旧版在线 | scores-20261024T101536222957Z.zip | 993a1f3d6c558ed5e551494122904a0172cd5f898a5b4da4d845747e8468c916 | 0dab4559cae2d89d0825b079 |
| 停服最终 | scores-20261024T101744315933Z.zip | 5683d4f1428adce8b485ac815e0af9354cc0be11fc1e8fa6ebfcf38f2b99b66f | 42528d264180abbdfa386c5f |
| 新版在线 | scores-20261024T101841793136Z.zip | 7baef80f7f2ba7104c785bc1e2d29db050490b7f7da4c5900cff13466bf4b6a5 | 64035cd63ef8aeb26f45cba8 |

三份均161263字节、racepick:racepick、mode600，内部全部文件哈希一致。SQLite快照SHA256 `565aa54f8eda24e49675ae2d83e9783736e81d65ba074fdf041b83f384361d33`；国服活动成绩JSON SHA256 `bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9`。三次恢复结果均39用户/21车库/3投稿、pending_batches0、active_database_replaced=false；贡献schema1及counts0/1/0/1，反馈schema1及三项counts全0。旧历史部署缺失的最终备份路径仍属旧轮缺项，不以本轮路径替代。

18:18:43 CST恢复racepick-backup.timer，enabled、active(waiting)，LAST2026-10-24 04:16:12 CST，NEXT2026-10-25 04:18:33 CST。恢复后health正常。这证明调度恢复，不表示10月25日任务已执行。

公网78次只读GET（6种启动资源各13次、并发6）全部200，无失败/429；公网api.js逐字节等于新版，SHA256 `3663cfed057fd0158b8d92b03effa104c2e006edd1c51c07a5ade3ba0256f837`。用户明确确认桌面和手机微信均通过：连续切服无报错，计算、OC/特殊跑法、分服车库和草稿正常；代理没有独立操作手机微信，不将此扩写为未回传的其他功能逐项验收。

本地结构化回执：工作区`本地归档/server-switch-fix-deployment-20261024/DEPLOYMENT_RECEIPT.json`。收尾仅改部署/交接文档，不重打包、不修改程序/JSON/Excel/台账或公告，不清理旧应用、备份、演练、测试环境、分支或未跟踪文件。完成授权文档提交推送并核对远端后暂停；无新授权不继续部署、开发、清理或创建监控。

## 2026-10-24 最新暂停交接：OC插值暂缓，下一轮仅继续部署修复

用户决定暂不实施OC插值/外推补缺；等取得更多同图同车、同跑法且配置可比的OC/非OC独立数据对后，再进行数据分析。上一轮提出的万达8条插值候选均未获采纳、未写入，5条外推及滑栏杆也未处理。不将历史公式生成记录反过来当作实测训练或验证样本，不自动扩大OC范围，也不撤回此前已批准的OC估算数据。

分析已核实：当前OC仍21条，杰哥18/万达3，全部普通路线。其中当前直接给定5条、按此前减0.10规则估算16条；追溯勇往直前被替换的24.19可恢复第6个独立直接给定参考点，但当前已接受值仍24.15，不回改。杰哥现有18条非OC均已有OC；万达普通路线8个缺口在参考时长范围内、5个需外推，另1个滑栏杆缺乏同跑法OC参照。所有差值仅为现表配对，包含作者/路线/原成绩质量影响，非受控性能测量。以上仅分析结论，不构成新增成绩采纳。

开发/发布固定状态：main仍d84becdd854dc6156d9517ae4234d9e6795ef058（上轮已推送并核对远端），修复源码绑定4ff5f6f159bf579c3dd058f78d7bc7f6659967ce。完整包release_id=66b9d32c1857d2b3c2cc533f；repo/.production-build/RacePick-SwitchFix599-20261024-66b9d32c-delivery.zip，10949010字节，SHA256=f35d888ef61a5a9591a99e1bccecc433946a166136b36322e9963605ca15171a。暂停前重新核对该包哈希及11份本地数据/工作簿保护哈希均保持；发布包继续仅599条，601条本地数据及国服Excel保存修改仍未提交，公告未发布。85文件manifest、19wheel、86项前端、214项Python（1跳过）、独立暂存与临时库自检为上轮已完成证据，不在本轮重复运行。

本轮只追加此暂停记录到工作区CLAUDE.md、context.md及repo/docs/CLOUD_HANDOFF.md，未提交推送；不重打包、不改代码/成绩/工作簿/台账、不清理环境、不操作服务器。线上仍仅沿用此前0ee524e31734b44fb7771b79/599条用户验收结论，未现场核验。

下一模型可直接使用既有通用交接提示词，从docs/CLOUD_HANDOFF.md最新记录、docs/SERVER_SWITCH_FIX.md及交付说明接续。下一步必须先给用户只读命令核对线上nginx -T及429日志、实际current/进程/health/备份调度；用户执行回传，逐步审核后推进。不能当作半途部署续跑或直接切换。Nginx map/zone与站点limit_req需成套更新、保留原配置备份、nginx -t通过后再按授权reload，应用包不会自动改Nginx；不能夹带601条或覆盖score-state。保留旧版本/备份/演练目录。

按用户要求：完成记录后暂停，不自动继续部署、采集OC、创建监控或提交推送。


## 2026-10-24 最新交接：快速切换修复已推送，599条完整包就绪（尚未部署）

修复源码提交`4ff5f6f159bf579c3dd058f78d7bc7f6659967ce`已推送origin/main，并用git ls-remote核对一致。随后仅追加发布完成交接文档提交，不重建或改变已绑定源码的交付包。原5份本地JSON/工作簿修改和3个未跟踪用户文件未加入提交；601条数据继续留本地，国服Excel保存改动未自动回代，公告未发布。

应用发布ID：`66b9d32c1857d2b3c2cc533f`，85个manifest文件、19个锁定离线wheel，代码/数据provenance均绑定本次源码提交。使用干净独立检出与build_production.py构建；包内国服两份JSON、国际服三份JSON逐字节等于已上线0ee524e3包，国际服数据版本仍f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e，仅五区满星理论599（578非OC+21OC、561普通+38特殊），49车44图42有值，其他区档不混入。没有工作簿、601数据、维护台账、账号/成绩库、凭据或测试材料。

完整上传包：`repo/.production-build/RacePick-SwitchFix599-20261024-66b9d32c-delivery.zip`，10949010字节；SHA256：`f35d888ef61a5a9591a99e1bccecc433946a166136b36322e9963605ca15171a`，同目录有.sha256.txt。展开交付为`repo/.production-build/delivery-20261024-switchfix599`，17文件，SHA256SUMS.txt覆盖其余16文件；外层ZIP逐项回读相等。应用包SHA256为c224289955714d6f54e1b5fdb3ba5d3c7484c3e8b34f3e79157253d510b09984。RELEASE.json和PACKAGE_VERIFICATION.json为独立校验入口。

已完成：干净构建前端86全通过、Python214执行/213通过/1个Linux专用跳过；源码逐字节回比、599条无重复和五区满星隔离、19wheel锁定哈希与Linux CPython3.12离线解析、交付自带部署工具独立暂存未激活、Windows临时数据库HTTP/备份恢复/组件冒烟。Nginx本地旧/新模板78请求对照45次429降为0，登录和管理员等接口仍限流；不是生产Linux原生验收。两份当前/上一完整旧归档SHA和11份本地数据/工作簿哈希保持。

本轮没有访问生产、执行nginx -T、修改/etc/nginx、迁移/初始化正式库、切换current、重启服务或改变备份调度。线上版本仅沿用此前0ee524e31734b44fb7771b79/599条用户验收记录，不视为已实时核验。

后续部署第一步必须用户执行只读核验Nginx生效配置和429日志，同时核对current/进程/health/备份timer。交付附01-readonly-preflight.sh（bash -n通过）；标准日志无结果不等于没有429，按nginx -T中的实际日志路径继续核实。回传审核后才逐步推进上传校验、暂存/独立运行时、成套备份演练及版本/配置切换，禁止一口气执行历史部署脚本。修复须成套更新Nginx map/新zone和站点limit_req，移除旧全站限流，先nginx -t再审核reload；应用切换不会自动改Nginx。证书/其他站点保持，旧版本、备份、演练目录保留，不重复迁移，不用代码包覆盖服务器score-state。

本地完整回执：本地归档/server-switch-fix-20261024/release-receipt.json及application-verification.json。本轮到“可校验包就绪、等待用户开始只读核验”为止，不自动执行部署。


## 2026-10-24 快速切换修复提交与599条完整包准备（禁止夹带601条）

用户授权提交推送本次修复，准备完整可校验发布包，不操作服务器。暂存仅api.js、index.html、两份Nginx模板、新增重试测试、构包附带修复说明的改动及相关文档；现有5份JSON/Excel修改、未跟踪来源表和脚本全部排除。提交前核对HEAD中的国服两份JSON、国际服三份JSON与已上线0ee524e3完整应用包逐字节相等，运行599条；本地601条继续保持未提交，国服工作簿保存改动不自动回代。

构建复用build_production.py及已验证锁定19wheel，使用本轮提交的独立干净检出，完整包需逐文件manifest、数据范围/版本、与旧版数据字节、离线依赖、暂存及临时库自检、外层SHA和ZIP回读核验。具体提交、发布ID和外包SHA以本轮交付RELEASE.json、PACKAGE_VERIFICATION.json及后续完成交接记录为准，本段不提前宣称构包完成或线上已修复。

下一轮部署先用户执行只读核验nginx -T、429日志、current/进程/health/备份调度，现场确认后才按步骤推进上传、校验、暂存、独立运行时、备份演练、Nginx配置备份和成套调整、nginx -t、切换与公网高频切换验收。应用包不会自动改/etc/nginx，不能只切代码；不重复生产schema迁移、不覆盖score-state、不导入本地数据库或601数据。旧版本、备份和演练目录均保留。


## 2026-10-24 快速切换服别报错：本地修复待发布

本轮用户要求修复快速反复切换国服/国际服时api未定义、国际服数据及成绩版本加载失败。切换仍为整页导航；仓库旧Nginx对全部请求使用同一个5r/s、burst30桶。独立本地真实Nginx 1.26.3及假接口对照复现：相同78次启动资源GET旧版33次200/45次429，新版78次200；新版登录POST、公开路径POST、管理员GET仍能触发429，业务桶耗尽后脚本和快照继续200。仅本地证据，未读取本轮生产配置或日志，线上原因需部署前只读核验。

已调整production/nginx-rate.conf和nginx-https-location.conf，GET/HEAD公开资源与明确列出的启动只读接口使用空限流key，其余请求保持原额度；使用新zone racepick_api_requests。api.js对启动成绩GET的429/503最多3次请求，保留快照一致性及完整性校验，不重试写入；国服失败缓存清除后允许重新读取。页面缺脚本给明确提示，不再将普通网络错误统一提示为本地HTTP打开问题。

前端86项全通过；发布包/部署工具15项通过（其中1项按环境跳过）；两套本地Nginx配置语法和限流对照通过，测试进程已停止。11份现有数据/工作簿保护哈希保持，国服和601条本地数据均未改；现有未提交的数据及未跟踪来源表继续保留。无提交推送、构包、生产操作、公告发布或业务数据写入。

说明：repo/docs/SERVER_SWITCH_FIX.md；本地复现及结果：本地归档/server-switch-fix-20261024/check_nginx.py、nginx-result.json。后续部署必须先读nginx -T与日志，备份配置后成套更新两份Nginx配置，nginx -t核验再reload；仅切换应用包无效。保持用户逐步执行回传流程；不可顺带上线尚未批准的601条更新。线上仍只沿用此前0ee524e31734b44fb7771b79/599条用户验收记录，未重新现场核验。

## 2026-10-24 按分级完成工作树与sandbox清理（分支全部保留）

用户本轮明确授权移除allocator-perf，并将3个已合入但含历史构包的工作树和9个冒烟sandbox完整归档校验后清理，其他先保留。已执行：allocator-perf、account-feedback-production、contribution-production、score-versions-local共4个检出均使用git worktree remove正常移除，无--force；所有分支名称/提交指针与操作前逐项一致，主仓库HEAD仍fe0702252b7ddc8c325a37367339391f8c8b678b，未合并或删除分支。

3个工作树（含全部忽略文件、构包/缓存/.git指针元数据）、9个sandbox（含数据库、版本、测试邮件及空目录）共808文件分别封存为12个带日期统一命名ZIP，位于E:/hzz/work/MutualExclusionAllocator/本地归档/retire-worktrees-sandboxes-20261024。每份有ARCHIVE_MANIFEST.json并逐文件SHA256回读通过；sandbox数据库只读完整性通过、无待处理WAL/journal，非阻塞维护锁探测通过；删除前再次检查绝对路径在工作区、无重解析点且完整文件集/哈希不变。再使用PowerShell Remove-Item -LiteralPath清理9个原目录。没有停用其他进程、绕过锁或删分支。

保留主repo及5个开发工作树：account-feedback、accounts-local、community-controls、contribution-leaderboard、garage-toolbar-responsive；保留3个有验收/回滚资料的sandbox：87ead67eb276a87abd6b70ca、a97eb79fdbf9a00e9b1169f1、b3966af9ba0b2695eaae226e。保留目录全部原文件哈希/mtime不变；community-controls独有文档提交继续保留，不自动合入。被归档的9个ID完整值、3个分支及恢复方法见retirement-plan.json和恢复说明.txt。

根目录目录导航.html、directory-review-20261024/directory-index.json和逐项统一命名索引已同步归档状态，仍列原21项以便追溯；不再把已清理的原路径显示为仍可用。恢复sandbox必须用完整24位ID及原父级；恢复工作树先git worktree add，再按需恢复payload，不能覆盖Git新登记的.git指针。归档含本地测试快照，仅留本地，不提交或上传。

清理后601本地运行、616完整维护JSON/Excel一致性与生成器--check通过；国服、工作簿、台账、OC/36参考、正式公告草稿、其余测试环境及当前/上一发布包均保持。当前工作树既有未提交修改和未跟踪文件保持，原434来源和维护SHA校验通过。回执本地归档/retire-worktrees-sandboxes-20261024/retirement-result.json，恢复说明同目录。未提交推送、未发布公告、未上线、未访问或清理服务器；线上仅沿用此前599条已验收结论，未重新做现场核验。


## 2026-10-24 历史工作树及sandbox目录标注完成（本轮未删改目录）

用户要求进一步检查根目录.score-version-sandboxes及allocator-perf、contribution-production等，并先统一时间标注/命名、评估清理。已检查9个Git工作树和12个成绩版本隔离环境，统一索引名称为“日期__用途__状态__原名/ID短码”，每目录单独说明保存在本地归档/directory-review-20261024/统一命名索引。根目录可直接打开E:/hzz/work/MutualExclusionAllocator/目录导航.html；完整机器可读元数据同目录directory-index.json。日期依据明确区分工作树最后提交时间、环境初始版本manifest时间和本机文件系统时间，不冒充原始创建/业务使用时间。

12个sandbox中9个为单图单版本且无验收文件的疑似自动化冒烟环境，可先归档后考虑清理；3个含验收/回滚/登录说明或多版本，先保留。backend/score_repository.py的validate_lab要求父级固定、lab.json.id等于目录名，不能直接加日期重命名或换父级。目录索引统一命名不代表已经改物理名称。

9个工作树全部无已跟踪或未忽略的修改，但忽略目录不为空。allocator-perf已在main且仅有pycache，可作为优先清理候选；account-feedback-production、contribution-production、score-versions-local已合入但有历史构包，需先归档；account-feedback、accounts-local、contribution-leaderboard、garage-toolbar-responsive有测试资料/库/邮件/写回环境，先归档保留。community-controls仍有主线没有的文档提交6ef9062（5份文档），不视作完全合入，保留该分支历史；本轮不合并。所有分支仍保留。

本轮只建立21项带日期标签、目录导航和清理分级；没有删除/重命名/移动任何工作树或sandbox，没有新建目录联接，也未停用进程。进程快照未观察到Python服务，与本工作区相关Node进程是Codex CUA运行时，不能据此保证所有文件无占用。数据库只读汇总，不输出邮箱/密码/令牌或LOGIN内容，原始目录文件哈希/mtime核对保持。当前601本地/616维护数据、工作簿、草稿、601待发布状态和599线上最后验收状态均保持，不提交推送、不上线。


## 2026-10-24 本轮授权本地清理完成（未提交推送，未操作服务器）

用户本轮明确要求清理杂乱本地备份和历史构包，覆盖此前暂停/保留策略中“不得自行清理”的默认边界；本次只处理已列清单的本地产物。先核验所有目标绝对路径都在工作区内、无重解析点/目录联接，再逐文件SHA比对。旧回代备份、构表材料、20261021交付及源码快照共572文件封存到3个ZIP，逐条回读及内置ARCHIVE_MANIFEST.json校验通过；之后删除原散文件。其余直接清理项均证明为保留发布包中的相同字节副本，或干净、提交仍在主线的专用构建检出。

本次清理2148个文件、27个目录目标及196个单文件目标，原内容约165.59MiB；归档约18.67MiB，净减少约146MiB（另留少量审计脚本/清单）。清理包括三份临时发布暂存、两份wheel副本、上一版冗余展开交付、最新备份中的两份发布ZIP重复拷贝和两份专用构建检出。release-build-20261024用git worktree remove正常解除；release-build-global599-20261024为无修改/无未跟踪或忽略文件的独立构建克隆，全部引用对象已在主仓库中，方才清理。没有删除开发分支或更改其他开发工作树。

保留当前0ee524e3完整上线包、其展开交付及上一bd12e3fb回退完整包与校验文件；保留最新workbook-return2-sort和前一accepted-tier-review备份，当前校验清单引用的旧style两份记录原路径也保留。现有601本地运行数据、616完整维护键、所有工作簿、来源/台账、OC/36参考、正式公告草稿、素材和本地账号/测试库均保持哈希及mtime。外部运行时node_modules联接未删除或遍历。国服未改，线上仍按上次验收599记录，服务器旧版本/备份/演练目录完全未操作。

清理/恢复总索引：E:/hzz/work/MutualExclusionAllocator/本地归档/cleanup-20261024/清理与恢复说明.txt；同目录有3个归档、ARCHIVE_SHA256SUMS.txt、cleanup-plan.json、cleanup-actions.jsonl、cleanup-result.json。旧历史路径被清理后，请先查这里的归档映射；每个ZIP保留原相对路径/SHA/mtime，需要时先解压到新临时目录核验，再按需取回，不能将整个历史备份覆盖当前工作区。被移除的专用构建检出可由保留Git提交重新创建。

清理后601运行生成器--check、616键Excel与完整JSON一致性、原434项来源与当前维护SHA清单、两个完整发布ZIP及保护文件哈希全部通过。Git HEAD仍fe0702252b7ddc8c325a37367339391f8c8b678b；既存未提交数据/提示词/文档改动及3个未跟踪用户文件保留，不reset、不clean、不提交推送、不发布公告、不上线。此次不重跑应用回归，因为代码/数据字节没有变化。


## 2026-10-24 最新交接：正式公告草稿已保存，保留本地601条后暂停

正式公告草稿（用户已确认文案）：`E:/hzz/work/MutualExclusionAllocator/数据源/international-prep-20261023/maintenance/local-hold-announcement-20261024/国际服五区理论更新_正式公告草稿.txt`。包含标题“国际服五区理论数据更新与界面优化”、功能版本标签“国际服五区理论更新”及纯文本正文；后续公告使用此正式草稿，旧“更新公告草稿.txt”仅作历史备选保留。预告仅说明后续数据更新和计划探索OCR，不披露两条未上线圈速，也不声称OCR已开放。

本地五区理论601条、完整维护616键及已验收的Excel排序保留，尚未提交、未推送、未打包或上线；Git HEAD仍为fe0702252b7ddc8c325a37367339391f8c8b678b。线上仍保留此前用户验收的0ee524e31734b44fb7771b79/599条版本，本轮未重新访问服务器。公告仅本地草稿，尚未发布、未调用公告平台接口。四区与高手维护数据仍不进入当前五区理论计算。

本次只补交接说明，不改草稿、代码、成绩、台账、工作簿、发布包或服务器，不提交推送。用户要求完成后暂停；后续无新指令不得继续开发、上线、公告发布或清理旧版本/备份/演练目录。



## 2026-10-24 用户确认排序并保留本地更新；公告仅草稿

用户明确确认“排序没问题”，要求保留本地更新、更新交接记录，暂不提交推送、不上线，并起草更新公告。当前本地五区理论601条、完整维护616键及13页现有Excel保持，原本轮两条evo肥龙普通路线岩石山谷20.66/幽灵船22.02不再变更；排序规则/OC邻接已获用户验收。上轮35项验证为本轮沿用已通过基线，没有为文档动作重复跑测试或再导出工作簿。

最后已知线上仍是已验收的0ee524e31734b44fb7771b79/599条、数据版本f4f36ae…；本地运行601条版本7fffdbbb…未提交推送、未打包、未上线。Git HEAD继续fe0702252b7ddc8c325a37367339391f8c8b678b，后续不得将当前本地状态误作已发布内容。国服、账号、反馈、备份、演练、发布包及未跟踪文件继续保留。

公告按“已上线599条国际服更新与界面调整＋两条本地成绩待发布预告”起草，正文不混入内部维护实现细节，也不把四区/高手或601条写成已上线。草稿在maintenance/local-hold-announcement-20261024/更新公告草稿.txt，未调用公告发布接口、未写服务器或外部平台。用户若后续要求发布，须按当轮明确授权办理，不由本轮起草推导发布授权。

## 2026-10-24 最新本地：用户表新增2条已回代，车辆列按数据量降序（未提交/未推送）

用户保存国际服现有Excel后授权回代，并要求列顺序与国服一样左往右数据量递减。独立差异只有五区理论普通路线evo肥龙：苏格兰/岩石山谷20.66、苏格兰/幽灵船22.02，原键均为空；无改慢、删除、星级/OC/区档或结构变化。按最终表内值原样回代，不减0.1、不自动改SC；普通与已有特殊跑法分别保留。此为用户直接维护值，不冒充已补看2026-05后视频日期。

完整维护JSON/台账/同一Excel现616完整键，含614条有秒数和2普通可用镜像；运行投影601＝580非OC+21OC、563普通路线+38特殊，49车44图42覆盖。四区仍11理论、高手两区各1（爱音E三星33.85）和普通镜像各1，继续只维护，不入运行。原614维护键及线上599运行值全部保持，正好新增两键。运行数据新版本7fffdbbb888fb2e0c7d54accf04f12b32719f735adbaf2c057617d34a6f67a71，仅本地；线上仍是已验收0ee524e31734b44fb7771b79/599条，未发布这两项。

排序复用export_xlsx.py的compute_car_stats/order_combos：主表按本区理论+高手普通路线覆盖赛道数降序，同量按平均相对速度/车名排序；同车星级聚合、普通和OC紧邻。特殊跑法表按本表自身覆盖量降序，次级相对速度；数据空列留最右，不删车型。7张含车辆列的标准表完成重排，其他标准表无车列保持，独立高手参考页不参与横向排序。逐格按列标签回比，排序本身0值变化；地图行序/合并/冻结C2与SC D2、原字体（含中文charset元数据）/样式、逐车列宽、行高及参考页内容保持。

先保存用户原件及所有维护输入于maintenance/change-history/workbook-return2-sort-20261024；对Git已提交614键基准和本轮Artifact Tool独立导出基准分别回比，复用diff_workbooks.py/apply_changes.py/validate_data.py/format_json.py完成预览与回代。更新后Excel=完整JSON=完整台账616、运行JSON=投影=运行台账601，0重复；字段键含区档/星级/OC/SC类型。35项针对性回归（Node14/Python21）、生成器--check、排序单调性/OC邻接/样式映射检查、图像预览和0公式错误扫描通过；未原生Excel打开。

回执/差异/列序见maintenance/workbook-return2-sort-20261024/final-verification.json、approved-workbook-diff.json、column-order-verification.json。国服原表/目录/JSON、源成绩表、原36参考、OC台账、身份目录、旧新发布ZIP及原434来源哈希保持。仅本地数据和排序维护，未改应用功能代码、未提交、未推送、未打包或操作服务器。


## 2026-10-24 最新：599条国际服更新已上线，桌面与手机微信验收通过

本轮部署及验收已经完成，没有半途部署需要续跑。服务器操作均由用户执行命令并回传，代理未登录服务器；以下是本轮回传与用户确认所证明的状态，不是之后自动持续监控的结果。用户要求本次交接提交推送后暂停，不继续开发、部署、清理或创建监控。

### 实际运行与发布范围

2026-10-24 13:13:28 CST启用应用`0ee524e31734b44fb7771b79`，源码和包内数据均绑定`a0298cd25da9cbf46a9909d7e5b3723e82adea8f`。`current`与`/proc/148673/cwd`均指向`/opt/racepick/releases/0ee524e31734b44fb7771b79`，服务active/running。PID148673仅为当时快照，以后须重新核对。上一应用`bd12e3fb2c2519b0238afd90`保留。

公网global manifest回传数据版本`f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e`，仅五区满星理论599＝578非OC＋21OC，561普通路线/38特殊，49车、44图42有值；四区/高手没有进入运行数据。614键完整维护数据、四区11理论、两区三星高手与普通镜像、36条独立参考及工作簿仍只在维护侧。国服完整health保持ok/production/schema6/community1/contribution1/feedback1，contributions/feedback/score_writes均true，成绩版本`42d62fde9b81197ac0558087a9a25f97`未变。未执行正式库初始化、schema迁移或本地成绩/账号/测试数据导入，也未用代码包覆盖score-state。

上传完整归档SHA256`85ee2e8e26045b51f4b67dbbb439dfda21ce95d0673b1ddc4da57f84cde9c448`及10929698字节核对；交付目录13项SHA、应用包85文件、599/21OC/38SC范围均通过。用户确认19个离线依赖安装、pip check和Linux/Python3.12临时库原生自检通过，新版独立.venv成功；本轮安装完整日志未回传，不扩写成Linux全量测试套件均已重跑。旧包及新包均未重建或修改；包构建记录中的“PENDING server”是构建当时状态，本节是后续实际验收结果。

### 成套备份与独立恢复演练

| 阶段 | 备份（/var/lib/racepick/backups/） | 独立演练（/var/lib/racepick/restore-drills/） | 证据 |
| --- | --- | --- | --- |
| 旧版在线 | scores-20261024T050437147757Z.zip | e354e96ad92c1b79e112b266 | 完整回传通过 |
| 停服最终 | 未回传具体路径 | 未回传具体目录 | 用户明确确认备份/演练通过、正式库未替换；不得猜测路径或SHA |
| 新版在线 | scores-20261024T051434290756Z.zip | 7fc34c4d8b50be02f8e3713a | 完整回传通过 |

两份已完整回传备份均159785字节、racepick:racepick、mode600；旧版ZIP SHA256`d8d097aca054ab05d9123aa2bf4eda09252b1d862a965f151621c4e04bdf0b38`，新版ZIP SHA256`7342fe3b17eb98dfc1683c3ac5e808b4af6db1d60ac37989bd2f617c41950cd0`。两份解包内容哈希一致：accounts.sqlite3=`7f1cd5db2c7d0d404f00cd1aed3dab6aa68e2e753acbbef26e862130cfe8d81d`，国服当前成绩JSON=`bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9`。恢复结果39用户、21车库、3投稿，pending_batches0、active_database_replaced=false；贡献schema1，contributions0/sources1/events0/preferences1；反馈schema1，tickets/events/requests均0。上述计数仅对应两份完整回传，不为缺失最终备份日志补造计数。

### 调度与公网验收

2026-10-24 13:17:20 CST回传，racepick-backup.timer已恢复enabled、active(waiting)，LAST2026-10-24 04:16:12 CST，NEXT2026-10-25 04:18:31 CST。这证明调度恢复；不是宣称10月25日任务已执行。上次04:16:13定时备份成功见本轮最初journal回传。恢复调度后health仍ok，成绩版本及开关保持。

用户明确确认桌面浏览器与手机微信公网验收通过。此前所列国服正常、国际五区理论选车计算/OC/SC、分服车库、三行布局、c2兔子搜索与国际服隐藏R筛选的验收，以用户本轮整体通过确认为依据；代理未独立操作微信或取得逐项截图。没有遗留的待执行部署步骤。本轮保留旧版本、全部备份/演练、工作簿和测试数据；没有系统升级、Nginx重配或目录清理。

### 本次收尾边界

仅更新部署/交接文档并按授权提交推送；不改代码、成绩JSON、运行manifest、维护台账或现有Excel，不重新打包、不重启服务、不重复演练或迁移。精确记录在工作区maintenance/deployment-global599-20261024/DEPLOYMENT_RECEIPT.json。唯一记录缺项为停服最终备份路径、SHA及演练目录未回传；其成功由用户确认，不影响已经完成的部署验收结论。以后的新任务先读最新文档并核对现场，不能照历史PID和目录状态续跑。提交推送完成后暂停。


## 2026-10-24 最新：599条更新已提交推送，完整发布包就绪，尚未部署

本轮代码/数据提交a0298cd25da9cbf46a9909d7e5b3723e82adea8f已推送main，git ls-remote核对一致；随后本段交接记录单独提交，不改变发布包源码绑定。构建使用新的干净独立检出release-build-global599-20261024，旧release-build-20261024和旧交付包均保留。原未跟踪源表、shared工作簿和_star_curve_fit.py未加入提交或打包。

- 新发布ID：0ee524e31734b44fb7771b79；目标Ubuntu24.04/x86_64/Python3.12。
- 本地交付目录：repo/.production-build/delivery-20261024-global599，14文件，SHA256SUMS.txt覆盖其余13文件。
- 完整上传归档：repo/.production-build/RacePick-International599-20261024-0ee524e3-delivery.zip，10929698字节；SHA256：85ee2e8e26045b51f4b67dbbb439dfda21ce95d0673b1ddc4da57f84cde9c448，旁有.sha256.txt。
- 内层应用ZIP：racepick-accounts-release.zip，10858488字节；SHA256：b39d06f2cec0de56f09be985222921139ed35c8da25174be3ec15ae29220f29d；85个manifest文件，含19个锁定离线依赖。
- source/data provenance均绑定a0298cd25da9cbf46a9909d7e5b3723e82adea8f；三份国际JSON及国服两份JSON逐字节等于已提交内容，其余文本仅有Windows检出行尾差异，已逐项规范化回比。相较上一发布包仅PRODUCTION_DEPLOYMENT.md、三份global JSON、index.html、styles.css、tools/build_global_data.py改变；账号/成绩/贡献/反馈运行代码和两份国服JSON均与旧包一致。

发布范围仅五区满星理论599（578非OC+21OC，561普通路线+38特殊），49车、44图42有值，数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。包内其他区档为空，无显式低星成绩；四区11理论、两区三星高手、2个普通镜像、36参考记录、614键完整维护JSON/台账与所有Excel均未打包。包内国服JSON与上一发布包字节一致，不额外发布国服成绩；更不能覆盖服务器score-state。没有数据库/账号/凭据/反馈/候选/测试数据或未跟踪文件。

本轮验证：JavaScript81通过；Python214执行、213通过、1个Linux专用检查在Windows跳过。完整维护614键/运行599键隔离核对、原434来源与旧发布包哈希、85文件/19wheel锁定哈希、外层13SHA与14文件归档回读均通过。用交付目录内独立deploy_production.py在本地新目录暂存成功，未激活；解包程序production/selfcheck.py以Windows临时数据库通过HTTP、备份/恢复和组件自检，不发邮件、不用现有用户库；19wheel按Linux CPython3.12标签离线解析成功并逐哈希相等。PACKAGE_VERIFICATION.json/RELEASE.json保存可独立核验结果。Linux原生安装/正式库现场兼容性仍待用户上传后执行，不冒充已在Linux或生产运行。

本轮没有登录/读取/修改生产服务器，也没有运行迁移、初始化、切换或清理。最后已知生产仍为用户此前验收的bd12e3fb2c2519b0238afd90；其PID、健康、成绩版本、备份调度和公网情况须部署时先只读重核。下一轮用户开始部署后，再逐步给命令、等待回传核对，不能直接续跑旧部署步骤。国服原表/目录、源工作簿、614维护数据、OC、36参考、旧包/备份/演练/测试数据保持。原完整工作树只保留3个既存未跟踪文件；不clean/reset或自动同步工作簿。


## 2026-10-24 本轮599条国际服更新：提交与完整发布包准备

用户已授权提交推送本轮更新并准备完整可校验发布包，明确暂不操作服务器。发布仍严格限定国际服五区满星理论：599条＝578非OC＋21OC，561普通路线/38特殊，49辆可计算车，44图42有值，富士最后两图空。数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。维护侧完整JSON/台账/现有Excel的614键及36条高手参考均保留；四区11理论、两区三星高手和普通可用镜像只用于维护，不装入运行包。Git跟踪的Excel可以提交，但发布白名单排除所有工作簿、完整维护JSON/台账、候选、真实账号/成绩库、凭据和测试数据。

与最后验收的bd12e3fb2c2519b0238afd90相比，待发布内容还包含此前已提交未上线的三行分组布局与c2“兔子”别名，本轮国际服隐藏R级占位、已授权OC估算来源绑定及国际数据维护成果。国服已跟踪数据/原表未改；包内国服基线来自已提交版本，不能覆盖线上独立score-state，不导入本地成绩或重跑迁移。

fetch后main与origin/main同为4d261611f666685bb865dd81cc83e5ad9ea9697a，无新远端变更，无需合并。发布前JavaScript81项通过，Python214项运行/213通过/1项Linux专用跳过；完整维护614键、运行投影599键、manifest哈希与纯生成器校验均通过。复用build_production.py和19个哈希锁定的Ubuntu24.04/x86_64/Python3.12离线wheel，从本轮提交的干净检出构建。具体源码提交、发布ID、包哈希和独立验证结果以本轮RELEASE.json与PACKAGE_VERIFICATION.json为准；旧包不覆盖。

最后已知生产部署为用户此前验收的bd12e3fb2c2519b0238afd90（321条国际数据），成绩版本42d62fde9b81197ac0558087a9a25f97。本轮未登录服务器或重新核验线上，不把历史PID/备份调度时间当现场状态。以后部署仍先给只读核验命令，由用户执行回传逐步核对，再暂存/安装运行环境/成套备份演练/切换/恢复调度/公网验收；不初始化、重复迁移、覆盖服务器成绩或清理旧版本、备份和演练目录。


## 2026-10-24 最新整体核对通过：614维护键／599运行键

按用户要求整体复核，完整维护JSON gauntlet_data_international_maintenance.json＝现有Excel标准12表＝maintenance-score-ledger.json，614完整键，612条有秒数+2个普通可用镜像，无重复/缺漏/多出。五区理论599、高手1、普通镜像1、自动0；四区理论11、高手1、普通镜像1、自动0。原13页独立高手参考36行与参考JSON逐格一致，不计614活动键。

gauntlet_data_international.json＝score-ledger.json＝运行gauntlet_data.global.json＝完整维护五区理论子集，599键，578非OC+21OC、561普通路线+38特殊，49辆可计算车（维护身份55），44图42覆盖。全部四区/高手/普通镜像不在运行数据；运行目录仅五区满星规则。直接将完整维护JSON作为构建输入会以“International phase one supports only five-zone theory”拒绝，前端config仍仅加载独立运行三文件，不读取维护表。21OC来源与运行值、两区三星高手/普通镜像、Fordo11四区副本星级/满改分均独立核验。

本批已入库数据当前等待用户决定0项，玻璃破冰者31.85已通过二审。共享表原214唯一标记来源未导入：208待核/参考+6原版已作废，208中分类跑法121、星级27、四区参考52、版本61、离群2，相互重叠不能相加。早期7暂缓另按原授权保留，未与214合并去重，不编造总数。已接受的20EVO配置缺失、4EVO性能参数待补、12玻璃参数差异、Fordo视频星级未逐车复看均继续保留证据限制，不重新当作待用户审批。富士极速列车/乡间冲刺仍空。

发现维护指针现状文案残留Bolide ice pending、439及旧600条描述，已仅更正元数据文字，刷新manifest的current-maintenance来源哈希；运行两份JSON、成绩/台账/Excel及国服/代码字节mtime保持，dataset_version仍f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。26项回归（Node14/Python12）、生成器--check、原434来源及旧发布包校验通过。完整回执、各档位与未导入清单在maintenance/overall-reconciliation-20261024，报告国际服整体核对与待核清单.html；改前指针/manifest备份change-history同名目录。仅本地核对和审核状态维护，未提交推送、打包、上线或操作服务器。


## 2026-10-24 最新本地：爱音E三星高手／Fordo四区理论／EVO保留

用户本轮授权：爱音E移五区和四区高手并标三星；玻璃除破冰者二审外接受；EVO仅严重落后同图平均才删；Fordo星级核验后可保留五区并加四区理论。

爱音E偏离中心从五区理论撤下33.85，原值保留写入五区/四区高手，cars.stars=3，未再加减。源表6星标注、原始33.8与配置4102/480/84.18/39.97/18.33完整保留；三星是用户明确纠正，不伪造为原表实证。沿用数据模型给高手各加1个普通可用镜像（无新秒数）。四区车池身份按授权增加爱音E，zone4Max3，不套国服上限。

Fordo11条涉及ap0、阿波罗n、avj、迈凯伦p1、叶问、小牛（5星）及自私（6星），源配置星级与各自目录满改参数一致，性能分3946/4047/4133/3602/3929/4109/4213均≤国际4400。保留五区理论并复制原已接受值至四区理论，普通路线；星级核验是表内星级+满改参数交叉，不声称逐车视频星级画面认证。11项来源、星级/性能分与视频归属见accepted-tier-review-20261024/fordo-star-proof11.json。

20条EVO对照同图其他非OC、非SC普通理论，参照中排除被评估的全部20条，避免自证。每图有9–23左右参照；严重落后判断为同时≥2秒且≥10%，实际最慢仅evo女武神巴黎圣母院20.95对均值20.74706，+0.20294秒/+0.97817%，全部保留，0删除。玻璃其他11条标记用户已接受参数冲突；破冰者31.85未动，单列二审，原31.8、旧32.13、未知作者/无链接、5190分但加速/氮气冲突等见玻璃破冰者二次审核.html。国服同车同图31.20只是参数不同的参照，没有迁移。

重要维护边界：完整维护入口新增maintenance/gauntlet_data_international_maintenance.json与maintenance-score-ledger.json，614完整键＝五区理论599+四区理论11+两区高手各1+各自普通可用镜像1，其中有秒数612。现有gauntlet_data.global.xlsx标准12表与这份完整维护JSON/台账614键一致，原独立36条高手参考页仍不计入活动键，字节数据保持。以后核对维护Excel要用current-maintenance.json的authoritative_maintenance_json/workbook_validation_json，不应再直接与运行投影相比。

gauntlet_data_international.json/score-ledger.json继续作为已验证生成器的运行投影输入，严格只599条五区满星理论，不含新增高手/四区/普通镜像；生成器及应用功能代码未扩展。两份JSON均保留区档完整结构。运行49车、44图42覆盖，578非OC/21OC、561普通/38特殊；原其余599条运行值不变，只有爱音E退出理论。维护身份目录55保留，仅按授权7款Fordo车及爱音E加四区身份。

本轮106项回归（Node34/Python72）、完整维护JSON校验、614键Excel和全台账独立核对、生成器--check均通过。数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。原13页所有未授权格值/样式/列宽/合并/冻结保持，变动普通/高手/四区理论渲染检查、公式扫描通过，未原生Excel打开；国服JSON/表/目录、源表、旧36参考、OC台账及既有审核资料字节mtime保持，原434项来源和旧发布ZIP校验通过。备份maintenance/change-history/accepted-tier-review-20261024，完整回执在maintenance/accepted-tier-review-20261024。未提交推送、打包或操作服务器，旧版本/备份/演练/测试数据继续保留。


## 2026-10-24 最新：evo狼崽隧道冲刺修正21.89（仍600条）

用户标注五区_理论!U23，明确最终值21.89。对应内华达/隧道冲刺普通理论，原23.00→21.89，不再减0.1。维护JSON、同一Excel、活动台账及运行数据已同步；另外599条与工作簿所有其他单元格/样式/布局保持，36条独立高手参考、OC台账和国服保护输入字节/mtime不变。

旧23.00来源为BV1uNpU6CEVg约04:10的23.099秒，原跑者Fordo，B站转载者煙KiVi，投稿记录2026-10-14。作者信息来自既有归档记录与原审核材料；本轮B站页面不可访问，未声称重新看过视频。新21.89是用户指定最终值，台账新source_kind=user_direct_final_theory，旧作者/视频/秒数完整收在previous_record，不将21.89冒充原片实测，也不恢复待核21秒条目。

JSON/Excel/台账保持600键，49可计算车辆、44图42覆盖、579非OC/21OC、562普通/38特殊。数据版本2e4305806e2f8a210ee458db1b70283847c5c512903f0daf04d62c826c8eea73，生成器--check、14项Node+21项Python共35项针对性回归通过；13表逐格/样式核对与渲染、公式扫描通过，未原生Excel打开；434项原来源校验通过。改前备份maintenance/change-history/wolf-tunnel-correction-20261024，来源追溯及回执maintenance/wolf-tunnel-correction-20261024。未改应用功能代码、国服或生产，未提交推送/上线；旧版、备份、演练与测试数据继续保留。


## 2026-10-24 最新：撤下两位作者36条理论，原配置转高手参考（本地600条）

按用户明确授权，将疯狼4条、皮卡丘32条（25普通车型+11EVO）撤出理论。35个新增补缺键移除；evo狼崽×内华达/隧道冲刺22.75恢复为导入前23.00，原台账来源完整恢复。其余599个保留活动键值不变，OC及SC不动。当前国际活动JSON/同一Excel标准12表/台账600完整键一致，无重复：579非OC+21OC、562普通路线+38特殊；44图42覆盖，富士两图仍空。

36条原始秒数（未经+0.05或截位）、星级、性能分及四维、作者/源行/完整原配置及撤下台账另存maintenance/expert-reference-scores.json，runtime_enabled=false；同一gauntlet_data.global.xlsx末尾新增“高手参考_原始配置”页，保留原始值与曾录理论值两列，标明分区/跑法待核。该参考页不进入标准高手/普通镜像或理论计算，国际服仍只开放五区满星理论；没有把低改装实测伪装成满改高手。此前全部原件备份在maintenance/change-history/withdraw-author36-20261024。

维护身份目录55辆与原Excel车名列保留；既有生成器按剩余活动成绩自动投影49辆可计算车型，不修改生成逻辑。原12张表只改授权36格，其余值/格式/列宽/合并/冻结保持，高手参考页同用宋体10与原表配色。600键独立回读一致，36参考行逐格核对，渲染及公式扫描通过；未原生Excel打开。

本轮Python72+Node34共106项回归通过，生成器--check通过，数据版本eb5908d8b9e2c2645902c2abe53cd2ddc2cacf12123cdd8784a9da960f76289a。原434项来源与旧发布包校验通过，国服原表/JSON/目录、源工作簿、候选审核资料、OC台账、维护身份目录字节及mtime保持。完整撤下/恢复/保护与检查结果见maintenance/withdraw-author36-20261024/final-verification.json及changes.json。仅本地数据、参考页和相关测试数量基线更新，未修改应用功能代码、提交推送、打包或服务器；线上仍是先前验收的bd12e3fb2c2519b0238afd90/321条国际数据，非本轮实时生产复核。保留旧版本、备份、演练和测试数据。


## 2026-10-24 最新本地：258条获批候选回代完成（635条，55车）

用户明确接受258条主候选，并确认整数和一位小数加0.05、两位原值、三位直接截去末位不舍入，之后保留同完整键更快值。本轮196新增、49更快替换、13保留原表更快/相等值；没有把258条都算作新增。20辆新车补入独立国际目录，用户昵称ars、ap0、阿波罗n、avj、evo百年牛、evo讴歌、fxxk、gtr、乐高c8、迈凯伦p1、叶问已采用，其余沿用已识别昵称。EVO参数仍留null，不借原车参数伪装。

普通杰哥勇往直前24.33→24.25；按此前授权派生规则，OC杰哥24.19→24.15、奇美拉24.09→24.05，两条单列为估算而非实测。飞向未来的候选25.95慢于原25.93，保留原值。OC台账现为5条直接值+16条授权估算，共21条；其余20条OC键值保持。

国际活动JSON、现有Excel及台账635完整键一致，无重复；597普通路线/38特殊，614非OC/21OC，55辆物理车、44图42覆盖，富士最后两图仍空。只在现有五区理论主表末尾追加20列并更新获批格值，OC相邻列和SC分表保留，12表原有值（授权修改除外）、字体、配色、列宽、合并及冻结C2/SC D2核对通过；渲染检查和公式错误扫描通过，未在原生Excel打开。

获批记录原始值、精度处理、作者、来源行/链接、原值与最终值见maintenance/accepted-review258-20261024/decisions.json和accepted-decisions.csv；两个派生值见derived-changes.json。原件备份在maintenance/change-history/accepted-review258-20261024。待核来源/审核表/清单保持字节及mtime不变，未采纳待核值；同键另有获批来源时仅按获批来源更新，不表示该键上的待核来源获批。国服JSON/目录/原两表、用户源表、保留脚本、历史发布包均保持。

当前仅本地数据与目录及对应测试基线更新；本轮没有修改应用功能代码、提交推送、发布打包或服务器操作。线上沿用此前验收的bd12e3fb2c2519b0238afd90及321条国际服数据，这不是本轮实时服务器复核。旧版本、备份、演练目录和测试数据保留。


## 2026-10-24 最新：候选待审核、global显示修复（活动439不变）

新表潜在行分组后472个唯一编号，258主候选；跑法/星级/四区/离群/版本及已作废原版另页，候选0回代。独立审核本在maintenance/source-quality-review-20261024/candidate-review-20261024。global表非数据截断，是P21误冻结，已仅改主表视图为C2，SC表D2保持；439记录/35车、所有值/样式不变，两运行数据JSON和台账字节mtime不变。数据版本仍30a5da9…，只刷新文件/来源校验。未提交推送或上线，生产仍bd12e3fb2c2519b0238afd90/321。

## 2026-10-24 最新本地439及共享表只读评估（未提交/未上线）

仅写入用户直接6条（r兔4、绿兔1、超光孙1）及单独授权的超光孙隧道21.36，当前JSON/同一Excel/台账439完整键一致，35车、401普通/38特殊、418非OC/21OC，35项相关回归通过。共享成绩表836条仅评估0导入；按用户要求不把零件缺失作为质量门槛，整体偏高，名义满星/版本/跑法合格值可作理论候选，低星分层高手参考，异常暂存。B站明确四区来源先保留参考；Driver投稿触发-799后停止。完整报告见maintenance/source-quality-review-20261024/数据质量评估.md。生产仍bd12e3fb2c2519b0238afd90/321，旧发布包不改。

## 2026-10-24 最新本地数据：秋王迁移后433（未提交/未上线）

按用户授权，Battista/秋王从国服五区理论直接迁移13条（9普通/4SC），原值不加减，图池外4条仅参考，旧420全保持。当前JSON/同一Excel/台账433完整键一致、无重复，34车，396普通路线/37特殊、412非OC/21OC；国服保护输入及OC原台账不变。35项相关回归通过，普通/SC新列渲染核对通过；详见LOCAL_INTERNATIONAL.md最新节及maintenance/battista-migration-20261024。仍未提交推送/部署，生产bd12e3fb2c2519b0238afd90和旧交付包保持。

## 2026-10-24 最新本地估算数据（420，未提交/未上线）

按用户明确规则及“保留更快”新增奇美拉18、杰哥OC15（既有3条更快OC保留）；F5按国服五区分段加时24项覆盖/补缺，含两条SC。当前JSON/同一Excel/台账420完整键一致、零重复，33车，387普通路线/33特殊、399非OC/21OC。源值与估算来源分别保留，F5旧杰基拉22.10按授权改为21.90；国服保护输入不变。106项相关测试及浏览器SC开关核对通过。详见LOCAL_INTERNATIONAL.md最新节和maintenance/chimera-review-20261024。生产仍bd12e3fb2c2519b0238afd90/321条；不要续用旧包部署本地新数据，暂不提交推送。

## 2026-10-24 最新本地待发布事项（不改变下方已验收生产版本）

本轮新增爱音R20/爱音E5/陀飞轮17条，回代用户国际Excel另1新增及2更快修改；当前本地364=333普通+31特殊、358非OC+6OC，32辆车，JSON/同一Excel/台账完整键一致。爱音R信仰之跃平跑17.89原样、铁道迷滑栏杆21.90；仅迁爱音E五区理论，四区/池外参考不运算。国际服R级筛选隐藏，国服保留；105项相关测试和浏览器核对通过。当前修改尚未提交推送或部署，详情见LOCAL_INTERNATIONAL.md文末及maintenance/aeon-review-20261024回执。生产仍bd12e3fb2c2519b0238afd90/321条，旧包不改。

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

## 以下为历史交接记录

## 2026-10-23 本轮接手核验（未进行新部署）

以下为本轮只读检查结果；不延续历史部署步骤，不表示已重新核验服务器内部状态。

- 已读取根目录CLAUDE.md/context.md及本仓库交接、车库部署与验收记录。根目录说明仍停在发布准备阶段；README部分版本/合并描述也有历史残留，不能据此判断实时状态。
- git fetch origin成功；本地main、origin/main及git ls-remote的main均为90db8b90969214f696501455f74a113af8d6e590。已包含3baf0b3车库修复和1760a11上线验收记录。相对打包源码3baf0b3，HEAD只变更CLOUD_HANDOFF.md、CLOUD_HANDOFF_PROMPT.md、GARAGE_DEPLOYMENT.md、GARAGE_LAYOUT_FIX.md四份文档，没有待发布的运行代码。
- 全部10个已登记工作树没有已跟踪文件的未提交改动（本记录写入前）；repo仍有既存未跟踪_star_curve_fit.py、gauntlet_data_shared.xlsx，均未操作。feature/track-top-three虽显示领先自己的旧远端25项，但它是当前main的祖先（main领先21项、该本地分支独有0项），不构成新的待发布功能。没有合并、切换分支、推送或清理。
- 本轮直接HTTPS读取/api/health返回200：status=ok、mode=production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true、score_version=42d62fde9b81197ac0558087a9a25f97、score_writes=true。首页/返回200；按backend.app的首页注入规则生成预期内容，与公网响应完全一致；styles.css公网与本地SHA256均为07d51cf3530b3b52ff96fb01ac68409fac214002b0a32c5773e9c5012e2fb4e0。/index.html返回404符合路由白名单，主页实际入口为/。
- 公网health不包含应用发布ID，因此6ee40a45b00b0e347bf973fe仍是最近用户回传确认的应用版本，不能仅据本轮HTTP检查声称重新确认了current或实际进程cwd。本轮未登录服务器，也未核验当前systemd、备份文件或timer；最近自动备份及下次调度证据仍见下方验收记录，10月24日计划执行不能提前记为成功。
- 本地8000–8011范围仅发现127.0.0.1:8011监听；PID8776的命令指向garage-toolbar-responsive/.local-accounts/preview，health为local、贡献/反馈关闭。其余历史环境文件保留，端口未监听不代表数据已删除。本轮未启动、停止或重建任何测试环境。
- 现有11文件车库交付目录保留，ZIP SHA256重新读取仍为fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb；没有重打包或变更旧包。本次未重跑回归，沿用既有验收记录；HTTP检查不替代登录、真实邮件及手机交互验收。

当前没有明确的新开发或发布目标，先由用户确定范围。账号、成绩、反馈、备份、测试数据、工作簿和未跟踪文件继续保留；服务器仍按给命令、用户执行并回传的方式逐步推进。本轮交接更新仅保留在工作区，尚未授权提交推送。

## 主线整合与通用交接入口

用户随后授权合并main。已验收的fix/garage-toolbar-responsive是远端main的后继，使用快进整合，无冲突；本地两份JSON、两份工作簿及保留脚本的哈希与修改时间均未变化。下文“未合并main”属于当时的历史状态，不再作为当前Git结论。源码整合未重新部署或修改生产环境，后续先fetch核对最新状态。

长期复用、无需填写版本号的提示词见[CLOUD_HANDOFF_PROMPT.md](CLOUD_HANDOFF_PROMPT.md)。该提示词以“上一轮部署已完成”为交接起点，要求接手模型自主探索代码和运行状态；本文件继续保留具体历史证据。

## 最新交接：车库布局修复已上线验收，工作暂停

本节覆盖下方历史状态。用户于2026-10-23确认页面验收完成，并要求更新交接、完成必要推送后暂停。以下生产证据来自用户回传，本次文档收尾未访问或修改生产环境。

- 当前应用 **6ee40a45b00b0e347bf973fe**，打包源码3baf0b3970dc638afd9910723943f3a7ad6a0781，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与实际进程cwd均已确认，切换时PID138683仅作历史记录。
- 最后完整health：status=ok、mode=production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true，成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。本次无数据库迁移，没有用包内JSON覆盖成绩。
- 用户确认页面验收完成；范围为此前要求的桌面对齐、手机微信分行以及保存/恢复/点亮/清空/排序。没有提供新的真机截图，不声称代理独立完成真机检查。
- 旧版在线备份演练、停服最终备份校验、新版备份演练均由用户简述确认通过，新版active_database_replaced=false；具体ZIP及演练目录未回传，不编造恢复点路径。
- 完整回传确认 **10月23日04:16:09–04:16:10 CST自动备份成功，退出码0**，文件scores-20261022T201610532450Z.zip，155551字节。这是升级前反馈版本的自动备份证据，覆盖下文“10月23日自动执行尚未核实”。
- 本次timer于 **2026-10-23 10:46:44 CST** 恢复enabled/active(waiting)，NEXT为 **2026-10-24 04:16:12 CST**。该次未来计划尚未执行核验；一条health回传被截断，随后单独回传完整JSON确认正常。
- 交付garage-toolbar-responsive/.production-build/delivery-20261023-garage共11文件，服务器上传目录/root/racepick-deploy/20261023-garage-6ee40a45。ZIP SHA256：fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb。包内只有index.html和styles.css有运行内容变化，另一个后端文件仅LF/CRLF不同，逻辑一致；旧包不修改。
- 最新交接分支 **fix/garage-toolbar-responsive**。main仍73e3f8b，未合并；反馈与其他已验收功能都在本分支历史中。先fetch核对最新状态，不把源码同步当成再次部署。
- 原8011、8010、8009测试环境及账号库、工作簿、未跟踪文件保留；本轮不清理目录、不改配置、不新增监控。当前6ee40a…与旧4a28f6d…及备份均保留。

详细记录见[GARAGE_DEPLOYMENT.md](GARAGE_DEPLOYMENT.md)和[GARAGE_LAYOUT_FIX.md](GARAGE_LAYOUT_FIX.md)。完成本轮文档推送后暂停，不自动继续合并、部署、清理或核验未来备份。

## 上一轮交接：反馈功能已上线验收（2026-10-22，历史）

本节为最新状态，覆盖下文上一轮排行榜升级的历史快照。所有生产事实来自用户服务器回传或明确反馈，本次文档收尾未访问生产环境。

- 当前应用 **4a28f6d76b9d3e93d3227120**，打包源码b17d6fcfe1c831b3f7fbb2b4923ea0a9efb33168，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与实际进程cwd已确认一致，切换时PID132627仅作历史记录。
- health：production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true；最后成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。用户确认昵称展示、按钮统一、文字反馈公网验收通过，功能正常。不能重新执行已完成的反馈/贡献/成绩迁移。
- 新版成套备份及独立恢复演练由用户简述确认通过，feedback_schema=1、contribution_schema=1、active_database_replaced=false；新版ZIP和演练目录未回传，不编造路径。
- timer于 **2026-10-22 21:46:12 CST** 恢复enabled/active(waiting)，NEXT为 **2026-10-23 04:15:58 CST**，替代下文旧的04:19:44计划；LAST仍为10月22日04:18:37，尚无新版首次定时执行成功证据。
- 本次已核实的旧版在线备份为scores-20261022T134206474628Z.zip，演练目录6ed23e688a30ec2f6f7418fd，counts27/15/2、昵称偏好1、未替换活动库。停服最终备份、迁移保护备份、新版备份的具体路径未提供，若需恢复点须现场只读核验。
- 当前文档分支 **release/account-feedback-production**；功能基线feature/account-feedback=28d4c96，生产适配b17d6fc；main最后核对73e3f8b，未合并。先fetch核对最新状态，源码同步不等于部署。
- 本次交付account-feedback-production/.production-build/delivery-20261022-feedback，共10文件，绑定4a28f6d…；ZIP SHA256为89fc52c23d5aea9f16eee985124f4eb51dd73706d0799b44d1529fac1cfe4b78。服务器上传目录/root/racepick-deploy/20261022-feedback-4a28f6d7保留。文档更新不修改已部署包。
- 先读本节和[反馈生产验收记录](FEEDBACK_PRODUCTION.md)文末，再查下文的历史部署、清理和保护约束。原8010及8009测试环境、账号、工作簿和未跟踪文件继续保留。
- 本轮未进一步清理目录。当前4a28f6d…、上一1fcc18c…及此前保留的651ea3d…不因新部署被自动删除。反馈schema1后不能直接切回不支持反馈的旧程序；禁止单SQLite恢复或用旧工具绕过兼容检查。

后续待证据：10月23日04:15:58计划备份的实际结果；本次未回传的具体备份路径。此处不自行新增监控或重复生产操作。本轮仅提交推送文档，不合main、不修改生产。

## 上一轮排行榜已验收状态（历史）

本交接依据用户服务器回传和明确验收反馈，不是代理独立登录服务器的结论。历史文档中的“仅本地/尚未上线”以最新验收记录覆盖；未来操作前重新只读核验。

- 域名https://racepick.cn；Ubuntu24.04、Python3.12、Nginx代理127.0.0.1:8001。服务racepick-accounts，应用链接/opt/racepick/current，数据/var/lib/racepick。
- 当前已验收应用 **1fcc18c06a7b920ed0aa8b0b**，源码fa23531106e4eec54ccf9cd91164475888f354a9，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与运行进程cwd已确认一致；主进程当时130103，后续不能盲用旧PID。
- health：production、schema6、community_schema1、contribution_schema1、contributions=true；最后成绩版本42d62fde9b81197ac0558087a9a25f97、score_writes=true。版本和数量是历史快照，勿强制修回。
- 排行榜质量0–10＋正式采用10分、历史不补计、公开昵称/匿名、三类主页导航已上线，用户确认功能正常。原公告、账号管理、手动车库及成绩版本化均已完成，不重复迁移。
- 备份和独立恢复演练通过。timer在2026-10-22 20:28:08 CST恢复enabled/active(waiting)，NEXT为2026-10-23 04:19:44 CST；尚无该次定时执行回传。

## 先读与后续操作

先读本文件及[本次部署与清理记录](CONTRIBUTIONS_PRODUCTION.md)，再查COMMUNITY_DEPLOYMENT.md、SCORE_PRODUCTION_DEPLOYMENT.md、PRODUCTION_DEPLOYMENT.md和工作区根目录CLAUDE.md/context.md。本次文档分支release/contribution-production；main最后核对73e3f8b，功能分支feature/contribution-leaderboard为0938886，生产适配fa23531在release分支，未合main。先fetch核对最新Git状态，不把源码同步当成部署。

本地交付位于contribution-production/.production-build/delivery-20261022-contributions，9文件，绑定1fcc18c…；不可修改旧包冒充新版本。完整ZIP SHA256：aa7e70ba59f203c6ed2870d5689a840c8202c7534fd2234f10a5108e2ad0e0d9。当前服务器上传目录/root/racepick-deploy/20261022-contributions-1fcc18c0保留。

先确认新的任务范围；没有新部署目标时不重跑上线。发布先准备完整校验包，再按用户回传逐步暂存、临时库自检、备份、必要迁移、切换、验收和恢复timer。每次切换必须核对current、服务状态、/proc/<MainPID>/cwd、公网health，不能只看终端目录。

## 数据与恢复边界

保留所有账号库、测试环境和工作簿，特别是repo/gauntlet_data_shared.xlsx、repo/_star_curve_fit.py；不reset --hard、clean或自动同步工作簿。原8009独立模拟环境保留，不能把其数据导入公网。

成绩从独立score-state读取，代码包JSON不覆盖正式成绩。main的73e3f8b仅同步了云端肥龙★6四区高手34.90和普通镜像，工作簿未同步；后续云端写回不会自动同步本地JSON/工作簿。

迁移前最终成套备份scores-20261022T122554381864Z.zip；迁移保护备份scores-20261022T122638564366Z.zip；新版运行后盘点备份scores-20261022T122749408259Z.zip。均在/var/lib/racepick/backups。原始演练输出及证据限制见部署记录，不编造备份与演练目录映射。

禁止单SQLite恢复；灾难恢复须保留现场、独立目录演练并核对整套数据。贡献schema1后不能直接切回旧代码，即使保留了上一版本651ea3d…也不代表兼容回退。不要使用旧部署工具或手工ln绕过兼容检查。SMTP密码不输出、不打包。

## 已清理与继续保留

用户已确认删除旧应用目录09897d5f81a696dca0b95c8e、3ac58aba697f3189b751d6ea、7a0f2927404cab20f0a5a020、c907541d0c209f9a38a181a5；以及/root/racepick-deploy下accounts-release、accounts-credentials-fix、data-20261021、score-versions-20261021。旧包本地留档及校验已核实。约释放300M，非精确测量。

当前版和上一版应用保留；当前上传目录、community-20261022、20261016-icp、nginx-before-accounts-ghnuwvit及顶层静态发布文件保留。所有业务数据、成套备份、历史SQLite、score-state、恢复演练和/var/www静态目录均未清理。Nginx仍引用静态root，不可仅因代理已启用就删静态目录。以后清理重新核对路径/引用并取得具体范围授权，不扩大本轮删除授权。

## 尚无新证据的事项

- 10月23日04:19:44计划备份是否实际成功。
- 新规则启用后的真实投稿计分与发布回执逐项证据（不否定用户已确认的功能验收）。
- 公告由用户自行发布；本轮没有代发或核验其发布状态。

本次收尾仅更新并推送文档，不合并main，不修改生产、发布包或任何账号/成绩/工作簿数据。

## 反馈生产准备阶段记录（已被文首验收结果覆盖）
功能基线28d4c96，在独立release/account-feedback-production准备生产适配与交付。随后用户逐步完成安装、迁移、切换、备份演练及timer恢复，并确认公网功能正常。完整证据边界见FEEDBACK_PRODUCTION.md文末，最新状态以本文件首节为准。

## 2026-10-24 国际服本地验收通过，提交及发布包准备

用户明确本地验收通过，授权统一Excel为旧字体格式、提交推送并准备完整可校验包；本轮禁止服务器操作。国际服五区满星理论321条（315非OC/6OC），普通291/SC30，29基础车、44图42有值，富士两空图仍在最后。运行版本c7ea2f354e90bf70711c04ae05ced8d894ac9c1168a9b4c18393c9a9fd1b31f0，国际云车库/投稿/版本链及自审免积分/OCR未实现。

国际维护表与shared已统一宋体10pt及旧表头风格，成绩、行列、冻结及OC/SC区分不变；国服主表和同步副本已有宋体，字节保持。修改前原件在数据源/international-prep-20261023/maintenance/change-history/style-unification-20261024，历史表和资料均保留。gauntlet_data.global.xlsx为当前国际321条版本库副本。shared仅格式调整，仍是未跟踪文件；不将其历史缺项当删除授权。

现有生产打包器已补国际组件及独立哈希校验，保留旧包读取兼容；自检增加三JSON及国际入口HTTP检查。发布从干净提交及锁定Linux离线依赖构建，工作簿、账号/成绩状态、反馈、凭据及本地测试库不入包。包内国服JSON新增22.84不会自动覆盖服务器score-state，是否需要单独发布该成绩须现场核对。具体流程见INTERNATIONAL_DEPLOYMENT.md，包内RELEASE.json绑定真实源码/数据提交。

本轮未访问或修改生产，当前运行应用、health、备份timer及公网验收未重核。之后仍由代理给一条命令、用户执行回传后逐步核对，不重跑生产迁移、不初始化、不清理旧文件。

### 本轮发布包已生成并校验（尚未上线）

源码/国服数据提交5ade7ea3598eb104f136365fb0a51574c16d8013已推送main并用ls-remote核对。发布ID bd12e3fb2c2519b0238afd90；完整目录repo/.production-build/delivery-20261024-international共14文件，外层SHA清单13项全部通过，ZIP内85白名单文件（含19锁定离线依赖）。内层racepick-accounts-release.zip SHA256：1ecc93ea6d36eec12a5e3ca0ed96acddf8847dc6f549546c52d1eac9c11939ee。

便于完整上传的归档repo/.production-build/RacePick-International-20261024-bd12e3fb-delivery.zip，SHA256：ac6016cf81b3fa5f900a4d1aea1bc7c538d1b4218916fb8947d1fa8c835c8036；归档含上述完整14文件目录，已逐字节回读。PACKAGE_VERIFICATION.json保留详细回执。使用提交的干净独立检出构建，保护原工作树未跟踪脚本/shared；数据JSON与提交字节一致，Windows代码检出换行差异已独立核对，内层manifest绑定实际交付字节。

本轮Node80+Python125共205项通过，交付目录自带工具的独立本地暂存、解包目录验证和临时库HTTP自检通过；原始434资料哈希保持。Linux/Python3.12离线安装及原生自检尚待上传后用户执行。未操作服务器、未激活、未生产迁移；实际运行版本、健康、备份调度、线上成绩差异和公网验收均留待部署轮核对。后续文档提交不改变该已校验包绑定的源码提交。

核验补充：本轮Node34项+Python72项共106项通过；生成器--check通过，数据版本08d864c84f8c187f787095547d9d8c63df13f7f9be3a655b5198f5f32090395e。原434项来源校验全部通过，旧发布ZIP哈希保持；受保护输入逐项字节及mtime复核通过。详见accepted-review258-20261024/final-verification.json。

## 2026-10-24 标注作者质量复核（635条活动数据未修改）

用户对BG16/BG37霓虹gtr、BC4小牛、AU3及AT21:AU23的成绩提出偏慢疑问，要求检查作者其他成绩。定位作者为疯狼、皮卡丘，源表全部42+145=187条已复核；其中此前采纳4+32=36条。36条中25条普通车虽名义满星，但性能分及部分参数低于已抓取国际服满改目录；11条EVO不套用基版参数判断，仍需单独核实。满星不等于满改，先前补缺筛选没有据此充分限制理论适用性。无特殊跑法图且有导入前国际同车普通参照：疯狼14条均慢，中位差+0.909；皮卡丘18条中17条慢，中位差+1.250；均为原始圈速差，不是原作者能力或跑法一致性的证明。

建议25条普通车先撤出满改理论候选，原始配置成绩保留作高手参考；11条EVO单独复核，不自动降档或删除。活动JSON/同一Excel/台账仍635条，无成绩改动。国服喧闹铁路小牛理论18.60对现国际19.98，仅作为参考，未迁移；两图霓虹gtr在当前国服表没有同车同图值，不编造参照。两作者源记录均没有BV号，未据同名绑定B站账号，未声称检查全站视频投稿。报告、全部187条及已采纳36条逐项清单在maintenance/author-quality-review-20261024。保护输入逐项哈希/mtime保持，未改代码、国服、工作簿或生产，未提交推送。

## 2026-10-24 来源地图纠正：旧evo狼崽23.00实际应归龙卷风山道23.05

用户明确指出该旧来源录入图名错误，原图应为龙卷风山道23.05。已在活动台账隧道冲刺21.89的previous_record旁明确标注历史来源错图、更正目标与用户最终值23.05；原误识别记录保留追溯，不再视作隧道同图来源。龙卷风现有用户表内值22.99更快，按保留更快规则不覆盖，23.05作为该图纠正后备选来源保留。隧道21.89仍是用户独立指定最终值，Fordo/煙KiVi只关联纠正后的历史来源，不冒充21.89视频证据；本轮未重新看视频。

活动600条值、现有Excel字节与mtime全部不变，国服/OC/36条高手参考保持。仅来源台账、当前维护备注及生成manifest来源哈希更新，dataset_version仍2e4305806e2f8a210ee458db1b70283847c5c512903f0daf04d62c826c8eea73。生成器--check与12项数据回归通过，纠正及回执见maintenance/wolf-source-map-correction-20261024，改前备份在maintenance/change-history同名目录。未提交推送、上线或操作服务器。

## 2026-10-24 剩余本批已采纳成绩质量复核（仅审核，600条未修改）

用户要求重点检查满星未满改及地图错误，发现后先列审核，不改成绩/上线。范围为本批258项中实际写入245减已撤36后仍生效209项，13项当时保留原值没有导入；额外检查全部600活动台账地图目标与国服迁移源映射。对源XLSX重新从XML逐行读取209条，车辆/作者/秒数、配置页唯一关联及目标映射均核对，无新结构性错位。176条普通车型参数与归档满改一致；1条爱音E偏离中心33.85（源33.8，耄耋，6星）配置4102/480/84.18/39.97/18.33低于实时满改5106/491.5/86.23/46.03/25.94，建议退出满改理论待用户审核。12条玻璃满星分5190相同但加速84.61/氮气21.71冲突，实时目录84.28/27.50；不能直接判未满改、OC或国服配置。20条EVO（女武神7、狼崽13）星级有记录但性能分和四维缺失，只标缺证待核，不套用基版参数，不以零件作门槛。33条配置问题均未改动。

本轮公开view接口3条视频成功：BV17jtnzgEC6含11条Fordo记录，标题“对三、四区友好”，B站转载Moon_River-OL，列为分区待核提示而非认定实际四区，11条配置本身均与满改目录一致；BV13LgW62E3D标题AL金恶魔擂台圈速，3条；BV1PCRmYHEQ2标题国际服擂台全图参考，1条，简介明确并非最快。194条没有BV号；15条只核验元数据，未逐图重看终点/路线，所以原作者源表错图未能独立排除，不声称209条地图均实测验证正确。既有23.05龙卷风错图已纠正，不计新发现，隧道21.89和龙卷风22.99保持。

实时ASEC只重读304/314并与归档一致，其余车型只使用2026-10-23已抓取目录，不声称全部实时重抓。公开网页工具无法打开API后，正常urllib读取公开接口成功，无cookie/登录/绕过；没有重新尝试投稿列表风控接口。报告maintenance/remaining-adopted-review-20261024/剩余已采纳成绩复核.html含33配置逐条、11分区提示与全部209行、原值和回退值；原始响应及核验JSON同目录。工作簿13页、国际/国服活动JSON、台账、OC/36高手参考、目录、代码等保护输入哈希及mtime保持，原434项来源校验通过；未提交推送、打包或操作生产。

## 2026-10-24 玻璃破冰者二次审核通过（仅审核记录更新）

用户明确接受T0352玻璃/格陵兰·破冰者，保留31.85，不回退旧32.13。accepted-tier-review-20261024/bolide-ice-secondary-review.json及对应HTML已由待二审改为用户已接受，源31.8及配置参数冲突、未知作者/无链接等事实继续保留；接受不等于这些缺证已补齐。回执在maintenance/bolide-ice-approved-20261024/approval-receipt.json，原待审记录已备份至maintenance/change-history/bolide-ice-approved-20261024。

本轮没有改任何成绩：运行599、完整维护614键、现有Excel、两份成绩台账、国服/OC/高手参考及程序文件字节和mtime保持；不生成新运行数据，不修改manifest或数据版本。只更新审核记录/交接说明及其校验；未提交推送、打包或上线。


## 2026-10-24 仓库目录分类（本地未提交）

本轮按用户要求整理GitHub仓库目录：24份根目录说明文档移至repo/docs/，14个顶层回归测试移至repo/tests/，2个本地隔离演示脚本移至repo/examples/；README中英文入口及文档相对链接、测试命令、示例导入路径已更新。后端测试仍在backend/。文档索引repo/docs/INDEX.md；后续交接入口为repo/docs/CLOUD_HANDOFF.md，可复用提示词repo/docs/CLOUD_HANDOFF_PROMPT.md，国际服维护说明repo/docs/LOCAL_INTERNATIONAL.md。

production_release_tools.py和build_production.py改为从docs读取源码文档，交付包与应用包仍保留原文档文件名及包内位置，历史发布包不重打包。前端资源、JSON、工作簿及数据维护脚本位置不变。移动保留既有未提交文档内容；国服/国际服JSON、当前工作簿、两个完整发布包逐文件哈希未变。现有gauntlet_data.xlsx在本轮开始时也已被Git标记为修改，保留用户保存内容，不自动回代。

本轮发现repo根目录44个.bak文件（合计7798392字节），全部被Git忽略，未在当前Git跟踪清单。自动审批在执行前拦截批量删除命令，仅返回blocked by policy，因此未删除备份、未换工具重试绕过。清单保存在本地归档/repo-layout-20261024/bak-files.json；并非所有历史备份均保证可从GitHub恢复，Git只保存已提交版本。

本地运行仍601条，完整维护与四区/高手隔离策略不变；线上仅沿用此前用户验收599条的结论，未重新访问生产。正式公告草稿路径不变且未发布。未提交、未暂存、未推送、未上线，不删除分支/服务器旧版本/备份/演练目录。文件映射和保护哈希见本地归档/repo-layout-20261024/layout-result.json。

目录调整验证：前端81项全通过；Python214项执行成功（1项环境条件跳过）；示例仅导入检查通过，未启动演示或生成账号库。601条生成器--check、40文件映射、13份数据/工作簿/发布包保护哈希及Markdown相对链接校验通过。44个bak仍保留，删除未执行；Git暂存区为空。


## 2026-10-24 目录分类提交范围与备份删除确认

用户确认已自行删除bak，并授权提交推送本轮分类更新。现场只读检查repo根目录.bak为0，确认删除已完成；之前的审批拦截记录保留为历史过程。fetch后main与origin/main在提交前一致（fe070225），没有需要合并的远端更新。

本轮提交仅包含docs/tests/examples分类、README及相对链接、测试/演示导入路径和构包文档来源路径调整，并携带移动文档中既有的本地交接说明。不暂存任何JSON、Excel、用户来源表或本地实验脚本；601条数据保持本地未提交，线上沿用上次599条验收记录，公告未发布。本次推送不涉及生产服务器切换、成绩导入或清理。

分类实现已通过前端81项、Python214项（跳过1项）、示例仅导入检查和Markdown链接核对。本轮再确认数据/工作簿字节未改，提交前检查暂存文件清单和空白错误。推送结果以本地回执layout-push-result.json及远端main提交核对为准。


## 2026-10-24 本轮接手核验完成：未开启新部署，等待范围确认

本节为本轮实际核验结果，覆盖历史状态描述；不将上一轮599条已完成部署当作半途部署，也不将后来准备好的切服修复包视为已上线。

- 已读取根目录CLAUDE.md/context.md及docs/INDEX.md、CLOUD_HANDOFF.md、PRODUCTION_DEPLOYMENT.md、INTERNATIONAL_DEPLOYMENT.md、SERVER_SWITCH_FIX.md等入口，结合Git、发布包与公网只读响应核对。git fetch origin成功；本地main、origin/main及git ls-remote均为d84becdd854dc6156d9517ae4234d9e6795ef058。4ff5f6f之后main只有两份交接/部署文档变化。
- 7个已登记工作树：主repo有原6份已跟踪修改（3份global JSON、国际/国服两工作簿、CLOUD_HANDOFF）及3个未跟踪用户文件（来源Excel、_star_curve_fit.py、gauntlet_data_shared.xlsx），暂存区为空；其余6个工作树无未忽略修改。community-controls相对main仍独有文档提交6ef9062，不自动合并；其余开发工作树HEAD均为main祖先。release-build-switchfix-20261024干净、detached于4ff5f6f。未切分支、合并、暂存、提交、推送或清理。
- 本轮HTTPS GET /api/health为200：ok/production，schema6/community1/contribution1/feedback1，contributions/feedback/score_writes均true，国服成绩版本42d62fde9b81197ac0558087a9a25f97。公网国际三份JSON逐字节等于已上线0ee524e3包及待发布修复包中的对应数据，版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e，599条/49车/44图、38SC/21OC，其他区档为空。公网api.js逐字节等于旧0ee524e3包、与切服修复包不同；styles.css与本地一致。这证明被读取的公网资源仍未含切服修复，不能据此重新证明服务器current或进程cwd。
- 最近用户回传验收的应用ID仍为0ee524e31734b44fb7771b79，桌面/手机微信验收、备份及timer恢复为此前证据。本轮未登录服务器，未读取Nginx实际配置、429日志、systemd、内部版本、备份文件或timer；10月25日备份未核验，不宣称成功。停服最终备份路径/SHA/演练目录历史缺项仍保留，不补造。
- 当前本地运行601条（580非OC/21OC，563普通/38特殊），版本7fffdbbb888fb2e0c7d54accf04f12b32719f735adbaf2c057617d34a6f67a71；build_global_data.py --check本轮通过，无写入。完整维护JSON实际616键=五区理论601+四区理论11+两区高手各1+普通镜像各1。601相对已提交599仅新增evo肥龙幽灵船22.02、岩石山谷20.66及版本元数据，未获本轮发布授权。完整维护和36条独立参考不自动进入运行包。工作簿本轮未同步、导出或逐格重验，保留现有保存内容。
- 切服修复完整包66b9d32c1857d2b3c2cc533f仍在repo/.production-build/RacePick-SwitchFix599-20261024-66b9d32c-delivery.zip，10949010字节，本轮重算SHA256=f35d888ef61a5a9591a99e1bccecc433946a166136b36322e9963605ca15171a；交付16项SHA、外层17项逐项回读及内层85文件manifest大小/哈希全部通过，19个wheel在清单内。国服两份JSON和国际三份JSON与0ee524e3旧包字节相同。仅复核现有包，未重打包或暂存/激活应用。86项前端、214项Python（1跳过）、临时库与Nginx对照为上轮证据，本轮未重复运行，亦不冒充生产Linux验证。
- 本机Python3.14.4、Node24.15.0；8000–8099未观察到监听，相关进程查询未观察到本项目Python/Nginx服务（不等于其他端口或所有占用均已排除）。现有测试库/邮件/验收资料、3个保留sandbox、各工作树忽略目录继续保留，未启动/停止/重建测试环境。生产目标仍以包内Ubuntu24.04/x86_64/Python3.12为准。
- 正式公告草稿仍在maintenance/local-hold-announcement-20261024/国际服五区理论更新_正式公告草稿.txt；本轮仅确认文件存在，未发布。OC插值/外推继续暂缓，不新增成绩或扩大范围。

本轮只追加接手记录到根目录CLAUDE.md、context.md及repo/docs/CLOUD_HANDOFF.md；未授权提交推送。现有数据、工作簿、3个未跟踪文件和正式公告草稿在记录前后SHA256及mtime_ns逐项保持。

下一步先由用户确认本轮范围。若决定部署切服修复，复用上述599包及01-readonly-preflight.sh，先仅给用户当前一步只读命令，回传核对nginx -T/实际日志、current/进程/health/备份调度，再决定后续步骤；Nginx map/新zone与站点limit_req须成套调整、保留配置备份并先nginx -t。不能夹带601、覆盖score-state、重复迁移、发布公告或清理旧版/备份/演练。本轮不自动继续部署或创建监控。
