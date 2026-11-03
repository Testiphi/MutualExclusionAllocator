# 原生镜像 A–E 接线与固定来源

2026-11-03，小程序树 `miniprogram-v1 / feature/miniprogram-v1`，接手HEAD `8e65e47`。用户回交A与B–E之后继续实施客户端；个人主体原生路径不变，识图保持地图上方的小按钮。没有改网站公共文件、维护数据、正式库或微信后台，没有向其他对话派任务。

## 来源核验

- A：`a38faaf4c7fa05f853b89ae2db31708ec2f8b52d`，回执22文件。
- B–E、正式presenter/主题/机器契约：`8da16097978500f1a127cc92ada09fcc1a653f2b`，回执33文件。
- 两份回执全部Git blob一致。A的tests/test_production_release.py与B–E的tests/fixtures/home_page_reference.cjs文件SHA差异仅CRLF/LF，未修改来源来凑校验。其余原字节SHA一致。
- 原共享五模块仍从 `198999a9ff5ca2ad524c50112ac6e03f5f18149f` 原字节生成。正式home_presenter/home_theme和OpenAPI从8da1609单独清单生成，附源SHA/长度。小程序不支持直接require JSON，构建额外生成feature_contract.js并记录生成SHA；主题生成WXSS，原始完整主题保留供对照。
- 临时网页原文提取器及旧证据保留作冻结oracle，不再被local/native运行服务引用；实际筛选、车序、别名、初始档、副标题、前三和完整方案摘要均委托正式presenter。源文件不从网站dirty页面复制。

## 已接入的客户端

| 范围 | 本轮原生实现 |
|---|---|
| A账号 | 独立账号页：邮箱/密码登录、注册、验证/重发、找回/重置、邀请兑换、再次认证、退出、丢失响应查询。密码/token不持久化，页面隐藏清密码/邮件token/邀请码。访客与账号各自内存transport；不桥接Cookie/Origin，不永久绑定微信身份。 |
| A两服车库 | 复用固定ProfileStore，按origin/actor/server隔离账号草稿；云端null与合法空车库分开。登录/GET不导入，用户导入先临时，明确保存才上传；Global含OC且不改CN revision。409保留两份，明确加载远端或以最新revision保存本地。未知保存结果先恢复，后续本地修改不被查询结果丢弃。GET失败保持本机草稿、阻止未初始化账号车库改写。 |
| B成绩表 | 两服、区/档/普通与特殊跑法、星级及逐车星级、OC、车型搜索、缺成绩、48列分页、横向表格、权益选择与投稿target直达。“未解锁”和“无成绩”独立呈现，不推算隐藏成绩或插值。 |
| C投稿/贡献 | 目录驱动的单条/1–20条录入、创建草稿/提交、我的投稿/审核队列、过滤/分页/详情/历史/补充；证据仅相册、≤2MiB multipart、认证下载临时文件、停用。贡献榜/月/总/指定月份、本人明细、公开昵称/匿名设置。来源视频仅复制链接供浏览器打开，不下载/上传视频。 |
| D社区/已读 | 私人反馈与补充、公告/提醒/忽略、未读渠道及详情跳转；实际详情中明确标记已读，列表/刷新不自动读。内部统计独立token、身份变化重置、Global限制home、失败不阻塞业务；不外发消息。 |
| E工作台 | 实时角色下的审核预览/拟采纳内容/质量评分、反馈处理、账号/邀请/管理员、公告、统计与账号活动、成绩批次准备/完整diff/逐项确认/专属认证/应用/回滚/恢复。写由服务端独立lab门禁及原600秒/300秒认证、CAS/basis/digest/审计约束。页面不授予角色。 |

业务调用按固定OpenAPI白名单与运行时组件availability；角色/权限最终由服务端判定。写失败不确定时记录原key，阻止同路径换key盲重传，先查询原操作；邀请码明文不进恢复缓存。账号切换/失效清发布视图、权限和私有临时图，保留按actor隔离的草稿。没有把网站调试台/任意转发/工作簿放进小程序。

## 本机隔离环境与证据

新建lab `.score-version-sandboxes/808480ed2a05820efdcbb815`，guest `.mini-session-sandboxes/c3fdbdc00f62342a624b6c92`，account `.mini-account-sandboxes/ab52697223553e8fb27af683`，本机8052。未启停或改库8033/8043/8044/8045/8046/8051。原8052观察PID80336仅当时记录，后续操作前必须再核对。

创建使用网站mini_local的 `--accounts --full-mirror`，五份运行JSON按既有接收SHA显式导入，仍4504/693未冻结。本地仅fixture微信验证/file邮件，测试账号明确新注册；file outbox验证码与随机密码只在测试进程内存，不写本交接或回执。两份fixture代码均已使用：code1/key `mini-mirror-client-20261103-01`，code2/key `mini-mirror-http-other-20261103-01`；过期不能换key续用，须新建独立lab。8052不是手机可达或登记HTTPS地址。

证据目录 `offline-evaluation/miniprogram-full-mirror-20261103-01/`：

