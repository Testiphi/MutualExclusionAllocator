# RacePick 云端运维交接（2026-10-24 更新）

## 2026-10-24 最新：599条更新已提交推送，完整发布包就绪，尚未部署

本轮代码/数据提交a0298cd25da9cbf46a9909d7e5b3723e82adea8f已推送main，git ls-remote核对一致；随后本段交接记录单独提交，不改变发布包源码绑定。构建使用新的干净独立检出release-build-global599-20261024，旧release-build-20261024和旧交付包均保留。原未跟踪源表、shared工作簿和_star_curve_fit.py未加入提交或打包。

- 新发布ID：0ee524e31734b44fb7771b79；目标Ubuntu24.04/x86_64/Python3.12。
- 本地交付目录：repo/.production-build/delivery-20261024-global599，14文件，SHA256SUMS.txt覆盖其余13文件。
- 完整上传归档：repo/.production-build/RacePick-International599-20261024-0ee524e3-delivery.zip，10929698字节；SHA256：85ee2e8e26045b51f4b67dbbb439dfda21ce95d0673b1ddc4da57f84cde9c448，旁有.sha256.txt。
- 内层应用ZIP：racepick-accounts-release.zip，10858488字节；SHA256：b39d06f2cec0de56f09be985222921139ed35c8da25174be3ec15ae29220f29d；85个manifest文件，含19个锁定离线依赖。
- source/data provenance均绑定a0298cd25da9cbf46a9909d7e5b3723e82adea8f；三份国际JSON及国服两份JSON逐字节等于已提交内容，其余文本仅有Windows检出行尾差异，已逐项规范化回比。相较上一发布包仅PRODUCTION_DEPLOYMENT.md、三份global JSON、index.html、styles.css、tools/build_global_data.py改变；账号/成绩/贡献/反馈运行代码和两份国服JSON均与旧包一致。

发布范围仅五区满星理论599（578非OC+21OC，561普通路线+38特殊），49车、44图42有值，数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。包内其他区档为空，无显式低星成绩；四区11理论、两区三星高手、2个普通镜像、36参考记录、614键完整维护JSON/台账与所有Excel均未打包。包内国服JSON与上一发布包字节一致，不额外发布国服成绩；更不能覆盖服务器score-state。没有数据库/账号/凭据/反馈/候选/测试数据或未跟踪文件。

本轮验证：JavaScript81通过；Python214执行、213通过、1个Linux专用检查在Windows跳过。完整维护614键/运行599键隔离核对、原434来源与旧发布包哈希、85文件/19wheel锁定哈希、外层13SHA与14文件归档回读均通过。用交付目录内独立deploy_production.py在本地新目录暂存成功，未激活；解包程序production/selfcheck.py以Windows临时数据库通过HTTP、备份/恢复和组件自检，不发邮件、不用现有用户库；19wheel按Linux CPython3.12标签离线解析成功并逐哈希相等。PACKAGE_VERIFICATION.json/RELEASE.json保存可独立核验结果。Linux原生安装/正式库现场兼容性仍待用户上传后执行，不冒充已在Linux或生产运行。

本轮没有登录/读取/修改生产服务器，也没有运行迁移、初始化、切换或清理。最后已知生产仍为用户此前验收的bd12e3fb2c2519b0238afd90；其PID、健康、成绩版本、备份调度和公网情况须部署时先只读重核。下一轮用户开始部署后，再逐步给命令、等待回传核对，不能直接续跑旧部署步骤。国服原表/目录、源工作簿、614维护数据、OC、36参考、旧包/备份/演练/测试数据保持。原完整工作树只保留3个既存未跟踪文件；不clean/reset或自动同步工作簿。


## 2026-10-24 本轮599条国际服更新：提交与完整发布包准备

用户已授权提交推送本轮更新并准备完整可校验发布包，明确暂不操作服务器。发布仍严格限定国际服五区满星理论：599条＝578非OC＋21OC，561普通路线/38特殊，49辆可计算车，44图42有值，富士最后两图空。数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。维护侧完整JSON/台账/现有Excel的614键及36条高手参考均保留；四区11理论、两区三星高手和普通可用镜像只用于维护，不装入运行包。Git跟踪的Excel可以提交，但发布白名单排除所有工作簿、完整维护JSON/台账、候选、真实账号/成绩库、凭据和测试数据。

与最后验收的bd12e3fb2c2519b0238afd90相比，待发布内容还包含此前已提交未上线的三行分组布局与c2“兔子”别名，本轮国际服隐藏R级占位、已授权OC估算来源绑定及国际数据维护成果。国服已跟踪数据/原表未改；包内国服基线来自已提交版本，不能覆盖线上独立score-state，不导入本地成绩或重跑迁移。

fetch后main与origin/main同为4d261611f666685bb865dd81cc83e5ad9ea9697a，无新远端变更，无需合并。发布前JavaScript81项通过，Python214项运行/213通过/1项Linux专用跳过；完整维护614键、运行投影599键、manifest哈希与纯生成器校验均通过。复用build_production.py和19个哈希锁定的Ubuntu24.04/x86_64/Python3.12离线wheel，从本轮提交的干净检出构建。具体源码提交、发布ID、包哈希和独立验证结果以本轮RELEASE.json与PACKAGE_VERIFICATION.json为准；旧包不覆盖。

最后已知生产部署为用户此前验收的bd12e3fb2c2519b0238afd90（321条国际数据），成绩版本42d62fde9b81197ac0558087a9a25f97。本轮未登录服务器或重新核验线上，不把历史PID/备份调度时间当现场状态。以后部署仍先给只读核验命令，由用户执行回传逐步核对，再暂存/安装运行环境/成套备份演练/切换/恢复调度/公网验收；不初始化、重复迁移、覆盖服务器成绩或清理旧版本、备份和演练目录。


## 2026-10-24 最新整体核对通过：614维护键／599运行键

按用户要求整体复核，完整维护JSON gauntlet_data_international_maintenance.json＝现有Excel标准12表＝maintenance-score-ledger.json，614完整键，612条有秒数+2个普通可用镜像，无重复/缺漏/多出。五区理论599、高手1、普通镜像1、自动0；四区理论11、高手1、普通镜像1、自动0。原13页独立高手参考36行与参考JSON逐格一致，不计614活动键。

