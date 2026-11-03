# 主页镜像第二轮：实施与验证

2026-11-03。分支 `feature/miniprogram-v1`，接手基线 `c6e6bf142e2a96361259a1405a01cfbdd8459ba4`。个人主体已确认，web-view不适用；原生页面继续按网页镜像，不另设计产品。完整范围/缺口见 `WEB_MIRROR_SCOPE_20261103.md`，供用户转交的网站侧接口清单见 `HANDOFF_WEB_FULL_MIRROR_20261103.md`。

## 本轮实际变更

- 保留网页背景、颜色和控件值；OCR区域置于地图上方，五图表单和结果按手机网页宽度换行；车辆自然宽度标签，生成按钮按内容居中。地图/星级/SC类型/方案均页内下拉；顶部重复标题继续为空。
- 首次进入CN高手/Global理论、初始全选车池；已保存的合法空车库不补车。搜索别名、等级筛选、排序、单图前三与副标题来自固定网页源码；候选、估算与分配继续共用五模块。
- 输入变化自动重算，忽略未完成地图槽；空车库可生成留空方案。单图前三不扣除其他图用车。结果补星级/OC，成绩两位小数，保持原方案顺序。
- 显式保存与临时试算分离；后台和切服只写working，不覆盖已保存车库。保存时检测已保存基线变化；冲突/损坏保持原记录。恢复保留当前地图/区档/SC，临时记录清除失败保留当前选择。
- native模式选相册截图即开始识别；保留取消、重新识别/查询、核对确认后填图及前后台原任务恢复。选择器仅album，说明清晰显示五图中文名，不支持拍屏照片。

## 来源与复现

五模块 `allocator.js/race_scores.js/app_state.js/profile_store.js/selection_core.js` 仍从Git对象 `198999a9ff5ca2ad524c50112ac6e03f5f18149f` 原字节生成。新增 `tools/web_home_adapter.cjs` 从同对象index.html提取网页函数及常量，严格边界检查，生成文件 `shared/web_home.js`；源SHA `802d2191b65e10ff4844d85d0ec28715940ba37c0c7a9bcbb8445928e929c35f`，生成SHA `42582b8ae35ebb3ed73cfd201e7700a2b8c71a33b5a8a6081f3405e490058dd5`。不读取网站dirty页面，不提交生成物/运行JSON，不修改网站公共文件。该提取适配是过渡方案，正式共享presenter由网站归口。

运行数据仍为接收回执批准的五份4504/693文件，未重新冻结。网站API固定交付c26a708；创建新独立fixture lab，不复用已过期会话或修改原状态：

```powershell
# 在网站树执行；只新建隔离状态，读取既有模型路径，不复制账号库
python -B -X utf8 -m backend.mini_local create --source . --receipt ..\offline-evaluation\data-sync-20261102-01\sync-receipt.json --model-config ..\.score-version-sandboxes\9f326b2976b6637b90f07be5\config.json
python -B -X utf8 -m backend.mini_local serve --lab E:\hzz\work\MutualExclusionAllocator\.score-version-sandboxes\ed2e413010a67355e2a0f0f3 --port 8044 --fixture-auth
```

本轮lab `ed2e413010a67355e2a0f0f3`，独立guest state `973d9f6494047616e7f4fa60`。初始观察PID69036仅历史记录，后续不可凭旧PID操作。fixture-code-1首次key `client-fixture-session-20261103`，过期后不能续用；客户端token仅内存，不入文档/文件。工具本机8044不是手机可达地址或登记HTTPS域名。生成配置/工具复现命令见miniapp/README.md。

## 验证证据与限度

外层 `offline-evaluation/miniprogram-home-mirror-20261103-01/`：

- `node-tests.log`：64项客户端测试通过，包括默认/合法空车库、临时草稿/保存冲突/恢复失败保全、自动计算、单图候选与生成来源一致性。
- `final/native-ocr-report.json`：六组开发者工具检查通过、exceptions空、storageRestored=true；基础库3.17.5、390×753、platform=devtools。覆盖真实wx.request及快照核验、全选/排序/自然宽度/星级下拉、自动计算/前三展开/两位小数、wx.uploadFile/CPU OCR、模拟hide/show同任务不重传、确认填图与共享分配/方案下拉。
- `final/*.png`：工具截图。仅相册选择被替换为用户此前批准的attack06.png受控样图；一次真实上传，同worker五图顺序正确。fixture身份不是真实微信鉴权，模拟生命周期不等于真实手机切后台。
- 最后一处空方案控件由原生disabled button换成静态暗色view以避开工具默认白底，随后64项测试通过；该纯模板调整在上述六组OCR检查之后，最终工具截图 `final/empty-results.png` 已目视确认暗色空方案状态。补充脚本的style查询曾在SDK超时，不算通过证据；移除该查询后截图成功，不影响之前完成的六组检查。

未运行iOS/Android真机、真实wx.login交换/手机相册、真实TLS域名或图片安全服务。后台/弱网/存储边界的单测不等于真实设备验收；未重新运行网站全量测试，网站源未修改。未操作生产/微信后台/上传体验版/提审/上线，审核状态仍未知。

## 剩余工作

主页不是完整网站镜像：账号/云车库、完整成绩表/权益、投稿/贡献榜、反馈/公告/消息、角色管理页面仍需网站提供原生业务契约，不用空壳或mock冒充已迁移。用户将具体交接单给网站侧协调；本分支不抢写公共源码，也不自动向其他对话派任务。后续按交回的固定契约接页面，再做同角色/同服/同数据对照与真机验收。
