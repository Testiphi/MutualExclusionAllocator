当前生产（2026-10-31，部署及用户验收完成）：OCR发布c06cc48b已上线，正式worker隔离及资源配置核验通过，用户桌面/手机微信验收均正常。仍使用原双服活动成绩（国际659，不导入包基线664），国际写回关闭。新版真实备份/独立恢复及timer恢复完成，未来自动执行尚未核验；见[CLOUD_HANDOFF](CLOUD_HANDOFF.md)文首、[部署回执](MAP_OCR_DEPLOYMENT_RECEIPT_20261031.json)、[执行记录](TAKEOVER_20261031.md)及[准备阶段核验](MAP_OCR_PREFLIGHT_20261031.md)。下方旧上线/未部署状态均为历史。

# 文档索引

当前交付：[覆盖表发布完成回执](COVERAGE_RELEASE_RECEIPT_20261029.json)、[云端可复制提示词](COVERAGE_CLOUD_PROMPT_20261029.md)。最终包9f9b2e2b已构建校验，未部署；fe8候选保留但已被替代；历史阶段状态以最新CLOUD_HANDOFF为准。

最新工作：[真实覆盖表与发布准备](COVERAGE_RELEASE_20261029.md)、[已有站点升级](COVERAGE_DEPLOYMENT.md)。用户已更新A方案范围，正式实现后与最新数据分组提交推送/构包；生产由云端运维另行执行。

最新本地整合：[20261029功能合并与数据配套](FEATURE_MERGE_20261029.md)。A原型不合并，数据未代提交，生产未操作。

最新本地修正：[审核意见合并输入](REVIEW_OPINION_20261027.md)，功能完成，用户验收待确认，未发布。

最新本地开发：[页面样式统一](STYLE_UNIFICATION_20261026.md)，独立分支样式已于2026-10-27通过用户本地验收，标志仅保留主页，未发布；A原型保留不合并；下方历史发布状态以CLOUD_HANDOFF最新记录为准。

本轮已完成main合并推送与完整构包（发布ID171d872a414dea28be25eaa1），未部署。先读 [完成回执](RELEASE_RECEIPT_20261025.json)、[云端交接提示词](UNREAD_USAGE_CLOUD_PROMPT_20261025.md) 与 [升级交接](UNREAD_USAGE_DEPLOYMENT.md)。历史限制仅对应此前阶段。

当前功能：未读提醒与使用统计已本地验收，构包源码7651da5、数据cbe9ea3。生产状态须运维现场核验；下方历史开发/接收记录不代表当前发布状态。

仓库说明集中在 `docs/`。以下路径从本目录出发；发布包仍沿用已验证的文档文件名和包内位置。

## 当前交接与部署

- [2026-10-30参考列与精简投稿完整包](COVERAGE_RELEASE_20261030.md)、[云端提示词](COVERAGE_CLOUD_PROMPT_20261030.md)、[机器回执](COVERAGE_RELEASE_RECEIPT_20261030.json)：本地构包完成，生产待核验；替代9f/fe8包。

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