gauntlet_data_international.json＝score-ledger.json＝运行gauntlet_data.global.json＝完整维护五区理论子集，599键，578非OC+21OC、561普通路线+38特殊，49辆可计算车（维护身份55），44图42覆盖。全部四区/高手/普通镜像不在运行数据；运行目录仅五区满星规则。直接将完整维护JSON作为构建输入会以“International phase one supports only five-zone theory”拒绝，前端config仍仅加载独立运行三文件，不读取维护表。21OC来源与运行值、两区三星高手/普通镜像、Fordo11四区副本星级/满改分均独立核验。

本批已入库数据当前等待用户决定0项，玻璃破冰者31.85已通过二审。共享表原214唯一标记来源未导入：208待核/参考+6原版已作废，208中分类跑法121、星级27、四区参考52、版本61、离群2，相互重叠不能相加。早期7暂缓另按原授权保留，未与214合并去重，不编造总数。已接受的20EVO配置缺失、4EVO性能参数待补、12玻璃参数差异、Fordo视频星级未逐车复看均继续保留证据限制，不重新当作待用户审批。富士极速列车/乡间冲刺仍空。

发现维护指针现状文案残留Bolide ice pending、439及旧600条描述，已仅更正元数据文字，刷新manifest的current-maintenance来源哈希；运行两份JSON、成绩/台账/Excel及国服/代码字节mtime保持，dataset_version仍f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。26项回归（Node14/Python12）、生成器--check、原434来源及旧发布包校验通过。完整回执、各档位与未导入清单在maintenance/overall-reconciliation-20261024，报告国际服整体核对与待核清单.html；改前指针/manifest备份change-history同名目录。仅本地核对和审核状态维护，未提交推送、打包、上线或操作服务器。


## 2026-10-24 最新本地：爱音E三星高手／Fordo四区理论／EVO保留

用户本轮授权：爱音E移五区和四区高手并标三星；玻璃除破冰者二审外接受；EVO仅严重落后同图平均才删；Fordo星级核验后可保留五区并加四区理论。

爱音E偏离中心从五区理论撤下33.85，原值保留写入五区/四区高手，cars.stars=3，未再加减。源表6星标注、原始33.8与配置4102/480/84.18/39.97/18.33完整保留；三星是用户明确纠正，不伪造为原表实证。沿用数据模型给高手各加1个普通可用镜像（无新秒数）。四区车池身份按授权增加爱音E，zone4Max3，不套国服上限。

Fordo11条涉及ap0、阿波罗n、avj、迈凯伦p1、叶问、小牛（5星）及自私（6星），源配置星级与各自目录满改参数一致，性能分3946/4047/4133/3602/3929/4109/4213均≤国际4400。保留五区理论并复制原已接受值至四区理论，普通路线；星级核验是表内星级+满改参数交叉，不声称逐车视频星级画面认证。11项来源、星级/性能分与视频归属见accepted-tier-review-20261024/fordo-star-proof11.json。

20条EVO对照同图其他非OC、非SC普通理论，参照中排除被评估的全部20条，避免自证。每图有9–23左右参照；严重落后判断为同时≥2秒且≥10%，实际最慢仅evo女武神巴黎圣母院20.95对均值20.74706，+0.20294秒/+0.97817%，全部保留，0删除。玻璃其他11条标记用户已接受参数冲突；破冰者31.85未动，单列二审，原31.8、旧32.13、未知作者/无链接、5190分但加速/氮气冲突等见玻璃破冰者二次审核.html。国服同车同图31.20只是参数不同的参照，没有迁移。

重要维护边界：完整维护入口新增maintenance/gauntlet_data_international_maintenance.json与maintenance-score-ledger.json，614完整键＝五区理论599+四区理论11+两区高手各1+各自普通可用镜像1，其中有秒数612。现有gauntlet_data.global.xlsx标准12表与这份完整维护JSON/台账614键一致，原独立36条高手参考页仍不计入活动键，字节数据保持。以后核对维护Excel要用current-maintenance.json的authoritative_maintenance_json/workbook_validation_json，不应再直接与运行投影相比。

gauntlet_data_international.json/score-ledger.json继续作为已验证生成器的运行投影输入，严格只599条五区满星理论，不含新增高手/四区/普通镜像；生成器及应用功能代码未扩展。两份JSON均保留区档完整结构。运行49车、44图42覆盖，578非OC/21OC、561普通/38特殊；原其余599条运行值不变，只有爱音E退出理论。维护身份目录55保留，仅按授权7款Fordo车及爱音E加四区身份。

本轮106项回归（Node34/Python72）、完整维护JSON校验、614键Excel和全台账独立核对、生成器--check均通过。数据版本f4f36ae874e2ddec845435efd965db87e27f8b10a7a178da67a8293539399a3e。原13页所有未授权格值/样式/列宽/合并/冻结保持，变动普通/高手/四区理论渲染检查、公式扫描通过，未原生Excel打开；国服JSON/表/目录、源表、旧36参考、OC台账及既有审核资料字节mtime保持，原434项来源和旧发布ZIP校验通过。备份maintenance/change-history/accepted-tier-review-20261024，完整回执在maintenance/accepted-tier-review-20261024。未提交推送、打包或操作服务器，旧版本/备份/演练/测试数据继续保留。


## 2026-10-24 最新：evo狼崽隧道冲刺修正21.89（仍600条）

用户标注五区_理论!U23，明确最终值21.89。对应内华达/隧道冲刺普通理论，原23.00→21.89，不再减0.1。维护JSON、同一Excel、活动台账及运行数据已同步；另外599条与工作簿所有其他单元格/样式/布局保持，36条独立高手参考、OC台账和国服保护输入字节/mtime不变。

旧23.00来源为BV1uNpU6CEVg约04:10的23.099秒，原跑者Fordo，B站转载者煙KiVi，投稿记录2026-10-14。作者信息来自既有归档记录与原审核材料；本轮B站页面不可访问，未声称重新看过视频。新21.89是用户指定最终值，台账新source_kind=user_direct_final_theory，旧作者/视频/秒数完整收在previous_record，不将21.89冒充原片实测，也不恢复待核21秒条目。

