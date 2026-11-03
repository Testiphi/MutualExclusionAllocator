# A批账号与双服云车库固定交接 · 完成后暂停

2026-11-03。本轮从网站c26a7088efba783b69baf986f291e593d8aa411d开发A批；用户中途要求国际服车库现在绑定账号云端、做完暂停，已作为最后范围实施。最终提交/逐文件SHA及Git blob见外层 `offline-evaluation/mini-account-a-20261103-01/commit-receipt.json`。不推送/合并、不构正式包、不操作生产、不派其他对话任务。

## 给小程序侧的固定材料

- `MINI_ACCOUNT_CONTRACT_A_20261103.md`：账号前缀 `/api/mini/account/v1`，明确邮箱/密码登录，独立账号Bearer、actor/角色/开关、TTL/撤销/再认证、注册/验证/重发/重置/邀请码、显式导入、操作恢复、分服车库/冲突/缓存。
- `GLOBAL_PROFILE_CLOUD_20261103.md`：本轮追加的国际云车库最终语义、网页/原生同库、星级/OC、独立revision、新schema、迁移/备份/恢复/旧程序拒绝及暂停边界。它覆盖早先仅本机的阶段结论。
- `MINI_MIRROR_ROLLOUT_20261103.md`：完整原生镜像范围保留；旧四项V1不再删减功能。B–E、正式主页presenter/主题导出均待后续恢复，不在本轮继续。

旧 `/api/mini/v1` 访客/快照/OCR继续使用原访客token，不升级其权限。账号登录使用父访客token+明确的邮箱/密码，返回另一种rpa1账号token；账号私有请求使用它和X-Account-ID。两种token不能混用，不建立静默永久微信绑定。网页Cookie/Origin/CSRF保持原行为，没有通配Origin或Cookie桥接入口。

两服GET/PUT `/profile?server=cn|global`现在都为账号云端，各自记录/revision；global包含ocMap，原计算仍五区满星理论。恢复profile-save必须同时提供server，同key不能换服/换正文。客户端保留本机游客、按actor/server分开的草稿和冲突两份；登录/GET不自动导入。本批后端已支持，原生账号页面与transport仍由小程序侧接线，不能把接口完成写成原生整页已验收。

五个共享模块allocator/race_scores/app_state/profile_store/selection_core保持198999a原Git blob。网页auth.js/api.js/index.html/config.js仅增加国际账号云车库接线和分服草稿，未改算法或规则。客户端现有固定198999a主页提取器继续按其固定源使用，不自行从新index抽取并宣称presenter已完成。

## 隔离入口与证据

本轮追加云车库的当前预览为 `http://127.0.0.1:8046/`，原生基址 `http://127.0.0.1:8046/api/mini/account/v1`；只用新lab/新访客/新账号原生状态和空业务库，fixture微信验证、file模拟邮件。源目录/新状态/当时进程信息见global-cloud-lab.json、cloud-process*.json。8033/8043/已有8044及前阶段8045未启停/改库；不要拿旧端口结果判断本轮国际云车库。

本轮浏览器测试已占用fixture-code-1及固定key cloud-browser-fixture-session；继续fixture联调可使用fixture-code-2及自行生成并保留的key。所有token/密码仅内存，随机测试密码未写入材料；接收方请在此新隔离环境明确注册自己的测试账号，从本机file outbox取验证token，不请求真实邮件或生产账号。真实平台模式仍需用户私有AppSecret、隔离后端/域名/TLS/策略；不把秘密贴聊天。

验证结果：

- 最终前端131项通过；Python全量377项执行，376通过、1项平台相关跳过，日志frontend-global-final.log/python-global-final.log。旧网页账号、访客识图、共享计算与组件发布回归在内。
- 双服云车库/原生账号定向22项通过：网页与原生读写同一国际记录、CN不变、星级/OC、空车库、revision冲突、跨服key拒绝、角色/账号隔离、迁移幂等、完整备份恢复及不兼容旧程序拒绝。
- 独立已安装Chrome实际操作：明确登录→首次云端null不导入→用户选择导入本机→仍不上传→点击保存→重载恢复车辆/OC→另一个独立浏览器登录恢复→原生账号接口读到相同记录。国服云车库与两份游客存储保持。1440px/390px截图已查看，无横向溢出、pageerror为空、“新功能”保留。证据global-browser.json/global-browser-native-final.log及global-cloud-desktop/mobile.png。
- 浏览器工具默认缓存缺失后改用本机Chrome；两次夹具过早读取页面的失败日志保留，最后增加等待真实DOM渲染后通过。错误期没有把失败写成通过。前阶段http-account-flow.json的global=device为用户追加要求前的历史证据，以最终cloud证据为准。
- 原始30个修改文件继续保护；最终保全与五共享模块blob对照记录随交付。运行数据仍按4504/693接收SHA本地使用，未提交/未重新冻结；工作簿/完整维护/成绩/映射/估算未动。截图里可能显示工作树已有未提交识图文案，不代表它纳入本提交。

## 生产准备与暂停

国际云车库需要新增global_profile_schema=1/profiles_global；新建隔离本地库自动创建空组件，旧库/生产库启动不自动迁移。迁移工具、备份manifest与恢复检查、capability及激活兼容门禁已准备。生产迁移/停服/服务锁/成套恢复点/Linux演练仍必须用户后续单独授权、由运维执行，本轮没有执行，也未改变正式两服成绩或写回开关。

真实微信身份、真实邮件、TLS合法域名、手机相册/iOS/Android、图片安全与本轮Linux正式迁移均未据本机结果宣称通过。没有外发通知/邮件、体验版上传/提审或生产部署。正式包仍需批准功能/源码与维护侧新冻结，独立干净检出，不能拿旧冻结构包或覆盖score-state。

按用户最后指令：完成以上源码固定和交接后暂停。不继续B–E、正式主页presenter、部署、迁移正式库、推送/合并、构正式包、发布/公告、清理或监控。
