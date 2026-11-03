# 网站侧接手核验与本轮范围建议

2026-11-02。依据 `HANDOFF_WEB_RELEASE_DEV_20261102.md` 接手。本文是本地实查及待确认的范围/契约建议，不是发布批准或已实施的原生接口说明。未操作生产、正式迁移、微信后台、推送或合并。

## 当前事实与证据边界

| 状态 | 内容 |
|---|---|
| 已上线（历史回执） | `repo/docs/CLOUD_HANDOFF.md` 文首及 `MAP_OCR_DEPLOYMENT_RECEIPT_20261031.json` 记录 c06cc48b2b55b7bcec58e68b，源码 f44e3c219bceb185d055b1ae9e5570ed639e2786，旧数据冻结 9e7d21f。用户当时完成桌面/手机微信验收；本轮没有读取生产现场，不能据此断言当前服务状态。 |
| 已实现、未进入该旧包 | 55c9a3e 截图能力说明；4df66bf 替图/取消不等待旧任务；85be28f 统一特殊跑法按钮和选择记忆；406fa4d 按当前区档实际类型显示单跑法名称。保留现有页面、账号/车库语义及成绩表“新功能”标识。 |
| 本地待用户验收 | 上述后续网页改动，以及当前 4504/693 数据组合。历史自动化和浏览器证据不替代本次用户验收；本轮只做 HTTP、数据和自动化核验，没有操作手机或重新执行真实图片 OCR。 |
| 待发布准备 | 尚无包含上述后续功能及 4504/693 的新批准包。维护侧未提交、未重新冻结，源码和发布功能范围也未最终批准。 |
| 共享/原生待开发 | allocator.js、race_scores.js、app_state.js 已支持 CommonJS，profile_store.js 可注入 request/storage；候选生成和规则派生仍在 index.html。没有 `/api/mini/v1` 实现。 |

旧包 SHA256 为 `4a5a318d7ad7d57a8049910593287571068790201888d56b41d9e440ec9e9373`，本轮未重新计算旧归档哈希或修改归档。历史生产国际仍 659、写回关闭，包内 4487/664 未覆盖正式 score-state；均为历史回执口径，不是本轮现场核验。OCR 现场配置历史为 High640M/Max768M，不能拿旧包 1GiB 模板覆盖。

## Git 与现有修改

- 已 fetch origin，`main`、`origin/main` 及 `ls-remote refs/heads/main` 均为 `82492772f7407412c63c973bc5c2e02be87dfba3`。
- 继续复用 `map-layout-parser` / `feature/map-layout-parser`，HEAD `f47ff1982ea0fc266beeaa5bfcf9b73968927ebc`；比提示词的 40217c0 多一条职责交接文档提交。远端未见同名功能分支；本轮不推送。
- 首次检查 22 树；核查期间另一个对话创建 `miniprogram-v1` / `feature/miniprogram-v1`，同基线 f47ff19，首次观察时干净；收尾时已有未跟踪 miniapp 客户端/适配/mock 等文件，说明对方正在开发，不视为本轮交付。最终共 23 个登记树，未操作对方树。
- 主树保留 8 个已跟踪修改和 14 个未跟踪文件：运行数据/两本工作簿、CLOUD_HANDOFF/INDEX、维护与部署回执、用户来源表/脚本及分享表。
- 功能树原有状态显示五份运行 JSON，加 INDEX 与 MINIPROGRAM_COMPATIBILITY 两份其他会话文档；cars.json 的 Git 状态存在，但 diff 无实质内容差异。另四份运行 JSON 有真实差异。本轮不暂存这些文件。
- `unify-home-style` 保留四个未跟踪的 `examples/unlock-table/` 文件；其他树在本轮观察窗口无未忽略修改。所有暂存区为空。忽略的备份、测试状态、模型、旧包等未清理。

逐树 HEAD、完整修改路径和 32 个既有修改文件的 SHA256/大小/mtime 快照见外层 `offline-evaluation/web-takeover-20261102-01/before.json`。恢复预览及验证后这些文件均保持；两份隔离业务库逐表内容摘要均保持。并发开发可能继续产生新改动，实施前须再次核对目标文件。

## 数据与本地预览重现

