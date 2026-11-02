# RacePick 微信原生客户端 · 本地开发

本轮基线 `f47ff1982ea0fc266beeaa5bfcf9b73968927ebc`，分支 `feature/miniprogram-v1`。
当前启动固定使用独立 mock：目录为“联调区域/赛道/车”，结果无真实成绩，识图返回脚本五槽。页面持续显示 mock 状态，不连接网络、不调用 wx.login、不上传照片。它用于验收客户端流程，不是可交付体验版。

在仓库根目录执行：

```powershell
node tools/prepare_miniapp.cjs
node --test tests/test_miniapp.cjs
node --test tests/test_allocator.js tests/test_allocator_pruning.js tests/test_race_scores.js tests/test_app_state.js
```

`prepare_miniapp.cjs` 只生成 `miniapp/shared/` 四个 CommonJS 源文件和 SHA 清单；这些文件被忽略，不手动维护。共享源存在未提交改动时构建拒绝继续。没有把网页内候选生成复制到客户端。实际使用共享选择模块前，先由网站分支实现并验收协调单中的接口。

安装微信开发者工具后，导入当前目录 `miniapp`。配置为 `touristappid` 本地占位、合法域名检查开启；工具对游客项目的实际限制需现场核验，不能代替真实 AppID 权限。未固定或猜测基础库版本，建议先选择工具可用的稳定基础库，记录准确版本；当前用到的 chooseMedia 从 2.10.0 支持、安全随机数从 2.15.0 支持，隐私指南说明 2.32.3 以下缺少相应隐私拦截，最终最低版本须真机确认。

导入后可按顺序选择五个不同区域的小地图、展开车库选车/改星、保存/恢复、生成 mock 结果；切国际服检查独立草稿及 OC。国服选择相册图片后只在本机预览，点“开始识别”仍是 mock；核对/补齐五槽并确认后才替换手选。取消不改原选图。

草稿键为 `racepick.mini.mock.draft.v1.cn/global`，真实环境将使用独立 `native` 命名空间。前后台会取消旧结果发布，隐藏时尝试保存；存储失败阻止切服并保留内存选择。损坏或未知 schema 草稿保持原记录且禁止覆盖，当前先排查存储，不自动清库。临时照片路径不写入草稿。

原生页面代码不包含 AppSecret、session_key、生产地址或用户账号。transport 只有默认关闭的低层接口；会话交换、原子缓存、任务轮询/取消/过期恢复及隐私实接仍待网站契约和真实服务。mock 不构成后端、内容安全、工具模拟器、真机或审核证据。

详见 `docs/MINIPROGRAM_CLIENT_HANDOFF_20261102.md` 与 `docs/MINIPROGRAM_CROSS_BRANCH_REQUESTS_20261102.md`。不运行上传、预览分发、提审或发布命令。