JSON/Excel/台账保持600键，49可计算车辆、44图42覆盖、579非OC/21OC、562普通/38特殊。数据版本2e4305806e2f8a210ee458db1b70283847c5c512903f0daf04d62c826c8eea73，生成器--check、14项Node+21项Python共35项针对性回归通过；13表逐格/样式核对与渲染、公式扫描通过，未原生Excel打开；434项原来源校验通过。改前备份maintenance/change-history/wolf-tunnel-correction-20261024，来源追溯及回执maintenance/wolf-tunnel-correction-20261024。未改应用功能代码、国服或生产，未提交推送/上线；旧版、备份、演练与测试数据继续保留。


## 2026-10-24 最新：撤下两位作者36条理论，原配置转高手参考（本地600条）

按用户明确授权，将疯狼4条、皮卡丘32条（25普通车型+11EVO）撤出理论。35个新增补缺键移除；evo狼崽×内华达/隧道冲刺22.75恢复为导入前23.00，原台账来源完整恢复。其余599个保留活动键值不变，OC及SC不动。当前国际活动JSON/同一Excel标准12表/台账600完整键一致，无重复：579非OC+21OC、562普通路线+38特殊；44图42覆盖，富士两图仍空。

36条原始秒数（未经+0.05或截位）、星级、性能分及四维、作者/源行/完整原配置及撤下台账另存maintenance/expert-reference-scores.json，runtime_enabled=false；同一gauntlet_data.global.xlsx末尾新增“高手参考_原始配置”页，保留原始值与曾录理论值两列，标明分区/跑法待核。该参考页不进入标准高手/普通镜像或理论计算，国际服仍只开放五区满星理论；没有把低改装实测伪装成满改高手。此前全部原件备份在maintenance/change-history/withdraw-author36-20261024。

维护身份目录55辆与原Excel车名列保留；既有生成器按剩余活动成绩自动投影49辆可计算车型，不修改生成逻辑。原12张表只改授权36格，其余值/格式/列宽/合并/冻结保持，高手参考页同用宋体10与原表配色。600键独立回读一致，36参考行逐格核对，渲染及公式扫描通过；未原生Excel打开。

本轮Python72+Node34共106项回归通过，生成器--check通过，数据版本eb5908d8b9e2c2645902c2abe53cd2ddc2cacf12123cdd8784a9da960f76289a。原434项来源与旧发布包校验通过，国服原表/JSON/目录、源工作簿、候选审核资料、OC台账、维护身份目录字节及mtime保持。完整撤下/恢复/保护与检查结果见maintenance/withdraw-author36-20261024/final-verification.json及changes.json。仅本地数据、参考页和相关测试数量基线更新，未修改应用功能代码、提交推送、打包或服务器；线上仍是先前验收的bd12e3fb2c2519b0238afd90/321条国际数据，非本轮实时生产复核。保留旧版本、备份、演练和测试数据。


## 2026-10-24 最新本地：258条获批候选回代完成（635条，55车）

用户明确接受258条主候选，并确认整数和一位小数加0.05、两位原值、三位直接截去末位不舍入，之后保留同完整键更快值。本轮196新增、49更快替换、13保留原表更快/相等值；没有把258条都算作新增。20辆新车补入独立国际目录，用户昵称ars、ap0、阿波罗n、avj、evo百年牛、evo讴歌、fxxk、gtr、乐高c8、迈凯伦p1、叶问已采用，其余沿用已识别昵称。EVO参数仍留null，不借原车参数伪装。

普通杰哥勇往直前24.33→24.25；按此前授权派生规则，OC杰哥24.19→24.15、奇美拉24.09→24.05，两条单列为估算而非实测。飞向未来的候选25.95慢于原25.93，保留原值。OC台账现为5条直接值+16条授权估算，共21条；其余20条OC键值保持。

国际活动JSON、现有Excel及台账635完整键一致，无重复；597普通路线/38特殊，614非OC/21OC，55辆物理车、44图42覆盖，富士最后两图仍空。只在现有五区理论主表末尾追加20列并更新获批格值，OC相邻列和SC分表保留，12表原有值（授权修改除外）、字体、配色、列宽、合并及冻结C2/SC D2核对通过；渲染检查和公式错误扫描通过，未在原生Excel打开。

获批记录原始值、精度处理、作者、来源行/链接、原值与最终值见maintenance/accepted-review258-20261024/decisions.json和accepted-decisions.csv；两个派生值见derived-changes.json。原件备份在maintenance/change-history/accepted-review258-20261024。待核来源/审核表/清单保持字节及mtime不变，未采纳待核值；同键另有获批来源时仅按获批来源更新，不表示该键上的待核来源获批。国服JSON/目录/原两表、用户源表、保留脚本、历史发布包均保持。

当前仅本地数据与目录及对应测试基线更新；本轮没有修改应用功能代码、提交推送、发布打包或服务器操作。线上沿用此前验收的bd12e3fb2c2519b0238afd90及321条国际服数据，这不是本轮实时服务器复核。旧版本、备份、演练目录和测试数据保留。


## 2026-10-24 最新：候选待审核、global显示修复（活动439不变）

新表潜在行分组后472个唯一编号，258主候选；跑法/星级/四区/离群/版本及已作废原版另页，候选0回代。独立审核本在maintenance/source-quality-review-20261024/candidate-review-20261024。global表非数据截断，是P21误冻结，已仅改主表视图为C2，SC表D2保持；439记录/35车、所有值/样式不变，两运行数据JSON和台账字节mtime不变。数据版本仍30a5da9…，只刷新文件/来源校验。未提交推送或上线，生产仍bd12e3fb2c2519b0238afd90/321。

## 2026-10-24 最新本地439及共享表只读评估（未提交/未上线）

