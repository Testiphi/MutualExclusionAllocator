# 真实SDK传输及共享队列桥本地实现（2026-11-04）

本轮按用户授权完成本地代码、模拟测试与可行的Linux隔离验证。未配置真实密钥、未向审核服务传图或收费调用、未操作服务器/微信后台，公网OCR仍关闭。前一轮“尚无真实SDK传输”的说明属于此前阶段；本文件为新的实现状态，不倒改旧回执。

## 实现

- `image_safety_sdk.py`使用官方green20220302 SDK的签名/请求/响应模型和oss2签名上传。真实网络发送被限制到独立SDK子进程；默认没有live授权，读凭据、启动子进程和发送请求都不会发生。配置mode=live本身也不够，调用方还必须显式给予allow_live_calls=True，桥入口另外要求显式命令参数。本轮没有这样启动真实子进程入口；测试子进程只执行合成回包/挂起夹具。
- 为约束SDK默认行为，SDK子进程内将其HTTP发送边界换成有界HTTPS发送器：固定国内审核endpoint及临时token指定的OSS主机，TLS验证、关闭环境代理与重定向、自动重试0、响应最多64KiB。钩子只存在于专用子进程，不在网页共享进程中替换SDK全局方法。OSS使用官方STS签名，不使用用户自有bucket、不暴露长期访问链接。
- 父进程以总60秒预算等待并终止/回收自己的SDK子进程；POSIX子进程额外禁止core dump、限制64文件描述符和512MiB地址空间。单步连接/读取预算5/15秒，所有供应商异常统一转为不含敏感信息的错误码。地址空间限制不是整个服务的cgroup内存容量结论。
- `ocr_queue_bridge.py`提供AF_UNIX服务器/客户端和QueueBridgeCore。Linux核验SO_PEERCRED指定UID，socket0660，私有父目录；只接受create/recover/get/cancel/catalog固定字段及CN固定目录，不接受SQL、路径、客户端maps、网页owner或任意URL。一个连接一帧，8KiB头/8MiB图片，20秒总读取限制，拒绝重复字段/尾部数据；连接和安全处理均有界，最多8个已接纳审核工作、2个审核线程，不加载OCR模型。
- `JobStore`增加显式prepare_safety_schema，普通启动不迁移；增量表为safety_schema/safety_checks，仍使用同一个识图SQLite。新任务初始checking，原worker只claim queued，因此审核前不能领取；共享8任务/owner2及owner/IP每600秒20次统计包括checking。网页沿原JobStore.create也计入checking，不另开额度。安全检查60秒超时失败并删除媒体，不释放后自动重送。排队超时仍按任务最初创建起120秒上限计算，审核耗时包含在这段等待内。
- 同owner/key/原图SHA/目录复用唯一id和保存状态。审核通过才CAS转queued；拒绝/超时/服务失败保持failed，重复上传不会再送审。取消、到期、停止后的审核回包无法复活任务；关闭新上传后仍可恢复/查询/取消旧任务。checking内部状态对桥调用者投影为既有queued。结果仅通过现有map-only清洗返回，不返回原图或OCR无关原文。

## 当前没有改变的入口与交付边界

第一阶段mini_guest_service仍只开放session/snapshot，image_policy仍disabled；mini_api和mini_auth没有改为接受新图片策略或共享桥配置。桥客户端已实现，但独立原生HTTP网关的正式接线、Nginx和systemd安装仍未执行；不能把桥代码存在当作公网OCR已可用。

桥的内部消息/状态不构成已上线的第二套HTTP协议。后续原生网关应经QueueBridgeClient调用，禁止再直接挂队列SQLite或正式账号库。固定快照通过现有load_snapshot核原字节，CN目录hash由快照版本和原成绩字节派生；不跟踪或改写正式成绩指针。Global识图继续关闭。

本地实现改变了网页共用的JobStore容量统计，因此未来不能只安装桥、继续让旧a933的旧JobStore并发入队，否则旧代码不计算checking，无法保证共享容量。需要先在隔离环境打包核对网站共用模块与桥的兼容，再按用户授权分步骤升级。原OCR worker不识别checking也不会领取它；这不代表旧网页容量检查可直接混用。

新增的识图安全schema需要未来单独授权的显式增量迁移；serve不调用prepare_safety_schema，不创建队列、不初始化业务组件，不重复global-profile或维护成绩迁移。新运行代码尚未提交、推送或制作可部署包。

## 配置材料

