# RacePick 原生OCR第二阶段：完整本地候选交付

> 本文正文保留v2构包时的授权与状态，不是实时运维记录。后续CN服务端已获用户授权开启；实际是35bd交付加已记录的单文件运行依赖补件，唯一合成审核通过，真实微信/手机OCR尚待验收。最新状态以主repo `docs/CLOUD_HANDOFF.md` 文首及 `docs/MINI_OCR_CN_CLOUD_HANDOFF_20261104.md` 为准。本轮用户又明确授权分功能Git提交推送，不能用下方构包阶段“未授权提交/未上线”覆盖新授权或现场证据；历史封存包的source_commit=null等元数据仍保持原样。

先读本文件、docs/ALIYUN_OCR_RELEASE_PREPARATION_20261104.md、SOURCE.json、DATA_SOURCE.json、VALIDATION.json及RELEASE.json。

本包包含：a933网页基底加本轮共享后端兼容改动的完整网站ZIP、独立访客HTTP网关、唯一队列桥及真实阿里SDK传输、Ubuntu24.04/Python3.12离线wheel与分环境哈希锁、默认关闭配置、候选Nginx/systemd模板、合成验证源码及只读校验器。账号/B–E关闭，没有小程序上传/提审/发布。

外层ZIP先与旁边的.zip.sha256核对；解压后核SHA256SUMS.txt，再运行`python3 -B tools/verify_mini_ocr_delivery.py`。校验器核严格文件清单、逐文件SHA/大小、来源快照、离线锁及内层网站manifest。不要将外层ZIP直接交旧网站部署工具；只有website/racepick-accounts-release.zip是网站工具可读的内层包。

源码为封存的未提交工作区快照：source_commit/code_commit=null，base_commit只是开发基准，不冒充新提交。SOURCE.json逐项绑定实际交付源码；本轮未授权Git提交推送。数据沿批准冻结b57d97a8、清单SHA940f8660585c495a780390b709dfd52e80f7610f57e0179c5da937c53c4e4282、data_commit=null。五份4516/694运行JSON仅为测试快照/包种子，**不导入已有正式score-state、不改规则、不重复维护发布**。维护733、工作簿、账号/成绩/反馈库、凭据和用户私人截图均不在交付内。

默认image_policy=disabled、bridge enabled=false；配置检查不打开队列/凭据，包内没有真实AppSecret、RAM密钥、token、OpenID或测试SQLite。source/backend下的测试只含显式合成夹具，不是可导入业务数据。DEFAULT_EXPECTATIONS.json是默认关闭期望；OCR_EXPECTATIONS.json仅供未来明确开启并现场ready后核验，不能把它当公网已开证据。

服务器现状以工作区**主repo最新docs/CLOUD_HANDOFF.md**及用户本轮只读回传为准，不能用功能树旧记录或包内历史组件文档覆盖。最近完成的a933网站部署及global-profile/维护发布不是半途任务，本轮不续跑旧迁移。独立原生入口仍需保留既有访客状态、真实配置和固定快照，不重建或续期旧会话。

未来部署必须由用户另行授权、一次一个步骤：先只读核版本/健康/队列/容量/备份；成套备份和独立恢复通过后，再决定共用网站代码兼容升级及**识图队列safety_schema0→1**的显式迁移。它不是账号业务迁移；普通启动和serve均不自动迁移。新schema存在后不能切回旧a933队列容量代码，不能恢复旧账号库或删队列绕过检查。关闭OCR应保留session/snapshot/手选和原任务恢复/查询/取消。

所有模板均为候选，包含需填写的固定release路径、UID/GID和共享组；不得原样覆盖现行Nginx/systemd/证书/SMTP。templates/install-runtime.sh只适用于新暂存组件，拒绝覆盖已有.venv，不创建用户、状态、队列，不执行迁移/启动/切换。本次没有运行任何生产命令、真实传图或付费调用。

在完成实际源审核、Linux离线安装、兼容与容量核验、私有凭据安全配置和获准样图验收之前，公网OCR继续关闭。下一步所需配置及验证边界见交付准备说明。
