"""Apply only explicitly reviewed changes; default is a validated dry run."""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from data_tools import ROOT, atomic_write, car_key, configure_stdout, is_time, read_json
from format_json import format_data
from validate_data import validate_data


def apply_changes(data, report, cars):
    if report.get('version') != 1:
        raise ValueError('不支持的审核清单版本')
    result = deepcopy(data)
    original_tracks = {(t['大地图'], t['小地图']): t for t in data['tracks']}
    tracks = {(t['大地图'], t['小地图']): t for t in result['tracks']}
    if len(tracks) != len(result['tracks']):
        raise ValueError('源数据有重复赛道')
    identities = set()
    logs = []
    for change in report['changes']:
        if type(change.get('accepted')) is not bool:
            raise ValueError('accepted 必须是 true 或 false')
        if not change['accepted']:
            continue
        zone, tier = change['zone'], change['tier']
        if zone not in ('五区', '四区') or tier not in ('理论', '高手', '普通', '自动'):
            raise ValueError('无效区档')
        sc = change['sc']
        if type(sc) is not bool or (sc and tier not in ('理论', '高手')):
            raise ValueError('无效特殊跑法区档')
        for flag in ('old_present', 'new_present'):
            if type(change.get(flag)) is not bool:
                raise ValueError(f'{flag} 必须是布尔值')
        key = (change['big'], change['small'])
        car = (change['car'], change['stars'])
        route = change['sc_type'] or 'sc' if sc else None
        identity = (*key, zone, tier, *car, sc, route)
        if identity in identities:
            raise ValueError(f'同一条目接受了多个改动: {identity}')
        identities.add(identity)
        if key not in tracks:
            raise ValueError(f'新赛道需先补齐结构并审核: {key}')
        track = tracks[key]
        if zone not in track or tier not in track[zone]:
            raise ValueError(f'区档不存在: {identity}')
        entries = track[zone][tier]
        matches = [e for e in entries if len(e['cars']) == 1 and car_key(e['cars'][0]) == car
                   and bool(e.get('sc')) == sc and (not sc or (e.get('sc_type') or 'sc') == route)]
        if len(matches) > 1:
            raise ValueError(f'目标不唯一: {identity}')
        entry = matches[0] if matches else None
        original_matches = [e for e in original_tracks[key][zone][tier]
                            if len(e['cars']) == 1 and car_key(e['cars'][0]) == car
                            and bool(e.get('sc')) == sc and (not sc or (e.get('sc_type') or 'sc') == route)]
        if len(original_matches) > 1:
            raise ValueError(f'源数据目标不唯一: {identity}')
        original_entry = original_matches[0] if original_matches else None
        current = original_entry.get('time') if original_entry else None
        if tier in ('普通', '自动'):
            current = '✓' if original_entry else None
        # 存在性统一按「xlsx 该格是否有值」判定: sc 条目在 json 中可能只是占位
        # (带 sc/sc_type 但无 time), 对应空单元格, 故 sc 也看 time 是否存在。
        # 若按「条目是否存在」判定, diff 侧把占位填值报成 added(old_present=false) 时会误报旧值不匹配。
        current_present = current is not None
        if change['old_present'] != current_present or current != change['old']:
            raise ValueError(f'旧值不匹配，数据已变化: {identity}, 当前 {current!r}, 清单 {change["old"]!r}')
        new = change['new']
        if not change['new_present']:
            if new is not None or original_entry is None:
                raise ValueError(f'无效删除: {identity}')
            if entry is not None:
                entries.remove(entry)
            if tier == '高手' and not sc:
                track[zone]['普通'][:] = [e for e in track[zone]['普通']
                                           if not (not e.get('sc') and len(e['cars']) == 1 and car_key(e['cars'][0]) == car)]
        else:
            if tier in ('理论', '高手') and not is_time(new):
                raise ValueError(f'成绩必须是正有限数值: {identity} {new!r}')
            if tier in ('普通', '自动') and new != '✓':
                raise ValueError(f'可用性必须是 ✓: {identity}')
            if entry is None:
                car_data = {'name': car[0]}
                if car[1] is not None:
                    car_data['stars'] = car[1]
                entry = {'cars': [car_data]}
                if sc:
                    entry.update(sc=True, sc_type=route)
                entries.append(entry)
            if tier in ('理论', '高手'):
                entry['time'] = new
            if tier == '高手' and not sc:
                normal = track[zone]['普通']
                if not any(not e.get('sc') and len(e['cars']) == 1 and car_key(e['cars'][0]) == car for e in normal):
                    normal.append({'cars': deepcopy(entry['cars'])})
        logs.append(f'{identity}: {change["old"]!r} → {new!r}')
    # Do not reorder or rewrite unrelated tracks.
    touched = {(c['big'], c['small'], c['zone'], c['tier']) for c in report['changes'] if c.get('accepted') is True}
    for big, small, zone, tier in touched:
        if tier in ('理论', '高手'):
            tracks[(big, small)][zone][tier].sort(key=lambda e: (e.get('time') is None, e.get('time') or 0))
    errors, _ = validate_data(result, cars)
    if errors:
        raise ValueError('应用后校验失败:\n' + '\n'.join(errors))
    return result, logs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', type=Path, required=True, help='将接受条目的 accepted 改为 true 后的清单')
    parser.add_argument('--input', type=Path, default=ROOT / 'gauntlet_data.json')
    parser.add_argument('--cars', type=Path, default=ROOT / 'cars.json')
    parser.add_argument('--output', type=Path, help='写入独立预览 JSON；省略时仅检查')
    parser.add_argument('--write', action='store_true', help='应用已审核条目到输入 JSON，替换前自动备份')
    args = parser.parse_args(argv)
    configure_stdout()
    try:
        if args.write and args.output:
            raise ValueError('--write 与 --output 不能同时使用')
        target = args.input if args.write else args.output
        if target and target.resolve() in (args.review.resolve(), args.cars.resolve()):
            raise ValueError('输出不能覆盖审核清单或车辆库')
        if args.output and args.output.resolve() == args.input.resolve():
            raise ValueError('原地应用请明确使用 --write')
        digest = hashlib.sha256(args.input.read_bytes()).digest()
        result, logs = apply_changes(read_json(args.input), read_json(args.review), read_json(args.cars))
        for log in logs:
            print(log)
        if target and logs:
            output = format_data(result)
            if hashlib.sha256(args.input.read_bytes()).digest() != digest:
                raise ValueError('处理期间源数据变化，停止写入')
            atomic_write(target, output)
        print(f'已接受 {len(logs)} 条；' + (f'输出 {target}' if target and logs else '未写入文件'))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(1, f'应用失败: {error}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
