# CN原生OCR服务端交接（2026-11-04）

本文件只交接非秘密来源与证据，由用户转交小程序侧；不授权继续付费调用、微信后台配置、客户端上传/提审/发布或账号/B–E。服务器操作均由用户执行回传，最新回执在主repo `CLOUD_HANDOFF.md` 文首和 `MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json`。不要拿第一阶段false/null期望当作现在CN OCR期望。

## 已确认的服务器状态

- HTTPS origin：`https://mini-test.racepick.cn`。公网CN catalog未认证401/no-store、双服snapshot未认证401、账号路径404；这不是完整会话或实图链路验收。
- 网站：`7241d9d67cc99178bd7d2d14`。guest/bridge基底交付：`35bd5c5d2e618b555de3a70c`，封存源码 `source_commit=null`，开发base为0b97dae9e1003c1bc2c4c5b7a189b81cb4002112，不冒充新Git提交。
- bridge实际多一个修复依赖：`backend/map_ocr_production.py`，从网站7241原文件复制，SHA `3c8a7d64564da8d7804bd0f35a8aba960ee922d86573af8973c857ec10718872`、4495字节；原ZIP未改，运行目录含补件不能冒充原包零差异。guest源文件保持原交付。
- guest `image_policy=aliyun_baseline`、bridge enabled true、safety mode live。二者active且开机启动；原唯一监督者/worker/JobStore继续复用，没有第二套模型。schema0→1仅一次，原jobs指纹核保留（当时0任务）。Global OCR false/null，账号/B–E继续关闭。
- 实际UID996通过SO_PEERCRED访问受限Unix socket，验证CN目录83图、版本 `57876474bd3cd25c283e79a471be99ec76d4e58ed16fa0e2c8ae2a6cdf0b9ced`，完整maps SHA `7b4e180ed199d4319f4b756477039232038043214a9a239d20ac782f97670b54`。Global目录请求由桥明确拒绝。
- 最终回执：`/root/racepick-deploy/mini-ocr-20261104-35bd5c5d/native-final-nudoqb0h/activation.json`；备份timer active，下一次定时执行尚未观察，不新建监控。

## 固定数据绑定

完整五文件SHA/bytes、83图原顺序与目录绑定见同目录 `MINI_OCR_CN_BINDING_20261104.json`，来源封存包 `OCR_EXPECTATIONS.json`，附现场目录证据和未核边界；不是用旧DEFAULT_EXPECTATIONS改名冒充实测。

- CN固定快照 `593ecc7222ceea5856b2f576b4f5bca8`，Global固定快照 `e29f52e7f81c3e337985bf05dedb7e88`。
- Global dataset `9b83ddd062a4d4b0c15d51dc0eed323aabb8e599e3e9544bc91714b70a7a4259`。
- 冻结 `b57d97a8f4e484be69238ab0`，清单SHA `940f8660585c495a780390b709dfd52e80f7610f57e0179c5da937c53c4e4282`，`data_commit=null`；CN4516/Global694固定数据。本次没有维护成绩导入或正式成绩指针切换。
- 正式网站仍CN `c815b612a17433f403ae2965000fd74b` / Global `435d5b40fd1aa4a01753a395f28d1f89`；不能与原生固定快照ID混用。identity须每个真实会话动态核验，不在交付中预填。

## 路由和边界

沿 `MINI_API_CONTRACT_20261102.md` 的固定方法/query，multipart仅一份image。根路径均为 `/api/mini/v1`：

| 方法 | 路径 | query恰好包含 |
|---|---|---|
| POST | /session | 无 |
| GET | /snapshot | server |
| GET | /map-recognition/catalog | server |
| POST | /map-recognition/jobs | server、catalog_version、request_key |
| GET | /map-recognition/jobs/by-request | server、catalog_version、request_key |
| GET / DELETE | /map-recognition/jobs/{32位hex id} | server、catalog_version |

单图8388608字节，multipart封装8454144字节，16000000像素；静态PNG/JPEG/WebP和横屏有效性由服务端校验。上传Nginx client_body_timeout20秒、proxy_read_timeout25秒，禁请求/响应缓冲；其余OCR读取5秒，保持原session/snapshot的4KiB及独立预算。新增OCR边缘2r/s burst4，429；共享队列总8、owner2、同可信IP20/600秒，checking也占额度，审核通过才可被唯一worker领取。SDK连接5秒/读取15秒/总60秒、无自动重试；原worker45秒运行截止及TTL3600秒沿原实现。JSON不缓存、Cookie/Origin拒绝，客户端不猜额外字段或把错误文案解析成重试指令。

## 图片安全和证据限制

已实际使用阿里云baselineCheck：服务端临时上传凭证→供应商临时OSS→同步ImageModeration，只有明确none/nonLabel通过才允许OCR准入；识别成功不是内容安全审核。仅部署的一张非私人合成图明确通过，修复及最终续开命令均未再调用审核接口。没有用私人图片、真实微信code、OpenID或其他业务正文验证。

图片确实会发送阿里云，不能声明“仅本地处理”“不外发”或“零留存”。先前官方选型记录为临时OSS约30分钟、审核结果近30天可查询；这是供应商文档记录，未现场验证副本/删除时点或全部日志保留。客户端上线前需核对实际隐私提示、第三方处理声明及用户授权，拒绝/取消仍可手选。当前用户仅授权本轮一次合成审核验证；额外开发者工具/真机实图调用和费用须后续明确范围，不自动重试或切提供方。

现阶段未生成新的真实任务成功/部分/拒绝/限流/超时/取消/恢复响应样本；本地模拟样本与Ubuntu隔离测试属于之前开发证据，不能当成这次公网/手机通过。国际服禁止OCR不影响国际服手选/快照。

## 小程序侧下一阶段

由用户协调小程序侧，先按固定原字节与catalog maps重算校验，再建独立OCR检查工程；保留已验收工程/车库，不连接完整账号/管理UI。实际uploadFile合法域名由用户后续在微信后台配置，保持TLS与request条目，不开放下载私人照片域名。

获准样图/调用范围明确后，先开发者工具真实会话与uploadFile；再用户手动手机验收相册取消/拒绝、上传失败、前后台/切网、同key恢复、到期与迟到结果。入口仍小按钮、直接相册、无拍摄选项，结果先确认且未知/重复/缺图不能自动覆盖。iOS/Android分别记录，服务器目录或一次供应商通过均不能代替真机验收。本轮没有操作微信后台或向其他聊天派任务。
