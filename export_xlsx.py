# -*- coding: utf-8 -*-
"""从 gauntlet_data.json 导出透视表格式 gauntlet_data.xlsx
- 12 sheets: 五区/四区 × 理论/高手/普通/自动 + 五区/四区 × 理论/高手_特殊跑法
- 行 = 大地图/小地图 (按大地图分组); 特殊跑法表行 = 大地图/小地图/跑法
- 列 = 车辆 (高手档按星级拆列, 如 ssc★2/ssc★6; 无星级条目显示纯车名)
- 格 = 成绩(秒), 无数据留空; 普通/自动档填 ✓ 表示该车可用
- 特殊跑法表列出全部跑法组合(含空行), 四张表共用行集; 列按各自区档收集
  (理论档只有纯车名列, 高手档只有带星列), 空行可直接填值

用法:
    python export_xlsx.py
    python export_xlsx.py --input gauntlet_data.json --output custom.xlsx
默认路径相对脚本目录；显式参数路径相对当前工作目录。
"""
import argparse
import json
from pathlib import Path
from data_tools import ROOT, SC_SUFFIX, atomic_save_workbook, configure_stdout
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

SCRIPT_DIR = ROOT
DEFAULT_INPUT = SCRIPT_DIR / 'gauntlet_data.json'
DEFAULT_OUTPUT = SCRIPT_DIR / 'gauntlet_data.xlsx'

HEADER_FILL = PatternFill('solid', fgColor='2F5496')
HEADER_FONT = Font(color='FFFFFF', bold=True, size=10)
ZONE_FILL = PatternFill('solid', fgColor='D9E2F3')   # 大地图分组行底色
TRACK_FONT = Font(size=10)
CAR_HEADER_FONT = Font(size=9, bold=True, color='1F3864')
CELL_FONT = Font(size=10)
THIN = Side(style='thin', color='BFBFBF')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center')

def car_combo_key(c):
    """(车名, 星级) — 高手档拆星级; None 星显示纯车名"""
    return (c['name'], c.get('stars'))

# ---------- 列排序: 数据量优先, 其次平均速度, 无数据车按名字排右侧 ----------

def compute_car_stats(tracks, zone):
    """每车: (覆盖赛道数, 平均相对速度)
    数据源: 理论+高手档 非sc 有time条目, 同一赛道取该车最快成绩
    相对速度 = 赛道最快成绩 / 该车成绩 (1.0 = 该赛道最快, 越小越慢)
    """
    # 先算每条赛道在该区的最快非sc成绩
    track_fastest = {}
    for t in tracks:
        best = None
        for tier in ('理论', '高手'):
            for e in t.get(zone, {}).get(tier, []):
                if e.get('sc') or e.get('time') is None:
                    continue
                if best is None or e['time'] < best:
                    best = e['time']
        if best is not None:
            track_fastest[(t['大地图'], t['小地图'])] = best
    # 每车每赛道最快成绩
    car_best = {}  # car -> {track_key: best_time}
    for t in tracks:
        tk = (t['大地图'], t['小地图'])
        for tier in ('理论', '高手'):
            for e in t.get(zone, {}).get(tier, []):
                if e.get('sc') or e.get('time') is None:
                    continue
                tm = e['time']
                for c in e.get('cars', []):
                    n = c['name']
                    if tk not in car_best.setdefault(n, {}) or tm < car_best[n][tk]:
                        car_best[n][tk] = tm
    stats = {}
    for n, track_times in car_best.items():
        ratios = [track_fastest[tk] / tm for tk, tm in track_times.items() if tk in track_fastest]
        stats[n] = (len(track_times), sum(ratios) / len(ratios) if ratios else 0.0)
    return stats

