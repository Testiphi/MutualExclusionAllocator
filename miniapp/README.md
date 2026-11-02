# RacePick 微信原生客户端 · 本地开发

本轮基线 `f47ff1982ea0fc266beeaa5bfcf9b73968927ebc`，分支 `feature/miniprogram-v1`。
当前已接入网站固定提交 `198999a9ff5ca2ad524c50112ac6e03f5f18149f` 的共享选择模块。下列本地数据命令生成的客户端使用真实4504/693数据计算，持续标明数据未冻结、识图未接入。不连接网络、不调用 wx.login、不上传照片，不是可分发体验版。仅运行无数据参数的准备命令会生成独立 mock（联调车/地图），不把mock当真实计算。

在仓库根目录执行：

```powershell
node tools/prepare_miniapp.cjs --data-receipt ../offline-evaluation/miniprogram-v1-20261102-01/runtime-source.json
node --test tests/test_miniapp.cjs tests/test_miniapp_local.cjs
node --test tests/test_allocator.js tests/test_allocator_pruning.js tests/test_race_scores.js tests/test_app_state.js
```

`prepare_miniapp.cjs` 根据 `shared-source.json` 从固定Git对象生成 `miniapp/shared/` 五个 CommonJS 模块及 SHA 清单，不读取网站dirty源码。加数据参数时，严格校验本地回执五文件SHA/长度，再生成 `generated/local-bundle.js`；客户端启动再次验证原始字节及国际三件套版本。两目录均忽略，不手动维护，不把生成数据代提交为正式冻结。

开发者工具已安装到 `E:\Software\微信web开发者工具` 并运行，导入当前目录 `miniapp`。配置为 `touristappid` 本地占位、合法域名检查开启；工具对游客项目的实际限制需现场核验，不能代替真实 AppID 权限。CLI检测服务端口关闭，需用户手动在设置→安全设置开启服务端口后继续自动化。未固定或猜测基础库版本；当前用到的 chooseMedia 从 2.10.0 支持、安全随机数从 2.15.0 支持，隐私指南说明 2.32.3 以下缺少相应隐私拦截，最终最低版本须真机确认。

本地数据模式下可手选真实地图、选车/改星/OC，修改SC开关或具体类型并生成真实共享计算结果。关闭/重开SC记忆选择，切区不丢其他区车辆/星级。原生OCR未接入时会明确报错，不返回mock识图；只有无数据mock模式返回脚本五槽。

草稿使用 `racepick.mini.local.draft.v1.cn/global`，与 `mock/native` 命名空间隔离。前后台会取消旧结果发布，隐藏时尝试保存；存储失败阻止切服并保留内存选择。损坏或未知 schema 草稿保持原记录且禁止覆盖。临时照片路径不写入草稿。

原生页面代码不包含 AppSecret、session_key、生产地址或用户账号。transport 只有默认关闭的低层接口；会话交换、原子缓存、任务轮询/取消/过期恢复及隐私实接仍待网站契约和真实服务。mock 不构成后端、内容安全、工具模拟器、真机或审核证据。

详见 `docs/MINIPROGRAM_CLIENT_HANDOFF_20261102.md` 与 `docs/MINIPROGRAM_CROSS_BRANCH_REQUESTS_20261102.md`。不运行上传、预览分发、提审或发布命令。
