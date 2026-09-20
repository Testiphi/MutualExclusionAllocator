# Python 数据维护工具

需要 Python 3.10 或以上版本：

```powershell
python -m pip install -r requirements.txt
```

默认输入路径定位在脚本所在目录，与执行命令时的工作目录无关。
显式提供的相对路径则相对当前工作目录。工具导入时不执行文件读写。
所有命令失败时返回非零退出码。

## 导出与格式化

```powershell
python export_xlsx.py
python export_xlsx.py --input gauntlet_data.json --output baseline.xlsx
python format_json.py
python format_json.py --input gauntlet_data.json --output formatted.preview.json
python validate_data.py
python validate_data.py --input formatted.preview.json --cars cars.json
```

默认导出写入 `gauntlet_data.xlsx`（12 张工作表：五区/四区 × 理论/高手/普通/自动，
外加五区/四区 × 理论/高手_特殊跑法）；默认格式化仍写回源 JSON。
特殊跑法表行 = `大地图/小地图/跑法`，列同主表按车辆+星级拆分，格 = 成绩。
四张跑法表列出全部跑法组合并共用列集，空行表示该区档尚无数据，直接填值即可。
列序由 `export_xlsx.SC_COLUMN_ORDER` 控制：`'main'`（默认）沿用主表车序，
改成 `'sheet'` 则按本表内最快成绩排、无成绩车按主表序附后；列序不影响键控对比。
替换现有目标前自动保存带时间戳的 `.bak` 备份。
JSON 先检查格式化前后数据等价；Excel 先检查生成的 XLSX 压缩包，
随后以临时文件原子替换目标。缺少输出目录时明确报错，不自动创建目录。
格式化保留未知字段和原有字段顺序，并正确转义引号、反斜杠及换行。

校验包括赛道复合键、单车条目、重复条目、已知车名、星级上下限、
正有限成绩、特殊跑法标记、非特殊跑法高手到普通的镜像，以及理论/高手成绩排序。
特殊跑法条目必须带 `sc_type`，且类型必须在 `data_tools.SC_TYPES` 白名单内
（新增跑法类型须先在该常量登记，避免拼写变体混入）。
已有的 `sc: null` 与未设置标记兼容；旧版明细式 `特殊跑法` 工作表不再被解析。

## 键控对比和人工审核

先备份用户工作簿。建议另行导出基准，避免覆盖正在填写的文件：

```powershell
python export_xlsx.py --output baseline.xlsx
python diff_xlsx.py --base baseline.xlsx --user user.xlsx --output changes.review.json
```

`diff_xlsx.py` 是兼容入口，直接使用 `diff_workbooks.py` 也可。
行按 `(大地图, 小地图)` 匹配（特殊跑法表为 `(大地图, 小地图, 跑法)`），
列按车辆和星级标题匹配，不受行列移动影响；区档由工作表名解析。
普通/自动使用 `✓`。重复行、重复车辆列、空跑法行键和公式单元格会报错，避免静默丢值。
请先把公式转换为明确的实测数值。

清单包含 `structure`（新增/缺失工作表、赛道、车辆列）和 `changes`（值差异）。
每条值差异有稳定于本次清单的 `id`、完整目标键、`old`、`new`、存在性标记、
差异分类及 `accepted: false`。
逐条审核后，仅将明确接受的条目的 `accepted` 改为 `true`。
更慢成绩、删值和挪车需要逐条确认，不按“全选接受”自动处理。
保持其余目标键、旧值和存在性标记不变。

缺失工作表、赛道或车辆列只作为结构差异列出，**不会隐式转成批量删除**。
现有赛道上的新车列可生成值建议；应用时校验车名和星级。
新赛道或缺失区档需要先人工补齐并审核结构，再生成新的清单。
工具不会凭单张工作表猜测其他档位或删除整张赛道。

## 预检、预览和应用

```powershell
python apply_changes.py --review changes.review.json
python apply_changes.py --review changes.review.json --output updated.preview.json
python validate_data.py --input updated.preview.json
```

默认仅预检，不写文件。`--output` 将校验后的结果写到独立预览 JSON，
不能指向源 JSON、车辆库或审核清单。
确认后可明确写回：

```powershell
python apply_changes.py --review changes.review.json --write
python export_xlsx.py
python export_xlsx.py --output gauntlet_data_shared.xlsx
```

应用行为：

- 只处理 `accepted: true`，包括明确接受的更慢成绩和删除。
- 旧值检查针对本批操作开始前的源数据，不受自动镜像修改影响。
- 同一条目不能接受两个改动；旧值漂移、目标不唯一或全库校验失败时不写入。
- 有同键占位就填值；不存在才新增，保留已有条目的其他字段。
- 仅非特殊跑法高手条目补普通镜像；理论和特殊跑法不自动加镜像。
- 删除非特殊跑法高手条目时，同时删除对应普通镜像；自动档白名单不自动改动。
- 对本次修改的理论/高手列表按成绩升序排序，占位在末尾。
- 校验完整结果并复核源文件未在处理期间变化，然后备份并原子替换。
- 没有接受的改动时，不写入文件或创建备份。

应用后重新导出并键控对比。高手新增或删除带来的普通镜像差异应单独核对；
其余差异应只剩未接受的建议。工具不会自行提交或推送数据。

## 维护与测试

```powershell
python -m unittest test_data_tools -v
```

历史 `_diff_keyed_*.py`、`_apply_*.py`、校验脚本和用户表格备份保留作记录，
新任务使用上述固定入口，不再复制并修改日期脚本。
目前工具仍位于仓库根目录，避免同时迁移文件路径。