仅写入用户直接6条（r兔4、绿兔1、超光孙1）及单独授权的超光孙隧道21.36，当前JSON/同一Excel/台账439完整键一致，35车、401普通/38特殊、418非OC/21OC，35项相关回归通过。共享成绩表836条仅评估0导入；按用户要求不把零件缺失作为质量门槛，整体偏高，名义满星/版本/跑法合格值可作理论候选，低星分层高手参考，异常暂存。B站明确四区来源先保留参考；Driver投稿触发-799后停止。完整报告见maintenance/source-quality-review-20261024/数据质量评估.md。生产仍bd12e3fb2c2519b0238afd90/321，旧发布包不改。

## 2026-10-24 最新本地数据：秋王迁移后433（未提交/未上线）

按用户授权，Battista/秋王从国服五区理论直接迁移13条（9普通/4SC），原值不加减，图池外4条仅参考，旧420全保持。当前JSON/同一Excel/台账433完整键一致、无重复，34车，396普通路线/37特殊、412非OC/21OC；国服保护输入及OC原台账不变。35项相关回归通过，普通/SC新列渲染核对通过；详见LOCAL_INTERNATIONAL.md最新节及maintenance/battista-migration-20261024。仍未提交推送/部署，生产bd12e3fb2c2519b0238afd90和旧交付包保持。

## 2026-10-24 最新本地估算数据（420，未提交/未上线）

按用户明确规则及“保留更快”新增奇美拉18、杰哥OC15（既有3条更快OC保留）；F5按国服五区分段加时24项覆盖/补缺，含两条SC。当前JSON/同一Excel/台账420完整键一致、零重复，33车，387普通路线/33特殊、399非OC/21OC。源值与估算来源分别保留，F5旧杰基拉22.10按授权改为21.90；国服保护输入不变。106项相关测试及浏览器SC开关核对通过。详见LOCAL_INTERNATIONAL.md最新节和maintenance/chimera-review-20261024。生产仍bd12e3fb2c2519b0238afd90/321条；不要续用旧包部署本地新数据，暂不提交推送。

## 2026-10-24 最新本地待发布事项（不改变下方已验收生产版本）

本轮新增爱音R20/爱音E5/陀飞轮17条，回代用户国际Excel另1新增及2更快修改；当前本地364=333普通+31特殊、358非OC+6OC，32辆车，JSON/同一Excel/台账完整键一致。爱音R信仰之跃平跑17.89原样、铁道迷滑栏杆21.90；仅迁爱音E五区理论，四区/池外参考不运算。国际服R级筛选隐藏，国服保留；105项相关测试和浏览器核对通过。当前修改尚未提交推送或部署，详情见LOCAL_INTERNATIONAL.md文末及maintenance/aeon-review-20261024回执。生产仍bd12e3fb2c2519b0238afd90/321条，旧包不改。

## 2026-10-24 国际服上线及公网验收完成，工作暂停

证据来自用户逐步执行服务器命令的完整回传及明确验收确认，代理未登录服务器。2026-10-24 08:30:27 CST启用新应用bd12e3fb2c2519b0238afd90，源码/数据提交5ade7ea3598eb104f136365fb0a51574c16d8013；current与/proc/145790/cwd均为/opt/racepick/releases/bd12e3fb2c2519b0238afd90，active/running。PID为当时记录，后续重新核对。

- 完整上传归档SHA、目录13项SHA均通过，发布ID及85文件清单核对；暂存未激活阶段旧版保持。Ubuntu24.04/x86_64/Python3.12.3，19个锁定离线依赖安装及pip check、Linux临时库原生自检均通过；临时库自检不等于生产迁移，本次没有生产初始化/迁移/导入。
- 上线后完整health：ok/production/schema6/community1/contribution1/feedback1，contributions=true、feedback=true、score_writes=true，成绩版本42d62fde9b81197ac0558087a9a25f97保持。当前国服成绩JSON哈希bed4cf05fd8d2332e043513820adae39d9c01453dedb602dd374fe64355ae9a9；包内新增白龙普通22.84没有通过此次代码部署发布到score-state，后续如需发布须单独比较审核，不能用整包覆盖线上成绩。
- 三次成套备份及独立恢复演练均通过，均160113字节、racepick:racepick、权限600；恢复结果39用户/21车库/3投稿，pending_batches=0、active_database_replaced=false。贡献schema1，counts contributions0/sources1/events0/preferences1；反馈schema1，tickets/events/requests均0。停服最终备份与新版备份内各文件哈希一致，账号SQLite哈希cef5bfa17f519c03b59459e173a2ec48743464a2e24d49a1c31c696aaf8b201a。

| 阶段 | 备份（/var/lib/racepick/backups/） | 独立演练（/var/lib/racepick/restore-drills/） |
| --- | --- | --- |
| 旧版在线 | scores-20261024T002837971492Z.zip | 3f1ef0a291f8b20324111663 |
| 停服最终 | scores-20261024T002956371320Z.zip | 4e858de18e76f918a60f2029 |
| 新版在线 | scores-20261024T003107716123Z.zip | c7b65a1385de6745d3d7a78b |

- 2026-10-24 08:31:40 CST回传：备份timer已恢复enabled、active(waiting)，NEXT为2026-10-25 04:17:45 CST；LAST为10月24日04:16:12，实际04:16:13成功生成scores-20261023T201613699083Z.zip。这证明新版切换前的自动备份成功及切换后的调度恢复，不表示10月25日已执行。恢复timer后的完整health保持。
- 用户明确确认桌面和手机微信验收通过，覆盖此前五图选车/分服车库与草稿/OC及SC/空图项目；两张截图另指出控件排版偏好，不将此偏好混作既有功能验收失败。代理未独立操作手机微信。
- 登录提示另行只读核查：dpkg --audit无输出、无reboot-required标记，最近自动更新日志All upgrades installed，cloud-init被保留未升级；早期发行版元数据警告后近期日志不再出现。未执行apt升级、发行版升级或重启，不凭日志推断cloud-init保留原因。

### 已提交但尚未发布的两项后续修正

