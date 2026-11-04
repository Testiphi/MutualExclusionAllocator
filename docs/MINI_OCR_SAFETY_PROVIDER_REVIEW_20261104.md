# 访客OCR图片安全提供方核验与建议（2026-11-04）

本轮只读取公开官方文档和用户粘贴资料，没有调用审核API、上传图片、调试API、登录云控制台、开通服务、收费操作、访问服务器或改变公网OCR。此前方案的“微信官方页访问失败”是上一轮状态；本轮普通HTTPS请求成功读取新官方HTML及Markdown，以下是补充核验，不回写旧回执为已通过。

## 建议

优先选择**阿里云图片审核增强版的国内同步接口，采用本地文件上传方式**作为下一步开发候选。建议按覆盖范围选择postImageCheck（30元/万次）或经明确范围评审后的baselineCheck（15元/万次）；不默认开启大模型/人工审核，不采购资源包。此处是技术选型建议，不是开通或外发授权。

选择理由是现有8MiB/16M静态PNG/JPEG/WebP上限可在官方范围内处理，不需要微信OpenID、不增加微信回调入口，审核结果可在同一次后端调用中返回，更容易接入先审核再领取的短任务流程。阿里“本地上传”实际先送到提供方的临时OSS，并非直接把二进制放进ImageModeration请求，也不是零留存；是否接受这一数据边界是最终选定前的必要决定。

微信mediaCheckAsync 2.0属于技术上可实现的备选，但不适合作为当前快速识图主路径：要求额外保存/持有真实OpenID、可下载的媒体URL和消息推送配置，官方异步结果窗口为30分钟。当前拟60秒审核截止不能由此得到保障。若用户后续更重视微信原生能力且接受较长等待，可重新设计为长任务；不能先放行OCR、事后等审核。

## 微信官方：逐项核验

