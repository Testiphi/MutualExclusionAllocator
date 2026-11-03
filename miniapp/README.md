# RacePick 微信原生客户端 · 本地开发

2026-11-03，独立分支 `feature/miniprogram-v1`。用户已确认个人主体，采用原生镜像；网站是唯一外观与功能基准。完整账号、成绩表、投稿及管理功能仍待网站侧契约，见 `docs/HANDOFF_WEB_FULL_MIRROR_20261103.md`，不把主页本地完成当全网站镜像完成。

## 构建与测试

在小程序工作树根目录执行：

```powershell
node tools/prepare_miniapp.cjs --data-receipt ../offline-evaluation/miniprogram-v1-20261102-01/runtime-source.json
node --test tests/test_miniapp.cjs tests/test_miniapp_local.cjs tests/test_miniapp_dropdown.cjs tests/test_native_api.cjs tests/test_recognition_jobs.cjs tests/test_web_home_mirror.cjs
```

该命令生成离线local模式，不调用登录或上传。省略数据回执则是明确标记的mock。五个共享模块从固定Git对象198999a原字节生成；另从同一index.html生成网页搜索/排序/单图候选/副标题函数，记录输入输出SHA。`miniapp/shared/`和`generated/`忽略，不将未冻结4504/693数据当发布来源。源网页函数边界变化时生成失败，必须核对后更新适配。

原生HTTP联调需显式增加 `--native-origin <本地基址>`。隔离fixture还需 `--fixture-code <lab中未用代码> --fixture-key <该代码首次使用的固定key>`，仅开发者工具接受fixture。接口默认关闭；token仅内存，快照严格核验后原子缓存。过期代码不能换key续期，应新建独立lab。当前本机8044联调环境和复现记录见 `docs/HOME_MIRROR_IMPLEMENTATION_20261103.md`。不用生产账号或8033测试库。

## 开发者工具

安装目录 `E:\Software\微信web开发者工具`，使用用户AppID，保持直连即可。用户已开启服务端口及本地跳过域名校验；后者只支持localhost开发，不代表已登记HTTPS域名或具备发布条件。工具曾更新重启，不沿用旧版本号作当前证据。

```powershell
& 'E:\Software\微信web开发者工具\cli.bat' auto --project 'E:\hzz\work\MutualExclusionAllocator\miniprogram-v1\miniapp' --auto-port 9420
node tools/check_native_ocr_devtools.cjs ../offline-evaluation/miniprogram-v1-20261102-03/automation/node_modules/miniprogram-automator ../offline-evaluation/miniprogram-home-mirror-20261103-01/new-run ../offline-evaluation/maps-20261031-01/samples/attack06.png
```

SDK为独立目录的官方miniprogram-automator@0.13.0。此脚本仅用于已显式配置的本机fixture，实际wx.request/uploadFile和CPU OCR；chooseMedia被受控样图替换，不是真实手机相册或微信鉴权。测试备份并恢复fixture两服saved/working/view键，删除自己创建的临时图片，检查token未持久化；不清理其他存储。旧 `check_miniapp_devtools.cjs` 是历史local页面验收脚本，未适配本轮布局，不作为本轮复现入口。

## 页面与存储

地图、星级、SC类型与方案均用页内下拉。截图只打开相册，说明必须清晰显示五图中文名称，不支持拍屏；识别后核对并确认再填图。CN首次高手、Global理论、首次全选均沿用网页；已保存的合法空车库保持空。选图/车库/星级/SC变化自动重算，单图前三只作参考，不扣其他图用车。

存储按mock/local/native/native-fixture及两服隔离：`racepick.mini.<模式>.draft.v1.<服>`是显式保存车库，`working.v1`是临时试算。后台/切服只暂存working；恢复已保存保留当前地图/区档/SC。已有损坏/未知schema及基线冲突记录保持，不静默覆盖。照片路径与token不写草稿；不自动读取浏览器车库或账号。云端账号车库尚未接入。

未执行生产、微信后台、上传体验版、提交审核或发布。真实微信登录、合法域名/图片安全策略、iOS/Android及用户验收仍待完成；审核未假定通过。