def order_combos(combos, stats):
    """列序: 车名按 (数据量↓, 速度↓, 名字) 排, 同车不同星聚在一起按星级升序
    None 星(纯车名)放该车组末尾
    """
    names = {n for n, s in combos}
    def key(n):
        cnt, spd = stats.get(n, (0, 0.0))
        return (-cnt, -spd, n)
    ranked = sorted(names, key=key)
    cols = []
    for n in ranked:
        stars = sorted({s for nn, s in combos if nn == n}, key=lambda s: (s is None, s if s is not None else 0))
        for s in stars:
            cols.append((n, s))
    return cols

def build_pivot_sheet(ws, tracks, zone, tier, show_check=False, stats=None, preset_cols=None):
    """透视表: 行=赛道, 列=车辆
    stats: compute_car_stats(tracks, zone) 结果, 用于数据量+速度排序
    preset_cols: 指定列序 (普通档镜像高手档)
    """
    # 收集列 (特殊跑法成绩见 *_特殊跑法 表, 不占主表列)
    combos = set()
    for t in tracks:
        for e in t.get(zone, {}).get(tier, []):
            if e.get('sc'):
                continue
            for c in e.get('cars', []):
                combos.add(car_combo_key(c))
    if preset_cols is not None:
        # 普通档镜像高手档列序; 防御: 万一有差异, 多余列按名字追加尾部
        cols = [k for k in preset_cols if k in combos]
        extra = sorted([k for k in combos if k not in preset_cols], key=lambda k: (k[0], k[1] if k[1] is not None else 0))
        cols += extra
    else:
        cols = order_combos(combos, stats)

    # 表头
    ws.cell(1, 1, '大地图')
    ws.cell(1, 2, '小地图')
    for j, (name, stars) in enumerate(cols, 3):
        label = f'{name}★{stars}' if stars else name
        ws.cell(1, j, label)
    for j in range(1, len(cols) + 3):
        c = ws.cell(1, j)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = CENTER
        c.border = BORDER

    # 行: 按大地图分组, 组间空一行? 不, 直接连续+大地图合并单元格
    r = 2
    cur_map = None
    map_start = 2
    for t in tracks:
        dm, xm = t['大地图'], t['小地图']
        if dm != cur_map:
            if cur_map is not None:
                ws.merge_cells(start_row=map_start, start_column=1, end_row=r - 1, end_column=1)
            cur_map = dm
            map_start = r
        # 构建该赛道单元格数据
        cell = {}
        for e in t.get(zone, {}).get(tier, []):
            if e.get('sc'):
                continue
            for c in e.get('cars', []):
                key = car_combo_key(c)
                val = e.get('time')
                if key in cell and val is not None and cell[key] is not None:
                    # 同格多值: 取更快(更小), 记录警告
                    cell[key] = min(cell[key], val)
                elif val is not None:
                    cell[key] = val
                elif key not in cell:
                    cell[key] = None
        ws.cell(r, 1, dm)
        ws.cell(r, 2, xm)
        for j, key in enumerate(cols, 3):
            v = cell.get(key)
            if show_check:
                # 普通/自动: 有条目填 ✓
                if key in cell:
                    ws.cell(r, j, '✓')
            else:
                if v is not None:
                    ws.cell(r, j, v)
        # 样式
        for j in range(1, len(cols) + 3):
            c = ws.cell(r, j)
            c.border = BORDER
            if j <= 2:
                c.font = TRACK_FONT
            else:
                c.font = CELL_FONT
                c.alignment = CENTER
        if dm == cur_map:
            ws.cell(r, 1).fill = ZONE_FILL
        r += 1
    if cur_map is not None:
        ws.merge_cells(start_row=map_start, start_column=1, end_row=r - 1, end_column=1)
        ws.cell(map_start, 1).fill = ZONE_FILL
        ws.cell(map_start, 1).alignment = CENTER

    # 列宽
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 14
    for j in range(3, len(cols) + 3):
        ws.column_dimensions[get_column_letter(j)].width = 7.5
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(cols)+2)}{r-1}'
    return cols