主来源：[mediaCheckAsync官方接口](https://developers.weixin.qq.com/miniprogram/dev/server/API/sec-center/sec-check/api_mediacheckasync.html)，页面标注最后编辑2026-10-29；[同页官方Markdown](https://developers.weixin.qq.com/miniprogram/dev/server/API/sec-center/sec-check/api_mediacheckasync.md)。本轮web阅读器仍不可打开该页，使用普通HTTPS读取成功并解压gzip后核验，无登录或接口调用。

| 项目 | 官方正文确认 | 对当前项目的影响 / 未确认项 |
|---|---|---|
| 账号权限 | 适用账号类型列小程序、小游戏；必须服务端调用、持有效access_token。第三方代调用权限集18 | 没有在该页看到“必须企业主体/认证”条文；不能自行加此前提。也未核你的账号后台权限或实际调用，wx.login成功不等于审核权限已证实。18是第三方平台代调用说明，不是自建后端必须接入第三方平台 |
| OpenID | 2.0正文必填openid，用户需近两小时访问过小程序；43104表示appid不匹配，61010表示访问超时 | 现有GuestStore仅存HMAC摘要，无法还原OpenID。选择微信需要显式改身份数据最小化策略；可设计短期服务器内存/加密暂存，不能让客户端传任意OpenID，不能从旧code重新交换或从摘要逆推。仍无需RacePick邮箱账号 |
| 传图 | 必填media_url，微信检测服务器必须能下载；不是二进制/Base64输入 | 需新增受限下载能力或受控云对象URL。可以设计短时签名链接，避免永久公开，但仍扩大“没有媒体下载入口”的现有边界，且要覆盖异步取图时机 |
| 大小/格式 | 单文件≤10M；列jpg/jpeg/png/bmp/gif首帧；2.0必填version=2、media_type=2和scene | 现有8MiB数值小于10M，但WebP未列为支持，需有绑定的转码设计或限制格式。该页未给16M像素保证；不能据大小上限推导像素支持。scene只有资料/评论/论坛/社交日志，截图工具应进一步确认适用映射，不伪装为评论 |
| 配额 | 每AppID 2000次/分钟、200000次/天 | 远高于当前业务设计限额，但不能代替本地共享配额，也不保证当前账号无额外限制 |
| 回调 | 初始成功给trace_id，最终通过wxa_media_check事件推送，官方窗口30分钟 | 必须配置消息接收服务器；HTTP调用成功/errcode0只表示接收，不是审核通过。校验回调appID/trace_id/版本/签名/去重/到期；结果errcode0且suggest=pass才允许OCR，review/risky均不放行 |
| 留存 | 本页没有给图片副本、缓存、审核记录的删除期限或立即删除API | “30分钟”是结果推送窗口，不是图片删除承诺；不能宣称微信不留存，取消本地任务也不代表撤销微信已收到的图片 |
| 费用 | 该接口当前官方页列配额，未列单价或永久免费的保证 | 未找到足够的当前官方价格依据；本报告不以非官方文章把它写成已核实0元。媒体存储、URL出站流量和运维成本还需单算；不为核价执行开通/付费 |

回调配置来源：[微信消息推送官方文档](https://developers.weixin.qq.com/miniprogram/dev/framework/server-ability/message-push)。配置包含URL/Token/EncodingAESKey与安全模式；实际部署需要用户另行授权后台设置及服务器入口。不能把uploadFile合法域名登记当消息推送设置已完成。

旧imgSecCheck的常见1MB/750×1334同步示例不是本次选型依据；本轮两个旧官方URL返回404，没有把旧参数当作新接口能力。小程序已有真实访客也不等于可沿用这些历史接口。

## 阿里云：本地上传与直接二进制的区别

官方来源：[同步检测API](https://help.aliyun.com/zh/document_detail/467829.html)、[SDK接入指南](https://help.aliyun.com/zh/document_detail/467828.html)、[功能和计费](https://help.aliyun.com/zh/document_detail/467826.html)、[控制台结果查询](https://help.aliyun.com/zh/document_detail/467827.html)。

- 开通按量服务后使用RAM身份签名；不要求微信身份。文档给系统策略AliyunYundunGreenWebFullAccess，实际落地还应核实ImageModeration及DescribeUploadToken所需最小权限，不把主账号AccessKey交给访客进程。
- 同步ImageModeration接受URL、已授权OSS对象，或SDK本地图片流程。本地流程先DescribeUploadToken，再上传内容安全提供的OSS Bucket，随后调用审核。无需自有公网媒体URL，不占用户自己的OSS存储空间；仍然向阿里云外发图片。
- 当前官方API限制20MB、单边≤30000px、总像素≤2.5亿，含PNG/JPEG/WebP，覆盖现有8MiB/16M输入设计；不因此扩大RacePick自身上限。
- 临时文件文档明确30分钟；控制台支持近30天结果查询，详情可含图片预览/URL及完整审核结果。两者不是同一类数据期限；不能宣传“所有数据30分钟彻底删除”。审核日志、派生内容、备份、训练使用与提前删除需提供方进一步澄清。
- baselineCheck同时涵盖色情、涉政、暴恐、违禁等；tonalityImprove负责广告引流等治理；postImageCheck组合范围含广告引流和其他风险。15元单Service不代表全部服务都检测。两项15元服务会分别收费；postImageCheck为30元/万次；大模型单独计费或开启增强产生额外计费，不能自动开启。
- 建议对实际游戏截图与误上传图片做未来授权的效果验证，不能依据产品描述断言准确率。请求成功还需检查业务Code/风险结果，超时、未知、review/需人工的分支均不进入OCR；不自动把图片交人工审核。

## 腾讯：CI与IMS是两套产品

用户提供的是数据万象CI及其COS授权/桶绑定流程，不能套用到IMS后宣称同一费用。

| 项目 | 腾讯CI（用户提供方案） | 腾讯IMS（另行比较） |
|---|---|---|
| 输入 | 图片批量审核POST支持Content Base64，Async=0可同步；不是只能对象URL | ImageModeration支持FileContent Base64或FileUrl，同步 |
| 依赖/身份 | 必须绑定桶开通CI；子账号ci:CreateAuditingPictureJob；异步另涉cam:PassRole；微信身份非必填 | 开通IMS及CAM权限；不强制绑定COS桶；User/Device可选，微信OpenID不是必填 |
| 8MiB边界 | >5MB需LargeImageDetect=1，最大32MB，附图片处理费；处理后图像与原图的绑定要记录 | FileContent为编码后<10MB；8MiB Base64为11184812字节，超过10MB，即便10MB按10MiB算也超限。要压缩/降低上限或改URL，不是完整8MiB无损直传替代 |
| 费用 | 当前在线表≤300万审核次时1.50元/千次；每场景分别计费，另核处理/读请求等 | 正式后付费25元/万张；3000张/15天试用和具体后付费开通规则以当前控制台条款为准，未领取 |
| 留存 | 已读API没有给供应商全部副本/结果统一删除时限；绑定桶不等于图片必须永久存桶，也不等于供应商不留数据 | FileContent避免自建图片URL，但官方同步API未给零留存保证；StoreUrl等转存能力需保持关闭并另核 |

来源：[CI图片单次审核](https://cloud.tencent.com/document/product/460/37318)、[CI批量审核](https://cloud.tencent.com/document/product/436/119479)、[CI当前计费](https://cloud.tencent.com/document/product/436/58965?lang=zh)、[IMS同步检测](https://cloud.tencent.com/document/product/1125/53273)、[IMS当前计费](https://cloud.tencent.com/document/product/1125/37108)。

用户粘贴的CI“确定/不确定”双价格不能直接用于当前预算。当前在线表以普通内容审核/闲时审核分栏；当前API为1.50元/千次起，按场景累计，并非因结果“不确定”就自动按0.38元/千张。示例：10000张×3场景×0.0015元=45元，未含大图和其他费用。这里是算术示例，不代表已确定选3场景。

## 成本口径与后续准备

| 假设每图一次、不含失败重试/免费额度 | 1000图 | 10000图 |
|---|---:|---:|
| 阿里baselineCheck一种Service | 1.50元 | 15元 |
| 阿里postImageCheck一种Service | 3元 | 30元 |
| CI一种计费场景 | 1.50元 | 15元 |
| IMS正式后付费 | 2.50元 | 25元 |
| 微信mediaCheckAsync | 当前官方单价未核实；另有URL/流量和回调运维 | 同左 |

这些价格是本轮公开页面核验，不是账单或特定账号报价。审核初始请求成功但响应丢失时，业务侧必须先按原key恢复，不用切提供方/换key自动重复送图；DataId/trace_id也不自动意味着供应商幂等免计费。

下一步可以在本地实现不联网的提供方端口及mock契约，把“传输成功/业务失败/明确通过/拒绝/未知/超时/回包丢失”固定成测试。真实接入前由用户选定可接受的数据外发和留存范围，并核对提供方条款/账号资格；现场操作和付费仍另行授权。即使外部审核通过，也仍需共享单队列/目录/owner/取消与迟到结果隔离。

最终采用阿里候选的前提：接受至少30分钟临时图片和独立结果查询边界，明确其余数据处理条件，确认具体Service覆盖范围；如不能接受，则当前不具备“零留存”的已核实候选，继续保持公网OCR关闭，不能退回private_unmoderated试跑。此报告没有修改任何运行开关或原生协议代码。
