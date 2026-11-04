# 原生HTTP接桥与完整交付准备（2026-11-04）

> 后续现场结果：CN原生OCR服务端现已由用户执行开启，唯一一次非私人合成图baselineCheck通过，schema1仅迁移一次，桥/guest active并开机启用；Global OCR及账号/B–E关闭，真实微信/手机OCR待验收。最新事实见主repo `docs/CLOUD_HANDOFF.md` 文首、`docs/MINI_OCR_DEPLOYMENT_PREPARATION_20261104.json` 和 `docs/MINI_OCR_CN_CLOUD_HANDOFF_20261104.md`，本文下方“仅本地/未上线”为构包阶段记录。原ZIP未改；运行桥另补网站7241原始 `backend/map_ocr_production.py`（SHA3c8a7d64564da8d7804bd0f35a8aba960ee922d86573af8973c857ec10718872/4495字节），本地builder已补该依赖并新增实际模块集隔离导入回归，不冒充原ZIP已重构。安装候选guest单元前必须确保 `/etc/racepick-ocr-safety` 私有目录存在，否则InaccessiblePaths会报226/NAMESPACE；当前配置完成后目录归运行UID999且0700。配置在失败回退后已存在时比较准确内容与owner/mode后复用，不删除重做。部署就绪检查需等待Nginx reload后新worker生效，避免把短暂404判作最终失败。

本轮用户授权本地接线、Ubuntu离线依赖锁、完整可校验包及可做的验证；排除真实密钥/供应商传图或付费调用、服务器、微信后台和公网启用。所有现有账号/成绩/反馈/备份、工作簿、测试资料和未跟踪文件保留。

## 最终结构与默认关闭

`mini_ocr_guest_service`复用既有真实访客校验和五文件固定快照，通过`BridgeRecognitionPort → QueueBridgeClient → AF_UNIX → QueueBridgeCore`访问唯一JobStore。访客进程没有queue-config/数据库/阿里凭据字段，无法因配置注入挂载业务库。原第一阶段mini_guest_service继续支持原配置，未自动切入口。

image_policy默认disabled时只开放POST session、GET双服snapshot，OCR404、两服false/null，不构造桥客户端、不启动模型或读RAM凭据。只有显式选择aliyun_baseline的独立网关才注册catalog、POST jobs、GET by-request、GET/DELETE jobs/{id}；account/B–E及其他路径404。Cookie/Origin/OPTIONS仍拒绝，JSON no-store，严格method/query及单份image multipart沿原协议。

新桥目录、前置容量查询及上传调用放在线程池，避免阻塞HTTP事件循环。原key读取租约、同文件/同目录/owner绑定保留；桥已提交但响应丢失时，先查原key，恢复同id，不再送审。关闭上传或worker不ready时CN快照继续可手选并回false/null，原任务GET/recover/cancel使用固定目录而不依赖上传开关。Global始终false/null/识图403。

审核checking任务占网页与原生同一8任务/owner2容量及同IP20次/600秒；审核通过才queued，旧worker只领取queued。取消/超时/关闭后迟到审核不能复活任务，真实SDK子进程仍受60秒总截止。仅none+nonLabel放行；low/medium/high、review、人审、未知、空或错误均失败关闭。本轮没有启用广告引流专项、大模型、人审或自动OSS扫描。

## 网站兼容与数据边界

完整网站包取已验收a933原字节为基底，仅叠加backend/map_recognition.py、mini_api.py、mini_auth.py、新mini_result.py、production_release_tools.py和score-capability.json。CODE_DIFF.json列实际差异，HTML/CSS/JS、模型、原37个依赖保持基底字节，不夹带其他本地页面更新。

新工具在只读发现队列safety_schema1或部分结构时拒绝不具备ocr_queue_safety_schema1的旧网站。普通JobStore启动和桥serve不自动迁移；未来必须显式授权准备识图安全schema，并保留所有既有任务/图像/结果。旧a933代码不统计checking，不能只部署桥后混跑旧容量检查。关闭OCR后可以保留新兼容网站代码和schema，继续原网页及原生手选；不靠恢复旧SQLite回退。

本包五份JSON与批准b57d97a8冻结一致，测试快照版本CN593ecc7222ceea5856b2f576b4f5bca8、Globale29f52e7f81c3e337985bf05dedb7e88；它们不是正式活动指针。CN目录版本57876474bd3cd25c283e79a471be99ec76d4e58ed16fa0e2c8ae2a6cdf0b9ced，目录map清单及SHA见OCR_EXPECTATIONS.json。Global dataset9b83ddd062a4d4b0c15d51dc0eed323aabb8e599e3e9544bc91714b70a7a4259。identity仍由每个真实会话动态签发，不预填或回传秘密。

源码source_commit=null，实际文件用SOURCE.json封存，开发base_commit仅供追溯。网站基底代码765a4a6/a933与本轮封存overlay分开标记。没有代用户提交推送或把旧HEAD当作实际新源码提交。

## Ubuntu离线依赖与本地证据

