# RacePick 账号与投稿审核：首次生产部署

当前状态（2026-10-20）：账号、真实邮件验证/重置、车库同步、投稿审核与管理员邀请已上线，用户公网验收通过；自动备份已启用。正式成绩写回继续仅本地。详细验收与证据范围见文末。

本包范围：账号注册、真实邮箱验证、密码重置、个人车库、投稿及审核、超级管理员和管理员邀请码。成绩采纳只保存审核决定，不自动改正式JSON。公网不安装只读变更预览及写回接口，也不包含写回实验室文件、数据库、测试账号、既有工作簿或SMTP密码。

目标：Ubuntu 24.04、x86_64、Python 3.12；域名https://racepick.cn。若服务器架构不是x86_64，先停止并重新制作相应依赖包。依赖wheel及哈希锁已随包提供，安装无需联网到PyPI；系统python3-venv仍需已安装。

## 0. 只读预检，先回传结果

```bash
uname -m
python3 --version
systemctl is-active nginx
nginx -t
cat /etc/nginx/sites-available/racepick
ss -lntp | grep -E ':80 |:443 |:8001 '
df -h / /var
```

先核对当前HTTPS/证书与端口配置，再按下列步骤部署。端口8001只监听回环，不增加公网安全组规则；保留已有80/443和Certbot续签。

## 1. 上传并暂存完整包

上传交付目录中的所有文件到服务器新目录，例如`/root/racepick-deploy/accounts-release/`。不覆盖旧静态发布包。

```bash
cd /root/racepick-deploy/accounts-release
sha256sum -c SHA256SUMS.txt
python3 deploy_production.py --bundle racepick-accounts-release.zip
```

记录输出的24位版本ID，后续将`VERSION_ID`替换为它。此步只暂存到`/opt/racepick/releases/VERSION_ID`，不切换网站。

## 2. 安装独立运行环境和服务用户

若没有venv，先安装系统依赖：

```bash
apt-get update
apt-get install -y python3-venv
```

```bash
id racepick || useradd --system --home /var/lib/racepick --shell /usr/sbin/nologin racepick
install -d -o racepick -g racepick -m 700 /var/lib/racepick
cd /opt/racepick/releases/VERSION_ID
bash production/install-runtime.sh
```

脚本校验架构/Python版本，离线按哈希安装，并用临时数据库跑原生HTTP冒烟。未发送邮件，未创建正式账号，未修改Nginx。失败时先查看错误，不激活或覆盖已有venv。

## 3. 隐藏输入SMTP密码，初始化全新正式库

```bash
python3 production/configure.py
```

按提示输入用户确认的主邮箱（即后续注册并验证的超级管理员邮箱），以及两遍阿里云SMTP专用密码。密码不会进入命令行参数、终端回显或Git；root文件`/etc/racepick/smtp-password`权限600，由systemd LoadCredential提供给服务。配置文件640、目录750，服务仅能读取非密码配置。SMTP发信地址沿用已测试的no-reply@notify.racepick.cn，SSL465。初始总额度100次/24小时、每账号6次/24小时、同用途60秒冷却；如需调整总额度修改配置后重启。

```bash
runuser -u racepick -- /opt/racepick/releases/VERSION_ID/.venv/bin/python -B -m backend.production init
```

在当前版本目录执行。初始化仅接受空的`/var/lib/racepick`；若非空会拒绝，不删除、不覆盖、不导入本地账号。成功后库为v6、没有用户和模拟投稿。

## 4. 激活应用服务，先测试回环

```bash
cd /root/racepick-deploy/accounts-release
python3 deploy_production.py --version VERSION_ID --activate
install -m 644 /opt/racepick/current/production/racepick-accounts.service /etc/systemd/system/
install -m 644 /opt/racepick/current/production/racepick-backup.service /etc/systemd/system/
install -m 644 /opt/racepick/current/production/racepick-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now racepick-accounts
systemctl status racepick-accounts --no-pager
curl --fail --silent --show-error -H 'Host: racepick.cn' -H 'X-Forwarded-Proto: https' -H 'X-Real-IP: 127.0.0.1' http://127.0.0.1:8001/api/health
```