| 项目 | 模板 / 后续填写内容 |
|---|---|
| 阿里策略配置 | [aliyun-baseline.config.example.json](../production/aliyun-baseline.config.example.json)，默认disabled、cn-shanghai、baselineCheck、5/15/60秒、0重试，仅none+nonLabel通过 |
| 私有凭据 | 未来路径`/etc/racepick-ocr-safety/aliyun-baseline-credentials.json`；JSON恰好access_key_id、access_key_secret。由安全桥运行用户私有持有，0600、单硬链接、无符号路径；访客进程不可见。不要将值发到聊天/仓库/客户端 |
| RAM | [两项最小Action提案](../production/aliyun-baseline.ram-policy.example.json)：yundun-greenweb:DescribeUploadToken、yundun-greenweb:ImageModeration；未实际应用或验证账号权限 |
| 队列桥 | [ocr-queue-bridge.config.example.json](../production/ocr-queue-bridge.config.example.json)，默认enabled=false；须填现场核实的访客UID、最小socket共享组GID，不能直接照抄历史值 |
| 路径绑定 | 唯一现有队列config、固定已核验快照目录、独立socket路径及安全配置文件；禁止改为账号库、score-state、维护数据或旧测试库 |
| 网络依赖 | [requirements-aliyun-sdk.in](../production/requirements-aliyun-sdk.in)固定SDK3.6.9/oss2 2.19.1及所依赖HTTP核心版本。仅安装于本轮独立Windows虚拟环境；未并入网站/worker生产锁，Ubuntu Linux离线wheel全量锁及打包仍待做 |

现在可以只读校验公开模板，命令不读凭据、不打开队列或模型：

```powershell
python -B -m backend.ocr_queue_bridge check-config --config production/ocr-queue-bridge.config.example.json
```

本轮实际输出enabled=false、credentials_loaded=false、queue_opened=false、model_started=false。本文不提供服务器写脚本或公网开启命令。

## 实际验证

1. Windows Python3.14：适配/SDK/桥测试48项执行、37通过、11项仅Linux的Unix测试跳过。随后补测官方SDK HTTP500不重试，SDK真实签名/模型/OSS模拟发送3项通过。原访客/原生接口/识图/生产形态队列回归53项通过。SDK网路边界全部mock，使用假凭据/合成纯色PNG，无真实供应商请求。完整日志在offline-evaluation/mini-ocr-sdk-bridge-20261104-01。
2. SDK确实从官方PyPI安装到本轮新venv，未修改系统或既有项目依赖。默认阿里镜像源未提供对应版本，切到官方PyPI后安装成功；sdk-windows-freeze.txt保留实际解析版本。SDK依赖有既有utcnow弃用提示，不影响通过；未为此改第三方源码。
3. Docker Desktop启动在本机Inference manager失败；用户截图确认。没有reset、删镜像/volume、上传诊断或修复Docker配置。现有docker-desktop WSL可运行，但原先无Python。仅本轮新建的临时root中安装Alpine3.22/Python3.12.16/Pillow11.2.1，不修改WSL系统包。
4. 真Linux测试：独立mount/network/PID namespace、chroot、UID/GID10001、只读root、96MiB可写tmpfs、512MiB进程地址空间/96文件描述符。46项全部通过，无跳过；含真实AF_UNIX、内核peer UID、不正确peer拒绝、真实共享SQLite网页/原生配额、审核前worker不可领取、取消防迟到、关闭仍可恢复/取消，以及SDK挂起子进程硬截止回收。业务路径不可见，model_loaded=false。
5. 失败尝试如实保留：便携musl静态Python不能动态加载Pillow；首个Alpine测试因该WSL临时文件系统空间不足而失败，隔离tmpfs后通过。首次失败stdout未完整保存为文件，不能声称有完整原始日志；后续linux-attempt-02.log及linux-final.log已保存。用于复验的Alpine临时root完整归档到linux-fixture-rootfs.tar.gz及SHA/清单，随后只移除了本轮新建的该临时root以释放其占用；Docker原有数据未变。

## 尚未证明与下一步

Linux为本地WSL/Alpine，不是目标Ubuntu24.04、真实systemd挂载/cgroup或生产常驻容量；未验证8MiB/16M并发峰值、外部接口速度、审核准确率、RAM实际权限及供应商留存履约。Linux的SDK子进程测试使用合成目标，真实官方SDK签名模型仅在Windows模拟HTTP边界验证。不能把这些结果写成Linux真实阿里调用通过。

下一步先完成原生HTTP网关到桥的隔离接线、Ubuntu离线依赖锁与可校验构包/兼容报告；这些本地工作可继续在不提供真实密钥时完成。需要真实配置时再由用户安全放置RAM凭据，并确认地域、实际UID/GID和路径，明确小批获准样图调用范围与预算。服务器安装/队列schema变更/网站兼容升级/Nginx/systemd和公网开关均按既有方式另获授权，一次一个步骤；保留业务状态、旧包、备份及原队列，不开启账号/B–E、微信后台或小程序发布。