# ---------- 特殊跑法: 行 = 赛道·跑法, 列 = 车辆 ----------
# 行集四张表共用(全部跑法组合), 列集按 (区, 档) 各自收集 —— 与主表 build_pivot_sheet 一致:
#   理论档列集只含不带星条目, 高手档列集只含带星条目。
# 列序: 'main' 沿用主表车序(数据量+速度); 'sheet' 按本表内最快成绩排, 无成绩车按主表序附后。
# 两种列序只影响展示, 键控对比按表头集合比较, 不会产生差异条目。
SC_COLUMN_ORDER = 'main'

def collect_sc_rows(tracks):
    """全部 (大地图, 小地图, 跑法) 组合, 按数据出现顺序
    四张跑法表都列全: 空行即"该区档还没数据", 填值即可, 无需插行
    """
    rows, seen = [], set()
    for t in tracks:
        for zone in ('五区', '四区'):
            for tier in ('理论', '高手'):
                for e in t.get(zone, {}).get(tier, []):
                    if not e.get('sc'):
                        continue
                    key = (t['大地图'], t['小地图'], e.get('sc_type') or 'sc')
                    if key not in seen:
                        seen.add(key)
                        rows.append(key)
    return rows

def collect_sc_combos(tracks, zone, tier):
    """本区本档 sc 条目涉及的 (车名, 星级) 集合 —— 该表自己的列集"""
    combos = set()
    for t in tracks:
        for e in t.get(zone, {}).get(tier, []):
            if e.get('sc'):
                for c in e.get('cars', []):
                    combos.add(car_combo_key(c))
    return combos

def sc_cell_values(tracks, zone, tier):
    """{(大地图, 小地图, 跑法): {(车名, 星级): 成绩}}"""
    cells = {}
    for t in tracks:
        for e in t.get(zone, {}).get(tier, []):
            if not e.get('sc'):
                continue
            values = cells.setdefault((t['大地图'], t['小地图'], e.get('sc_type') or 'sc'), {})
            for c in e.get('cars', []):
                key, value = car_combo_key(c), e.get('time')
                if value is None:
                    values.setdefault(key, None)
                elif values.get(key) is None:
                    values[key] = value
                else:
                    values[key] = min(values[key], value)
    return cells

def order_sc_combos(combos, cells, stats):
    """特殊跑法列序（SC_COLUMN_ORDER）；同车不同星始终聚在一起
    combos 必须是本区本档的列集, 排序键也只在该集合内取
    """
    main_cols = order_combos(combos, stats)
    if SC_COLUMN_ORDER != 'sheet':
        return main_cols
    best = {}
    for values in cells.values():
        for combo, value in values.items():
            if value is not None and (combo[0] not in best or value < best[combo[0]]):
                best[combo[0]] = value
    rank = {combo: index for index, combo in enumerate(main_cols)}
    names = {name for name, _ in combos}
    def key(name):
        return (best.get(name) is None, best.get(name, 0.0),
                min([rank[c] for c in combos if c[0] == name] or [len(rank)]))
    cols = []
    for name in sorted(names, key=key):
        stars = sorted({s for n, s in combos if n == name}, key=lambda s: (s is None, s if s is not None else 0))
        cols += [(name, s) for s in stars]
    return cols

