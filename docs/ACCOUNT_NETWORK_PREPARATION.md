# 账号联网客户端准备记录

接手089f4a8，用户要求继续下一步。独立工作树feature/miniprogram-v1干净接入；本轮只改小程序原生客户端、测试/工具/文档，不改网站公共源码、维护数据、账号库或云配置。账号A与Global云车库原契约/固定模块已核对，无新的服务端启用回交；实际无认证GET账号session为404。

## 修复内容

1. 原createTransport会在所有401清token；访客Bearer用于A密码入口时，CREDENTIALS_REJECTED也会把父访客凭据清掉。现在guest-account transport保留业务401的父token，native_api仅对固定父会话错误码失效处理；RPA私有transport保留原401清账号逻辑。测试覆盖先密码错、再正确请求仍有原访客Bearer，以及真正父会话过期清身份。
2. AccountClient登录成功在install前校验原generation、角色及整数有效期；平台模式额外要求schema/token_type、session_only/persistent_binding=false、guest_identity和父TTL绑定，拒绝过期/跨父身份会话。未把测试fixture宽松性扩展到真实平台。
3. 未知auth结果将key/action保留client内存，不保存password/token/email正文。新auth被挡住并指向原操作；恢复须匹配原动作/编号，成功才解除。账号页切表单保留pending，重开页面可读取client内存pending，不因换模式而丢号盲发。
4. 身份清理同时清组件缓存；contract迟到响应作generation检查，旧flight结束不能覆盖新flight。固定请求字段拒绝schema/request_key/角色等额外覆盖。

## 独立工程

路径：`E:\hzz\work\MutualExclusionAllocator\offline-evaluation\mini-account-network-prep-01\account-check`。

`node tools/prepare_account_probe.cjs <外层全新目录> miniapp/account.profile.example.json` 默认生成关闭工程。配置只允许非秘密声明字段，不能填密码/令牌/AppSecret；account.profile.local.json已忽略Git。启用要求明确隔离和账号路由声明，这些声明本身不算验收。

探针委托同一AccountClient/CloudProfile；profile_store从198999a原Git对象、feature_contract从8da1609固定对象生成，保留SHA。可用路由限定访客session与A登录/再认证/session/profile/原操作查询，拒绝图片上传/下载、注册/邮件、B–E。默认cloudWrites=false，保存按钮即使被调用也在发PUT前拒绝。测试草稿有独立racepick.account.probe.<planId>前缀；登录/GET不导入，不把云端null混同合法空车库。启用后的测试页可显式暂存空示例、单独保存、核对/解决冲突；它是开发者验收工具，不替代已镜像的主页外观与真实车型/星级/OC功能验收。

## 验证

- 11个客户端测试文件共140项通过，覆盖原生/离线/OCR/呈现旧回归，新增未知auth恢复、字段覆盖拒绝、失效/跨父会话响应拒绝、表单pending保留、密码401父身份保留、A-only登录与两服读取不写、草稿隔离与默认保存禁用、本地模拟明确空Global保存不影响CN。
- 初次回归130/131，失败来自旧platform mock登录响应缺schema/token_type/association；按已固定契约补齐mock，而非放松平台校验。后续新增测试后140/140，旧失败日志保留。
- 官方CLI/SDK在独立端口9421编译关闭account-probe；enabled=false、probeCreated=false、密码空、异常0，urlCheck=true/无private override，SDK3.17.6。没有触发wx.login或账号/车库请求；截图已查看。与一次独立未认证HTTP404门禁检查分开记录。
- 证据位于外层mini-account-network-prep-01：client-tests-initial.log、client-tests.log、unauthenticated-account-gate.json、preflight-final/disabled-result.json与截图、生成与提交回执。实际HTTP观察UTC2026-11-04T16:05:35.927127Z，不虚构服务器就绪或后续状态。

未执行真实注册/邮件/账号登录/云保存、管理员操作、图片调用或手机账号验收。没有新收费、服务器部署/正式迁移、推送/合并或发布。旧手机OCR已通过，不重复要求测试；开发者工具只关闭本轮已完成的临时phone-02窗口，没有清存储或改其工程文件。

下一项依赖已整理到 [网站侧交接清单](HANDOFF_ACCOUNT_NETWORK.md)。用户现在只需转交清单协调固定账号入口，暂不需要扫码本关闭工程或发送密码/密钥；入口回交后继续真实SDK，再给手机步骤。