应返回status=ok、mode=production、schema=6。应用通过Nginx接收可信客户端IP；不信任任意Forwarded链。系统服务只监听127.0.0.1:8001，不能直接公开该端口。无访问日志中的请求参数或邮件链接。此时公网仍是原静态站。

## 5. 备份并调整现有Nginx，确认后切流

先保留当前配置，记录实际备份文件名：

```bash
cp -a /etc/nginx/sites-available/racepick /etc/nginx/sites-available/racepick.before-accounts.$(date +%Y%m%d-%H%M%S)
```

核对预检得到的完整配置后：
- 将`production/nginx-rate.conf`安装到`/etc/nginx/conf.d/racepick-rate.conf`（http上下文）。
- 在现有racepick.cn的HTTPS server内，用`production/nginx-https-location.conf`替换原`location /`，不要追加重复location。
- 保留原有证书路径、Certbot配置及80端口跳转/验证配置。
- 不把发布目录、数据库、凭据目录设为Nginx公开root；所有应用请求交给上游白名单路由。

修改完成后：

```bash
nginx -t && systemctl reload nginx
curl -I http://racepick.cn/
curl -I https://racepick.cn/
curl --fail https://racepick.cn/api/health
```

不通过时不要反复改证书；按第8节回到静态配置。

## 6. 注册主号、真实邮件验收并提升权限

在https://racepick.cn注册配置中的主邮箱，由用户自行输入正式账号密码（不是SMTP密码）。从163收件箱打开链接，点击确认并验证登录。然后在服务器执行：

```bash
cd /opt/racepick/current
runuser -u racepick -- .venv/bin/python -B -m backend.production bootstrap-owner
```

只允许提升配置中已验证的主邮箱，已有其他超级管理员则拒绝替换；提升前自动备份数据库，旧会话退出。主号重新登录应显示超级管理员，普通注册仍为玩家。

接着分步验证：注册/重发邮件、密码重置、新密码可登录、旧密码及旧会话失效、投稿、评分/补充/忽略、管理员邀请码及权限隔离。测试投稿完成后忽略并保留历史，不采纳虚构成绩。

必须确认公网`/data-previews`、`/writeback-lab`、`/api/admin/writeback`均404；公开成绩JSON未因采纳而改变。浏览器Cookie应有Secure、HttpOnly、SameSite=Strict。

## 7. 开启备份并记录验收

```bash
systemctl enable --now racepick-backup.timer
systemctl start racepick-backup.service
systemctl status racepick-backup.service --no-pager
systemctl list-timers racepick-backup.timer --no-pager
```

备份保存在`/var/lib/racepick/backups`，使用SQLite backup API并校验完整性和外键，可在服务运行中备份。定时备份不自动删除历史，定期检查空间并将需要的备份复制到另一安全位置。权限只给服务用户/root，Nginx不可下载。上线验收另行记录，打包或本地测试通过不等于服务器已验收。

## 8. 回退与恢复

**首次上线故障，优先回到原静态网站：**
恢复第5节记录的Nginx备份（用真实文件名），执行`nginx -t && systemctl reload nginx`；静态内容仍在原`/var/www/racepick-releases/current`。停用新应用服务，但保留新数据库及备份，不删除用户已注册资料。再次上线前先修复并验收。

**后续应用版本回退：**
先备份数据库，停止racepick-accounts，再用`deploy_production.py --version 旧版本ID --activate`切回已经验证的兼容版本，启动并验证health。版本切换不自动恢复数据库，必须核对schema兼容性；当前只支持v6。

**仅在确定需要恢复数据时：**
恢复会将业务数据回到备份时点，之后的注册/投稿可能不在旧备份中。先停止服务，保存现有库，再执行：

```bash
systemctl stop racepick-accounts
cd /opt/racepick/current
runuser -u racepick -- .venv/bin/python -B -m backend.production restore --backup /var/lib/racepick/backups/选定备份.sqlite3
systemctl start racepick-accounts
```

工具使用独占服务锁，在线时拒绝恢复；恢复前再次备份当前库，检查兼容schema和超级管理员邮箱，恢复后撤销全部会话及未使用验证链接。工具拒绝测试写回数据库和未处理SQLite日志文件。恢复后需重新验收，不自动发布任何成绩。


## 构建与验证记录（2026-10-20）

