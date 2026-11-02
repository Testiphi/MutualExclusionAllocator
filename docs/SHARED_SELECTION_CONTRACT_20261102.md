# 网站 → 小程序：共享选择核心交付与原生接口边界

2026-11-02。用户确认网站侧先固定契约、再抽取核心的顺序。本文件与本轮源码提交共同交付；未向其他对话发任务，未修改小程序工作树。本轮从磁盘读取了小程序侧 `docs/MINIPROGRAM_CROSS_BRANCH_REQUESTS_20261102.md` 提案，按其首个依赖补齐高层端口。网络契约仍是下一阶段实现依据，尚无原生路由或真实会话/OCR接入。

## 文件归属

- 网站侧：根 `selection_core.js`、allocator.js、race_scores.js、app_state.js、profile_store.js、网页接线、共享对照测试、backend/**、发布工具/模板。
- 小程序侧：miniapp 页面、request/storage/media/hash/id/lifecycle 适配、客户端 controller/service、tools/prepare_miniapp.cjs 及专属测试/文档。
- miniapp/shared 为生成副本。小程序侧将 selection_core.js 加入生成清单，并从固定的网站源码提交取五个共享模块（另有 profile_store.js），逐文件记录 SHA/大小；不得长期人工维护第二套算法。不要直接从网站 dirty 树无校验复制数据或源码。
- 后续公共文件改动继续通过路径、源码基线、签名/DTO、兼容影响、验收用例交接，避免两个工作树同时改公共文件。

## 已实施的纯核心契约

`require('./selection_core.js')` 返回以下端口；浏览器对应全局词法变量 `selectionCore`，依赖加载顺序为 app_state.js、allocator.js、race_scores.js、selection_core.js。共享模块不调用 DOM、wx、网络或存储。

### 高层端口：对应小程序现有桥接

```js
const context = selectionCore.createSelectionContext({
  server: 'cn',       // cn | global；不能混服或隐式回退
  version: '活动版本ID',
  cars: carsObject,   // 已验证的 cars.json / cars.global.json 解析对象
  data: scoresObject // 同一原子快照的成绩解析对象
});
const model = context.getModel(draft);
const result = context.calculate(draft);
```

快照字节校验、缓存事务、服别/版本绑定由客户端快照适配执行；核心接收解析对象不是网络真实性证明。国际 manifest 仍必须先在适配层校验，本模块不取代原始字节 SHA 检查。

`draft` 与小程序提案一致：`{schema:1,server,zone,tier,maps,cars,stars,oc,routes}`。maps 恰好五槽，元素为 null 或 `{big,small}`；`{big,small:''}` 可作为编辑中状态而不参与求解。完整地图必须在当前目录且大地图不重复，非法输入报错。cars 为昵称 ID 数组，合法空车库保留为空；未知/不在当前区车池的车由既有 garage 边界过滤。stars/oc/routes 为映射，省略时空映射；核心不修改草稿或快照。

`getModel` 返回 `server,version,zones,tiers,maps,cars,routes`：

- maps 为当前目录原顺序的 `{big,small}`。
- cars 按当前区车池顺序返回 `{id,label,stars,defaultStar,ocAllowed}`。label 当前为昵称；stars 为该区允许整数数组，国际仅满星；defaultStar 为原网页同区无用户覆盖时的有效值。OC 只对国际运行数据实际存在 OC 的车型开放。
- routes 仅为已选完整地图、当前区档有 SC 的控件，字段 `{key,label,types}`。单类型 label 使用实际类型；多类型 types 保持数据出现顺序，“全部/关闭”是控件状态，不是新增 SC 类型。

`calculate` 同步返回 `{schemes}`，最多 25 个方案，顺序沿用原分配器：

```js
{ schemes: [{
  rows: [{map: '小地图名或空串', car: '昵称或null', time: 23.2 /*或null*/}], // 恰好5行
  assignment: ['昵称或null'], // 恰好5槽
  vector: [0 /*原优先级；已选地图缺车为99，未选槽为null*/], // 恰好5槽
  prioritySum: 0,
  total: null
}] }
```

没有完整地图时 schemes=[]。部分选图/缺车/任一行无成绩时 total=null；仅五行均分配且有成绩才求秒数之和，不额外取整，展示层自行格式化。不能把未知成绩当0。`prioritySum` 是网页原有 Σ 优先级分，与秒数 total 是不同字段；网页原界面和排序继续按优先级处理，没有把秒数总和改成排序依据。

低层端口 `createSelectionCore({cars,data,server})` 返回 `carRules()`、`prepareMapCandidates({maps,zone,tier,starsMap,ocMap,scStates})` 与 `effectiveTime({big,small,car,zone,tier,starsMap,ocMap,scStates})`。候选输出每图 `{groups,carToPriority:Map}`，地图顺序保留；已选车过滤在分配器执行，不重新压缩优先级。测试/适配可直接对照完整候选。

另导出 carRules、starRange、carStars、originalGroups 和 prepareMapCandidates 低层函数供网页委托；UI 内状态/存储/调度不进入核心。国际仅 zone5/理论，其他区档明确报错；无成绩不借其他区档，OC/SC/星级估算继续委托 race_scores.js。

## 对小程序侧的具体接收项

现有 `miniapp/services/selection.js` 检查 createSelectionContext 并委托 getModel/calculate，可按上述 DTO 接线。真实快照适配需输出 `{server,version,cars,data}`，先验证所有原始字节及服别/版本再交核心；只有核验通过才替换原子缓存。把 mock 模式与实际共享核心计算分别记录，不能将 mock 结果算成真实计算或 OCR 验收。

本轮不改对方生成器、controller 或页面。请由用户协调将本文件和网站提交交给小程序侧；接收方在独立树更新生成清单及契约测试，回传源码/数据 SHA、差异和失败用例。这个交接不要求重新批准已经授权的核心开发。

## 原生网络接口：下一阶段准备，未实现

路径继续使用 `/api/mini/v1`，默认关闭，保留网页 Cookie/Origin/CSRF/raw 图片上传。以下字段按两侧清单对齐，服务端实现前还需固定会话/错误/恢复细节：

| 路由 | 接线方向 |
|---|---|
| POST /session | `{code,client_schema:1,request_key}` → 内存用最低权限访客 token/expires_at。不创建网页账号或自动绑定 user_id。 |
| GET /snapshot?server=cn或global | Bearer；返回 server/version/capabilities/files。建议 files 为原始 UTF-8 文件文本封装，逐份 SHA/字节数；客户端解码文本后重新编码 UTF-8校验文件字节，不把整个 JSON 封装/压缩传输字节当文件，不重序列化解析对象。国服两文件、国际三文件，单次活动版本原子读取；不能跨服回退。 |
| GET /map-recognition/catalog?server=cn | 同活动目录/版本，只开放中文国服截图。国际手选计算保持。 |
| POST /map-recognition/jobs | multipart 单文件字段 image；server/catalog_version/request_key；文件≤8MiB、≤16M像素，总请求拟≤8MiB+64KiB。先鉴权/预算再有界读取，精确路由限制文件/字段数及长度。 |
| GET/DELETE /map-recognition/jobs/{id} | 同 owner、服别、目录版本绑定，保留五槽及原 state/result 语义。取消幂等且客户端不等待取消响应才能替图；继续受原硬截止管理。 |

实施前需写清：code 重用与响应丢失、token TTL/撤销/预算/存储 schema、跨会话拒绝、request_key 幂等/恢复查询、401/403/409/410/413/415/429/503 与 Retry-After、到期及目录变化后的恢复。原生 owner 独立命名空间，网页/原生共享唯一队列、模型和全局配额，不能再开另一套容量。不得将 AppID/Referer 当身份，或向客户端泄漏 AppSecret/session_key。

原生会话拟独立状态，不改正式账号结构、不自动迁移。Nginx、默认关闭配置、独立状态目录、兼容/回退和精确上传大小需要成套落地；真实平台验证另需实际 AppID/服务器配置及平台权限。图片安全策略仍待实际实施，OCR不是安全审核，不自行外送媒体、开户、付费或操作后台。

## 验证、数据与发布边界

本轮对照基线为 f47ff1982ea0fc266beeaa5bfcf9b73968927ebc 抽取前页面函数，保存在 `tests/fixtures/selection_page_reference.cjs`，仅作测试参考，不入运行白名单。对照覆盖当前国服所有83图、国际44图、两区各档、混合/损坏星级、OC开关、全部/关闭/指定/失效跑法，共216组配置；逐项核对全部候选、每车成绩、方案顺序/向量/五槽/总成绩和输入不变性，另覆盖部分选图、空车库及河畔漂移高手标签。

前端最终131项通过；Python全量326项执行/325通过/1跳过（Windows平台限制）。之后发布工具补充旧包兼容检查，发布/OCR相关14项通过。全部是Windows本地验证，未进行本轮Linux、开发者工具、手机真机、真实原生会话或真实原生OCR验收。

证据 `offline-evaluation/web-core-20261102-01/`。8033预览已在确认归属/无未完成任务后，仅停止本轮持有的旧worker与父进程并恢复；health local/ready、新核心200且字节匹配，两服快照200且与接手时响应哈希相同，“新功能”保留。没有重建账号或版本状态。

数据仍来自 DATA_HANDOFF_20261101_OWL_SYNC / 接收回执，国服4504、国际693，未提交/未重新冻结；国际dataset `7e9e8ca61000f8b2426c565fb1d6d9016691642d715a3364ccd7d4acaf7c61ed`。本轮源码提交不包括运行JSON、他人INDEX/兼容文档、工作簿、账号/成绩/反馈/备份/测试状态或小程序文件。构包仍需批准源码/功能并接收维护侧新冻结，在独立干净检出执行；不沿用旧冻结、不覆盖正式score-state。
