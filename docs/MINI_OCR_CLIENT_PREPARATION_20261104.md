# 独立OCR检查工程与只读联网结果

后续记录：用户随后明确授权合成图一次并确认添加uploadFile域名，已实施单样图SHA/额度/独占预约驱动，调用失败且未重试；详见[单次联调结果](MINI_OCR_SYNTHETIC_ONCE_20261104.md)。生成器现在仅在显式本地单次permit下允许额度1，默认仍0。下面保留授权前的只读准备范围，不作为新付费调用授权。

2026-11-04，小程序分支接手feb36f8。用户回交CN OCR已部署的非秘密材料，明确不授权额外付费审核、微信后台配置、上传体验版/提审/发布或账号/B–E。本轮完成客户端准备及无图片的元数据联网，不执行付费实图。

## 来源与固定校验

来源为主repo的MINI_OCR_CN_BINDING_20261104.json / MINI_OCR_CN_CLOUD_HANDOFF_20261104.md和CLOUD_HANDOFF文首，及外层封存v2包 `offline-evaluation/mini-ocr-gateway-release-20261104-01/RacePick-MiniOCR-Baseline-20261104-delivery-v2` 的OCR_EXPECTATIONS.json、snapshot与guest/bridge源码。没有从并行dirty后端抽取新的公共逻辑，也不修改这些来源。

独立期望写入 [MINI_OCR_EXPECTED_20261104.json](MINI_OCR_EXPECTED_20261104.json)。交付35bd5c5d2e618b555de3a70c，网站7241d9d67cc99178bd7d2d14；封存source_commit=null，开发base0b97dae不伪装成新提交。运行桥补件map_ocr_production.py的来源/SHA/4495字节保留原回执，不能声称运行目录与原ZIP零差异。

本地实际重算并通过：五文件原字节SHA/bytes、两服固定版本、Global dataset、CN catalog=sha256(UTF8(snapshot_version+':')+原gauntlet_data.json)、tracks原顺序83图，以及Python json.dumps(sort_keys=True)格式maps SHA。新CN能力是true / 57876474bd3cd25c283e79a471be99ec76d4e58ed16fa0e2c8ae2a6cdf0b9ced；Global仍false/null。没有复用第一阶段false/null期望或正式活动指针。

## 新工程

最终目录：

`E:\hzz\work\MutualExclusionAllocator\offline-evaluation\mini-ocr-client-20261104-01\ocr-check`

`node tools/prepare_ocr_probe.cjs <全新外层目录> docs/MINI_OCR_EXPECTED_20261104.json` 创建独立工程，拒绝覆盖。当前生成器把maxUploads固定为0、uploadDomainDeclared=false，没有CLI开关偷偷允许实图。AppID只继承本机忽略配置；不含AppSecret，不复制私人project设置；urlCheck=true。固定原生方法/query白名单，不加载账号/管理/统计页面，不读写wx storage，不改已验收工程或车库。

页面保留小“地图识别”按钮、直接相册、仅支持清晰五图中文名的说明；选图不会自动上传。上传需明确本次同意、域名声明及总次数额度，底层wx.uploadFile还会再次检查。当前0额度即使同意/选图也无法上传。内容提示明确发送服务端及阿里云安全处理、存在供应商留存，可取消和手选；不声明本地处理、零外发或零留存。正式平台隐私指引/第三方声明与实际授权仍须用户后续核对；此开发者检查页不替代平台配置。

服务端内部checking映射为queued，客户端不发明新状态。识别仍复用原recognition_jobs：原任务/key恢复、同owner/目录校验、五槽固定顺序、后台暂停、取消/迟到结果拒绝。新增白名单IMAGE_SAFETY_REJECTED / UNAVAILABLE / TIMEOUT作为终态固定说明，不解析error文案、不自动新key送审。候选不会自动覆盖五图，缺图/重复大地图拒绝确认；确认前再次核对目录。图片路径、token、任务key/id不进页面报告或持久存储。

## 已验证与限制

- 10份客户端测试119项通过，覆盖默认零上传、逐次同意/额度、固定原字节目录、部分槽位补正、未知上传响应原key恢复且无第二次发送、安全终态、相册跨前后台返回、迟到结果及原任务恢复、手选保留等。测试实图请求均为本地mock，不是供应商证据。
- 最终工程通过官方CLI/SDK真实元数据检查：session一次、CN/Global snapshot各一次、catalog一次；两服版本/原字节与83图匹配、content_safety=required_approval、worker=ready。上传/查询任务/恢复/取消均0，hasImage=false；没有选择或发送图片，没有触发额外阿里云审核。无账号调用、异常或车库读写。证据 `sdk-metadata-confirmed/metadata-result.json`，工程唯一标识1d58501a06b0d2a4b634、base SDK3.17.5、devtools。
- 过程中CLI把第二临时工程的实际端口改为9422，初次驱动仍连9421前一份临时工程，得到的只读结果不能归给第二份。保留sdk-metadata历史结果；仅关闭本轮两份无任务临时工程后重开最终ocr-check。增加工程唯一标识并在任何联网前核对；首次最终驱动未通过且没有详细异常/结果，不编造精确原因，保留空证据目录。随后增加有界等待真实Page/标识就绪，明确实际端口9421后通过，以sdk-metadata-confirmed为准。不清缓存、不改安全选项，不把准备失败写成通过。
- 供应商留存约30分钟/审核结果近30天可查询仅沿用户回交的官方选型记录，未验证实际副本删除/全日志期限；本轮不作法律或平台合规通过声明。服务器部署和供应商一次合成图成功按用户现场证据记录，不扩展为本机/手机真实OCR通过。

没有执行真实uploadFile、阿里云实图、安全拒绝/限流/取消/过期公网任务或手机OCR验收。原诊断版2手机通过仅指访客/快照阶段，不受本工程准备影响。

## 待用户确定的一次实图方案

已在外层准备无账号/昵称/资源信息的 `synthetic-five-maps.png` 与SHA/预期五图清单。若获准，可先只做**开发者工具一次上传/一次安全审核及队列返回**，失败不自动重传/换key/换供应商，不扩大到手机。合成图仅验证链路，不代表真实游戏截图准确率；后续真实游戏样图和手机各自授权/验收。

另一候选是既有attack06.png，但视觉核对发现含游戏昵称/公会/资源信息，不能称作无账号信息的非私人合成图。未将其发送第三方；使用它需要用户明确知情授权。样图本地查看与原历史本机OCR授权，不自动等于外送阿里云授权。

付费调用范围获准、实际uploadFile合法域名由用户添加并确认后，才准备相应限次上传配置/驱动。当前不要求用户预览这个0额度工程；账号/B–E、私人图下载、生产变更、正式构包/上传/提审/发布继续排除。
