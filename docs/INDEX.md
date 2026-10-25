# 文档索引

当前功能：未读提醒与使用统计已获用户本地验收，通过本轮授权提交推送功能分支；不合并main、不构包、不上线。数据独立接收，见 [20261025接收回执](DATA_RECEIPT_20261025.md)。下方历史“未提交/本地开发”标题保留其开发阶段含义。

仓库说明集中在 `docs/`。以下路径从本目录出发；发布包仍沿用已验证的文档文件名和包内位置。

## 当前交接与部署

- [云端交接记录](CLOUD_HANDOFF.md)：从最新记录开始，区分历史验收与本轮现场证据。
- [可复用交接提示词](CLOUD_HANDOFF_PROMPT.md)
- [生产部署流程](PRODUCTION_DEPLOYMENT.md)
- [快速切换服别的限流修复（599条已上线验收）](SERVER_SWITCH_FIX.md)
- [国际服部署与范围](INTERNATIONAL_DEPLOYMENT.md)
- [成绩版本与生产写回](SCORE_PRODUCTION_DEPLOYMENT.md)
- [静态部署](DEPLOYMENT.md)

## 功能开发与验收

| 功能 | 本地说明 | 部署或专项说明 |
|---|---|---|
| 国际服 | [本地与维护范围](LOCAL_INTERNATIONAL.md) | [部署](INTERNATIONAL_DEPLOYMENT.md) |
| 账号 | [本地账号](ACCOUNTS_LOCAL.md)、[邀请](INVITATIONS_LOCAL.md)、[邮件](MAIL_LOCAL.md) | [生产](PRODUCTION_DEPLOYMENT.md) |
| 投稿 | [成绩提交](SUBMISSIONS_LOCAL.md)、[预览](PREVIEWS_LOCAL.md) | [成绩生产流程](SCORE_PRODUCTION_DEPLOYMENT.md) |
| 公告与账号管理 | [本地](COMMUNITY_LOCAL.md) | [部署](COMMUNITY_DEPLOYMENT.md) |
| 贡献排行榜 | [本地](CONTRIBUTIONS_LOCAL.md) | [部署](CONTRIBUTIONS_PRODUCTION.md) |
| 反馈 | [本地](FEEDBACK_LOCAL.md) | [部署](FEEDBACK_PRODUCTION.md) |
| 车库布局 | [布局修复](GARAGE_LAYOUT_FIX.md) | [部署](GARAGE_DEPLOYMENT.md) |
| 成绩版本 | [本地版本](SCORE_VERSIONS_LOCAL.md) | [写回实验环境](WRITEBACK_LAB.md) |

## 未读提醒（独立工作树本地开发）

- [功能、隔离演示与验收](NOTIFICATIONS_LOCAL.md)：尚未提交、构包或上线；首页/菜单/条目按账号未读。

## 使用统计（本地开发，未提交）

- [采集口径、统计页、隔离演示与部署边界](USAGE_LOCAL.md)：新端口8017；模拟统计与线上事实分开。

## 数据维护

- [Python工具](PYTHON_TOOLS.md)
- [赛道标签](track_tags.md)
- 根目录保留数据文件和维护工具入口；`tests/` 存放顶层回归测试，`backend/` 内的后端测试继续与模块同目录，`examples/` 存放隔离演示脚本。

旧文档中的历史提交、线上版本及验收结果仅作为历史记录，不代表实时服务器状态。
