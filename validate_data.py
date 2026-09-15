"""Validate track identities, entries, stars, times, mirrors and ordering."""
import argparse
from pathlib import Path
from data_tools import ROOT, ZONES, TIERS, ZONE4_MAX, car_key, configure_stdout, is_time, read_json


def validate_data(data, cars):
    errors = []
    known = set(cars.get('_nickname_map', {}))
    for car in cars['cars']:
        known.add(car['title'])
        if car.get('nickname'):
            known.add(car['nickname'])
    tracks_seen = set()
    counts = {f'{zone}_{tier}': 0 for zone in ZONES for tier in TIERS}
    for track in data['tracks']:
        track_key = (track['大地图'], track['小地图'])
        if track_key in tracks_seen:
            errors.append(f'重复赛道: {track_key}')
        tracks_seen.add(track_key)
        for zone in ZONES:
            tiers = track.get(zone, {})
            for tier, entries in tiers.items():
                label = f'{track_key} {zone}/{tier}'
                if tier not in TIERS or not isinstance(entries, list):
                    errors.append(f'无效档位结构: {label}')
                    continue
                counts[f'{zone}_{tier}'] += len(entries)
                seen = set()
                previous = None
                placeholder = False
                for entry in entries:
                    if not isinstance(entry, dict) or not isinstance(entry.get('cars'), list) or len(entry['cars']) != 1:
                        errors.append(f'条目必须包含一辆车: {label}')
                        continue
                    car = entry['cars'][0]
                    name, stars = car_key(car)
                    if name not in known:
                        errors.append(f'未知车名: {label} {name}')
                    maximum = ZONE4_MAX.get(name, 6) if zone == '四区' else 6
                    if stars is not None and (type(stars) is not int or not 1 <= stars <= maximum):
                        errors.append(f'星级越界: {label} {name}★{stars}')
                    if entry.get('sc') is not None and type(entry['sc']) is not bool:
                        errors.append(f'无效 sc: {label} {name}')
                    if entry.get('sc_type') is not None and not isinstance(entry['sc_type'], str):
                        errors.append(f'无效 sc_type: {label} {name}')
                    identity = (name, stars, bool(entry.get('sc')), str(entry.get('sc_type')))
                    if identity in seen:
                        errors.append(f'重复条目: {label} {identity}')
                    seen.add(identity)
                    time = entry.get('time')
                    if time is not None and not is_time(time):
                        errors.append(f'无效成绩: {label} {name} {time!r}')
                    elif tier in ('理论', '高手'):
                        if time is None:
                            placeholder = True
                        else:
                            if placeholder or (previous is not None and time < previous):
                                errors.append(f'成绩乱序: {label} {name}')
                            previous = time
            normal_keys = {car_key(e['cars'][0]) for e in tiers.get('普通', []) if not e.get('sc') and len(e.get('cars', [])) == 1}
            for entry in tiers.get('高手', []):
                if not entry.get('sc') and len(entry.get('cars', [])) == 1 and car_key(entry['cars'][0]) not in normal_keys:
                    errors.append(f'缺普通镜像: {track_key} {zone} {car_key(entry["cars"][0])}')
    return errors, counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'gauntlet_data.json')
    parser.add_argument('--cars', type=Path, default=ROOT / 'cars.json')
    args = parser.parse_args(argv)
    configure_stdout()
    try:
        errors, counts = validate_data(read_json(args.input), read_json(args.cars))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(1, f'校验失败: {error}\n')
    for name, count in counts.items():
        print(f'{name}: {count}')
    for error in errors:
        print(error)
    print(f'校验错误: {len(errors)}')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
