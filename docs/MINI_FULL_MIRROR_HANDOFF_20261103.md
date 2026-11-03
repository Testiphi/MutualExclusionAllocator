# B–E及主页presenter固定回交

2026-11-03，用户明确恢复剩余契约/源码开发。本轮基线a38faaf4c7fa05f853b89ae2db31708ec2f8b52d，网站feature/map-layout-parser归口；不修改小程序树、不跨对话派工。最终源码及逐文件Git blob/SHA见外层 `offline-evaluation/mini-mirror-b-e-20261103-01/commit-receipt.json`。各批共用同一固定源码提交，但契约/机器模型按B/C/D/E单独交付，接收方不必猜字段或合并未提交修改。

## 分批材料

| 批次 | 固定文档/产物 | 已实现 |
|---|---|---|
| 共用 | MINI_FEATURES_COMMON_20261103.md、MINI_FEATURES_OPENAPI_20261103.json | 路径/完整原请求模型/角色/限制/错误/时间/恢复/运行；59个显式白名单端点 |
| B | MINI_BATCH_B_20261103.md | 两服覆盖表/星级/SC/OC、服务端权益、48列分页、隐藏/无数据区别、原子source_snapshot、选图/直达target。网页补OC筛选，默认非OC兼容旧客户端 |
| C | MINI_BATCH_C_20261103.md | 投稿/目录/草稿/提交/补充/私有证据JSON和原生单文件multipart、认证下载/停用、幂等、榜单/月榜/个人明细/昵称匿名 |
| D | MINI_BATCH_D_20261103.md | 私人反馈/回复、公告/偏好/忽略、独立已读/未读、原生内部统计token/events；无外发通知 |
| E | MINI_BATCH_E_20261103.md | 实时角色/对象级权限下的审核评分、账号/邀请码/公告/反馈/统计读写、成绩预览/准备/再认证/逐条确认/应用/回滚/恢复；写仅新隔离lab |
| presenter | HOME_PRESENTER_CONTRACT_20261103.md、home_presenter.js、home_theme.json | DOM无关筛选/车序/别名/初始档/副标题/单图前三/完整方案摘要；原CSS设计值和条件导出、生成漂移检查 |

请求schema来自相同网站原函数的Pydantic签名，错误不回显输入，响应/分页/权限语义在各批文件逐项列明。线上路由是否安装看组件开关和运行时contract availability，不能把契约ready理解为生产写已启用或页面已验收。原本地data-previews/writeback-lab调试台不打入小程序；正式变更预览/应用由本批投稿preview及版本化批次prepare完整diff承接，不转发任意开发工具地址或维护工作簿。

原五模块allocator/race_scores/app_state/profile_store/selection_core仍198999a原Git blob，算法/车库/成绩/地图规则不变。新增presenter及主题取代客户端临时原文提取端口，接收方把它们及依赖纳入固定构建清单，记录来源/生成SHA；保留旧提取器/证据，正式迁移后停止维护第二份呈现逻辑。CSS文件本身不修改，仍自然宽度flex车签。网页对应五呈现函数及方案摘要已委托新模块。

## 身份、写入和安全

沿用A `/api/mini/account/v1` rpa1账号Bearer/X-Account-ID，旧 `/api/mini/v1` 访客/快照/OCR兼容。public覆盖/榜/公告可匿名或访客，私有账号数据必须真实RacePick会话；Cookie/Origin不能在原生桥接成身份。每个对象仍走原网页处理函数的所有权/角色/revision/basis/写回开关/审计，不给普通账号“隐藏按钮即授权”。

本批写仅CLI显式新建的全功能隔离lab可启用，生产source.production恒拒绝；JSON配置/客户端字段不能开写。可在这个隔离lab安全配置真实微信验证，但真实身份不意味着生产权限。E还需600秒近期认证，成绩操作另需原300秒会话锚再认证；一次性邀请码只返回一次、不存原生恢复缓存明文。同key恢复不重新写，跨对象/服别/正文拒绝，异常结果不确定不假装未执行。