功能分支实现生产适配，真实账号密码/SMTP凭据均不随包。打包器绑定干净代码提交、正式JSON来源提交及每文件SHA256，单独读取repo当前JSON/cars，不读取或改动两份工作簿。静态旧部署工具仍保留原功能，生产账号包使用独立deploy_production.py。

本轮Python应用回归82项执行81通过、1项Linux专用跳过；生产包校验/暂存/篡改/路径白名单测试3项通过，总计84通过、1跳过。JS回归51项、启动冒烟和账号脚本语法检查通过。生产SMTP测试使用mock，不发送邮件；临时生产数据库HTTP冒烟通过；Linux Python3.12离线wheel集合按哈希离线解析通过，版本与本地验收版本一致。Windows不能替代Ubuntu原生运行，install-runtime.sh会在服务器切流前进行原生冒烟与Linux独占恢复锁校验。

实际发布、主号注册验证、服务器收发邮件、Nginx切流、Certbot续签及在线恢复演练尚未在服务器执行，不宣称已经上线。


### 2026-10-20 systemd凭据兼容修复

服务器实际LoadCredential呈现root:root目录550、文件440，原始SMTP文件600 root:root。原启动检查把组读权限一律拒绝，导致服务启动前退出，尚未发生SMTP认证。修复只接受本服务固定/run/credentials/racepick-accounts.service下的root所有只读目录500/550及普通文件400/440，拒绝符号链接、可写/其他用户权限、异常所有者及路径，不修改原始秘密权限。新增元数据和路径回归测试。

此前原生HTTP冒烟没有通过systemd凭据加载入口，因此不能覆盖此兼容问题；修复后仍须实际启动systemd服务并检查health。更新时保留/etc/racepick及/var/lib/racepick，仅暂存新版本、安装该版本venv，再切换应用版本和重启服务；不要重跑configure.py或production init，不切换Nginx。


## 2026-10-20 正式上线与用户验收完成

### 发布与运行状态

- 域名：https://racepick.cn；已部署版本`3ac58aba697f3189b751d6ea`，代码提交`11bd7708e5109787642235d5dff00cda39b461c9`。本次文档提交不改变服务器正在运行的发布包。
- 用户回传Ubuntu服务器x86_64、Python 3.12.3；离线依赖安装与服务器原生冒烟通过。
- systemd凭据兼容修复后，用户确认racepick-accounts为active (running)，只监听127.0.0.1:8001；回环及公网health均返回status=ok、mode=production、schema=6。
- Nginx已将HTTPS网站接入账号服务；用户回传HTTP 301转HTTPS、HTTPS首页200，并确认页面出现登录/注册。原有证书配置保留；本轮未重新执行Certbot续签验收。
- 使用全新生产数据库，未导入本地账号、密码或模拟投稿。主邮箱完成真实验证后通过bootstrap-owner设为超级管理员，重新登录可打开审核工作台和邀请码管理。本地账号和数据继续保留。

### 用户确认通过的公网验收

| 项目 | 结果 |
|---|---|
| 注册与邮箱验证 | 163收到重发验证邮件，链接确认后能正常登录 |
| 密码重置 | 真实重置邮件收到；新密码可登录，旧密码拒绝，旧登录会话失效；超级管理员权限保留 |
| 车库及星级保存 | 修改后刷新、退出重新登录均保留 |
| 投稿审核 | 投稿、补充重提、审核评分及忽略通过 |
| 权限隔离 | 普通玩家与受邀管理员权限隔离通过 |
| 公网写回边界 | 用户确认没有开放正式成绩写回入口 |

上述运行状态和公网验收来自用户逐步回传的命令输出及明确反馈；不是代理直接登录服务器或独立公网复测的结论。未执行生产数据库恢复演练或正式成绩写回。

### 邮件问题处理记录

上线过程中SMTP凭据与阿里云当前密码不一致，发信记录为failed/authentication。更新服务器凭据并重启后，重复注册已有账号不会重新发送验证邮件，通用注册提示曾造成误解；用户从“重发验证邮件”表单实际提交后收到邮件并验证成功。网站登录密码与SMTP专用密码独立，前者最少12位不会限制后者。密码、验证链接及真实邮箱未加入本次公开文档。

### 自动备份状态

