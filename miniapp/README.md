# RacePick 微信原生客户端 · 本地开发

2026-11-03，独立分支 `feature/miniprogram-v1`。用户已确认个人主体，采用原生镜像；网站是唯一外观与功能基准。网站A–E契约已经回交并完成本轮客户端接线，详情见 `docs/NATIVE_FULL_MIRROR_INTEGRATION_20261103.md`；页面实现、fixture联调与完整镜像验收分别记录。

## 构建与测试

在小程序工作树根目录执行：

```powershell
node tools/prepare_miniapp.cjs --data-receipt ../offline-evaluation/miniprogram-v1-20261102-01/runtime-source.json
node --test tests/test_miniapp.cjs tests/test_miniapp_local.cjs tests/test_miniapp_dropdown.cjs tests/test_native_api.cjs tests/test_recognition_jobs.cjs tests/test_web_home_mirror.cjs tests/test_account_mirror.cjs tests/test_visual_acceptance.cjs tests/test_platform_network.cjs
```

该命令生成离线local模式，不调用登录或上传。省略数据回执则是明确标记的mock。五个共享模块从固定Git对象198999a原字节生成；正式presenter、主题与OpenAPI另固定8da1609，从Git原字节生成并记录SHA；JSON机器契约转换为CommonJS，主题生成WXSS。旧网页提取器仅保留作冻结对照，不再参与运行服务。`miniapp/shared/`和`generated/`忽略，不将未冻结4504/693数据当发布来源。切换来源必须先核对协议/依赖及原字节SHA，不从dirty网页抽取新规则。

原生HTTP联调需显式增加 `--native-origin <本地基址>`。隔离fixture还需 `--fixture-code <lab中未用代码> --fixture-key <该代码首次使用的固定key>`，仅开发者工具接受fixture。接口默认关闭；token仅内存，快照严格核验后原子缓存。过期代码不能换key续期，应新建独立lab。8052为本轮全功能测试lab，交付查看环境另为8055；用过的fixture代码/key见 `docs/NATIVE_FULL_MIRROR_INTEGRATION_20261103.md`。旧8044等环境保持。不用生产账号或8033测试库。

## 真实联网准备（2026-11-03）

离线真机用户验收已通过。下一步为真实微信访客会话/两服快照，再OCR，最后RacePick账号与云车库。准备与边界见 [本轮记录](../docs/PLATFORM_NETWORK_PREPARATION_20261103.md)；[网站/运维交接清单](../docs/HANDOFF_PLATFORM_NETWORK_20261103.md) 可直接转交，不需要再买域名。

`node tools/setup_platform_profile.cjs` 只在缺少时创建忽略Git的 `miniapp/platform.profile.local.json`，不会覆盖现有文件。当前origin为空、声明均false。运维确认后填写实际HTTPS origin和已完成事项；不填AppSecret/token。声明不是验收证据。

`node tools/prepare_network_probe.cjs <外层offline-evaluation下全新工程目录> --expected docs/MINI_STAGE1_EXPECTED_20261104.json` 生成独立网络探针，拒绝覆盖旧目录；未满足第一阶段声明时保持关闭，启用时必须指定固定交付期望。生成工程启用域名校验，不改主工程或已验收phone-local。服务就绪后才运行真实SDK检查 `tools/check_platform_network_devtools.cjs <SDK目录> <探针工程> <新证据目录> [自动化端口]`。探针只调用session和两服snapshot，不上传、不登录账号、不写车库。主工程将来用 `--platform-profile miniapp/platform.profile.local.json` 显式构建；当前不切换主工程，避免顺带启动完整业务请求。

2026-11-04：隔离入口与真实微信访客/两服固定快照已由开发者工具SDK实际通过；105项本地测试通过，真机待用户手动预览扫码。具体工程、结果和步骤见[第一阶段客户端验收](../docs/MINI_GUEST_STAGE1_CLIENT_20261104.md)。旧准备段落与前一日记录按历史边界阅读。

## 开发者工具

安装目录 `E:\Software\微信web开发者工具`，使用用户AppID，保持直连即可。用户已开启服务端口及本地跳过域名校验；后者只支持localhost开发，不代表已登记HTTPS域名或具备发布条件。工具曾更新重启，不沿用旧版本号作当前证据。

