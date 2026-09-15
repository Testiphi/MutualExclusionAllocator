"""Keyed workbook parsing; reject ambiguous rows, columns and formulas."""
import openpyxl
from data_tools import ZONES, TIERS, parse_column


def load_workbook_data(path):
    workbook = openpyxl.load_workbook(path, data_only=False)
    result = {}
    try:
        for sheet in workbook:
            for row in sheet:
                if any(cell.data_type == 'f' for cell in row):
                    raise ValueError(f'请将公式转为明确数值: {sheet.title}')
            if sheet.title == '特殊跑法':
                values = {}
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if all(v in (None, '') for v in row):
                        continue
                    big, small, name, stars, zone_tier, time, route = row[:7]
                    stars = int(str(stars).removeprefix('★')) if stars not in (None, '') else None
                    if zone_tier not in ('五区理', '五区高', '四区理', '四区高'):
                        raise ValueError(f'无效区档: {zone_tier}')
                    key = (big, small, name, stars, zone_tier[:2], '理论' if zone_tier[-1] == '理' else '高手', route or 'sc')
                    if key in values:
                        raise ValueError(f'重复特殊跑法键: {key}')
                    values[key] = time
                result[sheet.title] = {'values': values}
                continue
            if sheet.title not in {f'{z}_{t}' for z in ZONES for t in TIERS}:
                continue
            headers = [sheet.cell(1, c).value for c in range(3, sheet.max_column + 1)]
            present = [h for h in headers if h not in (None, '')]
            if len(set(present)) != len(present):
                raise ValueError(f'重复车辆列: {sheet.title}')
            for header in present:
                parse_column(header)
            rows = {}
            big = None
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if row[0] not in (None, ''):
                    big = row[0]
                if row[1] in (None, ''):
                    continue
                key = (big, row[1])
                if big is None or key in rows:
                    raise ValueError(f'缺大地图或重复赛道: {sheet.title} {key}')
                rows[key] = {header: value for header, value in zip(headers, row[2:])
                             if header not in (None, '') and value not in (None, '')}
            result[sheet.title] = {'headers': present, 'rows': rows}
        return result
    finally:
        workbook.close()
