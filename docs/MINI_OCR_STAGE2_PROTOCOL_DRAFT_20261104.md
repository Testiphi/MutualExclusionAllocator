# 原生OCR第二阶段协议增补 R1（待评审，2026-11-04）

本文件是 `MINI_API_CONTRACT_20261102.md` 的候选增补，不覆盖第一阶段固定交付，也不表示服务器实现或开启。原路由、Bearer、严格query、multipart、identity与catalog绑定、同key恢复均沿旧协议；仅图片安全相关的候选增补在此明确列出。客户端在双方固定版本前不得猜字段。

## 既有协议保持

| method | `/api/mini/v1` 后路径 | query恰好包含 |
|---|---|---|
| POST | /session | 无 |
| GET | /snapshot | server |
| GET | /map-recognition/catalog | server |
| POST | /map-recognition/jobs | server、catalog_version、request_key |
| GET | /map-recognition/jobs/by-request | server、catalog_version、request_key |
| GET / DELETE | /map-recognition/jobs/{32位hex id} | server、catalog_version |

重复/额外/缺失字段400；OPTIONS/Cookie/Origin403。Global OCR403；账号/B–E、DELETE session和其他路径不开放。上传multipart只有image一份，不把query字段放form；图片8388608、封装8454144字节、16000000像素、静态PNG/JPEG/WebP。目录只由固定CN快照派生，不与正式活动指针混用。

CN catalog_version定义为 `sha256(UTF8(cn_snapshot_version + ':') + 原gauntlet_data.json字节)`，64位小写hex；catalog.version与catalog_version相同，maps按tracks原顺序取大地图/小地图。snapshot的version仍是第一阶段固定快照ID。新增桥必须在两端独立重算并验证相同，不采用“当前正式网站目录”代替。

## 安全处理候选增补

1. 配置disabled时保持第一阶段snapshot=false/null和上传404。提供方未配置、不可用或未验证均不能凭客户端开关宣称map_recognition=true。服务就绪且范围获准后，CN才提供true/64位catalog，Global保持false/null。
2. catalog的既有content_safety字段拟新增值 `required_approval`，意为每图必须经服务端安全门禁，并非当前图片已通过审核。`not_integrated`不能用作本阶段开放依据。此枚举尚未写入运行代码。
3. 不新增客户端任务state：queued涵盖服务端安全处理及等待唯一worker，running只表示CPU OCR实际领取；安全处理未通过不得进入running。内部审核状态不要求客户端轮询另一路径。
4. 完整任务形态保留id/server/catalog_version/state/result/error/expires_at，拟**仅增加** `error_code: null | string`。error仍是可展示的固定中文说明，不能解析其文字控制重试；error_code仅在failed时非空。旧客户端忽略未知字段仍可显示failed并继续手选；支持新版诊断前必须确认适配。
5. 新任务错误码：`IMAGE_SAFETY_REJECTED`（拒绝或需人工复核）、`IMAGE_SAFETY_UNAVAILABLE`（服务失败）、`IMAGE_SAFETY_TIMEOUT`（60秒未得明确通过）。均state=failed/result=null，不自动新key/新会话上传。提供方原始错误/分类详情不透传。
6. 未提交任务前安全服务明确不可用可返回503业务错误 `IMAGE_SAFETY_UNAVAILABLE`，Retry-After:30；响应丢失一律先GET by-request。503不证明没收到图片，也不保证重传安全。若已有任务，恢复原任务和最终failed状态，不重新送审计费。
7. 未完成审核返回既有queued形态，查询同id；请求层错误体仍是schema_version/code/detail。终态任务的错误通过error_code呈现，不把HTTP200的failed误当成功。队列、安全、取消/到期和原key记录必须共用可恢复的单一任务关联。

## 非秘密响应示意

以下为协议示意，**不是公网抓包、可用任务或真实目录**。`${id}`/`${catalog}`/`${expires}`由测试夹具填入；不携带任何凭据或私人图片。另附[有效JSON响应示意](MINI_OCR_STAGE2_RESPONSE_DRAFT_20261104.json)，包含8个完全合成的示例，均未作为真实HTTP证据。

安全处理或排队中（上传202、查询200）：

```json
{"id":"${id}","server":"cn","catalog_version":"${catalog}","state":"queued","result":null,"error":null,"expires_at":"${expires}","error_code":null}
```

