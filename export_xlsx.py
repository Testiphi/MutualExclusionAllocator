# -*- coding: utf-8 -*-
"""从 gauntlet_data.json 重新导出 gauntlet_data.xlsx（全量 9 sheet）"""
import json, sys
sys.stdout.reconfigure(encoding='utf-8')
import openpyxl
from openpyxl.styles import Font, PatternFill

JSON = 'C:/Users/asus/.openclaw/workspace/tasks/mutex-alloc/repo/gauntlet_data.json'
XLSX = 'C:/Users/asus/.openclaw/workspace/tasks/mutex-alloc/repo/gauntlet_data.xlsx'

d = json.load(open(JSON, encoding='utf-8'))
wb = openpyxl.Workbook()

HEADER = ['大地图', '小地图', '序号', '车辆', '星级', '成绩', '特殊跑法', '特殊跑法类型']
SC_HEADER = ['大地图', '小地图', '区', '档位', '车辆', '星级', '成绩', '特殊跑法类型']
HEADER_FILL = PatternFill('solid', fgColor='2F5496')
HEADER_FONT = Font(color='FFFFFF', bold=True)

sc_rows = []  # 特殊跑法汇总

def stars_str(c):
    s = c.get('stars')
    return f'★{s}' if s else None

def sc_flag(e):
    return 'sc' if e.get('sc') else None

def build_sheet(name, zone, tier, with_stars):
    ws = wb.create_sheet(name)
    ws.append(HEADER)
    for c in ws[1]:
        c.fill = HEADER_FILL
        c.font = HEADER_FONT
    n = 0
    for t in d['tracks']:
        entries = t.get(zone, {}).get(tier, [])
        if not entries:
            continue
        for e in entries:
            for c in e.get('cars', []):
                n += 1
                ws.append([t['大地图'], t['小地图'], n, c['name'],
                           stars_str(c) if with_stars else None,
                           e.get('time'), sc_flag(e), e.get('sc_type')])
                if e.get('sc'):
                    sc_rows.append([t['大地图'], t['小地图'], zone, tier, c['name'],
                                    stars_str(c), e.get('time'), e.get('sc_type')])
    return ws

# 8 个 zone/tier sheets（高手档带星级）
build_sheet('五区_理论', '五区', '理论', False)
build_sheet('五区_高手', '五区', '高手', True)
build_sheet('五区_普通', '五区', '普通', False)
build_sheet('五区_自动', '五区', '自动', False)
build_sheet('四区_理论', '四区', '理论', False)
build_sheet('四区_高手', '四区', '高手', True)
build_sheet('四区_普通', '四区', '普通', False)
build_sheet('四区_自动', '四区', '自动', False)

# 特殊跑法汇总
ws = wb.create_sheet('特殊跑法')
ws.append(SC_HEADER)
for c in ws[1]:
    c.fill = HEADER_FILL
    c.font = HEADER_FONT
for r in sc_rows:
    ws.append(r)

# 移除默认 sheet
if 'Sheet' in wb.sheetnames:
    del wb['Sheet']

wb.save(XLSX)
print('saved:', XLSX)
print('sheets:', wb.sheetnames)
for name in wb.sheetnames:
    print(f'  {name}: {wb[name].max_row - 1} rows')