def build_sc_pivot_sheet(ws, tracks, zone, tier, row_keys, stats=None):
    """特殊跑法透视表: 行 = 大地图/小地图/跑法, 列 = 车辆, 格 = 成绩
    列集按本区本档 sc 条目收集 —— 理论档无星列, 高手档带星列
    """
    cells = sc_cell_values(tracks, zone, tier)
    cols = order_sc_combos(collect_sc_combos(tracks, zone, tier), cells, stats)

    for j, header in enumerate(('大地图', '小地图', '跑法'), 1):
        ws.cell(1, j, header)
    for j, (name, stars) in enumerate(cols, 4):
        ws.cell(1, j, f'{name}★{stars}' if stars else name)
    for j in range(1, len(cols) + 4):
        c = ws.cell(1, j)
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
        c.alignment = CENTER
        c.border = BORDER

    r = 2
    cur_map = None
    map_start = 2
    for dm, xm, route in row_keys:
        if dm != cur_map:
            if cur_map is not None:
                ws.merge_cells(start_row=map_start, start_column=1, end_row=r - 1, end_column=1)
            cur_map = dm
            map_start = r
        values = cells.get((dm, xm, route), {})
        ws.cell(r, 1, dm)
        ws.cell(r, 2, xm)
        ws.cell(r, 3, route)
        for j, key in enumerate(cols, 4):
            value = values.get(key)
            if value is not None:
                ws.cell(r, j, value)
        for j in range(1, len(cols) + 4):
            c = ws.cell(r, j)
            c.border = BORDER
            if j <= 3:
                c.font = TRACK_FONT
            else:
                c.font = CELL_FONT
                c.alignment = CENTER
        if dm == cur_map:
            ws.cell(r, 1).fill = ZONE_FILL
        r += 1
    if cur_map is not None:
        ws.merge_cells(start_row=map_start, start_column=1, end_row=r - 1, end_column=1)
        ws.cell(map_start, 1).fill = ZONE_FILL
        ws.cell(map_start, 1).alignment = CENTER

    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 14
    ws.column_dimensions['C'].width = 12
    for j in range(4, len(cols) + 4):
        ws.column_dimensions[get_column_letter(j)].width = 7.5
    ws.freeze_panes = 'D2'
    if row_keys:
        ws.auto_filter.ref = f'A1:{get_column_letter(len(cols)+3)}{r-1}'
    return cols

def build_workbook(tracks):
    """从赛道数据构建工作簿与导出统计，不读写文件。"""
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    sheet_stats = {}
    for zone in ['五区', '四区']:
        car_stats = compute_car_stats(tracks, zone)
        high_cols = None
        for tier, show in [('理论', False), ('高手', False), ('普通', True), ('自动', True)]:
            worksheet = workbook.create_sheet(f'{zone}_{tier}')
            preset = high_cols if tier == '普通' else None
            cols = build_pivot_sheet(
                worksheet, tracks, zone, tier,
                show_check=show, stats=car_stats, preset_cols=preset,
            )
            if tier == '高手':
                high_cols = cols
            sheet_stats[f'{zone}_{tier}'] = len(cols)
    sc_rows = collect_sc_rows(tracks)
    for zone in ['五区', '四区']:
        car_stats = compute_car_stats(tracks, zone)
        for tier in ['理论', '高手']:
            name = f'{zone}_{tier}_{SC_SUFFIX}'
            worksheet = workbook.create_sheet(name)
            sheet_stats[name] = len(build_sc_pivot_sheet(
                worksheet, tracks, zone, tier, sc_rows, stats=car_stats))
    return workbook, sheet_stats


def export_workbook(input_path, output_path):
    """读取 JSON 并导出工作簿，返回各工作表统计。"""
    input_path = Path(input_path)
    output_path = Path(output_path)
    if input_path.resolve() == output_path.resolve():
        raise ValueError('输入与输出不能是同一个文件')
    with input_path.open(encoding='utf-8') as source:
        data = json.load(source)
    workbook, sheet_stats = build_workbook(data['tracks'])
    try:
        atomic_save_workbook(workbook, output_path)
    finally:
        workbook.close()
    return sheet_stats


def main(argv=None):
    parser = argparse.ArgumentParser(description='将赛道 JSON 导出为十二张工作表的 Excel 工作簿')
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT, help='输入 JSON（默认：脚本目录下 gauntlet_data.json）')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='输出 Excel（默认：脚本目录下 gauntlet_data.xlsx）')
    args = parser.parse_args(argv)
    configure_stdout()
    try:
        sheet_stats = export_workbook(args.input, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'导出失败: {error}\n')
    print('saved:', args.output)
    for sheet_name, count in sheet_stats.items():
        print(f'  {sheet_name}: 列数/条目 = {count}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
