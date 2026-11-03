# 原生完整镜像：网站侧分批交付表

2026-11-03恢复：用户已要求继续其他契约与源码。B–E和正式主页presenter现已完成本地交付，最新入口MINI_FULL_MIRROR_HANDOFF_20261103.md及分批文档/固定OpenAPI；生产写和真实平台验收仍未执行。下方“暂停/待固定”为前阶段历史清单。

2026-11-03用户新范围：个人主体，不用web-view；除有明确事实证明不可行或移植成本极大并经用户决定的事项外，镜像全部网页外观和功能。旧四项V1及旧暂停仅为历史，不再删减功能。当前没有新增获准的功能豁免。

本文件优先描述后续开发范围，既有发布/生产状态仍按各自回执。网页功能树基线c26a708，五个共享模块仍198999a；本轮只提交网站自有A批代码/契约/测试。检查窗口中小程序树HEAD已从用户所列c6e6bf1推进为34684cb2447e65396f00a84480e4c8474f484f36、未观察到dirty；只读核对，未编辑/切换/提交该树或向其他对话派任务。网站原数据、INDEX、MINIPROGRAM_COMPATIBILITY、FEATURE_POLISH及map_recognition.js等并行修改保留。

## 分批状态及交付要求

| 批次 | 已核对的网页/后端来源 | 当前交付和后续必须覆盖 |
|---|---|---|
| A：身份/账号/主页接线 | auth.js、profile_store.js、backend/app.py、roles.py、community.py、mailing.py；主页/快照 | 本批新增独立账号会话、注册/验证/重发/重置、邀请码、退出/再认证、实时actor/组件开关、双服独立账号云车库revision/OC。固定契约MINI_ACCOUNT_CONTRACT_A_20261103；仅API ready，小程序账号UI/真实邮件/真机仍待接线验收。主页原文提取临时适配继续保留，正式presenter为A2。 |
| A2：DOM无关主页presenter/主题 | index.html中的filterBySearch/filterByClass/sortCarList/getTopCars/updateSubtitle、别名与初始档位；theme.css/ui.css/styles.css | 后续正式导出同一snapshot/服别/区档/地图/车库/星级/OC/SC/筛选输入，输出subtitle、可见车序、单图候选、方案摘要/空状态及网站原主题值。先保留临时198999a提取器的源/生成SHA与结构漂移拒绝，再替换为正式导出；网页及两种渲染同输入对照。不得重写第二套算法/映射或改成整齐网格车签。尚未新增此导出，不冒称完成。 |
| B：成绩表/权益/直达 | coverage.html/js/css、backend/coverage.py及rights/matrix、score_scopes/global_scores、contributions权益 | 待固定原生协议/源码。两服目录、区档、车型/星级/OC/SC、覆盖/估算来源、分页过滤排序、活动版本、权益/未解锁/无数据的不同状态全部保留；主页“新功能”和单图前三直达参数保留。服务端判定权益与版本，不靠客户端隐藏。当前web接口仍是Cookie契约，客户端不得猜原生路径。 |
| C：投稿/贡献榜/个人中心 | submissions.html/js、leaderboard.html/js、backend/submissions.py、contributions.py、score_versions.py | 待固定字段、证据上传/所有权/删除/保留/安全策略、同key恢复、基线变化、我的投稿/补充状态、月榜/总榜/个人明细、昵称匿名权限。原生与网页复用同一校验/审查/权益，不复制规则；未知图片安全服务不写成已接入。 |
| D：反馈/公告/消息 | feedback.html/js、announcements.js、notifications.js；backend/feedback.py、community.py、notifications.py | 待固定私人反馈/公开内容权限、列表详情回复分页、独立已读/未读、开关、公告范围/版本与缓存失效。没有外发通知授权，只做协议和隔离夹具。 |
| E：管理员/超管 | admin_submissions/admin_access/admin_accounts/score_versions/usage等实际工作台；roles/community/submissions/score_versions/feedback/usage后端 | 待逐个核对对象权限，先只读/隔离协议，再按明确范围实现审核评分/预览、发布批次回滚、账号/邀请码/公告/反馈/统计。高权限写必须原业务再认证、revision/幂等、审计/拒绝矩阵；A的role/authenticated_at不自动授权这些操作。镜像UI不代表批准真实审核/生产发布。 |

各批都交固定源码/文件SHA、精确请求/响应/错误/分页/时间/编码、撤销/跨服/角色变化/缓存失效及新隔离fixture入口。源路径表仅供审查，不是待实现接口的公开承诺。客户端只按已固定协议接线，不从现有网页URL推断Bearer可用。

## 统一协作与呈现约束

网站归口backend/**、共享模块/presenter/主题导出、网站接线、发布工具/模板及自有契约。小程序归口miniapp/**、平台request/storage/media/hash/lifecycle、客户端测试/构建适配。公共文件按路径/基线/签名/DTO/兼容影响/用例交接，不同时改两树或人工复制第二套成绩/规则。5个共享模块原Git blob保持198999a；本轮不改主页index或主题，临时提取器仍可按固定源生成。

对照覆盖未登录、微信访客、普通、管理员、超管，两服同开关/快照/输入下的显示内容、候选和完整方案顺序、星级/时间、按钮状态和后端拒绝。每批分别记录接口夹具、开发者工具、真实平台身份、手机相册、iOS/Android、TLS合法域名、图片安全和用户验收，不能相互替代。

账号与本机草稿按actor/server隔离；登录/GET失败不覆盖车库，冲突保留本地与远端。用户随后要求本轮先接通国际服账号云车库，网站与原生均按同一账号、分服独立记录、显式导入和revision冲突语义支持；本机游客资料保留。本轮仅会话级微信访客↔RacePick账号关联，用户明确邮箱/密码登录，不静默建号/永久绑定。

## 发布边界

现阶段在独立状态验证，不依赖用户把秘密贴聊天。真实微信登录/邮件/域名和图片策略仍需用户在服务端安全配置；不将fixture验收写成真实平台/真机通过。维护数据仍4504/693未提交/未重新冻结，仅按接收SHA本地使用。正式构包需批准源码/功能与维护新冻结，独立干净检出，排除账号库、密钥、工作簿、完整维护/测试数据。不生产写入、部署、体验版上传/提审/发布、公告、清理或监控。