用户希望桌面恢复三行，手机档位换行时分组更清楚。476a9e2只改styles.css：服别/档位/分区各自一行，浅色分隔线；档位组内仍可换行。真实本地浏览器1280/390/320宽验证，无横向溢出；320宽自动档换到本组下一行，分区仍在下组，国际服隐藏项无残余分隔。1b2361b只在既有NICKNAME_ALIASES加入兔子→c2，保持车辆身份/目录/成绩不变，国服与国际服实际搜索均匹配c2。14项前端回归通过。截图位于repo/.production-build/layout-followup-20261024/。

这两项仅提交到源码，未重新打包或部署；生产仍为bd12e3fb2c2519b0238afd90，旧发布包及其校验值保持。未来需另行准备新包并由用户执行部署。用户要求完成交接推送后暂停：不清理旧应用、备份、演练、工作簿或测试数据，不继续系统维护、成绩发布或其他开发，无监控/提醒。

## 以下为历史交接记录

## 2026-10-23 本轮接手核验（未进行新部署）

以下为本轮只读检查结果；不延续历史部署步骤，不表示已重新核验服务器内部状态。

- 已读取根目录CLAUDE.md/context.md及本仓库交接、车库部署与验收记录。根目录说明仍停在发布准备阶段；README部分版本/合并描述也有历史残留，不能据此判断实时状态。
- git fetch origin成功；本地main、origin/main及git ls-remote的main均为90db8b90969214f696501455f74a113af8d6e590。已包含3baf0b3车库修复和1760a11上线验收记录。相对打包源码3baf0b3，HEAD只变更CLOUD_HANDOFF.md、CLOUD_HANDOFF_PROMPT.md、GARAGE_DEPLOYMENT.md、GARAGE_LAYOUT_FIX.md四份文档，没有待发布的运行代码。
- 全部10个已登记工作树没有已跟踪文件的未提交改动（本记录写入前）；repo仍有既存未跟踪_star_curve_fit.py、gauntlet_data_shared.xlsx，均未操作。feature/track-top-three虽显示领先自己的旧远端25项，但它是当前main的祖先（main领先21项、该本地分支独有0项），不构成新的待发布功能。没有合并、切换分支、推送或清理。
- 本轮直接HTTPS读取/api/health返回200：status=ok、mode=production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true、score_version=42d62fde9b81197ac0558087a9a25f97、score_writes=true。首页/返回200；按backend.app的首页注入规则生成预期内容，与公网响应完全一致；styles.css公网与本地SHA256均为07d51cf3530b3b52ff96fb01ac68409fac214002b0a32c5773e9c5012e2fb4e0。/index.html返回404符合路由白名单，主页实际入口为/。
- 公网health不包含应用发布ID，因此6ee40a45b00b0e347bf973fe仍是最近用户回传确认的应用版本，不能仅据本轮HTTP检查声称重新确认了current或实际进程cwd。本轮未登录服务器，也未核验当前systemd、备份文件或timer；最近自动备份及下次调度证据仍见下方验收记录，10月24日计划执行不能提前记为成功。
- 本地8000–8011范围仅发现127.0.0.1:8011监听；PID8776的命令指向garage-toolbar-responsive/.local-accounts/preview，health为local、贡献/反馈关闭。其余历史环境文件保留，端口未监听不代表数据已删除。本轮未启动、停止或重建任何测试环境。
- 现有11文件车库交付目录保留，ZIP SHA256重新读取仍为fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb；没有重打包或变更旧包。本次未重跑回归，沿用既有验收记录；HTTP检查不替代登录、真实邮件及手机交互验收。

当前没有明确的新开发或发布目标，先由用户确定范围。账号、成绩、反馈、备份、测试数据、工作簿和未跟踪文件继续保留；服务器仍按给命令、用户执行并回传的方式逐步推进。本轮交接更新仅保留在工作区，尚未授权提交推送。

## 主线整合与通用交接入口

用户随后授权合并main。已验收的fix/garage-toolbar-responsive是远端main的后继，使用快进整合，无冲突；本地两份JSON、两份工作簿及保留脚本的哈希与修改时间均未变化。下文“未合并main”属于当时的历史状态，不再作为当前Git结论。源码整合未重新部署或修改生产环境，后续先fetch核对最新状态。

长期复用、无需填写版本号的提示词见[CLOUD_HANDOFF_PROMPT.md](CLOUD_HANDOFF_PROMPT.md)。该提示词以“上一轮部署已完成”为交接起点，要求接手模型自主探索代码和运行状态；本文件继续保留具体历史证据。

## 最新交接：车库布局修复已上线验收，工作暂停

本节覆盖下方历史状态。用户于2026-10-23确认页面验收完成，并要求更新交接、完成必要推送后暂停。以下生产证据来自用户回传，本次文档收尾未访问或修改生产环境。

- 当前应用 **6ee40a45b00b0e347bf973fe**，打包源码3baf0b3970dc638afd9910723943f3a7ad6a0781，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与实际进程cwd均已确认，切换时PID138683仅作历史记录。
- 最后完整health：status=ok、mode=production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true，成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。本次无数据库迁移，没有用包内JSON覆盖成绩。
- 用户确认页面验收完成；范围为此前要求的桌面对齐、手机微信分行以及保存/恢复/点亮/清空/排序。没有提供新的真机截图，不声称代理独立完成真机检查。
- 旧版在线备份演练、停服最终备份校验、新版备份演练均由用户简述确认通过，新版active_database_replaced=false；具体ZIP及演练目录未回传，不编造恢复点路径。
- 完整回传确认 **10月23日04:16:09–04:16:10 CST自动备份成功，退出码0**，文件scores-20261022T201610532450Z.zip，155551字节。这是升级前反馈版本的自动备份证据，覆盖下文“10月23日自动执行尚未核实”。
- 本次timer于 **2026-10-23 10:46:44 CST** 恢复enabled/active(waiting)，NEXT为 **2026-10-24 04:16:12 CST**。该次未来计划尚未执行核验；一条health回传被截断，随后单独回传完整JSON确认正常。
- 交付garage-toolbar-responsive/.production-build/delivery-20261023-garage共11文件，服务器上传目录/root/racepick-deploy/20261023-garage-6ee40a45。ZIP SHA256：fc16b2d678b601c0689e91eee5b2286bfa50c8444a6ce60117933f9b3dbb15fb。包内只有index.html和styles.css有运行内容变化，另一个后端文件仅LF/CRLF不同，逻辑一致；旧包不修改。
- 最新交接分支 **fix/garage-toolbar-responsive**。main仍73e3f8b，未合并；反馈与其他已验收功能都在本分支历史中。先fetch核对最新状态，不把源码同步当成再次部署。
- 原8011、8010、8009测试环境及账号库、工作簿、未跟踪文件保留；本轮不清理目录、不改配置、不新增监控。当前6ee40a…与旧4a28f6d…及备份均保留。

