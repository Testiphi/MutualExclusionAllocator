# 微信绑定与解绑 · 客户端联调约定

当前仅有小程序客户端与夹具。正式和现有隔离连接没有开启绑定能力，也没有放行绑定路由。快捷登录留到绑定和解绑验收之后。

- 未来独立隔离连接必须显式设置客户端 wechatBinding，并由已登录账号会话返回 features.wechat_binding_v1 = { enabled: true, bound: boolean }。个人中心只有同时满足两个条件才显示入口。现有会话关联字段仍描述临时会话。
- POST /api/mini/account/v1/auth/wechat-bind 使用账号 Bearer、X-Account-ID 和 JSON { schema: 1, request_key, password, code }。code 仅在用户确认后通过一次新的 wx.login 获取。wechat-unbind 使用相同请求格式但不含 code。两个操作均由服务端验证当前账号密码、有效账号会话及实时账号状态，绑定时再校验新的微信身份。错密码用 403，401 用于账号会话失效。
- 成功响应为 { actor_id, bound }，不得替换当前账号会话。绑定与解绑使用同一原用户 ID。结果未知只 GET /api/mini/account/v1/operations/{key}?action=wechat-bind 或 wechat-unbind，并使用同一账号认证，不重传密码或 code。查询不到不得重发。若服务端能证明原操作已经结束且失败，错误响应标记 operation_resolved=true。
- 服务端联调还需证明唯一绑定及并发互斥、重复操作、凭证过期、禁用账号、解绑后邮箱登录。以已有账号的非空双服车库检查绑定前、绑定后与解绑后的账号 ID、revision 及记录内容。

服务端仅接受全新隔离状态。用 mini_account_service 的 provision --wechat-binding 显式建表并固定快照，启动配置设 wechat_binding=true、enabled=true、cloud_writes=false，registration 关闭。启动不会迁移旧库。预检确认独立账号库、原生库、访客库和只读双服快照归属同一候选。绑定仅接受与本次微信访客相同的新平台身份。数据库只保留带密钥的身份摘要，每个账号和每个微信身份各自唯一。

真机窗口前，在同一个新隔离库预先准备已验证测试账号及两服非空车库，再切到绑定验收配置。现场先读取两服的用户 ID、内容与 revision，绑定后复读，解绑后用原邮箱分别重新登录并复读。密码与微信凭证只在各自受控端使用。正式服务不启用绑定。公网测试路由需要精确放行绑定、解绑、相应原操作查询，等 Nginx reload 后读到固定交付再验收，结束后回退。旧测试状态与正式账号库不作候选输入。
