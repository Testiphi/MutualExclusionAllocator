# E：管理/超管工作台与隔离写入

共用契约、固定OpenAPI及A账号协议构成本批规范。路径相对账号前缀。所有E读要求服务器实时角色；所有写除原对象规则外，还要求全功能独立lab、最近600秒密码认证和幂等头。生产恒拒绝本批业务写，不能因镜像页面或拿到role=superadmin就真实发布。

| 权限/路径 | 请求模型/行为 | 响应 |
|---|---|---|
| admin/super POST /admin/submissions/{sid}/preview | revision、entry:Score | {candidate,basis,comparison}等原校验预览 |
| 同上 POST .../review | revision、action=accept/needs_info/ignore/reopen、entry(nullable)、reason≤2000、basis、slower_confirmed、review_score或quality | {revision,status}；禁止审核本人合资格投稿，变慢确认/基线漂移仍拒绝 |
| 同上 POST /admin/contributions/{sid}/rating | revision、quality | 质量调整结果及原审计 |
| super GET /admin/feedback[/{tid}]、/summary | 列表status/offset/q | 列表30项/total，详情加owner_email/nickname，summary pending/counts |
| super POST /admin/feedback/{tid}/handle | request_key/revision/message/status | {id,revision,status}；原私有事件/通知 |
| super GET /admin/accounts | q、role、verified、status、offset、activity、order；枚举见schema | {total,items}，20项分页，服务端过滤角色/状态/活动 |
| super POST /admin/accounts/{uid}/control | action=disable/restore/logout、revision≥0、reason1..200 | {revision,disabled}；保护主超管，停用/全部退出撤销会话 |
| super GET .../{uid}/events | 原查询 | 访问/处理审计项目 |
| super GET/POST /admin/invitations | 创建email、expires_hours1..168默认72 | 列表items；创建{id,code,email,expires_at,revision}，code只返回一次 |
| super POST /admin/invitations/{iid}/revoke | revision≥1 | 原撤销确认；不能复用/跨邮箱 |
| super GET /admin/members；POST .../{uid}/revoke | 收回reason1..200 | items或确认；主超管不可降级，撤销目标会话 |
| super GET/POST /admin/announcements | 创建title1..120/body1..6000/release_label≤80 | items或{id,revision}，初始draft |
| super PUT /admin/announcements/{aid} | 同内容+revision≥1 | {revision} |
| super POST .../{aid}/state | revision/action=publish/withdraw | {revision,state}，保留首次published_at及审计 |
| super GET /admin/usage | start/end日期、server=all/cn/global | 原概览、时间序列、registrations；Asia/Shanghai |
| super GET /admin/usage/accounts | offset≥0/q≤100 | {items,total,timezone}，50项 |
| super GET .../{uid} | 日期/服别/offset | {first_seen,last_visit,last_interaction,summary,items,total,offset,page_size:10,start,end,server,timezone} |

quality={completeness严格0..3,evidence严格0..4,value严格0..3,reason1..1000}，value=0时总质量须0；不是“成绩真伪/内容安全自动审核”。积分/权益、重复来源、评分/采用奖励、self-review禁令均走原事务，不从客户端传入points/level。

## 成绩批次与再认证

GET `/admin/score-versions?server=cn|global` 返回server/current/production/write_enabled/items（可应用已采纳投稿）/batches；GET `/admin/score-versions/{bid}?server=...` 返回原manifest/state/stale_reasons。Global和CN写回开关分别遵守现场值，关闭时409，不因Native身份打开。

POST `/admin/score-versions/reauth?server=...`：{password1..128}，返回{expires_at}，**300秒**有效、锚绑定。A再认证轮换token时旧锚失效，应先A再认证再调用此处。服务端原生E最近认证600秒不能代替本规则。

POST `/admin/score-versions?server=...`：{request_key,items:[{id,revision}]}1..50，同幂等头；返回{id,actor,created_at,base,target,result,engine,extra,events,digest,state,stale_reasons}。result包含每项变化、accepted_hash、普通镜像/变慢等确认信息，客户端不得自行算digest或删除某项确认。

POST `/{bid}/execute`：{digest,effects_confirmed:true,items:[{submission_id,confirmed:true,slower_confirmed,slower_reason}]}。逐项必须与服务器待变更集合相同，变慢再次确认并填原因，结果applied。源新版本/工具/内容/basis变化拒绝409，先重预览；检查写回开关/会话/角色，成套备份验证后才切本环境活动指针，不覆盖维护JSON/工作簿。

POST `/{bid}/rollback` 或 `/recover`：{reason1..2000}，仍需原300秒再认证/兼容和审计。返回原manifest/state，保留新增，不“整库恢复”。本轮自动化实际执行的是新建本地lab的接受→预览→准备→应用→回滚，不能写成正式成绩发布或真实库验收。

## 幂等、秘密与拒绝

读/预览/审核/写回所需准确body/query枚举均在机器schema，禁止客户端从网页地址猜字段。403可来自角色、本人审核、对象状态、源再认证或新增STEP_UP_REQUIRED；401撤销/切账号；409包含revision/basis/digest/旧工具/关闭写回等。副作用不确定返回保留状态，不重新执行。邀请码code不落原生恢复缓存/日志，响应丢失返回409 ONE_TIME_RESULT_UNRECOVERABLE，仅给id；先看列表后明确撤销/新建。

权限矩阵实际覆盖匿名/访客/普通/管理员/超管；私有GET/图片也鉴权，源事务内再次检查会话。账号/反馈/公告/统计的superadmin约束不因“/admin”统一降低成admin；审核/评分可以admin。普通账号不能伪造X-Account-ID或role；降级/停用的旧token不能读取旧管理缓存。没有生产动作、外发邮件/通知或平台后台操作。