```powershell
& 'E:\Software\微信web开发者工具\cli.bat' auto --project 'E:\hzz\work\MutualExclusionAllocator\miniprogram-v1\miniapp' --auto-port 9420
node tools/check_native_ocr_devtools.cjs ../offline-evaluation/miniprogram-v1-20261102-03/automation/node_modules/miniprogram-automator ../offline-evaluation/miniprogram-home-mirror-20261103-01/new-run ../offline-evaluation/maps-20261031-01/samples/attack06.png
```

SDK为独立目录的官方miniprogram-automator@0.13.0。此脚本仅用于已显式配置的本机fixture，实际wx.request/uploadFile和CPU OCR；chooseMedia被受控样图替换，不是真实手机相册或微信鉴权。测试备份并恢复fixture两服saved/working/view键，删除自己创建的临时图片，检查token未持久化；不清理其他存储。旧 `check_miniapp_devtools.cjs` 是历史local页面验收脚本，未适配本轮布局，不作为本轮复现入口。

## 页面与存储

地图、星级、SC类型与方案均用页内下拉。截图只打开相册，说明必须清晰显示五图中文名称，不支持拍屏；识别后核对并确认再填图。CN首次高手、Global理论、首次全选均沿用网页；已保存的合法空车库保持空。选图/车库/星级/SC变化自动重算，单图前三只作参考，不扣其他图用车。

存储按mock/local/native/native-fixture及两服隔离：`racepick.mini.<模式>.draft.v1.<服>`是显式保存车库，`working.v1`是临时试算。后台/切服只暂存working；恢复已保存保留当前地图/区档/SC。已有损坏/未知schema及基线冲突记录保持，不静默覆盖。照片路径与token不写草稿；不自动读取浏览器车库或账号。登录后两服使用账号云车库；按origin/actor/server隔离，ProfileStore保留revision和冲突，不自动导入游客车库。响应丢失先核对原key，核对不会丢弃后续临时编辑。

未执行生产、微信后台、上传体验版、提交审核或发布。真实微信登录、合法域名/图片安全策略、iOS/Android及用户验收仍待完成；审核未假定通过。


## A–E本地验证入口

```powershell
# 必须是显式新建的 --accounts --full-mirror lab，fixture/file邮件；参数按实际回执填写
node tools/check_account_mirror_http.cjs <新lab> <外层证据目录>
node tools/check_mirror_devtools.cjs ../offline-evaluation/miniprogram-v1-20261102-03/automation/node_modules/miniprogram-automator <新lab> <外层证据目录>
```

HTTP脚本硬限定本机8052、校验lab标记，使用内存随机密码、file outbox和新注册账号，在该新lab明确bootstrap自己的超级管理员、运行隔离审核/应用/回滚。不能指向旧测试库/生产库；完整脚本不应在已存在主超管的旧lab重复执行，下一轮先新建lab并明确更新隔离配置。SDK脚本要求当前没有已登录账号，创建自己的fixture账号，恢复测试前游客记录，只删除自己账号的新临时草稿键；混合按钮/输入与Page handler驱动，不冒称全手工测试。两脚本不上传小程序、不提审、不外发邮件/通知。

开发者工具当前观察2.02.2611022、基础库3.17.5。新增页面须带page.json；SDK0.13.0在更新工具后存在旧页面元数据/方法调用时序问题，夹具以当前路由和真实界面数据等待，不把瞬时失败算通过。不得用清storage/auth/session等缓存修复代码问题。


## 本轮逐项本地验收与手机项目

管理与外观本地验收见 `docs/MINIPROGRAM_LOCAL_ACCEPTANCE_20261103.md`，三阶段真实本机流程及89项客户端回归已记录。外层 `offline-evaluation/miniprogram-acceptance-20261103-01/visual-review.html` 可查看网页/原生对照。固定网页UI/接口仍为8da1609；网站并行维护发布变更如实单列，未纳入本分支。

生成独立离线手机项目（只创建本地目录，不执行预览/上传）：

```powershell
node tools/prepare_phone_local.cjs ../offline-evaluation/miniprogram-acceptance-20261103-01/phone-local
```

必须先提交本轮miniapp源码；脚本拒绝覆盖已有项目，验证固定依赖/运行数据和两服真实计算。副本API关闭，车库与视图使用独立devicecheck存储前缀，不带原账号/测试状态。由用户按 `docs/PHONE_ACCEPTANCE_20261103.md` 手动导入和预览扫码；不将其视为体验版/正式冻结包或真实网络识图验收。当前主项目8058仍只供开发者工具fixture，不能让手机访问127.0.0.1或绕过fixture平台保护。