详细记录见[GARAGE_DEPLOYMENT.md](GARAGE_DEPLOYMENT.md)和[GARAGE_LAYOUT_FIX.md](GARAGE_LAYOUT_FIX.md)。完成本轮文档推送后暂停，不自动继续合并、部署、清理或核验未来备份。

## 上一轮交接：反馈功能已上线验收（2026-10-22，历史）

本节为最新状态，覆盖下文上一轮排行榜升级的历史快照。所有生产事实来自用户服务器回传或明确反馈，本次文档收尾未访问生产环境。

- 当前应用 **4a28f6d76b9d3e93d3227120**，打包源码b17d6fcfe1c831b3f7fbb2b4923ea0a9efb33168，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与实际进程cwd已确认一致，切换时PID132627仅作历史记录。
- health：production、schema6/community1/contribution1/feedback1，contributions=true、feedback=true；最后成绩42d62fde9b81197ac0558087a9a25f97、score_writes=true。用户确认昵称展示、按钮统一、文字反馈公网验收通过，功能正常。不能重新执行已完成的反馈/贡献/成绩迁移。
- 新版成套备份及独立恢复演练由用户简述确认通过，feedback_schema=1、contribution_schema=1、active_database_replaced=false；新版ZIP和演练目录未回传，不编造路径。
- timer于 **2026-10-22 21:46:12 CST** 恢复enabled/active(waiting)，NEXT为 **2026-10-23 04:15:58 CST**，替代下文旧的04:19:44计划；LAST仍为10月22日04:18:37，尚无新版首次定时执行成功证据。
- 本次已核实的旧版在线备份为scores-20261022T134206474628Z.zip，演练目录6ed23e688a30ec2f6f7418fd，counts27/15/2、昵称偏好1、未替换活动库。停服最终备份、迁移保护备份、新版备份的具体路径未提供，若需恢复点须现场只读核验。
- 当前文档分支 **release/account-feedback-production**；功能基线feature/account-feedback=28d4c96，生产适配b17d6fc；main最后核对73e3f8b，未合并。先fetch核对最新状态，源码同步不等于部署。
- 本次交付account-feedback-production/.production-build/delivery-20261022-feedback，共10文件，绑定4a28f6d…；ZIP SHA256为89fc52c23d5aea9f16eee985124f4eb51dd73706d0799b44d1529fac1cfe4b78。服务器上传目录/root/racepick-deploy/20261022-feedback-4a28f6d7保留。文档更新不修改已部署包。
- 先读本节和[反馈生产验收记录](FEEDBACK_PRODUCTION.md)文末，再查下文的历史部署、清理和保护约束。原8010及8009测试环境、账号、工作簿和未跟踪文件继续保留。
- 本轮未进一步清理目录。当前4a28f6d…、上一1fcc18c…及此前保留的651ea3d…不因新部署被自动删除。反馈schema1后不能直接切回不支持反馈的旧程序；禁止单SQLite恢复或用旧工具绕过兼容检查。

后续待证据：10月23日04:15:58计划备份的实际结果；本次未回传的具体备份路径。此处不自行新增监控或重复生产操作。本轮仅提交推送文档，不合main、不修改生产。

## 上一轮排行榜已验收状态（历史）

本交接依据用户服务器回传和明确验收反馈，不是代理独立登录服务器的结论。历史文档中的“仅本地/尚未上线”以最新验收记录覆盖；未来操作前重新只读核验。

- 域名https://racepick.cn；Ubuntu24.04、Python3.12、Nginx代理127.0.0.1:8001。服务racepick-accounts，应用链接/opt/racepick/current，数据/var/lib/racepick。
- 当前已验收应用 **1fcc18c06a7b920ed0aa8b0b**，源码fa23531106e4eec54ccf9cd91164475888f354a9，数据基线73e3f8b0bb1ea0c6b2cafe82d8002e1fe4a775ee。current与运行进程cwd已确认一致；主进程当时130103，后续不能盲用旧PID。
- health：production、schema6、community_schema1、contribution_schema1、contributions=true；最后成绩版本42d62fde9b81197ac0558087a9a25f97、score_writes=true。版本和数量是历史快照，勿强制修回。
- 排行榜质量0–10＋正式采用10分、历史不补计、公开昵称/匿名、三类主页导航已上线，用户确认功能正常。原公告、账号管理、手动车库及成绩版本化均已完成，不重复迁移。
- 备份和独立恢复演练通过。timer在2026-10-22 20:28:08 CST恢复enabled/active(waiting)，NEXT为2026-10-23 04:19:44 CST；尚无该次定时执行回传。

## 先读与后续操作

先读本文件及[本次部署与清理记录](CONTRIBUTIONS_PRODUCTION.md)，再查COMMUNITY_DEPLOYMENT.md、SCORE_PRODUCTION_DEPLOYMENT.md、PRODUCTION_DEPLOYMENT.md和工作区根目录CLAUDE.md/context.md。本次文档分支release/contribution-production；main最后核对73e3f8b，功能分支feature/contribution-leaderboard为0938886，生产适配fa23531在release分支，未合main。先fetch核对最新Git状态，不把源码同步当成部署。

本地交付位于contribution-production/.production-build/delivery-20261022-contributions，9文件，绑定1fcc18c…；不可修改旧包冒充新版本。完整ZIP SHA256：aa7e70ba59f203c6ed2870d5689a840c8202c7534fd2234f10a5108e2ad0e0d9。当前服务器上传目录/root/racepick-deploy/20261022-contributions-1fcc18c0保留。