当前接收源 `repo/docs/DATA_HANDOFF_20261101_OWL_SYNC.md/.json`，机器交接 SHA256 `4096f98430f3c7971df75ef2a9bce8d8a253d68d42380e5bdd1365b8b7e4199b`；接收回执为 `offline-evaluation/data-sync-20261102-01/sync-receipt.json`。

五份运行 JSON 在主树、功能树和既有隔离预览 reference 中，均与接收回执 SHA/大小一致。国服 4504 键/83 图；国际 693 条/47 车/44 图/21OC/52SC，dataset `7e9e8ca61000f8b2426c565fb1d6d9016691642d715a3364ccd7d4acaf7c61ed`。完整维护 732 不复制、不入运行包。本轮没有重新接收/写入运行 JSON 或维护工作簿。

8033 最初无监听、未观察到对应存活进程；本地目录标记有效，OCR 队列仅两个 expired 任务，没有 queued/running。保留原状态，复制既有恢复脚本到本轮证据目录运行，没有重新 provision 或初始化账号。当前预览 `http://127.0.0.1:8033/`，仍使用 `.score-version-sandboxes/9f326b2976b6637b90f07be5`。

恢复后 health 200 / local / OCR ready；首页及两服原子快照 200，国服对象与源相同、国际三件套原始字符串字节 SHA 匹配接收回执。活动版本国服 `b14e088edb0966bb9ac42ec6461c04a6`，国际 `1d4b242418e285aea03a16e5f46d8138`。启动进程/日志见本轮 restored-preview.json 与 preview.*.log，PID 仅为当时证据，不供未来直接启停。

## 本轮验证

- `node --test` 全部 tests/test*.js：127 通过、0 失败，含启动冒烟及页面真实候选与参考算法对照。
- `python -B -X utf8 -m unittest backend.test_map_recognition backend.test_map_layout backend.test_global_static -q`：47 通过。
- `python -B -X utf8 validate_data.py`：0 错误，各档合计 4504。
- 首次后端命令误列了不存在的 `backend.test_global_score_versions`，导致导入错误；保留该失败事实，改用实际存在的 `backend.test_global_static` 后上述 47 项通过，未修改应用代码。
- HTTP/快照与保全机器记录位于外层 `offline-evaluation/web-takeover-20261102-01/`。这些是 Windows 本地验证，未做本轮 Linux、微信开发者工具、手机真机或生产验收。

## 建议本轮范围：先确认契约，再做共享核心

交接要求“先与我确认两个分支的接口契约/文件归属，再接收小程序侧交接单”。因此本轮先完成接手和以下可审阅建议，不先实现新路由或抽取模块。建议下一阶段批准 A；B 待接口细节及小程序需求单确认后执行，C 等维护冻结后再开展。

### A：共享核心抽取及网页等价验证

网站侧归口根目录 allocator.js、race_scores.js、app_state.js、profile_store.js，以及拟新增 `selection_core.js`、网页接线和共享测试。候选/规则只抽取、不改算法、成绩、排序、星级、OC、SC 或地图规则。

拟接口为 `createSelectionCore({cars, data, server, capabilities})`，返回 `carRules()`、`prepareMapCandidates({maps, zone, tier, starsMap, ocMap, scStates})`、`effectiveTime(...)`；最终签名须结合小程序需求单确认，尚不可调用。核心不引用 DOM、wx、网络和存储；maps 保留顺序及 originalIndex，候选输出保留 groups 与 carToPriority 的原顺序/语义。车库过滤、互斥分配继续使用现有模块。

验收使用本轮 SHA 绑定的本地快照，明确标为未冻结；保留抽取前网页作为对照，覆盖国服四/五区各档、无成绩/空候选、星级、SC 全部/指定/关闭、国际 OC/非 OC、并列顺序、缺车与空行。逐项对照候选、方案顺序、每车时间和总成绩，网页原回归继续通过。

小程序侧独占 `miniapp/pages/`、`miniapp/adapters/{request,storage,media,hash,lifecycle}`、小程序配置及客户端测试；不在两树同时改公共核心。`miniapp/shared/` 仅为从固定网站源码生成的产物，不人工维护第二套算法。共享契约和生成清单由双方通过用户协调，收到路径/基线/签名/兼容影响/用例后再改。

### B：原生后端契约（草案，默认关闭）

