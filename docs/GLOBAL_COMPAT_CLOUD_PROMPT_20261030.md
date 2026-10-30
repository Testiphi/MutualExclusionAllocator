# 本轮完整归档与SHA256

E:\hzz\work\MutualExclusionAllocator\repo\.production-build\RacePick-Global659-Compat-20261030-3d978fd3-delivery.zip

SHA256：`34d11ecaa1a23dc3e9225f8838b209a611ac178c551152cf23007b302eabbf35`

源码：`1dba7e47eff47fb4423203e0008514aefb6337be`；发布ID：`3d978fd30812fa8f72ba928d`。以下为需要用户协调的运维交接，不是开发对话已执行的操作。

# 云端运维交接：3d978fd30812fa8f72ba928d

用户已授权开发对话构包与推送，并确认维护侧659数据冻结。请先核对完整归档外置SHA256、外层清单及内层manifest，然后仅回传第一步现场只读结果，不根据历史回执直接迁移。

源码 1dba7e47eff47fb4423203e0008514aefb6337be；国际种子 b5aa1a40fae685bb9440a78b0453125c4d063cad02d9610e39c4daa934872392；659运行/698完整维护，后者不入包。国服包内基线4458不能覆盖独立score-state。

第一步：阅读README.md和GLOBAL_SUBMISSIONS_DEPLOYMENT.md，运行01-readonly-preflight.sh，核对current/PIDcwd、health/组件、正式国服版本、国际实际版本、Nginx、备份timer和最近真实备份/恢复。随后用新版只读工具核对pending_batches与global_pending_batches、coverage实际schema和国际状态是否已存在。

首次运行：从新版本离线锁定安装并执行Linux原生临时库自检；完整备份/恢复演练→暂停timer/等待备份服务→停服MainPID0→停服最终成套备份/演练→coverage1→2→仅在国际未初始化时按批准659做global-score-state首次迁移→含双服的新备份/恢复演练→兼容门禁与激活→接口/用户验收→真实新版备份服务成功→恢复timer并核验调度。

国际初始化使用新版本目录作--source，明确指定--expected-dataset上述国际版本及--expected-cn-version现场国服版本；保持国际写回默认关闭，按用户授权决定enable，不顺带改变国服开关。已有国际状态不重播种。部分表、版本漂移或未完成批次须停止；不使用代码包替换正式成绩或导入测试库，不造真实权益验收数据。

如果现场已完整coverage2/global-score1，本次仅应用升级，必须保全原选图、事件、运行投稿和两服活动版本；不要再执行首次种子导入。退回旧无双服状态的应用不兼容；整套数据恢复须先保全新增并另获授权。

开发对话未登录或写生产；Windows测试不算Linux原生或生产验收。请由用户在运维对话逐步协调，无公告、自动清理或监控任务授权。
