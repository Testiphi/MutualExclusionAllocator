# DOM无关主页presenter与原主题导出

本批正式新增home_presenter.js/home_theme.json，既有五模块仍固定198999a原Git blob。网页index仅委托搜索、车型筛选、排序、单图前三、副标题等呈现；算法/候选/时间/OC/SC继续调用selection_core/race_scores/allocator/app_state。未改CSS设计值或自然宽度车签。

CommonJS：`require('./home_presenter.js').createHomePresenter({server,version,cars,data})`；snapshot为已校验原子快照解析对象。`present(draft,filters)`纯同步、无DOM/wx/网络/存储。

draft沿A前共享契约：{schema:1,server,zone,tier,maps:恰好五槽null或{big,small},cars:[昵称],stars:{昵称:整数},oc:{昵称:boolean},routes:{大/小:off/all/sc_type}}。filters={query:'',class:null或S/A/B/C/D/R,sort:alpha/score-desc/score-asc}。

输出：subtitle、visibleCars（当前区/筛选/原排序的昵称序列）、references（恰好5槽，每槽前三[{car,stars,score}]，空/部分地图保留空数组）、model（共享选择上下文的目录/车池/跑法）、schemes（原完整顺序的五槽rows/assignment/vector/total/prioritySum，另summary）、emptyState（未完整选图时“请先选择地图”，真正无方案时“无可分配方案”，其余null）。无车不产生假成绩，summary的Σ是优先级分，不是总秒数。数据可能包含估算/迁移来源，presenter不补造独立实测标签。

另导出aliases、initialTier(server)、filterBySearch(list,query,{nickToName,aliases})、filterByClass/sortCarList的显式lookup接口、getTopCars(candidate,owned,{tier,starsFor,scoreFor})、subtitle、schemeSummary。DOM/WXML渲染这些结果，不抄第二套筛选/估算规则。CN默认高手、Global默认理论；别名从原页面移入同一模块，网页也引用它。

home_theme.json包含tokens、每份原CSS全文及UTF-8/LF规范化SHA/长度、按原顺序的selector/conditions/declarations。sources包括theme/styles/ui/accounts/map_recognition.css，保留背景/颜色/按钮/间距/响应式条件和flex换行的自然车签宽度；不把CSS“翻译”成新的固定网格。源码Git blob/实际制品SHA另外随交付记录，规范化CSS哈希不冒充平台换行后的原文件字节SHA。

生成器 `python -B -X utf8 tools/export_home_theme.py`；`--check`拒绝过期产物/关键selector漂移。主题不手改第二份；客户端可由同一声明生成WXSS映射并记录生成SHA。本轮不操作小程序树，接收方在原tools/web_home_adapter迁移时把新模块/主题及依赖加入固定来源清单，保留旧提取器/证据，结构变更先拒绝而不猜。

测试保留a38faaf抽取前页面函数作为只读oracle，对两服/区档/搜索/排序/类筛选等405组组合比对车序、副标题、单图前三与方案摘要；同snapshot/draft输入不变。浏览器/Node测试不等于WX引擎Locale排序/真机性能证明，接收方仍跑同输入对照与iOS/Android验收。