四环境分锁：guest14 wheel、bridge37 wheel、web沿原37 wheel、validation55 wheel；锁中每项固定版本及SHA，网关不安装阿里SDK，安全桥不安装OCR模型推理依赖。web的requests2.33.1和bridge的requests2.34.2各在自己的环境，不互相覆盖。

Ubuntu24.04用户态chroot/CPython3.12.16中，全部环境经无索引、require-hashes离线安装和pip check；真实SDK签名/模型/oss2测试仍mock HTTP，无供应商请求。crcmod1.7没有合适原生wheel时，使用上游支持的纯Python回退模块，未修改模块源码；来源sdistSHA、可重现构建脚本、逐字节重建校验和wheelSHA随包保存，实际Ubuntu SDK模拟线测覆盖该wheel。

Windows新旧合并142项执行，122通过、20项Linux专用跳过；Ubuntu完整124项全部通过、无跳过（Windows另跑的18项发布工具回归不计入Linux124）。Linux还实际运行Nginx1.24 HTTPS、生成的隔离CA验证和真实Unix socket，broker UID10001、guest UID10002；guest读queue SQLite被权限拒绝。原key同一图片只触发一次模拟审核，Global拒绝识图，Cookie/Origin403、未知账号404、session4097字节及上传封装超限413，关闭新上传后手选/恢复/取消保持。实际8MiB合成PNG边界结果及详细回执以VALIDATION.json为准。

systemd255的systemd-analyze verify已核候选两单元语法，退出0；仅在隔离root中替换为测试路径/数字UID，并补充基线target占位用于静态解析。没有启动真实systemd单元或验证服务器cgroup/挂载视图，不能把静态语法检查当作资源与隔离策略已上线。

环境为独立mount/network/PID namespace，只开其内部loopback、只读运行目录、有界tmpfs；模型未在HTTP/桥进程加载。合成OCR worker仅测试claim/finish和五槽结果清洗，不是中文截图CPU识别、真实微信或手机验收。源码、离线wheel和模板核验都不代表生产服务已更新。

最初Ubuntu测试目录漏带两个配置/测试依赖，已补齐后完整通过；原失败日志保留。Windows早期新兼容测试夹具连接未关闭导致临时目录清理失败，已改为显式close并通过；不是正式库修改或应用回滚。之前Docker Inference manager故障未reset或修复；本轮用现有WSL隔离用户态验证，没有配置远程服务器。

## 需要配置的内容（现在不填真实值）

1. 地域与服务：默认cn-shanghai，固定baselineCheck；不自动跨地域/换服务重试。真实送审前确认接受临时OSS30分钟和独立审核结果近30天查询边界，其他删除/留存细节不能写零留存。
2. 专用RAM凭据：access_key_id、access_key_secret，私有文件`/etc/racepick-ocr-safety/aliyun-baseline-credentials.json`，只给安全桥运行用户600权限；guest和客户端不可见，不在聊天/Git中发送。RAM最小Action提案为DescribeUploadToken与ImageModeration，本轮未实际授权/验证。
3. 现有微信配置：保留访客state_dir、AppID/AppSecret文件和原session密钥，不复制测试状态/重新provision；新独立配置只增加bridge_socket及默认disabled策略。无需微信内容安全OpenID或审核回调。
4. 现场UID/GID与路径：核实原队列owner、guest UID、最小socket共享组GID、固定release和snapshot路径及唯一queue config；模板null/占位符不能照抄。桥运行用户可访问队列和阿里私有配置，挂载视图必须隐藏账号/score-state/SMTP/微信秘密；guest只访问自己的状态/快照/socket。
5. 资源：guest候选High128/Max256MiB，bridge候选High256/Max512MiB，均无swap；原OCR640/768MiB和唯一监督者保持。候选数值不是现网容量验收，必须先结合实际内存、并发及SDK子进程峰值核对，不能盲覆盖原单元。

## 后续推进顺序

先核本包SHA/目录/manifest及主repo最新CLOUD_HANDOFF，再给用户当前一步服务器只读核验命令；没有本轮生产授权时不执行。核实际current/PIDcwd/health、原生状态、双服活动指针、队列/唯一worker、备份服务和实际最近备份及timer、内存磁盘/Nginx配置。状态漂移先停在核对。

之后按新授权准备完整成套备份与独立恢复，原队列单独保全；只在证据通过后请求必要的共用网站兼容升级和识图队列schema准备，不重跑账号/global-profile/coverage/国际成绩或维护发布。新网关和桥先保持disabled暂存，离线安装、路径权限及挂载隔离核实后，再决定安全配置、获准样图限量付费测试和CN开启。最终实际版本/健康/原队列/备份调度恢复及公网验收逐步收尾。

小程序侧只能在服务端实际准备后拿OCR_EXPECTATIONS绑定原字节、目录和identity，创建独立OCR检查工程；随后另由用户登记uploadFile合法域名，先工具再手机分系统验收。本轮不操作微信后台、上传体验版/提审/发布，不开放账号/B–E，不清理旧包/旧版本/业务数据，不创建监控。
