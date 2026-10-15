# 完整版本发布与回滚

当前运行文件为九个，发布工具只打包这些文件，不包含工作簿、Python工具、Git或密钥。
2026-10-16 已根据用户回传的 Ubuntu 24.04 服务器输出验证暂存、current 链接启用和 Nginx 服务；真实服务器回滚尚未演练。
现有直接上传到 `/var/www/racepick` 的方式仍有效，不会被工具自动改动。

## 2026-10-16 部署完成记录

- 正式网站：https://racepick.cn/；网站名称：擂台选车助手；ICP 备案号：粤ICP备2026156614号-1。页脚链接到 https://beian.miit.gov.cn/。
- 域名 A 记录已指向 ECS；用户提供 DNS 查询结果，且手机移动网络访问通过。Nginx root 已切至 `/var/www/racepick-releases/current`，原 `/var/www/racepick` 保留。
- 首次完整版本：`a8d4f1f5e4b028caa54d1a3e`；备案页脚完整版本：`1a8333a8007d71b5e4588016`。后者仅 index.html/styles.css 与前者不同，用户已确认线上备案号与链接正常；第二次切换的终端输出未回传。
- Certbot Nginx 插件已配置 HTTPS；用户回传 HTTP 301 跳转 HTTPS、HTTPS 200、`certbot renew --dry-run` 成功。续期演练通过不等于已观察到未来定时续期执行。
- 用户已验收页面加载、区档切换、计算和保存。一次 reload 后立即检测 app_state.js 返回 404，后续复查文件存在且返回 200，实际配置指向新版。
- 完整包准备时 Python 53 项通过/1 项 Linux 专用测试在 Windows 跳过，JS 43 项及 DOM 桩启动冒烟通过，全库 0 错误；页脚修改后启动冒烟及包内哈希/源码一致性检查通过。
- 公安联网备案截图仅提供办理数据码，不是公安备案号；未展示数据码，公安备案完成状态未确认。
- VPN 下访问异常由用户报告，原因及 HTTPS 配置后的表现尚未确认。账号系统本轮不做，当前仍是静态前端和 localStorage。

上述线上结果来自用户执行命令后回传的输出及浏览器验收，非开发代理直接登录服务器验证。

## 本地打包

先运行README中的回归和全库校验，再在repo目录执行：

```powershell
python -B -X utf8 build_release.py --output "$env:TEMP\racepick-release.zip"
```

输出已存在会报错，请选择新的文件名。包内包含完整文件集和SHA256清单。
校验和用于检测传输损坏或漏传，不是签名；只使用自己生成的发布包。

## 服务器暂存

通过Workbench或SCP把发布包、`deploy_release.py`、`release_tools.py` 上传到服务器的管理目录，例如 `/root/racepick-deploy`。
管理脚本应放在网页目录外。Ubuntu服务器运行：

```bash
python3 /root/racepick-deploy/deploy_release.py --bundle /root/racepick-deploy/racepick-release.zip
```

工具检查完整文件集和哈希后，将版本放到 `/var/www/racepick-releases/<版本ID>`。
默认不更改正在使用的版本；重复暂存同一版本会校验已有内容，不覆盖。

## 首次启用版本目录

确认暂存成功后，在同一命令末尾加 `--activate`，建立或切换 `/var/www/racepick-releases/current`。
记录命令输出的版本ID。此操作尚不改变Nginx现有网站根目录。

在已有的Nginx racepick配置中，将：

```nginx
root /var/www/racepick;
```

改为：

```nginx
root /var/www/racepick-releases/current;
```

保持现有 `listen 127.0.0.1:8080`，通过 `nginx -t` 后再reload。内部HTTP及浏览器功能测试通过后才进入公开上线步骤。
首次切换失败时，可将Nginx root改回原目录并检查/reload；原 `/var/www/racepick` 不会被删除。

## 后续版本切换与回滚

后续每次上传完整发布包，先暂存，再显式 `--activate`。工具以原子替换链接的方式切换current，
避免用户访问到尚未上传完的目录；不涉及Nginx配置变化，通常无需reload。
这不保证切换时浏览器连续多个资源请求都落在同一版本，也不处理浏览器缓存，更新后仍须刷新并测试。

回滚到命令输出的上一版本ID：

```bash
python3 /root/racepick-deploy/deploy_release.py --rollback 上一版本ID
```

回滚同样先检查版本内容，拒绝切换到损坏的目录。工具不删除旧版本；首次没有上一版本时不能用版本ID回滚。
旧版本占用空间需在确认稳定后人工清理，保留当前和必要的回滚版本。开发机的临时发布包用完后清理。