`${expires}`在实际协议中必须是Unix秒整数，上面的字符串只是文档占位，不能复制为响应。

| 场景 | 既有或候选返回 | 客户端下一步 |
|---|---|---|
| 成功 / partial / rejected地图布局 | state=succeeded，result.status=complete/partial/rejected，5槽；error_code=null | matched才有当前maps的big/small；unknown/重复/缺图先确认，不覆盖旧图 |
| 安全拒绝或需复核 | HTTP200，state=failed，error_code=IMAGE_SAFETY_REJECTED，result=null | 展示说明并手选，不把它当地图布局rejected |
| 安全服务失败 / 超时 | HTTP200 failed，error_code=IMAGE_SAFETY_UNAVAILABLE/TIMEOUT | 手选；不得自动换key重传 |
| 安全尚未完成 | HTTP200 queued，error_code=null | 查同id，不额外上传 |
| 限流 | HTTP429，code=OCR_LIMITED等既有码，正整数Retry-After | 等待；上传先恢复原key |
| 到期 | HTTP410，code=JOB_EXPIRED | 保留草稿，不自动重传 |
| 取消 | HTTP200 cancelled，result/error/error_code均null | 不应用迟到结果；替图无需等DELETE |
| 上传已提交但响应丢失 | GET by-request recovery=found，附完整任务形态 | 查同id，不重复送审或耗额度 |
| 正在读体 | recovery=reading/retry_same_key=false，Retry-After:2 | 查询原key |
| 读体中断/未找到 | interrupted或not_found/retry_same_key=true | 仅同文件/同目录/同key，仍按原协议，不保证旧请求未到达 |
| 会话到期 | HTTP401 SESSION_EXPIRED | 不换身份接管或重传旧任务 |

所有result只含旧协议允许字段和5槽；不得返回完整OCR原文、图片URL、token/code/OpenID。需要真实成功/部分例子时由获准样图产生，不能把本表示意作为验收证据。

## 必须新增的可执行测试（均未实现/未运行）

| 编号 | 场景 | 必须观察的断言 |
|---|---|---|
| S01 | 缺失审核配置/未知策略/提供方异常 | fail closed，capability关闭，无外发，无worker领取 |
| S02 | 安全审核通过、拒绝、复核、超时 | 只有明确通过可领取；其余failed/result=null/稳定error_code |
| S03 | 替换图像SHA/目录/owner/key/租约/策略版本 | 旧审核回执不能放行 |
| S04 | 待审取消、过期、重启后迟到/重复回调 | 无结果复活，无第二次入队/计费 |
| S05 | 断流发生在接收/登记/送审/入队/响应各阶段 | by-request恢复一致，无双任务/绕额度 |
| Q01 | 网页7任务+原生1任务，及并发第9任务 | 同一个事务容量；审核reservation也占位 |
| Q02 | 同IP网页与原生累计20次，伪造XFF/IP字段 | 第21次拒绝；只信Nginx覆盖的IP |
| Q03 | 同owner2任务、相同key重试/换图 | 第3任务拒绝，原key恢复不二次计数，换图409 |
| I01 | 错误Unix peer UID/socket权限/消息长度/方法/路径 | 拒绝；不能查网页owner、数据库或任意文件 |
| I02 | 访客/桥/worker实际挂载和子进程 | 访客无业务库/队列，桥无业务库/模型；仅唯一worker |
| B01 | 8MiB/总封装+64KiB/16M边界、慢传/半包 | 正确413/422/503；20秒总截止且预算释放 |
| B02 | 旧session4KiB、非OCR路由/错query/method | 不泛化放宽，Cookie/Origin/OPTIONS拒绝 |
| C01 | 固定CN与正式CN版本相同/不同，两服切换 | 独立测试目录一致，正式指针不变，Global永远false/null |
| R01 | 关闭OCR，新上传与既有查/取消并发 | 新上传关闭，收尾窗口可查/取消，session/snapshot手选保持 |
| R02 | 原网站兼容及旧worker面对新表/待审记录 | 待审绝不被旧claim读取，不改业务表/历史任务 |
| P01 | 删除失败/停机/日志/备份/供应商留存 | 不承诺准点删除；无媒体或敏感身份落业务备份/日志 |

验收需保留Windows单测、Linux真socket/沙箱/单worker与实际现场三层不同回执；测试样图和审核mock的许可/模拟性质明确记录。当前只完成既有协议回归，不得将此表标成通过。