网站侧归口 `backend/`、后端测试、production 配套模板、构包工具和锁；小程序仅接平台适配。拟定前缀 `/api/mini/v1`：

| 请求 | 约定方向与待固定项 |
|---|---|
| POST /session | wx.login 临时代码由服务端验证，返回短期最低权限访客令牌；仅内存持有。有效期、撤销、签发/可信IP预算及平台错误映射需先固定。不得自动创建/绑定正式网页账号。 |
| GET /snapshot?server=cn\|global | 从同一活动版本原子读取；拟统一返回 schema_version/server/version/files/capabilities，各运行文件携带原始 UTF-8 内容与 SHA/大小。现网页国服接口只返回解析对象，不能把其重序列化当原始字节；新适配须从版本存储读取原内容，不改旧客户端格式。精确字段和编码在实现前固定。 |
| GET /map-recognition/catalog?server=cn | 复用活动目录/版本；识图首版仅国服中文游戏截图，国际手选/计算保持。 |
| POST /map-recognition/jobs | 精确路由接收一张 multipart 图片，绑定访客、server、catalog_version、request_key。沿用单图 8MiB/16M 像素，拟请求封装最多额外 64KiB；文件/字段数量和长度逐项限定，先鉴权/预算再有界读取。字段位置和错误码待固定。 |
| GET/DELETE /map-recognition/jobs/{id} | 共用任务状态、五槽结果、版本绑定、取消/到期/超时；保留现有 state/result 语义，限定本会话所有权。过期后不静默换身份重复上传，草稿不丢失。 |

保持网页 Cookie/Origin/CSRF/raw 图片上传限制；禁止全局放宽 Origin 或 multipart。AppID/Referer 不作为身份，AppSecret/session_key 不进客户端。网页与原生复用唯一私有队列/模型，owner 命名空间隔离且共享全局额度，不能分别增加一套并发配额。

新访客会话状态拟独立存储，不修改正式账号表、不自动迁移或合并 user_id；实施前先写清文件归属、schema、TTL/撤销、备份及升级/回退边界，临时测试状态验证。Nginx、环境项和状态目录变化须成套列明；默认关闭、旧网页客户端兼容均须回归。

图片用途、访问/保留/删除与内容安全策略仍有待落实项，OCR 不当审核服务；不得把未接入的微信/外部安全服务填写成已实施，不自行外送媒体或配置后台。

### C：发布包准备门槛

构包前由用户批准具体功能范围和源码提交，维护侧提供重新冻结的五份运行 JSON 来源与逐文件校验且确认不再变化；代码与数据分别固定。禁止用旧 9e7d21f 冻结绑定 4504/693，也不代维护侧提交。

届时使用独立干净检出，复用 build_production.py / production_release_tools.py，按实际新增依赖更新锁/严格白名单。产物包含运行文件、Linux 离线依赖/模型来源、版本、完整逐文件与整包 SHA、部署/配置/执行顺序/回退说明；排除账号/成绩/反馈库、凭据、照片队列、测试数据、工作簿及完整维护。现有 score-state 不被应用包 JSON 覆盖。正式成绩导入另交运维按现场版本/差异与授权执行。

## 本轮收尾

仅新增本文及外层本轮证据目录；本地预览保持运行便于用户检查。没有功能代码修改、Git 暂存/提交/推送、构包、合并、工作簿同步、生产访问/写入、正式迁移、上线、公告、清理或监控。A/B 的接口与文件归属待用户确认及小程序需求单；C 仍缺重新冻结和批准的源码/功能范围。

## 用户确认后的 A 阶段实施

上节是首次只读接手收尾的历史状态。用户随后确认按建议顺序推进；现已完成 selection_core.js 抽取、网页委托、静态与发布白名单接线及216组真实数据配置对照，并按小程序新协调清单补齐 createSelectionContext/getModel/calculate。详细接口、职责、131项前端/326项Python（1跳过）及后续14项发布工具验证见 [共享核心交付契约](SHARED_SELECTION_CONTRACT_20261102.md)。本阶段只在网站树本地提交自有代码/测试/交接，不推送、不合并、不代提交数据或他人文档；实际提交回执写在外层 web-core-20261102-01。原生网络接口仍未实现，接下来需按契约落实会话/错误/恢复及图片安全边界；数据冻结、构包及各类现场验收仍待完成。
