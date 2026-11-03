# D：私人反馈、公告、独立已读与内部统计

依赖共用契约/固定OpenAPI；路径相对账号前缀。私有反馈只本人和超管，不是公共评论。没有外发通知/邮件调用授权或实现。

| 路径 | 请求 | 响应/分页 |
|---|---|---|
| GET /feedback/context | 账号，无query | app_version/privacy |
| POST /feedback | request_key同幂等头，category=bug/data/suggestion/other，title1..100，description1..6000，steps≤3000，expected/actual≤2000，source_page固定内部页面路径≤100 | {id,revision,status}；本人每日最多10个新反馈 |
| GET /feedback | status=all/pending/needs_info/resolved/closed/ignored，offset≥0，q≤100 | {items,total}，每页30，updated_at DESC,id |
| GET /feedback/{tid} | 账号 | 标题/正文/重现/预期实际/source_page/app_version/status/revision/created_at/updated_at；events为actor_role/message/from_status/to_status/time/revision，不向本人返回管理者邮箱 |
| POST /feedback/{tid}/reply | request_key、revision≥1、message1..4000 | {id,revision,status}；补充needs_info/resolved会回到pending |
| GET /announcements | 公开，offset≥0 | {total,items}，每页20，仅published，published_at DESC,id；item id/title/body/release_label/revision/published_at |
| GET /me/announcement-preferences | 账号 | {muted:bool,revision,ignored:[公告id]} |
| PUT 同路径 | {muted:bool,revision≥0} | revision |
| POST/DELETE /me/announcements/{aid}/dismiss | 账号，无业务正文时发送{} | 原业务确认响应；不修改公告公开状态 |
| GET /notifications | 账号 | {user_id,role,counts:{channel:count},items:{channel:[id]},feedback_pending:null或超管待处理数} |
| POST /notifications/read | {channel,item_id,event_id} | {read:true} |

准确枚举/字段默认值以机器schema为准。反馈GET详情不把owner_id或别人的信息回给普通用户；超管的管理详情在E批路径可附owner_email/owner_nickname。不同tid/账号/角色的拒绝由源业务检查。revision不符409保留输入重读，不能自动覆写。

通知渠道由源角色决定：普通账号看到本人的submissions/feedback，管理员增加review，超管有feedback_admin等实际渠道。GET/刷新/后台轮询不自动已读；仅用户实际展示对应项目后提交其服务器event_id/cursor。任意猜测/他人event_id拒绝，read只推进到更大事件，不倒退旧客户端游标。退出/降级清旧channel缓存；旧账号/旧角色响应不覆盖新状态。公告muted/ignored是用户偏好，不能客户端把草稿公告当published或改公告revision。

## 内部统计端口

POST `/usage/session`，公开只签名不写业务：JSON visitor_id/session_id均32位hex，返回{token,expires_in:1800,identity,timezone:Asia/Shanghai}。token仅内存；不是账号认证/权益凭据。账号actor由真实会话确定，不接受客户端user_id/role。

POST `/usage/events`，JSON events 1..20，携带X-Usage-Token及幂等头。每项id32位hex，kind=visit/active/feature，page=home/submissions/feedback/leaderboard，server=cn/global；feature/result/reason受源枚举及组合校验。visit需要reason=open/resume，active不带reason；功能事件只允许源白名单。返回{accepted:新增事件数}，原event.id重复不计两次。token过期/登录身份变化409，先重新初始化；不能把旧访客token用于新账号或代别人统计。

保留原统计范围：当前Global只有home事件，其他页面的Global统计拒绝422，不改成CN伪造来源；业务页面正常功能不依赖统计成功。活跃按服务器分钟去重，后台不发送伪活跃。统计写也只在显式全功能隔离lab开放；源反馈/投稿触发的是内部记录，不是邮件/推送/第三方通知。读写权限与时区/分页明细在E统计接口定义。
