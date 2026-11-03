# 原生B–E共用传输、身份与运行契约

2026-11-03。用户恢复剩余批次开发。本轮交付B成绩表、C投稿/贡献、D反馈/消息、E工作台，以及独立主页presenter/主题导出。固定提交/逐文件SHA见本轮交付回执；不是生产配置、审核、成绩写回、部署或小程序发布授权。

## 路径及机器协议

新业务使用已有账号命名空间 `/api/mini/account/v1`；下列分批文档路径均相对此前缀。网页原 `/api/...` Cookie/Origin/CSRF/raw门禁不变。原 `/api/mini/v1` 访客/快照/OCR及A批双服云车库/账号契约兼容，不改变既有五共享模块。字段、必填、长度、枚举、query/body/path位置、类型及默认值的机器定义固定在 `MINI_FEATURES_OPENAPI_20261103.json`；运行时GET `/contract`可读取当前服务器已安装组件的定义。不要把不存在/未启用组件的schema当作可调用能力。

实现是逐条白名单的原网页处理函数委托：保留原Pydantic模型、服务端实时actor、对象所有权、revision/版本、权益、审计和事务。没有客户端可指定的转发地址/角色，也不转发客户端Cookie/Origin。服务器私有请求上下文只传本app验证过的账号会话锚、actor及经原服务校验的X-Usage-Token。

## 角色、读取与缓存

- public：B覆盖查询、C公开榜、D已发布公告、统计初始化/采集支持无令牌/访客；账号token可获得其实际权益，须X-Account-ID。匿名/访客不会获得user_id/管理权。
- account：其余私有功能须A批rpa1账号Bearer与X-Account-ID；访客token不能代替登录。401清旧身份/权限缓存，保留按actor/server隔离的草稿，不能自动换身份提交。
- reviewer：投稿审核/评分要求admin或superadmin；仍受“不能审核本人合资格投稿”、草稿私有等原对象权限。
- superadmin：账号/邀请码/公告/全部反馈/统计/成绩版本工作台。客户端声明role无效。

全部响应no-store，无跨域放行。读取图片用认证下载转本机临时文件，不把私有证据URL公开。source_snapshot仅用于B原子活动版本绑定；其他对象以自身revision/basis/digest/read_cursor验证。账号切换、父访客失效、停用/降级/撤销都重新校验，不能靠隐藏按钮代替服务器拒绝。

## 写入范围与幂等

本次B–E**业务写默认关闭**，仅CLI显式创建的新全功能隔离lab可开；生产source.production恒拒绝。A云车库和已固定OCR不受此新开关改变。隔离可用stub微信，也可由用户安全配置真实微信验证，但真实身份不等于生产写授权。没有JSON配置/客户端字段能打开此隔离写开关。

除只读POST `/coverage/view`、`/usage/session`外，POST/PUT/DELETE必须 `Idempotency-Key:<16..80 ASCII字母数字_横线>`。原模型有request_key时它必须与头一致，不一致409 REQUEST_KEY_MISMATCH。每次用户明确的新操作新key；响应丢失保持key、路径、query及正文。JSON按原请求字节HMAC绑定；multipart证据按实际图片字节及revision绑定，boundary/文件名变化不会重复创建。key不能换动作/对象/服别/正文。

GET `/feature-operations/{key}`：当前账号会话+X-Account-ID，无query，返回保留的原HTTP状态/响应，不重新执行写入。作用域是账号会话，重新登录/轮换后不承诺找回旧传输记录；原投稿/反馈模型自带的owner/request_key幂等继续生效。404不证明未执行；409 OPERATION_UNCERTAIN表示进行中或跨库结果不确定，先查询对象/版本，不自动换key重传。独立私有恢复记录保留策略同A批24小时/会话有效边界，不含密码/证据原文/一次性邀请码明文。

邀请码创建只返回一次code；缓存中只保存id和409 ONE_TIME_RESULT_UNRECOVERABLE。丢失响应先查看邀请列表，必要时明确撤销再新建，不重复执行同key。所有源业务审计保留，另记原生传输确认的action/actor/time，不记录请求正文或秘密。

E写还要求最近600秒密码认证（A登录/再认证为服务器时间），过期403 STEP_UP_REQUIRED。成绩发布另需原业务的**300秒、会话锚绑定**超管再认证，原digest/逐条确认/变慢理由/备份/恢复/写回开关全部保留。A再认证轮换token后原成绩再认证不继承，应先A再认证、再成绩专属再认证。

## 时间、大小、错误

时间戳Unix秒，时长/Retry-After秒；日期/月份及统计时区Asia/Shanghai。客户端规范为retryAfterMs。JSON一般≤65536字节，证据JSON≤3000000，统计≤8192；multipart证据文件≤2MiB、封装额外≤64KiB。读取20秒截止。未知/重复query拒绝，框架校验错误只给loc/type，不回显输入值。

错误统一schema_version/code/detail；FIELD_VALIDATION(422)另有fields。常见：401账号失效/访客无私有权；403 NATIVE_ONLY/REVIEWER_REQUIRED/SUPERADMIN_REQUIRED/STEP_UP_REQUIRED或BUSINESS_REJECTED；404对象不存在/不属于当前身份；409 revision、basis/digest、幂等冲突/结果不确定；413正文/文件过大；415类型不符；422字段/业务范围；429限流，503组件未启用/隔离写关闭/服务不可用。原业务拒绝BUSINESS_REJECTED保留源detail，但不转成成功或替用户重试。429通常带60秒最短等待，日预算不承诺60秒恢复；原生请求总IP预算仍120/分钟。Nginx HTML429/413按HTTP状态处理，不能只解析JSON。

## 独立运行与配套

```powershell
python -B -X utf8 -m backend.mini_local create --accounts --full-mirror --source . --receipt ..\offline-evaluation\data-sync-20261102-01\sync-receipt.json --model-config ..\.score-version-sandboxes\9f326b2976b6637b90f07be5\config.json
python -B -X utf8 -m backend.mini_local serve --lab <上述新lab> --port <已核验空闲端口> --fixture-auth
```

只创建新lab/访客/账号/反馈/统计状态；不复用旧库或正式账号。真实平台模式可换`--mini-config <私有文件>`，仍须匹配新lab记录中的guest/account目录，--full-mirror标记及独立lab校验不能由HTTP伪造。AppSecret不发聊天/客户端/日志。模型沿用唯一既有worker/队列，证据图片走原独立业务存储，不复制OCR服务。

新业务无需新正式业务schema；使用既有已迁移组件。新隔离库可初始化，不自动给正式库补组件/迁移。原生业务正文采用现有Nginx默认3m/业务5r/s桶；新证据multipart最大2MiB+64KiB无需放大全局上限；旧OCR8MiB/独立桶保持。TLS/可信代理/原服务沙箱和资源值不改。发布白名单新增桥接、presenter/主题及契约；不纳入fixture启动器/测试/照片/账号库/密钥/维护工作簿。构正式包仍需新维护冻结及批准源码/功能，独立干净检出。

图片/UGC安全检测仍未接入，格式/尺寸/OCR/成绩审批均不当作安全审核。本轮只操作显式隔离数据，不向审核供应商送图、不发邮件/通知、不开户付费。真实平台、TLS域名、iOS/Android及生产Linux/Nginx验收另记，不以本机fixture代替。
