# B：成绩表、权益与直达

依赖 MINI_FEATURES_COMMON_20261103.md 与固定OpenAPI。路径相对 `/api/mini/account/v1`。

| 方法/路径 | 输入 | 响应 |
|---|---|---|
| GET /coverage | query server=cn/global；zone=五区/四区；tier=理论/高手；big=all或地图id；route=normal/special；q≤80；stars=all/1..6；offset=0..5000；gaps=false；oc=false | 下述覆盖矩阵 |
| POST /coverage/view | 同字段JSON，另star_map:{昵称:整数1..6}≤200；只读，无幂等头要求 | 相同覆盖矩阵 |
| POST /coverage/choice | 账号；JSON server,map_id(24位hex)；幂等头 | {chosen:map_id}；仅一级权益可首选，每服独立、不可自行换图 |

Global仍仅五区理论；OC仅Global允许，不能回退国服。网页表格也补OC选择器，默认非OC与旧客户端一致。OC与普通分别统计/排序/构造target键；无OC不借用普通成绩。

响应：columns、rows、column_total、column_offset、column_limit=48、oc、provenance，另version/server/production/access/user_id/rules/capabilities/maps/source_snapshot。

- columns每项car/title/stars/max_stars/star_options/coverage_count/public；理论stars=null，高手选择按当前车辆区档上限校验。参考列先于其他列，再覆盖数、昵称casefold排序；q/翻页/星级不改变原固定参考选取规则。
- rows每项big/small/route/map_id/cells。cells有key、status(empty/filled)、value(数字秒或null)、public、target、value_source(runtime_dataset/missing)、calculation=none、visibility(public/unlocked/locked)，必要时mine={id,status}。
- target含big/small/zone/tier/car/stars/route；Global另server=global/oc。CN旧target/key保持兼容。
- filled且value=null为未解锁，不是无数据；empty为该身份/星级/跑法无收录。public列可见，其他由服务端access判定。
- access={level,points,valid,high,chosen,admin}；两服共积分但一级chosen分服。level1需50分/5有效，level2需150分/15有效/5高质量；质量≥6有效、≥8高质量；管理角色按原规则。不得客户端造积分/权益。
- maps=[{id,name}]；rules含当前版本/门槛，capabilities为该服真实能力。source_snapshot={server,version,sha256:{文件名:SHA}}来自同一活动版本，读取前后变化409 SNAPSHOT_CHANGED。旧version语义保留：CN活动id，Global dataset id；不要混作source_snapshot.version。

表格不做插值/外推；calculation=none不代表每条数据都是独立实测。运行投影没有完整维护来源台账，provenance如实标明；禁止补造实测/估算标签。主页星级估算与单图前三继续由原race_scores/selection_core及新home_presenter输出，参数不改。

直达使用结构化target、server及cell.key：成绩表pick是选中格key，big是maps.id，投稿prefill是当前目录绑定target，不携带猜测成绩/备注。主页“新功能”标识保留。客户端原生路由自行映射，不能把网页URL放web-view或把旧Cookie路径当Bearer入口。

同账号/两服/区档/星级/OC/SC对照网页；匿名/访客只取公开参考，普通未达标不会取得隐藏时间；管理员/超管的真实服务器权益与网页相同。选择失败/降级/版本变化保留输入，重新读取access，不靠隐藏按钮授权。
