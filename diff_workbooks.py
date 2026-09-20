"""Generate keyed, reviewable changes; every change starts accepted=false."""
import argparse
import json
from pathlib import Path
from data_tools import ROOT, atomic_write, configure_stdout, is_time, parse_column, parse_sheet_name
from xlsx_tools import load_workbook_data


def compare_workbooks(base, user):
    changes, structure = [], []
    for sheet in sorted(set(base) | set(user)):
        if sheet not in base or sheet not in user:
            structure.append({'sheet': sheet, 'kind': 'sheet_added' if sheet in user else 'sheet_missing'})
            continue
        parsed = parse_sheet_name(sheet)
        if parsed is None:
            continue
        zone, tier, sc = parsed
        left, right = base[sheet], user[sheet]
        for column in sorted(set(left['headers']) ^ set(right['headers'])):
            structure.append({'sheet': sheet, 'kind': 'column_added' if column in right['headers'] else 'column_missing', 'column': column})
        for key in sorted(set(left['rows']) ^ set(right['rows'])):
            structure.append({'sheet': sheet, 'kind': 'track_added' if key in right['rows'] else 'track_missing', 'track': list(key)})
        # Missing sheets/rows/columns are structural findings, never implicit deletions.
        for key in sorted(set(left['rows']) & set(right['rows'])):
            lrow, rrow = left['rows'][key], right['rows'][key]
            route = key[2] if sc else None
            for column in right['headers']:
                old, new = lrow.get(column), rrow.get(column)
                if old == new or (column not in left['headers'] and new is None):
                    continue
                name, stars = parse_column(column)
                changes.append({'sheet': sheet, 'big': key[0], 'small': key[1], 'zone': zone, 'tier': tier,
                                'car': name, 'stars': stars, 'sc': sc, 'sc_type': route,
                                'old': old, 'new': new, 'old_present': old is not None, 'new_present': new is not None})
    for index, change in enumerate(changes, 1):
        old, new = change['old'], change['new']
        change.update(id=index, accepted=False, kind=('added' if not change['old_present'] else 'deleted' if not change['new_present'] else
                      'faster' if is_time(old) and is_time(new) and new < old else
                      'slower' if is_time(old) and is_time(new) and new > old else 'changed'))
    return {'version': 1, 'structure': structure, 'changes': changes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=ROOT / 'gauntlet_data.xlsx')
    parser.add_argument('--user', type=Path, default=ROOT / 'gauntlet_data.user.xlsx')
    parser.add_argument('--output', type=Path, help='审核清单 JSON')
    args = parser.parse_args(argv)
    configure_stdout()
    try:
        if args.output and args.output.resolve() in (args.base.resolve(), args.user.resolve()):
            raise ValueError('清单不能覆盖输入工作簿')
        report = compare_workbooks(load_workbook_data(args.base), load_workbook_data(args.user))
        if args.output:
            atomic_write(args.output, json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        for finding in report['structure']:
            print('结构差异:', finding)
        for change in report['changes']:
            print(f"#{change['id']} {change['kind']} {change['sheet']} {change['big']}/{change['small']} {change['car']}★{change['stars']}: {change['old']} → {change['new']}")
        print(f"值差异 {len(report['changes'])}；结构差异 {len(report['structure'])}；均未自动接受")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'对比失败: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
