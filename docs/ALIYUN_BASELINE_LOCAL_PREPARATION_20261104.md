# baselineCheck本地适配器与配置准备（2026-11-04）

用户已确认采用阿里云baselineCheck，后付费服务由用户开通。本轮授权仅本地适配器、配置模板和模拟测试；真实送图/付费调用、服务器变更和公网OCR开启不在范围。

## 已实现及边界

- `backend/image_safety_aliyun.py`：独立适配器，按官方DescribeUploadToken→临时OSS上传→同步ImageModeration流程构造参数。固定baselineCheck、国内endpoint、不上传OpenID或owner/key、仅接受明确RiskLevel=none且Result为官方nonLabel正常标记；low/medium/high及人工审核均不放行，免审图库nonLabel_lib也不等同本流程安全通过。只返回批准标志与图像SHA，不透传供应商原文、URL、令牌或图中文字。
- 配置只接受disabled/simulation，默认disabled。不包含真实HTTP/SDK传输实现，不安装新依赖、不读凭据、不自动发现环境变量或云账号。simulation仍必须注入显式is_simulated=True的测试传输；目前不是可以通过填入凭据直接联网的版本。
- `backend/image_safety_local.py`：只允许显式创建的本地demo JobStore，拒绝production store。审核回执存在同一个识图SQLite的新local_safety_receipts表内，不创建第二队列、不启动模型；审核通过才调用原JobStore.create，其容量8/owner2和原事务保持。
- 回执绑定owner、原key、图像SHA和目录；完成后同key恢复同id、不重复送审；换图/换目录409语义；拒绝或响应不确定持久记忆，不自动再次送审。入队后响应丢失亦可恢复；队列满保留该key的批准回执，释放槽位后可同key重试，不二次调用供应商。
- 尚在送审的本地回执不是OCR任务、不会被worker领取。本轮没有实现生产reservation/共享待审核配额/socket桥；模拟不能证明网页与原生并发审核的总资源隔离已完成。真实生产接线仍须原第二阶段方案里的Unix桥、准入容量、取消待审/关闭收尾及Linux沙箱验证。
- 本地recover返回deciding/approved/rejected/uncertain仅为Python测试诊断，不修改MINI_API_CONTRACT的HTTP字段或让客户端接新状态。现有mini_guest_service/mini_api/mini_auth/JobStore/worker/监督者和原生image_policy均未修改；公网session/snapshot仍按原交付，OCR保持关闭。

## 配置模板

非秘密模板：[`production/aliyun-baseline.config.example.json`](../production/aliyun-baseline.config.example.json)。RAM策略提案：[`production/aliyun-baseline.ram-policy.example.json`](../production/aliyun-baseline.ram-policy.example.json)。它们均未安装到服务器，也未在任何云账号应用权限。

| 配置 | 当前模板 / 后续需要准备 |
|---|---|
| 地域 | 默认cn-shanghai，endpoint自动派生green-cip.cn-shanghai.aliyuncs.com；可在已支持国内地域中明确选择，后续不自动跨地域重试 |
| Service | 固定baselineCheck，不能从此模板切换到postImageCheck或大模型 |
| 模式 | disabled；仅独立测试复制配置改simulation。当前不支持live值，填凭据也不会自动上线 |
| 凭据位置 | `/etc/racepick-ocr-safety/aliyun-baseline-credentials.json`只是将来安全适配进程私有文件的候选路径，访客进程不得可见；本轮没有创建/读取此文件，也不用现在往聊天发送凭据 |
| RAM身份 | 将来使用专用RAM用户/角色，需DescribeUploadToken和ImageModeration两项权限；不用主账号AccessKey，不给自有OSS全权限 |
| 超时 | connect5秒、单步read15秒、总60秒；本轮是模拟超时参数与迟到回包检查。真实socket/SDK强制截止需后续传输实现与Linux测试，不能把模拟结果当硬截止已部署 |
| 重试 | automatic_retries=0，供应商异常不自动切区域/切提供方/换key；收费结果不确定先查本地原key |
| 通过策略 | allow_risk_levels仅none，正常标记nonLabel；未知、空结果、异常、DataId不匹配均拒绝 |
| 费用与增值项 | 用户后付费已开通；baselineCheck沿既有15元/万次口径。暂不启用广告引流专项、大模型增强、人工审核或自动OSS扫描 |

用户后续真正需要安全配置的秘密仅RAM AccessKey ID与AccessKey Secret（若未来采用STS，还需明确临时凭据加载与续期设计）；凭据文件字段和安全加载由后续真实传输层固定。本轮模板只有文件引用，不收集或验证这些秘密。真实配置须由运行用户私有文件加载，密钥不入仓库、交付、客户端或聊天。

不需要准备微信OpenID、微信审核回调服务器、第二个OCR模型或自己的图片审核OSS Bucket。上传凭据和临时bucket由DescribeUploadToken返回，图像仍会在未来真实调用时发给阿里云；临时图片30分钟、审核结果近30天查询的边界仍须如实告知，不因用户开通服务变为零留存。

## RAM策略依据

官方[DescribeUploadToken授权信息](https://help.aliyun.com/zh/document_detail/2926827.html)明确Action=`yundun-greenweb:DescribeUploadToken`、Resource=`*`；官方[ImageModeration授权信息](https://help.aliyun.com/zh/document_detail/2528742.html)明确Action=`yundun-greenweb:ImageModeration`、Resource=`*`。因此附带提案只允许这两项Action，未使用全功能权限。实际有效权限及账号状态需未来只读核验，不把模板写成已授权成功。

请求及正常结果形态依据[同步API](https://help.aliyun.com/zh/document_detail/467829.html)、临时上传流程依据[SDK本地图片说明](https://help.aliyun.com/zh/document_detail/467828.html)。适配器中的传输端口使用statusCode/body映射；后续SDK桥需使用官方模型to_map等做格式归一化、限响应大小、关闭自动重试及重定向。当前未固定真实SDK/OSS依赖版本，也未宣称已完成SDK联网验证。

## 本轮实际验证

在网站功能工作树执行：

```powershell
python -B -m unittest backend.test_image_safety_aliyun
python -B -m unittest backend.test_mini_guest_service backend.test_mini_api backend.test_mini_production backend.test_map_recognition
```

新增23项模拟测试通过；既有48项回归通过。新测试仅使用内存生成的640×360纯色PNG、假供应商回包及TemporaryDirectory队列，不使用用户截图或现有测试库；适配器单测禁止socket.connect。没有真实微信/阿里调用、CPU模型推理、Linux单元或生产容量验收。

覆盖：默认disabled且不读凭据、未知配置/真实传输拒绝、三步固定请求与不重试、HTTP与业务失败、风险/人工/免审库拒绝、供应商DataId不匹配、临时token过期/非法目标、超时/迟到、原key图像/目录冲突、owner隔离、并发同key去重、崩溃deciding记录阻止重送、重开SQLite恢复、入队响应丢失、共享原队列满与owner2限制、取消后迟到结果不复活、production store拒绝。

测试不证明真实RAM权限、SDK归一化、原图送审准确率、供应商留存/删除履约、生产待审取消/全局配额或公网OCR。所有待完成项仍见第二阶段方案。准备结果机器回执：`ALIYUN_BASELINE_LOCAL_RECEIPT_20261104.json`。本轮文件均未提交/推送，无部署包或上线来源变更。
