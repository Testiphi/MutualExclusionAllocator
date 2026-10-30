# 擂台成绩表紧凑入口 · 本地待用户验收

用户选定紧凑入口，授权本地实施。本轮未合并 main、提交推送、构包、上线或发布公告。

## 分支、基线与修改

- 工作树：`E:\hzz\work\MutualExclusionAllocator\coverage-entry`。
- 分支：`feature/coverage-entry-compact`；基线：`336730fb7ab8266eab995d291a9e4158782e47b5`。
- 管理工作树工具因外层工作区非 Git 仓库返回 Not a git repository，改用实际 repo 仓库的 `git worktree add` 新建；未搬走主树未完成内容。
- `backend/app.py`：覆盖表启用时，在首页副标题下渲染紧凑入口。两服文案均为“查看各图参考成绩，补充缺失记录”，国际服链接保留 `server=global`。国际服投稿为本轮后续新增，见 GLOBAL_SUBMISSIONS_20261030.md；早期截图的“国际仅浏览”文案已被后续实现替代。
- `styles.css`：沿用已有深色主题，仅对 `.coverage-entry` 局部增加低强度蓝色底和边框；桌面说明在左、按钮在右，520px 及以下按钮换行占满入口宽度。标题、标志和原主操作颜色不改。
- `auth.js`：启用入口时将账号区插在入口后；无覆盖表时仍沿用副标题后的原位置。防止账号初始化将新入口推到下面。
- 用户后续明确要求“不要做点击后隐藏，等到下次再有新功能更新的时候再改”。新功能标签常驻，不设置到期时间，不读写访问标记，不随点击或刷新隐藏。下次功能更新时再按用户要求调整；`index.html` 中本轮新增的标签逻辑已完整移除，恢复原字节。没有新账号字段或服务端已读状态。

未改成绩、车辆规则、地图映射、估算、工作簿、维护台账、投稿/解锁规则、数据库结构或依赖。入口继续受既有 coverage 开关控制，静态模式不凭空开放覆盖表页面。

## 验证与边界

- 43 项 JS 通过：coverage、quick_submissions、profile_store、global_frontend、bootstrap_retry。
- 启动冒烟通过；`node --check auth.js` 与 `git diff --check` 通过。
- 14 项后端通过：`python -B -X utf8 -m unittest backend.test_coverage backend.test_coverage_production`。全部使用测试夹具隔离库，未执行生产迁移。
- Chromium 布局检查：320/390/1280px × 国服/国际服，均无整页横向溢出；入口位于账号区前；按钮在入口内；文案和链接服别正确；没有页面脚本异常。
- 标签常驻的修订验证另见 `本地归档/coverage-entry-20261030/BADGE_ALWAYS_VISIBLE.json`：点击、真实进入后返回、刷新、模拟未来时间及已有旧访问标记均不隐藏标签。此前 BROWSER_CHECK.json 的隐藏行为检查仅为已取消方案的历史证据，不代表当前需求。
- 浏览器检查脚本、JSON 回执与四张实际页面截图：`本地归档/coverage-entry-20261030/`。
- 未重复全量后端、Linux 原生、真实手机微信或生产验收。用户选择的是设计方案，实际页面用户验收仍待确认。

## 可复现本地验收

本轮新建独立成绩版本实验室：`E:\hzz\work\MutualExclusionAllocator\.score-version-sandboxes\6885edd95fc9e1bcb4bb994a`。以本轮工作树冻结 JSON 生成，不复用或改动既有实验室；账号库新建，无预置账号或虚构权限。

当前本地服务：`http://127.0.0.1:8025/`；国际服：`http://127.0.0.1:8025/?server=global`。进程号只作启动快照，不作为后续进程操作依据。

如需在服务停止后复现，从本工作树运行（先确认 8025 未被其他服务占用）：

```powershell
python -B -X utf8 -m backend.app --port 8025 --data-dir 'E:\hzz\work\MutualExclusionAllocator\.score-version-sandboxes\6885edd95fc9e1bcb4bb994a\accounts' --score-version-lab 'E:\hzz\work\MutualExclusionAllocator\.score-version-sandboxes\6885edd95fc9e1bcb4bb994a' --contributions --coverage
```

1. 先看桌面与手机窄屏的入口、账号区和原选图区域是否协调。
2. 点击“查看成绩表”，确认进入对应服别；返回首页或刷新后，新功能标签仍显示。
3. 无需清理浏览器存储来查看标签，已有旧访问标记也不影响显示；不要为验收清空 localStorage、账号库或车库。
4. 实际手机微信由用户在可达的验收环境确认；本机回环 URL 不能直接作为手机可访问地址，不自行开放网络或改防火墙。

## 后续发布边界

本次仅三份现有源码修改（backend/app.py、styles.css、auth.js）及本说明未提交。主 repo/main 的部署文档修改和未跟踪文件保持；未自动合并其他工作树。

后续须用户确认实际页面，再明确提交推送/合并/构包授权与数据来源。既有 bbd92687 包没有本轮修改，不能声称新入口已构包或上线。若以后发布仅此功能，所需源码为上述三份现有文件，无新增发布白名单、依赖、Nginx、系统服务、环境变量或迁移要求；仍须按现行完整包流程和生产现场状态核验。本地冻结国服 JSON 不能覆盖生产 score-state。
