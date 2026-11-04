# 小程序真实微信访客与快照：网站／运维侧回交（2026-11-04）

服务器侧入口和HTTPS门禁已就绪，真实微信验证仅已配置，尚未通过真实wx.login/code交换、开发者工具SDK或真机验证。服务端测试不替代客户端验收。本文件不授权开启OCR、账号/B–E、上传/提审或发布。

## 固定入口与来源

- HTTPS origin：`https://mini-test.racepick.cn`（无API路径、无自定义端口）。
- 交付ID：`9d856fba3f6b825b255bc17e`；源码：`0b97dae9e1003c1bc2c4c5b7a189b81cb4002112`，本机feature/map-layout-parser已固定，当前尚未推送/合入main。
- 整包3243638字节，SHA256 `a48875c79258d5c662847879afbd74603baf08ad6ff238c78dd2179b53c856e7`。
- 仅使用已批准冻结b57d97a8的五份4516/694运行JSON，不复制正式账号库/score-state/旧测试库。Global dataset=`9b83ddd062a4d4b0c15d51dc0eed323aabb8e599e3e9544bc91714b70a7a4259`。
- 测试快照版本：CN `593ecc7222ceea5856b2f576b4f5bca8`；Global `e29f52e7f81c3e337985bf05dedb7e88`。这些是独立测试版本，不是正式成绩活动指针。
- 会话identity由服务端按每次访客会话生成，客户端须比较session与snapshot的identity；不预填、不索取OpenID明文。

## 两个接口与客户端验收

1. `POST /api/mini/v1/session`：JSON恰好code/client_schema=1/request_key。code来自真实wx.login；同次交换响应不确定时保留原code/key，不盲目新建key或切换身份重传。token只留内存，不进入存储/日志/截图/回传。
2. `GET /api/mini/v1/snapshot?server=cn|global`：Authorization Bearer访客token；不使用RacePick账号或网页Cookie/Origin。校验schema/server/identity、准确文件白名单、text重新UTF-8编码后的SHA与bytes，再验证Global三件套绑定。
3. 两服capabilities.map_recognition=false，catalog_version=null；image_policy=disabled。账号、B–E及OCR路由404；不上传图片，不调用账号接口，不写本机车库。
4. 固定协议仍参考MINI_API_CONTRACT_20261102.md和MINI_DEPLOYMENT_20261102.md；第一阶段服务外层进一步仅开放上述两个接口，包括DELETE session等后续路径也不开放。
5. 由小程序侧生成**独立网络检查工程**，保留原离线工程和车库，先开发者工具，再提供用户手动预览扫码真机步骤；不要自动上传体验版或提审。

## 需要用户做的下一步

在微信公众平台相应小程序的开发管理→开发设置→服务器域名中，只新增request合法域名 `https://mini-test.racepick.cn`，保留已有条目。当前未得到完成确认；仅配置服务器或CA证书不代表微信登记/SDK校验已通过。开发者工具保持合法域名、TLS与HTTPS证书校验。uploadFile/downloadFile域名留待后续各阶段，不现在开放。

## 运行与隔离证据

- 服务racepick-mini-test，独立UID996/GID987，真实release实际cwd匹配，仅监听127.0.0.1:8011。真实微信私有配置已加载；AppID/AppSecret均不在本文、源码或交付内，平台凭据是否正确仍待真实code验证。
- state=`/var/lib/racepick-mini-test/guests`，目录700/文件600；新schema1，最后观测sessions=0/codes=0/uploads=0。服务挂载视图中正式账号库及配置文件不可见，不引用正式业务状态。
- 仅该状态目录可写，ProtectSystem=strict/ProtectHome=yes；High96MiB/Max128MiB/Swap0/CPU25%/Tasks32。采样MemoryCurrent36155392、MemoryPeak36626432字节、TasksCurrent1，仅短期未认证流量，不是长期容量证明。
- Nginx精确两个路径，独立5r/s burst10、4KiB请求体限制、可信回环/Host/HTTPS/X-Real-IP边界；拒绝Origin/Cookie，无CORS允许头，原生JSON no-store。
- 实际域名TLSv1.3、主机名和系统CA链验证通过，呈现证书与签发叶证书一致；DER SHA256=`3c7ab8dc29c8f75761cdcaa50ccb5f7858619c3f3a0b365a777e9baec0c6952e`，截至2027-02-01T15:03:46Z有效。尚未证明微信SDK/手机的TLS验证结果。
- 公网未登录双服快照401，空session正文400、Origin/Cookie403，账号/B–E/OCR404，4097字节session正文413。未向真实平台提交任何有效登录code。
- 原网站a933及双服正式活动版本保持，原OCR ready、账号服务和备份timer active；Nginx原配置与两份证书基线26项保持。新服务当前active/running，但开机自启disabled，不能假设重启后自动恢复。

## 快照原字节核验表

| 文件 | 字节数 | SHA256 |
|---|---:|---|
| cars.global.json | 29852 | `6d35da66c9c0d2d7335b3e80d6a7351bbc494911a5b1d8dab0a0c2137cbc9759` |
| cars.json | 83653 | `ea42daedfdb73a4963e2e70c6cdf91deb29ae6bec5143b697e50d8c877961b17` |
| gauntlet_data.global.json | 133918 | `79958b507b814fb0823e03aa8f97843fafe9b61a558c428336a4879587a33bd2` |
| gauntlet_data.json | 225341 | `2e8bf6ba763a64f24cd1e93be0afbaca8c77e24efcb9a96812952de800b018b6` |
| global-data-manifest.json | 1866 | `7e38469bc6bd6de5498bc1e38c16898c0a34eddb86ead72d610e0e1883e6dbe6` |

## 尚待核验与后续边界

真实wx.login、两服授权快照、合法域名登记、开发者工具与真机均待小程序侧验证。开机自启、认证/并发长时容量，以及该新证书实际自动续期与续期后Nginx加载仍待后续安排；现有snap.certbot.renew.timer在00:11观测NEXT11月4日06:00，这只是当时计划，不记为未来执行成功。没有新增监控、定时清理或业务备份任务；独立访客状态未加入正式成套备份。

后续顺序仍为访客与快照→OCR→RacePick账号/云车库。OCR阶段先明确图片内容安全和隐私策略、共享队列/执行容量，不把图片策略改成private_unmoderated试跑，不新增第二套模型/配额。账号/B–E保持关闭，另行授权和隔离测试。

执行和证据详见[激活回执](MINI_GUEST_STAGE1_ACTIVATION_RECEIPT_20261104.json)，旧准备/证书阶段回执保留为历史。