- `intake.json`、`build-sources.json`：固定来源、生成SHA和网站原dirty文件保全基线；最终preservation另记。
- `http-client-report.json`：真实本机HTTP，实际运行本轮账号/车库/业务client；A注册验证/空云库/显式导入/Global-CN独立/双会话冲突，B公开OC表及原子快照，C multipart证据/私有下载/提交，D回复及独立游标，E异owner审核/评分/专属认证/准备→应用→回滚和一次性邀请/普通账号拒绝，七组通过。这里wx由Node适配，不冒称微信uploadFile。后续新增的未知结果阻断/不丢新草稿等改动另由客户端定向测试覆盖，不冒称整套HTTP再次重跑。
- `devtools-connected/devtools-mirror-report.json`：真实开发者工具wx.request和原生页面，七组通过、exceptions空、fixture游客记录恢复。覆盖原生注册/验证/登录、null不导入、国际OC保存与CN隔离、成绩表/投稿/消息页面、普通账号直接进入审核队列的拒绝。界面输入和按钮操作与部分Page handler调用混合，不冒称全部手点或真机。`devtools-final/`追加再次七组通过，并目视检查account/coverage/submissions/home截图，修复禁用白底和控件溢出；之后的最后控件宽度/匿名传输/并发key绑定修正由定向测试覆盖，没有冒称再跑一遍全部工具流程。
- `client-tests.log`：本轮最终78项客户端测试通过；覆盖双token/actor、迟到请求、白名单/权限、key恢复、ProfileStore分服/null/冲突、丢失响应保留后续编辑、正式presenter与旧冻结oracle多组合一致，以及页面事件接线/manifest、生成key期间切账号不发送旧写入、旧退出不能清新会话、切服后旧保存不能发布到新视图。没有跑网站全量、生产或Linux测试。

测试过程失败保留：访客调用/contract被401后改为账号读取（游客直接请求固定公开端点并处理503）；WXML按XML转义被编译器拒绝后恢复WXML语法；JSON require改CommonJS；新增页面缺page.json导致未注册后补齐；旧SDK Page.callMethod/页面元数据不稳定，夹具改为等待当前路由/真实DOM，必要时通过Page handler驱动。连续重载一度429，按原限额退避，没有放宽校验。重开项目并单独重建该项目compile缓存，未清storage/auth/session/file/network或all缓存。失败目录不算通过。

追加公开读取 `anonymous-http-final.json`：最新匿名分支不使用访客凭据，真实HTTP读取CN83行/48列（1144497字节）、Global OC44行、贡献榜和公告成功。最后补充工具截图尝试曾超时，未当作通过；当前主页已另行截图确认小按钮及主入口，失败不覆盖之前已通过记录。

## 确认的契约/运行差异

1. 运行时GET /contract实际要求账号Bearer；使用访客会返回ACCOUNT_SESSION_REQUIRED。客户端已按真实行为处理，公开成绩表/榜/公告无需先取得该私有契约。
2. E文档写账号列表20项，固定backend/community.py实际LIMIT 50，响应没有page_size。客户端按首组返回长度确定步长，保留原server offset；建议网站后续把文档/机器响应统一。不改共享后端来凑契约。

## 尚不能宣称完成的验收

接口接线和页面实现不等于全网站逐像素/逐角色验收。E管理原生页面尚未在真实开发者工具以admin/superadmin逐项点验；HTTP高权限流程只在本轮新lab执行。其他表单、边界/复杂数据、弱网/取消/存储满、降级/过期、完整主题与390px各页视觉仍需进一步逐项验收，不以几个截图覆盖所有组合。

真实微信身份、真实邮件、合法TLS域名、iOS/Android手机相册及前后台、所需UGC实际安全机制、Linux/systemd/Nginx/生产迁移均未完成。图片格式/OCR/人工成绩审批不是内容安全审核。本轮没有上传体验版、提审、发布、部署、正式迁移、构正式包、推送/合并或外发公告/邮件/通知；正式构包仍需维护侧新冻结及批准范围。


## 交付时当前可查看环境

测试8052的fixture临近一小时到期后，另外新建了空白本地预览环境，原8052及全部测试库保留：`http://127.0.0.1:8055/`，lab `.score-version-sandboxes/517152525e7b8497fc3581e5`。创建回执 `local-view-lab.json`；当前ignored native-config已显式指向8055，fixture-code-1/key `mini-mirror-user-view-20261103-01`。未登录账号，旧游客地图/车库保留，账号库为空且为file邮件。

`local-view-ready.json`证明最终源码在真实开发者工具使用的新访客identity与8055本机返回一致、online=true、actor=null；`local-view-home.png`已截图。它是新环境接通证明，不把8052的完整业务测试冒称在8055重复执行。新会话仍按协议一小时到期，不延长TTL、不复用过期code；下一次本地联调应按回执新建隔离环境，或由用户安全配置真实平台验证。当前工具无需重新安装或修改设置。


后续状态：管理原生逐项与各页外观验收已在 `MINIPROGRAM_LOCAL_ACCEPTANCE_20261103.md` 补齐。本文件保留上轮真实边界，不把旧证据重写成新阶段结果。
