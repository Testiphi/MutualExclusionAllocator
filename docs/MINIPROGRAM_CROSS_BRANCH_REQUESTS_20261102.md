# 小程序 → 网站分支协调清单

2026-11-02。本清单交用户协调，未向其他对话发任务。以下签名/DTO是待确认提案，不是现存协议。基线为网站 `f47ff1982ea0fc266beeaa5bfcf9b73968927ebc`。本轮仅新增 `miniapp/**`、`tools/prepare_miniapp.cjs`、`tests/test_miniapp.cjs` 和小程序专属交接文档，未改公共源码、后端、原方案、INDEX 或兼容文档。

## 1. 共享选择模块（首个依赖）

网站归口：建议新增根 `selection_core.js` 及其网页接线/对照测试；实际名称由用户协调确认。相关基线位置为 `index.html:218 buildCarRules`、`getOriginalGroups`、`prepareMapCandidates`、`mapSchemesToRows`、成绩显示/特殊跑法和 OC 逻辑。`allocator.js`、`race_scores.js`、`app_state.js`、`profile_store.js` 仍由网站归口。

建议同步无 DOM 端口：

```js
createSelectionContext(snapshot) => {
  getModel(draft) => model,
  calculate(draft) => { schemes: [{ rows: [{map, car, time}], total }] }
}
```

`draft`：`{schema:1,server:'cn'|'global',zone:'zone5'|'zone4',tier,maps:[null|{big,small}] /*恰好5槽*/,cars:[id],stars:{[id]:number},oc:{[id]:boolean},routes:{[big+'/'+small]:'off'|'all'|sc_type}}`。界面正在编辑的地图可能为 `{big,small:''}`，核心只计算完整地图；不得将未填槽压缩后丢失原位置。车库允许合法空数组。客户端不派生或改变车池、星级上限、成绩估算、映射、路线或 OC 规则。

`model` 建议含：`server, version, zones, tiers, maps:[{big,small}], cars:[{id,label,stars:[允许值],defaultStar,ocAllowed}], routes:[{key,label,types:[sc_type]}]`。它应由同一活动数据和共享规则派生；不将缺失能力默认为另一个服。路线控件后续消费此列表，客户端不扫描成绩生成自己的跑法规则。

`calculate` 必须返回全五行位置、空缺、各车成绩与总成绩，保持候选与方案稳定顺序；可附带完整候选和优先级向量供对照。普通/高手没有成绩时不借用其他档；普通与 OC、不同 SC 不混算。`time/total:null` 是无成绩，不能用 0 伪装。建议测试接口单独暴露候选以便对照，结果 UI DTO 不反向决定算法。

验收：使用同一批准快照、地图次序、车库、星级、OC、SC 输入，对照抽取前网页与新模块的**全部候选、完整方案顺序、各车/总成绩、空缺位置**。覆盖国服四/五区及四档、河畔漂移/地心探险多跑法、缺成绩/空车库/稀缺车辆和国际满星理论/OC。不能只比较第一条方案或算法单测。本分支桥接见 `miniapp/services/selection.js`，目前未启用。

## 2. 原生访客与快照

网站归口 `backend/app.py` 及新的原生入口模块/会话存储；保留网页 Cookie/Origin/CSRF，默认关闭原生入口。建议沿方案 `/api/mini/v1` 前缀，具体字段待确认：

| 方法/路径 | 请求 | 响应与约束 |
|---|---|---|
| POST `/session` | `{code,client_schema:1,request_key}`；wx.login 临时代码 | 内存使用的最低权限 token、expires_at；不注册网页账号；过期、撤销、限流与同码重试语义明确 |
| GET `/snapshot?server=cn\|global` | Bearer token | server、version、capabilities、原始字节文件与 SHA/字节数；两服均原子返回，错误不能回退另一服 |
| GET `/map-recognition/catalog?server=cn` | token | 与同一活动快照绑定的目录及 catalog_version，仅开放 CN 中文截图 |

需协调快照究竟以 ArrayBuffer 文件还是 JSON 封装 UTF-8 文本传输、文件清单和版本一致性校验规则。明确 HTTP Content-Encoding 处理后客户端应校验的字节，不把重序列化 JSON 当原文件。本分支提供 UTF-8/SHA 和 `wx.request(responseType:'arraybuffer')` 低层适配；**原子缓存/真实会话尚未实现**，等确定契约后接入。AppSecret/session_key 只在服务端。原生 owner 命名空间独立，不复制正式账号库或自动绑定 user_id。

## 3. 上传、查询和取消

| 方法/路径（拟） | 需固定字段和行为 |
|---|---|
| POST `/map-recognition/jobs` | multipart 单文件字段名（建议 `image`）、server、catalog_version、request_key；先鉴权/限额再读取，文件≤8MiB，封装总量有界；委托既有同一队列/worker |
| GET `/map-recognition/jobs/{id}` | 返回 server/catalog_version、五槽状态、job状态、到期时间；歧义留空；只允许原 owner；不返回无关 OCR 原文 |
| DELETE 同路径 | 幂等取消；用户退出/替图不等待取消响应才继续；原任务仍受硬截止管理 |

明确 queued/running/succeeded/failed/cancelled/expired、401/403/409/410/413/415/429/503 和 Retry-After，任务归属/版本过期后恢复方式。定义上传响应丢失时按同一 request_key 查询或安全重试的方式，不能直接新建任务。隐藏后不重复上传；显示后重新验证会话/目录并查询已有任务；会话失效且不允许取回旧任务时保留手选/车库。最终真实任务恢复需按确认契约实现，本轮没有用 mock 代验。

网页 raw-body 和原生 multipart 保持独立精确路由，不全局放宽请求大小/Origin。配额共享全局容量，不能网页/小程序各分一组后突破上限。Nginx、默认关闭环境配置、会话/任务所有权、限流/取消和回退由网站/运维归口；本分支不操作生产。

## 4. 图片安全与平台前置

需要用户协调：AppID/主体、审核实际状态、开发者和体验成员权限、隔离后端 URL、request/upload 域名与 TLS、隐私声明、图片安全处理策略、iOS/Android 设备、批准数据冻结。本轮不需 AppSecret。真实服务接入时才索取必要客户端资料，不猜测凭据。

首版图片输入仅为私有中文游戏截图；本机预览后用户点识别才发起上传，无公共图库，不扫描相册、不拍照、不上传第三方。本地 mock 实际不上传。真实服务拟复用现有1小时到期/元数据另留10分钟的策略，但必须由服务端确认原生入口也落实，停机时不保证准点清理。需确定原图访问者、失败/取消清理、备份排除及安全检查时点/异常处理。现有 OCR/格式校验不是内容安全服务，未接入微信图片安全API，不能勾填已接入；外部服务传图或付费须另行决定。

小程序仍不开放账号绑定/云同步、投稿/昵称/反馈附件、视频/音频/支付/通知或国际识图。后续扩大入口再评估声明，不能把本轮协调清单当作平台批准或上线授权。