先确认新的任务范围；没有新部署目标时不重跑上线。发布先准备完整校验包，再按用户回传逐步暂存、临时库自检、备份、必要迁移、切换、验收和恢复timer。每次切换必须核对current、服务状态、/proc/<MainPID>/cwd、公网health，不能只看终端目录。

## 数据与恢复边界

保留所有账号库、测试环境和工作簿，特别是repo/gauntlet_data_shared.xlsx、repo/_star_curve_fit.py；不reset --hard、clean或自动同步工作簿。原8009独立模拟环境保留，不能把其数据导入公网。

成绩从独立score-state读取，代码包JSON不覆盖正式成绩。main的73e3f8b仅同步了云端肥龙★6四区高手34.90和普通镜像，工作簿未同步；后续云端写回不会自动同步本地JSON/工作簿。

迁移前最终成套备份scores-20261022T122554381864Z.zip；迁移保护备份scores-20261022T122638564366Z.zip；新版运行后盘点备份scores-20261022T122749408259Z.zip。均在/var/lib/racepick/backups。原始演练输出及证据限制见部署记录，不编造备份与演练目录映射。

禁止单SQLite恢复；灾难恢复须保留现场、独立目录演练并核对整套数据。贡献schema1后不能直接切回旧代码，即使保留了上一版本651ea3d…也不代表兼容回退。不要使用旧部署工具或手工ln绕过兼容检查。SMTP密码不输出、不打包。

## 已清理与继续保留

用户已确认删除旧应用目录09897d5f81a696dca0b95c8e、3ac58aba697f3189b751d6ea、7a0f2927404cab20f0a5a020、c907541d0c209f9a38a181a5；以及/root/racepick-deploy下accounts-release、accounts-credentials-fix、data-20261021、score-versions-20261021。旧包本地留档及校验已核实。约释放300M，非精确测量。

当前版和上一版应用保留；当前上传目录、community-20261022、20261016-icp、nginx-before-accounts-ghnuwvit及顶层静态发布文件保留。所有业务数据、成套备份、历史SQLite、score-state、恢复演练和/var/www静态目录均未清理。Nginx仍引用静态root，不可仅因代理已启用就删静态目录。以后清理重新核对路径/引用并取得具体范围授权，不扩大本轮删除授权。

## 尚无新证据的事项

- 10月23日04:19:44计划备份是否实际成功。
- 新规则启用后的真实投稿计分与发布回执逐项证据（不否定用户已确认的功能验收）。
- 公告由用户自行发布；本轮没有代发或核验其发布状态。

本次收尾仅更新并推送文档，不合并main，不修改生产、发布包或任何账号/成绩/工作簿数据。

## 反馈生产准备阶段记录（已被文首验收结果覆盖）
功能基线28d4c96，在独立release/account-feedback-production准备生产适配与交付。随后用户逐步完成安装、迁移、切换、备份演练及timer恢复，并确认公网功能正常。完整证据边界见FEEDBACK_PRODUCTION.md文末，最新状态以本文件首节为准。

## 2026-10-24 国际服本地验收通过，提交及发布包准备

用户明确本地验收通过，授权统一Excel为旧字体格式、提交推送并准备完整可校验包；本轮禁止服务器操作。国际服五区满星理论321条（315非OC/6OC），普通291/SC30，29基础车、44图42有值，富士两空图仍在最后。运行版本c7ea2f354e90bf70711c04ae05ced8d894ac9c1168a9b4c18393c9a9fd1b31f0，国际云车库/投稿/版本链及自审免积分/OCR未实现。

国际维护表与shared已统一宋体10pt及旧表头风格，成绩、行列、冻结及OC/SC区分不变；国服主表和同步副本已有宋体，字节保持。修改前原件在数据源/international-prep-20261023/maintenance/change-history/style-unification-20261024，历史表和资料均保留。gauntlet_data.global.xlsx为当前国际321条版本库副本。shared仅格式调整，仍是未跟踪文件；不将其历史缺项当删除授权。

现有生产打包器已补国际组件及独立哈希校验，保留旧包读取兼容；自检增加三JSON及国际入口HTTP检查。发布从干净提交及锁定Linux离线依赖构建，工作簿、账号/成绩状态、反馈、凭据及本地测试库不入包。包内国服JSON新增22.84不会自动覆盖服务器score-state，是否需要单独发布该成绩须现场核对。具体流程见INTERNATIONAL_DEPLOYMENT.md，包内RELEASE.json绑定真实源码/数据提交。

本轮未访问或修改生产，当前运行应用、health、备份timer及公网验收未重核。之后仍由代理给一条命令、用户执行回传后逐步核对，不重跑生产迁移、不初始化、不清理旧文件。

### 本轮发布包已生成并校验（尚未上线）

源码/国服数据提交5ade7ea3598eb104f136365fb0a51574c16d8013已推送main并用ls-remote核对。发布ID bd12e3fb2c2519b0238afd90；完整目录repo/.production-build/delivery-20261024-international共14文件，外层SHA清单13项全部通过，ZIP内85白名单文件（含19锁定离线依赖）。内层racepick-accounts-release.zip SHA256：1ecc93ea6d36eec12a5e3ca0ed96acddf8847dc6f549546c52d1eac9c11939ee。

便于完整上传的归档repo/.production-build/RacePick-International-20261024-bd12e3fb-delivery.zip，SHA256：ac6016cf81b3fa5f900a4d1aea1bc7c538d1b4218916fb8947d1fa8c835c8036；归档含上述完整14文件目录，已逐字节回读。PACKAGE_VERIFICATION.json保留详细回执。使用提交的干净独立检出构建，保护原工作树未跟踪脚本/shared；数据JSON与提交字节一致，Windows代码检出换行差异已独立核对，内层manifest绑定实际交付字节。

本轮Node80+Python125共205项通过，交付目录自带工具的独立本地暂存、解包目录验证和临时库HTTP自检通过；原始434资料哈希保持。Linux/Python3.12离线安装及原生自检尚待上传后用户执行。未操作服务器、未激活、未生产迁移；实际运行版本、健康、备份调度、线上成绩差异和公网验收均留待部署轮核对。后续文档提交不改变该已校验包绑定的源码提交。

