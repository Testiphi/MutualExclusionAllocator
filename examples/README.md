# 本地隔离演示

从仓库根目录运行：

```powershell
python examples/contribution_demo.py
python examples/feedback_demo.py
```

脚本会新建独立本地测试环境，包含演示账号、测试成绩和邮件材料。不要在正式服务器运行，也不要将生成的测试资料上传。具体验收流程见 [排行榜说明](../docs/CONTRIBUTIONS_LOCAL.md) 和 [反馈说明](../docs/FEEDBACK_LOCAL.md)。

- `unread_demo.py`：新建独立未读提醒演示环境，打印专用路径和登录说明；不复用现有库。
- `home-unread-preview.html` / `unread-marker-preview.html`：静态样式对比，不代表真实未读数量。

- `usage_demo.py`：新建独立统计演示环境及模拟分布，使用8017端口；不复用8016的未读验收数据，不代表线上用户分布。
