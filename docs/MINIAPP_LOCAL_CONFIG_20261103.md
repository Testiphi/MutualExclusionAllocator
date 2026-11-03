# 小程序真实项目配置仅留本机（2026-11-03）

GitHub告警命中此前302d547d提交中miniapp/project.config.json的真实App ID。本次停止跟踪实际配置并加入ignore，本机现有文件、App ID及开发者工具现场保持；不在文档记录真实值。仓库改为project.config.example.json（touristappid）及tools/setup_miniapp_project.cjs。

新检出先运行 `node tools/setup_miniapp_project.cjs`，生成被忽略的本机project.config.json，再由用户在开发者工具中配置自己的项目。也可通过本机RACEPICK_MINI_APP_ID环境变量提供App ID，工具不回显值；已有文件不会被覆盖。AppSecret、私钥、会话令牌始终不写入客户端配置或提交。

本次仅修正Git配置跟踪，不操作微信后台、不改AppSecret、不上传/提审、不改生产。真实App ID已存在于远端历史提交；普通删除提交不会抹除历史，也不宣称GitHub告警已关闭。未自动force-push或改写历史。定向检查发现App ID只在小程序分支该配置出现，未发现已跟踪文本中的AppSecret字面值；这不是全历史、全类型凭据扫描的替代。