证据multipart路径只收image+query revision，文件≤2MiB/封装额外64KiB；转交原图片格式/尺寸/权限/重编码/数量规则，URL改为原生私有认证下载。OCR仍是原8MiB任务协议，不能混用；新桥不另开模型/队列/配额。证据停用和历史保留按原业务，不冒充1小时物理删除。OCR/格式/成绩审批不是安全审核；未接入内容审核，未向第三方送图/开户/付费。

## 本地运行与验证

新独立服务 `http://127.0.0.1:8051/`，原生基址同源 `/api/mini/account/v1`；lab/私有状态/当时进程信息在本轮local-lab.json、process*.json。原8033/8043/8044/8045/8046等服务未启停/改库。当前为fixture微信验证、file模拟邮箱，测试密码/token仅内存，不随材料/源码发送。接收方可明确注册自己的隔离账号，读取该lab的file outbox完成验证；管理角色仅对新lab用原roles工具按用户测试需求设定，不能指向正式库。真实平台需要用户安全配置私有AppSecret、隔离后端/TLS/合法域名及实际安全策略。

复现命令见共用契约：create增加`--accounts --full-mirror`，serve先查空闲端口再`--fixture-auth`或私有`--mini-config`。原生接口默认关闭/已有A云车库语义保持；普通A环境未开某业务组件返回503，不自动给正式库初始化组件。业务写开关只作用于本批，不能替代A或原OCR配置。

已完成：

- Python全量387项执行/386通过/1项平台相关跳过，前端134项通过；随后OpenAPI敏感字段/统计头元数据及隔离写保护增补，26项原生/发布定向通过，未冒称再跑全量。日志python-full.log/frontend-full.log/contract-final-check.log。
- B访客/普通/admin/superadmin逐角色两服对照网页返回一致；OC/普通目标不混、隐藏与缺成绩区分、绑定原子快照。C同key建稿、私有图/跨owner拒绝、wx式multipart边界变化不重复建图。D反馈/超管回复/独立未读cursor/统计身份token绑定与event.id去重。E禁止本人审核等源规则保持，非超管拒绝、默认写关闭/近期认证过期拒绝、一次性code不缓存，隔离接受→准备→应用→回滚通过。
- 真实HTTP8051再次跑通B公开OC表、C建稿提交、D私有反馈、E管理读/审核/准备/应用/回滚，全部只在新lab，证据http-mirror-flow.json。
- 独立已安装Chrome主页云车库重载/第二浏览器/原生同库/OC、390px/“新功能”及无pageerror通过；成绩表OC切换为普通通过。截图/记录见本轮global-browser.json、coverage-browser.json及PNG。
- presenter对冻结a38faaf页面函数与同快照405组输入组合对照，搜索/类/排序/副标题/单图参考/完整摘要一致；主题--check及CSS值/条件校验通过。参考夹具/生成工具不入运行白名单。

最后保全与五共享blob对照随回执，原30个dirty文件不提交/覆盖。4504/693仍未提交/未重新冻结，不夹完整维护732/工作簿/来源台账/账号库/测试图进入运行包。发布工具新增成套桥接/presenter/主题/契约依赖校验，继续读旧包；本轮没有构正式包。

## 接收方下一步与未验证项

小程序分支按分批契约接WXML/controller/request/media/storage/lifecycle和原生路由；私有图先认证下载到临时文件，通知仅实际展示后读cursor，账号/服别/角色变化清缓存。主页消费presenter，不复制规则，主题生成后对照原图，不改整齐网格。业务写默认只读，完整交互在新隔离lab验证；不可把SDK页面fixture算真实平台验收。

尚未验证：真实微信身份/手机相册/iOS与Android/TLS合法域名、所需UGC实际安全机制、Linux原生/systemd/Nginx及生产现场。当前统计沿用原服务Global仅home的范围，不伪造CN活动。没有操作微信后台/体验版上传/审核/发布/生产迁移/正式库/公告/清理或监控；源网页管理UI及API开发不授权真实审核/上线。固定提交和本文件交由用户协调回交，本对话不自行派工。
