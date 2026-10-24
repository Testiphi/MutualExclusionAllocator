# 回归测试

在仓库根目录运行 Python 测试（包含 `backend/` 中的测试）：

```powershell
python -B -X utf8 -m unittest discover -p 'test*.py' -q
```

运行前端测试：

```powershell
$racepickTests = Get-ChildItem tests -Filter 'test*.js' | ForEach-Object FullName
node --test @racepickTests
```

运行单项测试：`node --test tests/test_race_scores.js` 或 `python -B -m unittest tests.test_data_tools -q`。

后端测试保留在 `backend/`，邮件工具测试保留在 `tools/`；不连接正式服务器，也不使用正式账号库。
