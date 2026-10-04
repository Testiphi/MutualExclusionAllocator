# 完整版本发布与回滚

当前运行文件为九个，发布工具只打包这些文件，不包含工作簿、Python工具、Git或密钥。
本工具尚未在真实Linux服务器验证目录链接切换；首次使用先暂存、核验，再启用。
现有直接上传到 `/var/www/racepick` 的方式仍有效，不会被工具自动改动。

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