核验补充：本轮Node34项+Python72项共106项通过；生成器--check通过，数据版本08d864c84f8c187f787095547d9d8c63df13f7f9be3a655b5198f5f32090395e。原434项来源校验全部通过，旧发布ZIP哈希保持；受保护输入逐项字节及mtime复核通过。详见accepted-review258-20261024/final-verification.json。

## 2026-10-24 标注作者质量复核（635条活动数据未修改）

用户对BG16/BG37霓虹gtr、BC4小牛、AU3及AT21:AU23的成绩提出偏慢疑问，要求检查作者其他成绩。定位作者为疯狼、皮卡丘，源表全部42+145=187条已复核；其中此前采纳4+32=36条。36条中25条普通车虽名义满星，但性能分及部分参数低于已抓取国际服满改目录；11条EVO不套用基版参数判断，仍需单独核实。满星不等于满改，先前补缺筛选没有据此充分限制理论适用性。无特殊跑法图且有导入前国际同车普通参照：疯狼14条均慢，中位差+0.909；皮卡丘18条中17条慢，中位差+1.250；均为原始圈速差，不是原作者能力或跑法一致性的证明。

建议25条普通车先撤出满改理论候选，原始配置成绩保留作高手参考；11条EVO单独复核，不自动降档或删除。活动JSON/同一Excel/台账仍635条，无成绩改动。国服喧闹铁路小牛理论18.60对现国际19.98，仅作为参考，未迁移；两图霓虹gtr在当前国服表没有同车同图值，不编造参照。两作者源记录均没有BV号，未据同名绑定B站账号，未声称检查全站视频投稿。报告、全部187条及已采纳36条逐项清单在maintenance/author-quality-review-20261024。保护输入逐项哈希/mtime保持，未改代码、国服、工作簿或生产，未提交推送。

## 2026-10-24 来源地图纠正：旧evo狼崽23.00实际应归龙卷风山道23.05

用户明确指出该旧来源录入图名错误，原图应为龙卷风山道23.05。已在活动台账隧道冲刺21.89的previous_record旁明确标注历史来源错图、更正目标与用户最终值23.05；原误识别记录保留追溯，不再视作隧道同图来源。龙卷风现有用户表内值22.99更快，按保留更快规则不覆盖，23.05作为该图纠正后备选来源保留。隧道21.89仍是用户独立指定最终值，Fordo/煙KiVi只关联纠正后的历史来源，不冒充21.89视频证据；本轮未重新看视频。

活动600条值、现有Excel字节与mtime全部不变，国服/OC/36条高手参考保持。仅来源台账、当前维护备注及生成manifest来源哈希更新，dataset_version仍2e4305806e2f8a210ee458db1b70283847c5c512903f0daf04d62c826c8eea73。生成器--check与12项数据回归通过，纠正及回执见maintenance/wolf-source-map-correction-20261024，改前备份在maintenance/change-history同名目录。未提交推送、上线或操作服务器。

## 2026-10-24 剩余本批已采纳成绩质量复核（仅审核，600条未修改）

用户要求重点检查满星未满改及地图错误，发现后先列审核，不改成绩/上线。范围为本批258项中实际写入245减已撤36后仍生效209项，13项当时保留原值没有导入；额外检查全部600活动台账地图目标与国服迁移源映射。对源XLSX重新从XML逐行读取209条，车辆/作者/秒数、配置页唯一关联及目标映射均核对，无新结构性错位。176条普通车型参数与归档满改一致；1条爱音E偏离中心33.85（源33.8，耄耋，6星）配置4102/480/84.18/39.97/18.33低于实时满改5106/491.5/86.23/46.03/25.94，建议退出满改理论待用户审核。12条玻璃满星分5190相同但加速84.61/氮气21.71冲突，实时目录84.28/27.50；不能直接判未满改、OC或国服配置。20条EVO（女武神7、狼崽13）星级有记录但性能分和四维缺失，只标缺证待核，不套用基版参数，不以零件作门槛。33条配置问题均未改动。

本轮公开view接口3条视频成功：BV17jtnzgEC6含11条Fordo记录，标题“对三、四区友好”，B站转载Moon_River-OL，列为分区待核提示而非认定实际四区，11条配置本身均与满改目录一致；BV13LgW62E3D标题AL金恶魔擂台圈速，3条；BV1PCRmYHEQ2标题国际服擂台全图参考，1条，简介明确并非最快。194条没有BV号；15条只核验元数据，未逐图重看终点/路线，所以原作者源表错图未能独立排除，不声称209条地图均实测验证正确。既有23.05龙卷风错图已纠正，不计新发现，隧道21.89和龙卷风22.99保持。

实时ASEC只重读304/314并与归档一致，其余车型只使用2026-10-23已抓取目录，不声称全部实时重抓。公开网页工具无法打开API后，正常urllib读取公开接口成功，无cookie/登录/绕过；没有重新尝试投稿列表风控接口。报告maintenance/remaining-adopted-review-20261024/剩余已采纳成绩复核.html含33配置逐条、11分区提示与全部209行、原值和回退值；原始响应及核验JSON同目录。工作簿13页、国际/国服活动JSON、台账、OC/36高手参考、目录、代码等保护输入哈希及mtime保持，原434项来源校验通过；未提交推送、打包或操作生产。

## 2026-10-24 玻璃破冰者二次审核通过（仅审核记录更新）

用户明确接受T0352玻璃/格陵兰·破冰者，保留31.85，不回退旧32.13。accepted-tier-review-20261024/bolide-ice-secondary-review.json及对应HTML已由待二审改为用户已接受，源31.8及配置参数冲突、未知作者/无链接等事实继续保留；接受不等于这些缺证已补齐。回执在maintenance/bolide-ice-approved-20261024/approval-receipt.json，原待审记录已备份至maintenance/change-history/bolide-ice-approved-20261024。

本轮没有改任何成绩：运行599、完整维护614键、现有Excel、两份成绩台账、国服/OC/高手参考及程序文件字节和mtime保持；不生成新运行数据，不修改manifest或数据版本。只更新审核记录/交接说明及其校验；未提交推送、打包或上线。