- 用户手动执行racepick-backup.service成功，日志显示Deactivated successfully/Finished；一次性任务结束后inactive (dead)为正常状态。
- 已确认备份文件：`accounts-20261020T144914248192Z.sqlite3`和`accounts-20261020T151426867682Z.sqlite3`，均为168K、racepick:racepick、权限600，存于`/var/lib/racepick/backups/`。
- racepick-backup.timer已enable并启动。用户回传NEXT为**2026-10-21 04:19:24 CST**，符合04:15加最多5分钟随机延迟。
- 回传时LAST为`-`：定时器尚未首次触发。已确认的是手动备份成功及定时器启用，不能记为自动备份已实际运行成功；首次定时执行结果仍待后续查看日志。没有创建额外监控或提醒任务。
- 备份仍在同一服务器上；本轮未完成异机备份或生产恢复演练。后续按需检查磁盘空间、保留策略及恢复可用性。

### 保持的范围

正式成绩写回、逐项应用/回滚和工作簿同步继续仅在本地隔离环境；公网采纳只保存审核决定，不自动修改JSON。工作簿不随账号发布修改。本次收尾仅更新文档并推送feature/accounts-local，不合入main，不改线上配置或数据，不重建发布包；沿用已有自动化检查与以上用户验收，无需重复运行应用测试。


## 2026-10-20 功能分支正常合入main

用户授权将已上线验收的账号功能分支合入main，仅做源码整合，不重新部署线上服务。合并前本地/远端main均为4b34b85422b1fe94699a70689d69863a958b6e34，功能分支均为a861daf3ebae031fc8b642e800245e4594bec0b0，共同基点a3d01fb。main独有两次成绩维护提交，功能分支独有19次提交；双方修改文件不重叠。

使用正常三方合并`git merge --no-ff feature/accounts-local`，合并提交为**38268534294b046dc29e6e5bd09e4fbc27787bda**，父提交依次为4b34b85和a861daf，无冲突，未使用目录覆盖、强制重置、stash或clean。功能分支保留，不删除。

### 数据与工作簿保护

合并后的gauntlet_data.json、cars.json、gauntlet_data.xlsx Git对象与合并前main完全一致，保留main最新成绩维护。合并及测试前后，下列磁盘文件的SHA256、大小与纳秒修改时间均不变：

| 文件 | SHA256 |
|---|---|
| gauntlet_data.json | 9142daa5ebcebb43d750b381385b85ef918c1777eff42590564142e91d94dc9c |
| cars.json | 02018b620074173f0aaa560f5ecad43046c02731d0065c7ee2d1a578259fd67d |
| gauntlet_data.xlsx | fba396a6b179060b64afcf507a3420fc3c3bf41bf8484358b851fe6b22be6248 |
| gauntlet_data_shared.xlsx | ecff22a681fc2e1392d91ca81f6dd6c582d6f28e2b6d4863161ea636039f073d |
| _star_curve_fit.py | 8e5448fd5d7c56890ee6976ec24328b8f2d6aa2d4b7e667fcd15fdb706ec23d6 |

共享工作簿和_star_curve_fit.py原为未跟踪文件，仍保持原状态，未纳入提交。未读取或控制Excel会话，未保存其可能存在的未落盘编辑；未导出、回代或重写现有工作簿。账号及测试数据库没有迁移或复制。

### 合并后验证

- Python账号、邮件、权限、投稿、预览、隔离写回、生产入口、发布工具、数据工具和车库规则共135项执行：134通过，1项Linux专用检查在Windows跳过。
- JS账号资料、分配算法及剪枝、成绩与状态回归51项通过；页面启动冒烟通过。
- main当前JSON数据校验零错误；生产入口临时数据库HTTP冒烟通过，未发真实邮件。
- Git差异空白检查通过；生产入口仍拒绝启用预览/写回实验室，生产发布白名单仍排除写回实验室文件和工作簿。

源码合入main不等于重新部署：线上继续使用已验收的3ac58aba697f3189b751d6ea发布包（代码11bd770）。本轮不重建发布包、不重启服务、不改Nginx、不访问或修改生产数据库；正式成绩写回仍只留在本地隔离环境。自动备份首次定时触发尚无新回传，不更新其验收状态。
